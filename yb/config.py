"""User configuration for ``yb`` publishing defaults.

Single source of truth for the publishing defaults you don't want to repeat on
every call — the privacy a new upload gets, and a playlist to drop every upload
into so you can find your videos later. The config lives next to the OAuth token
(``$XDG_CONFIG_HOME/yb/config.json`` or ``~/.config/yb/config.json``) so all of
``yb``'s persistent state sits in one directory.

The file is **optional**: with no file present the built-in defaults apply
(``privacy_status="unlisted"``, no playlist). Any subset of keys may be set;
unspecified keys fall back to the built-in defaults, and unknown keys are
ignored (forward-compatible).

Example ``~/.config/yb/config.json``::

    {
        "privacy_status": "unlisted",
        "playlist": "TW Uploads",
        "create_playlist_if_missing": true,
        "playlist_privacy_status": "private"
    }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields
from pathlib import Path

PathLike = str | Path

#: Default privacy for a freshly uploaded video when neither the call nor the
#: config file specifies one. ``"unlisted"`` keeps videos off your public feed
#: but shareable by link until you deliberately make one ``"public"``.
DEFAULT_PRIVACY_STATUS = "unlisted"

#: Default privacy for a playlist that ``yb`` auto-creates. ``"private"`` means
#: only you see it — ideal for a personal "find my uploads" playlist.
DEFAULT_PLAYLIST_PRIVACY_STATUS = "private"


def default_config_file() -> Path:
    """Config file location (``$XDG_CONFIG_HOME`` or ``~/.config``)."""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "yb" / "config.json"


@dataclass(frozen=True)
class YbConfig:
    """Resolved publishing defaults.

    Attributes:
        privacy_status: Privacy a new upload gets (``unlisted`` | ``private`` |
            ``public``) when the call doesn't override it.
        playlist: Title of a playlist every upload is added to (``None`` = none).
        create_playlist_if_missing: Create ``playlist`` if no playlist of that
            title exists yet, rather than erroring.
        playlist_privacy_status: Privacy for an auto-created playlist.
    """

    privacy_status: str = DEFAULT_PRIVACY_STATUS
    playlist: str | None = None
    create_playlist_if_missing: bool = True
    playlist_privacy_status: str = DEFAULT_PLAYLIST_PRIVACY_STATUS

    @classmethod
    def from_mapping(cls, mapping: dict | None) -> "YbConfig":
        """Build a config from a mapping, ignoring unknown keys."""
        mapping = mapping or {}
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in mapping.items() if k in known})


def load_config(config_file: PathLike | None = None, **overrides) -> YbConfig:
    """Load publishing defaults from ``config_file`` (or the default location).

    A missing file yields the built-in defaults. ``overrides`` (typically the
    explicit keyword arguments a caller passed) take precedence when not
    ``None``, so call-site arguments always win over the file.
    """
    path = Path(config_file).expanduser() if config_file else default_config_file()
    data: dict = {}
    if path.exists():
        data = json.loads(path.read_text())
    data.update({k: v for k, v in overrides.items() if v is not None})
    return YbConfig.from_mapping(data)
