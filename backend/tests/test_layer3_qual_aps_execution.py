from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

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
    L3Descriptor,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3SelectionManifest,
)
from app.services import layer3_package_entry, layer3_pass_entry, layer3_workbench
from app.services.layer3_qual_aps_execution import (
    ENGINE_FAMILY_QUAL_APS_DOCUMENT,
    PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
    QUALITATIVE_BOUNDARY_CONTRACT_SCHEMA_ID,
    QUALITATIVE_BOUNDARY_MODE,
    Layer3QualApsExecutionError,
    QUAL_APS_METHOD_NAME,
    QUAL_APS_OUTPUT_SCHEMA_ID,
    QUAL_APS_SOURCE_GATE,
    qualitative_hybrid_rag_boundary_contract,
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


@pytest.fixture()
def reserved_db_session(tmp_path, monkeypatch):
    storage_dir = tmp_path / "reserved-storage"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'reserved.sqlite3').as_posix()}",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
        pool_size=4,
        max_overflow=0,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _seed_aps_content_document(
    db,
    tmp_path: Path,
    *,
    content_id: str = "content-qual-aps-001",
    reserved_origin: bool = False,
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
            ConnectorRun(
                connector_run_id=run_id,
                connector_key="nrc_adams_aps",
                source_system=("nrc_adams" if reserved_origin else None),
                source_mode=("strict_live_egress" if reserved_origin else None),
                status="completed",
            ),
            ConnectorRunTarget(
                connector_run_target_id=target_id,
                connector_run_id=run_id,
                status="completed",
                ordinal=0,
                stable_release_key=("ML17123A319" if reserved_origin else None),
                stable_release_identifier=(
                    "adams_accession:ML17123A319"
                    if reserved_origin
                    else None
                ),
                selection_source=(
                    "strict_exact_accession" if reserved_origin else None
                ),
                selection_scope=(
                    "dual_live_proof_v1" if reserved_origin else None
                ),
                fetch_policy_mode=(
                    "strict_live_egress" if reserved_origin else None
                ),
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
                document_class=(
                    "nrc_adams_aps" if reserved_origin else "inspection_report"
                ),
                quality_status="strong",
                page_count=max(len(chunks), 1),
                diagnostics_ref=diagnostics_ref,
                visual_page_refs_json=json.dumps([]),
            ),
            ApsContentLinkage(
                content_id=content_id,
                run_id=run_id,
                target_id=target_id,
                accession_number=(
                    "ML17123A319" if reserved_origin else "ML26001A001"
                ),
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


def _commit_single_doc_plan(
    db,
    tmp_path: Path,
    *,
    content_id: str = "content-qual-aps-001",
    reserved_origin: bool = False,
) -> dict[str, object]:
    _seed_aps_content_document(
        db,
        tmp_path,
        content_id=content_id,
        reserved_origin=reserved_origin,
    )
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
            "query_basis": {
                "terms": (
                    ["dual-live-proof"]
                    if reserved_origin
                    else ["aps", "document"]
                )
            },
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
    descriptor = (
        db.query(L3Descriptor)
        .filter(L3Descriptor.session_id == gate_b["session_id"])
        .one()
    )
    manifest = (
        db.query(L3SelectionManifest)
        .filter(L3SelectionManifest.session_id == gate_b["session_id"])
        .one()
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
        "descriptor_selector": copy.deepcopy(
            descriptor.selector_payload_json
        ),
        "manifest_selector": copy.deepcopy(
            manifest.manifest_json["items"][0]["selector_payload"]
        ),
        "expected_selector": {
            "candidate_id": candidate["candidate_id"],
            "source_ref": f"aps_content_document:{content_id}",
        },
    }


def test_qualitative_hybrid_rag_boundary_contract_keeps_broad_execution_fail_closed() -> None:
    contract = qualitative_hybrid_rag_boundary_contract()

    assert contract["schema_id"] == QUALITATIVE_BOUNDARY_CONTRACT_SCHEMA_ID
    assert contract["mode"] == QUALITATIVE_BOUNDARY_MODE
    assert contract["owner_service"] == "backend/app/services/layer3_qual_aps_execution.py"
    assert contract["admitted_execution_modes"] == [PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE]
    assert contract["admitted_engine_family"] == ENGINE_FAMILY_QUAL_APS_DOCUMENT
    assert contract["admitted_method_name"] == QUAL_APS_METHOD_NAME
    assert contract["admitted_source_gate"] == QUAL_APS_SOURCE_GATE
    assert set(contract["deferred_capabilities"]) >= {
        "broad_qualitative_execution",
        "qualitative_associated_cohort_execution",
        "comparative_qualitative_execution",
        "cross_document_synthesis",
        "hybrid_execution",
        "rag_vector_retrieval",
        "hidden_llm_planning",
        "qualitative_package_handoff_export",
    }
    assert set(contract["forbidden_runtime_fields"]) >= {
        "qualitative_plan",
        "hybrid_plan",
        "rag_plan",
        "vector_plan",
        "run_all",
        "artifact_manifest",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "connector_id",
        "destination_id",
        "provider_url",
        "public_url",
        "source_upload",
        "schema_migration",
        "runtime_db_write",
        "hidden_llm_plan",
    }
    assert contract["single_aps_doc_qualitative_execution_enabled"] is True
    assert contract["broad_qualitative_execution_enabled"] is False
    assert contract["qualitative_associated_cohort_execution_enabled"] is False
    assert contract["comparative_qualitative_execution_enabled"] is False
    assert contract["cross_document_synthesis_enabled"] is False
    assert contract["hybrid_execution_enabled"] is False
    assert contract["rag_vector_retrieval_enabled"] is False
    assert contract["hidden_llm_planning_enabled"] is False
    assert contract["qualitative_package_handoff_export_enabled"] is False
    assert contract["source_widening_enabled"] is False
    assert contract["connector_destination_dispatch_enabled"] is False
    assert contract["package_mutation_reconstruction_enabled"] is False
    assert contract["requires_later_freeze"] is True


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
    assert output["output_items_json"][0]["highlight_spans"] == [
        {
            "start": 0,
            "end": output["output_items_json"][0]["text_char_count"],
            "source": "citations[].highlight_spans",
        }
    ]

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


def test_single_aps_doc_qualitative_owner_error_maps_without_side_effects(
    db_session,
    tmp_path,
    monkeypatch,
) -> None:
    flow = _commit_single_doc_plan(db_session, tmp_path, content_id="content-qual-aps-owner-error")
    counts_before = {
        "analysis_runs": db_session.query(AnalysisRun).count(),
        "dataset_versions": db_session.query(DatasetVersion).count(),
        "output_packages": db_session.query(L3OutputPackage).count(),
        "reconciliation_records": db_session.query(L3ReconciliationRecord).count(),
        "connector_runs": db_session.query(ConnectorRun).count(),
        "connector_run_targets": db_session.query(ConnectorRunTarget).count(),
    }

    def _raise_qualitative_owner_error(*_args, **_kwargs):
        raise Layer3QualApsExecutionError("forced qualitative APS owner-service proof failure")

    monkeypatch.setattr(
        layer3_workbench,
        "execute_single_aps_doc_qualitative_pass",
        _raise_qualitative_owner_error,
    )

    with pytest.raises(Layer3WorkbenchError) as exc:
        layer3_workbench.analysis_execution_start(
            db_session,
            {
                "client_request_id": "req-qual-start-owner-error",
                "session_id": flow["session_id"],
                "analysis_plan_id": flow["analysis_plan_id"],
                "pass_run_id": flow["pass_run_id"],
                "preview_id": flow["preview_id"],
                "preview_hash": flow["preview_hash"],
            },
        )

    assert exc.value.error_code == "analysis_execution_start_not_admitted"
    assert exc.value.status == "conflict"
    assert exc.value.http_status == 409
    assert "forced qualitative APS owner-service proof failure" in exc.value.message

    pass_run = db_session.get(L3PassRun, flow["pass_run_id"])
    assert pass_run.status == "selected_not_started"
    assert pass_run.output_payload_ref is None
    assert pass_run.summary_json["selection_state"] == "execution_selected_not_started"
    assert pass_run.summary_json["execution_started"] is False
    assert pass_run.summary_json["analysis_run_id"] is None
    assert "analysis_execution_start" not in pass_run.summary_json
    assert {
        "analysis_runs": db_session.query(AnalysisRun).count(),
        "dataset_versions": db_session.query(DatasetVersion).count(),
        "output_packages": db_session.query(L3OutputPackage).count(),
        "reconciliation_records": db_session.query(L3ReconciliationRecord).count(),
        "connector_runs": db_session.query(ConnectorRun).count(),
        "connector_run_targets": db_session.query(ConnectorRunTarget).count(),
    } == counts_before


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


def test_single_aps_doc_qualitative_package_preview_construction_and_submit_guard(
    reserved_db_session,
    tmp_path,
    monkeypatch,
) -> None:
    db_session = reserved_db_session
    content_id = "content-qual-aps-package"
    target_id = f"target-{content_id}"
    origin_integrity = {
        "schema_id": "layer3.connector_origin_integrity.v1",
        "connector_key": "nrc_adams_aps",
        "connector_run_target_id": target_id,
        "connector_origin_receipt_hash": hashlib.sha256(
            target_id.encode("utf-8")
        ).hexdigest(),
        "proof_class": "fresh_live",
    }
    origin_boundaries: list[str] = []

    def resolve_origin(_db, *, session_id: str, boundary: str):
        assert session_id
        origin_boundaries.append(boundary)
        return copy.deepcopy(origin_integrity)

    def assert_pass_origin(_db, *, pass_run: L3PassRun, boundary: str):
        assert pass_run.summary_json[
            "connector_origin_integrity_v1"
        ] == origin_integrity
        origin_boundaries.append(boundary)
        return copy.deepcopy(origin_integrity)

    monkeypatch.setattr(
        layer3_workbench,
        "resolve_downstream_connector_origin",
        resolve_origin,
    )
    monkeypatch.setattr(
        layer3_workbench,
        "assert_pass_downstream_connector_origin",
        assert_pass_origin,
    )
    monkeypatch.setattr(
        layer3_package_entry,
        "assert_pass_downstream_connector_origin",
        assert_pass_origin,
    )
    monkeypatch.setattr(
        layer3_pass_entry,
        "assert_pass_downstream_connector_origin",
        assert_pass_origin,
    )
    flow = _commit_single_doc_plan(
        db_session,
        tmp_path,
        content_id=content_id,
        reserved_origin=True,
    )
    assert flow["descriptor_selector"] == flow["expected_selector"]
    assert flow["manifest_selector"] == flow["expected_selector"]
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
    pass_run = db_session.get(L3PassRun, flow["pass_run_id"])
    assert pass_run is not None
    assert pass_run.summary_json[
        "connector_origin_integrity_v1"
    ] == origin_integrity
    output_integrity = copy.deepcopy(
        pass_run.summary_json["connector_output_integrity_v1"]
    )
    assert set(output_integrity) == {
        "schema_id",
        "connector_key",
        "connector_run_target_id",
        "connector_origin_receipt_hash",
        "proof_class",
        "artifact_receipts",
        "artifact_set_hash",
        "output_manifest_sha256",
    }
    assert output_integrity["schema_id"] == (
        "layer3.connector_output_integrity.v1"
    )
    assert {
        key: output_integrity[key]
        for key in (
            "connector_key",
            "connector_run_target_id",
            "connector_origin_receipt_hash",
            "proof_class",
        )
    } == {
        key: origin_integrity[key]
        for key in (
            "connector_key",
            "connector_run_target_id",
            "connector_origin_receipt_hash",
            "proof_class",
        )
    }
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
    db_session.expire(pass_run, ["summary_json"])
    assert pass_run.summary_json["execution_result_review"][
        "connector_origin_integrity_v1"
    ] == origin_integrity
    assert pass_run.summary_json["execution_result_review"][
        "connector_output_integrity_v1"
    ] == output_integrity
    alternate_chunk_text = "Reprocessed chunk from a later APS contract version."
    db_session.add(
        ApsContentChunk(
            content_id=flow["content_id"],
            chunk_id=f"{flow['content_id']}-chunk-alt-1",
            content_contract_id="aps_pdf_content_units_v2",
            chunking_contract_id="aps_pdf_chunking_v2",
            chunk_ordinal=0,
            start_char=0,
            end_char=len(alternate_chunk_text),
            chunk_text=alternate_chunk_text,
            chunk_text_sha256=hashlib.sha256(alternate_chunk_text.encode("utf-8")).hexdigest(),
            page_start=1,
            page_end=1,
            unit_kind="pdf_paragraph",
            quality_status="strong",
        )
    )
    db_session.flush()

    preview = layer3_workbench.package_review_preview(
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

    assert preview["schema_id"] == "layer3.qual_aps_package_review_preview.v1"
    assert preview["status"] == "available"
    assert preview["engine_family"] == ENGINE_FAMILY_QUAL_APS_DOCUMENT
    assert preview["pass_scope"] == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
    assert preview["method"] == QUAL_APS_METHOD_NAME
    assert preview["source_gate"] == QUAL_APS_SOURCE_GATE
    assert preview["analysis_run_id"] is None
    assert preview["package_review_preview_enabled"] is True
    assert preview["package_commit_enabled"] is True
    assert preview["package_review_submit_enabled"] is False
    assert preview["handoff_enabled"] is False
    assert preview["aps_handoff_enabled"] is False
    assert preview["external_export_download_enabled"] is False
    assert preview["connector_dispatch_enabled"] is False
    assert preview["provider_public_url_enabled"] is False
    assert preview["content_id"] == "content-qual-aps-package"
    assert preview["chunk_count"] == 2
    assert preview["output_payload_hash"]
    assert db_session.query(L3OutputPackage).count() == 0
    assert db_session.query(L3ReconciliationRecord).count() == 0

    commit = layer3_workbench.package_construction_commit(
        db_session,
        {
            "client_request_id": "req-qual-package-commit",
            "session_id": flow["session_id"],
            "analysis_plan_id": flow["analysis_plan_id"],
            "pass_run_id": flow["pass_run_id"],
            "preview_id": flow["preview_id"],
            "preview_hash": flow["preview_hash"],
            "analysis_run_id": start["analysis_run_id"],
            "result_review_record_ref": review["review_record_ref"],
            "package_review_preview_hash": preview["package_review_preview_hash"],
            "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
        },
    )

    assert commit["schema_id"] == "layer3.qual_aps_package_construction_commit.v1"
    assert commit["status"] == "committed"
    assert commit["package_review_submit_enabled"] is True
    assert commit["package_construction_source_gate"] == "140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE"
    assert commit["content_id"] == "content-qual-aps-package"
    assert commit["output_payload_hash"] == preview["output_payload_hash"]
    assert commit["package_kinds"] == ["canonical_internal", "user_facing", "review_facing"]
    assert len(commit["output_package_ids"]) == 3
    assert len(commit["payload_refs"]) == 3
    assert len(commit["payload_hashes"]) == 3
    assert db_session.query(L3OutputPackage).count() == 3
    assert db_session.query(L3ReconciliationRecord).count() == 1
    reconciliation = db_session.get(
        L3ReconciliationRecord,
        commit["reconciliation_record_id"],
    )
    assert reconciliation is not None
    for package in commit["output_packages"]:
        payload_path = Path(package["payload_ref"])
        assert payload_path.exists()
        assert hashlib.sha256(payload_path.read_bytes()).hexdigest() == package["payload_hash"]
        package_payload = json.loads(
            payload_path.read_text(encoding="utf-8")
        )
        assert package_payload["connector_origin_integrity_v1"] == (
            origin_integrity
        )
        assert package_payload["connector_output_integrity_v1"] == (
            output_integrity
        )

    submit_payload = {
        "client_request_id": "req-qual-package-submit",
        "session_id": flow["session_id"],
        "analysis_plan_id": flow["analysis_plan_id"],
        "pass_run_id": flow["pass_run_id"],
        "preview_id": flow["preview_id"],
        "preview_hash": flow["preview_hash"],
        "result_review_record_ref": review["review_record_ref"],
        "package_review_preview_hash": preview["package_review_preview_hash"],
        "construction_basis_hash": commit["construction_basis_hash"],
        "reconciliation_record_id": commit["reconciliation_record_id"],
        "operator_decision": "approved",
        "output_package_ids": commit["output_package_ids"],
        "payload_refs": commit["payload_refs"],
        "payload_hashes": commit["payload_hashes"],
        "expected_package_kinds": ["canonical_internal", "user_facing", "review_facing"],
    }
    with pytest.raises(Layer3WorkbenchError) as stale_construction_exc:
        layer3_workbench.package_review_submit(
            db_session,
            {**submit_payload, "construction_basis_hash": "stale-construction-basis"},
        )
    assert stale_construction_exc.value.error_code == (
        "qualitative_aps_package_review_submit_construction_basis_mismatch"
    )
    assert db_session.query(L3OutputPackage).count() == 3
    assert db_session.query(L3ReconciliationRecord).count() == 1

    submit = layer3_workbench.package_review_submit(db_session, submit_payload)

    assert submit["schema_id"] == "layer3.qual_aps_package_review_submit.v1"
    assert submit["status"] == "submitted"
    assert submit["analysis_run_id"] is None
    assert submit["construction_basis_hash"] == commit["construction_basis_hash"]
    assert submit["payload_refs"] == commit["payload_refs"]
    assert submit["payload_hashes"] == commit["payload_hashes"]
    assert submit["package_review_state"] == "package_review_approved"
    assert submit["package_review_submit_enabled"] is False
    assert submit["handoff_enabled"] is False
    assert submit["aps_handoff_enabled"] is False
    assert submit["external_export_download_enabled"] is False
    assert submit["connector_dispatch_enabled"] is False
    assert submit["provider_public_url_enabled"] is False
    assert "package_review_submit" not in submit["downstream_unavailable"]
    assert "handoff" in submit["downstream_unavailable"]
    assert "external_export_download" in submit["downstream_unavailable"]
    assert db_session.query(L3OutputPackage).count() == 3
    assert db_session.query(L3ReconciliationRecord).count() == 1
    db_session.refresh(reconciliation)
    submit_state = reconciliation.summary_json[
        "package_review_submit"
    ]
    assert submit_state["connector_origin_integrity_v1"] == (
        origin_integrity
    )
    assert submit_state["connector_output_integrity_v1"] == (
        output_integrity
    )

    replay = layer3_workbench.package_review_submit(db_session, submit_payload)
    assert replay["status"] == "already_submitted"
    assert replay["submit_record_ref"] == submit["submit_record_ref"]

    handoff_payload = {
        "client_request_id": "req-qual-handoff-prepare",
        "session_id": flow["session_id"],
        "analysis_plan_id": flow["analysis_plan_id"],
        "pass_run_id": flow["pass_run_id"],
        "preview_id": flow["preview_id"],
        "preview_hash": flow["preview_hash"],
        "result_review_record_ref": review["review_record_ref"],
        "package_review_preview_hash": preview[
            "package_review_preview_hash"
        ],
        "construction_basis_hash": commit["construction_basis_hash"],
        "reconciliation_record_id": commit["reconciliation_record_id"],
        "package_review_submit_record_ref": submit["submit_record_ref"],
        "package_review_state": submit["package_review_state"],
        "package_review_submit_schema_id": submit["schema_id"],
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
        "operator_decision": "authorize_prepare",
        "output_package_ids": commit["output_package_ids"],
        "payload_refs": commit["payload_refs"],
        "payload_hashes": commit["payload_hashes"],
    }
    handoff = layer3_workbench.handoff_export_prepare(
        db_session,
        handoff_payload,
    )
    assert handoff["schema_id"] == (
        "layer3.qual_aps_handoff_export_prepare.v1"
    )
    assert handoff["status"] == "prepared"
    assert handoff["handoff_export_envelope"][
        "connector_origin_integrity_v1"
    ] == origin_integrity
    assert handoff["handoff_export_envelope"][
        "connector_output_integrity_v1"
    ] == output_integrity

    db_session.refresh(reconciliation)
    original_summary = copy.deepcopy(reconciliation.summary_json)
    prepare_state = original_summary["handoff_export_prepare"]
    assert prepare_state["connector_origin_integrity_v1"] == (
        origin_integrity
    )
    assert prepare_state["connector_output_integrity_v1"] == (
        output_integrity
    )
    assert prepare_state["handoff_export_envelope"][
        "connector_origin_integrity_v1"
    ] == origin_integrity
    assert prepare_state["handoff_export_envelope"][
        "connector_output_integrity_v1"
    ] == output_integrity

    for corruption in ("one_sided_state", "mismatched_envelope"):
        changed_summary = copy.deepcopy(original_summary)
        changed_prepare = changed_summary["handoff_export_prepare"]
        if corruption == "one_sided_state":
            changed_prepare.pop("connector_output_integrity_v1")
        else:
            changed_prepare["handoff_export_envelope"][
                "connector_output_integrity_v1"
            ] = {
                **output_integrity,
                "output_manifest_sha256": "0" * 64,
            }
        reconciliation.summary_json = changed_summary
        db_session.commit()

        with pytest.raises(Layer3WorkbenchError) as replay_exc:
            layer3_workbench.handoff_export_prepare(
                db_session,
                handoff_payload,
            )
        assert replay_exc.value.error_code == (
            "handoff_export_prepare_integrity_mismatch"
        )
        db_session.rollback()

    reconciliation.summary_json = original_summary
    db_session.commit()
    handoff_replay = layer3_workbench.handoff_export_prepare(
        db_session,
        handoff_payload,
    )
    assert handoff_replay["status"] == "already_prepared"
    assert handoff_replay["prepare_record_ref"] == (
        handoff["prepare_record_ref"]
    )
    assert {
        "gate_c_typing",
        "pass_selection",
        "execution_output",
        "result_review",
        "package_commit",
        "package_submit",
        "handoff_prepare",
    } <= set(origin_boundaries)


def test_generic_handoff_integrity_state_remains_pair_free() -> None:
    prepare_state = {
        "operator_decision": "authorize_prepare",
        "handoff_export_envelope": {
            "schema_id": "layer3.handoff_export_envelope.v1",
        },
    }

    layer3_workbench._assert_handoff_prepare_connector_integrity(  # type: ignore[attr-defined]
        prepare_state=prepare_state,
        connector_origin_integrity=None,
        connector_output_integrity=None,
    )

    assert "connector_origin_integrity_v1" not in prepare_state
    assert "connector_output_integrity_v1" not in prepare_state
    assert "connector_origin_integrity_v1" not in prepare_state[
        "handoff_export_envelope"
    ]
    assert "connector_output_integrity_v1" not in prepare_state[
        "handoff_export_envelope"
    ]


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
