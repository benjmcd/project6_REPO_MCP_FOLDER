"""Service tests for inspect_redacted_production_admission_status.

Hermetic: in-memory SQLite, tmp_path for storage, monkeypatch for env/settings.
The complex _validate_workflow_row_for_status is mocked so tests focus on
evidence assembly and admission evaluation rather than workflow schema checks
(those are covered by the operator-review-workflow test suite).
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_INIT_MODE", "none")
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.db.session import Base
from app.models.models import (
    L3SecXbrlOperatorReviewDecision,
    L3SecXbrlOperatorReviewWorkflow,
    L3SecXbrlProjectionFact,
    L3SecXbrlProjectionSet,
    L3SecXbrlStatementPacketSet,
    L3SecXbrlValueRevealAuthorityReceipt,
    L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_MODE,
    L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_REDACTION_POLICY,
    L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_STATUS_RECORDED,
    L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
    L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
    L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_STATUS_READY,
    L3_SEC_XBRL_PROJECTION_REDACTION_POLICY,
    L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED,
    L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
    L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY,
    L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY,
)
from app.services.layer3_sec_xbrl_admission_status import (
    ADMISSION_STATUS_SCHEMA_ID,
    inspect_redacted_production_admission_status,
)
from app.services.layer3_sec_edgar_real_company_corpus_validation import (
    READY_STATE as CORPUS_READY_STATE,
    RECEIPT_DIR,
    RECEIPT_PREFIX,
)
from app.services.layer3_sec_xbrl_auth_binding import AUTH_OWNER_MODE_NONE
from app.services.layer3_utils import stable_hash


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SIDECAR_HASH = "a" * 64
_WORKFLOW_BASIS_HASH = stable_hash({"test": "workflow-basis"})
_PACKET_BASIS_HASH = stable_hash({"test": "packet-basis"})
_PROJECTION_BASIS_HASH = stable_hash({"test": "projection-basis"})
_VALUE_STORE_HASH = stable_hash({"test": "value-store"})
_SOURCE_REPORT_HASH = stable_hash({"test": "source-report"})

_NONE_POLICY = {"workspace_ref_hash": "0" * 64}
_NONE_AUTH_MODE = AUTH_OWNER_MODE_NONE


# ---------------------------------------------------------------------------
# In-memory DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


def _build_projection_set(db, *, sidecar_hash: str = _SIDECAR_HASH) -> L3SecXbrlProjectionSet:
    proj = L3SecXbrlProjectionSet(
        sec_xbrl_projection_set_id=_uid(),
        client_request_id="test-proj-client",
        projection_basis_hash=_PROJECTION_BASIS_HASH,
        projection_schema_id="layer3.sec_xbrl_projection_set.v1",
        source_report_schema_id="layer3.sec_xbrl_source_report.v1",
        source_report_hash=_SOURCE_REPORT_HASH,
        sidecar_receipt_hash=sidecar_hash,
        value_store_hash=_VALUE_STORE_HASH,
        sector_family_presence_json={},
        period_refs_json=[],
        projection_summary_json={},
        status=L3_SEC_XBRL_PROJECTION_STATUS_MATERIALIZED,
        redaction_policy=L3_SEC_XBRL_PROJECTION_REDACTION_POLICY,
    )
    db.add(proj)
    db.flush()
    return proj


def _add_oracle_facts(
    db,
    proj: L3SecXbrlProjectionSet,
    *,
    total: int = 3,
    confirmed: int = 3,
    sidecar_hash: str = _SIDECAR_HASH,
) -> None:
    """Add projection facts to the set with a given confirmed/eligible split."""
    for i in range(total):
        oracle_val = (
            "projected_oracle_confirmed" if i < confirmed else "projected_unconfirmed"
        )
        fact = L3SecXbrlProjectionFact(
            sec_xbrl_projection_fact_id=_uid(),
            sec_xbrl_projection_set_id=proj.sec_xbrl_projection_set_id,
            period_ref=f"FY2023-{i}",
            period_index=i,
            statement="income_statement",
            statement_row_index=i,
            canonical_id=f"canonical-{i}",
            basis="primary",
            requested_basis="primary",
            family="income",
            status="projected_oracle_confirmed" if i < confirmed else "projected_unconfirmed",
            oracle_confirmed=oracle_val,
            value_redacted=True,
            provenance_complete=True,
            resolved_fact_provenance_present=True,
            sidecar_receipt_hash=sidecar_hash,
            value_store_hash=_VALUE_STORE_HASH,
            derived_from_concepts_json=[],
        )
        db.add(fact)
    db.flush()


def _build_packet_set(
    db,
    proj: L3SecXbrlProjectionSet,
    *,
    review_exception_count: int = 0,
) -> L3SecXbrlStatementPacketSet:
    packet = L3SecXbrlStatementPacketSet(
        sec_xbrl_statement_packet_set_id=_uid(),
        sec_xbrl_projection_set_id=proj.sec_xbrl_projection_set_id,
        client_request_id="test-packet-client",
        packet_basis_hash=_PACKET_BASIS_HASH,
        packet_schema_id="layer3.sec_xbrl_statement_packet_set.v1",
        source_projection_basis_hash=_PROJECTION_BASIS_HASH,
        source_projection_schema_id="layer3.sec_xbrl_projection_set.v1",
        statement_organization_authority="test-authority",
        value_policy=L3_SEC_XBRL_STATEMENT_PACKET_REDACTION_POLICY,
        statement_count=1,
        total_review_rows=3,
        provenance_complete_count=3,
        review_exception_count=review_exception_count,
        review_ready=True,
        identity_rollup_json={},
        organization_contract_json={},
        packet_summary_json={},
        status=L3_SEC_XBRL_STATEMENT_PACKET_STATUS_MATERIALIZED,
    )
    db.add(packet)
    db.flush()
    return packet


def _build_workflow(
    db,
    packet: L3SecXbrlStatementPacketSet,
    *,
    review_exception_count: int = 0,
    workflow_basis_hash: str = _WORKFLOW_BASIS_HASH,
) -> L3SecXbrlOperatorReviewWorkflow:
    wf = L3SecXbrlOperatorReviewWorkflow(
        sec_xbrl_operator_review_workflow_id=_uid(),
        sec_xbrl_statement_packet_set_id=packet.sec_xbrl_statement_packet_set_id,
        client_request_id="test-wf-client",
        workflow_basis_hash=workflow_basis_hash,
        workflow_schema_id="layer3.sec_xbrl_operator_review_workflow.v1",
        statement_packet_basis_hash=_PACKET_BASIS_HASH,
        source_projection_basis_hash=_PROJECTION_BASIS_HASH,
        control_mode=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
        review_status=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_STATUS_READY,
        redaction_policy=L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
        statement_count=1,
        row_count=3,
        review_exception_count=review_exception_count,
        review_ready=True,
        permitted_controls_json=[],
        blocked_controls_json=[],
        authority_refs_json={},
        review_summary_json={
            "statement_count": 1,
            "row_count": 3,
            "review_exception_count": review_exception_count,
            "review_ready": True,
            "redaction_policy": L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_REDACTION_POLICY,
            "control_mode": L3_SEC_XBRL_OPERATOR_REVIEW_WORKFLOW_CONTROL_MODE,
        },
    )
    db.add(wf)
    db.flush()
    return wf


def _build_decision(
    db,
    wf: L3SecXbrlOperatorReviewWorkflow,
    *,
    review_decision: str = "approved",
    decision_reason_code: str = "ready_for_next_freeze",
) -> L3SecXbrlOperatorReviewDecision:
    decision_basis = stable_hash({"decision": "test", "wf": wf.sec_xbrl_operator_review_workflow_id})
    dec = L3SecXbrlOperatorReviewDecision(
        sec_xbrl_operator_review_decision_id=_uid(),
        sec_xbrl_operator_review_workflow_id=wf.sec_xbrl_operator_review_workflow_id,
        client_request_id="test-decision-client",
        decision_basis_hash=decision_basis,
        decision_schema_id="layer3.sec_xbrl_operator_review_decision.v1",
        workflow_basis_hash=wf.workflow_basis_hash,
        statement_packet_basis_hash=_PACKET_BASIS_HASH,
        source_projection_basis_hash=_PROJECTION_BASIS_HASH,
        decision_mode=L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_MODE,
        review_decision=review_decision,
        decision_status=L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_STATUS_RECORDED,
        redaction_policy=L3_SEC_XBRL_OPERATOR_REVIEW_DECISION_REDACTION_POLICY,
        decision_reason_code=decision_reason_code,
        decision_notes_present=False,
        decision_summary_json={},
        authority_refs_json={},
        permitted_controls_after_decision_json=[],
        blocked_controls_after_decision_json=[],
    )
    db.add(dec)
    db.flush()
    return dec


def _build_authority(
    db,
    wf: L3SecXbrlOperatorReviewWorkflow,
    dec: L3SecXbrlOperatorReviewDecision,
    proj: L3SecXbrlProjectionSet,
    packet: L3SecXbrlStatementPacketSet,
    *,
    authority_state: str = L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_STATE_READY,
    sidecar_hash: str = _SIDECAR_HASH,
) -> L3SecXbrlValueRevealAuthorityReceipt:
    authority_basis = stable_hash({"authority": "test", "wf": wf.sec_xbrl_operator_review_workflow_id})
    auth = L3SecXbrlValueRevealAuthorityReceipt(
        sec_xbrl_value_reveal_authority_receipt_id=_uid(),
        client_request_id="test-authority-client",
        authority_basis_hash=authority_basis,
        authority_schema_id="layer3.sec_xbrl_value_reveal_authority_receipt.v1",
        sec_xbrl_operator_review_decision_id=dec.sec_xbrl_operator_review_decision_id,
        decision_basis_hash=dec.decision_basis_hash,
        sec_xbrl_operator_review_workflow_id=wf.sec_xbrl_operator_review_workflow_id,
        workflow_basis_hash=wf.workflow_basis_hash,
        sec_xbrl_statement_packet_set_id=packet.sec_xbrl_statement_packet_set_id,
        statement_packet_basis_hash=_PACKET_BASIS_HASH,
        sec_xbrl_projection_set_id=proj.sec_xbrl_projection_set_id,
        projection_basis_hash=_PROJECTION_BASIS_HASH,
        dataset_version_id=_uid(),
        dataset_version_hash=stable_hash({"dataset": "test"}),
        sidecar_receipt_id_hash=stable_hash({"sidecar_id": "test"}),
        sidecar_receipt_hash=sidecar_hash,
        value_store_hash=_VALUE_STORE_HASH,
        authority_state=authority_state,
        authority_policy_id=L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_POLICY_ID,
        redaction_policy=L3_SEC_XBRL_VALUE_REVEAL_AUTHORITY_REDACTION_POLICY,
        authority_summary_json={},
        negative_invariants_json={},
    )
    db.add(auth)
    db.flush()
    return auth


def _write_corpus_receipt(tmp_path: Path, *, sidecar_hash: str = _SIDECAR_HASH) -> None:
    """Write a minimal READY corpus receipt containing the sidecar hash."""
    receipts_dir = tmp_path / RECEIPT_DIR / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    receipt_id = f"{RECEIPT_PREFIX}-{'c' * 24}"
    receipt = {
        "schema_id": "layer3.sec_edgar_real_company_corpus_validation.v1",
        "validation_state": CORPUS_READY_STATE,
        "validation_receipt_id": receipt_id,
        "validation_receipt_hash": "d" * 64,
        "filing_validation_records": [
            {
                "record_index": 1,
                "authority_hashes": {"arelle_sidecar_receipt_hash": sidecar_hash},
                "supported_degraded_blocked": "supported",
            }
        ],
    }
    (receipts_dir / f"{receipt_id}.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8"
    )


def _write_ownership_marker(tmp_path: Path, *, sidecar_hash: str = _SIDECAR_HASH) -> None:
    """Write the ownership marker that require_sec_xbrl_evidence_ownership_marker looks for
    under none-mode (workspace_ref_hash from policy_decision)."""
    # Under none-mode with workspace_ref_hash="0"*64, marker goes at:
    # {storage_dir}/layer3-sec-xbrl-evidence-ownership/{workspace_ref_hash}/sidecar-{sidecar_hash}.json
    workspace_ref_hash = "0" * 64
    marker_dir = (
        tmp_path
        / "layer3-sec-xbrl-evidence-ownership"
        / workspace_ref_hash
    )
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = {
        "schema_id": "layer3.sec_xbrl_evidence_ownership_marker.v1",
        "workspace_ref_hash": workspace_ref_hash,
        "sidecar_receipt_hash": sidecar_hash,
    }
    (marker_dir / f"sidecar-{sidecar_hash}.json").write_text(
        json.dumps(marker, indent=2, sort_keys=True), encoding="utf-8"
    )


def _call(
    db,
    wf: L3SecXbrlOperatorReviewWorkflow,
    *,
    flag_on: bool = True,
) -> dict[str, Any]:
    """Call inspect_redacted_production_admission_status with _validate mocked to pass."""
    with patch(
        "app.services.layer3_sec_xbrl_admission_status._validate_workflow_row_for_status",
    ):
        with patch(
            "app.services.layer3_sec_xbrl_admission_status.production_admission_flag_enabled",
            return_value=flag_on,
        ):
            return inspect_redacted_production_admission_status(
                db,
                client_request_id="test-admission-request",
                sec_xbrl_operator_review_workflow_id=wf.sec_xbrl_operator_review_workflow_id,
                policy_decision=_NONE_POLICY,
                auth_owner_mode=_NONE_AUTH_MODE,
            )


# ---------------------------------------------------------------------------
# Tests: full happy path with flag ON => production_admission_ready True
# ---------------------------------------------------------------------------

def test_full_evidence_flag_on_returns_true(db, tmp_path, monkeypatch):
    """With all evidence present and flag ON, production_admission_ready must be True."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    _add_oracle_facts(db, proj, total=3, confirmed=3)
    packet = _build_packet_set(db, proj, review_exception_count=0)
    wf = _build_workflow(db, packet, review_exception_count=0)
    dec = _build_decision(db, wf)
    _build_authority(db, wf, dec, proj, packet)
    db.commit()

    _write_corpus_receipt(tmp_path)
    _write_ownership_marker(tmp_path)

    result = _call(db, wf, flag_on=True)

    assert result["production_admission_ready"] is True, (
        f"Expected True, blocked_reason={result.get('production_admission_blocked_reason')!r}, "
        f"criteria={result.get('criteria')}"
    )
    assert result["production_readiness_claimed"] is False
    assert result["schema_id"] == ADMISSION_STATUS_SCHEMA_ID
    assert result["admission_note"]


def test_production_readiness_claimed_always_false_on_true_path(db, tmp_path, monkeypatch):
    """production_readiness_claimed stays False even when production_admission_ready is True."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    _add_oracle_facts(db, proj, total=3, confirmed=3)
    packet = _build_packet_set(db, proj)
    wf = _build_workflow(db, packet)
    dec = _build_decision(db, wf)
    _build_authority(db, wf, dec, proj, packet)
    db.commit()

    _write_corpus_receipt(tmp_path)
    _write_ownership_marker(tmp_path)

    result = _call(db, wf, flag_on=True)

    assert result["production_readiness_claimed"] is False


# ---------------------------------------------------------------------------
# Tests: flag OFF => always False
# ---------------------------------------------------------------------------

def test_flag_off_returns_false(db, tmp_path, monkeypatch):
    """With flag OFF, production_admission_ready must be False regardless of evidence."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    _add_oracle_facts(db, proj, total=3, confirmed=3)
    packet = _build_packet_set(db, proj)
    wf = _build_workflow(db, packet)
    dec = _build_decision(db, wf)
    _build_authority(db, wf, dec, proj, packet)
    db.commit()

    _write_corpus_receipt(tmp_path)
    _write_ownership_marker(tmp_path)

    result = _call(db, wf, flag_on=False)

    assert result["production_admission_ready"] is False
    assert result["production_readiness_claimed"] is False
    assert result["production_admission_blocked_reason"] == "production_admission_flag_disabled"


# ---------------------------------------------------------------------------
# Tests: break each evidence piece
# ---------------------------------------------------------------------------

def test_no_decision_blocks_on_operator_decision(db, tmp_path, monkeypatch):
    """Without a decision row, operator_decision criterion must fail."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    _add_oracle_facts(db, proj, total=3, confirmed=3)
    packet = _build_packet_set(db, proj)
    wf = _build_workflow(db, packet)
    # No decision record written.
    db.commit()

    _write_corpus_receipt(tmp_path)
    _write_ownership_marker(tmp_path)

    result = _call(db, wf, flag_on=True)

    assert result["production_admission_ready"] is False
    # Must fail on operator_decision criterion or earlier.
    assert result["production_admission_blocked_reason"] in {
        "operator_decision_not_approved_ready",
        "corpus_validation_or_ownership_missing",
        "companyfacts_oracle_not_full_coverage",
        "value_reveal_authority_not_valid",
    }


def test_wrong_decision_blocks(db, tmp_path, monkeypatch):
    """A decision with wrong review_decision must block on operator_decision criterion."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    _add_oracle_facts(db, proj, total=3, confirmed=3)
    packet = _build_packet_set(db, proj)
    wf = _build_workflow(db, packet)
    dec = _build_decision(db, wf, review_decision="changes_requested", decision_reason_code="needs_packet_revision")
    _build_authority(db, wf, dec, proj, packet)
    db.commit()

    _write_corpus_receipt(tmp_path)
    _write_ownership_marker(tmp_path)

    result = _call(db, wf, flag_on=True)

    assert result["production_admission_ready"] is False
    assert "criteria" in result
    assert result["criteria"]["operator_decision_approved_ready_for_next_freeze"]["passed"] is False


def test_no_authority_blocks_on_value_reveal(db, tmp_path, monkeypatch):
    """Without a value-reveal authority receipt, value_reveal criterion must fail."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    _add_oracle_facts(db, proj, total=3, confirmed=3)
    packet = _build_packet_set(db, proj)
    wf = _build_workflow(db, packet)
    _build_decision(db, wf)
    # No authority record.
    db.commit()

    _write_corpus_receipt(tmp_path)
    _write_ownership_marker(tmp_path)

    result = _call(db, wf, flag_on=True)

    assert result["production_admission_ready"] is False
    assert result["criteria"]["value_reveal_authority_receipt_valid"]["passed"] is False


def test_partial_oracle_blocks(db, tmp_path, monkeypatch):
    """Partial oracle coverage (confirmed < eligible) must block."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    _add_oracle_facts(db, proj, total=3, confirmed=1)  # 2 unconfirmed
    packet = _build_packet_set(db, proj)
    wf = _build_workflow(db, packet)
    dec = _build_decision(db, wf)
    _build_authority(db, wf, dec, proj, packet)
    db.commit()

    _write_corpus_receipt(tmp_path)
    _write_ownership_marker(tmp_path)

    result = _call(db, wf, flag_on=True)

    assert result["production_admission_ready"] is False
    assert result["criteria"]["companyfacts_oracle_full_coverage"]["passed"] is False


def test_no_corpus_receipt_blocks(db, tmp_path, monkeypatch):
    """Without a corpus receipt on disk, corpus criterion must fail."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    _add_oracle_facts(db, proj, total=3, confirmed=3)
    packet = _build_packet_set(db, proj)
    wf = _build_workflow(db, packet)
    dec = _build_decision(db, wf)
    _build_authority(db, wf, dec, proj, packet)
    db.commit()

    _write_ownership_marker(tmp_path)
    # Do NOT write corpus receipt.

    result = _call(db, wf, flag_on=True)

    assert result["production_admission_ready"] is False
    assert result["criteria"]["corpus_validation_passed_with_ownership"]["passed"] is False


def test_review_exceptions_nonzero_blocks(db, tmp_path, monkeypatch):
    """A workflow with nonzero review_exception_count must block on review_exceptions_zero."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    _add_oracle_facts(db, proj, total=3, confirmed=3)
    packet = _build_packet_set(db, proj, review_exception_count=2)
    wf = _build_workflow(db, packet, review_exception_count=2)
    dec = _build_decision(db, wf)
    _build_authority(db, wf, dec, proj, packet)
    db.commit()

    _write_corpus_receipt(tmp_path)
    _write_ownership_marker(tmp_path)

    result = _call(db, wf, flag_on=True)

    assert result["production_admission_ready"] is False
    assert result["criteria"]["review_exceptions_zero"]["passed"] is False


# ---------------------------------------------------------------------------
# Tests: no raw leak in response
# ---------------------------------------------------------------------------

def test_no_raw_leak_in_response(db, tmp_path, monkeypatch):
    """The response dict must not contain raw CIK, ticker, or value leaks."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    _add_oracle_facts(db, proj, total=3, confirmed=3)
    packet = _build_packet_set(db, proj)
    wf = _build_workflow(db, packet)
    dec = _build_decision(db, wf)
    _build_authority(db, wf, dec, proj, packet)
    db.commit()

    _write_corpus_receipt(tmp_path)
    _write_ownership_marker(tmp_path)

    result = _call(db, wf, flag_on=True)

    # Confirm no forbidden raw keys appear in the serialized response.
    serialized = json.dumps(result)
    forbidden = ("cik", "ticker", "issuer_name", "entity_name", "company_name")
    for key in forbidden:
        assert f'"{key}"' not in serialized, f"Found forbidden key {key!r} in response"


# ---------------------------------------------------------------------------
# Tests: workflow not found => blocked
# ---------------------------------------------------------------------------

def test_workflow_not_found_returns_blocked(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    with patch(
        "app.services.layer3_sec_xbrl_admission_status.production_admission_flag_enabled",
        return_value=True,
    ):
        result = inspect_redacted_production_admission_status(
            db,
            client_request_id="test-not-found",
            sec_xbrl_operator_review_workflow_id="does-not-exist",
            policy_decision=_NONE_POLICY,
            auth_owner_mode=_NONE_AUTH_MODE,
        )
    assert result["status"] == "blocked"
    assert result["production_admission_ready"] is False
    assert result["production_readiness_claimed"] is False


def test_no_workflow_id_returns_blocked(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    with patch(
        "app.services.layer3_sec_xbrl_admission_status.production_admission_flag_enabled",
        return_value=True,
    ):
        result = inspect_redacted_production_admission_status(
            db,
            client_request_id="test-no-id",
            policy_decision=_NONE_POLICY,
            auth_owner_mode=_NONE_AUTH_MODE,
        )
    assert result["status"] == "blocked"
    assert result["production_readiness_claimed"] is False


# ---------------------------------------------------------------------------
# Tests: response structure
# ---------------------------------------------------------------------------

def test_response_echoes_workflow_id_and_basis_hash(db, tmp_path, monkeypatch):
    """Response must echo workflow_id and basis_hash (not raw cik/values)."""
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    proj = _build_projection_set(db)
    packet = _build_packet_set(db, proj)
    wf = _build_workflow(db, packet)
    db.commit()

    result = _call(db, wf, flag_on=True)

    assert result["sec_xbrl_operator_review_workflow_id"] == wf.sec_xbrl_operator_review_workflow_id
    assert result["workflow_basis_hash"] == wf.workflow_basis_hash
    assert result["sidecar_receipt_hash"] == _SIDECAR_HASH
