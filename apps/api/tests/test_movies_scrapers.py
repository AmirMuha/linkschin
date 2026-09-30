"""Unit and fixture parser tests for movie scraper plugins."""

from __future__ import annotations

from models import Category
from sources.base import is_host, parse_codec, parse_quality
from sources.movies.doostihaa import DoostihaaPlugin
from sources.movies.uptvs import UpTVsPlugin


def test_uptvs_search_parsing(uptvs_search_html: str):
    """Verify item extraction from real UpTVs search page fixture."""
    plugin = UpTVsPlugin()
    items = plugin.parse_search_results(uptvs_search_html)

    # Exactly the 15 rendered cards: the page also ships a `uas_search_modal` widget
    # whose hardcoded "suggested categories" links are not results for any query.
    assert len(items) == 15
    assert not ({"سیلو", "باب اسفنجی", "From"} & {i.title for i in items})
    first = items[0]
    assert "بتمن" in first.title
    assert first.page_url.startswith("https://www.uptvs.com/contents/")
    assert first.category == Category.MOVIES
    assert first.source_id == "uptvs"
    # The thumbnail lives in the same card block, so search can populate it directly.
    assert all(i.poster_url and i.poster_url.startswith("https://") for i in items)


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


def test_doostihaa_flags_login_walled_links(doostihaa_item_html: str):
    """hub.irdanlod.ir answers 200 with an HTML login page, not the file.

    Those links must be labelled, not offered as a plain download. Matching is on
    the host, because a URL starts with its scheme - a prefix test silently never
    matches and every row ends up flagged 'direct'.
    """
    plugin = DoostihaaPlugin()
    item = plugin.parse_search_results(
        "<article><a href='https://www.doostihaa.com/post/spider.html'>Spider</a></article>"
    )[0]
    plugin.parse_item_page(doostihaa_item_html, item)

    assert item.movie_variants, "fixture must yield variants"
    walled = [v for v in item.movie_variants if "hub.irdanlod.ir" in v.download_url]
    assert walled, "fixture must contain hub.irdanlod.ir links"
    assert all(v.access == "needs_login" for v in walled), \
        f"got {sorted({v.access for v in walled})}"


def test_is_host_matches_on_host_not_prefix():
    """Regression: `url.startswith(domain)` is never true for an absolute URL."""
    assert is_host("https://hub.irdanlod.ir/a/b.mkv", "hub.irdanlod.ir") is True
    assert is_host("https://HUB.IRDANLOD.IR/a.mkv", "hub.irdanlod.ir") is True
    assert is_host("https://cdn.hub.irdanlod.ir/a.mkv", "hub.irdanlod.ir") is True
    assert is_host("https://cdn.uptvs.com/a.mp4", "hub.irdanlod.ir") is False
    assert is_host("https://hub.irdanlod.ir.evil.com/a.mkv", "hub.irdanlod.ir") is False
    assert is_host("", "hub.irdanlod.ir") is False


def test_movies_do_not_fabricate_quality_or_codec():
    """A filename with no resolution must yield "", not a guessed 1080p/x264."""
    plugin = DoostihaaPlugin()
    item = plugin.parse_search_results(
        "<article><a href='https://www.doostihaa.com/post/x.html'>X</a></article>"
    )[0]
    plugin.parse_item_page(
        '<a href="https://cdn.example.com/movie.farsi.mkv">لینک</a>', item
    )
    v = item.movie_variants[0]
    assert v.quality == "", "resolution was never stated by the source"
    assert v.codec == "", "codec was never stated by the source"


def test_parse_quality_reads_positional_cdn_names():
    """`3080511-0-720.mp4` is a 720p stream; the old pattern called it 1080p."""
    assert parse_quality("https://uptv.upera.tv/3080511-0-720.mp4") == "720p"
    assert parse_quality("https://uptv.upera.tv/3080511-0-1080.mp4") == "1080p"
    assert parse_quality("Batman_2026_720p_UPTV.co.mp4") == "720p"
    assert parse_quality("spiderman moghavemat_UPTV.co.mp4") == ""
    assert parse_codec("movie.x265.mkv") == "x265"
    assert parse_codec("spiderman moghavemat_UPTV.co.mp4") == ""

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
