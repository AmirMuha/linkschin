"""Tests for source management, JWT operator authentication, and suggestions (US3)."""

import os
from fastapi.testclient import TestClient
from web.app import app
import db
from web.auth import hash_password

client = TestClient(app)


def test_auth_and_sources_lifecycle():
    # 1. Seed test operator into database
    test_user = "test_operator"
    test_pass = "SecurePass123!"
    db.create_operator_user(test_user, hash_password(test_pass), role="admin")

    # Login with operator credentials
    login_resp = client.post("/api/auth/login", json={"username": test_user, "password": test_pass})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Unauthorized request to PATCH /api/sources/uptvs
    bad_resp = client.patch("/api/sources/uptvs", json={"base_url": "https://new.uptvs.com"})
    assert bad_resp.status_code == 401

    # 3. Authorized request to update source
    patch_resp = client.patch(
        "/api/sources/uptvs",
        json={"base_url": "https://new.uptvs.com", "mirror_url": "https://mirror.uptvs.com"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["base_url"] == "https://new.uptvs.com"

    # 4. Toggle source
    toggle_resp = client.patch("/api/sources/uptvs/toggle", json={"enabled": False}, headers=headers)
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["enabled"] == 0

    # 5. Community suggestion with deduplication
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_domain = f"test-{uid}.ir"
    sug_resp1 = client.post(
        "/api/sources/suggest",
        json={
            "url": f"https://{test_domain}/post/1",
            "category": "movies",
            "source_name": "TestMedia",
        },
    )
    assert sug_resp1.status_code == 201
    assert sug_resp1.json()["request_count"] == 1

    # Duplicate submission increments counter
    sug_resp2 = client.post(
        "/api/sources/suggest",
        json={
            "url": f"https://{test_domain}/another",
            "category": "movies",
            "source_name": "TestMedia Mirror",
        },
    )
    assert sug_resp2.status_code == 201
    assert sug_resp2.json()["request_count"] >= 2


def test_address_edit_preserves_disabled_state():
    """Saving a base URL must not silently re-enable a source that was turned off.

    upsert_source_config's ON CONFLICT writes `enabled = excluded.enabled`, so the
    PATCH handler has to pass the current value through (default is True).
    """
    db.create_operator_user("test_operator", hash_password("SecurePass123!"), role="admin")
    login = client.post(
        "/api/auth/login", json={"username": "test_operator", "password": "SecurePass123!"}
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    original = db.get_source_config("uptvs") or {}
    was_enabled = bool(original.get("enabled", True))
    try:
        client.patch("/api/sources/uptvs/toggle", json={"enabled": False}, headers=headers)

        edit = client.patch(
            "/api/sources/uptvs",
            json={"base_url": "https://changed.uptvs.example"},
            headers=headers,
        )
        assert edit.status_code == 200
        assert db.get_source_config("uptvs")["enabled"] == 0  # still off after the edit
    finally:
        client.patch(
            "/api/sources/uptvs/toggle", json={"enabled": was_enabled}, headers=headers
        )


def test_probe_decide_policy():
    """The probe's on/off policy at every boundary (web/probe.py::decide)."""
    from web.probe import PROBE_RECOVERY_THRESHOLD, decide

    # Below the failure threshold: leave it alone.
    assert decide(2, 0, enabled=True, auto_disabled_at=None) is None
    # At the threshold (FR-018a): hold it off.
    assert decide(3, 0, enabled=True, auto_disabled_at=None) == "disable"
    # Probe holds it off but has not answered enough probes yet.
    assert decide(0, PROBE_RECOVERY_THRESHOLD - 1, enabled=False, auto_disabled_at=1.0) is None
    # Probe holds it off and it answered: let it back in.
    assert decide(0, PROBE_RECOVERY_THRESHOLD, enabled=False, auto_disabled_at=1.0) == "enable"
    # Operator-disabled (no probe marker): never re-enable, however healthy it looks.
    assert decide(0, 99, enabled=False, auto_disabled_at=None) is None
    # Healthy while on: nothing to do.
    assert decide(0, 0, enabled=True, auto_disabled_at=None) is None
