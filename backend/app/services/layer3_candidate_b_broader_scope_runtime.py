from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_candidate_b_broader_scope_readiness


SCHEMA_ID = "layer3.candidate_b_broader_eligible_corpus_default_scope_runtime.v1"
SCHEMA_VERSION = 1
RUNTIME_MODE = "candidate_b_broader_eligible_corpus_default_scope_runtime_v1"
SELECTED_STATE = "candidate_b_broader_eligible_corpus_default_scope_runtime_selected"
BLOCKED_STATE = "candidate_b_broader_eligible_corpus_default_scope_runtime_blocked"
CURRENT_DEFAULT_SCOPE = layer3_candidate_b_broader_scope_readiness.CURRENT_DEFAULT_SCOPE
READINESS_SCHEMA_ID = layer3_candidate_b_broader_scope_readiness.SCHEMA_ID
READINESS_MODE = layer3_candidate_b_broader_scope_readiness.AUDIT_MODE
READY_STATE = layer3_candidate_b_broader_scope_readiness.READY_STATE
RECEIPT_PREFIX = "cb-broader-scope-runtime"
REDACTION_POLICY_ID = "candidate_b_broader_scope_runtime_selection_redaction_v1"
NON_PDF_DEFAULT = "baseline"
SELECTED_SCOPE_CLASSES_SOURCE = "proposed_default_scope_classes_from_matching_ready_audit"

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


class CandidateBBroaderScopeRuntimeError(Exception):
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
            "request_id": "candidate-b-broader-scope-runtime-error",
            "server_time": _server_time(),
            "status": "blocked",
            "mode": RUNTIME_MODE,
            "runtime_state": BLOCKED_STATE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def select_candidate_b_broader_scope_runtime(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required_str(fields, "client_request_id")
    runtime_mode = _required_str(fields, "runtime_mode")
    if runtime_mode != RUNTIME_MODE:
        raise CandidateBBroaderScopeRuntimeError(
            "candidate_b_broader_scope_runtime_mode_not_admitted",
            "Only the frozen Candidate B broader eligible-corpus default-scope runtime mode is admitted.",
            details={"expected_runtime_mode": RUNTIME_MODE, "received_runtime_mode": runtime_mode},
        )

    readiness_audit = fields.get("readiness_audit")
    selected_scope_classes = _string_list(fields.get("selected_scope_classes"))
    expected_audit_id = _required_storage_id(fields, "readiness_audit_id")
    expected_audit_hash = _required_str(fields, "readiness_audit_hash")

    blocked: list[dict[str, Any]] = []
    if fields.get("operator_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_runtime_operator_confirmation_missing"))
    if fields.get("rollback_to_baseline_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_runtime_rollback_to_baseline_missing"))
    if not selected_scope_classes:
        blocked.append(_reason("candidate_b_broader_scope_runtime_no_selected_scope_class"))

    persisted_audit, persisted_audit_blocks = _load_persisted_readiness_audit(
        expected_audit_id,
        expected_audit_hash,
    )
    blocked.extend(persisted_audit_blocks)
    inline_audit_binding_blocks = _validate_inline_readiness_audit_binding(
        readiness_audit,
        expected_audit_id,
        expected_audit_hash,
    )

    audit_summary = _validate_readiness_audit(
        persisted_audit,
        selected_scope_classes=selected_scope_classes,
        expected_audit_id=expected_audit_id,
        expected_audit_hash=expected_audit_hash,
    )
    blocked.extend(audit_summary["blocked_reasons"])

    receipt_hash = _stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "runtime_mode": RUNTIME_MODE,
            "readiness_audit_id": expected_audit_id,
            "readiness_audit_hash": expected_audit_hash,
            "selected_scope_classes": selected_scope_classes,
            "current_default_scope_preserved": CURRENT_DEFAULT_SCOPE,
            "non_pdf_default_preserved": NON_PDF_DEFAULT,
            "baseline_rollback_preserved": fields.get("rollback_to_baseline_confirmation") is True,
            "candidate_a_semantics_preserved": True,
            "candidate_b_document_processing_engine_preserved": (
                layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_ENGINE_SCOPE
            ),
            "candidate_b_visual_lane_preserved": (
                layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_VISUAL_LANE_SCOPE
            ),
            "redaction_policy_id": REDACTION_POLICY_ID,
        }
    )
    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    runtime_state = SELECTED_STATE if not blocked else BLOCKED_STATE
    receipt_ref = None
    receipt_status = "not_recorded"
    if runtime_state == SELECTED_STATE:
        receipt_ref = _write_selection_receipt(
            receipt_id=receipt_id,
            receipt_hash=receipt_hash,
            request_id=request_id,
            readiness_audit_id=expected_audit_id,
            readiness_audit_hash=expected_audit_hash,
            selected_scope_classes=selected_scope_classes,
            audit_summary=audit_summary["summary"],
        )
        receipt_status = "recorded"

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "selected" if runtime_state == SELECTED_STATE else "blocked",
        "mode": RUNTIME_MODE,
        "runtime_state": runtime_state,
        "selection_receipt_id": receipt_id if runtime_state == SELECTED_STATE else None,
        "selection_receipt_hash": receipt_hash if runtime_state == SELECTED_STATE else None,
        "selection_receipt_ref": receipt_ref,
        "selection_receipt_status": receipt_status,
        "blocked_reasons": blocked,
        "readiness_audit_binding": {
            "schema_id": READINESS_SCHEMA_ID,
            "mode": READINESS_MODE,
            "required_state": READY_STATE,
            "readiness_audit_id": expected_audit_id,
            "readiness_audit_hash": expected_audit_hash,
            "server_issued_receipt_required": True,
            "inline_readiness_audit_required": False,
            "inline_readiness_audit_binding_blocks": inline_audit_binding_blocks,
            "binding_verified": not audit_summary["blocked_reasons"] and not persisted_audit_blocks,
        },
        "selected_scope_classes": selected_scope_classes,
        "selected_scope_classes_source": SELECTED_SCOPE_CLASSES_SOURCE,
        "current_default_scope_preserved": CURRENT_DEFAULT_SCOPE,
        "non_pdf_default_preserved": NON_PDF_DEFAULT,
        "baseline_rollback": {
            "selector": NON_PDF_DEFAULT,
            "available": fields.get("rollback_to_baseline_confirmation") is True,
            "depends_on_candidate_b_artifacts": False,
        },
        "candidate_a_semantics": {"visual_lane_mode": "candidate_a_page_evidence_v1", "preserved": True},
        "candidate_b_scope_authority": {
            "document_processing_engine": layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_ENGINE_SCOPE,
            "visual_lane_mode": layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_VISUAL_LANE_SCOPE,
            "bundle_and_runtime_authority_remain_distinct": True,
        },
        "operator_visible_scope_status": {
            "broader_scope_runtime_selected": runtime_state == SELECTED_STATE,
            "selected_scope_class_count": len(selected_scope_classes) if runtime_state == SELECTED_STATE else 0,
            "redacted_selection_receipt_available": receipt_ref is not None,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_or_connector_secret_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_ready_audit_blocks_selection": True,
            "missing_server_issued_ready_audit_receipt_blocks_selection": True,
            "stale_audit_hash_blocks_selection": True,
            "unready_scope_class_blocks_selection": True,
            "unproposed_scope_class_blocks_selection": True,
            "missing_rollback_confirmation_blocks_selection": True,
            "candidate_a_semantic_drift_blocks_selection": True,
        },
        "default_scope_expansion_enabled": runtime_state == SELECTED_STATE,
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
        "negative_invariants": _negative_invariants(runtime_state == SELECTED_STATE),
        "next_allowed_actions": (
            ["use redacted receipt as broader Candidate B scope runtime-selection authority"]
            if runtime_state == SELECTED_STATE
            else ["repair or bind a ready broader-scope audit receipt before selecting runtime scope"]
        ),
    }


def _load_persisted_readiness_audit(audit_id: str, audit_hash: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    try:
        audit = layer3_candidate_b_broader_scope_readiness.read_candidate_b_broader_scope_readiness_audit_receipt(
            audit_id,
            expected_audit_hash=audit_hash,
        )
    except layer3_candidate_b_broader_scope_readiness.CandidateBBroaderScopeReadinessError as exc:
        return None, [
            _reason(
                "candidate_b_broader_scope_runtime_server_ready_audit_receipt_unavailable",
                readiness_error_code=exc.code,
            )
        ]
    return audit, []


def _validate_inline_readiness_audit_binding(
    value: Any,
    expected_audit_id: str,
    expected_audit_hash: str,
) -> list[dict[str, Any]]:
    if not value:
        return []
    if not isinstance(value, Mapping):
        return [_reason("candidate_b_broader_scope_runtime_ready_audit_inline_invalid")]
    blocked: list[dict[str, Any]] = []
    for field, expected in (("audit_id", expected_audit_id), ("audit_hash", expected_audit_hash)):
        if value.get(field) != expected:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_runtime_ready_audit_field_mismatch",
                    field=field,
                    expected=expected,
                    received=value.get(field),
                )
            )
    recomputed_hash = _readiness_audit_hash(value)
    if recomputed_hash != expected_audit_hash:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_runtime_stale_audit_hash",
                expected=recomputed_hash,
                received=expected_audit_hash,
            )
        )
    return blocked


def _validate_readiness_audit(
    value: Any,
    *,
    selected_scope_classes: list[str],
    expected_audit_id: str,
    expected_audit_hash: str,
) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    if not isinstance(value, Mapping):
        return {
            "blocked_reasons": [_reason("candidate_b_broader_scope_runtime_ready_audit_missing")],
            "summary": {"status": "missing"},
        }
    audit = value
    expected_fields = {
        "schema_id": READINESS_SCHEMA_ID,
        "schema_version": layer3_candidate_b_broader_scope_readiness.SCHEMA_VERSION,
        "mode": READINESS_MODE,
        "status": "ready",
        "audit_state": READY_STATE,
        "audit_id": expected_audit_id,
        "audit_hash": expected_audit_hash,
        "current_default_scope": CURRENT_DEFAULT_SCOPE,
    }
    for field, expected in expected_fields.items():
        if audit.get(field) != expected:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_runtime_ready_audit_field_mismatch",
                    field=field,
                    expected=expected,
                    received=audit.get(field),
                )
            )
    recomputed_hash = _readiness_audit_hash(audit)
    if recomputed_hash != expected_audit_hash:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_runtime_stale_audit_hash",
                expected=recomputed_hash,
                received=expected_audit_hash,
            )
        )
    _validate_readiness_semantic_authority(audit, blocked)

    proposed_scope_classes = _string_list(audit.get("proposed_default_scope_classes"))
    if selected_scope_classes != proposed_scope_classes:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_runtime_selected_classes_do_not_match_ready_audit",
                expected=proposed_scope_classes,
                received=selected_scope_classes,
            )
        )
    class_results = audit.get("scope_class_results")
    if not isinstance(class_results, list):
        blocked.append(_reason("candidate_b_broader_scope_runtime_scope_results_missing"))
        class_results = []
    result_by_class = {
        str(item.get("scope_class") or ""): item
        for item in class_results
        if isinstance(item, Mapping)
    }
    for scope_class in selected_scope_classes:
        item = result_by_class.get(scope_class)
        if not item:
            blocked.append(_reason("candidate_b_broader_scope_runtime_selected_scope_result_missing", scope_class=scope_class))
            continue
        if item.get("proposed_for_default_scope") is not True:
            blocked.append(_reason("candidate_b_broader_scope_runtime_unproposed_scope_class", scope_class=scope_class))
        if item.get("scope_readiness") != "ready_for_separate_selection":
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_runtime_unready_scope_class",
                    scope_class=scope_class,
                    received=item.get("scope_readiness"),
                )
            )
    if audit.get("default_scope_expansion_admitted") is not False:
        blocked.append(_reason("candidate_b_broader_scope_runtime_audit_already_expands_default_scope"))
    for field in (
        "selector_mutation_performed",
        "source_expansion_admitted",
        "runtime_db_or_storage_expansion_admitted",
        "provider_object_write_enabled",
        "connector_dispatch_enabled",
        "rag_vector_model_runtime_enabled",
        "full_mockup_activation_enabled",
        "frontend_durable_authority_enabled",
        "browser_storage_authority_enabled",
        "raw_local_path_exposed",
        "raw_url_exposed",
    ):
        if audit.get(field) is not False:
            blocked.append(_reason("candidate_b_broader_scope_runtime_audit_negative_invariant_drift", field=field))

    return {
        "blocked_reasons": blocked,
        "summary": {
            "audit_id": audit.get("audit_id"),
            "audit_hash": audit.get("audit_hash"),
            "proposed_default_scope_classes": proposed_scope_classes,
            "selected_scope_classes": selected_scope_classes,
            "ready_scope_class_count": len(selected_scope_classes) if not blocked else 0,
        },
    }


def _readiness_audit_hash(audit: Mapping[str, Any]) -> str:
    return _stable_hash(
        {
            "hash_version": "candidate_b_broader_scope_readiness_audit_hash_v1",
            "audit_mode": READINESS_MODE,
            "exact_corpus_class_list": _string_list(audit.get("exact_corpus_class_list")),
            "explicit_exclusion_list": sorted(_string_list(audit.get("explicit_exclusion_list"))),
            "proposed_default_scope_classes": _string_list(audit.get("proposed_default_scope_classes")),
            "scope_results": audit.get("scope_class_results") if isinstance(audit.get("scope_class_results"), list) else [],
            "operator_confirmation": audit.get("status") == "ready",
            "rollback_to_baseline_confirmation": (
                isinstance(audit.get("baseline_rollback"), Mapping)
                and audit["baseline_rollback"].get("available") is True
            ),
            "candidate_a_semantics": {
                "visual_lane_mode": _mapping_value(audit.get("candidate_a_semantics"), "visual_lane_mode"),
                "preserved": _mapping_value(audit.get("candidate_a_semantics"), "preserved"),
            },
            "candidate_b_scope_authority": {
                "document_processing_engine": _mapping_value(
                    audit.get("candidate_b_scope_authority"),
                    "document_processing_engine",
                ),
                "visual_lane_mode": _mapping_value(audit.get("candidate_b_scope_authority"), "visual_lane_mode"),
                "bundle_and_runtime_authority_remain_distinct": _mapping_value(
                    audit.get("candidate_b_scope_authority"),
                    "bundle_and_runtime_authority_remain_distinct",
                ),
            },
        }
    )


def _validate_readiness_semantic_authority(audit: Mapping[str, Any], blocked: list[dict[str, Any]]) -> None:
    expected = (
        ("candidate_a_semantics", "visual_lane_mode", "candidate_a_page_evidence_v1"),
        ("candidate_a_semantics", "preserved", True),
        (
            "candidate_b_scope_authority",
            "document_processing_engine",
            layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_ENGINE_SCOPE,
        ),
        (
            "candidate_b_scope_authority",
            "visual_lane_mode",
            layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_VISUAL_LANE_SCOPE,
        ),
        ("candidate_b_scope_authority", "bundle_and_runtime_authority_remain_distinct", True),
    )
    for section, field, expected_value in expected:
        section_value = audit.get(section)
        received = _mapping_value(section_value, field)
        if received != expected_value:
            blocked.append(
                _reason(
                    "candidate_b_broader_scope_runtime_ready_audit_semantic_authority_drift",
                    section=section,
                    field=field,
                    expected=expected_value,
                    received=received,
                )
            )


def _mapping_value(value: Any, field: str) -> Any:
    if not isinstance(value, Mapping):
        return None
    return value.get(field)


def _write_selection_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    request_id: str,
    readiness_audit_id: str,
    readiness_audit_hash: str,
    selected_scope_classes: list[str],
    audit_summary: Mapping[str, Any],
) -> str:
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "runtime_mode": RUNTIME_MODE,
        "runtime_state": SELECTED_STATE,
        "request_id": request_id,
        "selection_receipt_id": receipt_id,
        "selection_receipt_hash": receipt_hash,
        "readiness_audit_id": readiness_audit_id,
        "readiness_audit_hash": readiness_audit_hash,
        "selected_scope_classes": selected_scope_classes,
        "selected_scope_classes_source": SELECTED_SCOPE_CLASSES_SOURCE,
        "current_default_scope_preserved": CURRENT_DEFAULT_SCOPE,
        "non_pdf_default_preserved": NON_PDF_DEFAULT,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "candidate_b_document_processing_engine_preserved": (
            layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_ENGINE_SCOPE
        ),
        "candidate_b_visual_lane_preserved": layer3_candidate_b_broader_scope_readiness.CANDIDATE_B_VISUAL_LANE_SCOPE,
        "redaction_policy_id": REDACTION_POLICY_ID,
        "audit_summary": dict(audit_summary),
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_or_connector_secret_exposed": False,
        "recorded_at": _server_time(),
    }
    target = _receipt_root() / "broader-scope-runtime" / f"{receipt_id}.json"
    if target.exists():
        existing = _read_receipt(target)
        if existing.get("selection_receipt_hash") != receipt_hash:
            raise CandidateBBroaderScopeRuntimeError(
                "candidate_b_broader_scope_runtime_selection_receipt_conflict",
                "The Candidate B broader-scope runtime selection receipt is stale or contradictory.",
                http_status=409,
            )
    else:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            raise CandidateBBroaderScopeRuntimeError(
                "candidate_b_broader_scope_runtime_selection_receipt_write_failed",
                "Candidate B broader-scope runtime selection receipt could not be recorded.",
                http_status=409,
                details={"reason": exc.__class__.__name__},
            ) from exc
    return f"candidate-b-broader-scope-runtime://{receipt_id}/{receipt_hash[:24]}"


def _receipt_root() -> Path:
    configured = str(settings.layer3_candidate_b_runtime_bridge_dir or "").strip()
    if not configured:
        raise CandidateBBroaderScopeRuntimeError(
            "candidate_b_broader_scope_runtime_receipt_dir_unset",
            "LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR must be set before broader-scope runtime selection can record receipts.",
            http_status=409,
        )
    root = Path(configured)
    if not root.is_absolute():
        raise CandidateBBroaderScopeRuntimeError(
            "candidate_b_broader_scope_runtime_receipt_dir_not_absolute",
            "LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR must be an absolute server-owned directory.",
            http_status=409,
        )
    resolved = root.resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _read_receipt(path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBBroaderScopeRuntimeError(
            "candidate_b_broader_scope_runtime_selection_receipt_unreadable",
            "Candidate B broader-scope runtime selection receipt could not be read.",
            http_status=409,
            details={"reason": exc.__class__.__name__},
        ) from exc
    if not isinstance(receipt, dict):
        raise CandidateBBroaderScopeRuntimeError(
            "candidate_b_broader_scope_runtime_selection_receipt_invalid",
            "Candidate B broader-scope runtime selection receipts must be JSON objects.",
            http_status=409,
        )
    return receipt


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(_find_forbidden_fields(fields))
    if blocked:
        raise CandidateBBroaderScopeRuntimeError(
            "candidate_b_broader_scope_runtime_forbidden_request_fields",
            "The broader-scope runtime selection does not admit caller paths, URLs, selectors, connectors, storage roots, or browser authority.",
            details={"blocked_fields": blocked},
        )
    return fields


def _find_forbidden_fields(value: Any, *, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key) in FORBIDDEN_FIELDS and not _allowed_readiness_authority_field(path):
                found.append(path)
            found.extend(_find_forbidden_fields(child, prefix=path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_fields(child, prefix=f"{prefix}[{index}]"))
    return found


def _allowed_readiness_authority_field(path: str) -> bool:
    return path in {
        "readiness_audit.candidate_a_semantics.visual_lane_mode",
        "readiness_audit.candidate_b_scope_authority.document_processing_engine",
        "readiness_audit.candidate_b_scope_authority.visual_lane_mode",
    }


def _required_str(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBBroaderScopeRuntimeError(
            "candidate_b_broader_scope_runtime_required_field_missing",
            "A required Candidate B broader-scope runtime field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_storage_id(fields: Mapping[str, Any], key: str) -> str:
    value = _required_str(fields, key)
    if not all(ch.isascii() and (ch.isalnum() or ch in {"-", "_"}) for ch in value):
        raise CandidateBBroaderScopeRuntimeError(
            "candidate_b_broader_scope_runtime_receipt_id_invalid",
            "Candidate B broader-scope runtime receipt ids must be server-owned storage identifiers.",
            details={"field": key},
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
