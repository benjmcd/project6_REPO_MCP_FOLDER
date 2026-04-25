from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3MaterialSnapshot,
    L3PassRun,
    L3SelectionManifest,
    L3Session,
    L3TypingRecord,
    uuid_str,
)
from app.services.layer3_pass_entry import (
    PLAN_PREVIEW_HASH_SCHEMA_ID,
    Layer3PassEntryError,
    approve_pass_entry_plan,
    preview_pass_entry,
)
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_typing_entry import (
    SUPPORTED_TYPING_RULES,
    Layer3TypingEntryError,
    materialize_typing_entry,
)

SCHEMA_VERSION = 1
ROUTE = "/review/layer3"
API_ROOT = "/api/v1/layer3"
SUPPORTED_SOURCE_CLASSES = ("dataset_version", "aps_content_document")
UNSUPPORTED_SOURCE_CLASSES = (
    "rag_vector_index",
    "arbitrary_local_directory",
    "broad_file_upload",
    "web_connector",
    "unbounded_runtime_db",
)
GATE_LABELS = ("intent", "sources", "gate_b", "gate_c", "plan", "execution", "results", "package")
ACTIVE_GATES = ("intent", "sources", "gate_b", "gate_c")
DOWNSTREAM_UNAVAILABLE = ("plan", "execution", "results", "package")
PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE = ("execution", "results", "package")
GATE_B_DECISIONS = ("approved", "denied", "isolated", "flagged")
PLAN_PREVIEW_SCOPE = "owner_service_default"
PLAN_APPROVAL_SCOPE = "owner_service_default"
PLAN_PREVIEW_IDENTITY_SCHEMA_ID = "layer3.plan_preview_identity.v1"
EXECUTION_READINESS_SCHEMA_ID = "layer3.execution_readiness_contract.v1"
EXECUTION_SELECTION_SCHEMA_ID = "layer3.execution_selection.v1"
EXECUTION_SELECTION_STATE_SCHEMA_ID = "layer3.execution_selection_state.v1"
EXECUTION_SELECTION_STATE = "execution_selected_not_started"
STATE_MODEL_SCHEMA_ID = "layer3.workbench_state_model.v1"
PLAN_REVISION_DECISIONS = frozenset({"reject_current_preview", "request_revision"})
PLAN_REVISION_STATE_BY_DECISION = {
    "reject_current_preview": "plan_rejected",
    "request_revision": "plan_revision_requested",
}
PLAN_APPROVAL_FORBIDDEN_FIELDS = frozenset(
    {
        "execute",
        "execution",
        "run",
        "run_analysis",
        "package",
        "package_review",
        "handoff",
        "plan_edits",
        "natural_language_plan",
        "llm_plan",
    }
)
PLAN_REVISION_FORBIDDEN_FIELDS = PLAN_APPROVAL_FORBIDDEN_FIELDS | frozenset(
    {
        "execution_started",
        "create_pass_runs",
        "pass_run_ids",
        "artifact_manifest",
        "result_review",
        "qualitative_plan",
        "hybrid_plan",
        "rag_plan",
        "vector_plan",
    }
)
EXECUTION_SELECTION_FORBIDDEN_FIELDS = frozenset(
    {
        "execute",
        "execution",
        "run",
        "run_analysis",
        "start_execution",
        "analysis_run_id",
        "analysis_run_ids",
        "result_review",
        "results",
        "package",
        "package_review",
        "handoff",
        "artifact_manifest",
        "local_upload",
        "local_directory",
        "rag_plan",
        "vector_plan",
        "qualitative_plan",
        "hybrid_plan",
    }
)
EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE = ("analysis_execution", "results", "package", "handoff")
PLAN_PREVIEW_HASH_INCLUDED_INPUTS = (
    "session_id",
    "committed_gate_b_material_and_source_ids",
    "committed_gate_c_analysis_set_unit_group_ids",
    "owner_service_plan_version",
    "admissible_and_excluded_set_payloads",
    "planned_pass_payloads",
    "deterministic_warning_codes",
)
PLAN_PREVIEW_HASH_EXCLUDED_INPUTS = (
    "browser_render_order",
    "local_ui_labels",
    "non_semantic_timestamps",
    "collapsed_or_expanded_ui_state",
    "non_authoritative_explanatory_text",
    "unpersisted_generated_alternatives",
)
READINESS_REQUIRED_GATES = (
    "proof-manifest",
    "state-model",
    "preview-hash",
    "idempotency",
    "concurrency",
    "revision-recovery",
    "approved-plan-correction",
    "output-taxonomy",
    "source-breadth",
    "execution-selection",
    "browser-proof",
)
READINESS_IMPLEMENTED_GATES = (
    "proof-manifest",
    "state-model",
    "preview-hash",
    "idempotency",
    "concurrency",
    "execution-selection",
)
READINESS_DEFERRED_GATES = (
    "revision-recovery",
    "approved-plan-correction",
    "output-taxonomy",
    "source-breadth",
    "browser-proof",
)


@dataclass(frozen=True)
class Layer3WorkbenchError(ValueError):
    error_code: str
    message: str
    status: str = "invalid"
    http_status: int = 400
    recoverable: bool = True
    blocked_fields: list[str] = field(default_factory=list)
    next_allowed_actions: list[str] = field(default_factory=list)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def _stable_id(prefix: str, payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:16]}"


def _base_response(schema_id: str, *, request_id: str | None = None, status: str = "ok") -> dict[str, Any]:
    return {
        "schema_id": schema_id,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id or uuid_str(),
        "server_time": _utcnow_iso(),
        "status": status,
    }


def workbench_error_response(exc: Layer3WorkbenchError, *, request_id: str | None = None) -> dict[str, Any]:
    return {
        **_base_response("layer3.workbench_error.v1", request_id=request_id, status=exc.status),
        "error_code": exc.error_code,
        "message": exc.message,
        "recoverable": exc.recoverable,
        "blocked_fields": list(exc.blocked_fields),
        "next_allowed_actions": list(exc.next_allowed_actions),
    }


def _authority_rail(
    *,
    session_id: str | None = None,
    preflight_id: str | None = None,
    source_set_id: str | None = None,
    current_gate: str = "intent",
    persistence_mode: str = "not_committed",
    source_classes: list[str] | None = None,
    counts: dict[str, int] | None = None,
    typing_status: str = "not_started",
    browser_only_state: list[str] | None = None,
    downstream_unavailable: list[str] | tuple[str, ...] | None = None,
    execution_enabled: bool = False,
    package_review_enabled: bool = False,
) -> dict[str, Any]:
    gate_counts = counts or {}
    return {
        "schema_id": "layer3.authority_rail.v1",
        "schema_version": SCHEMA_VERSION,
        "session_id": session_id or "none",
        "preflight_id": preflight_id or "none",
        "source_set_id": source_set_id or "none",
        "current_gate": current_gate,
        "persistence_mode": persistence_mode,
        "source_authority": {
            "source_classes": list(source_classes or []),
            "runtime_label": None,
            "database_label": None,
            "storage_label": None,
        },
        "approved_material_count": gate_counts.get("approved", 0),
        "denied_material_count": gate_counts.get("denied", 0),
        "isolated_material_count": gate_counts.get("isolated", 0),
        "flagged_material_count": gate_counts.get("flagged", 0),
        "typing_status": typing_status,
        "execution_enabled": execution_enabled,
        "package_review_enabled": package_review_enabled,
        "downstream_unavailable": list(downstream_unavailable or DOWNSTREAM_UNAVAILABLE),
        "browser_only_state": list(browser_only_state or []),
    }


def _workbench_state_model() -> dict[str, Any]:
    return {
        "schema_id": STATE_MODEL_SCHEMA_ID,
        "authority_order": [
            "durable_layer3_session_state",
            "committed_gate_b_and_gate_c_decisions",
            "server_owner_service_preview",
            "persisted_approval_or_revision_control_state",
            "browser_display_cache_only",
        ],
        "states": [
            {
                "state": "intent_preflight_ready",
                "authority_source": "server_preflight_validation",
                "allowed_next_actions": ["source_preview"],
                "forbidden_downstream_actions": ["plan", "execution", "results", "package"],
            },
            {
                "state": "source_preview_ready",
                "authority_source": "server_source_preview",
                "allowed_next_actions": ["material_preview"],
                "forbidden_downstream_actions": ["plan", "execution", "results", "package"],
            },
            {
                "state": "material_preview_ready",
                "authority_source": "server_material_preview",
                "allowed_next_actions": ["gate_b_decision"],
                "forbidden_downstream_actions": ["plan", "execution", "results", "package"],
            },
            {
                "state": "gate_b_committed",
                "authority_source": "l3_session_and_l3_selection_manifest",
                "allowed_next_actions": ["gate_c_preview", "gate_c_commit"],
                "forbidden_downstream_actions": ["execution", "results", "package"],
            },
            {
                "state": "gate_c_typing_committed",
                "authority_source": "l3_typing_record_and_l3_analysis_set",
                "allowed_next_actions": ["plan_preview"],
                "forbidden_downstream_actions": ["execution", "results", "package"],
            },
            {
                "state": "plan_preview_ready",
                "authority_source": "server_owner_service_preview",
                "allowed_next_actions": ["plan_approve", "plan_reject", "plan_request_revision"],
                "forbidden_downstream_actions": ["execution", "results", "package"],
            },
            {
                "state": "plan_approved",
                "authority_source": "l3_analysis_plan_approval_only",
                "allowed_next_actions": ["execution_select"],
                "forbidden_downstream_actions": ["analysis_execution", "results", "package", "handoff"],
            },
            {
                "state": EXECUTION_SELECTION_STATE,
                "authority_source": "server_created_l3_pass_run_shell",
                "allowed_next_actions": [],
                "forbidden_downstream_actions": ["analysis_execution", "results", "package", "handoff"],
            },
            {
                "state": "plan_rejected",
                "authority_source": "l3_session_summary_plan_revision_control",
                "allowed_next_actions": [],
                "forbidden_downstream_actions": ["approval", "execution", "results", "package"],
            },
            {
                "state": "plan_revision_requested",
                "authority_source": "l3_session_summary_plan_revision_control",
                "allowed_next_actions": [],
                "forbidden_downstream_actions": ["approval", "execution", "results", "package"],
            },
            {
                "state": "execution_readiness_blocked",
                "authority_source": "layer3_execution_readiness_contract",
                "allowed_next_actions": ["resolve_deferred_readiness_gates"],
                "forbidden_downstream_actions": ["execution", "results", "package"],
            },
        ],
    }


def _plan_preview_hash_contract() -> dict[str, Any]:
    return {
        "schema_id": PLAN_PREVIEW_HASH_SCHEMA_ID,
        "authority_source": "server_owner_service_preview",
        "included_inputs": list(PLAN_PREVIEW_HASH_INCLUDED_INPUTS),
        "excluded_inputs": list(PLAN_PREVIEW_HASH_EXCLUDED_INPUTS),
        "mismatch_error_code": "preview_mismatch",
        "mismatch_rule": "fail_closed_no_execution_or_artifact_writes",
    }


def _preview_identity(*, preview_id: str, preview_hash: str) -> dict[str, Any]:
    return {
        "schema_id": PLAN_PREVIEW_IDENTITY_SCHEMA_ID,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "preview_hash_schema_id": PLAN_PREVIEW_HASH_SCHEMA_ID,
        "authority_source": "server_owner_service_preview",
        "stale_preview_writes_blocked": True,
        "mismatch_error_code": "preview_mismatch",
    }


def readiness_contract() -> dict[str, Any]:
    return {
        **_base_response(EXECUTION_READINESS_SCHEMA_ID),
        "execution_admitted": False,
        "execution_enabled": False,
        "execution_selection_admitted": True,
        "execution_selection_endpoint": f"{API_ROOT}/execution/select",
        "analysis_execution_admitted": False,
        "readiness_state": "execution_readiness_blocked",
        "required_gates": list(READINESS_REQUIRED_GATES),
        "implemented_gates": list(READINESS_IMPLEMENTED_GATES),
        "deferred_gates": list(READINESS_DEFERRED_GATES),
        "state_model": _workbench_state_model(),
        "preview_hash_contract": _plan_preview_hash_contract(),
        "idempotency_contract": {
            "schema_id": "layer3.idempotency_contract.v1",
            "client_request_id_supported": True,
            "client_request_id_required_current_slice": False,
            "client_request_id_required_for_execution_selection": True,
            "duplicate_plan_approval": "returns existing approved-plan conflict; no duplicate L3AnalysisPlan",
            "duplicate_plan_revision": "returns existing revision-control conflict; no duplicate revision-control state",
            "duplicate_execution_selection": "same client_request_id and same approved plan returns existing selection; conflicts fail closed",
            "duplicate_without_client_request_id": "server-authoritative state conflicts still prevent duplicate durable approval or revision-control state",
            "analysis_execution": "not admitted until separately frozen",
        },
        "concurrency_contract": {
            "schema_id": "layer3.concurrency_contract.v1",
            "approval_revision_mutual_exclusion": True,
            "server_authority": "durable_session_row_lock_or_equivalent_transaction",
            "browser_in_flight_lock_is_authoritative": False,
            "execution_selection_uses_session_and_plan_locks": True,
            "analysis_execution_requires_separate_locking_freeze": True,
        },
        "deferred_decisions": {
            "schema_id": "layer3.deferred_execution_decisions.v1",
            "revision_recovery": "requires later freeze",
            "approved_plan_correction": "requires later freeze",
            "output_taxonomy": "requires later freeze before results or package UI",
            "source_breadth": "requires later freeze before RAG/vector/upload/local-directory expansion",
        },
    }


def bootstrap() -> dict[str, Any]:
    return {
        **_base_response("layer3.workbench_bootstrap.v1"),
        "route": ROUTE,
        "api_root": API_ROOT,
        "supported_source_classes": list(SUPPORTED_SOURCE_CLASSES),
        "preview_only_source_classes": [],
        "unsupported_source_classes": list(UNSUPPORTED_SOURCE_CLASSES),
        "gate_labels": list(GATE_LABELS),
        "active_gate_labels": list(ACTIVE_GATES),
        "unavailable_gate_labels": list(DOWNSTREAM_UNAVAILABLE),
        "features": {
            "plan_preview": True,
            "plan_approval": True,
            "execution_selection": True,
            "analysis_execution": False,
            "qualitative_execution": False,
            "hybrid_execution": False,
            "rag_vector_retrieval": False,
            "package_review": False,
            "handoff": False,
            "runtime_snapshot_db_writes": False,
            "schema_widening": False,
            "typing_override_enabled": False,
        },
        "execution_readiness": {
            "schema_id": EXECUTION_READINESS_SCHEMA_ID,
            "execution_admitted": False,
            "execution_enabled": False,
            "execution_selection_admitted": True,
            "execution_selection_endpoint": f"{API_ROOT}/execution/select",
            "analysis_execution_admitted": False,
            "readiness_state": "execution_readiness_blocked",
            "readiness_endpoint": f"{API_ROOT}/readiness",
        },
        "authority_rail": _authority_rail(
            current_gate="intent",
            browser_only_state=["expanded_rows", "hidden_uncommitted_candidates", "selected_tab"],
        ),
    }


def _manual_constraints(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("manual_constraints") or {}
    return value if isinstance(value, dict) else {}


def _requested_source_classes(manual_constraints: dict[str, Any]) -> list[str]:
    source_classes = manual_constraints.get("source_classes") or []
    if not source_classes:
        return list(SUPPORTED_SOURCE_CLASSES)
    return [str(item) for item in source_classes]


def _unsupported_requested(classes: list[str]) -> list[str]:
    return [item for item in classes if item not in SUPPORTED_SOURCE_CLASSES]


def preflight(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    intent = str(payload.get("natural_language_intent") or "").strip()
    manual_constraints = _manual_constraints(payload)
    if not intent:
        raise Layer3WorkbenchError(
            "empty_intent",
            "Natural-language intent is required before source selection.",
            status="blocked",
            blocked_fields=["natural_language_intent"],
            next_allowed_actions=["edit_intent"],
        )
    if manual_constraints.get("conflict") is True or manual_constraints.get("conflicts"):
        raise Layer3WorkbenchError(
            "conflicting_constraints",
            "Manual constraints declare a conflict that must be resolved before source selection.",
            status="blocked",
            blocked_fields=["manual_constraints"],
            next_allowed_actions=["edit_constraints"],
        )
    source_classes = _requested_source_classes(manual_constraints)
    unsupported = _unsupported_requested(source_classes)
    if unsupported:
        raise Layer3WorkbenchError(
            "unsupported_source_class",
            f"Unsupported source class requested: {', '.join(unsupported)}.",
            status="blocked",
            blocked_fields=["manual_constraints.source_classes"],
            next_allowed_actions=["choose_supported_sources"],
        )
    normalized = {
        "intent_text": " ".join(intent.split()),
        "manual_constraints": _json_clone(manual_constraints),
    }
    preflight_id = _stable_id("preflight", normalized)
    return {
        **_base_response("layer3.preflight_result.v1", request_id=request_id),
        "preflight_id": preflight_id,
        "normalized_intent": normalized,
        "blockers": [],
        "warnings": [],
        "eligible_for_source_selection": True,
        "authority_rail": _authority_rail(
            preflight_id=preflight_id,
            current_gate="sources",
            persistence_mode="preview_only",
            source_classes=source_classes,
        ),
    }


def source_preview(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    preflight_id = str(payload.get("preflight_id") or "").strip()
    if not preflight_id:
        raise Layer3WorkbenchError("empty_intent", "preflight_id is required for source preview.", status="blocked")
    requested = [str(item) for item in payload.get("selected_source_classes") or SUPPORTED_SOURCE_CLASSES]
    unsupported = _unsupported_requested(requested)
    if unsupported:
        raise Layer3WorkbenchError(
            "unsupported_source_class",
            f"Unsupported source class requested: {', '.join(unsupported)}.",
            status="blocked",
            blocked_fields=["selected_source_classes"],
            next_allowed_actions=["choose_supported_sources"],
        )
    candidates = []
    for source_class in requested:
        short_id = _stable_id("src", {"preflight_id": preflight_id, "source_class": source_class}).split("-", 1)[1]
        candidates.append(
            {
                "source_candidate_id": f"src-{source_class}-{short_id}",
                "source_class": source_class,
                "source_label": source_class.replace("_", " ").title(),
                "source_ref": f"{source_class}:preview:{short_id}",
                "source_authority": "repo_supported",
                "eligible_for_material_preview": True,
                "unavailable_reason": None,
            }
        )
    source_set_id = _stable_id("source-set", [item["source_candidate_id"] for item in candidates])
    return {
        **_base_response("layer3.source_preview_result.v1", request_id=request_id),
        "source_set_id": source_set_id,
        "source_candidates": candidates,
        "unsupported_sources": [],
        "authority_rail": _authority_rail(
            preflight_id=preflight_id,
            source_set_id=source_set_id,
            current_gate="gate_b",
            persistence_mode="preview_only",
            source_classes=requested,
        ),
    }


def _source_class_from_source_candidate_id(source_candidate_id: str) -> str | None:
    for source_class in SUPPORTED_SOURCE_CLASSES:
        if source_candidate_id.startswith(f"src-{source_class}-"):
            return source_class
    return None


def _source_class_from_material_candidate_id(candidate_id: str) -> str | None:
    for source_class in SUPPORTED_SOURCE_CLASSES:
        if candidate_id.startswith(f"mat-{source_class}-"):
            return source_class
    return None


def material_preview(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    source_ids = [str(item) for item in payload.get("source_candidate_ids") or []]
    if not source_ids:
        raise Layer3WorkbenchError("no_source_candidates", "At least one source candidate is required.", status="blocked")
    terms = [str(item) for item in (payload.get("query_basis") or {}).get("terms") or []]
    query_label = ", ".join(terms) if terms else "operator_intent"
    candidates = []
    for source_id in source_ids:
        source_class = _source_class_from_source_candidate_id(source_id)
        if source_class is None:
            raise Layer3WorkbenchError("invalid_material_candidate", f"Unknown source candidate: {source_id}.")
        short_id = _stable_id("mat", {"source_id": source_id, "query_basis": query_label}).split("-", 1)[1]
        planning_shape = "tabular_numeric" if source_class == "dataset_version" else "document_chunks"
        candidates.append(
            {
                "candidate_id": f"mat-{source_class}-{short_id}",
                "source_label": source_class.replace("_", " ").title(),
                "source_class": source_class,
                "source_ref": f"{source_class}:preview:{short_id}",
                "owner_service_source_shape": source_class,
                "planning_shape_family": planning_shape,
                "query_basis": query_label,
                "validation_status": "valid",
                "duplicate_status": "unique",
                "size_or_unit_count": 1,
                "preview_payload_ref": None,
                "provenance_ref": f"layer3-preview:{short_id}",
                "current_decision_state": "candidate",
            }
        )
    preview_id = _stable_id("material-preview", [item["candidate_id"] for item in candidates])
    return {
        **_base_response("layer3.material_preview_result.v1", request_id=request_id),
        "material_preview_id": preview_id,
        "material_candidates": candidates,
        "partial_retrieval": False,
        "authority_rail": _authority_rail(
            preflight_id=str(payload.get("preflight_id") or "none"),
            source_set_id=str(payload.get("source_set_id") or "none"),
            current_gate="gate_b",
            persistence_mode="preview_only",
            source_classes=sorted({item["source_class"] for item in candidates}),
        ),
    }


def _gate_b_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    return {decision: sum(1 for item in decisions if item["decision"] == decision) for decision in GATE_B_DECISIONS}


def _candidate_decision_manifest(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema_id": "layer3.gate_b_decision_manifest.v1", "schema_version": SCHEMA_VERSION, "items": _json_clone(decisions)}


def gate_b_decision(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    raw_decisions = payload.get("candidate_decisions") or []
    if not isinstance(raw_decisions, list) or not raw_decisions:
        raise Layer3WorkbenchError("no_approved_material", "At least one Gate B decision is required.", status="blocked")

    decisions: list[dict[str, Any]] = []
    for raw in raw_decisions:
        if not isinstance(raw, dict):
            raise Layer3WorkbenchError("invalid_material_candidate", "Gate B decision entries must be objects.")
        candidate_id = str(raw.get("candidate_id") or "").strip()
        source_class = _source_class_from_material_candidate_id(candidate_id)
        decision = str(raw.get("decision") or "").strip()
        reason = str(raw.get("operator_reason") or "").strip()
        if source_class is None:
            raise Layer3WorkbenchError("invalid_material_candidate", f"Unknown material candidate: {candidate_id}.")
        if decision not in GATE_B_DECISIONS:
            raise Layer3WorkbenchError("invalid_material_candidate", f"Unsupported Gate B decision: {decision}.")
        if decision in {"denied", "isolated", "flagged"} and not reason:
            raise Layer3WorkbenchError(
                "invalid_material_candidate",
                f"Decision '{decision}' requires an operator reason.",
                blocked_fields=["candidate_decisions.operator_reason"],
            )
        decision_basis = raw.get("decision_basis") if isinstance(raw.get("decision_basis"), dict) else {}
        decisions.append(
            {
                "candidate_id": candidate_id,
                "source_class": source_class,
                "decision": decision,
                "operator_reason": reason,
                "decision_basis": _json_clone(decision_basis),
            }
        )

    approved = [item for item in decisions if item["decision"] == "approved"]
    if not approved:
        raise Layer3WorkbenchError(
            "no_approved_material",
            "At least one material candidate must be approved before Gate C.",
            status="blocked",
            next_allowed_actions=["approve_material", "revise_sources"],
        )

    counts = _gate_b_counts(decisions)
    decision_manifest = _candidate_decision_manifest(decisions)
    manifest_items = []
    for item in approved:
        short_id = hashlib.sha256(item["candidate_id"].encode("utf-8")).hexdigest()[:12]
        manifest_items.append(
            {
                "source_plane": f"plane_{item['source_class']}_{short_id}",
                "descriptor_type": item["source_class"],
                "selector_payload": {
                    "candidate_id": item["candidate_id"],
                    "source_ref": item["decision_basis"].get("source_ref", item["candidate_id"]),
                },
                "selection_basis": {
                    "candidate_id": item["candidate_id"],
                    "query_basis": item["decision_basis"].get("query_basis", "operator_intent"),
                    "provenance_ref": item["decision_basis"].get("provenance_ref", "layer3-preview"),
                    "gate_b_decision": "approved",
                },
                "expansion_reason": "gate_b_approved_material",
            }
        )

    session, manifest = commit_selection(
        db,
        SessionEntryRequest(
            manifest_items=manifest_items,
            source_plane_hints={
                "preflight_id": payload.get("preflight_id"),
                "source_set_id": payload.get("source_set_id"),
                "source_classes": sorted({item["source_class"] for item in approved}),
            },
            commit_reason=str(payload.get("commit_reason") or "operator_gate_b_decision"),
            entry_route_context={"route": ROUTE, "api_root": API_ROOT, "slice": "workbench_first_slice"},
            operator_context={"actor": payload.get("actor") or "operator", "layer3_gate_b_decision_manifest_v1": decision_manifest},
            summary={"current_gate": "gate_c", "gate_b_summary_v1": counts},
        ),
    )
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    for descriptor, item in zip(descriptors, approved, strict=True):
        record_retrieval_event(
            db,
            session=session,
            descriptor=descriptor,
            outcome="loaded",
            reason_code="gate_b_approved_preview_material",
            loaded_materials=[
                SnapshotMaterial(
                    source_shape=item["source_class"],
                    source_identity={"candidate_id": item["candidate_id"], "source_class": item["source_class"]},
                    source_provenance=item["decision_basis"],
                    payload={"candidate_id": item["candidate_id"], "source_class": item["source_class"], "decision": "approved"},
                    load_summary={"loaded_records": 1, "failed_records": 0, "preview_material": True},
                )
            ],
        )
    finalize_session(db, session=session)
    db.commit()
    return {
        **_base_response("layer3.gate_b_decision_result.v1", request_id=request_id),
        "session_id": session.session_id,
        "selection_manifest_id": manifest.selection_manifest_id,
        "gate_b_decision_manifest_id": _stable_id("gate-b", decision_manifest),
        "approved_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "approved"],
        "denied_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "denied"],
        "isolated_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "isolated"],
        "flagged_candidate_ids": [item["candidate_id"] for item in decisions if item["decision"] == "flagged"],
        "next_state": "gate_c_preview_ready",
        "authority_rail": _authority_rail(
            session_id=session.session_id,
            preflight_id=str(payload.get("preflight_id") or "none"),
            source_set_id=str(payload.get("source_set_id") or "none"),
            current_gate="gate_c",
            persistence_mode="durable_layer3_control",
            source_classes=sorted({item["source_class"] for item in approved}),
            counts=counts,
        ),
    }


def _load_session(db: Session, session_id: str) -> L3Session:
    session = db.get(L3Session, session_id)
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    return session


def _source_classes_from_latest_manifest(db: Session, session_id: str) -> list[str]:
    manifest = (
        db.query(L3SelectionManifest)
        .filter(L3SelectionManifest.session_id == session_id)
        .order_by(L3SelectionManifest.committed_at.desc())
        .first()
    )
    if manifest is None:
        return []
    hints = manifest.source_plane_hints_json or {}
    hinted_classes = hints.get("source_classes")
    if isinstance(hinted_classes, list):
        return sorted({str(item) for item in hinted_classes if item is not None and str(item).strip()})
    items = (manifest.manifest_json or {}).get("items") or []
    return sorted(
        {
            str(item.get("descriptor_type"))
            for item in items
            if isinstance(item, dict) and str(item.get("descriptor_type") or "").strip()
        }
    )


def _snapshot_projection(snapshot: L3MaterialSnapshot) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    rule = SUPPORTED_TYPING_RULES.get(snapshot.source_shape)
    if rule is None:
        return None, {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "owner_service_source_shape": snapshot.source_shape,
            "reason": "unsupported_typing_shape",
        }
    return {
        "typing_record_id": None,
        "material_snapshot_id": snapshot.material_snapshot_id,
        "owner_service_source_shape": snapshot.source_shape,
        "planning_shape_family": rule.planning_shape_family,
        "candidate_modalities": list(rule.candidate_modalities),
        "chosen_modality": rule.chosen_modality,
        "confidence": rule.confidence,
        "authoritative": False,
    }, None


def _serialize_typing_record(record: L3TypingRecord) -> dict[str, Any]:
    basis = record.typing_basis_json or {}
    return {
        "typing_record_id": record.typing_record_id,
        "material_snapshot_id": record.material_snapshot_id,
        "owner_service_source_shape": basis.get("source_shape"),
        "planning_shape_family": basis.get("planning_shape_family"),
        "candidate_modalities": list(record.candidate_modalities_json or []),
        "chosen_modality": record.chosen_modality,
        "confidence": record.confidence,
        "authoritative": True,
    }


def _serialize_analysis_unit(unit: L3AnalysisUnit) -> dict[str, Any]:
    return {
        "analysis_unit_id": unit.analysis_unit_id,
        "unit_kind": unit.unit_kind,
        "analysis_modality": unit.analysis_modality,
        "member_snapshot_ids": list(unit.member_snapshot_ids_json or []),
        "typing_record_ids": list(unit.typing_record_ids_json or []),
        "must_remain_intact": unit.must_remain_intact,
        "authoritative": True,
    }


def _serialize_analysis_group(group: L3AnalysisGroup) -> dict[str, Any]:
    return {
        "analysis_group_id": group.analysis_group_id,
        "analysis_modality": group.analysis_modality,
        "analysis_unit_ids": list(group.analysis_unit_ids_json or []),
        "status": group.status,
        "typing_basis": group.typing_basis_json or {},
    }


def _serialize_analysis_set(analysis_set: L3AnalysisSet) -> dict[str, Any]:
    return {
        "analysis_set_id": analysis_set.analysis_set_id,
        "analysis_group_ids": list(analysis_set.analysis_group_ids_json or []),
        "analysis_unit_ids": list(analysis_set.analysis_unit_ids_json or []),
        "set_type": analysis_set.set_type,
        "formation_basis": analysis_set.formation_basis_json or {},
    }


def gate_c_preview(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for Gate C preview.", http_status=404)
    session = _load_session(db, session_id)
    gate_b_counts = _gate_b_summary_from_session(session)
    source_classes = _source_classes_from_latest_manifest(db, session_id)
    commit_typing = bool(payload.get("commit_typing"))
    try:
        if commit_typing:
            result = materialize_typing_entry(db, session_id=session_id)
            db.commit()
            typing_records = [_serialize_typing_record(record) for record in result.typing_records]
            analysis_units = [_serialize_analysis_unit(unit) for unit in result.analysis_units]
            analysis_groups = [_serialize_analysis_group(group) for group in result.analysis_groups]
            analysis_sets = [_serialize_analysis_set(analysis_set) for analysis_set in result.analysis_sets]
            typing_status = "committed"
        else:
            snapshots = (
                db.query(L3MaterialSnapshot)
                .filter(L3MaterialSnapshot.session_id == session_id)
                .order_by(L3MaterialSnapshot.material_snapshot_id.asc())
                .all()
            )
            if not snapshots:
                raise Layer3WorkbenchError(
                    "typing_not_ready",
                    f"Layer 3 session '{session_id}' has no material snapshots to type.",
                    status="blocked",
                )
            typing_records = []
            unsupported_material = []
            for snapshot in snapshots:
                projection, unsupported = _snapshot_projection(snapshot)
                if projection is not None:
                    typing_records.append(projection)
                if unsupported is not None:
                    unsupported_material.append(unsupported)
            analysis_units = [
                {
                    "analysis_unit_id": None,
                    "unit_kind": "atomic",
                    "analysis_modality": record["chosen_modality"],
                    "member_snapshot_ids": [record["material_snapshot_id"]],
                    "typing_record_ids": [],
                    "must_remain_intact": False,
                    "authoritative": False,
                }
                for record in typing_records
            ]
            analysis_groups = []
            analysis_sets = []
            typing_status = "previewed" if typing_records else "unavailable"
            return {
                **_base_response("layer3.gate_c_preview_result.v1", request_id=request_id),
                "session_id": session_id,
                "typing_records": typing_records,
                "analysis_units": analysis_units,
                "analysis_groups": analysis_groups,
                "analysis_sets": analysis_sets,
                "unsupported_material": unsupported_material,
                "override_allowed": False,
                "next_state": "first_slice_complete" if typing_records and not unsupported_material else "blocked_typing_unavailable",
                "authority_rail": _authority_rail(
                    session_id=session_id,
                    current_gate="complete" if typing_records and not unsupported_material else "gate_c",
                    persistence_mode="durable_layer3_control",
                    source_classes=source_classes,
                    counts=gate_b_counts,
                    typing_status=typing_status,
                ),
            }
    except Layer3WorkbenchError:
        raise
    except Layer3TypingEntryError as exc:
        detail = str(exc)
        code = "typing_already_materialized" if "already has" in detail else "typing_not_ready"
        raise Layer3WorkbenchError(code, detail, status="blocked", http_status=409) from exc

    return {
        **_base_response("layer3.gate_c_preview_result.v1", request_id=request_id),
        "session_id": session_id,
        "typing_records": typing_records,
        "analysis_units": analysis_units,
        "analysis_groups": analysis_groups,
        "analysis_sets": analysis_sets,
        "unsupported_material": [],
        "override_allowed": False,
        "next_state": "plan_preview_ready",
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="durable_layer3_control",
            source_classes=source_classes,
            counts=gate_b_counts,
            typing_status=typing_status,
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
    }


def gate_c_override_unavailable(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **_base_response(
            "layer3.typing_override_unavailable.v1",
            request_id=str(payload.get("client_request_id") or uuid_str()),
            status="unavailable",
        ),
        "error_code": "override_unavailable",
        "message": "Typing override is not enabled in this first slice.",
        "recoverable": False,
        "next_allowed_actions": ["review_typing", "finish_first_slice"],
    }


def _gate_b_summary_from_session(session: L3Session) -> dict[str, int]:
    summary = session.summary_json or {}
    counts = summary.get("gate_b_summary_v1")
    if isinstance(counts, dict):
        return {decision: int(counts.get(decision, 0)) for decision in GATE_B_DECISIONS}
    decisions = ((session.operator_context_json or {}).get("layer3_gate_b_decision_manifest_v1") or {}).get("items") or []
    return _gate_b_counts([item for item in decisions if isinstance(item, dict)])


def _plan_preview_readiness(db: Session, *, session_id: str, include_owner_service: bool = False) -> dict[str, Any]:
    typing_record_count = db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count()
    analysis_set_count = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).count()
    analysis_plan_count = db.query(L3AnalysisPlan).filter(L3AnalysisPlan.session_id == session_id).count()
    pass_run_count = db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count()
    blocked_reason = None
    admitted_set_count = None
    excluded_set_count = None
    planned_pass_count = None
    if typing_record_count == 0:
        blocked_reason = "gate_c_not_committed"
    elif analysis_set_count == 0:
        blocked_reason = "no_analysis_sets"
    elif analysis_plan_count > 0 or pass_run_count > 0:
        blocked_reason = "plan_already_materialized"
    elif (revision_control := _plan_revision_control(db, session_id=session_id)) is not None:
        blocked_reason = str(revision_control.get("state") or "plan_revision_recorded")
    elif include_owner_service:
        try:
            owner_preview = preview_pass_entry(db, session_id=session_id)
            admitted_set_count = len(owner_preview.admitted_sets)
            excluded_set_count = len(owner_preview.excluded_sets)
            planned_pass_count = len(owner_preview.planned_passes)
        except Layer3PassEntryError as exc:
            blocked_reason = _plan_preview_error(exc).error_code
    return {
        "schema_id": "layer3.plan_preview_readiness.v1",
        "available": blocked_reason is None,
        "blocked_reason": blocked_reason,
        "typing_record_count": typing_record_count,
        "analysis_set_count": analysis_set_count,
        "analysis_plan_count": analysis_plan_count,
        "pass_run_count": pass_run_count,
        "admitted_set_count": admitted_set_count,
        "excluded_set_count": excluded_set_count,
        "planned_pass_count": planned_pass_count,
    }


def _latest_analysis_plan(db: Session, *, session_id: str) -> L3AnalysisPlan | None:
    return (
        db.query(L3AnalysisPlan)
        .filter(L3AnalysisPlan.session_id == session_id)
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .first()
    )


def _plan_revision_control_from_session(session: L3Session | None) -> dict[str, Any] | None:
    if session is None:
        return None
    control = (session.summary_json or {}).get("plan_revision_control")
    if not isinstance(control, dict):
        return None
    if control.get("schema_id") != "layer3.plan_revision_control.v1":
        return None
    return control


def _plan_revision_control(db: Session, *, session_id: str) -> dict[str, Any] | None:
    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    return _plan_revision_control_from_session(session)


def _plan_approval_summary(db: Session, *, session_id: str) -> dict[str, Any]:
    analysis_plan = _latest_analysis_plan(db, session_id=session_id)
    pass_run_count = db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count()
    if analysis_plan is None:
        preview = _plan_preview_readiness(db, session_id=session_id, include_owner_service=True)
        return {
            "schema_id": "layer3.plan_approval_readiness.v1",
            "available": preview["available"],
            "approved": False,
            "blocked_reason": preview["blocked_reason"],
            "analysis_plan_id": None,
            "plan_status": None,
            "approved_by_operator": False,
            "approved_at": None,
            "approved_set_count": preview["admitted_set_count"],
            "excluded_set_count": preview["excluded_set_count"],
            "planned_pass_count": preview["planned_pass_count"],
            "pass_run_count": pass_run_count,
        }
    plan_json = analysis_plan.plan_json or {}
    approved = bool(analysis_plan.approved_by_operator)
    return {
        "schema_id": "layer3.plan_approval_readiness.v1",
        "available": False,
        "approved": approved,
        "blocked_reason": "plan_already_approved" if approved else "plan_already_materialized",
        "analysis_plan_id": analysis_plan.analysis_plan_id,
        "plan_status": analysis_plan.status,
        "approved_by_operator": approved,
        "approved_at": analysis_plan.approved_at.isoformat() if analysis_plan.approved_at else None,
        "approved_set_count": len(analysis_plan.analysis_set_ids_json or []),
        "excluded_set_count": len(plan_json.get("excluded_sets_json") or []),
        "planned_pass_count": len(plan_json.get("planned_passes_json") or []),
        "pass_run_count": pass_run_count,
        "approval_only": bool(plan_json.get("approval_only")),
        "execution_started": bool(plan_json.get("execution_started")),
    }


def _plan_revision_summary(db: Session, *, session_id: str) -> dict[str, Any]:
    control = _plan_revision_control(db, session_id=session_id)
    if control is None:
        preview = _plan_preview_readiness(db, session_id=session_id, include_owner_service=True)
        return {
            "schema_id": "layer3.plan_revision_readiness.v1",
            "available": preview["available"],
            "state": None,
            "blocked_reason": preview["blocked_reason"],
            "source_preview_id": None,
            "source_preview_hash": None,
            "operator_decision": None,
            "operator_note_recorded": False,
            "approval_available": preview["available"],
            "execution_started": False,
        }
    return {
        "schema_id": "layer3.plan_revision_readiness.v1",
        "available": False,
        "state": control.get("state"),
        "blocked_reason": control.get("state"),
        "source_preview_id": control.get("source_preview_id"),
        "source_preview_hash": control.get("source_preview_hash"),
        "operator_decision": control.get("operator_decision"),
        "operator_note_recorded": bool(control.get("operator_note_recorded")),
        "approval_available": False,
        "execution_started": False,
        "created_at": control.get("created_at"),
    }


def _source_classes_from_plan_preview(plan_preview: dict[str, Any]) -> list[str]:
    source_classes = set()
    for collection_name in ("admitted_sets", "excluded_sets"):
        for item in plan_preview.get(collection_name) or []:
            source_summary = item.get("source_summary") if isinstance(item, dict) else {}
            for source_class in (source_summary or {}).get("source_classes") or []:
                source_classes.add(str(source_class))
    return sorted(source_classes)


def _plan_preview_error(exc: Layer3PassEntryError) -> Layer3WorkbenchError:
    message = str(exc)
    if "was not found" in message:
        return Layer3WorkbenchError("session_not_found", message, http_status=404)
    if "must be finalized" in message:
        return Layer3WorkbenchError("gate_c_not_committed", message, status="blocked", http_status=409)
    if "already has analysis plans" in message or "already has pass runs" in message:
        return Layer3WorkbenchError("plan_already_materialized", message, status="conflict", http_status=409)
    if "has no analysis sets" in message:
        return Layer3WorkbenchError("no_analysis_sets", message, status="blocked", http_status=409)
    if "has no admissible analysis sets" in message:
        return Layer3WorkbenchError("no_admissible_plan", message, status="blocked", http_status=409)
    return Layer3WorkbenchError(
        "owner_service_error",
        message,
        status="failed",
        http_status=500,
        recoverable=False,
    )


def _plan_approval_error(exc: Layer3PassEntryError) -> Layer3WorkbenchError:
    message = str(exc)
    if "preview hash mismatch" in message:
        return Layer3WorkbenchError("preview_mismatch", message, status="conflict", http_status=409)
    if "operator confirmation" in message:
        return Layer3WorkbenchError(
            "operator_confirmation_required",
            message,
            status="blocked",
            http_status=400,
            blocked_fields=["operator_confirmation"],
            next_allowed_actions=["confirm_plan_approval"],
        )
    if "already has analysis plans" in message:
        return Layer3WorkbenchError("plan_already_materialized", message, status="conflict", http_status=409)
    if "already has pass runs" in message:
        return Layer3WorkbenchError("pass_runs_already_exist", message, status="conflict", http_status=409)
    return _plan_preview_error(exc)


def plan_preview(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for plan preview.", http_status=404)

    preview_scope = str(payload.get("preview_scope") or PLAN_PREVIEW_SCOPE).strip()
    if preview_scope != PLAN_PREVIEW_SCOPE:
        raise Layer3WorkbenchError(
            "unsupported_preview_scope",
            f"Unsupported plan preview scope: {preview_scope}.",
            status="invalid",
            blocked_fields=["preview_scope"],
            next_allowed_actions=["use_owner_service_default"],
        )

    session = _load_session(db, session_id)
    gate_b_counts = _gate_b_summary_from_session(session)
    readiness = _plan_preview_readiness(db, session_id=session_id)
    if not readiness["available"]:
        raise Layer3WorkbenchError(
            readiness["blocked_reason"],
            f"Layer 3 session '{session_id}' is not ready for plan preview: {readiness['blocked_reason']}.",
            status="blocked" if readiness["blocked_reason"] != "plan_already_materialized" else "conflict",
            http_status=409,
            next_allowed_actions=["commit_gate_c_typing"] if readiness["blocked_reason"] == "gate_c_not_committed" else [],
        )

    try:
        owner_preview = preview_pass_entry(db, session_id=session_id)
    except Layer3PassEntryError as exc:
        raise _plan_preview_error(exc) from exc

    plan_preview_payload = {
        "schema_id": "layer3.plan_preview_payload.v1",
        "plan_version": PLAN_PREVIEW_SCOPE,
        "owner_plan_version": owner_preview.owner_service_basis["owner_plan_version"],
        "preview_hash": owner_preview.preview_hash,
        "preview_hash_contract": _plan_preview_hash_contract(),
        "approval_ready": True,
        "would_create_analysis_plan": False,
        "would_create_pass_runs": False,
        "would_execute_passes": False,
        "admitted_sets": [dict(item) for item in owner_preview.admitted_sets],
        "excluded_sets": [dict(item) for item in owner_preview.excluded_sets],
        "planned_passes": [dict(item) for item in owner_preview.planned_passes],
        "warnings": [dict(item) for item in owner_preview.warnings],
        "owner_service_basis": dict(owner_preview.owner_service_basis),
    }
    preview_id = _stable_id("plan-preview", {"session_id": session_id, "plan_preview": plan_preview_payload})
    return {
        **_base_response("layer3.plan_preview_result.v1", request_id=request_id),
        "session_id": session_id,
        "next_state": "plan_preview_ready",
        "preview_id": preview_id,
        "preview_hash": owner_preview.preview_hash,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=owner_preview.preview_hash),
        "preview_only": True,
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="preview_only",
            source_classes=_source_classes_from_plan_preview(plan_preview_payload),
            counts=gate_b_counts,
            typing_status="committed",
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
        "plan_preview": plan_preview_payload,
    }


def _approved_set_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {**_json_clone(item), "readiness": "approved"}


def _approved_planned_pass_payload(item: dict[str, Any]) -> dict[str, Any]:
    payload = _json_clone(item)
    payload.pop("preview_only", None)
    payload["approval_only"] = True
    payload["execution_status"] = "not_started"
    return payload


def plan_approval(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for plan approval.", http_status=404)

    if not bool(payload.get("operator_confirmation")):
        raise Layer3WorkbenchError(
            "operator_confirmation_required",
            "operator_confirmation must be true before plan approval is persisted.",
            status="blocked",
            blocked_fields=["operator_confirmation"],
            next_allowed_actions=["confirm_plan_approval"],
        )
    approval_scope = str(payload.get("approval_scope") or PLAN_APPROVAL_SCOPE).strip()
    if approval_scope != PLAN_APPROVAL_SCOPE:
        raise Layer3WorkbenchError(
            "unsupported_approval_scope",
            f"Unsupported plan approval scope: {approval_scope}.",
            status="invalid",
            blocked_fields=["approval_scope"],
            next_allowed_actions=["use_owner_service_default"],
        )
    forbidden = sorted(key for key in PLAN_APPROVAL_FORBIDDEN_FIELDS if key in payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "execution_not_admitted",
            f"Plan approval request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_approval_only_request"],
        )
    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    existing_control = _plan_revision_control_from_session(session)
    if existing_control is not None:
        raise Layer3WorkbenchError(
            str(existing_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )
    existing_plan = _latest_analysis_plan(db, session_id=session_id)
    if existing_plan is not None:
        if bool(existing_plan.approved_by_operator):
            error_code = "plan_already_approved"
            message = f"Layer 3 session '{session_id}' already has an approved analysis plan."
        else:
            error_code = "plan_already_materialized"
            message = f"Layer 3 session '{session_id}' already has a non-approved analysis plan."
        raise Layer3WorkbenchError(
            error_code,
            message,
            status="conflict",
            http_status=409,
        )
    if db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count() > 0:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )

    expected_preview = plan_preview(
        db,
        {
            "client_request_id": request_id,
            "session_id": session_id,
            "preview_scope": PLAN_PREVIEW_SCOPE,
        },
    )
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    if preview_id != expected_preview["preview_id"] or preview_hash != expected_preview["preview_hash"]:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Plan approval must reference the current server-recomputed preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    try:
        approved = approve_pass_entry_plan(
            db,
            session_id=session_id,
            preview_hash=preview_hash,
            source_preview_id=preview_id,
            approved_by_operator=True,
        )
        db.commit()
    except Layer3PassEntryError as exc:
        db.rollback()
        raise _plan_approval_error(exc) from exc

    session = _load_session(db, session_id)
    gate_b_counts = _gate_b_summary_from_session(session)
    approved_sets = [_approved_set_payload(item) for item in approved.approved_sets]
    planned_passes = [_approved_planned_pass_payload(item) for item in approved.planned_passes]
    approved_plan = {
        "schema_id": "layer3.approved_plan_payload.v1",
        "plan_version": PLAN_APPROVAL_SCOPE,
        "source_preview_id": approved.source_preview_id,
        "source_preview_hash": approved.source_preview_hash,
        "would_create_pass_runs": False,
        "would_execute_passes": False,
        "approved_sets": approved_sets,
        "excluded_sets": [dict(item) for item in approved.excluded_sets],
        "planned_passes": planned_passes,
        "warnings": [dict(item) for item in approved.warnings],
        "owner_service_basis": dict(approved.owner_service_basis),
    }
    return {
        **_base_response("layer3.plan_approval_result.v1", request_id=request_id),
        "session_id": session_id,
        "next_state": "plan_approved",
        "approval_only": True,
        "execution_started": False,
        "analysis_plan_id": approved.analysis_plan.analysis_plan_id,
        "plan_status": approved.analysis_plan.status,
        "approved_by_operator": bool(approved.analysis_plan.approved_by_operator),
        "approved_at": approved.analysis_plan.approved_at.isoformat() if approved.analysis_plan.approved_at else None,
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="approved_plan",
            source_classes=_source_classes_from_plan_preview(
                {
                    "admitted_sets": approved_sets,
                    "excluded_sets": approved_plan["excluded_sets"],
                }
            ),
            counts=gate_b_counts,
            typing_status="committed",
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
        "approved_plan": approved_plan,
    }


def plan_revision(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or uuid_str())
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise Layer3WorkbenchError("session_not_found", "session_id is required for plan revision.", http_status=404)

    operator_decision = str(payload.get("operator_decision") or "").strip()
    if operator_decision not in PLAN_REVISION_DECISIONS:
        raise Layer3WorkbenchError(
            "unsupported_revision_decision",
            f"Unsupported plan revision decision: {operator_decision or 'missing'}.",
            status="invalid",
            blocked_fields=["operator_decision"],
            next_allowed_actions=["use_supported_revision_decision"],
        )

    forbidden = sorted(key for key in PLAN_REVISION_FORBIDDEN_FIELDS if key in payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "execution_not_admitted",
            f"Plan revision request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_revision_control_only_request"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)
    existing_control = _plan_revision_control_from_session(session)
    if existing_control is not None:
        raise Layer3WorkbenchError(
            str(existing_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )

    existing_plan = _latest_analysis_plan(db, session_id=session_id)
    if existing_plan is not None:
        if bool(existing_plan.approved_by_operator):
            error_code = "plan_already_approved"
            message = f"Layer 3 session '{session_id}' already has an approved analysis plan."
        else:
            error_code = "plan_already_materialized"
            message = f"Layer 3 session '{session_id}' already has a non-approved analysis plan."
        raise Layer3WorkbenchError(error_code, message, status="conflict", http_status=409)

    if db.query(L3PassRun).filter(L3PassRun.session_id == session_id).count() > 0:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )

    expected_preview = plan_preview(
        db,
        {
            "client_request_id": request_id,
            "session_id": session_id,
            "preview_scope": PLAN_PREVIEW_SCOPE,
        },
    )
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    if preview_id != expected_preview["preview_id"] or preview_hash != expected_preview["preview_hash"]:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Plan revision must reference the current server-recomputed preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    next_state = PLAN_REVISION_STATE_BY_DECISION[operator_decision]
    operator_note = str(payload.get("operator_note") or "").strip()
    gate_b_counts = _gate_b_summary_from_session(session)
    source_classes = _source_classes_from_plan_preview(expected_preview.get("plan_preview") or {})
    control = {
        "schema_id": "layer3.plan_revision_control.v1",
        "state": next_state,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "operator_decision": operator_decision,
        "operator_note_recorded": bool(operator_note),
        "approval_available": False,
        "execution_started": False,
        "created_at": _utcnow_iso(),
    }
    session.summary_json = {
        **_json_clone(session.summary_json),
        "plan_revision_control": control,
    }
    db.commit()

    return {
        **_base_response("layer3.plan_revision_result.v1", request_id=request_id),
        "session_id": session_id,
        "next_state": next_state,
        "revision_control_only": True,
        "execution_started": False,
        "source_preview_id": preview_id,
        "source_preview_hash": preview_hash,
        "operator_decision": operator_decision,
        "operator_note_recorded": bool(operator_note),
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate="plan",
            persistence_mode="plan_revision_control",
            source_classes=source_classes,
            counts=gate_b_counts,
            typing_status="committed",
            downstream_unavailable=PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE,
        ),
        "downstream_unavailable": list(PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE),
        "plan_revision_control": control,
    }


def _execution_selection_from_session(session: L3Session | None) -> dict[str, Any] | None:
    if session is None:
        return None
    selection = (session.summary_json or {}).get("execution_selection")
    if not isinstance(selection, dict):
        return None
    if selection.get("schema_id") != EXECUTION_SELECTION_STATE_SCHEMA_ID:
        return None
    return selection


def _execution_selection_pass_runs(db: Session, *, session_id: str) -> list[L3PassRun]:
    return (
        db.query(L3PassRun)
        .filter(L3PassRun.session_id == session_id)
        .order_by(L3PassRun.created_at.asc(), L3PassRun.pass_run_id.asc())
        .all()
    )


def _execution_selection_response(
    *,
    request_id: str,
    status: str,
    session_id: str,
    analysis_plan_id: str,
    preview_id: str,
    preview_hash: str,
    pass_runs: list[L3PassRun],
) -> dict[str, Any]:
    return {
        **_base_response(EXECUTION_SELECTION_SCHEMA_ID, request_id=request_id, status=status),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "preview_identity": _preview_identity(preview_id=preview_id, preview_hash=preview_hash),
        "pass_run_ids": [pass_run.pass_run_id for pass_run in pass_runs],
        "pass_run_count": len(pass_runs),
        "execution_started": False,
        "analysis_run_ids": [],
        "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
        "next_state": EXECUTION_SELECTION_STATE,
    }


def _execution_selection_summary(db: Session, *, session_id: str) -> dict[str, Any]:
    session = db.query(L3Session).filter(L3Session.session_id == session_id).first()
    selection = _execution_selection_from_session(session)
    pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    if selection is not None:
        return {
            "schema_id": "layer3.execution_selection_readiness.v1",
            "available": False,
            "selected": True,
            "state": selection.get("state"),
            "blocked_reason": "execution_selection_already_exists",
            "analysis_plan_id": selection.get("analysis_plan_id"),
            "source_preview_id": selection.get("source_preview_id"),
            "source_preview_hash": selection.get("source_preview_hash"),
            "pass_run_ids": [pass_run.pass_run_id for pass_run in pass_runs],
            "pass_run_count": len(pass_runs),
            "execution_started": False,
            "analysis_run_ids": [],
            "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
            "selected_at": selection.get("selected_at"),
        }

    analysis_plan_id = None
    source_preview_id = None
    source_preview_hash = None
    if (revision_control := _plan_revision_control(db, session_id=session_id)) is not None:
        blocked_reason = str(revision_control.get("state") or "plan_revision_recorded")
    else:
        approved_plans = (
            db.query(L3AnalysisPlan)
            .filter(
                L3AnalysisPlan.session_id == session_id,
                L3AnalysisPlan.status == "approved",
                L3AnalysisPlan.approved_by_operator.is_(True),
            )
            .all()
        )
        if not approved_plans:
            blocked_reason = "no_approved_plan"
        elif len(approved_plans) > 1:
            blocked_reason = "multiple_approved_plans"
        elif pass_runs:
            blocked_reason = "pass_runs_already_exist"
        else:
            approved_plan = approved_plans[0]
            plan_json = approved_plan.plan_json or {}
            analysis_plan_id = approved_plan.analysis_plan_id
            source_preview_id = plan_json.get("source_preview_id")
            source_preview_hash = plan_json.get("source_preview_hash")
            blocked_reason = None

    return {
        "schema_id": "layer3.execution_selection_readiness.v1",
        "available": blocked_reason is None,
        "selected": False,
        "state": None,
        "blocked_reason": blocked_reason,
        "analysis_plan_id": analysis_plan_id,
        "source_preview_id": source_preview_id,
        "source_preview_hash": source_preview_hash,
        "pass_run_ids": [],
        "pass_run_count": len(pass_runs),
        "execution_started": False,
        "analysis_run_ids": [],
        "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
        "selected_at": None,
    }


def execution_selection(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = str(payload.get("client_request_id") or "").strip()
    if not request_id:
        raise Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for execution selection.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_idempotent_execution_selection"],
        )

    session_id = str(payload.get("session_id") or "").strip()
    analysis_plan_id = str(payload.get("analysis_plan_id") or "").strip()
    preview_id = str(payload.get("preview_id") or "").strip()
    preview_hash = str(payload.get("preview_hash") or "").strip()
    missing = [
        field
        for field, value in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("preview_id", preview_id),
            ("preview_hash", preview_hash),
        )
        if not value
    ]
    if missing:
        raise Layer3WorkbenchError(
            "missing_execution_selection_fields",
            f"Execution selection is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_execution_selection_request"],
        )

    forbidden = sorted(key for key in EXECUTION_SELECTION_FORBIDDEN_FIELDS if key in payload)
    if forbidden:
        raise Layer3WorkbenchError(
            "analysis_execution_not_admitted",
            f"Execution selection request includes non-admitted fields: {', '.join(forbidden)}.",
            status="invalid",
            blocked_fields=forbidden,
            next_allowed_actions=["submit_selection_only_request"],
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).with_for_update().first()
    if session is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' was not found.", http_status=404)

    revision_control = _plan_revision_control_from_session(session)
    if revision_control is not None:
        raise Layer3WorkbenchError(
            str(revision_control.get("state") or "plan_revision_recorded"),
            f"Layer 3 session '{session_id}' already has a plan revision-control decision.",
            status="conflict",
            http_status=409,
        )

    approved_plans = (
        db.query(L3AnalysisPlan)
        .filter(
            L3AnalysisPlan.session_id == session_id,
            L3AnalysisPlan.status == "approved",
            L3AnalysisPlan.approved_by_operator.is_(True),
        )
        .with_for_update()
        .order_by(L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc())
        .all()
    )
    if len(approved_plans) == 0:
        raise Layer3WorkbenchError(
            "no_approved_plan",
            f"Layer 3 session '{session_id}' has no current approved analysis plan.",
            status="blocked",
            http_status=409,
            next_allowed_actions=["approve_current_plan"],
        )
    if len(approved_plans) > 1:
        raise Layer3WorkbenchError(
            "multiple_approved_plans",
            f"Layer 3 session '{session_id}' has multiple approved analysis plans.",
            status="conflict",
            http_status=409,
        )
    approved_plan = approved_plans[0]

    existing_selection = _execution_selection_from_session(session)
    existing_pass_runs = _execution_selection_pass_runs(db, session_id=session_id)
    if existing_selection is not None:
        stored_pass_run_ids = list(existing_selection.get("pass_run_ids_json") or [])
        existing_pass_run_ids = [pass_run.pass_run_id for pass_run in existing_pass_runs]
        if stored_pass_run_ids != existing_pass_run_ids:
            raise Layer3WorkbenchError(
                "execution_selection_inconsistent",
                f"Layer 3 session '{session_id}' has inconsistent execution-selection shell state.",
                status="conflict",
                http_status=409,
            )
        if str(existing_selection.get("client_request_id") or "") == request_id:
            if (
                str(existing_selection.get("analysis_plan_id") or "") == analysis_plan_id
                and str(existing_selection.get("source_preview_id") or "") == preview_id
                and str(existing_selection.get("source_preview_hash") or "") == preview_hash
            ):
                return _execution_selection_response(
                    request_id=request_id,
                    status="already_selected",
                    session_id=session_id,
                    analysis_plan_id=analysis_plan_id,
                    preview_id=preview_id,
                    preview_hash=preview_hash,
                    pass_runs=existing_pass_runs,
                )
            raise Layer3WorkbenchError(
                "idempotency_conflict",
                "client_request_id already selected execution for a different approved plan or preview identity.",
                status="conflict",
                http_status=409,
                blocked_fields=["client_request_id"],
            )
        raise Layer3WorkbenchError(
            "execution_selection_already_exists",
            f"Layer 3 session '{session_id}' already has an execution selection.",
            status="conflict",
            http_status=409,
        )
    if existing_pass_runs:
        raise Layer3WorkbenchError(
            "pass_runs_already_exist",
            f"Layer 3 session '{session_id}' already has pass runs.",
            status="conflict",
            http_status=409,
        )

    if approved_plan.analysis_plan_id != analysis_plan_id:
        raise Layer3WorkbenchError(
            "approved_plan_mismatch",
            "Execution selection must reference the current approved analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["analysis_plan_id"],
        )

    plan_json = approved_plan.plan_json or {}
    stored_preview_id = str(plan_json.get("source_preview_id") or "").strip()
    stored_preview_hash = str(plan_json.get("source_preview_hash") or "").strip()
    if preview_id != stored_preview_id or preview_hash != stored_preview_hash:
        raise Layer3WorkbenchError(
            "preview_mismatch",
            "Execution selection must reference the approved plan preview id and hash.",
            status="conflict",
            http_status=409,
            blocked_fields=["preview_id", "preview_hash"],
            next_allowed_actions=["refresh_plan_preview"],
        )

    approved_set_ids = [str(item) for item in (approved_plan.analysis_set_ids_json or []) if str(item)]
    planned_passes = [item for item in (plan_json.get("planned_passes_json") or []) if isinstance(item, dict)]
    if not approved_set_ids or not planned_passes:
        raise Layer3WorkbenchError(
            "no_admissible_plan",
            f"Layer 3 session '{session_id}' has no approved analysis sets for execution selection.",
            status="blocked",
            http_status=409,
        )

    planned_by_set_id = {str(item.get("analysis_set_id") or ""): item for item in planned_passes}
    selected_planned_passes: list[dict[str, Any]] = []
    for analysis_set_id in approved_set_ids:
        planned_pass = planned_by_set_id.get(analysis_set_id)
        if planned_pass is None:
            raise Layer3WorkbenchError(
                "approved_plan_malformed",
                f"Approved plan '{analysis_plan_id}' is missing a planned pass for analysis set '{analysis_set_id}'.",
                status="conflict",
                http_status=409,
            )
        if not str(planned_pass.get("pass_type") or "").strip():
            raise Layer3WorkbenchError(
                "approved_plan_malformed",
                f"Approved plan '{analysis_plan_id}' has a planned pass without pass_type.",
                status="conflict",
                http_status=409,
            )
        selected_planned_passes.append(planned_pass)

    selected_at = _utcnow_iso()
    pass_runs: list[L3PassRun] = []
    for planned_pass in selected_planned_passes:
        pass_run_id = uuid_str()
        pass_run = L3PassRun(
            pass_run_id=pass_run_id,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            analysis_set_id=str(planned_pass.get("analysis_set_id")),
            pass_type=str(planned_pass.get("pass_type")),
            engine_family=str(planned_pass.get("engine_family") or "wrapped_quantitative_analysis"),
            status="selected_not_started",
            started_at=None,
            completed_at=None,
            input_payload_ref=f"layer3://execution-selection/{pass_run_id}/input",
            output_payload_ref=None,
            summary_json={
                "schema_id": "layer3.pass_run_shell_summary.v1",
                "execution_selection_schema_id": EXECUTION_SELECTION_SCHEMA_ID,
                "selection_state": EXECUTION_SELECTION_STATE,
                "client_request_id": request_id,
                "analysis_plan_id": analysis_plan_id,
                "source_preview_id": preview_id,
                "source_preview_hash": preview_hash,
                "execution_started": False,
                "analysis_run_id": None,
                "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
                "planned_pass": _json_clone(planned_pass),
                "selected_at": selected_at,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(pass_run)
        pass_runs.append(pass_run)

    db.flush()
    session.summary_json = {
        **_json_clone(session.summary_json),
        "execution_selection": {
            "schema_id": EXECUTION_SELECTION_STATE_SCHEMA_ID,
            "state": EXECUTION_SELECTION_STATE,
            "client_request_id": request_id,
            "analysis_plan_id": analysis_plan_id,
            "source_preview_id": preview_id,
            "source_preview_hash": preview_hash,
            "pass_run_ids_json": [pass_run.pass_run_id for pass_run in pass_runs],
            "pass_run_count": len(pass_runs),
            "execution_started": False,
            "analysis_run_ids_json": [],
            "downstream_unavailable": list(EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE),
            "operator_reason_recorded": bool(str(payload.get("operator_reason") or "").strip()),
            "selected_at": selected_at,
        },
    }
    db.commit()

    return _execution_selection_response(
        request_id=request_id,
        status="selected_not_started",
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        preview_id=preview_id,
        preview_hash=preview_hash,
        pass_runs=pass_runs,
    )


def session_summary(db: Session, session_id: str) -> dict[str, Any]:
    session = _load_session(db, session_id)
    manifest = (
        db.query(L3SelectionManifest)
        .filter(L3SelectionManifest.session_id == session_id)
        .order_by(L3SelectionManifest.committed_at.desc())
        .first()
    )
    if manifest is None:
        raise Layer3WorkbenchError("session_not_found", f"Layer 3 session '{session_id}' has no selection manifest.", http_status=404)

    typing_record_count = db.query(L3TypingRecord).filter(L3TypingRecord.session_id == session_id).count()
    analysis_unit_count = db.query(L3AnalysisUnit).filter(L3AnalysisUnit.session_id == session_id).count()
    analysis_group_count = db.query(L3AnalysisGroup).filter(L3AnalysisGroup.session_id == session_id).count()
    analysis_set_count = db.query(L3AnalysisSet).filter(L3AnalysisSet.session_id == session_id).count()
    gate_b_counts = _gate_b_summary_from_session(session)
    typing_committed = typing_record_count > 0
    plan_preview_readiness = _plan_preview_readiness(db, session_id=session_id, include_owner_service=True)
    plan_approval_readiness = _plan_approval_summary(db, session_id=session_id)
    plan_revision_readiness = _plan_revision_summary(db, session_id=session_id)
    execution_selection_readiness = _execution_selection_summary(db, session_id=session_id)
    selection_active = bool(execution_selection_readiness["selected"])
    current_gate = "execution" if selection_active else ("plan" if typing_committed else "gate_c")
    downstream_unavailable = (
        EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE
        if selection_active
        else (PLAN_PREVIEW_DOWNSTREAM_UNAVAILABLE if typing_committed else DOWNSTREAM_UNAVAILABLE)
    )

    return {
        **_base_response("layer3.workbench_session_summary.v1"),
        "session_id": session_id,
        "selection_manifest_id": manifest.selection_manifest_id,
        "current_gate": current_gate,
        "gate_b_summary": gate_b_counts,
        "gate_c_summary": {
            "typing_committed": typing_committed,
            "typing_record_count": typing_record_count,
            "analysis_unit_count": analysis_unit_count,
            "analysis_group_count": analysis_group_count,
            "analysis_set_count": analysis_set_count,
        },
        "plan_preview": plan_preview_readiness,
        "plan_approval": plan_approval_readiness,
        "plan_revision": plan_revision_readiness,
        "execution_selection": execution_selection_readiness,
        "downstream_unavailable": list(downstream_unavailable),
        "authority_rail": _authority_rail(
            session_id=session_id,
            current_gate=current_gate,
            persistence_mode="durable_layer3_control",
            counts=gate_b_counts,
            typing_status="committed" if typing_committed else "previewed",
            downstream_unavailable=downstream_unavailable,
        ),
    }
