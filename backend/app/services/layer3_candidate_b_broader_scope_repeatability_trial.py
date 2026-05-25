from __future__ import annotations

import json
from typing import Any, Mapping

from app.services import layer3_candidate_b_broader_scope_readiness
from app.services import layer3_candidate_b_broader_scope_selector_use as selector_use


SCHEMA_ID = "layer3.candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial.v1"
SCHEMA_VERSION = 1
TRIAL_MODE = "append_only_trial_receipt_over_original_and_repeat_use_status_authority_without_processing_execution"
TRIAL_OPERATOR_DECISION = "record_candidate_b_broader_scope_operator_repeatability_trial"
TRIAL_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/"
    "default-scope/operator-repeatability/trial"
)
TRIAL_RECEIPT_PREFIX = "cb-broader-scope-operator-repeatability-trial"
TRIAL_RECEIPT_DIR = "broader-scope-operator-repeatability-trial"
TRIAL_ACCEPTED_STATE = "candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial_accepted"
TRIAL_BLOCKED_STATE = "candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial_blocked"
ACCEPTED_DISPOSITIONS = {"no_regression_observed", "delta_reviewed_no_regression"}
BLOCKED_DISPOSITION = "regression_detected_blocked"
REDACTION_POLICY_ID = "candidate_b_broader_scope_operator_repeatability_trial_redaction_v1"


class CandidateBBroaderScopeOperatorRepeatabilityTrialError(
    selector_use.CandidateBBroaderScopeSelectorUseError
):
    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-broader-scope-operator-repeatability-trial-error",
            "server_time": selector_use._server_time(),
            "status": "blocked",
            "mode": TRIAL_MODE,
            "operator_repeatability_trial_state": TRIAL_BLOCKED_STATE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_broader_scope_operator_repeatability_trial(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = selector_use._normalise_payload(
        payload,
        error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
    )
    request_id = selector_use._required_str(
        fields,
        "client_request_id",
        error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
    )
    trial_mode = selector_use._required_str(
        fields,
        "trial_mode",
        error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
    )
    if trial_mode != TRIAL_MODE:
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            "candidate_b_broader_scope_operator_repeatability_trial_mode_not_admitted",
            "Only the frozen Candidate B broader-scope operator repeatability trial mode is admitted.",
            details={"expected_trial_mode": TRIAL_MODE, "received_trial_mode": trial_mode},
        )

    operator_decision = selector_use._required_str(
        fields,
        "operator_decision",
        error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
    )
    if operator_decision != TRIAL_OPERATOR_DECISION:
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            "candidate_b_broader_scope_operator_repeatability_trial_decision_not_admitted",
            "The operator decision does not match the admitted Candidate B broader-scope repeatability trial.",
            details={"expected_operator_decision": TRIAL_OPERATOR_DECISION},
        )

    disposition = selector_use._required_str(
        fields,
        "operator_repeatability_disposition",
        error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
    )
    if disposition not in ACCEPTED_DISPOSITIONS and disposition != BLOCKED_DISPOSITION:
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            "candidate_b_broader_scope_operator_repeatability_trial_disposition_not_admitted",
            "The repeatability trial disposition is not admitted.",
            details={
                "accepted_dispositions": sorted(ACCEPTED_DISPOSITIONS),
                "blocked_disposition": BLOCKED_DISPOSITION,
                "received_disposition": disposition,
            },
        )
    if fields.get("operator_confirmation") is not True:
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            "candidate_b_broader_scope_operator_repeatability_trial_operator_confirmation_missing",
            "Operator confirmation is required before recording a Candidate B broader-scope repeatability trial.",
            http_status=409,
        )

    selected_scope_classes = selector_use._string_list(fields.get("selected_scope_classes"))
    if not selected_scope_classes:
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            "candidate_b_broader_scope_operator_repeatability_trial_selected_classes_missing",
            "The repeatability trial must identify the receipt-bound selected scope classes.",
            http_status=409,
        )
    invalid_classes = sorted(
        set(selected_scope_classes) - set(layer3_candidate_b_broader_scope_readiness.SCOPE_CLASSES)
    )
    if invalid_classes:
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            "candidate_b_broader_scope_operator_repeatability_trial_unknown_scope_class",
            "The repeatability trial includes a scope class outside the admitted broader eligible-corpus class set.",
            http_status=409,
            details={"invalid_scope_classes": invalid_classes},
        )

    original_status = _load_use_status(
        fields=fields,
        prefix="original",
        request_id=request_id,
        selected_scope_classes=selected_scope_classes,
    )
    repeat_status = _load_use_status(
        fields=fields,
        prefix="repeat",
        request_id=request_id,
        selected_scope_classes=selected_scope_classes,
    )
    _require_same_authority(
        original_status=original_status,
        repeat_status=repeat_status,
        selected_scope_classes=selected_scope_classes,
    )

    selected_scope_classes_hash = selector_use._stable_hash(
        {"selected_scope_classes": selected_scope_classes}
    )
    original_receipt_chain_hash = _receipt_chain_hash(original_status)
    repeat_receipt_chain_hash = _receipt_chain_hash(repeat_status)
    original_negative_invariants_hash = selector_use._stable_hash(
        {"negative_invariants": original_status.get("negative_invariants")}
    )
    repeat_negative_invariants_hash = selector_use._stable_hash(
        {"negative_invariants": repeat_status.get("negative_invariants")}
    )
    use_status_hash_comparison = _comparison(
        original_status.get("use_receipt_status_hash"),
        repeat_status.get("use_receipt_status_hash"),
    )
    receipt_chain_hash_comparison = _comparison(original_receipt_chain_hash, repeat_receipt_chain_hash)
    selected_scope_classes_hash_comparison = "match"
    negative_invariants_hash_comparison = _comparison(
        original_negative_invariants_hash,
        repeat_negative_invariants_hash,
    )

    if disposition == "no_regression_observed" and use_status_hash_comparison != "match":
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            "candidate_b_broader_scope_operator_repeatability_trial_disposition_contradicts_delta",
            "The no-regression disposition requires matching original and repeat use-status hashes.",
            http_status=409,
            details={"use_status_hash_comparison": use_status_hash_comparison},
        )
    if receipt_chain_hash_comparison != "match" or negative_invariants_hash_comparison != "match":
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            "candidate_b_broader_scope_operator_repeatability_trial_authority_hash_mismatch",
            "The repeatability trial must keep receipt-chain and negative-invariant authority stable.",
            http_status=409,
            details={
                "receipt_chain_hash_comparison": receipt_chain_hash_comparison,
                "negative_invariants_hash_comparison": negative_invariants_hash_comparison,
            },
        )

    authority_pair_hash = selector_use._stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "trial_mode": TRIAL_MODE,
            "original_use_receipt_id": original_status["use_receipt_id"],
            "original_use_receipt_hash": original_status["use_receipt_hash"],
            "original_use_receipt_status_hash": original_status["use_receipt_status_hash"],
            "repeat_use_receipt_id": repeat_status["use_receipt_id"],
            "repeat_use_receipt_hash": repeat_status["use_receipt_hash"],
            "repeat_use_receipt_status_hash": repeat_status["use_receipt_status_hash"],
            "receipt_chain_hash": original_receipt_chain_hash,
            "selected_scope_classes_hash": selected_scope_classes_hash,
            "negative_invariants_hash": original_negative_invariants_hash,
        }
    )
    trial_hash = selector_use._stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "trial_mode": TRIAL_MODE,
            "operator_decision": TRIAL_OPERATOR_DECISION,
            "operator_repeatability_disposition": disposition,
            "authority_pair_hash": authority_pair_hash,
            "selected_scope_classes_hash": selected_scope_classes_hash,
            "use_status_hash_comparison": use_status_hash_comparison,
            "receipt_chain_hash_comparison": receipt_chain_hash_comparison,
            "negative_invariants_hash_comparison": negative_invariants_hash_comparison,
            "baseline_rollback_preserved": True,
            "candidate_a_semantics_preserved": True,
            "redaction_policy_id": REDACTION_POLICY_ID,
        }
    )
    trial_receipt_id = f"{TRIAL_RECEIPT_PREFIX}-{authority_pair_hash[:24]}"
    accepted = disposition in ACCEPTED_DISPOSITIONS
    trial_receipt_ref, idempotent_replay = _write_trial_receipt(
        receipt_id=trial_receipt_id,
        receipt_hash=trial_hash,
        request_id=request_id,
        disposition=disposition,
        accepted=accepted,
        authority_pair_hash=authority_pair_hash,
        selected_scope_classes=selected_scope_classes,
        selected_scope_classes_hash=selected_scope_classes_hash,
        original_status=original_status,
        repeat_status=repeat_status,
        original_receipt_chain_hash=original_receipt_chain_hash,
        repeat_receipt_chain_hash=repeat_receipt_chain_hash,
        original_negative_invariants_hash=original_negative_invariants_hash,
        repeat_negative_invariants_hash=repeat_negative_invariants_hash,
        use_status_hash_comparison=use_status_hash_comparison,
        receipt_chain_hash_comparison=receipt_chain_hash_comparison,
        selected_scope_classes_hash_comparison=selected_scope_classes_hash_comparison,
        negative_invariants_hash_comparison=negative_invariants_hash_comparison,
    )

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": selector_use._server_time(),
        "status": "accepted" if accepted else "blocked",
        "mode": TRIAL_MODE,
        "operator_decision": TRIAL_OPERATOR_DECISION,
        "operator_repeatability_trial_state": TRIAL_ACCEPTED_STATE if accepted else TRIAL_BLOCKED_STATE,
        "operator_repeatability_disposition": disposition,
        "trial_receipt_id": trial_receipt_id,
        "trial_receipt_hash": trial_hash,
        "trial_receipt_ref": trial_receipt_ref,
        "trial_receipt_status": "recorded",
        "trial_authority_hash": trial_hash,
        "authority_pair_hash": authority_pair_hash,
        "idempotent_replay": idempotent_replay,
        "append_only_repeatability_trial_receipt": True,
        "exclusive_trial_per_original_repeat_authority_pair": True,
        "original_use_status": _status_summary(original_status),
        "repeat_use_status": _status_summary(repeat_status),
        "readiness_audit_binding": original_status["readiness_audit_binding"],
        "runtime_selection_receipt_binding": original_status["runtime_selection_receipt_binding"],
        "selector_use_status_binding": original_status["selector_use_status_binding"],
        "selector_use_receipt_binding": original_status["selector_use_receipt_binding"],
        "activation_receipt_binding": original_status["activation_receipt_binding"],
        "consumption_receipt_binding": original_status["consumption_receipt_binding"],
        "selected_scope_classes": selected_scope_classes,
        "selected_scope_classes_hash": selected_scope_classes_hash,
        "original_receipt_chain_hash": original_receipt_chain_hash,
        "repeat_receipt_chain_hash": repeat_receipt_chain_hash,
        "original_negative_invariants_hash": original_negative_invariants_hash,
        "repeat_negative_invariants_hash": repeat_negative_invariants_hash,
        "use_status_hash_comparison": use_status_hash_comparison,
        "receipt_chain_hash_comparison": receipt_chain_hash_comparison,
        "selected_scope_classes_hash_comparison": selected_scope_classes_hash_comparison,
        "negative_invariants_hash_comparison": negative_invariants_hash_comparison,
        "trial_authority": {
            "source": "server_revalidated_consumption_receipt_use_status_projections",
            "original_status_available": original_status.get("status") == "available",
            "repeat_status_available": repeat_status.get("status") == "available",
            "browser_supplied_local_authority_rejected": True,
            "browser_supplied_raw_url_rejected": True,
            "process_execution_admitted": False,
        },
        "baseline_rollback": {
            "selector": selector_use.NON_SELECTED_CLASS_DEFAULT,
            "available": True,
            "non_selected_classes_remain_baseline": True,
        },
        "candidate_a_semantics": {"visual_lane_mode": "candidate_a_page_evidence_v1", "preserved": True},
        "candidate_b_scope_authority": {
            "document_processing_engine": (
                layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_ENGINE_SCOPE
            ),
            "visual_lane_mode": (
                layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_VISUAL_LANE_SCOPE
            ),
            "eligible_effective_pdf_default_preserved": True,
        },
        "operator_visible_repeatability_trial_status": {
            "trial_receipt_recorded": True,
            "trial_accepted": accepted,
            "selected_scope_class_count": len(selected_scope_classes),
            "redacted_trial_receipt_available": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_or_connector_secret_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_original_use_receipt_blocks_trial": True,
            "missing_repeat_use_receipt_blocks_trial": True,
            "stale_original_use_status_hash_blocks_trial": True,
            "stale_repeat_use_status_hash_blocks_trial": True,
            "mismatched_selected_classes_block_trial": True,
            "mismatched_readiness_audit_blocks_trial": True,
            "mismatched_runtime_or_selector_receipts_block_trial": True,
            "non_available_original_or_repeat_status_blocks_trial": True,
        },
        "default_scope_expansion_admitted": False,
        "actual_corpus_processing_execution_admitted": False,
        "actual_subprocess_spawn_admitted": False,
        "process_control_admitted": False,
        "selector_mutation_performed": False,
        "default_scope_mutation_performed": False,
        "source_expansion_admitted": False,
        "runtime_db_or_storage_expansion_admitted": False,
        "pdf_or_image_text_material_ingestion_admitted": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "auth_security_expansion_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "browser_storage_authority_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "negative_invariants": selector_use._negative_invariants(False),
        "next_allowed_actions": [
            "inspect the recorded Candidate B broader-scope repeatability trial receipt",
            "select a separately admitted rendered/status pass before adding operator UI controls",
        ],
    }


def _load_use_status(
    *,
    fields: Mapping[str, Any],
    prefix: str,
    request_id: str,
    selected_scope_classes: list[str],
) -> dict[str, Any]:
    expected_status_hash = selector_use._required_str(
        fields,
        f"{prefix}_use_receipt_status_hash",
        error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
    )
    status_payload = {
        "client_request_id": f"{request_id}:{prefix}-use-status",
        "status_mode": selector_use.CONSUMPTION_USE_STATUS_MODE,
        "operator_decision": selector_use.CONSUMPTION_USE_STATUS_OPERATOR_DECISION,
        "use_receipt_id": selector_use._required_storage_id(
            fields,
            f"{prefix}_use_receipt_id",
            prefix=selector_use.CONSUMPTION_USE_RECEIPT_PREFIX,
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "use_receipt_hash": selector_use._required_str(
            fields,
            f"{prefix}_use_receipt_hash",
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "consumption_receipt_id": selector_use._required_storage_id(
            fields,
            f"{prefix}_consumption_receipt_id",
            prefix=selector_use.CONSUMPTION_RECEIPT_PREFIX,
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "consumption_receipt_hash": selector_use._required_str(
            fields,
            f"{prefix}_consumption_receipt_hash",
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "activation_receipt_id": selector_use._required_storage_id(
            fields,
            f"{prefix}_activation_receipt_id",
            prefix=selector_use.ACTIVATION_RECEIPT_PREFIX,
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "activation_receipt_hash": selector_use._required_str(
            fields,
            f"{prefix}_activation_receipt_hash",
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "selector_use_status_hash": selector_use._required_str(
            fields,
            f"{prefix}_selector_use_status_hash",
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "selector_use_receipt_id": selector_use._required_storage_id(
            fields,
            f"{prefix}_selector_use_receipt_id",
            prefix=selector_use.RECEIPT_PREFIX,
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "selector_use_receipt_hash": selector_use._required_str(
            fields,
            f"{prefix}_selector_use_receipt_hash",
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "runtime_selection_receipt_id": selector_use._required_str(
            fields,
            f"{prefix}_runtime_selection_receipt_id",
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "runtime_selection_receipt_hash": selector_use._required_str(
            fields,
            f"{prefix}_runtime_selection_receipt_hash",
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "readiness_audit_id": selector_use._required_str(
            fields,
            f"{prefix}_readiness_audit_id",
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "readiness_audit_hash": selector_use._required_str(
            fields,
            f"{prefix}_readiness_audit_hash",
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        ),
        "selected_scope_classes": selected_scope_classes,
    }
    try:
        status = selector_use.inspect_candidate_b_broader_scope_consumption_receipt_use_status(
            status_payload
        )
    except selector_use.CandidateBBroaderScopeSelectorUseError as exc:
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            f"candidate_b_broader_scope_operator_repeatability_trial_{prefix}_use_status_invalid",
            "The repeatability trial could not revalidate the requested consumption-receipt use status.",
            http_status=exc.http_status,
            details={"authority_error_code": exc.code, "authority_error_details": exc.details},
        ) from exc
    if status.get("status") != "available" or status.get("use_receipt_status") != "recorded":
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            f"candidate_b_broader_scope_operator_repeatability_trial_{prefix}_use_status_not_available",
            "The repeatability trial requires available original and repeat use-status projections.",
            http_status=409,
            details={"received_status": status.get("status"), "use_receipt_status": status.get("use_receipt_status")},
        )
    if status.get("use_receipt_status_hash") != expected_status_hash:
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            f"candidate_b_broader_scope_operator_repeatability_trial_stale_{prefix}_use_status_hash",
            "The supplied use-status hash is stale or contradictory.",
            http_status=409,
            details={
                "expected": status.get("use_receipt_status_hash"),
                "received": expected_status_hash,
            },
        )
    return status


def _require_same_authority(
    *,
    original_status: Mapping[str, Any],
    repeat_status: Mapping[str, Any],
    selected_scope_classes: list[str],
) -> None:
    blocked: list[dict[str, Any]] = []
    for binding_name, fields in (
        ("readiness_audit_binding", ("readiness_audit_id", "readiness_audit_hash")),
        (
            "runtime_selection_receipt_binding",
            ("runtime_selection_receipt_id", "runtime_selection_receipt_hash"),
        ),
        ("selector_use_receipt_binding", ("selector_use_receipt_id", "selector_use_receipt_hash")),
        ("selector_use_status_binding", ("selector_use_status_hash",)),
        ("activation_receipt_binding", ("activation_receipt_id", "activation_receipt_hash")),
        ("consumption_receipt_binding", ("consumption_receipt_id", "consumption_receipt_hash")),
    ):
        original_binding = original_status.get(binding_name) or {}
        repeat_binding = repeat_status.get(binding_name) or {}
        for field in fields:
            if original_binding.get(field) != repeat_binding.get(field):
                blocked.append(
                    selector_use._reason(
                        "candidate_b_broader_scope_operator_repeatability_trial_authority_mismatch",
                        binding=binding_name,
                        field=field,
                        original=original_binding.get(field),
                        repeat=repeat_binding.get(field),
                    )
                )
    if selector_use._string_list(original_status.get("selected_scope_classes")) != selected_scope_classes:
        blocked.append(
            selector_use._reason(
                "candidate_b_broader_scope_operator_repeatability_trial_original_selected_classes_mismatch"
            )
        )
    if selector_use._string_list(repeat_status.get("selected_scope_classes")) != selected_scope_classes:
        blocked.append(
            selector_use._reason(
                "candidate_b_broader_scope_operator_repeatability_trial_repeat_selected_classes_mismatch"
            )
        )
    if blocked:
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            "candidate_b_broader_scope_operator_repeatability_trial_authority_mismatch",
            "The original and repeat use-status projections are not bound to the same authority chain.",
            http_status=409,
            details={"blocked_reasons": blocked},
        )


def _receipt_chain_hash(status: Mapping[str, Any]) -> str:
    return selector_use._stable_hash(
        {
            "readiness_audit_binding": status.get("readiness_audit_binding"),
            "runtime_selection_receipt_binding": status.get("runtime_selection_receipt_binding"),
            "selector_use_receipt_binding": status.get("selector_use_receipt_binding"),
            "selector_use_status_binding": status.get("selector_use_status_binding"),
            "activation_receipt_binding": status.get("activation_receipt_binding"),
            "consumption_receipt_binding": status.get("consumption_receipt_binding"),
        }
    )


def _comparison(original: Any, repeat: Any) -> str:
    return "match" if original == repeat else "delta"


def _status_summary(status: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": status.get("status"),
        "use_receipt_status": status.get("use_receipt_status"),
        "use_receipt_id": status.get("use_receipt_id"),
        "use_receipt_hash": status.get("use_receipt_hash"),
        "use_receipt_status_hash": status.get("use_receipt_status_hash"),
        "selected_scope_classes": status.get("selected_scope_classes"),
        "raw_local_path_exposed": status.get("raw_local_path_exposed"),
        "raw_url_exposed": status.get("raw_url_exposed"),
    }


def _write_trial_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    request_id: str,
    disposition: str,
    accepted: bool,
    authority_pair_hash: str,
    selected_scope_classes: list[str],
    selected_scope_classes_hash: str,
    original_status: Mapping[str, Any],
    repeat_status: Mapping[str, Any],
    original_receipt_chain_hash: str,
    repeat_receipt_chain_hash: str,
    original_negative_invariants_hash: str,
    repeat_negative_invariants_hash: str,
    use_status_hash_comparison: str,
    receipt_chain_hash_comparison: str,
    selected_scope_classes_hash_comparison: str,
    negative_invariants_hash_comparison: str,
) -> tuple[str, bool]:
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "trial_mode": TRIAL_MODE,
        "operator_decision": TRIAL_OPERATOR_DECISION,
        "operator_repeatability_trial_state": TRIAL_ACCEPTED_STATE if accepted else TRIAL_BLOCKED_STATE,
        "operator_repeatability_disposition": disposition,
        "request_id": request_id,
        "trial_receipt_id": receipt_id,
        "trial_receipt_hash": receipt_hash,
        "authority_pair_hash": authority_pair_hash,
        "selected_scope_classes": selected_scope_classes,
        "selected_scope_classes_hash": selected_scope_classes_hash,
        "original_use_status": _status_summary(original_status),
        "repeat_use_status": _status_summary(repeat_status),
        "readiness_audit_binding": original_status.get("readiness_audit_binding"),
        "runtime_selection_receipt_binding": original_status.get("runtime_selection_receipt_binding"),
        "selector_use_status_binding": original_status.get("selector_use_status_binding"),
        "selector_use_receipt_binding": original_status.get("selector_use_receipt_binding"),
        "activation_receipt_binding": original_status.get("activation_receipt_binding"),
        "consumption_receipt_binding": original_status.get("consumption_receipt_binding"),
        "original_receipt_chain_hash": original_receipt_chain_hash,
        "repeat_receipt_chain_hash": repeat_receipt_chain_hash,
        "original_negative_invariants_hash": original_negative_invariants_hash,
        "repeat_negative_invariants_hash": repeat_negative_invariants_hash,
        "use_status_hash_comparison": use_status_hash_comparison,
        "receipt_chain_hash_comparison": receipt_chain_hash_comparison,
        "selected_scope_classes_hash_comparison": selected_scope_classes_hash_comparison,
        "negative_invariants_hash_comparison": negative_invariants_hash_comparison,
        "append_only_repeatability_trial_receipt": True,
        "exclusive_trial_per_original_repeat_authority_pair": True,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "candidate_b_document_processing_engine_preserved": (
            layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_ENGINE_SCOPE
        ),
        "candidate_b_visual_lane_preserved": (
            layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_VISUAL_LANE_SCOPE
        ),
        "default_scope_expansion_admitted": False,
        "actual_corpus_processing_execution_admitted": False,
        "actual_subprocess_spawn_admitted": False,
        "process_control_admitted": False,
        "source_expansion_admitted": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "auth_security_expansion_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "browser_storage_authority_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "redaction_policy_id": REDACTION_POLICY_ID,
        "recorded_at": selector_use._server_time(),
    }
    target = selector_use._runtime_receipt_root(
        error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError
    ) / TRIAL_RECEIPT_DIR / f"{receipt_id}.json"
    if target.exists():
        existing = selector_use._read_required_receipt(
            target,
            error_cls=CandidateBBroaderScopeOperatorRepeatabilityTrialError,
        )
        if existing.get("trial_receipt_hash") != receipt_hash:
            raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
                "candidate_b_broader_scope_operator_repeatability_trial_receipt_conflict",
                "A repeatability trial already exists for this original/repeat authority pair.",
                http_status=409,
            )
        return f"candidate-b-broader-scope-repeatability-trial://{receipt_id}/{receipt_hash[:24]}", True
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise CandidateBBroaderScopeOperatorRepeatabilityTrialError(
            "candidate_b_broader_scope_operator_repeatability_trial_receipt_write_failed",
            "Candidate B broader-scope repeatability trial receipt could not be recorded.",
            http_status=409,
            details={"reason": exc.__class__.__name__},
        ) from exc
    return f"candidate-b-broader-scope-repeatability-trial://{receipt_id}/{receipt_hash[:24]}", False
