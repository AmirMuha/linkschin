# Data Model: User Source Suggestion Form

**Branch**: `004-source-suggestions` | **Date**: 2026-09-29

## Entity: SourceSuggestion

Represents a requested or suggested media download site submitted by one or more users.

### Schema Definition (SQLite)

```sql
CREATE TABLE IF NOT EXISTS source_suggestions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    domain             TEXT NOT NULL UNIQUE,
    url                TEXT NOT NULL,
    category           TEXT NOT NULL,
    source_name        TEXT NOT NULL DEFAULT '',
    sample_url         TEXT NOT NULL DEFAULT '',
    notes              TEXT NOT NULL DEFAULT '',
    requires_auth      INTEGER NOT NULL DEFAULT 0,
    request_count      INTEGER NOT NULL DEFAULT 1,
    status             TEXT NOT NULL DEFAULT 'pending',
    first_submitted_at REAL NOT NULL,
    last_submitted_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_source_suggestions_status_count 
ON source_suggestions(status, request_count DESC);
```

### Fields

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| `id` | Integer | Primary Key, Autoincrement | Unique internal ID |
| `domain` | Text | NOT NULL, UNIQUE | Canonical domain (e.g. `example.com`), extracted from URL |
| `url` | Text | NOT NULL | Most recent or primary full URL submitted |
| `category` | Text | NOT NULL | Category enum: `movies`, `games`, or `music` |
| `source_name` | Text | Default `''` | User-provided friendly title or brand |
| `sample_url` | Text | Default `''` | Sample post or direct link verifying content |
| `notes` | Text | Default `''` | Max 500 chars commentary or scraper suggestions |
| `requires_auth` | Integer (Boolean) | Default 0 | 1 if source requires registration or VIP account |
| `request_count` | Integer | Default 1 | Total number of user submissions for this domain |
| `status` | Text | Default `'pending'` | Lifecycle status: `pending`, `reviewed`, `implemented`, `rejected` |
| `first_submitted_at`| Real | NOT NULL | Unix epoch timestamp of initial submission |
| `last_submitted_at` | Real | NOT NULL | Unix epoch timestamp of most recent submission |

### State Transitions

```text
[User Submits New Domain] -> 'pending'
[User Submits Existing Domain] -> 'pending' (increments request_count, updates last_submitted_at)

'pending' -> 'reviewed'      (Maintainer has evaluated site structure)
'reviewed' -> 'implemented'  (Scraper added under apps/api/sources/)
'reviewed' -> 'rejected'     (Unviable: heavy DRM, paywalled, or non-functional)
```

---

## Entity: SuggestionRateLimit

Tracks client submission frequency by hashed client IP over rolling 24-hour windows.

### Schema Definition (SQLite)

```sql
CREATE TABLE IF NOT EXISTS suggestion_rate_limits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_hash    TEXT NOT NULL,
    timestamp  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rate_limits_ip_time 
ON suggestion_rate_limits(ip_hash, timestamp);
```

### Validation Rules

- **URL**: Must start with `http://` or `https://`. Must contain a valid hostname.
- **Category**: Must be one of `['movies', 'games', 'music']`.
- **Domain Normalization**: Strips `www.`, ports, and paths; downcased.
- **Rate Limit Window**:
  - Max 10 records per `ip_hash` in `timestamp > (current_time - 86400)`.
  - Violations return HTTP 429 Too Many Requests.
- **Notes Length**: Max 500 characters.
- **Source Name Length**: Max 100 characters.
