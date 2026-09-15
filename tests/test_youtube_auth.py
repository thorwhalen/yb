"""Tests for the OAuth consent flow in ``yb.youtube.auth``.

Offline and credential-free: ``InstalledAppFlow.from_client_secrets_file`` is
patched to hand back an autospecced stand-in for the real class, so the mock
carries that class's attribute surface and method signatures. A call to
something Google has removed (``run_console``, the cause of #7) therefore fails
here the way it fails against a live install.

``spec``/``autospec`` can only police attribute names and *our* call, though —
never the callee's own parameter list. :func:`test_run_local_server_contract`
covers that gap by asserting, against the installed library, that the keywords
this module passes still exist.
"""

import inspect
from unittest import mock

import pytest

flow_module = pytest.importorskip("google_auth_oauthlib.flow")
InstalledAppFlow = flow_module.InstalledAppFlow

from google.auth.exceptions import RefreshError as _RefreshError  # noqa: E402
from google.oauth2.credentials import Credentials as _Credentials  # noqa: E402

from yb.youtube.auth import (  # noqa: E402  (needs the gate above)
    DEFAULT_CONSENT_TIMEOUT_S,
    ConsentRequired,
    get_credentials,
)

#: The flow's own timeout error, or a stand-in on releases that lack it.
_WSGITimeoutError = getattr(flow_module, "WSGITimeoutError", TimeoutError)

#: Keywords ``get_credentials`` drives the consent flow with, and the value each
#: takes when the caller says nothing. Every case below asserts the *whole* call,
#: so a dropped, renamed, or silently rewritten keyword fails the suite.
CONSENT_DEFAULTS = {
    "port": 0,
    "open_browser": True,
    "timeout_seconds": DEFAULT_CONSENT_TIMEOUT_S,
}


def _expected(**overrides):
    return {**CONSENT_DEFAULTS, **overrides}


@pytest.fixture
def consent_flow(tmp_path):
    """Patch the consent flow and yield ``(flow, get_credentials_kwargs)``.

    ``flow`` is the mock whose ``run_local_server`` records how consent was
    driven; the kwargs point ``get_credentials`` at throwaway files.
    """
    secrets = tmp_path / "client_secret.json"
    secrets.write_text("{}")
    flow = mock.create_autospec(InstalledAppFlow, instance=True)
    flow.run_local_server.return_value = mock.Mock(to_json=lambda: "{}")
    with mock.patch.object(
        InstalledAppFlow, "from_client_secrets_file", return_value=flow
    ):
        yield (
            flow,
            dict(client_secrets_file=secrets, token_file=tmp_path / "token.json"),
        )


@pytest.mark.parametrize(
    "caller_kwargs, expected",
    [
        pytest.param({}, _expected(), id="defaults-open-a-browser-on-a-free-port"),
        pytest.param(
            {"open_browser": False},
            _expected(open_browser=False),
            id="headless-consent-reaches-the-flow-not-a-removed-method",
        ),
        pytest.param(
            {"port": 8080}, _expected(port=8080), id="a-pinned-port-is-forwarded"
        ),
        # The combination is the whole point of #7: an SSH-forwarded consent
        # needs the pinned port kept *on the headless path* specifically.
        pytest.param(
            {"open_browser": False, "port": 8080},
            _expected(open_browser=False, port=8080),
            id="headless-plus-pinned-port-the-ssh--L-recipe",
        ),
        pytest.param(
            {"timeout_seconds": 300},
            _expected(timeout_seconds=300),
            id="the-wait-can-be-bounded",
        ),
    ],
)
def test_consent_kwargs_reach_the_local_server(consent_flow, caller_kwargs, expected):
    """Whatever the caller asks for is what the local consent server gets."""
    flow, kwargs = consent_flow
    get_credentials(**caller_kwargs, **kwargs)
    assert flow.run_local_server.call_args.kwargs == expected


def test_run_local_server_contract():
    """The installed library still takes the keywords ``auth`` passes it.

    The equivalent assertion on ``run_console`` is what would have caught #7 at
    test time rather than at a user's first headless consent.
    """
    params = inspect.signature(InstalledAppFlow.run_local_server).parameters
    assert set(CONSENT_DEFAULTS) <= set(params)


# --------------------------------------------------------------------------- #
# #13 — a caller that cannot consent must be told, not blocked
# --------------------------------------------------------------------------- #

class TestConsentNeverHangs:
    """The reported failure: an automated upload stopped dead and stayed there.

    A refresh token had expired (an OAuth client in "Testing" rotates them out
    after ~7 days). ``get_credentials`` swallowed the ``invalid_grant`` and fell
    back to ``run_local_server``, which printed a consent URL to a stdout nobody
    was reading and waited on localhost for a redirect that could never arrive.
    With ``timeout_seconds=None`` that wait was unbounded, so the process blocked
    for hours and read as a slow network.

    Every assertion here is about the *shape* of the failure: it must be an
    exception, it must arrive, and it must say what to do about it.
    """

    @staticmethod
    def _dead_token(tmp_path):
        """A cached token whose refresh fails the way a rotated-out one does."""
        token = tmp_path / "token.json"
        token.write_text("{}")
        creds = mock.Mock(valid=False, expired=True, refresh_token="r")
        creds.refresh.side_effect = _RefreshError("Token has been expired or revoked.")
        return token, creds

    def test_non_interactive_raises_instead_of_starting_a_flow(
        self, consent_flow, tmp_path
    ):
        flow, kwargs = consent_flow
        token, creds = self._dead_token(tmp_path)
        with mock.patch.object(
            _Credentials, "from_authorized_user_file", return_value=creds
        ):
            with pytest.raises(ConsentRequired):
                get_credentials(**{**kwargs, "token_file": token}, interactive=False)
        flow.run_local_server.assert_not_called()

    def test_the_message_names_the_cause_and_both_remedies(
        self, consent_flow, tmp_path
    ):
        """A traceback nobody can act on is barely better than the hang."""
        _, kwargs = consent_flow
        token, creds = self._dead_token(tmp_path)
        with mock.patch.object(
            _Credentials, "from_authorized_user_file", return_value=creds
        ):
            with pytest.raises(ConsentRequired) as excinfo:
                get_credentials(**{**kwargs, "token_file": token}, interactive=False)
        message = str(excinfo.value)
        assert "expired or revoked" in message  # the cause, no longer swallowed
        assert "interactive=True" in message  # how to re-consent now
        assert "Testing" in message  # why it will happen again
        assert "Publish app" in message  # how to stop it happening again

    def test_a_timeout_is_reported_as_the_same_actionable_error(
        self, consent_flow, tmp_path
    ):
        """"Nobody answered" and "nobody could answer" want the same fix."""
        flow, kwargs = consent_flow
        token, creds = self._dead_token(tmp_path)
        flow.run_local_server.side_effect = _WSGITimeoutError("timed out")
        with mock.patch.object(
            _Credentials, "from_authorized_user_file", return_value=creds
        ):
            with pytest.raises(ConsentRequired) as excinfo:
                get_credentials(**{**kwargs, "token_file": token})
        assert "Publish app" in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, _WSGITimeoutError)

    def test_consent_is_bounded_by_default(self, consent_flow):
        """The hang itself: the library's own default is "wait indefinitely"."""
        flow, kwargs = consent_flow
        get_credentials(**kwargs)
        assert DEFAULT_CONSENT_TIMEOUT_S is not None
        assert (
            flow.run_local_server.call_args.kwargs["timeout_seconds"]
            == DEFAULT_CONSENT_TIMEOUT_S
        )

    def test_an_explicit_none_still_waits_forever(self, consent_flow):
        """The old behaviour stays reachable for anyone who wants it."""
        flow, kwargs = consent_flow
        get_credentials(**kwargs, timeout_seconds=None)
        assert flow.run_local_server.call_args.kwargs["timeout_seconds"] is None

    def test_a_valid_cached_token_never_consults_any_of_this(
        self, consent_flow, tmp_path
    ):
        """The common path must stay silent, offline and unchanged."""
        flow, kwargs = consent_flow
        token = tmp_path / "token.json"
        token.write_text("{}")
        good = mock.Mock(valid=True)
        with mock.patch.object(
            _Credentials, "from_authorized_user_file", return_value=good
        ):
            assert get_credentials(**{**kwargs, "token_file": token}) is good
        flow.run_local_server.assert_not_called()
