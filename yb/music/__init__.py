"""Publish songs to YouTube as music videos.

You have a song and (usually) its cover art; YouTube wants a video. This module
renders one (via :mod:`muvid.visualize`) and hands off to the publishing
machinery ``yb`` already has:

    >>> from yb.music import prepare_music_video, publish_music
    >>> mv = prepare_music_video("song.wav", image="cover.png")   # doctest: +SKIP
    >>> mv.video, mv.thumbnail                                    # doctest: +SKIP
    (PosixPath('song.mp4'), PosixPath('song.thumb.jpg'))

    >>> publish_music("song.wav", image="cover.png",              # doctest: +SKIP
    ...               privacy_status="unlisted")

A whole folder of ``(song, cover)`` pairs becomes an album, each song rendered
with the next visual in a rotation:

    >>> from yb.music import publish_folder
    >>> publish_folder("~/album", limit=1)         # test the first song  # doctest: +SKIP
    >>> publish_folder("~/album", playlist="My Album")   # then the rest  # doctest: +SKIP

The picture is chosen by a *visual strategy* — a still cover on a 16:9 canvas, a
Ken Burns pan, or an audio-reactive visualizer — and any callable of your own
plugs into the same seam. See :mod:`muvid.visualize`.

Needs ``pip install 'yb[music]'`` (pulls ``muvid``, which needs ``ffmpeg``);
uploading additionally needs ``yb[youtube]``.
"""

from yb.music.publish import (
    CATEGORY_MUSIC,
    DEFAULT_VISUAL_CYCLE,
    FolderItem,
    MusicVideo,
    pair_folder,
    prepare_folder,
    prepare_music_video,
    prepare_music_videos,
    publish_folder,
    publish_music,
)

__all__ = [
    "CATEGORY_MUSIC",
    "DEFAULT_VISUAL_CYCLE",
    "FolderItem",
    "MusicVideo",
    "pair_folder",
    "prepare_folder",
    "prepare_music_video",
    "prepare_music_videos",
    "publish_folder",
    "publish_music",
]
