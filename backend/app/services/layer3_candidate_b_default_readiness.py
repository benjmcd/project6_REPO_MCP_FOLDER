from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_runtime_bridge,
    layer3_candidate_b_visual_lane_status,
)


SCHEMA_ID = "layer3.candidate_b_default_promotion_readiness_audit.v1"
SCHEMA_VERSION = 1
READINESS_MODE = "candidate_b_default_promotion_readiness_audit_v1"
READY_STATE = "candidate_b_default_promotion_ready_for_separate_selection"
BLOCKED_STATE = "candidate_b_default_promotion_readiness_blocked"
CANDIDATE_A_VARIANT = "candidate_a_page_evidence_v1"
CANDIDATE_B_ENGINE = "candidate_b_opendataloader_pdf"
CANDIDATE_B_VISUAL_LANE_MODE = layer3_candidate_b_runtime_bridge.CANDIDATE_B_VISUAL_LANE_MODE
ELIGIBLE_CORPUS_SCOPE = "candidate_b_opendataloader_pdf_eligible_pdf_corpus_processing_only"
REGRESSION_DISPOSITION_READY = "no_unacceptable_regression_against_baseline_and_candidate_a"

_BUNDLE_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "bridge_mode",
    "candidate_b_bundle_id",
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_source_kind",
    "compare_target_set_hash",
    "bundle_file_manifest_hash",
    "bundle_raw_file_manifest_hash",
    "admitted_file_subset_source_hash",
    "admitted_file_subset_hash",
    "governed_retained_artifact_family_hash",
    "redaction_policy_id",
)
_RUNTIME_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "bridge_mode",
    "candidate_b_run_id",
    "baseline_run_id",
    "candidate_a_run_id",
    "candidate_b_source_kind",
    "document_processing_engine",
    "visual_lane_mode",
    "compare_target_set_hash",
    "runtime_review_root_storage_authority_hash",
    "admitted_file_subset_hash",
    "governed_retained_artifact_family_hash",
    "redaction_policy_id",
)
_REQUIRED_COVERAGE = frozenset(
    {
        "source_directory_scan",
        "material_preview",
        "gate_b",
        "hybrid_qualitative_analysis",
        "package_commit",
        "package_review_submit",
        "handoff_export_prepare",
        "external_export_download_prepare",
        "same_origin_delivery_status",
        "same_origin_delivery",
        "provider_private_prepare",
        "provider_private_status",
        "provider_private_use",
        "provider_private_revoke",
        "internal_webhook_dispatch",
        "internal_webhook_status",
        "session_status_projection",
    }
)
_FORBIDDEN_REQUEST_FIELDS = {
    "path",
    "paths",
    "directory",
    "local_directory",
    "local_path",
    "url",
    "urls",
    "glob",
    "recursive",
    "file",
    "files",
    "file_bytes",
    "visual_lane_mode",
    "document_processing_engine",
    "default_selector",
    "make_default",
    "candidate_b_default",
    "candidate_b_default_enabled",
    "candidate_b_default_promotion_enabled",
    "runtime_database_path",
    "runtime_storage_dir",
    "database_path",
    "storage_dir",
    "provider_public_url",
    "provider_private_url",
    "provider_private_signed_url_token",
    "connector_dispatch",
    "rag_vector_index",
    "browser_storage",
}


class CandidateBDefaultReadinessError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-default-readiness-error",
            "server_time": _server_time(),
            "mode": READINESS_MODE,
            "status": "blocked",
            "readiness_state": BLOCKED_STATE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def evaluate_candidate_b_default_promotion_readiness(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    readiness_mode = _required(fields, "readiness_mode")
    if readiness_mode != READINESS_MODE:
        raise CandidateBDefaultReadinessError(
            "candidate_b_default_readiness_mode_not_admitted",
            "Only the frozen Candidate B default-promotion readiness audit mode is admitted.",
            details={"expected_readiness_mode": READINESS_MODE, "received_readiness_mode": readiness_mode},
        )

    baseline_run_id = _required(fields, "baseline_run_id")
    candidate_a_run_id = _required(fields, "candidate_a_run_id")
    candidate_b_bundle_id = _required(fields, "candidate_b_bundle_id")
    candidate_b_run_id = _required(fields, "candidate_b_run_id")
    bundle_receipt_id = _required(fields, "candidate_b_bundle_bridge_receipt_id")
    runtime_receipt_id = _required(fields, "candidate_b_runtime_bridge_receipt_id")

    blocked: list[dict[str, Any]] = []
    _required_ready_value(
        blocked,
        "eligible_corpus_scope",
        str(fields.get("eligible_corpus_scope") or "").strip(),
        ELIGIBLE_CORPUS_SCOPE,
        "candidate_b_default_readiness_eligible_scope_not_admitted",
    )
    _required_ready_value(
        blocked,
        "regression_disposition",
        str(fields.get("regression_disposition") or "").strip(),
        REGRESSION_DISPOSITION_READY,
        "candidate_b_default_readiness_regression_disposition_not_ready",
    )
    if fields.get("operator_confirmation") is not True:
        blocked.append(_reason("candidate_b_default_readiness_operator_confirmation_missing"))
    if fields.get("rollback_to_baseline_confirmation") is not True:
        blocked.append(_reason("candidate_b_default_readiness_rollback_to_baseline_missing"))

    bundle_receipt = _validate_receipt(
        kind="bundle",
        receipt_id=bundle_receipt_id,
        expected={
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_bundle_id": candidate_b_bundle_id,
        },
    )
    runtime_receipt = _validate_receipt(
        kind="runtime",
        receipt_id=runtime_receipt_id,
        expected={
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_run_id": candidate_b_run_id,
        },
    )
    bundle_proof = _validate_downstream_proof(
        fields.get("bundle_downstream_proof"),
        source_kind="bundle",
        bridge_receipt_id=bundle_receipt_id,
    )
    runtime_proof = _validate_downstream_proof(
        fields.get("runtime_downstream_proof"),
        source_kind="runtime",
        bridge_receipt_id=runtime_receipt_id,
    )
    visual_lane_status = _validate_visual_lane_status_evidence(
        fields.get("candidate_b_visual_lane_status_evidence"),
        candidate_b_run_id=candidate_b_run_id,
        runtime_receipt_id=runtime_receipt_id,
        runtime_receipt_hash=runtime_receipt["authority_hashes"].get("bridge_receipt_hash"),
    )
    operator_status = _validate_operator_status(fields.get("operator_status_evidence"))
    blocked.extend(bundle_receipt["blocked_reasons"])
    blocked.extend(runtime_receipt["blocked_reasons"])
    blocked.extend(bundle_proof["blocked_reasons"])
    blocked.extend(runtime_proof["blocked_reasons"])
    blocked.extend(visual_lane_status["blocked_reasons"])
    blocked.extend(operator_status["blocked_reasons"])

    audit_hash = _stable_hash(
        {
            "hash_version": "candidate_b_default_readiness_audit_hash_v1",
            "readiness_mode": READINESS_MODE,
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_bundle_id": candidate_b_bundle_id,
            "candidate_b_run_id": candidate_b_run_id,
            "bundle_bridge_receipt_id": bundle_receipt_id,
            "bundle_bridge_receipt_hash": bundle_receipt["authority_hashes"].get("bridge_receipt_hash"),
            "runtime_bridge_receipt_id": runtime_receipt_id,
            "runtime_bridge_receipt_hash": runtime_receipt["authority_hashes"].get("bridge_receipt_hash"),
            "bundle_downstream_proof_hash": bundle_proof["proof_hash"],
            "runtime_downstream_proof_hash": runtime_proof["proof_hash"],
            "candidate_b_visual_lane_status_hash": visual_lane_status["status_hash"],
            "eligible_corpus_scope": fields.get("eligible_corpus_scope"),
            "regression_disposition": fields.get("regression_disposition"),
            "rollback_to_baseline_confirmation": fields.get("rollback_to_baseline_confirmation") is True,
            "operator_status_hash": operator_status["operator_status_hash"],
        }
    )
    readiness_state = READY_STATE if not blocked else BLOCKED_STATE

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "ready" if readiness_state == READY_STATE else "blocked",
        "mode": READINESS_MODE,
        "readiness_state": readiness_state,
        "readiness_audit_id": f"cb-default-readiness-{audit_hash[:24]}",
        "readiness_audit_hash": audit_hash,
        "blocked_reasons": blocked,
        "baseline_current_default_evidence": {
            "default_visual_lane_mode": "baseline",
            "document_processing_engine_default": CANDIDATE_B_ENGINE,
            "document_processing_engine_default_scope": ELIGIBLE_CORPUS_SCOPE,
            "non_pdf_document_processing_engine_default": "baseline",
            "explicit_baseline_rollback_preserved": True,
            "baseline_default_scope": "visual_lane_and_non_pdf_processing",
            "baseline_default_changed": False,
        },
        "candidate_a_admitted_variant_evidence": {
            "visual_lane_mode": CANDIDATE_A_VARIANT,
            "candidate_a_semantics_changed": False,
        },
        "candidate_b_selector_evidence": {
            "candidate_b_family": CANDIDATE_B_ENGINE,
            "candidate_b_is_visual_lane_mode": True,
            "candidate_b_visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
            "candidate_b_visual_lane_mode_admitted": True,
            "candidate_b_is_default_visual_lane_mode": False,
            "candidate_b_visual_lane_selector_is_explicit": True,
            "candidate_b_default_for_eligible_pdf_when_engine_omitted": True,
            "candidate_b_runtime_selector_is_opt_in": True,
            "candidate_b_visual_lane_material_ingestion_enabled": False,
        },
        "selected_evidence": {
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "candidate_b_bundle_id": candidate_b_bundle_id,
            "candidate_b_run_id": candidate_b_run_id,
            "eligible_corpus_scope": fields.get("eligible_corpus_scope"),
        },
        "bridge_receipts": {"bundle": bundle_receipt["summary"], "runtime": runtime_receipt["summary"]},
        "compare_target_sets": {
            "bundle": bundle_receipt["compare_target_set"],
            "runtime": runtime_receipt["compare_target_set"],
        },
        "authority_hashes": {"bundle": bundle_receipt["authority_hashes"], "runtime": runtime_receipt["authority_hashes"]},
        "downstream_proofs": {"bundle": bundle_proof["summary"], "runtime": runtime_proof["summary"]},
        "candidate_b_visual_lane_status_evidence": visual_lane_status["summary"],
        "operator_status_evidence": operator_status["summary"],
        "rollback_to_baseline": {
            "available": fields.get("rollback_to_baseline_confirmation") is True,
            "selector": "baseline",
            "depends_on_candidate_b_artifacts": False,
        },
        "regression_disposition": fields.get("regression_disposition"),
        "fail_closed_behavior": {
            "missing_bridge_receipt_blocks_readiness": True,
            "stale_bridge_receipt_hash_blocks_readiness": True,
            "missing_downstream_proof_blocks_readiness": True,
            "missing_rollback_confirmation_blocks_readiness": True,
            "unacceptable_regression_blocks_readiness": True,
        },
        "default_selector_change_enabled": readiness_state == READY_STATE,
        "candidate_b_default_promotion_enabled": readiness_state == READY_STATE,
        "selector_mutation_performed": False,
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": (
            [
                "monitor_candidate_b_default_selector",
                "use_explicit_baseline_document_processing_engine_for_rollback",
            ]
            if readiness_state == READY_STATE
            else [
                "repair_or_prepare_missing_candidate_b_bridge_receipts",
                "rerun_bounded_candidate_b_layer3_downstream_proof",
                "record_no_unacceptable_regression_and_rollback_evidence",
            ]
        ),
    }


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBDefaultReadinessError(
            "candidate_b_default_readiness_forbidden_request_fields",
            "The readiness audit does not admit caller paths, selector mutation, visual-lane overrides, URLs, connectors, or browser authority.",
            details={"blocked_fields": blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBDefaultReadinessError(
            "candidate_b_default_readiness_required_field_missing",
            "A required Candidate B readiness field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_ready_value(
    blocked: list[dict[str, Any]],
    field: str,
    received: str,
    expected: str,
    code: str,
) -> None:
    if received != expected:
        blocked.append({"code": code, "field": field, "expected": expected, "received": received or None})


def _validate_receipt(*, kind: str, receipt_id: str, expected: Mapping[str, str]) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    receipt = _read_receipt(kind=kind, receipt_id=receipt_id, blocked=blocked)
    if receipt is None:
        return _receipt_result(kind=kind, receipt_id=receipt_id, blocked=blocked)

    schema_id = layer3_candidate_b_bundle_bridge.SCHEMA_ID if kind == "bundle" else layer3_candidate_b_runtime_bridge.SCHEMA_ID
    bridge_mode = layer3_candidate_b_bundle_bridge.BRIDGE_MODE if kind == "bundle" else layer3_candidate_b_runtime_bridge.BRIDGE_MODE
    _receipt_equals(blocked, kind, receipt, "schema_id", schema_id)
    _receipt_equals(blocked, kind, receipt, "bridge_mode", bridge_mode)
    _receipt_equals(blocked, kind, receipt, "candidate_b_source_kind", kind)
    _receipt_equals(blocked, kind, receipt, "bridge_receipt_id", receipt_id)
    for field, expected_value in expected.items():
        _receipt_equals(blocked, kind, receipt, field, expected_value)
    if kind == "runtime":
        _receipt_equals(blocked, kind, receipt, "document_processing_engine", CANDIDATE_B_ENGINE)
        _receipt_equals(blocked, kind, receipt, "visual_lane_mode", CANDIDATE_B_VISUAL_LANE_MODE)

    keys = _BUNDLE_HASH_KEYS if kind == "bundle" else _RUNTIME_HASH_KEYS
    missing = [key for key in keys if key not in receipt]
    if missing:
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_receipt_authority_field_missing", missing_fields=missing))
    else:
        expected_hash = _stable_hash({key: receipt[key] for key in keys})
        if receipt.get("bridge_receipt_hash") != expected_hash:
            blocked.append(
                _reason(
                    f"candidate_b_default_readiness_{kind}_receipt_hash_mismatch",
                    expected=expected_hash,
                    received=receipt.get("bridge_receipt_hash"),
                )
            )

    validation_key = "candidate_b_bundle_validation" if kind == "bundle" else "candidate_b_runtime_validation"
    validation = receipt.get(validation_key) if isinstance(receipt.get(validation_key), dict) else {}
    if validation.get("status") != "passed":
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_validation_not_passed", received=validation.get("status")))
    target_set = receipt.get("compare_target_set") if isinstance(receipt.get("compare_target_set"), dict) else {}
    if not target_set.get("fixture_ids") or int(target_set.get("target_count") or 0) <= 0:
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_compare_target_set_empty"))
    _validate_receipt_invariants(kind=kind, receipt=receipt, blocked=blocked)
    artifact_family = _validate_governed_artifact_family(kind=kind, receipt=receipt, blocked=blocked)
    if kind == "runtime":
        _validate_runtime_visual_lane_evidence(receipt=receipt, blocked=blocked)
    return _receipt_result(
        kind=kind,
        receipt_id=receipt_id,
        blocked=blocked,
        receipt=receipt,
        validation=validation,
        target_set=target_set,
        artifact_family=artifact_family,
    )


def _read_receipt(*, kind: str, receipt_id: str, blocked: list[dict[str, Any]]) -> dict[str, Any] | None:
    configured = settings.layer3_candidate_b_bundle_bridge_dir if kind == "bundle" else settings.layer3_candidate_b_runtime_bridge_dir
    if not str(configured or "").strip():
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_bridge_dir_unset"))
        return None
    root = Path(str(configured))
    if not root.is_absolute():
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_bridge_dir_not_absolute"))
        return None
    path = root / receipt_id / "receipt.json"
    if not path.is_file():
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_bridge_receipt_missing", bridge_receipt_id=receipt_id))
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_bridge_receipt_unreadable", reason=str(exc)))
        return None
    if not isinstance(payload, dict):
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_bridge_receipt_invalid"))
        return None
    return payload


def _receipt_equals(blocked: list[dict[str, Any]], kind: str, receipt: Mapping[str, Any], field: str, expected: str) -> None:
    received = str(receipt.get(field) or "").strip()
    if received != expected:
        blocked.append(
            _reason(
                f"candidate_b_default_readiness_{kind}_receipt_{field}_mismatch",
                field=field,
                expected=expected,
                received=received or None,
            )
        )


def _validate_receipt_invariants(*, kind: str, receipt: Mapping[str, Any], blocked: list[dict[str, Any]]) -> None:
    invariants = receipt.get("negative_invariants")
    if not isinstance(invariants, dict):
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_negative_invariants_missing"))
        return
    required_false = {
        "baseline_default_changed",
        "candidate_a_semantics_changed",
        "candidate_b_visual_lane_material_ingestion_enabled",
        "candidate_b_default_promotion_enabled",
        "pdf_ingestion_enabled",
        "image_ingestion_enabled",
        "provider_object_writes_enabled",
        "connector_dispatch_enabled",
        "rag_vector_model_runtime_enabled",
        "browser_storage_authority_enabled",
        "frontend_durable_authority_enabled",
        "full_mockup_activation_enabled",
    }
    failed = sorted(key for key in required_false if invariants.get(key) is not False)
    if failed:
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_negative_invariant_failed", fields=failed))


def _receipt_result(
    *,
    kind: str,
    receipt_id: str,
    blocked: list[dict[str, Any]],
    receipt: Mapping[str, Any] | None = None,
    validation: Mapping[str, Any] | None = None,
    target_set: Mapping[str, Any] | None = None,
    artifact_family: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    target_set = target_set or {}
    return {
        "blocked_reasons": blocked,
        "summary": {
            "bridge_receipt_id": receipt_id,
            "bridge_receipt_ref": f"candidate-b-{kind}-bridge://{receipt_id}/receipt.json",
            "bridge_receipt_hash": receipt.get("bridge_receipt_hash"),
            "candidate_b_source_kind": kind,
            "validation": dict(validation or {}),
            "layer3_material_preview_compatible": bool(
                receipt.get("layer3_compatibility", {}).get("material_preview_uses_existing_hash_checks")
            ),
            "gate_b_material_authority_compatible": bool(
                receipt.get("layer3_compatibility", {}).get("gate_b_uses_existing_decision_basis_validation")
            ),
            "raw_local_path_exposed": False,
            "governed_retained_artifact_family_hash": receipt.get("governed_retained_artifact_family_hash"),
            **_runtime_visual_lane_summary(kind=kind, receipt=receipt),
        },
        "compare_target_set": {
            key: target_set.get(key)
            for key in (
                "candidate_b_source_kind",
                "baseline_run_id",
                "candidate_a_run_id",
                "candidate_b_bundle_id",
                "candidate_b_run_id",
                "fixture_ids",
                "target_count",
                "compare_target_set_hash",
            )
            if key in target_set
        },
        "authority_hashes": _authority_hashes(kind=kind, receipt=receipt),
        "governed_retained_artifact_family": _artifact_family_summary(artifact_family),
    }


def _runtime_visual_lane_summary(*, kind: str, receipt: Mapping[str, Any]) -> dict[str, Any]:
    if kind != "runtime":
        return {}
    evidence = receipt.get("candidate_b_visual_lane_evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    return {
        "visual_lane_mode": receipt.get("visual_lane_mode"),
        "candidate_b_visual_lane_evidence": {
            "visual_lane_mode": evidence.get("visual_lane_mode"),
            "candidate_b_visual_lane_selected": evidence.get("candidate_b_visual_lane_selected") is True,
            "candidate_b_visual_ref_total": int(evidence.get("candidate_b_visual_ref_total") or 0),
            "candidate_b_retained_source_pdf_ref_count": int(
                evidence.get("candidate_b_retained_source_pdf_ref_count") or 0
            ),
            "source_pdf_material_text_payload_enabled": evidence.get("source_pdf_material_text_payload_enabled") is True,
            "image_material_text_payload_enabled": evidence.get("image_material_text_payload_enabled") is True,
        },
    }


def _validate_runtime_visual_lane_evidence(
    *,
    receipt: Mapping[str, Any],
    blocked: list[dict[str, Any]],
) -> None:
    evidence = receipt.get("candidate_b_visual_lane_evidence")
    if not isinstance(evidence, dict):
        blocked.append(_reason("candidate_b_default_readiness_runtime_visual_lane_evidence_missing"))
        return
    if str(evidence.get("visual_lane_mode") or "").strip() != CANDIDATE_B_VISUAL_LANE_MODE:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_runtime_visual_lane_evidence_mode_mismatch",
                expected=CANDIDATE_B_VISUAL_LANE_MODE,
                received=evidence.get("visual_lane_mode"),
            )
        )
    if evidence.get("candidate_b_visual_lane_selected") is not True:
        blocked.append(_reason("candidate_b_default_readiness_runtime_visual_lane_not_selected"))
    for field in ("source_pdf_material_text_payload_enabled", "image_material_text_payload_enabled"):
        if evidence.get(field) is not False:
            blocked.append(_reason(f"candidate_b_default_readiness_runtime_visual_lane_{field}_not_false", field=field))


def _validate_governed_artifact_family(
    *,
    kind: str,
    receipt: Mapping[str, Any],
    blocked: list[dict[str, Any]],
) -> Mapping[str, Any]:
    artifact_family = receipt.get("governed_retained_artifact_family")
    if not isinstance(artifact_family, dict):
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_governed_artifact_family_missing"))
        return {}
    expected_hash = str(receipt.get("governed_retained_artifact_family_hash") or "").strip()
    received_hash = str(artifact_family.get("artifact_family_hash") or "").strip()
    if len(expected_hash) != 64 or received_hash != expected_hash:
        blocked.append(
            _reason(
                f"candidate_b_default_readiness_{kind}_governed_artifact_family_hash_mismatch",
                expected=expected_hash or None,
                received=received_hash or None,
            )
        )
    for field in ("pdf_material_text_payload_enabled", "image_material_text_payload_enabled", "raw_url_exposure_enabled"):
        if artifact_family.get(field) is not False:
            blocked.append(_reason(f"candidate_b_default_readiness_{kind}_{field}_not_false", field=field))
    roles = artifact_family.get("roles")
    required_roles = {
        "material_analysis_payloads",
        "visual_page_evidence",
        "provenance_audit_artifacts",
        "product_inspection_artifacts",
        "delivery_artifacts",
    }
    if not isinstance(roles, dict):
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_governed_artifact_roles_missing"))
    else:
        missing_roles = sorted(role for role in required_roles if role not in roles)
        if missing_roles:
            blocked.append(
                _reason(
                    f"candidate_b_default_readiness_{kind}_governed_artifact_roles_incomplete",
                    missing_roles=missing_roles,
                )
            )
        if not isinstance(roles.get("material_analysis_payloads"), list) or not roles["material_analysis_payloads"]:
            blocked.append(_reason(f"candidate_b_default_readiness_{kind}_material_payload_artifacts_missing"))
        if not isinstance(roles.get("provenance_audit_artifacts"), list) or not roles["provenance_audit_artifacts"]:
            blocked.append(_reason(f"candidate_b_default_readiness_{kind}_provenance_artifacts_missing"))
    return artifact_family


def _artifact_family_summary(artifact_family: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact_family, Mapping):
        return {"available": False}
    return {
        "available": True,
        "policy": artifact_family.get("policy"),
        "artifact_family_hash": artifact_family.get("artifact_family_hash"),
        "role_counts": artifact_family.get("role_counts") if isinstance(artifact_family.get("role_counts"), dict) else {},
        "pdf_material_text_payload_enabled": artifact_family.get("pdf_material_text_payload_enabled") is True,
        "image_material_text_payload_enabled": artifact_family.get("image_material_text_payload_enabled") is True,
        "raw_url_exposure_enabled": artifact_family.get("raw_url_exposure_enabled") is True,
    }


def _authority_hashes(*, kind: str, receipt: Mapping[str, Any]) -> dict[str, str]:
    keys = (
        (
            "bridge_receipt_hash",
            "compare_target_set_hash",
            "bundle_file_manifest_hash",
            "bundle_raw_file_manifest_hash",
            "admitted_file_subset_source_hash",
            "admitted_file_subset_hash",
            "governed_retained_artifact_family_hash",
        )
        if kind == "bundle"
        else (
            "bridge_receipt_hash",
            "compare_target_set_hash",
            "runtime_review_root_storage_authority_hash",
            "admitted_file_subset_hash",
            "governed_retained_artifact_family_hash",
        )
    )
    return {key: str(receipt[key]) for key in keys if receipt.get(key)}


def _validate_downstream_proof(proof: Any, *, source_kind: str, bridge_receipt_id: str) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    if not isinstance(proof, dict):
        return {
            "blocked_reasons": [_reason(f"candidate_b_default_readiness_{source_kind}_downstream_proof_missing")],
            "proof_hash": None,
            "summary": {"candidate_b_source_kind": source_kind, "coverage": [], "raw_local_path_exposed": False},
        }
    for field, expected in {
        "candidate_b_source_kind": source_kind,
        "bridge_receipt_id": bridge_receipt_id,
        "proof_state": "candidate_b_layer3_downstream_e2e_proven",
    }.items():
        if str(proof.get(field) or "").strip() != expected:
            blocked.append(_reason(f"candidate_b_default_readiness_{source_kind}_downstream_{field}_mismatch", field=field))
    for field in (
        "raw_local_path_exposed",
        "provider_private_token_exposed",
        "provider_public_url_enabled",
        "provider_object_writes_enabled",
        "connector_dispatch_enabled",
        "candidate_b_default_promotion_enabled",
    ):
        if proof.get(field) is not False:
            blocked.append(_reason(f"candidate_b_default_readiness_{source_kind}_downstream_{field}_not_false", field=field))
    if source_kind == "runtime":
        if proof.get("visual_lane_mode_enabled") is not True:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_runtime_downstream_visual_lane_mode_not_enabled",
                    field="visual_lane_mode_enabled",
                )
            )
        if str(proof.get("visual_lane_mode") or "").strip() != CANDIDATE_B_VISUAL_LANE_MODE:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_runtime_downstream_visual_lane_mode_mismatch",
                    expected=CANDIDATE_B_VISUAL_LANE_MODE,
                    received=proof.get("visual_lane_mode"),
                )
            )
    elif proof.get("visual_lane_mode_enabled") is not False:
        blocked.append(
            _reason(
                f"candidate_b_default_readiness_{source_kind}_downstream_visual_lane_mode_enabled_not_false",
                field="visual_lane_mode_enabled",
            )
        )
    coverage = _coverage_values(proof.get("coverage"))
    missing = sorted(_REQUIRED_COVERAGE.difference(coverage))
    if missing:
        blocked.append(_reason(f"candidate_b_default_readiness_{source_kind}_downstream_coverage_incomplete", missing_coverage=missing))
    proof_hash = str(proof.get("proof_hash") or _stable_hash(proof)).strip()
    if len(proof_hash) != 64:
        blocked.append(_reason(f"candidate_b_default_readiness_{source_kind}_downstream_proof_hash_invalid", received=proof_hash or None))
    return {
        "blocked_reasons": blocked,
        "proof_hash": proof_hash,
        "summary": {
            "candidate_b_source_kind": source_kind,
            "bridge_receipt_id": proof.get("bridge_receipt_id"),
            "proof_state": proof.get("proof_state"),
            "proof_hash": proof_hash,
            "coverage": sorted(coverage),
            "missing_coverage": missing,
            "raw_local_path_exposed": proof.get("raw_local_path_exposed") is True,
            "provider_private_token_exposed": proof.get("provider_private_token_exposed") is True,
            "visual_lane_mode_enabled": proof.get("visual_lane_mode_enabled") is True,
            "visual_lane_mode": proof.get("visual_lane_mode"),
        },
    }


def _coverage_values(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    out: set[str] = set()
    for item in value:
        if isinstance(item, str) and item.strip():
            out.add(item.strip())
        elif isinstance(item, dict):
            step = str(item.get("step") or item.get("name") or "").strip()
            if step:
                out.add(step)
    return out


def _validate_operator_status(value: Any) -> dict[str, Any]:
    evidence = value if isinstance(value, dict) else {}
    required_true = (
        "operator_visible_provenance_status",
        "bundle_status_projection_visible",
        "runtime_status_projection_visible",
        "default_selector_change_visible_as_enabled",
    )
    summary = {key: evidence.get(key) is True for key in required_true}
    summary["raw_local_path_exposed"] = evidence.get("raw_local_path_exposed") is True
    summary["provider_private_token_exposed"] = evidence.get("provider_private_token_exposed") is True
    blocked = []
    missing = [key for key in required_true if evidence.get(key) is not True]
    if missing:
        blocked.append(_reason("candidate_b_default_readiness_operator_status_evidence_incomplete", missing_fields=missing))
    if summary["raw_local_path_exposed"] or summary["provider_private_token_exposed"]:
        blocked.append(_reason("candidate_b_default_readiness_operator_status_exposes_sensitive_authority"))
    return {"blocked_reasons": blocked, "summary": summary, "operator_status_hash": _stable_hash(summary)}


def _validate_visual_lane_status_evidence(
    value: Any,
    *,
    candidate_b_run_id: str,
    runtime_receipt_id: str,
    runtime_receipt_hash: str | None,
) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    if not isinstance(value, dict):
        return {
            "blocked_reasons": [_reason("candidate_b_default_readiness_visual_lane_status_evidence_missing")],
            "status_hash": None,
            "summary": {"status": "missing"},
        }
    for field, expected in {
        "schema_id": layer3_candidate_b_visual_lane_status.SCHEMA_ID,
        "mode": layer3_candidate_b_visual_lane_status.STATUS_MODE,
        "status": "available",
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": candidate_b_run_id,
        "bridge_receipt_id": runtime_receipt_id,
        "bridge_receipt_hash": runtime_receipt_hash,
        "document_processing_engine": CANDIDATE_B_ENGINE,
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
        "visual_lane_status": "available",
    }.items():
        if str(value.get(field) or "").strip() != str(expected or "").strip():
            blocked.append(
                _reason(
                    f"candidate_b_default_readiness_visual_lane_status_{field}_mismatch",
                    field=field,
                    expected=expected,
                    received=value.get(field),
                )
            )

    visual_evidence = value.get("candidate_b_visual_lane_evidence")
    if not isinstance(visual_evidence, dict):
        blocked.append(_reason("candidate_b_default_readiness_visual_lane_status_evidence_detail_missing"))
        visual_evidence = {}
    if str(visual_evidence.get("visual_lane_mode") or "").strip() != CANDIDATE_B_VISUAL_LANE_MODE:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_visual_lane_status_evidence_mode_mismatch",
                expected=CANDIDATE_B_VISUAL_LANE_MODE,
                received=visual_evidence.get("visual_lane_mode"),
            )
        )
    if visual_evidence.get("candidate_b_visual_lane_selected") is not True:
        blocked.append(_reason("candidate_b_default_readiness_visual_lane_status_not_selected"))
    for field in ("source_pdf_material_text_payload_enabled", "image_material_text_payload_enabled"):
        if visual_evidence.get(field) is not False:
            blocked.append(_reason(f"candidate_b_default_readiness_visual_lane_status_{field}_not_false", field=field))

    operator_projection = value.get("operator_projection")
    if not isinstance(operator_projection, dict):
        blocked.append(_reason("candidate_b_default_readiness_visual_lane_status_operator_projection_missing"))
        operator_projection = {}
    for field in ("candidate_b_visual_lane_status_projection_visible", "candidate_b_visual_lane_selected"):
        if operator_projection.get(field) is not True:
            blocked.append(_reason(f"candidate_b_default_readiness_visual_lane_status_{field}_not_true", field=field))
    for field in ("raw_local_path_exposed", "raw_url_exposed", "artifact_bytes_exposed"):
        if operator_projection.get(field) is not False:
            blocked.append(_reason(f"candidate_b_default_readiness_visual_lane_status_{field}_not_false", field=field))

    material_policy = value.get("material_policy")
    if not isinstance(material_policy, dict):
        blocked.append(_reason("candidate_b_default_readiness_visual_lane_status_material_policy_missing"))
        material_policy = {}
    for field in (
        "source_pdf_material_text_payload_enabled",
        "image_material_text_payload_enabled",
        "visual_lane_material_ingestion_enabled",
    ):
        if material_policy.get(field) is not False:
            blocked.append(_reason(f"candidate_b_default_readiness_visual_lane_status_material_{field}_not_false", field=field))

    invariants = value.get("negative_invariants")
    if not isinstance(invariants, dict):
        blocked.append(_reason("candidate_b_default_readiness_visual_lane_status_negative_invariants_missing"))
        invariants = {}
    for field in (
        "candidate_b_default_promotion_enabled",
        "candidate_b_visual_lane_material_ingestion_enabled",
        "source_pdf_material_text_payload_enabled",
        "image_material_text_payload_enabled",
        "raw_url_exposure_enabled",
        "provider_object_writes_enabled",
        "connector_dispatch_enabled",
        "rag_vector_model_runtime_enabled",
        "browser_storage_authority_enabled",
        "frontend_durable_authority_enabled",
    ):
        if invariants.get(field) is not False:
            blocked.append(_reason(f"candidate_b_default_readiness_visual_lane_status_negative_{field}_not_false", field=field))

    status_hash = _stable_hash(value)
    return {
        "blocked_reasons": blocked,
        "status_hash": status_hash,
        "summary": {
            "status": value.get("status"),
            "mode": value.get("mode"),
            "candidate_b_run_id": value.get("candidate_b_run_id"),
            "bridge_receipt_id": value.get("bridge_receipt_id"),
            "bridge_receipt_hash": value.get("bridge_receipt_hash"),
            "visual_lane_mode": value.get("visual_lane_mode"),
            "visual_lane_status": value.get("visual_lane_status"),
            "candidate_b_visual_lane_status_projection_visible": (
                operator_projection.get("candidate_b_visual_lane_status_projection_visible") is True
            ),
            "candidate_b_visual_ref_total": int(operator_projection.get("candidate_b_visual_ref_total") or 0),
            "candidate_b_retained_source_pdf_ref_count": int(
                operator_projection.get("candidate_b_retained_source_pdf_ref_count") or 0
            ),
            "raw_local_path_exposed": operator_projection.get("raw_local_path_exposed") is True,
            "raw_url_exposed": operator_projection.get("raw_url_exposed") is True,
            "artifact_bytes_exposed": operator_projection.get("artifact_bytes_exposed") is True,
            "status_hash": status_hash,
        },
    }


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_non_pdf_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_visual_lane_mode_enabled": True,
        "candidate_b_visual_lane_default_enabled": False,
        "candidate_b_visual_lane_material_ingestion_enabled": False,
        "candidate_b_default_promotion_outside_eligible_pdf_enabled": False,
        "default_selector_changed_outside_eligible_pdf": False,
        "runtime_db_expansion_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "browser_storage_authority_enabled": False,
        "frontend_durable_authority_enabled": False,
        "full_mockup_activation_enabled": False,
    }


def _reason(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, **details}


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
