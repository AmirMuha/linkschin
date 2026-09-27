"""Source registry and configuration loader."""

from __future__ import annotations

import os
from typing import Dict, List

from models import Category, SourceConfig
from sources.base import SourcePlugin
from sources.games.downloadha import DownloadhaPlugin
from sources.music.nex1music import Nex1MusicPlugin
from sources.music.popmusic import PopMusicPlugin


def apply_env_overrides(config: SourceConfig) -> SourceConfig:
    """
    Override source base URL via environment variable if present.
    Format: MOVIE_FETCHER_URL_<SOURCE_ID_UPPER>
    Example: MOVIE_FETCHER_URL_DOWNLOADHA=https://mirror.downloadha.com
    """
    env_var = f"MOVIE_FETCHER_URL_{config.id.upper()}"
    override_url = os.environ.get(env_var)
    if override_url:
        config.base_urls = [override_url.strip()]

    # Also allow enabling/disabling via MOVIE_FETCHER_ENABLE_<SOURCE_ID_UPPER>
    enable_var = f"MOVIE_FETCHER_ENABLE_{config.id.upper()}"
    if enable_var in os.environ:
        config.enabled = os.environ[enable_var].strip().lower() in ("1", "true", "yes")

    return config


# Default registry specifications
DEFAULT_CONFIGS: list[SourceConfig] = [
    # Live verified plugins
    SourceConfig(
        id="downloadha",
        name="Downloadha",
        category=Category.GAMES,
        base_urls=["https://www.downloadha.com"],
        enabled=True,
    ),
    SourceConfig(
        id="popmusic",
        name="Pop-Music",
        category=Category.MUSIC,
        base_urls=["https://pop-music.ir"],
        enabled=True,
    ),
    # Dead / Parked / Bot-walled sources preserved in config as disabled entries
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
        id="yasdl",
        name="YasDL",
        category=Category.GAMES,
        base_urls=["https://www.yasdl.com"],
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
        id="nex1music",
        name="Nex1Music",
        category=Category.MUSIC,
        base_urls=["https://nex1music.com"],
        enabled=True,
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
]


def get_all_source_configs() -> list[SourceConfig]:
    """Get all source configurations with environment variable overrides applied."""
    return [apply_env_overrides(cfg) for cfg in DEFAULT_CONFIGS]


def get_sources_for_category(category: Category, include_disabled: bool = False) -> list[SourcePlugin]:
    """Instantiate and return active scraper plugins for a given category."""
    plugins: list[SourcePlugin] = []
    configs = get_all_source_configs()

    for cfg in configs:
        if cfg.category != category:
            continue
        if not cfg.enabled and not include_disabled:
            continue

        if cfg.id == "downloadha":
            plugins.append(DownloadhaPlugin(config=cfg))
        elif cfg.id == "popmusic":
            plugins.append(PopMusicPlugin(config=cfg))
        elif cfg.id == "nex1music":
            plugins.append(Nex1MusicPlugin(config=cfg))

    return plugins
