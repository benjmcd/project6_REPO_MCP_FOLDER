from __future__ import annotations

import json

import pytest

from app.services.layer3_provider_private_signed_url_fake_provider import (
    PROVIDER_PRIVATE_SIGNED_URL_BLOCKED_STATE,
    PROVIDER_PRIVATE_SIGNED_URL_CONFLICT_STATE,
    PROVIDER_PRIVATE_SIGNED_URL_EXPIRED_STATE,
    PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
    PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_SCHEMA_ID,
    PROVIDER_PRIVATE_SIGNED_URL_PREPARED_STATE,
    PROVIDER_PRIVATE_SIGNED_URL_RESPONSE_FORBIDDEN_FIELDS,
    PROVIDER_PRIVATE_SIGNED_URL_REPLAY_POLICY,
    PROVIDER_PRIVATE_SIGNED_URL_REVOKED_STATE,
    PROVIDER_PRIVATE_SIGNED_URL_USED_STATE,
    ProviderArtifactAuthority,
    ProviderPrivateSignedUrlError,
    ProviderPrivateSignedUrlFakeProvider,
    ProviderPrivateSignedUrlPrepareRequest,
)


NOW_EPOCH = 1_800_000_000
SOURCE_ARTIFACT_HASH = "a" * 64
SOURCE_ARTIFACT_SIZE_BYTES = 128


def test_fake_provider_prepare_is_deterministic_idempotent_and_redacted() -> None:
    provider = ProviderPrivateSignedUrlFakeProvider()
    request = _prepare_request()

    first = provider.prepare(request)
    second = provider.prepare(request)

    assert first is second
    assert first.provider_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_PREPARED_STATE
    assert first.provider_object_identity.startswith("fake-provider-object:")
    assert first.source_artifact_hash == SOURCE_ARTIFACT_HASH
    assert first.source_artifact_size_bytes == SOURCE_ARTIFACT_SIZE_BYTES
    assert first.provider_url_replay_policy == PROVIDER_PRIVATE_SIGNED_URL_REPLAY_POLICY
    assert first.provider_url_revocation_supported is True
    assert first.to_prepare_response(request_id="req-1")["provider_url_expires_in_seconds"] == 300
    assert first.audit_receipt["provider_authority"] == PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY
    assert first.audit_receipt["provider_network_enabled"] is False
    assert first.audit_receipt["provider_object_write_enabled"] is False
    assert "signature=redacted" in first.provider_url_redacted
    assert first.token_for_test not in json.dumps(first.to_prepare_response(request_id="req-1"), sort_keys=True)
    _assert_forbidden_response_surface_absent(first.to_prepare_response(request_id="req-1"))


def test_fake_provider_rejects_stale_hash_size_authority_and_idempotency_conflicts() -> None:
    provider = ProviderPrivateSignedUrlFakeProvider()
    request = _prepare_request()
    receipt = provider.prepare(request)

    with pytest.raises(ProviderPrivateSignedUrlError) as stale_error:
        provider.use(
            provider_signed_url_receipt_id=receipt.provider_signed_url_receipt_id,
            provider_private_signed_url_token=receipt.token_for_test,
            now_epoch=NOW_EPOCH + 60,
            current_authority=_authority(source_artifact_hash="b" * 64),
        )
    assert stale_error.value.error_code == "provider_private_signed_url_authority_mismatch"
    assert stale_error.value.status == PROVIDER_PRIVATE_SIGNED_URL_CONFLICT_STATE
    assert "source_artifact_hash" in stale_error.value.blocked_fields

    with pytest.raises(ProviderPrivateSignedUrlError) as conflict_error:
        provider.prepare(
            _prepare_request(
                client_request_id=request.client_request_id,
                source_artifact_size_bytes=SOURCE_ARTIFACT_SIZE_BYTES + 1,
            )
        )
    assert conflict_error.value.error_code == "provider_private_signed_url_idempotency_conflict"
    assert conflict_error.value.status == PROVIDER_PRIVATE_SIGNED_URL_CONFLICT_STATE


def test_fake_provider_validates_artifact_hash_size_and_ttl() -> None:
    provider = ProviderPrivateSignedUrlFakeProvider()

    with pytest.raises(ProviderPrivateSignedUrlError) as hash_error:
        provider.prepare(_prepare_request(source_artifact_hash="not-a-hash"))
    assert hash_error.value.error_code == "provider_private_signed_url_artifact_hash_invalid"
    assert hash_error.value.blocked_fields == ("source_artifact_hash",)

    with pytest.raises(ProviderPrivateSignedUrlError) as size_error:
        provider.prepare(_prepare_request(source_artifact_size_bytes=0))
    assert size_error.value.error_code == "provider_private_signed_url_artifact_size_invalid"
    assert size_error.value.blocked_fields == ("source_artifact_size_bytes",)

    with pytest.raises(ProviderPrivateSignedUrlError) as ttl_error:
        provider.prepare(_prepare_request(requested_ttl_seconds=901))
    assert ttl_error.value.error_code == "provider_private_signed_url_ttl_not_admitted"
    assert ttl_error.value.blocked_fields == ("requested_ttl_seconds",)


def test_fake_provider_supports_failure_injection_without_secret_leakage() -> None:
    provider = ProviderPrivateSignedUrlFakeProvider(
        fail_operations={"prepare": "provider_private_signed_url_fake_provider_unavailable"}
    )

    with pytest.raises(ProviderPrivateSignedUrlError) as error:
        provider.prepare(_prepare_request())

    assert error.value.error_code == "provider_private_signed_url_fake_provider_unavailable"
    assert error.value.status == PROVIDER_PRIVATE_SIGNED_URL_BLOCKED_STATE
    _assert_forbidden_response_surface_absent(error.value.to_response())


def test_fake_provider_enforces_ttl_expiry_replay_and_revocation() -> None:
    provider = ProviderPrivateSignedUrlFakeProvider()
    receipt = provider.prepare(_prepare_request(requested_ttl_seconds=60))

    with pytest.raises(ProviderPrivateSignedUrlError) as expired_error:
        provider.use(
            provider_signed_url_receipt_id=receipt.provider_signed_url_receipt_id,
            provider_private_signed_url_token=receipt.token_for_test,
            now_epoch=NOW_EPOCH + 60,
            current_authority=_authority(),
        )
    assert expired_error.value.error_code == "provider_private_signed_url_expired"
    assert expired_error.value.status == PROVIDER_PRIVATE_SIGNED_URL_BLOCKED_STATE
    assert provider.status(
        provider_signed_url_receipt_id=receipt.provider_signed_url_receipt_id,
        now_epoch=NOW_EPOCH + 60,
    )["provider_signed_url_state"] == PROVIDER_PRIVATE_SIGNED_URL_EXPIRED_STATE

    replay_provider = ProviderPrivateSignedUrlFakeProvider()
    replay_receipt = replay_provider.prepare(_prepare_request(client_request_id="req-replay"))
    used = replay_provider.use(
        provider_signed_url_receipt_id=replay_receipt.provider_signed_url_receipt_id,
        provider_private_signed_url_token=replay_receipt.token_for_test,
        now_epoch=NOW_EPOCH + 30,
        current_authority=_authority(),
    )
    assert used.provider_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_USED_STATE
    assert used.use_count == 1
    with pytest.raises(ProviderPrivateSignedUrlError) as replay_error:
        replay_provider.use(
            provider_signed_url_receipt_id=replay_receipt.provider_signed_url_receipt_id,
            provider_private_signed_url_token=replay_receipt.token_for_test,
            now_epoch=NOW_EPOCH + 31,
            current_authority=_authority(),
        )
    assert replay_error.value.error_code == "provider_private_signed_url_replay_denied"

    revoke_provider = ProviderPrivateSignedUrlFakeProvider()
    revoke_receipt = revoke_provider.prepare(_prepare_request(client_request_id="req-revoke"))
    revoked = revoke_provider.revoke(
        provider_signed_url_receipt_id=revoke_receipt.provider_signed_url_receipt_id,
        revocation_reason="operator cancelled external recipient access",
        now_epoch=NOW_EPOCH + 20,
    )
    assert revoked.provider_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_REVOKED_STATE
    assert revoked.revoked_reason_hash
    with pytest.raises(ProviderPrivateSignedUrlError) as revoked_error:
        revoke_provider.use(
            provider_signed_url_receipt_id=revoke_receipt.provider_signed_url_receipt_id,
            provider_private_signed_url_token=revoke_receipt.token_for_test,
            now_epoch=NOW_EPOCH + 21,
            current_authority=_authority(),
        )
    assert revoked_error.value.error_code == "provider_private_signed_url_revoked"


def test_fake_provider_status_and_audit_receipts_are_redacted() -> None:
    provider = ProviderPrivateSignedUrlFakeProvider()
    receipt = provider.prepare(_prepare_request())

    status = provider.status(
        provider_signed_url_receipt_id=receipt.provider_signed_url_receipt_id,
        now_epoch=NOW_EPOCH + 1,
    )

    assert status["schema_id"] == PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_SCHEMA_ID
    assert status["provider_signed_url_state"] == PROVIDER_PRIVATE_SIGNED_URL_PREPARED_STATE
    assert status["provider_url_redacted"] == receipt.provider_url_redacted
    assert "provider_url_token_hash" in status["audit_receipt"]
    serialized = json.dumps(status, sort_keys=True)
    assert receipt.token_for_test not in serialized
    assert receipt.provider_object_identity not in serialized
    _assert_forbidden_response_surface_absent(status)


def _prepare_request(
    *,
    client_request_id: str = "req-provider-private-url",
    source_artifact_hash: str = SOURCE_ARTIFACT_HASH,
    source_artifact_size_bytes: int = SOURCE_ARTIFACT_SIZE_BYTES,
    requested_ttl_seconds: int = 300,
) -> ProviderPrivateSignedUrlPrepareRequest:
    return ProviderPrivateSignedUrlPrepareRequest(
        client_request_id=client_request_id,
        authority=_authority(
            source_artifact_hash=source_artifact_hash,
            source_artifact_size_bytes=source_artifact_size_bytes,
        ),
        recipient_scope="external-downstream-recipient:demo",
        requested_ttl_seconds=requested_ttl_seconds,
        now_epoch=NOW_EPOCH,
    )


def _authority(
    *,
    source_artifact_hash: str = SOURCE_ARTIFACT_HASH,
    source_artifact_size_bytes: int = SOURCE_ARTIFACT_SIZE_BYTES,
) -> ProviderArtifactAuthority:
    return ProviderArtifactAuthority(
        source_artifact_ref="artifact://layer3/aps-bundle.json",
        source_artifact_hash=source_artifact_hash,
        source_artifact_size_bytes=source_artifact_size_bytes,
        external_export_download_record_ref="external-export-download:prepared",
        export_download_descriptor_ref="external-export-download-descriptor:aps-bundle",
    )


def _assert_forbidden_response_surface_absent(payload: object) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in PROVIDER_PRIVATE_SIGNED_URL_RESPONSE_FORBIDDEN_FIELDS
            _assert_forbidden_response_surface_absent(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_forbidden_response_surface_absent(value)
