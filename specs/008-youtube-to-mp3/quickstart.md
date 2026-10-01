# Quickstart: YouTube to MP3 Downloader Validation

This guide explains how to validate the YouTube to MP3 Downloader feature end-to-end.

## Prerequisites
- Backend API running (`pnpm --filter api dev`)
- Frontend Web running (`pnpm --filter web dev`)
- `ffmpeg` installed on the host system (required by `yt-dlp` for MP3 extraction)

## Scenario 1: Successful Conversion
1. Open the frontend application in a browser (typically `http://localhost:3000`).
2. Navigate to the MP3 Downloader section.
3. Paste a valid YouTube URL of a short music video (under 20 minutes), e.g., `https://www.youtube.com/watch?v=dQw4w9WgXcQ`.
4. Click **Convert to MP3**.
5. **Observe**: The UI should display a progress indicator (e.g., "pending" -> "processing").
6. **Observe**: Once completed, a download link/button appears.
7. Click the download button.
8. **Verify**: An MP3 file downloads. Play the file to confirm audio quality.
9. **Verify**: Check the MP3 metadata (ID3 tags) in a media player to ensure the title is populated.

## Scenario 2: Rate Limiting
1. Using an API client (like `curl` or Postman), send 21 consecutive POST requests to `/api/convert` with a valid URL.
   ```bash
   for i in {1..21}; do curl -X POST http://localhost:8000/api/convert -json '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'; done
   ```
2. **Verify**: The first 20 requests return `202 Accepted`.
3. **Verify**: The 21st request returns `429 Too Many Requests`.

## Scenario 3: History
1. After completing Scenario 1, refresh the page or navigate away and back.
2. View the conversion history section.
3. **Verify**: The previously converted video is listed with its title and a ready-to-use download button.

## Scenario 4: Error Handling
1. Paste an invalid URL (e.g., `https://example.com`) or a video longer than 20 minutes.
2. Click **Convert**.
3. **Verify**: The UI displays a clear error message (e.g., "Invalid YouTube URL" or "Video exceeds maximum length of 20 minutes") and no download is initiated.