# yb.podcast

Podcast publishing: show notes, chapters, cover video, and RSS.

Optionally installed (`pip install 'yb[podcast]'`). Consumes the same
platform-neutral [`yb.content.PublicationContent`](yb.content.html.md#yb.content.PublicationContent) as the YouTube adapter.

```pycon
>>> from yb.podcast import prepare_podcast_episode
>>> ep = prepare_podcast_episode("episode.mp3", "out/", cover_image="cover.jpg")
>>> print(ep.show_notes, ep.chapters_psc)
```

### Functions

| [`format_show_notes`](#yb.podcast.format_show_notes)(content, \*[, include_chapters])   | Render show notes (title + description + optional chapters) as text.   |
|-------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| [`psc_xml`](#yb.podcast.psc_xml)(chapters)                                    | Render chapters as a Podlove Simple Chapters (PSC) XML document.       |
| [`write_psc`](#yb.podcast.write_psc)(chapters, path)                            | Write a PSC XML sidecar to `path`.                                     |
| [`write_id3_chapters`](#yb.podcast.write_id3_chapters)(mp3_path, chapters, \*[, ...])    | Embed ID3v2 chapter frames (`CHAP` + `CTOC`) into an MP3 file.         |
| [`cover_video`](#yb.podcast.cover_video)(audio, image, \*[, saveas, ...])         | Render a video of `image` held over `audio`.                           |
| [`build_feed`](#yb.podcast.build_feed)(channel, episodes)                        | Build podcast RSS XML for `channel` and its `episodes`.                |
| [`prepare_podcast_episode`](#yb.podcast.prepare_podcast_episode)(media, output_dir, \*)       | Build a podcast episode bundle from `media` into `output_dir`.         |

### Classes

| [`PodcastChannel`](#yb.podcast.PodcastChannel)(title, link, description, ...)   | Podcast-level (show) metadata.         |
|--------------------------------------------------------------------------------------------------|----------------------------------------|
| [`EpisodeFeedItem`](#yb.podcast.EpisodeFeedItem)(title, description, ...[, ...]) | One episode's feed entry.              |
| [`PodcastEpisode`](#yb.podcast.PodcastEpisode)(audio, show_notes[, ...])        | Paths to the generated episode assets. |

### *class* yb.podcast.EpisodeFeedItem(title, description, audio_url, audio_length_bytes, pubdate, guid=None, audio_mime='audio/mpeg', duration_seconds=None, image_url=None, chapters_url=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One episode’s feed entry.

### *class* yb.podcast.PodcastChannel(title, link, description, author, email, image_url=None, language='en', categories=<factory>, explicit=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Podcast-level (show) metadata.

### *class* yb.podcast.PodcastEpisode(audio, show_notes, chapters_psc=None, chapters_json=None, cover_video=None, content=None, extras=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Paths to the generated episode assets.

### yb.podcast.build_feed(channel, episodes)

Build podcast RSS XML for `channel` and its `episodes`.

* **Raises:**
  [**ImportError**](https://docs.python.org/3/builtins/exceptions.html#ImportError) – `feedgen` is not installed (`pip install 'yb[podcast]'`).
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### yb.podcast.cover_video(audio, image, , saveas=None, ken_burns=False, size=None, fps=None, layout=None)

Render a video of `image` held over `audio`.

The cover is composed onto a 16:9 canvas — filled with a blurred, darkened
copy of itself rather than black bars — so square or portrait art still
looks deliberate at 1080p.

* **Parameters:**
  * **audio** (PathLike) – The episode audio file.
  * **image** (PathLike) – Cover image to display.
  * **saveas** (PathLike | None) – Output path (defaults to `<audio-stem>.cover.mp4`).
  * **ken_burns** (bool) – Apply a slow pan/zoom (rendered by `burns`) instead of a
    static image. Much slower than the static path.
  * **size** (tuple[int, int] | None) – Output resolution (width, height); defaults to 1080p.
  * **fps** (int | None) – Output frame rate; defaults to muvid’s default.
  * **layout** (CoverLayout | None) – How the cover sits on the canvas.
* **Return type:**
  Path
* **Returns:**
  Path to the rendered mp4.
* **Raises:**
  * [**ImportError**](https://docs.python.org/3/builtins/exceptions.html#ImportError) – the `muvid` package is not installed (`pip install
        'yb[music]'`).
  * **FfmpegError** – ffmpeg is missing, or the render failed.

### yb.podcast.format_show_notes(content, , include_chapters=True)

Render show notes (title + description + optional chapters) as text.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### yb.podcast.prepare_podcast_episode(media, output_dir, , content=None, audio=None, cover_image=None, make_cover_video=False, ken_burns=False, embed_chapters=True, language='English', brand=None, extra_context=None, audio_bitrate='192k')

Build a podcast episode bundle from `media` into `output_dir`.

* **Parameters:**
  * **media** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – Source audio or video.
  * **output_dir** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – Directory to write the episode assets into.
  * **content** ([`PublicationContent`](yb.content.html.md#yb.content.PublicationContent) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Precomputed `PublicationContent`; built via
    [`yb.content.prepare_content()`](yb.content.html.md#yb.content.prepare_content) when omitted.
  * **audio** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Explicit episode audio. When omitted, `media` is used if it is
    audio, else its audio track is extracted to MP3.
  * **cover_image** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Cover art (required for `make_cover_video`).
  * **make_cover_video** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also render a cover-over-audio mp4 (e.g. for YouTube).
  * **ken_burns** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Apply a Ken Burns pan/zoom to the cover video.
  * **embed_chapters** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Embed ID3 chapter frames into the episode MP3.
  * **extra_context** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Forwarded to `prepare_content`.
  * **audio_bitrate** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Bitrate for extracted MP3 audio.
* **Return type:**
  [`PodcastEpisode`](yb.podcast.publish.html.md#yb.podcast.publish.PodcastEpisode)
* **Returns:**
  A [`PodcastEpisode`](#yb.podcast.PodcastEpisode) with the asset paths.

### yb.podcast.psc_xml(chapters)

Render chapters as a Podlove Simple Chapters (PSC) XML document.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### yb.podcast.write_id3_chapters(mp3_path, chapters, , duration=None, toc_id='toc')

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

### yb.podcast.write_psc(chapters, path)

Write a PSC XML sidecar to `path`.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### Modules

| [`chapters`](yb.podcast.chapters.html.md#module-yb.podcast.chapters)   | Podcast chapter markers: Podlove Simple Chapters (PSC) + MP3 ID3 chapters.   |
|----------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`cover`](yb.podcast.cover.html.md#module-yb.podcast.cover)         | Cover-over-audio video: turn a podcast audio file into a simple video.       |
| [`feed`](yb.podcast.feed.html.md#module-yb.podcast.feed)           | Podcast RSS feed generation (iTunes-compatible) via feedgen.                 |
| [`publish`](yb.podcast.publish.html.md#module-yb.podcast.publish)     | Assemble a publishable podcast episode from a media file.                    |
| [`shownotes`](yb.podcast.shownotes.html.md#module-yb.podcast.shownotes) | Podcast show notes — the human-readable episode description block.           |
