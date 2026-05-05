from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db.session import Base
from app.models.models import (
    L3SignedReferenceAuditEvent,
    L3SignedReferenceReceipt,
    L3SignedReferenceRevocation,
    L3SignedReferenceToken,
    uuid_str,
)
from app.services.layer3_signed_reference_state import (
    INTERNAL_ARTIFACT_REF_PLACEHOLDER,
    SIGNED_REFERENCE_TOKEN_STATE_EXPIRED,
    SIGNED_REFERENCE_TOKEN_STATE_READY,
    SIGNED_REFERENCE_TOKEN_STATE_REVOKED,
    SIGNED_REFERENCE_TOKEN_STATE_USED,
    SignedReferenceStateError,
    hash_signed_reference_token,
    record_generated_signed_reference,
    record_used_signed_reference,
)


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'layer3-signed-reference.sqlite'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    try:
        yield SessionLocal
    finally:
        engine.dispose()


def _token_body(*, expires_at_epoch: int | None = None) -> dict:
    return {
        "schema_id": "layer3.external_export_download_signed_reference.v1",
        "schema_version": "1",
        "expires_at_epoch": expires_at_epoch or int(time.time()) + 300,
    }


def _payload() -> dict:
    return {
        "session_id": "session-signed-reference",
        "reconciliation_record_id": "reconciliation-signed-reference",
    }


def _authority_basis(*, artifact_ref: str = "C:/operator/private/export.zip") -> dict:
    return {
        "session_id": "session-signed-reference",
        "reconciliation_record_id": "reconciliation-signed-reference",
        "source_artifact_ref": artifact_ref,
        "source_artifact_hash": "a" * 64,
        "source_artifact_size_bytes": 1024,
        "nested": {
            "source_artifact_ref": artifact_ref,
        },
    }


def _generate(SessionLocal, *, raw_token: str = "signed-reference-token", request_id: str = "generate-1"):
    db = SessionLocal()
    try:
        state = record_generated_signed_reference(
            db,
            raw_token=raw_token,
            token_body=_token_body(),
            request_id=request_id,
            payload=_payload(),
            authority_basis=_authority_basis(),
        )
        return state
    finally:
        db.close()


def test_record_generated_signed_reference_persists_sanitized_durable_state(session_factory) -> None:
    raw_token = "signed-reference-sensitive-token"
    state = _generate(session_factory, raw_token=raw_token)

    db = session_factory()
    try:
        token = db.query(L3SignedReferenceToken).one()
        receipt = db.query(L3SignedReferenceReceipt).filter_by(receipt_type="generated").one()
        audit = db.query(L3SignedReferenceAuditEvent).filter_by(event_type="generate").one()

        assert state.signed_reference_token_id == token.signed_reference_token_id
        assert token.token_hash == hash_signed_reference_token(raw_token)
        assert token.token_hash != raw_token
        assert token.token_prefix == token.token_hash[:16]
        assert token.state == SIGNED_REFERENCE_TOKEN_STATE_READY
        assert token.use_count == 0
        assert token.authority_snapshot_json["source_artifact_ref"] == INTERNAL_ARTIFACT_REF_PLACEHOLDER
        assert token.authority_snapshot_json["nested"]["source_artifact_ref"] == INTERNAL_ARTIFACT_REF_PLACEHOLDER
        assert receipt.receipt_payload_json["delivery_authority"]["source_artifact_ref"] == INTERNAL_ARTIFACT_REF_PLACEHOLDER
        assert raw_token not in str(token.authority_snapshot_json)
        assert audit.event_status == "accepted"
        assert audit.reason_code == "generated_after_delivery_authority_validation"
    finally:
        db.close()


def test_single_use_reference_records_one_delivery_and_rejects_replay(session_factory) -> None:
    raw_token = "signed-reference-single-use"
    _generate(session_factory, raw_token=raw_token)

    db = session_factory()
    try:
        first = record_used_signed_reference(
            db,
            raw_token=raw_token,
            token_body=_token_body(),
            request_id="use-1",
            authority_basis=_authority_basis(),
            now_epoch=int(time.time()),
        )
        assert first.signed_reference_use_count == 1
        assert first.signed_reference_revoked is False
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(SignedReferenceStateError) as replay:
            record_used_signed_reference(
                db,
                raw_token=raw_token,
                token_body=_token_body(),
                request_id="use-2",
                authority_basis=_authority_basis(),
                now_epoch=int(time.time()),
            )
        assert replay.value.error_code == "external_export_download_signed_reference_replay_denied"
    finally:
        db.close()

    db = session_factory()
    try:
        token = db.query(L3SignedReferenceToken).one()
        used_receipts = db.query(L3SignedReferenceReceipt).filter_by(receipt_type="used").all()
        rejected_audits = db.query(L3SignedReferenceAuditEvent).filter_by(
            event_status="rejected",
            reason_code="single_use_replay_denied",
        ).all()
        assert token.state == SIGNED_REFERENCE_TOKEN_STATE_USED
        assert token.use_count == 1
        assert len(used_receipts) == 1
        assert len(rejected_audits) == 1
    finally:
        db.close()


def test_revoked_reference_fails_closed_and_records_rejected_audit(session_factory) -> None:
    raw_token = "signed-reference-revoked"
    state = _generate(session_factory, raw_token=raw_token)

    db = session_factory()
    try:
        db.add(
            L3SignedReferenceRevocation(
                signed_reference_revocation_id=uuid_str(),
                signed_reference_token_id=state.signed_reference_token_id,
                idempotency_key="revoke-1",
                revoked_by="test",
                revocation_reason="operator_revoked",
                revocation_payload_json={"source": "test"},
            )
        )
        db.commit()
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(SignedReferenceStateError) as revoked:
            record_used_signed_reference(
                db,
                raw_token=raw_token,
                token_body=_token_body(),
                request_id="use-revoked",
                authority_basis=_authority_basis(),
                now_epoch=int(time.time()),
            )
        assert revoked.value.error_code == "external_export_download_signed_reference_revoked"
    finally:
        db.close()

    db = session_factory()
    try:
        token = db.query(L3SignedReferenceToken).one()
        rejected = db.query(L3SignedReferenceAuditEvent).filter_by(
            event_status="rejected",
            reason_code="token_revoked",
        ).one()
        assert token.state == SIGNED_REFERENCE_TOKEN_STATE_REVOKED
        assert rejected.signed_reference_token_id == state.signed_reference_token_id
    finally:
        db.close()


def test_expired_reference_fails_closed_and_marks_token_expired(session_factory) -> None:
    raw_token = "signed-reference-expired"
    expires_at_epoch = int(time.time()) - 1
    db = session_factory()
    try:
        record_generated_signed_reference(
            db,
            raw_token=raw_token,
            token_body=_token_body(expires_at_epoch=expires_at_epoch),
            request_id="generate-expired",
            payload=_payload(),
            authority_basis=_authority_basis(),
        )
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(SignedReferenceStateError) as expired:
            record_used_signed_reference(
                db,
                raw_token=raw_token,
                token_body=_token_body(expires_at_epoch=expires_at_epoch),
                request_id="use-expired",
                authority_basis=_authority_basis(),
                now_epoch=int(time.time()),
            )
        assert expired.value.error_code == "external_export_download_signed_reference_expired"
    finally:
        db.close()

    db = session_factory()
    try:
        token = db.query(L3SignedReferenceToken).one()
        audit = db.query(L3SignedReferenceAuditEvent).filter_by(
            event_status="rejected",
            reason_code="token_expired",
        ).one()
        assert token.state == SIGNED_REFERENCE_TOKEN_STATE_EXPIRED
        assert audit.signed_reference_token_id == token.signed_reference_token_id
    finally:
        db.close()


def test_concurrent_single_use_reference_does_not_double_deliver(session_factory) -> None:
    raw_token = "signed-reference-concurrent-single-use"
    _generate(session_factory, raw_token=raw_token)

    def use_reference(request_id: str) -> tuple[str, str | int]:
        db = session_factory()
        try:
            state = record_used_signed_reference(
                db,
                raw_token=raw_token,
                token_body=_token_body(),
                request_id=request_id,
                authority_basis=_authority_basis(),
                now_epoch=int(time.time()),
            )
            return ("accepted", state.signed_reference_use_count)
        except SignedReferenceStateError as exc:
            return ("rejected", exc.error_code)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(use_reference, ("use-concurrent-1", "use-concurrent-2")))

    assert sum(1 for status, _ in results if status == "accepted") == 1
    assert any(
        status == "rejected"
        and value
        in {
            "external_export_download_signed_reference_replay_denied",
            "external_export_download_signed_reference_state_persist_failed",
        }
        for status, value in results
    )

    db = session_factory()
    try:
        token = db.query(L3SignedReferenceToken).one()
        used_receipts = db.query(L3SignedReferenceReceipt).filter_by(receipt_type="used").all()
        accepted_use_audits = db.query(L3SignedReferenceAuditEvent).filter_by(
            event_type="use",
            event_status="accepted",
        ).all()
        assert token.state == SIGNED_REFERENCE_TOKEN_STATE_USED
        assert token.use_count == 1
        assert len(used_receipts) == 1
        assert len(accepted_use_audits) == 1
    finally:
        db.close()
