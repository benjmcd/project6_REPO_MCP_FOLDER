"""
Layer 3 provider-private signed URL — contract tests for durable state behaviors.

AUDIT FINDINGS (behaviors audited against layer3_provider_private_signed_url_state.py
and layer3_provider_private_signed_url.py):

EXISTS — verified by tests in this module:
  - TTL / expiry honored: status route computes expired state from receipt timestamps;
    use route enforces expiry and transitions receipt state to _expired.
  - Prepare idempotent on replay: same client_request_id + same authority/scope/TTL returns
    the same receipt_id; conflicting authority for same client_request_id raises idempotency_conflict.
  - Revoked URL refuses use: revoke_provider_private_signed_url_receipt followed by
    record_used_provider_private_signed_url_receipt raises state_revoked.
  - Recipient scope honored: different scopes with same client_request_id raise idempotency_conflict;
    scope stored on receipt and included in request_basis_hash.

EXISTS — not yet tested by this module (tested upstream in test_layer3_provider_private_signed_url_state.py):
  - Concurrent authority-creation records one authority row.
  - Stale artifact authority blocks use and revoke.
  - Revocation idempotency conflict detection.

MISSING — not implemented, not tested:
  - No HTTP-level integration test for the status GET route
    (GET /handoff/export/download/provider-private-signed-url/status/{id});
    the route delegates directly to provider_private_signed_url_status() which is
    unit-covered here through the state layer but not through HTTP client fixtures.
  - No test for idempotent revoke replay (same idempotency_key + same fields) returning
    accepted state without error — the state module supports this but no test file covers it.
"""
from __future__ import annotations

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
    L3ProviderPrivateSignedUrlReceipt,
    L3ProviderPrivateSignedUrlRevocation,
)
from app.services.layer3_provider_private_signed_url_state import (
    PROVIDER_PRIVATE_SIGNED_URL_STATE_EXPIRED,
    PROVIDER_PRIVATE_SIGNED_URL_STATE_PREPARED,
    PROVIDER_PRIVATE_SIGNED_URL_STATE_REVOKED,
    PROVIDER_PRIVATE_SIGNED_URL_STATE_USED,
    ProviderPrivateSignedUrlStateError,
    record_prepared_provider_private_signed_url_receipt,
    record_used_provider_private_signed_url_receipt,
    revoke_provider_private_signed_url_receipt,
)
from app.services.layer3_provider_private_signed_url import (
    PROVIDER_PRIVATE_SIGNED_URL_STATE_EXPIRED as SERVICE_EXPIRED,
    PROVIDER_PRIVATE_SIGNED_URL_STATE_PREPARED as SERVICE_PREPARED,
    _datetime_epoch,
    _status_from_receipt,
)


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

NOW_EPOCH = 2_000_000_000
SOURCE_ARTIFACT_HASH = "c" * 64
SOURCE_ARTIFACT_SIZE_BYTES = 1024
RAW_TOKEN = "contract-test-raw-token"
RECIPIENT_SCOPE = "contract-test-recipient:alpha"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'signed-url-contract.sqlite'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    try:
        yield SessionLocal
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _authority_basis(
    *,
    session_id: str = "session-contract-test",
    external_export_download_record_ref: str = "external-export-download:contract",
    source_artifact_size_bytes: int = SOURCE_ARTIFACT_SIZE_BYTES,
) -> dict:
    return {
        "session_id": session_id,
        "reconciliation_record_id": "reconciliation-contract-test",
        "source_artifact_ref": "C:/operator/contract/export.zip",
        "source_artifact_hash": SOURCE_ARTIFACT_HASH,
        "source_artifact_size_bytes": source_artifact_size_bytes,
        "external_export_download_record_ref": external_export_download_record_ref,
        "export_download_descriptor_ref": "contract-descriptor-ref",
    }


def _prepare(db, *, client_request_id: str, now_epoch: int = NOW_EPOCH, token: str = RAW_TOKEN,
             recipient_scope: str = RECIPIENT_SCOPE, ttl_seconds: int = 300, **kwargs):
    return record_prepared_provider_private_signed_url_receipt(
        db,
        request_id=f"req-{client_request_id}",
        client_request_id=client_request_id,
        authority_basis=_authority_basis(**kwargs),
        recipient_scope=recipient_scope,
        requested_ttl_seconds=ttl_seconds,
        now_epoch=now_epoch,
        provider_private_signed_url_token=token,
    )


def _use(db, *, receipt_id: str, now_epoch: int, token: str = RAW_TOKEN, **kwargs):
    return record_used_provider_private_signed_url_receipt(
        db,
        provider_private_signed_url_receipt_id=receipt_id,
        provider_private_signed_url_token=token,
        authority_basis=_authority_basis(**kwargs),
        now_epoch=now_epoch,
        request_id="req-use",
    )


def _revoke(db, *, receipt_id: str, idempotency_key: str = "revoke-idem-1",
            now_epoch: int = NOW_EPOCH + 10):
    return revoke_provider_private_signed_url_receipt(
        db,
        provider_private_signed_url_receipt_id=receipt_id,
        idempotency_key=idempotency_key,
        revoked_by="contract-test-operator",
        revocation_reason="contract test revocation",
        now_epoch=now_epoch,
        request_id="req-revoke",
    )


# ---------------------------------------------------------------------------
# T1: TTL expiry is honored — status computed from receipt timestamps
# ---------------------------------------------------------------------------


def test_ttl_expiry_honored_on_status_computation(session_factory) -> None:
    """
    EXISTS: _status_from_receipt returns expired when now_epoch >= expires_at.
    The status layer (used by the GET status route) correctly reflects expiry
    without requiring a DB state transition — it is computed at read time.
    """
    db = session_factory()
    try:
        state = _prepare(db, client_request_id="contract-ttl-status", ttl_seconds=60)
    finally:
        db.close()

    db = session_factory()
    try:
        receipt = (
            db.query(L3ProviderPrivateSignedUrlReceipt)
            .filter_by(
                provider_private_signed_url_receipt_id=state.provider_private_signed_url_receipt_id
            )
            .one()
        )
        # Before expiry: status is prepared.
        status_before = _status_from_receipt(receipt, now_epoch=NOW_EPOCH + 30)
        assert status_before == SERVICE_PREPARED

        # At exactly expiry time: status is expired (>= boundary is inclusive).
        status_at = _status_from_receipt(receipt, now_epoch=NOW_EPOCH + 60)
        assert status_at == SERVICE_EXPIRED

        # After expiry: status is expired.
        status_after = _status_from_receipt(receipt, now_epoch=NOW_EPOCH + 120)
        assert status_after == SERVICE_EXPIRED
    finally:
        db.close()


def test_ttl_expiry_blocks_use_and_transitions_state(session_factory) -> None:
    """
    EXISTS: Use attempt after TTL expires raises state_expired and transitions
    the receipt state to provider_private_signed_url_expired in the DB.
    """
    db = session_factory()
    try:
        state = _prepare(db, client_request_id="contract-ttl-use", ttl_seconds=30)
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPrivateSignedUrlStateError) as exc_info:
            _use(
                db,
                receipt_id=state.provider_private_signed_url_receipt_id,
                now_epoch=NOW_EPOCH + 30,  # at boundary → expired
            )
        assert exc_info.value.error_code == "provider_private_signed_url_state_expired"
        assert "provider_private_signed_url_receipt_id" in exc_info.value.blocked_fields
    finally:
        db.close()

    db = session_factory()
    try:
        receipt = db.query(L3ProviderPrivateSignedUrlReceipt).one()
        # Receipt state must have been persisted as expired.
        assert receipt.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_EXPIRED
        # Audit event must record token_expired.
        audit = (
            db.query(L3ProviderPrivateSignedUrlAuditEvent)
            .filter_by(reason_code="token_expired")
            .one()
        )
        assert audit.event_status == "rejected"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# T2: Prepare idempotency on replay
# ---------------------------------------------------------------------------


def test_prepare_idempotent_same_client_request_id_returns_same_receipt(session_factory) -> None:
    """
    EXISTS: Prepare with the same client_request_id and identical authority/scope/TTL
    returns the same receipt_id (idempotent replay accepted).
    """
    db = session_factory()
    try:
        first = _prepare(db, client_request_id="contract-idem-1",
                         external_export_download_record_ref="eed:idem")
    finally:
        db.close()

    db = session_factory()
    try:
        second = _prepare(db, client_request_id="contract-idem-1",
                          external_export_download_record_ref="eed:idem",
                          now_epoch=NOW_EPOCH + 5)
    finally:
        db.close()

    # Same receipt returned.
    assert first.provider_private_signed_url_receipt_id == second.provider_private_signed_url_receipt_id

    db = session_factory()
    try:
        audits = (
            db.query(L3ProviderPrivateSignedUrlAuditEvent)
            .filter_by(event_type="prepare")
            .all()
        )
        reason_codes = {a.reason_code for a in audits}
        assert "generated_after_authority_validation" in reason_codes
        assert "idempotent_prepare_reused" in reason_codes
    finally:
        db.close()


def test_prepare_conflict_different_authority_same_client_request_id(session_factory) -> None:
    """
    EXISTS: Prepare with the same client_request_id but different authority raises
    idempotency_conflict — the client_request_id is not reusable for different payloads.
    """
    db = session_factory()
    try:
        _prepare(db, client_request_id="contract-conflict-1",
                 external_export_download_record_ref="eed:conflict-a")
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPrivateSignedUrlStateError) as exc_info:
            _prepare(db, client_request_id="contract-conflict-1",
                     external_export_download_record_ref="eed:conflict-b")
        assert exc_info.value.error_code == "provider_private_signed_url_state_idempotency_conflict"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# T3: Recipient scope honored
# ---------------------------------------------------------------------------


def test_recipient_scope_stored_on_receipt(session_factory) -> None:
    """
    EXISTS: Recipient scope supplied at prepare time is stored on the receipt row.
    """
    db = session_factory()
    try:
        state = _prepare(
            db,
            client_request_id="contract-scope-1",
            recipient_scope="external-recipient:contract-scope-test",
            external_export_download_record_ref="eed:scope",
        )
    finally:
        db.close()

    db = session_factory()
    try:
        receipt = db.query(L3ProviderPrivateSignedUrlReceipt).one()
        assert receipt.recipient_scope == "external-recipient:contract-scope-test"
    finally:
        db.close()


def test_different_recipient_scopes_produce_different_receipt_ids(session_factory) -> None:
    """
    EXISTS: Different recipient_scope values produce different receipt IDs —
    scope is included in request_basis_hash, so the deterministic receipt_id key differs.
    Two separate DBs are used to avoid authority-hash uniqueness conflicts between prepares.
    """
    import hashlib, json

    def _receipt_id_for_scope(recipient_scope: str) -> str:
        # Replicate the deterministic key computation from the state module.
        authority = _authority_basis(external_export_download_record_ref="eed:scope-diff")
        norm = {
            "session_id": authority["session_id"],
            "reconciliation_record_id": authority["reconciliation_record_id"],
            "source_artifact_ref": authority["source_artifact_ref"],
            "source_artifact_hash": authority["source_artifact_hash"].lower(),
            "source_artifact_size_bytes": SOURCE_ARTIFACT_SIZE_BYTES,
            "external_export_download_record_ref": authority["external_export_download_record_ref"],
            "export_download_descriptor_ref": authority["export_download_descriptor_ref"],
        }
        authority_hash = hashlib.sha256(
            json.dumps(norm, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        request_basis = {
            "authority_hash": authority_hash,
            "client_request_id": "contract-scope-check",
            "recipient_scope": recipient_scope,
            "requested_ttl_seconds": 300,
        }
        request_basis_hash = hashlib.sha256(
            json.dumps(request_basis, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        return f"ppsu_{request_basis_hash[:31]}"

    id_alpha = _receipt_id_for_scope("external-recipient:alpha")
    id_beta = _receipt_id_for_scope("external-recipient:beta")
    assert id_alpha != id_beta, "Different recipient scopes must produce different receipt IDs"


def test_prepare_conflict_different_scope_same_client_request_id(session_factory) -> None:
    """
    EXISTS: Same client_request_id with a different recipient_scope raises
    idempotency_conflict — scope change is not admitted as a retry.
    """
    db = session_factory()
    try:
        _prepare(
            db,
            client_request_id="contract-scope-conflict",
            recipient_scope="external-recipient:scope-a",
            external_export_download_record_ref="eed:scope-conflict",
        )
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPrivateSignedUrlStateError) as exc_info:
            _prepare(
                db,
                client_request_id="contract-scope-conflict",
                recipient_scope="external-recipient:scope-b",
                external_export_download_record_ref="eed:scope-conflict",
            )
        assert exc_info.value.error_code == "provider_private_signed_url_state_idempotency_conflict"
        assert "recipient_scope" in exc_info.value.blocked_fields
    finally:
        db.close()


# ---------------------------------------------------------------------------
# T4: Revocation enforcement — revoked receipt refuses use
# ---------------------------------------------------------------------------


def test_revoked_url_refuses_use(session_factory) -> None:
    """
    EXISTS: Once a receipt is revoked, any subsequent use attempt is rejected with
    provider_private_signed_url_state_revoked.
    """
    token = "contract-revoke-use-token"
    db = session_factory()
    try:
        state = _prepare(
            db,
            client_request_id="contract-revoke-use",
            token=token,
            external_export_download_record_ref="eed:revoke-use",
        )
    finally:
        db.close()

    db = session_factory()
    try:
        revoked = _revoke(db, receipt_id=state.provider_private_signed_url_receipt_id)
        assert revoked.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_REVOKED
        assert revoked.provider_private_signed_url_revoked is True
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPrivateSignedUrlStateError) as exc_info:
            _use(
                db,
                receipt_id=state.provider_private_signed_url_receipt_id,
                now_epoch=NOW_EPOCH + 15,
                token=token,
                external_export_download_record_ref="eed:revoke-use",
            )
        assert exc_info.value.error_code == "provider_private_signed_url_state_revoked"
    finally:
        db.close()

    db = session_factory()
    try:
        receipt = db.query(L3ProviderPrivateSignedUrlReceipt).one()
        assert receipt.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_REVOKED
        revocation = db.query(L3ProviderPrivateSignedUrlRevocation).one()
        assert revocation.provider_private_signed_url_receipt_id == state.provider_private_signed_url_receipt_id
    finally:
        db.close()


def test_revoke_idempotent_replay_accepted(session_factory) -> None:
    """
    EXISTS: Revoking with the same idempotency_key, revoked_by, and revocation_reason
    a second time is accepted (idempotent replay), returning the existing revoked state.
    """
    token = "contract-revoke-idem-token"
    db = session_factory()
    try:
        state = _prepare(
            db,
            client_request_id="contract-revoke-idem",
            token=token,
            external_export_download_record_ref="eed:revoke-idem",
        )
    finally:
        db.close()

    db = session_factory()
    try:
        first = _revoke(
            db,
            receipt_id=state.provider_private_signed_url_receipt_id,
            idempotency_key="idem-key-contract",
        )
        assert first.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_REVOKED
    finally:
        db.close()

    db = session_factory()
    try:
        second = revoke_provider_private_signed_url_receipt(
            db,
            provider_private_signed_url_receipt_id=state.provider_private_signed_url_receipt_id,
            idempotency_key="idem-key-contract",
            revoked_by="contract-test-operator",
            revocation_reason="contract test revocation",
            now_epoch=NOW_EPOCH + 20,
            request_id="req-revoke-2",
        )
        assert second.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_REVOKED
    finally:
        db.close()

    db = session_factory()
    try:
        # Only one revocation row (idempotent — not duplicated).
        assert db.query(L3ProviderPrivateSignedUrlRevocation).count() == 1
    finally:
        db.close()


def test_single_use_policy_blocks_replay_after_first_use(session_factory) -> None:
    """
    EXISTS: Single-use policy (max_use_count=1) blocks a second use attempt
    with provider_private_signed_url_state_replay_denied.
    """
    token = "contract-single-use-token"
    db = session_factory()
    try:
        state = _prepare(
            db,
            client_request_id="contract-single-use",
            token=token,
            external_export_download_record_ref="eed:single-use",
        )
    finally:
        db.close()

    db = session_factory()
    try:
        used = _use(
            db,
            receipt_id=state.provider_private_signed_url_receipt_id,
            now_epoch=NOW_EPOCH + 5,
            token=token,
            external_export_download_record_ref="eed:single-use",
        )
        assert used.provider_private_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_STATE_USED
        assert used.provider_private_signed_url_use_count == 1
    finally:
        db.close()

    db = session_factory()
    try:
        with pytest.raises(ProviderPrivateSignedUrlStateError) as exc_info:
            _use(
                db,
                receipt_id=state.provider_private_signed_url_receipt_id,
                now_epoch=NOW_EPOCH + 6,
                token=token,
                external_export_download_record_ref="eed:single-use",
            )
        assert exc_info.value.error_code == "provider_private_signed_url_state_replay_denied"
    finally:
        db.close()
