from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_candidate_b_broader_scope_readiness
from app.services import layer3_candidate_b_broader_scope_runtime


SCHEMA_ID = "layer3.candidate_b_broader_eligible_corpus_default_scope_selector_use.v1"
STATUS_SCHEMA_ID = "layer3.candidate_b_broader_eligible_corpus_default_scope_selector_use_status.v1"
ACTIVATION_SCHEMA_ID = "layer3.candidate_b_broader_eligible_corpus_default_scope_selector_activation.v1"
CONSUMPTION_SCHEMA_ID = (
    "layer3.candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption.v1"
)
CONSUMPTION_USE_SCHEMA_ID = (
    "layer3.candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use.v1"
)
SCHEMA_VERSION = 1
RUNTIME_MODE = "candidate_b_broader_eligible_corpus_default_scope_selector_use_runtime_v1"
STATUS_MODE = "candidate_b_broader_eligible_corpus_default_scope_selector_use_status_v1"
ACTIVATION_MODE = "candidate_b_broader_eligible_corpus_default_scope_selector_activation_runtime_v1"
CONSUMPTION_MODE = (
    "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_runtime_v1"
)
CONSUMPTION_USE_MODE = "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_runtime_v1"
STATUS_OPERATOR_DECISION = "inspect_candidate_b_broader_eligible_corpus_default_scope_selector_use_status"
SELECTED_STATE = "candidate_b_broader_eligible_corpus_default_scope_selector_use_selected"
BLOCKED_STATE = "candidate_b_broader_eligible_corpus_default_scope_selector_use_blocked"
ACTIVATION_SELECTED_STATE = "candidate_b_broader_eligible_corpus_default_scope_selector_activation_selected"
ACTIVATION_BLOCKED_STATE = "candidate_b_broader_eligible_corpus_default_scope_selector_activation_blocked"
CONSUMPTION_SELECTED_STATE = (
    "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_selected"
)
CONSUMPTION_BLOCKED_STATE = (
    "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_blocked"
)
CONSUMPTION_USE_SELECTED_STATE = (
    "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_selected"
)
CONSUMPTION_USE_BLOCKED_STATE = (
    "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_blocked"
)
SOURCE_RUNTIME_SCHEMA_ID = layer3_candidate_b_broader_scope_runtime.SCHEMA_ID
SOURCE_RUNTIME_MODE = layer3_candidate_b_broader_scope_runtime.RUNTIME_MODE
SOURCE_RUNTIME_SELECTED_STATE = layer3_candidate_b_broader_scope_runtime.SELECTED_STATE
CURRENT_DEFAULT_SCOPE = layer3_candidate_b_broader_scope_readiness.CURRENT_DEFAULT_SCOPE
NON_SELECTED_CLASS_DEFAULT = "baseline"
RECEIPT_PREFIX = "cb-broader-scope-selector-use"
ACTIVATION_RECEIPT_PREFIX = "cb-broader-scope-selector-activation"
CONSUMPTION_RECEIPT_PREFIX = "cb-broader-scope-activation-consumption"
CONSUMPTION_USE_RECEIPT_PREFIX = "cb-broader-scope-consumption-receipt-use"
REDACTION_POLICY_ID = "candidate_b_broader_scope_selector_use_redaction_v1"
ACTIVATION_REDACTION_POLICY_ID = "candidate_b_broader_scope_selector_activation_redaction_v1"
CONSUMPTION_REDACTION_POLICY_ID = "candidate_b_broader_scope_activation_consumption_redaction_v1"
CONSUMPTION_USE_REDACTION_POLICY_ID = "candidate_b_broader_scope_consumption_receipt_use_redaction_v1"
SELECTOR_AUTHORITY_SOURCE = "redacted_candidate_b_broader_scope_runtime_receipt"
ACTIVATION_AUTHORITY_SOURCE = "server_revalidated_selector_use_status"
CONSUMPTION_AUTHORITY_SOURCE = "redacted_candidate_b_broader_scope_selector_activation_receipt"
CONSUMPTION_USE_AUTHORITY_SOURCE = "redacted_candidate_b_broader_scope_activation_consumption_receipt"

FORBIDDEN_FIELDS = {
    "path",
    "paths",
    "directory",
    "local_directory",
    "local_path",
    "url",
    "urls",
    "file",
    "files",
    "file_bytes",
    "document_processing_engine",
    "visual_lane_mode",
    "default_selector",
    "make_default",
    "candidate_b_default",
    "candidate_b_default_enabled",
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
    "raw_local_path",
    "raw_url",
    "provider_secret",
    "connector_secret",
}


class CandidateBBroaderScopeSelectorUseError(Exception):
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
            "request_id": "candidate-b-broader-scope-selector-use-error",
            "server_time": _server_time(),
            "status": "blocked",
            "mode": RUNTIME_MODE,
            "selector_use_state": BLOCKED_STATE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class CandidateBBroaderScopeSelectorUseStatusError(CandidateBBroaderScopeSelectorUseError):
    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": STATUS_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-broader-scope-selector-use-status-error",
            "server_time": _server_time(),
            "status": "blocked",
            "mode": STATUS_MODE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class CandidateBBroaderScopeSelectorActivationError(CandidateBBroaderScopeSelectorUseError):
    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": ACTIVATION_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-broader-scope-selector-activation-error",
            "server_time": _server_time(),
            "status": "blocked",
            "mode": ACTIVATION_MODE,
            "selector_activation_state": ACTIVATION_BLOCKED_STATE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class CandidateBBroaderScopeActivationConsumptionError(CandidateBBroaderScopeSelectorUseError):
    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": CONSUMPTION_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-broader-scope-activation-consumption-error",
            "server_time": _server_time(),
            "status": "blocked",
            "mode": CONSUMPTION_MODE,
            "activation_receipt_consumption_state": CONSUMPTION_BLOCKED_STATE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


class CandidateBBroaderScopeConsumptionReceiptUseError(CandidateBBroaderScopeSelectorUseError):
    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": CONSUMPTION_USE_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-broader-scope-consumption-receipt-use-error",
            "server_time": _server_time(),
            "status": "blocked",
            "mode": CONSUMPTION_USE_MODE,
            "consumption_receipt_use_state": CONSUMPTION_USE_BLOCKED_STATE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def record_candidate_b_broader_scope_selector_use(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required_str(fields, "client_request_id")
    selector_use_mode = _required_str(fields, "selector_use_mode")
    if selector_use_mode != RUNTIME_MODE:
        raise CandidateBBroaderScopeSelectorUseError(
            "candidate_b_broader_scope_selector_use_mode_not_admitted",
            "Only the frozen Candidate B broader eligible-corpus selector-use runtime mode is admitted.",
            details={"expected_selector_use_mode": RUNTIME_MODE, "received_selector_use_mode": selector_use_mode},
        )

    source_receipt_id = _required_str(fields, "runtime_selection_receipt_id")
    source_receipt_hash = _required_str(fields, "runtime_selection_receipt_hash")
    selected_scope_classes = _string_list(fields.get("selected_scope_classes"))

    blocked: list[dict[str, Any]] = []
    if fields.get("operator_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_selector_use_operator_confirmation_missing"))
    if fields.get("rollback_to_baseline_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_selector_use_rollback_to_baseline_missing"))
    if not selected_scope_classes:
        blocked.append(_reason("candidate_b_broader_scope_selector_use_no_selected_scope_class"))

    source_summary = _validate_source_runtime_receipt(
        receipt_id=source_receipt_id,
        receipt_hash=source_receipt_hash,
        selected_scope_classes=selected_scope_classes,
    )
    blocked.extend(source_summary["blocked_reasons"])

    receipt_hash = _stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "selector_use_mode": RUNTIME_MODE,
            "source_runtime_schema_id": SOURCE_RUNTIME_SCHEMA_ID,
            "source_runtime_mode": SOURCE_RUNTIME_MODE,
            "runtime_selection_receipt_id": source_receipt_id,
            "runtime_selection_receipt_hash": source_receipt_hash,
            "selected_scope_classes": selected_scope_classes,
            "selector_authority_source": SELECTOR_AUTHORITY_SOURCE,
            "current_default_scope_before_use": CURRENT_DEFAULT_SCOPE,
            "non_selected_class_default_preserved": NON_SELECTED_CLASS_DEFAULT,
            "baseline_rollback_preserved": fields.get("rollback_to_baseline_confirmation") is True,
            "candidate_a_semantics_preserved": True,
            "redaction_policy_id": REDACTION_POLICY_ID,
        }
    )
    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    selector_use_state = SELECTED_STATE if not blocked else BLOCKED_STATE
    selector_use_receipt_ref = None
    selector_use_receipt_status = "not_recorded"
    if selector_use_state == SELECTED_STATE:
        selector_use_receipt_ref = _write_selector_use_receipt(
            receipt_id=receipt_id,
            receipt_hash=receipt_hash,
            request_id=request_id,
            source_receipt_id=source_receipt_id,
            source_receipt_hash=source_receipt_hash,
            selected_scope_classes=selected_scope_classes,
            source_summary=source_summary["summary"],
        )
        selector_use_receipt_status = "recorded"

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "selected" if selector_use_state == SELECTED_STATE else "blocked",
        "mode": RUNTIME_MODE,
        "selector_use_state": selector_use_state,
        "selector_use_receipt_id": receipt_id if selector_use_state == SELECTED_STATE else None,
        "selector_use_receipt_hash": receipt_hash if selector_use_state == SELECTED_STATE else None,
        "selector_use_receipt_ref": selector_use_receipt_ref,
        "selector_use_receipt_status": selector_use_receipt_status,
        "blocked_reasons": blocked,
        "runtime_selection_receipt_binding": {
            "schema_id": SOURCE_RUNTIME_SCHEMA_ID,
            "mode": SOURCE_RUNTIME_MODE,
            "required_state": SOURCE_RUNTIME_SELECTED_STATE,
            "runtime_selection_receipt_id": source_receipt_id,
            "runtime_selection_receipt_hash": source_receipt_hash,
            "binding_verified": not source_summary["blocked_reasons"],
        },
        "selector_authority": {
            "source": SELECTOR_AUTHORITY_SOURCE,
            "selected_scope_classes_source": "selected_scope_classes_from_matching_runtime_receipt",
            "receipt_bound": selector_use_state == SELECTED_STATE,
            "stale_authority_rejected": bool(source_summary["blocked_reasons"]),
        },
        "selected_scope_classes": selected_scope_classes,
        "current_default_scope_before_use": CURRENT_DEFAULT_SCOPE,
        "default_scope_enabled_for_selected_classes": selector_use_state == SELECTED_STATE,
        "non_selected_class_default_preserved": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback": {
            "selector": NON_SELECTED_CLASS_DEFAULT,
            "available": fields.get("rollback_to_baseline_confirmation") is True,
            "depends_on_candidate_b_artifacts": False,
        },
        "candidate_a_semantics": {"visual_lane_mode": "candidate_a_page_evidence_v1", "preserved": True},
        "candidate_b_scope_authority": {
            "document_processing_engine": layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_ENGINE_SCOPE,
            "visual_lane_mode": layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_VISUAL_LANE_SCOPE,
            "bundle_and_runtime_authority_remain_distinct": True,
        },
        "operator_visible_selector_status": {
            "selector_use_recorded": selector_use_state == SELECTED_STATE,
            "selected_scope_class_count": len(selected_scope_classes) if selector_use_state == SELECTED_STATE else 0,
            "redacted_selector_use_receipt_available": selector_use_receipt_ref is not None,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_or_connector_secret_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_runtime_receipt_blocks_selector_use": True,
            "blocked_runtime_receipt_blocks_selector_use": True,
            "stale_runtime_receipt_hash_blocks_selector_use": True,
            "stale_readiness_audit_hash_blocks_selector_use": True,
            "unknown_scope_class_blocks_selector_use": True,
            "unselected_scope_class_blocks_selector_use": True,
            "missing_rollback_confirmation_blocks_selector_use": True,
            "candidate_a_semantic_drift_blocks_selector_use": True,
        },
        "default_scope_expansion_enabled": selector_use_state == SELECTED_STATE,
        "selector_use_authority_recorded": selector_use_state == SELECTED_STATE,
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
        "negative_invariants": _negative_invariants(selector_use_state == SELECTED_STATE),
        "next_allowed_actions": (
            ["use selector-use receipt for exact broader Candidate B selected classes"]
            if selector_use_state == SELECTED_STATE
            else ["repair or bind a selected broader-scope runtime receipt before selector use"]
        ),
    }


def inspect_candidate_b_broader_scope_selector_use_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload, error_cls=CandidateBBroaderScopeSelectorUseStatusError)
    request_id = _required_str(fields, "client_request_id", error_cls=CandidateBBroaderScopeSelectorUseStatusError)
    status_mode = _required_str(fields, "status_mode", error_cls=CandidateBBroaderScopeSelectorUseStatusError)
    if status_mode != STATUS_MODE:
        raise CandidateBBroaderScopeSelectorUseStatusError(
            "candidate_b_broader_scope_selector_use_status_mode_not_admitted",
            "Only the frozen Candidate B broader eligible-corpus selector-use status mode is admitted.",
            details={"expected_status_mode": STATUS_MODE, "received_status_mode": status_mode},
        )
    operator_decision = _required_str(
        fields,
        "operator_decision",
        error_cls=CandidateBBroaderScopeSelectorUseStatusError,
    )
    if operator_decision != STATUS_OPERATOR_DECISION:
        raise CandidateBBroaderScopeSelectorUseStatusError(
            "candidate_b_broader_scope_selector_use_status_decision_not_admitted",
            "The operator decision does not match the admitted selector-use status inspection.",
            details={"expected_operator_decision": STATUS_OPERATOR_DECISION},
        )

    selector_use_receipt_id = _required_storage_id(
        fields,
        "selector_use_receipt_id",
        prefix=RECEIPT_PREFIX,
        error_cls=CandidateBBroaderScopeSelectorUseStatusError,
    )
    selector_use_receipt_hash = _required_str(
        fields,
        "selector_use_receipt_hash",
        error_cls=CandidateBBroaderScopeSelectorUseStatusError,
    )
    runtime_selection_receipt_id = _required_str(
        fields,
        "runtime_selection_receipt_id",
        error_cls=CandidateBBroaderScopeSelectorUseStatusError,
    )
    runtime_selection_receipt_hash = _required_str(
        fields,
        "runtime_selection_receipt_hash",
        error_cls=CandidateBBroaderScopeSelectorUseStatusError,
    )
    receipt = _read_selector_use_receipt(selector_use_receipt_id)
    blocked = _validate_selector_use_receipt(
        receipt=receipt,
        selector_use_receipt_id=selector_use_receipt_id,
        selector_use_receipt_hash=selector_use_receipt_hash,
        runtime_selection_receipt_id=runtime_selection_receipt_id,
        runtime_selection_receipt_hash=runtime_selection_receipt_hash,
    )
    selected_scope_classes = _string_list(receipt.get("selected_scope_classes"))
    runtime_summary = _validate_source_runtime_receipt(
        receipt_id=runtime_selection_receipt_id,
        receipt_hash=runtime_selection_receipt_hash,
        selected_scope_classes=selected_scope_classes,
        create_root=False,
        error_cls=CandidateBBroaderScopeSelectorUseStatusError,
    )
    blocked.extend(runtime_summary["blocked_reasons"])
    if blocked:
        raise CandidateBBroaderScopeSelectorUseStatusError(
            "candidate_b_broader_scope_selector_use_status_authority_invalid",
            "The selected Candidate B broader-scope selector-use receipt is missing, stale, or contradictory.",
            http_status=409,
            details={"blocked_reasons": blocked},
        )

    status_hash = _stable_hash(
        {
            "schema_id": STATUS_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "status_mode": STATUS_MODE,
            "selector_use_receipt_id": selector_use_receipt_id,
            "selector_use_receipt_hash": selector_use_receipt_hash,
            "runtime_selection_receipt_id": runtime_selection_receipt_id,
            "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
            "selected_scope_classes": selected_scope_classes,
            "selector_authority_source": SELECTOR_AUTHORITY_SOURCE,
            "redaction_policy_id": REDACTION_POLICY_ID,
        }
    )
    return {
        "schema_id": STATUS_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "available",
        "mode": STATUS_MODE,
        "operator_decision": STATUS_OPERATOR_DECISION,
        "selector_use_status_hash": status_hash,
        "selector_use_receipt_id": selector_use_receipt_id,
        "selector_use_receipt_hash": selector_use_receipt_hash,
        "selector_use_receipt_status": "recorded",
        "selector_use_state": SELECTED_STATE,
        "runtime_selection_receipt_binding": {
            "schema_id": SOURCE_RUNTIME_SCHEMA_ID,
            "mode": SOURCE_RUNTIME_MODE,
            "required_state": SOURCE_RUNTIME_SELECTED_STATE,
            "runtime_selection_receipt_id": runtime_selection_receipt_id,
            "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
            "binding_verified": True,
        },
        "selector_authority": {
            "source": SELECTOR_AUTHORITY_SOURCE,
            "selected_scope_classes_source": "selected_scope_classes_from_matching_selector_use_receipt",
            "receipt_bound": True,
            "stale_authority_rejected": True,
        },
        "operator_visible_selector_status": {
            "selector_use_recorded": True,
            "selected_scope_class_count": len(selected_scope_classes),
            "redacted_selector_use_receipt_available": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_or_connector_secret_exposed": False,
        },
        "selected_scope_classes": selected_scope_classes,
        "current_default_scope_before_use": CURRENT_DEFAULT_SCOPE,
        "default_scope_enabled_for_selected_classes": True,
        "non_selected_class_default_preserved": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback": {"selector": NON_SELECTED_CLASS_DEFAULT, "available": True},
        "candidate_a_semantics_preserved": True,
        "selector_mutation_performed": False,
        "source_expansion_admitted": False,
        "runtime_db_or_storage_expansion_admitted": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "auth_security_expansion_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "browser_storage_authority_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "negative_invariants": _negative_invariants(True),
        "next_allowed_actions": [
            "use this read-only selector-use status when evaluating broader Candidate B default-scope closeout",
            "inspect downstream operator status before any broader default selector promotion",
        ],
    }


def record_candidate_b_broader_scope_selector_activation(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload, error_cls=CandidateBBroaderScopeSelectorActivationError)
    request_id = _required_str(fields, "client_request_id", error_cls=CandidateBBroaderScopeSelectorActivationError)
    activation_mode = _required_str(fields, "activation_mode", error_cls=CandidateBBroaderScopeSelectorActivationError)
    if activation_mode != ACTIVATION_MODE:
        raise CandidateBBroaderScopeSelectorActivationError(
            "candidate_b_broader_scope_selector_activation_mode_not_admitted",
            "Only the frozen Candidate B broader eligible-corpus selector activation runtime mode is admitted.",
            details={"expected_activation_mode": ACTIVATION_MODE, "received_activation_mode": activation_mode},
        )

    selector_use_status_hash = _required_str(
        fields,
        "selector_use_status_hash",
        error_cls=CandidateBBroaderScopeSelectorActivationError,
    )
    selector_use_receipt_id = _required_storage_id(
        fields,
        "selector_use_receipt_id",
        prefix=RECEIPT_PREFIX,
        error_cls=CandidateBBroaderScopeSelectorActivationError,
    )
    selector_use_receipt_hash = _required_str(
        fields,
        "selector_use_receipt_hash",
        error_cls=CandidateBBroaderScopeSelectorActivationError,
    )
    runtime_selection_receipt_id = _required_str(
        fields,
        "runtime_selection_receipt_id",
        error_cls=CandidateBBroaderScopeSelectorActivationError,
    )
    runtime_selection_receipt_hash = _required_str(
        fields,
        "runtime_selection_receipt_hash",
        error_cls=CandidateBBroaderScopeSelectorActivationError,
    )
    selected_scope_classes = _string_list(fields.get("selected_scope_classes"))

    blocked: list[dict[str, Any]] = []
    if fields.get("operator_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_selector_activation_operator_confirmation_missing"))
    if fields.get("rollback_to_baseline_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_selector_activation_rollback_to_baseline_missing"))
    if not selected_scope_classes:
        blocked.append(_reason("candidate_b_broader_scope_selector_activation_no_selected_scope_class"))

    status_summary: dict[str, Any] | None = None
    runtime_summary: dict[str, Any] | None = None
    try:
        status_summary = inspect_candidate_b_broader_scope_selector_use_status(
            {
                "client_request_id": f"{request_id}:selector-use-status",
                "status_mode": STATUS_MODE,
                "operator_decision": STATUS_OPERATOR_DECISION,
                "selector_use_receipt_id": selector_use_receipt_id,
                "selector_use_receipt_hash": selector_use_receipt_hash,
                "runtime_selection_receipt_id": runtime_selection_receipt_id,
                "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
            }
        )
    except CandidateBBroaderScopeSelectorUseError as exc:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_selector_activation_status_authority_invalid",
                authority_error_code=exc.code,
                authority_error_details=exc.details,
            )
        )

    if status_summary is not None:
        if status_summary.get("selector_use_status_hash") != selector_use_status_hash:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_selector_activation_stale_status_hash",
                    expected=status_summary.get("selector_use_status_hash"),
                    received=selector_use_status_hash,
                )
            )
        if status_summary.get("selector_use_state") != SELECTED_STATE:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_selector_activation_status_not_selected",
                    received=status_summary.get("selector_use_state"),
                )
            )
        status_classes = _string_list(status_summary.get("selected_scope_classes"))
        if selected_scope_classes != status_classes:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_selector_activation_selected_classes_do_not_match_status",
                    expected=status_classes,
                    received=selected_scope_classes,
                )
            )
        invalid_classes = sorted(
            set(selected_scope_classes) - set(layer3_candidate_b_broader_scope_readiness.SCOPE_CLASSES)
        )
        if invalid_classes:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_selector_activation_unknown_scope_class",
                    invalid_scope_classes=invalid_classes,
                )
            )
        unselected_classes = sorted(set(selected_scope_classes) - set(status_classes))
        if unselected_classes:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_selector_activation_unselected_scope_class",
                    unselected_scope_classes=unselected_classes,
                )
            )

        runtime_summary = _validate_source_runtime_receipt(
            receipt_id=runtime_selection_receipt_id,
            receipt_hash=runtime_selection_receipt_hash,
            selected_scope_classes=status_classes,
            create_root=False,
            error_cls=CandidateBBroaderScopeSelectorActivationError,
        )
        blocked.extend(
            [
                _reason(
                    "candidate_b_broader_scope_selector_activation_runtime_authority_invalid",
                    runtime_blocked_reason=reason,
                )
                for reason in runtime_summary["blocked_reasons"]
            ]
        )

    runtime_source_summary = runtime_summary["summary"] if runtime_summary is not None else {}
    readiness_audit_id = str(runtime_source_summary.get("readiness_audit_id") or "")
    readiness_audit_hash = str(runtime_source_summary.get("readiness_audit_hash") or "")
    activation_hash = _stable_hash(
        {
            "schema_id": ACTIVATION_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "activation_mode": ACTIVATION_MODE,
            "activation_authority_source": ACTIVATION_AUTHORITY_SOURCE,
            "selector_use_status_hash": selector_use_status_hash,
            "selector_use_receipt_id": selector_use_receipt_id,
            "selector_use_receipt_hash": selector_use_receipt_hash,
            "runtime_selection_receipt_id": runtime_selection_receipt_id,
            "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
            "readiness_audit_id": readiness_audit_id,
            "readiness_audit_hash": readiness_audit_hash,
            "selected_scope_classes": selected_scope_classes,
            "current_default_before_activation_runtime": CURRENT_DEFAULT_SCOPE,
            "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
            "baseline_rollback_preserved": fields.get("rollback_to_baseline_confirmation") is True,
            "candidate_a_semantics_preserved": True,
            "redaction_policy_id": ACTIVATION_REDACTION_POLICY_ID,
        }
    )
    activation_receipt_id = f"{ACTIVATION_RECEIPT_PREFIX}-{activation_hash[:24]}"
    activation_state = ACTIVATION_SELECTED_STATE if not blocked else ACTIVATION_BLOCKED_STATE
    activation_receipt_ref = None
    activation_receipt_status = "not_recorded"
    if activation_state == ACTIVATION_SELECTED_STATE:
        activation_receipt_ref = _write_selector_activation_receipt(
            receipt_id=activation_receipt_id,
            receipt_hash=activation_hash,
            request_id=request_id,
            selector_use_status_hash=selector_use_status_hash,
            selector_use_receipt_id=selector_use_receipt_id,
            selector_use_receipt_hash=selector_use_receipt_hash,
            runtime_selection_receipt_id=runtime_selection_receipt_id,
            runtime_selection_receipt_hash=runtime_selection_receipt_hash,
            readiness_audit_id=readiness_audit_id,
            readiness_audit_hash=readiness_audit_hash,
            selected_scope_classes=selected_scope_classes,
        )
        activation_receipt_status = "recorded"

    activation_enabled = activation_state == ACTIVATION_SELECTED_STATE
    return {
        "schema_id": ACTIVATION_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "selected" if activation_enabled else "blocked",
        "mode": ACTIVATION_MODE,
        "selector_activation_state": activation_state,
        "activation_receipt_id": activation_receipt_id if activation_enabled else None,
        "activation_receipt_hash": activation_hash if activation_enabled else None,
        "activation_receipt_ref": activation_receipt_ref,
        "activation_receipt_status": activation_receipt_status,
        "blocked_reasons": blocked,
        "activation_authority": {
            "source": ACTIVATION_AUTHORITY_SOURCE,
            "selector_use_status_hash": selector_use_status_hash,
            "status_revalidated": status_summary is not None and not blocked,
            "receipt_bound": activation_enabled,
        },
        "selector_use_receipt_binding": {
            "schema_id": SCHEMA_ID,
            "mode": RUNTIME_MODE,
            "required_state": SELECTED_STATE,
            "selector_use_receipt_id": selector_use_receipt_id,
            "selector_use_receipt_hash": selector_use_receipt_hash,
            "binding_verified": status_summary is not None and not blocked,
        },
        "runtime_selection_receipt_binding": {
            "schema_id": SOURCE_RUNTIME_SCHEMA_ID,
            "mode": SOURCE_RUNTIME_MODE,
            "required_state": SOURCE_RUNTIME_SELECTED_STATE,
            "runtime_selection_receipt_id": runtime_selection_receipt_id,
            "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
            "binding_verified": status_summary is not None and not blocked,
        },
        "readiness_audit_binding": {
            "readiness_audit_id": readiness_audit_id or None,
            "readiness_audit_hash": readiness_audit_hash or None,
            "binding_verified": bool(readiness_audit_id and readiness_audit_hash and not blocked),
        },
        "selected_scope_classes": selected_scope_classes,
        "selected_scope_classes_source": "selected_scope_classes_from_revalidated_selector_use_status",
        "current_default_before_activation_runtime": CURRENT_DEFAULT_SCOPE,
        "default_scope_activation_enabled": activation_enabled,
        "default_scope_expansion_enabled": activation_enabled,
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
        "operator_visible_activation_status": {
            "activation_recorded": activation_enabled,
            "selected_scope_class_count": len(selected_scope_classes) if activation_enabled else 0,
            "redacted_activation_receipt_available": activation_receipt_ref is not None,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_or_connector_secret_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_status_blocks_activation": True,
            "stale_selector_use_receipt_hash_blocks_activation": True,
            "stale_runtime_receipt_hash_blocks_activation": True,
            "stale_readiness_audit_hash_blocks_activation": True,
            "unknown_scope_class_blocks_activation": True,
            "unselected_scope_class_blocks_activation": True,
            "missing_rollback_confirmation_blocks_activation": True,
            "candidate_a_semantic_drift_blocks_activation": True,
        },
        "selector_activation_authority_recorded": activation_enabled,
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
        "negative_invariants": _negative_invariants(activation_enabled),
        "next_allowed_actions": (
            ["use activation receipt for exact broader Candidate B selected classes"]
            if activation_enabled
            else ["inspect selector-use status and repair stale or missing authority before activation"]
        ),
    }


def record_candidate_b_broader_scope_activation_receipt_consumption(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload, error_cls=CandidateBBroaderScopeActivationConsumptionError)
    request_id = _required_str(
        fields,
        "client_request_id",
        error_cls=CandidateBBroaderScopeActivationConsumptionError,
    )
    consumption_mode = _required_str(
        fields,
        "consumption_mode",
        error_cls=CandidateBBroaderScopeActivationConsumptionError,
    )
    if consumption_mode != CONSUMPTION_MODE:
        raise CandidateBBroaderScopeActivationConsumptionError(
            "candidate_b_broader_scope_activation_consumption_mode_not_admitted",
            "Only the frozen Candidate B broader eligible-corpus activation receipt consumption mode is admitted.",
            details={"expected_consumption_mode": CONSUMPTION_MODE, "received_consumption_mode": consumption_mode},
        )

    activation_receipt_id = _required_storage_id(
        fields,
        "activation_receipt_id",
        prefix=ACTIVATION_RECEIPT_PREFIX,
        error_cls=CandidateBBroaderScopeActivationConsumptionError,
    )
    activation_receipt_hash = _required_str(
        fields,
        "activation_receipt_hash",
        error_cls=CandidateBBroaderScopeActivationConsumptionError,
    )
    selector_use_status_hash = _required_str(
        fields,
        "selector_use_status_hash",
        error_cls=CandidateBBroaderScopeActivationConsumptionError,
    )
    selector_use_receipt_id = _required_storage_id(
        fields,
        "selector_use_receipt_id",
        prefix=RECEIPT_PREFIX,
        error_cls=CandidateBBroaderScopeActivationConsumptionError,
    )
    selector_use_receipt_hash = _required_str(
        fields,
        "selector_use_receipt_hash",
        error_cls=CandidateBBroaderScopeActivationConsumptionError,
    )
    runtime_selection_receipt_id = _required_str(
        fields,
        "runtime_selection_receipt_id",
        error_cls=CandidateBBroaderScopeActivationConsumptionError,
    )
    runtime_selection_receipt_hash = _required_str(
        fields,
        "runtime_selection_receipt_hash",
        error_cls=CandidateBBroaderScopeActivationConsumptionError,
    )
    selected_scope_classes = _string_list(fields.get("selected_scope_classes"))

    blocked: list[dict[str, Any]] = []
    if fields.get("operator_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_activation_consumption_operator_confirmation_missing"))
    if fields.get("rollback_to_baseline_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_activation_consumption_rollback_to_baseline_missing"))
    if not selected_scope_classes:
        blocked.append(_reason("candidate_b_broader_scope_activation_consumption_no_selected_scope_class"))

    activation_receipt = _read_selector_activation_receipt(activation_receipt_id)
    if activation_receipt is None:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_activation_consumption_missing_activation_receipt",
                activation_receipt_id=activation_receipt_id,
            )
        )

    status_summary: dict[str, Any] | None = None
    runtime_summary: dict[str, Any] | None = None
    receipt_classes: list[str] = []
    readiness_audit_id = ""
    readiness_audit_hash = ""
    if activation_receipt is not None:
        blocked.extend(
            _validate_selector_activation_receipt(
                receipt=activation_receipt,
                activation_receipt_id=activation_receipt_id,
                activation_receipt_hash=activation_receipt_hash,
            )
        )
        receipt_classes = _string_list(activation_receipt.get("selected_scope_classes"))
        readiness_audit_id = str(activation_receipt.get("readiness_audit_id") or "")
        readiness_audit_hash = str(activation_receipt.get("readiness_audit_hash") or "")

        expected_payload_fields = {
            "selector_use_status_hash": selector_use_status_hash,
            "selector_use_receipt_id": selector_use_receipt_id,
            "selector_use_receipt_hash": selector_use_receipt_hash,
            "runtime_selection_receipt_id": runtime_selection_receipt_id,
            "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
        }
        for field, received in expected_payload_fields.items():
            expected = activation_receipt.get(field)
            if expected != received:
                blocked.append(
                    _reason(
                        "candidate_b_broader_scope_activation_consumption_activation_binding_mismatch",
                        field=field,
                        expected=expected,
                        received=received,
                    )
                )

        if selected_scope_classes != receipt_classes:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_activation_consumption_selected_classes_do_not_match_activation",
                    expected=receipt_classes,
                    received=selected_scope_classes,
                )
            )
        invalid_classes = sorted(
            set(selected_scope_classes) - set(layer3_candidate_b_broader_scope_readiness.SCOPE_CLASSES)
        )
        if invalid_classes:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_activation_consumption_unknown_scope_class",
                    invalid_scope_classes=invalid_classes,
                )
            )
        unselected_classes = sorted(set(selected_scope_classes) - set(receipt_classes))
        if unselected_classes:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_activation_consumption_unselected_scope_class",
                    unselected_scope_classes=unselected_classes,
                )
            )

        try:
            status_summary = inspect_candidate_b_broader_scope_selector_use_status(
                {
                    "client_request_id": f"{request_id}:selector-use-status",
                    "status_mode": STATUS_MODE,
                    "operator_decision": STATUS_OPERATOR_DECISION,
                    "selector_use_receipt_id": activation_receipt.get("selector_use_receipt_id"),
                    "selector_use_receipt_hash": activation_receipt.get("selector_use_receipt_hash"),
                    "runtime_selection_receipt_id": activation_receipt.get("runtime_selection_receipt_id"),
                    "runtime_selection_receipt_hash": activation_receipt.get("runtime_selection_receipt_hash"),
                }
            )
        except CandidateBBroaderScopeSelectorUseError as exc:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_activation_consumption_status_authority_invalid",
                    authority_error_code=exc.code,
                    authority_error_details=exc.details,
                )
            )

        if status_summary is not None:
            if status_summary.get("selector_use_status_hash") != activation_receipt.get("selector_use_status_hash"):
                blocked.append(
                    _reason(
                        "candidate_b_broader_scope_activation_consumption_stale_selector_use_status_hash",
                        expected=status_summary.get("selector_use_status_hash"),
                        received=activation_receipt.get("selector_use_status_hash"),
                    )
                )
            if status_summary.get("selector_use_state") != SELECTED_STATE:
                blocked.append(
                    _reason(
                        "candidate_b_broader_scope_activation_consumption_status_not_selected",
                        received=status_summary.get("selector_use_state"),
                    )
                )
            status_classes = _string_list(status_summary.get("selected_scope_classes"))
            if receipt_classes != status_classes:
                blocked.append(
                    _reason(
                        "candidate_b_broader_scope_activation_consumption_selected_classes_do_not_match_status",
                        expected=status_classes,
                        received=receipt_classes,
                    )
                )

        runtime_summary = _validate_source_runtime_receipt(
            receipt_id=str(activation_receipt.get("runtime_selection_receipt_id") or ""),
            receipt_hash=str(activation_receipt.get("runtime_selection_receipt_hash") or ""),
            selected_scope_classes=receipt_classes,
            create_root=False,
            error_cls=CandidateBBroaderScopeActivationConsumptionError,
        )
        blocked.extend(
            [
                _reason(
                    "candidate_b_broader_scope_activation_consumption_runtime_authority_invalid",
                    runtime_blocked_reason=reason,
                )
                for reason in runtime_summary["blocked_reasons"]
            ]
        )

    consumption_hash = _stable_hash(
        {
            "schema_id": CONSUMPTION_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "consumption_mode": CONSUMPTION_MODE,
            "consumption_authority_source": CONSUMPTION_AUTHORITY_SOURCE,
            "activation_schema_id": ACTIVATION_SCHEMA_ID,
            "activation_mode": ACTIVATION_MODE,
            "activation_receipt_id": activation_receipt_id,
            "activation_receipt_hash": activation_receipt_hash,
            "selector_use_status_hash": selector_use_status_hash,
            "selector_use_receipt_id": selector_use_receipt_id,
            "selector_use_receipt_hash": selector_use_receipt_hash,
            "runtime_selection_receipt_id": runtime_selection_receipt_id,
            "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
            "readiness_audit_id": readiness_audit_id,
            "readiness_audit_hash": readiness_audit_hash,
            "selected_scope_classes": selected_scope_classes,
            "current_default_before_consumption_runtime": CURRENT_DEFAULT_SCOPE,
            "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
            "baseline_rollback_preserved": fields.get("rollback_to_baseline_confirmation") is True,
            "candidate_a_semantics_preserved": True,
            "redaction_policy_id": CONSUMPTION_REDACTION_POLICY_ID,
        }
    )
    consumption_receipt_id = f"{CONSUMPTION_RECEIPT_PREFIX}-{consumption_hash[:24]}"
    consumption_state = CONSUMPTION_SELECTED_STATE if not blocked else CONSUMPTION_BLOCKED_STATE
    consumption_receipt_ref = None
    consumption_receipt_status = "not_recorded"
    if consumption_state == CONSUMPTION_SELECTED_STATE:
        consumption_receipt_ref = _write_activation_consumption_receipt(
            receipt_id=consumption_receipt_id,
            receipt_hash=consumption_hash,
            request_id=request_id,
            activation_receipt_id=activation_receipt_id,
            activation_receipt_hash=activation_receipt_hash,
            selector_use_status_hash=selector_use_status_hash,
            selector_use_receipt_id=selector_use_receipt_id,
            selector_use_receipt_hash=selector_use_receipt_hash,
            runtime_selection_receipt_id=runtime_selection_receipt_id,
            runtime_selection_receipt_hash=runtime_selection_receipt_hash,
            readiness_audit_id=readiness_audit_id,
            readiness_audit_hash=readiness_audit_hash,
            selected_scope_classes=selected_scope_classes,
        )
        consumption_receipt_status = "recorded"

    consumption_enabled = consumption_state == CONSUMPTION_SELECTED_STATE
    return {
        "schema_id": CONSUMPTION_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "selected" if consumption_enabled else "blocked",
        "mode": CONSUMPTION_MODE,
        "activation_receipt_consumption_state": consumption_state,
        "consumption_receipt_id": consumption_receipt_id if consumption_enabled else None,
        "consumption_receipt_hash": consumption_hash if consumption_enabled else None,
        "consumption_receipt_ref": consumption_receipt_ref,
        "consumption_receipt_status": consumption_receipt_status,
        "blocked_reasons": blocked,
        "consumption_authority": {
            "source": CONSUMPTION_AUTHORITY_SOURCE,
            "activation_receipt_id": activation_receipt_id,
            "activation_receipt_hash": activation_receipt_hash,
            "activation_receipt_reloaded": activation_receipt is not None,
            "receipt_bound": consumption_enabled,
        },
        "activation_receipt_binding": {
            "schema_id": ACTIVATION_SCHEMA_ID,
            "mode": ACTIVATION_MODE,
            "required_state": ACTIVATION_SELECTED_STATE,
            "activation_receipt_id": activation_receipt_id,
            "activation_receipt_hash": activation_receipt_hash,
            "binding_verified": activation_receipt is not None and not blocked,
        },
        "selector_use_status_binding": {
            "schema_id": STATUS_SCHEMA_ID,
            "mode": STATUS_MODE,
            "selector_use_status_hash": selector_use_status_hash,
            "status_revalidated": status_summary is not None and not blocked,
            "binding_verified": status_summary is not None and not blocked,
        },
        "selector_use_receipt_binding": {
            "schema_id": SCHEMA_ID,
            "mode": RUNTIME_MODE,
            "required_state": SELECTED_STATE,
            "selector_use_receipt_id": selector_use_receipt_id,
            "selector_use_receipt_hash": selector_use_receipt_hash,
            "binding_verified": status_summary is not None and not blocked,
        },
        "runtime_selection_receipt_binding": {
            "schema_id": SOURCE_RUNTIME_SCHEMA_ID,
            "mode": SOURCE_RUNTIME_MODE,
            "required_state": SOURCE_RUNTIME_SELECTED_STATE,
            "runtime_selection_receipt_id": runtime_selection_receipt_id,
            "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
            "binding_verified": runtime_summary is not None and not runtime_summary["blocked_reasons"] and not blocked,
        },
        "readiness_audit_binding": {
            "readiness_audit_id": readiness_audit_id or None,
            "readiness_audit_hash": readiness_audit_hash or None,
            "binding_verified": bool(readiness_audit_id and readiness_audit_hash and not blocked),
        },
        "selected_scope_classes": selected_scope_classes,
        "selected_scope_classes_source": "selected_scope_classes_from_revalidated_activation_receipt",
        "current_default_before_consumption_runtime": CURRENT_DEFAULT_SCOPE,
        "default_scope_consumption_enabled": consumption_enabled,
        "default_scope_expansion_enabled": consumption_enabled,
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
        "operator_visible_consumption_status": {
            "consumption_recorded": consumption_enabled,
            "selected_scope_class_count": len(selected_scope_classes) if consumption_enabled else 0,
            "redacted_consumption_receipt_available": consumption_receipt_ref is not None,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_or_connector_secret_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_activation_receipt_blocks_consumption": True,
            "stale_activation_receipt_hash_blocks_consumption": True,
            "stale_selector_use_status_hash_blocks_consumption": True,
            "stale_selector_use_receipt_hash_blocks_consumption": True,
            "stale_runtime_receipt_hash_blocks_consumption": True,
            "stale_readiness_audit_hash_blocks_consumption": True,
            "unknown_scope_class_blocks_consumption": True,
            "unselected_scope_class_blocks_consumption": True,
            "missing_rollback_confirmation_blocks_consumption": True,
            "candidate_a_semantic_drift_blocks_consumption": True,
        },
        "activation_receipt_consumption_authority_recorded": consumption_enabled,
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
        "negative_invariants": _negative_invariants(consumption_enabled),
        "next_allowed_actions": (
            ["use consumption receipt for exact broader Candidate B selected classes"]
            if consumption_enabled
            else ["reload activation receipt and repair stale or missing authority before consumption"]
        ),
    }


def record_candidate_b_broader_scope_consumption_receipt_use(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload, error_cls=CandidateBBroaderScopeConsumptionReceiptUseError)
    request_id = _required_str(fields, "client_request_id", error_cls=CandidateBBroaderScopeConsumptionReceiptUseError)
    use_mode = _required_str(fields, "use_mode", error_cls=CandidateBBroaderScopeConsumptionReceiptUseError)
    if use_mode != CONSUMPTION_USE_MODE:
        raise CandidateBBroaderScopeConsumptionReceiptUseError(
            "candidate_b_broader_scope_consumption_receipt_use_mode_not_admitted",
            "Only the frozen Candidate B broader eligible-corpus consumption receipt use mode is admitted.",
            details={"expected_use_mode": CONSUMPTION_USE_MODE, "received_use_mode": use_mode},
        )

    consumption_receipt_id = _required_storage_id(
        fields,
        "consumption_receipt_id",
        prefix=CONSUMPTION_RECEIPT_PREFIX,
        error_cls=CandidateBBroaderScopeConsumptionReceiptUseError,
    )
    consumption_receipt_hash = _required_str(
        fields,
        "consumption_receipt_hash",
        error_cls=CandidateBBroaderScopeConsumptionReceiptUseError,
    )
    activation_receipt_id = _required_storage_id(
        fields,
        "activation_receipt_id",
        prefix=ACTIVATION_RECEIPT_PREFIX,
        error_cls=CandidateBBroaderScopeConsumptionReceiptUseError,
    )
    activation_receipt_hash = _required_str(
        fields,
        "activation_receipt_hash",
        error_cls=CandidateBBroaderScopeConsumptionReceiptUseError,
    )
    selector_use_status_hash = _required_str(
        fields,
        "selector_use_status_hash",
        error_cls=CandidateBBroaderScopeConsumptionReceiptUseError,
    )
    selector_use_receipt_id = _required_storage_id(
        fields,
        "selector_use_receipt_id",
        prefix=RECEIPT_PREFIX,
        error_cls=CandidateBBroaderScopeConsumptionReceiptUseError,
    )
    selector_use_receipt_hash = _required_str(
        fields,
        "selector_use_receipt_hash",
        error_cls=CandidateBBroaderScopeConsumptionReceiptUseError,
    )
    runtime_selection_receipt_id = _required_str(
        fields,
        "runtime_selection_receipt_id",
        error_cls=CandidateBBroaderScopeConsumptionReceiptUseError,
    )
    runtime_selection_receipt_hash = _required_str(
        fields,
        "runtime_selection_receipt_hash",
        error_cls=CandidateBBroaderScopeConsumptionReceiptUseError,
    )
    selected_scope_classes = _string_list(fields.get("selected_scope_classes"))

    blocked: list[dict[str, Any]] = []
    if fields.get("operator_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_consumption_receipt_use_operator_confirmation_missing"))
    if fields.get("rollback_to_baseline_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_consumption_receipt_use_rollback_to_baseline_missing"))
    if not selected_scope_classes:
        blocked.append(_reason("candidate_b_broader_scope_consumption_receipt_use_no_selected_scope_class"))

    consumption_receipt = _read_activation_consumption_receipt(consumption_receipt_id)
    if consumption_receipt is None:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_consumption_receipt_use_missing_consumption_receipt",
                consumption_receipt_id=consumption_receipt_id,
            )
        )

    activation_receipt: dict[str, Any] | None = None
    status_summary: dict[str, Any] | None = None
    runtime_summary: dict[str, Any] | None = None
    receipt_classes: list[str] = []
    readiness_audit_id = ""
    readiness_audit_hash = ""
    if consumption_receipt is not None:
        blocked.extend(
            _validate_activation_consumption_receipt(
                receipt=consumption_receipt,
                consumption_receipt_id=consumption_receipt_id,
                consumption_receipt_hash=consumption_receipt_hash,
            )
        )
        receipt_classes = _string_list(consumption_receipt.get("selected_scope_classes"))
        readiness_audit_id = str(consumption_receipt.get("readiness_audit_id") or "")
        readiness_audit_hash = str(consumption_receipt.get("readiness_audit_hash") or "")

        expected_payload_fields = {
            "activation_receipt_id": activation_receipt_id,
            "activation_receipt_hash": activation_receipt_hash,
            "selector_use_status_hash": selector_use_status_hash,
            "selector_use_receipt_id": selector_use_receipt_id,
            "selector_use_receipt_hash": selector_use_receipt_hash,
            "runtime_selection_receipt_id": runtime_selection_receipt_id,
            "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
        }
        for field, received in expected_payload_fields.items():
            expected = consumption_receipt.get(field)
            if expected != received:
                blocked.append(
                    _reason(
                        "candidate_b_broader_scope_consumption_receipt_use_consumption_binding_mismatch",
                        field=field,
                        expected=expected,
                        received=received,
                    )
                )

        if selected_scope_classes != receipt_classes:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_consumption_receipt_use_selected_classes_do_not_match_consumption",
                    expected=receipt_classes,
                    received=selected_scope_classes,
                )
            )
        invalid_classes = sorted(
            set(selected_scope_classes) - set(layer3_candidate_b_broader_scope_readiness.SCOPE_CLASSES)
        )
        if invalid_classes:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_consumption_receipt_use_unknown_scope_class",
                    invalid_scope_classes=invalid_classes,
                )
            )
        unselected_classes = sorted(set(selected_scope_classes) - set(receipt_classes))
        if unselected_classes:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_consumption_receipt_use_unselected_scope_class",
                    unselected_scope_classes=unselected_classes,
                )
            )

        activation_receipt = _read_selector_activation_receipt(activation_receipt_id)
        if activation_receipt is None:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_consumption_receipt_use_missing_activation_receipt",
                    activation_receipt_id=activation_receipt_id,
                )
            )
        else:
            blocked.extend(
                [
                    _reason(
                        "candidate_b_broader_scope_consumption_receipt_use_activation_authority_invalid",
                        activation_blocked_reason=reason,
                    )
                    for reason in _validate_selector_activation_receipt(
                        receipt=activation_receipt,
                        activation_receipt_id=activation_receipt_id,
                        activation_receipt_hash=activation_receipt_hash,
                    )
                ]
            )

        try:
            status_summary = inspect_candidate_b_broader_scope_selector_use_status(
                {
                    "client_request_id": f"{request_id}:selector-use-status",
                    "status_mode": STATUS_MODE,
                    "operator_decision": STATUS_OPERATOR_DECISION,
                    "selector_use_receipt_id": consumption_receipt.get("selector_use_receipt_id"),
                    "selector_use_receipt_hash": consumption_receipt.get("selector_use_receipt_hash"),
                    "runtime_selection_receipt_id": consumption_receipt.get("runtime_selection_receipt_id"),
                    "runtime_selection_receipt_hash": consumption_receipt.get("runtime_selection_receipt_hash"),
                }
            )
        except CandidateBBroaderScopeSelectorUseError as exc:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_consumption_receipt_use_status_authority_invalid",
                    authority_error_code=exc.code,
                    authority_error_details=exc.details,
                )
            )

        if status_summary is not None:
            if status_summary.get("selector_use_status_hash") != consumption_receipt.get("selector_use_status_hash"):
                blocked.append(
                    _reason(
                        "candidate_b_broader_scope_consumption_receipt_use_stale_selector_use_status_hash",
                        expected=status_summary.get("selector_use_status_hash"),
                        received=consumption_receipt.get("selector_use_status_hash"),
                    )
                )
            if status_summary.get("selector_use_state") != SELECTED_STATE:
                blocked.append(
                    _reason(
                        "candidate_b_broader_scope_consumption_receipt_use_status_not_selected",
                        received=status_summary.get("selector_use_state"),
                    )
                )
            status_classes = _string_list(status_summary.get("selected_scope_classes"))
            if receipt_classes != status_classes:
                blocked.append(
                    _reason(
                        "candidate_b_broader_scope_consumption_receipt_use_selected_classes_do_not_match_status",
                        expected=status_classes,
                        received=receipt_classes,
                    )
                )

        runtime_summary = _validate_source_runtime_receipt(
            receipt_id=str(consumption_receipt.get("runtime_selection_receipt_id") or ""),
            receipt_hash=str(consumption_receipt.get("runtime_selection_receipt_hash") or ""),
            selected_scope_classes=receipt_classes,
            create_root=False,
            error_cls=CandidateBBroaderScopeConsumptionReceiptUseError,
        )
        blocked.extend(
            [
                _reason(
                    "candidate_b_broader_scope_consumption_receipt_use_runtime_authority_invalid",
                    runtime_blocked_reason=reason,
                )
                for reason in runtime_summary["blocked_reasons"]
            ]
        )

    use_hash = _stable_hash(
        {
            "schema_id": CONSUMPTION_USE_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "use_mode": CONSUMPTION_USE_MODE,
            "use_authority_source": CONSUMPTION_USE_AUTHORITY_SOURCE,
            "consumption_schema_id": CONSUMPTION_SCHEMA_ID,
            "consumption_mode": CONSUMPTION_MODE,
            "consumption_receipt_id": consumption_receipt_id,
            "consumption_receipt_hash": consumption_receipt_hash,
            "activation_receipt_id": activation_receipt_id,
            "activation_receipt_hash": activation_receipt_hash,
            "selector_use_status_hash": selector_use_status_hash,
            "selector_use_receipt_id": selector_use_receipt_id,
            "selector_use_receipt_hash": selector_use_receipt_hash,
            "runtime_selection_receipt_id": runtime_selection_receipt_id,
            "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
            "readiness_audit_id": readiness_audit_id,
            "readiness_audit_hash": readiness_audit_hash,
            "selected_scope_classes": selected_scope_classes,
            "current_default_before_use_runtime": CURRENT_DEFAULT_SCOPE,
            "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
            "baseline_rollback_preserved": fields.get("rollback_to_baseline_confirmation") is True,
            "candidate_a_semantics_preserved": True,
            "redaction_policy_id": CONSUMPTION_USE_REDACTION_POLICY_ID,
        }
    )
    use_receipt_id = f"{CONSUMPTION_USE_RECEIPT_PREFIX}-{use_hash[:24]}"
    use_state = CONSUMPTION_USE_SELECTED_STATE if not blocked else CONSUMPTION_USE_BLOCKED_STATE
    use_receipt_ref = None
    use_receipt_status = "not_recorded"
    if use_state == CONSUMPTION_USE_SELECTED_STATE:
        use_receipt_ref = _write_consumption_receipt_use_receipt(
            receipt_id=use_receipt_id,
            receipt_hash=use_hash,
            request_id=request_id,
            consumption_receipt_id=consumption_receipt_id,
            consumption_receipt_hash=consumption_receipt_hash,
            activation_receipt_id=activation_receipt_id,
            activation_receipt_hash=activation_receipt_hash,
            selector_use_status_hash=selector_use_status_hash,
            selector_use_receipt_id=selector_use_receipt_id,
            selector_use_receipt_hash=selector_use_receipt_hash,
            runtime_selection_receipt_id=runtime_selection_receipt_id,
            runtime_selection_receipt_hash=runtime_selection_receipt_hash,
            readiness_audit_id=readiness_audit_id,
            readiness_audit_hash=readiness_audit_hash,
            selected_scope_classes=selected_scope_classes,
        )
        use_receipt_status = "recorded"

    use_enabled = use_state == CONSUMPTION_USE_SELECTED_STATE
    return {
        "schema_id": CONSUMPTION_USE_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "selected" if use_enabled else "blocked",
        "mode": CONSUMPTION_USE_MODE,
        "consumption_receipt_use_state": use_state,
        "use_receipt_id": use_receipt_id if use_enabled else None,
        "use_receipt_hash": use_hash if use_enabled else None,
        "use_receipt_ref": use_receipt_ref,
        "use_receipt_status": use_receipt_status,
        "blocked_reasons": blocked,
        "use_authority": {
            "source": CONSUMPTION_USE_AUTHORITY_SOURCE,
            "consumption_receipt_id": consumption_receipt_id,
            "consumption_receipt_hash": consumption_receipt_hash,
            "consumption_receipt_reloaded": consumption_receipt is not None,
            "receipt_bound": use_enabled,
        },
        "consumption_receipt_binding": {
            "schema_id": CONSUMPTION_SCHEMA_ID,
            "mode": CONSUMPTION_MODE,
            "required_state": CONSUMPTION_SELECTED_STATE,
            "consumption_receipt_id": consumption_receipt_id,
            "consumption_receipt_hash": consumption_receipt_hash,
            "binding_verified": consumption_receipt is not None and not blocked,
        },
        "activation_receipt_binding": {
            "schema_id": ACTIVATION_SCHEMA_ID,
            "mode": ACTIVATION_MODE,
            "required_state": ACTIVATION_SELECTED_STATE,
            "activation_receipt_id": activation_receipt_id,
            "activation_receipt_hash": activation_receipt_hash,
            "binding_verified": activation_receipt is not None and not blocked,
        },
        "selector_use_status_binding": {
            "schema_id": STATUS_SCHEMA_ID,
            "mode": STATUS_MODE,
            "selector_use_status_hash": selector_use_status_hash,
            "status_revalidated": status_summary is not None and not blocked,
            "binding_verified": status_summary is not None and not blocked,
        },
        "selector_use_receipt_binding": {
            "schema_id": SCHEMA_ID,
            "mode": RUNTIME_MODE,
            "required_state": SELECTED_STATE,
            "selector_use_receipt_id": selector_use_receipt_id,
            "selector_use_receipt_hash": selector_use_receipt_hash,
            "binding_verified": status_summary is not None and not blocked,
        },
        "runtime_selection_receipt_binding": {
            "schema_id": SOURCE_RUNTIME_SCHEMA_ID,
            "mode": SOURCE_RUNTIME_MODE,
            "required_state": SOURCE_RUNTIME_SELECTED_STATE,
            "runtime_selection_receipt_id": runtime_selection_receipt_id,
            "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
            "binding_verified": runtime_summary is not None and not runtime_summary["blocked_reasons"] and not blocked,
        },
        "readiness_audit_binding": {
            "readiness_audit_id": readiness_audit_id or None,
            "readiness_audit_hash": readiness_audit_hash or None,
            "binding_verified": bool(readiness_audit_id and readiness_audit_hash and not blocked),
        },
        "selected_scope_classes": selected_scope_classes,
        "selected_scope_classes_source": "selected_scope_classes_from_revalidated_consumption_receipt",
        "current_default_before_use_runtime": CURRENT_DEFAULT_SCOPE,
        "default_scope_use_enabled": use_enabled,
        "default_scope_expansion_enabled": use_enabled,
        "default_scope_application_scope": "consumed_receipt_bound_selected_classes_only",
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
        "operator_visible_use_status": {
            "use_recorded": use_enabled,
            "selected_scope_class_count": len(selected_scope_classes) if use_enabled else 0,
            "redacted_default_scope_use_receipt_available": use_receipt_ref is not None,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_or_connector_secret_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_consumption_receipt_blocks_use": True,
            "stale_consumption_receipt_hash_blocks_use": True,
            "stale_activation_receipt_binding_blocks_use": True,
            "stale_selector_use_status_hash_blocks_use": True,
            "stale_selector_use_receipt_hash_blocks_use": True,
            "stale_runtime_receipt_hash_blocks_use": True,
            "stale_readiness_audit_hash_blocks_use": True,
            "unknown_scope_class_blocks_use": True,
            "unselected_scope_class_blocks_use": True,
            "missing_rollback_confirmation_blocks_use": True,
            "candidate_a_semantic_drift_blocks_use": True,
        },
        "default_scope_use_authority_recorded": use_enabled,
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
        "negative_invariants": _negative_invariants(use_enabled),
        "next_allowed_actions": (
            ["inspect Candidate B broader default-scope use status for exact consumed selected classes"]
            if use_enabled
            else ["reload consumption receipt and repair stale or missing authority before default-scope use"]
        ),
    }


def _validate_source_runtime_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    selected_scope_classes: list[str],
    create_root: bool = True,
    error_cls: type[CandidateBBroaderScopeSelectorUseError] = CandidateBBroaderScopeSelectorUseError,
) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    receipt_path = (
        _runtime_receipt_root(create=create_root, error_cls=error_cls)
        / "broader-scope-runtime"
        / f"{receipt_id}.json"
    )
    receipt = _read_optional_receipt(receipt_path)
    if receipt is None:
        return {
            "blocked_reasons": [_reason("candidate_b_broader_scope_selector_use_runtime_receipt_missing")],
            "summary": {"status": "missing"},
        }
    if _find_forbidden_fields(receipt):
        blocked.append(_reason("candidate_b_broader_scope_selector_use_runtime_receipt_forbidden_authority"))
    expected_fields = {
        "schema_id": SOURCE_RUNTIME_SCHEMA_ID,
        "schema_version": layer3_candidate_b_broader_scope_runtime.SCHEMA_VERSION,
        "runtime_mode": SOURCE_RUNTIME_MODE,
        "runtime_state": SOURCE_RUNTIME_SELECTED_STATE,
        "selection_receipt_id": receipt_id,
        "selection_receipt_hash": receipt_hash,
        "current_default_scope_preserved": CURRENT_DEFAULT_SCOPE,
        "non_pdf_default_preserved": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_or_connector_secret_exposed": False,
    }
    for field, expected in expected_fields.items():
        if receipt.get(field) != expected:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_selector_use_runtime_receipt_field_mismatch",
                    field=field,
                    expected=expected,
                    received=receipt.get(field),
                )
            )
    receipt_classes = _string_list(receipt.get("selected_scope_classes"))
    if selected_scope_classes != receipt_classes:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_selector_use_selected_classes_do_not_match_runtime_receipt",
                expected=receipt_classes,
                received=selected_scope_classes,
            )
        )
    invalid_classes = sorted(set(selected_scope_classes) - set(layer3_candidate_b_broader_scope_readiness.SCOPE_CLASSES))
    if invalid_classes:
        blocked.append(
            _reason("candidate_b_broader_scope_selector_use_unknown_scope_class", invalid_scope_classes=invalid_classes)
        )
    unselected_classes = sorted(set(selected_scope_classes) - set(receipt_classes))
    if unselected_classes:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_selector_use_unselected_scope_class",
                unselected_scope_classes=unselected_classes,
            )
        )
    recomputed_hash = _source_runtime_receipt_hash(receipt)
    if recomputed_hash != receipt_hash:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_selector_use_stale_runtime_receipt_hash",
                expected=recomputed_hash,
                received=receipt_hash,
            )
        )
    if not str(receipt.get("readiness_audit_hash") or "").strip():
        blocked.append(_reason("candidate_b_broader_scope_selector_use_readiness_audit_hash_missing"))
    if receipt.get("redaction_policy_id") != layer3_candidate_b_broader_scope_runtime.REDACTION_POLICY_ID:
        blocked.append(_reason("candidate_b_broader_scope_selector_use_redaction_policy_mismatch"))

    return {
        "blocked_reasons": blocked,
        "summary": {
            "runtime_selection_receipt_id": receipt.get("selection_receipt_id"),
            "runtime_selection_receipt_hash": receipt.get("selection_receipt_hash"),
            "readiness_audit_id": receipt.get("readiness_audit_id"),
            "readiness_audit_hash": receipt.get("readiness_audit_hash"),
            "selected_scope_classes": receipt_classes,
            "selected_scope_class_count": len(receipt_classes) if not blocked else 0,
        },
    }


def _source_runtime_receipt_hash(receipt: Mapping[str, Any]) -> str:
    return _stable_hash(
        {
            "schema_id": SOURCE_RUNTIME_SCHEMA_ID,
            "schema_version": layer3_candidate_b_broader_scope_runtime.SCHEMA_VERSION,
            "runtime_mode": SOURCE_RUNTIME_MODE,
            "readiness_audit_id": receipt.get("readiness_audit_id"),
            "readiness_audit_hash": receipt.get("readiness_audit_hash"),
            "selected_scope_classes": _string_list(receipt.get("selected_scope_classes")),
            "current_default_scope_preserved": CURRENT_DEFAULT_SCOPE,
            "non_pdf_default_preserved": NON_SELECTED_CLASS_DEFAULT,
            "baseline_rollback_preserved": receipt.get("baseline_rollback_preserved") is True,
            "candidate_a_semantics_preserved": receipt.get("candidate_a_semantics_preserved") is True,
            "candidate_b_document_processing_engine_preserved": (
                layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_ENGINE_SCOPE
            ),
            "candidate_b_visual_lane_preserved": (
                layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_VISUAL_LANE_SCOPE
            ),
            "redaction_policy_id": layer3_candidate_b_broader_scope_runtime.REDACTION_POLICY_ID,
        }
    )


def _write_selector_use_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    request_id: str,
    source_receipt_id: str,
    source_receipt_hash: str,
    selected_scope_classes: list[str],
    source_summary: Mapping[str, Any],
) -> str:
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "selector_use_mode": RUNTIME_MODE,
        "selector_use_state": SELECTED_STATE,
        "request_id": request_id,
        "selector_use_receipt_id": receipt_id,
        "selector_use_receipt_hash": receipt_hash,
        "runtime_selection_receipt_id": source_receipt_id,
        "runtime_selection_receipt_hash": source_receipt_hash,
        "selected_scope_classes": selected_scope_classes,
        "selector_authority_source": SELECTOR_AUTHORITY_SOURCE,
        "current_default_scope_before_use": CURRENT_DEFAULT_SCOPE,
        "default_scope_enabled_for_selected_classes": True,
        "non_selected_class_default_preserved": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "redaction_policy_id": REDACTION_POLICY_ID,
        "source_summary": dict(source_summary),
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_or_connector_secret_exposed": False,
        "recorded_at": _server_time(),
    }
    target = _runtime_receipt_root() / "broader-scope-selector-use" / f"{receipt_id}.json"
    if target.exists():
        existing = _read_required_receipt(target)
        if existing.get("selector_use_receipt_hash") != receipt_hash:
            raise CandidateBBroaderScopeSelectorUseError(
                "candidate_b_broader_scope_selector_use_receipt_conflict",
                "The Candidate B broader-scope selector-use receipt is stale or contradictory.",
                http_status=409,
            )
    else:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            raise CandidateBBroaderScopeSelectorUseError(
                "candidate_b_broader_scope_selector_use_receipt_write_failed",
                "Candidate B broader-scope selector-use receipt could not be recorded.",
                http_status=409,
                details={"reason": exc.__class__.__name__},
            ) from exc
    return f"candidate-b-broader-scope-selector-use://{receipt_id}/{receipt_hash[:24]}"


def _write_selector_activation_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    request_id: str,
    selector_use_status_hash: str,
    selector_use_receipt_id: str,
    selector_use_receipt_hash: str,
    runtime_selection_receipt_id: str,
    runtime_selection_receipt_hash: str,
    readiness_audit_id: str,
    readiness_audit_hash: str,
    selected_scope_classes: list[str],
) -> str:
    receipt = {
        "schema_id": ACTIVATION_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "activation_mode": ACTIVATION_MODE,
        "selector_activation_state": ACTIVATION_SELECTED_STATE,
        "request_id": request_id,
        "activation_receipt_id": receipt_id,
        "activation_receipt_hash": receipt_hash,
        "activation_authority_source": ACTIVATION_AUTHORITY_SOURCE,
        "selector_use_status_hash": selector_use_status_hash,
        "selector_use_receipt_id": selector_use_receipt_id,
        "selector_use_receipt_hash": selector_use_receipt_hash,
        "runtime_selection_receipt_id": runtime_selection_receipt_id,
        "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
        "readiness_audit_id": readiness_audit_id,
        "readiness_audit_hash": readiness_audit_hash,
        "selected_scope_classes": selected_scope_classes,
        "current_default_before_activation_runtime": CURRENT_DEFAULT_SCOPE,
        "default_scope_activation_enabled": True,
        "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "redaction_policy_id": ACTIVATION_REDACTION_POLICY_ID,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_or_connector_secret_exposed": False,
        "recorded_at": _server_time(),
    }
    target = _runtime_receipt_root() / "broader-scope-selector-activation" / f"{receipt_id}.json"
    if target.exists():
        existing = _read_required_receipt(target)
        if existing.get("activation_receipt_hash") != receipt_hash:
            raise CandidateBBroaderScopeSelectorActivationError(
                "candidate_b_broader_scope_selector_activation_receipt_conflict",
                "The Candidate B broader-scope selector activation receipt is stale or contradictory.",
                http_status=409,
            )
    else:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            raise CandidateBBroaderScopeSelectorActivationError(
                "candidate_b_broader_scope_selector_activation_receipt_write_failed",
                "Candidate B broader-scope selector activation receipt could not be recorded.",
                http_status=409,
                details={"reason": exc.__class__.__name__},
            ) from exc
    return f"candidate-b-broader-scope-selector-activation://{receipt_id}/{receipt_hash[:24]}"


def _write_activation_consumption_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    request_id: str,
    activation_receipt_id: str,
    activation_receipt_hash: str,
    selector_use_status_hash: str,
    selector_use_receipt_id: str,
    selector_use_receipt_hash: str,
    runtime_selection_receipt_id: str,
    runtime_selection_receipt_hash: str,
    readiness_audit_id: str,
    readiness_audit_hash: str,
    selected_scope_classes: list[str],
) -> str:
    receipt = {
        "schema_id": CONSUMPTION_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "consumption_mode": CONSUMPTION_MODE,
        "activation_receipt_consumption_state": CONSUMPTION_SELECTED_STATE,
        "request_id": request_id,
        "consumption_receipt_id": receipt_id,
        "consumption_receipt_hash": receipt_hash,
        "consumption_authority_source": CONSUMPTION_AUTHORITY_SOURCE,
        "activation_receipt_id": activation_receipt_id,
        "activation_receipt_hash": activation_receipt_hash,
        "selector_use_status_hash": selector_use_status_hash,
        "selector_use_receipt_id": selector_use_receipt_id,
        "selector_use_receipt_hash": selector_use_receipt_hash,
        "runtime_selection_receipt_id": runtime_selection_receipt_id,
        "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
        "readiness_audit_id": readiness_audit_id,
        "readiness_audit_hash": readiness_audit_hash,
        "selected_scope_classes": selected_scope_classes,
        "current_default_before_consumption_runtime": CURRENT_DEFAULT_SCOPE,
        "default_scope_consumption_enabled": True,
        "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "redaction_policy_id": CONSUMPTION_REDACTION_POLICY_ID,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_or_connector_secret_exposed": False,
        "recorded_at": _server_time(),
    }
    target = _runtime_receipt_root() / "broader-scope-activation-consumption" / f"{receipt_id}.json"
    if target.exists():
        existing = _read_required_receipt(target)
        if existing.get("consumption_receipt_hash") != receipt_hash:
            raise CandidateBBroaderScopeActivationConsumptionError(
                "candidate_b_broader_scope_activation_consumption_receipt_conflict",
                "The Candidate B broader-scope activation consumption receipt is stale or contradictory.",
                http_status=409,
            )
    else:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            raise CandidateBBroaderScopeActivationConsumptionError(
                "candidate_b_broader_scope_activation_consumption_receipt_write_failed",
                "Candidate B broader-scope activation consumption receipt could not be recorded.",
                http_status=409,
                details={"reason": exc.__class__.__name__},
            ) from exc
    return f"candidate-b-broader-scope-activation-consumption://{receipt_id}/{receipt_hash[:24]}"


def _write_consumption_receipt_use_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    request_id: str,
    consumption_receipt_id: str,
    consumption_receipt_hash: str,
    activation_receipt_id: str,
    activation_receipt_hash: str,
    selector_use_status_hash: str,
    selector_use_receipt_id: str,
    selector_use_receipt_hash: str,
    runtime_selection_receipt_id: str,
    runtime_selection_receipt_hash: str,
    readiness_audit_id: str,
    readiness_audit_hash: str,
    selected_scope_classes: list[str],
) -> str:
    receipt = {
        "schema_id": CONSUMPTION_USE_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "use_mode": CONSUMPTION_USE_MODE,
        "consumption_receipt_use_state": CONSUMPTION_USE_SELECTED_STATE,
        "request_id": request_id,
        "use_receipt_id": receipt_id,
        "use_receipt_hash": receipt_hash,
        "use_authority_source": CONSUMPTION_USE_AUTHORITY_SOURCE,
        "consumption_receipt_id": consumption_receipt_id,
        "consumption_receipt_hash": consumption_receipt_hash,
        "activation_receipt_id": activation_receipt_id,
        "activation_receipt_hash": activation_receipt_hash,
        "selector_use_status_hash": selector_use_status_hash,
        "selector_use_receipt_id": selector_use_receipt_id,
        "selector_use_receipt_hash": selector_use_receipt_hash,
        "runtime_selection_receipt_id": runtime_selection_receipt_id,
        "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
        "readiness_audit_id": readiness_audit_id,
        "readiness_audit_hash": readiness_audit_hash,
        "selected_scope_classes": selected_scope_classes,
        "current_default_before_use_runtime": CURRENT_DEFAULT_SCOPE,
        "default_scope_use_enabled": True,
        "default_scope_application_scope": "consumed_receipt_bound_selected_classes_only",
        "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "redaction_policy_id": CONSUMPTION_USE_REDACTION_POLICY_ID,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_or_connector_secret_exposed": False,
        "recorded_at": _server_time(),
    }
    target = _runtime_receipt_root() / "broader-scope-consumption-receipt-use" / f"{receipt_id}.json"
    if target.exists():
        existing = _read_required_receipt(target)
        if existing.get("use_receipt_hash") != receipt_hash:
            raise CandidateBBroaderScopeConsumptionReceiptUseError(
                "candidate_b_broader_scope_consumption_receipt_use_receipt_conflict",
                "The Candidate B broader-scope consumption receipt use receipt is stale or contradictory.",
                http_status=409,
            )
    else:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            raise CandidateBBroaderScopeConsumptionReceiptUseError(
                "candidate_b_broader_scope_consumption_receipt_use_receipt_write_failed",
                "Candidate B broader-scope consumption receipt use receipt could not be recorded.",
                http_status=409,
                details={"reason": exc.__class__.__name__},
            ) from exc
    return f"candidate-b-broader-scope-consumption-receipt-use://{receipt_id}/{receipt_hash[:24]}"


def _read_activation_consumption_receipt(consumption_receipt_id: str) -> dict[str, Any] | None:
    target = (
        _runtime_receipt_root(create=False, error_cls=CandidateBBroaderScopeConsumptionReceiptUseError)
        / "broader-scope-activation-consumption"
        / f"{consumption_receipt_id}.json"
    )
    if not target.is_file():
        return None
    return _read_required_receipt(target, error_cls=CandidateBBroaderScopeConsumptionReceiptUseError)


def _validate_activation_consumption_receipt(
    *,
    receipt: Mapping[str, Any],
    consumption_receipt_id: str,
    consumption_receipt_hash: str,
) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    expected_fields = {
        "schema_id": CONSUMPTION_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "consumption_mode": CONSUMPTION_MODE,
        "activation_receipt_consumption_state": CONSUMPTION_SELECTED_STATE,
        "consumption_receipt_id": consumption_receipt_id,
        "consumption_receipt_hash": consumption_receipt_hash,
        "consumption_authority_source": CONSUMPTION_AUTHORITY_SOURCE,
        "current_default_before_consumption_runtime": CURRENT_DEFAULT_SCOPE,
        "default_scope_consumption_enabled": True,
        "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "redaction_policy_id": CONSUMPTION_REDACTION_POLICY_ID,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_or_connector_secret_exposed": False,
    }
    for field, expected in expected_fields.items():
        if receipt.get(field) != expected:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_consumption_receipt_use_consumption_receipt_field_mismatch",
                    field=field,
                    expected=expected,
                    received=receipt.get(field),
                )
            )
    if _find_forbidden_fields(receipt):
        blocked.append(_reason("candidate_b_broader_scope_consumption_receipt_use_consumption_receipt_forbidden_authority"))
    recomputed_hash = _activation_consumption_receipt_hash(receipt)
    if recomputed_hash != consumption_receipt_hash:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_consumption_receipt_use_stale_consumption_receipt_hash",
                expected=recomputed_hash,
                received=consumption_receipt_hash,
            )
        )
    if not str(receipt.get("readiness_audit_hash") or "").strip():
        blocked.append(_reason("candidate_b_broader_scope_consumption_receipt_use_readiness_audit_hash_missing"))
    return blocked


def _activation_consumption_receipt_hash(receipt: Mapping[str, Any]) -> str:
    return _stable_hash(
        {
            "schema_id": CONSUMPTION_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "consumption_mode": CONSUMPTION_MODE,
            "consumption_authority_source": CONSUMPTION_AUTHORITY_SOURCE,
            "activation_schema_id": ACTIVATION_SCHEMA_ID,
            "activation_mode": ACTIVATION_MODE,
            "activation_receipt_id": receipt.get("activation_receipt_id"),
            "activation_receipt_hash": receipt.get("activation_receipt_hash"),
            "selector_use_status_hash": receipt.get("selector_use_status_hash"),
            "selector_use_receipt_id": receipt.get("selector_use_receipt_id"),
            "selector_use_receipt_hash": receipt.get("selector_use_receipt_hash"),
            "runtime_selection_receipt_id": receipt.get("runtime_selection_receipt_id"),
            "runtime_selection_receipt_hash": receipt.get("runtime_selection_receipt_hash"),
            "readiness_audit_id": receipt.get("readiness_audit_id"),
            "readiness_audit_hash": receipt.get("readiness_audit_hash"),
            "selected_scope_classes": _string_list(receipt.get("selected_scope_classes")),
            "current_default_before_consumption_runtime": CURRENT_DEFAULT_SCOPE,
            "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
            "baseline_rollback_preserved": receipt.get("baseline_rollback_preserved") is True,
            "candidate_a_semantics_preserved": receipt.get("candidate_a_semantics_preserved") is True,
            "redaction_policy_id": CONSUMPTION_REDACTION_POLICY_ID,
        }
    )


def _read_selector_activation_receipt(activation_receipt_id: str) -> dict[str, Any] | None:
    target = (
        _runtime_receipt_root(create=False, error_cls=CandidateBBroaderScopeActivationConsumptionError)
        / "broader-scope-selector-activation"
        / f"{activation_receipt_id}.json"
    )
    if not target.is_file():
        return None
    return _read_required_receipt(target, error_cls=CandidateBBroaderScopeActivationConsumptionError)


def _validate_selector_activation_receipt(
    *,
    receipt: Mapping[str, Any],
    activation_receipt_id: str,
    activation_receipt_hash: str,
) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    expected_fields = {
        "schema_id": ACTIVATION_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "activation_mode": ACTIVATION_MODE,
        "selector_activation_state": ACTIVATION_SELECTED_STATE,
        "activation_receipt_id": activation_receipt_id,
        "activation_receipt_hash": activation_receipt_hash,
        "activation_authority_source": ACTIVATION_AUTHORITY_SOURCE,
        "current_default_before_activation_runtime": CURRENT_DEFAULT_SCOPE,
        "default_scope_activation_enabled": True,
        "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "redaction_policy_id": ACTIVATION_REDACTION_POLICY_ID,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_or_connector_secret_exposed": False,
    }
    for field, expected in expected_fields.items():
        if receipt.get(field) != expected:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_activation_consumption_activation_receipt_field_mismatch",
                    field=field,
                    expected=expected,
                    received=receipt.get(field),
                )
            )
    if _find_forbidden_fields(receipt):
        blocked.append(_reason("candidate_b_broader_scope_activation_consumption_activation_receipt_forbidden_authority"))
    recomputed_hash = _selector_activation_receipt_hash(receipt)
    if recomputed_hash != activation_receipt_hash:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_activation_consumption_stale_activation_receipt_hash",
                expected=recomputed_hash,
                received=activation_receipt_hash,
            )
        )
    if not str(receipt.get("readiness_audit_hash") or "").strip():
        blocked.append(_reason("candidate_b_broader_scope_activation_consumption_readiness_audit_hash_missing"))
    return blocked


def _selector_activation_receipt_hash(receipt: Mapping[str, Any]) -> str:
    return _stable_hash(
        {
            "schema_id": ACTIVATION_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "activation_mode": ACTIVATION_MODE,
            "activation_authority_source": ACTIVATION_AUTHORITY_SOURCE,
            "selector_use_status_hash": receipt.get("selector_use_status_hash"),
            "selector_use_receipt_id": receipt.get("selector_use_receipt_id"),
            "selector_use_receipt_hash": receipt.get("selector_use_receipt_hash"),
            "runtime_selection_receipt_id": receipt.get("runtime_selection_receipt_id"),
            "runtime_selection_receipt_hash": receipt.get("runtime_selection_receipt_hash"),
            "readiness_audit_id": receipt.get("readiness_audit_id"),
            "readiness_audit_hash": receipt.get("readiness_audit_hash"),
            "selected_scope_classes": _string_list(receipt.get("selected_scope_classes")),
            "current_default_before_activation_runtime": CURRENT_DEFAULT_SCOPE,
            "non_selected_class_default": NON_SELECTED_CLASS_DEFAULT,
            "baseline_rollback_preserved": receipt.get("baseline_rollback_preserved") is True,
            "candidate_a_semantics_preserved": receipt.get("candidate_a_semantics_preserved") is True,
            "redaction_policy_id": ACTIVATION_REDACTION_POLICY_ID,
        }
    )


def _read_selector_use_receipt(selector_use_receipt_id: str) -> dict[str, Any]:
    target = (
        _runtime_receipt_root(create=False, error_cls=CandidateBBroaderScopeSelectorUseStatusError)
        / "broader-scope-selector-use"
        / f"{selector_use_receipt_id}.json"
    )
    if not target.is_file():
        raise CandidateBBroaderScopeSelectorUseStatusError(
            "candidate_b_broader_scope_selector_use_status_receipt_missing",
            "The selected Candidate B broader-scope selector-use receipt is missing.",
            http_status=404,
            details={"selector_use_receipt_id": selector_use_receipt_id},
        )
    return _read_required_receipt(target, error_cls=CandidateBBroaderScopeSelectorUseStatusError)


def _validate_selector_use_receipt(
    *,
    receipt: Mapping[str, Any],
    selector_use_receipt_id: str,
    selector_use_receipt_hash: str,
    runtime_selection_receipt_id: str,
    runtime_selection_receipt_hash: str,
) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    expected_fields = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "selector_use_mode": RUNTIME_MODE,
        "selector_use_state": SELECTED_STATE,
        "selector_use_receipt_id": selector_use_receipt_id,
        "selector_use_receipt_hash": selector_use_receipt_hash,
        "runtime_selection_receipt_id": runtime_selection_receipt_id,
        "runtime_selection_receipt_hash": runtime_selection_receipt_hash,
        "selector_authority_source": SELECTOR_AUTHORITY_SOURCE,
        "current_default_scope_before_use": CURRENT_DEFAULT_SCOPE,
        "default_scope_enabled_for_selected_classes": True,
        "non_selected_class_default_preserved": NON_SELECTED_CLASS_DEFAULT,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "redaction_policy_id": REDACTION_POLICY_ID,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_or_connector_secret_exposed": False,
    }
    for field, expected in expected_fields.items():
        if receipt.get(field) != expected:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_selector_use_status_receipt_field_mismatch",
                    field=field,
                    expected=expected,
                    received=receipt.get(field),
                )
            )
    if _find_forbidden_fields(receipt):
        blocked.append(_reason("candidate_b_broader_scope_selector_use_status_receipt_forbidden_authority"))
    recomputed_hash = _selector_use_receipt_hash(receipt)
    if recomputed_hash != selector_use_receipt_hash:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_selector_use_status_stale_receipt_hash",
                expected=recomputed_hash,
                received=selector_use_receipt_hash,
            )
        )
    return blocked


def _selector_use_receipt_hash(receipt: Mapping[str, Any]) -> str:
    return _stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "selector_use_mode": RUNTIME_MODE,
            "source_runtime_schema_id": SOURCE_RUNTIME_SCHEMA_ID,
            "source_runtime_mode": SOURCE_RUNTIME_MODE,
            "runtime_selection_receipt_id": receipt.get("runtime_selection_receipt_id"),
            "runtime_selection_receipt_hash": receipt.get("runtime_selection_receipt_hash"),
            "selected_scope_classes": _string_list(receipt.get("selected_scope_classes")),
            "selector_authority_source": SELECTOR_AUTHORITY_SOURCE,
            "current_default_scope_before_use": CURRENT_DEFAULT_SCOPE,
            "non_selected_class_default_preserved": NON_SELECTED_CLASS_DEFAULT,
            "baseline_rollback_preserved": receipt.get("baseline_rollback_preserved") is True,
            "candidate_a_semantics_preserved": receipt.get("candidate_a_semantics_preserved") is True,
            "redaction_policy_id": REDACTION_POLICY_ID,
        }
    )


def _runtime_receipt_root(
    *,
    create: bool = True,
    error_cls: type[CandidateBBroaderScopeSelectorUseError] = CandidateBBroaderScopeSelectorUseError,
) -> Path:
    configured = str(settings.layer3_candidate_b_runtime_bridge_dir or "").strip()
    if not configured:
        raise error_cls(
            "candidate_b_broader_scope_selector_use_receipt_dir_unset",
            "LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR must be set before selector use can record receipts.",
            http_status=409,
        )
    root = Path(configured)
    if not root.is_absolute():
        raise error_cls(
            "candidate_b_broader_scope_selector_use_receipt_dir_not_absolute",
            "LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR must be an absolute server-owned directory.",
            http_status=409,
        )
    resolved = root.resolve()
    if create:
        resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _read_optional_receipt(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_required_receipt(path)


def _read_required_receipt(
    path: Path,
    *,
    error_cls: type[CandidateBBroaderScopeSelectorUseError] = CandidateBBroaderScopeSelectorUseError,
) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise error_cls(
            "candidate_b_broader_scope_selector_use_receipt_unreadable",
            "Candidate B broader-scope selector-use receipt authority could not be read.",
            http_status=409,
            details={"reason": exc.__class__.__name__},
        ) from exc
    if not isinstance(receipt, dict):
        raise error_cls(
            "candidate_b_broader_scope_selector_use_receipt_invalid",
            "Candidate B broader-scope selector-use receipts must be JSON objects.",
            http_status=409,
        )
    return receipt


def _normalise_payload(
    payload: Mapping[str, Any],
    *,
    error_cls: type[CandidateBBroaderScopeSelectorUseError] = CandidateBBroaderScopeSelectorUseError,
) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(_find_forbidden_fields(fields))
    if blocked:
        raise error_cls(
            "candidate_b_broader_scope_selector_use_forbidden_request_fields",
            "The selector-use runtime does not admit caller paths, URLs, selectors, connectors, storage roots, or browser authority.",
            details={"blocked_fields": blocked},
        )
    return fields


def _find_forbidden_fields(value: Any, *, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key) in FORBIDDEN_FIELDS:
                found.append(path)
            found.extend(_find_forbidden_fields(child, prefix=path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_fields(child, prefix=f"{prefix}[{index}]"))
    return found


def _required_str(
    fields: Mapping[str, Any],
    key: str,
    *,
    error_cls: type[CandidateBBroaderScopeSelectorUseError] = CandidateBBroaderScopeSelectorUseError,
) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise error_cls(
            "candidate_b_broader_scope_selector_use_required_field_missing",
            "A required Candidate B broader-scope selector-use field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_storage_id(
    fields: Mapping[str, Any],
    key: str,
    *,
    prefix: str,
    error_cls: type[CandidateBBroaderScopeSelectorUseError] = CandidateBBroaderScopeSelectorUseError,
) -> str:
    value = _required_str(fields, key, error_cls=error_cls)
    if (
        not value.startswith(f"{prefix}-")
        or "/" in value
        or "\\" in value
        or ".." in value
        or value in {".", ".."}
    ):
        raise error_cls(
            "candidate_b_broader_scope_selector_use_storage_id_invalid",
            "Candidate B broader-scope selector-use receipt identifiers must be server-owned storage identifiers.",
            http_status=409,
            details={"expected_prefix": prefix},
        )
    return value


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]


def _negative_invariants(default_scope_expansion_enabled: bool) -> dict[str, bool]:
    return {
        "baseline_non_pdf_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_current_pdf_default_changed": False,
        "candidate_b_broader_default_scope_enabled": default_scope_expansion_enabled,
        "selector_mutation_performed": False,
        "source_expansion_enabled": False,
        "runtime_db_or_storage_expansion_enabled": False,
        "pdf_or_image_text_material_ingestion_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "auth_security_expansion_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "browser_storage_authority_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
    }


def _reason(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "details": details}


def _stable_hash(value: Mapping[str, Any]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat()
