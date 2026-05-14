from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    AnalysisRun,
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetSourceProvenance,
    DatasetVersion,
    L3AnalysisPlan,
    L3AnalysisGroup,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ProviderPrivateSignedUrlAuditEvent,
    L3ProviderPrivateSignedUrlObjectAuthority,
    L3ProviderPrivateSignedUrlReceipt,
    L3ProviderPrivateSignedUrlRevocation,
    L3ReconciliationRecord,
    L3SelectionManifest,
    L3Session,
    L3SourceIntakeRecord,
    L3TypingRecord,
    VariableDefinition,
)
from app.services import layer3_provider_private_signed_url, layer3_workbench
from app.services.layer3_workbench import Layer3WorkbenchError
from app.services.layer3_state_action_contract import STATE_ACTION_CONTRACT_SCHEMA_ID
from app.services.layer3_authority_matrix_contract import (
    AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID,
    AUTHORITY_MATRIX_EXISTING_ROUTE_RESPONSE_RESULT,
    AUTHORITY_MATRIX_FAIL_CLOSED_RESULT,
    AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_CONTEXT,
    AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_RESULT,
    AUTHORITY_MATRIX_RESPONSE_MODEL_RESULT,
)


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    bootstrap_storage_tree(storage_dir)
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


def _preflight_source_material() -> tuple[dict, dict, dict]:
    preflight = layer3_workbench.preflight(
        {
            "client_request_id": "req-preflight",
            "natural_language_intent": "Review deterministic dataset and APS document material.",
            "manual_constraints": {"source_classes": ["dataset_version", "aps_content_document"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": "req-source",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version", "aps_content_document"],
        }
    )
    material = layer3_workbench.material_preview(
        {
            "client_request_id": "req-material",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [item["source_candidate_id"] for item in source["source_candidates"]],
            "query_basis": {"terms": ["deterministic", "document"]},
        }
    )
    return preflight, source, material


def test_execution_start_runs_source_intake_selected_pass_without_analysis_run(db_session, monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    session = L3Session(
        session_id="session-source-intake-exec-selection",
        status="completed",
        selection_manifest_id="manifest-source-intake-exec-selection",
        entry_route_context_json={"entrypoint": "pytest"},
        operator_context_json={"operator": "pytest"},
        summary_json={},
        started_at=now,
        created_at=now,
        completed_at=now,
    )
    plan = L3AnalysisPlan(
        analysis_plan_id="plan-source-intake-exec-selection",
        session_id=session.session_id,
        analysis_set_ids_json=["analysis-set-source-intake"],
        status="approved",
        approved_by_operator=True,
        approved_at=now,
        plan_json={
            "source_preview_id": "source-intake-plan-preview",
            "source_preview_hash": "source-intake-preview-hash",
            "planned_passes_json": [
                {
                    "analysis_set_id": "analysis-set-source-intake",
                    "pass_type": "single_item",
                    "pass_scope": "qualitative_single_item_operator_uploaded_source",
                    "engine_family": "source_intake_qualitative_preview",
                    "selected_method_name": "operator_uploaded_source_review_preview",
                    "source_gate": "299_SOURCE_INTAKE_PLAN_PREVIEW_BOUNDARY_FREEZE",
                    "source_intake_record_id": "src-intake-plan-001",
                    "candidate_id": "mat-source_intake_record-src-intake-plan-001",
                }
            ],
        },
        created_at=now,
    )
    source_record = L3SourceIntakeRecord(
        source_intake_record_id="src-intake-plan-001",
        client_request_id="source-intake-record-request",
        operator_decision="record_operator_uploaded_source",
        source_family="operator_uploaded_single_source",
        source_label="Operator uploaded source",
        source_description="Source-intake execution-start proof fixture.",
        original_filename="operator-source.txt",
        media_type="text/plain",
        content_size_bytes=27,
        content_sha256="a" * 64,
        metadata_hash="b" * 64,
        authority_basis_hash="c" * 64,
        storage_ref="raw/layer3-source-intake/operator-source.txt",
        freshness_timestamp=now,
        provenance_json={
            "schema_id": "layer3.source_intake_record.v1",
            "mode": "operator_single_upload_source_intake",
            "source_gate": "286_SOURCE_BREADTH_RUNTIME_ENTRY_FREEZE",
        },
        downstream_eligibility_json={"gate_b_material_candidate": True},
        summary_json={"metadata": {"source_label": "Operator uploaded source"}},
        status="recorded",
        created_at=now,
        updated_at=now,
    )
    manifest = L3SelectionManifest(
        selection_manifest_id=session.selection_manifest_id,
        session_id=session.session_id,
        manifest_json={"session_id": session.session_id, "source": "pytest_source_intake"},
        source_plane_hints_json={"source_intake_record_ids": ["src-intake-plan-001"]},
        selection_hash="source-intake-selection-hash",
        committed_at=now,
        commit_reason="pytest source-intake selection manifest",
    )
    db_session.add_all([session, plan, source_record, manifest])
    db_session.commit()

    result = layer3_workbench.execution_selection(
        db_session,
        {
            "client_request_id": "source-intake-exec-selection",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
        },
    )

    pass_run = db_session.query(L3PassRun).one()
    planned_pass = pass_run.summary_json["planned_pass"]
    assert result["status"] == "selected_not_started"
    assert result["pass_run_ids"] == [pass_run.pass_run_id]
    assert result["pass_run_count"] == 1
    assert result["execution_started"] is False
    assert result["pass_run_statuses"] == {pass_run.pass_run_id: "selected_not_started"}
    assert pass_run.status == "selected_not_started"
    assert pass_run.engine_family == "source_intake_qualitative_preview"
    assert pass_run.output_payload_ref is None
    assert pass_run.summary_json["execution_started"] is False
    assert pass_run.summary_json["analysis_run_id"] is None
    assert pass_run.summary_json["source_preview_id"] == "source-intake-plan-preview"
    assert pass_run.summary_json["source_preview_hash"] == "source-intake-preview-hash"
    assert planned_pass["pass_scope"] == "qualitative_single_item_operator_uploaded_source"
    assert planned_pass["source_intake_record_id"] == "src-intake-plan-001"
    assert planned_pass["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"

    idempotent_replay = layer3_workbench.execution_selection(
        db_session,
        {
            "client_request_id": "source-intake-exec-selection",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
        },
    )
    assert idempotent_replay["status"] == "already_selected"
    assert db_session.query(L3PassRun).count() == 1

    start = layer3_workbench.analysis_execution_start(
        db_session,
        {
            "client_request_id": "source-intake-execution-start",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
        },
    )
    db_session.refresh(pass_run)
    output_payload = json.loads(Path(pass_run.output_payload_ref).read_text(encoding="utf-8"))

    assert start["status"] == "completed"
    assert start["execution_started"] is True
    assert start["analysis_run_id"] is None
    assert start["pass_run_status"] == "completed"
    assert start["engine_family"] == "source_intake_qualitative_preview"
    assert pass_run.status == "completed"
    assert pass_run.summary_json["execution_started"] is True
    assert pass_run.summary_json["analysis_run_id"] is None
    assert pass_run.summary_json["source_intake_record_id"] == "src-intake-plan-001"
    assert pass_run.summary_json["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert pass_run.summary_json["source_gate"] == "306_SOURCE_INTAKE_EXECUTION_START_BOUNDARY_FREEZE"
    assert output_payload["schema_id"] == "layer3.source_intake_execution_output.v1"
    assert output_payload["analysis_run_id"] is None
    assert output_payload["source_intake_record_id"] == "src-intake-plan-001"
    assert output_payload["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert output_payload["storage_pointer"]["absolute_path_exposed"] is False
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(L3OutputPackage).count() == 0

    idempotent_start = layer3_workbench.analysis_execution_start(
        db_session,
        {
            "client_request_id": "source-intake-execution-start",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
        },
    )
    assert idempotent_start["status"] == "already_completed"
    assert db_session.query(L3PassRun).count() == 1

    status = layer3_workbench.execution_result_status(
        db_session,
        {
            "client_request_id": "source-intake-result-status",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "operator_view_mode": "status_only",
        },
    )
    assert status["status"] == "available"
    assert status["result_status_available"] is True
    assert status["analysis_run_id"] is None
    assert status["analysis_run_status"] is None
    assert status["result_review_enabled"] is False
    assert status["package_review_enabled"] is False
    assert status["handoff_enabled"] is False
    assert status["output_metadata_summary"]["schema_id"] == "layer3.source_intake_execution_output.v1"
    assert status["output_metadata_summary"]["source_intake_record_id"] == "src-intake-plan-001"
    assert status["output_metadata_summary"]["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert status["output_metadata_summary"]["storage_pointer"]["absolute_path_exposed"] is False
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(L3OutputPackage).count() == 0

    result_review = layer3_workbench.execution_result_review(
        db_session,
        {
            "client_request_id": "source-intake-result-review-approved",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "operator_decision": "approved",
        },
    )
    db_session.refresh(pass_run)
    stored_review = pass_run.summary_json["execution_result_review"]
    assert result_review["status"] == "recorded"
    assert result_review["analysis_run_id"] is None
    assert result_review["review_state"] == "execution_result_review_approved"
    assert result_review["operator_decision"] == "approved"
    assert result_review["package_review_enabled"] is False
    assert result_review["handoff_enabled"] is False
    assert stored_review["source_intake_record_id"] == "src-intake-plan-001"
    assert stored_review["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert stored_review["output_schema_id"] == "layer3.source_intake_execution_output.v1"
    assert stored_review["output_hash"] == output_payload["output_hash"]
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(L3OutputPackage).count() == 0

    package_preview = layer3_workbench.package_review_preview(
        db_session,
        {
            "client_request_id": "source-intake-package-preview-ready",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
        },
    )
    assert package_preview["status"] == "available"
    assert package_preview["schema_id"] == "layer3.source_intake_package_review_preview.v1"
    assert package_preview["analysis_run_id"] is None
    assert package_preview["package_review_preview_enabled"] is True
    assert package_preview["package_commit_enabled"] is True
    assert package_preview["package_review_submit_enabled"] is False
    assert package_preview["source_intake_record_id"] == "src-intake-plan-001"
    assert package_preview["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert package_preview["output_payload_hash"] == output_payload["output_hash"]
    assert package_preview["package_owner_compatibility"]["workbench_package_commit_callable"] is True
    assert "package_construction" not in package_preview["downstream_unavailable"]
    preview_session_summary = layer3_workbench.session_summary(db_session, session.session_id)
    assert preview_session_summary["package_review_preview"]["package_commit_enabled"] is True
    assert preview_session_summary["package_review_preview"]["source_intake_record_id"] == "src-intake-plan-001"
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(L3OutputPackage).count() == 0
    assert db_session.query(L3ReconciliationRecord).count() == 0

    package_construction = layer3_workbench.package_construction_commit(
        db_session,
        {
            "client_request_id": "source-intake-package-construction-commit",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
        },
    )
    assert package_construction["status"] == "committed"
    assert package_construction["schema_id"] == "layer3.source_intake_package_construction_commit.v1"
    assert package_construction["analysis_run_id"] is None
    assert package_construction["source_intake_record_id"] == "src-intake-plan-001"
    assert package_construction["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert package_construction["output_payload_hash"] == output_payload["output_hash"]
    assert package_construction["package_review_submit_enabled"] is True
    assert package_construction["next_allowed_actions"] == ["submit_package_review"]
    assert package_construction["package_construction_source_gate"] == (
        "314_SOURCE_INTAKE_PACKAGE_CONSTRUCTION_COMMIT_BOUNDARY_FREEZE"
    )
    assert set(package_construction["package_kinds"]) == {
        "canonical_internal",
        "user_facing",
        "review_facing",
    }
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(L3OutputPackage).count() == 3
    assert db_session.query(L3ReconciliationRecord).count() == 1
    construction_session_summary = layer3_workbench.session_summary(db_session, session.session_id)
    assert construction_session_summary["package_construction"]["package_review_submit_enabled"] is True
    assert construction_session_summary["package_construction"]["source_intake_record_id"] == "src-intake-plan-001"
    assert (
        construction_session_summary["package_review_submit"]["package_review_submit_schema_id"]
        == "layer3.source_intake_package_review_submit.v1"
    )
    assert construction_session_summary["package_review_submit"]["available"] is True

    package_construction_replay = layer3_workbench.package_construction_commit(
        db_session,
        {
            "client_request_id": "source-intake-package-construction-commit",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
        },
    )
    assert package_construction_replay["status"] == "already_committed"
    assert package_construction_replay["output_package_ids"] == package_construction["output_package_ids"]
    assert db_session.query(L3OutputPackage).count() == 3
    assert db_session.query(L3ReconciliationRecord).count() == 1

    with pytest.raises(Layer3WorkbenchError) as package_review_submit_blocked:
        layer3_workbench.package_construction_commit(
            db_session,
            {
                "client_request_id": "source-intake-package-construction-conflict",
                "session_id": session.session_id,
                "analysis_plan_id": plan.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "preview_id": "source-intake-plan-preview",
                "preview_hash": "source-intake-preview-hash",
                "result_review_record_ref": result_review["review_record_ref"],
                "package_review_preview_hash": "source-intake-package-preview-hash-mismatch",
            },
        )
    assert package_review_submit_blocked.value.error_code == "package_review_preview_mismatch"

    with pytest.raises(Layer3WorkbenchError) as handoff_export_not_admitted:
        layer3_workbench.handoff_export_prepare(
            db_session,
            {
                "client_request_id": "source-intake-handoff-export-blocked",
                "session_id": session.session_id,
                "analysis_plan_id": plan.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "preview_id": "source-intake-plan-preview",
                "preview_hash": "source-intake-preview-hash",
                "result_review_record_ref": result_review["review_record_ref"],
                "package_review_preview_hash": package_preview["package_review_preview_hash"],
                "construction_basis_hash": package_construction["construction_basis_hash"],
                "reconciliation_record_id": package_construction["reconciliation_record_id"],
                "package_review_submit_record_ref": "source-intake-package-review-submit-missing",
                "package_review_state": "package_review_approved",
                "package_review_submit_schema_id": "layer3.source_intake_package_review_submit.v1",
                "handoff_target": "internal_export_envelope",
                "export_mode": "prepare_only",
                "operator_decision": "authorize_prepare",
                "output_package_ids": package_construction["output_package_ids"],
                "payload_refs": package_construction["payload_refs"],
                "payload_hashes": package_construction["payload_hashes"],
            },
        )
    assert handoff_export_not_admitted.value.error_code == "handoff_export_prepare_requires_approved_package_review"

    with pytest.raises(Layer3WorkbenchError) as package_review_submit_mismatched_construction:
        layer3_workbench.package_review_submit(
            db_session,
            {
                "client_request_id": "source-intake-package-review-submit-construction-mismatch",
                "session_id": session.session_id,
                "analysis_plan_id": plan.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "preview_id": "source-intake-plan-preview",
                "preview_hash": "source-intake-preview-hash",
                "result_review_record_ref": result_review["review_record_ref"],
                "package_review_preview_hash": package_preview["package_review_preview_hash"],
                "construction_basis_hash": "source-intake-construction-basis-mismatch",
                "reconciliation_record_id": package_construction["reconciliation_record_id"],
                "output_package_ids": package_construction["output_package_ids"],
                "payload_refs": package_construction["payload_refs"],
                "payload_hashes": package_construction["payload_hashes"],
                "operator_decision": "approved",
            },
        )
    assert (
        package_review_submit_mismatched_construction.value.error_code
        == "source_intake_package_review_submit_construction_basis_mismatch"
    )

    package_review_submit = layer3_workbench.package_review_submit(
        db_session,
        {
            "client_request_id": "source-intake-package-review-submit-approved",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "construction_basis_hash": package_construction["construction_basis_hash"],
            "reconciliation_record_id": package_construction["reconciliation_record_id"],
            "output_package_ids": package_construction["output_package_ids"],
            "payload_refs": package_construction["payload_refs"],
            "payload_hashes": package_construction["payload_hashes"],
            "operator_decision": "approved",
        },
    )
    assert package_review_submit["status"] == "submitted"
    assert package_review_submit["schema_id"] == "layer3.source_intake_package_review_submit.v1"
    assert package_review_submit["analysis_run_id"] is None
    assert package_review_submit["source_intake_record_id"] == "src-intake-plan-001"
    assert package_review_submit["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert package_review_submit["output_payload_hash"] == output_payload["output_hash"]
    assert package_review_submit["package_review_state"] == "package_review_approved"
    assert package_review_submit["package_review_submit_enabled"] is False
    assert package_review_submit["handoff_enabled"] is False
    assert "handoff" in package_review_submit["downstream_unavailable"]
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(L3OutputPackage).count() == 3
    assert db_session.query(L3ReconciliationRecord).count() == 1

    package_review_submit_replay = layer3_workbench.package_review_submit(
        db_session,
        {
            "client_request_id": "source-intake-package-review-submit-approved",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "construction_basis_hash": package_construction["construction_basis_hash"],
            "reconciliation_record_id": package_construction["reconciliation_record_id"],
            "output_package_ids": package_construction["output_package_ids"],
            "payload_refs": package_construction["payload_refs"],
            "payload_hashes": package_construction["payload_hashes"],
            "operator_decision": "approved",
        },
    )
    assert package_review_submit_replay["status"] == "already_submitted"
    assert package_review_submit_replay["submit_record_ref"] == package_review_submit["submit_record_ref"]

    with pytest.raises(Layer3WorkbenchError) as handoff_export_mismatched_construction:
        layer3_workbench.handoff_export_prepare(
            db_session,
            {
                "client_request_id": "source-intake-handoff-export-construction-mismatch",
                "session_id": session.session_id,
                "analysis_plan_id": plan.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "preview_id": "source-intake-plan-preview",
                "preview_hash": "source-intake-preview-hash",
                "result_review_record_ref": result_review["review_record_ref"],
                "package_review_preview_hash": package_preview["package_review_preview_hash"],
                "construction_basis_hash": "source-intake-handoff-construction-mismatch",
                "reconciliation_record_id": package_construction["reconciliation_record_id"],
                "package_review_submit_record_ref": package_review_submit["submit_record_ref"],
                "package_review_state": package_review_submit["package_review_state"],
                "package_review_submit_schema_id": package_review_submit["schema_id"],
                "handoff_target": "internal_export_envelope",
                "export_mode": "prepare_only",
                "operator_decision": "authorize_prepare",
                "output_package_ids": package_construction["output_package_ids"],
                "payload_refs": package_construction["payload_refs"],
                "payload_hashes": package_construction["payload_hashes"],
            },
        )
    assert (
        handoff_export_mismatched_construction.value.error_code
        == "source_intake_handoff_export_prepare_construction_basis_mismatch"
    )

    handoff_export = layer3_workbench.handoff_export_prepare(
        db_session,
        {
            "client_request_id": "source-intake-handoff-export-prepare",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "construction_basis_hash": package_construction["construction_basis_hash"],
            "reconciliation_record_id": package_construction["reconciliation_record_id"],
            "package_review_submit_record_ref": package_review_submit["submit_record_ref"],
            "package_review_state": package_review_submit["package_review_state"],
            "package_review_submit_schema_id": package_review_submit["schema_id"],
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "operator_decision": "authorize_prepare",
            "output_package_ids": package_construction["output_package_ids"],
            "payload_refs": package_construction["payload_refs"],
            "payload_hashes": package_construction["payload_hashes"],
        },
    )
    assert handoff_export["status"] == "prepared"
    assert handoff_export["schema_id"] == "layer3.source_intake_handoff_export_prepare.v1"
    assert handoff_export["analysis_run_id"] is None
    assert handoff_export["source_intake_record_id"] == "src-intake-plan-001"
    assert handoff_export["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert handoff_export["output_payload_hash"] == output_payload["output_hash"]
    assert handoff_export["package_review_submit_schema_id"] == "layer3.source_intake_package_review_submit.v1"
    assert handoff_export["handoff_export_state"] == "handoff_export_prepared"
    assert handoff_export["handoff_export_envelope"]["external_handoff_enabled"] is False
    assert handoff_export["aps_handoff_enabled"] is False
    assert handoff_export["external_export_download_enabled"] is False
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(L3OutputPackage).count() == 3
    assert db_session.query(L3ReconciliationRecord).count() == 1

    handoff_export_replay = layer3_workbench.handoff_export_prepare(
        db_session,
        {
            "client_request_id": "source-intake-handoff-export-prepare",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "construction_basis_hash": package_construction["construction_basis_hash"],
            "reconciliation_record_id": package_construction["reconciliation_record_id"],
            "package_review_submit_record_ref": package_review_submit["submit_record_ref"],
            "package_review_state": package_review_submit["package_review_state"],
            "package_review_submit_schema_id": package_review_submit["schema_id"],
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "operator_decision": "authorize_prepare",
            "output_package_ids": package_construction["output_package_ids"],
            "payload_refs": package_construction["payload_refs"],
            "payload_hashes": package_construction["payload_hashes"],
        },
    )
    assert handoff_export_replay["status"] == "already_prepared"
    assert handoff_export_replay["prepare_record_ref"] == handoff_export["prepare_record_ref"]

    original_payload_refs_by_kind = dict(zip(package_construction["package_kinds"], package_construction["payload_refs"]))
    original_payload_hashes_by_kind = dict(zip(package_construction["package_kinds"], package_construction["payload_hashes"]))

    monkeypatch.setattr(
        layer3_workbench,
        "check_aps_handoff_compatibility",
        lambda db, *, session_id: type("Compat", (), {"compatible": True, "blocked_reason": None})(),
    )

    def fake_materialize_aps_handoff(db, *, session_id):
        bundle_ref = Path(settings.storage_dir) / "source-intake-aps-bundle.json"
        bundle_ref.write_text(json.dumps({"bundle_id": "source-intake-aps-bundle"}), encoding="utf-8")
        output_package = L3OutputPackage(
            output_package_id="source-intake-aps-output-package",
            session_id=session_id,
            reconciliation_record_id=package_construction["reconciliation_record_id"],
            package_kind="aps_evidence_bundle_handoff",
            status="complete",
            payload_ref=str(bundle_ref),
            payload_hash=hashlib.sha256(bundle_ref.read_bytes()).hexdigest(),
            summary_json={
                "bundle_id": "source-intake-aps-bundle",
                "aps_schema_id": "layer3.aps_evidence_bundle_handoff.v1",
            },
        )
        db.add(output_package)
        db.flush()
        return type("ApsResult", (), {"output_package": output_package, "bundle_payload": {}})()

    monkeypatch.setattr(layer3_workbench, "materialize_aps_handoff", fake_materialize_aps_handoff)

    with pytest.raises(Layer3WorkbenchError) as aps_handoff_prepare_ref_mismatch:
        layer3_workbench.aps_handoff_dispatch(
            db_session,
            {
                "client_request_id": "source-intake-aps-handoff-prepare-mismatch",
                "session_id": session.session_id,
                "analysis_plan_id": plan.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "preview_id": "source-intake-plan-preview",
                "preview_hash": "source-intake-preview-hash",
                "result_review_record_ref": result_review["review_record_ref"],
                "package_review_preview_hash": package_preview["package_review_preview_hash"],
                "reconciliation_record_id": package_construction["reconciliation_record_id"],
                "package_review_submit_record_ref": package_review_submit["submit_record_ref"],
                "package_review_state": package_review_submit["package_review_state"],
                "prepare_record_ref": "source-intake-prepare-ref-mismatch",
                "handoff_export_state": handoff_export["handoff_export_state"],
                "handoff_export_envelope_ref": handoff_export["handoff_export_envelope"]["envelope_ref"],
                "handoff_target": "internal_export_envelope",
                "export_mode": "prepare_only",
                "aps_handoff_target": "aps_evidence_bundle",
                "dispatch_mode": "server_side_aps_handoff",
                "operator_decision": "dispatch_aps_handoff",
                "output_package_ids": package_construction["output_package_ids"],
                "package_kinds": package_construction["package_kinds"],
                "payload_refs": package_construction["payload_refs"],
                "payload_hashes": package_construction["payload_hashes"],
            },
        )
    assert aps_handoff_prepare_ref_mismatch.value.error_code == "aps_handoff_dispatch_prepare_ref_mismatch"

    aps_handoff = layer3_workbench.aps_handoff_dispatch(
        db_session,
        {
            "client_request_id": "source-intake-aps-handoff-dispatch",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "reconciliation_record_id": package_construction["reconciliation_record_id"],
            "package_review_submit_record_ref": package_review_submit["submit_record_ref"],
            "package_review_state": package_review_submit["package_review_state"],
            "prepare_record_ref": handoff_export["prepare_record_ref"],
            "handoff_export_state": handoff_export["handoff_export_state"],
            "handoff_export_envelope_ref": handoff_export["handoff_export_envelope"]["envelope_ref"],
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "aps_handoff_target": "aps_evidence_bundle",
            "dispatch_mode": "server_side_aps_handoff",
            "operator_decision": "dispatch_aps_handoff",
            "output_package_ids": package_construction["output_package_ids"],
            "package_kinds": package_construction["package_kinds"],
            "payload_refs": package_construction["payload_refs"],
            "payload_hashes": package_construction["payload_hashes"],
        },
    )
    assert aps_handoff["status"] == "dispatched"
    assert aps_handoff["schema_id"] == "layer3.source_intake_aps_handoff_dispatch.v1"
    assert aps_handoff["analysis_run_id"] is None
    assert aps_handoff["source_intake_record_id"] == "src-intake-plan-001"
    assert aps_handoff["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert aps_handoff["output_payload_hash"] == output_payload["output_hash"]
    assert aps_handoff["package_review_submit_schema_id"] == "layer3.source_intake_package_review_submit.v1"
    assert aps_handoff["aps_handoff_state"] == "aps_handoff_dispatched"
    assert aps_handoff["aps_output_package_kind"] == "aps_evidence_bundle_handoff"
    assert aps_handoff["external_export_enabled"] is False
    assert aps_handoff["download_enabled"] is False
    assert aps_handoff["connector_dispatch_enabled"] is False
    assert aps_handoff["next_allowed_actions"] == []
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(L3OutputPackage).count() == 4
    assert db_session.query(L3ReconciliationRecord).count() == 1
    source_packages_after_dispatch = [
        package
        for package in db_session.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        if package.package_kind != "aps_evidence_bundle_handoff"
    ]
    assert {package.package_kind: package.payload_ref for package in source_packages_after_dispatch} == original_payload_refs_by_kind
    assert {package.package_kind: package.payload_hash for package in source_packages_after_dispatch} == original_payload_hashes_by_kind

    aps_handoff_replay = layer3_workbench.aps_handoff_dispatch(
        db_session,
        {
            "client_request_id": "source-intake-aps-handoff-dispatch",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "reconciliation_record_id": package_construction["reconciliation_record_id"],
            "package_review_submit_record_ref": package_review_submit["submit_record_ref"],
            "package_review_state": package_review_submit["package_review_state"],
            "prepare_record_ref": handoff_export["prepare_record_ref"],
            "handoff_export_state": handoff_export["handoff_export_state"],
            "handoff_export_envelope_ref": handoff_export["handoff_export_envelope"]["envelope_ref"],
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "aps_handoff_target": "aps_evidence_bundle",
            "dispatch_mode": "server_side_aps_handoff",
            "operator_decision": "dispatch_aps_handoff",
            "output_package_ids": package_construction["output_package_ids"],
            "package_kinds": package_construction["package_kinds"],
            "payload_refs": package_construction["payload_refs"],
            "payload_hashes": package_construction["payload_hashes"],
        },
    )
    assert aps_handoff_replay["status"] == "already_dispatched"
    assert aps_handoff_replay["aps_handoff_record_ref"] == aps_handoff["aps_handoff_record_ref"]

    with pytest.raises(Layer3WorkbenchError) as external_export_dispatch_ref_mismatch:
        layer3_workbench.external_export_download_prepare(
            db_session,
            {
                "client_request_id": "source-intake-external-export-dispatch-mismatch",
                "session_id": session.session_id,
                "analysis_plan_id": plan.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "preview_id": "source-intake-plan-preview",
                "preview_hash": "source-intake-preview-hash",
                "result_review_record_ref": result_review["review_record_ref"],
                "package_review_preview_hash": package_preview["package_review_preview_hash"],
                "reconciliation_record_id": package_construction["reconciliation_record_id"],
                "package_review_submit_record_ref": package_review_submit["submit_record_ref"],
                "package_review_state": package_review_submit["package_review_state"],
                "prepare_record_ref": handoff_export["prepare_record_ref"],
                "handoff_export_state": handoff_export["handoff_export_state"],
                "handoff_export_envelope_ref": handoff_export["handoff_export_envelope"]["envelope_ref"],
                "handoff_target": "internal_export_envelope",
                "export_mode": "prepare_only",
                "aps_handoff_record_ref": "source-intake-aps-dispatch-ref-mismatch",
                "aps_handoff_state": aps_handoff["aps_handoff_state"],
                "aps_handoff_target": "aps_evidence_bundle",
                "dispatch_mode": "server_side_aps_handoff",
                "aps_output_package_id": aps_handoff["aps_output_package_id"],
                "aps_output_package_kind": aps_handoff["aps_output_package_kind"],
                "aps_bundle_ref": aps_handoff["aps_bundle_ref"],
                "aps_bundle_id": aps_handoff["aps_bundle_id"],
                "aps_schema_id": aps_handoff["aps_schema_id"],
                "export_download_target": "aps_evidence_bundle_download_reference",
                "download_mode": "reference_only_prepare",
                "operator_decision": "prepare_external_export_download",
                "output_package_ids": package_construction["output_package_ids"],
                "package_kinds": package_construction["package_kinds"],
                "payload_refs": package_construction["payload_refs"],
                "payload_hashes": package_construction["payload_hashes"],
            },
            validate_source_artifact=False,
        )
    assert (
        external_export_dispatch_ref_mismatch.value.error_code
        == "source_intake_external_export_download_prepare_not_admitted"
    )

    external_export = layer3_workbench.external_export_download_prepare(
        db_session,
        {
            "client_request_id": "source-intake-external-export-download",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "reconciliation_record_id": package_construction["reconciliation_record_id"],
            "package_review_submit_record_ref": package_review_submit["submit_record_ref"],
            "package_review_state": package_review_submit["package_review_state"],
            "prepare_record_ref": handoff_export["prepare_record_ref"],
            "handoff_export_state": handoff_export["handoff_export_state"],
            "handoff_export_envelope_ref": handoff_export["handoff_export_envelope"]["envelope_ref"],
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "aps_handoff_record_ref": aps_handoff["aps_handoff_record_ref"],
            "aps_handoff_state": aps_handoff["aps_handoff_state"],
            "aps_handoff_target": "aps_evidence_bundle",
            "dispatch_mode": "server_side_aps_handoff",
            "aps_output_package_id": aps_handoff["aps_output_package_id"],
            "aps_output_package_kind": aps_handoff["aps_output_package_kind"],
            "aps_bundle_ref": aps_handoff["aps_bundle_ref"],
            "aps_bundle_id": aps_handoff["aps_bundle_id"],
            "aps_schema_id": aps_handoff["aps_schema_id"],
            "export_download_target": "aps_evidence_bundle_download_reference",
            "download_mode": "reference_only_prepare",
            "operator_decision": "prepare_external_export_download",
            "output_package_ids": package_construction["output_package_ids"],
            "package_kinds": package_construction["package_kinds"],
            "payload_refs": package_construction["payload_refs"],
            "payload_hashes": package_construction["payload_hashes"],
        },
        validate_source_artifact=False,
    )
    assert external_export["status"] == "prepared"
    assert external_export["schema_id"] == "layer3.source_intake_external_export_download_prepare.v1"
    assert external_export["analysis_run_id"] is None
    assert external_export["source_intake_record_id"] == "src-intake-plan-001"
    assert external_export["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert external_export["output_payload_hash"] == output_payload["output_hash"]
    assert external_export["package_review_submit_schema_id"] == "layer3.source_intake_package_review_submit.v1"
    assert external_export["external_export_download_state"] == "external_export_download_prepared"
    assert external_export["aps_handoff_record_ref"] == aps_handoff["aps_handoff_record_ref"]
    assert external_export["aps_output_package_id"] == aps_handoff["aps_output_package_id"]
    assert external_export["aps_bundle_ref"] == aps_handoff["aps_bundle_ref"]
    assert external_export["browser_download_enabled"] is False
    assert external_export["download_url_enabled"] is False
    assert external_export["connector_dispatch_enabled"] is False
    assert external_export["destination_selection_enabled"] is False
    assert external_export["generic_downstream_dispatch_enabled"] is False
    assert external_export["delivery_ui"]["available"] is True
    assert external_export["delivery_ui"]["state"] == "source_intake_external_export_download_delivery_ui_ready"
    assert "external_export_download_descriptor" in external_export
    external_export_session_summary = layer3_workbench.session_summary(db_session, session.session_id)
    assert (
        external_export_session_summary["external_export_download"]["schema_id"]
        == "layer3.source_intake_external_export_download_prepare.v1"
    )
    assert external_export_session_summary["external_export_download"]["source_intake_record_id"] == "src-intake-plan-001"
    assert external_export_session_summary["external_export_download"]["delivery_ui"]["available"] is True

    from app.services import nrc_aps_evidence_bundle

    monkeypatch.setattr(
        nrc_aps_evidence_bundle,
        "load_persisted_bundle_artifact",
        lambda bundle_ref: (json.loads(Path(bundle_ref).read_text(encoding="utf-8")), Path(bundle_ref)),
    )
    source_intake_delivery_payload = {
        "client_request_id": "source-intake-external-export-download-delivery",
        "session_id": session.session_id,
        "analysis_plan_id": plan.analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "preview_id": "source-intake-plan-preview",
        "preview_hash": "source-intake-preview-hash",
        "result_review_record_ref": result_review["review_record_ref"],
        "package_review_preview_hash": package_preview["package_review_preview_hash"],
        "reconciliation_record_id": package_construction["reconciliation_record_id"],
        "package_review_submit_record_ref": package_review_submit["submit_record_ref"],
        "package_review_state": package_review_submit["package_review_state"],
        "prepare_record_ref": handoff_export["prepare_record_ref"],
        "handoff_export_state": handoff_export["handoff_export_state"],
        "handoff_export_envelope_ref": handoff_export["handoff_export_envelope"]["envelope_ref"],
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "aps_handoff_record_ref": aps_handoff["aps_handoff_record_ref"],
        "aps_handoff_state": aps_handoff["aps_handoff_state"],
        "aps_handoff_target": "aps_evidence_bundle",
        "dispatch_mode": "server_side_aps_handoff",
        "aps_output_package_id": aps_handoff["aps_output_package_id"],
        "aps_output_package_kind": aps_handoff["aps_output_package_kind"],
        "aps_bundle_ref": external_export["aps_bundle_ref"],
        "aps_bundle_id": external_export["aps_bundle_id"],
        "aps_schema_id": external_export["aps_schema_id"],
        "external_export_download_record_ref": external_export["external_export_download_record_ref"],
        "export_download_descriptor_ref": external_export["export_download_descriptor_ref"],
        "external_export_download_state": external_export["external_export_download_state"],
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "delivery_mode": "same_origin_artifact_stream",
        "operator_decision": "deliver_external_export_download",
        "output_package_ids": package_construction["output_package_ids"],
        "package_kinds": package_construction["package_kinds"],
        "payload_refs": package_construction["payload_refs"],
        "payload_hashes": package_construction["payload_hashes"],
    }
    source_intake_delivery = layer3_workbench.external_export_download_deliver(
        db_session,
        source_intake_delivery_payload,
    )
    assert source_intake_delivery.media_type == "application/json"
    assert source_intake_delivery.artifact_path == Path(external_export["aps_bundle_ref"])
    assert (
        source_intake_delivery.headers["X-Layer3-Schema-Id"]
        == "layer3.source_intake_external_export_download_delivery.v1"
    )
    assert source_intake_delivery.headers["X-Layer3-Delivery-State"] == "external_export_download_delivered"
    assert (
        source_intake_delivery.headers["X-Layer3-External-Export-Download-Record-Ref"]
        == external_export["external_export_download_record_ref"]
    )
    assert source_intake_delivery.authority["schema_id"] == "layer3.source_intake_external_export_download_prepare.v1"
    assert source_intake_delivery.authority["analysis_run_id"] is None
    assert source_intake_delivery.authority["source_intake_record_id"] == "src-intake-plan-001"
    assert source_intake_delivery.authority["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert source_intake_delivery.authority["source_artifact_hash"] == external_export["source_artifact_hash"]
    assert source_intake_delivery.authority["output_payload_hash"] == output_payload["output_hash"]

    monkeypatch.setenv("LAYER3_SIGNED_REFERENCE_SECRET", "source-intake-signed-reference-secret")
    source_intake_signed_reference = layer3_workbench.external_export_download_generate_signed_reference(
        db_session,
        {
            **source_intake_delivery_payload,
            "client_request_id": "source-intake-external-export-download-signed-reference",
        },
        now_epoch=1_800_000_000,
    )
    assert source_intake_signed_reference["schema_id"] == "layer3.external_export_download_signed_reference.v1"
    assert (
        source_intake_signed_reference["signed_reference_state"]
        == "external_export_download_signed_reference_ready"
    )
    assert source_intake_signed_reference["delivery_mode"] == "same_origin_signed_delivery_reference"
    assert (
        source_intake_signed_reference["server_authority"]
        == "source_intake_external_export_download_signed_reference_gate"
    )
    assert source_intake_signed_reference["analysis_run_id"] is None
    assert source_intake_signed_reference["source_intake_record_id"] == "src-intake-plan-001"
    assert source_intake_signed_reference["candidate_id"] == "mat-source_intake_record-src-intake-plan-001"
    assert source_intake_signed_reference["output_payload_hash"] == output_payload["output_hash"]
    assert source_intake_signed_reference["source_artifact_hash"] == external_export["source_artifact_hash"]
    assert source_intake_signed_reference["source_artifact_size_bytes"] == Path(
        external_export["aps_bundle_ref"]
    ).stat().st_size
    source_intake_signed_reference_use = layer3_workbench.external_export_download_use_signed_reference(
        db_session,
        {"signed_reference_token": source_intake_signed_reference["signed_reference_token"]},
        now_epoch=1_800_000_001,
    )
    assert source_intake_signed_reference_use.artifact_path == Path(external_export["aps_bundle_ref"])
    assert (
        source_intake_signed_reference_use.headers["X-Layer3-Schema-Id"]
        == "layer3.external_export_download_signed_reference_use.v1"
    )
    assert (
        source_intake_signed_reference_use.headers["X-Layer3-Signed-Reference-State"]
        == "external_export_download_signed_reference_delivered"
    )
    assert source_intake_signed_reference_use.authority["analysis_run_id"] is None
    assert source_intake_signed_reference_use.authority["source_intake_record_id"] == "src-intake-plan-001"
    assert (
        source_intake_signed_reference_use.authority["candidate_id"]
        == "mat-source_intake_record-src-intake-plan-001"
    )
    source_intake_provider_private_payload = {
        "client_request_id": "source-intake-provider-private-signed-url-prepare",
        "session_id": session.session_id,
        "analysis_plan_id": plan.analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "reconciliation_record_id": package_construction["reconciliation_record_id"],
        "external_export_download_record_ref": external_export["external_export_download_record_ref"],
        "export_download_descriptor_ref": external_export["export_download_descriptor_ref"],
        "external_export_download_state": external_export["external_export_download_state"],
        "export_download_target": "aps_evidence_bundle_download_reference",
        "download_mode": "reference_only_prepare",
        "delivery_mode": "provider_private_signed_url",
        "operator_decision": "prepare_provider_private_signed_url",
        "source_artifact_hash": external_export["source_artifact_hash"],
        "source_artifact_size_bytes": Path(external_export["aps_bundle_ref"]).stat().st_size,
        "recipient_scope": "external_downstream_recipient_private_artifact_delivery",
        "requested_ttl_seconds": 300,
        "signed_reference_receipt_id": source_intake_signed_reference_use.headers[
            "X-Layer3-Signed-Reference-Receipt-Id"
        ],
    }
    source_intake_provider_private = layer3_provider_private_signed_url.provider_private_signed_url_prepare(
        db_session,
        source_intake_provider_private_payload,
        now_epoch=1_800_000_002,
    )
    assert source_intake_provider_private["schema_id"] == "layer3.provider_private_signed_url.prepare.v1"
    assert source_intake_provider_private["provider_signed_url_state"] == "provider_private_signed_url_prepared"
    assert source_intake_provider_private["delivery_mode"] == "provider_private_signed_url"
    assert source_intake_provider_private["provider_url_redacted"] == "provider-private-signed-url:redacted"
    assert source_intake_provider_private["authority_rail"]["provider_network_enabled"] is False
    assert source_intake_provider_private["authority_rail"]["provider_object_write_enabled"] is False
    assert source_intake_provider_private["authority_rail"]["public_url_enabled"] is False
    assert source_intake_provider_private["source_artifact_hash"] == external_export["source_artifact_hash"]
    source_intake_provider_status = layer3_provider_private_signed_url.provider_private_signed_url_status(
        db_session,
        source_intake_provider_private["provider_signed_url_receipt_id"],
        now_epoch=1_800_000_003,
    )
    assert source_intake_provider_status["schema_id"] == "layer3.provider_private_signed_url.status.v1"
    assert source_intake_provider_status["provider_signed_url_state"] == "provider_private_signed_url_prepared"
    source_intake_provider_revoke = layer3_provider_private_signed_url.provider_private_signed_url_revoke(
        db_session,
        {
            "client_request_id": "source-intake-provider-private-signed-url-revoke",
            "provider_signed_url_receipt_id": source_intake_provider_private["provider_signed_url_receipt_id"],
            "idempotency_key": "source-intake-provider-private-signed-url-revoke",
            "revoked_by": "layer3-workbench-test",
            "revocation_reason": "operator requested stop",
            "operator_decision": "revoke_provider_private_signed_url",
        },
        now_epoch=1_800_000_004,
    )
    assert source_intake_provider_revoke["schema_id"] == "layer3.provider_private_signed_url.revoke.v1"
    assert source_intake_provider_revoke["provider_signed_url_state"] == "provider_private_signed_url_revoked"
    assert db_session.query(L3ProviderPrivateSignedUrlObjectAuthority).count() == 1
    assert db_session.query(L3ProviderPrivateSignedUrlReceipt).count() == 1
    assert db_session.query(L3ProviderPrivateSignedUrlAuditEvent).count() == 2
    assert db_session.query(L3ProviderPrivateSignedUrlRevocation).count() == 1

    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(L3OutputPackage).count() == 4
    assert db_session.query(L3ReconciliationRecord).count() == 1
    source_packages_after_external_export = [
        package
        for package in db_session.query(L3OutputPackage).order_by(L3OutputPackage.package_kind.asc()).all()
        if package.package_kind != "aps_evidence_bundle_handoff"
    ]
    assert {
        package.package_kind: package.payload_ref for package in source_packages_after_external_export
    } == original_payload_refs_by_kind
    assert {
        package.package_kind: package.payload_hash for package in source_packages_after_external_export
    } == original_payload_hashes_by_kind

    external_export_replay = layer3_workbench.external_export_download_prepare(
        db_session,
        {
            "client_request_id": "source-intake-external-export-download",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "result_review_record_ref": result_review["review_record_ref"],
            "package_review_preview_hash": package_preview["package_review_preview_hash"],
            "reconciliation_record_id": package_construction["reconciliation_record_id"],
            "package_review_submit_record_ref": package_review_submit["submit_record_ref"],
            "package_review_state": package_review_submit["package_review_state"],
            "prepare_record_ref": handoff_export["prepare_record_ref"],
            "handoff_export_state": handoff_export["handoff_export_state"],
            "handoff_export_envelope_ref": handoff_export["handoff_export_envelope"]["envelope_ref"],
            "handoff_target": "internal_export_envelope",
            "export_mode": "prepare_only",
            "aps_handoff_record_ref": aps_handoff["aps_handoff_record_ref"],
            "aps_handoff_state": aps_handoff["aps_handoff_state"],
            "aps_handoff_target": "aps_evidence_bundle",
            "dispatch_mode": "server_side_aps_handoff",
            "aps_output_package_id": aps_handoff["aps_output_package_id"],
            "aps_output_package_kind": aps_handoff["aps_output_package_kind"],
            "aps_bundle_ref": aps_handoff["aps_bundle_ref"],
            "aps_bundle_id": aps_handoff["aps_bundle_id"],
            "aps_schema_id": aps_handoff["aps_schema_id"],
            "export_download_target": "aps_evidence_bundle_download_reference",
            "download_mode": "reference_only_prepare",
            "operator_decision": "prepare_external_export_download",
            "output_package_ids": package_construction["output_package_ids"],
            "package_kinds": package_construction["package_kinds"],
            "payload_refs": package_construction["payload_refs"],
            "payload_hashes": package_construction["payload_hashes"],
        },
        validate_source_artifact=False,
    )
    assert external_export_replay["status"] == "already_prepared"
    assert (
        external_export_replay["external_export_download_record_ref"]
        == external_export["external_export_download_record_ref"]
    )


    pass_run.summary_json = {**(pass_run.summary_json or {}), "analysis_run_id": "unexpected-analysis-run"}
    db_session.commit()
    with pytest.raises(Layer3WorkbenchError) as package_preview_analysis_run_blocked:
        layer3_workbench.package_review_preview(
            db_session,
            {
                "client_request_id": "source-intake-package-preview-analysis-run-blocked",
                "session_id": session.session_id,
                "analysis_plan_id": plan.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "preview_id": "source-intake-plan-preview",
                "preview_hash": "source-intake-preview-hash",
                "result_review_record_ref": result_review["review_record_ref"],
            },
        )
    assert (
        package_preview_analysis_run_blocked.value.error_code
        == "source_intake_execution_result_status_analysis_run_not_admitted"
    )
    pass_run.summary_json = {
        key: value for key, value in (pass_run.summary_json or {}).items() if key != "analysis_run_id"
    }
    db_session.commit()

    with pytest.raises(Layer3WorkbenchError) as duplicate_review_blocked:
        layer3_workbench.execution_result_review(
            db_session,
            {
                "client_request_id": "source-intake-result-review-blocked",
                "session_id": session.session_id,
                "analysis_plan_id": plan.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "preview_id": "source-intake-plan-preview",
                "preview_hash": "source-intake-preview-hash",
                "operator_decision": "approved",
            },
        )
    assert duplicate_review_blocked.value.error_code == "execution_result_review_already_recorded"

    original_summary = pass_run.summary_json
    pass_run.summary_json = {**original_summary, "analysis_run_id": "unexpected-analysis-run"}
    db_session.commit()
    with pytest.raises(Layer3WorkbenchError) as analysis_run_blocked:
        layer3_workbench.execution_result_status(
            db_session,
            {
                "client_request_id": "source-intake-result-status-analysis-run",
                "session_id": session.session_id,
                "analysis_plan_id": plan.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "preview_id": "source-intake-plan-preview",
                "preview_hash": "source-intake-preview-hash",
                "operator_view_mode": "status_only",
            },
        )
    assert analysis_run_blocked.value.error_code == "source_intake_execution_result_status_analysis_run_not_admitted"
    pass_run.summary_json = original_summary
    db_session.commit()

    original_output_ref = pass_run.output_payload_ref
    pass_run.output_payload_ref = None
    db_session.commit()
    missing_status = layer3_workbench.execution_result_status(
        db_session,
        {
            "client_request_id": "source-intake-result-status-missing-output",
            "session_id": session.session_id,
            "analysis_plan_id": plan.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "preview_id": "source-intake-plan-preview",
            "preview_hash": "source-intake-preview-hash",
            "operator_view_mode": "status_only",
        },
    )
    assert missing_status["status"] == "missing_output_metadata"
    assert missing_status["result_status_available"] is False
    assert missing_status["output_metadata_error"] == "output_payload_ref_missing"

    pass_run.output_payload_ref = original_output_ref
    tampered_payload = json.loads(Path(original_output_ref).read_text(encoding="utf-8"))
    tampered_payload["source_identity"]["source_label"] = "Tampered source label"
    Path(original_output_ref).write_text(json.dumps(tampered_payload), encoding="utf-8")
    db_session.commit()
    with pytest.raises(Layer3WorkbenchError) as mismatched_output:
        layer3_workbench.execution_result_status(
            db_session,
            {
                "client_request_id": "source-intake-result-status-mismatch",
                "session_id": session.session_id,
                "analysis_plan_id": plan.analysis_plan_id,
                "pass_run_id": pass_run.pass_run_id,
                "preview_id": "source-intake-plan-preview",
                "preview_hash": "source-intake-preview-hash",
                "operator_view_mode": "status_only",
            },
        )
    assert mismatched_output.value.error_code == "source_intake_execution_result_status_output_not_admitted"
    assert "output_hash" in mismatched_output.value.blocked_fields


def _gate_b_payload(preflight: dict, source: dict, material: dict) -> dict:
    candidates = material["material_candidates"]
    first, second = candidates
    return {
        "client_request_id": "req-gate-b",
        "preflight_id": preflight["preflight_id"],
        "source_set_id": source["source_set_id"],
        "material_preview_id": material["material_preview_id"],
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
                "decision": "flagged",
                "operator_reason": "Held for second-slice review.",
                "decision_basis": {
                    "source_ref": second["source_ref"],
                    "query_basis": second["query_basis"],
                    "provenance_ref": second["provenance_ref"],
                },
            },
        ],
        "commit_reason": "pytest_gate_b",
        "actor": "pytest",
    }


def _seed_aps_derived_dataset_version(
    db,
    tmp_path: Path,
    *,
    dataset_version_id: str = "dv-aps-csv-001",
    parser_family: str = "csv_table",
    typed_content_contract_id: str = "aps_csv_table_units_v1",
    source_system: str = "nrc_adams_aps",
    source_mode: str = "artifact_csv_parser",
    artifact_locator_type: str | None = None,
    fetch_policy_mode: str | None = None,
    parser_contract_id: str = "aps_csv_parser_v1",
) -> str:
    dataset_id = f"ds-{dataset_version_id}"
    dataset = Dataset(
        dataset_id=dataset_id,
        name="APS CSV bridge dataset",
        description="APS-derived CSV dataset for Layer 3 workbench proof",
        frequency_hint="MS",
        time_column="observed_at",
    )
    version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        dataset_id=dataset_id,
        version_label="table-0",
        version_type="aps_csv_bridge",
        status="ready",
        notes="aps_csv_bridge_contract_id=aps_csv_dataset_bridge_v1",
        row_count=3,
    )
    observed_at = VariableDefinition(
        variable_id="var-time-aps-csv-001",
        dataset_version_id=dataset_version_id,
        variable_name="observed_at",
        dtype="datetime64[ns]",
        role="time_index",
        is_numeric=False,
        is_time_index=True,
        ordinal_position=0,
    )
    value = VariableDefinition(
        variable_id="var-value-aps-csv-001",
        dataset_version_id=dataset_version_id,
        variable_name="value",
        dtype="float64",
        role="measure",
        is_numeric=True,
        is_time_index=False,
        ordinal_position=1,
    )
    dataset_dir = tmp_path / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / f"{dataset_version_id}.csv"
    csv_path.write_text(
        "observed_at,value\n2025-01-01,1.0\n2025-02-01,2.5\n2025-03-01,3.0\n",
        encoding="utf-8",
    )
    version.storage_ref = str(csv_path)
    provenance = DatasetSourceProvenance(
        dataset_version_id=dataset_version_id,
        connector_run_id=None,
        source_system=source_system,
        source_mode=source_mode,
        source_artifact_key="aps-target-artifacts/run-001/target-001/extraction.json",
        sciencebase_file_name="fixture.csv",
        downloaded_sha256="0" * 64,
        raw_storage_ref="aps-target-artifacts/run-001/target-001/blob.csv",
        artifact_locator_type=artifact_locator_type,
        fetch_policy_mode=fetch_policy_mode,
        source_reference_json={
            "target_id": "target-001",
            "accession_number": "ML000000001",
            "table_index": 0,
            "table_hash": "hash-table-001",
            "parser_family": parser_family,
            "parser_contract_id": parser_contract_id,
            "typed_content_contract_id": typed_content_contract_id,
            "diagnostics_ref": "aps-target-artifacts/run-001/target-001/diagnostics.json",
        },
    )
    db.add_all([dataset, version, observed_at, value, provenance])
    db.flush()
    return dataset_version_id


def _seed_aps_content_document(
    db,
    tmp_path: Path,
    *,
    content_id: str = "content-layer3-doc-001",
    run_id: str = "run-layer3-doc-001",
    target_id: str = "target-layer3-doc-001",
) -> str:
    content_contract_id = "aps_pdf_content_units_v1"
    chunking_contract_id = "aps_pdf_chunking_v1"
    normalization_contract_id = "aps_pdf_normalization_v1"
    artifact_root = tmp_path / "aps"
    artifact_root.mkdir(parents=True, exist_ok=True)
    chunk_texts = [
        "Inspection findings confirm stable cooling performance.",
        "No safety-significant degradation was identified during the interval.",
    ]
    normalized_text = "\n".join(chunk_texts)
    content_units_ref = str(artifact_root / f"{content_id}_content_units.json")
    normalized_text_ref = str(artifact_root / f"{content_id}_normalized.txt")
    blob_ref = str(artifact_root / f"{content_id}.pdf")
    diagnostics_ref = str(artifact_root / f"{content_id}_diagnostics.json")
    Path(content_units_ref).write_text(json.dumps({"content_id": content_id}), encoding="utf-8")
    Path(normalized_text_ref).write_text(normalized_text, encoding="utf-8")
    Path(blob_ref).write_text("pdf-placeholder", encoding="utf-8")
    Path(diagnostics_ref).write_text(json.dumps({"quality_status": "strong"}), encoding="utf-8")

    db.add_all(
        [
            ConnectorRun(connector_run_id=run_id, connector_key="nrc_adams_aps", status="completed"),
            ConnectorRunTarget(
                connector_run_target_id=target_id,
                connector_run_id=run_id,
                status="completed",
                ordinal=0,
            ),
            ApsContentDocument(
                content_id=content_id,
                content_contract_id=content_contract_id,
                chunking_contract_id=chunking_contract_id,
                normalization_contract_id=normalization_contract_id,
                normalized_text_sha256=hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
                normalized_char_count=len(normalized_text),
                chunk_count=len(chunk_texts),
                content_status="indexed",
                media_type="application/pdf",
                document_class="inspection_report",
                quality_status="strong",
                page_count=2,
                diagnostics_ref=diagnostics_ref,
                visual_page_refs_json=json.dumps([]),
            ),
            ApsContentLinkage(
                content_id=content_id,
                run_id=run_id,
                target_id=target_id,
                accession_number="ML26001A001",
                content_contract_id=content_contract_id,
                chunking_contract_id=chunking_contract_id,
                content_units_ref=content_units_ref,
                normalized_text_ref=normalized_text_ref,
                normalized_text_sha256=hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
                blob_ref=blob_ref,
                blob_sha256=hashlib.sha256(Path(blob_ref).read_bytes()).hexdigest(),
                download_exchange_ref="aps/download_exchange.json",
                discovery_ref="aps/discovery.json",
                selection_ref="aps/selection.json",
                diagnostics_ref=diagnostics_ref,
            ),
        ]
    )
    for ordinal, chunk_text in enumerate(chunk_texts):
        db.add(
            ApsContentChunk(
                content_id=content_id,
                chunk_id=f"{content_id}-chunk-{ordinal + 1}",
                content_contract_id=content_contract_id,
                chunking_contract_id=chunking_contract_id,
                chunk_ordinal=ordinal,
                start_char=ordinal * 64,
                end_char=(ordinal * 64) + len(chunk_text),
                chunk_text=chunk_text,
                chunk_text_sha256=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                page_start=ordinal + 1,
                page_end=ordinal + 1,
                unit_kind="pdf_paragraph",
                quality_status="strong",
            )
        )
    db.flush()
    return content_id


def test_bootstrap_is_explicit_about_first_slice_limits() -> None:
    result = layer3_workbench.bootstrap()

    assert result["route"] == "/review/layer3"
    assert result["api_root"] == "/api/v1/layer3"
    assert result["features"]["analysis_execution"] is False
    assert result["features"]["plan_preview"] is True
    assert result["features"]["execution_result_review"] is True
    assert result["features"]["single_aps_doc_qualitative_execution"] is True
    assert result["features"]["broad_qualitative_execution"] is False
    assert result["features"]["rag_vector_retrieval"] is False
    assert result["features"]["typing_override_enabled"] is False
    assert result["unavailable_gate_labels"] == ["plan", "execution", "results", "package"]
    contract = result["state_action_contract"]
    assert contract["schema_id"] == STATE_ACTION_CONTRACT_SCHEMA_ID
    assert contract["gate_labels"] == result["gate_labels"]
    assert contract["active_gate_labels"] == result["active_gate_labels"]
    assert contract["unavailable_gate_labels"] == result["unavailable_gate_labels"]
    assert "gate_b_decision" in contract["action_ids"]
    assert "external_export_download_deliver" in contract["action_ids"]
    assert "rag_vector_retrieval" not in contract["action_ids"]
    authority_matrix = result["authority_matrix_contract"]
    assert authority_matrix["schema_id"] == AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID
    assert authority_matrix["exposure_context"] == AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_CONTEXT
    assert authority_matrix["fail_closed_result"] == AUTHORITY_MATRIX_FAIL_CLOSED_RESULT
    assert authority_matrix["source_contract_ids"] == [
        STATE_ACTION_CONTRACT_SCHEMA_ID,
        contract["state_model_schema_id"],
    ]
    assert {
        "route_api_posture",
        "response_dto_posture",
        "rendered_review_posture",
        "side_effect_policy",
    } <= {row["row"] for row in authority_matrix["authority_matrix"]}
    authority_rows = {row["row"]: row for row in authority_matrix["authority_matrix"]}
    assert (
        authority_rows["workbench_exposure_substrate"]["admission_result"]
        == AUTHORITY_MATRIX_READ_ONLY_EXPOSURE_RESULT
    )
    assert (
        authority_rows["route_api_posture"]["admission_result"]
        == AUTHORITY_MATRIX_EXISTING_ROUTE_RESPONSE_RESULT
    )
    assert authority_rows["route_api_posture"]["blocked_scope"] == ["separate_authority_matrix_route"]
    assert (
        authority_rows["response_dto_posture"]["admission_result"]
        == AUTHORITY_MATRIX_RESPONSE_MODEL_RESULT
    )
    assert result["authority_rail"]["browser_only_state"] == [
        "expanded_rows",
        "hidden_uncommitted_candidates",
        "selected_tab",
    ]


def test_state_action_contract_is_derived_from_state_model_without_admitting_deferred_work() -> None:
    readiness = layer3_workbench.readiness_contract()
    state_model = readiness["state_model"]
    contract = readiness["state_action_contract"]
    authority_matrix = readiness["authority_matrix_contract"]

    assert contract["state_model_schema_id"] == state_model["schema_id"]
    assert contract["authority_order"] == state_model["authority_order"]
    assert contract["state_action_matrix"] == state_model["states"]
    assert contract["state_count"] == len(state_model["states"])
    assert contract["states"] == [state["state"] for state in state_model["states"]]

    derived_action_ids = sorted(
        {
            action
            for state in state_model["states"]
            for action in state["allowed_next_actions"]
        }
    )
    assert contract["action_ids"] == derived_action_ids
    assert contract["decision_sets"]["gate_b"] == ["approved", "denied", "isolated", "flagged"]
    assert contract["decision_sets"]["external_export_download_deliver"] == [
        "deliver_external_export_download"
    ]
    assert contract["decision_sets"]["package_supersession_preview"] == ["preview_package_supersession"]
    assert contract["decision_sets"]["record_replacement_package_set_authority"] == [
        "record_replacement_package_set_authority"
    ]
    assert contract["decision_sets"]["package_supersession_commit"] == ["commit_package_supersession"]
    assert authority_matrix["schema_id"] == AUTHORITY_MATRIX_CONTRACT_SCHEMA_ID
    assert authority_matrix["source_contract_ids"] == [STATE_ACTION_CONTRACT_SCHEMA_ID, state_model["schema_id"]]
    assert authority_matrix["fail_closed_result"] == AUTHORITY_MATRIX_FAIL_CLOSED_RESULT
    blocked_rows = {row["row"]: row for row in authority_matrix["authority_matrix"]}
    assert blocked_rows["route_api_posture"]["admission_result"] == AUTHORITY_MATRIX_EXISTING_ROUTE_RESPONSE_RESULT
    assert blocked_rows["route_api_posture"]["blocked_scope"] == ["separate_authority_matrix_route"]
    assert blocked_rows["response_dto_posture"]["admission_result"] == AUTHORITY_MATRIX_RESPONSE_MODEL_RESULT
    assert set(blocked_rows["response_dto_posture"]["blocked_scope"]) == {
        "schema_model_migration_change",
        "separate_response_dto_module_change",
    }
    assert blocked_rows["rendered_review_posture"]["admission_result"] == AUTHORITY_MATRIX_FAIL_CLOSED_RESULT
    assert "runtime_behavior" in blocked_rows["side_effect_policy"]["blocked_scope"]

    admitted_capabilities = {item["capability"]: item for item in contract["admitted_capabilities"]}
    assert admitted_capabilities["single_aps_doc_qualitative_execution"]["admitted"] is True
    assert (
        admitted_capabilities["single_aps_doc_qualitative_execution"]["source_gate"]
        == "119_L3_QUAL_APS_EXEC_ENTRY_FREEZE"
    )
    assert (
        admitted_capabilities["single_aps_doc_qualitative_execution"]["owner_service"]
        == "backend/app/services/layer3_qual_aps_execution.py"
    )
    assert admitted_capabilities["internal_dispatch_record_only"]["admitted"] is True
    assert admitted_capabilities["internal_dispatch_record_only"]["source_gate"] == "121_CONNECTOR_DISPATCH_ENTRY_FREEZE"
    assert admitted_capabilities["package_supersession_preview_only"]["admitted"] is True
    assert admitted_capabilities["package_supersession_preview_only"]["source_gate"] == "122_PACKAGE_MUTATION_FREEZE"
    assert (
        admitted_capabilities["package_supersession_preview_only"]["owner_service"]
        == "backend/app/services/layer3_package_mutation_entry.py"
    )
    assert admitted_capabilities["replacement_package_set_authority"]["admitted"] is True
    assert (
        admitted_capabilities["replacement_package_set_authority"]["source_gate"]
        == "127_PACKAGE_REPLACEMENT_SET_FREEZE"
    )
    assert (
        admitted_capabilities["replacement_package_set_authority"]["owner_service"]
        == "backend/app/services/layer3_replacement_package_set_authority.py"
    )
    assert admitted_capabilities["package_supersession_commit_entry"]["admitted"] is True
    assert admitted_capabilities["package_supersession_commit_entry"]["source_gate"] == "126_PACKAGE_COMMIT_FREEZE"
    assert (
        admitted_capabilities["package_supersession_commit_entry"]["owner_service"]
        == "backend/app/services/layer3_package_supersession_commit.py"
    )

    deferred_capabilities = {item["capability"]: item for item in contract["deferred_capabilities"]}
    assert "qualitative_execution" not in deferred_capabilities
    assert deferred_capabilities["broad_qualitative_execution"]["admitted"] is False
    assert deferred_capabilities["broad_qualitative_execution"]["reason"] == "single_aps_doc_qualitative_pass_only"
    assert deferred_capabilities["hybrid_execution"]["admitted"] is False
    assert deferred_capabilities["rag_vector_retrieval"]["admitted"] is False
    assert deferred_capabilities["provider_public_url"]["admitted"] is False
    assert deferred_capabilities["connector_destination_dispatch"]["admitted"] is False
    assert deferred_capabilities["package_mutation_reconstruction"]["admitted"] is False
    assert deferred_capabilities["auth_security_hardening"]["reason"] == "deferred_by_operator_instruction"
    assert not set(deferred_capabilities).intersection(contract["action_ids"])
    assert not set(admitted_capabilities).intersection(contract["action_ids"])


def test_preflight_fails_closed_on_missing_intent_and_unsupported_sources() -> None:
    with pytest.raises(Layer3WorkbenchError) as empty:
        layer3_workbench.preflight({"natural_language_intent": " "})
    assert empty.value.error_code == "empty_intent"
    assert empty.value.status == "blocked"

    with pytest.raises(Layer3WorkbenchError) as unsupported:
        layer3_workbench.preflight(
            {
                "natural_language_intent": "Review material.",
                "manual_constraints": {"source_classes": ["rag_vector_index"]},
            }
        )
    assert unsupported.value.error_code == "unsupported_source_class"
    assert unsupported.value.next_allowed_actions == ["choose_supported_sources"]

    with pytest.raises(Layer3WorkbenchError) as forbidden:
        layer3_workbench.preflight(
            {
                "natural_language_intent": "Review material.",
                "manual_constraints": {
                    "source_classes": ["dataset_version"],
                    "local_upload": {"path": "not-admitted"},
                    "date_bounds": {"provider_public_url": "https://example.invalid/export"},
                },
            }
        )
    assert forbidden.value.error_code == "preflight_manual_constraint_scope_not_admitted"
    assert forbidden.value.blocked_fields == [
        "manual_constraints.date_bounds.provider_public_url",
        "manual_constraints.local_upload",
    ]
    assert forbidden.value.next_allowed_actions == ["remove_non_admitted_manual_constraints"]


def test_preview_shapes_keep_owner_service_and_planning_shape_separate() -> None:
    preflight, source, material = _preflight_source_material()

    assert preflight["eligible_for_source_selection"] is True
    assert {item["source_class"] for item in source["source_candidates"]} == {
        "dataset_version",
        "aps_content_document",
    }
    shapes = {
        item["owner_service_source_shape"]: item["planning_shape_family"]
        for item in material["material_candidates"]
    }
    assert shapes == {"dataset_version": "tabular_numeric", "aps_content_document": "document_chunks"}
    assert material["authority_rail"]["persistence_mode"] == "preview_only"


def test_gate_b_requires_client_request_id_before_persistence(db_session) -> None:
    preflight, source, material = _preflight_source_material()
    payload = _gate_b_payload(preflight, source, material)
    payload.pop("client_request_id")

    with pytest.raises(Layer3WorkbenchError) as exc:
        layer3_workbench.gate_b_decision(db_session, payload)

    assert exc.value.error_code == "client_request_id_required"
    assert exc.value.blocked_fields == ["client_request_id"]
    assert db_session.query(L3Session).count() == 0
    assert db_session.query(L3SelectionManifest).count() == 0
    assert db_session.query(L3MaterialSnapshot).count() == 0


def test_gate_b_persists_only_approved_material_through_layer3_owner_services(db_session) -> None:
    preflight, source, material = _preflight_source_material()

    result = layer3_workbench.gate_b_decision(db_session, _gate_b_payload(preflight, source, material))

    assert result["next_state"] == "gate_c_preview_ready"
    assert len(result["approved_candidate_ids"]) == 1
    assert len(result["flagged_candidate_ids"]) == 1
    assert result["authority_rail"]["persistence_mode"] == "durable_layer3_control"
    assert result["authority_rail"]["approved_material_count"] == 1
    assert result["authority_rail"]["flagged_material_count"] == 1

    session = db_session.get(L3Session, result["session_id"])
    manifest = db_session.get(L3SelectionManifest, result["selection_manifest_id"])
    snapshots = db_session.query(L3MaterialSnapshot).all()

    assert session is not None
    assert session.status == "completed"
    assert session.operator_context_json["layer3_gate_b_decision_manifest_v1"]["schema_id"] == (
        "layer3.gate_b_decision_manifest.v1"
    )
    assert session.summary_json["gate_b_summary_v1"]["approved"] == 1
    assert session.summary_json["gate_b_summary_v1"]["flagged"] == 1
    assert manifest is not None
    assert len(manifest.manifest_json["items"]) == 1
    assert len(snapshots) == 1
    assert snapshots[0].source_shape == "dataset_version"
    assert Path(snapshots[0].payload_ref).is_file()


def test_aps_derived_dataset_version_flows_from_material_preview_to_plan_preview(db_session, tmp_path) -> None:
    dataset_version_id = _seed_aps_derived_dataset_version(db_session, tmp_path)
    preflight = layer3_workbench.preflight(
        {
            "client_request_id": "req-preflight-aps-dataset",
            "natural_language_intent": "Review APS-derived CSV table as quantitative source material.",
            "manual_constraints": {"source_classes": ["dataset_version"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": "req-source-aps-dataset",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version"],
        }
    )
    material = layer3_workbench.material_preview(
        {
            "client_request_id": "req-material-aps-dataset",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [source["source_candidates"][0]["source_candidate_id"]],
            "dataset_version_ids": [dataset_version_id],
            "query_basis": {"terms": ["aps", "csv"]},
        },
        db_session,
    )

    candidate = material["material_candidates"][0]
    assert candidate["source_ref"] == f"dataset_version:{dataset_version_id}"
    assert candidate["planning_shape_family"] == "tabular_numeric"
    assert candidate["source_family"] == "csv"
    assert candidate["source_admission_state"] == "admitted_materialized_dataset_version"
    assert candidate["source_identity"]["dataset_version_id"] == dataset_version_id
    assert candidate["source_provenance"]["aps_derived"] is True
    assert candidate["source_provenance"]["source_family_label"] == "CSV table"
    assert candidate["source_provenance"]["aps_source_provenance"][0]["parser_family"] == "csv_table"
    assert candidate["source_trace"]["schema_id"] == "layer3.dataset_version_source_trace.v1"
    assert candidate["source_trace"]["trace_readiness"] == "traceable_aps_dataset_version"
    assert candidate["source_trace"]["dataset_identity"]["dataset_version_id"] == dataset_version_id
    assert candidate["source_trace"]["variable_summary"]["numeric_variables"] == ["value"]
    assert candidate["source_trace"]["aps_trace_refs"]["typed_content_contract_id"] == "aps_csv_table_units_v1"
    assert candidate["source_provenance"]["source_trace"]["aps_trace_refs"]["target_id"] == "target-001"

    gate_b = layer3_workbench.gate_b_decision(
        db_session,
        {
            "client_request_id": "req-gate-b-aps-dataset",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "material_preview_id": material["material_preview_id"],
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "operator_reason": "",
                    "decision_basis": {
                        "source_ref": candidate["source_ref"],
                        "query_basis": candidate["query_basis"],
                        "provenance_ref": candidate["provenance_ref"],
                        "source_identity": candidate["source_identity"],
                        "source_provenance": candidate["source_provenance"],
                        "payload": candidate["payload"],
                        "load_summary": candidate["load_summary"],
                    },
                }
            ],
            "commit_reason": "pytest_aps_dataset_gate_b",
            "actor": "pytest",
        },
    )

    snapshot = db_session.query(L3MaterialSnapshot).one()
    assert snapshot.source_shape == "dataset_version"
    assert snapshot.source_identity_json["dataset_version_id"] == dataset_version_id
    assert snapshot.source_provenance_json["aps_source_provenance"][0]["typed_content_contract_id"] == (
        "aps_csv_table_units_v1"
    )
    assert snapshot.source_provenance_json["source_trace"]["trace_readiness"] == "traceable_aps_dataset_version"

    committed = layer3_workbench.gate_c_preview(
        db_session,
        {"client_request_id": "req-gate-c-aps-dataset", "session_id": gate_b["session_id"], "commit_typing": True},
    )
    assert committed["typing_records"][0]["planning_shape_family"] == "tabular_numeric"
    assert committed["analysis_units"][0]["analysis_modality"] == "quantitative"

    plan = layer3_workbench.plan_preview(
        db_session,
        {"client_request_id": "req-plan-aps-dataset", "session_id": gate_b["session_id"]},
    )
    assert plan["plan_preview"]["admitted_sets"][0]["readiness"] == "admitted"
    assert plan["plan_preview"]["planned_passes"][0]["dataset_version_id"] == dataset_version_id


def test_aps_derived_dataset_material_preview_uses_newest_provenance(db_session, tmp_path) -> None:
    dataset_version_id = _seed_aps_derived_dataset_version(db_session, tmp_path)
    older = (
        db_session.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.dataset_version_id == dataset_version_id)
        .one()
    )
    older.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db_session.add(
        DatasetSourceProvenance(
            dataset_version_id=dataset_version_id,
            connector_run_id=None,
            source_system="nrc_adams_aps",
            source_mode="artifact_xlsx_parser",
            source_artifact_key="aps-target-artifacts/run-002/target-002/extraction.json",
            sciencebase_file_name="fixture.xlsx",
            downloaded_sha256="1" * 64,
            raw_storage_ref="aps-target-artifacts/run-002/target-002/blob.xlsx",
            source_reference_json={
                "target_id": "target-002",
                "accession_number": "ML000000002",
                "table_index": 0,
                "table_hash": "hash-table-002",
                "parser_family": "xlsx_workbook",
                "parser_contract_id": "aps_xlsx_workbook_parser_v1",
                "typed_content_contract_id": "aps_xlsx_workbook_units_v1",
                "diagnostics_ref": "aps-target-artifacts/run-002/target-002/diagnostics.json",
            },
            created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
    )
    db_session.flush()
    preflight = layer3_workbench.preflight(
        {
            "client_request_id": "req-preflight-aps-dataset-newest",
            "natural_language_intent": "Review latest APS-derived table provenance.",
            "manual_constraints": {"source_classes": ["dataset_version"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": "req-source-aps-dataset-newest",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version"],
        }
    )

    material = layer3_workbench.material_preview(
        {
            "client_request_id": "req-material-aps-dataset-newest",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [source["source_candidates"][0]["source_candidate_id"]],
            "dataset_version_ids": [dataset_version_id],
            "query_basis": {"terms": ["aps", "latest"]},
        },
        db_session,
    )

    candidate = material["material_candidates"][0]
    assert candidate["source_family"] == "xlsx"
    assert candidate["provenance_ref"] == "aps-target-artifacts/run-002/target-002/extraction.json"
    assert candidate["source_trace"]["aps_trace_refs"]["target_id"] == "target-002"
    assert candidate["source_trace"]["aps_trace_refs"]["typed_content_contract_id"] == "aps_xlsx_workbook_units_v1"
    assert candidate["source_provenance"]["aps_source_provenance"][0]["parser_family"] == "xlsx_workbook"


def test_aps_dataset_version_candidates_list_uses_dataset_source_provenance(db_session, tmp_path) -> None:
    dataset_version_id = _seed_aps_derived_dataset_version(db_session, tmp_path)

    result = layer3_workbench.aps_dataset_version_candidates(db_session)

    assert result["schema_id"] == "layer3.aps_dataset_version_candidates.v1"
    assert result["candidate_count"] == 1
    candidate = result["dataset_version_candidates"][0]
    assert candidate["dataset_version_id"] == dataset_version_id
    assert candidate["dataset_name"] == "APS CSV bridge dataset"
    assert candidate["source_system"] == "nrc_adams_aps"
    assert candidate["parser_family"] == "csv_table"
    assert candidate["typed_content_contract_id"] == "aps_csv_table_units_v1"
    assert candidate["source_family"] == "csv"
    assert candidate["source_family_label"] == "CSV table"
    assert candidate["source_admission_state"] == "admitted_materialized_dataset_version"
    assert candidate["row_count"] == 3
    assert candidate["variable_count"] == 2
    summary = result["source_family_summary"]
    assert summary["selection_shape"] == "dataset_version"
    assert summary["observed_candidate_counts"] == {"csv_table": 1}
    admitted_parser_families = {item["parser_family"] for item in summary["admitted_materialized_families"]}
    assert {"csv_table", "xlsx_workbook", "json_recordset", "sec_edgar_filing"} <= admitted_parser_families
    assert any(item["source_family"] == "xml_html_inline_xbrl" for item in summary["not_admitted_or_deferred_families"])
    assert result["authority_rail"]["read_only"] is True


def test_aps_dataset_version_candidates_surface_sec_edgar_family_scope(db_session, tmp_path) -> None:
    dataset_version_id = _seed_aps_derived_dataset_version(
        db_session,
        tmp_path,
        dataset_version_id="dv-aps-sec-edgar-001",
        parser_family="sec_edgar_filing",
        typed_content_contract_id="aps_sec_edgar_filing_units_v1",
        source_mode="artifact_sec_edgar_filing_parser",
        parser_contract_id="aps_sec_edgar_filing_parser_v1",
    )

    result = layer3_workbench.aps_dataset_version_candidates(db_session)

    candidate = result["dataset_version_candidates"][0]
    assert candidate["dataset_version_id"] == dataset_version_id
    assert candidate["parser_family"] == "sec_edgar_filing"
    assert candidate["source_family"] == "sec_edgar_text_table"
    assert candidate["source_family_label"] == "SEC/EDGAR text table"
    assert "complete-submission text" in candidate["source_family_scope"]
    assert result["source_family_summary"]["observed_candidate_counts"] == {"sec_edgar_filing": 1}


def test_dataset_version_candidates_include_server_owned_raw_mixed_materialization(db_session, tmp_path) -> None:
    dataset_version_id = _seed_aps_derived_dataset_version(
        db_session,
        tmp_path,
        dataset_version_id="dv-local-raw-mixed-001",
        source_system="local_operator_staged_server_owned_manifest",
        source_mode="raw_mixed_materialized",
        artifact_locator_type="server_owned_ref",
        fetch_policy_mode="server_owned_manifest",
    )

    result = layer3_workbench.aps_dataset_version_candidates(db_session)

    assert result["schema_id"] == "layer3.aps_dataset_version_candidates.v1"
    candidate = result["dataset_version_candidates"][0]
    assert candidate["dataset_version_id"] == dataset_version_id
    assert candidate["source_system"] == "local_operator_staged_server_owned_manifest"
    assert candidate["source_mode"] == "raw_mixed_materialized"
    assert candidate["source_admission_state"] == "admitted_materialized_dataset_version"
    assert result["source_family_summary"]["ui_scope"].startswith(
        "This endpoint surfaces server-backed materialized DatasetVersion choices only"
    )

    preflight = layer3_workbench.preflight(
        {
            "client_request_id": "req-preflight-raw-mixed-dataset",
            "natural_language_intent": "Review server-owned raw mixed materialized dataset.",
            "manual_constraints": {"source_classes": ["dataset_version"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": "req-source-raw-mixed-dataset",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version"],
        }
    )
    material = layer3_workbench.material_preview(
        {
            "client_request_id": "req-material-raw-mixed-dataset",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [
                source["source_candidates"][0]["source_candidate_id"],
            ],
            "dataset_version_ids": [dataset_version_id],
            "query_basis": {"terms": ["raw", "mixed"]},
        },
        db_session,
    )

    material_candidate = material["material_candidates"][0]
    source_provenance = material_candidate["source_provenance"]
    assert material_candidate["source_family"] == "csv"
    assert material_candidate["source_admission_state"] == "admitted_materialized_dataset_version"
    assert source_provenance["aps_derived"] is True
    assert source_provenance["source_family"] == "csv"
    assert source_provenance["source_admission_state"] == "admitted_materialized_dataset_version"
    assert (
        material_candidate["source_trace"]["trace_readiness"]
        == "traceable_aps_dataset_version"
    )
    assert (
        source_provenance["aps_source_provenance"][0]["source_system"]
        == "local_operator_staged_server_owned_manifest"
    )
    assert source_provenance["aps_source_provenance"][0]["source_mode"] == (
        "raw_mixed_materialized"
    )


def test_dataset_version_candidates_reject_unrecognized_server_owned_raw_mixed_source_system(
    db_session, tmp_path
) -> None:
    _seed_aps_derived_dataset_version(
        db_session,
        tmp_path,
        dataset_version_id="dv-other-raw-mixed-001",
        source_system="unrecognized_server_owned_manifest",
        source_mode="raw_mixed_materialized",
        artifact_locator_type="server_owned_ref",
        fetch_policy_mode="server_owned_manifest",
    )

    result = layer3_workbench.aps_dataset_version_candidates(db_session)

    assert result["candidate_count"] == 0
    assert result["dataset_version_candidates"] == []


def test_raw_mixed_aps_shortcut_is_not_admitted_without_server_owned_sentinel(
    db_session, tmp_path
) -> None:
    dataset_version_id = _seed_aps_derived_dataset_version(
        db_session,
        tmp_path,
        dataset_version_id="dv-aps-raw-mixed-shortcut-001",
        source_system="nrc_adams_aps",
        source_mode="raw_mixed_materialized",
        artifact_locator_type="server_owned_ref",
        fetch_policy_mode="server_owned_manifest",
    )

    result = layer3_workbench.aps_dataset_version_candidates(db_session)

    assert result["candidate_count"] == 0
    preflight = layer3_workbench.preflight(
        {
            "client_request_id": "req-preflight-aps-raw-mixed-shortcut",
            "natural_language_intent": "Reject raw mixed APS shortcut provenance.",
            "manual_constraints": {"source_classes": ["dataset_version"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": "req-source-aps-raw-mixed-shortcut",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version"],
        }
    )
    with pytest.raises(layer3_workbench.Layer3WorkbenchError) as exc:
        layer3_workbench.material_preview(
            {
                "client_request_id": "req-material-aps-raw-mixed-shortcut",
                "preflight_id": preflight["preflight_id"],
                "source_set_id": source["source_set_id"],
                "source_candidate_ids": [source["source_candidates"][0]["source_candidate_id"]],
                "dataset_version_ids": [dataset_version_id],
                "query_basis": {"terms": ["raw", "mixed"]},
            },
            db_session,
        )
    assert exc.value.error_code == "dataset_version_provenance_not_admitted"


def test_newest_rejected_raw_mixed_provenance_blocks_stale_accepted_fallback(
    db_session, tmp_path
) -> None:
    dataset_version_id = _seed_aps_derived_dataset_version(db_session, tmp_path)
    older = (
        db_session.query(DatasetSourceProvenance)
        .filter(DatasetSourceProvenance.dataset_version_id == dataset_version_id)
        .one()
    )
    older.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db_session.add(
        DatasetSourceProvenance(
            dataset_version_id=dataset_version_id,
            connector_run_id=None,
            source_system="nrc_adams_aps",
            source_mode="raw_mixed_materialized",
            source_artifact_key="aps-target-artifacts/run-raw/target-raw/extraction.json",
            sciencebase_file_name="fixture-raw.csv",
            downloaded_sha256="2" * 64,
            raw_storage_ref="aps-target-artifacts/run-raw/target-raw/blob.csv",
            artifact_locator_type="server_owned_ref",
            fetch_policy_mode="server_owned_manifest",
            source_reference_json={
                "target_id": "target-raw",
                "accession_number": "ML000000RAW",
                "parser_family": "csv_table",
                "parser_contract_id": "aps_csv_parser_v1",
                "typed_content_contract_id": "aps_csv_table_units_v1",
            },
            created_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        )
    )
    db_session.flush()

    result = layer3_workbench.aps_dataset_version_candidates(db_session)

    assert result["candidate_count"] == 0
    preflight = layer3_workbench.preflight(
        {
            "client_request_id": "req-preflight-newest-raw-mixed-rejected",
            "natural_language_intent": "Reject stale fallback after newer raw mixed provenance.",
            "manual_constraints": {"source_classes": ["dataset_version"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": "req-source-newest-raw-mixed-rejected",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["dataset_version"],
        }
    )
    with pytest.raises(layer3_workbench.Layer3WorkbenchError) as exc:
        layer3_workbench.material_preview(
            {
                "client_request_id": "req-material-newest-raw-mixed-rejected",
                "preflight_id": preflight["preflight_id"],
                "source_set_id": source["source_set_id"],
                "source_candidate_ids": [source["source_candidates"][0]["source_candidate_id"]],
                "dataset_version_ids": [dataset_version_id],
                "query_basis": {"terms": ["aps", "latest"]},
            },
            db_session,
        )
    assert exc.value.error_code == "dataset_version_provenance_not_admitted"


def test_aps_content_document_candidates_list_uses_content_linkage(db_session, tmp_path) -> None:
    content_id = _seed_aps_content_document(db_session, tmp_path)

    result = layer3_workbench.aps_content_document_candidates(db_session)

    assert result["schema_id"] == "layer3.aps_content_document_candidates.v1"
    assert result["candidate_count"] == 1
    assert result["authority_rail"]["authority_source"] == "aps_content_document_and_linkage"
    candidate = result["aps_content_document_candidates"][0]
    assert candidate["content_id"] == content_id
    assert candidate["source_family"] == "aps_content_document"
    assert candidate["source_admission_state"] == "admitted_content_document"
    assert candidate["accession_number"] == "ML26001A001"
    assert candidate["content_units_ref"].endswith("_content_units.json")
    assert candidate["chunk_count"] == 2
    assert candidate["page_count"] == 2


def test_aps_content_document_flows_from_material_preview_to_gate_b(db_session, tmp_path) -> None:
    content_id = _seed_aps_content_document(db_session, tmp_path)
    preflight = layer3_workbench.preflight(
        {
            "client_request_id": "req-preflight-aps-doc",
            "natural_language_intent": "Review indexed APS document chunks as qualitative source material.",
            "manual_constraints": {"source_classes": ["aps_content_document"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": "req-source-aps-doc",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["aps_content_document"],
        }
    )
    material = layer3_workbench.material_preview(
        {
            "client_request_id": "req-material-aps-doc",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [source["source_candidates"][0]["source_candidate_id"]],
            "aps_content_document_ids": [content_id],
            "query_basis": {"terms": ["aps", "document"]},
        },
        db_session,
    )

    candidate = material["material_candidates"][0]
    assert candidate["source_ref"] == f"aps_content_document:{content_id}"
    assert candidate["planning_shape_family"] == "document_chunks"
    assert candidate["source_family"] == "aps_content_document"
    assert candidate["source_admission_state"] == "admitted_content_document"
    assert candidate["source_identity"]["content_id"] == content_id
    assert candidate["source_provenance"]["aps_derived"] is True
    assert candidate["source_provenance"]["linkage_count"] == 1
    assert candidate["source_trace"]["schema_id"] == "layer3.aps_content_document_source_trace.v1"
    assert candidate["source_trace"]["trace_readiness"] == "traceable_aps_content_document"
    assert candidate["source_trace"]["document_identity"]["content_id"] == content_id
    assert candidate["source_trace"]["chunk_summary"]["loaded_chunk_count"] == 2
    assert candidate["source_trace"]["aps_trace_refs"]["accession_number"] == "ML26001A001"
    assert candidate["source_trace"]["aps_trace_refs"]["content_units_ref"].endswith("_content_units.json")

    layer3_workbench.gate_b_decision(
        db_session,
        {
            "client_request_id": "req-gate-b-aps-doc",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "material_preview_id": material["material_preview_id"],
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "operator_reason": "",
                    "decision_basis": {
                        "source_ref": candidate["source_ref"],
                        "query_basis": candidate["query_basis"],
                        "provenance_ref": candidate["provenance_ref"],
                        "source_identity": candidate["source_identity"],
                        "source_provenance": candidate["source_provenance"],
                        "payload": candidate["payload"],
                        "load_summary": candidate["load_summary"],
                    },
                }
            ],
            "commit_reason": "pytest_aps_doc_gate_b",
            "actor": "pytest",
        },
    )

    snapshot = db_session.query(L3MaterialSnapshot).one()
    assert snapshot.source_shape == "aps_content_document"
    assert snapshot.source_identity_json["content_id"] == content_id
    assert snapshot.source_identity_json["run_id"] == "run-layer3-doc-001"
    assert snapshot.source_identity_json["target_id"] == "target-layer3-doc-001"
    assert snapshot.source_provenance_json["source_trace"]["trace_readiness"] == "traceable_aps_content_document"
    assert snapshot.source_provenance_json["source_trace"]["aps_trace_refs"]["target_id"] == "target-layer3-doc-001"


def test_gate_c_preview_is_non_authoritative_and_override_is_unavailable(db_session) -> None:
    preflight, source, material = _preflight_source_material()
    gate_b = layer3_workbench.gate_b_decision(db_session, _gate_b_payload(preflight, source, material))

    preview = layer3_workbench.gate_c_preview(
        db_session,
        {"client_request_id": "req-gate-c", "session_id": gate_b["session_id"], "commit_typing": False},
    )
    override = layer3_workbench.gate_c_override_unavailable({"client_request_id": "req-override"})

    assert preview["next_state"] == "first_slice_complete"
    assert preview["override_allowed"] is False
    assert preview["typing_records"][0]["authoritative"] is False
    assert preview["analysis_units"][0]["authoritative"] is False
    assert preview["authority_rail"]["approved_material_count"] == 1
    assert preview["authority_rail"]["flagged_material_count"] == 1
    assert preview["authority_rail"]["source_authority"]["source_classes"] == ["dataset_version"]
    assert db_session.query(L3TypingRecord).count() == 0
    assert db_session.query(L3AnalysisUnit).count() == 0
    assert override["status"] == "unavailable"
    assert override["error_code"] == "override_unavailable"


def test_gate_c_commit_typing_materializes_owner_service_records(db_session) -> None:
    preflight, source, material = _preflight_source_material()
    gate_b = layer3_workbench.gate_b_decision(db_session, _gate_b_payload(preflight, source, material))

    committed = layer3_workbench.gate_c_preview(
        db_session,
        {"client_request_id": "req-gate-c-commit", "session_id": gate_b["session_id"], "commit_typing": True},
    )

    assert committed["next_state"] == "plan_preview_ready"
    assert committed["override_allowed"] is False
    assert committed["typing_records"][0]["authoritative"] is True
    assert committed["analysis_units"][0]["authoritative"] is True
    assert committed["authority_rail"]["approved_material_count"] == 1
    assert committed["authority_rail"]["flagged_material_count"] == 1
    assert committed["authority_rail"]["source_authority"]["source_classes"] == ["dataset_version"]
    assert db_session.query(L3TypingRecord).count() == 1
    assert db_session.query(L3AnalysisUnit).count() == 1
    assert db_session.query(L3AnalysisGroup).count() == 1
    assert db_session.query(L3AnalysisSet).count() == 1

    summary = layer3_workbench.session_summary(db_session, gate_b["session_id"])
    assert summary["current_gate"] == "plan"
    assert summary["gate_c_summary"]["typing_committed"] is True
    assert summary["authority_rail"]["typing_status"] == "committed"
    assert summary["plan_preview"]["available"] is False
    assert summary["plan_preview"]["blocked_reason"] == "no_admissible_plan"
    assert summary["downstream_unavailable"] == ["execution", "results", "package"]


def test_plan_preview_is_blocked_until_gate_c_commit(db_session) -> None:
    preflight, source, material = _preflight_source_material()
    gate_b = layer3_workbench.gate_b_decision(db_session, _gate_b_payload(preflight, source, material))

    with pytest.raises(Layer3WorkbenchError) as blocked:
        layer3_workbench.plan_preview(
            db_session,
            {
                "client_request_id": "req-plan-before-gate-c",
                "session_id": gate_b["session_id"],
            },
        )

    assert blocked.value.error_code == "gate_c_not_committed"
    assert blocked.value.status == "blocked"
    assert blocked.value.next_allowed_actions == ["commit_gate_c_typing"]


def test_plan_preview_fails_closed_when_committed_session_has_no_admissible_plan(db_session) -> None:
    preflight, source, material = _preflight_source_material()
    gate_b = layer3_workbench.gate_b_decision(db_session, _gate_b_payload(preflight, source, material))
    layer3_workbench.gate_c_preview(
        db_session,
        {"client_request_id": "req-gate-c-commit", "session_id": gate_b["session_id"], "commit_typing": True},
    )

    with pytest.raises(Layer3WorkbenchError) as blocked:
        layer3_workbench.plan_preview(
            db_session,
            {
                "client_request_id": "req-plan-synthetic-material",
                "session_id": gate_b["session_id"],
            },
        )

    assert blocked.value.error_code == "no_admissible_plan"
    assert blocked.value.status == "blocked"


def test_session_summary_reflects_gate_b_counts_without_overclaiming_typing_commit(db_session) -> None:
    preflight, source, material = _preflight_source_material()
    gate_b = layer3_workbench.gate_b_decision(db_session, _gate_b_payload(preflight, source, material))

    summary = layer3_workbench.session_summary(db_session, gate_b["session_id"])

    assert summary["current_gate"] == "gate_c"
    assert summary["gate_b_summary"] == {"approved": 1, "denied": 0, "isolated": 0, "flagged": 1}
    assert summary["gate_c_summary"]["typing_committed"] is False
    assert summary["downstream_unavailable"] == ["plan", "execution", "results", "package"]
