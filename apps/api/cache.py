"""In-memory cache with Persian text normalization."""

from __future__ import annotations

import re
import time
import unicodedata
from typing import Any

from models import Category, MediaItem

# Persian (۰-۹) and Arabic-Indic (٠-٩) digits -> ASCII. NFKC folds neither set,
# so a search for "۱۲۳" and "١٢٣" would otherwise reach the sources as two
# different queries (FR-006). Defined here rather than reusing
# sources.base.PERSIAN_DIGITS, which maps only the Persian set and would pull
# the whole scraper layer into this module for one table.
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_persian_text(text: str) -> str:
    """
    Apply Unicode normalization (NFKC) and standardize Persian characters.
    - Arabic Yeh (ي) -> Persian Yeh (ی)
    - Arabic Kaf (ك) -> Persian Keheh (ک)
    - Arabic Heh with Yeh (ة / ۀ) -> Persian Heh (ه)
    - Persian and Arabic-Indic digits -> ASCII
    - Zero-width non-joiner (ZWNJ) -> space
    - Collapse redundant whitespace and trim
    """
    if not text:
        return ""

    # NFKC normalizes compatibility characters
    normalized = unicodedata.normalize("NFKC", text)

    # Character substitutions
    substitutions = {
        "ي": "ی",  # ي -> ی
        "ك": "ک",  # ك -> ک
        "ة": "ه",  # ة -> ه
        "ۀ": "ه",  # ۀ -> ه
        "‌": " ",       # ZWNJ -> space
        "‏": "",        # RLM -> empty
        "‎": "",        # LRM -> empty
    }
    for src, dst in substitutions.items():
        normalized = normalized.replace(src, dst)

    normalized = normalized.translate(PERSIAN_DIGITS)

    # Clean punctuation and normalize spacing
    normalized = re.sub(r"[\s\-_.:,;!?()\[\]{}\"\']+", " ", normalized)
    return normalized.strip().lower()


def extract_release_year(text: str) -> int | None:
    """Extract 4-digit release year between 1950 and 2035 from query text."""
    match = re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", text)
    if match:
        return int(match.group(1))
    return None


class SearchCache:
    """
    In-memory TTL cache for category queries.
    Default TTL: 45 minutes (2700 seconds). Max entries: 2000.
    """

    def __init__(self, maxsize: int = 2000, ttl_seconds: int = 2700):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[list[MediaItem], float]] = {}

    # FR-005: the two scopes are different result sets, so they are different keys.
    # Without the scope in the key, whichever ran first would answer for both and the
    # toggle would appear to do nothing on a warm cache.
    def _make_key(self, category: Category | str, query: str, scope: str = "downloads") -> str:
        cat_str = category.value if isinstance(category, Category) else str(category)
        norm_q = normalize_persian_text(query)
        return f"{cat_str.lower()}:{scope}:{norm_q}"

    def get(self, category: Category | str, query: str, scope: str = "downloads") -> list[MediaItem] | None:
        key = self._make_key(category, query, scope)
        entry = self._store.get(key)
        if entry is None:
            return None
        items, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return items

    def set(
        self,
        category: Category | str,
        query: str,
        items: list[MediaItem],
        scope: str = "downloads",
    ) -> None:
        key = self._make_key(category, query, scope)
        if len(self._store) >= self.maxsize:
            # Evict oldest entry (simple FIFO / TTL eviction)
            now = time.time()
            expired = [k for k, (_, exp) in self._store.items()
                       if now > exp]
            for k in expired:
                del self._store[k]
            while len(self._store) >= self.maxsize:
                del self._store[next(iter(self._store))]
        self._store[key] = (items, time.time() + self.ttl_seconds)

    def clear(self) -> None:
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)


# Global singleton instance
GLOBAL_CACHE = SearchCache()
