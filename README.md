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
from yb.download import download_youtube_video, download_youtube_audio, youtube_video_info

youtube_video_info(url)                       # metadata only, no download
download_youtube_video(url)                   # best quality -> ~/Downloads/"Title (id).mp4"
download_youtube_video(url, download_dir="~/clips", write_info_json=True,
                       write_subtitles=True, subtitle_langs=("en", "fr"))

download_youtube_audio(url)                   # audio only, source format -> "Title (id).webm"
download_youtube_audio(url, audio_format="mp3")           # ...converted (needs ffmpeg)
download_youtube_audio(url, audio_format="mp3", bitrate="320k")
```

The destination defaults to `$YB_DOWNLOAD_DIR` (else `~/Downloads`). Every knob
— format, filename template, which sidecar metadata to also save — is
overridable, and any raw yt-dlp option can be passed via `extra_opts=`.

**Audio format.** `download_youtube_audio` keeps whatever the source offers by
default (YouTube's best audio is normally Opus in a `.webm` container). That
default needs no ffmpeg and avoids re-encoding one lossy format into another.
Pass `audio_format=` when you need a specific one — it's a no-op if the download
already is that format, so it's safe to pass unconditionally. If conversion
can't happen (no ffmpeg) it raises, and **the download is always left on disk**;
pass `on_error="warn"` to fall back to the unconverted file instead.

The same conversion is available standalone for files you already have:

```python
from yb.audio_convert import convert_audio

convert_audio("talk.webm", "mp3")             # -> talk.mp3
convert_audio("talk.webm", "wav")             # lossless: bitrate not applied
```

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

### Read live stats & metadata

```python
from yb.youtube import video_metadata, FIELD_GROUPS

video_metadata("VIDEO_ID", group="engagement")            # dict: views, likes, dislikes, comments, ...
print(video_metadata("VIDEO_ID", group="engagement", as_table=True))  # readable ASCII table
video_metadata("VIDEO_ID", fields=["title", "views", "likes"])        # pick & order exact fields
print(video_metadata(["ID1", "ID2"], group="engagement", as_table=True))  # compare videos, one row each
```

One request returns a flat, typed view of a video's live numbers plus content
and status details. With no `group`/`fields` you get every field; `fields`
overrides `group`. Named groups (`FIELD_GROUPS`): `engagement`, `overview`,
`content`, `status`, `identity`. `dislikes` is returned only to the video's
**owner** (else `None`); watch-time/retention/shares live in the YouTube
*Analytics* API, not here.

### Publish a song as a music video

You have a song and its cover; YouTube wants a video. `yb.music` renders one
(through [`muvid.visualize`](https://github.com/thorwhalen/muvid)) and publishes
it through the same machinery as everything else. Needs `pip install 'yb[music]'`
(pulls `muvid`, which needs `ffmpeg`); uploading also needs `yb[youtube]`.

```python
from yb.music import prepare_music_video, publish_music, publish_folder

# Simplest: the cover on a 16:9 canvas, held for the song's length.
mv = prepare_music_video("song.wav", image="cover.png")
mv.video, mv.thumbnail            # -> song.mp4, song.thumb.jpg

# Render and upload in one call.
publish_music("song.wav", image="cover.png", privacy_status="unlisted")
```

**A whole folder → an album.** Drop `(song.wav, song.jpeg)` pairs in a folder —
the **filename is the title**, covers match by name — and publish them all, each
song rendered with the next visual in a rotation:

```python
# Test the first song (unlisted) before committing the set…
publish_folder("~/album", limit=1)
# …then do the rest, collected into one playlist.
publish_folder("~/album", playlist="My Album")
```

By default the rotation is `waves → cqt → spectrum → bars → scope` (override with
`cycle=`), so a set varies method to method yet reads as one release — reinforced
by a consistent **teal** accent and one loudness target across every video.
`prepare_folder(...)` renders without uploading, for review first.

Pick a single **visual** with `visual=`: `"still"` (default when there's an
image), `"ken_burns"` (a slow pan/zoom), or an audio-reactive one — `"cqt"`
(pitch-aligned bars, the most musical), `"bars"`, `"spectrum"`, `"waves"`,
`"scope"`. All the reactive ones are pure ffmpeg. You can also pass **your own
callable** (see `muvid.visualize.register_visual`).

What you get for free, because it's what makes a set of songs feel like a release:

- **16:9, never pillarboxed.** Square or portrait art is composed onto a 1080p
  canvas filled with a blurred, darkened copy of itself — not black bars.
- **Loudness-normalized** to −14 LUFS (EBU R128, two-pass), so an album plays at
  one level. `normalize=False` to opt out.
- **A thumbnail** derived from the same composition (1280×720, under YouTube's
  2 MiB limit), used as the video's thumbnail by default.
- **Music category**, and a video exactly as long as the song.

Check what you made before you ship it:

```python
from muvid.visualize import verify_video, report
print(report(verify_video("song.mp4", audio="song.wav", thumbnail="song.thumb.jpg")))
```

See the **`music2video`** skill for the visualizer menu and the full quality
checklist.

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
| `yb.music` | songs → music videos, published as an album | `music` (+`youtube` to upload) |
| `yb.youtube` | upload, edit + read stats via YouTube Data API v3 | `youtube` |
| `yb.podcast` | show notes, ID3/PSC chapters, cover video, RSS | `podcast` (+`music` for cover video) |
| `yb.download` | yt-dlp downloader (video, audio-only, playlists, metadata) | `download` |
| `yb.audio_convert` | audio format conversion via ffmpeg | core (needs `ffmpeg`) |

The audio→video rendering itself lives in
[`muvid.visualize`](https://github.com/thorwhalen/muvid) (canvas, visual
strategies, loudness, verification); `yb.music` is the publish-facing facade over
it, and the `music` extra pulls `muvid`.
