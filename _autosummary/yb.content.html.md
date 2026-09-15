# yb.content

Target-agnostic publication content: prepare it once, publish anywhere.

A [`PublicationContent`](#yb.content.PublicationContent) bundles everything a publication needs that is
*not* specific to a destination — title, description, keywords, chapters,
languages, and the media/transcript/thumbnail assets. Platform adapters
(`yb.youtube`, `yb.podcast`) consume it and map it to their own schema.

The heavy lifting (transcription, chapter detection, thumbnail rendering) is
delegated to the `mixing` package; the copywriting (title/description/
keywords) is LLM-backed via `aix` and pluggable.

### Functions

| [`format_chapter_lines`](#yb.content.format_chapter_lines)(chapters)                     | Render chapters as `M:SS Title` lines (the shared text convention).                                             |
|-----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| [`generate_metadata`](#yb.content.generate_metadata)(transcript, \*[, language, ...]) | Generate platform-neutral title/description/keywords from a transcript.                                         |
| [`prepare_content`](#yb.content.prepare_content)(media, \*[, language, ...])        | Build a [`PublicationContent`](#yb.content.PublicationContent) for `media` (destination-agnostic). |

### Classes

| [`ContentMetadata`](#yb.content.ContentMetadata)(title, description[, keywords])   | Platform-neutral copy: a title, a description, and keywords.         |
|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`PublicationContent`](#yb.content.PublicationContent)(media[, title, ...])           | Everything needed to publish a piece of media, destination-agnostic. |

### *class* yb.content.ContentMetadata(title, description, keywords=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Platform-neutral copy: a title, a description, and keywords.

### *class* yb.content.PublicationContent(media, title='', description='', keywords=<factory>, chapters=<factory>, language=None, audio_language=None, srt_path=None, thumbnail=None, duration=None)

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

### yb.content.format_chapter_lines(chapters)

Render chapters as `M:SS Title` lines (the shared text convention).

Uses `H:MM:SS` when any chapter is at or beyond one hour. This is the
text format both YouTube descriptions and podcast show notes accept.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### yb.content.generate_metadata(transcript, , language='English', brand=None, extra_context=None, model=None)

Generate platform-neutral title/description/keywords from a transcript.

LLM-backed via `aix`. Pass a ready [`ContentMetadata`](#yb.content.ContentMetadata) to
[`prepare_content()`](#yb.content.prepare_content) instead if you want to skip generation.

* **Raises:**
  [**ImportError**](https://docs.python.org/3/builtins/exceptions.html#ImportError) – `aix` is not importable.
* **Return type:**
  [`ContentMetadata`](#yb.content.ContentMetadata)

### yb.content.prepare_content(media, , language='English', language_code=None, audio_language_code=None, brand=None, extra_context=None, transcript=None, with_chapters=True, with_thumbnail=False, thumbnail_text=None, metadata=None, model=None, transcribe_kwargs=None, chapters_kwargs=None)

Build a [`PublicationContent`](#yb.content.PublicationContent) for `media` (destination-agnostic).

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
  * **metadata** ([`ContentMetadata`](#yb.content.ContentMetadata) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Precomputed [`ContentMetadata`](#yb.content.ContentMetadata) to reuse.
  * **model** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – LLM model override.
  * **chapters_kwargs** ([`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Forwarded to the mixing calls.
* **Return type:**
  [`PublicationContent`](#yb.content.PublicationContent)
* **Returns:**
  A populated [`PublicationContent`](#yb.content.PublicationContent).
