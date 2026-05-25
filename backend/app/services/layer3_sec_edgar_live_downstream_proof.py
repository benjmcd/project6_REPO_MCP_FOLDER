from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.services import (
    layer3_sec_edgar_downstream_proof,
    layer3_sec_edgar_live_material_bridge,
    layer3_sec_edgar_live_source_artifact,
    layer3_sec_edgar_source_acquisition,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_text_table_live_source_artifact_downstream_proof.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_text_table_live_source_artifact_downstream_proof_request.v1"
SCHEMA_VERSION = 1
PROOF_MODE = "sec_edgar_text_table_live_source_artifact_downstream_layer3_e2e_proof_v1"
OPERATOR_DECISION = "record_sec_edgar_text_table_live_source_artifact_downstream_layer3_e2e_proof"
PROOF_STATE = "sec_edgar_text_table_live_source_artifact_downstream_layer3_e2e_proven"
PROOF_RECEIPT_PREFIX = "sec-edgar-text-table-live-source-artifact-downstream-proof"

SOURCE_FAMILY = layer3_sec_edgar_downstream_proof.SOURCE_FAMILY
PARSER_FAMILY = layer3_sec_edgar_downstream_proof.PARSER_FAMILY
TYPED_CONTENT_CONTRACT_ID = layer3_sec_edgar_downstream_proof.TYPED_CONTENT_CONTRACT_ID
LIVE_BRIDGE_MODE = layer3_sec_edgar_live_material_bridge.BRIDGE_MODE
LIVE_BRIDGE_READY_STATE = layer3_sec_edgar_live_material_bridge.READY_STATE
EXISTING_DOWNSTREAM_PROOF_MODE = layer3_sec_edgar_downstream_proof.PROOF_MODE
EXISTING_DOWNSTREAM_OPERATOR_DECISION = layer3_sec_edgar_downstream_proof.OPERATOR_DECISION

LIVE_COVERAGE = frozenset(
    {
        "live_source_artifact_acquisition",
        "source_acquisition_authority",
        "live_material_authority_bridge",
    }
)
REQUIRED_COVERAGE = layer3_sec_edgar_downstream_proof.REQUIRED_COVERAGE | LIVE_COVERAGE
FORBIDDEN_REQUEST_FIELDS = layer3_sec_edgar_downstream_proof.FORBIDDEN_REQUEST_FIELDS | {
    "live_sec_url",
    "sec_url",
    "retained_artifact_path",
    "source_artifact_path",
}
ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "proof_mode",
    "operator_decision",
    "live_source_artifact_receipt_id",
    "live_source_artifact_receipt_hash",
    "source_acquisition_receipt_id",
    "source_acquisition_receipt_hash",
    "dataset_version_id",
    "authority_envelope_hash",
    "live_source_artifact_material_bridge_receipt_id",
    "live_source_artifact_material_bridge_receipt_hash",
    "material_bridge_receipt_hash",
    "material_preview_hash",
    "gate_b_decision_manifest_id",
    "session_id",
    "selection_manifest_id",
    "material_snapshot_payload_hash",
    "coverage_evidence",
    "operator_confirmation",
    "actor",
}
PROOF_HASH_KEYS = (
    "schema_id",
    "schema_version",
    "mode",
    "dataset_version_id",
    "live_source_artifact_receipt_hash",
    "source_acquisition_receipt_hash",
    "authority_envelope_hash",
    "materialization_receipt_hash",
    "live_source_artifact_material_bridge_receipt_hash",
    "material_bridge_receipt_hash",
    "material_preview_hash",
    "gate_b_decision_manifest_id",
    "session_id",
    "selection_manifest_id",
    "material_snapshot_payload_hash",
    "downstream_proof_hash",
    "coverage_evidence_hash",
    "negative_invariants_hash",
    "operator_confirmation",
)

_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def record_sec_edgar_text_table_live_source_artifact_downstream_layer3_proof(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "proof_mode", PROOF_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    if request.get("operator_confirmation") is not True:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_operator_confirmation_required",
            "operator_confirmation=true is required before recording SEC EDGAR live source-artifact downstream proof.",
            blocked_fields=["operator_confirmation"],
        )

    live_receipt_id = _required(request, "live_source_artifact_receipt_id")
    live_receipt_hash = _required_hash(request, "live_source_artifact_receipt_hash")
    source_acquisition_receipt_id = _required(request, "source_acquisition_receipt_id")
    source_acquisition_receipt_hash = _required_hash(request, "source_acquisition_receipt_hash")
    dataset_version_id = _required(request, "dataset_version_id")
    authority_envelope_hash = _required_hash(request, "authority_envelope_hash")
    live_bridge_receipt_id = _required(request, "live_source_artifact_material_bridge_receipt_id")
    live_bridge_receipt_hash = _required_hash(request, "live_source_artifact_material_bridge_receipt_hash")
    material_bridge_receipt_hash = _required_hash(request, "material_bridge_receipt_hash")
    material_preview_hash = _required_hash(request, "material_preview_hash")
    gate_b_decision_manifest_id = _required(request, "gate_b_decision_manifest_id")
    session_id = _required(request, "session_id")
    selection_manifest_id = _required(request, "selection_manifest_id")
    material_snapshot_payload_hash = _required_hash(request, "material_snapshot_payload_hash")

    live_receipt = layer3_sec_edgar_live_source_artifact.read_sec_edgar_text_table_live_source_artifact_receipt(
        live_receipt_id,
        expected_live_source_artifact_receipt_hash=live_receipt_hash,
    )
    source_acquisition_receipt = layer3_sec_edgar_source_acquisition.read_sec_edgar_text_table_source_acquisition_receipt(
        source_acquisition_receipt_id,
        expected_source_acquisition_receipt_hash=source_acquisition_receipt_hash,
    )
    live_bridge_receipt = (
        layer3_sec_edgar_live_material_bridge.read_sec_edgar_text_table_live_source_artifact_material_authority_bridge_receipt(
            live_bridge_receipt_id,
            expected_bridge_receipt_hash=live_bridge_receipt_hash,
            live_source_artifact_receipt_hash=live_receipt_hash,
            source_acquisition_receipt_hash=source_acquisition_receipt_hash,
        )
    )

    live_bridge = _validate_live_bridge_receipt(
        live_bridge_receipt,
        live_receipt=live_receipt,
        source_acquisition_receipt=source_acquisition_receipt,
        dataset_version_id=dataset_version_id,
        authority_envelope_hash=authority_envelope_hash,
        live_bridge_receipt_hash=live_bridge_receipt_hash,
        material_bridge_receipt_hash=material_bridge_receipt_hash,
        material_preview_hash=material_preview_hash,
        gate_b_decision_manifest_id=gate_b_decision_manifest_id,
    )
    downstream_proof = layer3_sec_edgar_downstream_proof.record_sec_edgar_text_table_downstream_layer3_proof(
        {
            "client_request_id": f"{request_id}:underlying-downstream-proof",
            "proof_mode": EXISTING_DOWNSTREAM_PROOF_MODE,
            "operator_decision": EXISTING_DOWNSTREAM_OPERATOR_DECISION,
            "dataset_version_id": dataset_version_id,
            "authority_envelope_hash": authority_envelope_hash,
            "bridge_receipt_hash": material_bridge_receipt_hash,
            "material_preview_hash": material_preview_hash,
            "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
            "session_id": session_id,
            "selection_manifest_id": selection_manifest_id,
            "material_snapshot_payload_hash": material_snapshot_payload_hash,
            "coverage_evidence": request.get("coverage_evidence"),
            "operator_confirmation": True,
        },
        db,
    )
    coverage = _validate_live_coverage(
        request.get("coverage_evidence"),
        live_source_artifact_receipt_hash=live_receipt_hash,
        live_source_artifact_receipt_id=live_receipt_id,
        source_acquisition_receipt_hash=source_acquisition_receipt_hash,
        source_acquisition_receipt_id=source_acquisition_receipt_id,
        live_bridge_receipt_hash=live_bridge_receipt_hash,
        live_bridge_receipt_id=live_bridge_receipt_id,
        material_bridge_receipt_hash=material_bridge_receipt_hash,
        material_preview_hash=material_preview_hash,
        gate_b_decision_manifest_id=gate_b_decision_manifest_id,
        downstream_proof=downstream_proof,
    )

    negative_invariants = _negative_invariants()
    coverage_hash = stable_hash(coverage)
    negative_invariants_hash = stable_hash(negative_invariants)
    proof_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROOF_MODE,
        "dataset_version_id": dataset_version_id,
        "live_source_artifact_receipt_hash": live_receipt_hash,
        "source_acquisition_receipt_hash": source_acquisition_receipt_hash,
        "authority_envelope_hash": authority_envelope_hash,
        "materialization_receipt_hash": live_bridge["materialization_receipt_hash"],
        "live_source_artifact_material_bridge_receipt_hash": live_bridge_receipt_hash,
        "material_bridge_receipt_hash": material_bridge_receipt_hash,
        "material_preview_hash": material_preview_hash,
        "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
        "session_id": session_id,
        "selection_manifest_id": selection_manifest_id,
        "material_snapshot_payload_hash": material_snapshot_payload_hash,
        "downstream_proof_hash": downstream_proof["proof_hash"],
        "coverage_evidence_hash": coverage_hash,
        "negative_invariants_hash": negative_invariants_hash,
        "operator_confirmation": True,
    }
    proof_hash = stable_hash({key: proof_input[key] for key in PROOF_HASH_KEYS})
    proof_receipt_id = f"{PROOF_RECEIPT_PREFIX}-{proof_hash[:24]}"
    proof = {
        **proof_input,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "proven",
        "proof_state": PROOF_STATE,
        "proof_hash": proof_hash,
        "proof_receipt_id": proof_receipt_id,
        "proof_receipt_ref": f"{PROOF_RECEIPT_PREFIX}:{proof_hash[:24]}",
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "live_source_artifact_receipt_id": live_receipt_id,
        "source_acquisition_receipt_id": source_acquisition_receipt_id,
        "live_source_artifact_material_bridge_receipt_id": live_bridge_receipt_id,
        "material_bridge_receipt_id": live_bridge["material_bridge_receipt_id"],
        "downstream_proof_mode": EXISTING_DOWNSTREAM_PROOF_MODE,
        "downstream_proof_hash": downstream_proof["proof_hash"],
        "downstream_proof_receipt_id": downstream_proof["proof_receipt_id"],
        "downstream_proof_receipt_ref": downstream_proof["proof_receipt_ref"],
        "material_snapshot_id": downstream_proof["material_snapshot_id"],
        "coverage": sorted(coverage),
        "coverage_evidence": {step: coverage[step] for step in sorted(coverage)},
        "coverage_evidence_hash": coverage_hash,
        "negative_invariants_hash": negative_invariants_hash,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "provider_private_token_exposed": False,
        "provider_public_url_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "runtime_db_or_storage_expansion_admitted": False,
        "frontend_durable_authority_enabled": False,
        "browser_storage_authority_enabled": False,
        "full_mockup_activation_enabled": False,
        "negative_invariants": negative_invariants,
        "status_projection": {
            "ready": True,
            "blocked_reasons": [],
            "live_source_artifact_authority_bound": True,
            "source_acquisition_authority_bound": True,
            "live_material_bridge_authority_bound": True,
            "underlying_downstream_proof_bound": True,
            "next_allowed_actions": [
                "inspect_sec_edgar_live_source_artifact_downstream_proof_status",
                "select_rendered_or_repeatability_status_after_current_main_sync",
            ],
        },
        "next_allowed_actions": [
            "use this proof as live SEC EDGAR source-artifact downstream Layer 3 evidence",
            "select operator-visible status for the live source-artifact downstream proof after current-main sync",
        ],
    }
    if _contains_forbidden_output_ref(proof):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_raw_authority_exposed",
            "SEC EDGAR live source-artifact downstream proof would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return proof


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_forbidden_request_fields",
            "SEC EDGAR live source-artifact downstream proof does not admit caller paths, URLs, bytes, credentials, connector, model, browser, source-expansion, or frontend authority.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_unknown_field",
            "SEC EDGAR live source-artifact downstream proof fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_schema_not_admitted",
            "SEC EDGAR live source-artifact downstream proof requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _validate_live_bridge_receipt(
    receipt: Mapping[str, Any],
    *,
    live_receipt: Mapping[str, Any],
    source_acquisition_receipt: Mapping[str, Any],
    dataset_version_id: str,
    authority_envelope_hash: str,
    live_bridge_receipt_hash: str,
    material_bridge_receipt_hash: str,
    material_preview_hash: str,
    gate_b_decision_manifest_id: str,
) -> dict[str, str]:
    if str(receipt.get("schema_id") or "") != layer3_sec_edgar_live_material_bridge.SCHEMA_ID:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_live_bridge_schema_mismatch",
            "SEC EDGAR live source-artifact downstream proof requires the live material bridge receipt schema.",
            http_status=409,
            blocked_fields=["live_source_artifact_material_bridge_receipt_id"],
        )
    if str(receipt.get("bridge_mode") or "") != LIVE_BRIDGE_MODE or str(receipt.get("bridge_state") or "") != LIVE_BRIDGE_READY_STATE:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_live_bridge_not_ready",
            "SEC EDGAR live source-artifact downstream proof requires a ready live material bridge receipt.",
            http_status=409,
            blocked_fields=["live_source_artifact_material_bridge_receipt_id"],
        )
    live_authority = _mapping(receipt, "live_source_artifact_authority")
    source_authority = _mapping(receipt, "source_acquisition_authority")
    material_bridge = _mapping(receipt, "material_authority_bridge")
    live_source_artifact = _mapping(live_receipt, "source_artifact_receipt")
    source_acquisition_artifact = _mapping(source_acquisition_receipt, "source_artifact_authority")
    expected = {
        "source_artifact_receipt_hash": str(live_source_artifact.get("source_artifact_receipt_hash") or ""),
        "source_artifact_ref_hash": str(live_source_artifact.get("source_artifact_ref_hash") or ""),
        "content_sha256": str(live_source_artifact.get("content_sha256") or ""),
    }
    for field, value in expected.items():
        if str(live_authority.get(field) or "") != value:
            _blocked(
                "sec_edgar_text_table_live_source_artifact_downstream_proof_live_artifact_mismatch",
                "SEC EDGAR live source-artifact downstream proof live artifact authority is stale or mismatched.",
                http_status=409,
                blocked_fields=[field],
            )
    if str(source_acquisition_artifact.get("source_artifact_receipt_hash") or "") != expected["source_artifact_receipt_hash"]:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_source_acquisition_artifact_mismatch",
            "SEC EDGAR live source-artifact downstream proof requires matching source-acquisition source artifact authority.",
            http_status=409,
            blocked_fields=["source_artifact_receipt_hash"],
        )
    comparisons = {
        "dataset_version_id": dataset_version_id,
        "authority_envelope_hash": authority_envelope_hash,
        "bridge_receipt_hash": material_bridge_receipt_hash,
        "material_preview_hash": material_preview_hash,
        "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
    }
    for field, expected_value in comparisons.items():
        actual = source_authority.get(field) if field in source_authority else material_bridge.get(field)
        if str(actual or "") != expected_value:
            _blocked(
                "sec_edgar_text_table_live_source_artifact_downstream_proof_live_bridge_authority_mismatch",
                "SEC EDGAR live source-artifact downstream proof live bridge authority is stale or mismatched.",
                http_status=409,
                blocked_fields=[field],
            )
    if str(receipt.get("bridge_receipt_hash") or "") != live_bridge_receipt_hash:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_live_bridge_receipt_mismatch",
            "SEC EDGAR live source-artifact downstream proof live bridge receipt hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["live_source_artifact_material_bridge_receipt_hash"],
        )
    return {
        "materialization_receipt_hash": str(source_authority.get("materialization_receipt_hash") or ""),
        "material_bridge_receipt_id": str(material_bridge.get("bridge_receipt_id") or ""),
    }


def _validate_live_coverage(
    value: Any,
    *,
    live_source_artifact_receipt_hash: str,
    live_source_artifact_receipt_id: str,
    source_acquisition_receipt_hash: str,
    source_acquisition_receipt_id: str,
    live_bridge_receipt_hash: str,
    live_bridge_receipt_id: str,
    material_bridge_receipt_hash: str,
    material_preview_hash: str,
    gate_b_decision_manifest_id: str,
    downstream_proof: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_coverage_evidence_missing",
            "Structured per-step live SEC EDGAR downstream coverage evidence is required.",
            http_status=409,
            blocked_fields=["coverage_evidence"],
        )
    missing = sorted(step for step in REQUIRED_COVERAGE if step not in value)
    if missing:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_coverage_incomplete",
            "SEC EDGAR live source-artifact downstream proof evidence is missing required coverage steps.",
            http_status=409,
            blocked_fields=[f"coverage_evidence.{step}" for step in missing],
        )
    coverage = dict(downstream_proof.get("coverage_evidence") or {})
    expected_by_step = {
        "live_source_artifact_acquisition": {
            "live_source_artifact_receipt_hash": live_source_artifact_receipt_hash,
            "server_receipt_id": live_source_artifact_receipt_id,
        },
        "source_acquisition_authority": {
            "source_acquisition_receipt_hash": source_acquisition_receipt_hash,
            "server_receipt_id": source_acquisition_receipt_id,
        },
        "live_material_authority_bridge": {
            "live_source_artifact_material_bridge_receipt_hash": live_bridge_receipt_hash,
            "server_receipt_id": live_bridge_receipt_id,
            "material_bridge_receipt_hash": material_bridge_receipt_hash,
            "material_preview_hash": material_preview_hash,
            "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
        },
    }
    for step, expected_fields in expected_by_step.items():
        item = value.get(step)
        if not isinstance(item, Mapping):
            _blocked(
                "sec_edgar_text_table_live_source_artifact_downstream_proof_coverage_item_invalid",
                "Each live SEC EDGAR downstream proof coverage item must be an object.",
                http_status=409,
                blocked_fields=[f"coverage_evidence.{step}"],
            )
        if str(item.get("status") or "").strip() != "proven":
            _blocked(
                "sec_edgar_text_table_live_source_artifact_downstream_proof_coverage_item_not_proven",
                "Each live SEC EDGAR downstream proof coverage item must be marked proven.",
                http_status=409,
                blocked_fields=[f"coverage_evidence.{step}.status"],
            )
        _validate_negative_flags(step, item)
        for field, expected in expected_fields.items():
            if str(item.get(field) or "") != expected:
                _blocked(
                    "sec_edgar_text_table_live_source_artifact_downstream_proof_coverage_authority_mismatch",
                    "SEC EDGAR live source-artifact downstream proof coverage is not bound to expected live authority.",
                    http_status=409,
                    blocked_fields=[f"coverage_evidence.{step}.{field}"],
                )
        if not any(
            str(item.get(field) or "").strip()
            for field in ("server_response_hash", "response_hash", "receipt_hash", "server_receipt_id")
        ):
            _blocked(
                "sec_edgar_text_table_live_source_artifact_downstream_proof_coverage_not_bound_to_server_receipt",
                "SEC EDGAR live source-artifact downstream proof coverage must include a server response hash, receipt hash, or receipt id.",
                http_status=409,
                blocked_fields=[f"coverage_evidence.{step}"],
            )
        evidence_ref = str(item.get("evidence_ref") or f"{PROOF_RECEIPT_PREFIX}:{step}")
        if _is_forbidden_ref(evidence_ref):
            _blocked(
                "sec_edgar_text_table_live_source_artifact_downstream_proof_coverage_forbidden_reference",
                "SEC EDGAR live source-artifact downstream proof coverage cannot expose raw URL, file, or local path references.",
                http_status=409,
                blocked_fields=[f"coverage_evidence.{step}.evidence_ref"],
            )
        evidence_hash = _required_coverage_hash(step, item)
        coverage[step] = {
            "status": "proven",
            "evidence_ref": evidence_ref,
            "evidence_hash": evidence_hash,
            "server_response_hash": str(item.get("server_response_hash") or item.get("response_hash") or ""),
            "server_receipt_id": str(item.get("server_receipt_id") or ""),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_private_token_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
        }
    return coverage


def _mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_authority_missing",
            f"SEC EDGAR live source-artifact downstream proof requires {key}.",
            http_status=409,
            blocked_fields=[key],
        )
    return item


def _validate_negative_flags(step: str, item: Mapping[str, Any]) -> None:
    for field in (
        "raw_local_path_exposed",
        "raw_url_exposed",
        "artifact_bytes_exposed",
        "provider_private_token_exposed",
        "provider_public_url_enabled",
        "provider_object_writes_enabled",
        "connector_dispatch_enabled",
        "rag_vector_model_runtime_enabled",
        "browser_storage_authority_enabled",
        "frontend_durable_authority_enabled",
        "full_mockup_activation_enabled",
    ):
        if item.get(field) not in (None, False):
            _blocked(
                "sec_edgar_text_table_live_source_artifact_downstream_proof_coverage_exposes_forbidden_authority",
                "SEC EDGAR live source-artifact downstream proof coverage exposes non-admitted authority.",
                http_status=409,
                blocked_fields=[f"coverage_evidence.{step}.{field}"],
            )


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_required_field_missing",
            "A required SEC EDGAR live source-artifact downstream proof field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_sha256(value):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_hash_invalid",
            "SEC EDGAR live source-artifact downstream proof hash fields must be SHA-256 hex strings.",
            blocked_fields=[key],
        )
    return value


def _required_coverage_hash(step: str, item: Mapping[str, Any]) -> str:
    value = str(item.get("evidence_hash") or "").strip()
    if not _is_sha256(value):
        _blocked(
            "sec_edgar_text_table_live_source_artifact_downstream_proof_coverage_hash_invalid",
            "SEC EDGAR live source-artifact downstream proof coverage evidence_hash values must be SHA-256 hex strings.",
            blocked_fields=[f"coverage_evidence.{step}.evidence_hash"],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_text_table_live_source_artifact_downstream_proof_{key}_not_admitted",
            "SEC EDGAR live source-artifact downstream proof request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in FORBIDDEN_REQUEST_FIELDS and item is not None:
                found.append(child)
            found.extend(_find_forbidden_nested_fields(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_forbidden_nested_fields(item, f"{prefix}[{index}]"))
    return sorted(set(found))


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_default_scope_changed": False,
        "live_sec_network_fetch_admitted_for_proof": False,
        "sec_edgar_parser_expansion_admitted": False,
        "xml_html_inline_xbrl_admitted": False,
        "raw_sec_filing_url_authority_admitted": False,
        "direct_live_artifact_to_material_without_source_acquisition_admitted": False,
        "direct_raw_artifact_parse_or_materialization_admitted": False,
        "dataset_version_creation_admitted": False,
        "gate_b_mutation_admitted_in_proof": False,
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
        "artifact_bytes_exposed": False,
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
        text.startswith(("http://", "https://", "file://", "\\\\", "/tmp/", "/var/", "/home/"))
        or "aps-target-artifacts/" in text
        or bool(_LOCAL_PATH_RE.match(value.strip()))
    )


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _blocked(
    code: str,
    message: str,
    *,
    http_status: int = 400,
    blocked_fields: list[str] | None = None,
    next_allowed_actions: list[str] | None = None,
) -> None:
    raise Layer3WorkbenchError(
        code,
        message,
        status="blocked" if http_status < 409 else "conflict",
        http_status=http_status,
        blocked_fields=blocked_fields or [],
        next_allowed_actions=next_allowed_actions or [],
    )


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
