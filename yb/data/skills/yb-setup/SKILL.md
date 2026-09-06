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
3. **Audience** — add the channel-owner Google account as a **Test user**;
   keep publishing status **Testing**.
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

### Headless (no browser on the machine running `yb`)

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
- **Testing-mode tokens expire in ~7 days.** For uninterrupted use, set the
  consent screen's publishing status to **In production** (still usable by you
  with the unverified warning; tokens then don't expire).
- **`youtube-upload` (PyPI) is not a shortcut** — it's abandoned, uses
  deprecated auth, and needs the same OAuth client. Use `yb.youtube`.

## Troubleshooting

- `accessNotConfigured` / API disabled → finish step 2 (enable the API).
- `No OAuth client secrets` → set `$YOUTUBE_CLIENT_SECRETS_FILE` (step 4).
- `invalid_grant` / token errors → delete `~/.config/yb/youtube_token.json` and
  re-run consent.
- Wrong channel authorized → delete the cached token and re-consent with the
  correct Google account.
