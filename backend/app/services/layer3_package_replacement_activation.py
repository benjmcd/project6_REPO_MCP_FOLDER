from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3OutputPackage,
    L3PackageReplacementActivation,
    L3PackageSupersessionCommit,
    L3ReplacementOutputPackage,
    L3ReplacementPackageArtifactManifest,
    L3ReplacementPackageSetAuthority,
    L3Session,
)
from app.services import layer3_workbench
from app.services.layer3_package_entry import PACKAGE_SCHEMA_IDS
from app.services.layer3_utils import json_clone, stable_hash, utc_isoformat, utcnow


PACKAGE_REPLACEMENT_ACTIVATION_SCHEMA_ID = "layer3.package_replacement_activation.v1"
PACKAGE_REPLACEMENT_ACTIVATION_MODE = "source_l3_output_package_replacement_activation"
PACKAGE_REPLACEMENT_ACTIVATION_SOURCE_GATE = "664_SOURCE_L3_OUTPUT_PACKAGE_REPLACEMENT_ACTIVATION_FREEZE"
PACKAGE_REPLACEMENT_ACTIVATION_OPERATOR_DECISION = "activate_replacement_output_package_namespace"
PACKAGE_REPLACEMENT_ACTIVATION_STATUS = "activated"
PACKAGE_REPLACEMENT_ACTIVATION_STATE = "source_l3_output_package_replacement_activation_recorded"

PACKAGE_REPLACEMENT_ACTIVATION_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "replacement_artifact_manifest_id",
        "replacement_package_set_authority_id",
        "package_supersession_commit_id",
        "replacement_output_package_ids",
        "source_output_package_ids",
        "package_kinds",
        "replacement_activation_basis_hash",
        "operator_decision",
    }
)
PACKAGE_REPLACEMENT_ACTIVATION_FORBIDDEN_FIELDS = frozenset(
    {
        "package_payload",
        "package_payload_bytes",
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
PACKAGE_REPLACEMENT_ACTIVATION_ALLOWED_FIELDS = (
    PACKAGE_REPLACEMENT_ACTIVATION_REQUIRED_FIELDS | PACKAGE_REPLACEMENT_ACTIVATION_FORBIDDEN_FIELDS
)
PACKAGE_REPLACEMENT_ACTIVATION_DOWNSTREAM_UNAVAILABLE = (
    "source_l3_output_package_row_mutation",
    "package_payload_rewrite",
    "downstream_handoff_rebinding",
    "provider_public_url",
    "connector_destination_dispatch",
    "source_upload_expansion",
    "broad_qualitative_hybrid_rag_execution",
    "full_mockup_activation",
)


def _canonical_package_kinds() -> list[str]:
    return list(PACKAGE_SCHEMA_IDS.keys())


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
        next_allowed_actions=["refresh_package_replacement_activation_authority"],
    )


def _response_safe_artifact_ref(*, manifest_id: str, package_kind: str) -> str:
    return f"artifact://replacement-package-artifacts/{manifest_id}/{package_kind}"


def package_replacement_activation_basis_hash(
    *,
    session_id: str,
    source_output_package_ids: list[str],
    source_package_kinds: list[str],
    source_payload_hashes: list[str],
    replacement_output_package_ids: list[str],
    replacement_namespace_basis_hashes: list[str],
    active_artifact_refs: list[str],
    active_artifact_hashes: list[str],
    replacement_artifact_manifest_id: str,
    replacement_artifact_manifest_authority_basis_hash: str,
    replacement_artifact_manifest_hash: str,
    replacement_package_set_authority_id: str,
    replacement_package_set_authority_basis_hash: str,
    package_supersession_commit_id: str,
    package_supersession_commit_basis_hash: str,
    package_kinds: list[str],
    operator_decision: str,
) -> str:
    return stable_hash(
        {
            "schema_id": "layer3.package_replacement_activation_authority.v1",
            "mode": PACKAGE_REPLACEMENT_ACTIVATION_MODE,
            "session_id": session_id,
            "source": {
                "output_package_ids": list(source_output_package_ids),
                "package_kinds": list(source_package_kinds),
                "payload_hashes": list(source_payload_hashes),
            },
            "replacement_namespace": {
                "replacement_output_package_ids": list(replacement_output_package_ids),
                "authority_basis_hashes": list(replacement_namespace_basis_hashes),
                "artifact_refs": list(active_artifact_refs),
                "artifact_hashes": list(active_artifact_hashes),
            },
            "replacement_artifact_manifest": {
                "replacement_artifact_manifest_id": replacement_artifact_manifest_id,
                "authority_basis_hash": replacement_artifact_manifest_authority_basis_hash,
                "artifact_manifest_hash": replacement_artifact_manifest_hash,
            },
            "replacement_package_set_authority": {
                "replacement_package_set_authority_id": replacement_package_set_authority_id,
                "authority_basis_hash": replacement_package_set_authority_basis_hash,
            },
            "package_supersession_commit": {
                "package_supersession_commit_id": package_supersession_commit_id,
                "commit_basis_hash": package_supersession_commit_basis_hash,
            },
            "package_kinds": list(package_kinds),
            "operator_decision": operator_decision,
        }
    )


def _validate_payload(payload: dict[str, Any]) -> str:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for package replacement activation.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_complete_package_replacement_activation_request"],
        )
    unknown = sorted(key for key in payload if key not in PACKAGE_REPLACEMENT_ACTIVATION_ALLOWED_FIELDS)
    forbidden = sorted(key for key in PACKAGE_REPLACEMENT_ACTIVATION_FORBIDDEN_FIELDS if key in payload)
    blocked = sorted(set(unknown) | set(forbidden))
    if blocked:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_replacement_activation_scope_not_admitted",
            "Package replacement activation request includes non-admitted fields: " + ", ".join(blocked) + ".",
            status="blocked",
            blocked_fields=blocked,
            next_allowed_actions=["submit_package_replacement_activation_only_request"],
        )
    missing = sorted(
        field for field in PACKAGE_REPLACEMENT_ACTIVATION_REQUIRED_FIELDS if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_package_replacement_activation_fields",
            "Package replacement activation request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_package_replacement_activation_request"],
        )
    if _string(payload.get("operator_decision")) != PACKAGE_REPLACEMENT_ACTIVATION_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_package_replacement_activation_decision",
            "operator_decision must be activate_replacement_output_package_namespace.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )
    return request_id


def _activation_response(*, request_id: str, status: str, row: L3PackageReplacementActivation) -> dict[str, Any]:
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            PACKAGE_REPLACEMENT_ACTIVATION_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "package_replacement_activation_id": row.package_replacement_activation_id,
        "session_id": row.session_id,
        "replacement_artifact_manifest_id": row.replacement_artifact_manifest_id,
        "replacement_package_set_authority_id": row.replacement_package_set_authority_id,
        "package_supersession_commit_id": row.package_supersession_commit_id,
        "replacement_output_package_ids": json_clone(row.replacement_output_package_ids_json),
        "source_output_package_ids": json_clone(row.source_output_package_ids_json),
        "package_kinds": json_clone(row.package_kinds_json),
        "active_artifact_refs": json_clone(row.active_artifact_refs_json),
        "active_artifact_hashes": json_clone(row.active_artifact_hashes_json),
        "replacement_activation_basis_hash": row.replacement_activation_basis_hash,
        "activation_snapshot": json_clone(row.activation_snapshot_json),
        "operator_decision": row.operator_decision,
        "package_replacement_activation_mode": PACKAGE_REPLACEMENT_ACTIVATION_MODE,
        "source_gate": PACKAGE_REPLACEMENT_ACTIVATION_SOURCE_GATE,
        "activation_receipt_persisted": True,
        "package_activation_state_persisted": True,
        "source_l3_output_package_mutated": False,
        "package_row_mutation_enabled": False,
        "package_payload_write_enabled": False,
        "package_payload_rewrite_enabled": False,
        "downstream_handoff_rebinding_enabled": False,
        "source_widening_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "frontend_only_durable_state_enabled": False,
        "downstream_unavailable": list(PACKAGE_REPLACEMENT_ACTIVATION_DOWNSTREAM_UNAVAILABLE),
        "next_state": PACKAGE_REPLACEMENT_ACTIVATION_STATE,
        "created_at": utc_isoformat(row.created_at),
        "updated_at": utc_isoformat(row.updated_at),
        "authority_rail": {
            "dedicated_activation_table": True,
            "replacement_namespace_rows_selected": True,
            "active_package_authority_resolver_available": True,
            "source_l3_output_package_uniqueness_preserved": True,
            "raw_local_paths_exposed": False,
            "browser_package_bytes_accepted": False,
            "browser_destination_path_accepted": False,
        },
    }


def _activation_inputs(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    session_id = _string(payload.get("session_id"))
    manifest_id = _string(payload.get("replacement_artifact_manifest_id"))
    replacement_authority_id = _string(payload.get("replacement_package_set_authority_id"))
    commit_id = _string(payload.get("package_supersession_commit_id"))
    package_kinds = _string_list(payload.get("package_kinds"))
    source_ids = _string_list(payload.get("source_output_package_ids"))
    replacement_ids = _string_list(payload.get("replacement_output_package_ids"))

    if package_kinds != _canonical_package_kinds():
        _raise_mismatch(
            "package_replacement_activation_package_kinds_mismatch",
            "package_kinds",
            "package_kinds must equal the complete canonical Layer 3 output package-kind set.",
        )
    if len(set(source_ids)) != len(source_ids) or len(set(replacement_ids)) != len(replacement_ids):
        _raise_mismatch(
            "package_replacement_activation_duplicate_package_ids",
            "replacement_output_package_ids",
            "source_output_package_ids and replacement_output_package_ids must not contain duplicates.",
        )
    if len(source_ids) != len(package_kinds) or len(replacement_ids) != len(package_kinds):
        _raise_mismatch(
            "package_replacement_activation_package_vector_length_mismatch",
            "package_kinds",
            "source, replacement, and package-kind vectors must have the same length.",
        )

    session = db.query(L3Session).filter(L3Session.session_id == session_id).one_or_none()
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
    if session is None or manifest is None or replacement_authority is None or supersession_commit is None:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_replacement_activation_requires_existing_authority",
            "Package replacement activation requires existing session, manifest, replacement authority, and supersession commit.",
            status="blocked",
            http_status=409,
            blocked_fields=[
                "session_id",
                "replacement_artifact_manifest_id",
                "replacement_package_set_authority_id",
                "package_supersession_commit_id",
            ],
            next_allowed_actions=["refresh_package_replacement_activation_authority"],
        )
    if manifest.session_id != session_id or replacement_authority.session_id != session_id or supersession_commit.session_id != session_id:
        _raise_mismatch("package_replacement_activation_session_mismatch", "session_id", "All authority rows must belong to the same session.")
    if manifest.replacement_package_set_authority_id != replacement_authority_id:
        _raise_mismatch("package_replacement_activation_manifest_authority_mismatch", "replacement_artifact_manifest_id", "Manifest must belong to the supplied replacement package-set authority.")
    if manifest.package_supersession_commit_id != commit_id:
        _raise_mismatch("package_replacement_activation_manifest_commit_mismatch", "replacement_artifact_manifest_id", "Manifest must belong to the supplied supersession commit.")
    if supersession_commit.replacement_package_set_authority_id != replacement_authority_id:
        _raise_mismatch("package_replacement_activation_commit_authority_mismatch", "package_supersession_commit_id", "Supersession commit must belong to the supplied replacement package-set authority.")

    for owner, field, values in (
        ("replacement_authority", "source_output_package_ids_json", source_ids),
        ("replacement_authority", "source_package_kinds_json", package_kinds),
        ("replacement_authority", "replacement_package_kinds_json", package_kinds),
        ("supersession_commit", "source_output_package_ids_json", source_ids),
        ("supersession_commit", "source_package_kinds_json", package_kinds),
        ("supersession_commit", "replacement_package_kinds_json", package_kinds),
        ("manifest", "replacement_package_kinds_json", package_kinds),
    ):
        row = {"replacement_authority": replacement_authority, "supersession_commit": supersession_commit, "manifest": manifest}[owner]
        if _string_list(getattr(row, field)) != values:
            _raise_mismatch(f"package_replacement_activation_{owner}_{field}_mismatch", field, "Activation vectors must match durable package authority.")

    source_rows = db.query(L3OutputPackage).filter(L3OutputPackage.output_package_id.in_(source_ids)).all()
    replacement_rows = (
        db.query(L3ReplacementOutputPackage)
        .filter(L3ReplacementOutputPackage.replacement_output_package_id.in_(replacement_ids))
        .all()
    )
    if len(source_rows) != len(source_ids) or len(replacement_rows) != len(replacement_ids):
        _raise_mismatch(
            "package_replacement_activation_missing_namespace_or_source_rows",
            "replacement_output_package_ids",
            "Every source and replacement package id must resolve to an existing durable row.",
        )

    source_by_kind = {row.package_kind: row for row in source_rows if row.session_id == session_id}
    replacement_by_kind = {row.package_kind: row for row in replacement_rows if row.session_id == session_id}
    if set(source_by_kind) != set(package_kinds) or set(replacement_by_kind) != set(package_kinds):
        _raise_mismatch("package_replacement_activation_kind_row_mismatch", "package_kinds", "Source and replacement rows must cover the complete package-kind set for the same session.")

    source_hashes = _string_list(replacement_authority.source_payload_hashes_json)
    source_refs = _string_list(replacement_authority.source_payload_refs_json)
    verified_hashes = _string_list(manifest.verified_artifact_hashes_json)
    if len(source_hashes) != len(package_kinds) or len(source_refs) != len(package_kinds) or len(verified_hashes) != len(package_kinds):
        _raise_mismatch("package_replacement_activation_authority_vector_malformed", "package_kinds", "Durable source or manifest vectors are malformed.")

    active_refs: list[str] = []
    active_hashes: list[str] = []
    namespace_basis_hashes: list[str] = []
    for index, kind in enumerate(package_kinds):
        source_row = source_by_kind[kind]
        replacement_row = replacement_by_kind[kind]
        if source_row.output_package_id != source_ids[index]:
            _raise_mismatch("package_replacement_activation_source_id_mismatch", "source_output_package_ids", "Source package ids must match package_kinds order.")
        if source_row.payload_ref != source_refs[index] or source_row.payload_hash != source_hashes[index]:
            _raise_mismatch("package_replacement_activation_source_payload_mismatch", "source_output_package_ids", "Current source package payload authority is stale relative to replacement authority.")
        if replacement_row.replacement_output_package_id != replacement_ids[index]:
            _raise_mismatch("package_replacement_activation_replacement_id_mismatch", "replacement_output_package_ids", "Replacement package ids must match package_kinds order.")
        if replacement_row.source_output_package_id != source_ids[index]:
            _raise_mismatch("package_replacement_activation_namespace_source_mismatch", "replacement_output_package_ids", "Replacement namespace row must bind to the matching source package.")
        if replacement_row.replacement_artifact_manifest_id != manifest_id or replacement_row.replacement_package_set_authority_id != replacement_authority_id or replacement_row.package_supersession_commit_id != commit_id:
            _raise_mismatch("package_replacement_activation_namespace_lineage_mismatch", "replacement_output_package_ids", "Replacement namespace row lineage must match the selected activation authority.")
        if replacement_row.package_schema_id != PACKAGE_SCHEMA_IDS[kind]:
            _raise_mismatch("package_replacement_activation_namespace_schema_mismatch", "replacement_output_package_ids", "Replacement namespace package schema must match package kind.")
        expected_ref = _response_safe_artifact_ref(manifest_id=manifest_id, package_kind=kind)
        if replacement_row.artifact_ref != expected_ref:
            _raise_mismatch("package_replacement_activation_artifact_ref_mismatch", "replacement_output_package_ids", "Replacement namespace artifact refs must be response-safe manifest refs.")
        if replacement_row.artifact_hash != verified_hashes[index]:
            _raise_mismatch("package_replacement_activation_artifact_hash_mismatch", "replacement_output_package_ids", "Replacement namespace artifact hash must match verified manifest hash.")
        active_refs.append(replacement_row.artifact_ref)
        active_hashes.append(replacement_row.artifact_hash)
        namespace_basis_hashes.append(replacement_row.authority_basis_hash)

    computed_basis_hash = package_replacement_activation_basis_hash(
        session_id=session_id,
        source_output_package_ids=source_ids,
        source_package_kinds=package_kinds,
        source_payload_hashes=source_hashes,
        replacement_output_package_ids=replacement_ids,
        replacement_namespace_basis_hashes=namespace_basis_hashes,
        active_artifact_refs=active_refs,
        active_artifact_hashes=active_hashes,
        replacement_artifact_manifest_id=manifest_id,
        replacement_artifact_manifest_authority_basis_hash=manifest.authority_basis_hash,
        replacement_artifact_manifest_hash=manifest.artifact_manifest_hash,
        replacement_package_set_authority_id=replacement_authority_id,
        replacement_package_set_authority_basis_hash=replacement_authority.authority_basis_hash,
        package_supersession_commit_id=commit_id,
        package_supersession_commit_basis_hash=supersession_commit.commit_basis_hash,
        package_kinds=package_kinds,
        operator_decision=PACKAGE_REPLACEMENT_ACTIVATION_OPERATOR_DECISION,
    )
    if _string(payload.get("replacement_activation_basis_hash")) != computed_basis_hash:
        _raise_mismatch("package_replacement_activation_basis_hash_mismatch", "replacement_activation_basis_hash", "replacement_activation_basis_hash must match current activation authority.")

    return {
        "session_id": session_id,
        "manifest_id": manifest_id,
        "replacement_authority_id": replacement_authority_id,
        "commit_id": commit_id,
        "package_kinds": package_kinds,
        "source_ids": source_ids,
        "source_hashes": source_hashes,
        "replacement_ids": replacement_ids,
        "active_refs": active_refs,
        "active_hashes": active_hashes,
        "namespace_basis_hashes": namespace_basis_hashes,
        "basis_hash": computed_basis_hash,
        "manifest": manifest,
        "replacement_authority": replacement_authority,
        "supersession_commit": supersession_commit,
    }


def resolve_active_replacement_package_authority(db: Session, *, session_id: str) -> dict[str, Any] | None:
    row = (
        db.query(L3PackageReplacementActivation)
        .filter(L3PackageReplacementActivation.session_id == session_id)
        .one_or_none()
    )
    if row is None:
        return None
    return {
        "schema_id": "layer3.active_replacement_package_authority.v1",
        "session_id": row.session_id,
        "package_replacement_activation_id": row.package_replacement_activation_id,
        "package_kinds": json_clone(row.package_kinds_json),
        "replacement_output_package_ids": json_clone(row.replacement_output_package_ids_json),
        "active_artifact_refs": json_clone(row.active_artifact_refs_json),
        "active_artifact_hashes": json_clone(row.active_artifact_hashes_json),
        "replacement_activation_basis_hash": row.replacement_activation_basis_hash,
        "source_gate": PACKAGE_REPLACEMENT_ACTIVATION_SOURCE_GATE,
    }


def commit_package_replacement_activation(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _validate_payload(payload)
    inputs = _activation_inputs(db, payload)

    existing_for_request = (
        db.query(L3PackageReplacementActivation)
        .filter(L3PackageReplacementActivation.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        if existing_for_request.replacement_activation_basis_hash != inputs["basis_hash"]:
            _raise_mismatch("package_replacement_activation_client_request_conflict", "client_request_id", "client_request_id already activated a different replacement package namespace.")
        return _activation_response(request_id=request_id, status="already_activated", row=existing_for_request)

    existing_for_basis = (
        db.query(L3PackageReplacementActivation)
        .filter(L3PackageReplacementActivation.replacement_activation_basis_hash == inputs["basis_hash"])
        .one_or_none()
    )
    if existing_for_basis is not None:
        return _activation_response(request_id=request_id, status="already_activated", row=existing_for_basis)

    existing_for_session = (
        db.query(L3PackageReplacementActivation)
        .filter(L3PackageReplacementActivation.session_id == inputs["session_id"])
        .one_or_none()
    )
    if existing_for_session is not None:
        _raise_mismatch("package_replacement_activation_active_conflict", "session_id", "A different replacement package namespace is already active for this session.")

    now = utcnow()
    snapshot = {
        "schema_id": "layer3.package_replacement_activation_snapshot.v1",
        "mode": PACKAGE_REPLACEMENT_ACTIVATION_MODE,
        "source_gate": PACKAGE_REPLACEMENT_ACTIVATION_SOURCE_GATE,
        "source": {
            "output_package_ids": inputs["source_ids"],
            "package_kinds": inputs["package_kinds"],
            "payload_hashes": inputs["source_hashes"],
        },
        "replacement_namespace": {
            "replacement_output_package_ids": inputs["replacement_ids"],
            "authority_basis_hashes": inputs["namespace_basis_hashes"],
            "artifact_refs": inputs["active_refs"],
            "artifact_hashes": inputs["active_hashes"],
        },
        "authority": {
            "replacement_artifact_manifest_id": inputs["manifest_id"],
            "replacement_artifact_manifest_basis_hash": inputs["manifest"].authority_basis_hash,
            "replacement_package_set_authority_id": inputs["replacement_authority_id"],
            "replacement_package_set_authority_basis_hash": inputs["replacement_authority"].authority_basis_hash,
            "package_supersession_commit_id": inputs["commit_id"],
            "package_supersession_commit_basis_hash": inputs["supersession_commit"].commit_basis_hash,
        },
        "negative_invariants": {
            "mutates_l3_output_package": False,
            "writes_package_payload": False,
            "accepts_browser_package_bytes": False,
            "accepts_browser_destination_path": False,
            "enables_connector_dispatch": False,
            "enables_source_widening": False,
            "enables_qualitative_hybrid_rag": False,
            "enables_provider_public_url": False,
        },
    }
    row = L3PackageReplacementActivation(
        client_request_id=request_id,
        session_id=inputs["session_id"],
        replacement_artifact_manifest_id=inputs["manifest_id"],
        replacement_package_set_authority_id=inputs["replacement_authority_id"],
        package_supersession_commit_id=inputs["commit_id"],
        replacement_output_package_ids_json=inputs["replacement_ids"],
        source_output_package_ids_json=inputs["source_ids"],
        package_kinds_json=inputs["package_kinds"],
        active_artifact_refs_json=inputs["active_refs"],
        active_artifact_hashes_json=inputs["active_hashes"],
        replacement_activation_basis_hash=inputs["basis_hash"],
        activation_snapshot_json=snapshot,
        operator_decision=PACKAGE_REPLACEMENT_ACTIVATION_OPERATOR_DECISION,
        status=PACKAGE_REPLACEMENT_ACTIVATION_STATUS,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = (
            db.query(L3PackageReplacementActivation)
            .filter(L3PackageReplacementActivation.client_request_id == request_id)
            .one_or_none()
        )
        if existing is None:
            existing = (
                db.query(L3PackageReplacementActivation)
                .filter(L3PackageReplacementActivation.replacement_activation_basis_hash == inputs["basis_hash"])
                .one_or_none()
            )
        if existing is not None and existing.replacement_activation_basis_hash == inputs["basis_hash"]:
            return _activation_response(request_id=request_id, status="already_activated", row=existing)
        raise layer3_workbench.Layer3WorkbenchError(
            "package_replacement_activation_in_progress",
            "Package replacement activation is already being recorded for this request or session.",
            status="conflict",
            http_status=409,
            blocked_fields=["client_request_id", "replacement_activation_basis_hash", "session_id"],
            recoverable=True,
            next_allowed_actions=["retry_package_replacement_activation_request"],
        ) from exc
    return _activation_response(request_id=request_id, status="activated", row=row)
