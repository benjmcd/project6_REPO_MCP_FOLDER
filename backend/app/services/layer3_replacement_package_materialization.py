from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    L3AnalysisPlan,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3ReplacementPackageArtifactMaterialization,
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
from app.services.layer3_utils import (
    json_clone,
    stable_hash,
    stable_id,
    stable_json_bytes,
    utc_isoformat,
    utcnow,
)
from app.services.layer3_workbench_package_state import packages_in_kind_order, packages_with_kinds


REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_SCHEMA_ID = (
    "layer3.replacement_package_artifact_materialization.v1"
)
REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_MODE = (
    "server_owned_replacement_package_artifact_materialization_request_source"
)
REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_SOURCE_GATE = (
    "640_REPLACEMENT_PACKAGE_SET_REQUEST_SOURCE_AUTHORITY_SELECTION_FREEZE"
)
REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_OPERATOR_DECISION = (
    "materialize_replacement_package_artifacts_from_supersession_preview"
)
REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_STATE = "replacement_package_artifacts_materialized"
REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_STATUS = "materialized"
REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE = "replacement-package-artifacts"
REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM = "sha256"

REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_PACKAGE_KINDS = (
    PACKAGE_KIND_CANONICAL_INTERNAL,
    PACKAGE_KIND_USER_FACING,
    PACKAGE_KIND_REVIEW_FACING,
)

REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_REQUIRED_FIELDS = frozenset(
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
        "operator_decision",
    }
)
REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_FORBIDDEN_FIELDS = frozenset(
    {
        "replacement_package_set_id",
        "replacement_package_set_hash",
        "replacement_package_kinds",
        "replacement_payload_refs",
        "replacement_payload_hashes",
        "authority_basis_hash",
        "materialization_basis_hash",
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
        "replacement_package_set_authority_id",
        "package_supersession_commit",
        "package_supersession_commit_id",
        "replacement_output_package_ids",
        "package_row_mutation",
        "package_payload_write",
        "package_payload_rewrite",
        "artifact_manifest",
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
REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_ALLOWED_FIELDS = (
    REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_REQUIRED_FIELDS
    | REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_FORBIDDEN_FIELDS
)
REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_DOWNSTREAM_UNAVAILABLE = (
    "package_row_mutation",
    "source_l3_output_package_mutation",
    "source_package_payload_rewrite",
    "package_supersession_commit",
    "replacement_artifact_manifest_record",
    "replacement_namespace_rows",
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


def _safe_token(value: str) -> str:
    raw = _string(value) or "unknown"
    return "".join(char for char in raw if char.isalnum() or char in {"_", "-", "."}) or "unknown"


def _raise_mismatch(error_code: str, field: str, message: str) -> None:
    raise layer3_workbench.Layer3WorkbenchError(
        error_code,
        message,
        status="conflict",
        http_status=409,
        blocked_fields=[field],
        recoverable=True,
        next_allowed_actions=["refresh_replacement_package_artifact_materialization_authority"],
    )


def _artifact_root() -> Path:
    root = Path(settings.artifact_storage_dir) / "layer3" / REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE
    root.mkdir(parents=True, exist_ok=True)
    return root


def _artifact_path(
    *,
    session_id: str,
    package_supersession_preview_hash: str,
    package_kind: str,
    payload_hash: str,
) -> Path:
    return (
        _artifact_root()
        / _safe_token(session_id)
        / _safe_token(package_supersession_preview_hash[:24])
        / f"{_safe_token(package_kind)}_{payload_hash}.json"
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
        package_kinds=REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_PACKAGE_KINDS,
    )
    if (
        len(packages) != len(REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_PACKAGE_KINDS)
        or {package.package_kind for package in packages}
        != set(REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_PACKAGE_KINDS)
    ):
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_materialization_requires_complete_source_package_set",
            "Replacement package artifact materialization requires the existing canonical_internal, user_facing, and review_facing packages.",
            status="blocked",
            http_status=409,
            blocked_fields=["source_output_package_ids", "source_package_kinds"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    return packages_in_kind_order(
        packages,
        package_kinds=REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_PACKAGE_KINDS,
    )


def _validate_supplied_list(*, payload: dict[str, Any], field: str, expected_values: list[str]) -> None:
    supplied_values = _string_list(payload.get(field))
    if len(supplied_values) != len(expected_values) or set(supplied_values) != set(expected_values):
        _raise_mismatch(
            f"replacement_package_artifact_materialization_{field}_mismatch",
            field,
            f"Supplied {field} do not match immutable package materialization authority.",
        )


def _downstream_dependencies_from_reconciliation(reconciliation: L3ReconciliationRecord) -> list[dict[str, Any]]:
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
                "state_key": spec["state_key"],
                "schema_id": state.get("schema_id"),
                "request_ref_field": spec["request_ref_field"],
                "record_ref": _string(state.get(str(spec["state_ref_field"]))),
                "state": state.get(str(spec["state_value_field"])),
                "present": True,
            }
        )
    return dependencies


def _payload_matches_existing_request(
    *,
    payload: dict[str, Any],
    existing: L3ReplacementPackageArtifactMaterialization,
) -> bool:
    def _same_supplied_values(field: str, existing_values: Any) -> bool:
        supplied_values = _string_list(payload.get(field))
        persisted_values = [_string(item) for item in list(existing_values or [])]
        return len(supplied_values) == len(persisted_values) and set(supplied_values) == set(persisted_values)

    return (
        _string(payload.get("session_id")) == existing.session_id
        and _string(payload.get("analysis_plan_id")) == existing.analysis_plan_id
        and _string(payload.get("pass_run_id")) == existing.pass_run_id
        and _string(payload.get("reconciliation_record_id")) == existing.reconciliation_record_id
        and _string(payload.get("package_supersession_preview_hash")) == existing.package_supersession_preview_hash
        and _string(payload.get("source_package_set_hash")) == existing.source_package_set_hash
        and _same_supplied_values("source_output_package_ids", existing.source_output_package_ids_json)
        and _same_supplied_values("source_package_kinds", existing.source_package_kinds_json)
        and _same_supplied_values("source_payload_refs", existing.source_payload_refs_json)
        and _same_supplied_values("source_payload_hashes", existing.source_payload_hashes_json)
        and _string(payload.get("operator_decision")) == existing.operator_decision
    )


def _materialization_response(
    *,
    request_id: str,
    status: str,
    materialization: L3ReplacementPackageArtifactMaterialization,
) -> dict[str, Any]:
    return {
        **layer3_workbench._base_response(  # noqa: SLF001
            REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_SCHEMA_ID,
            request_id=request_id,
            status=status,
        ),
        "replacement_artifact_materialization_id": (
            materialization.replacement_artifact_materialization_id
        ),
        "session_id": materialization.session_id,
        "analysis_plan_id": materialization.analysis_plan_id,
        "pass_run_id": materialization.pass_run_id,
        "reconciliation_record_id": materialization.reconciliation_record_id,
        "package_supersession_preview_hash": materialization.package_supersession_preview_hash,
        "source_package_set_hash": materialization.source_package_set_hash,
        "source_output_package_ids": json_clone(materialization.source_output_package_ids_json),
        "source_package_kinds": json_clone(materialization.source_package_kinds_json),
        "source_payload_refs": json_clone(materialization.source_payload_refs_json),
        "source_payload_hashes": json_clone(materialization.source_payload_hashes_json),
        "replacement_package_set_id": materialization.replacement_package_set_id,
        "replacement_package_set_hash": materialization.replacement_package_set_hash,
        "replacement_package_kinds": json_clone(materialization.replacement_package_kinds_json),
        "replacement_payload_refs": json_clone(materialization.replacement_payload_refs_json),
        "replacement_payload_hashes": json_clone(materialization.replacement_payload_hashes_json),
        "authority_basis_hash": materialization.authority_basis_hash,
        "materialization_basis_hash": materialization.materialization_basis_hash,
        "materialization_snapshot": json_clone(materialization.materialization_snapshot_json),
        "operator_decision": materialization.operator_decision,
        "replacement_package_artifact_materialization_mode": (
            REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_MODE
        ),
        "source_gate": REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_SOURCE_GATE,
        "artifact_namespace": REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
        "hash_algorithm": REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
        "materialization_record_persisted": True,
        "artifact_write_enabled": True,
        "package_row_mutation_enabled": False,
        "source_l3_output_package_mutation_enabled": False,
        "source_package_payload_rewrite_enabled": False,
        "replacement_package_set_authority_record_enabled": False,
        "package_supersession_commit_enabled": False,
        "replacement_artifact_manifest_record_enabled": False,
        "replacement_namespace_record_enabled": False,
        "source_widening_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_url_enabled": False,
        "qualitative_hybrid_rag_execution_enabled": False,
        "frontend_only_durable_state_enabled": False,
        "downstream_unavailable": list(REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_DOWNSTREAM_UNAVAILABLE),
        "next_state": REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_STATE,
        "created_at": utc_isoformat(materialization.created_at),
        "updated_at": utc_isoformat(materialization.updated_at),
        "authority_rail": {
            "server_owned_materialization": True,
            "artifact_namespace": REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
            "hash_algorithm": REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
            "package_rows_mutated": False,
            "source_payloads_rewritten": False,
            "replacement_authority_recorded": False,
            "supersession_committed": False,
            "manifest_recorded": False,
            "namespace_rows_recorded": False,
            "connector_dispatch_enabled": False,
        },
    }


def _source_payload_json(package: L3OutputPackage) -> Any:
    ref = _string(package.payload_ref)
    try:
        source_path = Path(ref).resolve(strict=True)
    except FileNotFoundError as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_materialization_source_payload_ref_missing",
            "Source package payload ref is missing and cannot be materialized.",
            status="blocked",
            http_status=409,
            blocked_fields=["source_payload_refs"],
            next_allowed_actions=["inspect_package_payload_refs"],
        ) from exc
    if not source_path.is_file():
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_materialization_source_payload_ref_unreadable",
            "Source package payload ref is not a readable file.",
            status="blocked",
            http_status=409,
            blocked_fields=["source_payload_refs"],
            next_allowed_actions=["inspect_package_payload_refs"],
        )
    payload_bytes = source_path.read_bytes()
    if hashlib.sha256(payload_bytes).hexdigest() != package.payload_hash:
        _raise_mismatch(
            "replacement_package_artifact_materialization_source_payload_hash_mismatch",
            "source_payload_hashes",
            "Source package payload bytes do not match immutable package authority.",
        )
    try:
        return json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_materialization_source_payload_not_json",
            "Source package payload must be server-readable JSON before replacement materialization.",
            status="blocked",
            http_status=409,
            blocked_fields=["source_payload_refs"],
            next_allowed_actions=["inspect_package_payload_refs"],
        ) from exc


def _write_replacement_artifact(
    *,
    session_id: str,
    package_supersession_preview_hash: str,
    replacement_package_set_id: str,
    package: L3OutputPackage,
) -> tuple[str, str]:
    payload = {
        "schema_id": "layer3.replacement_package_artifact.v1",
        "materialization_schema_id": REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_SCHEMA_ID,
        "materialization_mode": REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_MODE,
        "package_supersession_preview_hash": package_supersession_preview_hash,
        "replacement_package_set_id": replacement_package_set_id,
        "package_kind": package.package_kind,
        "source_output_package_id": package.output_package_id,
        "source_payload_hash": package.payload_hash,
        "source_package_payload": _source_payload_json(package),
        "negative_invariants": {
            "source_l3_output_package_mutated": False,
            "source_package_payload_rewritten": False,
            "browser_package_bytes_accepted": False,
        },
    }
    payload_bytes = stable_json_bytes(payload)
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    artifact_path = _artifact_path(
        session_id=session_id,
        package_supersession_preview_hash=package_supersession_preview_hash,
        package_kind=package.package_kind,
        payload_hash=payload_hash,
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    if artifact_path.exists():
        if artifact_path.read_bytes() != payload_bytes:
            _raise_mismatch(
                "replacement_package_artifact_materialization_existing_output_conflict",
                "source_payload_refs",
                "Existing replacement artifact path contains conflicting bytes.",
            )
    else:
        artifact_path.write_bytes(payload_bytes)
    return str(artifact_path.resolve(strict=True)), payload_hash


def materialize_replacement_package_artifacts(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = _string(payload.get("client_request_id"))
    if not request_id:
        raise layer3_workbench.Layer3WorkbenchError(
            "client_request_id_required",
            "client_request_id is required for replacement package artifact materialization.",
            status="invalid",
            blocked_fields=["client_request_id"],
            next_allowed_actions=["submit_complete_replacement_package_artifact_materialization_request"],
        )

    unknown = sorted(
        key for key in payload if key not in REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_ALLOWED_FIELDS
    )
    forbidden = sorted(
        key for key in REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_FORBIDDEN_FIELDS if key in payload
    )
    blocked_payload_fields = sorted(set(unknown) | set(forbidden))
    if blocked_payload_fields:
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_materialization_scope_not_admitted",
            "Replacement package artifact materialization request includes non-admitted fields: "
            + ", ".join(blocked_payload_fields)
            + ".",
            status="invalid",
            blocked_fields=blocked_payload_fields,
            next_allowed_actions=["submit_materialization_request_source_only_request"],
        )

    missing = sorted(
        field
        for field in REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_REQUIRED_FIELDS
        if field not in payload or payload.get(field) in (None, "", [])
    )
    if missing:
        raise layer3_workbench.Layer3WorkbenchError(
            "missing_replacement_package_artifact_materialization_fields",
            "Replacement package artifact materialization request is missing required fields: "
            + ", ".join(missing)
            + ".",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_replacement_package_artifact_materialization_request"],
        )

    if _string(payload.get("operator_decision")) != REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_OPERATOR_DECISION:
        raise layer3_workbench.Layer3WorkbenchError(
            "unsupported_replacement_package_artifact_materialization_decision",
            "operator_decision must be materialize_replacement_package_artifacts_from_supersession_preview.",
            status="invalid",
            blocked_fields=["operator_decision"],
        )

    existing_for_request = (
        db.query(L3ReplacementPackageArtifactMaterialization)
        .filter(L3ReplacementPackageArtifactMaterialization.client_request_id == request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        if not _payload_matches_existing_request(payload=payload, existing=existing_for_request):
            _raise_mismatch(
                "replacement_package_artifact_materialization_client_request_conflict",
                "client_request_id",
                "client_request_id already materialized a different replacement artifact basis.",
            )
        return _materialization_response(
            request_id=request_id,
            status="already_materialized",
            materialization=existing_for_request,
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
            "replacement_package_artifact_materialization_requires_existing_authority",
            "Replacement package artifact materialization requires existing session, plan, pass, and reconciliation authority.",
            status="blocked",
            http_status=409,
            blocked_fields=["session_id", "analysis_plan_id", "pass_run_id", "reconciliation_record_id"],
            next_allowed_actions=["inspect_existing_package_state"],
        )
    if pass_run.session_id != session_id or pass_run.analysis_plan_id != analysis_plan_id:
        _raise_mismatch(
            "replacement_package_artifact_materialization_pass_run_mismatch",
            "pass_run_id",
            "pass_run_id must belong to the supplied session and analysis plan.",
        )

    reconciliation_summary = reconciliation.summary_json or {}
    commit_summary = reconciliation_summary.get("workbench_package_commit")
    if not isinstance(commit_summary, dict):
        raise layer3_workbench.Layer3WorkbenchError(
            "replacement_package_artifact_materialization_requires_package_construction",
            "Replacement package artifact materialization requires existing workbench package-construction provenance.",
            status="blocked",
            http_status=409,
            blocked_fields=["reconciliation_record_id"],
            next_allowed_actions=["inspect_existing_package_state"],
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
    for field, expected_values in (
        ("source_output_package_ids", source_output_package_ids),
        ("source_package_kinds", source_package_kinds),
        ("source_payload_refs", source_payload_refs),
        ("source_payload_hashes", source_payload_hashes),
    ):
        _validate_supplied_list(payload=payload, field=field, expected_values=expected_values)

    source_package_set_hash = stable_hash(
        {
            "schema_id": "layer3.package_supersession_source_package_set.v1",
            "session_id": session_id,
            "reconciliation_record_id": reconciliation_record_id,
            "output_packages": [_package_row_projection(package) for package in ordered_packages],
        }
    )
    if _string(payload.get("source_package_set_hash")) != source_package_set_hash:
        _raise_mismatch(
            "replacement_package_artifact_materialization_source_package_set_hash_mismatch",
            "source_package_set_hash",
            "Supplied source_package_set_hash does not match immutable source package authority.",
        )

    downstream_dependencies = _downstream_dependencies_from_reconciliation(reconciliation)
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
            "replacement_package_artifact_materialization_preview_hash_mismatch",
            "package_supersession_preview_hash",
            "Supplied package_supersession_preview_hash does not match current package supersession preview authority.",
        )

    replacement_package_set_id = stable_id(
        "replacement-set",
        {
            "session_id": session_id,
            "reconciliation_record_id": reconciliation_record_id,
            "package_supersession_preview_hash": computed_preview_hash,
            "source_package_set_hash": source_package_set_hash,
        },
        digest_chars=24,
    )
    replacement_package_kinds = list(REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_PACKAGE_KINDS)
    replacement_payload_refs: list[str] = []
    replacement_payload_hashes: list[str] = []
    artifact_rows: list[dict[str, Any]] = []
    for package in ordered_packages:
        artifact_ref, artifact_hash = _write_replacement_artifact(
            session_id=session_id,
            package_supersession_preview_hash=computed_preview_hash,
            replacement_package_set_id=replacement_package_set_id,
            package=package,
        )
        replacement_payload_refs.append(artifact_ref)
        replacement_payload_hashes.append(artifact_hash)
        artifact_rows.append(
            {
                "package_kind": package.package_kind,
                "source_output_package_id": package.output_package_id,
                "replacement_payload_ref": artifact_ref,
                "replacement_payload_hash": artifact_hash,
            }
        )

    replacement_package_set_hash = layer3_replacement_package_set_authority.replacement_package_set_hash(
        replacement_package_set_id=replacement_package_set_id,
        replacement_package_kinds=replacement_package_kinds,
        replacement_payload_refs=replacement_payload_refs,
        replacement_payload_hashes=replacement_payload_hashes,
    )
    authority_basis_hash = (
        layer3_replacement_package_set_authority.replacement_package_set_authority_basis_hash(
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
            replacement_package_set_hash=replacement_package_set_hash,
            replacement_package_kinds=replacement_package_kinds,
            replacement_payload_refs=replacement_payload_refs,
            replacement_payload_hashes=replacement_payload_hashes,
        )
    )
    materialization_basis_hash = stable_hash(
        {
            "schema_id": "layer3.replacement_package_artifact_materialization_basis.v1",
            "mode": REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_MODE,
            "operator_decision": REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_OPERATOR_DECISION,
            "session_id": session_id,
            "analysis_plan_id": analysis_plan_id,
            "pass_run_id": pass_run_id,
            "reconciliation_record_id": reconciliation_record_id,
            "package_supersession_preview_hash": computed_preview_hash,
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
            "authority_basis_hash": authority_basis_hash,
        }
    )

    existing_for_basis = (
        db.query(L3ReplacementPackageArtifactMaterialization)
        .filter(
            L3ReplacementPackageArtifactMaterialization.materialization_basis_hash
            == materialization_basis_hash
        )
        .one_or_none()
    )
    if existing_for_basis is not None:
        return _materialization_response(
            request_id=request_id,
            status="already_materialized",
            materialization=existing_for_basis,
        )

    now = utcnow()
    snapshot = {
        "schema_id": "layer3.replacement_package_artifact_materialization_snapshot.v1",
        "mode": REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_MODE,
        "source_gate": REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_SOURCE_GATE,
        "package_supersession_preview_hash": computed_preview_hash,
        "source": {
            "package_set_hash": source_package_set_hash,
            "output_package_ids": source_output_package_ids,
            "package_kinds": source_package_kinds,
            "payload_refs": source_payload_refs,
            "payload_hashes": source_payload_hashes,
        },
        "replacement": {
            "replacement_package_set_id": replacement_package_set_id,
            "replacement_package_set_hash": replacement_package_set_hash,
            "package_kinds": replacement_package_kinds,
            "payload_refs": replacement_payload_refs,
            "payload_hashes": replacement_payload_hashes,
            "authority_basis_hash": authority_basis_hash,
        },
        "artifacts": {
            "artifact_namespace": REPLACEMENT_PACKAGE_ARTIFACT_NAMESPACE,
            "hash_algorithm": REPLACEMENT_PACKAGE_ARTIFACT_HASH_ALGORITHM,
            "rows": artifact_rows,
        },
        "negative_invariants": {
            "creates_l3_output_package": False,
            "mutates_l3_output_package": False,
            "rewrites_source_package_payload": False,
            "records_replacement_package_set_authority": False,
            "commits_package_supersession": False,
            "records_replacement_artifact_manifest": False,
            "records_replacement_namespace": False,
            "accepts_browser_package_bytes": False,
            "accepts_browser_replacement_refs_or_hashes": False,
            "enables_connector_dispatch": False,
            "enables_source_widening": False,
            "enables_qualitative_hybrid_rag": False,
            "enables_provider_public_url": False,
        },
    }

    materialization = L3ReplacementPackageArtifactMaterialization(
        client_request_id=request_id,
        session_id=session_id,
        analysis_plan_id=analysis_plan_id,
        pass_run_id=pass_run_id,
        reconciliation_record_id=reconciliation_record_id,
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
        authority_basis_hash=authority_basis_hash,
        materialization_basis_hash=materialization_basis_hash,
        materialization_snapshot_json=snapshot,
        operator_decision=REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_OPERATOR_DECISION,
        status=REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_STATUS,
        created_at=now,
        updated_at=now,
    )
    db.add(materialization)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_for_request = (
            db.query(L3ReplacementPackageArtifactMaterialization)
            .filter(L3ReplacementPackageArtifactMaterialization.client_request_id == request_id)
            .one_or_none()
        )
        if existing_for_request is not None:
            if existing_for_request.materialization_basis_hash == materialization_basis_hash:
                return _materialization_response(
                    request_id=request_id,
                    status="already_materialized",
                    materialization=existing_for_request,
                )
            raise Layer3WorkbenchError(
                "replacement_package_artifact_materialization_client_request_conflict",
                "client_request_id already belongs to a different replacement package artifact materialization.",
                status="conflict",
                http_status=409,
                blocked_fields=["client_request_id"],
                next_allowed_actions=["submit_new_client_request_id"],
            )
        existing = (
            db.query(L3ReplacementPackageArtifactMaterialization)
            .filter(
                L3ReplacementPackageArtifactMaterialization.materialization_basis_hash
                == materialization_basis_hash
            )
            .one_or_none()
        )
        if existing is not None:
            return _materialization_response(
                request_id=request_id,
                status="already_materialized",
                materialization=existing,
            )
        raise
    db.refresh(materialization)
    return _materialization_response(
        request_id=request_id,
        status=REPLACEMENT_PACKAGE_ARTIFACT_MATERIALIZATION_STATUS,
        materialization=materialization,
    )
