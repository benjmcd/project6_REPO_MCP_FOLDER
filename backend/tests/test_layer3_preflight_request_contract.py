from app.services.layer3_preflight_request_contract import (
    PREFLIGHT_MANUAL_CONSTRAINT_ALLOWED_FIELDS,
    PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS,
    manual_constraints_from_payload,
    preflight_manual_constraint_blocked_fields,
)
from app.services.layer3_state_action_contract import STATE_ACTION_DEFERRED_CAPABILITIES


def test_preflight_manual_constraints_preserve_known_open_shape() -> None:
    payload = {
        "manual_constraints": {
            "topics": ["decommissioning"],
            "source_classes": ("dataset_version", "aps_content_document"),
            "operator_note": "allowed as inert manual context",
        }
    }

    constraints = manual_constraints_from_payload(payload)

    assert constraints == payload["manual_constraints"]
    assert manual_constraints_from_payload({"manual_constraints": ["not", "a", "dict"]}) == {}
    assert PREFLIGHT_MANUAL_CONSTRAINT_ALLOWED_FIELDS == frozenset(
        {
            "topics",
            "source_classes",
            "date_bounds",
            "required_artifacts",
            "conflict",
            "conflicts",
        }
    )
    assert preflight_manual_constraint_blocked_fields(constraints) == []


def test_preflight_manual_constraints_block_deferred_capability_sentinels_recursively() -> None:
    blocked = preflight_manual_constraint_blocked_fields(
        {
            "source_classes": ["dataset_version"],
            "connector_destination_dispatch": True,
            "local_upload": {"path": "not-admitted"},
            "package_mutation_reconstruction": {"enabled": True},
            "date_bounds": {"provider_public_url": "https://example.invalid/export"},
            "topics": [
                {"rag_plan": {"enabled": True}},
                {"full_mockup_activation": "not-admitted"},
            ],
            "required_artifacts": [{"local_upload_or_directory_source_expansion": True}],
            "conflict": {"auth_security_hardening": "deferred"},
        }
    )

    assert {
        "auth_security_hardening",
        "connector_destination_dispatch",
        "full_mockup_activation",
        "local_upload",
        "local_upload_or_directory_source_expansion",
        "package_mutation_reconstruction",
        "provider_public_url",
        "rag_plan",
    } <= set(PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS)
    assert blocked == [
        "manual_constraints.conflict.auth_security_hardening",
        "manual_constraints.connector_destination_dispatch",
        "manual_constraints.date_bounds.provider_public_url",
        "manual_constraints.local_upload",
        "manual_constraints.package_mutation_reconstruction",
        "manual_constraints.required_artifacts[0].local_upload_or_directory_source_expansion",
        "manual_constraints.topics[0].rag_plan",
        "manual_constraints.topics[1].full_mockup_activation",
    ]


def test_preflight_manual_constraints_block_every_state_action_deferred_capability() -> None:
    deferred_capability_names = {
        str(capability["capability"]) for capability in STATE_ACTION_DEFERRED_CAPABILITIES
    }

    assert deferred_capability_names <= set(PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS)
