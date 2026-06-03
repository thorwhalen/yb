"""Podcast show notes — the human-readable episode description block.

Same content as a YouTube description, formatted for podcast directories:
title, body, then a chapters list (``M:SS Title``) when chapters are present.
"""

from __future__ import annotations

from yb.content import PublicationContent, format_chapter_lines


def format_show_notes(content: PublicationContent, *, include_chapters: bool = True) -> str:
    """Render show notes (title + description + optional chapters) as text."""
    parts = [content.title.strip(), "", content.description.strip()]
    if include_chapters and content.chapters:
        parts += ["", "Chapters:", format_chapter_lines(content.chapters)]
    return "\n".join(parts).strip() + "\n"
