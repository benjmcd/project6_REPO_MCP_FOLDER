from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services import (
    layer3_sec_edgar_html_inline_xbrl_fact_authority,
    layer3_sec_edgar_html_inline_xbrl_fact_material_bridge,
    layer3_sec_edgar_html_inline_xbrl_fact_statement_classification,
    layer3_sec_xbrl_sidecar,
)
from app.services.layer3_sec_edgar_html_inline_xbrl_fact_statement_classification_contract import (
    STATEMENT_CLASSIFICATION_MODE,
)
from app.services.layer3_sec_edgar_ref_safety import contains_forbidden_ref, find_forbidden_ref_paths
from app.services.layer3_utils import stable_hash
from app.services.layer3_workbench_error import Layer3WorkbenchError


SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product.v1"
REQUEST_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_request.v1"
STATUS_SCHEMA_ID = "layer3.sec_edgar_html_inline_xbrl_fact_statement_classification_downstream_product_status.v1"
SCHEMA_VERSION = 1
PRODUCT_MODE = "sec_edgar_html_inline_xbrl_statement_candidate_product_v1"
CLASSIFICATION_MODE = STATEMENT_CLASSIFICATION_MODE
OPERATOR_DECISION = "build_sec_edgar_html_inline_xbrl_statement_candidate_product_evidence"
READY_STATE = "sec_edgar_html_inline_xbrl_statement_candidate_product_ready"
BLOCKED_STATE = "sec_edgar_html_inline_xbrl_statement_candidate_product_blocked"
SOURCE_FAMILY = "sec_edgar_html_inline_xbrl"
PARSER_FAMILY = "sec_edgar_html_inline_xbrl_source_family_parser_v1"
FACT_MATERIAL_CONTRACT_ID = "sec_edgar_html_inline_xbrl_fact_material_units_v1"
RECEIPT_PREFIX = "sec-edgar-html-inline-xbrl-statement-candidate-product"
RECEIPT_DIR = "layer3-sec-edgar-html-inline-xbrl-statement-candidate-product"
REDACTION_POLICY_ID = "sec_edgar_html_inline_xbrl_statement_candidate_product_redaction_v1"
AUTHORITY_HASH_VERSION = "sec_edgar_html_inline_xbrl_statement_candidate_product_hash_v1"

_ALLOWED_FIELDS = {
    "schema_id",
    "schema_version",
    "client_request_id",
    "product_mode",
    "operator_decision",
    "statement_classification_receipt_id",
    "statement_classification_receipt_hash",
    "expected_fact_authority_receipt_hash",
    "expected_fact_material_bridge_receipt_hash",
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
    "expected_classification_inventory_hash",
    "expected_classification_order_hash",
    "expected_statement_group_inventory_hash",
    "expected_unclassified_fact_inventory_hash",
    "expected_classification_diagnostics_hash",
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
def build_sec_edgar_html_inline_xbrl_statement_candidate_product_evidence(
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    request = _normalise_request(fields)
    request_id = _required(request, "client_request_id")
    _require_exact(request, "product_mode", PRODUCT_MODE)
    _require_exact(request, "operator_decision", OPERATOR_DECISION)
    classification_receipt_id = _required(request, "statement_classification_receipt_id")
    classification_receipt_hash = _required_hash(request, "statement_classification_receipt_hash")
    if request.get("operator_confirmation") is not True:
        return _blocked_response(
            request_id=request_id,
            statement_classification_receipt_hash=classification_receipt_hash,
            reasons=[_reason("missing_operator_confirmation")],
        )

    classification = layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.inspect_sec_edgar_html_inline_xbrl_fact_statement_classification_status(
        classification_receipt_id
    )
    _validate_classification_authority(request, classification, classification_receipt_hash)
    bridge_status = layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.inspect_sec_edgar_html_inline_xbrl_fact_material_bridge_status(
        str(classification["fact_material_bridge_receipt_id"])
    )
    fact_receipt = _read_fact_authority_for_classification(classification, bridge_status)
    _validate_upstream_authority(request, classification, fact_receipt, bridge_status)

    classification_inventory = list(classification.get("classification_inventory") or [])
    statement_groups = list(classification.get("statement_group_inventory") or [])
    _validate_product_inputs(classification, classification_inventory, statement_groups)

    role_group_inventory = _role_group_inventory(classification_inventory)
    table_anchor_crosswalk = _table_anchor_crosswalk(classification_inventory)
    unknown_fact_diagnostics = _unknown_fact_diagnostics(classification_inventory)
    authority_provenance = _authority_provenance(classification, bridge_status)
    downstream_readiness_manifest = _downstream_readiness_manifest(classification, role_group_inventory)
    operator_inspection_summary = _operator_inspection_summary(classification, role_group_inventory, unknown_fact_diagnostics)
    product_manifest = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_product_manifest.v1",
        "product_mode": PRODUCT_MODE,
        "statement_candidate_summary": operator_inspection_summary,
        "role_group_inventory": role_group_inventory,
        "table_anchor_crosswalk": table_anchor_crosswalk,
        "unknown_fact_diagnostics": unknown_fact_diagnostics,
        "authority_provenance": authority_provenance,
        "downstream_readiness_manifest": downstream_readiness_manifest,
        "redaction_manifest": _redaction_manifest(),
    }
    product_manifest_hash = stable_hash(product_manifest)
    statement_candidate_product_hash = stable_hash(
        {
            "classification_receipt_hash": classification_receipt_hash,
            "role_group_inventory": role_group_inventory,
            "table_anchor_crosswalk": table_anchor_crosswalk,
            "unknown_fact_diagnostics": unknown_fact_diagnostics,
        }
    )
    product_order_hash = stable_hash(
        [
            {
                "statement_candidate_role": item["statement_candidate_role"],
                "first_fact_order": item["first_fact_order"],
                "last_fact_order": item["last_fact_order"],
                "fact_order_hash": item["fact_order_hash"],
            }
            for item in role_group_inventory
        ]
    )
    inspection_summary_hash = stable_hash(operator_inspection_summary)
    redaction_manifest_hash = stable_hash(product_manifest["redaction_manifest"])
    downstream_readiness_hash = stable_hash(downstream_readiness_manifest)
    receipt_hash = stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "product_mode": PRODUCT_MODE,
            "statement_classification_receipt_hash": classification_receipt_hash,
            "classification_inventory_hash": classification["classification_inventory_hash"],
            "classification_order_hash": classification["classification_order_hash"],
            "statement_group_inventory_hash": classification["statement_group_inventory_hash"],
            "unclassified_fact_inventory_hash": classification["unclassified_fact_inventory_hash"],
            "classification_diagnostics_hash": classification["classification_diagnostics_hash"],
            "product_manifest_hash": product_manifest_hash,
            "statement_candidate_product_hash": statement_candidate_product_hash,
            "product_order_hash": product_order_hash,
            "inspection_summary_hash": inspection_summary_hash,
            "redaction_manifest_hash": redaction_manifest_hash,
            "downstream_readiness_hash": downstream_readiness_hash,
        }
    )
    binding = _read_request_binding(request_id)
    if binding and binding.get("downstream_product_basis_hash") != receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_client_request_id_conflict",
            "client_request_id is already bound to a different SEC EDGAR HTML/iXBRL statement product basis.",
            http_status=409,
            blocked_fields=["client_request_id"],
        )
    existing = _read_receipt_by_hash(receipt_hash)
    if existing is not None:
        _write_request_binding(request_id, receipt_hash, str(existing["downstream_product_receipt_id"]))
        return _response_from_receipt(existing, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=True)

    receipt_id = f"{RECEIPT_PREFIX}-{receipt_hash[:24]}"
    receipt = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "product_state": READY_STATE,
        "downstream_product_receipt_id": receipt_id,
        "downstream_product_receipt_ref": f"{RECEIPT_PREFIX}:{receipt_hash[:24]}",
        "downstream_product_receipt_hash": receipt_hash,
        "statement_classification_receipt_id": classification_receipt_id,
        "statement_classification_receipt_hash": classification_receipt_hash,
        "fact_authority_receipt_id": classification["fact_authority_receipt_id"],
        "fact_authority_receipt_hash": classification["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_id": classification["fact_material_bridge_receipt_id"],
        "fact_material_bridge_receipt_hash": classification["fact_material_bridge_receipt_hash"],
        "parser_receipt_hash": classification["parser_receipt_hash"],
        "dataset_version_hash": classification["dataset_version_hash"],
        "materialization_receipt_hash": classification["materialization_receipt_hash"],
        "gate_b_decision_manifest_id": classification["gate_b_decision_manifest_id"],
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": FACT_MATERIAL_CONTRACT_ID,
        "product_manifest": product_manifest,
        "product_manifest_hash": product_manifest_hash,
        "statement_candidate_product_hash": statement_candidate_product_hash,
        "product_order_hash": product_order_hash,
        "inspection_summary_hash": inspection_summary_hash,
        "redaction_manifest_hash": redaction_manifest_hash,
        "downstream_readiness_hash": downstream_readiness_hash,
        "authority_hashes": _authority_hashes(classification, bridge_status),
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "request_id_hash": _sha256_text(request_id),
        "recorded_at": _server_time(),
        "updated_at": _server_time(),
    }
    _write_receipt(receipt)
    _write_request_binding(request_id, receipt_hash, receipt_id)
    return _response_from_receipt(receipt, request_id=request_id, schema_id=SCHEMA_ID, idempotent_replay=False)


def inspect_sec_edgar_html_inline_xbrl_statement_candidate_product_status(receipt_id: str) -> dict[str, Any]:
    receipt = _read_verified_receipt(receipt_id)
    return _response_from_receipt(
        receipt,
        request_id=f"sec-edgar-html-inline-xbrl-statement-candidate-product-status-{receipt['downstream_product_receipt_hash'][:12]}",
        schema_id=STATUS_SCHEMA_ID,
        idempotent_replay=False,
    )


def _read_fact_authority_for_classification(
    classification: Mapping[str, Any],
    bridge_status: Mapping[str, Any],
) -> Mapping[str, Any]:
    input_mode = str(
        bridge_status.get("fact_authority_input_mode")
        or layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.REGEX_FACT_AUTHORITY_INPUT_MODE
    )
    if input_mode == layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.REGEX_FACT_AUTHORITY_INPUT_MODE:
        return layer3_sec_edgar_html_inline_xbrl_fact_authority.read_sec_edgar_html_inline_xbrl_fact_authority_receipt(
            str(classification["fact_authority_receipt_id"]),
            expected_fact_authority_receipt_hash=str(classification["fact_authority_receipt_hash"]),
        )
    if input_mode == layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.ARELLE_FACT_AUTHORITY_INPUT_MODE:
        sidecar_receipt = layer3_sec_xbrl_sidecar.read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt(
            str(classification["fact_authority_receipt_id"]),
            expected_sidecar_receipt_hash=str(classification["fact_authority_receipt_hash"]),
        )
        return layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.sidecar_fact_authority_view_for_downstream(
            sidecar_receipt
        )
    _blocked(
        "sec_edgar_html_inline_xbrl_statement_candidate_product_unsupported_fact_authority_input_mode",
        "SEC EDGAR HTML/iXBRL statement product requires a supported material bridge fact-authority input mode.",
        http_status=409,
        blocked_fields=["fact_authority_input_mode"],
    )


def _validate_classification_authority(
    request: Mapping[str, Any],
    classification: Mapping[str, Any],
    classification_receipt_hash: str,
) -> None:
    if str(classification.get("statement_classification_receipt_hash") or "") != classification_receipt_hash:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_classification_hash_mismatch",
            "SEC EDGAR HTML/iXBRL statement product requires statement-classification receipt hash parity.",
            http_status=409,
            blocked_fields=["statement_classification_receipt_hash"],
        )
    if classification.get("classification_mode") != CLASSIFICATION_MODE:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_classification_mode_not_admitted",
            "SEC EDGAR HTML/iXBRL statement product requires the admitted statement-classification mode.",
            http_status=409,
            blocked_fields=["classification_mode"],
        )
    checks = {
        "fact_authority_receipt_hash": "expected_fact_authority_receipt_hash",
        "fact_material_bridge_receipt_hash": "expected_fact_material_bridge_receipt_hash",
        "parser_receipt_hash": "expected_parser_receipt_hash",
        "classification_inventory_hash": "expected_classification_inventory_hash",
        "classification_order_hash": "expected_classification_order_hash",
        "statement_group_inventory_hash": "expected_statement_group_inventory_hash",
        "unclassified_fact_inventory_hash": "expected_unclassified_fact_inventory_hash",
        "classification_diagnostics_hash": "expected_classification_diagnostics_hash",
        "materialization_receipt_hash": "expected_materialization_receipt_hash",
        "dataset_version_hash": "expected_dataset_version_hash",
    }
    for authority_key, request_key in checks.items():
        expected = str(request.get(request_key) or classification.get(authority_key) or "").strip()
        if not _is_hash(expected) or str(classification.get(authority_key) or "") != expected:
            _blocked(
                f"sec_edgar_html_inline_xbrl_statement_candidate_product_{authority_key}_mismatch",
                "SEC EDGAR HTML/iXBRL statement product requires classification authority hash parity.",
                http_status=409,
                blocked_fields=[request_key],
            )
    expected_gate_b = str(
        request.get("expected_gate_b_decision_manifest_id")
        or classification.get("gate_b_decision_manifest_id")
        or ""
    ).strip()
    if not expected_gate_b or str(classification.get("gate_b_decision_manifest_id") or "") != expected_gate_b:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_gate_b_decision_manifest_mismatch",
            "SEC EDGAR HTML/iXBRL statement product requires Gate B manifest parity.",
            http_status=409,
            blocked_fields=["expected_gate_b_decision_manifest_id"],
        )


def _validate_upstream_authority(
    request: Mapping[str, Any],
    classification: Mapping[str, Any],
    fact_receipt: Mapping[str, Any],
    bridge_status: Mapping[str, Any],
) -> None:
    authority_hashes = classification.get("authority_hashes")
    if not isinstance(authority_hashes, Mapping):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_classification_authority_hashes_missing",
            "SEC EDGAR HTML/iXBRL statement product requires classification authority hashes.",
            http_status=409,
            blocked_fields=["authority_hashes"],
        )
    checks = {
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
    }
    for authority_key, request_key in checks.items():
        expected = str(request.get(request_key) or authority_hashes.get(authority_key) or "").strip()
        if not _is_hash(expected):
            _blocked(
                f"sec_edgar_html_inline_xbrl_statement_candidate_product_{request_key}_invalid",
                "SEC EDGAR HTML/iXBRL statement product requires SHA-256 authority hashes.",
                blocked_fields=[request_key],
            )
        if str(fact_receipt.get(authority_key) or "") != expected or str(authority_hashes.get(authority_key) or "") != expected:
            _blocked(
                f"sec_edgar_html_inline_xbrl_statement_candidate_product_{authority_key}_mismatch",
                "SEC EDGAR HTML/iXBRL statement product requires fact and classification authority parity.",
                http_status=409,
                blocked_fields=[request_key],
            )
    bridge_checks = {
        "fact_material_bridge_receipt_hash": classification["fact_material_bridge_receipt_hash"],
        "materialization_receipt_hash": classification["materialization_receipt_hash"],
        "dataset_version_hash": classification["dataset_version_hash"],
        "gate_b_decision_manifest_id": classification["gate_b_decision_manifest_id"],
    }
    for key, expected in bridge_checks.items():
        if str(bridge_status.get(key) or "") != str(expected or ""):
            _blocked(
                f"sec_edgar_html_inline_xbrl_statement_candidate_product_bridge_{key}_mismatch",
                "SEC EDGAR HTML/iXBRL statement product requires material bridge authority parity.",
                http_status=409,
                blocked_fields=[key],
            )


def _validate_product_inputs(
    classification: Mapping[str, Any],
    inventory: list[Any],
    statement_groups: list[Any],
) -> None:
    if not inventory or stable_hash(inventory) != classification.get("classification_inventory_hash"):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_classification_inventory_hash_mismatch",
            "SEC EDGAR HTML/iXBRL statement product requires classification inventory hash parity.",
            http_status=409,
            blocked_fields=["classification_inventory_hash"],
        )
    if stable_hash(statement_groups) != classification.get("statement_group_inventory_hash"):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_statement_group_inventory_hash_mismatch",
            "SEC EDGAR HTML/iXBRL statement product requires statement group inventory hash parity.",
            http_status=409,
            blocked_fields=["statement_group_inventory_hash"],
        )
    if not all(isinstance(item, Mapping) and item.get("statement_candidate_role") for item in inventory):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_classification_inventory_invalid",
            "SEC EDGAR HTML/iXBRL statement product requires a classified fact inventory.",
            http_status=409,
            blocked_fields=["classification_inventory"],
        )


def _role_group_inventory(inventory: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    roles = sorted({str(item.get("statement_candidate_role") or "") for item in inventory})
    groups: list[dict[str, Any]] = []
    for role in roles:
        items = [item for item in inventory if item.get("statement_candidate_role") == role]
        orders = [int(item.get("fact_order") or 0) for item in items]
        table_anchors = sorted({str(item.get("table_candidate_anchor_hash") or "") for item in items if item.get("table_candidate_anchor_hash")})
        groups.append(
            {
                "statement_candidate_role": role,
                "fact_count": len(items),
                "first_fact_order": min(orders) if orders else None,
                "last_fact_order": max(orders) if orders else None,
                "fact_order_hash": stable_hash(orders),
                "classification_record_inventory_hash": stable_hash(
                    [item.get("classification_id_or_order_key") for item in items]
                ),
                "table_anchor_inventory_hash": stable_hash(table_anchors),
                "table_anchor_count": len(table_anchors),
                "raw_values_included": False,
                "final_financial_statement_semantics_claimed": False,
            }
        )
    return groups


def _table_anchor_crosswalk(inventory: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    anchors = sorted({str(item.get("table_candidate_anchor_hash") or "") for item in inventory if item.get("table_candidate_anchor_hash")})
    return [
        {
            "table_candidate_anchor_hash": anchor,
            "statement_candidate_roles": sorted(
                {
                    str(item.get("statement_candidate_role") or "")
                    for item in inventory
                    if item.get("table_candidate_anchor_hash") == anchor
                }
            ),
            "classification_record_inventory_hash": stable_hash(
                [
                    item.get("classification_id_or_order_key")
                    for item in inventory
                    if item.get("table_candidate_anchor_hash") == anchor
                ]
            ),
            "raw_table_bytes_included": False,
        }
        for anchor in anchors
    ]


def _unknown_fact_diagnostics(inventory: list[Mapping[str, Any]]) -> dict[str, Any]:
    unknown = [item for item in inventory if item.get("statement_candidate_role") == "unknown_or_unclassified"]
    return {
        "unknown_or_unclassified_count": len(unknown),
        "unknown_or_unclassified_inventory_hash": stable_hash(unknown),
        "unknown_facts_retained": True,
        "unknown_raw_values_included": False,
    }


def _authority_provenance(classification: Mapping[str, Any], bridge_status: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "statement_classification_receipt_id": classification["statement_classification_receipt_id"],
        "statement_classification_receipt_hash": classification["statement_classification_receipt_hash"],
        "fact_authority_receipt_id": classification["fact_authority_receipt_id"],
        "fact_authority_receipt_hash": classification["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_id": classification["fact_material_bridge_receipt_id"],
        "fact_material_bridge_receipt_hash": classification["fact_material_bridge_receipt_hash"],
        "parser_receipt_hash": classification["parser_receipt_hash"],
        "materialization_receipt_hash": bridge_status["materialization_receipt_hash"],
        "dataset_version_hash": bridge_status["dataset_version_hash"],
        "gate_b_decision_manifest_id": bridge_status["gate_b_decision_manifest_id"],
        "raw_url_included": False,
        "raw_local_path_included": False,
    }


def _downstream_readiness_manifest(
    classification: Mapping[str, Any],
    role_group_inventory: list[Mapping[str, Any]],
) -> dict[str, Any]:
    fact_count = int((classification.get("classification_diagnostics") or {}).get("fact_count") or 0)
    grouped_count = sum(int(item.get("fact_count") or 0) for item in role_group_inventory)
    return {
        "ready_for_layer3_downstream_product_inspection": True,
        "ready_for_package_review_selection": True,
        "fact_count": fact_count,
        "product_grouped_fact_count": grouped_count,
        "count_reconciles_with_classification": grouped_count == fact_count,
        "requires_taxonomy_for_final_statement_semantics": True,
        "requires_companyfacts_for_external_fact_validation": True,
        "raw_values_required_for_this_product": False,
        "raw_values_included": False,
    }


def _operator_inspection_summary(
    classification: Mapping[str, Any],
    role_group_inventory: list[Mapping[str, Any]],
    unknown_fact_diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "redacted_projection": True,
        "classification_inventory_hash": classification["classification_inventory_hash"],
        "classification_order_hash": classification["classification_order_hash"],
        "statement_group_inventory_hash": classification["statement_group_inventory_hash"],
        "statement_candidate_role_counts": {
            item["statement_candidate_role"]: item["fact_count"] for item in role_group_inventory
        },
        "unknown_or_unclassified_count": unknown_fact_diagnostics["unknown_or_unclassified_count"],
        "source_order_preserved": True,
        "marker_order_preserved": True,
        "table_anchor_order_preserved": True,
        "final_financial_statement_semantics_claimed": False,
        "raw_values_returned": False,
        "raw_html_returned": False,
        "raw_url_returned": False,
    }


def _redaction_manifest() -> dict[str, Any]:
    return {
        "redaction_policy_id": REDACTION_POLICY_ID,
        "raw_fact_values_exposed": False,
        "raw_html_exposed": False,
        "raw_urls_exposed": False,
        "local_paths_exposed": False,
        "artifact_bytes_exposed": False,
        "dataset_storage_ref_exposed": False,
    }


def _authority_hashes(
    classification: Mapping[str, Any],
    bridge_status: Mapping[str, Any],
) -> dict[str, str]:
    authority = dict(classification.get("authority_hashes") or {})
    return {
        **{str(key): str(value) for key, value in authority.items()},
        "statement_classification_receipt_hash": str(classification["statement_classification_receipt_hash"]),
        "classification_inventory_hash": str(classification["classification_inventory_hash"]),
        "classification_order_hash": str(classification["classification_order_hash"]),
        "statement_group_inventory_hash": str(classification["statement_group_inventory_hash"]),
        "unclassified_fact_inventory_hash": str(classification["unclassified_fact_inventory_hash"]),
        "classification_diagnostics_hash": str(classification["classification_diagnostics_hash"]),
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
    product_manifest = dict(receipt["product_manifest"])
    response = {
        **_base_response(request_id=request_id, status="ready", schema_id=schema_id),
        "mode": PRODUCT_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "product_state": receipt["product_state"],
        "downstream_product_receipt_id": receipt["downstream_product_receipt_id"],
        "downstream_product_receipt_ref": receipt["downstream_product_receipt_ref"],
        "downstream_product_receipt_hash": receipt["downstream_product_receipt_hash"],
        "statement_classification_receipt_id": receipt["statement_classification_receipt_id"],
        "statement_classification_receipt_hash": receipt["statement_classification_receipt_hash"],
        "fact_authority_receipt_hash": receipt["fact_authority_receipt_hash"],
        "fact_material_bridge_receipt_hash": receipt["fact_material_bridge_receipt_hash"],
        "parser_receipt_hash": receipt["parser_receipt_hash"],
        "source_family": SOURCE_FAMILY,
        "parser_family": PARSER_FAMILY,
        "typed_content_contract_id": FACT_MATERIAL_CONTRACT_ID,
        "product_manifest": product_manifest,
        "product_manifest_hash": receipt["product_manifest_hash"],
        "statement_candidate_product_hash": receipt["statement_candidate_product_hash"],
        "product_order_hash": receipt["product_order_hash"],
        "inspection_summary_hash": receipt["inspection_summary_hash"],
        "redaction_manifest_hash": receipt["redaction_manifest_hash"],
        "downstream_readiness_hash": receipt["downstream_readiness_hash"],
        "authority_hashes": dict(receipt["authority_hashes"]),
        "status_projection": {
            "ready": True,
            "redacted_projection": True,
            "statement_candidate_role_counts": product_manifest["statement_candidate_summary"][
                "statement_candidate_role_counts"
            ],
            "unknown_or_unclassified_count": product_manifest["unknown_fact_diagnostics"][
                "unknown_or_unclassified_count"
            ],
            "product_manifest_hash": receipt["product_manifest_hash"],
            "statement_candidate_product_hash": receipt["statement_candidate_product_hash"],
            "redaction_manifest_hash": receipt["redaction_manifest_hash"],
            "downstream_readiness_hash": receipt["downstream_readiness_hash"],
            "raw_values_returned": False,
            "final_financial_statement_semantics_claimed": False,
            "next_allowed_actions": ["select_sec_edgar_html_inline_xbrl_statement_candidate_package_review"],
        },
        "cache": {"idempotent_replay": idempotent_replay, "network_request_made": False},
        "negative_invariants": dict(receipt["negative_invariants"]),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["select SEC HTML/iXBRL statement candidate package/review slice"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL statement product would expose raw path, URL, token, or value authority.",
            http_status=409,
        )
    return response


def _blocked_response(
    *,
    request_id: str,
    statement_classification_receipt_hash: str,
    reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    response = {
        **_base_response(request_id=request_id, status="blocked", schema_id=SCHEMA_ID),
        "mode": PRODUCT_MODE,
        "product_mode": PRODUCT_MODE,
        "classification_mode": CLASSIFICATION_MODE,
        "operator_decision": OPERATOR_DECISION,
        "product_state": BLOCKED_STATE,
        "downstream_product_receipt_id": None,
        "downstream_product_receipt_ref": None,
        "downstream_product_receipt_hash": None,
        "statement_classification_receipt_hash": statement_classification_receipt_hash,
        "product_manifest": None,
        "product_manifest_hash": None,
        "statement_candidate_product_hash": None,
        "product_order_hash": None,
        "inspection_summary_hash": None,
        "redaction_manifest_hash": None,
        "downstream_readiness_hash": None,
        "status_projection": {
            "ready": False,
            "redacted_projection": True,
            "blocked_reasons": reasons,
            "next_allowed_actions": ["refresh_sec_edgar_html_inline_xbrl_statement_classification_authority"],
        },
        "negative_invariants": _negative_invariants(),
        "redaction_policy_id": REDACTION_POLICY_ID,
        "next_allowed_actions": ["refresh SEC HTML/iXBRL statement classification authority"],
    }
    if _contains_forbidden_output_ref(response):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_blocked_response_raw_authority_exposed",
            "SEC EDGAR HTML/iXBRL statement product blocked response would expose raw authority.",
            http_status=409,
        )
    return response


def _normalise_request(fields: Mapping[str, Any]) -> dict[str, Any]:
    request = {str(key): value for key, value in dict(fields or {}).items() if value is not None}
    blocked = sorted(key for key in request if key.lower() in _FORBIDDEN_INPUT_KEYS)
    nested = _find_forbidden_nested_fields(request)
    if blocked or nested:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_forbidden_request_fields",
            "SEC EDGAR HTML/iXBRL statement product rejects caller paths, URLs, HTML, values, bytes, credentials, connector dispatch, model, browser, source-expansion, and frontend authority.",
            blocked_fields=[*blocked, *nested],
        )
    unknown = sorted(set(request) - _ALLOWED_FIELDS)
    if unknown:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_unknown_field",
            "SEC EDGAR HTML/iXBRL statement product fields are intentionally scoped.",
            blocked_fields=unknown,
        )
    schema_id = str(request.get("schema_id") or REQUEST_SCHEMA_ID).strip()
    if schema_id != REQUEST_SCHEMA_ID:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_schema_not_admitted",
            "SEC EDGAR HTML/iXBRL statement product requires the admitted request schema.",
            blocked_fields=["schema_id"],
        )
    return request


def _write_receipt(receipt: Mapping[str, Any]) -> None:
    target = _receipt_path(str(receipt["downstream_product_receipt_id"]))
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
            "sec_edgar_html_inline_xbrl_statement_candidate_product_receipt_id_invalid",
            "SEC EDGAR HTML/iXBRL statement product status requires a server-issued receipt id.",
            http_status=400,
            blocked_fields=["downstream_product_receipt_id"],
        )
    try:
        receipt = json.loads(_receipt_path(receipt_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_receipt_missing",
            "SEC EDGAR HTML/iXBRL statement product receipt was not found.",
            http_status=404,
            blocked_fields=["downstream_product_receipt_id"],
        )
    except (OSError, json.JSONDecodeError) as exc:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_receipt_unreadable",
            "SEC EDGAR HTML/iXBRL statement product receipt could not be read.",
            http_status=409,
            blocked_fields=[exc.__class__.__name__],
        )
    if not isinstance(receipt, dict) or receipt.get("downstream_product_receipt_id") != receipt_id:
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_receipt_invalid",
            "SEC EDGAR HTML/iXBRL statement product receipt is invalid or mismatched.",
            http_status=409,
        )
    if not _is_hash(str(receipt.get("downstream_product_receipt_hash") or "")):
        _blocked(
            "sec_edgar_html_inline_xbrl_statement_candidate_product_receipt_hash_invalid",
            "SEC EDGAR HTML/iXBRL statement product receipt hash is invalid.",
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
            "sec_edgar_html_inline_xbrl_statement_candidate_product_request_binding_unreadable",
            "SEC EDGAR HTML/iXBRL statement product request binding could not be read.",
            http_status=409,
        )
    return value if isinstance(value, dict) else None


def _write_request_binding(request_id: str, basis_hash: str, receipt_id: str) -> None:
    target = _request_bindings_dir() / f"{_sha256_text(request_id)}.json"
    binding = {
        "schema_id": "layer3.sec_edgar_html_inline_xbrl_statement_candidate_product_request_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "client_request_id_hash": _sha256_text(request_id),
        "downstream_product_basis_hash": basis_hash,
        "downstream_product_receipt_id": receipt_id,
        "recorded_at": _server_time(),
    }
    if target.exists():
        existing = _read_request_binding(request_id) or {}
        if existing.get("downstream_product_basis_hash") != basis_hash:
            _blocked(
                "sec_edgar_html_inline_xbrl_statement_candidate_product_request_binding_conflict",
                "SEC EDGAR HTML/iXBRL statement product request binding conflicts with existing authority.",
                http_status=409,
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(binding, sort_keys=True, indent=2) + "\n")


def _find_forbidden_nested_fields(value: Any, prefix: str = "") -> list[str]:
    return find_forbidden_ref_paths(value, forbidden_keys=_FORBIDDEN_INPUT_KEYS, prefix=prefix)


def _contains_forbidden_output_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output_ref(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden_output_ref(item) for item in value)
    if isinstance(value, str):
        return contains_forbidden_ref(value)
    return False


def _negative_invariants() -> dict[str, bool]:
    return {
        "statement_classification_receipt_required": True,
        "fact_authority_receipt_required": True,
        "fact_material_bridge_receipt_required": True,
        "live_sec_network_fetch_performed_by_product": False,
        "submissions_lookup_runtime_performed_by_product": False,
        "browser_supplied_html_admitted": False,
        "browser_supplied_raw_url_admitted": False,
        "browser_supplied_local_path_admitted": False,
        "artifact_bytes_admitted": False,
        "raw_fact_values_admitted": False,
        "standalone_xml_xbrl_fact_authority_enabled": False,
        "sec_companyfacts_api_runtime_enabled": False,
        "taxonomy_network_resolution_enabled": False,
        "financial_statement_semantics_finalized": False,
        "statement_classification_mutated": False,
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
            "sec_edgar_html_inline_xbrl_statement_candidate_product_storage_root_unavailable",
            "SEC EDGAR HTML/iXBRL statement product requires the existing Layer 3 storage root.",
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
            f"sec_edgar_html_inline_xbrl_statement_candidate_product_{key}_missing",
            f"SEC EDGAR HTML/iXBRL statement product requires {key}.",
            blocked_fields=[key],
        )
    return value


def _required_hash(fields: Mapping[str, Any], key: str) -> str:
    value = _required(fields, key)
    if not _is_hash(value):
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_product_{key}_invalid",
            f"SEC EDGAR HTML/iXBRL statement product requires a 64-character hash for {key}.",
            blocked_fields=[key],
        )
    return value


def _require_exact(fields: Mapping[str, Any], key: str, expected: str) -> None:
    if _required(fields, key) != expected:
        _blocked(
            f"sec_edgar_html_inline_xbrl_statement_candidate_product_{key}_not_admitted",
            "SEC EDGAR HTML/iXBRL statement product request does not match the admitted runtime contract.",
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
