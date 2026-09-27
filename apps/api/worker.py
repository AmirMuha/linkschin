"""Background crawler worker and Cloudflare solver.

Runs out of the user request path so slow Cloudflare solves never block a search.

Usage:
    python apps/api/worker.py --seed-pages 20
    python apps/api/worker.py --daemon --interval 21600
    python apps/api/worker.py --source nex1music --pages 5
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
from http_client import DEFAULT_HEADERS, AsyncHttpClient  # noqa: E402
from models import Category, MediaItem  # noqa: E402
from sources.music.nex1music import Nex1MusicPlugin  # noqa: E402

logger = logging.getLogger("worker")

FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191/v1")
CRAWLABLE_SOURCES = ("nex1music",)
BATCH_SIZE = 200

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
    """Return challenge-free HTML for `url`, or None if it cannot be solved.

    Tries FlareSolverr first; falls back to a direct GET when no challenge is present.
    """
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
        # Stable across processes: hash() is salted per run, which would duplicate rows.
        digest = hashlib.sha1(music_url.encode("utf-8")).hexdigest()[:16]
        try:
            item = MediaItem(
                id=f"{source_id}_rel_{digest}",
                title=f"{artist} - {track}",
                category=Category.MUSIC,
                source_id=source_id,
                # (source_id, page_url) is the natural key, so every track on a post
                # needs a distinct page_url or they collapse into (and delete) each other.
                page_url=f"{page_url}#t-{digest}",
                stream_url=music_url,
            )
        except ValueError as e:
            logger.debug("Skipping related track %d on %s: %s", index, page_url, e)
            continue
        item.original_title = track
        items.append(item)
    return items


def _page_url(source_id: str, page: int) -> str:
    if source_id == "nex1music":
        return f"{Nex1MusicPlugin().base_url}/page/{page}/"
    raise ValueError(f"Unknown crawlable source '{source_id}'")


def _extract_post_urls(html: str, base_url: str) -> list[str]:
    """Post permalinks from a listing page: absolute, slug-shaped, on the source host.

    Paths are percent-encoded because Persian slugs are not valid request targets.
    """
    urls: list[str] = []
    host = re.sub(r"^www\.", "", base_url.split("://", 1)[-1])
    for href in re.findall(r'<a[^>]+href=["\'](https?://[^"\']+)["\']', html or "", re.IGNORECASE):
        if host not in href:
            continue
        path = href.split(host, 1)[-1].strip("/")
        if not path or "/" in path or path.startswith(("tag", "page", "themev4")) or "." in path:
            continue
        encoded = urllib.parse.urlsplit(href)
        urls.append(urllib.parse.urlunsplit(
            (encoded.scheme, encoded.netloc, urllib.parse.quote(encoded.path), "", "")
        ))
    return list(dict.fromkeys(urls))


async def _crawl_source(
    source_id: str,
    pages: int,
    db_path: str | None,
    per_page_posts: int = 30,
) -> dict[str, int]:
    """Crawl `pages` listing pages after the stored high-water mark, then their posts.

    Returns stats. The crawl only advances the high-water mark for pages it fully
    completed, so a mid-run failure resumes where it stopped instead of skipping.
    """
    plugin = Nex1MusicPlugin()
    conn = db.connect(db_path)
    try:
        start = db.get_last_page(conn, source_id) + 1
    finally:
        conn.close()

    discovered: list[MediaItem] = []
    visited = 0
    written = 0
    completed_pages = 0

    async with AsyncHttpClient(timeout=plugin.config.timeout_seconds) as client:
        for page in range(start, start + pages):
            url = _page_url(source_id, page)
            try:
                resp = await client.get(url, timeout=plugin.config.timeout_seconds)
            except Exception as e:
                logger.warning("Crawl fetch failed %s: %s", url, e)
                break

            if resp.status_code != 200 or not resp.text.strip():
                logger.warning("Crawl stop at %s (status=%s)", url, resp.status_code)
                break

            html = resp.text
            if _is_challenge(html):
                solved = await asyncio.to_thread(solve_url, url)
                if solved is None:
                    logger.warning("Cloudflare challenge on %s, ending run", url)
                    break
                html = solved

            # Listing page: parse its own cards, then walk into the post pages.
            discovered.extend(plugin.parse_search_results(html))
            post_urls = _extract_post_urls(html, plugin.base_url)

            for post_url in post_urls[:per_page_posts]:
                try:
                    post_resp = await client.get(post_url, timeout=plugin.config.timeout_seconds)
                except Exception as e:
                    logger.debug("Post fetch failed %s: %s", post_url, e)
                    continue
                if post_resp.status_code != 200 or not post_resp.text.strip():
                    continue

                post_html = post_resp.text
                if _is_challenge(post_html):
                    post_html = await asyncio.to_thread(solve_url, post_url) or ""
                if not post_html:
                    continue
                visited += 1

                # Related-tracks multiplier: direct MP3 streams off the post page.
                discovered.extend(parse_related_tracks(post_html, post_url, source_id))

                # The post page is itself a full card list; enrich the one matching it.
                for card in plugin.parse_search_results(post_html):
                    if card.page_url.rstrip("/") == post_url.rstrip("/"):
                        try:
                            plugin.parse_item_page(post_html, card)
                        except Exception as e:
                            logger.debug("parse_item_page failed on %s: %s", post_url, e)
                        discovered.append(card)
                        break

                if len(discovered) >= BATCH_SIZE:
                    written += db.upsert_items(discovered, db_path)
                    discovered = []

            completed_pages += 1
            state = db.connect(db_path)
            try:
                db.set_last_page(state, source_id, page)
            finally:
                state.close()
            logger.info("crawled %s: %d post links, %d items pending", url, len(post_urls), len(discovered))

    written += db.upsert_items(discovered, db_path)
    return {
        "source": source_id,
        "pages_requested": pages,
        "pages_completed": completed_pages,
        "posts_visited": visited,
        "items_written": written,
    }


def run_crawl(source_id: str, pages: int, db_path: str | None = None) -> dict[str, int]:
    """Crawl one source and persist discovered items. Returns a small stats dict."""
    stats = asyncio.run(_crawl_source(source_id, pages, db_path))
    stats["total_items"] = db.stats(db_path)["total"]
    return stats


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.DEBUG if os.environ.get("WORKER_DEBUG") else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Background crawler worker for Nex1Music.")
    parser.add_argument("--source", default="nex1music", choices=list(CRAWLABLE_SOURCES))
    parser.add_argument("--pages", type=int, default=1, help="listing pages to crawl this run")
    parser.add_argument("--seed-pages", type=int, default=0, help="backfill N pages from the current high-water mark")
    parser.add_argument("--daemon", action="store_true", help="loop forever, sleeping --interval seconds between runs")
    parser.add_argument("--interval", type=float, default=21600.0, help="seconds between daemon runs (default 6h)")
    parser.add_argument("--db", default=None, help="override sqlite path")
    args = parser.parse_args(argv)

    pages = args.seed_pages or args.pages

    if not args.daemon:
        stats = run_crawl(args.source, pages, args.db)
        logger.info("crawl done: %s", stats)
        return 0

    while True:
        started = time.time()
        try:
            logger.info("crawl done: %s", run_crawl(args.source, pages, args.db))
        except Exception as e:
            logger.error("crawl run failed: %s", e)
        sleep_for = max(0.0, args.interval - (time.time() - started))
        logger.info("sleeping %.0fs until next run", sleep_for)
        time.sleep(sleep_for)


if __name__ == "__main__":
    raise SystemExit(main())
