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
    layer3_sec_edgar_delivery_status_provenance,
    layer3_sec_edgar_operator_inspection,
    layer3_sec_edgar_operator_product_surface,
    layer3_sec_edgar_real_company_corpus_validation,
)
from app.services.layer3_sec_edgar_ref_safety import (
    contains_forbidden_ref,
    find_forbidden_ref_paths,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_durable_delivery_archive.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_durable_delivery_archive_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_durable_delivery_archive_status.v1"
SCHEMA_VERSION = 1
ARCHIVE_MODE = "sec_edgar_durable_delivery_archive_v1"
OPERATOR_DECISION = "archive_sec_edgar_operator_product_surface_delivery_package"
ARCHIVE_STATUS_SURFACE_MODE = "sec_edgar_durable_delivery_archive_status_surface_v1"
ARCHIVE_STATUS_RESPONSE_AUTHORITY = "sec_edgar_durable_delivery_archive_receipt_and_manifest_readiness"
READY_STATE = "sec_edgar_durable_delivery_archive_ready"
BLOCKED_STATE = "sec_edgar_durable_delivery_archive_blocked"
RECEIPT_PREFIX = "sec-edgar-durable-delivery-archive"
RECEIPT_DIR = "layer3-sec-edgar-durable-delivery-archive"
REDACTION_POLICY_ID = "sec_edgar_durable_delivery_archive_redaction_v1"
ARCHIVE_MANIFEST_SCHEMA_ID = "layer3.sec_edgar_durable_delivery_archive_manifest.v1"
ARCHIVE_SCOPE = "redacted_product_surface_package_manifest_and_delivery_readiness_archive"
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_RUNTIME_VERSION = "sec_edgar_durable_delivery_archive_runtime_v1"
SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_RUNTIME_ENABLED = True

ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "archive_mode",
    "operator_decision",
    "sec_edgar_operator_product_surface_receipt_id",
    "sec_edgar_operator_product_surface_receipt_hash",
    "operator_confirmation",
    "actor",
}
FORBIDDEN_REQUEST_FIELDS = {
    *layer3_sec_edgar_operator_product_surface.FORBIDDEN_REQUEST_FIELDS,
    "delivery_file_response",
    "provider_object_write",
    "internal_webhook_dispatch",
    "archive_file_path",
    "manifest_path",
    "package_payload",
    "package_mutation",
    "archive_bytes",
}
PRODUCT_VIEW_ORDER = (
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
ARCHIVE_ROLES = (
    "product_surface_receipt",
    "delivery_status_provenance_receipt",
    "operator_inspection_receipt",
    "validation_receipt",
    "authority_chain",
    "product_view_manifest",
    "surface_rollup",
    "diagnostics_loss_report",
    "redaction_manifest",
)
ARCHIVE_STATUS_DOWNSTREAM_UNAVAILABLE = (
    "delivery_file_response",
    "provider_object_write",
    "connector_dispatch",
    "internal_webhook_dispatch",
    "frontend_durable_authority",
    "browser_storage_authority",
    "rag_vector_model_runtime",
    "package_mutation",
    "sec_network_fetch",
    "parser_rerun",
    "html_inline_xbrl_reparse_or_rematerialization",
    "cross_company_comparability_normalization",
)
_ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")


def archive_sec_edgar_durable_delivery(
    fields: Mapping[str, Any],
    db: Session,
) -> dict[str, Any]:
    del db
    _validate_request_fields(fields)
    request_id = _required(fields, "client_request_id")
    _require_exact(fields, "archive_mode", ARCHIVE_MODE)
    _require_exact(fields, "operator_decision", OPERATOR_DECISION)
    if not bool(fields.get("operator_confirmation")):
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason("sec_edgar_durable_delivery_archive_operator_confirmation_missing")],
        )

    product_surface_receipt_id = _required(fields, "sec_edgar_operator_product_surface_receipt_id")
    expected_product_surface_hash = _required(fields, "sec_edgar_operator_product_surface_receipt_hash")
    if not _is_sha256(expected_product_surface_hash):
        return _blocked_response(
            request_id=request_id,
            reasons=[
                _reason(
                    "sec_edgar_durable_delivery_archive_product_surface_hash_invalid",
                    blocked_fields=["sec_edgar_operator_product_surface_receipt_hash"],
                )
            ],
        )
    try:
        product_surface = layer3_sec_edgar_operator_product_surface._read_verified_receipt(
            product_surface_receipt_id
        )
        operator = layer3_sec_edgar_operator_inspection._read_verified_receipt(
            _required_receipt_field(product_surface, "operator_inspection_receipt_id")
        )
        delivery = layer3_sec_edgar_delivery_status_provenance._read_verified_receipt(
            _required_receipt_field(product_surface, "delivery_status_provenance_receipt_id")
        )
        validation = layer3_sec_edgar_real_company_corpus_validation._read_verified_receipt(
            _required_receipt_field(delivery, "validation_receipt_id")
        )
    except Layer3WorkbenchError as exc:
        return _blocked_response(
            request_id=request_id,
            reasons=[_reason(exc.error_code, message=exc.message, blocked_fields=list(exc.blocked_fields))],
        )

    readiness_reasons = _readiness_reasons(
        product_surface,
        operator,
        delivery,
        validation,
        expected_product_surface_hash,
    )
    if readiness_reasons:
        return _blocked_response(
            request_id=request_id,
            product_surface=product_surface,
            delivery=delivery,
            operator=operator,
            validation=validation,
            reasons=readiness_reasons,
        )

    archive_manifest = _archive_manifest(product_surface, operator, delivery, validation)
    redaction_manifest = archive_manifest["redaction_manifest"]
    archive_manifest_hash = stable_hash(archive_manifest)
    archive_order_hash = stable_hash(archive_manifest["archive_order"])
    source_authority_chain_hash = stable_hash(archive_manifest["source_authority_chain"])
    redaction_manifest_hash = stable_hash(redaction_manifest)
    receipt_hash = stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "archive_mode": ARCHIVE_MODE,
            "operator_decision": OPERATOR_DECISION,
            "operator_product_surface_receipt_hash": expected_product_surface_hash,
            "archive_manifest_hash": archive_manifest_hash,
            "archive_order_hash": archive_order_hash,
            "source_authority_chain_hash": source_authority_chain_hash,
            "redaction_manifest_hash": redaction_manifest_hash,
        }
    )
    binding = _read_request_binding(request_id)
    if binding and binding.get("durable_delivery_archive_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_durable_delivery_archive_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR durable delivery archive basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["sec_edgar_durable_delivery_archive_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "archive_mode": ARCHIVE_MODE,
        "runtime_version": SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_RUNTIME_VERSION,
        "operator_decision": OPERATOR_DECISION,
        "durable_delivery_archive_state": READY_STATE,
        "sec_edgar_durable_delivery_archive_receipt_id": f"{RECEIPT_PREFIX}-{receipt_hash[:24]}",
        "sec_edgar_durable_delivery_archive_receipt_hash": receipt_hash,
        "sec_edgar_durable_delivery_archive_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "archive_manifest_hash": archive_manifest_hash,
        "archive_order_hash": archive_order_hash,
        "source_authority_chain_hash": source_authority_chain_hash,
        "redaction_manifest_hash": redaction_manifest_hash,
        "archive_manifest": archive_manifest,
        "operator_product_surface_receipt_id": product_surface["operator_product_surface_receipt_id"],
        "operator_product_surface_receipt_hash": product_surface["operator_product_surface_receipt_hash"],
        "delivery_status_provenance_receipt_hash": delivery["delivery_status_provenance_receipt_hash"],
        "operator_inspection_receipt_hash": operator["operator_inspection_receipt_hash"],
        "validation_receipt_hash": validation["validation_receipt_hash"],
        "connector_receipt_hash": validation["connector_receipt_hash"],
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "request_id_hash": _sha256_text(request_id),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_archive_manifest(receipt["sec_edgar_durable_delivery_archive_receipt_id"], archive_manifest)
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt["sec_edgar_durable_delivery_archive_receipt_id"])
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_durable_delivery_archive_status(
    sec_edgar_durable_delivery_archive_receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(sec_edgar_durable_delivery_archive_receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-durable-delivery-archive-status-{receipt['sec_edgar_durable_delivery_archive_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
        include_status_surface=True,
    )


def _readiness_reasons(
    product_surface: Mapping[str, Any],
    operator: Mapping[str, Any],
    delivery: Mapping[str, Any],
    validation: Mapping[str, Any],
    expected_product_surface_hash: str,
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    if product_surface.get("operator_product_surface_receipt_hash") != expected_product_surface_hash:
        reasons.append(
            _reason(
                "sec_edgar_durable_delivery_archive_product_surface_hash_mismatch",
                blocked_fields=[
                    "sec_edgar_operator_product_surface_receipt_id",
                    "sec_edgar_operator_product_surface_receipt_hash",
                ],
            )
        )
    if product_surface.get("operator_product_surface_state") != layer3_sec_edgar_operator_product_surface.READY_STATE:
        reasons.append(_reason("sec_edgar_durable_delivery_archive_product_surface_not_ready"))
    if operator.get("operator_inspection_state") != layer3_sec_edgar_operator_inspection.READY_STATE:
        reasons.append(_reason("sec_edgar_durable_delivery_archive_operator_inspection_not_ready"))
    if delivery.get("delivery_status_provenance_state") != layer3_sec_edgar_delivery_status_provenance.READY_STATE:
        reasons.append(_reason("sec_edgar_durable_delivery_archive_delivery_status_provenance_not_ready"))
    if validation.get("validation_state") != layer3_sec_edgar_real_company_corpus_validation.READY_STATE:
        reasons.append(_reason("sec_edgar_durable_delivery_archive_validation_not_ready"))
    if tuple(validation.get("company_matrix") or ()) not in layer3_sec_edgar_operator_product_surface._admitted_company_matrices():
        reasons.append(_reason("sec_edgar_durable_delivery_archive_company_matrix_not_admitted"))
    if product_surface.get("operator_inspection_receipt_hash") != operator.get("operator_inspection_receipt_hash"):
        reasons.append(_reason("sec_edgar_durable_delivery_archive_operator_hash_chain_mismatch"))
    if product_surface.get("delivery_status_provenance_receipt_hash") != delivery.get("delivery_status_provenance_receipt_hash"):
        reasons.append(_reason("sec_edgar_durable_delivery_archive_delivery_hash_chain_mismatch"))
    if delivery.get("validation_receipt_hash") != validation.get("validation_receipt_hash"):
        reasons.append(_reason("sec_edgar_durable_delivery_archive_validation_hash_chain_mismatch"))
    return reasons


def _archive_manifest(
    product_surface: Mapping[str, Any],
    operator: Mapping[str, Any],
    delivery: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> dict[str, Any]:
    product_views = dict(product_surface.get("product_views") or {})
    product_view_manifest = _product_view_manifest(product_views)
    source_authority_chain = {
        "operator_product_surface_receipt_hash": product_surface.get("operator_product_surface_receipt_hash"),
        "operator_inspection_receipt_hash": operator.get("operator_inspection_receipt_hash"),
        "delivery_status_provenance_receipt_hash": delivery.get("delivery_status_provenance_receipt_hash"),
        "validation_receipt_hash": validation.get("validation_receipt_hash"),
        "connector_receipt_hash": validation.get("connector_receipt_hash"),
        "authority_chain_hash": stable_hash(product_surface.get("authority_chain") or {}),
        "delivery_status_record_hashes": _ordered_record_hashes(
            delivery.get("delivery_status_records") or [],
            "delivery_status_record_hash",
        ),
        "operator_inspection_record_hashes": _ordered_record_hashes(
            operator.get("company_filing_inspection_matrix") or [],
            "operator_inspection_record_hash",
        ),
        "validation_record_hashes": _ordered_record_hashes(
            validation.get("filing_validation_records") or [],
            "record_hash",
        ),
    }
    archive_order = {
        "product_view_order": [name for name in PRODUCT_VIEW_ORDER if name in product_views],
        "company_form_matrix_record_order": _record_indexes(
            product_views.get("company_form_matrix") or []
        ),
        "delivery_status_record_order": _record_indexes(delivery.get("delivery_status_records") or []),
        "operator_inspection_record_order": _record_indexes(
            operator.get("company_filing_inspection_matrix") or []
        ),
        "validation_record_order": _record_indexes(validation.get("filing_validation_records") or []),
    }
    redaction_manifest = {
        "redaction_policy_id": REDACTION_POLICY_ID,
        "redacted_fields": [
            "raw_url",
            "raw_local_path",
            "artifact_bytes",
            "raw_fact_value",
            "accession",
            "ticker",
            "company_name",
            "provider_credentials",
            "connector_credentials",
        ],
        "hash_only_fields": [
            "ticker_hash",
            "company_name_hash",
            "cik_hash",
            "quality_evidence_hash",
            "semantic_profile_inventory_hash",
            "delivery_status_record_hash",
            "operator_inspection_record_hash",
            "validation_record_hash",
        ],
        "provider_delivery_enabled": False,
        "delivery_file_response_served": False,
        "frontend_durable_authority_enabled": False,
    }
    manifest = {
        "schema_id": ARCHIVE_MANIFEST_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "archive_scope": ARCHIVE_SCOPE,
        "archive_roles": list(ARCHIVE_ROLES),
        "archive_mode": ARCHIVE_MODE,
        "runtime_version": SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_RUNTIME_VERSION,
        "product_surface_authority": {
            "operator_product_surface_receipt_id": product_surface.get("operator_product_surface_receipt_id"),
            "operator_product_surface_receipt_hash": product_surface.get("operator_product_surface_receipt_hash"),
            "operator_product_surface_state": product_surface.get("operator_product_surface_state"),
            "surface_rollup_hash": stable_hash(product_surface.get("surface_rollup") or {}),
        },
        "source_authority_chain": source_authority_chain,
        "product_view_manifest": product_view_manifest,
        "surface_rollup": _surface_rollup_archive(product_surface.get("surface_rollup") or {}),
        "diagnostics_loss_report": _diagnostics_loss_report_archive(
            product_views.get("diagnostics_loss_report") or {}
        ),
        "archive_order": archive_order,
        "redaction_manifest": redaction_manifest,
        "non_admissions": {
            "delivery_file_response_served": False,
            "provider_object_write_enabled": False,
            "connector_dispatch_enabled": False,
            "internal_webhook_dispatch_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
            "package_mutation_performed": False,
            "sec_network_fetch_performed": False,
            "parser_rerun_performed": False,
            "html_inline_xbrl_reparse_or_rematerialization_performed": False,
            "financial_statement_semantics_finalized": False,
            "cross_company_comparability_admitted": False,
            "comparability_normalization_performed": False,
        },
    }
    if _contains_forbidden_output_ref(manifest):
        _blocked(
            "sec_edgar_durable_delivery_archive_manifest_raw_authority_exposed",
            "SEC EDGAR durable delivery archive manifest would expose raw authority.",
            http_status=409,
        )
    return manifest


def _product_view_manifest(product_views: Mapping[str, Any]) -> dict[str, Any]:
    manifest: dict[str, Any] = {}
    for name in PRODUCT_VIEW_ORDER:
        value = product_views.get(name)
        if isinstance(value, list):
            manifest[name] = {
                "record_count": len(value),
                "records": [_record_archive_ref(item) for item in value if isinstance(item, Mapping)],
                "section_hash": stable_hash(value),
            }
        elif isinstance(value, Mapping):
            manifest[name] = _mapping_archive_ref(value)
    return manifest


def _record_archive_ref(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_index": record.get("record_index"),
        "record_hash": stable_hash(record),
        "semantic_profile_inventory_hash": record.get("semantic_profile_inventory_hash"),
        "statement_role_quality_profile_hash": record.get("statement_role_quality_profile_hash"),
        "period_unit_context_dimension_profile_hash": record.get("period_unit_context_dimension_profile_hash"),
        "extension_taxonomy_retention_profile_hash": record.get("extension_taxonomy_retention_profile_hash"),
        "standard_concept_mapping_profile_hash": record.get("standard_concept_mapping_profile_hash"),
        "fact_deduplication_conflict_diagnostics_hash": record.get(
            "fact_deduplication_conflict_diagnostics_hash"
        ),
        "cross_company_comparability_readiness_audit_hash": record.get(
            "cross_company_comparability_readiness_audit_hash"
        ),
        "quality_evidence_hash": record.get("quality_evidence_hash"),
        "delivery_status_record_hash": record.get("delivery_status_record_hash"),
        "operator_inspection_record_hash": record.get("operator_inspection_record_hash"),
        "validation_record_hash": record.get("validation_record_hash"),
        "profile_status": record.get("profile_status"),
        "quality_assessment_status": record.get("quality_assessment_status"),
        "extension_fact_count": record.get("extension_fact_count"),
        "unknown_or_unclassified_count": record.get("unknown_or_unclassified_count"),
        "delivery_readiness_status": record.get("delivery_readiness_status"),
        "inspection_status": record.get("inspection_status"),
    }


def _mapping_archive_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "section_hash": stable_hash(value),
        "distinct_quality_gap_count": len(value.get("distinct_quality_gaps") or [])
        if isinstance(value.get("distinct_quality_gaps"), list)
        else None,
        "financial_statement_semantics_finalized": value.get("financial_statement_semantics_finalized"),
        "cross_company_comparability_ready": value.get("cross_company_comparability_ready"),
        "cross_company_comparability_admitted": value.get("cross_company_comparability_admitted"),
        "comparability_normalization_performed": value.get("comparability_normalization_performed"),
        "sec_companyfacts_api_called": value.get("sec_companyfacts_api_called"),
    }


def _surface_rollup_archive(surface_rollup: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "surface_rollup_hash": stable_hash(surface_rollup),
        "filing_count": surface_rollup.get("filing_count"),
        "inspectable_count": surface_rollup.get("inspectable_count"),
        "semantic_profile_record_count": surface_rollup.get("semantic_profile_record_count"),
        "server_receipt_projection_only": surface_rollup.get("server_receipt_projection_only"),
        "frontend_durable_authority_enabled": surface_rollup.get("frontend_durable_authority_enabled"),
        "durable_delivery_archive_runtime_enabled": SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_RUNTIME_ENABLED,
    }


def _diagnostics_loss_report_archive(diagnostics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "diagnostics_loss_report_hash": stable_hash(diagnostics),
        "unclassified_record_count": diagnostics.get("unclassified_record_count"),
        "financial_statement_semantics_finalized": diagnostics.get("financial_statement_semantics_finalized"),
        "cross_company_comparability_ready": diagnostics.get("cross_company_comparability_ready"),
        "comparability_normalization_performed": diagnostics.get("comparability_normalization_performed"),
        "sec_companyfacts_api_called": diagnostics.get("sec_companyfacts_api_called"),
        "blocked_or_degraded_delivery_gap_count": len(diagnostics.get("blocked_or_degraded_delivery_gaps") or [])
        if isinstance(diagnostics.get("blocked_or_degraded_delivery_gaps"), list)
        else None,
    }


def _ordered_record_hashes(records: Any, hash_key: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, Mapping):
            continue
        refs.append(
            {
                "record_index": record.get("record_index"),
                hash_key: record.get(hash_key),
            }
        )
    return refs


def _record_indexes(records: Any) -> list[Any]:
    return [
        record.get("record_index")
        for record in records
        if isinstance(record, Mapping) and record.get("record_index") is not None
    ]


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    schema_id: str,
    idempotent_replay: bool,
    include_status_surface: bool = False,
) -> dict[str, Any]:
    write_performed = not idempotent_replay and not include_status_surface
    response = {
        **dict(receipt),
        "schema_id": schema_id,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "ready",
        "cache": {
            "idempotent_replay": idempotent_replay,
            "archive_receipt_write_performed": write_performed,
            "archive_manifest_write_performed": write_performed,
            "network_request_made_by_archive": False,
            "parser_rerun_performed_by_archive": False,
            "package_mutation_performed_by_archive": False,
            "delivery_file_response_served_by_archive": False,
            "provider_object_write_performed_by_archive": False,
            "connector_dispatch_performed_by_archive": False,
        },
        "next_allowed_actions": ["inspect_sec_edgar_durable_delivery_archive_status"],
    }
    if include_status_surface:
        status_surface = _archive_status_surface(receipt)
        response.update(
            {
                "status_surface_mode": ARCHIVE_STATUS_SURFACE_MODE,
                "response_authority": ARCHIVE_STATUS_RESPONSE_AUTHORITY,
                "read_only_status_surface": True,
                "archive_status_surface_hash": stable_hash(status_surface),
                "archive_status_surface": status_surface,
                "downstream_unavailable": list(ARCHIVE_STATUS_DOWNSTREAM_UNAVAILABLE),
                "next_allowed_actions": [
                    "inspect_sec_edgar_durable_delivery_archive_status",
                    "review_sec_edgar_durable_delivery_archive_manifest_readiness",
                ],
            }
        )
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_durable_delivery_archive_response_raw_authority_exposed",
            "SEC EDGAR durable delivery archive response would expose raw authority.",
            http_status=409,
        )
    return response


def _archive_status_surface(receipt: Mapping[str, Any]) -> dict[str, Any]:
    archive_manifest = _read_archive_manifest_for_status(receipt)
    source_authority_chain = archive_manifest.get("source_authority_chain") or {}
    archive_order = archive_manifest.get("archive_order") or {}
    product_view_manifest = archive_manifest.get("product_view_manifest") or {}
    redaction_manifest = archive_manifest.get("redaction_manifest") or {}
    non_admissions = archive_manifest.get("non_admissions") or {}
    company_form_matrix = product_view_manifest.get("company_form_matrix") or {}
    status_surface = {
        "schema_id": "layer3.sec_edgar_durable_delivery_archive_status_surface.v1",
        "schema_version": SCHEMA_VERSION,
        "status_surface_mode": ARCHIVE_STATUS_SURFACE_MODE,
        "response_authority": ARCHIVE_STATUS_RESPONSE_AUTHORITY,
        "read_only_status_surface": True,
        "server_receipt_projection_only": True,
        "archive_receipt_available": True,
        "archive_manifest_available": True,
        "archive_manifest_readiness": {
            "archive_manifest_ready": True,
            "archive_manifest_file_backed": True,
            "archive_manifest_hash_verified": stable_hash(archive_manifest) == receipt.get("archive_manifest_hash"),
            "archive_order_hash_verified": stable_hash(archive_order) == receipt.get("archive_order_hash"),
            "source_authority_chain_hash_verified": stable_hash(source_authority_chain)
            == receipt.get("source_authority_chain_hash"),
            "redaction_manifest_hash_verified": stable_hash(redaction_manifest)
            == receipt.get("redaction_manifest_hash"),
        },
        "authority_chain_status": {
            "operator_product_surface_receipt_hash": receipt.get("operator_product_surface_receipt_hash"),
            "delivery_status_provenance_receipt_hash": receipt.get("delivery_status_provenance_receipt_hash"),
            "operator_inspection_receipt_hash": receipt.get("operator_inspection_receipt_hash"),
            "validation_receipt_hash": receipt.get("validation_receipt_hash"),
            "connector_receipt_hash": receipt.get("connector_receipt_hash"),
            "delivery_status_record_count": len(source_authority_chain.get("delivery_status_record_hashes") or []),
            "operator_inspection_record_count": len(
                source_authority_chain.get("operator_inspection_record_hashes") or []
            ),
            "validation_record_count": len(source_authority_chain.get("validation_record_hashes") or []),
        },
        "manifest_order_status": {
            "product_view_order": archive_order.get("product_view_order") or [],
            "company_form_matrix_record_order": archive_order.get("company_form_matrix_record_order") or [],
            "delivery_status_record_order": archive_order.get("delivery_status_record_order") or [],
            "operator_inspection_record_order": archive_order.get("operator_inspection_record_order") or [],
            "validation_record_order": archive_order.get("validation_record_order") or [],
        },
        "product_view_status": {
            "product_view_count": len(product_view_manifest),
            "company_form_matrix_record_count": len(company_form_matrix.get("records") or []),
            "semantic_profile_section_available": "semantic_profile" in product_view_manifest,
            "statement_role_quality_profile_section_available": "statement_role_quality_profile"
            in product_view_manifest,
            "period_unit_context_dimension_profile_section_available": "period_unit_context_dimension_profile"
            in product_view_manifest,
            "extension_taxonomy_retention_profile_section_available": "extension_taxonomy_retention_profile"
            in product_view_manifest,
            "standard_concept_mapping_profile_section_available": "standard_concept_mapping_profile"
            in product_view_manifest,
            "fact_deduplication_conflict_diagnostics_section_available": (
                "fact_deduplication_conflict_diagnostics" in product_view_manifest
            ),
            "cross_company_comparability_readiness_audit_section_available": (
                "cross_company_comparability_readiness_audit" in product_view_manifest
            ),
        },
        "redaction_status": {
            "redaction_policy_id": receipt.get("redaction_policy_id"),
            "redacted_field_count": len(redaction_manifest.get("redacted_fields") or []),
            "hash_only_field_count": len(redaction_manifest.get("hash_only_fields") or []),
            "raw_url_exposed": False,
            "raw_local_path_exposed": False,
            "artifact_bytes_exposed": False,
            "raw_fact_values_exposed": False,
        },
        "non_admissions": dict(non_admissions),
        "downstream_unavailable": list(ARCHIVE_STATUS_DOWNSTREAM_UNAVAILABLE),
        "next_allowed_actions": [
            "inspect_sec_edgar_durable_delivery_archive_status",
            "review_sec_edgar_durable_delivery_archive_manifest_readiness",
        ],
    }
    if not all(status_surface["archive_manifest_readiness"].values()):
        _blocked(
            "sec_edgar_durable_delivery_archive_status_surface_hash_mismatch",
            "SEC EDGAR durable delivery archive status surface could not verify archive manifest readiness.",
            http_status=409,
        )
    if _contains_forbidden_output_ref(status_surface):
        _blocked(
            "sec_edgar_durable_delivery_archive_status_surface_raw_authority_exposed",
            "SEC EDGAR durable delivery archive status surface would expose raw authority.",
            http_status=409,
        )
    return status_surface


def _read_archive_manifest_for_status(receipt: Mapping[str, Any]) -> dict[str, Any]:
    receipt_id = str(receipt.get("sec_edgar_durable_delivery_archive_receipt_id") or "")
    path = _archive_manifest_path(receipt_id)
    if not path.exists():
        _blocked(
            "sec_edgar_durable_delivery_archive_status_surface_manifest_missing",
            "SEC EDGAR durable delivery archive status surface requires the stored archive manifest.",
            http_status=404,
        )
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_durable_delivery_archive_status_surface_manifest_unreadable",
            "SEC EDGAR durable delivery archive status surface could not read the archive manifest.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(manifest, dict):
        _blocked(
            "sec_edgar_durable_delivery_archive_status_surface_manifest_invalid",
            "SEC EDGAR durable delivery archive status surface found an invalid archive manifest.",
            http_status=409,
        )
    if stable_hash(manifest) != receipt.get("archive_manifest_hash"):
        _blocked(
            "sec_edgar_durable_delivery_archive_status_surface_manifest_hash_mismatch",
            "SEC EDGAR durable delivery archive status surface found a stale or mismatched archive manifest.",
            http_status=409,
        )
    if _contains_forbidden_output_ref(manifest):
        _blocked(
            "sec_edgar_durable_delivery_archive_status_surface_manifest_raw_authority_exposed",
            "SEC EDGAR durable delivery archive status surface found raw authority in the archive manifest.",
            http_status=409,
        )
    return manifest


def _blocked_response(
    *,
    request_id: str,
    reasons: list[dict[str, Any]],
    product_surface: Mapping[str, Any] | None = None,
    delivery: Mapping[str, Any] | None = None,
    operator: Mapping[str, Any] | None = None,
    validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    response = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": "blocked",
        "archive_mode": ARCHIVE_MODE,
        "runtime_version": SEC_EDGAR_DURABLE_DELIVERY_ARCHIVE_RUNTIME_VERSION,
        "operator_decision": OPERATOR_DECISION,
        "durable_delivery_archive_state": BLOCKED_STATE,
        "operator_product_surface_receipt_id": product_surface.get("operator_product_surface_receipt_id")
        if product_surface
        else None,
        "operator_product_surface_receipt_hash": product_surface.get("operator_product_surface_receipt_hash")
        if product_surface
        else None,
        "delivery_status_provenance_receipt_hash": delivery.get("delivery_status_provenance_receipt_hash")
        if delivery
        else None,
        "operator_inspection_receipt_hash": operator.get("operator_inspection_receipt_hash")
        if operator
        else None,
        "validation_receipt_hash": validation.get("validation_receipt_hash") if validation else None,
        "blocked_reasons": reasons,
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["repair_or_refresh_sec_edgar_operator_product_surface_receipt"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_durable_delivery_archive_blocked_response_raw_authority_exposed",
            "Blocked SEC EDGAR durable delivery archive response would expose raw authority.",
            http_status=409,
        )
    return response


def _validate_request_fields(fields: Mapping[str, Any]) -> None:
    keys = set(fields)
    blocked = sorted(keys & FORBIDDEN_REQUEST_FIELDS)
    nested_blocked = sorted(_find_forbidden_nested_fields(fields))
    if blocked or nested_blocked:
        _blocked(
            "sec_edgar_durable_delivery_archive_forbidden_request_fields",
            "SEC EDGAR durable delivery archive does not admit caller paths, URLs, bytes, commands, credentials, connector dispatch, model, browser, source expansion, parser expansion, frontend authority, accessions, tickers, company names, raw fact values, file responses, provider writes, or package mutations.",
            blocked_fields=[*blocked, *nested_blocked],
        )
    unknown = sorted(keys - ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_durable_delivery_archive_unknown_field",
            "SEC EDGAR durable delivery archive fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = fields.get("schema_id") or REQUEST_SCHEMA_ID
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_durable_delivery_archive_schema_not_admitted",
            "SEC EDGAR durable delivery archive requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    return find_forbidden_ref_paths(value, forbidden_keys=FORBIDDEN_REQUEST_FIELDS, prefix=prefix)


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(child) for child in value)
    if isinstance(value, str):
        lowered = value.lower()
        if (
            "https://www.sec.gov" in lowered
            or "https://data.sec.gov" in lowered
            or contains_forbidden_ref(value)
            or _ACCESSION_RE.search(value)
        ):
            return True
    return False


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
            "sec_edgar_durable_delivery_archive_receipt_id_invalid",
            "SEC EDGAR durable delivery archive status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["sec_edgar_durable_delivery_archive_receipt_id"],
        )
    path = _receipt_path(receipt_id)
    if not path.exists():
        _blocked(
            "sec_edgar_durable_delivery_archive_receipt_missing",
            "SEC EDGAR durable delivery archive receipt was not found.",
            http_status=404,
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_durable_delivery_archive_receipt_unreadable",
            "SEC EDGAR durable delivery archive receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("sec_edgar_durable_delivery_archive_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_durable_delivery_archive_receipt_invalid",
            "SEC EDGAR durable delivery archive receipt is invalid or mismatched.",
            http_status=409,
        )
    receipt_hash = str(receipt.get("sec_edgar_durable_delivery_archive_receipt_hash") or "")
    if receipt_hash[:24] != suffix or receipt_hash != _durable_delivery_archive_receipt_hash(receipt):
        _blocked(
            "sec_edgar_durable_delivery_archive_receipt_hash_mismatch",
            "SEC EDGAR durable delivery archive receipt hash is stale or mismatched.",
            http_status=409,
        )
    return receipt


def _durable_delivery_archive_receipt_hash(receipt: Mapping[str, Any]) -> str:
    return stable_hash(
        {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "archive_mode": ARCHIVE_MODE,
            "operator_decision": OPERATOR_DECISION,
            "operator_product_surface_receipt_hash": receipt.get("operator_product_surface_receipt_hash"),
            "archive_manifest_hash": receipt.get("archive_manifest_hash"),
            "archive_order_hash": receipt.get("archive_order_hash"),
            "source_authority_chain_hash": receipt.get("source_authority_chain_hash"),
            "redaction_manifest_hash": receipt.get("redaction_manifest_hash"),
        }
    )


def _required_receipt_field(receipt: Mapping[str, Any], key: str) -> str:
    value = str(receipt.get(key) or "").strip()
    if not value:
        _blocked(
            f"sec_edgar_durable_delivery_archive_{key}_missing",
            "SEC EDGAR durable delivery archive requires complete upstream receipt lineage.",
            http_status=409,
            blocked_fields=[key],
        )
    return value


def _write_archive_manifest(receipt_id: str, archive_manifest: Mapping[str, Any]) -> None:
    target = _archive_manifest_path(receipt_id)
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _blocked(
                "sec_edgar_durable_delivery_archive_manifest_unreadable",
                "SEC EDGAR durable delivery archive manifest could not be read.",
                http_status=409,
                blocked_fields=[exc.__class__.__name__],
            )
        if stable_hash(existing) != stable_hash(archive_manifest):
            _blocked(
                "sec_edgar_durable_delivery_archive_manifest_conflict",
                "SEC EDGAR durable delivery archive manifest conflicts with existing archive authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(archive_manifest), sort_keys=True, indent=2) + "\n")


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["sec_edgar_durable_delivery_archive_receipt_id"]))
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
            "sec_edgar_durable_delivery_archive_receipt_write_failed",
            "SEC EDGAR durable delivery archive receipt could not be recorded.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not target.exists():
        return None
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_durable_delivery_archive_request_binding_unreadable",
            "SEC EDGAR durable delivery archive request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_durable_delivery_archive_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "durable_delivery_archive_basis_hash": basis_hash,
        "sec_edgar_durable_delivery_archive_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("durable_delivery_archive_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_durable_delivery_archive_request_binding_conflict",
                "SEC EDGAR durable delivery archive request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")
    except FileExistsError:
        existing = _read_request_binding(request_id) or {}
        if existing.get("durable_delivery_archive_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_durable_delivery_archive_request_binding_conflict",
                "SEC EDGAR durable delivery archive request binding conflicts with existing authority.",
                http_status=409,
            )
    except OSError as exc:
        _blocked(
            "sec_edgar_durable_delivery_archive_request_binding_write_failed",
            "SEC EDGAR durable delivery archive request binding could not be recorded.",
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
        "internal_webhook_dispatch_enabled": False,
        "candidate_b_pdf_only_routing_performed": False,
        "taxonomy_network_resolution_performed": False,
        "sec_companyfacts_api_called": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "browser_storage_authority_enabled": False,
        "financial_statement_semantics_finalized": False,
        "cross_company_comparability_admitted": False,
        "comparability_normalization_performed": False,
    }


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _archive_manifest_path(receipt_id: str) -> Path:
    return _root() / "archive-manifests" / f"{receipt_id}.json"


def _request_bindings_dir() -> Path:
    return _root() / "request-bindings"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_durable_delivery_archive_storage_root_unavailable",
            "SEC EDGAR durable delivery archive requires the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            "sec_edgar_durable_delivery_archive_required_field_missing",
            "A required SEC EDGAR durable delivery archive field is missing or empty.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_durable_delivery_archive_{key}_not_admitted",
            "SEC EDGAR durable delivery archive request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _reason(
    reason: str,
    *,
    message: str | None = None,
    blocked_fields: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    item: dict[str, Any] = {"reason": reason}
    if message:
        item["message"] = message
    if blocked_fields:
        item["blocked_fields"] = blocked_fields
    item.update(extra)
    return item


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
