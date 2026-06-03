# yb

Streamline media publishing: **prepare a piece of media once, publish it
anywhere** — to YouTube (upload + edit) or as a podcast (show notes, chapters,
RSS) — plus a download module for pulling videos back down.

```python
import yb

# Download a video (-> ~/Downloads, named "Title (id).mp4")
r = yb.download_youtube_video("https://youtu.be/PRa9ciOe-us")

# One call: transcribe, write title/description/keywords, detect chapters,
# render a thumbnail, and upload to YouTube (unlisted) with captions.
yb.prepare_and_publish(r.path, language="English", language_code="en",
                       audio_language_code="en", privacy_status="unlisted")
```

## Why

`yb` separates **what** you publish from **where** you publish it. A media file
is turned into a platform-neutral [`PublicationContent`](yb/content.py) — title,
description, keywords, chapters, captions, thumbnail — and thin *adapters* map
that onto each destination's API. The media work itself (transcription, chapter
detection, thumbnails, dubbing/translation) lives in the
[`mixing`](https://github.com/thorwhalen/mixing) package; `yb` is the
publication layer on top.

## Install

```bash
pip install yb                 # core (needs `mixing`)
pip install 'yb[youtube]'      # YouTube upload/edit (Google API client)
pip install 'yb[download]'     # yt-dlp downloader
pip install 'yb[podcast]'      # podcast chapters (ID3/PSC) + RSS
pip install 'yb[llm]'          # LLM metadata/chapter copy (via `aix`)
pip install 'yb[all]'          # everything
```

Everything heavy is an optional extra, and `import yb` never fails for a missing
one — the error only surfaces when you actually call that feature. You also need
**ffmpeg** on PATH for media work, and an `ELEVENLABS_API_KEY` for transcription.

## Common tasks

### Download

```python
from yb.download import download_youtube_video, youtube_video_info

youtube_video_info(url)                       # metadata only, no download
download_youtube_video(url)                   # best quality -> ~/Downloads/"Title (id).mp4"
download_youtube_video(url, download_dir="~/clips", write_info_json=True,
                       write_subtitles=True, subtitle_langs=("en", "fr"))
```

The destination defaults to `$YB_DOWNLOAD_DIR` (else `~/Downloads`). Every knob
— format, filename template, which sidecar metadata to also save — is
overridable, and any raw yt-dlp option can be passed via `extra_opts=`.

### Publish to YouTube

```python
from yb.youtube import prepare_and_publish, VideoMetadata, publish_video, CaptionTrack

# High level: prepare assets from the media file, then upload.
result = prepare_and_publish("promo.fr.mp4", language="French",
                             language_code="fr", audio_language_code="fr",
                             privacy_status="unlisted")
print(result["url"])

# Lower level: you supply the metadata and captions.
meta = VideoMetadata(title="...", description="...", tags=[...],
                     default_language="en", default_audio_language="en")
publish_video("promo.en.mp4", meta, privacy_status="unlisted",
              captions=[CaptionTrack("promo.en.srt", "en", "English")],
              thumbnail="thumb.jpg")
```

**Chapters** are on by default: when the media is long enough to host them
(YouTube requires ≥3 markers, each ≥10 s, first at `0:00`), they are detected
from the transcript and embedded in the description so YouTube renders
interactive chapters. Short clips simply get none.

### Edit an already-published video

```python
from yb.youtube import update_video_fields, upsert_caption, set_chapters, set_thumbnail
from mixing.chapters import Chapter

update_video_fields("VIDEO_ID", title="New title", tags=["a", "b"])
upsert_caption("VIDEO_ID", "subs.fr.srt", language="fr", name="Français")  # replaces same-lang track
set_chapters("VIDEO_ID", [Chapter(0, "Intro"), Chapter(45, "Demo")])
set_thumbnail("VIDEO_ID", "thumb.jpg")
```

### Publish a podcast episode

```python
from yb.podcast import prepare_podcast_episode, PodcastChannel, EpisodeFeedItem, build_feed

ep = prepare_podcast_episode("episode.mp3", "out/",
                             cover_image="cover.jpg", make_cover_video=True)
# -> out/episode.mp3 (with ID3 chapters), .shownotes.txt, .psc.xml,
#    .chapters.json, and .cover.mp4

# Assemble an RSS feed (delivery to Spotify/Apple is via your podcast host).
```

A podcast episode and a YouTube video are built from the *same*
`PublicationContent`: an episode "could just be audio with a cover image" (or a
Ken Burns video), which is exactly what `prepare_podcast_episode` can render.

## Setup (YouTube OAuth)

YouTube upload needs a Google OAuth *Desktop* client (one-time). `gcloud` is
**not required** — the console path works. See the **`yb-setup`** skill for the
full walkthrough (enable the API, create the OAuth client, run consent, test).
Point `yb` at the client JSON via `$YOUTUBE_CLIENT_SECRETS_FILE`.

> Note: until your Google Cloud project passes YouTube's one-time API
> compliance audit, uploads may be forced to **private** even when you request
> `unlisted`/`public`.

## Layout

| Module | Role | Extra |
|---|---|---|
| `yb.content` | platform-neutral content prep (metadata, chapters, thumbnail) | core |
| `yb.youtube` | upload + edit via YouTube Data API v3 | `youtube` |
| `yb.podcast` | show notes, ID3/PSC chapters, cover video, RSS | `podcast` |
| `yb.download` | yt-dlp downloader | `download` |
