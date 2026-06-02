from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction,
)
from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_contract import (
    STATEMENT_CLASSIFICATION_MODE,
)
from app.services.layer3_sec_edgar_ref_safety import contains_forbidden_ref, find_forbidden_ref_paths
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError

SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit.v1"
)
REQUEST_SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit_request.v1"
)
STATUS_SCHEMA_ID = (
    "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_review_submit_status.v1"
)
SCHEMA_VERSION = 1
PACKAGE_REVIEW_SUBMIT_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_submit_v1"
PACKAGE_CONSTRUCTION_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_commit_v1"
PACKAGE_REVIEW_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_preview_v1"
PRODUCT_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_v1"
CLASSIFICATION_MODE = STATEMENT_CLASSIFICATION_MODE
OPERATOR_DECISION = "submit_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review"
SOURCE_FAMILY = "sec_edgar_html_inline_xbrl"
RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-statement-candidate-package-review-submit"
RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-statement-candidate-package-review-submit"
REDACTION_POLICY_ID = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_submit_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_submit_hash_v1"
APPROVED_STATE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_approved"
CHANGES_REQUESTED_STATE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_changes_requested"
REJECTED_STATE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_rejected"
BLOCKED_STATE = "sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_blocked"
REVIEW_STATE_BY_DECISION = {
    "approved": APPROVED_STATE,
    "changes_requested": CHANGES_REQUESTED_STATE,
    "rejected": REJECTED_STATE,
    "blocked": BLOCKED_STATE,
}
NOTE_REQUIRED_DECISIONS = {"changes_requested", "rejected", "blocked"}
_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "package_review_submit_mode",
    "operator_decision",
    "review_decision",
    "decision_notes",
    "package_construction_receipt_id",
    "package_construction_receipt_hash",
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
def submit_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review(
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    request = _normalize_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "package_review_submit_mode", PACKAGE_REVIEW_SUBMIT_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    construction_receipt_id = _required(request, "package_construction_receipt_id")
    construction_receipt_hash = _required_hash(request, "package_construction_receipt_hash")
    review_decision = _review_decision(request)
    decision_notes_hash = _decision_notes_hash(request.get("decision_notes"))

    if request.get("operator_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            package_construction_receipt_hash=construction_receipt_hash,
            reasons=[_reason("missing_operator_confirmation")],
        )
    if review_decision in NOTE_REQUIRED_DECISIONS and not str(request.get("decision_notes") or "").strip():
        return _blocked_response(
            request_id=request_id,
            package_construction_receipt_hash=construction_receipt_hash,
            reasons=[_reason("decision_notes_required")],
        )

    construction = (
        layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_package_construction
        .inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_status(
            construction_receipt_id
        )
    )
    _validate_construction_authority(request, construction, construction_receipt_hash)
    receipt_hash = _submit_hash(
        construction=construction,
        review_decision=review_decision,
        decision_notes_hash=decision_notes_hash,
    )

    binding = _read_request_binding(request_id)
    if binding and binding.get("package_review_submit_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR HTML/iXBRL package-review submit basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    construction_binding = _read_construction_binding(construction_receipt_hash)
    if construction_binding and construction_binding.get("package_review_submit_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_already_recorded",
            "SEC EDGAR HTML/iXBRL package construction authority already has a package-review submit receipt.",
            http_status=409,
            blocked_fields=["package_construction_receipt_id", "review_decision"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["package_review_submit_receipt_id"]))
        _write_construction_binding(construction_receipt_hash, receipt_hash, str(existing["package_review_submit_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "package_review_submit_mode": PACKAGE_REVIEW_SUBMIT_MODE,
        "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "review_decision": review_decision,
        "decision_notes_present": bool(str(request.get("decision_notes") or "").strip()),
        "decision_notes_hash": decision_notes_hash,
        "package_review_state": REVIEW_STATE_BY_DECISION[review_decision],
        "package_review_submit_receipt_id": receipt_id,
        "package_review_submit_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "package_review_submit_record_ref": f"sec-edgar-html-inline-xbrl-package-review-submit:{receipt_hash[:24]}",
        "package_review_submit_receipt_hash": receipt_hash,
        "package_construction_receipt_id": construction["package_construction_receipt_id"],
        "package_construction_receipt_hash": construction_receipt_hash,
        "package_review_preview_receipt_id": construction["package_review_preview_receipt_id"],
        "package_review_preview_receipt_hash": construction["package_review_preview_receipt_hash"],
        "downstream_product_receipt_hash": construction["downstream_product_receipt_hash"],
        "statement_classification_receipt_hash": construction["statement_classification_receipt_hash"],
        "fact_authority_receipt_hash": construction["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_hash": construction["fact_material_bridge_receipt_hash"],
        "parser_receipt_hash": construction["parser_receipt_hash"],
        "source_family": SOURCE_FAMILY,
        "typed_content_contract_id": construction["typed_content_contract_id"],
        "candidate_package_manifest_hash": construction["candidate_package_manifest_hash"],
        "review_readiness_hash": construction["review_readiness_hash"],
        "package_order_hash": construction["package_order_hash"],
        "redaction_manifest_hash": construction["redaction_manifest_hash"],
        "product_manifest_hash": construction["product_manifest_hash"],
        "statement_candidate_product_hash": construction["statement_candidate_product_hash"],
        "product_order_hash": construction["product_order_hash"],
        "inspection_summary_hash": construction["inspection_summary_hash"],
        "downstream_readiness_hash": construction["downstream_readiness_hash"],
        "package_payload_manifest": construction["package_payload_manifest"],
        "package_payload_manifest_hash": construction["package_payload_manifest_hash"],
        "package_payload_order_hash": construction["package_payload_order_hash"],
        "package_kinds": list(construction.get("package_kinds") or []),
        "payload_refs": list(construction.get("payload_refs") or []),
        "payload_hashes": list(construction.get("payload_hashes") or []),
        "authority_hashes": _authority_hashes(construction, decision_notes_hash),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "negative_invariants": _negative_invariants(),
        "actor_hash": _sha256_text(str(request.get("actor") or "system")),
        "created_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt_id)
    _write_construction_binding(construction_receipt_hash, receipt_hash, receipt_id)
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_package_review_submit_status(
    receipt_id: str,
) -> dict[str, Any]:
    receipt = _read_verified_receipt(receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-html-inline-xbrl-statement-candidate-package-review-submit-status-{receipt['package_review_submit_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def _validate_construction_authority(
    request: Mapping[str, Any],
    construction: Mapping[str, Any],
    construction_receipt_hash: str,
) -> None:
    if str(construction.get("package_construction_receipt_hash") or "") != construction_receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_construction_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package-review submit requires package-construction receipt hash parity.",
            http_status=409,
            blocked_fields=["package_construction_receipt_hash"],
        )
    if construction.get("package_construction_state") != (
        "sec_edgar_html_inline_xbrl_statement_candidate_product_package_construction_ready"
    ):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_construction_not_ready",
            "SEC EDGAR HTML/iXBRL package-review submit requires ready package-construction authority.",
            http_status=409,
            blocked_fields=["package_construction_receipt_id"],
        )
    checks = {
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
    for construction_key, request_key in checks.items():
        expected = request.get(request_key)
        if expected is not None and str(construction.get(construction_key) or "") != str(expected):
            _blocked(
                f"sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_{construction_key}_mismatch",
                f"SEC EDGAR HTML/iXBRL package-review submit requires {construction_key} parity.",
                http_status=409,
                blocked_fields=[request_key],
            )


def _submit_hash(*, construction: Mapping[str, Any], review_decision: str, decision_notes_hash: str) -> str:
    return stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "package_review_submit_mode": PACKAGE_REVIEW_SUBMIT_MODE,
            "review_decision": review_decision,
            "decision_notes_hash": decision_notes_hash,
            "package_construction_receipt_hash": construction["package_construction_receipt_hash"],
            "package_payload_manifest_hash": construction["package_payload_manifest_hash"],
            "package_payload_order_hash": construction["package_payload_order_hash"],
            "package_review_preview_receipt_hash": construction["package_review_preview_receipt_hash"],
            "candidate_package_manifest_hash": construction["candidate_package_manifest_hash"],
            "review_readiness_hash": construction["review_readiness_hash"],
            "redaction_manifest_hash": construction["redaction_manifest_hash"],
            "downstream_product_receipt_hash": construction["downstream_product_receipt_hash"],
            "statement_classification_receipt_hash": construction["statement_classification_receipt_hash"],
            "fact_authority_receipt_hash": construction["fact_authority_receipt_hash"],
            "fact_material_bridge_receipt_hash": construction["fact_material_bridge_receipt_hash"],
            "parser_receipt_hash": construction["parser_receipt_hash"],
            "product_manifest_hash": construction["product_manifest_hash"],
            "statement_candidate_product_hash": construction["statement_candidate_product_hash"],
            "product_order_hash": construction["product_order_hash"],
            "inspection_summary_hash": construction["inspection_summary_hash"],
            "downstream_readiness_hash": construction["downstream_readiness_hash"],
        }
    )


def _authority_hashes(construction: Mapping[str, Any], decision_notes_hash: str) -> dict[str, str]:
    return {
        "package_construction_receipt_hash": str(construction["package_construction_receipt_hash"]),
        "package_payload_manifest_hash": str(construction["package_payload_manifest_hash"]),
        "package_payload_order_hash": str(construction["package_payload_order_hash"]),
        "package_review_preview_receipt_hash": str(construction["package_review_preview_receipt_hash"]),
        "candidate_package_manifest_hash": str(construction["candidate_package_manifest_hash"]),
        "review_readiness_hash": str(construction["review_readiness_hash"]),
        "redaction_manifest_hash": str(construction["redaction_manifest_hash"]),
        "downstream_product_receipt_hash": str(construction["downstream_product_receipt_hash"]),
        "statement_classification_receipt_hash": str(construction["statement_classification_receipt_hash"]),
        "fact_authority_receipt_hash": str(construction["fact_authority_receipt_hash"]),
        "fact_material_bridge_receipt_hash": str(construction["fact_material_bridge_receipt_hash"]),
        "parser_receipt_hash": str(construction["parser_receipt_hash"]),
        "product_manifest_hash": str(construction["product_manifest_hash"]),
        "statement_candidate_product_hash": str(construction["statement_candidate_product_hash"]),
        "product_order_hash": str(construction["product_order_hash"]),
        "inspection_summary_hash": str(construction["inspection_summary_hash"]),
        "downstream_readiness_hash": str(construction["downstream_readiness_hash"]),
        "decision_notes_hash": decision_notes_hash,
    }


def _response_from_receipt(
    receipt: Mapping[str, Any],
    *,
    request_id: str,
    schema_id: str,
    idempotent_replay: bool,
) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="submitted", schema_id=schema_id),
        "mode": PACKAGE_REVIEW_SUBMIT_MODE,
        "package_review_submit_mode": PACKAGE_REVIEW_SUBMIT_MODE,
        "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "review_decision": receipt["review_decision"],
        "decision_notes_present": receipt["decision_notes_present"],
        "decision_notes_hash": receipt["decision_notes_hash"],
        "package_review_state": receipt["package_review_state"],
        "package_review_submit_receipt_id": receipt["package_review_submit_receipt_id"],
        "package_review_submit_receipt_ref": receipt["package_review_submit_receipt_ref"],
        "package_review_submit_record_ref": receipt["package_review_submit_record_ref"],
        "package_review_submit_receipt_hash": receipt["package_review_submit_receipt_hash"],
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
        "package_payload_manifest": receipt["package_payload_manifest"],
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
        "next_allowed_actions": (
            ["select SEC HTML/iXBRL statement candidate handoff/export slice"]
            if receipt["review_decision"] == "approved"
            else ["inspect SEC HTML/iXBRL package-review decision"]
        ),
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL package-review submit would expose raw path, URL, token, or value authority.",
            http_status=409,
        )
    return response


def _status_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ready": True,
        "redacted_projection": True,
        "review_decision": receipt["review_decision"],
        "package_review_state": receipt["package_review_state"],
        "decision_notes_present": receipt["decision_notes_present"],
        "decision_notes_hash": receipt["decision_notes_hash"],
        "package_construction_receipt_hash": receipt["package_construction_receipt_hash"],
        "package_payload_manifest_hash": receipt["package_payload_manifest_hash"],
        "package_payload_order_hash": receipt["package_payload_order_hash"],
        "package_review_preview_receipt_hash": receipt["package_review_preview_receipt_hash"],
        "candidate_package_manifest_hash": receipt["candidate_package_manifest_hash"],
        "review_readiness_hash": receipt["review_readiness_hash"],
        "redaction_manifest_hash": receipt["redaction_manifest_hash"],
        "payload_hashes": list(receipt["payload_hashes"]),
        "payload_refs_redacted": True,
        "package_review_submit_recorded": True,
        "package_review_submit_enabled": False,
        "handoff_export_enabled": False,
        "delivery_enabled": False,
        "raw_values_returned": False,
        "raw_html_returned": False,
        "raw_urls_returned": False,
        "dataset_storage_ref_returned": False,
        "final_financial_statement_semantics_claimed": False,
        "next_allowed_actions": (
            ["select_sec_edgar_html_inline_xbrl_statement_candidate_handoff_export"]
            if receipt["review_decision"] == "approved"
            else ["inspect_sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit"]
        ),
    }


def _blocked_response(
    *,
    request_id: str,
    package_construction_receipt_hash: str,
    reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        **_base_response(request_id=request_id, status="blocked", schema_id=SCHEMA_ID),
        "mode": PACKAGE_REVIEW_SUBMIT_MODE,
        "package_review_submit_mode": PACKAGE_REVIEW_SUBMIT_MODE,
        "package_construction_mode": PACKAGE_CONSTRUCTION_MODE,
        "package_review_mode": PACKAGE_REVIEW_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "review_decision": None,
        "decision_notes_present": False,
        "decision_notes_hash": None,
        "package_review_state": BLOCKED_STATE,
        "package_review_submit_receipt_id": None,
        "package_review_submit_receipt_ref": None,
        "package_review_submit_record_ref": None,
        "package_review_submit_receipt_hash": None,
        "package_construction_receipt_id": None,
        "package_construction_receipt_hash": package_construction_receipt_hash,
        "package_payload_manifest": None,
        "package_payload_manifest_hash": None,
        "package_payload_order_hash": None,
        "package_kinds": [],
        "payload_refs": [],
        "payload_hashes": [],
        "authority_hashes": {},
        "status_projection": {
            "ready": False,
            "redacted_projection": True,
            "blocked_reasons": reasons,
            "package_review_submit_recorded": False,
            "handoff_export_enabled": False,
            "delivery_enabled": False,
            "raw_values_returned": False,
            "raw_html_returned": False,
            "raw_urls_returned": False,
        },
        "cache": {"idempotent_replay": False, "network_request_made": False},
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["inspect SEC HTML/iXBRL package-review submit prerequisites"],
    }


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["package_review_submit_receipt_id"]))
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
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_receipt_id_invalid",
            "SEC EDGAR HTML/iXBRL package-review submit status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["package_review_submit_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_receipt_missing",
            "SEC EDGAR HTML/iXBRL package-review submit receipt was not found.",
            http_status=404,
            blocked_fields=["package_review_submit_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL package-review submit receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("package_review_submit_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_receipt_invalid",
            "SEC EDGAR HTML/iXBRL package-review submit receipt is invalid or mismatched.",
            http_status=409,
        )
    recomputed_hash = _submit_hash(
        construction=receipt,
        review_decision=str(receipt.get("review_decision") or ""),
        decision_notes_hash=str(receipt.get("decision_notes_hash") or ""),
    )
    if recomputed_hash != str(receipt.get("package_review_submit_receipt_hash") or ""):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_receipt_hash_mismatch",
            "SEC EDGAR HTML/iXBRL package-review submit receipt hash does not match stored authority.",
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
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_request_binding_unreadable",
            "SEC EDGAR HTML/iXBRL package-review submit request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "package_review_submit_basis_hash": basis_hash,
        "package_review_submit_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id)
        if existing and existing.get("package_review_submit_basis_hash") == basis_hash:
            return
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_request_binding_conflict",
            "SEC EDGAR HTML/iXBRL package-review submit request binding conflicts with existing authority.",
            http_status=409,
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _read_construction_binding(construction_receipt_hash: str) -> dict[str, Any] | None:
    target = _construction_bindings_dir() / f"{construction_receipt_hash}.json"
    if not target.exists():
        return None
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_construction_binding_unreadable",
            "SEC EDGAR HTML/iXBRL package-review submit construction binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_construction_binding(construction_receipt_hash: str, basis_hash: str, receipt_id: str) -> None:
    target = _construction_bindings_dir() / f"{construction_receipt_hash}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_construction_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "package_construction_receipt_hash": construction_receipt_hash,
        "package_review_submit_basis_hash": basis_hash,
        "package_review_submit_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_construction_binding(construction_receipt_hash)
        if existing and existing.get("package_review_submit_basis_hash") == basis_hash:
            return
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_construction_binding_conflict",
            "SEC EDGAR HTML/iXBRL package-review submit construction binding conflicts with existing authority.",
            http_status=409,
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _negative_invariants() -> dict[str, bool]:
    return {
        "package_construction_receipt_required": True,
        "package_payload_manifest_required": True,
        "package_review_submit_recorded": True,
        "package_payloads_mutated": False,
        "handoff_export_enabled": False,
        "delivery_enabled": False,
        "live_sec_network_fetch_performed_by_package_review_submit": False,
        "html_inline_xbrl_reparse_enabled": False,
        "standalone_xml_xbrl_fact_authority_enabled": False,
        "sec_companyfacts_api_runtime_enabled": False,
        "taxonomy_network_resolution_enabled": False,
        "financial_statement_semantics_finalized": False,
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
        "decision_notes_exposed": False,
    }


def _normalize_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = dict(fields)
    blocked = sorted(key for key in request if key.lower() in _FORBIDDEN_INPUT_KEYS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL package-review submit rejects caller paths, URLs, HTML, values, bytes, payload mutation, handoff, delivery, connector dispatch, model, browser, source-expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(key for key in request if key not in _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_unknown_field",
            "SEC EDGAR HTML/iXBRL package-review submit fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    if request.get("schema_id") not in (None, REQUEST_SCHEMA_ID):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL package-review submit requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _review_decision(request: Mapping[str, Any]) -> str:
    decision = str(request.get("review_decision") or "").strip()
    if decision not in REVIEW_STATE_BY_DECISION:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_decision_not_admitted",
            "SEC EDGAR HTML/iXBRL package-review submit requires an admitted review decision.",
            blocked_fields=["review_decision"],
        )
    return decision


def _decision_notes_hash(value: Any) -> str:
    notes = str(value or "").strip()
    return stable_hash({"decision_notes_present": bool(notes), "decision_notes": notes})


def _receipt_path(receipt_id: str) -> Path:
    return _root() / "receipts" / f"{receipt_id}.json"


def _request_bindings_dir() -> Path:
    return _root() / "request-bindings"


def _construction_bindings_dir() -> Path:
    return _root() / "construction-bindings"


def _root() -> Path:
    storage_dir = str(settings.storage_dir or "").strip()
    if not storage_dir:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_storage_root_unavailable",
            "SEC EDGAR HTML/iXBRL package-review submit requires the existing Layer 3 storage root.",
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
            f"sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_{key}_missing",
            f"SEC EDGAR HTML/iXBRL package-review submit requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_{key}_invalid",
            f"SEC EDGAR HTML/iXBRL package-review submit requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if fields.get(key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_package_review_submit_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL package-review submit request does not match the admitted runtime contract.",
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
