"""Render media assets: turn audio into video that a platform will accept.

``yb`` separates *what* you publish from *where*. This package is the "what"
for audio: given a song (and usually a cover), it produces the 16:9, H.264,
loudness-normalized mp4 that YouTube expects, plus a matching thumbnail.

The one call most people need:

    >>> from yb.render import render_audio_video
    >>> render_audio_video("song.wav", image="cover.png")            # doctest: +SKIP

Everything else is a knob on that: :func:`~yb.render.visuals.list_visuals`
names the built-in looks, :func:`~yb.render.visuals.register_visual` adds your
own, :class:`~yb.render.canvas.CoverLayout` controls how the cover sits on the
canvas, and :func:`~yb.render.canvas.thumbnail_image` derives the thumbnail
from that same composition.

Needs ``ffmpeg`` (and ``ffprobe``) on the PATH — as the rest of ``yb`` does.
Every built-in visual is ffmpeg-native, except Ken Burns, which renders through
``burns`` (already a dependency of ``mixing``, so it needs no extra either).
"""

from yb.render.ffmpeg import (
    FfmpegError,
    Loudness,
    has_filter,
    measure_loudness,
    media_duration,
    probe,
    require_ffmpeg,
    run_ffmpeg,
)
from yb.render.canvas import (
    DEFAULT_SIZE,
    THUMBNAIL_SIZE,
    CoverLayout,
    TitleStyle,
    canvas_image,
    thumbnail_image,
)
from yb.render.visuals import (
    VisualContext,
    VisualPlan,
    list_visuals,
    register_visual,
    resolve_visual,
)
from yb.render.video import (
    DEFAULT_FPS,
    RenderResult,
    render_audio_video,
)
from yb.render.verify import (
    Check,
    failures,
    report,
    verify_video,
)

__all__ = [
    "Check",
    "failures",
    "report",
    "verify_video",
    "FfmpegError",
    "Loudness",
    "has_filter",
    "measure_loudness",
    "media_duration",
    "probe",
    "require_ffmpeg",
    "run_ffmpeg",
    "DEFAULT_SIZE",
    "THUMBNAIL_SIZE",
    "CoverLayout",
    "TitleStyle",
    "canvas_image",
    "thumbnail_image",
    "VisualContext",
    "VisualPlan",
    "list_visuals",
    "register_visual",
    "resolve_visual",
    "DEFAULT_FPS",
    "RenderResult",
    "render_audio_video",
]
