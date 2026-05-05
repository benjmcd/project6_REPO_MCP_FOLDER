from __future__ import annotations

from app.services import layer3_handoff_contract as contract
from app.services import layer3_workbench


def test_handoff_contract_is_shared_without_behavior_change() -> None:
    assert (
        layer3_workbench.HANDOFF_EXPORT_PREPARE_ALLOWED_FIELDS
        is contract.HANDOFF_EXPORT_PREPARE_ALLOWED_FIELDS
    )
    assert (
        layer3_workbench.HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS
        is contract.HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS
    )
    assert (
        layer3_workbench.APS_HANDOFF_DISPATCH_ALLOWED_FIELDS
        is contract.APS_HANDOFF_DISPATCH_ALLOWED_FIELDS
    )
    assert (
        layer3_workbench.APS_HANDOFF_DISPATCH_FORBIDDEN_FIELDS
        is contract.APS_HANDOFF_DISPATCH_FORBIDDEN_FIELDS
    )


def test_handoff_contract_blocks_same_fields_as_legacy_logic() -> None:
    prepare_payload = {
        "session_id": "session-1",
        "download": True,
        "unexpected_field": True,
    }
    legacy_prepare_blocked = sorted(
        set(
            key
            for key in prepare_payload
            if key not in contract.HANDOFF_EXPORT_PREPARE_ALLOWED_FIELDS
        )
        | set(
            key
            for key in contract.HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS
            if key in prepare_payload
        )
    )
    assert contract.handoff_export_prepare_blocked_fields(prepare_payload) == legacy_prepare_blocked

    dispatch_payload = {
        "session_id": "session-1",
        "aps_handoff_target": "aps_evidence_bundle",
        "connector_dispatch": True,
        "unexpected_field": True,
    }
    legacy_dispatch_blocked = sorted(
        set(
            key
            for key in dispatch_payload
            if key not in contract.APS_HANDOFF_DISPATCH_ALLOWED_FIELDS
        )
        | set(
            key
            for key in contract.APS_HANDOFF_DISPATCH_FORBIDDEN_FIELDS
            if key in dispatch_payload
        )
    )
    assert contract.aps_handoff_dispatch_blocked_fields(dispatch_payload) == legacy_dispatch_blocked
