from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services import layer3_sec_edgar_authority_envelope, layer3_workbench
from app.services.layer3_gate_b_state import (
    candidate_decision_manifest,
    gate_b_decision_manifest_id as compute_gate_b_decision_manifest_id,
    material_candidate_basis_from_decision,
    material_candidate_basis_from_preview,
    material_preview_hash,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError

SCHEMA_ID = "layer3.sec_edgar_text_table_material_authority_bridge.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_text_table_material_authority_bridge_request.v1"
SCHEMA_VERSION = 1
BRIDGE_MODE = "sec_edgar_text_table_authority_envelope_to_layer3_material_authority_v1"
READY_STATE = "sec_edgar_text_table_layer3_material_authority_bridge_ready"
BLOCKED_STATE = "sec_edgar_text_table_layer3_material_authority_bridge_blocked"
SOURCE_FAMILY = layer3_sec_edgar_authority_envelope.SOURCE_FAMILY
PARSER_FAMILY = layer3_sec_edgar_authority_envelope.PARSER_FAMILY
TYPED_CONTENT_CONTRACT_ID = layer3_sec_edgar_authority_envelope.TYPED_CONTENT_CONTRACT_ID
MATERIAL_PREVIEW_SCHEMA_ID = "layer3.material_preview_request.v1"
GATE_B_DECISION_SCHEMA_ID = "layer3.gate_b_decision_request.v1"
SOURCE_CLASS = "dataset_version"
SOURCE_CANDIDATE_PREFIX = "src-dataset_version-"
BRIDGE_RECEIPT_PREFIX = "sec-edgar-text-table-l3-material-bridge"
AUTHORITY_HASH_VERSION = "sec_edgar_text_table_layer3_material_bridge_hash_v1"

_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "bridge_mode",
    "dataset_version_id",
    "authority_envelope_hash",
    "authority_envelope_ref",
    "expected_materialization_receipt_hash",
    "expected_material_preview_hash",
    "operator_confirmed",
    "rollback_confirmed",
    "actor",
}
_FORBIDDEN_INPUT_KEYS = {
    "path",
    "raw_path",
    "local_path",
    "file_path",
    "directory",
    "url",
    "raw_url",
    "source_url",
    "filing_url",
    "provider_url",
    "connector_url",
    "command",
    "args",
    "provider_credentials",
    "connector_credentials",
    "browser_storage",
    "source_upload",
    "source_expansion",
    "runtime_db_write",
    "rag_vector_index",
    "full_mockup_activation",
}
_REDACT_KEYS = {
    "source_artifact_key",
    "raw_storage_ref",
    "diagnostics_ref",
    "storage_ref",
    "blob_ref",
    "content_units_ref",
    "normalized_text_ref",
    "download_exchange_ref",
    "discovery_ref",
    "selection_ref",
    "provider_url",
    "connector_url",
    "public_url",
    "signed_url",
}
_RAW_URL_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://")
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def prepare_sec_edgar_text_table_material_authority_bridge(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    bridge_mode = str(request.get("bridge_mode") or BRIDGE_MODE).strip()
    if bridge_mode != BRIDGE_MODE:
        raise Layer3WorkbenchError(
            "sec_edgar_text_table_material_bridge_mode_not_admitted",
            "SEC EDGAR text-table material authority bridge requires the admitted bridge mode.",
            status="blocked",
            http_status=400,
            blocked_fields=["bridge_mode"],
            details={"expected_bridge_mode": BRIDGE_MODE, "received_bridge_mode": bridge_mode},
        )

    dataset_version_id = _required(request, "dataset_version_id")
    authority_envelope_hash = _required(request, "authority_envelope_hash")
    rollback_confirmed = request.get("rollback_confirmed") is True
    operator_confirmed = request.get("operator_confirmed") is True
    if not rollback_confirmed or not operator_confirmed:
        return _blocked_response(
            request_id=request_id,
            dataset_version_id=dataset_version_id,
            authority_envelope_hash=authority_envelope_hash,
            reasons=[
                *([] if rollback_confirmed else [_reason("missing_rollback_confirmation")]),
                *([] if operator_confirmed else [_reason("missing_operator_confirmation")]),
            ],
        )

    envelope = layer3_sec_edgar_authority_envelope.validate_sec_edgar_text_table_authority_envelope(
        {
            "dataset_version_id": dataset_version_id,
            "expected_authority_envelope_hash": authority_envelope_hash,
            "expected_parser_family": PARSER_FAMILY,
            "expected_source_family": SOURCE_FAMILY,
            "expected_typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "rollback_confirmed": True,
            "operator_confirmed": True,
        },
        db,
    )
    if envelope.get("authority_envelope_state") != layer3_sec_edgar_authority_envelope.READY_STATE:
        return _blocked_response(
            request_id=request_id,
            dataset_version_id=dataset_version_id,
            authority_envelope_hash=authority_envelope_hash,
            authority_envelope=envelope,
            reasons=[
                _reason("missing_ready_envelope"),
                *list((envelope.get("status_projection") or {}).get("blocked_reasons") or []),
            ],
        )
    expected_authority_ref = str(request.get("authority_envelope_ref") or "").strip()
    if expected_authority_ref and expected_authority_ref != str(envelope.get("authority_envelope_ref") or ""):
        return _blocked_response(
            request_id=request_id,
            dataset_version_id=dataset_version_id,
            authority_envelope_hash=authority_envelope_hash,
            authority_envelope=envelope,
            reasons=[_reason("authority_envelope_ref_mismatch")],
        )

    materialization_hash = str(envelope.get("materialization_receipt_hash") or "")
    expected_materialization_hash = str(request.get("expected_materialization_receipt_hash") or "").strip()
    if expected_materialization_hash and expected_materialization_hash != materialization_hash:
        return _blocked_response(
            request_id=request_id,
            dataset_version_id=dataset_version_id,
            authority_envelope_hash=authority_envelope_hash,
            authority_envelope=envelope,
            reasons=[
                _reason(
                    "materialization_receipt_hash_mismatch",
                    expected_materialization_receipt_hash=expected_materialization_hash,
                    received_materialization_receipt_hash=materialization_hash,
                )
            ],
        )

    source_candidate_id = f"{SOURCE_CANDIDATE_PREFIX}sec-edgar-{_short_hash(dataset_version_id)}"
    actor = str(request.get("actor") or "operator").strip() or "operator"
    material_preview_request_basis = {
        "schema_id": MATERIAL_PREVIEW_SCHEMA_ID,
        "schema_version": 1,
        "client_request_id": f"{request_id}:material-preview",
        "source_candidate_ids": [source_candidate_id],
        "dataset_version_ids": [dataset_version_id],
        "query_basis": {
            "terms": ["sec_edgar_text_table_authority_envelope"],
            "filters": {"dataset_version_ids": [dataset_version_id]},
        },
        "actor": actor,
    }
    raw_preview = layer3_workbench.material_preview(material_preview_request_basis, db)
    raw_candidates = raw_preview.get("material_candidates") if isinstance(raw_preview.get("material_candidates"), list) else []
    if len(raw_candidates) != 1:
        return _blocked_response(
            request_id=request_id,
            dataset_version_id=dataset_version_id,
            authority_envelope_hash=authority_envelope_hash,
            authority_envelope=envelope,
            reasons=[_reason("material_preview_candidate_count_mismatch", candidate_count=len(raw_candidates))],
        )

    material_candidate = _redacted_material_candidate(raw_candidates[0], authority_envelope=envelope)
    candidate_basis = material_candidate_basis_from_preview(material_candidate)
    bridged_material_preview_hash = material_preview_hash([candidate_basis])
    expected_material_preview_hash = str(request.get("expected_material_preview_hash") or "").strip()
    if expected_material_preview_hash and expected_material_preview_hash != bridged_material_preview_hash:
        return _blocked_response(
            request_id=request_id,
            dataset_version_id=dataset_version_id,
            authority_envelope_hash=authority_envelope_hash,
            authority_envelope=envelope,
            reasons=[
                _reason(
                    "material_preview_hash_mismatch",
                    expected_material_preview_hash=expected_material_preview_hash,
                    received_material_preview_hash=bridged_material_preview_hash,
                )
            ],
        )

    gate_b_decision_basis = _gate_b_decision_basis(material_candidate)
    gate_b_material_basis = material_candidate_basis_from_decision(
        candidate_id=str(material_candidate["candidate_id"]),
        source_class=SOURCE_CLASS,
        decision_basis=gate_b_decision_basis,
    )
    if gate_b_material_basis != candidate_basis:
        return _blocked_response(
            request_id=request_id,
            dataset_version_id=dataset_version_id,
            authority_envelope_hash=authority_envelope_hash,
            authority_envelope=envelope,
            reasons=[_reason("gate_b_decision_basis_mismatch")],
        )

    gate_b_decision_item = {
        "candidate_id": material_candidate["candidate_id"],
        "source_class": SOURCE_CLASS,
        "decision": "approved",
        "operator_reason": "",
        "decision_basis": gate_b_decision_basis,
        "material_preview_basis": gate_b_material_basis,
        "source_identity": gate_b_decision_basis["source_identity"],
        "source_provenance": gate_b_decision_basis["source_provenance"],
        "payload": gate_b_decision_basis["payload"],
        "load_summary": gate_b_decision_basis["load_summary"],
    }
    gate_b_decision_manifest = candidate_decision_manifest([gate_b_decision_item])
    gate_b_decision_manifest_id = compute_gate_b_decision_manifest_id(gate_b_decision_manifest)
    gate_b_decision_payload = {
        "schema_id": GATE_B_DECISION_SCHEMA_ID,
        "schema_version": 1,
        "client_request_id": f"{request_id}:gate-b",
        "preflight_id": f"sec-edgar-text-table-envelope-{_short_hash(authority_envelope_hash)}",
        "source_set_id": f"sec-edgar-text-table-material-{_short_hash(dataset_version_id)}",
        "material_preview_id": raw_preview["material_preview_id"],
        "material_preview_hash": bridged_material_preview_hash,
        "candidate_decisions": [
            {
                "candidate_id": material_candidate["candidate_id"],
                "decision": "approved",
                "operator_reason": "",
                "decision_basis": gate_b_decision_basis,
            }
        ],
        "commit_reason": "sec_edgar_text_table_authority_envelope_material_bridge",
        "actor": actor,
    }

    bridge_receipt_hash = stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "bridge_mode": BRIDGE_MODE,
            "dataset_version_id": dataset_version_id,
            "dataset_version_hash": envelope.get("dataset_version_hash"),
            "materialization_receipt_hash": materialization_hash,
            "authority_envelope_hash": authority_envelope_hash,
            "material_preview_hash": bridged_material_preview_hash,
            "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
        }
    )
    bridge_receipt_id = f"{BRIDGE_RECEIPT_PREFIX}-{bridge_receipt_hash[:24]}"
    response = {
        **_base_response(request_id=request_id, status="ready"),
        "mode": BRIDGE_MODE,
        "bridge_state": READY_STATE,
        "bridge_receipt_id": bridge_receipt_id,
        "bridge_receipt_ref": f"{BRIDGE_RECEIPT_PREFIX}:{bridge_receipt_hash[:24]}",
        "bridge_receipt_hash": bridge_receipt_hash,
        "dataset_version_id": dataset_version_id,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "authority_envelope_hash": authority_envelope_hash,
        "authority_envelope_ref": envelope.get("authority_envelope_ref"),
        "materialization_receipt_hash": materialization_hash,
        "material_preview_request_basis": material_preview_request_basis,
        "material_preview_id": raw_preview["material_preview_id"],
        "material_preview_hash": bridged_material_preview_hash,
        "raw_material_preview_hash_exposed": False,
        "material_candidate": material_candidate,
        "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
        "gate_b_decision_payload": gate_b_decision_payload,
        "authority_hashes": {
            "dataset_version_hash": str(envelope.get("dataset_version_hash") or ""),
            "materialization_receipt_hash": materialization_hash,
            "authority_envelope_hash": authority_envelope_hash,
            "material_preview_hash": bridged_material_preview_hash,
            "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
            "bridge_receipt_hash": bridge_receipt_hash,
        },
        "provenance_summary": envelope.get("provenance_summary") or {},
        "compatibility": {
            "material_preview_schema_id": MATERIAL_PREVIEW_SCHEMA_ID,
            "gate_b_decision_schema_id": GATE_B_DECISION_SCHEMA_ID,
            "source_class": SOURCE_CLASS,
            "source_candidate_prefix": SOURCE_CANDIDATE_PREFIX,
            "existing_layer3_dataset_version_material_preview_without_source_class_widening": True,
            "existing_gate_b_material_preview_hash_and_decision_basis_validation": True,
        },
        "status_projection": {
            "ready": True,
            "blocked_reasons": [],
            "next_allowed_actions": [
                "submit_sec_edgar_material_bridge_gate_b_decision_payload",
                "select_sec_edgar_text_table_downstream_layer3_proof",
            ],
        },
        "negative_invariants": _negative_invariants(),
    }
    if _contains_forbidden_output_ref(response):
        return _blocked_response(
            request_id=request_id,
            dataset_version_id=dataset_version_id,
            authority_envelope_hash=authority_envelope_hash,
            authority_envelope=envelope,
            reasons=[_reason("raw_path_or_url_authority")],
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    _reject_forbidden_input_authority(fields)
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    unknown = sorted(set(request) - _ALLOWED_FIELDS)
    if unknown:
        raise Layer3WorkbenchError(
            "sec_edgar_text_table_material_bridge_unknown_field",
            "SEC EDGAR text-table material bridge fields are intentionally scoped.",
            status="blocked",
            http_status=400,
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        raise Layer3WorkbenchError(
            "sec_edgar_text_table_material_bridge_schema_not_admitted",
            "SEC EDGAR text-table material bridge requires the admitted request schema.",
            status="blocked",
            http_status=400,
            blocked_fields=["schema_id"],
            details={"expected_schema_id": REQUEST_SCHEMA_ID, "received_schema_id": schema_id},
        )
    return request


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise Layer3WorkbenchError(
            f"sec_edgar_text_table_material_bridge_{key}_missing",
            f"SEC EDGAR text-table material bridge requires {key}.",
            status="blocked",
            http_status=400,
            blocked_fields=[key],
        )
    return value


def _blocked_response(
    *,
    request_id: str,
    dataset_version_id: str,
    authority_envelope_hash: str,
    reasons: list[dict[str, Any]],
    authority_envelope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        **_base_response(request_id=request_id, status="blocked"),
        "mode": BRIDGE_MODE,
        "bridge_state": BLOCKED_STATE,
        "dataset_version_id": dataset_version_id,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "authority_envelope_hash": authority_envelope_hash,
        "authority_envelope_state": (
            authority_envelope.get("authority_envelope_state")
            if isinstance(authority_envelope, Mapping)
            else None
        ),
        "material_preview_request_basis": None,
        "material_preview_hash": None,
        "gate_b_decision_manifest_id": None,
        "status_projection": {
            "ready": False,
            "blocked_reasons": reasons,
            "next_allowed_actions": ["refresh_sec_edgar_text_table_authority_envelope"],
        },
        "negative_invariants": _negative_invariants(),
    }


def _base_response(*, request_id: str, status: str) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }


def _reason(reason: str, **details: Any) -> dict[str, Any]:
    return {"reason": reason, **details}


def _redacted_material_candidate(
    candidate: Mapping[str, Any],
    *,
    authority_envelope: Mapping[str, Any],
) -> dict[str, Any]:
    source_identity = _redact_value(candidate.get("source_identity"))
    source_provenance = _redact_value(candidate.get("source_provenance"))
    source_trace = _redact_value(candidate.get("source_trace"))
    source_identity = source_identity if isinstance(source_identity, dict) else {}
    source_provenance = source_provenance if isinstance(source_provenance, dict) else {}
    source_trace = source_trace if isinstance(source_trace, dict) else {}
    source_provenance["authority_envelope_ref"] = authority_envelope.get("authority_envelope_ref")
    source_provenance["authority_envelope_hash"] = authority_envelope.get("authority_envelope_hash")
    source_provenance["materialization_receipt_hash"] = authority_envelope.get("materialization_receipt_hash")
    source_provenance["redaction"] = {
        "raw_source_artifact_key_exposed": False,
        "raw_storage_ref_exposed": False,
        "diagnostics_ref_exposed": False,
        "raw_url_exposed": False,
    }
    source_trace["aps_trace_refs"] = {
        "source_artifact_key_redacted": True,
        "raw_storage_ref_redacted": True,
        "diagnostics_ref_redacted": True,
        "target_id": (candidate.get("source_trace") or {}).get("aps_trace_refs", {}).get("target_id")
        if isinstance(candidate.get("source_trace"), Mapping)
        else None,
        "accession_number": (candidate.get("source_trace") or {}).get("aps_trace_refs", {}).get("accession_number")
        if isinstance(candidate.get("source_trace"), Mapping)
        else None,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
    }
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "source_label": "SEC EDGAR Text Table Dataset Version",
        "source_class": SOURCE_CLASS,
        "source_ref": str(candidate.get("source_ref") or ""),
        "owner_service_source_shape": SOURCE_CLASS,
        "planning_shape_family": "mixed_narrative_table",
        "source_family": SOURCE_FAMILY,
        "source_family_label": str(candidate.get("source_family_label") or "SEC/EDGAR text table"),
        "source_admission_state": str(candidate.get("source_admission_state") or "admitted_materialized_dataset_version"),
        "source_family_scope": str(candidate.get("source_family_scope") or ""),
        "source_trace": source_trace,
        "query_basis": BRIDGE_MODE,
        "validation_status": str(candidate.get("validation_status") or "valid"),
        "duplicate_status": str(candidate.get("duplicate_status") or "unique"),
        "size_or_unit_count": int(candidate.get("size_or_unit_count") or 0),
        "preview_payload_ref": None,
        "provenance_ref": str(authority_envelope.get("authority_envelope_ref") or ""),
        "source_identity": source_identity,
        "source_provenance": source_provenance,
        "payload": {
            "dataset_version_id": (candidate.get("payload") or {}).get("dataset_version_id")
            if isinstance(candidate.get("payload"), Mapping)
            else None,
            "source_family": SOURCE_FAMILY,
            "parser_family": PARSER_FAMILY,
            "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
            "authority_envelope_hash": authority_envelope.get("authority_envelope_hash"),
            "materialization_receipt_hash": authority_envelope.get("materialization_receipt_hash"),
        },
        "load_summary": {
            "loaded_records": int((candidate.get("load_summary") or {}).get("loaded_records") or 0)
            if isinstance(candidate.get("load_summary"), Mapping)
            else 0,
            "failed_records": 0,
            "preview_material": True,
            "storage_available": bool((candidate.get("load_summary") or {}).get("storage_available"))
            if isinstance(candidate.get("load_summary"), Mapping)
            else False,
            "sec_edgar_text_table_material_authority_bridge": True,
            "raw_refs_redacted": True,
        },
        "current_decision_state": "candidate",
    }


def _gate_b_decision_basis(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_ref": str(candidate.get("source_ref") or ""),
        "query_basis": str(candidate.get("query_basis") or BRIDGE_MODE),
        "provenance_ref": str(candidate.get("provenance_ref") or ""),
        "source_identity": dict(candidate.get("source_identity") or {}),
        "source_provenance": dict(candidate.get("source_provenance") or {}),
        "payload": dict(candidate.get("payload") or {}),
        "load_summary": dict(candidate.get("load_summary") or {}),
    }


def _redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _REDACT_KEYS:
                result[f"{key_text}_redacted"] = _redacted_ref(nested)
            else:
                result[key_text] = _redact_value(nested)
        return result
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        text = value.strip()
        if _RAW_URL_RE.search(text) or _LOCAL_PATH_RE.search(text) or "aps-target-artifacts/" in text:
            return _redacted_ref(text)
        return value
    return value


def _redacted_ref(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    return {
        "present": bool(text),
        "redacted": True,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None,
    }


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        text = value.strip()
        return bool(_LOCAL_PATH_RE.search(text) or text.startswith("http://") or text.startswith("https://"))
    return False


def _reject_forbidden_input_authority(value: Any, path: str = "") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in _FORBIDDEN_INPUT_KEYS:
                raise Layer3WorkbenchError(
                    "sec_edgar_text_table_material_bridge_forbidden_input_authority",
                    "SEC EDGAR text-table material bridge rejects caller-supplied raw paths, URLs, commands, credentials, connectors, providers, browser authority, and source expansion fields.",
                    status="blocked",
                    http_status=400,
                    blocked_fields=[child_path],
                )
            _reject_forbidden_input_authority(nested, child_path)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_forbidden_input_authority(nested, f"{path}[{index}]")
    elif isinstance(value, str) and (_LOCAL_PATH_RE.search(value) or value.startswith("http://") or value.startswith("https://")):
        raise Layer3WorkbenchError(
            "sec_edgar_text_table_material_bridge_forbidden_input_ref",
            "SEC EDGAR text-table material bridge rejects caller-supplied raw paths and URLs.",
            status="blocked",
            http_status=400,
            blocked_fields=[path or "request_body"],
        )


def _negative_invariants() -> dict[str, bool]:
    return {
        "direct_unbridged_sec_edgar_dataset_version_material_authority_admitted": False,
        "sec_edgar_network_fetch_admitted": False,
        "sec_edgar_parser_expansion_admitted": False,
        "xml_html_inline_xbrl_admitted": False,
        "raw_sec_filing_url_authority_admitted": False,
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
    }


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
