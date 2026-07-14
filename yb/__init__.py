"""yb — streamline media publishing: prepare once, publish to YouTube or podcast.

Layered by separation of concerns:

- **core (always available):** :mod:`yb.content` — build a platform-neutral
  :class:`~yb.content.PublicationContent` (title, description, keywords,
  chapters, captions, thumbnail) from a media file, delegating transcription,
  chapter detection, and thumbnails to the ``mixing`` package.
- **rendering (needs only ffmpeg):** :mod:`yb.render` — turn audio into a video
  a platform will accept (a cover on a 16:9 canvas, a Ken Burns pan, or an
  audio-reactive visualizer), plus the matching thumbnail.
- **adapters (optional extras):**
  - :mod:`yb.youtube` (``pip install 'yb[youtube]'``) — upload and edit videos.
  - :mod:`yb.music` — publish songs as music videos (renders, then uploads
    through :mod:`yb.youtube`).
  - :mod:`yb.podcast` (``pip install 'yb[podcast]'``) — show notes, chapter
    markers, cover-over-audio video, RSS episode item.
  - :mod:`yb.download` (``pip install 'yb[download]'``) — fetch videos/metadata.

The most common callables are re-exported here for convenience; the ones that
live in optional extras are imported lazily, so ``import yb`` never fails for a
missing extra — the error surfaces only when you actually use that feature.

Examples:
    >>> import yb  # doctest: +SKIP
    >>> r = yb.download_youtube_video("https://youtu.be/PRa9ciOe-us")  # needs yb[download]
    >>> content = yb.prepare_content(r.path, language="English", language_code="en")
    >>> yb.prepare_and_publish(r.path, privacy_status="unlisted")        # needs yb[youtube]
"""

from yb.config import YbConfig, load_config, default_config_file
from yb.content import (
    PublicationContent,
    ContentMetadata,
    prepare_content,
    generate_metadata,
    format_chapter_lines,
)

# Optional-extra callables, resolved lazily on first access so that a missing
# extra (yt-dlp / google libs / mutagen) doesn't break ``import yb``.
_LAZY = {
    "download_youtube_video": "yb.download",
    "youtube_video_info": "yb.download",
    "prepare_and_publish": "yb.youtube",
    "publish_content": "yb.youtube",
    "update_video_fields": "yb.youtube",
    "upsert_caption": "yb.youtube",
    "set_chapters": "yb.youtube",
    "add_video_to_playlist": "yb.youtube",
    "prepare_podcast_episode": "yb.podcast",
    "render_audio_video": "yb.render",
    "list_visuals": "yb.render",
    "register_visual": "yb.render",
    "prepare_music_video": "yb.music",
    "prepare_music_videos": "yb.music",
    "publish_music": "yb.music",
}

__all__ = [
    "PublicationContent",
    "ContentMetadata",
    "prepare_content",
    "generate_metadata",
    "format_chapter_lines",
    "YbConfig",
    "load_config",
    "default_config_file",
    *_LAZY.keys(),
]


def __getattr__(name: str):
    """Lazily import optional-extra callables on first access (PEP 562)."""
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module 'yb' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module), name)


def __dir__():
    return sorted(__all__)
