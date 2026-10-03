# Quickstart & Validation Guide: Backend API & UI Alignment

**Feature Branch**: `009-backend-api-ui-alignment`  
**Date**: 2026-10-03  
**Spec Reference**: `specs/009-backend-api-ui-alignment/spec.md`

---

## 1. Prerequisites & Environment Setup

### Backend API (`apps/api`)
```bash
cd apps/api
# Install all dependencies including langchain, pyjwt, yt-dlp
uv sync --all-extras
```

Ensure environment variables in `.env` (or shell profile):
```ini
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-4o-mini  # or claude-3-5-haiku / compatible endpoint
OPERATOR_USERNAME=admin
OPERATOR_PASSWORD_HASH=argon2-hash-or-plaintext-dev-secret
JWT_SECRET_KEY=dev-secret-super-long-key-for-signing-jwt-tokens-12345
```

### Web Frontend (`apps/web`)
```bash
cd apps/web
pnpm install
```

---

## 2. Launching Services & Background Crawlers

In terminal 1 (API Server):
```bash
cd apps/api
uv run poe dev
# Runs FastAPI on http://localhost:8000
```

In terminal 2 (Category Background Crawlers):
```bash
cd apps/api
# Runs all 3 category loops (movies, games, music) concurrently
uv run python worker.py --category all --interval 300
```

In terminal 3 (Web Frontend):
```bash
pnpm dev
# Runs Next.js on http://localhost:3000 (or 3001)
```

---

## 3. End-to-End Validation Scenarios

### Scenario 1: Search Indexing & Movie On-Demand Fallback
1. **Initial Search (Database Miss -> Live Scrape -> Index)**:
   ```bash
   curl -s "http://localhost:8000/api/search?q=Inception&category=movies" | jq '{query, is_cached, count: (.items | length)}'
   ```
   - **Expected**: `is_cached: false`, live scraper executes across movie sources, returns items with download variants, and persists records to SQLite.

2. **Repeat Search (Instant Sub-50ms Index Hit)**:
   ```bash
   curl -w "\nTime: %{time_total}s\n" -s "http://localhost:8000/api/search?q=Inception&category=movies" | jq '{query, is_cached, count: (.items | length)}'
   ```
   - **Expected**: `is_cached: true`, resolves from SQLite FTS5 in `< 0.050s`.

3. **Music / Game Offline-First Resolution**:
   ```bash
   curl -s "http://localhost:8000/api/search?q=gta&category=games" | jq '{query, is_cached, count: (.items | length)}'
   ```
   - **Expected**: Served strictly from local database populated by background game worker.

---

### Scenario 2: Dynamic Home Shelves (Trending & Latest)
1. **Fetch Trending Movies**:
   ```bash
   curl -s "http://localhost:8000/api/catalog/trending?category=movies&limit=6" | jq '.items[] | {id, title, poster_url, imdb_rating}'
   ```
   - **Expected**: Dynamic list of trending movie items populated from live DB records.

2. **Fetch Latest Games**:
   ```bash
   curl -s "http://localhost:8000/api/catalog/latest?category=games&limit=6" | jq '.items[] | {id, title, release_group}'
   ```
   - **Expected**: Chronological game releases sorted by `last_seen`.

---

### Scenario 3: Source Registry Management & Persistent Overrides
1. **Authenticate Operator**:
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "dev-password"}' | jq -r .access_token)
   ```

2. **Update Portal Address (Authenticated)**:
   ```bash
   curl -s -X PATCH http://localhost:8000/api/sources/uptvs \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"base_url": "https://new-uptvs-mirror.com"}' | jq '{id, base_url}'
   ```
   - **Expected**: Returns updated source object; `base_url` is stored in SQLite `source_configs` and persists across API restarts.

3. **Unauthenticated Edit Rejection**:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" -X PATCH http://localhost:8000/api/sources/uptvs \
     -H "Content-Type: application/json" \
     -d '{"enabled": false}'
   ```
   - **Expected**: `401 Unauthorized`.

---

### Scenario 4: Community Source Suggestion Queue
1. **Submit Portal Suggestion**:
   ```bash
   curl -s -X POST http://localhost:8000/api/sources/suggest \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://zarfilm1.com",
       "category": "movies",
       "source_name": "ZarFilm Mirror",
       "proposed_tier": "1"
     }' | jq
   ```
   - **Expected**: `201 Created` with `domain: "zarfilm1.com"` and `request_count: 1`.

2. **Operator Triage Queue**:
   ```bash
   curl -s http://localhost:8000/api/admin/suggestions \
     -H "Authorization: Bearer $TOKEN" | jq '.[0]'
   ```
   - **Expected**: Shows pending suggestion item.

---

### Scenario 5: YouTube to MP3 Extraction & Immediate Stream
1. **Initiate Audio Conversion**:
   ```bash
   JOB=$(curl -s -X POST http://localhost:8000/api/convert \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "bitrate": 320}')
   JOB_ID=$(echo $JOB | jq -r .request_id)
   ```

2. **Poll Status**:
   ```bash
   curl -s "http://localhost:8000/api/convert/$JOB_ID" | jq '{status, progress, current_step}'
   ```
   - **Expected**: Status transitions from `queued` -> `processing` -> `completed`.

3. **Download & Immediate Purge**:
   ```bash
   curl -s -O -J "http://localhost:8000/api/download/$JOB_ID"
   ```
   - **Expected**: Downloads playable `.mp3` file. File is deleted from temporary disk immediately upon stream completion.

---

### Scenario 6: AI Assistant with Database Tools
1. **Ask Assistant About Offline Sources**:
   ```bash
   curl -s -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -H "Accept: application/json" \
     -d '{"message": "کدام منبع‌ها در حال حاضر غیرفعال هستند؟"}' | jq '{message}'
   ```
   - **Expected**: Agent executes `check_source_health` tool and returns grounded answer listing actual inactive sources.

2. **Ask Assistant for Dubbed Releases**:
   ```bash
   curl -s -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -H "Accept: application/json" \
     -d '{"message": "فیلم‌های با دوبله فارسی را به من نشان بده"}' | jq '{message, count: (.media_items | length)}'
   ```
   - **Expected**: Agent executes `search_catalog` tool and embeds matching movie cards.

---

### Scenario 7: Centralized Adaptive Queue & Preemption (User Story 6)
1. **Background Crawl Scheduling**:
   - The queue worker continuously schedules tasks across portal domains obeying domain rate limits (`concurrency = 1`, `delay = 1.0s`).
2. **On-Demand Search Preemption**:
   - When a user submits an on-demand movie search (`GET /api/search?q=NewRelease`), an on-demand task is queued with Priority 0, preempting background crawl tasks (Priority 1) within 100ms.
3. **Adaptive Backoff on 429**:
   - When a portal returns HTTP 429, the domain throttle policy increases delay for that domain (e.g. 2s -> 4s -> 8s) while other domain scrapers execute without delay.

---

### Scenario 8: Dead Letter Queue (DLQ) Failure & Automated Retry (User Story 7)
1. **Simulate AI Extraction Failure**:
   - An unparseable or timed-out page extraction is saved to `extraction_dead_letter` with `status: "pending"`.
2. **Inspect DLQ (Operator Auth)**:
   ```bash
   curl -s http://localhost:8000/api/admin/dlq \
     -H "Authorization: Bearer $TOKEN" | jq '.items[0]'
   ```
   - **Expected**: Returns failed item with `error_message` and `status: "pending"`.
3. **Manual or Automated Re-extraction**:
   ```bash
   curl -s -X POST http://localhost:8000/api/admin/dlq/1/retry \
     -H "Authorization: Bearer $TOKEN" | jq
   ```
   - **Expected**: Re-runs extraction, marks item `status: "resolved"`, and cleanly upserts records into `media_items` without duplicates.
