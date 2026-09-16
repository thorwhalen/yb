# yb.youtube.search

Search YouTube for videos, with engagement numbers to rank them by.

A read-only companion to [`yb.youtube.stats`](yb.youtube.stats.html.md#module-yb.youtube.stats): that module tells you about a
video you already know; this one finds the videos.

Simple things simple:

```default
>>> from yb.youtube import search_videos
>>> for v in search_videos("prime factorisation", max_results=3):
...     print(v["views"], v["title"])
```

Two backends, because the obvious one is not always available:

`"api"`
: The official Data API `search.list`. Costs 100 quota units per call out of
  a default 10 000/day, so roughly 100 searches. Needs `GOOGLE_API_KEY` *and*
  YouTube Data API v3 enabled on that key’s Cloud project.

`"scrape"`
: Reads the public results page and pulls the same public fields out of the
  `ytInitialData` blob the page ships to render itself. No key, no quota. It
  depends on a page layout Google can change, so it is the fallback, not the
  default — and it is for occasional personal use, not bulk collection.

`backend="auto"` (the default) uses the API when it can and falls back
otherwise, telling you which it used in each result’s `source` field, so a
silently degraded search is never mistaken for a good one.

Search results carry no engagement numbers on either backend. Pass
`with_stats=True` to fill in `views`/`likes`/`comments` — one extra
batched call per 50 videos on the API backend (1 quota unit), or one page fetch
per video when scraping.

**What each backend can actually tell you about engagement** (measured, not
assumed): the API gives views, likes and comments. The scrape gives \*\*views
only\*\* – YouTube no longer ships the like count in the watch page HTML for a
signed-out request, so `likes` comes back `None` there rather than wrong.
[`rank_by_engagement()`](#yb.youtube.search.rank_by_engagement) degrades to ranking on reach alone when likes are
missing; enabling the Data API is what makes approval-weighted ranking possible.

### Module Attributes

| [`WATCH_URL`](#yb.youtube.search.WATCH_URL)           | Where a video lives, and the thumbnail YouTube always serves for it.   |
|----------------------------------------------------------------------|------------------------------------------------------------------------|
| [`THUMBNAIL_QUALITIES`](#yb.youtube.search.THUMBNAIL_QUALITIES) | Thumbnail sizes YouTube serves for every video without an API call.    |

### Functions

| [`add_stats`](#yb.youtube.search.add_stats)(videos, \*[, api_key, backend])        | Fill in engagement numbers on search results, in place-ish (returns them).   |
|---------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`api_available`](#yb.youtube.search.api_available)(\*[, api_key])                     | Whether the Data API can actually be called with the key we have.            |
| [`rank_by_engagement`](#yb.youtube.search.rank_by_engagement)(videos, \*[, min_views, ...]) | Order videos by a like-rate-and-reach score.                                 |
| [`search_videos`](#yb.youtube.search.search_videos)(query, \*[, max_results, ...])     | Search YouTube and return a list of video records.                           |
| [`thumbnail_url`](#yb.youtube.search.thumbnail_url)(video_id, \*[, quality])           | Thumbnail URL for a video.                                                   |
| `watch_url`(video_id)                                                                             |                                                                              |

### yb.youtube.search.THUMBNAIL_QUALITIES *= ('default', 'mqdefault', 'hqdefault', 'sddefault', 'maxresdefault')*

Thumbnail sizes YouTube serves for every video without an API call.

### yb.youtube.search.WATCH_URL *= 'https://www.youtube.com/watch?v={video_id}'*

Where a video lives, and the thumbnail YouTube always serves for it.

### yb.youtube.search.add_stats(videos, , api_key=None, backend='auto')

Fill in engagement numbers on search results, in place-ish (returns them).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)

### yb.youtube.search.api_available(, api_key=None)

Whether the Data API can actually be called with the key we have.

A key that exists is not a key that works: the API has to be enabled on its
Cloud project too, and that failure is a 403 at call time rather than
anything visible up front.

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### yb.youtube.search.rank_by_engagement(videos, , min_views=0, like_weight=1.0, view_weight=1.0)

Order videos by a like-rate-and-reach score.

Raw view count alone rewards age and luck, and like count alone rewards the
same. The score multiplies *reach* (log views, so an order of magnitude
counts for a fixed amount) by *approval* (likes per thousand views), which
ranks a well-liked mid-sized video above a big indifferent one. Videos
missing numbers sort last rather than being dropped, since absent is not the
same as bad.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)

### yb.youtube.search.search_videos(query, , max_results=10, backend='auto', with_stats=False, api_key=None, language=None, region=None, \*\*params)

Search YouTube and return a list of video records.

`language`/`region` bias results (`"en"`, `"GB"`) rather than filter
them — YouTube offers no hard language filter. Check what comes back if the
language matters; a title can be auto-translated by the interface, which
makes an English video look like a local one.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)

### yb.youtube.search.thumbnail_url(video_id, , quality='mqdefault')

Thumbnail URL for a video. Always available, no API call, no key.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
