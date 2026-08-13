from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
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

MAX_PROTECTED_JSON_BYTES = 64 * 1024
MAX_EVIDENCE_INDEX_REVISIONS = 128
MAX_CAPTURE_STREAM_BYTES = 16 * 1024 * 1024
MAX_CAPTURE_AGGREGATE_BYTES = 32 * 1024 * 1024
MAX_STREAM_BYTES = MAX_CAPTURE_STREAM_BYTES
MAX_AGGREGATE_BYTES = MAX_CAPTURE_AGGREGATE_BYTES
_EXPECTED_CONNECTORS = frozenset(("nrc_adams_aps", "sciencebase_mcs"))
_EXPECTED_CAPTURE_FILES = ("app.jsonl", "http.jsonl", "stdout.log", "stderr.log")
_DRIVE_FIXED = 3
_WINDOWS_RESERVED_COMPONENTS = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)


class ConnectorEgressTransportError(RuntimeError):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = str(code)
        self.message = str(message or code)
        super().__init__(self.message)


class CounterEvidenceError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ConnectorEvidenceError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class VerifiedEvidenceIndexRevision:
    model: Any
    raw_bytes: bytes
    raw_sha256: str
    path: Path


@dataclass(frozen=True, slots=True)
class VerifiedEvidenceIndexChain:
    evidence_root: Path
    head: Any
    head_raw_sha256: str
    head_path: Path
    revisions: tuple[VerifiedEvidenceIndexRevision, ...]


@dataclass(frozen=True, slots=True)
class VerifiedHistoricalGrantEvidence:
    definition_model: Any
    model: Any
    raw_definition_sha256: str
    canonical_campaign_fingerprint: str
    raw_sha256: str
    canonical_fingerprint: str
    introduction_index_revision: int
    introduction_index_sha256: str
    definition_archive_path: Path
    grant_archive_path: Path
    marker_model: Any
    consumption_marker_path: Path
    consumption_marker_sha256: str
    index_chain: VerifiedEvidenceIndexChain


@dataclass(frozen=True, slots=True)
class VerifiedCampaignLogCapture:
    manifest_bytes: bytes
    manifest_sha256: str
    file_set_hash: str
    seal_bytes: bytes
    seal_sha256: str
    stream_bytes: Mapping[str, bytes]
    seal_event_ids: tuple[str, ...]
    stable_snapshot: tuple[tuple[str, int, str], ...]


@dataclass(frozen=True, slots=True)
class _EvidenceFileSnapshot:
    relative_path: str
    data: bytes
    size: int
    sha256: str
    identity: tuple[int, int, int, int]


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
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _canonical_value(model_dump(mode="python"))
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


canonical_json_bytes = _canonical_json_bytes


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


strict_json_loads = _strict_json_loads


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


def _evidence_fail(code: str) -> NoReturn:
    raise ConnectorEvidenceError(code)


def _safe_evidence_relative(value: object) -> str:
    raw = str(value or "").replace("\\", "/")
    if (
        not raw
        or raw.startswith("/")
        or raw.endswith("/")
        or "//" in raw
        or ":" in raw
        or "\x00" in raw
        or any(ord(character) < 32 for character in raw)
    ):
        _evidence_fail("connector_evidence_path_invalid")
    parts = PurePosixPath(raw).parts
    if any(part in {"", ".", ".."} for part in parts):
        _evidence_fail("connector_evidence_path_invalid")
    return "/".join(parts)


def _lexical_fixed_local_evidence_path(value: object) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        _evidence_fail("connector_evidence_path_invalid")
    text = os.fspath(value)
    if not isinstance(text, str) or not text or text != text.strip() or "\x00" in text:
        _evidence_fail("connector_evidence_path_invalid")
    if os.name != "nt":
        path = Path(text)
        if not path.is_absolute() or text.startswith("//"):
            _evidence_fail("connector_evidence_path_invalid")
        posix_path = PurePosixPath(text)
        if any(part in {"", ".", ".."} for part in posix_path.parts[1:]):
            _evidence_fail("connector_evidence_path_invalid")
        return path
    normalized = text.replace("/", "\\")
    folded = normalized.casefold()
    if (
        folded.startswith(("\\\\", "\\??\\", "globalroot\\"))
        or re.fullmatch(r"[A-Za-z]:\\.*", normalized) is None
        or ":" in normalized[2:]
    ):
        _evidence_fail("connector_evidence_path_invalid")
    windows_path = PureWindowsPath(normalized)
    if not windows_path.is_absolute() or len(windows_path.drive) != 2:
        _evidence_fail("connector_evidence_path_invalid")
    for component in windows_path.parts[1:]:
        if (
            component in {"", ".", ".."}
            or component.endswith((" ", "."))
            or any(character in component for character in '*?"<>|')
            or component.split(".", 1)[0].upper() in _WINDOWS_RESERVED_COMPONENTS
        ):
            _evidence_fail("connector_evidence_path_invalid")
    import ctypes
    from ctypes import wintypes

    get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
    get_drive_type.argtypes = (wintypes.LPCWSTR,)
    get_drive_type.restype = wintypes.UINT
    if get_drive_type(f"{windows_path.drive}\\") != _DRIVE_FIXED:
        _evidence_fail("connector_evidence_path_invalid")
    return Path(normalized)


def _reparse(info: os.stat_result) -> bool:
    return bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _assert_existing_path_chain(path: Path) -> Path:
    path = _lexical_fixed_local_evidence_path(path)
    ordered = [Path(path.anchor)]
    ordered.extend(reversed(path.parents[:-1]))
    ordered.append(path)
    for component in ordered:
        try:
            info = component.lstat()
        except OSError as exc:
            raise ConnectorEvidenceError("connector_evidence_path_invalid") from exc
        if stat.S_ISLNK(info.st_mode) or _reparse(info):
            _evidence_fail("connector_evidence_path_invalid")
    return path


def _path_identity(value: Path) -> str:
    return os.path.normcase(os.path.normpath(str(value)))


def _opened_fixed_local_evidence_path(handle: Any) -> Path:
    if os.name != "nt":
        return _lexical_fixed_local_evidence_path(handle.name)
    import ctypes
    from ctypes import wintypes
    import msvcrt

    get_final_path = ctypes.windll.kernel32.GetFinalPathNameByHandleW
    get_final_path.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    get_final_path.restype = wintypes.DWORD
    native_handle = msvcrt.get_osfhandle(handle.fileno())
    capacity = 512
    while True:
        buffer = ctypes.create_unicode_buffer(capacity)
        length = get_final_path(
            wintypes.HANDLE(native_handle),
            buffer,
            capacity,
            0,
        )
        if length == 0:
            _evidence_fail("connector_evidence_path_invalid")
        if length < capacity:
            final = buffer.value
            break
        capacity = int(length) + 1
        if capacity > 32_768:
            _evidence_fail("connector_evidence_path_invalid")
    if final.casefold().startswith("\\\\?\\unc\\"):
        _evidence_fail("connector_evidence_path_invalid")
    if final.startswith("\\\\?\\"):
        final = final[4:]
    return _lexical_fixed_local_evidence_path(final)


def _assert_opened_evidence_path(handle: Any, expected_path: Path) -> None:
    opened = _opened_fixed_local_evidence_path(handle)
    if _path_identity(opened) != _path_identity(expected_path):
        _evidence_fail("connector_evidence_path_invalid")


def _evidence_root(settings: Any) -> Path:
    root = _assert_existing_path_chain(
        Path(settings.connector_campaign_evidence_root)
    )
    if not root.is_dir():
        _evidence_fail("connector_evidence_root_invalid")
    return root


def _evidence_path(root: Path, relative: object) -> tuple[Path, str]:
    normalized = _safe_evidence_relative(relative)
    path = root.joinpath(*PurePosixPath(normalized).parts)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ConnectorEvidenceError("connector_evidence_path_escape") from exc
    path = _assert_existing_path_chain(path)
    return path, normalized


def _file_identity(value: os.stat_result) -> tuple[int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def _read_evidence_file(
    root: Path,
    relative: object,
    *,
    max_bytes: int,
) -> _EvidenceFileSnapshot:
    path, normalized = _evidence_path(root, relative)
    before = path.lstat()
    if _reparse(before) or not stat.S_ISREG(before.st_mode):
        _evidence_fail("connector_evidence_file_invalid")
    if before.st_size < 0 or before.st_size > max_bytes:
        _evidence_fail("connector_evidence_file_oversized")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        _assert_opened_evidence_path(handle, path)
        if _file_identity(opened) != _file_identity(before):
            _evidence_fail("connector_evidence_file_changed")
        data = handle.read(max_bytes + 1)
        after = os.fstat(handle.fileno())
    final = path.lstat()
    if (
        len(data) > max_bytes
        or _file_identity(before) != _file_identity(after)
        or _file_identity(after) != _file_identity(final)
    ):
        _evidence_fail("connector_evidence_file_changed")
    return _EvidenceFileSnapshot(
        relative_path=normalized,
        data=data,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        identity=_file_identity(final),
    )


def _parse_evidence_model(snapshot: _EvidenceFileSnapshot, model_type: Any) -> Any:
    try:
        payload = _strict_json_loads(snapshot.data)
        if not isinstance(payload, dict):
            raise ValueError("root")
        model = model_type.model_validate(payload)
    except (TypeError, ValueError) as exc:
        raise ConnectorEvidenceError("connector_evidence_json_invalid") from exc
    if snapshot.data != _canonical_json_bytes(model):
        _evidence_fail("connector_evidence_json_noncanonical")
    return model


def _campaign_key(value: Any) -> tuple[str, str]:
    return str(value.campaign_id), str(value.campaign_fingerprint)


def _validate_slice(index: Any) -> None:
    definitions = list(index.campaigns)
    entries = list(index.entries)
    captures = list(index.log_captures)
    keys = [_campaign_key(item) for item in definitions]
    if not keys or len(keys) != len(set(keys)):
        _evidence_fail("connector_evidence_index_slice_invalid")
    referenced: list[str] = []
    for definition in definitions:
        key = _campaign_key(definition)
        matched_entries = [item for item in entries if _campaign_key(item) == key]
        matched_captures = [item for item in captures if _campaign_key(item) == key]
        if (
            len(matched_entries) != 2
            or {item.connector_key for item in matched_entries} != _EXPECTED_CONNECTORS
            or len(matched_captures) != 1
        ):
            _evidence_fail("connector_evidence_index_slice_invalid")
        definition_path = _safe_evidence_relative(definition.definition_relative_path)
        if definition_path != f"campaigns/{definition.raw_definition_sha256}.json":
            _evidence_fail("connector_evidence_index_slice_invalid")
        referenced.append(definition_path)
        for entry in matched_entries:
            grant_path = _safe_evidence_relative(entry.grant_relative_path)
            marker_path = _safe_evidence_relative(entry.consumption_marker_relative_path)
            if (
                entry.campaign_definition_sha256 != definition.raw_definition_sha256
                or entry.code_revision != definition.code_revision
                or grant_path != f"grants/{entry.raw_grant_sha256}.json"
                or marker_path != f"consumed/{entry.raw_grant_sha256}.json"
            ):
                _evidence_fail("connector_evidence_index_slice_invalid")
            referenced.extend((grant_path, marker_path))
        capture = matched_captures[0]
        expected_log = f"logs/{definition.campaign_fingerprint}"
        if (
            capture.campaign_definition_sha256 != definition.raw_definition_sha256
            or capture.code_revision != definition.code_revision
            or _safe_evidence_relative(capture.log_dir_relative_path) != expected_log
            or _safe_evidence_relative(capture.manifest_relative_path)
            != f"{expected_log}/manifest.json"
            or _safe_evidence_relative(capture.seal_relative_path)
            != f"log-seals/{definition.campaign_fingerprint}.json"
        ):
            _evidence_fail("connector_evidence_index_slice_invalid")
        referenced.extend(
            (
                capture.log_dir_relative_path,
                capture.manifest_relative_path,
                capture.seal_relative_path,
            )
        )
    if (
        any(_campaign_key(item) not in set(keys) for item in entries + captures)
        or len({item.casefold() for item in referenced}) != len(referenced)
    ):
        _evidence_fail("connector_evidence_index_slice_invalid")


def _validate_successor(
    predecessor: VerifiedEvidenceIndexRevision,
    successor: VerifiedEvidenceIndexRevision,
) -> None:
    previous = predecessor.model
    current = successor.model
    if (
        current.revision != previous.revision + 1
        or current.predecessor_index_sha256 != predecessor.raw_sha256
        or _safe_evidence_relative(current.predecessor_index_relative_path)
        != f"indexes/{predecessor.raw_sha256}.json"
        or current.campaigns[:-1] != previous.campaigns
        or current.entries[:-2] != previous.entries
        or current.log_captures[:-1] != previous.log_captures
        or len(current.campaigns) != len(previous.campaigns) + 1
        or len(current.entries) != len(previous.entries) + 2
        or len(current.log_captures) != len(previous.log_captures) + 1
    ):
        _evidence_fail("connector_evidence_index_not_linear")


def load_evidence_index_chain_read_only(settings: Any) -> VerifiedEvidenceIndexChain:
    from app.schemas.api import ConnectorCampaignEvidenceIndexV1

    root = _evidence_root(settings)
    head_sha256 = str(settings.connector_campaign_evidence_index_sha256 or "")
    if not _LOWERCASE_SHA256.fullmatch(head_sha256):
        _evidence_fail("connector_evidence_index_head_invalid")
    configured = Path(settings.connector_campaign_evidence_index_path)
    expected = root / "indexes" / f"{head_sha256}.json"
    if not configured.is_absolute() or os.path.normcase(str(configured)) != os.path.normcase(
        str(expected)
    ):
        _evidence_fail("connector_evidence_index_head_invalid")
    indexes = root / "indexes"
    _assert_existing_path_chain(indexes)
    children = tuple(indexes.iterdir())
    if not children or len(children) > MAX_EVIDENCE_INDEX_REVISIONS:
        _evidence_fail("connector_evidence_index_count_invalid")
    if len({child.name.casefold() for child in children}) != len(children):
        _evidence_fail("connector_evidence_index_name_invalid")
    objects: dict[str, VerifiedEvidenceIndexRevision] = {}
    revisions: dict[int, str] = {}
    for child in children:
        digest = child.name[:-5] if child.name.endswith(".json") else ""
        if not _LOWERCASE_SHA256.fullmatch(digest):
            _evidence_fail("connector_evidence_index_name_invalid")
        snapshot = _read_evidence_file(
            root,
            f"indexes/{child.name}",
            max_bytes=MAX_PROTECTED_JSON_BYTES,
        )
        if snapshot.sha256 != digest:
            _evidence_fail("connector_evidence_index_digest_invalid")
        model = _parse_evidence_model(snapshot, ConnectorCampaignEvidenceIndexV1)
        _validate_slice(model)
        if digest in objects or int(model.revision) in revisions:
            _evidence_fail("connector_evidence_index_revision_invalid")
        item = VerifiedEvidenceIndexRevision(
            model=model,
            raw_bytes=snapshot.data,
            raw_sha256=digest,
            path=child,
        )
        objects[digest] = item
        revisions[int(model.revision)] = digest
    head = objects.get(head_sha256)
    if head is None or int(head.model.revision) != max(revisions):
        _evidence_fail("connector_evidence_index_head_invalid")
    descending: list[VerifiedEvidenceIndexRevision] = []
    seen: set[str] = set()
    current = head
    while True:
        if current.raw_sha256 in seen:
            _evidence_fail("connector_evidence_index_not_linear")
        descending.append(current)
        seen.add(current.raw_sha256)
        if int(current.model.revision) == 1:
            if (
                current.model.predecessor_index_sha256 is not None
                or current.model.predecessor_index_relative_path is not None
            ):
                _evidence_fail("connector_evidence_index_not_linear")
            break
        predecessor = objects.get(str(current.model.predecessor_index_sha256))
        if predecessor is None:
            _evidence_fail("connector_evidence_index_not_linear")
        current = predecessor
    if seen != set(objects):
        _evidence_fail("connector_evidence_index_not_linear")
    ascending = tuple(reversed(descending))
    if tuple(int(item.model.revision) for item in ascending) != tuple(
        range(1, len(ascending) + 1)
    ):
        _evidence_fail("connector_evidence_index_not_linear")
    if (
        len(ascending[0].model.campaigns) != 1
        or len(ascending[0].model.entries) != 2
        or len(ascending[0].model.log_captures) != 1
    ):
        _evidence_fail("connector_evidence_index_not_linear")
    for index in range(1, len(ascending)):
        _validate_successor(ascending[index - 1], ascending[index])
    return VerifiedEvidenceIndexChain(
        evidence_root=root,
        head=head.model,
        head_raw_sha256=head_sha256,
        head_path=head.path,
        revisions=ascending,
    )


def _find_campaign_refs(
    chain: VerifiedEvidenceIndexChain,
    campaign_id: str,
    campaign_fingerprint: str,
) -> tuple[Any, tuple[Any, ...], Any]:
    key = (campaign_id, campaign_fingerprint)
    definitions = [item for item in chain.head.campaigns if _campaign_key(item) == key]
    entries = [item for item in chain.head.entries if _campaign_key(item) == key]
    captures = [item for item in chain.head.log_captures if _campaign_key(item) == key]
    if (
        len(definitions) != 1
        or len(entries) != 2
        or {item.connector_key for item in entries} != _EXPECTED_CONNECTORS
        or len(captures) != 1
    ):
        _evidence_fail("connector_evidence_campaign_slice_missing")
    return definitions[0], tuple(entries), captures[0]


def _introduction(
    chain: VerifiedEvidenceIndexChain,
    campaign_id: str,
    campaign_fingerprint: str,
) -> VerifiedEvidenceIndexRevision:
    key = (campaign_id, campaign_fingerprint)
    for revision in chain.revisions:
        if any(_campaign_key(item) == key for item in revision.model.campaigns):
            _find_campaign_refs(
                VerifiedEvidenceIndexChain(
                    evidence_root=chain.evidence_root,
                    head=revision.model,
                    head_raw_sha256=revision.raw_sha256,
                    head_path=revision.path,
                    revisions=chain.revisions[: int(revision.model.revision)],
                ),
                campaign_id,
                campaign_fingerprint,
            )
            return revision
    _evidence_fail("connector_evidence_campaign_introduction_missing")


def _archived_model(
    chain: VerifiedEvidenceIndexChain,
    relative_path: object,
    expected_sha256: str,
    model_type: Any,
) -> tuple[Path, bytes, Any, str]:
    snapshot = _read_evidence_file(
        chain.evidence_root,
        relative_path,
        max_bytes=MAX_PROTECTED_JSON_BYTES,
    )
    if snapshot.sha256 != expected_sha256:
        _evidence_fail("connector_evidence_archive_digest_invalid")
    model = _parse_evidence_model(snapshot, model_type)
    canonical_hash = hashlib.sha256(_canonical_json_bytes(model)).hexdigest()
    return (
        chain.evidence_root.joinpath(*PurePosixPath(snapshot.relative_path).parts),
        snapshot.data,
        model,
        canonical_hash,
    )


def resolve_historical_connector_grant_evidence_read_only(
    settings: Any,
    *,
    connector_key: str,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    expected_grant_sha256: str,
) -> VerifiedHistoricalGrantEvidence:
    from app.schemas.api import (
        ConnectorEgressGrantV1,
        ConnectorGrantConsumptionMarkerV1,
        DualLiveCampaignDefinitionV1,
        expected_grant_rule_payloads,
    )

    if (
        connector_key not in _EXPECTED_CONNECTORS
        or not _LOWERCASE_SHA256.fullmatch(expected_campaign_fingerprint)
        or not _LOWERCASE_SHA256.fullmatch(expected_grant_sha256)
    ):
        _evidence_fail("connector_evidence_historical_input_invalid")
    chain = load_evidence_index_chain_read_only(settings)
    definition_ref, entries, _capture_ref = _find_campaign_refs(
        chain,
        campaign_id,
        expected_campaign_fingerprint,
    )
    matches = [
        item
        for item in entries
        if item.connector_key == connector_key
        and item.raw_grant_sha256 == expected_grant_sha256
    ]
    if len(matches) != 1:
        _evidence_fail("connector_evidence_historical_grant_missing")
    entry = matches[0]
    definition_path, definition_bytes, definition, campaign_hash = _archived_model(
        chain,
        definition_ref.definition_relative_path,
        definition_ref.raw_definition_sha256,
        DualLiveCampaignDefinitionV1,
    )
    if (
        str(definition.campaign_id) != campaign_id
        or campaign_hash != expected_campaign_fingerprint
        or definition.code_revision != definition_ref.code_revision
    ):
        _evidence_fail("connector_evidence_definition_invalid")
    grant_path, grant_bytes, grant, grant_hash = _archived_model(
        chain,
        entry.grant_relative_path,
        expected_grant_sha256,
        ConnectorEgressGrantV1,
    )
    expected_rules = expected_grant_rule_payloads(connector_key)
    actual_rules = tuple(item.model_dump(mode="python") for item in grant.request_rules)
    expected_target = (
        definition.sciencebase_target
        if connector_key == "sciencebase_mcs"
        else definition.nrc_target
    )
    if (
        grant.connector_key != connector_key
        or grant.campaign_id != campaign_id
        or grant.campaign_fingerprint != expected_campaign_fingerprint
        or grant.campaign_definition_sha256 != definition_ref.raw_definition_sha256
        or grant.code_revision != definition.code_revision
        or grant_hash != entry.canonical_grant_fingerprint
        or grant.target != expected_target
        or actual_rules != expected_rules
        or grant.issued_at < definition.not_before
        or grant.expires_at > definition.expires_at
    ):
        _evidence_fail("connector_evidence_grant_invalid")
    marker_path, marker_bytes, marker, _marker_hash = _archived_model(
        chain,
        entry.consumption_marker_relative_path,
        entry.consumption_marker_sha256,
        ConnectorGrantConsumptionMarkerV1,
    )
    if marker_bytes != _canonical_json_bytes(marker) or any(
        (
            marker.connector_key != connector_key,
            marker.campaign_id != campaign_id,
            marker.campaign_fingerprint != expected_campaign_fingerprint,
            marker.campaign_definition_sha256 != definition_ref.raw_definition_sha256,
            marker.raw_grant_sha256 != expected_grant_sha256,
            marker.canonical_grant_fingerprint != entry.canonical_grant_fingerprint,
            marker.arming_nonce != grant.arming_nonce,
            marker.max_armings != 1,
        )
    ):
        _evidence_fail("connector_evidence_marker_invalid")
    introduction = _introduction(chain, campaign_id, expected_campaign_fingerprint)
    return VerifiedHistoricalGrantEvidence(
        definition_model=definition,
        model=grant,
        raw_definition_sha256=definition_ref.raw_definition_sha256,
        canonical_campaign_fingerprint=campaign_hash,
        raw_sha256=expected_grant_sha256,
        canonical_fingerprint=grant_hash,
        introduction_index_revision=int(introduction.model.revision),
        introduction_index_sha256=introduction.raw_sha256,
        definition_archive_path=definition_path,
        grant_archive_path=grant_path,
        marker_model=marker,
        consumption_marker_path=marker_path,
        consumption_marker_sha256=entry.consumption_marker_sha256,
        index_chain=chain,
    )


def _validate_log_capture_paths(ref: Any) -> tuple[str, str, str]:
    log_dir = _safe_evidence_relative(ref.log_dir_relative_path)
    manifest = _safe_evidence_relative(ref.manifest_relative_path)
    seal = _safe_evidence_relative(ref.seal_relative_path)
    fingerprint = str(ref.campaign_fingerprint)
    if (
        log_dir != f"logs/{fingerprint}"
        or manifest != f"logs/{fingerprint}/manifest.json"
        or seal != f"log-seals/{fingerprint}.json"
    ):
        _evidence_fail("connector_evidence_capture_path_invalid")
    return log_dir, manifest, seal


def _read_stable_capture_bytes(
    root: Path,
    relative_path: str,
    *,
    max_bytes: int,
) -> _EvidenceFileSnapshot:
    return _read_evidence_file(root, relative_path, max_bytes=max_bytes)


def _parse_canonical_capture_model(
    snapshot: _EvidenceFileSnapshot,
    model_type: Any,
    *,
    label: str,
) -> Any:
    del label
    return _parse_evidence_model(snapshot, model_type)


def verify_connector_campaign_log_capture_read_only(
    db: Any,
    chain: VerifiedEvidenceIndexChain,
    campaign_id: str,
    expected_campaign_fingerprint: str,
) -> VerifiedCampaignLogCapture:
    from sqlalchemy import select

    from app.models.models import ConnectorRunEvent
    from app.schemas.api import (
        ConnectorCampaignLogManifestV1,
        ConnectorCampaignLogSealV1,
    )

    definition_ref, _entries, capture_ref = _find_campaign_refs(
        chain,
        campaign_id,
        expected_campaign_fingerprint,
    )
    introduction = _introduction(chain, campaign_id, expected_campaign_fingerprint)
    _log_dir, manifest_relative, seal_relative = _validate_log_capture_paths(capture_ref)
    manifest_snapshot = _read_evidence_file(
        chain.evidence_root,
        manifest_relative,
        max_bytes=MAX_PROTECTED_JSON_BYTES,
    )
    seal_snapshot = _read_evidence_file(
        chain.evidence_root,
        seal_relative,
        max_bytes=MAX_PROTECTED_JSON_BYTES,
    )
    manifest = _parse_evidence_model(
        manifest_snapshot,
        ConnectorCampaignLogManifestV1,
    )
    seal = _parse_evidence_model(seal_snapshot, ConnectorCampaignLogSealV1)
    identity = (
        campaign_id,
        expected_campaign_fingerprint,
        definition_ref.raw_definition_sha256,
        definition_ref.code_revision,
    )
    if (
        (
            manifest.campaign_id,
            manifest.campaign_fingerprint,
            manifest.campaign_definition_sha256,
            manifest.code_revision,
        )
        != identity
        or (
            seal.campaign_id,
            seal.campaign_fingerprint,
            seal.campaign_definition_sha256,
            seal.code_revision,
        )
        != identity
        or seal.campaign_introduction_index_revision != introduction.model.revision
        or seal.campaign_introduction_index_sha256 != introduction.raw_sha256
        or seal.manifest_relative_path != manifest_relative
        or seal.sealed_at < manifest.runtime_stopped_at
    ):
        _evidence_fail("connector_evidence_capture_identity_invalid")
    if tuple(Path(item.relative_path).name for item in manifest.files) != _EXPECTED_CAPTURE_FILES:
        _evidence_fail("connector_evidence_capture_membership_invalid")
    file_set_hash = hashlib.sha256(
        _canonical_json_bytes(
            {
                "schema_id": "project6.connector_campaign_log_file_set.v1",
                "files": [item.model_dump(mode="python") for item in manifest.files],
            }
        )
    ).hexdigest()
    if (
        seal.manifest_sha256 != manifest_snapshot.sha256
        or seal.file_set_hash != file_set_hash
    ):
        _evidence_fail("connector_evidence_capture_seal_invalid")
    aggregate = 0
    stream_snapshots: list[_EvidenceFileSnapshot] = []
    stream_bytes: dict[str, bytes] = {}
    for item in manifest.files:
        snapshot = _read_evidence_file(
            chain.evidence_root,
            item.relative_path,
            max_bytes=MAX_CAPTURE_STREAM_BYTES,
        )
        aggregate += snapshot.size
        if (
            aggregate > MAX_CAPTURE_AGGREGATE_BYTES
            or snapshot.size != item.byte_count
            or snapshot.sha256 != item.sha256
        ):
            _evidence_fail("connector_evidence_capture_stream_invalid")
        stream_snapshots.append(snapshot)
        stream_bytes[item.relative_path] = snapshot.data
    run_ids = tuple(str(value) for value in seal.connector_run_ids)
    events = tuple(
        db.scalars(
            select(ConnectorRunEvent)
            .where(
                ConnectorRunEvent.event_type == "campaign_log_capture_sealed",
                ConnectorRunEvent.connector_run_id.in_(run_ids),
            )
            .order_by(
                ConnectorRunEvent.connector_run_id.asc(),
                ConnectorRunEvent.connector_run_event_id.asc(),
            )
            .limit(len(run_ids) + 1)
        )
    )
    if (
        len(run_ids) != 2
        or len(set(run_ids)) != 2
        or len(events) != 2
        or {str(event.connector_run_id) for event in events} != set(run_ids)
    ):
        _evidence_fail("connector_evidence_capture_event_invalid")
    first = tuple(
        stream_snapshots
        + [manifest_snapshot, seal_snapshot]
    )
    second = tuple(
        _read_evidence_file(
            chain.evidence_root,
            item.relative_path,
            max_bytes=(
                MAX_CAPTURE_STREAM_BYTES
                if index < len(stream_snapshots)
                else MAX_PROTECTED_JSON_BYTES
            ),
        )
        for index, item in enumerate(first)
    )
    if first != second:
        _evidence_fail("connector_evidence_capture_changed")
    return VerifiedCampaignLogCapture(
        manifest_bytes=manifest_snapshot.data,
        manifest_sha256=manifest_snapshot.sha256,
        file_set_hash=file_set_hash,
        seal_bytes=seal_snapshot.data,
        seal_sha256=seal_snapshot.sha256,
        stream_bytes=MappingProxyType(stream_bytes),
        seal_event_ids=tuple(str(event.connector_run_event_id) for event in events),
        stable_snapshot=tuple(
            (item.relative_path, item.size, item.sha256) for item in first
        ),
    )


_RUNTIME_RECORD_KEYS = (
    "schema_id",
    "ordinal",
    "runtime_instance_id",
    "phase",
    "event",
    "process_boot_id",
    "previous_record_sha256",
    "payload",
    "record_sha256",
)
_RUNTIME_SCHEMA_ID = "project6.dual_live_runtime_record.v1"
_RUNTIME_EVENT_PHASES = {
    "runtime_start": frozenset(("wrapper",)),
    "phase_child_start": frozenset(("A", "B")),
    "logger_census": frozenset(("A", "B")),
    "phase_go": frozenset(("A", "B")),
    "stop_latched": frozenset(("wrapper",)),
    "socket_census": frozenset(("A", "B")),
    "job_zero": frozenset(("A", "B")),
    "authority_cleared": frozenset(("A", "B")),
    "phase_complete": frozenset(("A", "B")),
    "runtime_complete": frozenset(("wrapper",)),
}
_RUNTIME_PAYLOAD_KEYS = {
    "runtime_start": frozenset(
        (
            "code_revision",
            "wrapper_image_sha256",
            "interpreter_image_sha256",
            "dependency_set_sha256",
            "phase_timeout_contract",
            "mutex_identity_sha256",
        )
    ),
    "phase_child_start": frozenset(
        ("process_creation_identity_sha256", "executable_sha256", "job_policy_sha256")
    ),
    "logger_census": frozenset(
        (
            "census_point",
            "topology_sha256",
            "handler_count",
            "guard_state",
            "topology_matches_initial",
        )
    ),
    "phase_go": frozenset(("prior_state", "next_state", "control_nonce_sha256")),
    "stop_latched": frozenset(("reason_code", "monotonic_tick_ns")),
    "socket_census": frozenset(
        (
            "tcp4_state_counts",
            "tcp6_state_counts",
            "udp4_count",
            "udp6_count",
            "process_identity_sha256",
            "stable",
        )
    ),
    "job_zero": frozenset(("active_process_count", "process_list_sha256")),
    "authority_cleared": frozenset(
        ("authority_posture_sha256", "all_required_absent")
    ),
    "phase_complete": frozenset(("terminal_state", "exit_code")),
    "runtime_complete": frozenset(
        ("phase_a_result_sha256", "phase_b_result_sha256", "terminal_state")
    ),
}


def _runtime_record_hash(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        _canonical_json_bytes(
            {key: record[key] for key in _RUNTIME_RECORD_KEYS if key != "record_sha256"}
        )
    ).hexdigest()


def read_runtime_records(app_log: bytes) -> tuple[dict[str, Any], ...]:
    if not isinstance(app_log, bytes) or (app_log and not app_log.endswith(b"\n")):
        _evidence_fail("dual_live_runtime_log_invalid")
    records: list[dict[str, Any]] = []
    runtime_id: str | None = None
    predecessor: str | None = None
    for line in app_log.splitlines():
        if not line:
            _evidence_fail("dual_live_runtime_log_invalid")
        try:
            value = _strict_json_loads(line)
        except (TypeError, ValueError) as exc:
            raise ConnectorEvidenceError("dual_live_runtime_log_invalid") from exc
        if not isinstance(value, dict) or value.get("schema_id") != _RUNTIME_SCHEMA_ID:
            continue
        if _canonical_json_bytes(value) != line or set(value) != set(_RUNTIME_RECORD_KEYS):
            _evidence_fail("dual_live_runtime_record_invalid")
        ordinal = value.get("ordinal")
        phase = value.get("phase")
        event = value.get("event")
        payload = value.get("payload")
        try:
            parsed_runtime_id = UUID(str(value.get("runtime_instance_id")))
        except (TypeError, ValueError) as exc:
            raise ConnectorEvidenceError("dual_live_runtime_record_invalid") from exc
        if (
            type(ordinal) is not int
            or ordinal != len(records) + 1
            or parsed_runtime_id.version != 4
            or str(parsed_runtime_id) != value.get("runtime_instance_id")
            or phase not in {"wrapper", "A", "B"}
            or event not in _RUNTIME_EVENT_PHASES
            or phase not in _RUNTIME_EVENT_PHASES[event]
            or not isinstance(payload, dict)
            or set(payload) != _RUNTIME_PAYLOAD_KEYS[event]
            or value.get("previous_record_sha256") != predecessor
            or not _LOWERCASE_SHA256.fullmatch(str(value.get("record_sha256") or ""))
            or _runtime_record_hash(value) != value.get("record_sha256")
        ):
            _evidence_fail("dual_live_runtime_record_invalid")
        boot = value.get("process_boot_id")
        if (phase == "wrapper" and boot is not None) or (
            phase != "wrapper" and not _LOWERCASE_SHA256.fullmatch(str(boot or ""))
        ):
            _evidence_fail("dual_live_runtime_record_invalid")
        if runtime_id is None:
            runtime_id = str(parsed_runtime_id)
        elif runtime_id != str(parsed_runtime_id):
            _evidence_fail("dual_live_runtime_record_invalid")
        normalized = {key: value[key] for key in _RUNTIME_RECORD_KEYS}
        records.append(normalized)
        predecessor = normalized["record_sha256"]
    return tuple(records)
