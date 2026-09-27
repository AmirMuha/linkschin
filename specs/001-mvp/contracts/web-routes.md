# Contract: Web Endpoints & UI Routes

- **Feature**: `001-mvp`
- **Component**: `movie_fetcher.web.app`
- **Status**: Draft

This document defines the web routes, HTTP methods, parameters, and response contracts for the server-rendered application.

---

## Routes

### 1. `GET /`
**Description**: Landing page displaying the search bar and active category tabs.
- **Query Parameters**:
  - `category` (optional string, default: `"movies"`): Initial active tab (`"movies"`, `"games"`, `"music"`).
- **Response**: `200 OK` — `text/html; charset=utf-8`
- **Rendered Components**:
  - Category navigation tabs (`Movies`, `Games`, `Music`).
  - Search input form with Persian/English placeholder.
  - Active source status badge list showing configured portals.

---

### 2. `GET /search`
**Description**: Executes search across the scrapers registered for the active category.
- **Query Parameters**:
  - `q` (required string): Search query text (e.g. `"Interstellar"`, `"تلقین"`, `"Witcher 3"`, `"شادمهر"`).
  - `category` (required string): Selected category (`"movies"`, `"games"`, or `"music"`).
  - `refresh` (optional boolean, default: `false`): If `true`, bypasses cache and forces fresh scrape.
- **Response**: `200 OK` — `text/html; charset=utf-8`
- **Rendered Content**:
  - Main search bar with current query preserved.
  - Category tabs with active state preserved.
  - Result list rendered per category:
    - *Movies*: Grid/cards showing title, year, poster image, and direct download links segmented by resolution (1080p, 720p, 480p, x265) and Persian dub/sub tags. Opportunistic `<video>` embed if stream URL verified.
    - *Games*: Release cards showing repack name, version, total size, archive password with copy button, and complete sequential list of part links with "Copy all links" action.
    - *Music*: Track list with cover art, artist/song title, inline HTML5 `<audio>` player, and 128k/320k direct download buttons.
  - Source diagnostics summary: Lists which sources returned results, and displays soft warning banners for any source that timed out or failed.

---

### 3. `GET /health`
**Description**: System health check and uptime monitor.
- **Response**: `200 OK` — `application/json`
- **Body Schema**:
  ```json
  {
    "status": "healthy",
    "version": "0.1.0",
    "cache_entries": 42,
    "registered_sources": {
      "movies": ["film2media", "avamovie", "zarfilm", "mobomovie"],
      "games": ["yasdl", "downloadha", "game2dl"],
      "music": ["nex1music", "popmusic", "radiojavan", "upmusic"]
    }
  }
  ```

---

### 4. `GET /api/sources`
**Description**: Read-only JSON endpoint detailing configured scraper sources and their active base URLs.
- **Response**: `200 OK` — `application/json`
- **Body Schema**:
  ```json
  [
    {
      "id": "film2media",
      "name": "Film2Media",
      "category": "movies",
      "base_url": "https://www.film2media.click",
      "enabled": true
    },
    {
      "id": "yasdl",
      "name": "YasDL",
      "category": "games",
      "base_url": "https://www.yasdl.com",
      "enabled": true
    }
  ]
  ```
