from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_authority,
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit,
    layer3_sec_edgar_html_inline_xbrl_parser,
    layer3_sec_edgar_real_filing_acquisition_connector,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_real_company_corpus_validation.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_real_company_corpus_validation_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_real_company_corpus_validation_status.v1"
SCHEMA_VERSION = 1
VALIDATION_MODE = "sec_edgar_real_company_corpus_validation_v1"
OPERATOR_DECISION = "validate_sec_edgar_real_company_corpus_product_path"
READY_STATE = "sec_edgar_real_company_corpus_validation_ready"
BLOCKED_STATE = "sec_edgar_real_company_corpus_validation_blocked"
RECEIPT_PREFIX = "sec-edgar-real-company-corpus-validation"
RECEIPT_DIR = "layer3-sec-edgar-real-company-corpus-validation"
REDACTION_POLICY_ID = "sec_edgar_real_company_corpus_validation_redaction_v1"

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "validation_mode",
    "operator_decision",
    "company_matrix",
    "operator_confirmation",
    "actor",
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
    "process",
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
    "value",
    "value_text",
    "fact_value",
    "raw_fact_value",
}
_LOCAL_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")


def validate_sec_edgar_real_company_corpus_product_path(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "validation_mode", VALIDATION_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    if request.get("operator_confirmation") is not True:
        return _blocked_response(request_id, reasons=[_reason("missing_operator_confirmation")])

    company_matrix = _company_matrix(request.get("company_matrix"))
    connector = layer3_sec_edgar_real_filing_acquisition_connector.acquire_sec_edgar_real_filing_validation_corpus(
        {
            "client_request_id": f"{request_id}-connector",
            "connector_mode": layer3_sec_edgar_real_filing_acquisition_connector.CONNECTOR_MODE,
            "operator_decision": layer3_sec_edgar_real_filing_acquisition_connector.OPERATOR_DECISION,
            "example_set_mode": layer3_sec_edgar_real_filing_acquisition_connector.EXAMPLE_SET_MODE,
            "company_matrix": list(company_matrix),
            "filing_selection_policy": (
                layer3_sec_edgar_real_filing_acquisition_connector.REAL_COMPANY_DISCOVERY_POLICY
            ),
            "operator_confirmation": True,
        }
    )
    records = _filing_validation_records(connector, request_id=request_id, db=db)
    matrix = _product_utility_matrix(records)
    diagnostics = _diagnostics(connector, records)
    receipt_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_mode": VALIDATION_MODE,
            "connector_receipt_hash": connector["connector_receipt_hash"],
            "company_matrix": list(company_matrix),
            "record_hashes": [record["record_hash"] for record in records],
            "matrix_hash": stable_hash(matrix),
            "diagnostics_hash": stable_hash(diagnostics),
        }
    )
    binding = _read_request_binding(request_id)
    if binding and binding.get("validation_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_real_company_corpus_validation_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR real-company corpus validation basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["validation_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_mode": VALIDATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "validation_state": READY_STATE,
        "validation_receipt_id": f"{RECEIPT_PREFIX}-{receipt_hash[:24]}",
        "validation_receipt_hash": receipt_hash,
        "validation_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "connector_receipt_id": connector["connector_receipt_id"],
        "connector_receipt_hash": connector["connector_receipt_hash"],
        "company_matrix": list(company_matrix),
        "filing_selection_policy": layer3_sec_edgar_real_filing_acquisition_connector.REAL_COMPANY_DISCOVERY_POLICY,
        "filing_validation_records": records,
        "product_utility_matrix": matrix,
        "diagnostics": diagnostics,
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "request_id_hash": _sha256_text(request_id),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt["validation_receipt_id"])
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_real_company_corpus_validation_status(validation_receipt_id: str) -> dict[str, Any]:
    receipt = _read_verified_receipt(validation_receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-real-company-corpus-validation-status-{receipt['validation_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def _filing_validation_records(connector: Mapping[str, Any], *, request_id: str, db: Session) -> list[dict[str, Any]]:
    examples = {
        str(item.get("example_id")): item
        for item in ((connector.get("corpus_manifest") or {}).get("example_records") or [])
        if isinstance(item, Mapping)
    }
    records: list[dict[str, Any]] = []
    for index, acquisition in enumerate(connector.get("acquisition_receipts") or [], start=1):
        if not isinstance(acquisition, Mapping):
            continue
        example_id = str(acquisition.get("example_id") or "")
        example = examples.get(example_id, {})
        record = _base_record(index=index, example=example, acquisition=acquisition)
        if "html_inline_xbrl_classified_not_parsed" in list(example.get("source_family_roles") or []):
            record.update(_run_html_inline_xbrl_path(connector, example, acquisition, request_id=request_id, db=db))
        else:
            record["supported_degraded_blocked"] = "degraded_or_blocked"
            record["failure_classification"] = "parser_family"
            record["gaps_found"].append("html_inline_xbrl_source_family_not_classified")
        record["record_hash"] = stable_hash(record)
        records.append(record)
    return records


def _run_html_inline_xbrl_path(
    connector: Mapping[str, Any],
    example: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    *,
    request_id: str,
    db: Session,
) -> dict[str, Any]:
    outputs: dict[str, Any] = {"outputs_produced": [], "authority_hashes": {}}
    try:
        parser = layer3_sec_edgar_html_inline_xbrl_parser.parse_sec_edgar_html_inline_xbrl_source_family(
            {
                "client_request_id": f"{request_id}-{example['example_id']}-parser",
                "parser_mode": layer3_sec_edgar_html_inline_xbrl_parser.PARSER_MODE,
                "operator_decision": layer3_sec_edgar_html_inline_xbrl_parser.OPERATOR_DECISION,
                "connector_receipt_id": connector["connector_receipt_id"],
                "connector_receipt_hash": connector["connector_receipt_hash"],
                "connector_example_id": example["example_id"],
                "live_source_artifact_receipt_id": acquisition["live_source_artifact_receipt_id"],
                "live_source_artifact_receipt_hash": acquisition["live_source_artifact_receipt_hash"],
                "expected_source_artifact_receipt_hash": acquisition["source_artifact_receipt"][
                    "source_artifact_receipt_hash"
                ],
                "operator_confirmation": True,
            }
        )
        fact = layer3_sec_edgar_html_inline_xbrl_fact_authority.derive_sec_edgar_html_inline_xbrl_fact_authority(
            _fact_authority_payload(request_id, example, parser)
        )
        bridge = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.prepare_sec_edgar_html_inline_xbrl_fact_material_bridge(
            _fact_material_bridge_payload(request_id, example, parser, fact),
            db,
        )
        classification = (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification
            .classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates(
                _statement_classification_payload(request_id, example, parser, fact, bridge)
            )
        )
        product = (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product
            .build_sec_edgar_html_inline_xbrl_statement_candidate_product_evidence(
                _product_payload(request_id, example, classification)
            )
        )
        preview = (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review
            .preview_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review(
                _package_review_payload(request_id, example, product)
            )
        )
        construction = (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction
            .commit_sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction(
                _package_construction_payload(request_id, example, preview)
            )
        )
        submit = (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit
            .submit_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review(
                _package_submit_payload(request_id, example, construction)
            )
        )
        handoff = (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare
            .prepare_sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export(
                _handoff_payload(request_id, example, submit)
            )
        )
    except Layer3WorkbenchError as exc:
        return {
            **outputs,
            "supported_degraded_blocked": "blocked",
            "failure_classification": _failure_classification(exc.error_code),
            "gaps_found": [exc.error_code],
            "operator_usefulness": "diagnostic_block_recorded",
        }
    outputs["outputs_produced"] = [
        "parser",
        "fact_authority",
        "fact_material_bridge",
        "statement_classification",
        "statement_candidate_product",
        "package_review_preview",
        "package_construction_commit",
        "package_review_submit",
        "handoff_export_prepare",
    ]
    outputs["authority_hashes"] = {
        "parser_receipt_hash": parser["parser_receipt_hash"],
        "fact_authority_receipt_hash": fact["fact_authority_receipt_hash"],
        "fact_inventory_hash": fact["fact_inventory_hash"],
        "fact_material_bridge_receipt_hash": bridge["fact_material_bridge_receipt_hash"],
        "statement_classification_receipt_hash": classification["statement_classification_receipt_hash"],
        "downstream_product_receipt_hash": product["downstream_product_receipt_hash"],
        "package_review_preview_receipt_hash": preview["package_review_preview_receipt_hash"],
        "package_construction_receipt_hash": construction["package_construction_receipt_hash"],
        "package_review_submit_receipt_hash": submit["package_review_submit_receipt_hash"],
        "handoff_export_prepare_receipt_hash": handoff["handoff_export_prepare_receipt_hash"],
    }
    outputs["order_evidence"] = {
        "document_order_hash": parser["content_order_hash"],
        "fact_source_order_inventory": fact["fact_inventory_hash"],
        "statement_candidate_order": classification["classification_order_hash"],
        "package_artifact_order_hash": construction["package_payload_order_hash"],
    }
    outputs["supported_degraded_blocked"] = "supported"
    outputs["failure_classification"] = None
    outputs["gaps_found"] = []
    outputs["operator_usefulness"] = "product_path_validated"
    return outputs


def _base_record(index: int, example: Mapping[str, Any], acquisition: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_index": index,
        "example_id": str(example.get("example_id") or acquisition.get("example_id") or ""),
        "ticker_hash": example.get("ticker_hash"),
        "cik_hash": str(example.get("cik_hash") or ""),
        "company_name_hash": example.get("company_name_hash"),
        "form_type": str(example.get("form_type") or ""),
        "filing_date": str(example.get("filing_date") or ""),
        "report_period_present": bool(example.get("report_period_present")),
        "primary_document_hash": example.get("primary_document_hash"),
        "source_artifact_hash": (acquisition.get("source_artifact_receipt") or {}).get("content_sha256"),
        "source_family": str(example.get("source_family") or ""),
        "source_family_roles": list(example.get("source_family_roles") or []),
        "primary_document_family": str(example.get("primary_document_family") or ""),
        "supported_degraded_blocked": "not_evaluated",
        "outputs_produced": [],
        "authority_hashes": {},
        "order_evidence": {},
        "gaps_found": [],
        "operator_usefulness": "not_evaluated",
    }


def _fact_authority_payload(request_id: str, example: Mapping[str, Any], parser: Mapping[str, Any]) -> dict[str, Any]:
    identity = parser["identity_binding"]
    return {
        "client_request_id": f"{request_id}-{example['example_id']}-fact-authority",
        "fact_authority_mode": layer3_sec_edgar_html_inline_xbrl_fact_authority.FACT_AUTHORITY_MODE,
        "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_authority.OPERATOR_DECISION,
        "parser_receipt_id": parser["parser_receipt_id"],
        "parser_receipt_hash": parser["parser_receipt_hash"],
        "expected_connector_receipt_hash": parser["connector_receipt_hash"],
        "expected_live_source_artifact_receipt_hash": parser["live_source_artifact_receipt_hash"],
        "expected_source_artifact_receipt_hash": parser["source_artifact_receipt_hash"],
        "expected_content_sha256": identity["content_sha256"],
        "expected_primary_document_hash": identity["primary_document_hash"],
        "expected_document_inventory_hash": parser["document_inventory_hash"],
        "expected_content_order_hash": parser["content_order_hash"],
        "expected_table_candidate_inventory_hash": parser["table_candidate_inventory_hash"],
        "expected_inline_xbrl_marker_inventory_hash": parser["inline_xbrl_marker_inventory_hash"],
        "operator_confirmation": True,
    }


def _fact_material_bridge_payload(
    request_id: str,
    example: Mapping[str, Any],
    parser: Mapping[str, Any],
    fact: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _fact_authority_payload(request_id, example, parser)
    payload.pop("fact_authority_mode")
    payload["client_request_id"] = f"{request_id}-{example['example_id']}-fact-material-bridge"
    payload["bridge_mode"] = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.BRIDGE_MODE
    payload["operator_decision"] = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.OPERATOR_DECISION
    payload["fact_authority_receipt_id"] = fact["fact_authority_receipt_id"]
    payload["fact_authority_receipt_hash"] = fact["fact_authority_receipt_hash"]
    payload["expected_fact_inventory_hash"] = fact["fact_inventory_hash"]
    payload["expected_diagnostics_hash"] = fact["diagnostics_hash"]
    payload["rollback_confirmed"] = True
    payload["operator_confirmed"] = True
    payload.pop("operator_confirmation")
    return payload


def _statement_classification_payload(
    request_id: str,
    example: Mapping[str, Any],
    parser: Mapping[str, Any],
    fact: Mapping[str, Any],
    bridge: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _fact_material_bridge_payload(request_id, example, parser, fact)
    payload["client_request_id"] = f"{request_id}-{example['example_id']}-statement-classification"
    payload["classification_mode"] = layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.CLASSIFICATION_MODE
    payload["operator_decision"] = layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.OPERATOR_DECISION
    payload["fact_material_bridge_receipt_id"] = bridge["fact_material_bridge_receipt_id"]
    payload["fact_material_bridge_receipt_hash"] = bridge["fact_material_bridge_receipt_hash"]
    payload["expected_materialization_receipt_hash"] = bridge["materialization_receipt_hash"]
    payload["expected_dataset_version_hash"] = bridge["dataset_version_hash"]
    payload["expected_gate_b_decision_manifest_id"] = bridge["gate_b_decision_manifest_id"]
    payload["operator_confirmation"] = True
    payload.pop("bridge_mode")
    payload.pop("parser_receipt_id")
    payload.pop("parser_receipt_hash")
    payload.pop("rollback_confirmed")
    payload.pop("operator_confirmed")
    return payload


def _product_payload(request_id: str, example: Mapping[str, Any], classification: Mapping[str, Any]) -> dict[str, Any]:
    hashes = classification["authority_hashes"]
    return {
        "client_request_id": f"{request_id}-{example['example_id']}-product",
        "product_mode": layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product.PRODUCT_MODE,
        "operator_decision": layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product.OPERATOR_DECISION,
        "statement_classification_receipt_id": classification["statement_classification_receipt_id"],
        "statement_classification_receipt_hash": classification["statement_classification_receipt_hash"],
        "expected_fact_authority_receipt_hash": classification["fact_authority_receipt_hash"],
        "expected_fact_material_bridge_receipt_hash": classification["fact_material_bridge_receipt_hash"],
        "expected_parser_receipt_hash": classification["parser_receipt_hash"],
        "expected_connector_receipt_hash": hashes["connector_receipt_hash"],
        "expected_live_source_artifact_receipt_hash": hashes["live_source_artifact_receipt_hash"],
        "expected_source_artifact_receipt_hash": hashes["source_artifact_receipt_hash"],
        "expected_content_sha256": hashes["content_sha256"],
        "expected_primary_document_hash": hashes["primary_document_hash"],
        "expected_document_inventory_hash": hashes["document_inventory_hash"],
        "expected_content_order_hash": hashes["content_order_hash"],
        "expected_table_candidate_inventory_hash": hashes["table_candidate_inventory_hash"],
        "expected_inline_xbrl_marker_inventory_hash": hashes["inline_xbrl_marker_inventory_hash"],
        "expected_fact_inventory_hash": hashes["fact_inventory_hash"],
        "expected_classification_inventory_hash": classification["classification_inventory_hash"],
        "expected_classification_order_hash": classification["classification_order_hash"],
        "expected_statement_group_inventory_hash": classification["statement_group_inventory_hash"],
        "expected_unclassified_fact_inventory_hash": classification["unclassified_fact_inventory_hash"],
        "expected_classification_diagnostics_hash": classification["classification_diagnostics_hash"],
        "expected_materialization_receipt_hash": hashes["materialization_receipt_hash"],
        "expected_dataset_version_hash": hashes["dataset_version_hash"],
        "expected_gate_b_decision_manifest_id": hashes["gate_b_decision_manifest_id"],
        "operator_confirmation": True,
    }


def _package_review_payload(request_id: str, example: Mapping[str, Any], product: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "client_request_id": f"{request_id}-{example['example_id']}-package-review",
        "package_review_mode": (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review
            .PACKAGE_REVIEW_MODE
        ),
        "operator_decision": (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review
            .OPERATOR_DECISION
        ),
        "downstream_product_receipt_id": product["downstream_product_receipt_id"],
        "downstream_product_receipt_hash": product["downstream_product_receipt_hash"],
        "expected_statement_classification_receipt_hash": product["statement_classification_receipt_hash"],
        "expected_fact_authority_receipt_hash": product["fact_authority_receipt_hash"],
        "expected_fact_material_bridge_receipt_hash": product["fact_material_bridge_receipt_hash"],
        "expected_parser_receipt_hash": product["parser_receipt_hash"],
        "expected_product_manifest_hash": product["product_manifest_hash"],
        "expected_statement_candidate_product_hash": product["statement_candidate_product_hash"],
        "expected_product_order_hash": product["product_order_hash"],
        "expected_inspection_summary_hash": product["inspection_summary_hash"],
        "expected_redaction_manifest_hash": product["redaction_manifest_hash"],
        "expected_downstream_readiness_hash": product["downstream_readiness_hash"],
        "operator_confirmation": True,
    }


def _package_construction_payload(
    request_id: str,
    example: Mapping[str, Any],
    preview: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "client_request_id": f"{request_id}-{example['example_id']}-package-construction",
        "package_construction_mode": (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction
            .PACKAGE_CONSTRUCTION_MODE
        ),
        "operator_decision": (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction
            .OPERATOR_DECISION
        ),
        "package_review_preview_receipt_id": preview["package_review_preview_receipt_id"],
        "package_review_preview_receipt_hash": preview["package_review_preview_receipt_hash"],
        "expected_candidate_package_manifest_hash": preview["candidate_package_manifest_hash"],
        "expected_review_readiness_hash": preview["review_readiness_hash"],
        "expected_package_order_hash": preview["package_order_hash"],
        "expected_redaction_manifest_hash": preview["redaction_manifest_hash"],
        "expected_downstream_product_receipt_hash": preview["downstream_product_receipt_hash"],
        "expected_statement_classification_receipt_hash": preview["statement_classification_receipt_hash"],
        "expected_fact_authority_receipt_hash": preview["fact_authority_receipt_hash"],
        "expected_fact_material_bridge_receipt_hash": preview["fact_material_bridge_receipt_hash"],
        "expected_parser_receipt_hash": preview["parser_receipt_hash"],
        "expected_product_manifest_hash": preview["product_manifest_hash"],
        "expected_statement_candidate_product_hash": preview["statement_candidate_product_hash"],
        "expected_product_order_hash": preview["product_order_hash"],
        "expected_inspection_summary_hash": preview["inspection_summary_hash"],
        "expected_downstream_readiness_hash": preview["downstream_readiness_hash"],
        "operator_confirmation": True,
    }


def _package_submit_payload(
    request_id: str,
    example: Mapping[str, Any],
    construction: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "client_request_id": f"{request_id}-{example['example_id']}-package-submit",
        "package_review_submit_mode": (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit
            .PACKAGE_REVIEW_SUBMIT_MODE
        ),
        "operator_decision": (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit
            .OPERATOR_DECISION
        ),
        "review_decision": "approved",
        "package_construction_receipt_id": construction["package_construction_receipt_id"],
        "package_construction_receipt_hash": construction["package_construction_receipt_hash"],
        "expected_package_payload_manifest_hash": construction["package_payload_manifest_hash"],
        "expected_package_payload_order_hash": construction["package_payload_order_hash"],
        "expected_package_review_preview_receipt_hash": construction["package_review_preview_receipt_hash"],
        "expected_candidate_package_manifest_hash": construction["candidate_package_manifest_hash"],
        "expected_review_readiness_hash": construction["review_readiness_hash"],
        "expected_package_order_hash": construction["package_order_hash"],
        "expected_redaction_manifest_hash": construction["redaction_manifest_hash"],
        "expected_downstream_product_receipt_hash": construction["downstream_product_receipt_hash"],
        "expected_statement_classification_receipt_hash": construction["statement_classification_receipt_hash"],
        "expected_fact_authority_receipt_hash": construction["fact_authority_receipt_hash"],
        "expected_fact_material_bridge_receipt_hash": construction["fact_material_bridge_receipt_hash"],
        "expected_parser_receipt_hash": construction["parser_receipt_hash"],
        "expected_product_manifest_hash": construction["product_manifest_hash"],
        "expected_statement_candidate_product_hash": construction["statement_candidate_product_hash"],
        "expected_product_order_hash": construction["product_order_hash"],
        "expected_inspection_summary_hash": construction["inspection_summary_hash"],
        "expected_downstream_readiness_hash": construction["downstream_readiness_hash"],
        "operator_confirmation": True,
    }


def _handoff_payload(request_id: str, example: Mapping[str, Any], submit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "client_request_id": f"{request_id}-{example['example_id']}-handoff",
        "handoff_export_prepare_mode": (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare
            .HANDOFF_EXPORT_PREPARE_MODE
        ),
        "operator_decision": (
            layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare
            .OPERATOR_DECISION
        ),
        "package_review_submit_receipt_id": submit["package_review_submit_receipt_id"],
        "package_review_submit_receipt_hash": submit["package_review_submit_receipt_hash"],
        "expected_package_review_submit_record_ref": submit["package_review_submit_record_ref"],
        "expected_package_construction_receipt_hash": submit["package_construction_receipt_hash"],
        "expected_package_payload_manifest_hash": submit["package_payload_manifest_hash"],
        "expected_package_payload_order_hash": submit["package_payload_order_hash"],
        "expected_package_review_preview_receipt_hash": submit["package_review_preview_receipt_hash"],
        "expected_candidate_package_manifest_hash": submit["candidate_package_manifest_hash"],
        "expected_review_readiness_hash": submit["review_readiness_hash"],
        "expected_package_order_hash": submit["package_order_hash"],
        "expected_redaction_manifest_hash": submit["redaction_manifest_hash"],
        "expected_downstream_product_receipt_hash": submit["downstream_product_receipt_hash"],
        "expected_statement_classification_receipt_hash": submit["statement_classification_receipt_hash"],
        "expected_fact_authority_receipt_hash": submit["fact_authority_receipt_hash"],
        "expected_fact_material_bridge_receipt_hash": submit["fact_material_bridge_receipt_hash"],
        "expected_parser_receipt_hash": submit["parser_receipt_hash"],
        "expected_product_manifest_hash": submit["product_manifest_hash"],
        "expected_statement_candidate_product_hash": submit["statement_candidate_product_hash"],
        "expected_product_order_hash": submit["product_order_hash"],
        "expected_inspection_summary_hash": submit["inspection_summary_hash"],
        "expected_downstream_readiness_hash": submit["downstream_readiness_hash"],
        "operator_confirmation": True,
    }


def _product_utility_matrix(records: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "example_id": record["example_id"],
            "form_family": record["form_type"],
            "source_family": record["source_family"],
            "supported_degraded_blocked": record["supported_degraded_blocked"],
            "outputs_produced": list(record["outputs_produced"]),
            "gaps_found": list(record["gaps_found"]),
            "operator_usefulness": record["operator_usefulness"],
        }
        for record in records
    ]


def _diagnostics(connector: Mapping[str, Any], records: list[Mapping[str, Any]]) -> dict[str, Any]:
    states = [str(record.get("supported_degraded_blocked") or "") for record in records]
    return {
        "connector_authority_bound": True,
        "connector_receipt_hash": connector["connector_receipt_hash"],
        "real_company_count": len(connector.get("example_set", {}).get("company_matrix") or []),
        "filing_count": len(records),
        "supported_count": states.count("supported"),
        "blocked_count": states.count("blocked"),
        "degraded_or_blocked_count": states.count("degraded_or_blocked"),
        "generic_text_downgrade_performed": False,
        "candidate_b_pdf_only_routing_performed": False,
        "full_sec_support_claimed": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
    }


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    schema_id: str,
    idempotent_replay: bool,
) -> dict[str, Any]:
    response = {
        "schema_id": schema_id,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "ready",
        "validation_mode": VALIDATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "validation_state": receipt["validation_state"],
        "validation_receipt_id": receipt["validation_receipt_id"],
        "validation_receipt_hash": receipt["validation_receipt_hash"],
        "validation_receipt_ref": receipt["validation_receipt_ref"],
        "connector_receipt_id": receipt["connector_receipt_id"],
        "connector_receipt_hash": receipt["connector_receipt_hash"],
        "company_matrix": list(receipt["company_matrix"]),
        "filing_selection_policy": receipt["filing_selection_policy"],
        "filing_validation_records": list(receipt["filing_validation_records"]),
        "product_utility_matrix": list(receipt["product_utility_matrix"]),
        "diagnostics": dict(receipt["diagnostics"]),
        "cache": {
            "idempotent_replay": idempotent_replay,
            "network_request_made_by_validation_status": False,
        },
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "inspect real-company corpus validation status",
            "use supported records as SEC filing product-path evidence",
            "select explicit remediation slices for recorded blocked or degraded source families",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_real_company_corpus_validation_raw_authority_exposed",
            "SEC EDGAR real-company validation would expose raw path, URL, token, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _blocked_response(request_id: str, *, reasons: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "blocked",
        "validation_mode": VALIDATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "validation_state": BLOCKED_STATE,
        "blocked_reasons": reasons,
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
    }


def _failure_classification(error_code: str) -> str:
    if "parser" in error_code:
        return "parser_family"
    if "fact_authority" in error_code:
        return "fact_authority"
    if "statement_classification" in error_code:
        return "statement_classification"
    if "package_review" in error_code:
        return "package_review"
    if "handoff" in error_code:
        return "handoff_export"
    return "source_routing"


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_real_company_corpus_validation_forbidden_request_fields",
            "SEC EDGAR real-company validation does not admit caller paths, URLs, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, parser-expansion, frontend authority, or raw fact values.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_real_company_corpus_validation_unknown_field",
            "SEC EDGAR real-company validation fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_real_company_corpus_validation_schema_not_admitted",
            "SEC EDGAR real-company validation requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _company_matrix(value: Any) -> tuple[str, ...]:
    return layer3_sec_edgar_real_filing_acquisition_connector._normalise_company_matrix(
        value or layer3_sec_edgar_real_filing_acquisition_connector.DEFAULT_REAL_COMPANY_MATRIX
    )


def _read_receipt_by_hash(receipt_hash: str) -> dict[str, Any] | None:
    path = _receipt_path(f"{RECEIPT_PREFIX}-{receipt_hash[:24]}")
    if not path.exists():
        return None
    return _read_verified_receipt(path.stem)


def _read_verified_receipt(receipt_id: str) -> dict[str, Any]:
    receipt_id = str(receipt_id or "").strip()
    suffix = receipt_id.removeprefix(f"{RECEIPT_PREFIX}-")
    if not receipt_id.startswith(f"{RECEIPT_PREFIX}-") or len(suffix) != 24 or not _is_hex(suffix):
        _blocked(
            "sec_edgar_real_company_corpus_validation_receipt_id_invalid",
            "SEC EDGAR real-company validation status requires a server-issued validation receipt id.",
            http_status=400,
            blocked_fields=["sec_edgar_real_company_corpus_validation_receipt_id"],
        )
    path = _receipt_path(receipt_id)
    if not path.exists():
        _blocked(
            "sec_edgar_real_company_corpus_validation_receipt_missing",
            "SEC EDGAR real-company validation receipt was not found.",
            http_status=404,
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_real_company_corpus_validation_receipt_unreadable",
            "SEC EDGAR real-company validation receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("validation_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_real_company_corpus_validation_receipt_invalid",
            "SEC EDGAR real-company validation receipt is invalid or mismatched.",
            http_status=409,
        )
    if receipt.get("validation_receipt_hash") != suffix + receipt.get("validation_receipt_hash", "")[24:]:
        _blocked(
            "sec_edgar_real_company_corpus_validation_receipt_hash_mismatch",
            "SEC EDGAR real-company validation receipt hash is stale or mismatched.",
            http_status=409,
        )
    return receipt


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["validation_receipt_id"]))
    if target.exists():
        _read_verified_receipt(target.stem)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    path = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_real_company_corpus_validation_request_binding_unreadable",
            "SEC EDGAR real-company validation request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_real_company_corpus_validation_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "validation_basis_hash": basis_hash,
        "validation_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("validation_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_real_company_corpus_validation_request_binding_conflict",
                "SEC EDGAR real-company validation request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _negative_invariants() -> dict[str, bool]:
    return {
        "raw_url_exposed": False,
        "raw_local_path_exposed": False,
        "artifact_bytes_exposed": False,
        "raw_fact_values_exposed": False,
        "candidate_b_pdf_only_routing_performed": False,
        "generic_text_downgrade_performed": False,
        "unauthorized_parser_expansion_enabled": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
    }


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in FORBIDDEN_REQUEST_FIELDS:
                found.append(child)
            found.extend(_find_forbidden_nested_fields(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_forbidden_nested_fields(item, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        text = value.strip()
        if text.startswith(("http://", "https://", "file://", "\\\\", "/tmp/", "/var/", "/home/")) or _LOCAL_PATH_RE.match(text):
            found.append(prefix or "request_body")
    return sorted(set(found))


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        text = value.strip()
        return text.startswith(("http://", "https://", "file://", "\\\\", "/tmp/", "/var/", "/home/")) or bool(
            _LOCAL_PATH_RE.match(text)
        )
    return False


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _request_bindings_dir() -> Path:
    return _root() / "requests"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_real_company_corpus_validation_storage_root_unavailable",
            "SEC EDGAR real-company validation requires the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _reason(reason: str, **details: Any) -> dict[str, Any]:
    return {"reason": reason, **details}


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            "sec_edgar_real_company_corpus_validation_required_field_missing",
            "A required SEC EDGAR real-company validation field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_real_company_corpus_validation_{key}_not_admitted",
            "SEC EDGAR real-company validation request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _is_hex(value: str) -> bool:
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        status="blocked",
        http_status=http_status,
        blocked_fields=blocked_fields or [],
    )
