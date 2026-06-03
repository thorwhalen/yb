"""Download YouTube videos (and their metadata) via yt-dlp.

The common case is one call — ``download_youtube_video(url)`` — which fetches
the best video+audio into ``~/Downloads`` as ``Title (video_id).mp4``. Every
knob (destination, format, filename template, and which sidecar metadata to
also save) is overridable, and any raw yt-dlp option can be passed through.

The destination defaults to ``$YB_DOWNLOAD_DIR`` when set, else ``~/Downloads``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PathLike = str | Path

#: Env var that overrides the default download directory.
DOWNLOAD_DIR_ENV = "YB_DOWNLOAD_DIR"

#: yt-dlp output template: human title plus the stable id, e.g. "My Talk (dQw4...).mp4".
DEFAULT_OUTTMPL = "%(title)s (%(id)s).%(ext)s"

#: Fields surfaced on the result's ``info`` (the rest of yt-dlp's dict is dropped).
_INFO_FIELDS = (
    "id",
    "title",
    "uploader",
    "channel",
    "channel_id",
    "duration",
    "upload_date",
    "view_count",
    "like_count",
    "description",
    "tags",
    "categories",
    "chapters",
    "webpage_url",
    "thumbnail",
    "language",
)


def default_download_dir() -> Path:
    """Resolve the default download directory (``$YB_DOWNLOAD_DIR`` or ``~/Downloads``)."""
    override = os.environ.get(DOWNLOAD_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / "Downloads"


@dataclass
class DownloadResult:
    """Outcome of a download.

    Attributes:
        path: The downloaded media file.
        info: A trimmed metadata dict (see :data:`_INFO_FIELDS`).
        sidecars: Map of extra artifacts written (``info_json``, ``thumbnail``,
            ``description``, ``subtitles`` → path(s)).
    """

    path: Path
    info: dict[str, Any]
    sidecars: dict[str, Any] = field(default_factory=dict)

    @property
    def video_id(self) -> str:
        """The YouTube video id."""
        return self.info.get("id", "")


def youtube_video_info(url: str, *, extra_opts: dict | None = None) -> dict[str, Any]:
    """Fetch a video's metadata without downloading it.

    Returns the trimmed info dict (see :data:`_INFO_FIELDS`). Useful to preview
    the title/duration/chapters before deciding to download.
    """
    from yt_dlp import YoutubeDL

    opts = {"quiet": True, "skip_download": True, "noplaylist": True}
    opts.update(extra_opts or {})
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return _trim_info(info)


def download_youtube_video(
    url: str,
    *,
    download_dir: PathLike | None = None,
    fmt: str = "bestvideo+bestaudio/best",
    merge_to: str | None = "mp4",
    filename_template: str = DEFAULT_OUTTMPL,
    write_info_json: bool = False,
    write_thumbnail: bool = False,
    write_description: bool = False,
    write_subtitles: bool = False,
    write_auto_subtitles: bool = False,
    subtitle_langs: tuple[str, ...] = ("en",),
    quiet: bool = True,
    extra_opts: dict | None = None,
) -> DownloadResult:
    """Download a YouTube video to ``download_dir`` (default ``~/Downloads``).

    Simplest use: ``download_youtube_video(url)`` → best quality merged to mp4,
    named ``Title (video_id).mp4`` in ``~/Downloads``.

    Args:
        url: The video URL (or id).
        download_dir: Destination directory. Defaults to
            :func:`default_download_dir`.
        fmt: yt-dlp format selector (default best video + best audio).
        merge_to: Container to merge video+audio into (default ``"mp4"``;
            requires ffmpeg). Set ``None`` to keep yt-dlp's default.
        filename_template: yt-dlp output template (default
            ``"%(title)s (%(id)s).%(ext)s"``).
        write_info_json: Also save the full metadata as ``*.info.json``.
        write_thumbnail: Also save the thumbnail image.
        write_description: Also save the description as ``*.description``.
        write_subtitles: Also save uploaded subtitles for ``subtitle_langs``.
        write_auto_subtitles: Also save auto-generated subtitles.
        subtitle_langs: Subtitle languages to fetch when subtitles are enabled.
        quiet: Suppress yt-dlp console output.
        extra_opts: Any additional raw yt-dlp options (merged last, so they win).

    Returns:
        A :class:`DownloadResult` with the media path, trimmed ``info``, and any
        ``sidecars`` written.
    """
    from yt_dlp import YoutubeDL

    out_dir = Path(download_dir) if download_dir else default_download_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    opts: dict[str, Any] = {
        "format": fmt,
        "outtmpl": str(out_dir / filename_template),
        "noplaylist": True,
        "quiet": quiet,
        "writeinfojson": write_info_json,
        "writethumbnail": write_thumbnail,
        "writedescription": write_description,
        "writesubtitles": write_subtitles,
        "writeautomaticsub": write_auto_subtitles,
        "subtitleslangs": list(subtitle_langs),
    }
    if merge_to:
        opts["merge_output_format"] = merge_to
    opts.update(extra_opts or {})

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    path = _resolve_output_path(info, ydl, out_dir, merge_to)
    sidecars = _collect_sidecars(
        info,
        path,
        info_json=write_info_json,
        thumbnail=write_thumbnail,
        description=write_description,
        subtitles=write_subtitles or write_auto_subtitles,
    )
    return DownloadResult(path=path, info=_trim_info(info), sidecars=sidecars)


def _resolve_output_path(info, ydl, out_dir: Path, merge_to: str | None) -> Path:
    """Best-effort resolution of the final media path yt-dlp produced."""
    downloads = info.get("requested_downloads")
    if downloads and downloads[0].get("filepath"):
        return Path(downloads[0]["filepath"])
    name = ydl.prepare_filename(info)
    p = Path(name)
    if merge_to and p.suffix.lower() != f".{merge_to.lower()}":
        merged = p.with_suffix(f".{merge_to}")
        if merged.exists():
            return merged
    return p


def _collect_sidecars(
    info,
    media_path: Path,
    *,
    info_json: bool,
    thumbnail: bool,
    description: bool,
    subtitles: bool,
) -> dict[str, Any]:
    stem = media_path.with_suffix("")
    out: dict[str, Any] = {}
    if info_json:
        cand = stem.with_suffix(".info.json")
        if cand.exists():
            out["info_json"] = cand
    if description:
        cand = stem.with_suffix(".description")
        if cand.exists():
            out["description"] = cand
    if thumbnail:
        for ext in (".jpg", ".webp", ".png"):
            cand = stem.with_suffix(ext)
            if cand.exists():
                out["thumbnail"] = cand
                break
    if subtitles:
        subs = sorted(
            media_path.parent.glob(f"{glob_escape(stem.name)}.*.srt")
        ) + sorted(media_path.parent.glob(f"{glob_escape(stem.name)}.*.vtt"))
        if subs:
            out["subtitles"] = subs
    return out


def glob_escape(name: str) -> str:
    """Escape glob metacharacters in a literal filename stem."""
    return (
        name.replace("[", "[[]")
        .replace("]", "[]]")
        .replace("*", "[*]")
        .replace("?", "[?]")
    )


def _trim_info(info: dict | None) -> dict[str, Any]:
    if not info:
        return {}
    return {k: info.get(k) for k in _INFO_FIELDS if info.get(k) is not None}
