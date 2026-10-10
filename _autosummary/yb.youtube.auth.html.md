# yb.youtube.auth

OAuth 2.0 plumbing for the YouTube Data API v3.

Runs the installed-app consent flow once (browser), caches the token, and
refreshes it silently thereafter. Needs only `google-api-python-client` +
`google-auth-oauthlib` (`pip install 'yb[youtube]'`) and an OAuth client of
type *Desktop app* — point `client_secrets_file` at its JSON or set
`$YOUTUBE_CLIENT_SECRETS_FILE` / `$GOOGLE_CLIENT_SECRETS_FILE`.

No `gcloud` required: creating the project / enabling the API / making the
OAuth client is all doable in the Google Cloud console (the `yb-setup` skill
walks through it).

### Module Attributes

| [`DEFAULT_SCOPES`](#yb.youtube.auth.DEFAULT_SCOPES)            | Upload + force-ssl (the latter is needed for captions.insert and thumbnails.set).                                                                                                                                                |
|----------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`CONSENT_MODES`](#yb.youtube.auth.CONSENT_MODES)             | `"local"` waits for a redirect on this machine's `localhost`; `"paste"` is two-step and needs no shared network (see [`yb.youtube.paste_consent`](yb.youtube.paste_consent.html.md#module-yb.youtube.paste_consent)). |
| [`DEFAULT_CONSENT_TIMEOUT_S`](#yb.youtube.auth.DEFAULT_CONSENT_TIMEOUT_S) | How long consent may wait for its redirect before giving up.                                                                                                                                                                     |

### Functions

| [`default_client_secrets_file`](#yb.youtube.auth.default_client_secrets_file)()                   | Default OAuth client-secrets location: `<config dir>/client_secret.json`.   |
|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| [`default_token_file`](#yb.youtube.auth.default_token_file)()                            | Cached OAuth token location (`$XDG_CONFIG_HOME` or `~/.config`).            |
| [`get_credentials`](#yb.youtube.auth.get_credentials)(\*[, client_secrets_file, ...]) | Return OAuth user credentials, running the consent flow if needed.          |
| [`get_service`](#yb.youtube.auth.get_service)(\*[, credentials])                  | Build a YouTube Data API v3 service object.                                 |

### Exceptions

| [`ConsentRequired`](#yb.youtube.auth.ConsentRequired)   | Consent is needed and this process cannot obtain it.   |
|--------------------------------------------------------------------|--------------------------------------------------------|

### yb.youtube.auth.CONSENT_MODES *= ('local', 'paste')*

`"local"` waits for a redirect on this machine’s
`localhost`; `"paste"` is two-step and needs no shared network (see
[`yb.youtube.paste_consent`](yb.youtube.paste_consent.html.md#module-yb.youtube.paste_consent)).

* **Type:**
  Ways to obtain consent

### *exception* yb.youtube.auth.ConsentRequired

Bases: [`RuntimeError`](https://docs.python.org/3/builtins/exceptions.html#RuntimeError)

Consent is needed and this process cannot obtain it.

Raised instead of starting a consent flow that nobody can complete. The
alternative is worse than an error: `run_local_server` prints a URL to a
stdout nobody is reading and waits on `localhost` for a redirect that will
never arrive, so an automated caller *blocks* rather than failing. That has
happened — an upload stopped dead mid-script and read as a slow network for
hours, when the underlying cause was one line of `invalid_grant`.

### yb.youtube.auth.DEFAULT_CONSENT_TIMEOUT_S *= 300.0*

How long consent may wait for its redirect before giving up.

The library’s own default is “wait indefinitely”, which is not a good default
for anything: a caller that cannot complete consent then *blocks* rather than
failing, and an automated upload reads as a slow network until someone thinks
to run `ps`. Five minutes is long enough for a human to find the tab and
click through an unverified-app warning, and short enough that a machine
finds out today. Pass `timeout_seconds=None` for the old behaviour.

### yb.youtube.auth.DEFAULT_SCOPES *= ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl']*

Upload + force-ssl (the latter is needed for captions.insert and thumbnails.set).

### yb.youtube.auth.default_client_secrets_file()

Default OAuth client-secrets location: `<config dir>/client_secret.json`.

Used when neither `client_secrets_file=` nor the env vars are set, so all
of `yb`’s state can live in one directory next to the token.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### yb.youtube.auth.default_token_file()

Cached OAuth token location (`$XDG_CONFIG_HOME` or `~/.config`).

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### yb.youtube.auth.get_credentials(, client_secrets_file=None, token_file=None, scopes=['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl'], open_browser=True, port=0, timeout_seconds=300.0, interactive=True, consent='local', authorization_response=None)

Return OAuth user credentials, running the consent flow if needed.

First use runs the installed-app consent flow and caches the token to
`token_file` so later calls are non-interactive. Expired tokens are
refreshed automatically.

Pass `interactive=False` when nobody can answer a consent prompt — a cron
job, a queue worker, an agent. Consent is then never started; a token that
cannot be refreshed raises [`ConsentRequired`](#yb.youtube.auth.ConsentRequired) naming the cause and the
fix. This is not an edge case: an OAuth client left in “Testing” rotates
refresh tokens out after about seven days, so anything scheduled hits it
weekly.

Even with the default `interactive=True` the call can no longer hang:
consent is bounded by `timeout_seconds`
([`DEFAULT_CONSENT_TIMEOUT_S`](#yb.youtube.auth.DEFAULT_CONSENT_TIMEOUT_S)), and a timeout is reported as the same
[`ConsentRequired`](#yb.youtube.auth.ConsentRequired), because “nobody answered” and “nobody could
answer” want the same thing done about them.

Consent always goes through a temporary local web server on `port` (`0`
picks a free one), because Google retired the copy-paste “out-of-band” flow
in 2022. `open_browser=False` only stops the browser from being launched:
the authorization URL is printed instead, and the redirect must still reach
that local server.

Headless recipe: pass `interactive=True` (there is no terminal, so the
default would refuse), `open_browser=False` and a fixed `port=`, then
forward that port from the machine holding the browser
(`ssh -L <port>:localhost:<port> <host>`). Nothing needs registering in
the Cloud console — the *Desktop app* client this module requires accepts
any `localhost` port, which is also why the `port=0` default works.

The call blocks until the redirect arrives, bounded by `timeout_seconds`
(default [`DEFAULT_CONSENT_TIMEOUT_S`](#yb.youtube.auth.DEFAULT_CONSENT_TIMEOUT_S); pass `None` for the library’s
“wait indefinitely”, which is what this used to do).

\*\*No shared `localhost`? Use\*\* `consent="paste"`. Consent then needs no
running server and no waiting: the first call returns by raising
[`ConsentPending`](yb.youtube.paste_consent.html.md#yb.youtube.paste_consent.ConsentPending) carrying the URL to open
(anywhere — a phone will do); the browser’s redirect to `localhost` fails
to load, and the second call passes that address-bar URL (or just its
`code`) as `authorization_response=` to finish and cache the token. The
two calls may be separate turns or separate processes; `yb auth` is the
command-line form. `port` only names the (unreachable) redirect.

These keywords ride `**cred_kwargs` through [`get_service()`](#yb.youtube.auth.get_service) and the
publishing helpers. The few entry points that take none (notably
`yb.music.publish.publish_folder()`) still work headlessly: call this
once to mint the token, after which nothing prompts again.

### yb.youtube.auth.get_service(, credentials=None, \*\*cred_kwargs)

Build a YouTube Data API v3 service object.

`cred_kwargs` are forwarded to [`get_credentials()`](#yb.youtube.auth.get_credentials) (`token_file=`,
`open_browser=`, `port=`, …) unless `credentials` is given.
