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
    L3ProviderPrivateSignedUrlAuditEvent,
    L3ProviderPrivateSignedUrlObjectAuthority,
    L3ProviderPrivateSignedUrlReceipt,
    L3ProviderPrivateSignedUrlRevocation,
)
from app.services.layer3_provider_private_signed_url_state import (
    INTERNAL_ARTIFACT_REF_PLACEHOLDER,
    PROVIDER_PRIVATE_SIGNED_URL_STATE_EXPIRED,
    PROVIDER_PRIVATE_SIGNED_URL_STATE_REVOKED,
    PROVIDER_PRIVATE_SIGNED_URL_STATE_USED,
    ProviderPrivateSignedUrlStateError,
    record_prepared_provider_private_signed_url_receipt,
    record_used_provider_private_signed_url_receipt,
    revoke_provider_private_signed_url_receipt,
)


NOW_EPOCH = 1_800_000_000
SOURCE_ARTIFACT_HASH = "a" * 64
SOURCE_ARTIFACT_SIZE_BYTES = 512
RAW_TOKEN = "provider-private-signed-url-sensitive-token"


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'layer3-provider-private-state.sqlite'}",
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
        first = record_prepared_provider_private_signed_url_receipt(
            db,
            request_id="prepare-1",
            client_request_id="client-request-provider-private-1",
            authority_basis=_authority_basis(),
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH,
            provider_private_signed_url_token=RAW_TOKEN,
        )
    finally:
        db.close()

    db = session_factory()
    try:
        second = record_prepared_provider_private_signed_url_receipt(
            db,
            request_id="prepare-2",
            client_request_id="client-request-provider-private-1",
            authority_basis=_authority_basis(),
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH + 1,
            provider_private_signed_url_token=RAW_TOKEN,
        )
    finally:
        db.close()

    assert first.provider_private_signed_url_receipt_id == second.provider_private_signed_url_receipt_id

    db = session_factory()
    try:
        authority = db.query(L3ProviderPrivateSignedUrlObjectAuthority).one()
        receipt = db.query(L3ProviderPrivateSignedUrlReceipt).one()
        audits = db.query(L3ProviderPrivateSignedUrlAuditEvent).filter_by(event_type="prepare").all()

        assert authority.authority_snapshot_json["source_artifact_ref"] == INTERNAL_ARTIFACT_REF_PLACEHOLDER
        assert authority.source_artifact_hash == SOURCE_ARTIFACT_HASH
        assert authority.source_artifact_size_bytes == SOURCE_ARTIFACT_SIZE_BYTES
        assert authority.provider_object_identity_hash
        assert receipt.provider_private_signed_url_token_hash != RAW_TOKEN
        assert receipt.provider_private_signed_url_token_prefix == receipt.provider_private_signed_url_token_hash[:16]
        serialized = json.dumps(
            {
                "authority_snapshot_json": authority.authority_snapshot_json,
                "prepare_audits": [audit.event_payload_json for audit in audits],
            },
            sort_keys=True,
        )
        assert RAW_TOKEN not in serialized
        assert "C:/operator/private/export.zip" not in serialized
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
        record_prepared_provider_private_signed_url_receipt(
            db,
            request_id="prepare-conflict-1",
            client_request_id="client-request-provider-private-conflict",
            authority_basis=_authority_basis(),
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH,
            provider_private_signed_url_token=RAW_TOKEN,
        )
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPrivateSignedUrlStateError) as conflict:
            record_prepared_provider_private_signed_url_receipt(
                db,
                request_id="prepare-conflict-2",
                client_request_id="client-request-provider-private-conflict",
                authority_basis=_authority_basis(source_artifact_size_bytes=SOURCE_ARTIFACT_SIZE_BYTES + 1),
                requested_ttl_seconds=300,
                now_epoch=NOW_EPOCH + 1,
                provider_private_signed_url_token=RAW_TOKEN,
            )
        assert conflict.value.error_code == "provider_private_signed_url_state_idempotency_conflict"
    finally:
        db.close()


def test_use_blocks_stale_session_and_artifact_authority(session_factory) -> None:
    db = session_factory()
    try:
        state = record_prepared_provider_private_signed_url_receipt(
            db,
            request_id="prepare-stale-1",
            client_request_id="client-request-provider-private-stale",
            authority_basis=_authority_basis(),
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH,
            provider_private_signed_url_token=RAW_TOKEN,
        )
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPrivateSignedUrlStateError) as stale:
            record_used_provider_private_signed_url_receipt(
                db,
                provider_private_signed_url_receipt_id=state.provider_private_signed_url_receipt_id,
                provider_private_signed_url_token=RAW_TOKEN,
                authority_basis=_authority_basis(session_id="wrong-session"),
                now_epoch=NOW_EPOCH + 5,
                request_id="use-stale-1",
            )
        assert stale.value.error_code == "provider_private_signed_url_state_authority_mismatch"
        assert "session_id" in stale.value.blocked_fields
    finally:
        db.close()

    db = session_factory()
    try:
        rejected = db.query(L3ProviderPrivateSignedUrlAuditEvent).filter_by(reason_code="authority_hash_mismatch").one()
        assert rejected.event_status == "rejected"
    finally:
        db.close()


def test_use_enforces_expiry_and_single_use_replay(session_factory) -> None:
    db = session_factory()
    try:
        state = record_prepared_provider_private_signed_url_receipt(
            db,
            request_id="prepare-expiry-1",
            client_request_id="client-request-provider-private-expiry",
            authority_basis=_authority_basis(),
            requested_ttl_seconds=10,
            now_epoch=NOW_EPOCH,
            provider_private_signed_url_token=RAW_TOKEN,
        )
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPrivateSignedUrlStateError) as expired:
            record_used_provider_private_signed_url_receipt(
                db,
                provider_private_signed_url_receipt_id=state.provider_private_signed_url_receipt_id,
                provider_private_signed_url_token=RAW_TOKEN,
                authority_basis=_authority_basis(),
                now_epoch=NOW_EPOCH + 10,
                request_id="use-expired-1",
            )
        assert expired.value.error_code == "provider_private_signed_url_state_expired"
    finally:
        db.close()

    db = session_factory()
    try:
        expired_receipt = db.query(L3ProviderPrivateSignedUrlReceipt).one()
        assert expired_receipt.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_EXPIRED
    finally:
        db.close()

    db = session_factory()
    try:
        active = record_prepared_provider_private_signed_url_receipt(
            db,
            request_id="prepare-replay-1",
            client_request_id="client-request-provider-private-replay",
            authority_basis=_authority_basis(external_export_download_record_ref="external-export-download:replay"),
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH,
            provider_private_signed_url_token="provider-private-signed-url-replay-token",
        )
    finally:
        db.close()

    db = session_factory()
    try:
        used = record_used_provider_private_signed_url_receipt(
            db,
            provider_private_signed_url_receipt_id=active.provider_private_signed_url_receipt_id,
            provider_private_signed_url_token="provider-private-signed-url-replay-token",
            authority_basis=_authority_basis(external_export_download_record_ref="external-export-download:replay"),
            now_epoch=NOW_EPOCH + 30,
            request_id="use-replay-1",
        )
        assert used.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_USED
        assert used.provider_private_signed_url_use_count == 1
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPrivateSignedUrlStateError) as replay:
            record_used_provider_private_signed_url_receipt(
                db,
                provider_private_signed_url_receipt_id=active.provider_private_signed_url_receipt_id,
                provider_private_signed_url_token="provider-private-signed-url-replay-token",
                authority_basis=_authority_basis(external_export_download_record_ref="external-export-download:replay"),
                now_epoch=NOW_EPOCH + 31,
                request_id="use-replay-2",
            )
        assert replay.value.error_code == "provider_private_signed_url_state_replay_denied"
    finally:
        db.close()


def test_revoke_blocks_future_use_and_redacts_audit(session_factory) -> None:
    db = session_factory()
    try:
        state = record_prepared_provider_private_signed_url_receipt(
            db,
            request_id="prepare-revoke-1",
            client_request_id="client-request-provider-private-revoke",
            authority_basis=_authority_basis(external_export_download_record_ref="external-export-download:revoke"),
            requested_ttl_seconds=300,
            now_epoch=NOW_EPOCH,
            provider_private_signed_url_token="provider-private-signed-url-revoke-token",
        )
    finally:
        db.close()

    db = session_factory()
    try:
        revoked = revoke_provider_private_signed_url_receipt(
            db,
            provider_private_signed_url_receipt_id=state.provider_private_signed_url_receipt_id,
            idempotency_key="revoke-key-1",
            revoked_by="operator@example.test",
            revocation_reason="operator removed downstream access",
            now_epoch=NOW_EPOCH + 20,
            request_id="revoke-1",
        )
        assert revoked.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_REVOKED
        assert revoked.provider_private_signed_url_revoked is True
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPrivateSignedUrlStateError) as revoked_error:
            record_used_provider_private_signed_url_receipt(
                db,
                provider_private_signed_url_receipt_id=state.provider_private_signed_url_receipt_id,
                provider_private_signed_url_token="provider-private-signed-url-revoke-token",
                authority_basis=_authority_basis(external_export_download_record_ref="external-export-download:revoke"),
                now_epoch=NOW_EPOCH + 21,
                request_id="use-revoked-1",
            )
        assert revoked_error.value.error_code == "provider_private_signed_url_state_revoked"
    finally:
        db.close()

    db = session_factory()
    try:
        revocation = db.query(L3ProviderPrivateSignedUrlRevocation).one()
        revoke_audit = db.query(L3ProviderPrivateSignedUrlAuditEvent).filter_by(event_type="revoke").one()
        serialized = json.dumps(
            {
                "revocation_payload_json": revocation.revocation_payload_json,
                "audit_payload_json": revoke_audit.event_payload_json,
            },
            sort_keys=True,
        )
        assert "operator removed downstream access" not in serialized
        assert revocation.revocation_reason_hash
        assert revoke_audit.reason_code == "revoked_by_operator"
    finally:
        db.close()


def _authority_basis(
    *,
    session_id: str = "session-provider-private",
    source_artifact_size_bytes: int = SOURCE_ARTIFACT_SIZE_BYTES,
    external_export_download_record_ref: str = "external-export-download:prepared",
) -> dict[str, object]:
    return {
        "session_id": session_id,
        "reconciliation_record_id": "reconciliation-provider-private",
        "source_artifact_ref": "C:/operator/private/export.zip",
        "source_artifact_hash": SOURCE_ARTIFACT_HASH,
        "source_artifact_size_bytes": source_artifact_size_bytes,
        "external_export_download_record_ref": external_export_download_record_ref,
        "export_download_descriptor_ref": "external-export-download-descriptor:bundle",
    }
