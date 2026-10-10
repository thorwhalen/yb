# yb.youtube.publish

High-level YouTube publishing: prepare → upload → captions → thumbnail.

Two entry points:

> - [`publish_content()`](#yb.youtube.publish.publish_content) — given a prepared
>   [`yb.content.PublicationContent`](yb.content.md#yb.content.PublicationContent), upload it with captions,
>   > thumbnail, and chapters (in the description).
> - [`prepare_and_publish()`](#yb.youtube.publish.prepare_and_publish) — the one-call path: transcribe/derive
>   metadata/detect chapters (via [`yb.content.prepare_content()`](yb.content.md#yb.content.prepare_content)) and
>   upload, all from a media path.

### Functions

| [`prepare_and_publish`](#yb.youtube.publish.prepare_and_publish)(media, \*[, language, ...])   | One call: prepare publication content from `media` and upload it.   |
|----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| [`publish_content`](#yb.youtube.publish.publish_content)(content, \*[, ...])               | Upload a prepared `PublicationContent` to YouTube.                  |
| [`publish_video`](#yb.youtube.publish.publish_video)(video_path, metadata, \*[, ...])    | Lower-level upload: explicit `VideoMetadata` + caption tracks.      |

### yb.youtube.publish.prepare_and_publish(media, \*, language='English', language_code=None, audio_language_code=None, brand=None, extra_context=None, with_chapters=True, with_thumbnail=True, privacy_status=None, playlist=<object object>, category_id='28', config=None, client_secrets_file=None, token_file=None, progress=True, \*\*cred_kwargs)

One call: prepare publication content from `media` and upload it.

Transcribes (persisting the SRT next to the media) if needed, writes
LLM metadata, detects chapters, renders a thumbnail, then uploads with
captions + thumbnail + chapters and adds the video to the configured
playlist. `privacy_status` and `playlist` default to your `yb` config
(see [`publish_content()`](#yb.youtube.publish.publish_content)).

`cred_kwargs` reach [`get_credentials()`](yb.youtube.auth.md#yb.youtube.auth.get_credentials) (e.g.
`open_browser=False, port=8080` for headless consent).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.publish.publish_content(content, \*, privacy_status=None, playlist=<object object>, category_id='28', with_chapters=True, attach_caption=True, set_thumb=True, config=None, client_secrets_file=None, token_file=None, progress=True, service=None, \*\*cred_kwargs)

Upload a prepared `PublicationContent` to YouTube.

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

### yb.youtube.publish.publish_video(video_path, metadata, \*, privacy_status=None, playlist=<object object>, captions=None, thumbnail=None, config=None, client_secrets_file=None, token_file=None, progress=True, service=None, \*\*cred_kwargs)

Lower-level upload: explicit `VideoMetadata` + caption tracks.

`privacy_status` and `playlist` default to your `yb` config (see
[`publish_content()`](#yb.youtube.publish.publish_content)).

`cred_kwargs` reach [`get_credentials()`](yb.youtube.auth.md#yb.youtube.auth.get_credentials) (e.g.
`open_browser=False, port=8080` for headless consent).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
