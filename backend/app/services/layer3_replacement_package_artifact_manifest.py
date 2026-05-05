from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisPlan,
    L3OutputPackage,
    L3PackageSupersessionCommit,
    L3PassRun,
    L3ReconciliationRecord,
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
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_MODE = "replacement_package_artifact_manifest_only"
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_SOURCE_GATE = "129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE"
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION = "record_replacement_package_artifact_manifest"
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
) -> dict[str, Any]:
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
        "replacement_package_kinds": json_clone(manifest.replacement_package_kinds_json),
        "replacement_payload_refs": json_clone(manifest.replacement_payload_refs_json),
        "replacement_payload_hashes": json_clone(manifest.replacement_payload_hashes_json),
        "verified_artifact_refs": json_clone(manifest.verified_artifact_refs_json),
        "verified_artifact_hashes": json_clone(manifest.verified_artifact_hashes_json),
        "verified_artifact_byte_sizes": json_clone(manifest.verified_artifact_byte_sizes_json),
        "hash_algorithm": manifest.hash_algorithm,
        "artifact_namespace": manifest.artifact_namespace,
        "artifact_manifest_hash": manifest.artifact_manifest_hash,
        "authority_basis_hash": manifest.authority_basis_hash,
        "manifest_snapshot": json_clone(manifest.manifest_snapshot_json),
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
