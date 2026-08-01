from __future__ import annotations

import hashlib
import io
import logging
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, BinaryIO, Callable, Mapping, NoReturn
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
CHILD_CONTROL_SCHEMA_ID = "project6.dual_live_child_control.v1"
CHILD_STATUS_SCHEMA_ID = "project6.dual_live_child_status.v1"
_RESERVED_CAPTURE_SCHEMA_IDS = frozenset(
    (CHILD_CONTROL_SCHEMA_ID, CHILD_STATUS_SCHEMA_ID, RUNTIME_SCHEMA_ID)
)
MAX_FRAME_BYTES = 64 * 1024
MAX_CONTROL_FRAME_BYTES = 4 * 1024
MAX_FRAMES_PER_STREAM = 10_000
MAX_STREAM_BYTES = 16 * 1024 * 1024
MAX_CAPTURE_BYTES = 32 * 1024 * 1024
PUMP_CANCEL_JOIN_SECONDS = 1.0
_CHILD_WAIT_POLL_SECONDS = 0.05
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


def _fail(code: str) -> NoReturn:
    raise DualLiveRuntimeError(code)


class FirstStopLatch:
    """Thread-safe first-reason-wins stop signal for one controller run."""

    __slots__ = (
        "_event",
        "_lock",
        "_monotonic_tick_ns",
        "_reason_code",
    )

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._reason_code: str | None = None
        self._monotonic_tick_ns: int | None = None

    @property
    def is_set(self) -> bool:
        return self._event.is_set()

    @property
    def reason_code(self) -> str | None:
        with self._lock:
            return self._reason_code

    @property
    def monotonic_tick_ns(self) -> int | None:
        with self._lock:
            return self._monotonic_tick_ns

    @property
    def snapshot(self) -> tuple[str, int] | None:
        with self._lock:
            if self._reason_code is None:
                return None
            if self._monotonic_tick_ns is None:
                _fail("dual_live_stop_latch_invalid")
            return self._reason_code, self._monotonic_tick_ns

    def latch(self, reason_code: str) -> bool:
        if reason_code not in _STOP_REASONS:
            _fail("dual_live_stop_reason_invalid")
        with self._lock:
            if self._reason_code is not None:
                return False
            self._monotonic_tick_ns = time.monotonic_ns()
            self._reason_code = reason_code
            self._event.set()
            return True

    def commit_if_clear(self) -> bool:
        """Atomically classify a transition before any external I/O begins."""
        with self._lock:
            return self._reason_code is None

    def wait(self, timeout: float | None = None) -> bool:
        if timeout is not None and (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout < 0
        ):
            _fail("dual_live_stop_wait_invalid")
        return self._event.wait(timeout)


class PhaseControlState:
    """Validate a child control stream and consume exactly one nonce-bound GO."""

    __slots__ = (
        "_control_nonce_sha256",
        "_lock",
        "_phase",
        "_state",
        "_stop_latch",
    )

    def __init__(
        self,
        *,
        phase: str,
        control_nonce_sha256: str,
        stop_latch: FirstStopLatch,
    ) -> None:
        if phase not in {"A", "B"}:
            _fail("dual_live_phase_control_invalid")
        if (
            not isinstance(control_nonce_sha256, str)
            or _LOWERCASE_SHA256.fullmatch(control_nonce_sha256) is None
            or type(stop_latch) is not FirstStopLatch
        ):
            _fail("dual_live_phase_control_invalid")
        self._phase = phase
        self._control_nonce_sha256 = control_nonce_sha256
        self._stop_latch = stop_latch
        self._state = "boot"
        self._lock = threading.RLock()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def _protocol_failure(
        self,
        code: str,
        *,
        cause: BaseException | None = None,
    ) -> NoReturn:
        with self._lock:
            if self._state not in {"complete", "stopped"}:
                self._state = "failed"
        self._stop_latch.latch("protocol_failure")
        if cause is not None:
            raise DualLiveRuntimeError(code) from cause
        _fail(code)

    def mark_census_ready(self) -> None:
        with self._lock:
            if self._state != "boot":
                self._protocol_failure("dual_live_phase_census_duplicate")
            self._state = "census_ready"

    def consume(self, payload: bytes) -> str:
        with self._lock:
            if self._state in {"complete", "failed", "stopped"}:
                self._stop_latch.latch("protocol_failure")
                _fail("dual_live_phase_control_terminal")
            if not isinstance(payload, bytes) or not payload:
                self._protocol_failure("dual_live_phase_control_invalid")
            try:
                message = strict_json_loads(payload)
            except (TypeError, ValueError):
                self._protocol_failure("dual_live_phase_control_invalid")
            if type(message) is not dict or canonical_json_bytes(message) != payload:
                self._protocol_failure("dual_live_phase_control_invalid")
            command = message.get("command")
            if command == "GO":
                expected_keys = (
                    "schema_id",
                    "phase",
                    "command",
                    "control_nonce",
                )
            elif command == "STOP":
                expected_keys = (
                    "schema_id",
                    "phase",
                    "command",
                    "reason_code",
                )
            else:
                self._protocol_failure("dual_live_phase_control_invalid")
            if (
                tuple(message) != tuple(sorted(expected_keys))
                or message["schema_id"] != CHILD_CONTROL_SCHEMA_ID
                or message["phase"] != self._phase
            ):
                self._protocol_failure("dual_live_phase_control_invalid")

            if command == "STOP":
                reason_code = message["reason_code"]
                if not isinstance(reason_code, str) or reason_code not in _STOP_REASONS:
                    self._protocol_failure("dual_live_phase_control_invalid")
                self._stop_latch.latch(reason_code)
                self._state = "stopped"
                return "STOP"

            nonce = message["control_nonce"]
            if (
                not isinstance(nonce, str)
                or _LOWERCASE_SHA256.fullmatch(nonce) is None
                or hashlib.sha256(nonce.encode("ascii")).hexdigest()
                != self._control_nonce_sha256
            ):
                self._protocol_failure("dual_live_phase_go_invalid")
            if self._state == "boot":
                self._protocol_failure("dual_live_phase_go_early")
            if self._state == "go_consumed":
                self._protocol_failure("dual_live_phase_go_duplicate")
            if self._state != "census_ready":
                self._protocol_failure("dual_live_phase_go_late")
            self._state = "go_consumed"
            return "GO"

    def consume_frame(self, reader: BinaryIO) -> str:
        try:
            payload = _read_control_frame(reader)
        except Exception as exc:
            self._protocol_failure("dual_live_phase_control_invalid", cause=exc)
        if payload is None:
            self._protocol_failure("dual_live_phase_control_invalid")
        return self.consume(payload)

    def complete(self) -> None:
        with self._lock:
            if self._state != "go_dispatched":
                self._protocol_failure("dual_live_phase_complete_invalid")
            self._state = "complete"

    def commit_go_if_clear(self) -> bool:
        """Commit at most one GO as in-flight without performing external I/O."""

        with self._lock:
            if self._state != "go_consumed":
                self._protocol_failure("dual_live_phase_go_late")
            if not self._stop_latch.commit_if_clear():
                self._state = "stopped"
                return False
            self._state = "go_in_flight"
            return True

    def finish_go_dispatch(self, *, dispatched: bool) -> None:
        if type(dispatched) is not bool:
            _fail("dual_live_phase_control_invalid")
        with self._lock:
            if self._state != "go_in_flight":
                _fail("dual_live_phase_control_invalid")
            if self._stop_latch.is_set:
                self._state = "stopped"
            elif not dispatched:
                self._state = "failed"
            else:
                self._state = "go_dispatched"


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
    __slots__ = (
        "_failed",
        "_identity",
        "_lock",
        "_ordinal",
        "_previous_record_sha256",
        "_sink",
    )

    def __init__(
        self,
        sink: Callable[[bytes], int],
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
        self._failed = False

    def append(
        self,
        *,
        phase: str,
        event: str,
        process_boot_id: str | None,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        with self._lock:
            if self._failed:
                _fail("dual_live_runtime_writer_poisoned")
        if phase not in _PHASES:
            _fail("dual_live_runtime_phase_invalid")
        if phase == "wrapper":
            if process_boot_id is not None:
                _fail("dual_live_runtime_process_boot_id_invalid")
        else:
            _require_sha256(
                process_boot_id,
                "dual_live_runtime_process_boot_id_invalid",
            )
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
            if self._failed:
                _fail("dual_live_runtime_writer_poisoned")
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
            except BaseException as exc:
                self._failed = True
                if isinstance(exc, Exception):
                    raise DualLiveRuntimeError(
                        "dual_live_runtime_writer_failure"
                    ) from exc
                raise
            if (
                isinstance(written, bool)
                or not isinstance(written, int)
                or written != len(encoded)
            ):
                self._failed = True
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
        _require_sha256(process_boot_id, code)
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


def _validate_frame_payload(
    payload: bytes,
    *,
    allowed_reserved_schema_ids: frozenset[str] = frozenset(),
) -> None:
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
    schema_id = value.get("schema_id") if isinstance(value, dict) else None
    if (
        isinstance(schema_id, str)
        and schema_id in _RESERVED_CAPTURE_SCHEMA_IDS
        and schema_id not in allowed_reserved_schema_ids
    ):
        _fail("dual_live_child_reserved_schema")


def encode_pipe_frame(payload: bytes) -> bytes:
    return _encode_pipe_frame(payload)


def _encode_pipe_frame(
    payload: bytes,
    *,
    allowed_reserved_schema_ids: frozenset[str] = frozenset(),
) -> bytes:
    if not isinstance(payload, bytes):
        _fail("dual_live_frame_type_invalid")
    _validate_frame_payload(
        payload,
        allowed_reserved_schema_ids=allowed_reserved_schema_ids,
    )
    return len(payload).to_bytes(4, "big", signed=False) + payload


def encode_child_control_frame(
    *,
    phase: str,
    command: str,
    control_nonce: str | None = None,
    reason_code: str | None = None,
) -> bytes:
    if phase not in {"A", "B"}:
        _fail("dual_live_phase_control_invalid")
    if command == "GO":
        if (
            not isinstance(control_nonce, str)
            or _LOWERCASE_SHA256.fullmatch(control_nonce) is None
            or reason_code is not None
        ):
            _fail("dual_live_phase_control_invalid")
        payload = {
            "schema_id": CHILD_CONTROL_SCHEMA_ID,
            "phase": phase,
            "command": command,
            "control_nonce": control_nonce,
        }
    elif command == "STOP":
        if reason_code not in _STOP_REASONS or control_nonce is not None:
            _fail("dual_live_phase_control_invalid")
        payload = {
            "schema_id": CHILD_CONTROL_SCHEMA_ID,
            "phase": phase,
            "command": command,
            "reason_code": reason_code,
        }
    else:
        _fail("dual_live_phase_control_invalid")
    return _encode_pipe_frame(
        canonical_json_bytes(payload),
        allowed_reserved_schema_ids=frozenset((CHILD_CONTROL_SCHEMA_ID,)),
    )


def encode_child_status_frame(
    *,
    phase: str,
    event: str,
    process_boot_id: str,
    status_nonce_sha256: str,
    ordinal: int,
    payload: Mapping[str, Any],
) -> bytes:
    if (
        phase not in {"A", "B"}
        or event != "logger_census"
        or not isinstance(process_boot_id, str)
        or _LOWERCASE_SHA256.fullmatch(process_boot_id) is None
        or not isinstance(status_nonce_sha256, str)
        or _LOWERCASE_SHA256.fullmatch(status_nonce_sha256) is None
        or isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal <= 0
        or not isinstance(payload, Mapping)
    ):
        _fail("dual_live_child_status_invalid")
    encoded = canonical_json_bytes(
        {
            "schema_id": CHILD_STATUS_SCHEMA_ID,
            "phase": phase,
            "event": event,
            "process_boot_id": process_boot_id,
            "status_nonce_sha256": status_nonce_sha256,
            "ordinal": ordinal,
            "payload": payload,
        }
    )
    decode_child_status_frame(
        encoded,
        expected_phase=phase,
        expected_process_boot_id=process_boot_id,
        expected_status_nonce_sha256=status_nonce_sha256,
        expected_ordinal=ordinal,
    )
    return _encode_pipe_frame(
        encoded,
        allowed_reserved_schema_ids=frozenset((CHILD_STATUS_SCHEMA_ID,)),
    )


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
    return _read_pipe_frame(reader)


def _read_pipe_frame(
    reader: BinaryIO,
    *,
    allowed_reserved_schema_ids: frozenset[str] = frozenset(),
) -> bytes | None:
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
    _validate_frame_payload(
        payload,
        allowed_reserved_schema_ids=allowed_reserved_schema_ids,
    )
    return payload


def _read_control_frame(reader: BinaryIO) -> bytes | None:
    prefix = _read_exact(reader, 4, clean_eof=True)
    if prefix is None:
        return None
    length = int.from_bytes(prefix, "big", signed=False)
    if length == 0:
        _fail("dual_live_frame_empty")
    if length > MAX_CONTROL_FRAME_BYTES:
        _fail("dual_live_phase_control_oversized")
    payload = _read_exact(reader, length, clean_eof=False)
    if payload is None:  # pragma: no cover - clean_eof is false
        _fail("dual_live_frame_unexpected_eof")
    return payload


class PipeFrameBudget:
    __slots__ = ("_lock", "_stream_bytes", "_stream_frames", "_total_bytes")

    def __init__(self) -> None:
        self._stream_bytes = {stream: 0 for stream in PIPE_STREAM_CLASSES}
        self._stream_frames = {stream: 0 for stream in PIPE_STREAM_CLASSES}
        self._total_bytes = 0
        self._lock = threading.Lock()

    def _reserve(
        self,
        stream: str,
        emitted_bytes: int,
        *,
        count_frame: bool,
    ) -> None:
        if stream not in self._stream_bytes:
            _fail("dual_live_pump_stream_invalid")
        if (
            isinstance(emitted_bytes, bool)
            or not isinstance(emitted_bytes, int)
            or emitted_bytes < 0
        ):
            _fail("dual_live_pump_emitted_bytes_invalid")
        with self._lock:
            next_frames = self._stream_frames[stream] + int(count_frame)
            next_stream_bytes = self._stream_bytes[stream] + emitted_bytes
            next_total_bytes = self._total_bytes + emitted_bytes
            if next_frames > MAX_FRAMES_PER_STREAM:
                _fail("dual_live_pump_frame_count_exceeded")
            if next_stream_bytes > MAX_STREAM_BYTES:
                _fail("dual_live_pump_stream_bytes_exceeded")
            if next_total_bytes > MAX_CAPTURE_BYTES:
                _fail("dual_live_pump_aggregate_bytes_exceeded")
            self._stream_frames[stream] = next_frames
            self._stream_bytes[stream] = next_stream_bytes
            self._total_bytes = next_total_bytes

    def consume(
        self,
        stream: str,
        payload_bytes: int,
        *,
        emitted_bytes: int | None = None,
    ) -> None:
        if (
            isinstance(payload_bytes, bool)
            or not isinstance(payload_bytes, int)
            or payload_bytes <= 0
            or payload_bytes > MAX_FRAME_BYTES
        ):
            _fail("dual_live_pump_frame_bytes_invalid")
        actual_emitted = payload_bytes if emitted_bytes is None else emitted_bytes
        if (
            isinstance(actual_emitted, bool)
            or not isinstance(actual_emitted, int)
            or actual_emitted < 0
            or actual_emitted > payload_bytes + 1
        ):
            _fail("dual_live_pump_emitted_bytes_invalid")
        self._reserve(stream, actual_emitted, count_frame=True)

    def consume_wrapper(self, stream: str, emitted_bytes: int) -> None:
        if (
            isinstance(emitted_bytes, bool)
            or not isinstance(emitted_bytes, int)
            or emitted_bytes <= 0
        ):
            _fail("dual_live_pump_emitted_bytes_invalid")
        self._reserve(stream, emitted_bytes, count_frame=False)


def decode_child_status_frame(
    payload: bytes,
    *,
    expected_phase: str,
    expected_process_boot_id: str,
    expected_status_nonce_sha256: str,
    expected_ordinal: int,
) -> dict[str, Any]:
    if (
        not isinstance(payload, bytes)
        or not payload
        or expected_phase not in {"A", "B"}
        or not isinstance(expected_process_boot_id, str)
        or _LOWERCASE_SHA256.fullmatch(expected_process_boot_id) is None
        or not isinstance(expected_status_nonce_sha256, str)
        or _LOWERCASE_SHA256.fullmatch(expected_status_nonce_sha256) is None
        or isinstance(expected_ordinal, bool)
        or not isinstance(expected_ordinal, int)
        or expected_ordinal <= 0
    ):
        _fail("dual_live_child_status_invalid")
    try:
        value = strict_json_loads(payload)
    except (TypeError, ValueError):
        _fail("dual_live_child_status_invalid")
    if (
        type(value) is not dict
        or canonical_json_bytes(value) != payload
        or tuple(value)
        != (
            "event",
            "ordinal",
            "payload",
            "phase",
            "process_boot_id",
            "schema_id",
            "status_nonce_sha256",
        )
        or value["schema_id"] != CHILD_STATUS_SCHEMA_ID
        or value["phase"] != expected_phase
        or value["process_boot_id"] != expected_process_boot_id
        or value["status_nonce_sha256"] != expected_status_nonce_sha256
        or value["ordinal"] != expected_ordinal
        or value["event"] != "logger_census"
        or type(value["payload"]) is not dict
        or tuple(value["payload"])
        != ("census_point", "handler_count", "topology_sha256")
        or value["payload"]["census_point"] not in {"pre_activity", "exit"}
        or isinstance(value["payload"]["handler_count"], bool)
        or not isinstance(value["payload"]["handler_count"], int)
        or value["payload"]["handler_count"] < 0
        or not isinstance(value["payload"]["topology_sha256"], str)
        or _LOWERCASE_SHA256.fullmatch(value["payload"]["topology_sha256"])
        is None
    ):
        _fail("dual_live_child_status_invalid")
    return dict(value)


def _reader_alias_keys(reader: BinaryIO) -> tuple[tuple[object, ...], ...]:
    """Return only safely-derived identities for one child pipe reader."""

    code = "dual_live_controller_child_invalid"
    keys: list[tuple[object, ...]] = []
    try:
        fileno = getattr(reader, "fileno", None)
        handle = getattr(reader, "handle", None)
    except Exception as exc:
        raise DualLiveRuntimeError(code) from exc

    descriptor: int | None = None
    if fileno is not None:
        if not callable(fileno):
            _fail(code)
        try:
            candidate = fileno()
        except (OSError, ValueError):
            candidate = None
        except Exception as exc:
            raise DualLiveRuntimeError(code) from exc
        if candidate is not None:
            if type(candidate) is not int or candidate < 0:
                _fail(code)
            descriptor = candidate
            keys.append(("descriptor", descriptor))

    if handle is not None:
        if type(handle) is not int or handle <= 0:
            _fail(code)
        keys.append(("handle", handle))

    if descriptor is not None:
        try:
            source = os.fstat(descriptor)
        except (OSError, ValueError):
            source = None
        except Exception as exc:
            raise DualLiveRuntimeError(code) from exc
        if source is not None:
            device = int(source.st_dev)
            inode = int(source.st_ino)
            if device != 0 or inode != 0:
                keys.append(("source", device, inode))
    return tuple(keys)


def _validate_windows_reader_descriptors_distinct(
    descriptors: tuple[int, ...],
) -> None:
    """Fail closed unless every exposed Windows pipe descriptor is distinct."""

    if os.name != "nt" or len(descriptors) < 2:
        return
    code = "dual_live_controller_child_invalid"
    try:
        from app.services.dual_live_windows import pipe_descriptors_same
    except Exception as exc:
        raise DualLiveRuntimeError(code) from exc
    for index, left in enumerate(descriptors):
        for right in descriptors[index + 1 :]:
            try:
                same = pipe_descriptors_same(left, right)
            except Exception as exc:
                raise DualLiveRuntimeError(code) from exc
            if type(same) is not bool:
                _fail(code)
            if same:
                _fail("dual_live_pump_reader_alias_invalid")


def _writer_destination_identity(writer: BinaryIO) -> tuple[object, ...]:
    if type(writer) is LockedCampaignSink:
        return _writer_destination_identity(writer._writer)
    if isinstance(writer, io.BytesIO):
        return ("object", id(writer))
    try:
        fileno = getattr(writer, "fileno", None)
    except Exception as exc:
        raise DualLiveRuntimeError("dual_live_pump_writer_invalid") from exc
    if fileno is None:
        _fail("dual_live_pump_writer_invalid")
    if not callable(fileno):
        _fail("dual_live_pump_writer_invalid")
    try:
        descriptor = fileno()
        if type(descriptor) is not int or descriptor < 0:
            _fail("dual_live_pump_writer_invalid")
        destination = os.fstat(descriptor)
    except DualLiveRuntimeError:
        raise
    except Exception as exc:
        raise DualLiveRuntimeError("dual_live_pump_writer_invalid") from exc
    return ("file", int(destination.st_dev), int(destination.st_ino))


class LockedCampaignSink:
    """Serialize all wrapper writes to one capture writer."""

    __slots__ = ("_failed", "_lock", "_stop_latch", "_writer")

    def __init__(self, writer: BinaryIO, *, stop_latch: FirstStopLatch) -> None:
        if (
            not callable(getattr(writer, "write", None))
            or type(stop_latch) is not FirstStopLatch
        ):
            _fail("dual_live_pump_writer_invalid")
        self._writer = writer
        self._stop_latch = stop_latch
        self._failed = False
        self._lock = threading.Lock()

    def write(
        self,
        content: bytes,
        *,
        before_write: Callable[[], None] | None = None,
    ) -> int:
        with self._lock:
            if self._failed:
                _fail("dual_live_pump_writer_poisoned")
            if (
                not isinstance(content, bytes)
                or not content
                or (before_write is not None and not callable(before_write))
            ):
                _fail("dual_live_pump_write_invalid")
            if before_write is not None:
                before_write()
            try:
                written = self._writer.write(content)
            except BaseException as exc:
                self._failed = True
                self._stop_latch.latch("writer_failure")
                if isinstance(exc, Exception):
                    raise DualLiveRuntimeError("dual_live_pump_write_failed") from exc
                raise
            if (
                isinstance(written, bool)
                or not isinstance(written, int)
                or written != len(content)
            ):
                self._failed = True
                self._stop_latch.latch("writer_failure")
                _fail("dual_live_pump_write_failed")
            return written


class FourStreamPumpGroup:
    """Own four bounded frame pumps and the only capture-writer references."""

    __slots__ = (
        "_budget",
        "_cancel_completed_reader_ids",
        "_cancel_errors",
        "_cancel_owned_reader_ids",
        "_cancel_pump_errors",
        "_cancel_start_errors",
        "_cancel_started",
        "_cancel_threads",
        "_errors",
        "_errors_lock",
        "_expected_status_nonce_sha256",
        "_expected_status_phase",
        "_expected_status_process_boot_id",
        "_http_frame_validator",
        "_join_active",
        "_lifecycle_lock",
        "_next_status_ordinal",
        "_readers",
        "_sinks",
        "_started",
        "_started_cancel_threads",
        "_started_threads",
        "_status_callback",
        "_stop_latch",
        "_threads",
    )

    def __init__(
        self,
        *,
        readers: Mapping[str, BinaryIO],
        writers: Mapping[str, BinaryIO],
        status_callback: Callable[[dict[str, Any]], None],
        http_frame_validator: Callable[[bytes], None],
        stop_latch: FirstStopLatch,
        expected_status_phase: str,
        expected_status_process_boot_id: str,
        expected_status_nonce_sha256: str,
        budget: PipeFrameBudget | None = None,
    ) -> None:
        if (
            set(readers) != set(PIPE_STREAM_CLASSES)
            or set(writers) != set(PIPE_STREAM_CLASSES)
            or not callable(status_callback)
            or not callable(http_frame_validator)
            or type(stop_latch) is not FirstStopLatch
            or expected_status_phase not in {"A", "B"}
            or not isinstance(expected_status_process_boot_id, str)
            or _LOWERCASE_SHA256.fullmatch(expected_status_process_boot_id) is None
            or not isinstance(expected_status_nonce_sha256, str)
            or _LOWERCASE_SHA256.fullmatch(expected_status_nonce_sha256) is None
            or (budget is not None and type(budget) is not PipeFrameBudget)
        ):
            _fail("dual_live_pump_arguments_invalid")
        copied_readers = dict(readers)
        if any(
            not callable(getattr(reader, "read", None))
            or not callable(getattr(reader, "close", None))
            for reader in copied_readers.values()
        ):
            _fail("dual_live_pump_reader_invalid")
        copied_writers = dict(writers)
        if any(
            not callable(getattr(writer, "write", None))
            for writer in copied_writers.values()
        ):
            _fail("dual_live_pump_writer_invalid")
        writer_destinations = tuple(
            _writer_destination_identity(copied_writers[stream])
            for stream in PIPE_STREAM_CLASSES
        )
        if len(set(writer_destinations)) != len(PIPE_STREAM_CLASSES):
            _fail("dual_live_pump_writer_alias_invalid")
        self._readers = copied_readers
        self._sinks = {
            stream: LockedCampaignSink(
                copied_writers[stream],
                stop_latch=stop_latch,
            )
            for stream in PIPE_STREAM_CLASSES
        }
        self._status_callback = status_callback
        self._http_frame_validator = http_frame_validator
        self._stop_latch = stop_latch
        self._expected_status_phase = expected_status_phase
        self._expected_status_process_boot_id = expected_status_process_boot_id
        self._expected_status_nonce_sha256 = expected_status_nonce_sha256
        self._next_status_ordinal = 1
        self._budget = PipeFrameBudget() if budget is None else budget
        self._errors: dict[str, BaseException] = {}
        self._cancel_errors: dict[str, BaseException] = {}
        self._cancel_pump_errors: dict[str, BaseException] = {}
        self._cancel_start_errors: dict[str, BaseException] = {}
        self._cancel_owned_reader_ids: set[int] = set()
        self._cancel_completed_reader_ids: set[int] = set()
        self._errors_lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._started = False
        self._join_active = False
        self._cancel_started = False
        self._threads: tuple[threading.Thread, ...] = ()
        self._started_threads: tuple[threading.Thread, ...] = ()
        self._cancel_threads: tuple[threading.Thread, ...] = ()
        self._started_cancel_threads: tuple[threading.Thread, ...] = ()

    @property
    def threads_alive(self) -> tuple[str, ...]:
        with self._lifecycle_lock:
            return tuple(
                thread.name
                for thread in self._started_threads
                if thread.is_alive()
            )

    def app_write(self, content: bytes) -> int:
        """Write one wrapper-owned runtime-record line under the app lock."""

        return self._sinks["app"].write(
            content,
            before_write=lambda: self._budget.consume_wrapper("app", len(content)),
        )

    def _write_frame(self, stream: str, payload: bytes) -> None:
        output = payload
        if stream == "app":
            try:
                value = strict_json_loads(payload)
            except (TypeError, ValueError):
                _fail("dual_live_app_frame_invalid")
            if type(value) is not dict or canonical_json_bytes(value) != payload:
                _fail("dual_live_app_frame_invalid")
            if value.get("schema_id") == CHILD_STATUS_SCHEMA_ID:
                status = decode_child_status_frame(
                    payload,
                    expected_phase=self._expected_status_phase,
                    expected_process_boot_id=self._expected_status_process_boot_id,
                    expected_status_nonce_sha256=(
                        self._expected_status_nonce_sha256
                    ),
                    expected_ordinal=self._next_status_ordinal,
                )
                self._next_status_ordinal += 1
                self._budget.consume(stream, len(payload), emitted_bytes=0)
                try:
                    result = self._status_callback(status)
                except Exception as exc:
                    raise DualLiveRuntimeError(
                        "dual_live_child_status_callback_invalid"
                    ) from exc
                if result is not None:
                    _fail("dual_live_child_status_callback_invalid")
                return
            if value.get("schema_id") == CHILD_CONTROL_SCHEMA_ID:
                _fail("dual_live_app_frame_reserved_schema")
            output = payload + b"\n"
        elif stream == "http":
            try:
                result = self._http_frame_validator(payload)
            except Exception as exc:
                raise DualLiveRuntimeError(
                    "dual_live_http_frame_validator_invalid"
                ) from exc
            if result is not None:
                _fail("dual_live_http_frame_validator_invalid")
            output = payload + b"\n"
        with self._errors_lock:
            write_started_before_cancel = not self._cancel_started
        try:
            self._sinks[stream].write(
                output,
                before_write=lambda: self._budget.consume(
                    stream,
                    len(payload),
                    emitted_bytes=len(output),
                ),
            )
        except BaseException as exc:
            self._record_pump_error(
                stream,
                exc,
                force_pre_cancel=write_started_before_cancel,
            )
            raise

    def _pump(self, stream: str) -> None:
        try:
            reader = self._readers[stream]
            while True:
                if stream == "app":
                    payload = _read_pipe_frame(
                        reader,
                        allowed_reserved_schema_ids=frozenset(
                            (CHILD_STATUS_SCHEMA_ID,)
                        ),
                    )
                else:
                    payload = read_pipe_frame(reader)
                if payload is None:
                    return
                self._write_frame(stream, payload)
        except BaseException as exc:
            self._record_pump_error(stream, exc)

    def _record_pump_error(
        self,
        stream: str,
        error: BaseException,
        *,
        force_pre_cancel: bool = False,
    ) -> None:
        with self._errors_lock:
            if self._errors.get(stream) is error:
                return
            if force_pre_cancel or not self._cancel_started:
                self._errors.setdefault(stream, error)
                self._stop_latch.latch("pump_failure")
            else:
                self._cancel_pump_errors.setdefault(stream, error)

    def _error_snapshot(self) -> tuple[tuple[str, BaseException], ...]:
        with self._errors_lock:
            return tuple(
                (stream, self._errors[stream])
                for stream in PIPE_STREAM_CLASSES
                if stream in self._errors
            )

    def _cancel_error_snapshot(self) -> tuple[tuple[str, BaseException], ...]:
        with self._errors_lock:
            return tuple(
                (stream, self._cancel_errors[stream])
                for stream in PIPE_STREAM_CLASSES
                if stream in self._cancel_errors
            )

    def _cancel_start_error_snapshot(
        self,
    ) -> tuple[tuple[str, BaseException], ...]:
        with self._errors_lock:
            return tuple(
                (stream, self._cancel_start_errors[stream])
                for stream in PIPE_STREAM_CLASSES
                if stream in self._cancel_start_errors
            )

    def _join_until(self, deadline: float) -> None:
        for thread in self._started_threads:
            thread.join(max(0.0, deadline - time.monotonic()))

    def _join_cancel_until(self, deadline: float) -> None:
        for thread in self._started_cancel_threads:
            thread.join(max(0.0, deadline - time.monotonic()))

    def _cancel_reader(self, stream: str, reader: BinaryIO) -> None:
        try:
            reader.close()
        except Exception as exc:
            with self._errors_lock:
                self._cancel_errors.setdefault(stream, exc)
        finally:
            with self._errors_lock:
                self._cancel_completed_reader_ids.add(id(reader))

    def _begin_cancellation(self) -> None:
        unique_readers: list[tuple[str, BinaryIO]] = []
        seen_reader_ids: set[int] = set()
        for stream in PIPE_STREAM_CLASSES:
            reader = self._readers[stream]
            if id(reader) in seen_reader_ids:
                continue
            seen_reader_ids.add(id(reader))
            unique_readers.append((stream, reader))
        with self._errors_lock:
            if self._cancel_started:
                return
            if not self._errors:
                self._stop_latch.latch("timeout")
            self._cancel_started = True
        self._cancel_threads = tuple(
            threading.Thread(
                target=self._cancel_reader,
                args=(stream, reader),
                name=f"dual-live-{stream}-cancel",
                daemon=True,
            )
            for stream, reader in unique_readers
        )
        started_threads: list[threading.Thread] = []
        for (stream, reader), thread in zip(
            unique_readers,
            self._cancel_threads,
            strict=True,
        ):
            try:
                thread.start()
            except BaseException as exc:
                with self._errors_lock:
                    self._cancel_start_errors.setdefault(stream, exc)
                continue
            started_threads.append(thread)
            with self._errors_lock:
                self._cancel_owned_reader_ids.add(id(reader))
            with self._lifecycle_lock:
                self._started_cancel_threads = tuple(started_threads)

    @staticmethod
    def _cancel_failure_cause(
        cancel_errors: tuple[tuple[str, BaseException], ...],
        cancel_start_errors: tuple[tuple[str, BaseException], ...],
    ) -> DualLiveRuntimeError:
        if cancel_start_errors:
            failure = DualLiveRuntimeError("dual_live_pump_cancel_start_failed")
            failure.__cause__ = cancel_start_errors[0][1]
            return failure
        if not cancel_errors:
            return DualLiveRuntimeError("dual_live_pump_cancel_stuck")
        failure = DualLiveRuntimeError("dual_live_pump_cancel_reader_failed")
        failure.__cause__ = cancel_errors[0][1]
        return failure

    def start(self) -> None:
        with self._lifecycle_lock:
            if self._started:
                _fail("dual_live_pump_already_started")
            self._started = True
            self._threads = tuple(
                threading.Thread(
                    target=self._pump,
                    args=(stream,),
                    name=f"dual-live-{stream}-pump",
                    daemon=True,
                )
                for stream in PIPE_STREAM_CLASSES
            )
            started_threads: list[threading.Thread] = []
            try:
                for thread in self._threads:
                    thread.start()
                    started_threads.append(thread)
            finally:
                self._started_threads = tuple(started_threads)

    @property
    def has_live_workers(self) -> bool:
        with self._lifecycle_lock:
            return any(
                thread.is_alive()
                for thread in (
                    self._started_threads + self._started_cancel_threads
                )
            )

    @property
    def cancellation_reader_custody(
        self,
    ) -> tuple[frozenset[int], frozenset[int]]:
        with self._errors_lock:
            return (
                frozenset(self._cancel_owned_reader_ids),
                frozenset(self._cancel_completed_reader_ids),
            )

    def wait_for_writer_release(self, *, timeout: float) -> bool:
        """Passively prove that no pump thread retains capture-writer access."""

        with self._lifecycle_lock:
            if (
                not self._started
                or isinstance(timeout, bool)
                or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout)
                or timeout < 0
                or self._join_active
            ):
                _fail("dual_live_pump_join_invalid")
            self._join_active = True
        try:
            self._join_until(time.monotonic() + timeout)
            released = not any(
                thread.is_alive() for thread in self._started_threads
            )
            if released:
                pump_errors = self._error_snapshot()
                if pump_errors:
                    raise DualLiveRuntimeError("dual_live_pump_failed") from (
                        pump_errors[0][1]
                    )
            return released
        finally:
            with self._lifecycle_lock:
                self._join_active = False

    def join(self, *, timeout: float) -> None:
        with self._lifecycle_lock:
            if (
                not self._started
                or isinstance(timeout, bool)
                or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout)
                or timeout < 0
            ):
                _fail("dual_live_pump_join_invalid")
            if self._join_active:
                _fail("dual_live_pump_join_in_progress")
            self._join_active = True
        try:
            self._join_until(time.monotonic() + timeout)
            alive = any(thread.is_alive() for thread in self._started_threads)
            if not alive:
                pump_errors = self._error_snapshot()
                cancel_errors = self._cancel_error_snapshot()
                cancel_start_errors = self._cancel_start_error_snapshot()
                cancel_alive = any(
                    thread.is_alive() for thread in self._started_cancel_threads
                )
                if cancel_alive or cancel_errors or cancel_start_errors:
                    raise DualLiveRuntimeError(
                        "dual_live_pump_cancel_failed"
                    ) from self._cancel_failure_cause(
                        cancel_errors,
                        cancel_start_errors,
                    )
                if pump_errors:
                    raise DualLiveRuntimeError("dual_live_pump_failed") from (
                        pump_errors[0][1]
                    )
                return

            self._begin_cancellation()
            cancel_deadline = time.monotonic() + PUMP_CANCEL_JOIN_SECONDS
            self._join_until(cancel_deadline)
            self._join_cancel_until(cancel_deadline)

            final_pump_errors = self._error_snapshot()
            cancel_errors = self._cancel_error_snapshot()
            cancel_start_errors = self._cancel_start_error_snapshot()
            still_alive = any(
                thread.is_alive() for thread in self._started_threads
            )
            cancel_alive = any(
                thread.is_alive() for thread in self._started_cancel_threads
            )
            if (
                still_alive
                or cancel_alive
                or cancel_errors
                or cancel_start_errors
            ):
                raise DualLiveRuntimeError("dual_live_pump_cancel_failed") from (
                    self._cancel_failure_cause(
                        cancel_errors,
                        cancel_start_errors,
                    )
                )
            if final_pump_errors:
                raise DualLiveRuntimeError("dual_live_pump_failed") from (
                    final_pump_errors[0][1]
                )
            raise DualLiveRuntimeError("dual_live_pump_join_timeout")
        finally:
            with self._lifecycle_lock:
                self._join_active = False


@dataclass(frozen=True, slots=True)
class _ControllerChild:
    """Private kernel projection with trusted bounded dispatch/exit adapters.

    ``send_control`` remains a private/test seam until an owned, bounded,
    cancelable PhaseChannels dispatcher synchronously sets Phase A revocation
    and the child rechecks that revocation before enabling egress.
    """

    process_boot_id: str
    process_creation_identity_sha256: str
    executable_sha256: str
    job_policy_sha256: str
    status_nonce_sha256: str
    control_nonce: str
    readers: Mapping[str, BinaryIO]
    send_control: Callable[[bytes], None]
    wait: Callable[[float], int | None]
    stop: Callable[[], None]

    def __post_init__(self) -> None:
        code = "dual_live_controller_child_invalid"
        for value in (
            self.process_boot_id,
            self.process_creation_identity_sha256,
            self.executable_sha256,
            self.job_policy_sha256,
            self.status_nonce_sha256,
            self.control_nonce,
        ):
            _require_sha256(value, code)
        if not isinstance(self.readers, Mapping):
            _fail(code)
        readers = dict(self.readers)
        if set(readers) != set(PIPE_STREAM_CLASSES) or any(
            not callable(getattr(reader, "read", None))
            or not callable(getattr(reader, "close", None))
            for reader in readers.values()
        ):
            _fail(code)
        reader_values = tuple(readers[stream] for stream in PIPE_STREAM_CLASSES)
        if len({id(reader) for reader in reader_values}) != len(reader_values):
            _fail("dual_live_pump_reader_alias_invalid")
        seen_reader_keys: set[tuple[object, ...]] = set()
        reader_descriptors: list[int] = []
        for reader in reader_values:
            alias_keys = _reader_alias_keys(reader)
            for key in alias_keys:
                if key in seen_reader_keys:
                    _fail("dual_live_pump_reader_alias_invalid")
                seen_reader_keys.add(key)
                if key[0] == "descriptor":
                    descriptor = key[1]
                    if type(descriptor) is not int:
                        _fail(code)
                    reader_descriptors.append(descriptor)
        _validate_windows_reader_descriptors_distinct(tuple(reader_descriptors))
        if not all(
            callable(callback)
            for callback in (self.send_control, self.wait, self.stop)
        ):
            _fail(code)
        object.__setattr__(self, "readers", readers)


def _run_two_phase_controller(
    *,
    identity: RuntimeIdentity,
    runtime_start_payload: Mapping[str, Any],
    writers: Mapping[str, BinaryIO],
    create_phase_a: Callable[[], _ControllerChild],
    create_phase_b: Callable[[], _ControllerChild],
    quiesce_phase: Callable[
        [str, _ControllerChild],
        tuple[Mapping[str, Any], Mapping[str, Any]],
    ],
    clear_authority: Callable[[str, _ControllerChild], Mapping[str, Any]],
    http_frame_validator: Callable[[bytes], None],
    seal: Callable[[], Any],
    timeout_seconds: float,
) -> Any:
    """Run the bounded mechanical A/B spine; no production semantics live here."""

    if (
        type(identity) is not RuntimeIdentity
        or not isinstance(runtime_start_payload, Mapping)
        or not isinstance(writers, Mapping)
        or not all(
            callable(callback)
            for callback in (
                create_phase_a,
                create_phase_b,
                quiesce_phase,
                clear_authority,
                http_frame_validator,
                seal,
            )
        )
        or isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        _fail("dual_live_controller_invalid")
    capture_writers = dict(writers)
    if set(capture_writers) != set(PIPE_STREAM_CLASSES) or any(
        not callable(getattr(writer, method, None))
        for writer in capture_writers.values()
        for method in ("write", "flush", "close")
    ):
        _fail("dual_live_controller_invalid")
    destinations = tuple(
        _writer_destination_identity(capture_writers[stream])
        for stream in PIPE_STREAM_CLASSES
    )
    if len(set(destinations)) != len(PIPE_STREAM_CLASSES):
        _fail("dual_live_pump_writer_alias_invalid")

    stop_latch = FirstStopLatch()
    shared_sinks = {
        stream: LockedCampaignSink(
            capture_writers[stream],
            stop_latch=stop_latch,
        )
        for stream in PIPE_STREAM_CLASSES
    }
    shared_budget = PipeFrameBudget()
    runtime_writer = RuntimeRecordWriter(
        lambda content: shared_sinks["app"].write(
            content,
            before_write=lambda: shared_budget.consume_wrapper(
                "app", len(content)
            ),
        ),
        identity=identity,
    )
    stop_recorded = False
    capture_close_safe = True

    def record_stop_once() -> None:
        nonlocal stop_recorded
        snapshot = stop_latch.snapshot
        if stop_recorded or snapshot is None:
            return
        reason_code, monotonic_tick_ns = snapshot
        runtime_writer.append(
            phase="wrapper",
            event="stop_latched",
            process_boot_id=None,
            payload={
                "reason_code": reason_code,
                "monotonic_tick_ns": monotonic_tick_ns,
            },
        )
        stop_recorded = True

    def normalized_error(
        code: str,
        reason_code: str,
        cause: BaseException,
    ) -> DualLiveRuntimeError:
        stop_latch.latch(reason_code)
        error = DualLiveRuntimeError(code)
        error.__cause__ = cause
        return error

    def close_readers(
        child: _ControllerChild,
        *,
        excluded_reader_ids: frozenset[int] = frozenset(),
    ) -> BaseException | None:
        first_error: BaseException | None = None
        seen: set[int] = set()
        for stream in PIPE_STREAM_CLASSES:
            reader = child.readers[stream]
            if id(reader) in seen or id(reader) in excluded_reader_ids:
                continue
            seen.add(id(reader))
            try:
                reader.close()
            except BaseException as exc:
                if first_error is None:
                    first_error = exc
        return first_error

    def run_phase(
        phase: str,
        factory: Callable[[], _ControllerChild],
    ) -> str:
        nonlocal capture_close_safe
        child: _ControllerChild | None = None
        pumps: FourStreamPumpGroup | None = None
        control: PhaseControlState | None = None
        census_ready = threading.Event()
        census_points: list[tuple[str, int, str]] = []
        phase_error: BaseException | None = None
        exit_code: int | None = None
        exit_proven = False
        stop_called = False
        stopped = False

        def is_writer_failure(error: BaseException) -> bool:
            current: BaseException | None = error
            seen: set[int] = set()
            writer_codes = {
                "dual_live_pump_write_failed",
                "dual_live_pump_writer_poisoned",
                "dual_live_runtime_writer_failure",
                "dual_live_runtime_writer_poisoned",
            }
            while current is not None and id(current) not in seen:
                seen.add(id(current))
                if (
                    isinstance(current, DualLiveRuntimeError)
                    and current.code in writer_codes
                ):
                    return True
                current = current.__cause__
            return False

        def fail(code: str, reason_code: str, cause: BaseException) -> None:
            nonlocal phase_error
            if reason_code == "writer_failure":
                code = "dual_live_runtime_writer_failure"
            replacement = normalized_error(code, reason_code, cause)
            if phase_error is None:
                phase_error = replacement
            elif reason_code == "writer_failure":
                replacement.__context__ = phase_error
                phase_error = replacement

        def stop_child_once() -> None:
            nonlocal stop_called, stopped
            if child is None or stop_called:
                return
            stop_called = True
            try:
                result = child.stop()
                if result is not None:
                    _fail("dual_live_child_stop_invalid")
                stopped = True
            except BaseException as exc:
                fail("dual_live_child_stop_failed", "protocol_failure", exc)

        def record_stop_if_latched() -> None:
            try:
                record_stop_once()
            except BaseException as exc:
                fail("dual_live_runtime_writer_failure", "writer_failure", exc)

        def close_controller_owned_readers() -> None:
            nonlocal capture_close_safe
            if child is None:
                return
            cancellation_owned_reader_ids: frozenset[int] = frozenset()
            if pumps is not None:
                if pumps.has_live_workers:
                    capture_close_safe = False
                    return
                owned, completed = pumps.cancellation_reader_custody
                if owned != completed:
                    capture_close_safe = False
                    return
                cancellation_owned_reader_ids = owned
            reader_error = close_readers(
                child,
                excluded_reader_ids=cancellation_owned_reader_ids,
            )
            if reader_error is not None:
                fail(
                    "dual_live_reader_close_failed",
                    "protocol_failure",
                    reader_error,
                )
                record_stop_if_latched()

        def poll_child_exit(
            deadline: float,
            *,
            observe_stop: bool,
        ) -> int:
            if child is None:
                _fail("dual_live_controller_child_invalid")
            while True:
                if observe_stop and stop_latch.is_set:
                    _fail("dual_live_phase_stopped")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    if observe_stop:
                        stop_latch.latch("timeout")
                    _fail("dual_live_phase_exit_timeout")

                poll_seconds = min(_CHILD_WAIT_POLL_SECONDS, remaining)
                poll_started = time.monotonic()
                result = child.wait(poll_seconds)
                if result is None:
                    unused_poll = poll_seconds - (time.monotonic() - poll_started)
                    if unused_poll > 0:
                        if observe_stop:
                            stop_latch.wait(unused_poll)
                        else:
                            time.sleep(unused_poll)
                    continue
                if (
                    isinstance(result, bool)
                    or not isinstance(result, int)
                    or result < 0
                ):
                    _fail("dual_live_phase_exit_invalid")
                return result

        try:
            candidate = factory()
            if type(candidate) is not _ControllerChild:
                _fail("dual_live_controller_child_invalid")
            child = candidate
            control = PhaseControlState(
                phase=phase,
                control_nonce_sha256=hashlib.sha256(
                    child.control_nonce.encode("ascii")
                ).hexdigest(),
                stop_latch=stop_latch,
            )
            runtime_writer.append(
                phase=phase,
                event="phase_child_start",
                process_boot_id=child.process_boot_id,
                payload={
                    "process_creation_identity_sha256": (
                        child.process_creation_identity_sha256
                    ),
                    "executable_sha256": child.executable_sha256,
                    "job_policy_sha256": child.job_policy_sha256,
                },
            )

            def status_callback(status: dict[str, Any]) -> None:
                point = status["payload"]["census_point"]
                handler_count = status["payload"]["handler_count"]
                topology_sha256 = status["payload"]["topology_sha256"]
                if point == "pre_activity":
                    if census_points or control is None:
                        _fail("dual_live_logger_census_invalid")
                    census_points.append((point, handler_count, topology_sha256))
                    runtime_writer.append(
                        phase=phase,
                        event="logger_census",
                        process_boot_id=child.process_boot_id,
                        payload={
                            "census_point": point,
                            "topology_sha256": topology_sha256,
                            "handler_count": handler_count,
                            "guard_state": f"{phase}_CENSUS_OK",
                            "topology_matches_initial": True,
                        },
                    )
                    control.mark_census_ready()
                    census_ready.set()
                    return
                control_state = None if control is None else control.state
                if (
                    point != "exit"
                    or len(census_points) != 1
                    or (
                        control_state not in {"go_in_flight", "go_dispatched"}
                        and not (
                            control_state == "stopped" and stop_latch.is_set
                        )
                    )
                ):
                    _fail("dual_live_logger_census_invalid")
                initial = census_points[0]
                matches = (handler_count, topology_sha256) == initial[1:]
                census_points.append((point, handler_count, topology_sha256))
                runtime_writer.append(
                    phase=phase,
                    event="logger_census",
                    process_boot_id=child.process_boot_id,
                    payload={
                        "census_point": point,
                        "topology_sha256": topology_sha256,
                        "handler_count": handler_count,
                        "guard_state": f"{phase}_STOPPED",
                        "topology_matches_initial": matches,
                    },
                )
                if not matches:
                    _fail("dual_live_logger_topology_changed")

            pumps = FourStreamPumpGroup(
                readers=child.readers,
                writers=shared_sinks,
                status_callback=status_callback,
                http_frame_validator=http_frame_validator,
                stop_latch=stop_latch,
                expected_status_phase=phase,
                expected_status_process_boot_id=child.process_boot_id,
                expected_status_nonce_sha256=child.status_nonce_sha256,
                budget=shared_budget,
            )
            pumps.start()
            deadline = time.monotonic() + timeout_seconds
            while not census_ready.wait(min(0.05, max(0.0, deadline - time.monotonic()))):
                if stop_latch.is_set or time.monotonic() >= deadline:
                    _fail("dual_live_phase_census_failed")
            if stop_latch.is_set:
                _fail("dual_live_phase_census_failed")
            control_frame = encode_child_control_frame(
                phase=phase,
                command="GO",
                control_nonce=child.control_nonce,
            )
            control.consume_frame(io.BytesIO(control_frame))
            if not control.commit_go_if_clear():
                _fail("dual_live_phase_stopped")
            dispatched = False
            try:
                runtime_writer.append(
                    phase=phase,
                    event="phase_go",
                    process_boot_id=child.process_boot_id,
                    payload={
                        "prior_state": f"{phase}_CENSUS_OK",
                        "next_state": f"{phase}_GO",
                        "control_nonce_sha256": hashlib.sha256(
                            child.control_nonce.encode("ascii")
                        ).hexdigest(),
                    },
                )
                if stop_latch.is_set:
                    _fail("dual_live_phase_stopped")
                result = child.send_control(control_frame)
                if result is not None:
                    _fail("dual_live_phase_control_invalid")
                dispatched = True
            except BaseException:
                stop_latch.latch("protocol_failure")
                raise
            finally:
                control.finish_go_dispatch(dispatched=dispatched)
            if stop_latch.is_set:
                _fail("dual_live_phase_stopped")
            exit_code = poll_child_exit(deadline, observe_stop=True)
            exit_proven = True
            if stop_latch.is_set:
                _fail("dual_live_phase_stopped")
            if exit_code != 0:
                stop_latch.latch("child_exit_nonzero")
                _fail("dual_live_phase_failed")
        except BaseException as exc:
            reason = stop_latch.reason_code
            if reason is None:
                if (
                    isinstance(exc, DualLiveRuntimeError)
                    and exc.code == "dual_live_phase_census_failed"
                ):
                    reason = "logger_census_failure"
                elif (
                    isinstance(exc, DualLiveRuntimeError)
                    and exc.code == "dual_live_phase_failed"
                ):
                    reason = "child_exit_nonzero"
                else:
                    reason = "protocol_failure"
            fail(
                (
                    exc.code
                    if isinstance(exc, DualLiveRuntimeError)
                    else "dual_live_phase_failed"
                ),
                reason,
                exc,
            )

        if phase_error is not None:
            record_stop_if_latched()
        stop_child_once()
        if phase_error is not None and not stop_recorded:
            record_stop_if_latched()

        if child is not None and not exit_proven:
            exit_deadline = time.monotonic() + min(
                timeout_seconds,
                PUMP_CANCEL_JOIN_SECONDS,
            )
            try:
                exit_code = poll_child_exit(
                    exit_deadline,
                    observe_stop=False,
                )
                exit_proven = True
            except BaseException as exc:
                fail(
                    (
                        exc.code
                        if isinstance(exc, DualLiveRuntimeError)
                        else "dual_live_phase_exit_unproven"
                    ),
                    "protocol_failure",
                    exc,
                )
                record_stop_if_latched()

        if child is not None and not exit_proven:
            if pumps is not None:
                capture_close_safe = False
                try:
                    capture_close_safe = pumps.wait_for_writer_release(
                        timeout=min(timeout_seconds, PUMP_CANCEL_JOIN_SECONDS)
                    )
                except BaseException as exc:
                    capture_close_safe = not pumps.has_live_workers
                    if is_writer_failure(exc):
                        fail(
                            "dual_live_runtime_writer_failure",
                            "writer_failure",
                            exc,
                        )
                    else:
                        fail("dual_live_pump_failed", "pump_failure", exc)
                    record_stop_if_latched()
            if capture_close_safe:
                close_controller_owned_readers()
            if phase_error is None:
                phase_error = normalized_error(
                    "dual_live_phase_exit_unproven",
                    "protocol_failure",
                    DualLiveRuntimeError("dual_live_phase_exit_unproven"),
                )
                record_stop_if_latched()
            raise phase_error

        workers_quiesced = pumps is None
        if pumps is not None:
            try:
                pumps.join(timeout=timeout_seconds)
                workers_quiesced = True
            except BaseException as exc:
                if is_writer_failure(exc):
                    fail(
                        "dual_live_runtime_writer_failure",
                        "writer_failure",
                        exc,
                    )
                else:
                    fail("dual_live_pump_failed", "pump_failure", exc)
                workers_quiesced = not pumps.has_live_workers
                if not workers_quiesced:
                    capture_close_safe = False
                record_stop_if_latched()
        if workers_quiesced:
            close_controller_owned_readers()
        if (
            phase_error is None
            and control is not None
            and len(census_points) == 2
        ):
            try:
                control.complete()
            except BaseException as exc:
                fail("dual_live_phase_incomplete", "protocol_failure", exc)

        if phase_error is not None:
            record_stop_if_latched()

        if child is not None:
            authority_payload: dict[str, Any] | None = None
            if phase == "A":
                try:
                    validated_authority_payload = _validate_payload(
                        "authority_cleared",
                        clear_authority(phase, child),
                    )
                    if (
                        validated_authority_payload["all_required_absent"]
                        is not True
                    ):
                        _fail("dual_live_authority_clear_invalid")
                    authority_payload = validated_authority_payload
                except BaseException as exc:
                    if is_writer_failure(exc):
                        fail(
                            "dual_live_runtime_writer_failure",
                            "writer_failure",
                            exc,
                        )
                    else:
                        fail(
                            "dual_live_authority_clear_failed",
                            "protocol_failure",
                            exc,
                        )
                    try:
                        record_stop_once()
                    except BaseException:
                        pass
            quiescence_recorded = False
            try:
                quiescence = quiesce_phase(phase, child)
                if (
                    type(quiescence) is not tuple
                    or len(quiescence) != 2
                    or not all(isinstance(item, Mapping) for item in quiescence)
                ):
                    _fail("dual_live_quiescence_invalid")
                socket_payload, job_payload = quiescence
                socket_record = runtime_writer.append(
                    phase=phase,
                    event="socket_census",
                    process_boot_id=child.process_boot_id,
                    payload=socket_payload,
                )
                if socket_record["payload"]["stable"] is not True:
                    _fail("dual_live_quiescence_invalid")
                runtime_writer.append(
                    phase=phase,
                    event="job_zero",
                    process_boot_id=child.process_boot_id,
                    payload=job_payload,
                )
                quiescence_recorded = True
            except BaseException as exc:
                if is_writer_failure(exc):
                    fail(
                        "dual_live_runtime_writer_failure",
                        "writer_failure",
                        exc,
                    )
                else:
                    fail("dual_live_quiescence_failed", "protocol_failure", exc)
                try:
                    record_stop_once()
                except BaseException:
                    pass
            if (
                phase == "A"
                and authority_payload is not None
                and quiescence_recorded
            ):
                try:
                    runtime_writer.append(
                        phase=phase,
                        event="authority_cleared",
                        process_boot_id=child.process_boot_id,
                        payload=authority_payload,
                    )
                except BaseException as exc:
                    if is_writer_failure(exc):
                        fail(
                            "dual_live_runtime_writer_failure",
                            "writer_failure",
                            exc,
                        )
                    else:
                        fail(
                            "dual_live_authority_clear_failed",
                            "protocol_failure",
                            exc,
                        )
                    try:
                        record_stop_once()
                    except BaseException:
                        pass

        if child is None:
            if phase_error is None:
                phase_error = normalized_error(
                    "dual_live_controller_child_invalid",
                    "protocol_failure",
                    DualLiveRuntimeError("dual_live_controller_child_invalid"),
                )
            record_stop_once()

        complete_record: dict[str, Any] | None = None
        if child is not None and exit_code is not None:
            terminal_state = "completed" if phase_error is None else "failed"
            try:
                complete_record = runtime_writer.append(
                    phase=phase,
                    event="phase_complete",
                    process_boot_id=child.process_boot_id,
                    payload={
                        "terminal_state": terminal_state,
                        "exit_code": exit_code,
                    },
                )
            except BaseException as exc:
                fail(
                    "dual_live_runtime_writer_failure",
                    "writer_failure",
                    exc,
                )
        if phase_error is not None:
            raise phase_error
        if not stopped or len(census_points) != 2 or complete_record is None:
            stop_latch.latch("protocol_failure")
            record_stop_once()
            _fail("dual_live_phase_incomplete")
        return complete_record["record_sha256"]

    run_error: BaseException | None = None
    try:
        runtime_writer.append(
            phase="wrapper",
            event="runtime_start",
            process_boot_id=None,
            payload=runtime_start_payload,
        )
        phase_a_sha256 = run_phase("A", create_phase_a)
        if stop_latch.is_set:
            _fail("dual_live_phase_failed")
        phase_b_sha256 = run_phase("B", create_phase_b)
        if stop_latch.is_set:
            _fail("dual_live_phase_failed")
        runtime_writer.append(
            phase="wrapper",
            event="runtime_complete",
            process_boot_id=None,
            payload={
                "phase_a_result_sha256": phase_a_sha256,
                "phase_b_result_sha256": phase_b_sha256,
                "terminal_state": "completed",
            },
        )
    except BaseException as exc:
        run_error = exc

    if not capture_close_safe:
        failure = DualLiveRuntimeError("dual_live_capture_ownership_unproven")
        failure.__cause__ = run_error
        raise failure

    close_error: BaseException | None = None
    for stream in PIPE_STREAM_CLASSES:
        try:
            capture_writers[stream].flush()
        except BaseException as exc:
            if close_error is None:
                close_error = exc
    for stream in PIPE_STREAM_CLASSES:
        try:
            capture_writers[stream].close()
        except BaseException as exc:
            if close_error is None:
                close_error = exc

    if close_error is not None:
        failure = DualLiveRuntimeError("dual_live_capture_close_failed")
        failure.__cause__ = close_error
        failure.__context__ = run_error
        raise failure
    if run_error is not None:
        raise run_error
    return seal()


class CampaignPipeSink:
    __slots__ = ("_bound_handler", "_failed", "_lock", "_pipe_token", "_writer")

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
        self._failed = False
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
            if self._failed:
                _fail("dual_live_logger_pipe_writer_poisoned")
            try:
                written = self._writer.write(frame)
            except BaseException as exc:
                self._failed = True
                if isinstance(exc, Exception):
                    raise DualLiveRuntimeError(
                        "dual_live_logger_pipe_write_failed"
                    ) from exc
                raise
            if (
                isinstance(written, bool)
                or not isinstance(written, int)
                or written != len(frame)
            ):
                self._failed = True
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


def _census_loggers_locked(
    allowed_pipe_tokens: frozenset[str],
) -> dict[str, Any]:
    root = logging.root
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


def census_loggers(allowed_pipe_tokens: frozenset[str]) -> dict[str, Any]:
    _require_allowed_pipe_tokens(allowed_pipe_tokens)
    logging._acquireLock()
    try:
        return _census_loggers_locked(allowed_pipe_tokens)
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
    _require_allowed_pipe_tokens(allowed_pipe_tokens)
    patched: list[tuple[object, str, object]] = []
    logging._acquireLock()
    try:
        initial = _census_loggers_locked(allowed_pipe_tokens)
        root = logging.root
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
            try:
                current = _census_loggers_locked(allowed_pipe_tokens)
                if current != initial:
                    _fail("dual_live_logger_topology_changed")
                return current
            finally:
                _restore_logging_attributes(patched)
        finally:
            logging._releaseLock()

    return _recheck
