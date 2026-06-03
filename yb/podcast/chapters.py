"""Podcast chapter markers: Podlove Simple Chapters (PSC) + MP3 ID3 chapters.

Two standards cover most podcast players:

- **PSC** — an XML sidecar (``<psc:chapters>``) referenced from the RSS feed.
- **ID3 chapters** — ``CHAP``/``CTOC`` frames embedded directly in the MP3, so
  chapters travel with the file (Apple Podcasts, Overcast, etc.).

Both are derived from the same platform-neutral ``mixing.chapters.Chapter`` list.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence
from xml.sax.saxutils import escape

from mixing.chapters import Chapter

PathLike = str | Path


def psc_xml(chapters: Sequence[Chapter]) -> str:
    """Render chapters as a Podlove Simple Chapters (PSC) XML document."""
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<psc:chapters version="1.2" xmlns:psc="http://podlove.org/simple-chapters">',
    ]
    for c in chapters:
        lines.append(f'  <psc:chapter start="{_psc_time(c.start)}" title="{escape(c.title)}"/>')
    lines.append("</psc:chapters>")
    return "\n".join(lines) + "\n"


def write_psc(chapters: Sequence[Chapter], path: PathLike) -> Path:
    """Write a PSC XML sidecar to ``path``."""
    path = Path(path)
    path.write_text(psc_xml(chapters), encoding="utf-8")
    return path


def write_id3_chapters(
    mp3_path: PathLike,
    chapters: Sequence[Chapter],
    *,
    duration: float | None = None,
    toc_id: str = "toc",
) -> Path:
    """Embed ID3v2 chapter frames (``CHAP`` + ``CTOC``) into an MP3 file.

    Args:
        mp3_path: The MP3 to modify in place.
        chapters: Ordered chapter markers.
        duration: Total media duration (s) — used as the last chapter's end.
            Inferred from the file when omitted.
        toc_id: Element id for the table-of-contents frame.

    Returns:
        The path written.

    Raises:
        ImportError: ``mutagen`` is not installed (``pip install 'yb[podcast]'``).
    """
    from mutagen.id3 import ID3, CHAP, CTOC, TIT2, CTOCFlags
    from mutagen.mp3 import MP3

    mp3_path = Path(mp3_path)
    if duration is None:
        duration = MP3(str(mp3_path)).info.length

    try:
        tags = ID3(str(mp3_path))
    except Exception:
        tags = ID3()

    # Drop any prior chapter frames so re-runs are idempotent.
    for key in [k for k in tags.keys() if k.startswith(("CHAP", "CTOC"))]:
        del tags[key]

    starts = [c.start for c in chapters]
    ends = [*starts[1:], float(duration)]
    element_ids = []
    for i, (c, end) in enumerate(zip(chapters, ends)):
        eid = f"chp{i}"
        element_ids.append(eid)
        tags.add(CHAP(
            element_id=eid,
            start_time=int(c.start * 1000),
            end_time=int(end * 1000),
            sub_frames=[TIT2(encoding=3, text=[c.title])],
        ))
    tags.add(CTOC(
        element_id=toc_id,
        flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
        child_element_ids=element_ids,
        sub_frames=[TIT2(encoding=3, text=["Chapters"])],
    ))
    tags.save(str(mp3_path))
    return mp3_path


def _psc_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600 * 1000)
    m, ms = divmod(ms, 60 * 1000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
