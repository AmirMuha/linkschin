"""FastAPI JSON API for Iranian Multi-Media Direct Link Aggregator.

The UI is the Next.js app in ``apps/web``; this service only exposes JSON.
"""

from __future__ import annotations

import os

import asyncio
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, Query, Path, Body, Depends, HTTPException, Request, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse

from cache import GLOBAL_CACHE, normalize_persian_text
import db
from http_client import AsyncHttpClient
from models import (
    Category,
    MediaItem,
    SearchQuery,
    SourceKind,
    LoginRequest,
    SourceUpdateRequest,
    SourceToggleRequest,
    SuggestionCreateRequest,
    ConvertCreateRequest,
    ChatMessageRequest,
)
from sources import INACTIVE_REASONS, get_all_source_configs, get_sources_for_category
from sources import health
from sources.base import validate_stream_url
import web.catalog as catalog
import web.convert as convert
import web.chat as chat
from web.auth import authenticate_operator, create_access_token, get_current_operator
import extraction.dead_letter as dlq

DEGRADED_THRESHOLD = 3  # 3 consecutive failures → degraded, excluded from search (FR-018a)

app = FastAPI(
    title="Iranian Multi-Media Direct Link Aggregator",
    version="0.2.0",
    docs_url=None,
    redoc_url=None,
)

# Enable CORS for frontend web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.environ.get("FRONTEND_URL", "http://localhost:3000"),
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    Stamping the dataclass (not just the JSON dict) is what the client
    branches on: ``item.source_kind == "reference"`` reads the attribute. Applied
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
    quality: str | None = None,
    censorship: str | None = None,
    access_tier: str | None = None,
    limit: int = 40,
    offset: int = 0,
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
    stale_db_items: list[MediaItem] = []

    # 1. Offline-First Check:
    #    Query local SQLite database index first. If found, return sub-50ms immediately.
    if not refresh and not exclude_ids:
        cached_items = GLOBAL_CACHE.get(cat_enum, norm_query, scope)
        if cached_items:
            return _finalize(cached_items), [], True

        db_items = db.search(
            category=cat_enum,
            query=norm_query,
            quality=quality,
            censorship=censorship,
            access_tier=access_tier,
            exclude_sources=list(exclude_ids or ()),
            limit=limit,
            offset=offset,
        )
        if db_items:
            db_items = _finalize(db_items)
            GLOBAL_CACHE.set(cat_enum, norm_query, db_items, scope)
            return db_items, [], True

    # 2. Category Routing:
    #    Games and Music are served strictly offline-first from the database index for standard queries
    #    unless an explicit refresh or custom source exclusion is requested.
    if cat_enum in (Category.GAMES, Category.MUSIC) and not refresh and not exclude_ids:
        warning = f"عنوانی با مشخصات «{raw_query}» در پایگاه داده محلی یافت نشد. خزنده‌های پس‌زمینه در حال ایندکس خودکار هستند."
        return [], [warning], False

    # 3. For Movies (or explicit refresh): Trigger on-demand live scraper query
    degraded = _degraded_ids()
    hidden = set(exclude_ids or ())
    plugins = [
        p for p in get_sources_for_category(
            cat_enum, include_disabled=False, exclude_streaming=(scope != "all")
        )
        if p.config.id not in degraded and p.config.id not in hidden
    ]
    if not plugins:
        warning = f"هیچ منبع فعالی برای دسته «{cat_clean}» در دسترس نیست. منابع در حال به‌روزرسانی هستند."
        return [], [warning], False

    # 4. Concurrent search with timeout budget (7s per source, 10s global deadline)
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

    # 5. Record health per source
    for plugin in plugins:
        got_items = any(i.source_id == plugin.config.id for i in all_items)
        if got_items:
            try:
                db.record_search_success(plugin.config.id)
            except Exception:
                pass
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
            try:
                health.record_empty_response(plugin.config.id)
            except Exception:
                pass

    # 6. Discard unusable entries
    all_items = _finalize(_discard_unusable(all_items))

    # 7. Persist ALL live search results to SQLite database for fast future searches
    if not exclude_ids and all_items:
        try:
            db.upsert_items(all_items)
        except Exception:
            pass

    # 8. Filter to this tab, then cache
    matching = [i for i in all_items if i.category == cat_enum]
    if not exclude_ids and matching:
        GLOBAL_CACHE.set(cat_enum, norm_query, matching, scope)
    if matching:
        return matching, warnings, False

    return [], warnings, False

    return [], warnings, False


@app.get("/api/search", response_class=JSONResponse)
async def api_search_media(
    q: str = Query(..., description="Search query string"),
    category: str = Query("movies", description="Active media category"),
    refresh: bool = Query(False, description="Force fresh scrape and bypass cache"),
    sources: list[str] = Query(default=[], description="Source ids to exclude (per-user hidden set, FR-029)"),
    scope: str = Query("downloads", description="'all' to include streaming video platforms"),
    quality: str | None = Query(None, description="Quality filter e.g. 1080p, 720p"),
    censorship: str | None = Query(None, description="Censorship filter e.g. uncensored_only"),
    access_tier: str | None = Query(None, description="Access tier e.g. free, premium"),
    limit: int = Query(40, description="Max items"),
    offset: int = Query(0, description="Offset items"),
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
        cat_enum=cat_enum,
        norm_query=norm_query,
        raw_query=q,
        refresh=refresh,
        exclude_ids=set(sources),
        scope=scope,
        quality=quality,
        censorship=censorship,
        access_tier=access_tier,
        limit=limit,
        offset=offset,
    )

    return JSONResponse(
        {
            "query": q,
            "category": cat_clean,
            "is_cached": is_cached,
            "warnings": warnings,
            "total": len(items),
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
    """Build the display row for every registered source, merging persistent DB overrides."""
    all_sources = get_all_source_configs()
    db_configs = db.get_source_configs()
    reference_ids = {
        (c.category, c.id) for c in all_sources if c.kind is SourceKind.REFERENCE
    }
    degraded = _degraded_ids()
    rows: list[dict] = []
    for s in all_sources:
        override = db_configs.get(s.id)
        base_url = override["base_url"] if override and override.get("base_url") else s.primary_base_url
        mirror_url = override["mirror_url"] if override else None
        enabled = bool(override["enabled"]) if override else s.enabled

        row: dict = {
            "id": s.id,
            "name": s.name,
            "category": s.category.value,
            "base_url": base_url,
            "mirror_url": mirror_url,
            "enabled": enabled,
            "kind": "reference" if (s.category, s.id) in reference_ids else "full",
            "status": "inactive" if not enabled else ("degraded" if s.id in degraded else "active"),
            "inactive_reason": INACTIVE_REASONS.get(s.id) if not enabled else None,
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
        if not enabled and INACTIVE_REASONS.get(s.id):
            row["inactive_reason"] = INACTIVE_REASONS[s.id]
        rows.append(row)
    return rows


@app.get("/api/sources")
async def list_sources() -> JSONResponse:
    """Return full source listing with kind and health status per FR-017/T013."""
    return JSONResponse(_source_display_rows())


# ============================================================================
# Dynamic Catalog Feed Endpoints (User Story 1)
# ============================================================================

@app.get("/api/catalog/trending")
async def api_get_trending(
    category: str = Query("movies", description="Media category"),
    limit: int = Query(12, description="Max items"),
) -> JSONResponse:
    """Dynamic trending items for home hero banner and top shelf."""
    items = catalog.get_trending_items(category, limit)
    return JSONResponse({"category": category, "items": items})


@app.get("/api/catalog/latest")
async def api_get_latest(
    category: str = Query("movies", description="Media category"),
    limit: int = Query(14, description="Max items"),
) -> JSONResponse:
    """Dynamic latest released items for shelf browsing."""
    items = catalog.get_latest_items(category, limit)
    return JSONResponse({"category": category, "items": items})


@app.get("/api/items/{id}")
async def api_get_item(id: str = Path(..., description="Media item ID")) -> JSONResponse:
    """Retrieve detailed metadata and all download variants for a single item."""
    item = catalog.get_item_detail(id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return JSONResponse(item)


# ============================================================================
# Operator Authentication & Source Administration (User Story 3)
# ============================================================================

@app.post("/api/auth/login")
async def api_login(req: LoginRequest) -> JSONResponse:
    """Authenticate operator and return signed JWT Bearer token."""
    user = authenticate_operator(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid operator credentials")
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return JSONResponse({"access_token": token, "token_type": "bearer", "expires_in": 86400})


@app.patch("/api/sources/{id}")
async def api_update_source(
    id: str = Path(...),
    req: SourceUpdateRequest = Body(...),
    operator: dict = Depends(get_current_operator),
) -> JSONResponse:
    """Update source primary base address or fallback mirror."""
    all_cfgs = {s.id: s for s in get_all_source_configs()}
    base_cfg = all_cfgs.get(id)
    if not base_cfg:
        raise HTTPException(status_code=404, detail=f"Source '{id}' not found")
    res = db.upsert_source_config(
        source_id=id,
        category=base_cfg.category.value,
        name=base_cfg.name,
        base_url=req.base_url or base_cfg.primary_base_url,
        mirror_url=req.mirror_url,
    )
    return JSONResponse(res)


@app.patch("/api/sources/{id}/toggle")
async def api_toggle_source(
    id: str = Path(...),
    req: SourceToggleRequest = Body(...),
    operator: dict = Depends(get_current_operator),
) -> JSONResponse:
    """Toggle source enabled / disabled state."""
    all_cfgs = {s.id: s for s in get_all_source_configs()}
    base_cfg = all_cfgs.get(id)
    if not base_cfg:
        raise HTTPException(status_code=404, detail=f"Source '{id}' not found")
    res = db.toggle_source_config(id, req.enabled)
    if not res:
        res = db.upsert_source_config(
            source_id=id,
            category=base_cfg.category.value,
            name=base_cfg.name,
            base_url=base_cfg.primary_base_url,
            enabled=req.enabled,
        )
    return JSONResponse(res)


@app.post("/api/sources/suggest", status_code=status.HTTP_201_CREATED)
async def api_suggest_source(req: SuggestionCreateRequest) -> JSONResponse:
    """Submit a portal suggestion to the operator review queue with domain deduplication."""
    from urllib.parse import urlparse
    domain = urlparse(req.url).netloc.lower().split(":")[0]
    if not domain:
        domain = req.url.lower().strip()
    res = db.create_suggestion(
        url=req.url,
        domain=domain,
        category=req.category,
        source_name=req.source_name,
        proposed_tier=req.proposed_tier,
        default_audio_track=req.default_audio_track,
        contact=req.contact,
        notes=req.notes,
    )
    return JSONResponse(
        {
            "success": True,
            "message": "پیشنهاد منبع با موفقیت در صف بررسی اپراتور ثبت شد",
            "domain": res.get("domain", domain),
            "request_count": res.get("request_count", 1),
        },
        status_code=201,
    )


@app.get("/api/admin/suggestions")
async def api_admin_suggestions(
    status: str = Query("pending"),
    category: str | None = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    operator: dict = Depends(get_current_operator),
) -> JSONResponse:
    """List suggestions in the operator review queue."""
    return JSONResponse(db.list_suggestions(status, category, limit, offset))


@app.patch("/api/admin/suggestions/{id}")
async def api_admin_update_suggestion(
    id: int = Path(...),
    body: dict = Body(...),
    operator: dict = Depends(get_current_operator),
) -> JSONResponse:
    """Approve or reject a community portal suggestion."""
    new_status = body.get("status")
    if new_status not in ("approved", "rejected", "pending"):
        raise HTTPException(status_code=400, detail="Invalid status")
    ok = db.update_suggestion_status(id, new_status)
    if not ok:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return JSONResponse({"success": True, "id": id, "status": new_status})


# ============================================================================
# YouTube to MP3 Converter Utility (User Story 4)
# ============================================================================

@app.post("/api/convert", status_code=status.HTTP_202_ACCEPTED)
async def api_start_convert(
    req: ConvertCreateRequest,
    request: Request,
) -> JSONResponse:
    """Start asynchronous YouTube audio extraction."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        job = await convert.start_conversion_task(
            url=req.url,
            bitrate=req.bitrate,
            sample_rate=req.sample_rate,
            write_meta=req.write_meta,
            client_ip=client_ip,
        )
        return JSONResponse(
            {"request_id": job["id"], "status": job["status"], "message": "Conversion started"},
            status_code=202,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=429, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/api/convert/{id}")
async def api_get_convert_status(id: str = Path(...)) -> JSONResponse:
    """Poll progress and state of a YouTube conversion job."""
    job = db.get_conversion_job(id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    resp: dict[str, Any] = {
        "request_id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "current_step": job["current_step"],
        "video_title": job["video_title"],
        "error_message": job["error_message"],
    }
    if job["status"] == "completed":
        resp["download_url"] = f"/api/download/{id}"
    return JSONResponse(resp)


@app.get("/api/download/{id}")
async def api_download_mp3(
    id: str = Path(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> FileResponse:
    """Stream converted MP3 file directly and immediately purge temporary files."""
    job = db.get_conversion_job(id)
    if not job or job["status"] != "completed":
        raise HTTPException(status_code=404, detail="Audio file not ready or job not found")
    file_path = convert.get_job_mp3_path(id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file already delivered or expired")

    # Immediate single-use cleanup hook
    background_tasks.add_task(convert.cleanup_job_files, id)
    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg",
        filename=file_path.name,
    )


@app.get("/api/convert/history")
async def api_convert_history(request: Request) -> JSONResponse:
    """Return recent conversion history for client IP."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    history = db.get_conversion_history(client_ip=client_ip)
    return JSONResponse({"history": history})


# ============================================================================
# Conversational Search Assistant (User Story 5)
# ============================================================================

@app.post("/api/chat")
async def api_chat(req: ChatMessageRequest, request: Request):
    """Interact with AI assistant (supports JSON and SSE text/event-stream)."""
    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept:
        return StreamingResponse(
            chat.generate_chat_events(req.message, req.session_id, req.category),
            media_type="text/event-stream",
        )
    res = await chat.process_chat_message(req.message, req.session_id, req.category)
    return JSONResponse(res)


@app.delete("/api/chat/session/{id}")
async def api_clear_chat(id: str = Path(...)) -> JSONResponse:
    """Reset conversational session context."""
    chat.clear_session(id)
    return JSONResponse({"success": True, "session_id": id})


# ============================================================================
# Dead Letter Queue (DLQ, User Story 7)
# ============================================================================

@app.get("/api/admin/dlq")
async def api_admin_dlq(
    status: str = Query("pending"),
    category: str | None = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    operator: dict = Depends(get_current_operator),
) -> JSONResponse:
    """Inspect dead-letter queue records for failed AI extractions."""
    items = dlq.list_dead_letters(status, category, limit, offset)
    return JSONResponse({"items": items, "total": len(items)})


@app.post("/api/admin/dlq/{id}/retry")
async def api_admin_retry_dlq(
    id: int = Path(...),
    operator: dict = Depends(get_current_operator),
) -> JSONResponse:
    """Trigger manual re-extraction for a specific DLQ item."""
    res = await dlq.retry_dead_letter(id)
    return JSONResponse(res)

