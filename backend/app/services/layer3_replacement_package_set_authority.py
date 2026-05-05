from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisPlan,
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
)
from app.services.layer3_utils import json_clone, stable_hash, utcnow
from app.services.layer3_workbench_package_state import packages_in_kind_order, packages_with_kinds


REPLACEMENT_PACKAGE_SET_AUTHORITY_SCHEMA_ID = "layer3.replacement_package_set_authority.v1"
REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE = "replacement_package_set_authority"
REPLACEMENT_PACKAGE_SET_AUTHORITY_SOURCE_GATE = "127_PACKAGE_REPLACEMENT_SET_FREEZE"
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
            "mode": REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE,
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
