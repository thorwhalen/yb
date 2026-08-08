"""Download YouTube videos (and their metadata) via yt-dlp.

The common case is one call — ``download_youtube_video(url)`` — which fetches
the best video+audio into ``~/Downloads`` as ``Title (video_id).mp4``. Every
knob (destination, format, filename template, and which sidecar metadata to
also save) is overridable, and any raw yt-dlp option can be passed through.

The destination defaults to ``$YB_DOWNLOAD_DIR`` when set, else ``~/Downloads``.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

PathLike = str | Path

#: What :func:`download_youtube_audio` does when a format conversion fails.
OnConvertError = Literal["raise", "warn"]

_ON_CONVERT_ERROR_CHOICES = frozenset({"raise", "warn"})

#: Env var that overrides the default download directory.
DOWNLOAD_DIR_ENV = "YB_DOWNLOAD_DIR"

#: yt-dlp output template: human title plus the stable id, e.g. "My Talk (dQw4...).mp4".
DEFAULT_OUTTMPL = "%(title)s (%(id)s).%(ext)s"

#: yt-dlp format selector for the best audio-only stream.
DEFAULT_AUDIO_FMT = "bestaudio/best"

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
    "original_url",
    "thumbnail",
    "language",
    "fps",
    "width",
    "height",
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


def download_youtube_audio(
    url: str,
    *,
    download_dir: PathLike | None = None,
    audio_format: str | None = None,
    bitrate: str | None = None,
    keep_original: bool = False,
    on_error: OnConvertError = "raise",
    fmt: str = DEFAULT_AUDIO_FMT,
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
    """Download only a video's audio (no video stream).

    Simplest use: ``download_youtube_audio(url)`` → the best audio stream, kept
    in whatever format the source offers (YouTube's is usually Opus in a
    ``.webm`` container), named ``Title (video_id).webm`` in ``~/Downloads``.

    Pass ``audio_format`` to get a specific format instead:

        >>> download_youtube_audio(url, audio_format="mp3")  # doctest: +SKIP

    Args:
        url: The video URL (or id).
        download_dir: Destination directory. Defaults to
            :func:`default_download_dir`.
        audio_format: Target format as an extension (``"mp3"``, ``".wav"``, ...).
            The default ``None`` means **no conversion** — keep the downloaded
            bytes exactly as they came, which needs no ffmpeg and avoids
            re-encoding a lossy stream into another lossy format.
        bitrate: Bitrate for lossy targets (e.g. ``"320k"``). Ignored when
            ``audio_format`` is lossless or ``None``.
        keep_original: When converting, also keep the originally downloaded
            file (by default it is removed once converted).
        on_error: What to do when conversion fails (ffmpeg missing or erroring).
            ``"raise"`` (default) propagates
            :class:`~yb.audio_convert.AudioConversionError`; ``"warn"`` emits a
            warning and returns the unconverted download. Either way the
            downloaded audio is left on disk — a failed conversion never costs
            you the download.
        fmt: yt-dlp format selector (default best audio-only stream).
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
        A :class:`DownloadResult` whose ``path`` is the audio file — converted
        when ``audio_format`` was given and conversion succeeded.

    Raises:
        ValueError: If ``on_error`` is not ``"raise"`` or ``"warn"``.
        AudioConversionError: If conversion fails and ``on_error="raise"``.
    """
    if on_error not in _ON_CONVERT_ERROR_CHOICES:
        raise ValueError(
            f"on_error must be one of {sorted(_ON_CONVERT_ERROR_CHOICES)}, "
            f"got {on_error!r}"
        )

    result = download_youtube_video(
        url,
        download_dir=download_dir,
        fmt=fmt,
        merge_to=None,  # keep the audio stream's own container
        filename_template=filename_template,
        write_info_json=write_info_json,
        write_thumbnail=write_thumbnail,
        write_description=write_description,
        write_subtitles=write_subtitles,
        write_auto_subtitles=write_auto_subtitles,
        subtitle_langs=subtitle_langs,
        quiet=quiet,
        extra_opts=extra_opts,
    )
    if audio_format is None:
        return result

    from yb.audio_convert import AudioConversionError, convert_audio

    original = result.path
    try:
        converted = convert_audio(original, audio_format, bitrate=bitrate)
    except AudioConversionError:
        if on_error == "raise":
            raise
        warnings.warn(
            f"Could not convert to {audio_format!r}; keeping the downloaded "
            f"file as is: {original}",
            stacklevel=2,
        )
        return result

    if converted != original and not keep_original:
        original.unlink(missing_ok=True)
    result.path = converted
    return result


def youtube_playlist_info(
    url: str,
    *,
    playlist_items: str | None = None,
    flat: bool = True,
    extra_opts: dict | None = None,
) -> dict[str, Any]:
    """Fetch a playlist's per-video metadata without downloading.

    Returns a dict with playlist-level fields (``playlist_id``, ``playlist_title``,
    ``webpage_url``, ``uploader``, ``count``) and an ``entries`` list. With
    ``flat=True`` (default) extraction is fast/shallow (each entry has at least
    ``id``, ``title``, ``url``); with ``flat=False`` each entry is fully resolved
    and trimmed to :data:`_INFO_FIELDS` (slower, but includes duration/fps/etc.).

    Args:
        url: The playlist URL.
        playlist_items: yt-dlp ``--playlist-items`` selector, 1-based, e.g.
            ``"2:"`` (all but the first), ``"2"`` (only the 2nd), ``"1:5,8"``.
        flat: Shallow vs full per-entry extraction.
        extra_opts: Additional raw yt-dlp options (merged last).
    """
    from yt_dlp import YoutubeDL

    opts: dict[str, Any] = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist" if flat else False,
        "ignoreerrors": True,
    }
    if playlist_items:
        opts["playlist_items"] = playlist_items
    opts.update(extra_opts or {})
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    raw_entries = (info.get("entries") if info else None) or []
    if flat:
        entries = [
            {
                "id": e.get("id"),
                "title": e.get("title"),
                "webpage_url": e.get("url") or e.get("webpage_url"),
                "duration": e.get("duration"),
            }
            for e in raw_entries
            if e
        ]
    else:
        entries = [_trim_info(e) for e in raw_entries if e]
    return {
        "playlist_id": (info or {}).get("id"),
        "playlist_title": (info or {}).get("title"),
        "webpage_url": (info or {}).get("webpage_url"),
        "uploader": (info or {}).get("uploader"),
        "count": len(entries),
        "entries": entries,
    }


def download_youtube_playlist(
    url: str,
    *,
    download_dir: PathLike | None = None,
    playlist_items: str | None = None,
    skip_first: bool = False,
    title_reject: str | None = None,
    download_archive: PathLike | None = None,
    fmt: str = "bestvideo+bestaudio/best",
    merge_to: str | None = "mp4",
    filename_template: str = DEFAULT_OUTTMPL,
    write_info_json: bool = True,
    write_thumbnail: bool = False,
    write_description: bool = False,
    write_subtitles: bool = False,
    write_auto_subtitles: bool = False,
    subtitle_langs: tuple[str, ...] = ("en",),
    cookies_from_browser: str | tuple | None = None,
    extractor_args: dict | None = None,
    quiet: bool = True,
    extra_opts: dict | None = None,
) -> list[DownloadResult]:
    """Download all (or a selected subset of) a YouTube playlist's videos.

    Simplest use: ``download_youtube_playlist(url)`` → every video downloaded best
    quality merged to mp4 into ``download_dir`` (default ``~/Downloads``), each with
    its ``*.info.json`` sidecar (``write_info_json`` defaults to ``True`` here, since
    a playlist download is usually an archival operation).

    Selecting a subset (yt-dlp ``--playlist-items`` is **1-based**):

        # skip the first ("PV"/intro) entry, keep the rest
        download_youtube_playlist(url, skip_first=True)         # -> playlist_items="2:"
        download_youtube_playlist(url, playlist_items="2:")     # same, explicit
        download_youtube_playlist(url, playlist_items="2")      # only the 2nd video
        download_youtube_playlist(url, title_reject="PV")       # skip entries whose title contains "PV"

    Args:
        url: The playlist URL.
        download_dir: Destination directory (default :func:`default_download_dir`).
        playlist_items: yt-dlp item selector (1-based; ``"2:"``, ``"2"``, ``"1:5,8"``).
        skip_first: Convenience for ``playlist_items="2:"`` (ignored if
            ``playlist_items`` is given).
        title_reject: Skip entries whose (case-insensitive) title contains this
            substring — more robust than a positional skip if ordering changes.
        download_archive: Path to a yt-dlp archive file recording downloaded ids,
            making re-runs idempotent/resumable.
        fmt: yt-dlp format selector (default best video + best audio).
        merge_to: Container to merge into (default ``"mp4"``; needs ffmpeg).
        filename_template: yt-dlp output template (default
            ``"%(title)s (%(id)s).%(ext)s"``).
        write_info_json: Save each video's ``*.info.json`` (default ``True``).
        write_thumbnail, write_description, write_subtitles, write_auto_subtitles,
        subtitle_langs: As in :func:`download_youtube_video`.
        cookies_from_browser: Browser to read cookies from for bot-detection /
            age / region issues, e.g. ``"safari"`` or ``("chrome", "Profile 1")``.
        extractor_args: yt-dlp ``extractor_args`` (e.g.
            ``{"youtube": {"player_client": ["web_safari"]}}``).
        quiet: Suppress yt-dlp console output.
        extra_opts: Any additional raw yt-dlp options (merged last, so they win).

    Returns:
        A list of :class:`DownloadResult`, one per successfully-downloaded entry,
        in playlist order. Entries skipped by selection/filter or that failed
        (under ``ignoreerrors``) are omitted.
    """
    from yt_dlp import YoutubeDL

    out_dir = Path(download_dir) if download_dir else default_download_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    if playlist_items is None and skip_first:
        playlist_items = "2:"

    opts: dict[str, Any] = {
        "format": fmt,
        "outtmpl": str(out_dir / filename_template),
        "noplaylist": False,
        "ignoreerrors": "only_download",
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
    if playlist_items:
        opts["playlist_items"] = playlist_items
    if download_archive:
        opts["download_archive"] = str(Path(download_archive).expanduser())
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = _coerce_cookies_from_browser(cookies_from_browser)
    if extractor_args:
        opts["extractor_args"] = extractor_args
    if title_reject:
        opts["match_filter"] = _reject_title_filter(title_reject)
    opts.update(extra_opts or {})

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    results: list[DownloadResult] = []
    for entry in (info.get("entries") if info else None) or []:
        if not entry:
            continue  # selection/filter skipped it, or it failed under ignoreerrors
        path = _resolve_output_path(entry, ydl, out_dir, merge_to)
        sidecars = _collect_sidecars(
            entry,
            path,
            info_json=write_info_json,
            thumbnail=write_thumbnail,
            description=write_description,
            subtitles=write_subtitles or write_auto_subtitles,
        )
        results.append(
            DownloadResult(path=path, info=_trim_info(entry), sidecars=sidecars)
        )
    return results


def _coerce_cookies_from_browser(value: str | tuple) -> tuple:
    """Normalize ``cookies_from_browser`` into yt-dlp's ``cookiesfrombrowser`` tuple."""
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def _reject_title_filter(substring: str):
    """Build a yt-dlp ``match_filter`` that skips entries whose title contains ``substring``."""
    needle = substring.lower()

    def _filter(info_dict, *, incomplete=False):
        title = (info_dict.get("title") or "").lower()
        if needle in title:
            return f"skipping {info_dict.get('title')!r}: title matches reject {substring!r}"
        return None

    return _filter


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
