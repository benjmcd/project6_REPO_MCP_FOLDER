from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any, Mapping


PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_SCHEMA_ID = (
    "layer3.provider_private_signed_url.fake_provider.v1"
)
PROVIDER_PRIVATE_SIGNED_URL_PREPARED_STATE = "provider_private_signed_url_prepared"
PROVIDER_PRIVATE_SIGNED_URL_USED_STATE = "provider_private_signed_url_used"
PROVIDER_PRIVATE_SIGNED_URL_REVOKED_STATE = "provider_private_signed_url_revoked"
PROVIDER_PRIVATE_SIGNED_URL_EXPIRED_STATE = "provider_private_signed_url_expired"
PROVIDER_PRIVATE_SIGNED_URL_BLOCKED_STATE = "provider_private_signed_url_blocked"
PROVIDER_PRIVATE_SIGNED_URL_CONFLICT_STATE = "provider_private_signed_url_conflict"
PROVIDER_PRIVATE_SIGNED_URL_REPLAY_POLICY = "single_use"
PROVIDER_PRIVATE_SIGNED_URL_MAX_TTL_SECONDS = 900
PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY = "deterministic_in_memory_fake_provider"

PROVIDER_PRIVATE_SIGNED_URL_RESPONSE_FORBIDDEN_FIELDS = frozenset(
    {
        "provider_credentials",
        "provider_secret",
        "raw_provider_signature",
        "raw_provider_object_key",
        "raw_local_path",
        "provider_bucket",
        "provider_container",
        "public_url",
        "public_proxy_url",
        "connector_run_id",
        "destination_write_id",
        "package_payload",
        "source_expansion_state",
        "rag_vector_state",
        "prompt_or_model_payload",
        "auth_internal_state",
    }
)


@dataclass(frozen=True)
class ProviderPrivateSignedUrlError(Exception):
    error_code: str
    message: str
    status: str
    blocked_fields: tuple[str, ...] = ()
    next_allowed_actions: tuple[str, ...] = ()

    def to_response(self) -> dict[str, Any]:
        return {
            "schema_id": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_SCHEMA_ID,
            "status": self.status,
            "error_code": self.error_code,
            "message": self.message,
            "blocked_fields": list(self.blocked_fields),
            "next_allowed_actions": list(self.next_allowed_actions),
        }


@dataclass(frozen=True)
class ProviderArtifactAuthority:
    source_artifact_ref: str
    source_artifact_hash: str
    source_artifact_size_bytes: int
    external_export_download_record_ref: str
    export_download_descriptor_ref: str


@dataclass(frozen=True)
class ProviderPrivateSignedUrlPrepareRequest:
    client_request_id: str
    authority: ProviderArtifactAuthority
    recipient_scope: str
    requested_ttl_seconds: int
    now_epoch: int
    provider_policy_ref: str = "fake-provider-single-use-v1"


@dataclass(frozen=True)
class ProviderPrivateSignedUrlReceipt:
    provider_signed_url_receipt_id: str
    provider_object_identity: str
    provider_url_token_hash: str
    provider_url_redacted: str
    provider_url_expires_at_epoch: int
    provider_url_expires_in_seconds: int
    provider_url_replay_policy: str
    provider_url_revocation_supported: bool
    provider_signed_url_state: str
    source_artifact_ref: str
    source_artifact_hash: str
    source_artifact_size_bytes: int
    authority_identity_hash: str
    audit_receipt: dict[str, Any]
    next_allowed_actions: tuple[str, ...]
    next_state: str
    use_count: int = 0
    revoked_reason_hash: str | None = None
    _token_for_test: str = ""
    _idempotency_identity_hash: str = ""

    @property
    def token_for_test(self) -> str:
        return self._token_for_test

    def to_prepare_response(self, *, request_id: str) -> dict[str, Any]:
        return {
            "schema_id": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_SCHEMA_ID,
            "schema_version": "1",
            "request_id": request_id,
            "status": "prepared",
            "provider_signed_url_receipt_id": self.provider_signed_url_receipt_id,
            "provider_signed_url_state": self.provider_signed_url_state,
            "delivery_mode": "provider_private_signed_url",
            "provider_url_redacted": self.provider_url_redacted,
            "provider_url_expires_at": self.provider_url_expires_at_epoch,
            "provider_url_expires_in_seconds": self.provider_url_expires_in_seconds,
            "provider_url_replay_policy": self.provider_url_replay_policy,
            "provider_url_revocation_supported": self.provider_url_revocation_supported,
            "source_artifact_ref": self.source_artifact_ref,
            "source_artifact_hash": self.source_artifact_hash,
            "source_artifact_size_bytes": self.source_artifact_size_bytes,
            "authority_rail": {
                "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
                "artifact_authority": "external_export_download_hash_size_authority",
                "provider_url_secret_redacted": True,
                "provider_network_enabled": False,
                "provider_object_write_enabled": False,
                "connector_dispatch_enabled": False,
                "destination_write_enabled": False,
                "public_url_enabled": False,
            },
            "audit_receipt": dict(self.audit_receipt),
            "next_allowed_actions": list(self.next_allowed_actions),
            "next_state": self.next_state,
        }

    def to_status_response(self, *, now_epoch: int) -> dict[str, Any]:
        state = self.provider_signed_url_state
        if state == PROVIDER_PRIVATE_SIGNED_URL_PREPARED_STATE and now_epoch >= self.provider_url_expires_at_epoch:
            state = PROVIDER_PRIVATE_SIGNED_URL_EXPIRED_STATE
        return {
            "schema_id": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_SCHEMA_ID,
            "status": "ok",
            "provider_signed_url_receipt_id": self.provider_signed_url_receipt_id,
            "provider_signed_url_state": state,
            "provider_url_redacted": self.provider_url_redacted,
            "provider_url_expires_at": self.provider_url_expires_at_epoch,
            "provider_url_replay_policy": self.provider_url_replay_policy,
            "provider_url_revocation_supported": self.provider_url_revocation_supported,
            "use_count": self.use_count,
            "revoked": state == PROVIDER_PRIVATE_SIGNED_URL_REVOKED_STATE,
            "source_artifact_hash": self.source_artifact_hash,
            "source_artifact_size_bytes": self.source_artifact_size_bytes,
            "audit_receipt": dict(self.audit_receipt),
        }


class ProviderPrivateSignedUrlFakeProvider:
    def __init__(self, *, fail_operations: Mapping[str, str] | None = None) -> None:
        self._receipts_by_id: dict[str, ProviderPrivateSignedUrlReceipt] = {}
        self._receipts_by_client_request_id: dict[str, ProviderPrivateSignedUrlReceipt] = {}
        self._fail_operations = dict(fail_operations or {})

    def prepare(self, request: ProviderPrivateSignedUrlPrepareRequest) -> ProviderPrivateSignedUrlReceipt:
        self._fail_if_requested("prepare")
        _validate_prepare_request(request)
        object_identity = "fake-provider-object:" + _digest(
            {
                "source_artifact_ref": request.authority.source_artifact_ref,
                "source_artifact_hash": request.authority.source_artifact_hash,
                "source_artifact_size_bytes": request.authority.source_artifact_size_bytes,
            }
        )
        authority_identity_hash = _digest(_authority_identity(request.authority))
        idempotency_identity_hash = _digest(
            {
                "client_request_id": request.client_request_id.strip(),
                "authority_identity_hash": authority_identity_hash,
                "recipient_scope": request.recipient_scope.strip(),
                "requested_ttl_seconds": request.requested_ttl_seconds,
                "provider_policy_ref": request.provider_policy_ref.strip(),
            }
        )
        existing = self._receipts_by_client_request_id.get(request.client_request_id.strip())
        if existing is not None:
            if existing._idempotency_identity_hash != idempotency_identity_hash:
                raise ProviderPrivateSignedUrlError(
                    "provider_private_signed_url_idempotency_conflict",
                    "client_request_id was already used for different provider private signed URL authority.",
                    PROVIDER_PRIVATE_SIGNED_URL_CONFLICT_STATE,
                    blocked_fields=("client_request_id", "source_artifact_hash", "source_artifact_size_bytes"),
                    next_allowed_actions=("submit_new_client_request_id",),
                )
            return existing

        expires_at_epoch = request.now_epoch + request.requested_ttl_seconds
        receipt_id = "provider-signed-url:" + _digest(
            {
                "idempotency_identity_hash": idempotency_identity_hash,
                "expires_at_epoch": expires_at_epoch,
            }
        )[:32]
        token = "fake-provider-private-token:" + _digest(
            {
                "receipt_id": receipt_id,
                "object_identity": object_identity,
                "expires_at_epoch": expires_at_epoch,
                "authority_identity_hash": authority_identity_hash,
            }
        )
        receipt = ProviderPrivateSignedUrlReceipt(
            provider_signed_url_receipt_id=receipt_id,
            provider_object_identity=object_identity,
            provider_url_token_hash=_digest(token),
            provider_url_redacted=f"https://provider.invalid/layer3/{receipt_id}?signature=redacted",
            provider_url_expires_at_epoch=expires_at_epoch,
            provider_url_expires_in_seconds=request.requested_ttl_seconds,
            provider_url_replay_policy=PROVIDER_PRIVATE_SIGNED_URL_REPLAY_POLICY,
            provider_url_revocation_supported=True,
            provider_signed_url_state=PROVIDER_PRIVATE_SIGNED_URL_PREPARED_STATE,
            source_artifact_ref=request.authority.source_artifact_ref.strip(),
            source_artifact_hash=request.authority.source_artifact_hash.strip().lower(),
            source_artifact_size_bytes=request.authority.source_artifact_size_bytes,
            authority_identity_hash=authority_identity_hash,
            audit_receipt={
                "provider_authority": PROVIDER_PRIVATE_SIGNED_URL_FAKE_PROVIDER_AUTHORITY,
                "provider_object_identity_hash": _digest(object_identity),
                "provider_url_token_hash": _digest(token),
                "authority_identity_hash": authority_identity_hash,
                "provider_network_enabled": False,
                "provider_object_write_enabled": False,
            },
            next_allowed_actions=("use_provider_private_signed_url", "revoke_provider_private_signed_url"),
            next_state=PROVIDER_PRIVATE_SIGNED_URL_PREPARED_STATE,
            _token_for_test=token,
            _idempotency_identity_hash=idempotency_identity_hash,
        )
        self._receipts_by_id[receipt.provider_signed_url_receipt_id] = receipt
        self._receipts_by_client_request_id[request.client_request_id.strip()] = receipt
        return receipt

    def use(
        self,
        *,
        provider_signed_url_receipt_id: str,
        provider_private_signed_url_token: str,
        now_epoch: int,
        current_authority: ProviderArtifactAuthority,
    ) -> ProviderPrivateSignedUrlReceipt:
        self._fail_if_requested("use")
        receipt = self._receipt(provider_signed_url_receipt_id)
        if not provider_private_signed_url_token.strip():
            raise ProviderPrivateSignedUrlError(
                "provider_private_signed_url_token_required",
                "provider_private_signed_url_token is required.",
                "invalid",
                blocked_fields=("provider_private_signed_url_token",),
                next_allowed_actions=("submit_provider_private_signed_url_token",),
            )
        if _digest(provider_private_signed_url_token.strip()) != receipt.provider_url_token_hash:
            raise ProviderPrivateSignedUrlError(
                "provider_private_signed_url_token_mismatch",
                "Provider private signed URL token could not be verified by the fake provider.",
                "invalid",
                blocked_fields=("provider_private_signed_url_token",),
                next_allowed_actions=("refresh_provider_private_signed_url",),
            )
        if _digest(_authority_identity(current_authority)) != receipt.authority_identity_hash:
            raise ProviderPrivateSignedUrlError(
                "provider_private_signed_url_authority_mismatch",
                "Current artifact authority no longer matches the provider private signed URL receipt.",
                PROVIDER_PRIVATE_SIGNED_URL_CONFLICT_STATE,
                blocked_fields=("source_artifact_ref", "source_artifact_hash", "source_artifact_size_bytes"),
                next_allowed_actions=("prepare_new_provider_private_signed_url",),
            )
        if receipt.provider_signed_url_state == PROVIDER_PRIVATE_SIGNED_URL_REVOKED_STATE:
            raise ProviderPrivateSignedUrlError(
                "provider_private_signed_url_revoked",
                "Provider private signed URL receipt has been revoked.",
                PROVIDER_PRIVATE_SIGNED_URL_BLOCKED_STATE,
                blocked_fields=("provider_signed_url_receipt_id",),
                next_allowed_actions=("prepare_new_provider_private_signed_url",),
            )
        if now_epoch >= receipt.provider_url_expires_at_epoch:
            expired = replace(receipt, provider_signed_url_state=PROVIDER_PRIVATE_SIGNED_URL_EXPIRED_STATE)
            self._store_receipt(expired)
            raise ProviderPrivateSignedUrlError(
                "provider_private_signed_url_expired",
                "Provider private signed URL receipt has expired.",
                PROVIDER_PRIVATE_SIGNED_URL_BLOCKED_STATE,
                blocked_fields=("provider_signed_url_receipt_id",),
                next_allowed_actions=("prepare_new_provider_private_signed_url",),
            )
        if receipt.use_count >= 1:
            raise ProviderPrivateSignedUrlError(
                "provider_private_signed_url_replay_denied",
                "Provider private signed URL replay is denied by the single-use replay policy.",
                PROVIDER_PRIVATE_SIGNED_URL_BLOCKED_STATE,
                blocked_fields=("provider_signed_url_receipt_id",),
                next_allowed_actions=("prepare_new_provider_private_signed_url",),
            )
        used = replace(
            receipt,
            provider_signed_url_state=PROVIDER_PRIVATE_SIGNED_URL_USED_STATE,
            use_count=receipt.use_count + 1,
            next_allowed_actions=("inspect_provider_private_signed_url_status",),
            next_state=PROVIDER_PRIVATE_SIGNED_URL_USED_STATE,
        )
        self._store_receipt(used)
        return used

    def revoke(
        self,
        *,
        provider_signed_url_receipt_id: str,
        revocation_reason: str,
        now_epoch: int,
    ) -> ProviderPrivateSignedUrlReceipt:
        del now_epoch
        self._fail_if_requested("revoke")
        if not revocation_reason.strip():
            raise ProviderPrivateSignedUrlError(
                "provider_private_signed_url_revocation_reason_required",
                "revocation_reason is required.",
                "invalid",
                blocked_fields=("revocation_reason",),
                next_allowed_actions=("submit_revocation_reason",),
            )
        receipt = self._receipt(provider_signed_url_receipt_id)
        revoked = replace(
            receipt,
            provider_signed_url_state=PROVIDER_PRIVATE_SIGNED_URL_REVOKED_STATE,
            revoked_reason_hash=_digest(revocation_reason.strip()),
            next_allowed_actions=("inspect_provider_private_signed_url_status",),
            next_state=PROVIDER_PRIVATE_SIGNED_URL_REVOKED_STATE,
        )
        self._store_receipt(revoked)
        return revoked

    def status(self, *, provider_signed_url_receipt_id: str, now_epoch: int) -> dict[str, Any]:
        self._fail_if_requested("status")
        return self._receipt(provider_signed_url_receipt_id).to_status_response(now_epoch=now_epoch)

    def _receipt(self, provider_signed_url_receipt_id: str) -> ProviderPrivateSignedUrlReceipt:
        receipt = self._receipts_by_id.get(provider_signed_url_receipt_id.strip())
        if receipt is None:
            raise ProviderPrivateSignedUrlError(
                "provider_private_signed_url_receipt_not_found",
                "Provider private signed URL receipt was not found in the fake provider.",
                "not_found",
                blocked_fields=("provider_signed_url_receipt_id",),
                next_allowed_actions=("prepare_provider_private_signed_url",),
            )
        return receipt

    def _store_receipt(self, receipt: ProviderPrivateSignedUrlReceipt) -> None:
        self._receipts_by_id[receipt.provider_signed_url_receipt_id] = receipt

    def _fail_if_requested(self, operation: str) -> None:
        error_code = self._fail_operations.get(operation)
        if error_code:
            raise ProviderPrivateSignedUrlError(
                error_code,
                f"Fake provider failure injected for {operation}.",
                PROVIDER_PRIVATE_SIGNED_URL_BLOCKED_STATE,
                blocked_fields=(operation,),
                next_allowed_actions=("retry_after_provider_recovery",),
            )


def _validate_prepare_request(request: ProviderPrivateSignedUrlPrepareRequest) -> None:
    missing = []
    if not request.client_request_id.strip():
        missing.append("client_request_id")
    if not request.authority.source_artifact_ref.strip():
        missing.append("source_artifact_ref")
    if not request.authority.source_artifact_hash.strip():
        missing.append("source_artifact_hash")
    if not request.authority.external_export_download_record_ref.strip():
        missing.append("external_export_download_record_ref")
    if not request.authority.export_download_descriptor_ref.strip():
        missing.append("export_download_descriptor_ref")
    if not request.recipient_scope.strip():
        missing.append("recipient_scope")
    if missing:
        raise ProviderPrivateSignedUrlError(
            "provider_private_signed_url_required_fields_missing",
            "Provider private signed URL prepare request is missing required authority fields.",
            "invalid",
            blocked_fields=tuple(missing),
            next_allowed_actions=("submit_complete_provider_private_signed_url_request",),
        )
    if not _is_sha256(request.authority.source_artifact_hash.strip()):
        raise ProviderPrivateSignedUrlError(
            "provider_private_signed_url_artifact_hash_invalid",
            "source_artifact_hash must be a lowercase SHA-256 hex digest.",
            "invalid",
            blocked_fields=("source_artifact_hash",),
            next_allowed_actions=("refresh_external_export_download_prepare",),
        )
    if request.authority.source_artifact_size_bytes <= 0:
        raise ProviderPrivateSignedUrlError(
            "provider_private_signed_url_artifact_size_invalid",
            "source_artifact_size_bytes must be positive.",
            "invalid",
            blocked_fields=("source_artifact_size_bytes",),
            next_allowed_actions=("refresh_external_export_download_prepare",),
        )
    ttl_out_of_bounds = (
        request.requested_ttl_seconds <= 0
        or request.requested_ttl_seconds > PROVIDER_PRIVATE_SIGNED_URL_MAX_TTL_SECONDS
    )
    if ttl_out_of_bounds:
        raise ProviderPrivateSignedUrlError(
            "provider_private_signed_url_ttl_not_admitted",
            "requested_ttl_seconds must be positive and within the fake provider TTL bound.",
            "invalid",
            blocked_fields=("requested_ttl_seconds",),
            next_allowed_actions=("submit_bounded_provider_private_signed_url_ttl",),
        )


def _authority_identity(authority: ProviderArtifactAuthority) -> dict[str, Any]:
    return {
        "source_artifact_ref": authority.source_artifact_ref.strip(),
        "source_artifact_hash": authority.source_artifact_hash.strip().lower(),
        "source_artifact_size_bytes": authority.source_artifact_size_bytes,
        "external_export_download_record_ref": authority.external_export_download_record_ref.strip(),
        "export_download_descriptor_ref": authority.export_download_descriptor_ref.strip(),
    }


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _digest(value: Any) -> str:
    if isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
