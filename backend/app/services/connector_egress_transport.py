from __future__ import annotations

import hashlib
import http.client
import ipaddress
import math
import os
from pathlib import Path
import socket
import time
from types import MappingProxyType
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.cookiejar import DefaultCookiePolicy
from typing import Any, Callable, Iterable, Mapping, NoReturn
from urllib.parse import parse_qsl, urlsplit
from uuid import NAMESPACE_URL, uuid5

import requests  # type: ignore[import-untyped]
from requests.adapters import HTTPAdapter  # type: ignore[import-untyped]
from requests.cookies import RequestsCookieJar  # type: ignore[import-untyped]
from requests.models import PreparedRequest, Response  # type: ignore[import-untyped]
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import ConnectorPolicySnapshot, ConnectorRun, ConnectorRunEvent
from app.schemas.api import (
    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES as GRANT_DETECTION_ALLOWANCE_BYTES,
)
from app.services.connector_egress_authorization import (
    canonical_json_bytes,
    strict_json_loads,
)


HTTP_MAX_LINE_BYTES = 65_536
HTTP_MAX_HEADER_LINES = 100
STREAM_READ_CHUNK_BYTES = 65_536
MAX_SINGLE_SEND_HEADER_BYTES = (
    HTTP_MAX_HEADER_LINES * HTTP_MAX_LINE_BYTES + HTTP_MAX_LINE_BYTES
)
SINGLE_SEND_DETECTION_ALLOWANCE_BYTES = (
    MAX_SINGLE_SEND_HEADER_BYTES + STREAM_READ_CHUNK_BYTES
)

RESERVATION_EVENT_TYPE = "egress_reserved"
COMPLETION_EVENT_TYPE = "egress_completed"
TERMINAL_LEDGER_SCHEMA_ID = "project6.connector_egress_terminal_ledger.v1"

SESSION_FACTORY = SessionLocal

_CLOSED_OUTCOME_CLASSES = frozenset(
    {
        "completed",
        "reserved_not_sent",
        "timeout",
        "oversized",
        "content_encoding_rejected",
        "transport_error",
        "counter_write_failed",
    }
)
_HTTP_HEADER_TOKEN_CHARS = frozenset(
    "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)
_EXACT_PATH_RULES = {
    "sciencebase_item_exact_v1": (
        "/catalog/item/63d1a3c6d34e06fef15006be",
        "sciencebase_item_exact",
    ),
    "sciencebase_file_exact_v1": (
        "/catalog/file/get/63d1a3c6d34e06fef15006be",
        "sciencebase_file_exact",
    ),
    "nrc_get_document_exact_v1": (
        "/aps/api/search/ML17123A319",
        "nrc_accession_exact",
    ),
    "nrc_public_pdf_exact_v1": (
        "/docs/ML1712/ML17123A319.pdf",
        "nrc_public_pdf_exact",
    ),
}
_QUERY_CLASSES = {
    "none_v1": "none",
    "format_json_exact_v1": "format_json_exact",
    "sciencebase_exact_file_selector_v1": "exact_single_f_expected_filename",
}
_EXACT_QUERY_VALUES = {
    "none_v1": "",
    "format_json_exact_v1": "format=json",
    "sciencebase_exact_file_selector_v1": "f=mcs2023-germa_salient.csv",
}
_RESERVATION_METRIC_KEYS = frozenset(
    {
        "ordinal",
        "stage",
        "method",
        "host",
        "path_class",
        "query_class",
        "credential_audience",
        "request_fingerprint",
        "grant_sha256",
        "derived_arming_hash",
        "effective_streaming_cap",
        "remaining_aggregate_counted_byte_budget",
        "single_send_detection_allowance_bytes",
        "reserved_at",
    }
)
_COMPLETION_METRIC_KEYS = frozenset(
    {
        "ordinal",
        "stage",
        "reservation_event_id",
        "request_fingerprint",
        "outcome_class",
        "response_status",
        "byte_count",
        "body_sha256",
        "counted_status_header_bytes",
        "delivered_body_bytes",
        "decoded_body_bytes",
        "decoded_body_sha256",
        "send_started_at",
        "completed_at",
    }
)
_COUNTER_RECORD_KEYS = frozenset(
    {
        "schema_id",
        "ordinal",
        "stage",
        "request_fingerprint",
        "canonical_status_header_bytes",
        "delivered_body_bytes",
        "decoded_body_bytes",
        "decoded_body_sha256",
        "response_status",
        "error_class",
        "monotonic_started_at",
        "monotonic_stopped_at",
        "evidence_started_at",
        "evidence_stopped_at",
    }
)


class ConnectorEgressTransportError(RuntimeError):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = str(code)
        self.message = str(message or code)
        super().__init__(self.message)


@dataclass(frozen=True)
class FrozenPhysicalRequest:
    method: str
    url: str = field(repr=False)
    headers: Mapping[str, str] = field(default_factory=dict, repr=False)
    body: bytes | None = field(default=None, repr=False)
    credential_audience: str = "none"

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))
        if self.body is not None and not isinstance(self.body, bytes):
            raise TypeError("FrozenPhysicalRequest.body must be bytes or None")


@dataclass(frozen=True)
class PhysicalRequestReservation:
    connector_run_id: str
    connector_key: str
    arming_fingerprint: str
    grant_sha256: str
    ordinal: int
    stage: str
    reservation_event_id: str
    request_fingerprint: str
    method: str
    host: str
    path_class: str
    query_class: str
    credential_audience: str
    effective_streaming_cap: int
    remaining_aggregate_budget: int
    detection_allowance_bytes: int
    reserved_at: datetime
    already_reserved: bool = False


@dataclass(frozen=True)
class PhysicalRequestOutcome:
    outcome_class: str
    response_status: int | None
    byte_count: int | None
    body_sha256: str | None
    counted_status_header_bytes: int
    delivered_body_bytes: int
    decoded_body_bytes: int
    decoded_body_sha256: str | None
    send_started_at: datetime | None
    completed_at: datetime


@dataclass(frozen=True)
class VerifiedTerminalRequestLedger:
    connector_run_id: str
    entries: tuple[dict[str, Any], ...]
    ledger_terminal_hash: str
    eligible: bool
    validation_errors: tuple[str, ...]
    canonical_projection: Mapping[str, Any] = field(repr=False)


@dataclass(frozen=True)
class BoundedConnectorResponse:
    outcome_class: str
    response_status: int | None
    safe_headers: Mapping[str, str]
    body: bytes = field(repr=False)
    body_sha256: str | None
    byte_count: int | None
    location_values: tuple[str, ...] = field(repr=False)
    counted_status_header_bytes: int
    delivered_body_bytes: int


@dataclass
class _DeliveredByteCounter:
    delivered_body_bytes: int = 0


class _CountingRawReadPath:
    def __init__(self, raw: Any, counter: _DeliveredByteCounter) -> None:
        self._raw = raw
        self._counter = counter

    def read(self, *args: Any, **kwargs: Any) -> bytes:
        chunk = self._raw.read(*args, **kwargs)
        if not isinstance(chunk, (bytes, bytearray)):
            _fail("connector_egress_transport_non_bytes")
        payload = bytes(chunk)
        self._counter.delivered_body_bytes += len(payload)
        return payload

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw, name)


def _set_raw_socket_timeout(raw: Any, timeout_seconds: float) -> bool:
    target = raw._raw if isinstance(raw, _CountingRawReadPath) else raw
    candidates: list[Any] = [target]
    connection = getattr(target, "_connection", None)
    if connection is not None:
        candidates.append(getattr(connection, "sock", None))
    http_response = getattr(target, "_fp", None)
    buffered = getattr(http_response, "fp", None)
    socket_io = getattr(buffered, "raw", None)
    candidates.append(getattr(socket_io, "_sock", None))
    for candidate in candidates:
        setter = getattr(candidate, "settimeout", None)
        if not callable(setter):
            continue
        try:
            setter(max(0.001, float(timeout_seconds)))
        except (OSError, ValueError):
            return False
        return True
    return False


class CountingHTTPAdapter(HTTPAdapter):
    def __init__(
        self,
        *,
        observe_prepared: Callable[[PreparedRequest], None],
        counter: _DeliveredByteCounter,
    ) -> None:
        self._observe_prepared = observe_prepared
        self._counter = counter
        self.network_send_started = False
        super().__init__(max_retries=0)

    def send(self, request: PreparedRequest, **kwargs: Any) -> Response:
        self._observe_prepared(request)
        self.network_send_started = True
        response = super().send(request, **kwargs)
        response.raw = _CountingRawReadPath(response.raw, self._counter)
        return response


class _RejectAllCookiePolicy(DefaultCookiePolicy):
    def set_ok(self, cookie: Any, request: Any) -> bool:
        return False

    def return_ok(self, cookie: Any, request: Any) -> bool:
        return False


def _fail(code: str, message: str | None = None) -> NoReturn:
    raise ConnectorEgressTransportError(code, message)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utc_six_z(value: datetime) -> str:
    return _as_utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_utc(value: Any, *, code: str) -> datetime:
    if isinstance(value, datetime):
        return _as_utc(value)
    if not isinstance(value, str):
        _fail(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConnectorEgressTransportError(code) from exc
    if parsed.tzinfo is None:
        _fail(code)
    return parsed.astimezone(timezone.utc)


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(payload)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _event_id(
    connector_run_id: str,
    arming_fingerprint: str,
    ordinal: int,
    kind: str,
) -> str:
    name = f"project6:egress:{connector_run_id}:{arming_fingerprint}:{ordinal}:{kind}"
    return str(uuid5(NAMESPACE_URL, name))


def assert_pinned_http_parser_limits(
    *,
    maxline: int | None = None,
    maxheaders: int | None = None,
) -> None:
    observed_line = int(
        getattr(http.client, "_MAXLINE") if maxline is None else maxline
    )
    observed_headers = int(
        getattr(http.client, "_MAXHEADERS") if maxheaders is None else maxheaders
    )
    if (
        observed_line != HTTP_MAX_LINE_BYTES
        or observed_headers != HTTP_MAX_HEADER_LINES
        or GRANT_DETECTION_ALLOWANCE_BYTES != SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
    ):
        _fail("connector_egress_http_parser_limit_drift")


def aggregate_budget_crossed(
    *,
    status_header_bytes: int,
    delivered_body_bytes: int,
    remaining_budget: int,
) -> bool:
    return int(status_header_bytes) + int(delivered_body_bytes) > int(remaining_budget)


def _strict_envelope(run: ConnectorRun) -> dict[str, Any]:
    config = run.request_config_json
    if not isinstance(config, dict):
        _fail("connector_egress_arming_missing")
    envelope = config.get("connector_egress_arming")
    if not isinstance(envelope, dict):
        _fail("connector_egress_arming_missing")
    if envelope.get("schema_id") != "project6.connector_egress_arming.v1":
        _fail("connector_egress_arming_schema_mismatch")
    return dict(envelope)


def _revalidate_run_authority(
    *,
    db: Session,
    run: ConnectorRun,
    envelope: Mapping[str, Any],
    now: datetime,
) -> None:
    """Reload owner authority and prove the persisted envelope is still immutable."""
    if (
        not settings.connector_live_egress_enabled
        or not settings.connector_live_egress_exclusive_proof_mode
    ):
        _fail("connector_egress_feature_disabled")
    try:
        from app.services import connector_egress_arming as arming
    except ImportError as exc:
        raise ConnectorEgressTransportError(
            "connector_egress_authority_resolver_unavailable"
        ) from exc

    try:
        grant = arming.resolve_current_egress_authority(
            db,
            connector_run_id=run.connector_run_id,
            now=now,
        )
        campaign = grant.verified_campaign
    except arming.ConnectorEgressArmingError as exc:
        raise ConnectorEgressTransportError(
            "connector_egress_authority_revalidation_failed"
        ) from exc
    exact_bindings = (
        (
            str(getattr(campaign, "raw_sha256", "")),
            str(envelope.get("campaign_definition_sha256") or ""),
            "connector_egress_campaign_definition_digest_mismatch",
        ),
        (
            str(getattr(campaign, "canonical_fingerprint", "")),
            str(envelope.get("campaign_fingerprint") or ""),
            "connector_egress_campaign_fingerprint_mismatch",
        ),
        (
            str(getattr(campaign, "introduction_index_revision", "")),
            str(envelope.get("campaign_introduction_index_revision") or ""),
            "connector_egress_campaign_index_revision_mismatch",
        ),
        (
            str(getattr(campaign, "introduction_index_sha256", "")),
            str(envelope.get("campaign_introduction_index_sha256") or ""),
            "connector_egress_campaign_index_digest_mismatch",
        ),
        (
            str(getattr(grant, "raw_sha256", "")),
            str(envelope.get("grant_sha256") or ""),
            "connector_egress_grant_digest_mismatch",
        ),
        (
            str(getattr(grant, "canonical_fingerprint", "")),
            str(envelope.get("canonical_grant_fingerprint") or ""),
            "connector_egress_grant_fingerprint_mismatch",
        ),
    )
    for verified, persisted, code in exact_bindings:
        if not verified or verified != persisted:
            _fail(code)


def _rule_for(
    envelope: Mapping[str, Any],
    *,
    ordinal: int,
    stage: str,
) -> dict[str, Any]:
    rules = envelope.get("request_rules")
    if not isinstance(rules, (list, tuple)):
        _fail("connector_egress_request_rules_missing")
    matches = [
        dict(rule)
        for rule in rules
        if isinstance(rule, Mapping)
        and rule.get("ordinal") == ordinal
        and rule.get("stage") == stage
    ]
    if len(matches) != 1:
        _fail("connector_egress_stage_ordinal_not_authorized")
    return matches[0]


def _raw_url_has_delimiter(url: str, delimiter: str) -> bool:
    return delimiter in url


def _validate_exact_request(
    request: FrozenPhysicalRequest,
    *,
    rule: Mapping[str, Any],
) -> tuple[str, str, str]:
    raw_url = request.url
    if not isinstance(raw_url, str) or not raw_url or raw_url.strip() != raw_url:
        _fail("connector_egress_url_invalid")
    if any(ord(char) < 0x20 or ord(char) > 0x7E for char in raw_url):
        _fail("connector_egress_url_invalid")
    if "\\" in raw_url or _raw_url_has_delimiter(raw_url, "#"):
        _fail("connector_egress_url_invalid")
    parsed = urlsplit(raw_url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        _fail("connector_egress_url_invalid")
    try:
        parsed_port = parsed.port
        host = str(parsed.hostname or "").lower()
    except ValueError as exc:
        raise ConnectorEgressTransportError("connector_egress_url_invalid") from exc
    if "@" in parsed.netloc or parsed_port not in (None, 443) or parsed.netloc != host:
        _fail("connector_egress_url_invalid")
    allowed_hosts = tuple(str(item).lower() for item in rule["allowed_hosts"])
    if host not in allowed_hosts:
        _fail("connector_egress_host_not_authorized")
    if request.method != str(rule["method"]):
        _fail("connector_egress_method_not_authorized")
    if request.credential_audience != str(rule["credential_audience"]):
        _fail("connector_egress_credential_audience_mismatch")
    safe_headers = dict(_normalized_headers(request))
    if (
        request.credential_audience == "nrc_aps_api_key"
        and "ocp-apim-subscription-key" not in safe_headers
    ):
        _fail("connector_egress_credential_header_missing")
    if request.body is not None:
        _fail("connector_egress_request_body_not_authorized")

    path_rule = str(rule["path_rule_id"])
    expected = _EXACT_PATH_RULES.get(path_rule)
    if expected is None or parsed.path != expected[0] or "%" in parsed.path:
        _fail("connector_egress_path_not_authorized")

    query_rule = str(rule["query_rule_id"])
    if query_rule not in _QUERY_CLASSES:
        _fail("connector_egress_query_not_authorized")
    if query_rule == "none_v1":
        if _raw_url_has_delimiter(raw_url, "?") or parsed.query:
            _fail("connector_egress_query_not_authorized")
        query_class = _QUERY_CLASSES[query_rule]
    else:
        expected_query = _EXACT_QUERY_VALUES[query_rule]
        if parsed.query != expected_query or raw_url.count("?") != 1:
            _fail("connector_egress_query_not_authorized")
        try:
            pairs = parse_qsl(
                parsed.query,
                keep_blank_values=True,
                strict_parsing=True,
                encoding="utf-8",
                errors="strict",
                separator="&",
            )
        except (UnicodeDecodeError, ValueError) as exc:
            raise ConnectorEgressTransportError(
                "connector_egress_query_not_authorized"
            ) from exc
        required = (
            [("format", "json")]
            if query_rule == "format_json_exact_v1"
            else [("f", "mcs2023-germa_salient.csv")]
        )
        if pairs != required:
            _fail("connector_egress_query_not_authorized")
        query_class = _QUERY_CLASSES[query_rule]
    return host, expected[1], query_class


def _normalized_headers(request: FrozenPhysicalRequest) -> tuple[tuple[str, str], ...]:
    values: dict[str, tuple[str, str]] = {}
    for raw_name, raw_value in request.headers.items():
        if not isinstance(raw_name, str) or not isinstance(raw_value, str):
            _fail("connector_egress_header_invalid")
        name = raw_name.strip()
        value = raw_value
        lowered = name.lower()
        if (
            not name
            or name != raw_name
            or any(character not in _HTTP_HEADER_TOKEN_CHARS for character in name)
            or not value
            or value.strip() != value
            or any(
                ord(character) < 0x20 or ord(character) > 0x7E for character in value
            )
        ):
            _fail("connector_egress_header_invalid")
        if lowered in values:
            _fail("connector_egress_header_duplicate")
        allowed_names = {"accept-encoding"}
        if request.credential_audience == "nrc_aps_api_key":
            allowed_names.add("ocp-apim-subscription-key")
        if lowered not in allowed_names:
            _fail("connector_egress_header_not_authorized")
        if lowered == "ocp-apim-subscription-key":
            if request.credential_audience != "nrc_aps_api_key" or not value:
                _fail("connector_egress_credential_header_invalid")
            safe_value = "<credential:nrc_aps_api_key>"
        else:
            safe_value = value
        values[lowered] = (lowered, safe_value)
    existing = values.get("accept-encoding")
    if existing is not None and existing[1].lower() != "identity":
        _fail("connector_egress_accept_encoding_invalid")
    values["accept-encoding"] = ("accept-encoding", "identity")
    return tuple(values[key] for key in sorted(values))


def secret_free_request_fingerprint(
    request: FrozenPhysicalRequest,
    *,
    arming_fingerprint: str,
    grant_sha256: str,
    ordinal: int,
    stage: str,
) -> str:
    payload = {
        "arming_fingerprint": arming_fingerprint,
        "grant_sha256": grant_sha256,
        "ordinal": ordinal,
        "stage": stage,
        "method": request.method.strip().upper(),
        "normalized_exact_url": request.url,
        "headers": [list(item) for item in _normalized_headers(request)],
        "credential_audience": request.credential_audience,
        "body_sha256": (None if request.body is None else _sha256_bytes(request.body)),
    }
    return _sha256_bytes(_canonical_json_bytes(payload))


def _validate_envelope_and_run(
    run: ConnectorRun,
    *,
    envelope: Mapping[str, Any],
    lease_token: str,
    arming_fingerprint: str,
    now: datetime,
) -> None:
    now_utc = _as_utc(now)
    if run.status != "running" or run.source_mode != "strict_live_egress":
        _fail("connector_egress_run_not_running")
    if run.connector_key != str(envelope.get("connector_key") or ""):
        _fail("connector_egress_connector_mismatch")
    if run.request_fingerprint != arming_fingerprint:
        _fail("connector_egress_run_fingerprint_mismatch")
    if str(envelope.get("arming_fingerprint") or "") != arming_fingerprint:
        _fail("connector_egress_arming_fingerprint_mismatch")
    if not lease_token or run.execution_lease_token != lease_token:
        _fail("connector_egress_lease_mismatch")
    if run.execution_lease_expires_at is None:
        _fail("connector_egress_lease_expired")
    if _as_utc(run.execution_lease_expires_at) <= now_utc:
        _fail("connector_egress_lease_expired")

    campaign_start = _parse_utc(
        envelope.get("campaign_not_before"),
        code="connector_egress_campaign_window_invalid",
    )
    campaign_end = _parse_utc(
        envelope.get("campaign_expires_at"),
        code="connector_egress_campaign_window_invalid",
    )
    grant_start = _parse_utc(
        envelope.get("grant_issued_at"),
        code="connector_egress_grant_window_invalid",
    )
    grant_end = _parse_utc(
        envelope.get("grant_expires_at"),
        code="connector_egress_grant_window_invalid",
    )
    if not campaign_start <= now_utc < campaign_end:
        _fail("connector_egress_campaign_expired")
    if not grant_start <= now_utc < grant_end:
        _fail("connector_egress_grant_expired")
    if int(envelope.get("max_single_send_detection_allowance_bytes") or -1) != (
        SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
    ):
        _fail("connector_egress_detection_allowance_mismatch")


def _reservation_from_event(
    run: ConnectorRun,
    envelope: Mapping[str, Any],
    event: ConnectorRunEvent,
    *,
    already_reserved: bool,
) -> PhysicalRequestReservation:
    metrics = event.metrics_json if isinstance(event.metrics_json, dict) else {}
    try:
        return PhysicalRequestReservation(
            connector_run_id=run.connector_run_id,
            connector_key=run.connector_key,
            arming_fingerprint=str(envelope["arming_fingerprint"]),
            grant_sha256=str(envelope["grant_sha256"]),
            ordinal=int(metrics["ordinal"]),
            stage=str(metrics["stage"]),
            reservation_event_id=event.connector_run_event_id,
            request_fingerprint=str(metrics["request_fingerprint"]),
            method=str(metrics["method"]),
            host=str(metrics["host"]),
            path_class=str(metrics["path_class"]),
            query_class=str(metrics["query_class"]),
            credential_audience=str(metrics["credential_audience"]),
            effective_streaming_cap=int(metrics["effective_streaming_cap"]),
            remaining_aggregate_budget=int(
                metrics["remaining_aggregate_counted_byte_budget"]
            ),
            detection_allowance_bytes=int(
                metrics["single_send_detection_allowance_bytes"]
            ),
            reserved_at=_parse_utc(
                metrics["reserved_at"],
                code="connector_egress_reservation_event_invalid",
            ),
            already_reserved=already_reserved,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConnectorEgressTransportError(
            "connector_egress_reservation_event_invalid"
        ) from exc


def _events_for_run(db: Session, connector_run_id: str) -> list[ConnectorRunEvent]:
    return (
        db.query(ConnectorRunEvent)
        .filter(ConnectorRunEvent.connector_run_id == connector_run_id)
        .filter(
            ConnectorRunEvent.event_type.in_(
                [RESERVATION_EVENT_TYPE, COMPLETION_EVENT_TYPE]
            )
        )
        .order_by(
            ConnectorRunEvent.created_at.asc(),
            ConnectorRunEvent.connector_run_event_id.asc(),
        )
        .all()
    )


def _ordinal_from_event(event: ConnectorRunEvent) -> int | None:
    metrics = event.metrics_json if isinstance(event.metrics_json, dict) else {}
    value = metrics.get("ordinal")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _derive_counted_prior_bytes(
    events: list[ConnectorRunEvent],
    *,
    before_ordinal: int,
) -> int:
    reservations: dict[int, ConnectorRunEvent] = {}
    completions: dict[int, ConnectorRunEvent] = {}
    for event in events:
        ordinal = _ordinal_from_event(event)
        if ordinal is None or ordinal >= before_ordinal:
            continue
        destination = (
            reservations if event.event_type == RESERVATION_EVENT_TYPE else completions
        )
        if ordinal in destination:
            _fail("connector_egress_ledger_duplicate_event")
        destination[ordinal] = event
    expected = set(range(1, before_ordinal))
    if set(reservations) != expected or set(completions) != expected:
        _fail("connector_egress_prior_reservation_unresolved")

    counted = 0
    for ordinal in sorted(expected):
        completion = completions[ordinal]
        metrics = (
            completion.metrics_json if isinstance(completion.metrics_json, dict) else {}
        )
        try:
            header_bytes = int(metrics["counted_status_header_bytes"])
            body_bytes = int(metrics["delivered_body_bytes"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ConnectorEgressTransportError(
                "connector_egress_prior_counter_unresolved"
            ) from exc
        if header_bytes < 0 or body_bytes < 0:
            _fail("connector_egress_prior_counter_unresolved")
        if metrics.get("outcome_class") != "completed":
            _fail("connector_egress_prior_outcome_not_successful")
        counted += header_bytes + body_bytes
    return counted


def _load_counter_records(
    path: Path,
    *,
    empty_is_valid: bool = False,
) -> tuple[dict[str, Any], ...]:
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        if empty_is_valid:
            return ()
        _fail("connector_egress_prior_counter_unresolved")
    except OSError as exc:
        raise ConnectorEgressTransportError(
            "connector_egress_prior_counter_unresolved"
        ) from exc
    if not payload:
        if empty_is_valid:
            return ()
        _fail("connector_egress_prior_counter_unresolved")
    if len(payload) > 1_048_576 or not payload.endswith(b"\n"):
        _fail("connector_egress_prior_counter_unresolved")

    records: list[dict[str, Any]] = []
    for raw_line in payload.splitlines():
        if not raw_line:
            _fail("connector_egress_prior_counter_unresolved")
        try:
            parsed = strict_json_loads(raw_line)
        except (TypeError, ValueError) as exc:
            raise ConnectorEgressTransportError(
                "connector_egress_prior_counter_unresolved"
            ) from exc
        if (
            not isinstance(parsed, dict)
            or set(parsed) != _COUNTER_RECORD_KEYS
            or _canonical_json_bytes(parsed) != raw_line
        ):
            _fail("connector_egress_prior_counter_unresolved")
        records.append(dict(parsed))
    return tuple(records)


def _counter_value_is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _reconcile_prior_counter_stream(
    events: list[ConnectorRunEvent],
    *,
    before_ordinal: int,
    counter_path: Path | None,
    expected_ordinals: set[int] | None = None,
) -> int:
    expected = (
        set(range(1, before_ordinal))
        if expected_ordinals is None
        else set(expected_ordinals)
    )
    expected_order = sorted(expected)
    if expected_order and expected_order != list(
        range(expected_order[0], expected_order[-1] + 1)
    ):
        _fail("connector_egress_prior_counter_unresolved")
    if counter_path is None:
        if not expected:
            return 0
        _fail("connector_egress_prior_counter_unresolved")
    records = _load_counter_records(counter_path, empty_is_valid=not expected)
    if not expected:
        return 0

    reservations: dict[int, ConnectorRunEvent] = {}
    completions: dict[int, ConnectorRunEvent] = {}
    for event in events:
        ordinal = _ordinal_from_event(event)
        if ordinal is None or ordinal not in expected:
            continue
        destination = (
            reservations if event.event_type == RESERVATION_EVENT_TYPE else completions
        )
        if ordinal in destination:
            _fail("connector_egress_prior_counter_unresolved")
        destination[ordinal] = event

    if set(reservations) != expected or set(completions) != expected:
        _fail("connector_egress_prior_counter_unresolved")

    expected_identities: list[tuple[str, int, str]] = []
    reservation_metrics_by_ordinal: dict[int, dict[str, Any]] = {}
    completion_metrics_by_ordinal: dict[int, dict[str, Any]] = {}
    for ordinal in sorted(expected):
        reservation_metrics = _event_metrics(reservations[ordinal])
        completion_metrics = _event_metrics(completions[ordinal])
        request_fingerprint = reservation_metrics.get("request_fingerprint")
        stage = reservation_metrics.get("stage")
        if (
            not isinstance(request_fingerprint, str)
            or not isinstance(stage, str)
            or completion_metrics.get("request_fingerprint")
            != request_fingerprint
            or completion_metrics.get("ordinal") != ordinal
            or completion_metrics.get("stage") != stage
        ):
            _fail("connector_egress_prior_counter_unresolved")
        expected_identities.append((request_fingerprint, ordinal, stage))
        reservation_metrics_by_ordinal[ordinal] = reservation_metrics
        completion_metrics_by_ordinal[ordinal] = completion_metrics
    expected_identity_set = set(expected_identities)
    if len(expected_identity_set) != len(expected_identities):
        _fail("connector_egress_prior_counter_unresolved")
    expected_fingerprints = {
        request_fingerprint
        for request_fingerprint, _ordinal, _stage in expected_identities
    }
    if len(expected_fingerprints) != len(expected_identities):
        _fail("connector_egress_prior_counter_unresolved")

    current_records: list[dict[str, Any]] = []
    current_record_indices: list[int] = []
    found_identities: set[tuple[str, int, str]] = set()
    for stream_index, record in enumerate(records):
        request_fingerprint = record.get("request_fingerprint")
        if request_fingerprint not in expected_fingerprints:
            continue
        identity = (
            request_fingerprint,
            record.get("ordinal"),
            record.get("stage"),
        )
        if identity not in expected_identity_set or identity in found_identities:
            _fail("connector_egress_prior_counter_unresolved")
        found_identities.add(identity)
        current_records.append(record)
        current_record_indices.append(stream_index)
    if [
        (
            record.get("request_fingerprint"),
            record.get("ordinal"),
            record.get("stage"),
        )
        for record in current_records
    ] != expected_identities:
        _fail("connector_egress_prior_counter_unresolved")
    if current_record_indices != list(
        range(
            current_record_indices[0],
            current_record_indices[0] + len(current_record_indices),
        )
    ):
        _fail("connector_egress_prior_counter_unresolved")

    counted = 0
    for ordinal, record in zip(sorted(expected), current_records, strict=True):
        reservation_metrics = reservation_metrics_by_ordinal[ordinal]
        completion_metrics = completion_metrics_by_ordinal[ordinal]

        status_header_bytes = record.get("canonical_status_header_bytes")
        delivered_body_bytes = record.get("delivered_body_bytes")
        decoded_body_bytes = record.get("decoded_body_bytes")
        monotonic_started = record.get("monotonic_started_at")
        monotonic_stopped = record.get("monotonic_stopped_at")
        expected_error = (
            None
            if completion_metrics.get("outcome_class") == "completed"
            else completion_metrics.get("outcome_class")
        )
        if (
            record.get("schema_id") != "project6.connector_http_counter.v1"
            or not _counter_value_is_nonnegative_int(status_header_bytes)
            or not _counter_value_is_nonnegative_int(delivered_body_bytes)
            or not _counter_value_is_nonnegative_int(decoded_body_bytes)
            or delivered_body_bytes != decoded_body_bytes
            or status_header_bytes
            != completion_metrics.get("counted_status_header_bytes")
            or delivered_body_bytes != completion_metrics.get("delivered_body_bytes")
            or decoded_body_bytes != completion_metrics.get("decoded_body_bytes")
            or record.get("decoded_body_sha256")
            != completion_metrics.get("decoded_body_sha256")
            or record.get("response_status")
            != completion_metrics.get("response_status")
            or record.get("error_class") != expected_error
            or isinstance(monotonic_started, bool)
            or not isinstance(monotonic_started, (int, float))
            or isinstance(monotonic_stopped, bool)
            or not isinstance(monotonic_stopped, (int, float))
            or not math.isfinite(float(monotonic_started))
            or not math.isfinite(float(monotonic_stopped))
            or float(monotonic_stopped) < float(monotonic_started)
        ):
            _fail("connector_egress_prior_counter_unresolved")
        try:
            evidence_started = _parse_utc(
                record.get("evidence_started_at"),
                code="connector_egress_prior_counter_unresolved",
            )
            evidence_stopped = _parse_utc(
                record.get("evidence_stopped_at"),
                code="connector_egress_prior_counter_unresolved",
            )
        except ConnectorEgressTransportError:
            raise
        if (
            completion_metrics.get("send_started_at") != utc_six_z(evidence_started)
            or record.get("evidence_started_at") != utc_six_z(evidence_started)
            or record.get("evidence_stopped_at") != utc_six_z(evidence_stopped)
            or completion_metrics.get("completed_at")
            != utc_six_z(evidence_stopped)
            or evidence_stopped < evidence_started
        ):
            _fail("connector_egress_prior_counter_unresolved")
        assert isinstance(status_header_bytes, int)
        assert isinstance(delivered_body_bytes, int)
        counted += status_header_bytes + delivered_body_bytes
    return counted


def _require_committed_derived_arming(
    db: Session,
    *,
    connector_run_id: str,
    ordinal: int,
    stage: str,
    rule: Mapping[str, Any],
    expected_url_sha256: str,
    host: str,
    query_class: str,
    raw_url: str,
) -> None:
    expected_payload = {
        "kind": "derived_egress_arming",
        "ordinal": ordinal,
        "stage": stage,
        "url_sha256": expected_url_sha256,
        "scheme": "https",
        "host": host,
        "port": 443,
        "path_rule_id": str(rule["path_rule_id"]),
        "query_class": query_class,
    }
    expected_event_id = str(
        uuid5(
            NAMESPACE_URL,
            (
                "project6:connector-egress:"
                f"{connector_run_id}:derived_egress_arming_created:{ordinal}"
            ),
        )
    )
    expected_policy_id = str(
        uuid5(
            NAMESPACE_URL,
            (f"project6:connector-egress:{connector_run_id}:derived-policy:{ordinal}"),
        )
    )
    events = (
        db.query(ConnectorRunEvent)
        .filter(ConnectorRunEvent.connector_run_id == connector_run_id)
        .filter(ConnectorRunEvent.event_type == "derived_egress_arming_created")
        .all()
    )
    matching_events = [
        event
        for event in events
        if isinstance(event.metrics_json, dict)
        and event.metrics_json.get("ordinal") == ordinal
    ]
    policies = (
        db.query(ConnectorPolicySnapshot)
        .filter(ConnectorPolicySnapshot.connector_run_id == connector_run_id)
        .all()
    )
    matching_policies = [
        policy
        for policy in policies
        if isinstance(policy.policy_json, dict)
        and policy.policy_json.get("kind") == "derived_egress_arming"
        and policy.policy_json.get("ordinal") == ordinal
    ]
    if not matching_events or not matching_policies:
        _fail("connector_egress_derived_arming_missing")
    if len(matching_events) != 1 or len(matching_policies) != 1:
        _fail("connector_egress_derived_arming_duplicate")
    event = matching_events[0]
    policy = matching_policies[0]
    if (
        event.connector_run_event_id != expected_event_id
        or policy.connector_policy_snapshot_id != expected_policy_id
        or event.stage != stage
        or event.metrics_json != expected_payload
        or policy.policy_json != expected_payload
        or policy.retry_matrix_json != {"automatic_retry_authorized": False}
    ):
        _fail("connector_egress_derived_arming_mismatch")
    serialized = _canonical_json_bytes(expected_payload).decode("utf-8")
    if raw_url in serialized or "://" in serialized:
        _fail("connector_egress_derived_arming_unsafe_payload")


def reserve_physical_request(
    *,
    connector_run_id: str,
    lease_token: str,
    arming_fingerprint: str,
    ordinal: int,
    stage: str,
    request: FrozenPhysicalRequest,
    expected_derived_arming_hash: str | None,
    now: datetime,
    counter_path: Path | None = None,
) -> PhysicalRequestReservation:
    assert_pinned_http_parser_limits()
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        _fail("connector_egress_ordinal_invalid")

    db = SESSION_FACTORY()
    try:
        run = (
            db.query(ConnectorRun)
            .filter(ConnectorRun.connector_run_id == connector_run_id)
            .with_for_update()
            .one_or_none()
        )
        if run is None:
            _fail("connector_egress_run_not_found")
        envelope = _strict_envelope(run)
        _validate_envelope_and_run(
            run,
            envelope=envelope,
            lease_token=lease_token,
            arming_fingerprint=arming_fingerprint,
            now=now,
        )
        _revalidate_run_authority(
            db=db,
            run=run,
            envelope=envelope,
            now=_as_utc(now),
        )

        ceiling = int(envelope.get("max_physical_requests") or 0)
        if ordinal > ceiling:
            _fail("connector_egress_ordinal_over_ceiling")
        rule = _rule_for(envelope, ordinal=ordinal, stage=stage)
        reservation_id = _event_id(
            connector_run_id,
            arming_fingerprint,
            ordinal,
            RESERVATION_EVENT_TYPE,
        )
        existing = db.get(ConnectorRunEvent, reservation_id)
        events = _events_for_run(db, connector_run_id)
        prior_counted_bytes = 0
        if existing is None:
            for event in events:
                event_ordinal = _ordinal_from_event(event)
                if event_ordinal is None:
                    _fail("connector_egress_ledger_event_invalid")
                if event_ordinal >= ordinal:
                    _fail("connector_egress_ordinal_out_of_order")
            prior_counted_bytes = _derive_counted_prior_bytes(
                events,
                before_ordinal=ordinal,
            )
            counter_counted_bytes = _reconcile_prior_counter_stream(
                events,
                before_ordinal=ordinal,
                counter_path=counter_path,
            )
            if counter_counted_bytes != prior_counted_bytes:
                _fail("connector_egress_prior_counter_unresolved")
            prior_counted_bytes = counter_counted_bytes
            prior_ledger = derive_terminal_request_ledger(
                db,
                connector_run_id=connector_run_id,
                counter_path=counter_path,
            )
            if not prior_ledger.eligible or [
                entry["ordinal"] for entry in prior_ledger.entries
            ] != list(range(1, ordinal)):
                _fail("connector_egress_prior_ledger_invalid")

        host, path_class, query_class = _validate_exact_request(
            request,
            rule=rule,
        )
        request_fingerprint = secret_free_request_fingerprint(
            request,
            arming_fingerprint=arming_fingerprint,
            grant_sha256=str(envelope.get("grant_sha256") or ""),
            ordinal=ordinal,
            stage=stage,
        )
        if expected_derived_arming_hash is not None:
            if _sha256_bytes(request.url.encode("ascii")) != (
                expected_derived_arming_hash
            ):
                _fail("connector_egress_derived_arming_mismatch")
            _require_committed_derived_arming(
                db,
                connector_run_id=connector_run_id,
                ordinal=ordinal,
                stage=stage,
                rule=rule,
                expected_url_sha256=expected_derived_arming_hash,
                host=host,
                query_class=query_class,
                raw_url=request.url,
            )
        elif ordinal > 1 and stage in {"artifact", "artifact_redirect"}:
            _fail("connector_egress_derived_arming_required")

        if existing is not None:
            reservation = _reservation_from_event(
                run,
                envelope,
                existing,
                already_reserved=True,
            )
            if (
                reservation.ordinal != ordinal
                or reservation.stage != stage
                or reservation.request_fingerprint != request_fingerprint
            ):
                _fail("connector_egress_reservation_conflict")
            return reservation

        max_run_bytes = int(envelope.get("max_run_bytes") or 0)
        remaining_budget = max_run_bytes - prior_counted_bytes
        if remaining_budget <= 0:
            _fail("connector_egress_budget_exhausted")
        stage_cap = int(rule.get("max_response_bytes") or 0)
        if stage_cap <= 0:
            _fail("connector_egress_stage_cap_invalid")
        effective_cap = min(stage_cap, remaining_budget)

        reserved_at = _as_utc(now)
        event = ConnectorRunEvent(
            connector_run_event_id=reservation_id,
            connector_run_id=connector_run_id,
            phase="egress",
            stage=stage,
            event_type=RESERVATION_EVENT_TYPE,
            status_before="running",
            status_after="running",
            reason_code="physical_request_reserved",
            metrics_json={
                "ordinal": ordinal,
                "stage": stage,
                "method": request.method.strip().upper(),
                "host": host,
                "path_class": path_class,
                "query_class": query_class,
                "credential_audience": request.credential_audience,
                "request_fingerprint": request_fingerprint,
                "grant_sha256": str(envelope.get("grant_sha256") or ""),
                "derived_arming_hash": expected_derived_arming_hash,
                "effective_streaming_cap": effective_cap,
                "remaining_aggregate_counted_byte_budget": remaining_budget,
                "single_send_detection_allowance_bytes": (
                    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
                ),
                "reserved_at": utc_six_z(reserved_at),
            },
            created_at=reserved_at,
        )
        db.add(event)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.get(ConnectorRunEvent, reservation_id)
            if existing is None:
                raise
            reservation = _reservation_from_event(
                run,
                envelope,
                existing,
                already_reserved=True,
            )
            if reservation.request_fingerprint != request_fingerprint:
                _fail("connector_egress_reservation_conflict")
            return reservation
        return _reservation_from_event(
            run,
            envelope,
            event,
            already_reserved=False,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _validate_outcome(outcome: PhysicalRequestOutcome) -> None:
    if outcome.outcome_class not in _CLOSED_OUTCOME_CLASSES:
        _fail("connector_egress_outcome_class_invalid")
    if outcome.response_status is not None and (
        isinstance(outcome.response_status, bool)
        or not 100 <= outcome.response_status <= 599
    ):
        _fail("connector_egress_response_status_invalid")
    for value in (
        outcome.counted_status_header_bytes,
        outcome.delivered_body_bytes,
        outcome.decoded_body_bytes,
    ):
        if isinstance(value, bool) or int(value) < 0:
            _fail("connector_egress_outcome_counter_invalid")
    if outcome.byte_count is not None and outcome.byte_count != (
        outcome.decoded_body_bytes
    ):
        _fail("connector_egress_outcome_body_count_mismatch")
    if outcome.body_sha256 != outcome.decoded_body_sha256:
        _fail("connector_egress_outcome_body_hash_mismatch")
    if outcome.body_sha256 is not None and not _is_sha256(outcome.body_sha256):
        _fail("connector_egress_outcome_body_hash_invalid")
    if outcome.byte_count is None and outcome.body_sha256 is not None:
        _fail("connector_egress_outcome_body_hash_without_count")
    if outcome.byte_count is not None and outcome.body_sha256 is None:
        _fail("connector_egress_outcome_body_hash_missing")
    if outcome.delivered_body_bytes != outcome.decoded_body_bytes:
        _fail("connector_egress_outcome_decoding_mismatch")
    if outcome.outcome_class == "completed" and outcome.response_status is None:
        _fail("connector_egress_completed_status_missing")
    if outcome.send_started_at is None and outcome.outcome_class not in {
        "reserved_not_sent",
        "counter_write_failed",
    }:
        _fail("connector_egress_send_started_at_missing")
    if outcome.outcome_class == "reserved_not_sent" and (
        outcome.response_status is not None
        or outcome.byte_count is not None
        or outcome.body_sha256 is not None
        or outcome.counted_status_header_bytes != 0
        or outcome.delivered_body_bytes != 0
        or outcome.decoded_body_bytes != 0
        or outcome.decoded_body_sha256 is not None
        or outcome.send_started_at is not None
    ):
        _fail("connector_egress_reserved_not_sent_counter_invalid")
    if outcome.send_started_at is not None and _as_utc(outcome.completed_at) < _as_utc(
        outcome.send_started_at
    ):
        _fail("connector_egress_completion_time_invalid")


def complete_physical_request(
    *,
    reservation: PhysicalRequestReservation,
    outcome: PhysicalRequestOutcome,
) -> None:
    _validate_outcome(outcome)
    completion_id = _event_id(
        reservation.connector_run_id,
        reservation.arming_fingerprint,
        reservation.ordinal,
        COMPLETION_EVENT_TYPE,
    )
    db = SESSION_FACTORY()
    try:
        reservation_event = db.get(
            ConnectorRunEvent,
            reservation.reservation_event_id,
        )
        if reservation_event is None:
            _fail("connector_egress_reservation_missing")
        if db.get(ConnectorRunEvent, completion_id) is not None:
            _fail("connector_egress_completion_already_exists")
        metrics = (
            reservation_event.metrics_json
            if isinstance(reservation_event.metrics_json, dict)
            else {}
        )
        expected_reservation_id = _event_id(
            reservation.connector_run_id,
            reservation.arming_fingerprint,
            reservation.ordinal,
            RESERVATION_EVENT_TYPE,
        )
        if (
            reservation.reservation_event_id != expected_reservation_id
            or reservation_event.event_type != RESERVATION_EVENT_TYPE
            or reservation_event.connector_run_id != reservation.connector_run_id
            or metrics.get("ordinal") != reservation.ordinal
            or metrics.get("stage") != reservation.stage
            or metrics.get("request_fingerprint") != reservation.request_fingerprint
            or metrics.get("method") != reservation.method
            or metrics.get("host") != reservation.host
            or metrics.get("path_class") != reservation.path_class
            or metrics.get("query_class") != reservation.query_class
            or metrics.get("credential_audience") != reservation.credential_audience
        ):
            _fail("connector_egress_reservation_conflict")
        event = ConnectorRunEvent(
            connector_run_event_id=completion_id,
            connector_run_id=reservation.connector_run_id,
            phase="egress",
            stage=reservation.stage,
            event_type=COMPLETION_EVENT_TYPE,
            status_before="running",
            status_after="running",
            reason_code=outcome.outcome_class,
            error_class=(
                None if outcome.outcome_class == "completed" else outcome.outcome_class
            ),
            metrics_json={
                "ordinal": reservation.ordinal,
                "stage": reservation.stage,
                "reservation_event_id": reservation.reservation_event_id,
                "request_fingerprint": reservation.request_fingerprint,
                "outcome_class": outcome.outcome_class,
                "response_status": outcome.response_status,
                "byte_count": outcome.byte_count,
                "body_sha256": outcome.body_sha256,
                "counted_status_header_bytes": (outcome.counted_status_header_bytes),
                "delivered_body_bytes": outcome.delivered_body_bytes,
                "decoded_body_bytes": outcome.decoded_body_bytes,
                "decoded_body_sha256": outcome.decoded_body_sha256,
                "send_started_at": (
                    None
                    if outcome.send_started_at is None
                    else utc_six_z(outcome.send_started_at)
                ),
                "completed_at": utc_six_z(outcome.completed_at),
            },
            created_at=_as_utc(outcome.completed_at),
        )
        db.add(event)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _event_metrics(event: ConnectorRunEvent) -> dict[str, Any]:
    if not isinstance(event.metrics_json, dict):
        _fail("connector_egress_ledger_event_invalid")
    return dict(event.metrics_json)


def _window_contains(
    envelope: Mapping[str, Any],
    timestamp: datetime,
) -> bool:
    campaign_start = _parse_utc(
        envelope.get("campaign_not_before"),
        code="connector_egress_campaign_window_invalid",
    )
    campaign_end = _parse_utc(
        envelope.get("campaign_expires_at"),
        code="connector_egress_campaign_window_invalid",
    )
    grant_start = _parse_utc(
        envelope.get("grant_issued_at"),
        code="connector_egress_grant_window_invalid",
    )
    grant_end = _parse_utc(
        envelope.get("grant_expires_at"),
        code="connector_egress_grant_window_invalid",
    )
    instant = _as_utc(timestamp)
    return (
        campaign_start <= instant < campaign_end and grant_start <= instant < grant_end
    )


def _validate_ledger_derived_arming(
    db: Session,
    *,
    connector_run_id: str,
    ordinal: int,
    stage: str,
    reservation_metrics: Mapping[str, Any],
    rule: Mapping[str, Any],
) -> None:
    derived_hash = reservation_metrics.get("derived_arming_hash")
    if ordinal == 1:
        if derived_hash is not None:
            raise ValueError("unexpected derived arming")
        return
    if not _is_sha256(derived_hash):
        raise ValueError("derived arming hash")

    expected_payload = {
        "kind": "derived_egress_arming",
        "ordinal": ordinal,
        "stage": stage,
        "url_sha256": derived_hash,
        "scheme": "https",
        "host": reservation_metrics["host"],
        "port": 443,
        "path_rule_id": str(rule["path_rule_id"]),
        "query_class": reservation_metrics["query_class"],
    }
    event_id = str(
        uuid5(
            NAMESPACE_URL,
            (
                "project6:connector-egress:"
                f"{connector_run_id}:derived_egress_arming_created:{ordinal}"
            ),
        )
    )
    policy_id = str(
        uuid5(
            NAMESPACE_URL,
            f"project6:connector-egress:{connector_run_id}:derived-policy:{ordinal}",
        )
    )
    event = db.get(ConnectorRunEvent, event_id)
    policy = db.get(ConnectorPolicySnapshot, policy_id)
    if (
        event is None
        or policy is None
        or event.connector_run_id != connector_run_id
        or event.phase != "execution"
        or event.stage != stage
        or event.event_type != "derived_egress_arming_created"
        or event.status_before != "running"
        or event.status_after != "running"
        or event.reason_code != "derived_url_grant_intersection"
        or event.error_class is not None
        or event.metrics_json != expected_payload
        or policy.connector_run_id != connector_run_id
        or policy.policy_json != expected_payload
        or policy.retry_matrix_json != {"automatic_retry_authorized": False}
    ):
        raise ValueError("derived arming projection mismatch")


def _validate_ledger_reservation(
    db: Session,
    *,
    connector_run_id: str,
    envelope: Mapping[str, Any],
    event: ConnectorRunEvent,
    metrics: Mapping[str, Any],
    ordinal: int,
    prior_counted_bytes: int,
) -> None:
    if (
        set(metrics) != _RESERVATION_METRIC_KEYS
        or event.phase != "egress"
        or event.event_type != RESERVATION_EVENT_TYPE
        or event.status_before != "running"
        or event.status_after != "running"
        or event.reason_code != "physical_request_reserved"
        or event.error_class is not None
    ):
        raise ValueError("reservation event shape")

    stage = metrics.get("stage")
    if not isinstance(stage, str) or event.stage != stage:
        raise ValueError("stage mismatch")
    rule = _rule_for(envelope, ordinal=ordinal, stage=stage)
    path_rule = _EXACT_PATH_RULES.get(str(rule.get("path_rule_id") or ""))
    query_class = _QUERY_CLASSES.get(str(rule.get("query_rule_id") or ""))
    allowed_hosts = tuple(str(value).lower() for value in rule.get("allowed_hosts", ()))
    host = metrics.get("host")
    if (
        metrics.get("ordinal") != ordinal
        or rule.get("scheme") != "https"
        or rule.get("port") != 443
        or not isinstance(host, str)
        or host != host.lower()
        or host not in allowed_hosts
        or metrics.get("method") != rule.get("method")
        or path_rule is None
        or metrics.get("path_class") != path_rule[1]
        or query_class is None
        or metrics.get("query_class") != query_class
        or metrics.get("credential_audience") != rule.get("credential_audience")
        or not _is_sha256(metrics.get("request_fingerprint"))
        or metrics.get("grant_sha256") != envelope.get("grant_sha256")
    ):
        raise ValueError("reservation authority identity")

    query_value = _EXACT_QUERY_VALUES[str(rule["query_rule_id"])]
    normalized_url = f"https://{host}{path_rule[0]}"
    if query_value:
        normalized_url = f"{normalized_url}?{query_value}"
    request_headers = {"Accept-Encoding": "identity"}
    if rule.get("credential_audience") == "nrc_aps_api_key":
        request_headers["Ocp-Apim-Subscription-Key"] = "<credential>"
    expected_request_fingerprint = secret_free_request_fingerprint(
        FrozenPhysicalRequest(
            method=str(rule["method"]),
            url=normalized_url,
            headers=request_headers,
            credential_audience=str(rule["credential_audience"]),
        ),
        arming_fingerprint=str(envelope.get("arming_fingerprint") or ""),
        grant_sha256=str(envelope.get("grant_sha256") or ""),
        ordinal=ordinal,
        stage=stage,
    )
    if metrics.get("request_fingerprint") != expected_request_fingerprint:
        raise ValueError("request fingerprint authority mismatch")
    if ordinal > 1 and metrics.get("derived_arming_hash") != _sha256_bytes(
        normalized_url.encode("ascii")
    ):
        raise ValueError("derived arming URL mismatch")

    max_run_bytes = int(envelope.get("max_run_bytes") or 0)
    remaining = max_run_bytes - prior_counted_bytes
    stage_cap = int(rule.get("max_response_bytes") or 0)
    if (
        remaining <= 0
        or stage_cap <= 0
        or metrics.get("remaining_aggregate_counted_byte_budget") != remaining
        or metrics.get("effective_streaming_cap") != min(stage_cap, remaining)
        or metrics.get("single_send_detection_allowance_bytes")
        != SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
    ):
        raise ValueError("reservation budget identity")

    _validate_ledger_derived_arming(
        db,
        connector_run_id=connector_run_id,
        ordinal=ordinal,
        stage=stage,
        reservation_metrics=metrics,
        rule=rule,
    )


def derive_terminal_request_ledger(
    db: Session,
    *,
    connector_run_id: str,
    counter_path: Path | None = None,
) -> VerifiedTerminalRequestLedger:
    run = db.get(ConnectorRun, connector_run_id)
    if run is None:
        _fail("connector_egress_run_not_found")
    envelope = _strict_envelope(run)
    arming_fingerprint = str(envelope.get("arming_fingerprint") or "")
    errors: list[str] = []
    if (
        run.source_mode != "strict_live_egress"
        or not _is_sha256(arming_fingerprint)
        or run.request_fingerprint != arming_fingerprint
    ):
        errors.append("run_authority_identity_invalid")
    reservations: dict[int, ConnectorRunEvent] = {}
    completions: dict[int, ConnectorRunEvent] = {}

    for event in _events_for_run(db, connector_run_id):
        ordinal = _ordinal_from_event(event)
        if ordinal is None or ordinal < 1:
            errors.append("invalid_event_ordinal")
            continue
        destination = (
            reservations if event.event_type == RESERVATION_EVENT_TYPE else completions
        )
        if ordinal in destination:
            errors.append(f"duplicate_{event.event_type}_{ordinal}")
            continue
        expected_id = _event_id(
            connector_run_id,
            arming_fingerprint,
            ordinal,
            event.event_type,
        )
        if event.connector_run_event_id != expected_id:
            errors.append(f"noncanonical_{event.event_type}_{ordinal}")
        destination[ordinal] = event

    for orphan in sorted(set(completions) - set(reservations)):
        errors.append(f"completion_without_reservation_{orphan}")
    reservation_ordinals = sorted(reservations)
    if reservation_ordinals and reservation_ordinals != list(
        range(1, reservation_ordinals[-1] + 1)
    ):
        errors.append("noncontiguous_ordinals")
    ceiling = int(envelope.get("max_physical_requests") or 0)
    if reservation_ordinals and reservation_ordinals[-1] > ceiling:
        errors.append("ordinal_over_ceiling")

    entries: list[dict[str, Any]] = []
    total_counted = 0
    for ordinal in reservation_ordinals:
        reservation_event = reservations[ordinal]
        try:
            reservation_metrics = _event_metrics(reservation_event)
            _validate_ledger_reservation(
                db,
                connector_run_id=connector_run_id,
                envelope=envelope,
                event=reservation_event,
                metrics=reservation_metrics,
                ordinal=ordinal,
                prior_counted_bytes=total_counted,
            )
            if not isinstance(reservation_metrics["reserved_at"], str):
                raise ValueError("reservation timestamp type")
            reserved_at = _parse_utc(
                reservation_metrics["reserved_at"],
                code="connector_egress_ledger_event_invalid",
            )
            if reservation_metrics["reserved_at"] != utc_six_z(reserved_at):
                raise ValueError("reservation timestamp canonicalization")
            if int(reservation_metrics["ordinal"]) != ordinal:
                raise ValueError("ordinal mismatch")
            if reservation_metrics["stage"] != reservation_event.stage:
                raise ValueError("stage mismatch")
            if utc_six_z(reservation_event.created_at) != utc_six_z(reserved_at):
                raise ValueError("reservation event time mismatch")
            if (
                int(reservation_metrics["single_send_detection_allowance_bytes"])
                != SINGLE_SEND_DETECTION_ALLOWANCE_BYTES
            ):
                raise ValueError("allowance mismatch")
        except (
            ConnectorEgressTransportError,
            KeyError,
            TypeError,
            ValueError,
        ):
            errors.append(f"invalid_reservation_{ordinal}")
            continue
        if not _window_contains(envelope, reserved_at):
            errors.append(f"reservation_outside_authority_window_{ordinal}")

        completion_event = completions.get(ordinal)
        if completion_event is None:
            outcome_class = "spent_unknown"
            completion_event_id = None
            send_started_at = None
            completed_at = None
            response_status = None
            byte_count = None
            body_sha256 = None
            errors.append(f"missing_completion_{ordinal}")
        else:
            completion_event_id = completion_event.connector_run_event_id
            try:
                completion_metrics = _event_metrics(completion_event)
                if (
                    set(completion_metrics) != _COMPLETION_METRIC_KEYS
                    or completion_event.phase != "egress"
                    or completion_event.stage != reservation_metrics["stage"]
                    or completion_event.status_before != "running"
                    or completion_event.status_after != "running"
                    or completion_metrics["ordinal"] != ordinal
                    or completion_metrics["stage"] != reservation_metrics["stage"]
                    or completion_metrics["reservation_event_id"]
                    != reservation_event.connector_run_event_id
                ):
                    raise ValueError("reservation event mismatch")
                if (
                    completion_metrics["request_fingerprint"]
                    != reservation_metrics["request_fingerprint"]
                ):
                    raise ValueError("request fingerprint mismatch")
                outcome_class = str(completion_metrics["outcome_class"])
                if outcome_class not in _CLOSED_OUTCOME_CLASSES:
                    raise ValueError("outcome class")
                if (
                    completion_event.reason_code != outcome_class
                    or completion_event.error_class
                    != (None if outcome_class == "completed" else outcome_class)
                ):
                    raise ValueError("completion event classification")
                raw_send_started_at = completion_metrics.get("send_started_at")
                if raw_send_started_at is not None and not isinstance(
                    raw_send_started_at, str
                ):
                    raise ValueError("send timestamp type")
                send_started = (
                    None
                    if raw_send_started_at is None
                    else _parse_utc(
                        raw_send_started_at,
                        code="connector_egress_ledger_event_invalid",
                    )
                )
                if send_started is not None and raw_send_started_at != utc_six_z(
                    send_started
                ):
                    raise ValueError("send timestamp canonicalization")
                if not isinstance(completion_metrics["completed_at"], str):
                    raise ValueError("completion timestamp type")
                completed = _parse_utc(
                    completion_metrics["completed_at"],
                    code="connector_egress_ledger_event_invalid",
                )
                if completion_metrics["completed_at"] != utc_six_z(completed):
                    raise ValueError("completion timestamp canonicalization")
                if utc_six_z(completion_event.created_at) != utc_six_z(completed):
                    raise ValueError("completion event time mismatch")
                if _as_utc(completion_event.created_at) < _as_utc(
                    reservation_event.created_at
                ):
                    raise ValueError("event order mismatch")
                status_value = completion_metrics.get("response_status")
                if status_value is not None and (
                    isinstance(status_value, bool)
                    or not isinstance(status_value, int)
                    or not 100 <= status_value <= 599
                ):
                    raise ValueError("response status")
                response_status = status_value
                raw_byte_count = completion_metrics.get("byte_count")
                if raw_byte_count is not None and not _counter_value_is_nonnegative_int(
                    raw_byte_count
                ):
                    raise ValueError("decoded count type")
                byte_count = raw_byte_count
                delivered = completion_metrics["delivered_body_bytes"]
                decoded = completion_metrics["decoded_body_bytes"]
                status_headers = completion_metrics["counted_status_header_bytes"]
                if not all(
                    _counter_value_is_nonnegative_int(value)
                    for value in (delivered, decoded, status_headers)
                ):
                    raise ValueError("negative counter")
                if delivered != decoded:
                    raise ValueError("identity decoding mismatch")
                if byte_count is not None and byte_count != decoded:
                    raise ValueError("decoded count mismatch")
                body_sha256 = completion_metrics.get("body_sha256")
                if body_sha256 != completion_metrics.get("decoded_body_sha256"):
                    raise ValueError("decoded hash mismatch")
                if body_sha256 is not None and not _is_sha256(body_sha256):
                    raise ValueError("decoded hash invalid")
                if (byte_count is None) != (body_sha256 is None):
                    raise ValueError("body count/hash nullability mismatch")
                if outcome_class == "completed" and response_status is None:
                    raise ValueError("completed status missing")
                if outcome_class == "reserved_not_sent" and (
                    response_status is not None
                    or byte_count is not None
                    or body_sha256 is not None
                    or status_headers != 0
                    or delivered != 0
                    or decoded != 0
                    or completion_metrics.get("decoded_body_sha256") is not None
                    or send_started is not None
                ):
                    raise ValueError("reserved_not_sent counter shape")
                total_counted += status_headers + delivered
                if outcome_class == "reserved_not_sent":
                    if send_started is not None:
                        raise ValueError("reserved_not_sent has send time")
                    errors.append(f"reserved_not_sent_{ordinal}")
                elif send_started is None:
                    outcome_class = "spent_unknown"
                    errors.append(f"missing_send_started_at_{ordinal}")
                elif not _window_contains(envelope, send_started):
                    errors.append(f"send_outside_authority_window_{ordinal}")
                if send_started is not None and send_started < reserved_at:
                    raise ValueError("send before reservation")
                if send_started is not None and completed < send_started:
                    raise ValueError("completion time")
                send_started_at = (
                    None if send_started is None else utc_six_z(send_started)
                )
                completed_at = utc_six_z(completed)
            except (
                ConnectorEgressTransportError,
                KeyError,
                TypeError,
                ValueError,
            ):
                outcome_class = "spent_unknown"
                send_started_at = None
                completed_at = None
                response_status = None
                byte_count = None
                body_sha256 = None
                errors.append(f"invalid_completion_{ordinal}")

        entries.append(
            {
                "ordinal": ordinal,
                "stage": str(reservation_metrics["stage"]),
                "reservation_event_id": (reservation_event.connector_run_event_id),
                "completion_event_id": completion_event_id,
                "reserved_at": utc_six_z(reserved_at),
                "send_started_at": send_started_at,
                "completed_at": completed_at,
                "request_fingerprint": str(reservation_metrics["request_fingerprint"]),
                "method": str(reservation_metrics["method"]),
                "host": str(reservation_metrics["host"]),
                "path_class": str(reservation_metrics["path_class"]),
                "query_class": str(reservation_metrics["query_class"]),
                "credential_audience": str(reservation_metrics["credential_audience"]),
                "outcome_class": outcome_class,
                "response_status": response_status,
                "byte_count": byte_count,
                "body_sha256": body_sha256,
            }
        )

    if reservation_ordinals:
        sent_ordinals = {
            ordinal
            for ordinal, completion in completions.items()
            if isinstance(completion.metrics_json, dict)
            and completion.metrics_json.get("send_started_at") is not None
        }
        try:
            reconciled_counted = _reconcile_prior_counter_stream(
                _events_for_run(db, connector_run_id),
                before_ordinal=reservation_ordinals[-1] + 1,
                counter_path=counter_path,
                expected_ordinals=sent_ordinals,
            )
            if reconciled_counted != total_counted:
                errors.append("counter_reconciliation_mismatch")
        except ConnectorEgressTransportError:
            errors.append("counter_reconciliation_failed")

    max_run_bytes = int(envelope.get("max_run_bytes") or 0)
    if total_counted > max_run_bytes:
        errors.append("aggregate_ceiling_crossed")
    if total_counted > max_run_bytes + SINGLE_SEND_DETECTION_ALLOWANCE_BYTES:
        errors.append("aggregate_detection_allowance_exceeded")
    if any(entry["outcome_class"] == "spent_unknown" for entry in entries):
        errors.append("spent_unknown")
    if any(entry["outcome_class"] != "completed" for entry in entries):
        errors.append("non_successful_send")

    projection = {
        "schema_id": TERMINAL_LEDGER_SCHEMA_ID,
        "connector_run_id": connector_run_id,
        "connector_key": run.connector_key,
        "campaign_fingerprint": str(envelope.get("campaign_fingerprint") or ""),
        "arming_fingerprint": arming_fingerprint,
        "grant_sha256": str(envelope.get("grant_sha256") or ""),
        "campaign_introduction_index_revision": int(
            envelope.get("campaign_introduction_index_revision") or 0
        ),
        "campaign_introduction_index_sha256": str(
            envelope.get("campaign_introduction_index_sha256") or ""
        ),
        "frozen_max_physical_requests": ceiling,
        "entries": entries,
    }
    canonical = _canonical_json_bytes(projection)
    return VerifiedTerminalRequestLedger(
        connector_run_id=connector_run_id,
        entries=tuple(entries),
        ledger_terminal_hash=_sha256_bytes(canonical),
        eligible=not errors,
        validation_errors=tuple(dict.fromkeys(errors)),
        canonical_projection=projection,
    )


def _new_isolated_session(
    adapter: CountingHTTPAdapter,
) -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.clear()
    jar = RequestsCookieJar()
    jar.set_policy(_RejectAllCookiePolicy())
    session.cookies = jar
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _default_dns_resolver(host: str, port: int) -> list[str]:
    try:
        answers = socket.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise ConnectorEgressTransportError(
            "connector_egress_dns_resolution_failed"
        ) from exc
    addresses = sorted({str(answer[4][0]) for answer in answers})
    if not addresses:
        _fail("connector_egress_dns_resolution_failed")
    return addresses


def _assert_all_addresses_public(addresses: Iterable[str]) -> None:
    found = False
    for raw in addresses:
        found = True
        try:
            address = ipaddress.ip_address(str(raw))
        except ValueError as exc:
            raise ConnectorEgressTransportError(
                "connector_egress_dns_answer_invalid"
            ) from exc
        if (
            not address.is_global
            or address.is_link_local
            or address.is_loopback
            or address.is_multicast
            or address.is_private
            or address.is_reserved
            or address.is_unspecified
        ):
            _fail("connector_egress_dns_non_public")
    if not found:
        _fail("connector_egress_dns_resolution_failed")


def _header_pairs(response: Response) -> tuple[tuple[str, str], ...]:
    headers = getattr(response.raw, "headers", None)
    if headers is None:
        headers = response.headers
    iterator = getattr(headers, "iteritems", None)
    if callable(iterator):
        raw_pairs = iterator()
    else:
        raw_pairs = headers.items()
    pairs: list[tuple[str, str]] = []
    for name, value in raw_pairs:
        pairs.append((str(name), str(value)))
    return tuple(pairs)


def _canonical_status_header_bytes(
    response: Response,
    pairs: tuple[tuple[str, str], ...],
) -> bytes:
    raw_version = getattr(response.raw, "version", 11)
    versions = {9: "0.9", 10: "1.0", 11: "1.1", 20: "2"}
    version = versions.get(raw_version)
    if version is None:
        _fail("connector_egress_http_version_invalid")
    status = int(response.status_code)
    reason = str(response.reason or "")
    lines = [f"HTTP/{version} {status} {reason}\r\n"]
    lines.extend(f"{name}: {value}\r\n" for name, value in pairs)
    lines.append("\r\n")
    try:
        return "".join(lines).encode("iso-8859-1", errors="strict")
    except UnicodeEncodeError as exc:
        raise ConnectorEgressTransportError(
            "connector_egress_header_serialization_failed"
        ) from exc


def _header_values(
    pairs: tuple[tuple[str, str], ...],
    name: str,
) -> tuple[str, ...]:
    lowered = name.lower()
    return tuple(value for key, value in pairs if key.lower() == lowered)


def _safe_header_facts(
    pairs: tuple[tuple[str, str], ...],
) -> dict[str, str]:
    facts: dict[str, str] = {}
    content_types = _header_values(pairs, "content-type")
    if len(content_types) == 1:
        facts["content_type"] = content_types[0].split(";", 1)[0].strip().lower()
    encodings = _header_values(pairs, "content-encoding")
    if len(encodings) == 1:
        facts["content_encoding"] = encodings[0].strip().lower()
    return facts


def _prepared_request_as_frozen(
    prepared: PreparedRequest,
    *,
    credential_audience: str,
) -> FrozenPhysicalRequest:
    raw_body = prepared.body
    if raw_body is None:
        body = None
    elif isinstance(raw_body, bytes):
        body = raw_body
    elif isinstance(raw_body, str):
        body = raw_body.encode("utf-8")
    else:
        _fail("connector_egress_streaming_request_body_forbidden")
    return FrozenPhysicalRequest(
        method=str(prepared.method or ""),
        url=str(prepared.url or ""),
        headers=dict(prepared.headers),
        body=body,
        credential_audience=credential_audience,
    )


def _append_counter_record(path: Path, record: Mapping[str, Any]) -> None:
    line = _canonical_json_bytes(record) + b"\n"
    try:
        with path.open("ab", buffering=0) as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise ConnectorEgressTransportError(
            "connector_egress_counter_write_failed"
        ) from exc


def _load_and_revalidate_after_reservation(
    *,
    connector_run_id: str,
    lease_token: str,
    arming_fingerprint: str,
    now: datetime,
) -> dict[str, Any]:
    db = SESSION_FACTORY()
    try:
        run = db.get(ConnectorRun, connector_run_id)
        if run is None:
            _fail("connector_egress_run_not_found")
        envelope = _strict_envelope(run)
        _validate_envelope_and_run(
            run,
            envelope=envelope,
            lease_token=lease_token,
            arming_fingerprint=arming_fingerprint,
            now=now,
        )
        _revalidate_run_authority(
            db=db,
            run=run,
            envelope=envelope,
            now=now,
        )
        return envelope
    finally:
        db.close()


def _preflight_exact_request(
    *,
    connector_run_id: str,
    lease_token: str,
    arming_fingerprint: str,
    ordinal: int,
    stage: str,
    request: FrozenPhysicalRequest,
    now: datetime,
) -> str:
    db = SESSION_FACTORY()
    try:
        run = db.get(ConnectorRun, connector_run_id)
        if run is None:
            _fail("connector_egress_run_not_found")
        envelope = _strict_envelope(run)
        _validate_envelope_and_run(
            run,
            envelope=envelope,
            lease_token=lease_token,
            arming_fingerprint=arming_fingerprint,
            now=now,
        )
        _revalidate_run_authority(
            db=db,
            run=run,
            envelope=envelope,
            now=now,
        )
        rule = _rule_for(envelope, ordinal=ordinal, stage=stage)
        host, _, _ = _validate_exact_request(request, rule=rule)
        return host
    finally:
        db.close()


def _remaining_window_seconds(
    envelope: Mapping[str, Any],
    now: datetime,
) -> float:
    now_utc = _as_utc(now)
    end = min(
        _parse_utc(
            envelope.get("campaign_expires_at"),
            code="connector_egress_campaign_window_invalid",
        ),
        _parse_utc(
            envelope.get("grant_expires_at"),
            code="connector_egress_grant_window_invalid",
        ),
    )
    return max(0.0, (end - now_utc).total_seconds())


class BoundedConnectorTransport:
    def __init__(
        self,
        *,
        connector_run_id: str,
        lease_token: str,
        arming_fingerprint: str,
        counter_path: str | Path,
        send_callable: Callable[..., Response] | None = None,
        dns_resolver: Callable[[str, int], Iterable[str]] | None = None,
        prepared_request_adapter: (
            Callable[[PreparedRequest], PreparedRequest] | None
        ) = None,
        utc_clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
        rate_state: dict[str, float] | None = None,
    ) -> None:
        assert_pinned_http_parser_limits()
        self.connector_run_id = connector_run_id
        self.lease_token = lease_token
        self.arming_fingerprint = arming_fingerprint
        self.counter_path = Path(counter_path)
        self._send_callable = send_callable
        self._dns_resolver = dns_resolver or _default_dns_resolver
        self._prepared_request_adapter = prepared_request_adapter or (
            lambda prepared: prepared
        )
        self._utc_clock = utc_clock or (lambda: datetime.now(timezone.utc))
        self._monotonic_clock = monotonic_clock or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._last_send_start = rate_state if rate_state is not None else {}
        self._authority_deadline_monotonic: float | None = None

    def _bind_authority_deadline(self, envelope: Mapping[str, Any]) -> float:
        monotonic_now = self._monotonic_clock()
        wall_now = _as_utc(self._utc_clock())
        candidate = monotonic_now + _remaining_window_seconds(envelope, wall_now)
        if self._authority_deadline_monotonic is None:
            self._authority_deadline_monotonic = candidate
        return self._authority_deadline_monotonic

    def _prepared_fingerprint(
        self,
        prepared: PreparedRequest,
        *,
        reservation: PhysicalRequestReservation,
    ) -> str:
        frozen = _prepared_request_as_frozen(
            prepared,
            credential_audience=reservation.credential_audience,
        )
        return secret_free_request_fingerprint(
            frozen,
            arming_fingerprint=reservation.arming_fingerprint,
            grant_sha256=reservation.grant_sha256,
            ordinal=reservation.ordinal,
            stage=reservation.stage,
        )

    def _complete_reserved_not_sent(
        self,
        reservation: PhysicalRequestReservation,
    ) -> None:
        complete_physical_request(
            reservation=reservation,
            outcome=PhysicalRequestOutcome(
                outcome_class="reserved_not_sent",
                response_status=None,
                byte_count=None,
                body_sha256=None,
                counted_status_header_bytes=0,
                delivered_body_bytes=0,
                decoded_body_bytes=0,
                decoded_body_sha256=None,
                send_started_at=None,
                completed_at=_as_utc(self._utc_clock()),
            ),
        )

    def _counter_record(
        self,
        *,
        reservation: PhysicalRequestReservation,
        status_header_bytes: int,
        delivered_body_bytes: int,
        decoded_body: bytes,
        response_status: int | None,
        error_class: str | None,
        monotonic_started_at: float,
        monotonic_stopped_at: float,
        evidence_started_at: datetime,
        evidence_stopped_at: datetime,
    ) -> dict[str, Any]:
        decoded_hash = (
            None
            if response_status is None and not decoded_body
            else _sha256_bytes(decoded_body)
        )
        return {
            "schema_id": "project6.connector_http_counter.v1",
            "ordinal": reservation.ordinal,
            "stage": reservation.stage,
            "request_fingerprint": reservation.request_fingerprint,
            "canonical_status_header_bytes": status_header_bytes,
            "delivered_body_bytes": delivered_body_bytes,
            "decoded_body_bytes": len(decoded_body),
            "decoded_body_sha256": decoded_hash,
            "response_status": response_status,
            "error_class": error_class,
            "monotonic_started_at": monotonic_started_at,
            "monotonic_stopped_at": monotonic_stopped_at,
            "evidence_started_at": utc_six_z(evidence_started_at),
            "evidence_stopped_at": utc_six_z(evidence_stopped_at),
        }

    def _record_terminal(
        self,
        *,
        reservation: PhysicalRequestReservation,
        outcome_class: str,
        response_status: int | None,
        status_header_bytes: int,
        delivered_body_bytes: int,
        decoded_body: bytes,
        send_started_at: datetime,
        completed_at: datetime,
    ) -> None:
        body_hash = (
            None
            if response_status is None and not decoded_body
            else _sha256_bytes(decoded_body)
        )
        complete_physical_request(
            reservation=reservation,
            outcome=PhysicalRequestOutcome(
                outcome_class=outcome_class,
                response_status=response_status,
                byte_count=(
                    None
                    if response_status is None and not decoded_body
                    else len(decoded_body)
                ),
                body_sha256=body_hash,
                counted_status_header_bytes=status_header_bytes,
                delivered_body_bytes=delivered_body_bytes,
                decoded_body_bytes=len(decoded_body),
                decoded_body_sha256=body_hash,
                send_started_at=send_started_at,
                completed_at=_as_utc(completed_at),
            ),
        )

    def _enforce_rate_interval(
        self,
        *,
        host: str,
        envelope: Mapping[str, Any],
        reservation: PhysicalRequestReservation,
    ) -> dict[str, Any]:
        minimum = max(0, int(envelope.get("min_request_interval_ms") or 0))
        prior = self._last_send_start.get(host)
        if prior is None or minimum == 0:
            return dict(envelope)
        elapsed = self._monotonic_clock() - prior
        wait_seconds = minimum / 1000.0 - elapsed
        if wait_seconds <= 0:
            return dict(envelope)
        authority_deadline = self._bind_authority_deadline(envelope)
        if wait_seconds >= authority_deadline - self._monotonic_clock():
            _fail("connector_egress_rate_interval_outside_authority")
        self._sleeper(wait_seconds)
        refreshed = _load_and_revalidate_after_reservation(
            connector_run_id=self.connector_run_id,
            lease_token=self.lease_token,
            arming_fingerprint=self.arming_fingerprint,
            now=_as_utc(self._utc_clock()),
        )
        if self._monotonic_clock() - prior < minimum / 1000.0:
            _fail("connector_egress_rate_interval_unsatisfied")
        return refreshed

    def send_once(
        self,
        *,
        ordinal: int,
        stage: str,
        request: FrozenPhysicalRequest,
        expected_derived_arming_hash: str | None = None,
    ) -> BoundedConnectorResponse:
        assert_pinned_http_parser_limits()
        host = _preflight_exact_request(
            connector_run_id=self.connector_run_id,
            lease_token=self.lease_token,
            arming_fingerprint=self.arming_fingerprint,
            ordinal=ordinal,
            stage=stage,
            request=request,
            now=_as_utc(self._utc_clock()),
        )
        _assert_all_addresses_public(self._dns_resolver(host, 443))

        reservation = reserve_physical_request(
            connector_run_id=self.connector_run_id,
            lease_token=self.lease_token,
            arming_fingerprint=self.arming_fingerprint,
            ordinal=ordinal,
            stage=stage,
            request=request,
            expected_derived_arming_hash=expected_derived_arming_hash,
            now=_as_utc(self._utc_clock()),
            counter_path=self.counter_path,
        )
        if reservation.already_reserved:
            _fail("connector_egress_reservation_already_spent")
        session: requests.Session | None = None
        try:
            envelope = _load_and_revalidate_after_reservation(
                connector_run_id=self.connector_run_id,
                lease_token=self.lease_token,
                arming_fingerprint=self.arming_fingerprint,
                now=_as_utc(self._utc_clock()),
            )
            self._bind_authority_deadline(envelope)
            envelope = self._enforce_rate_interval(
                host=reservation.host,
                envelope=envelope,
                reservation=reservation,
            )

            counter = _DeliveredByteCounter()

            def observe_prepared(prepared: PreparedRequest) -> None:
                try:
                    fingerprint = self._prepared_fingerprint(
                        prepared,
                        reservation=reservation,
                    )
                except ConnectorEgressTransportError as exc:
                    raise ConnectorEgressTransportError(
                        "connector_egress_prepared_request_mismatch"
                    ) from exc
                if fingerprint != reservation.request_fingerprint:
                    _fail("connector_egress_prepared_request_mismatch")

            adapter = CountingHTTPAdapter(
                observe_prepared=observe_prepared,
                counter=counter,
            )
            session = _new_isolated_session(adapter)
            headers = dict(request.headers)
            headers["Accept-Encoding"] = "identity"
            prepared = session.prepare_request(
                requests.Request(
                    method=request.method,
                    url=request.url,
                    headers=headers,
                    data=request.body,
                )
            )
            try:
                prepared = self._prepared_request_adapter(prepared)
            except Exception as exc:
                raise ConnectorEgressTransportError(
                    "connector_egress_prepared_request_adapter_failed"
                ) from exc
            if not isinstance(prepared, PreparedRequest):
                _fail("connector_egress_prepared_request_invalid")
            observe_prepared(prepared)
            envelope = _load_and_revalidate_after_reservation(
                connector_run_id=self.connector_run_id,
                lease_token=self.lease_token,
                arming_fingerprint=self.arming_fingerprint,
                now=_as_utc(self._utc_clock()),
            )
            authority_deadline = self._bind_authority_deadline(envelope)
            timeout_seconds = float(envelope.get("request_timeout_seconds") or 0)
            if timeout_seconds <= 0:
                _fail("connector_egress_timeout_invalid")

            send_started_at = _as_utc(self._utc_clock())
            if (
                not _window_contains(envelope, send_started_at)
                or self._monotonic_clock() >= authority_deadline
            ):
                _fail("connector_egress_send_start_outside_authority")
        except Exception as exc:
            if session is not None:
                session.close()
            self._complete_reserved_not_sent(reservation)
            if isinstance(exc, ConnectorEgressTransportError):
                raise
            raise ConnectorEgressTransportError(
                "connector_egress_pre_send_failed"
            ) from exc

        assert session is not None
        monotonic_started_at = self._monotonic_clock()
        deadline = monotonic_started_at + timeout_seconds
        self._last_send_start[reservation.host] = monotonic_started_at
        response: Response | None = None
        body = bytearray()
        response_status: int | None = None
        status_header_bytes = 0
        outcome_class = "completed"
        error_class: str | None = None
        safe_headers: dict[str, str] = {}
        location_values: tuple[str, ...] = ()

        try:
            remaining = max(0.001, deadline - self._monotonic_clock())
            if self._send_callable is None:
                response = session.send(
                    prepared,
                    allow_redirects=False,
                    stream=True,
                    timeout=(remaining, remaining),
                    verify=True,
                )
            else:
                response = self._send_callable(
                    prepared,
                    allow_redirects=False,
                    stream=True,
                    timeout=(remaining, remaining),
                    verify=True,
                    session=session,
                )
            if not isinstance(response, Response):
                _fail("connector_egress_transport_response_invalid")
            if not isinstance(response.raw, _CountingRawReadPath):
                response.raw = _CountingRawReadPath(response.raw, counter)
            response_status = int(response.status_code)
            pairs = _header_pairs(response)
            canonical_headers = _canonical_status_header_bytes(response, pairs)
            status_header_bytes = len(canonical_headers)
            safe_headers = _safe_header_facts(pairs)
            location_values = _header_values(pairs, "location")
            encodings = _header_values(pairs, "content-encoding")
            deadline_expired = self._monotonic_clock() >= deadline

            if aggregate_budget_crossed(
                status_header_bytes=status_header_bytes,
                delivered_body_bytes=0,
                remaining_budget=reservation.remaining_aggregate_budget,
            ):
                outcome_class = "oversized"
                error_class = "oversized"
            elif any(value.strip().lower() != "identity" for value in encodings):
                outcome_class = "content_encoding_rejected"
                error_class = "content_encoding_rejected"
            elif deadline_expired:
                outcome_class = "timeout"
                error_class = "timeout"
            else:
                while True:
                    remaining = deadline - self._monotonic_clock()
                    if remaining <= 0:
                        outcome_class = "timeout"
                        error_class = "timeout"
                        break
                    timeout_applied = _set_raw_socket_timeout(response.raw, remaining)
                    if self._send_callable is None and not timeout_applied:
                        outcome_class = "transport_error"
                        error_class = "transport_error"
                        break
                    chunk = response.raw.read(
                        STREAM_READ_CHUNK_BYTES,
                        decode_content=False,
                    )
                    if not chunk:
                        break
                    body.extend(chunk)
                    if len(
                        body
                    ) > reservation.effective_streaming_cap or aggregate_budget_crossed(
                        status_header_bytes=status_header_bytes,
                        delivered_body_bytes=counter.delivered_body_bytes,
                        remaining_budget=(reservation.remaining_aggregate_budget),
                    ):
                        outcome_class = "oversized"
                        error_class = "oversized"
                        break
                    if self._monotonic_clock() >= deadline:
                        outcome_class = "timeout"
                        error_class = "timeout"
                        break
        except requests.Timeout:
            outcome_class = "timeout"
            error_class = "timeout"
        except ConnectorEgressTransportError as exc:
            if (
                exc.code == "connector_egress_prepared_request_mismatch"
                and self._send_callable is None
                and not adapter.network_send_started
            ):
                session.close()
                self._complete_reserved_not_sent(reservation)
                raise
            outcome_class = "transport_error"
            error_class = "transport_error"
        except Exception:
            outcome_class = "transport_error"
            error_class = "transport_error"

        monotonic_stopped_at = self._monotonic_clock()
        evidence_stopped_at = _as_utc(self._utc_clock())
        record = self._counter_record(
            reservation=reservation,
            status_header_bytes=status_header_bytes,
            delivered_body_bytes=counter.delivered_body_bytes,
            decoded_body=bytes(body),
            response_status=response_status,
            error_class=error_class,
            monotonic_started_at=monotonic_started_at,
            monotonic_stopped_at=monotonic_stopped_at,
            evidence_started_at=send_started_at,
            evidence_stopped_at=evidence_stopped_at,
        )
        try:
            _append_counter_record(self.counter_path, record)
            self._record_terminal(
                reservation=reservation,
                outcome_class=outcome_class,
                response_status=response_status,
                status_header_bytes=status_header_bytes,
                delivered_body_bytes=counter.delivered_body_bytes,
                decoded_body=bytes(body),
                send_started_at=send_started_at,
                completed_at=evidence_stopped_at,
            )
        finally:
            if response is not None:
                response.close()
            session.cookies.clear()
            session.close()

        if outcome_class == "transport_error":
            _fail("connector_egress_transport_failed")
        if outcome_class == "timeout":
            _fail("connector_egress_transport_timeout")
        body_bytes = bytes(body)
        body_hash = (
            None
            if response_status is None and not body_bytes
            else _sha256_bytes(body_bytes)
        )
        return BoundedConnectorResponse(
            outcome_class=outcome_class,
            response_status=response_status,
            safe_headers=safe_headers,
            body=body_bytes,
            body_sha256=body_hash,
            byte_count=(
                None if response_status is None and not body_bytes else len(body_bytes)
            ),
            location_values=location_values,
            counted_status_header_bytes=status_header_bytes,
            delivered_body_bytes=counter.delivered_body_bytes,
        )
