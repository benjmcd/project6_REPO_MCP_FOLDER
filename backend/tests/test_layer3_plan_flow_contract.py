from __future__ import annotations

from app.services import layer3_plan_flow_contract as contract
from app.services import layer3_workbench


def _legacy_blocked(payload: dict[str, object], forbidden_fields: frozenset[str]) -> list[str]:
    return sorted(key for key in forbidden_fields if key in payload)


def test_plan_flow_contract_is_shared() -> None:
    assert layer3_workbench.PLAN_APPROVAL_FORBIDDEN_FIELDS is contract.PLAN_APPROVAL_FORBIDDEN_FIELDS
    assert layer3_workbench.PLAN_REVISION_FORBIDDEN_FIELDS is contract.PLAN_REVISION_FORBIDDEN_FIELDS
    assert (
        layer3_workbench.APPROVED_PLAN_CANCEL_FORBIDDEN_FIELDS
        is contract.APPROVED_PLAN_CANCEL_FORBIDDEN_FIELDS
    )
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

    recovery_payload = {
        "client_request_id": "recovery-1",
        "session_id": "session-1",
        "source_revision_state": "plan_rejected",
        "source_preview_id": "preview-1",
        "source_preview_hash": "hash-1",
        "operator_decision": "recover_for_preview_refresh",
        "approved_plan_supersession": True,
        "provider_public_url": "https://example.invalid/object",
        "browser_persisted_state": {"authoritative": True},
    }
    assert contract.plan_revision_recovery_blocked_fields(recovery_payload) == _legacy_blocked(
        recovery_payload,
        contract.PLAN_REVISION_RECOVERY_FORBIDDEN_FIELDS,
    )

    cancel_payload = {
        "client_request_id": "cancel-1",
        "session_id": "session-1",
        "analysis_plan_id": "plan-1",
        "source_preview_id": "preview-1",
        "source_preview_hash": "hash-1",
        "operator_decision": "cancel_approved_plan_without_replacement",
        "replacement_plan": {"mode": "not-admitted"},
        "approved_plan_supersession": True,
        "create_pass_runs": True,
    }
    assert contract.approved_plan_cancel_blocked_fields(cancel_payload) == _legacy_blocked(
        cancel_payload,
        contract.APPROVED_PLAN_CANCEL_FORBIDDEN_FIELDS,
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


def test_source_classes_from_plan_preview_preserves_workbench_authority_ordering() -> None:
    plan_preview = {
        "admitted_sets": [
            {"source_summary": {"source_classes": ["aps", "dataset"]}},
            {"source_summary": {"source_classes": ["aps", 42]}},
            "ignored-non-dict-item",
        ],
        "excluded_sets": [
            {"source_summary": {"source_classes": ["manual", "dataset"]}},
            {"source_summary": {"source_classes": []}},
        ],
    }

    assert contract.source_classes_from_plan_preview(plan_preview) == [
        "42",
        "aps",
        "dataset",
        "manual",
    ]


def test_workbench_delegates_plan_preview_source_classes_to_contract() -> None:
    plan_preview = {
        "admitted_sets": [
            {"source_summary": {"source_classes": ["dataset", "aps"]}},
        ],
        "excluded_sets": [
            {"source_summary": {"source_classes": ["unsupported"]}},
        ],
    }

    assert layer3_workbench._source_classes_from_plan_preview(plan_preview) == (
        contract.source_classes_from_plan_preview(plan_preview)
    )
