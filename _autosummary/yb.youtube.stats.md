# yb.youtube.stats

Read live video metadata & engagement numbers from the YouTube Data API v3.

A read-only companion to [`yb.youtube.api`](yb.youtube.api.md#module-yb.youtube.api): fetch a flattened, typed,
human-friendly view of a video’s *live* numbers (views, likes, dislikes,
comments, …) together with content and status details — all in one request —
with optional field selection, named field **groups** (presets like
`"engagement"`), and an ASCII-table rendering for quick terminal reading.

Simple things simple:

```default
>>> from yb.youtube import video_metadata
>>> video_metadata("VIDEO_ID", group="engagement")
{'views': 666, 'likes': 11, 'dislikes': 0, 'comments': 0, ...}
```

Readable table for a terminal:

```default
>>> print(video_metadata("VIDEO_ID", group="engagement", as_table=True))
field              value
-----------------  -----
views                666
likes                 11
...
```

Pick exact fields and order, or compare several videos at once:

```default
>>> video_metadata("VIDEO_ID", fields=["title", "views", "likes"])
>>> print(video_metadata(["ID1", "ID2"], group="engagement", as_table=True))
```

#### NOTE
`dislikes` is only returned by the API to a video’s **owner**; for
other people’s videos it comes back as `None`. With no `group`/`fields` you
get every available field (“take whatever is there”).

### Module Attributes

| [`DEFAULT_PARTS`](#yb.youtube.stats.DEFAULT_PARTS)   | Parts fetched by default — everything a single `videos.list` call needs to populate the flattened fields below.   |
|------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| [`FIELD_GROUPS`](#yb.youtube.stats.FIELD_GROUPS)    | a group name -> the ordered fields it selects.                                                                    |

### Functions

| [`flatten_video`](#yb.youtube.stats.flatten_video)(resource)                            | Flatten a raw `videos.list` item into a friendly, typed, ordered dict.   |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [`render_table`](#yb.youtube.stats.render_table)(data, \*[, fields])                   | Render metadata as an ASCII table.                                       |
| [`resolve_fields`](#yb.youtube.stats.resolve_fields)(\*[, group, fields, available])     | Resolve the ordered field list to show.                                  |
| [`select_fields`](#yb.youtube.stats.select_fields)(flat, \*[, group, fields])           | Return an ordered subset of `flat` per `fields`/`group`.                 |
| [`video_metadata`](#yb.youtube.stats.video_metadata)(video_id, \*[, group, fields, ...]) | Fetch a video's live metadata & engagement numbers.                      |

### yb.youtube.stats.DEFAULT_PARTS *= 'snippet,statistics,contentDetails,status'*

Parts fetched by default — everything a single `videos.list` call needs to
populate the flattened fields below.

### yb.youtube.stats.FIELD_GROUPS *: [dict](https://docs.python.org/3/builtins/stdtypes.html#dict)[[str](https://docs.python.org/3/builtins/stdtypes.html#str), [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]]* *= {'content': ['duration', 'duration_seconds', 'definition', 'dimension', 'has_captions', 'has_custom_thumbnail', 'licensed_content', 'projection'], 'engagement': ['views', 'likes', 'dislikes', 'comments', 'favorites', 'like_view_pct', 'comment_view_pct'], 'identity': ['id', 'url', 'title', 'channel_title', 'channel_id', 'category_id', 'published_at'], 'overview': ['title', 'url', 'privacy', 'published_at', 'duration', 'views', 'likes', 'comments'], 'status': ['privacy', 'upload_status', 'made_for_kids', 'embeddable', 'license', 'public_stats_viewable']}*

a group name -> the ordered fields it selects. `"engagement"`
is the headline one (the live numbers); the rest are common practical cuts.

* **Type:**
  Named presets

### yb.youtube.stats.flatten_video(resource)

Flatten a raw `videos.list` item into a friendly, typed, ordered dict.

Pure: pass the dict returned by the API. Missing pieces (from a partial
`part=` request, disabled stats, or an unauthorized dislike count) become
`None` rather than raising, so callers never have to guard the shape.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.stats.render_table(data, , fields=None)

Render metadata as an ASCII table.

A single flat dict renders as a two-column `field | value` table; a list
of flat dicts renders one row per video with `fields` as columns.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### yb.youtube.stats.resolve_fields(, group=None, fields=None, available=None)

Resolve the ordered field list to show.

Precedence: explicit `fields` > named `group` > every `available`
field. An unknown `group` raises `KeyError` naming the valid options.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### yb.youtube.stats.select_fields(flat, , group=None, fields=None)

Return an ordered subset of `flat` per `fields`/`group`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### yb.youtube.stats.video_metadata(video_id, , group=None, fields=None, part='snippet,statistics,contentDetails,status', as_table=False, service=None, \*\*cred_kwargs)

Fetch a video’s live metadata & engagement numbers.

* **Parameters:**
  * **video_id** (`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]) – A single video id or an iterable of ids (batched, ≤50/call).
  * **group** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Name of a preset field set from [`FIELD_GROUPS`](#yb.youtube.stats.FIELD_GROUPS)
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
