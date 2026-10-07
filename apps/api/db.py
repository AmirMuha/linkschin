"""Persistent local search index built on stdlib sqlite3 only."""

from __future__ import annotations

import os
import sqlite3
import time
from enum import Enum
from pathlib import Path

from cache import normalize_persian_text
from models import (
    Category,
    CensorshipStatus,
    GamePartLink,
    GameRelease,
    MediaItem,
    MovieDownloadVariant,
    MusicDownloadVariant,
    MusicTrack,
    SourceAccessTier,
)

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "index.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS media_items (
    id               TEXT PRIMARY KEY,
    category         TEXT NOT NULL,
    source_id        TEXT NOT NULL,
    title            TEXT NOT NULL,
    title_norm       TEXT NOT NULL,
    artist           TEXT NOT NULL DEFAULT '',
    page_url         TEXT NOT NULL,
    poster_url       TEXT,
    release_year     INT,
    description      TEXT,
    watch_url        TEXT,
    stream_url       TEXT,
    release_group    TEXT,
    archive_password TEXT,
    total_size       TEXT,
    imdb_rating      REAL,
    censorship_status TEXT,
    source_access_tier TEXT,
    first_seen       REAL NOT NULL,
    last_seen        REAL NOT NULL,
    UNIQUE(source_id, page_url)
);
CREATE TABLE IF NOT EXISTS download_variants (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     TEXT NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    label       TEXT,
    codec       TEXT,
    audio_track TEXT,
    size_bytes  INT,
    size_text   TEXT,
    is_censored INT,
    is_premium  INT,
    url         TEXT NOT NULL,
    access      TEXT DEFAULT 'direct'
);
CREATE TABLE IF NOT EXISTS game_parts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     TEXT NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    release_id  TEXT,
    part_number INT NOT NULL,
    part_label  TEXT,
    file_size   TEXT,
    url         TEXT NOT NULL,
    access      TEXT DEFAULT 'direct'
);
-- One post can ship several archives (an exFAT set and a PKG set), each numbered
-- from 1. Their per-release metadata needs somewhere to live, otherwise _rehydrate
-- would collapse every part into a single release.
CREATE TABLE IF NOT EXISTS game_releases (
    id               TEXT NOT NULL,
    item_id          TEXT NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    source_name      TEXT,
    release_group    TEXT,
    version          TEXT,
    total_size       TEXT,
    archive_password TEXT,
    sort_order       INT NOT NULL DEFAULT 0,
    UNIQUE(item_id, id)
);
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
    title_norm, artist, page_url, item_id UNINDEXED, tokenize='trigram'
);
CREATE TABLE IF NOT EXISTS crawl_state (
    source_id  TEXT PRIMARY KEY,
    last_page  INT NOT NULL DEFAULT 0,
    last_crawl REAL,
    consecutive_failures INT NOT NULL DEFAULT 0
);
-- Per-source operational health (FR-008/FR-020). crawl_state counts failures for the
-- degraded filter; this table is the richer record a maintainer reads: which state the
-- source is in, why, when it last worked, and which address served the last request.
CREATE TABLE IF NOT EXISTS source_health (
    source_id            TEXT PRIMARY KEY,
    state                TEXT NOT NULL,
    reason               TEXT,
    last_success_at      TEXT,
    last_failure_at      TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    active_address       TEXT
);
-- Persistent operator source configuration overrides
CREATE TABLE IF NOT EXISTS source_configs (
    source_id           TEXT PRIMARY KEY,
    category            TEXT NOT NULL,
    name                TEXT NOT NULL,
    base_url            TEXT NOT NULL,
    mirror_url          TEXT,
    enabled             INT NOT NULL DEFAULT 1,
    timeout_seconds     REAL NOT NULL DEFAULT 7.0,
    updated_at          REAL NOT NULL
);
-- Community portal suggestions for operator review queue
CREATE TABLE IF NOT EXISTS source_suggestions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    url                 TEXT NOT NULL,
    domain              TEXT NOT NULL UNIQUE,
    category            TEXT NOT NULL,
    source_name         TEXT NOT NULL,
    proposed_tier       TEXT NOT NULL DEFAULT '1',
    default_audio_track TEXT NOT NULL DEFAULT 'EN',
    contact             TEXT,
    notes               TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
    request_count       INT NOT NULL DEFAULT 1,
    created_at          REAL NOT NULL,
    updated_at          REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_suggestions_status ON source_suggestions(status, category);
-- YouTube to MP3 asynchronous conversion task tracking
CREATE TABLE IF NOT EXISTS conversion_jobs (
    id                  TEXT PRIMARY KEY,
    client_ip           TEXT NOT NULL,
    youtube_url         TEXT NOT NULL,
    video_id            TEXT NOT NULL,
    video_title         TEXT,
    bitrate             INT NOT NULL DEFAULT 320,
    sample_rate         INT NOT NULL DEFAULT 44100,
    write_meta          INT NOT NULL DEFAULT 1,
    status              TEXT NOT NULL DEFAULT 'queued',
    progress            INT NOT NULL DEFAULT 0,
    current_step        TEXT,
    error_message       TEXT,
    created_at          REAL NOT NULL,
    completed_at        REAL
);
CREATE INDEX IF NOT EXISTS idx_conversion_client ON conversion_jobs(client_ip, created_at);
-- Dead-letter queue for failed or unparseable LangChain extraction attempts (US7)
CREATE TABLE IF NOT EXISTS extraction_dead_letter (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id           TEXT NOT NULL,
    page_url            TEXT NOT NULL,
    category            TEXT NOT NULL,
    raw_html            TEXT NOT NULL,
    error_message       TEXT NOT NULL,
    model_name          TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
    retry_count         INT NOT NULL DEFAULT 0,
    next_retry_at       REAL NOT NULL,
    created_at          REAL NOT NULL,
    resolved_at         REAL
);
CREATE INDEX IF NOT EXISTS idx_dlq_status ON extraction_dead_letter(status, next_retry_at);
-- Per-domain adaptive rate limiting and backoff state (US6)
CREATE TABLE IF NOT EXISTS domain_throttle_state (
    domain              TEXT PRIMARY KEY,
    consecutive_429     INT NOT NULL DEFAULT 0,
    current_delay_sec   REAL NOT NULL DEFAULT 1.0,
    backoff_until       REAL NOT NULL DEFAULT 0,
    total_requests      INT NOT NULL DEFAULT 0,
    total_throttled     INT NOT NULL DEFAULT 0,
    updated_at          REAL NOT NULL
);
-- Operator credentials for administrative actions
CREATE TABLE IF NOT EXISTS operator_users (
    username            TEXT PRIMARY KEY,
    password_hash       TEXT NOT NULL,
    role                TEXT NOT NULL DEFAULT 'operator',
    created_at          REAL NOT NULL
);
-- One-shot data migrations record that they have run here, so they stay idempotent
-- across restarts without re-scanning the whole table every time the DB is opened.
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_category ON media_items(category);
CREATE INDEX IF NOT EXISTS idx_parts_release ON game_parts(item_id, release_id);
CREATE INDEX IF NOT EXISTS idx_releases_item ON game_releases(item_id);
-- FTS has no foreign keys, so keep the index in sync with deletes.
CREATE TRIGGER IF NOT EXISTS trg_fts_delete AFTER DELETE ON media_items BEGIN
    DELETE FROM search_fts WHERE item_id = old.id;
END;
"""

# `CREATE TABLE IF NOT EXISTS` never adds columns to an existing table, so new ones
# ship as idempotent migrations checked against PRAGMA table_info.
_ADDED_COLUMNS = {
    "media_items": [
        ("imdb_rating", "REAL"),
        ("censorship_status", "TEXT"),
        ("source_access_tier", "TEXT"),
        ("watch_url", "TEXT"),
        ("is_featured", "INT NOT NULL DEFAULT 0"),
        ("view_count", "INT NOT NULL DEFAULT 0"),
    ],
    "download_variants": [
        ("access", "TEXT DEFAULT 'direct'"),
        ("is_censored", "INT"),
        ("is_premium", "INT"),
    ],
    "game_parts": [("access", "TEXT DEFAULT 'direct'")],
    "crawl_state": [("consecutive_failures", "INTEGER NOT NULL DEFAULT 0")],
    # Non-NULL only while the probe loop holds a source off (web/probe.py). It is
    # what separates "the probe turned this off" from "an operator turned this off" —
    # without it the probe would re-enable a portal someone deliberately disabled.
    "source_configs": [("auto_disabled_at", "REAL")],
}


def _migrate(conn: sqlite3.Connection) -> None:
    """Add missing columns to pre-existing databases (idempotent)."""
    for table, columns in _ADDED_COLUMNS.items():
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, decl in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
    _drop_misfiled_game_rows(conn)


# Rows the games scrapers filed before parse_search_results learned to tell a game post
# from a soundtrack. Fixed at the source, but a stale row is never re-emitted to
# overwrite, and db.search filters on the stored category -- so they would keep serving
# music in the games tab forever. Scoped to Downloadha alone: its URL carries the section
# (`/game/`, `/mobile/`), while YasDL permalinks are flat and would match nothing here.
# The marker insert and the DELETE share one transaction, so a fresh deploy can never
# burn the marker and skip the delete. FTS follows via trg_fts_delete; child rows via
# ON DELETE CASCADE.
_MISFILED_GAME_ROWS = "drop_misfiled_game_rows_v1"


def _drop_misfiled_game_rows(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT 1 FROM schema_meta WHERE key=?", (_MISFILED_GAME_ROWS,)).fetchone():
        return
    with conn:
        conn.execute(
            """DELETE FROM media_items
               WHERE source_id='downloadha' AND category='games'
                 AND page_url NOT LIKE '%/game/%'
                 AND NOT (page_url LIKE '%/mobile/%' AND title LIKE '%بازی%')"""
        )
        conn.execute("INSERT INTO schema_meta(key, value) VALUES (?, ?)",
                     (_MISFILED_GAME_ROWS, "1"))


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open (and initialize) the index database."""
    raw = db_path or os.environ.get("LINKSCHIN_DB") or DEFAULT_DB_PATH
    path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    return conn


def _cat(category: Category | str) -> str:
    return category.value if isinstance(category, Category) else str(category)


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _variant_rows(item: MediaItem) -> list[tuple]:
    rows = []
    for v in item.movie_variants:
        # ponytail: size_bytes holds file_size_mb as-is; rename the column if MB->bytes ever matters.
        rows.append((item.id, "movie", v.quality, v.codec, v.audio_track,
                     int(v.file_size_mb) if v.file_size_mb is not None else None,
                     None,
                     None if v.is_censored is None else int(v.is_censored),
                     int(v.is_premium),
                     v.download_url, v.access))
    for t in item.music_tracks:
        for d in t.downloads:
            rows.append((item.id, "music", d.bitrate, None, None, None, d.file_size,
                         None, None, d.download_url, d.access))
    return rows


def _part_rows(item: MediaItem) -> list[tuple]:
    return [(item.id, r.id, p.part_number, p.part_label, p.file_size, p.download_url, p.access)
            for r in item.game_releases for p in r.parts]


def _release_rows(item: MediaItem) -> list[tuple]:
    return [(r.id, item.id, r.source_name, r.release_group, r.version, r.total_size,
             r.archive_password, order)
            for order, r in enumerate(item.game_releases)]


def upsert_items(items: list[MediaItem], db_path: Path | str | None = None) -> int:
    """Insert or refresh items, their variants/parts, and the FTS index. Returns count written."""
    if not items:
        return 0
    now = time.time()
    conn = connect(db_path)
    try:
        with conn:
            for item in items:
                game = item.game_releases[0] if item.game_releases else None
                artist = item.music_tracks[0].artist if item.music_tracks else ""
                # The natural key (source_id, page_url) wins over a stale id for the same page.
                conn.execute(
                    "DELETE FROM media_items WHERE source_id=? AND page_url=? AND id<>?",
                    (item.source_id, item.page_url, item.id),
                )
                conn.execute(
                    """INSERT INTO media_items
                       (id, category, source_id, title, title_norm, artist, page_url, poster_url,
                        release_year, description, watch_url, stream_url, release_group, archive_password,
                        total_size, imdb_rating, censorship_status, source_access_tier,
                        first_seen, last_seen)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         category=excluded.category, title=excluded.title,
                         title_norm=excluded.title_norm, artist=excluded.artist,
                         poster_url=excluded.poster_url, release_year=excluded.release_year,
                         description=excluded.description, watch_url=excluded.watch_url,
                         stream_url=excluded.stream_url,
                         release_group=excluded.release_group, archive_password=excluded.archive_password,
                         total_size=excluded.total_size,
                         imdb_rating=excluded.imdb_rating,
                         censorship_status=excluded.censorship_status,
                         source_access_tier=excluded.source_access_tier,
                         first_seen=MIN(media_items.first_seen, excluded.first_seen),
                         last_seen=excluded.last_seen""",
                    (item.id, _cat(item.category), item.source_id, item.title,
                     normalize_persian_text(item.title), artist, item.page_url, item.poster_url,
                     item.release_year, item.description, item.watch_url, item.stream_url,
                     game.release_group if game else None,
                     game.archive_password if game else None,
                     game.total_size if game else None,
                     item.imdb_rating, item.censorship_status.value, item.source_access_tier.value,
                     now, now),
                )
                conn.execute("DELETE FROM download_variants WHERE item_id=?", (item.id,))
                conn.executemany(
                    "INSERT INTO download_variants (item_id, kind, label, codec, audio_track,"
                    " size_bytes, size_text, is_censored, is_premium, url, access)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    _variant_rows(item),
                )
                conn.execute("DELETE FROM game_releases WHERE item_id=?", (item.id,))
                conn.executemany(
                    "INSERT INTO game_releases (id, item_id, source_name, release_group, version,"
                    " total_size, archive_password, sort_order) VALUES (?,?,?,?,?,?,?,?)"
                    " ON CONFLICT(item_id, id) DO UPDATE SET"
                    "   source_name=excluded.source_name, release_group=excluded.release_group,"
                    "   version=excluded.version, total_size=excluded.total_size,"
                    "   archive_password=excluded.archive_password, sort_order=excluded.sort_order",
                    _release_rows(item),
                )
                conn.execute("DELETE FROM game_parts WHERE item_id=?", (item.id,))
                conn.executemany(
                    "INSERT INTO game_parts (item_id, release_id, part_number, part_label, file_size, url, access)"
                    " VALUES (?,?,?,?,?,?,?)",
                    _part_rows(item),
                )
                conn.execute("DELETE FROM search_fts WHERE item_id=?", (item.id,))
                conn.execute(
                    "INSERT INTO search_fts (title_norm, artist, page_url, item_id) VALUES (?,?,?,?)",
                    (normalize_persian_text(item.title), artist, item.page_url, item.id),
                )
        return len(items)
    finally:
        conn.close()


def _enum_or_default(row: sqlite3.Row, key: str, enum_cls: type[Enum], default: Enum):
    """Read an enum column, tolerating NULL and any value a future version may add.

    A hand-edited or newer-format row must degrade to the default, not raise a
    ValueError out of search() and 500 the request.
    """
    raw = row[key]
    if not raw:
        return default
    try:
        return enum_cls(raw)
    except ValueError:
        return default


def _rehydrate(conn: sqlite3.Connection, row: sqlite3.Row) -> MediaItem:
    """Rebuild a typed MediaItem from its row plus child rows."""
    # ponytail: 3 extra queries per result; batch-load child rows if result sets grow past ~100.
    variants = conn.execute(
        "SELECT * FROM download_variants WHERE item_id=? ORDER BY id", (row["id"],)
    ).fetchall()
    parts = conn.execute(
        "SELECT * FROM game_parts WHERE item_id=? ORDER BY release_id, part_number", (row["id"],)
    ).fetchall()
    release_rows = conn.execute(
        "SELECT * FROM game_releases WHERE item_id=? ORDER BY sort_order, id", (row["id"],)
    ).fetchall()

    movies = [
        MovieDownloadVariant(
            id=f"{row['id']}:{v['id']}", quality=v["label"] or "", codec=v["codec"] or "",
            audio_track=v["audio_track"] or "", download_url=v["url"],
            file_size_mb=float(v["size_bytes"]) if v["size_bytes"] is not None else None,
            access=v["access"] or "direct",
            is_censored=None if v["is_censored"] is None else bool(v["is_censored"]),
            is_premium=bool(v["is_premium"]) if v["is_premium"] is not None else False,
        )
        for v in variants if v["kind"] == "movie"
    ]

    tracks: list[MusicTrack] = []
    track = None
    for v in variants:
        if v["kind"] != "music":
            continue
        if track is None:
            track = MusicTrack(
                id=f"{row['id']}:music", title=row["title"], artist=row["artist"],
                source_name=row["source_id"], cover_url=row["poster_url"],
                stream_url=row["stream_url"],
            )
            tracks.append(track)
        track.downloads.append(
            MusicDownloadVariant(bitrate=v["label"] or "", download_url=v["url"],
                                 file_size=v["size_text"], access=v["access"] or "direct")
        )

    # Group parts by their release so two archives from one post stay separate
    # sequences instead of merging into one list with duplicate part numbers.
    releases: list[GameRelease] = []
    if release_rows:
        parts_by_release: dict[str, list[sqlite3.Row]] = {}
        for p in parts:
            parts_by_release.setdefault(p["release_id"] or release_rows[0]["id"], []).append(p)
        for r in release_rows:
            rel_parts = parts_by_release.get(r["id"])
            if not rel_parts:
                continue
            releases.append(GameRelease(
                id=r["id"], source_name=r["source_name"] or row["source_id"],
                release_group=r["release_group"] or "",
                version=r["version"] or "", total_size=r["total_size"] or "",
                archive_password=r["archive_password"] or "",
                parts=[GamePartLink(part_number=p["part_number"], part_label=p["part_label"] or "",
                                    download_url=p["url"], file_size=p["file_size"],
                                    access=p["access"] or "direct") for p in rel_parts],
            ))
    elif parts:
        # Legacy rows written before game_releases existed: keep them readable.
        releases.append(GameRelease(
            id=parts[0]["release_id"] or row["id"], source_name=row["source_id"],
            release_group=row["release_group"] or "", total_size=row["total_size"] or "",
            archive_password=row["archive_password"] or "",
            parts=[GamePartLink(part_number=p["part_number"], part_label=p["part_label"] or "",
                                download_url=p["url"], file_size=p["file_size"],
                                access=p["access"] or "direct") for p in parts],
        ))

    return MediaItem(
        id=row["id"], title=row["title"], category=Category(row["category"]),
        source_id=row["source_id"], page_url=row["page_url"],
        release_year=row["release_year"], poster_url=row["poster_url"],
        description=row["description"], stream_url=row["stream_url"],
        watch_url=row["watch_url"],
        imdb_rating=float(row["imdb_rating"]) if row["imdb_rating"] is not None else None,
        censorship_status=_enum_or_default(row, "censorship_status", CensorshipStatus,
                                           CensorshipStatus.UNSPECIFIED),
        source_access_tier=_enum_or_default(row, "source_access_tier", SourceAccessTier,
                                            SourceAccessTier.FREE),
        movie_variants=movies, game_releases=releases, music_tracks=tracks,
    )


def search(
    category: Category | str,
    query: str,
    limit: int = 40,
    offset: int = 0,
    db_path: Path | str | None = None,
    max_age_seconds: float | None = None,
    quality: str | None = None,
    censorship: str | None = None,
    access_tier: str | None = None,
    exclude_sources: list[str] | None = None,
) -> list[MediaItem]:
    """Search the index: trigram FTS for 3+ char queries, LIKE scan for shorter ones."""
    conn = connect(db_path)
    try:
        norm = normalize_persian_text(query)
        if not norm:
            return []
        cat = _cat(category)
        filters = []
        params: list = []

        if max_age_seconds is not None:
            filters.append("m.last_seen >= ?")
            params.append(time.time() - max_age_seconds)

        if censorship and censorship != "include":
            if censorship == "uncensored_only":
                filters.append("m.censorship_status = 'uncensored'")
            elif censorship == "censored_only":
                filters.append("m.censorship_status = 'censored'")

        if access_tier:
            filters.append("m.source_access_tier = ?")
            params.append(access_tier.lower())

        if exclude_sources:
            placeholders = ",".join("?" for _ in exclude_sources)
            filters.append(f"m.source_id NOT IN ({placeholders})")
            params.extend(exclude_sources)

        filter_clause = (" AND " + " AND ".join(filters)) if filters else ""

        if len(norm) >= 3:
            match = " ".join('"' + tok.replace('"', '""') + '"' for tok in norm.split())
            sql = (
                "SELECT m.* FROM search_fts f JOIN media_items m ON m.id = f.item_id"
                " WHERE search_fts MATCH ? AND m.category = ?" + filter_clause
                + " ORDER BY m.last_seen DESC LIMIT ? OFFSET ?"
            )
            all_params = [match, cat, *params, limit, offset]
        else:
            like = f"%{_escape_like(norm)}%"
            sql = (
                "SELECT m.* FROM media_items m WHERE m.category = ?"
                " AND (m.title_norm LIKE ? ESCAPE '\\' OR m.artist LIKE ? ESCAPE '\\')"
                + filter_clause + " ORDER BY m.last_seen DESC LIMIT ? OFFSET ?"
            )
            all_params = [cat, like, like, *params, limit, offset]

        try:
            rows = conn.execute(sql, all_params).fetchall()
        except sqlite3.Error:
            return []
        return [_rehydrate(conn, r) for r in rows]
    finally:
        conn.close()


def get_last_page(conn: sqlite3.Connection, source_id: str) -> int:
    """Return the last fully crawled listing page for a source (0 when new)."""
    row = conn.execute(
        "SELECT last_page FROM crawl_state WHERE source_id=?", (source_id,)
    ).fetchone()
    return int(row["last_page"]) if row else 0


def set_last_page(conn: sqlite3.Connection, source_id: str, page: int) -> None:
    """Advance the crawl high-water mark so the next run resumes at page + 1."""
    with conn:
        conn.execute(
            "INSERT INTO crawl_state (source_id, last_page, last_crawl) VALUES (?, ?, ?) "
            "ON CONFLICT(source_id) DO UPDATE SET last_page=excluded.last_page, "
            "last_crawl=excluded.last_crawl",
            (source_id, page, time.time()),
        )


def get_source_health(source_id: str, db_path: Path | str | None = None) -> dict | None:
    """Return the stored health record for a source, or None when it has no row."""
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM source_health WHERE source_id=?", (source_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_source_health(db_path: Path | str | None = None) -> list[dict]:
    """Every stored health record, so a restart can restore the in-memory registry."""
    conn = connect(db_path)
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM source_health").fetchall()]
    finally:
        conn.close()


def set_source_health(
    conn: sqlite3.Connection,
    source_id: str,
    state: str,
    reason: str | None = None,
    last_success_at: str | None = None,
    last_failure_at: str | None = None,
    consecutive_failures: int = 0,
    active_address: str | None = None,
) -> None:
    """Upsert a source's health record. Takes an open conn, like set_last_page."""
    with conn:
        conn.execute(
            "INSERT INTO source_health (source_id, state, reason, last_success_at, "
            "last_failure_at, consecutive_failures, active_address) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(source_id) DO UPDATE SET "
            "state=excluded.state, reason=excluded.reason, "
            "last_success_at=excluded.last_success_at, "
            "last_failure_at=excluded.last_failure_at, "
            "consecutive_failures=excluded.consecutive_failures, "
            "active_address=excluded.active_address",
            (source_id, state, reason, last_success_at, last_failure_at,
             consecutive_failures, active_address),
        )


def get_consecutive_failures(source_id: str, db_path: Path | str | None = None) -> int:
    """Failed searches since the last success (0 when the source has no row)."""
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT consecutive_failures FROM crawl_state WHERE source_id=?", (source_id,)
        ).fetchone()
        return int(row["consecutive_failures"]) if row else 0
    finally:
        conn.close()


def record_search_failure(source_id: str, db_path: Path | str | None = None) -> int:
    """Increment the failure counter once per completed search; return the new value."""
    conn = connect(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO crawl_state (source_id, consecutive_failures) VALUES (?, 1) "
                "ON CONFLICT(source_id) DO UPDATE SET"
                " consecutive_failures = consecutive_failures + 1",
                (source_id,),
            )
        row = conn.execute(
            "SELECT consecutive_failures FROM crawl_state WHERE source_id=?", (source_id,)
        ).fetchone()
        return int(row["consecutive_failures"])
    finally:
        conn.close()


def record_search_success(source_id: str, db_path: Path | str | None = None) -> None:
    """Any success resets the counter to 0."""
    conn = connect(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO crawl_state (source_id, consecutive_failures) VALUES (?, 0) "
                "ON CONFLICT(source_id) DO UPDATE SET consecutive_failures = 0",
                (source_id,),
            )
    finally:
        conn.close()


def stats(db_path: Path | str | None = None) -> dict:
    """Item counts by category and source, plus the newest last_seen timestamp."""
    conn = connect(db_path)
    try:
        by_category = dict(conn.execute(
            "SELECT category, COUNT(*) FROM media_items GROUP BY category").fetchall())
        by_source = dict(conn.execute(
            "SELECT source_id, COUNT(*) FROM media_items GROUP BY source_id").fetchall())
        total, last_seen = conn.execute(
            "SELECT COUNT(*), MAX(last_seen) FROM media_items").fetchone()
        return {"total": total, "by_category": by_category, "by_source": by_source, "last_seen": last_seen}
    finally:
        conn.close()


def get_item_by_id(item_id: str, db_path: Path | str | None = None) -> MediaItem | None:
    """Fetch single item by its id, rehydrating its variants and parts."""
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM media_items WHERE id=?", (item_id,)).fetchone()
        return _rehydrate(conn, row) if row else None
    finally:
        conn.close()


def get_trending(category: Category | str, limit: int = 12, db_path: Path | str | None = None) -> list[MediaItem]:
    """Top items for hero and trending shelves, ordered by is_featured then views/last_seen."""
    conn = connect(db_path)
    try:
        cat = _cat(category)
        rows = conn.execute(
            "SELECT * FROM media_items WHERE category=? ORDER BY is_featured DESC, view_count DESC, last_seen DESC LIMIT ?",
            (cat, limit)
        ).fetchall()
        return [_rehydrate(conn, r) for r in rows]
    finally:
        conn.close()


def get_latest(category: Category | str, limit: int = 14, db_path: Path | str | None = None) -> list[MediaItem]:
    """Latest items chronologically by last_seen."""
    conn = connect(db_path)
    try:
        cat = _cat(category)
        rows = conn.execute(
            "SELECT * FROM media_items WHERE category=? ORDER BY last_seen DESC LIMIT ?",
            (cat, limit)
        ).fetchall()
        return [_rehydrate(conn, r) for r in rows]
    finally:
        conn.close()


def record_item_view(item_id: str, db_path: Path | str | None = None) -> None:
    """Increment item view counter for trending calculations."""
    conn = connect(db_path)
    try:
        with conn:
            conn.execute("UPDATE media_items SET view_count = view_count + 1 WHERE id=?", (item_id,))
    finally:
        conn.close()


# --- Source Configs & Overrides ---

def get_source_configs(db_path: Path | str | None = None) -> dict[str, dict]:
    """Return all persistent source configuration overrides."""
    conn = connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM source_configs").fetchall()
        return {r["source_id"]: dict(r) for r in rows}
    finally:
        conn.close()


def get_source_config(source_id: str, db_path: Path | str | None = None) -> dict | None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM source_configs WHERE source_id=?", (source_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def upsert_source_config(
    source_id: str,
    category: str,
    name: str,
    base_url: str,
    mirror_url: str | None = None,
    enabled: bool = True,
    timeout_seconds: float = 7.0,
    db_path: Path | str | None = None,
) -> dict:
    now = time.time()
    conn = connect(db_path)
    try:
        with conn:
            conn.execute(
                """INSERT INTO source_configs (source_id, category, name, base_url, mirror_url, enabled, timeout_seconds, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source_id) DO UPDATE SET
                     base_url = excluded.base_url,
                     mirror_url = COALESCE(excluded.mirror_url, source_configs.mirror_url),
                     enabled = excluded.enabled,
                     timeout_seconds = excluded.timeout_seconds,
                     updated_at = excluded.updated_at""",
                (source_id, category, name, base_url, mirror_url, int(enabled), timeout_seconds, now),
            )
        return get_source_config(source_id, db_path) or {}
    finally:
        conn.close()


def toggle_source_config(source_id: str, enabled: bool, db_path: Path | str | None = None) -> dict | None:
    conn = connect(db_path)
    try:
        with conn:
            # An explicit operator action always wins over a probe-held disable:
            # clear the marker so the probe never re-enables what the operator just set.
            conn.execute(
                "UPDATE source_configs SET enabled = ?, auto_disabled_at = NULL, updated_at = ? WHERE source_id = ?",
                (int(enabled), time.time(), source_id),
            )
        return get_source_config(source_id, db_path)
    finally:
        conn.close()


def set_source_auto_disabled(
    source_id: str, auto_disabled_at: float | None, db_path: Path | str | None = None
) -> None:
    """Stamp/clear the probe's hold on a source. NULL means the probe has no hold."""
    conn = connect(db_path)
    try:
        with conn:
            conn.execute(
                "UPDATE source_configs SET auto_disabled_at = ? WHERE source_id = ?",
                (auto_disabled_at, source_id),
            )
    finally:
        conn.close()


# --- Community Suggestions ---

def create_suggestion(
    url: str,
    domain: str,
    category: str,
    source_name: str,
    proposed_tier: str = "1",
    default_audio_track: str = "EN",
    contact: str | None = None,
    notes: str | None = None,
    db_path: Path | str | None = None,
) -> dict:
    now = time.time()
    conn = connect(db_path)
    try:
        with conn:
            conn.execute(
                """INSERT INTO source_suggestions
                   (url, domain, category, source_name, proposed_tier, default_audio_track, contact, notes, status, request_count, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 1, ?, ?)
                   ON CONFLICT(domain) DO UPDATE SET
                     request_count = source_suggestions.request_count + 1,
                     updated_at = excluded.updated_at""",
                (url, domain, category, source_name, proposed_tier, default_audio_track, contact, notes, now, now),
            )
            row = conn.execute("SELECT * FROM source_suggestions WHERE domain=?", (domain,)).fetchone()
            return dict(row) if row else {}
    finally:
        conn.close()


def list_suggestions(
    status: str = "pending",
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Path | str | None = None,
) -> list[dict]:
    conn = connect(db_path)
    try:
        if category:
            rows = conn.execute(
                "SELECT * FROM source_suggestions WHERE status=? AND category=? ORDER BY request_count DESC, created_at DESC LIMIT ? OFFSET ?",
                (status, category, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM source_suggestions WHERE status=? ORDER BY request_count DESC, created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_suggestion_status(suggestion_id: int, status: str, db_path: Path | str | None = None) -> bool:
    conn = connect(db_path)
    try:
        with conn:
            cur = conn.execute(
                "UPDATE source_suggestions SET status=?, updated_at=? WHERE id=?",
                (status, time.time(), suggestion_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


# --- Conversion Jobs (YouTube to MP3) ---

def create_conversion_job(
    job_id: str,
    client_ip: str,
    youtube_url: str,
    video_id: str,
    video_title: str | None = None,
    bitrate: int = 320,
    sample_rate: int = 44100,
    write_meta: bool = True,
    db_path: Path | str | None = None,
) -> dict:
    now = time.time()
    conn = connect(db_path)
    try:
        with conn:
            conn.execute(
                """INSERT INTO conversion_jobs
                   (id, client_ip, youtube_url, video_id, video_title, bitrate, sample_rate, write_meta, status, progress, current_step, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', 0, 'In queue', ?)""",
                (job_id, client_ip, youtube_url, video_id, video_title, bitrate, sample_rate, int(write_meta), now),
            )
        return get_conversion_job(job_id, db_path) or {}
    finally:
        conn.close()


def get_conversion_job(job_id: str, db_path: Path | str | None = None) -> dict | None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM conversion_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_conversion_job(
    job_id: str,
    status: str,
    progress: int | None = None,
    current_step: str | None = None,
    video_title: str | None = None,
    error_message: str | None = None,
    completed: bool = False,
    db_path: Path | str | None = None,
) -> None:
    conn = connect(db_path)
    try:
        completed_at = time.time() if completed else None
        with conn:
            conn.execute(
                """UPDATE conversion_jobs SET
                     status = ?,
                     progress = COALESCE(?, progress),
                     current_step = COALESCE(?, current_step),
                     video_title = COALESCE(?, video_title),
                     error_message = COALESCE(?, error_message),
                     completed_at = COALESCE(?, completed_at)
                   WHERE id = ?""",
                (status, progress, current_step, video_title, error_message, completed_at, job_id),
            )
    finally:
        conn.close()


def get_conversion_history(client_ip: str | None = None, limit: int = 20, db_path: Path | str | None = None) -> list[dict]:
    conn = connect(db_path)
    try:
        if client_ip:
            rows = conn.execute(
                "SELECT * FROM conversion_jobs WHERE client_ip=? ORDER BY created_at DESC LIMIT ?",
                (client_ip, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM conversion_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_recent_conversions(client_ip: str, window_seconds: float = 3600.0, db_path: Path | str | None = None) -> int:
    cutoff = time.time() - window_seconds
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) as count FROM conversion_jobs WHERE client_ip=? AND created_at >= ?",
            (client_ip, cutoff),
        ).fetchone()
        return int(row["count"]) if row else 0
    finally:
        conn.close()


# --- Dead Letter Queue (DLQ, User Story 7) ---

def insert_dead_letter(
    source_id: str,
    page_url: str,
    category: str,
    raw_html: str,
    error_message: str,
    model_name: str | None = None,
    db_path: Path | str | None = None,
) -> int:
    now = time.time()
    conn = connect(db_path)
    try:
        with conn:
            cur = conn.execute(
                """INSERT INTO extraction_dead_letter
                   (source_id, page_url, category, raw_html, error_message, model_name, status, retry_count, next_retry_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?)""",
                (source_id, page_url, category, raw_html, error_message, model_name, now + 60.0, now),
            )
            return cur.lastrowid
    finally:
        conn.close()


def list_dead_letters(
    status: str = "pending",
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Path | str | None = None,
) -> list[dict]:
    conn = connect(db_path)
    try:
        if category:
            rows = conn.execute(
                "SELECT id, source_id, page_url, category, error_message, model_name, status, retry_count, next_retry_at, created_at, resolved_at FROM extraction_dead_letter WHERE status=? AND category=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, category, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, source_id, page_url, category, error_message, model_name, status, retry_count, next_retry_at, created_at, resolved_at FROM extraction_dead_letter WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_pending_dead_letters(limit: int = 20, db_path: Path | str | None = None) -> list[dict]:
    now = time.time()
    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM extraction_dead_letter WHERE status='pending' AND next_retry_at <= ? ORDER BY next_retry_at ASC LIMIT ?",
            (now, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_dead_letter(
    dlq_id: int,
    status: str,
    error_message: str | None = None,
    next_retry_delay_sec: float | None = None,
    db_path: Path | str | None = None,
) -> None:
    now = time.time()
    resolved_at = now if status == "resolved" else None
    next_retry_at = (now + next_retry_delay_sec) if next_retry_delay_sec else now
    conn = connect(db_path)
    try:
        with conn:
            conn.execute(
                """UPDATE extraction_dead_letter SET
                     status = ?,
                     retry_count = retry_count + 1,
                     error_message = COALESCE(?, error_message),
                     next_retry_at = ?,
                     resolved_at = COALESCE(?, resolved_at)
                   WHERE id = ?""",
                (status, error_message, next_retry_at, resolved_at, dlq_id),
            )
    finally:
        conn.close()


# --- Domain Throttle State (User Story 6) ---

def get_domain_throttle(domain: str, db_path: Path | str | None = None) -> dict | None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM domain_throttle_state WHERE domain=?", (domain,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def record_domain_request(
    domain: str,
    is_throttled: bool = False,
    backoff_delay: float | None = None,
    db_path: Path | str | None = None,
) -> None:
    now = time.time()
    conn = connect(db_path)
    try:
        with conn:
            existing = conn.execute("SELECT * FROM domain_throttle_state WHERE domain=?", (domain,)).fetchone()
            if not existing:
                consec = 1 if is_throttled else 0
                delay = backoff_delay if backoff_delay else 1.0
                backoff_until = (now + delay) if is_throttled else 0
                conn.execute(
                    """INSERT INTO domain_throttle_state (domain, consecutive_429, current_delay_sec, backoff_until, total_requests, total_throttled, updated_at)
                       VALUES (?, ?, ?, ?, 1, ?, ?)""",
                    (domain, consec, delay, backoff_until, 1 if is_throttled else 0, now),
                )
            else:
                consec = (existing["consecutive_429"] + 1) if is_throttled else 0
                delay = backoff_delay if backoff_delay else (existing["current_delay_sec"] * 2 if is_throttled else 1.0)
                delay = min(delay, 60.0)
                backoff_until = (now + delay) if is_throttled else 0
                throttled_inc = 1 if is_throttled else 0
                conn.execute(
                    """UPDATE domain_throttle_state SET
                         consecutive_429 = ?,
                         current_delay_sec = ?,
                         backoff_until = ?,
                         total_requests = total_requests + 1,
                         total_throttled = total_throttled + ?,
                         updated_at = ?
                       WHERE domain = ?""",
                    (consec, delay, backoff_until, throttled_inc, now, domain),
                )
    finally:
        conn.close()


# --- Operator Authentication ---

def get_operator_user(username: str, db_path: Path | str | None = None) -> dict | None:
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM operator_users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_operator_user(
    username: str, password_hash: str, role: str = "operator", db_path: Path | str | None = None
) -> None:
    now = time.time()
    conn = connect(db_path)
    try:
        with conn:
            conn.execute(
                """INSERT INTO operator_users (username, password_hash, role, created_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, role=excluded.role""",
                (username, password_hash, role, now),
            )
    finally:
        conn.close()
