# yb.podcast.feed

Podcast RSS feed generation (iTunes-compatible) via feedgen.

Builds a standards-compliant podcast RSS channel from a channel description and
a list of episodes. Chapters travel with the audio (ID3 frames) and/or as a PSC
sidecar; a Podcasting-2.0 `<podcast:chapters>` URL can be supplied per episode.

`pubdate` is always caller-supplied (never implicitly “now”) to keep feed
generation deterministic and reproducible.

### Functions

| [`build_feed`](#yb.podcast.feed.build_feed)(channel, episodes)   | Build podcast RSS XML for `channel` and its `episodes`.   |
|----------------------------------------------------------------------------------|-----------------------------------------------------------|

### Classes

| [`EpisodeFeedItem`](#yb.podcast.feed.EpisodeFeedItem)(title, description, ...[, ...])   | One episode's feed entry.      |
|----------------------------------------------------------------------------------------------------|--------------------------------|
| [`PodcastChannel`](#yb.podcast.feed.PodcastChannel)(title, link, description, ...)     | Podcast-level (show) metadata. |

### *class* yb.podcast.feed.EpisodeFeedItem(title, description, audio_url, audio_length_bytes, pubdate, guid=None, audio_mime='audio/mpeg', duration_seconds=None, image_url=None, chapters_url=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One episode’s feed entry.

### *class* yb.podcast.feed.PodcastChannel(title, link, description, author, email, image_url=None, language='en', categories=<factory>, explicit=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Podcast-level (show) metadata.

### yb.podcast.feed.build_feed(channel, episodes)

Build podcast RSS XML for `channel` and its `episodes`.

* **Raises:**
  [**ImportError**](https://docs.python.org/3/builtins/exceptions.html#ImportError) – `feedgen` is not installed (`pip install 'yb[podcast]'`).
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
