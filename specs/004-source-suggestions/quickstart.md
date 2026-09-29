# Quickstart & Validation Guide: User Source Suggestion Form

**Branch**: `004-source-suggestions` | **Date**: 2026-09-29

This guide provides end-to-end verification steps for the source suggestions feature across both backend API and web client.

## Prerequisites

- Python 3.12+ with virtual environment activated (`.venv`)
- Node.js 20+ and `pnpm`
- Running backend service: `poe dev` or `python apps/api/main.py` (port 8000)
- Running frontend service: `pnpm --filter web dev` (port 3000)

---

## Scenario 1: Submit a New Valid Source Suggestion

Submit a new source suggestion for movies via the API.

```bash
curl -X POST http://127.0.0.1:8000/api/sources/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://film2media.click",
    "category": "movies",
    "source_name": "Film2Media",
    "notes": "Direct download links for series and movies",
    "requires_auth": false
  }'
```

**Expected Outcome**:
```json
{
  "success": true,
  "message": "پیشنهاد شما با موفقیت ثبت شد",
  "domain": "film2media.click",
  "request_count": 1,
  "is_existing": false
}
```

---

## Scenario 2: Submit a Duplicate Source (Upvote Test)

Submit the same domain with a path variation or subdomain to verify automatic deduplication and count increment.

```bash
curl -X POST http://127.0.0.1:8000/api/sources/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.film2media.click/page/2",
    "category": "movies"
  }'
```

**Expected Outcome**:
```json
{
  "success": true,
  "message": "پیشنهاد شما با موفقیت ثبت شد",
  "domain": "film2media.click",
  "request_count": 2,
  "is_existing": true
}
```

---

## Scenario 3: Verify Abuse Prevention & Rate Limiting

Send 10 submissions in rapid succession to trigger the 10/day quota per IP.

```bash
for i in {1..11}; do
  curl -s -X POST http://127.0.0.1:8000/api/sources/suggest \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"https://test-site-$i.com\", \"category\": \"movies\"}"
  echo ""
done
```

**Expected Outcome**:
- Submissions 1 through 10 return HTTP 200 with `"success": true`.
- Submission 11 returns HTTP 429 Too Many Requests:
```json
{
  "detail": "سقف مجاز پیشنهاد روزانه شما تکمیل شده است"
}
```

---

## Scenario 4: Admin Inspection of Suggestions

Retrieve the list of suggestions using the admin authentication token.

```bash
# Valid token test (defaults to dev-secret-token if ADMIN_TOKEN unset)
curl -s -X GET "http://127.0.0.1:8000/api/admin/suggestions?status=pending" \
  -H "X-Admin-Token: dev-secret-token"
```

**Expected Outcome**:
```json
{
  "suggestions": [
    {
      "id": 1,
      "domain": "film2media.click",
      "url": "https://film2media.click",
      "category": "movies",
      "source_name": "Film2Media",
      "request_count": 2,
      "status": "pending"
    }
  ],
  "total": 1
}
```

```bash
# Unauthorized test
curl -s -o /dev/null -w "%{http_code}\n" -X GET "http://127.0.0.1:8000/api/admin/suggestions"
# Expected output: 401
```

---

## Scenario 5: Web UI Modal Verification

1. Open `http://localhost:3000` in browser.
2. In the `SourceStatusBar` component, verify the new "پیشنهاد منبع" (Suggest Source) button is visible.
3. Click the button; confirm modal opens with RTL styling, dark mode support, and fields for URL, Category, Source Name, Sample URL, and Notes.
4. Attempt submit without URL or Category; confirm inline form error indicators appear.
5. Fill valid URL and category, submit, and confirm modal closes and a success toast notification appears.

---

## Scenario 6: Automated Test Suite

Run backend and frontend tests to ensure no regressions:

```bash
# Backend pytest suite
pytest apps/api/tests/test_suggestions.py -v

# Frontend type check & tests
pnpm --filter web lint
pnpm --filter web test
```
