from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisPlan,
    L3CorrectedPackageArtifactSet,
    L3OutputPackage,
    L3PackageSupersessionCommit,
    L3PassRun,
    L3ProviderPrivateSignedUrlAuditEvent,
    L3ProviderPrivateSignedUrlObjectAuthority,
    L3ProviderPrivateSignedUrlReceipt,
    L3ReconciliationRecord,
    L3ReplacementPackageSetAuthority,
    L3Session,
)
from app.services import (
    layer3_package_mutation_entry,
    layer3_replacement_package_set_authority,
    layer3_workbench,
)
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
)
from app.services.layer3_workbench_package_state import packages_in_kind_order, packages_with_kinds
from app.services.layer3_provider_private_signed_url_fake_provider import (
    PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
    ProviderArtifactAuthority,
    ProviderPrivateSignedUrlError,
    ProviderPrivateSignedUrlFakeProvider,
    ProviderPrivateSignedUrlPrepareRequest,
)
from app.services.layer3_provider_private_signed_url_state import (
    INTERNAL_ARTIFACT_REF_PLACEHOLDER,
    PROVIDER_PRIVATE_SIGNED_URL_MAX_TTL_SECONDS,
    ProviderPrivateSignedUrlStateError,
    record_prepared_provider_private_signed_url_receipt,
    record_server_owned_provider_private_signed_url_receipt_use,
    revoke_provider_private_signed_url_receipt,
)
from app.services.layer3_utils import json_clone, stable_hash, stable_json_bytes, utcnow


PACKAGE_SUPERSESSION_COMMIT_SCHEMA_ID = "layer3.package_supersession_commit.v1"
PACKAGE_SUPERSESSION_COMMIT_MODE = "package_supersession_commit_entry"
PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_MODE = (
    "package_supersession_commit_from_corrected_artifact_set_authority"
)
PACKAGE_SUPERSESSION_COMMIT_SOURCE_GATE = "126_PACKAGE_COMMIT_FREEZE"
PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_SOURCE_GATE = (
    "711_CORRECTED_ARTIFACT_PACKAGE_REBUILD_DOWNSTREAM_AUTHORITY_FREEZE_CURRENT_MAIN_SYNC"
)
SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_MODE = (
    "source_directory_package_lifecycle_package_supersession_commit_authority"
)
SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_SOURCE_GATE = (
    layer3_replacement_package_set_authority.SOURCE_DIRECTORY_PACKAGE_LIFECYCLE_SOURCE_GATE
)
PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION = "commit_package_supersession"
PACKAGE_SUPERSESSION_COMMIT_STATE = "package_supersession_commit_recorded"
PACKAGE_SUPERSESSION_COMMIT_STATUS = "committed"
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_DELIVERY_MODE = "provider_private_signed_url"
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REDACTED_MARKER = "provider-private-signed-url:redacted"
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_DEFAULT_TTL_SECONDS = 300
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_FIXED_FAKE_PROVIDER_EPOCH = 0
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_PREPARE_SCHEMA_ID = (
    "layer3.source_directory_package_supersession_provider_private_signed_url.prepare.v1"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_STATUS_SCHEMA_ID = (
    "layer3.source_directory_package_supersession_provider_private_signed_url.status.v1"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_USE_SCHEMA_ID = (
    "layer3.source_directory_package_supersession_provider_private_signed_url.use.v1"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REVOKE_SCHEMA_ID = (
    "layer3.source_directory_package_supersession_provider_private_signed_url.revoke.v1"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_PREPARE_MODE = (
    "source_directory_package_supersession_provider_private_signed_url_prepare_authority"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_STATUS_MODE = (
    "source_directory_package_supersession_provider_private_signed_url_status_authority"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_USE_MODE = (
    "source_directory_package_supersession_provider_private_signed_url_use_authority"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REVOKE_MODE = (
    "source_directory_package_supersession_provider_private_signed_url_revoke_authority"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_PREPARE_OPERATOR_DECISION = (
    "prepare_source_directory_package_supersession_provider_private_signed_url"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_STATUS_OPERATOR_DECISION = (
    "inspect_source_directory_package_supersession_provider_private_signed_url_status"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_USE_OPERATOR_DECISION = (
    "use_source_directory_package_supersession_provider_private_signed_url"
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REVOKE_OPERATOR_DECISION = (
    "revoke_source_directory_package_supersession_provider_private_signed_url"
)

PACKAGE_SUPERSESSION_COMMIT_SOURCE_PACKAGE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)

PACKAGE_SUPERSESSION_COMMIT_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "package_supersession_preview_hash",
        "source_package_set_hash",
        "source_output_package_ids",
        "source_package_kinds",
        "source_payload_refs",
        "source_payload_hashes",
        "replacement_package_set_authority_id",
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "replacement_authority_basis_hash",
        "downstream_dependency_hash",
        "commit_basis_hash",
        "operator_decision",
    }
)
PACKAGE_SUPERSESSION_COMMIT_FORBIDDEN_FIELDS = frozenset(
    {
        "package_payload",
        "package_variant_content",
        "replacement_output_package_ids",
        "replacement_package_payloads",
        "edited_package_content",
        "rewrite_output",
        "rebuild_package",
        "mutate_package",
        "replace_package",
        "delete_package",
        "update_package_row",
        "package_row_mutation",
        "package_payload_rewrite",
        "artifact_manifest",
        "analysis_artifact",
        "handoff_package",
        "export_package",
        "connector_key",
        "connector_payload",
        "destination_id",
        "provider_public_url",
        "public_url",
        "signed_url",
        "source_upload",
        "local_directory",
        "rag_plan",
        "qualitative_plan",
        "hybrid_execution",
        "rag_execution",
        "hidden_llm_plan",
        "ui_control",
        "auth_context",
        "security_context",
    }
)
PACKAGE_SUPERSESSION_COMMIT_ALLOWED_FIELDS = (
    PACKAGE_SUPERSESSION_COMMIT_REQUIRED_FIELDS | PACKAGE_SUPERSESSION_COMMIT_FORBIDDEN_FIELDS
)
PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_REQUIRED_FIELDS = frozenset(
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
        "operator_decision",
    }
)
PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS = (
    PACKAGE_SUPERSESSION_COMMIT_FORBIDDEN_FIELDS
    | {
        "package_supersession_preview_hash",
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
        "downstream_dependency_hash",
        "commit_basis_hash",
        "corrected_artifact_refs",
        "corrected_artifact_hashes",
        "corrected_artifact_bytes",
        "replacement_package_payloads",
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
PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_ALLOWED_FIELDS = (
    PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_REQUIRED_FIELDS
    | PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS
)
SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "reconciliation_record_id",
        "package_supersession_preview_hash",
        "source_package_set_hash",
        "replacement_package_set_authority_id",
        "replacement_authority_basis_hash",
        "operator_decision",
    }
)
SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_FORBIDDEN_FIELDS = (
    PACKAGE_SUPERSESSION_COMMIT_FORBIDDEN_FIELDS
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
        "downstream_dependency_hash",
        "commit_basis_hash",
        "authority_basis_hash",
        "materialization_basis_hash",
        "frontend_state",
        "browser_state",
        "rendered_control_state",
    }
)
SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_ALLOWED_FIELDS = (
    SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_REQUIRED_FIELDS
    | SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_FORBIDDEN_FIELDS
    | {"analysis_plan_id", "pass_run_id"}
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "reconciliation_record_id",
        "package_supersession_commit_id",
        "package_supersession_commit_basis_hash",
        "replacement_package_set_authority_id",
        "replacement_authority_basis_hash",
        "delivery_mode",
        "operator_decision",
    }
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_PREPARE_REQUIRED_FIELDS = (
    SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REQUIRED_FIELDS | {"recipient_scope"}
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_LIFECYCLE_REQUIRED_FIELDS = (
    SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REQUIRED_FIELDS | {"provider_signed_url_receipt_id"}
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REVOKE_REQUIRED_FIELDS = (
    SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_LIFECYCLE_REQUIRED_FIELDS
    | {"idempotency_key", "revoked_by", "revocation_reason"}
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_FORBIDDEN_FIELDS = frozenset(
    {
        "provider_private_signed_url_token",
        "raw_provider_private_signed_url_token",
        "provider_credentials",
        "provider_secret",
        "provider_public_url",
        "raw_public_url",
        "raw_provider_url",
        "public_url",
        "signed_url",
        "download_url",
        "provider_object_key",
        "provider_bucket",
        "provider_container",
        "package_payload",
        "replacement_package_payloads",
        "replacement_package_payload_bytes",
        "source_payload_refs",
        "replacement_payload_refs",
        "local_path",
        "raw_local_path",
        "connector_run_id",
        "destination_url",
        "destination_id",
        "source_expansion",
        "rag_vector_index",
        "model_runtime",
        "frontend_state",
        "browser_state",
        "frontend_durable_authority",
    }
)
SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_ALLOWED_FIELDS = (
    SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REVOKE_REQUIRED_FIELDS
    | SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_FORBIDDEN_FIELDS
    | {"recipient_scope", "requested_ttl_seconds", "decision_notes", "analysis_plan_id", "pass_run_id"}
)
PACKAGE_SUPERSESSION_COMMIT_DOWNSTREAM_UNAVAILABLE = (
    "package_row_mutation",
    "package_payload_rewrite",
    "broad_package_mutation_reconstruction",
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
        next_allowed_actions=["refresh_package_supersession_commit_authority"],
    )


def _validate_supplied_list(*, payload: dict[str, Any], field: str, expected_values: list[str]) -> None:
    supplied = _string_list(payload.get(field))
    if supplied != expected_values:
        _raise_mismatch(
            f"package_supersession_commit_{field}_mismatch",
            field,
            f"Supplied {field} do not match immutable package supersession authority.",
        )


def _ordered_source_packages(
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
        package_kinds=PACKAGE_SUPERSESSION_COMMIT_SOURCE_PACKAGE_KINDS,
    )
    if (
        len(packages) != len(PACKAGE_SUPERSESSION_COMMIT_SOURCE_PACKAGE_KINDS)
        or {package.package_kind for package in packages} != set(PACKAGE_SUPERSESSION_COMMIT_SOURCE_PACKAGE_KINDS)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_commit_requires_complete_source_package_set",
            "Package supersession commit requires the existing canonical_internal, user_facing, and review_facing packages.",
            status="blocked",
            http_status=409,
            blocked_fields=["source_output_package_ids", "source_package_kinds"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    return packages_in_kind_order(packages, package_kinds=PACKAGE_SUPERSESSION_COMMIT_SOURCE_PACKAGE_KINDS)


def _package_row_projection(package: L3OutputPackage) -> dict[str, Any]:
    return {
        "output_package_id": package.output_package_id,
        "package_kind": package.package_kind,
        "status": package.status,
        "payload_ref": package.payload_ref,
        "payload_hash": package.payload_hash,
    }


def _current_downstream_dependencies(reconciliation: L3ReconciliationRecord) -> list[dict[str, Any]]:
    dependencies: list[dict[str, Any]] = []
    for spec in layer3_package_mutation_entry.DOWNSTREAM_DEPENDENCY_SPECS:
        state = layer3_package_mutation_entry._state_from_reconciliation(  # noqa: SLF001
            reconciliation,
            str(spec["state_key"]),
            str(spec["schema_id"]),
        )
        if state is None:
            continue
        dependencies.append(
            {
                "state_key": str(spec["state_key"]),
                "schema_id": state.get("schema_id"),
                "request_ref_field": str(spec["request_ref_field"]),
                "record_ref": _string(state.get(str(spec["state_ref_field"]))),
                "state": state.get(str(spec["state_value_field"])),
                "present": True,
            }
        )
    return dependencies


def package_supersession_downstream_dependency_hash(
    downstream_dependencies: list[dict[str, Any]],
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.package_supersession_downstream_dependencies.v1",
            "downstream_dependencies": downstream_dependencies,
        }
    )


def package_supersession_commit_basis_hash(
    *,
    mode: str = PACKAGE_SUPERSESSION_COMMIT_MODE,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    reconciliation_record_id: str,
    package_supersession_preview_hash: str,
    source_package_set_hash: str,
    source_output_package_ids: list[str],
    source_package_kinds: list[str],
    source_payload_refs: list[str],
    source_payload_hashes: list[str],
    replacement_package_set_authority_id: str,
    replacement_authority_basis_hash: str,
    replacement_package_set_id: str,
    replacement_package_set_hash: str,
    replacement_package_kinds: list[str],
    replacement_payload_refs: list[str],
    replacement_payload_hashes: list[str],
    downstream_dependency_hash: str,
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.package_supersession_commit_basis.v1",
            "mode": mode,
            "operator_decision": PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION,
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "reconciliation_record_id": reconciliation_record_id,
            "package_supersession_preview_hash": package_supersession_preview_hash,
            "source_package_set_hash": source_package_set_hash,
            "source_output_package_ids": source_output_package_ids,
            "source_package_kinds": source_package_kinds,
            "source_payload_refs": source_payload_refs,
            "source_payload_hashes": source_payload_hashes,
            "replacement_package_set_authority_id": replacement_package_set_authority_id,
            "replacement_authority_basis_hash": replacement_authority_basis_hash,
            "replacement_package_set_id": replacement_package_set_id,
            "replacement_package_set_hash": replacement_package_set_hash,
            "replacement_package_kinds": replacement_package_kinds,
            "replacement_payload_refs": replacement_payload_refs,
            "replacement_payload_hashes": replacement_payload_hashes,
            "downstream_dependency_hash": downstream_dependency_hash,
        }
    )


def _commit_response(
    *,
    request_id: str,
    status: str,
    commit: L3PackageSupersessionCommit,
) -> dict[str, Any]:
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            PACKAGE_SUPERSESSION_COMMIT_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "package_supersession_commit_id": commit.package_supersession_commit_id,
        "session_id": commit.session_id,
        "analysis_plan_id": commit.analysis_plan_id,
        "pass_run_id": commit.pass_run_id,
        "reconciliation_record_id": commit.reconciliation_record_id,
        "replacement_package_set_authority_id": commit.replacement_package_set_authority_id,
        "package_supersession_preview_hash": commit.package_supersession_preview_hash,
        "source_package_set_hash": commit.source_package_set_hash,
        "source_output_package_ids": list(commit.source_output_package_ids_json or []),
        "source_package_kinds": list(commit.source_package_kinds_json or []),
        "source_payload_refs": list(commit.source_payload_refs_json or []),
        "source_payload_hashes": list(commit.source_payload_hashes_json or []),
        "replacement_package_set_id": commit.replacement_package_set_id,
        "replacement_package_set_hash": commit.replacement_package_set_hash,
        "replacement_package_kinds": list(commit.replacement_package_kinds_json or []),
        "replacement_payload_refs": list(commit.replacement_payload_refs_json or []),
        "replacement_payload_hashes": list(commit.replacement_payload_hashes_json or []),
        "replacement_authority_basis_hash": commit.replacement_authority_basis_hash,
        "downstream_dependency_hash": commit.downstream_dependency_hash,
        "commit_basis_hash": commit.commit_basis_hash,
        "commit_snapshot": json_clone(commit.commit_snapshot_json),
        "operator_decision": commit.operator_decision,
        "package_supersession_commit_mode": PACKAGE_SUPERSESSION_COMMIT_MODE,
        "source_gate": PACKAGE_SUPERSESSION_COMMIT_SOURCE_GATE,
        "package_supersession_commit_record_persisted": True,
        "package_row_mutation_enabled": False,
        "package_payload_write_enabled": False,
        "l3_output_package_write_enabled": False,
        "broad_package_mutation_enabled": False,
        "source_widening_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "frontend_only_durable_state_enabled": False,
        "downstream_unavailable": list(PACKAGE_SUPERSESSION_COMMIT_DOWNSTREAM_UNAVAILABLE),
        "next_state": PACKAGE_SUPERSESSION_COMMIT_STATE,
        "authority_rail": layer3_workbench._authority_rail(  # noqa: SLF001
            session_id=commit.session_id,
            current_gate="package",
            persistence_mode="durable_package_supersession_lineage_record",
            downstream_unavailable=PACKAGE_SUPERSESSION_COMMIT_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }


def _redacted_commit_source_refs(commit: L3PackageSupersessionCommit) -> list[str]:
    return [
        f"artifact://source-output-package/{commit.package_supersession_commit_id}/{package_kind}"
        for package_kind in list(commit.source_package_kinds_json or [])
    ]


def _redacted_commit_replacement_refs(commit: L3PackageSupersessionCommit) -> list[str]:
    return [
        f"artifact://package-supersession-commit-replacement/{commit.package_supersession_commit_id}/{package_kind}"
        for package_kind in list(commit.replacement_package_kinds_json or [])
    ]


def _commit_response_from_corrected_artifact_authority(
    *,
    request_id: str,
    status: str,
    commit: L3PackageSupersessionCommit,
    corrected: L3CorrectedPackageArtifactSet,
) -> dict[str, Any]:
    response = _commit_response(request_id=request_id, status=status, commit=commit)
    source_refs = _redacted_commit_source_refs(commit)
    replacement_refs = _redacted_commit_replacement_refs(commit)
    response["source_payload_refs"] = source_refs
    response["replacement_payload_refs"] = replacement_refs
    snapshot = json_clone(response.get("commit_snapshot") or {})
    if isinstance(snapshot, dict):
        source_snapshot = dict(snapshot.get("source") or {})
        source_snapshot["payload_refs"] = source_refs
        source_snapshot["raw_payload_refs_exposed"] = False
        replacement_snapshot = dict(snapshot.get("replacement") or {})
        replacement_snapshot["payload_refs"] = replacement_refs
        replacement_snapshot["raw_payload_refs_exposed"] = False
        snapshot["source"] = source_snapshot
        snapshot["replacement"] = replacement_snapshot
        snapshot["corrected_artifact_set"] = {
            "corrected_package_artifact_set_id": corrected.corrected_package_artifact_set_id,
            "corrected_artifact_basis_hash": corrected.corrected_artifact_basis_hash,
            "corrected_package_set_id": corrected.corrected_package_set_id,
            "corrected_package_set_hash": corrected.corrected_package_set_hash,
            "raw_artifact_refs_exposed": False,
        }
    response["commit_snapshot"] = snapshot
    response["source_gate"] = PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_SOURCE_GATE
    authority_rail = dict(response.get("authority_rail") or {})
    authority_rail.update(
        {
            "corrected_artifact_set_source_authority": True,
            "server_computed_payload_refs": True,
            "response_payload_refs_redacted": True,
            "raw_payload_refs_exposed": False,
        }
    )
    response["authority_rail"] = authority_rail
    return response


def _source_directory_commit_error(
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


def _commit_response_from_source_directory_lifecycle(
    *,
    request_id: str,
    status: str,
    commit: L3PackageSupersessionCommit,
) -> dict[str, Any]:
    response = _commit_response(request_id=request_id, status=status, commit=commit)
    source_refs = _redacted_commit_source_refs(commit)
    replacement_refs = _redacted_commit_replacement_refs(commit)
    response["source_payload_refs"] = source_refs
    response["replacement_payload_refs"] = replacement_refs
    response["package_supersession_commit_mode"] = SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_MODE
    response["source_gate"] = SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_SOURCE_GATE
    response["source_directory_package_lifecycle_authority"] = True
    snapshot = json_clone(response.get("commit_snapshot") or {})
    if isinstance(snapshot, dict):
        source_snapshot = dict(snapshot.get("source") or {})
        source_snapshot["payload_refs"] = source_refs
        source_snapshot["raw_payload_refs_exposed"] = False
        replacement_snapshot = dict(snapshot.get("replacement") or {})
        replacement_snapshot["payload_refs"] = replacement_refs
        replacement_snapshot["raw_payload_refs_exposed"] = False
        snapshot["source"] = source_snapshot
        snapshot["replacement"] = replacement_snapshot
    response["commit_snapshot"] = snapshot
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


def _epoch_iso(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def _provider_private_receipt_state(
    receipt: L3ProviderPrivateSignedUrlReceipt,
    *,
    now_epoch: int,
) -> str:
    if (
        receipt.provider_private_signed_url_state == "provider_private_signed_url_prepared"
        and now_epoch >= int(receipt.provider_private_signed_url_expires_at.timestamp())
    ):
        return "provider_private_signed_url_expired"
    return receipt.provider_private_signed_url_state


def _latest_provider_private_audit(
    db: Session,
    *,
    receipt_id: str,
) -> L3ProviderPrivateSignedUrlAuditEvent | None:
    return (
        db.query(L3ProviderPrivateSignedUrlAuditEvent)
        .filter(L3ProviderPrivateSignedUrlAuditEvent.provider_private_signed_url_receipt_id == receipt_id)
        .order_by(
            L3ProviderPrivateSignedUrlAuditEvent.created_at.desc(),
            L3ProviderPrivateSignedUrlAuditEvent.provider_private_signed_url_audit_event_id.desc(),
        )
        .first()
    )


def _provider_private_audit_receipt(
    *,
    receipt: L3ProviderPrivateSignedUrlReceipt,
    authority: L3ProviderPrivateSignedUrlObjectAuthority,
    audit: L3ProviderPrivateSignedUrlAuditEvent | None,
) -> dict[str, Any]:
    return {
        "provider_private_signed_url_receipt_id": receipt.provider_private_signed_url_receipt_id,
        "provider_private_signed_url_object_authority_id": authority.provider_private_signed_url_object_authority_id,
        "provider_private_signed_url_audit_event_id": (
            audit.provider_private_signed_url_audit_event_id if audit is not None else None
        ),
        "authority_hash": authority.authority_hash,
        "provider_object_identity_hash": authority.provider_object_identity_hash,
        "provider_private_signed_url_token_prefix": receipt.provider_private_signed_url_token_prefix,
        "provider_private_signed_url_token_redacted": True,
        "raw_provider_url_exposed": False,
    }


def _provider_private_error(exc: ProviderPrivateSignedUrlStateError) -> layer3_workbench.Layer3WorkbenchError:
    http_status = 404 if exc.status == "not_found" else 409 if exc.status in {"blocked", "conflict"} else 400
    return layer3_workbench.Layer3WorkbenchError(
        exc.error_code,
        exc.message,
        status=exc.status,
        http_status=http_status,
        blocked_fields=list(exc.blocked_fields),
        next_allowed_actions=list(exc.next_allowed_actions),
    )


def _fake_provider_error(exc: ProviderPrivateSignedUrlError) -> layer3_workbench.Layer3WorkbenchError:
    return layer3_workbench.Layer3WorkbenchError(
        exc.error_code,
        exc.message,
        status=exc.status,
        http_status=409 if exc.status in {"provider_private_signed_url_blocked", "provider_private_signed_url_conflict"} else 400,
        blocked_fields=list(exc.blocked_fields),
        next_allowed_actions=list(exc.next_allowed_actions),
    )


def _normalise_source_directory_package_provider_private_payload(
    payload: dict[str, Any],
    *,
    required_fields: frozenset[str],
    operator_decision: str,
) -> dict[str, Any]:
    fields = dict(payload)
    unknown = sorted(key for key in fields if key not in SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_ALLOWED_FIELDS)
    forbidden = sorted(key for key in SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_FORBIDDEN_FIELDS if key in fields)
    blocked = sorted(set(unknown) | set(forbidden))
    if blocked:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_scope_not_admitted",
            "Source-directory package supersession provider-private request includes non-admitted fields: "
            + ", ".join(blocked)
            + ".",
            status="blocked",
            http_status=409,
            blocked_fields=blocked,
            next_allowed_actions=["submit_redacted_source_directory_package_provider_private_request"],
        )
    missing = sorted(field for field in required_fields if not _string(fields.get(field)))
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_source_directory_package_supersession_provider_private_fields",
            "Source-directory package supersession provider-private request is missing required fields: "
            + ", ".join(missing)
            + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_source_directory_package_provider_private_request"],
        )
    if _string(fields.get("delivery_mode")) != SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_DELIVERY_MODE:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_delivery_mode_not_admitted",
            "delivery_mode must be provider_private_signed_url.",
            status="blocked",
            http_status=409,
            blocked_fields=["delivery_mode"],
        )
    if _string(fields.get("operator_decision")) != operator_decision:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_decision_not_admitted",
            f"operator_decision must be {operator_decision}.",
            status="blocked",
            http_status=409,
            blocked_fields=["operator_decision"],
        )
    return fields


def _source_directory_package_provider_private_ttl_seconds(fields: dict[str, Any]) -> int:
    raw_value = fields.get(
        "requested_ttl_seconds",
        SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_DEFAULT_TTL_SECONDS,
    )
    try:
        ttl = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_ttl_invalid",
            "requested_ttl_seconds must be an integer.",
            status="invalid",
            blocked_fields=["requested_ttl_seconds"],
        ) from exc
    if ttl <= 0 or ttl > PROVIDER_PRIVATE_SIGNED_URL_MAX_TTL_SECONDS:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_ttl_not_admitted",
            "requested_ttl_seconds must be positive and within the admitted provider-private TTL bound.",
            status="invalid",
            blocked_fields=["requested_ttl_seconds"],
        )
    return ttl


def _source_directory_package_provider_private_authority(
    db: Session,
    fields: dict[str, Any],
) -> tuple[L3PackageSupersessionCommit, dict[str, Any], dict[str, Any]]:
    commit_id = _string(fields.get("package_supersession_commit_id"))
    commit = (
        db.query(L3PackageSupersessionCommit)
        .filter(L3PackageSupersessionCommit.package_supersession_commit_id == commit_id)
        .one_or_none()
    )
    if commit is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_commit_not_found",
            "Source-directory package supersession provider-private lifecycle requires an existing supersession commit.",
            status="not_found",
            http_status=404,
            blocked_fields=["package_supersession_commit_id"],
            next_allowed_actions=["commit_source_directory_package_supersession_first"],
        )
    snapshot = dict(commit.commit_snapshot_json or {})
    if snapshot.get("mode") != SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_MODE:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_commit_mode_not_admitted",
            "Supersession commit was not produced by the source-directory package lifecycle authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["package_supersession_commit_id"],
        )
    for field, expected in (
        ("session_id", commit.session_id),
        ("reconciliation_record_id", commit.reconciliation_record_id),
        ("replacement_package_set_authority_id", commit.replacement_package_set_authority_id),
        ("replacement_authority_basis_hash", commit.replacement_authority_basis_hash),
        ("package_supersession_commit_basis_hash", commit.commit_basis_hash),
    ):
        if _string(fields.get(field)) != _string(expected):
            raise layer3_workbench.Layer3WorkbenchError(
                f"source_directory_package_supersession_provider_private_{field}_mismatch",
                f"Supplied {field} does not match current source-directory supersession authority.",
                status="conflict",
                http_status=409,
                blocked_fields=[field],
                next_allowed_actions=["refresh_source_directory_package_supersession_authority"],
            )
    authority = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(
            L3ReplacementPackageSetAuthority.replacement_package_set_authority_id
            == commit.replacement_package_set_authority_id
        )
        .one_or_none()
    )
    if authority is None or authority.authority_basis_hash != commit.replacement_authority_basis_hash:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_replacement_authority_mismatch",
            "Current replacement package-set authority no longer matches the supersession commit.",
            status="conflict",
            http_status=409,
            blocked_fields=["replacement_package_set_authority_id", "replacement_authority_basis_hash"],
            next_allowed_actions=["refresh_source_directory_replacement_authority"],
        )
    authority_snapshot = dict(authority.authority_snapshot_json or {})
    if (
        authority.session_id != commit.session_id
        or authority.reconciliation_record_id != commit.reconciliation_record_id
        or authority_snapshot.get("mode")
        != layer3_replacement_package_set_authority.SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_replacement_authority_not_current",
            "Replacement package-set authority is not the current source-directory lifecycle authority.",
            status="conflict",
            http_status=409,
            blocked_fields=["replacement_package_set_authority_id", "replacement_authority_basis_hash"],
            next_allowed_actions=["refresh_source_directory_replacement_authority"],
        )
    source_refs = _redacted_commit_source_refs(commit)
    replacement_refs = _redacted_commit_replacement_refs(commit)
    artifact = {
        "schema_id": "layer3.source_directory_package_supersession_provider_private_artifact.v1",
        "mode": SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_MODE,
        "package_supersession_commit_id": commit.package_supersession_commit_id,
        "package_supersession_commit_basis_hash": commit.commit_basis_hash,
        "replacement_package_set_authority_id": commit.replacement_package_set_authority_id,
        "replacement_authority_basis_hash": commit.replacement_authority_basis_hash,
        "source_package_set_hash": commit.source_package_set_hash,
        "replacement_package_set_hash": commit.replacement_package_set_hash,
        "source_package_kinds": list(commit.source_package_kinds_json or []),
        "replacement_package_kinds": list(commit.replacement_package_kinds_json or []),
        "source_payload_refs": source_refs,
        "replacement_payload_refs": replacement_refs,
        "source_payload_hashes": list(commit.source_payload_hashes_json or []),
        "replacement_payload_hashes": list(commit.replacement_payload_hashes_json or []),
        "raw_payload_refs_exposed": False,
        "package_payload_bytes_exposed": False,
        "negative_invariants": {
            "raw_provider_url_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_write_enabled": False,
            "provider_object_copy_enabled": False,
            "provider_object_mutation_enabled": False,
            "public_proxy_enabled": False,
            "connector_dispatch_enabled": False,
            "package_mutation_enabled": False,
            "frontend_durable_authority_enabled": False,
            "source_expansion_enabled": False,
            "rag_vector_runtime_enabled": False,
            "model_runtime_enabled": False,
            "full_mockup_activation_enabled": False,
        },
    }
    artifact_bytes = stable_json_bytes(artifact)
    authority_basis = {
        "session_id": commit.session_id,
        "reconciliation_record_id": commit.reconciliation_record_id,
        "source_artifact_ref": (
            f"artifact://source-directory-package-supersession/{commit.package_supersession_commit_id}"
        ),
        "source_artifact_hash": hashlib.sha256(artifact_bytes).hexdigest(),
        "source_artifact_size_bytes": len(artifact_bytes),
        "external_export_download_record_ref": commit.package_supersession_commit_id,
        "export_download_descriptor_ref": commit.replacement_package_set_authority_id,
    }
    return commit, artifact, authority_basis


def _assert_source_directory_package_provider_private_authority(
    provider_authority: L3ProviderPrivateSignedUrlObjectAuthority,
    authority_basis: dict[str, Any],
) -> None:
    mismatched = [
        field
        for field in (
            "session_id",
            "reconciliation_record_id",
            "external_export_download_record_ref",
            "export_download_descriptor_ref",
            "source_artifact_hash",
            "source_artifact_size_bytes",
        )
        if str(getattr(provider_authority, field)) != str(authority_basis[field])
    ]
    if mismatched:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_authority_mismatch",
            "Current source-directory package supersession authority no longer matches the provider-private receipt.",
            status="conflict",
            http_status=409,
            blocked_fields=mismatched,
            next_allowed_actions=["prepare_new_source_directory_package_provider_private_signed_url"],
        )


def _source_directory_package_provider_private_response(
    *,
    schema_id: str,
    mode: str,
    request_id: str,
    status: str,
    receipt: L3ProviderPrivateSignedUrlReceipt,
    provider_authority: L3ProviderPrivateSignedUrlObjectAuthority,
    audit: L3ProviderPrivateSignedUrlAuditEvent | None,
    commit: L3PackageSupersessionCommit,
    artifact: dict[str, Any],
    effective_now: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expires_at_epoch = int(receipt.provider_private_signed_url_expires_at.timestamp())
    state = _provider_private_receipt_state(receipt, now_epoch=effective_now)
    return {
        **layer3_workbench._base_response(schema_id, request_id=request_id, status=status),  # noqa: SLF001
        "mode": mode,
        "session_id": commit.session_id,
        "reconciliation_record_id": commit.reconciliation_record_id,
        "package_supersession_commit_id": commit.package_supersession_commit_id,
        "package_supersession_commit_basis_hash": commit.commit_basis_hash,
        "replacement_package_set_authority_id": commit.replacement_package_set_authority_id,
        "replacement_authority_basis_hash": commit.replacement_authority_basis_hash,
        "source_package_set_hash": commit.source_package_set_hash,
        "replacement_package_set_hash": commit.replacement_package_set_hash,
        "provider_signed_url_receipt_id": receipt.provider_private_signed_url_receipt_id,
        "provider_private_signed_url_object_authority_id": (
            receipt.provider_private_signed_url_object_authority_id
        ),
        "provider_signed_url_state": state,
        "delivery_mode": SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_DELIVERY_MODE,
        "provider_url_redacted": SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REDACTED_MARKER,
        "provider_url_expires_at": _epoch_iso(expires_at_epoch),
        "provider_url_expires_in_seconds": max(0, expires_at_epoch - effective_now),
        "provider_url_replay_policy": receipt.provider_private_signed_url_replay_policy,
        "provider_url_revocation_supported": True,
        "provider_url_use_count": receipt.provider_private_signed_url_use_count,
        "provider_url_max_use_count": receipt.provider_private_signed_url_max_use_count,
        "provider_url_revoked": receipt.provider_private_signed_url_state == "provider_private_signed_url_revoked",
        "source_artifact_ref": INTERNAL_ARTIFACT_REF_PLACEHOLDER,
        "source_artifact_hash": provider_authority.source_artifact_hash,
        "source_artifact_size_bytes": provider_authority.source_artifact_size_bytes,
        "source_directory_package_supersession_authority": artifact,
        "audit_receipt": _provider_private_audit_receipt(
            receipt=receipt,
            authority=provider_authority,
            audit=audit,
        ),
        "authority_rail": {
            "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
            "artifact_authority": SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_MODE,
            "durable_state_authority": True,
            "provider_url_secret_redacted": True,
            "server_owned_use_authority": True,
            "provider_network_enabled": False,
            "provider_object_write_enabled": False,
            "connector_dispatch_enabled": False,
            "destination_write_enabled": False,
            "public_url_enabled": False,
            "source_directory_package_lifecycle_authority": True,
        },
        "source_directory_package_supersession_provider_private_signed_url_enabled": True,
        "provider_private_signed_url_enabled": True,
        "provider_public_url_prepare_enabled": False,
        "raw_provider_url_exposed": False,
        "raw_provider_private_signed_url_token_exposed": False,
        "raw_local_path_exposed": False,
        "package_payload_bytes_exposed": False,
        "provider_network_enabled": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "destination_write_enabled": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "frontend_durable_authority_enabled": False,
        "next_allowed_actions": ["inspect_provider_private_signed_url_status"],
        "next_state": state,
        **dict(extra or {}),
    }


def source_directory_package_supersession_provider_private_signed_url_prepare(
    db: Session,
    payload: dict[str, Any],
    *,
    fake_provider: ProviderPrivateSignedUrlFakeProvider | None = None,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    fields = _normalise_source_directory_package_provider_private_payload(
        payload,
        required_fields=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_PREPARE_REQUIRED_FIELDS,
        operator_decision=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_PREPARE_OPERATOR_DECISION,
    )
    request_id = _string(fields.get("client_request_id"))
    ttl_seconds = _source_directory_package_provider_private_ttl_seconds(fields)
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    commit, artifact, authority_basis = _source_directory_package_provider_private_authority(db, fields)
    provider = fake_provider or ProviderPrivateSignedUrlFakeProvider()
    try:
        fake_receipt = provider.prepare(
            ProviderPrivateSignedUrlPrepareRequest(
                client_request_id=request_id,
                authority=ProviderArtifactAuthority(
                    source_artifact_ref=authority_basis["source_artifact_ref"],
                    source_artifact_hash=authority_basis["source_artifact_hash"],
                    source_artifact_size_bytes=authority_basis["source_artifact_size_bytes"],
                    external_export_download_record_ref=authority_basis[
                        "external_export_download_record_ref"
                    ],
                    export_download_descriptor_ref=authority_basis["export_download_descriptor_ref"],
                ),
                recipient_scope=_string(fields.get("recipient_scope")),
                requested_ttl_seconds=ttl_seconds,
                now_epoch=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_FIXED_FAKE_PROVIDER_EPOCH,
            )
        )
    except ProviderPrivateSignedUrlError as exc:
        raise _fake_provider_error(exc) from exc
    try:
        durable_state = record_prepared_provider_private_signed_url_receipt(
            db,
            request_id=request_id,
            client_request_id=request_id,
            authority_basis=authority_basis,
            recipient_scope=_string(fields.get("recipient_scope")),
            requested_ttl_seconds=ttl_seconds,
            now_epoch=effective_now,
            provider_private_signed_url_token=fake_receipt.token_for_test,
        )
    except ProviderPrivateSignedUrlStateError as exc:
        raise _provider_private_error(exc) from exc
    receipt = db.get(L3ProviderPrivateSignedUrlReceipt, durable_state.provider_private_signed_url_receipt_id)
    if receipt is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_receipt_missing_after_prepare",
            "Provider-private signed URL durable receipt was not readable after prepare.",
            status="conflict",
            http_status=409,
            blocked_fields=["provider_signed_url_receipt_id"],
        )
    provider_authority = db.get(
        L3ProviderPrivateSignedUrlObjectAuthority,
        receipt.provider_private_signed_url_object_authority_id,
    )
    audit = db.get(
        L3ProviderPrivateSignedUrlAuditEvent,
        durable_state.provider_private_signed_url_audit_event_id,
    )
    if provider_authority is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_authority_missing_after_prepare",
            "Provider-private signed URL durable authority was not readable after prepare.",
            status="conflict",
            http_status=409,
            blocked_fields=["provider_private_signed_url_object_authority_id"],
        )
    return _source_directory_package_provider_private_response(
        schema_id=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_PREPARE_SCHEMA_ID,
        mode=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_PREPARE_MODE,
        request_id=request_id,
        status="prepared",
        receipt=receipt,
        provider_authority=provider_authority,
        audit=audit,
        commit=commit,
        artifact=artifact,
        effective_now=effective_now,
    )


def source_directory_package_supersession_provider_private_signed_url_status(
    db: Session,
    payload: dict[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    fields = _normalise_source_directory_package_provider_private_payload(
        payload,
        required_fields=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_LIFECYCLE_REQUIRED_FIELDS,
        operator_decision=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_STATUS_OPERATOR_DECISION,
    )
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    commit, artifact, authority_basis = _source_directory_package_provider_private_authority(db, fields)
    receipt = db.get(L3ProviderPrivateSignedUrlReceipt, _string(fields.get("provider_signed_url_receipt_id")))
    if receipt is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_receipt_not_found",
            "Provider-private signed URL receipt was not found.",
            status="not_found",
            http_status=404,
            blocked_fields=["provider_signed_url_receipt_id"],
            next_allowed_actions=["prepare_source_directory_package_provider_private_signed_url"],
        )
    provider_authority = db.get(
        L3ProviderPrivateSignedUrlObjectAuthority,
        receipt.provider_private_signed_url_object_authority_id,
    )
    if provider_authority is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_authority_missing",
            "Provider-private signed URL durable authority is missing.",
            status="conflict",
            http_status=409,
            blocked_fields=["provider_signed_url_receipt_id"],
        )
    _assert_source_directory_package_provider_private_authority(provider_authority, authority_basis)
    return _source_directory_package_provider_private_response(
        schema_id=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_STATUS_SCHEMA_ID,
        mode=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_STATUS_MODE,
        request_id=_string(fields.get("client_request_id")),
        status="ok",
        receipt=receipt,
        provider_authority=provider_authority,
        audit=_latest_provider_private_audit(
            db,
            receipt_id=receipt.provider_private_signed_url_receipt_id,
        ),
        commit=commit,
        artifact=artifact,
        effective_now=effective_now,
    )


def source_directory_package_supersession_provider_private_signed_url_use(
    db: Session,
    payload: dict[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    fields = _normalise_source_directory_package_provider_private_payload(
        payload,
        required_fields=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_LIFECYCLE_REQUIRED_FIELDS,
        operator_decision=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_USE_OPERATOR_DECISION,
    )
    request_id = _string(fields.get("client_request_id"))
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    commit, artifact, authority_basis = _source_directory_package_provider_private_authority(db, fields)
    try:
        durable_state = record_server_owned_provider_private_signed_url_receipt_use(
            db,
            provider_private_signed_url_receipt_id=_string(fields.get("provider_signed_url_receipt_id")),
            authority_basis=authority_basis,
            now_epoch=effective_now,
            request_id=request_id,
        )
    except ProviderPrivateSignedUrlStateError as exc:
        raise _provider_private_error(exc) from exc
    receipt = db.get(L3ProviderPrivateSignedUrlReceipt, durable_state.provider_private_signed_url_receipt_id)
    provider_authority = (
        db.get(L3ProviderPrivateSignedUrlObjectAuthority, receipt.provider_private_signed_url_object_authority_id)
        if receipt is not None else None
    )
    audit = db.get(
        L3ProviderPrivateSignedUrlAuditEvent,
        durable_state.provider_private_signed_url_audit_event_id,
    )
    if receipt is None or provider_authority is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_state_missing_after_use",
            "Provider-private signed URL durable state was not readable after use.",
            status="conflict",
            http_status=409,
            blocked_fields=["provider_signed_url_receipt_id"],
        )
    return _source_directory_package_provider_private_response(
        schema_id=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_USE_SCHEMA_ID,
        mode=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_USE_MODE,
        request_id=request_id,
        status="used",
        receipt=receipt,
        provider_authority=provider_authority,
        audit=audit,
        commit=commit,
        artifact=artifact,
        effective_now=effective_now,
        extra={
            "delivery_use_decision": "allowed",
            "delivery_use_mode": "server_owned_redacted_provider_private_use",
        },
    )


def source_directory_package_supersession_provider_private_signed_url_revoke(
    db: Session,
    payload: dict[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    fields = _normalise_source_directory_package_provider_private_payload(
        payload,
        required_fields=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REVOKE_REQUIRED_FIELDS,
        operator_decision=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REVOKE_OPERATOR_DECISION,
    )
    request_id = _string(fields.get("client_request_id"))
    effective_now = int(time.time() if now_epoch is None else now_epoch)
    commit, artifact, authority_basis = _source_directory_package_provider_private_authority(db, fields)
    try:
        durable_state = revoke_provider_private_signed_url_receipt(
            db,
            provider_private_signed_url_receipt_id=_string(fields.get("provider_signed_url_receipt_id")),
            idempotency_key=_string(fields.get("idempotency_key")),
            revoked_by=_string(fields.get("revoked_by")),
            revocation_reason=_string(fields.get("revocation_reason")),
            now_epoch=effective_now,
            authority_basis=authority_basis,
            request_id=request_id,
        )
    except ProviderPrivateSignedUrlStateError as exc:
        raise _provider_private_error(exc) from exc
    receipt = db.get(L3ProviderPrivateSignedUrlReceipt, durable_state.provider_private_signed_url_receipt_id)
    provider_authority = (
        db.get(L3ProviderPrivateSignedUrlObjectAuthority, receipt.provider_private_signed_url_object_authority_id)
        if receipt is not None else None
    )
    audit = db.get(
        L3ProviderPrivateSignedUrlAuditEvent,
        durable_state.provider_private_signed_url_audit_event_id,
    )
    if receipt is None or provider_authority is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_provider_private_state_missing_after_revoke",
            "Provider-private signed URL durable state was not readable after revoke.",
            status="conflict",
            http_status=409,
            blocked_fields=["provider_signed_url_receipt_id"],
        )
    return _source_directory_package_provider_private_response(
        schema_id=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REVOKE_SCHEMA_ID,
        mode=SOURCE_DIRECTORY_PACKAGE_PROVIDER_PRIVATE_REVOKE_MODE,
        request_id=request_id,
        status="revoked",
        receipt=receipt,
        provider_authority=provider_authority,
        audit=audit,
        commit=commit,
        artifact=artifact,
        effective_now=effective_now,
        extra={
            "revocation_recorded": True,
            "revocation_idempotency_key": _string(fields.get("idempotency_key")),
        },
    )


def _validate_source_directory_replacement_authority(
    *,
    payload: dict[str, Any],
    authority: L3ReplacementPackageSetAuthority,
    lifecycle: dict[str, Any],
) -> tuple[str, str, list[str], list[str], list[str], str]:
    session_id = lifecycle["session"].session_id
    analysis_plan_id = str(lifecycle["analysis_plan_id"])
    pass_run_id = str(lifecycle["pass_run_id"])
    reconciliation_record_id = lifecycle["reconciliation"].reconciliation_record_id
    source_package_set_hash = str(lifecycle["source_package_set_hash"])
    source_output_package_ids = list(lifecycle["source_output_package_ids"])
    source_package_kinds = list(lifecycle["source_package_kinds"])
    source_payload_refs = list(lifecycle["source_payload_refs"])
    source_payload_hashes = list(lifecycle["source_payload_hashes"])

    snapshot = dict(authority.authority_snapshot_json or {})
    if snapshot.get("mode") != layer3_replacement_package_set_authority.SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE:
        _raise_mismatch(
            "source_directory_package_supersession_commit_replacement_authority_mode_mismatch",
            "replacement_package_set_authority_id",
            "Replacement package-set authority was not produced from source-directory package lifecycle authority.",
        )
    if snapshot.get("source_gate") != SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_SOURCE_GATE:
        _raise_mismatch(
            "source_directory_package_supersession_commit_replacement_authority_gate_mismatch",
            "replacement_package_set_authority_id",
            "Replacement package-set authority source gate does not match source-directory package lifecycle authority.",
        )
    for field, expected in (
        ("session_id", session_id),
        ("analysis_plan_id", analysis_plan_id),
        ("pass_run_id", pass_run_id),
        ("reconciliation_record_id", reconciliation_record_id),
    ):
        if _string(getattr(authority, field)) != expected:
            _raise_mismatch(
                f"source_directory_package_supersession_commit_replacement_authority_{field}_mismatch",
                "replacement_package_set_authority_id",
                f"Replacement package-set authority {field} does not match source-directory lifecycle authority.",
            )
    if authority.source_package_set_hash != source_package_set_hash:
        _raise_mismatch(
            "source_directory_package_supersession_commit_replacement_authority_source_hash_mismatch",
            "source_package_set_hash",
            "Replacement authority source package-set hash does not match source-directory lifecycle authority.",
        )
    for field, expected_values in (
        ("source_output_package_ids", source_output_package_ids),
        ("source_package_kinds", source_package_kinds),
        ("source_payload_refs", source_payload_refs),
        ("source_payload_hashes", source_payload_hashes),
    ):
        authority_values = list(getattr(authority, f"{field}_json") or [])
        if authority_values != expected_values:
            _raise_mismatch(
                f"source_directory_package_supersession_commit_replacement_authority_{field}_mismatch",
                "replacement_package_set_authority_id",
                f"Replacement authority {field} do not match source-directory lifecycle authority.",
            )
    if _string(payload.get("replacement_authority_basis_hash")) != authority.authority_basis_hash:
        _raise_mismatch(
            "source_directory_package_supersession_commit_replacement_authority_basis_hash_mismatch",
            "replacement_authority_basis_hash",
            "Supplied replacement_authority_basis_hash does not match source-directory replacement authority.",
        )
    return (
        authority.replacement_package_set_id,
        authority.replacement_package_set_hash,
        list(authority.replacement_package_kinds_json or []),
        list(authority.replacement_payload_refs_json or []),
        list(authority.replacement_payload_hashes_json or []),
        authority.authority_basis_hash,
    )


def _validate_replacement_authority(
    *,
    payload: dict[str, Any],
    authority: L3ReplacementPackageSetAuthority,
    session_id: str,
    analysis_plan_id: str,
    pass_run_id: str,
    reconciliation_record_id: str,
    source_package_set_hash: str,
    source_output_package_ids: list[str],
    source_package_kinds: list[str],
    source_payload_refs: list[str],
    source_payload_hashes: list[str],
) -> tuple[str, str, list[str], list[str], list[str], str]:
    if (
        authority.session_id != session_id
        or authority.analysis_plan_id != analysis_plan_id
        or authority.pass_run_id != pass_run_id
        or authority.reconciliation_record_id != reconciliation_record_id
    ):
        _raise_mismatch(
            "package_supersession_commit_replacement_authority_scope_mismatch",
            "replacement_package_set_authority_id",
            "replacement_package_set_authority_id does not belong to the supplied package authority rail.",
        )
    if authority.source_package_set_hash != source_package_set_hash:
        _raise_mismatch(
            "package_supersession_commit_replacement_authority_source_hash_mismatch",
            "source_package_set_hash",
            "Replacement authority source package-set hash does not match current source authority.",
        )
    for field, expected_values in (
        ("source_output_package_ids", source_output_package_ids),
        ("source_package_kinds", source_package_kinds),
        ("source_payload_refs", source_payload_refs),
        ("source_payload_hashes", source_payload_hashes),
    ):
        authority_values = list(getattr(authority, f"{field}_json") or [])
        if authority_values != expected_values:
            _raise_mismatch(
                f"package_supersession_commit_replacement_authority_{field}_mismatch",
                field,
                f"Replacement authority {field} do not match current source authority.",
            )

    replacement_package_set_id = authority.replacement_package_set_id
    replacement_package_set_hash = authority.replacement_package_set_hash
    replacement_package_kinds = list(authority.replacement_package_kinds_json or [])
    replacement_payload_refs = list(authority.replacement_payload_refs_json or [])
    replacement_payload_hashes = list(authority.replacement_payload_hashes_json or [])
    replacement_authority_basis_hash = authority.authority_basis_hash

    if _string(payload.get("replacement_authority_basis_hash")) != replacement_authority_basis_hash:
        _raise_mismatch(
            "package_supersession_commit_replacement_authority_basis_hash_mismatch",
            "replacement_authority_basis_hash",
            "Supplied replacement_authority_basis_hash does not match durable replacement authority.",
        )
    if _string(payload.get("replacement_package_set_id")) != replacement_package_set_id:
        _raise_mismatch(
            "package_supersession_commit_replacement_package_set_id_mismatch",
            "replacement_package_set_id",
            "Supplied replacement_package_set_id does not match durable replacement authority.",
        )
    if _string(payload.get("replacement_package_set_hash")) != replacement_package_set_hash:
        _raise_mismatch(
            "package_supersession_commit_replacement_package_set_hash_mismatch",
            "replacement_package_set_hash",
            "Supplied replacement_package_set_hash does not match durable replacement authority.",
        )
    for field, expected_values in (
        ("replacement_package_kinds", replacement_package_kinds),
        ("replacement_payload_refs", replacement_payload_refs),
        ("replacement_payload_hashes", replacement_payload_hashes),
    ):
        _validate_supplied_list(payload=payload, field=field, expected_values=expected_values)
    return (
        replacement_package_set_id,
        replacement_package_set_hash,
        replacement_package_kinds,
        replacement_payload_refs,
        replacement_payload_hashes,
        replacement_authority_basis_hash,
    )


def commit_package_supersession(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for package supersession commit.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_complete_package_supersession_commit_request"],
        )

    unknown = sorted(key for key in payload if key not in PACKAGE_SUPERSESSION_COMMIT_ALLOWED_FIELDS)
    forbidden = sorted(key for key in PACKAGE_SUPERSESSION_COMMIT_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_commit_scope_not_admitted",
            "Package supersession commit request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="blocked",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_package_supersession_commit_lineage_only_request"],
        )

    missing = sorted(
        field
        for field in PACKAGE_SUPERSESSION_COMMIT_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_package_supersession_commit_fields",
            "Package supersession commit request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_package_supersession_commit_request"],
        )

    if _string(payload.get("operator_decision")) != PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_package_supersession_commit_decision",
            "operator_decision must be commit_package_supersession.",
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
        .filter(
            L3AnalysisPlan.analysis_plan_id == analysis_plan_id,
            L3AnalysisPlan.session_id == session_id,
        )
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
            "package_supersession_commit_requires_existing_authority",
            "Package supersession commit requires existing session, plan, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "analysis_plan_id", "pass_run_id", "reconciliation_record_id"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_commit_pass_run_mismatch",
            "pass_run_id must belong to the supplied session and analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    commit_summary = dict((reconciliation.summary_json or {}).get("workbench_package_commit") or {})
    if not commit_summary:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_commit_requires_package_construction",
            "Package supersession commit requires existing workbench package-construction provenance.",
            status="blocked",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
            next_allowed_actions=["inspect_existing_package_state"],
        )

    ordered_packages = _ordered_source_packages(
        db,
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    layer3_package_mutation_entry._validate_package_files(ordered_packages)  # noqa: SLF001
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
            "package_supersession_commit_source_package_set_hash_mismatch",
            "source_package_set_hash",
            "Supplied source_package_set_hash does not match current package authority.",
        )

    authority_id = _string(payload.get("replacement_package_set_authority_id"))
    replacement_authority = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.replacement_package_set_authority_id == authority_id)
        .one_or_none()
    )
    if replacement_authority is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_commit_requires_replacement_authority",
            "Package supersession commit requires an existing replacement package-set authority record.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_package_set_authority_id"],
            next_allowed_actions=["record_replacement_package_set_authority"],
        )
    (
        replacement_package_set_id,
        replacement_package_set_hash,
        replacement_package_kinds,
        replacement_payload_refs,
        replacement_payload_hashes,
        replacement_authority_basis_hash,
    ) = _validate_replacement_authority(
        payload=payload,
        authority=replacement_authority,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids=source_output_package_ids,
        source_package_kinds=source_package_kinds,
        source_payload_refs=source_payload_refs,
        source_payload_hashes=source_payload_hashes,
    )

    downstream_dependencies = _current_downstream_dependencies(reconciliation)
    computed_downstream_hash = package_supersession_downstream_dependency_hash(downstream_dependencies)
    if _string(payload.get("downstream_dependency_hash")) != computed_downstream_hash:
        _raise_mismatch(
            "package_supersession_commit_downstream_dependency_hash_mismatch",
            "downstream_dependency_hash",
            "Supplied downstream_dependency_hash does not match current downstream dependency authority.",
        )

    preview_basis = {
        "schema_id": "layer3.package_supersession_preview_basis.v1",
        "mode": layer3_package_mutation_entry.PACKAGE_SUPERSESSION_PREVIEW_MODE,
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "reconciliation_record_id": reconciliation_record_id,
        "package_review_preview_hash": _string(commit_summary.get("package_review_preview_hash")),
        "package_set_hash": source_package_set_hash,
        "downstream_dependencies": downstream_dependencies,
    }
    computed_preview_hash = stable_hash(preview_basis)
    if _string(payload.get("package_supersession_preview_hash")) != computed_preview_hash:
        _raise_mismatch(
            "package_supersession_commit_preview_hash_mismatch",
            "package_supersession_preview_hash",
            "Supplied package_supersession_preview_hash does not match current package preview authority.",
        )

    computed_basis_hash = package_supersession_commit_basis_hash(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        package_supersession_preview_hash=computed_preview_hash,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids=source_output_package_ids,
        source_package_kinds=source_package_kinds,
        source_payload_refs=source_payload_refs,
        source_payload_hashes=source_payload_hashes,
        replacement_package_set_authority_id=authority_id,
        replacement_authority_basis_hash=replacement_authority_basis_hash,
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=replacement_package_set_hash,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
        downstream_dependency_hash=computed_downstream_hash,
    )
    if _string(payload.get("commit_basis_hash")) != computed_basis_hash:
        _raise_mismatch(
            "package_supersession_commit_basis_hash_mismatch",
            "commit_basis_hash",
            "Supplied commit_basis_hash does not match package supersession commit authority.",
        )

    existing_for_request = (
        db.query(L3PackageSupersessionCommit)
        .filter(L3PackageSupersessionCommit.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        if existing_for_request.commit_basis_hash != computed_basis_hash:
            _raise_mismatch(
                "package_supersession_commit_client_request_conflict",
                "client_request_id",
                "client_request_id already recorded a different package supersession commit.",
            )
        return _commit_response(request_id=request_id, status="already_committed", commit=existing_for_request)

    existing_for_basis = (
        db.query(L3PackageSupersessionCommit)
        .filter(L3PackageSupersessionCommit.commit_basis_hash == computed_basis_hash)
        .one_or_none()
    )
    if existing_for_basis is not None:
        return _commit_response(request_id=request_id, status="already_committed", commit=existing_for_basis)

    now = utcnow()
    snapshot = {
        "schema_id": "layer3.package_supersession_commit_snapshot.v1",
        "mode": PACKAGE_SUPERSESSION_COMMIT_MODE,
        "source_gate": PACKAGE_SUPERSESSION_COMMIT_SOURCE_GATE,
        "source": {
            "package_set_hash": source_package_set_hash,
            "output_package_ids": source_output_package_ids,
            "package_kinds": source_package_kinds,
            "payload_refs": source_payload_refs,
            "payload_hashes": source_payload_hashes,
        },
        "replacement": {
            "replacement_package_set_authority_id": authority_id,
            "replacement_package_set_id": replacement_package_set_id,
            "replacement_package_set_hash": replacement_package_set_hash,
            "package_kinds": replacement_package_kinds,
            "payload_refs": replacement_payload_refs,
            "payload_hashes": replacement_payload_hashes,
            "replacement_authority_basis_hash": replacement_authority_basis_hash,
        },
        "preview": {
            "package_supersession_preview_hash": computed_preview_hash,
            "downstream_dependency_hash": computed_downstream_hash,
            "downstream_dependencies": downstream_dependencies,
        },
        "negative_invariants": {
            "updates_l3_output_package": False,
            "writes_package_payload": False,
            "enables_broad_package_mutation": False,
            "enables_connector_dispatch": False,
            "enables_source_widening": False,
            "enables_qualitative_hybrid_rag": False,
            "enables_provider_public_url": False,
            "enables_full_mockup_activation": False,
        },
    }
    commit = L3PackageSupersessionCommit(
        client_request_id=request_id,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        replacement_package_set_authority_id=authority_id,
        package_supersession_preview_hash=computed_preview_hash,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids_json=source_output_package_ids,
        source_package_kinds_json=source_package_kinds,
        source_payload_refs_json=source_payload_refs,
        source_payload_hashes_json=source_payload_hashes,
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=replacement_package_set_hash,
        replacement_package_kinds_json=replacement_package_kinds,
        replacement_payload_refs_json=replacement_payload_refs,
        replacement_payload_hashes_json=replacement_payload_hashes,
        downstream_dependency_hash=computed_downstream_hash,
        replacement_authority_basis_hash=replacement_authority_basis_hash,
        commit_basis_hash=computed_basis_hash,
        commit_snapshot_json=snapshot,
        operator_decision=PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION,
        status=PACKAGE_SUPERSESSION_COMMIT_STATUS,
        created_at=now,
        updated_at=now,
    )
    db.add(commit)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = (
            db.query(L3PackageSupersessionCommit)
            .filter(L3PackageSupersessionCommit.commit_basis_hash == computed_basis_hash)
            .one_or_none()
        )
        if existing is not None and existing.commit_basis_hash == computed_basis_hash:
            return _commit_response(request_id=request_id, status="already_committed", commit=existing)
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_commit_in_progress",
            "Package supersession commit is already being recorded for this request.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "commit_basis_hash"],
            recoverable=True,
            next_allowed_actions=["retry_package_supersession_commit_request"],
        ) from exc
    return _commit_response(request_id=request_id, status="committed", commit=commit)


def commit_package_supersession_from_source_directory_lifecycle(
    db: Session,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for source-directory package supersession commit.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_complete_source_directory_package_supersession_commit_request"],
        )

    unknown = sorted(key for key in payload if key not in SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_ALLOWED_FIELDS)
    forbidden = sorted(key for key in SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_commit_scope_not_admitted",
            "Source-directory package supersession commit request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="blocked",
            http_status=409,
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_source_directory_package_supersession_commit_authority_only_request"],
        )

    missing = sorted(
        field
        for field in SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_source_directory_package_supersession_commit_fields",
            "Source-directory package supersession commit request is missing required fields: "
            + ", ".join(missing)
            + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_source_directory_package_supersession_commit_request"],
        )

    if _string(payload.get("operator_decision")) != PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_source_directory_package_supersession_commit_decision",
            "operator_decision must be commit_package_supersession.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )

    lifecycle = layer3_replacement_package_set_authority.source_directory_package_lifecycle_context(db, payload)
    session_id = lifecycle["session"].session_id
    analysis_plan_id = str(lifecycle["analysis_plan_id"])
    pass_run_id = str(lifecycle["pass_run_id"])
    reconciliation_record_id = lifecycle["reconciliation"].reconciliation_record_id
    source_package_set_hash = str(lifecycle["source_package_set_hash"])
    source_output_package_ids = list(lifecycle["source_output_package_ids"])
    source_package_kinds = list(lifecycle["source_package_kinds"])
    source_payload_refs = list(lifecycle["source_payload_refs"])
    source_payload_hashes = list(lifecycle["source_payload_hashes"])
    package_supersession_preview_hash = str(lifecycle["package_supersession_preview_hash"])
    downstream_dependency_hash = str(lifecycle["downstream_dependency_hash"])

    authority_id = _string(payload.get("replacement_package_set_authority_id"))
    replacement_authority = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.replacement_package_set_authority_id == authority_id)
        .one_or_none()
    )
    if replacement_authority is None:
        _source_directory_commit_error(
            "source_directory_package_supersession_commit_requires_replacement_authority",
            "Source-directory package supersession commit requires replacement package-set authority.",
            blocked_fields=["replacement_package_set_authority_id"],
        )
    assert replacement_authority is not None
    (
        replacement_package_set_id,
        replacement_package_set_hash,
        replacement_package_kinds,
        replacement_payload_refs,
        replacement_payload_hashes,
        replacement_authority_basis_hash,
    ) = _validate_source_directory_replacement_authority(
        payload=payload,
        authority=replacement_authority,
        lifecycle=lifecycle,
    )

    computed_basis_hash = package_supersession_commit_basis_hash(
        mode=SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_MODE,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        package_supersession_preview_hash=package_supersession_preview_hash,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids=source_output_package_ids,
        source_package_kinds=source_package_kinds,
        source_payload_refs=source_payload_refs,
        source_payload_hashes=source_payload_hashes,
        replacement_package_set_authority_id=authority_id,
        replacement_authority_basis_hash=replacement_authority_basis_hash,
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=replacement_package_set_hash,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
        downstream_dependency_hash=downstream_dependency_hash,
    )

    existing_for_request = (
        db.query(L3PackageSupersessionCommit)
        .filter(L3PackageSupersessionCommit.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        if existing_for_request.commit_basis_hash != computed_basis_hash:
            _raise_mismatch(
                "source_directory_package_supersession_commit_client_request_conflict",
                "client_request_id",
                "client_request_id already recorded a different source-directory package supersession commit.",
            )
        return _commit_response_from_source_directory_lifecycle(
            request_id=request_id,
            status="already_committed",
            commit=existing_for_request,
        )

    existing_for_basis = (
        db.query(L3PackageSupersessionCommit)
        .filter(L3PackageSupersessionCommit.commit_basis_hash == computed_basis_hash)
        .one_or_none()
    )
    if existing_for_basis is not None:
        return _commit_response_from_source_directory_lifecycle(
            request_id=request_id,
            status="already_committed",
            commit=existing_for_basis,
        )

    now = utcnow()
    snapshot = {
        "schema_id": "layer3.source_directory_package_supersession_commit_snapshot.v1",
        "mode": SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_MODE,
        "source_gate": SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_SOURCE_GATE,
        "source_directory_package_lifecycle": {
            "package_supersession_preview_hash": package_supersession_preview_hash,
            "source_package_set_hash": source_package_set_hash,
            "downstream_dependency_hash": downstream_dependency_hash,
            "downstream_dependencies": list(lifecycle["downstream_dependencies"]),
            "material_snapshot_id": lifecycle["material_snapshot_id"],
            "qualitative_analysis_hash": lifecycle["qualitative_analysis_hash"],
            "package_review_preview_hash": lifecycle["package_review_preview_hash"],
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
            "replacement_package_set_authority_id": authority_id,
            "replacement_package_set_id": replacement_package_set_id,
            "replacement_package_set_hash": replacement_package_set_hash,
            "package_kinds": replacement_package_kinds,
            "payload_refs": replacement_payload_refs,
            "payload_hashes": replacement_payload_hashes,
            "replacement_authority_basis_hash": replacement_authority_basis_hash,
            "raw_payload_refs_exposed": False,
        },
        "negative_invariants": {
            "updates_l3_output_package": False,
            "writes_package_payload": False,
            "enables_broad_package_mutation": False,
            "enables_connector_dispatch": False,
            "enables_source_widening": False,
            "enables_qualitative_hybrid_rag": False,
            "enables_provider_public_url": False,
            "enables_full_mockup_activation": False,
        },
    }
    commit = L3PackageSupersessionCommit(
        client_request_id=request_id,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        replacement_package_set_authority_id=authority_id,
        package_supersession_preview_hash=package_supersession_preview_hash,
        source_package_set_hash=source_package_set_hash,
        source_output_package_ids_json=source_output_package_ids,
        source_package_kinds_json=source_package_kinds,
        source_payload_refs_json=source_payload_refs,
        source_payload_hashes_json=source_payload_hashes,
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_set_hash=replacement_package_set_hash,
        replacement_package_kinds_json=replacement_package_kinds,
        replacement_payload_refs_json=replacement_payload_refs,
        replacement_payload_hashes_json=replacement_payload_hashes,
        downstream_dependency_hash=downstream_dependency_hash,
        replacement_authority_basis_hash=replacement_authority_basis_hash,
        commit_basis_hash=computed_basis_hash,
        commit_snapshot_json=snapshot,
        operator_decision=PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION,
        status=PACKAGE_SUPERSESSION_COMMIT_STATUS,
        created_at=now,
        updated_at=now,
    )
    db.add(commit)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = (
            db.query(L3PackageSupersessionCommit)
            .filter(L3PackageSupersessionCommit.commit_basis_hash == computed_basis_hash)
            .one_or_none()
        )
        if existing is not None and existing.commit_basis_hash == computed_basis_hash:
            return _commit_response_from_source_directory_lifecycle(
                request_id=request_id,
                status="already_committed",
                commit=existing,
            )
        raise layer3_workbench.Layer3WorkbenchError(
            "source_directory_package_supersession_commit_in_progress",
            "Source-directory package supersession commit is already being recorded for this request.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "commit_basis_hash"],
            recoverable=True,
            next_allowed_actions=["retry_source_directory_package_supersession_commit_request"],
        ) from exc
    db.refresh(commit)
    return _commit_response_from_source_directory_lifecycle(
        request_id=request_id,
        status="committed",
        commit=commit,
    )


def commit_package_supersession_from_corrected_artifact_set_authority(
    db: Session,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for corrected-artifact package supersession commit.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_complete_corrected_artifact_package_supersession_commit_request"],
        )

    unknown = sorted(
        key for key in payload if key not in PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_ALLOWED_FIELDS
    )
    forbidden = sorted(
        key for key in PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_FORBIDDEN_FIELDS if key in payload
    )
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_commit_from_corrected_artifact_set_scope_not_admitted",
            "Corrected-artifact package supersession commit request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="blocked",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_corrected_artifact_package_supersession_commit_authority_only_request"],
        )

    missing = sorted(
        field
        for field in PACKAGE_SUPERSESSION_COMMIT_FROM_CORRECTED_ARTIFACT_SET_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_package_supersession_commit_from_corrected_artifact_set_fields",
            "Corrected-artifact package supersession commit request is missing required fields: "
            + ", ".join(missing)
            + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_corrected_artifact_package_supersession_commit_request"],
        )

    if _string(payload.get("operator_decision")) != PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_package_supersession_commit_from_corrected_artifact_set_decision",
            "operator_decision must be commit_package_supersession.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )

    session_id = _string(payload.get("session_id"))
    analysis_plan_id = _string(payload.get("analysis_plan_id"))
    pass_run_id = _string(payload.get("pass_run_id"))
    reconciliation_record_id = _string(payload.get("reconciliation_record_id"))
    corrected_id = _string(payload.get("corrected_package_artifact_set_id"))
    replacement_authority_id = _string(payload.get("replacement_package_set_authority_id"))

    corrected = (
        db.query(L3CorrectedPackageArtifactSet)
        .filter(L3CorrectedPackageArtifactSet.corrected_package_artifact_set_id == corrected_id)
        .one_or_none()
    )
    if corrected is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_commit_corrected_artifact_set_not_found",
            "Corrected package artifact set authority was not found.",
            status="blocked",
            http_status=409,
            blocked_fields=["corrected_package_artifact_set_id"],
            next_allowed_actions=["record_corrected_package_artifact_set"],
        )
    for field, expected in (
        ("session_id", session_id),
        ("analysis_plan_id", analysis_plan_id),
        ("pass_run_id", pass_run_id),
        ("reconciliation_record_id", reconciliation_record_id),
    ):
        if _string(getattr(corrected, field)) != expected:
            _raise_mismatch(
                f"package_supersession_commit_corrected_artifact_set_{field}_mismatch",
                field,
                f"Corrected artifact set {field} does not match supplied package authority.",
            )
    if _string(payload.get("corrected_artifact_basis_hash")) != corrected.corrected_artifact_basis_hash:
        _raise_mismatch(
            "package_supersession_commit_corrected_artifact_basis_hash_mismatch",
            "corrected_artifact_basis_hash",
            "Supplied corrected_artifact_basis_hash does not match corrected artifact authority.",
        )

    replacement_authority = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.replacement_package_set_authority_id == replacement_authority_id)
        .one_or_none()
    )
    if replacement_authority is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_commit_corrected_replacement_authority_not_found",
            "Corrected-artifact package supersession commit requires replacement package-set authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["replacement_package_set_authority_id"],
            next_allowed_actions=["record_replacement_package_set_authority_from_corrected_artifact_set"],
        )
    replacement_snapshot = dict(replacement_authority.authority_snapshot_json or {})
    if replacement_snapshot.get("mode") != "replacement_package_set_authority_from_corrected_artifact_set":
        _raise_mismatch(
            "package_supersession_commit_corrected_replacement_authority_mode_mismatch",
            "replacement_package_set_authority_id",
            "Replacement package-set authority was not produced from corrected artifact set authority.",
        )
    if _string(payload.get("replacement_authority_basis_hash")) != replacement_authority.authority_basis_hash:
        _raise_mismatch(
            "package_supersession_commit_corrected_replacement_authority_basis_hash_mismatch",
            "replacement_authority_basis_hash",
            "Supplied replacement_authority_basis_hash does not match corrected-artifact replacement authority.",
        )
    if (
        replacement_authority.session_id != session_id
        or replacement_authority.analysis_plan_id != analysis_plan_id
        or replacement_authority.pass_run_id != pass_run_id
        or replacement_authority.reconciliation_record_id != reconciliation_record_id
    ):
        _raise_mismatch(
            "package_supersession_commit_corrected_replacement_authority_scope_mismatch",
            "replacement_package_set_authority_id",
            "Replacement package-set authority does not belong to the supplied corrected artifact authority rail.",
        )
    if (
        replacement_authority.source_package_set_hash != corrected.source_package_set_hash
        or list(replacement_authority.source_output_package_ids_json or [])
        != list(corrected.source_output_package_ids_json or [])
        or list(replacement_authority.source_package_kinds_json or []) != list(corrected.source_package_kinds_json or [])
        or list(replacement_authority.source_payload_refs_json or []) != list(corrected.source_payload_refs_json or [])
        or list(replacement_authority.source_payload_hashes_json or [])
        != list(corrected.source_payload_hashes_json or [])
        or replacement_authority.replacement_package_set_id != corrected.corrected_package_set_id
        or replacement_authority.replacement_package_set_hash != corrected.corrected_package_set_hash
        or list(replacement_authority.replacement_package_kinds_json or [])
        != list(corrected.corrected_package_kinds_json or [])
        or list(replacement_authority.replacement_payload_refs_json or [])
        != list(corrected.corrected_artifact_refs_json or [])
        or list(replacement_authority.replacement_payload_hashes_json or [])
        != list(corrected.corrected_artifact_hashes_json or [])
    ):
        _raise_mismatch(
            "package_supersession_commit_corrected_replacement_authority_basis_mismatch",
            "replacement_package_set_authority_id",
            "Replacement package-set authority does not match corrected artifact set authority.",
        )

    reconciliation = (
        db.query(L3ReconciliationRecord)
        .filter(
            L3ReconciliationRecord.reconciliation_record_id == reconciliation_record_id,
            L3ReconciliationRecord.session_id == session_id,
        )
        .one_or_none()
    )
    if reconciliation is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_commit_requires_existing_authority",
            "Corrected-artifact package supersession commit requires reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    commit_summary = dict((reconciliation.summary_json or {}).get("workbench_package_commit") or {})
    downstream_dependencies = _current_downstream_dependencies(reconciliation)
    downstream_dependency_hash = package_supersession_downstream_dependency_hash(downstream_dependencies)
    preview_hash = stable_hash(
        {
            "schema_id": "layer3.package_supersession_preview_basis.v1",
            "mode": layer3_package_mutation_entry.PACKAGE_SUPERSESSION_PREVIEW_MODE,
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "reconciliation_record_id": reconciliation_record_id,
            "package_review_preview_hash": _string(commit_summary.get("package_review_preview_hash")),
            "package_set_hash": corrected.source_package_set_hash,
            "downstream_dependencies": downstream_dependencies,
        }
    )
    full_payload = {
        "client_request_id": request_id,
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "reconciliation_record_id": reconciliation_record_id,
        "package_supersession_preview_hash": preview_hash,
        "source_package_set_hash": corrected.source_package_set_hash,
        "source_output_package_ids": list(corrected.source_output_package_ids_json or []),
        "source_package_kinds": list(corrected.source_package_kinds_json or []),
        "source_payload_refs": list(corrected.source_payload_refs_json or []),
        "source_payload_hashes": list(corrected.source_payload_hashes_json or []),
        "replacement_package_set_authority_id": replacement_authority_id,
        "replacement_package_set_id": replacement_authority.replacement_package_set_id,
        "replacement_package_set_hash": replacement_authority.replacement_package_set_hash,
        "replacement_package_kinds": list(replacement_authority.replacement_package_kinds_json or []),
        "replacement_payload_refs": list(replacement_authority.replacement_payload_refs_json or []),
        "replacement_payload_hashes": list(replacement_authority.replacement_payload_hashes_json or []),
        "replacement_authority_basis_hash": replacement_authority.authority_basis_hash,
        "downstream_dependency_hash": downstream_dependency_hash,
        "operator_decision": PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION,
    }
    full_payload["commit_basis_hash"] = package_supersession_commit_basis_hash(
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
        package_supersession_preview_hash=preview_hash,
        source_package_set_hash=full_payload["source_package_set_hash"],
        source_output_package_ids=full_payload["source_output_package_ids"],
        source_package_kinds=full_payload["source_package_kinds"],
        source_payload_refs=full_payload["source_payload_refs"],
        source_payload_hashes=full_payload["source_payload_hashes"],
        replacement_package_set_authority_id=replacement_authority_id,
        replacement_authority_basis_hash=replacement_authority.authority_basis_hash,
        replacement_package_set_id=replacement_authority.replacement_package_set_id,
        replacement_package_set_hash=replacement_authority.replacement_package_set_hash,
        replacement_package_kinds=full_payload["replacement_package_kinds"],
        replacement_payload_refs=full_payload["replacement_payload_refs"],
        replacement_payload_hashes=full_payload["replacement_payload_hashes"],
        downstream_dependency_hash=downstream_dependency_hash,
    )
    response = commit_package_supersession(db, full_payload)
    commit_id = response["package_supersession_commit_id"]
    commit = (
        db.query(L3PackageSupersessionCommit)
        .filter(L3PackageSupersessionCommit.package_supersession_commit_id == commit_id)
        .one()
    )
    return _commit_response_from_corrected_artifact_authority(
        request_id=request_id,
        status=response["status"],
        commit=commit,
        corrected=corrected,
    )
