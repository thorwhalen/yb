"""Media download (yt-dlp) — fetch videos and their metadata.

A separate, optionally-installed module (``pip install 'yb[download]'``).
Common use:

    >>> from yb.download import download_youtube_video  # doctest: +SKIP
    >>> result = download_youtube_video("https://youtu.be/PRa9ciOe-us")  # doctest: +SKIP
    >>> print(result.path, result.video_id)  # doctest: +SKIP
"""

from yb.download.youtube import (
    download_youtube_video,
    youtube_video_info,
    default_download_dir,
    DownloadResult,
    DOWNLOAD_DIR_ENV,
    DEFAULT_OUTTMPL,
)

__all__ = [
    "download_youtube_video",
    "youtube_video_info",
    "default_download_dir",
    "DownloadResult",
    "DOWNLOAD_DIR_ENV",
    "DEFAULT_OUTTMPL",
]
