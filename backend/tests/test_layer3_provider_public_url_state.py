from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models.models import (
    L3ProviderPublicUrlAuditEvent,
    L3ProviderPublicUrlObjectAuthority,
    L3ProviderPublicUrlReceipt,
    L3ProviderPublicUrlRevocation,
)
from app.services.layer3_provider_public_url_fake_provider import ProviderPublicUrlFakeReceipt
from app.services.layer3_provider_public_url_state import (
    PROVIDER_PUBLIC_URL_REDACTED_MARKER,
    PROVIDER_PUBLIC_URL_STATE_EXPIRED,
    PROVIDER_PUBLIC_URL_STATE_REVOKED,
    ProviderPublicUrlStateError,
    record_prepared_provider_public_url_receipt,
    revoke_provider_public_url_receipt,
)


NOW_EPOCH = 1_800_000_000
SOURCE_ARTIFACT_HASH = "c" * 64
SOURCE_ARTIFACT_SIZE_BYTES = 1024
PUBLIC_URL = "https://provider.example.invalid/public/source-intake-bundle.zip?token=secret-public-token"
RECIPIENT_SCOPE = "external-recipient:provider-public-pytest"


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'layer3-provider-public-state.sqlite'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    try:
        yield SessionLocal
    finally:
        engine.dispose()


def test_prepare_persists_redacted_authority_and_idempotent_receipt_state(session_factory) -> None:
    db = session_factory()
    try:
        first = record_prepared_provider_public_url_receipt(
            db,
            request_id="prepare-public-1",
            client_request_id="client-request-provider-public-1",
            authority_basis=_authority_basis(),
            recipient_scope=RECIPIENT_SCOPE,
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH,
            provider_public_url=PUBLIC_URL,
        )
    finally:
        db.close()

    db = session_factory()
    try:
        second = record_prepared_provider_public_url_receipt(
            db,
            request_id="prepare-public-2",
            client_request_id="client-request-provider-public-1",
            authority_basis=_authority_basis(),
            recipient_scope=RECIPIENT_SCOPE,
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH + 1,
            provider_public_url=PUBLIC_URL,
        )
    finally:
        db.close()

    assert first.provider_public_url_receipt_id == second.provider_public_url_receipt_id
    assert first.provider_public_url_receipt_id.startswith("ppub_")
    assert len(first.provider_public_url_receipt_id) == 36
    response = first.response_fields()
    assert response["provider_public_url"] == PROVIDER_PUBLIC_URL_REDACTED_MARKER
    assert response["public_url_enabled"] is False
    assert response["raw_public_url_exposed"] is False

    db = session_factory()
    try:
        authority = db.query(L3ProviderPublicUrlObjectAuthority).one()
        receipt = db.query(L3ProviderPublicUrlReceipt).one()
        audits = db.query(L3ProviderPublicUrlAuditEvent).filter_by(event_type="prepare").all()
        assert authority.authority_snapshot_json["provider_public_url"] == PROVIDER_PUBLIC_URL_REDACTED_MARKER
        assert authority.provider_private_signed_url_receipt_id == "ppsu_source_intake_private_receipt"
        assert receipt.provider_public_url_hash != PUBLIC_URL
        assert receipt.provider_public_url_prefix == receipt.provider_public_url_hash[:16]
        serialized = json.dumps(
            {
                "authority_snapshot_json": authority.authority_snapshot_json,
                "receipt": receipt.__dict__,
                "prepare_audits": [audit.event_payload_json for audit in audits],
            },
            sort_keys=True,
            default=str,
        )
        assert PUBLIC_URL not in serialized
        assert "secret-public-token" not in serialized
        assert len(audits) == 2
        assert {audit.reason_code for audit in audits} == {
            "generated_after_authority_validation",
            "idempotent_prepare_reused",
        }
    finally:
        db.close()


def test_prepare_conflict_rejects_changed_authority_for_same_client_request_id(session_factory) -> None:
    db = session_factory()
    try:
        record_prepared_provider_public_url_receipt(
            db,
            request_id="prepare-public-conflict-1",
            client_request_id="client-request-provider-public-conflict",
            authority_basis=_authority_basis(),
            recipient_scope=RECIPIENT_SCOPE,
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH,
            provider_public_url=PUBLIC_URL,
        )
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPublicUrlStateError) as conflict:
            record_prepared_provider_public_url_receipt(
                db,
                request_id="prepare-public-conflict-2",
                client_request_id="client-request-provider-public-conflict",
                authority_basis=_authority_basis(source_artifact_size_bytes=SOURCE_ARTIFACT_SIZE_BYTES + 1),
                recipient_scope=RECIPIENT_SCOPE,
                requested_ttl_seconds=300,
                now_epoch=NOW_EPOCH + 1,
                provider_public_url=PUBLIC_URL,
            )
        assert conflict.value.error_code == "provider_public_url_state_idempotency_conflict"
    finally:
        db.close()


def test_prepare_reuse_after_expiry_marks_existing_receipt_expired(session_factory) -> None:
    db = session_factory()
    try:
        state = record_prepared_provider_public_url_receipt(
            db,
            request_id="prepare-public-expiry-1",
            client_request_id="client-request-provider-public-expiry",
            authority_basis=_authority_basis(),
            recipient_scope=RECIPIENT_SCOPE,
            requested_ttl_seconds=1,
            now_epoch=NOW_EPOCH,
            provider_public_url=PUBLIC_URL,
        )
    finally:
        db.close()

    db = session_factory()
    try:
        expired = record_prepared_provider_public_url_receipt(
            db,
            request_id="prepare-public-expiry-2",
            client_request_id="client-request-provider-public-expiry",
            authority_basis=_authority_basis(),
            recipient_scope=RECIPIENT_SCOPE,
            requested_ttl_seconds=1,
            now_epoch=NOW_EPOCH + 2,
            provider_public_url=PUBLIC_URL,
        )
        receipt = db.query(L3ProviderPublicUrlReceipt).filter_by(
            provider_public_url_receipt_id=state.provider_public_url_receipt_id
        ).one()
        assert expired.provider_public_url_receipt_id == state.provider_public_url_receipt_id
        assert expired.provider_public_url_state == PROVIDER_PUBLIC_URL_STATE_EXPIRED
        assert receipt.provider_public_url_state == PROVIDER_PUBLIC_URL_STATE_EXPIRED
    finally:
        db.close()


def test_prepare_enforces_ttl_and_stale_authority_on_revoke(session_factory) -> None:
    db = session_factory()
    try:
        with pytest.raises(ProviderPublicUrlStateError) as ttl:
            record_prepared_provider_public_url_receipt(
                db,
                request_id="prepare-public-ttl",
                client_request_id="client-request-provider-public-ttl",
                authority_basis=_authority_basis(),
                recipient_scope=RECIPIENT_SCOPE,
                requested_ttl_seconds=901,
                now_epoch=NOW_EPOCH,
                provider_public_url=PUBLIC_URL,
            )
        assert ttl.value.error_code == "provider_public_url_state_ttl_not_admitted"
    finally:
        db.close()

    db = session_factory()
    try:
        state = record_prepared_provider_public_url_receipt(
            db,
            request_id="prepare-public-stale",
            client_request_id="client-request-provider-public-stale",
            authority_basis=_authority_basis(),
            recipient_scope=RECIPIENT_SCOPE,
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH,
            provider_public_url=PUBLIC_URL,
        )
    finally:
        db.close()

    stale_authority = _authority_basis()
    stale_authority["source_artifact_hash"] = "d" * 64
    db = session_factory()
    try:
        with pytest.raises(ProviderPublicUrlStateError) as stale:
            revoke_provider_public_url_receipt(
                db,
                provider_public_url_receipt_id=state.provider_public_url_receipt_id,
                idempotency_key="revoke-public-stale",
                revoked_by="pytest",
                revocation_reason="operator requested revoke after stale authority",
                now_epoch=NOW_EPOCH + 5,
                authority_basis=stale_authority,
                request_id="revoke-public-stale",
            )
        assert stale.value.error_code == "provider_public_url_state_authority_mismatch"
    finally:
        db.close()


def test_revoke_blocks_future_public_url_state_and_redacts_audit(session_factory) -> None:
    db = session_factory()
    try:
        state = record_prepared_provider_public_url_receipt(
            db,
            request_id="prepare-public-revoke",
            client_request_id="client-request-provider-public-revoke",
            authority_basis=_authority_basis(external_export_download_record_ref="external-export-download:public-revoke"),
            recipient_scope=RECIPIENT_SCOPE,
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH,
            provider_public_url=PUBLIC_URL,
        )
    finally:
        db.close()

    db = session_factory()
    try:
        revoked = revoke_provider_public_url_receipt(
            db,
            provider_public_url_receipt_id=state.provider_public_url_receipt_id,
            idempotency_key="revoke-public-1",
            revoked_by="operator@example.test",
            revocation_reason="operator removed public URL access",
            now_epoch=NOW_EPOCH + 20,
            request_id="revoke-public-1",
        )
        assert revoked.provider_public_url_state == PROVIDER_PUBLIC_URL_STATE_REVOKED
        assert revoked.provider_public_url_revoked is True
    finally:
        db.close()

    db = session_factory()
    try:
        revocation = db.query(L3ProviderPublicUrlRevocation).one()
        receipt = db.query(L3ProviderPublicUrlReceipt).one()
        revoke_audit = db.query(L3ProviderPublicUrlAuditEvent).filter_by(event_type="revoke").one()
        assert receipt.provider_public_url_state == PROVIDER_PUBLIC_URL_STATE_REVOKED
        serialized = json.dumps(
            {
                "revocation_payload_json": revocation.revocation_payload_json,
                "audit_payload_json": revoke_audit.event_payload_json,
                "receipt": receipt.__dict__,
            },
            sort_keys=True,
            default=str,
        )
        assert PUBLIC_URL not in serialized
        assert "operator removed public URL access" not in serialized
        assert revocation.revocation_reason_hash
        assert revoke_audit.reason_code == "revoked_by_operator"
    finally:
        db.close()


def test_fake_provider_response_never_exposes_raw_public_url() -> None:
    fake = ProviderPublicUrlFakeReceipt(
        provider_public_url_receipt_id="ppub_fake_provider_public_url",
        provider_public_url_state="provider_public_url_prepared",
        provider_public_url_prefix="abc123",
        provider_public_url_expires_at_epoch=NOW_EPOCH + 300,
    )
    response = fake.to_prepare_response()
    assert response["provider_public_url"] == PROVIDER_PUBLIC_URL_REDACTED_MARKER
    assert response["public_url_enabled"] is False
    assert response["raw_public_url_exposed"] is False
    assert "raw_public_url" not in response
    assert "provider_secret" not in response


def _authority_basis(
    *,
    source_artifact_size_bytes: int = SOURCE_ARTIFACT_SIZE_BYTES,
    external_export_download_record_ref: str = "external-export-download:provider-public-prepared",
) -> dict[str, object]:
    return {
        "session_id": "session-provider-public",
        "provider_private_signed_url_receipt_id": "ppsu_source_intake_private_receipt",
        "external_export_download_record_ref": external_export_download_record_ref,
        "export_download_descriptor_ref": "external-export-download-descriptor:public-bundle",
        "source_artifact_hash": SOURCE_ARTIFACT_HASH,
        "source_artifact_size_bytes": source_artifact_size_bytes,
    }
