from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    L3AnalysisPlan,
    L3OutputPackage,
    L3PackageSupersessionCommit,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementPackageSetAuthority,
    L3Session,
)
from app.services import layer3_package_mutation_entry, layer3_workbench
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
)
from app.services.layer3_workbench_package_state import packages_in_kind_order, packages_with_kinds
from app.services.layer3_utils import json_clone, stable_hash, utcnow


PACKAGE_SUPERSESSION_COMMIT_SCHEMA_ID = "layer3.package_supersession_commit.v1"
PACKAGE_SUPERSESSION_COMMIT_MODE = "package_supersession_commit_entry"
PACKAGE_SUPERSESSION_COMMIT_SOURCE_GATE = "126_PACKAGE_COMMIT_FREEZE"
PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION = "commit_package_supersession"
PACKAGE_SUPERSESSION_COMMIT_STATE = "package_supersession_commit_recorded"
PACKAGE_SUPERSESSION_COMMIT_STATUS = "committed"

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
            "mode": PACKAGE_SUPERSESSION_COMMIT_MODE,
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
