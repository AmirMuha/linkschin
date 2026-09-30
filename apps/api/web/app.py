"""FastAPI web application for Iranian Multi-Media Direct Link Aggregator."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cache import GLOBAL_CACHE, normalize_persian_text
import db
from http_client import AsyncHttpClient
from models import Category, MediaItem, SearchQuery, SourceKind
from sources import INACTIVE_REASONS, get_all_source_configs, get_sources_for_category
from sources import health
from sources.base import validate_stream_url

DEGRADED_THRESHOLD = 3  # 3 consecutive failures → degraded, excluded from search (FR-018a)

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

app = FastAPI(
    title="Iranian Multi-Media Direct Link Aggregator",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

# Enable CORS for frontend web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Re-scrape a stored row once it is this old, so renamed posts and rotated download
# links surface without waiting for a user to hit refresh.
DB_STALE_TTL_SECONDS = 6 * 3600


def _degraded_ids() -> set[str]:
    """Source ids at/over the failure threshold, excluded from search (FR-019)."""
    degraded: set[str] = set()
    for cfg in get_all_source_configs():
        if not cfg.enabled:
            continue
        try:
            if db.get_consecutive_failures(cfg.id) >= DEGRADED_THRESHOLD:
                degraded.add(cfg.id)
        except Exception:
            pass  # a broken DB must not silently drop every source
    return degraded


def _source_status(cfg) -> str:
    """Derive a source's health: inactive | degraded | active (data-model.md)."""
    if not cfg.enabled:
        return "inactive"
    try:
        return "degraded" if db.get_consecutive_failures(cfg.id) >= DEGRADED_THRESHOLD else "active"
    except Exception:
        return "active"


def _finalize(items: list[MediaItem]) -> list[MediaItem]:
    """Stamp item.source_kind, drop degraded sources, sort full-before-reference (FR-005a/018a, T012/T017).

    Stamping the dataclass (not just the JSON dict) is what the Jinja templates
    branch on: ``item.source_kind == "reference"`` reads the attribute. Applied
    on cache/DB paths too because rehydrated items default to "full" and come
    back in last_seen order. Degraded sources are also dropped here: their
    stale items can still live in the cache/DB from before they failed, and
    FR-018a excludes them from returning results regardless of source.
    """
    reference_ids = {
        (c.category, c.id) for c in get_all_source_configs() if c.kind is SourceKind.REFERENCE
    }
    degraded = _degraded_ids()
    kept: list[MediaItem] = []
    for item in items:
        if item.source_id in degraded:
            continue
        item.source_kind = "reference" if (item.category, item.source_id) in reference_ids else "full"
        kept.append(item)
    # Stable sort: the key is constant within a kind, so relevance order inside
    # each group survives exactly.
    return sorted(kept, key=lambda i: 1 if i.source_kind == "reference" else 0)


def _discard_unusable(items: list[MediaItem]) -> list[MediaItem]:
    """Drop entries with nothing to open, and collapse same-title repeats (FR-017, FR-018).

    A movie result with no ``movie_variants`` and no ``watch_url`` offers the user no
    action at all — the parser matched the markup but the link extraction found
    nothing, and shipping the row would advertise a result the page cannot deliver.
    Games and music keep their own payloads and are not touched by this rule.

    Duplicates are keyed by normalized title per source: one site listing a film
    twice (a featured row and a grid entry) must not fill the list with copies.
    """

    def _title_key(item: MediaItem) -> str:
        return " ".join((item.title or "").split()).casefold()

    kept: list[MediaItem] = []
    seen_titles: set[tuple[str, str]] = set()
    for item in items:
        if item.category is Category.MOVIES:
            if not item.movie_variants and not item.watch_url:
                continue
            key = (item.source_id, _title_key(item))
            if key in seen_titles:
                continue
            seen_titles.add(key)
        kept.append(item)
    return kept


async def _collect_items(
    cat_enum: Category,
    norm_query: str,
    raw_query: str,
    refresh: bool = False,
    exclude_ids: set[str] | None = None,
    scope: str = "downloads",
) -> tuple[list[MediaItem], list[str], bool]:
    """Fetch items from cache, persistent DB, or concurrent scraper plugins.

    A portal is not partitioned by category: Downloadha answers a games query from its
    soundtrack section too, so a plugin's output can carry an item labelled for another
    tab. The cache and the DB both filter by the stored category, so without this the
    fresh-scrape path was the one route that put a music post in the games tab. Filtering
    here covers every caller and every item source in one place.
    """
    # Per-user hidden-source set (FR-029): applied BEFORE plugin selection;
    # the filtered result set is NEVER cached — the shared cache must never
    # leak one user's filter into another's response (FR-030).
    cat_clean = cat_enum.value
    # Anything older than this is re-scraped on the next request, because portals
    # rename posts and rotate download links (a cached uptvs title pointed at a
    # different film's file than the page it was taken from).
    stale_db_items: list[MediaItem] = []

    # 1. Check in-memory cache and persistent database.
    #    A filtered (hidden-source) request MUST NOT read the shared cache:
    #    cached results are the unfiltered set, so serving them to a user who
    #    hid a source would re-introduce the hidden source (FR-030). Filtered
    #    requests always scrape fresh and never write back to the cache.
    if not refresh and not exclude_ids:
        cached_items = GLOBAL_CACHE.get(cat_enum, norm_query, scope)
        # `if cached_items:` not `is not None` - a cached [] means an earlier scrape
        # found nothing, and treating it as authoritative would shadow the DB below
        # for the whole TTL, blanking out a query the index can still answer.
        if cached_items:
            return _finalize(cached_items), [], True

        db_items = db.search(cat_enum, norm_query)
        if db_items:
            if db.search(cat_enum, norm_query, max_age_seconds=DB_STALE_TTL_SECONDS):
                db_items = _finalize(db_items)
                GLOBAL_CACHE.set(cat_enum, norm_query, db_items, scope)
                return db_items, [], True
            # Stale: fall through and re-scrape, but keep these as a floor so a failed
            # or slow refresh can never reduce a result set to nothing.
            stale_db_items = _finalize(db_items)

    # 2. Get active scraper plugins, excluding degraded ones (FR-019) and the
    #    user's hidden set (FR-029). Unknown ids in exclude_ids simply match
    #    nothing, so a stale saved set can never break a search.
    degraded = _degraded_ids()
    hidden = set(exclude_ids or ())
    # Default scope excludes streaming platforms. scope='all' opts into them.
    plugins = [
        p for p in get_sources_for_category(
            cat_enum, include_disabled=False, exclude_streaming=(scope != "all")
        )
        if p.config.id not in degraded and p.config.id not in hidden
    ]
    if not plugins:
        warning = f"هیچ منبع فعالی برای دسته «{cat_clean}» در دسترس نیست. منابع در حال به‌روزرسانی هستند."
        if stale_db_items:
            GLOBAL_CACHE.set(cat_enum, norm_query, stale_db_items, scope)
            return stale_db_items, [warning], False
        return [], [warning], False

    # 3. Concurrent search with timeout budget (7s per source, 10s global deadline)
    all_items: list[MediaItem] = []
    warnings: list[str] = []
    search_q = SearchQuery(raw_query=raw_query, normalized_query=norm_query, category=cat_enum)

    async with AsyncHttpClient(timeout=7.0) as client:
        async def _query_plugin(plugin: Any) -> list[MediaItem]:
            try:
                found = await asyncio.wait_for(plugin.search(search_q, client), timeout=7.0)
                if found:
                    extract_tasks = [plugin.extract_links(item, client) for item in found[:5]]
                    await asyncio.gather(*extract_tasks, return_exceptions=True)
                    for item in found[:5]:
                        if item.category == Category.MOVIES and item.stream_url:
                            if not await validate_stream_url(item.stream_url, client):
                                item.stream_url = None
                    return found
            except asyncio.TimeoutError:
                warnings.append(f"منبع {plugin.config.name} به دلیل تأخیر پاسخ موقتاً در دسترس نبود.")
                return []
            except Exception:
                warnings.append(f"خطا در دریافت اطلاعات از منبع {plugin.config.name}.")
                return []

        try:
            search_tasks = [_query_plugin(p) for p in plugins]
            results = await asyncio.wait_for(
                asyncio.gather(*search_tasks, return_exceptions=True),
                timeout=10.0,
            )
            for res in results:
                if isinstance(res, list):
                    all_items.extend(res)
        except asyncio.TimeoutError:
            warnings.append("زمان جستجوی سراسری به پایان رسید. برخی نتایج ممکن است ناقص باشند.")

    # 4. Record one failure/success per source per completed search (FR-018a, T020).
    #    The counter moves once per SEARCH, not once per HTTP request.
    #    sources/health.py is the richer record a maintainer reads: which state the
    #    source is in, why, when it last worked, and which address served it (T080).
    for plugin in plugins:
        got_items = any(i.source_id == plugin.config.id for i in all_items)
        if got_items:
            try:
                db.record_search_success(plugin.config.id)
            except Exception:
                pass  # health tracking must not break the search
            try:
                health.record_success(
                    plugin.config.id,
                    address=getattr(plugin, "active_address", None),
                    provides_downloads=plugin.config.provides_downloads,
                )
            except Exception:
                pass
        else:
            try:
                db.record_search_failure(plugin.config.id)
            except Exception:
                pass
            # An empty answer is its own signal: the site answered 200 with nothing
            # parseable, which is how a silent markup change shows up (FR-019).
            try:
                health.record_empty_response(plugin.config.id)
            except Exception:
                pass

    # 5. Discard unusable entries (FR-017, FR-018, T035): a movie carrying neither a
    #    download nor a watch destination has nothing for the user to open, and one
    #    source repeating a title must not fill the list with copies (T020).
    all_items = _finalize(_discard_unusable(all_items))

    # 6. Persist the whole scrape, not the filtered view: a portal answers a games
    #    query from its soundtrack section too, and that item is correctly filed as
    #    music -- it just must not appear in THIS tab. Dropping it before the upsert
    #    would mean the music tab can never find it, since the index is the only way
    #    a re-labelled item becomes searchable. Filtering after the write keeps both.
    #    Only for unfiltered requests (FR-030): a filtered result set written under
    #    the shared key would either re-introduce hidden sources for others (cache)
    #    or persist an incomplete index for the query (db).
    if not exclude_ids and all_items:
        try:
            db.upsert_items(all_items)
        except Exception:
            pass

    # 7. Filter to this tab, then cache. Only a non-empty result is cached: a
    #    timed-out scrape must not overwrite a good answer with nothing.
    matching = [i for i in all_items if i.category == cat_enum]
    if not exclude_ids and matching:
        GLOBAL_CACHE.set(cat_enum, norm_query, matching, scope)
    if matching:
        return matching, warnings, False

    # Nothing fresh: serve the stale index rather than claim the query has no results.
    if stale_db_items:
        GLOBAL_CACHE.set(cat_enum, norm_query, stale_db_items, scope)
        warnings.append("نتایج ذخیره‌شده ممکن است به‌روز نباشند؛ منابع در دسترس نبودند.")
        return stale_db_items, warnings, False

    return [], warnings, False


@app.get("/", response_class=HTMLResponse)
async def index_page(
    request: Request,
    category: str = Query("movies", description="Default active tab category"),
) -> HTMLResponse:
    """Render landing page with active category and sources."""
    cat_clean = category.lower()
    if cat_clean not in ("movies", "games", "music"):
        cat_clean = "movies"

    all_sources = _source_display_rows()
    return templates.TemplateResponse(
        request=request,
        name="base.html",
        context={
            "active_category": cat_clean,
            "all_sources": all_sources,
            "query": "",
        },
    )


@app.get("/search", response_class=HTMLResponse)
async def search_media(
    request: Request,
    q: str = Query(..., description="Search query string"),
    category: str = Query("movies", description="Active media category"),
    refresh: bool = Query(False, description="Force fresh scrape and bypass cache"),
    sources: list[str] = Query(default=[], description="Source ids to exclude (per-user hidden set, FR-029)"),
    scope: str = Query("downloads", description="'all' to include streaming video platforms"),
) -> HTMLResponse:
    """Search enabled sources for the category, extract direct links, and render results."""
    cat_clean = category.lower()
    try:
        cat_enum = Category(cat_clean)
    except ValueError:
        cat_enum = Category.MOVIES
        cat_clean = "movies"

    norm_query = normalize_persian_text(q)
    items, warnings, is_cached = await _collect_items(
        cat_enum, norm_query, q, refresh, exclude_ids=set(sources), scope=scope
    )
    all_sources = _source_display_rows()

    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={
            "active_category": cat_clean,
            "all_sources": all_sources,
            "query": q,
            "items": items,
            "is_cached": is_cached,
            "warnings": warnings,
        },
    )


@app.get("/api/search", response_class=JSONResponse)
async def api_search_media(
    q: str = Query(..., description="Search query string"),
    category: str = Query("movies", description="Active media category"),
    refresh: bool = Query(False, description="Force fresh scrape and bypass cache"),
    sources: list[str] = Query(default=[], description="Source ids to exclude (per-user hidden set, FR-029)"),
    scope: str = Query("downloads", description="'all' to include streaming video platforms"),
) -> JSONResponse:
    """JSON API endpoint returning structured media search results."""
    cat_clean = category.lower()
    try:
        cat_enum = Category(cat_clean)
    except ValueError:
        cat_enum = Category.MOVIES
        cat_clean = "movies"

    norm_query = normalize_persian_text(q)
    items, warnings, is_cached = await _collect_items(
        cat_enum, norm_query, q, refresh, exclude_ids=set(sources), scope=scope
    )

    # source_kind ships via asdict(); _collect_items stamped it on the objects.
    return JSONResponse(
        {
            "query": q,
            "category": cat_clean,
            "is_cached": is_cached,
            "warnings": warnings,
            "items": [asdict(item) for item in items],
        }
    )


@app.get("/health")
@app.get("/api/health")
async def health_check() -> JSONResponse:
    """System health check and diagnostic information."""
    all_sources = get_all_source_configs()
    reg_sources: dict[str, list[str]] = {
        "movies": [],
        "games": [],
        "music": [],
    }
    for s in all_sources:
        reg_sources[s.category.value].append(s.id)

    try:
        db_stats = db.stats()
    except Exception:
        db_stats = {}

    return JSONResponse(
        {
            "status": "healthy",
            "version": "0.1.0",
            "cache_entries": GLOBAL_CACHE.size,
            "registered_sources": reg_sources,
            "database_stats": db_stats,
            "source_health": _source_health_rows(),
            "source_health_counts": health.get_counts(),
        }
    )


def _source_health_rows() -> list[dict]:
    """Every tracked source's health record, for /health (FR-008, T014).

    Read from the DB rather than the in-memory registry so a fresh process reports
    the state a previous one recorded. A DB that cannot be read falls back to the
    in-memory registry rather than reporting nothing.
    """
    rows: list[dict] = []
    try:
        rows = db.get_all_source_health()
    except Exception:
        rows = []
    if rows:
        return rows
    return [
        {
            "source_id": h.source_id,
            "state": h.state.value,
            "reason": h.reason,
            "last_success_at": h.last_success_at,
            "last_failure_at": h.last_failure_at,
            "consecutive_failures": h.consecutive_failures,
            "active_address": h.active_address,
        }
        for h in health.get_all().values()
    ]


def _source_display_rows() -> list[dict]:
    """Build the display row for every registered source (FR-017, T080).

    One derivation, two consumers: the ``/api/sources`` JSON and the Jinja
    source list in ``base.html``. They MUST NOT diverge — the template previously
    received raw ``SourceConfig`` objects, which have no ``status`` or
    ``inactive_reason``, so every inactive source rendered with no reason.

    Derived at request time so a row never contradicts the DB or the registry.

    ``id`` stays the bare source id even where a movie source and a music source
    share one (aparat, namasha, fam, rubika). ``category`` disambiguates them for
    any consumer that needs to address one specifically.
    """
    all_sources = get_all_source_configs()
    reference_ids = {
        (c.category, c.id) for c in all_sources if c.kind is SourceKind.REFERENCE
    }
    degraded = _degraded_ids()
    rows: list[dict] = []
    for s in all_sources:
        row: dict = {
            "id": s.id,
            "name": s.name,
            "category": s.category.value,
            "base_url": s.primary_base_url,
            "enabled": s.enabled,
            "kind": "reference" if (s.category, s.id) in reference_ids else "full",
            "status": "inactive" if not s.enabled else ("degraded" if s.id in degraded else "active"),
            "inactive_reason": INACTIVE_REASONS.get(s.id) if not s.enabled else None,
            "consecutive_failures": 0,
            "access_tier": s.access_tier.value,
            "provides_downloads": s.provides_downloads,
            "is_streaming": s.is_streaming,
            "state": health.get(s.id).state.value,
            "last_reachable_at": None,
            "active_address": None,
        }
        try:
            row["consecutive_failures"] = db.get_consecutive_failures(s.id)
        except Exception:
            pass  # a failing DB must not break the listing
        h = health.get(s.id)
        row["state"] = h.state.value
        row["last_reachable_at"] = h.last_success_at
        row["active_address"] = h.active_address
        # FR-020: a source can be disabled in config yet still be reachable; the
        # registry reason is the authority for why it is off.
        if not s.enabled and INACTIVE_REASONS.get(s.id):
            row["inactive_reason"] = INACTIVE_REASONS[s.id]
        rows.append(row)
    return rows


@app.get("/api/sources")
async def list_sources() -> JSONResponse:
    """Return full source listing with kind and health status per FR-017/T013.

    Fields: id, name, category, base_url, enabled, kind, status, inactive_reason,
    consecutive_failures, access_tier, provides_downloads, state,
    last_reachable_at, active_address.
    """
    return JSONResponse(_source_display_rows())
