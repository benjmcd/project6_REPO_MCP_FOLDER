from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import re
import sys
import time
from collections.abc import Mapping
from ctypes import wintypes
from pathlib import Path
from typing import Callable, NoReturn, Protocol, TypedDict, cast
from uuid import UUID


_CHILD_SCHEMA_ID = "project6.dual_live_owned_child.v1"
_BOOT_SCHEMA_ID = "project6.dual_live_owned_boot.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_HANDLE_FLAG_INHERIT = 1
_WAIT_OBJECT_0 = 0
_WAIT_TIMEOUT = 0x102
_WAIT_FAILED = 0xFFFFFFFF
_COUNTER_ACK_TIMEOUT_SECONDS = 5.0
_COUNTER_ACK_POLL_MILLISECONDS = 50
_INSPECTION_REQUIRED_CODE = "dual_live_phase_timeout_inspection_required"
_PUBLIC_REFUSAL_CODES = frozenset((_INSPECTION_REQUIRED_CODE,))
_PUBLIC_PATH_ENVIRONMENT_NAMES = (
    "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
    "CONNECTOR_SCIENCEBASE_GRANT_PATH",
    "CONNECTOR_NRC_APS_GRANT_PATH",
    "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
    "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
    "DATABASE_URL",
    "STORAGE_DIR",
)
_PUBLIC_DRIVE_PATH = re.compile(r"[A-Za-z]:[\\/]")
_PUBLIC_DOS_DEVICES = frozenset(
    {"aux", "con", "nul", "prn"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
)
_PUBLIC_DRIVE_FIXED = 3
_PUBLIC_REPARSE_POINT = 0x400
_PUBLIC_INVALID_ATTRIBUTES = 0xFFFFFFFF
_WRAPPER_BLOCKED_CONNECTOR_MODULES = frozenset(
    (
        "app.services.connector_egress_transport",
        "app.services.connectors_nrc_adams",
        "app.services.connectors_sciencebase",
    )
)


class _OwnedCapsule(TypedDict):
    handles: dict[str, int]
    phase: str
    runtime_instance_id: str
    schema_id: str
    wrapper_nonce_sha256: str


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _refuse(code: str | None = None) -> int:
    output = (
        code.encode("ascii") + b"\n"
        if code in _PUBLIC_REFUSAL_CODES
        else b"dual_live_run_refused\n"
    )
    os.write(2, output)
    return 2


def _allowlisted_refusal_code(error: BaseException) -> str | None:
    code = getattr(error, "code", None)
    return code if code in _PUBLIC_REFUSAL_CODES else None


def _public_path_error() -> NoReturn:
    raise ValueError("dual_live_public_path_invalid")


def _public_local_path_text(value: str) -> tuple[str, str]:
    normalized = value.replace("/", "\\")
    folded = normalized.casefold()
    tail = normalized[3:] if len(normalized) >= 3 else ""
    components = tail.split("\\") if tail else []
    if components and components[-1] == "":
        components.pop()
    if (
        not value
        or "\x00" in value
        or any(ord(character) < 32 for character in value)
        or folded.startswith(("\\\\", "\\??\\", "\\device\\", "\\global??\\"))
        or _PUBLIC_DRIVE_PATH.match(normalized) is None
        or any(
            not component
            or component in {".", ".."}
            or component.endswith((".", " "))
            or any(character in component for character in ':*?"<>|')
            or component.split(".", 1)[0].casefold() in _PUBLIC_DOS_DEVICES
            for component in components
        )
    ):
        _public_path_error()
    return normalized, normalized[:3]


def _public_database_path(raw_url: str) -> str:
    prefix = "sqlite:///"
    if (
        not raw_url.startswith(prefix)
        or any(token in raw_url for token in ("?", "#"))
        or not raw_url[len(prefix) :]
        or raw_url[len(prefix) :] == ":memory:"
        or raw_url[len(prefix) :].startswith("file:")
    ):
        _public_path_error()
    return raw_url[len(prefix) :]


def _public_path_kernel32() -> ctypes.WinDLL:
    if os.name != "nt":
        _public_path_error()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)
    kernel32.GetDriveTypeW.restype = wintypes.UINT
    kernel32.GetFileAttributesW.argtypes = (wintypes.LPCWSTR,)
    kernel32.GetFileAttributesW.restype = wintypes.DWORD
    return kernel32


def _preflight_public_paths(environ: Mapping[str, str]) -> None:
    normalized_environment: dict[str, str] = {}
    for key, value in environ.items():
        if not isinstance(key, str) or not isinstance(value, str):
            _public_path_error()
        folded = key.casefold()
        if folded in normalized_environment:
            _public_path_error()
        normalized_environment[folded] = value

    raw_paths: list[str] = []
    for name in _PUBLIC_PATH_ENVIRONMENT_NAMES:
        configured_value = normalized_environment.get(name.casefold())
        if configured_value is None:
            _public_path_error()
        raw_paths.append(
            _public_database_path(configured_value)
            if name == "DATABASE_URL"
            else configured_value
        )
    parsed = tuple(_public_local_path_text(value) for value in raw_paths)
    kernel32 = _public_path_kernel32()
    if any(
        int(kernel32.GetDriveTypeW(drive_root)) != _PUBLIC_DRIVE_FIXED
        for _, drive_root in parsed
    ):
        _public_path_error()
    for normalized, _drive_root in parsed:
        current = normalized[:3]
        components = normalized[3:].split("\\")
        if components and components[-1] == "":
            components.pop()
        for component in (None, *components):
            if component is not None:
                current = current + component
            attributes = int(kernel32.GetFileAttributesW(current))
            if (
                attributes == _PUBLIC_INVALID_ATTRIBUTES
                or attributes & _PUBLIC_REPARSE_POINT
            ):
                _public_path_error()
            if component is not None:
                current += "\\"


def _decode_capsule(encoded: str) -> _OwnedCapsule:
    if not encoded or any(character.isspace() for character in encoded):
        raise ValueError
    padding = "=" * (-len(encoded) % 4)
    raw = base64.b64decode(
        (encoded + padding).encode("ascii"),
        altchars=b"-_",
        validate=True,
    )
    if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != encoded:
        raise ValueError
    decoded: object = json.loads(raw.decode("utf-8"))
    if type(decoded) is not dict or _canonical_json_bytes(decoded) != raw:
        raise ValueError
    value = cast(dict[str, object], decoded)
    if tuple(value) != (
        "handles",
        "phase",
        "runtime_instance_id",
        "schema_id",
        "wrapper_nonce_sha256",
    ):
        raise ValueError
    if value["schema_id"] != _CHILD_SCHEMA_ID or value["phase"] not in {"A", "B"}:
        raise ValueError
    runtime_id = value["runtime_instance_id"]
    if not isinstance(runtime_id, str):
        raise ValueError
    parsed = UUID(runtime_id)
    if parsed.version != 4 or str(parsed) != runtime_id:
        raise ValueError
    wrapper_nonce = value["wrapper_nonce_sha256"]
    if not isinstance(wrapper_nonce, str) or _SHA256.fullmatch(wrapper_nonce) is None:
        raise ValueError
    decoded_handles = value["handles"]
    if type(decoded_handles) is not dict:
        raise ValueError
    handles = cast(dict[str, object], decoded_handles)
    pipe_roles = (
        "child_app_write_handle",
        "child_control_read_handle",
        "child_http_write_handle",
        "child_stderr_write_handle",
        "child_stdout_write_handle",
    )
    stdio_roles = (
        "child_stdio_stderr_write_handle",
        "child_stdio_stdin_read_handle",
        "child_stdio_stdout_write_handle",
    )
    event_roles = (
        "child_counter_ack_event_handle",
        "child_revocation_event_handle",
        "child_send_idle_event_handle",
    )
    expected_roles = tuple(
        sorted(pipe_roles + stdio_roles + (event_roles if value["phase"] == "A" else ()))
    )
    if tuple(handles) != expected_roles:
        raise ValueError
    values = tuple(handles.values())
    if any(isinstance(handle, bool) or not isinstance(handle, int) or handle <= 0 for handle in values):
        raise ValueError
    if len(set(values)) != len(values):
        raise ValueError
    return cast(_OwnedCapsule, value)


def _clear_inheritance(handles: dict[str, int]) -> ctypes.WinDLL:
    if os.name != "nt":
        raise OSError
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetHandleInformation.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.GetHandleInformation.restype = wintypes.BOOL
    kernel32.SetHandleInformation.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    kernel32.SetHandleInformation.restype = wintypes.BOOL
    for handle in handles.values():
        flags = wintypes.DWORD()
        if (
            not kernel32.GetHandleInformation(handle, ctypes.byref(flags))
            or flags.value & _HANDLE_FLAG_INHERIT == 0
        ):
            raise OSError
        if not kernel32.SetHandleInformation(handle, _HANDLE_FLAG_INHERIT, 0):
            raise OSError
    for handle in handles.values():
        flags = wintypes.DWORD()
        if (
            not kernel32.GetHandleInformation(handle, ctypes.byref(flags))
            or flags.value & _HANDLE_FLAG_INHERIT
        ):
            raise OSError
    return kernel32


class _NativeWriter:
    __slots__ = ("_kernel32", "_value")

    def __init__(self, kernel32: ctypes.WinDLL, value: int) -> None:
        self._kernel32 = kernel32
        self._value = value

    def write(self, content: bytes) -> int:
        if not isinstance(content, bytes) or not content:
            raise OSError
        buffer = ctypes.create_string_buffer(content)
        written = wintypes.DWORD()
        if not self._kernel32.WriteFile(
            self._value,
            buffer,
            len(content),
            ctypes.byref(written),
            None,
        ) or written.value != len(content):
            raise OSError
        return int(written.value)


class _RuntimeModule(Protocol):
    CampaignPipeSink: Callable[[str, _NativeWriter], object]
    CampaignPipeHandler: Callable[[str, object], object]

    def census_loggers(self, pipe_tokens: frozenset[str]) -> dict[str, object]: ...

    def encode_child_status_frame(
        self,
        *,
        phase: str,
        event: str,
        process_boot_id: str,
        status_nonce_sha256: str,
        ordinal: int,
        payload: dict[str, object],
    ) -> bytes: ...

    def encode_pipe_frame(self, payload: bytes) -> bytes: ...

    def encode_child_proof_frame(
        self,
        *,
        phase: str,
        event: str,
        process_boot_id: str,
        status_nonce_sha256: str,
        ordinal: int,
        previous_record_sha256: str | None,
        payload: Mapping[str, object],
    ) -> bytes: ...

    def freeze_logger_topology(
        self,
        pipe_tokens: frozenset[str],
    ) -> Callable[[], dict[str, object]]: ...

    def run_owned_phase_a_workload(
        self,
        *,
        runtime_instance_id: str,
        process_boot_id: str,
        append_counter_frame: Callable[[bytes], None],
        revocation_is_set: Callable[[], bool],
        acquire_send_idle: Callable[[], None],
        release_send_idle: Callable[[], None],
    ) -> Mapping[str, object]: ...

    def run_owned_phase_b_workload(self) -> Mapping[str, object]: ...

    def _install_phase_b_connector_guards(self) -> None: ...

    def _preload_owned_workload_modules(self) -> None: ...

    def exercise_owned_phase_b_connector_guard(self) -> None: ...


def _read_exact(kernel32: ctypes.WinDLL, handle: int, size: int) -> bytes:
    result = bytearray()
    while len(result) < size:
        buffer = ctypes.create_string_buffer(size - len(result))
        received = wintypes.DWORD()
        if not kernel32.ReadFile(
            handle,
            buffer,
            len(buffer),
            ctypes.byref(received),
            None,
        ) or received.value == 0:
            raise OSError
        result.extend(buffer.raw[: received.value])
    return bytes(result)


def _read_control(kernel32: ctypes.WinDLL, handle: int) -> bytes:
    size = int.from_bytes(_read_exact(kernel32, handle, 4), "big")
    if size <= 0 or size > 4096:
        raise ValueError
    return _read_exact(kernel32, handle, size)


def _validate_go(payload: bytes, *, phase: str, control_nonce: str) -> None:
    value = json.loads(payload.decode("utf-8"))
    if (
        type(value) is not dict
        or _canonical_json_bytes(value) != payload
        or tuple(value) != ("command", "control_nonce", "phase", "schema_id")
        or value["schema_id"] != "project6.dual_live_child_control.v1"
        or value["command"] != "GO"
        or value["phase"] != phase
        or value["control_nonce"] != control_nonce
    ):
        raise ValueError


def _configure_logger_topology(
    runtime: _RuntimeModule,
    app_writer: _NativeWriter,
    pipe_token: str,
) -> tuple[Callable[[], dict[str, object]], dict[str, object]]:
    import logging

    root = logging.root
    root.handlers.clear()
    root.filters.clear()
    root.disabled = False
    root.setLevel(logging.INFO)
    root.propagate = True
    sink = runtime.CampaignPipeSink(pipe_token, app_writer)
    handler = cast(
        logging.Handler,
        runtime.CampaignPipeHandler(pipe_token, sink),
    )
    root.addHandler(handler)
    for value in logging.Logger.manager.loggerDict.values():
        if isinstance(value, logging.Logger):
            value.handlers.clear()
            value.filters.clear()
            value.addHandler(logging.NullHandler())
            value.propagate = False
            value.disabled = False
    logging.lastResort = None
    recheck = runtime.freeze_logger_topology(frozenset((pipe_token,)))
    return recheck, runtime.census_loggers(frozenset((pipe_token,)))


def _emit_status(
    runtime: _RuntimeModule,
    writer: _NativeWriter,
    *,
    phase: str,
    process_boot_id: str,
    status_nonce_sha256: str,
    ordinal: int,
    point: str,
    census: dict[str, object],
) -> str:
    frame = runtime.encode_child_status_frame(
        phase=phase,
        event="logger_census",
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce_sha256,
        ordinal=ordinal,
        payload={
            "census_point": point,
            "handler_count": census["handler_count"],
            "topology_sha256": census["topology_sha256"],
        },
    )
    writer.write(frame)
    return hashlib.sha256(frame).hexdigest()


class _DenyGuard:
    """Subclass-safe permanent denial for late standard-library imports."""

    def __new__(cls, *args: object, **kwargs: object) -> NoReturn:
        del cls, args, kwargs
        raise PermissionError("dual_live_inert_guard")


_deny_guard = _DenyGuard


class _StandardLibraryGuards:
    __slots__ = (
        "_entries",
        "_guard",
        "_installed",
        "_network_enable_attempt_count",
        "_network_state",
        "_network_entries",
        "_original_implementation_call_count",
        "_phase",
        "_subprocess_entries",
    )

    def __init__(self, phase: str) -> None:
        import http.client
        import requests  # type: ignore[import-untyped]
        import socket
        import subprocess
        import urllib.request

        if phase not in {"A", "B", "wrapper"}:
            raise ValueError("dual_live_inert_guard_phase_invalid")
        self._phase = phase
        self._network_entries = (
            (socket, "socket", socket.socket),
            (socket, "create_connection", socket.create_connection),
            (socket, "getaddrinfo", socket.getaddrinfo),
            (socket, "gethostbyname", socket.gethostbyname),
            (socket, "gethostbyname_ex", socket.gethostbyname_ex),
            (socket, "getnameinfo", socket.getnameinfo),
            (http.client.HTTPConnection, "request", http.client.HTTPConnection.request),
            (urllib.request, "urlopen", urllib.request.urlopen),
            (requests, "request", requests.request),
            (requests.sessions.Session, "request", requests.sessions.Session.request),
        )
        self._subprocess_entries = (
            (subprocess, "Popen", subprocess.Popen),
            (subprocess, "run", subprocess.run),
            (subprocess, "check_call", subprocess.check_call),
            (subprocess, "check_output", subprocess.check_output),
        )
        self._entries = self._network_entries + self._subprocess_entries
        self._guard = _deny_guard
        self._installed = False
        self._network_state = "uninstalled"
        self._network_enable_attempt_count = 0
        self._original_implementation_call_count = 0

    def install(self) -> None:
        if self._phase == "wrapper":
            if self._network_state != "denied" or any(
                getattr(target, name) is not self._guard
                for target, name, _original in self._network_entries
            ):
                raise RuntimeError("dual_live_inert_guard_changed")
            if any(
                getattr(target, name) is not original
                for target, name, original in self._subprocess_entries
            ):
                raise RuntimeError("dual_live_inert_guard_changed")
        previously_enabled = self._network_state == "phase_a_enabled"
        for target, name, _original in self._entries:
            setattr(target, name, self._guard)
        self._installed = True
        self._network_state = "sealed" if previously_enabled else "denied"
        self.assert_intact()

    def install_wrapper_network_denial(self) -> None:
        if (
            self._phase != "wrapper"
            or self._installed
            or self._network_state != "uninstalled"
            or any(
                getattr(target, name) is not original
                for target, name, original in self._subprocess_entries
            )
        ):
            raise RuntimeError("dual_live_inert_guard_changed")
        for target, name, _original in self._network_entries:
            setattr(target, name, self._guard)
        self._network_state = "denied"
        if any(
            getattr(target, name) is not self._guard
            for target, name, _original in self._network_entries
        ):
            raise RuntimeError("dual_live_inert_guard_changed")

    def restore(self) -> None:
        raise RuntimeError("dual_live_inert_guard_permanent")

    def enable_phase_a_transport(self) -> None:
        self.assert_intact()
        self._network_enable_attempt_count += 1
        if self._phase != "A" or self._network_state != "denied":
            raise PermissionError("dual_live_inert_guard_enable_denied")
        for target, name, original in self._network_entries:
            setattr(target, name, original)
        self._network_state = "phase_a_enabled"
        self.assert_intact()

    def assert_intact(self) -> None:
        if not self._installed:
            raise RuntimeError("dual_live_inert_guard_changed")
        if self._phase in {"B", "wrapper"} and self._network_enable_attempt_count:
            raise RuntimeError("dual_live_inert_guard_enable_attempted")
        if self._network_state == "phase_a_enabled":
            expected = tuple(self._network_entries) + tuple(
                (target, name, self._guard)
                for target, name, _original in self._subprocess_entries
            )
        elif self._network_state in {"denied", "sealed"}:
            expected = tuple(
                (target, name, self._guard)
                for target, name, _original in self._entries
            )
        else:
            raise RuntimeError("dual_live_inert_guard_changed")
        if any(getattr(target, name) is not value for target, name, value in expected):
            raise RuntimeError("dual_live_inert_guard_changed")

    def exercise(
        self,
        *,
        connector_probe: Callable[[], None] | None = None,
    ) -> dict[str, object]:
        import socket
        import subprocess
        import requests

        self.assert_intact()
        if self._network_state == "phase_a_enabled":
            raise RuntimeError("dual_live_inert_guard_wrong_mode")
        probes = (
            ("dns", socket.getaddrinfo, ("localhost", 80)),
            ("http", requests.request, ("GET", "https://example.invalid")),
            ("socket", socket.socket, ()),
            ("subprocess", subprocess.run, ((sys.executable, "-c", "pass"),)),
        )
        denied: list[str] = []
        for route, callback, arguments in probes:
            try:
                callback(*arguments)
            except PermissionError:
                denied.append(route)
            else:
                raise RuntimeError("dual_live_inert_guard_failed")
        if connector_probe is not None:
            if connector_probe() is not None:
                raise RuntimeError("dual_live_inert_guard_failed")
            denied.append("connector_transport")
        self.assert_intact()
        return {
            "denied_routes": denied,
            "network_enable_attempt_count": self._network_enable_attempt_count,
            "original_implementation_call_count": (
                self._original_implementation_call_count
            ),
        }


def _phase_a_guard_window(
    kernel32: ctypes.WinDLL,
    guards: _StandardLibraryGuards,
    *,
    idle: int,
    revoked: int,
) -> int:
    if not kernel32.ResetEvent(idle):
        raise OSError
    try:
        wait_result = int(kernel32.WaitForSingleObject(revoked, 0))
        if wait_result == _WAIT_OBJECT_0:
            return 23
        if wait_result == _WAIT_TIMEOUT:
            return 0
        raise OSError
    finally:
        if not kernel32.SetEvent(idle):
            raise OSError


def _event_is_set(kernel32: ctypes.WinDLL, handle: int) -> bool:
    wait_result = int(kernel32.WaitForSingleObject(handle, 0))
    if wait_result == _WAIT_OBJECT_0:
        return True
    if wait_result == _WAIT_TIMEOUT:
        return False
    raise OSError


def _dispatch_owned_workload(
    runtime: _RuntimeModule,
    guards: _StandardLibraryGuards,
    kernel32: ctypes.WinDLL,
    *,
    phase: str,
    handles: dict[str, int],
    runtime_instance_id: str,
    process_boot_id: str,
) -> tuple[int, Mapping[str, object]]:
    if phase == "B":
        guards.assert_intact()
        projection = runtime.run_owned_phase_b_workload()
        guards.assert_intact()
        if (
            not isinstance(projection, Mapping)
            or projection.get("terminal_boundary") != "handoff_prepared"
        ):
            raise RuntimeError("dual_live_phase_b_projection_invalid")
        return 0, dict(projection)
    if phase != "A":
        raise ValueError("dual_live_owned_phase_invalid")

    revoked_handle = handles["child_revocation_event_handle"]
    idle_handle = handles["child_send_idle_event_handle"]
    ack_handle = handles["child_counter_ack_event_handle"]
    http_writer = _NativeWriter(kernel32, handles["child_http_write_handle"])
    if _event_is_set(kernel32, revoked_handle):
        return 23, {"connector_acquisitions": [], "downstream_action_count": 0}

    def revocation_is_set() -> bool:
        return _event_is_set(kernel32, revoked_handle)

    def acquire_send_idle() -> None:
        if not kernel32.ResetEvent(idle_handle):
            raise OSError
        try:
            if revocation_is_set():
                raise PermissionError("dual_live_owned_phase_a_revoked")
        except BaseException:
            if not kernel32.SetEvent(idle_handle):
                raise OSError
            raise

    def release_send_idle() -> None:
        if not kernel32.SetEvent(idle_handle):
            raise OSError

    def append_counter_frame(payload: bytes) -> None:
        if revocation_is_set():
            raise PermissionError("dual_live_owned_phase_a_revoked")
        if not kernel32.ResetEvent(ack_handle):
            raise OSError
        if revocation_is_set():
            raise PermissionError("dual_live_owned_phase_a_revoked")
        framed = runtime.encode_pipe_frame(payload)
        if http_writer.write(framed) != len(framed):
            raise OSError
        deadline = time.monotonic() + _COUNTER_ACK_TIMEOUT_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("dual_live_owned_counter_ack_timeout")
            wait_ms = min(
                _COUNTER_ACK_POLL_MILLISECONDS,
                max(1, int(remaining * 1000)),
            )
            wait_result = int(kernel32.WaitForSingleObject(ack_handle, wait_ms))
            if wait_result == _WAIT_OBJECT_0:
                return
            if wait_result != _WAIT_TIMEOUT:
                raise OSError
            if revocation_is_set():
                raise PermissionError("dual_live_owned_phase_a_revoked")

    guards.enable_phase_a_transport()
    try:
        projection = runtime.run_owned_phase_a_workload(
            runtime_instance_id=runtime_instance_id,
            process_boot_id=process_boot_id,
            append_counter_frame=append_counter_frame,
            revocation_is_set=revocation_is_set,
            acquire_send_idle=acquire_send_idle,
            release_send_idle=release_send_idle,
        )
    finally:
        guards.install()
    if not isinstance(projection, Mapping):
        raise RuntimeError("dual_live_phase_a_projection_invalid")
    return 0, dict(projection)


def _run_owned_child(capsule: _OwnedCapsule, kernel32: ctypes.WinDLL) -> int:
    if any(name == "app" or name.startswith("app.") for name in sys.modules):
        raise RuntimeError
    phase = str(capsule["phase"])
    workload_coordinates = (
        os.environ.get("DUAL_LIVE_CAMPAIGN_ID"),
        os.environ.get("DUAL_LIVE_CAMPAIGN_FINGERPRINT"),
        os.environ.get("DUAL_LIVE_CODE_REVISION"),
        os.environ.get("DUAL_LIVE_DEPENDENCY_SET_SHA256"),
    )
    real_workload = all(value is not None for value in workload_coordinates)
    if not real_workload and any(
        value is not None for value in workload_coordinates
    ):
        raise RuntimeError("dual_live_owned_workload_environment_partial")
    import asyncio  # noqa: F401
    import http.client  # noqa: F401
    import ssl  # noqa: F401
    import urllib.request  # noqa: F401
    import warnings

    if not real_workload:
        with warnings.catch_warnings(record=True) as preload_warnings:
            warnings.simplefilter("always")
            import requests  # type: ignore[import-untyped]  # noqa: F401
        if any(
            warning.category
            is not requests.exceptions.RequestsDependencyWarning
            for warning in preload_warnings
        ):
            raise RuntimeError("dual_live_preload_warning_unexpected")
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            import requests  # type: ignore[import-untyped]  # noqa: F401

    guards = _StandardLibraryGuards(phase)
    guards.install()
    backend = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend))
    dependency_digest: str | None = None
    if real_workload:
        from app.services.dual_live_dependencies import (
            verify_dual_live_dependencies,
        )

        dependency_digest = verify_dual_live_dependencies()
        if dependency_digest != workload_coordinates[3]:
            raise RuntimeError("dual_live_dependency_provenance_invalid")
    from app.services import dual_live_runtime
    from app.services import dual_live_windows as windows

    runtime = cast(_RuntimeModule, dual_live_runtime)
    if real_workload and verify_dual_live_dependencies() != dependency_digest:
        raise RuntimeError("dual_live_dependency_provenance_invalid")
    guards.assert_intact()

    kernel32.ReadFile.argtypes = (
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    )
    kernel32.ReadFile.restype = wintypes.BOOL
    kernel32.WriteFile.argtypes = (
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    )
    kernel32.WriteFile.restype = wintypes.BOOL
    kernel32.SetEvent.argtypes = (wintypes.HANDLE,)
    kernel32.SetEvent.restype = wintypes.BOOL
    kernel32.ResetEvent.argtypes = (wintypes.HANDLE,)
    kernel32.ResetEvent.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.argtypes = ()
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE

    handles = capsule["handles"]
    assert isinstance(handles, dict)
    app_writer = _NativeWriter(kernel32, handles["child_app_write_handle"])
    stdout_writer = _NativeWriter(kernel32, handles["child_stdout_write_handle"])
    current_process = int(kernel32.GetCurrentProcess())
    executable_sha256 = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
    creation_filetime = windows._process_creation_filetime(
        current_process,
        refusal_code="dual_live_process_identity_indeterminate",
    )
    _, process_boot_id = windows._derive_process_boot_identity(
        pid=os.getpid(),
        creation_filetime=creation_filetime,
        executable_sha256=executable_sha256,
        runtime_instance_id=capsule["runtime_instance_id"],
        wrapper_nonce_sha256=capsule["wrapper_nonce_sha256"],
    )
    status_nonce = windows._owned_domain_nonce(
        "status",
        process_boot_id=process_boot_id,
        wrapper_nonce_sha256=capsule["wrapper_nonce_sha256"],
    )
    control_nonce = windows._owned_domain_nonce(
        "control",
        process_boot_id=process_boot_id,
        wrapper_nonce_sha256=capsule["wrapper_nonce_sha256"],
    )
    boot = _canonical_json_bytes(
        {
            "control_nonce": control_nonce,
            "phase": phase,
            "process_boot_id": process_boot_id,
            "schema_id": _BOOT_SCHEMA_ID,
            "status_nonce_sha256": status_nonce,
        }
    )
    boot_frame = runtime.encode_pipe_frame(boot)
    app_writer.write(boot_frame)
    boot_frame_sha256 = hashlib.sha256(boot_frame).hexdigest()
    runtime._preload_owned_workload_modules()
    if phase == "B":
        runtime._install_phase_b_connector_guards()
    guards.assert_intact()

    recheck, census = _configure_logger_topology(
        runtime,
        app_writer,
        f"app:{status_nonce[:32]}",
    )
    pre_activity_status_frame_sha256 = _emit_status(
        runtime,
        app_writer,
        phase=phase,
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce,
        ordinal=1,
        point="pre_activity",
        census=census,
    )
    proof_scope = "production" if real_workload else "mechanical"
    control_nonce_sha256 = hashlib.sha256(control_nonce.encode("ascii")).hexdigest()
    previous_proof_record_sha256: str | None = None

    def emit_proof(event: str, ordinal: int, payload: Mapping[str, object]) -> None:
        nonlocal previous_proof_record_sha256
        frame = runtime.encode_child_proof_frame(
            phase=phase,
            event=event,
            process_boot_id=process_boot_id,
            status_nonce_sha256=status_nonce,
            ordinal=ordinal,
            previous_record_sha256=previous_proof_record_sha256,
            payload=payload,
        )
        if stdout_writer.write(frame) != len(frame):
            raise OSError
        size = int.from_bytes(frame[:4], "big")
        record = json.loads(frame[4:].decode("utf-8"))
        record_sha256 = record.get("record_sha256") if isinstance(record, dict) else None
        if size != len(frame) - 4 or not isinstance(record_sha256, str) or _SHA256.fullmatch(record_sha256) is None:
            raise RuntimeError("dual_live_child_proof_encoding_invalid")
        previous_proof_record_sha256 = record_sha256

    guard_common = {
        "boot_frame_sha256": boot_frame_sha256,
        "control_nonce_sha256": control_nonce_sha256,
        "pre_activity_status_frame_sha256": pre_activity_status_frame_sha256,
        "proof_scope": proof_scope,
    }
    if phase == "B":
        pre_go_guard = guards.exercise(
            connector_probe=runtime.exercise_owned_phase_b_connector_guard,
        )
        emit_proof(
            "guard",
            1,
            {
                **guard_common,
                **pre_go_guard,
                "proof_point": "pre_go",
            },
        )
    control = _read_control(kernel32, handles["child_control_read_handle"])
    _validate_go(control, phase=phase, control_nonce=control_nonce)
    control_frame_sha256 = hashlib.sha256(
        len(control).to_bytes(4, "big") + control
    ).hexdigest()
    guards.assert_intact()

    if real_workload:
        exit_code, workload_projection = _dispatch_owned_workload(
            runtime,
            guards,
            kernel32,
            phase=phase,
            handles=handles,
            runtime_instance_id=capsule["runtime_instance_id"],
            process_boot_id=process_boot_id,
        )
    else:
        # Compatibility-only mechanical child proof; the public producer always
        # supplies all four coordinates and therefore cannot enter this lane.
        exit_code = 0
        if phase == "A":
            exit_code = _phase_a_guard_window(
                kernel32,
                guards,
                idle=handles["child_send_idle_event_handle"],
                revoked=handles["child_revocation_event_handle"],
            )
            workload_projection = {
                "connector_acquisitions": [],
                "downstream_action_count": 0,
            }
        else:
            workload_projection = {
                "downstream_actions": [],
                "source_bindings": [],
                "terminal_boundary": "mechanical_complete",
            }

    exit_census = recheck()
    guards.assert_intact()
    exit_status_frame_sha256 = _emit_status(
        runtime,
        app_writer,
        phase=phase,
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce,
        ordinal=2,
        point="exit",
        census=exit_census,
    )
    terminal_common = {
        **guard_common,
        "control_frame_sha256": control_frame_sha256,
        "exit_status_frame_sha256": exit_status_frame_sha256,
    }
    if phase == "A":
        guards.exercise()
        emit_proof(
            "acquisition_boundary",
            1,
            {
                **terminal_common,
                **workload_projection,
            },
        )
    else:
        emit_proof(
            "downstream_chain",
            2,
            {
                **terminal_common,
                **workload_projection,
            },
        )
        exit_guard = guards.exercise(
            connector_probe=runtime.exercise_owned_phase_b_connector_guard,
        )
        emit_proof(
            "guard",
            3,
            {
                **terminal_common,
                **exit_guard,
                "proof_point": "exit",
            },
        )
    for role, handle in handles.items():
        if role.startswith("child_stdio_"):
            continue
        if not kernel32.CloseHandle(handle):
            raise OSError
    return exit_code


def _parse_public_arguments(arguments: tuple[str, ...]) -> tuple[str, str] | None:
    if (
        len(arguments) != 4
        or arguments[0] != "--campaign-id"
        or arguments[2] != "--campaign-fingerprint"
    ):
        return None
    campaign_id = arguments[1]
    campaign_fingerprint = arguments[3]
    if (
        not campaign_id
        or not campaign_fingerprint
        or any(character.isspace() for character in campaign_id)
        or any(character.isspace() for character in campaign_fingerprint)
    ):
        return None
    return campaign_id, campaign_fingerprint


class _WrapperConnectorImportGuard:
    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> None:
        del path, target
        if fullname in _WRAPPER_BLOCKED_CONNECTOR_MODULES:
            raise ImportError("dual_live_wrapper_connector_import_denied")
        return None


def _install_wrapper_connector_import_guard() -> _WrapperConnectorImportGuard:
    if any(name in sys.modules for name in _WRAPPER_BLOCKED_CONNECTOR_MODULES):
        raise RuntimeError("dual_live_wrapper_connector_import_preloaded")
    guard = _WrapperConnectorImportGuard()
    sys.meta_path.insert(0, guard)
    return guard


def _assert_wrapper_backend_not_preloaded() -> None:
    if any(
        name in sys.modules
        for name in (
            "app.services.dual_live_runtime",
            "app.services.dual_live_windows",
        )
    ):
        raise RuntimeError("dual_live_wrapper_backend_import_preloaded")


def _run_public_mode(
    arguments: tuple[str, ...],
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    parsed = _parse_public_arguments(arguments)
    if parsed is None:
        return _refuse()
    campaign_id, campaign_fingerprint = parsed
    _preflight_public_paths(os.environ if environ is None else environ)
    guards = _StandardLibraryGuards("wrapper")
    guards.install_wrapper_network_denial()
    _install_wrapper_connector_import_guard()
    backend = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend))
    _assert_wrapper_backend_not_preloaded()
    from app.services import dual_live_windows

    guards.install()
    dual_live_windows._register_subprocess_gate_baseline(guards._guard)
    guards.assert_intact()
    from app.services.dual_live_runtime import run_dual_live_campaign

    guards.assert_intact()
    result = run_dual_live_campaign(campaign_id, campaign_fingerprint)
    guards.assert_intact()
    output = _canonical_json_bytes(result) + b"\n"
    if os.write(1, output) != len(output):
        raise OSError
    return 0


def main() -> int:
    try:
        if sys.flags.isolated != 1 or not sys.dont_write_bytecode:
            return _refuse()
        arguments = tuple(sys.argv[1:])
        if len(arguments) == 2 and arguments[0] == "--owned-child":
            if sys.pycache_prefix != "NUL":
                return _refuse()
            capsule = _decode_capsule(arguments[1])
            handles = capsule["handles"]
            assert isinstance(handles, dict)
            kernel32 = _clear_inheritance(handles)
            return _run_owned_child(capsule, kernel32)
        if sys.pycache_prefix is None:
            sys.pycache_prefix = "NUL"
        if sys.pycache_prefix != "NUL":
            return _refuse()
        return _run_public_mode(arguments)
    except BaseException as exc:
        return _refuse(_allowlisted_refusal_code(exc))


if __name__ == "__main__":
    raise SystemExit(main())
