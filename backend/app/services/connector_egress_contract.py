"""Secret-free value contracts for the B0 connector effect boundary."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import UUID, uuid5


AUTHORITY_SCHEMA_VERSION = "project6.connector_authority.v1"
PHYSICAL_REQUEST_PLAN_SCHEMA = "project6.physical_request_plan.v1"
RESERVATION_SLOT_NAMESPACE = UUID("9fab120d-3790-5e28-9728-a8f7682b1cd4")
_DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,254}\Z")
_HEADER_NAME_PATTERN = re.compile(r"[!#$%&'*+.^_`|~0-9a-z-]+\Z")


class ContractHold(ValueError):
    pass


def _matches(pattern: re.Pattern[str], value: object) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _is_canonical_absolute_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and Path(value).is_absolute()
        and str(Path(value).resolve()) == value
    )


def _is_canonical_redirect_location(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        redirect = urlsplit(value)
        return (
            not redirect.scheme
            and not redirect.netloc
            and redirect.path.startswith("/")
            and not redirect.fragment
        ) or (
            redirect.scheme == "https"
            and bool(redirect.hostname)
            and redirect.hostname == redirect.hostname.lower()
            and redirect.username is None
            and redirect.password is None
            and not redirect.fragment
        )
    except ValueError:
        return False


@dataclass(frozen=True)
class AuthorityBindings:
    schema_version: str
    campaign_id: str
    canonical_root: str
    connector_run_id: str
    source_commit: str
    interpreter_identity: str
    authorization_digest: str
    grant_digest: str
    wrapper_start_token_ref: str


@dataclass(frozen=True)
class AuthorityEnvelope(AuthorityBindings):
    content_digest: str


@dataclass(frozen=True)
class RequestLimits:
    timeout_seconds: float
    max_response_bytes: int = 64 * 1024 * 1024
    max_redirects: int = 0

    def __post_init__(self) -> None:
        if not (
            not isinstance(self.timeout_seconds, bool)
            and isinstance(self.timeout_seconds, (int, float))
            and 0 < self.timeout_seconds <= 120
        ):
            raise ContractHold("request_limits_invalid:timeout_seconds")
        if not (
            not isinstance(self.max_response_bytes, bool)
            and isinstance(self.max_response_bytes, int)
            and 0 < self.max_response_bytes <= 64 * 1024 * 1024
        ):
            raise ContractHold("request_limits_invalid:max_response_bytes")
        if (
            isinstance(self.max_redirects, bool)
            or not isinstance(self.max_redirects, int)
            or self.max_redirects != 0
        ):
            raise ContractHold("request_limits_invalid:max_redirects")


@dataclass(frozen=True)
class PhysicalRequestPlan:
    envelope_digest: str
    campaign_id: str
    canonical_root: str
    connector_run_id: str
    target_id: str
    request_ordinal: int
    stage: str
    method: str
    canonical_destination: str
    header_names: tuple[str, ...]
    header_value_sha256s: tuple[str, ...]
    body_sha256: str
    limits: RequestLimits
    authorization_digest: str
    grant_digest: str

    def __post_init__(self) -> None:
        try:
            destination = urlsplit(
                self.canonical_destination
                if isinstance(self.canonical_destination, str)
                else ""
            )
            destination_valid = (
                destination.scheme == "https"
                and bool(destination.hostname)
                and destination.hostname == destination.hostname.lower()
                and destination.username is None
                and destination.password is None
                and not destination.fragment
            )
        except ValueError:
            destination_valid = False
        empty_body = "sha256:" + hashlib.sha256(b"").hexdigest()
        header_names_valid = (
            isinstance(self.header_names, tuple)
            and all(isinstance(name, str) for name in self.header_names)
            and self.header_names == tuple(sorted(set(self.header_names)))
            and all(
                re.fullmatch(r"[a-z0-9-]{1,64}", name) for name in self.header_names
            )
        )
        checks = {
            "envelope_digest": _matches(_DIGEST_PATTERN, self.envelope_digest),
            "campaign_id": _matches(_TOKEN_PATTERN, self.campaign_id),
            "canonical_root": _is_canonical_absolute_path(self.canonical_root),
            "connector_run_id": _is_canonical_uuid(self.connector_run_id),
            "target_id": _matches(_TOKEN_PATTERN, self.target_id),
            "request_ordinal": not isinstance(self.request_ordinal, bool)
            and isinstance(self.request_ordinal, int)
            and self.request_ordinal > 0,
            "stage": _matches(_TOKEN_PATTERN, self.stage),
            "method": isinstance(self.method, str) and self.method in {"GET", "HEAD"},
            "canonical_destination": destination_valid,
            "header_names": header_names_valid,
            "header_value_sha256s": isinstance(self.header_value_sha256s, tuple)
            and all(isinstance(value, str) for value in self.header_value_sha256s)
            and header_names_valid
            and len(self.header_value_sha256s) == len(self.header_names)
            and all(
                _matches(_DIGEST_PATTERN, value) for value in self.header_value_sha256s
            ),
            "body_sha256": _matches(_DIGEST_PATTERN, self.body_sha256)
            and (
                not isinstance(self.method, str)
                or self.method not in {"GET", "HEAD"}
                or self.body_sha256 == empty_body
            ),
            "limits": isinstance(self.limits, RequestLimits),
            "authorization_digest": _matches(
                _DIGEST_PATTERN, self.authorization_digest
            ),
            "grant_digest": _matches(_DIGEST_PATTERN, self.grant_digest),
        }
        for field, valid in checks.items():
            if not valid:
                raise ContractHold(f"physical_request_plan_invalid:{field}")

    @property
    def slot_name(self) -> str:
        return _canonical_json(
            [
                PHYSICAL_REQUEST_PLAN_SCHEMA,
                self.campaign_id,
                self.canonical_root,
                self.connector_run_id,
                self.request_ordinal,
            ]
        ).decode("utf-8")

    @property
    def slot_uuid(self) -> str:
        return str(uuid5(RESERVATION_SLOT_NAMESPACE, self.slot_name))

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": PHYSICAL_REQUEST_PLAN_SCHEMA,
            "envelope_digest": self.envelope_digest,
            "campaign_id": self.campaign_id,
            "canonical_root": self.canonical_root,
            "connector_run_id": self.connector_run_id,
            "target_id": self.target_id,
            "request_ordinal": self.request_ordinal,
            "stage": self.stage,
            "method": self.method,
            "canonical_destination": self.canonical_destination,
            "header_names": list(self.header_names),
            "header_value_sha256s": list(self.header_value_sha256s),
            "body_sha256": self.body_sha256,
            "limits": {
                "timeout_seconds": self.limits.timeout_seconds,
                "max_response_bytes": self.limits.max_response_bytes,
                "max_redirects": self.limits.max_redirects,
            },
            "authorization_digest": self.authorization_digest,
            "grant_digest": self.grant_digest,
        }

    @property
    def plan_digest(self) -> str:
        return (
            "sha256:" + hashlib.sha256(_canonical_json(self.to_document())).hexdigest()
        )


def physical_request_plan_from_document(document: Any) -> PhysicalRequestPlan:
    if not isinstance(document, dict):
        raise ContractHold("physical_request_plan_document_invalid")
    values = dict(document)
    if values.pop("schema", None) != PHYSICAL_REQUEST_PLAN_SCHEMA or set(values) != set(
        PhysicalRequestPlan.__dataclass_fields__
    ):
        raise ContractHold("physical_request_plan_document_invalid")
    if (
        not isinstance(values["limits"], dict)
        or not isinstance(values["header_names"], list)
        or not isinstance(values["header_value_sha256s"], list)
    ):
        raise ContractHold("physical_request_plan_document_invalid")
    if set(values["limits"]) != set(RequestLimits.__dataclass_fields__):
        raise ContractHold("physical_request_plan_document_invalid")
    try:
        values["limits"] = RequestLimits(**values["limits"])
    except TypeError as exc:
        raise ContractHold("physical_request_plan_document_invalid") from exc
    values["header_names"] = tuple(values["header_names"])
    values["header_value_sha256s"] = tuple(values["header_value_sha256s"])
    return PhysicalRequestPlan(**values)


@dataclass(frozen=True)
class EffectResult:
    reservation_event_id: str
    plan_digest: str
    status_code: int
    body: bytes
    response_header_names: tuple[str, ...] = ()
    redirect_location: str | None = None

    def __post_init__(self) -> None:
        if not _is_canonical_uuid(self.reservation_event_id):
            raise ContractHold("effect_result_invalid:reservation_event_id")
        if not _matches(_DIGEST_PATTERN, self.plan_digest):
            raise ContractHold("effect_result_invalid:plan_digest")
        if (
            isinstance(self.status_code, bool)
            or not isinstance(self.status_code, int)
            or not 100 <= self.status_code <= 599
        ):
            raise ContractHold("effect_result_invalid:status_code")
        if not isinstance(self.body, bytes):
            raise ContractHold("effect_result_invalid:body")
        if not (
            isinstance(self.response_header_names, tuple)
            and all(
                isinstance(name, str) and _HEADER_NAME_PATTERN.fullmatch(name)
                for name in self.response_header_names
            )
            and self.response_header_names
            == tuple(sorted(set(self.response_header_names)))
        ):
            raise ContractHold("effect_result_invalid:response_header_names")
        redirect_status = self.status_code in {301, 302, 303, 307, 308}
        if redirect_status != (self.redirect_location is not None) or (
            self.redirect_location is not None
            and not _is_canonical_redirect_location(self.redirect_location)
        ):
            raise ContractHold("effect_result_invalid:redirect_location")


class EffectPort(Protocol):
    def execute(self, plan: PhysicalRequestPlan) -> EffectResult: ...


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _is_canonical_uuid(value: Any) -> bool:
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except (TypeError, ValueError, AttributeError):
        return False


def _validate_authority_fields(document: dict[str, Any]) -> None:
    checks = {
        "schema_version": document.get("schema_version") == AUTHORITY_SCHEMA_VERSION,
        "campaign_id": _matches(_TOKEN_PATTERN, document.get("campaign_id")),
        "canonical_root": _is_canonical_absolute_path(document.get("canonical_root")),
        "source_commit": _matches(_COMMIT_PATTERN, document.get("source_commit")),
        "interpreter_identity": _matches(
            _TOKEN_PATTERN, document.get("interpreter_identity")
        ),
        "authorization_digest": _matches(
            _DIGEST_PATTERN, document.get("authorization_digest")
        ),
        "grant_digest": _matches(_DIGEST_PATTERN, document.get("grant_digest")),
        "wrapper_start_token_ref": _matches(
            _TOKEN_PATTERN, document.get("wrapper_start_token_ref")
        ),
    }
    checks["connector_run_id"] = _is_canonical_uuid(document.get("connector_run_id"))
    for field, valid in checks.items():
        if not valid:
            raise ContractHold(f"authority_envelope_field_invalid:{field}")


def validate_authority_envelope(
    raw: bytes,
    expected_content_digest: str,
    expected: AuthorityBindings,
) -> AuthorityEnvelope:
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractHold("authority_envelope_malformed") from exc
    if not isinstance(document, dict) or _canonical_json(document) != raw:
        raise ContractHold("authority_envelope_not_canonical")
    actual_digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual_digest != expected_content_digest:
        raise ContractHold("authority_envelope_digest_mismatch")
    _validate_authority_fields(document)
    expected_document = {
        name: getattr(expected, name) for name in AuthorityBindings.__dataclass_fields__
    }
    if document != expected_document:
        raise ContractHold("authority_envelope_binding_mismatch")
    return AuthorityEnvelope(**expected_document, content_digest=actual_digest)
