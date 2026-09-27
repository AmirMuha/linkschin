"""CLI smoke check runner for testing scrapers directly from the terminal."""

from __future__ import annotations

import argparse
import asyncio
import sys

from cache import normalize_persian_text
from http_client import AsyncHttpClient
from models import Category, SearchQuery
from sources import get_sources_for_category


async def run_check(category_str: str, source_id: str | None, query_str: str) -> int:
    try:
        cat = Category(category_str.lower())
    except ValueError:
        print(f"Error: Invalid category '{category_str}'. Choices: movies, games, music", file=sys.stderr)
        return 1

    sources = get_sources_for_category(cat, include_disabled=True)
    if source_id:
        sources = [s for s in sources if s.config.id.lower() == source_id.lower()]

    if not sources:
        print(f"No plugins found for category '{cat.value}' and source '{source_id}'", file=sys.stderr)
        return 1

    norm_q = normalize_persian_text(query_str)
    search_q = SearchQuery(raw_query=query_str, normalized_query=norm_q, category=cat)

    print(f"\n=======================================================")
    print(f"Running Scraper Check: Category={cat.value} | Query='{query_str}'")
    print(f"Normalized: '{norm_q}'")
    print(f"=======================================================\n")

    async with AsyncHttpClient(timeout=10.0) as client:
        for plugin in sources:
            print(f"[*] Querying source: {plugin.config.name} ({plugin.config.id})...")
            try:
                items = await plugin.search(search_q, client)
            except Exception as e:
                print(f"[-] Search error for {plugin.config.id}: {e}")
                continue

            print(f"[+] Found {len(items)} items from {plugin.config.name}")
            for idx, item in enumerate(items[:3], 1):
                print(f"\n  --- Item {idx}: {item.title} ---")
                print(f"      URL: {item.page_url}")
                if item.poster_url:
                    print(f"      Poster: {item.poster_url}")

                # Extract links for top item
                if idx == 1:
                    print(f"      [*] Extracting detailed links...")
                    enriched = await plugin.extract_links(item, client)
                    if enriched.game_releases:
                        for rel in enriched.game_releases:
                            print(f"      [Game Release] Group: {rel.release_group} | Password: '{rel.archive_password}'")
                            print(f"      [Parts Total]: {len(rel.parts)} parts (Missing gaps: {rel.has_missing_parts})")
                            for p in rel.parts[:4]:
                                print(f"        -> Part {p.part_number}: {p.download_url}")
                    if enriched.music_tracks:
                        for track in enriched.music_tracks:
                            print(f"      [Audio Stream]: {track.stream_url}")
                            for dl in track.downloads:
                                print(f"      [Download {dl.bitrate}]: {dl.download_url}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test Iranian media scrapers")
    parser.add_argument("--category", required=True, help="Media category (movies, games, music)")
    parser.add_argument("--source", required=False, help="Specific source ID (e.g. downloadha, popmusic)")
    parser.add_argument("--query", required=True, help="Search query string")
    args = parser.parse_args()

    exit_code = asyncio.run(run_check(args.category, args.source, args.query))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
