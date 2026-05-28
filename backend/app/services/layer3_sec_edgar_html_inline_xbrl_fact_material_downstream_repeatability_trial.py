from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_status
from app.services.layer3_sec_edgar_ref_safety import contains_forbidden_ref, find_forbidden_ref_paths
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial.v1"
)
REQUEST_SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_request.v1"
)
SCHEMA_VERSION = 1
TRIAL_MODE = (
    "append_only_trial_receipt_over_original_and_repeat_fact_material_downstream_status_authority_without_sec_fetch_or_processing_execution"
)
OPERATOR_DECISION = (
    "record_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial"
)
TRIAL_RECEIPT_PREFIX = (
    "sec-edgar-html-inline-xbrl-fact-material-downstream-operator-repeatability-trial"
)
TRIAL_RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-fact-material-repeatability-trial"
TRIAL_ACCEPTED_STATE = (
    "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_accepted"
)
TRIAL_BLOCKED_STATE = (
    "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_blocked"
)
ACCEPTED_DISPOSITIONS = {"no_regression_observed", "delta_reviewed_no_regression"}
BLOCKED_DISPOSITION = "regression_detected_blocked"
REDACTION_POLICY_ID = (
    "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_redaction_v1"
)

FORBIDDEN_REQUEST_FIELDS = {
    "args",
    "path",
    "paths",
    "directory",
    "file_path",
    "local_directory",
    "local_path",
    "raw_path",
    "url",
    "urls",
    "raw_url",
    "source_url",
    "filing_url",
    "sec_url",
    "live_sec_url",
    "provider_url",
    "connector_url",
    "command",
    "process",
    "process_id",
    "pid",
    "stdout",
    "stderr",
    "file",
    "files",
    "file_bytes",
    "artifact_bytes",
    "provider_credentials",
    "connector_credentials",
    "provider_public_url",
    "provider_private_url",
    "provider_private_signed_url_token",
    "connector_dispatch",
    "rag_vector_index",
    "browser_storage",
    "frontend_authority",
    "full_mockup_activation",
    "source_upload",
    "source_expansion",
    "parser_expansion",
    "runtime_db_write",
    "storage_dir",
    "value_text",
    "fact_value",
    "fact_values",
    "raw_fact_value",
    "raw_fact_values",
}
ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "trial_mode",
    "operator_decision",
    "original_operator_status_request",
    "original_operator_status_hash",
    "repeat_operator_status_request",
    "repeat_operator_status_hash",
    "operator_repeatability_disposition",
    "operator_confirmation",
    "actor",
}
AUTHORITY_FIELDS = (
    "dataset_version_id",
    "dataset_version_hash",
    "source_family",
    "parser_family",
    "typed_content_contract_id",
    "parser_receipt_hash",
    "connector_receipt_hash",
    "live_source_artifact_receipt_hash",
    "source_artifact_receipt_hash",
    "content_sha256",
    "primary_document_hash",
    "content_order_hash",
    "inline_xbrl_marker_inventory_hash",
    "fact_authority_receipt_hash",
    "fact_inventory_hash",
    "diagnostics_hash",
    "materialization_receipt_hash",
    "fact_material_bridge_receipt_hash",
    "material_bridge_receipt_hash",
    "material_preview_hash",
    "gate_b_decision_manifest_id",
    "session_id",
    "selection_manifest_id",
    "material_snapshot_payload_hash",
    "coverage_evidence_hash",
    "negative_invariants_hash",
)

def record_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "trial_mode", TRIAL_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)

    disposition = _required(request, "operator_repeatability_disposition")
    if disposition not in ACCEPTED_DISPOSITIONS and disposition != BLOCKED_DISPOSITION:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_disposition_not_admitted",
            "The SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial disposition is not admitted.",
            blocked_fields=["operator_repeatability_disposition"],
        )
    if request.get("operator_confirmation") is not True:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_operator_confirmation_missing",
            "operator_confirmation=true is required before recording a SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial.",
            http_status=409,
            blocked_fields=["operator_confirmation"],
        )

    original_status = _load_operator_status(
        request=request,
        prefix="original",
        request_id=request_id,
        db=db,
    )
    repeat_status = _load_operator_status(
        request=request,
        prefix="repeat",
        request_id=request_id,
        db=db,
    )
    authority_mismatches = _authority_mismatches(original_status, repeat_status)
    if authority_mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_authority_mismatch",
            "The original and repeat SEC EDGAR HTML/iXBRL fact-material downstream status projections are not bound to the same authority chain.",
            http_status=409,
            blocked_fields=authority_mismatches,
        )

    original_operator_status_hash = str(original_status["operator_status_hash"])
    repeat_operator_status_hash = str(repeat_status["operator_status_hash"])
    original_proof_hash = str(original_status["proof_hash"])
    repeat_proof_hash = str(repeat_status["proof_hash"])
    original_coverage_steps = sorted((original_status.get("proof_summary") or {}).get("coverage") or [])
    repeat_coverage_steps = sorted((repeat_status.get("proof_summary") or {}).get("coverage") or [])
    coverage_step_set_comparison = _comparison(original_coverage_steps, repeat_coverage_steps)
    operator_status_hash_comparison = _comparison(original_operator_status_hash, repeat_operator_status_hash)
    proof_hash_comparison = _comparison(original_proof_hash, repeat_proof_hash)
    fact_inventory_hash_comparison = _comparison(
        str(original_status.get("fact_inventory_hash") or ""),
        str(repeat_status.get("fact_inventory_hash") or ""),
    )
    fact_material_authority_hash_comparison = _comparison(
        _authority_hash(original_status),
        _authority_hash(repeat_status),
    )
    if (
        proof_hash_comparison != "match"
        or coverage_step_set_comparison != "match"
        or fact_inventory_hash_comparison != "match"
        or fact_material_authority_hash_comparison != "match"
    ):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_proof_or_authority_mismatch",
            "The fact-material repeatability trial requires matching proof, coverage, fact inventory, and fact-material authority hashes.",
            http_status=409,
            blocked_fields=[
                "proof_hash",
                "coverage",
                "fact_inventory_hash",
                "fact_material_authority_hash",
            ],
        )
    if disposition == "no_regression_observed" and operator_status_hash_comparison != "match":
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_disposition_contradicts_delta",
            "The no-regression disposition requires matching original and repeat operator-status hashes.",
            http_status=409,
            blocked_fields=["operator_repeatability_disposition", "operator_status_hash"],
        )

    authority_pair_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "trial_mode": TRIAL_MODE,
            "authority": {field: original_status.get(field) for field in AUTHORITY_FIELDS},
            "original_operator_status_hash": original_operator_status_hash,
            "repeat_operator_status_hash": repeat_operator_status_hash,
            "proof_hash": original_proof_hash,
            "fact_inventory_hash": original_status.get("fact_inventory_hash"),
            "coverage_step_set": original_coverage_steps,
        }
    )
    trial_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "trial_mode": TRIAL_MODE,
            "operator_decision": OPERATOR_DECISION,
            "operator_repeatability_disposition": disposition,
            "authority_pair_hash": authority_pair_hash,
            "operator_status_hash_comparison": operator_status_hash_comparison,
            "proof_hash_comparison": proof_hash_comparison,
            "coverage_step_set_comparison": coverage_step_set_comparison,
            "fact_inventory_hash_comparison": fact_inventory_hash_comparison,
            "fact_material_authority_hash_comparison": fact_material_authority_hash_comparison,
            "redaction_policy_id": REDACTION_POLICY_ID,
            "baseline_rollback_preserved": True,
            "candidate_a_semantics_preserved": True,
            "candidate_b_default_scope_preserved": True,
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
        original_status=original_status,
        repeat_status=repeat_status,
        operator_status_hash_comparison=operator_status_hash_comparison,
        proof_hash_comparison=proof_hash_comparison,
        coverage_step_set_comparison=coverage_step_set_comparison,
        fact_inventory_hash_comparison=fact_inventory_hash_comparison,
        fact_material_authority_hash_comparison=fact_material_authority_hash_comparison,
    )

    response = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "accepted" if accepted else "blocked",
        "mode": TRIAL_MODE,
        "operator_decision": OPERATOR_DECISION,
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
        "original_operator_status": _status_summary(original_status),
        "repeat_operator_status": _status_summary(repeat_status),
        "authority_bindings": {field: original_status.get(field) for field in AUTHORITY_FIELDS},
        "operator_status_hash_comparison": operator_status_hash_comparison,
        "proof_hash_comparison": proof_hash_comparison,
        "coverage_step_set_comparison": coverage_step_set_comparison,
        "fact_inventory_hash_comparison": fact_inventory_hash_comparison,
        "fact_material_authority_hash_comparison": fact_material_authority_hash_comparison,
        "trial_authority": {
            "source": "server_revalidated_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_projections",
            "original_status_available": original_status.get("status") == "available",
            "repeat_status_available": repeat_status.get("status") == "available",
            "parser_authority_bound": bool(original_status.get("parser_receipt_hash")),
            "fact_authority_bound": bool(original_status.get("fact_authority_receipt_hash")),
            "fact_inventory_bound": bool(original_status.get("fact_inventory_hash")),
            "fact_material_bridge_authority_bound": bool(original_status.get("fact_material_bridge_receipt_hash")),
            "browser_supplied_local_authority_rejected": True,
            "browser_supplied_raw_url_rejected": True,
            "browser_supplied_raw_fact_values_rejected": True,
            "process_execution_admitted": False,
        },
        "operator_visible_repeatability_trial_status": {
            "trial_receipt_recorded": True,
            "trial_accepted": accepted,
            "redacted_trial_receipt_available": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "raw_fact_values_exposed": False,
            "provider_or_connector_secret_exposed": False,
        },
        "fail_closed_behavior": {
            "missing_original_operator_status_blocks_trial": True,
            "missing_repeat_operator_status_blocks_trial": True,
            "stale_original_operator_status_hash_blocks_trial": True,
            "stale_repeat_operator_status_hash_blocks_trial": True,
            "mismatched_source_or_parser_family_blocks_trial": True,
            "mismatched_fact_authority_blocks_trial": True,
            "mismatched_fact_inventory_blocks_trial": True,
            "mismatched_fact_material_bridge_blocks_trial": True,
            "mismatched_material_authority_blocks_trial": True,
            "mismatched_gate_b_or_selection_blocks_trial": True,
            "mismatched_coverage_evidence_blocks_trial": True,
            "non_available_original_or_repeat_status_blocks_trial": True,
            "raw_fact_value_authority_blocks_trial": True,
            "raw_url_or_path_authority_blocks_trial": True,
        },
        "baseline_rollback": {"preserved": True},
        "candidate_a_semantics": {"visual_lane_mode": "candidate_a_page_evidence_v1", "preserved": True},
        "candidate_b_default_scope": {
            "preserved": True,
            "scope": "eligible_effective_pdfs_plus_receipt_bound_selected_classes_only",
        },
        "actual_sec_processing_execution_admitted": False,
        "actual_subprocess_spawn_admitted": False,
        "process_control_admitted": False,
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
        "artifact_bytes_exposed": False,
        "raw_fact_values_exposed": False,
        "fact_value_reconstruction_enabled": False,
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "inspect the recorded SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial receipt",
            "select a separately admitted rendered/status pass before adding operator UI controls",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial would expose raw path, URL, token, fact-value, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _load_operator_status(
    *,
    request: Mapping[str, Any],
    prefix: str,
    request_id: str,
    db: Session,
) -> dict[str, Any]:
    status_request = request.get(f"{prefix}_operator_status_request")
    if not isinstance(status_request, Mapping):
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_{prefix}_status_request_missing",
            "The repeatability trial requires a structured SEC EDGAR HTML/iXBRL fact-material downstream operator-status request.",
            http_status=409,
            blocked_fields=[f"{prefix}_operator_status_request"],
        )
    expected_status_hash = _required_hash(request, f"{prefix}_operator_status_hash")
    try:
        status = (
            layer3_sec_edgar_html_inline_xbrl_fact_material_downstream_status
            .inspect_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status(
                {
                    **dict(status_request),
                    "client_request_id": f"{request_id}:{prefix}-operator-status",
                },
                db,
            )
        )
    except Layer3WorkbenchError as exc:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_{prefix}_status_invalid",
            "The repeatability trial could not revalidate the requested SEC EDGAR HTML/iXBRL fact-material downstream operator status.",
            http_status=exc.http_status,
            blocked_fields=list(exc.blocked_fields),
        )
    if status.get("status") != "available" or status.get("operator_status_state") != "available":
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_{prefix}_status_not_available",
            "The repeatability trial requires available original and repeat fact-material downstream operator-status projections.",
            http_status=409,
            blocked_fields=[f"{prefix}_operator_status_request"],
        )
    if status.get("proof_available") is not True or not status.get("proof_hash"):
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_{prefix}_proof_missing",
            "The repeatability trial requires fact-material downstream proof to be available for both status projections.",
            http_status=409,
            blocked_fields=[f"{prefix}_operator_status_request"],
        )
    if str(status.get("operator_status_hash") or "") != expected_status_hash:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_stale_{prefix}_operator_status_hash",
            "The supplied SEC EDGAR HTML/iXBRL fact-material downstream operator-status hash is stale or contradictory.",
            http_status=409,
            blocked_fields=[f"{prefix}_operator_status_hash"],
        )
    return status


def _authority_mismatches(original_status: Mapping[str, Any], repeat_status: Mapping[str, Any]) -> list[str]:
    return [
        field
        for field in AUTHORITY_FIELDS
        if str(original_status.get(field) or "") != str(repeat_status.get(field) or "")
    ]


def _authority_hash(status: Mapping[str, Any]) -> str:
    return stable_hash({field: status.get(field) for field in AUTHORITY_FIELDS})


def _status_summary(status: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": status.get("status"),
        "operator_status_state": status.get("operator_status_state"),
        "operator_status_hash": status.get("operator_status_hash"),
        "operator_status_projection_ref": status.get("operator_status_projection_ref"),
        "proof_hash": status.get("proof_hash"),
        "dataset_version_id": status.get("dataset_version_id"),
        "dataset_version_hash": status.get("dataset_version_hash"),
        "source_family": status.get("source_family"),
        "parser_family": status.get("parser_family"),
        "typed_content_contract_id": status.get("typed_content_contract_id"),
        "parser_receipt_hash": status.get("parser_receipt_hash"),
        "connector_receipt_hash": status.get("connector_receipt_hash"),
        "live_source_artifact_receipt_hash": status.get("live_source_artifact_receipt_hash"),
        "source_artifact_receipt_hash": status.get("source_artifact_receipt_hash"),
        "content_sha256": status.get("content_sha256"),
        "primary_document_hash": status.get("primary_document_hash"),
        "content_order_hash": status.get("content_order_hash"),
        "inline_xbrl_marker_inventory_hash": status.get("inline_xbrl_marker_inventory_hash"),
        "fact_authority_receipt_hash": status.get("fact_authority_receipt_hash"),
        "fact_inventory_hash": status.get("fact_inventory_hash"),
        "diagnostics_hash": status.get("diagnostics_hash"),
        "materialization_receipt_hash": status.get("materialization_receipt_hash"),
        "fact_material_bridge_receipt_hash": status.get("fact_material_bridge_receipt_hash"),
        "material_bridge_receipt_hash": status.get("material_bridge_receipt_hash"),
        "material_preview_hash": status.get("material_preview_hash"),
        "gate_b_decision_manifest_id": status.get("gate_b_decision_manifest_id"),
        "session_id": status.get("session_id"),
        "selection_manifest_id": status.get("selection_manifest_id"),
        "material_snapshot_payload_hash": status.get("material_snapshot_payload_hash"),
        "coverage_evidence_hash": status.get("coverage_evidence_hash"),
        "negative_invariants_hash": status.get("negative_invariants_hash"),
        "raw_local_path_rendered": status.get("raw_local_path_rendered"),
        "raw_url_rendered": status.get("raw_url_rendered"),
        "artifact_bytes_rendered": status.get("artifact_bytes_rendered"),
        "raw_fact_values_rendered": status.get("raw_fact_values_rendered"),
    }


def _write_trial_receipt(
    *,
    receipt_id: str,
    receipt_hash: str,
    request_id: str,
    disposition: str,
    accepted: bool,
    authority_pair_hash: str,
    original_status: Mapping[str, Any],
    repeat_status: Mapping[str, Any],
    operator_status_hash_comparison: str,
    proof_hash_comparison: str,
    coverage_step_set_comparison: str,
    fact_inventory_hash_comparison: str,
    fact_material_authority_hash_comparison: str,
) -> tuple[str, bool]:
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "trial_mode": TRIAL_MODE,
        "operator_decision": OPERATOR_DECISION,
        "operator_repeatability_trial_state": TRIAL_ACCEPTED_STATE if accepted else TRIAL_BLOCKED_STATE,
        "operator_repeatability_disposition": disposition,
        "request_id": request_id,
        "trial_receipt_id": receipt_id,
        "trial_receipt_hash": receipt_hash,
        "authority_pair_hash": authority_pair_hash,
        "original_operator_status": _status_summary(original_status),
        "repeat_operator_status": _status_summary(repeat_status),
        "authority_bindings": {field: original_status.get(field) for field in AUTHORITY_FIELDS},
        "operator_status_hash_comparison": operator_status_hash_comparison,
        "proof_hash_comparison": proof_hash_comparison,
        "coverage_step_set_comparison": coverage_step_set_comparison,
        "fact_inventory_hash_comparison": fact_inventory_hash_comparison,
        "fact_material_authority_hash_comparison": fact_material_authority_hash_comparison,
        "append_only_repeatability_trial_receipt": True,
        "exclusive_trial_per_original_repeat_authority_pair": True,
        "baseline_rollback_preserved": True,
        "candidate_a_semantics_preserved": True,
        "candidate_b_default_scope_preserved": True,
        "actual_sec_processing_execution_admitted": False,
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
        "raw_fact_values_exposed": False,
        "fact_value_reconstruction_enabled": False,
        "redaction_policy_id": REDACTION_POLICY_ID,
        "recorded_at": _server_time(),
    }
    target = _receipt_root() / f"{receipt_id}.json"
    if target.exists():
        existing = _read_receipt(target)
        if existing.get("trial_receipt_hash") != receipt_hash:
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_receipt_conflict",
                "A fact-material downstream repeatability trial already exists for this original/repeat authority pair.",
                http_status=409,
            )
        return f"{TRIAL_RECEIPT_PREFIX}:{receipt_hash[:24]}", True
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_receipt_write_failed",
            "SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial receipt could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    return f"{TRIAL_RECEIPT_PREFIX}:{receipt_hash[:24]}", False


def _receipt_root() -> Path:
    return Path(str(settings.storage_dir or "")).resolve() / TRIAL_RECEIPT_DIR


def _read_receipt(path: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_receipt_invalid",
            "SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial receipts must be JSON objects.",
            http_status=409,
        )
    return receipt


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial does not admit caller paths, URLs, bytes, credentials, raw fact values, commands, process state, connector, model, browser, source-expansion, or frontend authority.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_unknown_field",
            "SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    return find_forbidden_ref_paths(value, forbidden_keys=FORBIDDEN_REQUEST_FIELDS, prefix=prefix)


def _comparison(original: Any, repeat: Any) -> str:
    return "match" if original == repeat else "delta"


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_required_field_missing",
            "A required SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_sha256(value):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_hash_invalid",
            "SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial hash fields must be SHA-256 hex strings.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL fact-material downstream repeatability trial request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_default_scope_changed": False,
        "live_sec_network_fetch_admitted_by_trial": False,
        "sec_edgar_parser_expansion_admitted": False,
        "html_inline_xbrl_reparse_or_rematerialization_admitted": False,
        "fact_value_reconstruction_enabled": False,
        "xml_xbrl_fact_authority_admitted": False,
        "sec_companyfacts_api_runtime_enabled": False,
        "taxonomy_network_resolution_enabled": False,
        "financial_statement_semantics_admitted": False,
        "fact_to_statement_classification_enabled": False,
        "raw_sec_filing_url_authority_admitted": False,
        "source_expansion_enabled": False,
        "runtime_db_or_storage_expansion_enabled": False,
        "process_execution_enabled": False,
        "process_control_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "auth_security_expansion_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "browser_storage_authority_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "raw_fact_values_exposed": False,
    }


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        return _is_forbidden_ref(value)
    return False


def _is_forbidden_ref(value: str) -> bool:
    text = value.strip().lower()
    return (
        contains_forbidden_ref(value)
        or "aps-target-artifacts/" in text
    )


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _blocked(
    code: str,
    message: str,
    *,
    http_status: int = 400,
    blocked_fields: list[str] | None = None,
) -> None:
    raise Layer3WorkbenchError(
        code,
        message,
        status="blocked" if http_status < 409 else "conflict",
        http_status=http_status,
        blocked_fields=blocked_fields or [],
    )


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
