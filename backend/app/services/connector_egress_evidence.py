from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Literal, Mapping, NoReturn, Sequence
from uuid import NAMESPACE_URL, UUID, uuid5


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
COUNTER_V1_SCHEMA_ID = "project6.connector_http_counter.v1"
COUNTER_V2_SCHEMA_ID = "project6.connector_http_counter.v2"
COUNTER_V1_KEYS = frozenset(
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
COUNTER_V2_EXTRA_KEYS = frozenset(("runtime_instance_id", "process_boot_id"))
COUNTER_V2_KEYS = COUNTER_V1_KEYS | COUNTER_V2_EXTRA_KEYS
_LOWERCASE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class ConnectorEgressTransportError(RuntimeError):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = str(code)
        self.message = str(message or code)
        super().__init__(self.message)


class CounterEvidenceError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


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
class VerifiedTerminalRequestLedger:
    connector_run_id: str
    entries: tuple[dict[str, Any], ...]
    ledger_terminal_hash: str
    eligible: bool
    validation_errors: tuple[str, ...]
    canonical_projection: Mapping[str, Any] = field(repr=False)


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


def _canonical_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_value(asdict(value))
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("canonical JSON rejects naive datetime values")
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("canonical JSON requires string object keys")
            result[key] = _canonical_value(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON rejects non-finite numbers")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"canonical JSON cannot encode {type(value).__name__}")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _strict_json_loads(value: bytes | str) -> Any:
    if isinstance(value, bytes):
        try:
            text = value.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("protected JSON must be strict UTF-8") from exc
    elif isinstance(value, str):
        text = value
    else:
        raise TypeError("strict JSON accepts bytes or str")

    def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON member: {key}")
            result[key] = item
        return result

    def _nonfinite(token: str) -> None:
        raise ValueError(f"JSON number must be finite: {token}")

    try:
        return json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=_nonfinite,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed protected JSON: {exc.msg}") from exc


def _counter_schema(record: Mapping[str, Any]) -> Literal["v1", "v2"]:
    keys = set(record)
    if record.get("schema_id") == COUNTER_V1_SCHEMA_ID and keys == COUNTER_V1_KEYS:
        return "v1"
    if record.get("schema_id") == COUNTER_V2_SCHEMA_ID and keys == COUNTER_V2_KEYS:
        return "v2"
    raise CounterEvidenceError("connector_http_counter_schema_invalid")


def _validate_v2_counter_identity(record: Mapping[str, Any]) -> tuple[str, str]:
    runtime_instance_id = record.get("runtime_instance_id")
    process_boot_id = record.get("process_boot_id")
    try:
        runtime_id = UUID(runtime_instance_id)  # type: ignore[arg-type]
    except (AttributeError, TypeError, ValueError) as exc:
        raise CounterEvidenceError("connector_http_counter_runtime_invalid") from exc
    if runtime_id.version != 4 or str(runtime_id) != runtime_instance_id:
        raise CounterEvidenceError("connector_http_counter_runtime_invalid")
    if (
        not isinstance(process_boot_id, str)
        or _LOWERCASE_SHA256.fullmatch(process_boot_id) is None
    ):
        raise CounterEvidenceError("connector_http_counter_boot_invalid")
    assert isinstance(runtime_instance_id, str)
    return runtime_instance_id, process_boot_id


def parse_connector_counter_records(
    payload: bytes,
    *,
    empty_is_valid: bool = False,
) -> tuple[dict[str, Any], ...]:
    if not isinstance(payload, bytes):
        raise CounterEvidenceError("connector_http_counter_stream_invalid")
    if not payload:
        if empty_is_valid:
            return ()
        raise CounterEvidenceError("connector_http_counter_stream_invalid")
    if len(payload) > 1_048_576 or not payload.endswith(b"\n"):
        raise CounterEvidenceError("connector_http_counter_stream_invalid")

    records: list[dict[str, Any]] = []
    expected_schema: Literal["v1", "v2"] | None = None
    expected_runtime_instance_id: str | None = None
    expected_process_boot_id: str | None = None
    for raw_line in payload.splitlines():
        if not raw_line:
            raise CounterEvidenceError("connector_http_counter_stream_invalid")
        try:
            parsed = _strict_json_loads(raw_line)
        except (TypeError, ValueError) as exc:
            raise CounterEvidenceError("connector_http_counter_record_invalid") from exc
        if not isinstance(parsed, dict):
            raise CounterEvidenceError("connector_http_counter_record_invalid")
        schema = _counter_schema(parsed)
        if _canonical_json_bytes(parsed) != raw_line:
            raise CounterEvidenceError("connector_http_counter_record_noncanonical")
        if expected_schema is None:
            expected_schema = schema
        elif schema != expected_schema:
            raise CounterEvidenceError("connector_http_counter_schema_mixed")
        if schema == "v2":
            runtime_instance_id, process_boot_id = _validate_v2_counter_identity(parsed)
            if expected_runtime_instance_id is None:
                expected_runtime_instance_id = runtime_instance_id
                expected_process_boot_id = process_boot_id
            elif runtime_instance_id != expected_runtime_instance_id:
                raise CounterEvidenceError("connector_http_counter_runtime_mixed")
            elif process_boot_id != expected_process_boot_id:
                raise CounterEvidenceError("connector_http_counter_boot_mixed")
        records.append(dict(parsed))
    return tuple(records)


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


def aggregate_budget_crossed(
    *,
    status_header_bytes: int,
    delivered_body_bytes: int,
    remaining_budget: int,
) -> bool:
    return int(status_header_bytes) + int(delivered_body_bytes) > int(remaining_budget)


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


def _connector_models() -> tuple[type[Any], type[Any], type[Any]]:
    from app.models import ConnectorPolicySnapshot, ConnectorRun, ConnectorRunEvent

    return ConnectorPolicySnapshot, ConnectorRun, ConnectorRunEvent


def _strict_envelope(run: Any) -> dict[str, Any]:
    config = run.request_config_json
    if not isinstance(config, dict):
        _fail("connector_egress_arming_missing")
    envelope = config.get("connector_egress_arming")
    if not isinstance(envelope, dict):
        _fail("connector_egress_arming_missing")
    if envelope.get("schema_id") != "project6.connector_egress_arming.v1":
        _fail("connector_egress_arming_schema_mismatch")
    return dict(envelope)


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


def _canonical_physical_request_ceiling(
    run: Any,
    envelope: Mapping[str, Any],
) -> int:
    from app.schemas.api import expected_grant_rule_payloads

    connector_key = run.connector_key
    envelope_connector_key = envelope.get("connector_key")
    stored_ceiling = envelope.get("max_physical_requests")
    if (
        not isinstance(connector_key, str)
        or connector_key != envelope_connector_key
        or isinstance(stored_ceiling, bool)
        or not isinstance(stored_ceiling, int)
    ):
        _fail("connector_egress_ledger_bound_invalid")
    try:
        canonical_ceiling = len(expected_grant_rule_payloads(connector_key))
    except (TypeError, ValueError) as exc:
        raise ConnectorEgressTransportError(
            "connector_egress_ledger_bound_invalid"
        ) from exc
    if stored_ceiling != canonical_ceiling:
        _fail("connector_egress_ledger_bound_invalid")
    return canonical_ceiling


def _events_for_run(
    db: Any,
    *,
    run: Any,
    envelope: Mapping[str, Any],
) -> tuple[Any, ...]:
    _, _, connector_run_event = _connector_models()
    max_events = _canonical_physical_request_ceiling(run, envelope) * 2
    query = (
        db.query(connector_run_event)
        .filter(connector_run_event.connector_run_id == run.connector_run_id)
        .filter(
            connector_run_event.event_type.in_(
                [RESERVATION_EVENT_TYPE, COMPLETION_EVENT_TYPE]
            )
        )
        .order_by(
            connector_run_event.created_at.asc(),
            connector_run_event.connector_run_event_id.asc(),
        )
    )
    limit_query = getattr(query, "limit", None)
    if not callable(limit_query):
        _fail("connector_egress_ledger_query_unbounded")
    events = tuple(limit_query(max_events + 1).all())
    if len(events) > max_events:
        _fail("connector_egress_ledger_event_limit_exceeded")
    if any(
        not isinstance(event, connector_run_event)
        or event.connector_run_id != run.connector_run_id
        or event.event_type not in {RESERVATION_EVENT_TYPE, COMPLETION_EVENT_TYPE}
        or not isinstance(event.created_at, datetime)
        or not isinstance(event.connector_run_event_id, str)
        for event in events
    ):
        _fail("connector_egress_ledger_event_invalid")
    if events != tuple(
        sorted(
            events,
            key=lambda event: (
                _as_utc(event.created_at),
                event.connector_run_event_id,
            ),
        )
    ):
        _fail("connector_egress_ledger_event_invalid")
    return events


def _ordinal_from_event(event: Any) -> int | None:
    metrics = event.metrics_json if isinstance(event.metrics_json, dict) else {}
    value = metrics.get("ordinal")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _derive_counted_prior_bytes(
    events: Sequence[Any],
    *,
    before_ordinal: int,
) -> int:
    reservations: dict[int, Any] = {}
    completions: dict[int, Any] = {}
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
    try:
        return parse_connector_counter_records(
            payload,
            empty_is_valid=empty_is_valid,
        )
    except CounterEvidenceError as exc:
        raise ConnectorEgressTransportError(
            "connector_egress_prior_counter_unresolved"
        ) from exc


def _validate_counter_record_sequence(
    records: Sequence[Mapping[str, Any]],
    *,
    empty_is_valid: bool,
) -> tuple[dict[str, Any], ...]:
    payload = b"".join(_canonical_json_bytes(record) + b"\n" for record in records)
    try:
        return parse_connector_counter_records(
            payload,
            empty_is_valid=empty_is_valid,
        )
    except CounterEvidenceError as exc:
        raise ConnectorEgressTransportError(
            "connector_egress_prior_counter_unresolved"
        ) from exc


def _counter_value_is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _event_metrics(event: Any) -> dict[str, Any]:
    if not isinstance(event.metrics_json, dict):
        _fail("connector_egress_ledger_event_invalid")
    return dict(event.metrics_json)


def _reconcile_prior_counter_stream(
    events: Sequence[Any],
    *,
    before_ordinal: int,
    counter_path: Path | None,
    counter_records: Sequence[Mapping[str, Any]] | None = None,
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
    if counter_path is not None and counter_records is not None:
        _fail("connector_egress_prior_counter_unresolved")
    if counter_records is not None:
        records = _validate_counter_record_sequence(
            counter_records,
            empty_is_valid=not expected,
        )
    elif counter_path is None:
        if not expected:
            return 0
        _fail("connector_egress_prior_counter_unresolved")
    else:
        records = _load_counter_records(counter_path, empty_is_valid=not expected)
    if not expected:
        return 0

    reservations: dict[int, Any] = {}
    completions: dict[int, Any] = {}
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
            or completion_metrics.get("request_fingerprint") != request_fingerprint
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
            record.get("schema_id")
            not in (COUNTER_V1_SCHEMA_ID, COUNTER_V2_SCHEMA_ID)
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
        evidence_started = _parse_utc(
            record.get("evidence_started_at"),
            code="connector_egress_prior_counter_unresolved",
        )
        evidence_stopped = _parse_utc(
            record.get("evidence_stopped_at"),
            code="connector_egress_prior_counter_unresolved",
        )
        if (
            completion_metrics.get("send_started_at") != utc_six_z(evidence_started)
            or record.get("evidence_started_at") != utc_six_z(evidence_started)
            or record.get("evidence_stopped_at") != utc_six_z(evidence_stopped)
            or completion_metrics.get("completed_at") != utc_six_z(evidence_stopped)
            or evidence_stopped < evidence_started
        ):
            _fail("connector_egress_prior_counter_unresolved")
        assert isinstance(status_header_bytes, int)
        assert isinstance(delivered_body_bytes, int)
        counted += status_header_bytes + delivered_body_bytes
    return counted


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
    db: Any,
    *,
    connector_run_id: str,
    ordinal: int,
    stage: str,
    reservation_metrics: Mapping[str, Any],
    rule: Mapping[str, Any],
) -> None:
    connector_policy_snapshot, _, connector_run_event = _connector_models()
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
    event = db.get(connector_run_event, event_id)
    policy = db.get(connector_policy_snapshot, policy_id)
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
    db: Any,
    *,
    connector_run_id: str,
    envelope: Mapping[str, Any],
    event: Any,
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
    db: Any,
    *,
    connector_run_id: str,
    counter_path: Path | None = None,
    counter_records: Sequence[Mapping[str, Any]] | None = None,
) -> VerifiedTerminalRequestLedger:
    _, connector_run, _ = _connector_models()
    run = db.get(connector_run, connector_run_id)
    if run is None:
        _fail("connector_egress_run_not_found")
    envelope = _strict_envelope(run)
    ceiling = _canonical_physical_request_ceiling(run, envelope)
    events = _events_for_run(db, run=run, envelope=envelope)
    arming_fingerprint = str(envelope.get("arming_fingerprint") or "")
    errors: list[str] = []
    if (
        run.source_mode != "strict_live_egress"
        or not _is_sha256(arming_fingerprint)
        or run.request_fingerprint != arming_fingerprint
    ):
        errors.append("run_authority_identity_invalid")
    reservations: dict[int, Any] = {}
    completions: dict[int, Any] = {}

    for event in events:
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
        except (ConnectorEgressTransportError, KeyError, TypeError, ValueError):
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
            except (ConnectorEgressTransportError, KeyError, TypeError, ValueError):
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
                "reservation_event_id": reservation_event.connector_run_event_id,
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
                events,
                before_ordinal=reservation_ordinals[-1] + 1,
                counter_path=counter_path,
                counter_records=counter_records,
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
