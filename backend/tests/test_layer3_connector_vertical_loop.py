from __future__ import annotations

# ruff: noqa: E402

import copy
import hashlib
import importlib
import inspect
import json
import os
import secrets
import socket
import sqlite3
import stat
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Iterator, Literal, get_type_hints


def _sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix) or database_url == "sqlite:///:memory:":
        raise AssertionError("B1a requires one file-backed SQLite database")
    return Path(database_url[len(prefix) :]).resolve()


_AMBIENT_WRITE_ENV = (
    "LAYER3_EXTERNAL_LOCAL_EXPORT_DIR",
    "LAYER3_CANDIDATE_B_BUNDLE_BRIDGE_DIR",
    "LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR",
    "LAYER3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR",
    "LAYER3_SOURCE_INGESTION_DIR",
)


def _emit_initialization_stop_receipt(exc: BaseException, last_step: str) -> None:
    local_temp_root = Path(tempfile.gettempdir()).resolve()
    worktree_root = Path(__file__).resolve().parents[2]
    onedrive_root = Path(os.environ.get("OneDrive", Path.home() / "OneDrive")).resolve()
    raw_run_root = os.environ.get("B1A_RUN_ROOT")
    raw_evidence_dir = os.environ.get("B1A_EVIDENCE_DIR")
    evidence_dir: Path | None = None
    disposition = "OS-TEMP-FALLBACK"
    if raw_run_root and raw_evidence_dir:
        try:
            candidate_run_root = Path(raw_run_root).resolve()
            candidate_evidence_dir = Path(raw_evidence_dir).resolve()
            if (
                candidate_run_root.is_relative_to(local_temp_root)
                and not candidate_run_root.is_relative_to(worktree_root)
                and not candidate_run_root.is_relative_to(onedrive_root)
                and candidate_evidence_dir == candidate_run_root / "evidence"
            ):
                evidence_dir = candidate_evidence_dir
                disposition = "CONFIGURED-EVIDENCE-DIR"
        except (OSError, RuntimeError, ValueError):
            evidence_dir = None
    if evidence_dir is None:
        evidence_dir = Path(tempfile.mkdtemp(prefix="project6-b1a-stop-")).resolve()
    try:
        evidence_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        evidence_dir = Path(tempfile.mkdtemp(prefix="project6-b1a-stop-")).resolve()
        disposition = "OS-TEMP-FALLBACK"
    path = evidence_dir / "stop-receipt.json"
    payload = {
        "condition": "INITIAL-CONFIGURATION-OR-PATH-SAFETY-FAILURE",
        "measured_facts": {
            "exception_class": type(exc).__name__,
            "exception_message": str(exc),
            "configured_run_root": raw_run_root,
            "configured_evidence_dir": raw_evidence_dir,
            "receipt_disposition": disposition,
            "receipt_path": str(path),
        },
        "last_completed_step": last_step,
        "row_count_snapshot": {},
        "zero_further_mutation_assertion": True,
        "run_id": globals().get(
            "_RUN_ID", os.environ.get("B1A_RUN_ID", "PREIMPORT-CONFIGURATION")
        ),
        "run_nonce": globals().get("_RUN_NONCE", secrets.token_hex(16)),
        "producer_node": "module-import",
        "status": "STOP",
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"B1A_STOP_RECEIPT={path}", file=sys.stderr)


# The external B2 wrapper may set these first.  The fallbacks keep the tracked
# Tier-1 authoring proof hermetic without claiming that the B2 wrapper ran.
try:
    _CONFIGURED_RUN_ROOT = os.environ.get("B1A_RUN_ROOT")
    _DEV_RUN_ROOT = (
        Path(_CONFIGURED_RUN_ROOT).resolve()
        if _CONFIGURED_RUN_ROOT
        else Path(tempfile.mkdtemp(prefix="project6-b1a-authoring-")).resolve()
    )
    _RUN_ID = os.environ.get("B1A_RUN_ID", _DEV_RUN_ROOT.name)
    _RUN_NONCE = secrets.token_hex(16)
    _DISTRIBUTED_COLLECTION = (
        bool(os.environ.get("PYTEST_XDIST_WORKER"))
        or int(os.environ.get("PYTEST_SHARD_TOTAL", "1")) > 1
    )
    if _CONFIGURED_RUN_ROOT and _DISTRIBUTED_COLLECTION:
        raise AssertionError("the B2 runtime forbids xdist and manual pytest sharding")
    _DESIRED_DB_INIT_MODE = "create_all" if _CONFIGURED_RUN_ROOT else "none"
    if _CONFIGURED_RUN_ROOT and os.environ.get("DB_INIT_MODE") != "create_all":
        raise AssertionError("the B2 wrapper must set DB_INIT_MODE=create_all")
    _DESIRED_DATABASE_URL = (
        os.environ.get("DATABASE_URL")
        if _CONFIGURED_RUN_ROOT
        else f"sqlite:///{(_DEV_RUN_ROOT / 'b1.sqlite3').as_posix()}"
    )
    _DESIRED_STORAGE_DIR = (
        os.environ.get("STORAGE_DIR")
        if _CONFIGURED_RUN_ROOT
        else str(_DEV_RUN_ROOT / "storage")
    )
    _DESIRED_EVIDENCE_DIR = (
        os.environ.get("B1A_EVIDENCE_DIR")
        if _CONFIGURED_RUN_ROOT
        else str(_DEV_RUN_ROOT / "evidence")
    )
    if not all((_DESIRED_DATABASE_URL, _DESIRED_STORAGE_DIR, _DESIRED_EVIDENCE_DIR)):
        raise AssertionError(
            "B1A_RUN_ROOT requires DATABASE_URL, STORAGE_DIR, and B1A_EVIDENCE_DIR"
        )

    _DESIRED_DATABASE_PATH = _sqlite_path(str(_DESIRED_DATABASE_URL))
    _DESIRED_STORAGE_PATH = Path(str(_DESIRED_STORAGE_DIR)).resolve()
    _DESIRED_EVIDENCE_PATH = Path(str(_DESIRED_EVIDENCE_DIR)).resolve()
    _WORKTREE_ROOT = Path(__file__).resolve().parents[2]
    _ONEDRIVE_ROOT = Path(
        os.environ.get("OneDrive", Path.home() / "OneDrive")
    ).resolve()
    _LOCAL_TEMP_ROOT = Path(tempfile.gettempdir()).resolve()
    if not _DEV_RUN_ROOT.is_relative_to(_LOCAL_TEMP_ROOT):
        raise AssertionError("RUN_ROOT must be contained by the OS local temp root")
    if _DEV_RUN_ROOT.is_relative_to(_WORKTREE_ROOT):
        raise AssertionError("RUN_ROOT must be outside the focused worktree")
    if _DEV_RUN_ROOT.is_relative_to(_ONEDRIVE_ROOT):
        raise AssertionError("RUN_ROOT must be outside OneDrive")
    if _DESIRED_DATABASE_PATH != _DEV_RUN_ROOT / "b1.sqlite3":
        raise AssertionError("DATABASE_URL must resolve exactly to RUN_ROOT/b1.sqlite3")
    if _DESIRED_STORAGE_PATH != _DEV_RUN_ROOT / "storage":
        raise AssertionError("STORAGE_DIR must resolve exactly to RUN_ROOT/storage")
    if _DESIRED_EVIDENCE_PATH != _DEV_RUN_ROOT / "evidence":
        raise AssertionError(
            "B1A_EVIDENCE_DIR must resolve exactly to RUN_ROOT/evidence"
        )
    for runtime_path in (
        _DESIRED_DATABASE_PATH,
        _DESIRED_STORAGE_PATH,
        _DESIRED_EVIDENCE_PATH,
    ):
        if not runtime_path.is_relative_to(_DEV_RUN_ROOT):
            raise AssertionError(f"runtime path escapes RUN_ROOT: {runtime_path}")

    _DESIRED_AMBIENT_WRITE_TARGETS = {
        name: (os.environ.get(name) or None) if _CONFIGURED_RUN_ROOT else None
        for name in _AMBIENT_WRITE_ENV
    }
    for name, value in _DESIRED_AMBIENT_WRITE_TARGETS.items():
        if value is not None and not Path(value).resolve().is_relative_to(
            _DEV_RUN_ROOT
        ):
            raise AssertionError(f"{name} escapes RUN_ROOT")

    _RUNTIME_ENV = {
        "DB_INIT_MODE": _DESIRED_DB_INIT_MODE,
        "DATABASE_URL": str(_DESIRED_DATABASE_URL),
        "STORAGE_DIR": str(_DESIRED_STORAGE_PATH),
        **{name: value or "" for name, value in _DESIRED_AMBIENT_WRITE_TARGETS.items()},
    }
    _PRIOR_IMPORT_ENV = {name: os.environ.get(name) for name in _RUNTIME_ENV}
    os.environ.update(_RUNTIME_ENV)
except BaseException as _configuration_error:
    _emit_initialization_stop_receipt(
        _configuration_error, "INITIAL-CONFIGURATION-AND-PATH-RAILS"
    )
    raise

AUTHORITY_SHA = "2b7973d72e65661acc30c3ec88791fe1c88061e0"
FIXTURE_BYTES = b"site_id,value\nSB-001,42\nSB-002,43\n"
FIXTURE_SHA256 = "d4eb55501d9003c9c769fa3dbd5d92c9b68a7c42f8be493a17b1e6ec42eca3ad"
FIXTURE_SOURCE_FILE_GIT_BLOB = "b8a89df28ed1ed5adfd8ded7ee12d28863cf0ed2"
FIXTURE_PAYLOAD_GIT_BLOB = "9c748de955a84cf3da7282d87d352017f423be20"
C6_DEGENERATE_N_RAIL = (
    "the 2-row/1-numeric-column fixture proves seam wiring and provenance ONLY; "
    "mean/SD are trivial arithmetic and never evidence of analytical capability"
)
FIXED_TERMINAL_STATEMENT = "B1B-BLOCKED-ON-OWNER; INTEGRATED-LOOP-NOT-PROVEN"
SOCKET_GUARD_SOURCE = """from __future__ import annotations

import json
import os
import socket
import threading
import time

B1A_SOCKET_GUARD_ID = os.environ["B1A_RUN_ID"]
B1A_ATTEMPT_LEDGER = os.environ["B1A_NETWORK_ATTEMPT_LEDGER"]
_B1A_LEDGER_LOCK = threading.Lock()
_B1A_REAL_CONNECT = socket.socket.connect
_B1A_REAL_CONNECT_EX = socket.socket.connect_ex
_B1A_REAL_CREATE_CONNECTION = socket.create_connection
_B1A_AF_INET = socket.AF_INET
_B1A_AF_INET6 = socket.AF_INET6
_B1A_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _b1a_is_loopback(
    api: str, address: object, socket_family: object
) -> bool:
    if api not in {
        "socket.connect",
        "socket.connect_ex",
        "socket.create_connection",
    }:
        return False
    if type(address) is not tuple or len(address) not in {2, 4}:
        return False
    if api == "socket.create_connection" and len(address) != 2:
        return False
    host, port = address[:2]
    if (
        type(host) is not str
        or not host.isascii()
        or host.lower() not in _B1A_LOOPBACK_HOSTS
        or type(port) is not int
        or not 0 <= port <= 65535
    ):
        return False
    normalized_host = host.lower()
    if api != "socket.create_connection":
        if normalized_host == "localhost":
            if socket_family not in {_B1A_AF_INET, _B1A_AF_INET6}:
                return False
        else:
            expected_family = (
                _B1A_AF_INET6 if normalized_host == "::1" else _B1A_AF_INET
            )
            if socket_family != expected_family:
                return False
    if normalized_host != "::1":
        return len(address) == 2
    if len(address) == 2:
        return True
    flowinfo, scope_id = address[2:]
    return (
        type(flowinfo) is int
        and 0 <= flowinfo <= 0xFFFFF
        and type(scope_id) is int
        and 0 <= scope_id <= 0xFFFFFFFF
    )


def _b1a_forward_address(address: object, socket_family: object) -> object:
    assert type(address) is tuple
    host = address[0]
    if type(host) is str and host.isascii() and host.lower() == "localhost":
        forwarded_host = "::1" if socket_family == _B1A_AF_INET6 else "127.0.0.1"
        return (forwarded_host, *address[1:])
    return address


def _b1a_create_connection_source(
    args: tuple[object, ...], kwargs: dict[str, object]
) -> tuple[bool, object]:
    if len(args) > 2 or (len(args) == 2 and "source_address" in kwargs):
        return False, None
    if len(args) == 2:
        return True, args[1]
    return True, kwargs.get("source_address")


def _b1a_forward_create_connection_source(
    args: tuple[object, ...],
    kwargs: dict[str, object],
    forwarded_source_address: object,
) -> tuple[tuple[object, ...], dict[str, object]]:
    if forwarded_source_address is None:
        return args, kwargs
    if len(args) == 2:
        return (args[0], forwarded_source_address), kwargs
    if "source_address" in kwargs:
        forwarded_kwargs = dict(kwargs)
        forwarded_kwargs["source_address"] = forwarded_source_address
        return args, forwarded_kwargs
    return args, kwargs


def _b1a_record_attempt(
    api: str,
    address: object,
    socket_family: object,
    *,
    source_address: object = None,
    source_family: object = None,
    source_shape_valid: bool = True,
) -> tuple[bool, object, object]:
    destination_is_loopback = _b1a_is_loopback(api, address, socket_family)
    source_is_loopback = source_shape_valid and (
        source_address is None
        or _b1a_is_loopback("socket.connect", source_address, source_family)
    )
    is_loopback = destination_is_loopback and source_is_loopback
    forwarded_address = (
        _b1a_forward_address(address, socket_family)
        if destination_is_loopback
        else address
    )
    forwarded_source_address = (
        _b1a_forward_address(source_address, source_family)
        if source_address is not None and source_is_loopback
        else source_address
    )
    record = {
        "api": api,
        "address_repr": repr(address),
        "forwarded_address_repr": repr(forwarded_address),
        "source_address_repr": repr(source_address),
        "forwarded_source_address_repr": repr(forwarded_source_address),
        "is_loopback": is_loopback,
        "run_id": B1A_SOCKET_GUARD_ID,
        "time_ns": time.time_ns(),
    }
    with _B1A_LEDGER_LOCK:
        with open(B1A_ATTEMPT_LEDGER, "a", encoding="utf-8", newline="\\n") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\\n")
            handle.flush()
            os.fsync(handle.fileno())
    return is_loopback, forwarded_address, forwarded_source_address


def _b1a_connect(_socket: socket.socket, address: object) -> None:
    is_loopback, forwarded_address, _ = _b1a_record_attempt(
        "socket.connect", address, _socket.family
    )
    if not is_loopback:
        raise OSError("OFFLINE-ONLY: outbound socket attempt denied")
    return _B1A_REAL_CONNECT(_socket, forwarded_address)


def _b1a_connect_ex(_socket: socket.socket, address: object) -> int:
    is_loopback, forwarded_address, _ = _b1a_record_attempt(
        "socket.connect_ex", address, _socket.family
    )
    if not is_loopback:
        raise OSError("OFFLINE-ONLY: outbound socket attempt denied")
    return _B1A_REAL_CONNECT_EX(_socket, forwarded_address)


def _b1a_create_connection(address: object, *args: object, **kwargs: object) -> socket.socket:
    source_shape_valid, source_address = _b1a_create_connection_source(args, kwargs)
    target_family = (
        _B1A_AF_INET6
        if type(address) is tuple
        and len(address) > 0
        and type(address[0]) is str
        and address[0].isascii()
        and address[0].lower() == "::1"
        else _B1A_AF_INET
    )
    is_loopback, forwarded_address, forwarded_source_address = _b1a_record_attempt(
        "socket.create_connection",
        address,
        None,
        source_address=source_address,
        source_family=target_family,
        source_shape_valid=source_shape_valid,
    )
    if not is_loopback:
        raise OSError("OFFLINE-ONLY: outbound socket attempt denied")
    forwarded_args, forwarded_kwargs = _b1a_forward_create_connection_source(
        args, kwargs, forwarded_source_address
    )
    return _B1A_REAL_CREATE_CONNECTION(
        forwarded_address, *forwarded_args, **forwarded_kwargs
    )


assert _b1a_is_loopback("socket.connect", ("127.0.0.1", 1), _B1A_AF_INET)
assert _b1a_is_loopback("socket.connect_ex", ("::1", 1, 0, 0), _B1A_AF_INET6)
assert _b1a_is_loopback("socket.connect_ex", ("localhost", 1), _B1A_AF_INET6)
assert _b1a_is_loopback("socket.create_connection", ("localhost", 1), None)
assert _b1a_is_loopback("socket.create_connection", ("LOCALHOST", 1), None)
assert not _b1a_is_loopback("socket.connect", ("127.0.0.1", 1), _B1A_AF_INET6)
assert not _b1a_is_loopback("socket.connect", ("::1", 1), _B1A_AF_INET)
assert not _b1a_is_loopback("socket.connect", ("127.0.0.2", 1), _B1A_AF_INET)
assert not _b1a_is_loopback("socket.connect", ("10.0.0.1", 1), _B1A_AF_INET)
assert not _b1a_is_loopback("socket.connect", ("localhoſt", 1), _B1A_AF_INET)
assert not _b1a_is_loopback("socket.connect", ("localhost",), _B1A_AF_INET)
assert not _b1a_is_loopback(
    "socket.connect_ex", ("127.0.0.1", "not-a-port"), _B1A_AF_INET
)
assert not _b1a_is_loopback(
    "socket.connect_ex", ("::1", 1, "not-flowinfo", 0), _B1A_AF_INET6
)
assert not _b1a_is_loopback(
    "socket.create_connection", ("::1", 1, 0, 0), None
)
assert not _b1a_is_loopback(
    "socket.connect_ex", ("::1", 1, 0, 1 << 100), _B1A_AF_INET6
)
assert not _b1a_is_loopback(
    "socket.connect", "local-domain-socket", _B1A_AF_INET
)
assert not _b1a_is_loopback("unknown", ("127.0.0.1", 1), _B1A_AF_INET)
assert _b1a_forward_address(("localhost", 1), None) == ("127.0.0.1", 1)
assert _b1a_forward_address(("localhost", 1), _B1A_AF_INET6) == ("::1", 1)
assert _b1a_forward_address(("::1", 1), _B1A_AF_INET6) == ("::1", 1)


for _guarded in (_b1a_connect, _b1a_connect_ex, _b1a_create_connection):
    _guarded.__b1a_socket_guard_id__ = B1A_SOCKET_GUARD_ID
    _guarded.__b1a_attempt_ledger__ = B1A_ATTEMPT_LEDGER

socket.socket.connect = _b1a_connect
socket.socket.connect_ex = _b1a_connect_ex
socket.create_connection = _b1a_create_connection

assert socket.socket.connect is _b1a_connect
assert socket.socket.connect_ex is _b1a_connect_ex
assert socket.create_connection is _b1a_create_connection
"""
SOCKET_GUARD_BYTES = SOCKET_GUARD_SOURCE.encode("utf-8")
SOCKET_GUARD_SHA256 = hashlib.sha256(SOCKET_GUARD_BYTES).hexdigest()
compile(SOCKET_GUARD_SOURCE, "sitecustomize.py", "exec")

EXPECTED_SEALS: dict[str, tuple[int, str]] = {
    "child_manifest": (
        4_184,
        "f56cad4693468a5163b6fae30fb3d2ae12044a3014cda608c451c2b0d82b66b4",
    ),
    "freeze_manifest": (
        19_437,
        "6cd70a58c04f2cf672e4171f1a767b9aea8bd88b1268dce9d09e3ef88201a188",
    ),
    "freeze_aggregate": (
        5_819,
        "25fb67a447ac441f5f50856bc1638db87547a119df2c91f9b91e6631b7a6ee1b",
    ),
    "fixture": (34, FIXTURE_SHA256),
    "packet": (
        52_631,
        "1d0201668a9a4976b2d30267386fe4fcb23413ec717b82ca356eb0db7919370e",
    ),
    "owner_record": (
        9_063,
        "534cd5a70825c88b3f722754bb0e6dffb52626c5bb3da4c32e33fe5afb24ca9f",
    ),
    "ct3_table": (
        22_297,
        "fdfd2ba785801c015eb68f3c311d80b3caf002444f8dee46c1f79ab887e38fa2",
    ),
}

B2_RECEIPT_NAMES = (
    "authority-seals.json",
    "b2-storage-preflight.json",
    "process-census-before.json",
    "network-deny.json",
    "durability-disposition.json",
)
EXPECTED_B2_CHECKS_BY_RECEIPT = {
    "authority-seals.json": {},
    "b2-storage-preflight.json": {
        **{f"B2-{index:02d}": "PASS" for index in range(1, 8)},
        "B2-04b": "PASS",
        "B2-11": "PASS",
    },
    "process-census-before.json": {
        "B2-08": "PASS",
        "B2-09": "PASS",
        "B2-12": "PASS",
        "B2-13": "PASS",
        "B2-14": "PASS",
        "B2-15": "ARMED",
        "B2-15b": "ARMED",
    },
    "network-deny.json": {"B2-10": "PASS"},
    "durability-disposition.json": {"B2-16": "PASS-TO-LAUNCH"},
}


def _assert_utc(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AssertionError(f"{field} must be a UTC timestamp ending in Z")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise AssertionError(f"{field} must resolve to UTC")


def _query_live_process_identity(pid: int) -> dict[str, Any]:
    if os.name != "nt":
        raise AssertionError("the configured B2 monitor identity probe is Windows-only")

    import ctypes
    from ctypes import wintypes

    process_query_limited_information = 0x1000
    synchronize = 0x00100000
    wait_timeout = 0x00000102
    process_basic_information = 0
    process_command_line_information = 60

    class FileTime(ctypes.Structure):
        _fields_ = (
            ("low", wintypes.DWORD),
            ("high", wintypes.DWORD),
        )

    class ProcessBasicInformation(ctypes.Structure):
        _fields_ = (
            ("reserved1", ctypes.c_void_p),
            ("peb_base_address", ctypes.c_void_p),
            ("reserved2", ctypes.c_void_p * 2),
            ("unique_process_id", ctypes.c_void_p),
            ("inherited_from_unique_process_id", ctypes.c_void_p),
        )

    class UnicodeString(ctypes.Structure):
        _fields_ = (
            ("length", wintypes.USHORT),
            ("maximum_length", wintypes.USHORT),
            ("buffer", ctypes.c_void_p),
        )

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    open_process.restype = wintypes.HANDLE
    wait_for_single_object = kernel32.WaitForSingleObject
    wait_for_single_object.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    wait_for_single_object.restype = wintypes.DWORD
    query_full_process_image_name = kernel32.QueryFullProcessImageNameW
    query_full_process_image_name.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    query_full_process_image_name.restype = wintypes.BOOL
    get_process_times = kernel32.GetProcessTimes
    get_process_times.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
    )
    get_process_times.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL

    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    nt_query_information_process = ntdll.NtQueryInformationProcess
    nt_query_information_process.argtypes = (
        wintypes.HANDLE,
        wintypes.ULONG,
        ctypes.c_void_p,
        wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG),
    )
    nt_query_information_process.restype = wintypes.LONG

    handle = open_process(
        process_query_limited_information | synchronize,
        False,
        pid,
    )
    if not handle:
        error = ctypes.get_last_error()
        raise AssertionError(
            f"B2-15 monitor PID cannot be queried non-destructively: {error}"
        )
    try:
        if wait_for_single_object(handle, 0) != wait_timeout:
            raise AssertionError("B2-15 receipted monitor PID is not live")

        image_size = wintypes.DWORD(32_768)
        image_buffer = ctypes.create_unicode_buffer(image_size.value)
        if not query_full_process_image_name(
            handle, 0, image_buffer, ctypes.byref(image_size)
        ):
            error = ctypes.get_last_error()
            raise AssertionError(f"B2-15 monitor executable cannot be queried: {error}")

        creation_time = FileTime()
        exit_time = FileTime()
        kernel_time = FileTime()
        user_time = FileTime()
        if not get_process_times(
            handle,
            ctypes.byref(creation_time),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            error = ctypes.get_last_error()
            raise AssertionError(
                f"B2-15 monitor creation time cannot be queried: {error}"
            )

        basic_information = ProcessBasicInformation()
        returned_length = wintypes.ULONG()
        status = nt_query_information_process(
            handle,
            process_basic_information,
            ctypes.byref(basic_information),
            ctypes.sizeof(basic_information),
            ctypes.byref(returned_length),
        )
        if status != 0:
            raise AssertionError(
                f"B2-15 monitor parent PID cannot be queried: NTSTATUS={status}"
            )

        command_length = wintypes.ULONG()
        nt_query_information_process(
            handle,
            process_command_line_information,
            None,
            0,
            ctypes.byref(command_length),
        )
        if command_length.value <= ctypes.sizeof(UnicodeString):
            raise AssertionError("B2-15 monitor command-line length is unavailable")
        command_buffer = ctypes.create_string_buffer(command_length.value)
        status = nt_query_information_process(
            handle,
            process_command_line_information,
            command_buffer,
            command_length.value,
            ctypes.byref(command_length),
        )
        if status != 0:
            raise AssertionError(
                f"B2-15 monitor command line cannot be queried: NTSTATUS={status}"
            )
        command_record = ctypes.cast(
            command_buffer, ctypes.POINTER(UnicodeString)
        ).contents
        command_line = ctypes.wstring_at(
            command_record.buffer,
            command_record.length // ctypes.sizeof(ctypes.c_wchar),
        )
        return {
            "pid": pid,
            "parent_pid": int(basic_information.inherited_from_unique_process_id or 0),
            "executable": image_buffer.value,
            "command_line": command_line,
            "creation_time_filetime": ((creation_time.high << 32) | creation_time.low),
        }
    finally:
        close_handle(handle)


def _canonical_json_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _early_external_seal_rehash() -> dict[str, dict[str, Any]] | None:
    configured_root = os.environ.get("B1A_CHAIN_ROOT")
    root = Path(configured_root).resolve() if configured_root else None
    if root is None:
        for parent in Path(__file__).resolve().parents:
            if (
                parent.name == "worktrees"
                and parent.parent.name == "project6_REPO_MCP_FOLDER"
            ):
                root = parent.parent
                break
    if root is None:
        return None
    paths = {
        "child_manifest": root
        / "worktrees/manifest-children/ct4b-fixture-child-manifest.json",
        "freeze_manifest": root / "worktrees/freeze-v1/manifest-v1.json",
        "freeze_aggregate": root / "worktrees/freeze-v1/aggregate-rows.txt",
        "fixture": Path(
            os.environ.get(
                "B1A_FIXTURE_PATH",
                "C:/p6fixtures/sciencebase-v1/water-quality.csv",
            )
        ),
        "packet": root / "state/agent-inbox/b1-vertical-loop-packet.md",
        "owner_record": root / "state/agent-inbox/owner-decision-record-2026-07-10.md",
        "ct3_table": root / "state/agent-inbox/ct3-semantics-table.md",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise AssertionError(f"STOP #6: sealed instrument missing: {missing}")
    freeze_names = sorted(
        path.name for path in paths["freeze_manifest"].parent.iterdir()
    )
    if freeze_names != ["aggregate-rows.txt", "manifest-v1.json"]:
        raise AssertionError(f"STOP #6: freeze-v1 census drifted: {freeze_names}")
    receipts: dict[str, dict[str, Any]] = {}
    for name, path in paths.items():
        payload = path.read_bytes()
        receipt = {
            "path": str(path),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        if (receipt["bytes"], receipt["sha256"]) != EXPECTED_SEALS[name]:
            raise AssertionError(f"STOP #6: {name} seal drifted: {receipt}")
        receipts[name] = receipt
    return receipts


def _load_and_validate_b2_receipts() -> dict[str, dict[str, Any]] | None:
    if not _CONFIGURED_RUN_ROOT:
        return None
    receipt_dir = _DESIRED_EVIDENCE_PATH
    if not receipt_dir.is_relative_to(_DEV_RUN_ROOT):
        raise AssertionError("B1A_EVIDENCE_DIR must be contained by B1A_RUN_ROOT")
    paths = {name: receipt_dir / name for name in B2_RECEIPT_NAMES}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise AssertionError(f"B2 receipt set incomplete before app import: {missing}")
    receipts = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in paths.items()
    }
    if not all(isinstance(receipt, dict) for receipt in receipts.values()):
        raise AssertionError("B2 receipt files must contain JSON objects")

    for name, receipt in receipts.items():
        if receipt.get("run_id") != _RUN_ID:
            raise AssertionError(f"{name} does not bind run_id={_RUN_ID}")
        _assert_utc(receipt.get("utc"), f"{name}.utc")
        if receipt.get("checks") != EXPECTED_B2_CHECKS_BY_RECEIPT[name]:
            raise AssertionError(f"{name} check ownership/status map is not exact")

    authority = receipts["authority-seals.json"]
    expected_seal_objects = {
        name: {"bytes": size, "sha256": digest}
        for name, (size, digest) in EXPECTED_SEALS.items()
    }
    if authority.get("status") != "PASS":
        raise AssertionError("authority-seals.json status must equal PASS")
    if authority.get("authority_sha") != AUTHORITY_SHA:
        raise AssertionError("authority-seals.json must bind the audited Git SHA")
    if authority.get("seals") != expected_seal_objects:
        raise AssertionError("authority-seals.json seal map is not exact")
    if (
        not isinstance(authority.get("commands"), list)
        or not authority["commands"]
        or not all(
            isinstance(command, str) and command.strip()
            for command in authority["commands"]
        )
    ):
        raise AssertionError("authority-seals.json must retain executed commands")
    if (
        not isinstance(authority.get("raw_outputs"), dict)
        or not authority["raw_outputs"]
    ):
        raise AssertionError("authority-seals.json must retain raw command outputs")

    storage = receipts["b2-storage-preflight.json"]
    expected_paths = {
        "storage": str(_DESIRED_STORAGE_PATH),
        "raw": str(_DESIRED_STORAGE_PATH / "raw"),
        "artifacts": str(_DESIRED_STORAGE_PATH / "artifacts"),
        "datasets": str(_DESIRED_STORAGE_PATH / "datasets"),
        "connector_raw": str(_DESIRED_STORAGE_PATH / "connectors/raw"),
        "layer3_outbox": str(_DESIRED_STORAGE_PATH / "layer3-outbox"),
    }
    expected_storage_fields = {
        "status": "PASS",
        "run_root": str(_DEV_RUN_ROOT),
        "storage_dir": str(_DESIRED_STORAGE_PATH),
        "database_url": str(_DESIRED_DATABASE_URL),
        "database_path": str(_DESIRED_DATABASE_PATH),
        "evidence_dir": str(_DESIRED_EVIDENCE_PATH),
        "db_init_mode": _DESIRED_DB_INIT_MODE,
        "paths": expected_paths,
        "ambient_write_targets": _DESIRED_AMBIENT_WRITE_TARGETS,
        "outside_repo": True,
        "outside_onedrive": True,
        "local_temp_root": str(_LOCAL_TEMP_ROOT),
        "under_local_temp": True,
        "no_reparse_ancestors": True,
        "empty_at_start": True,
        "database_absent_or_zero_at_start": True,
        "config_probe_only": True,
    }
    for key, expected in expected_storage_fields.items():
        if storage.get(key) != expected:
            raise AssertionError(f"b2-storage-preflight.json {key} is not exact")
    if _DESIRED_DATABASE_PATH.exists() and (
        not _DESIRED_DATABASE_PATH.is_file()
        or _DESIRED_DATABASE_PATH.stat().st_size != 0
    ):
        raise AssertionError(
            "B2-07 database must still be absent or zero bytes before app import"
        )
    storage_commands = storage.get("commands")
    if (
        not isinstance(storage_commands, list)
        or not storage_commands
        or not all(
            isinstance(command, str) and command.strip() for command in storage_commands
        )
    ):
        raise AssertionError("B2-11 must retain its executed command list")
    raw_path_outputs = storage.get("raw_path_outputs")
    if not isinstance(raw_path_outputs, dict) or not raw_path_outputs:
        raise AssertionError("B2-11 must retain raw path/config-probe outputs")
    ancestors = storage.get("ancestor_inventory")
    if not isinstance(ancestors, list) or not ancestors:
        raise AssertionError("B2-06 must retain the ancestor inventory")
    for ancestor in ancestors:
        if (
            not isinstance(ancestor, dict)
            or not {
                "path",
                "exists",
                "is_reparse_point",
            }
            <= ancestor.keys()
        ):
            raise AssertionError("B2-06 ancestor rows lack raw path facts")
        if ancestor["is_reparse_point"] is not False:
            raise AssertionError("B2-06 ancestor inventory contains a reparse point")
    if storage.get("initial_inventory") != []:
        raise AssertionError("B2-07 initial run-root inventory must be exactly empty")
    write_inventory = storage.get("write_inventory_before_app_import")
    if not isinstance(write_inventory, list) or not write_inventory:
        raise AssertionError("B2-11 must retain the pre-import write inventory")
    resolved_write_inventory: list[str] = []
    for raw_path in write_inventory:
        if not isinstance(raw_path, str) or not raw_path:
            raise AssertionError("B2-11 write inventory rows must be path strings")
        path = Path(str(raw_path)).resolve()
        if not path.is_relative_to(_DEV_RUN_ROOT):
            raise AssertionError(f"B2-11 write inventory escapes RUN_ROOT: {path}")
        if raw_path != str(path):
            raise AssertionError("B2-11 write inventory paths must be canonical")
        resolved_write_inventory.append(str(path))
    if len(resolved_write_inventory) != len(set(resolved_write_inventory)):
        raise AssertionError("B2-11 write inventory contains duplicate paths")
    live_write_inventory = sorted(
        str(path.resolve()) for path in _DEV_RUN_ROOT.rglob("*") if path.is_file()
    )
    if sorted(resolved_write_inventory) != live_write_inventory:
        raise AssertionError(
            "B2-11 write inventory does not equal the live pre-import file census"
        )
    config_probe = storage.get("config_probe")
    expected_config_probe = {
        "status": "PASS",
        "imports": ["app.core.config"],
        "database_url": str(_DESIRED_DATABASE_URL),
        "storage_dir": str(_DESIRED_STORAGE_PATH),
        "paths": expected_paths,
        "non_evidence_writes": [],
    }
    if config_probe != expected_config_probe:
        raise AssertionError("B2-11 configuration-only probe receipt is not exact")

    process = receipts["process-census-before.json"]
    if process.get("status") != "PASS":
        raise AssertionError("process-census-before.json status must equal PASS")
    if process.get("pytest_workers") != 1 or process.get("sqlite_engines") != 1:
        raise AssertionError("B2 process census must bind one worker and one engine")
    if process.get("xdist") is not False or process.get("uvicorn") is not False:
        raise AssertionError("B2 process census must exclude xdist and uvicorn")
    if process.get("prelaunch_free_bytes", 0) < 4_294_967_296:
        raise AssertionError("B2 prelaunch memory floor was not met")
    if process.get("rss_ceiling_bytes") != 2_147_483_648:
        raise AssertionError("B2 RSS ceiling is not exact")
    if process.get("midrun_free_floor_bytes") != 1_073_741_824:
        raise AssertionError("B2-15b memory floor is not exact")
    if process.get("wall_ceiling_seconds") != 900:
        raise AssertionError("B2 wall ceiling is not exact")
    if process.get("monitor_interval_seconds") != 1:
        raise AssertionError("B2 monitor cadence is not exact")
    if process.get("name_agnostic_top_n") is not True:
        raise AssertionError("B2-14 must use a name-agnostic top-N census")
    if process.get("exclusive_run_root_lock") is not True:
        raise AssertionError("B2 process receipt must bind the exclusive run-root lock")
    raw_memory = process.get("raw_os_memory")
    if not isinstance(raw_memory, dict) or set(raw_memory) != {
        "total_visible_memory_kib",
        "free_physical_memory_kib",
    }:
        raise AssertionError("B2-12 raw OS memory facts are incomplete")
    total_kib = raw_memory["total_visible_memory_kib"]
    free_kib = raw_memory["free_physical_memory_kib"]
    if not isinstance(total_kib, int) or not isinstance(free_kib, int):
        raise AssertionError("B2-12 raw OS memory facts must be integer KiB")
    if process.get("total_memory_bytes") != total_kib * 1024:
        raise AssertionError("B2-12 total-memory conversion is inconsistent")
    if process.get("prelaunch_free_bytes") != free_kib * 1024:
        raise AssertionError("B2-12 free-memory conversion is inconsistent")
    process_rows = process.get("processes")
    if not isinstance(process_rows, list) or not process_rows:
        raise AssertionError("B2-14 must retain name-agnostic process rows")
    required_process_fields = {
        "pid",
        "parent_pid",
        "executable",
        "command_line",
        "working_set_size",
        "private_page_count",
    }
    for row in process_rows:
        if not isinstance(row, dict) or not required_process_fields <= row.keys():
            raise AssertionError("B2-14 process row lacks required raw fields")
        if not isinstance(row["pid"], int) or row["pid"] <= 0:
            raise AssertionError("B2-14 PID must be a positive integer")
        if not isinstance(row["parent_pid"], int) or row["parent_pid"] < 0:
            raise AssertionError("B2-14 parent PID must be a nonnegative integer")
        if not isinstance(row["executable"], str) or not row["executable"]:
            raise AssertionError("B2-14 executable must be retained")
        if not isinstance(row["command_line"], str):
            raise AssertionError("B2-14 command line must be retained")
        for field in ("working_set_size", "private_page_count"):
            if not isinstance(row[field], int) or row[field] < 0:
                raise AssertionError(f"B2-14 {field} must be a nonnegative integer")
    if process.get("top_n_count") != len(process_rows):
        raise AssertionError("B2-14 top-N count does not match retained process rows")
    if process.get("unexplained_competing_processes") != []:
        raise AssertionError("B2-14 must exclude unexplained competing processes")
    if process.get("prelaunch_pytest_processes") != []:
        raise AssertionError("B2-09 must observe zero pytest processes before launch")
    pytest_rows = [
        row
        for row in process_rows
        if "pytest" in row["command_line"].casefold()
        or "test_layer3_connector_vertical_loop.py" in row["command_line"].casefold()
    ]
    if pytest_rows:
        raise AssertionError(
            f"B2-09 prelaunch census contains a competing pytest process: {pytest_rows}"
        )
    if (
        not isinstance(process.get("raw_cim_output"), str)
        or not process["raw_cim_output"]
    ):
        raise AssertionError("B2-14 must retain raw CIM process output")
    if not isinstance(process.get("monitor_pid"), int) or process["monitor_pid"] <= 0:
        raise AssertionError("B2-15 monitor PID must be retained")
    live_monitor = _query_live_process_identity(process["monitor_pid"])
    monitor_identity = process.get("monitor_identity")
    expected_monitor_identity_keys = {
        "pid",
        "parent_pid",
        "executable",
        "command_line",
        "creation_time_filetime",
        "run_id",
        "run_root",
        "monitor_token",
    }
    if (
        not isinstance(monitor_identity, dict)
        or set(monitor_identity) != expected_monitor_identity_keys
    ):
        raise AssertionError("B2-15 monitor identity receipt is not exact")
    for field in ("pid", "parent_pid", "creation_time_filetime"):
        if monitor_identity[field] != live_monitor[field]:
            raise AssertionError(f"B2-15 live monitor {field} does not match receipt")
    if (
        not isinstance(monitor_identity["executable"], str)
        or Path(monitor_identity["executable"]).resolve()
        != Path(live_monitor["executable"]).resolve()
    ):
        raise AssertionError("B2-15 live monitor executable does not match receipt")
    if monitor_identity["command_line"] != live_monitor["command_line"]:
        raise AssertionError("B2-15 live monitor command line does not match receipt")
    if monitor_identity["run_id"] != _RUN_ID:
        raise AssertionError("B2-15 monitor identity does not bind the run ID")
    if monitor_identity["run_root"] != str(_DEV_RUN_ROOT):
        raise AssertionError("B2-15 monitor identity does not bind RUN_ROOT")
    expected_monitor_token = f"B1A-B2-MONITOR:{_RUN_ID}"
    if monitor_identity["monitor_token"] != expected_monitor_token:
        raise AssertionError("B2-15 monitor identity token is not exact")
    normalized_command_line = live_monitor["command_line"].replace("/", "\\").casefold()
    if expected_monitor_token.casefold() not in normalized_command_line:
        raise AssertionError("B2-15 live monitor command line lacks the run token")
    if str(_DEV_RUN_ROOT).replace("/", "\\").casefold() not in normalized_command_line:
        raise AssertionError("B2-15 live monitor command line lacks RUN_ROOT")
    _assert_utc(process.get("monitor_armed_utc"), "monitor_armed_utc")

    network = receipts["network-deny.json"]
    if network.get("status") != "ARMED":
        raise AssertionError("network-deny.json status must equal ARMED")
    if network.get("allowed_hosts") != [] or network.get("request_budget") != 0:
        raise AssertionError(
            "network-deny.json must bind zero-host/zero-request budget"
        )
    if network.get("guard_loaded") is not True:
        raise AssertionError("network-deny.json must bind a loaded socket guard")
    if network.get("intercepts") != [
        "socket.connect",
        "socket.connect_ex",
        "socket.create_connection",
    ]:
        raise AssertionError("network-deny.json intercept set is not exact")
    attempt_path = Path(str(network.get("attempt_ledger_path", ""))).resolve()
    guard_path = Path(str(network.get("guard_path", ""))).resolve()
    if not attempt_path.is_relative_to(_DEV_RUN_ROOT) or not attempt_path.is_file():
        raise AssertionError("network attempt ledger must be a RUN_ROOT file")
    if attempt_path.read_bytes() != b"":
        raise AssertionError("network attempt ledger must be empty at prelaunch")
    if not guard_path.is_relative_to(_DEV_RUN_ROOT) or not guard_path.is_file():
        raise AssertionError("socket guard must be a RUN_ROOT file")
    guard_bytes = guard_path.read_bytes()
    if guard_bytes != SOCKET_GUARD_BYTES:
        raise AssertionError(
            "socket guard bytes do not match the independently frozen guard"
        )
    if network.get("guard_sha256") != SOCKET_GUARD_SHA256:
        raise AssertionError(
            "socket guard receipt does not match the frozen guard hash"
        )
    if network.get("guard_bytes") != len(SOCKET_GUARD_BYTES):
        raise AssertionError("socket guard byte count is not exact")
    if network.get("attempt_ledger_initial_bytes") != 0:
        raise AssertionError("network attempt ledger initial size must equal zero")
    if network.get("attempt_ledger_initial_sha256") != hashlib.sha256(b"").hexdigest():
        raise AssertionError(
            "network attempt ledger initial hash must bind empty bytes"
        )
    loaded_guard = sys.modules.get("sitecustomize")
    loaded_guard_path = Path(str(getattr(loaded_guard, "__file__", ""))).resolve()
    if loaded_guard_path != guard_path:
        raise AssertionError(
            "the receipted socket guard is not the loaded sitecustomize"
        )
    pythonpath_entries = {
        Path(entry).resolve()
        for entry in os.environ.get("PYTHONPATH", "").split(os.pathsep)
        if entry
    }
    if guard_path.parent not in pythonpath_entries:
        raise AssertionError("the socket guard directory is absent from PYTHONPATH")
    if getattr(loaded_guard, "B1A_SOCKET_GUARD_ID", None) != _RUN_ID:
        raise AssertionError("loaded socket guard does not bind the B1a run ID")
    if (
        Path(str(getattr(loaded_guard, "B1A_ATTEMPT_LEDGER", ""))).resolve()
        != attempt_path
    ):
        raise AssertionError("loaded socket guard does not bind the attempt ledger")
    expected_wrappers = {
        "socket.connect": (socket.socket.connect, "_b1a_connect"),
        "socket.connect_ex": (socket.socket.connect_ex, "_b1a_connect_ex"),
        "socket.create_connection": (
            socket.create_connection,
            "_b1a_create_connection",
        ),
    }
    for api, (live_wrapper, module_name) in expected_wrappers.items():
        frozen_wrapper = getattr(loaded_guard, module_name, None)
        if live_wrapper is not frozen_wrapper:
            raise AssertionError(f"{api} is not bound to the frozen socket guard")
        if getattr(live_wrapper, "__b1a_socket_guard_id__", None) != _RUN_ID:
            raise AssertionError(f"{api} wrapper does not bind the B1a run ID")
        if (
            Path(str(getattr(live_wrapper, "__b1a_attempt_ledger__", ""))).resolve()
            != attempt_path
        ):
            raise AssertionError(f"{api} wrapper does not bind the attempt ledger")

    durability = receipts["durability-disposition.json"]
    if durability.get("status") != "PASS-TO-LAUNCH":
        raise AssertionError("durability receipt status must equal PASS-TO-LAUNCH")
    if durability.get("pass_to_launch") is not True:
        raise AssertionError("durability receipt must bind pass_to_launch=true")
    if durability.get("run_root_disposition") != "RETAIN EVIDENCE_DIR":
        raise AssertionError("durability disposition must equal RETAIN EVIDENCE_DIR")
    if (
        not isinstance(durability.get("operator"), str)
        or not durability["operator"].strip()
    ):
        raise AssertionError("B2-16 must retain the operator identity")
    if (
        not isinstance(durability.get("raw_outputs"), dict)
        or not durability["raw_outputs"]
    ):
        raise AssertionError("B2-16 must retain raw prelaunch outputs")
    if durability.get("config_probe_sha256") != _canonical_json_sha256(config_probe):
        raise AssertionError("B2-16 config-probe hash is inconsistent")
    if durability.get("guard_sha256") != SOCKET_GUARD_SHA256:
        raise AssertionError("B2-16 guard hash is inconsistent")
    expected_receipt_hashes = {
        name: hashlib.sha256(paths[name].read_bytes()).hexdigest()
        for name in B2_RECEIPT_NAMES
        if name != "durability-disposition.json"
    }
    if durability.get("receipt_hashes") != expected_receipt_hashes:
        raise AssertionError("B2-16 cross-receipt hashes are inconsistent")
    if durability.get("receipt_digest_algorithm") != (
        "sha256(canonical-json-without-receipt_digest)"
    ):
        raise AssertionError("B2-16 receipt digest algorithm is not exact")
    digest_payload = dict(durability)
    receipt_digest = digest_payload.pop("receipt_digest", None)
    if receipt_digest != _canonical_json_sha256(digest_payload):
        raise AssertionError("B2-16 receipt digest is inconsistent")
    return receipts


def _emit_preimport_stop_receipt(exc: BaseException, last_step: str) -> None:
    evidence_dir = _DESIRED_EVIDENCE_PATH
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / "stop-receipt.json"
    if path.exists():
        return
    payload = {
        "condition": "PRE-APP-IMPORT-SAFETY-OR-RECEIPT-FAILURE",
        "measured_facts": {
            "exception_class": type(exc).__name__,
            "exception_message": str(exc),
            "run_root": str(_DEV_RUN_ROOT),
            "database_path": str(_DESIRED_DATABASE_PATH),
            "storage_dir": str(_DESIRED_STORAGE_PATH),
        },
        "last_completed_step": last_step,
        "row_count_snapshot": {},
        "zero_further_mutation_assertion": True,
        "run_id": _RUN_ID,
        "run_nonce": _RUN_NONCE,
        "producer_node": "module-import",
        "status": "STOP",
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# P1 ordering rail: in the mandated repo-local worktree, rehash the sealed
# instruments before importing any application module.  CI lacks these
# untracked child-manifest artifacts and therefore validates the contract in
# the first test without pretending that B2 ran.
try:
    EARLY_EXTERNAL_SEAL_RECEIPTS = _early_external_seal_rehash()
    EARLY_B2_RECEIPTS = _load_and_validate_b2_receipts()
    if _CONFIGURED_RUN_ROOT and EARLY_EXTERNAL_SEAL_RECEIPTS is None:
        raise AssertionError("B2 runtime must rehash the external sealed chain")
    EARLY_B2_RECEIPT_FILE_HASHES = (
        {
            name: hashlib.sha256(
                (_DESIRED_EVIDENCE_PATH / name).read_bytes()
            ).hexdigest()
            for name in B2_RECEIPT_NAMES
        }
        if EARLY_B2_RECEIPTS is not None
        else {}
    )
except BaseException as _preimport_error:
    _emit_preimport_stop_receipt(_preimport_error, "P1/B2-PRE-APP-IMPORT")
    raise


def _is_app_module(module_name: str) -> bool:
    return (
        module_name == "main" or module_name == "app" or module_name.startswith("app.")
    )


if "app.db.session" in sys.modules and "app.models.models" not in sys.modules:
    for _name, _prior_value in _PRIOR_IMPORT_ENV.items():
        if _prior_value is None:
            os.environ.pop(_name, None)
        else:
            os.environ[_name] = _prior_value
    try:
        importlib.import_module("app.models.models")
    except BaseException as _baseline_orm_error:
        _emit_preimport_stop_receipt(
            _baseline_orm_error, "BASELINE-PARTIAL-ORM-PRELOAD-NORMALIZATION"
        )
        raise
    else:
        os.environ.update(_RUNTIME_ENV)

_PREEXISTING_APP_MODULES = {
    name: module for name, module in sys.modules.items() if _is_app_module(name)
}
_PREEXISTING_APP_MODULE_STATE = {
    name: dict(module.__dict__) for name, module in _PREEXISTING_APP_MODULES.items()
}
_B1A_SETTINGS_OVERRIDES = {
    "db_init_mode": _DESIRED_DB_INIT_MODE,
    "database_url": str(_DESIRED_DATABASE_URL),
    "storage_dir": str(_DESIRED_STORAGE_PATH),
    "layer3_external_local_export_dir": (
        _DESIRED_AMBIENT_WRITE_TARGETS["LAYER3_EXTERNAL_LOCAL_EXPORT_DIR"] or ""
    ),
    "layer3_candidate_b_bundle_bridge_dir": (
        _DESIRED_AMBIENT_WRITE_TARGETS["LAYER3_CANDIDATE_B_BUNDLE_BRIDGE_DIR"] or ""
    ),
    "layer3_candidate_b_runtime_bridge_dir": (
        _DESIRED_AMBIENT_WRITE_TARGETS["LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR"] or ""
    ),
    "layer3_candidate_b_full_corpus_operator_workflow_dir": (
        _DESIRED_AMBIENT_WRITE_TARGETS[
            "LAYER3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR"
        ]
        or ""
    ),
    "layer3_source_ingestion_dir": (
        _DESIRED_AMBIENT_WRITE_TARGETS["LAYER3_SOURCE_INGESTION_DIR"] or ""
    ),
}
_IMPORT_SETTINGS_PRIOR: dict[str, Any] | None = None
_APP_IMPORT_FAILURE: BaseException | None = None
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

try:
    import pytest
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, event, select, update
    from sqlalchemy.engine import Connection, Engine, make_url
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import QueuePool, StaticPool

    from app.core.config import bootstrap_storage_tree, settings

    _IMPORT_SETTINGS_PRIOR = {
        name: getattr(settings, name) for name in _B1A_SETTINGS_OVERRIDES
    }
    for _setting_name, _setting_value in _B1A_SETTINGS_OVERRIDES.items():
        setattr(settings, _setting_name, _setting_value)

    from app.api.deps import get_db
    from app.db.session import Base, engine as app_engine
    from app.models.models import (
        AnalysisArtifact,
        AnalysisRun,
        ApsContentDocument,
        ApsContentLinkage,
        AssumptionCheck,
        CaveatNote,
        ConnectorPolicySnapshot,
        ConnectorRun,
        ConnectorRunEvent,
        ConnectorRunTarget,
        Dataset,
        DatasetRow,
        DatasetSourceProvenance,
        DatasetVersion,
        L3AnalysisGroup,
        L3AnalysisPlan,
        L3AnalysisSet,
        L3AnalysisUnit,
        L3ConnectorSourceIntakeRecord,
        L3Descriptor,
        L3GateBIdempotencyKey,
        L3MaterialSnapshot,
        L3OutputPackage,
        L3PassRun,
        L3ReconciliationRecord,
        L3RetrievalEvent,
        L3SelectionManifest,
        L3Session,
        L3TypingRecord,
        SourceConnector,
        VariableDefinition,
    )
    from app.services.analysis import run_analysis
    from app.services import layer3_connector_source_intake as connector_intake
    from app.services import layer3_gate_b_state as gate_b_state
    from app.services import layer3_origin_continuity as origin
    from app.services import layer3_workbench
    from app.services.ingest import ingest_csv_bytes_to_dataset
    from app.services.layer3_connector_source_intake import (
        ConnectorSourceIntakeError,
        connector_source_intake_material_preview,
        record_connector_produced_source_intake,
    )
    from app.services.layer3_workbench import gate_b_decision
    from app.services.layer3_workbench_error import Layer3WorkbenchError
    from main import app
except BaseException as _app_import_error:
    _APP_IMPORT_FAILURE = _app_import_error
finally:
    if _IMPORT_SETTINGS_PRIOR is not None:
        for _setting_name, _setting_value in _IMPORT_SETTINGS_PRIOR.items():
            setattr(settings, _setting_name, _setting_value)
    for _name, _prior_value in _PRIOR_IMPORT_ENV.items():
        if _prior_value is None:
            os.environ.pop(_name, None)
        else:
            os.environ[_name] = _prior_value

_B1A_IMPORTED_APP_MODULES = {
    name: module for name, module in sys.modules.items() if _is_app_module(name)
}
_DETACHED_APP_MODULE_NAMES = sorted(
    set(_B1A_IMPORTED_APP_MODULES) - set(_PREEXISTING_APP_MODULES)
)
for _module_name in list(sys.modules):
    if _is_app_module(_module_name) and _module_name not in _PREEXISTING_APP_MODULES:
        sys.modules.pop(_module_name, None)
for _module_name, _module in _PREEXISTING_APP_MODULES.items():
    _module.__dict__.clear()
    _module.__dict__.update(_PREEXISTING_APP_MODULE_STATE[_module_name])
    sys.modules[_module_name] = _module
assert all(name not in sys.modules for name in _DETACHED_APP_MODULE_NAMES)
assert all(
    sys.modules.get(name) is module for name, module in _PREEXISTING_APP_MODULES.items()
)
if _APP_IMPORT_FAILURE is not None:
    _emit_preimport_stop_receipt(_APP_IMPORT_FAILURE, "APPLICATION-MODULE-IMPORT")
    raise _APP_IMPORT_FAILURE


@pytest.fixture(scope="module", autouse=True)
def _b1a_settings_scope() -> Iterator[None]:
    previous = {name: getattr(settings, name) for name in _B1A_SETTINGS_OVERRIDES}
    for name, value in _B1A_SETTINGS_OVERRIDES.items():
        setattr(settings, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(settings, name, value)


CT3_ROWS = {
    "CT3-01": "UNDECIDED (explicit)",
    "CT3-02": "S1",
    "CT3-03": "E2",
    "CT3-04": "R1",
    "CT3-05": "N2",
    "CT3-06": "UNDECIDED (explicit)",
    "CT3-07": "UNDECIDED (explicit)",
    "CT3-08": "M1",
}
CT3_STOPS = {
    "CT3-01": "STOP-CT3-01-IDENTITY",
    "CT3-06": "STOP-CT3-06-PROMOTION",
    "CT3-07": "STOP-CT3-07-REPLAY",
}
CT3_CONSUMPTION = {
    "CT3-01": {
        "disposition": "UNDECIDED (explicit)",
        "fill_class": "undecided",
        "case_evidence_refs": ["b1b-owner-stops.json"],
        "nonclaim": "no canonical cross-run identity or equivalence",
    },
    "CT3-02": {
        "disposition": "S1",
        "fill_class": "owner-delegated provisional",
        "case_evidence_refs": ["b1a-positive-gate-b.json"],
    },
    "CT3-03": {
        "disposition": "E2",
        "fill_class": "owner-delegated provisional",
        "case_evidence_refs": ["b1a-positive-gate-b.json"],
    },
    "CT3-04": {
        "disposition": "R1",
        "fill_class": "owner-delegated provisional",
        "case_evidence_refs": ["negative-battery-summary.json"],
    },
    "CT3-05": {
        "disposition": "N2",
        "fill_class": "owner-delegated provisional",
        "case_evidence_refs": [
            "negative-01-denied.json",
            "negative-02-isolated.json",
        ],
    },
    "CT3-06": {
        "disposition": "UNDECIDED (explicit)",
        "fill_class": "undecided",
        "case_evidence_refs": ["b1b-owner-stops.json"],
        "nonclaim": "no approval-to-3C promotion lifecycle or receipt",
    },
    "CT3-07": {
        "disposition": "UNDECIDED (explicit)",
        "fill_class": "undecided",
        "case_evidence_refs": [
            "dual-seam-replay.json",
            "negative-08-replay-conflict.json",
            "b1b-owner-stops.json",
        ],
        "nonclaim": "no unified retry, recovery, replay, or deduplication policy",
    },
    "CT3-08": {
        "disposition": "M1",
        "fill_class": "owner-decided",
        "case_evidence_refs": [
            "dual-seam-replay.json",
            "negative-08-replay-conflict.json",
        ],
    },
}
assert {row: entry["disposition"] for row, entry in CT3_CONSUMPTION.items()} == CT3_ROWS

REQUIRED_PRE_CLOSEOUT_EVIDENCE = {
    "p1-authoring-seals.json",
    "fixture-c01.json",
    "fixture-copy.json",
    "b1a-positive-gate-b.json",
    "negative-01-denied.json",
    "negative-02-isolated.json",
    "negative-03-null-unreviewed.json",
    "negative-04-stale.json",
    "negative-05-duplicate.json",
    "negative-06-missing-provenance.json",
    "negative-07-malformed.json",
    "negative-08-replay-conflict.json",
    "negative-battery-summary.json",
    "dual-seam-replay.json",
    "descriptive-run-1.json",
    "descriptive-run-2.json",
    "descriptive-determinism.json",
    "component-nonclaim.json",
    "ct3-b1a-consumption.json",
    "b1b-owner-stops.json",
    "stop-receipt.json",
}

_EVIDENCE_PRODUCERS = {
    "test_b1a_b2_receipt_and_fixture_assertions": {
        "p1-authoring-seals.json",
        "fixture-c01.json",
        "fixture-copy.json",
    },
    "test_b1a_connector_gate_b_positive_and_eight_negatives": {
        "b1a-positive-gate-b.json",
        "negative-01-denied.json",
        "negative-02-isolated.json",
        "negative-03-null-unreviewed.json",
        "negative-04-stale.json",
        "negative-05-duplicate.json",
        "negative-06-missing-provenance.json",
        "negative-07-malformed.json",
        "negative-08-replay-conflict.json",
        "negative-battery-summary.json",
    },
    "test_b1a_dual_seam_replay_matrix": {"dual-seam-replay.json"},
    "test_b1a_descriptive_summary_component_determinism": {
        "descriptive-run-1.json",
        "descriptive-run-2.json",
        "descriptive-determinism.json",
        "component-nonclaim.json",
    },
    "test_b1b_owner_semantic_stops_are_zero_mutation": {
        "ct3-b1a-consumption.json",
        "b1b-owner-stops.json",
        "stop-receipt.json",
    },
}
assert set().union(*_EVIDENCE_PRODUCERS.values()) == REQUIRED_PRE_CLOSEOUT_EVIDENCE
_REGISTERED_STORED_PATHS: set[Path] = set()
_LAST_COMPLETED_STEP = "MODULE-IMPORT-COMPLETE"
_LAST_ROW_SNAPSHOT: dict[str, int] = {}

CENSUS_MODELS = {
    model.__name__: model
    for model in (
        ConnectorRun,
        ConnectorRunTarget,
        L3ConnectorSourceIntakeRecord,
        SourceConnector,
        Dataset,
        DatasetVersion,
        VariableDefinition,
        DatasetRow,
        DatasetSourceProvenance,
        L3GateBIdempotencyKey,
        L3Session,
        L3SelectionManifest,
        L3Descriptor,
        L3RetrievalEvent,
        L3MaterialSnapshot,
        L3TypingRecord,
        L3AnalysisUnit,
        L3AnalysisGroup,
        L3AnalysisSet,
        L3AnalysisPlan,
        L3PassRun,
        AnalysisRun,
        AssumptionCheck,
        CaveatNote,
        AnalysisArtifact,
        L3ReconciliationRecord,
        L3OutputPackage,
    )
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _network_evidence() -> dict[str, Any]:
    if EARLY_B2_RECEIPTS is None:
        return {
            "measurement_status": "NOT-RUN-IN-STEP1-AUTHORING",
            "socket_attempts": None,
            "loopback_socket_attempts": None,
            "non_loopback_socket_attempts": None,
        }
    network = EARLY_B2_RECEIPTS["network-deny.json"]
    attempt_path = Path(network["attempt_ledger_path"]).resolve()
    guard_path = Path(network["guard_path"]).resolve()
    assert guard_path.read_bytes() == SOCKET_GUARD_BYTES
    assert _sha256_bytes(guard_path.read_bytes()) == SOCKET_GUARD_SHA256
    loaded_guard = sys.modules.get("sitecustomize")
    assert Path(str(getattr(loaded_guard, "__file__", ""))).resolve() == guard_path
    assert getattr(loaded_guard, "B1A_SOCKET_GUARD_ID", None) == _RUN_ID
    assert (
        Path(str(getattr(loaded_guard, "B1A_ATTEMPT_LEDGER", ""))).resolve()
        == attempt_path
    )
    for live_wrapper, module_name in (
        (socket.socket.connect, "_b1a_connect"),
        (socket.socket.connect_ex, "_b1a_connect_ex"),
        (socket.create_connection, "_b1a_create_connection"),
    ):
        assert live_wrapper is getattr(loaded_guard, module_name, None)
        assert getattr(live_wrapper, "__b1a_socket_guard_id__", None) == _RUN_ID
        assert (
            Path(str(getattr(live_wrapper, "__b1a_attempt_ledger__", ""))).resolve()
            == attempt_path
        )
    payload = attempt_path.read_bytes()
    attempts = []
    for line in payload.splitlines():
        if line.strip():
            attempt = json.loads(line)
            assert isinstance(attempt, dict)
            assert type(attempt.get("is_loopback")) is bool
            attempts.append(attempt)
    loopback_attempts = [attempt for attempt in attempts if attempt["is_loopback"]]
    non_loopback_attempts = [
        attempt for attempt in attempts if not attempt["is_loopback"]
    ]
    assert non_loopback_attempts == [], (
        "offline socket guard recorded non-loopback attempts: "
        f"{non_loopback_attempts}"
    )
    return {
        "measurement_status": "B2-LIVE-SOCKET-DENY-LEDGER",
        "socket_attempts": len(attempts),
        "loopback_socket_attempts": len(loopback_attempts),
        "non_loopback_socket_attempts": len(non_loopback_attempts),
        "loopback_attempts": loopback_attempts,
        "attempt_ledger_path": str(attempt_path),
        "attempt_ledger_bytes": len(payload),
        "attempt_ledger_sha256": _sha256_bytes(payload),
        "guard_sha256": network["guard_sha256"],
    }


def _phase_status() -> str:
    network = _network_evidence()
    if network["non_loopback_socket_attempts"] == 0:
        return "PASS"
    return "AUTHORING-CONTRACT-PASS"


def _git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def _assert_socket_guard_loopback_contract() -> None:
    ledger_path = "C:/b1a-socket-guard-self-check/network-attempts.ndjson"
    ledger_writes: list[str] = []
    ledger_flushes: list[bool] = []
    fsync_calls: list[int] = []
    real_calls: list[tuple[str, object]] = []
    forwarded_create_connection: list[
        tuple[object, tuple[object, ...], dict[str, object]]
    ] = []
    create_connection_result = object()

    class _FakeLedgerHandle:
        def __enter__(self) -> _FakeLedgerHandle:
            return self

        def __exit__(self, *args: object) -> None:
            del args

        def write(self, payload: str) -> int:
            ledger_writes.append(payload)
            return len(payload)

        def flush(self) -> None:
            ledger_flushes.append(True)

        def fileno(self) -> int:
            return 41

    def _fake_open(
        path: object,
        mode: str,
        *,
        encoding: str,
        newline: str,
    ) -> _FakeLedgerHandle:
        assert path == ledger_path
        assert mode == "a"
        assert encoding == "utf-8"
        assert newline == "\n"
        return _FakeLedgerHandle()

    def _fake_fsync(file_descriptor: int) -> None:
        fsync_calls.append(file_descriptor)

    class _FakeSocket:
        def __init__(self, family: int = 2) -> None:
            self.family = family

        def connect(self, address: object) -> None:
            real_calls.append(("socket.connect", address))

        def connect_ex(self, address: object) -> int:
            real_calls.append(("socket.connect_ex", address))
            return 17

    def _fake_create_connection(
        address: object, *args: object, **kwargs: object
    ) -> object:
        real_calls.append(("socket.create_connection", address))
        forwarded_create_connection.append((address, args, kwargs))
        return create_connection_result

    fake_socket_module = type("_FakeSocketModule", (), {})()
    fake_socket_module.AF_INET = 2
    fake_socket_module.AF_INET6 = 23
    fake_socket_module.socket = _FakeSocket
    fake_socket_module.create_connection = _fake_create_connection
    fake_os_module = type("_FakeOsModule", (), {"fsync": staticmethod(_fake_fsync)})()
    prior_socket_module = sys.modules["socket"]
    guard_env = {
        "B1A_RUN_ID": "b1a-socket-guard-self-check",
        "B1A_NETWORK_ATTEMPT_LEDGER": str(ledger_path),
    }
    prior_guard_env = {name: os.environ.get(name) for name in guard_env}
    guard_namespace: dict[str, Any] = {}
    try:
        sys.modules["socket"] = fake_socket_module
        os.environ.update(guard_env)
        exec(
            compile(SOCKET_GUARD_SOURCE, "sitecustomize.py", "exec"),
            guard_namespace,
        )
    finally:
        sys.modules["socket"] = prior_socket_module
        for name, value in prior_guard_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    guard_namespace["open"] = _fake_open
    guard_namespace["os"] = fake_os_module
    client = fake_socket_module.socket()
    ipv6_client = fake_socket_module.socket(fake_socket_module.AF_INET6)
    unix_client = fake_socket_module.socket(1)
    assert client.connect(("127.0.0.1", 41001)) is None
    assert ipv6_client.connect_ex(("::1", 41002)) == 17
    assert ipv6_client.connect_ex(("localhost", 41011)) == 17
    assert (
        fake_socket_module.create_connection(
            ("localhost", 41003),
            1.0,
            source_address=("localhost", 0),
        )
        is create_connection_result
    )
    assert real_calls == [
        ("socket.connect", ("127.0.0.1", 41001)),
        ("socket.connect_ex", ("::1", 41002)),
        ("socket.connect_ex", ("::1", 41011)),
        ("socket.create_connection", ("127.0.0.1", 41003)),
    ]
    assert forwarded_create_connection == [
        (
            ("127.0.0.1", 41003),
            (1.0,),
            {"source_address": ("127.0.0.1", 0)},
        )
    ]

    class _LoopbackHost(str):
        pass

    class _LoopbackAddress(tuple):
        pass

    denied_calls = (
        lambda: client.connect(("198.51.100.1", 9)),
        lambda: client.connect_ex(("198.51.100.1", 9)),
        lambda: fake_socket_module.create_connection(("198.51.100.1", 9)),
        lambda: client.connect(("localhost",)),
        lambda: client.connect_ex(("127.0.0.1", "not-a-port")),
        lambda: fake_socket_module.create_connection(("::1",)),
        lambda: client.connect(("localhoſt", 41004)),
        lambda: client.connect_ex((_LoopbackHost("localhost"), 41005)),
        lambda: fake_socket_module.create_connection(
            _LoopbackAddress(("::1", 41006))
        ),
        lambda: fake_socket_module.create_connection(("::1", 41007, 0, 0)),
        lambda: client.connect_ex(("::1", 41008, 0, 1 << 100)),
        lambda: unix_client.connect(("127.0.0.1", 41009)),
        lambda: fake_socket_module.create_connection(
            ("127.0.0.1", 41010),
            source_address=("example.com", 0),
        ),
    )
    for denied_call in denied_calls:
        with pytest.raises(
            OSError, match=r"^OFFLINE-ONLY: outbound socket attempt denied$"
        ):
            denied_call()
    assert len(real_calls) == 4

    attempts = [json.loads(payload) for payload in ledger_writes]
    assert [attempt["api"] for attempt in attempts] == [
        "socket.connect",
        "socket.connect_ex",
        "socket.connect_ex",
        "socket.create_connection",
        "socket.connect",
        "socket.connect_ex",
        "socket.create_connection",
        "socket.connect",
        "socket.connect_ex",
        "socket.create_connection",
        "socket.connect",
        "socket.connect_ex",
        "socket.create_connection",
        "socket.create_connection",
        "socket.connect_ex",
        "socket.connect",
        "socket.create_connection",
    ]
    assert [attempt["is_loopback"] for attempt in attempts] == [
        True,
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ]
    assert all(attempt["run_id"] == guard_env["B1A_RUN_ID"] for attempt in attempts)
    assert attempts[2]["address_repr"] == "('localhost', 41011)"
    assert attempts[2]["forwarded_address_repr"] == "('::1', 41011)"
    assert attempts[3]["address_repr"] == "('localhost', 41003)"
    assert attempts[3]["forwarded_address_repr"] == "('127.0.0.1', 41003)"
    assert attempts[3]["source_address_repr"] == "('localhost', 0)"
    assert attempts[3]["forwarded_source_address_repr"] == "('127.0.0.1', 0)"
    assert ledger_flushes == [True] * len(attempts)
    assert fsync_calls == [41] * len(attempts)


def _file_receipt(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": str(path),
        "bytes": len(payload),
        "sha256": _sha256_bytes(payload),
    }


def _assert_file_seal(path: Path, expected: tuple[int, str]) -> dict[str, Any]:
    receipt = _file_receipt(path)
    assert receipt["bytes"] == expected[0]
    assert receipt["sha256"] == expected[1]
    return receipt


def _preservation_root() -> Path | None:
    configured = os.environ.get("B1A_CHAIN_ROOT")
    if configured:
        return Path(configured).resolve()
    resolved = Path(__file__).resolve()
    for parent in resolved.parents:
        if (
            parent.name == "worktrees"
            and parent.parent.name == "project6_REPO_MCP_FOLDER"
        ):
            return parent.parent
    return None


def _chain_paths() -> dict[str, Path] | None:
    root = _preservation_root()
    fixture = Path(
        os.environ.get(
            "B1A_FIXTURE_PATH", "C:/p6fixtures/sciencebase-v1/water-quality.csv"
        )
    )
    if root is None:
        return None
    paths = {
        "child_manifest": root
        / "worktrees/manifest-children/ct4b-fixture-child-manifest.json",
        "freeze_manifest": root / "worktrees/freeze-v1/manifest-v1.json",
        "freeze_aggregate": root / "worktrees/freeze-v1/aggregate-rows.txt",
        "fixture": fixture,
        "packet": root / "state/agent-inbox/b1-vertical-loop-packet.md",
        "owner_record": root / "state/agent-inbox/owner-decision-record-2026-07-10.md",
        "ct3_table": root / "state/agent-inbox/ct3-semantics-table.md",
    }
    return paths if all(path.is_file() for path in paths.values()) else None


def _evidence_dir(tmp_path: Path) -> Path:
    del tmp_path
    path = _DESIRED_EVIDENCE_PATH
    path.mkdir(parents=True, exist_ok=True)
    return path


def _current_test_node() -> str:
    current = os.environ.get("PYTEST_CURRENT_TEST", "")
    return current.split("::")[-1].split(" ", maxsplit=1)[0]


def _write_evidence(
    evidence_dir: Path,
    name: str,
    payload: dict[str, Any],
    *,
    producer_node: str | None = None,
) -> Path:
    global _LAST_COMPLETED_STEP
    assert evidence_dir.resolve() == _DESIRED_EVIDENCE_PATH
    path = evidence_dir / name
    assert not path.exists(), f"refusing to overwrite evidence file: {path}"
    assert not {"run_id", "run_nonce", "producer_node"} & payload.keys()
    enriched = {
        **payload,
        "run_id": _RUN_ID,
        "run_nonce": _RUN_NONCE,
        "producer_node": producer_node or _current_test_node(),
    }
    path.write_text(
        json.dumps(enriched, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _LAST_COMPLETED_STEP = name
    return path


def _emit_runtime_stop_receipt(
    exc: BaseException,
    *,
    producer_node: str,
    condition: str,
) -> None:
    evidence_dir = _DESIRED_EVIDENCE_PATH
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / "stop-receipt.json"
    prior_expected_stop: dict[str, Any] | None = None
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if isinstance(existing, dict) and existing.get("status") == "STOP":
            return
        if isinstance(existing, dict) and existing.get("status") == "EXPECTED-B1B-STOP":
            prior_expected_stop = copy.deepcopy(existing)
    if EARLY_B2_RECEIPTS is None:
        network_facts: dict[str, Any] = {
            "measurement_status": "NOT-RUN-IN-STEP1-AUTHORING",
            "socket_attempts": None,
            "loopback_socket_attempts": None,
            "non_loopback_socket_attempts": None,
        }
    else:
        attempt_path = Path(
            EARLY_B2_RECEIPTS["network-deny.json"]["attempt_ledger_path"]
        ).resolve()
        attempt_bytes = attempt_path.read_bytes()
        attempt_lines = [
            line for line in attempt_bytes.splitlines() if line.strip()
        ]
        loopback_socket_attempts = 0
        malformed_socket_attempts = 0
        for line in attempt_lines:
            try:
                attempt = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                malformed_socket_attempts += 1
                continue
            if (
                not isinstance(attempt, dict)
                or type(attempt.get("is_loopback")) is not bool
            ):
                malformed_socket_attempts += 1
                continue
            if attempt["is_loopback"]:
                loopback_socket_attempts += 1
        network_facts = {
            "measurement_status": "B2-LIVE-SOCKET-DENY-LEDGER",
            "socket_attempts": len(attempt_lines),
            "loopback_socket_attempts": loopback_socket_attempts,
            "non_loopback_socket_attempts": (
                len(attempt_lines) - loopback_socket_attempts
            ),
            "malformed_socket_attempts": malformed_socket_attempts,
            "attempt_ledger_bytes": len(attempt_bytes),
            "attempt_ledger_sha256": hashlib.sha256(attempt_bytes).hexdigest(),
        }
    payload = {
        "condition": condition,
        "measured_facts": {
            "exception_class": type(exc).__name__,
            "exception_message": str(exc),
            "network": network_facts,
            "run_root": str(_DEV_RUN_ROOT),
            "database_path": str(_DESIRED_DATABASE_PATH),
            "storage_dir": str(_DESIRED_STORAGE_PATH),
        },
        "last_completed_step": _LAST_COMPLETED_STEP,
        "row_count_snapshot": _LAST_ROW_SNAPSHOT,
        "zero_further_mutation_assertion": True,
        "run_id": _RUN_ID,
        "run_nonce": _RUN_NONCE,
        "producer_node": producer_node,
        "status": "STOP",
    }
    if prior_expected_stop is not None:
        payload["prior_expected_stop"] = prior_expected_stop
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _stop_receipt_on_failure(test_function: Any) -> Any:
    @wraps(test_function)
    def guarded(*args: Any, **kwargs: Any) -> Any:
        try:
            return test_function(*args, **kwargs)
        except BaseException as exc:
            _emit_runtime_stop_receipt(
                exc,
                producer_node=test_function.__name__,
                condition="PYTEST-CALL-G6-OR-SAFETY-FAILURE",
            )
            pytest.exit(
                "B1a STOP receipt emitted; zero further test mutation", returncode=1
            )

    return guarded


def _register_stored_path(path: Path) -> Path:
    resolved = path.resolve()
    assert resolved.is_relative_to(_DESIRED_STORAGE_PATH), resolved
    assert resolved.is_file(), resolved
    _REGISTERED_STORED_PATHS.add(resolved)
    return resolved


@contextmanager
def _runtime_environment() -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in _RUNTIME_ENV}
    os.environ.update(_RUNTIME_ENV)
    try:
        yield
    finally:
        for name, prior_value in previous.items():
            if prior_value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = prior_value


@contextmanager
def _one_isolated_app_engine() -> Iterator[Engine]:
    assert app_engine.dialect.name == "sqlite"
    original_pool = app_engine.pool
    original_url = app_engine.url
    original_checked_out = getattr(original_pool, "checkedout", lambda: 0)
    assert original_checked_out() == 0
    original_pool.dispose()
    isolated_pool = QueuePool(
        lambda: sqlite3.connect(
            str(_DESIRED_DATABASE_PATH),
            check_same_thread=False,
        ),
        reset_on_return="rollback",
    )
    app_engine.pool = isolated_pool
    app_engine.url = make_url(str(_DESIRED_DATABASE_URL))
    try:
        yield app_engine
    finally:
        assert isolated_pool.checkedout() == 0
        isolated_pool.dispose()
        app_engine.pool = original_pool
        app_engine.url = original_url
        assert original_checked_out() == 0


class _B1aRuntime:
    def __init__(self, engine: Engine, storage_dir: Path) -> None:
        self.engine = engine
        self.storage_dir = storage_dir
        self.connection: Connection | None = None
        self.client: TestClient | None = None
        self.closeout_requested = False
        self.final_row_ledger: dict[str, Any] | None = None

    def override_get_db(self) -> Iterator[Session]:
        if self.connection is None:
            raise RuntimeError("B1a request attempted outside the owned transaction")
        request_session = Session(
            bind=self.connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="rollback_only",
        )
        try:
            yield request_session
        finally:
            request_session.close()

    @contextmanager
    def scenario(self) -> Iterator[Session]:
        if self.connection is not None:
            raise RuntimeError("B1a scenarios are serialized")
        connection = self.engine.connect()
        outer = connection.begin()
        direct_session = Session(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="rollback_only",
        )
        self.connection = connection
        try:
            yield direct_session
        finally:
            direct_session.close()
            self.connection = None
            if not outer.is_active:
                connection.close()
                raise AssertionError(
                    "scenario service ended the outer rollback boundary"
                )
            outer.rollback()
            connection.close()


def _phase_evidence_is_fresh(evidence_dir: Path) -> bool:
    if any(path.is_dir() for path in evidence_dir.rglob("*")):
        return False
    names = {
        path.relative_to(evidence_dir).as_posix()
        for path in evidence_dir.rglob("*")
        if path.is_file()
    }
    expected_names = set(REQUIRED_PRE_CLOSEOUT_EVIDENCE)
    if EARLY_B2_RECEIPTS is not None:
        expected_names |= set(B2_RECEIPT_NAMES)
        network = EARLY_B2_RECEIPTS["network-deny.json"]
        for key in ("attempt_ledger_path", "guard_path"):
            external_path = Path(network[key]).resolve()
            if external_path.is_relative_to(evidence_dir):
                expected_names.add(external_path.relative_to(evidence_dir).as_posix())
    if names != expected_names:
        return False
    expected_producer = {
        name: node
        for node, node_names in _EVIDENCE_PRODUCERS.items()
        for name in node_names
    }
    for name in REQUIRED_PRE_CLOSEOUT_EVIDENCE:
        try:
            payload = json.loads((evidence_dir / name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        if payload.get("run_id") != _RUN_ID or payload.get("run_nonce") != _RUN_NONCE:
            return False
        if payload.get("producer_node") != expected_producer[name]:
            return False
    return True


def _finalize_closeout(runtime: _B1aRuntime) -> None:
    if not runtime.closeout_requested:
        return
    assert runtime.connection is None
    assert runtime.client is None
    assert runtime.final_row_ledger is not None
    evidence_dir = _DESIRED_EVIDENCE_PATH
    aggregate_phases_present = _phase_evidence_is_fresh(evidence_dir)
    if not _DISTRIBUTED_COLLECTION:
        assert aggregate_phases_present, (
            "all five fresh phase-node evidence sets are required"
        )

    final_network = _network_evidence()
    if EARLY_B2_RECEIPTS is not None:
        closeout_b2_hashes = {
            name: hashlib.sha256((evidence_dir / name).read_bytes()).hexdigest()
            for name in B2_RECEIPT_NAMES
        }
        assert closeout_b2_hashes == EARLY_B2_RECEIPT_FILE_HASHES
    _write_evidence(
        evidence_dir,
        "row-ledger-final.json",
        {
            **runtime.final_row_ledger,
            "status": _phase_status(),
        },
        producer_node="module-teardown",
    )
    _write_evidence(
        evidence_dir,
        "network-ledger-final.json",
        {
            **final_network,
            "status": _phase_status(),
        },
        producer_node="module-teardown",
    )

    chain_paths = _chain_paths()
    closeout_fixture = (
        chain_paths["fixture"].read_bytes()
        if chain_paths is not None
        else FIXTURE_BYTES
    )
    assert len(closeout_fixture) == 34
    assert _sha256_bytes(closeout_fixture) == FIXTURE_SHA256
    assert _sha256_bytes(bytes(closeout_fixture)) == FIXTURE_SHA256

    storage_files = {
        path.resolve() for path in _DESIRED_STORAGE_PATH.rglob("*") if path.is_file()
    }
    assert _REGISTERED_STORED_PATHS <= storage_files, {
        "registered_but_missing": sorted(
            str(path) for path in _REGISTERED_STORED_PATHS - storage_files
        )
    }
    assert all(path.is_relative_to(_DESIRED_STORAGE_PATH) for path in storage_files)
    assert _DESIRED_DATABASE_PATH.is_relative_to(_DEV_RUN_ROOT)
    assert _DESIRED_STORAGE_PATH.is_relative_to(_DEV_RUN_ROOT)
    assert _DESIRED_EVIDENCE_PATH.is_relative_to(_DEV_RUN_ROOT)

    _write_evidence(
        evidence_dir,
        "b1a-verdict.json",
        {
            "five_node_aggregate_present": aggregate_phases_present,
            "step1_authoring_contract": (
                "PASS" if aggregate_phases_present else "NONAGGREGATE-CI-SHARD-NODE"
            ),
            "b2_runtime_proof": (
                "PRELAUNCH-AND-LIVE-NETWORK-RECEIPTS-VALIDATED; FINAL-SEAL-PENDING"
                if EARLY_B2_RECEIPTS is not None
                else "NOT-RUN-IN-STEP1-AUTHORING"
            ),
            "b1a_runtime_verdict": (
                "INTERNAL-PHASES-PASS; EXTERNAL-B2-FINAL-SEAL-PENDING"
                if aggregate_phases_present and EARLY_B2_RECEIPTS is not None
                else "NOT-CLAIMED-UNTIL-EXTERNAL-B2-CLOSEOUT"
            ),
            "rss_peak_ledger": "EXTERNAL-B2-WRAPPER-REQUIRED",
            "run_root_disposition": "RETAIN EVIDENCE_DIR; NO BLANKET DELETE",
            "tracked_diff_census": "EXTERNAL-C8-CLOSEOUT-REQUIRED",
            "tracked_diff_contract": (
                "backend/tests/test_layer3_connector_vertical_loop.py"
            ),
            "schema_changed": False,
            "terminal_statement": FIXED_TERMINAL_STATEMENT,
            "status": (
                "INTERNAL-PASS-PENDING-B2-CLOSEOUT"
                if aggregate_phases_present and EARLY_B2_RECEIPTS is not None
                else "AUTHORING-CONTRACT-PASS"
                if aggregate_phases_present
                else "NODE-PASS-NONAGGREGATE"
            ),
        },
        producer_node="module-teardown",
    )

    final_files = {
        path.resolve() for path in _DEV_RUN_ROOT.rglob("*") if path.is_file()
    }
    assert all(path.is_file() for path in final_files)
    assert all(path.is_relative_to(_DEV_RUN_ROOT) for path in final_files)
    assert all(
        not path.name.endswith(("-journal", "-wal", "-shm")) for path in final_files
    )
    file_receipts = [_file_receipt(path) for path in sorted(final_files)]
    receipted_paths = {Path(receipt["path"]).resolve() for receipt in file_receipts}
    assert _REGISTERED_STORED_PATHS <= receipted_paths
    if aggregate_phases_present:
        receipted_names = {path.name for path in receipted_paths}
        assert REQUIRED_PRE_CLOSEOUT_EVIDENCE <= receipted_names
        assert {
            "row-ledger-final.json",
            "network-ledger-final.json",
            "b1a-verdict.json",
        } <= receipted_names
    _write_evidence(
        evidence_dir,
        "file-ledger-final.json",
        {
            "fixture": {"bytes": len(closeout_fixture), "sha256": FIXTURE_SHA256},
            "registered_stored_paths": sorted(
                str(path) for path in _REGISTERED_STORED_PATHS
            ),
            "storage_files": sorted(str(path) for path in storage_files),
            "run_root_files": file_receipts,
            "database_disposition": (
                "APP-ENGINE-CONNECTION-POOLS-DISPOSED; "
                "DATABASE-RECEIPTED; EXTERNAL-B2-WRAPPER-SEALS-RUN-ROOT"
            ),
            "all_live_roots_contained": True,
            "all_registered_refs_receipted": True,
            "all_five_nodes_receipted": aggregate_phases_present,
            "self_receipt": "DETACHED-BY-DESIGN",
            "status": (
                _phase_status()
                if aggregate_phases_present
                else "NODE-PASS-NONAGGREGATE"
            ),
        },
        producer_node="module-teardown",
    )


@pytest.fixture(scope="module")
def b1a_runtime() -> Iterator[_B1aRuntime]:
    previous_storage_dir = settings.storage_dir
    try:
        with _runtime_environment(), _one_isolated_app_engine() as engine:
            settings.storage_dir = str(_DESIRED_STORAGE_PATH)
            bootstrap_storage_tree(_DESIRED_STORAGE_PATH)
            Base.metadata.create_all(engine)
            runtime = _B1aRuntime(engine, _DESIRED_STORAGE_PATH)
            previous_override = app.dependency_overrides.get(get_db)
            app.dependency_overrides[get_db] = runtime.override_get_db
            try:
                with TestClient(app) as client:
                    runtime.client = client
                    try:
                        yield runtime
                    finally:
                        runtime.client = None
            finally:
                if previous_override is None:
                    app.dependency_overrides.pop(get_db, None)
                else:
                    app.dependency_overrides[get_db] = previous_override
        _finalize_closeout(runtime)
    except BaseException as exc:
        _emit_runtime_stop_receipt(
            exc,
            producer_node="b1a_runtime",
            condition="RUNTIME-FIXTURE-G6-OR-SAFETY-FAILURE",
        )
        raise
    finally:
        settings.storage_dir = previous_storage_dir


@pytest.fixture
def task7_origin_runtime(
    tmp_path: Path,
    monkeypatch,
) -> Iterator[_B1aRuntime]:
    database_path = (tmp_path / "origin.sqlite3").resolve()
    storage_dir = (tmp_path / "storage").resolve()
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
        pool_size=4,
        max_overflow=0,
    )
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    bootstrap_storage_tree(storage_dir)
    Base.metadata.create_all(engine)
    with engine.connect() as first, engine.connect() as second:
        assert (
            first.connection.dbapi_connection
            is not second.connection.dbapi_connection
        )
    runtime = _B1aRuntime(engine, storage_dir)
    try:
        yield runtime
    finally:
        assert engine.pool.checkedout() == 0
        engine.dispose()


def _row_census(db: Session) -> dict[str, int]:
    global _LAST_ROW_SNAPSHOT
    db.expire_all()
    census = {name: db.query(model).count() for name, model in CENSUS_MODELS.items()}
    _LAST_ROW_SNAPSHOT = census
    return census


def _stored_path_census(db: Session) -> list[str]:
    refs: set[str] = set()
    for model, field, relative_root in (
        (ConnectorRunTarget, "raw_storage_ref", _DESIRED_STORAGE_PATH),
        (L3ConnectorSourceIntakeRecord, "storage_ref", _DESIRED_STORAGE_PATH),
        (L3MaterialSnapshot, "payload_ref", Path(settings.artifact_storage_dir)),
        (DatasetVersion, "storage_ref", Path(settings.dataset_storage_dir)),
        (AnalysisArtifact, "storage_ref", Path(settings.artifact_storage_dir)),
    ):
        for row in db.query(model).all():
            value = getattr(row, field, None)
            if value:
                path = Path(str(value))
                resolved = (
                    path.resolve()
                    if path.is_absolute()
                    else (relative_root / path).resolve()
                )
                _register_stored_path(resolved)
                refs.add(str(value))
    return sorted(refs)


def _seed_downloaded_target(
    db: Session,
    runtime: _B1aRuntime,
    *,
    stem: str,
) -> tuple[ConnectorRun, ConnectorRunTarget]:
    raw_dir = runtime.storage_dir / "connectors/raw" / stem
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "water-quality.csv"
    raw_path.write_bytes(FIXTURE_BYTES)
    _register_stored_path(raw_path)
    run = ConnectorRun(
        connector_run_id=f"{stem}-run",
        connector_key="sciencebase_public",
        source_system="sciencebase",
        source_mode="public_api",
        status="running",
    )
    target = ConnectorRunTarget(
        connector_run_target_id=f"{stem}-target",
        connector_run_id=run.connector_run_id,
        ordinal=1,
        sciencebase_item_id="synthetic-sb-item-001",
        sciencebase_item_url="https://www.sciencebase.gov/catalog/item/synthetic-sb-item-001",
        sciencebase_file_name="water-quality.csv",
        sciencebase_download_uri="https://www.sciencebase.gov/catalog/file/get/synthetic-sb-item-001",
        artifact_surface="files",
        artifact_locator_type="download_uri",
        source_artifact_key="sciencebase://synthetic-sb-item-001/water-quality.csv",
        downloaded_sha256=FIXTURE_SHA256,
        raw_storage_ref=str(raw_path.resolve()),
        public_read_confirmed=True,
        status="downloaded",
    )
    db.add_all([run, target])
    db.commit()
    return run, target


def _intake_arguments(
    run: ConnectorRun, target: ConnectorRunTarget, *, stem: str
) -> dict[str, Any]:
    return {
        "client_request_id": f"{stem}-intake",
        "connector_key": run.connector_key,
        "connector_run_id": run.connector_run_id,
        "connector_run_target_id": target.connector_run_target_id,
        "source_label": "Synthetic C01 ScienceBase-family CSV",
        "source_description": "Offline synthetic fixture; not official ScienceBase or USGS data.",
        "media_type": "text/csv",
        "freshness_timestamp": "2026-07-10T00:00:00+00:00",
    }


def _record_and_preview(
    db: Session,
    run: ConnectorRun,
    target: ConnectorRunTarget,
    *,
    stem: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    arguments = _intake_arguments(run, target, stem=stem)
    record = record_connector_produced_source_intake(db, **arguments)
    preview = connector_source_intake_material_preview(
        db,
        connector_source_intake_record_id=record["connector_source_intake_record_id"],
    )
    return record, preview, arguments


def _decision_basis(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_ref": candidate["source_ref"],
        "query_basis": candidate["query_basis"],
        "provenance_ref": candidate["provenance_ref"],
        "source_identity": copy.deepcopy(candidate["source_identity"]),
        "source_provenance": copy.deepcopy(candidate["source_provenance"]),
        "payload": copy.deepcopy(candidate["payload"]),
        "load_summary": copy.deepcopy(candidate["load_summary"]),
        "connector_target": {
            "connector_run_target_id": candidate["payload"]["connector_run_target_id"],
            "connector_key": "sciencebase_public",
        },
    }


def _gate_b_payload(
    preview: dict[str, Any],
    *,
    stem: str,
    decision: str = "approved",
    operator_reason: str = "",
) -> dict[str, Any]:
    candidate = preview["material_candidate"]
    return {
        "client_request_id": f"{stem}-gate-b",
        "preflight_id": f"{stem}-preflight",
        "source_set_id": f"{stem}-source-set",
        "material_preview_id": preview["material_preview_id"],
        "material_preview_hash": preview["material_preview_hash"],
        "candidate_decisions": [
            {
                "candidate_id": candidate["candidate_id"],
                "decision": decision,
                "operator_reason": operator_reason,
                "decision_basis": _decision_basis(candidate),
            }
        ],
        "actor": "pytest-b1a",
    }


def _assert_no_gate_or_downstream(census: dict[str, int]) -> None:
    assert census["L3ConnectorSourceIntakeRecord"] == 1
    for name in (
        "L3GateBIdempotencyKey",
        "L3Session",
        "L3SelectionManifest",
        "L3Descriptor",
        "L3RetrievalEvent",
        "L3MaterialSnapshot",
        "L3TypingRecord",
        "L3AnalysisUnit",
        "L3AnalysisGroup",
        "L3AnalysisSet",
        "L3AnalysisPlan",
        "L3PassRun",
        "AnalysisRun",
        "AnalysisArtifact",
        "L3ReconciliationRecord",
        "L3OutputPackage",
        "DatasetSourceProvenance",
    ):
        assert census[name] == 0, name


def _negative_evidence(
    *,
    case_id: str,
    name: str,
    expected_symbol: str,
    material_preview_hash: str,
    request_or_arguments: dict[str, Any],
    result: dict[str, Any],
    before: dict[str, int],
    after: dict[str, int],
    stored_paths: list[str],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "name": name,
        "authority_sha": AUTHORITY_SHA,
        "fixture_sha256": FIXTURE_SHA256,
        "material_preview_hash": material_preview_hash,
        "request_or_arguments": request_or_arguments,
        "result": result,
        "expected_symbol": expected_symbol,
        "before_row_census": before,
        "after_row_census": after,
        "stored_paths": stored_paths,
        "network_ledger": _network_evidence(),
        "status": _phase_status(),
    }


def _exercise_replay_matrix(
    db: Session,
    runtime: _B1aRuntime,
    *,
    stem: str,
) -> dict[str, Any]:
    assert runtime.client is not None
    run, target = _seed_downloaded_target(db, runtime, stem=stem)
    _record, preview, intake_arguments = _record_and_preview(
        db,
        run,
        target,
        stem=stem,
    )
    intake_baseline = _row_census(db)

    with pytest.raises(ConnectorSourceIntakeError) as exact_error:
        record_connector_produced_source_intake(db, **intake_arguments)
    assert exact_error.value.http_status == 409
    assert exact_error.value.code == "connector_source_intake_idempotency_conflict"
    intake_after_exact = _row_census(db)
    assert intake_after_exact == intake_baseline

    changed_intake_arguments = {
        **intake_arguments,
        "freshness_timestamp": "2026-07-11T00:00:00+00:00",
    }
    with pytest.raises(ConnectorSourceIntakeError) as changed_error:
        record_connector_produced_source_intake(db, **changed_intake_arguments)
    assert changed_error.value.http_status == 409
    assert changed_error.value.code == "connector_source_intake_idempotency_conflict"
    intake_after_changed = _row_census(db)
    assert intake_after_changed == intake_baseline

    gate_payload = _gate_b_payload(preview, stem=stem)
    committed = runtime.client.post("/api/v1/layer3/gate-b/decision", json=gate_payload)
    assert committed.status_code == 200, committed.text
    assert committed.json()["status"] == "ok"
    committed_census = _row_census(db)

    exact_gate = runtime.client.post(
        "/api/v1/layer3/gate-b/decision", json=gate_payload
    )
    assert exact_gate.status_code == 200, exact_gate.text
    assert exact_gate.json()["status"] == "already_committed"
    gate_after_exact = _row_census(db)
    assert gate_after_exact == committed_census

    changed_source_payload = copy.deepcopy(gate_payload)
    changed_source_payload["source_set_id"] = f"{stem}-changed-source-set"
    changed_source = runtime.client.post(
        "/api/v1/layer3/gate-b/decision",
        json=changed_source_payload,
    )
    assert changed_source.status_code == 409, changed_source.text
    assert changed_source.json()["status"] == "conflict"
    assert changed_source.json()["error_code"] == "idempotency_conflict"
    gate_after_changed_source = _row_census(db)
    assert gate_after_changed_source == committed_census

    changed_decision_payload = copy.deepcopy(gate_payload)
    changed_decision_payload["candidate_decisions"][0]["decision"] = "denied"
    changed_decision_payload["candidate_decisions"][0]["operator_reason"] = (
        "Changed after the committed approval."
    )
    changed_decision = runtime.client.post(
        "/api/v1/layer3/gate-b/decision",
        json=changed_decision_payload,
    )
    assert changed_decision.status_code == 409, changed_decision.text
    assert changed_decision.json()["status"] == "conflict"
    assert changed_decision.json()["error_code"] == "idempotency_conflict"
    gate_after_changed_decision = _row_census(db)
    assert gate_after_changed_decision == committed_census

    matrix = [
        {
            "seam": "connector_intake",
            "variant": "exact",
            "http_status": exact_error.value.http_status,
            "symbol": exact_error.value.code,
        },
        {
            "seam": "connector_intake",
            "variant": "changed",
            "http_status": changed_error.value.http_status,
            "symbol": changed_error.value.code,
        },
        {
            "seam": "gate_b",
            "variant": "exact",
            "http_status": exact_gate.status_code,
            "symbol": exact_gate.json()["status"],
        },
        {
            "seam": "gate_b",
            "variant": "changed",
            "http_status": changed_source.status_code,
            "symbol": changed_source.json()["error_code"],
        },
    ]
    assert matrix == [
        {
            "seam": "connector_intake",
            "variant": "exact",
            "http_status": 409,
            "symbol": "connector_source_intake_idempotency_conflict",
        },
        {
            "seam": "connector_intake",
            "variant": "changed",
            "http_status": 409,
            "symbol": "connector_source_intake_idempotency_conflict",
        },
        {
            "seam": "gate_b",
            "variant": "exact",
            "http_status": 200,
            "symbol": "already_committed",
        },
        {
            "seam": "gate_b",
            "variant": "changed",
            "http_status": 409,
            "symbol": "idempotency_conflict",
        },
    ]
    assert committed_census["L3ConnectorSourceIntakeRecord"] == 1
    for name in (
        "L3GateBIdempotencyKey",
        "L3Session",
        "L3SelectionManifest",
        "L3Descriptor",
        "L3RetrievalEvent",
        "L3MaterialSnapshot",
    ):
        assert committed_census[name] == 1, name
    for name in (
        "DatasetSourceProvenance",
        "L3TypingRecord",
        "L3AnalysisUnit",
        "L3AnalysisGroup",
        "L3AnalysisSet",
        "L3AnalysisPlan",
        "L3PassRun",
        "AnalysisRun",
        "AnalysisArtifact",
        "L3ReconciliationRecord",
        "L3OutputPackage",
    ):
        assert committed_census[name] == 0, name
    return {
        "authority_sha": AUTHORITY_SHA,
        "fixture_sha256": FIXTURE_SHA256,
        "material_preview_hash": preview["material_preview_hash"],
        "matrix": matrix,
        "intake_arguments": {
            "exact": intake_arguments,
            "changed": changed_intake_arguments,
        },
        "intake_direct_exceptions": {
            "exact": {
                "exception_class": type(exact_error.value).__name__,
                "http_status": exact_error.value.http_status,
                "code": exact_error.value.code,
            },
            "changed": {
                "exception_class": type(changed_error.value).__name__,
                "http_status": changed_error.value.http_status,
                "code": changed_error.value.code,
            },
        },
        "gate_b_requests": {
            "committed_and_exact": gate_payload,
            "changed_source": changed_source_payload,
            "changed_decision": changed_decision_payload,
        },
        "gate_b_responses": {
            "committed": {
                "http_status": committed.status_code,
                "body": committed.json(),
            },
            "exact": {
                "http_status": exact_gate.status_code,
                "body": exact_gate.json(),
            },
            "changed_source": {
                "http_status": changed_source.status_code,
                "body": changed_source.json(),
            },
            "changed_decision": {
                "http_status": changed_decision.status_code,
                "body": changed_decision.json(),
            },
        },
        "row_censuses": {
            "intake_before_replay": intake_baseline,
            "intake_after_exact": intake_after_exact,
            "intake_after_changed": intake_after_changed,
            "gate_b_committed": committed_census,
            "gate_b_after_exact": gate_after_exact,
            "gate_b_after_changed_source": gate_after_changed_source,
            "gate_b_after_changed_decision": gate_after_changed_decision,
        },
        "changed_gate_b_probes": [
            {
                "axis": "source_set_id",
                "http_status": changed_source.status_code,
                "body": changed_source.json(),
            },
            {
                "axis": "candidate_decisions",
                "http_status": changed_decision.status_code,
                "body": changed_decision.json(),
            },
        ],
        "final_row_census": committed_census,
        "stored_paths": _stored_path_census(db),
        "cross_seam_unification": "UNDECIDED/NOT-CLAIMED",
        "network_ledger": _network_evidence(),
        "status": _phase_status(),
    }


@_stop_receipt_on_failure
def test_b1a_b2_receipt_and_fixture_assertions(tmp_path: Path) -> None:
    evidence_dir = _evidence_dir(tmp_path)
    if EARLY_B2_RECEIPTS is None:
        _assert_socket_guard_loopback_contract()
    assert len(FIXTURE_BYTES) == 34
    assert _sha256_bytes(FIXTURE_BYTES) == FIXTURE_SHA256
    assert _git_blob_sha1(FIXTURE_BYTES) == FIXTURE_PAYLOAD_GIT_BLOB
    source_authority_path = (
        _WORKTREE_ROOT / "backend/tests/test_layer3_connector_source_intake_pilot.py"
    )
    source_authority_bytes = source_authority_path.read_bytes()
    source_authority_git_bytes = source_authority_bytes.replace(b"\r\n", b"\n")
    assert b"\r" not in source_authority_git_bytes
    source_file_git_blob = _git_blob_sha1(source_authority_git_bytes)
    if EARLY_EXTERNAL_SEAL_RECEIPTS is not None:
        assert source_file_git_blob == FIXTURE_SOURCE_FILE_GIT_BLOB
    for expected_size, expected_sha in EXPECTED_SEALS.values():
        assert expected_size > 0
        assert len(expected_sha) == 64
        assert set(expected_sha) <= set("0123456789abcdef")

    paths = _chain_paths()
    child_manifest_source_entry: dict[str, Any] | None = None
    if paths is None:
        execution_scope = "authoring-contract-only"
        assert EARLY_EXTERNAL_SEAL_RECEIPTS is None
        seal_receipts: dict[str, dict[str, Any]] = {}
        fixture_source = None
        source_bytes = FIXTURE_BYTES
    else:
        execution_scope = "local-external-seal-rehash"
        assert EARLY_EXTERNAL_SEAL_RECEIPTS is not None
        freeze_names = sorted(
            path.name for path in paths["freeze_manifest"].parent.iterdir()
        )
        assert freeze_names == ["aggregate-rows.txt", "manifest-v1.json"]
        seal_receipts = {
            name: _assert_file_seal(paths[name], EXPECTED_SEALS[name])
            for name in EXPECTED_SEALS
        }
        child_manifest = json.loads(paths["child_manifest"].read_text(encoding="utf-8"))
        child_manifest_source_entry = next(
            entry
            for entry in child_manifest["entries"]
            if entry["id"] == "ct4b-bound-fixture-bytes"
        )
        assert child_manifest_source_entry == {
            "id": "ct4b-bound-fixture-bytes",
            "path": "C:/p6fixtures/sciencebase-v1/water-quality.csv",
            "path_class": "absolute_local_outside_repo_and_onedrive",
            "bytes": 34,
            "sha256": FIXTURE_SHA256,
            "read_only": True,
            "candidate_id": "C01",
            "source_locator": (
                "backend/tests/test_layer3_connector_source_intake_pilot.py:90@"
                + AUTHORITY_SHA
            ),
            "source_blob": source_file_git_blob,
        }
        assert {
            name: (receipt["bytes"], receipt["sha256"])
            for name, receipt in EARLY_EXTERNAL_SEAL_RECEIPTS.items()
        } == EXPECTED_SEALS
        fixture_source = paths["fixture"]
        source_stat = fixture_source.stat()
        file_attributes = int(getattr(source_stat, "st_file_attributes", 0))
        if os.name == "nt":
            assert file_attributes & stat.FILE_ATTRIBUTE_READONLY
            assert not file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
        first_read = fixture_source.read_bytes()
        second_read = fixture_source.read_bytes()
        assert first_read == second_read == FIXTURE_BYTES
        source_bytes = first_read

    source_hash_before = _sha256_bytes(source_bytes)
    connector_raw_dir = _DESIRED_STORAGE_PATH / "connectors/raw/b1a-c01"
    connector_raw_dir.mkdir(parents=True, exist_ok=True)
    copied_fixture = connector_raw_dir / "water-quality.csv"
    copied_fixture.write_bytes(source_bytes)
    _register_stored_path(copied_fixture)
    assert copied_fixture.read_bytes() == source_bytes
    assert _sha256_bytes(copied_fixture.read_bytes()) == FIXTURE_SHA256
    if fixture_source is not None:
        assert _sha256_bytes(fixture_source.read_bytes()) == source_hash_before

    _write_evidence(
        evidence_dir,
        "p1-authoring-seals.json",
        {
            "authority_sha": AUTHORITY_SHA,
            "execution_scope": execution_scope,
            "pre_app_import_external_rehash": EARLY_EXTERNAL_SEAL_RECEIPTS is not None,
            "seal_receipts": seal_receipts,
            "declared_seal_contract": {
                name: {"bytes": size, "sha256": digest}
                for name, (size, digest) in EXPECTED_SEALS.items()
            },
            "b2_receipts_validated_before_app_import": EARLY_B2_RECEIPTS is not None,
            "b2_receipt_names": list(B2_RECEIPT_NAMES),
            "b2_wrapper_status": (
                "PASS-TO-LAUNCH"
                if EARLY_B2_RECEIPTS is not None
                else "NOT-RUN-IN-STEP1-AUTHORING"
            ),
            "status": (
                "PASS" if EARLY_B2_RECEIPTS is not None else "AUTHORING-CONTRACT-PASS"
            ),
        },
    )
    _write_evidence(
        evidence_dir,
        "fixture-c01.json",
        {
            "candidate": "C01",
            "bytes": len(source_bytes),
            "sha256_read_1": source_hash_before,
            "sha256_read_2": _sha256_bytes(source_bytes),
            "source_file_git_blob": source_file_git_blob,
            "source_authority_path": str(source_authority_path),
            "source_git_text_normalization": "CRLF-to-LF",
            "child_manifest_source_entry": child_manifest_source_entry,
            "payload_git_blob": _git_blob_sha1(source_bytes),
            "source_read_only": bool(
                fixture_source is not None
                and os.name == "nt"
                and int(getattr(fixture_source.stat(), "st_file_attributes", 0))
                & stat.FILE_ATTRIBUTE_READONLY
            ),
            "source_no_reparse": (
                None
                if fixture_source is None or os.name != "nt"
                else not bool(
                    int(getattr(fixture_source.stat(), "st_file_attributes", 0))
                    & stat.FILE_ATTRIBUTE_REPARSE_POINT
                )
            ),
            "status": _phase_status(),
        },
    )
    _write_evidence(
        evidence_dir,
        "fixture-copy.json",
        {
            "source_sha256": source_hash_before,
            "destination": str(copied_fixture),
            "destination_sha256": _sha256_bytes(copied_fixture.read_bytes()),
            "source_untouched": True,
            "status": _phase_status(),
        },
    )


@_stop_receipt_on_failure
def test_b1a_connector_gate_b_positive_and_eight_negatives(
    b1a_runtime: _B1aRuntime,
    tmp_path: Path,
) -> None:
    assert b1a_runtime.client is not None
    evidence_dir = _evidence_dir(tmp_path)

    with b1a_runtime.scenario() as db:
        run, target = _seed_downloaded_target(db, b1a_runtime, stem="b1a-positive")
        record, preview, intake_arguments = _record_and_preview(
            db,
            run,
            target,
            stem="b1a-positive",
        )
        before_gate = _row_census(db)
        assert before_gate["ConnectorRun"] == 1
        assert before_gate["ConnectorRunTarget"] == 1
        assert before_gate["L3ConnectorSourceIntakeRecord"] == 1
        _assert_no_gate_or_downstream(before_gate)
        payload = _gate_b_payload(preview, stem="b1a-positive")
        response = b1a_runtime.client.post(
            "/api/v1/layer3/gate-b/decision",
            json=payload,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "ok"
        assert body["next_state"] == "connector_source_intake_gate_b_admitted"
        assert body["authority_rail"]["current_gate"] == "gate_b"
        positive_census = _row_census(db)
        for name in (
            "L3GateBIdempotencyKey",
            "L3Session",
            "L3SelectionManifest",
            "L3Descriptor",
            "L3RetrievalEvent",
            "L3MaterialSnapshot",
        ):
            assert positive_census[name] == 1, name
        for name in (
            "DatasetSourceProvenance",
            "L3TypingRecord",
            "L3AnalysisUnit",
            "L3AnalysisGroup",
            "L3AnalysisSet",
        ):
            assert positive_census[name] == 0, name
        _write_evidence(
            evidence_dir,
            "b1a-positive-gate-b.json",
            {
                "authority_sha": AUTHORITY_SHA,
                "connector_key": "sciencebase_public",
                "route_slug_not_used_as_connector_key": "sciencebase-public",
                "source_mode": "public_api",
                "target_status": target.status,
                "public_read_confirmed": target.public_read_confirmed,
                "official_public_read_evidence": False,
                "f20": "NOT ESTABLISHED FOR THESE BYTES",
                "intake_arguments": intake_arguments,
                "intake_record": record,
                "material_preview_hash": preview["material_preview_hash"],
                "request": payload,
                "response": body,
                "row_census": positive_census,
                "network_ledger": _network_evidence(),
                "connector_material_reached_dataset_version": False,
                "status": _phase_status(),
            },
        )

    cases: list[dict[str, Any]] = []
    route_specs = [
        (
            "N01",
            "denied",
            "denied",
            "Not approved for this tranche.",
            400,
            "blocked",
            "no_approved_material",
            [],
        ),
        (
            "N02",
            "isolated",
            "isolated",
            "Isolated for this tranche.",
            400,
            "blocked",
            "no_approved_material",
            [],
        ),
        (
            "N04",
            "stale",
            "approved",
            "",
            409,
            "conflict",
            "material_preview_mismatch",
            ["material_preview_hash", "candidate_decisions"],
        ),
        (
            "N05",
            "duplicate",
            "approved",
            "",
            400,
            "invalid",
            "duplicate_material_candidate_decision",
            ["candidate_decisions.candidate_id"],
        ),
        (
            "N06",
            "missing-provenance",
            "approved",
            "",
            409,
            "conflict",
            "connector_source_intake_gate_b_provenance_ref_mismatch",
            ["candidate_decisions.decision_basis.provenance_ref"],
        ),
        (
            "N07",
            "malformed",
            "malformed",
            "",
            400,
            "invalid",
            "invalid_material_candidate",
            [],
        ),
    ]
    for (
        case_id,
        case_name,
        decision,
        reason,
        http_status,
        status,
        symbol,
        expected_blocked_fields,
    ) in route_specs:
        with b1a_runtime.scenario() as db:
            stem = f"b1a-{case_id.lower()}"
            run, target = _seed_downloaded_target(db, b1a_runtime, stem=stem)
            _record, preview, _arguments = _record_and_preview(
                db, run, target, stem=stem
            )
            before = _row_census(db)
            payload = _gate_b_payload(
                preview,
                stem=stem,
                decision=decision,
                operator_reason=reason,
            )
            if case_id == "N04":
                payload["material_preview_hash"] = "0" * 64
            elif case_id == "N05":
                payload["candidate_decisions"].append(
                    copy.deepcopy(payload["candidate_decisions"][0])
                )
            elif case_id == "N06":
                del payload["candidate_decisions"][0]["decision_basis"][
                    "provenance_ref"
                ]
            response = b1a_runtime.client.post(
                "/api/v1/layer3/gate-b/decision",
                json=payload,
            )
            assert response.status_code == http_status, response.text
            response_body = response.json()
            assert response_body["status"] == status
            assert response_body["error_code"] == symbol
            assert response_body["blocked_fields"] == expected_blocked_fields
            after = _row_census(db)
            assert after == before
            _assert_no_gate_or_downstream(after)
            evidence = _negative_evidence(
                case_id=case_id,
                name=case_name,
                expected_symbol=symbol,
                material_preview_hash=preview["material_preview_hash"],
                request_or_arguments=payload,
                result={"http_status": response.status_code, "body": response_body},
                before=before,
                after=after,
                stored_paths=_stored_path_census(db),
            )
            _write_evidence(
                evidence_dir,
                f"negative-{int(case_id[1:]):02d}-{case_name}.json",
                evidence,
            )
            cases.append(evidence)

    with b1a_runtime.scenario() as db:
        stem = "b1a-n03"
        run, target = _seed_downloaded_target(db, b1a_runtime, stem=stem)
        _record, preview, _arguments = _record_and_preview(db, run, target, stem=stem)
        before = _row_census(db)
        base_payload = _gate_b_payload(preview, stem=stem)
        omitted_payload = copy.deepcopy(base_payload)
        del omitted_payload["candidate_decisions"][0]["decision"]
        omitted = b1a_runtime.client.post(
            "/api/v1/layer3/gate-b/decision",
            json=omitted_payload,
        )
        assert omitted.status_code == 422
        assert "error_code" not in omitted.json()
        null_payload = copy.deepcopy(base_payload)
        null_payload["candidate_decisions"][0]["decision"] = None
        null_response = b1a_runtime.client.post(
            "/api/v1/layer3/gate-b/decision",
            json=null_payload,
        )
        assert null_response.status_code == 422
        assert "error_code" not in null_response.json()
        direct_payload = copy.deepcopy(base_payload)
        direct_payload["candidate_decisions"][0]["decision"] = ""
        with pytest.raises(Layer3WorkbenchError) as direct_error:
            gate_b_decision(db, direct_payload)
        assert direct_error.value.http_status == 400
        assert direct_error.value.status == "invalid"
        assert direct_error.value.error_code == "invalid_material_candidate"
        after = _row_census(db)
        assert after == before
        _assert_no_gate_or_downstream(after)
        n03_evidence = _negative_evidence(
            case_id="N03",
            name="null-unreviewed",
            expected_symbol="route-422/direct-invalid_material_candidate",
            material_preview_hash=preview["material_preview_hash"],
            request_or_arguments={
                "omitted": omitted_payload,
                "null": null_payload,
                "direct_blank": direct_payload,
            },
            result={
                "omitted_http_status": omitted.status_code,
                "omitted_body": omitted.json(),
                "null_http_status": null_response.status_code,
                "null_body": null_response.json(),
                "direct": {
                    "exception_class": type(direct_error.value).__name__,
                    "http_status": direct_error.value.http_status,
                    "status": direct_error.value.status,
                    "error_code": direct_error.value.error_code,
                },
            },
            before=before,
            after=after,
            stored_paths=_stored_path_census(db),
        )
        _write_evidence(evidence_dir, "negative-03-null-unreviewed.json", n03_evidence)
        cases.append(n03_evidence)

    with b1a_runtime.scenario() as db:
        n08_replay = _exercise_replay_matrix(db, b1a_runtime, stem="b1a-n08")
        n08_evidence = {
            "case_id": "N08",
            "name": "replay-conflict",
            "expected_symbol": "seam-specific-replay-matrix",
            **n08_replay,
        }
        _write_evidence(evidence_dir, "negative-08-replay-conflict.json", n08_evidence)
        cases.append(n08_evidence)

    assert {case["case_id"] for case in cases} == {
        "N01",
        "N02",
        "N03",
        "N04",
        "N05",
        "N06",
        "N07",
        "N08",
    }
    assert all(case["status"] == _phase_status() for case in cases)
    _write_evidence(
        evidence_dir,
        "negative-battery-summary.json",
        {
            "authority_sha": AUTHORITY_SHA,
            "case_ids": sorted(case["case_id"] for case in cases),
            "pass_count": 8,
            "network_ledger": _network_evidence(),
            "status": _phase_status(),
        },
    )


@_stop_receipt_on_failure
def test_b1a_dual_seam_replay_matrix(
    b1a_runtime: _B1aRuntime,
    tmp_path: Path,
) -> None:
    evidence_dir = _evidence_dir(tmp_path)
    with b1a_runtime.scenario() as db:
        evidence = _exercise_replay_matrix(
            db,
            b1a_runtime,
            stem="b1a-p5-replay",
        )
        assert evidence["cross_seam_unification"] == "UNDECIDED/NOT-CLAIMED"
        assert evidence["matrix"][0]["http_status"] == 409
        assert evidence["matrix"][1]["http_status"] == 409
        assert evidence["matrix"][2]["symbol"] == "already_committed"
        assert evidence["matrix"][3]["symbol"] == "idempotency_conflict"
        _write_evidence(evidence_dir, "dual-seam-replay.json", evidence)


def _analysis_artifact_payload(db: Session, analysis_run_id: str) -> dict[str, Any]:
    artifact = (
        db.query(AnalysisArtifact)
        .filter(AnalysisArtifact.analysis_run_id == analysis_run_id)
        .one()
    )
    assert artifact.artifact_type == "descriptive_summary_result"
    path = Path(settings.artifact_storage_dir) / Path(artifact.storage_ref).name
    assert path.is_file()
    _register_stored_path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _analysis_checks(db: Session, analysis_run_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(AssumptionCheck)
        .filter(AssumptionCheck.analysis_run_id == analysis_run_id)
        .order_by(AssumptionCheck.assumption_name.asc())
        .all()
    )
    return [
        {
            "name": row.assumption_name,
            "method": row.check_method,
            "result": row.check_result,
            "severity": row.severity,
            "notes": row.notes,
        }
        for row in rows
    ]


def _analysis_caveats(db: Session, analysis_run_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(CaveatNote)
        .filter(CaveatNote.analysis_run_id == analysis_run_id)
        .order_by(CaveatNote.caveat_type.asc())
        .all()
    )
    return [
        {
            "type": row.caveat_type,
            "severity": row.severity,
            "message": row.message,
        }
        for row in rows
    ]


@_stop_receipt_on_failure
def test_b1a_descriptive_summary_component_determinism(
    b1a_runtime: _B1aRuntime,
    tmp_path: Path,
) -> None:
    evidence_dir = _evidence_dir(tmp_path)
    with b1a_runtime.scenario() as db:
        ingest_result = ingest_csv_bytes_to_dataset(
            db,
            filename="water-quality.csv",
            content=FIXTURE_BYTES,
            name="B1a standalone C01 component",
            description=(
                "Standalone COMPONENT proof; explicitly not connector approval lineage."
            ),
            domain_pack=None,
            primary_time_column=None,
            source_name="b1a_component",
            source_category="component",
            source_notes="CT4B-C01-DESC-001; connector_lineage=false",
        )
        dataset_version_id = str(ingest_result["dataset_version_id"])
        version = db.get(DatasetVersion, dataset_version_id)
        assert version is not None
        assert version.version_type == "raw"
        assert version.content_hash == FIXTURE_SHA256
        _register_stored_path(Path(version.storage_ref))
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        assert db.query(L3ConnectorSourceIntakeRecord).count() == 0
        assert db.query(DatasetSourceProvenance).count() == 0

        first_run = run_analysis(
            db,
            dataset_version_id,
            "descriptive_summary",
            None,
            {},
            None,
        )
        second_run = run_analysis(
            db,
            dataset_version_id,
            "descriptive_summary",
            None,
            {},
            None,
        )
        first_payload = _analysis_artifact_payload(db, first_run.analysis_run_id)
        second_payload = _analysis_artifact_payload(db, second_run.analysis_run_id)
        first_checks = _analysis_checks(db, first_run.analysis_run_id)
        second_checks = _analysis_checks(db, second_run.analysis_run_id)
        first_caveats = _analysis_caveats(db, first_run.analysis_run_id)
        second_caveats = _analysis_caveats(db, second_run.analysis_run_id)

        assert first_payload == second_payload
        assert first_checks == second_checks
        assert first_caveats == second_caveats
        assert [item["name"] for item in first_checks] == [
            "column_classification",
            "data_availability",
            "missingness_scan",
            "time_column_coverage",
        ]
        assert [item["type"] for item in first_caveats] == [
            "non_time_series_interpretation"
        ]

        stats = first_payload["summary_stats"]
        assert stats == {
            "row_count": 2,
            "column_count": 2,
            "numeric_column_count": 1,
            "categorical_column_count": 1,
            "boolean_column_count": 0,
            "time_column_count": 0,
            "missing_cell_count": 0,
            "missing_fraction": 0.0,
        }
        site = first_payload["columns"]["site_id"]
        assert site["inferred_class"] == "categorical"
        assert site["non_null_count"] == 2
        assert site["missing_count"] == 0
        assert site["unique_count"] == 2
        assert site["top_values"] == [
            {"value": "SB-001", "count": 1},
            {"value": "SB-002", "count": 1},
        ]
        value = first_payload["columns"]["value"]
        assert value["inferred_class"] == "numeric"
        assert value["non_null_count"] == 2
        assert value["missing_count"] == 0
        numeric = value["numeric_summary"]
        assert numeric["min"] == pytest.approx(42.0, rel=1e-12, abs=1e-12)
        assert numeric["max"] == pytest.approx(43.0, rel=1e-12, abs=1e-12)
        assert numeric["mean"] == pytest.approx(42.5, rel=1e-12, abs=1e-12)
        assert numeric["median"] == pytest.approx(42.5, rel=1e-12, abs=1e-12)
        assert numeric["std_dev"] == pytest.approx(
            0.7071067811865476,
            rel=1e-12,
            abs=1e-12,
        )
        assert value["top_values"] == [
            {"value": 42, "count": 1},
            {"value": 43, "count": 1},
        ]

        census = _row_census(db)
        expected_component_counts = {
            "SourceConnector": 1,
            "Dataset": 1,
            "DatasetVersion": 1,
            "VariableDefinition": 2,
            "DatasetRow": 0,
            "DatasetSourceProvenance": 0,
            "AnalysisRun": 2,
            "AssumptionCheck": 8,
            "CaveatNote": 2,
            "AnalysisArtifact": 2,
        }
        for name, expected in expected_component_counts.items():
            assert census[name] == expected, name

        common_nonclaim = {
            "component_classification": "COMPONENT DatasetVersion",
            "connector_lineage": False,
            "question_id": "CT4B-C01-DESC-001",
            "method": "descriptive_summary",
            "parameters": {},
            "c6_degenerate_n_rail": C6_DEGENERATE_N_RAIL,
            "official_causal_population_inference": False,
        }
        _write_evidence(
            evidence_dir,
            "descriptive-run-1.json",
            {
                **common_nonclaim,
                "analysis_run_id": first_run.analysis_run_id,
                "payload": first_payload,
                "checks": first_checks,
                "caveats": first_caveats,
                "status": _phase_status(),
            },
        )
        _write_evidence(
            evidence_dir,
            "descriptive-run-2.json",
            {
                **common_nonclaim,
                "analysis_run_id": second_run.analysis_run_id,
                "payload": second_payload,
                "checks": second_checks,
                "caveats": second_caveats,
                "status": _phase_status(),
            },
        )
        _write_evidence(
            evidence_dir,
            "descriptive-determinism.json",
            {
                **common_nonclaim,
                "float_tolerance": {"absolute": 1e-12, "relative": 1e-12},
                "mean": 42.5,
                "sample_standard_deviation": 0.7071067811865476,
                "substantive_payloads_equal": True,
                "checks_equal": True,
                "caveats_equal": True,
                "row_census": census,
                "status": _phase_status(),
            },
        )
        _write_evidence(
            evidence_dir,
            "component-nonclaim.json",
            {
                **common_nonclaim,
                "connector_approval_ids_attached": False,
                "integrated_loop_proven": False,
                "terminal_statement": FIXED_TERMINAL_STATEMENT,
                "status": _phase_status(),
            },
        )


_DOWNSTREAM_ORIGIN_BOUNDARIES = (
    "execution_output",
    "result_review",
    "package_commit",
    "package_submit",
    "handoff_prepare",
)


def _register_origin_test_path(
    path: Path,
    runtime: _B1aRuntime,
) -> Path:
    resolved = path.resolve()
    if resolved.is_relative_to(_DESIRED_STORAGE_PATH):
        return _register_stored_path(resolved)
    assert resolved.is_relative_to(runtime.storage_dir)
    assert resolved.is_file()
    return resolved


def _commit_origin_test_session(
    db: Session,
    runtime: _B1aRuntime,
    *,
    session_id: str,
    source_class: str,
    decision_item: dict[str, Any],
    snapshot_identity: dict[str, Any],
    snapshot_provenance: dict[str, Any],
    snapshot_payload: dict[str, Any],
    include_snapshot: bool = True,
) -> tuple[L3Session, L3MaterialSnapshot | None]:
    manifest_id = f"{session_id}-manifest"
    descriptor_id = f"{session_id}-descriptor"
    payload_bytes = json.dumps(
        snapshot_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    assert Path(settings.artifact_storage_dir) == runtime.storage_dir / "artifacts"
    payload_path = (
        Path(settings.artifact_storage_dir)
        / "layer3"
        / session_id
        / f"{payload_hash}.json"
    )
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_bytes(payload_bytes)
    _register_origin_test_path(payload_path, runtime)
    normalized_decision = copy.deepcopy(decision_item)
    normalized_decision["material_preview_basis"] = (
        gate_b_state.material_candidate_basis_from_decision(
            candidate_id=normalized_decision["candidate_id"],
            source_class=normalized_decision["source_class"],
            decision_basis=normalized_decision["decision_basis"],
        )
    )
    decision_manifest = gate_b_state.candidate_decision_manifest(
        [normalized_decision]
    )
    decision_manifest_id = gate_b_state.gate_b_decision_manifest_id(
        decision_manifest
    )
    descriptor_selector = gate_b_state.gate_b_descriptor_selector(
        normalized_decision
    )
    material_preview_hash = gate_b_state.material_preview_hash(
        [normalized_decision["material_preview_basis"]]
    )
    client_request_id = f"{session_id}-gate-b"
    preflight_id = f"{session_id}-preflight"
    source_set_id = f"{session_id}-source-set"
    material_preview_id = f"{session_id}-preview"
    idempotency_record = gate_b_state.gate_b_idempotency_record(
        client_request_id=client_request_id,
        preflight_id=preflight_id,
        source_set_id=source_set_id,
        material_preview_id=material_preview_id,
        material_preview_hash=material_preview_hash,
        gate_b_decision_manifest_id=decision_manifest_id,
    )
    manifest_json = {
        "items": [
            {
                "source_plane": f"plane-{source_class}",
                "descriptor_type": source_class,
                "selector_payload": copy.deepcopy(descriptor_selector),
                "selection_basis": {"gate_b_decision": "approved"},
                "expansion_reason": "gate_b_approved_material",
            }
        ]
    }
    source_plane_hints = {"source_classes": [source_class]}
    session = L3Session(
        session_id=session_id,
        status="completed",
        selection_manifest_id=manifest_id,
        entry_route_context_json={"route": "/layer3/workbench"},
        operator_context_json={
            "actor": "pytest-task7a",
            "layer3_gate_b_decision_manifest_v1": decision_manifest,
            "layer3_gate_b_idempotency_v1": idempotency_record,
        },
        summary_json={
            "current_gate": "gate_b",
            "gate_b_summary_v1": {
                "approved": 1,
                "denied": 0,
                "isolated": 0,
                "flagged": 0,
            },
        },
    )
    manifest = L3SelectionManifest(
        selection_manifest_id=manifest_id,
        session_id=session_id,
        manifest_json=manifest_json,
        source_plane_hints_json=source_plane_hints,
        selection_hash=hashlib.sha256(
            json.dumps(
                {
                    "manifest_json": manifest_json,
                    "source_plane_hints_json": source_plane_hints,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        commit_reason="operator_gate_b_decision",
    )
    descriptor = L3Descriptor(
        descriptor_id=descriptor_id,
        session_id=session_id,
        selection_manifest_id=manifest_id,
        source_plane=f"plane-{source_class}",
        descriptor_type=source_class,
        selector_payload_json=copy.deepcopy(descriptor_selector),
        selection_basis_json={"gate_b_decision": "approved"},
        expansion_reason="gate_b_approved_material",
        status="resolved_loaded",
        descriptor_hash=hashlib.sha256(descriptor_id.encode()).hexdigest(),
    )
    snapshot = L3MaterialSnapshot(
        material_snapshot_id=f"{session_id}-snapshot",
        session_id=session_id,
        descriptor_id=descriptor_id,
        source_plane=f"plane-{source_class}",
        source_shape=source_class,
        payload_ref=str(payload_path),
        payload_hash=payload_hash,
        source_identity_json=copy.deepcopy(snapshot_identity),
        source_provenance_json=copy.deepcopy(snapshot_provenance),
        co_retrieval_group_id=f"{session_id}-group",
        load_summary_json=copy.deepcopy(
            normalized_decision["load_summary"]
        ),
    )
    idempotency = L3GateBIdempotencyKey(
        gate_b_idempotency_key_id=f"{session_id}-gate-b-key",
        client_request_id=client_request_id,
        request_basis_hash=gate_b_state.gate_b_idempotency_request_hash(
            client_request_id=client_request_id,
            preflight_id=preflight_id,
            source_set_id=source_set_id,
            material_preview_id=material_preview_id,
            material_preview_hash=material_preview_hash,
            gate_b_decision_manifest_id=decision_manifest_id,
        ),
        preflight_id=preflight_id,
        source_set_id=source_set_id,
        material_preview_id=material_preview_id,
        material_preview_hash=material_preview_hash,
        gate_b_decision_manifest_id=decision_manifest_id,
        status="committed",
        session_id=session_id,
        selection_manifest_id=manifest_id,
    )
    rows: list[Any] = [session, manifest, idempotency]
    if include_snapshot:
        rows.extend([descriptor, snapshot])
    db.add_all(rows)
    db.flush()
    return session, snapshot


def _sciencebase_origin_session(
    db: Session,
    runtime: _B1aRuntime,
    *,
    stem: str,
) -> tuple[str, str, str, L3MaterialSnapshot]:
    run_id = f"{stem}-run"
    target_id = f"{stem}-target"
    record_id = f"{stem}-intake"
    session_id = f"{stem}-session"
    receipt_hash = hashlib.sha256(target_id.encode()).hexdigest()
    raw_path = runtime.storage_dir / "connectors" / "raw" / f"{stem}.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(FIXTURE_BYTES)
    _register_origin_test_path(raw_path, runtime)
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="sciencebase_mcs",
        source_system="sciencebase",
        source_mode="strict_live_egress",
        status="completed",
    )
    target = ConnectorRunTarget(
        connector_run_target_id=target_id,
        connector_run_id=run_id,
        ordinal=1,
        sciencebase_item_id="63d1a3c6d34e06fef15006be",
        sciencebase_file_name="mcs2023-germa_salient.csv",
        artifact_surface="files",
        artifact_locator_type="downloadUri_hash_only",
        source_artifact_key=(
            "sciencebase:63d1a3c6d34e06fef15006be:"
            "mcs2023-germa_salient.csv"
        ),
        downloaded_sha256=FIXTURE_SHA256,
        raw_storage_ref=str(raw_path),
        public_read_confirmed=True,
        status="downloaded",
        source_reference_json={},
    )
    pair = {
        "connector_run_target_id": target_id,
        "connector_origin_receipt_hash": receipt_hash,
    }
    strict_values = connector_intake._strict_sciencebase_intake_values(
        connector_key="sciencebase_mcs",
        connector_run_id=run_id,
        connector_run_target_id=target_id,
        raw_storage_ref=str(raw_path),
        freshness_timestamp=datetime.fromisoformat(
            "2026-07-30T12:00:00+00:00"
        ),
        content_size_bytes=len(FIXTURE_BYTES),
        content_sha256=FIXTURE_SHA256,
        connector_origin_receipt_hash=receipt_hash,
    )
    record = L3ConnectorSourceIntakeRecord(
        connector_source_intake_record_id=record_id,
        **strict_values,
    )
    source_identity = {
        "connector_source_intake_record_id": record_id,
        "source_family": "connector_produced_single_source",
        "content_sha256": FIXTURE_SHA256,
        "metadata_hash": strict_values["metadata_hash"],
        "connector_key": "sciencebase_mcs",
        "connector_run_id": run_id,
        **pair,
    }
    source_provenance = {
        **copy.deepcopy(strict_values["provenance_json"]),
        "mode": "connector_source_intake_gate_b_material_admission",
        "source_ref": f"connector_source_intake_record:{record_id}",
    }
    payload = {
        "connector_source_intake_record_id": record_id,
        "source_class": connector_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS,
        "content_sha256": FIXTURE_SHA256,
        "metadata_hash": strict_values["metadata_hash"],
        "authority_basis_hash": strict_values["authority_basis_hash"],
        "connector_key": "sciencebase_mcs",
        "connector_run_id": run_id,
        "bounded_preview_char_count": len(FIXTURE_BYTES.decode("utf-8")),
        "preview_truncated": False,
        **pair,
    }
    load_summary = {
        "loaded_records": 1,
        "failed_records": 0,
        "preview_material": True,
        "bounded_text_preview": True,
        "connector_source_intake_gate_b_material_admission": True,
    }
    decision_basis = {
        "source_ref": f"connector_source_intake_record:{record_id}",
        "query_basis": "connector_produced_source_intake",
        "provenance_ref": (
            f"connector_source_intake_record:{record_id}:"
            f"metadata:{strict_values['metadata_hash']}"
        ),
        "source_identity": copy.deepcopy(source_identity),
        "source_provenance": copy.deepcopy(source_provenance),
        "payload": copy.deepcopy(payload),
        "load_summary": copy.deepcopy(load_summary),
        "connector_target": {
            "connector_run_target_id": target_id,
            "connector_key": "sciencebase_mcs",
        },
    }
    decision_item = {
        "candidate_id": f"mat-connector_source_intake_record-{record_id}",
        "source_class": connector_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS,
        "decision": "approved",
        "decision_basis": copy.deepcopy(decision_basis),
        "source_identity": copy.deepcopy(source_identity),
        "source_provenance": copy.deepcopy(source_provenance),
        "payload": copy.deepcopy(payload),
        "load_summary": copy.deepcopy(load_summary),
    }
    db.add_all([run, target, record])
    _, snapshot = _commit_origin_test_session(
        db,
        runtime,
        session_id=session_id,
        source_class=connector_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS,
        decision_item=decision_item,
        snapshot_identity={
            "candidate_id": decision_item["candidate_id"],
            "source_class": connector_intake.STRICT_SCIENCEBASE_GATE_C_SOURCE_CLASS,
            **source_identity,
        },
        snapshot_provenance=source_provenance,
        snapshot_payload=payload,
    )
    assert snapshot is not None
    return session_id, target_id, receipt_hash, snapshot


def _nrc_origin_session(
    db: Session,
    runtime: _B1aRuntime,
    *,
    stem: str,
) -> tuple[str, str, str]:
    run_id = f"{stem}-run"
    target_id = f"{stem}-target-dynamic"
    content_id = f"{stem}-content"
    session_id = f"{stem}-session"
    content_contract_id = f"{stem}-content-contract"
    chunking_contract_id = f"{stem}-chunk-contract"
    normalization_contract_id = f"{stem}-normalization"
    receipt_hash = hashlib.sha256(target_id.encode()).hexdigest()
    run = ConnectorRun(
        connector_run_id=run_id,
        connector_key="nrc_adams_aps",
        source_system="nrc_adams",
        source_mode="strict_live_egress",
        status="completed",
    )
    target = ConnectorRunTarget(
        connector_run_target_id=target_id,
        connector_run_id=run_id,
        ordinal=1,
        stable_release_key="ML17123A319",
        stable_release_identifier="adams_accession:ML17123A319",
        selection_source="strict_exact_accession",
        selection_scope="dual_live_proof_v1",
        fetch_policy_mode="strict_live_egress",
        status="downloaded",
        source_reference_json={},
    )
    document = ApsContentDocument(
        aps_content_document_id=f"{stem}-document",
        content_id=content_id,
        content_contract_id=content_contract_id,
        chunking_contract_id=chunking_contract_id,
        normalization_contract_id=normalization_contract_id,
        normalized_text_sha256="a" * 64,
        normalized_char_count=128,
        chunk_count=1,
        content_status="indexed",
        media_type="application/pdf",
        document_class="nrc_adams_aps",
        quality_status="verified",
        page_count=1,
    )
    linkage = ApsContentLinkage(
        aps_content_linkage_id=f"{stem}-linkage",
        content_id=content_id,
        run_id=run_id,
        target_id=target_id,
        accession_number="ML17123A319",
        content_contract_id=content_contract_id,
        chunking_contract_id=chunking_contract_id,
        normalized_text_sha256=document.normalized_text_sha256,
    )
    source_identity = {
        "schema_id": "layer3.aps_content_document_source_identity.v1",
        "source_class": "aps_content_document",
        "content_id": content_id,
        "content_contract_id": content_contract_id,
        "chunking_contract_id": chunking_contract_id,
        "normalization_contract_id": normalization_contract_id,
        "content_status": "indexed",
        "media_type": "application/pdf",
        "document_class": "nrc_adams_aps",
        "quality_status": "verified",
    }
    source_provenance = {
        "schema_id": "layer3.aps_content_document_source_provenance.v1",
        "content_id": content_id,
        "aps_content_linkages": [
            {
                "aps_content_linkage_id": linkage.aps_content_linkage_id,
                "content_id": content_id,
                "run_id": run_id,
                "target_id": target_id,
                "accession_number": "ML17123A319",
                "content_contract_id": content_contract_id,
                "chunking_contract_id": chunking_contract_id,
                "content_units_ref": None,
                "normalized_text_ref": None,
                "normalized_text_sha256": "a" * 64,
                "blob_ref": None,
                "blob_sha256": None,
                "download_exchange_ref": None,
                "discovery_ref": None,
                "selection_ref": None,
                "diagnostics_ref": None,
            }
        ],
        "source_trace": {
            "document_identity": {"content_id": content_id},
            "aps_trace_refs": {
                "run_id": run_id,
                "target_id": target_id,
            },
        },
    }
    decision_item = {
        "candidate_id": f"mat-aps_content_document-{stem}",
        "source_class": "aps_content_document",
        "decision": "approved",
        "decision_basis": {
            "source_ref": f"aps_content_document:{content_id}",
            "query_basis": "dual-live-proof",
            "provenance_ref": f"aps_content_document:{content_id}",
            "source_identity": copy.deepcopy(source_identity),
            "source_provenance": copy.deepcopy(source_provenance),
            "payload": {"content_id": content_id},
            "load_summary": {"loaded_records": 1, "failed_records": 0},
        },
        "source_identity": copy.deepcopy(source_identity),
        "source_provenance": copy.deepcopy(source_provenance),
        "payload": {"content_id": content_id},
        "load_summary": {"loaded_records": 1, "failed_records": 0},
    }
    db.add_all([run, target, document, linkage])
    _commit_origin_test_session(
        db,
        runtime,
        session_id=session_id,
        source_class="aps_content_document",
        decision_item=decision_item,
        snapshot_identity={
            "candidate_id": decision_item["candidate_id"],
            **source_identity,
            "run_id": run_id,
            "target_id": target_id,
        },
        snapshot_provenance=source_provenance,
        snapshot_payload={"content_id": content_id},
    )
    return session_id, target_id, receipt_hash


def _mock_origin_verifiers(
    monkeypatch,
    *,
    target_id: str,
    receipt_hash: str,
    connector_key: str,
    final_receipt_hash: str | None = None,
) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    monkeypatch.setitem(
        sys.modules,
        "app.services.layer3_origin_continuity",
        origin,
    )
    services_package = sys.modules.get("app.services")
    if services_package is not None:
        monkeypatch.setattr(
            services_package,
            "layer3_origin_continuity",
            origin,
            raising=False,
        )

    def verified(db, *, connector_run_target_id: str):
        del db
        calls.append(("verified", connector_run_target_id))
        assert connector_run_target_id == target_id
        projected_receipt_hash = receipt_hash
        if final_receipt_hash is not None and len(calls) > 3:
            projected_receipt_hash = final_receipt_hash
        return {
            "connector_run_target_id": target_id,
            "connector_origin_receipt_hash": projected_receipt_hash,
        }

    def derived(db, *, connector_run_target_id: str):
        del db
        calls.append(("derived", connector_run_target_id))
        assert connector_run_target_id == target_id
        return {
            "connector_run_target_id": target_id,
            "connector_key": connector_key,
            "proof_class": "fresh_live",
            "receipt_hash": receipt_hash,
        }

    def continuous(
        db,
        *,
        connector_run_target_id: str,
        expected_receipt_hash: str,
        expected_bindings: dict[str, str],
    ):
        del db
        calls.append(("continuous", connector_run_target_id))
        assert connector_run_target_id == target_id
        assert expected_receipt_hash == receipt_hash
        assert expected_bindings == {
            "connector_run_target_id": target_id,
            "connector_key": connector_key,
            "proof_class": "fresh_live",
        }

    monkeypatch.setattr(
        origin,
        "verified_connector_origin_projection",
        verified,
    )
    monkeypatch.setattr(origin, "derive_connector_origin_receipt", derived)
    monkeypatch.setattr(origin, "assert_connector_origin_continuity", continuous)
    return calls


def _origin_authority_state(
    db: Session,
    runtime: _B1aRuntime,
) -> dict[str, Any]:
    models = (
        L3Session,
        L3SelectionManifest,
        L3GateBIdempotencyKey,
        L3Descriptor,
        L3MaterialSnapshot,
        L3ConnectorSourceIntakeRecord,
        ConnectorRun,
        ConnectorRunTarget,
        ApsContentDocument,
        ApsContentLinkage,
    )
    files = {}
    for path in sorted(
        candidate
        for candidate in runtime.storage_dir.rglob("*")
        if candidate.is_file()
    ):
        payload = path.read_bytes()
        files[path.relative_to(runtime.storage_dir).as_posix()] = {
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    return {
        "rows": {model.__name__: db.query(model).count() for model in models},
        "files": files,
    }


def _scrub_downstream_session_surfaces(
    db: Session,
    *,
    session_id: str,
    rewrite_mode: str,
) -> None:
    session_values = {
        "entry_route_context_json": {},
        "operator_context_json": {},
        "summary_json": {},
    }
    manifest_values = {
        "manifest_json": {},
        "source_plane_hints_json": {},
    }
    descriptor_values = {
        "source_plane": "generic",
        "descriptor_type": "manual_upload",
        "selector_payload_json": {},
        "selection_basis_json": {},
    }
    snapshot_values = {
        "source_plane": "generic",
        "source_shape": "manual_upload",
        "source_identity_json": {},
        "source_provenance_json": {},
        "load_summary_json": {},
    }
    if rewrite_mode == "orm_flush":
        session = db.get(L3Session, session_id)
        manifest = (
            db.query(L3SelectionManifest)
            .filter(L3SelectionManifest.session_id == session_id)
            .one()
        )
        descriptor = (
            db.query(L3Descriptor)
            .filter(L3Descriptor.session_id == session_id)
            .one()
        )
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == session_id)
            .one()
        )
        assert session is not None
        for field, value in session_values.items():
            setattr(session, field, copy.deepcopy(value))
        for row, values in (
            (manifest, manifest_values),
            (descriptor, descriptor_values),
            (snapshot, snapshot_values),
        ):
            for field, value in values.items():
                setattr(row, field, copy.deepcopy(value))
        db.flush()
    elif rewrite_mode == "raw_sql":
        connection = db.connection()
        for model, values in (
            (L3Session, session_values),
            (L3SelectionManifest, manifest_values),
            (L3Descriptor, descriptor_values),
            (L3MaterialSnapshot, snapshot_values),
        ):
            table = model.__table__
            connection.execute(
                update(table)
                .where(table.c.session_id == session_id)
                .values(**values)
            )
        db.expire_all()
    else:
        raise AssertionError(f"unsupported rewrite mode: {rewrite_mode}")
    assert not db.new
    assert not db.dirty
    assert not db.deleted


def test_downstream_origin_guard_has_exact_public_signature() -> None:
    signature = inspect.signature(
        origin.assert_downstream_connector_origin
    )
    assert list(signature.parameters) == [
        "db",
        "session_id",
        "expected_receipt_hash",
        "boundary",
    ]
    assert signature.parameters["session_id"].kind is inspect.Parameter.KEYWORD_ONLY
    assert (
        signature.parameters["expected_receipt_hash"].kind
        is inspect.Parameter.KEYWORD_ONLY
    )
    assert signature.parameters["boundary"].kind is inspect.Parameter.KEYWORD_ONLY
    hints = get_type_hints(origin.assert_downstream_connector_origin)
    assert hints["boundary"] == Literal[
        "execution_output",
        "result_review",
        "package_commit",
        "package_submit",
        "handoff_prepare",
    ]
    assert hints["return"] == dict[str, Any]


def test_downstream_committed_reader_accepts_connection_bound_session(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    with task7_origin_runtime.engine.connect() as caller_connection:
        with Session(
            bind=caller_connection,
            autoflush=False,
            expire_on_commit=False,
        ) as db:
            session_id, target_id, receipt_hash, _ = (
                _sciencebase_origin_session(
                    db,
                    task7_origin_runtime,
                    stem="origin-connection-bind",
                )
            )
            db.commit()
            db.begin()
            _mock_origin_verifiers(
                monkeypatch,
                target_id=target_id,
                receipt_hash=receipt_hash,
                connector_key="sciencebase_mcs",
            )

            assert origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash=receipt_hash,
                boundary="execution_output",
            )["connector_run_target_id"] == target_id


def test_downstream_engine_url_predicate_is_dialect_correct() -> None:
    assert origin._downstream_engine_url_admitted(  # type: ignore[attr-defined]
        make_url("postgresql://task7@localhost/project6")
    )
    for url in (
        "sqlite://",
        "sqlite:///:memory:",
        "sqlite:///file::memory:?cache=shared&uri=true",
        "sqlite:///file:task7?mode=memory&cache=shared&uri=true",
        "sqlite:///file:/proof?vfs=memdb&uri=true",
    ):
        assert not origin._downstream_engine_url_admitted(  # type: ignore[attr-defined]
            make_url(url)
        )


def test_downstream_committed_reader_rejects_sqlite_named_memory() -> None:
    engine = create_engine(
        "sqlite:///file:task7-shared?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
        pool_size=2,
        max_overflow=0,
    )
    try:
        with Session(engine, autoflush=False) as db:
            db.begin()
            with pytest.raises(
                origin.Layer3OriginContinuityError
            ) as excinfo:
                origin._downstream_committed_engine(db)  # type: ignore[attr-defined]
        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
    finally:
        engine.dispose()


def test_downstream_guard_rejects_relative_configured_storage_root(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
    ) as db:
        db.begin()
        monkeypatch.setattr(settings, "storage_dir", "relative-storage")
        monkeypatch.setattr(
            origin,
            "_downstream_session_origin",
            lambda *args, **kwargs: pytest.fail(
                "invalid configured root must fail before authority reads"
            ),
        )

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id="root-validation-session",
                expected_receipt_hash="0" * 64,
                boundary="execution_output",
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )


def test_downstream_origin_rejects_fully_flushed_uncommitted_authority(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        session_id, target_id, receipt_hash, _ = _sciencebase_origin_session(
            db,
            task7_origin_runtime,
            stem="origin-uncommitted-forge",
        )
        _mock_origin_verifiers(
            monkeypatch,
            target_id=target_id,
            receipt_hash=receipt_hash,
            connector_key="sciencebase_mcs",
        )
        before = _origin_authority_state(db, task7_origin_runtime)
        flushes: list[bool] = []

        def record_flush(*_args: object) -> None:
            flushes.append(True)

        event.listen(db, "before_flush", record_flush)
        try:
            with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
                origin.assert_downstream_connector_origin(
                    db,
                    session_id=session_id,
                    expected_receipt_hash=receipt_hash,
                    boundary="execution_output",
                )
        finally:
            event.remove(db, "before_flush", record_flush)

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
        assert flushes == []
        assert _origin_authority_state(db, task7_origin_runtime) == before
        db.rollback()

    with Session(task7_origin_runtime.engine, autoflush=False) as durable:
        assert durable.query(L3Session).count() == 0
        assert durable.query(ConnectorRun).count() == 0
        assert durable.query(ConnectorRunTarget).count() == 0


def test_downstream_origin_rejects_self_consistent_flushed_manifest_rewrite(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        session_id, target_id, receipt_hash, _ = _sciencebase_origin_session(
            db,
            task7_origin_runtime,
            stem="origin-flushed-manifest",
        )
        db.commit()
        original_manifest = copy.deepcopy(
            db.query(L3SelectionManifest).one().manifest_json
        )
        db.commit()
        db.begin()
        manifest = db.query(L3SelectionManifest).one()
        rewritten = copy.deepcopy(manifest.manifest_json)
        rewritten["flushed_rewrite"] = {"self_consistent": True}
        manifest.manifest_json = rewritten
        manifest.selection_hash = hashlib.sha256(
            json.dumps(
                {
                    "manifest_json": rewritten,
                    "source_plane_hints_json": (
                        manifest.source_plane_hints_json
                    ),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        db.flush()
        unrelated = L3Session(
            session_id="origin-unrelated-pending",
            status="completed",
            selection_manifest_id="origin-unrelated-manifest",
            entry_route_context_json={},
            operator_context_json={},
            summary_json={},
        )
        db.add(unrelated)
        caller_root = db.get_transaction()
        _mock_origin_verifiers(
            monkeypatch,
            target_id=target_id,
            receipt_hash=receipt_hash,
            connector_key="sciencebase_mcs",
        )

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash=receipt_hash,
                boundary="package_commit",
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
        assert db.get_transaction() is caller_root
        assert caller_root is not None and caller_root.is_active
        assert unrelated in db.new
        assert manifest.manifest_json == rewritten
        with Session(
            task7_origin_runtime.engine,
            autoflush=False,
        ) as committed:
            durable_manifest = committed.query(L3SelectionManifest).one()
            assert durable_manifest.manifest_json == original_manifest


def test_downstream_sciencebase_origin_uses_committed_session_authority(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        session_id, target_id, receipt_hash, snapshot = (
            _sciencebase_origin_session(
                db,
                task7_origin_runtime,
                stem="origin-sciencebase",
            )
        )
        db.commit()
        db.begin()
        calls = _mock_origin_verifiers(
            monkeypatch,
            target_id=target_id,
            receipt_hash=receipt_hash,
            connector_key="sciencebase_mcs",
        )
        for boundary in _DOWNSTREAM_ORIGIN_BOUNDARIES:
            assert origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash=receipt_hash,
                boundary=boundary,
            ) == {
                "connector_run_target_id": target_id,
                "connector_origin_receipt_hash": receipt_hash,
                "proof_class": "fresh_live",
                "connector_key": "sciencebase_mcs",
                "boundary": boundary,
            }
        assert calls
        assert {target for _, target in calls} == {target_id}
        assert sum(label == "derived" for label, _ in calls) == 5
        assert sum(label == "continuous" for label, _ in calls) == 5
        assert sum(label == "verified" for label, _ in calls) >= 5

        call_count = len(calls)
        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash="f" * 64,
                boundary="execution_output",
            )
        assert excinfo.value.code == "layer3_downstream_origin_hash_mismatch"
        assert len(calls) > call_count
        assert {
            label for label, _ in calls[call_count:]
        } == {"verified"}

        changed_identity = copy.deepcopy(snapshot.source_identity_json)
        changed_identity["connector_origin_receipt_hash"] = "e" * 64
        snapshot.source_identity_json = changed_identity
        db.flush()
        before_census = _row_census(db)
        before_payload = Path(snapshot.payload_ref).read_bytes()
        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash=receipt_hash,
                boundary="result_review",
            )
        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
        assert _row_census(db) == before_census
        assert Path(snapshot.payload_ref).read_bytes() == before_payload


@pytest.mark.parametrize(
    "mutation",
    ("selection_hash", "snapshot_identity", "nrc_linkage_field"),
)
def test_downstream_origin_requires_exact_durable_authority(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
    mutation: str,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        if mutation == "nrc_linkage_field":
            session_id, target_id, receipt_hash = _nrc_origin_session(
                db,
                task7_origin_runtime,
                stem="origin-exact-nrc-linkage",
            )
            linkage = db.query(ApsContentLinkage).one()
            linkage.content_contract_id = "origin-contradictory-contract"
            connector_key = "nrc_adams_aps"
        else:
            session_id, target_id, receipt_hash, snapshot = (
                _sciencebase_origin_session(
                    db,
                    task7_origin_runtime,
                    stem=f"origin-exact-{mutation}",
                )
            )
            connector_key = "sciencebase_mcs"
            if mutation == "selection_hash":
                manifest = db.query(L3SelectionManifest).one()
                manifest.selection_hash = "f" * 64
            else:
                changed_identity = copy.deepcopy(
                    snapshot.source_identity_json
                )
                changed_identity["content_sha256"] = "d" * 64
                snapshot.source_identity_json = changed_identity
        db.commit()
        db.begin()
        _mock_origin_verifiers(
            monkeypatch,
            target_id=target_id,
            receipt_hash=receipt_hash,
            connector_key=connector_key,
        )
        before = _origin_authority_state(db, task7_origin_runtime)
        flushes: list[bool] = []

        def record_flush(*_args: object) -> None:
            flushes.append(True)

        event.listen(db, "before_flush", record_flush)
        try:
            with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
                origin.assert_downstream_connector_origin(
                    db,
                    session_id=session_id,
                    expected_receipt_hash=receipt_hash,
                    boundary="package_commit",
                )
        finally:
            event.remove(db, "before_flush", record_flush)

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
        assert flushes == []
        assert _origin_authority_state(db, task7_origin_runtime) == before


@pytest.mark.parametrize("mutation", ("target", "event", "policy"))
def test_downstream_origin_rejects_flushed_nrc_origin_anchor_mutation(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
    mutation: str,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        session_id, target_id, receipt_hash = _nrc_origin_session(
            db,
            task7_origin_runtime,
            stem=f"origin-anchor-{mutation}",
        )
        db.commit()
        db.begin()
        target = db.get(ConnectorRunTarget, target_id)
        assert target is not None
        run_id = target.connector_run_id
        if mutation == "target":
            target.source_reference_json = {"flushed": "target"}
        elif mutation == "event":
            db.add(
                ConnectorRunEvent(
                    connector_run_event_id="origin-flushed-event",
                    connector_run_id=run_id,
                    connector_run_target_id=target_id,
                    event_type="diagnostic",
                    metrics_json={"flushed": "event"},
                )
            )
        else:
            db.add(
                ConnectorPolicySnapshot(
                    connector_policy_snapshot_id="origin-flushed-policy",
                    connector_run_id=run_id,
                    policy_json={"flushed": "policy"},
                    retry_matrix_json={},
                )
            )
        db.flush()
        caller_root = db.get_transaction()
        _mock_origin_verifiers(
            monkeypatch,
            target_id=target_id,
            receipt_hash=receipt_hash,
            connector_key="nrc_adams_aps",
        )

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash=receipt_hash,
                boundary="handoff_prepare",
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
        assert db.get_transaction() is caller_root
        assert caller_root is not None and caller_root.is_active
        caller_values = {
            "target": copy.deepcopy(target.source_reference_json),
            "events": [
                (row.connector_run_event_id, copy.deepcopy(row.metrics_json))
                for row in db.query(ConnectorRunEvent).all()
            ],
            "policies": [
                (
                    row.connector_policy_snapshot_id,
                    copy.deepcopy(row.policy_json),
                )
                for row in db.query(ConnectorPolicySnapshot).all()
            ],
        }
        with Session(
            task7_origin_runtime.engine,
            autoflush=False,
        ) as committed:
            durable_target = committed.get(ConnectorRunTarget, target_id)
            assert durable_target is not None
            durable_values = {
                "target": durable_target.source_reference_json,
                "events": [
                    (
                        row.connector_run_event_id,
                        row.metrics_json,
                    )
                    for row in committed.query(ConnectorRunEvent).all()
                ],
                "policies": [
                    (
                        row.connector_policy_snapshot_id,
                        row.policy_json,
                    )
                    for row in committed.query(
                        ConnectorPolicySnapshot
                    ).all()
                ],
            }
        assert caller_values != durable_values


def test_downstream_reserved_sciencebase_missing_snapshot_fails_closed(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        source_session_id, target_id, receipt_hash, source_snapshot = (
            _sciencebase_origin_session(
                db,
                task7_origin_runtime,
                stem="origin-sciencebase-missing",
            )
        )
        source_session = db.get(L3Session, source_session_id)
        assert source_session is not None
        manifest = source_session.operator_context_json[
            "layer3_gate_b_decision_manifest_v1"
        ]
        decision_item = copy.deepcopy(manifest["items"][0])
        missing_session_id = "origin-sciencebase-no-snapshot-session"
        _commit_origin_test_session(
            db,
            task7_origin_runtime,
            session_id=missing_session_id,
            source_class="connector_produced_single_source",
            decision_item=decision_item,
            snapshot_identity=copy.deepcopy(
                source_snapshot.source_identity_json
            ),
            snapshot_provenance=copy.deepcopy(
                source_snapshot.source_provenance_json
            ),
            snapshot_payload={
                "connector_run_target_id": target_id,
                "connector_origin_receipt_hash": receipt_hash,
            },
            include_snapshot=False,
        )
        db.commit()
        db.begin()
        monkeypatch.setattr(
            origin,
            "verified_connector_origin_projection",
            lambda *args, **kwargs: pytest.fail(
                "missing reserved material must fail before origin verification"
            ),
        )
        before_census = _row_census(db)

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=missing_session_id,
                expected_receipt_hash=receipt_hash,
                boundary="execution_output",
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
        assert _row_census(db) == before_census


@pytest.mark.parametrize(
    ("source_class", "candidate_id", "identity_updates"),
    (
        (
            "aps_content_document",
            "mat-partial-nrc",
            {"selection_scope": "dual_live_proof_v1"},
        ),
        (
            "manual_upload",
            "mat-connector_source_intake_record-partial-sciencebase",
            {
                "source_system": "sciencebase",
                "source_mode": "strict_live_egress",
            },
        ),
        (
            "aps_content_document",
            "mat-connector_source_intake_record-contradictory",
            {
                "selection_scope": "dual_live_proof_v1",
                "source_system": "sciencebase",
                "source_mode": "strict_live_egress",
            },
        ),
    ),
)
def test_downstream_reserved_partial_signals_cannot_downgrade(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
    source_class: str,
    candidate_id: str,
    identity_updates: dict[str, str],
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        identity = {
            "candidate_id": candidate_id,
            "source_class": source_class,
            **identity_updates,
        }
        provenance = {"schema_id": "layer3.partial_origin.v1"}
        payload = {"partial": True}
        load_summary = {"loaded_records": 1, "failed_records": 0}
        decision = {
            "candidate_id": candidate_id,
            "source_class": source_class,
            "decision": "approved",
            "decision_basis": {
                "source_ref": f"partial:{candidate_id}",
                "query_basis": "partial_reserved_signal",
                "provenance_ref": f"partial:{candidate_id}",
                "source_identity": copy.deepcopy(identity),
                "source_provenance": copy.deepcopy(provenance),
                "payload": copy.deepcopy(payload),
                "load_summary": copy.deepcopy(load_summary),
            },
            "source_identity": copy.deepcopy(identity),
            "source_provenance": copy.deepcopy(provenance),
            "payload": copy.deepcopy(payload),
            "load_summary": copy.deepcopy(load_summary),
        }
        session, _ = _commit_origin_test_session(
            db,
            task7_origin_runtime,
            session_id=(
                "partial-"
                f"{hashlib.sha256(candidate_id.encode()).hexdigest()[:8]}"
            ),
            source_class=source_class,
            decision_item=decision,
            snapshot_identity=identity,
            snapshot_provenance=provenance,
            snapshot_payload=payload,
        )
        db.commit()
        db.begin()
        monkeypatch.setattr(
            origin,
            "verified_connector_origin_projection",
            lambda *args, **kwargs: pytest.fail(
                "partial reserved authority must fail before projection"
            ),
        )

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=session.session_id,
                expected_receipt_hash="0" * 64,
                boundary="result_review",
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )


@pytest.mark.parametrize("origin_kind", ("sciencebase", "nrc"))
def test_downstream_linked_reserved_authority_cannot_be_scrubbed(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
    origin_kind: str,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        if origin_kind == "sciencebase":
            session_id, _, receipt_hash, snapshot = (
                _sciencebase_origin_session(
                    db,
                    task7_origin_runtime,
                    stem="origin-scrubbed-sciencebase",
                )
            )
        else:
            session_id, _, receipt_hash = _nrc_origin_session(
                db,
                task7_origin_runtime,
                stem="origin-scrubbed-nrc",
            )
            snapshot = db.query(L3MaterialSnapshot).one()
        session = db.get(L3Session, session_id)
        assert session is not None
        session.operator_context_json = {"actor": "scrubbed"}
        snapshot.source_identity_json = {}
        snapshot.source_provenance_json = {}
        db.commit()
        db.begin()
        monkeypatch.setattr(
            origin,
            "verified_connector_origin_projection",
            lambda *args, **kwargs: pytest.fail(
                "scrubbed reserved authority must fail before verification"
            ),
        )

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash=receipt_hash,
                boundary="result_review",
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )


@pytest.mark.parametrize(
    "case",
    (
        "depth",
        "cycle",
        "non_string_key",
        "non_finite",
        "fanout",
        "string_bytes",
    ),
)
def test_downstream_reserved_signal_json_validation_is_bounded(
    monkeypatch,
    case: str,
) -> None:
    value: object
    if case == "depth":
        value = {}
        for _ in range(32):
            value = {"nested": value}
    elif case == "cycle":
        cyclic: list[object] = []
        cyclic.append(cyclic)
        value = cyclic
    elif case == "non_string_key":
        value = {1: "not-json-object-authority"}
    elif case == "non_finite":
        value = {"value": float("nan")}
    elif case == "fanout":
        monkeypatch.setattr(
            origin,
            "_DOWNSTREAM_JSON_FANOUT_CAP",
            4,
            raising=False,
        )
        value = {"values": list(range(5))}
    else:
        monkeypatch.setattr(
            origin,
            "_DOWNSTREAM_JSON_STRING_BYTE_CAP",
            8,
            raising=False,
        )
        value = {"value": "x" * 9}

    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        origin._downstream_reserved_kind(value)  # type: ignore[attr-defined]

    assert (
        excinfo.value.code
        == "layer3_downstream_origin_authority_invalid"
    )


@pytest.mark.parametrize(
    "encoding",
    ("duplicate_key", "invalid_constant", "noncanonical"),
)
def test_downstream_snapshot_payload_requires_strict_canonical_bytes(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
    encoding: str,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        session_id, target_id, receipt_hash, snapshot = (
            _sciencebase_origin_session(
                db,
                task7_origin_runtime,
                stem=f"origin-payload-{encoding}",
            )
        )
        canonical_bytes = Path(snapshot.payload_ref).read_bytes()
        payload = json.loads(canonical_bytes)
        if encoding == "duplicate_key":
            rewritten_bytes = (
                b'{"connector_key":"shadow",'
                + canonical_bytes.removeprefix(b"{")
            )
        elif encoding == "invalid_constant":
            rewritten_bytes = (
                canonical_bytes.removesuffix(b"}")
                + b',"invalid_constant":NaN}'
            )
        else:
            rewritten_bytes = json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=False,
            ).encode("utf-8")
        rewritten_hash = hashlib.sha256(rewritten_bytes).hexdigest()
        rewritten_path = (
            Path(settings.artifact_storage_dir)
            / "layer3"
            / session_id
            / f"{rewritten_hash}.json"
        )
        rewritten_path.write_bytes(rewritten_bytes)
        _register_origin_test_path(rewritten_path, task7_origin_runtime)
        snapshot.payload_ref = str(rewritten_path)
        snapshot.payload_hash = rewritten_hash
        db.commit()
        db.begin()
        _mock_origin_verifiers(
            monkeypatch,
            target_id=target_id,
            receipt_hash=receipt_hash,
            connector_key="sciencebase_mcs",
        )

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash=receipt_hash,
                boundary="package_submit",
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )


def test_downstream_generic_connector_session_is_not_applicable(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        generic_identity = {
            "candidate_id": "mat-manual_upload-origin-generic",
            "source_class": "connector_produced_single_source",
        }
        generic_provenance = {
            "schema_id": "layer3.manual_upload_source_provenance.v1",
        }
        generic_payload = {"record_count": 1}
        generic_load_summary = {"loaded_records": 1, "failed_records": 0}
        generic_decision = {
            "candidate_id": generic_identity["candidate_id"],
            "source_class": "connector_produced_single_source",
            "decision": "approved",
            "decision_basis": {
                "source_ref": "manual_upload:origin-generic",
                "query_basis": "manual_upload",
                "provenance_ref": "manual_upload:origin-generic",
                "source_identity": copy.deepcopy(generic_identity),
                "source_provenance": copy.deepcopy(generic_provenance),
                "payload": copy.deepcopy(generic_payload),
                "load_summary": copy.deepcopy(generic_load_summary),
            },
            "source_identity": copy.deepcopy(generic_identity),
            "source_provenance": copy.deepcopy(generic_provenance),
            "payload": copy.deepcopy(generic_payload),
            "load_summary": copy.deepcopy(generic_load_summary),
        }
        committed_session, _ = _commit_origin_test_session(
            db,
            task7_origin_runtime,
            session_id="origin-generic-session",
            source_class="connector_produced_single_source",
            decision_item=generic_decision,
            snapshot_identity=generic_identity,
            snapshot_provenance=generic_provenance,
            snapshot_payload=generic_payload,
        )
        db.commit()
        db.begin()
        monkeypatch.setattr(
            origin,
            "verified_connector_origin_projection",
            lambda *args, **kwargs: pytest.fail(
                "generic sessions must not enter reserved origin verification"
            ),
        )
        before_census = _row_census(db)

        assert origin.assert_downstream_connector_origin(
            db,
            session_id=committed_session.session_id,
            expected_receipt_hash="0" * 64,
            boundary="execution_output",
        ) == {
            "applicability": "not_applicable",
            "boundary": "execution_output",
        }
        assert _row_census(db) == before_census

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=committed_session.session_id,
                expected_receipt_hash="0" * 64,
                boundary="not-a-boundary",  # type: ignore[arg-type]
            )
        assert excinfo.value.code == "layer3_downstream_origin_boundary_invalid"
        assert _row_census(db) == before_census


@pytest.mark.parametrize(
    ("connector_key", "source_system", "source_mode", "weak_signal"),
    (
        (
            "nrc_adams_aps",
            "nrc_adams",
            "aps",
            {"source_shape": "aps_content_document"},
        ),
        (
            "sciencebase_mcs",
            "sciencebase",
            "public_api",
            {
                "candidate_id": (
                    "mat-connector_source_intake_record-legacy-record"
                )
            },
        ),
    ),
)
def test_downstream_legacy_connector_run_is_not_reserved(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
    connector_key: str,
    source_system: str,
    source_mode: str,
    weak_signal: dict[str, str],
) -> None:
    run_id = f"legacy-{connector_key}-run"
    session_id = f"legacy-{connector_key}-session"
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        db.add_all(
            [
                ConnectorRun(
                    connector_run_id=run_id,
                    connector_key=connector_key,
                    source_system=source_system,
                    source_mode=source_mode,
                    status="completed",
                ),
                L3Session(
                    session_id=session_id,
                    status="completed",
                    selection_manifest_id=f"manifest-{session_id}",
                    entry_route_context_json={},
                    operator_context_json={},
                    summary_json={"run_id": run_id, **weak_signal},
                ),
            ]
        )
        db.commit()
        db.begin()
        monkeypatch.setattr(
            origin,
            "verified_connector_origin_projection",
            lambda *args, **kwargs: pytest.fail(
                "legacy connector run entered reserved origin verification"
            ),
        )

        assert origin.assert_downstream_connector_origin(
            db,
            session_id=session_id,
            expected_receipt_hash="0" * 64,
            boundary="result_review",
        ) == {
            "applicability": "not_applicable",
            "boundary": "result_review",
        }


@pytest.mark.parametrize(
    ("database_url", "url_label"),
    (
        ("sqlite://", "empty"),
        ("sqlite:///:memory:", "explicit"),
    ),
)
@pytest.mark.parametrize("generic_aps_signals", (False, True))
def test_downstream_generic_guards_bypass_staticpool_in_memory_reader(
    tmp_path: Path,
    monkeypatch,
    database_url: str,
    url_label: str,
    generic_aps_signals: bool,
) -> None:
    storage_dir = (tmp_path / "generic-storage").resolve()
    bootstrap_storage_tree(storage_dir)
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    signal_label = "aps" if generic_aps_signals else "empty"
    session_id = f"origin-generic-staticpool-{url_label}-{signal_label}"
    with Session(
        engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        db.add(
            L3Session(
                session_id=session_id,
                status="completed",
                selection_manifest_id=f"manifest-{session_id}",
                entry_route_context_json={},
                operator_context_json={},
                summary_json=(
                    {
                        "source_class": "aps_content_document",
                        "source_shape": "aps_content_document",
                        "document_class": "nrc_adams_aps",
                        "accession_number": "ML17123A319",
                    }
                    if generic_aps_signals
                    else {}
                ),
            )
        )
        db.commit()
        db.begin()
        monkeypatch.setattr(
            origin,
            "_assert_downstream_connector_origin",
            lambda *args, **kwargs: pytest.fail(
                "generic resolution entered the committed reader"
            ),
        )

        assert origin.resolve_downstream_connector_origin(
            db,
            session_id=session_id,
            boundary="pass_selection",
        ) is None
        pass_run = L3PassRun(
            pass_run_id=f"pass-{session_id}",
            session_id=session_id,
            analysis_plan_id=f"plan-{session_id}",
            analysis_set_id=f"set-{session_id}",
            pass_type="single_item",
            engine_family="wrapped_quantitative_analysis",
            status="selected_not_started",
            input_payload_ref="layer3://generic/input",
            summary_json={},
        )
        assert origin.assert_pass_downstream_connector_origin(
            db,
            pass_run=pass_run,
            boundary="execution_output",
        ) is None
    engine.dispose()


def test_downstream_reserved_marker_cannot_bypass_staticpool_memory_reader(
    tmp_path: Path,
    monkeypatch,
) -> None:
    storage_dir = (tmp_path / "reserved-storage").resolve()
    bootstrap_storage_tree(storage_dir)
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as db:
            db.add(
                L3Session(
                    session_id="origin-reserved-staticpool",
                    status="completed",
                    selection_manifest_id="manifest-reserved-staticpool",
                    entry_route_context_json={},
                    operator_context_json={},
                    summary_json={"query_basis": "dual-live-proof"},
                )
            )
            db.commit()
            db.begin()

            with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
                origin.resolve_downstream_connector_origin(
                    db,
                    session_id="origin-reserved-staticpool",
                    boundary="pass_selection",
                )

            assert (
                excinfo.value.code
                == "layer3_downstream_origin_authority_invalid"
            )
    finally:
        engine.dispose()


def test_downstream_generic_resolver_rejects_file_staticpool_bypass(
    tmp_path: Path,
    monkeypatch,
) -> None:
    storage_dir = (tmp_path / "file-staticpool-storage").resolve()
    database_path = (tmp_path / "file-staticpool.sqlite3").resolve()
    bootstrap_storage_tree(storage_dir)
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as db:
            db.add(
                L3Session(
                    session_id="origin-generic-file-staticpool",
                    status="completed",
                    selection_manifest_id=(
                        "manifest-generic-file-staticpool"
                    ),
                    entry_route_context_json={},
                    operator_context_json={},
                    summary_json={},
                )
            )
            db.commit()
            db.begin()
            monkeypatch.setattr(
                origin,
                "_downstream_session_origin",
                lambda *args, **kwargs: pytest.fail(
                    "file StaticPool must fail before not_applicable"
                ),
            )
            caller_root = db.get_transaction()
            statements: list[str] = []

            def capture_statement(
                _connection: Connection,
                _cursor: object,
                statement: str,
                _parameters: object,
                _context: object,
                _executemany: bool,
            ) -> None:
                statements.append(
                    statement.lstrip().partition(" ")[0].upper()
                )

            event.listen(
                engine,
                "before_cursor_execute",
                capture_statement,
            )
            try:
                with pytest.raises(
                    origin.Layer3OriginContinuityError
                ) as excinfo:
                    origin.resolve_downstream_connector_origin(
                        db,
                        session_id=(
                            "origin-generic-file-staticpool"
                        ),
                        boundary="pass_selection",
                    )
            finally:
                event.remove(
                    engine,
                    "before_cursor_execute",
                    capture_statement,
                )

            assert (
                excinfo.value.code
                == "layer3_downstream_origin_authority_invalid"
            )
            assert not {"INSERT", "UPDATE", "DELETE"} & set(statements)
            assert db.get_transaction() is caller_root
            assert caller_root is not None and caller_root.is_active
    finally:
        engine.dispose()


def test_downstream_generic_pass_rejects_file_staticpool_bypass(
    tmp_path: Path,
    monkeypatch,
) -> None:
    storage_dir = (
        tmp_path / "file-staticpool-pass-storage"
    ).resolve()
    database_path = (
        tmp_path / "file-staticpool-pass.sqlite3"
    ).resolve()
    bootstrap_storage_tree(storage_dir)
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as db:
            session_id = "origin-pass-generic-file-staticpool"
            db.add(
                L3Session(
                    session_id=session_id,
                    status="completed",
                    selection_manifest_id=(
                        "manifest-pass-generic-file-staticpool"
                    ),
                    entry_route_context_json={},
                    operator_context_json={},
                    summary_json={},
                )
            )
            db.commit()
            db.begin()
            monkeypatch.setattr(
                origin,
                "_downstream_session_origin",
                lambda *args, **kwargs: pytest.fail(
                    "file StaticPool must fail before not_applicable"
                ),
            )
            pass_run = L3PassRun(
                pass_run_id="pass-generic-file-staticpool",
                session_id=session_id,
                analysis_plan_id="plan-generic-file-staticpool",
                analysis_set_id="set-generic-file-staticpool",
                pass_type="single_item",
                engine_family="wrapped_quantitative_analysis",
                status="selected_not_started",
                input_payload_ref="layer3://generic/input",
                summary_json={},
            )
            caller_root = db.get_transaction()
            statements: list[str] = []

            def capture_statement(
                _connection: Connection,
                _cursor: object,
                statement: str,
                _parameters: object,
                _context: object,
                _executemany: bool,
            ) -> None:
                statements.append(
                    statement.lstrip().partition(" ")[0].upper()
                )

            event.listen(
                engine,
                "before_cursor_execute",
                capture_statement,
            )
            try:
                with pytest.raises(
                    origin.Layer3OriginContinuityError
                ) as excinfo:
                    origin.assert_pass_downstream_connector_origin(
                        db,
                        pass_run=pass_run,
                        boundary="result_review",
                    )
            finally:
                event.remove(
                    engine,
                    "before_cursor_execute",
                    capture_statement,
                )

            assert (
                excinfo.value.code
                == "layer3_downstream_origin_authority_invalid"
            )
            assert not {"INSERT", "UPDATE", "DELETE"} & set(statements)
            assert db.get_transaction() is caller_root
            assert caller_root is not None and caller_root.is_active
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "connector_key",
    ("nrc_adams_aps", "sciencebase_mcs"),
)
def test_downstream_reserved_kind_preserves_explicit_integrity_key(
    connector_key: str,
) -> None:
    integrity = {
        "schema_id": "layer3.connector_origin_integrity.v1",
        "connector_key": connector_key,
        "connector_run_target_id": f"target-{connector_key}",
        "connector_origin_receipt_hash": "a" * 64,
        "proof_class": "offline_fixture",
    }

    assert (
        origin._downstream_reserved_kind(integrity)  # type: ignore[attr-defined]
        == connector_key
    )


def test_downstream_reserved_kind_rejects_unkeyed_receipt_claim() -> None:
    with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
        origin._downstream_reserved_kind(  # type: ignore[attr-defined]
            {
                "connector_run_target_id": "target-unkeyed-origin",
                "connector_origin_receipt_hash": "a" * 64,
            }
        )

    assert (
        excinfo.value.code
        == "layer3_downstream_origin_authority_invalid"
    )


def test_downstream_nrc_pass_wrapper_accepts_exact_integrity(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    integrity = {
        "schema_id": "layer3.connector_origin_integrity.v1",
        "connector_key": "nrc_adams_aps",
        "connector_run_target_id": "target-nrc-pass-wrapper",
        "connector_origin_receipt_hash": "a" * 64,
        "proof_class": "offline_fixture",
    }
    pass_run = L3PassRun(
        pass_run_id="pass-nrc-exact-origin",
        session_id="session-nrc-exact-origin",
        analysis_plan_id="plan-nrc-exact-origin",
        analysis_set_id="set-nrc-exact-origin",
        pass_type="single_item",
        engine_family="wrapped_quantitative_analysis",
        status="selected_not_started",
        input_payload_ref="layer3://nrc/input",
        summary_json={
            "planned_pass": {
                "connector_key": "nrc_adams_aps",
                "selected_method_name": "descriptive_summary",
            },
            "connector_origin_integrity_v1": copy.deepcopy(integrity),
        },
    )
    calls: list[dict[str, Any]] = []

    def exact_verifier(
        _db: Session,
        *,
        session_id: str,
        expected_receipt_hash: str | None,
        boundary: str,
    ) -> dict[str, Any]:
        calls.append(
            {
                "session_id": session_id,
                "expected_receipt_hash": expected_receipt_hash,
                "boundary": boundary,
            }
        )
        return {
            "connector_run_target_id": integrity[
                "connector_run_target_id"
            ],
            "connector_origin_receipt_hash": integrity[
                "connector_origin_receipt_hash"
            ],
            "proof_class": integrity["proof_class"],
            "connector_key": integrity["connector_key"],
            "boundary": boundary,
        }

    monkeypatch.setattr(
        origin,
        "assert_downstream_connector_origin",
        exact_verifier,
    )
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        db.begin()
        assert origin.assert_pass_downstream_connector_origin(
            db,
            pass_run=pass_run,
            boundary="execution_output",
        ) == integrity

    assert calls == [
        {
            "session_id": pass_run.session_id,
            "expected_receipt_hash": (
                integrity["connector_origin_receipt_hash"]
            ),
            "boundary": "execution_output",
        }
    ]


@pytest.mark.parametrize("rewrite_mode", ("orm_flush", "raw_sql"))
def test_downstream_resolver_rejects_committed_reserved_authority_scrub(
    task7_origin_runtime: _B1aRuntime,
    rewrite_mode: str,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        session_id, _, _, _ = _sciencebase_origin_session(
            db,
            task7_origin_runtime,
            stem=f"origin-resolver-scrub-{rewrite_mode}",
        )
        db.commit()
        db.begin()
        _scrub_downstream_session_surfaces(
            db,
            session_id=session_id,
            rewrite_mode=rewrite_mode,
        )
        assert (
            origin._downstream_session_reserved_row_kind(  # type: ignore[attr-defined]
                db,
                session_id=session_id,
            )
            is None
        )
        caller_root = db.get_transaction()
        statements: list[str] = []

        def capture_statement(
            _connection: Connection,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _executemany: bool,
        ) -> None:
            statements.append(statement.lstrip().partition(" ")[0].upper())

        event.listen(
            task7_origin_runtime.engine,
            "before_cursor_execute",
            capture_statement,
        )
        try:
            with pytest.raises(
                origin.Layer3OriginContinuityError
            ) as excinfo:
                origin.resolve_downstream_connector_origin(
                    db,
                    session_id=session_id,
                    boundary="pass_selection",
                )
        finally:
            event.remove(
                task7_origin_runtime.engine,
                "before_cursor_execute",
                capture_statement,
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
        assert not {"INSERT", "UPDATE", "DELETE"} & set(statements)
        assert db.get_transaction() is caller_root
        assert caller_root is not None and caller_root.is_active


@pytest.mark.parametrize("rewrite_mode", ("orm_flush", "raw_sql"))
def test_downstream_pass_wrapper_rejects_committed_reserved_summary_scrub(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
    rewrite_mode: str,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        session_id, target_id, receipt_hash, _ = (
            _sciencebase_origin_session(
                db,
                task7_origin_runtime,
                stem=f"origin-pass-scrub-{rewrite_mode}",
            )
        )
        integrity = {
            "schema_id": "layer3.connector_origin_integrity.v1",
            "connector_key": "sciencebase_mcs",
            "connector_run_target_id": target_id,
            "connector_origin_receipt_hash": receipt_hash,
            "proof_class": "fresh_live",
        }
        pass_run = L3PassRun(
            pass_run_id=f"pass-summary-scrub-{rewrite_mode}",
            session_id=session_id,
            analysis_plan_id=f"plan-summary-scrub-{rewrite_mode}",
            analysis_set_id=f"set-summary-scrub-{rewrite_mode}",
            pass_type="single_item",
            engine_family="wrapped_quantitative_analysis",
            status="selected_not_started",
            input_payload_ref="layer3://sciencebase/input",
            summary_json={
                "planned_pass": {
                    "connector_key": "sciencebase_mcs",
                    "selected_method_name": "descriptive_summary",
                },
                "connector_origin_integrity_v1": copy.deepcopy(
                    integrity
                ),
            },
        )
        db.add(pass_run)
        db.commit()
        db.begin()
        if rewrite_mode == "orm_flush":
            pass_run.summary_json = {}
            db.flush()
        else:
            table = L3PassRun.__table__
            db.connection().execute(
                update(table)
                .where(table.c.pass_run_id == pass_run.pass_run_id)
                .values(summary_json={})
            )
            db.expire_all()
            pass_run = db.get(L3PassRun, pass_run.pass_run_id)
            assert pass_run is not None
        assert pass_run.summary_json == {}
        assert not db.new
        assert not db.dirty
        assert not db.deleted
        _mock_origin_verifiers(
            monkeypatch,
            target_id=target_id,
            receipt_hash=receipt_hash,
            connector_key="sciencebase_mcs",
        )
        monkeypatch.setattr(
            origin,
            "assert_downstream_connector_origin",
            lambda *args, **kwargs: pytest.fail(
                "generic pass verification must use the private None-capable guard"
            ),
        )
        caller_root = db.get_transaction()
        statements: list[str] = []

        def capture_statement(
            _connection: Connection,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _executemany: bool,
        ) -> None:
            statements.append(statement.lstrip().partition(" ")[0].upper())

        event.listen(
            task7_origin_runtime.engine,
            "before_cursor_execute",
            capture_statement,
        )
        try:
            with pytest.raises(
                origin.Layer3OriginContinuityError
            ) as excinfo:
                origin.assert_pass_downstream_connector_origin(
                    db,
                    pass_run=pass_run,
                    boundary="result_review",
                )
        finally:
            event.remove(
                task7_origin_runtime.engine,
                "before_cursor_execute",
                capture_statement,
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
        assert not {"INSERT", "UPDATE", "DELETE"} & set(statements)
        assert db.get_transaction() is caller_root
        assert caller_root is not None and caller_root.is_active


def test_reserved_pass_rejects_not_applicable_origin_result(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    pass_run = L3PassRun(
        pass_run_id="pass-reserved-not-applicable",
        session_id="session-reserved-not-applicable",
        analysis_plan_id="plan-reserved-not-applicable",
        analysis_set_id="set-reserved-not-applicable",
        pass_type="single_item",
        engine_family="wrapped_quantitative_analysis",
        status="selected_not_started",
        input_payload_ref="layer3://reserved/input",
        summary_json={
            "planned_pass": {
                "connector_key": "sciencebase_mcs",
                "selected_method_name": "descriptive_summary",
            },
            "connector_origin_integrity_v1": {
                "schema_id": "layer3.connector_origin_integrity.v1",
                "connector_key": "sciencebase_mcs",
                "connector_run_target_id": "target-reserved-not-applicable",
                "connector_origin_receipt_hash": "a" * 64,
                "proof_class": "offline_fixture",
            },
        },
    )
    monkeypatch.setattr(
        origin,
        "assert_downstream_connector_origin",
        lambda *args, **kwargs: {
            "applicability": "not_applicable",
            "boundary": kwargs["boundary"],
        },
    )

    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        db.begin()
        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_pass_downstream_connector_origin(
                db,
                pass_run=pass_run,
                boundary="execution_output",
            )

    assert excinfo.value.code == "layer3_downstream_origin_authority_invalid"


def test_downstream_nrc_origin_resolves_dynamic_linkage_target(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        session_id, target_id, receipt_hash = _nrc_origin_session(
            db,
            task7_origin_runtime,
            stem="origin-nrc",
        )
        db.commit()
        db.begin()
        calls = _mock_origin_verifiers(
            monkeypatch,
            target_id=target_id,
            receipt_hash=receipt_hash,
            connector_key="nrc_adams_aps",
        )

        assert origin.assert_downstream_connector_origin(
            db,
            session_id=session_id,
            expected_receipt_hash=receipt_hash,
            boundary="handoff_prepare",
        ) == {
            "connector_run_target_id": target_id,
            "connector_origin_receipt_hash": receipt_hash,
            "proof_class": "fresh_live",
            "connector_key": "nrc_adams_aps",
            "boundary": "handoff_prepare",
        }
        assert {target for _, target in calls} == {target_id}
        assert {"verified", "derived", "continuous"} <= {
            label for label, _ in calls
        }
        assert not hasattr(
            ApsContentLinkage,
            "connector_origin_receipt_hash",
        )

        second_run_id = "origin-nrc-second-run"
        second_target_id = "origin-nrc-second-target"
        first_linkage = db.query(ApsContentLinkage).one()
        db.add_all(
            [
                ConnectorRun(
                    connector_run_id=second_run_id,
                    connector_key="nrc_adams_aps",
                    source_system="nrc_adams",
                    source_mode="strict_live_egress",
                    status="completed",
                ),
                ConnectorRunTarget(
                    connector_run_target_id=second_target_id,
                    connector_run_id=second_run_id,
                    ordinal=1,
                    stable_release_key="ML17123A319",
                    selection_scope="dual_live_proof_v1",
                    fetch_policy_mode="strict_live_egress",
                    status="downloaded",
                    source_reference_json={},
                ),
                ApsContentLinkage(
                    aps_content_linkage_id="origin-nrc-second-linkage",
                    content_id=first_linkage.content_id,
                    run_id=second_run_id,
                    target_id=second_target_id,
                    accession_number="ML17123A319",
                    content_contract_id="origin-nrc-second-content",
                    chunking_contract_id="origin-nrc-second-chunk",
                ),
            ]
        )
        db.flush()
        before_counts = {
            "runs": db.query(ConnectorRun).count(),
            "targets": db.query(ConnectorRunTarget).count(),
            "linkages": db.query(ApsContentLinkage).count(),
        }
        call_count = len(calls)

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash=receipt_hash,
                boundary="package_submit",
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
        assert len(calls) == call_count
        assert {
            "runs": db.query(ConnectorRun).count(),
            "targets": db.query(ConnectorRunTarget).count(),
            "linkages": db.query(ApsContentLinkage).count(),
        } == before_counts


def test_downstream_origin_revalidates_final_projection_before_return(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        session_id, target_id, receipt_hash = _nrc_origin_session(
            db,
            task7_origin_runtime,
            stem="origin-final-projection",
        )
        db.commit()
        db.begin()
        calls = _mock_origin_verifiers(
            monkeypatch,
            target_id=target_id,
            receipt_hash=receipt_hash,
            connector_key="nrc_adams_aps",
            final_receipt_hash="f" * 64,
        )

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash=receipt_hash,
                boundary="handoff_prepare",
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )
        assert [label for label, _ in calls] == [
            "verified",
            "verified",
            "derived",
            "continuous",
            "verified",
        ]


def test_downstream_committed_reread_bypasses_orm_identity_cache(
    task7_origin_runtime: _B1aRuntime,
    monkeypatch,
) -> None:
    with Session(
        task7_origin_runtime.engine,
        autoflush=False,
        expire_on_commit=False,
    ) as db:
        session_id, target_id, receipt_hash, _ = _sciencebase_origin_session(
            db,
            task7_origin_runtime,
            stem="origin-fresh-reread",
        )
        db.commit()
        db.begin()
        _mock_origin_verifiers(
            monkeypatch,
            target_id=target_id,
            receipt_hash=receipt_hash,
            connector_key="sciencebase_mcs",
        )
        base_verified = origin.verified_connector_origin_projection
        savepoints: list[Any] = []
        savepoint_owner: list[Session] = []

        def verified(db: Session, *, connector_run_target_id: str):
            if (
                savepoints
                and savepoint_owner[-1] is db
                and savepoints[-1].is_active
            ):
                savepoints[-1].rollback()
            return base_verified(
                db,
                connector_run_target_id=connector_run_target_id,
            )

        def mutate_during_continuity(
            committed_db: Session,
            **_kwargs: object,
        ) -> None:
            table = L3SelectionManifest.__table__
            row = committed_db.connection().execute(
                select(
                    table.c.selection_manifest_id,
                    table.c.manifest_json,
                    table.c.source_plane_hints_json,
                )
            ).mappings().one()
            rewritten = copy.deepcopy(row["manifest_json"])
            rewritten["fresh_reread_probe"] = True
            rewritten_hash = hashlib.sha256(
                json.dumps(
                    {
                        "manifest_json": rewritten,
                        "source_plane_hints_json": (
                            row["source_plane_hints_json"]
                        ),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            savepoints.append(committed_db.begin_nested())
            savepoint_owner.append(committed_db)
            committed_db.connection().execute(
                update(table)
                .where(
                    table.c.selection_manifest_id
                    == row["selection_manifest_id"]
                )
                .values(
                    manifest_json=rewritten,
                    selection_hash=rewritten_hash,
                )
            )

        monkeypatch.setattr(
            origin,
            "verified_connector_origin_projection",
            verified,
        )
        monkeypatch.setattr(
            origin,
            "assert_connector_origin_continuity",
            mutate_during_continuity,
        )

        with pytest.raises(origin.Layer3OriginContinuityError) as excinfo:
            origin.assert_downstream_connector_origin(
                db,
                session_id=session_id,
                expected_receipt_hash=receipt_hash,
                boundary="result_review",
            )

        assert (
            excinfo.value.code
            == "layer3_downstream_origin_authority_invalid"
        )


def test_gate_c_connector_origin_state_is_exact_and_fail_closed() -> None:
    origin_integrity = {
        "schema_id": "layer3.connector_origin_integrity.v1",
        "connector_key": "sciencebase_mcs",
        "connector_run_target_id": "target-gate-c-state",
        "connector_origin_receipt_hash": "a" * 64,
        "proof_class": "offline_fixture",
    }
    reserved_state = layer3_workbench._gate_c_connector_origin_state(  # type: ignore[attr-defined]
        origin_integrity
    )
    generic_state = layer3_workbench._gate_c_connector_origin_state(  # type: ignore[attr-defined]
        None
    )
    session = L3Session(
        session_id="session-gate-c-state",
        status="completed",
        selection_manifest_id="manifest-gate-c-state",
        entry_route_context_json={},
        operator_context_json={},
        summary_json={
            "gate_c_connector_origin_state_v1": reserved_state,
        },
    )

    layer3_workbench._assert_gate_c_connector_origin_state(  # type: ignore[attr-defined]
        session=session,
        connector_origin_integrity=origin_integrity,
    )
    assert generic_state == {
        "schema_id": "layer3.gate_c_connector_origin_state.v1",
        "applicability": "not_applicable",
    }

    changed_origin = {
        **origin_integrity,
        "connector_origin_receipt_hash": "b" * 64,
    }
    original_summary = copy.deepcopy(session.summary_json)
    with pytest.raises(Layer3WorkbenchError) as excinfo:
        layer3_workbench._assert_gate_c_connector_origin_state(  # type: ignore[attr-defined]
            session=session,
            connector_origin_integrity=changed_origin,
        )
    assert (
        excinfo.value.error_code
        == "gate_c_connector_origin_mismatch"
    )
    assert session.summary_json == original_summary


@_stop_receipt_on_failure
def test_b1b_owner_semantic_stops_are_zero_mutation(
    b1a_runtime: _B1aRuntime,
    tmp_path: Path,
) -> None:
    assert b1a_runtime.client is not None
    evidence_dir = _evidence_dir(tmp_path)
    with b1a_runtime.scenario() as db:
        run, target = _seed_downloaded_target(
            db,
            b1a_runtime,
            stem="b1a-p7-approved-e2",
        )
        record, preview, _intake_arguments_value = _record_and_preview(
            db,
            run,
            target,
            stem="b1a-p7-approved-e2",
        )
        gate_payload = _gate_b_payload(preview, stem="b1a-p7-approved-e2")
        gate_response = b1a_runtime.client.post(
            "/api/v1/layer3/gate-b/decision",
            json=gate_payload,
        )
        assert gate_response.status_code == 200, gate_response.text
        gate_body = gate_response.json()
        assert gate_body["status"] == "ok"
        assert gate_body["next_state"] == "connector_source_intake_gate_b_admitted"
        approved_snapshot = db.query(L3MaterialSnapshot).one()
        approved_session = db.get(L3Session, gate_body["session_id"])
        approved_intake = db.get(
            L3ConnectorSourceIntakeRecord,
            record["connector_source_intake_record_id"],
        )
        assert approved_session is not None
        assert approved_intake is not None
        physical_join = {
            "connector_run_id": run.connector_run_id,
            "connector_run_target_id": target.connector_run_target_id,
            "connector_source_intake_record_id": (
                approved_intake.connector_source_intake_record_id
            ),
            "content_sha256": approved_intake.content_sha256,
            "metadata_hash": approved_intake.metadata_hash,
            "material_preview_hash": preview["material_preview_hash"],
            "session_id": approved_session.session_id,
            "selection_manifest_id": approved_session.selection_manifest_id,
            "material_snapshot_id": approved_snapshot.material_snapshot_id,
            "snapshot_payload_hash": approved_snapshot.payload_hash,
        }
        assert physical_join["content_sha256"] == FIXTURE_SHA256
        before = _row_census(db)
        assert len(CT3_ROWS) == 8
        for row_id in CT3_STOPS:
            assert CT3_ROWS[row_id] == "UNDECIDED (explicit)"
        emitted_stops = [CT3_STOPS[row_id] for row_id in ("CT3-01", "CT3-06", "CT3-07")]
        assert emitted_stops == [
            "STOP-CT3-01-IDENTITY",
            "STOP-CT3-06-PROMOTION",
            "STOP-CT3-07-REPLAY",
        ]
        after = _row_census(db)
        assert after == before
        p7_stored_paths = _stored_path_census(db)
        for name in (
            "L3TypingRecord",
            "L3AnalysisUnit",
            "L3AnalysisGroup",
            "L3AnalysisSet",
            "L3AnalysisPlan",
            "L3PassRun",
            "AnalysisRun",
            "AnalysisArtifact",
            "L3ReconciliationRecord",
            "L3OutputPackage",
            "DatasetSourceProvenance",
        ):
            assert after[name] == 0, name

        ct3_receipt = (
            EARLY_EXTERNAL_SEAL_RECEIPTS["ct3_table"]
            if EARLY_EXTERNAL_SEAL_RECEIPTS is not None
            else {
                "bytes": EXPECTED_SEALS["ct3_table"][0],
                "sha256": EXPECTED_SEALS["ct3_table"][1],
                "measurement_status": "DECLARED-ONLY-IN-CI-AUTHORING-CONTEXT",
            }
        )
        _write_evidence(
            evidence_dir,
            "ct3-b1a-consumption.json",
            {
                "authority_sha": AUTHORITY_SHA,
                "ct3_table_receipt": ct3_receipt,
                "ct3_rows": CT3_CONSUMPTION,
                "physical_e2_join": physical_join,
                "bounded_consumption_rows": [
                    "CT3-02",
                    "CT3-03",
                    "CT3-04",
                    "CT3-05",
                    "CT3-08",
                ],
                "undecided_nonclaim_rows": ["CT3-01", "CT3-06", "CT3-07"],
                "status": _phase_status(),
            },
        )

        _write_evidence(
            evidence_dir,
            "b1b-owner-stops.json",
            {
                "authority_sha": AUTHORITY_SHA,
                "ct3_rows": CT3_ROWS,
                "emitted_stops": emitted_stops,
                "before_row_census": before,
                "after_row_census": after,
                "stored_paths": p7_stored_paths,
                "zero_mutation": True,
                "bridge_design_or_write": False,
                "canonical_identity_claim": False,
                "promotion_claim": False,
                "unified_replay_claim": False,
                "terminal_statement": FIXED_TERMINAL_STATEMENT,
                "status": _phase_status(),
            },
        )
        _write_evidence(
            evidence_dir,
            "stop-receipt.json",
            {
                "condition": "B1B-BLOCKED-ON-OWNER-CT3-01/06/07",
                "measured_facts": {
                    "physical_e2_join": physical_join,
                    "emitted_stops": emitted_stops,
                    "undecided_rows": ["CT3-01", "CT3-06", "CT3-07"],
                    "network": _network_evidence(),
                },
                "last_completed_step": "P7-B1B-DECISION-PROCEDURE",
                "row_count_snapshot": after,
                "zero_further_mutation_assertion": True,
                "terminal_statement": FIXED_TERMINAL_STATEMENT,
                "status": "EXPECTED-B1B-STOP",
            },
        )
        b1a_runtime.final_row_ledger = {
            "before": before,
            "after": after,
            "zero_mutation": True,
        }
        b1a_runtime.closeout_requested = True
