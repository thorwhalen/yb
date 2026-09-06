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

from yb.youtube.auth import get_credentials  # noqa: E402  (needs the gate above)

#: Keywords ``get_credentials`` drives the consent flow with, and the value each
#: takes when the caller says nothing. Every case below asserts the *whole* call,
#: so a dropped, renamed, or silently rewritten keyword fails the suite.
CONSENT_DEFAULTS = {"port": 0, "open_browser": True, "timeout_seconds": None}


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
