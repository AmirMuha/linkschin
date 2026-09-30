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
from models import Category, MediaItem, SearchQuery
from sources import get_all_source_configs, get_sources_for_category
from sources.base import validate_stream_url

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


async def _collect_items(
    cat_enum: Category,
    norm_query: str,
    raw_query: str,
    refresh: bool = False,
) -> tuple[list[MediaItem], list[str], bool]:
    """Fetch items from cache, persistent DB, or concurrent scraper plugins.

    A portal is not partitioned by category: Downloadha answers a games query from its
    soundtrack section too, so a plugin's output can carry an item labelled for another
    tab. The cache and the DB both filter by the stored category, so without this the
    fresh-scrape path was the one route that put a music post in the games tab. Filtering
    here covers every caller and every item source in one place.
    """
    cat_clean = cat_enum.value
    # Anything older than this is re-scraped on the next request, because portals
    # rename posts and rotate download links (a cached uptvs title pointed at a
    # different film's file than the page it was taken from).
    stale_db_items: list[MediaItem] = []

    # 1. Check in-memory cache and persistent database
    if not refresh:
        cached_items = GLOBAL_CACHE.get(cat_enum, norm_query)
        # `if cached_items:` not `is not None` - a cached [] means an earlier scrape
        # found nothing, and treating it as authoritative would shadow the DB below
        # for the whole TTL, blanking out a query the index can still answer.
        if cached_items:
            return cached_items, [], True

        db_items = db.search(cat_enum, norm_query)
        if db_items:
            if db.search(cat_enum, norm_query, max_age_seconds=DB_STALE_TTL_SECONDS):
                GLOBAL_CACHE.set(cat_enum, norm_query, db_items)
                return db_items, [], True
            # Stale: fall through and re-scrape, but keep these as a floor so a failed
            # or slow refresh can never reduce a result set to nothing.
            stale_db_items = db_items

    # 2. Get active scraper plugins
    plugins = get_sources_for_category(cat_enum, include_disabled=False)
    if not plugins:
        warning = f"هیچ منبع فعالی برای دسته «{cat_clean}» در دسترس نیست. منابع در حال به‌روزرسانی هستند."
        if stale_db_items:
            GLOBAL_CACHE.set(cat_enum, norm_query, stale_db_items)
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

    # 4. Cache, persist to SQLite, and return
    # Only a non-empty result is cached: a timed-out scrape must not overwrite a
    # good answer with nothing.
    if all_items:
        all_items = [i for i in all_items if i.category == cat_enum]
        if not all_items:
            return [], warnings, False
        GLOBAL_CACHE.set(cat_enum, norm_query, all_items)
        try:
            db.upsert_items(all_items)
        except Exception:
            pass
        return all_items, warnings, False

    # Nothing fresh: serve the stale index rather than claim the query has no results.
    if stale_db_items:
        GLOBAL_CACHE.set(cat_enum, norm_query, stale_db_items)
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

    all_sources = get_all_source_configs()
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
) -> HTMLResponse:
    """Search enabled sources for the category, extract direct links, and render results."""
    cat_clean = category.lower()
    try:
        cat_enum = Category(cat_clean)
    except ValueError:
        cat_enum = Category.MOVIES
        cat_clean = "movies"

    norm_query = normalize_persian_text(q)
    items, warnings, is_cached = await _collect_items(cat_enum, norm_query, q, refresh)
    all_sources = get_all_source_configs()

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
) -> JSONResponse:
    """JSON API endpoint returning structured media search results."""
    cat_clean = category.lower()
    try:
        cat_enum = Category(cat_clean)
    except ValueError:
        cat_enum = Category.MOVIES
        cat_clean = "movies"

    norm_query = normalize_persian_text(q)
    items, warnings, is_cached = await _collect_items(cat_enum, norm_query, q, refresh)

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


@app.get("/api/sources")
async def list_sources() -> JSONResponse:
    """Return JSON details of all configured sources and active base URLs."""
    all_sources = get_all_source_configs()
    data = [
        {
            "id": s.id,
            "name": s.name,
            "category": s.category.value,
            "base_url": s.primary_base_url,
            "enabled": s.enabled,
        }
        for s in all_sources
    ]
    return JSONResponse(data)
