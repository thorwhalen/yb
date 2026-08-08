---
name: yb-podcast
description: >
  Prepare a podcast episode with the `yb` package: show notes, chapter markers
  (ID3 chapters embedded in the MP3 + a Podlove PSC sidecar), an optional
  cover-over-audio video (static or Ken Burns), and an RSS episode item. Use
  when the user wants to turn audio (or a video's audio) into a publishable
  podcast episode, generate show notes / podcast chapters, embed chapters in an
  MP3, make a cover video for an audio episode, or build a podcast RSS feed.
---

# yb-podcast

Build a podcast episode bundle from a media file. Requires `yb[podcast]`
(mutagen + feedgen) and ffmpeg. Same platform-neutral `PublicationContent` as
the YouTube path — an episode is "just audio with a cover image" (or a Ken
Burns video).

## Prepare an episode

```python
from yb.podcast import prepare_podcast_episode

ep = prepare_podcast_episode(
    "episode.mp3",  # audio, or a video (its audio is extracted)
    "out/",
    cover_image="cover.jpg",
    make_cover_video=True,  # also render out/episode.cover.mp4 (e.g. for YouTube)
    ken_burns=True,  # slow pan/zoom instead of a static image
    language="English",
)
# ep.audio (MP3 with ID3 chapters), ep.show_notes, ep.chapters_psc,
# ep.chapters_json, ep.cover_video, ep.content
```

Chapters are detected from the transcript (persisted SRT, reused if present) and
written three ways: **embedded ID3 `CHAP`/`CTOC` frames** in the MP3 (travel
with the file), a **PSC XML sidecar**, and a **JSON** list. Show notes are
`title` + description + a `M:SS Title` chapter list.

## Build the RSS feed

```python
from datetime import datetime, timezone
from yb.podcast import PodcastChannel, EpisodeFeedItem, build_feed

channel = PodcastChannel(
    title="My Show",
    link="https://show.example",
    description="...",
    author="Me",
    email="me@example.com",
    image_url="https://show.example/cover.jpg",
    categories=["Technology"],
)
item = EpisodeFeedItem(
    title=ep.content.title,
    description=open(ep.show_notes).read(),
    audio_url="https://host.example/episode.mp3",
    audio_length_bytes=ep.audio.stat().st_size,
    pubdate=datetime(2026, 6, 3, tzinfo=timezone.utc),
    duration_seconds=...,
    image_url="https://show.example/cover.jpg",
)
rss = build_feed(channel, [item])
```

`pubdate` is always explicit (never implicit "now") so feeds are reproducible.

## Notes

- **Delivery**: Spotify/Apple ingest a podcast via its **RSS feed**, hosted by
  you/your podcast host — `yb` produces the assets + feed XML, not a direct push.
- `audio_url`/`image_url` must be the public URLs where you host the files;
  `build_feed` doesn't upload them.
- For a video platform instead, use `make_cover_video=True` and publish the mp4
  via `yb-publish`.
