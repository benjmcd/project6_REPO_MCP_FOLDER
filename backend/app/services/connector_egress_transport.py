from __future__ import annotations

from contextlib import contextmanager
import http.client
import ipaddress
import os
from pathlib import Path
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.cookiejar import DefaultCookiePolicy
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from urllib.parse import parse_qsl, urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

import requests  # type: ignore[import-untyped]
from requests.adapters import HTTPAdapter  # type: ignore[import-untyped]
from requests.cookies import RequestsCookieJar  # type: ignore[import-untyped]
from requests.models import PreparedRequest, Response  # type: ignore[import-untyped]
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schemas.api import (
    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES as GRANT_DETECTION_ALLOWANCE_BYTES,
)
from app.services.connector_egress_evidence import (
    COMPLETION_EVENT_TYPE,
    COUNTER_V1_KEYS as COUNTER_V1_KEYS,
    COUNTER_V1_SCHEMA_ID,
    COUNTER_V2_EXTRA_KEYS as COUNTER_V2_EXTRA_KEYS,
    COUNTER_V2_KEYS as COUNTER_V2_KEYS,
    COUNTER_V2_SCHEMA_ID,
    HTTP_MAX_HEADER_LINES,
    HTTP_MAX_LINE_BYTES,
    MAX_SINGLE_SEND_HEADER_BYTES as MAX_SINGLE_SEND_HEADER_BYTES,
    RESERVATION_EVENT_TYPE,
    SINGLE_SEND_DETECTION_ALLOWANCE_BYTES,
    STREAM_READ_CHUNK_BYTES,
    TERMINAL_LEDGER_SCHEMA_ID as TERMINAL_LEDGER_SCHEMA_ID,
    ConnectorEgressTransportError,
    CounterEvidenceError as CounterEvidenceError,
    FrozenPhysicalRequest,
    VerifiedTerminalRequestLedger as VerifiedTerminalRequestLedger,
    _as_utc,
    _canonical_json_bytes,
    _canonical_physical_request_ceiling,
    _CLOSED_OUTCOME_CLASSES,
    _derive_counted_prior_bytes,
    _event_id,
    _events_for_run,
    _EXACT_PATH_RULES,
    _EXACT_QUERY_VALUES,
    _fail,
    _is_sha256,
    _LOWERCASE_SHA256,
    _normalized_headers,
    _ordinal_from_event,
    _parse_utc,
    _reconcile_prior_counter_stream,
    _QUERY_CLASSES,
    _rule_for,
    _sha256_bytes,
    _strict_envelope,
    _window_contains,
    aggregate_budget_crossed,
    derive_terminal_request_ledger as derive_terminal_request_ledger,
    parse_connector_counter_records as parse_connector_counter_records,
    secret_free_request_fingerprint,
    utc_six_z,
)

if TYPE_CHECKING:
    from app.models import ConnectorRun, ConnectorRunEvent


def _default_session_factory() -> Session:
    from app.db.session import SessionLocal

    return SessionLocal()


SESSION_FACTORY: Callable[[], Session] = _default_session_factory


def _connector_models() -> tuple[type[Any], type[Any], type[Any]]:
    from app.models import ConnectorPolicySnapshot, ConnectorRun, ConnectorRunEvent

    return ConnectorPolicySnapshot, ConnectorRun, ConnectorRunEvent

_PHYSICAL_SEND_LOCK = threading.Lock()
_PHYSICAL_SEND_STATE = threading.local()


@contextmanager
def _serialized_physical_send() -> Iterator[None]:
    if getattr(_PHYSICAL_SEND_STATE, "active", False):
        _fail("connector_egress_send_reentry")
    with _PHYSICAL_SEND_LOCK:
        _PHYSICAL_SEND_STATE.active = True
        try:
            yield
        finally:
            _PHYSICAL_SEND_STATE.active = False


@dataclass(frozen=True, slots=True)
class ConnectorCounterRuntimeContext:
    runtime_instance_id: str
    process_boot_id: str
    append_frame: Callable[[bytes], None] = field(repr=False)
    revocation_is_set: Callable[[], bool] = field(repr=False)
    acquire_send_idle: Callable[[], None] = field(repr=False)
    release_send_idle: Callable[[], None] = field(repr=False)

    def __post_init__(self) -> None:
        try:
            runtime_id = UUID(self.runtime_instance_id)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ConnectorEgressTransportError(
                "connector_counter_runtime_context_invalid"
            ) from exc
        if (
            runtime_id.version != 4
            or str(runtime_id) != self.runtime_instance_id
            or not isinstance(self.process_boot_id, str)
            or _LOWERCASE_SHA256.fullmatch(self.process_boot_id) is None
            or any(
                not callable(callback)
                for callback in (
                    self.append_frame,
                    self.revocation_is_set,
                    self.acquire_send_idle,
                    self.release_send_idle,
                )
            )
        ):
            raise ConnectorEgressTransportError(
                "connector_counter_runtime_context_invalid"
            )


_COUNTER_RUNTIME_INSTALL_LOCK = threading.Lock()
_COUNTER_RUNTIME_CONTEXT: ConnectorCounterRuntimeContext | None = None
_COUNTER_RUNTIME_RECORDS: list[dict[str, Any]] = []


@contextmanager
def connector_counter_runtime(
    context: ConnectorCounterRuntimeContext,
) -> Iterator[ConnectorCounterRuntimeContext]:
    if type(context) is not ConnectorCounterRuntimeContext:
        _fail("connector_counter_runtime_context_invalid")
    global _COUNTER_RUNTIME_CONTEXT
    with _PHYSICAL_SEND_LOCK:
        with _COUNTER_RUNTIME_INSTALL_LOCK:
            if _COUNTER_RUNTIME_CONTEXT is not None:
                _fail("connector_counter_runtime_already_installed")
            _COUNTER_RUNTIME_CONTEXT = context
            _COUNTER_RUNTIME_RECORDS.clear()
    try:
        yield context
    finally:
        with _PHYSICAL_SEND_LOCK:
            with _COUNTER_RUNTIME_INSTALL_LOCK:
                if _COUNTER_RUNTIME_CONTEXT is context:
                    _COUNTER_RUNTIME_CONTEXT = None
                    _COUNTER_RUNTIME_RECORDS.clear()


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


_RAW_TIMEOUT_ARMED = "armed"
_RAW_TIMEOUT_NO_SOCKET = "no_socket"
_RAW_TIMEOUT_FAILED = "failed"


def _arm_raw_socket_timeout(raw: Any, timeout_seconds: float) -> str:
    target = raw._raw if isinstance(raw, _CountingRawReadPath) else raw
    candidates: list[Any] = [target]
    connection = getattr(target, "_connection", None)
    if connection is not None:
        candidates.append(getattr(connection, "sock", None))
    http_response = getattr(target, "_fp", None)
    buffered = getattr(http_response, "fp", None)
    socket_io = getattr(buffered, "raw", None)
    candidates.append(getattr(socket_io, "_sock", None))
    attempted = False
    for candidate in candidates:
        setter = getattr(candidate, "settimeout", None)
        if not callable(setter):
            continue
        attempted = True
        try:
            setter(max(0.001, float(timeout_seconds)))
        except (OSError, ValueError):
            # A rejected candidate must not short-circuit the remaining ones.
            continue
        return _RAW_TIMEOUT_ARMED
    return _RAW_TIMEOUT_FAILED if attempted else _RAW_TIMEOUT_NO_SOCKET


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


def _revalidate_run_authority(
    *,
    db: Session,
    run: ConnectorRun,
    envelope: Mapping[str, Any],
    now: datetime,
) -> None:
    """Reload owner authority and prove the persisted envelope is still immutable."""
    from app.core.config import settings as runtime_settings

    if (
        not runtime_settings.connector_live_egress_enabled
        or not runtime_settings.connector_live_egress_exclusive_proof_mode
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
    connector_policy_snapshot, _, connector_run_event = _connector_models()
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
        db.query(connector_run_event)
        .filter(connector_run_event.connector_run_id == connector_run_id)
        .filter(connector_run_event.event_type == "derived_egress_arming_created")
        .all()
    )
    matching_events = [
        event
        for event in events
        if isinstance(event.metrics_json, dict)
        and event.metrics_json.get("ordinal") == ordinal
    ]
    policies = (
        db.query(connector_policy_snapshot)
        .filter(connector_policy_snapshot.connector_run_id == connector_run_id)
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
    counter_records: Sequence[Mapping[str, Any]] | None = None,
) -> PhysicalRequestReservation:
    _, connector_run, connector_run_event = _connector_models()
    assert_pinned_http_parser_limits()
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        _fail("connector_egress_ordinal_invalid")

    db = SESSION_FACTORY()
    try:
        run = (
            db.query(connector_run)
            .filter(connector_run.connector_run_id == connector_run_id)
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

        ceiling = _canonical_physical_request_ceiling(run, envelope)
        if ordinal > ceiling:
            _fail("connector_egress_ordinal_over_ceiling")
        rule = _rule_for(envelope, ordinal=ordinal, stage=stage)
        reservation_id = _event_id(
            connector_run_id,
            arming_fingerprint,
            ordinal,
            RESERVATION_EVENT_TYPE,
        )
        events = _events_for_run(db, run=run, envelope=envelope)
        existing = db.get(connector_run_event, reservation_id)
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
                counter_records=counter_records,
            )
            if counter_counted_bytes != prior_counted_bytes:
                _fail("connector_egress_prior_counter_unresolved")
            prior_counted_bytes = counter_counted_bytes
            prior_ledger = derive_terminal_request_ledger(
                db,
                connector_run_id=connector_run_id,
                counter_path=counter_path,
                counter_records=counter_records,
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
        event = connector_run_event(
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
            existing = db.get(connector_run_event, reservation_id)
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
    _, _, connector_run_event = _connector_models()
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
            connector_run_event,
            reservation.reservation_event_id,
        )
        if reservation_event is None:
            _fail("connector_egress_reservation_missing")
        if db.get(connector_run_event, completion_id) is not None:
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
        event = connector_run_event(
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
    _, connector_run, _ = _connector_models()
    db = SESSION_FACTORY()
    try:
        run = db.get(connector_run, connector_run_id)
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
    _, connector_run, _ = _connector_models()
    db = SESSION_FACTORY()
    try:
        run = db.get(connector_run, connector_run_id)
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
        counter_path: str | Path | None = None,
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
        if counter_path is None and _COUNTER_RUNTIME_CONTEXT is None:
            _fail("connector_egress_counter_path_required")
        self.counter_path = None if counter_path is None else Path(counter_path)
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

    def _runtime_revoked(self) -> bool:
        context = _COUNTER_RUNTIME_CONTEXT
        if context is None:
            return False
        try:
            revoked = context.revocation_is_set()
        except Exception as exc:
            raise ConnectorEgressTransportError(
                "connector_egress_revocation_check_failed"
            ) from exc
        if type(revoked) is not bool:
            _fail("connector_egress_revocation_check_failed")
        return revoked

    def _acquire_send_idle(self) -> bool:
        context = _COUNTER_RUNTIME_CONTEXT
        if context is None:
            return False
        try:
            result = context.acquire_send_idle()
        except Exception as exc:
            raise ConnectorEgressTransportError(
                "connector_egress_send_idle_acquire_failed"
            ) from exc
        if result is not None:
            _fail("connector_egress_send_idle_acquire_failed")
        return True

    def _release_send_idle(self) -> None:
        context = _COUNTER_RUNTIME_CONTEXT
        if context is None:
            return
        try:
            result = context.release_send_idle()
        except Exception as exc:
            raise ConnectorEgressTransportError(
                "connector_egress_send_idle_release_failed"
            ) from exc
        if result is not None:
            _fail("connector_egress_send_idle_release_failed")

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
        record = {
            "schema_id": COUNTER_V1_SCHEMA_ID,
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
        context = _COUNTER_RUNTIME_CONTEXT
        if context is not None:
            record.update(
                schema_id=COUNTER_V2_SCHEMA_ID,
                runtime_instance_id=context.runtime_instance_id,
                process_boot_id=context.process_boot_id,
            )
        return record

    def _write_counter_record(self, record: Mapping[str, Any]) -> None:
        context = _COUNTER_RUNTIME_CONTEXT
        if context is None:
            if self.counter_path is None:  # pragma: no cover - constructor invariant
                _fail("connector_egress_counter_path_required")
            _append_counter_record(self.counter_path, record)
            return
        encoded = _canonical_json_bytes(record)
        try:
            result = context.append_frame(encoded)
        except Exception as exc:
            raise ConnectorEgressTransportError(
                "connector_egress_counter_write_failed"
            ) from exc
        if result is not None:
            _fail("connector_egress_counter_write_failed")
        _COUNTER_RUNTIME_RECORDS.append(dict(record))

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
        with _serialized_physical_send():
            if _COUNTER_RUNTIME_CONTEXT is None and self.counter_path is None:
                _fail("connector_counter_runtime_not_installed")
            return self._send_once_serialized(
                ordinal=ordinal,
                stage=stage,
                request=request,
                expected_derived_arming_hash=expected_derived_arming_hash,
            )

    def _send_once_serialized(
        self,
        *,
        ordinal: int,
        stage: str,
        request: FrozenPhysicalRequest,
        expected_derived_arming_hash: str | None,
    ) -> BoundedConnectorResponse:
        assert_pinned_http_parser_limits()
        if self._runtime_revoked():
            _fail("connector_egress_revoked")
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
        send_idle_acquired = self._acquire_send_idle()
        primary_error: BaseException | None = None
        try:
            return self._send_once_after_idle_acquired(
                ordinal=ordinal,
                stage=stage,
                request=request,
                expected_derived_arming_hash=expected_derived_arming_hash,
            )
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            if send_idle_acquired:
                try:
                    self._release_send_idle()
                except ConnectorEgressTransportError as release_error:
                    if primary_error is None:
                        raise
                    primary_error.add_note(
                        f"suppressed cleanup error: {release_error.code}"
                    )

    def _send_once_after_idle_acquired(
        self,
        *,
        ordinal: int,
        stage: str,
        request: FrozenPhysicalRequest,
        expected_derived_arming_hash: str | None,
    ) -> BoundedConnectorResponse:
        context = _COUNTER_RUNTIME_CONTEXT
        reservation_now = _as_utc(self._utc_clock())
        counter_path = self.counter_path if context is None else None
        counter_records = (
            tuple(_COUNTER_RUNTIME_RECORDS) if context is not None else None
        )
        if self._runtime_revoked():
            _fail("connector_egress_revoked")
        reservation = reserve_physical_request(
            connector_run_id=self.connector_run_id,
            lease_token=self.lease_token,
            arming_fingerprint=self.arming_fingerprint,
            ordinal=ordinal,
            stage=stage,
            request=request,
            expected_derived_arming_hash=expected_derived_arming_hash,
            now=reservation_now,
            counter_path=counter_path,
            counter_records=counter_records,
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
        physical_send_started = False
        post_release_unarmed_data = False

        try:
            remaining = max(0.001, deadline - self._monotonic_clock())
            if self._runtime_revoked():
                _fail("connector_egress_revoked")
            physical_send_started = True
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
                unarmed_read_spent = False
                while True:
                    remaining = deadline - self._monotonic_clock()
                    if remaining <= 0:
                        outcome_class = "timeout"
                        error_class = "timeout"
                        break
                    arming = _arm_raw_socket_timeout(response.raw, remaining)
                    unarmed_read = False
                    if self._send_callable is None and arming != _RAW_TIMEOUT_ARMED:
                        # urllib3 releases the connection once the declared body
                        # is delivered (response.py:787-792, :949-952), so no
                        # socket is left to arm. http/client.py:463-466 then
                        # returns b"" from the released reader (_close_conn at
                        # :483/:487 inside :475-488), which the clean break below
                        # consumes. Exactly one such read is bounded; a second is
                        # not, and a candidate that refused arming is not this
                        # case at all.
                        if arming == _RAW_TIMEOUT_FAILED or unarmed_read_spent:
                            outcome_class = "transport_error"
                            error_class = "transport_error"
                            break
                        unarmed_read_spent = True
                        unarmed_read = True
                    chunk = response.raw.read(
                        STREAM_READ_CHUNK_BYTES,
                        decode_content=False,
                    )
                    if not chunk:
                        break
                    body.extend(chunk)
                    if unarmed_read:
                        # Bytes delivered on a socket that could not be bounded.
                        # Evidence classes are closed
                        # (connector_egress_evidence.py:31-41, :887, :1234-1241),
                        # so the distinct code is raised at the terminal below.
                        outcome_class = "transport_error"
                        error_class = "transport_error"
                        post_release_unarmed_data = True
                        break
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
            if not physical_send_started and exc.code in {
                "connector_egress_revoked",
                "connector_egress_revocation_check_failed",
            }:
                session.close()
                self._complete_reserved_not_sent(reservation)
                raise
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
        counter_write_error: ConnectorEgressTransportError | None = None
        try:
            try:
                self._write_counter_record(record)
            except ConnectorEgressTransportError as exc:
                counter_write_error = exc
            self._record_terminal(
                reservation=reservation,
                outcome_class=(
                    "counter_write_failed"
                    if counter_write_error is not None
                    else outcome_class
                ),
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

        if counter_write_error is not None:
            raise counter_write_error
        if outcome_class == "transport_error":
            _fail(
                "connector_egress_transport_post_release_unarmed_data"
                if post_release_unarmed_data
                else "connector_egress_transport_failed"
            )
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
