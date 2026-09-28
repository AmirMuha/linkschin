# Quickstart & End-to-End Validation Guide: Iranian Media Fetcher

- **Feature**: `001-mvp`
- **Date**: 2026-09-27
- **Status**: Complete

This guide details how to set up the environment, run the application, execute automated tests, and validate the media categories end-to-end.

---

## 1. Prerequisites & Environment Setup

### System Requirements
- Node.js 18+ and `pnpm` (for Turborepo orchestration).
- Python 3.11 or newer (standard `venv` module) and `poethepoet` for `poe` tasks.
- Modern web browser (Chrome, Firefox, Safari, Edge).

### Setup Commands (Monorepo)
```bash
# 1. Clone/navigate to project root
cd /run/media/amirmuha/0C944DAF23695833/projects/movie-fetcher

# 2. Install monorepo tools (Turborepo)
pnpm install

# 3. Create the API virtualenv and install dependencies
cd apps/api
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"

# 4. Activate it for the remaining commands
source .venv/bin/activate
```

---

## 2. Running Automated Tests

Run the offline unit and fixture test suite (29 test cases verifying data models, Persian normalization, TTLCache, Downloadha split-archive extraction, Pop-Music audio stream extraction, stream URL validation, and environment variable overrides):

```bash
# From root via Turborepo
pnpm test

# Or from apps/api with the virtualenv active
cd apps/api
poe test-offline
```

---

## 3. Running Scraper CLI Smoke Checks

Verify individual source connectivity and link extraction directly against live internet sources:

```bash
# From apps/api with the virtualenv active

# Smoke test live game scraper (verifies multi-part links and password)
.venv/bin/python cli_check.py --category games --source downloadha --query "noire"

# Smoke test live music scraper (verifies direct MP3 stream URL and 128k/320k links)
.venv/bin/python cli_check.py --category music --source popmusic --query "محسن"
```

Expected output:
- Number of items discovered.
- Extracted direct download URLs.
- Archive password (`www.downloadha.com`) and sequential part counts for games.
- Direct streaming URL for music preview.

---

## 4. Running the Web Application

Launch the local web server:

```bash
# From root via Turborepo
pnpm dev

# Or directly inside apps/api
cd apps/api && .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser to: `http://127.0.0.1:8000`

---

## 5. End-to-End Validation Scenarios

### Scenario 1: Game Multi-Part Extraction & Password Copy (Live)
1. On `http://127.0.0.1:8000`, switch to the **Games** tab.
2. Search for `"noire"` or `"ragtag"`.
3. Locate a repack result and inspect the download links.
4. **Verify**:
   - The archive extraction password (`www.downloadha.com`) is displayed with a "Copy Password" button.
   - Parts are strictly numbered in sequential order: `Part 1`, `Part 2`, ... `Part N`.
   - Clicking "Copy all links" copies every part URL to the clipboard.

### Scenario 2: Music Discovery & Inline Playback (Live)
1. Switch to the **Music** tab.
2. Search for an artist or song name (e.g. `"محسن"` or `"شادمهر"`).
3. **Verify**:
   - Track cards display artist name, track title, and cover art.
   - An inline HTML5 `<audio>` player is rendered on each card.
   - Dedicated `320 kbps` and `128 kbps` buttons initiate direct MP3 downloads.

### Scenario 3: Fast Cache Verification
1. Repeat any of the searches above with the exact same query text.
2. **Verify**:
   - Results load instantly with the "⚡ خوانده شده از کش" badge displayed.
