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
    ],
    "download_variants": [
        ("access", "TEXT DEFAULT 'direct'"),
        ("is_censored", "INT"),
        ("is_premium", "INT"),
    ],
    "game_parts": [("access", "TEXT DEFAULT 'direct'")],
    "crawl_state": [("consecutive_failures", "INTEGER NOT NULL DEFAULT 0")],
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
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    _migrate(conn)
    conn.commit()
    return conn
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


def search(category: Category | str, query: str, limit: int = 40,
           db_path: Path | str | None = None,
           max_age_seconds: float | None = None) -> list[MediaItem]:
    """Search the index: trigram FTS for 3+ char queries, LIKE scan for shorter ones.

    `max_age_seconds` drops rows whose `last_seen` is older, letting the caller tell
    "still current" from "indexed a long time ago and never re-checked".
    """
    conn = connect(db_path)
    try:
        norm = normalize_persian_text(query)
        if not norm:
            return []
        cat = _cat(category)
        freshness = ""
        params: list = []
        if max_age_seconds is not None:
            freshness = " AND m.last_seen >= ?"
        if len(norm) >= 3:
            # Trigram tokenizer: each token must be its own quoted phrase, otherwise FTS parses
            # operators/NEAR/column filters straight out of raw user input.
            match = " ".join('"' + tok.replace('"', '""') + '"' for tok in norm.split())
            sql = ("SELECT m.* FROM search_fts f JOIN media_items m ON m.id = f.item_id"
                   " WHERE search_fts MATCH ? AND m.category = ?" + freshness
                   + " ORDER BY m.last_seen DESC LIMIT ?")
            params = [match, cat]
        else:
            like = f"%{_escape_like(norm)}%"
            sql = ("SELECT m.* FROM media_items m WHERE m.category = ?"
                   " AND (m.title_norm LIKE ? ESCAPE '\\' OR m.artist LIKE ? ESCAPE '\\')"
                   + freshness + " ORDER BY m.last_seen DESC LIMIT ?")
            params = [cat, like, like]
        if max_age_seconds is not None:
            params.append(time.time() - max_age_seconds)
        params.append(limit)
        try:
            rows = conn.execute(sql, params).fetchall()
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
