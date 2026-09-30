"""Reference source tests: link-out only, never media (FR-011, FR-012, constitution III)."""

from __future__ import annotations

import inspect

import pytest

from models import Category, SearchQuery, SourceConfig, SourceKind
from sources import get_all_source_configs
from sources.music.aparat import AparatPlugin
from sources.music.fam import FamPlugin
from sources.music.farsichart import FarsiChartPlugin
from sources.music.namasha import NamashaPlugin
from sources.music.reference import ReferenceSourcePlugin
from sources.music.shenoto import ShenotoPlugin
from sources.music.soundcloud import SoundcloudPlugin
from sources.music.spotify import SpotifyPlugin
from sources.music.youtube_music import YoutubeMusicPlugin

ALL_REFERENCE = [
    ShenotoPlugin,
    FarsiChartPlugin,
    AparatPlugin,
    NamashaPlugin,
    FamPlugin,
    SoundcloudPlugin,
    SpotifyPlugin,
    YoutubeMusicPlugin,
]


def _config(plugin_cls) -> SourceConfig:
    return SourceConfig(
        id=plugin_cls.__name__.lower().replace("plugin", ""),
        name=plugin_cls.__name__,
        category=Category.MUSIC,
        base_urls=["https://example.test"],
        kind=SourceKind.REFERENCE,
    )


def test_every_registered_reference_source_has_a_plugin():
    """Every enabled REFERENCE entry in the registry is backed by a plugin class."""
    from sources import _PLUGIN_BY_ID

    reference_ids = {
        c.id for c in get_all_source_configs()
        if c.kind is SourceKind.REFERENCE and c.enabled
    }
    assert reference_ids, "expected reference sources in the registry"
    for rid in reference_ids:
        assert rid in _PLUGIN_BY_ID, f"{rid} is registered as reference but has no plugin"
        assert issubclass(_PLUGIN_BY_ID[rid], ReferenceSourcePlugin)


@pytest.mark.parametrize("plugin_cls", ALL_REFERENCE)
def test_reference_plugin_has_no_media_assignment_path(plugin_cls):
    """Structural guarantee: the class body never mentions stream_url/music_tracks."""
    src = inspect.getsource(ReferenceSourcePlugin)
    # Only the docstrings and the intentional no-op may appear, never an assignment.
    for lineno, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(("#", "*", '"""')) or not stripped:
            continue
        assert "stream_url =" not in stripped, f"reference base assigns stream_url at line {lineno}"
        assert "music_tracks =" not in stripped, f"reference base assigns music_tracks at line {lineno}"


@pytest.mark.parametrize("plugin_cls", ALL_REFERENCE)
def test_reference_search_returns_linkout_only(plugin_cls):
    """search() yields a single MediaItem with a page_url and no media (FR-011)."""
    import asyncio

    plugin = plugin_cls(config=_config(plugin_cls))
    query = SearchQuery(raw_query="محسن یگانه", normalized_query="محسن یگانه", category=Category.MUSIC)

    items = asyncio.run(plugin.search(query, client=None))

    assert len(items) == 1
    item = items[0]
    assert item.source_id == plugin.config.id
    assert item.page_url.startswith("https://")
    assert item.stream_url is None
    assert item.music_tracks == []


@pytest.mark.parametrize("plugin_cls", ALL_REFERENCE)
def test_reference_extract_links_is_a_noop(plugin_cls):
    """extract_links returns the item unchanged, even if the pipeline calls it."""
    import asyncio

    from models import MediaItem

    plugin = plugin_cls(config=_config(plugin_cls))
    item = MediaItem(
        id="ref_test",
        title="test",
        category=Category.MUSIC,
        source_id=plugin.config.id,
        page_url="https://example.test/song",
    )
    result = asyncio.run(plugin.extract_links(item, client=None))

    assert result is item
    assert result.stream_url is None
    assert result.music_tracks == []


@pytest.mark.parametrize("plugin_cls", ALL_REFERENCE)
def test_reference_plugin_accepts_no_credentials(plugin_cls):
    """Constructor takes only a SourceConfig; no token/password/user params (FR-012)."""
    params = list(inspect.signature(plugin_cls.__init__).parameters)
    assert params == ["self", "config"], f"unexpected constructor params: {params}"

    config = _config(plugin_cls)
    forbidden = {"token", "password", "username", "user", "api_key", "secret", "credential"}
    for field in config.__dataclass_fields__:
        assert field.lower() not in forbidden


def test_reference_source_takes_no_constructor_defaults():
    """Subclasses must not add config of their own — they only carry a docstring."""
    for plugin_cls in ALL_REFERENCE:
        assert plugin_cls.__init__ is ReferenceSourcePlugin.__init__ or (
            "config" in inspect.signature(plugin_cls.__init__).parameters
        )


def test_reference_item_id_is_stable_across_processes():
    """crc32, not hash(): PYTHONHASHSEED must not change a reference item's id."""
    import subprocess
    import sys
    import zlib

    expected = f"ref_spotify_{zlib.crc32('محسن یگانه'.encode()):08x}"
    for seed in ("0", "1", "12345"):
        out = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.');"
             "import asyncio;"
             "from models import Category, SearchQuery, SourceConfig, SourceKind;"
             "from sources.music.spotify import SpotifyPlugin;"
             "p = SpotifyPlugin(config=SourceConfig(id='spotify', name='Spotify',"
             " category=Category.MUSIC, base_urls=['https://open.spotify.com'],"
             " kind=SourceKind.REFERENCE));"
             "q = SearchQuery(raw_query='محسن یگانه', normalized_query='محسن یگانه',"
             " category=Category.MUSIC);"
             "print(asyncio.run(p.search(q, None))[0].id)"],
            capture_output=True, text=True, env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin"},
        )
        assert out.returncode == 0, out.stderr
        assert out.stdout.strip() == expected, f"HASHSEED={seed} changed the id"


# --- T078: the link-out card is absent from the DOM, not merely hidden -------

def _render_music_card(item) -> str:
    """Render _music_card.html standalone and return the HTML string."""
    from pathlib import Path

    from fastapi.templating import Jinja2Templates
    from models import MusicTrack, MusicDownloadVariant

    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "web" / "templates"))
    return templates.get_template("_music_card.html").render(item=item)


def _reference_item():
    from models import MediaItem

    return MediaItem(
        id="ref_1",
        title="spotify: محسن یگانه",
        category=Category.MUSIC,
        source_id="spotify",
        page_url="https://open.spotify.com/search/محسن",
    )


def test_reference_card_emits_no_audio_element_and_no_download_control():
    """FR-011 / SC-003: the player must be ABSENT from the DOM.

    The reference branch is selected by item.source_kind, which _finalize stamps
    from the registry. A media-less item that is NOT stamped reference must take
    the other branch — that is what keeps the two wordings distinguishable.
    """
    item = _reference_item()
    item.source_kind = "reference"

    html = _render_music_card(item)

    assert "<audio" not in html, "reference card rendered an <audio> element"
    assert "btn-download" not in html, "reference card rendered a download control"
    assert "دانلود با کیفیت" not in html, "reference card offered a download"
    # The outbound link to the originating site is present.
    assert 'href="https://open.spotify.com/search/محسن"' in html
    assert 'rel="noopener"' in html
    # The link-out marker is what distinguishes this branch from the plain
    # full-source rendering. Without it, a media-less item would satisfy every
    # assertion above while silently taking the wrong branch.
    assert "گوش دادن در سایت منبع" in html, "reference card rendered no link-out marker"
    assert "لینک مستقیمی یافت نشد" not in html, \
        "a reference card fell through to the full-source unavailable message"


def test_reference_card_never_emits_a_player_even_when_media_is_present():
    """Defence in depth: kind, not media presence, gates the player.

    A subclass that wrongly populated stream_url must still render a link-out —
    the reference guarantee is structural, not contingent on a missing field.
    """
    from models import MusicDownloadVariant, MusicTrack

    item = _reference_item()
    item.source_kind = "reference"
    item.stream_url = "https://cdn.example.com/should-not-render.mp3"
    item.music_tracks = [MusicTrack(
        id="t1", title="t", artist="a", source_name="s",
        cover_url=None, stream_url=item.stream_url,
        downloads=[MusicDownloadVariant(bitrate="320kbps",
                                        download_url="https://cdn.example.com/x.mp3")],
    )]

    html = _render_music_card(item)
    assert "<audio" not in html, "reference card rendered an <audio> element"
    assert "btn-download" not in html, "reference card rendered a download control"


def test_full_source_card_without_a_link_reports_unavailable_not_a_broken_player():
    """FR-015: no stream_url means a plain message, never an empty <audio>."""
    from models import MediaItem

    item = MediaItem(
        id="mdel_empty",
        title="دانلود آهنگ بدون لینک",
        category=Category.MUSIC,
        source_id="musicdel",
        page_url="https://musicdel.ir/single-tracks/1/",
    )
    item.source_kind = "full"

    html = _render_music_card(item)

    assert "<audio" not in html, "a media-less full-source item rendered a player"
    assert "لینک مستقیمی یافت نشد" in html, "missing the unavailable message"
    assert "گوش دادن در سایت منبع" not in html, \
        "a full-source item used the reference link-out wording"


def test_full_source_card_with_a_link_renders_player_and_downloads():
    """The full-source branch is unchanged: player plus labelled downloads."""
    from models import MediaItem, MusicDownloadVariant, MusicTrack

    item = MediaItem(
        id="mdel_1", title="دانلود آهنگ لندکروز", category=Category.MUSIC,
        source_id="musicdel", page_url="https://musicdel.ir/single-tracks/1/",
    )
    item.source_kind = "full"
    item.stream_url = "https://cdn.musicdel.ir/128.mp3"
    item.music_tracks = [MusicTrack(
        id="t1", title="لندکروز", artist="محمد کجوری", source_name="MusicDel",
        cover_url=None, stream_url=item.stream_url,
        downloads=[
            MusicDownloadVariant(bitrate="320kbps", download_url="https://cdn.musicdel.ir/320.mp3"),
            MusicDownloadVariant(bitrate="128kbps", download_url="https://cdn.musicdel.ir/128.mp3"),
        ],
    )]

    html = _render_music_card(item)

    assert "<audio" in html
    assert "دانلود با کیفیت 320kbps" in html
    assert "دانلود با کیفیت 128kbps" in html
    assert "گوش دادن در سایت منبع" not in html
