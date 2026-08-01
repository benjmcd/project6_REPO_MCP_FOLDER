from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import re
import sys
from ctypes import wintypes
from pathlib import Path
from typing import Callable, Protocol, TypedDict, cast
from uuid import UUID


_CHILD_SCHEMA_ID = "project6.dual_live_owned_child.v1"
_BOOT_SCHEMA_ID = "project6.dual_live_owned_boot.v1"
_GUARD_SCHEMA_ID = "project6.dual_live_inert_guard.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_HANDLE_FLAG_INHERIT = 1
_WAIT_OBJECT_0 = 0
_WAIT_TIMEOUT = 0x102
_WAIT_FAILED = 0xFFFFFFFF


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


def _refuse() -> int:
    os.write(2, b"dual_live_run_refused\n")
    return 2


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

    def freeze_logger_topology(
        self,
        pipe_tokens: frozenset[str],
    ) -> Callable[[], dict[str, object]]: ...


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
) -> None:
    writer.write(
        runtime.encode_child_status_frame(
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
    )


def _deny_guard(*args: object, **kwargs: object) -> None:
    del args, kwargs
    raise PermissionError("dual_live_inert_guard")


class _StandardLibraryGuards:
    __slots__ = ("_entries", "_guard", "_installed")

    def __init__(self) -> None:
        import http.client
        import requests  # type: ignore[import-untyped]
        import socket
        import subprocess
        import urllib.request

        self._entries = (
            (socket, "socket", socket.socket),
            (socket, "create_connection", socket.create_connection),
            (socket, "getaddrinfo", socket.getaddrinfo),
            (socket, "gethostbyname", socket.gethostbyname),
            (socket, "gethostbyname_ex", socket.gethostbyname_ex),
            (socket, "getnameinfo", socket.getnameinfo),
            (http.client.HTTPConnection, "request", http.client.HTTPConnection.request),
            (urllib.request, "urlopen", urllib.request.urlopen),
            (subprocess, "Popen", subprocess.Popen),
            (subprocess, "run", subprocess.run),
            (subprocess, "check_call", subprocess.check_call),
            (subprocess, "check_output", subprocess.check_output),
            (requests, "request", requests.request),
            (requests.sessions.Session, "request", requests.sessions.Session.request),
        )
        self._guard = _deny_guard
        self._installed = False

    def install(self) -> None:
        for target, name, _original in self._entries:
            setattr(target, name, self._guard)
        self._installed = True
        self.assert_intact()

    def restore(self) -> None:
        self.assert_intact()
        for target, name, original in self._entries:
            setattr(target, name, original)
        self._installed = False

    def assert_intact(self) -> None:
        if not self._installed or any(
            getattr(target, name) is not self._guard
            for target, name, _original in self._entries
        ):
            raise RuntimeError("dual_live_inert_guard_changed")

    def exercise(self) -> list[str]:
        import socket
        import subprocess
        import requests

        self.assert_intact()
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
        self.assert_intact()
        return denied


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
            guards.restore()
            guards.install()
            return 0
        raise OSError
    finally:
        if not kernel32.SetEvent(idle):
            raise OSError


def _run_owned_child(capsule: _OwnedCapsule, kernel32: ctypes.WinDLL) -> int:
    if any(name == "app" or name.startswith("app.") for name in sys.modules):
        raise RuntimeError
    import asyncio  # noqa: F401
    import http.client  # noqa: F401
    import ssl  # noqa: F401
    import urllib.request  # noqa: F401
    import warnings

    with warnings.catch_warnings(record=True) as preload_warnings:
        warnings.simplefilter("always")
        import requests  # type: ignore[import-untyped]  # noqa: F401
    if any(
        warning.category is not requests.exceptions.RequestsDependencyWarning
        for warning in preload_warnings
    ):
        raise RuntimeError("dual_live_preload_warning_unexpected")

    guards = _StandardLibraryGuards()
    guards.install()
    backend = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend))
    from app.services import dual_live_runtime
    from app.services import dual_live_windows as windows

    runtime = cast(_RuntimeModule, dual_live_runtime)

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

    phase = str(capsule["phase"])
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
    app_writer.write(runtime.encode_pipe_frame(boot))

    recheck, census = _configure_logger_topology(
        runtime,
        app_writer,
        f"app:{status_nonce[:32]}",
    )
    _emit_status(
        runtime,
        app_writer,
        phase=phase,
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce,
        ordinal=1,
        point="pre_activity",
        census=census,
    )
    control = _read_control(kernel32, handles["child_control_read_handle"])
    _validate_go(control, phase=phase, control_nonce=control_nonce)
    guards.assert_intact()

    exit_code = 0
    if phase == "A":
        exit_code = _phase_a_guard_window(
            kernel32,
            guards,
            idle=handles["child_send_idle_event_handle"],
            revoked=handles["child_revocation_event_handle"],
        )
    denied = guards.exercise()
    guard = _canonical_json_bytes(
        {
            "denied_routes": denied,
            "guard_state": "selected_standard_routes",
            "http_call_count": 0,
            "phase": phase,
            "schema_id": _GUARD_SCHEMA_ID,
        }
    )
    stdout_writer.write(runtime.encode_pipe_frame(guard))

    exit_census = recheck()
    guards.assert_intact()
    _emit_status(
        runtime,
        app_writer,
        phase=phase,
        process_boot_id=process_boot_id,
        status_nonce_sha256=status_nonce,
        ordinal=2,
        point="exit",
        census=exit_census,
    )
    for role, handle in handles.items():
        if role.startswith("child_stdio_"):
            continue
        if not kernel32.CloseHandle(handle):
            raise OSError
    return exit_code


def main() -> int:
    try:
        if (
            len(sys.argv) != 3
            or sys.argv[1] != "--owned-child"
            or sys.flags.isolated != 1
            or not sys.dont_write_bytecode
            or sys.pycache_prefix != "NUL"
        ):
            return _refuse()
        capsule = _decode_capsule(sys.argv[2])
        handles = capsule["handles"]
        assert isinstance(handles, dict)
        kernel32 = _clear_inheritance(handles)
        return _run_owned_child(capsule, kernel32)
    except BaseException:
        return _refuse()


if __name__ == "__main__":
    raise SystemExit(main())
