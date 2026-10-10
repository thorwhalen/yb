# yb.podcast.chapters

Podcast chapter markers: Podlove Simple Chapters (PSC) + MP3 ID3 chapters.

Two standards cover most podcast players:

- **PSC** — an XML sidecar (`<psc:chapters>`) referenced from the RSS feed.
- **ID3 chapters** — `CHAP`/`CTOC` frames embedded directly in the MP3, so
  chapters travel with the file (Apple Podcasts, Overcast, etc.).

Both are derived from the same platform-neutral `mixing.chapters.Chapter` list.

### Functions

| [`psc_xml`](#yb.podcast.chapters.psc_xml)(chapters)                                 | Render chapters as a Podlove Simple Chapters (PSC) XML document.   |
|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`write_id3_chapters`](#yb.podcast.chapters.write_id3_chapters)(mp3_path, chapters, \*[, ...]) | Embed ID3v2 chapter frames (`CHAP` + `CTOC`) into an MP3 file.     |
| [`write_psc`](#yb.podcast.chapters.write_psc)(chapters, path)                         | Write a PSC XML sidecar to `path`.                                 |

### yb.podcast.chapters.psc_xml(chapters)

Render chapters as a Podlove Simple Chapters (PSC) XML document.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### yb.podcast.chapters.write_id3_chapters(mp3_path, chapters, , duration=None, toc_id='toc')

Embed ID3v2 chapter frames (`CHAP` + `CTOC`) into an MP3 file.

* **Parameters:**
  * **mp3_path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – The MP3 to modify in place.
  * **chapters** ([`Sequence`](https://docs.python.org/3/library/typing.html#typing.Sequence)[`Chapter`]) – Ordered chapter markers.
  * **duration** ([`float`](https://docs.python.org/3/builtins/functions.html#float) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Total media duration (s) — used as the last chapter’s end.
    Inferred from the file when omitted.
  * **toc_id** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Element id for the table-of-contents frame.
* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
* **Returns:**
  The path written.
* **Raises:**
  [**ImportError**](https://docs.python.org/3/builtins/exceptions.html#ImportError) – `mutagen` is not installed (`pip install 'yb[podcast]'`).

### yb.podcast.chapters.write_psc(chapters, path)

Write a PSC XML sidecar to `path`.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
