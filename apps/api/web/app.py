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


async def _collect_items(
    cat_enum: Category,
    norm_query: str,
    raw_query: str,
    refresh: bool = False,
) -> tuple[list[MediaItem], list[str], bool]:
    """Fetch items from cache, persistent DB, or concurrent scraper plugins."""
    cat_clean = cat_enum.value

    # 1. Check in-memory cache and persistent database
    if not refresh:
        cached_items = GLOBAL_CACHE.get(cat_enum, norm_query)
        if cached_items is not None:
            return cached_items, [], True

        db_items = db.search(cat_enum, norm_query)
        if db_items:
            GLOBAL_CACHE.set(cat_enum, norm_query, db_items)
            return db_items, [], True

    # 2. Get active scraper plugins
    plugins = get_sources_for_category(cat_enum, include_disabled=False)
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

    # 4. Cache, persist to SQLite, and return
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
