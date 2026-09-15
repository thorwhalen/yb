# yb.podcast.publish

Assemble a publishable podcast episode from a media file.

Produces the per-episode asset bundle in an output directory: an MP3 (with
ID3 chapters embedded), show-notes text, a PSC chapter sidecar, a chapters
JSON, and optionally a cover-over-audio video for video platforms. Delivery to
a host/Spotify is via RSS ([`yb.podcast.feed`](yb.podcast.feed.html.md#module-yb.podcast.feed)) — this prepares the assets
and a ready-to-use [`yb.podcast.feed.EpisodeFeedItem`](yb.podcast.feed.html.md#yb.podcast.feed.EpisodeFeedItem) stub.

### Functions

| [`prepare_podcast_episode`](#yb.podcast.publish.prepare_podcast_episode)(media, output_dir, \*)   | Build a podcast episode bundle from `media` into `output_dir`.   |
|---------------------------------------------------------------------------------------------------|------------------------------------------------------------------|

### Classes

| [`PodcastEpisode`](#yb.podcast.publish.PodcastEpisode)(audio, show_notes[, ...])   | Paths to the generated episode assets.   |
|---------------------------------------------------------------------------------------------|------------------------------------------|

### *class* yb.podcast.publish.PodcastEpisode(audio, show_notes, chapters_psc=None, chapters_json=None, cover_video=None, content=None, extras=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Paths to the generated episode assets.

### yb.podcast.publish.prepare_podcast_episode(media, output_dir, , content=None, audio=None, cover_image=None, make_cover_video=False, ken_burns=False, embed_chapters=True, language='English', brand=None, extra_context=None, audio_bitrate='192k')

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
  [`PodcastEpisode`](#yb.podcast.publish.PodcastEpisode)
* **Returns:**
  A [`PodcastEpisode`](#yb.podcast.publish.PodcastEpisode) with the asset paths.
