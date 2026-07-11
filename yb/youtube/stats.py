"""Read live video metadata & engagement numbers from the YouTube Data API v3.

A read-only companion to :mod:`yb.youtube.api`: fetch a flattened, typed,
human-friendly view of a video's *live* numbers (views, likes, dislikes,
comments, ...) together with content and status details — all in one request —
with optional field selection, named field **groups** (presets like
``"engagement"``), and an ASCII-table rendering for quick terminal reading.

Simple things simple::

    >>> from yb.youtube import video_metadata                       # doctest: +SKIP
    >>> video_metadata("VIDEO_ID", group="engagement")              # doctest: +SKIP
    {'views': 666, 'likes': 11, 'dislikes': 0, 'comments': 0, ...}

Readable table for a terminal::

    >>> print(video_metadata("VIDEO_ID", group="engagement", as_table=True))  # doctest: +SKIP
    field              value
    -----------------  -----
    views                666
    likes                 11
    ...

Pick exact fields and order, or compare several videos at once::

    >>> video_metadata("VIDEO_ID", fields=["title", "views", "likes"])        # doctest: +SKIP
    >>> print(video_metadata(["ID1", "ID2"], group="engagement", as_table=True))  # doctest: +SKIP

Note: ``dislikes`` is only returned by the API to a video's **owner**; for
other people's videos it comes back as ``None``. With no ``group``/``fields`` you
get every available field ("take whatever is there").
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Mapping, Sequence

PathLike = str | Path

#: Parts fetched by default — everything a single ``videos.list`` call needs to
#: populate the flattened fields below.
DEFAULT_PARTS = "snippet,statistics,contentDetails,status"

_ISO8601 = re.compile(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
_NUMISH = re.compile(r"^-?[\d,]+(?:\.\d+)?%?$")


# ---------------------------------------------------------------------------
# Pure helpers (no I/O) — small, single-purpose, module-private.
# ---------------------------------------------------------------------------
def _to_int(value):
    return int(value) if value is not None else None


def _pct(num, den):
    """Percentage ``num``/``den`` rounded to 3 dp, or ``None`` if not computable."""
    if not den or num is None:
        return None
    return round(100 * num / den, 3)


def _iso8601_to_seconds(duration: str | None) -> int | None:
    """Convert an ISO-8601 duration (e.g. ``PT1M51S``) to whole seconds."""
    if not duration:
        return None
    m = _ISO8601.fullmatch(duration)
    if not m:
        return None
    days, hours, minutes, seconds = (int(g) if g else 0 for g in m.groups())
    return ((days * 24 + hours) * 60 + minutes) * 60 + seconds


def _hms(seconds: int | None) -> str | None:
    """Format seconds as ``H:MM:SS`` (or ``M:SS`` when under an hour)."""
    if seconds is None:
        return None
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


_BOOL_STR = {"true": True, "false": False}


def flatten_video(resource: Mapping) -> dict:
    """Flatten a raw ``videos.list`` item into a friendly, typed, ordered dict.

    Pure: pass the dict returned by the API. Missing pieces (from a partial
    ``part=`` request, disabled stats, or an unauthorized dislike count) become
    ``None`` rather than raising, so callers never have to guard the shape.
    """
    sn = resource.get("snippet", {})
    stt = resource.get("statistics", {})
    cd = resource.get("contentDetails", {})
    st = resource.get("status", {})
    vid = resource.get("id")

    views = _to_int(stt.get("viewCount"))
    likes = _to_int(stt.get("likeCount"))
    comments = _to_int(stt.get("commentCount"))
    dur_s = _iso8601_to_seconds(cd.get("duration"))
    tags = sn.get("tags")

    return {
        # identity / basic
        "id": vid,
        "url": f"https://youtu.be/{vid}" if vid else None,
        "title": sn.get("title"),
        "channel_title": sn.get("channelTitle"),
        "channel_id": sn.get("channelId"),
        "published_at": sn.get("publishedAt"),
        "category_id": sn.get("categoryId"),
        "privacy": st.get("privacyStatus"),
        # engagement
        "views": views,
        "likes": likes,
        "dislikes": _to_int(stt.get("dislikeCount")),  # owner-only
        "comments": comments,
        "favorites": _to_int(stt.get("favoriteCount")),
        "like_view_pct": _pct(likes, views),
        "comment_view_pct": _pct(comments, views),
        # content
        "duration": _hms(dur_s),
        "duration_seconds": dur_s,
        "definition": cd.get("definition"),
        "dimension": cd.get("dimension"),
        "has_captions": _BOOL_STR.get(cd.get("caption")),
        "has_custom_thumbnail": cd.get("hasCustomThumbnail"),
        "licensed_content": cd.get("licensedContent"),
        "projection": cd.get("projection"),
        # status / snippet extras
        "upload_status": st.get("uploadStatus"),
        "license": st.get("license"),
        "embeddable": st.get("embeddable"),
        "public_stats_viewable": st.get("publicStatsViewable"),
        "made_for_kids": st.get("madeForKids"),
        "default_language": sn.get("defaultLanguage"),
        "default_audio_language": sn.get("defaultAudioLanguage"),
        "live_broadcast_content": sn.get("liveBroadcastContent"),
        "tags": tags,
        "tag_count": len(tags) if tags else 0,
    }


#: Named presets: a group name -> the ordered fields it selects. ``"engagement"``
#: is the headline one (the live numbers); the rest are common practical cuts.
FIELD_GROUPS: dict[str, list[str]] = {
    "engagement": [
        "views", "likes", "dislikes", "comments", "favorites",
        "like_view_pct", "comment_view_pct",
    ],
    "overview": [
        "title", "url", "privacy", "published_at", "duration",
        "views", "likes", "comments",
    ],
    "content": [
        "duration", "duration_seconds", "definition", "dimension",
        "has_captions", "has_custom_thumbnail", "licensed_content", "projection",
    ],
    "status": [
        "privacy", "upload_status", "made_for_kids", "embeddable",
        "license", "public_stats_viewable",
    ],
    "identity": [
        "id", "url", "title", "channel_title", "channel_id",
        "category_id", "published_at",
    ],
}


def resolve_fields(
    *,
    group: str | None = None,
    fields: Sequence[str] | None = None,
    available: Iterable[str] | None = None,
) -> list[str]:
    """Resolve the ordered field list to show.

    Precedence: explicit ``fields`` > named ``group`` > every ``available``
    field. An unknown ``group`` raises ``KeyError`` naming the valid options.
    """
    if fields is not None:
        return list(fields)
    if group is not None:
        if group not in FIELD_GROUPS:
            raise KeyError(
                f"Unknown field group {group!r}. "
                f"Choose from: {', '.join(sorted(FIELD_GROUPS))}"
            )
        return list(FIELD_GROUPS[group])
    return list(available) if available is not None else []


def select_fields(
    flat: Mapping,
    *,
    group: str | None = None,
    fields: Sequence[str] | None = None,
) -> dict:
    """Return an ordered subset of ``flat`` per ``fields``/``group``."""
    names = resolve_fields(group=group, fields=fields, available=flat.keys())
    return {name: flat.get(name) for name in names}


def _fmt_cell(value) -> str:
    """Human-readable cell text: thousands separators, yes/no, em-dash for None."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.3f}".rstrip("0").rstrip(".")
    if isinstance(value, (list, tuple)):
        return ", ".join(map(str, value))
    return str(value)


def _ascii(grid: Sequence[Sequence[str]], *, header: bool = True) -> str:
    """Render a grid of cells as a padded, column-aligned monospace table."""
    grid = [[str(c) for c in row] for row in grid]
    ncol = len(grid[0])
    widths = [max(len(row[i]) for row in grid) for i in range(ncol)]
    body = grid[1:] if header else grid
    # right-align columns whose body cells are all numeric-looking
    right = [
        bool(body) and all(_NUMISH.match(row[i]) for row in body)
        for i in range(ncol)
    ]

    def fmt(row):
        cells = [
            row[i].rjust(widths[i]) if right[i] else row[i].ljust(widths[i])
            for i in range(ncol)
        ]
        return "  ".join(cells).rstrip()

    lines = [fmt(grid[0])]
    if header:
        lines.append("  ".join("-" * w for w in widths))
    lines.extend(fmt(row) for row in grid[1:])
    return "\n".join(lines)


def render_table(
    data: Mapping | Sequence[Mapping],
    *,
    fields: Sequence[str] | None = None,
) -> str:
    """Render metadata as an ASCII table.

    A single flat dict renders as a two-column ``field | value`` table; a list
    of flat dicts renders one row per video with ``fields`` as columns.
    """
    if isinstance(data, Mapping):
        items = (
            data.items() if fields is None else [(f, data.get(f)) for f in fields]
        )
        rows = [("field", "value"), *((k, _fmt_cell(v)) for k, v in items)]
        return _ascii(rows)
    rows = list(data)
    cols = list(fields) if fields is not None else _union_keys(rows)
    grid = [cols] + [[_fmt_cell(row.get(c)) for c in cols] for row in rows]
    return _ascii(grid)


def _union_keys(dicts: Sequence[Mapping]) -> list[str]:
    """Ordered union of keys across ``dicts`` (first-seen order)."""
    seen: dict[str, None] = {}
    for d in dicts:
        for k in d:
            seen.setdefault(k, None)
    return list(seen)


# ---------------------------------------------------------------------------
# I/O orchestrator.
# ---------------------------------------------------------------------------
def video_metadata(
    video_id: str | Iterable[str],
    *,
    group: str | None = None,
    fields: Sequence[str] | None = None,
    part: str = DEFAULT_PARTS,
    as_table: bool = False,
    service=None,
    **cred_kwargs,
) -> dict | list[dict] | str:
    """Fetch a video's live metadata & engagement numbers.

    Args:
        video_id: A single video id or an iterable of ids (batched, ≤50/call).
        group: Name of a preset field set from :data:`FIELD_GROUPS`
            (e.g. ``"engagement"``). Ignored if ``fields`` is given.
        fields: Explicit ordered field names to keep (overrides ``group``).
            With neither ``group`` nor ``fields`` you get every field.
        part: ``videos.list`` parts to request (default covers all fields).
        as_table: When ``True``, return a ready-to-print ASCII table string
            instead of the dict/list.
        service: An authenticated YouTube service; else built from
            ``cred_kwargs`` (e.g. ``token_file=...``).

    Returns:
        A flat ``dict`` for one id / ``list[dict]`` for many — or an ASCII
        table ``str`` when ``as_table=True``.
    """
    single = isinstance(video_id, str)
    ids = [video_id] if single else list(video_id)
    if not ids:
        raise ValueError("video_id must be a non-empty id or iterable of ids")

    service = service or _service(**cred_kwargs)
    flats = [flatten_video(item) for item in _fetch(ids, part=part, service=service)]

    if as_table:
        cols = resolve_fields(
            group=group, fields=fields,
            available=flats[0].keys() if flats else [],
        )
        if single:
            return render_table(flats[0], fields=cols)
        # prepend an identifier column so rows are distinguishable
        id_col = "title" if any(f.get("title") for f in flats) else "id"
        cols = ([id_col] if id_col not in cols else []) + cols
        return render_table(flats, fields=cols)

    selected = [select_fields(flat, group=group, fields=fields) for flat in flats]
    return selected[0] if single else selected


def _fetch(ids: Sequence[str], *, part: str, service) -> list[dict]:
    """Fetch raw ``videos.list`` items for ``ids`` (batched by the API's 50 max)."""
    items: list[dict] = []
    for start in range(0, len(ids), 50):
        chunk = ids[start:start + 50]
        resp = service.videos().list(part=part, id=",".join(chunk)).execute()
        items.extend(resp.get("items", []))
    return items


def _service(**cred_kwargs):
    from yb.youtube.auth import get_service

    return get_service(**cred_kwargs)
