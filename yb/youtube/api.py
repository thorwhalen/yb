"""YouTube video operations: get, upload, update metadata, thumbnail, chapters.

These wrap the YouTube Data API v3 ``videos``/``thumbnails`` resources for both
creating videos and *editing already-published ones* (titles, descriptions,
tags, languages, and chapter blocks in the description).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from mixing.chapters import Chapter
from yb.content import format_chapter_lines

PathLike = str | Path

_CHAPTERS_HEADER = "Chapters:"


def get_video(video_id: str, *, part: str = "snippet,status", service=None, **cred_kwargs) -> dict:
    """Fetch a video resource (raises ``KeyError`` if not found/visible)."""
    service = service or _service(**cred_kwargs)
    items = service.videos().list(part=part, id=video_id).execute().get("items", [])
    if not items:
        raise KeyError(f"Video not found or not accessible: {video_id}")
    return items[0]


def upload_video(
    video_path: PathLike,
    body: dict,
    *,
    service=None,
    chunksize: int = 8 * 1024 * 1024,
    progress: bool = True,
    **cred_kwargs,
) -> dict:
    """Resumably upload a video with the given ``videos.insert`` ``body``.

    Returns the created video resource (includes ``id``).
    """
    from googleapiclient.http import MediaFileUpload

    service = service or _service(**cred_kwargs)
    media = MediaFileUpload(str(video_path), chunksize=chunksize, resumable=True, mimetype="video/*")
    request = service.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if progress and status:
            print(f"  upload {int(status.progress() * 100)}%")
    return response


def update_video(video_id: str, snippet: dict, *, service=None, **cred_kwargs) -> dict:
    """Update a video's snippet (``videos.update``). ``categoryId`` is required."""
    service = service or _service(**cred_kwargs)
    body = {"id": video_id, "snippet": snippet}
    return service.videos().update(part="snippet", body=body).execute()


def update_video_fields(
    video_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    tags: Sequence[str] | None = None,
    category_id: str | None = None,
    default_language: str | None = None,
    default_audio_language: str | None = None,
    service=None,
    **cred_kwargs,
) -> dict:
    """Patch selected snippet fields, preserving the rest.

    Fetches the current snippet, overlays the provided fields, and updates.
    ``categoryId`` must be present (kept from the existing snippet if not given).
    """
    service = service or _service(**cred_kwargs)
    snippet = dict(get_video(video_id, part="snippet", service=service)["snippet"])
    if title is not None:
        snippet["title"] = title
    if description is not None:
        snippet["description"] = description
    if tags is not None:
        snippet["tags"] = list(tags)
    if category_id is not None:
        snippet["categoryId"] = category_id
    if default_language is not None:
        snippet["defaultLanguage"] = default_language
    if default_audio_language is not None:
        snippet["defaultAudioLanguage"] = default_audio_language
    # videos.update replaces the snippet wholesale → keep only writable keys.
    writable = {
        k: snippet[k] for k in (
            "title", "description", "tags", "categoryId",
            "defaultLanguage", "defaultAudioLanguage",
        ) if k in snippet
    }
    return update_video(video_id, writable, service=service)


def set_thumbnail(video_id: str, image_path: PathLike, *, service=None, **cred_kwargs) -> dict:
    """Set a custom thumbnail (``thumbnails.set``)."""
    from googleapiclient.http import MediaFileUpload

    service = service or _service(**cred_kwargs)
    media = MediaFileUpload(str(image_path), mimetype="image/jpeg", resumable=False)
    return service.thumbnails().set(videoId=video_id, media_body=media).execute()


def set_chapters(
    video_id: str,
    chapters: Sequence[Chapter],
    *,
    header: str = _CHAPTERS_HEADER,
    service=None,
    **cred_kwargs,
) -> dict:
    """Insert/replace a chapters block in the video's description.

    Strips any prior block under ``header`` and appends the new one. YouTube
    renders interactive chapters when the first timestamp is ``0:00``.
    """
    service = service or _service(**cred_kwargs)
    snippet = get_video(video_id, part="snippet", service=service)["snippet"]
    new_desc = _replace_chapters_block(snippet.get("description", ""), chapters, header)
    return update_video_fields(video_id, description=new_desc, service=service)


def _replace_chapters_block(description: str, chapters: Sequence[Chapter], header: str) -> str:
    """Return ``description`` with its chapters block replaced (or appended)."""
    # Remove an existing "<header> ... " block (header line + following ts lines).
    pattern = re.compile(
        rf"\n*{re.escape(header)}\n(?:\s*\d{{1,2}}(?::\d{{2}}){{1,2}}\s+.*\n?)+",
        re.MULTILINE,
    )
    base = pattern.sub("", description).rstrip()
    if not chapters:
        return base
    block = format_chapter_lines(chapters)
    return f"{base}\n\n{header}\n{block}" if base else f"{header}\n{block}"


def _service(**cred_kwargs):
    from yb.youtube.auth import get_service

    return get_service(**cred_kwargs)
