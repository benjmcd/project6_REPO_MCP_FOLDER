from __future__ import annotations

from app.services import layer3_plan_flow_contract as contract
from app.services import layer3_workbench


def _legacy_blocked(payload: dict[str, object], forbidden_fields: frozenset[str]) -> list[str]:
    return sorted(key for key in forbidden_fields if key in payload)


def test_plan_flow_contract_is_shared_without_behavior_change() -> None:
    assert layer3_workbench.PLAN_APPROVAL_FORBIDDEN_FIELDS is contract.PLAN_APPROVAL_FORBIDDEN_FIELDS
    assert layer3_workbench.PLAN_REVISION_FORBIDDEN_FIELDS is contract.PLAN_REVISION_FORBIDDEN_FIELDS
    assert (
        layer3_workbench.EXECUTION_SELECTION_FORBIDDEN_FIELDS
        is contract.EXECUTION_SELECTION_FORBIDDEN_FIELDS
    )


def test_plan_flow_contract_blocks_same_fields_as_legacy_logic() -> None:
    approval_payload = {
        "session_id": "session-1",
        "operator_confirmation": True,
        "execute": True,
        "llm_plan": "make one",
        "client_request_id": "approval-1",
    }
    assert contract.plan_approval_blocked_fields(approval_payload) == _legacy_blocked(
        approval_payload,
        contract.PLAN_APPROVAL_FORBIDDEN_FIELDS,
    )

    revision_payload = {
        "session_id": "session-1",
        "operator_decision": "request_revision",
        "execute": True,
        "rag_plan": {"enabled": True},
    }
    assert contract.plan_revision_blocked_fields(revision_payload) == _legacy_blocked(
        revision_payload,
        contract.PLAN_REVISION_FORBIDDEN_FIELDS,
    )

    selection_payload = {
        "session_id": "session-1",
        "analysis_plan_id": "plan-1",
        "preview_id": "preview-1",
        "preview_hash": "hash-1",
        "start_execution": True,
        "local_upload": True,
    }
    assert contract.execution_selection_blocked_fields(selection_payload) == _legacy_blocked(
        selection_payload,
        contract.EXECUTION_SELECTION_FORBIDDEN_FIELDS,
    )
