"""Route-level tests for GET /api/v1/layer3/sec-xbrl/activation-posture.

Coverage:
1. Returns HTTP 200 with correct schema_id and all six surfaces.
2. Active states match the default flag values from config.
3. live_sec_acquisition surface has class=hold_live; others have class=active.
4. controls block asserts raw_values_returned=False and public_surface=True.
5. No authority artifact (email / local path / sec.gov / raw 10-digit CIK / key)
   leaks in the response body.
6. review_ui static file references the activation-posture endpoint path (wiring check).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import bootstrap_storage_tree, settings
from app.api.deps import get_db
from app.db.session import Base
from main import app


ROUTE_URL = "/api/v1/layer3/sec-xbrl/activation-posture"
LAYER3_HTML_PATH = BACKEND / "app" / "review_ui" / "static" / "layer3.html"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient with in-memory SQLite; mirrors the pattern from
    test_sec_xbrl_e2e_offline_orchestrator_route.py."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Authority-artifact assertion (mirrors test_sec_xbrl_e2e_offline_orchestrator_route.py)
# ---------------------------------------------------------------------------

def _assert_no_authority_artifacts(body_text: str) -> None:
    email_re = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    assert not email_re.search(body_text), f"Email artifact in response: {body_text[:500]}"
    assert not re.search(r"[A-Za-z]:[\\/]", body_text), f"Local path in response: {body_text[:500]}"
    assert "sec.gov" not in body_text.lower(), f"SEC URL in response: {body_text[:500]}"
    cik_contextual = re.compile(
        r"(?:cik|filer|issuer|registrant)[^\n]{0,40}\b\d{10}\b", re.IGNORECASE
    )
    assert not cik_contextual.search(body_text), f"Raw CIK in response: {body_text[:500]}"


# ---------------------------------------------------------------------------
# 1. HTTP 200 and schema_id
# ---------------------------------------------------------------------------

def test_activation_posture_returns_200(client) -> None:
    response = client.get(ROUTE_URL)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("schema_id") == "layer3.sec_xbrl_activation_posture.v1", body
    assert body.get("status") == "ok", body


# ---------------------------------------------------------------------------
# 2. All six surfaces present with correct default active states
# ---------------------------------------------------------------------------

def test_activation_posture_surfaces_default_active_states(client) -> None:
    """Default flag values (from config.py) determine active states:
    - value_reveal_submit: True (default_on)
    - arelle_fact_authority_cutover: True (default_on)
    - multi_filing_gate_route: True (default_on)
    - e2e_offline_orchestrator_route: True (default_on)
    - arelle_value_reveal: False (default_off)
    - live_sec_acquisition: False (default_off)
    """
    response = client.get(ROUTE_URL)
    assert response.status_code == 200, response.text
    body = response.json()

    surfaces = body.get("surfaces", [])
    assert isinstance(surfaces, list), body
    assert len(surfaces) == 6, f"Expected 6 surfaces, got {len(surfaces)}: {[s.get('key') for s in surfaces]}"

    by_key = {s["key"]: s for s in surfaces}

    assert by_key["value_reveal_submit"]["active"] is True, by_key["value_reveal_submit"]
    assert by_key["arelle_fact_authority_cutover"]["active"] is True, by_key["arelle_fact_authority_cutover"]
    assert by_key["multi_filing_gate_route"]["active"] is True, by_key["multi_filing_gate_route"]
    assert by_key["e2e_offline_orchestrator_route"]["active"] is True, by_key["e2e_offline_orchestrator_route"]
    assert by_key["arelle_value_reveal"]["active"] is False, by_key["arelle_value_reveal"]
    assert by_key["live_sec_acquisition"]["active"] is False, by_key["live_sec_acquisition"]


# ---------------------------------------------------------------------------
# 3. class field: live_sec_acquisition is hold_live; all others are active
# ---------------------------------------------------------------------------

def test_activation_posture_surface_classes(client) -> None:
    response = client.get(ROUTE_URL)
    assert response.status_code == 200, response.text
    body = response.json()
    by_key = {s["key"]: s for s in body.get("surfaces", [])}

    assert by_key["live_sec_acquisition"]["class"] == "hold_live", by_key["live_sec_acquisition"]
    for key in ("value_reveal_submit", "arelle_fact_authority_cutover", "multi_filing_gate_route",
                "e2e_offline_orchestrator_route", "arelle_value_reveal"):
        assert by_key[key]["class"] == "active", by_key[key]


# ---------------------------------------------------------------------------
# 4. controls block
# ---------------------------------------------------------------------------

def test_activation_posture_controls_block(client) -> None:
    response = client.get(ROUTE_URL)
    assert response.status_code == 200, response.text
    body = response.json()
    controls = body.get("controls", {})
    assert controls.get("raw_values_returned") is False, controls
    assert controls.get("public_surface") is True, controls


# ---------------------------------------------------------------------------
# 5. auth_owner_mode present (enum string only, no identity)
# ---------------------------------------------------------------------------

def test_activation_posture_auth_owner_mode_present(client) -> None:
    response = client.get(ROUTE_URL)
    assert response.status_code == 200, response.text
    body = response.json()
    auth_owner_mode = body.get("auth_owner_mode")
    assert auth_owner_mode in ("none", "proxy"), f"Unexpected auth_owner_mode: {auth_owner_mode}"


# ---------------------------------------------------------------------------
# 6. No authority artifacts in response
# ---------------------------------------------------------------------------

def test_activation_posture_no_authority_artifacts(client) -> None:
    response = client.get(ROUTE_URL)
    assert response.status_code == 200, response.text
    body_text = json.dumps(response.json(), sort_keys=True)
    _assert_no_authority_artifacts(body_text)


# ---------------------------------------------------------------------------
# 7. Flag monkeypatch: toggling a flag changes active state
# ---------------------------------------------------------------------------

def test_activation_posture_flag_monkeypatch_changes_active(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "layer3_sec_xbrl_controlled_value_reveal_submit_enabled", False)
    response = client.get(ROUTE_URL)
    assert response.status_code == 200, response.text
    body = response.json()
    by_key = {s["key"]: s for s in body.get("surfaces", [])}
    assert by_key["value_reveal_submit"]["active"] is False, by_key["value_reveal_submit"]


# ---------------------------------------------------------------------------
# 8. Static wiring: layer3.html references the endpoint path
# ---------------------------------------------------------------------------

def test_review_ui_layer3_html_references_activation_posture_endpoint() -> None:
    """No real browser required — just checks the endpoint path string is wired in."""
    assert LAYER3_HTML_PATH.is_file(), f"layer3.html not found at {LAYER3_HTML_PATH}"
    content = LAYER3_HTML_PATH.read_text(encoding="utf-8")
    assert "/api/v1/layer3/sec-xbrl/activation-posture" in content, (
        "layer3.html does not reference the activation-posture endpoint path"
    )
