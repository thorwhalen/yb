# yb.audio_convert

Convert audio files between formats with ffmpeg.

Audio arrives in whatever format the source offers — YouTube’s best audio is
typically Opus in a `.webm` container — which is usually fine to keep as is.
Publishing paths, though, often want something specific: `.mp3` for podcast
players, `.wav` for editing. [`convert_audio()`](#yb.audio_convert.convert_audio) is the one-call bridge:

```pycon
>>> from yb.audio_convert import convert_audio
>>> convert_audio("talk.webm", "mp3")
PosixPath('talk.mp3')
```

Conversion is a **no-op when the source is already in the target format**, so it
is safe to call unconditionally:

```pycon
>>> convert_audio("talk.mp3", "mp3")
PosixPath('talk.mp3')
```

Requires `ffmpeg` on `PATH`; without it [`AudioConversionError`](#yb.audio_convert.AudioConversionError) is
raised (see also the `on_error="warn"` escape hatch in
[`yb.download.download_youtube_audio()`](yb.download.html.md#yb.download.download_youtube_audio)).

### Module Attributes

| [`LOSSLESS_FORMATS`](#yb.audio_convert.LOSSLESS_FORMATS)      | Formats that store samples losslessly — a target bitrate is meaningless there.   |
|------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`DEFAULT_LOSSY_BITRATE`](#yb.audio_convert.DEFAULT_LOSSY_BITRATE) | Bitrate applied to lossy targets when the caller doesn't specify one.            |

### Functions

| [`convert_audio`](#yb.audio_convert.convert_audio)(src, audio_format, \*[, ...])   | Convert `src` to `audio_format`, returning the resulting path.   |
|------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| [`normalize_format`](#yb.audio_convert.normalize_format)(audio_format)                | Normalize a format spec to a bare lowercase extension.           |

### Exceptions

| [`AudioConversionError`](#yb.audio_convert.AudioConversionError)   | Raised when audio could not be converted to the requested format.   |
|-------------------------------------------------------------------------|---------------------------------------------------------------------|

### *exception* yb.audio_convert.AudioConversionError

Bases: [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

Raised when audio could not be converted to the requested format.

### yb.audio_convert.DEFAULT_LOSSY_BITRATE *= '192k'*

Bitrate applied to lossy targets when the caller doesn’t specify one.

### yb.audio_convert.LOSSLESS_FORMATS *= frozenset({'aif', 'aiff', 'alac', 'flac', 'wav'})*

Formats that store samples losslessly — a target bitrate is meaningless there.

### yb.audio_convert.convert_audio(src, audio_format, , output=None, bitrate=None, overwrite=True, extra_ffmpeg_args=())

Convert `src` to `audio_format`, returning the resulting path.

* **Parameters:**
  * **src** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – The audio file to convert.
  * **audio_format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Target format as an extension (`"mp3"`, `".wav"`, …).
  * **output** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Destination path. Defaults to `src` with the new extension.
  * **bitrate** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)) – Target bitrate for lossy formats (e.g. `"320k"`). Defaults to
    [`DEFAULT_LOSSY_BITRATE`](#yb.audio_convert.DEFAULT_LOSSY_BITRATE); ignored for [`LOSSLESS_FORMATS`](#yb.audio_convert.LOSSLESS_FORMATS).
  * **overwrite** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Overwrite `output` if it already exists.
  * **extra_ffmpeg_args** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Raw ffmpeg arguments, appended last so they win.
* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)
* **Returns:**
  The converted file’s path — or `src` unchanged when it is already in
  the target format (no pointless re-encode, no generation loss).
* **Raises:**
  * [**FileNotFoundError**](https://docs.python.org/3/builtins/exceptions.html#FileNotFoundError) – If `src` does not exist.
  * [**AudioConversionError**](#yb.audio_convert.AudioConversionError) – If ffmpeg is missing, or the conversion fails.

### yb.audio_convert.normalize_format(audio_format)

Normalize a format spec to a bare lowercase extension.

Accepts it with or without the leading dot, in any case:

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> normalize_format("mp3"), normalize_format(".MP3"), normalize_format(" .Wav ")
('mp3', 'mp3', 'wav')
```
