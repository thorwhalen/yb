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


class ConsentRequired(RuntimeError):
    """Consent is needed and this process cannot obtain it.

    Raised instead of starting a consent flow that nobody can complete. The
    alternative is worse than an error: ``run_local_server`` prints a URL to a
    stdout nobody is reading and waits on ``localhost`` for a redirect that will
    never arrive, so an automated caller *blocks* rather than failing. That has
    happened — an upload stopped dead mid-script and read as a slow network for
    hours, when the underlying cause was one line of ``invalid_grant``.
    """


#: Ways to obtain consent: ``"local"`` waits for a redirect on this machine's
#: ``localhost``; ``"paste"`` is two-step and needs no shared network (see
#: :mod:`yb.youtube.paste_consent`).
CONSENT_MODES = ("local", "paste")

#: How long consent may wait for its redirect before giving up.
#:
#: The library's own default is "wait indefinitely", which is not a good default
#: for anything: a caller that cannot complete consent then *blocks* rather than
#: failing, and an automated upload reads as a slow network until someone thinks
#: to run ``ps``. Five minutes is long enough for a human to find the tab and
#: click through an unverified-app warning, and short enough that a machine
#: finds out today. Pass ``timeout_seconds=None`` for the old behaviour.
DEFAULT_CONSENT_TIMEOUT_S = 300.0


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


def _consent_required_message(refresh_error, token_path: Path) -> str:
    """Why consent is needed, and the two things that fix it.

    Both halves earn their place. The *cause* is invisible otherwise — the
    underlying ``invalid_grant`` is swallowed by the fallback, so a caller sees
    only that something wants a browser. The *permanent* remedy matters because
    the usual one (re-consent) buys about seven days: an OAuth client left in
    "Testing" rotates refresh tokens out on that cycle, so anything scheduled
    breaks again next week unless the consent screen is published.
    """
    cause = (
        f"the cached token could not be refreshed ({refresh_error})"
        if refresh_error is not None
        else f"no usable cached token at {token_path}"
    )
    return (
        f"YouTube consent is required ({cause}), but this process cannot obtain "
        "it: there is no terminal, so the consent URL has nowhere to go.\n"
        "\n"
        "To re-consent now, from a shell you are watching:\n"
        "    python -c 'from yb.youtube import get_credentials; "
        "get_credentials(interactive=True)'\n"
        "or, with no browser or terminal here (e.g. a phone-driven session), "
        "paste-back consent -- print a URL, open it anywhere, paste the "
        "redirect back:\n"
        "    yb auth            # then: yb auth --paste '<redirected URL>'\n"
        "    get_credentials(consent='paste')\n"
        "\n"
        'To stop this recurring: an OAuth client in "Testing" rotates refresh '
        "tokens out after ~7 days. Publishing the consent screen (Google Cloud "
        "console -> APIs & Services -> Google Auth Platform -> Audience -> "
        "Publish app) removes that expiry; the unverified-app warning at "
        "consent time is the only cost.\n"
        "\n"
        "Pass interactive=True to run the flow here anyway (consent='paste' "
        "for the two-step form)."
    )


def _paste_consent(authorization_response, *, client_secrets_file, scopes, port):
    """Paste-back consent: finish if given the redirect, else start and raise."""
    from yb.youtube.paste_consent import (
        DEFAULT_PASTE_PORT,
        ConsentPending,
        _redirect_uri,
        finish_paste_consent,
        start_paste_consent,
    )

    if authorization_response:
        return finish_paste_consent(
            authorization_response, client_secrets_file=client_secrets_file
        )
    url = start_paste_consent(
        client_secrets_file=client_secrets_file, scopes=scopes, port=port
    )
    raise ConsentPending(url, redirect_uri=_redirect_uri(port or DEFAULT_PASTE_PORT))


def get_credentials(
    *,
    client_secrets_file: PathLike | None = None,
    token_file: PathLike | None = None,
    scopes: Sequence[str] = DEFAULT_SCOPES,
    open_browser: bool = True,
    port: int = 0,
    timeout_seconds: float | None = DEFAULT_CONSENT_TIMEOUT_S,
    interactive: bool = True,
    consent: str = "local",
    authorization_response: str | None = None,
):
    """Return OAuth user credentials, running the consent flow if needed.

    First use runs the installed-app consent flow and caches the token to
    ``token_file`` so later calls are non-interactive. Expired tokens are
    refreshed automatically.

    Pass ``interactive=False`` when nobody can answer a consent prompt — a cron
    job, a queue worker, an agent. Consent is then never started; a token that
    cannot be refreshed raises :class:`ConsentRequired` naming the cause and the
    fix. This is not an edge case: an OAuth client left in "Testing" rotates
    refresh tokens out after about seven days, so anything scheduled hits it
    weekly.

    Even with the default ``interactive=True`` the call can no longer hang:
    consent is bounded by ``timeout_seconds``
    (:data:`DEFAULT_CONSENT_TIMEOUT_S`), and a timeout is reported as the same
    :class:`ConsentRequired`, because "nobody answered" and "nobody could
    answer" want the same thing done about them.

    Consent always goes through a temporary local web server on ``port`` (``0``
    picks a free one), because Google retired the copy-paste "out-of-band" flow
    in 2022. ``open_browser=False`` only stops the browser from being launched:
    the authorization URL is printed instead, and the redirect must still reach
    that local server.

    Headless recipe: pass ``interactive=True`` (there is no terminal, so the
    default would refuse), ``open_browser=False`` and a fixed ``port=``, then
    forward that port from the machine holding the browser
    (``ssh -L <port>:localhost:<port> <host>``). Nothing needs registering in
    the Cloud console — the *Desktop app* client this module requires accepts
    any ``localhost`` port, which is also why the ``port=0`` default works.

    The call blocks until the redirect arrives, bounded by ``timeout_seconds``
    (default :data:`DEFAULT_CONSENT_TIMEOUT_S`; pass ``None`` for the library's
    "wait indefinitely", which is what this used to do).

    **No shared ``localhost``? Use** ``consent="paste"``. Consent then needs no
    running server and no waiting: the first call returns by raising
    :class:`~yb.youtube.paste_consent.ConsentPending` carrying the URL to open
    (anywhere — a phone will do); the browser's redirect to ``localhost`` fails
    to load, and the second call passes that address-bar URL (or just its
    ``code``) as ``authorization_response=`` to finish and cache the token. The
    two calls may be separate turns or separate processes; ``yb auth`` is the
    command-line form. ``port`` only names the (unreachable) redirect.

    These keywords ride ``**cred_kwargs`` through :func:`get_service` and the
    publishing helpers. The few entry points that take none (notably
    :func:`yb.music.publish.publish_folder`) still work headlessly: call this
    once to mint the token, after which nothing prompts again.
    """
    if consent not in CONSENT_MODES:
        raise ValueError(f"consent must be one of {CONSENT_MODES}, got {consent!r}")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    from google_auth_oauthlib.flow import InstalledAppFlow

    try:  # the flow's own timeout error; older releases may not define it
        from google_auth_oauthlib.flow import WSGITimeoutError as _WSGITimeoutError
    except ImportError:  # pragma: no cover - depends on the installed version

        class _WSGITimeoutError(Exception):
            """Never raised; keeps the except-clause valid on older releases."""

    token_path = Path(token_file) if token_file else default_token_file()
    scopes = list(scopes)
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if creds and creds.valid:
        return creds

    refreshed = False
    refresh_error: RefreshError | None = None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            refreshed = True
        except RefreshError as error:
            # Token revoked/expired beyond refresh (e.g. an OAuth app in
            # "Testing" mode rotates refresh tokens out after 7 days). Fall back
            # to a fresh interactive consent rather than propagating the error —
            # but only where consent can actually be given (see below).
            refresh_error = error
            creds = None
    if not refreshed:
        if not interactive:
            raise ConsentRequired(_consent_required_message(refresh_error, token_path))
        if consent == "paste":
            creds = _paste_consent(
                authorization_response,
                client_secrets_file=client_secrets_file,
                scopes=scopes,
                port=port,
            )
        else:
            secrets = _resolve_client_secrets(client_secrets_file)
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets), scopes)
            try:
                creds = flow.run_local_server(
                    port=port,
                    open_browser=open_browser,
                    timeout_seconds=timeout_seconds,
                )
            except _WSGITimeoutError as timed_out:
                # Nobody answered. Whatever the caller thought it was doing, the
                # actionable facts are the same ones `interactive=False` reports
                # — so report them, rather than a bare timeout from a library
                # the caller never named.
                raise ConsentRequired(
                    _consent_required_message(refresh_error, token_path)
                ) from timed_out

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds


def get_service(*, credentials=None, **cred_kwargs):
    """Build a YouTube Data API v3 service object.

    ``cred_kwargs`` are forwarded to :func:`get_credentials` (``token_file=``,
    ``open_browser=``, ``port=``, ...) unless ``credentials`` is given.
    """
    from googleapiclient.discovery import build

    credentials = credentials or get_credentials(**cred_kwargs)
    return build("youtube", "v3", credentials=credentials)
