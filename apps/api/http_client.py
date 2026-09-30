"""HTTP client wrapper with redirect tracking and domain mirror updates."""

from __future__ import annotations

import asyncio
from typing import Any, Mapping
from urllib.parse import urlparse
import urllib.request
import urllib.error

# In-memory mapping of observed domain migrations (e.g. "film2media.click" -> "f2m.link")
DOMAIN_MIRROR_MAP: dict[str, str] = {}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fa,en-US,en;q=0.9",
}

# Redirect hops allowed before a chain is called a loop (FR-015). tiwall answers
# with an endless 307 chain and fam with an endless 308 chain; httpx's own
# max_redirects default is 20, low enough that a legitimate CDN bounce still fits.
MAX_REDIRECTS = 5


class RedirectLoopError(RuntimeError):
    """Raised when a redirect chain exceeds MAX_REDIRECTS hops."""


class SimpleResponse:
    """Lightweight response wrapper compatible with httpx.Response."""
    def __init__(self, status_code: int, text: str, url: str, headers: Mapping[str, str] | None = None):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.headers = headers or {}


def track_redirect(original_url: str, final_url: str) -> None:
    """Track 301/302 domain shifts in DOMAIN_MIRROR_MAP."""
    orig_host = urlparse(original_url).netloc.lower()
    final_host = urlparse(final_url).netloc.lower()
    if orig_host and final_host and orig_host != final_host:
        DOMAIN_MIRROR_MAP[orig_host] = final_host


def get_effective_domain(domain: str) -> str:
    """Return latest tracked domain mirror if redirected previously."""
    clean_domain = domain.lower().strip()
    return DOMAIN_MIRROR_MAP.get(clean_domain, clean_domain)


try:
    import httpx

    class AsyncHttpClient:
        """httpx-backed asynchronous HTTP client with mirror tracking."""

        def __init__(self, timeout: float = 7.0):
            self.timeout = timeout
            self._client = httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=MAX_REDIRECTS,
                headers=DEFAULT_HEADERS,
            )

        async def get(self, url: str, headers: dict[str, str] | None = None, timeout: float | None = None) -> SimpleResponse:
            req_headers = {**DEFAULT_HEADERS, **(headers or {})}
            req_timeout = timeout if timeout is not None else self.timeout
            try:
                resp = await self._client.get(url, headers=req_headers, timeout=req_timeout)
            except httpx.TooManyRedirects as e:
                raise RedirectLoopError(
                    f"redirect loop: {url} exceeded {MAX_REDIRECTS} hops"
                ) from e
            final_url = str(resp.url)
            track_redirect(url, final_url)
            return SimpleResponse(
                status_code=resp.status_code,
                text=resp.text,
                url=final_url,
                headers=dict(resp.headers),
            )

        async def head(self, url: str, headers: dict[str, str] | None = None, timeout: float | None = None) -> SimpleResponse:
            req_headers = {**DEFAULT_HEADERS, **(headers or {})}
            req_timeout = timeout if timeout is not None else self.timeout
            try:
                resp = await self._client.head(url, headers=req_headers, timeout=req_timeout)
            except httpx.TooManyRedirects as e:
                raise RedirectLoopError(
                    f"redirect loop: {url} exceeded {MAX_REDIRECTS} hops"
                ) from e
            final_url = str(resp.url)
            track_redirect(url, final_url)
            return SimpleResponse(
                status_code=resp.status_code,
                text="",
                url=final_url,
                headers=dict(resp.headers),
            )

        async def aclose(self) -> None:
            await self._client.aclose()

        async def __aenter__(self) -> AsyncHttpClient:
            return self

        async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            await self.aclose()

except ImportError:
    # Stdlib fallback when httpx is not installed
    class AsyncHttpClient:  # type: ignore[no-redef]
        """Stdlib-backed asynchronous HTTP client fallback."""

        class _BoundedRedirectHandler(urllib.request.HTTPRedirectHandler):
            """urllib's default cap is 10 and it raises HTTPError; make the loop
            a distinct error so a caller can report it as a redirect loop."""

            max_redirections = MAX_REDIRECTS

            def http_error_308(self, req, fp, code, msg, headers):
                return self.http_error_307(req, fp, code, msg, headers)

            def http_error_301(self, req, fp, code, msg, headers):
                return self._bounded(req, fp, 301, msg, headers)

            def http_error_302(self, req, fp, code, msg, headers):
                return self._bounded(req, fp, 302, msg, headers)

            def http_error_303(self, req, fp, code, msg, headers):
                return self._bounded(req, fp, 303, msg, headers)

            def http_error_307(self, req, fp, code, msg, headers):
                return self._bounded(req, fp, 307, msg, headers)

            def _bounded(self, req, fp, code, msg, headers):
                if self.max_repeats >= MAX_REDIRECTS:
                    raise RedirectLoopError(
                        f"redirect loop: {req.full_url} exceeded {MAX_REDIRECTS} hops"
                    )
                return super().http_error_302(req, fp, code, msg, headers)

        def __init__(self, timeout: float = 7.0):
            self.timeout = timeout
            self._opener = urllib.request.build_opener(self._BoundedRedirectHandler)

        async def get(self, url: str, headers: dict[str, str] | None = None, timeout: float | None = None) -> SimpleResponse:
            loop = asyncio.get_running_loop()
            req_headers = {**DEFAULT_HEADERS, **(headers or {})}
            req_timeout = timeout if timeout is not None else self.timeout

            def _fetch() -> SimpleResponse:
                req = urllib.request.Request(url, headers=req_headers)
                try:
                    with self._opener.open(req, timeout=req_timeout) as resp:
                        final_url = resp.geturl()
                        text = resp.read().decode("utf-8", errors="replace")
                        track_redirect(url, final_url)
                        return SimpleResponse(
                            status_code=resp.status,
                            text=text,
                            url=final_url,
                            headers=dict(resp.headers),
                        )
                except urllib.error.HTTPError as e:
                    track_redirect(url, e.geturl())
                    err_text = e.read().decode("utf-8", errors="replace") if e.fp else ""
                    return SimpleResponse(
                        status_code=e.code,
                        text=err_text,
                        url=e.geturl(),
                        headers=dict(e.headers),
                    )
                except Exception as e:
                    raise e

            return await loop.run_in_executor(None, _fetch)

        async def head(self, url: str, headers: dict[str, str] | None = None, timeout: float | None = None) -> SimpleResponse:
            loop = asyncio.get_running_loop()
            req_headers = {**DEFAULT_HEADERS, **(headers or {})}
            req_timeout = timeout if timeout is not None else self.timeout

            def _head() -> SimpleResponse:
                req = urllib.request.Request(url, headers=req_headers, method="HEAD")
                try:
                    with self._opener.open(req, timeout=req_timeout) as resp:
                        final_url = resp.geturl()
                        track_redirect(url, final_url)
                        return SimpleResponse(
                            status_code=resp.status,
                            text="",
                            url=final_url,
                            headers=dict(resp.headers),
                        )
                except urllib.error.HTTPError as e:
                    track_redirect(url, e.geturl())
                    return SimpleResponse(
                        status_code=e.code,
                        text="",
                        url=e.geturl(),
                        headers=dict(e.headers),
                    )
                except Exception as e:
                    raise e

            return await loop.run_in_executor(None, _head)

        async def aclose(self) -> None:
            pass

        async def __aenter__(self) -> AsyncHttpClient:
            return self

        async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            pass
