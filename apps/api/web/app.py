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
    reference_ids = {c.id for c in get_all_source_configs() if c.kind is SourceKind.REFERENCE}
    degraded = _degraded_ids()
    kept: list[MediaItem] = []
    for item in items:
        if item.source_id in degraded:
            continue
        item.source_kind = "reference" if item.source_id in reference_ids else "full"
        kept.append(item)
    # Stable sort: the key is constant within a kind, so relevance order inside
    # each group survives exactly.
    return sorted(kept, key=lambda i: 1 if i.source_kind == "reference" else 0)


async def _collect_items(
    cat_enum: Category,
    norm_query: str,
    raw_query: str,
    refresh: bool = False,
    exclude_ids: set[str] | None = None,
) -> tuple[list[MediaItem], list[str], bool]:
    """Fetch items from cache, persistent DB, or concurrent scraper plugins."""
    # Per-user hidden-source set (FR-029): applied BEFORE plugin selection;
    # the filtered result set is NEVER cached — the shared cache must never
    # leak one user's filter into another's response (FR-030).
    cat_clean = cat_enum.value

    # 1. Check in-memory cache and persistent database.
    #    A filtered (hidden-source) request MUST NOT read the shared cache:
    #    cached results are the unfiltered set, so serving them to a user who
    #    hid a source would re-introduce the hidden source (FR-030). Filtered
    #    requests always scrape fresh and never write back to the cache.
    if not refresh and not exclude_ids:
        cached_items = GLOBAL_CACHE.get(cat_enum, norm_query)
        if cached_items is not None:
            return _finalize(cached_items), [], True

        db_items = db.search(cat_enum, norm_query)
        if db_items:
            db_items = _finalize(db_items)
            GLOBAL_CACHE.set(cat_enum, norm_query, db_items)
            return db_items, [], True

    # 2. Get active scraper plugins, excluding degraded ones (FR-019) and the
    #    user's hidden set (FR-029). Unknown ids in exclude_ids simply match
    #    nothing, so a stale saved set can never break a search.
    degraded = _degraded_ids()
    hidden = set(exclude_ids or ())
    plugins = [
        p for p in get_sources_for_category(cat_enum, include_disabled=False)
        if p.config.id not in degraded and p.config.id not in hidden
    ]
    if not plugins:
        warning = f"هیچ منبع فعالی برای دسته «{cat_clean}» در دسترس نیست. منابع در حال به‌روزرسانی هستند."
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
    for plugin in plugins:
        got_items = any(i.source_id == plugin.config.id for i in all_items)
        try:
            if got_items:
                db.record_search_success(plugin.config.id)
            else:
                db.record_search_failure(plugin.config.id)
        except Exception:
            pass  # health tracking must not break the search

    # 5. Stamp kind and order full-before-reference, before caching (FR-005a, T017/T018)
    all_items = _finalize(all_items)

    # 6. Cache and persist — only for unfiltered requests (FR-030): a filtered
    #    result set written under the shared key would either re-introduce
    #    hidden sources for others (cache) or persist an incomplete index for
    #    the query (db). The next unfiltered request populates both normally.
    if not exclude_ids:
        GLOBAL_CACHE.set(cat_enum, norm_query, all_items)
        if all_items:
            try:
                db.upsert_items(all_items)
            except Exception:
                pass

    return all_items, warnings, False


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
) -> HTMLResponse:
    """Search enabled sources for the category, extract direct links, and render results."""
    cat_clean = category.lower()
    try:
        cat_enum = Category(cat_clean)
    except ValueError:
        cat_enum = Category.MOVIES
        cat_clean = "movies"

    norm_query = normalize_persian_text(q)
    items, warnings, is_cached = await _collect_items(cat_enum, norm_query, q, refresh, exclude_ids=set(sources))
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
) -> JSONResponse:
    """JSON API endpoint returning structured media search results."""
    cat_clean = category.lower()
    try:
        cat_enum = Category(cat_clean)
    except ValueError:
        cat_enum = Category.MOVIES
        cat_clean = "movies"

    norm_query = normalize_persian_text(q)
    items, warnings, is_cached = await _collect_items(cat_enum, norm_query, q, refresh, exclude_ids=set(sources))

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
        }
    )


def _source_display_rows() -> list[dict]:
    """Build the display row for every registered source (FR-017, T080).

    One derivation, two consumers: the ``/api/sources`` JSON and the Jinja
    source list in ``base.html``. They MUST NOT diverge — the template previously
    received raw ``SourceConfig`` objects, which have no ``status`` or
    ``inactive_reason``, so every inactive source rendered with no reason.

    Derived at request time so a row never contradicts the DB or the registry.
    """
    all_sources = get_all_source_configs()
    reference_ids = {c.id for c in all_sources if c.kind is SourceKind.REFERENCE}
    degraded = _degraded_ids()
    rows: list[dict] = []
    for s in all_sources:
        row: dict = {
            "id": s.id,
            "name": s.name,
            "category": s.category.value,
            "base_url": s.primary_base_url,
            "enabled": s.enabled,
            "kind": "reference" if s.id in reference_ids else "full",
            "status": "inactive" if not s.enabled else ("degraded" if s.id in degraded else "active"),
            "inactive_reason": INACTIVE_REASONS.get(s.id) if not s.enabled else None,
            "consecutive_failures": 0,
        }
        try:
            row["consecutive_failures"] = db.get_consecutive_failures(s.id)
        except Exception:
            pass  # a failing DB must not break the listing
        rows.append(row)
    return rows


@app.get("/api/sources")
async def list_sources() -> JSONResponse:
    """Return full source listing with kind and health status per FR-017/T013.

    Fields: id, name, category, base_url, enabled, kind, status, inactive_reason,
    consecutive_failures.
    """
    return JSONResponse(_source_display_rows())
