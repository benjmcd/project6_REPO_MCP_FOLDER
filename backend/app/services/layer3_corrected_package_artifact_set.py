from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisPlan,
    L3CorrectedPackageArtifactSet,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementPackageArtifactMaterialization,
    L3Session,
)
from app.services import layer3_workbench
from app.services.layer3_execution_review import EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
)
from app.services.layer3_utils import json_clone, stable_hash, stable_id, utc_isoformat, utcnow
from app.services.layer3_workbench_package_state import packages_in_kind_order, packages_with_kinds


CORRECTED_PACKAGE_ARTIFACT_SET_SCHEMA_ID = "layer3.corrected_package_artifact_set.v1"
CORRECTED_PACKAGE_ARTIFACT_SET_MODE = "operator_review_corrections_server_owned_corrected_package_artifact_set"
CORRECTED_PACKAGE_ARTIFACT_SET_SOURCE_GATE = (
    "703_OPERATOR_REVIEW_CORRECTIONS_CORRECTED_PACKAGE_ARTIFACT_SET_ENTRY_FREEZE_CURRENT_MAIN_SYNC"
)
CORRECTED_PACKAGE_ARTIFACT_SET_OPERATOR_DECISION = (
    "record_corrected_package_artifact_set_from_review_corrections"
)
CORRECTED_PACKAGE_ARTIFACT_SET_STATE = "corrected_package_artifact_set_recorded"
CORRECTED_PACKAGE_ARTIFACT_SET_STATUS = "recorded"
CORRECTED_PACKAGE_ARTIFACT_NAMESPACE = "replacement-package-artifacts"
CORRECTED_PACKAGE_ARTIFACT_HASH_ALGORITHM = "sha256"

CORRECTED_PACKAGE_ARTIFACT_SET_PACKAGE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)

CORRECTED_PACKAGE_ARTIFACT_SET_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "result_review_record_ref",
        "reviewed_output_items_hash",
        "package_review_preview_hash",
        "operator_decision",
    }
)
CORRECTED_PACKAGE_ARTIFACT_SET_OPTIONAL_FIELDS = frozenset(
    {
        "package_supersession_preview_hash",
        "replacement_artifact_materialization_id",
        "materialization_basis_hash",
    }
)
CORRECTED_PACKAGE_ARTIFACT_SET_FORBIDDEN_FIELDS = frozenset(
    {
        "corrected_artifact_refs",
        "corrected_artifact_hashes",
        "corrected_artifact_bytes",
        "corrected_package_payloads",
        "package_payload",
        "package_payload_bytes",
        "package_variant_content",
        "replacement_package_payloads",
        "replacement_package_payload_bytes",
        "edited_package_content",
        "browser_generated_diff",
        "artifact_bytes",
        "generate_artifact",
        "rewrite_output",
        "rebuild_package",
        "mutate_package",
        "replace_package",
        "delete_package",
        "update_package_row",
        "update_payload_ref",
        "update_payload_hash",
        "replacement_output_package_ids",
        "source_l3_output_package_write",
        "source_output_package_update",
        "package_row_mutation",
        "package_payload_write",
        "package_payload_rewrite",
        "analysis_artifact",
        "handoff",
        "export",
        "connector_key",
        "connector_run_id",
        "connector_payload",
        "destination_id",
        "destination_url",
        "provider_public_url",
        "provider_url",
        "public_url",
        "signed_url",
        "download_url",
        "source_upload",
        "source_directory",
        "local_directory",
        "rag_vector_input",
        "rag_vector_index",
        "runtime_db_write",
        "qualitative_execution_instruction",
        "qualitative_plan",
        "hybrid_execution",
        "rag_execution",
        "hidden_llm_prompt",
        "hidden_llm_plan",
        "hidden_llm_planning",
        "rendered_control_state",
        "schema_migration",
        "auth_security_directive",
        "auth_context",
        "security_context",
        "retry",
        "rerun",
        "cancel",
    }
)
CORRECTED_PACKAGE_ARTIFACT_SET_ALLOWED_FIELDS = (
    CORRECTED_PACKAGE_ARTIFACT_SET_REQUIRED_FIELDS
    | CORRECTED_PACKAGE_ARTIFACT_SET_OPTIONAL_FIELDS
    | CORRECTED_PACKAGE_ARTIFACT_SET_FORBIDDEN_FIELDS
)
CORRECTED_PACKAGE_ARTIFACT_SET_DOWNSTREAM_UNAVAILABLE = (
    "package_rebuild_runtime",
    "package_payload_rewrite",
    "source_l3_output_package_mutation",
    "package_activation",
    "handoff_export_rerun",
    "provider_public_url",
    "connector_destination_dispatch",
    "source_upload_expansion",
    "broad_qualitative_hybrid_rag_execution",
    "full_mockup_activation",
)


def _string(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_string(item) for item in value]


def _raise_mismatch(error_code: str, field: str, message: str) -> None:
    raise layer3_workbench.Layer3WorkbenchError(
        error_code,
        message,
        status="conflict",
        http_status=409,
        blocked_fields=[field],
        recoverable=True,
        next_allowed_actions=["refresh_corrected_package_artifact_set_authority"],
    )


def _package_row_projection(package: L3OutputPackage) -> dict[str, Any]:
    return {
        "output_package_id": package.output_package_id,
        "package_kind": package.package_kind,
        "status": package.status,
        "payload_ref": package.payload_ref,
        "payload_hash": package.payload_hash,
    }


def _source_package_rows(db: Session, *, session_id: str, reconciliation_record_id: str) -> list[L3OutputPackage]:
    all_packages = (
        db.query(L3OutputPackage)
        .filter(
            L3OutputPackage.session_id == session_id,
            L3OutputPackage.reconciliation_record_id == reconciliation_record_id,
        )
        .all()
    )
    packages = packages_with_kinds(
        all_packages,
        package_kinds=CORRECTED_PACKAGE_ARTIFACT_SET_PACKAGE_KINDS,
    )
    if (
        len(packages) != len(CORRECTED_PACKAGE_ARTIFACT_SET_PACKAGE_KINDS)
        or {package.package_kind for package in packages} != set(CORRECTED_PACKAGE_ARTIFACT_SET_PACKAGE_KINDS)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "corrected_package_artifact_set_requires_complete_source_package_set",
            "Corrected package artifact-set authority requires the existing canonical_internal, user_facing, and review_facing packages.",
            status="blocked",
            http_status=409,
            blocked_fields=["source_output_package_ids", "source_package_kinds"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    return packages_in_kind_order(packages, package_kinds=CORRECTED_PACKAGE_ARTIFACT_SET_PACKAGE_KINDS)


def _validate_supplied_list(*, payload: dict[str, Any], field: str, expected_values: list[str]) -> None:
    supplied_values = _string_list(payload.get(field))
    if supplied_values != expected_values:
        _raise_mismatch(
            f"corrected_package_artifact_set_{field}_mismatch",
            field,
            f"Supplied {field} do not match immutable corrected artifact source authority.",
        )


def _result_review_state(pass_run: L3PassRun) -> dict[str, Any]:
    state = (pass_run.summary_json or {}).get("execution_result_review")
    if not isinstance(state, dict) or state.get("schema_id") != EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID:
        raise layer3_workbench.Layer3WorkbenchError(
            "corrected_package_artifact_set_requires_result_review",
            "Corrected package artifact-set authority requires an existing execution result-review state.",
            status="blocked",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
            next_allowed_actions=["record_approved_execution_result_review"],
        )
    if (
        state.get("review_state") != layer3_workbench.EXECUTION_RESULT_REVIEW_APPROVED_STATE
        or state.get("operator_decision") != "approved"
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "corrected_package_artifact_set_requires_approved_result_review",
            "Corrected package artifact-set authority requires an approved execution result review.",
            status="blocked",
            http_status=409,
            blocked_fields=["result_review_record_ref"],
            next_allowed_actions=["record_approved_execution_result_review"],
        )
    reviewed_items = state.get("reviewed_output_items")
    if not isinstance(reviewed_items, list) or not reviewed_items:
        raise layer3_workbench.Layer3WorkbenchError(
            "corrected_package_artifact_set_requires_structured_review_items",
            "Free-form review notes alone are not corrected-artifact authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["reviewed_output_items_hash"],
            next_allowed_actions=["record_structured_review_items"],
        )
    return state


def _package_review_preview_hash(reconciliation: L3ReconciliationRecord) -> str:
    commit_summary = (reconciliation.summary_json or {}).get("workbench_package_commit")
    if not isinstance(commit_summary, dict):
        return ""
    return _string(commit_summary.get("package_review_preview_hash"))


def corrected_package_set_hash(
    *,
    corrected_package_set_id: str,
    corrected_package_kinds: list[str],
    corrected_artifact_refs: list[str],
    corrected_artifact_hashes: list[str],
    corrected_artifact_byte_sizes: list[int],
) -> str:
    # Corrected artifact sets become replacement package-set authority, so this
    # identity must match the downstream replacement package-set hash contract.
    return stable_hash(
        {
            "schema_id": "layer3.replacement_package_set.v1",
            "replacement_package_set_id": corrected_package_set_id,
            "replacement_packages": [
                {
                    "package_kind": package_kind,
                    "payload_ref": artifact_ref,
                    "payload_hash": artifact_hash,
                }
                for package_kind, artifact_ref, artifact_hash in zip(
                    corrected_package_kinds,
                    corrected_artifact_refs,
                    corrected_artifact_hashes,
                )
            ],
        }
    )


def corrected_artifact_manifest_hash(
    *,
    corrected_package_set_id: str,
    corrected_package_set_hash: str,
    corrected_package_kinds: list[str],
    corrected_artifact_refs: list[str],
    corrected_artifact_hashes: list[str],
    corrected_artifact_byte_sizes: list[int],
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.corrected_package_artifact_manifest.v1",
            "mode": CORRECTED_PACKAGE_ARTIFACT_SET_MODE,
            "artifact_namespace": CORRECTED_PACKAGE_ARTIFACT_NAMESPACE,
            "hash_algorithm": CORRECTED_PACKAGE_ARTIFACT_HASH_ALGORITHM,
            "corrected_package_set_id": corrected_package_set_id,
            "corrected_package_set_hash": corrected_package_set_hash,
            "corrected_artifacts": [
                {
                    "package_kind": package_kind,
                    "artifact_ref": artifact_ref,
                    "artifact_hash": artifact_hash,
                    "artifact_byte_size": artifact_byte_size,
                }
                for package_kind, artifact_ref, artifact_hash, artifact_byte_size in zip(
                    corrected_package_kinds,
                    corrected_artifact_refs,
                    corrected_artifact_hashes,
                    corrected_artifact_byte_sizes,
                )
            ],
        }
    )


def corrected_artifact_basis_hash(
    *,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    reconciliation_record_id: str,
    source_package_set_hash: str,
    source_output_package_ids: list[str],
    source_package_kinds: list[str],
    source_payload_refs: list[str],
    source_payload_hashes: list[str],
    result_review_record_ref: str,
    reviewed_output_items_hash: str,
    package_review_preview_hash: str,
    replacement_artifact_materialization_id: str,
    materialization_basis_hash: str,
    corrected_package_set_id: str,
    corrected_package_set_hash: str,
    artifact_manifest_hash: str,
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.corrected_package_artifact_set_authority_basis.v1",
            "mode": CORRECTED_PACKAGE_ARTIFACT_SET_MODE,
            "operator_decision": CORRECTED_PACKAGE_ARTIFACT_SET_OPERATOR_DECISION,
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "reconciliation_record_id": reconciliation_record_id,
            "source_package_set_hash": source_package_set_hash,
            "source_output_package_ids": source_output_package_ids,
            "source_package_kinds": source_package_kinds,
            "source_payload_refs": source_payload_refs,
            "source_payload_hashes": source_payload_hashes,
            "result_review_record_ref": result_review_record_ref,
            "reviewed_output_items_hash": reviewed_output_items_hash,
            "package_review_preview_hash": package_review_preview_hash,
            "replacement_artifact_materialization_id": replacement_artifact_materialization_id,
            "materialization_basis_hash": materialization_basis_hash,
            "corrected_package_set_id": corrected_package_set_id,
            "corrected_package_set_hash": corrected_package_set_hash,
            "artifact_manifest_hash": artifact_manifest_hash,
        }
    )


def _verify_materialized_artifacts(
    materialization: L3ReplacementPackageArtifactMaterialization,
) -> tuple[list[str], list[str], list[int]]:
    refs = [str(ref) for ref in list(materialization.replacement_payload_refs_json or [])]
    hashes = [str(value) for value in list(materialization.replacement_payload_hashes_json or [])]
    if len(refs) != len(CORRECTED_PACKAGE_ARTIFACT_SET_PACKAGE_KINDS) or len(hashes) != len(refs):
        _raise_mismatch(
            "corrected_package_artifact_set_materialization_vector_mismatch",
            "replacement_artifact_materialization_id",
            "Replacement materialization vectors are incomplete for corrected artifact authority.",
        )
    verified_refs: list[str] = []
    verified_hashes: list[str] = []
    byte_sizes: list[int] = []
    for ref, expected_hash in zip(refs, hashes):
        try:
            artifact_path = Path(ref).resolve(strict=True)
        except FileNotFoundError as exc:
            raise layer3_workbench.Layer3WorkbenchError(
                "corrected_package_artifact_set_artifact_missing",
                "Materialized corrected artifact candidate is missing.",
                status="blocked",
                http_status=409,
                blocked_fields=["replacement_artifact_materialization_id"],
                next_allowed_actions=["rematerialize_replacement_package_artifacts"],
            ) from exc
        if not artifact_path.is_file():
            raise layer3_workbench.Layer3WorkbenchError(
                "corrected_package_artifact_set_artifact_unreadable",
                "Materialized corrected artifact candidate is not readable.",
                status="blocked",
                http_status=409,
                blocked_fields=["replacement_artifact_materialization_id"],
            )
        try:
            artifact_bytes = artifact_path.read_bytes()
        except OSError as exc:
            raise layer3_workbench.Layer3WorkbenchError(
                "corrected_package_artifact_set_artifact_unreadable",
                "Materialized corrected artifact candidate could not be read.",
                status="blocked",
                http_status=409,
                blocked_fields=["replacement_artifact_materialization_id"],
            ) from exc
        actual_hash = hashlib.sha256(artifact_bytes).hexdigest()
        if actual_hash != expected_hash:
            _raise_mismatch(
                "corrected_package_artifact_set_artifact_hash_mismatch",
                "replacement_artifact_materialization_id",
                "Materialized corrected artifact candidate hash does not match durable authority.",
            )
        verified_refs.append(str(artifact_path))
        verified_hashes.append(actual_hash)
        byte_sizes.append(len(artifact_bytes))
    return verified_refs, verified_hashes, byte_sizes


def _redacted_artifact_refs(record: L3CorrectedPackageArtifactSet) -> list[str]:
    return [
        f"artifact://corrected-package-artifacts/{record.corrected_package_artifact_set_id}/{package_kind}"
        for package_kind in list(record.corrected_package_kinds_json or [])
    ]


def _record_response(
    *,
    request_id: str,
    status: str,
    record: L3CorrectedPackageArtifactSet,
) -> dict[str, Any]:
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            CORRECTED_PACKAGE_ARTIFACT_SET_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "corrected_package_artifact_set_id": record.corrected_package_artifact_set_id,
        "session_id": record.session_id,
        "analysis_plan_id": record.analysis_plan_id,
        "pass_run_id": record.pass_run_id,
        "reconciliation_record_id": record.reconciliation_record_id,
        "replacement_artifact_materialization_id": record.replacement_artifact_materialization_id,
        "materialization_basis_hash": record.materialization_basis_hash,
        "source_package_set_hash": record.source_package_set_hash,
        "source_output_package_ids": json_clone(record.source_output_package_ids_json),
        "source_package_kinds": json_clone(record.source_package_kinds_json),
        "source_payload_hashes": json_clone(record.source_payload_hashes_json),
        "result_review_record_ref": record.result_review_record_ref,
        "reviewed_output_items_hash": record.reviewed_output_items_hash,
        "package_review_preview_hash": record.package_review_preview_hash,
        "corrected_package_set_id": record.corrected_package_set_id,
        "corrected_package_set_hash": record.corrected_package_set_hash,
        "corrected_package_kinds": json_clone(record.corrected_package_kinds_json),
        "corrected_artifact_refs": _redacted_artifact_refs(record),
        "corrected_artifact_hashes": json_clone(record.corrected_artifact_hashes_json),
        "corrected_artifact_byte_sizes": json_clone(record.corrected_artifact_byte_sizes_json),
        "artifact_namespace": CORRECTED_PACKAGE_ARTIFACT_NAMESPACE,
        "hash_algorithm": CORRECTED_PACKAGE_ARTIFACT_HASH_ALGORITHM,
        "artifact_manifest_hash": record.artifact_manifest_hash,
        "corrected_artifact_basis_hash": record.corrected_artifact_basis_hash,
        "audit_history": json_clone(record.audit_history_json),
        "authority_snapshot": json_clone(record.authority_snapshot_json),
        "operator_decision": record.operator_decision,
        "corrected_package_artifact_set_mode": CORRECTED_PACKAGE_ARTIFACT_SET_MODE,
        "source_gate": CORRECTED_PACKAGE_ARTIFACT_SET_SOURCE_GATE,
        "corrected_package_artifact_set_record_persisted": True,
        "artifact_refs_redacted": True,
        "package_rebuild_enabled": False,
        "package_row_mutation_enabled": False,
        "source_l3_output_package_mutation_enabled": False,
        "package_payload_rewrite_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "source_widening_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "frontend_only_durable_state_enabled": False,
        "downstream_unavailable": list(CORRECTED_PACKAGE_ARTIFACT_SET_DOWNSTREAM_UNAVAILABLE),
        "next_state": CORRECTED_PACKAGE_ARTIFACT_SET_STATE,
        "created_at": utc_isoformat(record.created_at),
        "updated_at": utc_isoformat(record.updated_at),
        "authority_rail": {
            "server_owned_corrected_artifact_set": True,
            "artifact_namespace": CORRECTED_PACKAGE_ARTIFACT_NAMESPACE,
            "hash_algorithm": CORRECTED_PACKAGE_ARTIFACT_HASH_ALGORITHM,
            "response_artifact_refs_redacted": True,
            "browser_package_bytes_accepted": False,
            "browser_generated_diffs_accepted": False,
            "source_l3_output_package_mutated": False,
            "package_rebuild_runtime_enabled": False,
            "connector_dispatch_enabled": False,
        },
    }


def _existing_record_mismatches_request(
    record: L3CorrectedPackageArtifactSet,
    *,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    reconciliation_record_id: str,
    materialization_id: str,
    materialization_basis_hash: str,
    source_package_set_hash: str,
    source_output_package_ids: list[str],
    source_package_kinds: list[str],
    source_payload_refs: list[str],
    source_payload_hashes: list[str],
    result_review_record_ref: str,
    reviewed_items_hash: str,
    package_review_preview_hash: str,
    corrected_package_set_id: str,
    corrected_package_kinds: list[str],
    corrected_artifact_refs: list[str],
    corrected_artifact_hashes: list[str],
) -> list[str]:
    mismatches = [
        field
        for field, expected in {
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "reconciliation_record_id": reconciliation_record_id,
            "replacement_artifact_materialization_id": materialization_id,
            "materialization_basis_hash": materialization_basis_hash,
            "source_package_set_hash": source_package_set_hash,
            "result_review_record_ref": result_review_record_ref,
            "reviewed_output_items_hash": reviewed_items_hash,
            "package_review_preview_hash": package_review_preview_hash,
            "corrected_package_set_id": corrected_package_set_id,
        }.items()
        if str(getattr(record, field) or "") != str(expected or "")
    ]
    for field, supplied, recorded in (
        ("source_output_package_ids", source_output_package_ids, record.source_output_package_ids_json),
        ("source_package_kinds", source_package_kinds, record.source_package_kinds_json),
        ("source_payload_refs", source_payload_refs, record.source_payload_refs_json),
        ("source_payload_hashes", source_payload_hashes, record.source_payload_hashes_json),
        ("corrected_package_kinds", corrected_package_kinds, record.corrected_package_kinds_json),
        ("corrected_artifact_refs", corrected_artifact_refs, record.corrected_artifact_refs_json),
        ("corrected_artifact_hashes", corrected_artifact_hashes, record.corrected_artifact_hashes_json),
    ):
        if list(recorded or []) != list(supplied):
            mismatches.append(field)
    return sorted(set(mismatches))


def record_corrected_package_artifact_set(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for corrected package artifact-set authority.",
            status="invalid",
            blocked_fields=["client_request_id"],
        )

    unknown = sorted(key for key in payload if key not in CORRECTED_PACKAGE_ARTIFACT_SET_ALLOWED_FIELDS)
    forbidden = sorted(key for key in CORRECTED_PACKAGE_ARTIFACT_SET_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "corrected_package_artifact_set_scope_not_admitted",
            "Corrected package artifact-set request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_corrected_package_artifact_set_authority_only_request"],
        )

    missing = sorted(
        field
        for field in CORRECTED_PACKAGE_ARTIFACT_SET_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_corrected_package_artifact_set_fields",
            "Corrected package artifact-set request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
        )

    if _string(payload.get("operator_decision")) != CORRECTED_PACKAGE_ARTIFACT_SET_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_corrected_package_artifact_set_decision",
            "operator_decision must be record_corrected_package_artifact_set_from_review_corrections.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )

    materialization_id = _string(payload.get("replacement_artifact_materialization_id"))
    materialization_basis_hash = _string(payload.get("materialization_basis_hash"))
    if not materialization_id or not materialization_basis_hash:
        raise layer3_workbench.Layer3WorkbenchError(
            "corrected_package_artifact_set_requires_materialization",
            "Corrected package artifact-set authority requires an existing server-owned artifact materialization.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_artifact_materialization_id", "materialization_basis_hash"],
            next_allowed_actions=["materialize_replacement_package_artifacts_from_supersession_preview"],
        )

    session_id = _string(payload.get("session_id"))
    analysis_plan_id = _string(payload.get("analysis_plan_id"))
    pass_run_id = _string(payload.get("pass_run_id"))
    reconciliation_record_id = _string(payload.get("reconciliation_record_id"))
    session = db.query(L3Session).filter(L3Session.session_id == session_id).one_or_none()
    analysis_plan = (
        db.query(L3AnalysisPlan)
        .filter(L3AnalysisPlan.analysis_plan_id == analysis_plan_id, L3AnalysisPlan.session_id == session_id)
        .one_or_none()
    )
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).one_or_none()
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .one_or_none()
    )
    if session is None or analysis_plan is None or pass_run is None or reconciliation is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "corrected_package_artifact_set_requires_existing_authority",
            "Corrected package artifact-set authority requires existing session, plan, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "analysis_plan_id", "pass_run_id", "reconciliation_record_id"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        _raise_mismatch(
            "corrected_package_artifact_set_pass_run_mismatch",
            "pass_run_id",
            "pass_run_id must belong to the supplied session and analysis plan.",
        )

    review_state = _result_review_state(pass_run)
    if _string(payload.get("result_review_record_ref")) != _string(review_state.get("review_record_ref")):
        _raise_mismatch(
            "corrected_package_artifact_set_result_review_mismatch",
            "result_review_record_ref",
            "Supplied result_review_record_ref does not match the approved result review.",
        )
    reviewed_items_hash = stable_hash(
        {
            "schema_id": "layer3.corrected_package_artifact_set_reviewed_items.v1",
            "reviewed_output_items": json_clone(review_state.get("reviewed_output_items") or []),
        }
    )
    if _string(payload.get("reviewed_output_items_hash")) != reviewed_items_hash:
        _raise_mismatch(
            "corrected_package_artifact_set_reviewed_output_items_hash_mismatch",
            "reviewed_output_items_hash",
            "Supplied reviewed_output_items_hash does not match approved structured result review.",
        )

    expected_package_preview_hash = _package_review_preview_hash(reconciliation)
    if not expected_package_preview_hash or _string(payload.get("package_review_preview_hash")) != expected_package_preview_hash:
        _raise_mismatch(
            "corrected_package_artifact_set_package_review_preview_hash_mismatch",
            "package_review_preview_hash",
            "Supplied package_review_preview_hash does not match package review authority.",
        )

    ordered_packages = _source_package_rows(db, session_id=session_id, reconciliation_record_id=reconciliation_record_id)
    source_output_package_ids = [package.output_package_id for package in ordered_packages]
    source_package_kinds = [package.package_kind for package in ordered_packages]
    source_payload_refs = [package.payload_ref for package in ordered_packages]
    source_payload_hashes = [package.payload_hash for package in ordered_packages]
    source_package_set_hash = stable_hash(
        {
            "schema_id": "layer3.package_supersession_source_package_set.v1",
            "session_id": session_id,
            "reconciliation_record_id": reconciliation_record_id,
            "output_packages": [_package_row_projection(package) for package in ordered_packages],
        }
    )
    for field, expected_values in (
        ("source_output_package_ids", source_output_package_ids),
        ("source_package_kinds", source_package_kinds),
        ("source_payload_refs", source_payload_refs),
        ("source_payload_hashes", source_payload_hashes),
    ):
        _validate_supplied_list(payload=payload, field=field, expected_values=expected_values)
    if _string(payload.get("source_package_set_hash")) != source_package_set_hash:
        _raise_mismatch(
            "corrected_package_artifact_set_source_package_set_hash_mismatch",
            "source_package_set_hash",
            "Supplied source_package_set_hash does not match immutable source package authority.",
        )

    materialization = (
        db.query(L3ReplacementPackageArtifactMaterialization)
        .filter(
            L3ReplacementPackageArtifactMaterialization.replacement_artifact_materialization_id == materialization_id
        )
        .one_or_none()
    )
    if materialization is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "corrected_package_artifact_set_materialization_not_found",
            "Corrected package artifact-set authority requires an existing materialization row.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_artifact_materialization_id"],
        )
    for field, expected in (
        ("session_id", session_id),
        ("analysis_plan_id", analysis_plan_id),
        ("pass_run_id", pass_run_id),
        ("reconciliation_record_id", reconciliation_record_id),
        ("package_supersession_preview_hash", _string(payload.get("package_supersession_preview_hash"))),
        ("source_package_set_hash", source_package_set_hash),
        ("materialization_basis_hash", materialization_basis_hash),
    ):
        if expected and getattr(materialization, field) != expected:
            _raise_mismatch(
                f"corrected_package_artifact_set_materialization_{field}_mismatch",
                "replacement_artifact_materialization_id",
                "Materialization authority must match the corrected artifact set basis.",
            )
    for field, expected_values in (
        ("source_output_package_ids_json", source_output_package_ids),
        ("source_package_kinds_json", source_package_kinds),
        ("source_payload_refs_json", source_payload_refs),
        ("source_payload_hashes_json", source_payload_hashes),
    ):
        if list(getattr(materialization, field) or []) != expected_values:
            _raise_mismatch(
                f"corrected_package_artifact_set_materialization_{field}_mismatch",
                "replacement_artifact_materialization_id",
                "Materialization source vectors must match source package authority.",
            )

    corrected_package_kinds = list(materialization.replacement_package_kinds_json or [])
    if corrected_package_kinds != source_package_kinds:
        _raise_mismatch(
            "corrected_package_artifact_set_materialization_package_kinds_mismatch",
            "replacement_artifact_materialization_id",
            "Materialization package kinds must match source package authority.",
        )
    corrected_package_set_id = stable_id(
        "corrset",
        {
            "session_id": session_id,
            "reconciliation_record_id": reconciliation_record_id,
            "result_review_record_ref": _string(payload.get("result_review_record_ref")),
            "materialization_id": materialization_id,
            "materialization_basis_hash": materialization_basis_hash,
        },
    )
    materialized_refs = [str(ref) for ref in list(materialization.replacement_payload_refs_json or [])]
    materialized_hashes = [str(value) for value in list(materialization.replacement_payload_hashes_json or [])]

    existing_for_request = (
        db.query(L3CorrectedPackageArtifactSet)
        .filter(L3CorrectedPackageArtifactSet.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        mismatches = _existing_record_mismatches_request(
            existing_for_request,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            reconciliation_record_id=reconciliation_record_id,
            materialization_id=materialization_id,
            materialization_basis_hash=materialization_basis_hash,
            source_package_set_hash=source_package_set_hash,
            source_output_package_ids=source_output_package_ids,
            source_package_kinds=source_package_kinds,
            source_payload_refs=source_payload_refs,
            source_payload_hashes=source_payload_hashes,
            result_review_record_ref=_string(payload.get("result_review_record_ref")),
            reviewed_items_hash=reviewed_items_hash,
            package_review_preview_hash=expected_package_preview_hash,
            corrected_package_set_id=corrected_package_set_id,
            corrected_package_kinds=corrected_package_kinds,
            corrected_artifact_refs=materialized_refs,
            corrected_artifact_hashes=materialized_hashes,
        )
        if mismatches:
            _raise_mismatch(
                "corrected_package_artifact_set_client_request_conflict",
                "client_request_id",
                "client_request_id already recorded a different corrected artifact basis.",
            )
        return _record_response(request_id=request_id, status="already_recorded", record=existing_for_request)

    existing_for_materialization = (
        db.query(L3CorrectedPackageArtifactSet)
        .filter(
            L3CorrectedPackageArtifactSet.session_id == session_id,
            L3CorrectedPackageArtifactSet.reconciliation_record_id == reconciliation_record_id,
            L3CorrectedPackageArtifactSet.replacement_artifact_materialization_id == materialization_id,
            L3CorrectedPackageArtifactSet.materialization_basis_hash == materialization_basis_hash,
            L3CorrectedPackageArtifactSet.corrected_package_set_id == corrected_package_set_id,
        )
        .one_or_none()
    )
    if existing_for_materialization is not None:
        mismatches = _existing_record_mismatches_request(
            existing_for_materialization,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            reconciliation_record_id=reconciliation_record_id,
            materialization_id=materialization_id,
            materialization_basis_hash=materialization_basis_hash,
            source_package_set_hash=source_package_set_hash,
            source_output_package_ids=source_output_package_ids,
            source_package_kinds=source_package_kinds,
            source_payload_refs=source_payload_refs,
            source_payload_hashes=source_payload_hashes,
            result_review_record_ref=_string(payload.get("result_review_record_ref")),
            reviewed_items_hash=reviewed_items_hash,
            package_review_preview_hash=expected_package_preview_hash,
            corrected_package_set_id=corrected_package_set_id,
            corrected_package_kinds=corrected_package_kinds,
            corrected_artifact_refs=materialized_refs,
            corrected_artifact_hashes=materialized_hashes,
        )
        if not mismatches:
            return _record_response(
                request_id=request_id,
                status="already_recorded",
                record=existing_for_materialization,
            )

    corrected_artifact_refs, corrected_artifact_hashes, corrected_artifact_byte_sizes = _verify_materialized_artifacts(
        materialization
    )
    corrected_set_hash = corrected_package_set_hash(
        corrected_package_set_id=corrected_package_set_id,
        corrected_package_kinds=corrected_package_kinds,
        corrected_artifact_refs=corrected_artifact_refs,
        corrected_artifact_hashes=corrected_artifact_hashes,
        corrected_artifact_byte_sizes=corrected_artifact_byte_sizes,
    )
    manifest_hash = corrected_artifact_manifest_hash(
        corrected_package_set_id=corrected_package_set_id,
        corrected_package_set_hash=corrected_set_hash,
        corrected_package_kinds=corrected_package_kinds,
        corrected_artifact_refs=corrected_artifact_refs,
        corrected_artifact_hashes=corrected_artifact_hashes,
        corrected_artifact_byte_sizes=corrected_artifact_byte_sizes,
    )
    basis_hash = corrected_artifact_basis_hash(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids=source_output_package_ids,
        source_package_kinds=source_package_kinds,
        source_payload_refs=source_payload_refs,
        source_payload_hashes=source_payload_hashes,
        result_review_record_ref=_string(payload.get("result_review_record_ref")),
        reviewed_output_items_hash=reviewed_items_hash,
        package_review_preview_hash=expected_package_preview_hash,
        replacement_artifact_materialization_id=materialization_id,
        materialization_basis_hash=materialization_basis_hash,
        corrected_package_set_id=corrected_package_set_id,
        corrected_package_set_hash=corrected_set_hash,
        artifact_manifest_hash=manifest_hash,
    )

    existing_for_request = (
        db.query(L3CorrectedPackageArtifactSet)
        .filter(L3CorrectedPackageArtifactSet.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        if existing_for_request.corrected_artifact_basis_hash != basis_hash:
            _raise_mismatch(
                "corrected_package_artifact_set_client_request_conflict",
                "client_request_id",
                "client_request_id already recorded a different corrected artifact basis.",
            )
        return _record_response(request_id=request_id, status="already_recorded", record=existing_for_request)

    existing_for_basis = (
        db.query(L3CorrectedPackageArtifactSet)
        .filter(L3CorrectedPackageArtifactSet.corrected_artifact_basis_hash == basis_hash)
        .one_or_none()
    )
    if existing_for_basis is not None:
        return _record_response(request_id=request_id, status="already_recorded", record=existing_for_basis)

    now = utcnow()
    audit_history = [
        {
            "status": CORRECTED_PACKAGE_ARTIFACT_SET_STATUS,
            "created_at": utc_isoformat(now),
            "redacted_failure_code": None,
        }
    ]
    snapshot = {
        "schema_id": "layer3.corrected_package_artifact_set_snapshot.v1",
        "mode": CORRECTED_PACKAGE_ARTIFACT_SET_MODE,
        "source_gate": CORRECTED_PACKAGE_ARTIFACT_SET_SOURCE_GATE,
        "source": {
            "package_set_hash": source_package_set_hash,
            "output_package_ids": source_output_package_ids,
            "package_kinds": source_package_kinds,
            "payload_hashes": source_payload_hashes,
            "raw_payload_refs_exposed": False,
        },
        "review": {
            "result_review_record_ref": _string(payload.get("result_review_record_ref")),
            "reviewed_output_items_hash": reviewed_items_hash,
            "package_review_preview_hash": expected_package_preview_hash,
        },
        "corrected_artifacts": {
            "corrected_package_set_id": corrected_package_set_id,
            "corrected_package_set_hash": corrected_set_hash,
            "package_kinds": corrected_package_kinds,
            "artifact_hashes": corrected_artifact_hashes,
            "artifact_byte_sizes": corrected_artifact_byte_sizes,
            "artifact_refs_redacted_in_response": True,
        },
        "negative_invariants": {
            "source_l3_output_package_mutated": False,
            "package_rebuild_runtime_enabled": False,
            "package_payload_rewritten": False,
            "browser_bytes_accepted": False,
            "connector_run_created": False,
            "provider_public_url_created": False,
        },
    }
    record = L3CorrectedPackageArtifactSet(
        client_request_id=request_id,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        replacement_artifact_materialization_id=materialization_id,
        materialization_basis_hash=materialization_basis_hash,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids_json=source_output_package_ids,
        source_package_kinds_json=source_package_kinds,
        source_payload_refs_json=source_payload_refs,
        source_payload_hashes_json=source_payload_hashes,
        result_review_record_ref=_string(payload.get("result_review_record_ref")),
        reviewed_output_items_hash=reviewed_items_hash,
        package_review_preview_hash=expected_package_preview_hash,
        corrected_package_set_id=corrected_package_set_id,
        corrected_package_set_hash=corrected_set_hash,
        corrected_package_kinds_json=corrected_package_kinds,
        corrected_artifact_refs_json=corrected_artifact_refs,
        corrected_artifact_hashes_json=corrected_artifact_hashes,
        corrected_artifact_byte_sizes_json=corrected_artifact_byte_sizes,
        artifact_namespace=CORRECTED_PACKAGE_ARTIFACT_NAMESPACE,
        artifact_manifest_hash=manifest_hash,
        corrected_artifact_basis_hash=basis_hash,
        audit_history_json=audit_history,
        authority_snapshot_json=snapshot,
        operator_decision=CORRECTED_PACKAGE_ARTIFACT_SET_OPERATOR_DECISION,
        status=CORRECTED_PACKAGE_ARTIFACT_SET_STATUS,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = (
            db.query(L3CorrectedPackageArtifactSet)
            .filter(L3CorrectedPackageArtifactSet.client_request_id == request_id)
            .one_or_none()
        )
        if existing is None:
            existing = (
                db.query(L3CorrectedPackageArtifactSet)
                .filter(L3CorrectedPackageArtifactSet.corrected_artifact_basis_hash == basis_hash)
                .one_or_none()
            )
        if existing is not None and existing.corrected_artifact_basis_hash == basis_hash:
            return _record_response(request_id=request_id, status="already_recorded", record=existing)
        raise layer3_workbench.Layer3WorkbenchError(
            "corrected_package_artifact_set_in_progress",
            "Corrected package artifact-set authority is already being recorded for this request.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "corrected_artifact_basis_hash"],
            recoverable=True,
            next_allowed_actions=["retry_corrected_package_artifact_set_request"],
        ) from exc
    return _record_response(request_id=request_id, status="recorded", record=record)
