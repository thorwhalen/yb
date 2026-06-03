"""Caption (subtitle) tracks on YouTube videos: list, insert, update, upsert.

Lets you attach an SRT/VTT track at upload time *and* manage tracks on
already-published videos — e.g. replace a hand-edited subtitle file, or add a
track in a new language. ``upsert_caption`` is the convenient default: it
updates an existing same-language track if present, else inserts a new one.

Note: YouTube auto-generates ASR tracks of its own (``trackKind="asr"``);
these helpers operate on uploaded ``"standard"`` tracks and ignore ASR.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PathLike = str | Path


@dataclass
class CaptionTrack:
    """A caption track to attach to a video.

    Attributes:
        path: Path to an ``.srt`` (or ``.vtt``) file.
        language: BCP-47 language code, e.g. ``"en"`` or ``"fr"``.
        name: Track name shown in the YouTube UI (e.g. ``"English"``).
        is_draft: When ``True``, uploaded but not published to viewers.
    """

    path: PathLike
    language: str
    name: str = ""
    is_draft: bool = False


def list_captions(video_id: str, *, service=None, **cred_kwargs) -> list[dict]:
    """List caption tracks on a video (each item's snippet has language/name/trackKind/status)."""
    service = service or _service(**cred_kwargs)
    return service.captions().list(part="snippet", videoId=video_id).execute().get("items", [])


def insert_caption(
    video_id: str,
    path: PathLike,
    *,
    language: str,
    name: str = "",
    is_draft: bool = False,
    service=None,
    **cred_kwargs,
) -> dict:
    """Insert a new caption track (``captions.insert``)."""
    from googleapiclient.http import MediaFileUpload

    service = service or _service(**cred_kwargs)
    body = {"snippet": {
        "videoId": video_id, "language": language, "name": name, "isDraft": is_draft,
    }}
    media = MediaFileUpload(str(path), mimetype="application/octet-stream", resumable=False)
    return service.captions().insert(part="snippet", body=body, media_body=media).execute()


def update_caption(
    caption_id: str,
    path: PathLike,
    *,
    is_draft: bool | None = None,
    service=None,
    **cred_kwargs,
) -> dict:
    """Replace the content of an existing caption track (``captions.update``)."""
    from googleapiclient.http import MediaFileUpload

    service = service or _service(**cred_kwargs)
    body: dict = {"id": caption_id}
    if is_draft is not None:
        body["snippet"] = {"isDraft": is_draft}
    part = "snippet" if "snippet" in body else "id"
    media = MediaFileUpload(str(path), mimetype="application/octet-stream", resumable=False)
    return service.captions().update(part=part, body=body, media_body=media).execute()


def upsert_caption(
    video_id: str,
    track: "CaptionTrack | PathLike",
    *,
    language: str | None = None,
    name: str = "",
    is_draft: bool = False,
    replace: bool = True,
    service=None,
    **cred_kwargs,
) -> dict:
    """Insert a caption track, or update the existing same-language one.

    Args:
        video_id: Target video.
        track: A :class:`CaptionTrack`, or a path (then ``language`` required).
        replace: When an uploaded track in the same language exists, update it
            (``True``, default) rather than inserting a duplicate.

    Returns:
        The inserted/updated caption resource.
    """
    if isinstance(track, CaptionTrack):
        path, language, name, is_draft = track.path, track.language, track.name, track.is_draft
    else:
        path = track
        if language is None:
            raise ValueError("language is required when track is a path.")

    service = service or _service(**cred_kwargs)
    if replace:
        for item in list_captions(video_id, service=service):
            sn = item["snippet"]
            if sn.get("trackKind") == "standard" and sn.get("language") == language:
                return update_caption(item["id"], path, service=service)
    return insert_caption(
        video_id, path, language=language, name=name, is_draft=is_draft, service=service
    )


def download_caption(
    caption_id: str, *, tfmt: str = "srt", service=None, **cred_kwargs
) -> bytes:
    """Download a caption track's content (``captions.download``), default SRT."""
    service = service or _service(**cred_kwargs)
    return service.captions().download(id=caption_id, tfmt=tfmt).execute()


def delete_caption(caption_id: str, *, service=None, **cred_kwargs) -> None:
    """Delete a caption track (``captions.delete``)."""
    service = service or _service(**cred_kwargs)
    service.captions().delete(id=caption_id).execute()


def _service(**cred_kwargs):
    from yb.youtube.auth import get_service

    return get_service(**cred_kwargs)
