from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db
from app.db.session import Base
from app.models.models import (
    L3ProviderPublicUrlAuditEvent,
    L3ProviderPublicUrlObjectAuthority,
    L3ProviderPublicUrlReceipt,
    L3ProviderPublicUrlRevocation,
)
from app.services.layer3_provider_public_url_delivery_use import (
    PROVIDER_PUBLIC_URL_DELIVERY_USE_MODE,
    PROVIDER_PUBLIC_URL_DELIVERY_USE_OPERATOR_DECISION,
    PROVIDER_PUBLIC_URL_DELIVERY_USE_SCHEMA_ID,
    provider_public_url_delivery_use,
)
from app.services.layer3_provider_public_url_state import (
    PROVIDER_PUBLIC_URL_REDACTED_MARKER,
    ProviderPublicUrlStateError,
    record_prepared_provider_public_url_receipt,
    revoke_provider_public_url_receipt,
)
from app.services.layer3_workbench_error import Layer3WorkbenchError
from main import app


NOW_EPOCH = 1_800_000_000
SOURCE_ARTIFACT_HASH = "e" * 64
SOURCE_ARTIFACT_SIZE_BYTES = 4096
RAW_PROVIDER_PUBLIC_REFERENCE = "provider-public-fixture-reference"


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'layer3-provider-public-use.sqlite'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    try:
        yield SessionLocal
    finally:
        engine.dispose()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_provider_public_delivery_use_allows_prepared_receipt_without_writes_or_raw_url(session_factory) -> None:
    state = _prepare_receipt(session_factory)
    before_counts = _state_counts(session_factory)

    db = session_factory()
    try:
        receipt = db.get(L3ProviderPublicUrlReceipt, state.provider_public_url_receipt_id)
        assert receipt is not None
        response = provider_public_url_delivery_use(
            db,
            _use_payload(
                provider_public_url_receipt_id=state.provider_public_url_receipt_id,
                expected_authority_hash=receipt.authority_hash,
            ),
            now_epoch=NOW_EPOCH + 10,
        )
    finally:
        db.close()

    assert response["schema_id"] == PROVIDER_PUBLIC_URL_DELIVERY_USE_SCHEMA_ID
    assert response["delivery_use_decision"] == "allowed"
    assert response["delivery_use_denied_reason"] is None
    assert response["provider_public_url_redacted"] == PROVIDER_PUBLIC_URL_REDACTED_MARKER
    assert response["raw_public_url_exposed"] is False
    assert response["public_url_enabled"] is False
    assert response["provider_network_enabled"] is False
    assert response["provider_object_write_enabled"] is False
    assert response["public_redirect_enabled"] is False
    assert response["byte_streaming_enabled"] is False
    assert response["durable_use_row_created"] is False
    assert response["audit_row_created"] is False
    assert response["connector_dispatch_enabled"] is False
    assert response["package_mutation_enabled"] is False
    assert response["source_expansion_enabled"] is False
    serialized = json.dumps(response, sort_keys=True)
    assert RAW_PROVIDER_PUBLIC_REFERENCE not in serialized
    assert "provider_public_url" not in response
    assert _state_counts(session_factory) == before_counts


@pytest.mark.parametrize(
    ("requested_ttl_seconds", "now_epoch", "expected_decision", "expected_reason"),
    [
        (1, NOW_EPOCH + 2, "denied", "provider_public_url_expired"),
        (300, NOW_EPOCH + 10, "denied", "provider_public_url_revoked"),
    ],
)
def test_provider_public_delivery_use_denies_expired_or_revoked_receipts(
    session_factory,
    requested_ttl_seconds: int,
    now_epoch: int,
    expected_decision: str,
    expected_reason: str,
) -> None:
    state = _prepare_receipt(session_factory, requested_ttl_seconds=requested_ttl_seconds)
    if expected_reason == "provider_public_url_revoked":
        db = session_factory()
        try:
            revoke_provider_public_url_receipt(
                db,
                provider_public_url_receipt_id=state.provider_public_url_receipt_id,
                idempotency_key="provider-public-use-revoke",
                revoked_by="pytest",
                revocation_reason="operator revoked fake-provider public use",
                now_epoch=NOW_EPOCH + 5,
                request_id="provider-public-use-revoke",
            )
        finally:
            db.close()
    before_counts = _state_counts(session_factory)

    db = session_factory()
    try:
        response = provider_public_url_delivery_use(
            db,
            _use_payload(provider_public_url_receipt_id=state.provider_public_url_receipt_id),
            now_epoch=now_epoch,
        )
    finally:
        db.close()

    assert response["delivery_use_decision"] == expected_decision
    assert response["delivery_use_denied_reason"] == expected_reason
    assert response["raw_public_url_exposed"] is False
    assert response["public_url_enabled"] is False
    assert "provider_public_url" not in response
    assert _state_counts(session_factory) == before_counts


@pytest.mark.parametrize(
    ("payload_updates", "expected_error", "expected_field"),
    [
        (
            {"expected_authority_hash": "f" * 64},
            "provider_public_url_delivery_use_authority_hash_mismatch",
            "expected_authority_hash",
        ),
        (
            {"expected_source_artifact_hash": "a" * 64},
            "provider_public_url_delivery_use_source_artifact_hash_mismatch",
            "expected_source_artifact_hash",
        ),
        (
            {"expected_source_artifact_size_bytes": SOURCE_ARTIFACT_SIZE_BYTES + 1},
            "provider_public_url_delivery_use_source_artifact_size_mismatch",
            "expected_source_artifact_size_bytes",
        ),
        (
            {"public_url": "not-admitted-provider-public-reference"},
            "provider_public_url_delivery_use_scope_not_admitted",
            "public_url",
        ),
    ],
)
def test_provider_public_delivery_use_fails_closed_for_stale_or_forbidden_inputs(
    session_factory,
    payload_updates: dict[str, object],
    expected_error: str,
    expected_field: str,
) -> None:
    state = _prepare_receipt(session_factory)
    payload = _use_payload(provider_public_url_receipt_id=state.provider_public_url_receipt_id)
    payload.update(payload_updates)

    db = session_factory()
    try:
        with pytest.raises(Layer3WorkbenchError) as error:
            provider_public_url_delivery_use(db, payload, now_epoch=NOW_EPOCH + 1)
    finally:
        db.close()

    assert error.value.error_code == expected_error
    assert expected_field in error.value.blocked_fields


def test_provider_public_delivery_use_fails_closed_for_missing_receipt_or_authority(session_factory) -> None:
    db = session_factory()
    try:
        with pytest.raises(Layer3WorkbenchError) as missing_receipt:
            provider_public_url_delivery_use(
                db,
                _use_payload(provider_public_url_receipt_id="ppub_" + "0" * 31),
                now_epoch=NOW_EPOCH,
            )
        assert missing_receipt.value.error_code == "provider_public_url_delivery_use_receipt_not_found"
    finally:
        db.close()

    state = _prepare_receipt(session_factory)
    db = session_factory()
    try:
        receipt = db.get(L3ProviderPublicUrlReceipt, state.provider_public_url_receipt_id)
        assert receipt is not None
        receipt.provider_public_url_object_authority_id = "missing-provider-public-url-authority"
        db.commit()
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(Layer3WorkbenchError) as missing_authority:
            provider_public_url_delivery_use(
                db,
                _use_payload(provider_public_url_receipt_id=state.provider_public_url_receipt_id),
                now_epoch=NOW_EPOCH + 1,
            )
    finally:
        db.close()

    assert missing_authority.value.error_code == "provider_public_url_delivery_use_authority_not_found"


def test_provider_public_delivery_use_api_route_is_redacted_and_openapi_guarded(
    client: TestClient,
    session_factory,
) -> None:
    state = _prepare_receipt(session_factory)
    db = session_factory()
    try:
        receipt = db.get(L3ProviderPublicUrlReceipt, state.provider_public_url_receipt_id)
        authority = db.get(L3ProviderPublicUrlObjectAuthority, receipt.provider_public_url_object_authority_id)
        assert receipt is not None
        assert authority is not None
        expected_authority_hash = receipt.authority_hash
    finally:
        db.close()

    response = client.post(
        "/api/v1/layer3/handoff/export/download/provider-public-url/use",
        json=_use_payload(
            provider_public_url_receipt_id=state.provider_public_url_receipt_id,
            expected_authority_hash=expected_authority_hash,
            expected_source_artifact_hash=SOURCE_ARTIFACT_HASH,
            expected_source_artifact_size_bytes=SOURCE_ARTIFACT_SIZE_BYTES,
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema_id"] == PROVIDER_PUBLIC_URL_DELIVERY_USE_SCHEMA_ID
    assert body["delivery_use_decision"] == "allowed"
    assert body["provider_public_url_redacted"] == PROVIDER_PUBLIC_URL_REDACTED_MARKER
    assert body["raw_public_url_exposed"] is False
    assert body["public_url_enabled"] is False
    assert "provider_public_url" not in body
    assert RAW_PROVIDER_PUBLIC_REFERENCE not in json.dumps(body, sort_keys=True)

    forbidden = client.post(
        "/api/v1/layer3/handoff/export/download/provider-public-url/use",
        json={
            **_use_payload(provider_public_url_receipt_id=state.provider_public_url_receipt_id),
            "provider_secret": "not-admitted",
        },
    )
    assert forbidden.status_code == 400
    assert forbidden.json()["error_code"] == "provider_public_url_delivery_use_scope_not_admitted"
    assert forbidden.json()["blocked_fields"] == ["provider_secret"]

    spec = client.get("/openapi.json").json()
    request_schema = spec["paths"]["/api/v1/layer3/handoff/export/download/provider-public-url/use"]["post"][
        "requestBody"
    ]["content"]["application/json"]["schema"]
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {
        "client_request_id",
        "provider_public_url_receipt_id",
        "delivery_use_mode",
        "operator_decision",
    }
    assert request_schema["properties"]["provider_secret"]["not"] == {}
    assert request_schema["properties"]["public_url"]["not"] == {}


def _prepare_receipt(session_factory, *, requested_ttl_seconds: int = 300):
    db = session_factory()
    try:
        return record_prepared_provider_public_url_receipt(
            db,
            request_id=f"provider-public-use-prepare-{requested_ttl_seconds}",
            client_request_id=f"provider-public-use-client-{requested_ttl_seconds}",
            authority_basis=_authority_basis(),
            recipient_scope="external-recipient:provider-public-use",
            requested_ttl_seconds=requested_ttl_seconds,
            now_epoch=NOW_EPOCH,
            provider_public_url=RAW_PROVIDER_PUBLIC_REFERENCE,
        )
    except ProviderPublicUrlStateError:
        db.rollback()
        raise
    finally:
        db.close()


def _authority_basis() -> dict[str, object]:
    return {
        "session_id": "session-provider-public-use",
        "provider_private_signed_url_receipt_id": "ppsu_provider_public_use_private_receipt",
        "external_export_download_record_ref": "external-export-download:provider-public-use",
        "export_download_descriptor_ref": "external-export-download-descriptor:provider-public-use",
        "source_artifact_hash": SOURCE_ARTIFACT_HASH,
        "source_artifact_size_bytes": SOURCE_ARTIFACT_SIZE_BYTES,
    }


def _use_payload(
    *,
    provider_public_url_receipt_id: str,
    expected_authority_hash: str | None = None,
    expected_source_artifact_hash: str | None = None,
    expected_source_artifact_size_bytes: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "client_request_id": "provider-public-use-request",
        "provider_public_url_receipt_id": provider_public_url_receipt_id,
        "delivery_use_mode": PROVIDER_PUBLIC_URL_DELIVERY_USE_MODE,
        "operator_decision": PROVIDER_PUBLIC_URL_DELIVERY_USE_OPERATOR_DECISION,
    }
    if expected_authority_hash is not None:
        payload["expected_authority_hash"] = expected_authority_hash
    if expected_source_artifact_hash is not None:
        payload["expected_source_artifact_hash"] = expected_source_artifact_hash
    if expected_source_artifact_size_bytes is not None:
        payload["expected_source_artifact_size_bytes"] = expected_source_artifact_size_bytes
    return payload


def _state_counts(session_factory) -> dict[str, int]:
    db = session_factory()
    try:
        return {
            "authorities": db.query(L3ProviderPublicUrlObjectAuthority).count(),
            "receipts": db.query(L3ProviderPublicUrlReceipt).count(),
            "audits": db.query(L3ProviderPublicUrlAuditEvent).count(),
            "revocations": db.query(L3ProviderPublicUrlRevocation).count(),
        }
    finally:
        db.close()
