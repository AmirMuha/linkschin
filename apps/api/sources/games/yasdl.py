"""YasDL scraper plugin for games."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote, urlparse

from http_client import AsyncHttpClient
from models import (
    Category,
    GamePartLink,
    GameRelease,
    MediaItem,
    SearchQuery,
    SourceConfig,
)
from sources.base import (
    ARCHIVE_LINK_RE,
    classify_post,
    clean_absolute_url,
    extract_archive_password,
    is_ad_or_shortener_url,
    is_parked_page,
    iter_links,
    parse_part_number,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.yasdl.com"


class YasDLPlugin:
    """YasDL game scraper plugin."""

    def __init__(self, config: SourceConfig | None = None):
        self.config = config or SourceConfig(
            id="yasdl",
            name="YasDL",
            category=Category.GAMES,
            base_urls=[DEFAULT_BASE_URL],
            enabled=True,
            timeout_seconds=7.0,
        )

    @property
    def base_url(self) -> str:
        return self.config.primary_base_url or DEFAULT_BASE_URL

    async def search(
        self,
        query: SearchQuery,
        client: AsyncHttpClient,
    ) -> list[MediaItem]:
        """Search YasDL for game titles."""
        search_term = query.normalized_query or query.raw_query
        encoded_term = quote(search_term)
        search_url = f"{self.base_url}/?s={encoded_term}"

        try:
            resp = await client.get(search_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                logger.warning("YasDL search returned %s or parked page", resp.status_code)
                return []
            return self.parse_search_results(resp.text)
        except Exception as e:
            logger.error("YasDL search failed: %s", e)
            return []

    def parse_search_results(self, html: str) -> list[MediaItem]:
        """Extract media items from search results HTML.

        YasDL permalinks are flat (`/105441/<slug>`) with no section segment, so unlike
        Downloadha the URL cannot prove a post is a game and the title is the only
        signal. Soundtracks and software are dropped rather than filed under `games`.
        """
        items: list[MediaItem] = []
        # YasDL posts are typically <h2 class="col post-title"><a href="..." title="...">...</a></h2>
        pattern = re.compile(
            r'<h[12][^>]*class=[\"\'][^\"\']*post-title[^\"\']*[\"\'][^>]*>\s*'
            r'<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*title=[\"\']([^\"\']+)[\"\']',
            re.IGNORECASE,
        )

        for match in pattern.finditer(html):
            raw_url = match.group(1).strip()
            raw_title = match.group(2).strip()
            clean_title = re.sub(r"<[^>]+>", "", raw_title).strip()
            # Clean HTML entities if any
            clean_title = clean_title.replace("&#8211;", "-").replace("&amp;", "&")

            if not raw_url or is_ad_or_shortener_url(raw_url):
                continue
            if classify_post(clean_title) != "game":
                continue

            item_id = f"yasdl_{re.sub(r'[^a-zA-Z0-9]', '_', clean_title)[:40]}"
            items.append(
                MediaItem(
                    id=item_id,
                    title=clean_title,
                    category=Category.GAMES,
                    source_id=self.config.id,
                    page_url=clean_absolute_url(self.base_url, raw_url),
                )
            )

        return items

    async def extract_links(
        self,
        item: MediaItem,
        client: AsyncHttpClient,
    ) -> MediaItem:
        """Fetch game post page and extract archive parts and password."""
        try:
            resp = await client.get(item.page_url, timeout=self.config.timeout_seconds)
            if resp.status_code == 200 and not is_parked_page(resp.text):
                self.parse_item_page(resp.text, item)
        except Exception as e:
            logger.error("YasDL link extraction failed for %s: %s", item.page_url, e)

        return item

    def parse_item_page(self, html: str, item: MediaItem) -> None:
        """Parse game post page for download parts and extraction password."""
        # 1. Extract extraction password
        password = extract_archive_password(html)
        if not password and "yasdl.com" in html.lower():
            # Many YasDL posts state password as www.yasdl.com
            pwd_match = re.search(r"رمز\s*(?:فایل)?\s*:\s*([^\s<]+)", html)
            if pwd_match:
                password = pwd_match.group(1).strip().rstrip(".,;:")

        # 2. Extract total size if listed
        total_size = ""
        size_match = re.search(r"حجم\s*:\s*([^\s<]+(?:\s*[^\s<]+)?)", html)
        if size_match:
            total_size = size_match.group(1).strip()

        # 3. Detect release group (e.g. FitGirl, ElAmigos, TENOKE, CODEX)
        release_group = ""
        group_match = re.search(
            r"\b(FitGirl|DODI|ElAmigos|TENOKE|FLT|RUNE|SKIDROW|CODEX|CPY|RELOADED|GOG)\b",
            html,
            re.IGNORECASE,
        )
        if group_match:
            release_group = group_match.group(1)

        # 4. Extract archive part links
        parts: list[GamePartLink] = []
        seen_urls: set[str] = set()

        for link in iter_links(html, ARCHIVE_LINK_RE):
            clean_url = clean_absolute_url(self.base_url, link.url)

            if not clean_url or clean_url in seen_urls:
                continue
            if is_ad_or_shortener_url(clean_url):
                continue

            # Don't capture side tools like ISDone.rar or DirectX
            if any(tool in clean_url.lower() for tool in ("isdone", "directx", "vcredist")):
                continue

            part_num = parse_part_number(link.label)
            if part_num is None:
                part_num = parse_part_number(clean_url)

            # Single part archives
            if part_num is None:
                part_num = 1
                label = link.label or "دانلود بازی با لینک مستقیم"
            else:
                label = link.label or f"پارت {part_num}"

            seen_urls.add(clean_url)
            parts.append(
                GamePartLink(
                    part_number=part_num,
                    part_label=label,
                    download_url=clean_url,
                )
            )

        if parts:
            item.game_releases = [
                GameRelease(
                    id=f"{item.id}_rel",
                    source_name=self.config.name,
                    release_group=release_group,
                    total_size=total_size,
                    archive_password=password,
                    parts=parts,
                )
            ]
