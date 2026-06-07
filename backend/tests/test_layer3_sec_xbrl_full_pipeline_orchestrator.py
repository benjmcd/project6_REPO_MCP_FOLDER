"""Tests for the SEC/XBRL full-pipeline orchestrator service and route.

Covers:
1. Happy path: full pipeline -> 200, combined response shape, no raw CIK leak.
2. CIK/cik_hash mismatch -> 409 full_pipeline_cik_hash_mismatch.
3. No supported filing -> 409 full_pipeline_no_supported_filing.
4. Missing operator_confirmation -> 400 full_pipeline_missing_operator_confirmation.
5. require_companyfacts_oracle=True calls acquire_and_stage; False skips it.

All network calls are monkeypatched. No live network access.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

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
    layer3_sec_xbrl_full_pipeline_orchestrator as orchestrator,
    layer3_sec_edgar_real_company_corpus_validation as corpus_svc,
    layer3_sec_xbrl_companyfacts_acquire_stage as cf_orchestrator,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_contract import (
    classification_receipt_hash_basis,
    STATEMENT_CLASSIFICATION_MODE,
)
from app.services import layer3_sec_xbrl_offline_evidence_loader as loader

# ---------------------------------------------------------------------------
# Route URL constants
# ---------------------------------------------------------------------------

FULL_PIPELINE_URL = "/api/v1/layer3/sec-xbrl/operator-review/workflow/open-full-pipeline"


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


# ---------------------------------------------------------------------------
# Offline evidence storage writer (for happy-path storage backing)
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
            "dataset_version_id": "dv-full-pipeline-test",
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
# Corpus validation response factory
# ---------------------------------------------------------------------------

def _make_corpus_response(
    *,
    cik: str,
    connector_receipt_hash: str,
    sidecar_hash: str,
    classification_hash: str,
    form_type: str = "10-K",
    supported: bool = True,
) -> dict[str, Any]:
    """Build a fake corpus validation response consistent with what the real service returns."""
    cik_hash = _sha256(cik)
    record: dict[str, Any] = {
        "cik_hash": cik_hash,
        "form_type": form_type,
        "supported_degraded_blocked": "supported" if supported else "blocked",
        "authority_hashes": {
            # fact_authority_receipt_hash == sidecar_hash (confirmed from live_oracle_chain.py)
            "fact_authority_receipt_hash": sidecar_hash,
            "statement_classification_receipt_hash": classification_hash,
            "arelle_sidecar_receipt_hash": sidecar_hash,
        },
    }
    return {
        "connector_receipt_hash": connector_receipt_hash,
        "validation_receipt_id": f"sec-edgar-real-company-corpus-validation-{connector_receipt_hash[:24]}",
        "validation_receipt_hash": _sha256(connector_receipt_hash + sidecar_hash),
        "filing_validation_records": [record],
        "status": "sec_edgar_real_company_corpus_validation_ready",
    }


# ---------------------------------------------------------------------------
# TestClient factory
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
# Test 1: Happy path
# ---------------------------------------------------------------------------

def test_full_pipeline_happy_path(tmp_path, monkeypatch) -> None:
    """Happy path: corpus-validation stubbed, open handler stubbed -> 200, combined shape, no CIK leak."""
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    cik = "320193"
    connector_hash = _hash("a")
    hashes = _stage_full_evidence_storage(storage_dir, connector_receipt_hash=connector_hash)
    sidecar_hash = hashes["sidecar_hash"]
    cls_hash = hashes["classification_hash"]

    # Stub corpus-validation in the orchestrator module's namespace
    fake_corpus = _make_corpus_response(
        cik=cik,
        connector_receipt_hash=connector_hash,
        sidecar_hash=sidecar_hash,
        classification_hash=cls_hash,
    )
    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda fields, db, evidence_owner=None: fake_corpus,
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )

    # Stub auth policy in the route (derive_sec_xbrl_evidence_owner always succeeds)
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )

    # Stub ownership marker requirement in auth binding (no real DB check)
    from app.services import layer3_sec_xbrl_auth_binding as auth_binding_svc
    monkeypatch.setattr(
        auth_binding_svc,
        "require_sec_xbrl_evidence_ownership_marker",
        lambda *args, **kwargs: None,
    )

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": f"fp-happy-{uuid.uuid4().hex[:12]}",
            "cik": cik,
            "company_matrix": ["AAPL"],
            "period_limit": 3,
            "operator_confirmation": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # Top-level shape
    assert body["status"] == "full_pipeline_open_ready"
    assert body["production_readiness_claimed"] is False
    assert "corpus_validation" in body
    assert "companyfacts_stage" in body
    assert "operator_review" in body

    # Corpus validation summary is redacted
    cv = body["corpus_validation"]
    assert "validation_receipt_id" in cv
    assert "connector_receipt_hash" in cv
    assert "selected_cik_hash" in cv
    assert cv["selected_form_type"] == "10-K"

    # No raw CIK in the full response
    raw_json = json.dumps(body)
    assert cik not in raw_json, f"Raw CIK '{cik}' leaked into response"
    assert "320193" not in raw_json


# ---------------------------------------------------------------------------
# Test 1b: Zero-padded CIK normalization (regression for the lstrip("0") fix)
# ---------------------------------------------------------------------------

def test_full_pipeline_zero_padded_cik_normalizes(tmp_path, monkeypatch) -> None:
    """A canonical zero-padded CIK (e.g. '0000320193') must normalize to the connector's
    zero-stripped cik_hash and succeed — NOT raise a spurious cik_hash_mismatch."""
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    padded_cik = "0000320193"
    canonical_cik = "320193"
    connector_hash = _hash("a")
    hashes = _stage_full_evidence_storage(storage_dir, connector_receipt_hash=connector_hash)

    # The record's cik_hash is derived from the connector's zero-STRIPPED CIK.
    fake_corpus = _make_corpus_response(
        cik=canonical_cik,
        connector_receipt_hash=connector_hash,
        sidecar_hash=hashes["sidecar_hash"],
        classification_hash=hashes["classification_hash"],
    )
    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda fields, db, evidence_owner=None: fake_corpus,
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )
    from app.services import layer3_sec_xbrl_auth_binding as auth_binding_svc
    monkeypatch.setattr(
        auth_binding_svc,
        "require_sec_xbrl_evidence_ownership_marker",
        lambda *args, **kwargs: None,
    )

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": f"fp-padded-{uuid.uuid4().hex[:12]}",
            "cik": padded_cik,
            "company_matrix": ["AAPL"],
            "operator_confirmation": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "full_pipeline_open_ready"
    # The discovered/selected cik_hash is the zero-stripped form's hash.
    assert body["corpus_validation"]["selected_cik_hash"] == _sha256(canonical_cik)
    # No raw CIK (padded or canonical) leaks.
    raw_json = json.dumps(body)
    assert padded_cik not in raw_json
    assert canonical_cik not in raw_json


# ---------------------------------------------------------------------------
# Test 2: CIK hash mismatch -> 409
# ---------------------------------------------------------------------------

def test_full_pipeline_cik_hash_mismatch(tmp_path, monkeypatch) -> None:
    """When the discovered cik_hash doesn't match sha256(cik), return 409 cik_hash_mismatch."""
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    cik = "320193"
    connector_hash = _hash("a")
    sidecar_hash = _hash("b")
    cls_hash = _hash("c")

    # Forge a corpus response with a WRONG cik_hash
    wrong_cik_hash = _sha256("999999")
    corpus_with_wrong_cik = {
        "connector_receipt_hash": connector_hash,
        "validation_receipt_id": "vr-mismatch-001",
        "validation_receipt_hash": _sha256("mismatch"),
        "filing_validation_records": [
            {
                "cik_hash": wrong_cik_hash,
                "form_type": "10-K",
                "supported_degraded_blocked": "supported",
                "authority_hashes": {
                    "fact_authority_receipt_hash": sidecar_hash,
                    "statement_classification_receipt_hash": cls_hash,
                    "arelle_sidecar_receipt_hash": sidecar_hash,
                },
            }
        ],
    }

    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda fields, db, evidence_owner=None: corpus_with_wrong_cik,
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )

    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": "fp-mismatch-001",
            "cik": cik,
            "company_matrix": ["AAPL"],
            "operator_confirmation": True,
        },
    )
    assert r.status_code == 409, r.text
    body = r.json()
    assert body.get("error_code") == "full_pipeline_cik_hash_mismatch"


# ---------------------------------------------------------------------------
# Test 3: No supported filing -> 409
# ---------------------------------------------------------------------------

def test_full_pipeline_no_supported_filing(tmp_path, monkeypatch) -> None:
    """When corpus validation returns no supported records, return 409 no_supported_filing."""
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    cik = "320193"
    connector_hash = _hash("a")

    corpus_no_supported = {
        "connector_receipt_hash": connector_hash,
        "validation_receipt_id": "vr-blocked-001",
        "validation_receipt_hash": _sha256("blocked"),
        "filing_validation_records": [
            {
                "cik_hash": _sha256(cik),
                "form_type": "10-K",
                "supported_degraded_blocked": "blocked",
                "authority_hashes": {},
            }
        ],
    }

    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda fields, db, evidence_owner=None: corpus_no_supported,
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )

    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": "fp-no-supported-001",
            "cik": cik,
            "company_matrix": ["AAPL"],
            "operator_confirmation": True,
        },
    )
    assert r.status_code == 409, r.text
    body = r.json()
    assert body.get("error_code") == "full_pipeline_no_supported_filing"


# ---------------------------------------------------------------------------
# Test 4: Missing operator_confirmation -> 400
# ---------------------------------------------------------------------------

def test_full_pipeline_missing_operator_confirmation(tmp_path, monkeypatch) -> None:
    """operator_confirmation=false (or absent) -> 400 full_pipeline_missing_operator_confirmation."""
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )

    # Stub corpus validation so it is never reached
    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda *a, **kw: (_ for _ in ()).throw(
                AssertionError("corpus_validation should not be called")
            ),
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": "fp-no-confirm-001",
            "cik": "320193",
            "company_matrix": ["AAPL"],
            "operator_confirmation": False,
        },
    )
    assert r.status_code == 400, r.text
    body = r.json()
    assert body.get("error_code") == "full_pipeline_missing_operator_confirmation"


# ---------------------------------------------------------------------------
# Test 5: require_companyfacts_oracle True/False spy
# ---------------------------------------------------------------------------

def _write_staged_companyfacts(
    storage: Path,
    *,
    cik: str,
    connector_receipt_hash: str,
) -> str:
    """Write a minimal companyfacts staged receipt to storage so the loader can discover it.

    Returns the companyfacts_receipt_id.
    Mirrors what stage_sec_xbrl_companyfacts writes, but bypasses the live-network fetch.
    """
    from app.services.layer3_sec_xbrl_offline_companyfacts_stage import (
        SCHEMA_ID as CF_SCHEMA_ID,
        COMPANYFACTS_RECEIPT_DIR,
        COMPANYFACTS_RECEIPT_PREFIX,
        companyfacts_receipt_hash_basis,
    )

    raw_cik = cik.lstrip("0") or "0"
    cik_hash = _sha256(raw_cik)
    companyfacts = {"us-gaap": {"Assets": {"units": {"USD": [{"val": 100, "end": "2023-12-31", "fp": "FY", "fy": 2023}]}}}}
    content = json.dumps(companyfacts, sort_keys=True, indent=2).encode("utf-8")
    content_sha256 = hashlib.sha256(content).hexdigest()

    source_identity_hash = stable_hash(
        {"hash_version": "sec_edgar_companyfacts_source_identity_hash_v1", "cik_hash": cik_hash}
    )
    companyfacts_payload_hash = stable_hash(companyfacts)
    basis = companyfacts_receipt_hash_basis(
        schema_id=CF_SCHEMA_ID,
        source_identity_hash=source_identity_hash,
        cik_hash=cik_hash,
        connector_receipt_hash=connector_receipt_hash,
        companyfacts_payload_hash=companyfacts_payload_hash,
        content_sha256=content_sha256,
    )
    receipt_hash = stable_hash(basis)
    receipt_id = f"{COMPANYFACTS_RECEIPT_PREFIX}-{source_identity_hash[:24]}-{receipt_hash[:24]}"

    raw_path = storage / COMPANYFACTS_RECEIPT_DIR / "companyfacts-store" / f"{receipt_id}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(content)

    receipt = {
        "schema_id": CF_SCHEMA_ID,
        "companyfacts_receipt_id": receipt_id,
        "companyfacts_receipt_hash": receipt_hash,
        "companyfacts_payload_hash": companyfacts_payload_hash,
        "cik_hash": cik_hash,
        "connector_receipt_hash": connector_receipt_hash,
        "companyfacts_observation_count": 1,
        "taxonomy_count": 1,
        "concept_count": 1,
        "content_sha256": content_sha256,
        "recorded_at": "2026-01-01T00:00:00+00:00",
        "gitignored_local_storage": True,
        "operator_surface_exposure": False,
    }
    receipt_path = storage / COMPANYFACTS_RECEIPT_DIR / "receipts" / f"{receipt_id}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")
    return receipt_id


def _setup_oracle_spy_env(tmp_path: Path, monkeypatch: Any) -> tuple[TestClient, Path, list[dict[str, Any]]]:
    """Shared setup for oracle True/False spy tests. Returns (client, storage_dir, cf_calls list)."""
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    cik = "320193"
    connector_hash = _hash("a")
    hashes = _stage_full_evidence_storage(storage_dir, connector_receipt_hash=connector_hash)
    sidecar_hash = hashes["sidecar_hash"]
    cls_hash = hashes["classification_hash"]

    fake_corpus = _make_corpus_response(
        cik=cik,
        connector_receipt_hash=connector_hash,
        sidecar_hash=sidecar_hash,
        classification_hash=cls_hash,
    )
    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda fields, db, evidence_owner=None: fake_corpus,
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )

    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )
    from app.services import layer3_sec_xbrl_auth_binding as auth_binding_svc
    monkeypatch.setattr(
        auth_binding_svc,
        "require_sec_xbrl_evidence_ownership_marker",
        lambda *args, **kwargs: None,
    )

    cf_calls: list[dict[str, Any]] = []

    def _fake_cf(**kwargs: Any) -> dict[str, Any]:
        cf_calls.append(kwargs)
        cf_rid = _write_staged_companyfacts(
            storage_dir, cik=kwargs["cik"], connector_receipt_hash=kwargs["connector_receipt_hash"]
        )
        return {
            "status": "companyfacts_acquired_and_staged",
            "acquire": {"cik_hash": _sha256(cik.lstrip("0") or "0"), "companyfacts_observation_count": 1},
            "stage": {"companyfacts_receipt_id": cf_rid},
        }

    monkeypatch.setattr(orchestrator, "layer3_sec_xbrl_companyfacts_acquire_stage", MagicMock(
        acquire_and_stage_companyfacts=_fake_cf,
    ))

    return client, storage_dir, cf_calls


def test_full_pipeline_companyfacts_oracle_called_when_required(tmp_path, monkeypatch) -> None:
    """require_companyfacts_oracle=True -> acquire_and_stage is called; bundle status reflects oracle."""
    cik = "320193"
    client, storage_dir, cf_calls = _setup_oracle_spy_env(tmp_path, monkeypatch)

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": f"fp-oracle-{uuid.uuid4().hex[:8]}",
            "cik": cik,
            "company_matrix": ["AAPL"],
            "operator_confirmation": True,
            "require_companyfacts_oracle": True,
        },
    )
    assert r.status_code == 200, r.text
    assert len(cf_calls) == 1, "acquire_and_stage should be called when require_companyfacts_oracle=True"
    assert cf_calls[0]["cik"] == cik
    body = r.json()
    assert body["companyfacts_stage"] is not None


def test_full_pipeline_companyfacts_oracle_skipped_when_not_required(tmp_path, monkeypatch) -> None:
    """require_companyfacts_oracle=False -> acquire_and_stage is NOT called; companyfacts_stage is None."""
    cik = "320193"
    client, storage_dir, cf_calls = _setup_oracle_spy_env(tmp_path, monkeypatch)

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": f"fp-no-oracle-{uuid.uuid4().hex[:8]}",
            "cik": cik,
            "company_matrix": ["AAPL"],
            "operator_confirmation": True,
            "require_companyfacts_oracle": False,
        },
    )
    assert r.status_code == 200, r.text
    assert len(cf_calls) == 0, "acquire_and_stage should NOT be called when require_companyfacts_oracle=False"
    body = r.json()
    assert body["companyfacts_stage"] is None


# ---------------------------------------------------------------------------
# Service-level unit tests (no HTTP layer)
# ---------------------------------------------------------------------------

def test_prepare_plan_raises_on_missing_confirmation() -> None:
    """Service raises SecXbrlFullPipelineOrchestratorError (400) with no operator_confirmation."""
    with pytest.raises(orchestrator.SecXbrlFullPipelineOrchestratorError) as exc_info:
        orchestrator.prepare_full_pipeline_open_plan(
            db=None,
            fields={"client_request_id": "x", "cik": "320193", "company_matrix": ["A"], "operator_confirmation": False},
            evidence_owner={},
        )
    assert exc_info.value.error_code == "full_pipeline_missing_operator_confirmation"
    assert exc_info.value.http_status == 400


def test_prepare_plan_raises_on_invalid_cik() -> None:
    """Service raises SecXbrlFullPipelineOrchestratorError (400) when cik is not digits."""
    with pytest.raises(orchestrator.SecXbrlFullPipelineOrchestratorError) as exc_info:
        orchestrator.prepare_full_pipeline_open_plan(
            db=None,
            fields={"client_request_id": "x", "cik": "AAPL", "company_matrix": ["A"], "operator_confirmation": True},
            evidence_owner={},
        )
    assert exc_info.value.error_code == "full_pipeline_invalid_cik"
    assert exc_info.value.http_status == 400


def test_prepare_plan_raises_on_overlong_cik_before_corpus_validation() -> None:
    """A digit-only but >10-digit CIK is rejected (400) BEFORE corpus-validation runs,
    so no live acquisition/staging side effects are triggered (codex P2)."""
    # corpus-validation is the real module here; it must NOT be reached. The 1-10 digit
    # bound check precedes it in the function body, so reaching it would mean the bound
    # check failed to fire.
    with pytest.raises(orchestrator.SecXbrlFullPipelineOrchestratorError) as exc_info:
        orchestrator.prepare_full_pipeline_open_plan(
            db=None,
            fields={
                "client_request_id": "x",
                "cik": "12345678901",  # 11 digits, no leading zeros to strip
                "company_matrix": ["AAPL"],
                "operator_confirmation": True,
            },
            evidence_owner={},
        )
    assert exc_info.value.error_code == "full_pipeline_invalid_cik"
    assert exc_info.value.http_status == 400


def test_full_pipeline_multi_ticker_selects_matching_cik(tmp_path, monkeypatch) -> None:
    """A multi-ticker matrix returns a record per company; selection must filter by the
    supplied CIK BEFORE the 10-K preference, so another company's 10-K appearing first
    does not cause a spurious cik_hash mismatch (codex P2)."""
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    apple_cik = "320193"
    connector_hash = _hash("a")
    # Real staged storage is keyed to the connector hash; the matching record points at it.
    hashes = _stage_full_evidence_storage(storage_dir, connector_receipt_hash=connector_hash)

    # Record 1: a DIFFERENT company (e.g. MSFT), a 10-K, appears FIRST, dummy hashes.
    other_record = {
        "cik_hash": _sha256("789019"),
        "form_type": "10-K",
        "supported_degraded_blocked": "supported",
        "authority_hashes": {
            "fact_authority_receipt_hash": _hash("9"),
            "statement_classification_receipt_hash": _hash("8"),
            "arelle_sidecar_receipt_hash": _hash("9"),
        },
    }
    # Record 2: Apple, a 10-K, real staged hashes — the one the supplied CIK matches.
    apple_record = {
        "cik_hash": _sha256(apple_cik),
        "form_type": "10-K",
        "supported_degraded_blocked": "supported",
        "authority_hashes": {
            "fact_authority_receipt_hash": hashes["sidecar_hash"],
            "statement_classification_receipt_hash": hashes["classification_hash"],
            "arelle_sidecar_receipt_hash": hashes["sidecar_hash"],
        },
    }
    multi_corpus = {
        "connector_receipt_hash": connector_hash,
        "validation_receipt_id": "vr-multi-001",
        "validation_receipt_hash": _sha256("multi"),
        "filing_validation_records": [other_record, apple_record],  # other FIRST
    }
    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda fields, db, evidence_owner=None: multi_corpus,
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )
    from app.services import layer3_sec_xbrl_auth_binding as auth_binding_svc
    monkeypatch.setattr(
        auth_binding_svc,
        "require_sec_xbrl_evidence_ownership_marker",
        lambda *args, **kwargs: None,
    )

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": f"fp-multi-{uuid.uuid4().hex[:12]}",
            "cik": apple_cik,
            "company_matrix": ["MSFT", "AAPL"],
            "operator_confirmation": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "full_pipeline_open_ready"
    # The Apple record (not the first-listed MSFT 10-K) was selected.
    assert body["corpus_validation"]["selected_cik_hash"] == _sha256(apple_cik)


# ---------------------------------------------------------------------------
# Task B — 5 new tests
# ---------------------------------------------------------------------------

# B1: ticker/CIK pairing pre-check fires before corpus-validation
# ---------------------------------------------------------------------------

def test_full_pipeline_cik_not_in_matrix() -> None:
    """Service raises 409 full_pipeline_cik_not_in_company_matrix when CIK doesn't belong to any
    ticker in company_matrix — BEFORE corpus-validation is reached."""
    # Apple's CIK 320193 is not MSFT's CIK (789019).
    # corpus-validation is the real module; if it were reached it would do live network work
    # or fail differently — reaching it means the pre-check did NOT fire.
    with pytest.raises(orchestrator.SecXbrlFullPipelineOrchestratorError) as exc_info:
        orchestrator.prepare_full_pipeline_open_plan(
            db=None,
            fields={
                "client_request_id": "x",
                "cik": "320193",
                "company_matrix": ["MSFT"],
                "operator_confirmation": True,
            },
            evidence_owner={},
        )
    assert exc_info.value.error_code == "full_pipeline_cik_not_in_company_matrix"
    assert exc_info.value.http_status == 409


# B2: zero-padded overlong CIK rejected on RAW length before lstrip("0")
# ---------------------------------------------------------------------------

def test_full_pipeline_zero_padded_overlong_cik() -> None:
    """A digit-only but 17-char zero-padded CIK is rejected (400 invalid_cik) on RAW length
    check BEFORE lstrip('0') would canonicalize it to a valid-looking value."""
    with pytest.raises(orchestrator.SecXbrlFullPipelineOrchestratorError) as exc_info:
        orchestrator.prepare_full_pipeline_open_plan(
            db=None,
            fields={
                "client_request_id": "x",
                "cik": "00000000000320193",  # 17 chars — exceeds 10-digit bound
                "company_matrix": ["AAPL"],
                "operator_confirmation": True,
            },
            evidence_owner={},
        )
    assert exc_info.value.error_code == "full_pipeline_invalid_cik"
    assert exc_info.value.http_status == 400


# B3: incomplete authority hashes -> 409 governed error
# ---------------------------------------------------------------------------

def test_full_pipeline_incomplete_authority_hashes(tmp_path, monkeypatch) -> None:
    """When the selected supported record has arelle_sidecar_receipt_hash but empty
    fact_authority_receipt_hash / statement_classification_receipt_hash, the route returns
    409 full_pipeline_incomplete_authority_hashes instead of an ungoverned 500."""
    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    cik = "320193"
    connector_hash = _hash("a")
    sidecar_hash = _hash("b")

    # Supported record: arelle_sidecar_receipt_hash is truthy so the supported filter passes,
    # but both consumable hashes are empty — the orchestrator's defense-in-depth guard fires.
    incomplete_record = {
        "cik_hash": _sha256(cik),
        "form_type": "10-K",
        "supported_degraded_blocked": "supported",
        "authority_hashes": {
            "arelle_sidecar_receipt_hash": sidecar_hash,
            "fact_authority_receipt_hash": "",
            "statement_classification_receipt_hash": "",
        },
    }
    fake_corpus = {
        "connector_receipt_hash": connector_hash,
        "validation_receipt_id": "vr-incomplete-001",
        "validation_receipt_hash": _sha256("incomplete"),
        "filing_validation_records": [incomplete_record],
    }

    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda fields, db, evidence_owner=None: fake_corpus,
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": "fp-incomplete-hashes-001",
            "cik": cik,
            "company_matrix": ["AAPL"],
            "operator_confirmation": True,
        },
    )
    assert r.status_code == 409, r.text
    body = r.json()
    assert body.get("error_code") == "full_pipeline_incomplete_authority_hashes"


# B4: open handler returning a JSONResponse error is passed through unchanged
# ---------------------------------------------------------------------------

def test_full_pipeline_open_step_error_passthrough(tmp_path, monkeypatch) -> None:
    """When the staged-evidence open handler returns a JSONResponse error, the full-pipeline
    route passes it through unchanged (status code and body preserved)."""
    from fastapi.responses import JSONResponse as _JSONResponse

    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    cik = "320193"
    connector_hash = _hash("a")
    sidecar_hash = _hash("b")
    cls_hash = _hash("c")

    # Valid corpus record — all three hashes truthy so we reach the open step.
    valid_record = {
        "cik_hash": _sha256(cik),
        "form_type": "10-K",
        "supported_degraded_blocked": "supported",
        "authority_hashes": {
            "arelle_sidecar_receipt_hash": sidecar_hash,
            "fact_authority_receipt_hash": sidecar_hash,
            "statement_classification_receipt_hash": cls_hash,
        },
    }
    fake_corpus = {
        "connector_receipt_hash": connector_hash,
        "validation_receipt_id": "vr-open-passthrough-001",
        "validation_receipt_hash": _sha256("passthrough"),
        "filing_validation_records": [valid_record],
    }

    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda fields, db, evidence_owner=None: fake_corpus,
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )

    # Stub the open handler to return a JSONResponse error.
    import app.api.layer3 as _layer3_api
    monkeypatch.setattr(
        _layer3_api,
        "post_sec_xbrl_operator_review_workflow_open_from_staged_evidence",
        lambda req, request, db: _JSONResponse(
            status_code=409,
            content={"error_code": "some_open_error"},
        ),
    )

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": "fp-open-passthrough-001",
            "cik": cik,
            "company_matrix": ["AAPL"],
            "operator_confirmation": True,
            "require_companyfacts_oracle": False,
        },
    )
    assert r.status_code == 409, r.text
    body = r.json()
    assert body.get("error_code") == "some_open_error"


# B5: SecXbrlCompanyfactsStageError from acquire_and_stage propagates as governed response
# ---------------------------------------------------------------------------

def test_full_pipeline_companyfacts_failure_propagates(tmp_path, monkeypatch) -> None:
    """When require_companyfacts_oracle=True and acquire_and_stage_companyfacts raises
    SecXbrlCompanyfactsStageError, the route returns a governed 409 via
    _companyfacts_stage_error_response."""
    from app.services.layer3_sec_xbrl_offline_companyfacts_stage import SecXbrlCompanyfactsStageError

    client, storage_dir = _make_test_client(tmp_path, monkeypatch)

    cik = "320193"
    connector_hash = _hash("a")
    sidecar_hash = _hash("b")
    cls_hash = _hash("c")

    # Valid corpus record — all hashes truthy so we pass steps 1-4 and reach step 5.
    valid_record = {
        "cik_hash": _sha256(cik),
        "form_type": "10-K",
        "supported_degraded_blocked": "supported",
        "authority_hashes": {
            "arelle_sidecar_receipt_hash": sidecar_hash,
            "fact_authority_receipt_hash": sidecar_hash,
            "statement_classification_receipt_hash": cls_hash,
        },
    }
    fake_corpus = {
        "connector_receipt_hash": connector_hash,
        "validation_receipt_id": "vr-cf-fail-001",
        "validation_receipt_hash": _sha256("cf-fail"),
        "filing_validation_records": [valid_record],
    }

    monkeypatch.setattr(
        orchestrator,
        "layer3_sec_edgar_real_company_corpus_validation",
        MagicMock(
            validate_sec_edgar_real_company_corpus_product_path=lambda fields, db, evidence_owner=None: fake_corpus,
            VALIDATION_MODE=corpus_svc.VALIDATION_MODE,
            OPERATOR_DECISION=corpus_svc.OPERATOR_DECISION,
        ),
    )
    from app.services import layer3_sec_xbrl_in_app_auth_policy as auth_policy_svc
    monkeypatch.setattr(
        auth_policy_svc,
        "derive_sec_xbrl_evidence_owner",
        lambda headers: {"owner_hash": _hash("f"), "auth_owner_mode": "test"},
    )

    # Stub the companyfacts acquire-and-stage to raise SecXbrlCompanyfactsStageError.
    cf_mock = MagicMock()
    cf_mock.acquire_and_stage_companyfacts.side_effect = SecXbrlCompanyfactsStageError(
        "companyfacts_stage_test_error",
        "Stubbed companyfacts stage failure for test.",
    )
    monkeypatch.setattr(orchestrator, "layer3_sec_xbrl_companyfacts_acquire_stage", cf_mock)

    r = client.post(
        FULL_PIPELINE_URL,
        json={
            "client_request_id": "fp-cf-fail-001",
            "cik": cik,
            "company_matrix": ["AAPL"],
            "operator_confirmation": True,
            "require_companyfacts_oracle": True,
        },
    )
    # _companyfacts_stage_error_response always returns 409 with the exc.code as error_code.
    assert r.status_code == 409, r.text
    body = r.json()
    assert body.get("error_code") == "companyfacts_stage_test_error"
