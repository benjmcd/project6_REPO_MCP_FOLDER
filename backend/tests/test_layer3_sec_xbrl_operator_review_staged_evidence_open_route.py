"""Route-level tests for POST /sec-xbrl/operator-review/workflow/open-from-staged-evidence.

Proves:
1. Happy path: staged storage + hashes → 200, review_ready workflow, no raw-value leak.
2. Chain to status: open response binds correctly so status route accepts it.
3. Missing evidence → 404 with a _missing-suffixed error code (fail-closed).
4. Extra request fields → 400 with governed-fields error code.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
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
from main import app

from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_contract as classification_contract,
    layer3_sec_xbrl_offline_evidence_loader as loader,
)
from app.services.layer3_utils import json_clone, stable_hash

# ---------------------------------------------------------------------------
# Route URL constants
# ---------------------------------------------------------------------------

OPEN_FROM_STAGED = "/api/v1/layer3/sec-xbrl/operator-review/workflow/open-from-staged-evidence"
WORKFLOW_STATUS = "/api/v1/layer3/sec-xbrl/operator-review/workflow/status"


# ---------------------------------------------------------------------------
# Storage staging helpers (replicated from test_sec_xbrl_offline_evidence_loader)
# ---------------------------------------------------------------------------

def _hash(char: str) -> str:
    return char * 64


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


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
    start: str,
    end: str,
    *,
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


def _redacted_fact(record: dict[str, Any]) -> dict[str, Any]:
    value = json_clone(record)
    value["value_redacted"] = True
    return value


def _sidecar_records() -> list[dict[str, Any]]:
    return [
        _record("rf-revenue-old", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", "start-1", "end-1"),
        _record("rf-assets-old", "us-gaap", "Assets", "USD", "", "end-1", instant=True),
        _record("rf-cashflow-old", "us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD", "start-1", "end-1"),
        _record("rf-revenue-fy", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", "start-2", "end-2"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", "", "end-2", instant=True),
        _record("rf-cashflow-fy", "us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD", "start-2", "end-2"),
        _record("rf-period-end", "dei", "DocumentPeriodEndDate", "unitless", "", "end-2", instant=True),
    ]


def _value_records() -> list[dict[str, str]]:
    return [
        {"resolved_fact_id": "rf-revenue-old", "effective_value": "90"},
        {"resolved_fact_id": "rf-assets-old", "effective_value": "180"},
        {"resolved_fact_id": "rf-cashflow-old", "effective_value": "30"},
        {"resolved_fact_id": "rf-revenue-fy", "effective_value": "100"},
        {"resolved_fact_id": "rf-assets-fy", "effective_value": "200"},
        {"resolved_fact_id": "rf-cashflow-fy", "effective_value": "40"},
        {"resolved_fact_id": "rf-period-end", "effective_value": "end-2"},
    ]


def _statement_roles() -> list[dict[str, Any]]:
    return [
        {"fact_id_or_order_key": "rf-revenue-old", "statement_candidate_role": "income_statement"},
        {"fact_id_or_order_key": "rf-assets-old", "statement_candidate_role": "balance_sheet"},
        {"fact_id_or_order_key": "rf-cashflow-old", "statement_candidate_role": "cash_flow_statement"},
        {"fact_id_or_order_key": "rf-revenue-fy", "statement_candidate_role": "income_statement"},
        {"fact_id_or_order_key": "rf-assets-fy", "statement_candidate_role": "balance_sheet"},
        {"fact_id_or_order_key": "rf-cashflow-fy", "statement_candidate_role": "cash_flow_statement"},
    ]


def _classification_receipt_hash(classification: dict[str, Any]) -> str:
    return stable_hash(
        classification_contract.classification_receipt_hash_basis(
            classification_mode=classification["classification_mode"],
            fact_authority_receipt_hash=classification["fact_authority_receipt_hash"],
            fact_material_bridge_receipt_hash=classification["fact_material_bridge_receipt_hash"],
            fact_inventory_hash=classification["fact_inventory_hash"],
            classification_inventory_hash=classification["classification_inventory_hash"],
            semantic_profile_inventory_hash=classification["semantic_profile_inventory_hash"],
            classification_order_hash=classification["classification_order_hash"],
            statement_group_inventory_hash=classification["statement_group_inventory_hash"],
            unclassified_fact_inventory_hash=classification["unclassified_fact_inventory_hash"],
            classification_diagnostics_hash=classification["classification_diagnostics_hash"],
        )
    )


def _stage_storage(storage: Path) -> dict[str, str]:
    """Write the minimal offline-evidence storage tree and return the disambiguation hashes."""
    sidecar_hash = _hash("b")
    sidecar_id = f"sec-edgar-arelle-resolved-fact-authority-{sidecar_hash[:24]}"
    bridge_hash = _hash("e")
    bridge_id = "sec-edgar-html-inline-xbrl-fact-material-bridge-" + "e" * 24
    sidecar_records = _sidecar_records()
    value_records = _value_records()
    value_store_hash = stable_hash(value_records)
    resolved_projection = [_redacted_fact(record) for record in sidecar_records]
    resolved_projection_hash = stable_hash(resolved_projection)
    statement_roles = _statement_roles()
    classification_inventory_hash = stable_hash(statement_roles)
    semantic_profile_inventory_hash = stable_hash([])
    classification_order_hash = stable_hash([item["fact_id_or_order_key"] for item in statement_roles])
    statement_group_inventory_hash = stable_hash([])
    unclassified_fact_inventory_hash = stable_hash([])
    classification_diagnostics_hash = stable_hash({})

    sidecar = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "sidecar_state": "sec_edgar_arelle_resolved_fact_authority_sidecar_ready",
        "resolved_fact_records": sidecar_records,
        "resolved_fact_projection": resolved_projection,
        "resolved_fact_inventory_hash": resolved_projection_hash,
        "internal_value_store": {
            "store_state": "persisted",
            "value_store_hash": value_store_hash,
            "value_record_count": len(value_records),
        },
        "authority_hashes": {
            "sidecar_receipt_hash": sidecar_hash,
            "internal_value_store_hash": value_store_hash,
        },
    }
    value_store = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_internal_value_store.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "value_record_count": len(value_records),
        "value_records": value_records,
    }
    classification = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification.v1",
        "classification_mode": "sec_edgar_html_inline_xbrl_fact_to_statement_classification_v1",
        "fact_authority_receipt_hash": sidecar_hash,
        "fact_inventory_hash": resolved_projection_hash,
        "fact_material_bridge_receipt_hash": bridge_hash,
        "classification_inventory_hash": classification_inventory_hash,
        "semantic_profile_inventory_hash": semantic_profile_inventory_hash,
        "classification_order_hash": classification_order_hash,
        "statement_group_inventory_hash": statement_group_inventory_hash,
        "unclassified_fact_inventory_hash": unclassified_fact_inventory_hash,
        "classification_diagnostics_hash": classification_diagnostics_hash,
        "authority_hashes": {
            "fact_authority_receipt_hash": sidecar_hash,
            "fact_inventory_hash": resolved_projection_hash,
            "fact_material_bridge_receipt_hash": bridge_hash,
        },
        "classification_inventory": statement_roles,
    }
    classification_hash = _classification_receipt_hash(classification)
    classification_id = f"sec-edgar-html-inline-xbrl-fact-statement-classification-{classification_hash[:24]}"
    classification["statement_classification_receipt_id"] = classification_id
    classification["statement_classification_receipt_hash"] = classification_hash

    bridge = {
        "fact_material_bridge_receipt_hash": bridge_hash,
        "fact_material_bridge_receipt_id": bridge_id,
        "response": {
            "arelle_sidecar_receipt_hash": sidecar_hash,
            "dataset_version_id": "dv-sec-ixbrl-facts-redacted",
        },
    }

    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / "receipts" / f"{sidecar_id}.json", sidecar)
    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / loader.VALUE_STORE_SUBDIR / f"{sidecar_id}.json", value_store)
    _write_json(
        storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts" / f"{classification_id}.json",
        classification,
    )
    _write_json(
        storage
        / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge"
        / "receipts"
        / f"{bridge_id}.json",
        bridge,
    )
    return {
        "sidecar_receipt_hash": sidecar_hash,
        "sidecar_receipt_id": sidecar_id,
        "classification_hash": classification_hash,
    }


# ---------------------------------------------------------------------------
# Fixture: TestClient with in-memory SQLite + staged storage
# ---------------------------------------------------------------------------

@pytest.fixture()
def staged_client(tmp_path, monkeypatch):
    """TestClient with an in-memory SQLite DB and a pre-staged offline evidence storage tree."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    bootstrap_storage_tree(storage_dir)
    refs = _stage_storage(storage_dir)

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
        yield test_client, refs
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def empty_storage_client(tmp_path, monkeypatch):
    """TestClient with an empty storage dir (no evidence staged)."""
    storage_dir = tmp_path / "empty-storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )

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
# Tests
# ---------------------------------------------------------------------------

def test_open_from_staged_evidence_opens_redacted_workflow(staged_client) -> None:
    """Staged storage + disambiguation hashes → 200, review_ready, no raw-value leak."""
    client, refs = staged_client
    client_request_id = f"test-open-from-staged-evidence-opens-redacted-{uuid.uuid4().hex[:12]}"

    resp = client.post(
        OPEN_FROM_STAGED,
        json={
            "client_request_id": client_request_id,
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
            "period_limit": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["status"] == "review_ready"
    assert body["sec_xbrl_operator_review_workflow_id"]
    assert body["sec_xbrl_statement_packet_set_id"]
    assert body["sec_xbrl_projection_set_id"]
    assert body["controls"]["value_reveal_performed"] is False
    assert body["controls"]["arelle_invoked"] is False
    assert body["controls"]["source_acquisition_performed"] is False
    assert body["auth_binding_ref"]
    # The route passes no companyfacts_path so the bundle status reflects that the
    # oracle was not supplied; the workflow still opens (review_ready).
    assert body["evidence_bundle_status"].startswith("offline_evidence_bundle_ready")

    # No raw value leak: staged raw concept ids and effective_value key must not appear in response.
    # Also assert that NON-fy fact ids (old-period) are absent — these are raw IDs that only
    # exist in the internal value store, not in the redacted projection surface.
    text = resp.text
    assert "rf-revenue-fy" not in text
    assert "rf-assets-fy" not in text
    assert "effective_value" not in text
    # Non-fy (old-period) resolved_fact_ids must also be absent from the redacted response
    assert "rf-revenue-old" not in text
    assert "rf-assets-old" not in text
    assert "rf-cashflow-old" not in text
    # The internal value_store JSON structure itself must not be serialised into the response
    assert "value_records" not in text
    assert "effective_value" not in text


def test_open_from_staged_evidence_chain_to_status(staged_client) -> None:
    """Open workflow → POST status with returned ids/hashes → 200 (binding accepted)."""
    client, refs = staged_client
    client_request_id = f"test-open-from-staged-chain-status-{uuid.uuid4().hex[:12]}"

    open_resp = client.post(
        OPEN_FROM_STAGED,
        json={
            "client_request_id": client_request_id,
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
        },
    )
    assert open_resp.status_code == 200, open_resp.text
    open_body = open_resp.json()

    workflow_id = open_body["sec_xbrl_operator_review_workflow_id"]
    workflow_basis_hash = open_body["workflow_basis_hash"]

    status_resp = client.post(
        WORKFLOW_STATUS,
        json={
            "client_request_id": f"status-{client_request_id}",
            "status_mode": "sec_xbrl_operator_review_workflow_status_v1",
            "operator_decision": "inspect_sec_xbrl_operator_review_workflow_status",
            "sec_xbrl_operator_review_workflow_id": workflow_id,
            "workflow_basis_hash": workflow_basis_hash,
        },
    )
    assert status_resp.status_code == 200, status_resp.text
    status_body = status_resp.json()
    assert status_body["sec_xbrl_operator_review_workflow_id"] == workflow_id


def test_open_from_staged_evidence_missing_evidence_is_fail_closed(empty_storage_client) -> None:
    """Empty storage dir → 404 with a _missing error code (fail-closed)."""
    client = empty_storage_client
    resp = client.post(
        OPEN_FROM_STAGED,
        json={
            "client_request_id": f"test-open-missing-{uuid.uuid4().hex[:12]}",
        },
    )
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body.get("error_code", "").endswith("_missing")


def test_open_from_staged_evidence_rejects_extra_fields(staged_client) -> None:
    """Extra fields in request body → 400 with governed-fields error code."""
    client, refs = staged_client
    resp = client.post(
        OPEN_FROM_STAGED,
        json={
            "client_request_id": f"test-extra-fields-{uuid.uuid4().hex[:12]}",
            "injected_junk_field": "should_be_rejected",
        },
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body.get("error_code") == (
        "sec_xbrl_operator_review_workflow_open_from_staged_evidence_request_fields_not_admitted"
    )


def test_open_from_staged_evidence_clean_idempotent_replay(staged_client) -> None:
    """Stage once, POST twice with same crid+params → both 200, same workflow_id and packet_set_id."""
    client, refs = staged_client
    client_request_id = f"test-idempotent-replay-{uuid.uuid4().hex[:12]}"
    payload = {
        "client_request_id": client_request_id,
        "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
        "expected_statement_classification_receipt_hash": refs["classification_hash"],
        "period_limit": 2,
    }

    resp1 = client.post(OPEN_FROM_STAGED, json=payload)
    assert resp1.status_code == 200, resp1.text
    body1 = resp1.json()

    resp2 = client.post(OPEN_FROM_STAGED, json=payload)
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()

    assert body1["sec_xbrl_operator_review_workflow_id"] == body2["sec_xbrl_operator_review_workflow_id"], (
        "Idempotent replay must return the same workflow_id"
    )
    assert body1["sec_xbrl_statement_packet_set_id"] == body2["sec_xbrl_statement_packet_set_id"], (
        "Idempotent replay must return the same statement_packet_set_id"
    )


def test_open_from_staged_evidence_replay_mismatch_is_governed_4xx(staged_client) -> None:
    """Same crid but different period_limit → second POST must be a governed 4xx (not 500).

    This is the regression test for the HIGH defect: inner-stage errors escaping as HTTP 500.
    """
    client, refs = staged_client
    client_request_id = f"test-replay-mismatch-{uuid.uuid4().hex[:12]}"
    base_payload = {
        "client_request_id": client_request_id,
        "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
        "expected_statement_classification_receipt_hash": refs["classification_hash"],
    }

    resp1 = client.post(OPEN_FROM_STAGED, json={**base_payload, "period_limit": 2})
    assert resp1.status_code == 200, resp1.text

    resp2 = client.post(OPEN_FROM_STAGED, json={**base_payload, "period_limit": 3})
    assert resp2.status_code in (400, 409), (
        f"Replay mismatch must return a governed 4xx, got {resp2.status_code}: {resp2.text}"
    )
    body2 = resp2.json()
    assert body2.get("error_code"), f"Response must carry an error_code, got: {body2}"


def test_open_from_staged_evidence_wrong_expected_hash_is_fail_closed(staged_client) -> None:
    """Non-matching expected_sidecar_receipt_hash → 404 with _missing error code (fail-closed)."""
    client, refs = staged_client
    wrong_hash = "0" * 64  # syntactically valid 64-hex-char hash that won't match staged storage

    resp = client.post(
        OPEN_FROM_STAGED,
        json={
            "client_request_id": f"test-wrong-hash-{uuid.uuid4().hex[:12]}",
            "expected_sidecar_receipt_hash": wrong_hash,
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
        },
    )
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body.get("error_code", "").endswith("_missing"), (
        f"Expected error_code ending in _missing, got: {body.get('error_code')}"
    )


# ---------------------------------------------------------------------------
# FIX 3 tests — require_companyfacts_oracle opt-in gate
# ---------------------------------------------------------------------------

import hashlib as _hashlib

from app.services import layer3_sec_xbrl_offline_companyfacts_stage as _stage_svc


def _write_connector_receipt_for_oracle(storage: Path, *, cik: str, connector_receipt_hash: str) -> None:
    """Write a minimal connector receipt so staging can bind the CIK."""
    raw_cik = cik.lstrip("0") or "0"
    cik_hash = _hashlib.sha256(raw_cik.encode("utf-8")).hexdigest()
    receipt = {
        "schema_id": "layer3.sec_edgar_real_filing_acquisition_connector.v1",
        "connector_receipt_id": f"sec-edgar-real-filing-connector-{connector_receipt_hash[:24]}-{connector_receipt_hash[24:48]}",
        "connector_receipt_hash": connector_receipt_hash,
        "corpus_manifest": {
            "example_records": [
                {"example_id": "ex-1", "cik_hash": cik_hash, "form_type": "10-K"}
            ]
        },
    }
    receipt_dir = storage / _stage_svc.CONNECTOR_RECEIPT_DIR / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / f"{receipt['connector_receipt_id']}.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8"
    )


def _sample_companyfacts_for_oracle() -> dict[str, Any]:
    """Minimal valid companyfacts with observations (mirrored from stage-and-oracle tests)."""
    facts: dict[str, Any] = {"us-gaap": {}}
    for local_name, val, unit, start, end, instant in [
        ("Assets", 200, "USD", "", "end-2", True),
        ("Assets", 180, "USD", "", "end-1", True),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", 100, "USD", "start-2", "end-2", False),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", 90, "USD", "start-1", "end-1", False),
        ("NetCashProvidedByUsedInOperatingActivities", 40, "USD", "start-2", "end-2", False),
        ("NetCashProvidedByUsedInOperatingActivities", 30, "USD", "start-1", "end-1", False),
    ]:
        fact: dict[str, Any] = {"fp": "FY", "fy": 2023, "val": val, "end": end}
        if not instant:
            fact["start"] = start
        facts["us-gaap"].setdefault(local_name, {"units": {}})["units"].setdefault(unit, []).append(fact)
    return facts


@pytest.fixture()
def staged_client_with_oracle(tmp_path, monkeypatch):
    """TestClient with staged evidence AND a staged companyfacts oracle."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(
        settings,
        "layer3_external_local_export_dir",
        str(tmp_path / "external-local-export"),
    )
    bootstrap_storage_tree(storage_dir)
    refs = _stage_storage(storage_dir)

    # Also write a connector receipt and stage companyfacts
    connector_hash = "f" * 64
    cik = "320193"
    _write_connector_receipt_for_oracle(storage_dir, cik=cik, connector_receipt_hash=connector_hash)
    # Add connector_receipt_hash to the sidecar so cross-issuer binding works
    sidecar_path = (
        storage_dir
        / loader.SIDECAR_RECEIPT_DIR
        / "receipts"
        / f"{refs['sidecar_receipt_id']}.json"
    )
    sidecar_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar_data["connector_receipt_hash"] = connector_hash
    sidecar_path.write_text(json.dumps(sidecar_data, sort_keys=True, indent=2), encoding="utf-8")

    facts = _sample_companyfacts_for_oracle()
    content = json.dumps({"facts": facts}).encode("utf-8")
    content_sha = _hashlib.sha256(content).hexdigest()
    raw_cik = cik.lstrip("0") or "0"
    cik_hash = _hashlib.sha256(raw_cik.encode("utf-8")).hexdigest()

    _stage_svc.stage_sec_xbrl_companyfacts(
        companyfacts=facts,
        cik=cik,
        connector_receipt_hash=connector_hash,
        content_sha256=content_sha,
        storage_dir=storage_dir,
    )

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
        yield test_client, refs, {"connector_receipt_hash": connector_hash, "cik_hash": cik_hash}
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_open_route_require_oracle_fails_closed_without_oracle(staged_client) -> None:
    """require_companyfacts_oracle=true with NO oracle staged → governed 4xx with oracle_required code."""
    client, refs = staged_client

    resp = client.post(
        OPEN_FROM_STAGED,
        json={
            "client_request_id": f"test-require-oracle-fail-{uuid.uuid4().hex[:12]}",
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
            "require_companyfacts_oracle": True,
        },
    )
    # Must fail closed — not 200
    assert resp.status_code in (400, 409), (
        f"Expected 4xx when oracle required but missing, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("error_code") == "sec_xbrl_operator_review_companyfacts_oracle_required", (
        f"Expected oracle_required error code, got: {body.get('error_code')}"
    )


def test_open_route_require_oracle_succeeds_with_oracle(staged_client_with_oracle) -> None:
    """require_companyfacts_oracle=true WITH oracle staged → 200."""
    client, refs, oracle_refs = staged_client_with_oracle

    resp = client.post(
        OPEN_FROM_STAGED,
        json={
            "client_request_id": f"test-require-oracle-ok-{uuid.uuid4().hex[:12]}",
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
            "connector_receipt_hash": oracle_refs["connector_receipt_hash"],
            "cik_hash": oracle_refs["cik_hash"],
            "require_companyfacts_oracle": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "review_ready"
    assert body["evidence_bundle_status"] == "offline_evidence_bundle_ready"


def test_open_route_default_allows_degraded(staged_client) -> None:
    """Without require_companyfacts_oracle (default False), no oracle → still 200 (backward-compat)."""
    client, refs = staged_client

    resp = client.post(
        OPEN_FROM_STAGED,
        json={
            "client_request_id": f"test-default-degraded-{uuid.uuid4().hex[:12]}",
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
            # No require_companyfacts_oracle → defaults to False
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "review_ready"
    # The bundle status reflects that the oracle was not supplied — but the route still opens
    assert body["evidence_bundle_status"] == "offline_evidence_bundle_ready_without_companyfacts_oracle"
