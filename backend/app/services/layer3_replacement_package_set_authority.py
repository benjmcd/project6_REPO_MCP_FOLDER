from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisSet,
    L3AnalysisPlan,
    L3CorrectedPackageArtifactSet,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementPackageSetAuthority,
    L3Session,
)
from app.services import layer3_workbench
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
    SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
)
from app.services.layer3_utils import json_clone, stable_hash, stable_id, utcnow
from app.services.layer3_workbench_package_state import packages_in_kind_order, packages_with_kinds


REPLACEMENT_PACKAGE_SET_AUTHORITY_SCHEMA_ID = "layer3.replacement_package_set_authority.v1"
REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE = "replacement_package_set_authority"
REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_MODE = (
    "replacement_package_set_authority_from_corrected_artifact_set"
)
REPLACEMENT_PACKAGE_SET_AUTHORITY_SOURCE_GATE = "127_PACKAGE_REPLACEMENT_SET_FREEZE"
REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_SOURCE_GATE = (
    "707_PACKAGE_REBUILD_FROM_CORRECTED_ARTIFACT_SET_ENTRY_FREEZE_CURRENT_MAIN_SYNC"
)
SOURCE_DIRECTORY_PACKAGE_LIFECYCLE_SOURCE_GATE = (
    "931_SOURCE_DIRECTORY_PACKAGE_LIFECYCLE_CONTRACT_FREEZE_CURRENT_MAIN_SYNC"
)
SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE = (
    "source_directory_package_lifecycle_replacement_package_set_authority"
)
SOURCE_DIRECTORY_REPLACEMENT_ARTIFACT_NAMESPACE = "source-directory-replacement-package-artifacts"
REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION = "record_replacement_package_set_authority"
REPLACEMENT_PACKAGE_SET_AUTHORITY_STATE = "replacement_package_set_authority_recorded"

REPLACEMENT_PACKAGE_SET_SOURCE_PACKAGE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)

REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUIRED_FIELDS = frozenset(
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
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "authority_basis_hash",
        "operator_decision",
    }
)
REPLACEMENT_PACKAGE_SET_AUTHORITY_FORBIDDEN_FIELDS = frozenset(
    {
        "package_payload",
        "package_variant_content",
        "replacement_package_payloads",
        "edited_package_content",
        "rewrite_output",
        "rebuild_package",
        "mutate_package",
        "replace_package",
        "delete_package",
        "update_payload_ref",
        "update_payload_hash",
        "package_supersession_commit",
        "package_row_mutation",
        "package_payload_rewrite",
        "artifact_manifest",
        "analysis_artifact",
        "handoff",
        "export",
        "connector_key",
        "connector_run_id",
        "destination_id",
        "destination_url",
        "provider_public_url",
        "public_url",
        "signed_url",
        "download_url",
        "source_upload",
        "local_directory",
        "rag_vector_index",
        "runtime_db_write",
        "qualitative_plan",
        "hybrid_execution",
        "rag_execution",
        "hidden_llm_planning",
        "schema_migration",
        "approved_plan_supersession",
        "retry",
        "rerun",
        "cancel",
    }
)
REPLACEMENT_PACKAGE_SET_AUTHORITY_ALLOWED_FIELDS = (
    REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUIRED_FIELDS | REPLACEMENT_PACKAGE_SET_AUTHORITY_FORBIDDEN_FIELDS
)
REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "source_package_set_hash",
        "corrected_package_artifact_set_id",
        "corrected_artifact_basis_hash",
        "operator_decision",
    }
)
REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS = (
    REPLACEMENT_PACKAGE_SET_AUTHORITY_FORBIDDEN_FIELDS
    | {
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "authority_basis_hash",
        "corrected_artifact_refs",
        "corrected_artifact_hashes",
        "corrected_artifact_bytes",
        "corrected_package_payloads",
        "replacement_output_package_ids",
        "source_l3_output_package_write",
        "source_output_package_update",
        "browser_generated_diff",
        "rendered_control_state",
        "auth_context",
        "security_context",
    }
)
REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_ALLOWED_FIELDS = (
    REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_REQUIRED_FIELDS
    | REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS
)
SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "reconciliation_record_id",
        "package_supersession_preview_hash",
        "source_package_set_hash",
        "operator_decision",
    }
)
SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_FORBIDDEN_FIELDS = (
    REPLACEMENT_PACKAGE_SET_AUTHORITY_FORBIDDEN_FIELDS
    | {
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "authority_basis_hash",
        "materialization_basis_hash",
        "replacement_package_set_authority_id",
        "commit_basis_hash",
        "downstream_dependency_hash",
        "frontend_state",
        "browser_state",
        "rendered_control_state",
    }
)
SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_ALLOWED_FIELDS = (
    SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUIRED_FIELDS
    | SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_FORBIDDEN_FIELDS
    | {"analysis_plan_id", "pass_run_id"}
)
REPLACEMENT_PACKAGE_SET_AUTHORITY_DOWNSTREAM_UNAVAILABLE = (
    "package_row_mutation",
    "package_payload_rewrite",
    "package_supersession_commit",
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
    )


def _package_row_projection(package: L3OutputPackage) -> dict[str, Any]:
    return {
        "output_package_id": package.output_package_id,
        "package_kind": package.package_kind,
        "status": package.status,
        "payload_ref": package.payload_ref,
        "payload_hash": package.payload_hash,
    }


def _source_package_rows(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
) -> list[L3OutputPackage]:
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
        package_kinds=REPLACEMENT_PACKAGE_SET_SOURCE_PACKAGE_KINDS,
    )
    if (
        len(packages) != len(REPLACEMENT_PACKAGE_SET_SOURCE_PACKAGE_KINDS)
        or {package.package_kind for package in packages} != set(REPLACEMENT_PACKAGE_SET_SOURCE_PACKAGE_KINDS)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_set_authority_requires_complete_source_package_set",
            "Replacement package-set authority requires the existing canonical_internal, user_facing, and review_facing packages.",
            status="blocked",
            http_status=409,
            blocked_fields=["source_output_package_ids", "source_package_kinds"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    return packages_in_kind_order(packages, package_kinds=REPLACEMENT_PACKAGE_SET_SOURCE_PACKAGE_KINDS)


def replacement_package_set_hash(
    *,
    replacement_package_set_id: str,
    replacement_package_kinds: list[str],
    replacement_payload_refs: list[str],
    replacement_payload_hashes: list[str],
) -> str:
    replacement_rows = [
        {
            "package_kind": package_kind,
            "payload_ref": payload_ref,
            "payload_hash": payload_hash,
        }
        for package_kind, payload_ref, payload_hash in zip(
            replacement_package_kinds,
            replacement_payload_refs,
            replacement_payload_hashes,
        )
    ]
    return stable_hash(
        {
            "schema_id": "layer3.replacement_package_set.v1",
            "replacement_package_set_id": replacement_package_set_id,
            "replacement_packages": replacement_rows,
        }
    )


def replacement_package_set_authority_basis_hash(
    *,
    mode: str = REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    reconciliation_record_id: str,
    source_package_set_hash: str,
    source_output_package_ids: list[str],
    source_package_kinds: list[str],
    source_payload_refs: list[str],
    source_payload_hashes: list[str],
    replacement_package_set_id: str,
    replacement_package_set_hash: str,
    replacement_package_kinds: list[str],
    replacement_payload_refs: list[str],
    replacement_payload_hashes: list[str],
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.replacement_package_set_authority_basis.v1",
            "mode": mode,
            "operator_decision": REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION,
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "reconciliation_record_id": reconciliation_record_id,
            "source_package_set_hash": source_package_set_hash,
            "source_output_package_ids": source_output_package_ids,
            "source_package_kinds": source_package_kinds,
            "source_payload_refs": source_payload_refs,
            "source_payload_hashes": source_payload_hashes,
            "replacement_package_set_id": replacement_package_set_id,
            "replacement_package_set_hash": replacement_package_set_hash,
            "replacement_package_kinds": replacement_package_kinds,
            "replacement_payload_refs": replacement_payload_refs,
            "replacement_payload_hashes": replacement_payload_hashes,
        }
    )


def _authority_response(
    *,
    request_id: str,
    status: str,
    authority: L3ReplacementPackageSetAuthority,
) -> dict[str, Any]:
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            REPLACEMENT_PACKAGE_SET_AUTHORITY_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "replacement_package_set_authority_id": authority.replacement_package_set_authority_id,
        "session_id": authority.session_id,
        "analysis_plan_id": authority.analysis_plan_id,
        "pass_run_id": authority.pass_run_id,
        "reconciliation_record_id": authority.reconciliation_record_id,
        "source_package_set_hash": authority.source_package_set_hash,
        "source_output_package_ids": list(authority.source_output_package_ids_json or []),
        "source_package_kinds": list(authority.source_package_kinds_json or []),
        "source_payload_refs": list(authority.source_payload_refs_json or []),
        "source_payload_hashes": list(authority.source_payload_hashes_json or []),
        "replacement_package_set_id": authority.replacement_package_set_id,
        "replacement_package_set_hash": authority.replacement_package_set_hash,
        "replacement_package_kinds": list(authority.replacement_package_kinds_json or []),
        "replacement_payload_refs": list(authority.replacement_payload_refs_json or []),
        "replacement_payload_hashes": list(authority.replacement_payload_hashes_json or []),
        "authority_basis_hash": authority.authority_basis_hash,
        "authority_snapshot": json_clone(authority.authority_snapshot_json),
        "operator_decision": authority.operator_decision,
        "replacement_package_set_authority_mode": REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE,
        "source_gate": REPLACEMENT_PACKAGE_SET_AUTHORITY_SOURCE_GATE,
        "authority_record_persisted": True,
        "package_row_mutation_enabled": False,
        "package_payload_write_enabled": False,
        "package_supersession_commit_enabled": False,
        "broad_package_mutation_enabled": False,
        "source_widening_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "frontend_only_durable_state_enabled": False,
        "downstream_unavailable": list(REPLACEMENT_PACKAGE_SET_AUTHORITY_DOWNSTREAM_UNAVAILABLE),
        "next_state": REPLACEMENT_PACKAGE_SET_AUTHORITY_STATE,
        "authority_rail": layer3_workbench._authority_rail(  # noqa: SLF001
            session_id=authority.session_id,
            current_gate="package",
            persistence_mode="durable_replacement_package_set_authority_record",
            downstream_unavailable=REPLACEMENT_PACKAGE_SET_AUTHORITY_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }


def _redacted_payload_refs(authority: L3ReplacementPackageSetAuthority) -> list[str]:
    return [
        f"artifact://replacement-package-set/{authority.replacement_package_set_authority_id}/{package_kind}"
        for package_kind in list(authority.replacement_package_kinds_json or [])
    ]


def _redacted_source_payload_refs(authority: L3ReplacementPackageSetAuthority) -> list[str]:
    return [
        f"artifact://source-output-package/{output_package_id}"
        for output_package_id in list(authority.source_output_package_ids_json or [])
    ]


def _authority_response_from_corrected_artifact_set(
    *,
    request_id: str,
    status: str,
    authority: L3ReplacementPackageSetAuthority,
) -> dict[str, Any]:
    snapshot = json_clone(authority.authority_snapshot_json)
    if isinstance(snapshot, dict):
        snapshot["raw_payload_refs_exposed"] = False
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            REPLACEMENT_PACKAGE_SET_AUTHORITY_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "replacement_package_set_authority_id": authority.replacement_package_set_authority_id,
        "session_id": authority.session_id,
        "analysis_plan_id": authority.analysis_plan_id,
        "pass_run_id": authority.pass_run_id,
        "reconciliation_record_id": authority.reconciliation_record_id,
        "source_package_set_hash": authority.source_package_set_hash,
        "source_output_package_ids": list(authority.source_output_package_ids_json or []),
        "source_package_kinds": list(authority.source_package_kinds_json or []),
        "source_payload_refs": _redacted_source_payload_refs(authority),
        "source_payload_hashes": list(authority.source_payload_hashes_json or []),
        "replacement_package_set_id": authority.replacement_package_set_id,
        "replacement_package_set_hash": authority.replacement_package_set_hash,
        "replacement_package_kinds": list(authority.replacement_package_kinds_json or []),
        "replacement_payload_refs": _redacted_payload_refs(authority),
        "replacement_payload_hashes": list(authority.replacement_payload_hashes_json or []),
        "authority_basis_hash": authority.authority_basis_hash,
        "authority_snapshot": snapshot,
        "operator_decision": authority.operator_decision,
        "replacement_package_set_authority_mode": REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_MODE,
        "source_gate": REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_SOURCE_GATE,
        "authority_record_persisted": True,
        "package_row_mutation_enabled": False,
        "package_payload_write_enabled": False,
        "package_supersession_commit_enabled": False,
        "broad_package_mutation_enabled": False,
        "source_widening_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "frontend_only_durable_state_enabled": False,
        "downstream_unavailable": list(REPLACEMENT_PACKAGE_SET_AUTHORITY_DOWNSTREAM_UNAVAILABLE),
        "next_state": REPLACEMENT_PACKAGE_SET_AUTHORITY_STATE,
        "authority_rail": layer3_workbench._authority_rail(  # noqa: SLF001
            session_id=authority.session_id,
            current_gate="package",
            persistence_mode="durable_replacement_package_set_authority_from_corrected_artifact_set",
            downstream_unavailable=REPLACEMENT_PACKAGE_SET_AUTHORITY_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        )
        | {
            "corrected_artifact_set_source_authority": True,
            "response_payload_refs_redacted": True,
            "raw_payload_refs_exposed": False,
        },
    }


def _source_directory_lifecycle_error(
    code: str,
    message: str,
    *,
    blocked_fields: list[str] | None = None,
    status: str = "blocked",
) -> None:
    raise layer3_workbench.Layer3WorkbenchError(
        code,
        message,
        status=status,
        http_status=409,
        blocked_fields=blocked_fields or [],
        recoverable=True,
        next_allowed_actions=["refresh_source_directory_package_lifecycle_authority"],
    )


def _source_directory_lifecycle_dependencies(reconciliation_summary: dict[str, Any]) -> list[dict[str, Any]]:
    dependencies: list[dict[str, Any]] = []
    dependency_specs = (
        (
            "package_review_submit",
            {
                "schema_id",
                "submit_record_ref",
                "package_review_state",
                "source_gate",
            },
        ),
        (
            "handoff_export_prepare",
            {
                "schema_id",
                "prepare_record_ref",
                "handoff_export_state",
                "source_gate",
            },
        ),
        (
            "external_export_download_prepare",
            {
                "schema_id",
                "external_export_download_record_ref",
                "external_export_download_state",
                "source_gate",
            },
        ),
    )
    for state_key, field_names in dependency_specs:
        state = reconciliation_summary.get(state_key)
        if not isinstance(state, dict):
            continue
        dependency = {"state_key": state_key}
        for field_name in sorted(field_names):
            if field_name in state:
                dependency[field_name] = state[field_name]
        if "payload_refs" in state or "payload_ref" in state:
            dependency["payload_refs_redacted"] = True
        dependencies.append(dependency)
    return dependencies


def _source_directory_package_lifecycle_downstream_dependency_hash_for_reconciliation(
    *,
    reconciliation_record_id: str,
    downstream_dependencies: list[dict[str, Any]],
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.source_directory_package_supersession_downstream_dependencies.v1",
            "reconciliation_record_id": reconciliation_record_id,
            "dependencies": downstream_dependencies,
        }
    )


def source_directory_package_lifecycle_preview_hash(
    *,
    source_package_set_hash: str,
    downstream_dependency_hash: str,
    qualitative_analysis_hash: str,
    package_review_preview_hash: str,
    package_review_submit_record_ref: str,
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.source_directory_package_supersession_preview_basis.v1",
            "source_package_set_hash": source_package_set_hash,
            "downstream_dependency_hash": downstream_dependency_hash,
            "qualitative_analysis_hash": qualitative_analysis_hash,
            "package_review_preview_hash": package_review_preview_hash,
            "package_review_submit_record_ref": package_review_submit_record_ref,
            "source_gate": "820_SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RUNTIME_ENTRY_FREEZE",
        }
    )


def _ensure_source_directory_lifecycle_scope(
    db: Session,
    *,
    session_id: str,
    reconciliation_record_id: str,
    payload: dict[str, Any],
) -> tuple[str, str]:
    basis = {
        "session_id": session_id,
        "reconciliation_record_id": reconciliation_record_id,
        "source_gate": SOURCE_DIRECTORY_PACKAGE_LIFECYCLE_SOURCE_GATE,
    }
    analysis_set_id = stable_id("l3srcset", basis, digest_chars=24)
    analysis_plan_id = stable_id("l3srcplan", basis, digest_chars=24)
    pass_run_id = stable_id("l3srcpass", basis, digest_chars=24)
    supplied_plan_id = _string(payload.get("analysis_plan_id"))
    supplied_pass_run_id = _string(payload.get("pass_run_id"))
    if supplied_plan_id and supplied_plan_id != analysis_plan_id:
        _source_directory_lifecycle_error(
            "source_directory_package_lifecycle_analysis_plan_id_mismatch",
            "Supplied analysis_plan_id does not match the server-owned source-directory package lifecycle rail.",
            blocked_fields=["analysis_plan_id"],
            status="conflict",
        )
    if supplied_pass_run_id and supplied_pass_run_id != pass_run_id:
        _source_directory_lifecycle_error(
            "source_directory_package_lifecycle_pass_run_id_mismatch",
            "Supplied pass_run_id does not match the server-owned source-directory package lifecycle rail.",
            blocked_fields=["pass_run_id"],
            status="conflict",
        )

    now = utcnow()
    analysis_set = db.query(L3AnalysisSet).filter(L3AnalysisSet.analysis_set_id == analysis_set_id).one_or_none()
    if analysis_set is None:
        db.add(
            L3AnalysisSet(
                analysis_set_id=analysis_set_id,
                session_id=session_id,
                analysis_group_ids_json=[],
                analysis_unit_ids_json=[],
                set_type="source_directory_package_lifecycle",
                formation_basis_json=basis,
            )
        )
    analysis_plan = db.query(L3AnalysisPlan).filter(L3AnalysisPlan.analysis_plan_id == analysis_plan_id).one_or_none()
    if analysis_plan is None:
        db.add(
            L3AnalysisPlan(
                analysis_plan_id=analysis_plan_id,
                session_id=session_id,
                analysis_set_ids_json=[analysis_set_id],
                status="approved",
                approved_by_operator=True,
                approved_at=now,
                plan_json={
                    "schema_id": "layer3.source_directory_package_lifecycle_plan.v1",
                    "mode": "server_owned_source_directory_package_lifecycle",
                    **basis,
                },
            )
        )
    pass_run = db.query(L3PassRun).filter(L3PassRun.pass_run_id == pass_run_id).one_or_none()
    if pass_run is None:
        db.add(
            L3PassRun(
                pass_run_id=pass_run_id,
                session_id=session_id,
                analysis_plan_id=analysis_plan_id,
                analysis_set_id=analysis_set_id,
                pass_type="source_directory_package_lifecycle",
                engine_family="server_authority",
                status="completed",
                started_at=now,
                completed_at=now,
                input_payload_ref=f"source-directory-package-lifecycle://{reconciliation_record_id}/input",
                output_payload_ref=f"source-directory-package-lifecycle://{reconciliation_record_id}/authority",
                summary_json={
                    "schema_id": "layer3.source_directory_package_lifecycle_pass_run.v1",
                    "source_gate": SOURCE_DIRECTORY_PACKAGE_LIFECYCLE_SOURCE_GATE,
                    "runtime_execution": False,
                    "model_provider_runtime": False,
                    "package_rows_mutated": False,
                },
            )
        )
    db.flush()
    return analysis_plan_id, pass_run_id


def source_directory_package_lifecycle_context(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    session_id = _string(payload.get("session_id"))
    reconciliation_record_id = _string(payload.get("reconciliation_record_id"))
    session = db.query(L3Session).filter(L3Session.session_id == session_id).one_or_none()
    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .one_or_none()
    )
    if session is None or reconciliation is None:
        _source_directory_lifecycle_error(
            "source_directory_package_lifecycle_requires_existing_authority",
            "Source-directory package lifecycle authority requires an existing session and reconciliation record.",
            blocked_fields=["session_id", "reconciliation_record_id"],
        )
    assert session is not None
    assert reconciliation is not None

    reconciliation_summary = json_clone(reconciliation.summary_json or {})
    commit_summary = reconciliation_summary.get("source_directory_qualitative_package_commit")
    submit_state = reconciliation_summary.get("package_review_submit")
    if not isinstance(commit_summary, dict) or not isinstance(submit_state, dict):
        _source_directory_lifecycle_error(
            "source_directory_package_lifecycle_requires_source_directory_package_review",
            "Source-directory package lifecycle authority requires existing package commit and approved review submit state.",
            blocked_fields=["reconciliation_record_id"],
        )
    assert isinstance(commit_summary, dict)
    assert isinstance(submit_state, dict)
    if _string(submit_state.get("package_review_state")) != "package_review_approved":
        _source_directory_lifecycle_error(
            "source_directory_package_lifecycle_requires_approved_review",
            "Source-directory package lifecycle authority requires package_review_approved state.",
            blocked_fields=["package_review_state"],
        )

    authority_basis = commit_summary.get("authority_basis")
    if not isinstance(authority_basis, dict):
        _source_directory_lifecycle_error(
            "source_directory_package_lifecycle_missing_package_commit_basis",
            "Source-directory package lifecycle authority requires package commit authority basis.",
            blocked_fields=["reconciliation_record_id"],
        )
    assert isinstance(authority_basis, dict)
    material_snapshot_id = _string(authority_basis.get("material_snapshot_id"))
    qualitative_analysis_hash = _string(authority_basis.get("qualitative_analysis_hash"))
    package_review_preview_hash = _string(commit_summary.get("package_review_preview_hash"))
    package_review_submit_record_ref = _string(submit_state.get("submit_record_ref"))
    if not all(
        (
            material_snapshot_id,
            qualitative_analysis_hash,
            package_review_preview_hash,
            package_review_submit_record_ref,
        )
    ):
        _source_directory_lifecycle_error(
            "source_directory_package_lifecycle_incomplete_package_commit_basis",
            "Source-directory package lifecycle authority basis is incomplete.",
            blocked_fields=["reconciliation_record_id"],
        )

    source_packages = _source_package_rows(
        db,
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    source_output_package_ids = [package.output_package_id for package in source_packages]
    source_package_kinds = [package.package_kind for package in source_packages]
    source_payload_refs = [package.payload_ref for package in source_packages]
    source_payload_hashes = [package.payload_hash for package in source_packages]
    source_package_set_hash = stable_hash(
        {
            "schema_id": "layer3.source_directory_package_supersession_source_package_set.v1",
            "session_id": session_id,
            "selection_manifest_id": session.selection_manifest_id,
            "material_snapshot_id": material_snapshot_id,
            "reconciliation_record_id": reconciliation_record_id,
            "output_package_ids": source_output_package_ids,
            "package_kinds": source_package_kinds,
            "payload_hashes": source_payload_hashes,
            "payload_refs_redacted": True,
            "source_gate": SOURCE_DIRECTORY_QUALITATIVE_PACKAGE_CONSTRUCTION_FREEZE,
        }
    )
    if _string(payload.get("source_package_set_hash")) != source_package_set_hash:
        _source_directory_lifecycle_error(
            "source_directory_package_lifecycle_source_package_set_hash_mismatch",
            "Supplied source_package_set_hash does not match server-owned source-directory package authority.",
            blocked_fields=["source_package_set_hash"],
            status="conflict",
        )

    downstream_dependencies = _source_directory_lifecycle_dependencies(reconciliation_summary)
    downstream_dependency_hash = _source_directory_package_lifecycle_downstream_dependency_hash_for_reconciliation(
        reconciliation_record_id=reconciliation_record_id,
        downstream_dependencies=downstream_dependencies,
    )
    package_supersession_preview_hash = source_directory_package_lifecycle_preview_hash(
        source_package_set_hash=source_package_set_hash,
        downstream_dependency_hash=downstream_dependency_hash,
        qualitative_analysis_hash=qualitative_analysis_hash,
        package_review_preview_hash=package_review_preview_hash,
        package_review_submit_record_ref=package_review_submit_record_ref,
    )
    if _string(payload.get("package_supersession_preview_hash")) != package_supersession_preview_hash:
        _source_directory_lifecycle_error(
            "source_directory_package_lifecycle_preview_hash_mismatch",
            "Supplied package_supersession_preview_hash does not match server-owned source-directory preview authority.",
            blocked_fields=["package_supersession_preview_hash"],
            status="conflict",
        )

    analysis_plan_id, pass_run_id = _ensure_source_directory_lifecycle_scope(
        db,
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
        payload=payload,
    )
    return {
        "session": session,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "reconciliation": reconciliation,
        "reconciliation_summary": reconciliation_summary,
        "source_packages": source_packages,
        "source_package_set_hash": source_package_set_hash,
        "source_output_package_ids": source_output_package_ids,
        "source_package_kinds": source_package_kinds,
        "source_payload_refs": source_payload_refs,
        "source_payload_hashes": source_payload_hashes,
        "downstream_dependencies": downstream_dependencies,
        "downstream_dependency_hash": downstream_dependency_hash,
        "package_supersession_preview_hash": package_supersession_preview_hash,
        "material_snapshot_id": material_snapshot_id,
        "qualitative_analysis_hash": qualitative_analysis_hash,
        "package_review_preview_hash": package_review_preview_hash,
        "package_review_submit_record_ref": package_review_submit_record_ref,
    }


def _source_directory_replacement_payload_ref(
    *,
    replacement_package_set_id: str,
    package_kind: str,
) -> str:
    return (
        "artifact://source-directory-replacement-package-artifact/"
        f"{replacement_package_set_id}/{package_kind}"
    )


def _authority_response_from_source_directory(
    *,
    request_id: str,
    status: str,
    authority: L3ReplacementPackageSetAuthority,
) -> dict[str, Any]:
    response = _authority_response(request_id=request_id, status=status, authority=authority)
    response["source_payload_refs"] = _redacted_source_payload_refs(authority)
    response["replacement_payload_refs"] = _redacted_payload_refs(authority)
    response["replacement_package_set_authority_mode"] = SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE
    response["source_gate"] = SOURCE_DIRECTORY_PACKAGE_LIFECYCLE_SOURCE_GATE
    response["source_directory_package_lifecycle_authority"] = True
    snapshot = json_clone(response.get("authority_snapshot") or {})
    if isinstance(snapshot, dict):
        source_snapshot = dict(snapshot.get("source") or {})
        source_snapshot["payload_refs"] = response["source_payload_refs"]
        source_snapshot["raw_payload_refs_exposed"] = False
        replacement_snapshot = dict(snapshot.get("replacement") or {})
        replacement_snapshot["payload_refs"] = response["replacement_payload_refs"]
        replacement_snapshot["raw_payload_refs_exposed"] = False
        snapshot["source"] = source_snapshot
        snapshot["replacement"] = replacement_snapshot
        artifacts_snapshot = dict(snapshot.get("artifacts") or {})
        redacted_rows = []
        for row in list(artifacts_snapshot.get("rows") or []):
            row_projection = dict(row)
            package_kind = _string(row_projection.get("package_kind"))
            row_projection["replacement_payload_ref"] = (
                f"artifact://source-directory-replacement-package-artifact/"
                f"{authority.replacement_package_set_authority_id}/{package_kind}"
            )
            row_projection["raw_payload_ref_exposed"] = False
            redacted_rows.append(row_projection)
        artifacts_snapshot["rows"] = redacted_rows
        artifacts_snapshot["raw_payload_refs_exposed"] = False
        snapshot["artifacts"] = artifacts_snapshot
    response["authority_snapshot"] = snapshot
    authority_rail = dict(response.get("authority_rail") or {})
    authority_rail.update(
        {
            "source_directory_package_lifecycle_authority": True,
            "server_computed_payload_refs": True,
            "response_payload_refs_redacted": True,
            "raw_payload_refs_exposed": False,
            "frontend_durable_authority_enabled": False,
        }
    )
    response["authority_rail"] = authority_rail
    return response


def record_replacement_package_set_authority_from_source_directory_supersession_preview(
    db: Session,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for source-directory replacement package-set authority.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_complete_source_directory_replacement_package_set_authority_request"],
        )

    unknown = sorted(key for key in payload if key not in SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_ALLOWED_FIELDS)
    forbidden = sorted(
        key for key in SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_FORBIDDEN_FIELDS if key in payload
    )
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_replacement_package_set_authority_scope_not_admitted",
            "Source-directory replacement package-set authority request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="blocked",
            http_status=409,
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_minimal_source_directory_replacement_package_set_authority_request"],
        )

    missing = sorted(
        field
        for field in SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_source_directory_replacement_package_set_authority_fields",
            "Source-directory replacement package-set authority request is missing required fields: "
            + ", ".join(missing)
            + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_source_directory_replacement_package_set_authority_request"],
        )

    if _string(payload.get("operator_decision")) != REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_source_directory_replacement_package_set_authority_decision",
            "operator_decision must be record_replacement_package_set_authority.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )

    lifecycle = source_directory_package_lifecycle_context(db, payload)
    session = lifecycle["session"]
    session_id = session.session_id
    analysis_plan_id = str(lifecycle["analysis_plan_id"])
    pass_run_id = str(lifecycle["pass_run_id"])
    reconciliation = lifecycle["reconciliation"]
    reconciliation_record_id = reconciliation.reconciliation_record_id
    source_package_set_hash = str(lifecycle["source_package_set_hash"])
    source_output_package_ids = list(lifecycle["source_output_package_ids"])
    source_package_kinds = list(lifecycle["source_package_kinds"])
    source_payload_refs = list(lifecycle["source_payload_refs"])
    source_payload_hashes = list(lifecycle["source_payload_hashes"])
    package_supersession_preview_hash = str(lifecycle["package_supersession_preview_hash"])
    replacement_package_set_id = stable_id(
        "source-directory-replacement-set",
        {
            "session_id": session_id,
            "reconciliation_record_id": reconciliation_record_id,
            "package_supersession_preview_hash": package_supersession_preview_hash,
            "source_package_set_hash": source_package_set_hash,
        },
        digest_chars=24,
    )

    replacement_package_kinds = list(REPLACEMENT_PACKAGE_SET_SOURCE_PACKAGE_KINDS)
    replacement_payload_refs: list[str] = []
    replacement_payload_hashes: list[str] = []
    artifact_rows: list[dict[str, Any]] = []
    for package in lifecycle["source_packages"]:
        artifact_ref = _source_directory_replacement_payload_ref(
            replacement_package_set_id=replacement_package_set_id,
            package_kind=package.package_kind,
        )
        artifact_hash = package.payload_hash
        replacement_payload_refs.append(artifact_ref)
        replacement_payload_hashes.append(artifact_hash)
        artifact_rows.append(
            {
                "package_kind": package.package_kind,
                "source_output_package_id": package.output_package_id,
                "replacement_payload_ref": artifact_ref,
                "replacement_payload_hash": artifact_hash,
                "logical_ref_only": True,
                "artifact_file_written": False,
            }
        )

    replacement_package_set_hash_value = replacement_package_set_hash(
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )
    computed_basis_hash = replacement_package_set_authority_basis_hash(
        mode=SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids=source_output_package_ids,
        source_package_kinds=source_package_kinds,
        source_payload_refs=source_payload_refs,
        source_payload_hashes=source_payload_hashes,
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=replacement_package_set_hash_value,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )

    existing_for_request = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        if existing_for_request.authority_basis_hash != computed_basis_hash:
            _raise_mismatch(
                "source_directory_replacement_package_set_authority_client_request_conflict",
                "client_request_id",
                "client_request_id already recorded different source-directory replacement authority.",
            )
        return _authority_response_from_source_directory(
            request_id=request_id,
            status="already_recorded",
            authority=existing_for_request,
        )

    existing_for_basis = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.authority_basis_hash == computed_basis_hash)
        .one_or_none()
    )
    if existing_for_basis is not None:
        return _authority_response_from_source_directory(
            request_id=request_id,
            status="already_recorded",
            authority=existing_for_basis,
        )

    now = utcnow()
    snapshot = {
        "schema_id": "layer3.source_directory_replacement_package_set_authority_snapshot.v1",
        "mode": SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE,
        "source_gate": SOURCE_DIRECTORY_PACKAGE_LIFECYCLE_SOURCE_GATE,
        "source_directory_package_supersession_preview": {
            "package_supersession_preview_hash": package_supersession_preview_hash,
            "source_package_set_hash": source_package_set_hash,
            "downstream_dependency_hash": lifecycle["downstream_dependency_hash"],
            "package_review_submit_record_ref": lifecycle["package_review_submit_record_ref"],
        },
        "source": {
            "package_set_hash": source_package_set_hash,
            "output_package_ids": source_output_package_ids,
            "package_kinds": source_package_kinds,
            "payload_refs": source_payload_refs,
            "payload_hashes": source_payload_hashes,
            "raw_payload_refs_exposed": False,
        },
        "replacement": {
            "replacement_package_set_id": replacement_package_set_id,
            "replacement_package_set_hash": replacement_package_set_hash_value,
            "package_kinds": replacement_package_kinds,
            "payload_refs": replacement_payload_refs,
            "payload_hashes": replacement_payload_hashes,
            "raw_payload_refs_exposed": False,
        },
        "artifacts": {
            "artifact_namespace": SOURCE_DIRECTORY_REPLACEMENT_ARTIFACT_NAMESPACE,
            "rows": artifact_rows,
        },
        "negative_invariants": {
            "creates_l3_output_package": False,
            "mutates_l3_output_package": False,
            "writes_source_package_payload": False,
            "commits_package_supersession": False,
            "enables_connector_dispatch": False,
            "enables_source_widening": False,
            "enables_qualitative_hybrid_rag": False,
            "enables_provider_public_url": False,
            "enables_full_mockup_activation": False,
        },
    }
    authority = L3ReplacementPackageSetAuthority(
        client_request_id=request_id,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids_json=source_output_package_ids,
        source_package_kinds_json=source_package_kinds,
        source_payload_refs_json=source_payload_refs,
        source_payload_hashes_json=source_payload_hashes,
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=replacement_package_set_hash_value,
        replacement_package_kinds_json=replacement_package_kinds,
        replacement_payload_refs_json=replacement_payload_refs,
        replacement_payload_hashes_json=replacement_payload_hashes,
        authority_basis_hash=computed_basis_hash,
        authority_snapshot_json=snapshot,
        operator_decision=REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION,
        created_at=now,
        updated_at=now,
    )
    db.add(authority)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = (
            db.query(L3ReplacementPackageSetAuthority)
            .filter(L3ReplacementPackageSetAuthority.authority_basis_hash == computed_basis_hash)
            .one_or_none()
        )
        if existing is not None and existing.authority_basis_hash == computed_basis_hash:
            return _authority_response_from_source_directory(
                request_id=request_id,
                status="already_recorded",
                authority=existing,
            )
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_replacement_package_set_authority_in_progress",
            "Source-directory replacement package-set authority is already being recorded for this request.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "authority_basis_hash"],
            recoverable=True,
            next_allowed_actions=["retry_source_directory_replacement_package_set_authority_request"],
        ) from exc
    db.refresh(authority)
    return _authority_response_from_source_directory(
        request_id=request_id,
        status="recorded",
        authority=authority,
    )


def _validate_supplied_list(
    *,
    payload: dict[str, Any],
    field: str,
    expected_values: list[str],
) -> None:
    supplied_values = _string_list(payload.get(field))
    if len(supplied_values) != len(expected_values) or set(supplied_values) != set(expected_values):
        _raise_mismatch(
            f"replacement_package_set_authority_{field}_mismatch",
            field,
            f"Supplied {field} do not match immutable source package authority.",
        )


def record_replacement_package_set_authority(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for replacement package-set authority.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_complete_replacement_package_set_authority_request"],
        )

    unknown = sorted(key for key in payload if key not in REPLACEMENT_PACKAGE_SET_AUTHORITY_ALLOWED_FIELDS)
    forbidden = sorted(key for key in REPLACEMENT_PACKAGE_SET_AUTHORITY_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_set_authority_scope_not_admitted",
            "Replacement package-set authority request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_replacement_package_set_authority_only_request"],
        )

    missing = sorted(
        field
        for field in REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_replacement_package_set_authority_fields",
            "Replacement package-set authority request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_replacement_package_set_authority_request"],
        )

    if _string(payload.get("operator_decision")) != REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_replacement_package_set_authority_decision",
            "operator_decision must be record_replacement_package_set_authority.",
            status="invalid",
            blocked_fields=["operator_decision"],
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
            "replacement_package_set_authority_requires_existing_authority",
            "Replacement package-set authority requires existing session, plan, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "analysis_plan_id", "pass_run_id", "reconciliation_record_id"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        _raise_mismatch(
            "replacement_package_set_authority_pass_run_mismatch",
            "pass_run_id",
            "pass_run_id must belong to the supplied session and analysis plan.",
        )

    ordered_packages = _source_package_rows(
        db,
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
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
            "replacement_package_set_authority_source_package_set_hash_mismatch",
            "source_package_set_hash",
            "Supplied source_package_set_hash does not match immutable source package authority.",
        )

    replacement_package_set_id = _string(payload.get("replacement_package_set_id"))
    replacement_package_kinds = _string_list(payload.get("replacement_package_kinds"))
    replacement_payload_refs = _string_list(payload.get("replacement_payload_refs"))
    replacement_payload_hashes = _string_list(payload.get("replacement_payload_hashes"))
    if (
        len(replacement_package_kinds) != len(REPLACEMENT_PACKAGE_SET_SOURCE_PACKAGE_KINDS)
        or set(replacement_package_kinds) != set(REPLACEMENT_PACKAGE_SET_SOURCE_PACKAGE_KINDS)
        or len(replacement_payload_refs) != len(replacement_package_kinds)
        or len(replacement_payload_hashes) != len(replacement_package_kinds)
        or not all(replacement_payload_refs)
        or not all(replacement_payload_hashes)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_set_authority_replacement_identity_incomplete",
            "Replacement package-set authority requires replacement kinds, refs, and hashes for the complete package set.",
            status="invalid",
            blocked_fields=["replacement_package_kinds", "replacement_payload_refs", "replacement_payload_hashes"],
            next_allowed_actions=["submit_complete_replacement_package_set_authority_request"],
        )
    replacement_rows = {
        package_kind: (payload_ref, payload_hash)
        for package_kind, payload_ref, payload_hash in zip(
            replacement_package_kinds,
            replacement_payload_refs,
            replacement_payload_hashes,
        )
    }
    replacement_package_kinds = list(REPLACEMENT_PACKAGE_SET_SOURCE_PACKAGE_KINDS)
    replacement_payload_refs = [replacement_rows[package_kind][0] for package_kind in replacement_package_kinds]
    replacement_payload_hashes = [replacement_rows[package_kind][1] for package_kind in replacement_package_kinds]

    if replacement_package_set_id in set(source_output_package_ids):
        _raise_mismatch(
            "replacement_package_set_authority_reuses_source_package_id",
            "replacement_package_set_id",
            "replacement_package_set_id must not reuse a source output package id.",
        )
    if set(replacement_payload_refs) & set(source_payload_refs):
        _raise_mismatch(
            "replacement_package_set_authority_reuses_source_payload_ref",
            "replacement_payload_refs",
            "replacement payload refs must be in a separate immutable namespace.",
        )
    computed_replacement_hash = replacement_package_set_hash(
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )
    if _string(payload.get("replacement_package_set_hash")) != computed_replacement_hash:
        _raise_mismatch(
            "replacement_package_set_authority_replacement_package_set_hash_mismatch",
            "replacement_package_set_hash",
            "Supplied replacement_package_set_hash does not match replacement package-set identity.",
        )
    if computed_replacement_hash == source_package_set_hash:
        _raise_mismatch(
            "replacement_package_set_authority_noop_replacement_set",
            "replacement_package_set_hash",
            "replacement_package_set_hash must differ from the source package-set hash.",
        )

    computed_basis_hash = replacement_package_set_authority_basis_hash(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids=source_output_package_ids,
        source_package_kinds=source_package_kinds,
        source_payload_refs=source_payload_refs,
        source_payload_hashes=source_payload_hashes,
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=computed_replacement_hash,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )
    if _string(payload.get("authority_basis_hash")) != computed_basis_hash:
        _raise_mismatch(
            "replacement_package_set_authority_basis_hash_mismatch",
            "authority_basis_hash",
            "Supplied authority_basis_hash does not match replacement package-set authority.",
        )

    existing_for_request = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        if existing_for_request.authority_basis_hash != computed_basis_hash:
            _raise_mismatch(
                "replacement_package_set_authority_client_request_conflict",
                "client_request_id",
                "client_request_id already recorded different replacement package-set authority.",
            )
        return _authority_response(request_id=request_id, status="already_recorded", authority=existing_for_request)

    existing_for_basis = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.authority_basis_hash == computed_basis_hash)
        .one_or_none()
    )
    if existing_for_basis is not None:
        return _authority_response(request_id=request_id, status="already_recorded", authority=existing_for_basis)

    now = utcnow()
    snapshot = {
        "schema_id": "layer3.replacement_package_set_authority_snapshot.v1",
        "mode": REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE,
        "source_gate": REPLACEMENT_PACKAGE_SET_AUTHORITY_SOURCE_GATE,
        "source": {
            "package_set_hash": source_package_set_hash,
            "output_package_ids": source_output_package_ids,
            "package_kinds": source_package_kinds,
            "payload_refs": source_payload_refs,
            "payload_hashes": source_payload_hashes,
        },
        "replacement": {
            "replacement_package_set_id": replacement_package_set_id,
            "replacement_package_set_hash": computed_replacement_hash,
            "package_kinds": replacement_package_kinds,
            "payload_refs": replacement_payload_refs,
            "payload_hashes": replacement_payload_hashes,
        },
        "negative_invariants": {
            "creates_l3_output_package": False,
            "mutates_l3_output_package": False,
            "writes_package_payload": False,
            "enables_package_supersession_commit": False,
            "enables_connector_dispatch": False,
            "enables_source_widening": False,
            "enables_qualitative_hybrid_rag": False,
            "enables_provider_public_url": False,
            "enables_full_mockup_activation": False,
        },
    }
    authority = L3ReplacementPackageSetAuthority(
        client_request_id=request_id,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids_json=source_output_package_ids,
        source_package_kinds_json=source_package_kinds,
        source_payload_refs_json=source_payload_refs,
        source_payload_hashes_json=source_payload_hashes,
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=computed_replacement_hash,
        replacement_package_kinds_json=replacement_package_kinds,
        replacement_payload_refs_json=replacement_payload_refs,
        replacement_payload_hashes_json=replacement_payload_hashes,
        authority_basis_hash=computed_basis_hash,
        authority_snapshot_json=snapshot,
        operator_decision=REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION,
        created_at=now,
        updated_at=now,
    )
    db.add(authority)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = (
            db.query(L3ReplacementPackageSetAuthority)
            .filter(L3ReplacementPackageSetAuthority.client_request_id == request_id)
            .one_or_none()
        )
        if existing is None:
            existing = (
                db.query(L3ReplacementPackageSetAuthority)
                .filter(L3ReplacementPackageSetAuthority.authority_basis_hash == computed_basis_hash)
                .one_or_none()
            )
        if existing is not None and existing.authority_basis_hash == computed_basis_hash:
            return _authority_response(request_id=request_id, status="already_recorded", authority=existing)
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_set_authority_in_progress",
            "Replacement package-set authority is already being recorded for this request.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "authority_basis_hash"],
            recoverable=True,
            next_allowed_actions=["retry_replacement_package_set_authority_request"],
        ) from exc
    return _authority_response(request_id=request_id, status="recorded", authority=authority)


def record_replacement_package_set_authority_from_corrected_artifact_set(
    db: Session,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for corrected-artifact replacement package-set authority.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_corrected_artifact_replacement_package_set_authority_request"],
        )

    unknown = sorted(
        key for key in payload if key not in REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_ALLOWED_FIELDS
    )
    forbidden = sorted(
        key for key in REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS if key in payload
    )
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_set_authority_from_corrected_artifact_set_scope_not_admitted",
            "Corrected-artifact replacement package-set authority request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_corrected_artifact_set_authority_only_request"],
        )

    missing = sorted(
        field
        for field in REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_replacement_package_set_authority_from_corrected_artifact_set_fields",
            "Corrected-artifact replacement package-set authority request is missing required fields: "
            + ", ".join(missing)
            + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_corrected_artifact_replacement_package_set_authority_request"],
        )

    if _string(payload.get("operator_decision")) != REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_replacement_package_set_authority_from_corrected_artifact_set_decision",
            "operator_decision must be record_replacement_package_set_authority.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )

    session_id = _string(payload.get("session_id"))
    analysis_plan_id = _string(payload.get("analysis_plan_id"))
    pass_run_id = _string(payload.get("pass_run_id"))
    reconciliation_record_id = _string(payload.get("reconciliation_record_id"))
    corrected_id = _string(payload.get("corrected_package_artifact_set_id"))
    supplied_corrected_basis_hash = _string(payload.get("corrected_artifact_basis_hash"))

    corrected = (
        db.query(L3CorrectedPackageArtifactSet)
        .filter(L3CorrectedPackageArtifactSet.corrected_package_artifact_set_id == corrected_id)
        .one_or_none()
    )
    if corrected is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_set_authority_corrected_artifact_set_not_found",
            "Replacement package-set authority requires an existing corrected package artifact-set authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["corrected_package_artifact_set_id"],
            next_allowed_actions=["record_corrected_package_artifact_set_authority"],
        )

    for field, expected in (
        ("session_id", session_id),
        ("analysis_plan_id", analysis_plan_id),
        ("pass_run_id", pass_run_id),
        ("reconciliation_record_id", reconciliation_record_id),
        ("source_package_set_hash", _string(payload.get("source_package_set_hash"))),
    ):
        actual = _string(getattr(corrected, field))
        if actual != expected:
            _raise_mismatch(
                f"replacement_package_set_authority_corrected_artifact_set_{field}_mismatch",
                field,
                "Corrected package artifact-set authority does not match the submitted basis.",
            )
    if corrected.corrected_artifact_basis_hash != supplied_corrected_basis_hash:
        _raise_mismatch(
            "replacement_package_set_authority_corrected_artifact_basis_hash_mismatch",
            "corrected_artifact_basis_hash",
            "Supplied corrected_artifact_basis_hash does not match corrected artifact authority.",
        )

    ordered_packages = _source_package_rows(
        db,
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    source_output_package_ids = [package.output_package_id for package in ordered_packages]
    source_package_kinds = [package.package_kind for package in ordered_packages]
    source_payload_refs = [package.payload_ref for package in ordered_packages]
    source_payload_hashes = [package.payload_hash for package in ordered_packages]
    if (
        source_output_package_ids != list(corrected.source_output_package_ids_json or [])
        or source_package_kinds != list(corrected.source_package_kinds_json or [])
        or source_payload_refs != list(corrected.source_payload_refs_json or [])
        or source_payload_hashes != list(corrected.source_payload_hashes_json or [])
    ):
        _raise_mismatch(
            "replacement_package_set_authority_corrected_artifact_source_package_basis_mismatch",
            "source_package_set_hash",
            "Current source package authority does not match the corrected artifact set basis.",
        )

    replacement_package_set_id = corrected.corrected_package_set_id
    replacement_package_kinds = list(corrected.corrected_package_kinds_json or [])
    replacement_payload_refs = list(corrected.corrected_artifact_refs_json or [])
    replacement_payload_hashes = list(corrected.corrected_artifact_hashes_json or [])
    if (
        replacement_package_kinds != source_package_kinds
        or len(replacement_payload_refs) != len(replacement_package_kinds)
        or len(replacement_payload_hashes) != len(replacement_package_kinds)
        or not all(replacement_payload_refs)
        or not all(replacement_payload_hashes)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_set_authority_corrected_artifact_vectors_incomplete",
            "Corrected artifact set vectors are incomplete for replacement package-set authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["corrected_package_artifact_set_id"],
            next_allowed_actions=["refresh_corrected_package_artifact_set_authority"],
        )
    replacement_package_set_hash_value = replacement_package_set_hash(
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )
    computed_basis_hash = replacement_package_set_authority_basis_hash(
        mode=REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_MODE,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        source_package_set_hash=corrected.source_package_set_hash,
        source_output_package_ids=source_output_package_ids,
        source_package_kinds=source_package_kinds,
        source_payload_refs=source_payload_refs,
        source_payload_hashes=source_payload_hashes,
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=replacement_package_set_hash_value,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )

    existing_for_request = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        if existing_for_request.authority_basis_hash != computed_basis_hash:
            _raise_mismatch(
                "replacement_package_set_authority_from_corrected_artifact_set_client_request_conflict",
                "client_request_id",
                "client_request_id already recorded different corrected-artifact replacement authority.",
            )
        return _authority_response_from_corrected_artifact_set(
            request_id=request_id,
            status="already_recorded",
            authority=existing_for_request,
        )

    existing_for_basis = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.authority_basis_hash == computed_basis_hash)
        .one_or_none()
    )
    if existing_for_basis is not None:
        return _authority_response_from_corrected_artifact_set(
            request_id=request_id,
            status="already_recorded",
            authority=existing_for_basis,
        )

    now = utcnow()
    snapshot = {
        "schema_id": "layer3.replacement_package_set_authority_from_corrected_artifact_set_snapshot.v1",
        "mode": REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_MODE,
        "source_gate": REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_SOURCE_GATE,
        "corrected_artifact_set": {
            "corrected_package_artifact_set_id": corrected.corrected_package_artifact_set_id,
            "corrected_artifact_basis_hash": corrected.corrected_artifact_basis_hash,
            "corrected_package_set_hash": corrected.corrected_package_set_hash,
            "artifact_manifest_hash": corrected.artifact_manifest_hash,
        },
        "source": {
            "package_set_hash": corrected.source_package_set_hash,
            "output_package_ids": source_output_package_ids,
            "package_kinds": source_package_kinds,
            "payload_hashes": source_payload_hashes,
            "raw_payload_refs_exposed": False,
        },
        "replacement": {
            "replacement_package_set_id": replacement_package_set_id,
            "replacement_package_set_hash": replacement_package_set_hash_value,
            "package_kinds": replacement_package_kinds,
            "payload_hashes": replacement_payload_hashes,
            "raw_payload_refs_exposed": False,
        },
        "negative_invariants": {
            "creates_l3_output_package": False,
            "mutates_l3_output_package": False,
            "writes_package_payload": False,
            "enables_package_supersession_commit": False,
            "enables_replacement_namespace": False,
            "enables_replacement_artifact_manifest": False,
            "enables_connector_dispatch": False,
            "enables_source_widening": False,
            "enables_qualitative_hybrid_rag": False,
            "enables_provider_public_url": False,
        },
    }
    authority = L3ReplacementPackageSetAuthority(
        client_request_id=request_id,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        source_package_set_hash=corrected.source_package_set_hash,
        source_output_package_ids_json=source_output_package_ids,
        source_package_kinds_json=source_package_kinds,
        source_payload_refs_json=source_payload_refs,
        source_payload_hashes_json=source_payload_hashes,
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=replacement_package_set_hash_value,
        replacement_package_kinds_json=replacement_package_kinds,
        replacement_payload_refs_json=replacement_payload_refs,
        replacement_payload_hashes_json=replacement_payload_hashes,
        authority_basis_hash=computed_basis_hash,
        authority_snapshot_json=snapshot,
        operator_decision=REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION,
        created_at=now,
        updated_at=now,
    )
    db.add(authority)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = (
            db.query(L3ReplacementPackageSetAuthority)
            .filter(L3ReplacementPackageSetAuthority.client_request_id == request_id)
            .one_or_none()
        )
        if existing is None:
            existing = (
                db.query(L3ReplacementPackageSetAuthority)
                .filter(L3ReplacementPackageSetAuthority.authority_basis_hash == computed_basis_hash)
                .one_or_none()
            )
        if existing is not None and existing.authority_basis_hash == computed_basis_hash:
            return _authority_response_from_corrected_artifact_set(
                request_id=request_id,
                status="already_recorded",
                authority=existing,
            )
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_set_authority_from_corrected_artifact_set_in_progress",
            "Corrected-artifact replacement package-set authority is already being recorded for this request.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "authority_basis_hash"],
            recoverable=True,
            next_allowed_actions=["retry_corrected_artifact_replacement_package_set_authority_request"],
        ) from exc
    return _authority_response_from_corrected_artifact_set(
        request_id=request_id,
        status="recorded",
        authority=authority,
    )
