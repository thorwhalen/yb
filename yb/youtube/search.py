"""Search YouTube for videos, with engagement numbers to rank them by.

A read-only companion to :mod:`yb.youtube.stats`: that module tells you about a
video you already know; this one finds the videos.

Simple things simple::

    >>> from yb.youtube import search_videos                        # doctest: +SKIP
    >>> for v in search_videos("prime factorisation", max_results=3):  # doctest: +SKIP
    ...     print(v["views"], v["title"])

Two backends, because the obvious one is not always available:

``"api"``
    The official Data API ``search.list``. Costs 100 quota units per call out of
    a default 10 000/day, so roughly 100 searches. Needs ``GOOGLE_API_KEY`` *and*
    YouTube Data API v3 enabled on that key's Cloud project.

``"scrape"``
    Reads the public results page and pulls the same public fields out of the
    ``ytInitialData`` blob the page ships to render itself. No key, no quota. It
    depends on a page layout Google can change, so it is the fallback, not the
    default — and it is for occasional personal use, not bulk collection.

``backend="auto"`` (the default) uses the API when it can and falls back
otherwise, telling you which it used in each result's ``source`` field, so a
silently degraded search is never mistaken for a good one.

Search results carry no engagement numbers on either backend. Pass
``with_stats=True`` to fill in ``views``/``likes``/``comments`` — one extra
batched call per 50 videos on the API backend (1 quota unit), or one page fetch
per video when scraping.

**What each backend can actually tell you about engagement** (measured, not
assumed): the API gives views, likes and comments. The scrape gives **views
only** -- YouTube no longer ships the like count in the watch page HTML for a
signed-out request, so ``likes`` comes back ``None`` there rather than wrong.
:func:`rank_by_engagement` degrades to ranking on reach alone when likes are
missing; enabling the Data API is what makes approval-weighted ranking possible.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Iterable, Iterator

#: Where a video lives, and the thumbnail YouTube always serves for it.
WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
THUMBNAIL_URL = "https://i.ytimg.com/vi/{video_id}/{quality}.jpg"

#: Thumbnail sizes YouTube serves for every video without an API call.
THUMBNAIL_QUALITIES = ("default", "mqdefault", "hqdefault", "sddefault", "maxresdefault")

DEFAULT_THUMBNAIL_QUALITY = "mqdefault"
DEFAULT_MAX_RESULTS = 10
_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


def thumbnail_url(video_id: str, *, quality: str = DEFAULT_THUMBNAIL_QUALITY) -> str:
    """Thumbnail URL for a video. Always available, no API call, no key."""
    if quality not in THUMBNAIL_QUALITIES:
        raise ValueError(f"quality must be one of {THUMBNAIL_QUALITIES}, got {quality!r}")
    return THUMBNAIL_URL.format(video_id=video_id, quality=quality)


def watch_url(video_id: str) -> str:
    return WATCH_URL.format(video_id=video_id)


def _get(url: str, *, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def _api_key(explicit: str = None) -> str | None:
    return explicit or os.environ.get("GOOGLE_API_KEY") or os.environ.get("YOUTUBE_API_KEY")


def api_available(*, api_key: str = None) -> bool:
    """Whether the Data API can actually be called with the key we have.

    A key that exists is not a key that works: the API has to be enabled on its
    Cloud project too, and that failure is a 403 at call time rather than
    anything visible up front.
    """
    key = _api_key(api_key)
    if not key:
        return False
    url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(
        {"part": "id", "id": "dQw4w9WgXcQ", "key": key}
    )
    try:
        _get(url, timeout=15)
        return True
    except Exception:
        return False


def _record(video_id: str, *, title: str, channel: str, source: str, **extra) -> dict:
    return {
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "url": watch_url(video_id),
        "thumbnail": thumbnail_url(video_id),
        "source": source,
        **extra,
    }


def _search_api(query, *, max_results, api_key, language, region, **params) -> list:
    key = _api_key(api_key)
    if not key:
        raise RuntimeError("no API key: set GOOGLE_API_KEY or pass api_key=")

    collected: list = []
    page_token = None
    while len(collected) < max_results:
        request_params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(50, max_results - len(collected)),
            "key": key,
            **params,
        }
        if language:
            request_params["relevanceLanguage"] = language
        if region:
            request_params["regionCode"] = region
        if page_token:
            request_params["pageToken"] = page_token

        url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(request_params)
        payload = json.loads(_get(url))
        for item in payload.get("items", []):
            snippet = item["snippet"]
            collected.append(
                _record(
                    item["id"]["videoId"],
                    title=snippet["title"],
                    channel=snippet.get("channelTitle", ""),
                    source="api",
                    published=snippet.get("publishedAt"),
                )
            )
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return collected[:max_results]


def _walk(node) -> Iterator[dict]:
    """Every dict in an arbitrarily nested JSON structure."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _text(node) -> str:
    if not isinstance(node, dict):
        return ""
    if "simpleText" in node:
        return node["simpleText"]
    return "".join(run.get("text", "") for run in node.get("runs", []))


def _initial_data(html: str) -> dict:
    match = re.search(r"ytInitialData\s*=\s*(\{.*?\});", html, re.S)
    if not match:
        raise RuntimeError("could not find ytInitialData — the page layout changed")
    return json.loads(match.group(1))


def _search_scrape(query, *, max_results, language, region, **_) -> list:
    params = {"search_query": query, "sp": "EgIQAQ%3D%3D"}  # sp = filter to videos
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode(params)
    if language or region:
        url += f"&hl={language or 'en'}&gl={region or 'US'}"

    data = _initial_data(_get(url))
    seen, out = set(), []
    for node in _walk(data):
        renderer = node.get("videoRenderer")
        if not isinstance(renderer, dict):
            continue
        video_id = renderer.get("videoId")
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        out.append(
            _record(
                video_id,
                title=_text(renderer.get("title")),
                channel=_text((renderer.get("ownerText") or {})),
                source="scrape",
                length=_text(renderer.get("lengthText")) or None,
            )
        )
        if len(out) >= max_results:
            break
    return out


def search_videos(
    query: str,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    backend: str = "auto",
    with_stats: bool = False,
    api_key: str = None,
    language: str = None,
    region: str = None,
    **params,
) -> list:
    """Search YouTube and return a list of video records.

    ``language``/``region`` bias results (``"en"``, ``"GB"``) rather than filter
    them — YouTube offers no hard language filter. Check what comes back if the
    language matters; a title can be auto-translated by the interface, which
    makes an English video look like a local one.
    """
    if backend not in ("auto", "api", "scrape"):
        raise ValueError(f"backend must be auto/api/scrape, got {backend!r}")

    chosen = backend
    if backend == "auto":
        chosen = "api" if api_available(api_key=api_key) else "scrape"

    search = _search_api if chosen == "api" else _search_scrape
    results = search(
        query,
        max_results=max_results,
        api_key=api_key,
        language=language,
        region=region,
        **params,
    )
    if with_stats:
        results = add_stats(results, api_key=api_key, backend=chosen)
    return results


def _stats_api(video_ids: Iterable[str], *, api_key: str = None) -> dict:
    key = _api_key(api_key)
    ids = list(video_ids)
    out: dict = {}
    for start in range(0, len(ids), 50):  # the API takes 50 ids per call
        batch = ids[start : start + 50]
        url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(
            {"part": "statistics,contentDetails", "id": ",".join(batch), "key": key}
        )
        for item in json.loads(_get(url)).get("items", []):
            stats = item.get("statistics", {})
            out[item["id"]] = {
                "views": int(stats["viewCount"]) if "viewCount" in stats else None,
                "likes": int(stats["likeCount"]) if "likeCount" in stats else None,
                "comments": int(stats["commentCount"]) if "commentCount" in stats else None,
                "duration": item.get("contentDetails", {}).get("duration"),
            }
    return out


def _stats_scrape(video_ids: Iterable[str]) -> dict:
    out: dict = {}
    for video_id in video_ids:
        try:
            html = _get(watch_url(video_id))
            views = re.search(r'"viewCount":\s*{"simpleText":"([\d\s ,.]+)', html)
            if not views:
                views = re.search(r'"viewCount":"(\d+)"', html)
            seconds = re.search(r'"lengthSeconds":"(\d+)"', html)
            digits = lambda m: int(re.sub(r"\D", "", m.group(1))) if m else None
            out[video_id] = {
                "views": digits(views),
                # Deliberately absent, not missed: a signed-out watch page no
                # longer carries the count. The API backend fills it in.
                "likes": None,
                "comments": None,
                "duration_seconds": int(seconds.group(1)) if seconds else None,
            }
        except Exception:
            out[video_id] = {"views": None, "likes": None, "comments": None}
    return out


def add_stats(videos: list, *, api_key: str = None, backend: str = "auto") -> list:
    """Fill in engagement numbers on search results, in place-ish (returns them)."""
    ids = [v["video_id"] for v in videos]
    if not ids:
        return videos
    use_api = backend == "api" or (backend == "auto" and api_available(api_key=api_key))
    stats = _stats_api(ids, api_key=api_key) if use_api else _stats_scrape(ids)
    for video in videos:
        video.update(stats.get(video["video_id"], {}))
    return videos


def rank_by_engagement(
    videos: list,
    *,
    min_views: int = 0,
    like_weight: float = 1.0,
    view_weight: float = 1.0,
) -> list:
    """Order videos by a like-rate-and-reach score.

    Raw view count alone rewards age and luck, and like count alone rewards the
    same. The score multiplies *reach* (log views, so an order of magnitude
    counts for a fixed amount) by *approval* (likes per thousand views), which
    ranks a well-liked mid-sized video above a big indifferent one. Videos
    missing numbers sort last rather than being dropped, since absent is not the
    same as bad.
    """
    import math

    def score(video):
        views, likes = video.get("views"), video.get("likes")
        if not views:
            return -1.0
        reach = math.log10(max(views, 1)) * view_weight
        approval = ((likes or 0) / views * 1000) * like_weight
        return reach * (1 + approval)

    for video in videos:
        video["engagement_score"] = round(score(video), 3)
    keep = [v for v in videos if (v.get("views") or 0) >= min_views or v.get("views") is None]
    return sorted(keep, key=lambda v: v["engagement_score"], reverse=True)
