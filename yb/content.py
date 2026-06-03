"""Target-agnostic publication content: prepare it once, publish anywhere.

A :class:`PublicationContent` bundles everything a publication needs that is
*not* specific to a destination — title, description, keywords, chapters,
languages, and the media/transcript/thumbnail assets. Platform adapters
(``yb.youtube``, ``yb.podcast``) consume it and map it to their own schema.

The heavy lifting (transcription, chapter detection, thumbnail rendering) is
delegated to the ``mixing`` package; the copywriting (title/description/
keywords) is LLM-backed via ``aix`` and pluggable.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from mixing.chapters import Chapter  # lightweight (no moviepy pulled)

PathLike = str | Path


@dataclass
class ContentMetadata:
    """Platform-neutral copy: a title, a description, and keywords."""

    title: str
    description: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class PublicationContent:
    """Everything needed to publish a piece of media, destination-agnostic.

    Attributes:
        media: Path to the audio/video file.
        title: Headline/title.
        description: Long-form description / show notes body.
        keywords: Topical keywords/tags.
        chapters: Ordered chapter markers (``mixing.chapters.Chapter``).
        language: BCP-47 code of the metadata text (e.g. ``"en"``).
        audio_language: BCP-47 code of the spoken audio (e.g. ``"fr"``).
        srt_path: Path to the SRT subtitle/caption file, if any.
        thumbnail: Path to a thumbnail/cover image, if any.
        duration: Media duration in seconds, if known.
    """

    media: Path
    title: str = ""
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    language: str | None = None
    audio_language: str | None = None
    srt_path: Path | None = None
    thumbnail: Path | None = None
    duration: float | None = None

    def description_with_chapters(self) -> str:
        """Description with a chapters block appended (if any chapters)."""
        if not self.chapters:
            return self.description
        block = format_chapter_lines(self.chapters)
        body = self.description.rstrip()
        return f"{body}\n\nChapters:\n{block}" if body else f"Chapters:\n{block}"


def format_chapter_lines(chapters: Sequence[Chapter]) -> str:
    """Render chapters as ``M:SS Title`` lines (the shared text convention).

    Uses ``H:MM:SS`` when any chapter is at or beyond one hour. This is the
    text format both YouTube descriptions and podcast show notes accept.
    """
    use_hours = any(c.start >= 3600 for c in chapters)
    return "\n".join(f"{_fmt_ts(c.start, use_hours)} {c.title}" for c in chapters)


def _fmt_ts(t: float, use_hours: bool) -> str:
    total = int(round(t))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if use_hours:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{h * 60 + m}:{s:02d}"


def prepare_content(
    media: PathLike,
    *,
    language: str = "English",
    language_code: str | None = None,
    audio_language_code: str | None = None,
    brand: str | None = None,
    extra_context: str | None = None,
    transcript: str | None = None,
    with_chapters: bool = True,
    with_thumbnail: bool = False,
    thumbnail_text: str | None = None,
    metadata: ContentMetadata | None = None,
    model: str | None = None,
    transcribe_kwargs: dict | None = None,
    chapters_kwargs: dict | None = None,
) -> PublicationContent:
    """Build a :class:`PublicationContent` for ``media`` (destination-agnostic).

    Ensures a persisted SRT next to the media (transcribing once via
    ``mixing`` if needed), writes LLM metadata, detects chapters (default on,
    auto-skipped for clips too short to host them), and optionally renders a
    thumbnail. Any precomputed pieces (``transcript``, ``metadata``) are reused
    instead of recomputed.

    Args:
        media: Audio or video file.
        language: Human-readable language to write metadata in.
        language_code / audio_language_code: BCP-47 codes for the metadata
            text and the spoken audio.
        brand: Product/brand name to keep verbatim in the copy.
        extra_context: Extra guidance for the copywriter (audience, CTA…).
        transcript: SRT text to use as-is (skips transcription).
        with_chapters: Detect chapters (default ``True``).
        with_thumbnail: Render a thumbnail image (default ``False``).
        thumbnail_text: Overlay text for the thumbnail (defaults to the title).
        metadata: Precomputed :class:`ContentMetadata` to reuse.
        model: LLM model override.
        transcribe_kwargs / chapters_kwargs: Forwarded to the mixing calls.

    Returns:
        A populated :class:`PublicationContent`.
    """
    from mixing.transcript.persist import srt_for_media
    from mixing.chapters import detect_chapters

    media = Path(media)

    if transcript is not None:
        srt_text, srt_path = transcript, media.with_suffix(".srt")
    else:
        srt_text, srt_path = srt_for_media(media, **(transcribe_kwargs or {}))

    if metadata is None:
        metadata = generate_metadata(
            srt_text,
            language=language,
            brand=brand,
            extra_context=extra_context,
            model=model,
        )

    chapters: list[Chapter] = []
    if with_chapters:
        chapters = detect_chapters(srt_text, **(chapters_kwargs or {}))

    thumbnail = None
    if with_thumbnail:
        from mixing.video.thumbnail import make_thumbnail

        thumbnail = make_thumbnail(media, text=thumbnail_text or metadata.title)

    return PublicationContent(
        media=media,
        title=metadata.title,
        description=metadata.description,
        keywords=list(metadata.keywords),
        chapters=chapters,
        language=language_code,
        audio_language=audio_language_code,
        srt_path=Path(srt_path),
        thumbnail=Path(thumbnail) if thumbnail else None,
    )


def generate_metadata(
    transcript: str,
    *,
    language: str = "English",
    brand: str | None = None,
    extra_context: str | None = None,
    model: str | None = None,
) -> ContentMetadata:
    """Generate platform-neutral title/description/keywords from a transcript.

    LLM-backed via ``aix``. Pass a ready :class:`ContentMetadata` to
    :func:`prepare_content` instead if you want to skip generation.

    Raises:
        ImportError: ``aix`` is not importable.
    """
    try:
        from aix import chat
    except ImportError as e:  # pragma: no cover - environment dependent
        raise ImportError(
            "generate_metadata needs the 'aix' package (pip install 'yb[llm]'), "
            "or build ContentMetadata directly."
        ) from e

    brand_line = f"Brand/product (keep verbatim): {brand}\n" if brand else ""
    ctx_line = f"Extra context: {extra_context}\n" if extra_context else ""
    prompt = (
        f"You are writing publication metadata in {language} for the media whose "
        "transcript is given below.\n"
        f"{brand_line}{ctx_line}"
        "Return ONLY a JSON object (no code fences) with keys:\n"
        '  "title": compelling, <= 90 characters, front-loads the benefit; no clickbait.\n'
        '  "description": 2-4 short paragraphs in ' + language + ", natural and "
        "persuasive, ending with a call to action. <= 1500 characters.\n"
        '  "keywords": array of 12-15 lowercase keyword strings (no "#").\n\n'
        "TRANSCRIPT:\n" + transcript.strip()
    )
    raw = chat(prompt, model=model, temperature=0.5)
    data = _parse_json_object(raw)
    return ContentMetadata(
        title=str(data.get("title", "")).strip(),
        description=str(data.get("description", "")).strip(),
        keywords=[str(k) for k in (data.get("keywords") or [])],
    )


def _parse_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    if not text.startswith("{"):
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            text = m[0]
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("Metadata response was not a JSON object.")
    return obj
