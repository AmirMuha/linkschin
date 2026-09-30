"""005: per-source parser verification against committed fixtures (T083, T084, T086).

Every movie plugin 005 adds gets a search-parsing test here, so a parser regression
fails offline instead of on the first live search after a site changes its markup.
The four fixtures are real captures of the live sites.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from http_client import SimpleResponse
from models import Category, SearchQuery, SourceConfig
from sources import get_all_source_configs, get_sources_for_category
from sources.base import is_ad_or_shortener_url, is_parked_page
from sources.movies import (
    BabakFilmPlugin,
    DigitoonPlugin,
    FilmnetPlugin,
    GapfilmPlugin,
    NamashaPlugin,
    NamavaPlugin,
    RubikaPlugin,
    TelewebionPlugin,
    UpTVsPlugin,
)
from sources.movies.aparat import AparatPlugin
from sources.movies.filimo import FilimoPlugin
from sources.movies.base_movie import extract_movie_variants_from_html

# Source id -> plugin class. Deliberately explicit rather than read from the
# registry: a test that discovers its own subject proves nothing when the registry
# is what is under test.
PARSER_BY_SOURCE: dict[str, type] = {
    "aparat": AparatPlugin,
    "babakfilm": BabakFilmPlugin,
    "digitoon": DigitoonPlugin,
    "filmnet": FilmnetPlugin,
    "filimo": FilimoPlugin,
    "gapfilm": GapfilmPlugin,
    "namasha": NamashaPlugin,
    "namava": NamavaPlugin,
    "rubika": RubikaPlugin,
    "telewebion": TelewebionPlugin,
    "uptvs": UpTVsPlugin,
}


def _config(source_id: str, **overrides) -> SourceConfig:
    """A synthetic config, so a parser test does not depend on the registry."""
    base = f"https://{source_id}.test"
    return SourceConfig(
        id=source_id,
        name=source_id.title(),
        category=Category.MOVIES,
        base_urls=overrides.pop("base_urls", [base]),
        enabled=True,
        **overrides,
    )


def _plugin(source_id: str, **overrides):
    return PARSER_BY_SOURCE[source_id](config=_config(source_id, **overrides))


class _StubClient:
    """Serves one canned response per host; anything else is a connection error."""

    def __init__(self, by_host: dict[str, str], status: int = 200):
        self.by_host = by_host
        self.status = status
        self.requested: list[str] = []

    async def get(self, url: str, headers=None, timeout=None) -> SimpleResponse:
        self.requested.append(url)
        for host, body in self.by_host.items():
            if host in url:
                return SimpleResponse(status_code=self.status, text=body, url=url)
        raise OSError(f"unreachable: {url}")

    async def aclose(self) -> None:
        pass


def _run(coro):
    return asyncio.run(coro)


def _reset_breaker() -> None:
    from sources.health import GLOBAL_BREAKER

    GLOBAL_BREAKER.reset()


# --- Every parser 005 adds actually parses (T084, FR-025, SC-010) -------------

# One card, in the shape each parser accepts. A parser that constrains its own URL
# shape (ITEM_URL_SUBSTRING) gets a link that satisfies it, so a failure here means
# the parser cannot read a result card at all -- not that the fixture was wrong.
_RESULT_HTML = """
<html><body>
  <div class="post-item"><a href="{href}">فیلم یک</a></div>
</body></html>
"""
_CARD_PATH = {
    "filmnet": "/contents/ab12/film-yek",
    "namasha": "/v/ab12cd34",
    "uptvs": "/contents/film-yek-2026.html",
}
_DEFAULT_CARD_PATH = "/post/one"


def _card(source_id: str) -> str:
    return _RESULT_HTML.format(href=_CARD_PATH.get(source_id, _DEFAULT_CARD_PATH))


def _card_page(source_id: str) -> str:
    return f"https://{source_id}.test{_CARD_PATH.get(source_id, _DEFAULT_CARD_PATH)}"


# uptvs and aparat are bespoke (a card-splitter and a JSON reader), so the shared
# card contract does not describe them. They are covered against real fixtures below.
_SHARED_CARD_PARSERS = sorted(set(PARSER_BY_SOURCE) - {"uptvs", "aparat"})


@pytest.mark.parametrize("source_id", _SHARED_CARD_PARSERS)
def test_each_parser_reads_a_result_card(source_id):
    """The minimum contract: one card in, one addressable MediaItem out.

    A parser that returns nothing here is the FR-023 "registers but returns
    nothing" defect, and it is the reason 19 parsers shipped with no test.
    """
    items = _plugin(source_id).parse_search_results(_card(source_id))

    assert len(items) == 1, f"{source_id} yielded {len(items)} items from one card"
    assert items[0].title == "فیلم یک"
    assert items[0].page_url == _card_page(source_id)


@pytest.mark.parametrize("source_id", _SHARED_CARD_PARSERS)
def test_no_parser_hardcodes_its_own_host(source_id):
    """FR-012/FR-014: an address change is configuration alone.

    A regex carrying the live domain would keep matching nothing, silently, after
    the domain moves -- the exact failure the address list exists to prevent.
    Asserted by parsing the same card through a mirror address.
    """
    mirror = _plugin(source_id, base_urls=["https://mirror.test"]).parse_search_results(
        _card(source_id)
    )

    assert mirror, f"{source_id} produced nothing to compare against"
    assert all("mirror.test" in i.page_url for i in mirror), (
        f"{source_id} ignored the configured address: {[i.page_url for i in mirror]}"
    )


def test_uptvs_reads_a_result_card_through_the_configured_address(uptvs_search_html):
    """uptvs is a bespoke card splitter, so it is checked against real markup.

    The fixture's hrefs are absolute uptvs.com links, so they must survive unchanged:
    a result page is a link the user follows, and rewriting it to the configured
    address would send them somewhere the page never pointed.
    """
    items = _plugin("uptvs").parse_search_results(uptvs_search_html)

    assert items, "uptvs produced no items from its own fixture"
    assert all(i.page_url.startswith("https://www.uptvs.com/contents/") for i in items), (
        f"uptvs mis-parsed its own card markup: {[i.page_url for i in items][:2]}"
    )


@pytest.mark.parametrize("source_id", sorted(PARSER_BY_SOURCE))
def test_a_relative_card_link_resolves_to_the_configured_address(source_id):
    """FR-012a: a site-relative href resolves against the address that served it.

    Each parser gets a card in its own required shape -- uptvs needs a content-thumb
    block with a title attribute, aparat reads JSON -- because the property under
    test is address resolution, not card detection. A parser that only ever saw
    absolute hrefs would pass every other test here and fail this one.
    """
    if source_id == "aparat":
        payload = json.dumps(
            {"included": [{"type": "Video", "attributes": {"title": {"text": "فیلم یک"}, "uid": "ab12"}}]}
        )
        items = _plugin(source_id, base_urls=["https://mirror.test"]).parse_search_results(payload)
        assert len(items) == 1, "aparat dropped its own API payload"
        assert items[0].page_url == "https://mirror.test/v/ab12"
        return

    path = _CARD_PATH.get(source_id, _DEFAULT_CARD_PATH)
    if source_id == "uptvs":
        html = f'<div class="content-thumb"><a href="{path}" title="فیلم یک">x</a></div>'
    else:
        html = _RESULT_HTML.format(href=path)

    items = _plugin(source_id, base_urls=["https://mirror.test"]).parse_search_results(html)

    assert len(items) == 1, f"{source_id} dropped a site-relative result link"
    assert items[0].page_url == f"https://mirror.test{path}"


def test_search_url_follows_the_configured_address():
    plugin = _plugin("filmnet", base_urls=["https://mirror.test"])
    assert plugin.build_search_url("batman").startswith("https://mirror.test/")


# --- Fixture-backed parsing: the four captured sites (T084) ------------------


def test_aparat_json_payload_yields_watch_destinations(aparat_search_html):
    """Aparat serves search client-side; the API JSON is the only real source.

    Its fixture is a JSON API payload, not HTML, so it cannot share the card test
    above. Every entry is a video page and must be a watch destination.
    """
    items = _plugin("aparat").parse_search_results(aparat_search_html)

    assert items, "aparat fixture produced no items"
    assert all(i.page_url.startswith("https://") for i in items)
    assert all(i.title.strip() for i in items)
    for item in items:
        assert item.watch_url, f"{item.id} carries no watch destination"
        assert not item.movie_variants, "a video host must not yield a download"


def test_aparat_ignores_a_non_json_response(aparat_search_html):
    """FR-019: a changed response shape must not raise, it must yield nothing."""
    assert _plugin("aparat").parse_search_results(aparat_search_html) is not None
    assert _plugin("aparat").parse_search_results("<html>rate limited</html>") == []


def test_filmnet_fixture_yields_watch_destinations(filmnet_search_html):
    """FR-006: filmnet is subscription-only, so results carry a watch page."""
    items = _plugin("filmnet", provides_downloads=False).parse_search_results(
        filmnet_search_html
    )

    assert items, "filmnet fixture produced no items"
    assert all(i.watch_url for i in items), "a watch-only source lost its destination"
    assert not any(i.movie_variants or i.stream_url for i in items)


def test_filmnet_titles_carry_no_inlined_css(filmnet_search_html):
    """filmnet inlines an emotion stylesheet per card; strip-tags must not yield CSS.

    The base parser removes <style> blocks, but a CSS text node that is not wrapped
    in one still lands in a title, so this asserts the outcome rather than the path.
    """
    for item in _plugin("filmnet").parse_search_results(filmnet_search_html):
        assert not re.search(r"[.#][\w-]+\s*\{[^}]*:", item.title), (
            f"CSS leaked into a filmnet title: {item.title[:80]!r}"
        )


def test_filmnet_drops_the_genre_filter_as_a_result(filmnet_search_html):
    """/contents?types=series is a filter link, not a release.

    Without this the first screen reads "فیلم", "سریال", "دسته‌بندی" as titles.
    """
    items = _plugin("filmnet").parse_search_results(filmnet_search_html)

    assert items
    assert all("/contents/" in i.page_url for i in items), (
        f"a non-content link survived: {[i.page_url for i in items if '/contents/' not in i.page_url][:3]}"
    )


def test_namasha_keeps_video_pages_and_drops_chrome(namasha_search_html):
    """namasha serves account/upload chrome beside the results.

    The chrome rows (/upload, /login) must not become results; /v/<hash> is content.
    """
    items = _plugin("namasha", provides_downloads=False).parse_search_results(
        namasha_search_html
    )

    assert items, "namasha fixture produced no items"
    assert all("/v/" in i.page_url for i in items), (
        f"a non-video link survived: {[i.page_url for i in items if '/v/' not in i.page_url][:3]}"
    )
    assert all(i.watch_url for i in items)


def test_rubika_search_page_carries_no_release_cards(rubika_search_html):
    """rubika.ir serves a navigation-only response for a search query.

    Asserted as zero results rather than skipped: the fixture is on disk and
    loaded, so if the site later starts serving cards this fails and the parser
    gets a real selector instead of staying untested against live markup.
    """
    assert not is_parked_page(rubika_search_html), "fixture is a parked page, not search chrome"
    assert _plugin("rubika", provides_downloads=False).parse_search_results(
        rubika_search_html
    ) == []


# --- Address fallback (FR-012a/FR-012b, T078) --------------------------------


@pytest.fixture(autouse=True)
def _clean_breaker():
    """Reset the process-global breaker around every test that touches it.

    Kept as an autouse fixture, but each test below ALSO resets inline: the
    zero-dependency runner in tests/run_all.py does not execute fixtures, so a
    test that depended on this alone passed under pytest and failed there. The
    inline reset is the one that actually runs in both.
    """
    from sources.health import GLOBAL_BREAKER

    GLOBAL_BREAKER.reset()
    yield
    GLOBAL_BREAKER.reset()


def test_unreachable_primary_falls_through_to_the_next_address():
    """FR-012a: the second configured address serves the request."""
    _reset_breaker()
    plugin = _plugin("filmnet", base_urls=["https://dead.test", "https://live.test"])
    client = _StubClient({"live.test": _card("filmnet")})

    items = _run(plugin.search(SearchQuery("batman", "batman", Category.MOVIES), client))

    assert items, "no items after falling through to the fallback address"
    assert plugin.active_address == "https://live.test"
    assert len(client.requested) == 2, "the dead address was never tried"


def test_a_breaker_tripped_address_is_not_retried():
    """FR-012b: a dead address costs one attempt, not one attempt per search."""
    from sources.health import GLOBAL_BREAKER

    _reset_breaker()
    for _ in range(GLOBAL_BREAKER.threshold):
        GLOBAL_BREAKER.record_failure("https://dead.test")
    plugin = _plugin("filmnet", base_urls=["https://dead.test", "https://live.test"])
    client = _StubClient({"live.test": _card("filmnet")})

    _run(plugin.search(SearchQuery("batman", "batman", Category.MOVIES), client))

    assert all("dead.test" not in u for u in client.requested), (
        f"a tripped address was retried: {client.requested}"
    )
    assert len(client.requested) == 1
    _reset_breaker()  # leave the process-global breaker as found


def test_relative_links_resolve_against_the_serving_address():
    """FR-012a: links absolutise against the host that actually answered."""
    _reset_breaker()
    plugin = _plugin("rubika", base_urls=["https://dead.test", "https://live.test"])
    client = _StubClient({"live.test": _card("rubika")})

    items = _run(plugin.search(SearchQuery("batman", "batman", Category.MOVIES), client))

    assert items[0].page_url == "https://live.test/post/one"


def test_every_address_down_yields_no_results_rather_than_raising():
    plugin = _plugin("filmnet", base_urls=["https://dead.test", "https://gone.test"])
    client = _StubClient({})

    assert _run(plugin.search(SearchQuery("batman", "batman", Category.MOVIES), client)) == []


# --- Discard rules (FR-016, SC-006, T086, T082) ------------------------------


def test_parked_page_moves_on_to_the_next_address():
    """A parked page answers 200; it is not a result set."""
    parked = "<html><body><h1>This domain is for sale</h1><a href='/lander'>x</a></body></html>"
    assert is_parked_page(parked), "the parked fixture is not actually parked"

    _reset_breaker()
    plugin = _plugin("filmnet", base_urls=["https://parked.test", "https://live.test"])
    client = _StubClient({"parked.test": parked, "live.test": _card("filmnet")})

    items = _run(plugin.search(SearchQuery("batman", "batman", Category.MOVIES), client))

    assert items
    assert plugin.active_address == "https://live.test", "a parked page was parsed as results"


def test_parked_page_is_never_the_only_address_yielded():
    plugin = _plugin("uptvs", base_urls=["https://parked.test"])
    parked = "<html><body>This domain is for sale</body></html>"
    client = _StubClient({"parked.test": parked})

    assert _run(plugin.search(SearchQuery("batman", "batman", Category.MOVIES), client)) == []


def test_ad_shortener_downloads_are_discarded():
    """FR-016: a shortener is an ad hop, not a file the user can fetch."""
    html = """
    <a href="https://adf.ly/abc">movie 1080p x264</a>
    <a href="https://cdn.host.test/movie.1080p.x264.mkv">movie 720p x264</a>
    """
    variants = extract_movie_variants_from_html(html, "Test", "https://cdn.host.test")

    assert [v.download_url for v in variants] == [
        "https://cdn.host.test/movie.1080p.x264.mkv"
    ]


@pytest.mark.parametrize("source_id", ["filmnet", "namasha", "rubika"])
def test_no_result_carries_an_ad_or_shortener_url(source_id):
    """FR-016 at the result level, for every shared parser, not just uptvs."""
    html = (
        '<div class="post-item"><a href="https://adf.ly/abc">فیلم تست</a></div>'
        f'<div class="post-item"><a href="{_CARD_PATH.get(source_id, _DEFAULT_CARD_PATH)}">فیلم واقعی</a></div>'
    )
    for item in _plugin(source_id).parse_search_results(html):
        assert not is_ad_or_shortener_url(item.page_url), (
            f"{source_id} kept an ad link as a result: {item.page_url}"
        )


# --- Registry wiring (T077, T085) --------------------------------------------


def test_every_enabled_profile_resolves_to_a_plugin():
    """FR-023: a profile that registers but instantiates nothing is a dead entry."""
    from sources.profiles import load_profiles

    live = {p.config.id for p in get_sources_for_category(Category.MOVIES)}

    dead = [p.id for p in load_profiles() if p.enabled and p.category is Category.MOVIES and p.id not in live]
    assert not dead, f"profiles with no plugin: {dead}"


def test_a_profile_naming_an_unimplemented_parser_is_rejected(tmp_path: Path):
    """FR-022/FR-023: validation resolves against the registry, not a hand-kept list."""
    from sources.profiles import load_profiles

    path = tmp_path / "profiles.yaml"
    path.write_text(
        "sources:\n"
        "  - id: ghost\n"
        "    name: Ghost\n"
        "    category: movies\n"
        "    parser: no_such_parser\n"
        "    addresses: ['https://ghost.test']\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unknown parser"):
        load_profiles(path)


# --- Source filtering (FR-005) and aliases (FR-021, T083) -------------------


def test_downloads_only_filter_drops_watch_destinations():
    """FR-005: the default Movies toggle excludes subscription sources."""
    all_ids = {p.config.id for p in get_sources_for_category(Category.MOVIES)}
    download_ids = {p.config.id for p in get_sources_for_category(Category.MOVIES, downloads_only=True)}

    assert download_ids < all_ids, "downloads_only removed nothing"
    assert {"filimo", "namava", "filmnet"} <= all_ids - download_ids
    assert all(
        next(c for c in get_all_source_configs() if c.category is Category.MOVIES and c.id == i)
        .provides_downloads
        for i in download_ids
    )


def test_an_alias_is_never_instantiated_as_its_own_stream(monkeypatch):
    """FR-021 / T083: an alias is listed but must not open a second result stream.

    Without the is_alias skip in get_sources_for_category, the same movie is
    scraped twice and every title appears twice in the result grid.
    """
    import sources

    real = sources.get_all_source_configs()
    target = next(c for c in real if c.category is Category.MOVIES and c.id == "filimo")
    alias = replace(target, id="filimo_mirror", name="Filimo Mirror", duplicate_of="filimo")
    assert alias.is_alias, "the alias fixture is not actually an alias"

    monkeypatch.setattr(sources, "_profile_configs", lambda: real + [alias])

    live = {p.config.id for p in sources.get_sources_for_category(Category.MOVIES)}
    listed = {c.id for c in sources.get_all_source_configs() if c.category is Category.MOVIES}

    assert "filimo" in live, "the aliased-away source stopped working"
    assert "filimo_mirror" in listed, "an alias must still be discoverable in the listing"
    assert "filimo_mirror" not in live, "an aliased source opened a second result stream"


# --- T079: bounded redirects -------------------------------------------------


def test_redirect_budget_is_finite_and_non_zero():
    from http_client import MAX_REDIRECTS, RedirectLoopError

    assert 0 < MAX_REDIRECTS < 50, "the budget is either unbounded or unusably small"
    assert issubclass(RedirectLoopError, RuntimeError)


# --- FR-005 scope plumbing end to end ----------------------------------------


def test_scope_param_selects_a_different_plugin_set(monkeypatch):
    """The two scopes are different scraper sets, not the same set re-filtered.

    Asserted on what _collect_items asks the registry for, so a scope that is
    accepted but ignored fails here rather than showing up as a toggle that
    changes nothing.
    """
    import asyncio

    from models import MediaItem
    from web import app as web_app

    seen: list[bool] = []

    def _record(category, include_disabled=False, exclude_ids=None, downloads_only=False):
        seen.append(downloads_only)
        return []

    monkeypatch.setattr(web_app, "get_sources_for_category", _record)
    monkeypatch.setattr(web_app.db, "upsert_items", lambda items: None)
    monkeypatch.setattr(web_app.GLOBAL_CACHE, "clear", lambda: None)

    for scope, expect in (("downloads", True), ("all", False)):
        seen.clear()
        asyncio.run(
            web_app._collect_items(
                Category.MOVIES, "batman", "batman", refresh=True, scope=scope
            )
        )
        assert seen == [expect], f"scope={scope} asked for downloads_only={seen}"


def test_scope_responses_do_not_share_a_cache_entry():
    """A warm downloads-only cache must not answer an all-sources search.

    Two different result sets under one key is the bug that makes the toggle look
    broken: whichever scope ran first would serve both.
    """
    from models import MediaItem
    from cache import GLOBAL_CACHE

    def _item(source_id: str) -> MediaItem:
        return MediaItem(
            id=f"movies-{source_id}",
            title=f"title {source_id}",
            category=Category.MOVIES,
            source_id=source_id,
            page_url=f"https://{source_id}.test/one",
        )

    GLOBAL_CACHE.clear()
    try:
        GLOBAL_CACHE.set(Category.MOVIES, "batman", [_item("uptvs")], "downloads")
        GLOBAL_CACHE.set(Category.MOVIES, "batman", [_item("filimo")], "all")

        assert [i.source_id for i in GLOBAL_CACHE.get(Category.MOVIES, "batman", "downloads")] == ["uptvs"]
        assert [i.source_id for i in GLOBAL_CACHE.get(Category.MOVIES, "batman", "all")] == ["filimo"]
    finally:
        GLOBAL_CACHE.clear()
