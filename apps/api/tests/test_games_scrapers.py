"""Unit and fixture parser tests for game scraper plugins."""

from __future__ import annotations

from models import Category
from sources.games.downloadha import DownloadhaPlugin


def test_downloadha_search_parsing(downloadha_search_html: str):
    """Verify item extraction from real Downloadha search page fixture."""
    plugin = DownloadhaPlugin()
    items = plugin.parse_search_results(downloadha_search_html)

    assert len(items) == 10
    # First item
    first = items[0]
    assert "GTA Online Arena War" in first.title
    assert first.page_url.startswith("https://www.downloadha.com/")
    assert first.category == Category.GAMES
    assert first.source_id == "downloadha"

    # Verify game repack item
    game_item = next(it for it in items if "L.A Noire" in it.title)
    assert "ElAmigos" in game_item.title
    assert "l-a-noire" in game_item.page_url


def test_downloadha_item_link_extraction(downloadha_item_html: str):
    """Verify split RAR parts and password extraction from Downloadha post fixture."""
    plugin = DownloadhaPlugin()
    items = plugin.parse_search_results(downloadha_item_html)
    # Target item
    target = items[0] if items else plugin.parse_search_results("<h1 class='entry-title'><a href='https://www.downloadha.com/game/l-a-noire/'>L.A Noire - ElAmigos</a></h1>")[0]

    plugin.parse_item_page(downloadha_item_html, target)

    assert len(target.game_releases) == 1
    rel = target.game_releases[0]
    assert rel.release_group == "ElAmigos"
    assert rel.archive_password == "www.downloadha.com"
    assert rel.total_size == "13.4 گیگابایت"
    assert len(rel.parts) == 5

    # Invariant: Parts strictly ascending 1..5 with no gaps
    part_numbers = [p.part_number for p in rel.parts]
    assert part_numbers == [1, 2, 3, 4, 5]
    assert rel.has_missing_parts is False
    assert rel.missing_part_numbers == []

    # Verify direct download URLs
    for part in rel.parts:
        assert part.download_url.startswith("https://")
        assert ".rar" in part.download_url


def test_downloadha_gap_detection_on_missing_parts():
    """Verify missing parts are flagged when an upstream site has missing segments."""
    plugin = DownloadhaPlugin()
    mock_html = """
    <div class='download-box'>
        <a href='https://dl.example.com/game.part1.rar'>دانلود پارت 1 با لینک مستقیم</a>
        <a href='https://dl.example.com/game.part2.rar'>دانلود پارت 2 با لینک مستقیم</a>
        <a href='https://dl.example.com/game.part4.rar'>دانلود پارت 4 با لینک مستقیم</a>
        <p>رمز فایل: www.downloadha.com</p>
    </div>
    """
    item = plugin.parse_search_results("<h1 class='entry-title'><a href='https://www.downloadha.com/game/test/'>Test Game FitGirl</a></h1>")[0]
    plugin.parse_item_page(mock_html, item)

    assert len(item.game_releases) == 1
    rel = item.game_releases[0]
    assert rel.has_missing_parts is True
    assert rel.missing_part_numbers == [3]


def test_downloadha_item_no_password():
    """Verify that pages without password labels do not fabricate arbitrary domain passwords."""
    plugin = DownloadhaPlugin()
    mock_html = """
    <div class='download-box'>
        <a href='https://dl.example.com/game.part1.rar'>دانلود پارت 1 با لینک مستقیم</a>
        <p>برای دریافت اطلاعات بیشتر به سایت www.other-site.com مراجعه کنید.</p>
    </div>
    """
    item = plugin.parse_search_results("<h1 class='entry-title'><a href='https://www.downloadha.com/game/test/'>Test Game FitGirl</a></h1>")[0]
    plugin.parse_item_page(mock_html, item)

    assert len(item.game_releases) == 1
    rel = item.game_releases[0]
    assert rel.archive_password == ""
