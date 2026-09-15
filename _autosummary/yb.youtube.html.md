# yb.youtube

YouTube publishing via the YouTube Data API v3.

Optionally installed (`pip install 'yb[youtube]'`). Needs an OAuth Desktop
client (see the `yb-setup` skill) — set `$YOUTUBE_CLIENT_SECRETS_FILE`.

Create:

```pycon
>>> from yb.youtube import prepare_and_publish
>>> prepare_and_publish("promo.fr.mp4", language="French", language_code="fr",
...                     audio_language_code="fr", privacy_status="unlisted")
```

Edit an existing video:

```pycon
>>> from yb.youtube import update_video_fields, upsert_caption, set_chapters
>>> update_video_fields("VIDEO_ID", title="New title")
>>> upsert_caption("VIDEO_ID", "subs.fr.srt", language="fr", name="Français")
```

### Functions

| [`get_credentials`](#yb.youtube.get_credentials)(\*[, client_secrets_file, ...])    | Return OAuth user credentials, running the consent flow if needed.                                            |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| [`get_service`](#yb.youtube.get_service)(\*[, credentials])                     | Build a YouTube Data API v3 service object.                                                                   |
| [`default_token_file`](#yb.youtube.default_token_file)()                               | Cached OAuth token location (`$XDG_CONFIG_HOME` or `~/.config`).                                              |
| [`default_client_secrets_file`](#yb.youtube.default_client_secrets_file)()                      | Default OAuth client-secrets location: `<config dir>/client_secret.json`.                                     |
| [`list_my_playlists`](#yb.youtube.list_my_playlists)(\*[, service])                   | Return all playlists owned by the authenticated channel (paginated).                                          |
| [`find_playlist`](#yb.youtube.find_playlist)(title, \*[, service])                | Return the id of the caller's playlist titled `title` (or `None`).                                            |
| [`create_playlist`](#yb.youtube.create_playlist)(title, \*[, description, ...])     | Create a playlist and return its id.                                                                          |
| [`ensure_playlist`](#yb.youtube.ensure_playlist)(title, \*[, create, ...])          | Return the id of the playlist titled `title`, creating it if missing.                                         |
| [`is_video_in_playlist`](#yb.youtube.is_video_in_playlist)(video_id, playlist_id, \*)    | Whether `video_id` is already an item of `playlist_id` (paginated).                                           |
| [`add_to_playlist`](#yb.youtube.add_to_playlist)(video_id, playlist_id, \*[, ...])  | Append `video_id` to `playlist_id` (`playlistItems.insert`).                                                  |
| [`add_video_to_playlist`](#yb.youtube.add_video_to_playlist)(video_id, title, \*[, ...])  | Find-or-create the playlist named `title` and append `video_id`.                                              |
| [`get_video`](#yb.youtube.get_video)(video_id, \*[, part, service])           | Fetch a video resource (raises `KeyError` if not found/visible).                                              |
| [`upload_video`](#yb.youtube.upload_video)(video_path, body, \*[, service, ...]) | Resumably upload a video with the given `videos.insert` `body`.                                               |
| [`update_video`](#yb.youtube.update_video)(video_id, snippet, \*[, service])     | Update a video's snippet (`videos.update`).                                                                   |
| [`update_video_fields`](#yb.youtube.update_video_fields)(video_id, \*[, title, ...])    | Patch selected snippet fields, preserving the rest.                                                           |
| [`set_thumbnail`](#yb.youtube.set_thumbnail)(video_id, image_path, \*[, service]) | Set a custom thumbnail (`thumbnails.set`).                                                                    |
| [`set_chapters`](#yb.youtube.set_chapters)(video_id, chapters, \*[, ...])        | Insert/replace a chapters block in the video's description.                                                   |
| [`video_metadata`](#yb.youtube.video_metadata)(video_id, \*[, group, fields, ...]) | Fetch a video's live metadata & engagement numbers.                                                           |
| [`flatten_video`](#yb.youtube.flatten_video)(resource)                            | Flatten a raw `videos.list` item into a friendly, typed, ordered dict.                                        |
| [`select_fields`](#yb.youtube.select_fields)(flat, \*[, group, fields])           | Return an ordered subset of `flat` per `fields`/`group`.                                                      |
| [`resolve_fields`](#yb.youtube.resolve_fields)(\*[, group, fields, available])     | Resolve the ordered field list to show.                                                                       |
| [`render_table`](#yb.youtube.render_table)(data, \*[, fields])                   | Render metadata as an ASCII table.                                                                            |
| [`list_captions`](#yb.youtube.list_captions)(video_id, \*[, service])             | List caption tracks on a video (each item's snippet has language/name/trackKind/status).                      |
| [`insert_caption`](#yb.youtube.insert_caption)(video_id, path, \*, language)       | Insert a new caption track (`captions.insert`).                                                               |
| [`update_caption`](#yb.youtube.update_caption)(caption_id, path, \*[, ...])        | Replace the content of an existing caption track (`captions.update`).                                         |
| [`upsert_caption`](#yb.youtube.upsert_caption)(video_id, track, \*[, ...])         | Insert a caption track, or update the existing same-language one.                                             |
| [`download_caption`](#yb.youtube.download_caption)(caption_id, \*[, tfmt, service])  | Download a caption track's content (`captions.download`), default SRT.                                        |
| [`delete_caption`](#yb.youtube.delete_caption)(caption_id, \*[, service])          | Delete a caption track (`captions.delete`).                                                                   |
| [`publish_content`](#yb.youtube.publish_content)(content, \*[, ...])                | Upload a prepared `PublicationContent` to YouTube.                                                            |
| [`prepare_and_publish`](#yb.youtube.prepare_and_publish)(media, \*[, language, ...])    | One call: prepare publication content from `media` and upload it.                                             |
| [`publish_video`](#yb.youtube.publish_video)(video_path, metadata, \*[, ...])     | Lower-level upload: explicit [`VideoMetadata`](#yb.youtube.VideoMetadata) + caption tracks. |

### Classes

| [`VideoMetadata`](#yb.youtube.VideoMetadata)(title, description[, tags, ...])   | YouTube-specific video metadata.      |
|---------------------------------------------------------------------------------------------------|---------------------------------------|
| [`CaptionTrack`](#yb.youtube.CaptionTrack)(path, language[, name, is_draft])   | A caption track to attach to a video. |

### Exceptions

| [`ConsentRequired`](#yb.youtube.ConsentRequired)   | Consent is needed and this process cannot obtain it.   |
|--------------------------------------------------------------------|--------------------------------------------------------|

### *class* yb.youtube.CaptionTrack(path, language, name='', is_draft=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A caption track to attach to a video.

#### path

Path to an `.srt` (or `.vtt`) file.

#### language

BCP-47 language code, e.g. `"en"` or `"fr"`.

#### name

Track name shown in the YouTube UI (e.g. `"English"`).

#### is_draft

When `True`, uploaded but not published to viewers.

### *exception* yb.youtube.ConsentRequired

Bases: [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

Consent is needed and this process cannot obtain it.

Raised instead of starting a consent flow that nobody can complete. The
alternative is worse than an error: `run_local_server` prints a URL to a
stdout nobody is reading and waits on `localhost` for a redirect that will
never arrive, so an automated caller *blocks* rather than failing. That has
happened — an upload stopped dead mid-script and read as a slow network for
hours, when the underlying cause was one line of `invalid_grant`.

### *class* yb.youtube.VideoMetadata(title, description, tags=<factory>, category_id='28', default_language=None, default_audio_language=None, contains_synthetic_media=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

YouTube-specific video metadata.

#### title

Title (<= 100 chars).

#### description

Description (<= 5000 chars), chapters already embedded.

#### tags

Keyword tags (combined length kept under 500 chars).

#### category_id

YouTube category id (default Science & Technology).

#### default_language

BCP-47 language of the metadata text.

#### default_audio_language

BCP-47 language of the audio.

#### contains_synthetic_media

Declare that the video contains realistic
altered or synthetic content. YouTube’s disclosure rule turns on
*realism*, not on whether AI was involved: it applies when a viewer
could mistake the content for a real person, place, or event —
not to stylised artwork or a visualizer. Left unset when `None`.

#### *classmethod* from_content(content, , category_id='28', with_chapters=True)

Build YouTube metadata from a platform-neutral content bundle.

Embeds the chapters block into the description (when present and
`with_chapters`), so YouTube renders interactive chapters.

* **Return type:**
  [`VideoMetadata`](yb.youtube.metadata.html.md#yb.youtube.metadata.VideoMetadata)

#### insert_body(, privacy_status='unlisted')

Build the `videos.insert` body (snippet + status).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

#### update_snippet()

Build the snippet for `videos.update` (categoryId is required).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.add_to_playlist(video_id, playlist_id, , service=None, \*\*cred_kwargs)

Append `video_id` to `playlist_id` (`playlistItems.insert`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.add_video_to_playlist(video_id, title, , create=True, privacy_status='private', skip_if_present=True, service=None, \*\*cred_kwargs)

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

### yb.youtube.create_playlist(title, , description='', privacy_status='private', service=None, \*\*cred_kwargs)

Create a playlist and return its id.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### yb.youtube.default_client_secrets_file()

Default OAuth client-secrets location: `<config dir>/client_secret.json`.

Used when neither `client_secrets_file=` nor the env vars are set, so all
of `yb`’s state can live in one directory next to the token.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### yb.youtube.default_token_file()

Cached OAuth token location (`$XDG_CONFIG_HOME` or `~/.config`).

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### yb.youtube.delete_caption(caption_id, , service=None, \*\*cred_kwargs)

Delete a caption track (`captions.delete`).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### yb.youtube.download_caption(caption_id, , tfmt='srt', service=None, \*\*cred_kwargs)

Download a caption track’s content (`captions.download`), default SRT.

* **Return type:**
  [`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes)

### yb.youtube.ensure_playlist(title, , create=True, description='', privacy_status='private', service=None, \*\*cred_kwargs)

Return the id of the playlist titled `title`, creating it if missing.

Returns `None` only when the playlist is absent and `create=False`.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### yb.youtube.find_playlist(title, , service=None, \*\*cred_kwargs)

Return the id of the caller’s playlist titled `title` (or `None`).

Matches the first playlist with an exact title; YouTube allows duplicate
titles, so prefer unique playlist names.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)

### yb.youtube.flatten_video(resource)

Flatten a raw `videos.list` item into a friendly, typed, ordered dict.

Pure: pass the dict returned by the API. Missing pieces (from a partial
`part=` request, disabled stats, or an unauthorized dislike count) become
`None` rather than raising, so callers never have to guard the shape.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.get_credentials(, client_secrets_file=None, token_file=None, scopes=['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl'], open_browser=True, port=0, timeout_seconds=300.0, interactive=True)

Return OAuth user credentials, running the consent flow if needed.

First use runs the installed-app consent flow and caches the token to
`token_file` so later calls are non-interactive. Expired tokens are
refreshed automatically.

Pass `interactive=False` when nobody can answer a consent prompt — a cron
job, a queue worker, an agent. Consent is then never started; a token that
cannot be refreshed raises [`ConsentRequired`](#yb.youtube.ConsentRequired) naming the cause and the
fix. This is not an edge case: an OAuth client left in “Testing” rotates
refresh tokens out after about seven days, so anything scheduled hits it
weekly.

Even with the default `interactive=True` the call can no longer hang:
consent is bounded by `timeout_seconds`
(`DEFAULT_CONSENT_TIMEOUT_S`), and a timeout is reported as the same
[`ConsentRequired`](#yb.youtube.ConsentRequired), because “nobody answered” and “nobody could
answer” want the same thing done about them.

Consent always goes through a temporary local web server on `port` (`0`
picks a free one), because Google retired the copy-paste “out-of-band” flow
in 2022. `open_browser=False` only stops the browser from being launched:
the authorization URL is printed instead, and the redirect must still reach
that local server.

Headless recipe: pass `interactive=True` (there is no terminal, so the
default would refuse), `open_browser=False` and a fixed `port=`, then
forward that port from the machine holding the browser
(`ssh -L <port>:localhost:<port> <host>`). Nothing needs registering in
the Cloud console — the *Desktop app* client this module requires accepts
any `localhost` port, which is also why the `port=0` default works.

The call blocks until the redirect arrives, bounded by `timeout_seconds`
(default `DEFAULT_CONSENT_TIMEOUT_S`; pass `None` for the library’s
“wait indefinitely”, which is what this used to do).

These keywords ride `**cred_kwargs` through [`get_service()`](#yb.youtube.get_service) and the
publishing helpers. The few entry points that take none (notably
`yb.music.publish.publish_folder()`) still work headlessly: call this
once to mint the token, after which nothing prompts again.

### yb.youtube.get_service(, credentials=None, \*\*cred_kwargs)

Build a YouTube Data API v3 service object.

`cred_kwargs` are forwarded to [`get_credentials()`](#yb.youtube.get_credentials) (`token_file=`,
`open_browser=`, `port=`, …) unless `credentials` is given.

### yb.youtube.get_video(video_id, , part='snippet,status', service=None, \*\*cred_kwargs)

Fetch a video resource (raises `KeyError` if not found/visible).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.insert_caption(video_id, path, , language, name='', is_draft=False, service=None, \*\*cred_kwargs)

Insert a new caption track (`captions.insert`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.is_video_in_playlist(video_id, playlist_id, , service=None, \*\*cred_kwargs)

Whether `video_id` is already an item of `playlist_id` (paginated).

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### yb.youtube.list_captions(video_id, , service=None, \*\*cred_kwargs)

List caption tracks on a video (each item’s snippet has language/name/trackKind/status).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### yb.youtube.list_my_playlists(, service=None, \*\*cred_kwargs)

Return all playlists owned by the authenticated channel (paginated).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### yb.youtube.prepare_and_publish(media, \*, language='English', language_code=None, audio_language_code=None, brand=None, extra_context=None, with_chapters=True, with_thumbnail=True, privacy_status=None, playlist=<object object>, category_id='28', config=None, client_secrets_file=None, token_file=None, progress=True, \*\*cred_kwargs)

One call: prepare publication content from `media` and upload it.

Transcribes (persisting the SRT next to the media) if needed, writes
LLM metadata, detects chapters, renders a thumbnail, then uploads with
captions + thumbnail + chapters and adds the video to the configured
playlist. `privacy_status` and `playlist` default to your `yb` config
(see [`publish_content()`](#yb.youtube.publish_content)).

`cred_kwargs` reach [`get_credentials()`](yb.youtube.auth.html.md#yb.youtube.auth.get_credentials) (e.g.
`open_browser=False, port=8080` for headless consent).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.publish_content(content, \*, privacy_status=None, playlist=<object object>, category_id='28', with_chapters=True, attach_caption=True, set_thumb=True, config=None, client_secrets_file=None, token_file=None, progress=True, service=None, \*\*cred_kwargs)

Upload a prepared `PublicationContent` to YouTube.

Maps the content to a YouTube snippet (chapters embedded in the
description when present), uploads, attaches the SRT caption track
(language = `content.audio_language` or `content.language`) and the
thumbnail when available, and adds the video to the configured playlist.

`privacy_status` and `playlist` default to your `yb` config (see
[`yb.config`](yb.config.html.md#module-yb.config)): unset means “use the config value”, so privacy falls back
to `unlisted` and the video joins your configured playlist. Pass
`playlist=None` to skip the playlist for one call, or `playlist="Name"`
to override the target.

`cred_kwargs` reach [`get_credentials()`](yb.youtube.auth.html.md#yb.youtube.auth.get_credentials) (e.g.
`open_browser=False, port=8080` for headless consent).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
* **Returns:**
  `{"video_id", "url", "studio_url", "privacy_status", "captions",
  "thumbnail", "playlist"}`. `privacy_status` reflects what YouTube
  actually set (an unaudited project may force `"private"`); `playlist`
  is the [`add_video_to_playlist()`](yb.youtube.playlists.html.md#yb.youtube.playlists.add_video_to_playlist) result or
  `None`.

### yb.youtube.publish_video(video_path, metadata, \*, privacy_status=None, playlist=<object object>, captions=None, thumbnail=None, config=None, client_secrets_file=None, token_file=None, progress=True, service=None, \*\*cred_kwargs)

Lower-level upload: explicit [`VideoMetadata`](#yb.youtube.VideoMetadata) + caption tracks.

`privacy_status` and `playlist` default to your `yb` config (see
[`publish_content()`](#yb.youtube.publish_content)).

`cred_kwargs` reach [`get_credentials()`](yb.youtube.auth.html.md#yb.youtube.auth.get_credentials) (e.g.
`open_browser=False, port=8080` for headless consent).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.render_table(data, , fields=None)

Render metadata as an ASCII table.

A single flat dict renders as a two-column `field | value` table; a list
of flat dicts renders one row per video with `fields` as columns.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### yb.youtube.resolve_fields(, group=None, fields=None, available=None)

Resolve the ordered field list to show.

Precedence: explicit `fields` > named `group` > every `available`
field. An unknown `group` raises `KeyError` naming the valid options.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### yb.youtube.select_fields(flat, , group=None, fields=None)

Return an ordered subset of `flat` per `fields`/`group`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.set_chapters(video_id, chapters, , header='Chapters:', service=None, \*\*cred_kwargs)

Insert/replace a chapters block in the video’s description.

Strips any prior block under `header` and appends the new one. YouTube
renders interactive chapters when the first timestamp is `0:00`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.set_thumbnail(video_id, image_path, , service=None, \*\*cred_kwargs)

Set a custom thumbnail (`thumbnails.set`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.update_caption(caption_id, path, , is_draft=None, service=None, \*\*cred_kwargs)

Replace the content of an existing caption track (`captions.update`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.update_video(video_id, snippet, , service=None, \*\*cred_kwargs)

Update a video’s snippet (`videos.update`). `categoryId` is required.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.update_video_fields(video_id, , title=None, description=None, tags=None, category_id=None, default_language=None, default_audio_language=None, service=None, \*\*cred_kwargs)

Patch selected snippet fields, preserving the rest.

Fetches the current snippet, overlays the provided fields, and updates.
`categoryId` must be present (kept from the existing snippet if not given).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.upload_video(video_path, body, , service=None, chunksize=8388608, progress=True, \*\*cred_kwargs)

Resumably upload a video with the given `videos.insert` `body`.

Returns the created video resource (includes `id`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.upsert_caption(video_id, track, , language=None, name='', is_draft=False, replace=True, service=None, \*\*cred_kwargs)

Insert a caption track, or update the existing same-language one.

* **Parameters:**
  * **video_id** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Target video.
  * **track** ([`CaptionTrack`](yb.youtube.captions.html.md#yb.youtube.captions.CaptionTrack) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – A [`CaptionTrack`](#yb.youtube.CaptionTrack), or a path (then `language` required).
  * **replace** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – When an uploaded track in the same language exists, update it
    (`True`, default) rather than inserting a duplicate.
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
* **Returns:**
  The inserted/updated caption resource.

### yb.youtube.video_metadata(video_id, , group=None, fields=None, part='snippet,statistics,contentDetails,status', as_table=False, service=None, \*\*cred_kwargs)

Fetch a video’s live metadata & engagement numbers.

* **Parameters:**
  * **video_id** (`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]) – A single video id or an iterable of ids (batched, ≤50/call).
  * **group** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Name of a preset field set from `FIELD_GROUPS`
    (e.g. `"engagement"`). Ignored if `fields` is given.
  * **fields** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]) – Explicit ordered field names to keep (overrides `group`).
    With neither `group` nor `fields` you get every field.
  * **part** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – `videos.list` parts to request (default covers all fields).
  * **as_table** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – When `True`, return a ready-to-print ASCII table string
    instead of the dict/list.
  * **service** – An authenticated YouTube service; else built from
    `cred_kwargs` (e.g. `token_file=...`).
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)] | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  A flat `dict` for one id / `list[dict]` for many — or an ASCII
  table `str` when `as_table=True`.

### Modules

| [`api`](yb.youtube.api.html.md#module-yb.youtube.api)             | YouTube video operations: get, upload, update metadata, thumbnail, chapters.   |
|----------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`auth`](yb.youtube.auth.html.md#module-yb.youtube.auth)           | OAuth 2.0 plumbing for the YouTube Data API v3.                                |
| [`captions`](yb.youtube.captions.html.md#module-yb.youtube.captions)   | Caption (subtitle) tracks on YouTube videos: list, insert, update, upsert.     |
| [`metadata`](yb.youtube.metadata.html.md#module-yb.youtube.metadata)   | YouTube video metadata ↔ API snippet mapping.                                  |
| [`playlists`](yb.youtube.playlists.html.md#module-yb.youtube.playlists) | YouTube playlist operations: find/create a playlist and add videos to it.      |
| [`publish`](yb.youtube.publish.html.md#module-yb.youtube.publish)     | High-level YouTube publishing: prepare → upload → captions → thumbnail.        |
| [`stats`](yb.youtube.stats.html.md#module-yb.youtube.stats)         | Read live video metadata & engagement numbers from the YouTube Data API v3.    |
