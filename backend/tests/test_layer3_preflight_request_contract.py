from app.services.layer3_preflight_request_contract import (
    PREFLIGHT_MANUAL_CONSTRAINT_ALLOWED_FIELDS,
    PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS,
    manual_constraints_from_payload,
    preflight_manual_constraint_blocked_fields,
)


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
            "local_upload": {"path": "not-admitted"},
            "date_bounds": {"provider_public_url": "https://example.invalid/export"},
            "topics": [{"rag_plan": {"enabled": True}}],
        }
    )

    assert {"local_upload", "provider_public_url", "rag_plan"} <= set(
        PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS
    )
    assert blocked == [
        "manual_constraints.date_bounds.provider_public_url",
        "manual_constraints.local_upload",
        "manual_constraints.topics[0].rag_plan",
    ]
