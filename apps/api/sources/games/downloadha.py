"""Downloadha scraper plugin for games."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote, unquote, urlparse

from http_client import AsyncHttpClient
from models import (
    Category,
    GamePartLink,
    GameRelease,
    MediaItem,
    MusicDownloadVariant,
    MusicTrack,
    SearchQuery,
    SourceConfig,
)
from sources.base import (
    SELF_EXTRACTING_LINK_RE,
    archive_family,
    classify_post,
    clean_absolute_url,
    extract_archive_password,
    is_ad_or_shortener_url,
    is_game_post,
    is_parked_page,
    iter_links,
    parse_part_number,
    unescape_html,
)

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://www.downloadha.com"


_BITRATE_RE = re.compile(r"\b(320|256|192|128|96|64)\s*kbps?\b", re.IGNORECASE)


def parse_bitrate(*parts: str) -> str:
    match = _BITRATE_RE.search(" ".join(parts))
    return f"{match.group(1)}kbps" if match else ""


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
        """Extract media items from search results HTML, routing non-game posts.

        Downloadha's search page is multi-section: `/game/`, `/mobile/`, `/others/`,
        `/movies/` all answer the same query. Stamping `Category.GAMES` on every card
        put a GTA OST in the games tab, so a card only counts as a game when its URL
        section says so (see `is_game_post`).
        """
        items: list[MediaItem] = []
        pattern = re.compile(
            r'<h[12][^>]*class=[\"\'][^\"\']*entry-title[^\"\']*[\"\'][^>]*>\s*'
            r'<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>\s*</h[12]>',
            re.IGNORECASE | re.DOTALL,
        )

        for match in pattern.finditer(html):
            raw_url = match.group(1).strip()
            raw_title = match.group(2).strip()
            clean_title = unescape_html(re.sub(r"<[^>]+>", "", raw_title)).strip()

            post_url = clean_absolute_url(self.base_url, raw_url)
            if not post_url or is_ad_or_shortener_url(post_url):
                continue

            kind = classify_post(clean_title)
            if kind is None:
                continue
            if kind == "game" and not is_game_post(clean_title, post_url):
                continue

            path_slug = [p for p in urlparse(post_url).path.split("/") if p]
            slug = path_slug[-1] if path_slug else str(len(items) + 1)

            items.append(MediaItem(
                id=f"dlha_{slug}",
                title=clean_title,
                category=Category.MUSIC if kind == "music" else Category.GAMES,
                source_id=self.config.id,
                page_url=post_url,
            ))

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
        """Parse a post's files: archive parts for games, bitrates for soundtracks."""
        password = extract_archive_password(html)
        if item.category == Category.MUSIC:
            # A soundtrack post lists one file per bitrate, not volumes of one
            # archive, so "copy all parts" must not present them as a split set.
            downloads: list[MusicDownloadVariant] = []
            seen: set[str] = set()
            for link in iter_links(html, SELF_EXTRACTING_LINK_RE):
                url = clean_absolute_url(self.base_url, link.url)
                if not url or is_ad_or_shortener_url(url) or url in seen:
                    continue
                seen.add(url)
                # The bitrate usually lives in the label or the percent-encoded
                # filename ("OST%20128kbps.zip"), where a word boundary won't match.
                downloads.append(MusicDownloadVariant(
                    bitrate=parse_bitrate(link.label, unquote(url)) or "لینک مستقیم",
                    download_url=url,
                ))
            if not downloads:
                return
            item.music_tracks = [MusicTrack(
                id=f"{item.id}_track",
                title=item.title,
                artist="",
                source_name=self.config.name,
                cover_url=item.poster_url,
                stream_url=downloads[0].download_url,
                downloads=downloads,
            )]
            item.stream_url = downloads[0].download_url
            return

        # Find all direct archive download links, grouped by archive family: one post
        # can ship an exFAT set and a PKG set that both number from 1, and merging
        # them produces duplicate part numbers and a "copy all parts" list that no
        # archiver can assemble.
        total_size = ""
        size_match = re.search(
            r"(?:حجم فایل|حجم)\s*[:：]?\s*([\d.,]+\s*(?:مگابایت|گیگابایت|ترابایت|MB|GB|TB))",
            html,
            re.IGNORECASE,
        )
        if size_match:
            total_size = size_match.group(1).strip()

        families: dict[str, list[tuple[int | None, str]]] = {}
        for link in iter_links(html, SELF_EXTRACTING_LINK_RE):
            abs_url = clean_absolute_url(self.base_url, link.url)
            if not abs_url or is_ad_or_shortener_url(abs_url):
                continue

            part_num = parse_part_number(link.label)
            if part_num is None:
                part_num = parse_part_number(abs_url)

            families.setdefault(archive_family(abs_url), []).append((part_num, abs_url))

        release_group = ""
        for grp in ["FitGirl", "ElAmigos", "DODI", "RUNE", "CODEX", "FLT", "SKIDROW", "CPY", "HI2U"]:
            if grp.lower() in item.title.lower():
                release_group = grp
                break

        releases: list[GameRelease] = []
        for index, (family, entries) in enumerate(families.items()):
            has_explicit_parts = any(p[0] is not None for p in entries)
            parts: list[GamePartLink] = []

            if has_explicit_parts:
                seen: set[int] = set()
                for p_num, p_url in entries:
                    if p_num is None or p_num in seen:
                        continue
                    seen.add(p_num)
                    parts.append(GamePartLink(part_number=p_num, part_label=f"Part {p_num}", download_url=p_url))
            else:
                # Single or unnumbered files -> sequential 1..N within this family.
                for idx, (_p_num, p_url) in enumerate(entries, 1):
                    parts.append(
                        GamePartLink(
                            part_number=idx,
                            part_label=f"Part {idx}" if len(entries) > 1 else "Full Game",
                            download_url=p_url,
                        )
                    )

            if not parts:
                continue
            # GameRelease.__post_init__ sorts and flags gaps, so each family stays
            # strictly sequential and missing volumes are surfaced, not hidden.
            releases.append(
                GameRelease(
                    id=f"{item.id}_release_{index}",
                    source_name=self.config.name,
                    release_group=release_group,
                    total_size=total_size if len(families) == 1 else "",
                    archive_password=password,
                    parts=parts,
                )
            )

        if releases:
            item.game_releases = releases
