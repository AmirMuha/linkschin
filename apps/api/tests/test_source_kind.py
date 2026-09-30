"""SourceKind, health-state, and result-ordering tests (FR-005a, FR-018a, T017-T020)."""

from __future__ import annotations

import pytest

import db
from models import Category, MediaItem, SourceConfig, SourceKind
from sources import DEFAULT_CONFIGS, get_all_source_configs


def _item(source_id: str, item_id: str) -> MediaItem:
    return MediaItem(
        id=item_id,
        title=item_id,
        category=Category.MUSIC,
        source_id=source_id,
        page_url=f"https://{source_id}.test/{item_id}",
    )


def test_source_kind_defaults_to_full():
    """A SourceConfig built with no kind is FULL, so pre-006 call sites are unchanged."""
    assert SourceConfig(id="x", name="X", category=Category.MUSIC).kind is SourceKind.FULL


def test_is_reference_reads_as_intent():
    ref = SourceConfig(id="x", name="X", category=Category.MUSIC, kind=SourceKind.REFERENCE)
    assert ref.is_reference is True
    assert ref.is_reference  # truthy in a plain conditional
    full = SourceConfig(id="y", name="Y", category=Category.MUSIC)
    assert full.is_reference is False


def test_every_registered_config_declares_a_kind():
    for cfg in DEFAULT_CONFIGS:
        assert isinstance(cfg.kind, SourceKind)


# --- Result ordering and kind stamping (FR-005a / T012 / T017 / T018) --------


def test_finalize_stamps_source_kind_attribute():
    """Templates read item.source_kind, so it must be an attribute, not only JSON."""
    from web.app import _finalize

    items = [_item("spotify", "r1"), _item("musicdel", "f1")]
    ordered = _finalize(items)

    assert [i.source_kind for i in ordered] == ["full", "reference"]
    assert [i.id for i in ordered] == ["f1", "r1"]


def test_source_kind_reaches_the_json_payload():
    """React gets the field from asdict() off the same stamped object (FR-005b)."""
    from dataclasses import asdict

    from web.app import _finalize

    payload = asdict(_finalize([_item("namasha", "r1")])[0])
    assert payload["source_kind"] == "reference"


def test_unknown_source_id_defaults_to_full():
    """An unregistered id is treated as full, never silently demoted to the tail."""
    from web.app import _finalize

    ordered = _finalize([_item("mystery", "m1"), _item("spotify", "r1")])
    assert [i.id for i in ordered] == ["m1", "r1"]
    assert ordered[0].source_kind == "full"


def test_finalize_is_stable_within_each_group():
    """Relevance order inside a group must survive the sort exactly."""
    from web.app import _finalize

    items = [
        _item("musicdel", "f1"),
        _item("spotify", "r1"),
        _item("popmusic", "f2"),
        _item("youtube_music", "r2"),
        _item("nex1music", "f3"),
        _item("aparat", "r3"),
    ]
    ordered = _finalize(items)

    assert [i.id for i in ordered] == ["f1", "f2", "f3", "r1", "r2", "r3"]


def test_ordering_agrees_with_the_registry_reference_set():
    """_finalize's stamp matches what the registry declares as REFERENCE, per id."""
    from web.app import _finalize

    reference_ids = {c.id for c in get_all_source_configs() if c.kind is SourceKind.REFERENCE}
    assert reference_ids, "expected reference sources in the registry"

    ordered = _finalize([_item(sid, f"i_{sid}") for sid in sorted(reference_ids)])
    assert all(i.source_kind == "reference" for i in ordered)

    full = _finalize([_item("one_rj", "f1"), _item("popmusic", "f2")])
    assert all(i.source_kind == "full" for i in full)


def test_media_item_defaults_to_full_kind():
    """Pre-006 constructor sites and the DB rehydrate path keep working (FR-028)."""
    assert _item("popmusic", "p1").source_kind == "full"


# --- Health state (FR-018a / T019 / T020) ------------------------------------


def test_failure_counter_increments_and_success_resets(tmp_path):
    db_path = tmp_path / "crawl.db"

    assert db.get_consecutive_failures("musicdel", db_path) == 0

    assert db.record_search_failure("musicdel", db_path) == 1
    assert db.record_search_failure("musicdel", db_path) == 2
    assert db.get_consecutive_failures("musicdel", db_path) == 2

    db.record_search_success("musicdel", db_path)
    assert db.get_consecutive_failures("musicdel", db_path) == 0


def test_counter_is_per_source(tmp_path):
    db_path = tmp_path / "crawl.db"
    db.record_search_failure("musicdel", db_path)
    db.record_search_failure("musicdel", db_path)

    assert db.get_consecutive_failures("popmusic", db_path) == 0


def test_third_failure_marks_degraded_but_first_two_stay_active(tmp_path, monkeypatch):
    """1-2 failures leave the source active; the 3rd crosses into degraded."""
    from web import app as web_app

    monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: 2)
    cfg = next(c for c in get_all_source_configs() if c.id == "musicdel")
    assert web_app._source_status(cfg) == "active"

    monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: 3)
    assert web_app._source_status(cfg) == "degraded"

    monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: 4)
    assert web_app._source_status(cfg) == "degraded"


def test_disabled_source_is_inactive_regardless_of_failure_count(tmp_path, monkeypatch):
    from web import app as web_app

    monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: 0)
    cfg = next(c for c in get_all_source_configs() if c.id == "radiojavan")
    assert cfg.enabled is False
    assert web_app._source_status(cfg) == "inactive"


def test_success_after_degraded_returns_source_to_active(tmp_path, monkeypatch):
    """The documented recovery path: any success resets the counter to 0."""
    from web import app as web_app

    db_path = tmp_path / "crawl.db"
    for _ in range(3):
        db.record_search_failure("musicdel", db_path)
    assert db.get_consecutive_failures("musicdel", db_path) == 3

    db.record_search_success("musicdel", db_path)
    assert db.get_consecutive_failures("musicdel", db_path) == 0

    monkeypatch.setattr(web_app.db, "get_consecutive_failures",
                        lambda sid: db.get_consecutive_failures(sid, db_path))
    cfg = next(c for c in get_all_source_configs() if c.id == "musicdel")
    assert web_app._source_status(cfg) == "active"


def test_degraded_sources_are_excluded_from_search(tmp_path, monkeypatch):
    """FR-019: a source at the threshold is not queried."""
    from web import app as web_app
    from sources import get_sources_for_category

    db_path = tmp_path / "crawl.db"
    for _ in range(web_app.DEGRADED_THRESHOLD):
        db.record_search_failure("musicdel", db_path)

    counts = {"musicdel": db.get_consecutive_failures("musicdel", db_path)}
    monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: counts.get(sid, 0))

    degraded = web_app._degraded_ids()
    assert "musicdel" in degraded

    kept = [p for p in get_sources_for_category(Category.MUSIC) if p.config.id not in degraded]
    assert "musicdel" not in {p.config.id for p in kept}
    assert "popmusic" in {p.config.id for p in kept}


# --- Registry filtering (T008) -----------------------------------------------


def _ids(**kwargs) -> set[str]:
    from sources import get_sources_for_category

    return {p.config.id for p in get_sources_for_category(Category.MUSIC, **kwargs)}


def test_exclude_ids_defaults_to_unaffected():
    baseline = _ids()
    assert baseline, "expected music plugins"
    assert _ids(exclude_ids=None) == baseline
    assert _ids(exclude_ids=set()) == baseline


def test_exclude_ids_removes_only_the_named_source():
    filtered = _ids(exclude_ids={"spotify"})
    assert "spotify" not in filtered
    assert "musicdel" in filtered
    assert len(filtered) == len(_ids()) - 1

# --- Endpoint wiring (T037/T038): the sources= param must reach _collect_items.
# Registry-level tests above cannot catch an unwired endpoint — these can.

class _StubPlugin:
    """Minimal plugin: every stub returns one item tagged with its own id."""

    def __init__(self, source_id: str):
        self.config = SourceConfig(id=source_id, name=source_id.title(), category=Category.MUSIC)

    async def search(self, query, client):
        return [_item(self.config.id, f"{self.config.id}-hit")]

    async def extract_links(self, item, client):
        return item


def _stub_music(monkeypatch, source_ids):
    from web import app as web_app
    plugins = [_StubPlugin(sid) for sid in source_ids]
    monkeypatch.setattr(web_app, "get_sources_for_category",
                        lambda cat, include_disabled=False, **kw: list(plugins))
    monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: 0)
    monkeypatch.setattr(web_app.db, "record_search_failure", lambda sid: 0)
    monkeypatch.setattr(web_app.db, "record_search_success", lambda sid: None)
    monkeypatch.setattr(web_app.db, "search", lambda *a, **k: [])
    monkeypatch.setattr(web_app.GLOBAL_CACHE, "set", lambda *a, **k: None)
    return web_app


def test_api_search_sources_param_excludes_source(tmp_path, monkeypatch):
    """FR-029/030: sources=<id> drops that source from the response only for that request."""
    from fastapi.testclient import TestClient
    api = TestClient(_stub_music(monkeypatch, ["musicdel", "upsong"]).app)

    both = api.get("/api/search", params={"q": "test", "category": "music", "refresh": "true"})
    assert both.status_code == 200
    ids = {i["source_id"] for i in both.json()["items"]}
    assert ids == {"musicdel", "upsong"}

    hidden = api.get("/api/search",
                     params={"q": "test", "category": "music", "refresh": "true", "sources": "upsong"})
    assert hidden.status_code == 200
    assert {i["source_id"] for i in hidden.json()["items"]} == {"musicdel"}


def test_api_search_unknown_source_is_ignored_not_rejected(tmp_path, monkeypatch):
    """A stale saved set must never break a search (search contract: ignore unknown ids)."""
    web_app = _stub_music(monkeypatch, ["musicdel"])
    from fastapi.testclient import TestClient
    api = TestClient(web_app.app)
    r = api.get("/api/search", params={"q": "test", "category": "music", "sources": "no-such-source"})
    assert r.status_code == 200
    assert {i["source_id"] for i in r.json()["items"]} == {"musicdel"}


def test_filtered_results_never_written_to_shared_cache_or_db(tmp_path, monkeypatch):
    """FR-030: a filtered scrape must not poison the shared cache or the persistent index."""
    web_app = _stub_music(monkeypatch, ["musicdel", "upsong"])
    cache_writes, db_writes = [], []
    monkeypatch.setattr(web_app.GLOBAL_CACHE, "set",
                        lambda *a, **k: cache_writes.append(a))
    monkeypatch.setattr(web_app.db, "upsert_items",
                        lambda items, *a, **k: db_writes.append(list(items)))
    from fastapi.testclient import TestClient
    api = TestClient(web_app.app)

    api.get("/api/search", params={"q": "f1", "category": "music", "refresh": "true", "sources": "upsong"})
    assert cache_writes == [] and db_writes == [], "filtered request must not write shared cache/db"

    api.get("/api/search", params={"q": "f2", "category": "music", "refresh": "true"})
    assert cache_writes and db_writes, "unfiltered request must still populate cache/db"


def test_finalize_drops_cached_items_from_degraded_source(monkeypatch):
    """FR-018a: a source that degraded AFTER its items were cached must not keep
    serving those stale items. _finalize runs on the cache/DB hit paths too, so
    the exclusion is enforced even when the scrape-time plugin filter never saw it."""
    from web import app as web_app
    monkeypatch.setattr(web_app.db, "get_consecutive_failures",
                        lambda sid: web_app.DEGRADED_THRESHOLD if sid == "musicdel" else 0)
    items = [_item("musicdel", "m1"), _item("popmusic", "p1"), _item("spotify", "s1")]
    out = web_app._finalize(items)
    kept = {i.source_id for i in out}
    assert "musicdel" not in kept, "degraded source's cached item must be dropped"
    assert kept == {"popmusic", "spotify"}


# --- T073 (FR-008): a slow source is abandoned, not waited on ---------------

class _SlowPlugin:
    """Sleeps past the per-source budget. The other stub returns instantly."""

    def __init__(self, source_id: str, delay: float):
        self.config = SourceConfig(id=source_id, name=source_id.title(), category=Category.MUSIC)

        async def _search(query, client):
            import asyncio

            await asyncio.sleep(delay)
            return [_item(self.config.id, f"{self.config.id}-late")]

        self.search = _search

    async def extract_links(self, item, client):
        return item


def test_slow_source_is_abandoned_without_blocking_the_search(monkeypatch):
    """FR-008: the slow plugin is dropped at its budget; the fast one still lands.

    The per-source budget is 7s in production. Shrinking it keeps the test fast,
    so the patch is bound to web.app's own `asyncio` name rather than to the
    shared asyncio module — patching the module would change wait_for for every
    later test in the same process.
    """
    import asyncio
    import time
    import types

    from fastapi.testclient import TestClient
    from web import app as web_app

    budget = 7.0          # the real value in web/app.py
    scaled = 0.2          # what the test pretends it is
    slow_delay = budget + 1.0

    proxy = types.SimpleNamespace(
        wait_for=lambda aw, timeout=None, **kw: asyncio.wait_for(
            aw, timeout=scaled if timeout == budget else timeout, **kw
        ),
        gather=asyncio.gather,
        TimeoutError=asyncio.TimeoutError,
        create_task=asyncio.create_task,
        sleep=asyncio.sleep,
    )
    monkeypatch.setattr(web_app, "asyncio", proxy)

    monkeypatch.setattr(web_app, "get_sources_for_category",
                        lambda cat, include_disabled=False, **kw: [
                            _SlowPlugin("slowsource", delay=slow_delay),
                            _StubPlugin("fastsource"),
                        ])
    monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: 0)
    monkeypatch.setattr(web_app.db, "record_search_failure", lambda sid: 0)
    monkeypatch.setattr(web_app.db, "record_search_success", lambda sid: None)
    monkeypatch.setattr(web_app.db, "search", lambda *a, **k: [])
    monkeypatch.setattr(web_app.GLOBAL_CACHE, "set", lambda *a, **k: None)

    started = time.monotonic()
    api = TestClient(web_app.app)
    resp = api.get("/api/search", params={"q": "test", "category": "music", "refresh": "true"})
    elapsed = time.monotonic() - started

    assert resp.status_code == 200
    data = resp.json()
    ids = {i["source_id"] for i in data["items"]}
    assert "fastsource" in ids, "the fast source's items were lost"
    assert "slowsource" not in ids, "the slow source was not abandoned"
    # The warning names the source by its display name (config.name), which the
    # stub derives as "Slowsource" from the id.
    assert any("slowsource" in w.lower() for w in data.get("warnings", [])), \
        f"no warning named the slow source: {data.get('warnings')}"
    # It returned at the (scaled) budget rather than waiting out the sleep.
    assert elapsed < 2.0, f"search blocked for {elapsed:.1f}s on the slow source"


def test_both_search_budgets_are_applied(monkeypatch):
    """The constitution's 7s-per-source / 10s-per-search budgets are load-bearing.

    Asserted by observing the timeouts the pipeline actually passes, with no
    patching of the values themselves: the outer 10s gather and the inner 7s
    per-plugin wait must both be present, and 7s must be the tighter of the two
    so a single slow source can never consume the whole search budget.
    """
    import asyncio
    import time

    from fastapi.testclient import TestClient
    from web import app as web_app

    used: list[float] = []
    original = asyncio.wait_for

    def _record(aw, timeout=None, **kw):
        used.append(timeout)
        return original(aw, timeout=timeout, **kw)

    # Bind the recorder to web.app's own name so asyncio itself is untouched.
    monkeypatch.setattr(web_app.asyncio, "wait_for", _record)

    monkeypatch.setattr(web_app, "get_sources_for_category",
                        lambda cat, include_disabled=False, **kw: [_StubPlugin("fastsource")])
    monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: 0)
    monkeypatch.setattr(web_app.db, "record_search_failure", lambda sid: 0)
    monkeypatch.setattr(web_app.db, "record_search_success", lambda sid: None)
    monkeypatch.setattr(web_app.db, "search", lambda *a, **k: [])
    monkeypatch.setattr(web_app.GLOBAL_CACHE, "set", lambda *a, **k: None)

    started = time.monotonic()
    api = TestClient(web_app.app)
    api.get("/api/search", params={"q": "budget", "category": "music", "refresh": "true"})
    elapsed = time.monotonic() - started

    # The outer gather is *called* before the inner coroutines run, so call
    # order is not execution order; assert on the set and the ordering guarantee.
    assert 7.0 in used, f"per-source 7s budget not applied: {used}"
    assert 10.0 in used, f"global 10s search budget not applied: {used}"
    assert min(used) == 7.0, f"the per-source budget must be the tighter bound: {used}"
    # A responsive source returns well inside its budget.
    assert elapsed < 7.0, f"a fast source took {elapsed:.1f}s"


def test_timed_out_source_counts_as_exactly_one_failure(monkeypatch):
    """FR-018a: the counter moves once per SEARCH, not once per timed-out request."""
    from web import app as web_app

    failures: list[str] = []
    monkeypatch.setattr(web_app, "get_sources_for_category",
                        lambda cat, include_disabled=False, **kw: [_StubPlugin("fastsource")])
    monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: 0)
    monkeypatch.setattr(web_app.db, "record_search_failure", lambda sid: failures.append(sid))
    monkeypatch.setattr(web_app.db, "record_search_success", lambda sid: None)
    monkeypatch.setattr(web_app.db, "search", lambda *a, **k: [])
    monkeypatch.setattr(web_app.GLOBAL_CACHE, "set", lambda *a, **k: None)

    from fastapi.testclient import TestClient

    api = TestClient(web_app.app)
    api.get("/api/search", params={"q": "counter", "category": "music", "refresh": "true"})

    # The stub source DID return an item, so it is a success, not a failure.
    assert failures == [], f"a successful source was counted as a failure: {failures}"


# --- T081 (FR-017): base.html actually shows kind, status, and the reason ---
#
# These drive the real "/" route. T080 fixed a defect where the template
# received raw SourceConfig objects, so `src.status` and `src.inactive_reason`
# were Undefined and every inactive source rendered with no reason at all.

def _landing_html(monkeypatch=None, category="music") -> str:
    from fastapi.testclient import TestClient
    from web import app as web_app

    if monkeypatch is not None:
        monkeypatch.setattr(web_app.db, "get_consecutive_failures", lambda sid: 0)
    return TestClient(web_app.app).get(f"/?category={category}").text


def test_source_list_shows_kind_for_every_source():
    """US4/AC1: each source's kind is visible as text, not implied by colour."""
    from sources import get_all_source_configs
    from models import Category, SourceKind

    html = _landing_html()
    music = [c for c in get_all_source_configs() if c.category is Category.MUSIC]
    expected_ref = sum(1 for c in music if c.kind is SourceKind.REFERENCE)
    expected_full = len(music) - expected_ref

    assert expected_ref > 0 and expected_full > 0, "fixture registry lost its kind split"
    # Each badge carries exactly one kind label.
    assert html.count("(ارجاعی") == expected_ref, "reference kind labels mismatched"
    assert html.count("(کامل") == expected_full, "full kind labels mismatched"


def test_every_inactive_source_renders_its_specific_reason():
    """FR-017 / SC-007: an inactive entry MUST display the actual cause.

    A generic "unavailable" is non-conforming; the test asserts each configured
    reason string appears verbatim in the rendered page.
    """
    from sources import INACTIVE_REASONS, get_all_source_configs
    from models import Category

    html = _landing_html()
    music_disabled = [
        c.id for c in get_all_source_configs()
        if c.category is Category.MUSIC and not c.enabled
    ]
    assert music_disabled, "expected inactive music sources to assert against"

    for sid in music_disabled:
        reason = INACTIVE_REASONS.get(sid, "")
        assert reason.strip(), f"{sid} has no reason configured"
        assert reason in html, f"{sid}'s reason {reason!r} is not rendered on the page"


def test_inactive_source_is_marked_inactive_and_enabled_one_is_not():
    """Status is visible as text for both states (US4/AC1)."""
    from sources import get_all_source_configs
    from models import Category

    html = _landing_html()
    music = [c for c in get_all_source_configs() if c.category is Category.MUSIC]
    disabled = [c for c in music if not c.enabled]
    enabled = [c for c in music if c.enabled]

    # One "(غیرفعال)" marker per disabled source; enabled ones never carry it.
    assert html.count("(غیرفعال)") == len(disabled), \
        f"expected {len(disabled)} inactive markers, found {html.count('(غیرفعال)')}"
    for cfg in enabled:
        start = html.find(cfg.name)
        assert start != -1, f"{cfg.name} missing from the source list"
        badge = html[start:start + 200]
        assert "غیرفعال" not in badge, f"{cfg.name} is enabled but rendered as inactive"


def test_degraded_source_is_labelled_degraded(monkeypatch):
    """The degraded branch must be reachable in the rendered output.

    Before T080 the template never received `status`, so this branch could not
    render at all. Forcing a source over the threshold proves it now does.
    """
    from fastapi.testclient import TestClient
    from web import app as web_app

    monkeypatch.setattr(web_app.db, "get_consecutive_failures",
                        lambda sid: web_app.DEGRADED_THRESHOLD if sid == "musicdel" else 0)

    html = TestClient(web_app.app).get("/?category=music").text
    assert "افت کیفیت" in html, "a degraded source is not labelled as degraded"

    # It stays listed (US4/AC3: degraded is visible, never silently removed).
    assert "MusicDel" in html, "a degraded source was removed from the list"


def test_source_rows_are_shared_with_the_api_listing():
    """T080: one derivation, two consumers — the JSON and the page cannot drift."""
    from fastapi.testclient import TestClient
    from web import app as web_app

    client = TestClient(web_app.app)
    api_rows = {r["id"]: r for r in client.get("/api/sources").json()}
    page_rows = web_app._source_display_rows()

    assert [r["id"] for r in page_rows] == list(api_rows), \
        "the page and the API disagree on which sources exist"
    for row in page_rows:
        assert row == api_rows[row["id"]], f"{row['id']} differs between page and API"
