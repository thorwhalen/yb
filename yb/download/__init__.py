"""Media download (yt-dlp) — fetch videos, audio, and their metadata.

A separate, optionally-installed module (``pip install 'yb[download]'``).
Common use:

    >>> from yb.download import download_youtube_video  # doctest: +SKIP
    >>> result = download_youtube_video("https://youtu.be/PRa9ciOe-us")  # doctest: +SKIP
    >>> print(result.path, result.video_id)  # doctest: +SKIP

For audio only — e.g. to feed a transcription or podcast workflow — use
:func:`download_youtube_audio`, which keeps the source format by default and
converts only when you ask it to (conversion needs ffmpeg):

    >>> from yb.download import download_youtube_audio  # doctest: +SKIP
    >>> ep = download_youtube_audio(url, audio_format="mp3")  # doctest: +SKIP
"""

from yb.audio_convert import AudioConversionError, convert_audio
from yb.download.youtube import (
    download_youtube_video,
    download_youtube_audio,
    youtube_video_info,
    download_youtube_playlist,
    youtube_playlist_info,
    default_download_dir,
    DownloadResult,
    DOWNLOAD_DIR_ENV,
    DEFAULT_OUTTMPL,
    DEFAULT_AUDIO_FMT,
)

__all__ = [
    "download_youtube_video",
    "download_youtube_audio",
    "youtube_video_info",
    "download_youtube_playlist",
    "youtube_playlist_info",
    "default_download_dir",
    "convert_audio",
    "AudioConversionError",
    "DownloadResult",
    "DOWNLOAD_DIR_ENV",
    "DEFAULT_OUTTMPL",
    "DEFAULT_AUDIO_FMT",
]
