from __future__ import annotations

import importlib.util
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
GATE_B_IDEMPOTENCY_MIGRATION = BACKEND / "alembic" / "versions" / "0017_layer3_gate_b_idempotency.py"

from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    L3GateBIdempotencyKey,
    L3OutputPackage,
    L3PassRun,
    L3SelectionManifest,
    L3Session,
)
from app.services import layer3_workbench
from app.services.layer3_gate_b_state import (
    GATE_B_DECISIONS,
    GATE_B_IDEMPOTENCY_CONTEXT_KEY,
    GATE_B_IDEMPOTENCY_SCHEMA_ID,
    GATE_B_IDEMPOTENCY_STATUS_CLAIMED,
    GATE_B_IDEMPOTENCY_STATUS_COMMITTED,
    claim_gate_b_idempotency,
    complete_gate_b_idempotency_claim,
    find_gate_b_idempotency_claim,
    find_gate_b_idempotency_session,
    gate_b_counts,
    gate_b_idempotency_claim_matches,
    gate_b_idempotency_from_session,
    gate_b_idempotency_record,
    gate_b_idempotency_request_hash,
    gate_b_summary_from_session,
)
from app.services.layer3_workbench import Layer3WorkbenchError


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _record(client_request_id: str = "req-gate-b") -> dict:
    return gate_b_idempotency_record(
        client_request_id=client_request_id,
        preflight_id="preflight-1",
        source_set_id="source-set-1",
        material_preview_id="material-preview-1",
        material_preview_hash="hash-1",
        gate_b_decision_manifest_id="gate-b-manifest-1",
    )


def test_gate_b_idempotency_record_round_trips_from_session() -> None:
    record = _record()
    session = L3Session(
        session_id="session-1",
        selection_manifest_id="manifest-1",
        operator_context_json={GATE_B_IDEMPOTENCY_CONTEXT_KEY: record},
    )

    assert record["schema_id"] == GATE_B_IDEMPOTENCY_SCHEMA_ID
    assert gate_b_idempotency_from_session(session) == record


def test_gate_b_idempotency_from_session_rejects_missing_or_wrong_schema() -> None:
    missing = L3Session(session_id="missing", selection_manifest_id="manifest-missing", operator_context_json={})
    wrong_schema = L3Session(
        session_id="wrong-schema",
        selection_manifest_id="manifest-wrong",
        operator_context_json={
            GATE_B_IDEMPOTENCY_CONTEXT_KEY: {
                **_record(),
                "schema_id": "layer3.gate_b_idempotency.v0",
            }
        },
    )

    assert gate_b_idempotency_from_session(missing) is None
    assert gate_b_idempotency_from_session(wrong_schema) is None


def test_gate_b_counts_preserve_workbench_decision_vocabulary() -> None:
    decisions = [
        {"decision": "approved"},
        {"decision": "approved"},
        {"decision": "denied"},
        {"decision": "isolated"},
        {"decision": "flagged"},
    ]

    assert GATE_B_DECISIONS == ("approved", "denied", "isolated", "flagged")
    assert gate_b_counts(decisions) == {
        "approved": 2,
        "denied": 1,
        "isolated": 1,
        "flagged": 1,
    }


def test_gate_b_summary_from_session_prefers_summary_json_counts() -> None:
    session = L3Session(
        session_id="session-summary",
        selection_manifest_id="manifest-summary",
        summary_json={"gate_b_summary_v1": {"approved": "2", "denied": 1}},
        operator_context_json={
            "layer3_gate_b_decision_manifest_v1": {
                "items": [
                    {"decision": "approved"},
                    {"decision": "flagged"},
                ]
            }
        },
    )

    assert gate_b_summary_from_session(session) == {
        "approved": 2,
        "denied": 1,
        "isolated": 0,
        "flagged": 0,
    }


def test_gate_b_summary_from_session_falls_back_to_decision_manifest() -> None:
    session = L3Session(
        session_id="session-manifest",
        selection_manifest_id="manifest-manifest",
        operator_context_json={
            "layer3_gate_b_decision_manifest_v1": {
                "items": [
                    {"decision": "approved"},
                    {"decision": "denied"},
                    {"decision": "flagged"},
                ]
            }
        },
    )

    assert gate_b_summary_from_session(session) == {
        "approved": 1,
        "denied": 1,
        "isolated": 0,
        "flagged": 1,
    }


def test_find_gate_b_idempotency_session_returns_matching_record(db_session) -> None:
    matching_record = _record("req-match")
    db_session.add_all(
        [
            L3Session(
                session_id="session-other",
                selection_manifest_id="manifest-other",
                operator_context_json={GATE_B_IDEMPOTENCY_CONTEXT_KEY: _record("req-other")},
            ),
            L3Session(
                session_id="session-match",
                selection_manifest_id="manifest-match",
                operator_context_json={GATE_B_IDEMPOTENCY_CONTEXT_KEY: matching_record},
            ),
        ]
    )
    db_session.commit()

    result = find_gate_b_idempotency_session(db_session, client_request_id="req-match")

    assert result is not None
    session, record = result
    assert session.session_id == "session-match"
    assert record == matching_record
    assert find_gate_b_idempotency_session(db_session, client_request_id="req-missing") is None
    assert find_gate_b_idempotency_session(db_session, client_request_id="") is None


def test_gate_b_idempotency_migration_defines_durable_unique_claim(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location("layer3_gate_b_idempotency_migration", GATE_B_IDEMPOTENCY_MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    created_tables = []
    created_indexes = []

    def capture_create_table(name, *elements):
        created_tables.append((name, elements))

    def capture_create_index(name, table, columns, **kwargs):
        created_indexes.append((name, table, columns, kwargs))

    monkeypatch.setattr(module, "create_table_idempotent", capture_create_table)
    monkeypatch.setattr(module, "create_index_idempotent", capture_create_index)
    module.upgrade()

    elements = next(items for name, items in created_tables if name == "l3_gate_b_idempotency_key")
    unique = next(element for element in elements if isinstance(element, UniqueConstraint))
    assert unique.name == "uq_l3_gate_b_idempotency_client_request"
    constraints = [element for element in elements if isinstance(element, CheckConstraint)]
    constraint = next(element for element in constraints if element.name == "ck_l3_gate_b_idempotency_status")
    assert "claimed" in str(constraint.sqltext)
    assert "committed" in str(constraint.sqltext)
    assert ("ix_l3_gate_b_idempotency_session", "l3_gate_b_idempotency_key", ["session_id"], {}) in created_indexes
    assert ("ix_l3_gate_b_idempotency_status", "l3_gate_b_idempotency_key", ["status"], {}) in created_indexes


def test_gate_b_idempotency_claim_round_trips_and_matches(db_session) -> None:
    claim, existing = claim_gate_b_idempotency(
        db_session,
        client_request_id="req-claim",
        preflight_id="preflight-1",
        source_set_id="source-set-1",
        material_preview_id="material-preview-1",
        material_preview_hash="hash-1",
        gate_b_decision_manifest_id="gate-b-manifest-1",
    )

    assert existing is None
    assert claim is not None
    assert claim.status == GATE_B_IDEMPOTENCY_STATUS_CLAIMED
    assert claim.request_basis_hash == gate_b_idempotency_request_hash(
        client_request_id="req-claim",
        preflight_id="preflight-1",
        source_set_id="source-set-1",
        material_preview_id="material-preview-1",
        material_preview_hash="hash-1",
        gate_b_decision_manifest_id="gate-b-manifest-1",
    )
    assert gate_b_idempotency_claim_matches(
        claim,
        client_request_id="req-claim",
        preflight_id="preflight-1",
        source_set_id="source-set-1",
        material_preview_id="material-preview-1",
        material_preview_hash="hash-1",
        gate_b_decision_manifest_id="gate-b-manifest-1",
    )
    assert not gate_b_idempotency_claim_matches(
        claim,
        client_request_id="req-claim",
        preflight_id="preflight-1",
        source_set_id="source-set-1",
        material_preview_id="material-preview-1",
        material_preview_hash="different-hash",
        gate_b_decision_manifest_id="gate-b-manifest-1",
    )
    db_session.commit()

    duplicate_claim, duplicate_existing = claim_gate_b_idempotency(
        db_session,
        client_request_id="req-claim",
        preflight_id="preflight-1",
        source_set_id="source-set-1",
        material_preview_id="material-preview-1",
        material_preview_hash="hash-1",
        gate_b_decision_manifest_id="gate-b-manifest-1",
    )
    assert duplicate_claim is None
    assert duplicate_existing is not None
    assert duplicate_existing.gate_b_idempotency_key_id == claim.gate_b_idempotency_key_id
    claim = duplicate_existing

    session = L3Session(session_id="session-claim", selection_manifest_id="manifest-claim")
    manifest = L3SelectionManifest(
        selection_manifest_id="manifest-claim",
        session_id="session-claim",
        manifest_json={"items": [{"source_plane": "plane-a"}]},
        source_plane_hints_json={},
        selection_hash="a" * 64,
        commit_reason="claim-proof",
    )
    complete_gate_b_idempotency_claim(claim, session=session, manifest=manifest)

    assert claim.status == GATE_B_IDEMPOTENCY_STATUS_COMMITTED
    assert claim.session_id == "session-claim"
    assert claim.selection_manifest_id == "manifest-claim"
    assert find_gate_b_idempotency_claim(db_session, client_request_id="req-claim") == claim


def _prepare_gate_b_payload(db_session, *, request_id: str) -> dict:
    preflight = layer3_workbench.preflight(
        {
            "client_request_id": f"{request_id}-preflight",
            "natural_language_intent": "Review deterministic Layer 3 source material.",
            "manual_constraints": {"source_classes": ["dataset_version", "aps_content_document"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": f"{request_id}-source",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version", "aps_content_document"],
        }
    )
    material = layer3_workbench.material_preview(
        {
            "client_request_id": f"{request_id}-material",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [item["source_candidate_id"] for item in source["source_candidates"]],
            "query_basis": {"terms": ["deterministic", "source"]},
        },
        db_session,
    )
    first, second = material["material_candidates"]
    return {
        "client_request_id": request_id,
        "preflight_id": preflight["preflight_id"],
        "source_set_id": source["source_set_id"],
        "material_preview_id": material["material_preview_id"],
        "material_preview_hash": material["material_preview_hash"],
        "candidate_decisions": [
            {
                "candidate_id": first["candidate_id"],
                "decision": "approved",
                "operator_reason": "",
                "decision_basis": {
                    "source_ref": first["source_ref"],
                    "query_basis": first["query_basis"],
                    "provenance_ref": first["provenance_ref"],
                },
            },
            {
                "candidate_id": second["candidate_id"],
                "decision": "denied",
                "operator_reason": "Not in first-slice scope.",
                "decision_basis": {
                    "source_ref": second["source_ref"],
                    "query_basis": second["query_basis"],
                    "provenance_ref": second["provenance_ref"],
                },
            },
        ],
        "actor": "pytest",
    }


def test_gate_b_decision_concurrent_duplicate_client_request_id_uses_durable_claim(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    bootstrap_storage_tree(settings.storage_dir)
    engine = create_engine(
        f"sqlite:///{tmp_path / 'gate-b-idempotency.sqlite'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    setup_db = SessionLocal()
    try:
        payload = _prepare_gate_b_payload(setup_db, request_id="req-gate-b-concurrent")
    finally:
        setup_db.close()

    def submit_gate_b(actor: str) -> tuple[str, str, str | None]:
        db = SessionLocal()
        try:
            response = layer3_workbench.gate_b_decision(db, {**payload, "actor": actor})
            return ("returned", response["status"], response["session_id"])
        except Layer3WorkbenchError as exc:
            return ("rejected", exc.error_code, None)
        finally:
            db.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(submit_gate_b, ("pytest-1", "pytest-2")))

        assert sum(result[0] == "returned" and result[1] == "ok" for result in results) == 1
        assert all(
            (kind == "returned" and status in {"ok", "already_committed"})
            or (kind == "rejected" and status == "gate_b_idempotency_in_progress")
            for kind, status, _ in results
        )

        db = SessionLocal()
        try:
            sessions = db.query(L3Session).all()
            claims = db.query(L3GateBIdempotencyKey).all()
            assert len(sessions) == 1
            assert len(claims) == 1
            assert claims[0].status == GATE_B_IDEMPOTENCY_STATUS_COMMITTED
            assert claims[0].session_id == sessions[0].session_id
            assert claims[0].selection_manifest_id == sessions[0].selection_manifest_id
            assert db.query(L3PassRun).count() == 0
            assert db.query(AnalysisRun).count() == 0
            assert db.query(AnalysisArtifact).count() == 0
            assert db.query(L3OutputPackage).count() == 0
        finally:
            db.close()
    finally:
        engine.dispose()
