# Technical Research & Decisions: User Source Suggestion Form

**Branch**: `004-source-suggestions` | **Date**: 2026-09-29

## 1. Canonical Domain Extraction & Normalization

### Decision
Use Python's standard library `urllib.parse.urlsplit` to extract the `netloc`, strip leading `www.`, convert to lowercase, and split ports if present.

```python
from urllib.parse import urlsplit

def extract_canonical_domain(url: str) -> str:
    parsed = urlsplit(url if "://" in url else f"http://{url}")
    netloc = parsed.netloc.lower().split(":")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc
```

### Rationale
- Zero external package dependencies (`tldextract` rejected).
- Matches standard Iranian media site patterns where mirrors often use subdomains or path variations on the same domain (e.g. `uptvs.com`, `www.uptvs.com`, `uptvs.com/movies`).
- Fast and predictable without filesystem or network access.

### Alternatives Considered
- `tldextract`: Rejected due to external dependency and periodic requirements to download/update Public Suffix Lists.
- Regex extraction: Rejected as brittle across malformed URL edge cases.

---

## 2. Rate Limiting Strategy (10 Submissions / Day per IP)

### Decision
Store rate limit records in a lightweight SQLite table `source_suggestion_rate_limits(ip_hash TEXT NOT NULL, timestamp REAL NOT NULL)` with an index on `(ip_hash, timestamp)`. Submissions check:
`SELECT COUNT(*) FROM source_suggestion_rate_limits WHERE ip_hash = ? AND timestamp > ?`
Where cutoff timestamp is `time.time() - 86400`. Client IP is hashed using `hashlib.sha256(ip.encode()).hexdigest()` to avoid storing raw client IP addresses in plain text.

### Rationale
- Survives process restarts and worker reloads without external state stores.
- Single database connection already managed by `apps/api/db.py`.
- Privacy-conscious: hashes IP before persistence.
- Auto-cleanup: Purge entries older than 24 hours during insertions or periodic startup checks.

### Alternatives Considered
- In-memory dict with TTL: Rejected because restarting Uvicorn or running multiple workers wipes rate limit state.
- Redis: Rejected because introducing a Redis server violates Constitution Principle II (Simplicity / YAGNI).

---

## 3. Duplicate Handling & Upvoting

### Decision
Maintain a `UNIQUE(domain, category)` or `UNIQUE(domain)` constraint on `source_suggestions`.
When a user submits an existing domain:
1. Increment `request_count = request_count + 1`.
2. Update `last_submitted_at = time.time()`.
3. If new optional fields (e.g. `source_name`, `sample_url`, `notes`) are provided and previously empty, update them (or append note snippet).
4. Return HTTP 200 with standard success confirmation so users know their vote was counted.

### Rationale
- Completely avoids row explosion in SQLite.
- Directly translates user submissions into a prioritized demand signal.
- No negative error messages shown to users who suggest a source someone else already submitted.

---

## 4. Admin Endpoint Authentication

### Decision
Use a standard HTTP header `X-Admin-Token` checked against `os.environ.get("ADMIN_TOKEN", "dev-secret-token")`.
Endpoint: `GET /api/admin/suggestions?status=pending&limit=50`.

### Rationale
- Built into FastAPI via `Security(APIKeyHeader(name="X-Admin-Token"))`.
- Simple, testable with `curl -H "X-Admin-Token: dev-secret-token" http://localhost:8000/api/admin/suggestions`.
- Zero user tables, zero password hashing dependencies (bcrypt/argon2), zero cookie sessions.

---

## 5. UI Integration & Modal Design

### Decision
1. Add a small "پیشنهاد منبع" (Suggest Source) link/button directly into `SourceStatusBar.tsx` next to the active sources summary.
2. Render `SourceSuggestModal.tsx` using native React state (open/close).
3. Validate fields on blur/submit (URL scheme, category selected).
4. Trigger existing `ToastNotification` on success/error.

### Rationale
- Places the feature in the exact context where users notice missing or offline sources.
- Reuses existing UI theme, RTL direction, and Tailwind styling tokens.
- Zero state management libraries needed.
