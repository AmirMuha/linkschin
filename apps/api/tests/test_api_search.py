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
# --- T074 / T075 / T076: merge breadth, failure isolation, normalization ------
#
# These drive the real /api/search endpoint with stub plugins rather than
# respx: the endpoint's own behaviour (gather, merge, order, isolate failures,
# normalize the query) is what is under test, not any single plugin's HTTP
# layer. The stub mirrors the plugin protocol the pipeline consumes.


def _stub_plugin(source_id: str, kind_full: bool = True):
    """A plugin returning exactly one item tagged with its own source id."""
    from models import SourceConfig, SourceKind

    config = SourceConfig(
        id=source_id,
        name=source_id.title(),
        category=Category.MUSIC,
        kind=SourceKind.FULL if kind_full else SourceKind.REFERENCE,
    )
    plugin = type("Stub", (), {"config": config})()

    async def search(query, client):
        return [MediaItem(
            id=f"{source_id}-hit",
            title=f"{source_id} hit",
            category=Category.MUSIC,
            source_id=source_id,
            page_url=f"https://{source_id}.test/hit",
        )]

    async def extract_links(item, client):
        return item

    plugin.search = search
    plugin.extract_links = extract_links
    return plugin


def _isolated_search(monkeypatch, plugins):
    """Point /api/search at `plugins` with cache, DB, and health tracking stubbed."""
    from web import app as web_app

    monkeypatch.setattr(web_app, "get_sources_for_category",
                        lambda cat, include_disabled=False, **kw: list(plugins))
    monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: 0)
    monkeypatch.setattr(web_app.db, "record_search_failure", lambda sid: 0)
    monkeypatch.setattr(web_app.db, "record_search_success", lambda sid: None)
    monkeypatch.setattr(web_app.db, "search", lambda *a, **k: [])
    monkeypatch.setattr(web_app.db, "upsert_items", lambda *a, **k: None)
    monkeypatch.setattr(web_app.GLOBAL_CACHE, "set", lambda *a, **k: None)
    return TestClient(web_app.app)


def test_single_search_returns_results_from_at_least_six_distinct_music_sources(monkeypatch):
    """SC-001: six or more distinct music sources in one response."""
    ids = ["musicdel", "musicsfa", "upsong", "upmusics", "musictarin", "one_rj", "popmusic"]
    api = _isolated_search(monkeypatch, [_stub_plugin(sid) for sid in ids])

    resp = api.get("/api/search", params={"q": "محسن یگانه", "category": "music", "refresh": "true"})
    assert resp.status_code == 200

    returned = {i["source_id"] for i in resp.json()["items"]}
    assert len(returned) >= 6, f"only {len(returned)} distinct sources returned: {returned}"
    assert set(ids).issubset(returned), f"missing sources: {set(ids) - returned}"


def test_full_source_results_precede_reference_results_in_one_response(monkeypatch):
    """FR-005a: every full item appears above every reference item, and the
    relative order within each group is unchanged by the presence of the other."""
    full_ids = ["musicdel", "upsong", "upmusics"]
    ref_ids = ["spotify", "aparat", "namasha"]
    # Interleave so ordering cannot be an accident of stub order.
    stubs = [_stub_plugin(f, kind_full=True) for f in full_ids]
    stubs += [_stub_plugin(r, kind_full=False) for r in ref_ids]
    api = _isolated_search(monkeypatch, stubs)

    resp = api.get("/api/search", params={"q": "test", "category": "music", "refresh": "true"})
    items = resp.json()["items"]
    kinds = [i["source_kind"] for i in items]

    assert kinds.count("full") == 3 and kinds.count("reference") == 3, kinds
    assert kinds == sorted(kinds, key=lambda k: 0 if k == "full" else 1), kinds

    # Intra-group order matches the order the plugins were registered in.
    assert [i["source_id"] for i in items[:3]] == full_ids
    assert [i["source_id"] for i in items[3:]] == ref_ids


def test_one_failing_source_does_not_block_the_others(monkeypatch):
    """FR-007 / SC-005: a raising source costs its own results, not everyone's."""
    from web import app as web_app

    def _exploding(source_id: str):
        plugin = _stub_plugin(source_id)

        async def boom(query, client):
            raise ConnectionError("upstream reset")

        plugin.search = boom
        return plugin

    api = _isolated_search(
        monkeypatch,
        [_stub_plugin("musicdel"), _exploding("brokensource"), _stub_plugin("upsong")],
    )

    resp = api.get("/api/search", params={"q": "test", "category": "music", "refresh": "true"})
    assert resp.status_code == 200
    data = resp.json()

    ids = {i["source_id"] for i in data["items"]}
    assert ids == {"musicdel", "upsong"}, f"surviving sources were lost: {ids}"
    assert "brokensource" not in ids

    warnings = data.get("warnings", [])
    assert any("brokensource" in w.lower() for w in warnings), \
        f"no warning named the failed source: {warnings}"


def test_arabic_script_query_matches_its_persian_equivalent(monkeypatch):
    """FR-006: Arabic yeh/kaf and Arabic-Indic digits normalize to the same query.

    The endpoint is called twice with equivalent spellings; both must reach the
    plugins as the identical normalized term, and the stub records what it saw.
    """
    from cache import normalize_persian_text
    from web import app as web_app

    seen: list[str] = []

    def _recording(source_id: str):
        plugin = _stub_plugin(source_id)

        async def search(query, client):
            seen.append(query.normalized_query)
            return await _stub_plugin(source_id).search(query, client)

        plugin.search = search
        return plugin

    api = _isolated_search(monkeypatch, [_recording("musicdel"), _recording("upsong")])

    persian = api.get("/api/search",
                      params={"q": "محسن یگانه ۱۲۳", "category": "music", "refresh": "true"})
    arabic = api.get("/api/search",
                     params={"q": "محسن يگانه ١٢٣", "category": "music", "refresh": "true"})

    assert persian.status_code == arabic.status_code == 200
    assert len(persian.json()["items"]) == len(arabic.json()["items"]) == 2

    # Every source saw the same normalized term for both spellings.
    assert len(seen) == 4, seen
    assert set(seen[0:2]) == set(seen[2:4]), f"normalization differs: {seen}"
    assert "123" in seen[0], f"Arabic-Indic digits not normalized: {seen[0]!r}"


def test_zwnj_and_arabic_variants_collapse_to_one_cache_key(monkeypatch):
    """FR-006: ZWNJ spacing variants must not fork the normalized query."""
    from cache import normalize_persian_text

    base = normalize_persian_text("محسن یگانه")
    assert base == normalize_persian_text("محسن‌یگانه")
    assert base == normalize_persian_text("محسن  يگانه")
    assert base == normalize_persian_text("  محسن   یگانه  ")


# --- T082 (FR-029): the HTML /search route honours the hidden-source set ---
#
# The JSON route is covered in test_source_kind.py; the Jinja route at
# web/app.py:245 accepts `sources=` but had no test at all.

def test_html_search_route_excludes_a_hidden_source(monkeypatch):
    """A source named in `sources=` must be absent from the rendered page."""
    api = _isolated_search(monkeypatch, [_stub_plugin("musicdel"), _stub_plugin("upsong")])

    both = api.get("/search", params={"q": "test", "category": "music", "refresh": "true"})
    assert both.status_code == 200
    # Assert on the card TITLE, not the source id: `upsong` also appears in the
    # source list, so an id-based check would pass even with no result rendered.
    # "upsong hit" only ever appears inside a result card.
    assert "musicdel hit" in both.text, "musicdel's result card is missing"
    assert "upsong hit" in both.text, "upsong's result card is missing"

    hidden = api.get("/search", params={
        "q": "test", "category": "music", "refresh": "true", "sources": "upsong",
    })
    assert hidden.status_code == 200, "hiding a source broke the page"
    assert "musicdel hit" in hidden.text, "the visible source disappeared too"
    assert "upsong hit" not in hidden.text, "the hidden source's result is still rendered"
    # The header count reflects the filtered set, not the full one.
    assert "1 مورد" in hidden.text, "the result count did not drop after hiding a source"


def test_html_search_route_ignores_an_unknown_hidden_source(monkeypatch):
    """A stale saved set must never break the page (search contract)."""
    api = _isolated_search(monkeypatch, [_stub_plugin("musicdel")])

    resp = api.get("/search", params={
        "q": "test", "category": "music", "refresh": "true", "sources": "no-such-source",
    })
    assert resp.status_code == 200
    assert "musicdel hit" in resp.text


def test_html_search_route_still_lists_a_hidden_source_with_its_status(monkeypatch):
    """US3/AC5: hiding removes results, NOT the source entry.

    The user must still see what they turned off, with its status, so they can
    undo it. The source list comes from the registry, not from the search, so a
    hidden source stays listed.
    """
    api = _isolated_search(monkeypatch, [_stub_plugin("musicdel"), _stub_plugin("upsong")])

    resp = api.get("/search", params={
        "q": "test", "category": "music", "refresh": "true", "sources": "upsong",
    })
    assert resp.status_code == 200
    # The result card is gone, but the source is still named in the source list.
    assert "upsong hit" not in resp.text, "the hidden source's result is still rendered"
    assert "UpSong" in resp.text, "the hidden source vanished from the source list"
