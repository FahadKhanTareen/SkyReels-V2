# TikTok automation

Makes one short motivational video a day and posts it to TikTok.

1. **Script** – Claude writes a hook, 3–5 lines, a caption and hashtags (falls back to bundled scripts if no API key).
2. **Voiceover** – free Microsoft Edge voices via `edge-tts`.
3. **Video** – 1080×1920 slides with a slow zoom, timed to the voice, assembled with ffmpeg.
4. **Upload** – official TikTok Content Posting API.
5. **Schedule** – GitHub Actions, daily at 15:17 UTC (edit the `cron` line in `.github/workflows/daily.yml`).

## Try it on your computer

Needs Python 3.10+ and ffmpeg.

```bash
pip install -r requirements.txt
python -m tiktok_bot            # builds out/<timestamp>/video.mp4, no upload
python -m tiktok_bot --upload   # builds and posts
```

## Setup

This folder is meant to be the root of its own repository: GitHub only runs workflows
from `.github/workflows` at the top level of a repo.

### 1. TikTok developer app

1. Register at <https://developers.tiktok.com> and create an app.
2. Add the **Login Kit** and **Content Posting API** products, enable **Direct Post**, and request the `video.publish` scope.
3. Register a redirect URI under Login Kit (any https page you control).
4. Copy the **Client key** and **Client secret**.

Until TikTok audits your app, every post is private (`SELF_ONLY`) — only you can see it.
After the audit passes, set the repository variable `TIKTOK_PRIVACY` to `PUBLIC_TO_EVERYONE`.

### 2. Get a refresh token (once)

```bash
TIKTOK_CLIENT_KEY=... TIKTOK_CLIENT_SECRET=... TIKTOK_REDIRECT_URI=... python get_token.py
```

### 3. Repository secrets

Settings → Secrets and variables → Actions:

| Secret | Purpose |
| --- | --- |
| `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` | from your TikTok app |
| `TIKTOK_REFRESH_TOKEN` | printed by `get_token.py` |
| `ANTHROPIC_API_KEY` | optional; fresh scripts every day instead of the 7 bundled ones |
| `GH_PAT` | optional; fine-grained token with *Secrets: read and write*, lets the workflow save a rotated TikTok refresh token |

Optional variables: `TIKTOK_PRIVACY` (default `SELF_ONLY`), `TTS_VOICE` (default `en-US-AndrewNeural`; list voices with `edge-tts --list-voices`).

### 4. Run it

Actions → **Daily TikTok video** → **Run workflow**. Untick *upload* to only build the video;
it is attached to the run as a download either way.

## Settings

| Env var | Default | |
| --- | --- | --- |
| `TTS_VOICE` / `TTS_RATE` | `en-US-AndrewNeural` / `-5%` | voice and speed |
| `MUSIC_FILE` | none | path to a background track you have the rights to; mixed in quietly |
| `ANTHROPIC_MODEL` | `claude-opus-5-5` | model that writes the scripts |
| `TIKTOK_PRIVACY` | `SELF_ONLY` | must be one your account/app allows |

Posts are flagged as AI-generated (`is_aigc`), which TikTok requires for this kind of content.
