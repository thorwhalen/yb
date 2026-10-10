---
name: yb-setup
description: >
  Set up YouTube publishing for the `yb` package: install the right extras,
  create a Google OAuth client (gcloud optional — the console path works),
  wire up the credentials, run the one-time consent, and test the connection.
  Use when the user wants to publish/upload to YouTube for the first time, hits
  an OAuth or "client secrets" error, sees "accessNotConfigured", needs to make
  or replace a YouTube OAuth client, or asks how to authenticate yb with YouTube.
---

# yb-setup

Get `yb` ready to upload/edit YouTube videos. One-time setup; afterwards the
token is cached and uploads are non-interactive.

## 0. Is gcloud necessary? No.

Runtime needs only Python libs + an OAuth client JSON. `gcloud` is *optional* —
it only convenience-automates creating the project and enabling the API, both
of which are doable in the web console. Don't install gcloud just for this.

## 1. Install the extras

```bash
pip install 'yb[youtube]'     # google-api-python-client + google-auth-oauthlib
pip install 'yb[download]'    # optional: yt-dlp, if also downloading
```

## 2. Create a Google Cloud project + enable the API

**Console:** create/select a project at console.cloud.google.com, then enable
**YouTube Data API v3** (APIs & Services → Library).

**Or gcloud** (only if already installed/authenticated):
```bash
gcloud projects create <unique-id> --name="YouTube Publishing"
gcloud config set project <unique-id>
gcloud services enable youtube.googleapis.com
```
(Project ids are globally unique; add a suffix if taken. YouTube Data API has a
free quota — no billing account required.)

## 3. Configure the OAuth client (console only — gcloud can't do this)

In **APIs & Services → "Google Auth Platform"** (formerly OAuth consent screen):
1. **Get started / Branding** — app name + your support email; Audience: **External**.
2. **Data Access** — add scopes:
   `https://www.googleapis.com/auth/youtube.upload` and
   `https://www.googleapis.com/auth/youtube.force-ssl` (force-ssl is needed for
   captions + thumbnails).
3. **Audience** — add the channel-owner Google account as a **Test user**
   (lets you consent while setting up), then **Publish app** so the status is
   **In production** — *before* the consent in step 5. Do **not** leave it in
   **Testing**: Google expires every refresh token minted in Testing after
   7 days, so uploads and edits break weekly (reeleehq/yb#16). If publishing
   asks for verification, remove the Branding logo and leave the domains blank;
   a personal-use app needs neither. Consenting still shows an "unverified app"
   warning — click through it (Advanced → continue); that is the only cost.
4. **Clients** — Create client → **Desktop app** → **Download JSON**.

## 4. Point yb at the client JSON

```bash
mkdir -p ~/.config/youtube
mv ~/Downloads/client_secret_*.json ~/.config/youtube/client_secret.json
export YOUTUBE_CLIENT_SECRETS_FILE="$HOME/.config/youtube/client_secret.json"   # add to ~/.zshrc
```

## 5. Run consent + test

```python
from yb.youtube import get_service

svc = get_service()  # first run opens a browser; click through the
# "unverified app" warning (your own project) and
# grant the YouTube permissions. Token is cached.
me = svc.channels().list(part="snippet", mine=True).execute()
print(me["items"][0]["snippet"]["title"])  # your channel name => success
```

### Headless, paste-back (no browser *and* no terminal — e.g. a session driven from a phone)

The tunnel recipe below needs a second machine with a shell. When there is none,
use paste-back consent: two steps that may be separate turns or processes, and
that need no shared network.

```bash
yb auth                  # prints a consent URL; open it on any device and approve
yb auth --paste '<URL>'  # the URL the browser lands on afterwards
yb auth --check          # verify the cached token (never prompts)
```

After approving, the browser tries to load `http://localhost:8080/?state=…&code=…`
and fails to connect — that is expected. Copy that full address-bar URL (the bare
`code=…` value also works) into `--paste` (a literal, `-` for stdin, or a file
path). In Python the same two steps are:

```python
from yb.youtube import ConsentPending, get_credentials

try:
    get_credentials(consent="paste")  # step 1: raises ConsentPending(url=...)
except ConsentPending as pending:
    print(pending.url)
get_credentials(consent="paste", authorization_response="<pasted URL>")  # step 2
```

The pending request (PKCE verifier + state) is kept for 24 h in
`~/.config/yb/youtube_consent_pending.json` (mode 0600) and deleted on success;
asking for the URL again returns the same one. `interactive=False` still never
starts consent. Never print or paste the token file.

### Headless with a browser elsewhere (SSH tunnel)

The default `get_service()` tries to *launch* a browser, so on a box without one
it raises `webbrowser.Error` before printing anything. Ask for the URL instead,
on a port you can forward:

```bash
ssh -L 8080:localhost:8080 <host>   # from the machine that has the browser
```

```python
# on <host>
from yb.youtube import get_credentials

get_credentials(open_browser=False, port=8080)  # prints the URL, then waits
```

Open the printed URL in your local browser; the redirect travels back down the
tunnel to the flow's server. Nothing to register in the Cloud console — a
*Desktop app* client accepts any `localhost` port. The token is then cached, so
every later call is non-interactive, including `get_service()` and the publish
helpers (which also forward `open_browser=` / `port=` themselves).

Pass `timeout_seconds=` if you want the wait bounded rather than indefinite.

## Caveats to surface to the user

- **Unaudited project → forced private.** Until the project passes YouTube's
  one-time API compliance audit, uploads may be locked to **private** even when
  `unlisted`/`public` is requested. The video still uploads; flip visibility in
  Studio, or complete the audit.
- **Testing-mode tokens expire in ~7 days — publish the app (step 3).** Order
  matters: a refresh token minted *while in Testing* keeps its 7-day limit even
  after you publish, so publish first, then (re-)consent once. If consent was
  already done in Testing, publish and then re-consent.
- **`youtube-upload` (PyPI) is not a shortcut** — it's abandoned, uses
  deprecated auth, and needs the same OAuth client. Use `yb.youtube`.

## Troubleshooting

- `accessNotConfigured` / API disabled → finish step 2 (enable the API).
- `No OAuth client secrets` → set `$YOUTUBE_CLIENT_SECRETS_FILE` (step 4).
- `invalid_grant` / token errors → the token expired (Testing mode: see the
  caveat above) or was revoked; delete `~/.config/yb/youtube_token.json` and
  re-run consent.
- `ConsentRequired` from a session with no terminal → use paste-back above.
- Wrong channel authorized → delete the cached token and re-consent with the
  correct Google account.
