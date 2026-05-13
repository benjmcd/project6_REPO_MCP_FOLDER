from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3PassRun,
)
from app.services.layer3_utils import (
    json_clone as _json_clone,
    stable_hash as _stable_hash,
    stable_id as _stable_id,
    stable_json_text as _stable_json_text,
    utc_isoformat as _utc_isoformat,
    utcnow as _utcnow,
)

ENGINE_FAMILY_QUAL_APS_DOCUMENT = "qualitative_aps_document"
PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE = "single_aps_doc_qualitative_pass"
QUAL_APS_METHOD_NAME = "single_aps_doc_qualitative_pass"
QUAL_APS_SOURCE_GATE = "119_L3_QUAL_APS_EXEC_ENTRY_FREEZE"
QUAL_APS_OUTPUT_SCHEMA_ID = "layer3.single_aps_doc_qualitative_output.v1"
ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID = "layer3.analysis_execution_start_state.v1"
QUALITATIVE_BOUNDARY_CONTRACT_SCHEMA_ID = "layer3.qualitative_hybrid_rag_boundary_contract.v1"
QUALITATIVE_BOUNDARY_MODE = "single_aps_doc_qualitative_pass_only"

PASS_TYPE_SINGLE_ITEM = "single_item"
PASS_STATUS_SELECTED_NOT_STARTED = "selected_not_started"
PASS_STATUS_COMPLETED = "completed"
MODALITY_QUALITATIVE = "qualitative"
SOURCE_SHAPE_APS_CONTENT_DOCUMENT = "aps_content_document"
APS_HANDOFF_COMPANION_ANALYSIS_ROLE = "aps_handoff_companion_provenance"
QUALITATIVE_BOUNDARY_DEFERRED_CAPABILITIES = (
    "broad_qualitative_execution",
    "qualitative_associated_cohort_execution",
    "comparative_qualitative_execution",
    "cross_document_synthesis",
    "hybrid_execution",
    "rag_vector_retrieval",
    "hidden_llm_planning",
    "qualitative_package_handoff_export",
)
QUALITATIVE_BOUNDARY_FORBIDDEN_RUNTIME_FIELDS = (
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
)


class Layer3QualApsExecutionError(ValueError):
    pass


@dataclass(frozen=True)
class _QualApsBasis:
    analysis_set: L3AnalysisSet
    analysis_unit: L3AnalysisUnit
    material_snapshot: L3MaterialSnapshot
    document: ApsContentDocument
    chunks: tuple[ApsContentChunk, ...]
    linkages: tuple[ApsContentLinkage, ...]


@dataclass(frozen=True)
class Layer3QualApsExecutionResult:
    pass_run: L3PassRun
    output_payload_ref: str


def qualitative_hybrid_rag_boundary_contract() -> dict[str, Any]:
    return {
        "schema_id": QUALITATIVE_BOUNDARY_CONTRACT_SCHEMA_ID,
        "mode": QUALITATIVE_BOUNDARY_MODE,
        "owner_service": "backend/app/services/layer3_qual_aps_execution.py",
        "admitted_execution_modes": [PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE],
        "admitted_engine_family": ENGINE_FAMILY_QUAL_APS_DOCUMENT,
        "admitted_method_name": QUAL_APS_METHOD_NAME,
        "admitted_source_gate": QUAL_APS_SOURCE_GATE,
        "deferred_capabilities": list(QUALITATIVE_BOUNDARY_DEFERRED_CAPABILITIES),
        "forbidden_runtime_fields": list(QUALITATIVE_BOUNDARY_FORBIDDEN_RUNTIME_FIELDS),
        "single_aps_doc_qualitative_execution_enabled": True,
        "broad_qualitative_execution_enabled": False,
        "qualitative_associated_cohort_execution_enabled": False,
        "comparative_qualitative_execution_enabled": False,
        "cross_document_synthesis_enabled": False,
        "hybrid_execution_enabled": False,
        "rag_vector_retrieval_enabled": False,
        "hidden_llm_planning_enabled": False,
        "qualitative_package_handoff_export_enabled": False,
        "source_widening_enabled": False,
        "connector_destination_dispatch_enabled": False,
        "package_mutation_reconstruction_enabled": False,
        "requires_later_freeze": True,
    }


def is_single_aps_doc_qualitative_planned_pass(*, pass_run: L3PassRun, planned_pass: dict[str, Any]) -> bool:
    return (
        pass_run.pass_type == PASS_TYPE_SINGLE_ITEM
        and pass_run.engine_family == ENGINE_FAMILY_QUAL_APS_DOCUMENT
        and planned_pass.get("pass_type") == PASS_TYPE_SINGLE_ITEM
        and planned_pass.get("pass_scope") == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE
        and planned_pass.get("engine_family") == ENGINE_FAMILY_QUAL_APS_DOCUMENT
        and planned_pass.get("selected_method_name") == QUAL_APS_METHOD_NAME
        and planned_pass.get("source_gate") == QUAL_APS_SOURCE_GATE
    )


def qualitative_aps_candidate_exclusion_reason(
    db: Session,
    *,
    analysis_set: L3AnalysisSet,
    analysis_unit: L3AnalysisUnit,
    material_snapshot: L3MaterialSnapshot,
) -> str | None:
    if (material_snapshot.source_provenance_json or {}).get("analysis_admission_role") == (
        APS_HANDOFF_COMPANION_ANALYSIS_ROLE
    ):
        return "qualitative_aps_companion_provenance_not_pass_candidate"
    if analysis_set.set_type != PASS_TYPE_SINGLE_ITEM:
        return "qualitative_aps_set_type_not_single_item"
    if analysis_set.formation_basis_json.get("analysis_modality") != MODALITY_QUALITATIVE:
        return "qualitative_aps_set_modality_not_qualitative"
    if analysis_unit.analysis_modality != MODALITY_QUALITATIVE:
        return "qualitative_aps_unit_modality_not_qualitative"
    if material_snapshot.source_shape != SOURCE_SHAPE_APS_CONTENT_DOCUMENT:
        return "qualitative_aps_source_shape_not_aps_content_document"

    identity = _snapshot_content_identity(material_snapshot)
    missing_identity = [
        field
        for field in ("content_id", "content_contract_id", "chunking_contract_id")
        if not str(identity.get(field) or "").strip()
    ]
    if missing_identity:
        return "qualitative_aps_source_identity_incomplete"

    document = _load_document(db, identity=identity)
    if document is None:
        return "qualitative_aps_content_document_missing"
    chunks = _load_chunks(db, identity=identity)
    if not chunks:
        return "qualitative_aps_content_chunks_missing"
    if any(not str(chunk.chunk_text or "").strip() for chunk in chunks):
        return "qualitative_aps_content_chunk_empty"
    return None


def execute_single_aps_doc_qualitative_pass(
    db: Session,
    *,
    pass_run: L3PassRun,
    planned_pass: dict[str, Any],
    client_request_id: str,
) -> Layer3QualApsExecutionResult:
    if not is_single_aps_doc_qualitative_planned_pass(pass_run=pass_run, planned_pass=planned_pass):
        raise Layer3QualApsExecutionError("selected pass is not the frozen single APS-document qualitative pass")
    if pass_run.status != PASS_STATUS_SELECTED_NOT_STARTED:
        raise Layer3QualApsExecutionError(
            f"Selected qualitative APS pass run '{pass_run.pass_run_id}' must be selected_not_started"
        )
    if pass_run.output_payload_ref:
        raise Layer3QualApsExecutionError(
            f"Selected qualitative APS pass run '{pass_run.pass_run_id}' already has output metadata"
        )
    if (pass_run.summary_json or {}).get("analysis_run_id"):
        raise Layer3QualApsExecutionError(
            f"Selected qualitative APS pass run '{pass_run.pass_run_id}' must not reference AnalysisRun"
        )

    basis = _load_execution_basis(db, pass_run=pass_run)
    output_payload = _qualitative_output_payload(
        pass_run=pass_run,
        planned_pass=planned_pass,
        basis=basis,
        client_request_id=client_request_id,
    )
    output_payload["output_hash"] = _stable_hash(output_payload)
    output_ref = _persist_output(pass_run_id=pass_run.pass_run_id, payload=output_payload)
    completed_at = _utcnow()

    pass_run.status = PASS_STATUS_COMPLETED
    pass_run.started_at = completed_at
    pass_run.completed_at = completed_at
    pass_run.output_payload_ref = output_ref
    pass_run.summary_json = {
        **_json_clone(pass_run.summary_json or {}),
        "execution_started": True,
        "analysis_run_id": None,
        "dataset_version_id": None,
        "selected_method_name": QUAL_APS_METHOD_NAME,
        "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
        "source_gate": QUAL_APS_SOURCE_GATE,
        "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
        "material_snapshot_id": basis.material_snapshot.material_snapshot_id,
        "analysis_unit_id": basis.analysis_unit.analysis_unit_id,
        "content_id": basis.document.content_id,
        "content_contract_id": basis.document.content_contract_id,
        "chunking_contract_id": basis.document.chunking_contract_id,
        "chunk_ids_json": [chunk.chunk_id for chunk in basis.chunks],
        "chunk_hashes_json": [chunk.chunk_text_sha256 for chunk in basis.chunks],
        "linkage_refs_json": _linkage_refs(basis.linkages),
        "qualitative_output_schema_id": QUAL_APS_OUTPUT_SCHEMA_ID,
        "qualitative_output_hash": output_payload["output_hash"],
        "analysis_execution_start": {
            "schema_id": ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID,
            "client_request_id": client_request_id,
            "state": "execution_pass_completed",
            "started_at": _utc_isoformat(completed_at),
            "completed_at": _utc_isoformat(completed_at),
            "engine_family": ENGINE_FAMILY_QUAL_APS_DOCUMENT,
            "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
        },
    }
    db.flush()
    return Layer3QualApsExecutionResult(pass_run=pass_run, output_payload_ref=output_ref)


def _snapshot_content_identity(snapshot: L3MaterialSnapshot) -> dict[str, str | None]:
    identity = snapshot.source_identity_json or {}
    return {
        "content_id": str(identity.get("content_id") or "").strip() or None,
        "content_contract_id": str(identity.get("content_contract_id") or "").strip() or None,
        "chunking_contract_id": str(identity.get("chunking_contract_id") or "").strip() or None,
    }


def _load_document(db: Session, *, identity: dict[str, str | None]) -> ApsContentDocument | None:
    return (
        db.query(ApsContentDocument)
        .filter(ApsContentDocument.content_id == identity["content_id"])
        .filter(ApsContentDocument.content_contract_id == identity["content_contract_id"])
        .filter(ApsContentDocument.chunking_contract_id == identity["chunking_contract_id"])
        .order_by(ApsContentDocument.updated_at.desc(), ApsContentDocument.aps_content_document_id.desc())
        .first()
    )


def _load_chunks(db: Session, *, identity: dict[str, str | None]) -> list[ApsContentChunk]:
    return (
        db.query(ApsContentChunk)
        .filter(ApsContentChunk.content_id == identity["content_id"])
        .filter(ApsContentChunk.content_contract_id == identity["content_contract_id"])
        .filter(ApsContentChunk.chunking_contract_id == identity["chunking_contract_id"])
        .order_by(ApsContentChunk.chunk_ordinal.asc(), ApsContentChunk.chunk_id.asc())
        .all()
    )


def _load_linkages(db: Session, *, identity: dict[str, str | None]) -> list[ApsContentLinkage]:
    return (
        db.query(ApsContentLinkage)
        .filter(ApsContentLinkage.content_id == identity["content_id"])
        .filter(ApsContentLinkage.content_contract_id == identity["content_contract_id"])
        .filter(ApsContentLinkage.chunking_contract_id == identity["chunking_contract_id"])
        .order_by(ApsContentLinkage.created_at.asc(), ApsContentLinkage.aps_content_linkage_id.asc())
        .all()
    )


def _load_execution_basis(db: Session, *, pass_run: L3PassRun) -> _QualApsBasis:
    analysis_set = db.get(L3AnalysisSet, pass_run.analysis_set_id)
    if analysis_set is None or analysis_set.session_id != pass_run.session_id:
        raise Layer3QualApsExecutionError("qualitative APS execution analysis set is missing or session-mismatched")
    if analysis_set.set_type != PASS_TYPE_SINGLE_ITEM:
        raise Layer3QualApsExecutionError("qualitative APS execution requires exactly one single-item analysis set")
    if analysis_set.formation_basis_json.get("analysis_modality") != MODALITY_QUALITATIVE:
        raise Layer3QualApsExecutionError("qualitative APS execution requires a qualitative analysis set")

    analysis_unit_ids = list(analysis_set.analysis_unit_ids_json or [])
    if len(analysis_unit_ids) != 1:
        raise Layer3QualApsExecutionError("qualitative APS execution requires exactly one analysis unit")
    analysis_unit = db.get(L3AnalysisUnit, analysis_unit_ids[0])
    if analysis_unit is None or analysis_unit.session_id != pass_run.session_id:
        raise Layer3QualApsExecutionError("qualitative APS execution analysis unit is missing or session-mismatched")
    if analysis_unit.analysis_modality != MODALITY_QUALITATIVE:
        raise Layer3QualApsExecutionError("qualitative APS execution requires a qualitative analysis unit")

    snapshot_ids = list(analysis_unit.member_snapshot_ids_json or [])
    if len(snapshot_ids) != 1:
        raise Layer3QualApsExecutionError("qualitative APS execution requires exactly one material snapshot")
    snapshot = db.get(L3MaterialSnapshot, snapshot_ids[0])
    if snapshot is None or snapshot.session_id != pass_run.session_id:
        raise Layer3QualApsExecutionError("qualitative APS execution material snapshot is missing or session-mismatched")
    exclusion_reason = qualitative_aps_candidate_exclusion_reason(
        db,
        analysis_set=analysis_set,
        analysis_unit=analysis_unit,
        material_snapshot=snapshot,
    )
    if exclusion_reason is not None:
        raise Layer3QualApsExecutionError(exclusion_reason)

    identity = _snapshot_content_identity(snapshot)
    document = _load_document(db, identity=identity)
    chunks = _load_chunks(db, identity=identity)
    assert document is not None
    return _QualApsBasis(
        analysis_set=analysis_set,
        analysis_unit=analysis_unit,
        material_snapshot=snapshot,
        document=document,
        chunks=tuple(chunks),
        linkages=tuple(_load_linkages(db, identity=identity)),
    )


def _qualitative_output_payload(
    *,
    pass_run: L3PassRun,
    planned_pass: dict[str, Any],
    basis: _QualApsBasis,
    client_request_id: str,
) -> dict[str, Any]:
    output_items = [
        _chunk_output_item(
            pass_run=pass_run,
            basis=basis,
            chunk=chunk,
            index=index,
        )
        for index, chunk in enumerate(basis.chunks)
    ]
    return {
        "schema_id": QUAL_APS_OUTPUT_SCHEMA_ID,
        "client_request_id": client_request_id,
        "analysis_run_id": None,
        "analysis_set_id": pass_run.analysis_set_id,
        "dataset_version_id": None,
        "selected_method_name": QUAL_APS_METHOD_NAME,
        "artifact_refs_json": [],
        "artifact_types_json": [],
        "source_gate": QUAL_APS_SOURCE_GATE,
        "pass_scope": PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE,
        "engine_family": ENGINE_FAMILY_QUAL_APS_DOCUMENT,
        "pass_type": PASS_TYPE_SINGLE_ITEM,
        "planned_pass": _json_clone(planned_pass),
        "session_id": pass_run.session_id,
        "analysis_plan_id": pass_run.analysis_plan_id,
        "pass_run_id": pass_run.pass_run_id,
        "material_snapshot_id": basis.material_snapshot.material_snapshot_id,
        "analysis_unit_id": basis.analysis_unit.analysis_unit_id,
        "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
        "document_identity": {
            "aps_content_document_id": basis.document.aps_content_document_id,
            "content_id": basis.document.content_id,
            "content_contract_id": basis.document.content_contract_id,
            "chunking_contract_id": basis.document.chunking_contract_id,
            "normalization_contract_id": basis.document.normalization_contract_id,
            "content_status": basis.document.content_status,
            "media_type": basis.document.media_type,
            "document_class": basis.document.document_class,
            "quality_status": basis.document.quality_status,
            "normalized_text_sha256": basis.document.normalized_text_sha256,
        },
        "chunk_summary": {
            "chunk_count": len(basis.chunks),
            "chunk_ids": [chunk.chunk_id for chunk in basis.chunks],
            "chunk_hashes": [chunk.chunk_text_sha256 for chunk in basis.chunks],
            "ordering": "chunk_ordinal_then_chunk_id",
        },
        "linkage_refs": _linkage_refs(basis.linkages),
        "output_items_json": output_items,
        "caveats_json": _caveats(basis=basis),
    }


def _chunk_output_item(
    *,
    pass_run: L3PassRun,
    basis: _QualApsBasis,
    chunk: ApsContentChunk,
    index: int,
) -> dict[str, Any]:
    text = str(chunk.chunk_text or "").strip()
    return {
        "item_ref": _stable_id(
            "l3-qual-aps-item",
            {
                "pass_run_id": pass_run.pass_run_id,
                "chunk_id": chunk.chunk_id,
                "chunk_hash": chunk.chunk_text_sha256,
            },
        ),
        "item_type": "finding",
        "finding_kind": "chunk_observation",
        "content_id": basis.document.content_id,
        "chunk_id": chunk.chunk_id,
        "chunk_ordinal": chunk.chunk_ordinal,
        "chunk_text_sha256": chunk.chunk_text_sha256,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "text_char_count": len(text),
        "bounded_text_preview": _bounded_preview(text),
        "highlight_spans": _highlight_spans_for_chunk(text),
        "trace": {
            "session_id": pass_run.session_id,
            "analysis_plan_id": pass_run.analysis_plan_id,
            "pass_run_id": pass_run.pass_run_id,
            "material_snapshot_id": basis.material_snapshot.material_snapshot_id,
            "analysis_unit_id": basis.analysis_unit.analysis_unit_id,
            "content_id": basis.document.content_id,
            "content_contract_id": basis.document.content_contract_id,
            "chunking_contract_id": basis.document.chunking_contract_id,
            "chunk_id": chunk.chunk_id,
            "chunk_text_sha256": chunk.chunk_text_sha256,
            "source_shape": SOURCE_SHAPE_APS_CONTENT_DOCUMENT,
        },
        "ordinal": index,
    }


def _bounded_preview(text: str, *, limit: int = 160) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def _highlight_spans_for_chunk(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    return [
        {
            "start": 0,
            "end": len(text),
            "source": "citations[].highlight_spans",
        }
    ]


def _linkage_refs(linkages: tuple[ApsContentLinkage, ...] | list[ApsContentLinkage]) -> list[dict[str, Any]]:
    return [
        {
            "aps_content_linkage_id": linkage.aps_content_linkage_id,
            "run_id": linkage.run_id,
            "target_id": linkage.target_id,
            "accession_number": linkage.accession_number,
            "content_units_ref": linkage.content_units_ref,
            "normalized_text_ref": linkage.normalized_text_ref,
            "selection_ref": linkage.selection_ref,
            "discovery_ref": linkage.discovery_ref,
            "diagnostics_ref": linkage.diagnostics_ref,
        }
        for linkage in linkages
    ]


def _caveats(*, basis: _QualApsBasis) -> list[dict[str, Any]]:
    caveats: list[dict[str, Any]] = [
        {
            "caveat_code": "deterministic_extract_only",
            "message": "Output is deterministic chunk-level qualitative material; no hidden LLM planning or synthesis was used.",
        }
    ]
    if not basis.linkages:
        caveats.append(
            {
                "caveat_code": "aps_linkage_missing",
                "message": "APS content linkage rows were not present; output is bound to ApsContentDocument and chunk rows only.",
            }
        )
    return caveats


def _persist_output(*, pass_run_id: str, payload: dict[str, Any]) -> str:
    output_dir = Path(settings.artifact_storage_dir) / "layer3"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"l3_qual_aps_output_{pass_run_id}.json"
    output_path.write_text(_stable_json_text(payload), encoding="utf-8")
    return str(output_path)
