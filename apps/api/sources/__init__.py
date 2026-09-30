"""Source registry and configuration loader."""

from __future__ import annotations

import os
from dataclasses import replace

from models import Category, SourceAccessTier, SourceConfig, SourceKind
from sources.base import SourcePlugin
from sources.games.downloadha import DownloadhaPlugin
from sources.games.yasdl import YasDLPlugin
from sources.movies import (
    AparatPlugin as MovieAparatPlugin,
)
from sources.movies import (
    BabakFilmPlugin,
    DanfiloPlugin,
    DigitoonPlugin,
    DoostihaaPlugin,
    FamPlugin as MovieFamPlugin,
    FilimoPlugin,
    FilmChiinPlugin,
    FilmnetPlugin,
    FilmTarinPlugin,
    GapfilmPlugin,
    IMVBoxPlugin,
    NamashaPlugin as MovieNamashaPlugin,
    NamavaPlugin,
    NdaMediaPlugin,
    RubikaPlugin as MovieRubikaPlugin,
    SalamCinemaPlugin,
    SarvnemaPlugin,
    TelewebionPlugin,
    TiwallPlugin,
    UpTVsPlugin,
)
from sources.music.aparat import AparatPlugin
from sources.music.fam import FamPlugin
from sources.music.farsichart import FarsiChartPlugin
from sources.music.musicdel import MusicDelPlugin
from sources.music.musicsfa import MusicsFaPlugin
from sources.music.musictarin import MusicTarinPlugin
from sources.music.namasha import NamashaPlugin
from sources.music.nex1music import Nex1MusicPlugin
from sources.music.one_rj import OneRJPlugin
from sources.music.popmusic import PopMusicPlugin
from sources.music.shenoto import ShenotoPlugin
from sources.music.soundcloud import SoundcloudPlugin
from sources.music.spotify import SpotifyPlugin
from sources.music.upmusics import UpMusicsPlugin
from sources.music.upsong import UpSongPlugin
from sources.music.youtube_music import YoutubeMusicPlugin
from sources.profiles import load_profiles, register_parser


# Per-registry INACTIVE_REASONS strings for every source with enabled=False.
# Lives beside the registry rather than on SourceConfig (data-model.md).
INACTIVE_REASONS: dict[str, str] = {
    # 006 dead / blocked / unreachable music sites (FR-025, FR-026)
    "radiojavan": "Cloudflare bot detection — site denies headless requests",
    "tehranmusic": "Domain parked — page served but no content",
    "melodify": "Dead domain redirecting to parking page",
    "takmusics": "Site unreachable — persistent connection failures",
    "rubika": "Network unreachable — blocking or downtime",
    # Pre-existing disabled entries
    "film2media": "Site unreachable or blocked",
    "avamovie": "Site unreachable or blocked",
    "zarfilm": "Site unreachable or blocked",
    "mobomovie": "Site unreachable or blocked",
    "game2dl": "Site unreachable or blocked",
    "upmusic": "Site unreachable or blocked",
}


def apply_env_overrides(config: SourceConfig) -> SourceConfig:
    """
    Override source base URL via environment variable if present.
    Format: MOVIE_FETCHER_URL_<SOURCE_ID_UPPER>
    Example: MOVIE_FETCHER_URL_DOWNLOADHA=https://mirror2.downloadha.com

    Returns a copy: DEFAULT_CONFIGS holds shared module-level dataclasses, and
    mutating one in place would leak an env override into every later caller.
    """
    env_var = f"MOVIE_FETCHER_URL_{config.id.upper()}"
    enable_var = f"MOVIE_FETCHER_ENABLE_{config.id.upper()}"

    base_urls = list(config.base_urls)
    if override_url := os.environ.get(env_var):
        base_urls = [override_url.strip()]

    enabled = config.enabled
    if enable_var in os.environ:
        enabled = os.environ[enable_var].strip().lower() in ("1", "true", "yes")

    if base_urls == config.base_urls and enabled == config.enabled:
        return config
    return replace(config, base_urls=base_urls, enabled=enabled)


# Default registry specifications. Every entry sets `kind` explicitly (data-model.md).
DEFAULT_CONFIGS: list[SourceConfig] = [
    # ---- Full sources: resolve playable media ----
    SourceConfig(
        id="uptvs",
        name="UpTVs",
        category=Category.MOVIES,
        base_urls=["https://www.uptvs.com"],
        enabled=True,
        access_tier=SourceAccessTier.FREE,
    ),
    SourceConfig(
        id="doostihaa",
        name="Doostihaa",
        category=Category.MOVIES,
        base_urls=["https://www.doostihaa.com"],
        enabled=True,
        # ponytail: games/music sources keep the FREE default; declare a tier
        # here only when a registry entry deviates from it.
        access_tier=SourceAccessTier.FREEMIUM,
    ),
    SourceConfig(
        id="downloadha",
        name="Downloadha",
        category=Category.GAMES,
        base_urls=["https://www.downloadha.com"],
        enabled=True,
    ),
    SourceConfig(
        id="yasdl",
        name="YasDL",
        category=Category.GAMES,
        base_urls=["https://www.yasdl.com"],
        enabled=True,
    ),
    SourceConfig(
        id="popmusic",
        name="Pop-Music",
        category=Category.MUSIC,
        base_urls=["https://pop-music.ir"],
        enabled=True,
    ),
    # nex1music reconciled: both domains in one entry, not two (FR-024)
    SourceConfig(
        id="nex1music",
        name="Nex1Music",
        category=Category.MUSIC,
        base_urls=["https://nex1music.com", "https://nex1music.ir"],
        enabled=True,
    ),
    SourceConfig(
        id="musicdel",
        name="MusicDel",
        category=Category.MUSIC,
        base_urls=["https://musicdel.ir"],
        enabled=True,
    ),
    SourceConfig(
        id="musicsfa",
        name="MusicFa",
        category=Category.MUSIC,
        base_urls=["https://musics-fa.com"],
        enabled=True,
    ),
    SourceConfig(
        id="upsong",
        name="UpSong",
        category=Category.MUSIC,
        base_urls=["https://upsong.ir"],
        enabled=True,
    ),
    SourceConfig(
        id="upmusics",
        name="UpMusics",
        category=Category.MUSIC,
        base_urls=["https://upmusics.com"],
        enabled=True,
    ),
    SourceConfig(
        id="musictarin",
        name="MusicTarin",
        category=Category.MUSIC,
        base_urls=["https://musictarin.com"],
        enabled=True,
    ),
    SourceConfig(
        id="one_rj",
        name="1RJ",
        category=Category.MUSIC,
        base_urls=["https://1rj.ir"],
        enabled=True,
    ),
    # ---- Reference sources: link-out only, no media (FR-011) ----
    SourceConfig(
        id="shenoto",
        name="Shenoto",
        category=Category.MUSIC,
        base_urls=["https://shenoto.com"],
        enabled=True,
        kind=SourceKind.REFERENCE,
    ),
    SourceConfig(
        id="farsichart",
        name="FarsiChart",
        category=Category.MUSIC,
        base_urls=["https://farsichart.com"],
        enabled=True,
        kind=SourceKind.REFERENCE,
    ),
    SourceConfig(
        id="aparat",
        name="Aparat",
        category=Category.MUSIC,
        base_urls=["https://www.aparat.com"],
        enabled=True,
        kind=SourceKind.REFERENCE,
    ),
    SourceConfig(
        id="namasha",
        name="Namasha",
        category=Category.MUSIC,
        base_urls=["https://namasha.com"],
        enabled=True,
        kind=SourceKind.REFERENCE,
    ),
    SourceConfig(
        id="fam",
        name="Fam",
        category=Category.MUSIC,
        base_urls=["https://fam.ir"],
        enabled=True,
        kind=SourceKind.REFERENCE,
    ),
    SourceConfig(
        id="soundcloud",
        name="SoundCloud",
        category=Category.MUSIC,
        base_urls=["https://soundcloud.com"],
        enabled=True,
        kind=SourceKind.REFERENCE,
    ),
    SourceConfig(
        id="spotify",
        name="Spotify",
        category=Category.MUSIC,
        base_urls=["https://open.spotify.com"],
        enabled=True,
        kind=SourceKind.REFERENCE,
    ),
    SourceConfig(
        id="youtube_music",
        name="YouTube Music",
        category=Category.MUSIC,
        base_urls=["https://music.youtube.com"],
        enabled=True,
        kind=SourceKind.REFERENCE,
    ),
    # ---- Dead / blocked / unreachable: disabled with reason, no plugin ----
    SourceConfig(
        id="film2media",
        name="Film2Media",
        category=Category.MOVIES,
        base_urls=["https://www.film2media.click"],
        enabled=False,
    ),
    SourceConfig(
        id="avamovie",
        name="AvaMovie",
        category=Category.MOVIES,
        base_urls=["https://www.avasds.ir"],
        enabled=False,
    ),
    SourceConfig(
        id="zarfilm",
        name="Zarfilm",
        category=Category.MOVIES,
        base_urls=["https://www.zarfilm.click"],
        enabled=False,
    ),
    SourceConfig(
        id="mobomovie",
        name="MoboMovie",
        category=Category.MOVIES,
        base_urls=["https://mobomovie.com"],
        enabled=False,
    ),
    SourceConfig(
        id="game2dl",
        name="Game2DL",
        category=Category.GAMES,
        base_urls=["https://game2dl.com"],
        enabled=False,
    ),
    SourceConfig(
        id="radiojavan",
        name="RadioJavan",
        category=Category.MUSIC,
        base_urls=["https://radiojavan.com"],
        enabled=False,
    ),
    SourceConfig(
        id="upmusic",
        name="UpMusic",
        category=Category.MUSIC,
        base_urls=["https://upmusic.info"],
        enabled=False,
    ),
    SourceConfig(
        id="tehranmusic",
        name="TehranMusic",
        category=Category.MUSIC,
        base_urls=["https://tehranmusic.com"],
        enabled=False,
    ),
    SourceConfig(
        id="melodify",
        name="Melodify",
        category=Category.MUSIC,
        base_urls=["https://melodify.ir"],
        enabled=False,
    ),
    SourceConfig(
        id="takmusics",
        name="TakMusics",
        category=Category.MUSIC,
        base_urls=["https://takmusics.ir"],
        enabled=False,
    ),
    SourceConfig(
        id="rubika",
        name="Rubika",
        category=Category.MUSIC,
        base_urls=["https://rubika.com"],
        enabled=False,
        kind=SourceKind.REFERENCE,
    ),
]

# ponytail: linear if/elif lookup; switch to a dict if source count passes ~50.
_PLUGIN_BY_ID: dict[str, type] = {
    "downloadha": DownloadhaPlugin,
    "yasdl": YasDLPlugin,
    "uptvs": UpTVsPlugin,
    "doostihaa": DoostihaaPlugin,
    "popmusic": PopMusicPlugin,
    "nex1music": Nex1MusicPlugin,
    "musicdel": MusicDelPlugin,
    "musicsfa": MusicsFaPlugin,
    "upsong": UpSongPlugin,
    "upmusics": UpMusicsPlugin,
    "musictarin": MusicTarinPlugin,
    "one_rj": OneRJPlugin,
    "shenoto": ShenotoPlugin,
    "farsichart": FarsiChartPlugin,
    "aparat": AparatPlugin,
    "namasha": NamashaPlugin,
    "fam": FamPlugin,
    "soundcloud": SoundcloudPlugin,
    "spotify": SpotifyPlugin,
    "youtube_music": YoutubeMusicPlugin,
}

# Parser name -> plugin class for every movie profile. Registered here, where the
# plugin factory can see the same table, so a profile resolves to an
# implementation that genuinely exists (FR-022, FR-023).
_MOVIE_PARSER_PLUGINS: dict[str, type] = {
    "aparat": MovieAparatPlugin,
    "babakfilm": BabakFilmPlugin,
    "danfilo": DanfiloPlugin,
    "digitoon": DigitoonPlugin,
    "fam": MovieFamPlugin,
    "filimo": FilimoPlugin,
    "filmchiin": FilmChiinPlugin,
    "filmnet": FilmnetPlugin,
    "filmtarin": FilmTarinPlugin,
    "gapfilm": GapfilmPlugin,
    "imvbox": IMVBoxPlugin,
    "namasha": MovieNamashaPlugin,
    "namava": NamavaPlugin,
    "ndamedia": NdaMediaPlugin,
    "rubika": MovieRubikaPlugin,
    "salamcinema": SalamCinemaPlugin,
    "sarvnema": SarvnemaPlugin,
    "telewebion": TelewebionPlugin,
    "tiwall": TiwallPlugin,
    "uptvs": UpTVsPlugin,
}

for _parser_name, _plugin_cls in _MOVIE_PARSER_PLUGINS.items():
    register_parser(_parser_name, _plugin_cls)

# Movie plugins are keyed separately from _PLUGIN_BY_ID: a movie source and a music
# source may share an id (aparat, namasha, fam, rubika are all on both sides), and
# one key for both would silently wire the wrong scraper.
_MOVIE_PLUGIN_BY_ID: dict[str, type] = {**_MOVIE_PARSER_PLUGINS, "doostihaa": DoostihaaPlugin}


def _profile_configs() -> list[SourceConfig]:
    """Build SourceConfigs from profiles.yaml, merged over DEFAULT_CONFIGS.

    Merge is per (category, id), not per id: uptvs, aparat, namasha, fam and rubika
    exist on both the movie and the music side, and a movie plugin must not be
    folded into the music registry entry that happens to share its name.

    A (category, id) already in the registry keeps the registry entry, which carries
    fields a profile has no schema for (access_tier, and the INACTIVE_REASONS pairing
    a disabled source requires). Only ``provides_downloads`` is taken from the
    profile, because DEFAULT_CONFIGS has no other source of truth for it -- it marks
    a subscription service that returns a watch page instead of downloads (FR-003).
    """
    merged = {(c.category, c.id): c for c in DEFAULT_CONFIGS}
    for profile in load_profiles():
        key = (profile.category, profile.id)
        existing = merged.get(key)
        if existing is None:
            merged[key] = profile.to_source_config()
        elif profile.provides_downloads != existing.provides_downloads:
            merged[key] = replace(existing, provides_downloads=profile.provides_downloads)
    return list(merged.values())


def get_all_source_configs() -> list[SourceConfig]:
    """Get all source configurations with environment variable overrides applied."""
    return [apply_env_overrides(cfg) for cfg in _profile_configs()]


def get_sources_for_category(
    category: Category,
    include_disabled: bool = False,
    exclude_ids: set[str] | None = None,
    exclude_streaming: bool = False,
) -> list[SourcePlugin]:
    """Instantiate and return active scraper plugins for a given category.

    ``exclude_ids`` is the per-user hidden-source set (FR-029). It defaults to
    ``None`` so existing callers are unaffected.

    ``exclude_streaming`` drops sources that are streaming platforms.
    """
    excluded = exclude_ids or set()
    plugins: list[SourcePlugin] = []

    for cfg in get_all_source_configs():
        if cfg.category != category:
            continue
        if not cfg.enabled and not include_disabled:
            continue
        if cfg.id in excluded:
            continue
        if cfg.is_alias:
            continue
        if exclude_streaming and cfg.is_streaming:
            continue

        plugin_cls = (
            _MOVIE_PLUGIN_BY_ID.get(cfg.id)
            if cfg.category is Category.MOVIES
            else _PLUGIN_BY_ID.get(cfg.id)
        )
        if plugin_cls is not None:
            plugins.append(plugin_cls(config=cfg))

    return plugins
