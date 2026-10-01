# Data Model: YouTube to MP3 Downloader

## SQLite Schema Additions

### Table: `conversion_requests`
Tracks user requests, used for both history and rate-limiting.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID (Text) | Primary key, unique identifier for the request |
| `session_id` | Text | Identifier for the user/browser session |
| `ip_address` | Text | IP address (hashed or plain) for rate limiting |
| `youtube_url` | Text | The original YouTube URL |
| `video_title` | Text | Extracted title for metadata/history |
| `status` | Text | Enum: `pending`, `processing`, `completed`, `failed` |
| `file_path` | Text | Path or identifier of the resulting MP3 file (nullable) |
| `error_message`| Text | Explanation if status is `failed` (nullable) |
| `created_at` | Timestamp | When the request was initiated |
| `completed_at`| Timestamp | When the conversion finished (nullable) |

## State Transitions
- `pending`: Request received, validation passed, placed in processing queue.
- `processing`: Background task has started downloading/converting.
- `completed`: MP3 is ready for download.
- `failed`: An error occurred (e.g., video unavailable, too long).

## Validation Rules
- `youtube_url` must match a valid YouTube regex (e.g., `youtube.com/watch?v=`, `youtu.be/`).
- Rate limiting: Count `conversion_requests` for `ip_address` where `created_at` > `now - 1 hour`. If >= 20, reject.