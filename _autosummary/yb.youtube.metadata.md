# yb.youtube.metadata

YouTube video metadata ↔ API snippet mapping.

Maps the platform-neutral [`yb.content.PublicationContent`](yb.content.md#yb.content.PublicationContent) onto a
YouTube `videos.insert` body, applying YouTube’s field limits (title <= 100
chars, description <= 5000, tags combined <= 500) and embedding the chapters
block into the description (YouTube renders chapters from description
timestamps when the first is `0:00`).

### Module Attributes

| [`CATEGORY_SCIENCE_TECH`](#yb.youtube.metadata.CATEGORY_SCIENCE_TECH)   | A useful subset of YouTube video category ids.   |
|--------------------------------------------------------------------------|--------------------------------------------------|

### Classes

| [`VideoMetadata`](#yb.youtube.metadata.VideoMetadata)(title, description[, tags, ...])   | YouTube-specific video metadata.   |
|---------------------------------------------------------------------------------------------------|------------------------------------|

### yb.youtube.metadata.CATEGORY_SCIENCE_TECH *= '28'*

A useful subset of YouTube video category ids.

### *class* yb.youtube.metadata.VideoMetadata(title, description, tags=<factory>, category_id='28', default_language=None, default_audio_language=None, contains_synthetic_media=None)

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
  [`VideoMetadata`](#yb.youtube.metadata.VideoMetadata)

#### insert_body(, privacy_status='unlisted')

Build the `videos.insert` body (snippet + status).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

#### update_snippet()

Build the snippet for `videos.update` (categoryId is required).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
