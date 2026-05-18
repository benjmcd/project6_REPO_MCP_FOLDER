from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import L3ProviderPublicUrlObjectAuthority, L3ProviderPublicUrlReceipt
from app.services.layer3_provider_public_url_state import (
    PROVIDER_PUBLIC_URL_REDACTED_MARKER,
    PROVIDER_PUBLIC_URL_REPLAY_POLICY_STATUS_ONLY,
    PROVIDER_PUBLIC_URL_STATE_EXPIRED,
    PROVIDER_PUBLIC_URL_STATE_PREPARED,
    PROVIDER_PUBLIC_URL_STATE_REVOKED,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_workbench_error import Layer3WorkbenchError


PROVIDER_PUBLIC_URL_DELIVERY_USE_SCHEMA_ID = "layer3.provider_public_url.delivery_use.v1"
PROVIDER_PUBLIC_URL_DELIVERY_USE_MODE = "fake_provider_redacted_use_decision"
PROVIDER_PUBLIC_URL_DELIVERY_USE_OPERATOR_DECISION = "use_provider_public_url_redacted_fake_provider"
PROVIDER_PUBLIC_URL_RECEIPT_ID_PREFIX = "ppub_"

PROVIDER_PUBLIC_URL_DELIVERY_USE_ALLOWED_FIELDS = frozenset(
    {
        "client_request_id",
        "provider_public_url_receipt_id",
        "expected_authority_hash",
        "expected_source_artifact_hash",
        "expected_source_artifact_size_bytes",
        "delivery_use_mode",
        "operator_decision",
    }
)
PROVIDER_PUBLIC_URL_DELIVERY_USE_REQUIRED_FIELDS = frozenset(
    {
        "client_request_id",
        "provider_public_url_receipt_id",
        "delivery_use_mode",
        "operator_decision",
    }
)


def _text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return "" if value is None else str(value).strip()


def _blocked_fields(payload: dict[str, Any]) -> list[str]:
    return sorted(field for field in payload if field not in PROVIDER_PUBLIC_URL_DELIVERY_USE_ALLOWED_FIELDS)


def _missing_fields(payload: dict[str, Any]) -> list[str]:
    return sorted(field for field in PROVIDER_PUBLIC_URL_DELIVERY_USE_REQUIRED_FIELDS if not _text(payload, field))


def _datetime_epoch(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


def _require_fixed_values(payload: dict[str, Any]) -> None:
    mismatches = []
    if _text(payload, "delivery_use_mode") != PROVIDER_PUBLIC_URL_DELIVERY_USE_MODE:
        mismatches.append("delivery_use_mode")
    if _text(payload, "operator_decision") != PROVIDER_PUBLIC_URL_DELIVERY_USE_OPERATOR_DECISION:
        mismatches.append("operator_decision")
    if mismatches:
        raise Layer3WorkbenchError(
            "provider_public_url_delivery_use_fixed_value_mismatch",
            "Provider-public delivery/use request contains non-admitted fixed-value fields.",
            status="invalid",
            blocked_fields=mismatches,
            next_allowed_actions=["submit_provider_public_url_delivery_use_fixed_values"],
        )


def _require_receipt_id(provider_public_url_receipt_id: str) -> None:
    if (
        not provider_public_url_receipt_id.startswith(PROVIDER_PUBLIC_URL_RECEIPT_ID_PREFIX)
        or len(provider_public_url_receipt_id) != 36
    ):
        raise Layer3WorkbenchError(
            "provider_public_url_delivery_use_receipt_id_invalid",
            "provider_public_url_receipt_id must be an admitted provider-public receipt id.",
            status="invalid",
            blocked_fields=["provider_public_url_receipt_id"],
            next_allowed_actions=["submit_recorded_provider_public_url_receipt_id"],
        )


def _expected_size(payload: dict[str, Any]) -> int | None:
    if "expected_source_artifact_size_bytes" not in payload:
        return None
    try:
        return int(payload["expected_source_artifact_size_bytes"])
    except (TypeError, ValueError) as exc:
        raise Layer3WorkbenchError(
            "provider_public_url_delivery_use_expected_size_invalid",
            "expected_source_artifact_size_bytes must be an integer when provided.",
            status="invalid",
            blocked_fields=["expected_source_artifact_size_bytes"],
            next_allowed_actions=["submit_recorded_provider_public_url_authority_expectations"],
        ) from exc


def _require_expected_authority(
    payload: dict[str, Any],
    *,
    receipt: L3ProviderPublicUrlReceipt,
    authority: L3ProviderPublicUrlObjectAuthority,
) -> None:
    expected_authority_hash = _text(payload, "expected_authority_hash")
    if expected_authority_hash and expected_authority_hash != receipt.authority_hash:
        raise Layer3WorkbenchError(
            "provider_public_url_delivery_use_authority_hash_mismatch",
            "Expected authority hash does not match the provider-public URL receipt authority.",
            status="conflict",
            blocked_fields=["expected_authority_hash"],
            next_allowed_actions=["refresh_provider_public_url_status"],
        )
    expected_hash = _text(payload, "expected_source_artifact_hash").lower()
    if expected_hash and expected_hash != authority.source_artifact_hash:
        raise Layer3WorkbenchError(
            "provider_public_url_delivery_use_source_artifact_hash_mismatch",
            "Expected source artifact hash does not match the provider-public URL authority.",
            status="conflict",
            blocked_fields=["expected_source_artifact_hash"],
            next_allowed_actions=["refresh_provider_public_url_status"],
        )
    expected_size = _expected_size(payload)
    if expected_size is not None and expected_size != authority.source_artifact_size_bytes:
        raise Layer3WorkbenchError(
            "provider_public_url_delivery_use_source_artifact_size_mismatch",
            "Expected source artifact size does not match the provider-public URL authority.",
            status="conflict",
            blocked_fields=["expected_source_artifact_size_bytes"],
            next_allowed_actions=["refresh_provider_public_url_status"],
        )


def _state_at(receipt: L3ProviderPublicUrlReceipt, *, now_epoch: int) -> str:
    if receipt.provider_public_url_state == PROVIDER_PUBLIC_URL_STATE_PREPARED and now_epoch >= _datetime_epoch(
        receipt.provider_public_url_expires_at
    ):
        return PROVIDER_PUBLIC_URL_STATE_EXPIRED
    return receipt.provider_public_url_state


def _decision_for_state(state: str) -> tuple[str, str | None, list[str]]:
    if state == PROVIDER_PUBLIC_URL_STATE_PREPARED:
        return "allowed", None, ["inspect_provider_public_url_status", "revoke_provider_public_url"]
    if state == PROVIDER_PUBLIC_URL_STATE_REVOKED:
        return "denied", "provider_public_url_revoked", ["inspect_provider_public_url_status"]
    if state == PROVIDER_PUBLIC_URL_STATE_EXPIRED:
        return "denied", "provider_public_url_expired", ["prepare_new_provider_public_url"]
    return "denied", "provider_public_url_state_not_usable", ["inspect_provider_public_url_status"]


def provider_public_url_delivery_use(
    db: Session,
    payload: dict[str, Any],
    *,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    blocked = _blocked_fields(payload)
    if blocked:
        raise Layer3WorkbenchError(
            "provider_public_url_delivery_use_scope_not_admitted",
            "Provider-public delivery/use includes non-admitted fields.",
            status="invalid",
            blocked_fields=blocked,
            next_allowed_actions=["submit_bounded_provider_public_url_delivery_use_request"],
        )
    missing = _missing_fields(payload)
    if missing:
        raise Layer3WorkbenchError(
            "missing_provider_public_url_delivery_use_fields",
            f"Provider-public delivery/use request is missing required fields: {', '.join(missing)}.",
            status="invalid",
            blocked_fields=missing,
            next_allowed_actions=["submit_complete_provider_public_url_delivery_use_request"],
        )
    _require_fixed_values(payload)
    receipt_id = _text(payload, "provider_public_url_receipt_id")
    _require_receipt_id(receipt_id)
    effective_now = int(time.time() if now_epoch is None else now_epoch)

    receipt = db.get(L3ProviderPublicUrlReceipt, receipt_id)
    if receipt is None:
        raise Layer3WorkbenchError(
            "provider_public_url_delivery_use_receipt_not_found",
            "Provider-public URL receipt was not found.",
            status="not_found",
            http_status=404,
            blocked_fields=["provider_public_url_receipt_id"],
            next_allowed_actions=["prepare_provider_public_url"],
        )
    authority = db.get(L3ProviderPublicUrlObjectAuthority, receipt.provider_public_url_object_authority_id)
    if authority is None:
        raise Layer3WorkbenchError(
            "provider_public_url_delivery_use_authority_not_found",
            "Provider-public URL authority row was not found.",
            status="conflict",
            blocked_fields=["provider_public_url_receipt_id"],
            next_allowed_actions=["prepare_provider_public_url"],
        )
    _require_expected_authority(payload, receipt=receipt, authority=authority)
    state = _state_at(receipt, now_epoch=effective_now)
    decision, denied_reason, next_allowed_actions = _decision_for_state(state)
    return {
        **base_response(
            PROVIDER_PUBLIC_URL_DELIVERY_USE_SCHEMA_ID,
            request_id=_text(payload, "client_request_id"),
            status="ok" if decision == "allowed" else "denied",
        ),
        "provider_public_url_receipt_id": receipt.provider_public_url_receipt_id,
        "provider_public_url_object_authority_id": receipt.provider_public_url_object_authority_id,
        "provider_public_url_state": state,
        "delivery_use_mode": PROVIDER_PUBLIC_URL_DELIVERY_USE_MODE,
        "delivery_use_decision": decision,
        "delivery_use_denied_reason": denied_reason,
        "provider_public_url_redacted": PROVIDER_PUBLIC_URL_REDACTED_MARKER,
        "provider_public_url_replay_policy": PROVIDER_PUBLIC_URL_REPLAY_POLICY_STATUS_ONLY,
        "authority_hash": receipt.authority_hash,
        "source_artifact_hash": authority.source_artifact_hash,
        "source_artifact_size_bytes": authority.source_artifact_size_bytes,
        "raw_public_url_exposed": False,
        "public_url_enabled": False,
        "provider_network_enabled": False,
        "provider_object_write_enabled": False,
        "public_redirect_enabled": False,
        "byte_streaming_enabled": False,
        "durable_use_row_created": False,
        "audit_row_created": False,
        "provider_credentials_enabled": False,
        "connector_dispatch_enabled": False,
        "package_mutation_enabled": False,
        "source_expansion_enabled": False,
        "rag_vector_indexing_enabled": False,
        "frontend_durable_authority_enabled": False,
        "next_allowed_actions": next_allowed_actions,
    }
