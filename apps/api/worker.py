"""Background crawler worker and continuous multi-category ingestion daemon.

Runs out of the user request path, crawling sources and updating the local SQLite FTS5 index.

Usage:
    python apps/api/worker.py --category all --interval 300
    python apps/api/worker.py --category movies --pages 3
    python apps/api/worker.py --category games --pages 2
    python apps/api/worker.py --category music --source nex1music
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db
from crawler.throttle import GLOBAL_THROTTLE
from extraction.chains import extract_movie_metadata, extract_game_release, extract_music_track
import extraction.dead_letter as dlq
from http_client import DEFAULT_HEADERS, AsyncHttpClient
from models import (
    Category,
    GamePartLink,
    GameRelease,
    MediaItem,
    MovieDownloadVariant,
    MusicDownloadVariant,
    MusicTrack,
    SearchQuery,
)
from sources import get_all_source_configs, get_sources_for_category, health
from sources.music.nex1music import Nex1MusicPlugin

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("worker")

FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191/v1")
CRAWLABLE_SOURCES = ("nex1music",)
BATCH_SIZE = 100
DEFAULT_CRAWL_INTERVAL = 300.0  # 5 minutes

# Signatures of an interstitial Cloudflare challenge page.
CHALLENGE_MARKERS = (
    "cf-browser-verification",
    "cf_chl_opt",
    "just a moment",
    "cf_chl_jschl",
    "checking your browser",
)


def _is_challenge(html: str) -> bool:
    low = html[:20000].lower()
    return any(marker in low for marker in CHALLENGE_MARKERS)


def _urllib_get(url: str, payload: dict | None = None, timeout: float = 60.0) -> str:
    """POST JSON if payload given, else GET. Returns the response body."""
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {**DEFAULT_HEADERS, "Content-Type": "application/json"} if data else dict(DEFAULT_HEADERS)
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def solve_url(url: str, timeout: float = 60.0) -> str | None:
    """Return challenge-free HTML for `url`, or None if it cannot be solved."""
    try:
        raw = _urllib_get(FLARESOLVERR_URL, {"cmd": "request.get", "url": url, "maxTimeout": int(timeout * 1000)}, timeout)
        payload = json.loads(raw)
        solution = payload.get("solution") or {}
        html = solution.get("response")
        if html:
            return html
        logger.debug("FlareSolverr returned no HTML for %s (status=%s)", url, payload.get("status"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        logger.debug("FlareSolverr unavailable at %s (%s); falling back to direct GET", FLARESOLVERR_URL, e)
    except json.JSONDecodeError as e:
        logger.debug("FlareSolverr returned non-JSON for %s: %s", url, e)

    try:
        html = _urllib_get(url, timeout=min(timeout, 20.0))
    except (urllib.error.URLError, OSError) as e:
        logger.debug("Direct GET failed for %s: %s", url, e)
        return None

    if _is_challenge(html):
        logger.debug("Cloudflare challenge unresolved for %s and no FlareSolverr available", url)
        return None
    return html


def _encode_media_url(url: str) -> str:
    """Percent-encode a raw media href, preserving path separators and query syntax."""
    parts = urllib.parse.urlsplit(url.strip())
    return urllib.parse.urlunsplit((
        parts.scheme,
        parts.netloc,
        urllib.parse.quote(parts.path, safe="/%:@!$&'()*+,;=~-._"),
        parts.query,
        parts.fragment,
    ))


def _bitrate_of(url: str) -> str:
    match = re.search(r"\[(\d{3})\]", url)
    return f"{match.group(1)}kbps" if match else ""


def parse_related_tracks(html: str, page_url: str, source_id: str = "nex1music") -> list[MediaItem]:
    """Build direct-stream MediaItems from `div.item[data-artist][data-track][data-music]` blocks."""
    items: list[MediaItem] = []
    pattern = re.compile(
        r'<div class="item"[^>]*\bdata-artist="([^"]*)"[^>]*\bdata-track="([^"]*)"[^>]*\bdata-music="([^"]*)"',
        re.IGNORECASE,
    )
    for index, (artist, track, music_url) in enumerate(pattern.findall(html or "")):
        artist, track, music_url = artist.strip(), track.strip(), music_url.strip()
        if not (artist and track and music_url):
            continue
        music_url = _encode_media_url(music_url)
        digest = hashlib.sha1(music_url.encode("utf-8")).hexdigest()[:16]
        try:
            item = MediaItem(
                id=f"{source_id}_rel_{digest}",
                title=f"{artist} - {track}",
                category=Category.MUSIC,
                source_id=source_id,
                page_url=f"{page_url}#t-{digest}",
            )
        except ValueError as e:
            logger.debug("Skipping related track %d on %s: %s", index, page_url, e)
            continue
        item.original_title = track
        item.music_tracks = [
            MusicTrack(
                id=f"{item.id}_track",
                title=track,
                artist=artist,
                source_name=source_id,
                stream_url=music_url,
                downloads=[MusicDownloadVariant(bitrate=_bitrate_of(music_url), download_url=music_url)],
            )
        ]
        item.stream_url = music_url
        items.append(item)
    return items


def match_post_card(cards: list[MediaItem], post_url: str) -> MediaItem | None:
    """Find the card that represents `post_url` itself among a post page's cards."""
    target = post_url.rstrip("/")
    for card in cards:
        if card.page_url.rstrip("/") == target:
            return card
    slug = target.rsplit("/", 1)[-1]
    if slug:
        for card in cards:
            if card.page_url.rstrip("/").rsplit("/", 1)[-1] == slug:
                return card
    return None


async def crawl_category_sources(category: Category, pages: int = 1, db_path: str | None = None) -> dict[str, Any]:
    """Crawl active sources for a category using domain throttling and extraction chains."""
    plugins = get_sources_for_category(category, include_disabled=False)
    db_configs = db.get_source_configs(db_path)

    # Filter out sources disabled by database override
    active_plugins = []
    for p in plugins:
        override = db_configs.get(p.config.id)
        if override and not override.get("enabled", 1):
            continue
        active_plugins.append(p)

    total_discovered = 0
    errors = 0

    async with AsyncHttpClient(timeout=10.0) as client:
        for plugin in active_plugins:
            source_id = plugin.config.id
            domain = plugin.config.primary_base_url
            try:
                # 1. Acquire domain rate limit / backoff slot
                await GLOBAL_THROTTLE.acquire(domain)
                search_q = SearchQuery(raw_query="", normalized_query="", category=category)

                # Fetch listing or recent posts
                found = await asyncio.wait_for(plugin.search(search_q, client), timeout=10.0)
                GLOBAL_THROTTLE.release(domain, is_throttled=False)

                if found:
                    # Enrich and extract
                    for item in found[:15]:
                        try:
                            # Standard plugin extraction
                            await plugin.extract_links(item, client)
                        except Exception as ex:
                            logger.warning("Plugin extract error on %s: %s; routing to AI extraction", item.page_url, ex)
                            # Route to AI extraction / DLQ
                            try:
                                resp = await client.get(item.page_url)
                                raw_html = resp.text
                                if category == Category.MOVIES:
                                    extracted = await extract_movie_metadata(raw_html, item.page_url)
                                elif category == Category.GAMES:
                                    extracted = await extract_game_release(raw_html, item.page_url)
                                else:
                                    extracted = await extract_music_track(raw_html, item.page_url)
                            except Exception as dlq_err:
                                dlq.record_dead_letter(
                                    source_id=source_id,
                                    page_url=item.page_url,
                                    category=category.value,
                                    raw_html="",
                                    error_message=str(dlq_err),
                                )

                    written = db.upsert_items(found, db_path)
                    total_discovered += written
                    logger.info("Category %s - Source %s: %d items indexed", category.value, source_id, written)

            except asyncio.TimeoutError:
                logger.warning("Category %s - Source %s timed out", category.value, source_id)
                GLOBAL_THROTTLE.release(domain, is_throttled=True)
                errors += 1
            except Exception as e:
                logger.error("Category %s - Source %s failed: %s", category.value, source_id, e)
                GLOBAL_THROTTLE.release(domain, is_throttled=True)
                errors += 1

    return {
        "category": category.value,
        "items_written": total_discovered,
        "errors": errors,
    }


async def run_category_daemon(category: Category, interval: float = DEFAULT_CRAWL_INTERVAL, db_path: str | None = None) -> None:
    """Continuous background loop crawling one category and executing DLQ retries."""
    logger.info("Starting background crawl daemon for category: %s (interval=%.0fs)", category.value, interval)
    while True:
        started = time.time()
        try:
            stats = await crawl_category_sources(category, pages=1, db_path=db_path)
            logger.info("Crawl completed for %s: %s", category.value, stats)
            # Run DLQ retry cycle
            resolved = await dlq.run_dlq_retry_cycle()
            if resolved > 0:
                logger.info("DLQ retry cycle resolved %d failed extractions", resolved)
        except Exception as e:
            logger.error("Error in category daemon %s: %s", category.value, e)

        elapsed = time.time() - started
        sleep_time = max(10.0, interval - elapsed)
        await asyncio.sleep(sleep_time)


async def run_all_daemons(interval: float = DEFAULT_CRAWL_INTERVAL, db_path: str | None = None) -> None:
    """Run all three category background crawlers concurrently in one process."""
    await asyncio.gather(
        run_category_daemon(Category.MOVIES, interval, db_path),
        run_category_daemon(Category.GAMES, interval, db_path),
        run_category_daemon(Category.MUSIC, interval, db_path),
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("WORKER_DEBUG") else logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    )
    parser = argparse.ArgumentParser(description="Multi-category background crawler daemon for Linkschin.")
    parser.add_argument(
        "--category",
        default="all",
        choices=["all", "movies", "games", "music"],
        help="Media category to crawl continuously (default: all)",
    )
    parser.add_argument("--pages", type=int, default=1, help="Pages to crawl per run")
    parser.add_argument("--daemon", action="store_true", help="Loop forever, sleeping --interval seconds between runs")
    parser.add_argument("--interval", type=float, default=DEFAULT_CRAWL_INTERVAL, help="Seconds between daemon runs")
    parser.add_argument("--db", default=None, help="Override sqlite database path")
    args = parser.parse_args(argv)

    if not args.daemon:
        if args.category == "all":
            async def run_all_once():
                res = await asyncio.gather(
                    crawl_category_sources(Category.MOVIES, args.pages, args.db),
                    crawl_category_sources(Category.GAMES, args.pages, args.db),
                    crawl_category_sources(Category.MUSIC, args.pages, args.db),
                )
                return res
            results = asyncio.run(run_all_once())
            logger.info("One-shot crawl completed for all categories: %s", results)
        else:
            cat_enum = Category(args.category)
            stats = asyncio.run(crawl_category_sources(cat_enum, args.pages, args.db))
            logger.info("One-shot crawl completed for %s: %s", args.category, stats)
        return 0

    # Daemon mode
    if args.category == "all":
        asyncio.run(run_all_daemons(args.interval, args.db))
    else:
        cat_enum = Category(args.category)
        asyncio.run(run_category_daemon(cat_enum, args.interval, args.db))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
