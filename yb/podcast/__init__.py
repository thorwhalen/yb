"""Podcast publishing: show notes, chapters, cover video, and RSS.

Optionally installed (``pip install 'yb[podcast]'``). Consumes the same
platform-neutral :class:`yb.content.PublicationContent` as the YouTube adapter.

    >>> from yb.podcast import prepare_podcast_episode  # doctest: +SKIP
    >>> ep = prepare_podcast_episode("episode.mp3", "out/", cover_image="cover.jpg")  # doctest: +SKIP
    >>> print(ep.show_notes, ep.chapters_psc)  # doctest: +SKIP
"""

from yb.podcast.shownotes import format_show_notes
from yb.podcast.chapters import psc_xml, write_psc, write_id3_chapters
from yb.podcast.cover import cover_video
from yb.podcast.feed import PodcastChannel, EpisodeFeedItem, build_feed
from yb.podcast.publish import prepare_podcast_episode, PodcastEpisode

__all__ = [
    "format_show_notes",
    "psc_xml",
    "write_psc",
    "write_id3_chapters",
    "cover_video",
    "PodcastChannel",
    "EpisodeFeedItem",
    "build_feed",
    "prepare_podcast_episode",
    "PodcastEpisode",
]
