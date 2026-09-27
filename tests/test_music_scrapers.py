"""Unit and fixture parser tests for music scraper plugins."""

from __future__ import annotations

from models import Category, MediaItem
from sources.music.popmusic import PopMusicPlugin


def test_popmusic_search_parsing(popmusic_search_html: str):
    """Verify track card parsing from real Pop-Music search page fixture."""
    plugin = PopMusicPlugin()
    items = plugin.parse_search_results(popmusic_search_html)

    assert len(items) == 24
    first = items[0]
    assert "محسن میدانی" in first.title
    assert first.page_url.startswith("https://pop-music.ir/")
    assert first.poster_url is not None
    assert first.poster_url.startswith("https://")
    assert first.category == Category.MUSIC
    assert first.source_id == "popmusic"


def test_popmusic_item_stream_and_downloads(popmusic_item_html: str):
    """Verify stream URL and 128k/320k MP3 download extraction from Pop-Music fixture."""
    plugin = PopMusicPlugin()
    target = MediaItem(
        id="pop_test",
        title="محسن میدانی - شهر دودی",
        category=Category.MUSIC,
        source_id="popmusic",
        page_url="https://pop-music.ir/song/",
    )

    plugin.parse_item_page(popmusic_item_html, target)

    assert len(target.music_tracks) == 1
    track = target.music_tracks[0]

    # Stream URL must be present for inline player
    assert track.stream_url is not None
    assert track.stream_url.startswith("https://dl.pop-music.ir/")
    assert track.stream_url.endswith(".mp3")
    assert target.stream_url == track.stream_url

    # Download variants must include 128kbps and 320kbps
    bitrates = [d.bitrate for d in track.downloads]
    assert "128kbps" in bitrates
    assert "320kbps" in bitrates

    for dl in track.downloads:
        assert dl.download_url.startswith("https://")
        assert dl.download_url.endswith(".mp3")
