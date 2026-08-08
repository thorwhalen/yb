"""Convert audio files between formats with ffmpeg.

Audio arrives in whatever format the source offers — YouTube's best audio is
typically Opus in a ``.webm`` container — which is usually fine to keep as is.
Publishing paths, though, often want something specific: ``.mp3`` for podcast
players, ``.wav`` for editing. :func:`convert_audio` is the one-call bridge:

    >>> from yb.audio_convert import convert_audio
    >>> convert_audio("talk.webm", "mp3")  # doctest: +SKIP
    PosixPath('talk.mp3')

Conversion is a **no-op when the source is already in the target format**, so it
is safe to call unconditionally:

    >>> convert_audio("talk.mp3", "mp3")  # doctest: +SKIP
    PosixPath('talk.mp3')

Requires ``ffmpeg`` on ``PATH``; without it :class:`AudioConversionError` is
raised (see also the ``on_error="warn"`` escape hatch in
:func:`yb.download.download_youtube_audio`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

from mixing.util import has_ffmpeg

PathLike = str | Path

#: Formats that store samples losslessly — a target bitrate is meaningless there.
LOSSLESS_FORMATS = frozenset({"wav", "flac", "aiff", "aif", "alac"})

#: Bitrate applied to lossy targets when the caller doesn't specify one.
DEFAULT_LOSSY_BITRATE = "192k"

#: How many trailing lines of ffmpeg's stderr to quote when it fails.
_ERROR_TAIL_LINES = 8


class AudioConversionError(RuntimeError):
    """Raised when audio could not be converted to the requested format."""


def normalize_format(audio_format: str) -> str:
    """Normalize a format spec to a bare lowercase extension.

    Accepts it with or without the leading dot, in any case:

    >>> normalize_format("mp3"), normalize_format(".MP3"), normalize_format(" .Wav ")
    ('mp3', 'mp3', 'wav')
    """
    return audio_format.strip().lstrip(".").lower()


def convert_audio(
    src: PathLike,
    audio_format: str,
    *,
    output: PathLike | None = None,
    bitrate: str | None = None,
    overwrite: bool = True,
    extra_ffmpeg_args: Iterable[str] = (),
) -> Path:
    """Convert ``src`` to ``audio_format``, returning the resulting path.

    Args:
        src: The audio file to convert.
        audio_format: Target format as an extension (``"mp3"``, ``".wav"``, ...).
        output: Destination path. Defaults to ``src`` with the new extension.
        bitrate: Target bitrate for lossy formats (e.g. ``"320k"``). Defaults to
            :data:`DEFAULT_LOSSY_BITRATE`; ignored for :data:`LOSSLESS_FORMATS`.
        overwrite: Overwrite ``output`` if it already exists.
        extra_ffmpeg_args: Raw ffmpeg arguments, appended last so they win.

    Returns:
        The converted file's path — or ``src`` unchanged when it is already in
        the target format (no pointless re-encode, no generation loss).

    Raises:
        FileNotFoundError: If ``src`` does not exist.
        AudioConversionError: If ffmpeg is missing, or the conversion fails.
    """
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError(f"No such audio file: {src}")

    fmt = normalize_format(audio_format)
    # Already in the target format: converting would only lose quality.
    if normalize_format(src.suffix) == fmt and output is None:
        return src

    out_path = Path(output) if output else src.with_suffix(f".{fmt}")
    if out_path.exists() and not overwrite:
        raise AudioConversionError(
            f"Refusing to overwrite existing file: {out_path} (pass overwrite=True)"
        )

    if not has_ffmpeg():
        raise AudioConversionError(
            f"ffmpeg is required to convert {src.name} to {fmt!r} but was not found "
            "on PATH. Install it (macOS: `brew install ffmpeg`, Ubuntu: "
            "`apt install ffmpeg`), or skip conversion to keep the original file."
        )

    cmd = ["ffmpeg", "-y" if overwrite else "-n", "-i", str(src), "-vn"]
    if fmt not in LOSSLESS_FORMATS:
        cmd += ["-b:a", bitrate or DEFAULT_LOSSY_BITRATE]
    cmd += [*extra_ffmpeg_args, str(out_path)]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out_path.is_file():
        detail = "\n".join(proc.stderr.strip().splitlines()[-_ERROR_TAIL_LINES:])
        raise AudioConversionError(
            f"ffmpeg failed to convert {src} to {fmt!r} (exit {proc.returncode}).\n"
            f"The original file is untouched at: {src}\n{detail}"
        )
    return out_path
