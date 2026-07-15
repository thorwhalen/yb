"""Prepare and publish songs as YouTube music videos.

The publication-facing facade over :mod:`muvid.visualize` (the audio→video
renderer): a song (and usually a cover) becomes a video, a thumbnail, and a
:class:`~yb.content.PublicationContent` — which the existing :mod:`yb.youtube`
machinery uploads exactly as it uploads anything else.

Needs ``pip install 'yb[music]'`` (which pulls ``muvid``); uploading additionally
needs ``yb[youtube]``.

Simple things simple::

    >>> from yb.music import prepare_music_video, publish_music
    >>> mv = prepare_music_video("song.wav", image="cover.png")     # doctest: +SKIP
    >>> publish_music("song.wav", image="cover.png",                # doctest: +SKIP
    ...               privacy_status="unlisted")

An album stays a set: one visual template, one loudness target, one playlist::

    >>> publish_music(["01.wav", "02.wav"], images={"01.wav": "01.png"},  # doctest: +SKIP
    ...               visual="ken_burns", playlist="My Album")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from yb.content import PublicationContent

try:
    from muvid.visualize import (
        DEFAULT_FPS,
        DEFAULT_SIZE,
        THUMBNAIL_SIZE,
        CoverLayout,
        Loudness,
        PathLike,
        RenderResult,
        TitleStyle,
        render_audio_video,
        thumbnail_image,
    )
    from muvid.visualize.visuals import Visual
except ImportError as e:  # pragma: no cover - environment dependent
    raise ImportError(
        "yb.music needs the 'muvid' package for audio→video rendering "
        "(pip install 'yb[music]')."
    ) from e

from yb.youtube.metadata import CATEGORY_MUSIC

#: The visual template rotated across an album so its videos vary yet cohere —
#: the order :func:`publish_folder` cycles through by default.
DEFAULT_VISUAL_CYCLE = ("waves", "cqt", "spectrum", "bars", "scope")

_AUDIO_SUFFIXES = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".aiff"}
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


@dataclass
class MusicVideo:
    """A song, rendered and ready to publish.

    Attributes:
        audio: The source song.
        video: The rendered mp4.
        thumbnail: The 16:9 thumbnail derived from the cover, if there was one.
        content: The platform-neutral content bundle (title, description,
            keywords, thumbnail) that any ``yb`` adapter can publish.
        render: What the renderer did — duration, visual, loudness measurement.
    """

    audio: Path
    video: Path
    thumbnail: Path | None
    content: PublicationContent
    render: RenderResult


def prepare_music_video(
    audio: PathLike,
    image: PathLike | None = None,
    *,
    visual: str | Visual = "auto",
    title: str | None = None,
    artist: str | None = None,
    description: str = "",
    keywords: Sequence[str] = (),
    output_dir: PathLike | None = None,
    normalize: bool = True,
    loudness: Loudness | None = None,
    thumbnail: bool = True,
    burn_title: bool = False,
    size: tuple[int, int] = DEFAULT_SIZE,
    fps: int = DEFAULT_FPS,
    layout: CoverLayout | None = None,
    title_style: TitleStyle | None = None,
    thumbnail_size: tuple[int, int] = THUMBNAIL_SIZE,
    options: dict | None = None,
) -> MusicVideo:
    """Turn a song into a publishable music video (no upload).

    The title falls back to the audio file's tags, then to a tidied filename,
    so the one-argument call already produces something sensible. A cover image
    becomes both the picture and — by default — the thumbnail.

    Args:
        audio: The song. Prefer the lossless master (``.wav``) when you have it.
        image: Cover art.
        visual: Visual strategy: a name, ``"auto"``, or a callable
            (see :mod:`muvid.visualize.visuals`).
        title: Video title (default: from tags, else the filename).
        artist: Artist name; when given, the title becomes ``"Artist - Title"``.
        description: Video description.
        keywords: Tags for the upload.
        output_dir: Where the video and thumbnail go (default: next to ``audio``).
        normalize: Loudness-normalize to a consistent target (default ``True`` —
            this is what makes a set of songs play back at one level).
        loudness: Override the loudness target.
        thumbnail: Derive a 16:9 thumbnail from the cover.
        burn_title: Also draw the title into the video frame.
        size / fps / layout / title_style / options: Passed to the renderer.
        thumbnail_size: Thumbnail size (YouTube wants >= 1280x720).

    Returns:
        A :class:`MusicVideo`.
    """
    audio = Path(audio)
    image = Path(image) if image else None
    out_dir = Path(output_dir) if output_dir else audio.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    song_title = title or _title_from(audio)
    video_title = f"{artist} - {song_title}" if artist else song_title

    render = render_audio_video(
        audio,
        image,
        visual=visual,
        saveas=out_dir / f"{audio.stem}.mp4",
        size=size,
        fps=fps,
        title=song_title if burn_title else None,
        layout=layout,
        title_style=title_style,
        normalize=normalize,
        loudness=loudness,
        options=options,
    )

    thumb = None
    if thumbnail and image is not None:
        thumb = thumbnail_image(
            image,
            saveas=out_dir / f"{audio.stem}.thumb.jpg",
            size=thumbnail_size,
            layout=layout,
        )

    content = PublicationContent(
        media=render.path,
        title=video_title,
        description=description,
        keywords=list(keywords),
        thumbnail=thumb,
        duration=render.duration,
    )
    return MusicVideo(
        audio=audio,
        video=render.path,
        thumbnail=thumb,
        content=content,
        render=render,
    )


def prepare_music_videos(
    songs: PathLike | Sequence[PathLike],
    *,
    images: PathLike | Mapping[str, PathLike] | None = None,
    **kwargs,
) -> list[MusicVideo]:
    """Prepare several songs as one coherent set (same template, same loudness).

    Args:
        songs: One song, a list of songs, or a directory of audio files.
        images: One cover for all of them, or a per-song mapping keyed by the
            song path (or by its filename, or by its stem — whichever you find
            more convenient).
        **kwargs: Everything :func:`prepare_music_video` accepts; applied
            identically to every song, which is what makes the set read as a
            deliberate collection.

    Returns:
        One :class:`MusicVideo` per song, in order.
    """
    paths = _as_song_list(songs)
    return [
        prepare_music_video(song, _image_for(song, images), **kwargs) for song in paths
    ]


def publish_music(
    songs: PathLike | Sequence[PathLike],
    *,
    images: PathLike | Mapping[str, PathLike] | None = None,
    image: PathLike | None = None,
    privacy_status: str | None = None,
    playlist=None,
    category_id: str = CATEGORY_MUSIC,
    prepared: Sequence[MusicVideo] | None = None,
    progress: bool = True,
    service=None,
    **kwargs,
) -> list[dict]:
    """Render ``songs`` as music videos and upload them to YouTube.

    Reuses :func:`yb.youtube.publish_content` unchanged — the music path only
    prepares better assets for it. Videos are published under YouTube's *Music*
    category, and (when ``playlist`` is given) collected into one playlist, so
    an album arrives as an album.

    Args:
        songs: One song, a list of songs, or a directory of audio files.
        images: A cover for all songs, or a per-song mapping.
        image: A single cover (a friendlier alias for the one-song case).
        privacy_status: ``"unlisted"`` (the ``yb`` default), ``"private"``, or
            ``"public"``.
        playlist: Playlist title to collect the set into. ``None`` (the default
            here) publishes without touching a playlist.
        category_id: YouTube category (default: Music).
        prepared: Already-prepared :class:`MusicVideo` objects — skips rendering
            (useful to review the videos before they go up).
        progress: Print upload progress.
        service: An authenticated YouTube service to reuse across the batch.
        **kwargs: Forwarded to :func:`prepare_music_video`.

    Returns:
        One :func:`yb.youtube.publish_content` result dict per song.
    """
    from yb.youtube.publish import publish_content

    videos = (
        list(prepared)
        if prepared is not None
        else prepare_music_videos(
            songs, images=images if images is not None else image, **kwargs
        )
    )

    results = []
    for music_video in videos:
        if progress:
            print(f"Publishing {music_video.content.title!r}...")
        results.append(
            publish_content(
                music_video.content,
                privacy_status=privacy_status,
                playlist=playlist,
                category_id=category_id,
                with_chapters=False,
                attach_caption=False,
                progress=progress,
                service=service,
            )
        )
    return results


@dataclass
class FolderItem:
    """One song's plan within a folder: what to render, and how.

    Attributes:
        audio: The song file.
        image: The cover with the same filename stem, if there is one.
        title: The song title — the audio file's stem.
        visual: The visual assigned to this song by the rotation.
    """

    audio: Path
    image: Path | None
    title: str
    visual: str


def pair_folder(
    folder: PathLike, *, cycle: Sequence[str] = DEFAULT_VISUAL_CYCLE
) -> list[FolderItem]:
    """Plan an album from a folder of ``(song, cover)`` pairs.

    Each audio file is paired with an image of the **same filename stem** (so
    ``Blue Moon.wav`` ↔ ``Blue Moon.jpeg``), the stem is the song title, and
    visuals are handed out by cycling through ``cycle`` in sorted-filename order
    — so a set varies method to method yet stays a coherent release.

    Args:
        folder: Directory holding the audio files and their covers.
        cycle: Visual names to rotate through (defaults to
            :data:`DEFAULT_VISUAL_CYCLE`).

    Returns:
        One :class:`FolderItem` per song, in sorted order. Inspect it before
        publishing, or hand it straight to :func:`publish_folder`.
    """
    folder = Path(folder)
    songs = sorted(p for p in folder.iterdir() if p.suffix.lower() in _AUDIO_SUFFIXES)
    images = {
        p.stem: p
        for p in sorted(folder.iterdir())
        if p.suffix.lower() in _IMAGE_SUFFIXES
    }
    cycle = list(cycle) or list(DEFAULT_VISUAL_CYCLE)
    return [
        FolderItem(
            audio=song,
            image=images.get(song.stem),
            title=_title_from(song),
            visual=cycle[i % len(cycle)],
        )
        for i, song in enumerate(songs)
    ]


def prepare_folder(
    folder: PathLike,
    *,
    cycle: Sequence[str] = DEFAULT_VISUAL_CYCLE,
    limit: int | None = None,
    output_dir: PathLike | None = None,
    **kwargs,
) -> list[MusicVideo]:
    """Render every ``(song, cover)`` pair in ``folder`` — no upload.

    The way to *test the first song before committing the whole album*: call
    with ``limit=1``, review the one video, then :func:`publish_folder` the set.

    Args:
        folder: Directory of songs and covers (see :func:`pair_folder`).
        cycle: Visual rotation.
        limit: Render only the first ``limit`` songs.
        output_dir: Where the videos/thumbnails go (default: alongside each song).
        **kwargs: Forwarded to :func:`prepare_music_video` (e.g. ``normalize``,
            ``size``, ``fps``, ``options``).

    Returns:
        One :class:`MusicVideo` per rendered song.
    """
    items = pair_folder(folder, cycle=cycle)
    if limit is not None:
        items = items[:limit]
    return [
        prepare_music_video(
            item.audio,
            item.image,
            title=item.title,
            visual=item.visual,
            output_dir=output_dir,
            **kwargs,
        )
        for item in items
    ]


def publish_folder(
    folder: PathLike,
    *,
    cycle: Sequence[str] = DEFAULT_VISUAL_CYCLE,
    limit: int | None = None,
    privacy_status: str | None = "unlisted",
    playlist=None,
    prepared: Sequence[MusicVideo] | None = None,
    progress: bool = True,
    **kwargs,
) -> list[dict]:
    """Render every ``(song, cover)`` pair in ``folder`` and upload the album.

    Filename stem = title; covers match by stem; visuals rotate through ``cycle``
    (:data:`DEFAULT_VISUAL_CYCLE` — waves, cqt, spectrum, bars, scope); the teal
    accent and loudness normalization come from the renderer's defaults. One
    authenticated YouTube service is reused across the whole batch.

    Test-first workflow: ``publish_folder(folder, limit=1)`` publishes the first
    song (unlisted) to eyeball on YouTube; once happy, ``publish_folder(folder)``
    does the set.

    Args:
        folder: Directory of songs and covers.
        cycle: Visual rotation.
        limit: Publish only the first ``limit`` songs.
        privacy_status: ``"unlisted"`` (default), ``"private"``, or ``"public"``.
        playlist: Playlist title to collect the album into (``None`` = none).
        prepared: Already-rendered :class:`MusicVideo` objects to upload as-is
            (skip rendering — e.g. the return of :func:`prepare_folder`).
        progress: Print progress.
        **kwargs: Forwarded to :func:`prepare_music_video`.

    Returns:
        One :func:`yb.youtube.publish_content` result dict per song, each with an
        added ``"title"`` and ``"visual"`` for at-a-glance review.
    """
    from yb.youtube.auth import get_service
    from yb.youtube.publish import publish_content

    if prepared is not None:
        videos = list(prepared)
        visuals = [mv.render.visual for mv in videos]
    else:
        items = pair_folder(folder, cycle=cycle)
        if limit is not None:
            items = items[:limit]
        videos, visuals = [], []
        for item in items:
            if progress:
                print(f"Rendering {item.title!r} as {item.visual}...")
            videos.append(
                prepare_music_video(
                    item.audio,
                    item.image,
                    title=item.title,
                    visual=item.visual,
                    **kwargs,
                )
            )
            visuals.append(item.visual)

    service = get_service()  # authenticate once, reuse across the album
    results = []
    for music_video, visual in zip(videos, visuals):
        if progress:
            print(f"Publishing {music_video.content.title!r}...")
        result = publish_content(
            music_video.content,
            privacy_status=privacy_status,
            playlist=playlist,
            category_id=CATEGORY_MUSIC,
            with_chapters=False,
            attach_caption=False,
            progress=progress,
            service=service,
        )
        results.append({**result, "title": music_video.content.title, "visual": visual})
    return results


def _as_song_list(songs: PathLike | Sequence[PathLike]) -> list[Path]:
    """Normalize a song, a directory of songs, or a list of songs into a list."""
    if isinstance(songs, (str, Path)):
        path = Path(songs)
        if path.is_dir():
            return sorted(
                p for p in path.iterdir() if p.suffix.lower() in _AUDIO_SUFFIXES
            )
        return [path]
    return [Path(s) for s in songs]


def _image_for(
    song: Path, images: PathLike | Mapping[str, PathLike] | None
) -> Path | None:
    """The cover for ``song``: a shared one, or its entry in a per-song mapping."""
    if images is None:
        return None
    if isinstance(images, Mapping):
        for key in (str(song), song.name, song.stem):
            if key in images:
                return Path(images[key])
        return None
    return Path(images)


def _title_from(audio: Path) -> str:
    """The song's title: from its tags when readable, else from its filename."""
    tagged = _tag(audio, "title")
    if tagged:
        return tagged
    # "01 - time_to_go home.wav" -> "Time To Go Home"
    stem = re.sub(r"^\d+\s*[-_. ]\s*", "", audio.stem)
    stem = re.sub(r"[_-]+", " ", stem).strip()
    return stem.title() if stem.islower() or stem.isupper() else stem or audio.stem


def _tag(audio: Path, key: str) -> str | None:
    """Read one tag from ``audio``, or ``None`` (mutagen is optional)."""
    try:
        from mutagen import File as MutagenFile
    except ImportError:
        return None
    try:
        tags = MutagenFile(str(audio), easy=True)
        value = tags and tags.get(key)
        return str(value[0]) if value else None
    except Exception:  # an unreadable/absent tag is not an error worth raising
        return None
