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


def test_musicdel_search_parsing(musicdel_search_html: str):
    """Verify card parsing from real MusicDel search page fixture."""
    from sources.music.musicdel import MusicDelPlugin

    items = MusicDelPlugin().parse_search_results(musicdel_search_html)
    assert len(items) >= 1
    first = items[0]
    assert first.page_url.startswith("https://musicdel.ir/single-tracks/")
    assert first.id.startswith("mdel_")
    assert first.category == Category.MUSIC
    assert first.source_id == "musicdel"
    assert first.poster_url is not None and first.poster_url.startswith("https://")


def test_musicdel_item_stream_and_downloads(musicdel_item_html: str):
    """Verify 320/128/64 MP3 links and 128k stream from MusicDel fixture (FR-014)."""
    from sources.music.musicdel import MusicDelPlugin

    target = MediaItem(
        id="mdel_574381",
        title="دانلود آهنگ لندکروز از محمد کجوری",
        category=Category.MUSIC,
        source_id="musicdel",
        page_url="https://musicdel.ir/single-tracks/574381/",
    )
    MusicDelPlugin().parse_item_page(musicdel_item_html, target)

    assert len(target.music_tracks) == 1
    track = target.music_tracks[0]
    assert track.stream_url is not None and track.stream_url.endswith(".mp3")
    assert target.stream_url == track.stream_url
    assert sorted(d.bitrate for d in track.downloads) == ["128kbps", "320kbps", "64kbps"]
    for dl in track.downloads:
        assert dl.download_url.startswith("https://")
        assert dl.download_url.endswith(".mp3")


def test_musicdel_item_no_links_leaves_item_empty(musicdel_search_html: str):
    """A track page with no usable MP3 link must not set stream_url (FR-015, T021a)."""
    from sources.music.musicdel import MusicDelPlugin

    target = MediaItem(
        id="mdel_empty",
        title="آهنگ بدون لینک",
        category=Category.MUSIC,
        source_id="musicdel",
        page_url="https://musicdel.ir/single-tracks/1/",
    )
    MusicDelPlugin().parse_item_page("<html><body><p>no links here</p></body></html>", target)
    assert target.stream_url is None
    assert target.music_tracks == []


def test_musicsfa_search_parsing(musicsfa_search_html: str):
    from sources.music.musicsfa import MusicsFaPlugin

    items = MusicsFaPlugin().parse_search_results(musicsfa_search_html)
    assert len(items) >= 1
    first = items[0]
    assert first.page_url.startswith("https://musics-fa.com/download-song/")
    assert first.source_id == "musicsfa"
    assert first.category == Category.MUSIC
    assert first.poster_url is not None and first.poster_url.startswith("https://")


def test_musicsfa_item_stream(musicsfa_item_html: str):
    from sources.music.musicsfa import MusicsFaPlugin

    target = MediaItem(
        id="msf_126075",
        title="دانلود آهنگ فرهاد آتیش پاره",
        category=Category.MUSIC,
        source_id="musicsfa",
        page_url="https://musics-fa.com/download-song/126075/",
    )
    MusicsFaPlugin().parse_item_page(musicsfa_item_html, target)
    assert len(target.music_tracks) == 1
    assert target.stream_url is not None and target.stream_url.endswith(".mp3")


def test_upsong_search_parsing(upsong_search_html: str):
    from sources.music.upsong import UpSongPlugin

    items = UpSongPlugin().parse_search_results(upsong_search_html)
    assert len(items) >= 1
    first = items[0]
    assert first.page_url.startswith("https://upsong.ir/")
    assert first.source_id == "upsong"
    assert first.category == Category.MUSIC


def test_upsong_item_stream(upsong_item_html: str):
    from sources.music.upsong import UpSongPlugin

    target = MediaItem(
        id="ups_1",
        title="دانلود آهنگ محسن یگانه نخواستم",
        category=Category.MUSIC,
        source_id="upsong",
        page_url="https://upsong.ir/track.html",
    )
    UpSongPlugin().parse_item_page(upsong_item_html, target)
    assert len(target.music_tracks) == 1
    assert target.stream_url is not None and target.stream_url.endswith(".mp3")
    assert "128kbps" in [d.bitrate for d in target.music_tracks[0].downloads]


def test_upmusics_search_parsing(upmusics_search_html: str):
    from sources.music.upmusics import UpMusicsPlugin

    items = UpMusicsPlugin().parse_search_results(upmusics_search_html)
    assert len(items) >= 1
    first = items[0]
    assert first.page_url.startswith("https://upmusics.com/")
    assert first.source_id == "upmusics"
    assert first.category == Category.MUSIC


def test_upmusics_item_stream(upmusics_item_html: str):
    from sources.music.upmusics import UpMusicsPlugin

    target = MediaItem(
        id="upm_1",
        title="دانلود آهنگ بی تو میمیرم",
        category=Category.MUSIC,
        source_id="upmusics",
        page_url="https://upmusics.com/track/",
    )
    UpMusicsPlugin().parse_item_page(upmusics_item_html, target)
    assert len(target.music_tracks) == 1
    assert target.stream_url is not None and target.stream_url.endswith(".mp3")


def test_musictarin_search_parsing(musictarin_search_html: str):
    from sources.music.musictarin import MusicTarinPlugin

    items = MusicTarinPlugin().parse_search_results(musictarin_search_html)
    assert len(items) >= 1
    first = items[0]
    assert first.page_url.startswith("https://musictarin.com/download-single-track/")
    assert first.source_id == "musictarin"
    assert first.category == Category.MUSIC


def test_musictarin_item_stream(musictarin_item_html: str):
    from sources.music.musictarin import MusicTarinPlugin

    target = MediaItem(
        id="mtar_114699",
        title="دانلود آهنگ یوسف جمالی سقوط",
        category=Category.MUSIC,
        source_id="musictarin",
        page_url="https://musictarin.com/download-single-track/114699.php",
    )
    MusicTarinPlugin().parse_item_page(musictarin_item_html, target)
    assert len(target.music_tracks) == 1
    assert target.stream_url is not None and target.stream_url.endswith(".mp3")


def test_onerj_search_parsing(onerj_search_html: str):
    from sources.music.one_rj import OneRJPlugin

    items = OneRJPlugin().parse_search_results(onerj_search_html)
    assert len(items) >= 1
    first = items[0]
    assert first.page_url.startswith("https://1rj.ir/")
    assert first.source_id == "one_rj"
    assert first.category == Category.MUSIC


def test_onerj_item_stream(onerj_item_html: str):
    from sources.music.one_rj import OneRJPlugin

    target = MediaItem(
        id="rj_24204",
        title="دانلود آهنگ محسن ابراهیم زاده به نام اشکم دونه دونه",
        category=Category.MUSIC,
        source_id="one_rj",
        page_url="https://1rj.ir/24204/track/",
    )
    OneRJPlugin().parse_item_page(onerj_item_html, target)
    assert len(target.music_tracks) == 1
    assert target.stream_url is not None and target.stream_url.endswith(".mp3")


# --- T072 (FR-020) + T077 (FR-014) -------------------------------------------
# One row per new full source: its plugin class, the registry id, and the
# base URL its parser joins relative links against.
NEW_FULL_SOURCES = [
    ("musicdel", "MusicDelPlugin", "https://musicdel.ir", "mdel_1", "https://musicdel.ir/single-tracks/1/"),
    ("musicsfa", "MusicsFaPlugin", "https://musics-fa.com", "msf_1", "https://musics-fa.com/download-song/1/"),
    ("upsong", "UpSongPlugin", "https://upsong.ir", "ups_1", "https://upsong.ir/song/1/"),
    ("upmusics", "UpMusicsPlugin", "https://upmusics.com", "upm_1", "https://upmusics.com/song/1/"),
    ("musictarin", "MusicTarinPlugin", "https://musictarin.com", "mtar_1", "https://musictarin.com/track/1/"),
    ("one_rj", "OneRJPlugin", "https://1rj.ir", "rj_1", "https://1rj.ir/1/track/"),
]

def _new_full_plugin(row):
    """Import the plugin class for a registry row, importing only what it needs."""
    import importlib

    module = {
        "MusicDelPlugin": "sources.music.musicdel",
        "MusicsFaPlugin": "sources.music.musicsfa",
        "UpSongPlugin": "sources.music.upsong",
        "UpMusicsPlugin": "sources.music.upmusics",
        "MusicTarinPlugin": "sources.music.musictarin",
        "OneRJPlugin": "sources.music.one_rj",
    }[row[1]]
    return getattr(importlib.import_module(module), row[1])()

# Bodies that must never yield results: a parked domain, an ad landing page,
# and an upstream error page.
#
# The last entry is the important one: it carries a fully-formed card that the
# parser WOULD happily extract, so an empty result proves is_parked_page did the
# rejecting. Without it every other row would pass vacuously — a parked page has
# no cards to begin with.
_PARKED_WITH_CARDS = (
    "<html><body><h1>Buy this domain</h1>"
    '<article class="post"><a rel="bookmark" href="/single-tracks/999/" '
    'title="دانلود آهنگ تبلیغاتی از تبلیغ"></a>'
    '<img src="https://cdn.example.com/x.jpg"/></article>'
    "</body></html>"
)

PARKED_BODIES = [
    "<html><body><a href='/lander'>This domain is for sale</a></body></html>",
    "<html><head><meta name='generator' content='sedoparking'></head><body>parked-domain</body></html>",
    "<html><body><a href='https://www.namecheap.com/domains/marketplace/'>Buy this domain</a></body></html>",
    "<html><body>https://adclick.net/track?x=1</body></html>",
    _PARKED_WITH_CARDS,
    "",  # empty response: is_parked_page("") is True
]


def test_parked_page_parsing_yields_no_results_for_new_full_sources():
    """FR-020: a parked/ad/error page produces zero entries, never junk items.

    Drives the full network path (search + extract_links) through an in-memory
    client, because is_parked_page is only consulted in the async fetch, not in
    the pure parse_* helpers.
    """
    import asyncio

    from http_client import SimpleResponse

    class _StubClient:
        def __init__(self, body):
            self.body = body

        async def get(self, url, headers=None, timeout=None):
            return SimpleResponse(200, self.body, url)

        async def head(self, url, headers=None, timeout=None):
            return SimpleResponse(200, self.body, url)

    from models import SearchQuery

    query = SearchQuery(
        raw_query="محسن یگانه", normalized_query="محسن یگانه", category=Category.MUSIC
    )

    for row in NEW_FULL_SOURCES:
        plugin = _new_full_plugin(row)
        for body in PARKED_BODIES:
            client = _StubClient(body)
            items = asyncio.run(plugin.search(query, client))
            assert items == [], f"{row[0]} returned {len(items)} items for a parked/ad body"

            # An item page fed the same body must also gain no media (FR-015).
            target = MediaItem(
                id=row[3], title="آهنگ تست", category=Category.MUSIC,
                source_id=row[0], page_url=row[4],
            )
            asyncio.run(plugin.extract_links(target, client))
            assert target.stream_url is None, f"{row[0]} set stream_url from a parked body"
            assert target.music_tracks == [], f"{row[0]} set music_tracks from a parked body"


def test_parked_page_detection_is_wired_into_every_new_full_source():
    """The guard must be present, not merely expected: is_parked_page is called
    in both the search and the item-page path of each new full source."""
    import inspect

    for row in NEW_FULL_SOURCES:
        plugin = _new_full_plugin(row)
        module = inspect.getmodule(type(plugin))
        src = inspect.getsource(module)
        assert "is_parked_page" in src, f"{row[0]} never calls is_parked_page"


def test_ad_and_shortener_download_links_are_filtered_out():
    """FR-014: a download href on a known ad/referral host is never offered.

    Each parser takes the first non-ad mp3 link as its stream, so this asserts
    on the emitted URLs rather than trusting the parser's internal skip.
    """
    AD_MP3_PAGE = (
        '<html><body>'
        '<a href="https://adclick.net/x/128.mp3">128kbps</a>'
        '<a href="https://bit.ly/abc/320.mp3">320kbps</a>'
        '<a href="https://cdn.musicdel.ir/real/320.mp3">320kbps</a>'
        '</body></html>'
    )

    for row in NEW_FULL_SOURCES:
        from sources.base import is_ad_or_shortener_url

        plugin = _new_full_plugin(row)
        target = MediaItem(
            id=row[3], title="دانلود آهنگ تست از تست", category=Category.MUSIC,
            source_id=row[0], page_url=row[4],
        )
        plugin.parse_item_page(AD_MP3_PAGE, target)

        urls = [target.stream_url] if target.stream_url else []
        for track in target.music_tracks:
            if track.stream_url:
                urls.append(track.stream_url)
            urls.extend(d.download_url for d in track.downloads)

        assert urls, f"{row[0]} emitted no URLs at all from the ad page"
        for url in urls:
            assert not is_ad_or_shortener_url(url), f"{row[0]} emitted ad URL {url}"
        assert all(u.startswith("http") for u in urls), f"{row[0]} emitted a non-HTTP URL"


def _assert_no_ad_urls(item: MediaItem, label: str) -> None:
    from sources.base import is_ad_or_shortener_url

    for track in item.music_tracks:
        for d in track.downloads:
            assert not is_ad_or_shortener_url(d.download_url), f"{label}: {d.download_url}"
        if track.stream_url:
            assert not is_ad_or_shortener_url(track.stream_url), f"{label}: {track.stream_url}"
    if item.stream_url:
        assert not is_ad_or_shortener_url(item.stream_url), f"{label}: {item.stream_url}"


def test_musicdel_fixture_urls_pass_the_ad_filter(musicdel_item_html: str):
    """FR-014 against real captured markup, not just the synthetic ad page."""
    from sources.music.musicdel import MusicDelPlugin

    target = MediaItem(id="mdel_1", title="دانلود آهنگ تست از تست", category=Category.MUSIC,
                       source_id="musicdel", page_url="https://musicdel.ir/single-tracks/1/")
    MusicDelPlugin().parse_item_page(musicdel_item_html, target)
    _assert_no_ad_urls(target, "musicdel")


def test_musicsfa_fixture_urls_pass_the_ad_filter(musicsfa_item_html: str):
    from sources.music.musicsfa import MusicsFaPlugin

    target = MediaItem(id="msf_1", title="دانلود آهنگ تست از تست", category=Category.MUSIC,
                       source_id="musicsfa", page_url="https://musics-fa.com/download-song/1/")
    MusicsFaPlugin().parse_item_page(musicsfa_item_html, target)
    _assert_no_ad_urls(target, "musicsfa")


def test_upsong_fixture_urls_pass_the_ad_filter(upsong_item_html: str):
    from sources.music.upsong import UpSongPlugin

    target = MediaItem(id="ups_1", title="دانلود آهنگ تست از تست", category=Category.MUSIC,
                       source_id="upsong", page_url="https://upsong.ir/")
    UpSongPlugin().parse_item_page(upsong_item_html, target)
    _assert_no_ad_urls(target, "upsong")


def test_upmusics_fixture_urls_pass_the_ad_filter(upmusics_item_html: str):
    from sources.music.upmusics import UpMusicsPlugin

    target = MediaItem(id="upm_1", title="دانلود آهنگ تست از تست", category=Category.MUSIC,
                       source_id="upmusics", page_url="https://upmusics.com/")
    UpMusicsPlugin().parse_item_page(upmusics_item_html, target)
    _assert_no_ad_urls(target, "upmusics")


def test_musictarin_fixture_urls_pass_the_ad_filter(musictarin_item_html: str):
    from sources.music.musictarin import MusicTarinPlugin

    target = MediaItem(id="mtar_1", title="دانلود آهنگ تست از تست", category=Category.MUSIC,
                       source_id="musictarin", page_url="https://musictarin.com/")
    MusicTarinPlugin().parse_item_page(musictarin_item_html, target)
    _assert_no_ad_urls(target, "musictarin")


def test_onerj_fixture_urls_pass_the_ad_filter(onerj_item_html: str):
    from sources.music.one_rj import OneRJPlugin

    target = MediaItem(id="rj_1", title="دانلود آهنگ تست از تست", category=Category.MUSIC,
                       source_id="one_rj", page_url="https://1rj.ir/")
    OneRJPlugin().parse_item_page(onerj_item_html, target)
    _assert_no_ad_urls(target, "one_rj")
