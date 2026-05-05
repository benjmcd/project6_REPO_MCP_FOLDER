from __future__ import annotations

from app.services import layer3_workbench
from app.services.layer3_pass_entry import PLAN_PREVIEW_HASH_SCHEMA_ID
from app.services.layer3_preview_contract import (
    MATERIAL_PREVIEW_HASH_SCHEMA_ID,
    MATERIAL_PREVIEW_HASH_EXCLUDED_INPUTS,
    MATERIAL_PREVIEW_HASH_INCLUDED_INPUTS,
    PLAN_PREVIEW_HASH_EXCLUDED_INPUTS,
    PLAN_PREVIEW_HASH_INCLUDED_INPUTS,
    PLAN_PREVIEW_IDENTITY_SCHEMA_ID,
    material_preview_hash_contract,
    plan_preview_hash_contract,
    preview_identity,
)


def test_layer3_preview_contracts_are_shared_without_behavior_change() -> None:
    plan_contract = plan_preview_hash_contract()
    material_contract = material_preview_hash_contract()
    identity = preview_identity(preview_id="preview-1", preview_hash="hash-1")

    assert plan_contract == {
        "schema_id": PLAN_PREVIEW_HASH_SCHEMA_ID,
        "authority_source": "server_owner_service_preview",
        "included_inputs": list(PLAN_PREVIEW_HASH_INCLUDED_INPUTS),
        "excluded_inputs": list(PLAN_PREVIEW_HASH_EXCLUDED_INPUTS),
        "mismatch_error_code": "preview_mismatch",
        "mismatch_rule": "fail_closed_no_execution_or_artifact_writes",
    }
    assert material_contract == {
        "schema_id": MATERIAL_PREVIEW_HASH_SCHEMA_ID,
        "authority_source": "server_material_preview",
        "included_inputs": list(MATERIAL_PREVIEW_HASH_INCLUDED_INPUTS),
        "excluded_inputs": list(MATERIAL_PREVIEW_HASH_EXCLUDED_INPUTS),
        "mismatch_error_code": "material_preview_mismatch",
        "mismatch_rule": "fail_closed_no_session_or_artifact_writes",
        "supplied_hash_required_current_slice": False,
    }
    assert identity == {
        "schema_id": PLAN_PREVIEW_IDENTITY_SCHEMA_ID,
        "preview_id": "preview-1",
        "preview_hash": "hash-1",
        "preview_hash_schema_id": PLAN_PREVIEW_HASH_SCHEMA_ID,
        "authority_source": "server_owner_service_preview",
        "stale_preview_writes_blocked": True,
        "mismatch_error_code": "preview_mismatch",
    }

    readiness = layer3_workbench.readiness_contract()
    assert readiness["preview_hash_contract"] == plan_contract
    assert readiness["material_preview_hash_contract"] == material_contract
