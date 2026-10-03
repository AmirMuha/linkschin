"""Tests for YouTube to MP3 conversion tasks and DLQ reliability (US4, US6, US7)."""

import pytest
from fastapi.testclient import TestClient

import db
import extraction.dead_letter as dlq
from web.app import app
from web.convert import extract_youtube_id

client = TestClient(app)


def test_youtube_url_parsing():
    assert extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_youtube_id("https://invalid-url.com") is None


def test_convert_invalid_url_rejected():
    resp = client.post("/api/convert", json={"url": "https://not-youtube.com/audio"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_dlq_lifecycle():
    # Insert a dead letter item
    dlq_id = db.insert_dead_letter(
        source_id="uptvs",
        page_url="https://uptvs.com/broken-page",
        category="movies",
        raw_html="<html><body><h1>Test Broken Movie</h1></body></html>",
        error_message="Simulation test extraction failure",
    )
    assert dlq_id > 0

    # Verify listed in pending
    pending = dlq.list_dead_letters(status="pending")
    assert any(item["id"] == dlq_id for item in pending)

    # Retry the dead letter item
    result = await dlq.retry_dead_letter(dlq_id)
    assert result["success"] is True

    # Check status transitioned to resolved
    conn = db.connect()
    try:
        row = conn.execute("SELECT status FROM extraction_dead_letter WHERE id=?", (dlq_id,)).fetchone()
        assert row["status"] == "resolved"
    finally:
        conn.close()
