# Syncing output/ to Google Drive — Options Breakdown

**Problem:** `output/` is gitignored (personal data, API artifacts, ChromaDB binaries). Need access from anywhere.

---

## Option 1: `rclone` — Purpose-Built Cloud Sync

```bash
# Install
curl https://rclone.org/install.sh | bash

# One-time setup
rclone config          # interactive: name=gdrive, type=drive, OAuth flow

# Sync (excludes ChromaDB binaries)
rclone sync /root/search/job-search/output/ gdrive:job-search/output/ \
  --exclude ".chromadb/**"
```

| Aspect | Detail |
|--------|--------|
| **What it does** | One-way or bidirectional folder mirror to Google Drive |
| **Auth** | One-time `rclone config` — browser OAuth flow, stores token locally |
| **Sync mode** | Full folder mirror: adds new, updates changed, optionally deletes removed |
| **Automation** | Cron-friendly: single command, `--exclude` patterns, bandwidth limits |
| **Handles** | Nested dirs, large files, incremental updates, resume on failure |
| **Trade-off** | Extra tool to install, but gold standard for cloud sync |
| **Best for** | "I want the whole output/ folder mirrored automatically" |

### Automation example (cron)

```bash
# Every hour, sync output/ to Drive (skip ChromaDB)
0 * * * * rclone sync /root/search/job-search/output/ gdrive:job-search/output/ --exclude ".chromadb/**" --log-file /tmp/rclone.log
```

---

## Option 2: `gws` (Google Workspace CLI) — API-Level Control

```bash
# Install
npm install -g @googleworkspace/cli

# Auth
gws auth setup    # creates GCP project + enables APIs
gws auth login    # OAuth flow

# Create Drive folder
gws drive files create --json '{"name": "job-search-output", "mimeType": "application/vnd.google-apps.folder"}'

# Upload a file
gws drive files create --json '{"name": "scraped.json", "parents": ["<folder_id>"]}' --upload ./output/latest/scraped.json
```

| Aspect | Detail |
|--------|--------|
| **What it does** | Direct Google Drive API calls — upload, list, create, delete |
| **Auth** | `gws auth setup` + `gws auth login` — GCP project + OAuth |
| **Sync mode** | No built-in sync. File-by-file upload. Needs wrapper script for folder sync |
| **Automation** | Would need a custom `sync_drive.py` tracking upload state in `.sync_state.json` |
| **Handles** | Any Google Workspace API (Drive, Sheets, Gmail, Calendar) |
| **Trade-off** | Overkill for pure sync, but opens doors for smart integrations |
| **Best for** | "I want Google Workspace integration beyond file sync" |

### Smart integration ideas (beyond sync)

- Push `ranked.json` -> Google Sheet for mobile-friendly viewing
- Email summary of APPLY NOW jobs after each pipeline run
- Calendar events for follow-up reminders from opportunity tracker

---

## Option 3: Google Drive Python API — Pipeline Integration

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

creds = Credentials.from_authorized_user_file('token.json')
service = build('drive', 'v3', credentials=creds)

media = MediaFileUpload('output/latest/ranked.json', mimetype='application/json')
service.files().create(body={'name': 'ranked.json', 'parents': [FOLDER_ID]}, media_body=media).execute()
```

| Aspect | Detail |
|--------|--------|
| **What it does** | Programmatic Drive access from within the Python pipeline |
| **Auth** | OAuth2 credentials file + token refresh |
| **Sync mode** | Custom — control exactly what gets uploaded and when |
| **Automation** | Hook into `pipeline.py` — auto-upload after each stage completes |
| **Handles** | Upload, folder creation, sharing, permissions |
| **Trade-off** | More code to maintain, but zero external CLI dependencies |
| **Best for** | "I want the pipeline itself to push results to Drive after each run" |

---

## Option 4: Git Separate Private Repo

```bash
cd /root/search/job-search/output
git init
git remote add origin git@github.com:you/job-data-private.git
git add -A -- ':!.chromadb'
git commit -m "run 2026-03-09"
git push
```

| Aspect | Detail |
|--------|--------|
| **What it does** | Treats output/ as its own git repo, pushed to a private remote |
| **Auth** | Existing GitHub SSH keys |
| **Sync mode** | Manual commit + push, or hook after pipeline runs |
| **Handles** | JSON files well. NOT good for .chromadb/ (binary blobs) |
| **Trade-off** | Version history for free (diff between runs), but git isn't for large binaries |
| **Best for** | "I want version history of my job data + access from any machine with git" |

---

## Option 5: Hybrid — rclone for bulk + `gws` for smart features

| Layer | Tool | What it handles |
|-------|------|----------------|
| **Sync** | rclone | Mirror output/ -> Drive folder (cron, one command) |
| **Smart** | gws | Push ranked.json -> Google Sheet, send email summary, calendar reminders |
| **Best for** | "I want reliable sync AND Google Workspace integration" |

This is the natural evolution: start with rclone, add `gws` when you want smart features.

---

## Recommendation

| Goal | Pick |
|------|------|
| Just get files on Drive, fast | **rclone** (Option 1) |
| Integrate with Google Workspace (Sheets, email) | **gws** (Option 2) |
| Auto-upload from pipeline code | **Python API** (Option 3) |
| Version history + access | **Git private repo** (Option 4) |
| All of the above, over time | **Hybrid** (Option 5) |

**Start with rclone** — 5 min setup, one command, excludes .chromadb/. Add `gws` later when you want ranked jobs in a Google Sheet on your phone.

---

## What to sync vs skip

| Path | Sync? | Why |
|------|-------|-----|
| `output/runs/*/` | Yes | Per-run JSON files, small, valuable |
| `output/opportunities.json` | Yes | Persistent tracker state |
| `output/contacts.json` | Yes | Persistent contact state |
| `output/latest` | Skip | Symlink, recreated locally |
| `output/.chromadb/` | Skip | Large binary, machine-specific, rebuilt from resumes |
| `output/intelligence.db` | Yes (when built) | SQLite, small, cross-run knowledge |
