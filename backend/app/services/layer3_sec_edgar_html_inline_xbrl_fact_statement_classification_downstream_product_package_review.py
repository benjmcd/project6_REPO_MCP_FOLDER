from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_preview.v1"
)
REQUEST_SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_preview_request.v1"
)
STATUS_SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_preview_status.v1"
)
SCHEMA_VERSION = 1
PACKAGE_REVIEW_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_v1"
PRODUCT_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_v1"
CLASSIFICATION_MODE = "sec_edgar_html_inline_xbrl_fact_to_statement_classification_v1"
OPERATOR_DECISION = "preview_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review"
READY_STATE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_ready"
BLOCKED_STATE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_blocked"
SOURCE_FAMILY = "sec_edgar_html_inline_xbrl"
RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-statement-candidate-package-review-preview"
RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-statement-candidate-package-review-preview"
REDACTION_POLICY_ID = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_hash_v1"
PACKAGE_KINDS = ("canonical_internal", "review_facing", "user_facing")

_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "package_review_mode",
    "operator_decision",
    "downstream_product_receipt_id",
    "downstream_product_receipt_hash",
    "expected_statement_classification_receipt_hash",
    "expected_fact_authority_receipt_hash",
    "expected_fact_material_bridge_receipt_hash",
    "expected_parser_receipt_hash",
    "expected_product_manifest_hash",
    "expected_statement_candidate_product_hash",
    "expected_product_order_hash",
    "expected_inspection_summary_hash",
    "expected_redaction_manifest_hash",
    "expected_downstream_readiness_hash",
    "operator_confirmation",
    "actor",
}
_FORBIDDEN_INPUT_KEYS = {
    "path",
    "local_path",
    "raw_path",
    "url",
    "raw_url",
    "href",
    "html",
    "raw_html",
    "file",
    "bytes",
    "artifact_bytes",
    "value",
    "value_text",
    "fact_value",
    "raw_fact_value",
    "raw_fact_values",
    "package",
    "package_row",
    "package_payload",
    "package_review_decision",
    "review_submit",
    "handoff",
    "export",
    "delivery",
    "taxonomy_network_resolution",
    "sec_companyfacts_api",
    "standalone_xml_xbrl",
    "connector_dispatch",
    "provider",
    "provider_object_write",
    "rag",
    "model",
    "browser_storage",
    "frontend_authority",
    "full_mockup",
}
_RAW_URL_RE = re.compile(r"\b(?:https?|file)://", re.IGNORECASE)
_LOCAL_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|\\\\|/tmp/|/var/|/home/)", re.IGNORECASE)


def preview_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review(
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "package_review_mode", PACKAGE_REVIEW_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    product_receipt_id = _required(request, "downstream_product_receipt_id")
    product_receipt_hash = _required_hash(request, "downstream_product_receipt_hash")
    if request.get("operator_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            downstream_product_receipt_hash=product_receipt_hash,
            reasons=[_reason("missing_operator_confirmation")],
        )

    product = (
        layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product
        .inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_status(product_receipt_id)
    )
    _validate_product_authority(request, product, product_receipt_hash)

    product_manifest = dict(product["product_manifest"])
    candidate_package_manifest = _candidate_package_manifest(product, product_manifest)
    candidate_package_manifest_hash = stable_hash(candidate_package_manifest)
    review_readiness_manifest = _review_readiness_manifest(product, candidate_package_manifest)
    review_readiness_hash = stable_hash(review_readiness_manifest)
    redaction_manifest = _redaction_manifest(product)
    redaction_manifest_hash = stable_hash(redaction_manifest)
    package_order_hash = stable_hash(
        [
            {
                "package_kind": package["package_kind"],
                "package_order": package["package_order"],
                "package_evidence_hash": package["package_evidence_hash"],
            }
            for package in candidate_package_manifest["candidate_packages"]
        ]
    )
    receipt_hash = _package_review_preview_hash(
        product=product,
        candidate_package_manifest_hash=candidate_package_manifest_hash,
        review_readiness_hash=review_readiness_hash,
        package_order_hash=package_order_hash,
        redaction_manifest_hash=redaction_manifest_hash,
    )
    binding = _read_request_binding(request_id)
    if binding and binding.get("package_review_preview_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR HTML/iXBRL package-review preview basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["package_review_preview_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "package_review_preview_state": READY_STATE,
        "package_review_preview_receipt_id": receipt_id,
        "package_review_preview_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "package_review_preview_receipt_hash": receipt_hash,
        "downstream_product_receipt_id": product["downstream_product_receipt_id"],
        "downstream_product_receipt_hash": product["downstream_product_receipt_hash"],
        "statement_classification_receipt_id": product["statement_classification_receipt_id"],
        "statement_classification_receipt_hash": product["statement_classification_receipt_hash"],
        "fact_authority_receipt_hash": product["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_hash": product["fact_material_bridge_receipt_hash"],
        "parser_receipt_hash": product["parser_receipt_hash"],
        "source_family": SOURCE_FAMILY,
        "typed_content_contract_id": product["typed_content_contract_id"],
        "candidate_package_manifest": candidate_package_manifest,
        "candidate_package_manifest_hash": candidate_package_manifest_hash,
        "review_readiness_manifest": review_readiness_manifest,
        "review_readiness_hash": review_readiness_hash,
        "package_order_hash": package_order_hash,
        "redaction_manifest": redaction_manifest,
        "redaction_manifest_hash": redaction_manifest_hash,
        "product_manifest_hash": product["product_manifest_hash"],
        "statement_candidate_product_hash": product["statement_candidate_product_hash"],
        "product_order_hash": product["product_order_hash"],
        "inspection_summary_hash": product["inspection_summary_hash"],
        "downstream_readiness_hash": product["downstream_readiness_hash"],
        "authority_hashes": _authority_hashes(product),
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "request_id_hash": _sha256_text(request_id),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt_id)
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_status(
    receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-html-inline-xbrl-statement-candidate-package-review-preview-status-{receipt['package_review_preview_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def _validate_product_authority(
    request: Mapping[str, Any],
    product: Mapping[str, Any],
    product_receipt_hash: str,
) -> None:
    if str(product.get("downstream_product_receipt_hash") or "") != product_receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_downstream_product_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package-review preview requires downstream product receipt hash parity.",
            http_status=409,
            blocked_fields=["downstream_product_receipt_hash"],
        )
    if product.get("product_mode") != PRODUCT_MODE or product.get("product_state") != (
        "sec_edgar_html_inline_xbrl_statement_candidate_product_ready"
    ):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_product_not_ready",
            "SEC EDGAR HTML/iXBRL package-review preview requires a ready statement-candidate product receipt.",
            http_status=409,
            blocked_fields=["product_mode"],
        )
    _validate_downstream_product_receipt_hash(product, product_receipt_hash)
    checks = {
        "statement_classification_receipt_hash": "expected_statement_classification_receipt_hash",
        "fact_authority_receipt_hash": "expected_fact_authority_receipt_hash",
        "fact_material_bridge_receipt_hash": "expected_fact_material_bridge_receipt_hash",
        "parser_receipt_hash": "expected_parser_receipt_hash",
        "product_manifest_hash": "expected_product_manifest_hash",
        "statement_candidate_product_hash": "expected_statement_candidate_product_hash",
        "product_order_hash": "expected_product_order_hash",
        "inspection_summary_hash": "expected_inspection_summary_hash",
        "redaction_manifest_hash": "expected_redaction_manifest_hash",
        "downstream_readiness_hash": "expected_downstream_readiness_hash",
    }
    for authority_key, request_key in checks.items():
        expected = str(request.get(request_key) or product.get(authority_key) or "").strip()
        if not _is_hash(expected) or str(product.get(authority_key) or "") != expected:
            _blocked(
                f"sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_{authority_key}_mismatch",
                "SEC EDGAR HTML/iXBRL package-review preview requires downstream product authority hash parity.",
                http_status=409,
                blocked_fields=[request_key],
            )
    product_manifest = product.get("product_manifest")
    if not isinstance(product_manifest, Mapping) or stable_hash(product_manifest) != product.get("product_manifest_hash"):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_product_manifest_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package-review preview requires product manifest hash parity.",
            http_status=409,
            blocked_fields=["product_manifest_hash"],
        )
    if _contains_forbidden_output_ref(product):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_product_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL package-review preview refuses raw path, URL, token, or value authority.",
            http_status=409,
        )


def _validate_downstream_product_receipt_hash(product: Mapping[str, Any], product_receipt_hash: str) -> None:
    authority_hashes = product.get("authority_hashes")
    if not isinstance(authority_hashes, Mapping):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_downstream_product_authority_hashes_missing",
            "SEC EDGAR HTML/iXBRL package-review preview requires downstream product authority hashes.",
            http_status=409,
            blocked_fields=["authority_hashes"],
        )
    expected_hash = stable_hash(
        {
            "hash_version": (
                layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product.AUTHORITY_HASH_VERSION
            ),
            "product_mode": PRODUCT_MODE,
            "statement_classification_receipt_hash": product["statement_classification_receipt_hash"],
            "classification_inventory_hash": authority_hashes["classification_inventory_hash"],
            "classification_order_hash": authority_hashes["classification_order_hash"],
            "statement_group_inventory_hash": authority_hashes["statement_group_inventory_hash"],
            "unclassified_fact_inventory_hash": authority_hashes["unclassified_fact_inventory_hash"],
            "classification_diagnostics_hash": authority_hashes["classification_diagnostics_hash"],
            "product_manifest_hash": product["product_manifest_hash"],
            "statement_candidate_product_hash": product["statement_candidate_product_hash"],
            "product_order_hash": product["product_order_hash"],
            "inspection_summary_hash": product["inspection_summary_hash"],
            "redaction_manifest_hash": product["redaction_manifest_hash"],
            "downstream_readiness_hash": product["downstream_readiness_hash"],
        }
    )
    if expected_hash != product_receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_downstream_product_basis_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package-review preview requires recomputed downstream product authority hash parity.",
            http_status=409,
            blocked_fields=["downstream_product_receipt_hash"],
        )


def _candidate_package_manifest(
    product: Mapping[str, Any],
    product_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    role_group_refs = [
        {
            "statement_candidate_role": str(item["statement_candidate_role"]),
            "fact_count": int(item.get("fact_count") or 0),
            "first_fact_order": item.get("first_fact_order"),
            "last_fact_order": item.get("last_fact_order"),
            "fact_order_hash": str(item.get("fact_order_hash") or ""),
            "table_anchor_inventory_hash": str(item.get("table_anchor_inventory_hash") or ""),
            "role_group_hash": stable_hash(item),
            "raw_values_included": False,
        }
        for item in list(product_manifest.get("role_group_inventory") or [])
        if isinstance(item, Mapping)
    ]
    table_anchor_refs = [
        {
            "table_candidate_anchor_hash": str(item.get("table_candidate_anchor_hash") or ""),
            "statement_candidate_roles": list(item.get("statement_candidate_roles") or []),
            "table_anchor_crosswalk_hash": stable_hash(item),
            "raw_table_bytes_included": False,
        }
        for item in list(product_manifest.get("table_anchor_crosswalk") or [])
        if isinstance(item, Mapping)
    ]
    unknown_diagnostics = dict(product_manifest.get("unknown_fact_diagnostics") or {})
    evidence_refs = {
        "role_group_refs": role_group_refs,
        "role_group_ref_count": len(role_group_refs),
        "role_group_refs_hash": stable_hash(role_group_refs),
        "table_anchor_refs": table_anchor_refs,
        "table_anchor_ref_count": len(table_anchor_refs),
        "table_anchor_refs_hash": stable_hash(table_anchor_refs),
        "unknown_diagnostics_ref": {
            "unknown_or_unclassified_count": int(unknown_diagnostics.get("unknown_or_unclassified_count") or 0),
            "unknown_or_unclassified_inventory_hash": str(
                unknown_diagnostics.get("unknown_or_unclassified_inventory_hash") or ""
            ),
            "unknown_diagnostics_hash": stable_hash(unknown_diagnostics),
            "raw_values_included": False,
        },
    }
    evidence_hash = stable_hash(evidence_refs)
    candidate_packages = [
        {
            "package_kind": package_kind,
            "package_order": index,
            "preview_only": True,
            "package_evidence_hash": evidence_hash,
            "product_manifest_hash": str(product["product_manifest_hash"]),
            "statement_candidate_product_hash": str(product["statement_candidate_product_hash"]),
            "review_ready": True,
            "package_commit_enabled": False,
            "package_review_submit_enabled": False,
            "handoff_export_enabled": False,
            "delivery_enabled": False,
            "raw_values_included": False,
            "raw_html_included": False,
            "raw_urls_included": False,
        }
        for index, package_kind in enumerate(PACKAGE_KINDS, start=1)
    ]
    return {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_manifest.v1",
        "schema_version": SCHEMA_VERSION,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "source_family": SOURCE_FAMILY,
        "downstream_product_receipt_hash": str(product["downstream_product_receipt_hash"]),
        "product_manifest_hash": str(product["product_manifest_hash"]),
        "statement_candidate_product_hash": str(product["statement_candidate_product_hash"]),
        "package_kinds": list(PACKAGE_KINDS),
        "candidate_packages": candidate_packages,
        "evidence_refs": evidence_refs,
        "evidence_refs_hash": evidence_hash,
        "product_evidence_preserved": True,
        "final_financial_statement_semantics_claimed": False,
    }


def _review_readiness_manifest(
    product: Mapping[str, Any],
    candidate_package_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    product_manifest = dict(product["product_manifest"])
    unknown = dict(product_manifest.get("unknown_fact_diagnostics") or {})
    return {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_package_review_readiness.v1",
        "preview_ready": True,
        "redacted_projection": True,
        "package_kind_count": len(PACKAGE_KINDS),
        "package_kinds": list(PACKAGE_KINDS),
        "role_group_ref_count": candidate_package_manifest["evidence_refs"]["role_group_ref_count"],
        "table_anchor_ref_count": candidate_package_manifest["evidence_refs"]["table_anchor_ref_count"],
        "unknown_or_unclassified_count": int(unknown.get("unknown_or_unclassified_count") or 0),
        "product_evidence_preserved": True,
        "order_preserved": True,
        "package_construction_commit_enabled": False,
        "package_review_submit_enabled": False,
        "handoff_export_enabled": False,
        "delivery_enabled": False,
        "requires_future_package_construction_commit_slice": True,
        "raw_values_returned": False,
        "raw_html_returned": False,
        "raw_urls_returned": False,
        "final_financial_statement_semantics_claimed": False,
    }


def _redaction_manifest(product: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "redaction_policy_id": REDACTION_POLICY_ID,
        "source_product_redaction_manifest_hash": str(product["redaction_manifest_hash"]),
        "raw_fact_values_exposed": False,
        "raw_html_exposed": False,
        "raw_urls_exposed": False,
        "local_paths_exposed": False,
        "artifact_bytes_exposed": False,
        "dataset_storage_ref_exposed": False,
    }


def _package_review_preview_hash(
    *,
    product: Mapping[str, Any],
    candidate_package_manifest_hash: str,
    review_readiness_hash: str,
    package_order_hash: str,
    redaction_manifest_hash: str,
) -> str:
    return stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "package_review_mode": PACKAGE_REVIEW_MODE,
            "downstream_product_receipt_hash": product["downstream_product_receipt_hash"],
            "statement_classification_receipt_hash": product["statement_classification_receipt_hash"],
            "fact_authority_receipt_hash": product["fact_authority_receipt_hash"],
            "fact_material_bridge_receipt_hash": product["fact_material_bridge_receipt_hash"],
            "parser_receipt_hash": product["parser_receipt_hash"],
            "product_manifest_hash": product["product_manifest_hash"],
            "statement_candidate_product_hash": product["statement_candidate_product_hash"],
            "product_order_hash": product["product_order_hash"],
            "inspection_summary_hash": product["inspection_summary_hash"],
            "downstream_readiness_hash": product["downstream_readiness_hash"],
            "candidate_package_manifest_hash": candidate_package_manifest_hash,
            "review_readiness_hash": review_readiness_hash,
            "package_order_hash": package_order_hash,
            "redaction_manifest_hash": redaction_manifest_hash,
        }
    )


def _authority_hashes(product: Mapping[str, Any]) -> dict[str, str]:
    authority = dict(product.get("authority_hashes") or {})
    return {
        **{str(key): str(value) for key, value in authority.items()},
        "downstream_product_receipt_hash": str(product["downstream_product_receipt_hash"]),
        "statement_classification_receipt_hash": str(product["statement_classification_receipt_hash"]),
        "fact_authority_receipt_hash": str(product["fact_authority_receipt_hash"]),
        "fact_material_bridge_receipt_hash": str(product["fact_material_bridge_receipt_hash"]),
        "parser_receipt_hash": str(product["parser_receipt_hash"]),
        "product_manifest_hash": str(product["product_manifest_hash"]),
        "statement_candidate_product_hash": str(product["statement_candidate_product_hash"]),
        "product_order_hash": str(product["product_order_hash"]),
        "inspection_summary_hash": str(product["inspection_summary_hash"]),
        "redaction_manifest_hash": str(product["redaction_manifest_hash"]),
        "downstream_readiness_hash": str(product["downstream_readiness_hash"]),
    }


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    schema_id: str,
    idempotent_replay: bool,
) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="ready", schema_id=schema_id),
        "mode": PACKAGE_REVIEW_MODE,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "package_review_preview_state": receipt["package_review_preview_state"],
        "package_review_preview_receipt_id": receipt["package_review_preview_receipt_id"],
        "package_review_preview_receipt_ref": receipt["package_review_preview_receipt_ref"],
        "package_review_preview_receipt_hash": receipt["package_review_preview_receipt_hash"],
        "downstream_product_receipt_id": receipt["downstream_product_receipt_id"],
        "downstream_product_receipt_hash": receipt["downstream_product_receipt_hash"],
        "statement_classification_receipt_id": receipt["statement_classification_receipt_id"],
        "statement_classification_receipt_hash": receipt["statement_classification_receipt_hash"],
        "fact_authority_receipt_hash": receipt["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_hash": receipt["fact_material_bridge_receipt_hash"],
        "parser_receipt_hash": receipt["parser_receipt_hash"],
        "source_family": SOURCE_FAMILY,
        "typed_content_contract_id": receipt["typed_content_contract_id"],
        "candidate_package_manifest": dict(receipt["candidate_package_manifest"]),
        "candidate_package_manifest_hash": receipt["candidate_package_manifest_hash"],
        "review_readiness_manifest": dict(receipt["review_readiness_manifest"]),
        "review_readiness_hash": receipt["review_readiness_hash"],
        "package_order_hash": receipt["package_order_hash"],
        "redaction_manifest_hash": receipt["redaction_manifest_hash"],
        "product_manifest_hash": receipt["product_manifest_hash"],
        "statement_candidate_product_hash": receipt["statement_candidate_product_hash"],
        "product_order_hash": receipt["product_order_hash"],
        "inspection_summary_hash": receipt["inspection_summary_hash"],
        "downstream_readiness_hash": receipt["downstream_readiness_hash"],
        "authority_hashes": dict(receipt["authority_hashes"]),
        "status_projection": _status_projection(receipt),
        "cache": {"idempotent_replay": idempotent_replay, "network_request_made": False},
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["select SEC HTML/iXBRL statement candidate package construction commit slice"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL package-review preview would expose raw path, URL, token, or value authority.",
            http_status=409,
        )
    return response


def _status_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    readiness = dict(receipt["review_readiness_manifest"])
    return {
        "ready": True,
        "redacted_projection": True,
        "package_kind_count": readiness["package_kind_count"],
        "package_kinds": list(readiness["package_kinds"]),
        "unknown_or_unclassified_count": readiness["unknown_or_unclassified_count"],
        "product_evidence_preserved": True,
        "candidate_package_manifest_hash": receipt["candidate_package_manifest_hash"],
        "review_readiness_hash": receipt["review_readiness_hash"],
        "package_order_hash": receipt["package_order_hash"],
        "product_manifest_hash": receipt["product_manifest_hash"],
        "statement_candidate_product_hash": receipt["statement_candidate_product_hash"],
        "product_order_hash": receipt["product_order_hash"],
        "redaction_manifest_hash": receipt["redaction_manifest_hash"],
        "downstream_readiness_hash": receipt["downstream_readiness_hash"],
        "raw_values_returned": False,
        "raw_html_returned": False,
        "raw_urls_returned": False,
        "dataset_storage_ref_returned": False,
        "package_rows_written": False,
        "package_review_submit_enabled": False,
        "final_financial_statement_semantics_claimed": False,
        "next_allowed_actions": ["select_sec_edgar_html_inline_xbrl_statement_candidate_package_construction_commit"],
    }


def _blocked_response(
    *,
    request_id: str,
    downstream_product_receipt_hash: str,
    reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="blocked", schema_id=SCHEMA_ID),
        "mode": PACKAGE_REVIEW_MODE,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "package_review_preview_state": BLOCKED_STATE,
        "package_review_preview_receipt_id": None,
        "package_review_preview_receipt_ref": None,
        "package_review_preview_receipt_hash": None,
        "downstream_product_receipt_hash": downstream_product_receipt_hash,
        "candidate_package_manifest": None,
        "candidate_package_manifest_hash": None,
        "review_readiness_manifest": None,
        "review_readiness_hash": None,
        "package_order_hash": None,
        "redaction_manifest_hash": None,
        "status_projection": {
            "ready": False,
            "redacted_projection": True,
            "blocked_reasons": reasons,
            "next_allowed_actions": ["refresh_sec_edgar_html_inline_xbrl_statement_candidate_product_authority"],
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["refresh SEC HTML/iXBRL statement-candidate product authority"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_blocked_response_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL package-review preview blocked response would expose raw authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key.lower() in _FORBIDDEN_INPUT_KEYS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL package-review preview rejects caller paths, URLs, HTML, values, bytes, package rows, review submit, handoff, delivery, connector dispatch, model, browser, source-expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(set(request) - _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_unknown_field",
            "SEC EDGAR HTML/iXBRL package-review preview fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL package-review preview requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["package_review_preview_receipt_id"]))
    if target.exists():
        _read_verified_receipt(target.stem)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(receipt), sort_keys=True, indent=2) + "\n")


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
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_receipt_id_invalid",
            "SEC EDGAR HTML/iXBRL package-review preview status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["package_review_preview_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_receipt_missing",
            "SEC EDGAR HTML/iXBRL package-review preview receipt was not found.",
            http_status=404,
            blocked_fields=["package_review_preview_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL package-review preview receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("package_review_preview_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_receipt_invalid",
            "SEC EDGAR HTML/iXBRL package-review preview receipt is invalid or mismatched.",
            http_status=409,
        )
    _validate_stored_receipt_manifest_hashes(receipt)
    expected_hash = _package_review_preview_hash(
        product=receipt,
        candidate_package_manifest_hash=str(receipt.get("candidate_package_manifest_hash") or ""),
        review_readiness_hash=str(receipt.get("review_readiness_hash") or ""),
        package_order_hash=str(receipt.get("package_order_hash") or ""),
        redaction_manifest_hash=str(receipt.get("redaction_manifest_hash") or ""),
    )
    if receipt.get("package_review_preview_receipt_hash") != expected_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_receipt_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package-review preview receipt hash does not match stored authority.",
            http_status=409,
        )
    return receipt


def _validate_stored_receipt_manifest_hashes(receipt: Mapping[str, Any]) -> None:
    candidate_manifest = receipt.get("candidate_package_manifest")
    if not isinstance(candidate_manifest, Mapping) or stable_hash(candidate_manifest) != receipt.get(
        "candidate_package_manifest_hash"
    ):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_candidate_manifest_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package-review preview receipt candidate manifest hash is invalid.",
            http_status=409,
            blocked_fields=["candidate_package_manifest_hash"],
        )
    readiness = receipt.get("review_readiness_manifest")
    if not isinstance(readiness, Mapping) or stable_hash(readiness) != receipt.get("review_readiness_hash"):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_readiness_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package-review preview receipt readiness hash is invalid.",
            http_status=409,
            blocked_fields=["review_readiness_hash"],
        )
    redaction = receipt.get("redaction_manifest")
    if not isinstance(redaction, Mapping) or stable_hash(redaction) != receipt.get("redaction_manifest_hash"):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_redaction_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package-review preview receipt redaction hash is invalid.",
            http_status=409,
            blocked_fields=["redaction_manifest_hash"],
        )
    package_order_hash = stable_hash(
        [
            {
                "package_kind": package["package_kind"],
                "package_order": package["package_order"],
                "package_evidence_hash": package["package_evidence_hash"],
            }
            for package in list(candidate_manifest.get("candidate_packages") or [])
            if isinstance(package, Mapping)
        ]
    )
    if package_order_hash != receipt.get("package_order_hash"):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_package_order_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package-review preview receipt package order hash is invalid.",
            http_status=409,
            blocked_fields=["package_order_hash"],
        )


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    path = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_request_binding_unreadable",
            "SEC EDGAR HTML/iXBRL package-review preview request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "package_review_preview_basis_hash": basis_hash,
        "package_review_preview_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("package_review_preview_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_request_binding_conflict",
                "SEC EDGAR HTML/iXBRL package-review preview request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            child = f"{prefix}.{key_text}" if prefix else key_text
            if key_text.lower() in _FORBIDDEN_INPUT_KEYS:
                found.append(child)
            found.extend(_find_forbidden_nested_fields(nested, child))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_find_forbidden_nested_fields(nested, f"{prefix}[{index}]"))
    elif isinstance(value, str) and (_RAW_URL_RE.search(value) or _LOCAL_PATH_RE.search(value)):
        found.append(prefix or "request_body")
    return found


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        text = value.strip()
        return bool(_LOCAL_PATH_RE.search(text) or text.startswith(("http://", "https://", "file://", "\\\\")))
    return False


def _negative_invariants() -> dict[str, bool]:
    return {
        "downstream_product_receipt_required": True,
        "statement_classification_receipt_required": True,
        "fact_authority_receipt_required": True,
        "fact_material_bridge_receipt_required": True,
        "read_only_preview": True,
        "package_rows_written": False,
        "package_payload_written": False,
        "package_construction_commit_enabled": False,
        "package_review_submit_enabled": False,
        "handoff_export_enabled": False,
        "delivery_enabled": False,
        "live_sec_network_fetch_performed_by_package_review": False,
        "html_inline_xbrl_reparse_enabled": False,
        "standalone_xml_xbrl_fact_authority_enabled": False,
        "sec_companyfacts_api_runtime_enabled": False,
        "taxonomy_network_resolution_enabled": False,
        "financial_statement_semantics_finalized": False,
        "downstream_product_mutated": False,
        "statement_classification_mutated": False,
        "source_expansion_admitted": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "raw_fact_values_exposed": False,
    }


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _request_bindings_dir() -> Path:
    return _root() / "request-bindings"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_storage_root_unavailable",
            "SEC EDGAR HTML/iXBRL package-review preview requires the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _base_response(*, request_id: str, status: str, schema_id: str) -> dict[str, Any]:
    return {
        "schema_id": schema_id,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": status,
    }


def _reason(reason: str, **details: Any) -> dict[str, Any]:
    return {"reason": reason, **details}


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_{key}_missing",
            f"SEC EDGAR HTML/iXBRL package-review preview requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_{key}_invalid",
            f"SEC EDGAR HTML/iXBRL package-review preview requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_package_review_preview_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL package-review preview request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _is_hash(value: str) -> bool:
    return len(value) == 64 and _is_hex(value)


def _is_hex(value: str) -> bool:
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


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
