"""One-off reindex: refresh every stored item from its live page.

The index accumulates rows whose titles and download links have drifted from the
pages they were scraped from (portals rename posts and rotate CDN paths), and rows
written before link enrichment was fixed carry no downloads at all. This walks the
index, re-runs each source plugin's item parser over the stored page_url, and
re-upserts the result.

    python apps/api/backfill.py --dry-run
    python apps/api/backfill.py
    python apps/api/backfill.py --limit 50 --source uptvs

Safe to re-run: it only rewrites rows whose live page yields something, so a source
that is down leaves its existing rows untouched.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
from http_client import AsyncHttpClient  # noqa: E402
from models import Category, MediaItem  # noqa: E402
from sources.base import is_parked_page, unescape_html  # noqa: E402
from sources.games.downloadha import DownloadhaPlugin  # noqa: E402
from sources.games.yasdl import YasDLPlugin  # noqa: E402
from sources.movies.doostihaa import DoostihaaPlugin  # noqa: E402
from sources.movies.uptvs import UpTVsPlugin  # noqa: E402
from sources.music.nex1music import Nex1MusicPlugin  # noqa: E402
from sources.music.popmusic import PopMusicPlugin  # noqa: E402

PLUGINS = {
    "uptvs": UpTVsPlugin,
    "doostihaa": DoostihaaPlugin,
    "yasdl": YasDLPlugin,
    "downloadha": DownloadhaPlugin,
    "nex1music": Nex1MusicPlugin,
    "popmusic": PopMusicPlugin,
}


def stored_items(source_id: str | None, limit: int | None) -> list[dict]:
    conn = db.connect()
    try:
        sql = "SELECT id, source_id, category, title, page_url FROM media_items"
        params: list = []
        if source_id:
            sql += " WHERE source_id = ?"
            params.append(source_id)
        sql += " ORDER BY last_seen ASC"  # oldest/most stale first
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        return [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


async def refresh(row: dict, client: AsyncHttpClient) -> MediaItem | None:
    plugin = PLUGINS.get(row["source_id"])
    if plugin is None:
        return None
    try:
        resp = await client.get(row["page_url"], timeout=plugin().config.timeout_seconds)
    except Exception as e:  # noqa: BLE001 - a dead source must not abort the run
        print(f"  ! fetch failed {row['page_url']}: {e}")
        return None
    if resp.status_code != 200 or is_parked_page(resp.text):
        print(f"  ! skipped ({resp.status_code}) {row['page_url']}")
        return None

    # Start from the stored row so untouched metadata (poster, description) survives.
    # Titles are re-decoded because rows written before unescaping shipped baked-in
    # entities ("Marvel&#8217;s") that only a fresh scrape would have cleaned.
    item = MediaItem(
        id=row["id"],
        title=unescape_html(row["title"]),
        category=Category(row["category"]),
        source_id=row["source_id"],
        page_url=row["page_url"],
    )
    try:
        plugin().parse_item_page(resp.text, item)
    except Exception as e:  # noqa: BLE001
        print(f"  ! parse failed {row['page_url']}: {e}")
        return None
    return item


def summarize(item: MediaItem) -> str:
    if item.movie_variants:
        return f"{len(item.movie_variants)} variants"
    if item.game_releases:
        rels = ", ".join(f"{len(r.parts)}p" for r in item.game_releases)
        return f"{len(item.game_releases)} release(s) [{rels}]"
    if item.music_tracks:
        track = item.music_tracks[0]
        return f"{len(track.downloads)} downloads, stream={'yes' if track.stream_url else 'no'}"
    return "no links"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument("--limit", type=int, default=None, help="max rows to refresh")
    parser.add_argument("--source", default=None, help="restrict to one source id")
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    rows = stored_items(args.source, args.limit)
    if not rows:
        print("nothing to backfill")
        return 0
    print(f"{len(rows)} stored items; dry_run={args.dry_run}")

    semaphore = asyncio.Semaphore(args.concurrency)
    updated: list[MediaItem] = []
    skipped = 0

    async def run(row: dict) -> None:
        nonlocal skipped
        async with semaphore:
            item = await refresh(row, client)
            if item is None:
                skipped += 1
                return
            updated.append(item)
            print(f"  {row['source_id']:11} {row['title'][:42]:44} -> {summarize(item)}")

    async with AsyncHttpClient(timeout=7.0) as client:
        await asyncio.gather(*(run(r) for r in rows))

    if not args.dry_run and updated:
        db.upsert_items(updated)
    print(f"\nrefreshed={len(updated)} skipped={skipped} written={0 if args.dry_run else len(updated)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))