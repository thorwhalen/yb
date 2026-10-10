# yb.youtube.api

YouTube video operations: get, upload, update metadata, thumbnail, chapters.

These wrap the YouTube Data API v3 `videos`/`thumbnails` resources for both
creating videos and *editing already-published ones* (titles, descriptions,
tags, languages, and chapter blocks in the description).

### Functions

| [`get_video`](#yb.youtube.api.get_video)(video_id, \*[, part, service])           | Fetch a video resource (raises `KeyError` if not found/visible).   |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`set_chapters`](#yb.youtube.api.set_chapters)(video_id, chapters, \*[, ...])        | Insert/replace a chapters block in the video's description.        |
| [`set_thumbnail`](#yb.youtube.api.set_thumbnail)(video_id, image_path, \*[, service]) | Set a custom thumbnail (`thumbnails.set`).                         |
| [`update_video`](#yb.youtube.api.update_video)(video_id, snippet, \*[, service])     | Update a video's snippet (`videos.update`).                        |
| [`update_video_fields`](#yb.youtube.api.update_video_fields)(video_id, \*[, title, ...])    | Patch selected snippet fields, preserving the rest.                |
| [`upload_video`](#yb.youtube.api.upload_video)(video_path, body, \*[, service, ...]) | Resumably upload a video with the given `videos.insert` `body`.    |

### yb.youtube.api.get_video(video_id, , part='snippet,status', service=None, \*\*cred_kwargs)

Fetch a video resource (raises `KeyError` if not found/visible).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.api.set_chapters(video_id, chapters, , header='Chapters:', service=None, \*\*cred_kwargs)

Insert/replace a chapters block in the video’s description.

Strips any prior block under `header` and appends the new one. YouTube
renders interactive chapters when the first timestamp is `0:00`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.api.set_thumbnail(video_id, image_path, , service=None, \*\*cred_kwargs)

Set a custom thumbnail (`thumbnails.set`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.api.update_video(video_id, snippet, , service=None, \*\*cred_kwargs)

Update a video’s snippet (`videos.update`). `categoryId` is required.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.api.update_video_fields(video_id, , title=None, description=None, tags=None, category_id=None, default_language=None, default_audio_language=None, service=None, \*\*cred_kwargs)

Patch selected snippet fields, preserving the rest.

Fetches the current snippet, overlays the provided fields, and updates.
`categoryId` must be present (kept from the existing snippet if not given).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.api.upload_video(video_path, body, , service=None, chunksize=8388608, progress=True, \*\*cred_kwargs)

Resumably upload a video with the given `videos.insert` `body`.

Returns the created video resource (includes `id`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
