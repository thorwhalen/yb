"""YouTube video metadata ↔ API snippet mapping.

Maps the platform-neutral :class:`yb.content.PublicationContent` onto a
YouTube ``videos.insert`` body, applying YouTube's field limits (title <= 100
chars, description <= 5000, tags combined <= 500) and embedding the chapters
block into the description (YouTube renders chapters from description
timestamps when the first is ``0:00``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from yb.content import PublicationContent, format_chapter_lines

#: A useful subset of YouTube video category ids.
CATEGORY_SCIENCE_TECH = "28"
CATEGORY_EDUCATION = "27"
CATEGORY_PEOPLE_BLOGS = "22"
CATEGORY_ENTERTAINMENT = "24"

_TITLE_MAX = 100
_DESC_MAX = 5000
_TAGS_TOTAL_MAX = 500


@dataclass
class VideoMetadata:
    """YouTube-specific video metadata.

    Attributes:
        title: Title (<= 100 chars).
        description: Description (<= 5000 chars), chapters already embedded.
        tags: Keyword tags (combined length kept under 500 chars).
        category_id: YouTube category id (default Science & Technology).
        default_language: BCP-47 language of the metadata text.
        default_audio_language: BCP-47 language of the audio.
    """

    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    category_id: str = CATEGORY_SCIENCE_TECH
    default_language: str | None = None
    default_audio_language: str | None = None

    def __post_init__(self):
        self.title = self.title.strip()[:_TITLE_MAX]
        self.description = self.description.strip()[:_DESC_MAX]
        self.tags = _cap_tags(self.tags, _TAGS_TOTAL_MAX)

    @classmethod
    def from_content(
        cls,
        content: PublicationContent,
        *,
        category_id: str = CATEGORY_SCIENCE_TECH,
        with_chapters: bool = True,
    ) -> "VideoMetadata":
        """Build YouTube metadata from a platform-neutral content bundle.

        Embeds the chapters block into the description (when present and
        ``with_chapters``), so YouTube renders interactive chapters.
        """
        description = content.description
        if with_chapters and content.chapters:
            block = format_chapter_lines(content.chapters)
            body = description.rstrip()
            description = (
                f"{body}\n\nChapters:\n{block}" if body else f"Chapters:\n{block}"
            )
        return cls(
            title=content.title,
            description=description,
            tags=list(content.keywords),
            category_id=category_id,
            default_language=content.language,
            default_audio_language=content.audio_language,
        )

    def insert_body(self, *, privacy_status: str = "unlisted") -> dict:
        """Build the ``videos.insert`` body (snippet + status)."""
        return {
            "snippet": self._snippet(),
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

    def update_snippet(self) -> dict:
        """Build the snippet for ``videos.update`` (categoryId is required)."""
        return self._snippet()

    def _snippet(self) -> dict:
        snippet: dict = {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "categoryId": self.category_id,
        }
        if self.default_language:
            snippet["defaultLanguage"] = self.default_language
        if self.default_audio_language:
            snippet["defaultAudioLanguage"] = self.default_audio_language
        return snippet


def _cap_tags(tags: Sequence[str], total_max: int) -> list[str]:
    """Trim a tag list so the comma-joined length stays under ``total_max``."""
    out: list[str] = []
    used = 0
    for t in tags:
        t = t.strip()
        if not t:
            continue
        add = len(t) + (1 if out else 0)
        if used + add > total_max:
            break
        out.append(t)
        used += add
    return out
