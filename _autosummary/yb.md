# yb

yb — streamline media publishing: prepare once, publish to YouTube or podcast.

Layered by separation of concerns:

- **core (always available):** [`yb.content`](yb.content.md#module-yb.content) — build a platform-neutral
  [`PublicationContent`](yb.content.md#yb.content.PublicationContent) (title, description, keywords,
  > chapters, captions, thumbnail) from a media file, delegating transcription,
  > chapter detection, and thumbnails to the `mixing` package.
- **adapters (optional extras):**
  - [`yb.youtube`](yb.youtube.md#module-yb.youtube) (`pip install 'yb[youtube]'`) — upload and edit videos.
  - `yb.music` (`pip install 'yb[music]'`) — turn songs into music videos
  > (rendering via `muvid`) and publish them, including a whole folder as an
  > album. Uploading also needs `yb[youtube]`.
  - [`yb.podcast`](yb.podcast.md#module-yb.podcast) (`pip install 'yb[podcast]'`) — show notes, chapter
    markers, cover-over-audio video (via `muvid`), RSS episode item.
  - [`yb.download`](yb.download.md#module-yb.download) (`pip install 'yb[download]'`) — fetch videos/metadata.

The audio→video rendering itself lives in `muvid.visualize` (`yb` is the
publication layer); `yb.music` is the thin publish-facing facade over it.

The most common callables are re-exported here for convenience; the ones that
live in optional extras are imported lazily, so `import yb` never fails for a
missing extra — the error surfaces only when you actually use that feature.

### Examples

```pycon
>>> import yb
>>> r = yb.download_youtube_video("https://youtu.be/PRa9ciOe-us")  # needs yb[download]
>>> content = yb.prepare_content(r.path, language="English", language_code="en")
>>> yb.prepare_and_publish(r.path, privacy_status="unlisted")        # needs yb[youtube]
```

### *class* yb.ContentMetadata(title, description, keywords=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Platform-neutral copy: a title, a description, and keywords.

### *class* yb.PublicationContent(media, title='', description='', keywords=<factory>, chapters=<factory>, language=None, audio_language=None, srt_path=None, thumbnail=None, duration=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Everything needed to publish a piece of media, destination-agnostic.

#### media

Path to the audio/video file.

#### title

Headline/title.

#### description

Long-form description / show notes body.

#### keywords

Topical keywords/tags.

#### chapters

Ordered chapter markers (`mixing.chapters.Chapter`).

#### language

BCP-47 code of the metadata text (e.g. `"en"`).

#### audio_language

BCP-47 code of the spoken audio (e.g. `"fr"`).

#### srt_path

Path to the SRT subtitle/caption file, if any.

#### thumbnail

Path to a thumbnail/cover image, if any.

#### duration

Media duration in seconds, if known.

#### description_with_chapters()

Description with a chapters block appended (if any chapters).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### *class* yb.YbConfig(privacy_status='unlisted', playlist=None, create_playlist_if_missing=True, playlist_privacy_status='private')

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Resolved publishing defaults.

#### privacy_status

Privacy a new upload gets (`unlisted` | `private` |
`public`) when the call doesn’t override it.

#### playlist

Title of a playlist every upload is added to (`None` = none).

#### create_playlist_if_missing

Create `playlist` if no playlist of that
title exists yet, rather than erroring.

#### playlist_privacy_status

Privacy for an auto-created playlist.

#### *classmethod* from_mapping(mapping)

Build a config from a mapping, ignoring unknown keys.

* **Return type:**
  [`YbConfig`](yb.config.md#yb.config.YbConfig)

### yb.add_video_to_playlist(video_id, title, , create=True, privacy_status='private', skip_if_present=True, service=None, \*\*cred_kwargs)

Find-or-create the playlist named `title` and append `video_id`.

Idempotent: with `skip_if_present` (default), a video already in the
playlist is left alone instead of duplicated.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
* **Returns:**
  `{"playlist_id", "playlist_title", "added", "created"}` where `added`
  is `False` if the video was already present and `created` is `True`
  if the playlist had to be made.
* **Raises:**
  [**KeyError**](https://docs.python.org/3/builtins/exceptions.html#KeyError) – the playlist is absent and `create=False`.

### yb.default_config_file()

Config file location (`$XDG_CONFIG_HOME` or `~/.config`).

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### yb.download_youtube_audio(url, , download_dir=None, audio_format=None, bitrate=None, keep_original=False, on_error='raise', fmt='bestaudio/best', filename_template='%(title)s (%(id)s).%(ext)s', write_info_json=False, write_thumbnail=False, write_description=False, write_subtitles=False, write_auto_subtitles=False, subtitle_langs=('en',), quiet=True, extra_opts=None)

Download only a video’s audio (no video stream).

Simplest use: `download_youtube_audio(url)` → the best audio stream, kept
in whatever format the source offers (YouTube’s is usually Opus in a
`.webm` container), named `Title (video_id).webm` in `~/Downloads`.

Pass `audio_format` to get a specific format instead:

```pycon
>>> download_youtube_audio(url, audio_format="mp3")
```

* **Parameters:**
  * **url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The video URL (or id).
  * **download_dir** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Destination directory. Defaults to
    `default_download_dir()`.
  * **audio_format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Target format as an extension (`"mp3"`, `".wav"`, …).
    The default `None` means **no conversion** — keep the downloaded
    bytes exactly as they came, which needs no ffmpeg and avoids
    re-encoding a lossy stream into another lossy format.
  * **bitrate** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Bitrate for lossy targets (e.g. `"320k"`). Ignored when
    `audio_format` is lossless or `None`.
  * **keep_original** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – When converting, also keep the originally downloaded
    file (by default it is removed once converted).
  * **on_error** ([`Literal`](https://docs.python.org/3/library/typing.html#typing.Literal)[`'raise'`, `'warn'`]) – What to do when conversion fails (ffmpeg missing or erroring).
    `"raise"` (default) propagates
    [`AudioConversionError`](yb.audio_convert.md#yb.audio_convert.AudioConversionError); `"warn"` emits a
    warning and returns the unconverted download. Either way the
    downloaded audio is left on disk — a failed conversion never costs
    you the download.
  * **fmt** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – yt-dlp format selector (default best audio-only stream).
  * **filename_template** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – yt-dlp output template (default
    `"%(title)s (%(id)s).%(ext)s"`).
  * **write_info_json** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also save the full metadata as `*.info.json`.
  * **write_thumbnail** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also save the thumbnail image.
  * **write_description** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also save the description as `*.description`.
  * **write_subtitles** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also save uploaded subtitles for `subtitle_langs`.
  * **write_auto_subtitles** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also save auto-generated subtitles.
  * **subtitle_langs** ([`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)]) – Subtitle languages to fetch when subtitles are enabled.
  * **quiet** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Suppress yt-dlp console output.
  * **extra_opts** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Any additional raw yt-dlp options (merged last, so they win).
* **Return type:**
  [`DownloadResult`](yb.download.youtube.md#yb.download.youtube.DownloadResult)
* **Returns:**
  A `DownloadResult` whose `path` is the audio file — converted
  when `audio_format` was given and conversion succeeded.
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If `on_error` is not `"raise"` or `"warn"`.
  * [**AudioConversionError**](yb.audio_convert.md#yb.audio_convert.AudioConversionError) – If conversion fails and `on_error="raise"`.

### yb.download_youtube_video(url, , download_dir=None, fmt='bestvideo+bestaudio/best', merge_to='mp4', filename_template='%(title)s (%(id)s).%(ext)s', write_info_json=False, write_thumbnail=False, write_description=False, write_subtitles=False, write_auto_subtitles=False, subtitle_langs=('en',), quiet=True, extra_opts=None)

Download a YouTube video to `download_dir` (default `~/Downloads`).

Simplest use: `download_youtube_video(url)` → best quality merged to mp4,
named `Title (video_id).mp4` in `~/Downloads`.

* **Parameters:**
  * **url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The video URL (or id).
  * **download_dir** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Destination directory. Defaults to
    `default_download_dir()`.
  * **fmt** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – yt-dlp format selector (default best video + best audio).
  * **merge_to** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Container to merge video+audio into (default `"mp4"`;
    requires ffmpeg). Set `None` to keep yt-dlp’s default.
  * **filename_template** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – yt-dlp output template (default
    `"%(title)s (%(id)s).%(ext)s"`).
  * **write_info_json** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also save the full metadata as `*.info.json`.
  * **write_thumbnail** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also save the thumbnail image.
  * **write_description** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also save the description as `*.description`.
  * **write_subtitles** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also save uploaded subtitles for `subtitle_langs`.
  * **write_auto_subtitles** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also save auto-generated subtitles.
  * **subtitle_langs** ([`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`...`](https://docs.python.org/3/builtins/constants.html#Ellipsis)]) – Subtitle languages to fetch when subtitles are enabled.
  * **quiet** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Suppress yt-dlp console output.
  * **extra_opts** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Any additional raw yt-dlp options (merged last, so they win).
* **Return type:**
  [`DownloadResult`](yb.download.youtube.md#yb.download.youtube.DownloadResult)
* **Returns:**
  A `DownloadResult` with the media path, trimmed `info`, and any
  `sidecars` written.

### yb.format_chapter_lines(chapters)

Render chapters as `M:SS Title` lines (the shared text convention).

Uses `H:MM:SS` when any chapter is at or beyond one hour. This is the
text format both YouTube descriptions and podcast show notes accept.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### yb.generate_metadata(transcript, , language='English', brand=None, extra_context=None, model=None)

Generate platform-neutral title/description/keywords from a transcript.

LLM-backed via `aix`. Pass a ready [`ContentMetadata`](#yb.ContentMetadata) to
[`prepare_content()`](#yb.prepare_content) instead if you want to skip generation.

* **Raises:**
  [**ImportError**](https://docs.python.org/3/builtins/exceptions.html#ImportError) – `aix` is not importable.
* **Return type:**
  [`ContentMetadata`](yb.content.md#yb.content.ContentMetadata)

### yb.load_config(config_file=None, \*\*overrides)

Load publishing defaults from `config_file` (or the default location).

A missing file yields the built-in defaults. `overrides` (typically the
explicit keyword arguments a caller passed) take precedence when not
`None`, so call-site arguments always win over the file.

* **Return type:**
  [`YbConfig`](yb.config.md#yb.config.YbConfig)

### yb.prepare_and_publish(media, \*, language='English', language_code=None, audio_language_code=None, brand=None, extra_context=None, with_chapters=True, with_thumbnail=True, privacy_status=None, playlist=<object object>, category_id='28', config=None, client_secrets_file=None, token_file=None, progress=True, \*\*cred_kwargs)

One call: prepare publication content from `media` and upload it.

Transcribes (persisting the SRT next to the media) if needed, writes
LLM metadata, detects chapters, renders a thumbnail, then uploads with
captions + thumbnail + chapters and adds the video to the configured
playlist. `privacy_status` and `playlist` default to your `yb` config
(see [`publish_content()`](#yb.publish_content)).

`cred_kwargs` reach [`get_credentials()`](yb.youtube.auth.md#yb.youtube.auth.get_credentials) (e.g.
`open_browser=False, port=8080` for headless consent).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.prepare_content(media, , language='English', language_code=None, audio_language_code=None, brand=None, extra_context=None, transcript=None, with_chapters=True, with_thumbnail=False, thumbnail_text=None, metadata=None, model=None, transcribe_kwargs=None, chapters_kwargs=None)

Build a [`PublicationContent`](#yb.PublicationContent) for `media` (destination-agnostic).

Ensures a persisted SRT next to the media (transcribing once via
`mixing` if needed), writes LLM metadata, detects chapters (default on,
auto-skipped for clips too short to host them), and optionally renders a
thumbnail. Any precomputed pieces (`transcript`, `metadata`) are reused
instead of recomputed.

* **Parameters:**
  * **media** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – Audio or video file.
  * **language** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Human-readable language to write metadata in.
  * **audio_language_code** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – BCP-47 codes for the metadata
    text and the spoken audio.
  * **brand** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Product/brand name to keep verbatim in the copy.
  * **extra_context** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Extra guidance for the copywriter (audience, CTA…).
  * **transcript** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – SRT text to use as-is (skips transcription).
  * **with_chapters** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Detect chapters (default `True`).
  * **with_thumbnail** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Render a thumbnail image (default `False`).
  * **thumbnail_text** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Overlay text for the thumbnail (defaults to the title).
  * **metadata** ([`ContentMetadata`](yb.content.md#yb.content.ContentMetadata) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Precomputed [`ContentMetadata`](#yb.ContentMetadata) to reuse.
  * **model** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – LLM model override.
  * **chapters_kwargs** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Forwarded to the mixing calls.
* **Return type:**
  [`PublicationContent`](yb.content.md#yb.content.PublicationContent)
* **Returns:**
  A populated [`PublicationContent`](#yb.PublicationContent).

### yb.prepare_podcast_episode(media, output_dir, , content=None, audio=None, cover_image=None, make_cover_video=False, ken_burns=False, embed_chapters=True, language='English', brand=None, extra_context=None, audio_bitrate='192k')

Build a podcast episode bundle from `media` into `output_dir`.

* **Parameters:**
  * **media** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – Source audio or video.
  * **output_dir** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – Directory to write the episode assets into.
  * **content** ([`PublicationContent`](yb.content.md#yb.content.PublicationContent) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Precomputed [`PublicationContent`](#yb.PublicationContent); built via
    [`yb.content.prepare_content()`](yb.content.md#yb.content.prepare_content) when omitted.
  * **audio** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Explicit episode audio. When omitted, `media` is used if it is
    audio, else its audio track is extracted to MP3.
  * **cover_image** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Cover art (required for `make_cover_video`).
  * **make_cover_video** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also render a cover-over-audio mp4 (e.g. for YouTube).
  * **ken_burns** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Apply a Ken Burns pan/zoom to the cover video.
  * **embed_chapters** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Embed ID3 chapter frames into the episode MP3.
  * **extra_context** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Forwarded to `prepare_content`.
  * **audio_bitrate** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Bitrate for extracted MP3 audio.
* **Return type:**
  [`PodcastEpisode`](yb.podcast.publish.md#yb.podcast.publish.PodcastEpisode)
* **Returns:**
  A `PodcastEpisode` with the asset paths.

### yb.publish_content(content, \*, privacy_status=None, playlist=<object object>, category_id='28', with_chapters=True, attach_caption=True, set_thumb=True, config=None, client_secrets_file=None, token_file=None, progress=True, service=None, \*\*cred_kwargs)

Upload a prepared [`PublicationContent`](#yb.PublicationContent) to YouTube.

Maps the content to a YouTube snippet (chapters embedded in the
description when present), uploads, attaches the SRT caption track
(language = `content.audio_language` or `content.language`) and the
thumbnail when available, and adds the video to the configured playlist.

`privacy_status` and `playlist` default to your `yb` config (see
[`yb.config`](yb.config.md#module-yb.config)): unset means “use the config value”, so privacy falls back
to `unlisted` and the video joins your configured playlist. Pass
`playlist=None` to skip the playlist for one call, or `playlist="Name"`
to override the target.

`cred_kwargs` reach [`get_credentials()`](yb.youtube.auth.md#yb.youtube.auth.get_credentials) (e.g.
`open_browser=False, port=8080` for headless consent).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
* **Returns:**
  `{"video_id", "url", "studio_url", "privacy_status", "captions",
  "thumbnail", "playlist"}`. `privacy_status` reflects what YouTube
  actually set (an unaudited project may force `"private"`); `playlist`
  is the [`add_video_to_playlist()`](yb.youtube.playlists.md#yb.youtube.playlists.add_video_to_playlist) result or
  `None`.

### yb.set_chapters(video_id, chapters, , header='Chapters:', service=None, \*\*cred_kwargs)

Insert/replace a chapters block in the video’s description.

Strips any prior block under `header` and appends the new one. YouTube
renders interactive chapters when the first timestamp is `0:00`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.update_video_fields(video_id, , title=None, description=None, tags=None, category_id=None, default_language=None, default_audio_language=None, service=None, \*\*cred_kwargs)

Patch selected snippet fields, preserving the rest.

Fetches the current snippet, overlays the provided fields, and updates.
`categoryId` must be present (kept from the existing snippet if not given).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.upsert_caption(video_id, track, , language=None, name='', is_draft=False, replace=True, service=None, \*\*cred_kwargs)

Insert a caption track, or update the existing same-language one.

* **Parameters:**
  * **video_id** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Target video.
  * **track** ([`CaptionTrack`](yb.youtube.captions.md#yb.youtube.captions.CaptionTrack) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – A `CaptionTrack`, or a path (then `language` required).
  * **replace** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – When an uploaded track in the same language exists, update it
    (`True`, default) rather than inserting a duplicate.
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
* **Returns:**
  The inserted/updated caption resource.

### yb.youtube_video_info(url, , extra_opts=None)

Fetch a video’s metadata without downloading it.

Returns the trimmed info dict (see `_INFO_FIELDS`). Useful to preview
the title/duration/chapters before deciding to download.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### Modules

| [`audio_convert`](yb.audio_convert.md#module-yb.audio_convert)   | Convert audio files between formats with ffmpeg.                        |
|------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`config`](yb.config.md#module-yb.config)                 | User configuration for `yb` publishing defaults.                        |
| [`content`](yb.content.md#module-yb.content)               | Target-agnostic publication content: prepare it once, publish anywhere. |
| [`download`](yb.download.md#module-yb.download)             | Media download (yt-dlp) — fetch videos, audio, and their metadata.      |
| [`podcast`](yb.podcast.md#module-yb.podcast)               | Podcast publishing: show notes, chapters, cover video, and RSS.         |
| [`youtube`](yb.youtube.md#module-yb.youtube)               | YouTube publishing via the YouTube Data API v3.                         |
