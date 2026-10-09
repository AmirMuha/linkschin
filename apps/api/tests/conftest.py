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


@pytest.fixture
def yasdl_search_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "yasdl_search.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def yasdl_item_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "yasdl_item.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def uptvs_search_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "uptvs_search.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def uptvs_item_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "uptvs_item.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def doostihaa_search_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "doostihaa_search.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def doostihaa_item_html(fixtures_dir: Path) -> str:
    path = fixtures_dir / "doostihaa_item.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def musicdel_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "musicdel_search.html").read_text(encoding="utf-8")


@pytest.fixture
def musicdel_item_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "musicdel_item.html").read_text(encoding="utf-8")


@pytest.fixture
def musicsfa_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "musicsfa_search.html").read_text(encoding="utf-8")


@pytest.fixture
def musicsfa_item_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "musicsfa_item.html").read_text(encoding="utf-8")


@pytest.fixture
def upsong_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "upsong_search.html").read_text(encoding="utf-8")


@pytest.fixture
def upsong_item_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "upsong_item.html").read_text(encoding="utf-8")


@pytest.fixture
def upmusics_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "upmusics_search.html").read_text(encoding="utf-8")


@pytest.fixture
def upmusics_item_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "upmusics_item.html").read_text(encoding="utf-8")


@pytest.fixture
def musictarin_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "musictarin_search.html").read_text(encoding="utf-8")


@pytest.fixture
def musictarin_item_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "musictarin_item.html").read_text(encoding="utf-8")


@pytest.fixture
def onerj_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "onerj_search.html").read_text(encoding="utf-8")


@pytest.fixture
def onerj_item_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "onerj_item.html").read_text(encoding="utf-8")


# 005: committed search captures for the four movie sources whose markup was
# verified against the live site. A fixture on disk that no test loads is never
# executed, so these exist to be consumed by tests/test_movie_sources.py.


@pytest.fixture
def aparat_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "aparat_search.html").read_text(encoding="utf-8")


@pytest.fixture
def filmnet_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "filmnet_search.html").read_text(encoding="utf-8")


@pytest.fixture
def namasha_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "namasha_search.html").read_text(encoding="utf-8")


@pytest.fixture
def rubika_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "rubika_search.html").read_text(encoding="utf-8")


@pytest.fixture
def babakfilm_search_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "babakfilm_search.html").read_text(encoding="utf-8")
