"""Network-free tests for yb.youtube.stats pure logic + orchestrator (via a fake service)."""

from __future__ import annotations

import pytest

from yb.youtube.stats import (
    FIELD_GROUPS,
    flatten_video,
    render_table,
    resolve_fields,
    select_fields,
    video_metadata,
    _iso8601_to_seconds,
    _hms,
)


def _resource(vid="abc123", **over):
    base = {
        "id": vid,
        "snippet": {
            "title": "My Video",
            "channelTitle": "My Channel",
            "channelId": "UC_x",
            "publishedAt": "2026-07-05T00:00:00Z",
            "categoryId": "28",
            "defaultAudioLanguage": "en",
            "tags": ["a", "b", "c"],
        },
        "statistics": {
            "viewCount": "666",
            "likeCount": "11",
            "dislikeCount": "0",
            "favoriteCount": "0",
            "commentCount": "0",
        },
        "contentDetails": {
            "duration": "PT1M51S",
            "definition": "hd",
            "dimension": "2d",
            "caption": "true",
            "hasCustomThumbnail": False,
            "licensedContent": False,
            "projection": "rectangular",
        },
        "status": {
            "uploadStatus": "processed",
            "privacyStatus": "public",
            "license": "youtube",
            "embeddable": True,
            "publicStatsViewable": True,
            "madeForKids": False,
        },
    }
    for k, v in over.items():
        base[k] = {**base.get(k, {}), **v} if isinstance(v, dict) else v
    return base


class FakeService:
    """Minimal stand-in for the googleapiclient YouTube service."""

    def __init__(self, items):
        self._items = {it["id"]: it for it in items}

    def videos(self):
        return self

    def list(self, *, part, id):
        self._requested = id.split(",")
        return self

    def execute(self):
        return {"items": [self._items[i] for i in self._requested if i in self._items]}


# ---- pure helpers ---------------------------------------------------------
def test_iso8601_and_hms():
    assert _iso8601_to_seconds("PT1M51S") == 111
    assert _iso8601_to_seconds("PT1H2M3S") == 3723
    assert _iso8601_to_seconds("PT45S") == 45
    assert _iso8601_to_seconds(None) is None
    assert _hms(111) == "1:51"
    assert _hms(3723) == "1:02:03"


def test_flatten_types_and_derived():
    flat = flatten_video(_resource())
    assert flat["views"] == 666 and isinstance(flat["views"], int)
    assert flat["likes"] == 11
    assert flat["dislikes"] == 0  # owner-visible
    assert flat["url"] == "https://youtu.be/abc123"
    assert flat["duration"] == "1:51" and flat["duration_seconds"] == 111
    assert flat["has_captions"] is True
    assert flat["like_view_pct"] == pytest.approx(100 * 11 / 666, rel=1e-3)
    assert flat["tag_count"] == 3


def test_flatten_missing_parts_become_none():
    flat = flatten_video({"id": "z", "snippet": {"title": "T"}})
    assert flat["views"] is None
    assert flat["dislikes"] is None  # e.g. not the owner
    assert flat["duration"] is None
    assert flat["comment_view_pct"] is None
    assert flat["tag_count"] == 0


# ---- field selection ------------------------------------------------------
def test_resolve_precedence_and_unknown_group():
    assert resolve_fields(fields=["a", "b"], group="engagement") == ["a", "b"]
    assert resolve_fields(group="engagement") == FIELD_GROUPS["engagement"]
    assert resolve_fields(available=["x", "y"]) == ["x", "y"]
    with pytest.raises(KeyError):
        resolve_fields(group="nope")


def test_select_orders_by_request():
    flat = flatten_video(_resource())
    got = select_fields(flat, fields=["likes", "views", "title"])
    assert list(got) == ["likes", "views", "title"]
    assert got == {"likes": 11, "views": 666, "title": "My Video"}


# ---- table rendering ------------------------------------------------------
def test_render_single_two_column():
    flat = flatten_video(_resource())
    table = render_table(flat, fields=["views", "likes", "comments"])
    lines = table.splitlines()
    assert lines[0].split() == ["field", "value"]
    assert "views" in table and "666" in table
    # None renders as em-dash, ints get thousands separators
    big = render_table({"views": 1234567}, fields=["views"])
    assert "1,234,567" in big


def test_render_multi_row_per_video():
    a = flatten_video(_resource("id_a", snippet={"title": "A"}))
    b = flatten_video(_resource("id_b", snippet={"title": "B"}, statistics={"viewCount": "9"}))
    table = render_table([a, b], fields=["title", "views"])
    assert "title" in table.splitlines()[0]
    assert "A" in table and "B" in table


# ---- orchestrator via fake service (DI, no network) -----------------------
def test_video_metadata_single_dict():
    svc = FakeService([_resource("v1")])
    out = video_metadata("v1", group="engagement", service=svc)
    assert out["views"] == 666 and list(out) == FIELD_GROUPS["engagement"]


def test_video_metadata_table_flag():
    svc = FakeService([_resource("v1")])
    out = video_metadata("v1", group="engagement", as_table=True, service=svc)
    assert isinstance(out, str) and "views" in out and "666" in out


def test_video_metadata_many_returns_list():
    svc = FakeService([_resource("v1"), _resource("v2", statistics={"viewCount": "3"})])
    out = video_metadata(["v1", "v2"], fields=["id", "views"], service=svc)
    assert isinstance(out, list) and len(out) == 2
    assert out[1] == {"id": "v2", "views": 3}


def test_video_metadata_empty_raises():
    with pytest.raises(ValueError):
        video_metadata([], service=FakeService([]))
