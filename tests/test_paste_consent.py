"""Tests for paste-back consent (#17): headless, two-step, no live OAuth.

The consent URL is built by the *real* ``InstalledAppFlow`` (that step is pure
computation, no network), so state/PKCE plumbing is exercised for real. Only the
final token exchange — the one call that would reach Google — is replaced.
"""

import json
import os
import pickle
import stat
import sys
import time
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest

flow_module = pytest.importorskip("google_auth_oauthlib.flow")
InstalledAppFlow = flow_module.InstalledAppFlow

from oauthlib.oauth2.rfc6749.errors import InvalidGrantError  # noqa: E402

from yb.__main__ import main  # noqa: E402
from yb.youtube import paste_consent  # noqa: E402
from yb.youtube.auth import ConsentRequired, get_credentials  # noqa: E402
from yb.youtube.paste_consent import (  # noqa: E402
    ConsentPending,
    finish_paste_consent,
    start_paste_consent,
)

REDIRECT = "http://localhost:8080/"


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Throwaway client secrets + files; ``XDG_CONFIG_HOME`` kept off the real one."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    for name in ("YOUTUBE_CLIENT_SECRETS_FILE", "GOOGLE_CLIENT_SECRETS_FILE"):
        monkeypatch.delenv(name, raising=False)
    secrets = tmp_path / "client_secret.json"
    secrets.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "cid.apps.example",
                    "client_secret": "not-a-real-secret",
                    "auth_uri": "https://accounts.example/auth",
                    "token_uri": "https://accounts.example/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
        )
    )
    return dict(
        secrets=secrets,
        pending=tmp_path / "pending.json",
        token=tmp_path / "token.json",
    )


@pytest.fixture
def exchange():
    """Replace the one network call; yield the recorder of how it was driven."""
    creds = mock.Mock(to_json=lambda: '{"fake": "token"}')
    with mock.patch.object(
        InstalledAppFlow, "fetch_token", autospec=True
    ) as fetch, mock.patch.object(
        InstalledAppFlow, "credentials", new_callable=mock.PropertyMock
    ) as creds_prop:
        creds_prop.return_value = creds
        fetch.creds = creds
        yield fetch


def _start(env, **kw):
    return start_paste_consent(
        client_secrets_file=env["secrets"], pending_file=env["pending"], **kw
    )


def _finish(env, pasted):
    return finish_paste_consent(
        pasted, client_secrets_file=env["secrets"], pending_file=env["pending"]
    )


def _query(url):
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


class TestStart:
    def test_url_is_a_pkce_offline_consent_for_the_paste_redirect(self, env):
        query = _query(_start(env))
        assert query["redirect_uri"] == REDIRECT
        assert query["code_challenge_method"] == "S256"
        assert query["access_type"] == "offline"
        assert query["prompt"] == "consent"  # else Google may omit a refresh token

    def test_what_step_two_needs_is_saved_privately(self, env):
        url = _start(env)
        saved = json.loads(env["pending"].read_text())
        assert saved["state"] == _query(url)["state"]
        assert len(saved["code_verifier"]) >= 43
        if sys.platform != "win32":
            assert stat.S_IMODE(os.stat(env["pending"]).st_mode) == 0o600

    def test_asking_again_keeps_the_url_the_user_already_has_open(self, env):
        assert _start(env) == _start(env)

    def test_a_different_request_gets_a_fresh_url(self, env):
        first = _start(env)
        assert _start(env, port=9090) != first
        assert _start(env, reuse_pending=False) != first

    def test_a_swapped_client_does_not_inherit_the_old_clients_url(self, env):
        first = _start(env)
        other = json.loads(env["secrets"].read_text())
        other["installed"]["client_id"] = "someone-else.apps.example"
        env["secrets"].write_text(json.dumps(other))
        assert _start(env) != first
        assert "someone-else" in _start(env)

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX modes")
    def test_a_looser_preexisting_file_is_tightened(self, env):
        env["pending"].write_text("{}")
        env["pending"].chmod(0o644)
        _start(env)
        assert stat.S_IMODE(os.stat(env["pending"]).st_mode) == 0o600

    @pytest.mark.parametrize("junk", ["[]", "not json", '{"url": "x"}'])
    def test_a_damaged_pending_file_is_treated_as_absent(self, env, junk):
        env["pending"].write_text(junk)
        assert _start(env).startswith("https://")

    def test_an_expired_pending_is_replaced(self, env):
        first = _start(env)
        saved = json.loads(env["pending"].read_text())
        saved["created_at"] = time.time() - paste_consent.PENDING_TTL_S - 1
        env["pending"].write_text(json.dumps(saved))
        assert _start(env) != first


class TestFinish:
    @pytest.mark.parametrize(
        "paste",
        [
            pytest.param("{redirect}?state={state}&code=4%2FABC", id="full-url"),
            pytest.param("state={state}&code=4%2FABC", id="query-string"),
            pytest.param("4/ABC", id="bare-code"),
            pytest.param("?code=4%2FABC&state={state}", id="query-with-question-mark"),
            pytest.param("  <{redirect}?state={state}&code=4%2FABC>\n", id="messy"),
        ],
    )
    def test_every_way_of_pasting_ends_in_the_same_exchange(
        self, env, exchange, paste
    ):
        url = _start(env)
        saved = json.loads(env["pending"].read_text())
        pasted = paste.format(redirect=REDIRECT, state=saved["state"])

        assert _finish(env, pasted) is exchange.creds

        (flow,), kwargs = exchange.call_args
        response = _query(kwargs["authorization_response"])
        assert response == {"state": saved["state"], "code": "4/ABC"}
        # The exchange is made by a flow rebuilt from the file — same PKCE
        # verifier and state as the process that printed the URL.
        assert flow.code_verifier == saved["code_verifier"]
        assert flow.oauth2session._state == _query(url)["state"]
        assert flow.redirect_uri == REDIRECT

    def test_a_url_from_another_consent_is_rejected_before_any_exchange(self, env):
        """State is checked for real here (oauthlib, no network involved)."""
        _start(env)
        wrong = f"{REDIRECT}?state=someone-elses&code=4%2FABC"
        with pytest.raises(ConsentRequired, match="different consent request"):
            _finish(env, wrong)
        assert env["pending"].exists()

    def test_a_query_without_state_is_refused_but_a_bare_code_is_not(
        self, env, exchange
    ):
        _start(env)
        with pytest.raises(ConsentRequired, match="no state"):
            _finish(env, "code=4%2FABC")
        with pytest.raises(ConsentRequired, match="no state"):
            _finish(env, f"{REDIRECT}?code=4%2FABC")
        assert _finish(env, "4/ABC") is exchange.creds  # PKCE still binds it

    def test_granting_fewer_scopes_is_explained_not_a_traceback(self, env, exchange):
        exchange.side_effect = Warning("Scope has changed")
        _start(env)
        with pytest.raises(ConsentRequired, match="every box"):
            _finish(env, "4/ABC")

    def test_success_consumes_the_pending_file(self, env, exchange):
        _start(env)
        _finish(env, "4/ABC")
        assert not env["pending"].exists()

    def test_the_http_redirect_is_allowed_only_while_exchanging(self, env, exchange):
        seen = {}
        exchange.side_effect = lambda *a, **k: seen.update(
            flag=os.environ.get("OAUTHLIB_INSECURE_TRANSPORT")
        )
        _start(env)
        _finish(env, "4/ABC")
        assert seen["flag"] == "1"
        assert "OAUTHLIB_INSECURE_TRANSPORT" not in os.environ

    def test_nothing_pending_is_an_error_that_says_how_to_start(self, env):
        with pytest.raises(ConsentRequired, match="yb auth"):
            _finish(env, "4/ABC")

    def test_google_refusing_the_code_keeps_the_pending_for_a_retry(
        self, env, exchange
    ):
        exchange.side_effect = InvalidGrantError()
        _start(env)
        with pytest.raises(ConsentRequired, match="single-use") as excinfo:
            _finish(env, "4/stale")
        assert isinstance(excinfo.value.__cause__, InvalidGrantError)
        assert env["pending"].exists()


def test_consent_pending_survives_pickling():
    error = ConsentPending("https://x/auth", redirect_uri=REDIRECT)
    clone = pickle.loads(pickle.dumps(error))
    assert (clone.url, clone.redirect_uri, str(clone)) == (
        error.url,
        error.redirect_uri,
        str(error),
    )


class TestGetCredentialsPasteMode:
    @staticmethod
    def _kw(env):
        return dict(
            client_secrets_file=env["secrets"],
            token_file=env["token"],
            consent="paste",
        )

    @pytest.fixture(autouse=True)
    def _pending_in_tmp(self, env, monkeypatch):
        monkeypatch.setattr(
            paste_consent, "pending_consent_file", lambda: env["pending"]
        )

    def test_first_call_raises_pending_with_the_url_and_waits_for_nothing(
        self, env
    ):
        with mock.patch.object(InstalledAppFlow, "run_local_server") as local:
            with pytest.raises(ConsentPending) as excinfo:
                get_credentials(**self._kw(env))
        local.assert_not_called()
        assert excinfo.value.url == json.loads(env["pending"].read_text())["url"]
        assert excinfo.value.url in str(excinfo.value)
        assert "yb auth --paste" in str(excinfo.value)
        assert not env["token"].exists()
        assert isinstance(excinfo.value, ConsentRequired)

    def test_second_call_finishes_and_caches_the_token(self, env, exchange):
        with pytest.raises(ConsentPending):
            get_credentials(**self._kw(env))
        creds = get_credentials(**self._kw(env), authorization_response="4/ABC")
        assert creds is exchange.creds
        assert env["token"].read_text() == '{"fake": "token"}'

    def test_non_interactive_never_starts_consent_even_in_paste_mode(self, env):
        with pytest.raises(ConsentRequired) as excinfo:
            get_credentials(**self._kw(env), interactive=False)
        assert not isinstance(excinfo.value, ConsentPending)
        assert not env["pending"].exists()
        assert "yb auth" in str(excinfo.value)  # the headless remedy is named

    def test_unknown_consent_mode_fails_before_touching_anything(self, env):
        with pytest.raises(ValueError, match="consent"):
            get_credentials(**{**self._kw(env), "consent": "telepathy"})
        assert not env["pending"].exists()


class TestCli:
    @staticmethod
    def _argv(env, *extra):
        return [
            "auth",
            "--client-secrets", str(env["secrets"]),
            "--token-file", str(env["token"]),
            *extra,
        ]  # fmt: skip

    @pytest.fixture(autouse=True)
    def _pending_in_tmp(self, env, monkeypatch):
        monkeypatch.setattr(
            paste_consent, "pending_consent_file", lambda: env["pending"]
        )

    def test_auth_prints_the_url_and_succeeds(self, env, capsys):
        assert main(self._argv(env)) == 0
        out = capsys.readouterr().out
        assert json.loads(env["pending"].read_text())["url"] in out

    @pytest.mark.parametrize("how", ["argument", "stdin", "file"])
    def test_paste_finishes_from_any_source(
        self, env, exchange, capsys, monkeypatch, tmp_path, how
    ):
        main(self._argv(env))
        pasted = f"{REDIRECT}?code=4%2FABC&state=" + (
            json.loads(env["pending"].read_text())["state"]
        )
        if how == "stdin":
            monkeypatch.setattr(sys, "stdin", mock.Mock(read=lambda: pasted))
            value = "-"
        elif how == "file":
            value = "@" + str(tmp_path / "pasted.txt")
            (tmp_path / "pasted.txt").write_text(pasted)
        else:
            value = pasted
        assert main(self._argv(env, "--paste", value)) == 0
        assert env["token"].exists()
        assert "valid and cached" in capsys.readouterr().out

    def test_paste_without_a_pending_consent_exits_nonzero(self, env, capsys):
        assert main(self._argv(env, "--paste", "4/ABC")) == 1
        assert "No consent is pending" in capsys.readouterr().err

    def test_a_path_is_not_read_unless_asked_with_at(self, env, exchange, tmp_path):
        """Pasted text must never make the command open a file (a token, say)."""
        main(self._argv(env))
        secret = tmp_path / "secret.txt"
        secret.write_text("TOP-SECRET")
        main(self._argv(env, "--paste", str(secret)))
        (_, kwargs) = exchange.call_args
        assert "TOP-SECRET" not in kwargs["authorization_response"]

    def test_paste_and_check_are_mutually_exclusive(self, env):
        with pytest.raises(SystemExit):
            main(self._argv(env, "--check", "--paste", "x"))

    def test_check_fails_cleanly_without_a_token(self, env, capsys):
        assert main(self._argv(env, "--check")) == 1
        assert "consent is required" in capsys.readouterr().err
        assert not env["pending"].exists()
