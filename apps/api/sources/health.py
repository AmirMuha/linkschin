"""Per-source health state tracking, persistence, and circuit breaker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any

from models import SourceConfig


class SourceState(str, Enum):
    """Operational states for content sources (FR-008)."""
    PROVIDING_RESULTS = "providing_results"
    SUBSCRIPTION_ONLY = "subscription_only"
    UNREACHABLE = "unreachable"
    REQUIRES_LOGIN = "requires_login"
    NOT_YET_PROVEN = "not_yet_proven"


CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 60.0

# Initial default states and reasons for known unconfirmed / problematic sites
INITIAL_UNPROVEN_SITES: dict[str, tuple[SourceState, str]] = {
    "ndamedia": (SourceState.NOT_YET_PROVEN, "دامنه تایید شده‌ای ثبت نشده است"),
    "salamcinema": (SourceState.NOT_YET_PROVEN, "دامنه تایید شده‌ای ثبت نشده است"),
    "tiwall": (SourceState.NOT_YET_PROVEN, "حلقه ریدایرکت (۳۰۷) — در انتظار دامنه جایگزین"),
    "fam": (SourceState.NOT_YET_PROVEN, "حلقه ریدایرکت (۳۰۸) — در انتظار دامنه جایگزین"),
}


@dataclass
class SourceHealth:
    """Operational health record for a single source."""
    source_id: str
    state: SourceState = SourceState.PROVIDING_RESULTS
    reason: str | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None
    consecutive_failures: int = 0
    active_address: str | None = None


class CircuitBreaker:
    """In-memory circuit breaker per network address."""

    def __init__(self, failure_threshold: int = CIRCUIT_BREAKER_THRESHOLD, cooldown: float = CIRCUIT_BREAKER_COOLDOWN_SECONDS):
        self.threshold = failure_threshold
        self.cooldown = cooldown
        self.failures: dict[str, int] = {}
        self.last_failure_time: dict[str, float] = {}

    def is_available(self, address: str) -> bool:
        """Return True if address is not tripped or cooldown has expired."""
        addr = address.strip().lower()
        count = self.failures.get(addr, 0)
        if count < self.threshold:
            return True
        last_time = self.last_failure_time.get(addr, 0.0)
        if time.time() - last_time >= self.cooldown:
            # Cooldown passed, allow trial attempt
            return True
        return False

    def record_failure(self, address: str) -> None:
        """Increment failure counter and update timestamp."""
        addr = address.strip().lower()
        self.failures[addr] = self.failures.get(addr, 0) + 1
        self.last_failure_time[addr] = time.time()

    def record_success(self, address: str) -> None:
        """Reset failures on successful request."""
        addr = address.strip().lower()
        self.failures.pop(addr, None)
        self.last_failure_time.pop(addr, None)

    def reset(self) -> None:
        """Clear all breaker tracking."""
        self.failures.clear()
        self.last_failure_time.clear()


GLOBAL_BREAKER = CircuitBreaker()
_REGISTRY: dict[str, SourceHealth] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(source_id: str) -> SourceHealth:
    """Get or lazily initialize source health."""
    if source_id not in _REGISTRY:
        if source_id in INITIAL_UNPROVEN_SITES:
            init_state, init_reason = INITIAL_UNPROVEN_SITES[source_id]
            _REGISTRY[source_id] = SourceHealth(
                source_id=source_id,
                state=init_state,
                reason=init_reason,
            )
        else:
            _REGISTRY[source_id] = SourceHealth(
                source_id=source_id,
                state=SourceState.PROVIDING_RESULTS,
            )
    return _REGISTRY[source_id]


def record_success(source_id: str, address: str | None = None, provides_downloads: bool = True) -> None:
    """Record successful results retrieval from a source."""
    h = get(source_id)
    h.consecutive_failures = 0
    h.last_success_at = _now_iso()
    if address:
        h.active_address = address
        GLOBAL_BREAKER.record_success(address)

    # Automatic recovery to active state (FR-009c)
    if not provides_downloads:
        h.state = SourceState.SUBSCRIPTION_ONLY
        h.reason = "سرویس اشتراکی — بدون لینک دانلود عمومی"
    else:
        h.state = SourceState.PROVIDING_RESULTS
        h.reason = None

    _sync_to_db(h)


def record_failure(source_id: str, reason: str | None = None, address: str | None = None) -> None:
    """Record scrape or network failure for a source."""
    h = get(source_id)
    # Sticky login state: do not alter if already requires_login
    if h.state == SourceState.REQUIRES_LOGIN:
        return

    h.consecutive_failures += 1
    h.last_failure_at = _now_iso()
    if address:
        GLOBAL_BREAKER.record_failure(address)

    r_lower = (reason or "").lower()
    if any(k in r_lower for k in ("challenge", "cloudflare", "captcha", "sign-in", "login", "requires_login")):
        h.state = SourceState.REQUIRES_LOGIN
        h.reason = "نیازمند ورود کاربر یا حل چالش امنیتی"
    elif h.consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
        h.state = SourceState.UNREACHABLE
        h.reason = reason or "دامنه پاسخ نمی‌دهد"
    else:
        h.reason = reason or "خطا در دریافت اطلاعات"

    _sync_to_db(h)


def record_empty_response(source_id: str) -> None:
    """Record HTTP 200 with 0 parseable results (silent break detection, FR-019)."""
    h = get(source_id)
    if h.state == SourceState.REQUIRES_LOGIN:
        return

    h.consecutive_failures += 1
    h.last_failure_at = _now_iso()

    if h.consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
        h.state = SourceState.UNREACHABLE
        h.reason = "تغییر ساختار یا پاسخ خالی"

    _sync_to_db(h)


def get_all() -> dict[str, SourceHealth]:
    """Return all tracked health states."""
    return _REGISTRY


def get_counts() -> dict[str, int]:
    """Return counts grouped by SourceState."""
    counts = {s.value: 0 for s in SourceState}
    for h in _REGISTRY.values():
        counts[h.state.value] = counts.get(h.state.value, 0) + 1
    return counts


def reset_registry() -> None:
    """Reset in-memory registry and circuit breaker."""
    _REGISTRY.clear()
    GLOBAL_BREAKER.reset()


def _sync_to_db(health: SourceHealth) -> None:
    """Persist source health state to SQLite if possible."""
    try:
        import db
        conn = db.connect()
        try:
            db.set_source_health(
                conn=conn,
                source_id=health.source_id,
                state=health.state.value,
                reason=health.reason,
                last_success_at=health.last_success_at,
                last_failure_at=health.last_failure_at,
                consecutive_failures=health.consecutive_failures,
                active_address=health.active_address,
            )
        finally:
            conn.close()
    except Exception:
        pass
