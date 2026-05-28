from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.models.models import L3MaterialSnapshot, L3SelectionManifest, L3Session
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_authority,
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge,
    layer3_sec_edgar_html_inline_xbrl_parser,
)
from app.services.layer3_gate_b_state import (
    gate_b_decision_manifest_id as compute_gate_b_decision_manifest_id,
    gate_b_idempotency_from_session,
)
from app.services.layer3_sec_edgar_ref_safety import contains_forbidden_ref, find_forbidden_ref_paths
from app.services.layer3_utils import stable_hash, stable_json_bytes
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_material_downstream_proof.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_material_downstream_proof_request.v1"
SCHEMA_VERSION = 1
PROOF_MODE = "sec_edgar_html_inline_xbrl_fact_material_downstream_layer3_e2e_proof_v1"
OPERATOR_DECISION = "record_sec_edgar_html_inline_xbrl_fact_material_downstream_layer3_e2e_proof"
PROOF_STATE = "sec_edgar_html_inline_xbrl_fact_material_downstream_layer3_e2e_proven"
PROOF_RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-fact-material-downstream-proof"

SOURCE_FAMILY = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.SOURCE_FAMILY
PARSER_FAMILY = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.PARSER_FAMILY
TYPED_CONTENT_CONTRACT_ID = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.TYPED_CONTENT_CONTRACT_ID
SOURCE_CLASS = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.SOURCE_CLASS
BRIDGE_MODE = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.BRIDGE_MODE
BRIDGE_READY_STATE = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.READY_STATE

REQUIRED_COVERAGE = frozenset(
    {
        "real_filing_connector_acquisition",
        "live_source_artifact_acquisition",
        "html_inline_xbrl_source_family_parser",
        "html_inline_xbrl_fact_authority",
        "html_inline_xbrl_fact_material_authority_bridge",
        "gate_b_commit",
        "gate_c_typing",
        "retrieval_context",
        "analysis_execution_or_status",
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
        "operator_artifact_inspection",
    }
)
SESSION_BOUND_COVERAGE = REQUIRED_COVERAGE - {
    "real_filing_connector_acquisition",
    "live_source_artifact_acquisition",
    "html_inline_xbrl_source_family_parser",
    "html_inline_xbrl_fact_authority",
    "html_inline_xbrl_fact_material_authority_bridge",
}
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
    "provider_url",
    "connector_url",
    "command",
    "file",
    "files",
    "file_bytes",
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
    "stdout",
    "stderr",
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
    "proof_mode",
    "operator_decision",
    "parser_receipt_id",
    "parser_receipt_hash",
    "fact_authority_receipt_id",
    "fact_authority_receipt_hash",
    "fact_material_bridge_receipt_id",
    "fact_material_bridge_receipt_hash",
    "dataset_version_id",
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
    "parser_receipt_hash",
    "connector_receipt_hash",
    "live_source_artifact_receipt_hash",
    "source_artifact_receipt_hash",
    "content_sha256",
    "content_order_hash",
    "fact_authority_receipt_hash",
    "fact_inventory_hash",
    "diagnostics_hash",
    "dataset_version_id",
    "dataset_version_hash",
    "materialization_receipt_hash",
    "fact_material_bridge_receipt_hash",
    "material_preview_hash",
    "gate_b_decision_manifest_id",
    "session_id",
    "selection_manifest_id",
    "material_snapshot_id",
    "material_snapshot_payload_hash",
    "coverage_evidence_hash",
    "negative_invariants_hash",
    "operator_confirmation",
)

def record_sec_edgar_html_inline_xbrl_fact_material_downstream_layer3_proof(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "proof_mode", PROOF_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    if request.get("operator_confirmation") is not True:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_operator_confirmation_required",
            "operator_confirmation=true is required before recording SEC EDGAR HTML/iXBRL fact material downstream proof.",
            blocked_fields=["operator_confirmation"],
        )

    parser_receipt_id = _required(request, "parser_receipt_id")
    parser_receipt_hash = _required_hash(request, "parser_receipt_hash")
    fact_authority_receipt_id = _required(request, "fact_authority_receipt_id")
    fact_authority_receipt_hash = _required_hash(request, "fact_authority_receipt_hash")
    fact_material_bridge_receipt_id = _required(request, "fact_material_bridge_receipt_id")
    fact_material_bridge_receipt_hash = _required_hash(request, "fact_material_bridge_receipt_hash")
    dataset_version_id = _required(request, "dataset_version_id")
    material_preview_hash = _required_hash(request, "material_preview_hash")
    gate_b_decision_manifest_id = _required(request, "gate_b_decision_manifest_id")
    session_id = _required(request, "session_id")
    selection_manifest_id = _required(request, "selection_manifest_id")
    material_snapshot_payload_hash = _required_hash(request, "material_snapshot_payload_hash")

    parser_receipt = _validate_parser_receipt(
        parser_receipt_id=parser_receipt_id,
        parser_receipt_hash=parser_receipt_hash,
    )
    fact_authority = _validate_fact_authority_receipt(
        parser_receipt=parser_receipt,
        fact_authority_receipt_id=fact_authority_receipt_id,
        fact_authority_receipt_hash=fact_authority_receipt_hash,
    )
    bridge = _validate_material_bridge_projection(
        parser_receipt=parser_receipt,
        fact_authority=fact_authority,
        fact_material_bridge_receipt_id=fact_material_bridge_receipt_id,
        fact_material_bridge_receipt_hash=fact_material_bridge_receipt_hash,
        dataset_version_id=dataset_version_id,
        material_preview_hash=material_preview_hash,
        gate_b_decision_manifest_id=gate_b_decision_manifest_id,
    )
    session, manifest = _validate_gate_b_session(
        db,
        session_id=session_id,
        selection_manifest_id=selection_manifest_id,
        material_preview_hash=material_preview_hash,
        gate_b_decision_manifest_id=gate_b_decision_manifest_id,
    )
    snapshot, material_payload = _validate_material_snapshot(
        db,
        session_id=session.session_id,
        dataset_version_id=dataset_version_id,
        material_snapshot_payload_hash=material_snapshot_payload_hash,
    )
    authority = _authority_hashes(parser_receipt, fact_authority, bridge)
    coverage = _validate_coverage_evidence(
        request.get("coverage_evidence"),
        authority=authority,
        fact_material_bridge_receipt_hash=fact_material_bridge_receipt_hash,
        material_preview_hash=material_preview_hash,
        gate_b_decision_manifest_id=gate_b_decision_manifest_id,
        session_id=session.session_id,
        selection_manifest_id=manifest.selection_manifest_id,
        material_snapshot_payload_hash=snapshot.payload_hash,
    )

    negative_invariants = _negative_invariants()
    coverage_hash = stable_hash(coverage)
    negative_invariants_hash = stable_hash(negative_invariants)
    proof_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "mode": PROOF_MODE,
        "parser_receipt_hash": parser_receipt_hash,
        "connector_receipt_hash": authority["connector_receipt_hash"],
        "live_source_artifact_receipt_hash": authority["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": authority["source_artifact_receipt_hash"],
        "content_sha256": authority["content_sha256"],
        "content_order_hash": authority["content_order_hash"],
        "fact_authority_receipt_hash": fact_authority_receipt_hash,
        "fact_inventory_hash": authority["fact_inventory_hash"],
        "diagnostics_hash": authority["diagnostics_hash"],
        "dataset_version_id": dataset_version_id,
        "dataset_version_hash": authority["dataset_version_hash"],
        "materialization_receipt_hash": authority["materialization_receipt_hash"],
        "fact_material_bridge_receipt_hash": fact_material_bridge_receipt_hash,
        "material_preview_hash": material_preview_hash,
        "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
        "session_id": session.session_id,
        "selection_manifest_id": manifest.selection_manifest_id,
        "material_snapshot_id": snapshot.material_snapshot_id,
        "material_snapshot_payload_hash": snapshot.payload_hash,
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
        "parser_receipt_id": parser_receipt_id,
        "fact_authority_receipt_id": fact_authority_receipt_id,
        "fact_material_bridge_receipt_id": fact_material_bridge_receipt_id,
        "fact_material_bridge_receipt_hash": fact_material_bridge_receipt_hash,
        "bridge_receipt_hash": fact_material_bridge_receipt_hash,
        "fact_inventory_hash": authority["fact_inventory_hash"],
        "diagnostics_hash": authority["diagnostics_hash"],
        "primary_document_hash": authority["primary_document_hash"],
        "document_inventory_hash": authority["document_inventory_hash"],
        "table_candidate_inventory_hash": authority["table_candidate_inventory_hash"],
        "inline_xbrl_marker_inventory_hash": authority["inline_xbrl_marker_inventory_hash"],
        "material_snapshot_source_shape": snapshot.source_shape,
        "material_snapshot_authority": {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "source_shape": snapshot.source_shape,
            "payload_hash": snapshot.payload_hash,
            "dataset_version_id": dataset_version_id,
            "source_family": SOURCE_FAMILY,
            "parser_family": PARSER_FAMILY,
            "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        },
        "material_payload_contract": {
            "source_family": str(material_payload.get("source_family") or ""),
            "parser_family": str(material_payload.get("parser_family") or ""),
            "typed_content_contract_id": str(material_payload.get("typed_content_contract_id") or ""),
        },
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
            "next_allowed_actions": [
                "use_sec_edgar_html_inline_xbrl_fact_material_downstream_proof_as_layer3_e2e_evidence",
                "select_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_after_runtime_evidence",
            ],
        },
        "next_allowed_actions": [
            "use this proof as SEC EDGAR HTML/iXBRL fact material downstream Layer 3 evidence",
            "select the next operator-visible SEC EDGAR HTML/iXBRL status/checkpoint slice after current-main sync",
        ],
    }
    if _contains_forbidden_output_ref(proof):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL fact material downstream proof would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return proof


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL fact material downstream proof does not admit caller paths, URLs, bytes, credentials, connector, model, browser, source-expansion, or frontend authority.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_unknown_field",
            "SEC EDGAR HTML/iXBRL fact material downstream proof fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL fact material downstream proof requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _validate_parser_receipt(*, parser_receipt_id: str, parser_receipt_hash: str) -> dict[str, Any]:
    parser_receipt = layer3_sec_edgar_html_inline_xbrl_parser.read_sec_edgar_html_inline_xbrl_source_family_parser_receipt(
        parser_receipt_id,
        expected_parser_receipt_hash=parser_receipt_hash,
    )
    mismatches = []
    for field, expected in {
        "parser_receipt_id": parser_receipt_id,
        "parser_receipt_hash": parser_receipt_hash,
        "parser_mode": PARSER_FAMILY,
    }.items():
        if str(parser_receipt.get(field) or "").strip() != str(expected):
            mismatches.append(field)
    for field in (
        "connector_receipt_hash",
        "live_source_artifact_receipt_hash",
        "source_artifact_receipt_hash",
        "content_sha256",
        "primary_document_hash",
        "document_inventory_hash",
        "content_order_hash",
        "table_candidate_inventory_hash",
        "inline_xbrl_marker_inventory_hash",
    ):
        if not _is_sha256(str(parser_receipt.get(field) or "")):
            mismatches.append(field)
    if mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_parser_receipt_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof parser authority is missing, stale, or outside the admitted source-family contract.",
            http_status=409,
            blocked_fields=sorted(set(mismatches)),
            next_allowed_actions=["refresh_sec_edgar_html_inline_xbrl_source_family_parser_receipt"],
        )
    return dict(parser_receipt)


def _validate_fact_authority_receipt(
    *,
    parser_receipt: Mapping[str, Any],
    fact_authority_receipt_id: str,
    fact_authority_receipt_hash: str,
) -> dict[str, Any]:
    fact_authority = layer3_sec_edgar_html_inline_xbrl_fact_authority.read_sec_edgar_html_inline_xbrl_fact_authority_receipt(
        fact_authority_receipt_id,
        expected_fact_authority_receipt_hash=fact_authority_receipt_hash,
    )
    mismatches = []
    for field, expected in {
        "fact_authority_state": layer3_sec_edgar_html_inline_xbrl_fact_authority.READY_STATE,
        "fact_authority_receipt_id": fact_authority_receipt_id,
        "fact_authority_receipt_hash": fact_authority_receipt_hash,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "parser_receipt_id": parser_receipt["parser_receipt_id"],
        "parser_receipt_hash": parser_receipt["parser_receipt_hash"],
        "connector_receipt_hash": parser_receipt["connector_receipt_hash"],
        "live_source_artifact_receipt_hash": parser_receipt["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": parser_receipt["source_artifact_receipt_hash"],
        "content_sha256": parser_receipt["content_sha256"],
        "primary_document_hash": parser_receipt["primary_document_hash"],
        "document_inventory_hash": parser_receipt["document_inventory_hash"],
        "content_order_hash": parser_receipt["content_order_hash"],
        "table_candidate_inventory_hash": parser_receipt["table_candidate_inventory_hash"],
        "inline_xbrl_marker_inventory_hash": parser_receipt["inline_xbrl_marker_inventory_hash"],
    }.items():
        if str(fact_authority.get(field) or "").strip() != str(expected):
            mismatches.append(field)
    for field in ("fact_inventory_hash", "diagnostics_hash"):
        if not _is_sha256(str(fact_authority.get(field) or "")):
            mismatches.append(field)
    if mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_fact_authority_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof fact authority is missing, stale, blocked, or mismatched.",
            http_status=409,
            blocked_fields=sorted(set(mismatches)),
            next_allowed_actions=["refresh_sec_edgar_html_inline_xbrl_fact_authority_receipt"],
        )
    return dict(fact_authority)


def _validate_material_bridge_projection(
    *,
    parser_receipt: Mapping[str, Any],
    fact_authority: Mapping[str, Any],
    fact_material_bridge_receipt_id: str,
    fact_material_bridge_receipt_hash: str,
    dataset_version_id: str,
    material_preview_hash: str,
    gate_b_decision_manifest_id: str,
) -> dict[str, Any]:
    bridge = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.inspect_sec_edgar_html_inline_xbrl_fact_material_bridge_status(
        fact_material_bridge_receipt_id
    )
    if bridge.get("bridge_state") != BRIDGE_READY_STATE:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_missing_ready_bridge",
            "SEC EDGAR HTML/iXBRL fact material downstream proof requires a ready fact-material bridge receipt.",
            http_status=409,
            blocked_fields=["fact_material_bridge_receipt_id"],
            next_allowed_actions=["refresh_sec_edgar_html_inline_xbrl_fact_material_bridge"],
        )
    mismatches = []
    for field, expected in {
        "mode": BRIDGE_MODE,
        "fact_material_bridge_receipt_id": fact_material_bridge_receipt_id,
        "fact_material_bridge_receipt_hash": fact_material_bridge_receipt_hash,
        "bridge_receipt_id": fact_material_bridge_receipt_id,
        "bridge_receipt_hash": fact_material_bridge_receipt_hash,
        "dataset_version_id": dataset_version_id,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": TYPED_CONTENT_CONTRACT_ID,
        "fact_authority_receipt_id": fact_authority["fact_authority_receipt_id"],
        "fact_authority_receipt_hash": fact_authority["fact_authority_receipt_hash"],
        "parser_receipt_id": parser_receipt["parser_receipt_id"],
        "parser_receipt_hash": parser_receipt["parser_receipt_hash"],
        "material_preview_hash": material_preview_hash,
        "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
    }.items():
        if str(bridge.get(field) or "").strip() != str(expected):
            mismatches.append(field)
    authority = bridge.get("authority_hashes") if isinstance(bridge.get("authority_hashes"), Mapping) else {}
    for field, expected in {
        "connector_receipt_hash": parser_receipt["connector_receipt_hash"],
        "live_source_artifact_receipt_hash": parser_receipt["live_source_artifact_receipt_hash"],
        "source_artifact_receipt_hash": parser_receipt["source_artifact_receipt_hash"],
        "content_sha256": parser_receipt["content_sha256"],
        "fact_authority_receipt_hash": fact_authority["fact_authority_receipt_hash"],
        "fact_inventory_hash": fact_authority["fact_inventory_hash"],
        "diagnostics_hash": fact_authority["diagnostics_hash"],
        "material_preview_hash": material_preview_hash,
        "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
        "fact_material_bridge_receipt_hash": fact_material_bridge_receipt_hash,
    }.items():
        if str(authority.get(field) or "").strip() != str(expected):
            mismatches.append(f"authority_hashes.{field}")
    for field in ("dataset_version_hash", "materialization_receipt_hash"):
        if not _is_sha256(str(authority.get(field) or "")):
            mismatches.append(f"authority_hashes.{field}")
    compatibility = bridge.get("compatibility") if isinstance(bridge.get("compatibility"), Mapping) else {}
    if str(compatibility.get("source_class") or "") != SOURCE_CLASS:
        mismatches.append("compatibility.source_class")
    summary = bridge.get("materialization_summary") if isinstance(bridge.get("materialization_summary"), Mapping) else {}
    if summary.get("source_order_preserved") is not True:
        mismatches.append("materialization_summary.source_order_preserved")
    if summary.get("raw_content_returned") is not False:
        mismatches.append("materialization_summary.raw_content_returned")
    if not _is_sha256(str(summary.get("admitted_subset_hash") or "")):
        mismatches.append("materialization_summary.admitted_subset_hash")
    bridge_negative = bridge.get("negative_invariants") if isinstance(bridge.get("negative_invariants"), Mapping) else {}
    for field in (
        "live_sec_network_fetch_performed_by_bridge",
        "submissions_lookup_runtime_performed_by_bridge",
        "browser_supplied_html_admitted",
        "browser_supplied_raw_url_admitted",
        "browser_supplied_local_path_admitted",
        "artifact_bytes_admitted",
        "standalone_xml_xbrl_fact_authority_enabled",
        "sec_companyfacts_api_runtime_enabled",
        "taxonomy_network_resolution_enabled",
        "financial_statement_semantics_enabled",
        "fact_to_statement_classification_enabled",
        "source_expansion_admitted",
        "provider_object_write_enabled",
        "connector_dispatch_enabled",
        "rag_vector_model_runtime_enabled",
        "frontend_durable_authority_enabled",
        "full_mockup_activation_enabled",
        "raw_local_path_exposed",
        "raw_url_exposed",
        "artifact_bytes_exposed",
        "raw_fact_values_exposed_in_operator_projection",
    ):
        if bridge_negative.get(field) is not False:
            mismatches.append(f"negative_invariants.{field}")
    if mismatches:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_bridge_hash_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof bridge authority is stale, blocked, or mismatched.",
            http_status=409,
            blocked_fields=sorted(set(mismatches)),
            next_allowed_actions=["refresh_sec_edgar_html_inline_xbrl_fact_material_bridge"],
        )
    return dict(bridge)


def _validate_gate_b_session(
    db: Session,
    *,
    session_id: str,
    selection_manifest_id: str,
    material_preview_hash: str,
    gate_b_decision_manifest_id: str,
) -> tuple[L3Session, L3SelectionManifest]:
    session = db.get(L3Session, session_id)
    manifest = db.get(L3SelectionManifest, selection_manifest_id)
    if session is None or manifest is None:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_missing_gate_b_session",
            "SEC EDGAR HTML/iXBRL fact material downstream proof requires an existing committed Gate B session and selection manifest.",
            http_status=404,
            blocked_fields=["session_id", "selection_manifest_id"],
        )
    if session.selection_manifest_id != selection_manifest_id or manifest.session_id != session_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_selection_manifest_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof session and selection manifest do not match.",
            http_status=409,
            blocked_fields=["session_id", "selection_manifest_id"],
        )
    decision_manifest = (session.operator_context_json or {}).get("layer3_gate_b_decision_manifest_v1")
    if (
        not isinstance(decision_manifest, dict)
        or compute_gate_b_decision_manifest_id(decision_manifest) != gate_b_decision_manifest_id
    ):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_gate_b_hash_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof Gate B decision manifest is missing or stale.",
            http_status=409,
            blocked_fields=["gate_b_decision_manifest_id"],
        )
    gate_b_record = gate_b_idempotency_from_session(session)
    if not isinstance(gate_b_record, dict):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_gate_b_idempotency_missing",
            "SEC EDGAR HTML/iXBRL fact material downstream proof requires the committed Gate B idempotency record.",
            http_status=409,
            blocked_fields=["session_id"],
        )
    if (
        str(gate_b_record.get("material_preview_hash") or "") != material_preview_hash
        or str(gate_b_record.get("gate_b_decision_manifest_id") or "") != gate_b_decision_manifest_id
    ):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_gate_b_payload_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof Gate B commit does not match the bridge-returned material preview and decision manifest.",
            http_status=409,
            blocked_fields=["material_preview_hash", "gate_b_decision_manifest_id"],
        )
    return session, manifest


def _validate_material_snapshot(
    db: Session,
    *,
    session_id: str,
    dataset_version_id: str,
    material_snapshot_payload_hash: str,
) -> tuple[L3MaterialSnapshot, dict[str, Any]]:
    snapshots = (
        db.query(L3MaterialSnapshot)
        .filter(L3MaterialSnapshot.session_id == session_id)
        .filter(L3MaterialSnapshot.source_shape == SOURCE_CLASS)
        .all()
    )
    matching = [
        snapshot
        for snapshot in snapshots
        if str((snapshot.source_identity_json or {}).get("dataset_version_id") or "") == dataset_version_id
    ]
    if len(matching) != 1:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_material_snapshot_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof requires exactly one committed DatasetVersion material snapshot for the bridged DatasetVersion.",
            http_status=409,
            blocked_fields=["dataset_version_id", "session_id"],
        )
    snapshot = matching[0]
    if snapshot.payload_hash != material_snapshot_payload_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_material_snapshot_hash_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof material snapshot payload hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["material_snapshot_payload_hash"],
        )
    payload = _read_material_payload(snapshot)
    if _authority_value(snapshot, payload, "source_family") != SOURCE_FAMILY:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_source_family_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof material snapshot does not prove sec_edgar_html_inline_xbrl authority.",
            http_status=409,
            blocked_fields=["material_snapshot_payload_hash"],
        )
    if _authority_value(snapshot, payload, "parser_family") != PARSER_FAMILY:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_parser_family_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof material snapshot does not prove the admitted HTML/iXBRL parser authority.",
            http_status=409,
            blocked_fields=["material_snapshot_payload_hash"],
        )
    if _authority_value(snapshot, payload, "typed_content_contract_id") != TYPED_CONTENT_CONTRACT_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_typed_content_contract_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof material snapshot does not prove the admitted typed-content contract.",
            http_status=409,
            blocked_fields=["material_snapshot_payload_hash"],
        )
    return snapshot, payload


def _read_material_payload(snapshot: L3MaterialSnapshot) -> dict[str, Any]:
    path = Path(str(snapshot.payload_ref or ""))
    if not path.is_file():
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_material_snapshot_payload_missing",
            "SEC EDGAR HTML/iXBRL fact material downstream proof cannot read the committed material snapshot payload.",
            http_status=409,
            blocked_fields=["material_snapshot_payload_hash"],
        )
    try:
        body = path.read_bytes()
        payload = json.loads(body.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_material_snapshot_payload_unreadable",
            "SEC EDGAR HTML/iXBRL fact material downstream proof cannot read the committed material snapshot payload.",
            http_status=409,
            blocked_fields=["material_snapshot_payload_hash"],
        )
    if hashlib.sha256(stable_json_bytes(payload)).hexdigest() != snapshot.payload_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_material_snapshot_payload_hash_invalid",
            "SEC EDGAR HTML/iXBRL fact material downstream proof material snapshot payload bytes no longer match the committed hash.",
            http_status=409,
            blocked_fields=["material_snapshot_payload_hash"],
        )
    if not isinstance(payload, dict):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_material_snapshot_payload_invalid",
            "SEC EDGAR HTML/iXBRL fact material downstream proof material snapshot payload is not an object.",
            http_status=409,
            blocked_fields=["material_snapshot_payload_hash"],
        )
    return payload


def _validate_coverage_evidence(
    value: Any,
    *,
    authority: Mapping[str, str],
    fact_material_bridge_receipt_hash: str,
    material_preview_hash: str,
    gate_b_decision_manifest_id: str,
    session_id: str,
    selection_manifest_id: str,
    material_snapshot_payload_hash: str,
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_coverage_evidence_missing",
            "Structured per-step downstream coverage evidence is required.",
            http_status=409,
            blocked_fields=["coverage_evidence"],
        )
    missing = sorted(step for step in REQUIRED_COVERAGE if step not in value)
    if missing:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_coverage_incomplete",
            "SEC EDGAR HTML/iXBRL fact material downstream proof evidence is missing required coverage steps.",
            http_status=409,
            blocked_fields=[f"coverage_evidence.{step}" for step in missing],
        )
    coverage: dict[str, dict[str, Any]] = {}
    for step in sorted(REQUIRED_COVERAGE):
        item = value.get(step)
        if not isinstance(item, dict):
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_coverage_item_invalid",
                "Each SEC EDGAR HTML/iXBRL fact material downstream proof coverage item must be an object.",
                http_status=409,
                blocked_fields=[f"coverage_evidence.{step}"],
            )
        if str(item.get("status") or "").strip() != "proven":
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_coverage_item_not_proven",
                "Each SEC EDGAR HTML/iXBRL fact material downstream proof coverage item must be marked proven.",
                http_status=409,
                blocked_fields=[f"coverage_evidence.{step}.status"],
            )
        _validate_coverage_negative_invariants(step, item)
        _validate_coverage_bindings(
            step,
            item,
            authority=authority,
            fact_material_bridge_receipt_hash=fact_material_bridge_receipt_hash,
            material_preview_hash=material_preview_hash,
            gate_b_decision_manifest_id=gate_b_decision_manifest_id,
            session_id=session_id,
            selection_manifest_id=selection_manifest_id,
            material_snapshot_payload_hash=material_snapshot_payload_hash,
        )
        evidence_ref = str(item.get("evidence_ref") or f"{PROOF_RECEIPT_PREFIX}:{step}")
        if _is_forbidden_ref(evidence_ref):
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_coverage_exposes_forbidden_reference",
                "SEC EDGAR HTML/iXBRL fact material downstream proof coverage cannot expose raw URL, file, or local path references.",
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
            "session_id": str(item.get("session_id") or "") if step in SESSION_BOUND_COVERAGE else "",
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
            "provider_private_token_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
            "full_mockup_activation_enabled": False,
        }
    return coverage


def _validate_coverage_negative_invariants(step: str, item: Mapping[str, Any]) -> None:
    for field in (
        "raw_local_path_exposed",
        "raw_url_exposed",
        "artifact_bytes_exposed",
        "raw_fact_values_exposed_in_operator_projection",
        "fact_value_reconstruction_admitted_in_proof",
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
                "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_coverage_exposes_forbidden_authority",
                "SEC EDGAR HTML/iXBRL fact material downstream proof coverage exposes non-admitted authority.",
                http_status=409,
                blocked_fields=[f"coverage_evidence.{step}.{field}"],
            )


def _validate_coverage_bindings(
    step: str,
    item: Mapping[str, Any],
    *,
    authority: Mapping[str, str],
    fact_material_bridge_receipt_hash: str,
    material_preview_hash: str,
    gate_b_decision_manifest_id: str,
    session_id: str,
    selection_manifest_id: str,
    material_snapshot_payload_hash: str,
) -> None:
    if step in SESSION_BOUND_COVERAGE and str(item.get("session_id") or "") != session_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_coverage_session_mismatch",
            "SEC EDGAR HTML/iXBRL fact material downstream proof coverage must bind to the committed Layer 3 session.",
            http_status=409,
            blocked_fields=[f"coverage_evidence.{step}.session_id"],
        )
    expected_by_field = {
        "real_filing_connector_acquisition": {
            "connector_receipt_hash": authority["connector_receipt_hash"],
        },
        "live_source_artifact_acquisition": {
            "live_source_artifact_receipt_hash": authority["live_source_artifact_receipt_hash"],
            "source_artifact_receipt_hash": authority["source_artifact_receipt_hash"],
        },
        "html_inline_xbrl_source_family_parser": {
            "parser_receipt_hash": authority["parser_receipt_hash"],
            "content_sha256": authority["content_sha256"],
            "primary_document_hash": authority["primary_document_hash"],
            "content_order_hash": authority["content_order_hash"],
        },
        "html_inline_xbrl_fact_authority": {
            "fact_authority_receipt_hash": authority["fact_authority_receipt_hash"],
            "fact_inventory_hash": authority["fact_inventory_hash"],
            "diagnostics_hash": authority["diagnostics_hash"],
        },
        "html_inline_xbrl_fact_material_authority_bridge": {
            "fact_material_bridge_receipt_hash": fact_material_bridge_receipt_hash,
            "bridge_receipt_hash": fact_material_bridge_receipt_hash,
            "material_preview_hash": material_preview_hash,
            "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
        },
        "gate_b_commit": {
            "material_preview_hash": material_preview_hash,
            "gate_b_decision_manifest_id": gate_b_decision_manifest_id,
            "selection_manifest_id": selection_manifest_id,
            "material_snapshot_payload_hash": material_snapshot_payload_hash,
        },
    }
    for field, expected in expected_by_field.get(step, {}).items():
        if str(item.get(field) or "") != expected:
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_coverage_authority_mismatch",
                "SEC EDGAR HTML/iXBRL fact material downstream proof coverage is not bound to the expected server-owned authority.",
                http_status=409,
                blocked_fields=[f"coverage_evidence.{step}.{field}"],
            )
    if not any(
        str(item.get(field) or "").strip()
        for field in ("server_response_hash", "response_hash", "receipt_hash", "server_receipt_id")
    ):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_coverage_not_bound_to_server_receipt",
            "SEC EDGAR HTML/iXBRL fact material downstream proof coverage must include a server response hash, receipt hash, or receipt id.",
            http_status=409,
            blocked_fields=[f"coverage_evidence.{step}"],
        )


def _authority_hashes(
    parser_receipt: Mapping[str, Any],
    fact_authority: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> dict[str, str]:
    bridge_authority = bridge.get("authority_hashes") if isinstance(bridge.get("authority_hashes"), Mapping) else {}
    values = {
        "parser_receipt_hash": str(parser_receipt.get("parser_receipt_hash") or ""),
        "connector_receipt_hash": str(parser_receipt.get("connector_receipt_hash") or ""),
        "live_source_artifact_receipt_hash": str(parser_receipt.get("live_source_artifact_receipt_hash") or ""),
        "source_artifact_receipt_hash": str(parser_receipt.get("source_artifact_receipt_hash") or ""),
        "content_sha256": str(parser_receipt.get("content_sha256") or ""),
        "primary_document_hash": str(parser_receipt.get("primary_document_hash") or ""),
        "document_inventory_hash": str(parser_receipt.get("document_inventory_hash") or ""),
        "content_order_hash": str(parser_receipt.get("content_order_hash") or ""),
        "table_candidate_inventory_hash": str(parser_receipt.get("table_candidate_inventory_hash") or ""),
        "inline_xbrl_marker_inventory_hash": str(parser_receipt.get("inline_xbrl_marker_inventory_hash") or ""),
        "fact_authority_receipt_hash": str(fact_authority.get("fact_authority_receipt_hash") or ""),
        "fact_inventory_hash": str(fact_authority.get("fact_inventory_hash") or ""),
        "diagnostics_hash": str(fact_authority.get("diagnostics_hash") or ""),
        "dataset_version_hash": str(bridge_authority.get("dataset_version_hash") or ""),
        "materialization_receipt_hash": str(bridge_authority.get("materialization_receipt_hash") or ""),
        "fact_material_bridge_receipt_hash": str(bridge_authority.get("fact_material_bridge_receipt_hash") or ""),
    }
    missing = [key for key, value in values.items() if not _is_sha256(value)]
    if missing:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_authority_hash_missing",
            "SEC EDGAR HTML/iXBRL fact material downstream proof requires parser and material bridge SHA-256 authority bindings.",
            http_status=409,
            blocked_fields=missing,
        )
    return values


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_required_field_missing",
            "A required SEC EDGAR HTML/iXBRL fact material downstream proof field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_sha256(value):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_hash_invalid",
            "SEC EDGAR HTML/iXBRL fact material downstream proof hash fields must be SHA-256 hex strings.",
            blocked_fields=[key],
        )
    return value


def _required_coverage_hash(step: str, item: Mapping[str, Any]) -> str:
    value = str(item.get("evidence_hash") or "").strip()
    if not _is_sha256(value):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_material_downstream_proof_coverage_hash_invalid",
            "SEC EDGAR HTML/iXBRL fact material downstream proof coverage evidence_hash values must be SHA-256 hex strings.",
            blocked_fields=[f"coverage_evidence.{step}.evidence_hash"],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_material_downstream_proof_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL fact material downstream proof request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _authority_value(snapshot: L3MaterialSnapshot, payload: Mapping[str, Any], field: str) -> str:
    for candidate in (
        payload,
        snapshot.source_provenance_json or {},
        snapshot.source_identity_json or {},
        snapshot.load_summary_json or {},
    ):
        if isinstance(candidate, Mapping) and candidate.get(field):
            return str(candidate[field])
    return ""


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    return find_forbidden_ref_paths(value, forbidden_keys=FORBIDDEN_REQUEST_FIELDS, prefix=prefix)


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_default_scope_changed": False,
        "live_sec_network_fetch_admitted_for_proof": False,
        "submissions_lookup_runtime_admitted_for_proof": False,
        "html_inline_xbrl_reparse_or_materialization_admitted_in_proof": False,
        "fact_value_reconstruction_admitted_in_proof": False,
        "gate_b_mutation_admitted_in_proof": False,
        "xml_xbrl_fact_authority_admitted": False,
        "sec_companyfacts_api_runtime_enabled": False,
        "taxonomy_network_resolution_enabled": False,
        "financial_statement_semantics_admitted": False,
        "fact_to_statement_classification_enabled": False,
        "raw_sec_filing_url_authority_admitted": False,
        "broad_source_expansion_admitted": False,
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
        "raw_fact_values_exposed_in_operator_projection": False,
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
