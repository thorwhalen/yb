# yb.youtube.captions

Caption (subtitle) tracks on YouTube videos: list, insert, update, upsert.

Lets you attach an SRT/VTT track at upload time *and* manage tracks on
already-published videos — e.g. replace a hand-edited subtitle file, or add a
track in a new language. `upsert_caption` is the convenient default: it
updates an existing same-language track if present, else inserts a new one.

#### NOTE
YouTube auto-generates ASR tracks of its own (`trackKind="asr"`);
these helpers operate on uploaded `"standard"` tracks and ignore ASR.

### Functions

| [`delete_caption`](#yb.youtube.captions.delete_caption)(caption_id, \*[, service])         | Delete a caption track (`captions.delete`).                                              |
|----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| [`download_caption`](#yb.youtube.captions.download_caption)(caption_id, \*[, tfmt, service]) | Download a caption track's content (`captions.download`), default SRT.                   |
| [`insert_caption`](#yb.youtube.captions.insert_caption)(video_id, path, \*, language)      | Insert a new caption track (`captions.insert`).                                          |
| [`list_captions`](#yb.youtube.captions.list_captions)(video_id, \*[, service])            | List caption tracks on a video (each item's snippet has language/name/trackKind/status). |
| [`update_caption`](#yb.youtube.captions.update_caption)(caption_id, path, \*[, ...])       | Replace the content of an existing caption track (`captions.update`).                    |
| [`upsert_caption`](#yb.youtube.captions.upsert_caption)(video_id, track, \*[, ...])        | Insert a caption track, or update the existing same-language one.                        |

### Classes

| [`CaptionTrack`](#yb.youtube.captions.CaptionTrack)(path, language[, name, is_draft])   | A caption track to attach to a video.   |
|---------------------------------------------------------------------------------------------------|-----------------------------------------|

### *class* yb.youtube.captions.CaptionTrack(path, language, name='', is_draft=False)

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

### yb.youtube.captions.delete_caption(caption_id, , service=None, \*\*cred_kwargs)

Delete a caption track (`captions.delete`).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### yb.youtube.captions.download_caption(caption_id, , tfmt='srt', service=None, \*\*cred_kwargs)

Download a caption track’s content (`captions.download`), default SRT.

* **Return type:**
  [`bytes`](https://docs.python.org/3/builtins/stdtypes.html#bytes)

### yb.youtube.captions.insert_caption(video_id, path, , language, name='', is_draft=False, service=None, \*\*cred_kwargs)

Insert a new caption track (`captions.insert`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.captions.list_captions(video_id, , service=None, \*\*cred_kwargs)

List caption tracks on a video (each item’s snippet has language/name/trackKind/status).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### yb.youtube.captions.update_caption(caption_id, path, , is_draft=None, service=None, \*\*cred_kwargs)

Replace the content of an existing caption track (`captions.update`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.captions.upsert_caption(video_id, track, , language=None, name='', is_draft=False, replace=True, service=None, \*\*cred_kwargs)

Insert a caption track, or update the existing same-language one.

* **Parameters:**
  * **video_id** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Target video.
  * **track** ([`CaptionTrack`](#yb.youtube.captions.CaptionTrack) | [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – A [`CaptionTrack`](#yb.youtube.captions.CaptionTrack), or a path (then `language` required).
  * **replace** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – When an uploaded track in the same language exists, update it
    (`True`, default) rather than inserting a duplicate.
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
* **Returns:**
  The inserted/updated caption resource.
