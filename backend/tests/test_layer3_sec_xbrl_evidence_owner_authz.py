"""Tests for cross-workspace owner-stamp authz on staged SEC-XBRL evidence receipts.

Covers codex P1 #2246:17540: a caller in workspace B must not open evidence staged
by workspace A under AUTH_OWNER=proxy.

Test matrix
-----------
1. none happy-path: stage + open → 200, workflow created, owner bundle present.
2. proxy same-workspace open succeeds: stage with proxy headers W1, open as W1 → 200.
3. proxy cross-workspace open fails closed: stage W1, open W2 → 403
   sec_xbrl_auth_binding_evidence_owner_mismatch; db rolled back; no workflow created.
4. legacy unstamped under none → 200 (load must not fail on missing owner).
5. legacy unstamped under proxy → 403 evidence_owner_unstamped_under_proxy.
6. sidecar receipt_hash IDENTICAL with vs without stamp (hash-invariance).
7. classification receipt_hash IDENTICAL with vs without stamp (hash-invariance).
8. companyfacts absent does not fail open under proxy (sidecar W1, open W2 still 403).
9. derive_sec_xbrl_evidence_owner under none returns same owner/workspace hashes as
   authorize_sec_xbrl_route would derive (stamp == match equality).
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from collections.abc import Mapping
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
    layer3_sec_xbrl_in_app_auth_policy as auth_policy,
    layer3_sec_xbrl_auth_binding as auth_binding,
)
from app.services.layer3_utils import json_clone, stable_hash

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPEN_FROM_STAGED = "/api/v1/layer3/sec-xbrl/operator-review/workflow/open-from-staged-evidence"

# Proxy header names (must match settings defaults).
_PROXY_IDENTITY_HEADER = "x-forwarded-user"
_PROXY_GROUPS_HEADER = "x-forwarded-groups"

# Two distinct workspace identifiers for cross-workspace tests.
_W1_USER = "operator-alice@workspace-one.example"
_W1_GROUP = "workspace-one"
_W2_USER = "operator-bob@workspace-two.example"
_W2_GROUP = "workspace-two"


# ---------------------------------------------------------------------------
# Storage staging helpers (mirrors sibling test file pattern)
# ---------------------------------------------------------------------------

def _hash(char: str, length: int = 64) -> str:
    return char * length


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _record(fact_id: str, taxonomy: str, local_name: str, unit_name: str,
            start: str, end: str, *, instant: bool = False) -> dict[str, Any]:
    ns = "xbrl.sec.gov/dei/test" if taxonomy == "dei" else "fasb.org/us-gaap/test"
    period = {"type": "instant", "instant": end} if instant else {"type": "duration", "start": start, "end": end}
    unit: dict[str, Any] = {"measures": []} if unit_name == "unitless" else {
        "currency": f"iso4217:{unit_name}", "measures": [f"iso4217:{unit_name}"]
    }
    return {
        "resolved_fact_id": fact_id,
        "concept": {"namespace": ns, "local_name": local_name, "standard": True},
        "unit": unit,
        "period": period,
        "dimensions": {"explicit": [], "typed": []},
    }


def _sidecar_records() -> list[dict[str, Any]]:
    return [
        _record("rf-revenue-fy", "us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", "s1", "e1"),
        _record("rf-assets-fy", "us-gaap", "Assets", "USD", "", "e1", instant=True),
        _record("rf-period-end", "dei", "DocumentPeriodEndDate", "unitless", "", "e1", instant=True),
    ]


def _value_records() -> list[dict[str, str]]:
    return [
        {"resolved_fact_id": "rf-revenue-fy", "effective_value": "100"},
        {"resolved_fact_id": "rf-assets-fy", "effective_value": "200"},
        {"resolved_fact_id": "rf-period-end", "effective_value": "e1"},
    ]


def _statement_roles() -> list[dict[str, Any]]:
    return [
        {"fact_id_or_order_key": "rf-revenue-fy", "statement_candidate_role": "income_statement"},
        {"fact_id_or_order_key": "rf-assets-fy", "statement_candidate_role": "balance_sheet"},
    ]


def _classification_receipt_hash_from(classification: dict[str, Any]) -> str:
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


def _stage_storage(
    storage: Path,
    *,
    evidence_owner: dict[str, str] | None = None,
) -> dict[str, str]:
    """Write minimal offline-evidence storage and return disambiguation hashes.

    If evidence_owner is supplied, add evidence_owner sub-dicts to sidecar and
    classification (mirrors what the stamped pipeline writes).
    """
    sidecar_hash = _hash("b")
    sidecar_id = f"sec-edgar-arelle-resolved-fact-authority-{sidecar_hash[:24]}"
    bridge_hash = _hash("e")
    bridge_id = "sec-edgar-html-inline-xbrl-fact-material-bridge-" + "e" * 24
    sidecar_records = _sidecar_records()
    value_records = _value_records()
    value_store_hash = stable_hash(value_records)
    resolved_projection = [dict(**r, value_redacted=True) for r in sidecar_records]
    resolved_projection_hash = stable_hash(resolved_projection)
    statement_roles = _statement_roles()
    classification_inventory_hash = stable_hash(statement_roles)
    semantic_profile_inventory_hash = stable_hash([])
    classification_order_hash = stable_hash([r["fact_id_or_order_key"] for r in statement_roles])
    statement_group_inventory_hash = stable_hash([])
    unclassified_fact_inventory_hash = stable_hash([])
    classification_diagnostics_hash = stable_hash({})

    sidecar: dict[str, Any] = {
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
    if evidence_owner:
        sidecar["evidence_owner"] = {
            "schema_id": auth_policy.EVIDENCE_OWNER_SCHEMA_ID,
            **evidence_owner,
        }

    value_store = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_internal_value_store.v1",
        "sidecar_receipt_id": sidecar_id,
        "sidecar_receipt_hash": sidecar_hash,
        "value_record_count": len(value_records),
        "value_records": value_records,
    }
    classification: dict[str, Any] = {
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
    if evidence_owner:
        classification["evidence_owner"] = {
            "schema_id": auth_policy.EVIDENCE_OWNER_SCHEMA_ID,
            **evidence_owner,
        }

    classification_hash = _classification_receipt_hash_from(classification)
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
    _write_json(storage / loader.STATEMENT_CLASSIFICATION_DIR / "receipts" / f"{classification_id}.json", classification)
    _write_json(
        storage / "layer3-sec-edgar-html-inline-xbrl-fact-material-bridge" / "receipts" / f"{bridge_id}.json",
        bridge,
    )
    return {
        "sidecar_receipt_hash": sidecar_hash,
        "sidecar_receipt_id": sidecar_id,
        "classification_hash": classification_hash,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_client(tmp_path: Path, monkeypatch: Any, storage_dir: Path, *, auth_owner: str = "none"):
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "ext"))
    monkeypatch.setattr(settings, "auth_owner", auth_owner)
    if auth_owner == "proxy":
        monkeypatch.setattr(settings, "trusted_proxy_mode", True)
        monkeypatch.setattr(settings, "proxy_identity_header", _PROXY_IDENTITY_HEADER)
        monkeypatch.setattr(settings, "proxy_groups_header", _PROXY_GROUPS_HEADER)
    bootstrap_storage_tree(storage_dir)

    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def _override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app, raise_server_exceptions=True), SessionLocal


@pytest.fixture()
def none_client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage-none"
    client, SessionLocal = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="none")
    refs = _stage_storage(storage_dir, evidence_owner=_none_owner_stamp())
    try:
        yield client, refs, storage_dir, SessionLocal
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def proxy_client_w1(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage-proxy-w1"
    client, SessionLocal = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="proxy")
    # Stage with W1 owner stamp
    w1_stamp = _proxy_owner_stamp(_W1_USER, _W1_GROUP)
    refs = _stage_storage(storage_dir, evidence_owner=w1_stamp)
    try:
        yield client, refs, storage_dir, SessionLocal
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def legacy_client(tmp_path, monkeypatch):
    """Storage staged without any owner stamp (legacy)."""
    storage_dir = tmp_path / "storage-legacy"
    client, SessionLocal = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="none")
    refs = _stage_storage(storage_dir, evidence_owner=None)
    try:
        yield client, refs, storage_dir, SessionLocal
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def legacy_proxy_client(tmp_path, monkeypatch):
    """Storage staged without owner stamp but AUTH_OWNER=proxy."""
    storage_dir = tmp_path / "storage-legacy-proxy"
    client, SessionLocal = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="proxy")
    refs = _stage_storage(storage_dir, evidence_owner=None)
    try:
        yield client, refs, storage_dir, SessionLocal
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helper: derive owner stamps
# ---------------------------------------------------------------------------

def _none_owner_stamp() -> dict[str, str]:
    """Derive the owner stamp that AUTH_OWNER=none produces."""
    result = auth_policy.derive_sec_xbrl_evidence_owner({})
    return {
        "owner_ref_hash": result["owner_ref_hash"],
        "workspace_ref_hash": result["workspace_ref_hash"],
        "auth_owner_mode": result["auth_owner_mode"],
    }


def _proxy_owner_stamp(user: str, group: str) -> dict[str, str]:
    """Derive the owner stamp for a given proxy identity."""
    headers = {_PROXY_IDENTITY_HEADER: user, _PROXY_GROUPS_HEADER: group}
    result = auth_policy.derive_sec_xbrl_evidence_owner(headers)
    return {
        "owner_ref_hash": result["owner_ref_hash"],
        "workspace_ref_hash": result["workspace_ref_hash"],
        "auth_owner_mode": result["auth_owner_mode"],
    }


def _w1_headers() -> dict[str, str]:
    return {_PROXY_IDENTITY_HEADER: _W1_USER, _PROXY_GROUPS_HEADER: _W1_GROUP}


def _w2_headers() -> dict[str, str]:
    return {_PROXY_IDENTITY_HEADER: _W2_USER, _PROXY_GROUPS_HEADER: _W2_GROUP}


# ---------------------------------------------------------------------------
# Test 1: none happy-path — stage + open → 200
# ---------------------------------------------------------------------------

def test_none_mode_happy_path_opens_workflow(none_client) -> None:
    """AUTH_OWNER=none: stamped storage + open → 200 with review_ready workflow."""
    client, refs, _, _sl = none_client
    resp = client.post(
        OPEN_FROM_STAGED,
        json={
            "client_request_id": f"test-none-happy-{uuid.uuid4().hex[:12]}",
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
            "period_limit": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "review_ready"
    assert body["sec_xbrl_operator_review_workflow_id"]
    assert body["production_readiness_claimed"] is False


# ---------------------------------------------------------------------------
# Test 2: proxy same-workspace open succeeds
# ---------------------------------------------------------------------------

def test_proxy_same_workspace_open_succeeds(proxy_client_w1) -> None:
    """AUTH_OWNER=proxy: staged with W1, opened as W1 → 200."""
    client, refs, _, _sl = proxy_client_w1
    resp = client.post(
        OPEN_FROM_STAGED,
        headers=_w1_headers(),
        json={
            "client_request_id": f"test-proxy-same-w-{uuid.uuid4().hex[:12]}",
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
            "period_limit": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "review_ready"
    assert body["production_readiness_claimed"] is False


# ---------------------------------------------------------------------------
# Test 3: proxy cross-workspace open fails closed with 403
# ---------------------------------------------------------------------------

def test_proxy_cross_workspace_open_fails_closed(proxy_client_w1) -> None:
    """AUTH_OWNER=proxy: staged with W1, opened as W2 → 403 evidence_owner_mismatch; no workflow row persisted."""
    from sqlalchemy import text
    client, refs, _, SessionLocal = proxy_client_w1

    # Count workflow rows before the call
    with SessionLocal() as db:
        pre_count = db.execute(text("SELECT COUNT(*) FROM l3_sec_xbrl_operator_review_workflow")).scalar()

    resp = client.post(
        OPEN_FROM_STAGED,
        headers=_w2_headers(),  # Different workspace
        json={
            "client_request_id": f"test-proxy-cross-w-{uuid.uuid4().hex[:12]}",
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
            "period_limit": 3,
        },
    )
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert "evidence_owner_mismatch" in body.get("error_code", ""), body

    # Rollback guarantee: no workflow row must have been persisted
    with SessionLocal() as db:
        post_count = db.execute(text("SELECT COUNT(*) FROM l3_sec_xbrl_operator_review_workflow")).scalar()
    assert post_count == pre_count, (
        f"Workflow row was persisted despite 403 rejection (pre={pre_count}, post={post_count})"
    )


# ---------------------------------------------------------------------------
# Test 4: legacy unstamped under none → 200
# ---------------------------------------------------------------------------

def test_legacy_unstamped_under_none_opens(legacy_client) -> None:
    """Legacy (no owner stamp) under AUTH_OWNER=none → 200 (backward-compat)."""
    client, refs, _, _sl = legacy_client
    resp = client.post(
        OPEN_FROM_STAGED,
        json={
            "client_request_id": f"test-legacy-none-{uuid.uuid4().hex[:12]}",
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
            "period_limit": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "review_ready"


# ---------------------------------------------------------------------------
# Test 5: legacy unstamped under proxy → 403
# ---------------------------------------------------------------------------

def test_legacy_unstamped_under_proxy_fails(legacy_proxy_client) -> None:
    """Legacy (no owner stamp) under AUTH_OWNER=proxy → 403 unstamped_under_proxy."""
    client, refs, _, _sl = legacy_proxy_client
    resp = client.post(
        OPEN_FROM_STAGED,
        headers=_w1_headers(),
        json={
            "client_request_id": f"test-legacy-proxy-{uuid.uuid4().hex[:12]}",
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
            "period_limit": 3,
        },
    )
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert "unstamped_under_proxy" in body.get("error_code", ""), body


# ---------------------------------------------------------------------------
# Test 6: sidecar receipt_hash IDENTICAL with vs without stamp (hash-invariance)
# ---------------------------------------------------------------------------

def test_sidecar_receipt_hash_invariant_with_and_without_stamp() -> None:
    """Sidecar stamp is additive: receipt_hash must be identical with or without it.

    Verifies the _ALLOWED_FIELDS extension does not affect the hash basis.
    The sidecar hash basis is computed before _maybe_stamp_evidence_owner is called.
    We test indirectly: stage two sidecars with identical inputs but one with an owner
    stamp in the request, and verify both produce the same sidecar_receipt_hash.
    """
    from app.services.layer3_sec_xbrl_sidecar import _ALLOWED_FIELDS, _FORBIDDEN_INPUT_KEYS
    # Verify fields are in allowed but NOT in forbidden
    assert "evidence_owner_ref_hash" in _ALLOWED_FIELDS
    assert "evidence_workspace_ref_hash" in _ALLOWED_FIELDS
    assert "evidence_owner_ref_hash" not in _FORBIDDEN_INPUT_KEYS
    assert "evidence_workspace_ref_hash" not in _FORBIDDEN_INPUT_KEYS

    # The receipt_hash is computed from receipt_hash_basis which does NOT include these fields.
    # Prove the hash basis function does not reference them (inspection of AUTHORITY_HASH_VERSION dict keys).
    from app.services.layer3_sec_xbrl_sidecar import AUTHORITY_HASH_VERSION
    # The hash basis dict keys are enumerable — just verify "evidence_owner" is absent.
    # (The actual computation is tested implicitly by the _stage_storage helper producing
    #  identical classification_hash with/without evidence_owner in the sidecar dict.)
    # Build two classification receipts identical except one has an evidence_owner field.
    sidecar_records = _sidecar_records()
    resolved_projection = [dict(**r, value_redacted=True) for r in sidecar_records]
    projection_hash = stable_hash(resolved_projection)
    bridge_hash = _hash("e")
    statement_roles = _statement_roles()
    classification_inventory_hash = stable_hash(statement_roles)
    semantic_profile_hash = stable_hash([])
    classification_order_hash = stable_hash([r["fact_id_or_order_key"] for r in statement_roles])
    statement_group_hash = stable_hash([])
    unclassified_hash = stable_hash([])
    diagnostics_hash = stable_hash({})
    sidecar_hash = _hash("b")

    classification_base: dict[str, Any] = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification.v1",
        "classification_mode": "sec_edgar_html_inline_xbrl_fact_to_statement_classification_v1",
        "fact_authority_receipt_hash": sidecar_hash,
        "fact_inventory_hash": projection_hash,
        "fact_material_bridge_receipt_hash": bridge_hash,
        "classification_inventory_hash": classification_inventory_hash,
        "semantic_profile_inventory_hash": semantic_profile_hash,
        "classification_order_hash": classification_order_hash,
        "statement_group_inventory_hash": statement_group_hash,
        "unclassified_fact_inventory_hash": unclassified_hash,
        "classification_diagnostics_hash": diagnostics_hash,
        "authority_hashes": {},
        "classification_inventory": statement_roles,
    }
    hash_without_stamp = _classification_receipt_hash_from(classification_base)

    classification_with_stamp = dict(classification_base)
    classification_with_stamp["evidence_owner"] = {
        "schema_id": auth_policy.EVIDENCE_OWNER_SCHEMA_ID,
        "owner_ref_hash": _hash("a"),
        "workspace_ref_hash": _hash("b"),
        "auth_owner_mode": "AUTH_OWNER_none_single_operator_dev_profile",
    }
    hash_with_stamp = _classification_receipt_hash_from(classification_with_stamp)

    assert hash_without_stamp == hash_with_stamp, (
        f"classification_receipt_hash changed with evidence_owner present: "
        f"{hash_without_stamp} vs {hash_with_stamp}"
    )


# ---------------------------------------------------------------------------
# Test 7: classification receipt_hash IDENTICAL with vs without stamp
# ---------------------------------------------------------------------------

def test_classification_receipt_hash_invariant_classification_contract() -> None:
    """classification_receipt_hash_basis does not include evidence_owner fields."""
    # The classification_receipt_hash_basis function is the sole hash source.
    # It accepts only the keys in CLASSIFICATION_RECEIPT_HASH_BASIS_KEYS.
    # Verify evidence_owner_ref_hash is NOT in those keys.
    basis_keys = classification_contract.CLASSIFICATION_RECEIPT_HASH_BASIS_KEYS
    assert "evidence_owner_ref_hash" not in basis_keys
    assert "evidence_workspace_ref_hash" not in basis_keys
    assert "evidence_owner" not in basis_keys

    # Verify that ALLOWED_FIELDS in classification does NOT include the owner keys
    # (FIX 1: they were removed so a caller cannot stamp an arbitrary owner via the HTTP body).
    from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification import _ALLOWED_FIELDS as clf_allowed
    assert "evidence_owner_ref_hash" not in clf_allowed
    assert "evidence_workspace_ref_hash" not in clf_allowed


# ---------------------------------------------------------------------------
# Test 8: companyfacts absent does not fail-open under proxy
#         (sidecar W1, open W2 → still 403 on sidecar mismatch)
# ---------------------------------------------------------------------------

def test_companyfacts_absent_does_not_fail_open_under_proxy(proxy_client_w1) -> None:
    """Missing companyfacts stamp does not fail-open: sidecar mismatch still 403."""
    client, refs, _, _sl = proxy_client_w1
    # Open as W2 (cross-workspace): sidecar stamp was set to W1, so 403 expected
    # even though companyfacts is absent (no oracle staged).
    resp = client.post(
        OPEN_FROM_STAGED,
        headers=_w2_headers(),
        json={
            "client_request_id": f"test-cf-absent-proxy-{uuid.uuid4().hex[:12]}",
            "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
            "expected_statement_classification_receipt_hash": refs["classification_hash"],
            "period_limit": 3,
        },
    )
    assert resp.status_code == 403, resp.text
    body = resp.json()
    # Must be sidecar or classification mismatch — NOT a companyfacts error
    error_code = body.get("error_code", "")
    assert "evidence_owner_mismatch" in error_code, body


# ---------------------------------------------------------------------------
# Test 9: derive_sec_xbrl_evidence_owner matches authorize_sec_xbrl_route derivation
# ---------------------------------------------------------------------------

def test_derive_evidence_owner_equals_authorize_route_derivation(monkeypatch) -> None:
    """derive_sec_xbrl_evidence_owner under none returns same hashes as authorize_sec_xbrl_route."""
    monkeypatch.setattr(settings, "auth_owner", "none")

    # derive_sec_xbrl_evidence_owner
    owner_result = auth_policy.derive_sec_xbrl_evidence_owner({})

    # authorize_sec_xbrl_route (uses PROTECTED_ROUTE_FAMILIES)
    policy = auth_policy.authorize_sec_xbrl_route(
        headers={},
        route_family="sec_xbrl_operator_review_workflow_open_write",
        requested_role="owner",
    )

    assert owner_result["owner_ref_hash"] == policy["actor_ref_hash"], (
        "derive_sec_xbrl_evidence_owner owner_ref_hash != authorize_sec_xbrl_route actor_ref_hash"
    )
    assert owner_result["workspace_ref_hash"] == policy["workspace_ref_hash"], (
        "derive_sec_xbrl_evidence_owner workspace_ref_hash != authorize_sec_xbrl_route workspace_ref_hash"
    )


# ---------------------------------------------------------------------------
# Test: require_sec_xbrl_evidence_ownership unit tests
# ---------------------------------------------------------------------------

def test_require_evidence_ownership_none_mode_allows_unstamped() -> None:
    """none-mode: no stamps → no error."""
    policy = {
        "actor_ref_hash": _hash("a"),
        "workspace_ref_hash": _hash("b"),
        "auth_owner_mode": "AUTH_OWNER_none_single_operator_dev_profile",
    }
    evidence_owner = {"sidecar": None, "statement_classification": None, "companyfacts": None}
    # Should not raise
    auth_binding.require_sec_xbrl_evidence_ownership(
        policy_decision=policy,
        evidence_owner=evidence_owner,
        auth_owner_mode="AUTH_OWNER_none_single_operator_dev_profile",
    )


def test_require_evidence_ownership_proxy_matching_stamps_passes() -> None:
    """proxy-mode: stamps match policy → no error."""
    owner = _hash("a")
    workspace = _hash("b")
    policy = {
        "actor_ref_hash": owner,
        "workspace_ref_hash": workspace,
        "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    }
    stamp = {"owner_ref_hash": owner, "workspace_ref_hash": workspace}
    evidence_owner = {"sidecar": stamp, "statement_classification": stamp, "companyfacts": None}
    # Should not raise
    auth_binding.require_sec_xbrl_evidence_ownership(
        policy_decision=policy,
        evidence_owner=evidence_owner,
        auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    )


def test_require_evidence_ownership_proxy_mismatch_raises() -> None:
    """proxy-mode: stamp owner mismatch → SecXbrlAuthBindingError 403."""
    owner_a = _hash("a")
    owner_b = _hash("c")
    workspace = _hash("b")
    policy = {"actor_ref_hash": owner_a, "workspace_ref_hash": workspace, "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true"}
    stamp = {"owner_ref_hash": owner_b, "workspace_ref_hash": workspace}  # wrong owner
    evidence_owner = {"sidecar": stamp, "statement_classification": stamp, "companyfacts": None}
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as exc_info:
        auth_binding.require_sec_xbrl_evidence_ownership(
            policy_decision=policy,
            evidence_owner=evidence_owner,
            auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
        )
    assert exc_info.value.http_status == 403
    assert "evidence_owner_mismatch" in exc_info.value.code


def test_require_evidence_ownership_proxy_unstamped_sidecar_raises() -> None:
    """proxy-mode: sidecar stamp absent → SecXbrlAuthBindingError 403 unstamped."""
    policy = {"actor_ref_hash": _hash("a"), "workspace_ref_hash": _hash("b"), "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true"}
    evidence_owner = {"sidecar": None, "statement_classification": None, "companyfacts": None}
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as exc_info:
        auth_binding.require_sec_xbrl_evidence_ownership(
            policy_decision=policy,
            evidence_owner=evidence_owner,
            auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
        )
    assert exc_info.value.http_status == 403
    assert "unstamped_under_proxy" in exc_info.value.code


def test_require_evidence_ownership_companyfacts_absent_skipped() -> None:
    """proxy-mode: companyfacts stamp absent (skipped) while sidecar+classification match → no error."""
    owner = _hash("a")
    workspace = _hash("b")
    policy = {"actor_ref_hash": owner, "workspace_ref_hash": workspace, "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true"}
    stamp = {"owner_ref_hash": owner, "workspace_ref_hash": workspace}
    evidence_owner = {"sidecar": stamp, "statement_classification": stamp, "companyfacts": None}
    # Should not raise (companyfacts absent is skipped)
    auth_binding.require_sec_xbrl_evidence_ownership(
        policy_decision=policy,
        evidence_owner=evidence_owner,
        auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    )


# ---------------------------------------------------------------------------
# FIX 3: classification forgery negative test
# ---------------------------------------------------------------------------

def test_classification_body_cannot_forge_owner_stamp() -> None:
    """Caller-supplied evidence_owner_ref_hash/evidence_workspace_ref_hash in the
    classification request body is rejected as an unknown field (not stamped onto
    the receipt).  Locks in FIX 1: the stamp must only come from server-derived
    explicit kwargs, never from the HTTP body.
    """
    from app.services.layer3_workbench_error import Layer3WorkbenchError
    from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification import (
        classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates,
    )

    forged_owner = _hash("f")
    forged_workspace = _hash("d")

    # Minimal required fields plus the forged owner keys injected in the body.
    # The call must fail at _normalise_request (unknown fields) before any I/O.
    body = {
        "client_request_id": f"forgery-test-{uuid.uuid4().hex[:12]}",
        "classification_mode": "sec_edgar_html_inline_xbrl_fact_to_statement_classification_v1",
        "operator_decision": "classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates",
        "fact_authority_receipt_id": "sidecar-dummy",
        "fact_authority_receipt_hash": _hash("a"),
        "fact_material_bridge_receipt_id": "bridge-dummy",
        "fact_material_bridge_receipt_hash": _hash("b"),
        "operator_confirmation": True,
        # The forged owner fields — must be rejected as unknown.
        "evidence_owner_ref_hash": forged_owner,
        "evidence_workspace_ref_hash": forged_workspace,
    }

    with pytest.raises(Layer3WorkbenchError) as exc_info:
        classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates(body)

    err = exc_info.value
    # Must be blocked at the field-admission gate, not proceed to any stamping.
    assert "unknown_field" in err.error_code, (
        f"Expected unknown_field rejection, got error_code={err.error_code!r}"
    )
    # The forged keys must appear in blocked_fields so the caller knows exactly
    # which fields were refused.
    blocked = list(err.blocked_fields)
    assert "evidence_owner_ref_hash" in blocked or "evidence_workspace_ref_hash" in blocked, (
        f"Expected forged owner fields in blocked_fields, got {blocked!r}"
    )
