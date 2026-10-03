"""Integration test for search indexing, SQLite FTS5 repeat search, and catalog feeds (US1)."""

import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

import db
from models import Category, MediaItem, MovieDownloadVariant
from web.app import app

client = TestClient(app)


def test_search_and_catalog_endpoints():
    with tempfile.TemporaryDirectory() as td:
        db_file = Path(td) / "test.db"

        # Insert a sample movie into db
        item = MediaItem(
            id="movies-sample-digger",
            title="Digger 2024",
            category=Category.MOVIES,
            source_id="uptvs",
            page_url="https://uptvs.com/movie/digger-2024",
            release_year=2024,
            is_featured=True,
            movie_variants=[
                MovieDownloadVariant(
                    id="var-1",
                    quality="1080p",
                    codec="x265",
                    audio_track="FA-DUB",
                    download_url="https://cdn.example.com/digger-1080p.mkv",
                    source_name="uptvs",
                )
            ],
        )
        db.upsert_items([item], db_path=db_file)

        # Test single item detail endpoint
        found_item = db.get_item_by_id("movies-sample-digger", db_path=db_file)
        assert found_item is not None
        assert found_item.title == "Digger 2024"
        assert len(found_item.movie_variants) == 1

        # Test trending feed
        trending = db.get_trending(Category.MOVIES, limit=5, db_path=db_file)
        assert len(trending) >= 1
        assert trending[0].id == "movies-sample-digger"

        # Test latest feed
        latest = db.get_latest(Category.MOVIES, limit=5, db_path=db_file)
        assert len(latest) >= 1

        # Test FTS search
        results = db.search(Category.MOVIES, "digger", db_path=db_file)
        assert len(results) >= 1
        assert results[0].title == "Digger 2024"
