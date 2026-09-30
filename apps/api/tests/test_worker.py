"""Self-check for the crawler worker: db upsert/resume, related-track parse, solver.

Run directly (no pytest needed):
    python apps/api/tests/test_worker.py
"""

from __future__ import annotations

import sys
import tempfile
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import db
import worker
from models import Category, MediaItem

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _item(item_id: str = "nex_1", title: str = "T", slug: str = "x") -> MediaItem:
    return MediaItem(
        id=item_id,
        title=title,
        category=Category.MUSIC,
        source_id="nex1music",
        page_url=f"https://nex1music.com/{slug}/",
    )


def test_db_upsert_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "t.db"
        conn = db.connect(path)
        try:
            assert db.get_last_page(conn, "nex1music") == 0, "new source must start at page 0"
        finally:
            conn.close()

        assert db.upsert_items([_item("a", slug="one"), _item("b", slug="two")], path) == 2
        assert db.upsert_items([_item("a", title="T2", slug="one")], path) == 1
        assert db.stats(path)["total"] == 2, "upsert must replace, not duplicate"

        # Same page re-crawled under a new id must not leave a stale duplicate row.
        db.upsert_items([_item("a2", slug="one")], path)
        assert db.stats(path)["total"] == 2, "(source_id, page_url) is the natural key"

        conn = db.connect(path)
        try:
            db.set_last_page(conn, "nex1music", 7)
            db.set_last_page(conn, "nex1music", 9)
            assert db.get_last_page(conn, "nex1music") == 9
        finally:
            conn.close()


def test_related_tracks_from_real_fixture() -> None:
    html = (FIXTURES / "nex1music_search.html").read_text(encoding="utf-8", errors="replace")
    post = "https://nex1music.com/music/"
    items = worker.parse_related_tracks(html, post)

    assert len(items) == 50, f"expected the 50 div.item blocks, got {len(items)}"
    first = items[0]
    assert first.stream_url and first.stream_url.startswith("https://dl.nex1music.com/")
    assert first.title.startswith("محسن رضایی")

    # page_url is a natural key in the db, so shared page_urls would collapse these.
    assert len({i.page_url for i in items}) == len(items), "each related track needs a unique page_url"
    assert len({i.id for i in items}) == len(items)

    # IDs must be stable across calls, else every run duplicates rows.
    again = worker.parse_related_tracks(html, post)
    assert [i.id for i in again] == [i.id for i in items], "related-track ids must be deterministic"


def test_related_track_stream_urls_are_percent_encoded() -> None:
    """data-music carries raw spaces and brackets; the stored URL must be usable."""
    html = (
        '<div class="item" data-artist="Behnam Bani" '
        'data-track="Ashegham Karde" '
        'data-music="https://dl.nex1music.com/1395/12/21/Behnam Bani - Ashegham Karde [128].mp3">'
    )
    items = worker.parse_related_tracks(html, "https://nex1music.com/music/", "nex1music")

    assert len(items) == 1
    stream = items[0].stream_url
    assert stream and " " not in stream, "raw spaces make the URL unusable"
    assert "[" not in stream and "]" not in stream
    assert "%20" in stream and "%5B128%5D" in stream
    # And it must survive a real HTTP client's URL parser.
    assert urllib.parse.urlsplit(stream).path.endswith(".mp3")


def test_related_track_builds_a_usable_music_track() -> None:
    """Without a MusicTrack the web client disables play and renders no downloads."""
    html = (
        '<div class="item" data-artist="Behnam Bani" '
        'data-track="Ashegham Karde" '
        'data-music="https://dl.nex1music.com/a/Ashegham Karde [128].mp3">'
    )
    items = worker.parse_related_tracks(html, "https://nex1music.com/music/", "nex1music")

    assert len(items[0].music_tracks) == 1
    track = items[0].music_tracks[0]
    assert track.artist == "Behnam Bani"
    assert track.stream_url and track.stream_url == items[0].stream_url
    assert len(track.downloads) == 1


def test_crawl_enriches_the_posts_own_card() -> None:
    """A crawled post must come back with its downloads, not as a bare listing card.

    Listing-page cards carry no music_tracks, so persisting them unenriched is what
    left the whole music category without links.
    """
    plugin = worker.Nex1MusicPlugin()
    post_html = (
        '<div class="post anm"><h2><a href="https://nex1music.com/track/">'
        "<b>Behnam Bani</b> - Ashegham Karde</a></h2>"
        '<div class="plike" rel="739999"></div></div>'
        '<a href="https://dl.nex1music.com/a/Ashegham%20Karde%20%5B128%5D.mp3">'
        '<div class="dllink">128</div></a>'
    )
    post_url = "https://nex1music.com/track/"
    cards = plugin.parse_search_results(post_html)
    matching = worker.match_post_card(cards, post_url)
    assert matching is not None, "the post's own card must be found on its own page"
    plugin.parse_item_page(post_html, matching)
    assert len(matching.music_tracks) == 1
    assert matching.music_tracks[0].stream_url


def test_challenge_detection() -> None:
    assert worker._is_challenge("<title>Just a moment...</title>") is True
    assert worker._is_challenge("<div>normal music page</div>") is False


def test_solve_url_falls_back_without_flaresolverr() -> None:
    # No FlareSolverr listening -> direct GET path; a bad host must not raise.
    assert worker.solve_url("http://127.0.0.1:1/nope", timeout=1.0) is None


def main() -> int:
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("all worker checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
