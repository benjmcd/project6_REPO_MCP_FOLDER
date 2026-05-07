from __future__ import annotations

from typing import Any

from app.services.layer3_pass_entry import PLAN_PREVIEW_HASH_SCHEMA_ID


PLAN_PREVIEW_IDENTITY_SCHEMA_ID = "layer3.plan_preview_identity.v1"
MATERIAL_PREVIEW_HASH_SCHEMA_ID = "layer3.material_preview_hash.v1"

PLAN_PREVIEW_HASH_INCLUDED_INPUTS = (
    "session_id",
    "committed_gate_b_material_and_source_ids",
    "committed_gate_c_analysis_set_unit_group_ids",
    "owner_service_plan_version",
    "admissible_and_excluded_set_payloads",
    "planned_pass_payloads",
    "deterministic_warning_codes",
)
PLAN_PREVIEW_HASH_EXCLUDED_INPUTS = (
    "browser_render_order",
    "local_ui_labels",
    "non_semantic_timestamps",
    "collapsed_or_expanded_ui_state",
    "non_authoritative_explanatory_text",
    "unpersisted_generated_alternatives",
)
MATERIAL_PREVIEW_HASH_INCLUDED_INPUTS = (
    "candidate_id",
    "source_class",
    "source_ref",
    "query_basis",
    "provenance_ref",
    "source_identity",
    "source_provenance",
    "payload",
    "load_summary",
)
MATERIAL_PREVIEW_HASH_EXCLUDED_INPUTS = (
    "operator_decision",
    "operator_reason",
    "browser_render_order",
    "local_ui_labels",
    "expanded_or_collapsed_ui_state",
)


def plan_preview_hash_contract() -> dict[str, Any]:
    return {
        "schema_id": PLAN_PREVIEW_HASH_SCHEMA_ID,
        "authority_source": "server_owner_service_preview",
        "included_inputs": list(PLAN_PREVIEW_HASH_INCLUDED_INPUTS),
        "excluded_inputs": list(PLAN_PREVIEW_HASH_EXCLUDED_INPUTS),
        "mismatch_error_code": "preview_mismatch",
        "mismatch_rule": "fail_closed_no_execution_or_artifact_writes",
    }


def material_preview_hash_contract() -> dict[str, Any]:
    return {
        "schema_id": MATERIAL_PREVIEW_HASH_SCHEMA_ID,
        "authority_source": "server_material_preview",
        "included_inputs": list(MATERIAL_PREVIEW_HASH_INCLUDED_INPUTS),
        "excluded_inputs": list(MATERIAL_PREVIEW_HASH_EXCLUDED_INPUTS),
        "mismatch_error_code": "material_preview_mismatch",
        "mismatch_rule": "fail_closed_no_session_or_artifact_writes",
        "supplied_hash_required_current_slice": False,
    }


def preview_identity(*, preview_id: str, preview_hash: str) -> dict[str, Any]:
    return {
        "schema_id": PLAN_PREVIEW_IDENTITY_SCHEMA_ID,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "preview_hash_schema_id": PLAN_PREVIEW_HASH_SCHEMA_ID,
        "authority_source": "server_owner_service_preview",
        "stale_preview_writes_blocked": True,
        "mismatch_error_code": "preview_mismatch",
    }
