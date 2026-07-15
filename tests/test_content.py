"""Network-free tests for yb.content + yb.youtube.metadata pure logic."""

from __future__ import annotations

from mixing.chapters import Chapter

from yb.content import PublicationContent, format_chapter_lines
from yb.youtube.metadata import VideoMetadata, _cap_tags


def _content(**kw):
    base = dict(
        media="x.mp4",
        title="T",
        description="D",
        keywords=["a", "b"],
        language="en",
        audio_language="en",
        chapters=[Chapter(0, "Intro"), Chapter(20, "Middle"), Chapter(45, "End")],
    )
    base.update(kw)
    return PublicationContent(**base)


def test_format_chapter_lines_minutes_and_hours():
    chs = [Chapter(0, "Intro"), Chapter(83, "Part two")]
    assert format_chapter_lines(chs) == "0:00 Intro\n1:23 Part two"
    chs_hour = [Chapter(0, "A"), Chapter(3661, "B")]
    assert format_chapter_lines(chs_hour) == "0:00:00 A\n1:01:01 B"


def test_video_metadata_from_content_embeds_chapters():
    m = VideoMetadata.from_content(_content())
    desc = m.update_snippet()["description"]
    assert "Chapters:" in desc and "0:00 Intro" in desc
    assert m.default_language == "en"
    assert m.default_audio_language == "en"


def test_video_metadata_no_chapters_when_disabled_or_absent():
    m = VideoMetadata.from_content(_content(chapters=[]))
    assert "Chapters:" not in m.update_snippet()["description"]
    m2 = VideoMetadata.from_content(_content(), with_chapters=False)
    assert "Chapters:" not in m2.update_snippet()["description"]


def test_video_metadata_caps_limits():
    m = VideoMetadata(title="x" * 200, description="d", tags=["t" * 600, "short"])
    assert len(m.title) == 100
    # first tag alone exceeds the 500-char total cap → dropped before "short"
    assert "short" not in m.tags or len(",".join(m.tags)) <= 500


def test_cap_tags_total_length():
    tags = _cap_tags(["aaa", "bbb", "ccc"], total_max=7)
    assert tags == ["aaa", "bbb"]  # "aaa,bbb" == 7 chars; ccc would exceed


def test_description_with_chapters_helper():
    c = _content()
    out = c.description_with_chapters()
    assert out.startswith("D") and "0:00 Intro" in out
