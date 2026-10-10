"""Paste-back OAuth consent: consent from a machine nobody is sitting at.

The normal flow (``InstalledAppFlow.run_local_server``) keeps a web server up on
``localhost`` and waits for Google to redirect the browser to it. That needs the
browser and the process to share a ``localhost`` — which a session driven from a
phone does not have: the consent page opens on the phone, the redirect goes to
the *phone's* ``localhost``, and the process (no terminal, nothing to wait on)
gives up with :class:`~yb.youtube.auth.ConsentRequired`.

Paste-back splits consent into two steps that need no shared network and no
live process in between, so they can happen in different turns, even in
different Python processes:

1. :func:`start_paste_consent` builds the authorization URL and saves the one
   thing the second step needs (the PKCE verifier and ``state``) to a short-lived
   file next to the token. The user opens the URL anywhere and consents.
2. Google redirects to ``http://localhost:<port>/?state=…&code=…``. That page
   will not load — expected. The user copies the address-bar URL (or just the
   ``code``) back, and :func:`finish_paste_consent` completes the exchange.

Most callers never import this module: ``get_credentials(consent="paste")`` and
the ``yb auth`` command drive it. Nothing here writes the token — the caller
(``get_credentials``) does, so there is one place that does.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Sequence
from urllib.parse import urlencode

from yb.youtube.auth import (
    DEFAULT_SCOPES,
    ConsentRequired,
    PathLike,
    _config_dir,
    _resolve_client_secrets,
)

#: The redirect target. Nothing listens there in paste mode — the page failing to
#: load is the expected outcome; only its address-bar URL matters.
DEFAULT_PASTE_PORT = 8080

#: How long a printed consent URL stays usable by :func:`finish_paste_consent`.
#: Generous, because the gap is a human's: a phone-driven session may take hours
#: to come back with the redirect. Google's own limit is on the one-time *code*
#: it issues after consent, not on the URL, so this only bounds our bookkeeping.
PENDING_TTL_S = 24 * 3600.0


class ConsentPending(ConsentRequired):
    """Consent was started, and now waits for the user to paste the redirect back.

    Not a failure: it is the *normal* result of the first call in paste mode.
    ``url`` is the address to open; the message says what to do with the result.
    Subclasses :class:`~yb.youtube.auth.ConsentRequired` so a caller that only
    handles "no credentials" still stops, while one that knows about paste mode
    can catch this and relay ``url``.
    """

    def __init__(self, url: str, *, redirect_uri: str):
        self.url = url
        self.redirect_uri = redirect_uri
        super().__init__(
            "YouTube consent is waiting for you.\n"
            f"1. Open this URL in any browser and approve:\n   {url}\n"
            f"2. The browser then tries to load {redirect_uri}... and fails to "
            "connect. That is expected. Copy the full URL from the address bar "
            "(or just its code=… value).\n"
            "3. Finish with: yb auth --paste '<that URL>'   or   "
            "get_credentials(consent='paste', authorization_response='<that URL>')"
        )


def pending_consent_file() -> Path:
    """Where the in-progress consent is kept (next to the token, mode 0600)."""
    return _config_dir() / "youtube_consent_pending.json"


def _redirect_uri(port: int) -> str:
    return f"http://localhost:{port}/"


def _flow(secrets: Path, scopes: Sequence[str], **flow_kwargs):
    from google_auth_oauthlib.flow import InstalledAppFlow

    return InstalledAppFlow.from_client_secrets_file(
        str(secrets), list(scopes), **flow_kwargs
    )


def _load_pending(pending: Path) -> dict | None:
    try:
        data = json.loads(pending.read_text())
    except (OSError, ValueError):
        return None
    fresh = time.time() - data.get("created_at", 0) < PENDING_TTL_S
    return data if fresh else None


def _save_pending(pending: Path, data: dict) -> None:
    pending.parent.mkdir(parents=True, exist_ok=True)
    # The verifier is the proof that whoever finishes consent also started it,
    # so it is created private rather than tightened afterwards.
    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh)


def start_paste_consent(
    *,
    client_secrets_file: PathLike | None = None,
    scopes: Sequence[str] = DEFAULT_SCOPES,
    port: int = DEFAULT_PASTE_PORT,
    pending_file: PathLike | None = None,
    reuse_pending: bool = True,
) -> str:
    """Begin paste-back consent and return the URL to open.

    A consent already pending for the same ``scopes`` and ``port`` is reused
    (``reuse_pending=True``): re-printing the URL must not invalidate the one the
    user already has open on their phone.
    """
    scopes = list(scopes)
    port = port or DEFAULT_PASTE_PORT
    pending = Path(pending_file) if pending_file else pending_consent_file()
    redirect_uri = _redirect_uri(port)

    saved = _load_pending(pending) if reuse_pending else None
    if saved and saved["scopes"] == scopes and saved["redirect_uri"] == redirect_uri:
        return saved["url"]

    flow = _flow(
        _resolve_client_secrets(client_secrets_file), scopes, redirect_uri=redirect_uri
    )
    url, state = flow.authorization_url(prompt="consent")
    _save_pending(
        pending,
        dict(
            url=url,
            state=state,
            code_verifier=flow.code_verifier,
            scopes=scopes,
            redirect_uri=redirect_uri,
            created_at=time.time(),
        ),
    )
    return url


def _response_url(text: str, saved: dict) -> str:
    """Whatever the user pasted, as the redirect URL the token exchange wants.

    Accepts the full URL (the documented case), the bare query string, or only
    the ``code`` — typing a long URL on a phone is the weak step, so tolerate the
    shortest thing that still carries the information.
    """
    text = text.strip().strip("<>\"'")
    if "://" in text:
        return text
    if "code=" in text:
        return f"{saved['redirect_uri']}?{text.lstrip('?')}"
    query = urlencode({"state": saved["state"], "code": text})
    return f"{saved['redirect_uri']}?{query}"


@contextmanager
def _allow_http_redirect():
    """oauthlib refuses ``http://``; a ``localhost`` redirect is http by design.

    ``run_local_server`` does the same dance internally.
    """
    key = "OAUTHLIB_INSECURE_TRANSPORT"
    before = os.environ.get(key)
    os.environ[key] = "1"
    try:
        yield
    finally:
        if before is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = before


def finish_paste_consent(
    authorization_response: str,
    *,
    client_secrets_file: PathLike | None = None,
    pending_file: PathLike | None = None,
):
    """Complete a consent begun by :func:`start_paste_consent`; return credentials.

    ``authorization_response`` is the redirected URL, its query string, or the
    bare ``code``. The pending file is removed on success and left in place on
    failure, so a mistyped paste can simply be retried.
    """
    from oauthlib.oauth2.rfc6749.errors import OAuth2Error

    pending = Path(pending_file) if pending_file else pending_consent_file()
    saved = _load_pending(pending)
    if saved is None:
        raise ConsentRequired(
            "No consent is pending (or it is older than "
            f"{PENDING_TTL_S / 3600:g}h). Start one first: `yb auth`, or "
            "get_credentials(consent='paste')."
        )
    flow = _flow(
        _resolve_client_secrets(client_secrets_file),
        saved["scopes"],
        redirect_uri=saved["redirect_uri"],
        state=saved["state"],
        code_verifier=saved["code_verifier"],
    )
    try:
        with _allow_http_redirect():
            flow.fetch_token(
                authorization_response=_response_url(authorization_response, saved)
            )
    except OAuth2Error as error:
        raise ConsentRequired(
            f"Google rejected the pasted redirect ({error.error or error}). "
            "Codes are single-use and expire within minutes — paste the URL "
            "from the browser that just consented, or open the same consent URL "
            "again for a fresh one."
        ) from error
    pending.unlink(missing_ok=True)
    return flow.credentials
