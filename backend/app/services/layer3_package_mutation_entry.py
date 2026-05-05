from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3AnalysisPlan, L3OutputPackage, L3PassRun, L3ReconciliationRecord, L3Session
from app.services import layer3_workbench
from app.services.layer3_package_entry import (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_REVIEW_FACING,
    PACKAGE_KIND_USER_FACING,
)
from app.services.layer3_utils import json_clone, stable_hash
from app.services.layer3_workbench_package_state import packages_in_kind_order, packages_with_kinds


PACKAGE_SUPERSESSION_PREVIEW_SCHEMA_ID = "layer3.package_supersession_preview.v1"
PACKAGE_SUPERSESSION_PREVIEW_MODE = "package_supersession_preview_only"
PACKAGE_SUPERSESSION_PREVIEW_SOURCE_GATE = "122_PACKAGE_MUTATION_FREEZE"
PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION = "preview_package_supersession"
PACKAGE_SUPERSESSION_PREVIEW_STATE = "package_supersession_previewed"

PACKAGE_SUPERSESSION_SOURCE_PACKAGE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)

PACKAGE_SUPERSESSION_PREVIEW_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "session_id",
        "analysis_plan_id",
        "pass_run_id",
        "reconciliation_record_id",
        "output_package_ids",
        "package_kinds",
        "payload_refs",
        "payload_hashes",
        "package_review_preview_hash",
        "operator_decision",
    }
)
PACKAGE_SUPERSESSION_PREVIEW_OPTIONAL_FIELDS = frozenset(
    {
        "preview_id",
        "preview_hash",
        "analysis_run_id",
        "result_review_record_ref",
        "package_review_submit_record_ref",
        "handoff_export_record_ref",
        "aps_handoff_record_ref",
        "external_export_download_record_ref",
        "connector_dispatch_record_ref",
    }
)
PACKAGE_SUPERSESSION_PREVIEW_FORBIDDEN_FIELDS = frozenset(
    {
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "rebuild_package",
        "mutate_package",
        "replace_package",
        "delete_package",
        "update_payload_ref",
        "update_payload_hash",
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
        "result_review_amendment",
        "package_review_amendment",
        "handoff_export_amendment",
        "aps_handoff_amendment",
        "retry",
        "rerun",
        "cancel",
    }
)
PACKAGE_SUPERSESSION_PREVIEW_ALLOWED_FIELDS = (
    PACKAGE_SUPERSESSION_PREVIEW_REQUIRED_FIELDS
    | PACKAGE_SUPERSESSION_PREVIEW_OPTIONAL_FIELDS
    | PACKAGE_SUPERSESSION_PREVIEW_FORBIDDEN_FIELDS
)
PACKAGE_SUPERSESSION_PREVIEW_DOWNSTREAM_UNAVAILABLE = (
    "package_row_mutation",
    "package_payload_rewrite",
    "package_supersession_commit",
    "provider_public_url",
    "connector_destination_dispatch",
    "source_upload_expansion",
    "broad_qualitative_hybrid_rag_execution",
    "full_mockup_activation",
)

DOWNSTREAM_DEPENDENCY_SPECS = (
    {
        "state_key": "package_review_submit",
        "schema_id": layer3_workbench.PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID,
        "request_ref_field": "package_review_submit_record_ref",
        "state_ref_field": "submit_record_ref",
        "state_value_field": "package_review_state",
        "required_error_code": "package_supersession_preview_package_review_submit_record_ref_required",
    },
    {
        "state_key": "handoff_export_prepare",
        "schema_id": layer3_workbench.HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID,
        "request_ref_field": "handoff_export_record_ref",
        "state_ref_field": "prepare_record_ref",
        "state_value_field": "handoff_export_state",
        "required_error_code": "package_supersession_preview_handoff_export_record_ref_required",
    },
    {
        "state_key": "aps_handoff_dispatch",
        "schema_id": layer3_workbench.APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID,
        "request_ref_field": "aps_handoff_record_ref",
        "state_ref_field": "aps_handoff_record_ref",
        "state_value_field": "aps_handoff_state",
        "required_error_code": "package_supersession_preview_aps_handoff_record_ref_required",
    },
    {
        "state_key": "external_export_download_prepare",
        "schema_id": layer3_workbench.EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID,
        "request_ref_field": "external_export_download_record_ref",
        "state_ref_field": "external_export_download_record_ref",
        "state_value_field": "external_export_download_state",
        "required_error_code": "package_supersession_preview_external_export_download_record_ref_required",
    },
    {
        "state_key": "connector_dispatch_record",
        "schema_id": "layer3.connector_dispatch_record_state.v1",
        "request_ref_field": "connector_dispatch_record_ref",
        "state_ref_field": "connector_dispatch_record_ref",
        "state_value_field": "connector_dispatch_record_state",
        "required_error_code": "package_supersession_preview_connector_dispatch_record_ref_required",
    },
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


def _state_from_reconciliation(
    reconciliation: L3ReconciliationRecord,
    key: str,
    expected_schema: str,
) -> dict[str, Any] | None:
    state = (reconciliation.summary_json or {}).get(key)
    if not isinstance(state, dict):
        return None
    if state.get("schema_id") != expected_schema:
        return None
    return state


def _validate_supplied_list(
    *,
    payload: dict[str, Any],
    field: str,
    expected_values: list[str],
) -> None:
    supplied_values = _string_list(payload.get(field))
    if len(supplied_values) != len(expected_values) or set(supplied_values) != set(expected_values):
        _raise_mismatch(
            f"package_supersession_preview_{field}_mismatch",
            field,
            f"Supplied {field} do not match the immutable source package authority.",
        )


def _validate_optional_match(
    *,
    payload: dict[str, Any],
    field: str,
    expected: Any,
) -> None:
    if field in payload and _string(payload.get(field)) != _string(expected):
        _raise_mismatch(
            f"package_supersession_preview_{field}_mismatch",
            field,
            f"Supplied {field} does not match existing package authority.",
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
        package_kinds=PACKAGE_SUPERSESSION_SOURCE_PACKAGE_KINDS,
    )
    if (
        len(packages) != len(PACKAGE_SUPERSESSION_SOURCE_PACKAGE_KINDS)
        or {package.package_kind for package in packages} != set(PACKAGE_SUPERSESSION_SOURCE_PACKAGE_KINDS)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_preview_requires_complete_package_set",
            "Package supersession preview requires the existing canonical_internal, user_facing, and review_facing packages.",
            status="blocked",
            http_status=409,
            blocked_fields=["output_package_ids", "package_kinds"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    return packages_in_kind_order(packages, package_kinds=PACKAGE_SUPERSESSION_SOURCE_PACKAGE_KINDS)


def _package_row_projection(package: L3OutputPackage) -> dict[str, Any]:
    return {
        "output_package_id": package.output_package_id,
        "package_kind": package.package_kind,
        "status": package.status,
        "payload_ref": package.payload_ref,
        "payload_hash": package.payload_hash,
    }


def _validate_package_files(packages: list[L3OutputPackage]) -> None:
    missing_refs = [package.payload_ref for package in packages if not Path(package.payload_ref).exists()]
    if missing_refs:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_preview_payload_refs_unavailable",
            "Package supersession preview requires existing immutable package payload refs.",
            status="blocked",
            http_status=409,
            blocked_fields=["payload_refs"],
            next_allowed_actions=["inspect_package_payload_refs"],
        )


def _downstream_dependencies(
    *,
    reconciliation: L3ReconciliationRecord,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    dependencies: list[dict[str, Any]] = []
    for spec in DOWNSTREAM_DEPENDENCY_SPECS:
        state = _state_from_reconciliation(
            reconciliation,
            str(spec["state_key"]),
            str(spec["schema_id"]),
        )
        request_ref_field = str(spec["request_ref_field"])
        supplied_ref = _string(payload.get(request_ref_field))
        if state is None:
            if supplied_ref:
                _raise_mismatch(
                    f"package_supersession_preview_{request_ref_field}_not_recorded",
                    request_ref_field,
                    f"Supplied {request_ref_field} is not backed by existing downstream authority.",
                )
            continue

        expected_ref = _string(state.get(str(spec["state_ref_field"])))
        if not supplied_ref:
            raise layer3_workbench.Layer3WorkbenchError(
                str(spec["required_error_code"]),
                f"{request_ref_field} is required because downstream state already exists.",
                status="blocked",
                http_status=409,
                blocked_fields=[request_ref_field],
                next_allowed_actions=["submit_complete_package_supersession_preview_request"],
            )
        if supplied_ref != expected_ref:
            _raise_mismatch(
                f"package_supersession_preview_{request_ref_field}_mismatch",
                request_ref_field,
                f"Supplied {request_ref_field} does not match existing downstream authority.",
            )

        dependencies.append(
            {
                "state_key": spec["state_key"],
                "schema_id": state.get("schema_id"),
                "request_ref_field": request_ref_field,
                "record_ref": expected_ref,
                "state": state.get(str(spec["state_value_field"])),
                "present": True,
            }
        )
    return dependencies


def preview_package_supersession(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for package supersession preview.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_complete_package_supersession_preview_request"],
        )

    unknown = sorted(key for key in payload if key not in PACKAGE_SUPERSESSION_PREVIEW_ALLOWED_FIELDS)
    forbidden = sorted(key for key in PACKAGE_SUPERSESSION_PREVIEW_FORBIDDEN_FIELDS if key in payload)
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_preview_scope_not_admitted",
            "Package supersession preview request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_package_supersession_preview_only_request"],
        )

    missing = sorted(
        field
        for field in PACKAGE_SUPERSESSION_PREVIEW_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_package_supersession_preview_fields",
            "Package supersession preview request is missing required fields: " + ", ".join(missing) + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_package_supersession_preview_request"],
        )

    operator_decision = _string(payload.get("operator_decision"))
    if operator_decision != PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_package_supersession_preview_decision",
            "operator_decision must be preview_package_supersession.",
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
            "package_supersession_preview_requires_existing_authority",
            "Package supersession preview requires existing session, plan, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "analysis_plan_id", "pass_run_id", "reconciliation_record_id"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_preview_pass_run_mismatch",
            "pass_run_id must belong to the supplied session and analysis plan.",
            status="conflict",
            http_status=409,
            blocked_fields=["pass_run_id"],
        )

    reconciliation_summary = reconciliation.summary_json or {}
    commit_summary = reconciliation_summary.get("workbench_package_commit")
    if not isinstance(commit_summary, dict):
        raise layer3_workbench.Layer3WorkbenchError(
            "package_supersession_preview_requires_package_construction",
            "Package supersession preview requires existing workbench package-construction provenance.",
            status="blocked",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    if _string(payload.get("package_review_preview_hash")) != _string(
        commit_summary.get("package_review_preview_hash")
    ):
        _raise_mismatch(
            "package_supersession_preview_package_review_preview_hash_mismatch",
            "package_review_preview_hash",
            "Supplied package_review_preview_hash does not match package-construction authority.",
        )
    _validate_optional_match(
        payload=payload,
        field="result_review_record_ref",
        expected=commit_summary.get("result_review_record_ref"),
    )
    _validate_optional_match(
        payload=payload,
        field="analysis_run_id",
        expected=(pass_run.summary_json or {}).get("analysis_run_id"),
    )

    ordered_packages = _source_package_rows(
        db,
        session_id=session_id,
        reconciliation_record_id=reconciliation_record_id,
    )
    expected_package_ids = [package.output_package_id for package in ordered_packages]
    expected_package_kinds = [package.package_kind for package in ordered_packages]
    expected_payload_refs = [package.payload_ref for package in ordered_packages]
    expected_payload_hashes = [package.payload_hash for package in ordered_packages]
    _validate_supplied_list(payload=payload, field="output_package_ids", expected_values=expected_package_ids)
    _validate_supplied_list(payload=payload, field="package_kinds", expected_values=expected_package_kinds)
    _validate_supplied_list(payload=payload, field="payload_refs", expected_values=expected_payload_refs)
    _validate_supplied_list(payload=payload, field="payload_hashes", expected_values=expected_payload_hashes)
    _validate_package_files(ordered_packages)

    downstream_dependencies = _downstream_dependencies(reconciliation=reconciliation, payload=payload)
    package_rows = [_package_row_projection(package) for package in ordered_packages]
    package_set_hash = stable_hash(
        {
            "schema_id": "layer3.package_supersession_source_package_set.v1",
            "session_id": session_id,
            "reconciliation_record_id": reconciliation_record_id,
            "output_packages": package_rows,
        }
    )
    preview_basis = {
        "schema_id": "layer3.package_supersession_preview_basis.v1",
        "mode": PACKAGE_SUPERSESSION_PREVIEW_MODE,
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "reconciliation_record_id": reconciliation_record_id,
        "package_review_preview_hash": _string(payload.get("package_review_preview_hash")),
        "package_set_hash": package_set_hash,
        "downstream_dependencies": downstream_dependencies,
    }
    package_supersession_preview_hash = stable_hash(preview_basis)

    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            PACKAGE_SUPERSESSION_PREVIEW_SCHEMA_ID,
            request_id=request_id,
            status="previewed",
        ),
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_identity": {
            "preview_id": _string(payload.get("preview_id")) or None,
            "preview_hash": _string(payload.get("preview_hash")) or None,
            "authority_source": "optional_request_echo_package_construction_hash_is_authoritative",
        },
        "analysis_run_id": _string(payload.get("analysis_run_id"))
        or _string((pass_run.summary_json or {}).get("analysis_run_id"))
        or None,
        "result_review_record_ref": commit_summary.get("result_review_record_ref"),
        "package_review_preview_hash": _string(payload.get("package_review_preview_hash")),
        "reconciliation_record_id": reconciliation_record_id,
        "output_package_ids": expected_package_ids,
        "package_kinds": expected_package_kinds,
        "payload_refs": expected_payload_refs,
        "payload_hashes": expected_payload_hashes,
        "operator_decision": PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION,
        "package_supersession_preview_mode": PACKAGE_SUPERSESSION_PREVIEW_MODE,
        "package_supersession_preview_hash": package_supersession_preview_hash,
        "package_set_hash": package_set_hash,
        "package_rows": package_rows,
        "downstream_dependencies": json_clone(downstream_dependencies),
        "downstream_dependency_detected": bool(downstream_dependencies),
        "immutable_package_rule_enforced": True,
        "package_row_mutation_enabled": False,
        "package_payload_rewrite_enabled": False,
        "package_supersession_commit_enabled": False,
        "database_write_enabled": False,
        "filesystem_write_enabled": False,
        "broad_package_mutation_enabled": False,
        "source_widening_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "downstream_unavailable": list(PACKAGE_SUPERSESSION_PREVIEW_DOWNSTREAM_UNAVAILABLE),
        "next_state": PACKAGE_SUPERSESSION_PREVIEW_STATE,
        "authority_rail": layer3_workbench._authority_rail(  # noqa: SLF001
            session_id=session_id,
            current_gate="package",
            persistence_mode="read_only_package_supersession_preview",
            downstream_unavailable=PACKAGE_SUPERSESSION_PREVIEW_DOWNSTREAM_UNAVAILABLE,
            execution_enabled=False,
            package_review_enabled=False,
        ),
    }
