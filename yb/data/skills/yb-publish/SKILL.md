---
name: yb-publish
description: >
  Prepare and publish a video to YouTube with the `yb` package: transcribe,
  derive title/description/keywords, detect chapters, render a thumbnail,
  upload (with captions), and edit already-published videos (metadata,
  subtitles, chapters, thumbnail). Use when the user wants to publish/upload a
  video to YouTube, prepare YouTube metadata/chapters/subtitles, replace or add
  subtitles on an existing video, or update a published video's title/
  description/tags/thumbnail. For first-time OAuth setup, use yb-setup first.
---

# yb-publish

Turn a finished video into a YouTube publication, or edit one already up.
Requires `yb[youtube]` and a configured OAuth client (see **yb-setup**).

## Defaults: privacy & playlist (config)

Publishing defaults live in `~/.config/yb/config.json` (next to the OAuth token)
— the single source of truth, so you don't pass them on every call:

```json
{
  "privacy_status": "unlisted",
  "playlist": "TW Uploads",
  "create_playlist_if_missing": true,
  "playlist_privacy_status": "private"
}
```

- **Privacy** defaults to `unlisted` (off the public feed, shareable by link).
- **Playlist**: every upload is added to the named playlist (created if missing,
  as a `private` playlist) so you can find your videos. Adding is idempotent.
- The file is optional — with none, you get `unlisted` and no playlist.

Call-site arguments override the file: `privacy_status="public"` makes one video
public; `playlist=None` skips the playlist for one call; `playlist="Other"`
targets a different one. The result dict gains a `playlist` key:
`{"playlist_id", "playlist_title", "added", "created"}` (or `None`).

Add an *already-published* video to a playlist:

```python
from yb.youtube import add_video_to_playlist
add_video_to_playlist("VIDEO_ID", "TW Uploads")  # find-or-create, idempotent
```

## Reuse-and-persist rule

The transcript SRT lives next to the media (`<basename>.srt`) and is **reused if
present** — re-transcribing costs API credits and the file may be hand-edited.
`yb`/`mixing` handle this automatically (`mixing.transcript.srt_for_media`), and
Scribe responses are cached on disk too. Tell the user when an existing SRT is
reused; to regenerate, delete/rename it.

## Publish (one call)

```python
from yb.youtube import prepare_and_publish

result = prepare_and_publish(
    "promo.fr.mp4",
    language="French",            # language to WRITE metadata in
    language_code="fr",           # metadata language (defaultLanguage)
    audio_language_code="fr",     # spoken language (defaultAudioLanguage) — also the caption language
    brand="Inoocq",               # keep verbatim in copy
    privacy_status="unlisted",
)
print(result["url"], result["privacy_status"])
```

This transcribes (persisting the SRT), writes title/description/keywords (LLM),
detects chapters, renders a thumbnail, uploads, attaches the SRT caption track,
and sets the thumbnail. **Always set the audio language** — the caption track is
uploaded under it.

For full control, build `VideoMetadata` + `CaptionTrack` and call
`yb.youtube.publish_video(...)`.

## Chapters (default on)

Chapters come from the transcript and are embedded in the description so YouTube
renders interactive chapters. The rules (enforced in code, do not hand-roll):

- First chapter **must** start at `0:00`.
- Each chapter **≥ 10 seconds**; **≥ 3 chapters** total or none are shown.
- 4–8 chapters for a 5–15 min piece; scale up but don't over-segment — mark real
  topic shifts, on cue boundaries, titled in 2–7 words (no leading numbers).

Very short clips (e.g. a 60 s ad) get **no** chapters automatically — that's
expected, not a bug. Pass `with_chapters=False` to skip them.

## Edit an already-published video

```python
from yb.youtube import update_video_fields, upsert_caption, set_chapters, set_thumbnail
from mixing.chapters import Chapter

update_video_fields("VIDEO_ID", title="New title", description="...", tags=["a","b"])
upsert_caption("VIDEO_ID", "subs.fr.srt", language="fr", name="Français")  # replaces same-language track
set_chapters("VIDEO_ID", [Chapter(0,"Intro"), Chapter(45,"Demo"), Chapter(120,"Pricing")])
set_thumbnail("VIDEO_ID", "thumb.jpg")
```

`upsert_caption` updates an existing uploaded (`standard`) track in the same
language, else inserts one. (YouTube's own auto `asr` tracks are left alone.)

## Read live stats & metadata

`video_metadata` fetches a flattened, typed view of a video's live numbers
(views, likes, dislikes, comments, ...) plus content/status details in one call:

```python
from yb.youtube import video_metadata, FIELD_GROUPS

video_metadata("VIDEO_ID", group="engagement")                 # dict of the live numbers
print(video_metadata("VIDEO_ID", group="engagement", as_table=True))  # readable ASCII table
video_metadata("VIDEO_ID", fields=["title", "views", "likes"]) # pick/order exact fields
print(video_metadata(["ID1", "ID2"], group="engagement", as_table=True))  # compare videos (row each)
```

- No `group`/`fields` → every available field. `fields` overrides `group`.
- Named groups (`FIELD_GROUPS`): `engagement`, `overview`, `content`, `status`, `identity`.
- `dislikes` is returned **only to the video's owner**; else `None`. Deeper
  metrics (watch time, shares, retention) need the YouTube **Analytics** API +
  the `yt-analytics.readonly` scope — not covered here.

## Notes

- Multilingual: dub/translate with `mixing.dubbing` first, then publish each
  language version as its own video with its own `language_code`/`audio_language_code`.
- The result dict's `privacy_status` reflects what YouTube actually set — an
  unaudited project may force `private` (see yb-setup).
- The API cannot *pin* comments; surface suggested pinned-comment text for the
  user to post manually.
