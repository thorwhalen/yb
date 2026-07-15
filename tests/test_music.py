"""Tests for yb.music — the publish-facing facade over muvid.visualize.

The rendering itself is tested in ``muvid``; here we test the yb-side glue:
title/cover resolution, the folder→album planning, and (with ffmpeg) that a
prepared music video carries the right :class:`PublicationContent`.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from yb.music.publish import (
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


def test_folder_item_is_a_plain_record(tmp_path):
    item = FolderItem(audio=tmp_path / "x.wav", image=None, title="X", visual="cqt")
    assert (item.title, item.visual, item.image) == ("X", "cqt", None)


def test_the_default_cycle_is_the_five_reactive_visuals():
    assert DEFAULT_VISUAL_CYCLE == ("waves", "cqt", "spectrum", "bars", "scope")


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
