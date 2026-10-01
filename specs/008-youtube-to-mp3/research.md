# Research: YouTube to MP3 Downloader

## Audio Extraction and Conversion

**Decision**: Use `yt-dlp` invoked via Python's `subprocess` (or a wrapper library like `yt-dlp` python module) configured to extract audio as MP3.
**Rationale**: `yt-dlp` is the industry standard for YouTube extraction, actively maintained, and handles YouTube's frequent player updates. It natively supports invoking `ffmpeg` to extract and convert audio to MP3 format and embed metadata.
**Alternatives considered**: 
- `pytube`: Often broken due to YouTube changes.
- Direct API usage: YouTube Data API doesn't provide stream URLs.

## Rate Limiting and History Storage

**Decision**: Use SQLite for storing both the conversion history (user session -> conversion requests) and tracking rate limits.
**Rationale**: The constitution mandates SQLite with FTS5 and in-memory TTL caching. For persistent history, SQLite is the designated storage. Rate limiting (20/hr/IP) can be tracked in SQLite or an in-memory TTL cache (e.g., `cachetools` in Python). We will use the existing SQLite database to store `conversion_requests` which natively supports querying recent requests per IP/Session for rate limiting.
**Alternatives considered**:
- Redis: Violates the "No complex database servers" constitution rule.

## Progress Tracking

**Decision**: The frontend will poll the API (or use Server-Sent Events) for conversion status based on a `request_id`. The backend will run the download in a background task.
**Rationale**: Audio conversion takes time. Holding an HTTP connection open is brittle. Background processing (via `asyncio.create_task` or a lightweight queue) with status polling is robust and avoids adding heavy message brokers like Celery/RabbitMQ, adhering to the simplicity rule.
**Alternatives considered**: 
- WebSockets: Overkill for simple progress tracking.
- Message Brokers (Celery): Violates constitution's "no distributed message brokers" rule.