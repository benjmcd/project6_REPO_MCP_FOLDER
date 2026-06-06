"""Route-level tests for POST /api/v1/layer3/sec-xbrl/e2e/offline-operator-review/open.

Coverage:
1. Enabled happy path: valid offline evidence -> HTTP 200 with workflow id and
   offline-safety controls (source_acquisition_performed=False, arelle_invoked=False).
   Also asserts no authority artifact leaks (email/path/url/raw cik) in response body.
2. Feature-flag off (explicit-off): flag monkeypatched False -> fail-closed disabled
   response with the feature-flag disabled error code.
3. Proxy fail-closed: auth_owner=proxy + trusted_proxy_mode=True but identity header
   absent -> 401 auth-policy block.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

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
from app.services.layer3_utils import stable_hash
from main import app


ROUTE_URL = "/api/v1/layer3/sec-xbrl/e2e/offline-operator-review/open"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient with in-memory SQLite; mirrors the pattern from
    test_sec_xbrl_route_level_auth_enforcement.py."""
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


@pytest.fixture()
def proxy_fail_closed_client(tmp_path, monkeypatch):
    """Client with auth_owner=proxy and trusted_proxy_mode=True; requests without
    the identity header trigger the 401 fail-closed path."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", "x-forwarded-user")
    monkeypatch.setattr(settings, "proxy_groups_header", "x-forwarded-groups")
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
# Evidence builders (adapted from test_sec_xbrl_e2e_offline_orchestrator.py)
# ---------------------------------------------------------------------------

def _hash(char: str) -> str:
    return char * 64


def _namespace(taxonomy: str) -> str:
    if taxonomy == "dei":
        return "xbrl.sec.gov/dei/test"
    return "fasb.org/us-gaap/test"


def _unit(unit_name: str) -> dict[str, Any]:
    if unit_name == "unitless":
        return {"measures": []}
    return {"currency": f"iso4217:{unit_name}", "measures": [f"iso4217:{unit_name}"]}


def _record(
    fact_id: str,
    taxonomy: str,
    local_name: str,
    unit_name: str,
    *,
    start: str = "start-2",
    end: str = "end-2",
    instant: bool = False,
) -> dict[str, Any]:
    period = {"type": "instant", "instant": end} if instant else {"type": "duration", "start": start, "end": end}
    return {
        "resolved_fact_id": fact_id,
        "concept": {"namespace": _namespace(taxonomy), "local_name": local_name, "standard": True},
        "unit": _unit(unit_name),
        "period": period,
        "dimensions": {"explicit": [], "typed": []},
    }


def _value_rec(fact_id: str, effective_value: str) -> dict[str, Any]:
    return {"resolved_fact_id": fact_id, "effective_value": effective_value}


def _redacted_fact(record: dict[str, Any]) -> dict[str, Any]:
    from app.services.layer3_utils import json_clone
    value = json_clone(record)
    value["value_redacted"] = True
    return value


def _companyfacts_periods(entries: list[tuple[str, str, str, str, str, str, bool]]) -> dict[str, Any]:
    facts: dict[str, dict[str, Any]] = {}
    for taxonomy, local_name, val, unit, start, end, instant in entries:
        facts.setdefault(taxonomy, {}).setdefault(local_name, {"units": {}})
        fact: dict[str, Any] = {"fp": "FY", "fy": "", "val": val, "end": end}
        if not instant:
            fact["start"] = start
        facts[taxonomy][local_name]["units"].setdefault(unit, []).append(fact)
    return facts


def _offline_evidence() -> dict[str, Any]:
    sidecar_records = [
        _record("rf-revenue-old", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", start="start-1", end="end-1"),
        _record("rf-assets-old", "us-gaap", "Assets", "USD", end="end-1", instant=True),
        _record("rf-cashflow-old", "us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD", start="start-1", end="end-1"),
        _record("rf-revenue-fy", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", start="start-2", end="end-2"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", end="end-2", instant=True),
        _record("rf-cashflow-fy", "us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD", start="start-2", end="end-2"),
        _record("rf-period-end", "dei", "DocumentPeriodEndDate", "unitless", end="end-2", instant=True),
    ]
    value_records = [
        _value_rec("rf-revenue-old", "90"),
        _value_rec("rf-assets-old", "180"),
        _value_rec("rf-cashflow-old", "30"),
        _value_rec("rf-revenue-fy", "100"),
        _value_rec("rf-assets-fy", "200"),
        _value_rec("rf-cashflow-fy", "40"),
        _value_rec("rf-period-end", "end-2"),
    ]
    value_store_hash = stable_hash(value_records)
    resolved_fact_projection = [_redacted_fact(record) for record in sidecar_records]
    return {
        "companyfacts": _companyfacts_periods([
            ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "90", "USD", "start-1", "end-1", False),
            ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "100", "USD", "start-2", "end-2", False),
            ("us-gaap", "Assets", "180", "USD", "", "end-1", True),
            ("us-gaap", "Assets", "200", "USD", "", "end-2", True),
            ("us-gaap", "NetCashProvidedByUsedInOperatingActivities", "30", "USD", "start-1", "end-1", False),
            ("us-gaap", "NetCashProvidedByUsedInOperatingActivities", "40", "USD", "start-2", "end-2", False),
        ]),
        "sidecar_receipt": {
            "sidecar_receipt_id": "sidecar-receipt-route-test",
            "sidecar_receipt_hash": _hash("b"),
            "resolved_fact_records": sidecar_records,
            "resolved_fact_projection": resolved_fact_projection,
            "resolved_fact_inventory_hash": stable_hash(resolved_fact_projection),
            "internal_value_store": {"value_store_hash": value_store_hash, "value_record_count": len(value_records)},
            "authority_hashes": {"internal_value_store_hash": value_store_hash, "sidecar_receipt_hash": _hash("b")},
        },
        "value_store": {"value_records": value_records, "value_store_hash": value_store_hash},
        "statement_role_view_records": [
            {"fact_id_or_order_key": "rf-revenue-old", "statement_candidate_role": "income_statement"},
            {"fact_id_or_order_key": "rf-assets-old", "statement_candidate_role": "balance_sheet"},
            {"fact_id_or_order_key": "rf-cashflow-old", "statement_candidate_role": "cash_flow_statement"},
            {"fact_id_or_order_key": "rf-revenue-fy", "statement_candidate_role": "income_statement"},
            {"fact_id_or_order_key": "rf-assets-fy", "statement_candidate_role": "balance_sheet"},
            {"fact_id_or_order_key": "rf-cashflow-fy", "statement_candidate_role": "cash_flow_statement"},
        ],
        "dataset_version_id": "dataset-route-test",
    }


def _request_payload(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "client_request_id": "route-test-e2e-offline-open",
        "open_mode": "sec_xbrl_e2e_offline_operator_review_open_v1",
        "operator_action": "open_redacted_operator_review_from_offline_evidence",
        "evidence": evidence if evidence is not None else _offline_evidence(),
        "period_limit": 2,
    }


# ---------------------------------------------------------------------------
# 1. Enabled happy path
# ---------------------------------------------------------------------------

def test_route_e2e_offline_operator_review_open_happy_path(client) -> None:
    """POST enabled route with valid offline evidence returns HTTP 200 with a
    populated operator-review workflow id and offline-safety controls."""
    response = client.post(ROUTE_URL, json=_request_payload())
    assert response.status_code == 200, response.text
    body = response.json()

    # Workflow id present and non-empty
    workflow_id = body.get("sec_xbrl_operator_review_workflow_id")
    assert workflow_id and isinstance(workflow_id, str), body

    # Offline-safety controls must confirm no network / arelle / acquisition
    controls = body.get("controls", {})
    assert controls.get("source_acquisition_performed") is False, controls
    assert controls.get("arelle_invoked") is False, controls
    assert controls.get("offline_evidence_input_only") is True, controls
    assert controls.get("value_reveal_performed") is False, controls
    assert controls.get("file_write_performed") is True, controls

    containment = body.get("containment", {})
    assert containment.get("server_owned_dataset_version_authority_materialized") is True, containment
    assert containment.get("server_owned_sidecar_authority_materialized") is True, containment
    assert containment.get("file_backed_sidecar_authority_sql_rollback_claimed") is False, containment

    # Status must be review_ready
    assert body.get("status") == "review_ready", body

    # Auth policy metadata present in response
    assert body.get("auth_route_family") == "sec_xbrl_operator_review_decision_submit_write", body
    assert body.get("auth_policy_status") == "admitted", body
    assert body.get("auth_binding_required") is True, body
    assert body.get("auth_binding_ref", "").startswith("sec-xbrl-auth-binding:"), body
    assert body.get("auth_binding_route_family") == "sec_xbrl_operator_review_decision_submit_write", body

    # No authority artifact should leak in the response body
    body_text = json.dumps(body, sort_keys=True)
    _assert_no_authority_artifacts(body_text)


def _assert_no_authority_artifacts(body_text: str) -> None:
    import re
    # No email addresses
    email_re = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    assert not email_re.search(body_text), f"Email artifact in response: {body_text[:500]}"
    # No Windows-style local paths
    assert not re.search(r"[A-Za-z]:[\\/]", body_text), f"Local path in response: {body_text[:500]}"
    # No SEC URLs
    assert "sec.gov" not in body_text.lower(), f"SEC URL in response: {body_text[:500]}"
    # No raw 10-digit CIK patterns preceded by contextual markers
    cik_contextual = re.compile(
        r"(?:cik|filer|issuer|registrant)[^\n]{0,40}\b\d{10}\b", re.IGNORECASE
    )
    assert not cik_contextual.search(body_text), f"Raw CIK in response: {body_text[:500]}"


# ---------------------------------------------------------------------------
# 2. Feature-flag off (explicit-off)
# ---------------------------------------------------------------------------

def test_route_e2e_offline_operator_review_open_feature_flag_off(client, monkeypatch) -> None:
    """With the feature flag monkeypatched to False the route returns a
    fail-closed disabled response and writes nothing."""
    monkeypatch.setattr(settings, "layer3_sec_xbrl_e2e_offline_orchestrator_route_enabled", False)
    response = client.post(ROUTE_URL, json=_request_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("status") == "blocked", body
    blocked_reasons = body.get("blocked_reasons", [])
    assert any(
        r.get("reason") == "sec_xbrl_e2e_offline_orchestrator_route_feature_flag_disabled"
        for r in blocked_reasons
    ), body
    assert body.get("ready") is False, body
    controls = body.get("controls", {})
    assert controls.get("api_route_enabled") is False, controls
    assert controls.get("source_acquisition_performed") is False, controls
    assert controls.get("arelle_invoked") is False, controls


# ---------------------------------------------------------------------------
# 3. Proxy fail-closed: missing identity header -> 401
# ---------------------------------------------------------------------------

def test_route_e2e_offline_operator_review_open_proxy_fail_closed_missing_identity(
    proxy_fail_closed_client,
) -> None:
    """POST with auth_owner=proxy + trusted_proxy_mode=True but without the
    identity header returns 401 auth-policy block."""
    response = proxy_fail_closed_client.post(
        ROUTE_URL,
        json=_request_payload(),
        # No X-Forwarded-User header -> missing identity authority
    )
    assert response.status_code == 401, response.text
    body = response.json()
    assert body.get("schema_id") == "layer3.workbench_error.v1", body
    assert body.get("status") == "blocked", body
    assert "missing_identity_authority" in body.get("error_code", ""), body
