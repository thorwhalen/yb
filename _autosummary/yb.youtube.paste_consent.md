# yb.youtube.paste_consent

Paste-back OAuth consent: consent from a machine nobody is sitting at.

The normal flow (`InstalledAppFlow.run_local_server`) keeps a web server up on
`localhost` and waits for Google to redirect the browser to it. That needs the
browser and the process to share a `localhost` — which a session driven from a
phone does not have: the consent page opens on the phone, the redirect goes to
the *phone’s* `localhost`, and the process (no terminal, nothing to wait on)
gives up with [`ConsentRequired`](yb.youtube.auth.md#yb.youtube.auth.ConsentRequired).

Paste-back splits consent into two steps that need no shared network and no
live process in between, so they can happen in different turns, even in
different Python processes:

1. [`start_paste_consent()`](#yb.youtube.paste_consent.start_paste_consent) builds the authorization URL and saves the one
   thing the second step needs (the PKCE verifier and `state`) to a short-lived
   file next to the token. The user opens the URL anywhere and consents.
2. Google redirects to `http://localhost:<port>/?state=…&code=…`. That page
   will not load — expected. The user copies the address-bar URL (or just the
   `code`) back, and [`finish_paste_consent()`](#yb.youtube.paste_consent.finish_paste_consent) completes the exchange.

Most callers never import this module: `get_credentials(consent="paste")` and
the `yb auth` command drive it. Nothing here writes the token — the caller
(`get_credentials`) does, so there is one place that does.

### Module Attributes

| [`DEFAULT_PASTE_PORT`](#yb.youtube.paste_consent.DEFAULT_PASTE_PORT)   | The redirect target.                                                                                                    |
|-----------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [`PENDING_TTL_S`](#yb.youtube.paste_consent.PENDING_TTL_S)        | How long a printed consent URL stays usable by [`finish_paste_consent()`](#yb.youtube.paste_consent.finish_paste_consent). |

### Functions

| [`finish_paste_consent`](#yb.youtube.paste_consent.finish_paste_consent)(authorization_response, \*)   | Complete a consent begun by [`start_paste_consent()`](#yb.youtube.paste_consent.start_paste_consent); return credentials.   |
|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [`pending_consent_file`](#yb.youtube.paste_consent.pending_consent_file)()                             | Where the in-progress consent is kept (next to the token, mode 0600).                                                     |
| [`start_paste_consent`](#yb.youtube.paste_consent.start_paste_consent)(\*[, ...])                     | Begin paste-back consent and return the URL to open.                                                                      |

### Exceptions

| [`ConsentPending`](#yb.youtube.paste_consent.ConsentPending)(url, \*, redirect_uri)   | Consent was started, and now waits for the user to paste the redirect back.   |
|------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|

### *exception* yb.youtube.paste_consent.ConsentPending(url, , redirect_uri)

Bases: [`ConsentRequired`](yb.youtube.auth.md#yb.youtube.auth.ConsentRequired)

Consent was started, and now waits for the user to paste the redirect back.

Not a failure: it is the *normal* result of the first call in paste mode.
`url` is the address to open; the message says what to do with the result.
Subclasses [`ConsentRequired`](yb.youtube.auth.md#yb.youtube.auth.ConsentRequired) so a caller that only
handles “no credentials” still stops, while one that knows about paste mode
can catch this and relay `url`.

### yb.youtube.paste_consent.DEFAULT_PASTE_PORT *= 8080*

The redirect target. Nothing listens there in paste mode — the page failing to
load is the expected outcome; only its address-bar URL matters.

### yb.youtube.paste_consent.PENDING_TTL_S *= 86400.0*

How long a printed consent URL stays usable by [`finish_paste_consent()`](#yb.youtube.paste_consent.finish_paste_consent).
Generous, because the gap is a human’s: a phone-driven session may take hours
to come back with the redirect. Google’s own limit is on the one-time *code*
it issues after consent, not on the URL, so this only bounds our bookkeeping.

### yb.youtube.paste_consent.finish_paste_consent(authorization_response, , client_secrets_file=None, pending_file=None)

Complete a consent begun by [`start_paste_consent()`](#yb.youtube.paste_consent.start_paste_consent); return credentials.

`authorization_response` is the redirected URL, its query string, or the
bare `code`. The pending file is removed on success and left in place on
failure, so a mistyped paste can simply be retried.

### yb.youtube.paste_consent.pending_consent_file()

Where the in-progress consent is kept (next to the token, mode 0600).

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

### yb.youtube.paste_consent.start_paste_consent(, client_secrets_file=None, scopes=['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.force-ssl'], port=8080, pending_file=None, reuse_pending=True)

Begin paste-back consent and return the URL to open.

A consent already pending for the same client, `scopes` and `port` is reused
(`reuse_pending=True`): re-printing the URL must not invalidate the one the
user already has open on their phone.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
