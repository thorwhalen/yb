"""Publish songs to YouTube as music videos.

You have a song and (usually) its cover art; YouTube wants a video. This module
closes that gap and hands off to the publishing machinery ``yb`` already has:

    >>> from yb.music import prepare_music_video, publish_music
    >>> mv = prepare_music_video("song.wav", image="cover.png")   # doctest: +SKIP
    >>> mv.video, mv.thumbnail                                    # doctest: +SKIP
    (PosixPath('song.mp4'), PosixPath('song.thumb.jpg'))

    >>> publish_music("song.wav", image="cover.png",              # doctest: +SKIP
    ...               privacy_status="unlisted")

The picture is chosen by a *visual strategy* — a still cover on a 16:9 canvas
(the default), a Ken Burns pan, or an audio-reactive visualizer — and any
callable of your own plugs into the same seam. See :mod:`yb.render.visuals`.

Rendering needs only ``ffmpeg`` on the PATH; uploading needs ``pip install
'yb[youtube]'``.
"""

from yb.music.publish import (
    CATEGORY_MUSIC,
    MusicVideo,
    prepare_music_video,
    prepare_music_videos,
    publish_music,
)

__all__ = [
    "CATEGORY_MUSIC",
    "MusicVideo",
    "prepare_music_video",
    "prepare_music_videos",
    "publish_music",
]
