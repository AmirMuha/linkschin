# API Contracts: YouTube to MP3 Downloader

## 1. Initiate Conversion
**POST** `/api/convert`

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response (202 Accepted):**
```json
{
  "request_id": "uuid-1234",
  "status": "pending",
  "message": "Conversion started"
}
```

**Response (429 Too Many Requests):**
```json
{
  "error": "Rate limit exceeded. Maximum 20 conversions per hour."
}
```

**Response (400 Bad Request):**
```json
{
  "error": "Invalid YouTube URL"
}
```

## 2. Check Status
**GET** `/api/convert/{request_id}`

**Response (200 OK):**
```json
{
  "request_id": "uuid-1234",
  "status": "processing",
  "video_title": "Never Gonna Give You Up",
  "progress": 45 
}
```

**Response (200 OK - Completed):**
```json
{
  "request_id": "uuid-1234",
  "status": "completed",
  "video_title": "Never Gonna Give You Up",
  "download_url": "/api/download/uuid-1234"
}
```

## 3. Download File
**GET** `/api/download/{request_id}`

**Response (200 OK):**
- Headers: `Content-Disposition: attachment; filename="Never Gonna Give You Up.mp3"`, `Content-Type: audio/mpeg`
- Body: Binary MP3 data

## 4. Get History
**GET** `/api/convert/history`

**Response (200 OK):**
```json
{
  "history": [
    {
      "request_id": "uuid-1234",
      "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "video_title": "Never Gonna Give You Up",
      "status": "completed",
      "created_at": "2026-10-01T12:00:00Z"
    }
  ]
}
```