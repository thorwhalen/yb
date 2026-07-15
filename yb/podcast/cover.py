"""Cover-over-audio video: turn a podcast audio file into a simple video.

Useful for publishing an audio episode where a video is expected (YouTube): the
cover image, held for the episode's duration, muxed with the audio — optionally
with a slow Ken Burns pan/zoom.

This is a thin adapter over :mod:`muvid.visualize`, which owns the audio→video
rendering. Reach for :func:`muvid.visualize.render_audio_video` directly when you
want a visual other than a held cover, a burnt-in title, or loudness
normalization. Needs ``pip install 'yb[music]'`` (pulls ``muvid``).
"""

from __future__ import annotations

from pathlib import Path

try:
    from muvid.visualize import (
        DEFAULT_FPS,
        DEFAULT_SIZE,
        CoverLayout,
        PathLike,
        render_audio_video,
    )
except ImportError as e:  # pragma: no cover - environment dependent
    raise ImportError(
        "yb.podcast.cover needs the 'muvid' package for rendering "
        "(pip install 'yb[music]')."
    ) from e


def cover_video(
    audio: PathLike,
    image: PathLike,
    *,
    saveas: PathLike | None = None,
    ken_burns: bool = False,
    size: tuple[int, int] = DEFAULT_SIZE,
    fps: int = DEFAULT_FPS,
    layout: CoverLayout | None = None,
) -> Path:
    """Render a video of ``image`` held over ``audio``.

    The cover is composed onto a 16:9 canvas — filled with a blurred, darkened
    copy of itself rather than black bars — so square or portrait art still
    looks deliberate at 1080p.

    Args:
        audio: The episode audio file.
        image: Cover image to display.
        saveas: Output path (defaults to ``<audio-stem>.cover.mp4``).
        ken_burns: Apply a slow pan/zoom (rendered by ``burns``) instead of a
            static image. Much slower than the static path.
        size: Output resolution (width, height).
        fps: Output frame rate.
        layout: How the cover sits on the canvas.

    Returns:
        Path to the rendered mp4.

    Raises:
        ImportError: ``ken_burns=True`` but the ``burns`` renderer is absent.
        FfmpegError: ffmpeg is missing, or the render failed.
    """
    audio = Path(audio)
    out = Path(saveas) if saveas else audio.with_suffix(".cover.mp4")
    result = render_audio_video(
        audio,
        image,
        visual="ken_burns" if ken_burns else "still",
        saveas=out,
        size=size,
        fps=fps,
        layout=layout,
    )
    return result.path
