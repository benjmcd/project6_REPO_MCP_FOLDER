from __future__ import annotations

from collections.abc import Mapping
from typing import Any


STATEMENT_CLASSIFICATION_HASH_VERSION = "sec_edgar_html_inline_xbrl_fact_statement_classification_hash_v1"
STATEMENT_CLASSIFICATION_MODE = "sec_edgar_html_inline_xbrl_fact_to_statement_classification_v1"

CLASSIFICATION_RECEIPT_HASH_BASIS_KEYS = (
    "hash_version",
    "classification_mode",
    "fact_authority_receipt_hash",
    "fact_material_bridge_receipt_hash",
    "fact_inventory_hash",
    "classification_inventory_hash",
    "semantic_profile_inventory_hash",
    "classification_order_hash",
    "statement_group_inventory_hash",
    "unclassified_fact_inventory_hash",
    "classification_diagnostics_hash",
)

CLASSIFICATION_TOP_LEVEL_AUTHORITY_HASH_KEYS = (
    "fact_authority_receipt_hash",
    "fact_material_bridge_receipt_hash",
    "fact_inventory_hash",
)

CLASSIFICATION_AUTHORITY_HASH_KEYS = (
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
    "fact_authority_receipt_hash",
    "fact_material_bridge_receipt_hash",
    "dataset_version_hash",
    "materialization_receipt_hash",
    "gate_b_decision_manifest_id",
)


def classification_receipt_hash_basis(
    *,
    classification_mode: str = STATEMENT_CLASSIFICATION_MODE,
    fact_authority_receipt_hash: str,
    fact_material_bridge_receipt_hash: str,
    fact_inventory_hash: str,
    classification_inventory_hash: str,
    semantic_profile_inventory_hash: str,
    classification_order_hash: str,
    statement_group_inventory_hash: str,
    unclassified_fact_inventory_hash: str,
    classification_diagnostics_hash: str,
) -> dict[str, str]:
    return {
        "hash_version": STATEMENT_CLASSIFICATION_HASH_VERSION,
        "classification_mode": classification_mode,
        "fact_authority_receipt_hash": fact_authority_receipt_hash,
        "fact_material_bridge_receipt_hash": fact_material_bridge_receipt_hash,
        "fact_inventory_hash": fact_inventory_hash,
        "classification_inventory_hash": classification_inventory_hash,
        "semantic_profile_inventory_hash": semantic_profile_inventory_hash,
        "classification_order_hash": classification_order_hash,
        "statement_group_inventory_hash": statement_group_inventory_hash,
        "unclassified_fact_inventory_hash": unclassified_fact_inventory_hash,
        "classification_diagnostics_hash": classification_diagnostics_hash,
    }


def classification_authority_view(receipt: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    authority_hashes = receipt.get("authority_hashes")
    authority = authority_hashes if isinstance(authority_hashes, Mapping) else {}
    return {
        "top_level": {
            key: receipt.get(key) for key in CLASSIFICATION_TOP_LEVEL_AUTHORITY_HASH_KEYS
        },
        "authority_hashes": {
            key: authority.get(key) for key in CLASSIFICATION_AUTHORITY_HASH_KEYS
        },
    }
