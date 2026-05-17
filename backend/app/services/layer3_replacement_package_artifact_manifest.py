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
    L3PackageSupersessionCommit,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementPackageArtifactMaterialization,
    L3ReplacementPackageArtifactManifest,
    L3ReplacementPackageSetAuthority,
    L3Session,
)
from app.services import layer3_workbench
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
)
from app.services.layer3_utils import json_clone, stable_hash, utcnow
from app.services.layer3_workbench_package_state import packages_in_kind_order, packages_with_kinds


REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_SCHEMA_ID = "layer3.replacement_package_artifact_manifest.v1"
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_SCHEMA_ID = (
    "layer3.replacement_package_artifact_manifest_from_authority.v1"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_MODE = "replacement_package_artifact_manifest_only"
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_SOURCE_GATE = "129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE"
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION = "record_replacement_package_artifact_manifest"
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_MODE = (
    "server_computed_replacement_package_artifact_manifest_record_from_authority"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_SOURCE_GATE = (
    "652_REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUEST_AUTHORITY_SOURCE_SELECTION_FREEZE"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_OPERATOR_DECISION = (
    "record_replacement_package_artifact_manifest_from_authority"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_SCHEMA_ID = (
    "layer3.replacement_package_artifact_manifest_from_corrected_artifact_set_authority.v1"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_MODE = (
    "replacement_package_artifact_manifest_from_corrected_artifact_set_authority"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_SOURCE_GATE = (
    "715_CORRECTED_ARTIFACT_REPLACEMENT_MANIFEST_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_OPERATOR_DECISION = (
    "record_replacement_package_artifact_manifest_from_corrected_artifact_set_authority"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_STATE = "replacement_package_artifact_manifest_recorded"
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_STATUS = "verified"
REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE = "replacement-package-artifacts"
REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM = "sha256"

REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_PACKAGE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)

REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "replacement_package_set_authority_id",
        "package_supersession_commit_id",
        "package_supersession_commit_basis_hash",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "hash_algorithm",
        "artifact_namespace",
        "artifact_manifest_hash",
        "authority_basis_hash",
        "operator_decision",
    }
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FORBIDDEN_FIELDS = frozenset(
    {
        "package_payload",
        "package_variant_content",
        "replacement_package_payloads",
        "replacement_package_payload_bytes",
        "edited_package_content",
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
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_ALLOWED_FIELDS = (
    REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUIRED_FIELDS
    | REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FORBIDDEN_FIELDS
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "replacement_artifact_materialization_id",
        "materialization_basis_hash",
        "replacement_package_set_authority_id",
        "replacement_authority_basis_hash",
        "package_supersession_commit_id",
        "package_supersession_commit_basis_hash",
        "operator_decision",
    }
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_FORBIDDEN_FIELDS = frozenset(
    {
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "verified_artifact_refs",
        "verified_artifact_hashes",
        "verified_artifact_byte_sizes",
        "hash_algorithm",
        "artifact_namespace",
        "artifact_manifest_hash",
        "authority_basis_hash",
        "manifest_snapshot",
        "package_payload",
        "package_variant_content",
        "replacement_package_payloads",
        "replacement_package_payload_bytes",
        "edited_package_content",
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
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_ALLOWED_FIELDS = (
    REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_REQUIRED_FIELDS
    | REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_FORBIDDEN_FIELDS
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "corrected_package_artifact_set_id",
        "corrected_artifact_basis_hash",
        "replacement_package_set_authority_id",
        "replacement_authority_basis_hash",
        "package_supersession_commit_id",
        "package_supersession_commit_basis_hash",
        "operator_decision",
    }
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS = (
    REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_FORBIDDEN_FIELDS
    | {
        "replacement_artifact_materialization_id",
        "materialization_basis_hash",
        "corrected_artifact_refs",
        "corrected_artifact_hashes",
        "corrected_artifact_byte_sizes",
        "corrected_artifact_bytes",
        "corrected_package_payloads",
        "local_path",
        "destination_path",
        "destination_url",
        "connector_run_id",
        "connector_run_target_id",
        "credential_id",
        "credential_payload",
        "auth_token",
        "source_directory",
        "rag_query",
        "vector_index",
        "frontend_state",
        "browser_state",
    }
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_ALLOWED_FIELDS = (
    REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_REQUIRED_FIELDS
    | REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_DOWNSTREAM_UNAVAILABLE = (
    "package_mutation_reconstruction",
    "replacement_package_artifact_generation",
    "replacement_output_package_rows",
    "package_payload_rewrite",
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
        next_allowed_actions=["refresh_replacement_package_artifact_manifest_authority"],
    )


def _validate_supplied_list(*, payload: dict[str, Any], field: str, expected_values: list[str]) -> None:
    supplied = _string_list(payload.get(field))
    if supplied != expected_values:
        _raise_mismatch(
            f"replacement_package_artifact_manifest_{field}_mismatch",
            field,
            f"Supplied {field} do not match immutable replacement package authority.",
        )


def _validate_supplied_string(*, payload: dict[str, Any], field: str, expected_value: str) -> None:
    if _string(payload.get(field)) != expected_value:
        _raise_mismatch(
            f"replacement_package_artifact_manifest_{field}_mismatch",
            field,
            f"Supplied {field} does not match immutable replacement package authority.",
        )


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
        package_kinds=REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_PACKAGE_KINDS,
    )
    if (
        len(packages) != len(REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_PACKAGE_KINDS)
        or {package.package_kind for package in packages}
        != set(REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_PACKAGE_KINDS)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_requires_complete_source_package_set",
            "Replacement package artifact manifest requires the existing canonical_internal, user_facing, and review_facing packages.",
            status="blocked",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    return packages_in_kind_order(
        packages,
        package_kinds=REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_PACKAGE_KINDS,
    )


def replacement_package_artifact_manifest_hash(
    *,
    replacement_package_set_authority_id: str,
    package_supersession_commit_id: str,
    replacement_package_set_id: str,
    replacement_package_set_hash: str,
    replacement_package_kinds: list[str],
    replacement_payload_refs: list[str],
    replacement_payload_hashes: list[str],
    verified_artifact_refs: list[str],
    verified_artifact_hashes: list[str],
    verified_artifact_byte_sizes: list[int],
    artifact_namespace: str,
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.replacement_package_artifact_manifest_basis.v1",
            "mode": REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_MODE,
            "replacement_package_set_authority_id": replacement_package_set_authority_id,
            "package_supersession_commit_id": package_supersession_commit_id,
            "replacement_package_set_id": replacement_package_set_id,
            "replacement_package_set_hash": replacement_package_set_hash,
            "replacement_packages": [
                {
                    "package_kind": package_kind,
                    "payload_ref": payload_ref,
                    "payload_hash": payload_hash,
                    "verified_artifact_ref": verified_ref,
                    "verified_artifact_hash": verified_hash,
                    "verified_artifact_byte_size": byte_size,
                }
                for package_kind, payload_ref, payload_hash, verified_ref, verified_hash, byte_size in zip(
                    replacement_package_kinds,
                    replacement_payload_refs,
                    replacement_payload_hashes,
                    verified_artifact_refs,
                    verified_artifact_hashes,
                    verified_artifact_byte_sizes,
                )
            ],
            "hash_algorithm": REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
            "artifact_namespace": artifact_namespace,
        }
    )


def replacement_package_artifact_manifest_authority_basis_hash(
    *,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    reconciliation_record_id: str,
    replacement_package_set_authority_id: str,
    replacement_authority_basis_hash: str,
    package_supersession_commit_id: str,
    package_supersession_commit_basis_hash: str,
    artifact_manifest_hash: str,
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.replacement_package_artifact_manifest_authority.v1",
            "mode": REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_MODE,
            "operator_decision": REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION,
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "reconciliation_record_id": reconciliation_record_id,
            "replacement_package_set_authority_id": replacement_package_set_authority_id,
            "replacement_authority_basis_hash": replacement_authority_basis_hash,
            "package_supersession_commit_id": package_supersession_commit_id,
            "package_supersession_commit_basis_hash": package_supersession_commit_basis_hash,
            "artifact_manifest_hash": artifact_manifest_hash,
        }
    )


def _manifest_response(
    *,
    request_id: str,
    status: str,
    manifest: L3ReplacementPackageArtifactManifest,
    redact_artifact_refs: bool = False,
) -> dict[str, Any]:
    replacement_package_kinds = json_clone(manifest.replacement_package_kinds_json)
    replacement_payload_refs = json_clone(manifest.replacement_payload_refs_json)
    verified_artifact_refs = json_clone(manifest.verified_artifact_refs_json)
    manifest_snapshot = json_clone(manifest.manifest_snapshot_json)
    if redact_artifact_refs:
        redacted_refs = [
            f"artifact://replacement-package-artifacts/{manifest.replacement_package_artifact_manifest_id}/{package_kind}"
            for package_kind in replacement_package_kinds
        ]
        replacement_payload_refs = list(redacted_refs)
        verified_artifact_refs = list(redacted_refs)
        if isinstance(manifest_snapshot, dict):
            replacement_snapshot = manifest_snapshot.get("replacement")
            if isinstance(replacement_snapshot, dict):
                replacement_snapshot["payload_refs"] = list(redacted_refs)
            verified_snapshot = manifest_snapshot.get("verified_artifacts")
            if isinstance(verified_snapshot, dict):
                verified_snapshot["refs"] = list(redacted_refs)

    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "replacement_package_artifact_manifest_id": manifest.replacement_package_artifact_manifest_id,
        "session_id": manifest.session_id,
        "analysis_plan_id": manifest.analysis_plan_id,
        "pass_run_id": manifest.pass_run_id,
        "reconciliation_record_id": manifest.reconciliation_record_id,
        "replacement_package_set_authority_id": manifest.replacement_package_set_authority_id,
        "package_supersession_commit_id": manifest.package_supersession_commit_id,
        "package_supersession_commit_basis_hash": manifest.package_supersession_commit_basis_hash,
        "replacement_package_set_id": manifest.replacement_package_set_id,
        "replacement_package_set_hash": manifest.replacement_package_set_hash,
        "replacement_package_kinds": replacement_package_kinds,
        "replacement_payload_refs": replacement_payload_refs,
        "replacement_payload_hashes": json_clone(manifest.replacement_payload_hashes_json),
        "verified_artifact_refs": verified_artifact_refs,
        "verified_artifact_hashes": json_clone(manifest.verified_artifact_hashes_json),
        "verified_artifact_byte_sizes": json_clone(manifest.verified_artifact_byte_sizes_json),
        "hash_algorithm": manifest.hash_algorithm,
        "artifact_namespace": manifest.artifact_namespace,
        "artifact_manifest_hash": manifest.artifact_manifest_hash,
        "authority_basis_hash": manifest.authority_basis_hash,
        "manifest_snapshot": manifest_snapshot,
        "operator_decision": manifest.operator_decision,
        "replacement_package_artifact_manifest_mode": REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_MODE,
        "source_gate": REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_SOURCE_GATE,
        "manifest_record_persisted": True,
        "artifact_generation_enabled": False,
        "package_row_mutation_enabled": False,
        "package_payload_write_enabled": False,
        "l3_output_package_write_enabled": False,
        "broad_package_mutation_enabled": False,
        "source_widening_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "frontend_only_durable_state_enabled": False,
        "downstream_unavailable": list(REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_DOWNSTREAM_UNAVAILABLE),
        "next_state": REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_STATE,
        "authority_rail": {
            "server_verified_manifest": True,
            "server_artifact_namespace_allowlist": [REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE],
            "hash_algorithm": REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
            "package_rows_mutated": False,
            "package_payloads_written": False,
            "browser_package_bytes_accepted": False,
            "server_computed_from_authority": redact_artifact_refs,
            "browser_replacement_refs_accepted": False,
            "browser_replacement_hashes_accepted": False,
            "browser_manifest_hashes_accepted": False,
            "raw_artifact_refs_exposed": not redact_artifact_refs,
        },
    }


def _read_verified_artifact(ref: str) -> tuple[str, str, int]:
    artifact_path = Path(ref)
    if not artifact_path.is_absolute():
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_ref_outside_namespace",
            "Replacement package artifact refs must be absolute server-side artifact paths.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_payload_refs"],
            next_allowed_actions=["record_server_side_replacement_artifacts_first"],
        )
    try:
        resolved = artifact_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_ref_missing",
            "Replacement package artifact ref is missing and cannot be manifest-verified.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_payload_refs"],
            next_allowed_actions=["record_server_side_replacement_artifacts_first"],
        ) from exc
    except OSError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_ref_unreadable",
            "Replacement package artifact ref cannot be resolved by the server.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_payload_refs"],
            next_allowed_actions=["inspect_replacement_artifact_ref_permissions"],
        ) from exc
    if REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE not in resolved.parts or not resolved.is_file():
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_ref_outside_namespace",
            "Replacement package artifact ref is outside the server-side replacement artifact namespace.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_payload_refs"],
            next_allowed_actions=["record_server_side_replacement_artifacts_first"],
        )
    try:
        artifact_bytes = resolved.read_bytes()
    except OSError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_ref_unreadable",
            "Replacement package artifact ref exists but cannot be read by the server.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_payload_refs"],
            next_allowed_actions=["inspect_replacement_artifact_ref_permissions"],
        ) from exc
    return str(resolved), hashlib.sha256(artifact_bytes).hexdigest(), len(artifact_bytes)


def _verify_replacement_artifacts(
    *,
    replacement_payload_refs: list[str],
    replacement_payload_hashes: list[str],
    source_payload_refs: list[str],
) -> tuple[list[str], list[str], list[int]]:
    verified_refs: list[str] = []
    verified_hashes: list[str] = []
    verified_byte_sizes: list[int] = []
    source_refs = set(source_payload_refs)
    for payload_ref, expected_hash in zip(replacement_payload_refs, replacement_payload_hashes):
        verified_ref, verified_hash, byte_size = _read_verified_artifact(payload_ref)
        if payload_ref in source_refs or verified_ref in source_refs:
            _raise_mismatch(
                "replacement_package_artifact_manifest_reuses_source_payload_ref",
                "replacement_payload_refs",
                "replacement payload refs must stay in a separate immutable artifact namespace.",
            )
        if verified_hash != expected_hash:
            _raise_mismatch(
                "replacement_package_artifact_manifest_payload_hash_mismatch",
                "replacement_payload_hashes",
                "Replacement artifact bytes do not hash to the claimed replacement payload hash.",
            )
        verified_refs.append(verified_ref)
        verified_hashes.append(verified_hash)
        verified_byte_sizes.append(byte_size)
    if len(set(verified_refs)) != len(verified_refs):
        _raise_mismatch(
            "replacement_package_artifact_manifest_duplicate_ref",
            "replacement_payload_refs",
            "replacement artifact refs must be unique within the manifest.",
        )
    return verified_refs, verified_hashes, verified_byte_sizes


def record_replacement_package_artifact_manifest(
    db: Session,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    unknown = sorted(key for key in payload if key not in REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_ALLOWED_FIELDS)
    forbidden = sorted(key for key in REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_scope_not_admitted",
            "Replacement package artifact manifest request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="blocked",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_manifest_only_replacement_artifact_request"],
        )

    missing = sorted(
        field
        for field in REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_replacement_package_artifact_manifest_fields",
            "Replacement package artifact manifest request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_replacement_package_artifact_manifest_request"],
        )

    if _string(payload.get("operator_decision")) != REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_replacement_package_artifact_manifest_decision",
            "operator_decision must be record_replacement_package_artifact_manifest.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    if _string(payload.get("hash_algorithm")) != REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_replacement_package_artifact_manifest_hash_algorithm",
            "hash_algorithm must be sha256.",
            status="invalid",
            blocked_fields=["hash_algorithm"],
        )
    if _string(payload.get("artifact_namespace")) != REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_replacement_package_artifact_manifest_namespace",
            "artifact_namespace must be the server-side replacement package artifact namespace.",
            status="blocked",
            http_status=409,
            blocked_fields=["artifact_namespace"],
            next_allowed_actions=["record_server_side_replacement_artifacts_first"],
        )

    session_id = _string(payload.get("session_id"))
    analysis_plan_id = _string(payload.get("analysis_plan_id"))
    pass_run_id = _string(payload.get("pass_run_id"))
    reconciliation_record_id = _string(payload.get("reconciliation_record_id"))
    authority_id = _string(payload.get("replacement_package_set_authority_id"))
    commit_id = _string(payload.get("package_supersession_commit_id"))

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
            "replacement_package_artifact_manifest_requires_existing_authority",
            "Replacement package artifact manifest requires existing session, plan, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "analysis_plan_id", "pass_run_id", "reconciliation_record_id"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        _raise_mismatch(
            "replacement_package_artifact_manifest_pass_run_mismatch",
            "pass_run_id",
            "pass_run_id must belong to the supplied session and analysis plan.",
        )

    replacement_authority = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.replacement_package_set_authority_id == authority_id)
        .one_or_none()
    )
    if replacement_authority is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_requires_replacement_authority",
            "Replacement package artifact manifest requires an existing replacement package-set authority record.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_package_set_authority_id"],
            next_allowed_actions=["record_replacement_package_set_authority"],
        )

    supersession_commit = (
        db.query(L3PackageSupersessionCommit)
        .filter(L3PackageSupersessionCommit.package_supersession_commit_id == commit_id)
        .one_or_none()
    )
    if supersession_commit is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_requires_supersession_commit",
            "Replacement package artifact manifest requires existing package supersession lineage.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_supersession_commit_id"],
            next_allowed_actions=["commit_package_supersession"],
        )

    for field, expected in (
        ("session_id", session_id),
        ("analysis_plan_id", analysis_plan_id),
        ("pass_run_id", pass_run_id),
        ("reconciliation_record_id", reconciliation_record_id),
    ):
        if getattr(replacement_authority, field) != expected or getattr(supersession_commit, field) != expected:
            _raise_mismatch(
                f"replacement_package_artifact_manifest_stale_{field}",
                field,
                "Replacement package artifact manifest must match replacement authority and supersession lineage.",
            )
    if supersession_commit.replacement_package_set_authority_id != authority_id:
        _raise_mismatch(
            "replacement_package_artifact_manifest_supersession_commit_authority_mismatch",
            "package_supersession_commit_id",
            "package_supersession_commit_id must belong to the supplied replacement package-set authority.",
        )

    _validate_supplied_string(
        payload=payload,
        field="package_supersession_commit_basis_hash",
        expected_value=supersession_commit.commit_basis_hash,
    )
    _validate_supplied_string(
        payload=payload,
        field="replacement_package_set_id",
        expected_value=replacement_authority.replacement_package_set_id,
    )
    _validate_supplied_string(
        payload=payload,
        field="replacement_package_set_hash",
        expected_value=replacement_authority.replacement_package_set_hash,
    )

    replacement_package_kinds = list(REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_PACKAGE_KINDS)
    replacement_payload_refs = list(replacement_authority.replacement_payload_refs_json or [])
    replacement_payload_hashes = list(replacement_authority.replacement_payload_hashes_json or [])
    if list(replacement_authority.replacement_package_kinds_json or []) != replacement_package_kinds:
        _raise_mismatch(
            "replacement_package_artifact_manifest_authority_kinds_mismatch",
            "replacement_package_set_authority_id",
            "Replacement package-set authority package kinds are stale or malformed.",
        )
    if (
        len(replacement_payload_refs) != len(replacement_package_kinds)
        or len(replacement_payload_hashes) != len(replacement_package_kinds)
    ):
        _raise_mismatch(
            "replacement_package_artifact_manifest_authority_vector_mismatch",
            "replacement_package_set_authority_id",
            "Replacement package-set authority refs and hashes must align one-to-one with package kinds.",
        )
    _validate_supplied_list(payload=payload, field="replacement_package_kinds", expected_values=replacement_package_kinds)
    _validate_supplied_list(payload=payload, field="replacement_payload_refs", expected_values=replacement_payload_refs)
    _validate_supplied_list(
        payload=payload,
        field="replacement_payload_hashes",
        expected_values=replacement_payload_hashes,
    )
    if list(supersession_commit.replacement_package_kinds_json or []) != replacement_package_kinds:
        _raise_mismatch(
            "replacement_package_artifact_manifest_supersession_commit_kinds_mismatch",
            "package_supersession_commit_id",
            "Package supersession lineage package kinds are stale relative to replacement authority.",
        )
    if list(supersession_commit.replacement_payload_refs_json or []) != replacement_payload_refs:
        _raise_mismatch(
            "replacement_package_artifact_manifest_supersession_commit_refs_mismatch",
            "package_supersession_commit_id",
            "Package supersession lineage replacement refs are stale relative to replacement authority.",
        )
    if list(supersession_commit.replacement_payload_hashes_json or []) != replacement_payload_hashes:
        _raise_mismatch(
            "replacement_package_artifact_manifest_supersession_commit_hashes_mismatch",
            "package_supersession_commit_id",
            "Package supersession lineage replacement hashes are stale relative to replacement authority.",
        )

    source_packages = _source_package_rows(
        db,
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    source_payload_refs = [package.payload_ref for package in source_packages]
    if source_payload_refs != list(replacement_authority.source_payload_refs_json or []):
        _raise_mismatch(
            "replacement_package_artifact_manifest_source_payload_refs_mismatch",
            "reconciliation_record_id",
            "Current source package refs are stale relative to replacement authority.",
        )
    if [package.payload_hash for package in source_packages] != list(replacement_authority.source_payload_hashes_json or []):
        _raise_mismatch(
            "replacement_package_artifact_manifest_source_payload_hashes_mismatch",
            "reconciliation_record_id",
            "Current source package hashes are stale relative to replacement authority.",
        )

    verified_refs, verified_hashes, verified_byte_sizes = _verify_replacement_artifacts(
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
        source_payload_refs=source_payload_refs,
    )
    computed_manifest_hash = replacement_package_artifact_manifest_hash(
        replacement_package_set_authority_id=authority_id,
        package_supersession_commit_id=commit_id,
        replacement_package_set_id=replacement_authority.replacement_package_set_id,
        replacement_package_set_hash=replacement_authority.replacement_package_set_hash,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
        verified_artifact_refs=verified_refs,
        verified_artifact_hashes=verified_hashes,
        verified_artifact_byte_sizes=verified_byte_sizes,
        artifact_namespace=REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
    )
    if _string(payload.get("artifact_manifest_hash")) != computed_manifest_hash:
        _raise_mismatch(
            "replacement_package_artifact_manifest_hash_mismatch",
            "artifact_manifest_hash",
            "Supplied artifact_manifest_hash does not match server-verified replacement artifacts.",
        )
    computed_basis_hash = replacement_package_artifact_manifest_authority_basis_hash(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        replacement_package_set_authority_id=authority_id,
        replacement_authority_basis_hash=replacement_authority.authority_basis_hash,
        package_supersession_commit_id=commit_id,
        package_supersession_commit_basis_hash=supersession_commit.commit_basis_hash,
        artifact_manifest_hash=computed_manifest_hash,
    )
    if _string(payload.get("authority_basis_hash")) != computed_basis_hash:
        _raise_mismatch(
            "replacement_package_artifact_manifest_authority_basis_hash_mismatch",
            "authority_basis_hash",
            "Supplied authority_basis_hash does not match replacement package artifact manifest authority.",
        )

    existing_for_request = (
        db.query(L3ReplacementPackageArtifactManifest)
        .filter(L3ReplacementPackageArtifactManifest.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        if existing_for_request.authority_basis_hash != computed_basis_hash:
            _raise_mismatch(
                "replacement_package_artifact_manifest_client_request_conflict",
                "client_request_id",
                "client_request_id already recorded a different replacement package artifact manifest.",
            )
        return _manifest_response(request_id=request_id, status="already_recorded", manifest=existing_for_request)

    existing_for_basis = (
        db.query(L3ReplacementPackageArtifactManifest)
        .filter(L3ReplacementPackageArtifactManifest.authority_basis_hash == computed_basis_hash)
        .one_or_none()
    )
    if existing_for_basis is not None:
        return _manifest_response(request_id=request_id, status="already_recorded", manifest=existing_for_basis)

    now = utcnow()
    snapshot = {
        "schema_id": "layer3.replacement_package_artifact_manifest_snapshot.v1",
        "mode": REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_MODE,
        "source_gate": REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_SOURCE_GATE,
        "replacement_package_set_authority": {
            "replacement_package_set_authority_id": authority_id,
            "authority_basis_hash": replacement_authority.authority_basis_hash,
        },
        "package_supersession_commit": {
            "package_supersession_commit_id": commit_id,
            "commit_basis_hash": supersession_commit.commit_basis_hash,
        },
        "replacement": {
            "replacement_package_set_id": replacement_authority.replacement_package_set_id,
            "replacement_package_set_hash": replacement_authority.replacement_package_set_hash,
            "package_kinds": replacement_package_kinds,
            "payload_refs": replacement_payload_refs,
            "payload_hashes": replacement_payload_hashes,
        },
        "verified_artifacts": {
            "artifact_namespace": REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
            "hash_algorithm": REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
            "refs": verified_refs,
            "hashes": verified_hashes,
            "byte_sizes": verified_byte_sizes,
            "artifact_manifest_hash": computed_manifest_hash,
        },
        "negative_invariants": {
            "creates_l3_output_package": False,
            "mutates_l3_output_package": False,
            "writes_package_payload": False,
            "accepts_browser_package_bytes": False,
            "generates_replacement_artifact": False,
            "enables_connector_dispatch": False,
            "enables_source_widening": False,
            "enables_qualitative_hybrid_rag": False,
            "enables_provider_public_url": False,
            "enables_full_mockup_activation": False,
        },
    }
    manifest = L3ReplacementPackageArtifactManifest(
        client_request_id=request_id,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        replacement_package_set_authority_id=authority_id,
        package_supersession_commit_id=commit_id,
        replacement_authority_basis_hash=replacement_authority.authority_basis_hash,
        package_supersession_commit_basis_hash=supersession_commit.commit_basis_hash,
        replacement_package_set_id=replacement_authority.replacement_package_set_id,
        replacement_package_set_hash=replacement_authority.replacement_package_set_hash,
        replacement_package_kinds_json=replacement_package_kinds,
        replacement_payload_refs_json=replacement_payload_refs,
        replacement_payload_hashes_json=replacement_payload_hashes,
        verified_artifact_refs_json=verified_refs,
        verified_artifact_hashes_json=verified_hashes,
        verified_artifact_byte_sizes_json=verified_byte_sizes,
        hash_algorithm=REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
        artifact_namespace=REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
        artifact_manifest_hash=computed_manifest_hash,
        authority_basis_hash=computed_basis_hash,
        manifest_snapshot_json=snapshot,
        operator_decision=REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION,
        status=REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_STATUS,
        created_at=now,
        updated_at=now,
    )
    db.add(manifest)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = (
            db.query(L3ReplacementPackageArtifactManifest)
            .filter(L3ReplacementPackageArtifactManifest.client_request_id == request_id)
            .one_or_none()
        )
        if existing is None:
            existing = (
                db.query(L3ReplacementPackageArtifactManifest)
                .filter(L3ReplacementPackageArtifactManifest.authority_basis_hash == computed_basis_hash)
                .one_or_none()
            )
        if existing is not None and existing.authority_basis_hash == computed_basis_hash:
            return _manifest_response(request_id=request_id, status="already_recorded", manifest=existing)
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_in_progress",
            "Replacement package artifact manifest is already being recorded for this request.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "authority_basis_hash"],
            recoverable=True,
            next_allowed_actions=["retry_replacement_package_artifact_manifest_request"],
        ) from exc
    return _manifest_response(request_id=request_id, status="recorded", manifest=manifest)


def _require_from_authority_materialization(
    db: Session,
    *,
    materialization_id: str,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    reconciliation_record_id: str,
) -> L3ReplacementPackageArtifactMaterialization:
    materialization = (
        db.query(L3ReplacementPackageArtifactMaterialization)
        .filter(
            L3ReplacementPackageArtifactMaterialization.replacement_artifact_materialization_id
            == materialization_id
        )
        .one_or_none()
    )
    if materialization is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_from_authority_requires_materialization",
            "Record-from-authority manifest requests require an existing replacement artifact materialization row.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_artifact_materialization_id"],
            next_allowed_actions=["materialize_replacement_package_artifacts_from_supersession_preview"],
        )
    for field, expected in (
        ("session_id", session_id),
        ("analysis_plan_id", analysis_plan_id),
        ("pass_run_id", pass_run_id),
        ("reconciliation_record_id", reconciliation_record_id),
    ):
        if getattr(materialization, field) != expected:
            _raise_mismatch(
                f"replacement_package_artifact_manifest_from_authority_stale_{field}",
                field,
                "Replacement artifact materialization must match the selected manifest authority basis.",
            )
    return materialization


def _validate_materialization_matches_authority(
    *,
    materialization: L3ReplacementPackageArtifactMaterialization,
    replacement_authority: L3ReplacementPackageSetAuthority,
    supersession_commit: L3PackageSupersessionCommit,
) -> None:
    if materialization.authority_basis_hash != replacement_authority.authority_basis_hash:
        _raise_mismatch(
            "replacement_package_artifact_manifest_from_authority_materialization_authority_mismatch",
            "replacement_artifact_materialization_id",
            "Replacement artifact materialization does not match the replacement package-set authority.",
        )
    if materialization.source_package_set_hash != replacement_authority.source_package_set_hash:
        _raise_mismatch(
            "replacement_package_artifact_manifest_from_authority_materialization_source_hash_mismatch",
            "replacement_artifact_materialization_id",
            "Replacement artifact materialization source package set is stale relative to replacement authority.",
        )
    for field, expected_values in (
        ("source_output_package_ids_json", list(replacement_authority.source_output_package_ids_json or [])),
        ("source_package_kinds_json", list(replacement_authority.source_package_kinds_json or [])),
        ("source_payload_refs_json", list(replacement_authority.source_payload_refs_json or [])),
        ("source_payload_hashes_json", list(replacement_authority.source_payload_hashes_json or [])),
    ):
        if list(getattr(materialization, field) or []) != expected_values:
            _raise_mismatch(
                f"replacement_package_artifact_manifest_from_authority_{field}_mismatch",
                "replacement_artifact_materialization_id",
                "Replacement artifact materialization source vectors must match replacement authority.",
            )
    for field, expected in (
        ("replacement_package_set_id", replacement_authority.replacement_package_set_id),
        ("replacement_package_set_hash", replacement_authority.replacement_package_set_hash),
    ):
        if getattr(materialization, field) != expected or getattr(supersession_commit, field) != expected:
            _raise_mismatch(
                f"replacement_package_artifact_manifest_from_authority_{field}_mismatch",
                "replacement_artifact_materialization_id",
                "Replacement materialization, replacement authority, and supersession commit must agree.",
            )
    for field, expected_values in (
        ("replacement_package_kinds_json", list(replacement_authority.replacement_package_kinds_json or [])),
        ("replacement_payload_refs_json", list(replacement_authority.replacement_payload_refs_json or [])),
        ("replacement_payload_hashes_json", list(replacement_authority.replacement_payload_hashes_json or [])),
    ):
        if list(getattr(materialization, field) or []) != expected_values or list(
            getattr(supersession_commit, field) or []
        ) != expected_values:
            _raise_mismatch(
                f"replacement_package_artifact_manifest_from_authority_{field}_mismatch",
                "replacement_artifact_materialization_id",
                "Replacement materialization, replacement authority, and supersession commit vectors must agree.",
            )


def _validate_from_authority_supplied_string(*, payload: dict[str, Any], field: str, expected_value: str) -> None:
    if _string(payload.get(field)) != expected_value:
        _raise_mismatch(
            f"replacement_package_artifact_manifest_from_authority_{field}_mismatch",
            field,
            f"Supplied {field} does not match server-owned manifest authority.",
        )


def record_replacement_package_artifact_manifest_from_authority(
    db: Session,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    unknown = sorted(
        key for key in payload if key not in REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_ALLOWED_FIELDS
    )
    forbidden = sorted(
        key for key in REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_FORBIDDEN_FIELDS if key in payload
    )
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_from_authority_scope_not_admitted",
            "Replacement package artifact manifest record-from-authority request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_manifest_authority_ids_only_request"],
        )

    missing = sorted(
        field
        for field in REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_replacement_package_artifact_manifest_from_authority_fields",
            "Replacement package artifact manifest record-from-authority request is missing required fields: "
            + ", ".join(missing)
            + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_manifest_authority_ids_only_request"],
        )
    if _string(payload.get("operator_decision")) != REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_replacement_package_artifact_manifest_from_authority_decision",
            "operator_decision must be record_replacement_package_artifact_manifest_from_authority.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )

    session_id = _string(payload.get("session_id"))
    analysis_plan_id = _string(payload.get("analysis_plan_id"))
    pass_run_id = _string(payload.get("pass_run_id"))
    reconciliation_record_id = _string(payload.get("reconciliation_record_id"))
    materialization_id = _string(payload.get("replacement_artifact_materialization_id"))
    authority_id = _string(payload.get("replacement_package_set_authority_id"))
    commit_id = _string(payload.get("package_supersession_commit_id"))

    materialization = _require_from_authority_materialization(
        db,
        materialization_id=materialization_id,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    replacement_authority = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.replacement_package_set_authority_id == authority_id)
        .one_or_none()
    )
    if replacement_authority is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_from_authority_requires_replacement_authority",
            "Record-from-authority manifest requests require an existing replacement package-set authority row.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_package_set_authority_id"],
            next_allowed_actions=["record_replacement_package_set_authority"],
        )
    supersession_commit = (
        db.query(L3PackageSupersessionCommit)
        .filter(L3PackageSupersessionCommit.package_supersession_commit_id == commit_id)
        .one_or_none()
    )
    if supersession_commit is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_from_authority_requires_supersession_commit",
            "Record-from-authority manifest requests require existing package supersession lineage.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_supersession_commit_id"],
            next_allowed_actions=["commit_package_supersession"],
        )

    for field, expected in (
        ("session_id", session_id),
        ("analysis_plan_id", analysis_plan_id),
        ("pass_run_id", pass_run_id),
        ("reconciliation_record_id", reconciliation_record_id),
    ):
        if getattr(replacement_authority, field) != expected or getattr(supersession_commit, field) != expected:
            _raise_mismatch(
                f"replacement_package_artifact_manifest_from_authority_stale_{field}",
                field,
                "Replacement authority and supersession lineage must match the selected manifest authority basis.",
            )
    if supersession_commit.replacement_package_set_authority_id != authority_id:
        _raise_mismatch(
            "replacement_package_artifact_manifest_from_authority_supersession_commit_authority_mismatch",
            "package_supersession_commit_id",
            "package_supersession_commit_id must belong to the supplied replacement package-set authority.",
        )
    _validate_materialization_matches_authority(
        materialization=materialization,
        replacement_authority=replacement_authority,
        supersession_commit=supersession_commit,
    )
    _validate_from_authority_supplied_string(
        payload=payload,
        field="materialization_basis_hash",
        expected_value=materialization.materialization_basis_hash,
    )
    _validate_from_authority_supplied_string(
        payload=payload,
        field="replacement_authority_basis_hash",
        expected_value=replacement_authority.authority_basis_hash,
    )
    _validate_from_authority_supplied_string(
        payload=payload,
        field="package_supersession_commit_basis_hash",
        expected_value=supersession_commit.commit_basis_hash,
    )

    replacement_package_kinds = list(materialization.replacement_package_kinds_json or [])
    replacement_payload_refs = list(materialization.replacement_payload_refs_json or [])
    replacement_payload_hashes = list(materialization.replacement_payload_hashes_json or [])
    source_packages = _source_package_rows(
        db,
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    source_payload_refs = [package.payload_ref for package in source_packages]
    if source_payload_refs != list(replacement_authority.source_payload_refs_json or []):
        _raise_mismatch(
            "replacement_package_artifact_manifest_from_authority_source_payload_refs_mismatch",
            "reconciliation_record_id",
            "Current source package refs are stale relative to replacement authority.",
        )
    verified_refs, verified_hashes, verified_byte_sizes = _verify_replacement_artifacts(
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
        source_payload_refs=source_payload_refs,
    )
    computed_manifest_hash = replacement_package_artifact_manifest_hash(
        replacement_package_set_authority_id=authority_id,
        package_supersession_commit_id=commit_id,
        replacement_package_set_id=replacement_authority.replacement_package_set_id,
        replacement_package_set_hash=replacement_authority.replacement_package_set_hash,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
        verified_artifact_refs=verified_refs,
        verified_artifact_hashes=verified_hashes,
        verified_artifact_byte_sizes=verified_byte_sizes,
        artifact_namespace=REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
    )
    computed_basis_hash = replacement_package_artifact_manifest_authority_basis_hash(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        replacement_package_set_authority_id=authority_id,
        replacement_authority_basis_hash=replacement_authority.authority_basis_hash,
        package_supersession_commit_id=commit_id,
        package_supersession_commit_basis_hash=supersession_commit.commit_basis_hash,
        artifact_manifest_hash=computed_manifest_hash,
    )

    internal_payload = {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "reconciliation_record_id": reconciliation_record_id,
        "replacement_package_set_authority_id": authority_id,
        "package_supersession_commit_id": commit_id,
        "package_supersession_commit_basis_hash": supersession_commit.commit_basis_hash,
        "replacement_package_set_id": replacement_authority.replacement_package_set_id,
        "replacement_package_set_hash": replacement_authority.replacement_package_set_hash,
        "replacement_package_kinds": replacement_package_kinds,
        "replacement_payload_refs": replacement_payload_refs,
        "replacement_payload_hashes": replacement_payload_hashes,
        "hash_algorithm": REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
        "artifact_namespace": REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
        "artifact_manifest_hash": computed_manifest_hash,
        "authority_basis_hash": computed_basis_hash,
        "operator_decision": REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION,
    }
    result = record_replacement_package_artifact_manifest(db, internal_payload)
    manifest = (
        db.query(L3ReplacementPackageArtifactManifest)
        .filter(
            L3ReplacementPackageArtifactManifest.replacement_package_artifact_manifest_id
            == result["replacement_package_artifact_manifest_id"]
        )
        .one()
    )
    response = _manifest_response(
        request_id=request_id,
        status=result["status"],
        manifest=manifest,
        redact_artifact_refs=True,
    )
    response["schema_id"] = REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_SCHEMA_ID
    response["replacement_package_artifact_manifest_mode"] = (
        REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_MODE
    )
    response["source_gate"] = REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_SOURCE_GATE
    response["record_from_authority_operator_decision"] = (
        REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_AUTHORITY_OPERATOR_DECISION
    )
    response["replacement_artifact_materialization_id"] = materialization_id
    response["materialization_basis_hash"] = materialization.materialization_basis_hash
    response["replacement_authority_basis_hash"] = replacement_authority.authority_basis_hash
    response["authority_rail"]["server_verified_materialization_authority"] = True
    response["authority_rail"]["browser_supplied_authority_basis_hash_accepted"] = False
    response["authority_rail"]["browser_supplied_artifact_manifest_hash_accepted"] = False
    response["authority_rail"]["browser_supplied_byte_sizes_accepted"] = False
    response["authority_rail"]["response_artifact_refs_redacted"] = True
    return response


def _corrected_artifact_set(
    db: Session,
    *,
    corrected_id: str,
) -> L3CorrectedPackageArtifactSet:
    corrected = (
        db.query(L3CorrectedPackageArtifactSet)
        .filter(L3CorrectedPackageArtifactSet.corrected_package_artifact_set_id == corrected_id)
        .one_or_none()
    )
    if corrected is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_from_corrected_artifact_set_requires_corrected_artifact_set",
            "Corrected-artifact manifest requests require an existing corrected package artifact-set row.",
            status="blocked",
            http_status=409,
            blocked_fields=["corrected_package_artifact_set_id"],
            next_allowed_actions=["record_corrected_package_artifact_set_authority"],
        )
    return corrected


def _validate_corrected_manifest_authorities(
    *,
    payload: dict[str, Any],
    corrected: L3CorrectedPackageArtifactSet,
    replacement_authority: L3ReplacementPackageSetAuthority,
    supersession_commit: L3PackageSupersessionCommit,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    reconciliation_record_id: str,
) -> tuple[list[str], list[str], list[str]]:
    for authority_name, authority in (
        ("corrected_artifact_set", corrected),
        ("replacement_authority", replacement_authority),
        ("supersession_commit", supersession_commit),
    ):
        for field, expected in (
            ("session_id", session_id),
            ("analysis_plan_id", analysis_plan_id),
            ("pass_run_id", pass_run_id),
            ("reconciliation_record_id", reconciliation_record_id),
        ):
            if getattr(authority, field) != expected:
                _raise_mismatch(
                    f"replacement_package_artifact_manifest_from_corrected_artifact_set_{authority_name}_{field}_mismatch",
                    field,
                    "Corrected artifact, replacement authority, and supersession lineage must match the submitted basis.",
                )

    if corrected.corrected_artifact_basis_hash != _string(payload.get("corrected_artifact_basis_hash")):
        _raise_mismatch(
            "replacement_package_artifact_manifest_from_corrected_artifact_set_corrected_basis_hash_mismatch",
            "corrected_artifact_basis_hash",
            "Supplied corrected_artifact_basis_hash does not match corrected artifact authority.",
        )
    if replacement_authority.authority_basis_hash != _string(payload.get("replacement_authority_basis_hash")):
        _raise_mismatch(
            "replacement_package_artifact_manifest_from_corrected_artifact_set_replacement_authority_basis_hash_mismatch",
            "replacement_authority_basis_hash",
            "Supplied replacement_authority_basis_hash does not match durable replacement authority.",
        )
    if supersession_commit.commit_basis_hash != _string(payload.get("package_supersession_commit_basis_hash")):
        _raise_mismatch(
            "replacement_package_artifact_manifest_from_corrected_artifact_set_supersession_commit_basis_hash_mismatch",
            "package_supersession_commit_basis_hash",
            "Supplied package_supersession_commit_basis_hash does not match package supersession authority.",
        )
    if supersession_commit.replacement_package_set_authority_id != replacement_authority.replacement_package_set_authority_id:
        _raise_mismatch(
            "replacement_package_artifact_manifest_from_corrected_artifact_set_supersession_commit_authority_mismatch",
            "package_supersession_commit_id",
            "package_supersession_commit_id must belong to the supplied replacement package-set authority.",
        )

    replacement_kinds = list(REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_PACKAGE_KINDS)
    corrected_kinds = list(corrected.corrected_package_kinds_json or [])
    corrected_refs = list(corrected.corrected_artifact_refs_json or [])
    corrected_hashes = list(corrected.corrected_artifact_hashes_json or [])
    corrected_byte_sizes = list(corrected.corrected_artifact_byte_sizes_json or [])
    if (
        corrected_kinds != replacement_kinds
        or len(corrected_refs) != len(replacement_kinds)
        or len(corrected_hashes) != len(replacement_kinds)
        or len(corrected_byte_sizes) != len(replacement_kinds)
        or not all(corrected_refs)
        or not all(corrected_hashes)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_from_corrected_artifact_set_corrected_vectors_incomplete",
            "Corrected artifact-set vectors are incomplete for replacement artifact manifest authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["corrected_package_artifact_set_id"],
            next_allowed_actions=["refresh_corrected_package_artifact_set_authority"],
        )

    vector_expectations = (
        ("source_package_set_hash", corrected.source_package_set_hash),
        ("replacement_package_set_id", corrected.corrected_package_set_id),
        ("replacement_package_set_hash", corrected.corrected_package_set_hash),
    )
    for field, expected in vector_expectations:
        if getattr(replacement_authority, field) != expected or getattr(supersession_commit, field) != expected:
            _raise_mismatch(
                f"replacement_package_artifact_manifest_from_corrected_artifact_set_{field}_mismatch",
                field,
                "Replacement authority and supersession commit must derive from the corrected artifact set.",
            )
    for field, expected_values in (
        ("source_output_package_ids_json", list(corrected.source_output_package_ids_json or [])),
        ("source_package_kinds_json", list(corrected.source_package_kinds_json or [])),
        ("source_payload_refs_json", list(corrected.source_payload_refs_json or [])),
        ("source_payload_hashes_json", list(corrected.source_payload_hashes_json or [])),
        ("replacement_package_kinds_json", replacement_kinds),
        ("replacement_payload_refs_json", corrected_refs),
        ("replacement_payload_hashes_json", corrected_hashes),
    ):
        if list(getattr(replacement_authority, field) or []) != expected_values or list(
            getattr(supersession_commit, field) or []
        ) != expected_values:
            _raise_mismatch(
                f"replacement_package_artifact_manifest_from_corrected_artifact_set_{field}_mismatch",
                "corrected_package_artifact_set_id",
                "Corrected artifact, replacement authority, and supersession vectors must agree.",
            )

    return replacement_kinds, corrected_refs, corrected_hashes


def record_replacement_package_artifact_manifest_from_corrected_artifact_set_authority(
    db: Session,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    unknown = sorted(
        key
        for key in payload
        if key not in REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_ALLOWED_FIELDS
    )
    forbidden = sorted(
        key
        for key in REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS
        if key in payload
    )
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_from_corrected_artifact_set_scope_not_admitted",
            "Corrected-artifact replacement manifest request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_corrected_artifact_manifest_authority_ids_only_request"],
        )

    missing = sorted(
        field
        for field in REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_replacement_package_artifact_manifest_from_corrected_artifact_set_fields",
            "Corrected-artifact replacement manifest request is missing required fields: "
            + ", ".join(missing)
            + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_corrected_artifact_manifest_authority_request"],
        )
    if (
        _string(payload.get("operator_decision"))
        != REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_OPERATOR_DECISION
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_replacement_package_artifact_manifest_from_corrected_artifact_set_decision",
            "operator_decision must be record_replacement_package_artifact_manifest_from_corrected_artifact_set_authority.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )

    session_id = _string(payload.get("session_id"))
    analysis_plan_id = _string(payload.get("analysis_plan_id"))
    pass_run_id = _string(payload.get("pass_run_id"))
    reconciliation_record_id = _string(payload.get("reconciliation_record_id"))
    corrected_id = _string(payload.get("corrected_package_artifact_set_id"))
    authority_id = _string(payload.get("replacement_package_set_authority_id"))
    commit_id = _string(payload.get("package_supersession_commit_id"))

    corrected = _corrected_artifact_set(db, corrected_id=corrected_id)
    replacement_authority = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.replacement_package_set_authority_id == authority_id)
        .one_or_none()
    )
    if replacement_authority is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_from_corrected_artifact_set_requires_replacement_authority",
            "Corrected-artifact manifest requests require an existing replacement package-set authority row.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_package_set_authority_id"],
            next_allowed_actions=["record_replacement_package_set_authority_from_corrected_artifact_set"],
        )
    supersession_commit = (
        db.query(L3PackageSupersessionCommit)
        .filter(L3PackageSupersessionCommit.package_supersession_commit_id == commit_id)
        .one_or_none()
    )
    if supersession_commit is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_manifest_from_corrected_artifact_set_requires_supersession_commit",
            "Corrected-artifact manifest requests require existing corrected-artifact package supersession lineage.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_supersession_commit_id"],
            next_allowed_actions=["commit_package_supersession_from_corrected_artifact_set_authority"],
        )

    replacement_package_kinds, replacement_payload_refs, replacement_payload_hashes = (
        _validate_corrected_manifest_authorities(
            payload=payload,
            corrected=corrected,
            replacement_authority=replacement_authority,
            supersession_commit=supersession_commit,
            session_id=session_id,
            analysis_plan_id=analysis_plan_id,
            pass_run_id=pass_run_id,
            reconciliation_record_id=reconciliation_record_id,
        )
    )

    verified_refs, verified_hashes, verified_byte_sizes = _verify_replacement_artifacts(
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
        source_payload_refs=list(corrected.source_payload_refs_json or []),
    )
    computed_manifest_hash = replacement_package_artifact_manifest_hash(
        replacement_package_set_authority_id=authority_id,
        package_supersession_commit_id=commit_id,
        replacement_package_set_id=replacement_authority.replacement_package_set_id,
        replacement_package_set_hash=replacement_authority.replacement_package_set_hash,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
        verified_artifact_refs=verified_refs,
        verified_artifact_hashes=verified_hashes,
        verified_artifact_byte_sizes=verified_byte_sizes,
        artifact_namespace=REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
    )
    computed_basis_hash = replacement_package_artifact_manifest_authority_basis_hash(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        replacement_package_set_authority_id=authority_id,
        replacement_authority_basis_hash=replacement_authority.authority_basis_hash,
        package_supersession_commit_id=commit_id,
        package_supersession_commit_basis_hash=supersession_commit.commit_basis_hash,
        artifact_manifest_hash=computed_manifest_hash,
    )

    internal_payload = {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "reconciliation_record_id": reconciliation_record_id,
        "replacement_package_set_authority_id": authority_id,
        "package_supersession_commit_id": commit_id,
        "package_supersession_commit_basis_hash": supersession_commit.commit_basis_hash,
        "replacement_package_set_id": replacement_authority.replacement_package_set_id,
        "replacement_package_set_hash": replacement_authority.replacement_package_set_hash,
        "replacement_package_kinds": replacement_package_kinds,
        "replacement_payload_refs": replacement_payload_refs,
        "replacement_payload_hashes": replacement_payload_hashes,
        "hash_algorithm": REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
        "artifact_namespace": REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
        "artifact_manifest_hash": computed_manifest_hash,
        "authority_basis_hash": computed_basis_hash,
        "operator_decision": REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION,
    }
    result = record_replacement_package_artifact_manifest(db, internal_payload)
    manifest = (
        db.query(L3ReplacementPackageArtifactManifest)
        .filter(
            L3ReplacementPackageArtifactManifest.replacement_package_artifact_manifest_id
            == result["replacement_package_artifact_manifest_id"]
        )
        .one()
    )
    response = _manifest_response(
        request_id=request_id,
        status=result["status"],
        manifest=manifest,
        redact_artifact_refs=True,
    )
    response["schema_id"] = REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_SCHEMA_ID
    response["replacement_package_artifact_manifest_mode"] = (
        REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_MODE
    )
    response["source_gate"] = REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_SOURCE_GATE
    response["record_from_authority_operator_decision"] = (
        REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_FROM_CORRECTED_ARTIFACT_SET_OPERATOR_DECISION
    )
    response["replacement_artifact_materialization_id"] = None
    response["materialization_basis_hash"] = None
    response["replacement_authority_basis_hash"] = replacement_authority.authority_basis_hash
    response["manifest_snapshot"]["corrected_artifact_set"] = {
        "corrected_package_artifact_set_id": corrected.corrected_package_artifact_set_id,
        "corrected_artifact_basis_hash": corrected.corrected_artifact_basis_hash,
        "raw_artifact_refs_exposed": False,
    }
    response["authority_rail"]["corrected_artifact_set_source_authority"] = True
    response["authority_rail"]["server_verified_corrected_artifact_authority"] = True
    response["authority_rail"]["browser_supplied_corrected_artifact_refs_accepted"] = False
    response["authority_rail"]["browser_supplied_artifact_manifest_hash_accepted"] = False
    response["authority_rail"]["browser_supplied_byte_sizes_accepted"] = False
    response["authority_rail"]["response_artifact_refs_redacted"] = True
    response["authority_rail"]["raw_artifact_refs_exposed"] = False
    return response
