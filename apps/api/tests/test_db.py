"""Unit tests for the persistent SQLite search index."""

from __future__ import annotations

import tempfile
from pathlib import Path

import db
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


def _db_file() -> Path:
    return Path(tempfile.mkdtemp(prefix="mf-db-")) / "index.db"


def _movie_item() -> MediaItem:
    return MediaItem(
        id="mov-1", title="Interstellar 2014", category=Category.MOVIES,
        source_id="filmplus", page_url="https://example.com/interstellar",
        release_year=2014, poster_url="https://example.com/p.jpg",
        description="A movie about space.",
        movie_variants=[MovieDownloadVariant(
            id="v1", quality="1080p", codec="x265", audio_track="dub",
            download_url="https://example.com/i1080.mkv", file_size_mb=1400.0,
        )],
    )


def _persian_movie() -> MediaItem:
    return MediaItem(
        id="mov-2", title="بازی جادویی دوبله", category=Category.MOVIES,
        source_id="filmplus", page_url="https://example.com/jadui",
    )


def _game_item() -> MediaItem:
    return MediaItem(
        id="game-1", title="GTA V San Andreas", category=Category.GAMES,
        source_id="downloadha", page_url="https://example.com/gta",
        game_releases=[GameRelease(
            id="gta-repack", source_name="downloadha", release_group="FitGirl",
            total_size="60 GB", archive_password="mf",
            parts=[
                GamePartLink(part_number=2, part_label="part2", download_url="https://example.com/p2", file_size="30GB"),
                GamePartLink(part_number=1, part_label="part1", download_url="https://example.com/p1", file_size="30GB"),
            ],
        )],
    )


def _music_item() -> MediaItem:
    return MediaItem(
        id="mus-1", title="Shadmehr", category=Category.MUSIC,
        source_id="popmusic", page_url="https://example.com/shadmehr",
        music_tracks=[MusicTrack(
            id="t1", title="Shadmehr", artist="Shadmehr", source_name="popmusic",
            downloads=[MusicDownloadVariant(bitrate="320", download_url="https://example.com/s320.mp3", file_size="9MB")],
        )],
    )


def _dual_archive_game() -> MediaItem:
    """One post shipping two archives that both number their parts from 1."""
    return MediaItem(
        id="game-2", title="Ready or Not PS5", category=Category.GAMES,
        source_id="downloadha", page_url="https://example.com/ready-or-not",
        game_releases=[
            GameRelease(
                id="game-2_release_0", source_name="downloadha",
                total_size="26 GB", archive_password="mf",
                parts=[
                    GamePartLink(part_number=1, part_label="Part 1", download_url="https://example.com/exfat.part1.rar"),
                    GamePartLink(part_number=2, part_label="Part 2", download_url="https://example.com/exfat.part2.rar"),
                ],
            ),
            GameRelease(
                id="game-2_release_1", source_name="downloadha",
                archive_password="mf",
                parts=[
                    GamePartLink(part_number=1, part_label="Part 1", download_url="https://example.com/pkg.part1.rar"),
                    GamePartLink(part_number=2, part_label="Part 2", download_url="https://example.com/pkg.part2.rar"),
                ],
            ),
        ],
    )


def test_upsert_items_is_idempotent():
    """Re-upserting the same item updates it in place instead of duplicating rows."""
    path = _db_file()
    item = _movie_item()
    assert db.upsert_items([item], path) == 1
    assert db.upsert_items([item], path) == 1

    result = db.stats(path)
    assert result["total"] == 1
    assert result["by_category"] == {"movies": 1}
    assert result["by_source"] == {"filmplus": 1}
    assert result["last_seen"] is not None

    # Child rows are replaced, not accumulated.
    db.upsert_items([item, _game_item(), _music_item()], path)
    found = db.search(Category.MOVIES, "interstellar", db_path=path)
    assert len(found) == 1
    assert len(found[0].movie_variants) == 1
    assert db.stats(path)["total"] == 3


def test_fts_trigram_search_persian():
    """Persian queries match via the trigram tokenizer, across all categories."""
    path = _db_file()
    db.upsert_items([_persian_movie(), _game_item(), _music_item()], path)

    # Multi-token Persian query: every token must appear.
    hits = db.search(Category.MOVIES, "بازی جادویی", db_path=path)
    assert [h.id for h in hits] == ["mov-2"]
    # Partial (sub-word) fragment still matches thanks to trigrams.
    assert [h.id for h in db.search(Category.MOVIES, "جادوی", db_path=path)] == ["mov-2"]
    # A token absent from the item excludes it.
    assert db.search(Category.MOVIES, "جادویی ناموجود", db_path=path) == []
    # Category isolation.
    assert [h.id for h in db.search(Category.GAMES, "gta", db_path=path)] == ["game-1"]
    assert db.search(Category.MUSIC, "gta", db_path=path) == []
    # Game parts round-trip and stay sorted.
    game = db.search(Category.GAMES, "gta", db_path=path)[0]
    assert [p.part_number for p in game.game_releases[0].parts] == [1, 2]
    assert game.game_releases[0].archive_password == "mf"
    # Music rehydrates with its artist and downloads.
    song = db.search(Category.MUSIC, "shadmehr", db_path=path)[0]
    assert song.music_tracks[0].artist == "Shadmehr"
    assert song.music_tracks[0].downloads[0].bitrate == "320"


def test_short_query_falls_back_to_like():
    """Queries under 3 chars cannot be trigrammed, so they use a LIKE scan."""
    path = _db_file()
    db.upsert_items([_persian_movie()], path)

    hits = db.search(Category.MOVIES, "جاد", db_path=path)
    assert [h.id for h in hits] == ["mov-2"]
    # LIKE wildcards in user input are literal, not wildcards.
    assert db.search(Category.MOVIES, "%", db_path=path) == []
    assert db.search(Category.MOVIES, "_", db_path=path) == []
    assert db.search(Category.MOVIES, "   ", db_path=path) == []


def test_hostile_query_input_is_safe():
    """Injection-like input is neutralized by quoting and never raises."""
    path = _db_file()
    db.upsert_items([_movie_item(), _game_item(), _music_item()], path)

    hostile = [
        "' OR 1=1 --", "a-b", '""', '"', "*", "NEAR(a b)", "title_norm : x",
        "a AND b", "a OR b", "(", ")", "\\", "a%b", "a_b", "a;b", "ا OR 1=1",
        "1=1", "*'*", "'; DROP TABLE media_items; --",
    ]
    for q in hostile:
        for cat in (Category.MOVIES, Category.GAMES, Category.MUSIC):
            hits = db.search(cat, q, db_path=path)
            assert isinstance(hits, list), q
            # Nothing may match everything, and the table must survive.
            assert len(hits) < 3, f"{q!r} matched every row"
    assert db.stats(path)["total"] == 3


def test_multiple_archives_round_trip_as_separate_releases():
    """Two archives from one post must not collapse into one merged part list."""
    path = _db_file()
    db.upsert_items([_dual_archive_game()], path)

    found = db.search(Category.GAMES, "ready", db_path=path)
    assert len(found) == 1
    releases = found[0].game_releases
    assert len(releases) == 2, "each archive family is its own release"

    for rel in releases:
        assert [p.part_number for p in rel.parts] == [1, 2]
        assert rel.has_missing_parts is False
        assert len({p.part_number for p in rel.parts}) == len(rel.parts)

    urls = {p.download_url for rel in releases for p in rel.parts}
    assert len(urls) == 4, "no part may be lost or merged"
    # Per-release metadata must not bleed across archives.
    assert [rel.total_size for rel in releases] == ["26 GB", ""]


def test_access_flag_round_trips():
    """A link behind a login wall keeps its flag through the index."""
    path = _db_file()
    item = _movie_item()
    item.movie_variants[0].access = "needs_login"
    game = _dual_archive_game()
    game.game_releases[0].parts[0].access = "needs_login"
    db.upsert_items([item, game], path)

    movie = db.search(Category.MOVIES, "interstellar", db_path=path)[0]
    assert movie.movie_variants[0].access == "needs_login"

    game_found = db.search(Category.GAMES, "ready", db_path=path)[0]
    flagged = [p.access for rel in game_found.game_releases for p in rel.parts]
    assert flagged.count("needs_login") == 1
    assert flagged.count("direct") == 3


def test_access_flag_migration_is_idempotent_on_existing_db():
    """Opening a pre-migration database twice must not raise or duplicate columns."""
    path = _db_file()
    legacy = path.parent / "legacy.db"
    conn = db.connect(legacy)
    try:
        # Simulate the old schema: no access columns at all.
        conn.executescript(
            "DROP TABLE IF EXISTS game_releases;"
        )
        conn.execute("ALTER TABLE download_variants DROP COLUMN access")
        conn.execute("ALTER TABLE game_parts DROP COLUMN access")
        conn.commit()
    finally:
        conn.close()

    for _ in range(2):
        conn = db.connect(legacy)
        try:
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(download_variants)")}
            assert "access" in cols
            parts_cols = {r["name"] for r in conn.execute("PRAGMA table_info(game_parts)")}
            assert "access" in parts_cols
        finally:
            conn.close()


def test_cascade_delete_removes_child_rows():
    """Deleting an item removes its variants, parts, and FTS entry."""
    path = _db_file()
    db.upsert_items([_game_item(), _movie_item()], path)

    conn = db.connect(path)
    try:
        conn.execute("DELETE FROM media_items WHERE id='game-1'")
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM game_parts").fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM search_fts WHERE item_id='game-1'").fetchone()[0] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM download_variants WHERE item_id='mov-1'").fetchone()[0] == 1
    finally:
        conn.close()

    assert db.search(Category.GAMES, "gta", db_path=path) == []


def test_migration_drops_misfiled_game_rows_once():
    """Rows the games scrapers filed as games but filed outside the game sections.

    Fixing parse_search_results is not enough: a row already written stays in the
    index forever, because the fixed scraper never re-emits it to overwrite and
    db.search filters on the stored category. The cleanup runs once, guarded by a
    marker, and must not touch rows that were filed correctly.
    """
    path = _db_file()
    misfiled = MediaItem(
        id="game-ost", title="دانلود موسیقی متن بازی GTA Arena", category=Category.GAMES,
        source_id="downloadha", page_url="https://www.downloadha.com/others/gta-ost/",
        game_releases=[GameRelease(
            id="ost-rel", source_name="downloadha",
            parts=[GamePartLink(part_number=1, part_label="p1", download_url="https://dl/ost.rar")],
        )],
    )
    keep = MediaItem(
        id="game-ok", title="دانلود بازی Elden Ring", category=Category.GAMES,
        source_id="downloadha", page_url="https://www.downloadha.com/game/elden-ring/",
    )
    keep_mobile = MediaItem(
        id="game-apk", title="دانلود بازی PUBG Mobile", category=Category.GAMES,
        source_id="downloadha", page_url="https://www.downloadha.com/mobile/pubg/",
    )
    # YasDL permalinks are flat, so a /game/ predicate would wipe every yasdl row.
    keep_yasdl = MediaItem(
        id="yas-1", title="دانلود بازی American Truck Simulator", category=Category.GAMES,
        source_id="yasdl", page_url="https://www.yasdl.com/105441/x",
    )

    # Seed the rows, then clear the marker: that is the state a pre-fix install is in.
    # Clearing it last matters, because upsert_items itself opens the database and would
    # otherwise run the migration against an empty table and re-burn the marker.
    db.upsert_items([misfiled, keep, keep_mobile, keep_yasdl], path)
    conn = db.connect(path)
    try:
        conn.execute("DELETE FROM schema_meta WHERE key=?", (db._MISFILED_GAME_ROWS,))
        conn.commit()
    finally:
        conn.close()

    db.connect(path).close()  # the migration runs on connect

    conn = db.connect(path)
    try:
        ids = {r["id"] for r in conn.execute("SELECT id FROM media_items")}
        assert "game-ost" not in ids, "the misfiled soundtrack must be gone"
        assert {"game-ok", "game-apk", "yas-1"} <= ids
        # Child rows and the FTS entry follow the delete via cascade and trigger.
        assert conn.execute("SELECT COUNT(*) FROM game_parts WHERE item_id='game-ost'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM search_fts WHERE item_id='game-ost'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM schema_meta WHERE key=?",
                            (db._MISFILED_GAME_ROWS,)).fetchone()[0] == 1
    finally:
        conn.close()

    # Second connect is a no-op, so a row reinserted by hand afterwards survives.
    db.upsert_items([misfiled], path)
    db.connect(path).close()
    conn = db.connect(path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM media_items WHERE id='game-ost'").fetchone()[0] == 1
    finally:
        conn.close()

def test_enrichment_fields_survive_a_db_round_trip():
    """Search results are served from SQLite on a repeat query, so the spec-007 fields
    must persist — otherwise every cached card reads back unspecified/free/unrated."""
    path = _db_file()
    item = _movie_item()
    item.imdb_rating = 8.4
    item.censorship_status = CensorshipStatus.UNCENSORED
    item.source_access_tier = SourceAccessTier.FREEMIUM
    item.movie_variants[0].is_censored = False
    item.movie_variants[0].is_premium = True
    db.upsert_items([item], db_path=path)

    found = db.search(Category.MOVIES, "Interstellar", db_path=path)
    assert len(found) == 1
    back = found[0]
    assert back.imdb_rating == 8.4
    assert back.censorship_status is CensorshipStatus.UNCENSORED
    assert back.source_access_tier is SourceAccessTier.FREEMIUM
    variant = back.movie_variants[0]
    assert variant.is_censored is False
    assert variant.is_premium is True

def test_connect_migrates_a_pre_007_database():
    """An index.db written before the new columns must gain them, not raise."""
    path = _db_file()
    legacy = db.SCHEMA
    for column in ("imdb_rating      REAL,", "censorship_status TEXT,",
                   "source_access_tier TEXT,", "is_censored INT,", "is_premium  INT,"):
        legacy = legacy.replace(column, "")
    import sqlite3
    seed = sqlite3.connect(path)
    seed.executescript(legacy)
    seed.execute(
        "INSERT INTO media_items (id,category,source_id,title,title_norm,artist,page_url,"
        "first_seen,last_seen) VALUES ('old','movies','uptvs','قدیمی','قدیمی','','https://x.com',0,0)"
    )
    seed.execute("INSERT INTO search_fts (title_norm,artist,page_url,item_id) "
                 "VALUES ('قدیمی','','https://x.com','old')")
    seed.commit()
    seed.close()

    conn = db.connect(path)
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(media_items)")}
    assert {"imdb_rating", "censorship_status", "source_access_tier"} <= columns
    conn.close()

    back = db.search(Category.MOVIES, "قدیمی", db_path=path)[0]
    assert back.imdb_rating is None
    assert back.censorship_status is CensorshipStatus.UNSPECIFIED
    assert back.source_access_tier is SourceAccessTier.FREE
