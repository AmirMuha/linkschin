# Data Model: AI Conversational Search Assistant

**Feature**: `003-ai-assistant`
**Date**: 2026-09-29
**Status**: Completed

## 1. Conceptual Domain Entities

```text
+-----------------------+          +-----------------------+
|  ConversationSession  | 1      * |      ChatMessage      |
|-----------------------|<-------->|-----------------------|
| id: UUID/String       |          | id: String            |
| created_at: float     |          | role: user|assistant  |
| updated_at: float     |          | content: String       |
| metadata: dict        |          | tool_calls: list      |
+-----------------------+          | media_cards: list     |
                                   +-----------------------+
                                               |
                                               v references
                                   +-----------------------+
                                   |       MediaItem       |
                                   |  (Existing Model)     |
                                   +-----------------------+
                                               | persists into
                                               v
                                   +-----------------------+
                                   |      search_fts       |
                                   |  (SQLite FTS5 Index)  |
                                   +-----------------------+
```

---

## 2. Python Schemas & DTOs (`apps/api/assistant/models.py`)

### 2.1 Chat Request & Response Models

```python
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class ChatMessage(BaseModel):
    role: MessageRole
    content: str = ""
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[dict[str, Any]]] = None

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="Client session identifier")
    message: str = Field(..., min_length=1, max_length=2000, description="User input text")
    stream: bool = Field(True, description="Whether to stream response via Server-Sent Events")

class ToolExecutionEvent(BaseModel):
    tool_name: str
    stage: str  # "start" | "progress" | "complete" | "fallback"
    message: str
    query: Optional[str] = None
    result_count: Optional[int] = None

class ChatResponse(BaseModel):
    session_id: str
    message: str
    media_items: list[dict[str, Any]] = []
    events: list[ToolExecutionEvent] = []
```

### 2.2 Tool Definitions (OpenAI Function Calling Format)

```python
SEARCH_CATALOG_TOOL = {
    "type": "function",
    "function": {
        "name": "search_catalog",
        "description": "Search the local catalog database and configured scrapers for movies, series, games, or music. Always call this first.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["movies", "games", "music"],
                    "description": "Media category to search"
                },
                "query": {
                    "type": "string",
                    "description": "Normalized candidate search query in Persian or English"
                }
            },
            "required": ["category", "query"]
        }
    }
}

SEARCH_WEB_TOOL = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Fallback web discovery search. Only call this when search_catalog returns zero results or the requested media is missing.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["movies", "games", "music"],
                    "description": "Media category to search"
                },
                "query": {
                    "type": "string",
                    "description": "Specific search query for web search engine"
                }
            },
            "required": ["category", "query"]
        }
    }
}
```

---

## 3. Database Persistence Integration

Discovered external items leverage the existing database schema in `apps/api/db.py`:

```sql
-- Existing table in data/index.db
-- When search_web finds an item, it constructs a MediaItem and calls db.upsert_items([item])
-- SQLite trigger automatically indexes title_norm and page_url into search_fts
INSERT INTO media_items (
    id, category, source_id, title, title_norm, artist,
    page_url, poster_url, release_year, description, stream_url,
    release_group, archive_password, total_size, first_seen, last_seen
) VALUES (...)
ON CONFLICT(source_id, page_url) DO UPDATE SET
    title = excluded.title,
    title_norm = excluded.title_norm,
    last_seen = excluded.last_seen;
```

**State Transitions & Deduplication**:
1. `search_web` scrapes candidates.
2. Filter for direct media links (`.mp4`, `.mkv`, `.mp3`, `.zip`, `.rar`, CDN URLs).
3. If valid direct links exist, map to `MediaItem` with `source_id="web_search"`.
4. Commit via `db.upsert_items([item])`.
5. Trigger in `db.py` updates `search_fts`.
6. Immediate subsequent queries against `search_fts` match and return the newly ingested item.
