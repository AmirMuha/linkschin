"""Catalog feed helpers for trending and latest media shelves."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import db
from models import Category, MediaItem


def get_trending_items(category: str, limit: int = 12) -> list[dict[str, Any]]:
    """Return top trending items for hero banner and top shelf, dynamic from SQLite."""
    items = db.get_trending(category=category, limit=limit)
    return [asdict(item) for item in items]


def get_latest_items(category: str, limit: int = 14) -> list[dict[str, Any]]:
    """Return latest chronologically scraped items from SQLite."""
    items = db.get_latest(category=category, limit=limit)
    return [asdict(item) for item in items]


def get_item_detail(item_id: str) -> dict[str, Any] | None:
    """Return full item representation with all variants and parts."""
    item = db.get_item_by_id(item_id)
    if not item:
        return None
    db.record_item_view(item_id)
    return asdict(item)
