from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3OutputPackage,
    L3PackageSupersessionCommit,
    L3ReplacementOutputPackage,
    L3ReplacementPackageArtifactManifest,
    L3ReplacementPackageSetAuthority,
    L3Session,
)
from app.services import layer3_workbench
from app.services.layer3_package_entry import PACKAGE_SCHEMA_IDS
from app.services.layer3_utils import json_clone, stable_hash, utcnow


REPLACEMENT_PACKAGE_NAMESPACE_SCHEMA_ID = "layer3.replacement_package_namespace.v1"
REPLACEMENT_PACKAGE_NAMESPACE_MODE = "replacement_package_namespace_rows"
REPLACEMENT_PACKAGE_NAMESPACE_SOURCE_GATE = "131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE"
REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION = "record_replacement_package_namespace"
REPLACEMENT_PACKAGE_NAMESPACE_STATE = "replacement_package_namespace_recorded"
REPLACEMENT_PACKAGE_NAMESPACE_STATUS = "recorded"

REPLACEMENT_PACKAGE_NAMESPACE_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "replacement_artifact_manifest_id",
        "replacement_package_set_authority_id",
        "package_supersession_commit_id",
        "source_output_package_id",
        "package_kind",
        "package_schema_id",
        "artifact_ref",
        "artifact_hash",
        "authority_basis_hash",
        "operator_decision",
    }
)
REPLACEMENT_PACKAGE_NAMESPACE_FORBIDDEN_FIELDS = frozenset(
    {
        "package_payload",
        "package_payload_bytes",
        "package_variant_content",
        "replacement_package_payloads",
        "replacement_package_payload_bytes",
        "replacement_content",
        "generated_file_bytes",
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
        "source_l3_output_package_write",
        "source_output_package_update",
        "package_row_mutation",
        "package_payload_write",
        "package_payload_rewrite",
        "analysis_artifact",
        "handoff",
        "export",
        "connector_destination",
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
REPLACEMENT_PACKAGE_NAMESPACE_ALLOWED_FIELDS = (
    REPLACEMENT_PACKAGE_NAMESPACE_REQUIRED_FIELDS | REPLACEMENT_PACKAGE_NAMESPACE_FORBIDDEN_FIELDS
)
REPLACEMENT_PACKAGE_NAMESPACE_DOWNSTREAM_UNAVAILABLE = (
    "package_mutation_reconstruction",
    "package_payload_rewrite",
    "package_payload_generation",
    "source_l3_output_package_mutation",
    "replacement_package_artifact_generation",
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
        next_allowed_actions=["refresh_replacement_package_namespace_authority"],
    )


def _kind_index(values: list[str], package_kind: str, *, error_code: str, field: str) -> int:
    try:
        return values.index(package_kind)
    except ValueError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            error_code,
            "package_kind must exist in the durable replacement package authority chain.",
            status="blocked",
            http_status=409,
            blocked_fields=[field],
            next_allowed_actions=["refresh_replacement_package_namespace_authority"],
        ) from exc


def replacement_package_namespace_authority_basis_hash(
    *,
    session_id: str,
    source_output_package_id: str,
    source_package_kind: str,
    source_package_schema_id: str,
    source_payload_ref: str,
    source_payload_hash: str,
    replacement_artifact_manifest_id: str,
    replacement_artifact_manifest_authority_basis_hash: str,
    replacement_artifact_ref: str,
    replacement_artifact_hash: str,
    replacement_package_set_authority_id: str,
    replacement_package_set_authority_basis_hash: str,
    package_supersession_commit_id: str,
    package_supersession_commit_basis_hash: str,
    package_kind: str,
    package_schema_id: str,
    operator_decision: str,
    client_request_id: str,
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.replacement_package_namespace_authority.v1",
            "mode": REPLACEMENT_PACKAGE_NAMESPACE_MODE,
            "session_id": session_id,
            "source": {
                "output_package_id": source_output_package_id,
                "package_kind": source_package_kind,
                "package_schema_id": source_package_schema_id,
                "payload_ref": source_payload_ref,
                "payload_hash": source_payload_hash,
            },
            "replacement_artifact_manifest": {
                "replacement_artifact_manifest_id": replacement_artifact_manifest_id,
                "authority_basis_hash": replacement_artifact_manifest_authority_basis_hash,
                "artifact_ref": replacement_artifact_ref,
                "artifact_hash": replacement_artifact_hash,
            },
            "replacement_package_set_authority": {
                "replacement_package_set_authority_id": replacement_package_set_authority_id,
                "authority_basis_hash": replacement_package_set_authority_basis_hash,
            },
            "package_supersession_commit": {
                "package_supersession_commit_id": package_supersession_commit_id,
                "commit_basis_hash": package_supersession_commit_basis_hash,
            },
            "replacement": {
                "package_kind": package_kind,
                "package_schema_id": package_schema_id,
            },
            "operator_decision": operator_decision,
            "client_request_id": client_request_id,
        }
    )


def _namespace_response(
    *,
    request_id: str,
    status: str,
    row: L3ReplacementOutputPackage,
) -> dict[str, Any]:
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            REPLACEMENT_PACKAGE_NAMESPACE_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "replacement_output_package_id": row.replacement_output_package_id,
        "session_id": row.session_id,
        "source_output_package_id": row.source_output_package_id,
        "replacement_artifact_manifest_id": row.replacement_artifact_manifest_id,
        "replacement_package_set_authority_id": row.replacement_package_set_authority_id,
        "package_supersession_commit_id": row.package_supersession_commit_id,
        "package_kind": row.package_kind,
        "package_schema_id": row.package_schema_id,
        "artifact_ref": row.artifact_ref,
        "artifact_hash": row.artifact_hash,
        "authority_basis_hash": row.authority_basis_hash,
        "summary": json_clone(row.summary_json),
        "operator_decision": row.operator_decision,
        "replacement_package_namespace_mode": REPLACEMENT_PACKAGE_NAMESPACE_MODE,
        "source_gate": REPLACEMENT_PACKAGE_NAMESPACE_SOURCE_GATE,
        "namespace_row_persisted": True,
        "package_row_mutation_enabled": False,
        "package_payload_write_enabled": False,
        "l3_output_package_write_enabled": False,
        "broad_package_mutation_enabled": False,
        "source_widening_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "frontend_only_durable_state_enabled": False,
        "downstream_unavailable": list(REPLACEMENT_PACKAGE_NAMESPACE_DOWNSTREAM_UNAVAILABLE),
        "next_state": REPLACEMENT_PACKAGE_NAMESPACE_STATE,
        "authority_rail": {
            "separate_replacement_output_package_table": True,
            "source_l3_output_package_mutated": False,
            "source_l3_output_package_uniqueness_preserved": True,
            "package_payload_written": False,
            "browser_package_bytes_accepted": False,
        },
    }


def _validate_payload(payload: dict[str, Any]) -> str:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for replacement package namespace recording.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_complete_replacement_package_namespace_request"],
        )
    unknown = sorted(key for key in payload if key not in REPLACEMENT_PACKAGE_NAMESPACE_ALLOWED_FIELDS)
    forbidden = sorted(key for key in REPLACEMENT_PACKAGE_NAMESPACE_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_namespace_scope_not_admitted",
            "Replacement package namespace request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="blocked",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_replacement_package_namespace_only_request"],
        )
    missing = sorted(
        field for field in REPLACEMENT_PACKAGE_NAMESPACE_REQUIRED_FIELDS if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_replacement_package_namespace_fields",
            "Replacement package namespace request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_replacement_package_namespace_request"],
        )
    if _string(payload.get("operator_decision")) != REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_replacement_package_namespace_decision",
            "operator_decision must be record_replacement_package_namespace.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    return request_id


def record_replacement_package_namespace(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _validate_payload(payload)
    session_id = _string(payload.get("session_id"))
    source_output_package_id = _string(payload.get("source_output_package_id"))
    manifest_id = _string(payload.get("replacement_artifact_manifest_id"))
    replacement_authority_id = _string(payload.get("replacement_package_set_authority_id"))
    commit_id = _string(payload.get("package_supersession_commit_id"))
    package_kind = _string(payload.get("package_kind"))
    package_schema_id = _string(payload.get("package_schema_id"))
    artifact_ref = _string(payload.get("artifact_ref"))
    artifact_hash = _string(payload.get("artifact_hash"))

    if PACKAGE_SCHEMA_IDS.get(package_kind) != package_schema_id:
        _raise_mismatch(
            "replacement_package_namespace_package_schema_mismatch",
            "package_schema_id",
            "package_schema_id must match the canonical schema for package_kind.",
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).one_or_none()
    source_package = (
        db.query(L3OutputPackage)
        .filter(L3OutputPackage.output_package_id == source_output_package_id, L3OutputPackage.session_id == session_id)
        .one_or_none()
    )
    manifest = (
        db.query(L3ReplacementPackageArtifactManifest)
        .filter(L3ReplacementPackageArtifactManifest.replacement_package_artifact_manifest_id == manifest_id)
        .one_or_none()
    )
    replacement_authority = (
        db.query(L3ReplacementPackageSetAuthority)
        .filter(L3ReplacementPackageSetAuthority.replacement_package_set_authority_id == replacement_authority_id)
        .one_or_none()
    )
    supersession_commit = (
        db.query(L3PackageSupersessionCommit)
        .filter(L3PackageSupersessionCommit.package_supersession_commit_id == commit_id)
        .one_or_none()
    )
    if session is None or source_package is None or manifest is None or replacement_authority is None or supersession_commit is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_namespace_requires_existing_authority",
            "Replacement package namespace recording requires existing session, source package, manifest, replacement authority, and supersession lineage.",
            status="blocked",
            http_status=409,
            blocked_fields=[
                "session_id",
                "source_output_package_id",
                "replacement_artifact_manifest_id",
                "replacement_package_set_authority_id",
                "package_supersession_commit_id",
            ],
            next_allowed_actions=["refresh_replacement_package_namespace_authority"],
        )

    if source_package.package_kind != package_kind:
        _raise_mismatch(
            "replacement_package_namespace_source_package_kind_mismatch",
            "source_output_package_id",
            "source_output_package_id must identify the source package row for package_kind.",
        )

    for field, expected in (("session_id", session_id),):
        if getattr(manifest, field) != expected or getattr(replacement_authority, field) != expected or getattr(supersession_commit, field) != expected:
            _raise_mismatch(
                f"replacement_package_namespace_stale_{field}",
                field,
                "Replacement namespace row must match the same session across all authority records.",
            )
    if manifest.replacement_package_set_authority_id != replacement_authority_id:
        _raise_mismatch(
            "replacement_package_namespace_manifest_authority_mismatch",
            "replacement_artifact_manifest_id",
            "replacement_artifact_manifest_id must belong to the supplied replacement package-set authority.",
        )
    if manifest.package_supersession_commit_id != commit_id:
        _raise_mismatch(
            "replacement_package_namespace_manifest_commit_mismatch",
            "replacement_artifact_manifest_id",
            "replacement_artifact_manifest_id must belong to the supplied package supersession commit.",
        )
    if supersession_commit.replacement_package_set_authority_id != replacement_authority_id:
        _raise_mismatch(
            "replacement_package_namespace_commit_authority_mismatch",
            "package_supersession_commit_id",
            "package_supersession_commit_id must belong to the supplied replacement package-set authority.",
        )

    source_kinds = _string_list(replacement_authority.source_package_kinds_json)
    source_index = _kind_index(
        source_kinds,
        package_kind,
        error_code="replacement_package_namespace_source_kind_missing",
        field="package_kind",
    )
    source_ids = _string_list(replacement_authority.source_output_package_ids_json)
    source_refs = _string_list(replacement_authority.source_payload_refs_json)
    source_hashes = _string_list(replacement_authority.source_payload_hashes_json)
    if source_index >= len(source_ids) or source_index >= len(source_refs) or source_index >= len(source_hashes):
        _raise_mismatch(
            "replacement_package_namespace_source_authority_vector_mismatch",
            "replacement_package_set_authority_id",
            "Replacement authority source vectors are stale or malformed.",
        )
    if source_ids[source_index] != source_output_package_id:
        _raise_mismatch(
            "replacement_package_namespace_source_package_id_mismatch",
            "source_output_package_id",
            "source_output_package_id must match durable replacement authority source ids.",
        )
    if source_refs[source_index] != source_package.payload_ref or source_hashes[source_index] != source_package.payload_hash:
        _raise_mismatch(
            "replacement_package_namespace_source_payload_mismatch",
            "source_output_package_id",
            "Current source package payload authority is stale relative to replacement authority.",
        )

    for field, expected in (
        ("source_output_package_ids_json", source_ids),
        ("source_package_kinds_json", source_kinds),
        ("source_payload_refs_json", source_refs),
        ("source_payload_hashes_json", source_hashes),
    ):
        if _string_list(getattr(supersession_commit, field)) != expected:
            _raise_mismatch(
                f"replacement_package_namespace_commit_{field}_mismatch",
                "package_supersession_commit_id",
                "Package supersession lineage source authority is stale relative to replacement authority.",
            )

    replacement_kinds = _string_list(manifest.replacement_package_kinds_json)
    replacement_index = _kind_index(
        replacement_kinds,
        package_kind,
        error_code="replacement_package_namespace_replacement_kind_missing",
        field="package_kind",
    )
    verified_refs = _string_list(manifest.verified_artifact_refs_json)
    verified_hashes = _string_list(manifest.verified_artifact_hashes_json)
    if replacement_index >= len(verified_refs) or replacement_index >= len(verified_hashes):
        _raise_mismatch(
            "replacement_package_namespace_manifest_vector_mismatch",
            "replacement_artifact_manifest_id",
            "Replacement artifact manifest vectors are stale or malformed.",
        )
    if artifact_ref != verified_refs[replacement_index]:
        _raise_mismatch(
            "replacement_package_namespace_artifact_ref_mismatch",
            "artifact_ref",
            "artifact_ref must match the server-verified manifest artifact for package_kind.",
        )
    if artifact_hash != verified_hashes[replacement_index]:
        _raise_mismatch(
            "replacement_package_namespace_artifact_hash_mismatch",
            "artifact_hash",
            "artifact_hash must match the server-verified manifest hash for package_kind.",
        )
    if artifact_ref == source_package.payload_ref:
        _raise_mismatch(
            "replacement_package_namespace_reuses_source_payload_ref",
            "artifact_ref",
            "replacement namespace rows must not reuse the source package payload ref.",
        )

    computed_basis_hash = replacement_package_namespace_authority_basis_hash(
        session_id=session_id,
        source_output_package_id=source_output_package_id,
        source_package_kind=source_package.package_kind,
        source_package_schema_id=package_schema_id,
        source_payload_ref=source_package.payload_ref,
        source_payload_hash=source_package.payload_hash,
        replacement_artifact_manifest_id=manifest_id,
        replacement_artifact_manifest_authority_basis_hash=manifest.authority_basis_hash,
        replacement_artifact_ref=artifact_ref,
        replacement_artifact_hash=artifact_hash,
        replacement_package_set_authority_id=replacement_authority_id,
        replacement_package_set_authority_basis_hash=replacement_authority.authority_basis_hash,
        package_supersession_commit_id=commit_id,
        package_supersession_commit_basis_hash=supersession_commit.commit_basis_hash,
        package_kind=package_kind,
        package_schema_id=package_schema_id,
        operator_decision=REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION,
        client_request_id=request_id,
    )
    if _string(payload.get("authority_basis_hash")) != computed_basis_hash:
        _raise_mismatch(
            "replacement_package_namespace_authority_basis_hash_mismatch",
            "authority_basis_hash",
            "authority_basis_hash must match the replacement package namespace authority chain.",
        )

    existing_for_request = (
        db.query(L3ReplacementOutputPackage)
        .filter(L3ReplacementOutputPackage.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        if existing_for_request.authority_basis_hash != computed_basis_hash:
            _raise_mismatch(
                "replacement_package_namespace_client_request_conflict",
                "client_request_id",
                "client_request_id already recorded a different replacement package namespace row.",
            )
        return _namespace_response(request_id=request_id, status="already_recorded", row=existing_for_request)

    existing_for_basis = (
        db.query(L3ReplacementOutputPackage)
        .filter(L3ReplacementOutputPackage.authority_basis_hash == computed_basis_hash)
        .one_or_none()
    )
    if existing_for_basis is not None:
        return _namespace_response(request_id=request_id, status="already_recorded", row=existing_for_basis)

    existing_for_manifest_kind = (
        db.query(L3ReplacementOutputPackage)
        .filter(
            L3ReplacementOutputPackage.replacement_artifact_manifest_id == manifest_id,
            L3ReplacementOutputPackage.package_kind == package_kind,
        )
        .one_or_none()
    )
    if existing_for_manifest_kind is not None:
        if existing_for_manifest_kind.authority_basis_hash == computed_basis_hash:
            return _namespace_response(
                request_id=request_id,
                status="already_recorded",
                row=existing_for_manifest_kind,
            )
        _raise_mismatch(
            "replacement_package_namespace_manifest_kind_conflict",
            "package_kind",
            "replacement package namespace row already exists for this manifest and package kind.",
        )

    now = utcnow()
    summary = {
        "schema_id": "layer3.replacement_package_namespace_summary.v1",
        "mode": REPLACEMENT_PACKAGE_NAMESPACE_MODE,
        "source_gate": REPLACEMENT_PACKAGE_NAMESPACE_SOURCE_GATE,
        "source": {
            "output_package_id": source_output_package_id,
            "package_kind": source_package.package_kind,
            "package_schema_id": package_schema_id,
            "payload_ref": source_package.payload_ref,
            "payload_hash": source_package.payload_hash,
        },
        "replacement": {
            "artifact_ref": artifact_ref,
            "artifact_hash": artifact_hash,
            "replacement_artifact_manifest_id": manifest_id,
            "replacement_package_set_authority_id": replacement_authority_id,
            "package_supersession_commit_id": commit_id,
        },
        "negative_invariants": {
            "creates_l3_output_package": False,
            "mutates_l3_output_package": False,
            "writes_package_payload": False,
            "accepts_browser_package_bytes": False,
            "enables_connector_dispatch": False,
            "enables_source_widening": False,
            "enables_qualitative_hybrid_rag": False,
            "enables_provider_public_url": False,
            "enables_full_mockup_activation": False,
        },
    }
    row = L3ReplacementOutputPackage(
        client_request_id=request_id,
        session_id=session_id,
        source_output_package_id=source_output_package_id,
        replacement_artifact_manifest_id=manifest_id,
        replacement_package_set_authority_id=replacement_authority_id,
        package_supersession_commit_id=commit_id,
        package_kind=package_kind,
        package_schema_id=package_schema_id,
        artifact_ref=artifact_ref,
        artifact_hash=artifact_hash,
        authority_basis_hash=computed_basis_hash,
        operator_decision=REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION,
        status=REPLACEMENT_PACKAGE_NAMESPACE_STATUS,
        summary_json=summary,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = (
            db.query(L3ReplacementOutputPackage)
            .filter(L3ReplacementOutputPackage.client_request_id == request_id)
            .one_or_none()
        )
        if existing is None:
            existing = (
                db.query(L3ReplacementOutputPackage)
                .filter(L3ReplacementOutputPackage.authority_basis_hash == computed_basis_hash)
                .one_or_none()
            )
        if existing is not None and existing.authority_basis_hash == computed_basis_hash:
            return _namespace_response(request_id=request_id, status="already_recorded", row=existing)
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_namespace_in_progress",
            "Replacement package namespace row is already being recorded for this request.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "authority_basis_hash", "package_kind"],
            recoverable=True,
            next_allowed_actions=["retry_replacement_package_namespace_request"],
        ) from exc
    return _namespace_response(request_id=request_id, status="recorded", row=row)
