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


def test_package_review_submit_contract_admits_mixed_material_fields_only_at_contract_layer() -> None:
    mixed_submit_payload = {
        "client_request_id": "mixed-submit",
        "session_id": "session-1",
        "material_preview_id": "material-preview-1",
        "material_preview_hash": "a" * 64,
        "package_review_preview_hash": "preview-hash",
        "contract_hash": "b" * 64,
        "construction_basis_hash": "c" * 64,
        "reconciliation_record_id": "reconciliation-1",
        "output_package_ids": ["pkg-1", "pkg-2", "pkg-3"],
        "payload_hashes": ["h1", "h2", "h3"],
        "operator_decision": "approved",
    }
    assert contract.package_review_submit_blocked_fields(mixed_submit_payload) == []

    blocked = contract.package_review_submit_blocked_fields(
        {
            **mixed_submit_payload,
            "provider_public_url": "https://example.invalid/package",
            "connector_dispatch": {"target": "external"},
            "onlook": {"include": True},
        }
    )
    assert blocked == ["connector_dispatch", "onlook", "provider_public_url"]
