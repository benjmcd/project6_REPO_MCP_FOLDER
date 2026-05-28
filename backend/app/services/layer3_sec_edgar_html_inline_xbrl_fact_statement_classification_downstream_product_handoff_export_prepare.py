from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit,
)
from app.services.layer3_sec_edgar_ref_safety import contains_forbidden_ref, find_forbidden_ref_paths
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError

SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare.v1"
)
REQUEST_SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare_request.v1"
)
STATUS_SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_handoff_export_prepare_status.v1"
)
SCHEMA_VERSION = 1
HANDOFF_EXPORT_PREPARE_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export_prepare_v1"
PACKAGE_REVIEW_SUBMIT_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_submit_v1"
PACKAGE_CONSTRUCTION_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_commit_v1"
PACKAGE_REVIEW_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_v1"
PRODUCT_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_v1"
CLASSIFICATION_MODE = "sec_edgar_html_inline_xbrl_fact_to_statement_classification_v1"
OPERATOR_DECISION = "prepare_sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export"
SOURCE_FAMILY = "sec_edgar_html_inline_xbrl"
RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-statement-candidate-handoff-export-prepare"
RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-statement-candidate-handoff-export-prepare"
REDACTION_POLICY_ID = "sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export_prepare_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export_prepare_hash_v1"
HANDOFF_EXPORT_PREPARED_STATE = (
    "sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export_prepared"
)
_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "handoff_export_prepare_mode",
    "operator_decision",
    "package_review_submit_receipt_id",
    "package_review_submit_receipt_hash",
    "expected_package_review_submit_record_ref",
    "expected_package_construction_receipt_hash",
    "expected_package_payload_manifest_hash",
    "expected_package_payload_order_hash",
    "expected_package_review_preview_receipt_hash",
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
    "payload",
    "package_payload",
    "value",
    "value_text",
    "fact_value",
    "raw_fact_value",
    "raw_fact_values",
    "delivery",
    "webhook",
    "connector",
    "provider",
    "rag",
    "model",
    "browser_storage",
    "frontend_authority",
}
def prepare_sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export(
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    request = _normalize_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "handoff_export_prepare_mode", HANDOFF_EXPORT_PREPARE_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    review_submit_receipt_id = _required(request, "package_review_submit_receipt_id")
    review_submit_receipt_hash = _required_hash(request, "package_review_submit_receipt_hash")

    if request.get("operator_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            package_review_submit_receipt_hash=review_submit_receipt_hash,
            reasons=[_reason("missing_operator_confirmation")],
        )

    review_submit = (
        layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit
        .inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_submit_status(
            review_submit_receipt_id
        )
    )
    _validate_review_submit_authority(request, review_submit, review_submit_receipt_hash)
    receipt_hash = _prepare_hash(review_submit)

    binding = _read_request_binding(request_id)
    if binding and binding.get("handoff_export_prepare_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR HTML/iXBRL handoff/export prepare basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    submit_binding = _read_submit_binding(review_submit_receipt_hash)
    if submit_binding and submit_binding.get("handoff_export_prepare_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_already_recorded",
            "SEC EDGAR HTML/iXBRL package-review submit authority already has a handoff/export prepare receipt.",
            http_status=409,
            blocked_fields=["package_review_submit_receipt_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["handoff_export_prepare_receipt_id"]))
        _write_submit_binding(review_submit_receipt_hash, receipt_hash, str(existing["handoff_export_prepare_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    manifest = _handoff_export_manifest(review_submit)
    manifest_hash = stable_hash(manifest)
    order_hash = stable_hash(
        {
            "package_payload_order_hash": review_submit["package_payload_order_hash"],
            "package_kinds": list(review_submit.get("package_kinds") or []),
            "payload_hashes": list(review_submit.get("payload_hashes") or []),
            "manifest_roles": list(manifest["artifact_roles"]),
        }
    )
    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "handoff_export_prepare_mode": HANDOFF_EXPORT_PREPARE_MODE,
        "package_review_submit_mode": PACKAGE_REVIEW_SUBMIT_MODE,
        "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "handoff_export_state": HANDOFF_EXPORT_PREPARED_STATE,
        "handoff_export_prepare_receipt_id": receipt_id,
        "handoff_export_prepare_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "handoff_export_prepare_record_ref": f"sec-edgar-html-inline-xbrl-handoff-export-prepare:{receipt_hash[:24]}",
        "handoff_export_prepare_receipt_hash": receipt_hash,
        "handoff_export_manifest": manifest,
        "handoff_export_manifest_hash": manifest_hash,
        "handoff_export_order_hash": order_hash,
        "package_review_submit_receipt_id": review_submit["package_review_submit_receipt_id"],
        "package_review_submit_receipt_hash": review_submit_receipt_hash,
        "package_review_submit_record_ref": review_submit["package_review_submit_record_ref"],
        "review_decision": review_submit["review_decision"],
        "package_review_state": review_submit["package_review_state"],
        "decision_notes_present": bool(review_submit.get("decision_notes_present")),
        "decision_notes_hash": review_submit["decision_notes_hash"],
        "package_construction_receipt_id": review_submit["package_construction_receipt_id"],
        "package_construction_receipt_hash": review_submit["package_construction_receipt_hash"],
        "package_review_preview_receipt_id": review_submit["package_review_preview_receipt_id"],
        "package_review_preview_receipt_hash": review_submit["package_review_preview_receipt_hash"],
        "downstream_product_receipt_hash": review_submit["downstream_product_receipt_hash"],
        "statement_classification_receipt_hash": review_submit["statement_classification_receipt_hash"],
        "fact_authority_receipt_hash": review_submit["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_hash": review_submit["fact_material_bridge_receipt_hash"],
        "parser_receipt_hash": review_submit["parser_receipt_hash"],
        "source_family": SOURCE_FAMILY,
        "typed_content_contract_id": review_submit["typed_content_contract_id"],
        "candidate_package_manifest_hash": review_submit["candidate_package_manifest_hash"],
        "review_readiness_hash": review_submit["review_readiness_hash"],
        "package_order_hash": review_submit["package_order_hash"],
        "redaction_manifest_hash": review_submit["redaction_manifest_hash"],
        "product_manifest_hash": review_submit["product_manifest_hash"],
        "statement_candidate_product_hash": review_submit["statement_candidate_product_hash"],
        "product_order_hash": review_submit["product_order_hash"],
        "inspection_summary_hash": review_submit["inspection_summary_hash"],
        "downstream_readiness_hash": review_submit["downstream_readiness_hash"],
        "package_payload_manifest_hash": review_submit["package_payload_manifest_hash"],
        "package_payload_order_hash": review_submit["package_payload_order_hash"],
        "package_kinds": list(review_submit.get("package_kinds") or []),
        "payload_refs": list(review_submit.get("payload_refs") or []),
        "payload_hashes": list(review_submit.get("payload_hashes") or []),
        "authority_hashes": _authority_hashes(review_submit, manifest_hash, order_hash),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "negative_invariants": _negative_invariants(),
        "actor_hash": _sha256_text(str(request.get("actor") or "system")),
        "created_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt_id)
    _write_submit_binding(review_submit_receipt_hash, receipt_hash, receipt_id)
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export_prepare_status(
    receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-html-inline-xbrl-statement-candidate-handoff-export-prepare-status-{receipt['handoff_export_prepare_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def _validate_review_submit_authority(
    request: Mapping[str, Any],
    review_submit: Mapping[str, Any],
    review_submit_receipt_hash: str,
) -> None:
    if str(review_submit.get("package_review_submit_receipt_hash") or "") != review_submit_receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_submit_hash_mismatch",
            "SEC EDGAR HTML/iXBRL handoff/export prepare requires package-review submit receipt hash parity.",
            http_status=409,
            blocked_fields=["package_review_submit_receipt_hash"],
        )
    if review_submit.get("review_decision") != "approved":
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_submit_not_approved",
            "SEC EDGAR HTML/iXBRL handoff/export prepare requires an approved package-review submit receipt.",
            http_status=409,
            blocked_fields=["package_review_submit_receipt_id", "review_decision"],
        )
    checks = {
        "package_review_submit_record_ref": "expected_package_review_submit_record_ref",
        "package_construction_receipt_hash": "expected_package_construction_receipt_hash",
        "package_payload_manifest_hash": "expected_package_payload_manifest_hash",
        "package_payload_order_hash": "expected_package_payload_order_hash",
        "package_review_preview_receipt_hash": "expected_package_review_preview_receipt_hash",
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
    for submit_key, request_key in checks.items():
        expected = request.get(request_key)
        if expected is not None and str(review_submit.get(submit_key) or "") != str(expected):
            _blocked(
                f"sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_{submit_key}_mismatch",
                f"SEC EDGAR HTML/iXBRL handoff/export prepare requires {submit_key} parity.",
                http_status=409,
                blocked_fields=[request_key],
            )


def _prepare_hash(review_submit: Mapping[str, Any]) -> str:
    return stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "handoff_export_prepare_mode": HANDOFF_EXPORT_PREPARE_MODE,
            "package_review_submit_receipt_hash": review_submit["package_review_submit_receipt_hash"],
            "package_review_submit_record_ref": review_submit["package_review_submit_record_ref"],
            "review_decision": review_submit["review_decision"],
            "package_construction_receipt_hash": review_submit["package_construction_receipt_hash"],
            "package_payload_manifest_hash": review_submit["package_payload_manifest_hash"],
            "package_payload_order_hash": review_submit["package_payload_order_hash"],
            "redaction_manifest_hash": review_submit["redaction_manifest_hash"],
            "downstream_product_receipt_hash": review_submit["downstream_product_receipt_hash"],
            "statement_classification_receipt_hash": review_submit["statement_classification_receipt_hash"],
            "fact_authority_receipt_hash": review_submit["fact_authority_receipt_hash"],
            "fact_material_bridge_receipt_hash": review_submit["fact_material_bridge_receipt_hash"],
            "parser_receipt_hash": review_submit["parser_receipt_hash"],
            "product_manifest_hash": review_submit["product_manifest_hash"],
            "statement_candidate_product_hash": review_submit["statement_candidate_product_hash"],
            "product_order_hash": review_submit["product_order_hash"],
            "inspection_summary_hash": review_submit["inspection_summary_hash"],
            "downstream_readiness_hash": review_submit["downstream_readiness_hash"],
        }
    )


def _handoff_export_manifest(review_submit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_manifest.v1",
        "schema_version": SCHEMA_VERSION,
        "source_family": SOURCE_FAMILY,
        "artifact_roles": [
            "handoff_manifest",
            "export_summary",
            "review_receipt",
            "authority_provenance",
            "redaction_manifest",
            "payload_inventory",
            "downstream_readiness_marker",
        ],
        "package_review_submit_receipt_hash": review_submit["package_review_submit_receipt_hash"],
        "package_review_submit_record_ref": review_submit["package_review_submit_record_ref"],
        "package_construction_receipt_hash": review_submit["package_construction_receipt_hash"],
        "package_payload_manifest_hash": review_submit["package_payload_manifest_hash"],
        "package_payload_order_hash": review_submit["package_payload_order_hash"],
        "package_kinds": list(review_submit.get("package_kinds") or []),
        "payload_hashes": list(review_submit.get("payload_hashes") or []),
        "payload_count": len(list(review_submit.get("payload_hashes") or [])),
        "payload_refs_redacted": True,
        "redaction_manifest_hash": review_submit["redaction_manifest_hash"],
        "product_evidence_preserved": True,
        "delivery_prepared": False,
        "connector_dispatch_prepared": False,
        "provider_write_prepared": False,
        "raw_values_included": False,
        "raw_urls_included": False,
        "local_paths_included": False,
        "decision_notes_included": False,
    }


def _authority_hashes(review_submit: Mapping[str, Any], manifest_hash: str, order_hash: str) -> dict[str, str]:
    keys = (
        "package_review_submit_receipt_hash",
        "package_construction_receipt_hash",
        "package_payload_manifest_hash",
        "package_payload_order_hash",
        "package_review_preview_receipt_hash",
        "candidate_package_manifest_hash",
        "review_readiness_hash",
        "redaction_manifest_hash",
        "downstream_product_receipt_hash",
        "statement_classification_receipt_hash",
        "fact_authority_receipt_hash",
        "fact_material_bridge_receipt_hash",
        "parser_receipt_hash",
        "product_manifest_hash",
        "statement_candidate_product_hash",
        "product_order_hash",
        "inspection_summary_hash",
        "downstream_readiness_hash",
        "decision_notes_hash",
    )
    hashes = {key: str(review_submit[key]) for key in keys}
    hashes["handoff_export_manifest_hash"] = manifest_hash
    hashes["handoff_export_order_hash"] = order_hash
    return hashes


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    schema_id: str,
    idempotent_replay: bool,
) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="prepared", schema_id=schema_id),
        "mode": HANDOFF_EXPORT_PREPARE_MODE,
        "handoff_export_prepare_mode": HANDOFF_EXPORT_PREPARE_MODE,
        "package_review_submit_mode": PACKAGE_REVIEW_SUBMIT_MODE,
        "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "handoff_export_state": receipt["handoff_export_state"],
        "handoff_export_prepare_receipt_id": receipt["handoff_export_prepare_receipt_id"],
        "handoff_export_prepare_receipt_ref": receipt["handoff_export_prepare_receipt_ref"],
        "handoff_export_prepare_record_ref": receipt["handoff_export_prepare_record_ref"],
        "handoff_export_prepare_receipt_hash": receipt["handoff_export_prepare_receipt_hash"],
        "handoff_export_manifest": receipt["handoff_export_manifest"],
        "handoff_export_manifest_hash": receipt["handoff_export_manifest_hash"],
        "handoff_export_order_hash": receipt["handoff_export_order_hash"],
        "package_review_submit_receipt_id": receipt["package_review_submit_receipt_id"],
        "package_review_submit_receipt_hash": receipt["package_review_submit_receipt_hash"],
        "package_review_submit_record_ref": receipt["package_review_submit_record_ref"],
        "review_decision": receipt["review_decision"],
        "package_review_state": receipt["package_review_state"],
        "decision_notes_present": receipt["decision_notes_present"],
        "decision_notes_hash": receipt["decision_notes_hash"],
        "package_construction_receipt_id": receipt["package_construction_receipt_id"],
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
        "package_payload_manifest_hash": receipt["package_payload_manifest_hash"],
        "package_payload_order_hash": receipt["package_payload_order_hash"],
        "package_kinds": list(receipt["package_kinds"]),
        "payload_refs": list(receipt["payload_refs"]),
        "payload_hashes": list(receipt["payload_hashes"]),
        "authority_hashes": dict(receipt["authority_hashes"]),
        "status_projection": _status_projection(receipt),
        "cache": {"idempotent_replay": idempotent_replay, "network_request_made": False},
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["select SEC HTML/iXBRL statement candidate delivery slice"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL handoff/export prepare would expose raw path, URL, token, or value authority.",
            http_status=409,
        )
    return response


def _status_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ready": True,
        "redacted_projection": True,
        "handoff_export_prepared": True,
        "handoff_export_state": receipt["handoff_export_state"],
        "handoff_export_manifest_hash": receipt["handoff_export_manifest_hash"],
        "handoff_export_order_hash": receipt["handoff_export_order_hash"],
        "package_review_submit_receipt_hash": receipt["package_review_submit_receipt_hash"],
        "package_review_submit_record_ref": receipt["package_review_submit_record_ref"],
        "package_construction_receipt_hash": receipt["package_construction_receipt_hash"],
        "package_payload_manifest_hash": receipt["package_payload_manifest_hash"],
        "package_payload_order_hash": receipt["package_payload_order_hash"],
        "redaction_manifest_hash": receipt["redaction_manifest_hash"],
        "payload_hashes": list(receipt["payload_hashes"]),
        "payload_refs_redacted": True,
        "delivery_enabled": False,
        "internal_webhook_enabled": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "raw_values_returned": False,
        "raw_html_returned": False,
        "raw_urls_returned": False,
        "dataset_storage_ref_returned": False,
        "final_financial_statement_semantics_claimed": False,
        "next_allowed_actions": ["select_sec_edgar_html_inline_xbrl_statement_candidate_delivery"],
    }


def _blocked_response(
    *,
    request_id: str,
    package_review_submit_receipt_hash: str,
    reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        **_base_response(request_id=request_id, status="blocked", schema_id=SCHEMA_ID),
        "mode": HANDOFF_EXPORT_PREPARE_MODE,
        "handoff_export_prepare_mode": HANDOFF_EXPORT_PREPARE_MODE,
        "operator_decision": OPERATOR_DECISION,
        "handoff_export_state": "sec_edgar_html_inline_xbrl_statement_candidate_product_handoff_export_blocked",
        "handoff_export_prepare_receipt_id": None,
        "handoff_export_prepare_receipt_ref": None,
        "handoff_export_prepare_record_ref": None,
        "handoff_export_prepare_receipt_hash": None,
        "handoff_export_manifest": None,
        "handoff_export_manifest_hash": None,
        "handoff_export_order_hash": None,
        "package_review_submit_receipt_hash": package_review_submit_receipt_hash,
        "status_projection": {
            "ready": False,
            "redacted_projection": True,
            "blocked_reasons": reasons,
            "handoff_export_prepared": False,
            "delivery_enabled": False,
            "raw_values_returned": False,
            "raw_html_returned": False,
            "raw_urls_returned": False,
        },
        "cache": {"idempotent_replay": False, "network_request_made": False},
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["inspect SEC HTML/iXBRL handoff/export prepare prerequisites"],
    }


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["handoff_export_prepare_receipt_id"]))
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
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_receipt_id_invalid",
            "SEC EDGAR HTML/iXBRL handoff/export prepare status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["handoff_export_prepare_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_receipt_missing",
            "SEC EDGAR HTML/iXBRL handoff/export prepare receipt was not found.",
            http_status=404,
            blocked_fields=["handoff_export_prepare_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL handoff/export prepare receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("handoff_export_prepare_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_receipt_invalid",
            "SEC EDGAR HTML/iXBRL handoff/export prepare receipt is invalid or mismatched.",
            http_status=409,
        )
    if _prepare_hash(receipt) != str(receipt.get("handoff_export_prepare_receipt_hash") or ""):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_receipt_hash_mismatch",
            "SEC EDGAR HTML/iXBRL handoff/export prepare receipt hash does not match stored authority.",
            http_status=409,
        )
    return receipt


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not target.exists():
        return None
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_request_binding_unreadable",
            "SEC EDGAR HTML/iXBRL handoff/export prepare request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "handoff_export_prepare_basis_hash": basis_hash,
        "handoff_export_prepare_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id)
        if existing and existing.get("handoff_export_prepare_basis_hash") == basis_hash:
            return
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_request_binding_conflict",
            "SEC EDGAR HTML/iXBRL handoff/export prepare request binding conflicts with existing authority.",
            http_status=409,
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _read_submit_binding(review_submit_receipt_hash: str) -> dict[str, Any] | None:
    target = _submit_bindings_dir() / f"{review_submit_receipt_hash}.json"
    if not target.exists():
        return None
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_submit_binding_unreadable",
            "SEC EDGAR HTML/iXBRL handoff/export prepare submit binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_submit_binding(review_submit_receipt_hash: str, basis_hash: str, receipt_id: str) -> None:
    target = _submit_bindings_dir() / f"{review_submit_receipt_hash}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_submit_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "package_review_submit_receipt_hash": review_submit_receipt_hash,
        "handoff_export_prepare_basis_hash": basis_hash,
        "handoff_export_prepare_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_submit_binding(review_submit_receipt_hash)
        if existing and existing.get("handoff_export_prepare_basis_hash") == basis_hash:
            return
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_submit_binding_conflict",
            "SEC EDGAR HTML/iXBRL handoff/export prepare submit binding conflicts with existing authority.",
            http_status=409,
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _negative_invariants() -> dict[str, bool]:
    return {
        "package_review_submit_receipt_required": True,
        "approved_package_review_submit_required": True,
        "handoff_export_prepare_recorded": True,
        "package_payloads_mutated": False,
        "delivery_enabled": False,
        "internal_webhook_enabled": False,
        "provider_object_write_enabled": False,
        "connector_dispatch_enabled": False,
        "live_sec_network_fetch_performed_by_handoff_export_prepare": False,
        "html_inline_xbrl_reparse_enabled": False,
        "standalone_xml_xbrl_fact_authority_enabled": False,
        "sec_companyfacts_api_runtime_enabled": False,
        "taxonomy_network_resolution_enabled": False,
        "financial_statement_semantics_finalized": False,
        "source_expansion_admitted": False,
        "rag_vector_model_runtime_enabled": False,
        "full_mockup_activation_enabled": False,
        "frontend_durable_authority_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposed": False,
        "artifact_bytes_exposed": False,
        "raw_fact_values_exposed": False,
        "decision_notes_exposed": False,
    }


def _normalize_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = dict(fields)
    blocked = sorted(key for key in request if key.lower() in _FORBIDDEN_INPUT_KEYS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL handoff/export prepare rejects caller paths, URLs, HTML, values, bytes, payload mutation, delivery, connector dispatch, provider, model, browser, source-expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(key for key in request if key not in _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_unknown_field",
            "SEC EDGAR HTML/iXBRL handoff/export prepare fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    if request.get("schema_id") not in (None, REQUEST_SCHEMA_ID):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL handoff/export prepare requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _request_bindings_dir() -> Path:
    return _root() / "request-bindings"


def _submit_bindings_dir() -> Path:
    return _root() / "submit-bindings"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_storage_root_unavailable",
            "SEC EDGAR HTML/iXBRL handoff/export prepare requires the existing Layer 3 storage root.",
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


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_{key}_missing",
            f"SEC EDGAR HTML/iXBRL handoff/export prepare requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_{key}_invalid",
            f"SEC EDGAR HTML/iXBRL handoff/export prepare requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if fields.get(key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_handoff_export_prepare_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL handoff/export prepare request does not match the admitted runtime contract.",
            blocked_fields=[key],
        )


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


def _reason(reason: str) -> dict[str, Any]:
    return {"reason": reason, "redacted": True}


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


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_hash(value: str) -> bool:
    return len(value) == 64 and _is_hex(value)


def _is_hex(value: str) -> bool:
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
