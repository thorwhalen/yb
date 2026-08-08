"""Tests for audio-only download and format conversion.

Network is never touched: the yt-dlp call is monkeypatched out and only the
conversion/fallback logic around it is exercised. The one test that really
shells out to ffmpeg is skipped when ffmpeg is absent.
"""

import re

import pytest

from mixing.util import has_ffmpeg

from yb.audio_convert import (
    AudioConversionError,
    DEFAULT_LOSSY_BITRATE,
    convert_audio,
    normalize_format,
)
from yb.download import youtube as ytdl
from yb.download.youtube import DownloadResult, download_youtube_audio

needs_ffmpeg = pytest.mark.skipif(not has_ffmpeg(), reason="ffmpeg is not installed")


def _make_audio(path, *, seconds=1):
    """Render a short silent wav with ffmpeg (used as a real conversion input)."""
    import subprocess

    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono", "-t", str(seconds), str(path),
        ],
        capture_output=True,
        check=True,
    )
    return path


def _fake_download(path, **info):
    """Patch-in for ``download_youtube_video`` returning a canned result."""

    def _download(url, **kwargs):
        return DownloadResult(path=path, info={"id": "abc123", **info})

    return _download


# ---- normalize_format -----------------------------------------------------


@pytest.mark.parametrize(
    "given,expected",
    [("mp3", "mp3"), (".mp3", "mp3"), (".MP3", "mp3"), (" .Wav ", "wav")],
)
def test_normalize_format(given, expected):
    assert normalize_format(given) == expected


# ---- convert_audio --------------------------------------------------------


def test_convert_audio_is_a_noop_when_already_in_target_format(tmp_path):
    """Same format in and out: return the source untouched, never re-encode."""
    src = tmp_path / "already.mp3"
    src.write_bytes(b"not really an mp3, but never read")

    assert convert_audio(src, "mp3") == src
    assert convert_audio(src, ".MP3") == src  # normalization applies here too


def test_convert_audio_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        convert_audio(tmp_path / "nope.webm", "mp3")


def test_convert_audio_without_ffmpeg_raises_with_install_hint(tmp_path, monkeypatch):
    monkeypatch.setattr("yb.audio_convert.has_ffmpeg", lambda: False)
    src = tmp_path / "audio.webm"
    src.write_bytes(b"bytes")

    with pytest.raises(AudioConversionError, match="ffmpeg is required"):
        convert_audio(src, "mp3")
    assert src.is_file(), "the source must survive a failed conversion"


def test_convert_audio_refuses_to_overwrite_when_asked_not_to(tmp_path):
    src = tmp_path / "audio.webm"
    src.write_bytes(b"bytes")
    (tmp_path / "audio.mp3").write_bytes(b"existing")

    with pytest.raises(AudioConversionError, match="Refusing to overwrite"):
        convert_audio(src, "mp3", overwrite=False)


def test_convert_audio_failure_message_points_at_the_original(tmp_path, monkeypatch):
    """A failed conversion must say where the untouched original still is."""
    src = tmp_path / "audio.webm"
    src.write_bytes(b"definitely not decodable audio")
    monkeypatch.setattr("yb.audio_convert.has_ffmpeg", lambda: True)

    class _Failed:
        returncode = 1
        stderr = "Invalid data found when processing input"

    monkeypatch.setattr("subprocess.run", lambda *a, **k: _Failed())
    # re.escape: on Windows the path's backslashes are regex escapes.
    with pytest.raises(AudioConversionError, match=re.escape(str(src))):
        convert_audio(src, "mp3")


def test_lossless_target_gets_no_bitrate_flag(tmp_path, monkeypatch):
    """Bitrate is meaningless for wav/flac — don't pass -b:a for those."""
    src = tmp_path / "audio.webm"
    src.write_bytes(b"bytes")
    monkeypatch.setattr("yb.audio_convert.has_ffmpeg", lambda: True)
    seen = {}

    class _Ok:
        returncode = 0
        stderr = ""

    def _run(cmd, **kwargs):
        seen["cmd"] = cmd
        (tmp_path / "audio.wav").write_bytes(b"out")
        return _Ok()

    monkeypatch.setattr("subprocess.run", _run)
    convert_audio(src, "wav")
    assert "-b:a" not in seen["cmd"]


def test_lossy_target_uses_default_bitrate_and_honors_override(tmp_path, monkeypatch):
    src = tmp_path / "audio.webm"
    src.write_bytes(b"bytes")
    monkeypatch.setattr("yb.audio_convert.has_ffmpeg", lambda: True)
    seen = {}

    class _Ok:
        returncode = 0
        stderr = ""

    def _run(cmd, **kwargs):
        seen["cmd"] = cmd
        (tmp_path / "audio.mp3").write_bytes(b"out")
        return _Ok()

    monkeypatch.setattr("subprocess.run", _run)

    convert_audio(src, "mp3")
    assert seen["cmd"][seen["cmd"].index("-b:a") + 1] == DEFAULT_LOSSY_BITRATE

    convert_audio(src, "mp3", bitrate="320k")
    assert seen["cmd"][seen["cmd"].index("-b:a") + 1] == "320k"


@needs_ffmpeg
def test_convert_audio_really_converts(tmp_path):
    src = _make_audio(tmp_path / "tone.wav")

    out = convert_audio(src, "mp3")

    assert out == tmp_path / "tone.mp3"
    assert out.is_file() and out.stat().st_size > 0
    assert src.is_file(), "convert_audio itself never deletes the source"


# ---- download_youtube_audio ----------------------------------------------


def test_no_audio_format_means_no_conversion(tmp_path, monkeypatch):
    """The default keeps the downloaded bytes exactly as they came."""
    src = tmp_path / "video.webm"
    src.write_bytes(b"opus bytes")
    monkeypatch.setattr(ytdl, "download_youtube_video", _fake_download(src))

    def _boom(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("convert_audio must not be called")

    monkeypatch.setattr("yb.audio_convert.convert_audio", _boom)

    result = download_youtube_audio("https://youtu.be/abc123")
    assert result.path == src
    assert src.read_bytes() == b"opus bytes"


def test_audio_only_download_requests_an_audio_stream(tmp_path, monkeypatch):
    """The wrapper must ask yt-dlp for audio only and not force a container."""
    src = tmp_path / "video.webm"
    src.write_bytes(b"bytes")
    seen = {}

    def _download(url, **kwargs):
        seen.update(kwargs)
        return DownloadResult(path=src, info={"id": "abc123"})

    monkeypatch.setattr(ytdl, "download_youtube_video", _download)

    download_youtube_audio("https://youtu.be/abc123")
    assert seen["fmt"] == ytdl.DEFAULT_AUDIO_FMT
    assert seen["merge_to"] is None


def test_original_is_removed_after_conversion_unless_kept(tmp_path, monkeypatch):
    src = tmp_path / "video.webm"
    src.write_bytes(b"bytes")
    converted = tmp_path / "video.mp3"

    def _convert(path, fmt, **kwargs):
        converted.write_bytes(b"mp3 bytes")
        return converted

    monkeypatch.setattr(ytdl, "download_youtube_video", _fake_download(src))
    monkeypatch.setattr("yb.audio_convert.convert_audio", _convert)

    result = download_youtube_audio("https://youtu.be/abc123", audio_format="mp3")
    assert result.path == converted
    assert not src.exists(), "the intermediate download should be cleaned up"

    src.write_bytes(b"bytes")
    result = download_youtube_audio(
        "https://youtu.be/abc123", audio_format="mp3", keep_original=True
    )
    assert src.exists(), "keep_original=True must preserve the download"


def test_conversion_failure_raises_by_default_keeping_the_download(
    tmp_path, monkeypatch
):
    src = tmp_path / "video.webm"
    src.write_bytes(b"bytes")

    def _fail(*a, **k):
        raise AudioConversionError("ffmpeg is required")

    monkeypatch.setattr(ytdl, "download_youtube_video", _fake_download(src))
    monkeypatch.setattr("yb.audio_convert.convert_audio", _fail)

    with pytest.raises(AudioConversionError):
        download_youtube_audio("https://youtu.be/abc123", audio_format="mp3")
    assert src.is_file(), "a failed conversion must never cost us the download"


def test_on_error_warn_falls_back_to_the_unconverted_download(tmp_path, monkeypatch):
    src = tmp_path / "video.webm"
    src.write_bytes(b"bytes")

    def _fail(*a, **k):
        raise AudioConversionError("ffmpeg is required")

    monkeypatch.setattr(ytdl, "download_youtube_video", _fake_download(src))
    monkeypatch.setattr("yb.audio_convert.convert_audio", _fail)

    with pytest.warns(UserWarning, match="keeping the downloaded file"):
        result = download_youtube_audio(
            "https://youtu.be/abc123", audio_format="mp3", on_error="warn"
        )
    assert result.path == src
    assert src.is_file()


def test_invalid_on_error_is_rejected_before_downloading(tmp_path, monkeypatch):
    """Bad arguments fail immediately, not after a long download."""

    def _boom(*a, **k):  # pragma: no cover - must never run
        raise AssertionError("must validate before downloading")

    monkeypatch.setattr(ytdl, "download_youtube_video", _boom)

    with pytest.raises(ValueError, match="on_error must be one of"):
        download_youtube_audio("https://youtu.be/abc123", on_error="explode")
