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
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # annotations only; the real import is lazy (see _render)
    from muvid.visualize import CoverLayout, PathLike


def _render():
    """Import muvid.visualize lazily, so ``import yb.podcast`` works without it."""
    try:
        import muvid.visualize as viz
    except ImportError as e:  # pragma: no cover - environment dependent
        raise ImportError(
            "yb.podcast.cover needs the 'muvid' package for rendering "
            "(pip install 'yb[music]')."
        ) from e
    return viz


def cover_video(
    audio: PathLike,
    image: PathLike,
    *,
    saveas: PathLike | None = None,
    ken_burns: bool = False,
    size: tuple[int, int] | None = None,
    fps: int | None = None,
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
        size: Output resolution (width, height); defaults to 1080p.
        fps: Output frame rate; defaults to muvid's default.
        layout: How the cover sits on the canvas.

    Returns:
        Path to the rendered mp4.

    Raises:
        ImportError: the ``muvid`` package is not installed (``pip install
            'yb[music]'``).
        FfmpegError: ffmpeg is missing, or the render failed.
    """
    viz = _render()
    audio = Path(audio)
    out = Path(saveas) if saveas else audio.with_suffix(".cover.mp4")
    result = viz.render_audio_video(
        audio,
        image,
        visual="ken_burns" if ken_burns else "still",
        saveas=out,
        size=size if size is not None else viz.DEFAULT_SIZE,
        fps=fps if fps is not None else viz.DEFAULT_FPS,
        layout=layout,
    )
    return result.path
