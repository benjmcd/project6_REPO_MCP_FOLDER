from __future__ import annotations

from typing import Any, Mapping

from app.services import (
    layer3_candidate_b_broader_scope_readiness,
    layer3_candidate_b_broader_scope_repeatability_trial,
    layer3_candidate_b_broader_scope_selector_use as selector_use,
    layer3_candidate_b_operator_workflow_access_policy,
)


SCHEMA_ID = "layer3.candidate_b_broader_eligible_corpus_default_scope_promotion_readiness.v1"
SCHEMA_VERSION = 1
READINESS_MODE = "candidate_b_broader_eligible_corpus_default_scope_promotion_readiness_audit_v1"
OPERATOR_DECISION = "evaluate_candidate_b_broader_scope_default_promotion_readiness"
READY_STATE = (
    "candidate_b_broader_eligible_corpus_default_scope_promotion_ready_for_separate_selection"
)
BLOCKED_STATE = "candidate_b_broader_eligible_corpus_default_scope_promotion_readiness_blocked"
REQUIRED_PRODUCTION_OWNERSHIP_STORAGE_POLICY = (
    layer3_candidate_b_operator_workflow_access_policy.PROXY_OWNER_STORAGE_POLICY_RUNTIME
)
REQUIRED_STORAGE_ACCESS_POLICY = (
    layer3_candidate_b_operator_workflow_access_policy.STORAGE_ACCESS_POLICY
)
REQUIRED_AUTHORITY_CHAIN = (
    "readiness_audit",
    "runtime_selection",
    "selector_use",
    "selector_use_status",
    "selector_activation",
    "activation_consumption",
    "consumption_receipt_use",
    "consumption_receipt_use_status",
    "operator_repeatability_trial",
)


class CandidateBBroaderScopePromotionReadinessError(
    selector_use.CandidateBBroaderScopeSelectorUseError
):
    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-broader-scope-promotion-readiness-error",
            "server_time": selector_use._server_time(),
            "status": "blocked",
            "mode": READINESS_MODE,
            "promotion_readiness_state": BLOCKED_STATE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def evaluate_candidate_b_broader_scope_default_promotion_readiness(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = selector_use._normalise_payload(
        payload,
        error_cls=CandidateBBroaderScopePromotionReadinessError,
    )
    request_id = selector_use._required_str(
        fields,
        "client_request_id",
        error_cls=CandidateBBroaderScopePromotionReadinessError,
    )
    readiness_mode = selector_use._required_str(
        fields,
        "readiness_mode",
        error_cls=CandidateBBroaderScopePromotionReadinessError,
    )
    if readiness_mode != READINESS_MODE:
        raise CandidateBBroaderScopePromotionReadinessError(
            "candidate_b_broader_scope_promotion_readiness_mode_not_admitted",
            "Only the frozen Candidate B broader-scope promotion readiness audit mode is admitted.",
            details={"expected_readiness_mode": READINESS_MODE, "received_readiness_mode": readiness_mode},
        )

    operator_decision = selector_use._required_str(
        fields,
        "operator_decision",
        error_cls=CandidateBBroaderScopePromotionReadinessError,
    )
    if operator_decision != OPERATOR_DECISION:
        raise CandidateBBroaderScopePromotionReadinessError(
            "candidate_b_broader_scope_promotion_readiness_decision_not_admitted",
            "The operator decision does not match the admitted Candidate B broader-scope promotion readiness audit.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    selected_scope_classes = selector_use._string_list(fields.get("selected_scope_classes"))
    trial_receipt_id = selector_use._required_storage_id(
        fields,
        "trial_receipt_id",
        prefix=layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_RECEIPT_PREFIX,
        error_cls=CandidateBBroaderScopePromotionReadinessError,
    )
    trial_receipt_hash = selector_use._required_str(
        fields,
        "trial_receipt_hash",
        error_cls=CandidateBBroaderScopePromotionReadinessError,
    )
    trial_authority_hash = selector_use._required_str(
        fields,
        "trial_authority_hash",
        error_cls=CandidateBBroaderScopePromotionReadinessError,
    )
    authority_pair_hash = selector_use._required_str(
        fields,
        "authority_pair_hash",
        error_cls=CandidateBBroaderScopePromotionReadinessError,
    )

    blocked: list[dict[str, Any]] = []
    if not selected_scope_classes:
        blocked.append(_reason("candidate_b_broader_scope_promotion_readiness_selected_classes_missing"))
    invalid_classes = sorted(
        set(selected_scope_classes) - set(layer3_candidate_b_broader_scope_readiness.SCOPE_CLASSES)
    )
    if invalid_classes:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_promotion_readiness_unknown_scope_class",
                invalid_scope_classes=invalid_classes,
            )
        )
    if fields.get("operator_visible_status_confirmed") is not True:
        blocked.append(
            _reason("candidate_b_broader_scope_promotion_readiness_operator_visible_status_missing")
        )
    if fields.get("rollback_to_baseline_confirmation") is not True:
        blocked.append(
            _reason("candidate_b_broader_scope_promotion_readiness_rollback_to_baseline_missing")
        )
    if fields.get("operator_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_promotion_readiness_operator_confirmation_missing"))

    trial = _validate_trial_receipt(
        trial_receipt_id=trial_receipt_id,
        trial_receipt_hash=trial_receipt_hash,
        trial_authority_hash=trial_authority_hash,
        authority_pair_hash=authority_pair_hash,
        selected_scope_classes=selected_scope_classes,
    )
    policy = _validate_production_ownership_storage_policy(
        fields.get("production_ownership_storage_policy")
    )
    blocked.extend(trial["blocked_reasons"])
    blocked.extend(policy["blocked_reasons"])

    audit_hash = selector_use._stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "readiness_mode": READINESS_MODE,
            "operator_decision": OPERATOR_DECISION,
            "trial_receipt_id": trial_receipt_id,
            "trial_receipt_hash": trial_receipt_hash,
            "trial_authority_hash": trial_authority_hash,
            "authority_pair_hash": authority_pair_hash,
            "selected_scope_classes": selected_scope_classes,
            "production_policy_hash": policy["summary"].get("policy_hash"),
            "operator_visible_status_confirmed": fields.get("operator_visible_status_confirmed") is True,
            "rollback_to_baseline_confirmation": fields.get("rollback_to_baseline_confirmation") is True,
            "operator_confirmation": fields.get("operator_confirmation") is True,
            "required_authority_chain": list(REQUIRED_AUTHORITY_CHAIN),
        }
    )
    readiness_state = READY_STATE if not blocked else BLOCKED_STATE

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": selector_use._server_time(),
        "status": "ready" if readiness_state == READY_STATE else "blocked",
        "mode": READINESS_MODE,
        "operator_decision": OPERATOR_DECISION,
        "promotion_readiness_state": readiness_state,
        "promotion_readiness_audit_id": f"cb-broader-scope-promotion-readiness-{audit_hash[:24]}",
        "promotion_readiness_audit_hash": audit_hash,
        "blocked_reasons": blocked,
        "required_promotion_authority_chain": list(REQUIRED_AUTHORITY_CHAIN),
        "trial_receipt_binding": trial["summary"],
        "production_ownership_storage_policy": policy["summary"],
        "operator_visible_status_evidence": {
            "operator_visible_status_confirmed": fields.get("operator_visible_status_confirmed") is True,
            "operator_repeatability_trial_status_visible": fields.get("operator_visible_status_confirmed") is True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "selected_scope_classes": selected_scope_classes,
        "current_default_scope_before_promotion_readiness_audit": (
            f"{layer3_candidate_b_broader_scope_readiness.CURRENT_DEFAULT_SCOPE}"
            "_plus_receipt_bound_selected_classes_only"
        ),
        "scope_class_policy": "receipt_bound_selected_classes_only",
        "baseline_rollback": {
            "selector": selector_use.NON_SELECTED_CLASS_DEFAULT,
            "available": fields.get("rollback_to_baseline_confirmation") is True,
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
            "bundle_and_runtime_authority_remain_distinct": True,
        },
        "fail_closed_behavior": {
            "blocked_repeatability_disposition_blocks_promotion": True,
            "missing_or_stale_receipt_blocks_promotion": True,
            "mismatched_selected_classes_blocks_promotion": True,
            "missing_operator_visible_status_blocks_promotion": True,
            "missing_production_ownership_storage_policy_blocks_promotion": True,
            "baseline_rollback_missing_blocks_promotion": True,
        },
        "default_scope_promotion_ready_for_separate_selection": readiness_state == READY_STATE,
        "selector_mutation_admitted_now": False,
        "selector_mutation_performed": False,
        "default_scope_expansion_admitted": False,
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
        "next_allowed_actions": (
            ["select a separate broader default-scope mutation freeze for the accepted receipt-bound classes"]
            if readiness_state == READY_STATE
            else ["repair the blocked receipt, status, repeatability, rollback, or production policy authority"]
        ),
    }


def _validate_trial_receipt(
    *,
    trial_receipt_id: str,
    trial_receipt_hash: str,
    trial_authority_hash: str,
    authority_pair_hash: str,
    selected_scope_classes: list[str],
) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    receipt = _read_trial_receipt(trial_receipt_id, blocked)
    if receipt is None:
        return _trial_result(
            receipt_id=trial_receipt_id,
            receipt_hash=trial_receipt_hash,
            blocked=blocked,
        )

    _receipt_equals(blocked, receipt, "schema_id", layer3_candidate_b_broader_scope_repeatability_trial.SCHEMA_ID)
    _receipt_equals(blocked, receipt, "trial_mode", layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_MODE)
    _receipt_equals(
        blocked,
        receipt,
        "operator_decision",
        layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_OPERATOR_DECISION,
    )
    _receipt_equals(blocked, receipt, "trial_receipt_id", trial_receipt_id)
    _receipt_equals(blocked, receipt, "trial_receipt_hash", trial_receipt_hash)
    _receipt_equals(blocked, receipt, "trial_receipt_hash", trial_authority_hash)
    _receipt_equals(blocked, receipt, "authority_pair_hash", authority_pair_hash)
    if receipt.get("operator_repeatability_trial_state") != (
        layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_ACCEPTED_STATE
    ):
        blocked.append(
            _reason(
                "candidate_b_broader_scope_promotion_readiness_repeatability_trial_not_accepted",
                received=receipt.get("operator_repeatability_trial_state"),
            )
        )
    if receipt.get("operator_repeatability_disposition") not in (
        layer3_candidate_b_broader_scope_repeatability_trial.ACCEPTED_DISPOSITIONS
    ):
        blocked.append(
            _reason(
                "candidate_b_broader_scope_promotion_readiness_repeatability_disposition_not_ready",
                received=receipt.get("operator_repeatability_disposition"),
            )
        )
    if selector_use._string_list(receipt.get("selected_scope_classes")) != selected_scope_classes:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_promotion_readiness_selected_classes_mismatch",
                expected=selected_scope_classes,
                received=selector_use._string_list(receipt.get("selected_scope_classes")),
            )
        )
    for field in (
        "append_only_repeatability_trial_receipt",
        "exclusive_trial_per_original_repeat_authority_pair",
        "baseline_rollback_preserved",
        "candidate_a_semantics_preserved",
    ):
        if receipt.get(field) is not True:
            blocked.append(_reason("candidate_b_broader_scope_promotion_readiness_trial_flag_missing", field=field))
    for field in (
        "receipt_chain_hash_comparison",
        "selected_scope_classes_hash_comparison",
        "negative_invariants_hash_comparison",
    ):
        if receipt.get(field) != "match":
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_promotion_readiness_trial_authority_comparison_not_matching",
                    field=field,
                    received=receipt.get(field),
                )
            )
    for field in (
        "default_scope_expansion_admitted",
        "actual_corpus_processing_execution_admitted",
        "actual_subprocess_spawn_admitted",
        "process_control_admitted",
        "source_expansion_admitted",
        "provider_object_write_enabled",
        "connector_dispatch_enabled",
        "rag_vector_model_runtime_enabled",
        "auth_security_expansion_enabled",
        "full_mockup_activation_enabled",
        "frontend_durable_authority_enabled",
        "browser_storage_authority_enabled",
        "raw_local_path_exposed",
        "raw_url_exposed",
        "artifact_bytes_exposed",
    ):
        if receipt.get(field) is not False:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_promotion_readiness_trial_negative_invariant_failed",
                    field=field,
                    received=receipt.get(field),
                )
            )
    _validate_authority_bindings(receipt, blocked)
    return _trial_result(
        receipt_id=trial_receipt_id,
        receipt_hash=trial_receipt_hash,
        blocked=blocked,
        receipt=receipt,
    )


def _read_trial_receipt(
    trial_receipt_id: str,
    blocked: list[dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        root = selector_use._runtime_receipt_root(
            create=False,
            error_cls=CandidateBBroaderScopePromotionReadinessError,
        )
    except CandidateBBroaderScopePromotionReadinessError as exc:
        blocked.append(_reason(exc.code, **exc.details))
        return None
    path = (
        root
        / layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_RECEIPT_DIR
        / f"{trial_receipt_id}.json"
    )
    if not path.is_file():
        blocked.append(
            _reason(
                "candidate_b_broader_scope_promotion_readiness_trial_receipt_missing",
                trial_receipt_id=trial_receipt_id,
            )
        )
        return None
    try:
        return selector_use._read_required_receipt(
            path,
            error_cls=CandidateBBroaderScopePromotionReadinessError,
        )
    except CandidateBBroaderScopePromotionReadinessError as exc:
        blocked.append(_reason(exc.code, **exc.details))
        return None


def _validate_authority_bindings(receipt: Mapping[str, Any], blocked: list[dict[str, Any]]) -> None:
    for binding_name, required_fields in (
        ("readiness_audit_binding", ("readiness_audit_id", "readiness_audit_hash")),
        ("runtime_selection_receipt_binding", ("runtime_selection_receipt_id", "runtime_selection_receipt_hash")),
        ("selector_use_receipt_binding", ("selector_use_receipt_id", "selector_use_receipt_hash")),
        ("selector_use_status_binding", ("selector_use_status_hash",)),
        ("activation_receipt_binding", ("activation_receipt_id", "activation_receipt_hash")),
        ("consumption_receipt_binding", ("consumption_receipt_id", "consumption_receipt_hash")),
    ):
        binding = receipt.get(binding_name)
        if not isinstance(binding, Mapping):
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_promotion_readiness_authority_binding_missing",
                    binding=binding_name,
                )
            )
            continue
        missing = [field for field in required_fields if not str(binding.get(field) or "").strip()]
        if missing:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_promotion_readiness_authority_binding_field_missing",
                    binding=binding_name,
                    missing_fields=missing,
                )
            )
    for status_name in ("original_use_status", "repeat_use_status"):
        status = receipt.get(status_name)
        if not isinstance(status, Mapping) or not str(status.get("use_receipt_status_hash") or "").strip():
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_promotion_readiness_consumption_receipt_use_status_missing",
                    status=status_name,
                )
            )


def _validate_production_ownership_storage_policy(value: Any) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    if not isinstance(value, Mapping):
        return {
            "blocked_reasons": [
                _reason("candidate_b_broader_scope_promotion_readiness_production_policy_missing")
            ],
            "summary": {"available": False, "binding_verified": False},
        }
    policy_hash = str(value.get("policy_hash") or "").strip()
    if value.get("policy_runtime") != REQUIRED_PRODUCTION_OWNERSHIP_STORAGE_POLICY:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_promotion_readiness_production_policy_runtime_mismatch",
                expected=REQUIRED_PRODUCTION_OWNERSHIP_STORAGE_POLICY,
                received=value.get("policy_runtime"),
            )
        )
    if value.get("storage_access_policy") != REQUIRED_STORAGE_ACCESS_POLICY:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_promotion_readiness_storage_policy_mismatch",
                expected=REQUIRED_STORAGE_ACCESS_POLICY,
                received=value.get("storage_access_policy"),
            )
        )
    if value.get("policy_status") != "admitted":
        blocked.append(
            _reason(
                "candidate_b_broader_scope_promotion_readiness_production_policy_not_admitted",
                received=value.get("policy_status"),
            )
        )
    if len(policy_hash) != 64:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_promotion_readiness_production_policy_hash_invalid",
                received=policy_hash or None,
            )
        )
    return {
        "blocked_reasons": blocked,
        "summary": {
            "available": not blocked,
            "binding_verified": not blocked,
            "policy_runtime": value.get("policy_runtime"),
            "storage_access_policy": value.get("storage_access_policy"),
            "policy_status": value.get("policy_status"),
            "policy_hash": policy_hash or None,
            "required_policy_runtime": REQUIRED_PRODUCTION_OWNERSHIP_STORAGE_POLICY,
            "required_storage_access_policy": REQUIRED_STORAGE_ACCESS_POLICY,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_or_connector_secret_exposed": False,
        },
    }


def _trial_result(
    *,
    receipt_id: str,
    receipt_hash: str,
    blocked: list[dict[str, Any]],
    receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    receipt = receipt or {}
    return {
        "blocked_reasons": blocked,
        "summary": {
            "binding_verified": not blocked,
            "trial_receipt_id": receipt_id,
            "trial_receipt_hash": receipt_hash,
            "trial_receipt_ref": (
                f"candidate-b-broader-scope-repeatability-trial://{receipt_id}/{receipt_hash[:24]}"
            ),
            "trial_authority_hash": receipt.get("trial_receipt_hash"),
            "authority_pair_hash": receipt.get("authority_pair_hash"),
            "operator_repeatability_trial_state": receipt.get("operator_repeatability_trial_state"),
            "operator_repeatability_disposition": receipt.get("operator_repeatability_disposition"),
            "selected_scope_classes": selector_use._string_list(receipt.get("selected_scope_classes")),
            "selected_scope_classes_hash": receipt.get("selected_scope_classes_hash"),
            "readiness_audit_binding": receipt.get("readiness_audit_binding") or {},
            "runtime_selection_receipt_binding": receipt.get("runtime_selection_receipt_binding") or {},
            "selector_use_status_binding": receipt.get("selector_use_status_binding") or {},
            "selector_use_receipt_binding": receipt.get("selector_use_receipt_binding") or {},
            "activation_receipt_binding": receipt.get("activation_receipt_binding") or {},
            "consumption_receipt_binding": receipt.get("consumption_receipt_binding") or {},
            "receipt_chain_hash_comparison": receipt.get("receipt_chain_hash_comparison"),
            "negative_invariants_hash_comparison": receipt.get("negative_invariants_hash_comparison"),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
    }


def _receipt_equals(
    blocked: list[dict[str, Any]],
    receipt: Mapping[str, Any],
    field: str,
    expected: Any,
) -> None:
    if receipt.get(field) != expected:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_promotion_readiness_trial_receipt_field_mismatch",
                field=field,
                expected=expected,
                received=receipt.get(field),
            )
        )


def _reason(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "details": details}
