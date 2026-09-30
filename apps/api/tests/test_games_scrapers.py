"""Unit and fixture parser tests for game scraper plugins."""

from __future__ import annotations

from urllib.parse import urlparse

from models import Category
from sources.games.downloadha import DownloadhaPlugin
from sources.games.yasdl import YasDLPlugin


def test_downloadha_search_parsing(downloadha_search_html: str):
    """Verify item extraction from real Downloadha search page fixture."""
    plugin = DownloadhaPlugin()
    items = plugin.parse_search_results(downloadha_search_html)

    # The fixture's 10 cards yield 9 items: a task-manager app is not media and is
    # dropped, while the soundtrack is kept but filed under music so it stays
    # findable in the موسیقی tab instead of surfacing as a game.
    assert len(items) == 9
    assert [i.category for i in items].count(Category.GAMES) == 8
    assert [i.category for i in items].count(Category.MUSIC) == 1

    # First game item
    first = next(i for i in items if i.category == Category.GAMES)
    assert "Ragtag Adventurers" in first.title
    assert first.page_url.startswith("https://www.downloadha.com/")
    assert first.category == Category.GAMES
    assert first.source_id == "downloadha"

    # Verify game repack item
    game_item = next(it for it in items if "L.A Noire" in it.title)
    assert "ElAmigos" in game_item.title
    assert "l-a-noire" in game_item.page_url


def test_downloadha_keeps_only_posts_the_url_calls_games(downloadha_search_html: str):
    """Every game card must sit in the `/game/` section, or `/mobile/` with بازی.

    This is the invariant, not a count: Downloadha's search page is multi-section
    (`/game/`, `/mobile/`, `/others/`, `/movies/`), and the reported bug was a
    soundtrack surfacing in the games tab. A title marker cannot catch that post --
    its title *contains* بازی -- so the URL section is what has to hold.
    """
    items = DownloadhaPlugin().parse_search_results(downloadha_search_html)

    assert items, "fixture must still yield games"
    for item in items:
        # Soundtracks are emitted as Category.MUSIC precisely so they are indexed
        # under music; they legitimately live in /others/. The invariant is that
        # nothing *filed as a game* escapes the game sections.
        if item.category != Category.GAMES:
            continue
        section = [p for p in urlparse(item.page_url).path.split("/") if p][0]
        assert section == "game" or (section == "mobile" and "بازی" in item.title), (
            f"{item.title!r} at {item.page_url} is not a game post"
        )

    titles = [i.title for i in items if i.category == Category.GAMES]
    # The soundtrack is about a game, so it carries the game marker in its title.
    assert not any("Arena War" in t for t in titles), "GTA OST must not reach the games tab"
    assert not any("GTasks" in t for t in titles)


def test_downloadha_keeps_android_games_filed_under_mobile():
    """Android games live under `/mobile/` too, so the section gate needs the carve-out."""
    items = DownloadhaPlugin().parse_search_results(
        "<h1 class='entry-title'><a href='https://www.downloadha.com/mobile/pubg-mobile/'>"
        "دانلود بازی PUBG Mobile برای اندروید</a></h1>"
    )
    assert len(items) == 1
    assert items[0].category == Category.GAMES


def test_downloadha_keeps_games_whose_titles_collide_with_software_terms():
    """`شبیه ساز` ("simulator") is a substring of بازی شبیه ساز ("simulation game").

    Euro Truck Simulator 2 was dropped by the software list before this guard existed.
    """
    items = DownloadhaPlugin().parse_search_results(
        "<h1 class='entry-title'><a href='https://www.downloadha.com/game/ets2/'>"
        "دانلود بازی Euro Truck Simulator 2 - بازی شبیه ساز رانندگی</a></h1>"
    )
    assert len(items) == 1
    assert "Euro Truck" in items[0].title


def test_yasdl_keeps_only_game_posts():
    """YasDL permalinks are flat, so the title is the only signal there."""
    items = YasDLPlugin().parse_search_results(
        "<h2 class='col post-title'>"
        "<a href='https://www.yasdl.com/1/' title='دانلود بازی Elden Ring'></a></h2>"
        "<h2 class='col post-title'>"
        "<a href='https://www.yasdl.com/2/' title='دانلود موسیقی متن بازی Elden Ring'></a></h2>"
        "<h2 class='col post-title'>"
        "<a href='https://www.yasdl.com/3/' title='دانلود نرم افزار نروان'></a></h2>"
    )
    assert [i.title for i in items] == ["دانلود بازی Elden Ring"]


def test_downloadha_skips_non_media_posts(downloadha_search_html: str):
    """Emulators, storefronts and recovery tools are not games."""
    titles = [i.title for i in DownloadhaPlugin().parse_search_results(downloadha_search_html)]
    assert not any("GTasks" in t for t in titles)

    for junk in (
        "دانلود Microsoft Store 22608 - دروازه\u200cای امن و یکپارچه",
        "دانلود BlueStacks 5.22.280.1025 Win/Mac - بلو استکس شبیه ساز",
        "دانلود iCare Format Recovery 8.0.1.2 + Portable - بازیابی اطلاعات",
    ):
        plugin = DownloadhaPlugin()
        cards = plugin.parse_search_results(
            f"<h1 class='entry-title'><a href='https://www.downloadha.com/x/'>{junk}</a></h1>"
        )
        assert cards == [], f"{junk!r} must not be indexed"


def test_downloadha_unescapes_html_entities():
    """`&#8217;` used to reach the UI literally."""
    plugin = DownloadhaPlugin()
    cards = plugin.parse_search_results(
        "<h1 class='entry-title'><a href='https://www.downloadha.com/game/spider/'>"
        "دانلود بازی Marvel&#8217;s Spider-Man 2 - نسخه ElAmigos</a></h1>"
    )
    assert "Marvel’s Spider-Man 2" in cards[0].title
    assert "&#" not in cards[0].title


def test_downloadha_soundtrack_item_yields_bitrates_not_parts():
    """A soundtrack lists one file per bitrate; presenting them as split volumes
    would make "copy all parts" emit an unassemblable list."""
    plugin = DownloadhaPlugin()
    # `/movies/` is a real Downloadha section and a soundtrack post is not a game post,
    # so the section gate does not reject it before the music branch is reached.
    item = plugin.parse_search_results(
        "<h1 class='entry-title'><a href='https://www.downloadha.com/movies/ost-spider-man/'>"
        "دانلود موسیقی متن فیلم Spider-Man 2017</a></h1>"
    )[0]
    plugin.parse_item_page(
        "<div class='download-box'>"
        "<a href='https://dl5.dlhas.ir/AliGh/Music/OST%20128kbps.zip'>128kbps</a>"
        "<a href='https://dl5.dlhas.ir/AliGh/Music/OST.zip'>320kbps</a>"
        "</div>",
        item,
    )
    assert item.category == Category.MUSIC
    assert item.game_releases == []
    assert len(item.music_tracks) == 1
    track = item.music_tracks[0]
    assert [d.bitrate for d in track.downloads] == ["128kbps", "320kbps"]
    assert track.stream_url == item.stream_url


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


def test_yasdl_search_parsing(yasdl_search_html: str):
    """Verify item extraction from real YasDL search page fixture."""
    plugin = YasDLPlugin()
    items = plugin.parse_search_results(yasdl_search_html)

    assert len(items) == 10
    first = items[0]
    assert "American Truck Simulator" in first.title
    assert first.page_url.startswith("https://www.yasdl.com/")
    assert first.category == Category.GAMES
    assert first.source_id == "yasdl"


def test_yasdl_item_link_extraction(yasdl_item_html: str):
    """Verify split RAR parts and password extraction from YasDL post fixture."""
    plugin = YasDLPlugin()
    items = plugin.parse_search_results(yasdl_item_html)
    target = items[0] if items else plugin.parse_search_results("<h2 class='col post-title'><a href='https://www.yasdl.com/105441/' title='American Truck Simulator'>ATS</a></h2>")[0]

    plugin.parse_item_page(yasdl_item_html, target)

    assert len(target.game_releases) == 1
    rel = target.game_releases[0]
    assert rel.release_group == "ElAmigos"
    assert rel.archive_password == "www.yasdl.com"
    assert "14.7" in rel.total_size
    assert len(rel.parts) == 6

    # Verify parts strictly ascending 1..6 with no gaps
    part_numbers = [p.part_number for p in rel.parts]
    assert part_numbers == [1, 2, 3, 4, 5, 6]
    assert rel.has_missing_parts is False
    assert rel.missing_part_numbers == []

    # Verify direct download URLs
    for part in rel.parts:
        assert part.download_url.startswith("https://")
        assert ".rar" in part.download_url


def test_yasdl_recovers_parts_with_trailing_space_href():
    """Live YasDL markup puts a space between the extension and the closing quote.

    Real: href="...Disney.Infinity...part1.rar " for every part except the last,
    which has none. A pattern that requires the extension to touch the quote
    silently drops all but the final part.
    """
    plugin = YasDLPlugin()
    mock_html = """
    <ul class="desc-text tab-content row" id="dl-box1">
      <li class="row"><a class="col" href="https://dl.yasdl.com/user2/Disney.part1.rar "
         title="پارت اول">پارت اول</a></li>
      <li class="row"><a class="col" href="https://dl.yasdl.com/user2/Disney.part2.rar "
         title="پارت دوم">پارت دوم</a></li>
      <li class="row"><a class="col" href="https://dl.yasdl.com/user2/Disney.part3.rar"
         title="پارت سوم">پارت سوم</a></li>
    </ul>
    <p>رمز فایل: www.yasdl.com</p>
    """
    item = plugin.parse_search_results(
        "<h2 class='col post-title'><a href='https://www.yasdl.com/1/' title='T'>T</a></h2>"
    )[0]
    plugin.parse_item_page(mock_html, item)

    assert len(item.game_releases) == 1
    rel = item.game_releases[0]
    assert [p.part_number for p in rel.parts] == [1, 2, 3], "trailing space must not drop parts"
    assert rel.has_missing_parts is False
    for part in rel.parts:
        assert part.download_url == part.download_url.strip(), "URL must be stripped"


def test_downloadha_separates_archives_with_the_same_part_numbers():
    """One post can ship two different archives (exFAT + PKG), each numbered 1..N.

    Merging them into one 1..2N sequence breaks the sequential-ordering gate,
    duplicates part numbers, and makes "copy all parts" emit an unassemblable list.
    """
    plugin = DownloadhaPlugin()
    mock_html = """
    <div class='download-box'>
      <a href='https://dl.example.com/Game.exFAT.part1.rar'>Part 1</a>
      <a href='https://dl.example.com/Game.exFAT.part2.rar'>Part 2</a>
      <a href='https://dl.example.com/Game.PKG.part1.rar'>Part 1</a>
      <a href='https://dl.example.com/Game.PKG.part2.rar'>Part 2</a>
      <p>رمز فایل: www.downloadha.com</p>
    </div>
    """
    item = plugin.parse_search_results(
        "<h1 class='entry-title'><a href='https://www.downloadha.com/game/test/'>Test</a></h1>"
    )[0]
    plugin.parse_item_page(mock_html, item)

    assert len(item.game_releases) == 2, "each archive family is its own release"
    for rel in item.game_releases:
        numbers = [p.part_number for p in rel.parts]
        assert numbers == [1, 2], f"{numbers} must be strictly 1..N within its archive"
        assert rel.has_missing_parts is False
    # No part_number may repeat inside a single release.
    assert all(
        len({p.part_number for p in rel.parts}) == len(rel.parts)
        for rel in item.game_releases
    )


def test_yasdl_gap_detection_on_missing_parts():
    """Verify missing parts are flagged when an upstream site has missing segments."""
    plugin = YasDLPlugin()
    mock_html = """
    <div class='download-box'>
        <a href='https://dl.yasdl.com/game.part1.rar'>دانلود پارت 1</a>
        <a href='https://dl.yasdl.com/game.part3.rar'>دانلود پارت 3</a>
        <p>رمز فایل: www.yasdl.com</p>
    </div>
    """
    item = plugin.parse_search_results("<h2 class='col post-title'><a href='https://www.yasdl.com/test/' title='Test Game'>Test Game</a></h2>")[0]
    plugin.parse_item_page(mock_html, item)

    assert len(item.game_releases) == 1
    rel = item.game_releases[0]
    assert rel.has_missing_parts is True
    assert rel.missing_part_numbers == [2]
