# Quickstart & End-to-End Validation Guide: Iranian Media Fetcher

- **Feature**: `001-mvp`
- **Date**: 2026-09-27
- **Status**: Complete

This guide details how to set up the environment, run the application, execute automated tests, and validate the three media categories end-to-end.

---

## 1. Prerequisites & Environment Setup

### System Requirements
- Python 3.11 or newer installed on the host machine.
- Modern web browser (Chrome, Firefox, Safari, Edge).

### Setup Commands
```bash
# 1. Clone/navigate to project root
cd /run/media/amirmuha/0C944DAF23695833/projects/movie-fetcher

# 2. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies in editable mode
pip install -e ".[dev]"
```

---

## 2. Running Automated Tests

Run the test suite to verify models, scrapers with saved HTML fixtures, regex parsers, and cache TTL behavior:

```bash
# Run full unit and fixture test suite
pytest -v

# Run scraper parsing tests specifically
pytest tests/test_scrapers.py -v
```

---

## 3. Running Scraper CLI Smoke Checks

Before running the full web UI, verify individual source connectivity and link extraction against live portals:

```bash
# Smoke test a movie scraper
python -m movie_fetcher.cli_check --category movies --source film2media --query "Inception"

# Smoke test a game scraper (verifies multi-part links and password)
python -m movie_fetcher.cli_check --category games --source yasdl --query "GTA V"

# Smoke test a music scraper (verifies direct MP3 stream URL)
python -m movie_fetcher.cli_check --category music --source nex1music --query "محسن یگانه"
```

Expected output:
- Number of items discovered.
- Extracted direct download URLs with status codes (200/302).
- Archive password and part counts for game queries.

---

## 4. Running the Web Application

Launch the local web server:

```bash
uvicorn movie_fetcher.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser to: `http://127.0.0.1:8000`

---

## 5. End-to-End Validation Scenarios

### Scenario 1: Movie Search & Format Download
1. On `http://127.0.0.1:8000`, ensure the **Movies** tab is active.
2. Enter `"Interstellar"` (or Persian `"میان ستاره ای"`) in the search bar and press Enter.
3. **Verify**:
   - Results display poster art, title, and release year (2014).
   - Format boxes clearly distinguish resolutions: `1080p`, `720p`, `480p`, `x265`.
   - Badges indicate audio track (`دوبله فارسی` / Persian Dubbed vs Soft-sub).
   - Clicking a download button immediately starts downloading the `.mkv` or `.mp4` file directly from the upstream CDN without ad redirects.

### Scenario 2: Game Multi-Part Extraction & Password Copy
1. Switch to the **Games** tab.
2. Search for `"Need for Speed"` or `"Elden Ring"`.
3. Locate a repack result (e.g. from YasDL or Downloadha) and expand the download links.
4. **Verify**:
   - The archive extraction password (e.g. `www.yasdl.com`) is displayed with a "Copy Password" button.
   - Parts are strictly numbered in sequential order: `Part 1`, `Part 2`, ... `Part N`.
   - Clicking "Copy all links" copies every part URL to the clipboard, separated by newlines for immediate import into Internet Download Manager (IDM) or aria2.

### Scenario 3: Music Discovery & Inline Playback
1. Switch to the **Music** tab.
2. Search for an artist or song name (e.g. `"همایون شجریان"` or `"Shadmehr"`).
3. **Verify**:
   - Track cards display artist name, track title, and cover art.
   - An inline HTML5 `<audio>` player is rendered on each card.
   - Clicking play streams the audio smoothly in the browser.
   - Dedicated `320 kbps` and `128 kbps` buttons initiate direct MP3 downloads on click.

### Scenario 4: Fast Cache Verification
1. Repeat any of the searches above with the exact same query text.
2. **Verify**:
   - Results load virtually instantaneously (< 1 second).
   - Server console logs indicate a `CACHE_HIT`.
