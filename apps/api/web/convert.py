"""YouTube to MP3 asynchronous conversion and immediate streaming delivery (User Story 4)."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Callable

import db

logger = logging.getLogger("web.convert")

TMP_DIR_BASE = Path(os.environ.get("CONVERT_TMP_DIR", "/tmp/linkschin_mp3"))
MAX_HOURLY_CONVERSIONS = int(os.environ.get("MAX_HOURLY_CONVERSIONS", "20"))
YOUTUBE_ID_REGEX = re.compile(r"(?:youtu\.be\/|v=|embed\/|shorts\/)([A-Za-z0-9_-]{11})")


def extract_youtube_id(url: str) -> str | None:
    match = YOUTUBE_ID_REGEX.search(url)
    return match.group(1) if match else None


def check_rate_limit(client_ip: str) -> bool:
    """Return True if client has NOT exceeded 20 requests per hour."""
    recent_count = db.count_recent_conversions(client_ip, window_seconds=3600.0)
    return recent_count < MAX_HOURLY_CONVERSIONS


async def start_conversion_task(
    url: str,
    bitrate: int = 320,
    sample_rate: int = 44100,
    write_meta: bool = True,
    client_ip: str = "127.0.0.1",
) -> dict:
    """Validate YouTube URL, check rate limits, create task and trigger async worker."""
    video_id = extract_youtube_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL. Must contain a valid 11-character video ID.")

    if not check_rate_limit(client_ip):
        raise PermissionError(f"Hourly conversion rate limit exceeded (maximum {MAX_HOURLY_CONVERSIONS} per hour).")

    job_id = str(uuid.uuid4())
    job = db.create_conversion_job(
        job_id=job_id,
        client_ip=client_ip,
        youtube_url=url,
        video_id=video_id,
        bitrate=bitrate,
        sample_rate=sample_rate,
        write_meta=write_meta,
    )

    # Spawn async extraction job
    asyncio.create_task(_run_extraction(job_id, url, video_id, bitrate, sample_rate, write_meta))
    return job


async def _run_extraction(
    job_id: str,
    url: str,
    video_id: str,
    bitrate: int,
    sample_rate: int,
    write_meta: bool,
) -> None:
    job_dir = TMP_DIR_BASE / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(job_dir / "%(title)s.%(ext)s")

    try:
        db.update_conversion_job(job_id, status="processing", progress=15, current_step="Resolving audio streams")

        # Command using yt-dlp to extract best audio and convert to mp3
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", f"{bitrate}k",
            "--output", out_template,
        ]
        if write_meta:
            cmd.append("--add-metadata")

        cmd.append(url)

        db.update_conversion_job(job_id, status="processing", progress=35, current_step="Extracting audio track")

        # Run yt-dlp asynchronously
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace")[:300]
            logger.error("yt-dlp failed for job %s: %s", job_id, err_msg)
            db.update_conversion_job(job_id, status="failed", error_message=err_msg or "Extraction failed")
            cleanup_job_files(job_id)
            return

        db.update_conversion_job(job_id, status="processing", progress=85, current_step="Finalising tags")

        # Find produced mp3 file
        mp3_files = list(job_dir.glob("*.mp3"))
        if not mp3_files:
            db.update_conversion_job(job_id, status="failed", error_message="No MP3 output produced")
            cleanup_job_files(job_id)
            return

        target_file = mp3_files[0]
        title = target_file.stem
        db.update_conversion_job(
            job_id,
            status="completed",
            progress=100,
            current_step="Ready for download",
            video_title=title,
            completed=True,
        )
        logger.info("Conversion completed for job %s: %s", job_id, target_file.name)

    except Exception as exc:
        logger.exception("Unexpected error in extraction worker for job %s: %s", job_id, exc)
        db.update_conversion_job(job_id, status="failed", error_message=str(exc))
        cleanup_job_files(job_id)


def get_job_mp3_path(job_id: str) -> Path | None:
    """Return path to completed MP3 file if present."""
    job_dir = TMP_DIR_BASE / job_id
    if not job_dir.exists():
        return None
    mp3_files = list(job_dir.glob("*.mp3"))
    return mp3_files[0] if mp3_files else None


def cleanup_job_files(job_id: str) -> None:
    """Strictly purge temporary file and directory immediately upon completion."""
    job_dir = TMP_DIR_BASE / job_id
    if job_dir.exists():
        try:
            shutil.rmtree(job_dir, ignore_errors=True)
            logger.info("Purged temporary conversion files for job %s", job_id)
        except Exception as e:
            logger.warning("Failed to purge directory for job %s: %s", job_id, e)
