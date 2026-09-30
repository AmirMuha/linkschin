"""Unit and fixture parser tests for movie scraper plugins."""

from __future__ import annotations

from models import Category, CensorshipStatus, MovieDownloadVariant, SourceAccessTier
from sources.movies.doostihaa import DoostihaaPlugin, derive_censorship_status
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

def test_uptvs_scrapes_imdb_from_cards(uptvs_search_html: str):
    """Each UpTVs card carries 'N /10' after its ficon-imdb marker."""
    items = UpTVsPlugin().parse_search_results(uptvs_search_html)
    rated = [i for i in items if i.imdb_rating is not None]
    assert rated, "no UpTVs item extracted an IMDb score"
    assert items[0].imdb_rating == 7.9
    for i in rated:
        assert 0.0 <= i.imdb_rating <= 10.0

def test_uptvs_never_invents_a_censorship_claim(uptvs_item_html: str):
    """No censorship marker in the fixture means unspecified, never 'uncensored'."""
    plugin = UpTVsPlugin()
    target = plugin.parse_search_results(uptvs_item_html)[0]
    plugin.parse_item_page(uptvs_item_html, target)
    assert target.censorship_status is CensorshipStatus.UNSPECIFIED
    assert all(v.is_censored is None for v in target.movie_variants)

def test_doostihaa_scrapes_imdb_from_encoded_body(doostihaa_search_html: str):
    """IMDb lives in HTML-entity-encoded body text, so it needs html.unescape first."""
    items = DoostihaaPlugin().parse_search_results(doostihaa_search_html)
    assert items[0].imdb_rating == 7.9
    assert sum(1 for i in items if i.imdb_rating is not None) == len(items)

def test_doostihaa_reads_page_level_censorship_tag(doostihaa_item_html: str):
    """The item page tags the release 'نسخه سانسور شده', so it is CENSORED, not unspecified."""
    plugin = DoostihaaPlugin()
    target = plugin.parse_search_results(doostihaa_item_html)[0]
    plugin.parse_item_page(doostihaa_item_html, target)
    assert target.censorship_status is CensorshipStatus.CENSORED
    assert all(v.is_censored is True for v in target.movie_variants)

def test_movie_items_carry_their_source_tier(uptvs_search_html: str, doostihaa_search_html: str):
    """Tier comes from registry config, not from page markup."""
    uptvs = UpTVsPlugin().parse_search_results(uptvs_search_html)[0]
    doosti = DoostihaaPlugin().parse_search_results(doostihaa_search_html)[0]
    assert uptvs.source_access_tier is SourceAccessTier.FREE
    assert doosti.source_access_tier is SourceAccessTier.FREEMIUM

def test_derive_censorship_status_rolls_up_variant_flags():
    """Mixed flags mean a mixed release; no flags mean unknown, never assumed."""
    def v(flag):
        return MovieDownloadVariant(id=str(flag), quality="720p", codec="x264",
                                    audio_track="dub", download_url="https://c/a.mp4",
                                    is_censored=flag)
    assert derive_censorship_status([]) is CensorshipStatus.UNSPECIFIED
    assert derive_censorship_status([v(None)]) is CensorshipStatus.UNSPECIFIED
    assert derive_censorship_status([v(True), v(True)]) is CensorshipStatus.CENSORED
    assert derive_censorship_status([v(False), v(False)]) is CensorshipStatus.UNCENSORED
    assert derive_censorship_status([v(True), v(False)]) is CensorshipStatus.MIXED

def test_imdb_jsonld_aggregate_rating_is_never_used(uptvs_item_html: str, doostihaa_item_html: str):
    """JSON-LD aggregateRating is a site-user score (0-100 / 1-5), not an IMDb rating."""
    assert UpTVsPlugin._parse_imdb(uptvs_item_html) is None
    assert DoostihaaPlugin._parse_imdb(doostihaa_item_html) is None

def test_imdb_rejects_out_of_range_scores():
    """A parsed score outside 0-10 resolves to None instead of rendering a bogus badge."""
    assert DoostihaaPlugin._parse_imdb("امتیاز: 83") is None
    assert DoostihaaPlugin._parse_imdb("امتیاز: 6.5") == 6.5
    assert UpTVsPlugin._parse_imdb('<i class="ficon-imdb"></i> 55 /10') is None
    assert UpTVsPlugin._parse_imdb('<i class="ficon-imdb"></i> 7.9 /10') == 7.9
    assert UpTVsPlugin._parse_imdb("no marker here") is None

def test_movie_item_ids_are_unique_for_persian_titles(uptvs_search_html: str, doostihaa_search_html: str):
    """Persian titles reduce to '' under [^a-zA-Z0-9], so ids need a URL-derived suffix.

    Duplicate ids make React drop a card and collide in the SQLite primary key, so two
    distinct releases would silently disappear from the grid.
    """
    for plugin, html in ((UpTVsPlugin(), uptvs_search_html), (DoostihaaPlugin(), doostihaa_search_html)):
        items = plugin.parse_search_results(html)
        ids = [i.id for i in items]
        assert len(ids) == len(set(ids)), f"{plugin.config.id} produced duplicate ids"
        # Deterministic: re-parsing the same page yields the same ids.
        assert ids == [i.id for i in plugin.parse_search_results(html)]

def test_uptvs_unrated_card_does_not_borrow_a_neighbours_score(uptvs_search_html: str):
    """A card's rating must come from its own markup, not the next card along.

    A fixed character window would let an unrated card adopt the following
    card's score and display a rating the page never stated for it.
    """
    import re as _re
    cards = _re.split(r'<div class="content-thumb mb-20">', uptvs_search_html)[1:]
    target = next(c for c in cards if _re.search(r'ficon-imdb', c))
    stripped = _re.sub(
        r'(ficon-imdb[^>]*>\s*</i>\s*)[0-9]+(?:\.[0-9]+)?(\s*/\s*10)', r'\1\2', target, count=1
    )
    without = uptvs_search_html.replace(target, stripped, 1)

    before = {i.title: i.imdb_rating for i in UpTVsPlugin().parse_search_results(uptvs_search_html)}
    after = {i.title: i.imdb_rating for i in UpTVsPlugin().parse_search_results(without)}

    assert before != after, "fixture mutation did not remove any score"
    became_unrated = [t for t in before if before[t] != after[t]]
    assert len(became_unrated) == 1, f"expected exactly one card to lose its score, got {became_unrated}"
    assert after[became_unrated[0]] is None, "card must fall back to unrated, never a neighbour's score"
