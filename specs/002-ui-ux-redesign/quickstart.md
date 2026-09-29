# Quickstart Validation Guide: Modern Web Interface and UI/UX Redesign

- **Feature**: `002-ui-ux-redesign`
- **Date**: 2026-09-29
- **Status**: Complete

This guide details the step-by-step procedures to run, verify, and validate the modern web interface (`apps/web`) and backend service (`apps/api`) end-to-end.

---

## 1. Prerequisites

- **Node.js**: `v20+` (Detected: `v26.7.0`)
- **Package Manager**: `pnpm v9+` (Detected: `v11.3.0`)
- **Python**: `3.11+` (Detected: `3.12.14`)
- **Virtual Environment**: `.venv` in repository root or `apps/api/.venv`
- **Turborepo**: Configured in root workspace (`turbo.json`)

---

## 2. Environment Setup

### 2.1 Backend (`apps/api`)
```bash
# Activate Python virtual environment and run FastAPI development server
cd apps/api
source .venv/bin/activate  # or root .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Verify the API is operational:
```bash
curl -s http://127.0.0.1:8000/api/health | jq .
curl -s http://127.0.0.1:8000/api/sources | jq .
```

### 2.2 Frontend Web Platform (`apps/web`)
```bash
# In repository root, install dependencies and launch dev server via Turborepo
pnpm install
pnpm --filter @movie-fetcher/web dev
# Or run both simultaneously via Turborepo:
pnpm dev
```
Access web interface: `http://localhost:3000`

---

## 3. End-to-End Validation Scenarios

### Scenario 1: Movie Discovery & Quality Filter Verification
1. Navigate to `http://localhost:3000`.
2. Ensure the "فیلم و سریال" (Movies) tab is active.
3. In the search input, type `Inception` or `تلقین` and press Enter.
4. **Verification**:
   - Skeleton grid renders immediately while request is in-flight.
   - Cards display poster artwork, Persian title, English title, release year (2010), and source tags.
   - Click to expand download options. Check that badges for `1080p`, `720p`, and `480p` appear with audio type labels (e.g. `دوبله فارسی`).
   - Click "کپی لینک" (Copy Link) on any variant: verify toast notification appears with positive confirmation.
   - Inspect the download button markup: verify it links directly to the upstream CDN URL with zero backend proxying.

### Scenario 2: Game Multi-Part Archive & Batch Link Copy
1. Switch category tab to "بازی‌ها" (Games).
2. Enter search query `Cyberpunk` or `GTA`.
3. Locate a game release card with multi-part archives (e.g. from `YasDL`).
4. **Verification**:
   - Verify parts list displays in strictly ascending order (`Part 1`, `Part 2`, ...).
   - Check password pill: click the copy icon and verify clipboard receives the archive password (e.g. `www.yasdl.com`).
   - Click "کپی تمام پارت‌ها" (Copy All Links): verify clipboard contains all direct URLs separated by newlines (`\n`).
   - Paste clipboard into text editor or download manager to verify newline-separated URL formatting.

### Scenario 3: Audio Track Audition & Single-Instance Playback
1. Switch category tab to "موسیقی" (Music).
2. Enter search query `شجریان` or a known song title.
3. On the first result card, click the inline Play icon.
4. **Verification**:
   - Audio begins streaming immediately in the browser without page navigation.
   - The sticky `<GlobalAudioPlayer />` appears at the bottom with title, artist, and live time scrubber.
   - Click Play on a second result card: verify the first track stops immediately and the new track commences (no audio overlap).
   - Verify separate download buttons exist for `320kbps` and `128kbps` with file sizes.

### Scenario 4: Responsive Bidirectional (RTL/LTR) Layout Inspection
1. Open Chrome/Firefox DevTools and toggle Device Emulation to 375px viewport (mobile).
2. Inspect rendered cards:
   - Verify all Persian text aligns right-to-left.
   - Verify all filenames, codecs, hashes, and URLs maintain left-to-right alignment (`dir="ltr"`) without inverted brackets or displaced file extensions.
   - Verify touch targets for download triggers and audio controls measure at least 44x44px.
3. Test keyboard shortcuts on desktop:
   - Press `/` or `Ctrl+K`: verify search input receives immediate focus with existing text selected.
   - Press `Escape`: verify search input is blurred.

### Scenario 5: Direct CDN Invariant Audit (Constitution Principle III)
1. In browser DevTools, open the **Network** tab and filter by `Media`.
2. Play an audio preview or click a download link.
3. **Verification**:
   - The media request URL points directly to the upstream CDN host (e.g. `dl.nex1music.ir`, `dl.yasdl.com`, `cdn.uptvs.com`).
   - No request is sent to `http://localhost:8000/api/proxy/*` or `http://localhost:3000/api/*` for media streaming or downloading.
