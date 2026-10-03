"""Dead-letter queue persistence, inspection, and automated retry processor (User Story 7)."""

from __future__ import annotations

import logging
import time

import db
from models import Category, MediaItem, MovieDownloadVariant, GameRelease, GamePartLink, MusicTrack, MusicDownloadVariant
from extraction.chains import extract_movie_metadata, extract_game_release, extract_music_track

logger = logging.getLogger("extraction.dlq")

MAX_RETRIES = 5
BASE_RETRY_DELAY_SEC = 60.0


def record_dead_letter(
    source_id: str,
    page_url: str,
    category: str,
    raw_html: str,
    error_message: str,
    model_name: str | None = None,
) -> int:
    """Save failed extraction attempt to DLQ table."""
    logger.warning("Recording extraction failure to DLQ for source=%s url=%s: %s", source_id, page_url, error_message)
    return db.insert_dead_letter(
        source_id=source_id,
        page_url=page_url,
        category=category,
        raw_html=raw_html,
        error_message=error_message,
        model_name=model_name,
    )


def list_dead_letters(
    status: str = "pending",
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Return dead-letter queue records for administrative review."""
    return db.list_dead_letters(status=status, category=category, limit=limit, offset=offset)


async def retry_dead_letter(dlq_id: int) -> dict:
    """Re-process a single dead-letter extraction record."""
    conn = db.connect()
    try:
        row = conn.execute("SELECT * FROM extraction_dead_letter WHERE id=?", (dlq_id,)).fetchone()
        if not row:
            return {"id": dlq_id, "success": False, "message": "DLQ record not found"}
        record = dict(row)
    finally:
        conn.close()

    category = record["category"]
    raw_html = record["raw_html"]
    url = record["page_url"]
    source_id = record["source_id"]

    try:
        if category == "movies":
            extracted = await extract_movie_metadata(raw_html, url)
            if not extracted.title:
                raise ValueError("Extraction yielded empty title")
            # Build MediaItem
            item_id = f"{source_id}:{url.rstrip('/').split('/')[-1]}"
            variants = [
                MovieDownloadVariant(
                    id=f"{item_id}:{i}",
                    quality=v.quality,
                    codec=v.codec,
                    audio_track=v.audio_track,
                    download_url=v.download_url,
                    source_name=source_id,
                )
                for i, v in enumerate(extracted.variants)
            ]
            item = MediaItem(
                id=item_id,
                title=extracted.title,
                category=Category.MOVIES,
                source_id=source_id,
                page_url=url,
                release_year=extracted.release_year,
                poster_url=extracted.poster_url,
                description=extracted.description,
                imdb_rating=extracted.imdb_rating,
                movie_variants=variants,
            )
            db.upsert_items([item])

        elif category == "games":
            extracted = await extract_game_release(raw_html, url)
            if not extracted.title:
                raise ValueError("Extraction yielded empty title")
            item_id = f"{source_id}:{url.rstrip('/').split('/')[-1]}"
            parts = [
                GamePartLink(
                    part_number=p.part_number,
                    part_label=p.part_label,
                    download_url=p.download_url,
                    file_size=p.file_size,
                )
                for p in extracted.parts
            ]
            release = GameRelease(
                id=f"{item_id}:rel1",
                source_name=source_id,
                release_group=extracted.release_group,
                version=extracted.version,
                total_size=extracted.total_size,
                archive_password=extracted.archive_password,
                parts=parts,
            )
            item = MediaItem(
                id=item_id,
                title=extracted.title,
                category=Category.GAMES,
                source_id=source_id,
                page_url=url,
                release_group=extracted.release_group,
                archive_password=extracted.archive_password,
                game_releases=[release],
            )
            db.upsert_items([item])

        elif category == "music":
            extracted = await extract_music_track(raw_html, url)
            if not extracted.title:
                raise ValueError("Extraction yielded empty title")
            item_id = f"{source_id}:{url.rstrip('/').split('/')[-1]}"
            track = MusicTrack(
                id=f"{item_id}:track",
                title=extracted.title,
                artist=extracted.artist,
                source_name=source_id,
                poster_url=extracted.poster_url,
                stream_url=extracted.stream_url,
                downloads=[
                    MusicDownloadVariant(
                        bitrate=d.quality,
                        download_url=d.download_url,
                        file_size=d.file_size_text,
                    )
                    for d in extracted.downloads
                ],
            )
            item = MediaItem(
                id=item_id,
                title=extracted.title,
                category=Category.MUSIC,
                source_id=source_id,
                page_url=url,
                stream_url=extracted.stream_url,
                music_tracks=[track],
            )
            db.upsert_items([item])

        # Mark DLQ item as resolved
        db.update_dead_letter(dlq_id, status="resolved")
        logger.info("Successfully re-extracted and resolved DLQ item %d", dlq_id)
        return {"id": dlq_id, "success": True, "message": "Successfully resolved and indexed"}

    except Exception as exc:
        retries = record["retry_count"] + 1
        new_status = "failed" if retries >= MAX_RETRIES else "pending"
        delay = BASE_RETRY_DELAY_SEC * (2 ** retries)
        db.update_dead_letter(dlq_id, status=new_status, error_message=str(exc), next_retry_delay_sec=delay)
        logger.warning("DLQ retry failed for item %d (attempt %d/%d): %s", dlq_id, retries, MAX_RETRIES, exc)
        return {"id": dlq_id, "success": False, "message": f"Retry failed: {exc}"}


async def run_dlq_retry_cycle() -> int:
    """Find and re-process pending DLQ items ready for retry."""
    pending = db.get_pending_dead_letters(limit=10)
    resolved_count = 0
    for item in pending:
        res = await retry_dead_letter(item["id"])
        if res.get("success"):
            resolved_count += 1
    return resolved_count
