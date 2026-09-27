"""Unit and fixture parser tests for music scraper plugins."""

from __future__ import annotations

from models import Category, MediaItem
from sources.music.nex1music import Nex1MusicPlugin
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


def test_nex1music_search_parsing(nex1music_search_html: str):
    """Verify post card parsing from real Nex1Music search page fixture."""
    plugin = Nex1MusicPlugin()
    items = plugin.parse_search_results(nex1music_search_html)

    assert len(items) == 5
    first = items[0]
    assert "محسن رضایی" in first.title
    assert first.page_url.startswith("https://nex1music.com/")
    # Post ID comes from the like counter's rel attribute, not the URL slug.
    assert first.id == "nex_739671"
    # Poster must be a real cover image, not a theme icon under /themev4/.
    assert first.poster_url is not None
    assert first.poster_url.startswith("https://")
    assert "/themev4/" not in first.poster_url
    assert first.category == Category.MUSIC
    assert first.source_id == "nex1music"


def test_nex1music_item_stream_and_downloads(nex1music_item_html: str):
    """Verify 320k/128k/64k MP3 links and 128k stream from Nex1Music fixture."""
    plugin = Nex1MusicPlugin()
    target = MediaItem(
        id="nex_739671",
        title="دانلود آهنگ محسن رضایی به نام شغل خوانندگی",
        category=Category.MUSIC,
        source_id="nex1music",
        page_url="https://nex1music.com/%d8%a2%d9%87%d9%86%da%af/",
    )

    plugin.parse_item_page(nex1music_item_html, target)

    assert len(target.music_tracks) == 1
    track = target.music_tracks[0]

    # Artist and title come from the ld+json MusicRecording block.
    assert track.artist == "محسن رضایی"
    assert track.title == "شغل خوانندگی"

    # Stream must be the 128k direct link, mirrored onto the item.
    assert track.stream_url is not None
    assert track.stream_url.startswith("https://dl.nex1music.com/")
    assert track.stream_url.endswith(".mp3")
    assert "%5B128%5D" in track.stream_url
    assert target.stream_url == track.stream_url

    bitrates = [d.bitrate for d in track.downloads]
    assert sorted(bitrates) == ["128kbps", "320kbps", "64kbps"]

    for dl in track.downloads:
        assert dl.download_url.startswith("https://")
        assert dl.download_url.endswith(".mp3")
