"""Tests for the CompanyFacts acquire-and-stage HTTP orchestration slice.

Covers:
1. Happy-path orchestration (acquire → load raw → stage → redacted return).
2. operator_confirmation=false → governed 4xx (not 500).
3. CIK not in connector → governed 4xx (sec_xbrl_companyfacts_stage_cik_not_in_connector).
4. Open-from-staged-evidence with oracle discovery params → evidence_bundle_status reflects oracle.
5. Open-from-staged-evidence backward-compat without discovery params.

Self-contained: no cross-test-module imports. Uses tmp_path and monkeypatching.
Does NOT hit the network.
"""
from __future__ import annotations

import hashlib
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
    layer3_sec_xbrl_offline_companyfacts_stage as stage_svc,
    layer3_sec_xbrl_offline_evidence_loader as loader,
    layer3_sec_edgar_live_source_artifact as live_artifact,
    layer3_sec_xbrl_companyfacts_acquire_stage as orchestrator,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_contract import (
    classification_receipt_hash_basis,
    STATEMENT_CLASSIFICATION_MODE,
)

# ---------------------------------------------------------------------------
# Route URL constants
# ---------------------------------------------------------------------------

ACQUIRE_AND_STAGE_URL = "/api/v1/layer3/source/sec-edgar/companyfacts/acquire-and-stage"
OPEN_FROM_STAGED = "/api/v1/layer3/sec-xbrl/operator-review/workflow/open-from-staged-evidence"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash(char: str) -> str:
    return char * 64


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _sample_companyfacts() -> dict[str, Any]:
    """Minimal valid companyfacts with 2 observations."""
    return {
        "us-gaap": {
            "Assets": {
                "units": {
                    "USD": [
                        {"val": 200, "end": "2023-12-31", "fp": "FY", "fy": 2023},
                    ]
                }
            },
            "Revenues": {
                "units": {
                    "USD": [
                        {"val": 100, "start": "2023-01-01", "end": "2023-12-31", "fp": "FY", "fy": 2023},
                    ]
                }
            },
        }
    }


def _write_connector_receipt(storage: Path, *, cik: str, connector_receipt_hash: str) -> dict[str, Any]:
    cik_hash = _sha256(cik.lstrip("0") or "0")
    receipt = {
        "schema_id": "layer3.sec_edgar_real_filing_acquisition_connector.v1",
        "connector_receipt_id": f"sec-edgar-real-filing-connector-{connector_receipt_hash[:24]}-{connector_receipt_hash[24:48]}",
        "connector_receipt_hash": connector_receipt_hash,
        "corpus_manifest": {
            "example_records": [
                {
                    "example_id": "ex-1",
                    "cik_hash": cik_hash,
                    "form_type": "10-K",
                }
            ]
        },
    }
    receipt_dir = storage / stage_svc.CONNECTOR_RECEIPT_DIR / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    path = receipt_dir / f"{receipt['connector_receipt_id']}.json"
    _write_json(path, receipt)
    return receipt


def _make_fetch_receipt(
    cik: str,
    storage: Path,
    *,
    companyfacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a raw companyfacts artifact and a fetch receipt, mirroring what the live service writes.

    Returns the redacted receipt dict (same shape as acquire_sec_edgar_companyfacts_live_artifact).
    """
    if companyfacts is None:
        companyfacts = _sample_companyfacts()
    raw_cik = cik.lstrip("0") or "0"
    cik_hash = _sha256(raw_cik)
    content = json.dumps(companyfacts, sort_keys=True, indent=2).encode("utf-8")
    content_sha256 = hashlib.sha256(content).hexdigest()

    source_identity_hash = stable_hash(
        {"hash_version": "sec_edgar_companyfacts_source_identity_hash_v1", "cik_hash": cik_hash}
    )
    receipt_hash_basis = {
        "hash_version": "sec_edgar_companyfacts_live_artifact_receipt_hash_v1",
        "schema_id": "layer3.sec_edgar_companyfacts_live_artifact_acquisition.v1",
        "source_identity_hash": source_identity_hash,
        "cik_hash": cik_hash,
        "content_sha256": content_sha256,
    }
    receipt_hash = stable_hash(receipt_hash_basis)
    receipt_id = f"sec-edgar-companyfacts-live-artifact-{source_identity_hash[:24]}-{receipt_hash[:24]}"

    # Write raw artifact (same path load_staged_companyfacts_raw reads)
    artifact_path = storage / stage_svc.COMPANYFACTS_RECEIPT_DIR / "companyfacts-store" / f"{receipt_id}.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(content)

    # Write the fetch receipt into receipts/ — this faithfully mirrors what the real live service
    # does (acquire writes a fetch receipt, then stage scans receipts/).  Without FIX A the stage
    # scan would match this fetch receipt (same prefix glob), call _build_stage_response on it, and
    # raise KeyError: 'companyfacts_payload_hash'.  FIX A's schema_id guard skips it.
    fetch_receipt_payload = {
        "schema_id": "layer3.sec_edgar_companyfacts_live_artifact_acquisition.v1",
        "companyfacts_receipt_id": receipt_id,
        "companyfacts_receipt_hash": receipt_hash,
        "source_identity_hash": source_identity_hash,
        "cik_hash": cik_hash,
        "content_sha256": content_sha256,
        "companyfacts_observation_count": 2,
        "taxonomy_count": 1,
        "concept_count": 2,
        "recorded_at": "2026-01-01T00:00:00+00:00",
    }
    receipts_dir = storage / stage_svc.COMPANYFACTS_RECEIPT_DIR / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    receipt_file = receipts_dir / f"{receipt_id}.json"
    if not receipt_file.exists():
        receipt_file.write_text(
            __import__("json").dumps(fetch_receipt_payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    # Redacted dict matching what _response_from_companyfacts_receipt returns
    return {
        "schema_id": "layer3.sec_edgar_companyfacts_live_artifact_acquisition.v1",
        "status": "available",
        "companyfacts_receipt_id": receipt_id,
        "companyfacts_receipt_hash": receipt_hash,
        "cik_hash": cik_hash,
        "content_sha256": content_sha256,
        "companyfacts_observation_count": 2,
        "taxonomy_count": 1,
        "concept_count": 2,
        "live_network_flags": {
            "live_network_fetch_performed": True,
            "ci_live_network_disabled": True,
            "server_configured_user_agent_required": True,
            "rate_limit_enforced": True,
            "host_allowlist_enforced": True,
        },
        "idempotent_replay": False,
        "raw_cik_exposed": False,
        "raw_values_exposed": False,
        "raw_accession_exposed": False,
    }


# ---------------------------------------------------------------------------
# Minimal offline evidence storage writer (self-contained, not imported)
# ---------------------------------------------------------------------------

def _stage_full_evidence_storage(storage: Path, *, connector_receipt_hash: str) -> dict[str, str]:
    """Write a minimal offline-evidence storage tree and return disambiguation hashes."""
    sidecar_hash = _hash("b")
    sidecar_id = f"sec-edgar-arelle-resolved-fact-authority-{sidecar_hash[:24]}"
    bridge_hash = _hash("e")
    bridge_id = "sec-edgar-html-inline-xbrl-fact-material-bridge-" + "e" * 24

    records = [
        {
            "resolved_fact_id": "rf-assets",
            "concept": {"namespace": "fasb.org/us-gaap/test", "local_name": "Assets", "standard": True},
            "unit": {"currency": "iso4217:USD", "measures": ["iso4217:USD"]},
            "period": {"type": "instant", "instant": "2023-12-31"},
            "dimensions": {"explicit": [], "typed": []},
        },
        {
            "resolved_fact_id": "rf-revenue",
            "concept": {"namespace": "fasb.org/us-gaap/test", "local_name": "Revenues", "standard": True},
            "unit": {"currency": "iso4217:USD", "measures": ["iso4217:USD"]},
            "period": {"type": "duration", "start": "2023-01-01", "end": "2023-12-31"},
            "dimensions": {"explicit": [], "typed": []},
        },
    ]
    value_records = [
        {"resolved_fact_id": "rf-assets", "effective_value": "200"},
        {"resolved_fact_id": "rf-revenue", "effective_value": "100"},
    ]
    projection = [{**r, "value_redacted": True} for r in records]
    inventory_hash = stable_hash(projection)
    value_store_hash = stable_hash(value_records)
    statement_roles = [
        {"fact_id_or_order_key": "rf-assets", "statement_candidate_role": "balance_sheet"},
        {"fact_id_or_order_key": "rf-revenue", "statement_candidate_role": "income_statement"},
    ]
    cls_inv_hash = stable_hash(statement_roles)
    sem_hash = stable_hash([])
    cls_order_hash = stable_hash([r["fact_id_or_order_key"] for r in statement_roles])
    group_hash = stable_hash([])
    unclass_hash = stable_hash([])
    diag_hash = stable_hash({})

    sidecar = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "sidecar_state": "sec_edgar_arelle_resolved_fact_authority_sidecar_ready",
        "resolved_fact_records": records,
        "resolved_fact_projection": projection,
        "resolved_fact_inventory_hash": inventory_hash,
        "connector_receipt_hash": connector_receipt_hash,
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
    value_store_payload = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_internal_value_store.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "value_record_count": len(value_records),
        "value_records": value_records,
    }
    classification = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification.v1",
        "classification_mode": STATEMENT_CLASSIFICATION_MODE,
        "fact_authority_receipt_hash": sidecar_hash,
        "fact_inventory_hash": inventory_hash,
        "fact_material_bridge_receipt_hash": bridge_hash,
        "classification_inventory_hash": cls_inv_hash,
        "semantic_profile_inventory_hash": sem_hash,
        "classification_order_hash": cls_order_hash,
        "statement_group_inventory_hash": group_hash,
        "unclassified_fact_inventory_hash": unclass_hash,
        "classification_diagnostics_hash": diag_hash,
        "authority_hashes": {
            "fact_authority_receipt_hash": sidecar_hash,
            "fact_inventory_hash": inventory_hash,
            "fact_material_bridge_receipt_hash": bridge_hash,
        },
        "classification_inventory": statement_roles,
    }
    cls_hash = stable_hash(
        classification_receipt_hash_basis(
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
    cls_id = f"sec-edgar-html-inline-xbrl-fact-statement-classification-{cls_hash[:24]}"
    classification["statement_classification_receipt_id"] = cls_id
    classification["statement_classification_receipt_hash"] = cls_hash

    bridge = {
        "fact_material_bridge_receipt_hash": bridge_hash,
        "fact_material_bridge_receipt_id": bridge_id,
        "response": {
            "arelle_sidecar_receipt_hash": sidecar_hash,
            "dataset_version_id": "dv-companyfacts-test",
        },
    }

    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / "receipts" / f"{sidecar_id}.json", sidecar)
    _write_json(storage / loader.SIDECAR_RECEIPT_DIR / loader.VALUE_STORE_SUBDIR / f"{sidecar_id}.json", value_store_payload)
    _write_json(storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts" / f"{cls_id}.json", classification)
    _write_json(storage / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge" / "receipts" / f"{bridge_id}.json", bridge)

    return {
        "sidecar_hash": sidecar_hash,
        "classification_hash": cls_hash,
        "connector_receipt_hash": connector_receipt_hash,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_test_client(tmp_path: Path, monkeypatch: Any) -> tuple[TestClient, Path]:
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "ext"))
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
    client = TestClient(app)
    return client, storage_dir


# ---------------------------------------------------------------------------
# Test 1: Happy-path orchestration
# ---------------------------------------------------------------------------

def test_acquire_and_stage_orchestration_happy_path(tmp_path, monkeypatch) -> None:
    """monkeypatched acquire → write raw + receipt → orchestration returns redacted; stage discoverable."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    storage_dir.mkdir(parents=True, exist_ok=True)

    cik = "320193"
    connector_hash = _hash("a")
    companyfacts = _sample_companyfacts()

    # Pre-write connector receipt so staging can bind cik_hash
    _write_connector_receipt(storage_dir, cik=cik, connector_receipt_hash=connector_hash)

    # Build the fake fetch receipt (writes raw artifact + receipt file)
    fake_fetch_receipt = _make_fetch_receipt(cik, storage_dir, companyfacts=companyfacts)

    # Monkeypatch the live fetch IN THE ORCHESTRATOR's namespace (it imported the name directly)
    monkeypatch.setattr(
        orchestrator,
        "acquire_sec_edgar_companyfacts_live_artifact",
        lambda fields: fake_fetch_receipt,
    )

    result = orchestrator.acquire_and_stage_companyfacts(
        client_request_id="test-happy-path-001",
        cik=cik,
        connector_receipt_hash=connector_hash,
        operator_confirmation=True,
        storage_dir=str(storage_dir),
    )

    # Shape assertions
    assert result["schema_id"] == "layer3.sec_xbrl_companyfacts_acquire_stage.v1"
    assert result["status"] == "companyfacts_acquired_and_staged"
    assert result["request_id"] == "test-happy-path-001"  # base_response sets request_id=client_request_id

    # Acquire dict must be redacted
    acquire = result["acquire"]
    assert acquire["raw_cik_exposed"] is False
    assert acquire["raw_values_exposed"] is False
    assert "facts" not in acquire
    assert cik not in json.dumps(acquire)
    assert "320193" not in json.dumps(acquire)

    # Stage dict must be redacted
    stage = result["stage"]
    assert stage["raw_cik_exposed"] is False
    assert stage["raw_values_exposed"] is False
    assert "facts" not in stage
    assert cik not in json.dumps(stage)

    # Full result must not expose raw CIK, concept names, or raw financial values
    result_text = json.dumps(result)
    assert "320193" not in result_text
    assert "Assets" not in result_text
    assert "Revenues" not in result_text
    # The raw financial value "200" (as a number/string) must not appear; counts like "2" are fine
    assert '"val": 200' not in result_text
    assert '"val":200' not in result_text

    # Stage receipt must be discoverable
    cik_hash = _sha256(cik.lstrip("0") or "0")
    found = stage_svc.find_staged_companyfacts_receipt(
        storage_dir,
        connector_receipt_hash=connector_hash,
        cik_hash=cik_hash,
    )
    assert found is not None
    assert found["companyfacts_receipt_id"] == stage["companyfacts_receipt_id"]


# ---------------------------------------------------------------------------
# Test 2: operator_confirmation=False → governed 4xx, not 500
# ---------------------------------------------------------------------------

def test_acquire_and_stage_operator_confirmation_required(tmp_path, monkeypatch) -> None:
    """operator_confirmation=false → Layer3WorkbenchError → governed 4xx via route."""
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)
    try:
        connector_hash = _hash("b")
        _write_connector_receipt(storage_dir, cik="320193", connector_receipt_hash=connector_hash)

        resp = client.post(
            ACQUIRE_AND_STAGE_URL,
            json={
                "client_request_id": f"test-no-confirm-{uuid.uuid4().hex[:8]}",
                "cik": "320193",
                "connector_receipt_hash": connector_hash,
                "operator_confirmation": False,
            },
        )
        # Must be a governed 4xx (409), never a raw 500
        assert resp.status_code in {400, 409}, f"Expected 4xx, got {resp.status_code}: {resp.text}"
        body = resp.json()
        # Governed response envelope fields
        assert "error_code" in body
        assert "sec_edgar_companyfacts_live_artifact_operator_confirmation_missing" in body["error_code"]
        assert resp.status_code != 500
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 3: CIK not in connector → governed 4xx
# ---------------------------------------------------------------------------

def test_acquire_and_stage_cik_not_in_connector_fail_closed(tmp_path, monkeypatch) -> None:
    """Fetch succeeds but CIK hash not in connector corpus → sec_xbrl_companyfacts_stage_cik_not_in_connector."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    storage_dir.mkdir(parents=True, exist_ok=True)

    cik_in_connector = "320193"
    cik_wrong = "789012"  # NOT in connector
    connector_hash = _hash("c")

    # Connector only has cik_in_connector
    _write_connector_receipt(storage_dir, cik=cik_in_connector, connector_receipt_hash=connector_hash)

    # Pre-write raw artifact for the wrong CIK
    fake_fetch_receipt = _make_fetch_receipt(cik_wrong, storage_dir, companyfacts=_sample_companyfacts())

    # Patch in the orchestrator's namespace (it imported the function directly)
    monkeypatch.setattr(
        orchestrator,
        "acquire_sec_edgar_companyfacts_live_artifact",
        lambda fields: fake_fetch_receipt,
    )

    from app.services.layer3_sec_xbrl_offline_companyfacts_stage import SecXbrlCompanyfactsStageError

    with pytest.raises(SecXbrlCompanyfactsStageError) as exc_info:
        orchestrator.acquire_and_stage_companyfacts(
            client_request_id="test-cik-not-in-connector",
            cik=cik_wrong,
            connector_receipt_hash=connector_hash,
            operator_confirmation=True,
            storage_dir=str(storage_dir),
        )
    assert exc_info.value.code == "sec_xbrl_companyfacts_stage_cik_not_in_connector"


def test_acquire_and_stage_cik_not_in_connector_route_governed(tmp_path, monkeypatch) -> None:
    """Same but via route → must be a governed 409, not a raw 500."""
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)
    try:
        cik_in_connector = "320193"
        cik_wrong = "789012"
        connector_hash = _hash("d")

        _write_connector_receipt(storage_dir, cik=cik_in_connector, connector_receipt_hash=connector_hash)
        fake_fetch_receipt = _make_fetch_receipt(cik_wrong, storage_dir)

        # Patch in the orchestrator's namespace (it imported the function directly)
        monkeypatch.setattr(
            orchestrator,
            "acquire_sec_edgar_companyfacts_live_artifact",
            lambda fields: fake_fetch_receipt,
        )

        resp = client.post(
            ACQUIRE_AND_STAGE_URL,
            json={
                "client_request_id": f"test-cik-mismatch-{uuid.uuid4().hex[:8]}",
                "cik": cik_wrong,
                "connector_receipt_hash": connector_hash,
                "operator_confirmation": True,
            },
        )
        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert "error_code" in body
        assert "cik_not_in_connector" in body["error_code"]
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 4: Open route accepts oracle discovery params
# ---------------------------------------------------------------------------

def test_open_route_accepts_oracle_discovery_params(tmp_path, monkeypatch) -> None:
    """POST open-from-staged-evidence with connector_receipt_hash+cik_hash → oracle supplied."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "ext"))
    bootstrap_storage_tree(storage_dir)

    cik = "320193"
    connector_hash = _hash("f")

    # Write the sidecar/classification/bridge evidence tree
    refs = _stage_full_evidence_storage(storage_dir, connector_receipt_hash=connector_hash)

    # Write connector receipt so the staging service can bind cik_hash
    _write_connector_receipt(storage_dir, cik=cik, connector_receipt_hash=connector_hash)

    # Stage companyfacts for this cik+connector
    companyfacts = _sample_companyfacts()
    content_sha = hashlib.sha256(json.dumps(companyfacts, sort_keys=True, indent=2).encode()).hexdigest()
    stage_svc.stage_sec_xbrl_companyfacts(
        companyfacts=companyfacts,
        cik=cik,
        connector_receipt_hash=connector_hash,
        content_sha256=content_sha,
        storage_dir=storage_dir,
    )

    cik_hash = _sha256(cik.lstrip("0") or "0")

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
    try:
        client = TestClient(app)
        resp = client.post(
            OPEN_FROM_STAGED,
            json={
                "client_request_id": f"test-oracle-discovery-{uuid.uuid4().hex[:8]}",
                "expected_sidecar_receipt_hash": refs["sidecar_hash"],
                "expected_statement_classification_receipt_hash": refs["classification_hash"],
                "connector_receipt_hash": connector_hash,
                "cik_hash": cik_hash,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "review_ready"

        # Oracle supplied → evidence_bundle_status must be the non-degraded form
        evidence_status = body.get("evidence_bundle_status", "")
        assert evidence_status == "offline_evidence_bundle_ready", (
            f"Expected oracle-supplied status, got: {evidence_status}"
        )

        # No raw value leak
        text = resp.text
        assert "effective_value" not in text
        assert "value_records" not in text
        assert cik not in text
        assert "320193" not in text
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 5: Open route backward-compatible without discovery params
# ---------------------------------------------------------------------------

def test_open_route_backward_compatible_without_discovery_params(tmp_path, monkeypatch) -> None:
    """No connector_receipt_hash/cik_hash → opens with degraded oracle status (no error)."""
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "ext"))
    bootstrap_storage_tree(storage_dir)

    connector_hash = _hash("g")
    refs = _stage_full_evidence_storage(storage_dir, connector_receipt_hash=connector_hash)

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
    try:
        client = TestClient(app)
        resp = client.post(
            OPEN_FROM_STAGED,
            json={
                "client_request_id": f"test-no-oracle-{uuid.uuid4().hex[:8]}",
                "expected_sidecar_receipt_hash": refs["sidecar_hash"],
                "expected_statement_classification_receipt_hash": refs["classification_hash"],
                # No connector_receipt_hash, no cik_hash
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "review_ready"

        # Without oracle discovery → degraded status
        evidence_status = body.get("evidence_bundle_status", "")
        assert "without_companyfacts_oracle" in evidence_status, (
            f"Expected degraded oracle status, got: {evidence_status}"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 6: Happy-path route returns 200 (regression for FIX 1)
# ---------------------------------------------------------------------------

def test_acquire_and_stage_route_happy_path_returns_200(tmp_path, monkeypatch) -> None:
    """POST to the acquire-and-stage route with monkeypatched acquire → status_code == 200.

    This is the regression test for FIX 1: before the fix, FastAPI raised
    ResponseValidationError (missing schema_version/request_id/server_time) → HTTP 500
    on every successful orchestration call.
    """
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)
    try:
        cik = "320193"
        connector_hash = _hash("h")
        companyfacts = _sample_companyfacts()

        # Pre-write connector receipt so staging can bind cik_hash
        _write_connector_receipt(storage_dir, cik=cik, connector_receipt_hash=connector_hash)

        # Build a fake fetch receipt (writes the raw artifact the orchestrator will load)
        fake_fetch = _make_fetch_receipt(cik, storage_dir, companyfacts=companyfacts)

        # Patch acquire in the orchestrator's namespace
        monkeypatch.setattr(
            orchestrator,
            "acquire_sec_edgar_companyfacts_live_artifact",
            lambda fields: fake_fetch,
        )

        resp = client.post(
            ACQUIRE_AND_STAGE_URL,
            json={
                "client_request_id": f"test-happy-route-{uuid.uuid4().hex[:8]}",
                "cik": cik,
                "connector_receipt_hash": connector_hash,
                "operator_confirmation": True,
            },
        )

        # Core regression assertion: must be 200, not 500
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        body = resp.json()

        # Base envelope fields (set by base_response)
        assert "schema_version" in body, "schema_version missing from response"
        assert "request_id" in body, "request_id missing from response"
        assert "server_time" in body, "server_time missing from response"
        assert "status" in body, "status missing from response"

        # Domain fields
        assert "acquire" in body, "acquire missing from response"
        assert "stage" in body, "stage missing from response"

        # No raw leak
        text = resp.text
        assert cik not in text, f"raw CIK {cik!r} leaked into response"
        assert "320193" not in text
        # Ensure the raw facts dict was not embedded (key "facts" in body, not substring in receipt ids)
        assert "facts" not in body
        assert "facts" not in body.get("acquire", {})
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 7: Idempotent replay — both calls succeed
# ---------------------------------------------------------------------------

def test_acquire_and_stage_idempotent_replay(tmp_path, monkeypatch) -> None:
    """Calling acquire-and-stage twice with the same cik+connector succeeds both times.

    On the second call the monkeypatched acquire returns idempotent_replay=True
    but the raw artifact is still present, so stage replays without error.
    """
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)
    try:
        cik = "320193"
        connector_hash = _hash("i")
        companyfacts = _sample_companyfacts()

        _write_connector_receipt(storage_dir, cik=cik, connector_receipt_hash=connector_hash)
        fake_fetch_first = _make_fetch_receipt(cik, storage_dir, companyfacts=companyfacts)

        # Second call receipt: same ids/hashes, idempotent_replay=True
        fake_fetch_second = {**fake_fetch_first, "idempotent_replay": True}

        call_count = {"n": 0}

        def _mock_acquire(fields):
            call_count["n"] += 1
            return fake_fetch_first if call_count["n"] == 1 else fake_fetch_second

        monkeypatch.setattr(orchestrator, "acquire_sec_edgar_companyfacts_live_artifact", _mock_acquire)

        payload = {
            "client_request_id": f"test-idempotent-{uuid.uuid4().hex[:8]}",
            "cik": cik,
            "connector_receipt_hash": connector_hash,
            "operator_confirmation": True,
        }

        resp1 = client.post(ACQUIRE_AND_STAGE_URL, json=payload)
        assert resp1.status_code == 200, f"First call failed: {resp1.status_code}: {resp1.text}"

        resp2 = client.post(ACQUIRE_AND_STAGE_URL, json=payload)
        assert resp2.status_code == 200, f"Second (replay) call failed: {resp2.status_code}: {resp2.text}"

        body2 = resp2.json()
        assert body2.get("status") == "companyfacts_acquired_and_staged"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 8: Missing raw artifact → governed 409 (fail-closed)
# ---------------------------------------------------------------------------

def test_acquire_and_stage_missing_raw_artifact_fail_closed(tmp_path, monkeypatch) -> None:
    """Acquire returns a valid receipt but the raw artifact is deleted before stage reads it.

    The orchestrator must raise a governed error (not propagate a raw FileNotFoundError → 500).
    The route maps this to a non-500 response.
    """
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)
    try:
        cik = "320193"
        connector_hash = _hash("j")
        companyfacts = _sample_companyfacts()

        _write_connector_receipt(storage_dir, cik=cik, connector_receipt_hash=connector_hash)
        fake_fetch = _make_fetch_receipt(cik, storage_dir, companyfacts=companyfacts)

        # Identify and delete the raw artifact that the orchestrator will try to load
        receipt_id = fake_fetch["companyfacts_receipt_id"]
        artifact_path = (
            storage_dir
            / stage_svc.COMPANYFACTS_RECEIPT_DIR
            / "companyfacts-store"
            / f"{receipt_id}.json"
        )
        assert artifact_path.exists(), "test setup error: artifact not written"
        artifact_path.unlink()

        monkeypatch.setattr(
            orchestrator,
            "acquire_sec_edgar_companyfacts_live_artifact",
            lambda fields: fake_fetch,
        )

        resp = client.post(
            ACQUIRE_AND_STAGE_URL,
            json={
                "client_request_id": f"test-missing-artifact-{uuid.uuid4().hex[:8]}",
                "cik": cik,
                "connector_receipt_hash": connector_hash,
                "operator_confirmation": True,
            },
        )

        # Must NOT be a raw 500 — must be a governed 4xx (409)
        assert resp.status_code != 500, f"Got raw 500 — not fail-closed: {resp.text}"
        assert resp.status_code == 409, f"Expected governed 409, got {resp.status_code}: {resp.text}"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 9: Namespace collision regression — fetch receipt in receipts/ must not
#          cause KeyError in stage idempotency scan (FIX A regression).
# ---------------------------------------------------------------------------

def test_stage_not_confused_by_fetch_receipt_in_receipts_dir(tmp_path, monkeypatch) -> None:
    """Regression for FIX A: acquire writes a fetch receipt into receipts/; stage must skip it.

    _make_fetch_receipt now writes both the raw artifact AND a fetch receipt JSON into
    receipts/.  Without FIX A the stage idempotency scan would match that fetch receipt
    (same prefix glob), call _build_stage_response on it, and raise KeyError:
    'companyfacts_payload_hash'.  FIX A's schema_id guard skips fetch receipts, so the
    full orchestration must succeed without error and produce a distinct stage receipt.
    """
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    storage_dir.mkdir(parents=True, exist_ok=True)

    cik = "320193"
    connector_hash = _hash("k")
    companyfacts = _sample_companyfacts()

    _write_connector_receipt(storage_dir, cik=cik, connector_receipt_hash=connector_hash)

    # _make_fetch_receipt now writes a fetch receipt into receipts/ — this is the fidelity
    # gap that previously hid the bug.
    fake_fetch = _make_fetch_receipt(cik, storage_dir, companyfacts=companyfacts)

    # Sanity: confirm the fetch receipt was actually written to receipts/
    receipts_dir = storage_dir / stage_svc.COMPANYFACTS_RECEIPT_DIR / "receipts"
    fetch_receipt_path = receipts_dir / f"{fake_fetch['companyfacts_receipt_id']}.json"
    assert fetch_receipt_path.exists(), "test setup error: fetch receipt was not written to receipts/"
    fetch_on_disk = json.loads(fetch_receipt_path.read_text(encoding="utf-8"))
    assert fetch_on_disk.get("schema_id") == "layer3.sec_edgar_companyfacts_live_artifact_acquisition.v1"
    assert "companyfacts_payload_hash" not in fetch_on_disk  # confirms this would KeyError pre-fix

    monkeypatch.setattr(
        orchestrator,
        "acquire_sec_edgar_companyfacts_live_artifact",
        lambda fields: fake_fetch,
    )

    # Must not raise KeyError — FIX A skips the fetch receipt during stage idempotency scan
    result = orchestrator.acquire_and_stage_companyfacts(
        client_request_id="test-fix-a-regression",
        cik=cik,
        connector_receipt_hash=connector_hash,
        operator_confirmation=True,
        storage_dir=str(storage_dir),
    )

    assert result["status"] == "companyfacts_acquired_and_staged"
    stage = result["stage"]

    # The stage receipt must be distinct from the fetch receipt
    assert stage["companyfacts_receipt_id"] != fake_fetch["companyfacts_receipt_id"]

    # Stage receipt must be discoverable via find_staged_companyfacts_receipt
    cik_hash = _sha256(cik.lstrip("0") or "0")
    found = stage_svc.find_staged_companyfacts_receipt(
        storage_dir,
        connector_receipt_hash=connector_hash,
        cik_hash=cik_hash,
    )
    assert found is not None
    assert found["schema_id"] == stage_svc.SCHEMA_ID


# ---------------------------------------------------------------------------
# Test 10: Same CIK staged against two distinct connectors → two distinct receipts (FIX A).
# ---------------------------------------------------------------------------

def test_stage_same_cik_two_connectors_distinct_receipts(tmp_path) -> None:
    """Same issuer (same cik_hash) staged against connector A then connector B → two distinct
    stage receipts, each discoverable for its own connector.

    Without FIX A's connector-scoping guard the second stage call would match the first
    connector's receipt (same cik_hash) and replay it, returning the wrong receipt for
    connector B.  With the fix: each connector gets its own receipt.
    """
    storage_dir = tmp_path / "storage"
    cik = "320193"
    connector_a = _hash("m")
    connector_b = _hash("n")
    companyfacts = _sample_companyfacts()
    content_sha = hashlib.sha256(
        json.dumps(companyfacts, sort_keys=True, indent=2).encode("utf-8")
    ).hexdigest()

    _write_connector_receipt(storage_dir, cik=cik, connector_receipt_hash=connector_a)
    _write_connector_receipt(storage_dir, cik=cik, connector_receipt_hash=connector_b)

    result_a = stage_svc.stage_sec_xbrl_companyfacts(
        companyfacts=companyfacts,
        cik=cik,
        connector_receipt_hash=connector_a,
        content_sha256=content_sha,
        storage_dir=storage_dir,
    )
    result_b = stage_svc.stage_sec_xbrl_companyfacts(
        companyfacts=companyfacts,
        cik=cik,
        connector_receipt_hash=connector_b,
        content_sha256=content_sha,
        storage_dir=storage_dir,
    )

    # Each connector must get its own distinct receipt id
    assert result_a["companyfacts_receipt_id"] != result_b["companyfacts_receipt_id"], (
        "Expected distinct receipt ids for different connectors"
    )

    cik_hash = _sha256(cik.lstrip("0") or "0")

    # Each is discoverable only for its own connector
    found_a = stage_svc.find_staged_companyfacts_receipt(
        storage_dir, connector_receipt_hash=connector_a, cik_hash=cik_hash
    )
    found_b = stage_svc.find_staged_companyfacts_receipt(
        storage_dir, connector_receipt_hash=connector_b, cik_hash=cik_hash
    )

    assert found_a is not None and found_a["connector_receipt_hash"] == connector_a
    assert found_b is not None and found_b["connector_receipt_hash"] == connector_b
    assert found_a["companyfacts_receipt_id"] != found_b["companyfacts_receipt_id"]

    # Neither call was an idempotent replay
    assert result_a["idempotent_replay"] is False
    assert result_b["idempotent_replay"] is False


# ---------------------------------------------------------------------------
# Test 11: Same cik_hash + same connector + different content → conflict (FIX A).
# ---------------------------------------------------------------------------

def test_stage_same_cik_connector_different_content_conflicts(tmp_path) -> None:
    """Same cik_hash + same connector_receipt_hash but different content_sha256 → conflict error.

    This verifies the conflict branch of the stage idempotency scan still fires correctly
    after FIX A narrowed the scan to same-schema + same-connector receipts.
    """
    storage_dir = tmp_path / "storage"
    cik = "320193"
    connector_hash = _hash("p")

    facts_a = _sample_companyfacts()
    facts_b = {
        "us-gaap": {
            "NetIncomeLoss": {
                "units": {
                    "USD": [{"val": 999, "end": "2023-12-31", "fp": "FY", "fy": 2023}]
                }
            }
        }
    }
    sha_a = hashlib.sha256(
        json.dumps(facts_a, sort_keys=True, indent=2).encode("utf-8")
    ).hexdigest()
    sha_b = hashlib.sha256(
        json.dumps(facts_b, sort_keys=True, indent=2).encode("utf-8")
    ).hexdigest()

    _write_connector_receipt(storage_dir, cik=cik, connector_receipt_hash=connector_hash)

    stage_svc.stage_sec_xbrl_companyfacts(
        companyfacts=facts_a,
        cik=cik,
        connector_receipt_hash=connector_hash,
        content_sha256=sha_a,
        storage_dir=storage_dir,
    )

    with pytest.raises(stage_svc.SecXbrlCompanyfactsStageError) as exc_info:
        stage_svc.stage_sec_xbrl_companyfacts(
            companyfacts=facts_b,
            cik=cik,
            connector_receipt_hash=connector_hash,
            content_sha256=sha_b,
            storage_dir=storage_dir,
        )
    assert exc_info.value.code == "sec_xbrl_companyfacts_stage_conflict"
