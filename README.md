# Spotify Podcast Auto-Save + WhatsApp Summary
Automatically:
- scans your followed/saved shows on Spotify
- saves new episodes to Your Episodes
- (optionally) sends a WhatsApp template message via Meta’s Cloud API summarizing what was added  

This repo contains no secrets and includes sample environment variables for local setup.

## Features
- Incremental runs with a per-show release “watermark”
- Skips episodes already in Your Episodes
- UTF-8 (with BOM) log file for easy viewing on Windows Notepad
- Portable paths (defaults to a folder under your current working directory)

## Requirements 
- Python 3.9+
- Spotify account
- (Optional) Meta WhatsApp Cloud API account & a pre-approved template
```pip install spotipy python-dateutil requests```