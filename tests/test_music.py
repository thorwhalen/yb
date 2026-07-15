"""Tests for yb.music — the publish-facing facade over muvid.visualize.

The rendering itself is tested in ``muvid``; here we test the yb-side glue:
title/cover resolution, the folder→album planning, and (with ffmpeg) that a
prepared music video carries the right :class:`PublicationContent`.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

# yb.music imports muvid.visualize; skip the whole module (don't error at
# collection) when the 'music' extra isn't installed.
pytest.importorskip("muvid.visualize", reason="needs pip install 'yb[music]'")

from yb.music.publish import (  # noqa: E402
    DEFAULT_VISUAL_CYCLE,
    FolderItem,
    _as_song_list,
    _image_for,
    _title_from,
    pair_folder,
)

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is not installed")


# --------------------------------------------------------------------------
# title / cover resolution
# --------------------------------------------------------------------------


def test_title_falls_back_to_a_tidied_filename(tmp_path):
    assert _title_from(tmp_path / "time_to_go_home.wav") == "Time To Go Home"
    assert _title_from(tmp_path / "01 - Blue Moon.wav") == "Blue Moon"
    assert _title_from(tmp_path / "Already Nice.wav") == "Already Nice"


def test_songs_can_be_one_path_a_list_or_a_directory(tmp_path):
    (tmp_path / "b.wav").touch()
    (tmp_path / "a.mp3").touch()
    (tmp_path / "notes.txt").touch()
    assert _as_song_list(tmp_path / "a.mp3") == [tmp_path / "a.mp3"]
    assert _as_song_list([tmp_path / "b.wav"]) == [tmp_path / "b.wav"]
    assert _as_song_list(tmp_path) == [tmp_path / "a.mp3", tmp_path / "b.wav"]


def test_images_may_be_shared_or_per_song(tmp_path):
    song = tmp_path / "01.wav"
    assert _image_for(song, None) is None
    assert _image_for(song, tmp_path / "shared.png") == tmp_path / "shared.png"
    assert _image_for(song, {"01.wav": tmp_path / "a.png"}) == tmp_path / "a.png"
    assert _image_for(song, {"01": tmp_path / "b.png"}) == tmp_path / "b.png"  # by stem
    assert _image_for(song, {"other.wav": tmp_path / "c.png"}) is None


# --------------------------------------------------------------------------
# folder → album planning
# --------------------------------------------------------------------------


def test_pair_folder_matches_covers_by_stem_and_cycles_visuals(tmp_path):
    # Six songs, some with same-stem covers, some without.
    for name in [
        "01 Alpha",
        "02 Beta",
        "03 Gamma",
        "04 Delta",
        "05 Epsilon",
        "06 Zeta",
    ]:
        (tmp_path / f"{name}.wav").touch()
    (tmp_path / "01 Alpha.jpeg").touch()
    (tmp_path / "03 Gamma.png").touch()

    plan = pair_folder(tmp_path)
    assert [item.title for item in plan] == [
        "Alpha",
        "Beta",
        "Gamma",
        "Delta",
        "Epsilon",
        "Zeta",
    ]
    # covers matched by stem; missing ones are None.
    assert plan[0].image == tmp_path / "01 Alpha.jpeg"
    assert plan[2].image == tmp_path / "03 Gamma.png"
    assert plan[1].image is None
    # visuals rotate through the cycle in order, wrapping past its length.
    assert [item.visual for item in plan] == [
        *DEFAULT_VISUAL_CYCLE,
        DEFAULT_VISUAL_CYCLE[0],
    ]


def test_pair_folder_honours_a_custom_cycle(tmp_path):
    (tmp_path / "a.wav").touch()
    (tmp_path / "b.wav").touch()
    (tmp_path / "c.wav").touch()
    plan = pair_folder(tmp_path, cycle=["cqt", "waves"])
    assert [item.visual for item in plan] == ["cqt", "waves", "cqt"]


def test_pair_folder_treats_same_stem_files_as_one_song_preferring_lossless(tmp_path):
    # A lossless master next to a distribution copy is ONE song, not two videos
    # writing the same "Blue Moon.mp4".
    (tmp_path / "Blue Moon.wav").touch()
    (tmp_path / "Blue Moon.mp3").touch()
    (tmp_path / "Red Sun.mp3").touch()
    plan = pair_folder(tmp_path)
    assert [item.title for item in plan] == ["Blue Moon", "Red Sun"]
    assert plan[0].audio.suffix == ".wav"  # the master won
    assert len({item.audio.with_suffix(".mp4") for item in plan}) == 2  # no collision


def test_pair_folder_skips_hidden_and_sidecar_files(tmp_path):
    (tmp_path / "Song.wav").touch()
    (tmp_path / "._Song.wav").touch()  # macOS AppleDouble sidecar — suffix is .wav
    (tmp_path / ".hidden.wav").touch()
    (tmp_path / "sub").mkdir()
    plan = pair_folder(tmp_path)
    assert [item.audio.name for item in plan] == ["Song.wav"]


def test_folder_item_is_a_plain_record(tmp_path):
    item = FolderItem(audio=tmp_path / "x.wav", image=None, title="X", visual="cqt")
    assert (item.title, item.visual, item.image) == ("X", "cqt", None)


def test_the_default_cycle_is_the_five_reactive_visuals():
    assert DEFAULT_VISUAL_CYCLE == ("waves", "cqt", "spectrum", "bars", "scope")


def _fake_prepared(titles):
    """Minimal MusicVideo stand-ins for publish_folder(prepared=...) tests."""
    from types import SimpleNamespace

    from yb.content import PublicationContent
    from yb.music.publish import MusicVideo

    return [
        MusicVideo(
            audio=None,
            video=None,
            thumbnail=None,
            content=PublicationContent(media="x.mp4", title=t),
            render=SimpleNamespace(visual="cqt", duration=1.0),
        )
        for t in titles
    ]


def test_publish_folder_keeps_successes_when_one_upload_fails(monkeypatch):
    import yb.youtube.auth as auth
    import yb.youtube.publish as ytpub
    from yb.music import publish_folder

    monkeypatch.setattr(auth, "get_service", lambda *a, **k: object())

    def fake_publish_content(content, **kwargs):
        if content.title == "Two":
            raise RuntimeError("simulated 503")
        return {"video_id": f"id-{content.title}", "url": f"http://y/{content.title}"}

    monkeypatch.setattr(ytpub, "publish_content", fake_publish_content)

    results = publish_folder(
        None, prepared=_fake_prepared(["One", "Two", "Three"]), progress=False
    )
    assert [r["title"] for r in results] == ["One", "Two", "Three"]
    assert [r["ok"] for r in results] == [True, False, True]  # batch not aborted
    assert results[0]["video_id"] == "id-One"  # success preserved
    assert results[2]["video_id"] == "id-Three"  # after the failure
    assert "simulated 503" in results[1]["error"]


def test_publish_folder_limit_applies_to_prepared(monkeypatch):
    import yb.youtube.auth as auth
    import yb.youtube.publish as ytpub
    from yb.music import publish_folder

    monkeypatch.setattr(auth, "get_service", lambda *a, **k: object())
    monkeypatch.setattr(
        ytpub, "publish_content", lambda content, **k: {"video_id": content.title}
    )
    results = publish_folder(
        None, prepared=_fake_prepared(["One", "Two", "Three"]), limit=1, progress=False
    )
    assert [r["title"] for r in results] == ["One"]


# --------------------------------------------------------------------------
# end to end (renders through muvid.visualize)
# --------------------------------------------------------------------------


@pytest.fixture
def song_and_cover(tmp_path):
    audio, image = tmp_path / "Test Song.wav", tmp_path / "Test Song.png"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2:sample_rate=48000",
            "-ac",
            "2",
            str(audio),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=teal:s=300x400",
            "-frames:v",
            "1",
            str(image),
        ],
        check=True,
    )
    return audio, image


@needs_ffmpeg
def test_prepare_music_video_bundles_video_thumbnail_and_content(
    song_and_cover, tmp_path
):
    from yb.music import prepare_music_video

    audio, image = song_and_cover
    mv = prepare_music_video(
        audio,
        image,
        title="Test Song",
        artist="Testy",
        output_dir=tmp_path / "out",
        size=(320, 180),
        fps=10,
        normalize=False,
    )
    assert mv.video.exists()
    assert mv.thumbnail and mv.thumbnail.exists()
    assert mv.content.title == "Testy - Test Song"
    assert mv.content.media == mv.video
    assert mv.content.thumbnail == mv.thumbnail


@needs_ffmpeg
def test_prepare_folder_renders_each_song_with_its_rotated_visual(
    song_and_cover, tmp_path
):
    from yb.music import prepare_folder

    # A folder of three songs sharing one synthesized cover.
    _, cover = song_and_cover
    folder = tmp_path / "album"
    folder.mkdir()
    for name in ["01 One", "02 Two", "03 Three"]:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=330:duration=1:sample_rate=48000",
                "-ac",
                "2",
                str(folder / f"{name}.wav"),
            ],
            check=True,
        )
        shutil.copy(cover, folder / f"{name}.png")

    videos = prepare_folder(
        folder, cycle=["cqt", "waves"], size=(320, 180), fps=10, normalize=False
    )
    assert len(videos) == 3
    assert all(v.video.exists() for v in videos)
    assert [v.render.visual for v in videos] == ["cqt", "waves", "cqt"]
    assert [v.content.title for v in videos] == ["One", "Two", "Three"]
