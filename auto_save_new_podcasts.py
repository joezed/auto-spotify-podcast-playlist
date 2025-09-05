#!/usr/bin/env python3
"""
Spotify Podcast Auto-Save + WhatsApp (Meta Cloud API)
-----------------------------------------------------
- Scans followed/saved shows
- Saves new episodes into 'Your Episodes'
- Logs to autosave.log (UTF-8 with BOM)
- Skips already-saved episodes (prevents re-adding deletions)
- Sends a WhatsApp template summary via Meta WhatsApp Cloud API

Requires:
  pip install spotipy python-dateutil requests

Environment variables required (Spotify):
  SPOTIPY_CLIENT_ID
  SPOTIPY_CLIENT_SECRET
  SPOTIPY_REDIRECT_URI     (e.g. http://127.0.0.1:8888/callback)

Environment variables required (WhatsApp Cloud API):
  WA_ACCESS_TOKEN          (Permanent access token)
  WA_PHONE_NUMBER_ID       (e.g. 123456789012345)
  WA_TO                    (recipient, e.g. +1234567890)

Optional (WhatsApp):
  WA_LANG                  (default: en)
  WA_TPL_ADDED             (default: autosave_added)
  WA_TPL_NONE              (default: autosave_none)

Optional (Script behavior):
  LOOKBACK_DAYS            (default: 7)
  EPISODES_PER_SHOW        (default: 20)
  SPOTIFY_MARKET           (default: from_token)
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser

# ----- PATHS / CONFIG ---------------------------------------------------------
BASE_DIR   = os.path.join(os.getcwd(), "spotify_autosave")
LOG_PATH   = os.path.join(BASE_DIR, "autosave.log")
CACHE_PATH = os.path.join(BASE_DIR, "spotify_cache.json")
STATE_FILE = os.path.join(BASE_DIR, "podcast_state.json")

LOOKBACK_DAYS     = int(os.environ.get("LOOKBACK_DAYS", "7"))
EPISODES_PER_SHOW = int(os.environ.get("EPISODES_PER_SHOW", "20"))
MARKET            = os.environ.get("SPOTIFY_MARKET", "from_token")

SCOPES = ["user-library-read", "user-library-modify"]

# WhatsApp Cloud API config
WA_ACCESS_TOKEN    = os.environ.get("WA_ACCESS_TOKEN", "").strip()
WA_PHONE_NUMBER_ID = os.environ.get("WA_PHONE_NUMBER_ID", "").strip()
WA_TO              = os.environ.get("WA_TO", "").strip()
WA_LANG            = os.environ.get("WA_LANG", "en").strip()
WA_TPL_ADDED       = os.environ.get("WA_TPL_ADDED", "autosave_added").strip()
WA_TPL_NONE        = os.environ.get("WA_TPL_NONE",  "autosave_none").strip()

# Ensure base dir exists
os.makedirs(BASE_DIR, exist_ok=True)

# ----- SIMPLE LOGGER ---------------------------------------------------------
def log(message: str) -> None:
    """Append a line to autosave.log and print to console."""
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {message}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8-sig") as f:
        f.write(line + "\n")

log("=" * 70)
log("Run started")

# ----- SPOTIFY ---------------------------------------------------------------
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def get_spotify_client():
    required = ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI")
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        raise RuntimeError("Missing Spotify env vars: " + ", ".join(missing))
    auth = SpotifyOAuth(scope=" ".join(SCOPES), cache_path=CACHE_PATH)
    return spotipy.Spotify(auth_manager=auth)

def parse_release_date(s):
    if not s:
        return None
    try:
        return dateparser.parse(s).date()
    except Exception:
        return None

def get_all_saved_shows(sp):
    shows, offset, limit = [], 0, 50
    while True:
        page = sp.current_user_saved_shows(limit=limit, offset=offset, market=MARKET)
        items = page.get("items", [])
        shows.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return shows

def get_recent_episodes_for_show(sp, show_id, max_items=20):
    episodes, offset, limit, fetched = [], 0, min(50, max_items), 0
    while fetched < max_items:
        page = sp.show_episodes(show_id, market=MARKET, limit=limit, offset=offset)
        items = page.get("items", [])
        if not items:
            break
        episodes.extend(items)
        fetched += len(items)
        if len(items) < limit:
            break
        offset += limit
    return episodes

def get_saved_episode_ids(sp):
    """Return a set of episode IDs already in 'Your Episodes'."""
    saved_ids, offset, limit = set(), 0, 50
    while True:
        page = sp.current_user_saved_episodes(limit=limit, offset=offset)
        items = page.get("items", [])
        if not items:
            break
        saved_ids.update(ep["episode"]["id"] for ep in items)
        if len(items) < limit:
            break
        offset += limit
    return saved_ids

def iso_date(d):
    return d.strftime("%Y-%m-%d")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Could not read state file: {e}")
    return {"last_run": None, "show_latest_release": {}}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
    except Exception as e:
        log(f"Failed to write state file: {e}")

# ----- WHATSAPP (Meta Cloud API) ---------------------------------------------
from typing import Optional, List

def send_whatsapp_template(template_name: str, body_params: Optional[List[dict]] = None):
    """Send a WhatsApp template message via Meta Cloud API."""
    if not (WA_ACCESS_TOKEN and WA_PHONE_NUMBER_ID and WA_TO):
        log("WhatsApp config missing; skipping WhatsApp send.")
        return

    url = f"https://graph.facebook.com/v20.0/{WA_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WA_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": WA_TO,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": WA_LANG}
        }
    }
    if body_params:
        payload["template"]["components"] = [{
            "type": "body",
            "parameters": body_params
        }]

    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        if r.ok:
            log(f"WhatsApp template '{template_name}' sent. Response: {r.text}")
        else:
            log(f"WhatsApp send error ({r.status_code}): {r.text}")
    except Exception as e:
        log(f"WhatsApp request failed: {e}")

def format_show_list(names, max_names=3):
    names = [n for n in names if n]
    if not names:
        return "your podcasts"
    if len(names) > max_names:
        return ", ".join(names[:max_names]) + ", and more"
    return ", ".join(names)

# ----- MAIN ------------------------------------------------------------------
def main():
    sp = get_spotify_client()
    state = load_state()

    now_utc = datetime.now(timezone.utc)
    last_run_str = state.get("last_run")
    if last_run_str:
        baseline_date = dateparser.parse(last_run_str).date() - timedelta(days=1)
        log(f"Incremental run: baseline={baseline_date}")
    else:
        baseline_date = (now_utc - timedelta(days=LOOKBACK_DAYS)).date()
        log(f"First run: baseline={baseline_date} (lookback {LOOKBACK_DAYS}d)")

    saved_shows = get_all_saved_shows(sp)
    log(f"Found {len(saved_shows)} followed shows.")

    already_saved = get_saved_episode_ids(sp)
    episodes_to_save = []
    new_shows = []

    for show_item in saved_shows:
        show = show_item["show"]
        show_id = show["id"]
        show_name = show.get("name", show_id)

        per_show_str = state["show_latest_release"].get(show_id)
        per_show_baseline = parse_release_date(per_show_str) if per_show_str else baseline_date

        eps = get_recent_episodes_for_show(sp, show_id, max_items=EPISODES_PER_SHOW)
        new_count = 0
        newest_seen_for_show = per_show_baseline

        for ep in eps:
            rel_date = parse_release_date(ep.get("release_date", ""))
            if not rel_date:
                continue
            if rel_date > per_show_baseline and ep["id"] not in already_saved:
                episodes_to_save.append(ep["id"])
                new_count += 1
                if not newest_seen_for_show or rel_date > newest_seen_for_show:
                    newest_seen_for_show = rel_date

        if new_count > 0:
            new_shows.append(show_name)

        log(f"- {show_name}: +{new_count} new since {per_show_baseline}")

        if newest_seen_for_show and (not per_show_str or newest_seen_for_show > per_show_baseline):
            state["show_latest_release"][show_id] = iso_date(newest_seen_for_show)

    episodes_to_save = list(dict.fromkeys(episodes_to_save))

    added = 0
    if episodes_to_save:
        CHUNK = 50
        for i in range(0, len(episodes_to_save), CHUNK):
            chunk = episodes_to_save[i:i+CHUNK]
            sp.current_user_saved_episodes_add(chunk)
            added += len(chunk)
        log(f"Saved {added} new episode(s) to 'Your Episodes'.")
    else:
        log("No new episodes to save.")

    state["last_run"] = now_utc.isoformat()
    save_state(state)
    log("Run finished")

    try:
        if added > 0:
            show_list = format_show_list(new_shows)
            send_whatsapp_template(
                WA_TPL_ADDED,
                body_params=[
                    {"type": "text", "text": str(added)},
                    {"type": "text", "text": show_list}
                ]
            )
        else:
            send_whatsapp_template(WA_TPL_NONE)
    except Exception as e:
        log(f"WhatsApp send failed: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Fatal error: {e}")
        sys.exit(1)
