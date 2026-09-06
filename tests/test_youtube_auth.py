"""Tests for the OAuth consent flow in ``yb.youtube.auth``.

Offline and credential-free: ``InstalledAppFlow.from_client_secrets_file`` is
patched to hand back a ``Mock(spec=InstalledAppFlow)``. The ``spec=`` is
load-bearing — it gives the mock exactly the real class's attribute surface, so
a call to a method Google has removed (``run_console``) fails here just as it
does against a live install.
"""

from unittest import mock

import pytest

from yb.youtube.auth import get_credentials

flow_module = pytest.importorskip("google_auth_oauthlib.flow")
InstalledAppFlow = flow_module.InstalledAppFlow


@pytest.fixture
def consent_flow(tmp_path):
    """Patch the consent flow and yield ``(flow, get_credentials_kwargs)``.

    ``flow`` is the mock whose ``run_local_server`` records how consent was
    driven; the kwargs point ``get_credentials`` at throwaway files.
    """
    secrets = tmp_path / "client_secret.json"
    secrets.write_text("{}")
    flow = mock.Mock(spec=InstalledAppFlow)
    flow.run_local_server.return_value = mock.Mock(to_json=lambda: "{}")
    with mock.patch.object(
        InstalledAppFlow, "from_client_secrets_file", return_value=flow
    ):
        yield (
            flow,
            dict(client_secrets_file=secrets, token_file=tmp_path / "token.json"),
        )


def test_headless_consent_uses_run_local_server(consent_flow):
    """``open_browser=False`` must reach the flow, not a method Google removed."""
    flow, kwargs = consent_flow
    get_credentials(open_browser=False, **kwargs)
    assert flow.run_local_server.call_args.kwargs["open_browser"] is False


def test_port_is_forwarded(consent_flow):
    """A fixed ``port=`` is needed for SSH-forwarded headless consent."""
    flow, kwargs = consent_flow
    get_credentials(port=8080, **kwargs)
    assert flow.run_local_server.call_args.kwargs["port"] == 8080


def test_browser_path_unchanged(consent_flow):
    """Regression guard: the default path is still an ephemeral-port server."""
    flow, kwargs = consent_flow
    get_credentials(open_browser=True, **kwargs)
    assert flow.run_local_server.call_args.kwargs["port"] == 0
