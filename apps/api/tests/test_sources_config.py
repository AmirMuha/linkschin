"""Unit tests for source configurations, registry, and redirect tracking."""

from __future__ import annotations

import os
from http_client import DOMAIN_MIRROR_MAP, get_effective_domain, track_redirect
from models import Category, SourceAccessTier
from sources import get_all_source_configs, get_sources_for_category


def test_registry_contains_all_spec_sources():
    """Verify all 11 sources from specification are present in registry."""
    configs = get_all_source_configs()
    source_ids = {c.id for c in configs}
    expected = {
        "film2media", "avamovie", "zarfilm", "mobomovie",
        "yasdl", "downloadha", "game2dl",
        "nex1music", "popmusic", "radiojavan", "upmusic",
    }
    assert expected.issubset(source_ids)


def test_environment_variable_url_override(monkeypatch):
    """Verify MOVIE_FETCHER_URL_<ID> overrides base URLs dynamically."""
    monkeypatch.setenv("MOVIE_FETCHER_URL_DOWNLOADHA", "https://mirror2.downloadha.com")
    game_plugins = get_sources_for_category(Category.GAMES)
    dlha = next(p for p in game_plugins if p.config.id == "downloadha")
    assert dlha.config.primary_base_url == "https://mirror2.downloadha.com"


def test_environment_variable_enable_override(monkeypatch):
    """Verify MOVIE_FETCHER_ENABLE_<ID> enables/disables sources."""
    monkeypatch.setenv("MOVIE_FETCHER_ENABLE_FILM2MEDIA", "true")
    all_configs = get_all_source_configs()
    f2m = next(c for c in all_configs if c.id == "film2media")
    assert f2m.enabled is True


def test_redirect_tracking():
    """Verify 301/302 domain mirror detection updates in-memory mapping."""
    track_redirect("https://film2media.click/movie/1", "https://f2m.website/movie/1")
    assert get_effective_domain("film2media.click") == "f2m.website"
    assert get_effective_domain("untouched.com") == "untouched.com"

def test_every_source_declares_a_valid_access_tier():
    """Every registry entry exposes a SourceAccessTier so the frontend never sees a gap."""
    from models import SourceAccessTier
    for config in get_all_source_configs():
        assert isinstance(config.access_tier, SourceAccessTier), config.id

def test_movie_source_tiers_match_their_access_model():
    """UpTVs is fully free; Doostihaa gates HD behind membership, so it is freemium."""
    movie_tiers = {c.id: c.access_tier for c in get_all_source_configs()
                    if c.category == Category.MOVIES and c.enabled}
    assert movie_tiers["uptvs"] is SourceAccessTier.FREE
    assert movie_tiers["doostihaa"] is SourceAccessTier.FREEMIUM
