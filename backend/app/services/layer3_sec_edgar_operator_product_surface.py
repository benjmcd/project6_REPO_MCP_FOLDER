from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_delivery_status_provenance,
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge,
    layer3_sec_edgar_operator_inspection,
    layer3_sec_edgar_real_company_corpus_validation,
)
from app.services.layer3_sec_edgar_ref_safety import contains_forbidden_ref
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_operator_product_surface.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_operator_product_surface_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_operator_product_surface_status.v1"
SCHEMA_VERSION = 1
SURFACE_MODE = "sec_edgar_operator_product_surface_runtime_v1"
OPERATOR_DECISION = "render_sec_edgar_operator_product_surface"
READY_STATE = "sec_edgar_operator_product_surface_ready"
BLOCKED_STATE = "sec_edgar_operator_product_surface_blocked"
RECEIPT_PREFIX = "sec-edgar-operator-product-surface"
RECEIPT_DIR = "layer3-sec-edgar-operator-product-surface"
REDACTION_POLICY_ID = "sec_edgar_operator_product_surface_redaction_v1"
RENDERED_MODE = "rendered_sec_edgar_operator_product_surface_control"
VALUE_REVEAL_POLICY_ID = "sec_edgar_operator_surface_gated_value_reveal_v1"
VALUE_REVEAL_MAX_RECORDS_DEFAULT = 25
VALUE_REVEAL_MAX_RECORDS_LIMIT = 50
EXPECTED_COMPANY_MATRIX = ("MSFT", "STLD", "SONY", "CCJ")
OPERATOR_PRODUCT_SURFACE_BREADTH_SELECTION_VERSION = "sec_edgar_operator_product_surface_breadth_selection_v1"
OPERATOR_PRODUCT_SURFACE_BREADTH_SELECTED_MATRIX = ("XOM", "PFE", "UAL", "T")
OPERATOR_PRODUCT_SURFACE_BREADTH_SELECTED_PROFILE_TAGS = (
    "energy_major",
    "pharmaceutical_life_sciences",
    "airline_transport",
    "telecom_media",
    "debt_intensive",
    "commodity_exposure",
)
OPERATOR_PRODUCT_SURFACE_BREADTH_RUNTIME_VERSION = "sec_edgar_operator_product_surface_breadth_runtime_v1"
OPERATOR_PRODUCT_SURFACE_BREADTH_RUNTIME_ENABLED = True
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_SELECTION_VERSION = "sec_edgar_durable_delivery_archive_selection_v1"
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_SELECTED_RUNTIME_TARGET = "sec_edgar_durable_delivery_archive_runtime_v1"
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_SELECTED_SERVICE = (
    "backend/app/services/layer3_sec_edgar_durable_delivery_archive.py"
)
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_SELECTED_ENDPOINT = (
    "/api/v1/layer3/source/sec-edgar/real-company-corpus/durable-delivery/archive"
)
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_SELECTED_STATUS_ENDPOINT = (
    "/api/v1/layer3/source/sec-edgar/real-company-corpus/durable-delivery/archive/status/"
    "{sec_edgar_durable_delivery_archive_receipt_id}"
)
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_SELECTED_MODE = "sec_edgar_durable_delivery_archive_v1"
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_SELECTED_OPERATOR_DECISION = (
    "archive_sec_edgar_operator_product_surface_delivery_package"
)
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_SELECTED_INPUT_AUTHORITY = (
    "sec_edgar_operator_product_surface_receipt_id",
    "sec_edgar_operator_product_surface_receipt_hash",
)
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_RUNTIME_ENABLED = True

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "surface_mode",
    "operator_decision",
    "sec_edgar_operator_inspection_receipt_id",
    "sec_edgar_operator_inspection_receipt_hash",
    "operator_confirmation",
    "value_reveal_policy",
    "value_reveal_confirmation",
    "value_reveal_max_records",
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
    "download_url",
    "public_url",
    "signed_url",
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
    "accession",
    "accession_number",
    "company_name",
    "ticker",
    "value",
    "value_text",
    "fact_value",
    "raw_fact_value",
}
PRODUCT_VIEW_NAMES = (
    "company_form_matrix",
    "filing_identity",
    "source_family",
    "statement_candidates",
    "fact_inventory",
    "fact_deduplication_conflict_diagnostics",
    "cross_company_comparability_readiness_audit",
    "semantic_profile",
    "statement_role_quality_profile",
    "period_unit_context_dimension_profile",
    "extension_taxonomy_retention_profile",
    "standard_concept_mapping_profile",
    "extension_unclassified_facts",
    "quality_gaps",
    "diagnostics_loss_report",
    "package_review_handoff_state",
    "operator_inspection_status_links",
)


def render_sec_edgar_operator_product_surface(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    _ = db
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "surface_mode", SURFACE_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    if request.get("operator_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason("sec_edgar_operator_product_surface_operator_confirmation_missing")],
        )

    operator_receipt_id = _required(request, "sec_edgar_operator_inspection_receipt_id")
    expected_operator_hash = _required(request, "sec_edgar_operator_inspection_receipt_hash")
    if not _is_sha256(expected_operator_hash):
        return _blocked_response(
            request_id=request_id,
            reasons=[
                _reason(
                    "sec_edgar_operator_product_surface_operator_inspection_hash_invalid",
                    blocked_fields=["sec_edgar_operator_inspection_receipt_hash"],
                )
            ],
        )
    try:
        operator = layer3_sec_edgar_operator_inspection._read_verified_receipt(operator_receipt_id)
    except Layer3WorkbenchError as exc:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason(exc.error_code, message=exc.message, blocked_fields=list(exc.blocked_fields))],
        )
    if str(operator.get("operator_inspection_receipt_hash") or "") != expected_operator_hash:
        return _blocked_response(
            request_id=request_id,
            operator=operator,
            reasons=[
                _reason(
                    "sec_edgar_operator_product_surface_operator_inspection_hash_mismatch",
                    blocked_fields=[
                        "sec_edgar_operator_inspection_receipt_id",
                        "sec_edgar_operator_inspection_receipt_hash",
                    ],
                )
            ],
        )

    try:
        delivery = layer3_sec_edgar_delivery_status_provenance._read_verified_receipt(
            str(operator["delivery_status_provenance_receipt_id"])
        )
        validation = layer3_sec_edgar_real_company_corpus_validation._read_verified_receipt(
            str(delivery["validation_receipt_id"])
        )
    except Layer3WorkbenchError as exc:
        return _blocked_response(
            request_id=request_id,
            operator=operator,
            reasons=[_reason(exc.error_code, message=exc.message, blocked_fields=list(exc.blocked_fields))],
        )

    readiness_reasons = _readiness_reasons(operator, delivery, validation)
    if readiness_reasons:
        return _blocked_response(
            request_id=request_id,
            operator=operator,
            delivery=delivery,
            validation=validation,
            reasons=readiness_reasons,
        )

    product_views = _product_views(operator, delivery, validation)
    value_reveal = _value_reveal_surface(request, validation)
    if value_reveal["value_reveal_requested"] and value_reveal["value_reveal_state"] != "ready":
        return _blocked_response(
            request_id=request_id,
            operator=operator,
            delivery=delivery,
            validation=validation,
            reasons=list(value_reveal["blocked_reasons"]),
        )
    surface_rollup = _surface_rollup(product_views)
    authority_chain = _authority_chain(operator, delivery, validation, product_views)
    receipt_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "surface_mode": SURFACE_MODE,
            "operator_inspection_receipt_hash": operator["operator_inspection_receipt_hash"],
            "delivery_status_provenance_receipt_hash": delivery["delivery_status_provenance_receipt_hash"],
            "validation_receipt_hash": validation["validation_receipt_hash"],
            "product_views_hash": stable_hash(product_views),
            "value_reveal_hash": stable_hash(value_reveal),
            "surface_rollup_hash": stable_hash(surface_rollup),
            "authority_chain_hash": stable_hash(authority_chain),
        }
    )
    binding = _read_request_binding(request_id)
    if binding and binding.get("operator_product_surface_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_operator_product_surface_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR operator product surface basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["operator_product_surface_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "surface_mode": SURFACE_MODE,
        "rendered_mode": RENDERED_MODE,
        "operator_decision": OPERATOR_DECISION,
        "operator_product_surface_state": READY_STATE,
        "operator_product_surface_receipt_id": f"{RECEIPT_PREFIX}-{receipt_hash[:24]}",
        "operator_product_surface_receipt_hash": receipt_hash,
        "operator_product_surface_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "operator_inspection_receipt_id": operator["operator_inspection_receipt_id"],
        "operator_inspection_receipt_hash": operator["operator_inspection_receipt_hash"],
        "delivery_status_provenance_receipt_id": delivery["delivery_status_provenance_receipt_id"],
        "delivery_status_provenance_receipt_hash": delivery["delivery_status_provenance_receipt_hash"],
        "validation_receipt_hash": validation["validation_receipt_hash"],
        "connector_receipt_hash": validation["connector_receipt_hash"],
        "product_views": product_views,
        "value_reveal": value_reveal,
        "surface_rollup": surface_rollup,
        "authority_chain": authority_chain,
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "request_id_hash": _sha256_text(request_id),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt["operator_product_surface_receipt_id"])
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_operator_product_surface_status(
    operator_product_surface_receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(operator_product_surface_receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-operator-product-surface-status-{receipt['operator_product_surface_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def _readiness_reasons(
    operator: Mapping[str, Any],
    delivery: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    if operator.get("operator_inspection_state") != layer3_sec_edgar_operator_inspection.READY_STATE:
        reasons.append(_reason("sec_edgar_operator_product_surface_operator_inspection_not_ready"))
    if delivery.get("delivery_status_provenance_state") != layer3_sec_edgar_delivery_status_provenance.READY_STATE:
        reasons.append(_reason("sec_edgar_operator_product_surface_delivery_status_provenance_not_ready"))
    if validation.get("validation_state") != layer3_sec_edgar_real_company_corpus_validation.READY_STATE:
        reasons.append(_reason("sec_edgar_operator_product_surface_validation_not_ready"))
    if tuple(validation.get("company_matrix") or ()) not in _admitted_company_matrices():
        reasons.append(_reason("sec_edgar_operator_product_surface_company_matrix_mismatch"))
    if operator.get("delivery_status_provenance_receipt_hash") != delivery.get("delivery_status_provenance_receipt_hash"):
        reasons.append(_reason("sec_edgar_operator_product_surface_delivery_hash_chain_mismatch"))
    if delivery.get("validation_receipt_hash") != validation.get("validation_receipt_hash"):
        reasons.append(_reason("sec_edgar_operator_product_surface_validation_hash_chain_mismatch"))
    return reasons


def _admitted_company_matrices() -> tuple[tuple[str, ...], ...]:
    matrices = [EXPECTED_COMPANY_MATRIX]
    if OPERATOR_PRODUCT_SURFACE_BREADTH_RUNTIME_ENABLED:
        matrices.append(OPERATOR_PRODUCT_SURFACE_BREADTH_SELECTED_MATRIX)
    return tuple(matrices)


def _product_views(
    operator: Mapping[str, Any],
    delivery: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    validation_records = _records_by_index(validation.get("filing_validation_records") or [])
    delivery_records = _records_by_index(delivery.get("delivery_status_records") or [])
    operator_records = _records_by_index(operator.get("company_filing_inspection_matrix") or [])
    indexes = sorted(set(validation_records) | set(delivery_records) | set(operator_records))
    record_views = [
        _record_product_view(
            index,
            operator_records.get(index, {}),
            delivery_records.get(index, {}),
            validation_records.get(index, {}),
        )
        for index in indexes
    ]
    quality_gap_values = sorted(
        {
            str(gap)
            for view in record_views
            for gap in view["quality_gaps"]["quality_gaps"]
            if str(gap)
        }
    )
    return {
        "company_form_matrix": [
            {
                "record_index": view["record_index"],
                "ticker_hash": view["filing_identity"]["ticker_hash"],
                "company_name_hash": view["filing_identity"]["company_name_hash"],
                "form_type": view["filing_identity"]["form_type"],
                "filing_date": view["filing_identity"]["filing_date"],
                "source_family": view["source_family"]["source_family"],
                "inspection_status": view["operator_inspection_status_links"]["inspection_status"],
                "quality_assessment_status": view["quality_gaps"]["quality_assessment_status"],
                "quality_evidence_hash": view["quality_gaps"]["quality_evidence_hash"],
            }
            for view in record_views
        ],
        "filing_identity": [view["filing_identity"] for view in record_views],
        "source_family": _source_family_rollup(record_views),
        "statement_candidates": [view["statement_candidates"] for view in record_views],
        "fact_inventory": [view["fact_inventory"] for view in record_views],
        "fact_deduplication_conflict_diagnostics": [
            view["fact_deduplication_conflict_diagnostics"] for view in record_views
        ],
        "cross_company_comparability_readiness_audit": [
            view["cross_company_comparability_readiness_audit"] for view in record_views
        ],
        "semantic_profile": [view["semantic_profile"] for view in record_views],
        "statement_role_quality_profile": [view["statement_role_quality_profile"] for view in record_views],
        "period_unit_context_dimension_profile": [
            view["period_unit_context_dimension_profile"] for view in record_views
        ],
        "extension_taxonomy_retention_profile": [
            view["extension_taxonomy_retention_profile"] for view in record_views
        ],
        "standard_concept_mapping_profile": [
            view["standard_concept_mapping_profile"] for view in record_views
        ],
        "extension_unclassified_facts": [view["extension_unclassified_facts"] for view in record_views],
        "quality_gaps": {
            "distinct_quality_gaps": quality_gap_values,
            "financial_statement_semantics_finalized": False,
            "cross_company_comparability_admitted": False,
            "quality_gap_record_count": sum(len(view["quality_gaps"]["quality_gaps"]) for view in record_views),
            "records": [view["quality_gaps"] for view in record_views],
        },
        "diagnostics_loss_report": _diagnostics_loss_report(operator, delivery, validation, record_views),
        "package_review_handoff_state": [view["package_review_handoff_state"] for view in record_views],
        "operator_inspection_status_links": [view["operator_inspection_status_links"] for view in record_views],
    }


def _record_product_view(
    index: int,
    operator_record: Mapping[str, Any],
    delivery_record: Mapping[str, Any],
    validation_record: Mapping[str, Any],
) -> dict[str, Any]:
    quality = dict(validation_record.get("quality_evidence") or {})
    metrics = dict(quality.get("quality_metrics") or {})
    dimensions = dict(quality.get("quality_dimensions") or operator_record.get("quality_dimensions") or {})
    provenance_hashes = dict(delivery_record.get("provenance_hashes") or {})
    statement_role_counts = dict(metrics.get("statement_role_counts") or {})
    quality_gaps = list(quality.get("quality_gaps") or operator_record.get("quality_gaps") or [])
    source_family = str(operator_record.get("source_family") or delivery_record.get("source_family") or validation_record.get("source_family") or "")
    form_type = str(operator_record.get("form_type") or delivery_record.get("form_type") or validation_record.get("form_type") or "")
    filing_date = str(operator_record.get("filing_date") or delivery_record.get("filing_date") or validation_record.get("filing_date") or "")
    return {
        "record_index": index,
        "filing_identity": {
            "record_index": index,
            "example_id_hash": stable_hash({"example_id": str(validation_record.get("example_id") or delivery_record.get("example_id") or "")}),
            "ticker_hash": operator_record.get("ticker_hash") or delivery_record.get("ticker_hash") or validation_record.get("ticker_hash"),
            "cik_hash": operator_record.get("cik_hash") or delivery_record.get("cik_hash") or validation_record.get("cik_hash"),
            "company_name_hash": operator_record.get("company_name_hash") or delivery_record.get("company_name_hash") or validation_record.get("company_name_hash"),
            "form_type": form_type,
            "filing_date": filing_date,
            "validation_record_hash": validation_record.get("record_hash") or operator_record.get("validation_record_hash"),
            "delivery_status_record_hash": delivery_record.get("delivery_status_record_hash") or operator_record.get("delivery_status_record_hash"),
            "operator_inspection_record_hash": operator_record.get("operator_inspection_record_hash"),
            "redacted_identity_projection": True,
        },
        "source_family": {
            "record_index": index,
            "source_family": source_family,
            "primary_document_family_hash": stable_hash({"primary_document_family": str(validation_record.get("primary_document_family") or "")}),
            "source_family_roles_hash": stable_hash(list(validation_record.get("source_family_roles") or [])),
        },
        "statement_candidates": {
            "record_index": index,
            "statement_role_counts": statement_role_counts,
            "statement_group_inventory_hash": metrics.get("statement_group_inventory_hash"),
            "statement_candidate_product_hash": metrics.get("statement_candidate_product_hash"),
            "statement_candidate_usefulness": dimensions.get("statement_candidate_usefulness"),
            "classification_inventory_hash": metrics.get("classification_inventory_hash"),
            "classification_order_hash": metrics.get("classification_order_hash"),
        },
        "fact_inventory": {
            "record_index": index,
            "fact_count": metrics.get("fact_count"),
            "fact_inventory_hash": metrics.get("fact_inventory_hash"),
            "fact_diagnostics_hash": metrics.get("fact_diagnostics_hash"),
            "fact_context_unit_preservation": dimensions.get("fact_context_unit_preservation"),
            "period_unit_context_dimension_profile": dimensions.get("period_unit_context_dimension_profile"),
            "document_inventory_hash": metrics.get("document_inventory_hash"),
            "content_order_hash": metrics.get("content_order_hash"),
            "table_candidate_inventory_hash": metrics.get("table_candidate_inventory_hash"),
            "inline_xbrl_marker_inventory_hash": metrics.get("inline_xbrl_marker_inventory_hash"),
        },
        "fact_deduplication_conflict_diagnostics": {
            "record_index": index,
            "fact_deduplication_conflict_diagnostics_version": metrics.get(
                "fact_deduplication_conflict_diagnostics_version"
            )
            or "sec_edgar_fact_deduplication_conflict_diagnostics_v1",
            "fact_deduplication_conflict_diagnostics_hash": metrics.get(
                "fact_deduplication_conflict_diagnostics_hash"
            ),
            "fact_deduplication_conflict_diagnostics_status": metrics.get(
                "fact_deduplication_conflict_diagnostics_status"
            ),
            "profile_status": dimensions.get("fact_deduplication_conflict_diagnostics"),
            "fact_identity_group_count": metrics.get("fact_identity_group_count"),
            "fact_conflict_basis_group_count": metrics.get("fact_conflict_basis_group_count"),
            "exact_duplicate_fact_group_count": metrics.get("exact_duplicate_fact_group_count"),
            "exact_duplicate_fact_candidate_count": metrics.get("exact_duplicate_fact_candidate_count"),
            "conflicting_fact_group_count": metrics.get("conflicting_fact_group_count"),
            "conflicting_fact_candidate_count": metrics.get("conflicting_fact_candidate_count"),
            "exact_duplicate_fact_group_hashes_hash": metrics.get("exact_duplicate_fact_group_hashes_hash"),
            "conflicting_fact_group_hashes_hash": metrics.get("conflicting_fact_group_hashes_hash"),
            "fact_deduplication_performed": False,
            "fact_conflict_resolution_performed": False,
            "fact_values_dropped": False,
            "raw_values_returned": False,
            "final_financial_statement_semantics_claimed": False,
        },
        "semantic_profile": {
            "record_index": index,
            "semantic_profile_version": "sec_edgar_statement_semantic_profile_v1",
            "semantic_profile_inventory_hash": metrics.get("semantic_profile_inventory_hash"),
            "semantic_profile_assigned_count": metrics.get("semantic_profile_assigned_count"),
            "standard_taxonomy_fact_count": metrics.get("standard_taxonomy_fact_count"),
            "company_extension_fact_count": metrics.get("company_extension_fact_count"),
            "comparable_standard_fact_count": metrics.get("comparable_standard_fact_count"),
            "company_extension_unmapped_count": metrics.get("company_extension_unmapped_count"),
            "financial_statement_semantics": dimensions.get("financial_statement_semantics"),
            "cross_company_comparability": dimensions.get("cross_company_comparability"),
            "financial_statement_semantics_finalized": False,
            "cross_company_comparability_admitted": False,
        },
        "cross_company_comparability_readiness_audit": {
            "record_index": index,
            "cross_company_comparability_readiness_audit_version": metrics.get(
                "cross_company_comparability_readiness_audit_version"
            )
            or "sec_edgar_cross_company_comparability_readiness_audit_v1",
            "cross_company_comparability_readiness_audit_hash": metrics.get(
                "cross_company_comparability_readiness_audit_hash"
            ),
            "cross_company_comparability_readiness_status": metrics.get(
                "cross_company_comparability_readiness_status"
            ),
            "profile_status": dimensions.get("cross_company_comparability_readiness_audit"),
            "cross_company_comparability_readiness_blocker_count": metrics.get(
                "cross_company_comparability_readiness_blocker_count"
            ),
            "cross_company_comparability_readiness_blockers_hash": metrics.get(
                "cross_company_comparability_readiness_blockers_hash"
            ),
            "cross_company_comparability_ready": False,
            "cross_company_comparability_admitted": False,
            "comparability_normalization_performed": False,
            "period_unit_context_dimension_resolution_performed": False,
            "statement_role_semantics_finalized": False,
            "extension_taxonomy_mapping_performed": False,
            "standard_concept_normalization_performed": False,
            "fact_deduplication_performed": False,
            "fact_conflict_resolution_performed": False,
            "taxonomy_network_resolution_performed": False,
            "sec_companyfacts_api_called": False,
            "filing_specific_product_only": True,
        },
        "statement_role_quality_profile": {
            "record_index": index,
            "statement_role_quality_profile_version": metrics.get("statement_role_quality_profile_version")
            or "sec_edgar_statement_role_quality_profile_v1",
            "statement_role_quality_profile_hash": metrics.get("statement_role_quality_profile_hash"),
            "statement_role_quality_profile_assigned_count": metrics.get(
                "statement_role_quality_profile_assigned_count"
            ),
            "medium_statement_role_confidence_count": metrics.get("medium_statement_role_confidence_count"),
            "low_statement_role_confidence_count": metrics.get("low_statement_role_confidence_count"),
            "profile_status": dimensions.get("statement_role_quality_profile"),
            "taxonomy_network_resolution_performed": False,
            "presentation_linkbase_role_resolution_performed": False,
            "statement_role_semantics_finalized": False,
            "final_financial_statement_semantics_claimed": False,
        },
        "period_unit_context_dimension_profile": {
            "record_index": index,
            "period_unit_context_dimension_profile_version": metrics.get(
                "period_unit_context_dimension_profile_version"
            )
            or "sec_edgar_period_unit_context_dimension_profile_v1",
            "period_unit_context_dimension_profile_hash": metrics.get(
                "period_unit_context_dimension_profile_hash"
            ),
            "period_unit_context_dimension_profile_assigned_count": metrics.get(
                "period_unit_context_dimension_profile_assigned_count"
            ),
            "context_ref_hash_present_count": metrics.get("context_ref_hash_present_count"),
            "unit_ref_hash_present_count": metrics.get("unit_ref_hash_present_count"),
            "decimals_or_precision_present_count": metrics.get("decimals_or_precision_present_count"),
            "scale_or_format_present_count": metrics.get("scale_or_format_present_count"),
            "profile_status": dimensions.get("period_unit_context_dimension_profile"),
            "context_period_resolution_performed": False,
            "dimension_member_resolution_performed": False,
            "unit_normalization_performed": False,
            "final_period_unit_context_dimension_semantics_claimed": False,
        },
        "extension_taxonomy_retention_profile": {
            "record_index": index,
            "extension_taxonomy_retention_profile_version": metrics.get(
                "extension_taxonomy_retention_profile_version"
            )
            or "sec_edgar_extension_taxonomy_retention_profile_v1",
            "extension_taxonomy_retention_profile_hash": metrics.get(
                "extension_taxonomy_retention_profile_hash"
            ),
            "extension_taxonomy_retention_profile_assigned_count": metrics.get(
                "extension_taxonomy_retention_profile_assigned_count"
            ),
            "retained_company_extension_profile_count": metrics.get(
                "retained_company_extension_profile_count"
            ),
            "standard_taxonomy_retention_profile_count": metrics.get(
                "standard_taxonomy_retention_profile_count"
            ),
            "unknown_taxonomy_retention_profile_count": metrics.get(
                "unknown_taxonomy_retention_profile_count"
            ),
            "profile_status": dimensions.get("extension_taxonomy_retention_profile"),
            "extension_taxonomy_mapping_performed": False,
            "taxonomy_network_resolution_performed": False,
            "extension_taxonomy_facts_dropped": False,
            "final_financial_statement_semantics_claimed": False,
        },
        "standard_concept_mapping_profile": {
            "record_index": index,
            "standard_concept_mapping_profile_version": metrics.get(
                "standard_concept_mapping_profile_version"
            )
            or "sec_edgar_standard_concept_mapping_profile_v1",
            "standard_concept_mapping_profile_hash": metrics.get(
                "standard_concept_mapping_profile_hash"
            ),
            "standard_concept_mapping_profile_assigned_count": metrics.get(
                "standard_concept_mapping_profile_assigned_count"
            ),
            "standard_concept_profiled_count": metrics.get("standard_concept_profiled_count"),
            "issuer_extension_standard_concept_unmapped_count": metrics.get(
                "issuer_extension_standard_concept_unmapped_count"
            ),
            "unknown_taxonomy_standard_concept_unmapped_count": metrics.get(
                "unknown_taxonomy_standard_concept_unmapped_count"
            ),
            "profile_status": dimensions.get("standard_concept_mapping_profile"),
            "standard_concept_mapping_performed": False,
            "standard_concept_normalization_performed": False,
            "taxonomy_network_resolution_performed": False,
            "sec_companyfacts_api_called": False,
            "cross_company_comparability_admitted": False,
            "final_financial_statement_semantics_claimed": False,
        },
        "extension_unclassified_facts": {
            "record_index": index,
            "extension_fact_count": metrics.get("extension_fact_count"),
            "company_extension_fact_count": metrics.get("company_extension_fact_count"),
            "company_extension_unmapped_count": metrics.get("company_extension_unmapped_count"),
            "unknown_or_unclassified_count": metrics.get("unknown_or_unclassified_count"),
            "extension_fact_handling": dimensions.get("extension_fact_handling"),
            "classification_diagnostics_hash": metrics.get("classification_diagnostics_hash"),
        },
        "quality_gaps": {
            "record_index": index,
            "quality_assessment_status": quality.get("quality_assessment_status") or operator_record.get("quality_assessment_status"),
            "quality_dimensions": dimensions,
            "quality_gaps": quality_gaps,
            "quality_evidence_hash": quality.get("quality_evidence_hash") or operator_record.get("quality_evidence_hash"),
        },
        "package_review_handoff_state": {
            "record_index": index,
            "package_payload_manifest_hash": metrics.get("package_payload_manifest_hash"),
            "package_payload_order_hash": metrics.get("package_payload_order_hash"),
            "package_review_submit_receipt_hash": metrics.get("package_review_submit_receipt_hash") or provenance_hashes.get("package_review_submit_receipt_hash"),
            "handoff_export_prepare_receipt_hash": metrics.get("handoff_export_prepare_receipt_hash") or provenance_hashes.get("handoff_export_prepare_receipt_hash"),
            "handoff_export_prepare_status": delivery_record.get("handoff_export_prepare_status") or operator_record.get("handoff_export_prepare_status"),
            "delivery_readiness_status": delivery_record.get("delivery_readiness_status") or operator_record.get("delivery_readiness_status"),
            "package_review_handoff_coherence": dimensions.get("package_review_handoff_coherence"),
        },
        "operator_inspection_status_links": {
            "record_index": index,
            "inspection_status": operator_record.get("inspection_status"),
            "operator_inspection_record_hash": operator_record.get("operator_inspection_record_hash"),
            "delivery_status_record_hash": delivery_record.get("delivery_status_record_hash") or operator_record.get("delivery_status_record_hash"),
            "validation_record_hash": validation_record.get("record_hash") or operator_record.get("validation_record_hash"),
            "redacted_operator_projection": True,
        },
    }


def _records_by_index(records: Any) -> dict[int, Mapping[str, Any]]:
    indexed: dict[int, Mapping[str, Any]] = {}
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, Mapping):
            continue
        try:
            index = int(record.get("record_index") or 0)
        except (TypeError, ValueError):
            continue
        if index > 0:
            indexed[index] = record
    return indexed


def _source_family_rollup(record_views: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for view in record_views:
        source_family = str((view.get("source_family") or {}).get("source_family") or "")
        counts[source_family] = counts.get(source_family, 0) + 1
    return {
        "source_family_counts": counts,
        "source_family_count": len(counts),
        "source_family_hash": stable_hash(counts),
    }


def _diagnostics_loss_report(
    operator: Mapping[str, Any],
    delivery: Mapping[str, Any],
    validation: Mapping[str, Any],
    record_views: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "validation_diagnostics_hash": stable_hash(validation.get("diagnostics") or {}),
        "delivery_diagnostics_hash": stable_hash(delivery.get("diagnostics") or {}),
        "operator_inspection_summary_hash": stable_hash(operator.get("operator_inspection_summary") or {}),
        "blocked_or_degraded_delivery_gaps": list(operator.get("blocked_or_degraded_delivery_gaps") or []),
        "unclassified_record_count": sum(
            1
            for view in record_views
            if int((view.get("extension_unclassified_facts") or {}).get("unknown_or_unclassified_count") or 0) > 0
        ),
        "financial_statement_semantics_finalized": False,
        "cross_company_comparability_ready": False,
        "cross_company_comparability_admitted": False,
        "comparability_normalization_performed": False,
        "taxonomy_network_resolution_performed": False,
        "sec_companyfacts_api_called": False,
    }


def _value_reveal_surface(request: Mapping[str, Any], validation: Mapping[str, Any]) -> dict[str, Any]:
    if not any(key in request for key in ("value_reveal_policy", "value_reveal_confirmation", "value_reveal_max_records")):
        return _value_reveal_disabled()
    if not settings.layer3_sec_edgar_arelle_value_reveal_enabled:
        return _value_reveal_blocked(
            "sec_edgar_operator_product_surface_value_reveal_flag_disabled",
        )
    return _value_reveal_blocked(
        "sec_edgar_operator_product_surface_value_reveal_requires_sibling_endpoint",
        diagnostics=[
            {
                "sibling_endpoint": "/source/sec-edgar/real-company-corpus/operator-value-reveal",
                "default_operator_product_surface_remains_redacted": True,
            }
        ],
    )


def _value_reveal_disabled() -> dict[str, Any]:
    return {
        "schema_id": "layer3.sec_edgar_operator_surface_value_reveal.v1",
        "value_reveal_policy": VALUE_REVEAL_POLICY_ID,
        "value_reveal_requested": False,
        "value_reveal_state": "not_requested",
        "governed_operator_fact_values_revealed": False,
        "revealed_value_count": 0,
        "revealed_values": [],
    }


def _value_reveal_blocked(reason: str, *, diagnostics: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "schema_id": "layer3.sec_edgar_operator_surface_value_reveal.v1",
        "value_reveal_policy": VALUE_REVEAL_POLICY_ID,
        "value_reveal_requested": True,
        "value_reveal_state": "blocked",
        "governed_operator_fact_values_revealed": False,
        "revealed_value_count": 0,
        "revealed_values": [],
        "blocked_reasons": [{"reason": reason, "diagnostics": diagnostics or []}],
    }


def _value_reveal_max_records(value: Any) -> int:
    try:
        count = int(value or VALUE_REVEAL_MAX_RECORDS_DEFAULT)
    except (TypeError, ValueError):
        _blocked(
            "sec_edgar_operator_product_surface_value_reveal_max_records_invalid",
            "SEC EDGAR operator value reveal requires a positive bounded max record count.",
            blocked_fields=["value_reveal_max_records"],
        )
    if count <= 0 or count > VALUE_REVEAL_MAX_RECORDS_LIMIT:
        _blocked(
            "sec_edgar_operator_product_surface_value_reveal_max_records_not_admitted",
            "SEC EDGAR operator value reveal is capped for this slice.",
            blocked_fields=["value_reveal_max_records"],
        )
    return count


def _bridge_value_rows(bridge_response: Mapping[str, Any], *, record_index: int) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    dataset_version_id = str(bridge_response.get("dataset_version_id") or "")
    if not dataset_version_id:
        return [], [{"record_index": record_index, "reason": "dataset_version_id_missing"}]
    csv_path = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge._datasets_dir() / f"{dataset_version_id}.csv"
    try:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle)), []
    except FileNotFoundError:
        return [], [{"record_index": record_index, "reason": "dataset_version_rows_missing"}]
    except (OSError, csv.Error):
        return [], [{"record_index": record_index, "reason": "dataset_version_rows_unreadable"}]


def _row_is_standard_numeric_non_dimensional(row: Mapping[str, Any]) -> bool:
    namespace = str(row.get("concept_namespace") or "")
    if "fasb.org/us-gaap" not in namespace and "xbrl.sec.gov/dei" not in namespace:
        return False
    if str(row.get("concept_standard") or "").strip().lower() not in {"true", "1"}:
        return False
    if str(row.get("explicit_dimension_count") or "0") not in {"", "0"}:
        return False
    if str(row.get("typed_dimension_count") or "0") not in {"", "0"}:
        return False
    if not (str(row.get("unit_currency") or "").strip() or str(row.get("unit_measures_json") or "").strip()):
        return False
    try:
        Decimal(str(row.get("effective_value_text") or ""))
    except (InvalidOperation, ValueError):
        return False
    return True


def _revealed_value_record(row: Mapping[str, Any], *, record_index: int, bridge_hash: str) -> dict[str, Any]:
    return {
        "record_index": record_index,
        "fact_record_hash": stable_hash(
            {
                "bridge_hash": bridge_hash,
                "resolved_fact_id": str(row.get("resolved_fact_id") or ""),
                "fact_order": str(row.get("fact_order") or ""),
            }
        ),
        "fact_order": int(row.get("fact_order") or 0),
        "concept_qname": str(row.get("concept_qname") or ""),
        "concept_namespace_hash": stable_hash({"concept_namespace": str(row.get("concept_namespace") or "")}),
        "taxonomy_family": _taxonomy_family(str(row.get("concept_namespace") or "")),
        "concept_local_name": str(row.get("concept_local_name") or ""),
        "concept_standard": str(row.get("concept_standard") or "").strip().lower() in {"true", "1"},
        "concept_extension": False,
        "period_type": str(row.get("period_type") or ""),
        "period_start": str(row.get("period_start") or ""),
        "period_end": str(row.get("period_end") or ""),
        "period_instant": str(row.get("period_instant") or ""),
        "unit_currency": str(row.get("unit_currency") or ""),
        "unit_measures_json": str(row.get("unit_measures_json") or ""),
        "effective_value": str(row.get("effective_value_text") or ""),
        "effective_value_hash": str(row.get("effective_value_hash") or ""),
        "effective_value_length": int(row.get("effective_value_length") or 0),
        "value_semantics": str(row.get("value_semantics") or "arelle_effective_canonical_value_v1"),
        "lexical_value_hash": str(row.get("lexical_value_hash") or ""),
        "lexical_value_length": int(row.get("lexical_value_length") or 0),
        "transform_sign": str(row.get("transform_sign") or ""),
        "transform_scale": str(row.get("transform_scale") or ""),
        "transform_decimals": str(row.get("transform_decimals") or ""),
        "transform_precision": str(row.get("transform_precision") or ""),
        "transform_format": str(row.get("transform_format") or ""),
        "source_identity_redacted": True,
    }


def _taxonomy_family(namespace: str) -> str:
    if "fasb.org/us-gaap" in namespace:
        return "us-gaap"
    if "xbrl.sec.gov/dei" in namespace:
        return "dei"
    return "other"


def _surface_rollup(product_views: Mapping[str, Any]) -> dict[str, Any]:
    company_form_matrix = list(product_views.get("company_form_matrix") or [])
    semantic_profiles = list(product_views.get("semantic_profile") or [])
    fact_deduplication_conflict_diagnostics = list(
        product_views.get("fact_deduplication_conflict_diagnostics") or []
    )
    cross_company_comparability_readiness_audits = list(
        product_views.get("cross_company_comparability_readiness_audit") or []
    )
    statement_role_quality_profiles = list(product_views.get("statement_role_quality_profile") or [])
    period_unit_context_dimension_profiles = list(product_views.get("period_unit_context_dimension_profile") or [])
    extension_taxonomy_retention_profiles = list(product_views.get("extension_taxonomy_retention_profile") or [])
    standard_concept_mapping_profiles = list(product_views.get("standard_concept_mapping_profile") or [])
    extension_profiles = list(product_views.get("extension_unclassified_facts") or [])
    quality_gaps = dict(product_views.get("quality_gaps") or {})
    return {
        "rendered_mode": RENDERED_MODE,
        "product_view_names": list(PRODUCT_VIEW_NAMES),
        "filing_count": len(company_form_matrix),
        "inspectable_count": sum(1 for record in company_form_matrix if record.get("inspection_status") == "inspectable"),
        "semantic_profile_record_count": sum(1 for record in semantic_profiles if record.get("semantic_profile_inventory_hash")),
        "fact_deduplication_conflict_diagnostics_record_count": sum(
            1
            for record in fact_deduplication_conflict_diagnostics
            if record.get("fact_deduplication_conflict_diagnostics_hash")
        ),
        "cross_company_comparability_readiness_audit_record_count": sum(
            1
            for record in cross_company_comparability_readiness_audits
            if record.get("cross_company_comparability_readiness_audit_hash")
        ),
        "statement_role_quality_profile_record_count": sum(
            1
            for record in statement_role_quality_profiles
            if record.get("statement_role_quality_profile_hash")
        ),
        "period_unit_context_dimension_profile_record_count": sum(
            1
            for record in period_unit_context_dimension_profiles
            if record.get("period_unit_context_dimension_profile_hash")
        ),
        "extension_taxonomy_retention_profile_record_count": sum(
            1
            for record in extension_taxonomy_retention_profiles
            if record.get("extension_taxonomy_retention_profile_hash")
        ),
        "standard_concept_mapping_profile_record_count": sum(
            1
            for record in standard_concept_mapping_profiles
            if record.get("standard_concept_mapping_profile_hash")
        ),
        "extension_or_unclassified_record_count": sum(
            1
            for record in extension_profiles
            if int(record.get("extension_fact_count") or 0) > 0
            or int(record.get("unknown_or_unclassified_count") or 0) > 0
        ),
        "distinct_quality_gaps": list(quality_gaps.get("distinct_quality_gaps") or []),
        "server_receipt_projection_only": True,
        "frontend_durable_authority_enabled": False,
        "durable_delivery_archive_runtime_enabled": SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_RUNTIME_ENABLED,
    }


def _authority_chain(
    operator: Mapping[str, Any],
    delivery: Mapping[str, Any],
    validation: Mapping[str, Any],
    product_views: Mapping[str, Any],
) -> dict[str, Any]:
    semantic_hashes = [
        profile.get("semantic_profile_inventory_hash")
        for profile in product_views.get("semantic_profile", [])
        if isinstance(profile, Mapping) and profile.get("semantic_profile_inventory_hash")
    ]
    period_unit_context_dimension_hashes = [
        profile.get("period_unit_context_dimension_profile_hash")
        for profile in product_views.get("period_unit_context_dimension_profile", [])
        if isinstance(profile, Mapping) and profile.get("period_unit_context_dimension_profile_hash")
    ]
    statement_role_quality_hashes = [
        profile.get("statement_role_quality_profile_hash")
        for profile in product_views.get("statement_role_quality_profile", [])
        if isinstance(profile, Mapping) and profile.get("statement_role_quality_profile_hash")
    ]
    fact_deduplication_conflict_hashes = [
        profile.get("fact_deduplication_conflict_diagnostics_hash")
        for profile in product_views.get("fact_deduplication_conflict_diagnostics", [])
        if isinstance(profile, Mapping) and profile.get("fact_deduplication_conflict_diagnostics_hash")
    ]
    cross_company_comparability_readiness_hashes = [
        profile.get("cross_company_comparability_readiness_audit_hash")
        for profile in product_views.get("cross_company_comparability_readiness_audit", [])
        if isinstance(profile, Mapping) and profile.get("cross_company_comparability_readiness_audit_hash")
    ]
    extension_taxonomy_retention_hashes = [
        profile.get("extension_taxonomy_retention_profile_hash")
        for profile in product_views.get("extension_taxonomy_retention_profile", [])
        if isinstance(profile, Mapping) and profile.get("extension_taxonomy_retention_profile_hash")
    ]
    standard_concept_mapping_hashes = [
        profile.get("standard_concept_mapping_profile_hash")
        for profile in product_views.get("standard_concept_mapping_profile", [])
        if isinstance(profile, Mapping) and profile.get("standard_concept_mapping_profile_hash")
    ]
    quality_hashes = [
        record.get("quality_evidence_hash")
        for record in product_views.get("company_form_matrix", [])
        if isinstance(record, Mapping) and record.get("quality_evidence_hash")
    ]
    return {
        "validation_receipt_hash": validation["validation_receipt_hash"],
        "delivery_status_provenance_receipt_hash": delivery["delivery_status_provenance_receipt_hash"],
        "operator_inspection_receipt_hash": operator["operator_inspection_receipt_hash"],
        "connector_receipt_hash": validation["connector_receipt_hash"],
        "quality_evidence_hashes_hash": stable_hash(quality_hashes),
        "semantic_profile_inventory_hashes_hash": stable_hash(semantic_hashes),
        "fact_deduplication_conflict_diagnostics_hashes_hash": stable_hash(
            fact_deduplication_conflict_hashes
        ),
        "cross_company_comparability_readiness_audit_hashes_hash": stable_hash(
            cross_company_comparability_readiness_hashes
        ),
        "statement_role_quality_profile_hashes_hash": stable_hash(statement_role_quality_hashes),
        "extension_taxonomy_retention_profile_hashes_hash": stable_hash(extension_taxonomy_retention_hashes),
        "standard_concept_mapping_profile_hashes_hash": stable_hash(standard_concept_mapping_hashes),
        "period_unit_context_dimension_profile_hashes_hash": stable_hash(period_unit_context_dimension_hashes),
        "product_views_hash": stable_hash(product_views),
        "receipt_chain_bound": True,
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
        "surface_mode": SURFACE_MODE,
        "rendered_mode": RENDERED_MODE,
        "operator_decision": OPERATOR_DECISION,
        "operator_product_surface_state": receipt["operator_product_surface_state"],
        "operator_product_surface_receipt_id": receipt["operator_product_surface_receipt_id"],
        "operator_product_surface_receipt_hash": receipt["operator_product_surface_receipt_hash"],
        "operator_product_surface_receipt_ref": receipt["operator_product_surface_receipt_ref"],
        "operator_inspection_receipt_id": receipt["operator_inspection_receipt_id"],
        "operator_inspection_receipt_hash": receipt["operator_inspection_receipt_hash"],
        "delivery_status_provenance_receipt_id": receipt["delivery_status_provenance_receipt_id"],
        "delivery_status_provenance_receipt_hash": receipt["delivery_status_provenance_receipt_hash"],
        "validation_receipt_hash": receipt["validation_receipt_hash"],
        "connector_receipt_hash": receipt["connector_receipt_hash"],
        "product_views": dict(receipt["product_views"]),
        "value_reveal": dict(receipt.get("value_reveal") or _value_reveal_disabled()),
        "surface_rollup": dict(receipt["surface_rollup"]),
        "authority_chain": dict(receipt["authority_chain"]),
        "cache": {
            "idempotent_replay": idempotent_replay,
            "network_request_made_by_product_surface": False,
            "parser_rerun_performed_by_product_surface": False,
            "package_mutation_performed_by_product_surface": False,
            "provider_object_created_by_product_surface": False,
            "value_reveal_dataset_version_read_performed": bool(
                (receipt.get("value_reveal") or {}).get("value_reveal_requested")
            ),
        },
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [
            "inspect SEC EDGAR product surface quality gaps",
            "render SEC EDGAR product surface in the operator workbench",
            "request governed SEC EDGAR operator value reveal",
        ],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_operator_product_surface_raw_authority_exposed",
            "SEC EDGAR operator product surface would expose raw path, URL, token, accession, ticker, company name, raw value, or artifact-byte authority.",
            http_status=409,
        )
    return response


def _blocked_response(
    *,
    request_id: str,
    reasons: list[dict[str, Any]],
    operator: Mapping[str, Any] | None = None,
    delivery: Mapping[str, Any] | None = None,
    validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    response = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "blocked",
        "surface_mode": SURFACE_MODE,
        "rendered_mode": RENDERED_MODE,
        "operator_decision": OPERATOR_DECISION,
        "operator_product_surface_state": BLOCKED_STATE,
        "operator_inspection_receipt_id": operator.get("operator_inspection_receipt_id") if operator else None,
        "operator_inspection_receipt_hash": operator.get("operator_inspection_receipt_hash") if operator else None,
        "delivery_status_provenance_receipt_hash": delivery.get("delivery_status_provenance_receipt_hash") if delivery else None,
        "validation_receipt_hash": validation.get("validation_receipt_hash") if validation else None,
        "blocked_reasons": reasons,
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["repair_or_refresh_sec_edgar_operator_inspection_receipt"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_operator_product_surface_blocked_response_raw_authority_exposed",
            "Blocked SEC EDGAR operator product surface response would expose raw authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key in FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = _find_forbidden_nested_fields(request)
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_operator_product_surface_forbidden_request_fields",
            "SEC EDGAR operator product surface does not admit caller paths, URLs, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, parser-expansion, frontend authority, accessions, tickers, company names, or raw fact values.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(set(request) - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_operator_product_surface_unknown_field",
            "SEC EDGAR operator product surface fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_operator_product_surface_schema_not_admitted",
            "SEC EDGAR operator product surface requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


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
            "sec_edgar_operator_product_surface_receipt_id_invalid",
            "SEC EDGAR operator product surface status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["sec_edgar_operator_product_surface_receipt_id"],
        )
    path = _receipt_path(receipt_id)
    if not path.exists():
        _blocked(
            "sec_edgar_operator_product_surface_receipt_missing",
            "SEC EDGAR operator product surface receipt was not found.",
            http_status=404,
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_operator_product_surface_receipt_unreadable",
            "SEC EDGAR operator product surface receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("operator_product_surface_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_operator_product_surface_receipt_invalid",
            "SEC EDGAR operator product surface receipt is invalid or mismatched.",
            http_status=409,
        )
    _validate_required_receipt_keys(receipt)
    receipt_hash = str(receipt.get("operator_product_surface_receipt_hash") or "")
    if receipt_hash[:24] != suffix or receipt_hash != _operator_product_surface_receipt_hash(receipt):
        _blocked(
            "sec_edgar_operator_product_surface_receipt_hash_mismatch",
            "SEC EDGAR operator product surface receipt hash is stale or mismatched.",
            http_status=409,
        )
    return receipt


def _validate_required_receipt_keys(receipt: Mapping[str, Any]) -> None:
    required = (
        "operator_product_surface_state",
        "operator_product_surface_receipt_hash",
        "operator_product_surface_receipt_ref",
        "operator_inspection_receipt_id",
        "operator_inspection_receipt_hash",
        "delivery_status_provenance_receipt_id",
        "delivery_status_provenance_receipt_hash",
        "validation_receipt_hash",
        "connector_receipt_hash",
        "product_views",
        "surface_rollup",
        "authority_chain",
    )
    missing = [key for key in required if key not in receipt]
    if missing:
        _blocked(
            "sec_edgar_operator_product_surface_receipt_required_keys_missing",
            "SEC EDGAR operator product surface receipt is missing required authority fields.",
            http_status=409,
            blocked_fields=missing,
        )


def _operator_product_surface_receipt_hash(receipt: Mapping[str, Any]) -> str:
    return stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "surface_mode": SURFACE_MODE,
            "operator_inspection_receipt_hash": receipt.get("operator_inspection_receipt_hash"),
            "delivery_status_provenance_receipt_hash": receipt.get("delivery_status_provenance_receipt_hash"),
            "validation_receipt_hash": receipt.get("validation_receipt_hash"),
            "product_views_hash": stable_hash(receipt.get("product_views") or {}),
            "value_reveal_hash": stable_hash(receipt.get("value_reveal") or _value_reveal_disabled()),
            "surface_rollup_hash": stable_hash(receipt.get("surface_rollup") or {}),
            "authority_chain_hash": stable_hash(receipt.get("authority_chain") or {}),
        }
    )


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["operator_product_surface_receipt_id"]))
    if target.exists():
        _read_verified_receipt(target.stem)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        _read_verified_receipt(target.stem)
    except OSError as exc:
        _blocked(
            "sec_edgar_operator_product_surface_receipt_write_failed",
            "SEC EDGAR operator product surface receipt could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    path = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_operator_product_surface_request_binding_unreadable",
            "SEC EDGAR operator product surface request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_operator_product_surface_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "operator_product_surface_basis_hash": basis_hash,
        "operator_product_surface_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("operator_product_surface_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_operator_product_surface_request_binding_conflict",
                "SEC EDGAR operator product surface request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        existing = _read_request_binding(request_id) or {}
        if existing.get("operator_product_surface_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_operator_product_surface_request_binding_conflict",
                "SEC EDGAR operator product surface request binding conflicts with existing authority.",
                http_status=409,
            )
    except OSError as exc:
        _blocked(
            "sec_edgar_operator_product_surface_request_binding_write_failed",
            "SEC EDGAR operator product surface request binding could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )


def _negative_invariants() -> dict[str, bool]:
    return {
        "raw_url_exposed": False,
        "raw_local_path_exposed": False,
        "artifact_bytes_exposed": False,
        "raw_fact_values_exposed": False,
        "accession_exposed": False,
        "ticker_exposed": False,
        "company_name_exposed": False,
        "sec_network_fetch_performed": False,
        "parser_rerun_performed": False,
        "package_mutation_performed": False,
        "delivery_file_response_served": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "candidate_b_pdf_only_routing_performed": False,
        "taxonomy_network_resolution_performed": False,
        "sec_companyfacts_api_called": False,
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
        if _is_forbidden_ref(text):
            found.append(prefix or "request_body")
    return sorted(set(found))


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
        or "storage://" in text
    )


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _request_bindings_dir() -> Path:
    return _root() / "requests"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_operator_product_surface_storage_root_unavailable",
            "SEC EDGAR operator product surface requires the existing Layer 3 storage root.",
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
            "sec_edgar_operator_product_surface_required_field_missing",
            "A required SEC EDGAR operator product surface field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_operator_product_surface_{key}_not_admitted",
            "SEC EDGAR operator product surface request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _is_hex(value: str) -> bool:
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and _is_hex(value)


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
