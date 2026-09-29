# API Contract: Aggregator Backend & Web Client

- **Feature**: `002-ui-ux-redesign`
- **Host**: `apps/api` (FastAPI at `http://localhost:8000`)
- **Consumer**: `apps/web` (Next.js at `http://localhost:3000`)

---

## 1. `GET /api/search`

Executes multi-source concurrent scraping or cache lookup, returning structured media items with direct download and stream links.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | - | Search query string (Persian or English) |
| `category` | string | No | `"movies"` | Media category: `"movies"`, `"games"`, or `"music"` |
| `refresh` | boolean | No | `false` | Force bypass of in-memory cache and SQLite database to re-scrape |

### Response Headers
- `Content-Type: application/json`
- `Access-Control-Allow-Origin: *` (or configured web origin)

### Success Response (`200 OK`)

```json
{
  "query": "Inception",
  "category": "movies",
  "is_cached": false,
  "warnings": [
    "منبع AvaMovie به دلیل تأخیر پاسخ موقتاً در دسترس نبود."
  ],
  "items": [
    {
      "id": "movies-inception-2010-uptvs",
      "title": "تلقین (Inception)",
      "original_title": "Inception",
      "category": "movies",
      "source_id": "uptvs",
      "page_url": "https://uptvs.com/movies/inception-2010",
      "release_year": 2010,
      "poster_url": "https://cdn.uptvs.com/posters/inception.jpg",
      "description": "داستان مردی که توانایی ورود به رویاهای دیگران و دزدیدن ایده‌ها را دارد...",
      "stream_url": "https://direct.cdn.uptvs.com/stream/inception-1080p.mp4",
      "movie_variants": [
        {
          "id": "uptvs-1080p-x265-dubbed",
          "quality": "1080p",
          "codec": "x265 10bit",
          "audio_track": "دوبله فارسی",
          "file_size_mb": 1850.0,
          "download_url": "https://cdn.uptvs.com/dl/Inception.2010.1080p.x265.Dubbed.mkv",
          "source_name": "UpTVs"
        },
        {
          "id": "uptvs-720p-x264-sub",
          "quality": "720p",
          "codec": "x264",
          "audio_track": "زیرنویس چسبیده",
          "file_size_mb": 950.0,
          "download_url": "https://cdn.uptvs.com/dl/Inception.2010.720p.x264.SoftSub.mkv",
          "source_name": "UpTVs"
        }
      ],
      "game_releases": [],
      "music_tracks": []
    }
  ]
}
```

### Game Search Item Example (Category = `"games"`)

```json
{
  "id": "games-cyberpunk-2077-yasdl",
  "title": "Cyberpunk 2077: Phantom Liberty",
  "original_title": "Cyberpunk 2077",
  "category": "games",
  "source_id": "yasdl",
  "page_url": "https://yasdl.com/cyberpunk-2077",
  "release_year": 2023,
  "poster_url": "https://yasdl.com/images/cp2077.jpg",
  "description": "نسخه فشرده فیت‌گرل شامل آپدیت نهایی...",
  "stream_url": null,
  "movie_variants": [],
  "game_releases": [
    {
      "id": "yasdl-fitgirl-v2.1",
      "source_name": "YasDL",
      "release_group": "FitGirl Repack",
      "version": "v2.1 + Phantom Liberty DLC",
      "total_size": "58.4 GB",
      "archive_password": "www.yasdl.com",
      "has_missing_parts": false,
      "missing_part_numbers": [],
      "parts": [
        {
          "part_number": 1,
          "part_label": "Part 1",
          "file_size": "2.0 GB",
          "download_url": "https://dl.yasdl.com/games/CP2077.part01.rar"
        },
        {
          "part_number": 2,
          "part_label": "Part 2",
          "file_size": "2.0 GB",
          "download_url": "https://dl.yasdl.com/games/CP2077.part02.rar"
        }
      ]
    }
  ],
  "music_tracks": []
}
```

### Music Search Item Example (Category = `"music"`)

```json
{
  "id": "music-shajarian-rabena-nex1",
  "title": "ربنا",
  "original_title": "Rabbana",
  "category": "music",
  "source_id": "nex1music",
  "page_url": "https://nex1music.ir/shajarian-rabbana",
  "release_year": null,
  "poster_url": "https://nex1music.ir/covers/shajarian.jpg",
  "description": null,
  "stream_url": null,
  "movie_variants": [],
  "game_releases": [],
  "music_tracks": [
    {
      "id": "nex1-shajarian-rabbana",
      "title": "ربنا",
      "artist": "محمدرضا شجریان",
      "album": "آثار ماندگار",
      "cover_url": "https://nex1music.ir/covers/shajarian.jpg",
      "stream_url": "https://dl.nex1music.ir/music/Shajarian-Rabbana-Preview.mp3",
      "source_name": "Nex1Music",
      "downloads": [
        {
          "bitrate": "320kbps",
          "file_size": "9.2 MB",
          "download_url": "https://dl.nex1music.ir/music/Shajarian-Rabbana-320.mp3"
        },
        {
          "bitrate": "128kbps",
          "file_size": "3.8 MB",
          "download_url": "https://dl.nex1music.ir/music/Shajarian-Rabbana-128.mp3"
        }
      ]
    }
  ]
}
```

### Error Responses

- `422 Unprocessable Entity`: Missing `q` query string.
- `500 Internal Server Error`: Critical unhandled server error.

---

## 2. `GET /api/sources`

Returns the operational status, category mapping, and base URLs of all registered scraper plugins.

### Response (`200 OK`)

```json
[
  {
    "id": "uptvs",
    "name": "UpTVs",
    "category": "movies",
    "base_url": "https://uptvs.com",
    "enabled": true
  },
  {
    "id": "doostihaa",
    "name": "Doostihaa",
    "category": "movies",
    "base_url": "https://doostihaa.com",
    "enabled": true
  },
  {
    "id": "yasdl",
    "name": "YasDL",
    "category": "games",
    "base_url": "https://yasdl.com",
    "enabled": true
  },
  {
    "id": "nex1music",
    "name": "Nex1Music",
    "category": "music",
    "base_url": "https://nex1music.ir",
    "enabled": true
  }
]
```

---

## 3. `GET /api/health`

Diagnostic endpoint returning service version, cache stats, and SQLite database health.

### Response (`200 OK`)

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "cache_entries": 42,
  "registered_sources": {
    "movies": ["uptvs", "doostihaa"],
    "games": ["yasdl"],
    "music": ["nex1music"]
  },
  "database_stats": {
    "total_items": 150,
    "categories": {
      "movies": 80,
      "games": 40,
      "music": 30
    }
  }
}
```
