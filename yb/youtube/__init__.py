"""YouTube publishing via the YouTube Data API v3.

Optionally installed (``pip install 'yb[youtube]'``). Needs an OAuth Desktop
client (see the ``yb-setup`` skill) — set ``$YOUTUBE_CLIENT_SECRETS_FILE``.

Create:
    >>> from yb.youtube import prepare_and_publish  # doctest: +SKIP
    >>> prepare_and_publish("promo.fr.mp4", language="French", language_code="fr",  # doctest: +SKIP
    ...                     audio_language_code="fr", privacy_status="unlisted")

Edit an existing video:
    >>> from yb.youtube import update_video_fields, upsert_caption, set_chapters  # doctest: +SKIP
    >>> update_video_fields("VIDEO_ID", title="New title")  # doctest: +SKIP
    >>> upsert_caption("VIDEO_ID", "subs.fr.srt", language="fr", name="Français")  # doctest: +SKIP
"""

from yb.youtube.auth import (
    DEFAULT_SCOPES,
    get_credentials,
    get_service,
    default_token_file,
)
from yb.youtube.metadata import (
    VideoMetadata,
    CATEGORY_SCIENCE_TECH,
    CATEGORY_EDUCATION,
    CATEGORY_PEOPLE_BLOGS,
    CATEGORY_ENTERTAINMENT,
)
from yb.youtube.api import (
    get_video,
    upload_video,
    update_video,
    update_video_fields,
    set_thumbnail,
    set_chapters,
)
from yb.youtube.stats import (
    video_metadata,
    flatten_video,
    select_fields,
    resolve_fields,
    render_table,
    FIELD_GROUPS,
    DEFAULT_PARTS,
)
from yb.youtube.captions import (
    CaptionTrack,
    list_captions,
    insert_caption,
    update_caption,
    upsert_caption,
    download_caption,
    delete_caption,
)
from yb.youtube.publish import (
    publish_content,
    prepare_and_publish,
    publish_video,
)

__all__ = [
    "DEFAULT_SCOPES",
    "get_credentials",
    "get_service",
    "default_token_file",
    "VideoMetadata",
    "CATEGORY_SCIENCE_TECH",
    "CATEGORY_EDUCATION",
    "CATEGORY_PEOPLE_BLOGS",
    "CATEGORY_ENTERTAINMENT",
    "get_video",
    "upload_video",
    "update_video",
    "update_video_fields",
    "set_thumbnail",
    "set_chapters",
    "video_metadata",
    "flatten_video",
    "select_fields",
    "resolve_fields",
    "render_table",
    "FIELD_GROUPS",
    "DEFAULT_PARTS",
    "CaptionTrack",
    "list_captions",
    "insert_caption",
    "update_caption",
    "upsert_caption",
    "download_caption",
    "delete_caption",
    "publish_content",
    "prepare_and_publish",
    "publish_video",
]
