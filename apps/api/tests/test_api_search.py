"""Unit tests for JSON API endpoints in web/app.py."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cache import GLOBAL_CACHE
import db
from models import Category, MediaItem, MovieDownloadVariant
from web.app import app

client = TestClient(app)


def test_api_health_endpoint():
    """Verify /api/health returns operational status and stats."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "registered_sources" in data
    assert "cache_entries" in data


def test_api_sources_endpoint():
    """Verify /api/sources returns list of source configurations."""
    response = client.get("/api/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "category" in first
    assert "base_url" in first
    assert "enabled" in first


def test_api_search_missing_query():
    """Verify /api/search requires 'q' query parameter."""
    response = client.get("/api/search")
    assert response.status_code == 422


def test_api_search_cached_response():
    """Verify /api/search returns serialized JSON structure from cache."""
    cat = Category.MOVIES
    query = "test movie api"
    variant = MovieDownloadVariant(
        id="test-var-1",
        quality="1080p",
        codec="x265",
        audio_track="دوبله فارسی",
        download_url="https://cdn.example.com/movie.mkv",
        file_size_mb=1500.0,
        source_name="TestPortal",
    )
    item = MediaItem(
        id="movies-test-movie-api",
        title="تست فیلم",
        category=cat,
        source_id="film2media",
        page_url="https://film2media.click/movie/1",
        release_year=2024,
        movie_variants=[variant],
    )
    GLOBAL_CACHE.set(cat, query, [item])

    response = client.get(f"/api/search?q={query}&category=movies")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == query
    assert data["category"] == "movies"
    assert data["is_cached"] is True
    assert len(data["items"]) == 1

    item_dict = data["items"][0]
    assert item_dict["id"] == "movies-test-movie-api"
    assert item_dict["title"] == "تست فیلم"
    assert item_dict["category"] == "movies"
    assert len(item_dict["movie_variants"]) == 1
    assert item_dict["movie_variants"][0]["quality"] == "1080p"
    assert item_dict["movie_variants"][0]["download_url"] == "https://cdn.example.com/movie.mkv"


def test_api_search_empty_cache_entry_does_not_shadow_db(tmp_path, monkeypatch):
    """A scrape that timed out must not blank out a query for the whole TTL.

    GLOBAL_CACHE.set() used to run even with zero items, and a cache hit of []
    was treated as authoritative, so db.search() was never reached.
    """
    monkeypatch.setenv("MOVIE_FETCHER_DB", str(tmp_path / "index.db"))
    # YasDL answers the same query; this check is about Downloadha, so silence it.
    monkeypatch.setenv("MOVIE_FETCHER_ENABLE_YASDL", "false")
    cat = Category.MOVIES
    query = "مرد عنکبوتی"
    GLOBAL_CACHE.set(cat, query, [])

    # Non-empty DB row for the same query.
    stored = MediaItem(
        id="movies-empty-cache-db-row",
        title="انیمیشن مرد عنکبوتی هویت",
        category=cat,
        source_id="uptvs",
        page_url="https://www.uptvs.com/contents/1.html",
    )
    db.upsert_items([stored])

    try:
        response = client.get(f"/api/search?q={query}&category=movies")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1, "cached [] must fall through to the DB row"
        assert data["items"][0]["id"] == stored.id
    finally:
        GLOBAL_CACHE.clear()


def test_cors_headers_present():
    """Verify CORS headers are returned for frontend origin."""
    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_games_response_excludes_music_but_still_indexes_it(tmp_path, monkeypatch):
    """A games tab must not show a soundtrack, but the music tab must still find it.

    Downloadha answers a games query from its soundtrack section, and the scraper files
    that card as `music` rather than dropping it. So the games response has to filter,
    and the filter must not run before the upsert: the index is the only way a
    re-labelled item becomes searchable again, so filtering first would silently make
    every soundtrack permanently unfindable.
    """
    from sources.games.downloadha import DownloadhaPlugin

    scraped = DownloadhaPlugin().parse_search_results(
        "<h1 class='entry-title'><a href='https://www.downloadha.com/game/elden-ring/'>"
        "دانلود بازی Elden Ring</a></h1>"
        "<h1 class='entry-title'><a href='https://www.downloadha.com/others/elden-ost/'>"
        "دانلود موسیقی متن بازی Elden Ring</a></h1>"
    )
    assert [i.category for i in scraped] == [Category.GAMES, Category.MUSIC]

    async def fake_search(self, query, client):
        return list(scraped)

    monkeypatch.setenv("MOVIE_FETCHER_DB", str(tmp_path / "index.db"))
    # YasDL answers the same query; this check is about Downloadha, so silence it.
    monkeypatch.setenv("MOVIE_FETCHER_ENABLE_YASDL", "false")
    monkeypatch.setattr(DownloadhaPlugin, "search", fake_search)
    monkeypatch.setattr(DownloadhaPlugin, "extract_links",
                        lambda self, item, client: _identity(item))

    response = client.get("/api/search?q=elden%20ring&category=games&refresh=true")
    items = response.json()["items"]
    assert [i["title"] for i in items] == ["دانلود بازی Elden Ring"]
    assert all(i["category"] == "games" for i in items)

    # Persisted despite being filtered from the response, so the music tab can serve it.
    indexed = db.search(Category.MUSIC, "Elden Ring", db_path=tmp_path / "index.db")
    assert [i.title for i in indexed] == ["دانلود موسیقی متن بازی Elden Ring"]


async def _identity(item):
    return item
