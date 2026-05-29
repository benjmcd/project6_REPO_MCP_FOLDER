from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_candidate_b_bundle_downstream_proof,
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_downstream_proof,
    layer3_candidate_b_operator_status,
    layer3_candidate_b_promotion_closure,
    layer3_candidate_b_runtime_bridge,
    layer3_candidate_b_storage_id,
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
    "candidate_b_visual_lane_evidence",
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
        candidate_b_bundle_id=candidate_b_bundle_id,
        bridge_receipt_hash=bundle_receipt["authority_hashes"].get("bridge_receipt_hash"),
    )
    visual_lane_status = _validate_visual_lane_status_evidence(
        fields.get("candidate_b_visual_lane_status_evidence"),
        candidate_b_run_id=candidate_b_run_id,
        runtime_receipt_id=runtime_receipt_id,
        runtime_receipt_hash=runtime_receipt["authority_hashes"].get("bridge_receipt_hash"),
    )
    runtime_proof = _validate_downstream_proof(
        fields.get("runtime_downstream_proof"),
        source_kind="runtime",
        bridge_receipt_id=runtime_receipt_id,
        candidate_b_run_id=candidate_b_run_id,
        bridge_receipt_hash=runtime_receipt["authority_hashes"].get("bridge_receipt_hash"),
        visual_lane_status_hash=visual_lane_status["status_hash"],
    )
    operator_status = _validate_operator_status(
        fields.get("operator_status_evidence"),
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_bundle_id=candidate_b_bundle_id,
        candidate_b_run_id=candidate_b_run_id,
        bundle_receipt_id=bundle_receipt_id,
        bundle_receipt_hash=bundle_receipt["authority_hashes"].get("bridge_receipt_hash"),
        runtime_receipt_id=runtime_receipt_id,
        runtime_receipt_hash=runtime_receipt["authority_hashes"].get("bridge_receipt_hash"),
        visual_lane_status_hash=visual_lane_status["status_hash"],
        runtime_downstream_proof_hash=runtime_proof["proof_hash"],
        runtime_retained_artifact_family_hash=runtime_receipt["authority_hashes"].get(
            "governed_retained_artifact_family_hash"
        ),
    )
    closure_evidence = _validate_closure_evidence(
        fields.get("closure_evidence"),
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_bundle_id=candidate_b_bundle_id,
        candidate_b_run_id=candidate_b_run_id,
        bundle_receipt_id=bundle_receipt_id,
        bundle_receipt_hash=bundle_receipt["authority_hashes"].get("bridge_receipt_hash"),
        runtime_receipt_id=runtime_receipt_id,
        runtime_receipt_hash=runtime_receipt["authority_hashes"].get("bridge_receipt_hash"),
        bundle_downstream_proof_hash=bundle_proof["proof_hash"],
        runtime_downstream_proof_hash=runtime_proof["proof_hash"],
        operator_status_hash=operator_status["operator_status_hash"],
        operator_status_projection=operator_status["summary"],
    )
    blocked.extend(bundle_receipt["blocked_reasons"])
    blocked.extend(runtime_receipt["blocked_reasons"])
    blocked.extend(
        _validate_compare_target_set_consistency(
            bundle_target_set=bundle_receipt["compare_target_authority"],
            runtime_target_set=runtime_receipt["compare_target_authority"],
        )
    )
    blocked.extend(bundle_proof["blocked_reasons"])
    blocked.extend(runtime_proof["blocked_reasons"])
    blocked.extend(visual_lane_status["blocked_reasons"])
    blocked.extend(operator_status["blocked_reasons"])
    blocked.extend(closure_evidence["blocked_reasons"])
    final_operator_inspection = _final_operator_inspection_evidence(
        bundle_receipt["governed_retained_artifact_family"],
        runtime_receipt["governed_retained_artifact_family"],
    )
    blocked.extend(
        _final_operator_artifact_count_reasons(
            kind="bundle",
            artifact_family=bundle_receipt["governed_retained_artifact_family"],
        )
    )
    blocked.extend(
        _final_operator_artifact_count_reasons(
            kind="runtime",
            artifact_family=runtime_receipt["governed_retained_artifact_family"],
        )
    )
    if final_operator_inspection.get("status") != "available":
        blocked.append(
            _reason(
                "candidate_b_default_readiness_final_operator_inspection_blocked",
                bundle_available=final_operator_inspection.get("bundle", {}).get("available") is True,
                runtime_available=final_operator_inspection.get("runtime", {}).get("available") is True,
            )
        )

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
            "bundle_downstream_proof_receipt_id": bundle_proof["summary"].get("proof_receipt_id"),
            "runtime_downstream_proof_hash": runtime_proof["proof_hash"],
            "runtime_downstream_proof_receipt_id": runtime_proof["summary"].get("proof_receipt_id"),
            "candidate_b_visual_lane_status_hash": visual_lane_status["status_hash"],
            "eligible_corpus_scope": fields.get("eligible_corpus_scope"),
            "regression_disposition": fields.get("regression_disposition"),
            "rollback_to_baseline_confirmation": fields.get("rollback_to_baseline_confirmation") is True,
            "operator_status_hash": operator_status["operator_status_hash"],
            "closure_evidence_hash": closure_evidence["closure_evidence_hash"],
            "final_operator_inspection_hash": final_operator_inspection["final_operator_inspection_hash"],
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
        "closure_evidence": closure_evidence["summary"],
        "candidate_b_final_operator_inspection_evidence": final_operator_inspection,
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
    _validate_compare_target_set(kind=kind, receipt=receipt, target_set=target_set, blocked=blocked)
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
    prefix = (
        layer3_candidate_b_bundle_bridge.BRIDGE_RECEIPT_PREFIX
        if kind == "bundle"
        else layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX
    )
    if not layer3_candidate_b_storage_id.is_storage_id(receipt_id, prefix=prefix):
        blocked.append(
            _reason(
                f"candidate_b_default_readiness_{kind}_bridge_receipt_id_invalid",
                expected_prefix=prefix,
            )
        )
        return None
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
        blocked.append(
            _reason(
                f"candidate_b_default_readiness_{kind}_bridge_receipt_unreadable",
                reason=exc.__class__.__name__,
            )
        )
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


def _validate_compare_target_set(
    *,
    kind: str,
    receipt: Mapping[str, Any],
    target_set: Mapping[str, Any],
    blocked: list[dict[str, Any]],
) -> None:
    targets = _normalised_compare_targets(target_set)
    target_count = _safe_int(target_set.get("target_count"))
    if not targets or target_count <= 0:
        blocked.append(_reason(f"candidate_b_default_readiness_{kind}_compare_target_set_empty"))
    if target_count != len(targets):
        blocked.append(
            _reason(
                f"candidate_b_default_readiness_{kind}_compare_target_count_mismatch",
                expected=len(targets),
                received=target_set.get("target_count"),
            )
        )
    fixture_ids = [str(item).strip() for item in target_set.get("fixture_ids") or [] if str(item).strip()]
    target_fixture_ids = _target_fixture_ids(target_set)
    if target_fixture_ids and fixture_ids != target_fixture_ids:
        blocked.append(
            _reason(
                f"candidate_b_default_readiness_{kind}_compare_target_fixture_ids_mismatch",
                expected=target_fixture_ids,
                received=fixture_ids,
            )
        )
    receipt_hash = str(receipt.get("compare_target_set_hash") or "").strip()
    embedded_hash = str(target_set.get("compare_target_set_hash") or "").strip()
    if len(receipt_hash) != 64 or len(embedded_hash) != 64 or receipt_hash != embedded_hash:
        blocked.append(
            _reason(
                f"candidate_b_default_readiness_{kind}_compare_target_set_hash_mismatch",
                expected=receipt_hash or None,
                received=embedded_hash or None,
            )
        )
    expected_payload_hash = _expected_compare_target_set_hash(kind=kind, target_set=target_set)
    if expected_payload_hash is None:
        if targets and target_count > 0:
            blocked.append(_reason(f"candidate_b_default_readiness_{kind}_compare_target_set_payload_invalid"))
    elif embedded_hash != expected_payload_hash:
        blocked.append(
            _reason(
                f"candidate_b_default_readiness_{kind}_compare_target_set_payload_hash_mismatch",
                expected=expected_payload_hash,
                received=embedded_hash or None,
            )
        )


def _validate_compare_target_set_consistency(
    *,
    bundle_target_set: Mapping[str, Any],
    runtime_target_set: Mapping[str, Any],
) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    bundle_targets = _normalised_compare_targets(bundle_target_set)
    runtime_targets = _normalised_compare_targets(runtime_target_set)
    if not bundle_targets or not runtime_targets:
        return blocked
    bundle_count = _safe_int(bundle_target_set.get("target_count"))
    runtime_count = _safe_int(runtime_target_set.get("target_count"))
    if bundle_count != runtime_count:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_compare_target_count_mismatch",
                bundle_target_count=bundle_target_set.get("target_count"),
                runtime_target_count=runtime_target_set.get("target_count"),
            )
        )
    bundle_fixture_ids = [str(item).strip() for item in bundle_target_set.get("fixture_ids") or [] if str(item).strip()]
    runtime_fixture_ids = [str(item).strip() for item in runtime_target_set.get("fixture_ids") or [] if str(item).strip()]
    if bundle_fixture_ids and runtime_fixture_ids and bundle_fixture_ids != runtime_fixture_ids:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_compare_target_fixture_ids_mismatch",
                bundle_fixture_ids=bundle_fixture_ids,
                runtime_fixture_ids=runtime_fixture_ids,
            )
        )
    if bundle_targets != runtime_targets:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_compare_target_set_mismatch",
                bundle_targets=bundle_targets,
                runtime_targets=runtime_targets,
            )
        )
    return blocked


def _expected_compare_target_set_hash(*, kind: str, target_set: Mapping[str, Any]) -> str | None:
    compact_targets = _compact_compare_targets_for_hash(target_set)
    if not compact_targets:
        return None
    if kind == "bundle":
        return _stable_hash(compact_targets)
    candidate_b_run_id = str(target_set.get("candidate_b_run_id") or "").strip()
    if not candidate_b_run_id:
        return None
    return _stable_hash({"targets": compact_targets, "candidate_b_run_id": candidate_b_run_id})


def _compact_compare_targets_for_hash(target_set: Mapping[str, Any]) -> list[dict[str, str]]:
    targets = target_set.get("targets")
    if not isinstance(targets, list):
        return []
    compact = []
    for item in targets:
        if not isinstance(item, Mapping):
            continue
        record = {
            "fixture_id": str(item.get("fixture_id") or "").strip(),
            "baseline_target_id": str(item.get("baseline_target_id") or "").strip(),
            "candidate_a_target_id": str(item.get("candidate_a_target_id") or "").strip(),
            "candidate_b_target_id": str(item.get("candidate_b_target_id") or "").strip(),
            "comparability_state": str(item.get("comparability_state") or "").strip(),
        }
        if all(record.values()):
            compact.append(record)
    compact.sort(key=lambda item: item["fixture_id"])
    return compact


def _normalised_compare_targets(target_set: Mapping[str, Any]) -> list[dict[str, Any]]:
    targets = target_set.get("targets")
    if not isinstance(targets, list):
        return []
    normalised = []
    for item in targets:
        if not isinstance(item, Mapping):
            continue
        identity = {
            "fixture_id": str(item.get("fixture_id") or item.get("target_key") or item.get("ordinal") or "").strip(),
            "baseline_target_id": str(item.get("baseline_target_id") or "").strip(),
            "candidate_a_target_id": str(item.get("candidate_a_target_id") or "").strip(),
            "comparability_state": str(item.get("comparability_state") or "").strip(),
        }
        if all(identity.values()):
            normalised.append(identity)
    normalised.sort(key=lambda item: item["fixture_id"])
    return normalised


def _target_fixture_ids(target_set: Mapping[str, Any]) -> list[str]:
    targets = target_set.get("targets")
    if not isinstance(targets, list):
        return []
    fixture_ids = [
        str(item.get("fixture_id") or "").strip()
        for item in targets
        if isinstance(item, Mapping) and str(item.get("fixture_id") or "").strip()
    ]
    return sorted(fixture_ids)


def _safe_int(value: Any) -> int:
    parsed = _strict_nonnegative_int(value)
    return parsed if parsed is not None else 0


def _strict_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdecimal():
            return int(text)
    return None


def _project_nonnegative_int(value: Any) -> int:
    parsed = _strict_nonnegative_int(value)
    return parsed if parsed is not None else 0


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
        "caller_supplied_local_paths_enabled",
        "provider_object_writes_enabled",
        "connector_dispatch_enabled",
        "rag_vector_model_runtime_enabled",
        "browser_storage_authority_enabled",
        "frontend_durable_authority_enabled",
        "full_mockup_activation_enabled",
    }
    expected_values = {"candidate_b_visual_lane_mode_enabled": kind == "runtime"}
    if kind == "bundle":
        required_false.update(
            {
                "candidate_b_runtime_db_rows_enabled",
                "candidate_b_runtime_storage_rows_enabled",
                "broad_raw_root_ingestion_enabled",
            }
        )
    else:
        required_false.update(
            {
                "candidate_b_bundle_bridge_weakened",
                "broad_runtime_db_ingestion_enabled",
                "broad_runtime_storage_ingestion_enabled",
            }
        )
    failed = sorted(key for key in required_false if invariants.get(key) is not False)
    failed.extend(sorted(key for key, expected in expected_values.items() if invariants.get(key) is not expected))
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
        "compare_target_authority": dict(target_set),
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
            "candidate_b_visual_ref_total": _project_nonnegative_int(evidence.get("candidate_b_visual_ref_total")),
            "candidate_b_retained_source_pdf_ref_count": _project_nonnegative_int(
                evidence.get("candidate_b_retained_source_pdf_ref_count")
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
    for field in ("visual_ref_total", "candidate_b_visual_ref_total", "candidate_b_retained_source_pdf_ref_count"):
        count = _strict_nonnegative_int(evidence.get(field))
        if count is None:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_runtime_visual_lane_evidence_count_invalid",
                    field=field,
                    received=evidence.get(field),
                )
            )
        elif count <= 0:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_runtime_visual_lane_evidence_count_missing",
                    field=field,
                )
            )
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
    recomputed_hash = _artifact_family_hash(kind, artifact_family)
    if recomputed_hash != expected_hash:
        blocked.append(
            _reason(
                f"candidate_b_default_readiness_{kind}_governed_artifact_family_stale",
                expected=expected_hash or None,
                received=recomputed_hash,
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
        if not isinstance(roles.get("visual_page_evidence"), list) or not roles["visual_page_evidence"]:
            blocked.append(_reason(f"candidate_b_default_readiness_{kind}_visual_page_evidence_missing"))
        if not isinstance(roles.get("product_inspection_artifacts"), list) or not roles["product_inspection_artifacts"]:
            blocked.append(_reason(f"candidate_b_default_readiness_{kind}_product_inspection_artifacts_missing"))
        if not isinstance(roles.get("delivery_artifacts"), list) or not roles["delivery_artifacts"]:
            blocked.append(_reason(f"candidate_b_default_readiness_{kind}_delivery_artifacts_missing"))
    return artifact_family


def _artifact_family_hash(kind: str, artifact_family: Mapping[str, Any]) -> str:
    hash_version = (
        layer3_candidate_b_bundle_bridge.AUTHORITY_HASH_VERSION
        if kind == "bundle"
        else layer3_candidate_b_runtime_bridge.AUTHORITY_HASH_VERSION
    )
    classification = dict(artifact_family)
    classification.pop("artifact_family_hash", None)
    return _stable_hash({"hash_version": hash_version, "classification": classification})


def _artifact_family_summary(artifact_family: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact_family, Mapping):
        return {"available": False}
    return {
        "available": True,
        "policy": artifact_family.get("policy"),
        "artifact_family_hash": artifact_family.get("artifact_family_hash"),
        "role_counts": artifact_family.get("role_counts") if isinstance(artifact_family.get("role_counts"), dict) else {},
        "role_previews": _final_operator_role_previews(artifact_family),
        "pdf_material_text_payload_enabled": artifact_family.get("pdf_material_text_payload_enabled") is True,
        "image_material_text_payload_enabled": artifact_family.get("image_material_text_payload_enabled") is True,
        "raw_url_exposure_enabled": artifact_family.get("raw_url_exposure_enabled") is True,
    }


def _final_operator_artifact_count_reasons(
    *,
    kind: str,
    artifact_family: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(artifact_family, Mapping):
        return []
    role_counts = artifact_family.get("role_counts")
    if not isinstance(role_counts, Mapping):
        return [_reason(f"candidate_b_default_readiness_{kind}_final_operator_role_counts_missing")]
    reasons: list[dict[str, Any]] = []
    roles = artifact_family.get("roles")
    role_previews = artifact_family.get("role_previews")
    if isinstance(roles, Mapping):
        role_entries = roles
    elif isinstance(role_previews, Mapping):
        role_entries = role_previews
    else:
        reasons.append(_reason(f"candidate_b_default_readiness_{kind}_final_operator_roles_missing"))
        role_entries = {}
    for role in ("visual_page_evidence", "product_inspection_artifacts", "delivery_artifacts"):
        if not isinstance(role_entries.get(role), list):
            reasons.append(
                _reason(
                    f"candidate_b_default_readiness_{kind}_final_operator_role_entries_invalid",
                    field=role,
                    received_type=type(role_entries.get(role)).__name__,
                )
            )
        count = _strict_nonnegative_int(role_counts.get(role))
        if count is None:
            reasons.append(
                _reason(
                    f"candidate_b_default_readiness_{kind}_final_operator_artifact_count_invalid",
                    field=role,
                    received=role_counts.get(role),
                )
            )
        elif count <= 0:
            reasons.append(
                _reason(
                    f"candidate_b_default_readiness_{kind}_final_operator_artifact_count_missing",
                    field=role,
                )
            )
    return reasons


def _final_operator_inspection_evidence(
    bundle_artifact_family: Mapping[str, Any] | None,
    runtime_artifact_family: Mapping[str, Any] | None,
) -> dict[str, Any]:
    bundle_summary = _final_operator_artifact_summary("bundle", bundle_artifact_family)
    runtime_summary = _final_operator_artifact_summary("runtime", runtime_artifact_family)
    inspection_available = _final_operator_artifact_available(bundle_summary) and _final_operator_artifact_available(
        runtime_summary
    )
    evidence_input = {
        "hash_version": "candidate_b_final_operator_inspection_evidence_hash_v1",
        "bundle": bundle_summary,
        "runtime": runtime_summary,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
    }
    evidence_hash = _stable_hash(evidence_input)
    return {
        "status": "available" if inspection_available else "blocked",
        "final_operator_inspection_hash": evidence_hash,
        "bundle": bundle_summary,
        "runtime": runtime_summary,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
    }


def _final_operator_artifact_available(summary: Mapping[str, Any]) -> bool:
    role_previews = summary.get("role_previews") if isinstance(summary.get("role_previews"), Mapping) else {}
    preview_roles = ("visual_page_evidence", "product_inspection_artifacts", "delivery_artifacts")
    return (
        summary.get("available") is True
        and _project_nonnegative_int(summary.get("visual_page_evidence_count")) > 0
        and _project_nonnegative_int(summary.get("product_inspection_artifact_count")) > 0
        and _project_nonnegative_int(summary.get("delivery_artifact_count")) > 0
        and all(isinstance(role_previews.get(role), list) and role_previews[role] for role in preview_roles)
        and summary.get("pdf_material_text_payload_enabled") is False
        and summary.get("image_material_text_payload_enabled") is False
        and summary.get("raw_url_exposure_enabled") is False
    )


def _final_operator_artifact_summary(kind: str, artifact_family: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact_family, Mapping):
        return {
            "candidate_b_source_kind": kind,
            "available": False,
            "artifact_family_hash": None,
            "role_counts": {},
            "visual_page_evidence_count": 0,
            "product_inspection_artifact_count": 0,
            "delivery_artifact_count": 0,
            "pdf_material_text_payload_enabled": False,
            "image_material_text_payload_enabled": False,
            "raw_url_exposure_enabled": False,
        }
    role_counts = artifact_family.get("role_counts") if isinstance(artifact_family.get("role_counts"), dict) else {}
    role_previews = (
        _final_operator_role_previews(artifact_family)
        if isinstance(artifact_family.get("roles"), dict)
        else _final_operator_redacted_role_previews(artifact_family)
    )
    return {
        "candidate_b_source_kind": kind,
        "available": True,
        "artifact_family_hash": artifact_family.get("artifact_family_hash"),
        "role_counts": role_counts,
        "role_previews": role_previews,
        "visual_page_evidence_count": _project_nonnegative_int(role_counts.get("visual_page_evidence")),
        "product_inspection_artifact_count": _project_nonnegative_int(role_counts.get("product_inspection_artifacts")),
        "delivery_artifact_count": _project_nonnegative_int(role_counts.get("delivery_artifacts")),
        "pdf_material_text_payload_enabled": artifact_family.get("pdf_material_text_payload_enabled") is True,
        "image_material_text_payload_enabled": artifact_family.get("image_material_text_payload_enabled") is True,
        "raw_url_exposure_enabled": artifact_family.get("raw_url_exposure_enabled") is True,
    }


def _final_operator_role_previews(artifact_family: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    roles = artifact_family.get("roles") if isinstance(artifact_family.get("roles"), dict) else {}
    preview_roles = ("visual_page_evidence", "product_inspection_artifacts", "delivery_artifacts")
    return {
        role: [
            _final_operator_artifact_preview(item)
            for item in list(roles.get(role) or [])[:3]
            if isinstance(item, Mapping)
        ]
        for role in preview_roles
        if isinstance(roles.get(role), list)
    }


def _final_operator_redacted_role_previews(artifact_family: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    role_previews = artifact_family.get("role_previews") if isinstance(artifact_family.get("role_previews"), Mapping) else {}
    preview_roles = ("visual_page_evidence", "product_inspection_artifacts", "delivery_artifacts")
    result: dict[str, list[dict[str, Any]]] = {}
    for role in preview_roles:
        previews = role_previews.get(role)
        if not isinstance(previews, list):
            continue
        redacted = [_final_operator_redacted_preview(item) for item in previews[:3] if isinstance(item, Mapping)]
        redacted = [item for item in redacted if item is not None]
        if redacted:
            result[role] = redacted
    return result


def _final_operator_redacted_preview(item: Mapping[str, Any]) -> dict[str, Any] | None:
    display_ref = str(item.get("display_ref") or "").strip()
    if not display_ref or "/" in display_ref or "\\" in display_ref or ".." in display_ref:
        return None
    return {
        "display_ref": display_ref,
        "artifact_role": str(item.get("artifact_role") or "").strip() or None,
        "category": str(item.get("category") or "").strip() or None,
        "extension": str(item.get("extension") or "").strip() or None,
        "sha256": str(item.get("sha256") or "").strip() or None,
        "material_text_payload": item.get("material_text_payload") is True,
    }


def _final_operator_artifact_preview(item: Mapping[str, Any]) -> dict[str, Any]:
    source_ref = str(item.get("source_ref") or item.get("relative_name") or "").replace("\\", "/").strip()
    display_ref = source_ref.rsplit("/", 1)[-1] if source_ref else None
    return {
        "display_ref": display_ref,
        "artifact_role": str(item.get("artifact_role") or "").strip() or None,
        "category": str(item.get("category") or "").strip() or None,
        "extension": str(item.get("extension") or "").strip() or None,
        "sha256": str(item.get("sha256") or "").strip() or None,
        "material_text_payload": item.get("material_text_payload") is True,
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


def _validate_downstream_proof(
    proof: Any,
    *,
    source_kind: str,
    bridge_receipt_id: str,
    candidate_b_bundle_id: str | None = None,
    candidate_b_run_id: str | None = None,
    bridge_receipt_hash: str | None = None,
    visual_lane_status_hash: str | None = None,
) -> dict[str, Any]:
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
    if source_kind == "bundle":
        for field, expected in {
            "schema_id": layer3_candidate_b_bundle_downstream_proof.SCHEMA_ID,
            "schema_version": layer3_candidate_b_bundle_downstream_proof.SCHEMA_VERSION,
            "mode": layer3_candidate_b_bundle_downstream_proof.PROOF_MODE,
            "status": "proven",
            "candidate_b_bundle_id": candidate_b_bundle_id,
            "bridge_receipt_hash": bridge_receipt_hash,
        }.items():
            if str(proof.get(field) or "").strip() != str(expected or "").strip():
                blocked.append(
                    _reason(
                        f"candidate_b_default_readiness_bundle_downstream_{field}_mismatch",
                        field=field,
                        expected=expected,
                        received=proof.get(field),
                    )
                )
        missing_hash_fields = [
            key for key in layer3_candidate_b_bundle_downstream_proof.PROOF_HASH_KEYS if key not in proof
        ]
        if missing_hash_fields:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_bundle_downstream_proof_authority_field_missing",
                    missing_fields=missing_hash_fields,
                )
            )
        else:
            expected_hash = _stable_hash(
                {key: proof[key] for key in layer3_candidate_b_bundle_downstream_proof.PROOF_HASH_KEYS}
            )
            if proof.get("proof_hash") != expected_hash:
                blocked.append(
                    _reason(
                        "candidate_b_default_readiness_bundle_downstream_proof_hash_mismatch",
                        expected=expected_hash,
                        received=proof.get("proof_hash"),
                    )
                )
            _validate_bundle_downstream_proof_receipt(
                proof=proof,
                bridge_receipt_id=bridge_receipt_id,
                expected_hash=expected_hash,
                blocked=blocked,
            )
    if source_kind == "runtime":
        for field, expected in {
            "schema_id": layer3_candidate_b_downstream_proof.SCHEMA_ID,
            "schema_version": layer3_candidate_b_downstream_proof.SCHEMA_VERSION,
            "mode": layer3_candidate_b_downstream_proof.PROOF_MODE,
            "status": "proven",
            "candidate_b_run_id": candidate_b_run_id,
            "bridge_receipt_hash": bridge_receipt_hash,
            "document_processing_engine": CANDIDATE_B_ENGINE,
            "candidate_b_visual_lane_status_hash": visual_lane_status_hash,
        }.items():
            if str(proof.get(field) or "").strip() != str(expected or "").strip():
                blocked.append(
                    _reason(
                        f"candidate_b_default_readiness_runtime_downstream_{field}_mismatch",
                        field=field,
                        expected=expected,
                        received=proof.get(field),
                    )
                )
        missing_hash_fields = [key for key in layer3_candidate_b_downstream_proof.PROOF_HASH_KEYS if key not in proof]
        if missing_hash_fields:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_runtime_downstream_proof_authority_field_missing",
                    missing_fields=missing_hash_fields,
                )
            )
        else:
            expected_hash = _stable_hash({key: proof[key] for key in layer3_candidate_b_downstream_proof.PROOF_HASH_KEYS})
            if proof.get("proof_hash") != expected_hash:
                blocked.append(
                    _reason(
                        "candidate_b_default_readiness_runtime_downstream_proof_hash_mismatch",
                        expected=expected_hash,
                        received=proof.get("proof_hash"),
                    )
                )
            _validate_runtime_downstream_proof_receipt(
                proof=proof,
                bridge_receipt_id=bridge_receipt_id,
                expected_hash=expected_hash,
                blocked=blocked,
            )
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
            "proof_receipt_id": proof.get("proof_receipt_id"),
            "proof_receipt_ref": proof.get("proof_receipt_ref"),
            "coverage": sorted(coverage),
            "missing_coverage": missing,
            "raw_local_path_exposed": proof.get("raw_local_path_exposed") is True,
            "provider_private_token_exposed": proof.get("provider_private_token_exposed") is True,
            "visual_lane_mode_enabled": proof.get("visual_lane_mode_enabled") is True,
            "visual_lane_mode": proof.get("visual_lane_mode"),
        },
    }


def _validate_runtime_downstream_proof_receipt(
    *,
    proof: Mapping[str, Any],
    bridge_receipt_id: str,
    expected_hash: str,
    blocked: list[dict[str, Any]],
) -> None:
    _validate_persisted_downstream_proof_receipt(
        proof=proof,
        bridge_receipt_id=bridge_receipt_id,
        expected_hash=expected_hash,
        proof_receipt_prefix=layer3_candidate_b_downstream_proof.PROOF_RECEIPT_PREFIX,
        bridge_receipt_prefix=layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX,
        configured_root=settings.layer3_candidate_b_runtime_bridge_dir,
        hash_keys=layer3_candidate_b_downstream_proof.PROOF_HASH_KEYS,
        code_prefix="candidate_b_default_readiness_runtime_downstream_proof",
        blocked=blocked,
    )


def _validate_bundle_downstream_proof_receipt(
    *,
    proof: Mapping[str, Any],
    bridge_receipt_id: str,
    expected_hash: str,
    blocked: list[dict[str, Any]],
) -> None:
    _validate_persisted_downstream_proof_receipt(
        proof=proof,
        bridge_receipt_id=bridge_receipt_id,
        expected_hash=expected_hash,
        proof_receipt_prefix=layer3_candidate_b_bundle_downstream_proof.PROOF_RECEIPT_PREFIX,
        bridge_receipt_prefix=layer3_candidate_b_bundle_bridge.BRIDGE_RECEIPT_PREFIX,
        configured_root=settings.layer3_candidate_b_bundle_bridge_dir,
        hash_keys=layer3_candidate_b_bundle_downstream_proof.PROOF_HASH_KEYS,
        code_prefix="candidate_b_default_readiness_bundle_downstream_proof",
        blocked=blocked,
    )


def _validate_persisted_downstream_proof_receipt(
    *,
    proof: Mapping[str, Any],
    bridge_receipt_id: str,
    expected_hash: str,
    proof_receipt_prefix: str,
    bridge_receipt_prefix: str,
    configured_root: str | None,
    hash_keys: tuple[str, ...],
    code_prefix: str,
    blocked: list[dict[str, Any]],
) -> None:
    proof_receipt_id = str(proof.get("proof_receipt_id") or "").strip()
    if not proof_receipt_id:
        blocked.append(_reason(f"{code_prefix}_receipt_id_missing"))
        return
    if not layer3_candidate_b_storage_id.is_storage_id(
        proof_receipt_id,
        prefix=proof_receipt_prefix,
    ):
        blocked.append(_reason(f"{code_prefix}_receipt_id_invalid"))
        return
    expected_receipt_id = f"{proof_receipt_prefix}-{expected_hash[:24]}"
    if proof_receipt_id != expected_receipt_id:
        blocked.append(
            _reason(
                f"{code_prefix}_receipt_id_mismatch",
                expected=expected_receipt_id,
                received=proof_receipt_id,
            )
        )
        return
    if not layer3_candidate_b_storage_id.is_storage_id(
        bridge_receipt_id,
        prefix=bridge_receipt_prefix,
    ):
        blocked.append(_reason(f"{code_prefix}_bridge_receipt_id_invalid"))
        return
    if not str(configured_root or "").strip():
        blocked.append(_reason(f"{code_prefix}_bridge_dir_unset"))
        return
    root = Path(str(configured_root))
    if not root.is_absolute():
        blocked.append(_reason(f"{code_prefix}_bridge_dir_not_absolute"))
        return
    proof_path = root / bridge_receipt_id / "downstream-proof" / f"{proof_receipt_id}.json"
    if not proof_path.is_file():
        blocked.append(
            _reason(
                f"{code_prefix}_receipt_missing",
                proof_receipt_id=proof_receipt_id,
            )
        )
        return
    try:
        stored = json.loads(proof_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        blocked.append(
            _reason(
                f"{code_prefix}_receipt_unreadable",
                proof_receipt_id=proof_receipt_id,
                reason=str(exc),
            )
        )
        return
    if not isinstance(stored, dict):
        blocked.append(
            _reason(
                f"{code_prefix}_receipt_invalid",
                proof_receipt_id=proof_receipt_id,
            )
        )
        return
    mismatches = [
        {"field": field, "expected": expected, "received": stored.get(field)}
        for field, expected in {
            "proof_receipt_id": proof_receipt_id,
            "bridge_receipt_id": bridge_receipt_id,
        }.items()
        if str(stored.get(field) or "").strip() != str(expected or "").strip()
    ]
    if mismatches:
        blocked.append(_reason(f"{code_prefix}_receipt_mismatch", mismatches=mismatches))
        return
    missing_hash_fields = [key for key in hash_keys if key not in stored]
    if missing_hash_fields:
        blocked.append(
            _reason(
                f"{code_prefix}_receipt_authority_field_missing",
                missing_fields=missing_hash_fields,
            )
        )
        return
    recomputed_hash = _stable_hash({key: stored[key] for key in hash_keys})
    if stored.get("proof_hash") != expected_hash or recomputed_hash != expected_hash:
        blocked.append(
            _reason(
                f"{code_prefix}_receipt_hash_mismatch",
                expected=expected_hash,
                received=stored.get("proof_hash"),
                recomputed=recomputed_hash,
            )
        )


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


def _validate_operator_status(
    value: Any,
    *,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_bundle_id: str,
    candidate_b_run_id: str,
    bundle_receipt_id: str,
    bundle_receipt_hash: str | None,
    runtime_receipt_id: str,
    runtime_receipt_hash: str | None,
    visual_lane_status_hash: str | None,
    runtime_downstream_proof_hash: str | None,
    runtime_retained_artifact_family_hash: str | None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "blocked_reasons": [_reason("candidate_b_default_readiness_operator_status_evidence_missing")],
            "summary": {"status": "missing"},
            "operator_status_hash": None,
        }
    evidence = value
    required_true = (
        "operator_visible_provenance_status",
        "bundle_status_projection_visible",
        "runtime_status_projection_visible",
        "default_selector_change_visible_as_enabled",
        "runtime_delivery_artifact_projection_visible",
        "runtime_delivery_artifact_roles_bound",
    )
    summary = {key: evidence.get(key) is True for key in required_true}
    summary["raw_local_path_exposed"] = evidence.get("raw_local_path_exposed") is True
    summary["provider_private_token_exposed"] = evidence.get("provider_private_token_exposed") is True
    blocked = []
    for field, expected in {
        "schema_id": layer3_candidate_b_operator_status.SCHEMA_ID,
        "mode": layer3_candidate_b_operator_status.STATUS_MODE,
        "status": "available",
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_bundle_id": candidate_b_bundle_id,
        "candidate_b_run_id": candidate_b_run_id,
        "bundle_bridge_receipt_id": bundle_receipt_id,
        "bundle_bridge_receipt_hash": bundle_receipt_hash,
        "runtime_bridge_receipt_id": runtime_receipt_id,
        "runtime_bridge_receipt_hash": runtime_receipt_hash,
        "candidate_b_visual_lane_status_hash": visual_lane_status_hash,
        "runtime_downstream_proof_hash": runtime_downstream_proof_hash,
        "runtime_delivery_artifact_authority_hash": runtime_retained_artifact_family_hash,
    }.items():
        if str(evidence.get(field) or "").strip() != str(expected or "").strip():
            blocked.append(
                _reason(
                    f"candidate_b_default_readiness_operator_status_{field}_mismatch",
                    field=field,
                    expected=expected,
                    received=evidence.get(field),
                )
            )
    missing = [key for key in required_true if evidence.get(key) is not True]
    if missing:
        blocked.append(_reason("candidate_b_default_readiness_operator_status_evidence_incomplete", missing_fields=missing))
    expected_delivery_steps = sorted(layer3_candidate_b_downstream_proof.DELIVERY_ARTIFACT_AUTHORITY_COVERAGE)
    if evidence.get("runtime_delivery_artifact_coverage_steps") != expected_delivery_steps:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_operator_status_delivery_artifact_coverage_mismatch",
                expected=expected_delivery_steps,
                received=evidence.get("runtime_delivery_artifact_coverage_steps"),
            )
        )
    if (
        summary["raw_local_path_exposed"]
        or summary["provider_private_token_exposed"]
        or evidence.get("raw_url_exposed") is not False
        or evidence.get("artifact_bytes_exposed") is not False
        or evidence.get("selector_mutation_performed") is not False
    ):
        blocked.append(_reason("candidate_b_default_readiness_operator_status_exposes_sensitive_authority"))
    _validate_operator_status_delivery_previews(evidence, blocked)
    missing_hash_fields = [key for key in layer3_candidate_b_operator_status.STATUS_HASH_KEYS if key not in evidence]
    if missing_hash_fields:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_operator_status_authority_field_missing",
                missing_fields=missing_hash_fields,
            )
        )
        operator_status_hash = None
    else:
        operator_status_hash = _stable_hash({key: evidence[key] for key in layer3_candidate_b_operator_status.STATUS_HASH_KEYS})
        if evidence.get("operator_status_hash") != operator_status_hash:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_operator_status_hash_mismatch",
                    expected=operator_status_hash,
                    received=evidence.get("operator_status_hash"),
                )
            )
        _validate_operator_status_receipt(
            evidence=evidence,
            runtime_receipt_id=runtime_receipt_id,
            expected_hash=operator_status_hash,
            blocked=blocked,
        )
    summary.update(
        {
            "status": evidence.get("status"),
            "operator_status_hash": operator_status_hash,
            "operator_status_receipt_id": evidence.get("operator_status_receipt_id"),
            "bundle_bridge_receipt_id": evidence.get("bundle_bridge_receipt_id"),
            "runtime_bridge_receipt_id": evidence.get("runtime_bridge_receipt_id"),
            "runtime_delivery_artifact_authority_hash": evidence.get("runtime_delivery_artifact_authority_hash"),
            "runtime_delivery_artifact_coverage_steps": evidence.get("runtime_delivery_artifact_coverage_steps"),
            "runtime_delivery_artifact_role_previews": evidence.get("runtime_delivery_artifact_role_previews"),
            "runtime_delivery_artifact_projection_visible": (
                evidence.get("runtime_delivery_artifact_projection_visible") is True
            ),
            "runtime_delivery_artifact_roles_bound": evidence.get("runtime_delivery_artifact_roles_bound") is True,
            "raw_url_exposed": evidence.get("raw_url_exposed") is True,
            "artifact_bytes_exposed": evidence.get("artifact_bytes_exposed") is True,
            "selector_mutation_performed": evidence.get("selector_mutation_performed") is True,
        }
    )
    return {"blocked_reasons": blocked, "summary": summary, "operator_status_hash": operator_status_hash}


def _validate_operator_status_delivery_previews(evidence: Mapping[str, Any], blocked: list[dict[str, Any]]) -> None:
    previews = evidence.get("runtime_delivery_artifact_role_previews")
    if not isinstance(previews, list) or not previews:
        blocked.append(_reason("candidate_b_default_readiness_operator_status_delivery_previews_missing"))
        return
    for preview in previews:
        if not isinstance(preview, Mapping):
            blocked.append(_reason("candidate_b_default_readiness_operator_status_delivery_preview_invalid"))
            return
        display_ref = str(preview.get("display_ref") or "").strip()
        if not display_ref or "/" in display_ref or "\\" in display_ref or ".." in display_ref:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_operator_status_delivery_preview_not_redacted",
                    display_ref=display_ref or None,
                )
            )
            return


def _validate_closure_evidence(
    value: Any,
    *,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_bundle_id: str,
    candidate_b_run_id: str,
    bundle_receipt_id: str,
    bundle_receipt_hash: str | None,
    runtime_receipt_id: str,
    runtime_receipt_hash: str | None,
    bundle_downstream_proof_hash: str | None,
    runtime_downstream_proof_hash: str | None,
    operator_status_hash: str | None,
    operator_status_projection: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "blocked_reasons": [_reason("candidate_b_default_readiness_closure_evidence_missing")],
            "summary": {"status": "missing"},
            "closure_evidence_hash": None,
        }
    evidence = value
    blocked = []
    for field, expected in {
        "schema_id": layer3_candidate_b_promotion_closure.SCHEMA_ID,
        "mode": layer3_candidate_b_promotion_closure.CLOSURE_MODE,
        "status": "ready",
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_bundle_id": candidate_b_bundle_id,
        "candidate_b_run_id": candidate_b_run_id,
        "bundle_bridge_receipt_id": bundle_receipt_id,
        "bundle_bridge_receipt_hash": bundle_receipt_hash,
        "runtime_bridge_receipt_id": runtime_receipt_id,
        "runtime_bridge_receipt_hash": runtime_receipt_hash,
        "bundle_downstream_proof_hash": bundle_downstream_proof_hash,
        "runtime_downstream_proof_hash": runtime_downstream_proof_hash,
        "operator_status_hash": operator_status_hash,
        "eligible_corpus_scope": ELIGIBLE_CORPUS_SCOPE,
        "regression_disposition": REGRESSION_DISPOSITION_READY,
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }.items():
        if str(evidence.get(field) or "").strip() != str(expected or "").strip():
            blocked.append(
                _reason(
                    f"candidate_b_default_readiness_closure_{field}_mismatch",
                    field=field,
                    expected=expected,
                    received=evidence.get(field),
                )
            )
    if (
        evidence.get("raw_local_path_exposed") is not False
        or evidence.get("raw_url_exposed") is not False
        or evidence.get("provider_private_token_exposed") is not False
        or evidence.get("artifact_bytes_exposed") is not False
        or evidence.get("selector_mutation_performed") is not False
    ):
        blocked.append(_reason("candidate_b_default_readiness_closure_exposes_sensitive_authority"))
    missing_hash_fields = [key for key in layer3_candidate_b_promotion_closure.CLOSURE_HASH_KEYS if key not in evidence]
    if missing_hash_fields:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_closure_authority_field_missing",
                missing_fields=missing_hash_fields,
            )
        )
        closure_hash = None
    else:
        closure_hash = _stable_hash(
            {key: evidence[key] for key in layer3_candidate_b_promotion_closure.CLOSURE_HASH_KEYS}
        )
        if evidence.get("closure_evidence_hash") != closure_hash:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_closure_hash_mismatch",
                    expected=closure_hash,
                    received=evidence.get("closure_evidence_hash"),
                )
            )
        _validate_closure_receipt(
            evidence=evidence,
            runtime_receipt_id=runtime_receipt_id,
            expected_hash=closure_hash,
            blocked=blocked,
        )
    _validate_closure_operator_status_projection(
        evidence.get("candidate_b_operator_status_evidence"),
        operator_status_hash=operator_status_hash,
        expected_projection=operator_status_projection,
        blocked=blocked,
    )
    summary = {
        "status": evidence.get("status"),
        "closure_evidence_hash": closure_hash,
        "closure_receipt_id": evidence.get("closure_receipt_id"),
        "candidate_b_operator_status_evidence": evidence.get("candidate_b_operator_status_evidence"),
        "regression_disposition": evidence.get("regression_disposition"),
        "rollback_to_baseline_confirmation": evidence.get("rollback_to_baseline_confirmation") is True,
        "operator_confirmation": evidence.get("operator_confirmation") is True,
        "selector_mutation_performed": evidence.get("selector_mutation_performed") is True,
    }
    return {"blocked_reasons": blocked, "summary": summary, "closure_evidence_hash": closure_hash}


def _validate_closure_operator_status_projection(
    value: Any,
    *,
    operator_status_hash: str | None,
    expected_projection: Mapping[str, Any],
    blocked: list[dict[str, Any]],
) -> None:
    if not isinstance(value, dict):
        blocked.append(_reason("candidate_b_default_readiness_closure_operator_status_projection_missing"))
        return
    if str(value.get("operator_status_hash") or "").strip() != str(operator_status_hash or "").strip():
        blocked.append(
            _reason(
                "candidate_b_default_readiness_closure_operator_status_hash_mismatch",
                expected=operator_status_hash,
                received=value.get("operator_status_hash"),
            )
        )
    if dict(value) != dict(expected_projection):
        blocked.append(_reason("candidate_b_default_readiness_closure_operator_status_projection_mismatch"))
    required_true = (
        "runtime_delivery_artifact_projection_visible",
        "runtime_delivery_artifact_roles_bound",
    )
    missing = [field for field in required_true if value.get(field) is not True]
    if missing:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_closure_operator_status_projection_incomplete",
                missing_fields=missing,
            )
        )
    expected_delivery_steps = sorted(layer3_candidate_b_downstream_proof.DELIVERY_ARTIFACT_AUTHORITY_COVERAGE)
    if value.get("runtime_delivery_artifact_coverage_steps") != expected_delivery_steps:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_closure_operator_status_delivery_coverage_mismatch",
                expected=expected_delivery_steps,
                received=value.get("runtime_delivery_artifact_coverage_steps"),
            )
        )
    if not str(value.get("runtime_delivery_artifact_authority_hash") or "").strip():
        blocked.append(_reason("candidate_b_default_readiness_closure_operator_status_delivery_authority_missing"))


def _validate_closure_receipt(
    *,
    evidence: Mapping[str, Any],
    runtime_receipt_id: str,
    expected_hash: str,
    blocked: list[dict[str, Any]],
) -> None:
    receipt_id = str(evidence.get("closure_receipt_id") or "").strip()
    if not receipt_id:
        blocked.append(_reason("candidate_b_default_readiness_closure_receipt_id_missing"))
        return
    if not layer3_candidate_b_storage_id.is_storage_id(
        receipt_id,
        prefix=layer3_candidate_b_promotion_closure.CLOSURE_RECEIPT_PREFIX,
    ):
        blocked.append(_reason("candidate_b_default_readiness_closure_receipt_id_invalid"))
        return
    if not layer3_candidate_b_storage_id.is_storage_id(
        runtime_receipt_id,
        prefix=layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX,
    ):
        blocked.append(_reason("candidate_b_default_readiness_closure_runtime_receipt_id_invalid"))
        return
    configured = settings.layer3_candidate_b_runtime_bridge_dir
    if not str(configured or "").strip():
        blocked.append(_reason("candidate_b_default_readiness_closure_bridge_dir_unset"))
        return
    root = Path(str(configured))
    if not root.is_absolute():
        blocked.append(_reason("candidate_b_default_readiness_closure_bridge_dir_not_absolute"))
        return
    path = root / runtime_receipt_id / "default-promotion-closure" / f"{receipt_id}.json"
    if not path.is_file():
        blocked.append(_reason("candidate_b_default_readiness_closure_receipt_missing", receipt_id=receipt_id))
        return
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        blocked.append(_reason("candidate_b_default_readiness_closure_receipt_unreadable", reason=str(exc)))
        return
    if not isinstance(stored, dict) or stored.get("closure_evidence_hash") != expected_hash:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_closure_receipt_hash_mismatch",
                expected=expected_hash,
                received=stored.get("closure_evidence_hash") if isinstance(stored, dict) else None,
            )
        )


def _validate_operator_status_receipt(
    *,
    evidence: Mapping[str, Any],
    runtime_receipt_id: str,
    expected_hash: str,
    blocked: list[dict[str, Any]],
) -> None:
    receipt_id = str(evidence.get("operator_status_receipt_id") or "").strip()
    if not receipt_id:
        blocked.append(_reason("candidate_b_default_readiness_operator_status_receipt_id_missing"))
        return
    if not layer3_candidate_b_storage_id.is_storage_id(
        receipt_id,
        prefix=layer3_candidate_b_operator_status.STATUS_RECEIPT_PREFIX,
    ):
        blocked.append(_reason("candidate_b_default_readiness_operator_status_receipt_id_invalid"))
        return
    if not layer3_candidate_b_storage_id.is_storage_id(
        runtime_receipt_id,
        prefix=layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX,
    ):
        blocked.append(_reason("candidate_b_default_readiness_operator_status_runtime_receipt_id_invalid"))
        return
    configured = settings.layer3_candidate_b_runtime_bridge_dir
    if not str(configured or "").strip():
        blocked.append(_reason("candidate_b_default_readiness_operator_status_bridge_dir_unset"))
        return
    root = Path(str(configured))
    if not root.is_absolute():
        blocked.append(_reason("candidate_b_default_readiness_operator_status_bridge_dir_not_absolute"))
        return
    path = root / runtime_receipt_id / "operator-status" / f"{receipt_id}.json"
    if not path.is_file():
        blocked.append(_reason("candidate_b_default_readiness_operator_status_receipt_missing", receipt_id=receipt_id))
        return
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        blocked.append(_reason("candidate_b_default_readiness_operator_status_receipt_unreadable", reason=str(exc)))
        return
    if not isinstance(stored, dict) or stored.get("operator_status_hash") != expected_hash:
        blocked.append(
            _reason(
                "candidate_b_default_readiness_operator_status_receipt_hash_mismatch",
                expected=expected_hash,
                received=stored.get("operator_status_hash") if isinstance(stored, dict) else None,
            )
        )


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
    for field in ("visual_ref_total", "candidate_b_visual_ref_total", "candidate_b_retained_source_pdf_ref_count"):
        count = _strict_nonnegative_int(visual_evidence.get(field))
        if count is None:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_visual_lane_status_evidence_count_invalid",
                    field=field,
                    received=visual_evidence.get(field),
                )
            )
        elif count <= 0:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_visual_lane_status_evidence_count_missing",
                    field=field,
                )
            )
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
    operator_projection_counts: dict[str, int] = {}
    for field in ("visual_ref_total", "candidate_b_visual_ref_total", "candidate_b_retained_source_pdf_ref_count"):
        count = _strict_nonnegative_int(operator_projection.get(field))
        operator_projection_counts[field] = count if count is not None else 0
        if count is None:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_visual_lane_status_projection_count_invalid",
                    field=field,
                    received=operator_projection.get(field),
                )
            )
        elif count <= 0:
            blocked.append(
                _reason(
                    "candidate_b_default_readiness_visual_lane_status_projection_count_missing",
                    field=field,
                )
            )
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
            "visual_ref_total": operator_projection_counts.get("visual_ref_total", 0),
            "candidate_b_visual_ref_total": operator_projection_counts.get("candidate_b_visual_ref_total", 0),
            "candidate_b_retained_source_pdf_ref_count": operator_projection_counts.get(
                "candidate_b_retained_source_pdf_ref_count",
                0,
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
