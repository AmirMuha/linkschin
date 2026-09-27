"""Test configuration and shared fixtures."""

from __future__ import annotations

from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def downloadha_search_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "downloadha_search.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def downloadha_item_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "downloadha_item.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def popmusic_search_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "popmusic_search.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def popmusic_item_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "popmusic_item.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def nex1music_search_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "nex1music_search.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def nex1music_item_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "nex1music_item.html"
    return path.read_text(encoding="utf-8")
