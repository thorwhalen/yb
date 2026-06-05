"""Cover-over-audio video: turn a podcast audio file into a simple video.

Useful for publishing an audio episode on a video platform (YouTube) or
anywhere a video is expected: a still cover image (optionally with a slow
Ken Burns pan/zoom) held for the audio's duration, muxed with the audio.

The static path is pure ffmpeg (robust, no extra deps). The Ken Burns path
delegates to ``mixing`` (the ``burns`` package) and falls back to static.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

PathLike = str | Path

#: Default 16:9 output resolution for the cover video.
DEFAULT_SIZE = (1920, 1080)


def cover_video(
    audio: PathLike,
    image: PathLike,
    *,
    saveas: PathLike | None = None,
    ken_burns: bool = False,
    size: tuple[int, int] = DEFAULT_SIZE,
    fps: int = 24,
) -> Path:
    """Render a video of ``image`` held over ``audio``.

    Args:
        audio: The episode audio file.
        image: Cover image to display.
        saveas: Output path (defaults to ``<audio-stem>.cover.mp4``).
        ken_burns: Apply a slow pan/zoom (via ``mixing``) instead of a static
            image. Falls back to static if Ken Burns rendering is unavailable.
        size: Output resolution (width, height).
        fps: Output frame rate.

    Returns:
        Path to the rendered mp4.
    """
    audio, image = Path(audio), Path(image)
    out = Path(saveas) if saveas else audio.with_suffix(".cover.mp4")

    if ken_burns:
        try:
            return _ken_burns_cover(audio, image, out, size=size, fps=fps)
        except Exception:
            pass  # fall back to a static cover
    return _static_cover(audio, image, out, size=size, fps=fps)


def _static_cover(audio: Path, image: Path, out: Path, *, size, fps) -> Path:
    w, h = size
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-framerate",
            str(fps),
            "-i",
            str(image),
            "-i",
            str(audio),
            "-vf",
            vf,
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    return out


def _ken_burns_cover(audio: Path, image: Path, out: Path, *, size, fps) -> Path:
    """Pan/zoom the cover for the audio duration, then mux the audio."""
    from mixing.video import ken_burns_video, replace_audio

    duration = _audio_duration(audio)
    silent = ken_burns_video(
        str(image),
        duration=duration,
        size=size,
        fps=fps,
        output=str(out.with_suffix(".silent.mp4")),
    )
    replace_audio(str(silent), str(audio), output=str(out), match_duration=False)
    Path(silent).unlink(missing_ok=True)
    return out


def _audio_duration(path: PathLike) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return float(out.stdout.strip())
