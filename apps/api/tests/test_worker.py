"""Self-check for the crawler worker: db upsert/resume, related-track parse, solver.

Run directly (no pytest needed):
    python apps/api/tests/test_worker.py
"""

from __future__ import annotations

import sys
import tempfile
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
