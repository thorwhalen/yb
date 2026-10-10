# yb.podcast.cover

Cover-over-audio video: turn a podcast audio file into a simple video.

Useful for publishing an audio episode where a video is expected (YouTube): the
cover image, held for the episode’s duration, muxed with the audio — optionally
with a slow Ken Burns pan/zoom.

This is a thin adapter over `muvid.visualize`, which owns the audio→video
rendering. Reach for `muvid.visualize.render_audio_video()` directly when you
want a visual other than a held cover, a burnt-in title, or loudness
normalization. Needs `pip install 'yb[music]'` (pulls `muvid`).

### Functions

| [`cover_video`](#yb.podcast.cover.cover_video)(audio, image, \*[, saveas, ...])   | Render a video of `image` held over `audio`.   |
|-------------------------------------------------------------------------------------------------|------------------------------------------------|

### yb.podcast.cover.cover_video(audio, image, , saveas=None, ken_burns=False, size=None, fps=None, layout=None)

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
