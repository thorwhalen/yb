"""Render an audio file into a video: pick a visual, mux, normalize, encode.

This is the assembler. A :mod:`~yb.render.visuals` strategy says what the
frames look like; everything platform-facing lives here — the 16:9 canvas, the
H.264/AAC encode YouTube prefers, EBU R128 loudness normalization, and the
guarantee that the video ends exactly when the song does.

    >>> from yb.render import render_audio_video
    >>> result = render_audio_video("song.wav", image="cover.png")  # doctest: +SKIP
    >>> result.path, result.duration                                # doctest: +SKIP
    (PosixPath('song.mp4'), 154.92)
"""

from __future__ import annotations

import math
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from yb.render.canvas import (
    DEFAULT_SIZE,
    CoverLayout,
    TitleStyle,
    cover_chain,
    overlay_chain,
    title_chain,
)
from yb.render.ffmpeg import (
    Loudness,
    PathLike,
    media_duration,
    measure_loudness,
    require_ffmpeg,
    run_ffmpeg,
)
from yb.render.visuals import Visual, VisualContext, VisualPlan, resolve_visual

DEFAULT_FPS = 24

#: Constant-rate-factor: visually lossless enough for a source YouTube re-encodes.
DEFAULT_CRF = 18
DEFAULT_PRESET = "medium"

#: YouTube's recommended audio for stereo uploads.
DEFAULT_AUDIO_BITRATE = "384k"
AUDIO_SAMPLE_RATE = 48000

#: Length of the single segment the still fast-path encodes before looping it.
_STILL_SEGMENT_SECONDS = 2.0


@dataclass
class RenderResult:
    """A rendered video and what is worth knowing about it.

    Usable anywhere a path is (it implements ``os.PathLike``).

    Attributes:
        path: The rendered mp4.
        duration: Its duration in seconds.
        size: Frame size.
        fps: Frame rate.
        visual: The strategy that produced it.
        loudness: The applied loudness target and measurement, if normalized.
        canvas: The composed canvas image, when the strategy built one — reuse
            it as the thumbnail rather than re-deriving it.
    """

    path: Path
    duration: float
    size: tuple[int, int]
    fps: int
    visual: str
    loudness: Loudness | None = None
    canvas: Path | None = None
    extras: dict = field(default_factory=dict)

    def __fspath__(self) -> str:
        return str(self.path)


def render_audio_video(
    audio: PathLike,
    image: PathLike | None = None,
    *,
    visual: str | Visual = "auto",
    saveas: PathLike | None = None,
    size: tuple[int, int] = DEFAULT_SIZE,
    fps: int = DEFAULT_FPS,
    title: str | None = None,
    layout: CoverLayout | None = None,
    title_style: TitleStyle | None = None,
    normalize: bool = False,
    loudness: Loudness | None = None,
    crf: int = DEFAULT_CRF,
    preset: str = DEFAULT_PRESET,
    audio_bitrate: str = DEFAULT_AUDIO_BITRATE,
    options: dict | None = None,
    workdir: PathLike | None = None,
) -> RenderResult:
    """Render ``audio`` into a video, using ``visual`` for the picture.

    The video is exactly as long as the audio, 16:9, H.264/yuv420p + AAC — what
    YouTube asks for. With ``normalize=True`` the audio is brought to a fixed
    EBU R128 loudness with a two-pass ``loudnorm``, which is what makes a batch
    of songs play back at a consistent level.

    Args:
        audio: The song (``.wav`` is preferred when you have it — YouTube
            re-encodes regardless, so give it the cleanest input).
        image: Cover art. Used for the picture, and composed onto a 16:9 canvas.
        visual: A registered strategy name (``"still"``, ``"ken_burns"``,
            ``"cqt"``, ``"bars"``, ``"spectrum"``, ``"waves"``, ``"scope"``),
            ``"auto"``, or any callable (see :mod:`yb.render.visuals`).
        saveas: Output path (default: ``<audio-stem>.mp4``).
        size: Canvas size; the default is 1080p.
        fps: Frame rate.
        title: Burn this title into the frame.
        layout: How the cover sits on the canvas.
        title_style: How the title is drawn.
        normalize: Loudness-normalize the audio (two-pass EBU R128).
        loudness: The loudness target; a YouTube-appropriate default is used
            when omitted.
        crf / preset / audio_bitrate: Encoder knobs.
        options: Strategy-specific options, passed to the visual.
        workdir: Where intermediates go (a temporary directory by default).

    Returns:
        A :class:`RenderResult`.
    """
    require_ffmpeg()
    audio = Path(audio)
    out = Path(saveas) if saveas else audio.with_suffix(".mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    duration = media_duration(audio)

    with _work_dir(workdir) as work:
        ctx = VisualContext(
            audio=audio,
            image=Path(image) if image else None,
            duration=duration,
            size=size,
            fps=fps,
            layout=layout or CoverLayout(),
            title=title,
            title_style=title_style,
            workdir=work,
            options=dict(options or {}),
        )
        plan = resolve_visual(visual, ctx)

        loud = None
        if normalize:
            loud = measure_loudness(audio, loudness or Loudness())

        if plan.still is not None:
            _render_still(plan.still, ctx, out, loud=loud, crf=crf, preset=preset,
                          audio_bitrate=audio_bitrate)
        else:
            _render_filtergraph(plan, ctx, out, loud=loud, crf=crf, preset=preset,
                                audio_bitrate=audio_bitrate)

        canvas = plan.still if plan.still and plan.still.exists() else None
        if canvas and workdir is None:
            canvas = _keep(canvas, out.with_suffix(".canvas.png"))

    return RenderResult(
        path=out,
        duration=media_duration(out),
        size=size,
        fps=fps,
        visual=visual if isinstance(visual, str) else getattr(visual, "__name__", "custom"),
        loudness=loud,
        canvas=canvas,
    )


def _render_still(
    canvas: Path,
    ctx: VisualContext,
    out: Path,
    *,
    loud: Loudness | None,
    crf: int,
    preset: str,
    audio_bitrate: str,
) -> None:
    """Encode one short segment of the static canvas, then loop it, copying.

    A still video is thousands of identical frames. Encoding them all is a
    waste: instead encode a couple of seconds once, then concatenate that
    segment with ``-c:v copy``, which touches no pixels. On a small machine
    this is an order of magnitude faster than the naive encode, and the output
    is byte-for-byte the same picture.

    The loop count is finite and the output is bounded by ``-t`` on purpose:
    ``-shortest`` alone does *not* stop an infinitely looping copied stream,
    and ffmpeg will happily fill the disk.
    """
    segment_seconds = min(_STILL_SEGMENT_SECONDS, ctx.duration)
    segment = ctx.workdir / "segment.mp4"
    gop = max(1, int(round(ctx.fps * segment_seconds)))
    run_ffmpeg(
        [
            "-loop", "1",
            "-framerate", str(ctx.fps),
            "-i", str(canvas),
            "-t", f"{segment_seconds:.3f}",
            "-an",
            *_video_encode_args(crf=crf, preset=preset, fps=ctx.fps, gop=gop),
            "-tune", "stillimage",
            str(segment),
        ]
    )
    loops = math.ceil(ctx.duration / segment_seconds)
    run_ffmpeg(
        [
            "-stream_loop", str(loops),
            "-i", str(segment),
            "-i", str(ctx.audio),
            *(["-af", loud.filter_spec()] if loud else []),
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            *_audio_encode_args(audio_bitrate),
            "-t", f"{ctx.duration:.3f}",
            "-movflags", "+faststart",
            str(out),
        ]
    )


def _render_filtergraph(
    plan: VisualPlan,
    ctx: VisualContext,
    out: Path,
    *,
    loud: Loudness | None,
    crf: int,
    preset: str,
    audio_bitrate: str,
) -> None:
    """The general path: build one filter_complex, encode video and audio."""
    inputs: list[str] = ["-i", str(ctx.audio)]
    for group in plan.inputs:
        inputs += [str(a) for a in group]

    chains: list[str] = []
    audio_label = "0:a"
    if plan.uses_audio:
        chains.append("[0:a]asplit=2[atrack][aviz]")
        audio_label = "[atrack]"
    chains += list(plan.filters)

    video = plan.video
    if ctx.image is not None and not plan.has_cover:
        index = 1 + len(plan.inputs)
        inputs += ["-loop", "1", "-framerate", str(ctx.fps), "-i", str(ctx.image)]
        chains.append(cover_chain(ctx.size, ctx.layout, src=f"{index}:v", out="_fgc"))
        chains.append(
            overlay_chain(background=video, cover="_fgc", out="_vc", shortest=True)
        )
        video = "_vc"

    if ctx.title and not plan.has_title:
        chains.append(
            title_chain(ctx.title, ctx.size, ctx.title_style, src=video, out="_vt")
        )
        video = "_vt"

    chains.append(f"[{video}]fps={ctx.fps},format=yuv420p[vout]")

    if loud:
        chains.append(f"{_as_label(audio_label)}{loud.filter_spec()}[aout]")
        audio_label = "[aout]"

    gop = ctx.fps * 2
    run_ffmpeg(
        [
            *inputs,
            "-filter_complex", ";".join(chains),
            "-map", "[vout]",
            "-map", audio_label,
            *_video_encode_args(crf=crf, preset=preset, fps=ctx.fps, gop=gop),
            *_audio_encode_args(audio_bitrate),
            "-t", f"{ctx.duration:.3f}",
            "-shortest",
            "-movflags", "+faststart",
            str(out),
        ]
    )


def _as_label(stream: str) -> str:
    """``0:a`` -> ``[0:a]``; an already-bracketed label passes through."""
    return stream if stream.startswith("[") else f"[{stream}]"


def _video_encode_args(*, crf: int, preset: str, fps: int, gop: int) -> list[str]:
    """H.264 the way YouTube wants it: high profile, yuv420p, closed 2s GOP."""
    return [
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-profile:v", "high",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-g", str(gop),
        "-keyint_min", str(gop),
        "-sc_threshold", "0",
    ]


def _audio_encode_args(bitrate: str) -> list[str]:
    return [
        "-c:a", "aac",
        "-b:a", bitrate,
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-ac", "2",
    ]


class _work_dir:
    """Context manager yielding ``workdir``, or a temporary directory."""

    def __init__(self, workdir: PathLike | None):
        self._given = Path(workdir) if workdir else None
        self._tmp: tempfile.TemporaryDirectory | None = None

    def __enter__(self) -> Path:
        if self._given:
            self._given.mkdir(parents=True, exist_ok=True)
            return self._given
        self._tmp = tempfile.TemporaryDirectory(prefix="yb-render-")
        return Path(self._tmp.name)

    def __exit__(self, *exc) -> None:
        if self._tmp:
            self._tmp.cleanup()


def _keep(src: Path, dest: Path) -> Path:
    """Copy a temporary artefact out before its temp dir is cleaned up."""
    dest.write_bytes(src.read_bytes())
    return dest
