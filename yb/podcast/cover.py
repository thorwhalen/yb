"""Cover-over-audio video: turn a podcast audio file into a simple video.

Useful for publishing an audio episode where a video is expected (YouTube): the
cover image, held for the episode's duration, muxed with the audio — optionally
with a slow Ken Burns pan/zoom.

This is a thin adapter over :mod:`yb.render`, which owns the rendering for both
podcasts and music. Reach for :func:`yb.render.render_audio_video` directly when
you want a visual other than a held cover, a burnt-in title, or loudness
normalization.
"""

from __future__ import annotations

from pathlib import Path

from yb.render.canvas import DEFAULT_SIZE, CoverLayout
from yb.render.ffmpeg import PathLike
from yb.render.video import DEFAULT_FPS, render_audio_video


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
