"""Unit tests for domain entities and invariants."""

from __future__ import annotations

import time

try:
    import pytest
except ImportError:
    class _MockPytest:
        @staticmethod
        class raises:
            def __init__(self, expected_exc, match=None):
                self.expected_exc = expected_exc
                self.match = match
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    raise AssertionError(f"Expected {self.expected_exc}, but nothing was raised")
                return issubclass(exc_type, self.expected_exc)
    pytest = _MockPytest()  # type: ignore

from models import (
    Category,
    CachedResult,
    GamePartLink,
    GameRelease,
    MediaItem,
    MusicDownloadVariant,
    MusicTrack,
    validate_media_url,
)


def test_game_part_continuity_success():
    """Ensure sequential parts are ordered properly and mark no gaps."""
    parts = [
        GamePartLink(part_number=3, part_label="Part 3", download_url="https://dl.example.com/p3.rar"),
        GamePartLink(part_number=1, part_label="Part 1", download_url="https://dl.example.com/p1.rar"),
        GamePartLink(part_number=2, part_label="Part 2", download_url="https://dl.example.com/p2.rar"),
    ]
    release = GameRelease(
        id="rel_1",
        source_name="Downloadha",
        archive_password="www.downloadha.com",
        parts=parts,
    )
    assert [p.part_number for p in release.parts] == [1, 2, 3]
    assert release.has_missing_parts is False
    assert release.missing_part_numbers == []


def test_game_part_gap_detection():
    """Ensure gaps in part numbers are identified and recorded."""
    parts = [
        GamePartLink(part_number=1, part_label="Part 1", download_url="https://dl.example.com/p1.rar"),
        GamePartLink(part_number=2, part_label="Part 2", download_url="https://dl.example.com/p2.rar"),
        GamePartLink(part_number=5, part_label="Part 5", download_url="https://dl.example.com/p5.rar"),
    ]
    release = GameRelease(
        id="rel_2",
        source_name="Downloadha",
        parts=parts,
    )
    assert release.has_missing_parts is True
    assert release.missing_part_numbers == [3, 4]


def test_game_part_invalid_number():
    """Part numbers must be >= 1."""
    with pytest.raises(ValueError):
        GamePartLink(part_number=0, part_label="Part 0", download_url="https://dl.example.com/p0.rar")


def test_url_scheme_validation():
    """Only http and https schemes are permitted."""
    assert validate_media_url("https://example.com/test.mp4") == "https://example.com/test.mp4"
    assert validate_media_url("http://example.com/test.mp3") == "http://example.com/test.mp3"

    with pytest.raises(ValueError):
        validate_media_url("javascript:alert(1)")

    with pytest.raises(ValueError):
        validate_media_url("file:///etc/passwd")

    with pytest.raises(ValueError):
        validate_media_url("")


def test_music_track_creation():
    """Verify MusicTrack and MusicDownloadVariant properties."""
    downloads = [
        MusicDownloadVariant(bitrate="128kbps", download_url="https://dl.example.com/song128.mp3"),
        MusicDownloadVariant(bitrate="320kbps", download_url="https://dl.example.com/song320.mp3"),
    ]
    track = MusicTrack(
        id="track_1",
        title="Sample Song",
        artist="Sample Artist",
        source_name="Pop-Music",
        stream_url="https://dl.example.com/song128.mp3",
        downloads=downloads,
    )
    assert track.title == "Sample Song"
    assert len(track.downloads) == 2


def test_cached_result_expiration():
    """Verify TTL expiry calculation on CachedResult."""
    cached = CachedResult(
        key="games:gta",
        items=[],
        created_at=time.time() - 3000,
        ttl_seconds=2700,
    )
    assert cached.is_expired is True

    fresh = CachedResult(
        key="games:gta",
        items=[],
        created_at=time.time(),
        ttl_seconds=2700,
    )
    assert fresh.is_expired is False
