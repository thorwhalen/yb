"""Podcast RSS feed generation (iTunes-compatible) via feedgen.

Builds a standards-compliant podcast RSS channel from a channel description and
a list of episodes. Chapters travel with the audio (ID3 frames) and/or as a PSC
sidecar; a Podcasting-2.0 ``<podcast:chapters>`` URL can be supplied per episode.

``pubdate`` is always caller-supplied (never implicitly "now") to keep feed
generation deterministic and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence


@dataclass
class PodcastChannel:
    """Podcast-level (show) metadata."""

    title: str
    link: str
    description: str
    author: str
    email: str
    image_url: str | None = None
    language: str = "en"
    categories: list[str] = field(default_factory=list)
    explicit: bool = False


@dataclass
class EpisodeFeedItem:
    """One episode's feed entry."""

    title: str
    description: str
    audio_url: str
    audio_length_bytes: int
    pubdate: datetime
    guid: str | None = None
    audio_mime: str = "audio/mpeg"
    duration_seconds: float | None = None
    image_url: str | None = None
    chapters_url: str | None = None  # Podcasting-2.0 <podcast:chapters> (e.g. PSC/JSON)


def build_feed(channel: PodcastChannel, episodes: Sequence[EpisodeFeedItem]) -> str:
    """Build podcast RSS XML for ``channel`` and its ``episodes``.

    Raises:
        ImportError: ``feedgen`` is not installed (``pip install 'yb[podcast]'``).
    """
    from feedgen.feed import FeedGenerator

    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.title(channel.title)
    fg.link(href=channel.link, rel="alternate")
    fg.description(channel.description)
    fg.language(channel.language)
    fg.author({"name": channel.author, "email": channel.email})
    if channel.image_url:
        fg.image(channel.image_url)
        fg.podcast.itunes_image(channel.image_url)
    fg.podcast.itunes_author(channel.author)
    fg.podcast.itunes_explicit("yes" if channel.explicit else "no")
    if channel.categories:
        fg.podcast.itunes_category([{"cat": c} for c in channel.categories])

    for ep in episodes:
        fe = fg.add_entry()
        fe.id(ep.guid or ep.audio_url)
        fe.title(ep.title)
        fe.description(ep.description)
        fe.enclosure(ep.audio_url, str(ep.audio_length_bytes), ep.audio_mime)
        fe.published(ep.pubdate)
        if ep.duration_seconds is not None:
            fe.podcast.itunes_duration(_hms(ep.duration_seconds))
        if ep.image_url:
            fe.podcast.itunes_image(ep.image_url)

    return fg.rss_str(pretty=True).decode("utf-8")


def _hms(seconds: float) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"
