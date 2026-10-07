"""Active reachability probe for every registered source.

Source health used to be written only as a side effect of a user search
(``_collect_items`` step 5), so a portal that died between searches stayed green.
This loop pings each source on a timer, feeds the result through the same
``db.record_search_*`` / ``health.*`` path a search would use, and holds dead
sources off ``enabled`` until they come back.
"""

from __future__ import annotations

import asyncio
import os
import time

import db
from http_client import AsyncHttpClient
from sources import DEGRADED_THRESHOLD, get_all_source_configs, health

# Reachable probes before a probe-disabled source is let back in. 2 means one lucky
# answer never re-enables a flapping portal.
PROBE_RECOVERY_THRESHOLD = 2

# How often the loop probes. Must comfortably exceed a full sweep (~20 sources,
# concurrency 5, 7s timeout each ≈ 30s worst case).
SOURCE_PROBE_INTERVAL_SECONDS = float(os.environ.get("SOURCE_PROBE_INTERVAL_SECONDS", "300"))

# Bounded fan-out: never open one connection per registered source at once.
_PROBE_CONCURRENCY = 5
_PROBE_TIMEOUT_SECONDS = 7.0

# Consecutive reachable probes per source. In-memory on purpose: it is a flapping
# guard, not authority. Losing it on restart only delays re-enable by one sweep,
# while ``source_configs.auto_disabled_at`` (persistent) is what keeps the probe's
# hold visible across restarts. ponytail: persist alongside auto_disabled_at if a
# restart during the streak ever matters.
_reachable_streak: dict[str, int] = {}


def decide(
    consecutive_failures: int,
    reachable_streak: int,
    enabled: bool,
    auto_disabled_at: float | None,
) -> str | None:
    """Pure policy: what should happen to a source after one probe?

    - "disable": at the failure threshold while on (same threshold that makes a
      source degraded, FR-018a).
    - "enable":   the probe holds it off (``auto_disabled_at`` set) and it has
      answered PROBE_RECOVERY_THRESHOLD probes in a row.
    - None: leave it alone.

    An operator-disabled source (off with no marker) is never re-enabled.
    """
    if enabled:
        if consecutive_failures >= DEGRADED_THRESHOLD:
            return "disable"
        return None
    if auto_disabled_at is not None and reachable_streak >= PROBE_RECOVERY_THRESHOLD:
        return "enable"
    return None


async def probe_source(address: str, client: AsyncHttpClient) -> bool:
    """True when the portal answers at all (2xx/3xx), False on any error."""
    if not address or not address.startswith(("http://", "https://")):
        return False
    try:
        resp = await client.get(address, timeout=_PROBE_TIMEOUT_SECONDS)
    except Exception:
        return False
    return 200 <= resp.status_code < 400


async def probe_all() -> None:
    """Probe every enabled (or probe-disabled) source and record the outcome."""
    overrides = db.get_source_configs()
    sem = asyncio.Semaphore(_PROBE_CONCURRENCY)
    configs = {c.id: c for c in get_all_source_configs()}

    async with AsyncHttpClient(timeout=_PROBE_TIMEOUT_SECONDS) as client:

        async def _one(source_id: str, address: str) -> None:
            async with sem:
                ok = await probe_source(address, client)

            if ok:
                _reachable_streak[source_id] = _reachable_streak.get(source_id, 0) + 1
                try:
                    db.record_search_success(source_id)
                    health.record_reachable(source_id, address=address)
                except Exception:
                    pass  # health bookkeeping must never kill the sweep
            else:
                _reachable_streak[source_id] = 0
                try:
                    db.record_search_failure(source_id)
                    health.record_failure(source_id, reason="پاسخ‌گو نیست", address=address)
                except Exception:
                    pass

            # Decide on fresh DB state: a slow probe must not act on a snapshot
            # taken before a concurrent one recorded its result.
            try:
                row = db.get_source_config(source_id) or {}
                action = decide(
                    consecutive_failures=db.get_consecutive_failures(source_id),
                    reachable_streak=_reachable_streak.get(source_id, 0),
                    enabled=bool(row.get("enabled", True)),
                    auto_disabled_at=row.get("auto_disabled_at"),
                )
            except Exception:
                return
            if action is not None:
                _set_enabled(source_id, enabled=action == "enable", auto=action == "disable")

        # Must stay inside the `async with`: _one fires requests on this client,
        # and a coroutine created outside the block would run against a closed one
        # (every probe fails instantly with "client has been closed").
        tasks = []
        for source_id, cfg in configs.items():
            row = overrides.get(source_id)
            if row is None:
                # Never touched by operator or probe: follow config.
                if not cfg.enabled:
                    continue
            elif not row["enabled"] and row.get("auto_disabled_at") is None:
                # Operator-disabled (no probe marker): re-probing a deliberately off
                # portal is wasted load, and decide() would not re-enable it anyway.
                continue
            address = (
                row.get("base_url") if row and row.get("base_url") else cfg.primary_base_url
            )
            tasks.append(_one(source_id, address))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def _set_enabled(source_id: str, *, enabled: bool, auto: bool) -> None:
    """Persist a probe's on/off decision, marking ownership (auto = probe-held)."""
    try:
        cfg = {c.id: c for c in get_all_source_configs()}.get(source_id)
        if cfg is None:
            return
        row = db.get_source_config(source_id) or {}
        db.upsert_source_config(
            source_id=source_id,
            category=cfg.category.value,
            name=cfg.name,
            base_url=row.get("base_url") or cfg.primary_base_url,
            mirror_url=row.get("mirror_url"),
            enabled=enabled,
        )
        db.set_source_auto_disabled(source_id, time.time() if auto else None)
    except Exception:
        pass  # failed bookkeeping must never kill the loop


async def probe_loop(interval: float = SOURCE_PROBE_INTERVAL_SECONDS) -> None:
    """Probe forever. Each sweep is isolated: one bad sweep never ends the loop."""
    while True:
        await asyncio.sleep(interval)
        try:
            await probe_all()
        except asyncio.CancelledError:
            raise
        except Exception:
            continue
