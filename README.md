# Spotify Podcast Auto-Save + WhatsApp Summary

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Spotify API](https://img.shields.io/badge/Spotify-API-brightgreen)](https://developer.spotify.com/)
[![WhatsApp Cloud API](https://img.shields.io/badge/Meta-WhatsApp%20Cloud%20API-lightgrey)](https://developers.facebook.com/docs/whatsapp/cloud-api)

Automatically:
- scans your **followed/saved shows** on Spotify  
- saves **new episodes** to *Your Episodes*  
- (optionally) sends a **WhatsApp** template message via Meta’s Cloud API summarizing what was added


This repo contains **no secrets** and includes sample environment variables for local setup.

## Features
- Incremental runs with a per-show release “watermark”
- Skips episodes already in *Your Episodes*
- UTF-8 (with BOM) log file for easy viewing on Windows Notepad
- Portable paths (defaults to a folder under your current working directory)

## Requirements
- Python 3.9+
- Spotify account
- (Optional) Meta WhatsApp Cloud API account & a pre-approved template

Set up your Spotify API access here: [Spotify Developer Platform](https://developer.spotify.com/documentation/web-api)

```bash
pip install spotipy python-dateutil requests
```

## Environment Variables

Create a `.env` (or export in your shell/CI) using the keys below. See `.env.example` in this repo.

**Spotify (required)**
- `SPOTIPY_CLIENT_ID`
- `SPOTIPY_CLIENT_SECRET`
- `SPOTIPY_REDIRECT_URI` (e.g. `http://127.0.0.1:8888/callback`)

**WhatsApp Cloud API (optional)**
- `WA_ACCESS_TOKEN` (permanent access token)
- `WA_PHONE_NUMBER_ID` (e.g. `123456789012345`)
- `WA_TO` (recipient, e.g. `+1234567890`)
- `WA_LANG` (default: `en`)
- `WA_TPL_ADDED` (default: `autosave_added`)
- `WA_TPL_NONE` (default: `autosave_none`)

**Behavior (optional)**
- `LOOKBACK_DAYS` (default: `7`)
- `EPISODES_PER_SHOW` (default: `20`)
- `SPOTIFY_MARKET` (default: `from_token`)

> Tip: If you don’t set WhatsApp variables, the script simply logs and **skips sending**.

## Running

```bash
# 1) (optional) load env vars```
### macOS/Linux
```export $(grep -v '^#' .env | xargs)```

# 2) run the script
python auto_save_new_podcasts.py
```

On first run you’ll complete Spotify OAuth in the browser. A cache file is written under `spotify_autosave/`.

### Automate (cron / Task Scheduler)

**cron (Linux/macOS)**
```
0 8 * * * /usr/bin/env bash -lc 'cd /path/to/repo && export $(grep -v "^#" .env | xargs) && /usr/bin/python3 auto_save_new_podcasts.py >> cron.log 2>&1'
```

**Windows Task Scheduler**
- Action: `python.exe`  
- Arguments: `auto_save_new_podcasts.py`  
- Start in: repo directory  
- Ensure your environment variables are available to the task (System/User env or a wrapper `.bat` that sets them before calling Python).

## WhatsApp Templates

You’ll need two **pre-approved** templates in Meta:
- `autosave_added` (language `en`) with at least **two body variables**:
  1. number of episodes added (e.g., `3`)
  2. short list of show names (e.g., `The Daily, Cortex, and more`)
- `autosave_none` (language `en`) with **no variables**

If you prefer different names, set `WA_TPL_ADDED` and `WA_TPL_NONE`.  

Set them up here: [Meta Developers Platform](https://developers.facebook.com/apps/)

## Logs & State

Created under `./spotify_autosave/`:
- `autosave.log` — human-readable log
- `spotify_cache.json` — Spotify OAuth cache
- `podcast_state.json` — last run and per-show watermark

Delete these if you want a clean slate (you’ll re-auth with Spotify).

## Security & PII

- **Never commit** your `.env` or any tokens.
- This code contains **no hard-coded keys or phone numbers**.
- Use GitHub secrets/CI variables for automated runs.

## Troubleshooting

- **Spotify auth loop**: delete `spotify_cache.json` and re-run.
- **No new episodes found**: increase `LOOKBACK_DAYS` or confirm you have followed shows with recent releases.
- **WhatsApp send skipped**: ensure `WA_ACCESS_TOKEN`, `WA_PHONE_NUMBER_ID`, `WA_TO` are set and templates are approved.

## License

MIT (or your preferred license).
