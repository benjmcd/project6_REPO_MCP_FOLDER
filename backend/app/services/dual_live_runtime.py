from __future__ import annotations

import hashlib
import logging
import re
import threading
from dataclasses import dataclass
from typing import Any, BinaryIO, Callable, Mapping
from uuid import UUID

from app.services.connector_egress_authorization import (
    canonical_json_bytes,
    strict_json_loads,
)


RUNTIME_RECORD_KEYS = (
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
RUNTIME_SCHEMA_ID = "project6.dual_live_runtime_record.v1"
MAX_FRAME_BYTES = 64 * 1024
MAX_FRAMES_PER_STREAM = 10_000
MAX_STREAM_BYTES = 16 * 1024 * 1024
MAX_CAPTURE_BYTES = 32 * 1024 * 1024
PIPE_STREAM_CLASSES = ("app", "http", "stdout", "stderr")
LOGGER_TOPOLOGY_SCHEMA_ID = "project6.dual_live_logger_topology.v1"
WINDOWS_MIB_TCP_STATES = (
    "MIB_TCP_STATE_CLOSED",
    "MIB_TCP_STATE_LISTEN",
    "MIB_TCP_STATE_SYN_SENT",
    "MIB_TCP_STATE_SYN_RCVD",
    "MIB_TCP_STATE_ESTAB",
    "MIB_TCP_STATE_FIN_WAIT1",
    "MIB_TCP_STATE_FIN_WAIT2",
    "MIB_TCP_STATE_CLOSE_WAIT",
    "MIB_TCP_STATE_CLOSING",
    "MIB_TCP_STATE_LAST_ACK",
    "MIB_TCP_STATE_TIME_WAIT",
    "MIB_TCP_STATE_DELETE_TCB",
)

_LOWERCASE_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOWERCASE_CODE_REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_PHASES = frozenset(("wrapper", "A", "B"))
_EVENT_PHASES = {
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
_FSM_STATES = frozenset(
    (
        "A_BOOT_DENY",
        "A_CENSUS_OK",
        "A_GO",
        "A_EGRESS_ENABLED",
        "A_STOPPED",
        "A_ABORTED",
        "B_BOOT_DENY",
        "B_CENSUS_OK",
        "B_GO",
        "B_ACTIVE",
        "B_STOPPED",
        "B_ABORTED",
    )
)
_PHASE_GO_EDGES = frozenset(
    (
        ("A_CENSUS_OK", "A_GO"),
        ("B_CENSUS_OK", "B_GO"),
    )
)
_PHASE_GO_EDGE_BY_PHASE = {
    "A": ("A_CENSUS_OK", "A_GO"),
    "B": ("B_CENSUS_OK", "B_GO"),
}
_STOP_REASONS = frozenset(
    (
        "child_exit_nonzero",
        "protocol_failure",
        "logger_census_failure",
        "pump_failure",
        "timeout",
        "operator_stop",
        "console_close",
        "writer_failure",
        "send_idle_timeout",
    )
)
_TERMINAL_STATES = frozenset(("completed", "failed", "aborted"))
_EVENT_PAYLOAD_KEYS = {
    "runtime_start": (
        "code_revision",
        "wrapper_image_sha256",
        "interpreter_image_sha256",
        "mutex_identity_sha256",
    ),
    "phase_child_start": (
        "process_creation_identity_sha256",
        "executable_sha256",
        "job_policy_sha256",
    ),
    "logger_census": (
        "census_point",
        "topology_sha256",
        "handler_count",
        "guard_state",
        "topology_matches_initial",
    ),
    "phase_go": ("prior_state", "next_state", "control_nonce_sha256"),
    "stop_latched": ("reason_code", "monotonic_tick_ns"),
    "socket_census": (
        "tcp4_state_counts",
        "tcp6_state_counts",
        "udp4_count",
        "udp6_count",
        "process_identity_sha256",
        "stable",
    ),
    "job_zero": ("active_process_count", "process_list_sha256"),
    "authority_cleared": ("authority_posture_sha256", "all_required_absent"),
    "phase_complete": ("terminal_state", "exit_code"),
    "runtime_complete": (
        "phase_a_result_sha256",
        "phase_b_result_sha256",
        "terminal_state",
    ),
}
_UNSAFE_FIELD_MARKERS = (
    "secret",
    "credential",
    "api_key",
    "url",
    "query",
    "header_value",
    "headervalue",
    "command_line",
    "commandline",
    "argv",
    "endpoint",
    "raw_path",
    "rawpath",
)
_PIPE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class DualLiveRuntimeError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise DualLiveRuntimeError(code)


def _require_uuid4(value: object, code: str) -> str:
    if not isinstance(value, str):
        _fail(code)
    try:
        parsed = UUID(value)
    except (AttributeError, ValueError):
        _fail(code)
    if parsed.version != 4 or str(parsed) != value:
        _fail(code)
    return value


def _require_sha256(value: object, code: str) -> str:
    if not isinstance(value, str) or _LOWERCASE_SHA256.fullmatch(value) is None:
        _fail(code)
    return value


def _require_code_revision(value: object, code: str) -> str:
    if not isinstance(value, str) or _LOWERCASE_CODE_REVISION.fullmatch(value) is None:
        _fail(code)
    return value


def _require_nonnegative_int(value: object, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail(code)
    return value


def _require_bool(value: object, code: str) -> bool:
    if type(value) is not bool:
        _fail(code)
    return value


def _require_choice(value: object, choices: frozenset[str], code: str) -> str:
    if not isinstance(value, str) or value not in choices:
        _fail(code)
    return value


def _has_unsafe_field(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                return True
            normalized = key.lower().replace("-", "_")
            if any(marker in normalized for marker in _UNSAFE_FIELD_MARKERS):
                return True
            if _has_unsafe_field(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_has_unsafe_field(item) for item in value)
    return False


def _require_tcp_state_counts(value: object, code: str) -> None:
    if not isinstance(value, Mapping) or set(value) != set(WINDOWS_MIB_TCP_STATES):
        _fail(code)
    for state in WINDOWS_MIB_TCP_STATES:
        _require_nonnegative_int(value[state], code)


def _validate_payload(event: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    code = "dual_live_runtime_payload_invalid"
    if not isinstance(payload, Mapping):
        _fail(code)
    if _has_unsafe_field(payload):
        _fail("dual_live_runtime_payload_unsafe_field")
    expected_keys = _EVENT_PAYLOAD_KEYS[event]
    if set(payload) != set(expected_keys):
        _fail(code)

    if event == "runtime_start":
        _require_code_revision(payload["code_revision"], code)
        for field in (
            "wrapper_image_sha256",
            "interpreter_image_sha256",
            "mutex_identity_sha256",
        ):
            _require_sha256(payload[field], code)
    elif event == "phase_child_start":
        for field in expected_keys:
            _require_sha256(payload[field], code)
    elif event == "logger_census":
        _require_choice(
            payload["census_point"],
            frozenset(("pre_activity", "exit")),
            code,
        )
        _require_sha256(payload["topology_sha256"], code)
        _require_nonnegative_int(payload["handler_count"], code)
        _require_choice(payload["guard_state"], _FSM_STATES, code)
        _require_bool(payload["topology_matches_initial"], code)
    elif event == "phase_go":
        edge = (payload["prior_state"], payload["next_state"])
        if edge not in _PHASE_GO_EDGES:
            _fail(code)
        _require_sha256(payload["control_nonce_sha256"], code)
    elif event == "stop_latched":
        _require_choice(payload["reason_code"], _STOP_REASONS, code)
        _require_nonnegative_int(payload["monotonic_tick_ns"], code)
    elif event == "socket_census":
        _require_tcp_state_counts(payload["tcp4_state_counts"], code)
        _require_tcp_state_counts(payload["tcp6_state_counts"], code)
        _require_nonnegative_int(payload["udp4_count"], code)
        _require_nonnegative_int(payload["udp6_count"], code)
        _require_sha256(payload["process_identity_sha256"], code)
        _require_bool(payload["stable"], code)
    elif event == "job_zero":
        _require_nonnegative_int(payload["active_process_count"], code)
        if payload["active_process_count"] != 0:
            _fail(code)
        _require_sha256(payload["process_list_sha256"], code)
    elif event == "authority_cleared":
        _require_sha256(payload["authority_posture_sha256"], code)
        _require_bool(payload["all_required_absent"], code)
    elif event == "phase_complete":
        _require_choice(payload["terminal_state"], _TERMINAL_STATES, code)
        _require_nonnegative_int(payload["exit_code"], code)
    elif event == "runtime_complete":
        _require_sha256(payload["phase_a_result_sha256"], code)
        _require_sha256(payload["phase_b_result_sha256"], code)
        _require_choice(payload["terminal_state"], _TERMINAL_STATES, code)

    copied = strict_json_loads(canonical_json_bytes(payload))
    if not isinstance(copied, dict):  # pragma: no cover - mapping narrows this
        _fail(code)
    return {key: copied[key] for key in expected_keys}


def _require_event_phase(
    *,
    phase: str,
    event: str,
    payload: Mapping[str, Any] | None,
    code: str,
) -> None:
    if phase not in _EVENT_PHASES[event]:
        _fail(code)
    if event == "phase_go" and payload is not None:
        edge = (payload["prior_state"], payload["next_state"])
        if _PHASE_GO_EDGE_BY_PHASE.get(phase) != edge:
            _fail(code)


def _record_hash(record: Mapping[str, Any]) -> str:
    preimage = {key: value for key, value in record.items() if key != "record_sha256"}
    return hashlib.sha256(canonical_json_bytes(preimage)).hexdigest()


@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    runtime_instance_id: str
    wrapper_nonce_sha256: str
    code_revision: str
    wrapper_image_sha256: str
    interpreter_image_sha256: str
    root_mutex_identity_sha256: str
    campaign_mutex_identity_sha256: str

    def __post_init__(self) -> None:
        code = "dual_live_runtime_identity_invalid"
        _require_uuid4(self.runtime_instance_id, code)
        _require_sha256(self.wrapper_nonce_sha256, code)
        _require_code_revision(self.code_revision, code)
        _require_sha256(self.wrapper_image_sha256, code)
        _require_sha256(self.interpreter_image_sha256, code)
        _require_sha256(self.root_mutex_identity_sha256, code)
        _require_sha256(self.campaign_mutex_identity_sha256, code)


class RuntimeRecordWriter:
    __slots__ = ("_identity", "_lock", "_ordinal", "_previous_record_sha256", "_sink")

    def __init__(
        self,
        sink: Callable[[bytes], int | None],
        *,
        identity: RuntimeIdentity,
    ) -> None:
        if not callable(sink) or not isinstance(identity, RuntimeIdentity):
            _fail("dual_live_runtime_writer_invalid")
        self._sink = sink
        self._identity = identity
        self._ordinal = 0
        self._previous_record_sha256: str | None = None
        self._lock = threading.Lock()

    def append(
        self,
        *,
        phase: str,
        event: str,
        process_boot_id: str | None,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if phase not in _PHASES:
            _fail("dual_live_runtime_phase_invalid")
        if phase == "wrapper":
            if process_boot_id is not None:
                _fail("dual_live_runtime_process_boot_id_invalid")
        else:
            _require_uuid4(process_boot_id, "dual_live_runtime_process_boot_id_invalid")
        if event not in _EVENT_PAYLOAD_KEYS:
            _fail("dual_live_runtime_event_invalid")
        _require_event_phase(
            phase=phase,
            event=event,
            payload=None,
            code="dual_live_runtime_phase_invalid",
        )
        event_payload = _validate_payload(event, payload)
        _require_event_phase(
            phase=phase,
            event=event,
            payload=event_payload,
            code="dual_live_runtime_phase_invalid",
        )
        if event == "runtime_start" and any(
            event_payload[field] != getattr(self._identity, field)
            for field in (
                "code_revision",
                "wrapper_image_sha256",
                "interpreter_image_sha256",
            )
        ):
            _fail("dual_live_runtime_identity_mismatch")

        with self._lock:
            record: dict[str, Any] = {
                "schema_id": RUNTIME_SCHEMA_ID,
                "ordinal": self._ordinal + 1,
                "runtime_instance_id": self._identity.runtime_instance_id,
                "phase": phase,
                "event": event,
                "process_boot_id": process_boot_id,
                "previous_record_sha256": self._previous_record_sha256,
                "payload": event_payload,
            }
            record["record_sha256"] = _record_hash(record)
            encoded = canonical_json_bytes(record) + b"\n"
            try:
                written = self._sink(encoded)
            except Exception as exc:
                raise DualLiveRuntimeError("dual_live_runtime_writer_failure") from exc
            if written is not None and (
                isinstance(written, bool)
                or not isinstance(written, int)
                or written != len(encoded)
            ):
                _fail("dual_live_runtime_writer_failure")
            self._ordinal = record["ordinal"]
            self._previous_record_sha256 = record["record_sha256"]
            return record


def _validate_runtime_record(record: Mapping[str, Any]) -> dict[str, Any]:
    code = "dual_live_runtime_record_invalid"
    if set(record) != set(RUNTIME_RECORD_KEYS):
        _fail(code)
    if record["schema_id"] != RUNTIME_SCHEMA_ID:
        _fail(code)
    _require_nonnegative_int(record["ordinal"], code)
    if record["ordinal"] == 0:
        _fail(code)
    _require_uuid4(record["runtime_instance_id"], code)
    phase = record["phase"]
    if phase not in _PHASES:
        _fail(code)
    process_boot_id = record["process_boot_id"]
    if phase == "wrapper":
        if process_boot_id is not None:
            _fail(code)
    else:
        _require_uuid4(process_boot_id, code)
    event = record["event"]
    if not isinstance(event, str) or event not in _EVENT_PAYLOAD_KEYS:
        _fail(code)
    _require_event_phase(phase=phase, event=event, payload=None, code=code)
    payload = _validate_payload(event, record["payload"])
    _require_event_phase(phase=phase, event=event, payload=payload, code=code)
    previous = record["previous_record_sha256"]
    if previous is not None:
        _require_sha256(previous, code)
    _require_sha256(record["record_sha256"], code)
    normalized = {
        "schema_id": RUNTIME_SCHEMA_ID,
        "ordinal": record["ordinal"],
        "runtime_instance_id": record["runtime_instance_id"],
        "phase": phase,
        "event": event,
        "process_boot_id": process_boot_id,
        "previous_record_sha256": previous,
        "payload": payload,
        "record_sha256": record["record_sha256"],
    }
    if _record_hash(normalized) != normalized["record_sha256"]:
        _fail("dual_live_runtime_record_hash_mismatch")
    return normalized


def read_runtime_records(app_log: bytes) -> tuple[dict[str, Any], ...]:
    if not isinstance(app_log, bytes):
        _fail("dual_live_runtime_log_invalid")
    if not app_log:
        return ()
    if not app_log.endswith(b"\n"):
        _fail("dual_live_runtime_log_unexpected_eof")

    records: list[dict[str, Any]] = []
    expected_runtime_instance_id: str | None = None
    expected_previous: str | None = None
    for raw_line in app_log.splitlines():
        if not raw_line:
            _fail("dual_live_runtime_log_invalid")
        try:
            value = strict_json_loads(raw_line)
        except (TypeError, ValueError) as exc:
            raise DualLiveRuntimeError("dual_live_runtime_log_invalid") from exc
        if not isinstance(value, dict) or value.get("schema_id") != RUNTIME_SCHEMA_ID:
            continue
        if canonical_json_bytes(value) != raw_line:
            _fail("dual_live_runtime_record_noncanonical")
        record = _validate_runtime_record(value)
        if record["ordinal"] != len(records) + 1:
            _fail("dual_live_runtime_record_ordinal_invalid")
        if record["previous_record_sha256"] != expected_previous:
            _fail("dual_live_runtime_record_predecessor_invalid")
        if expected_runtime_instance_id is None:
            expected_runtime_instance_id = record["runtime_instance_id"]
        elif record["runtime_instance_id"] != expected_runtime_instance_id:
            _fail("dual_live_runtime_instance_mismatch")
        expected_previous = record["record_sha256"]
        records.append(record)
    return tuple(records)


def _validate_frame_payload(payload: bytes) -> None:
    if not payload:
        _fail("dual_live_frame_empty")
    if len(payload) > MAX_FRAME_BYTES:
        _fail("dual_live_frame_oversized")
    try:
        payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise DualLiveRuntimeError("dual_live_frame_invalid_utf8") from exc
    try:
        value = strict_json_loads(payload)
    except (TypeError, ValueError):
        return
    if isinstance(value, dict) and value.get("schema_id") == RUNTIME_SCHEMA_ID:
        _fail("dual_live_child_reserved_schema")


def encode_pipe_frame(payload: bytes) -> bytes:
    if not isinstance(payload, bytes):
        _fail("dual_live_frame_type_invalid")
    _validate_frame_payload(payload)
    return len(payload).to_bytes(4, "big", signed=False) + payload


def _read_exact(reader: BinaryIO, size: int, *, clean_eof: bool) -> bytes | None:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = reader.read(remaining)
        if not isinstance(chunk, bytes):
            _fail("dual_live_frame_reader_invalid")
        if not chunk:
            if clean_eof and not chunks:
                return None
            _fail("dual_live_frame_unexpected_eof")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_pipe_frame(reader: BinaryIO) -> bytes | None:
    prefix = _read_exact(reader, 4, clean_eof=True)
    if prefix is None:
        return None
    length = int.from_bytes(prefix, "big", signed=False)
    if length == 0:
        _fail("dual_live_frame_empty")
    if length > MAX_FRAME_BYTES:
        _fail("dual_live_frame_oversized")
    payload = _read_exact(reader, length, clean_eof=False)
    if payload is None:  # pragma: no cover - clean_eof is false
        _fail("dual_live_frame_unexpected_eof")
    _validate_frame_payload(payload)
    return payload


class PipeFrameBudget:
    __slots__ = ("_lock", "_stream_bytes", "_stream_frames", "_total_bytes")

    def __init__(self) -> None:
        self._stream_bytes = {stream: 0 for stream in PIPE_STREAM_CLASSES}
        self._stream_frames = {stream: 0 for stream in PIPE_STREAM_CLASSES}
        self._total_bytes = 0
        self._lock = threading.Lock()

    def consume(self, stream: str, payload_bytes: int) -> None:
        if stream not in self._stream_bytes:
            _fail("dual_live_pump_stream_invalid")
        if (
            isinstance(payload_bytes, bool)
            or not isinstance(payload_bytes, int)
            or payload_bytes <= 0
            or payload_bytes > MAX_FRAME_BYTES
        ):
            _fail("dual_live_pump_frame_bytes_invalid")
        with self._lock:
            next_frames = self._stream_frames[stream] + 1
            next_stream_bytes = self._stream_bytes[stream] + payload_bytes
            next_total_bytes = self._total_bytes + payload_bytes
            if next_frames > MAX_FRAMES_PER_STREAM:
                _fail("dual_live_pump_frame_count_exceeded")
            if next_stream_bytes > MAX_STREAM_BYTES:
                _fail("dual_live_pump_stream_bytes_exceeded")
            if next_total_bytes > MAX_CAPTURE_BYTES:
                _fail("dual_live_pump_aggregate_bytes_exceeded")
            self._stream_frames[stream] = next_frames
            self._stream_bytes[stream] = next_stream_bytes
            self._total_bytes = next_total_bytes


class CampaignPipeSink:
    __slots__ = ("_bound_handler", "_lock", "_pipe_token", "_writer")

    def __init__(self, pipe_token: str, writer: BinaryIO) -> None:
        if (
            not isinstance(pipe_token, str)
            or _PIPE_TOKEN.fullmatch(pipe_token) is None
            or not callable(getattr(writer, "write", None))
        ):
            _fail("dual_live_logger_pipe_sink_invalid")
        self._pipe_token = pipe_token
        self._writer = writer
        self._bound_handler: CampaignPipeHandler | None = None
        self._lock = threading.Lock()

    @property
    def pipe_token(self) -> str:
        return self._pipe_token

    def _bind(self, handler: CampaignPipeHandler) -> None:
        with self._lock:
            if (
                type(handler) is not CampaignPipeHandler
                or self._bound_handler is not None
            ):
                _fail("dual_live_logger_pipe_binding_invalid")
            self._bound_handler = handler

    def _is_bound_to(self, handler: CampaignPipeHandler) -> bool:
        with self._lock:
            return self._bound_handler is handler

    def _write_frame(self, handler: CampaignPipeHandler, frame: bytes) -> None:
        with self._lock:
            if self._bound_handler is not handler:
                _fail("dual_live_logger_pipe_binding_invalid")
            written = self._writer.write(frame)
        if written is not None and (
            isinstance(written, bool)
            or not isinstance(written, int)
            or written != len(frame)
        ):
            _fail("dual_live_logger_pipe_write_failed")


class CampaignPipeHandler(logging.Handler):
    def __init__(
        self,
        pipe_token: str,
        sink: CampaignPipeSink,
    ) -> None:
        if (
            not isinstance(pipe_token, str)
            or _PIPE_TOKEN.fullmatch(pipe_token) is None
            or type(sink) is not CampaignPipeSink
            or sink.pipe_token != pipe_token
        ):
            _fail("dual_live_logger_pipe_handler_invalid")
        super().__init__()
        self._pipe_token = pipe_token
        self._sink = sink
        sink._bind(self)

    @property
    def pipe_token(self) -> str:
        return self._pipe_token

    def emit(self, record: logging.LogRecord) -> None:
        payload = self.format(record).encode("utf-8", errors="strict")
        framed = encode_pipe_frame(payload)
        self._sink._write_frame(self, framed)


def _type_id(value: object) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _filter_ids(filters: list[logging.Filter]) -> list[str]:
    return [_type_id(filter_) for filter_ in filters]


def _require_allowed_pipe_tokens(allowed_pipe_tokens: frozenset[str]) -> None:
    if type(allowed_pipe_tokens) is not frozenset:
        _fail("dual_live_logger_allowed_tokens_invalid")
    if any(
        not isinstance(token, str) or _PIPE_TOKEN.fullmatch(token) is None
        for token in allowed_pipe_tokens
    ):
        _fail("dual_live_logger_allowed_tokens_invalid")


def _project_handler(
    handler: logging.Handler,
    *,
    allowed_pipe_tokens: frozenset[str],
    seen_pipe_tokens: set[str],
) -> dict[str, Any]:
    if type(handler) is CampaignPipeHandler:
        pipe_token: str | None = handler.pipe_token
        sink = getattr(handler, "_sink", None)
        if (
            type(sink) is not CampaignPipeSink
            or sink.pipe_token != pipe_token
            or not sink._is_bound_to(handler)
        ):
            _fail("dual_live_logger_pipe_binding_invalid")
        if pipe_token not in allowed_pipe_tokens:
            _fail("dual_live_logger_pipe_token_invalid")
        if pipe_token in seen_pipe_tokens:
            _fail("dual_live_logger_duplicate_pipe_token")
        seen_pipe_tokens.add(pipe_token)
    elif type(handler) is logging.NullHandler:
        pipe_token = None
        if handler.filters or handler.formatter is not None:
            _fail("dual_live_logger_handler_invalid")
    else:
        _fail("dual_live_logger_handler_invalid")

    level = handler.level
    if isinstance(level, bool) or not isinstance(level, int):
        _fail("dual_live_logger_handler_invalid")
    formatter = handler.formatter
    return {
        "type_id": _type_id(handler),
        "pipe_token": pipe_token,
        "level": level,
        "formatter_type_id": _type_id(formatter) if formatter is not None else None,
        "filters": _filter_ids(handler.filters),
    }


def _project_logger(
    logger: logging.Logger,
    *,
    name: str,
    kind: str,
    allowed_pipe_tokens: frozenset[str],
    seen_pipe_tokens: set[str],
) -> dict[str, Any]:
    if not isinstance(logger.disabled, bool):
        _fail("dual_live_logger_entry_invalid")
    if (
        isinstance(logger.level, bool)
        or not isinstance(logger.level, int)
        or isinstance(logger.getEffectiveLevel(), bool)
        or not isinstance(logger.getEffectiveLevel(), int)
        or not isinstance(logger.propagate, bool)
    ):
        _fail("dual_live_logger_entry_invalid")
    return {
        "name": name,
        "kind": kind,
        "disabled": logger.disabled,
        "level": logger.level,
        "effective_level": logger.getEffectiveLevel(),
        "propagate": logger.propagate,
        "filters": _filter_ids(logger.filters),
        "handlers": [
            _project_handler(
                handler,
                allowed_pipe_tokens=allowed_pipe_tokens,
                seen_pipe_tokens=seen_pipe_tokens,
            )
            for handler in logger.handlers
        ],
    }


def _project_placeholder(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "kind": "placeholder",
        "disabled": None,
        "level": None,
        "effective_level": None,
        "propagate": None,
        "filters": [],
        "handlers": [],
    }


def census_loggers(allowed_pipe_tokens: frozenset[str]) -> dict[str, Any]:
    _require_allowed_pipe_tokens(allowed_pipe_tokens)
    logging._acquireLock()
    try:
        root = logging.getLogger()
        manager = logging.Logger.manager
        if not isinstance(root, logging.RootLogger) or manager.root is not root:
            _fail("dual_live_logger_manager_invalid")
        seen_pipe_tokens: set[str] = set()
        entries = [
            _project_logger(
                root,
                name="",
                kind="root",
                allowed_pipe_tokens=allowed_pipe_tokens,
                seen_pipe_tokens=seen_pipe_tokens,
            )
        ]
        for name, value in sorted(manager.loggerDict.items()):
            if not isinstance(name, str):
                _fail("dual_live_logger_entry_invalid")
            if isinstance(value, logging.Logger):
                entries.append(
                    _project_logger(
                        value,
                        name=name,
                        kind="logger",
                        allowed_pipe_tokens=allowed_pipe_tokens,
                        seen_pipe_tokens=seen_pipe_tokens,
                    )
                )
            elif type(value) is logging.PlaceHolder:
                entries.append(_project_placeholder(name))
            else:
                _fail("dual_live_logger_entry_invalid")

        last_resort_handler = logging.lastResort
        last_resort = (
            _project_handler(
                last_resort_handler,
                allowed_pipe_tokens=allowed_pipe_tokens,
                seen_pipe_tokens=seen_pipe_tokens,
            )
            if last_resort_handler is not None
            else None
        )
        preimage: dict[str, Any] = {
            "schema_id": LOGGER_TOPOLOGY_SCHEMA_ID,
            "loggers": entries,
            "last_resort": last_resort,
            "handler_count": sum(len(entry["handlers"]) for entry in entries)
            + (1 if last_resort is not None else 0),
        }
        return {
            **preimage,
            "topology_sha256": hashlib.sha256(
                canonical_json_bytes(preimage)
            ).hexdigest(),
        }
    finally:
        logging._releaseLock()


def _deny_logger_topology_mutation(*args: object, **kwargs: object) -> None:
    _fail("dual_live_logger_topology_frozen")


_MISSING_LOGGING_ATTRIBUTE = object()


def _patch_logging_attribute(
    patched: list[tuple[object, str, object]],
    target: object,
    name: str,
) -> None:
    previous = vars(target).get(name, _MISSING_LOGGING_ATTRIBUTE)
    patched.append((target, name, previous))
    setattr(target, name, _deny_logger_topology_mutation)


def _restore_logging_attributes(
    patched: list[tuple[object, str, object]],
) -> None:
    for target, name, previous in reversed(patched):
        if previous is _MISSING_LOGGING_ATTRIBUTE:
            delattr(target, name)
        else:
            setattr(target, name, previous)


def freeze_logger_topology(
    allowed_pipe_tokens: frozenset[str],
) -> Callable[[], dict[str, Any]]:
    patched: list[tuple[object, str, object]] = []
    logging._acquireLock()
    try:
        initial = census_loggers(allowed_pipe_tokens)
        root = logging.getLogger()
        manager = logging.Logger.manager
        logger_values = [
            value
            for value in manager.loggerDict.values()
            if isinstance(value, logging.Logger)
        ]
        loggers = [root, *logger_values]
        handler_values = [
            handler
            for logger in loggers
            for handler in logger.handlers
        ]
        if logging.lastResort is not None:
            handler_values.append(logging.lastResort)
        handlers = list({id(handler): handler for handler in handler_values}.values())

        for target, method_names in (
            (logging, ("basicConfig", "getLogger", "setLoggerClass")),
            (logging.Manager, ("getLogger", "setLoggerClass")),
            (
                logging.Logger,
                (
                    "addFilter",
                    "addHandler",
                    "removeFilter",
                    "removeHandler",
                    "setLevel",
                ),
            ),
            (
                logging.Handler,
                (
                    "addFilter",
                    "close",
                    "removeFilter",
                    "setFormatter",
                    "setLevel",
                ),
            ),
            (manager, ("getLogger", "setLoggerClass")),
        ):
            for method_name in method_names:
                _patch_logging_attribute(patched, target, method_name)
        for logger in loggers:
            for method_name in (
                "addFilter",
                "addHandler",
                "removeFilter",
                "removeHandler",
                "setLevel",
            ):
                _patch_logging_attribute(patched, logger, method_name)
        for handler in handlers:
            for method_name in (
                "addFilter",
                "close",
                "removeFilter",
                "setFormatter",
                "setLevel",
            ):
                _patch_logging_attribute(patched, handler, method_name)
    except BaseException:
        _restore_logging_attributes(patched)
        raise
    finally:
        logging._releaseLock()

    finished = False

    def _recheck() -> dict[str, Any]:
        nonlocal finished
        logging._acquireLock()
        try:
            if finished:
                _fail("dual_live_logger_recheck_already_completed")
            finished = True
            _restore_logging_attributes(patched)
            current = census_loggers(allowed_pipe_tokens)
            if current != initial:
                _fail("dual_live_logger_topology_changed")
            return current
        finally:
            logging._releaseLock()

    return _recheck
