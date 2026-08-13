from __future__ import annotations

import hashlib
import io
import logging
import math
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import (
    Any,
    BinaryIO,
    Callable,
    Literal,
    Mapping,
    NoReturn,
    Protocol,
    Sequence,
    cast,
)
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

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
CHILD_BOOT_SCHEMA_ID = "project6.dual_live_owned_boot.v1"
CHILD_PROOF_SCHEMA_ID = "project6.dual_live_child_proof.v1"
_RESERVED_CAPTURE_SCHEMA_IDS = frozenset(
    (
        CHILD_CONTROL_SCHEMA_ID,
        CHILD_STATUS_SCHEMA_ID,
        CHILD_PROOF_SCHEMA_ID,
        RUNTIME_SCHEMA_ID,
    )
)
MAX_FRAME_BYTES = 64 * 1024
MAX_CONTROL_FRAME_BYTES = 4 * 1024
MAX_FRAMES_PER_STREAM = 10_000
MAX_STREAM_BYTES = 16 * 1024 * 1024
MAX_CAPTURE_BYTES = 32 * 1024 * 1024
PUMP_CANCEL_JOIN_SECONDS = 1.0
_CHILD_WAIT_POLL_SECONDS = 0.05
PIPE_STREAM_CLASSES = ("app", "http", "stdout", "stderr")
DUAL_LIVE_CAMPAIGN_RUN_SCHEMA_ID = "project6.dual_live_campaign_run.v1"
DUAL_LIVE_PHASE_TIMEOUT_SCHEMA_ID = "project6.dual_live_phase_timeout.v1"
_PRODUCER_FIXED_OVERHEAD_MILLISECONDS = 30_000
_PRODUCER_PHASE_B_TIMEOUT_MILLISECONDS = 30_000
_PRODUCER_COUNTER_ACK_TIMEOUT_MILLISECONDS = 5_000
_MAX_PHASE_TIMEOUT_MILLISECONDS = 0xFFFFFFFE
_PRODUCER_MAX_PATH_COMPONENTS = 64
_PRODUCER_REQUIRED_ENVIRONMENT = frozenset(
    (
        "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
        "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
        "CONNECTOR_SCIENCEBASE_GRANT_PATH",
        "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
        "CONNECTOR_NRC_APS_GRANT_PATH",
        "CONNECTOR_NRC_APS_GRANT_SHA256",
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256",
        "CONNECTOR_LIVE_EGRESS_ENABLED",
        "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE",
        "DATABASE_URL",
        "STORAGE_DIR",
        "NRC_ADAMS_APS_SUBSCRIPTION_KEY",
    )
)
PHASE_A_AUTHORITY_ENVIRONMENT_NAMES = tuple(
    sorted(
        (
            "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
            "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
            "CONNECTOR_LIVE_EGRESS_ENABLED",
            "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE",
            "CONNECTOR_NRC_APS_GRANT_PATH",
            "CONNECTOR_NRC_APS_GRANT_SHA256",
            "CONNECTOR_SCIENCEBASE_GRANT_PATH",
            "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
            "NRC_ADAMS_APS_SUBSCRIPTION_KEY",
        )
    )
)
_PHASE_A_AUTHORITY_ENVIRONMENT = frozenset(
    PHASE_A_AUTHORITY_ENVIRONMENT_NAMES
)
_PHASE_A_SETTINGS_AUTHORITY_COORDINATES = (
    ("connector_campaign_definition_path", None),
    ("connector_campaign_definition_sha256", None),
    ("connector_live_egress_enabled", False),
    ("connector_live_egress_exclusive_proof_mode", False),
    ("connector_nrc_aps_grant_path", None),
    ("connector_nrc_aps_grant_sha256", None),
    ("connector_sciencebase_grant_path", None),
    ("connector_sciencebase_grant_sha256", None),
    ("nrc_adams_subscription_key", ""),
)
_PHASE_B_REQUIRED_ENVIRONMENT = frozenset(
    (
        "AUTH_OWNER",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256",
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
        "CONNECTOR_LIVE_EGRESS_ENABLED",
        "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE",
        "DATABASE_URL",
        "DEPLOYMENT_MODE",
        "DUAL_LIVE_CAMPAIGN_FINGERPRINT",
        "DUAL_LIVE_CAMPAIGN_ID",
        "DUAL_LIVE_CODE_REVISION",
        "DUAL_LIVE_DEPENDENCY_SET_SHA256",
        "STORAGE_DIR",
        "TRUSTED_PROXY_MODE",
    )
)
_PHASE_B_FORBIDDEN_ENVIRONMENT = frozenset(
    (
        "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
        "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
        "CONNECTOR_NRC_APS_GRANT_PATH",
        "CONNECTOR_NRC_APS_GRANT_SHA256",
        "CONNECTOR_SCIENCEBASE_GRANT_PATH",
        "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
        "NRC_ADAMS_APS_SUBSCRIPTION_KEY",
    )
)
_PHASE_B_RUN_SCAN_CAP = 10_000
_PHASE_B_PACKAGE_KINDS = (
    "canonical_internal",
    "user_facing",
    "review_facing",
)
_PHASE_B_SOURCE_SHAPES = MappingProxyType(
    {
        "nrc_adams_aps": "aps_content_document",
        "sciencebase_mcs": "strict_sciencebase_connector_single_source",
    }
)
_PHASE_B_NO_DELIVERY_FLAGS = (
    "external_handoff_enabled",
    "external_export_enabled",
    "dispatch_enabled",
    "aps_handoff_enabled",
    "external_export_download_enabled",
    "connector_dispatch_enabled",
    "provider_public_url_enabled",
)
_PHASE_B_NRC_ACTIONS = (
    "nrc_preflight",
    "nrc_source_preview",
    "nrc_material_preview",
    "nrc_gate_b_decision",
    "nrc_gate_c_typing",
    "nrc_plan_preview",
    "nrc_plan_approval",
    "nrc_execution_selection",
    "nrc_analysis_execution_start",
    "nrc_execution_result_review",
    "nrc_package_review_preview",
    "nrc_package_construction_commit",
    "nrc_package_review_submit",
    "nrc_handoff_export_prepare",
)
_PHASE_B_SCIENCEBASE_ACTIONS = (
    "sciencebase_material_preview",
    "sciencebase_gate_b_decision",
    "sciencebase_gate_c_typing",
    "sciencebase_plan_preview",
    "sciencebase_plan_approval",
    "sciencebase_execution_selection",
    "sciencebase_analysis_execution_start",
    "sciencebase_execution_result_review",
    "sciencebase_package_review_preview",
    "sciencebase_package_construction_commit",
    "sciencebase_package_review_submit",
    "sciencebase_handoff_export_prepare",
)
_PHASE_B_DOWNSTREAM_ACTIONS = (
    "nrc_strict_parse",
    "nrc_origin_receipt",
    "sciencebase_origin_receipt",
    *_PHASE_B_NRC_ACTIONS,
    *_PHASE_B_SCIENCEBASE_ACTIONS,
)
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
        "dependency_set_sha256",
        "phase_timeout_contract",
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
_CHILD_PROOF_EVENTS = {
    "A": ("acquisition_boundary",),
    "B": ("guard", "downstream_chain", "guard"),
}
_CHILD_PROOF_DENIED_ROUTES = (
    "dns",
    "http",
    "socket",
    "subprocess",
    "connector_transport",
)


class DualLiveRuntimeError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _fail(code: str) -> NoReturn:
    raise DualLiveRuntimeError(code)


class FirstStopLatch:
    """Thread-safe first-reason-wins stop signal for one controller run."""

    __slots__ = (
        "_before_publish",
        "_event",
        "_lock",
        "_monotonic_tick_ns",
        "_publish_failure",
        "_reason_code",
    )

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._before_publish: Callable[[str], None] | None = None
        self._publish_failure: BaseException | None = None
        self._reason_code: str | None = None
        self._monotonic_tick_ns: int | None = None

    def _bind_before_publish(self, callback: Callable[[str], None]) -> None:
        if not callable(callback):
            _fail("dual_live_stop_bridge_invalid")
        with self._lock:
            if (
                self._before_publish is not None
                or self._reason_code is not None
                or self._publish_failure is not None
            ):
                _fail("dual_live_stop_bridge_invalid")
            self._before_publish = callback

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
            if self._publish_failure is not None:
                raise DualLiveRuntimeError(
                    "dual_live_stop_publish_failed"
                ) from self._publish_failure
            if self._reason_code is not None:
                return False
            if self._before_publish is not None:
                try:
                    result = self._before_publish(reason_code)
                    if result is not None:
                        _fail("dual_live_stop_bridge_invalid")
                except BaseException as exc:
                    self._publish_failure = exc
                    self._event.set()
                    raise DualLiveRuntimeError(
                        "dual_live_stop_publish_failed"
                    ) from exc
            self._monotonic_tick_ns = time.monotonic_ns()
            self._reason_code = reason_code
            self._event.set()
            return True

    def commit_if_clear(self) -> bool:
        """Atomically classify a transition before any external I/O begins."""
        with self._lock:
            return self._reason_code is None and self._publish_failure is None

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


def _require_positive_int(value: object, code: str) -> int:
    parsed = _require_nonnegative_int(value, code)
    if parsed == 0:
        _fail(code)
    return parsed


def _validate_phase_timeout_contract(value: object, code: str) -> None:
    contract_keys = (
        "schema_id",
        "phase_a_timeout_ms",
        "phase_b_timeout_ms",
        "fixed_non_egress_overhead_ms",
        "counter_ack_timeout_ms",
        "connector_grants",
    )
    grant_keys = (
        "connector_key",
        "max_physical_requests",
        "request_timeout_seconds",
        "min_request_interval_ms",
    )
    if not isinstance(value, Mapping) or set(value) != set(contract_keys):
        _fail(code)
    if value["schema_id"] != DUAL_LIVE_PHASE_TIMEOUT_SCHEMA_ID:
        _fail(code)
    fixed_overhead = _require_positive_int(
        value["fixed_non_egress_overhead_ms"],
        code,
    )
    counter_ack = _require_positive_int(value["counter_ack_timeout_ms"], code)
    phase_a_timeout = _require_positive_int(value["phase_a_timeout_ms"], code)
    phase_b_timeout = _require_positive_int(value["phase_b_timeout_ms"], code)
    if (
        fixed_overhead != _PRODUCER_FIXED_OVERHEAD_MILLISECONDS
        or counter_ack != _PRODUCER_COUNTER_ACK_TIMEOUT_MILLISECONDS
        or phase_b_timeout != _PRODUCER_PHASE_B_TIMEOUT_MILLISECONDS
        or phase_a_timeout > _MAX_PHASE_TIMEOUT_MILLISECONDS
    ):
        _fail(code)
    grants = value["connector_grants"]
    if not isinstance(grants, (list, tuple)) or len(grants) != 2:
        _fail(code)
    expected_connectors = (
        ("nrc_adams_aps", 2),
        ("sciencebase_mcs", 3),
    )
    derived = fixed_overhead
    for grant, (connector_key, expected_requests) in zip(
        grants,
        expected_connectors,
        strict=True,
    ):
        if not isinstance(grant, Mapping) or set(grant) != set(grant_keys):
            _fail(code)
        requests = _require_positive_int(grant["max_physical_requests"], code)
        request_timeout = _require_positive_int(
            grant["request_timeout_seconds"],
            code,
        )
        interval = _require_positive_int(grant["min_request_interval_ms"], code)
        if (
            grant["connector_key"] != connector_key
            or requests != expected_requests
            or request_timeout > _MAX_PHASE_TIMEOUT_MILLISECONDS // 1000
        ):
            _fail(code)
        contribution = requests * (request_timeout * 1000 + counter_ack)
        contribution += (requests - 1) * interval
        derived += contribution
        if derived > _MAX_PHASE_TIMEOUT_MILLISECONDS:
            _fail(code)
    if phase_a_timeout != derived:
        _fail(code)


def _validated_phase_timeout_seconds(
    value: float | Mapping[str, float],
    code: str,
) -> Mapping[str, float]:
    if isinstance(value, Mapping):
        if set(value) != {"A", "B"}:
            _fail(code)
        supplied = value
    else:
        supplied = {"A": value, "B": value}
    result: dict[str, float] = {}
    for phase in ("A", "B"):
        timeout = supplied[phase]
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
            or timeout * 1000 > _MAX_PHASE_TIMEOUT_MILLISECONDS
        ):
            _fail(code)
        result[phase] = float(timeout)
    return MappingProxyType(result)


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
            "dependency_set_sha256",
            "mutex_identity_sha256",
        ):
            _require_sha256(payload[field], code)
        _validate_phase_timeout_contract(payload["phase_timeout_contract"], code)
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
    dependency_set_sha256: str
    root_mutex_identity_sha256: str
    campaign_mutex_identity_sha256: str

    def __post_init__(self) -> None:
        code = "dual_live_runtime_identity_invalid"
        _require_uuid4(self.runtime_instance_id, code)
        _require_sha256(self.wrapper_nonce_sha256, code)
        _require_code_revision(self.code_revision, code)
        _require_sha256(self.wrapper_image_sha256, code)
        _require_sha256(self.interpreter_image_sha256, code)
        _require_sha256(self.dependency_set_sha256, code)
        _require_sha256(self.root_mutex_identity_sha256, code)
        _require_sha256(self.campaign_mutex_identity_sha256, code)


def _combined_mutex_identity_sha256(identity: RuntimeIdentity) -> str:
    if type(identity) is not RuntimeIdentity:
        _fail("dual_live_runtime_identity_invalid")
    return hashlib.sha256(
        b"project6:dual-live:proof-locks:v1\0"
        + identity.root_mutex_identity_sha256.encode("ascii")
        + b"\0"
        + identity.campaign_mutex_identity_sha256.encode("ascii")
    ).hexdigest()


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
                "dependency_set_sha256",
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
        or type(value["ordinal"]) is not int
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


def decode_child_boot_frame(
    payload: bytes,
    *,
    expected_phase: str,
    expected_process_boot_id: str,
    expected_status_nonce_sha256: str,
    expected_control_nonce: str,
) -> dict[str, Any]:
    code = "dual_live_child_boot_invalid"
    try:
        value = strict_json_loads(payload)
    except (TypeError, ValueError):
        _fail(code)
    if (
        type(value) is not dict
        or canonical_json_bytes(value) != payload
        or tuple(value)
        != (
            "control_nonce",
            "phase",
            "process_boot_id",
            "schema_id",
            "status_nonce_sha256",
        )
        or value["schema_id"] != CHILD_BOOT_SCHEMA_ID
        or value["phase"] != expected_phase
        or value["process_boot_id"] != expected_process_boot_id
        or value["status_nonce_sha256"] != expected_status_nonce_sha256
        or value["control_nonce"] != expected_control_nonce
    ):
        _fail(code)
    return dict(value)


def _framed_payload_sha256(payload: bytes) -> str:
    if not isinstance(payload, bytes) or not payload:
        _fail("dual_live_frame_type_invalid")
    return hashlib.sha256(
        len(payload).to_bytes(4, "big", signed=False) + payload
    ).hexdigest()


def _proof_identifier(value: Any, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or any(character.isspace() for character in value)
    ):
        _fail(code)
    return value


def _proof_hash_fields(payload: Mapping[str, Any], names: Sequence[str]) -> None:
    for name in names:
        value = payload.get(name)
        if (
            type(value) is not str
            or _LOWERCASE_SHA256.fullmatch(value) is None
        ):
            _fail("dual_live_child_proof_invalid")


def _validate_child_proof_payload(
    *,
    phase: str,
    event: str,
    ordinal: int,
    payload: Any,
    expected_proof_scope: str,
) -> dict[str, Any]:
    code = "dual_live_child_proof_invalid"
    if type(payload) is not dict or expected_proof_scope not in {
        "mechanical",
        "production",
    }:
        _fail(code)
    value = dict(payload)
    if value.get("proof_scope") != expected_proof_scope:
        _fail(code)
    if phase == "B" and event == "guard":
        point = "pre_go" if ordinal == 1 else "exit" if ordinal == 3 else None
        keys = {
            "boot_frame_sha256",
            "control_nonce_sha256",
            "denied_routes",
            "network_enable_attempt_count",
            "original_implementation_call_count",
            "pre_activity_status_frame_sha256",
            "proof_point",
            "proof_scope",
        }
        hashes: tuple[str, ...] = (
            "boot_frame_sha256",
            "control_nonce_sha256",
            "pre_activity_status_frame_sha256",
        )
        if point == "exit":
            keys |= {"control_frame_sha256", "exit_status_frame_sha256"}
            hashes += ("control_frame_sha256", "exit_status_frame_sha256")
        if (
            set(value) != keys
            or value.get("proof_point") != point
            or tuple(value.get("denied_routes") or ())
            != _CHILD_PROOF_DENIED_ROUTES
            or type(value.get("network_enable_attempt_count")) is not int
            or value["network_enable_attempt_count"] != 0
            or type(value.get("original_implementation_call_count")) is not int
            or value["original_implementation_call_count"] != 0
        ):
            _fail(code)
        _proof_hash_fields(value, hashes)
        return value
    if phase == "A" and event == "acquisition_boundary" and ordinal == 1:
        if set(value) != {
            "boot_frame_sha256",
            "connector_acquisitions",
            "control_frame_sha256",
            "control_nonce_sha256",
            "downstream_action_count",
            "exit_status_frame_sha256",
            "pre_activity_status_frame_sha256",
            "proof_scope",
        }:
            _fail(code)
        _proof_hash_fields(
            value,
            (
                "boot_frame_sha256",
                "control_frame_sha256",
                "control_nonce_sha256",
                "exit_status_frame_sha256",
                "pre_activity_status_frame_sha256",
            ),
        )
        acquisitions = value.get("connector_acquisitions")
        if (
            not isinstance(acquisitions, list)
            or type(value.get("downstream_action_count")) is not int
            or value["downstream_action_count"] != 0
        ):
            _fail(code)
        if expected_proof_scope == "mechanical":
            if acquisitions:
                _fail(code)
            return value
        if tuple(item.get("connector_key") for item in acquisitions if isinstance(item, dict)) != (
            "nrc_adams_aps",
            "sciencebase_mcs",
        ):
            _fail(code)
        for item in acquisitions:
            if type(item) is not dict or set(item) != {
                "action_codes",
                "connector_key",
                "connector_run_id",
                "connector_run_target_id",
                "ledger_terminal_hash",
                "raw_content_sha256",
                "terminal_transition_count",
            }:
                _fail(code)
            if tuple(item["action_codes"]) != (
                "derived_arming",
                "raw_acquisition",
                "terminal_transition",
            ) or (
                type(item.get("terminal_transition_count")) is not int
                or item["terminal_transition_count"] != 1
            ):
                _fail(code)
            _proof_identifier(item["connector_run_id"], code)
            _proof_identifier(item["connector_run_target_id"], code)
            _proof_hash_fields(
                item,
                ("ledger_terminal_hash", "raw_content_sha256"),
            )
        return value
    if phase == "B" and event == "downstream_chain" and ordinal == 2:
        expected_keys = {
            "boot_frame_sha256",
            "control_frame_sha256",
            "control_nonce_sha256",
            "downstream_actions",
            "exit_status_frame_sha256",
            "pre_activity_status_frame_sha256",
            "proof_scope",
            "source_bindings",
            "terminal_boundary",
        }
        if expected_proof_scope == "production":
            expected_keys.add("action_receipts")
        if set(value) != expected_keys:
            _fail(code)
        _proof_hash_fields(
            value,
            (
                "boot_frame_sha256",
                "control_frame_sha256",
                "control_nonce_sha256",
                "exit_status_frame_sha256",
                "pre_activity_status_frame_sha256",
            ),
        )
        actions = value.get("downstream_actions")
        bindings = value.get("source_bindings")
        if not isinstance(actions, list) or not isinstance(bindings, list):
            _fail(code)
        if expected_proof_scope == "mechanical":
            if actions or bindings or value.get("terminal_boundary") != "mechanical_complete":
                _fail(code)
            return value
        action_receipts = value.get("action_receipts")
        if (
            tuple(actions) != _PHASE_B_DOWNSTREAM_ACTIONS
            or value.get("terminal_boundary") != "handoff_prepared"
            or not isinstance(action_receipts, list)
            or len(action_receipts) != len(_PHASE_B_DOWNSTREAM_ACTIONS)
        ):
            _fail(code)
        for expected_action, receipt in zip(
            _PHASE_B_DOWNSTREAM_ACTIONS,
            action_receipts,
            strict=True,
        ):
            if (
                type(receipt) is not dict
                or set(receipt) != {"action", "result_sha256"}
                or receipt.get("action") != expected_action
            ):
                _fail(code)
            _proof_hash_fields(receipt, ("result_sha256",))
        if tuple(item.get("connector_key") for item in bindings if isinstance(item, dict)) != (
            "nrc_adams_aps",
            "sciencebase_mcs",
        ):
            _fail(code)
        for item in bindings:
            if type(item) is not dict or set(item) != {
                "analysis_plan_id",
                "analysis_run_id",
                "candidate_id",
                "connector_key",
                "connector_origin_receipt_hash",
                "connector_run_id",
                "connector_run_target_id",
                "construction_basis_hash",
                "handoff_export_envelope_ref",
                "output_package_ids",
                "package_kinds",
                "package_review_preview_hash",
                "package_review_submit_record_ref",
                "pass_run_id",
                "payload_hashes",
                "prepare_record_ref",
                "reconciliation_record_id",
                "result_review_record_ref",
                "session_id",
                "source_shape",
                "source_record_id",
            }:
                _fail(code)
            for name in (
                "analysis_plan_id",
                "candidate_id",
                "connector_run_id",
                "connector_run_target_id",
                "handoff_export_envelope_ref",
                "package_review_preview_hash",
                "package_review_submit_record_ref",
                "pass_run_id",
                "prepare_record_ref",
                "reconciliation_record_id",
                "result_review_record_ref",
                "session_id",
                "source_record_id",
            ):
                _proof_identifier(item[name], code)
            if item.get("analysis_run_id") is not None:
                _proof_identifier(item["analysis_run_id"], code)
            if item.get("source_shape") != _PHASE_B_SOURCE_SHAPES.get(
                item["connector_key"]
            ):
                _fail(code)
            package_ids = item.get("output_package_ids")
            package_kinds = item.get("package_kinds")
            payload_hashes = item.get("payload_hashes")
            if (
                not isinstance(package_ids, list)
                or len(package_ids) != 3
                or len(set(package_ids)) != 3
                or not all(
                    isinstance(package_id, str) and package_id
                    for package_id in package_ids
                )
                or tuple(package_kinds or ()) != _PHASE_B_PACKAGE_KINDS
                or not isinstance(payload_hashes, list)
                or len(payload_hashes) != 3
            ):
                _fail(code)
            for package_id in package_ids:
                _proof_identifier(package_id, code)
            for payload_hash in payload_hashes:
                _proof_hash_fields({"payload_hash": payload_hash}, ("payload_hash",))
            _proof_hash_fields(
                item,
                (
                    "connector_origin_receipt_hash",
                    "construction_basis_hash",
                ),
            )
        return value
    _fail(code)


def encode_child_proof_frame(
    *,
    phase: str,
    event: str,
    process_boot_id: str,
    status_nonce_sha256: str,
    ordinal: int,
    previous_record_sha256: str | None,
    payload: Mapping[str, Any],
) -> bytes:
    expected_events = _CHILD_PROOF_EVENTS.get(phase)
    expected_scope = payload.get("proof_scope") if isinstance(payload, Mapping) else None
    if (
        expected_events is None
        or isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or not 1 <= ordinal <= len(expected_events)
        or event != expected_events[ordinal - 1]
        or _LOWERCASE_SHA256.fullmatch(process_boot_id) is None
        or _LOWERCASE_SHA256.fullmatch(status_nonce_sha256) is None
        or (ordinal == 1) != (previous_record_sha256 is None)
        or (
            previous_record_sha256 is not None
            and _LOWERCASE_SHA256.fullmatch(previous_record_sha256) is None
        )
        or expected_scope not in {"mechanical", "production"}
    ):
        _fail("dual_live_child_proof_invalid")
    normalized_payload = _validate_child_proof_payload(
        phase=phase,
        event=event,
        ordinal=ordinal,
        payload=dict(payload),
        expected_proof_scope=str(expected_scope),
    )
    record: dict[str, Any] = {
        "schema_id": CHILD_PROOF_SCHEMA_ID,
        "phase": phase,
        "event": event,
        "ordinal": ordinal,
        "process_boot_id": process_boot_id,
        "status_nonce_sha256": status_nonce_sha256,
        "previous_record_sha256": previous_record_sha256,
        "payload": normalized_payload,
    }
    record["record_sha256"] = _record_hash(record)
    return _encode_pipe_frame(
        canonical_json_bytes(record),
        allowed_reserved_schema_ids=frozenset((CHILD_PROOF_SCHEMA_ID,)),
    )


def decode_child_proof_frame(
    payload: bytes,
    *,
    expected_phase: str,
    expected_process_boot_id: str,
    expected_status_nonce_sha256: str,
    expected_ordinal: int,
    expected_previous_record_sha256: str | None,
    expected_proof_scope: str,
) -> dict[str, Any]:
    code = "dual_live_child_proof_invalid"
    try:
        value = strict_json_loads(payload)
    except (TypeError, ValueError):
        _fail(code)
    expected_events = _CHILD_PROOF_EVENTS.get(expected_phase)
    if (
        type(value) is not dict
        or canonical_json_bytes(value) != payload
        or tuple(value) != (
            "event",
            "ordinal",
            "payload",
            "phase",
            "previous_record_sha256",
            "process_boot_id",
            "record_sha256",
            "schema_id",
            "status_nonce_sha256",
        )
        or value["schema_id"] != CHILD_PROOF_SCHEMA_ID
        or expected_events is None
        or not 1 <= expected_ordinal <= len(expected_events)
        or value["event"] != expected_events[expected_ordinal - 1]
        or value["phase"] != expected_phase
        or value["process_boot_id"] != expected_process_boot_id
        or value["status_nonce_sha256"] != expected_status_nonce_sha256
        or type(value["ordinal"]) is not int
        or value["ordinal"] != expected_ordinal
        or value["previous_record_sha256"] != expected_previous_record_sha256
        or type(value["record_sha256"]) is not str
        or _LOWERCASE_SHA256.fullmatch(value["record_sha256"]) is None
        or _record_hash(value) != value["record_sha256"]
    ):
        _fail(code)
    value["payload"] = _validate_child_proof_payload(
        phase=expected_phase,
        event=str(value["event"]),
        ordinal=expected_ordinal,
        payload=value["payload"],
        expected_proof_scope=expected_proof_scope,
    )
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
        "_boot_callback",
        "_boot_seen",
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
        "_expected_control_nonce",
        "_expected_proof_scope",
        "_expected_status_nonce_sha256",
        "_expected_status_phase",
        "_expected_status_process_boot_id",
        "_http_frame_committed",
        "_http_frame_validator",
        "_join_active",
        "_lifecycle_lock",
        "_next_proof_ordinal",
        "_next_status_ordinal",
        "_previous_proof_record_sha256",
        "_proof_callback",
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
        boot_callback: Callable[[str], None],
        status_callback: Callable[[dict[str, Any], str], None],
        proof_callback: Callable[[dict[str, Any]], None],
        http_frame_validator: Callable[[bytes], None],
        stop_latch: FirstStopLatch,
        expected_status_phase: str,
        expected_status_process_boot_id: str,
        expected_status_nonce_sha256: str,
        expected_control_nonce: str,
        expected_proof_scope: str,
        budget: PipeFrameBudget | None = None,
        http_frame_committed: Callable[[], None] | None = None,
    ) -> None:
        if (
            set(readers) != set(PIPE_STREAM_CLASSES)
            or set(writers) != set(PIPE_STREAM_CLASSES)
            or not callable(boot_callback)
            or not callable(status_callback)
            or not callable(proof_callback)
            or not callable(http_frame_validator)
            or (
                http_frame_committed is not None
                and not callable(http_frame_committed)
            )
            or type(stop_latch) is not FirstStopLatch
            or expected_status_phase not in {"A", "B"}
            or not isinstance(expected_status_process_boot_id, str)
            or _LOWERCASE_SHA256.fullmatch(expected_status_process_boot_id) is None
            or not isinstance(expected_status_nonce_sha256, str)
            or _LOWERCASE_SHA256.fullmatch(expected_status_nonce_sha256) is None
            or not isinstance(expected_control_nonce, str)
            or _LOWERCASE_SHA256.fullmatch(expected_control_nonce) is None
            or expected_proof_scope not in {"mechanical", "production"}
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
        self._boot_callback = boot_callback
        self._status_callback = status_callback
        self._proof_callback = proof_callback
        self._http_frame_validator = http_frame_validator
        self._http_frame_committed = http_frame_committed
        self._stop_latch = stop_latch
        self._expected_status_phase = expected_status_phase
        self._expected_status_process_boot_id = expected_status_process_boot_id
        self._expected_status_nonce_sha256 = expected_status_nonce_sha256
        self._expected_control_nonce = expected_control_nonce
        self._expected_proof_scope = expected_proof_scope
        self._boot_seen = False
        self._next_status_ordinal = 1
        self._next_proof_ordinal = 1
        self._previous_proof_record_sha256: str | None = None
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
        post_write: Callable[[], None] | None = None
        if stream == "app":
            try:
                value = strict_json_loads(payload)
            except (TypeError, ValueError):
                _fail("dual_live_app_frame_invalid")
            if type(value) is not dict or canonical_json_bytes(value) != payload:
                _fail("dual_live_app_frame_invalid")
            schema_id = value.get("schema_id")
            if schema_id == CHILD_STATUS_SCHEMA_ID:
                status = decode_child_status_frame(
                    payload,
                    expected_phase=self._expected_status_phase,
                    expected_process_boot_id=self._expected_status_process_boot_id,
                    expected_status_nonce_sha256=(
                        self._expected_status_nonce_sha256
                    ),
                    expected_ordinal=self._next_status_ordinal,
                )
                self._budget.consume(stream, len(payload), emitted_bytes=0)
                try:
                    result = self._status_callback(
                        status,
                        _framed_payload_sha256(payload),
                    )
                except Exception as exc:
                    raise DualLiveRuntimeError(
                        "dual_live_child_status_callback_invalid"
                    ) from exc
                if result is not None:
                    _fail("dual_live_child_status_callback_invalid")
                self._next_status_ordinal += 1
                return
            if schema_id in {CHILD_CONTROL_SCHEMA_ID, CHILD_PROOF_SCHEMA_ID}:
                _fail("dual_live_app_frame_reserved_schema")
            output = payload + b"\n"
            if schema_id == CHILD_BOOT_SCHEMA_ID:
                if self._boot_seen:
                    _fail("dual_live_child_boot_invalid")
                decode_child_boot_frame(
                    payload,
                    expected_phase=self._expected_status_phase,
                    expected_process_boot_id=(
                        self._expected_status_process_boot_id
                    ),
                    expected_status_nonce_sha256=(
                        self._expected_status_nonce_sha256
                    ),
                    expected_control_nonce=self._expected_control_nonce,
                )
                boot_sha256 = _framed_payload_sha256(payload)

                def publish_boot() -> None:
                    result = self._boot_callback(boot_sha256)
                    if result is not None:
                        _fail("dual_live_child_boot_callback_invalid")
                    self._boot_seen = True

                post_write = publish_boot
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
        elif stream == "stdout":
            proof = decode_child_proof_frame(
                payload,
                expected_phase=self._expected_status_phase,
                expected_process_boot_id=self._expected_status_process_boot_id,
                expected_status_nonce_sha256=(
                    self._expected_status_nonce_sha256
                ),
                expected_ordinal=self._next_proof_ordinal,
                expected_previous_record_sha256=(
                    self._previous_proof_record_sha256
                ),
                expected_proof_scope=self._expected_proof_scope,
            )
            output = payload + b"\n"

            def publish_proof() -> None:
                result = self._proof_callback(proof)
                if result is not None:
                    _fail("dual_live_child_proof_callback_invalid")
                self._next_proof_ordinal += 1
                self._previous_proof_record_sha256 = proof["record_sha256"]

            post_write = publish_proof
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
            if post_write is not None:
                post_write()
            if stream == "http" and self._http_frame_committed is not None:
                result = self._http_frame_committed()
                if result is not None:
                    _fail("dual_live_http_frame_commit_invalid")
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
                elif stream == "stdout":
                    payload = _read_pipe_frame(
                        reader,
                        allowed_reserved_schema_ids=frozenset(
                            (CHILD_PROOF_SCHEMA_ID,)
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
                try:
                    self._stop_latch.latch("pump_failure")
                except DualLiveRuntimeError as stop_error:
                    if stop_error.code != "dual_live_stop_publish_failed":
                        raise
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
            launched = False
            try:
                thread.start()
            except BaseException as exc:
                launched = thread.ident is not None
                with self._errors_lock:
                    self._cancel_start_errors.setdefault(stream, exc)
            else:
                launched = True
            if launched:
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
                    try:
                        thread.start()
                    except BaseException:
                        if thread.ident is not None:
                            started_threads.append(thread)
                        raise
                    else:
                        started_threads.append(thread)
            finally:
                self._started_threads = tuple(started_threads)

    @staticmethod
    def _writer_error(
        errors: tuple[tuple[str, BaseException], ...],
    ) -> BaseException | None:
        writer_codes = {
            "dual_live_pump_write_failed",
            "dual_live_pump_writer_poisoned",
        }
        for _stream, error in errors:
            current: BaseException | None = error
            seen: set[int] = set()
            while current is not None and id(current) not in seen:
                seen.add(id(current))
                if (
                    isinstance(current, DualLiveRuntimeError)
                    and current.code in writer_codes
                ):
                    return error
                current = current.__cause__
        return None

    def _raise_join_failures(
        self,
        *,
        pump_errors: tuple[tuple[str, BaseException], ...],
        cancel_errors: tuple[tuple[str, BaseException], ...],
        cancel_start_errors: tuple[tuple[str, BaseException], ...],
        cancel_incomplete: bool,
    ) -> None:
        writer_error = self._writer_error(pump_errors)
        cancel_failed = bool(
            cancel_incomplete or cancel_errors or cancel_start_errors
        )
        if writer_error is not None:
            failure = DualLiveRuntimeError("dual_live_pump_failed")
            failure.__cause__ = writer_error
            if cancel_failed:
                secondary = DualLiveRuntimeError("dual_live_pump_cancel_failed")
                secondary.__cause__ = self._cancel_failure_cause(
                    cancel_errors,
                    cancel_start_errors,
                )
                failure.__context__ = secondary
            raise failure
        if cancel_failed:
            raise DualLiveRuntimeError("dual_live_pump_cancel_failed") from (
                self._cancel_failure_cause(
                    cancel_errors,
                    cancel_start_errors,
                )
            )
        if pump_errors:
            raise DualLiveRuntimeError("dual_live_pump_failed") from (
                pump_errors[0][1]
            )

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
                self._raise_join_failures(
                    pump_errors=pump_errors,
                    cancel_errors=cancel_errors,
                    cancel_start_errors=cancel_start_errors,
                    cancel_incomplete=cancel_alive,
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
            self._raise_join_failures(
                pump_errors=final_pump_errors,
                cancel_errors=cancel_errors,
                cancel_start_errors=cancel_start_errors,
                cancel_incomplete=still_alive or cancel_alive,
            )
            raise DualLiveRuntimeError("dual_live_pump_join_timeout")
        finally:
            with self._lifecycle_lock:
                self._join_active = False


def _noop_http_frame_ack() -> None:
    return None


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
    boot_frame_sha256: str | None = None
    ack_http_frame: Callable[[], None] = _noop_http_frame_ack

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
        if self.boot_frame_sha256 is not None:
            _require_sha256(self.boot_frame_sha256, code)
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
            for callback in (
                self.send_control,
                self.wait,
                self.stop,
                self.ack_http_frame,
            )
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
    timeout_seconds: float | Mapping[str, float],
    _before_stop_publish: Callable[[str], None] | None = None,
    _http_frame_committed: Callable[[_ControllerChild], None] | None = None,
    _proof_scope: Literal["mechanical", "production"] = "mechanical",
) -> Any:
    """Run the bounded mechanical A/B spine; no production semantics live here."""

    phase_timeouts = _validated_phase_timeout_seconds(
        timeout_seconds,
        "dual_live_controller_invalid",
    )
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
        or (
            _before_stop_publish is not None
            and not callable(_before_stop_publish)
        )
        or (
            _http_frame_committed is not None
            and not callable(_http_frame_committed)
        )
        or _proof_scope not in {"mechanical", "production"}
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
    if _before_stop_publish is not None:
        stop_latch._bind_before_publish(_before_stop_publish)
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
        try:
            stop_latch.latch(reason_code)
        except DualLiveRuntimeError as stop_error:
            if stop_error.code != "dual_live_stop_publish_failed":
                raise
            fatal = DualLiveRuntimeError("dual_live_stop_publish_failed")
            fatal.__cause__ = stop_error.__cause__ or stop_error
            fatal.__context__ = cause
            return fatal
        error = DualLiveRuntimeError(code)
        error.__cause__ = cause
        return error

    def close_readers(
        child: _ControllerChild,
        *,
        timeout_seconds: float,
        excluded_reader_ids: frozenset[int] = frozenset(),
    ) -> tuple[BaseException | None, bool]:
        seen: set[int] = set()
        readers: list[tuple[str, BinaryIO]] = []
        for stream in PIPE_STREAM_CLASSES:
            reader = child.readers[stream]
            if id(reader) in seen or id(reader) in excluded_reader_ids:
                continue
            seen.add(id(reader))
            readers.append((stream, reader))

        start_errors: list[BaseException | None] = [None] * len(readers)
        close_errors: list[BaseException | None] = [None] * len(readers)

        def close_reader(index: int, reader: BinaryIO) -> None:
            try:
                reader.close()
            except BaseException as exc:
                close_errors[index] = exc

        threads = [
            threading.Thread(
                target=close_reader,
                args=(index, reader),
                name=f"dual-live-{stream}-owner-close",
                daemon=True,
            )
            for index, (stream, reader) in enumerate(readers)
        ]
        started: list[threading.Thread] = []
        for index, thread in enumerate(threads):
            try:
                thread.start()
            except BaseException as exc:
                if thread.ident is not None:
                    started.append(thread)
                start_errors[index] = exc
            else:
                started.append(thread)
        deadline = time.monotonic() + min(
            timeout_seconds,
            PUMP_CANCEL_JOIN_SECONDS,
        )
        for thread in started:
            thread.join(max(0.0, deadline - time.monotonic()))
        alive = [thread for thread in started if thread.is_alive()]
        if alive:
            first_error: BaseException | None = DualLiveRuntimeError(
                "dual_live_reader_close_stuck"
            )
        else:
            first_error = next(
                (
                    start_error or close_error
                    for start_error, close_error in zip(
                        start_errors,
                        close_errors,
                        strict=True,
                    )
                    if start_error is not None or close_error is not None
                ),
                None,
            )
        safe = len(started) == len(threads) and not alive
        return first_error, safe

    def run_phase(
        phase: str,
        factory: Callable[[], _ControllerChild],
    ) -> str:
        nonlocal capture_close_safe
        phase_timeout_seconds = phase_timeouts[phase]
        child: _ControllerChild | None = None
        pumps: FourStreamPumpGroup | None = None
        control: PhaseControlState | None = None
        census_ready = threading.Event()
        preproof_ready = threading.Event()
        census_points: list[tuple[str, int, str]] = []
        proof_lock = threading.Lock()
        proof_records: list[dict[str, Any]] = []
        boot_frame_sha256: str | None = None
        status_frame_sha256: dict[str, str] = {}
        control_frame_sha256: str | None = None
        proof_validated = False
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
            elif (
                isinstance(phase_error, DualLiveRuntimeError)
                and phase_error.code == "dual_live_stop_publish_failed"
            ):
                return
            elif reason_code == "writer_failure":
                replacement.__context__ = phase_error
                phase_error = replacement

        def stop_child_once() -> None:
            nonlocal stop_called, stopped
            if child is None or stop_called:
                return
            stop_called = True
            try:
                result = cast(Callable[[], object], child.stop)()
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
            reader_error, reader_close_safe = close_readers(
                child,
                timeout_seconds=phase_timeout_seconds,
                excluded_reader_ids=cancellation_owned_reader_ids,
            )
            if not reader_close_safe:
                capture_close_safe = False
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
                poll_finished = time.monotonic()
                if poll_finished >= deadline:
                    if observe_stop:
                        stop_latch.latch("timeout")
                    _fail("dual_live_phase_exit_timeout")
                if result is None:
                    unused_poll = poll_seconds - (poll_finished - poll_started)
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
            boot_frame_sha256 = child.boot_frame_sha256
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

            def boot_callback(frame_sha256: str) -> None:
                nonlocal boot_frame_sha256
                with proof_lock:
                    if boot_frame_sha256 is not None:
                        _fail("dual_live_child_boot_invalid")
                    boot_frame_sha256 = frame_sha256

            def proof_callback(proof: dict[str, Any]) -> None:
                with proof_lock:
                    if len(proof_records) + 1 != proof["ordinal"]:
                        _fail("dual_live_child_proof_invalid")
                    proof_records.append(proof)
                    if phase == "B" and proof["ordinal"] == 1:
                        preproof_ready.set()

            def status_callback(
                status: dict[str, Any],
                frame_sha256: str,
            ) -> None:
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
                    with proof_lock:
                        if "pre_activity" in status_frame_sha256:
                            _fail("dual_live_child_status_invalid")
                        status_frame_sha256["pre_activity"] = frame_sha256
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
                with proof_lock:
                    if "exit" in status_frame_sha256:
                        _fail("dual_live_child_status_invalid")
                    status_frame_sha256["exit"] = frame_sha256
                if not matches:
                    _fail("dual_live_logger_topology_changed")

            def validate_proof_bindings(*, final: bool) -> None:
                with proof_lock:
                    records = tuple(proof_records)
                    boot_sha256 = boot_frame_sha256
                    statuses = dict(status_frame_sha256)
                required = len(_CHILD_PROOF_EVENTS[phase]) if final else 1
                if (
                    boot_sha256 is None
                    or "pre_activity" not in statuses
                    or len(records) != required
                ):
                    _fail("dual_live_child_proof_incomplete")
                if not final and phase != "B":
                    _fail("dual_live_child_proof_invalid")
                control_nonce_sha256 = hashlib.sha256(
                    child.control_nonce.encode("ascii")
                ).hexdigest()
                for proof in records:
                    proof_payload = proof["payload"]
                    if (
                        proof_payload["boot_frame_sha256"] != boot_sha256
                        or proof_payload["control_nonce_sha256"]
                        != control_nonce_sha256
                        or proof_payload["pre_activity_status_frame_sha256"]
                        != statuses["pre_activity"]
                    ):
                        _fail("dual_live_child_proof_binding_invalid")
                if not final:
                    return
                if "exit" not in statuses or control_frame_sha256 is None:
                    _fail("dual_live_child_proof_incomplete")
                terminal_proofs = records if phase == "A" else records[1:]
                for proof in terminal_proofs:
                    proof_payload = proof["payload"]
                    if (
                        proof_payload["control_frame_sha256"]
                        != control_frame_sha256
                        or proof_payload["exit_status_frame_sha256"]
                        != statuses["exit"]
                    ):
                        _fail("dual_live_child_proof_binding_invalid")

            def http_frame_committed() -> None:
                if _http_frame_committed is not None:
                    result = _http_frame_committed(child)
                    if result is not None:
                        _fail("dual_live_http_frame_commit_invalid")

            pumps = FourStreamPumpGroup(
                readers=child.readers,
                writers=cast(Mapping[str, BinaryIO], shared_sinks),
                boot_callback=boot_callback,
                status_callback=status_callback,
                proof_callback=proof_callback,
                http_frame_validator=http_frame_validator,
                stop_latch=stop_latch,
                expected_status_phase=phase,
                expected_status_process_boot_id=child.process_boot_id,
                expected_status_nonce_sha256=child.status_nonce_sha256,
                expected_control_nonce=child.control_nonce,
                expected_proof_scope=_proof_scope,
                budget=shared_budget,
                http_frame_committed=(
                    http_frame_committed
                    if _http_frame_committed is not None
                    else None
                ),
            )
            pumps.start()
            deadline = time.monotonic() + phase_timeout_seconds
            while not (
                census_ready.is_set()
                and (phase == "A" or preproof_ready.is_set())
            ):
                if stop_latch.is_set or time.monotonic() >= deadline:
                    _fail(
                        "dual_live_phase_census_failed"
                        if not census_ready.is_set()
                        else "dual_live_phase_proof_failed"
                    )
                stop_latch.wait(
                    min(0.05, max(0.0, deadline - time.monotonic()))
                )
            if stop_latch.is_set:
                _fail("dual_live_phase_census_failed")
            if phase == "B":
                validate_proof_bindings(final=False)
            control_frame = encode_child_control_frame(
                phase=phase,
                command="GO",
                control_nonce=child.control_nonce,
            )
            control_frame_sha256 = hashlib.sha256(control_frame).hexdigest()
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
                result = cast(Callable[[bytes], object], child.send_control)(
                    control_frame
                )
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
                phase_timeout_seconds,
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
                try:
                    release_safe = pumps.wait_for_writer_release(
                        timeout=min(
                            phase_timeout_seconds,
                            PUMP_CANCEL_JOIN_SECONDS,
                        )
                    )
                except BaseException as exc:
                    release_safe = not pumps.has_live_workers
                    if is_writer_failure(exc):
                        fail(
                            "dual_live_runtime_writer_failure",
                            "writer_failure",
                            exc,
                        )
                    else:
                        fail("dual_live_pump_failed", "pump_failure", exc)
                    record_stop_if_latched()
                if not release_safe:
                    capture_close_safe = False
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
                pumps.join(timeout=phase_timeout_seconds)
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
        if child is not None and control is not None and len(census_points) == 2:
            try:
                validate_proof_bindings(final=True)
                proof_validated = True
            except BaseException as exc:
                fail("dual_live_phase_proof_failed", "protocol_failure", exc)
        if (
            phase_error is None
            and control is not None
            and len(census_points) == 2
            and proof_validated
        ):
            try:
                control.complete()
            except BaseException as exc:
                fail("dual_live_phase_incomplete", "protocol_failure", exc)

        if phase_error is not None:
            record_stop_if_latched()

        if child is not None:
            authority_payload: dict[str, Any] | None = None
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
            if phase == "A" and quiescence_recorded:
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
        if child is not None and exit_code is not None and proof_validated:
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


_OWNED_CONTEXT_TOKEN = object()


class _OwnedProcessProjection(Protocol):
    boot_frame_sha256: str
    process_boot_id: str
    process_creation_identity_sha256: str
    executable_sha256: str
    job_policy_sha256: str
    status_nonce_sha256: str
    control_nonce: str
    readers: Mapping[str, BinaryIO]

    def send_control(self, frame: bytes) -> None: ...

    def ack_http_frame(self) -> None: ...

    def poll_exit(self, timeout: float) -> int | None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


class _OwnedMechanicalCapture:
    """Exact non-production capture owner used only by the offline binder proof."""

    __slots__ = (
        "_app_writer",
        "_http_writer",
        "_sealed",
        "_stderr_writer",
        "_stdout_writer",
    )

    def __init__(
        self,
        *,
        _token: object,
        app_writer: BinaryIO,
        http_writer: BinaryIO,
        stdout_writer: BinaryIO,
        stderr_writer: BinaryIO,
    ) -> None:
        if _token is not _OWNED_CONTEXT_TOKEN:
            raise TypeError("owned mechanical capture is factory-only")
        candidates = (app_writer, http_writer, stdout_writer, stderr_writer)
        if any(
            not callable(getattr(writer, method, None))
            for writer in candidates
            for method in ("write", "flush", "close")
        ):
            _fail("dual_live_owned_capture_invalid")
        destinations = tuple(
            _writer_destination_identity(writer) for writer in candidates
        )
        if len(set(destinations)) != len(PIPE_STREAM_CLASSES):
            _fail("dual_live_pump_writer_alias_invalid")
        self._app_writer = app_writer
        self._http_writer = http_writer
        self._stdout_writer = stdout_writer
        self._stderr_writer = stderr_writer
        self._sealed = False

    @property
    def sealed(self) -> bool:
        return self._sealed

    def _writer_bindings(self) -> dict[str, BinaryIO]:
        return {
            "app": self._app_writer,
            "http": self._http_writer,
            "stdout": self._stdout_writer,
            "stderr": self._stderr_writer,
        }

    def _seal(self) -> None:
        if self._sealed:
            _fail("dual_live_owned_capture_already_sealed")
        self._sealed = True


class _OwnedCampaignCapture:
    """Factory-only owner for one canonical server-bound campaign capture."""

    __slots__ = ("_capture", "_db", "_sealed")

    def __init__(
        self,
        *,
        _token: object,
        capture: object,
        db: object,
    ) -> None:
        if _token is not _OWNED_CONTEXT_TOKEN:
            raise TypeError("owned campaign capture is factory-only")
        from sqlalchemy.orm import Session

        from app.services import connector_campaign_log_capture

        if not isinstance(
            capture,
            connector_campaign_log_capture.ConnectorCampaignLogCaptureSession,
        ) or not isinstance(db, Session):
            _fail("dual_live_owned_capture_invalid")
        binding = connector_campaign_log_capture._require_capture_binding(
            capture
        )
        if (
            capture.writers != binding.writers
            or tuple(writer.stream_class for writer in capture.writers)
            != PIPE_STREAM_CLASSES
        ):
            _fail("dual_live_owned_capture_invalid")
        self._capture = capture
        self._db = db
        self._sealed = False

    @property
    def sealed(self) -> bool:
        return self._sealed

    def _writer_bindings(self) -> dict[str, BinaryIO]:
        from app.services import connector_campaign_log_capture

        binding = connector_campaign_log_capture._require_capture_binding(
            self._capture
        )
        if self._capture.writers != binding.writers:
            _fail("dual_live_owned_capture_invalid")
        return {
            writer.stream_class: cast(BinaryIO, writer)
            for writer in binding.writers
        }

    def _seal(self) -> Any:
        if self._sealed:
            _fail("dual_live_owned_capture_already_sealed")
        from app.services import connector_campaign_log_capture

        stopped_at = datetime.now(UTC)
        result = (
            connector_campaign_log_capture.seal_connector_campaign_log_capture(
                self._db,
                capture=self._capture,
                runtime_stopped_at=stopped_at,
                now=stopped_at,
            )
        )
        self._sealed = True
        return result

    def _abort_close(self) -> BaseException | None:
        first_error: BaseException | None = None
        for writer in self._capture.writers:
            try:
                writer.close()
            except BaseException as exc:
                if first_error is None:
                    first_error = exc
        return first_error


class _OwnedCampaignAuthority(Protocol):
    @property
    def evidence_root(self) -> Any: ...

    @property
    def campaign_id(self) -> str: ...

    @property
    def campaign_fingerprint(self) -> str: ...

    @property
    def campaign_definition_sha256(self) -> str: ...


class _ReviewedSourceProjection(Protocol):
    code_revision: str
    wrapper_image_sha256: str
    interpreter_image_sha256: str

    def assert_stable(self) -> None: ...

    def close(self) -> object: ...


def _authority_posture_projection(
    *,
    parent_remaining_count: int,
    retained_phase_a_environment_count: int,
    child_revoked: bool,
    child_stopped: bool,
) -> dict[str, Any]:
    if (
        not isinstance(parent_remaining_count, int)
        or isinstance(parent_remaining_count, bool)
        or parent_remaining_count < 0
        or not isinstance(retained_phase_a_environment_count, int)
        or isinstance(retained_phase_a_environment_count, bool)
        or retained_phase_a_environment_count < 0
        or type(child_revoked) is not bool
        or type(child_stopped) is not bool
    ):
        _fail("dual_live_owned_authority_invalid")
    return {
        "required_environment_names": list(
            PHASE_A_AUTHORITY_ENVIRONMENT_NAMES
        ),
        "parent_remaining_count": parent_remaining_count,
        "retained_phase_a_environment_count": (
            retained_phase_a_environment_count
        ),
        "child_revoked": child_revoked,
        "child_stopped": child_stopped,
    }


AUTHORITY_CLEARED_POSTURE_SHA256 = hashlib.sha256(
    canonical_json_bytes(
        _authority_posture_projection(
            parent_remaining_count=0,
            retained_phase_a_environment_count=0,
            child_revoked=True,
            child_stopped=True,
        )
    )
).hexdigest()


def _parent_authority_environment_aliases() -> tuple[str, ...]:
    return tuple(
        sorted(
            (
                name
                for name in os.environ
                if name.upper() in _PHASE_A_AUTHORITY_ENVIRONMENT
            ),
            key=lambda name: (name.upper(), name),
        )
    )


def _clear_parent_authority_environment() -> list[BaseException]:
    failures: list[BaseException] = []
    try:
        aliases = _parent_authority_environment_aliases()
    except BaseException as exc:
        return [exc]
    for alias in aliases:
        try:
            del os.environ[alias]
        except KeyError:
            continue
        except BaseException as exc:
            failures.append(exc)
    return failures


def _authority_setting_absent(value: object, cleared_value: object) -> bool:
    if cleared_value is None:
        return value is None
    if cleared_value is False:
        return value is False
    return type(value) is str and value == ""


def _clear_parent_settings_authority(
    *,
    producer_environment_owned: bool,
) -> tuple[list[BaseException], int]:
    if not producer_environment_owned:
        return [], 0
    try:
        from app.core import config

        settings = config.settings
    except BaseException as exc:
        return [exc], 1
    failures: list[BaseException] = []
    for attribute, cleared_value in _PHASE_A_SETTINGS_AUTHORITY_COORDINATES:
        try:
            setattr(settings, attribute, cleared_value)
        except BaseException as exc:
            failures.append(exc)
    remaining = 0
    for attribute, cleared_value in _PHASE_A_SETTINGS_AUTHORITY_COORDINATES:
        try:
            value = getattr(settings, attribute)
        except BaseException as exc:
            failures.append(exc)
            remaining += 1
            continue
        if not _authority_setting_absent(value, cleared_value):
            remaining += 1
    return failures, remaining


class _OwnedControllerContext:
    """Shared factory-only state for exact mechanical or campaign ownership."""

    __slots__ = (
        "_active_process",
        "_capture",
        "_closed_process_ids",
        "_identity",
        "_lock",
        "_owned_processes",
        "_quiescing_process",
        "_quiesced_process_ids",
        "_runtime_start_payload",
        "_started",
        "_timeout_seconds",
    )

    def __init__(
        self,
        *,
        _token: object,
        identity: RuntimeIdentity,
        runtime_start_payload: Mapping[str, Any],
        capture: _OwnedMechanicalCapture | _OwnedCampaignCapture,
        timeout_seconds: float | Mapping[str, float],
    ) -> None:
        phase_timeouts = _validated_phase_timeout_seconds(
            timeout_seconds,
            "dual_live_owned_context_invalid",
        )
        if _token is not _OWNED_CONTEXT_TOKEN:
            raise TypeError("owned controller context is factory-only")
        if (
            type(identity) is not RuntimeIdentity
            or type(capture)
            not in {_OwnedMechanicalCapture, _OwnedCampaignCapture}
        ):
            _fail("dual_live_owned_context_invalid")
        payload = _validate_payload("runtime_start", runtime_start_payload)
        if any(
            payload[field] != getattr(identity, field)
            for field in (
                "code_revision",
                "wrapper_image_sha256",
                "interpreter_image_sha256",
                "dependency_set_sha256",
            )
        ):
            _fail("dual_live_runtime_identity_mismatch")
        self._identity = identity
        self._runtime_start_payload = payload
        self._capture = capture
        self._timeout_seconds = phase_timeouts
        self._lock = threading.Lock()
        self._owned_processes: list[tuple[str, object]] = []
        self._active_process: object | None = None
        self._quiescing_process: object | None = None
        self._quiesced_process_ids: set[int] = set()
        self._closed_process_ids: set[int] = set()
        self._started = False

    @property
    def nonproduction_mechanical_only(self) -> bool:
        return True

    def _phase_environment(self, phase: str) -> Mapping[str, str] | None:
        if phase not in {"A", "B"}:
            _fail("dual_live_owned_process_invalid")
        return None

    @property
    def sealed(self) -> bool:
        return self._capture.sealed

    def _assert_authority_active(self) -> None:
        return None

    def _prepare_to_seal(self) -> None:
        return None

    def _after_seal(self) -> None:
        return None

    def _discard_phase_a_authority(self) -> BaseException | None:
        return None

    def _begin_run(self) -> None:
        self._assert_authority_active()
        with self._lock:
            if self._started or self._capture.sealed:
                _fail("dual_live_owned_context_already_used")
            self._started = True

    def _bind_process(self, phase: str, process: object) -> None:
        if phase not in {"A", "B"}:
            _fail("dual_live_owned_process_invalid")
        with self._lock:
            if not self._started or self._capture.sealed:
                _fail("dual_live_owned_context_invalid")
            if self._active_process is not None:
                overlap = True
                self._owned_processes.append((phase, process))
            else:
                overlap = False
                self._owned_processes.append((phase, process))
                self._active_process = process
        if overlap:
            close = getattr(process, "close", None)
            if not callable(close):
                _fail("dual_live_owned_process_invalid")
            try:
                if close() is not None:
                    _fail("dual_live_owned_close_invalid")
            except BaseException as exc:
                raise DualLiveRuntimeError(
                    "dual_live_owned_close_failed"
                ) from exc
            with self._lock:
                for index in range(len(self._owned_processes) - 1, -1, -1):
                    owned_phase, owned_process = self._owned_processes[index]
                    if owned_phase == phase and owned_process is process:
                        del self._owned_processes[index]
                        break
            _fail("dual_live_owned_process_overlap")
        self._assert_authority_active()

    def _find_process_locked(
        self,
        phase: str,
        child: _ControllerChild,
    ) -> object:
        matches = [
            process
            for owned_phase, process in self._owned_processes
            if owned_phase == phase
            and getattr(process, "process_boot_id", None)
            == child.process_boot_id
        ]
        if len(matches) != 1:
            _fail("dual_live_owned_process_invalid")
        return matches[0]

    def _revoke_active(self, reason: str) -> None:
        with self._lock:
            process = self._active_process
            if process is None:
                return
            revoke = getattr(process, "revoke_before_stop", None)
            if not callable(revoke):
                _fail("dual_live_owned_process_invalid")
            if revoke(reason) is not None:
                _fail("dual_live_owned_revocation_invalid")

    def _authority_payload(
        self,
        phase: str,
        child: _ControllerChild,
    ) -> Mapping[str, Any]:
        if phase != "A":
            _fail("dual_live_owned_authority_invalid")
        with self._lock:
            process = self._find_process_locked(phase, child)
            authority = getattr(process, "authority_cleared_payload", None)
            if not callable(authority):
                _fail("dual_live_owned_process_invalid")
            result = authority()
            if not isinstance(result, Mapping):
                _fail("dual_live_owned_authority_invalid")
            return result

    def _quiesce_phase(
        self,
        phase: str,
        child: _ControllerChild,
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        with self._lock:
            process = self._find_process_locked(phase, child)
            if (
                self._active_process is not process
                or self._quiescing_process is not None
                or id(process) in self._quiesced_process_ids
                or id(process) in self._closed_process_ids
            ):
                _fail("dual_live_owned_quiescence_unproven")
            self._quiescing_process = process
        try:
            quiesce = getattr(process, "quiesce_and_close", None)
            if not callable(quiesce):
                _fail("dual_live_owned_process_invalid")
            result = quiesce()
            if (
                type(result) is not tuple
                or len(result) != 2
                or not all(isinstance(item, Mapping) for item in result)
            ):
                _fail("dual_live_quiescence_invalid")
            close = getattr(process, "close", None)
            if not callable(close):
                _fail("dual_live_owned_process_invalid")
            if close() is not None:
                _fail("dual_live_owned_close_invalid")
        except BaseException:
            with self._lock:
                if self._quiescing_process is process:
                    self._quiescing_process = None
            raise
        with self._lock:
            identity_matches = sum(
                owned_phase == phase and owned_process is process
                for owned_phase, owned_process in self._owned_processes
            )
            if (
                self._quiescing_process is not process
                or self._active_process is not process
                or identity_matches != 1
                or id(process) in self._quiesced_process_ids
                or id(process) in self._closed_process_ids
            ):
                if self._quiescing_process is process:
                    self._quiescing_process = None
                _fail("dual_live_owned_quiescence_unproven")
            self._quiescing_process = None
            self._closed_process_ids.add(id(process))
            self._quiesced_process_ids.add(id(process))
            if self._active_process is process:
                self._active_process = None
            return result

    def _seal_after_quiescence(self) -> Any:
        self._assert_authority_active()
        with self._lock:
            if (
                not self._started
                or self._active_process is not None
                or self._quiescing_process is not None
                or len(self._owned_processes) != 2
                or {phase for phase, _process in self._owned_processes}
                != {"A", "B"}
                or self._quiesced_process_ids
                != {id(process) for _phase, process in self._owned_processes}
                or self._closed_process_ids != self._quiesced_process_ids
            ):
                _fail("dual_live_owned_quiescence_unproven")
            self._prepare_to_seal()
            result = self._capture._seal()
            self._after_seal()
            return result

    def _close_all_processes(self) -> BaseException | None:
        first_error: BaseException | None = None
        with self._lock:
            processes = tuple(self._owned_processes)
            already_closed_ids = frozenset(self._closed_process_ids)
        closed_processes = [
            process
            for _phase, process in processes
            if id(process) in already_closed_ids
        ]
        for _phase, process in reversed(processes):
            if id(process) in already_closed_ids:
                continue
            close = getattr(process, "close", None)
            if not callable(close):
                if first_error is None:
                    first_error = DualLiveRuntimeError(
                        "dual_live_owned_process_invalid"
                    )
                continue
            try:
                result = close()
                if result is not None:
                    _fail("dual_live_owned_close_invalid")
            except BaseException as exc:
                if first_error is None:
                    first_error = exc
            else:
                closed_processes.append(process)
        with self._lock:
            for process in closed_processes:
                if any(
                    candidate is process
                    for _phase, candidate in self._owned_processes
                ):
                    self._closed_process_ids.add(id(process))
            self._owned_processes[:] = [
                (phase, process)
                for phase, process in self._owned_processes
                if not any(process is closed for closed in closed_processes)
            ]
            if any(
                self._active_process is closed for closed in closed_processes
            ):
                self._active_process = None
        return first_error


class _ProductionOwnedControllerContext(_OwnedControllerContext):
    """Exact canonical capture and lock binding for the future closed runner."""

    _phase_environments: dict[str, Mapping[str, str] | None] | None

    __slots__ = (
        "_authority",
        "_phase_environments",
        "_proof_locks",
        "_retired_quiesced_phases",
        "_source_custody",
        "_source_custody_closed",
    )

    def __init__(
        self,
        *,
        _token: object,
        identity: RuntimeIdentity,
        runtime_start_payload: Mapping[str, Any],
        capture: _OwnedCampaignCapture,
        timeout_seconds: float | Mapping[str, float],
        authority: _OwnedCampaignAuthority,
        phase_environments: Mapping[str, Mapping[str, str]] | None,
        proof_locks: object,
        source_custody: _ReviewedSourceProjection,
    ) -> None:
        if _token is not _OWNED_CONTEXT_TOKEN:
            raise TypeError(
                "production owned controller context is factory-only"
            )
        if type(capture) is not _OwnedCampaignCapture:
            _fail("dual_live_owned_context_invalid")
        if phase_environments is not None and (
            not isinstance(phase_environments, Mapping)
            or set(phase_environments) != {"A", "B"}
            or any(
                not isinstance(environment, Mapping)
                or any(
                    not isinstance(name, str)
                    or not name
                    or not isinstance(value, str)
                    for name, value in environment.items()
                )
                for environment in phase_environments.values()
            )
        ):
            _fail("dual_live_owned_context_invalid")
        self._authority = authority
        self._phase_environments = (
            None
            if phase_environments is None
            else {
                phase: MappingProxyType(dict(environment))
                for phase, environment in phase_environments.items()
            }
        )
        self._proof_locks = proof_locks
        self._retired_quiesced_phases: set[str] = set()
        self._source_custody = source_custody
        self._source_custody_closed = False
        super().__init__(
            _token=_token,
            identity=identity,
            runtime_start_payload=runtime_start_payload,
            capture=capture,
            timeout_seconds=timeout_seconds,
        )

    @property
    def nonproduction_mechanical_only(self) -> bool:
        return False

    def _phase_environment(self, phase: str) -> Mapping[str, str] | None:
        if phase not in {"A", "B"}:
            _fail("dual_live_owned_process_invalid")
        if self._phase_environments is None:
            return None
        environment = self._phase_environments[phase]
        if environment is None:
            _fail("dual_live_owned_authority_invalid")
        return environment

    def _assert_authority_active(self) -> None:
        from app.services import dual_live_windows

        authority = self._authority
        try:
            self._source_custody.assert_stable()
            dual_live_windows._require_active_proof_locks(
                self._proof_locks,
                evidence_root=authority.evidence_root,
                campaign_id=authority.campaign_id,
                campaign_fingerprint=authority.campaign_fingerprint,
                campaign_definition_sha256=(
                    authority.campaign_definition_sha256
                ),
                root_mutex_identity_sha256=(
                    self._identity.root_mutex_identity_sha256
                ),
                campaign_mutex_identity_sha256=(
                    self._identity.campaign_mutex_identity_sha256
                ),
            )
        except AttributeError as exc:
            raise DualLiveRuntimeError(
                "dual_live_owned_authority_invalid"
            ) from exc

    def _close_source_custody(self) -> BaseException | None:
        if self._source_custody_closed:
            return None
        self._source_custody_closed = True
        try:
            if self._source_custody.close() is not None:
                _fail("dual_live_source_identity_cleanup_failed")
        except BaseException as exc:
            return exc
        return None

    @staticmethod
    def _process_authority_posture(
        process: object,
    ) -> tuple[int, bool, bool]:
        posture_reader = getattr(process, "authority_coordinate_posture", None)
        if not callable(posture_reader):
            _fail("dual_live_owned_process_invalid")
        posture = posture_reader()
        if not isinstance(posture, Mapping) or set(posture) != {
            "retained_environment_names",
            "revoked",
            "stopped",
        }:
            _fail("dual_live_owned_authority_invalid")
        retained_names = posture["retained_environment_names"]
        if (
            type(retained_names) is not tuple
            or len(retained_names) != len(set(retained_names))
            or tuple(sorted(retained_names)) != retained_names
            or any(
                type(name) is not str
                or name not in _PHASE_A_AUTHORITY_ENVIRONMENT
                for name in retained_names
            )
            or type(posture["revoked"]) is not bool
            or type(posture["stopped"]) is not bool
        ):
            _fail("dual_live_owned_authority_invalid")
        return (
            len(retained_names),
            posture["revoked"],
            posture["stopped"],
        )

    def _authority_payload(
        self,
        phase: str,
        child: _ControllerChild,
    ) -> Mapping[str, Any]:
        if phase != "A":
            _fail("dual_live_owned_authority_invalid")
        with self._lock:
            process = self._find_process_locked(phase, child)
            if (
                self._active_process is not None
                or self._quiescing_process is not None
                or id(process) not in self._quiesced_process_ids
                or id(process) not in self._closed_process_ids
            ):
                _fail("dual_live_owned_quiescence_unproven")
            producer_environment_owned = self._phase_environments is not None

        failures = _clear_parent_authority_environment()
        settings_failures, settings_remaining = (
            _clear_parent_settings_authority(
                producer_environment_owned=producer_environment_owned,
            )
        )
        failures.extend(settings_failures)
        with self._lock:
            if self._phase_environments is not None:
                self._phase_environments["A"] = None
            context_remaining = (
                0
                if self._phase_environments is None
                or self._phase_environments["A"] is None
                else sum(
                    name in _PHASE_A_AUTHORITY_ENVIRONMENT
                    for name in self._phase_environments["A"]
                )
            )

        clear_process = getattr(process, "clear_authority_coordinates", None)
        if not callable(clear_process):
            failures.append(
                DualLiveRuntimeError("dual_live_owned_process_invalid")
            )
        else:
            try:
                if clear_process() is not None:
                    _fail("dual_live_owned_authority_invalid")
            except BaseException as exc:
                failures.append(exc)
        try:
            process_remaining, child_revoked, child_stopped = (
                self._process_authority_posture(process)
            )
        except BaseException as exc:
            failures.append(exc)
            process_remaining = 1
            child_revoked = False
            child_stopped = False
        try:
            parent_remaining = len(_parent_authority_environment_aliases())
        except BaseException as exc:
            failures.append(exc)
            parent_remaining = 1
        retained_remaining = (
            settings_remaining + context_remaining + process_remaining
        )
        posture = _authority_posture_projection(
            parent_remaining_count=parent_remaining,
            retained_phase_a_environment_count=retained_remaining,
            child_revoked=child_revoked,
            child_stopped=child_stopped,
        )
        all_required_absent = (
            parent_remaining == 0
            and retained_remaining == 0
            and child_revoked
            and child_stopped
        )

        with self._lock:
            matches = [
                index
                for index, (owned_phase, owned_process) in enumerate(
                    self._owned_processes
                )
                if owned_phase == "A" and owned_process is process
            ]
            if len(matches) != 1:
                failures.append(
                    DualLiveRuntimeError("dual_live_owned_process_invalid")
                )
            else:
                del self._owned_processes[matches[0]]
            self._quiesced_process_ids.discard(id(process))
            self._closed_process_ids.discard(id(process))
            self._retired_quiesced_phases.add("A")

        if failures:
            for current, following in zip(failures, failures[1:]):
                current.__context__ = following
            raise DualLiveRuntimeError(
                "dual_live_owned_authority_invalid"
            ) from failures[0]
        return MappingProxyType(
            {
                "authority_posture_sha256": hashlib.sha256(
                    canonical_json_bytes(posture)
                ).hexdigest(),
                "all_required_absent": all_required_absent,
            }
        )

    def _discard_phase_a_authority(self) -> BaseException | None:
        failures = _clear_parent_authority_environment()
        with self._lock:
            producer_environment_owned = self._phase_environments is not None
            if self._phase_environments is not None:
                self._phase_environments["A"] = None
            phase_a_processes = tuple(
                process
                for phase, process in self._owned_processes
                if phase == "A"
            )
        settings_failures, _remaining = _clear_parent_settings_authority(
            producer_environment_owned=producer_environment_owned,
        )
        failures.extend(settings_failures)
        for process in phase_a_processes:
            discard = getattr(process, "discard_authority_coordinates", None)
            if not callable(discard):
                failures.append(
                    DualLiveRuntimeError("dual_live_owned_process_invalid")
                )
                continue
            try:
                if discard() is not None:
                    _fail("dual_live_owned_authority_invalid")
            except BaseException as exc:
                failures.append(exc)
        if not failures:
            return None
        for current, following in zip(failures, failures[1:]):
            current.__context__ = following
        return failures[0]

    def _seal_after_quiescence(self) -> Any:
        self._assert_authority_active()
        with self._lock:
            if (
                not self._started
                or self._active_process is not None
                or self._quiescing_process is not None
                or self._retired_quiesced_phases != {"A"}
                or len(self._owned_processes) != 1
                or self._owned_processes[0][0] != "B"
                or self._quiesced_process_ids
                != {id(self._owned_processes[0][1])}
                or self._closed_process_ids != self._quiesced_process_ids
            ):
                _fail("dual_live_owned_quiescence_unproven")
            self._prepare_to_seal()
            result = self._capture._seal()
            self._after_seal()
            return result

    def _prepare_to_seal(self) -> None:
        self._assert_authority_active()

    def _after_seal(self) -> None:
        self._assert_authority_active()
        close_error = self._close_source_custody()
        if close_error is not None:
            raise DualLiveRuntimeError(
                "dual_live_source_identity_cleanup_failed"
            ) from close_error


def _close_incomplete_campaign_capture(
    capture: Any,
) -> BaseException | None:
    first_error: BaseException | None = None
    try:
        writers = capture.writers
    except BaseException as exc:
        return exc
    for writer in writers:
        try:
            writer.close()
        except BaseException as exc:
            if first_error is None:
                first_error = exc
    return first_error


def _make_production_owned_controller_context(
    *,
    campaign_id: str,
    expected_campaign_fingerprint: str,
    db: object,
    identity: RuntimeIdentity,
    runtime_start_payload: Mapping[str, Any],
    timeout_seconds: float | Mapping[str, float],
    proof_locks: object,
) -> _ProductionOwnedControllerContext:
    """Begin and bind the canonical capture after every no-effect check passes."""

    phase_timeouts = _validated_phase_timeout_seconds(
        timeout_seconds,
        "dual_live_owned_context_invalid",
    )
    phase_timeout_mapping_supplied = isinstance(timeout_seconds, Mapping)
    from sqlalchemy.orm import Session

    from app.services import connector_campaign_log_capture, dual_live_windows

    canonical_campaign_id = _require_uuid4(
        campaign_id,
        "dual_live_campaign_id_invalid",
    )
    canonical_fingerprint = _require_sha256(
        expected_campaign_fingerprint,
        "dual_live_campaign_fingerprint_invalid",
    )
    if (
        type(identity) is not RuntimeIdentity
        or not isinstance(db, Session)
        or not isinstance(runtime_start_payload, Mapping)
    ):
        _fail("dual_live_owned_context_invalid")
    producer_environment_names: dict[str, int] = {}
    for name in os.environ:
        canonical = name.upper()
        if canonical in _PRODUCER_REQUIRED_ENVIRONMENT:
            producer_environment_names[canonical] = (
                producer_environment_names.get(canonical, 0) + 1
            )
    phase_environments: Mapping[str, Mapping[str, str]] | None = None
    if producer_environment_names:
        if set(producer_environment_names) != _PRODUCER_REQUIRED_ENVIRONMENT or any(
            count != 1 for count in producer_environment_names.values()
        ):
            _fail("dual_live_producer_configuration_missing")
        producer_settings = _load_producer_settings()
        phase_a_environment, phase_b_environment = _producer_phase_environments(
            producer_settings,
            campaign_id=canonical_campaign_id,
            campaign_fingerprint=canonical_fingerprint,
            code_revision=identity.code_revision,
            dependency_set_sha256=identity.dependency_set_sha256,
        )
        phase_environments = MappingProxyType(
            {
                "A": phase_a_environment,
                "B": phase_b_environment,
            }
        )
    payload = _validate_payload("runtime_start", runtime_start_payload)
    timeout_contract = payload["phase_timeout_contract"]
    if phase_timeout_mapping_supplied and any(
        phase_timeouts[phase]
        != timeout_contract[f"phase_{phase.lower()}_timeout_ms"] / 1000
        for phase in ("A", "B")
    ):
        _fail("dual_live_phase_timeout_contract_invalid")
    if any(
        payload[field] != getattr(identity, field)
        for field in (
            "code_revision",
            "wrapper_image_sha256",
            "interpreter_image_sha256",
            "dependency_set_sha256",
        )
    ):
        _fail("dual_live_runtime_identity_mismatch")
    if payload["mutex_identity_sha256"] != _combined_mutex_identity_sha256(
        identity
    ):
        _fail("dual_live_runtime_identity_mismatch")
    connector_campaign_log_capture._require_clean_session(db)

    started_at = datetime.now(UTC)
    campaign_uuid = UUID(canonical_campaign_id)
    authority = connector_campaign_log_capture._current_authority(
        campaign_id=campaign_uuid,
        expected_campaign_fingerprint=canonical_fingerprint,
        expected_code_revision=identity.code_revision,
        started_at=started_at,
    )
    dual_live_windows._require_active_proof_locks(
        proof_locks,
        evidence_root=authority.evidence_root,
        campaign_id=authority.campaign_id,
        campaign_fingerprint=authority.campaign_fingerprint,
        campaign_definition_sha256=authority.campaign_definition_sha256,
        root_mutex_identity_sha256=identity.root_mutex_identity_sha256,
        campaign_mutex_identity_sha256=identity.campaign_mutex_identity_sha256,
    )

    source_custody = dual_live_windows._acquire_reviewed_source_custody()
    capture: object | None = None
    try:
        source_custody.assert_stable()
        if any(
            getattr(source_custody, field) != getattr(identity, field)
            for field in (
                "code_revision",
                "wrapper_image_sha256",
                "interpreter_image_sha256",
            )
        ):
            _fail("dual_live_runtime_identity_mismatch")
        payload = {
            "code_revision": source_custody.code_revision,
            "wrapper_image_sha256": source_custody.wrapper_image_sha256,
            "interpreter_image_sha256": source_custody.interpreter_image_sha256,
            "dependency_set_sha256": identity.dependency_set_sha256,
            "phase_timeout_contract": timeout_contract,
            "mutex_identity_sha256": payload["mutex_identity_sha256"],
        }
        derived_authority = connector_campaign_log_capture._current_authority(
            campaign_id=campaign_uuid,
            expected_campaign_fingerprint=canonical_fingerprint,
            expected_code_revision=source_custody.code_revision,
            started_at=started_at,
        )
        if derived_authority != authority:
            _fail("dual_live_owned_authority_changed")
        dual_live_windows._require_active_proof_locks(
            proof_locks,
            evidence_root=authority.evidence_root,
            campaign_id=authority.campaign_id,
            campaign_fingerprint=authority.campaign_fingerprint,
            campaign_definition_sha256=(
                authority.campaign_definition_sha256
            ),
            root_mutex_identity_sha256=(
                identity.root_mutex_identity_sha256
            ),
            campaign_mutex_identity_sha256=(
                identity.campaign_mutex_identity_sha256
            ),
        )
        capture = connector_campaign_log_capture.begin_connector_campaign_log_capture(
            campaign_id=campaign_uuid,
            expected_campaign_fingerprint=canonical_fingerprint,
            expected_code_revision=source_custody.code_revision,
            now=started_at,
        )
        binding = connector_campaign_log_capture._require_capture_binding(
            capture
        )
        if binding.authority != authority:
            _fail("dual_live_owned_authority_changed")
        dual_live_windows._require_active_proof_locks(
            proof_locks,
            evidence_root=binding.authority.evidence_root,
            campaign_id=binding.authority.campaign_id,
            campaign_fingerprint=binding.authority.campaign_fingerprint,
            campaign_definition_sha256=(
                binding.authority.campaign_definition_sha256
            ),
            root_mutex_identity_sha256=identity.root_mutex_identity_sha256,
            campaign_mutex_identity_sha256=(
                identity.campaign_mutex_identity_sha256
            ),
        )
        owned_capture = _OwnedCampaignCapture(
            _token=_OWNED_CONTEXT_TOKEN,
            capture=capture,
            db=db,
        )
        return _ProductionOwnedControllerContext(
            _token=_OWNED_CONTEXT_TOKEN,
            identity=identity,
            runtime_start_payload=payload,
            capture=owned_capture,
            timeout_seconds=phase_timeouts,
            authority=authority,
            phase_environments=phase_environments,
            proof_locks=proof_locks,
            source_custody=source_custody,
        )
    except BaseException as exc:
        capture_close_error: BaseException | None = None
        if capture is not None:
            capture_close_error = _close_incomplete_campaign_capture(capture)
        source_close_error: BaseException | None = None
        try:
            source_custody.close()
        except BaseException as close_exc:
            source_close_error = close_exc
        if capture_close_error is not None:
            failure = DualLiveRuntimeError("dual_live_capture_close_failed")
            if source_close_error is not None:
                source_close_error.__context__ = exc
                capture_close_error.__context__ = source_close_error
            else:
                capture_close_error.__context__ = exc
            raise failure from capture_close_error
        if source_close_error is not None:
            failure = DualLiveRuntimeError(
                "dual_live_source_identity_cleanup_failed"
            )
            failure.__cause__ = source_close_error
            failure.__context__ = exc
            raise failure
        raise


def _make_nonproduction_owned_controller_context(
    *,
    identity: RuntimeIdentity,
    runtime_start_payload: Mapping[str, Any],
    app_writer: BinaryIO,
    http_writer: BinaryIO,
    stdout_writer: BinaryIO,
    stderr_writer: BinaryIO,
    timeout_seconds: float,
) -> _OwnedControllerContext:
    """Build the explicit offline test context without importing DB capture code."""

    capture = _OwnedMechanicalCapture(
        _token=_OWNED_CONTEXT_TOKEN,
        app_writer=app_writer,
        http_writer=http_writer,
        stdout_writer=stdout_writer,
        stderr_writer=stderr_writer,
    )
    return _OwnedControllerContext(
        _token=_OWNED_CONTEXT_TOKEN,
        identity=identity,
        runtime_start_payload=runtime_start_payload,
        capture=capture,
        timeout_seconds=timeout_seconds,
    )


def _run_bound_owned_two_phase_controller(
    context: _OwnedControllerContext | _ProductionOwnedControllerContext,
) -> Any:
    if type(context) not in {
        _OwnedControllerContext,
        _ProductionOwnedControllerContext,
    }:
        _fail("dual_live_owned_context_invalid")
    from app.services import dual_live_windows

    context._begin_run()
    owned_child_factory = dual_live_windows._create_owned_phase_process
    active_counter_identity: dict[str, str] = {}

    def create(phase: str) -> _ControllerChild:
        context._assert_authority_active()
        phase_environment = context._phase_environment(phase)
        if phase_environment is None:
            created_process = owned_child_factory(
                phase,
                context._identity.runtime_instance_id,
                context._identity.wrapper_nonce_sha256,
            )
        else:
            created_process = owned_child_factory(
                phase,
                context._identity.runtime_instance_id,
                context._identity.wrapper_nonce_sha256,
                environment=phase_environment,
            )
        process = cast(_OwnedProcessProjection, created_process)
        context._bind_process(phase, process)
        active_counter_identity.clear()
        active_counter_identity.update(
            phase=phase,
            process_boot_id=process.process_boot_id,
        )
        if (
            not context.nonproduction_mechanical_only
            and process.executable_sha256
            != context._identity.interpreter_image_sha256
        ):
            _fail("dual_live_runtime_identity_mismatch")
        return _ControllerChild(
            process_boot_id=process.process_boot_id,
            process_creation_identity_sha256=(
                process.process_creation_identity_sha256
            ),
            executable_sha256=process.executable_sha256,
            job_policy_sha256=process.job_policy_sha256,
            status_nonce_sha256=process.status_nonce_sha256,
            control_nonce=process.control_nonce,
            readers=process.readers,
            send_control=process.send_control,
            wait=process.poll_exit,
            stop=process.stop,
            boot_frame_sha256=getattr(process, "boot_frame_sha256", None),
            ack_http_frame=getattr(
                process,
                "ack_http_frame",
                _noop_http_frame_ack,
            ),
        )

    def create_a() -> _ControllerChild:
        return create("A")

    def create_b() -> _ControllerChild:
        return create("B")

    def validate_http_counter(payload: bytes) -> None:
        from app.services.connector_egress_evidence import (
            COUNTER_V2_SCHEMA_ID,
            parse_connector_counter_records,
        )

        if active_counter_identity.get("phase") != "A":
            _fail("dual_live_owned_http_unexpected")
        records = parse_connector_counter_records(payload + b"\n")
        if (
            len(records) != 1
            or records[0].get("schema_id") != COUNTER_V2_SCHEMA_ID
            or records[0].get("runtime_instance_id")
            != context._identity.runtime_instance_id
            or records[0].get("process_boot_id")
            != active_counter_identity.get("process_boot_id")
        ):
            _fail("dual_live_owned_http_invalid")

    run_error: BaseException | None = None
    result: Any = None
    writer_bindings = context._capture._writer_bindings()

    def commit_http_counter(child: _ControllerChild) -> None:
        result = writer_bindings["http"].flush()
        if result is not None:
            _fail("dual_live_http_frame_commit_invalid")
        result = cast(Callable[[], object], child.ack_http_frame)()
        if result is not None:
            _fail("dual_live_http_frame_commit_invalid")

    try:
        result = _run_two_phase_controller(
            identity=context._identity,
            runtime_start_payload=context._runtime_start_payload,
            writers=writer_bindings,
            create_phase_a=create_a,
            create_phase_b=create_b,
            quiesce_phase=context._quiesce_phase,
            clear_authority=context._authority_payload,
            http_frame_validator=validate_http_counter,
            seal=context._seal_after_quiescence,
            timeout_seconds=context._timeout_seconds,
            _before_stop_publish=context._revoke_active,
            _http_frame_committed=(
                commit_http_counter
                if not context.nonproduction_mechanical_only
                else None
            ),
            _proof_scope=(
                "mechanical"
                if context.nonproduction_mechanical_only
                else "production"
            ),
        )
    except BaseException as exc:
        run_error = exc

    authority_cleanup_error = context._discard_phase_a_authority()
    close_error = context._close_all_processes()
    if close_error is not None:
        failure = DualLiveRuntimeError("dual_live_owned_close_failed")
        if authority_cleanup_error is not None:
            close_error.__context__ = authority_cleanup_error
            authority_cleanup_error.__context__ = run_error
        else:
            close_error.__context__ = run_error
        failure.__cause__ = close_error
        raise failure
    if authority_cleanup_error is not None:
        failure = DualLiveRuntimeError("dual_live_authority_clear_failed")
        authority_cleanup_error.__context__ = run_error
        raise failure from authority_cleanup_error
    if run_error is not None:
        raise run_error
    return result


def _run_owned_two_phase_controller(context: _OwnedControllerContext) -> Any:
    if type(context) is not _OwnedControllerContext:
        _fail("dual_live_owned_context_invalid")
    return _run_bound_owned_two_phase_controller(context)


def _exception_chain_has_runtime_code(
    error: BaseException,
    code: str,
) -> bool:
    pending = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, DualLiveRuntimeError) and current.code == code:
            return True
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)
    return False


def _run_production_owned_two_phase_controller(
    context: _ProductionOwnedControllerContext,
) -> Any:
    if type(context) is not _ProductionOwnedControllerContext:
        _fail("dual_live_owned_context_invalid")
    run_error: BaseException | None = None
    result: Any = None
    try:
        result = _run_bound_owned_two_phase_controller(context)
    except BaseException as exc:
        run_error = exc

    capture_close_error: BaseException | None = None
    if run_error is not None and not _exception_chain_has_runtime_code(
        run_error,
        "dual_live_capture_ownership_unproven",
    ):
        capture = cast(_OwnedCampaignCapture, context._capture)
        capture_close_error = capture._abort_close()
    source_close_error = context._close_source_custody()
    if capture_close_error is not None:
        failure = DualLiveRuntimeError("dual_live_capture_close_failed")
        if source_close_error is not None:
            source_close_error.__context__ = run_error
            capture_close_error.__context__ = source_close_error
        else:
            capture_close_error.__context__ = run_error
        raise failure from capture_close_error
    if source_close_error is not None:
        failure = DualLiveRuntimeError(
            "dual_live_source_identity_cleanup_failed"
        )
        source_close_error.__context__ = run_error
        raise failure from source_close_error
    if run_error is not None:
        if (
            isinstance(run_error, DualLiveRuntimeError)
            and run_error.code == "dual_live_phase_exit_timeout"
        ):
            raise DualLiveRuntimeError(
                "dual_live_phase_timeout_inspection_required"
            ) from run_error
        raise run_error
    return result


def _load_producer_settings() -> Any:
    configured_names: dict[str, int] = {}
    for name in os.environ:
        canonical = name.upper()
        if canonical in _PRODUCER_REQUIRED_ENVIRONMENT:
            configured_names[canonical] = configured_names.get(canonical, 0) + 1
    if set(configured_names) != _PRODUCER_REQUIRED_ENVIRONMENT or any(
        count != 1 for count in configured_names.values()
    ):
        _fail("dual_live_producer_configuration_missing")

    from app.core import config

    try:
        settings_factory = cast(Any, config.Settings)
        loaded = settings_factory(_env_file=None)
        loaded_projection = loaded.model_dump(mode="python")
        global_projection = config.settings.model_dump(mode="python")
    except BaseException as exc:
        raise DualLiveRuntimeError(
            "dual_live_producer_configuration_invalid"
        ) from exc
    if loaded_projection != global_projection:
        _fail("dual_live_producer_configuration_drift")

    path_fields = (
        "connector_campaign_definition_path",
        "connector_sciencebase_grant_path",
        "connector_nrc_aps_grant_path",
        "connector_campaign_evidence_root",
        "connector_campaign_evidence_index_path",
    )
    digest_fields = (
        "connector_campaign_definition_sha256",
        "connector_sciencebase_grant_sha256",
        "connector_nrc_aps_grant_sha256",
        "connector_campaign_evidence_index_sha256",
    )
    try:
        paths = tuple(Path(getattr(loaded, field)) for field in path_fields)
        digests = tuple(getattr(loaded, field) for field in digest_fields)
        database_url = getattr(loaded, "database_url")
        storage_dir = Path(getattr(loaded, "storage_dir"))
        nrc_key = getattr(loaded, "nrc_adams_subscription_key")
    except (AttributeError, TypeError) as exc:
        raise DualLiveRuntimeError(
            "dual_live_producer_configuration_invalid"
        ) from exc
    if (
        any(not path.is_absolute() for path in paths)
        or not storage_dir.is_absolute()
        or not isinstance(database_url, str)
        or not database_url.strip()
        or not isinstance(nrc_key, str)
        or not nrc_key.strip()
        or getattr(loaded, "deployment_mode", None) != "local"
        or getattr(loaded, "auth_owner", None) != "none"
        or getattr(loaded, "trusted_proxy_mode", None) is not False
        or getattr(loaded, "connector_live_egress_enabled", None) is not True
        or getattr(
            loaded,
            "connector_live_egress_exclusive_proof_mode",
            None,
        )
        is not True
    ):
        _fail("dual_live_producer_configuration_invalid")
    for digest in digests:
        _require_sha256(digest, "dual_live_producer_configuration_invalid")
    return loaded


@dataclass(frozen=True, slots=True)
class _ProducerGrantTimeoutInput:
    connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"]
    max_physical_requests: int
    request_timeout_seconds: int
    min_request_interval_ms: int


@dataclass(frozen=True, slots=True)
class _ProducerPreauthorization:
    code_revision: str
    grant_timeouts: tuple[_ProducerGrantTimeoutInput, ...]

    def __post_init__(self) -> None:
        _require_code_revision(
            self.code_revision,
            "dual_live_local_runner_authorization_denied",
        )
        if (
            type(self.grant_timeouts) is not tuple
            or len(self.grant_timeouts) != 2
            or any(
                type(value) is not _ProducerGrantTimeoutInput
                for value in self.grant_timeouts
            )
        ):
            _fail("dual_live_phase_timeout_contract_invalid")
        _producer_phase_timeout_contract(self.grant_timeouts)

    def timeout_contract(self) -> dict[str, Any]:
        return _producer_phase_timeout_contract(self.grant_timeouts)

    def phase_timeout_seconds(self) -> Mapping[str, float]:
        contract = self.timeout_contract()
        return _validated_phase_timeout_seconds(
            {
                "A": contract["phase_a_timeout_ms"] / 1000,
                "B": contract["phase_b_timeout_ms"] / 1000,
            },
            "dual_live_phase_timeout_contract_invalid",
        )


def _producer_phase_timeout_contract(
    grant_timeouts: Sequence[_ProducerGrantTimeoutInput],
) -> dict[str, Any]:
    if len(grant_timeouts) != 2 or any(
        type(value) is not _ProducerGrantTimeoutInput
        for value in grant_timeouts
    ):
        _fail("dual_live_phase_timeout_contract_invalid")
    grants: list[dict[str, object]] = []
    phase_a_timeout = _PRODUCER_FIXED_OVERHEAD_MILLISECONDS
    for value in grant_timeouts:
        requests = value.max_physical_requests
        request_timeout = value.request_timeout_seconds
        interval = value.min_request_interval_ms
        if any(
            isinstance(candidate, bool) or not isinstance(candidate, int)
            for candidate in (requests, request_timeout, interval)
        ):
            _fail("dual_live_phase_timeout_contract_invalid")
        phase_a_timeout += requests * (
            request_timeout * 1000
            + _PRODUCER_COUNTER_ACK_TIMEOUT_MILLISECONDS
        )
        phase_a_timeout += (requests - 1) * interval
        if phase_a_timeout > _MAX_PHASE_TIMEOUT_MILLISECONDS:
            _fail("dual_live_phase_timeout_contract_invalid")
        grants.append(
            {
                "connector_key": value.connector_key,
                "max_physical_requests": requests,
                "request_timeout_seconds": request_timeout,
                "min_request_interval_ms": interval,
            }
        )
    contract = {
        "schema_id": DUAL_LIVE_PHASE_TIMEOUT_SCHEMA_ID,
        "phase_a_timeout_ms": phase_a_timeout,
        "phase_b_timeout_ms": _PRODUCER_PHASE_B_TIMEOUT_MILLISECONDS,
        "fixed_non_egress_overhead_ms": (
            _PRODUCER_FIXED_OVERHEAD_MILLISECONDS
        ),
        "counter_ack_timeout_ms": _PRODUCER_COUNTER_ACK_TIMEOUT_MILLISECONDS,
        "connector_grants": grants,
    }
    _validate_phase_timeout_contract(
        contract,
        "dual_live_phase_timeout_contract_invalid",
    )
    return contract


def _preauthorize_producer_connectors(
    *,
    settings: Any,
    campaign_id: str,
    campaign_fingerprint: str,
) -> _ProducerPreauthorization:
    """Re-derive both OS/workspace-bound write receipts before effects."""

    from app.schemas.api import DualLiveCampaignDefinitionV1
    from app.services import connector_egress_authorization

    try:
        _, definition_bytes, _ = (
            connector_egress_authorization._read_protected_bytes(
                settings.connector_campaign_definition_path,
                expected_sha256=(
                    settings.connector_campaign_definition_sha256
                ),
                label="current dual-live campaign definition",
                settings_override=settings,
            )
        )
        definition = connector_egress_authorization._parse_model(
            definition_bytes,
            DualLiveCampaignDefinitionV1,
            label="current dual-live campaign definition",
        )
        code_revision = _require_code_revision(
            definition.code_revision,
            "dual_live_local_runner_authorization_denied",
        )
        now = datetime.now(UTC)
        verified_campaign = (
            connector_egress_authorization
            .resolve_current_dual_live_campaign_definition(
                expected_campaign_id=campaign_id,
                expected_campaign_fingerprint=campaign_fingerprint,
                code_revision=code_revision,
                now=now,
            )
        )
        grant_inputs = (
            (
                "nrc_adams_aps",
                settings.connector_nrc_aps_grant_sha256,
            ),
            (
                "sciencebase_mcs",
                settings.connector_sciencebase_grant_sha256,
            ),
        )
        grant_timeouts: list[_ProducerGrantTimeoutInput] = []
        for connector_key, grant_sha256 in grant_inputs:
            verified_grant = (
                connector_egress_authorization
                .resolve_current_connector_egress_grant(
                    verified_campaign=verified_campaign,
                    connector_key=connector_key,
                    expected_grant_sha256=grant_sha256,
                    campaign_id=campaign_id,
                    campaign_fingerprint=campaign_fingerprint,
                    code_revision=code_revision,
                    now=now,
                )
            )
            receipt = (
                connector_egress_authorization
                .authorize_connector_egress_local_runner(
                    verified_grant=verified_grant,
                    access="write",
                )
            )
            if (
                receipt.connector_key != connector_key
                or receipt.campaign_id != campaign_id
                or receipt.campaign_fingerprint != campaign_fingerprint
                or receipt.grant_sha256 != grant_sha256
                or receipt.access != "write"
                or receipt.auth_owner_mode
                != "AUTH_OWNER_none_single_operator_dev_profile"
            ):
                _fail("dual_live_local_runner_authorization_denied")
            grant_timeouts.append(
                _ProducerGrantTimeoutInput(
                    connector_key=cast(
                        Literal["sciencebase_mcs", "nrc_adams_aps"],
                        connector_key,
                    ),
                    max_physical_requests=(
                        verified_grant.model.max_physical_requests
                    ),
                    request_timeout_seconds=(
                        verified_grant.model.request_timeout_seconds
                    ),
                    min_request_interval_ms=(
                        verified_grant.model.min_request_interval_ms
                    ),
                )
            )
    except DualLiveRuntimeError:
        raise
    except BaseException as exc:
        raise DualLiveRuntimeError(
            "dual_live_local_runner_authorization_denied"
        ) from exc
    return _ProducerPreauthorization(
        code_revision=code_revision,
        grant_timeouts=tuple(grant_timeouts),
    )


def _producer_phase_environments(
    settings: Any,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
    code_revision: str,
    dependency_set_sha256: str,
) -> tuple[Mapping[str, str], Mapping[str, str]]:
    """Build immutable A-current-authority and B-historical-only environments."""

    dependency_digest = _require_sha256(
        dependency_set_sha256,
        "dual_live_dependency_provenance_invalid",
    )
    shared = {
        "AUTH_OWNER": "none",
        "DATABASE_URL": str(settings.database_url),
        "DEPLOYMENT_MODE": "local",
        "DUAL_LIVE_CAMPAIGN_FINGERPRINT": campaign_fingerprint,
        "DUAL_LIVE_CAMPAIGN_ID": campaign_id,
        "DUAL_LIVE_CODE_REVISION": code_revision,
        "DUAL_LIVE_DEPENDENCY_SET_SHA256": dependency_digest,
        "STORAGE_DIR": str(settings.storage_dir),
        "TRUSTED_PROXY_MODE": "false",
    }
    phase_a = {
        **shared,
        "CONNECTOR_CAMPAIGN_DEFINITION_PATH": str(
            settings.connector_campaign_definition_path
        ),
        "CONNECTOR_CAMPAIGN_DEFINITION_SHA256": str(
            settings.connector_campaign_definition_sha256
        ),
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH": str(
            settings.connector_campaign_evidence_index_path
        ),
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256": str(
            settings.connector_campaign_evidence_index_sha256
        ),
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT": str(
            settings.connector_campaign_evidence_root
        ),
        "CONNECTOR_LIVE_EGRESS_ENABLED": "true",
        "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE": "true",
        "CONNECTOR_NRC_APS_GRANT_PATH": str(
            settings.connector_nrc_aps_grant_path
        ),
        "CONNECTOR_NRC_APS_GRANT_SHA256": str(
            settings.connector_nrc_aps_grant_sha256
        ),
        "CONNECTOR_SCIENCEBASE_GRANT_PATH": str(
            settings.connector_sciencebase_grant_path
        ),
        "CONNECTOR_SCIENCEBASE_GRANT_SHA256": str(
            settings.connector_sciencebase_grant_sha256
        ),
        "NRC_ADAMS_APS_SUBSCRIPTION_KEY": str(
            settings.nrc_adams_subscription_key
        ),
    }
    phase_b = {
        **shared,
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH": str(
            settings.connector_campaign_evidence_index_path
        ),
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256": str(
            settings.connector_campaign_evidence_index_sha256
        ),
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT": str(
            settings.connector_campaign_evidence_root
        ),
        "CONNECTOR_LIVE_EGRESS_ENABLED": "false",
        "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE": "false",
    }
    return MappingProxyType(phase_a), MappingProxyType(phase_b)


def _preload_owned_workload_modules() -> None:
    """Materialize workload modules, and their loggers, before the freeze.

    run_owned_phase_a_workload imports these lazily at :5373-5381 and, via
    _phase_a_acquisition_projection, at :5543-5544 - all after
    tools/dual_live_run.py:432 has frozen the logger topology. SQLAlchemy
    creates loggers at import (sqlalchemy/log.py:53, :77) and per Engine and
    Pool instance (sqlalchemy/log.py:248); app/db/session.py:18 runs
    create_engine at module scope. Importing here keeps every getLogger call
    ahead of the freeze and lets tools/dual_live_run.py:424-430 normalize the
    resulting loggers before the census. This set also covers
    run_owned_phase_b_workload (:6526, :6556-6557, :6261-6266, :5739), whose
    own materialization is otherwise only an incidental side effect of
    _install_phase_b_connector_guards.
    """
    from app.db import session  # noqa: F401
    from app.models import models  # noqa: F401
    from app.schemas.api import ConnectorEgressArmingIn  # noqa: F401
    from app.services import (  # noqa: F401
        connector_egress_arming,
        connector_egress_authorization,
        connector_egress_evidence,
        connector_egress_transport,
        connectors_nrc_adams,
        connectors_sciencebase,
    )


def run_owned_phase_a_workload(
    *,
    runtime_instance_id: str,
    process_boot_id: str,
    append_counter_frame: Callable[[bytes], None],
    revocation_is_set: Callable[[], bool],
    acquire_send_idle: Callable[[], None],
    release_send_idle: Callable[[], None],
) -> Mapping[str, Any]:
    """Arm, claim, and execute NRC then ScienceBase inside Phase A."""

    runtime_id = _require_uuid4(
        runtime_instance_id,
        "dual_live_phase_a_runtime_invalid",
    )
    boot_id = _require_sha256(
        process_boot_id,
        "dual_live_phase_a_runtime_invalid",
    )
    callbacks = (
        append_counter_frame,
        revocation_is_set,
        acquire_send_idle,
        release_send_idle,
    )
    if any(not callable(callback) for callback in callbacks):
        _fail("dual_live_phase_a_runtime_invalid")
    campaign_id = _require_uuid4(
        os.environ.get("DUAL_LIVE_CAMPAIGN_ID"),
        "dual_live_phase_a_environment_invalid",
    )
    campaign_fingerprint = _require_sha256(
        os.environ.get("DUAL_LIVE_CAMPAIGN_FINGERPRINT"),
        "dual_live_phase_a_environment_invalid",
    )
    code_revision = _require_code_revision(
        os.environ.get("DUAL_LIVE_CODE_REVISION"),
        "dual_live_phase_a_environment_invalid",
    )
    settings = _load_producer_settings()

    from app.db import session as db_session
    from app.schemas.api import ConnectorEgressArmingIn
    from app.services import (
        connector_egress_arming,
        connector_egress_authorization,
        connector_egress_transport,
        connectors_nrc_adams,
        connectors_sciencebase,
    )

    def resolve_campaign() -> Any:
        resolved = (
            connector_egress_authorization
            .resolve_current_dual_live_campaign_definition(
                expected_campaign_id=campaign_id,
                expected_campaign_fingerprint=campaign_fingerprint,
                code_revision=code_revision,
                now=datetime.now(UTC),
            )
        )
        if resolved.model.code_revision != code_revision:
            _fail("dual_live_phase_a_authority_changed")
        return resolved

    def arm_and_claim(
        *,
        connector_key: Literal["sciencebase_mcs", "nrc_adams_aps"],
        verified_campaign: Any,
        grant_sha256: str,
    ) -> str:
        if revocation_is_set() is not False:
            _fail("dual_live_phase_a_revoked")
        now = datetime.now(UTC)
        grant = (
            connector_egress_authorization
            .resolve_current_connector_egress_grant(
                verified_campaign=verified_campaign,
                connector_key=connector_key,
                expected_grant_sha256=grant_sha256,
                campaign_id=campaign_id,
                campaign_fingerprint=campaign_fingerprint,
                code_revision=code_revision,
                now=now,
            )
        )
        receipt = (
            connector_egress_authorization
            .authorize_connector_egress_local_runner(
                verified_grant=grant,
                access="write",
            )
        )
        db = db_session.SessionLocal()
        try:
            run, created = connector_egress_arming.create_connector_egress_arming(
                db,
                payload=ConnectorEgressArmingIn(
                    schema_id="project6.connector_egress_arming.v1",
                    client_request_id=(
                        f"dual-live-arm-{connector_key}-{campaign_id}"
                    ),
                    connector_key=connector_key,
                    campaign_id=campaign_id,
                    campaign_fingerprint=campaign_fingerprint,
                    grant_sha256=grant_sha256,
                ),
                verified_grant=grant,
                operator_receipt=receipt.model_dump(mode="json"),
                code_revision=code_revision,
            )
            if created is not True:
                _fail("dual_live_phase_a_arming_not_fresh")
            claimed, claimed_now = (
                connector_egress_arming.claim_connector_egress_arming(
                    db,
                    connector_run_id=run.connector_run_id,
                    execution_idempotency_key=(
                        f"dual-live-execute-{connector_key}-{campaign_id}"
                    ),
                    expected_arming_fingerprint=_require_sha256(
                        run.request_fingerprint,
                        "dual_live_phase_a_arming_invalid",
                    ),
                    now=datetime.now(UTC),
                )
            )
            if (
                claimed_now is not True
                or claimed.connector_run_id != run.connector_run_id
            ):
                _fail("dual_live_phase_a_claim_not_fresh")
            return str(claimed.connector_run_id)
        finally:
            if cast(Callable[[], object], db.close)() is not None:
                _fail("dual_live_phase_a_database_close_failed")

    counter_payloads: list[bytes] = []

    def append_and_capture_counter(payload: bytes) -> None:
        if not isinstance(payload, bytes) or not payload:
            _fail("dual_live_phase_a_counter_invalid")
        counter_payloads.append(payload)
        append_counter_frame(payload)

    verified_campaign = resolve_campaign()
    counter_context = connector_egress_transport.ConnectorCounterRuntimeContext(
        runtime_instance_id=runtime_id,
        process_boot_id=boot_id,
        append_frame=append_and_capture_counter,
        revocation_is_set=revocation_is_set,
        acquire_send_idle=acquire_send_idle,
        release_send_idle=release_send_idle,
    )
    with connector_egress_transport.connector_counter_runtime(counter_context):
        nrc_run_id = arm_and_claim(
            connector_key="nrc_adams_aps",
            verified_campaign=verified_campaign,
            grant_sha256=str(settings.connector_nrc_aps_grant_sha256),
        )
        connectors_nrc_adams.execute_nrc_adams_run(nrc_run_id)
        nrc_counter_count = len(counter_payloads)
        db = db_session.SessionLocal()
        try:
            connector_egress_arming.evaluate_nrc_acquisition_success(
                db,
                verified_definition=verified_campaign,
            )
        finally:
            if cast(Callable[[], object], db.close)() is not None:
                _fail("dual_live_phase_a_database_close_failed")
        verified_campaign = resolve_campaign()
        sciencebase_run_id = arm_and_claim(
            connector_key="sciencebase_mcs",
            verified_campaign=verified_campaign,
            grant_sha256=str(settings.connector_sciencebase_grant_sha256),
        )
        connectors_sciencebase.execute_connector_run(sciencebase_run_id)
    db = db_session.SessionLocal()
    try:
        return {
            "connector_acquisitions": [
                _phase_a_acquisition_projection(
                    db,
                    connector_key="nrc_adams_aps",
                    connector_run_id=nrc_run_id,
                    counter_payloads=counter_payloads[:nrc_counter_count],
                ),
                _phase_a_acquisition_projection(
                    db,
                    connector_key="sciencebase_mcs",
                    connector_run_id=sciencebase_run_id,
                    counter_payloads=counter_payloads[nrc_counter_count:],
                ),
            ],
            "downstream_action_count": 0,
        }
    finally:
        if cast(Callable[[], object], db.close)() is not None:
            _fail("dual_live_phase_a_database_close_failed")


def _phase_a_acquisition_projection(
    db: Any,
    *,
    connector_key: str,
    connector_run_id: str,
    counter_payloads: Sequence[bytes],
) -> dict[str, Any]:
    from sqlalchemy import select

    from app.models.models import ConnectorRun, ConnectorRunEvent, ConnectorRunTarget
    from app.services.connector_egress_evidence import (
        derive_terminal_request_ledger,
        parse_connector_counter_records,
    )

    run = db.get(ConnectorRun, connector_run_id)
    records = tuple(
        record
        for payload in counter_payloads
        for record in parse_connector_counter_records(payload + b"\n")
    )
    targets = tuple(
        db.scalars(
            select(ConnectorRunTarget)
            .where(ConnectorRunTarget.connector_run_id == connector_run_id)
            .order_by(
                ConnectorRunTarget.ordinal.asc(),
                ConnectorRunTarget.connector_run_target_id.asc(),
            )
            .limit(2)
        ).all()
    )
    terminal_events = tuple(
        db.scalars(
            select(ConnectorRunEvent)
            .where(ConnectorRunEvent.connector_run_id == connector_run_id)
            .where(ConnectorRunEvent.event_type == "egress_run_terminal")
            .order_by(
                ConnectorRunEvent.created_at.asc(),
                ConnectorRunEvent.connector_run_event_id.asc(),
            )
            .limit(2)
        ).all()
    )
    ledger = derive_terminal_request_ledger(
        db,
        connector_run_id=connector_run_id,
        counter_records=records,
    )
    if (
        run is None
        or run.connector_key != connector_key
        or run.status != "completed"
        or len(targets) != 1
        or targets[0].status != "downloaded"
        or _LOWERCASE_SHA256.fullmatch(
            str(targets[0].downloaded_sha256 or "")
        )
        is None
        or len(terminal_events) != 1
        or terminal_events[0].status_after != "completed"
        or not ledger.eligible
    ):
        _fail("dual_live_phase_a_projection_invalid")
    return {
        "action_codes": [
            "derived_arming",
            "raw_acquisition",
            "terminal_transition",
        ],
        "connector_key": connector_key,
        "connector_run_id": connector_run_id,
        "connector_run_target_id": str(targets[0].connector_run_target_id),
        "ledger_terminal_hash": ledger.ledger_terminal_hash,
        "raw_content_sha256": str(targets[0].downloaded_sha256),
        "terminal_transition_count": 1,
    }


@dataclass(frozen=True, slots=True)
class _OwnedPhaseBTargets:
    nrc_run_id: str
    nrc_target_id: str
    sciencebase_run_id: str
    sciencebase_target_id: str
    sciencebase_intake_record_id: str


def _phase_b_environment_coordinates() -> tuple[str, str, str]:
    relevant = _PHASE_B_REQUIRED_ENVIRONMENT | _PHASE_B_FORBIDDEN_ENVIRONMENT
    configured: dict[str, list[str]] = {}
    for name in os.environ:
        canonical = name.upper()
        if canonical in relevant:
            configured.setdefault(canonical, []).append(name)
    if any(name in configured for name in _PHASE_B_FORBIDDEN_ENVIRONMENT):
        _fail("dual_live_phase_b_environment_invalid")
    if set(configured) != _PHASE_B_REQUIRED_ENVIRONMENT or any(
        len(names) != 1 for names in configured.values()
    ):
        _fail("dual_live_phase_b_environment_invalid")
    values = {
        canonical: os.environ[names[0]]
        for canonical, names in configured.items()
    }
    campaign_id = _require_uuid4(
        values["DUAL_LIVE_CAMPAIGN_ID"],
        "dual_live_phase_b_environment_invalid",
    )
    campaign_fingerprint = _require_sha256(
        values["DUAL_LIVE_CAMPAIGN_FINGERPRINT"],
        "dual_live_phase_b_environment_invalid",
    )
    code_revision = _require_code_revision(
        values["DUAL_LIVE_CODE_REVISION"],
        "dual_live_phase_b_environment_invalid",
    )
    index_sha256 = _require_sha256(
        values["CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256"],
        "dual_live_phase_b_environment_invalid",
    )
    del index_sha256
    paths = (
        Path(values["CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH"]),
        Path(values["CONNECTOR_CAMPAIGN_EVIDENCE_ROOT"]),
        Path(values["STORAGE_DIR"]),
    )
    if (
        any(not path.is_absolute() for path in paths)
        or not values["DATABASE_URL"].strip()
        or values["AUTH_OWNER"] != "none"
        or values["DEPLOYMENT_MODE"] != "local"
        or values["TRUSTED_PROXY_MODE"] != "false"
        or values["CONNECTOR_LIVE_EGRESS_ENABLED"] != "false"
        or values["CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE"] != "false"
    ):
        _fail("dual_live_phase_b_environment_invalid")
    return campaign_id, campaign_fingerprint, code_revision


def _deny_phase_b_connector_call(*args: object, **kwargs: object) -> NoReturn:
    del args, kwargs
    _fail("dual_live_phase_b_connector_call_denied")


_PHASE_B_CONNECTOR_GUARD_TARGETS: tuple[tuple[object, str], ...] | None = None


def _install_phase_b_connector_guards() -> None:
    global _PHASE_B_CONNECTOR_GUARD_TARGETS
    from app.services import (
        connector_egress_transport,
        connectors_nrc_adams,
        connectors_sciencebase,
    )

    targets = (
        (connector_egress_transport.BoundedConnectorTransport, "send_once"),
        (connectors_nrc_adams, "execute_nrc_adams_run"),
        (connectors_sciencebase, "execute_connector_run"),
    )
    if _PHASE_B_CONNECTOR_GUARD_TARGETS is not None:
        if _PHASE_B_CONNECTOR_GUARD_TARGETS != targets:
            _fail("dual_live_phase_b_connector_guard_failed")
        _assert_phase_b_connector_guards()
        return
    for target, name in targets:
        setattr(target, name, _deny_phase_b_connector_call)
    _PHASE_B_CONNECTOR_GUARD_TARGETS = targets
    _assert_phase_b_connector_guards()


def _assert_phase_b_connector_guards() -> None:
    targets = _PHASE_B_CONNECTOR_GUARD_TARGETS
    if targets is None or any(
        getattr(target, name, None) is not _deny_phase_b_connector_call
        for target, name in targets
    ):
        _fail("dual_live_phase_b_connector_guard_failed")


def exercise_owned_phase_b_connector_guard() -> None:
    _assert_phase_b_connector_guards()
    targets = _PHASE_B_CONNECTOR_GUARD_TARGETS
    assert targets is not None
    callback = getattr(targets[0][0], targets[0][1])
    try:
        callback()
    except DualLiveRuntimeError as exc:
        if exc.code != "dual_live_phase_b_connector_call_denied":
            raise
    else:
        _fail("dual_live_phase_b_connector_guard_failed")
    _assert_phase_b_connector_guards()


def _resolve_owned_phase_b_targets(
    db: Any,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
    code_revision: str,
) -> _OwnedPhaseBTargets:
    from sqlalchemy import select

    from app.models.models import (
        ConnectorRun,
        ConnectorRunTarget,
        L3ConnectorSourceIntakeRecord,
    )

    connector_keys = ("nrc_adams_aps", "sciencebase_mcs")
    runs = tuple(
        db.scalars(
            select(ConnectorRun)
            .where(ConnectorRun.connector_key.in_(connector_keys))
            .order_by(ConnectorRun.connector_run_id.asc())
            .limit(_PHASE_B_RUN_SCAN_CAP + 1)
        ).all()
    )
    if len(runs) > _PHASE_B_RUN_SCAN_CAP:
        _fail("dual_live_phase_b_run_scan_limit")
    matches: dict[str, list[Any]] = {key: [] for key in connector_keys}
    expected_envelope = {
        "campaign_id": campaign_id,
        "campaign_fingerprint": campaign_fingerprint,
        "code_revision": code_revision,
    }
    for run in runs:
        config = run.request_config_json
        envelope = (
            config.get("connector_egress_arming")
            if isinstance(config, Mapping)
            else None
        )
        connector_key = str(run.connector_key)
        if (
            connector_key not in matches
            or not isinstance(envelope, Mapping)
            or envelope.get("connector_key") != connector_key
            or any(envelope.get(key) != value for key, value in expected_envelope.items())
        ):
            continue
        matches[connector_key].append(run)

    selected: dict[str, Any] = {}
    for connector_key, candidates in matches.items():
        if len(candidates) != 1:
            _fail("dual_live_phase_b_campaign_run_cardinality")
        run = candidates[0]
        expected_source_system = (
            "sciencebase" if connector_key == "sciencebase_mcs" else "nrc_adams"
        )
        if (
            run.source_system != expected_source_system
            or run.source_mode != "strict_live_egress"
            or run.status != "completed"
            or run.completed_at is None
            or run.execution_lease_owner is not None
            or run.execution_lease_token is not None
            or run.execution_lease_expires_at is not None
            or run.terminal_target_count != 1
            or run.nonterminal_target_count != 0
            or run.downloaded_count != 1
            or run.failed_count != 0
        ):
            _fail("dual_live_phase_b_campaign_run_invalid")
        targets = tuple(
            db.scalars(
                select(ConnectorRunTarget)
                .where(ConnectorRunTarget.connector_run_id == run.connector_run_id)
                .order_by(
                    ConnectorRunTarget.ordinal.asc(),
                    ConnectorRunTarget.connector_run_target_id.asc(),
                )
                .limit(2)
            ).all()
        )
        if len(targets) != 1:
            _fail("dual_live_phase_b_target_cardinality")
        target = targets[0]
        if (
            target.ordinal != 1
            or target.status != "downloaded"
            or not isinstance(target.raw_storage_ref, str)
            or not target.raw_storage_ref.strip()
            or not isinstance(target.downloaded_sha256, str)
            or _LOWERCASE_SHA256.fullmatch(target.downloaded_sha256) is None
            or target.public_read_confirmed is not True
            or target.retry_eligible is not False
        ):
            _fail("dual_live_phase_b_target_invalid")
        selected[connector_key] = target

    sciencebase_target = selected["sciencebase_mcs"]
    intake_rows = tuple(
        db.scalars(
            select(L3ConnectorSourceIntakeRecord)
            .where(
                L3ConnectorSourceIntakeRecord.connector_run_target_id
                == sciencebase_target.connector_run_target_id
            )
            .order_by(
                L3ConnectorSourceIntakeRecord.connector_source_intake_record_id.asc()
            )
            .limit(2)
        ).all()
    )
    if len(intake_rows) != 1:
        _fail("dual_live_phase_b_sciencebase_intake_cardinality")
    intake = intake_rows[0]
    if (
        intake.connector_key != "sciencebase_mcs"
        or intake.connector_run_id != sciencebase_target.connector_run_id
        or intake.status != "recorded"
    ):
        _fail("dual_live_phase_b_sciencebase_intake_invalid")
    return _OwnedPhaseBTargets(
        nrc_run_id=str(selected["nrc_adams_aps"].connector_run_id),
        nrc_target_id=str(selected["nrc_adams_aps"].connector_run_target_id),
        sciencebase_run_id=str(sciencebase_target.connector_run_id),
        sciencebase_target_id=str(sciencebase_target.connector_run_target_id),
        sciencebase_intake_record_id=str(
            intake.connector_source_intake_record_id
        ),
    )


def _owned_phase_b_json_mapping(value: object, code: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail(code)
    try:
        copied = strict_json_loads(canonical_json_bytes(dict(value)))
    except (TypeError, ValueError):
        _fail(code)
    if type(copied) is not dict:
        _fail(code)
    return cast(dict[str, Any], copied)


def _owned_phase_b_record_action(
    receipts: list[dict[str, str]],
    *,
    action: str,
    result: object,
) -> dict[str, Any]:
    copied = _owned_phase_b_json_mapping(
        result,
        f"dual_live_phase_b_{action}_invalid",
    )
    receipts.append(
        {
            "action": action,
            "result_sha256": hashlib.sha256(
                canonical_json_bytes(copied)
            ).hexdigest(),
        }
    )
    return copied


def _owned_phase_b_required_text(
    value: Mapping[str, Any],
    field: str,
    code: str,
) -> str:
    text = value.get(field)
    if not isinstance(text, str) or not text.strip():
        _fail(code)
    return text


def _owned_phase_b_decision_basis(candidate: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "source_ref",
        "query_basis",
        "provenance_ref",
        "source_identity",
        "source_provenance",
        "payload",
        "load_summary",
    )
    if any(field not in candidate for field in fields):
        _fail("dual_live_phase_b_candidate_decision_basis_invalid")
    return _owned_phase_b_json_mapping(
        {field: candidate[field] for field in fields},
        "dual_live_phase_b_candidate_decision_basis_invalid",
    )


def _complete_owned_phase_b_chain(
    db: Any,
    *,
    layer3_workbench: Any,
    connector_key: str,
    action_prefix: str,
    request_prefix: str,
    gate_b_result: object,
    source_binding: Mapping[str, Any],
    action_receipts: list[dict[str, str]],
) -> dict[str, Any]:
    gate_b = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_gate_b_decision",
        result=gate_b_result,
    )
    session_id = _owned_phase_b_required_text(
        gate_b,
        "session_id",
        "dual_live_phase_b_gate_b_session_invalid",
    )
    gate_c = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_gate_c_typing",
        result=layer3_workbench.gate_c_preview(
            db,
            {
                "client_request_id": f"{request_prefix}-gate-c",
                "session_id": session_id,
                "commit_typing": True,
            },
        ),
    )
    if gate_c.get("next_state") != "plan_preview_ready":
        _fail("dual_live_phase_b_gate_c_not_ready")
    plan_preview = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_plan_preview",
        result=layer3_workbench.plan_preview(
            db,
            {
                "client_request_id": f"{request_prefix}-plan-preview",
                "session_id": session_id,
            },
        ),
    )
    preview_id = _owned_phase_b_required_text(
        plan_preview,
        "preview_id",
        "dual_live_phase_b_plan_preview_invalid",
    )
    preview_hash = _owned_phase_b_required_text(
        plan_preview,
        "preview_hash",
        "dual_live_phase_b_plan_preview_invalid",
    )
    if _LOWERCASE_SHA256.fullmatch(preview_hash) is None:
        _fail("dual_live_phase_b_plan_preview_invalid")
    approval = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_plan_approval",
        result=layer3_workbench.plan_approval(
            db,
            {
                "client_request_id": f"{request_prefix}-plan-approval",
                "session_id": session_id,
                "preview_id": preview_id,
                "preview_hash": preview_hash,
                "operator_confirmation": True,
            },
        ),
    )
    analysis_plan_id = _owned_phase_b_required_text(
        approval,
        "analysis_plan_id",
        "dual_live_phase_b_plan_approval_invalid",
    )
    selection = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_execution_selection",
        result=layer3_workbench.execution_selection(
            db,
            {
                "client_request_id": f"{request_prefix}-selection",
                "session_id": session_id,
                "analysis_plan_id": analysis_plan_id,
                "preview_id": preview_id,
                "preview_hash": preview_hash,
            },
        ),
    )
    pass_run_ids = selection.get("pass_run_ids")
    if (
        not isinstance(pass_run_ids, list)
        or len(pass_run_ids) != 1
        or not isinstance(pass_run_ids[0], str)
        or not pass_run_ids[0]
    ):
        _fail("dual_live_phase_b_execution_selection_invalid")
    pass_run_id = pass_run_ids[0]
    common = {
        "session_id": session_id,
        "analysis_plan_id": analysis_plan_id,
        "pass_run_id": pass_run_id,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
    }
    start = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_analysis_execution_start",
        result=layer3_workbench.analysis_execution_start(
            db,
            {
                "client_request_id": f"{request_prefix}-start",
                **common,
            },
        ),
    )
    analysis_run_id_value = start.get("analysis_run_id")
    analysis_run_id = (
        analysis_run_id_value
        if isinstance(analysis_run_id_value, str) and analysis_run_id_value
        else None
    )
    review = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_execution_result_review",
        result=layer3_workbench.execution_result_review(
            db,
            {
                "client_request_id": f"{request_prefix}-review",
                **common,
                "analysis_run_id": analysis_run_id,
                "operator_decision": "approved",
                "reviewed_output_items": [],
            },
        ),
    )
    if review.get("review_state") != "execution_result_review_approved":
        _fail("dual_live_phase_b_result_review_not_approved")
    review_ref = _owned_phase_b_required_text(
        review,
        "review_record_ref",
        "dual_live_phase_b_result_review_invalid",
    )
    package_preview = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_package_review_preview",
        result=layer3_workbench.package_review_preview(
            db,
            {
                "client_request_id": f"{request_prefix}-package-preview",
                **common,
                "analysis_run_id": analysis_run_id,
                "result_review_record_ref": review_ref,
            },
        ),
    )
    package_preview_hash = _owned_phase_b_required_text(
        package_preview,
        "package_review_preview_hash",
        "dual_live_phase_b_package_preview_invalid",
    )
    package_commit = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_package_construction_commit",
        result=layer3_workbench.package_construction_commit(
            db,
            {
                "client_request_id": f"{request_prefix}-package-commit",
                **common,
                "analysis_run_id": analysis_run_id,
                "result_review_record_ref": review_ref,
                "package_review_preview_hash": package_preview_hash,
                "expected_package_kinds": list(_PHASE_B_PACKAGE_KINDS),
            },
        ),
    )
    output_package_ids = package_commit.get("output_package_ids")
    payload_hashes = package_commit.get("payload_hashes")
    payload_refs = package_commit.get("payload_refs")
    if (
        tuple(package_commit.get("package_kinds") or ()) != _PHASE_B_PACKAGE_KINDS
        or not isinstance(output_package_ids, list)
        or len(output_package_ids) != 3
        or len(set(output_package_ids)) != 3
        or not all(isinstance(item, str) and item for item in output_package_ids)
        or not isinstance(payload_hashes, list)
        or len(payload_hashes) != 3
        or not all(
            isinstance(item, str) and _LOWERCASE_SHA256.fullmatch(item)
            for item in payload_hashes
        )
        or not isinstance(payload_refs, list)
        or len(payload_refs) != 3
        or not all(isinstance(item, str) and item for item in payload_refs)
    ):
        _fail("dual_live_phase_b_package_commit_invalid")

    construction_basis_hash = _owned_phase_b_required_text(
        package_commit,
        "construction_basis_hash",
        "dual_live_phase_b_package_commit_invalid",
    )
    if _LOWERCASE_SHA256.fullmatch(construction_basis_hash) is None:
        _fail("dual_live_phase_b_package_commit_invalid")
    reconciliation_record_id = _owned_phase_b_required_text(
        package_commit,
        "reconciliation_record_id",
        "dual_live_phase_b_package_commit_invalid",
    )
    submit = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_package_review_submit",
        result=layer3_workbench.package_review_submit(
            db,
            {
                "client_request_id": f"{request_prefix}-package-submit",
                **common,
                "analysis_run_id": analysis_run_id,
                "result_review_record_ref": review_ref,
                "package_review_preview_hash": package_preview_hash,
                "construction_basis_hash": construction_basis_hash,
                "reconciliation_record_id": reconciliation_record_id,
                "output_package_ids": output_package_ids,
                "payload_refs": payload_refs,
                "payload_hashes": payload_hashes,
                "expected_package_kinds": list(_PHASE_B_PACKAGE_KINDS),
                "operator_decision": "approved",
            },
        ),
    )
    if submit.get("package_review_state") != "package_review_approved":
        _fail("dual_live_phase_b_package_submit_not_approved")
    submit_ref = _owned_phase_b_required_text(
        submit,
        "submit_record_ref",
        "dual_live_phase_b_package_submit_invalid",
    )
    submit_schema_id = _owned_phase_b_required_text(
        submit,
        "schema_id",
        "dual_live_phase_b_package_submit_invalid",
    )
    handoff = _owned_phase_b_record_action(
        action_receipts,
        action=f"{action_prefix}_handoff_export_prepare",
        result=layer3_workbench.handoff_export_prepare(
            db,
            {
                "client_request_id": f"{request_prefix}-handoff",
                **common,
                "analysis_run_id": analysis_run_id,
                "result_review_record_ref": review_ref,
                "package_review_preview_hash": package_preview_hash,
                "construction_basis_hash": construction_basis_hash,
                "reconciliation_record_id": reconciliation_record_id,
                "package_review_submit_record_ref": submit_ref,
                "package_review_state": submit["package_review_state"],
                "package_review_submit_schema_id": submit_schema_id,
                "handoff_target": "internal_export_envelope",
                "export_mode": "prepare_only",
                "operator_decision": "authorize_prepare",
                "output_package_ids": output_package_ids,
                "payload_refs": payload_refs,
                "payload_hashes": payload_hashes,
                "expected_package_kinds": list(_PHASE_B_PACKAGE_KINDS),
            },
        ),
    )
    expected_source_shape = _PHASE_B_SOURCE_SHAPES.get(connector_key)
    handoff_envelope = handoff.get("handoff_export_envelope")
    if (
        expected_source_shape is None
        or handoff.get("handoff_export_state") != "handoff_export_prepared"
        or handoff.get("handoff_target") != "internal_export_envelope"
        or handoff.get("export_mode") != "prepare_only"
        or handoff.get("source_shape") != expected_source_shape
        or any(handoff.get(flag) is not False for flag in _PHASE_B_NO_DELIVERY_FLAGS)
        or not isinstance(handoff_envelope, Mapping)
        or handoff_envelope.get("source_shape") != expected_source_shape
        or any(
            handoff_envelope.get(flag) is not False
            for flag in _PHASE_B_NO_DELIVERY_FLAGS
        )
    ):
        _fail("dual_live_phase_b_handoff_not_prepared")
    prepare_record_ref = _owned_phase_b_required_text(
        handoff,
        "prepare_record_ref",
        "dual_live_phase_b_handoff_invalid",
    )
    envelope_ref = _owned_phase_b_required_text(
        handoff,
        "handoff_export_envelope_ref",
        "dual_live_phase_b_handoff_invalid",
    )
    source_shape = _owned_phase_b_required_text(
        handoff,
        "source_shape",
        "dual_live_phase_b_handoff_invalid",
    )
    binding = _owned_phase_b_json_mapping(
        source_binding,
        "dual_live_phase_b_source_binding_invalid",
    )
    binding.update(
        {
            "analysis_plan_id": analysis_plan_id,
            "analysis_run_id": analysis_run_id,
            "construction_basis_hash": construction_basis_hash,
            "handoff_export_envelope_ref": envelope_ref,
            "package_kinds": list(_PHASE_B_PACKAGE_KINDS),
            "package_review_preview_hash": package_preview_hash,
            "package_review_submit_record_ref": submit_ref,
            "pass_run_id": pass_run_id,
            "payload_hashes": list(payload_hashes),
            "prepare_record_ref": prepare_record_ref,
            "reconciliation_record_id": reconciliation_record_id,
            "result_review_record_ref": review_ref,
            "session_id": session_id,
            "source_shape": source_shape,
            "output_package_ids": list(output_package_ids),
        }
    )
    if binding.get("connector_key") != connector_key:
        _fail("dual_live_phase_b_source_binding_invalid")
    return binding


def _prepare_owned_phase_b(
    db: Any,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
    code_revision: str,
) -> dict[str, Any]:
    from app.services import (
        layer3_connector_source_intake,
        layer3_origin_continuity,
        layer3_workbench,
        nrc_aps_phase_b_linkage,
    )

    targets = _resolve_owned_phase_b_targets(
        db,
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
        code_revision=code_revision,
    )
    if db.rollback() is not None:
        _fail("dual_live_phase_b_database_rollback_failed")
    action_receipts: list[dict[str, str]] = []
    linkage = nrc_aps_phase_b_linkage.bind_strict_nrc_phase_b_linkage(
        db,
        connector_run_target_id=targets.nrc_target_id,
    )
    content_id = getattr(linkage, "content_id", None)
    if not isinstance(content_id, str) or not content_id.strip():
        _fail("dual_live_phase_b_nrc_linkage_invalid")
    _owned_phase_b_record_action(
        action_receipts,
        action="nrc_strict_parse",
        result={
            "connector_run_id": targets.nrc_run_id,
            "connector_run_target_id": targets.nrc_target_id,
            "content_id": content_id,
        },
    )

    origins: dict[str, dict[str, Any]] = {}
    for action, target_id in (
        ("nrc_origin_receipt", targets.nrc_target_id),
        ("sciencebase_origin_receipt", targets.sciencebase_target_id),
    ):
        with db.begin():
            projection = layer3_origin_continuity.mint_connector_origin_receipt(
                db,
                connector_run_target_id=target_id,
            )
        origin = _owned_phase_b_record_action(
            action_receipts,
            action=action,
            result=projection,
        )
        if (
            origin.get("connector_run_target_id") != target_id
            or not isinstance(origin.get("connector_origin_receipt_hash"), str)
            or _LOWERCASE_SHA256.fullmatch(
                str(origin["connector_origin_receipt_hash"])
            )
            is None
        ):
            _fail("dual_live_phase_b_origin_projection_invalid")
        origins[target_id] = origin

    nrc_prefix = f"dual-live-{campaign_id}-nrc"
    preflight = _owned_phase_b_record_action(
        action_receipts,
        action="nrc_preflight",
        result=layer3_workbench.preflight(
            {
                "client_request_id": f"{nrc_prefix}-preflight",
                "natural_language_intent": (
                    "Review the acquired NRC APS document as qualitative source material."
                ),
                "manual_constraints": {
                    "source_classes": ["aps_content_document"]
                },
            }
        ),
    )
    preflight_id = _owned_phase_b_required_text(
        preflight,
        "preflight_id",
        "dual_live_phase_b_nrc_preflight_invalid",
    )
    source = _owned_phase_b_record_action(
        action_receipts,
        action="nrc_source_preview",
        result=layer3_workbench.source_preview(
            {
                "client_request_id": f"{nrc_prefix}-source",
                "preflight_id": preflight_id,
                "selected_source_classes": ["aps_content_document"],
            }
        ),
    )
    source_set_id = _owned_phase_b_required_text(
        source,
        "source_set_id",
        "dual_live_phase_b_nrc_source_preview_invalid",
    )
    source_candidates = source.get("source_candidates")
    if (
        not isinstance(source_candidates, list)
        or len(source_candidates) != 1
        or not isinstance(source_candidates[0], Mapping)
    ):
        _fail("dual_live_phase_b_nrc_source_preview_invalid")
    source_candidate_id = _owned_phase_b_required_text(
        source_candidates[0],
        "source_candidate_id",
        "dual_live_phase_b_nrc_source_preview_invalid",
    )
    nrc_material = _owned_phase_b_record_action(
        action_receipts,
        action="nrc_material_preview",
        result=layer3_workbench.material_preview(
            {
                "client_request_id": f"{nrc_prefix}-material",
                "preflight_id": preflight_id,
                "source_set_id": source_set_id,
                "source_candidate_ids": [source_candidate_id],
                "aps_content_document_ids": [content_id],
                "query_basis": {"terms": ["dual-live-proof"]},
            },
            db,
        ),
    )
    nrc_candidates = nrc_material.get("material_candidates")
    if (
        not isinstance(nrc_candidates, list)
        or len(nrc_candidates) != 1
        or not isinstance(nrc_candidates[0], Mapping)
    ):
        _fail("dual_live_phase_b_nrc_material_preview_invalid")
    nrc_candidate = nrc_candidates[0]
    nrc_candidate_id = _owned_phase_b_required_text(
        nrc_candidate,
        "candidate_id",
        "dual_live_phase_b_nrc_material_preview_invalid",
    )
    nrc_gate_b = layer3_workbench.gate_b_decision(
        db,
        {
            "client_request_id": f"{nrc_prefix}-gate-b",
            "preflight_id": preflight_id,
            "source_set_id": source_set_id,
            "material_preview_id": nrc_material["material_preview_id"],
            "candidate_decisions": [
                {
                    "candidate_id": nrc_candidate_id,
                    "decision": "approved",
                    "operator_reason": "",
                    "decision_basis": _owned_phase_b_decision_basis(
                        nrc_candidate
                    ),
                }
            ],
            "commit_reason": "dual_live_campaign_nrc",
            "actor": "dual_live_campaign",
        },
    )
    nrc_binding = _complete_owned_phase_b_chain(
        db,
        layer3_workbench=layer3_workbench,
        connector_key="nrc_adams_aps",
        action_prefix="nrc",
        request_prefix=nrc_prefix,
        gate_b_result=nrc_gate_b,
        source_binding={
            "candidate_id": nrc_candidate_id,
            "connector_key": "nrc_adams_aps",
            "connector_origin_receipt_hash": origins[targets.nrc_target_id][
                "connector_origin_receipt_hash"
            ],
            "connector_run_id": targets.nrc_run_id,
            "connector_run_target_id": targets.nrc_target_id,
            "source_record_id": content_id,
        },
        action_receipts=action_receipts,
    )

    sciencebase_prefix = f"dual-live-{campaign_id}-sciencebase"
    sciencebase_preview = _owned_phase_b_record_action(
        action_receipts,
        action="sciencebase_material_preview",
        result=(
            layer3_connector_source_intake
            .connector_source_intake_material_preview(
                db,
                connector_source_intake_record_id=(
                    targets.sciencebase_intake_record_id
                ),
            )
        ),
    )
    sciencebase_candidate = sciencebase_preview.get("material_candidate")
    if not isinstance(sciencebase_candidate, Mapping):
        _fail("dual_live_phase_b_sciencebase_material_preview_invalid")
    sciencebase_candidate_id = _owned_phase_b_required_text(
        sciencebase_candidate,
        "candidate_id",
        "dual_live_phase_b_sciencebase_material_preview_invalid",
    )
    if (
        sciencebase_candidate.get("source_class")
        != layer3_connector_source_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS
    ):
        _fail("dual_live_phase_b_sciencebase_source_class_invalid")
    sciencebase_gate_b = layer3_workbench.gate_b_decision(
        db,
        {
            "client_request_id": f"{sciencebase_prefix}-gate-b",
            "preflight_id": f"{sciencebase_prefix}-preflight",
            "source_set_id": f"{sciencebase_prefix}-source-set",
            "material_preview_id": sciencebase_preview["material_preview_id"],
            "material_preview_hash": sciencebase_preview[
                "material_preview_hash"
            ],
            "candidate_decisions": [
                {
                    "candidate_id": sciencebase_candidate_id,
                    "decision": "approved",
                    "decision_basis": _owned_phase_b_decision_basis(
                        sciencebase_candidate
                    ),
                }
            ],
            "commit_reason": "dual_live_campaign_sciencebase",
            "actor": "dual_live_campaign",
        },
    )
    sciencebase_binding = _complete_owned_phase_b_chain(
        db,
        layer3_workbench=layer3_workbench,
        connector_key="sciencebase_mcs",
        action_prefix="sciencebase",
        request_prefix=sciencebase_prefix,
        gate_b_result=sciencebase_gate_b,
        source_binding={
            "candidate_id": sciencebase_candidate_id,
            "connector_key": "sciencebase_mcs",
            "connector_origin_receipt_hash": origins[
                targets.sciencebase_target_id
            ]["connector_origin_receipt_hash"],
            "connector_run_id": targets.sciencebase_run_id,
            "connector_run_target_id": targets.sciencebase_target_id,
            "source_record_id": targets.sciencebase_intake_record_id,
        },
        action_receipts=action_receipts,
    )
    if tuple(item["action"] for item in action_receipts) != (
        _PHASE_B_DOWNSTREAM_ACTIONS
    ):
        _fail("dual_live_phase_b_action_order_invalid")
    return {
        "action_receipts": action_receipts,
        "downstream_actions": list(_PHASE_B_DOWNSTREAM_ACTIONS),
        "source_bindings": [nrc_binding, sciencebase_binding],
        "terminal_boundary": "handoff_prepared",
    }


def run_owned_phase_b_workload() -> Mapping[str, Any]:
    """Complete both admitted internal public chains through prepared handoff."""

    campaign_id, campaign_fingerprint, code_revision = (
        _phase_b_environment_coordinates()
    )
    _assert_phase_b_connector_guards()
    from app.db import session as db_session

    db = db_session.SessionLocal()
    try:
        result = _prepare_owned_phase_b(
            db,
            campaign_id=campaign_id,
            campaign_fingerprint=campaign_fingerprint,
            code_revision=code_revision,
        )
        if result.get("terminal_boundary") != "handoff_prepared":
            _fail("dual_live_phase_b_projection_invalid")
        _assert_phase_b_connector_guards()
        return result
    finally:
        in_transaction = getattr(db, "in_transaction", lambda: True)
        if (
            in_transaction()
            and cast(Callable[[], object], db.rollback)() is not None
        ):
            _fail("dual_live_phase_b_database_rollback_failed")
        if cast(Callable[[], object], db.close)() is not None:
            _fail("dual_live_phase_b_database_close_failed")


def _resolve_staged_campaign_definition_sha256(
    settings: Any,
    campaign_id: str,
    expected_campaign_fingerprint: str,
) -> str:
    from app.schemas.api import DualLiveCampaignDefinitionV1
    from app.services import (
        connector_campaign_log_capture,
        connector_egress_authorization,
    )

    _, raw_bytes, raw_sha256 = connector_egress_authorization._read_protected_bytes(
        settings.connector_campaign_definition_path,
        expected_sha256=settings.connector_campaign_definition_sha256,
        label="current dual-live campaign definition",
        settings_override=settings,
    )
    model = connector_egress_authorization._parse_model(
        raw_bytes,
        DualLiveCampaignDefinitionV1,
        label="current dual-live campaign definition",
    )
    if (
        str(model.campaign_id) != campaign_id
        or hashlib.sha256(canonical_json_bytes(model)).hexdigest()
        != expected_campaign_fingerprint
    ):
        _fail("dual_live_producer_campaign_mismatch")
    authority = connector_campaign_log_capture._current_authority(
        campaign_id=UUID(campaign_id),
        expected_campaign_fingerprint=expected_campaign_fingerprint,
        expected_code_revision=model.code_revision,
        started_at=datetime.now(UTC),
    )
    if (
        authority.campaign_id != campaign_id
        or authority.campaign_fingerprint != expected_campaign_fingerprint
        or authority.campaign_definition_sha256 != raw_sha256
        or authority.code_revision != model.code_revision
    ):
        _fail("dual_live_producer_authority_changed")
    return raw_sha256


def _derive_reviewed_runtime_source_identity() -> tuple[str, str, str]:
    from app.services import dual_live_windows

    custody = dual_live_windows._acquire_reviewed_source_custody()
    source_error: BaseException | None = None
    values: tuple[str, str, str] | None = None
    try:
        custody.assert_stable()
        values = (
            _require_code_revision(
                custody.code_revision,
                "dual_live_source_identity_invalid",
            ),
            _require_sha256(
                custody.wrapper_image_sha256,
                "dual_live_source_identity_invalid",
            ),
            _require_sha256(
                custody.interpreter_image_sha256,
                "dual_live_source_identity_invalid",
            ),
        )
    except BaseException as exc:
        source_error = exc
    close_error: BaseException | None = None
    try:
        custody.close()
    except BaseException as exc:
        close_error = exc
    if close_error is not None:
        failure = DualLiveRuntimeError(
            "dual_live_source_identity_cleanup_failed"
        )
        close_error.__context__ = source_error
        raise failure from close_error
    if source_error is not None:
        raise source_error
    assert values is not None
    return values


def _producer_path_has_reparse_component(path: Path) -> bool:
    current = path
    for _index in range(_PRODUCER_MAX_PATH_COMPONENTS):
        metadata = os.lstat(current)
        if getattr(metadata, "st_file_attributes", 0) & 0x400:
            return True
        parent = current.parent
        if parent == current:
            return False
        current = parent
    return True


def _validate_producer_local_state(settings: Any) -> str:
    from app.core.config import _sqlite_database_path

    try:
        database_url = settings.database_url
        storage_path = Path(settings.storage_dir)
    except (AttributeError, TypeError) as exc:
        raise DualLiveRuntimeError("dual_live_producer_local_state_invalid") from exc
    if not isinstance(database_url, str) or database_url != database_url.strip():
        _fail("dual_live_producer_local_state_invalid")
    prefix = "sqlite:///"
    raw_path = database_url[len(prefix) :] if database_url.startswith(prefix) else ""
    if (
        not raw_path
        or raw_path.startswith(("file:", "//", "\\\\"))
        or "?" in database_url
        or "#" in database_url
    ):
        _fail("dual_live_producer_local_state_invalid")
    database_path = _sqlite_database_path(database_url)
    try:
        if database_path is None:
            _fail("dual_live_producer_local_state_invalid")
        resolved_database_path = database_path.resolve(strict=True)
        canonical_database_url = (
            f"sqlite:///{resolved_database_path.as_posix()}"
        )
        if (
            str(storage_path).startswith(("\\\\", "//"))
            or storage_path.drive.startswith("\\\\")
            or _producer_path_has_reparse_component(database_path)
            or _producer_path_has_reparse_component(storage_path)
        ):
            _fail("dual_live_producer_local_state_invalid")
        identity_before = _producer_database_file_identity(database_path)
        with database_path.open("rb", buffering=0) as database_file:
            header = database_file.read(16)
        identity_after = _producer_database_file_identity(database_path)
        local_state_valid = (
            database_url == canonical_database_url
            and database_path == resolved_database_path
            and database_path.is_absolute()
            and database_path.is_file()
            and identity_before == identity_after
            and identity_before[2] > 0
            and header == b"SQLite format 3\x00"
            and storage_path.is_absolute()
            and storage_path.is_dir()
        )
    except OSError:
        local_state_valid = False
    if not local_state_valid:
        _fail("dual_live_producer_local_state_invalid")
    return canonical_database_url


def _producer_database_file_identity(path: Path) -> tuple[int, int, int, int]:
    metadata = os.lstat(path)
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
    )


def _open_producer_database(settings: Any) -> tuple[Any, Any, Any]:
    database_url = _validate_producer_local_state(settings)
    from app.core.config import _sqlite_database_path
    from app.models import Base
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    database_path = _sqlite_database_path(database_url)
    if database_path is None:
        _fail("dual_live_producer_local_state_invalid")
    initial_identity = _producer_database_file_identity(database_path)
    engine = create_engine(
        database_url,
        future=True,
        connect_args={"check_same_thread": False},
    )
    connection: Any = None
    try:
        connection = engine.connect()
        connection.exec_driver_sql("PRAGMA query_only = ON")
        if tuple(connection.exec_driver_sql("PRAGMA query_only")) != ((1,),):
            _fail("dual_live_producer_local_state_invalid")
        database_list = tuple(connection.exec_driver_sql("PRAGMA database_list"))
        if (
            len(database_list) != 1
            or len(database_list[0]) != 3
            or database_list[0][1] != "main"
            or not isinstance(database_list[0][2], str)
            or Path(database_list[0][2]).resolve(strict=True) != database_path
        ):
            _fail("dual_live_producer_local_state_invalid")
        if tuple(connection.exec_driver_sql("PRAGMA quick_check(1)")) != (
            ("ok",),
        ):
            _fail("dual_live_producer_local_state_invalid")
        schema_rows = tuple(
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        )
        schema_names = frozenset(
            row[0]
            for row in schema_rows
            if len(row) == 1 and isinstance(row[0], str)
        )
        if not frozenset(Base.metadata.tables).issubset(schema_names):
            _fail("dual_live_producer_local_state_invalid")
        connection.exec_driver_sql("PRAGMA query_only = OFF")
        if tuple(connection.exec_driver_sql("PRAGMA query_only")) != ((0,),):
            _fail("dual_live_producer_local_state_invalid")
        connection.rollback()
        if connection.in_transaction():
            _fail("dual_live_producer_local_state_invalid")
        if _producer_database_file_identity(database_path) != initial_identity:
            _fail("dual_live_producer_local_state_invalid")
        db = Session(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )
    except BaseException as open_error:
        cleanup_errors: list[BaseException] = []
        for resource, method in (
            (connection, "close"),
            (engine, "dispose"),
        ):
            if resource is None:
                continue
            try:
                if getattr(resource, method)() is not None:
                    _fail("dual_live_producer_cleanup_failed")
            except BaseException as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if cleanup_errors:
            for current, following in zip(
                cleanup_errors,
                cleanup_errors[1:],
            ):
                current.__context__ = following
            cleanup_errors[-1].__context__ = open_error
            raise DualLiveRuntimeError("dual_live_producer_cleanup_failed") from (
                cleanup_errors[0]
            )
        raise
    return engine, connection, db


def _producer_result_projection(
    result: Any,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
) -> dict[str, Any]:
    try:
        manifest_sha256 = _require_sha256(
            result.manifest_sha256,
            "dual_live_producer_result_invalid",
        )
        file_set_hash = _require_sha256(
            result.file_set_hash,
            "dual_live_producer_result_invalid",
        )
        seal_sha256 = _require_sha256(
            result.seal_sha256,
            "dual_live_producer_result_invalid",
        )
        event_ids = result.event_ids
        connector_run_ids = result.seal.connector_run_ids
    except (AttributeError, TypeError) as exc:
        raise DualLiveRuntimeError("dual_live_producer_result_invalid") from exc
    if (
        type(event_ids) is not tuple
        or len(event_ids) != 2
        or type(connector_run_ids) is not tuple
        or len(connector_run_ids) != 2
        or connector_run_ids != tuple(sorted(connector_run_ids))
        or len(set(connector_run_ids)) != 2
    ):
        _fail("dual_live_producer_result_invalid")
    try:
        parsed_run_ids = tuple(UUID(run_id) for run_id in connector_run_ids)
        parsed_event_ids = tuple(UUID(event_id) for event_id in event_ids)
    except (AttributeError, TypeError, ValueError) as exc:
        raise DualLiveRuntimeError("dual_live_producer_result_invalid") from exc
    if (
        any(
            parsed.version != 5 or str(parsed) != raw
            for parsed, raw in zip(parsed_run_ids, connector_run_ids)
        )
        or any(
            parsed.version != 5 or str(parsed) != raw
            for parsed, raw in zip(parsed_event_ids, event_ids)
        )
    ):
        _fail("dual_live_producer_result_invalid")
    expected_event_ids = tuple(
        str(
            uuid5(
                NAMESPACE_URL,
                "project6:connector-egress:"
                f"{run_id}:campaign_log_capture_sealed:0",
            )
        )
        for run_id in connector_run_ids
    )
    if event_ids != expected_event_ids:
        _fail("dual_live_producer_result_invalid")
    return {
        "schema_id": DUAL_LIVE_CAMPAIGN_RUN_SCHEMA_ID,
        "campaign_id": campaign_id,
        "campaign_fingerprint": campaign_fingerprint,
        "status": "SEALED",
        "code": "dual_live_campaign_sealed",
        "manifest_sha256": manifest_sha256,
        "file_set_hash": file_set_hash,
        "seal_sha256": seal_sha256,
        "event_ids": list(event_ids),
    }


def run_dual_live_campaign(
    campaign_id: str,
    expected_campaign_fingerprint: str,
) -> dict[str, Any]:
    """Run one environment-owned campaign through canonical capture closeout."""

    canonical_campaign_id = _require_uuid4(
        campaign_id,
        "dual_live_campaign_id_invalid",
    )
    canonical_fingerprint = _require_sha256(
        expected_campaign_fingerprint,
        "dual_live_campaign_fingerprint_invalid",
    )
    try:
        from app.services.dual_live_dependencies import (
            verify_dual_live_dependencies,
        )

        dependency_set_sha256 = verify_dual_live_dependencies()
    except BaseException as exc:
        raise DualLiveRuntimeError(
            "dual_live_dependency_provenance_invalid"
        ) from exc
    settings = _load_producer_settings()
    preauthorization = _preauthorize_producer_connectors(
        settings=settings,
        campaign_id=canonical_campaign_id,
        campaign_fingerprint=canonical_fingerprint,
    )
    from app.services import dual_live_windows

    locks: Any = None
    engine: Any = None
    connection: Any = None
    db: Any = None
    run_error: BaseException | None = None
    report: dict[str, Any] | None = None
    try:
        locks = dual_live_windows.acquire_proof_locks_staged(
            Path(settings.connector_campaign_evidence_root),
            canonical_campaign_id,
            canonical_fingerprint,
            lambda: _resolve_staged_campaign_definition_sha256(
                settings,
                canonical_campaign_id,
                canonical_fingerprint,
            ),
            wait_ms=0,
        )
        engine, connection, db = _open_producer_database(settings)
        code_revision, wrapper_sha256, interpreter_sha256 = (
            _derive_reviewed_runtime_source_identity()
        )
        if code_revision != preauthorization.code_revision:
            _fail("dual_live_local_runner_authorization_changed")
        identity = RuntimeIdentity(
            runtime_instance_id=str(uuid4()),
            wrapper_nonce_sha256=secrets.token_hex(32),
            code_revision=code_revision,
            wrapper_image_sha256=wrapper_sha256,
            interpreter_image_sha256=interpreter_sha256,
            dependency_set_sha256=dependency_set_sha256,
            root_mutex_identity_sha256=locks.root_identity_sha256,
            campaign_mutex_identity_sha256=locks.campaign_identity_sha256,
        )
        runtime_start_payload = {
            "code_revision": identity.code_revision,
            "wrapper_image_sha256": identity.wrapper_image_sha256,
            "interpreter_image_sha256": identity.interpreter_image_sha256,
            "dependency_set_sha256": identity.dependency_set_sha256,
            "phase_timeout_contract": preauthorization.timeout_contract(),
            "mutex_identity_sha256": _combined_mutex_identity_sha256(identity),
        }
        context = _make_production_owned_controller_context(
            campaign_id=canonical_campaign_id,
            expected_campaign_fingerprint=canonical_fingerprint,
            db=db,
            identity=identity,
            runtime_start_payload=runtime_start_payload,
            timeout_seconds=preauthorization.phase_timeout_seconds(),
            proof_locks=locks,
        )
        # Release this frame's settings reference before Phase A. The owned
        # context clears the shared settings object's authority coordinates
        # only after the Phase-A quiescence records are durable. This is
        # semantic capability extinction, not secure memory zeroization.
        settings = None
        result = _run_production_owned_two_phase_controller(context)
        report = _producer_result_projection(
            result,
            campaign_id=canonical_campaign_id,
            campaign_fingerprint=canonical_fingerprint,
        )
    except BaseException as exc:
        run_error = exc

    cleanup_errors: list[BaseException] = []
    for resource, method in (
        (db, "close"),
        (connection, "close"),
        (engine, "dispose"),
        (locks, "close"),
    ):
        if resource is None:
            continue
        try:
            value = getattr(resource, method)()
            if value is not None:
                _fail("dual_live_producer_cleanup_failed")
        except BaseException as exc:
            cleanup_errors.append(exc)
    if cleanup_errors:
        for current, following in zip(
            cleanup_errors,
            cleanup_errors[1:],
        ):
            current.__context__ = following
        cleanup_errors[-1].__context__ = run_error
        raise DualLiveRuntimeError("dual_live_producer_cleanup_failed") from (
            cleanup_errors[0]
        )
    if run_error is not None:
        raise run_error
    assert report is not None
    return report


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


def _filter_ids(filters: Sequence[object]) -> list[str]:
    return [_type_id(filter_) for filter_ in filters]


def _call_logging_lock(name: str) -> None:
    operation = getattr(logging, name, None)
    if not callable(operation):
        _fail("dual_live_logger_manager_invalid")
    operation()


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
    _call_logging_lock("_acquireLock")
    try:
        return _census_loggers_locked(allowed_pipe_tokens)
    finally:
        _call_logging_lock("_releaseLock")


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
    _call_logging_lock("_acquireLock")
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
        _call_logging_lock("_releaseLock")

    finished = False

    def _recheck() -> dict[str, Any]:
        nonlocal finished
        _call_logging_lock("_acquireLock")
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
            _call_logging_lock("_releaseLock")

    return _recheck
