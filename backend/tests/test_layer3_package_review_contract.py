from __future__ import annotations

from app.services import layer3_package_review_contract as contract
from app.services import layer3_workbench


def _legacy_blocked(
    payload: dict[str, object],
    allowed_fields: frozenset[str],
    forbidden_fields: frozenset[str],
) -> list[str]:
    return sorted(
        set(key for key in payload if key not in allowed_fields)
        | set(key for key in forbidden_fields if key in payload)
    )


def test_package_review_contract_is_shared_without_behavior_change() -> None:
    assert (
        layer3_workbench.PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS
        is contract.PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS
    )
    assert (
        layer3_workbench.PACKAGE_REVIEW_PREVIEW_FORBIDDEN_FIELDS
        is contract.PACKAGE_REVIEW_PREVIEW_FORBIDDEN_FIELDS
    )
    assert (
        layer3_workbench.PACKAGE_CONSTRUCTION_COMMIT_ALLOWED_FIELDS
        is contract.PACKAGE_CONSTRUCTION_COMMIT_ALLOWED_FIELDS
    )
    assert (
        layer3_workbench.PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS
        is contract.PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS
    )
    assert (
        layer3_workbench.PACKAGE_REVIEW_SUBMIT_ALLOWED_FIELDS
        is contract.PACKAGE_REVIEW_SUBMIT_ALLOWED_FIELDS
    )
    assert (
        layer3_workbench.PACKAGE_REVIEW_SUBMIT_FORBIDDEN_FIELDS
        is contract.PACKAGE_REVIEW_SUBMIT_FORBIDDEN_FIELDS
    )


def test_package_review_contract_blocks_same_fields_as_legacy_logic() -> None:
    preview_payload = {
        "session_id": "session-1",
        "package": True,
        "source_expansion": True,
        "unexpected_field": True,
    }
    assert contract.package_review_preview_blocked_fields(preview_payload) == _legacy_blocked(
        preview_payload,
        contract.PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS,
        contract.PACKAGE_REVIEW_PREVIEW_FORBIDDEN_FIELDS,
    )

    commit_payload = {
        "session_id": "session-1",
        "expected_package_kinds": ["canonical_internal"],
        "package_payload": {},
        "unexpected_field": True,
    }
    assert contract.package_construction_commit_blocked_fields(commit_payload) == _legacy_blocked(
        commit_payload,
        contract.PACKAGE_CONSTRUCTION_COMMIT_ALLOWED_FIELDS,
        contract.PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS,
    )

    submit_payload = {
        "session_id": "session-1",
        "operator_decision": "approved",
        "rebuild_package": True,
        "unexpected_field": True,
    }
    assert contract.package_review_submit_blocked_fields(submit_payload) == _legacy_blocked(
        submit_payload,
        contract.PACKAGE_REVIEW_SUBMIT_ALLOWED_FIELDS,
        contract.PACKAGE_REVIEW_SUBMIT_FORBIDDEN_FIELDS,
    )
