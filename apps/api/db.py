"""Persistent local search index built on stdlib sqlite3 only."""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

from cache import normalize_persian_text
from models import (
    Category,
    GamePartLink,
    GameRelease,
    MediaItem,
    MovieDownloadVariant,
    MusicDownloadVariant,
    MusicTrack,
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
    stream_url       TEXT,
    release_group    TEXT,
    archive_password TEXT,
    total_size       TEXT,
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
    url         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS game_parts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     TEXT NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
    release_id  TEXT,
    part_number INT NOT NULL,
    part_label  TEXT,
    file_size   TEXT,
    url         TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
    title_norm, artist, page_url, item_id UNINDEXED, tokenize='trigram'
);
CREATE TABLE IF NOT EXISTS crawl_state (
    source_id  TEXT PRIMARY KEY,
    last_page  INT NOT NULL DEFAULT 0,
    last_crawl REAL
);
CREATE INDEX IF NOT EXISTS idx_items_category ON media_items(category);
-- FTS has no foreign keys, so keep the index in sync with deletes.
CREATE TRIGGER IF NOT EXISTS trg_fts_delete AFTER DELETE ON media_items BEGIN
    DELETE FROM search_fts WHERE item_id = old.id;
END;
"""


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open (and initialize) the index database."""
    raw = db_path or os.environ.get("MOVIE_FETCHER_DB") or DEFAULT_DB_PATH
    path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
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
                     None, v.download_url))
    for t in item.music_tracks:
        for d in t.downloads:
            rows.append((item.id, "music", d.bitrate, None, None, None, d.file_size, d.download_url))
    return rows


def _part_rows(item: MediaItem) -> list[tuple]:
    return [(item.id, r.id, p.part_number, p.part_label, p.file_size, p.download_url)
            for r in item.game_releases for p in r.parts]


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
                        release_year, description, stream_url, release_group, archive_password,
                        total_size, first_seen, last_seen)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         category=excluded.category, title=excluded.title,
                         title_norm=excluded.title_norm, artist=excluded.artist,
                         poster_url=excluded.poster_url, release_year=excluded.release_year,
                         description=excluded.description, stream_url=excluded.stream_url,
                         release_group=excluded.release_group, archive_password=excluded.archive_password,
                         total_size=excluded.total_size,
                         first_seen=MIN(media_items.first_seen, excluded.first_seen),
                         last_seen=excluded.last_seen""",
                    (item.id, _cat(item.category), item.source_id, item.title,
                     normalize_persian_text(item.title), artist, item.page_url, item.poster_url,
                     item.release_year, item.description, item.stream_url,
                     game.release_group if game else None,
                     game.archive_password if game else None,
                     game.total_size if game else None,
                     now, now),
                )
                conn.execute("DELETE FROM download_variants WHERE item_id=?", (item.id,))
                conn.executemany(
                    "INSERT INTO download_variants (item_id, kind, label, codec, audio_track,"
                    " size_bytes, size_text, url) VALUES (?,?,?,?,?,?,?,?)",
                    _variant_rows(item),
                )
                conn.execute("DELETE FROM game_parts WHERE item_id=?", (item.id,))
                conn.executemany(
                    "INSERT INTO game_parts (item_id, release_id, part_number, part_label, file_size, url)"
                    " VALUES (?,?,?,?,?,?)",
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


def _rehydrate(conn: sqlite3.Connection, row: sqlite3.Row) -> MediaItem:
    """Rebuild a typed MediaItem from its row plus child rows."""
    # ponytail: 2 extra queries per result; batch-load child rows if result sets grow past ~100.
    variants = conn.execute(
        "SELECT * FROM download_variants WHERE item_id=? ORDER BY id", (row["id"],)
    ).fetchall()
    parts = conn.execute(
        "SELECT * FROM game_parts WHERE item_id=? ORDER BY part_number", (row["id"],)
    ).fetchall()

    movies = [
        MovieDownloadVariant(
            id=f"{row['id']}:{v['id']}", quality=v["label"] or "", codec=v["codec"] or "",
            audio_track=v["audio_track"] or "", download_url=v["url"],
            file_size_mb=float(v["size_bytes"]) if v["size_bytes"] is not None else None,
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
            MusicDownloadVariant(bitrate=v["label"] or "", download_url=v["url"], file_size=v["size_text"])
        )

    releases = []
    if parts:
        releases.append(GameRelease(
            id=parts[0]["release_id"] or row["id"], source_name=row["source_id"],
            release_group=row["release_group"] or "", total_size=row["total_size"] or "",
            archive_password=row["archive_password"] or "",
            parts=[GamePartLink(part_number=p["part_number"], part_label=p["part_label"] or "",
                                download_url=p["url"], file_size=p["file_size"]) for p in parts],
        ))

    return MediaItem(
        id=row["id"], title=row["title"], category=Category(row["category"]),
        source_id=row["source_id"], page_url=row["page_url"],
        release_year=row["release_year"], poster_url=row["poster_url"],
        description=row["description"], stream_url=row["stream_url"],
        movie_variants=movies, game_releases=releases, music_tracks=tracks,
    )


def search(category: Category | str, query: str, limit: int = 40,
           db_path: Path | str | None = None) -> list[MediaItem]:
    """Search the index: trigram FTS for 3+ char queries, LIKE scan for shorter ones."""
    conn = connect(db_path)
    try:
        norm = normalize_persian_text(query)
        if not norm:
            return []
        cat = _cat(category)
        if len(norm) >= 3:
            # Trigram tokenizer: each token must be its own quoted phrase, otherwise FTS parses
            # operators/NEAR/column filters straight out of raw user input.
            match = " ".join('"' + tok.replace('"', '""') + '"' for tok in norm.split())
            sql = ("SELECT m.* FROM search_fts f JOIN media_items m ON m.id = f.item_id"
                   " WHERE search_fts MATCH ? AND m.category = ? ORDER BY m.last_seen DESC LIMIT ?")
            params: tuple = (match, cat, limit)
        else:
            like = f"%{_escape_like(norm)}%"
            sql = ("SELECT m.* FROM media_items m WHERE m.category = ?"
                   " AND (m.title_norm LIKE ? ESCAPE '\\' OR m.artist LIKE ? ESCAPE '\\')"
                   " ORDER BY m.last_seen DESC LIMIT ?")
            params = (cat, like, like, limit)
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
