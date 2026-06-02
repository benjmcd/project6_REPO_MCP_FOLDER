from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review
from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_contract import (
    STATEMENT_CLASSIFICATION_MODE,
)
from app.services.layer3_sec_edgar_ref_safety import contains_forbidden_ref, find_forbidden_ref_paths
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction_commit.v1"
)
REQUEST_SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction_commit_request.v1"
)
STATUS_SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction_commit_status.v1"
)
SCHEMA_VERSION = 1
PACKAGE_CONSTRUCTION_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_commit_v1"
PACKAGE_REVIEW_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_v1"
PRODUCT_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_v1"
CLASSIFICATION_MODE = STATEMENT_CLASSIFICATION_MODE
OPERATOR_DECISION = "commit_sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction"
READY_STATE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_ready"
BLOCKED_STATE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_blocked"
SOURCE_FAMILY = "sec_edgar_html_inline_xbrl"
RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-statement-candidate-package-construction"
RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-statement-candidate-package-construction"
REDACTION_POLICY_ID = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_hash_v1"
PACKAGE_KINDS = ("canonical_internal", "review_facing", "user_facing")

_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "package_construction_mode",
    "operator_decision",
    "package_review_preview_receipt_id",
    "package_review_preview_receipt_hash",
    "expected_candidate_package_manifest_hash",
    "expected_review_readiness_hash",
    "expected_package_order_hash",
    "expected_redaction_manifest_hash",
    "expected_downstream_product_receipt_hash",
    "expected_statement_classification_receipt_hash",
    "expected_fact_authority_receipt_hash",
    "expected_fact_material_bridge_receipt_hash",
    "expected_parser_receipt_hash",
    "expected_product_manifest_hash",
    "expected_statement_candidate_product_hash",
    "expected_product_order_hash",
    "expected_inspection_summary_hash",
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
    "connector",
    "provider",
    "rag",
    "model",
    "browser_storage",
    "frontend_authority",
}
def commit_sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction(
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    request = _normalize_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "package_construction_mode", PACKAGE_CONSTRUCTION_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    preview_receipt_id = _required(request, "package_review_preview_receipt_id")
    preview_receipt_hash = _required_hash(request, "package_review_preview_receipt_hash")
    if request.get("operator_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            package_review_preview_receipt_hash=preview_receipt_hash,
            reasons=[_reason("missing_operator_confirmation")],
        )

    preview = (
        layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review
        .inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_status(preview_receipt_id)
    )
    _validate_preview_authority(request, preview, preview_receipt_hash)
    payload_manifest = _package_payload_manifest(preview)
    payload_manifest_hash = stable_hash(payload_manifest)
    payload_order_hash = stable_hash(
        [
            {
                "package_kind": item["package_kind"],
                "package_order": item["package_order"],
                "payload_ref": item["payload_ref"],
                "payload_hash": item["payload_hash"],
            }
            for item in payload_manifest["payloads"]
        ]
    )
    receipt_hash = _construction_hash(
        preview=preview,
        payload_manifest_hash=payload_manifest_hash,
        payload_order_hash=payload_order_hash,
    )

    binding = _read_request_binding(request_id)
    if binding and binding.get("package_construction_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR HTML/iXBRL package construction basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["package_construction_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "package_construction_state": READY_STATE,
        "package_construction_receipt_id": receipt_id,
        "package_construction_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "package_construction_receipt_hash": receipt_hash,
        "package_review_preview_receipt_id": preview["package_review_preview_receipt_id"],
        "package_review_preview_receipt_hash": preview_receipt_hash,
        "downstream_product_receipt_hash": preview["downstream_product_receipt_hash"],
        "statement_classification_receipt_hash": preview["statement_classification_receipt_hash"],
        "fact_authority_receipt_hash": preview["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_hash": preview["fact_material_bridge_receipt_hash"],
        "parser_receipt_hash": preview["parser_receipt_hash"],
        "source_family": SOURCE_FAMILY,
        "typed_content_contract_id": preview["typed_content_contract_id"],
        "candidate_package_manifest_hash": preview["candidate_package_manifest_hash"],
        "review_readiness_hash": preview["review_readiness_hash"],
        "package_order_hash": preview["package_order_hash"],
        "redaction_manifest_hash": preview["redaction_manifest_hash"],
        "product_manifest_hash": preview["product_manifest_hash"],
        "statement_candidate_product_hash": preview["statement_candidate_product_hash"],
        "product_order_hash": preview["product_order_hash"],
        "inspection_summary_hash": preview["inspection_summary_hash"],
        "downstream_readiness_hash": preview["downstream_readiness_hash"],
        "package_payload_manifest": payload_manifest,
        "package_payload_manifest_hash": payload_manifest_hash,
        "package_payload_order_hash": payload_order_hash,
        "authority_hashes": _authority_hashes(preview, payload_manifest_hash, payload_order_hash),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "negative_invariants": _negative_invariants(),
        "actor_hash": _sha256_text(str(request.get("actor") or "system")),
        "created_at": _server_time(),
    }
    _write_payload_artifacts(receipt_id, payload_manifest)
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt_id)
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_status(
    receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-html-inline-xbrl-statement-candidate-package-construction-status-{receipt['package_construction_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def _validate_preview_authority(
    request: Mapping[str, Any],
    preview: Mapping[str, Any],
    preview_receipt_hash: str,
) -> None:
    if str(preview.get("package_review_preview_receipt_hash") or "") != preview_receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_preview_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package construction requires package-review preview receipt hash parity.",
            http_status=409,
            blocked_fields=["package_review_preview_receipt_hash"],
        )
    if preview.get("package_review_preview_state") != (
        "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_ready"
    ):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_preview_not_ready",
            "SEC EDGAR HTML/iXBRL package construction requires a ready package-review preview receipt.",
            http_status=409,
            blocked_fields=["package_review_preview_receipt_id"],
        )
    checks = {
        "candidate_package_manifest_hash": "expected_candidate_package_manifest_hash",
        "review_readiness_hash": "expected_review_readiness_hash",
        "package_order_hash": "expected_package_order_hash",
        "redaction_manifest_hash": "expected_redaction_manifest_hash",
        "downstream_product_receipt_hash": "expected_downstream_product_receipt_hash",
        "statement_classification_receipt_hash": "expected_statement_classification_receipt_hash",
        "fact_authority_receipt_hash": "expected_fact_authority_receipt_hash",
        "fact_material_bridge_receipt_hash": "expected_fact_material_bridge_receipt_hash",
        "parser_receipt_hash": "expected_parser_receipt_hash",
        "product_manifest_hash": "expected_product_manifest_hash",
        "statement_candidate_product_hash": "expected_statement_candidate_product_hash",
        "product_order_hash": "expected_product_order_hash",
        "inspection_summary_hash": "expected_inspection_summary_hash",
        "downstream_readiness_hash": "expected_downstream_readiness_hash",
    }
    for preview_key, request_key in checks.items():
        expected = request.get(request_key)
        if expected is not None and str(preview.get(preview_key) or "") != str(expected):
            _blocked(
                f"sec_edgar_html_inline_xbrl_statement_candidate_package_construction_{preview_key}_mismatch",
                f"SEC EDGAR HTML/iXBRL package construction requires {preview_key} parity.",
                http_status=409,
                blocked_fields=[request_key],
            )
    if stable_hash(preview.get("candidate_package_manifest") or {}) != str(
        preview.get("candidate_package_manifest_hash") or ""
    ):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_candidate_manifest_tampered",
            "SEC EDGAR HTML/iXBRL package construction requires intact candidate package manifest authority.",
            http_status=409,
        )


def _package_payload_manifest(preview: Mapping[str, Any]) -> dict[str, Any]:
    manifest = dict(preview.get("candidate_package_manifest") or {})
    evidence_refs = dict(manifest.get("evidence_refs") or {})
    payloads = []
    for package in list(manifest.get("candidate_packages") or []):
        if not isinstance(package, Mapping):
            continue
        package_kind = str(package.get("package_kind") or "")
        if package_kind not in PACKAGE_KINDS:
            continue
        payload = {
            "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_package_payload.v1",
            "schema_version": SCHEMA_VERSION,
            "package_kind": package_kind,
            "package_order": int(package.get("package_order") or 0),
            "source_family": SOURCE_FAMILY,
            "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
            "package_review_preview_receipt_hash": preview["package_review_preview_receipt_hash"],
            "candidate_package_manifest_hash": preview["candidate_package_manifest_hash"],
            "review_readiness_hash": preview["review_readiness_hash"],
            "package_order_hash": preview["package_order_hash"],
            "redaction_manifest_hash": preview["redaction_manifest_hash"],
            "product_manifest_hash": preview["product_manifest_hash"],
            "statement_candidate_product_hash": preview["statement_candidate_product_hash"],
            "package_evidence_hash": str(package.get("package_evidence_hash") or ""),
            "evidence_refs_hash": str(manifest.get("evidence_refs_hash") or ""),
            "role_group_ref_count": int(evidence_refs.get("role_group_ref_count") or 0),
            "table_anchor_ref_count": int(evidence_refs.get("table_anchor_ref_count") or 0),
            "unknown_diagnostics_hash": stable_hash(evidence_refs.get("unknown_diagnostics_ref") or {}),
            "product_evidence_preserved": True,
            "payload_redacted": True,
            "raw_values_included": False,
            "raw_html_included": False,
            "raw_urls_included": False,
            "artifact_bytes_included": False,
            "final_financial_statement_semantics_claimed": False,
        }
        payload_hash = stable_hash(payload)
        payloads.append(
            {
                "package_kind": package_kind,
                "package_order": payload["package_order"],
                "payload_ref": f"sec-edgar-html-inline-xbrl-package-payload:{payload_hash[:24]}",
                "payload_hash": payload_hash,
                "payload_byte_count": len(json.dumps(payload, sort_keys=True).encode("utf-8")),
                "payload_redacted": True,
                "payload": payload,
            }
        )
    payloads.sort(key=lambda item: int(item["package_order"]))
    return {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_package_payload_manifest.v1",
        "schema_version": SCHEMA_VERSION,
        "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
        "package_review_preview_receipt_hash": preview["package_review_preview_receipt_hash"],
        "package_kinds": [item["package_kind"] for item in payloads],
        "package_kind_count": len(payloads),
        "payloads": payloads,
        "payloads_redacted": True,
        "product_evidence_preserved": True,
        "package_review_submit_enabled": False,
        "handoff_export_enabled": False,
        "delivery_enabled": False,
    }


def _construction_hash(
    *,
    preview: Mapping[str, Any],
    payload_manifest_hash: str,
    payload_order_hash: str,
) -> str:
    return stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
            "package_review_preview_receipt_hash": preview["package_review_preview_receipt_hash"],
            "candidate_package_manifest_hash": preview["candidate_package_manifest_hash"],
            "review_readiness_hash": preview["review_readiness_hash"],
            "package_order_hash": preview["package_order_hash"],
            "redaction_manifest_hash": preview["redaction_manifest_hash"],
            "downstream_product_receipt_hash": preview["downstream_product_receipt_hash"],
            "statement_classification_receipt_hash": preview["statement_classification_receipt_hash"],
            "fact_authority_receipt_hash": preview["fact_authority_receipt_hash"],
            "fact_material_bridge_receipt_hash": preview["fact_material_bridge_receipt_hash"],
            "parser_receipt_hash": preview["parser_receipt_hash"],
            "product_manifest_hash": preview["product_manifest_hash"],
            "statement_candidate_product_hash": preview["statement_candidate_product_hash"],
            "product_order_hash": preview["product_order_hash"],
            "inspection_summary_hash": preview["inspection_summary_hash"],
            "downstream_readiness_hash": preview["downstream_readiness_hash"],
            "package_payload_manifest_hash": payload_manifest_hash,
            "package_payload_order_hash": payload_order_hash,
        }
    )


def _authority_hashes(preview: Mapping[str, Any], payload_manifest_hash: str, payload_order_hash: str) -> dict[str, str]:
    return {
        "package_review_preview_receipt_hash": str(preview["package_review_preview_receipt_hash"]),
        "candidate_package_manifest_hash": str(preview["candidate_package_manifest_hash"]),
        "review_readiness_hash": str(preview["review_readiness_hash"]),
        "package_order_hash": str(preview["package_order_hash"]),
        "redaction_manifest_hash": str(preview["redaction_manifest_hash"]),
        "downstream_product_receipt_hash": str(preview["downstream_product_receipt_hash"]),
        "statement_classification_receipt_hash": str(preview["statement_classification_receipt_hash"]),
        "fact_authority_receipt_hash": str(preview["fact_authority_receipt_hash"]),
        "fact_material_bridge_receipt_hash": str(preview["fact_material_bridge_receipt_hash"]),
        "parser_receipt_hash": str(preview["parser_receipt_hash"]),
        "product_manifest_hash": str(preview["product_manifest_hash"]),
        "statement_candidate_product_hash": str(preview["statement_candidate_product_hash"]),
        "product_order_hash": str(preview["product_order_hash"]),
        "inspection_summary_hash": str(preview["inspection_summary_hash"]),
        "downstream_readiness_hash": str(preview["downstream_readiness_hash"]),
        "package_payload_manifest_hash": payload_manifest_hash,
        "package_payload_order_hash": payload_order_hash,
    }


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    schema_id: str,
    idempotent_replay: bool,
) -> dict[str, Any]:
    payload_manifest = _redacted_payload_manifest(receipt["package_payload_manifest"])
    response = {
        **_base_response(request_id=request_id, status="ready", schema_id=schema_id),
        "mode": PACKAGE_CONSTRUCTION_MODE,
        "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "package_construction_state": receipt["package_construction_state"],
        "package_construction_receipt_id": receipt["package_construction_receipt_id"],
        "package_construction_receipt_ref": receipt["package_construction_receipt_ref"],
        "package_construction_receipt_hash": receipt["package_construction_receipt_hash"],
        "package_review_preview_receipt_id": receipt["package_review_preview_receipt_id"],
        "package_review_preview_receipt_hash": receipt["package_review_preview_receipt_hash"],
        "downstream_product_receipt_hash": receipt["downstream_product_receipt_hash"],
        "statement_classification_receipt_hash": receipt["statement_classification_receipt_hash"],
        "fact_authority_receipt_hash": receipt["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_hash": receipt["fact_material_bridge_receipt_hash"],
        "parser_receipt_hash": receipt["parser_receipt_hash"],
        "source_family": SOURCE_FAMILY,
        "typed_content_contract_id": receipt["typed_content_contract_id"],
        "candidate_package_manifest_hash": receipt["candidate_package_manifest_hash"],
        "review_readiness_hash": receipt["review_readiness_hash"],
        "package_order_hash": receipt["package_order_hash"],
        "redaction_manifest_hash": receipt["redaction_manifest_hash"],
        "product_manifest_hash": receipt["product_manifest_hash"],
        "statement_candidate_product_hash": receipt["statement_candidate_product_hash"],
        "product_order_hash": receipt["product_order_hash"],
        "inspection_summary_hash": receipt["inspection_summary_hash"],
        "downstream_readiness_hash": receipt["downstream_readiness_hash"],
        "package_payload_manifest": payload_manifest,
        "package_payload_manifest_hash": receipt["package_payload_manifest_hash"],
        "package_payload_order_hash": receipt["package_payload_order_hash"],
        "package_kinds": list(payload_manifest["package_kinds"]),
        "payload_refs": [item["payload_ref"] for item in payload_manifest["payloads"]],
        "payload_hashes": [item["payload_hash"] for item in payload_manifest["payloads"]],
        "authority_hashes": dict(receipt["authority_hashes"]),
        "status_projection": _status_projection(receipt),
        "cache": {"idempotent_replay": idempotent_replay, "network_request_made": False},
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["select SEC HTML/iXBRL statement candidate package review submit slice"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL package construction would expose raw path, URL, token, or value authority.",
            http_status=409,
        )
    return response


def _redacted_payload_manifest(payload_manifest: Mapping[str, Any]) -> dict[str, Any]:
    redacted_payloads = []
    for item in list(payload_manifest.get("payloads") or []):
        if not isinstance(item, Mapping):
            continue
        redacted_payloads.append(
            {
                "package_kind": item.get("package_kind"),
                "package_order": item.get("package_order"),
                "payload_ref": item.get("payload_ref"),
                "payload_hash": item.get("payload_hash"),
                "payload_byte_count": item.get("payload_byte_count"),
                "payload_redacted": True,
            }
        )
    return {
        "schema_id": payload_manifest.get("schema_id"),
        "schema_version": payload_manifest.get("schema_version"),
        "package_construction_mode": payload_manifest.get("package_construction_mode"),
        "package_review_preview_receipt_hash": payload_manifest.get("package_review_preview_receipt_hash"),
        "package_kinds": list(payload_manifest.get("package_kinds") or []),
        "package_kind_count": int(payload_manifest.get("package_kind_count") or 0),
        "payloads": redacted_payloads,
        "payloads_redacted": True,
        "product_evidence_preserved": payload_manifest.get("product_evidence_preserved") is True,
        "package_review_submit_enabled": False,
        "handoff_export_enabled": False,
        "delivery_enabled": False,
    }


def _status_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    payload_manifest = _redacted_payload_manifest(receipt["package_payload_manifest"])
    return {
        "ready": True,
        "redacted_projection": True,
        "package_kind_count": payload_manifest["package_kind_count"],
        "package_kinds": list(payload_manifest["package_kinds"]),
        "payload_hashes": [item["payload_hash"] for item in payload_manifest["payloads"]],
        "payload_refs_redacted": True,
        "package_payload_manifest_hash": receipt["package_payload_manifest_hash"],
        "package_payload_order_hash": receipt["package_payload_order_hash"],
        "package_review_preview_receipt_hash": receipt["package_review_preview_receipt_hash"],
        "candidate_package_manifest_hash": receipt["candidate_package_manifest_hash"],
        "review_readiness_hash": receipt["review_readiness_hash"],
        "package_order_hash": receipt["package_order_hash"],
        "redaction_manifest_hash": receipt["redaction_manifest_hash"],
        "product_evidence_preserved": True,
        "package_payloads_written": True,
        "package_construction_committed": True,
        "package_review_submit_enabled": False,
        "handoff_export_enabled": False,
        "delivery_enabled": False,
        "raw_values_returned": False,
        "raw_html_returned": False,
        "raw_urls_returned": False,
        "dataset_storage_ref_returned": False,
        "final_financial_statement_semantics_claimed": False,
        "next_allowed_actions": ["select_sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit"],
    }


def _blocked_response(
    *,
    request_id: str,
    package_review_preview_receipt_hash: str,
    reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="blocked", schema_id=SCHEMA_ID),
        "mode": PACKAGE_CONSTRUCTION_MODE,
        "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "package_construction_state": BLOCKED_STATE,
        "package_construction_receipt_id": None,
        "package_construction_receipt_ref": None,
        "package_construction_receipt_hash": None,
        "package_review_preview_receipt_id": None,
        "package_review_preview_receipt_hash": package_review_preview_receipt_hash,
        "package_payload_manifest": None,
        "package_payload_manifest_hash": None,
        "package_payload_order_hash": None,
        "package_kinds": [],
        "payload_refs": [],
        "payload_hashes": [],
        "authority_hashes": {},
        "status_projection": {
            "ready": False,
            "blocked_reasons": reasons,
            "package_construction_committed": False,
            "package_payloads_written": False,
            "package_review_submit_enabled": False,
            "handoff_export_enabled": False,
            "delivery_enabled": False,
            "redacted_projection": True,
        },
        "cache": {"idempotent_replay": False, "network_request_made": False},
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": [],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_blocked_response_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL package construction blocked response would expose raw authority.",
            http_status=409,
        )
    return response


def _normalize_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key.lower() in _FORBIDDEN_INPUT_KEYS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL package construction rejects caller paths, URLs, HTML, values, bytes, package rows, review submit, handoff, delivery, connector dispatch, model, browser, source-expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(key for key in request if key not in _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_unknown_field",
            "SEC EDGAR HTML/iXBRL package construction fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    if request.get("schema_id") not in (None, REQUEST_SCHEMA_ID):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL package construction requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _write_payload_artifacts(receipt_id: str, payload_manifest: Mapping[str, Any]) -> None:
    for item in list(payload_manifest.get("payloads") or []):
        if not isinstance(item, Mapping):
            continue
        package_kind = str(item.get("package_kind") or "")
        if package_kind not in PACKAGE_KINDS:
            _blocked(
                "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_payload_kind_invalid",
                "SEC EDGAR HTML/iXBRL package construction only writes admitted package kinds.",
                http_status=409,
                blocked_fields=["package_kind"],
            )
        payload = dict(item.get("payload") or {})
        target = _payload_path(receipt_id, package_kind)
        if target.exists():
            _validate_payload_artifact(target, str(item.get("payload_hash") or ""))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, indent=2) + "\n")


def _validate_payload_artifacts(receipt: Mapping[str, Any]) -> None:
    receipt_id = str(receipt["package_construction_receipt_id"])
    for item in list(dict(receipt["package_payload_manifest"]).get("payloads") or []):
        if not isinstance(item, Mapping):
            continue
        _validate_payload_artifact(_payload_path(receipt_id, str(item.get("package_kind") or "")), str(item.get("payload_hash") or ""))


def _validate_payload_artifact(path: Path, expected_hash: str) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_payload_missing",
            "SEC EDGAR HTML/iXBRL package construction payload artifact is missing.",
            http_status=409,
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_payload_unreadable",
            "SEC EDGAR HTML/iXBRL package construction payload artifact could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if stable_hash(payload) != expected_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_payload_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package construction payload artifact hash does not match receipt authority.",
            http_status=409,
        )


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["package_construction_receipt_id"]))
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
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_receipt_id_invalid",
            "SEC EDGAR HTML/iXBRL package construction status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["package_construction_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_receipt_missing",
            "SEC EDGAR HTML/iXBRL package construction receipt was not found.",
            http_status=404,
            blocked_fields=["package_construction_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL package construction receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("package_construction_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_receipt_invalid",
            "SEC EDGAR HTML/iXBRL package construction receipt is invalid or mismatched.",
            http_status=409,
        )
    payload_manifest_hash = stable_hash(receipt.get("package_payload_manifest") or {})
    if payload_manifest_hash != str(receipt.get("package_payload_manifest_hash") or ""):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_payload_manifest_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package construction payload manifest hash does not match receipt authority.",
            http_status=409,
        )
    payload_order_hash = stable_hash(
        [
            {
                "package_kind": item["package_kind"],
                "package_order": item["package_order"],
                "payload_ref": item["payload_ref"],
                "payload_hash": item["payload_hash"],
            }
            for item in list(dict(receipt["package_payload_manifest"]).get("payloads") or [])
        ]
    )
    if payload_order_hash != str(receipt.get("package_payload_order_hash") or ""):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_payload_order_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package construction payload order hash does not match receipt authority.",
            http_status=409,
        )
    if not _is_hash(str(receipt.get("package_construction_receipt_hash") or "")):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_receipt_hash_invalid",
            "SEC EDGAR HTML/iXBRL package construction receipt hash is invalid.",
            http_status=409,
        )
    recomputed_receipt_hash = _construction_hash(
        preview=receipt,
        payload_manifest_hash=payload_manifest_hash,
        payload_order_hash=payload_order_hash,
    )
    if recomputed_receipt_hash != str(receipt.get("package_construction_receipt_hash") or ""):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_receipt_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package construction receipt hash does not match stored authority.",
            http_status=409,
        )
    _validate_payload_artifacts(receipt)
    return receipt


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not target.exists():
        return None
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_request_binding_unreadable",
            "SEC EDGAR HTML/iXBRL package construction request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_package_construction_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "package_construction_basis_hash": basis_hash,
        "package_construction_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id)
        if existing and existing.get("package_construction_basis_hash") == basis_hash:
            return
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_request_binding_conflict",
            "SEC EDGAR HTML/iXBRL package construction request binding conflicts with existing authority.",
            http_status=409,
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _negative_invariants() -> dict[str, bool]:
    return {
        "package_review_preview_receipt_required": True,
        "downstream_product_receipt_required": True,
        "statement_classification_receipt_required": True,
        "fact_authority_receipt_required": True,
        "fact_material_bridge_receipt_required": True,
        "package_payloads_written": True,
        "package_review_submit_enabled": False,
        "handoff_export_enabled": False,
        "delivery_enabled": False,
        "live_sec_network_fetch_performed_by_package_construction": False,
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


def _payload_path(receipt_id: str, package_kind: str) -> Path:
    return _root() / "payloads" / receipt_id / f"{package_kind}.json"


def _request_bindings_dir() -> Path:
    return _root() / "request-bindings"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_construction_storage_root_unavailable",
            "SEC EDGAR HTML/iXBRL package construction requires the existing Layer 3 storage root.",
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
            f"sec_edgar_html_inline_xbrl_statement_candidate_package_construction_{key}_missing",
            f"SEC EDGAR HTML/iXBRL package construction requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_package_construction_{key}_invalid",
            f"SEC EDGAR HTML/iXBRL package construction requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if str(fields.get(key) or "") != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_package_construction_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL package construction request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


def _is_hash(value: str) -> bool:
    return len(value) == 64 and _is_hex(value)


def _is_hex(value: str) -> bool:
    return bool(value) and all(char in "0123456789abcdefABCDEF" for char in value)


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        return contains_forbidden_ref(value)
    return False


def _find_forbidden_nested_fields(value: Any, *, prefix: str = "") -> list[str]:
    return find_forbidden_ref_paths(value, forbidden_keys=_FORBIDDEN_INPUT_KEYS, prefix=prefix)


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
