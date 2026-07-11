"""High-level YouTube publishing: prepare → upload → captions → thumbnail.

Two entry points:
    - :func:`publish_content` — given a prepared
      :class:`yb.content.PublicationContent`, upload it with captions,
      thumbnail, and chapters (in the description).
    - :func:`prepare_and_publish` — the one-call path: transcribe/derive
      metadata/detect chapters (via :func:`yb.content.prepare_content`) and
      upload, all from a media path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from yb.config import YbConfig, load_config
from yb.content import PublicationContent, prepare_content
from yb.youtube.auth import get_service
from yb.youtube.metadata import VideoMetadata, CATEGORY_SCIENCE_TECH
from yb.youtube.api import upload_video, set_thumbnail
from yb.youtube.captions import CaptionTrack, upsert_caption
from yb.youtube.playlists import add_video_to_playlist

PathLike = str | Path

#: Sentinel marking "argument not given — fall back to the config default".
#: Distinguishes an unset playlist (use config) from an explicit ``None``
#: (publish without adding to any playlist).
_USE_CONFIG = object()


def _maybe_add_to_playlist(
    video_id: str, playlist, cfg: YbConfig, *, service, progress: bool
) -> dict | None:
    """Add ``video_id`` to ``playlist`` (a title, or the config default)."""
    title = cfg.playlist if playlist is _USE_CONFIG else playlist
    if not title:
        return None
    if progress:
        print(f"  adding to playlist: {title!r}")
    return add_video_to_playlist(
        video_id,
        title,
        create=cfg.create_playlist_if_missing,
        privacy_status=cfg.playlist_privacy_status,
        service=service,
    )


def publish_content(
    content: PublicationContent,
    *,
    privacy_status: str | None = None,
    playlist=_USE_CONFIG,
    category_id: str = CATEGORY_SCIENCE_TECH,
    with_chapters: bool = True,
    attach_caption: bool = True,
    set_thumb: bool = True,
    config: YbConfig | None = None,
    client_secrets_file: PathLike | None = None,
    token_file: PathLike | None = None,
    progress: bool = True,
    service=None,
) -> dict:
    """Upload a prepared :class:`PublicationContent` to YouTube.

    Maps the content to a YouTube snippet (chapters embedded in the
    description when present), uploads, attaches the SRT caption track
    (language = ``content.audio_language`` or ``content.language``) and the
    thumbnail when available, and adds the video to the configured playlist.

    ``privacy_status`` and ``playlist`` default to your ``yb`` config (see
    :mod:`yb.config`): unset means "use the config value", so privacy falls back
    to ``unlisted`` and the video joins your configured playlist. Pass
    ``playlist=None`` to skip the playlist for one call, or ``playlist="Name"``
    to override the target.

    Returns:
        ``{"video_id", "url", "studio_url", "privacy_status", "captions",
        "thumbnail", "playlist"}``. ``privacy_status`` reflects what YouTube
        actually set (an unaudited project may force ``"private"``); ``playlist``
        is the :func:`~yb.youtube.playlists.add_video_to_playlist` result or
        ``None``.
    """
    cfg = config or load_config(privacy_status=privacy_status)
    privacy_status = cfg.privacy_status
    service = service or get_service(
        client_secrets_file=client_secrets_file, token_file=token_file
    )
    meta = VideoMetadata.from_content(
        content, category_id=category_id, with_chapters=with_chapters
    )
    body = meta.insert_body(privacy_status=privacy_status)
    if progress:
        print(f"Uploading {content.media.name!r} as {privacy_status}...")
    resp = upload_video(content.media, body, service=service, progress=progress)
    video_id = resp["id"]
    actual_privacy = resp.get("status", {}).get("privacyStatus", privacy_status)

    captions: list[str] = []
    cap_lang = content.audio_language or content.language
    if (
        attach_caption
        and content.srt_path
        and Path(content.srt_path).exists()
        and cap_lang
    ):
        if progress:
            print(f"  attaching caption: {cap_lang}")
        upsert_caption(
            video_id,
            content.srt_path,
            language=cap_lang,
            name=_lang_name(cap_lang),
            service=service,
        )
        captions.append(cap_lang)

    thumb_set = False
    if set_thumb and content.thumbnail and Path(content.thumbnail).exists():
        if progress:
            print("  setting thumbnail")
        set_thumbnail(video_id, content.thumbnail, service=service)
        thumb_set = True

    playlist_result = _maybe_add_to_playlist(
        video_id, playlist, cfg, service=service, progress=progress
    )
    return _result(video_id, actual_privacy, captions, thumb_set, playlist_result)


def prepare_and_publish(
    media: PathLike,
    *,
    language: str = "English",
    language_code: str | None = None,
    audio_language_code: str | None = None,
    brand: str | None = None,
    extra_context: str | None = None,
    with_chapters: bool = True,
    with_thumbnail: bool = True,
    privacy_status: str | None = None,
    playlist=_USE_CONFIG,
    category_id: str = CATEGORY_SCIENCE_TECH,
    config: YbConfig | None = None,
    client_secrets_file: PathLike | None = None,
    token_file: PathLike | None = None,
    progress: bool = True,
) -> dict:
    """One call: prepare publication content from ``media`` and upload it.

    Transcribes (persisting the SRT next to the media) if needed, writes
    LLM metadata, detects chapters, renders a thumbnail, then uploads with
    captions + thumbnail + chapters and adds the video to the configured
    playlist. ``privacy_status`` and ``playlist`` default to your ``yb`` config
    (see :func:`publish_content`).
    """
    content = prepare_content(
        media,
        language=language,
        language_code=language_code,
        audio_language_code=audio_language_code,
        brand=brand,
        extra_context=extra_context,
        with_chapters=with_chapters,
        with_thumbnail=with_thumbnail,
    )
    return publish_content(
        content,
        privacy_status=privacy_status,
        playlist=playlist,
        category_id=category_id,
        with_chapters=with_chapters,
        config=config,
        client_secrets_file=client_secrets_file,
        token_file=token_file,
        progress=progress,
    )


def publish_video(
    video_path: PathLike,
    metadata: VideoMetadata,
    *,
    privacy_status: str | None = None,
    playlist=_USE_CONFIG,
    captions: Sequence[CaptionTrack] | None = None,
    thumbnail: PathLike | None = None,
    config: YbConfig | None = None,
    client_secrets_file: PathLike | None = None,
    token_file: PathLike | None = None,
    progress: bool = True,
    service=None,
) -> dict:
    """Lower-level upload: explicit :class:`VideoMetadata` + caption tracks.

    ``privacy_status`` and ``playlist`` default to your ``yb`` config (see
    :func:`publish_content`).
    """
    cfg = config or load_config(privacy_status=privacy_status)
    privacy_status = cfg.privacy_status
    service = service or get_service(
        client_secrets_file=client_secrets_file, token_file=token_file
    )
    body = metadata.insert_body(privacy_status=privacy_status)
    if progress:
        print(f"Uploading {Path(video_path).name!r} as {privacy_status}...")
    resp = upload_video(video_path, body, service=service, progress=progress)
    video_id = resp["id"]
    actual_privacy = resp.get("status", {}).get("privacyStatus", privacy_status)

    attached: list[str] = []
    for cap in captions or []:
        if progress:
            print(f"  attaching caption: {cap.name or cap.language}")
        upsert_caption(video_id, cap, service=service)
        attached.append(cap.language)

    thumb_set = False
    if thumbnail and Path(thumbnail).exists():
        set_thumbnail(video_id, thumbnail, service=service)
        thumb_set = True

    playlist_result = _maybe_add_to_playlist(
        video_id, playlist, cfg, service=service, progress=progress
    )
    return _result(video_id, actual_privacy, attached, thumb_set, playlist_result)


def _result(video_id, privacy, captions, thumb, playlist=None) -> dict:
    return {
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "studio_url": f"https://studio.youtube.com/video/{video_id}/edit",
        "privacy_status": privacy,
        "captions": captions,
        "thumbnail": thumb,
        "playlist": playlist,
    }


def _lang_name(code: str) -> str:
    return {
        "en": "English",
        "fr": "Français",
        "es": "Español",
        "de": "Deutsch",
        "it": "Italiano",
        "pt": "Português",
        "ja": "日本語",
        "zh": "中文",
    }.get(code, code)
