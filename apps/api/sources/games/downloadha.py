"""Downloadha scraper plugin for games."""

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
    clean_absolute_url,
    extract_archive_password,
    is_ad_or_shortener_url,
    is_parked_page,
    parse_part_number,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.downloadha.com"


class DownloadhaPlugin:
    """Downloadha game scraper plugin."""

    def __init__(self, config: SourceConfig | None = None):
        self.config = config or SourceConfig(
            id="downloadha",
            name="Downloadha",
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
        """Search Downloadha for game titles."""
        search_term = query.normalized_query or query.raw_query
        encoded_term = quote(search_term)
        search_url = f"{self.base_url}/?s={encoded_term}"

        try:
            resp = await client.get(search_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                logger.warning("Downloadha search returned %s or parked page", resp.status_code)
                return []
            return self.parse_search_results(resp.text)
        except Exception as e:
            logger.error("Downloadha search failed: %s", e)
            return []

    def parse_search_results(self, html: str) -> list[MediaItem]:
        """Extract media items from search results HTML."""
        items: list[MediaItem] = []
        pattern = re.compile(
            r'<h[12][^>]*class=[\"\'][^\"\']*entry-title[^\"\']*[\"\'][^>]*>\s*'
            r'<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>\s*</h[12]>',
            re.IGNORECASE | re.DOTALL,
        )

        for match in pattern.finditer(html):
            raw_url = match.group(1).strip()
            raw_title = match.group(2).strip()
            clean_title = re.sub(r"<[^>]+>", "", raw_title).strip()
            clean_title = clean_title.replace("&#8211;", "-").replace("&nbsp;", " ")

            post_url = clean_absolute_url(self.base_url, raw_url)
            if not post_url or is_ad_or_shortener_url(post_url):
                continue

            path_slug = [p for p in urlparse(post_url).path.split("/") if p]
            slug = path_slug[-1] if path_slug else str(len(items) + 1)
            item_id = f"dlha_{slug}"

            item = MediaItem(
                id=item_id,
                title=clean_title,
                category=Category.GAMES,
                source_id=self.config.id,
                page_url=post_url,
            )
            items.append(item)

        return items

    async def extract_links(
        self,
        item: MediaItem,
        client: AsyncHttpClient,
    ) -> MediaItem:
        """Extract split-archive download parts and extraction password."""
        try:
            resp = await client.get(item.page_url, timeout=self.config.timeout_seconds)
            if resp.status_code != 200 or is_parked_page(resp.text):
                return item
            self.parse_item_page(resp.text, item)
            return item
        except Exception as e:
            logger.error("Downloadha link extraction failed for %s: %s", item.page_url, e)
            return item

    def parse_item_page(self, html: str, item: MediaItem) -> None:
        """Parse parts, total size, and password from game post HTML."""
        password = extract_archive_password(html)
        total_size = ""
        size_match = re.search(
            r"(?:حجم فایل|حجم)\s*[:：]?\s*([\d.,]+\s*(?:مگابایت|گیگابایت|ترابایت|MB|GB|TB))",
            html,
            re.IGNORECASE,
        )
        if size_match:
            total_size = size_match.group(1).strip()

        # Find all direct archive download links
        link_pattern = re.compile(
            r'<a[^>]+href=[\"\']([^\"\']+\.(?:rar|zip|iso|exe))[\"\'][^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )

        raw_parts: list[tuple[int | None, str, str]] = []
        for match in link_pattern.finditer(html):
            href = match.group(1).strip()
            label = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            abs_url = clean_absolute_url(self.base_url, href)

            if not abs_url or is_ad_or_shortener_url(abs_url):
                continue

            part_num = parse_part_number(label)
            if part_num is None:
                part_num = parse_part_number(href)

            raw_parts.append((part_num, label, abs_url))

        parts: list[GamePartLink] = []
        if raw_parts:
            # Check if any parts had explicit part numbers
            has_explicit_parts = any(p[0] is not None for p in raw_parts)

            if has_explicit_parts:
                for p_num, p_lbl, p_url in raw_parts:
                    if p_num is not None:
                        parts.append(
                            GamePartLink(
                                part_number=p_num,
                                part_label=f"Part {p_num}",
                                download_url=p_url,
                            )
                        )
            else:
                # Single or unnumbered files -> sequential 1..N
                for idx, (_, p_lbl, p_url) in enumerate(raw_parts, 1):
                    parts.append(
                        GamePartLink(
                            part_number=idx,
                            part_label=f"Part {idx}" if len(raw_parts) > 1 else "Full Game",
                            download_url=p_url,
                        )
                    )

        if parts:
            release_group = ""
            for grp in ["FitGirl", "ElAmigos", "DODI", "RUNE", "CODEX", "FLT", "SKIDROW", "CPY", "HI2U"]:
                if grp.lower() in item.title.lower():
                    release_group = grp
                    break

            release = GameRelease(
                id=f"{item.id}_release",
                source_name=self.config.name,
                release_group=release_group,
                total_size=total_size,
                archive_password=password,
                parts=parts,
            )
            item.game_releases = [release]
