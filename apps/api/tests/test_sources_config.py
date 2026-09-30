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


# --- 006 registry completeness (T055, T056, T060) ----------------------------

# The 20 sites named in the feature request, by registry id.
SPEC_006_SITES = {
    # full / playable
    "nex1music", "radiojavan", "musicdel", "musicsfa", "upsong",
    "upmusics", "musictarin", "one_rj", "tehranmusic", "melodify", "takmusics",
    # reference / link-out
    "shenoto", "farsichart", "aparat", "namasha", "rubika",
    "fam", "soundcloud", "spotify", "youtube_music",
}

EXPECTED_REFERENCE_IDS = {
    "shenoto", "farsichart", "aparat", "namasha", "fam",
    "soundcloud", "spotify", "youtube_music", "rubika",
}


def test_all_20_spec_sites_present_exactly_once():
    """SC-007: every named site is registered, and none is duplicated."""
    configs = get_all_source_configs()
    ids = [c.id for c in configs]

    duplicated = {i for i in ids if ids.count(i) > 1}
    assert not duplicated, f"sources registered more than once: {duplicated}"

    missing = SPEC_006_SITES - set(ids)
    assert not missing, f"spec sites missing from registry: {missing}"


def test_nex1music_is_one_entry_carrying_both_domains():
    """FR-024: .com and ..ir are reconciled, never a second nex1music_ir entry."""
    configs = get_all_source_configs()
    assert [c.id for c in configs].count("nex1music") == 1
    assert "nex1music_ir" not in {c.id for c in configs}

    cfg = next(c for c in configs if c.id == "nex1music")
    assert cfg.base_urls == ["https://nex1music.com", "https://nex1music.ir"]
    assert cfg.primary_base_url == "https://nex1music.com"


def test_radiojavan_is_one_entry():
    configs = get_all_source_configs()
    assert [c.id for c in configs].count("radiojavan") == 1


def test_music_sources_split_into_full_and_reference():
    """11 full music sources (8 live + 3 dead) and 9 reference sources."""
    music = [c for c in get_all_source_configs() if c.category is Category.MUSIC]
    full = {c.id for c in music if not c.is_reference}
    reference = {c.id for c in music if c.is_reference}

    assert reference == EXPECTED_REFERENCE_IDS
    assert len(reference) == 9

    # 8 live full music sources + 4 dead/blocked ones (radiojavan, upmusic,
    # tehranmusic, melodify, takmusics -> 5 disabled; popmusic included above).
    assert full == {
        "popmusic", "nex1music", "musicdel", "musicsfa", "upsong",
        "upmusics", "musictarin", "one_rj",
        "radiojavan", "upmusic", "tehranmusic", "melodify", "takmusics",
    }, f"unexpected full music sources: {full}"


def test_every_disabled_source_has_an_inactive_reason():
    """T055/T056/T060: enabled=False without a reason is a reporting hole."""
    from sources import INACTIVE_REASONS

    for cfg in get_all_source_configs():
        if cfg.enabled:
            continue
        reason = INACTIVE_REASONS.get(cfg.id, "")
        assert reason.strip(), f"{cfg.id} is disabled but has no INACTIVE_REASONS entry"


def test_inactive_reasons_cover_exactly_the_disabled_sources():
    """No stale reasons for sources that are enabled again."""
    from sources import INACTIVE_REASONS

    disabled = {c.id for c in get_all_source_configs() if not c.enabled}
    assert set(INACTIVE_REASONS) == disabled


def test_dead_and_blocked_music_sources_are_disabled_with_reasons():
    """FR-025/FR-026: verified-dead sites ship as disabled entries, no plugin."""
    from sources import INACTIVE_REASONS, get_sources_for_category

    for sid in ("radiojavan", "tehranmusic", "melodify", "takmusics", "rubika"):
        cfg = next(c for c in get_all_source_configs() if c.id == sid)
        assert cfg.enabled is False, f"{sid} must be registered as disabled"
        assert INACTIVE_REASONS[sid].strip(), f"{sid} needs a specific reason"

    # A disabled source must never be instantiated as a searchable plugin.
    live = {p.config.id for p in get_sources_for_category(Category.MUSIC)}
    assert live.isdisjoint({"radiojavan", "tehranmusic", "melodify", "takmusics", "rubika"})


def test_new_full_sources_are_enabled_and_searchable():
    """Every source with a committed fixture must be live in search."""
    from sources import get_sources_for_category

    live = {p.config.id for p in get_sources_for_category(Category.MUSIC)}
    for sid in ("musicdel", "musicsfa", "upsong", "upmusics", "musictarin", "one_rj"):
        assert sid in live, f"{sid} should be an active searchable source"


def test_pre_006_categories_are_untouched():
    """FR-028: the movies and games registries keep their original sources."""
    from sources import get_sources_for_category

    movies = {p.config.id for p in get_sources_for_category(Category.MOVIES)}
    games = {p.config.id for p in get_sources_for_category(Category.GAMES)}
    assert movies == {"uptvs", "doostihaa"}
    assert games == {"downloadha", "yasdl"}

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
