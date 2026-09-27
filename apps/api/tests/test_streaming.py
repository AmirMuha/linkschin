"""Offline tests for stream URL validation logic (T033 & T035)."""

from http_client import SimpleResponse
from sources.base import is_directly_playable, validate_stream_url


class DummyClient:
    """In-memory client stub for stream validation testing."""

    def __init__(self, response: SimpleResponse | None = None, raise_error: bool = False):
        self.response = response
        self.raise_error = raise_error

    async def head(self, url: str, **kwargs) -> SimpleResponse:
        if self.raise_error:
            raise ConnectionError("Upstream timeout or connection reset")
        if self.response is None:
            return SimpleResponse(status_code=404, text="", url=url)
        return self.response


def test_is_directly_playable_valid_video():
    headers = {
        "Content-Type": "video/mp4",
        "Access-Control-Allow-Origin": "*",
    }
    assert is_directly_playable(200, headers) is True


def test_is_directly_playable_valid_audio():
    headers = {
        "Content-Type": "audio/mpeg; charset=utf-8",
        "Access-Control-Allow-Origin": "https://example.com",
    }
    assert is_directly_playable(200, headers) is True


def test_is_directly_playable_http_error():
    headers = {
        "Content-Type": "video/mp4",
        "Access-Control-Allow-Origin": "*",
    }
    assert is_directly_playable(404, headers) is False
    assert is_directly_playable(500, headers) is False


def test_is_directly_playable_wrong_mime():
    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
    }
    assert is_directly_playable(200, headers) is False


def test_is_directly_playable_missing_or_empty_cors():
    # Missing CORS header
    assert is_directly_playable(200, {"Content-Type": "video/mp4"}) is False
    # Empty CORS header
    assert is_directly_playable(200, {"Content-Type": "video/mp4", "Access-Control-Allow-Origin": "  "}) is False


async def test_validate_stream_url_ad_or_empty():
    client = DummyClient(SimpleResponse(200, "", "http://example.com", {"Content-Type": "video/mp4", "Access-Control-Allow-Origin": "*"}))
    assert await validate_stream_url("", client) is False
    assert await validate_stream_url("http://adclick.net/watch?id=123", client) is False


async def test_validate_stream_url_success():
    resp = SimpleResponse(
        status_code=200,
        text="",
        url="https://cdn.example.com/movie.mp4",
        headers={"Content-Type": "video/mp4", "Access-Control-Allow-Origin": "*"},
    )
    client = DummyClient(response=resp)
    assert await validate_stream_url("https://cdn.example.com/movie.mp4", client) is True


async def test_validate_stream_url_failure():
    resp = SimpleResponse(
        status_code=403,
        text="",
        url="https://cdn.example.com/forbidden.mp4",
        headers={"Content-Type": "video/mp4"},
    )
    client = DummyClient(response=resp)
    assert await validate_stream_url("https://cdn.example.com/forbidden.mp4", client) is False


async def test_validate_stream_url_exception_handling():
    client = DummyClient(raise_error=True)
    assert await validate_stream_url("https://cdn.example.com/error.mp4", client) is False
