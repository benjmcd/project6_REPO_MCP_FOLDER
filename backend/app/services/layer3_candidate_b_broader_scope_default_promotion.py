from __future__ import annotations

import json
from typing import Any, Mapping

from app.services import (
    layer3_candidate_b_broader_scope_promotion_readiness,
    layer3_candidate_b_broader_scope_readiness,
    layer3_candidate_b_broader_scope_repeatability_trial,
    layer3_candidate_b_broader_scope_selector_use as selector_use,
)


SCHEMA_ID = "layer3.candidate_b_broader_eligible_corpus_default_scope_default_promotion.v1"
SCHEMA_VERSION = 1
PROMOTION_MODE = "candidate_b_broader_eligible_corpus_default_scope_default_promotion_runtime_v1"
OPERATOR_DECISION = "record_candidate_b_broader_scope_default_promotion"
SELECTED_STATE = "candidate_b_broader_eligible_corpus_default_scope_default_promotion_selected"
BLOCKED_STATE = "candidate_b_broader_eligible_corpus_default_scope_default_promotion_blocked"
RECEIPT_PREFIX = "cb-broader-scope-default-promotion"
RECEIPT_DIR = "broader-scope-default-promotion"
REDACTION_POLICY_ID = "candidate_b_broader_scope_default_promotion_redaction_v1"
NON_SELECTED_CLASS_DEFAULT = selector_use.NON_SELECTED_CLASS_DEFAULT
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
    "promotion_readiness_audit",
    "promotion_readiness_rendered_status",
    "promotion_readiness_closeout",
)


class CandidateBBroaderScopeDefaultPromotionError(
    selector_use.CandidateBBroaderScopeSelectorUseError
):
    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-broader-scope-default-promotion-error",
            "server_time": selector_use._server_time(),
            "status": "blocked",
            "mode": PROMOTION_MODE,
            "default_promotion_state": BLOCKED_STATE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_broader_scope_default_promotion(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = selector_use._required_str(
        fields,
        "client_request_id",
        error_cls=CandidateBBroaderScopeDefaultPromotionError,
    )
    promotion_mode = selector_use._required_str(
        fields,
        "promotion_mode",
        error_cls=CandidateBBroaderScopeDefaultPromotionError,
    )
    if promotion_mode != PROMOTION_MODE:
        raise CandidateBBroaderScopeDefaultPromotionError(
            "candidate_b_broader_scope_default_promotion_mode_not_admitted",
            "Only the frozen Candidate B broader-scope default-promotion runtime mode is admitted.",
            details={"expected_promotion_mode": PROMOTION_MODE, "received_promotion_mode": promotion_mode},
        )

    operator_decision = selector_use._required_str(
        fields,
        "operator_decision",
        error_cls=CandidateBBroaderScopeDefaultPromotionError,
    )
    if operator_decision != OPERATOR_DECISION:
        raise CandidateBBroaderScopeDefaultPromotionError(
            "candidate_b_broader_scope_default_promotion_decision_not_admitted",
            "The operator decision does not match the admitted Candidate B broader-scope default promotion.",
            details={"expected_operator_decision": OPERATOR_DECISION},
        )

    readiness_audit_id = selector_use._required_storage_id(
        fields,
        "promotion_readiness_audit_id",
        prefix="cb-broader-scope-promotion-readiness",
        error_cls=CandidateBBroaderScopeDefaultPromotionError,
    )
    readiness_audit_hash = selector_use._required_str(
        fields,
        "promotion_readiness_audit_hash",
        error_cls=CandidateBBroaderScopeDefaultPromotionError,
    )
    trial_receipt_id = selector_use._required_storage_id(
        fields,
        "trial_receipt_id",
        prefix=layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_RECEIPT_PREFIX,
        error_cls=CandidateBBroaderScopeDefaultPromotionError,
    )
    trial_receipt_hash = selector_use._required_str(
        fields,
        "trial_receipt_hash",
        error_cls=CandidateBBroaderScopeDefaultPromotionError,
    )
    production_policy_hash = selector_use._required_str(
        fields,
        "production_policy_hash",
        error_cls=CandidateBBroaderScopeDefaultPromotionError,
    )
    selected_scope_classes = selector_use._string_list(fields.get("selected_scope_classes"))

    blocked: list[dict[str, Any]] = []
    if not selected_scope_classes:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_selected_classes_missing"))
    invalid_classes = sorted(
        set(selected_scope_classes) - set(layer3_candidate_b_broader_scope_readiness.SCOPE_CLASSES)
    )
    if invalid_classes:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_default_promotion_unknown_scope_class",
                invalid_scope_classes=invalid_classes,
            )
        )
    if fields.get("operator_visible_status_confirmed") is not True:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_operator_visible_status_missing"))
    if fields.get("promotion_readiness_rendered_status_confirmed") is not True:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_rendered_status_missing"))
    if fields.get("promotion_readiness_closeout_confirmed") is not True:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_closeout_missing"))
    if fields.get("rollback_to_baseline_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_rollback_to_baseline_missing"))
    if fields.get("operator_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_operator_confirmation_missing"))

    audit_validation = _validate_promotion_readiness_audit(
        fields.get("promotion_readiness_audit"),
        expected_audit_id=readiness_audit_id,
        expected_audit_hash=readiness_audit_hash,
        expected_trial_receipt_id=trial_receipt_id,
        expected_trial_receipt_hash=trial_receipt_hash,
        expected_selected_scope_classes=selected_scope_classes,
        expected_production_policy_hash=production_policy_hash,
    )
    blocked.extend(audit_validation["blocked_reasons"])

    selected_scope_classes_hash = selector_use._stable_hash(
        {"selected_scope_classes": selected_scope_classes}
    )
    receipt_hash = selector_use._stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "promotion_mode": PROMOTION_MODE,
            "operator_decision": OPERATOR_DECISION,
            "promotion_readiness_audit_id": readiness_audit_id,
            "promotion_readiness_audit_hash": readiness_audit_hash,
            "trial_receipt_id": trial_receipt_id,
            "trial_receipt_hash": trial_receipt_hash,
            "selected_scope_classes": selected_scope_classes,
            "selected_scope_classes_hash": selected_scope_classes_hash,
            "production_policy_hash": production_policy_hash,
            "operator_visible_status_confirmed": fields.get("operator_visible_status_confirmed") is True,
            "promotion_readiness_rendered_status_confirmed": (
                fields.get("promotion_readiness_rendered_status_confirmed") is True
            ),
            "promotion_readiness_closeout_confirmed": (
                fields.get("promotion_readiness_closeout_confirmed") is True
            ),
            "rollback_to_baseline_confirmation": fields.get("rollback_to_baseline_confirmation") is True,
            "operator_confirmation": fields.get("operator_confirmation") is True,
            "required_authority_chain": list(REQUIRED_AUTHORITY_CHAIN),
        }
    )
    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    promotion_state = SELECTED_STATE if not blocked else BLOCKED_STATE
    receipt_ref = None
    receipt_status = "not_recorded"
    idempotent_replay = False
    if promotion_state == SELECTED_STATE:
        receipt_ref, idempotent_replay = _write_default_promotion_receipt(
            receipt_id=receipt_id,
            receipt_hash=receipt_hash,
            request_id=request_id,
            readiness_audit_id=readiness_audit_id,
            readiness_audit_hash=readiness_audit_hash,
            trial_receipt_id=trial_receipt_id,
            trial_receipt_hash=trial_receipt_hash,
            selected_scope_classes=selected_scope_classes,
            selected_scope_classes_hash=selected_scope_classes_hash,
            production_policy_hash=production_policy_hash,
            audit_summary=audit_validation["summary"],
        )
        receipt_status = "idempotent_replay" if idempotent_replay else "recorded"

    selected = promotion_state == SELECTED_STATE
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": selector_use._server_time(),
        "status": "selected" if selected else "blocked",
        "mode": PROMOTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "default_promotion_state": promotion_state,
        "default_promotion_receipt_id": receipt_id if selected else None,
        "default_promotion_receipt_hash": receipt_hash if selected else None,
        "default_promotion_receipt_ref": receipt_ref,
        "default_promotion_receipt_status": receipt_status,
        "idempotent_replay": idempotent_replay,
        "blocked_reasons": blocked,
        "required_promotion_authority_chain": list(REQUIRED_AUTHORITY_CHAIN),
        "promotion_readiness_audit_binding": audit_validation["summary"],
        "trial_receipt_binding": audit_validation["summary"].get("trial_receipt_binding", {}),
        "production_ownership_storage_policy": audit_validation["summary"].get(
            "production_ownership_storage_policy", {}
        ),
        "selected_scope_classes": selected_scope_classes,
        "selected_scope_classes_hash": selected_scope_classes_hash,
        "scope_class_policy": "receipt_bound_selected_classes_only",
        "default_scope_promotion_enabled_for_selected_classes": selected,
        "default_scope_policy_mutation_performed": selected,
        "default_scope_expansion_mutation_performed": selected,
        "current_default_scope_before_promotion": (
            "eligible_effective_pdfs_only_plus_receipt_bound_selected_classes_only"
        ),
        "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback": {
            "selector": NON_SELECTED_CLASS_DEFAULT,
            "available": fields.get("rollback_to_baseline_confirmation") is True,
            "non_selected_classes_remain_baseline": True,
        },
        "candidate_a_semantics": {"visual_lane_mode": "candidate_a_page_evidence_v1", "preserved": True},
        "candidate_b_scope_authority": {
            "document_processing_engine": layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_ENGINE_SCOPE,
            "visual_lane_mode": layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_VISUAL_LANE_SCOPE,
            "bundle_and_runtime_authority_remain_distinct": True,
        },
        "operator_visible_status_evidence": {
            "operator_visible_status_confirmed": fields.get("operator_visible_status_confirmed") is True,
            "promotion_readiness_rendered_status_confirmed": (
                fields.get("promotion_readiness_rendered_status_confirmed") is True
            ),
            "promotion_readiness_closeout_confirmed": (
                fields.get("promotion_readiness_closeout_confirmed") is True
            ),
            "redacted_default_promotion_receipt_available": receipt_ref is not None,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_or_stale_promotion_readiness_audit_blocks_promotion": True,
            "blocked_promotion_readiness_blocks_promotion": True,
            "selected_class_mismatch_blocks_promotion": True,
            "production_policy_mismatch_blocks_promotion": True,
            "operator_visible_status_missing_blocks_promotion": True,
            "rollback_confirmation_missing_blocks_promotion": True,
            "browser_supplied_default_policy_rejected": True,
        },
        "selector_mutation_performed": False,
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
        "negative_invariants": selector_use._negative_invariants(selected),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": (
            ["project Candidate B broader-scope default promotion status for the selected classes"]
            if selected
            else ["repair the blocked audit, selected classes, production policy, status, or rollback authority"]
        ),
    }


def _validate_promotion_readiness_audit(
    value: Any,
    *,
    expected_audit_id: str,
    expected_audit_hash: str,
    expected_trial_receipt_id: str,
    expected_trial_receipt_hash: str,
    expected_selected_scope_classes: list[str],
    expected_production_policy_hash: str,
) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    if not isinstance(value, Mapping):
        return {
            "blocked_reasons": [_reason("candidate_b_broader_scope_default_promotion_readiness_audit_missing")],
            "summary": {"binding_verified": False, "promotion_readiness_audit_id": expected_audit_id},
        }
    audit = value
    expected_fields = {
        "schema_id": layer3_candidate_b_broader_scope_promotion_readiness.SCHEMA_ID,
        "schema_version": layer3_candidate_b_broader_scope_promotion_readiness.SCHEMA_VERSION,
        "mode": layer3_candidate_b_broader_scope_promotion_readiness.READINESS_MODE,
        "operator_decision": layer3_candidate_b_broader_scope_promotion_readiness.OPERATOR_DECISION,
        "status": "ready",
        "promotion_readiness_state": layer3_candidate_b_broader_scope_promotion_readiness.READY_STATE,
        "promotion_readiness_audit_id": expected_audit_id,
        "promotion_readiness_audit_hash": expected_audit_hash,
    }
    for field, expected in expected_fields.items():
        if audit.get(field) != expected:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_default_promotion_readiness_audit_field_mismatch",
                    field=field,
                    expected=expected,
                    received=audit.get(field),
                )
            )
    recomputed_hash = _promotion_readiness_hash(audit)
    if recomputed_hash != expected_audit_hash:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_default_promotion_stale_readiness_audit_hash",
                expected=recomputed_hash,
                received=expected_audit_hash,
            )
        )
    if audit.get("blocked_reasons") != []:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_readiness_audit_blocked"))
    if audit.get("default_scope_promotion_ready_for_separate_selection") is not True:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_readiness_not_ready"))

    selected_scope_classes = selector_use._string_list(audit.get("selected_scope_classes"))
    if selected_scope_classes != expected_selected_scope_classes:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_default_promotion_selected_classes_mismatch",
                expected=expected_selected_scope_classes,
                received=selected_scope_classes,
            )
        )

    trial = audit.get("trial_receipt_binding")
    if not isinstance(trial, Mapping):
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_trial_binding_missing"))
        trial = {}
    if trial.get("binding_verified") is not True:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_trial_binding_not_verified"))
    _binding_equals(blocked, trial, "trial_receipt_id", expected_trial_receipt_id)
    _binding_equals(blocked, trial, "trial_receipt_hash", expected_trial_receipt_hash)

    policy = audit.get("production_ownership_storage_policy")
    if not isinstance(policy, Mapping):
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_production_policy_missing"))
        policy = {}
    if policy.get("binding_verified") is not True:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_production_policy_not_verified"))
    _binding_equals(blocked, policy, "policy_hash", expected_production_policy_hash)
    if policy.get("policy_runtime") != (
        layer3_candidate_b_broader_scope_promotion_readiness
        .REQUIRED_PRODUCTION_OWNERSHIP_STORAGE_POLICY
    ):
        blocked.append(
            _reason(
                "candidate_b_broader_scope_default_promotion_production_policy_runtime_mismatch",
                received=policy.get("policy_runtime"),
            )
        )

    status = audit.get("operator_visible_status_evidence")
    if not isinstance(status, Mapping) or status.get("operator_visible_status_confirmed") is not True:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_operator_status_not_verified"))
    rollback = audit.get("baseline_rollback")
    if not isinstance(rollback, Mapping) or rollback.get("available") is not True:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_baseline_rollback_unavailable"))
    if isinstance(rollback, Mapping) and rollback.get("selector") != NON_SELECTED_CLASS_DEFAULT:
        blocked.append(_reason("candidate_b_broader_scope_default_promotion_rollback_selector_mismatch"))

    for field in (
        "selector_mutation_performed",
        "default_scope_expansion_admitted",
        "default_scope_mutation_performed",
        "source_expansion_admitted",
        "runtime_db_or_storage_expansion_admitted",
        "pdf_or_image_text_material_ingestion_admitted",
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
        if audit.get(field) is not False:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_default_promotion_readiness_negative_invariant_drift",
                    field=field,
                    received=audit.get(field),
                )
            )
    return {
        "blocked_reasons": blocked,
        "summary": {
            "binding_verified": not blocked,
            "promotion_readiness_audit_id": audit.get("promotion_readiness_audit_id") or expected_audit_id,
            "promotion_readiness_audit_hash": audit.get("promotion_readiness_audit_hash") or expected_audit_hash,
            "required_state": layer3_candidate_b_broader_scope_promotion_readiness.READY_STATE,
            "trial_receipt_binding": dict(trial),
            "production_ownership_storage_policy": dict(policy),
            "selected_scope_classes": selected_scope_classes,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
    }


def _promotion_readiness_hash(audit: Mapping[str, Any]) -> str:
    trial = audit.get("trial_receipt_binding")
    if not isinstance(trial, Mapping):
        trial = {}
    policy = audit.get("production_ownership_storage_policy")
    if not isinstance(policy, Mapping):
        policy = {}
    status = audit.get("operator_visible_status_evidence")
    if not isinstance(status, Mapping):
        status = {}
    rollback = audit.get("baseline_rollback")
    if not isinstance(rollback, Mapping):
        rollback = {}
    return selector_use._stable_hash(
        {
            "schema_id": layer3_candidate_b_broader_scope_promotion_readiness.SCHEMA_ID,
            "schema_version": layer3_candidate_b_broader_scope_promotion_readiness.SCHEMA_VERSION,
            "readiness_mode": layer3_candidate_b_broader_scope_promotion_readiness.READINESS_MODE,
            "operator_decision": layer3_candidate_b_broader_scope_promotion_readiness.OPERATOR_DECISION,
            "trial_receipt_id": trial.get("trial_receipt_id"),
            "trial_receipt_hash": trial.get("trial_receipt_hash"),
            "trial_authority_hash": trial.get("trial_authority_hash"),
            "authority_pair_hash": trial.get("authority_pair_hash"),
            "selected_scope_classes": selector_use._string_list(audit.get("selected_scope_classes")),
            "production_policy_hash": policy.get("policy_hash"),
            "operator_visible_status_confirmed": status.get("operator_visible_status_confirmed") is True,
            "rollback_to_baseline_confirmation": rollback.get("available") is True,
            "operator_confirmation": audit.get("status") == "ready",
            "required_authority_chain": list(
                layer3_candidate_b_broader_scope_promotion_readiness.REQUIRED_AUTHORITY_CHAIN
            ),
        }
    )


def _write_default_promotion_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    request_id: str,
    readiness_audit_id: str,
    readiness_audit_hash: str,
    trial_receipt_id: str,
    trial_receipt_hash: str,
    selected_scope_classes: list[str],
    selected_scope_classes_hash: str,
    production_policy_hash: str,
    audit_summary: Mapping[str, Any],
) -> tuple[str, bool]:
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "promotion_mode": PROMOTION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "default_promotion_state": SELECTED_STATE,
        "request_id": request_id,
        "default_promotion_receipt_id": receipt_id,
        "default_promotion_receipt_hash": receipt_hash,
        "promotion_readiness_audit_id": readiness_audit_id,
        "promotion_readiness_audit_hash": readiness_audit_hash,
        "trial_receipt_id": trial_receipt_id,
        "trial_receipt_hash": trial_receipt_hash,
        "selected_scope_classes": selected_scope_classes,
        "selected_scope_classes_hash": selected_scope_classes_hash,
        "production_policy_hash": production_policy_hash,
        "required_promotion_authority_chain": list(REQUIRED_AUTHORITY_CHAIN),
        "promotion_readiness_audit_binding": dict(audit_summary),
        "default_scope_promotion_enabled_for_selected_classes": True,
        "default_scope_policy_mutation_performed": True,
        "default_scope_expansion_mutation_performed": True,
        "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "candidate_b_document_processing_engine_preserved": (
            layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_ENGINE_SCOPE
        ),
        "candidate_b_visual_lane_preserved": (
            layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_VISUAL_LANE_SCOPE
        ),
        "selector_mutation_performed": False,
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
        "redaction_policy_id": REDACTION_POLICY_ID,
        "recorded_at": selector_use._server_time(),
    }
    target = (
        selector_use._runtime_receipt_root(error_cls=CandidateBBroaderScopeDefaultPromotionError)
        / RECEIPT_DIR
        / f"{receipt_id}.json"
    )
    if target.exists():
        existing = selector_use._read_required_receipt(
            target,
            error_cls=CandidateBBroaderScopeDefaultPromotionError,
        )
        if existing.get("default_promotion_receipt_hash") != receipt_hash:
            raise CandidateBBroaderScopeDefaultPromotionError(
                "candidate_b_broader_scope_default_promotion_receipt_conflict",
                "A Candidate B broader-scope default-promotion receipt already exists for this authority.",
                http_status=409,
            )
        return f"candidate-b-broader-scope-default-promotion://{receipt_id}/{receipt_hash[:24]}", True
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        raise CandidateBBroaderScopeDefaultPromotionError(
            "candidate_b_broader_scope_default_promotion_receipt_write_failed",
            "Candidate B broader-scope default-promotion receipt could not be recorded.",
            http_status=409,
            details={"reason": exc.__class__.__name__},
        ) from exc
    return f"candidate-b-broader-scope-default-promotion://{receipt_id}/{receipt_hash[:24]}", False


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(_find_forbidden_fields(fields))
    if blocked:
        raise CandidateBBroaderScopeDefaultPromotionError(
            "candidate_b_broader_scope_default_promotion_forbidden_request_fields",
            "The default-promotion runtime does not admit caller paths, URLs, selectors, connectors, storage roots, or browser authority.",
            details={"blocked_fields": blocked},
        )
    return fields


def _find_forbidden_fields(value: Any, *, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key) in selector_use.FORBIDDEN_FIELDS and not _allowed_readiness_audit_field(path):
                found.append(path)
            found.extend(_find_forbidden_fields(child, prefix=path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_fields(child, prefix=f"{prefix}[{index}]"))
    return found


def _allowed_readiness_audit_field(path: str) -> bool:
    return path in {
        "promotion_readiness_audit.candidate_a_semantics.visual_lane_mode",
        "promotion_readiness_audit.candidate_b_scope_authority.document_processing_engine",
        "promotion_readiness_audit.candidate_b_scope_authority.visual_lane_mode",
    }


def _binding_equals(
    blocked: list[dict[str, Any]],
    binding: Mapping[str, Any],
    field: str,
    expected: Any,
) -> None:
    if binding.get(field) != expected:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_default_promotion_binding_field_mismatch",
                field=field,
                expected=expected,
                received=binding.get(field),
            )
        )


def _reason(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "details": details}
