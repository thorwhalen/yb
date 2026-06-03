"""Network-free tests for yb.podcast chapter formats and YouTube edit helpers."""

from __future__ import annotations

import re

from mixing.chapters import Chapter

from yb.podcast.chapters import psc_xml
from yb.podcast.shownotes import format_show_notes
from yb.content import PublicationContent
from yb.youtube.api import _replace_chapters_block


CHAPTERS = [Chapter(0, "Intro"), Chapter(30, "How it works"), Chapter(75, "Wrap up")]


def test_psc_xml_structure():
    xml = psc_xml(CHAPTERS)
    assert 'xmlns:psc="http://podlove.org/simple-chapters"' in xml
    assert xml.count("<psc:chapter ") == 3
    assert 'start="00:00:00.000" title="Intro"' in xml
    assert 'start="00:01:15.000" title="Wrap up"' in xml


def test_psc_escapes_titles():
    xml = psc_xml([Chapter(0, "A & B <tag>")])
    assert "A &amp; B &lt;tag&gt;" in xml


def test_show_notes_includes_chapters():
    c = PublicationContent(media="e.mp3", title="Ep 1", description="Body.", chapters=CHAPTERS)
    notes = format_show_notes(c)
    assert notes.startswith("Ep 1")
    assert "Body." in notes
    assert "Chapters:\n0:00 Intro" in notes


def test_replace_chapters_block_appends_then_replaces():
    desc = "Great episode about X."
    once = _set(desc, CHAPTERS)
    assert once.endswith("0:00 Intro\n0:30 How it works\n1:15 Wrap up")
    # replacing should not duplicate the block
    twice = _set(once, [Chapter(0, "New intro"), Chapter(40, "New mid"), Chapter(75, "New end")])
    assert twice.count("Chapters:") == 1
    assert "New intro" in twice and "How it works" not in twice
    assert twice.startswith("Great episode about X.")


def test_replace_chapters_block_clear():
    desc = _set("Body", CHAPTERS)
    cleared = _replace_chapters_block(desc, [], "Chapters:")
    assert "Chapters:" not in cleared
    assert cleared.strip() == "Body"


def _set(desc, chapters):
    return _replace_chapters_block(desc, chapters, "Chapters:")
