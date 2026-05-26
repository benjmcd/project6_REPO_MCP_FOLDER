from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_authority,
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge,
)
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_status.v1"
SCHEMA_VERSION = 1
CLASSIFICATION_MODE = "sec_edgar_html_inline_xbrl_fact_to_statement_classification_v1"
OPERATOR_DECISION = "classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates"
READY_STATE = "sec_edgar_html_inline_xbrl_fact_statement_classification_ready"
BLOCKED_STATE = "sec_edgar_html_inline_xbrl_fact_statement_classification_blocked"
SOURCE_FAMILY = "sec_edgar_html_inline_xbrl"
PARSER_FAMILY = "sec_edgar_html_inline_xbrl_source_family_parser_v1"
FACT_MATERIAL_CONTRACT_ID = "sec_edgar_html_inline_xbrl_fact_material_units_v1"
RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-fact-statement-classification"
RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-fact-statement-classification"
REDACTION_POLICY_ID = "sec_edgar_html_inline_xbrl_fact_statement_classification_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_html_inline_xbrl_fact_statement_classification_hash_v1"

STATEMENT_ROLES = (
    "balance_sheet",
    "income_statement",
    "cash_flow_statement",
    "stockholders_equity_statement",
    "comprehensive_income_statement",
    "cover_page",
    "disclosure_or_note",
    "unknown_or_unclassified",
)
_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "classification_mode",
    "operator_decision",
    "fact_authority_receipt_id",
    "fact_authority_receipt_hash",
    "fact_material_bridge_receipt_id",
    "fact_material_bridge_receipt_hash",
    "expected_parser_receipt_hash",
    "expected_connector_receipt_hash",
    "expected_live_source_artifact_receipt_hash",
    "expected_source_artifact_receipt_hash",
    "expected_content_sha256",
    "expected_primary_document_hash",
    "expected_document_inventory_hash",
    "expected_content_order_hash",
    "expected_table_candidate_inventory_hash",
    "expected_inline_xbrl_marker_inventory_hash",
    "expected_fact_inventory_hash",
    "expected_diagnostics_hash",
    "expected_materialization_receipt_hash",
    "expected_dataset_version_hash",
    "expected_gate_b_decision_manifest_id",
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


def classify_sec_edgar_html_inline_xbrl_facts_to_statement_candidates(
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "classification_mode", CLASSIFICATION_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    fact_receipt_id = _required(request, "fact_authority_receipt_id")
    fact_receipt_hash = _required_hash(request, "fact_authority_receipt_hash")
    bridge_receipt_id = _required(request, "fact_material_bridge_receipt_id")
    bridge_receipt_hash = _required_hash(request, "fact_material_bridge_receipt_hash")
    if request.get("operator_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            fact_authority_receipt_hash=fact_receipt_hash,
            fact_material_bridge_receipt_hash=bridge_receipt_hash,
            reasons=[_reason("missing_operator_confirmation")],
        )

    fact_receipt = layer3_sec_edgar_html_inline_xbrl_fact_authority.read_sec_edgar_html_inline_xbrl_fact_authority_receipt(
        fact_receipt_id,
        expected_fact_authority_receipt_hash=fact_receipt_hash,
    )
    bridge_status = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.inspect_sec_edgar_html_inline_xbrl_fact_material_bridge_status(
        bridge_receipt_id
    )
    _validate_bridge_authority(request, fact_receipt, bridge_status, bridge_receipt_hash=bridge_receipt_hash)
    facts = list(fact_receipt.get("fact_inventory") or [])
    if not facts:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_fact_inventory_missing",
            "SEC EDGAR HTML/iXBRL fact statement classification requires existing fact authority inventory.",
            http_status=409,
            blocked_fields=["fact_inventory_hash"],
        )
    if stable_hash(facts) != str(fact_receipt.get("fact_inventory_hash") or ""):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_fact_inventory_hash_mismatch",
            "SEC EDGAR HTML/iXBRL fact statement classification requires fact inventory hash parity.",
            http_status=409,
            blocked_fields=["fact_inventory_hash"],
        )

    classification_inventory = [
        _classification_record(fact, fact_order=index, fact_inventory_hash=str(fact_receipt["fact_inventory_hash"]))
        for index, fact in enumerate(facts, start=1)
    ]
    _validate_classification_inventory(facts, classification_inventory)
    statement_groups = _statement_groups(classification_inventory)
    classification_inventory_hash = stable_hash(classification_inventory)
    classification_order_hash = stable_hash(
        [
            {
                "fact_order": item["fact_order"],
                "fact_id_or_order_key": item["fact_id_or_order_key"],
                "statement_candidate_role": item["statement_candidate_role"],
                "source_order_hash": item.get("source_order_hash"),
            }
            for item in classification_inventory
        ]
    )
    statement_group_inventory_hash = stable_hash(statement_groups)
    unclassified = [item for item in classification_inventory if item["statement_candidate_role"] == "unknown_or_unclassified"]
    unclassified_fact_inventory_hash = stable_hash(unclassified)
    diagnostics = {
        "fact_count": len(facts),
        "classified_fact_count": len(classification_inventory),
        "unknown_or_unclassified_count": len(unclassified),
        "every_fact_classified_exactly_once": True,
        "source_order_preserved": True,
        "marker_order_preserved": True,
        "raw_values_returned": False,
        "raw_html_returned": False,
        "raw_url_returned": False,
        "taxonomy_network_resolution_performed": False,
        "sec_companyfacts_api_called": False,
        "financial_statement_semantics_claimed": False,
    }
    diagnostics_hash = stable_hash(diagnostics)
    receipt_hash = stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "classification_mode": CLASSIFICATION_MODE,
            "fact_authority_receipt_hash": fact_receipt_hash,
            "fact_material_bridge_receipt_hash": bridge_receipt_hash,
            "fact_inventory_hash": fact_receipt["fact_inventory_hash"],
            "classification_inventory_hash": classification_inventory_hash,
            "classification_order_hash": classification_order_hash,
            "statement_group_inventory_hash": statement_group_inventory_hash,
            "unclassified_fact_inventory_hash": unclassified_fact_inventory_hash,
            "classification_diagnostics_hash": diagnostics_hash,
        }
    )
    binding = _read_request_binding(request_id)
    if binding and binding.get("statement_classification_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR HTML/iXBRL statement classification basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["statement_classification_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "classification_state": READY_STATE,
        "statement_classification_receipt_id": receipt_id,
        "statement_classification_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "statement_classification_receipt_hash": receipt_hash,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": FACT_MATERIAL_CONTRACT_ID,
        "fact_authority_receipt_id": fact_receipt_id,
        "fact_authority_receipt_hash": fact_receipt_hash,
        "fact_material_bridge_receipt_id": bridge_receipt_id,
        "fact_material_bridge_receipt_hash": bridge_receipt_hash,
        "parser_receipt_id": fact_receipt["parser_receipt_id"],
        "parser_receipt_hash": fact_receipt["parser_receipt_hash"],
        "dataset_version_hash": bridge_status["dataset_version_hash"],
        "materialization_receipt_hash": bridge_status["materialization_receipt_hash"],
        "gate_b_decision_manifest_id": bridge_status["gate_b_decision_manifest_id"],
        "classification_inventory": classification_inventory,
        "classification_inventory_hash": classification_inventory_hash,
        "classification_order_hash": classification_order_hash,
        "statement_group_inventory": statement_groups,
        "statement_group_inventory_hash": statement_group_inventory_hash,
        "unclassified_fact_inventory_hash": unclassified_fact_inventory_hash,
        "classification_diagnostics": diagnostics,
        "classification_diagnostics_hash": diagnostics_hash,
        "authority_hashes": _authority_hashes(fact_receipt, bridge_status, bridge_receipt_hash),
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "request_id_hash": _sha256_text(request_id),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt_id)
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_html_inline_xbrl_fact_statement_classification_status(receipt_id: str) -> dict[str, Any]:
    receipt = _read_verified_receipt(receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-html-inline-xbrl-fact-statement-classification-status-{receipt['statement_classification_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def _validate_bridge_authority(
    request: Mapping[str, Any],
    fact_receipt: Mapping[str, Any],
    bridge_status: Mapping[str, Any],
    *,
    bridge_receipt_hash: str,
) -> None:
    if str(bridge_status.get("fact_material_bridge_receipt_hash") or "") != bridge_receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_bridge_hash_mismatch",
            "SEC EDGAR HTML/iXBRL fact material bridge receipt hash is stale or mismatched.",
            http_status=409,
            blocked_fields=["fact_material_bridge_receipt_hash"],
        )
    checks = {
        "parser_receipt_hash": "expected_parser_receipt_hash",
        "connector_receipt_hash": "expected_connector_receipt_hash",
        "live_source_artifact_receipt_hash": "expected_live_source_artifact_receipt_hash",
        "source_artifact_receipt_hash": "expected_source_artifact_receipt_hash",
        "content_sha256": "expected_content_sha256",
        "primary_document_hash": "expected_primary_document_hash",
        "document_inventory_hash": "expected_document_inventory_hash",
        "content_order_hash": "expected_content_order_hash",
        "table_candidate_inventory_hash": "expected_table_candidate_inventory_hash",
        "inline_xbrl_marker_inventory_hash": "expected_inline_xbrl_marker_inventory_hash",
        "fact_inventory_hash": "expected_fact_inventory_hash",
        "diagnostics_hash": "expected_diagnostics_hash",
    }
    bridge_hashes = bridge_status.get("authority_hashes")
    if not isinstance(bridge_hashes, Mapping):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_bridge_authority_hashes_missing",
            "SEC EDGAR HTML/iXBRL statement classification requires material bridge authority hashes.",
            http_status=409,
            blocked_fields=["authority_hashes"],
        )
    for authority_key, request_key in checks.items():
        expected = _expected_or_authority(request, request_key, fact_receipt, authority_key)
        bridge_value = str(bridge_hashes.get(authority_key) or "").strip()
        if authority_key == "parser_receipt_hash" and not bridge_value:
            bridge_value = str(bridge_status.get("parser_receipt_hash") or "").strip()
        if not _is_hash(bridge_value):
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_statement_classification_bridge_authority_hash_missing",
                "SEC EDGAR HTML/iXBRL statement classification requires complete material bridge authority hash parity.",
                http_status=409,
                blocked_fields=[f"authority_hashes.{authority_key}"],
            )
        if bridge_value != expected:
            _blocked(
                f"sec_edgar_html_inline_xbrl_fact_statement_classification_{authority_key}_mismatch",
                "SEC EDGAR HTML/iXBRL statement classification requires fact and bridge authority hash parity.",
                http_status=409,
                blocked_fields=[request_key],
            )
    for authority_key, request_key in (
        ("materialization_receipt_hash", "expected_materialization_receipt_hash"),
        ("dataset_version_hash", "expected_dataset_version_hash"),
    ):
        expected = str(request.get(request_key) or bridge_status.get(authority_key) or "").strip()
        if not _is_hash(expected) or str(bridge_status.get(authority_key) or "") != expected:
            _blocked(
                f"sec_edgar_html_inline_xbrl_fact_statement_classification_{authority_key}_mismatch",
                "SEC EDGAR HTML/iXBRL statement classification requires material bridge authority hash parity.",
                http_status=409,
                blocked_fields=[request_key],
            )
    expected_gate_b = str(request.get("expected_gate_b_decision_manifest_id") or bridge_status.get("gate_b_decision_manifest_id") or "").strip()
    if not expected_gate_b or str(bridge_status.get("gate_b_decision_manifest_id") or "") != expected_gate_b:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_gate_b_decision_manifest_mismatch",
            "SEC EDGAR HTML/iXBRL statement classification requires Gate B manifest parity.",
            http_status=409,
            blocked_fields=["expected_gate_b_decision_manifest_id"],
        )


def _classification_record(fact: Mapping[str, Any], *, fact_order: int, fact_inventory_hash: str) -> dict[str, Any]:
    role, basis, confidence = _classify_role(str(fact.get("local_name") or ""), str(fact.get("namespace_prefix") or ""))
    record = {
        "classification_id_or_order_key": stable_hash(
            {
                "fact_inventory_hash": fact_inventory_hash,
                "fact_order": fact_order,
                "fact_id_or_order_key": fact.get("fact_id_or_order_key"),
                "statement_candidate_role": role,
            }
        ),
        "fact_id_or_order_key": str(fact.get("fact_id_or_order_key") or ""),
        "fact_order": fact_order,
        "marker_order_index": int(fact.get("marker_order_index") or fact_order),
        "qualified_name": str(fact.get("qualified_name") or ""),
        "namespace_prefix": str(fact.get("namespace_prefix") or ""),
        "local_name": str(fact.get("local_name") or ""),
        "statement_candidate_role": role,
        "classification_confidence": confidence,
        "classification_basis": basis,
        "context_ref_hash": fact.get("context_ref_hash"),
        "unit_ref_hash": fact.get("unit_ref_hash"),
        "decimals_or_precision": str(fact.get("decimals_or_precision") or ""),
        "scale_or_format": str(fact.get("scale_or_format") or ""),
        "source_order_hash": fact.get("source_order_hash"),
        "source_artifact_receipt_hash": str(fact.get("source_artifact_receipt_hash") or ""),
        "primary_document_hash": str(fact.get("primary_document_hash") or ""),
        "value_hash": str(fact.get("value_hash") or ""),
        "value_length": int(fact.get("value_length") or 0),
        "value_redacted": True,
        "table_candidate_anchor_hash": fact.get("table_candidate_anchor_hash"),
        "final_financial_statement_semantics_claimed": False,
    }
    return record


def _classify_role(local_name: str, namespace_prefix: str) -> tuple[str, dict[str, Any], str]:
    local = re.sub(r"[^a-z0-9]+", "", local_name.lower())
    prefix = namespace_prefix.lower()
    rules = (
        ("cover_page", prefix == "dei" or any(token in local for token in ("documenttype", "entityregistrantname", "tradingsymbol", "securityexchange", "documentperiodenddate")), "cover_page_or_dei"),
        ("cash_flow_statement", any(token in local for token in ("netcash", "cashflow", "providedbyusedin", "operatingactivities", "investingactivities", "financingactivities")), "cash_flow_keyword"),
        ("comprehensive_income_statement", any(token in local for token in ("comprehensiveincome", "othercomprehensive")), "comprehensive_income_keyword"),
        ("stockholders_equity_statement", any(token in local for token in ("stockholder", "shareholder", "retainedearnings", "treasurystock", "additionalpaidincapital", "commonstock", "preferredstock", "accumulatedothercomprehensive")), "equity_keyword"),
        ("income_statement", any(token in local for token in ("revenue", "sales", "income", "loss", "expense", "earnings", "profit", "costof", "grossprofit", "operatingincome", "netincome")), "income_statement_keyword"),
        ("balance_sheet", any(token in local for token in ("asset", "liabilit", "cashandcashequivalents", "receivable", "inventory", "propertyplant", "payable", "debt", "goodwill", "intangible", "accrued", "deferredtax")), "balance_sheet_keyword"),
        ("disclosure_or_note", any(token in local for token in ("policy", "disclosure", "note", "segment", "lease", "tax", "fairvalue", "commitment", "contingenc", "derivative")), "disclosure_note_keyword"),
    )
    for role, matched, rule_id in rules:
        if matched:
            return role, {"rule_id": rule_id, "taxonomy_network_resolution_used": False}, "medium"
    return "unknown_or_unclassified", {"rule_id": "no_local_name_keyword_match", "taxonomy_network_resolution_used": False}, "low"


def _validate_classification_inventory(facts: list[Any], inventory: list[Mapping[str, Any]]) -> None:
    if len(facts) != len(inventory):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_count_mismatch",
            "SEC EDGAR HTML/iXBRL statement classification requires exactly one classification per fact.",
            http_status=409,
            blocked_fields=["classification_inventory"],
        )
    for item in inventory:
        if item.get("statement_candidate_role") not in STATEMENT_ROLES:
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_statement_classification_role_invalid",
                "SEC EDGAR HTML/iXBRL statement classification emitted a non-admitted role.",
                http_status=409,
                blocked_fields=["statement_candidate_role"],
            )


def _statement_groups(inventory: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for role in STATEMENT_ROLES:
        items = [item for item in inventory if item["statement_candidate_role"] == role]
        groups.append(
            {
                "statement_candidate_role": role,
                "fact_count": len(items),
                "fact_order_hash": stable_hash([item["fact_order"] for item in items]),
                "fact_id_inventory_hash": stable_hash([item["fact_id_or_order_key"] for item in items]),
                "source_order_preserved": True,
            }
        )
    return groups


def _authority_hashes(
    fact_receipt: Mapping[str, Any],
    bridge_status: Mapping[str, Any],
    bridge_receipt_hash: str,
) -> dict[str, str]:
    keys = (
        "parser_receipt_hash",
        "connector_receipt_hash",
        "live_source_artifact_receipt_hash",
        "source_artifact_receipt_hash",
        "content_sha256",
        "primary_document_hash",
        "document_inventory_hash",
        "content_order_hash",
        "table_candidate_inventory_hash",
        "inline_xbrl_marker_inventory_hash",
        "fact_inventory_hash",
        "diagnostics_hash",
    )
    return {
        **{key: str(fact_receipt[key]) for key in keys if key in fact_receipt},
        "fact_authority_receipt_hash": str(fact_receipt["fact_authority_receipt_hash"]),
        "fact_material_bridge_receipt_hash": bridge_receipt_hash,
        "dataset_version_hash": str(bridge_status["dataset_version_hash"]),
        "materialization_receipt_hash": str(bridge_status["materialization_receipt_hash"]),
        "gate_b_decision_manifest_id": str(bridge_status["gate_b_decision_manifest_id"]),
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
        "mode": CLASSIFICATION_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "classification_state": receipt["classification_state"],
        "statement_classification_receipt_id": receipt["statement_classification_receipt_id"],
        "statement_classification_receipt_ref": receipt["statement_classification_receipt_ref"],
        "statement_classification_receipt_hash": receipt["statement_classification_receipt_hash"],
        "idempotent_replay": idempotent_replay,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": FACT_MATERIAL_CONTRACT_ID,
        "fact_authority_receipt_id": receipt["fact_authority_receipt_id"],
        "fact_authority_receipt_hash": receipt["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_id": receipt["fact_material_bridge_receipt_id"],
        "fact_material_bridge_receipt_hash": receipt["fact_material_bridge_receipt_hash"],
        "parser_receipt_hash": receipt["parser_receipt_hash"],
        "dataset_version_hash": receipt["dataset_version_hash"],
        "materialization_receipt_hash": receipt["materialization_receipt_hash"],
        "gate_b_decision_manifest_id": receipt["gate_b_decision_manifest_id"],
        "classification_inventory": list(receipt["classification_inventory"]),
        "classification_inventory_hash": receipt["classification_inventory_hash"],
        "classification_order_hash": receipt["classification_order_hash"],
        "statement_group_inventory": list(receipt["statement_group_inventory"]),
        "statement_group_inventory_hash": receipt["statement_group_inventory_hash"],
        "unclassified_fact_inventory_hash": receipt["unclassified_fact_inventory_hash"],
        "classification_diagnostics": dict(receipt["classification_diagnostics"]),
        "classification_diagnostics_hash": receipt["classification_diagnostics_hash"],
        "authority_hashes": dict(receipt["authority_hashes"]),
        "status_projection": {
            "ready": True,
            "redacted_projection": True,
            "fact_count": receipt["classification_diagnostics"]["fact_count"],
            "statement_role_counts": {
                item["statement_candidate_role"]: item["fact_count"] for item in receipt["statement_group_inventory"]
            },
            "classification_inventory_hash": receipt["classification_inventory_hash"],
            "statement_group_inventory_hash": receipt["statement_group_inventory_hash"],
            "classification_diagnostics_hash": receipt["classification_diagnostics_hash"],
            "raw_values_returned": False,
            "final_financial_statement_semantics_claimed": False,
            "next_allowed_actions": ["select_sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product"],
        },
        "cache": {"idempotent_replay": idempotent_replay, "network_request_made": False},
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["select SEC HTML/iXBRL fact statement classification downstream product slice"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL fact statement classification would expose raw path, URL, token, or value authority.",
            http_status=409,
        )
    return response


def _blocked_response(
    *,
    request_id: str,
    fact_authority_receipt_hash: str,
    fact_material_bridge_receipt_hash: str,
    reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="blocked", schema_id=SCHEMA_ID),
        "mode": CLASSIFICATION_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "classification_state": BLOCKED_STATE,
        "statement_classification_receipt_id": None,
        "statement_classification_receipt_ref": None,
        "statement_classification_receipt_hash": None,
        "idempotent_replay": False,
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": FACT_MATERIAL_CONTRACT_ID,
        "fact_authority_receipt_hash": fact_authority_receipt_hash,
        "fact_material_bridge_receipt_hash": fact_material_bridge_receipt_hash,
        "classification_inventory": [],
        "classification_inventory_hash": None,
        "classification_order_hash": None,
        "statement_group_inventory": [],
        "statement_group_inventory_hash": None,
        "unclassified_fact_inventory_hash": None,
        "classification_diagnostics_hash": None,
        "status_projection": {
            "ready": False,
            "redacted_projection": True,
            "blocked_reasons": reasons,
            "next_allowed_actions": ["refresh_sec_edgar_html_inline_xbrl_fact_and_bridge_authority_receipts"],
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["refresh SEC HTML/iXBRL fact and bridge authority receipts"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_blocked_response_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL fact statement classification blocked response would expose raw authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key.lower() in _FORBIDDEN_INPUT_KEYS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL fact statement classification rejects caller paths, URLs, HTML, values, bytes, commands, credentials, connector dispatch, model, browser, source-expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(set(request) - _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_unknown_field",
            "SEC EDGAR HTML/iXBRL fact statement classification fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL fact statement classification requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _expected_or_authority(request: Mapping[str, Any], request_key: str, authority: Mapping[str, Any], authority_key: str) -> str:
    value = str(request.get(request_key) or authority.get(authority_key) or "").strip()
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_statement_classification_{request_key}_invalid",
            "SEC EDGAR HTML/iXBRL fact statement classification requires SHA-256 authority hashes.",
            blocked_fields=[request_key],
        )
    if str(authority.get(authority_key) or "") != value:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_statement_classification_{authority_key}_mismatch",
            "SEC EDGAR HTML/iXBRL fact statement classification authority hash is stale or mismatched.",
            http_status=409,
            blocked_fields=[request_key],
        )
    return value


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["statement_classification_receipt_id"]))
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
            "sec_edgar_html_inline_xbrl_fact_statement_classification_receipt_id_invalid",
            "SEC EDGAR HTML/iXBRL fact statement classification status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["statement_classification_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_receipt_missing",
            "SEC EDGAR HTML/iXBRL fact statement classification receipt was not found.",
            http_status=404,
            blocked_fields=["statement_classification_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL fact statement classification receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("statement_classification_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_receipt_invalid",
            "SEC EDGAR HTML/iXBRL fact statement classification receipt is invalid or mismatched.",
            http_status=409,
        )
    if not _is_hash(str(receipt.get("statement_classification_receipt_hash") or "")):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_receipt_hash_invalid",
            "SEC EDGAR HTML/iXBRL fact statement classification receipt hash is invalid.",
            http_status=409,
        )
    return receipt


def _read_request_binding(request_id: str) -> dict[str, Any] | None:
    path = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _blocked(
            "sec_edgar_html_inline_xbrl_fact_statement_classification_request_binding_unreadable",
            "SEC EDGAR HTML/iXBRL fact statement classification request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "statement_classification_basis_hash": basis_hash,
        "statement_classification_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("statement_classification_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_html_inline_xbrl_fact_statement_classification_request_binding_conflict",
                "SEC EDGAR HTML/iXBRL fact statement classification request binding conflicts with existing authority.",
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
        "fact_authority_receipt_required": True,
        "fact_material_bridge_receipt_required": True,
        "live_sec_network_fetch_performed_by_classification": False,
        "submissions_lookup_runtime_performed_by_classification": False,
        "browser_supplied_html_admitted": False,
        "browser_supplied_raw_url_admitted": False,
        "browser_supplied_local_path_admitted": False,
        "artifact_bytes_admitted": False,
        "raw_fact_values_admitted": False,
        "standalone_xml_xbrl_fact_authority_enabled": False,
        "sec_companyfacts_api_runtime_enabled": False,
        "taxonomy_network_resolution_enabled": False,
        "financial_statement_semantics_finalized": False,
        "fact_material_bridge_mutated": False,
        "gate_b_mutated": False,
        "downstream_proof_mutated": False,
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
            "sec_edgar_html_inline_xbrl_fact_statement_classification_storage_root_unavailable",
            "SEC EDGAR HTML/iXBRL fact statement classification requires the existing Layer 3 storage root.",
            http_status=409,
            blocked_fields=["storage_dir"],
        )
    return Path(storage_dir).resolve() / RECEIPT_DIR


def _base_response(*, request_id: str, status: str, schema_id: str) -> dict[str, Any]:
    return {"schema_id": schema_id, "schema_version": SCHEMA_VERSION, "request_id": request_id, "server_time": _server_time(), "status": status}


def _reason(reason: str, **details: Any) -> dict[str, Any]:
    return {"reason": reason, **details}


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_statement_classification_{key}_missing",
            f"SEC EDGAR HTML/iXBRL fact statement classification requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_statement_classification_{key}_invalid",
            f"SEC EDGAR HTML/iXBRL fact statement classification requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_fact_statement_classification_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL fact statement classification request does not match the admitted runtime contract.",
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
