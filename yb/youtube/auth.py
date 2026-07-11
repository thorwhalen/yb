"""OAuth 2.0 plumbing for the YouTube Data API v3.

Runs the installed-app consent flow once (browser), caches the token, and
refreshes it silently thereafter. Needs only ``google-api-python-client`` +
``google-auth-oauthlib`` (``pip install 'yb[youtube]'``) and an OAuth client of
type *Desktop app* — point ``client_secrets_file`` at its JSON or set
``$YOUTUBE_CLIENT_SECRETS_FILE`` / ``$GOOGLE_CLIENT_SECRETS_FILE``.

No ``gcloud`` required: creating the project / enabling the API / making the
OAuth client is all doable in the Google Cloud console (the ``yb-setup`` skill
walks through it).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

PathLike = str | Path

#: Upload + force-ssl (the latter is needed for captions.insert and thumbnails.set).
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

_CLIENT_SECRETS_ENV = ("YOUTUBE_CLIENT_SECRETS_FILE", "GOOGLE_CLIENT_SECRETS_FILE")


def _config_dir() -> Path:
    """``yb`` config directory (``$XDG_CONFIG_HOME`` or ``~/.config``)/``yb``."""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "yb"


def default_token_file() -> Path:
    """Cached OAuth token location (``$XDG_CONFIG_HOME`` or ``~/.config``)."""
    return _config_dir() / "youtube_token.json"


def default_client_secrets_file() -> Path:
    """Default OAuth client-secrets location: ``<config dir>/client_secret.json``.

    Used when neither ``client_secrets_file=`` nor the env vars are set, so all
    of ``yb``'s state can live in one directory next to the token.
    """
    return _config_dir() / "client_secret.json"


def _resolve_client_secrets(client_secrets_file: PathLike | None) -> Path:
    if client_secrets_file:
        return Path(client_secrets_file).expanduser()
    for env in _CLIENT_SECRETS_ENV:
        val = os.environ.get(env)
        if val:
            return Path(val).expanduser()
    default = default_client_secrets_file()
    if default.exists():
        return default
    raise RuntimeError(
        "No OAuth client secrets. Pass client_secrets_file=, set one of "
        f"{', '.join(_CLIENT_SECRETS_ENV)}, or place the JSON at {default}. "
        "See the yb-setup skill."
    )


def get_credentials(
    *,
    client_secrets_file: PathLike | None = None,
    token_file: PathLike | None = None,
    scopes: Sequence[str] = DEFAULT_SCOPES,
    open_browser: bool = True,
):
    """Return OAuth user credentials, running the consent flow if needed.

    First use opens a browser for consent (or prints a URL when
    ``open_browser=False``) and caches the token to ``token_file`` so later
    calls are non-interactive. Expired tokens are refreshed automatically.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_path = Path(token_file) if token_file else default_token_file()
    scopes = list(scopes)
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if creds and creds.valid:
        return creds

    refreshed = False
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            refreshed = True
        except RefreshError:
            # Token revoked/expired beyond refresh (e.g. an OAuth app in
            # "Testing" mode rotates refresh tokens out after 7 days). Fall back
            # to a fresh interactive consent rather than propagating the error.
            creds = None
    if not refreshed:
        secrets = _resolve_client_secrets(client_secrets_file)
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets), scopes)
        creds = flow.run_local_server(port=0) if open_browser else flow.run_console()

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds


def get_service(*, credentials=None, **cred_kwargs):
    """Build a YouTube Data API v3 service object."""
    from googleapiclient.discovery import build

    credentials = credentials or get_credentials(**cred_kwargs)
    return build("youtube", "v3", credentials=credentials)
