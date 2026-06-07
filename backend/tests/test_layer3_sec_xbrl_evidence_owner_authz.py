"""Tests for per-principal evidence-ownership markers on staged SEC-XBRL evidence.

Covers codex P1 #2250: per-principal OWNERSHIP MARKERS replace the single-owner receipt
STAMP model.  Two workspaces staging the SAME filing each get their own marker file, so
dedup collision is impossible.

Test matrix
-----------
1. none happy-path: stage (writes constant-workspace marker) → open → 200.
2. proxy same-workspace: stage as W1 (marker for W1) → open as W1 → 200.
3. proxy cross-workspace: stage as W1 → open as W2 (no W2 marker) → 403
   marker_missing; assert 0 workflow rows persisted (rollback).
4. P1 regression — same content two workspaces: W1 stages content X (marker W1/X)
   → W2 stages same content X (marker W2/X) → BOTH W1 and W2 open → 200 each.
5. legacy no marker under none → 200.
6. legacy no marker under proxy → 403 marker_missing.
7. marker cannot be forged: caller with marker for sidecar A cannot open sidecar B
   (no B marker) → 403.
8. record_sec_xbrl_evidence_ownership_marker idempotency — second write with same
   owner is a no-op; different owner raises conflict.
9. derive_sec_xbrl_evidence_owner under none returns same hashes as
   authorize_sec_xbrl_route (stamp == match equality).
10. sidecar receipt_hash is NOT affected by the absence of evidence_owner fields
    (sidecar no longer accepts those fields).
11. classification receipt_hash basis does NOT include evidence_owner fields.
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
    layer3_sec_xbrl_in_app_auth_policy as auth_policy,
    layer3_sec_xbrl_auth_binding as auth_binding,
)
from app.services.layer3_utils import stable_hash

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPEN_FROM_STAGED = "/api/v1/layer3/sec-xbrl/operator-review/workflow/open-from-staged-evidence"

_PROXY_IDENTITY_HEADER = "x-forwarded-user"
_PROXY_GROUPS_HEADER = "x-forwarded-groups"

_W1_USER = "operator-alice@workspace-one.example"
_W1_GROUP = "workspace-one"
_W2_USER = "operator-bob@workspace-two.example"
_W2_GROUP = "workspace-two"


# ---------------------------------------------------------------------------
# Storage staging helpers
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


def _stage_storage(storage: Path, *, sidecar_hash: str | None = None) -> dict[str, str]:
    """Write minimal offline-evidence storage. Returns disambiguation hashes.

    sidecar_hash allows caller to control which content is staged (for P1 regression test).
    """
    if sidecar_hash is None:
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


def _write_marker(storage: Path, *, owner_ref_hash: str, workspace_ref_hash: str, sidecar_receipt_hash: str) -> None:
    """Directly write an ownership marker (simulates what corpus-validation does at staging)."""
    auth_binding.record_sec_xbrl_evidence_ownership_marker(
        str(storage),
        owner_ref_hash=owner_ref_hash,
        workspace_ref_hash=workspace_ref_hash,
        sidecar_receipt_hash=sidecar_receipt_hash,
    )


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


def _derive_owner(headers: dict[str, str]) -> dict[str, str]:
    result = auth_policy.derive_sec_xbrl_evidence_owner(headers)
    return {
        "owner_ref_hash": result["owner_ref_hash"],
        "workspace_ref_hash": result["workspace_ref_hash"],
    }


def _w1_headers() -> dict[str, str]:
    return {_PROXY_IDENTITY_HEADER: _W1_USER, _PROXY_GROUPS_HEADER: _W1_GROUP}


def _w2_headers() -> dict[str, str]:
    return {_PROXY_IDENTITY_HEADER: _W2_USER, _PROXY_GROUPS_HEADER: _W2_GROUP}


# ---------------------------------------------------------------------------
# Test 1: none happy-path — stage + open → 200
# ---------------------------------------------------------------------------

def test_none_mode_happy_path_opens_workflow(tmp_path, monkeypatch) -> None:
    """AUTH_OWNER=none: write constant-workspace marker → open → 200."""
    storage_dir = tmp_path / "storage-none"
    client, _ = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="none")
    try:
        refs = _stage_storage(storage_dir)
        # Derive the constant owner for none-mode and write its marker
        none_owner = _derive_owner({})
        _write_marker(storage_dir, sidecar_receipt_hash=refs["sidecar_receipt_hash"], **none_owner)

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
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 2: proxy same-workspace open succeeds
# ---------------------------------------------------------------------------

def test_proxy_same_workspace_open_succeeds(tmp_path, monkeypatch) -> None:
    """AUTH_OWNER=proxy: staged with W1 marker, opened as W1 → 200."""
    storage_dir = tmp_path / "storage-proxy-w1"
    client, _ = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="proxy")
    try:
        refs = _stage_storage(storage_dir)
        w1_owner = _derive_owner(_w1_headers())
        _write_marker(storage_dir, sidecar_receipt_hash=refs["sidecar_receipt_hash"], **w1_owner)

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
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 3: proxy cross-workspace open fails closed with 403
# ---------------------------------------------------------------------------

def test_proxy_cross_workspace_open_fails_closed(tmp_path, monkeypatch) -> None:
    """AUTH_OWNER=proxy: W1 has marker, W2 does not → 403 marker_missing; no workflow row."""
    from sqlalchemy import text
    storage_dir = tmp_path / "storage-cross"
    client, SessionLocal = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="proxy")
    try:
        refs = _stage_storage(storage_dir)
        # Only write marker for W1
        w1_owner = _derive_owner(_w1_headers())
        _write_marker(storage_dir, sidecar_receipt_hash=refs["sidecar_receipt_hash"], **w1_owner)

        with SessionLocal() as db:
            pre_count = db.execute(text("SELECT COUNT(*) FROM l3_sec_xbrl_operator_review_workflow")).scalar()

        resp = client.post(
            OPEN_FROM_STAGED,
            headers=_w2_headers(),  # W2 has no marker
            json={
                "client_request_id": f"test-cross-w-{uuid.uuid4().hex[:12]}",
                "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
                "expected_statement_classification_receipt_hash": refs["classification_hash"],
                "period_limit": 3,
            },
        )
        assert resp.status_code == 403, resp.text
        body = resp.json()
        assert "marker_missing" in body.get("error_code", ""), body

        # Rollback guarantee: no workflow row persisted
        with SessionLocal() as db:
            post_count = db.execute(text("SELECT COUNT(*) FROM l3_sec_xbrl_operator_review_workflow")).scalar()
        assert post_count == pre_count, (
            f"Workflow row was persisted despite 403 rejection (pre={pre_count}, post={post_count})"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 4: P1 regression — same content two workspaces, both can open
# ---------------------------------------------------------------------------

def test_p1_same_content_two_workspaces_both_open(tmp_path, monkeypatch) -> None:
    """P1 regression: W1 and W2 independently own the SAME staged content. Both open.

    The root P1 failure was the single-owner receipt STAMP: W2 hits 403 because the
    deduped receipt shows W1's stamp — W2's open is rejected before any projection work.

    With per-principal markers:
    - Each workspace writes its own marker file (keyed by workspace_ref_hash).
    - No dedup collision: same sidecar_receipt_hash, different marker files.
    - Both workspaces are authorized and open successfully.

    Isolation: each workspace gets its own in-memory SQLite DB (as happens in practice
    across separate operator instances).  Each uses its own distinct client_request_id.
    """
    from sqlalchemy import create_engine as _create_engine
    from sqlalchemy.orm import sessionmaker as _sessionmaker

    storage_dir = tmp_path / "storage-p1"

    # Patch proxy settings first so _derive_owner produces the correct proxy-mode hashes
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "ext"))
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", _PROXY_IDENTITY_HEADER)
    monkeypatch.setattr(settings, "proxy_groups_header", _PROXY_GROUPS_HEADER)
    bootstrap_storage_tree(storage_dir)

    # Write the shared sidecar content once to the shared storage filesystem
    shared_sidecar_hash = _hash("b")
    refs = _stage_storage(storage_dir, sidecar_hash=shared_sidecar_hash)

    # Now settings.auth_owner == "proxy" so _derive_owner returns proxy-mode hashes
    w1_owner = _derive_owner(_w1_headers())
    w2_owner = _derive_owner(_w2_headers())

    # Both workspaces write their own marker (no collision — separate files)
    _write_marker(storage_dir, sidecar_receipt_hash=refs["sidecar_receipt_hash"], **w1_owner)
    _write_marker(storage_dir, sidecar_receipt_hash=refs["sidecar_receipt_hash"], **w2_owner)

    def _fresh_client():
        """Returns a TestClient backed by a fresh in-memory DB (settings already patched)."""
        engine = _create_engine(
            "sqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        Session = _sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

        def _override():
            db = Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override
        return TestClient(app, raise_server_exceptions=True)

    try:
        # W1 opens in its own DB context
        client1 = _fresh_client()
        resp1 = client1.post(
            OPEN_FROM_STAGED,
            headers=_w1_headers(),
            json={
                "client_request_id": f"test-p1-w1-{uuid.uuid4().hex[:12]}",
                "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
                "expected_statement_classification_receipt_hash": refs["classification_hash"],
                "period_limit": 3,
            },
        )
        assert resp1.status_code == 200, resp1.text
        assert resp1.json()["status"] == "review_ready"

        # W2 opens in its own separate DB context — same shared storage filesystem,
        # independent in-memory DB so no projection dedup collision.
        # In the old stamp model W2 would 403 at authz (never reached DB).
        # In the new marker model W2's marker is found → 200.
        client2 = _fresh_client()
        resp2 = client2.post(
            OPEN_FROM_STAGED,
            headers=_w2_headers(),
            json={
                "client_request_id": f"test-p1-w2-{uuid.uuid4().hex[:12]}",
                "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
                "expected_statement_classification_receipt_hash": refs["classification_hash"],
                "period_limit": 3,
            },
        )
        assert resp2.status_code == 200, resp2.text
        assert resp2.json()["status"] == "review_ready"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test P2: proxy same-workspace different actor — both open + re-stage is no-op
# ---------------------------------------------------------------------------

def test_proxy_same_workspace_different_actor_both_open(tmp_path, monkeypatch) -> None:
    """P2 (codex #2252): two actors in the SAME workspace staging the same filing must not conflict.

    Actor A1 (workspace W, owner_A1) stages content X → marker W/X written.
    Actor A2 (workspace W, owner_A2, same workspace headers / different identity header)
      - opens X → 200 (workspace match; intra-workspace sharing)
      - re-stages X (record_ call) → no-op success (no 409 owner_conflict)

    Cross-workspace isolation (W1 vs W2) remains enforced by Test 3.
    """
    storage_dir = tmp_path / "storage-p2-intra-ws"

    # Both actors share the same workspace group header but differ in identity header.
    # Use W1_GROUP for both so the server derives the same workspace_ref_hash.
    _A1_USER = "operator-alice@workspace-one.example"
    _A2_USER = "operator-carol@workspace-one.example"  # same org, different person
    _SHARED_GROUP = _W1_GROUP

    def _a1_headers() -> dict[str, str]:
        return {_PROXY_IDENTITY_HEADER: _A1_USER, _PROXY_GROUPS_HEADER: _SHARED_GROUP}

    def _a2_headers() -> dict[str, str]:
        return {_PROXY_IDENTITY_HEADER: _A2_USER, _PROXY_GROUPS_HEADER: _SHARED_GROUP}

    # Patch proxy settings
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_external_local_export_dir", str(tmp_path / "ext"))
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)
    monkeypatch.setattr(settings, "proxy_identity_header", _PROXY_IDENTITY_HEADER)
    monkeypatch.setattr(settings, "proxy_groups_header", _PROXY_GROUPS_HEADER)
    bootstrap_storage_tree(storage_dir)

    refs = _stage_storage(storage_dir)
    sidecar_hash = refs["sidecar_receipt_hash"]

    # Derive owner hashes for both actors — workspace_ref_hash must be the same
    a1_owner = _derive_owner(_a1_headers())
    a2_owner = _derive_owner(_a2_headers())
    assert a1_owner["workspace_ref_hash"] == a2_owner["workspace_ref_hash"], (
        "Both actors must share the same workspace_ref_hash for this test to be valid"
    )
    assert a1_owner["owner_ref_hash"] != a2_owner["owner_ref_hash"], (
        "Actors must have distinct owner_ref_hash values for this test to be meaningful"
    )

    # A1 stages content → writes marker W/X
    _write_marker(storage_dir, sidecar_receipt_hash=sidecar_hash, **a1_owner)

    # A2 re-stages same content in same workspace → must be a no-op (no 409)
    auth_binding.record_sec_xbrl_evidence_ownership_marker(
        str(storage_dir),
        owner_ref_hash=a2_owner["owner_ref_hash"],
        workspace_ref_hash=a2_owner["workspace_ref_hash"],
        sidecar_receipt_hash=sidecar_hash,
    )

    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm

    def _fresh_client_for(actor_headers: dict[str, str]):
        engine = _ce(
            "sqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        Session = _sm(bind=engine, autocommit=False, autoflush=False, future=True)

        def _override():
            db = Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override
        return TestClient(app, raise_server_exceptions=True)

    try:
        # A2 opens X → must return 200 (workspace match, owner not compared)
        client_a2 = _fresh_client_for(_a2_headers())
        resp_a2 = client_a2.post(
            OPEN_FROM_STAGED,
            headers=_a2_headers(),
            json={
                "client_request_id": f"test-p2-a2-open-{uuid.uuid4().hex[:12]}",
                "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
                "expected_statement_classification_receipt_hash": refs["classification_hash"],
                "period_limit": 3,
            },
        )
        assert resp_a2.status_code == 200, (
            f"A2 (same workspace, different actor) should open successfully: {resp_a2.text}"
        )
        assert resp_a2.json()["status"] == "review_ready"
        assert resp_a2.json()["production_readiness_claimed"] is False

        # A1 can also open (baseline: original staging actor still works)
        client_a1 = _fresh_client_for(_a1_headers())
        resp_a1 = client_a1.post(
            OPEN_FROM_STAGED,
            headers=_a1_headers(),
            json={
                "client_request_id": f"test-p2-a1-open-{uuid.uuid4().hex[:12]}",
                "expected_sidecar_receipt_hash": refs["sidecar_receipt_hash"],
                "expected_statement_classification_receipt_hash": refs["classification_hash"],
                "period_limit": 3,
            },
        )
        assert resp_a1.status_code == 200, (
            f"A1 (original staging actor) should still open successfully: {resp_a1.text}"
        )
        assert resp_a1.json()["status"] == "review_ready"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 5: legacy no marker under none → 200
# ---------------------------------------------------------------------------

def test_legacy_no_marker_under_none_opens(tmp_path, monkeypatch) -> None:
    """No ownership marker under AUTH_OWNER=none → 200 (backward-compat)."""
    storage_dir = tmp_path / "storage-legacy-none"
    client, _ = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="none")
    try:
        refs = _stage_storage(storage_dir)
        # NO marker written

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
        assert resp.json()["status"] == "review_ready"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 6: legacy no marker under proxy → 403
# ---------------------------------------------------------------------------

def test_legacy_no_marker_under_proxy_fails(tmp_path, monkeypatch) -> None:
    """No ownership marker under AUTH_OWNER=proxy → 403 marker_missing."""
    storage_dir = tmp_path / "storage-legacy-proxy"
    client, _ = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="proxy")
    try:
        refs = _stage_storage(storage_dir)
        # NO marker written

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
        assert "marker_missing" in body.get("error_code", ""), body
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 7: marker forgery — caller with marker for sidecar A cannot open sidecar B
# ---------------------------------------------------------------------------

def test_marker_cannot_be_forged_for_different_sidecar(tmp_path, monkeypatch) -> None:
    """Caller has marker for sidecar A; tries to open sidecar B → 403 marker_missing."""
    storage_dir = tmp_path / "storage-forgery"
    client, _ = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="proxy")
    try:
        # Stage sidecar B (content we will try to open)
        sidecar_b_hash = _hash("b")
        refs_b = _stage_storage(storage_dir, sidecar_hash=sidecar_b_hash)

        # Write marker for sidecar A (different hash) — not for sidecar B
        sidecar_a_hash = _hash("a")
        w1_owner = _derive_owner(_w1_headers())
        _write_marker(storage_dir, sidecar_receipt_hash=sidecar_a_hash, **w1_owner)

        # Attempt to open sidecar B — no marker for B → 403
        resp = client.post(
            OPEN_FROM_STAGED,
            headers=_w1_headers(),
            json={
                "client_request_id": f"test-forgery-{uuid.uuid4().hex[:12]}",
                "expected_sidecar_receipt_hash": refs_b["sidecar_receipt_hash"],
                "expected_statement_classification_receipt_hash": refs_b["classification_hash"],
                "period_limit": 3,
            },
        )
        assert resp.status_code == 403, resp.text
        body = resp.json()
        assert "marker_missing" in body.get("error_code", ""), body
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Test 8: record_sec_xbrl_evidence_ownership_marker idempotency + conflict
# ---------------------------------------------------------------------------

def test_ownership_marker_idempotent(tmp_path) -> None:
    """Second write with same owner_ref_hash is a no-op (no error)."""
    storage = tmp_path / "storage-idem"
    storage.mkdir(parents=True, exist_ok=True)
    owner = _hash("a")
    workspace = _hash("b")
    sidecar = _hash("c")

    auth_binding.record_sec_xbrl_evidence_ownership_marker(
        str(storage), owner_ref_hash=owner, workspace_ref_hash=workspace,
        sidecar_receipt_hash=sidecar,
    )
    # Second call — same owner — must not raise
    auth_binding.record_sec_xbrl_evidence_ownership_marker(
        str(storage), owner_ref_hash=owner, workspace_ref_hash=workspace,
        sidecar_receipt_hash=sidecar,
    )


def test_ownership_marker_idempotent_different_actor_same_workspace(tmp_path) -> None:
    """Workspace-level idempotency: second write with DIFFERENT owner is a no-op (no conflict).

    Intra-workspace teammates (actor A1 then actor A2 re-staging the same content) must
    not produce a 409.  The first-staging actor's owner_ref_hash is preserved as audit
    metadata; subsequent calls for the same (workspace, sidecar) are silent no-ops.
    """
    storage = tmp_path / "storage-idem-diff-actor"
    storage.mkdir(parents=True, exist_ok=True)
    workspace = _hash("b")
    sidecar = _hash("c")
    owner_a1 = _hash("a")
    owner_a2 = _hash("d")

    auth_binding.record_sec_xbrl_evidence_ownership_marker(
        str(storage), owner_ref_hash=owner_a1, workspace_ref_hash=workspace,
        sidecar_receipt_hash=sidecar,
    )
    # A2 re-stages same content in same workspace — must be a no-op, not a 409
    auth_binding.record_sec_xbrl_evidence_ownership_marker(
        str(storage), owner_ref_hash=owner_a2, workspace_ref_hash=workspace,
        sidecar_receipt_hash=sidecar,
    )
    # First-actor's owner_ref_hash is preserved as audit metadata
    marker_path = (
        storage
        / auth_binding.OWNERSHIP_MARKER_DIR
        / workspace
        / f"sidecar-{sidecar}.json"
    )
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert marker["owner_ref_hash"] == owner_a1, "First-actor owner must be preserved as audit metadata"


def test_ownership_marker_skipped_when_hashes_empty(tmp_path) -> None:
    """Empty owner_ref_hash or workspace_ref_hash → silent skip (no file written)."""
    storage = tmp_path / "storage-skip"
    storage.mkdir(parents=True, exist_ok=True)
    sidecar = _hash("c")

    auth_binding.record_sec_xbrl_evidence_ownership_marker(
        str(storage), owner_ref_hash="", workspace_ref_hash=_hash("b"),
        sidecar_receipt_hash=sidecar,
    )
    auth_binding.record_sec_xbrl_evidence_ownership_marker(
        str(storage), owner_ref_hash=_hash("a"), workspace_ref_hash="",
        sidecar_receipt_hash=sidecar,
    )
    # No marker directory should exist
    marker_root = storage / auth_binding.OWNERSHIP_MARKER_DIR
    assert not marker_root.exists() or not any(marker_root.rglob("*.json"))


def test_ownership_marker_rejects_invalid_sidecar_hash(tmp_path) -> None:
    """Non-hex sidecar_receipt_hash → SecXbrlAuthBindingError 400."""
    storage = tmp_path / "storage-invalid"
    storage.mkdir(parents=True, exist_ok=True)
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as exc_info:
        auth_binding.record_sec_xbrl_evidence_ownership_marker(
            str(storage), owner_ref_hash=_hash("a"), workspace_ref_hash=_hash("b"),
            sidecar_receipt_hash="not-a-valid-hash",
        )
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# Test 9: derive_sec_xbrl_evidence_owner matches authorize_sec_xbrl_route derivation
# ---------------------------------------------------------------------------

def test_derive_evidence_owner_equals_authorize_route_derivation(monkeypatch) -> None:
    """derive_sec_xbrl_evidence_owner under none returns same hashes as authorize_sec_xbrl_route."""
    monkeypatch.setattr(settings, "auth_owner", "none")

    owner_result = auth_policy.derive_sec_xbrl_evidence_owner({})
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
# Test 10: sidecar no longer accepts evidence_owner_ref_hash in request body
# ---------------------------------------------------------------------------

def test_sidecar_rejects_evidence_owner_fields_in_request() -> None:
    """Sidecar _ALLOWED_FIELDS no longer includes evidence_owner_ref_hash/evidence_workspace_ref_hash."""
    from app.services.layer3_sec_xbrl_sidecar import _ALLOWED_FIELDS, _FORBIDDEN_INPUT_KEYS
    assert "evidence_owner_ref_hash" not in _ALLOWED_FIELDS, (
        "evidence_owner_ref_hash must not be in sidecar _ALLOWED_FIELDS after marker migration"
    )
    assert "evidence_workspace_ref_hash" not in _ALLOWED_FIELDS, (
        "evidence_workspace_ref_hash must not be in sidecar _ALLOWED_FIELDS after marker migration"
    )
    # Confirm they're also not in forbidden (they simply don't exist in this layer anymore)
    assert "evidence_owner_ref_hash" not in _FORBIDDEN_INPUT_KEYS
    assert "evidence_workspace_ref_hash" not in _FORBIDDEN_INPUT_KEYS


# ---------------------------------------------------------------------------
# Test 11: classification receipt_hash basis does NOT include evidence_owner fields
# ---------------------------------------------------------------------------

def test_classification_receipt_hash_basis_excludes_owner_fields() -> None:
    """classification_receipt_hash_basis does not include evidence_owner fields."""
    basis_keys = classification_contract.CLASSIFICATION_RECEIPT_HASH_BASIS_KEYS
    assert "evidence_owner_ref_hash" not in basis_keys
    assert "evidence_workspace_ref_hash" not in basis_keys
    assert "evidence_owner" not in basis_keys

    from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification import (
        _ALLOWED_FIELDS as clf_allowed,
    )
    assert "evidence_owner_ref_hash" not in clf_allowed
    assert "evidence_workspace_ref_hash" not in clf_allowed


# ---------------------------------------------------------------------------
# Test: require_sec_xbrl_evidence_ownership_marker unit tests
# ---------------------------------------------------------------------------

def test_require_marker_none_mode_no_marker_passes(tmp_path) -> None:
    """none-mode: no marker file → no error (legacy backward-compat)."""
    storage = tmp_path / "storage-req-none"
    storage.mkdir(parents=True, exist_ok=True)
    policy = {
        "actor_ref_hash": _hash("a"),
        "workspace_ref_hash": _hash("b"),
        "auth_owner_mode": "AUTH_OWNER_none_single_operator_dev_profile",
    }
    # No marker written — should not raise under none
    auth_binding.require_sec_xbrl_evidence_ownership_marker(
        str(storage),
        policy_decision=policy,
        auth_owner_mode="AUTH_OWNER_none_single_operator_dev_profile",
        sidecar_receipt_hash=_hash("c"),
    )


def test_require_marker_proxy_no_marker_raises(tmp_path) -> None:
    """proxy-mode: no marker → SecXbrlAuthBindingError 403 marker_missing."""
    storage = tmp_path / "storage-req-proxy-nomrk"
    storage.mkdir(parents=True, exist_ok=True)
    policy = {
        "actor_ref_hash": _hash("a"),
        "workspace_ref_hash": _hash("b"),
        "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    }
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as exc_info:
        auth_binding.require_sec_xbrl_evidence_ownership_marker(
            str(storage),
            policy_decision=policy,
            auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
            sidecar_receipt_hash=_hash("c"),
        )
    assert exc_info.value.http_status == 403
    assert "marker_missing" in exc_info.value.code


def test_require_marker_workspace_match_passes(tmp_path) -> None:
    """Marker exists for caller's workspace+sidecar → no error (workspace-level check)."""
    storage = tmp_path / "storage-req-match"
    storage.mkdir(parents=True, exist_ok=True)
    owner = _hash("a")
    workspace = _hash("b")
    sidecar = _hash("c")

    auth_binding.record_sec_xbrl_evidence_ownership_marker(
        str(storage), owner_ref_hash=owner, workspace_ref_hash=workspace,
        sidecar_receipt_hash=sidecar,
    )
    # Same workspace, same sidecar — authorized regardless of actor_ref_hash
    policy = {
        "actor_ref_hash": owner,
        "workspace_ref_hash": workspace,
        "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    }
    auth_binding.require_sec_xbrl_evidence_ownership_marker(
        str(storage),
        policy_decision=policy,
        auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
        sidecar_receipt_hash=sidecar,
    )


def test_require_marker_same_workspace_different_actor_passes(tmp_path) -> None:
    """Workspace-level open: marker written by actor A1, opened by actor A2 (same workspace) → no error.

    This is the intra-workspace sharing case: the tenant boundary is the workspace, not the actor.
    Cross-workspace isolation is still enforced (different workspace_ref_hash → no marker found).
    """
    storage = tmp_path / "storage-req-intra-ws"
    storage.mkdir(parents=True, exist_ok=True)
    owner_a1 = _hash("a")
    owner_a2 = _hash("d")
    workspace = _hash("b")
    sidecar = _hash("c")

    # A1 stages content → writes marker under workspace/sidecar
    auth_binding.record_sec_xbrl_evidence_ownership_marker(
        str(storage), owner_ref_hash=owner_a1, workspace_ref_hash=workspace,
        sidecar_receipt_hash=sidecar,
    )
    # A2 (different actor, SAME workspace) opens → must succeed (no owner comparison)
    policy_a2 = {
        "actor_ref_hash": owner_a2,
        "workspace_ref_hash": workspace,
        "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    }
    auth_binding.require_sec_xbrl_evidence_ownership_marker(
        str(storage),
        policy_decision=policy_a2,
        auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
        sidecar_receipt_hash=sidecar,
    )


def test_require_marker_invalid_sidecar_hash_raises(tmp_path) -> None:
    """Invalid sidecar_receipt_hash (not 64-hex) → 400."""
    storage = tmp_path / "storage-req-invalid"
    storage.mkdir(parents=True, exist_ok=True)
    policy = {
        "actor_ref_hash": _hash("a"),
        "workspace_ref_hash": _hash("b"),
        "auth_owner_mode": "AUTH_OWNER_none_single_operator_dev_profile",
    }
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as exc_info:
        auth_binding.require_sec_xbrl_evidence_ownership_marker(
            str(storage),
            policy_decision=policy,
            auth_owner_mode="AUTH_OWNER_none_single_operator_dev_profile",
            sidecar_receipt_hash="../traversal/attempt",
        )
    assert exc_info.value.http_status == 400


# ---------------------------------------------------------------------------
# L1: caller_workspace traversal guard in require_
# ---------------------------------------------------------------------------

def test_require_marker_traversal_workspace_hash_raises(tmp_path) -> None:
    """L1: A traversal string in policy_decision['workspace_ref_hash'] → 403/400 before path use."""
    storage = tmp_path / "storage-traversal"
    storage.mkdir(parents=True, exist_ok=True)
    # Use a proxy-mode token so the workspace hash is actually used in path construction.
    policy = {
        "actor_ref_hash": _hash("a"),
        "workspace_ref_hash": "../../../etc/passwd",
        "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    }
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as exc_info:
        auth_binding.require_sec_xbrl_evidence_ownership_marker(
            str(storage),
            policy_decision=policy,
            auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
            sidecar_receipt_hash=_hash("c"),
        )
    # Must raise before any path construction; http_status 400 or 403 both acceptable.
    assert exc_info.value.http_status in {400, 403}
    assert "workspace_hash_invalid" in exc_info.value.code


# ---------------------------------------------------------------------------
# L2: proxy-mode token is NOT treated as none (exact token match)
# ---------------------------------------------------------------------------

def test_proxy_mode_token_is_not_treated_as_none(tmp_path) -> None:
    """L2: A proxy-mode auth_owner_mode token must NOT enable the allow-without-marker path.

    Previously, 'none' in str(token).lower() would match any token containing the
    substring 'none' (e.g. a hypothetical 'AUTH_OWNER_proxy_none_stub_profile').
    With exact-match semantics, only AUTH_OWNER_MODE_NONE bypasses the marker check.
    """
    storage = tmp_path / "storage-l2"
    storage.mkdir(parents=True, exist_ok=True)
    # A proxy-mode token — no marker written
    proxy_token = "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true"
    policy = {
        "actor_ref_hash": _hash("a"),
        "workspace_ref_hash": _hash("b"),
        "auth_owner_mode": proxy_token,
    }
    with pytest.raises(auth_binding.SecXbrlAuthBindingError) as exc_info:
        auth_binding.require_sec_xbrl_evidence_ownership_marker(
            str(storage),
            policy_decision=policy,
            auth_owner_mode=proxy_token,
            sidecar_receipt_hash=_hash("c"),
        )
    assert exc_info.value.http_status == 403
    assert "marker_missing" in exc_info.value.code


# ---------------------------------------------------------------------------
# M1: malicious body carrying victim owner fields must not reach the marker
# ---------------------------------------------------------------------------

def test_m1_malicious_body_owner_fields_rejected_or_ignored(tmp_path, monkeypatch) -> None:
    """M1: Body carrying evidence_owner_ref_hash / evidence_workspace_ref_hash is rejected
    at ALLOWED_FIELDS validation (governed 400) or at minimum the written marker is under
    the SERVER-derived (W1) workspace, not the body-supplied victim (W2) workspace.

    With the M1 fix, evidence_owner_ref_hash and evidence_workspace_ref_hash are removed
    from ALLOWED_FIELDS, so any body containing them produces a 400 unknown_field error.
    This test asserts the 400 path — the victim marker dir must never be created.
    """
    from app.services.layer3_sec_edgar_real_company_corpus_validation import ALLOWED_FIELDS

    # Confirm the fields were removed from ALLOWED_FIELDS (structural assertion)
    assert "evidence_owner_ref_hash" not in ALLOWED_FIELDS, (
        "evidence_owner_ref_hash must be removed from corpus-validation ALLOWED_FIELDS (M1)"
    )
    assert "evidence_workspace_ref_hash" not in ALLOWED_FIELDS, (
        "evidence_workspace_ref_hash must be removed from corpus-validation ALLOWED_FIELDS (M1)"
    )
    assert "auth_owner_mode" not in ALLOWED_FIELDS, (
        "auth_owner_mode must be removed from corpus-validation ALLOWED_FIELDS (M1)"
    )

    # Drive the route with proxy-mode W1 headers + a malicious body carrying W2 victim hashes.
    storage_dir = tmp_path / "storage-m1"
    client, _ = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="proxy")
    try:
        # Derive W2 victim owner hashes (what the attacker tries to plant)
        w2_owner = _derive_owner(_w2_headers())

        resp = client.post(
            "/api/v1/layer3/source/sec-edgar/real-company-corpus/validation",
            headers=_w1_headers(),
            json={
                "client_request_id": f"m1-malicious-body-{uuid.uuid4().hex[:12]}",
                "validation_mode": "sec_edgar_real_company_corpus_validation_v1",
                "operator_decision": "validate_sec_edgar_real_company_corpus_product_path",
                "operator_confirmation": True,
                # Malicious fields: attacker tries to plant W2 victim owner info
                "evidence_owner_ref_hash": w2_owner["owner_ref_hash"],
                "evidence_workspace_ref_hash": w2_owner["workspace_ref_hash"],
                "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
            },
        )
        # With M1: body fields rejected at ALLOWED_FIELDS → 400 unknown_field.
        # The victim (W2) marker dir must NOT exist.
        assert resp.status_code == 400, (
            f"Expected 400 for body with removed owner fields, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert "unknown_field" in body.get("error_code", ""), body

        # Confirm victim workspace marker dir was never created
        victim_marker_dir = (
            storage_dir
            / auth_binding.OWNERSHIP_MARKER_DIR
            / w2_owner["workspace_ref_hash"]
        )
        assert not victim_marker_dir.exists(), (
            f"Victim marker dir was created despite body rejection: {victim_marker_dir}"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# M2: end-to-end corpus-validation marker-write + open-from-staged-evidence
# ---------------------------------------------------------------------------

def test_m2_corpus_validation_writes_marker_at_w1_workspace(tmp_path, monkeypatch) -> None:
    """M2-part-A: POSTing the corpus-validation route (proxy mode, W1 headers) writes
    ownership markers at W1's workspace dir with W1's owner_ref_hash for each produced
    sidecar_receipt_hash. W2's marker dir is untouched (no cross-workspace pollution).

    Uses _enable_sec_edgar_arelle_sidecar_for_corpus_validation + _FakeSecEdgarClient
    from test_layer3_api.py (same harness as test_layer3_api_runs_sec_edgar_default_on_arelle_product_path_through_archive).
    """
    import sys

    test_api_path = str(Path(__file__).resolve().parent)
    if test_api_path not in sys.path:
        sys.path.insert(0, test_api_path)

    import test_layer3_api as _tapi
    from app.services import layer3_sec_edgar_live_source_artifact

    storage_dir = tmp_path / "storage-m2a"
    monkeypatch.setattr(settings, "layer3_sec_edgar_live_network_enabled", True)
    client, _ = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="proxy")

    try:
        _tapi._enable_sec_edgar_arelle_sidecar_for_corpus_validation(tmp_path, monkeypatch)
        monkeypatch.setattr(settings, "layer3_sec_edgar_user_agent", "Layer3 Test contact@example.com")
        monkeypatch.setattr(layer3_sec_edgar_live_source_artifact, "SEC_EDGAR_SLEEP", lambda _seconds: None)
        monkeypatch.setattr(layer3_sec_edgar_live_source_artifact, "_enforce_rate_limit", lambda: None)
        fake_client = _tapi._FakeSecEdgarClient(_tapi._real_company_validation_fake_results())
        monkeypatch.setattr(layer3_sec_edgar_live_source_artifact, "SEC_EDGAR_CLIENT", fake_client)

        # POST corpus-validation as W1 — route must write ownership markers
        validation_resp = client.post(
            "/api/v1/layer3/source/sec-edgar/real-company-corpus/validation",
            headers=_w1_headers(),
            json={
                "client_request_id": f"m2a-corpus-val-{uuid.uuid4().hex[:12]}",
                "validation_mode": "sec_edgar_real_company_corpus_validation_v1",
                "operator_decision": "validate_sec_edgar_real_company_corpus_product_path",
                "company_matrix": ["MSFT", "STLD", "SONY", "CCJ"],
                "operator_confirmation": True,
            },
        )
        assert validation_resp.status_code == 200, validation_resp.text
        validation = validation_resp.json()
        assert validation["validation_state"] == "sec_edgar_real_company_corpus_validation_ready"

        # Every supported record must have an arelle sidecar receipt hash
        sidecar_hashes = [
            record["authority_hashes"]["arelle_sidecar_receipt_hash"]
            for record in validation["filing_validation_records"]
            if "arelle_sidecar_receipt_hash" in record.get("authority_hashes", {})
        ]
        assert sidecar_hashes, "No arelle sidecar receipt hashes in validation records"

        # Derive W1 owner (same derivation the route uses)
        w1_owner = _derive_owner(_w1_headers())
        marker_root = storage_dir / auth_binding.OWNERSHIP_MARKER_DIR / w1_owner["workspace_ref_hash"]

        # Each sidecar must have a marker at W1's workspace dir with W1's owner_ref_hash
        for sidecar_hash in sidecar_hashes:
            marker_path = marker_root / f"sidecar-{sidecar_hash}.json"
            assert marker_path.exists(), (
                f"Marker not written at W1 workspace path for sidecar {sidecar_hash[:16]}..."
            )
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            assert marker["owner_ref_hash"] == w1_owner["owner_ref_hash"], (
                f"Marker owner_ref_hash mismatch for sidecar {sidecar_hash[:16]}..."
            )
            assert marker["workspace_ref_hash"] == w1_owner["workspace_ref_hash"], (
                f"Marker workspace_ref_hash mismatch for sidecar {sidecar_hash[:16]}..."
            )

        # W2's marker dir must not exist — no cross-workspace pollution
        w2_owner = _derive_owner(_w2_headers())
        w2_marker_dir = storage_dir / auth_binding.OWNERSHIP_MARKER_DIR / w2_owner["workspace_ref_hash"]
        assert not w2_marker_dir.exists(), "W2 marker dir must not exist after W1-only corpus validation"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_m2_marker_written_by_corpus_validation_enables_open_from_staged(tmp_path, monkeypatch) -> None:
    """M2-part-B: A marker written for a sidecar (simulating what corpus-validation produces)
    allows open-from-staged-evidence as W1 → 200.

    This confirms the end-to-end chain: corpus-validation writes marker → open succeeds.
    Uses the same _stage_storage helper as the existing authz tests for the offline evidence,
    then writes the marker via record_sec_xbrl_evidence_ownership_marker (same call the
    corpus-validation service layer makes) and confirms the open route returns 200.
    """
    storage_dir = tmp_path / "storage-m2b"
    client, _ = _make_client(tmp_path, monkeypatch, storage_dir, auth_owner="proxy")
    try:
        refs = _stage_storage(storage_dir)
        sidecar_hash = refs["sidecar_receipt_hash"]
        clf_hash = refs["classification_hash"]

        # Simulate what corpus-validation does: write the W1 ownership marker
        w1_owner = _derive_owner(_w1_headers())
        auth_binding.record_sec_xbrl_evidence_ownership_marker(
            str(storage_dir),
            owner_ref_hash=w1_owner["owner_ref_hash"],
            workspace_ref_hash=w1_owner["workspace_ref_hash"],
            sidecar_receipt_hash=sidecar_hash,
        )

        # Confirm the marker exists at W1's workspace path
        marker_path = (
            storage_dir
            / auth_binding.OWNERSHIP_MARKER_DIR
            / w1_owner["workspace_ref_hash"]
            / f"sidecar-{sidecar_hash}.json"
        )
        assert marker_path.exists(), "Marker not written by record_sec_xbrl_evidence_ownership_marker"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        assert marker["owner_ref_hash"] == w1_owner["owner_ref_hash"]

        # Open the staged evidence as W1 → must return 200
        open_resp = client.post(
            OPEN_FROM_STAGED,
            headers=_w1_headers(),
            json={
                "client_request_id": f"m2b-open-{uuid.uuid4().hex[:12]}",
                "expected_sidecar_receipt_hash": sidecar_hash,
                "expected_statement_classification_receipt_hash": clf_hash,
                "period_limit": 3,
            },
        )
        assert open_resp.status_code == 200, open_resp.text
        body = open_resp.json()
        assert body["status"] == "review_ready"
        assert body["production_readiness_claimed"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# P2 codex #2253: marker read+parse+validate (fail-closed on garbage/directory/mismatch)
# ---------------------------------------------------------------------------

def test_require_marker_malformed_file_fails_closed_under_proxy(tmp_path) -> None:
    """P2 #2253: garbage/truncated (non-JSON) marker file under proxy → 403 invalid."""
    from app.services import layer3_sec_xbrl_auth_binding as ab

    storage = tmp_path / "storage-malformed-proxy"
    storage.mkdir(parents=True, exist_ok=True)
    workspace = _hash("b")
    sidecar = _hash("c")

    # Write a garbage (non-JSON) file at the expected marker path
    marker_dir = storage / ab.OWNERSHIP_MARKER_DIR / workspace
    marker_dir.mkdir(parents=True, exist_ok=True)
    (marker_dir / f"sidecar-{sidecar}.json").write_text("not-json{{garbage", encoding="utf-8")

    policy = {
        "actor_ref_hash": _hash("a"),
        "workspace_ref_hash": workspace,
        "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    }
    with pytest.raises(ab.SecXbrlAuthBindingError) as exc_info:
        ab.require_sec_xbrl_evidence_ownership_marker(
            str(storage),
            policy_decision=policy,
            auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
            sidecar_receipt_hash=sidecar,
        )
    assert exc_info.value.http_status == 403
    assert "marker_invalid" in exc_info.value.code


def test_require_marker_directory_at_path_fails_closed_under_proxy(tmp_path) -> None:
    """P2 #2253: a DIRECTORY at the marker path under proxy → 403 invalid."""
    from app.services import layer3_sec_xbrl_auth_binding as ab

    storage = tmp_path / "storage-dir-proxy"
    storage.mkdir(parents=True, exist_ok=True)
    workspace = _hash("b")
    sidecar = _hash("c")

    # Create a DIRECTORY at the expected marker path (not a regular file)
    marker_dir = storage / ab.OWNERSHIP_MARKER_DIR / workspace
    marker_dir.mkdir(parents=True, exist_ok=True)
    dir_at_marker_path = marker_dir / f"sidecar-{sidecar}.json"
    dir_at_marker_path.mkdir(parents=True, exist_ok=True)

    policy = {
        "actor_ref_hash": _hash("a"),
        "workspace_ref_hash": workspace,
        "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    }
    with pytest.raises(ab.SecXbrlAuthBindingError) as exc_info:
        ab.require_sec_xbrl_evidence_ownership_marker(
            str(storage),
            policy_decision=policy,
            auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
            sidecar_receipt_hash=sidecar,
        )
    assert exc_info.value.http_status == 403
    assert "marker_invalid" in exc_info.value.code


def test_require_marker_wrong_fields_fails_closed_under_proxy(tmp_path) -> None:
    """P2 #2253: parseable marker whose sidecar_receipt_hash doesn't match → proxy → 403 invalid."""
    from app.services import layer3_sec_xbrl_auth_binding as ab

    storage = tmp_path / "storage-wrongfields-proxy"
    storage.mkdir(parents=True, exist_ok=True)
    workspace = _hash("b")
    sidecar = _hash("c")
    wrong_sidecar = _hash("d")  # different sidecar hash in the file content

    # Write a valid-looking marker but with mismatched sidecar_receipt_hash
    marker_dir = storage / ab.OWNERSHIP_MARKER_DIR / workspace
    marker_dir.mkdir(parents=True, exist_ok=True)
    bad_marker = {
        "schema_id": ab.OWNERSHIP_MARKER_SCHEMA_ID,
        "owner_ref_hash": _hash("a"),
        "workspace_ref_hash": workspace,
        "evidence_kind": "sidecar",
        "sidecar_receipt_hash": wrong_sidecar,  # wrong — does not match what we request
    }
    (marker_dir / f"sidecar-{sidecar}.json").write_text(
        json.dumps(bad_marker), encoding="utf-8"
    )

    policy = {
        "actor_ref_hash": _hash("a"),
        "workspace_ref_hash": workspace,
        "auth_owner_mode": "AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
    }
    with pytest.raises(ab.SecXbrlAuthBindingError) as exc_info:
        ab.require_sec_xbrl_evidence_ownership_marker(
            str(storage),
            policy_decision=policy,
            auth_owner_mode="AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true",
            sidecar_receipt_hash=sidecar,
        )
    assert exc_info.value.http_status == 403
    assert "marker_invalid" in exc_info.value.code


def test_require_marker_malformed_under_none_allows(tmp_path) -> None:
    """P2 #2253: malformed marker + none-mode → allowed (legacy/backward-compat).

    Under none-mode, an invalid marker (non-JSON, directory, field-mismatch) is treated
    the same as an absent marker: the default flow/legacy path is not broken.
    """
    from app.services import layer3_sec_xbrl_auth_binding as ab

    storage = tmp_path / "storage-malformed-none"
    storage.mkdir(parents=True, exist_ok=True)
    workspace = _hash("b")
    sidecar = _hash("c")

    # Write garbage at the marker path
    marker_dir = storage / ab.OWNERSHIP_MARKER_DIR / workspace
    marker_dir.mkdir(parents=True, exist_ok=True)
    (marker_dir / f"sidecar-{sidecar}.json").write_text("{{not-json-garbage", encoding="utf-8")

    policy = {
        "actor_ref_hash": _hash("a"),
        "workspace_ref_hash": workspace,
        "auth_owner_mode": ab.AUTH_OWNER_MODE_NONE,
    }
    # Must NOT raise — none-mode treats malformed-as-absent → allow
    ab.require_sec_xbrl_evidence_ownership_marker(
        str(storage),
        policy_decision=policy,
        auth_owner_mode=ab.AUTH_OWNER_MODE_NONE,
        sidecar_receipt_hash=sidecar,
    )
