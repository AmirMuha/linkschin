# Quickstart & Verification Guide: AI Conversational Search Assistant

**Feature**: `003-ai-assistant`
**Date**: 2026-09-29
**Status**: Ready for Implementation

This guide provides step-by-step verification scenarios to test the AI assistant, catalog tool queries, web fallback, auto-indexing, and web widget end-to-end.

---

## 1. Prerequisites & Environment Setup

Ensure virtual environment is active and dev dependencies are installed:

```bash
cd apps/api
source .venv/bin/activate

# Environment variables for AI assistant (defaults work with local or mock server)
export AI_API_BASE_URL="http://localhost:11434/v1"   # Ollama / vLLM / OpenAI proxy
export AI_MODEL="qwen2.5:7b"                         # Any tool-calling model
export AI_API_KEY="dummy"                            # Key if remote provider used
```

---

## 2. Automated Test Verification (Offline & Mocked)

Run the dedicated test suite for assistant tool execution, query translation, and web fallback:

```bash
# Run unit & contract tests with respx mocks (no external network needed)
pytest tests/test_assistant.py -v

# Run full project test suite
pytest tests -v
```

Expected Outcome: All assistant tests pass without network requests or external LLM connectivity.

---

## 3. End-to-End Validation Scenarios

### Scenario A: Local Catalog Discovery (Tool 1 Execution)

1. Start development server:
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Send conversational query for a title existing in the local catalog:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "یک فیلم علمی تخیلی از نولان پیدا کن", "stream": false}'
   ```
3. **Verification**:
   - Response contains `media_items` with direct download links.
   - Events show `search_catalog` called.
   - `search_web` was **not** called.

---

### Scenario B: Web Search Fallback & Ingestion (Tool 2 & 3 Execution)

1. Query for a rare or unindexed title:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "دانلود انیمیشن کوتاه Piper با لینک مستقیم", "stream": false}'
   ```
2. **Verification**:
   - `events` show:
     1. `search_catalog` invoked and returned 0 results.
     2. Status event: `Searching external media sources...`
     3. `search_web` invoked.
     4. `index_discovered_media` invoked.
   - Inspect database to verify item was indexed:
     ```bash
     sqlite3 data/index.db "SELECT title, category, source_id FROM media_items WHERE title LIKE '%Piper%';"
     ```
3. Run identical query again:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Piper", "stream": false}'
   ```
   Verify that this time results resolve immediately from `search_catalog` without invoking `search_web`.

---

### Scenario C: Web Interface Chat Widget

1. Open browser at `http://127.0.0.1:8000/`.
2. Locate the floating chat assistant button in the bottom corner.
3. Click the widget button to expand the chat window.
4. Type a media request (e.g. `Need a racing game`) and press Enter.
5. **Verification**:
   - Widget displays typing / tool execution indicators ("Searching catalog...").
   - Results render as formatted media cards with direct download buttons.
   - Clicking download triggers direct CDN link without opening new advertising tabs or relaying through the app server (Constitution Principle III).
