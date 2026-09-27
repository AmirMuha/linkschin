"""Unit tests for cache and Persian text normalization."""

from __future__ import annotations

import time
from cache import SearchCache, extract_release_year, normalize_persian_text
from models import Category, MediaItem


def test_persian_text_normalization():
    """Verify Arabic character replacement and punctuation collapsing."""
    # Arabic Yeh (ي) -> Persian Yeh (ی)
    assert normalize_persian_text("علي") == "علی"
    # Arabic Kaf (ك) -> Persian Keheh (ک)
    assert normalize_persian_text("كتاب") == "کتاب"
    # Mixed punctuation and ZWNJ
    assert normalize_persian_text("موزیک‌محسن - جدید!") == "موزیک محسن جدید"
    # Case normalization for English terms
    assert normalize_persian_text("GTA V: San Andreas") == "gta v san andreas"


def test_extract_release_year():
    """Verify 4-digit release year extraction from titles."""
    assert extract_release_year("Interstellar 2014 1080p") == 2014
    assert extract_release_year("بازی Prototype - September 2025") == 2025
    assert extract_release_year("Old classic 1985 remastered") == 1985
    assert extract_release_year("No year in this title") is None
    # Out of range numbers should not match as years
    assert extract_release_year("Part 1080 or 4096") is None


def test_cache_hit_and_miss():
    """Verify in-memory TTLCache stores and retrieves items correctly."""
    cache = SearchCache(maxsize=10, ttl_seconds=100)
    items = [
        MediaItem(
            id="item1",
            title="GTA V",
            category=Category.GAMES,
            source_id="downloadha",
            page_url="https://www.downloadha.com/gta",
        )
    ]
    # Miss
    assert cache.get(Category.GAMES, "gta v") is None

    # Set and Hit
    cache.set(Category.GAMES, "GTA V", items)
    hit = cache.get(Category.GAMES, "gta v")
    assert hit is not None
    assert len(hit) == 1
    assert hit[0].title == "GTA V"

    # Different category is a miss
    assert cache.get(Category.MOVIES, "gta v") is None


def test_cache_expiration():
    """Verify cache item expires after TTL."""
    cache = SearchCache(maxsize=10, ttl_seconds=1)
    cache.set(Category.MUSIC, "shadmehr", [])
    assert cache.get(Category.MUSIC, "shadmehr") == []

    # Manually backdate expiration timestamp
    key = cache._make_key(Category.MUSIC, "shadmehr")
    items, _ = cache._store[key]
    cache._store[key] = (items, time.time() - 10)

    assert cache.get(Category.MUSIC, "shadmehr") is None
