"""Unit and fixture parser tests for movie scraper plugins."""

from __future__ import annotations

from models import Category
from sources.movies.doostihaa import DoostihaaPlugin
from sources.movies.uptvs import UpTVsPlugin


def test_uptvs_search_parsing(uptvs_search_html: str):
    """Verify item extraction from real UpTVs search page fixture."""
    plugin = UpTVsPlugin()
    items = plugin.parse_search_results(uptvs_search_html)

    assert len(items) > 0
    first = items[0]
    assert "بتمن" in first.title
    assert first.page_url.startswith("https://www.uptvs.com/contents/")
    assert first.category == Category.MOVIES
    assert first.source_id == "uptvs"


def test_uptvs_item_link_extraction(uptvs_item_html: str):
    """Verify video download links and stream URL extraction from UpTVs fixture."""
    plugin = UpTVsPlugin()
    items = plugin.parse_search_results(uptvs_item_html)
    target = items[0] if items else plugin.parse_search_results("<a href='https://www.uptvs.com/contents/batman-2026.html' title='Batman 2026'></a>")[0]

    plugin.parse_item_page(uptvs_item_html, target)

    assert len(target.movie_variants) >= 2
    qualities = [v.quality for v in target.movie_variants]
    assert "1080p" in qualities
    assert "720p" in qualities

    for v in target.movie_variants:
        assert v.download_url.startswith("https://")
        assert ".mp4" in v.download_url or ".mkv" in v.download_url
        assert v.source_name == "UpTVs"

    # Verify stream URL is selected from MP4 variant
    assert target.stream_url is not None
    assert target.stream_url.startswith("https://")
    assert ".mp4" in target.stream_url


def test_doostihaa_search_parsing(doostihaa_search_html: str):
    """Verify item extraction from real Doostihaa search page fixture."""
    plugin = DoostihaaPlugin()
    items = plugin.parse_search_results(doostihaa_search_html)

    assert len(items) == 10
    first = items[0]
    assert "Batman" in first.title or "بتمن" in first.title
    assert first.page_url.startswith("https://www.doostihaa.com/post/")
    assert first.category == Category.MOVIES
    assert first.source_id == "doostihaa"
    assert first.poster_url is not None
    assert first.poster_url.startswith("https://")


def test_doostihaa_item_link_extraction(doostihaa_item_html: str):
    """Verify video download links and stream URL extraction from Doostihaa fixture."""
    plugin = DoostihaaPlugin()
    items = plugin.parse_search_results(doostihaa_item_html)
    target = items[0] if items else plugin.parse_search_results("<article><a href='https://www.doostihaa.com/post/batman.html'>Batman</a></article>")[0]

    plugin.parse_item_page(doostihaa_item_html, target)

    assert len(target.movie_variants) == 6
    qualities = [v.quality for v in target.movie_variants]
    assert "1080p" in qualities
    assert "720p" in qualities
    assert "480p" in qualities

    # Check dubbed and subbed tracks
    audio_tracks = [v.audio_track for v in target.movie_variants]
    assert "دوبله فارسی" in audio_tracks
    assert "زیرنویس فارسی" in audio_tracks

    for v in target.movie_variants:
        assert v.download_url.startswith("https://")
        assert ".mp4" in v.download_url or ".mkv" in v.download_url
        assert v.source_name == "Doostihaa"

    # Verify stream URL is selected
    assert target.stream_url is not None
    assert target.stream_url.startswith("https://")
    assert ".mp4" in target.stream_url

def test_search_parsers_survive_base_url_override(uptvs_search_html: str, doostihaa_search_html: str):
    """Parsing must not depend on the literal upstream host.

    The e2e hermetic harness rewrites fixture hosts to its local stub, so a parser
    hardcoding 'www.uptvs.com' would silently return zero items there.
    """
    cases = [
        (UpTVsPlugin(), uptvs_search_html, "https://www.uptvs.com"),
        (DoostihaaPlugin(), doostihaa_search_html, "https://www.doostihaa.com"),
    ]
    for plugin, html, host in cases:
        baseline = plugin.parse_search_results(html)
        assert baseline, f"{plugin.config.id} baseline parse yielded nothing"
        overridden = plugin.parse_search_results(html.replace(host, "http://127.0.0.1:8899"))
        assert len(overridden) == len(baseline), f"{plugin.config.id} lost items under base-url override"
