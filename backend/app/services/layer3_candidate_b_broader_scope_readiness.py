from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings


SCHEMA_ID = "layer3.candidate_b_broader_eligible_corpus_scope_readiness_audit.v1"
SCHEMA_VERSION = 1
AUDIT_MODE = "candidate_b_broader_eligible_corpus_scope_readiness_audit_v1"
READY_STATE = "candidate_b_broader_eligible_corpus_scope_ready_for_separate_selection"
BLOCKED_STATE = "candidate_b_broader_eligible_corpus_scope_readiness_blocked"
CURRENT_DEFAULT_SCOPE = "eligible_effective_pdfs_only"
CANDIDATE_B_ENGINE_SCOPE = "candidate_b_opendataloader_pdf_for_eligible_effective_pdfs_only"
CANDIDATE_B_VISUAL_LANE_SCOPE = "candidate_b_opendataloader_page_evidence_v1_explicit_only"

SCOPE_CLASSES = (
    "office_documents",
    "images_or_ocr",
    "zip_members",
    "structured_json_or_csv_or_xlsx",
    "sec_edgar",
    "web_or_database_sources",
    "mixed_corpus_batches",
)
REQUIRED_EXCLUSIONS = (
    "selector_mutation_without_separate_freeze",
    "source_expansion_without_separate_freeze",
    "runtime_db_or_storage_expansion",
    "pdf_or_image_text_material_ingestion",
    "provider_object_writes",
    "connector_dispatch",
    "rag_vector_model_runtime",
    "auth_security_expansion",
    "full_mockup_activation",
    "frontend_durable_authority",
    "browser_storage_authority",
)
REQUIRED_SCOPE_FIELDS = (
    "current_parser_or_engine_authority",
    "baseline_rollback_behavior",
    "candidate_a_interaction",
    "candidate_b_runtime_compatibility",
    "layer3_material_authority_bridge_compatibility",
    "artifact_family_preservation",
    "redaction_and_status_projection",
    "corpus_scale_proof",
    "fail_closed_stale_or_missing_authority",
    "regression_disposition",
)
READY_SCOPE_VALUES = {
    "baseline_rollback_behavior": "baseline_preserved",
    "candidate_a_interaction": "candidate_a_semantics_preserved",
    "candidate_b_runtime_compatibility": "compatible_for_separate_selection",
    "layer3_material_authority_bridge_compatibility": "compatible_for_separate_selection",
    "artifact_family_preservation": "preserved",
    "redaction_and_status_projection": "redacted_operator_visible",
    "corpus_scale_proof": "available",
    "fail_closed_stale_or_missing_authority": "proven",
    "regression_disposition": "no_unacceptable_regression_identified",
}
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
}


class CandidateBBroaderScopeReadinessError(Exception):
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
            "request_id": "candidate-b-broader-scope-readiness-error",
            "server_time": _server_time(),
            "status": "blocked",
            "mode": AUDIT_MODE,
            "audit_state": BLOCKED_STATE,
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def evaluate_candidate_b_broader_scope_readiness(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required_str(fields, "client_request_id")
    audit_mode = _required_str(fields, "audit_mode")
    if audit_mode != AUDIT_MODE:
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_mode_not_admitted",
            "Only the frozen Candidate B broader eligible-corpus scope readiness audit mode is admitted.",
            details={"expected_audit_mode": AUDIT_MODE, "received_audit_mode": audit_mode},
        )

    exact_scope_classes = _required_string_list(fields, "exact_corpus_class_list")
    explicit_exclusions = _required_string_list(fields, "explicit_exclusion_list")
    proposed_scope_classes = _required_string_list(fields, "proposed_default_scope_classes")
    scope_evidence = fields.get("scope_evidence")
    if not isinstance(scope_evidence, Mapping):
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_scope_evidence_missing",
            "The broader scope audit requires per-class scope evidence.",
        )

    blocked: list[dict[str, Any]] = []
    if tuple(exact_scope_classes) != SCOPE_CLASSES:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_readiness_exact_class_list_mismatch",
                expected=list(SCOPE_CLASSES),
                received=exact_scope_classes,
            )
        )
    missing_exclusions = sorted(set(REQUIRED_EXCLUSIONS) - set(explicit_exclusions))
    if missing_exclusions:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_readiness_exclusion_list_incomplete",
                missing_exclusions=missing_exclusions,
            )
        )
    invalid_proposed = sorted(set(proposed_scope_classes) - set(SCOPE_CLASSES))
    if invalid_proposed:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_readiness_proposed_scope_class_not_admitted",
                invalid_scope_classes=invalid_proposed,
            )
        )
    if not proposed_scope_classes:
        blocked.append(_reason("candidate_b_broader_scope_readiness_no_proposed_scope_class"))
    if fields.get("operator_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_readiness_operator_confirmation_missing"))
    if fields.get("rollback_to_baseline_confirmation") is not True:
        blocked.append(_reason("candidate_b_broader_scope_readiness_rollback_to_baseline_missing"))

    scope_results = []
    for scope_class in SCOPE_CLASSES:
        result = _evaluate_scope_class(
            scope_class,
            scope_evidence.get(scope_class),
            proposed=scope_class in set(proposed_scope_classes),
        )
        blocked.extend(result["blocked_reasons"])
        scope_results.append(result["summary"])

    audit_hash = _readiness_audit_hash(
        exact_scope_classes=exact_scope_classes,
        explicit_exclusions=explicit_exclusions,
        proposed_scope_classes=proposed_scope_classes,
        scope_results=scope_results,
        operator_confirmation=fields.get("operator_confirmation") is True,
        rollback_to_baseline_confirmation=fields.get("rollback_to_baseline_confirmation") is True,
    )
    audit_state = READY_STATE if not blocked else BLOCKED_STATE
    default_scope_expansion_admitted = False

    audit = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "ready" if audit_state == READY_STATE else "blocked",
        "mode": AUDIT_MODE,
        "audit_state": audit_state,
        "audit_id": f"cb-broader-scope-readiness-{audit_hash[:24]}",
        "audit_hash": audit_hash,
        "blocked_reasons": blocked,
        "current_default_scope": CURRENT_DEFAULT_SCOPE,
        "selected_decision_scope": "candidate_b_default_scope_after_eligible_effective_pdf_acceptance",
        "exact_corpus_class_list": exact_scope_classes,
        "explicit_exclusion_list": explicit_exclusions,
        "proposed_default_scope_classes": proposed_scope_classes,
        "scope_class_results": scope_results,
        "required_scope_evidence": list(REQUIRED_SCOPE_FIELDS),
        "required_exclusions": list(REQUIRED_EXCLUSIONS),
        "baseline_rollback": {
            "selector": "baseline",
            "available": fields.get("rollback_to_baseline_confirmation") is True,
            "non_pdf_default_preserved": True,
            "depends_on_candidate_b_artifacts": False,
        },
        "candidate_a_semantics": {"visual_lane_mode": "candidate_a_page_evidence_v1", "preserved": True},
        "candidate_b_scope_authority": {
            "document_processing_engine": CANDIDATE_B_ENGINE_SCOPE,
            "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_SCOPE,
            "bundle_and_runtime_authority_remain_distinct": True,
        },
        "fail_closed_behavior": {
            "missing_scope_class_blocks_readiness": True,
            "missing_required_scope_evidence_blocks_readiness": True,
            "stale_or_missing_authority_blocks_readiness": True,
            "unacceptable_regression_blocks_readiness": True,
            "missing_rollback_confirmation_blocks_readiness": True,
        },
        "default_scope_expansion_admitted": default_scope_expansion_admitted,
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
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": (
            ["freeze_candidate_b_broader_default_scope_runtime_selection_for_exact_ready_classes"]
            if audit_state == READY_STATE
            else ["repair_missing_scope_evidence_or_keep_candidate_b_pdf_only_default"]
        ),
    }
    receipt = _record_readiness_audit_receipt(audit) if audit_state == READY_STATE else None
    audit["audit_receipt_status"] = "recorded" if receipt is not None else "not_recorded"
    audit["audit_receipt_ref"] = receipt["ref"] if receipt is not None else None
    return audit


def read_candidate_b_broader_scope_readiness_audit_receipt(
    audit_id: str,
    *,
    expected_audit_hash: str,
) -> dict[str, Any]:
    path = _readiness_receipt_path(audit_id)
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_receipt_missing",
            "The Candidate B broader-scope readiness audit must be server-issued and persisted before runtime selection.",
            http_status=409,
            details={"audit_id": audit_id},
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_receipt_unreadable",
            "The Candidate B broader-scope readiness audit receipt could not be read.",
            http_status=409,
            details={"reason": exc.__class__.__name__},
        ) from exc
    if not isinstance(receipt, dict) or not isinstance(receipt.get("readiness_audit"), dict):
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_receipt_invalid",
            "The Candidate B broader-scope readiness audit receipt must contain a readiness audit object.",
            http_status=409,
        )
    if receipt.get("audit_id") != audit_id or receipt.get("audit_hash") != expected_audit_hash:
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_receipt_binding_mismatch",
            "The Candidate B broader-scope readiness audit receipt does not match the requested audit binding.",
            http_status=409,
            details={"audit_id": audit_id},
        )
    return dict(receipt["readiness_audit"])


def _record_readiness_audit_receipt(audit: Mapping[str, Any]) -> dict[str, str] | None:
    configured = str(settings.layer3_candidate_b_runtime_bridge_dir or "").strip()
    if not configured:
        return None
    audit_id = str(audit.get("audit_id") or "")
    audit_hash = str(audit.get("audit_hash") or "")
    target = _readiness_receipt_path(audit_id)
    receipt = {
        "schema_id": "layer3.candidate_b_broader_eligible_corpus_scope_readiness_audit_receipt.v1",
        "schema_version": 1,
        "audit_id": audit_id,
        "audit_hash": audit_hash,
        "readiness_audit": dict(audit),
        "redaction_policy_id": "candidate_b_broader_scope_readiness_audit_receipt_redaction_v1",
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "provider_or_connector_secret_exposed": False,
        "recorded_at": _server_time(),
    }
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CandidateBBroaderScopeReadinessError(
                "candidate_b_broader_scope_readiness_receipt_unreadable",
                "The Candidate B broader-scope readiness audit receipt could not be read.",
                http_status=409,
                details={"reason": exc.__class__.__name__},
            ) from exc
        if not isinstance(existing, dict) or existing.get("audit_hash") != audit_hash:
            raise CandidateBBroaderScopeReadinessError(
                "candidate_b_broader_scope_readiness_receipt_conflict",
                "The Candidate B broader-scope readiness audit receipt is stale or contradictory.",
                http_status=409,
                details={"audit_id": audit_id},
            )
    else:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            raise CandidateBBroaderScopeReadinessError(
                "candidate_b_broader_scope_readiness_receipt_write_failed",
                "The Candidate B broader-scope readiness audit receipt could not be recorded.",
                http_status=409,
                details={"reason": exc.__class__.__name__},
            ) from exc
    return {"ref": f"candidate-b-broader-scope-readiness://{audit_id}/{audit_hash[:24]}"}


def _readiness_receipt_path(audit_id: str) -> Path:
    configured = str(settings.layer3_candidate_b_runtime_bridge_dir or "").strip()
    if not configured:
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_receipt_dir_unset",
            "LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR must be set before readiness audits can bind runtime selection.",
            http_status=409,
        )
    if not _is_storage_id(audit_id):
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_receipt_id_invalid",
            "Candidate B broader-scope readiness audit ids must be server-owned storage identifiers.",
            http_status=400,
            details={"field": "audit_id"},
        )
    root = Path(configured)
    if not root.is_absolute():
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_receipt_dir_not_absolute",
            "LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR must be an absolute server-owned directory.",
            http_status=409,
        )
    return root.resolve() / "broader-scope-readiness" / f"{audit_id}.json"


def _readiness_audit_hash(
    *,
    exact_scope_classes: list[str],
    explicit_exclusions: list[str],
    proposed_scope_classes: list[str],
    scope_results: list[dict[str, Any]],
    operator_confirmation: bool,
    rollback_to_baseline_confirmation: bool,
) -> str:
    return _stable_hash(
        {
            "hash_version": "candidate_b_broader_scope_readiness_audit_hash_v1",
            "audit_mode": AUDIT_MODE,
            "exact_corpus_class_list": exact_scope_classes,
            "explicit_exclusion_list": sorted(explicit_exclusions),
            "proposed_default_scope_classes": proposed_scope_classes,
            "scope_results": scope_results,
            "operator_confirmation": operator_confirmation,
            "rollback_to_baseline_confirmation": rollback_to_baseline_confirmation,
            "candidate_a_semantics": {
                "visual_lane_mode": "candidate_a_page_evidence_v1",
                "preserved": True,
            },
            "candidate_b_scope_authority": {
                "document_processing_engine": CANDIDATE_B_ENGINE_SCOPE,
                "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_SCOPE,
                "bundle_and_runtime_authority_remain_distinct": True,
            },
        }
    )


def _is_storage_id(value: str) -> bool:
    return bool(value) and all(ch.isascii() and (ch.isalnum() or ch in {"-", "_"}) for ch in value)


def _evaluate_scope_class(scope_class: str, evidence: Any, *, proposed: bool) -> dict[str, Any]:
    blocked: list[dict[str, Any]] = []
    if not isinstance(evidence, Mapping):
        return {
            "blocked_reasons": [_reason("candidate_b_broader_scope_readiness_scope_class_evidence_missing", scope_class=scope_class)],
            "summary": {"scope_class": scope_class, "scope_readiness": "missing", "proposed_for_default_scope": proposed},
        }

    missing = [field for field in REQUIRED_SCOPE_FIELDS if not str(evidence.get(field) or "").strip()]
    if missing:
        blocked.append(
            _reason(
                "candidate_b_broader_scope_readiness_required_scope_evidence_missing",
                scope_class=scope_class,
                missing_fields=missing,
            )
        )
    if evidence.get("selector_mutation_required_now") is not False:
        blocked.append(_reason("candidate_b_broader_scope_readiness_selector_mutation_required", scope_class=scope_class))
    if evidence.get("source_expansion_required_now") is not False:
        blocked.append(_reason("candidate_b_broader_scope_readiness_source_expansion_required", scope_class=scope_class))
    if evidence.get("runtime_db_or_storage_expansion_required_now") is not False:
        blocked.append(_reason("candidate_b_broader_scope_readiness_runtime_expansion_required", scope_class=scope_class))

    if proposed:
        for field, expected in READY_SCOPE_VALUES.items():
            received = str(evidence.get(field) or "").strip()
            if received != expected:
                blocked.append(
                    _reason(
                        "candidate_b_broader_scope_readiness_scope_field_not_ready",
                        scope_class=scope_class,
                        field=field,
                        expected=expected,
                        received=received or None,
                    )
                )

    return {
        "blocked_reasons": blocked,
        "summary": {
            "scope_class": scope_class,
            "proposed_for_default_scope": proposed,
            "scope_readiness": _scope_readiness_state(proposed=proposed, blocked=bool(blocked)),
            "current_parser_or_engine_authority": str(evidence.get("current_parser_or_engine_authority") or ""),
            "baseline_rollback_behavior": str(evidence.get("baseline_rollback_behavior") or ""),
            "candidate_a_interaction": str(evidence.get("candidate_a_interaction") or ""),
            "candidate_b_runtime_compatibility": str(evidence.get("candidate_b_runtime_compatibility") or ""),
            "layer3_material_authority_bridge_compatibility": str(
                evidence.get("layer3_material_authority_bridge_compatibility") or ""
            ),
            "artifact_family_preservation": str(evidence.get("artifact_family_preservation") or ""),
            "redaction_and_status_projection": str(evidence.get("redaction_and_status_projection") or ""),
            "corpus_scale_proof": str(evidence.get("corpus_scale_proof") or ""),
            "fail_closed_stale_or_missing_authority": str(evidence.get("fail_closed_stale_or_missing_authority") or ""),
            "regression_disposition": str(evidence.get("regression_disposition") or ""),
        },
    }


def _scope_readiness_state(*, proposed: bool, blocked: bool) -> str:
    if blocked:
        return "blocked"
    if proposed:
        return "ready_for_separate_selection"
    return "classified_not_proposed"


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(_find_forbidden_fields(fields))
    if blocked:
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_forbidden_request_fields",
            "The broader scope readiness audit does not admit caller paths, selector mutation, URLs, connectors, or browser authority.",
            details={"blocked_fields": blocked},
        )
    blocked_values = sorted(_find_forbidden_values(fields))
    if blocked_values:
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_forbidden_request_values",
            "The broader scope readiness audit does not admit caller paths, URLs, or secret-like values.",
            details={"blocked_values": blocked_values},
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


def _find_forbidden_values(value: Any, *, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.extend(_find_forbidden_values(child, prefix=path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_values(child, prefix=f"{prefix}[{index}]"))
    elif isinstance(value, str) and _looks_like_forbidden_value(value):
        found.append(prefix)
    return found


def _looks_like_forbidden_value(value: str) -> bool:
    candidate = value.strip()
    lowered = candidate.lower()
    return (
        "://" in candidate
        or candidate.startswith(("\\\\", "/"))
        or (len(candidate) >= 3 and candidate[1] == ":" and candidate[2] in {"\\", "/"})
        or candidate in {".", ".."}
        or candidate.startswith(("../", "..\\", "./", ".\\"))
        or "/" in candidate
        or "\\" in candidate
        or "begin private key" in lowered
        or "password=" in lowered
        or "secret=" in lowered
        or "token=" in lowered
    )


def _required_str(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_required_field_missing",
            "A required Candidate B broader scope readiness field is missing or empty.",
            details={"field": key},
        )
    return value


def _required_string_list(fields: Mapping[str, Any], key: str) -> list[str]:
    value = fields.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise CandidateBBroaderScopeReadinessError(
            "candidate_b_broader_scope_readiness_required_list_missing",
            "A required Candidate B broader scope readiness list is missing or invalid.",
            details={"field": key},
        )
    return [item.strip() for item in value]


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_non_pdf_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_default_scope_broadened": False,
        "candidate_b_visual_lane_default_enabled": False,
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
