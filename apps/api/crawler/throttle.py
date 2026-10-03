"""Domain-level rate limiting, concurrency semaphores, and adaptive backoff (User Story 6)."""

from __future__ import annotations

import asyncio
import os
import random
import time
from urllib.parse import urlparse

import db

DEFAULT_MAX_CONCURRENCY = int(os.environ.get("MAX_CONCURRENCY_PER_DOMAIN", "2"))
DEFAULT_DOMAIN_DELAY = float(os.environ.get("DEFAULT_DOMAIN_DELAY_SECONDS", "1.0"))
MAX_BACKOFF_SECONDS = 60.0


def extract_domain(url: str) -> str:
    """Extract normalized netloc/domain from URL."""
    try:
        parsed = urlparse(url)
        return (parsed.netloc or url).lower().split(":")[0]
    except Exception:
        return url.lower()


class DomainThrottlePolicy:
    """Manages concurrency locks and adaptive backoff per portal domain."""

    def __init__(self, default_concurrency: int = DEFAULT_MAX_CONCURRENCY):
        self.default_concurrency = default_concurrency
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._last_request_time: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def _get_semaphore(self, domain: str) -> asyncio.Semaphore:
        async with self._lock:
            if domain not in self._semaphores:
                self._semaphores[domain] = asyncio.Semaphore(self.default_concurrency)
            return self._semaphores[domain]

    async def acquire(self, url: str) -> str:
        """Acquire domain semaphore and wait for rate-limit spacing."""
        domain = extract_domain(url)
        sem = await self._get_semaphore(domain)
        await sem.acquire()

        # Check stored throttle state
        state = db.get_domain_throttle(domain)
        now = time.time()

        if state and state.get("backoff_until", 0) > now:
            wait_time = state["backoff_until"] - now
            await asyncio.sleep(min(wait_time, 15.0))

        last_time = self._last_request_time.get(domain, 0.0)
        delay = state["current_delay_sec"] if state else DEFAULT_DOMAIN_DELAY
        # Add small jitter +/- 15%
        jittered_delay = delay * random.uniform(0.85, 1.15)
        elapsed = now - last_time
        if elapsed < jittered_delay:
            await asyncio.sleep(jittered_delay - elapsed)

        self._last_request_time[domain] = time.time()
        return domain

    def release(self, url: str, is_throttled: bool = False) -> None:
        """Release domain semaphore and record throttle/success state."""
        domain = extract_domain(url)
        sem = self._semaphores.get(domain)
        if sem:
            try:
                sem.release()
            except ValueError:
                pass

        if is_throttled:
            state = db.get_domain_throttle(domain)
            current_delay = state["current_delay_sec"] if state else DEFAULT_DOMAIN_DELAY
            new_delay = min(current_delay * 2.0, MAX_BACKOFF_SECONDS)
            db.record_domain_request(domain, is_throttled=True, backoff_delay=new_delay)
        else:
            db.record_domain_request(domain, is_throttled=False, backoff_delay=DEFAULT_DOMAIN_DELAY)


# Global singleton throttle policy
GLOBAL_THROTTLE = DomainThrottlePolicy()
