"""Assemble a publishable podcast episode from a media file.

Produces the per-episode asset bundle in an output directory: an MP3 (with
ID3 chapters embedded), show-notes text, a PSC chapter sidecar, a chapters
JSON, and optionally a cover-over-audio video for video platforms. Delivery to
a host/Spotify is via RSS (:mod:`yb.podcast.feed`) — this prepares the assets
and a ready-to-use :class:`yb.podcast.feed.EpisodeFeedItem` stub.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from yb.content import PublicationContent, prepare_content
from yb.podcast.shownotes import format_show_notes
from yb.podcast.chapters import write_psc, write_id3_chapters

PathLike = str | Path


@dataclass
class PodcastEpisode:
    """Paths to the generated episode assets."""

    audio: Path
    show_notes: Path
    chapters_psc: Path | None = None
    chapters_json: Path | None = None
    cover_video: Path | None = None
    content: PublicationContent | None = None
    extras: dict = field(default_factory=dict)


def prepare_podcast_episode(
    media: PathLike,
    output_dir: PathLike,
    *,
    content: PublicationContent | None = None,
    audio: PathLike | None = None,
    cover_image: PathLike | None = None,
    make_cover_video: bool = False,
    ken_burns: bool = False,
    embed_chapters: bool = True,
    language: str = "English",
    brand: str | None = None,
    extra_context: str | None = None,
    audio_bitrate: str = "192k",
) -> PodcastEpisode:
    """Build a podcast episode bundle from ``media`` into ``output_dir``.

    Args:
        media: Source audio or video.
        output_dir: Directory to write the episode assets into.
        content: Precomputed :class:`PublicationContent`; built via
            :func:`yb.content.prepare_content` when omitted.
        audio: Explicit episode audio. When omitted, ``media`` is used if it is
            audio, else its audio track is extracted to MP3.
        cover_image: Cover art (required for ``make_cover_video``).
        make_cover_video: Also render a cover-over-audio mp4 (e.g. for YouTube).
        ken_burns: Apply a Ken Burns pan/zoom to the cover video.
        embed_chapters: Embed ID3 chapter frames into the episode MP3.
        language / brand / extra_context: Forwarded to ``prepare_content``.
        audio_bitrate: Bitrate for extracted MP3 audio.

    Returns:
        A :class:`PodcastEpisode` with the asset paths.
    """
    media = Path(media)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if content is None:
        content = prepare_content(
            media,
            language=language,
            brand=brand,
            extra_context=extra_context,
        )

    # Resolve / produce the episode MP3.
    if audio is not None:
        episode_audio = _copy_into(Path(audio), out)
    elif media.suffix.lower() in {
        ".mp3",
        ".m4a",
        ".aac",
        ".wav",
        ".flac",
        ".ogg",
        ".opus",
    }:
        episode_audio = _copy_into(
            media, out, to_mp3=media.suffix.lower() != ".mp3", bitrate=audio_bitrate
        )
    else:
        episode_audio = _extract_audio(
            media, out / f"{media.stem}.mp3", bitrate=audio_bitrate
        )

    # Show notes.
    show_notes = out / f"{media.stem}.shownotes.txt"
    show_notes.write_text(format_show_notes(content), encoding="utf-8")

    chapters_psc = chapters_json = None
    if content.chapters:
        chapters_psc = write_psc(content.chapters, out / f"{media.stem}.psc.xml")
        chapters_json = out / f"{media.stem}.chapters.json"
        chapters_json.write_text(
            json.dumps(
                [{"start": c.start, "title": c.title} for c in content.chapters],
                indent=2,
            ),
            encoding="utf-8",
        )
        if embed_chapters and episode_audio.suffix.lower() == ".mp3":
            write_id3_chapters(episode_audio, content.chapters)

    cover_video = None
    if make_cover_video:
        if not cover_image:
            raise ValueError("make_cover_video=True requires cover_image=.")
        from yb.podcast.cover import cover_video as _cover_video

        cover_video = _cover_video(
            episode_audio,
            cover_image,
            ken_burns=ken_burns,
            saveas=out / f"{media.stem}.cover.mp4",
        )

    return PodcastEpisode(
        audio=episode_audio,
        show_notes=show_notes,
        chapters_psc=chapters_psc,
        chapters_json=chapters_json,
        cover_video=cover_video,
        content=content,
    )


def _copy_into(
    src: Path, out_dir: Path, *, to_mp3: bool = False, bitrate: str = "192k"
) -> Path:
    if to_mp3:
        return _extract_audio(src, out_dir / f"{src.stem}.mp3", bitrate=bitrate)
    dest = out_dir / src.name
    if src.resolve() != dest.resolve():
        dest.write_bytes(src.read_bytes())
    return dest


def _extract_audio(src: Path, dest: Path, *, bitrate: str = "192k") -> Path:
    """Extract a podcast-quality (stereo, 44.1k) MP3 from any media file."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-b:a",
            bitrate,
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    return dest
