"""Prepare and publish songs as YouTube music videos.

The publication-facing facade over :mod:`yb.render`: a song (and usually a
cover) becomes a video, a thumbnail, and a
:class:`~yb.content.PublicationContent` — which the existing
:mod:`yb.youtube` machinery uploads exactly as it uploads anything else.

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
from yb.render.canvas import (
    DEFAULT_SIZE,
    THUMBNAIL_SIZE,
    CoverLayout,
    TitleStyle,
    thumbnail_image,
)
from yb.render.ffmpeg import Loudness, PathLike
from yb.render.video import DEFAULT_FPS, RenderResult, render_audio_video
from yb.render.visuals import Visual
from yb.youtube.metadata import CATEGORY_MUSIC

_AUDIO_SUFFIXES = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".aiff"}


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
            (see :mod:`yb.render.visuals`).
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

    videos = list(prepared) if prepared is not None else prepare_music_videos(
        songs, images=images if images is not None else image, **kwargs
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
