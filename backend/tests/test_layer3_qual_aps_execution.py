from __future__ import annotations

import hashlib
import json
import os
import sys
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
    DatasetVersion,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
)
from app.services import layer3_workbench
from app.services.layer3_qual_aps_execution import (
    ENGINE_FAMILY_QUAL_APS_DOCUMENT,
    PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
    QUAL_APS_METHOD_NAME,
    QUAL_APS_OUTPUT_SCHEMA_ID,
    QUAL_APS_SOURCE_GATE,
)
from app.services.layer3_workbench import Layer3WorkbenchError


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


def _seed_aps_content_document(
    db,
    tmp_path: Path,
    *,
    content_id: str = "content-qual-aps-001",
    chunks: tuple[str, ...] = (
        "Inspection findings confirm stable cooling performance.",
        "No safety-significant degradation was identified during the interval.",
    ),
) -> str:
    content_contract_id = "aps_pdf_content_units_v1"
    chunking_contract_id = "aps_pdf_chunking_v1"
    normalization_contract_id = "aps_pdf_normalization_v1"
    run_id = f"run-{content_id}"
    target_id = f"target-{content_id}"
    artifact_root = tmp_path / "aps"
    artifact_root.mkdir(parents=True, exist_ok=True)
    normalized_text = "\n".join(chunks)
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
                chunk_count=len(chunks),
                content_status="indexed",
                media_type="application/pdf",
                document_class="inspection_report",
                quality_status="strong",
                page_count=max(len(chunks), 1),
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
    for ordinal, chunk_text in enumerate(chunks):
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


def _commit_single_doc_plan(db, tmp_path: Path, *, content_id: str = "content-qual-aps-001") -> dict[str, object]:
    _seed_aps_content_document(db, tmp_path, content_id=content_id)
    preflight = layer3_workbench.preflight(
        {
            "client_request_id": f"req-preflight-{content_id}",
            "natural_language_intent": "Review indexed APS document chunks as qualitative source material.",
            "manual_constraints": {"source_classes": ["aps_content_document"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": f"req-source-{content_id}",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["aps_content_document"],
        }
    )
    material = layer3_workbench.material_preview(
        {
            "client_request_id": f"req-material-{content_id}",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [source["source_candidates"][0]["source_candidate_id"]],
            "aps_content_document_ids": [content_id],
            "query_basis": {"terms": ["aps", "document"]},
        },
        db,
    )
    candidate = material["material_candidates"][0]
    gate_b = layer3_workbench.gate_b_decision(
        db,
        {
            "client_request_id": f"req-gate-b-{content_id}",
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
            "commit_reason": "pytest_single_aps_doc_qualitative",
            "actor": "pytest",
        },
    )
    layer3_workbench.gate_c_preview(
        db,
        {
            "client_request_id": f"req-gate-c-{content_id}",
            "session_id": gate_b["session_id"],
            "commit_typing": True,
        },
    )
    preview = layer3_workbench.plan_preview(
        db,
        {"client_request_id": f"req-plan-{content_id}", "session_id": gate_b["session_id"]},
    )
    planned_pass = preview["plan_preview"]["planned_passes"][0]
    assert planned_pass["engine_family"] == ENGINE_FAMILY_QUAL_APS_DOCUMENT
    assert planned_pass["pass_scope"] == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
    approval = layer3_workbench.plan_approval(
        db,
        {
            "client_request_id": f"req-approval-{content_id}",
            "session_id": gate_b["session_id"],
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
            "operator_confirmation": True,
        },
    )
    selection = layer3_workbench.execution_selection(
        db,
        {
            "client_request_id": f"req-selection-{content_id}",
            "session_id": gate_b["session_id"],
            "analysis_plan_id": approval["analysis_plan_id"],
            "preview_id": preview["preview_id"],
            "preview_hash": preview["preview_hash"],
        },
    )
    return {
        "session_id": gate_b["session_id"],
        "analysis_plan_id": approval["analysis_plan_id"],
        "preview_id": preview["preview_id"],
        "preview_hash": preview["preview_hash"],
        "pass_run_id": selection["pass_run_ids"][0],
        "content_id": content_id,
    }


def test_single_aps_doc_qualitative_pass_executes_without_analysis_run_or_dataset_version(db_session, tmp_path) -> None:
    flow = _commit_single_doc_plan(db_session, tmp_path)

    result = layer3_workbench.analysis_execution_start(
        db_session,
        {
            "client_request_id": "req-qual-start",
            "session_id": flow["session_id"],
            "analysis_plan_id": flow["analysis_plan_id"],
            "pass_run_id": flow["pass_run_id"],
            "preview_id": flow["preview_id"],
            "preview_hash": flow["preview_hash"],
            "execution_mode": "synchronous_single_pass",
        },
    )

    assert result["status"] == "completed"
    assert result["execution_started"] is True
    assert result["analysis_run_id"] is None
    assert result["engine_family"] == ENGINE_FAMILY_QUAL_APS_DOCUMENT
    assert result["selected_method_name"] == QUAL_APS_METHOD_NAME
    assert result["dataset_version_id"] is None
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(DatasetVersion).count() == 0

    pass_run = db_session.get(L3PassRun, flow["pass_run_id"])
    assert pass_run.status == "completed"
    assert pass_run.summary_json["source_gate"] == QUAL_APS_SOURCE_GATE
    output = json.loads(Path(pass_run.output_payload_ref).read_text(encoding="utf-8"))
    assert output["schema_id"] == QUAL_APS_OUTPUT_SCHEMA_ID
    assert output["analysis_run_id"] is None
    assert output["document_identity"]["content_id"] == flow["content_id"]
    assert output["chunk_summary"]["ordering"] == "chunk_ordinal_then_chunk_id"
    assert output["chunk_summary"]["chunk_ids"] == [
        f"{flow['content_id']}-chunk-1",
        f"{flow['content_id']}-chunk-2",
    ]
    assert len(output["output_items_json"]) == 2
    assert output["output_items_json"][0]["trace"]["chunk_id"] == f"{flow['content_id']}-chunk-1"

    status = layer3_workbench.execution_result_status(
        db_session,
        {
            "client_request_id": "req-qual-status",
            "session_id": flow["session_id"],
            "analysis_plan_id": flow["analysis_plan_id"],
            "pass_run_id": flow["pass_run_id"],
            "preview_id": flow["preview_id"],
            "preview_hash": flow["preview_hash"],
        },
    )
    assert status["status"] == "available"
    assert status["analysis_run_id"] is None
    assert status["output_metadata_summary"]["content_id"] == flow["content_id"]
    assert status["output_metadata_summary"]["chunk_ids"] == output["chunk_summary"]["chunk_ids"]


def test_single_aps_doc_qualitative_execution_is_idempotent_for_same_request(db_session, tmp_path) -> None:
    flow = _commit_single_doc_plan(db_session, tmp_path, content_id="content-qual-aps-idem")
    payload = {
        "client_request_id": "req-qual-start-idem",
        "session_id": flow["session_id"],
        "analysis_plan_id": flow["analysis_plan_id"],
        "pass_run_id": flow["pass_run_id"],
        "preview_id": flow["preview_id"],
        "preview_hash": flow["preview_hash"],
    }

    first = layer3_workbench.analysis_execution_start(db_session, payload)
    second = layer3_workbench.analysis_execution_start(db_session, payload)

    assert first["output_payload_ref"] == second["output_payload_ref"]
    assert second["status"] == "already_completed"
    assert db_session.query(AnalysisRun).count() == 0
    assert db_session.query(L3PassRun).count() == 1


def test_single_aps_doc_qualitative_execution_rejects_forbidden_request_fields(db_session, tmp_path) -> None:
    flow = _commit_single_doc_plan(db_session, tmp_path, content_id="content-qual-aps-forbidden")

    with pytest.raises(Layer3WorkbenchError) as exc:
        layer3_workbench.analysis_execution_start(
            db_session,
            {
                "client_request_id": "req-qual-start-forbidden",
                "session_id": flow["session_id"],
                "analysis_plan_id": flow["analysis_plan_id"],
                "pass_run_id": flow["pass_run_id"],
                "preview_id": flow["preview_id"],
                "preview_hash": flow["preview_hash"],
                "rag_plan": {"retrieve": True},
            },
        )

    assert exc.value.error_code == "analysis_execution_start_scope_not_admitted"
    assert exc.value.blocked_fields == ["rag_plan"]
    pass_run = db_session.get(L3PassRun, flow["pass_run_id"])
    assert pass_run.status == "selected_not_started"
    assert pass_run.output_payload_ref is None


def test_single_aps_doc_qualitative_package_preview_remains_blocked(db_session, tmp_path) -> None:
    flow = _commit_single_doc_plan(db_session, tmp_path, content_id="content-qual-aps-package")
    start = layer3_workbench.analysis_execution_start(
        db_session,
        {
            "client_request_id": "req-qual-start-package",
            "session_id": flow["session_id"],
            "analysis_plan_id": flow["analysis_plan_id"],
            "pass_run_id": flow["pass_run_id"],
            "preview_id": flow["preview_id"],
            "preview_hash": flow["preview_hash"],
        },
    )
    review = layer3_workbench.execution_result_review(
        db_session,
        {
            "client_request_id": "req-qual-review-package",
            "session_id": flow["session_id"],
            "analysis_plan_id": flow["analysis_plan_id"],
            "pass_run_id": flow["pass_run_id"],
            "preview_id": flow["preview_id"],
            "preview_hash": flow["preview_hash"],
            "operator_decision": "approved",
            "reviewed_output_items": [],
        },
    )

    with pytest.raises(Layer3WorkbenchError) as exc:
        layer3_workbench.package_review_preview(
            db_session,
            {
                "client_request_id": "req-qual-package-preview",
                "session_id": flow["session_id"],
                "analysis_plan_id": flow["analysis_plan_id"],
                "pass_run_id": flow["pass_run_id"],
                "preview_id": flow["preview_id"],
                "preview_hash": flow["preview_hash"],
                "analysis_run_id": start["analysis_run_id"],
                "result_review_record_ref": review["review_record_ref"],
            },
        )

    assert exc.value.error_code == "qualitative_aps_package_review_preview_not_admitted"
    assert db_session.query(L3OutputPackage).count() == 0
    assert db_session.query(L3ReconciliationRecord).count() == 0


def test_single_aps_doc_qualitative_plan_requires_chunks(db_session, tmp_path) -> None:
    content_id = _seed_aps_content_document(
        db_session,
        tmp_path,
        content_id="content-qual-aps-no-chunks",
        chunks=(),
    )
    preflight = layer3_workbench.preflight(
        {
            "client_request_id": "req-preflight-no-chunks",
            "natural_language_intent": "Review indexed APS document chunks as qualitative source material.",
            "manual_constraints": {"source_classes": ["aps_content_document"]},
        }
    )
    source = layer3_workbench.source_preview(
        {
            "client_request_id": "req-source-no-chunks",
            "preflight_id": preflight["preflight_id"],
            "selected_source_classes": ["aps_content_document"],
        }
    )
    material = layer3_workbench.material_preview(
        {
            "client_request_id": "req-material-no-chunks",
            "preflight_id": preflight["preflight_id"],
            "source_set_id": source["source_set_id"],
            "source_candidate_ids": [source["source_candidates"][0]["source_candidate_id"]],
            "aps_content_document_ids": [content_id],
            "query_basis": {"terms": ["aps", "document"]},
        },
        db_session,
    )
    candidate = material["material_candidates"][0]
    gate_b = layer3_workbench.gate_b_decision(
        db_session,
        {
            "client_request_id": "req-gate-b-no-chunks",
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
            "commit_reason": "pytest_single_aps_doc_no_chunks",
            "actor": "pytest",
        },
    )
    layer3_workbench.gate_c_preview(
        db_session,
        {"client_request_id": "req-gate-c-no-chunks", "session_id": gate_b["session_id"], "commit_typing": True},
    )

    with pytest.raises(Layer3WorkbenchError) as exc:
        layer3_workbench.plan_preview(
            db_session,
            {"client_request_id": "req-plan-no-chunks", "session_id": gate_b["session_id"]},
        )

    assert exc.value.error_code == "no_admissible_plan"
    assert db_session.query(L3PassRun).count() == 0
    assert db_session.query(AnalysisRun).count() == 0
