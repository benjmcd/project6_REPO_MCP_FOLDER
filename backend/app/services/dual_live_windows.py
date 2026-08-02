from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, BinaryIO, NoReturn, cast
from uuid import UUID

_msvcrt: Any
try:
    import msvcrt as _msvcrt
except ImportError:  # pragma: no cover - non-Windows import path
    _msvcrt = None

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOCAL_DRIVE_ABSOLUTE = re.compile(r"[A-Za-z]:[\\/]")
_DOS_DEVICE_BASENAMES = frozenset(
    {"aux", "con", "nul", "prn"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
)
_WAIT_OBJECT_0 = 0
_WAIT_ABANDONED_0 = 0x80
_WAIT_TIMEOUT = 0x102
_WAIT_FAILED = 0xFFFFFFFF
_ERROR_INVALID_HANDLE = 6
_ERROR_ALREADY_EXISTS = 183
_ERROR_INSUFFICIENT_BUFFER = 122
_ERROR_INVALID_PARAMETER = 87
_ERROR_NOT_FOUND = 1168
_ERROR_NOT_SAME_OBJECT = 1656
_ERROR_BROKEN_PIPE = 109
_ERROR_OPERATION_ABORTED = 995
_FILE_ATTRIBUTE_DIRECTORY = 0x10
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_READ_ATTRIBUTES = 0x80
_GENERIC_READ = 0x80000000
_READ_CONTROL = 0x00020000
_FILE_SHARE_READ = 0x1
_FILE_SHARE_WRITE = 0x2
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_NORMAL = 0x80
_FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
_FILE_ID_INFO_CLASS = 18
_FILE_TYPE_DISK = 1
_FILE_TYPE_PIPE = 3
_DRIVE_FIXED = 3
_FILE_BEGIN = 0
_OWNER_SECURITY_INFORMATION = 0x1
_GROUP_SECURITY_INFORMATION = 0x2
_DACL_SECURITY_INFORMATION = 0x4
_SE_DACL_PROTECTED = 0x1000
_ACCESS_ALLOWED_ACE_TYPE = 0
_PRIVATE_NAMESPACE_ALL_ACCESS = 0x000F000F
_MUTEX_ALL_ACCESS = 0x001F0001
_TOKEN_QUERY = 0x8
_TOKEN_USER_CLASS = 1
_SDDL_REVISION_1 = 1
_HANDLE_FLAG_INHERIT = 0x1
_DUPLICATE_SAME_ACCESS = 0x2
_PIPE_CLIENT_END = 0
_PIPE_SERVER_END = 1
_BOUNDARY_NAME = "project6-dual-live-boundary-v1"
_NAMESPACE_ALIAS = "project6-dual-live-v1"
_PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
_PROC_THREAD_ATTRIBUTE_JOB_LIST = 0x0002000D
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
_JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
_JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00001000
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_EXTENDED_STARTUPINFO_PRESENT = 0x00080000
_CREATE_UNICODE_ENVIRONMENT = 0x00000400
_STARTF_USESTDHANDLES = 0x00000100
_TERMINATE_EXIT_CODE = 0xE0000001
_POST_CREATE_CLEANUP_WAIT_MS = 5_000
_ERROR_MORE_DATA = 234
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_SYNCHRONIZE = 0x00100000
_JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS = 1
_JOB_OBJECT_BASIC_PROCESS_ID_LIST_CLASS = 3
_AF_INET = 2
_AF_INET6 = 23
_TCP_TABLE_OWNER_PID_ALL = 5
_UDP_TABLE_OWNER_PID = 1
_OBJECT_TYPE_INFORMATION_CLASS = 2
_STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
_PERMITTED_INHERITED_HANDLE_TYPES = frozenset(("Event", "File"))
_OWNED_CHILD_SCHEMA_ID = "project6.dual_live_owned_child.v1"
_OWNED_PHASE_SHARED_ENVIRONMENT = frozenset(
    (
        "AUTH_OWNER",
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
_OWNED_PHASE_A_ENVIRONMENT = _OWNED_PHASE_SHARED_ENVIRONMENT | frozenset(
    (
        "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
        "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256",
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
        "CONNECTOR_LIVE_EGRESS_ENABLED",
        "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE",
        "CONNECTOR_NRC_APS_GRANT_PATH",
        "CONNECTOR_NRC_APS_GRANT_SHA256",
        "CONNECTOR_SCIENCEBASE_GRANT_PATH",
        "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
        "NRC_ADAMS_APS_SUBSCRIPTION_KEY",
    )
)
OWNED_PHASE_A_AUTHORITY_ENVIRONMENT_NAMES = tuple(
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
_OWNED_PHASE_A_AUTHORITY_ENVIRONMENT = frozenset(
    OWNED_PHASE_A_AUTHORITY_ENVIRONMENT_NAMES
)
_OWNED_PHASE_B_ENVIRONMENT = _OWNED_PHASE_SHARED_ENVIRONMENT | frozenset(
    (
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_PATH",
        "CONNECTOR_CAMPAIGN_EVIDENCE_INDEX_SHA256",
        "CONNECTOR_CAMPAIGN_EVIDENCE_ROOT",
        "CONNECTOR_LIVE_EGRESS_ENABLED",
        "CONNECTOR_LIVE_EGRESS_EXCLUSIVE_PROOF_MODE",
    )
)
_OWNED_BOOT_SCHEMA_ID = "project6.dual_live_owned_boot.v1"
_OWNED_IO_TIMEOUT_SECONDS = 5.0
_REVIEWED_GIT_POPEN = subprocess.Popen
_SUBPROCESS_GATE_BASELINE: object = subprocess.Popen
_SUBPROCESS_GATE_BASELINE_REGISTERED = False
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


def _canonical_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("canonical JSON requires string object keys")
            result[key] = _canonical_json_value(item)
        return result
    if isinstance(value, list):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON rejects non-finite numbers")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"canonical JSON cannot encode {type(value).__name__}")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        _canonical_json_value(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class DualLiveWindowsError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _fail(code: str) -> NoReturn:
    raise DualLiveWindowsError(code)


def _local_drive_path_text(value: object, *, code: str) -> tuple[str, str]:
    """Lexically admit only ordinary absolute drive-letter paths.

    This must stay free of path resolution and filesystem metadata calls. It is
    the first guard for every owner/config supplied path.
    """

    raw = os.fspath(value) if isinstance(value, os.PathLike) else str(value)
    normalized = raw.replace("/", "\\")
    folded = normalized.casefold()
    tail = normalized[3:] if len(normalized) >= 3 else ""
    components = tail.split("\\") if tail else []
    if components and components[-1] == "":
        components.pop()
    invalid_component = any(
        not component
        or component in {".", ".."}
        or component.endswith((".", " "))
        or any(character in component for character in ':*?"<>|')
        or component.split(".", 1)[0].casefold() in _DOS_DEVICE_BASENAMES
        for component in components
    )
    if (
        not raw
        or "\x00" in raw
        or any(ord(character) < 32 for character in raw)
        or folded.startswith(
            (
                "\\\\",
                "\\??\\",
                "\\device\\",
                "\\global??\\",
            )
        )
        or _LOCAL_DRIVE_ABSOLUTE.match(normalized) is None
        or invalid_component
    ):
        _fail(code)
    return raw, normalized[:3]


def assert_local_fixed_path_before_touch(
    value: object,
    *,
    code: str,
) -> Path:
    """Reject remote/device/mapped paths before stat, resolve, or open."""

    if os.name != "nt" or _kernel32 is None:
        _fail(code)
    raw, drive_root = _local_drive_path_text(value, code=code)
    if int(_kernel32.GetDriveTypeW(drive_root)) != _DRIVE_FIXED:
        _fail(code)
    return Path(raw)


def assert_fixed_local_no_reparse_path_before_open(
    value: object,
    *,
    code: str,
    reparse_code: str | None = None,
) -> Path:
    """Require every path component to exist without any reparse point."""

    path = assert_local_fixed_path_before_touch(value, code=code)
    assert _kernel32 is not None
    current = Path(path.anchor)
    components = (current,) + tuple(
        current.joinpath(*path.parts[1:index])
        for index in range(2, len(path.parts) + 1)
    )
    for component in components:
        attributes = int(_kernel32.GetFileAttributesW(str(component)))
        if attributes == 0xFFFFFFFF:
            _fail(code)
        if attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            _fail(code if reparse_code is None else reparse_code)
    return path


def _final_path_name_from_handle(handle: int, *, code: str) -> str:
    assert _kernel32 is not None
    required = int(_kernel32.GetFinalPathNameByHandleW(handle, None, 0, 0))
    if required == 0:
        _fail(code)
    buffer = ctypes.create_unicode_buffer(required + 1)
    written = int(
        _kernel32.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    )
    if written == 0 or written >= len(buffer):
        _fail(code)
    return buffer.value


def assert_open_handle_local_fixed(
    handle: int,
    *,
    expected_path: Path,
    code: str,
) -> Path:
    """Bind an opened object to the expected fixed-local DOS path."""

    raw_final = _final_path_name_from_handle(handle, code=code)
    normalized = raw_final.replace("/", "\\")
    if normalized.casefold().startswith("\\\\?\\"):
        normalized = normalized[4:]
    final_path = assert_local_fixed_path_before_touch(normalized, code=code)
    expected = assert_local_fixed_path_before_touch(expected_path, code=code)
    if os.path.normcase(os.path.normpath(str(final_path))) != os.path.normcase(
        os.path.normpath(str(expected))
    ):
        _fail(code)
    return final_path


class _FILE_ATTRIBUTE_TAG_INFO(ctypes.Structure):
    _fields_ = (("FileAttributes", wintypes.DWORD), ("ReparseTag", wintypes.DWORD))


class _FILE_ID_128(ctypes.Structure):
    _fields_ = (("Identifier", ctypes.c_ubyte * 16),)


class _FILE_ID_INFO(ctypes.Structure):
    _fields_ = (("VolumeSerialNumber", ctypes.c_ulonglong), ("FileId", _FILE_ID_128))


class _ACL(ctypes.Structure):
    _fields_ = (
        ("AclRevision", ctypes.c_ubyte),
        ("Sbz1", ctypes.c_ubyte),
        ("AclSize", ctypes.c_ushort),
        ("AceCount", ctypes.c_ushort),
        ("Sbz2", ctypes.c_ushort),
    )


class _ACE_HEADER(ctypes.Structure):
    _fields_ = (
        ("AceType", ctypes.c_ubyte),
        ("AceFlags", ctypes.c_ubyte),
        ("AceSize", ctypes.c_ushort),
    )


class _SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = (
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    )


class _UNICODE_STRING(ctypes.Structure):
    _fields_ = (
        ("Length", ctypes.c_ushort),
        ("MaximumLength", ctypes.c_ushort),
        ("Buffer", wintypes.LPWSTR),
    )


class _MUTANT_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = (
        ("CurrentCount", wintypes.LONG),
        ("OwnedByCaller", ctypes.c_ubyte),
        ("AbandonedState", ctypes.c_ubyte),
    )


class _FILETIME(ctypes.Structure):
    _fields_ = (("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD))


class _STARTUPINFOW(ctypes.Structure):
    _fields_ = (
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    )


class _STARTUPINFOEXW(ctypes.Structure):
    _fields_ = (("StartupInfo", _STARTUPINFOW), ("lpAttributeList", wintypes.LPVOID))


class _PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = (
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    )


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = (
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    )


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = (
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    )


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = (
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    )


class _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = (
        ("TotalUserTime", ctypes.c_longlong),
        ("TotalKernelTime", ctypes.c_longlong),
        ("ThisPeriodTotalUserTime", ctypes.c_longlong),
        ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    )


class _MIB_TCPROW_OWNER_PID(ctypes.Structure):
    _fields_ = (
        ("dwState", wintypes.DWORD),
        ("dwLocalAddr", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("dwRemoteAddr", wintypes.DWORD),
        ("dwRemotePort", wintypes.DWORD),
        ("dwOwningPid", wintypes.DWORD),
    )


class _MIB_TCP6ROW_OWNER_PID(ctypes.Structure):
    _fields_ = (
        ("ucLocalAddr", ctypes.c_ubyte * 16),
        ("dwLocalScopeId", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("ucRemoteAddr", ctypes.c_ubyte * 16),
        ("dwRemoteScopeId", wintypes.DWORD),
        ("dwRemotePort", wintypes.DWORD),
        ("dwState", wintypes.DWORD),
        ("dwOwningPid", wintypes.DWORD),
    )


class _MIB_UDPROW_OWNER_PID(ctypes.Structure):
    _fields_ = (
        ("dwLocalAddr", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("dwOwningPid", wintypes.DWORD),
    )


class _MIB_UDP6ROW_OWNER_PID(ctypes.Structure):
    _fields_ = (
        ("ucLocalAddr", ctypes.c_ubyte * 16),
        ("dwLocalScopeId", wintypes.DWORD),
        ("dwLocalPort", wintypes.DWORD),
        ("dwOwningPid", wintypes.DWORD),
    )


if os.name == "nt":
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    try:
        _kernelbase = ctypes.WinDLL("kernelbase", use_last_error=True)
        _compare_object_handles = _kernelbase.CompareObjectHandles
    except (AttributeError, OSError):
        _kernelbase = None
        _compare_object_handles = None
    _advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    _iphlpapi = ctypes.WinDLL("iphlpapi", use_last_error=False)
    _ntdll = ctypes.WinDLL("ntdll", use_last_error=False)

    _kernel32.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.GetFileInformationByHandleEx.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    _kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _kernel32.GetFinalPathNameByHandleW.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    _kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    _kernel32.GetFileType.argtypes = (wintypes.HANDLE,)
    _kernel32.GetFileType.restype = wintypes.DWORD
    _kernel32.GetFileAttributesW.argtypes = (wintypes.LPCWSTR,)
    _kernel32.GetFileAttributesW.restype = wintypes.DWORD
    _kernel32.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)
    _kernel32.GetDriveTypeW.restype = wintypes.UINT
    _kernel32.GetFileSizeEx.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_longlong),
    )
    _kernel32.GetFileSizeEx.restype = wintypes.BOOL
    _kernel32.SetFilePointerEx.argtypes = (
        wintypes.HANDLE,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_longlong),
        wintypes.DWORD,
    )
    _kernel32.SetFilePointerEx.restype = wintypes.BOOL
    _kernel32.ReadFile.argtypes = (
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    )
    _kernel32.ReadFile.restype = wintypes.BOOL
    _kernel32.WriteFile.argtypes = (
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    )
    _kernel32.WriteFile.restype = wintypes.BOOL
    _kernel32.GetNamedPipeInfo.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
    )
    _kernel32.GetNamedPipeInfo.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.GetHandleInformation.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    )
    _kernel32.GetHandleInformation.restype = wintypes.BOOL
    _kernel32.OpenProcessToken = _advapi32.OpenProcessToken
    _kernel32.OpenProcessToken.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    )
    _kernel32.OpenProcessToken.restype = wintypes.BOOL
    _kernel32.GetCurrentProcess.argtypes = ()
    _kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    _kernel32.OpenProcess.argtypes = (
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    )
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.GetProcessId.argtypes = (wintypes.HANDLE,)
    _kernel32.GetProcessId.restype = wintypes.DWORD
    _kernel32.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    _kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    _kernel32.GetTokenInformation = _advapi32.GetTokenInformation
    _kernel32.GetTokenInformation.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    _kernel32.GetTokenInformation.restype = wintypes.BOOL
    _advapi32.ConvertSidToStringSidW.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.LPWSTR),
    )
    _advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    _advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.DWORD),
    )
    _advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = (
        wintypes.BOOL
    )
    _advapi32.GetKernelObjectSecurity.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    _advapi32.GetKernelObjectSecurity.restype = wintypes.BOOL
    _advapi32.GetSecurityDescriptorDacl.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.BOOL),
        ctypes.POINTER(wintypes.LPVOID),
        ctypes.POINTER(wintypes.BOOL),
    )
    _advapi32.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    _advapi32.GetSecurityDescriptorControl.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(ctypes.c_ushort),
        ctypes.POINTER(wintypes.DWORD),
    )
    _advapi32.GetSecurityDescriptorControl.restype = wintypes.BOOL
    _advapi32.GetAce.argtypes = (
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.LPVOID),
    )
    _advapi32.GetAce.restype = wintypes.BOOL
    _kernel32.LocalFree.argtypes = (wintypes.HLOCAL,)
    _kernel32.LocalFree.restype = wintypes.HLOCAL
    _kernel32.CreateBoundaryDescriptorW.argtypes = (wintypes.LPCWSTR, wintypes.ULONG)
    _kernel32.CreateBoundaryDescriptorW.restype = wintypes.HANDLE
    _kernel32.AddSIDToBoundaryDescriptor.argtypes = (
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.LPVOID,
    )
    _kernel32.AddSIDToBoundaryDescriptor.restype = wintypes.BOOL
    _kernel32.DeleteBoundaryDescriptor.argtypes = (wintypes.HANDLE,)
    _kernel32.DeleteBoundaryDescriptor.restype = None
    _kernel32.CreatePrivateNamespaceW.argtypes = (
        ctypes.POINTER(_SECURITY_ATTRIBUTES),
        wintypes.HANDLE,
        wintypes.LPCWSTR,
    )
    _kernel32.CreatePrivateNamespaceW.restype = wintypes.HANDLE
    _kernel32.OpenPrivateNamespaceW.argtypes = (wintypes.HANDLE, wintypes.LPCWSTR)
    _kernel32.OpenPrivateNamespaceW.restype = wintypes.HANDLE
    _kernel32.ClosePrivateNamespace.argtypes = (wintypes.HANDLE, wintypes.ULONG)
    _kernel32.ClosePrivateNamespace.restype = ctypes.c_ubyte
    _kernel32.CreateMutexW.argtypes = (
        ctypes.POINTER(_SECURITY_ATTRIBUTES),
        wintypes.BOOL,
        wintypes.LPCWSTR,
    )
    _kernel32.CreateMutexW.restype = wintypes.HANDLE
    _kernel32.OpenMutexW.argtypes = (
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    )
    _kernel32.OpenMutexW.restype = wintypes.HANDLE
    _kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    _kernel32.WaitForSingleObject.restype = wintypes.DWORD
    _kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
    _kernel32.ReleaseMutex.restype = wintypes.BOOL
    _kernel32.CreatePipe.argtypes = (
        ctypes.POINTER(wintypes.HANDLE),
        ctypes.POINTER(wintypes.HANDLE),
        ctypes.POINTER(_SECURITY_ATTRIBUTES),
        wintypes.DWORD,
    )
    _kernel32.CreatePipe.restype = wintypes.BOOL
    _kernel32.SetHandleInformation.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    _kernel32.SetHandleInformation.restype = wintypes.BOOL
    _kernel32.DuplicateHandle.argtypes = (
        wintypes.HANDLE,
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    )
    _kernel32.DuplicateHandle.restype = wintypes.BOOL
    _kernel32.CreateEventW.argtypes = (
        ctypes.POINTER(_SECURITY_ATTRIBUTES),
        wintypes.BOOL,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    )
    _kernel32.CreateEventW.restype = wintypes.HANDLE
    _kernel32.SetEvent.argtypes = (wintypes.HANDLE,)
    _kernel32.SetEvent.restype = wintypes.BOOL
    _kernel32.ResetEvent.argtypes = (wintypes.HANDLE,)
    _kernel32.ResetEvent.restype = wintypes.BOOL
    _kernel32.GetCurrentThread.argtypes = ()
    _kernel32.GetCurrentThread.restype = wintypes.HANDLE
    _cancel_synchronous_io = getattr(_kernel32, "CancelSynchronousIo", None)
    if callable(_cancel_synchronous_io):
        _cancel_synchronous_io.argtypes = (wintypes.HANDLE,)
        _cancel_synchronous_io.restype = wintypes.BOOL
    _kernel32.GetProcessHandleCount.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    )
    _kernel32.GetProcessHandleCount.restype = wintypes.BOOL
    if _compare_object_handles is not None:
        _compare_object_handles.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        _compare_object_handles.restype = wintypes.BOOL
    _kernel32.CreateJobObjectW.argtypes = (
        ctypes.POINTER(_SECURITY_ATTRIBUTES),
        wintypes.LPCWSTR,
    )
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.QueryInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    _kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    _kernel32.InitializeProcThreadAttributeList.argtypes = (
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_size_t),
    )
    _kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
    _kernel32.UpdateProcThreadAttribute.argtypes = (
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.c_size_t,
        wintypes.LPVOID,
        ctypes.c_size_t,
        wintypes.LPVOID,
        ctypes.POINTER(ctypes.c_size_t),
    )
    _kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL
    _kernel32.DeleteProcThreadAttributeList.argtypes = (wintypes.LPVOID,)
    _kernel32.DeleteProcThreadAttributeList.restype = None
    _kernel32.CreateProcessW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.BOOL,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPCWSTR,
        wintypes.LPVOID,
        ctypes.POINTER(_PROCESS_INFORMATION),
    )
    _kernel32.CreateProcessW.restype = wintypes.BOOL
    _kernel32.GetProcessTimes.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_FILETIME),
        ctypes.POINTER(_FILETIME),
        ctypes.POINTER(_FILETIME),
        ctypes.POINTER(_FILETIME),
    )
    _kernel32.GetProcessTimes.restype = wintypes.BOOL
    _kernel32.GetExitCodeProcess.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    )
    _kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    _kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _kernel32.TerminateJobObject.restype = wintypes.BOOL
    _kernel32.IsProcessInJob.argtypes = (
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.BOOL),
    )
    _kernel32.IsProcessInJob.restype = wintypes.BOOL
    _iphlpapi.GetExtendedTcpTable.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.BOOL,
        wintypes.ULONG,
        ctypes.c_int,
        wintypes.ULONG,
    )
    _iphlpapi.GetExtendedTcpTable.restype = wintypes.ULONG
    _iphlpapi.GetExtendedUdpTable.argtypes = (
        wintypes.LPVOID,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.BOOL,
        wintypes.ULONG,
        ctypes.c_int,
        wintypes.ULONG,
    )
    _iphlpapi.GetExtendedUdpTable.restype = wintypes.ULONG
    _ntdll.NtQueryObject.argtypes = (
        wintypes.HANDLE,
        wintypes.ULONG,
        wintypes.LPVOID,
        wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG),
    )
    _ntdll.NtQueryObject.restype = ctypes.c_long
    _ntdll.NtQueryMutant.argtypes = (
        wintypes.HANDLE,
        wintypes.ULONG,
        wintypes.LPVOID,
        wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG),
    )
    _ntdll.NtQueryMutant.restype = ctypes.c_long
else:  # pragma: no cover - exercised by platform-refusal tests
    _kernel32 = None
    _kernelbase = None
    _compare_object_handles = None
    _advapi32 = None
    _iphlpapi = None
    _ntdll = None
    _cancel_synchronous_io = None


_held_lock = threading.Lock()
_phase_handles_lock = threading.Lock()
_child_creation_gate = threading.Lock()
_native_custody_gate = threading.RLock()
_owned_factory_window_active = threading.Event()
_retained_owned_handles_lock = threading.Lock()
_retained_owned_handles: set[int] = set()
_held_roots: set[str] = set()
_held_campaigns: set[str] = set()


def _require_windows() -> None:
    if _kernel32 is None or _advapi32 is None:
        _fail("dual_live_windows_unsupported")


def _require_sha256(value: object) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        _fail("dual_live_windows_arguments_invalid")
    return value


def _require_uuid4(value: object) -> str:
    if not isinstance(value, str):
        _fail("dual_live_windows_arguments_invalid")
    try:
        parsed = UUID(value)
    except ValueError:
        _fail("dual_live_windows_arguments_invalid")
    if parsed.version != 4 or str(parsed) != value:
        _fail("dual_live_windows_arguments_invalid")
    return value


def _close_handle(handle: int | None) -> None:
    if handle and _kernel32 is not None:
        if not _kernel32.CloseHandle(handle):
            _retain_owned_handle_for_retry(handle)
            _fail("dual_live_owned_handle_cleanup_failed")


def _object_security_bytes(handle: int, information: int) -> bytes:
    assert _advapi32 is not None
    needed = wintypes.DWORD()
    ctypes.set_last_error(0)
    _advapi32.GetKernelObjectSecurity(handle, information, None, 0, ctypes.byref(needed))
    if ctypes.get_last_error() != _ERROR_INSUFFICIENT_BUFFER or needed.value == 0:
        _fail("dual_live_windows_security_invalid")
    buffer = ctypes.create_string_buffer(needed.value)
    if not _advapi32.GetKernelObjectSecurity(
        handle, information, buffer, len(buffer), ctypes.byref(needed)
    ):
        _fail("dual_live_windows_security_invalid")
    return bytes(buffer.raw[: needed.value])


def _sid_text(sid_pointer: int) -> str:
    assert _advapi32 is not None and _kernel32 is not None
    text_pointer = wintypes.LPWSTR()
    if not _advapi32.ConvertSidToStringSidW(sid_pointer, ctypes.byref(text_pointer)):
        _fail("dual_live_windows_security_invalid")
    try:
        value = text_pointer.value
    finally:
        _kernel32.LocalFree(text_pointer)
    if not value:
        _fail("dual_live_windows_security_invalid")
    return value


def _dacl_entries(security_descriptor: bytes) -> tuple[tuple[str, int], ...]:
    assert _advapi32 is not None
    keepalive = ctypes.create_string_buffer(security_descriptor)
    pointer = ctypes.addressof(keepalive)
    control = ctypes.c_ushort()
    revision = wintypes.DWORD()
    if not _advapi32.GetSecurityDescriptorControl(
        pointer, ctypes.byref(control), ctypes.byref(revision)
    ):
        _fail("dual_live_windows_security_invalid")
    if not control.value & _SE_DACL_PROTECTED:
        _fail("dual_live_lock_acl_mismatch")
    present = wintypes.BOOL()
    defaulted = wintypes.BOOL()
    acl_pointer = wintypes.LPVOID()
    if not _advapi32.GetSecurityDescriptorDacl(
        pointer, ctypes.byref(present), ctypes.byref(acl_pointer), ctypes.byref(defaulted)
    ):
        _fail("dual_live_windows_security_invalid")
    if not present.value or not acl_pointer.value or defaulted.value:
        _fail("dual_live_windows_security_invalid")
    acl = ctypes.cast(acl_pointer, ctypes.POINTER(_ACL)).contents
    entries: list[tuple[str, int]] = []
    for index in range(acl.AceCount):
        ace_pointer = wintypes.LPVOID()
        if not _advapi32.GetAce(acl_pointer, index, ctypes.byref(ace_pointer)):
            _fail("dual_live_windows_security_invalid")
        header = ctypes.cast(ace_pointer, ctypes.POINTER(_ACE_HEADER)).contents
        if (
            header.AceType != _ACCESS_ALLOWED_ACE_TYPE
            or header.AceFlags != 0
            or header.AceSize < 12
        ):
            _fail("dual_live_lock_acl_mismatch")
        mask = ctypes.c_uint32.from_address(int(ace_pointer.value) + 4).value
        entries.append((_sid_text(int(ace_pointer.value) + 8), mask))
    return tuple(entries)


def _current_user_sid() -> tuple[ctypes.Array[ctypes.c_char], str]:
    assert _kernel32 is not None and _advapi32 is not None
    token = wintypes.HANDLE()
    if not _kernel32.OpenProcessToken(
        _kernel32.GetCurrentProcess(), _TOKEN_QUERY, ctypes.byref(token)
    ):
        _fail("dual_live_windows_security_invalid")
    try:
        needed = wintypes.DWORD()
        ctypes.set_last_error(0)
        _kernel32.GetTokenInformation(
            token, _TOKEN_USER_CLASS, None, 0, ctypes.byref(needed)
        )
        if ctypes.get_last_error() != _ERROR_INSUFFICIENT_BUFFER or needed.value == 0:
            _fail("dual_live_windows_security_invalid")
        token_user = ctypes.create_string_buffer(needed.value)
        if not _kernel32.GetTokenInformation(
            token,
            _TOKEN_USER_CLASS,
            token_user,
            len(token_user),
            ctypes.byref(needed),
        ):
            _fail("dual_live_windows_security_invalid")
        sid_pointer = ctypes.c_void_p.from_buffer(token_user).value
        if not sid_pointer:
            _fail("dual_live_windows_security_invalid")
        return token_user, _sid_text(sid_pointer)
    finally:
        _close_handle(token.value)


def current_user_sid_sha256() -> str:
    _require_windows()
    _, sid_text = _current_user_sid()
    return hashlib.sha256(sid_text.encode("utf-8")).hexdigest()


def _evidence_root_identity_from_handle(handle: int) -> str:
    assert _kernel32 is not None
    attributes = _FILE_ATTRIBUTE_TAG_INFO()
    if not _kernel32.GetFileInformationByHandleEx(
        handle,
        _FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(attributes),
        ctypes.sizeof(attributes),
    ):
        _fail("dual_live_evidence_root_invalid")
    if not attributes.FileAttributes & _FILE_ATTRIBUTE_DIRECTORY:
        _fail("dual_live_evidence_root_invalid")
    if attributes.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
        _fail("dual_live_evidence_root_reparse")
    file_id = _FILE_ID_INFO()
    if not _kernel32.GetFileInformationByHandleEx(
        handle,
        _FILE_ID_INFO_CLASS,
        ctypes.byref(file_id),
        ctypes.sizeof(file_id),
    ):
        _fail("dual_live_evidence_root_invalid")
    required = _kernel32.GetFinalPathNameByHandleW(handle, None, 0, 0)
    if required == 0:
        _fail("dual_live_evidence_root_invalid")
    final_path = ctypes.create_unicode_buffer(required + 1)
    written = _kernel32.GetFinalPathNameByHandleW(
        handle, final_path, len(final_path), 0
    )
    if written == 0 or written >= len(final_path):
        _fail("dual_live_evidence_root_invalid")
    security_sha256 = hashlib.sha256(
        _object_security_bytes(
            handle,
            _OWNER_SECURITY_INFORMATION
            | _GROUP_SECURITY_INFORMATION
            | _DACL_SECURITY_INFORMATION,
        )
    ).hexdigest()
    return hashlib.sha256(
        _canonical_json_bytes(
            {
                "file_id": bytes(file_id.FileId.Identifier).hex(),
                "final_path": final_path.value.replace("\\", "/").casefold(),
                "security_descriptor_sha256": security_sha256,
                "volume_serial_number": file_id.VolumeSerialNumber,
            }
        )
    ).hexdigest()


def _open_evidence_root(path: Path) -> tuple[int, str]:
    assert _kernel32 is not None
    expected_path = assert_fixed_local_no_reparse_path_before_open(
        path,
        code="dual_live_evidence_root_invalid",
        reparse_code="dual_live_evidence_root_reparse",
    )
    handle = _kernel32.CreateFileW(
        str(expected_path),
        _READ_CONTROL | _FILE_READ_ATTRIBUTES,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE,
        None,
        _OPEN_EXISTING,
        _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle in (None, ctypes.c_void_p(-1).value):
        _fail("dual_live_evidence_root_invalid")
    try:
        assert_open_handle_local_fixed(
            int(handle),
            expected_path=expected_path,
            code="dual_live_evidence_root_invalid",
        )
        return int(handle), _evidence_root_identity_from_handle(int(handle))
    except BaseException:
        _close_handle(handle)
        raise


class ProofLocks:
    __slots__ = (
        "root_identity_sha256",
        "campaign_identity_sha256",
        "_root_directory",
        "_namespace_handle",
        "_boundary_descriptor",
        "_security_descriptor",
        "_root_mutex",
        "_campaign_mutex",
        "_acquiring_thread_id",
        "_root_owned",
        "_campaign_owned",
        "_registered",
        "_closed",
    )

    def __init__(
        self,
        root_identity_sha256: str,
        campaign_identity_sha256: str,
    ) -> None:
        self.root_identity_sha256 = _require_sha256(root_identity_sha256)
        self.campaign_identity_sha256 = _require_sha256(campaign_identity_sha256)
        self._root_directory: int | None = None
        self._namespace_handle: int | None = None
        self._boundary_descriptor: int | None = None
        self._security_descriptor: int | None = None
        self._root_mutex: int | None = None
        self._campaign_mutex: int | None = None
        self._acquiring_thread_id: int | None = None
        self._root_owned = False
        self._campaign_owned = False
        self._registered = False
        self._closed = False

    @classmethod
    def _from_owned_handles(
        cls,
        root_identity_sha256: str,
        campaign_identity_sha256: str,
        *,
        root_directory: int,
        namespace_handle: int,
        boundary_descriptor: int,
        security_descriptor: int,
        root_mutex: int,
        campaign_mutex: int,
    ) -> ProofLocks:
        instance = cls(root_identity_sha256, campaign_identity_sha256)
        instance._root_directory = root_directory
        instance._namespace_handle = namespace_handle
        instance._boundary_descriptor = boundary_descriptor
        instance._security_descriptor = security_descriptor
        instance._root_mutex = root_mutex
        instance._campaign_mutex = campaign_mutex
        instance._acquiring_thread_id = threading.get_ident()
        instance._root_owned = True
        instance._campaign_owned = True
        instance._registered = True
        return instance

    def __enter__(self) -> ProofLocks:
        if self._closed:
            _fail("dual_live_lock_closed")
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        if (
            not self._root_owned
            and not self._campaign_owned
            and not self._registered
            and all(
                resource is None
                for resource in (
                    self._root_directory,
                    self._namespace_handle,
                    self._boundary_descriptor,
                    self._security_descriptor,
                    self._root_mutex,
                    self._campaign_mutex,
                )
            )
        ):
            self._closed = True
            return
        assert _kernel32 is not None
        if (
            self._root_owned or self._campaign_owned
        ) and threading.get_ident() != self._acquiring_thread_id:
            _fail("dual_live_lock_wrong_thread")
        if self._campaign_owned:
            assert self._campaign_mutex is not None
            if not _kernel32.ReleaseMutex(self._campaign_mutex):
                _fail("dual_live_lock_release_failed")
            self._campaign_owned = False
        if self._root_owned:
            assert self._root_mutex is not None
            if not _kernel32.ReleaseMutex(self._root_mutex):
                _fail("dual_live_lock_release_failed")
            self._root_owned = False

        cleanup_failed = False
        for name in ("_campaign_mutex", "_root_mutex", "_root_directory"):
            handle = getattr(self, name)
            if handle:
                if _kernel32.CloseHandle(handle):
                    setattr(self, name, None)
                else:
                    cleanup_failed = True
            else:
                setattr(self, name, None)
        if self._namespace_handle:
            if _kernel32.ClosePrivateNamespace(self._namespace_handle, 0):
                self._namespace_handle = None
            else:
                cleanup_failed = True
        else:
            self._namespace_handle = None
        if self._boundary_descriptor:
            _kernel32.DeleteBoundaryDescriptor(self._boundary_descriptor)
            self._boundary_descriptor = None
        if self._security_descriptor:
            if _kernel32.LocalFree(self._security_descriptor):
                cleanup_failed = True
            else:
                self._security_descriptor = None
        if cleanup_failed:
            _fail("dual_live_lock_cleanup_failed")
        if self._registered:
            with _held_lock:
                _held_roots.discard(self.root_identity_sha256)
                _held_campaigns.discard(self.campaign_identity_sha256)
            self._registered = False
        self._closed = True


def _wait_mutex(handle: int, wait_ms: int) -> bool:
    assert _kernel32 is not None
    result = _kernel32.WaitForSingleObject(handle, wait_ms)
    if result == _WAIT_OBJECT_0:
        return False
    if result == _WAIT_TIMEOUT:
        _fail("dual_live_lock_busy")
    if result == _WAIT_ABANDONED_0:
        return True
    if result == _WAIT_FAILED:
        _fail("dual_live_lock_access_refused")
    _fail("dual_live_lock_invalid")


def _verify_private_handle(handle: int, user_sid: str, expected_mask: int) -> None:
    assert _kernel32 is not None
    flags = wintypes.DWORD()
    if not _kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
        _fail("dual_live_windows_security_invalid")
    if flags.value & _HANDLE_FLAG_INHERIT:
        _fail("dual_live_windows_security_invalid")
    entries = _dacl_entries(
        _object_security_bytes(handle, _DACL_SECURITY_INFORMATION)
    )
    if entries != (("S-1-5-18", expected_mask), (user_sid, expected_mask)):
        _fail("dual_live_lock_acl_mismatch")


def _cleanup_failed_lock_acquisition(
    *,
    root_identity_sha256: str,
    campaign_identity_sha256: str,
    root_registered: bool,
    root_directory: int | None,
    namespace_handle: int | None,
    boundary_descriptor: int | None,
    security_descriptor: int | None,
    root_mutex: int | None,
    campaign_mutex: int | None,
    root_owned: bool,
    campaign_owned: bool,
    campaign_registered: bool | None = None,
) -> None:
    assert _kernel32 is not None
    cleanup_failed = False

    if campaign_owned:
        if _kernel32.ReleaseMutex(campaign_mutex):
            campaign_owned = False
        else:
            cleanup_failed = True
    if root_owned:
        if _kernel32.ReleaseMutex(root_mutex):
            root_owned = False
        else:
            cleanup_failed = True

    for handle, still_owned in (
        (campaign_mutex, campaign_owned),
        (root_mutex, root_owned),
        (root_directory, False),
    ):
        if handle and not still_owned and not _kernel32.CloseHandle(handle):
            cleanup_failed = True
    if namespace_handle and not _kernel32.ClosePrivateNamespace(namespace_handle, 0):
        cleanup_failed = True
    if boundary_descriptor:
        _kernel32.DeleteBoundaryDescriptor(boundary_descriptor)
    if security_descriptor and _kernel32.LocalFree(security_descriptor):
        cleanup_failed = True

    if cleanup_failed:
        _fail("dual_live_lock_cleanup_failed")
    if campaign_registered is None:
        campaign_registered = root_registered
    if root_registered or campaign_registered:
        with _held_lock:
            if root_registered:
                _held_roots.discard(root_identity_sha256)
            if campaign_registered:
                _held_campaigns.discard(campaign_identity_sha256)


def acquire_proof_locks(
    evidence_root: Path,
    campaign_id: str,
    campaign_fingerprint: str,
    campaign_definition_sha256: str,
    wait_ms: int = 0,
) -> ProofLocks:
    return _acquire_proof_locks(
        evidence_root,
        campaign_id,
        campaign_fingerprint,
        campaign_definition_sha256=campaign_definition_sha256,
        campaign_definition_sha256_resolver=None,
        wait_ms=wait_ms,
    )


def acquire_proof_locks_staged(
    evidence_root: Path,
    campaign_id: str,
    campaign_fingerprint: str,
    campaign_definition_sha256_resolver: Callable[[], str],
    wait_ms: int = 0,
) -> ProofLocks:
    return _acquire_proof_locks(
        evidence_root,
        campaign_id,
        campaign_fingerprint,
        campaign_definition_sha256=None,
        campaign_definition_sha256_resolver=(
            campaign_definition_sha256_resolver
        ),
        wait_ms=wait_ms,
    )


def _campaign_lock_identity_sha256(
    campaign_id: str,
    campaign_fingerprint: str,
    campaign_definition_sha256: str,
) -> str:
    return hashlib.sha256(
        _canonical_json_bytes(
            {
                "campaign_definition_sha256": campaign_definition_sha256,
                "campaign_fingerprint": campaign_fingerprint,
                "campaign_id": campaign_id,
            }
        )
    ).hexdigest()


def _require_named_mutex_owned_by_current_thread(
    handle: int,
    expected_name: str,
) -> None:
    assert _kernel32 is not None and _ntdll is not None
    if _compare_object_handles is None:
        _fail("dual_live_proof_locks_inactive")
    try:
        if _handle_type_name(handle) != "Mutant":
            _fail("dual_live_proof_locks_inactive")
    except DualLiveWindowsError as exc:
        if exc.code == "dual_live_proof_locks_inactive":
            raise
        raise DualLiveWindowsError(
            "dual_live_proof_locks_inactive"
        ) from exc

    information = _MUTANT_BASIC_INFORMATION()
    returned = wintypes.ULONG()
    status = int(
        _ntdll.NtQueryMutant(
            handle,
            0,
            ctypes.byref(information),
            ctypes.sizeof(information),
            ctypes.byref(returned),
        )
    ) & 0xFFFFFFFF
    if (
        status != 0
        or returned.value < ctypes.sizeof(information)
        or information.OwnedByCaller != 1
        or information.AbandonedState != 0
    ):
        _fail("dual_live_proof_locks_inactive")

    comparison_handle = _kernel32.OpenMutexW(
        _MUTEX_ALL_ACCESS,
        False,
        expected_name,
    )
    if not comparison_handle:
        _fail("dual_live_proof_locks_inactive")
    comparison_failed = False
    try:
        if not _kernel_objects_same(
            handle,
            int(comparison_handle),
            indeterminate_code="dual_live_proof_locks_inactive",
        ):
            comparison_failed = True
    finally:
        if not _kernel32.CloseHandle(comparison_handle):
            comparison_failed = True
    if comparison_failed:
        _fail("dual_live_proof_locks_inactive")


def _require_active_proof_locks(
    proof_locks: object,
    *,
    evidence_root: Path,
    campaign_id: str,
    campaign_fingerprint: str,
    campaign_definition_sha256: str,
    root_mutex_identity_sha256: str,
    campaign_mutex_identity_sha256: str,
) -> ProofLocks:
    """Bind exact live locks to independently-derived canonical authority."""

    _require_windows()
    if (
        type(proof_locks) is not ProofLocks
        or not isinstance(evidence_root, Path)
        or not evidence_root.is_absolute()
    ):
        _fail("dual_live_proof_locks_inactive")
    canonical_campaign_id = _require_uuid4(campaign_id)
    canonical_fingerprint = _require_sha256(campaign_fingerprint)
    canonical_definition_sha256 = _require_sha256(campaign_definition_sha256)
    expected_root_identity = _require_sha256(root_mutex_identity_sha256)
    expected_campaign_identity = _require_sha256(
        campaign_mutex_identity_sha256
    )
    root_handle: int | None = None
    try:
        root_handle, canonical_root_identity = _open_evidence_root(
            evidence_root
        )
    finally:
        if root_handle is not None:
            _close_handle(root_handle)
    canonical_campaign_identity = _campaign_lock_identity_sha256(
        canonical_campaign_id,
        canonical_fingerprint,
        canonical_definition_sha256,
    )
    if (
        expected_root_identity != canonical_root_identity
        or expected_campaign_identity != canonical_campaign_identity
        or proof_locks.root_identity_sha256 != canonical_root_identity
        or proof_locks.campaign_identity_sha256 != canonical_campaign_identity
    ):
        _fail("dual_live_proof_locks_identity_mismatch")

    resources = (
        proof_locks._root_directory,
        proof_locks._namespace_handle,
        proof_locks._boundary_descriptor,
        proof_locks._security_descriptor,
        proof_locks._root_mutex,
        proof_locks._campaign_mutex,
    )
    with _held_lock:
        active = (
            proof_locks._acquiring_thread_id == threading.get_ident()
            and proof_locks._root_owned
            and proof_locks._campaign_owned
            and proof_locks._registered
            and not proof_locks._closed
            and all(
                type(resource) is int and resource > 0
                for resource in resources
            )
            and canonical_root_identity in _held_roots
            and canonical_campaign_identity in _held_campaigns
        )
    if not active:
        _fail("dual_live_proof_locks_inactive")

    assert _kernel32 is not None
    root_directory = cast(int, proof_locks._root_directory)
    namespace_handle = cast(int, proof_locks._namespace_handle)
    root_mutex = cast(int, proof_locks._root_mutex)
    campaign_mutex = cast(int, proof_locks._campaign_mutex)
    try:
        stored_root_identity = _evidence_root_identity_from_handle(
            root_directory
        )
    except DualLiveWindowsError as exc:
        raise DualLiveWindowsError(
            "dual_live_proof_locks_inactive"
        ) from exc
    if stored_root_identity != canonical_root_identity:
        _fail("dual_live_proof_locks_identity_mismatch")
    flags = wintypes.DWORD()
    for handle in (
        root_directory,
        namespace_handle,
        root_mutex,
        campaign_mutex,
    ):
        if not _kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
            _fail("dual_live_proof_locks_inactive")
    _require_named_mutex_owned_by_current_thread(
        root_mutex,
        f"{_NAMESPACE_ALIAS}\\root-{canonical_root_identity}",
    )
    _require_named_mutex_owned_by_current_thread(
        campaign_mutex,
        f"{_NAMESPACE_ALIAS}\\campaign-{canonical_campaign_identity}",
    )
    return proof_locks


def _acquire_proof_locks(
    evidence_root: Path,
    campaign_id: str,
    campaign_fingerprint: str,
    *,
    campaign_definition_sha256: str | None,
    campaign_definition_sha256_resolver: Callable[[], str] | None,
    wait_ms: int,
) -> ProofLocks:
    _require_windows()
    if not isinstance(evidence_root, Path) or not evidence_root.is_absolute():
        _fail("dual_live_windows_arguments_invalid")
    campaign_id = _require_uuid4(campaign_id)
    campaign_fingerprint = _require_sha256(campaign_fingerprint)
    if campaign_definition_sha256 is not None:
        fixed_campaign_definition_sha256 = _require_sha256(
            campaign_definition_sha256
        )

        def definition_resolver() -> str:
            return fixed_campaign_definition_sha256

        campaign_identity_sha256 = _campaign_lock_identity_sha256(
            campaign_id,
            campaign_fingerprint,
            fixed_campaign_definition_sha256,
        )
    else:
        if not callable(campaign_definition_sha256_resolver):
            _fail("dual_live_windows_arguments_invalid")
        definition_resolver = campaign_definition_sha256_resolver
        campaign_identity_sha256 = ""
    if isinstance(wait_ms, bool) or not isinstance(wait_ms, int) or not 0 <= wait_ms < 2**32:
        _fail("dual_live_windows_arguments_invalid")

    root_directory, root_identity_sha256 = _open_evidence_root(evidence_root)
    sid_buffer: ctypes.Array[ctypes.c_char] | None = None
    security_descriptor = wintypes.LPVOID()
    boundary_descriptor: int | None = None
    namespace_handle: int | None = None
    root_mutex: int | None = None
    campaign_mutex: int | None = None
    root_owned = False
    campaign_owned = False
    root_registered = False
    campaign_registered = False
    try:
        with _held_lock:
            if (
                root_identity_sha256 in _held_roots
                or (
                    campaign_identity_sha256
                    and campaign_identity_sha256 in _held_campaigns
                )
            ):
                _fail("dual_live_lock_busy")
            root_registered = True
            _held_roots.add(root_identity_sha256)
            if campaign_identity_sha256:
                campaign_registered = True
                _held_campaigns.add(campaign_identity_sha256)
        sid_buffer, sid_text = _current_user_sid()
        sddl = f"D:P(A;;GA;;;SY)(A;;GA;;;{sid_text})"
        descriptor_size = wintypes.DWORD()
        assert _advapi32 is not None and _kernel32 is not None
        if not _advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl,
            _SDDL_REVISION_1,
            ctypes.byref(security_descriptor),
            ctypes.byref(descriptor_size),
        ):
            _fail("dual_live_windows_security_invalid")
        security_attributes = _SECURITY_ATTRIBUTES(
            ctypes.sizeof(_SECURITY_ATTRIBUTES), security_descriptor, False
        )
        boundary_descriptor = _kernel32.CreateBoundaryDescriptorW(_BOUNDARY_NAME, 0)
        if not boundary_descriptor:
            _fail("dual_live_lock_namespace_invalid")
        boundary_value = wintypes.HANDLE(boundary_descriptor)
        sid_pointer = ctypes.c_void_p.from_buffer(sid_buffer).value
        if not _kernel32.AddSIDToBoundaryDescriptor(
            ctypes.byref(boundary_value), sid_pointer
        ):
            _fail("dual_live_lock_namespace_invalid")
        boundary_descriptor = int(boundary_value.value)
        ctypes.set_last_error(0)
        namespace_handle = _kernel32.CreatePrivateNamespaceW(
            ctypes.byref(security_attributes), boundary_descriptor, _NAMESPACE_ALIAS
        )
        if not namespace_handle:
            if ctypes.get_last_error() != _ERROR_ALREADY_EXISTS:
                _fail("dual_live_lock_namespace_invalid")
            namespace_handle = _kernel32.OpenPrivateNamespaceW(
                boundary_descriptor, _NAMESPACE_ALIAS
            )
            if not namespace_handle:
                _fail("dual_live_lock_namespace_squatted")
        _verify_private_handle(
            namespace_handle, sid_text, _PRIVATE_NAMESPACE_ALL_ACCESS
        )
        ctypes.set_last_error(0)
        root_mutex = _kernel32.CreateMutexW(
            ctypes.byref(security_attributes),
            False,
            f"{_NAMESPACE_ALIAS}\\root-{root_identity_sha256}",
        )
        if not root_mutex:
            _fail("dual_live_lock_namespace_squatted")
        _verify_private_handle(root_mutex, sid_text, _MUTEX_ALL_ACCESS)
        root_abandoned = _wait_mutex(root_mutex, wait_ms)
        root_owned = True
        if root_abandoned:
            _fail("dual_live_lock_abandoned")
        resolved_campaign_definition_sha256 = _require_sha256(
            definition_resolver()
        )
        resolved_campaign_identity_sha256 = _campaign_lock_identity_sha256(
            campaign_id,
            campaign_fingerprint,
            resolved_campaign_definition_sha256,
        )
        if campaign_registered:
            if resolved_campaign_identity_sha256 != campaign_identity_sha256:
                _fail("dual_live_windows_arguments_invalid")
        else:
            with _held_lock:
                if resolved_campaign_identity_sha256 in _held_campaigns:
                    _fail("dual_live_lock_busy")
                campaign_identity_sha256 = resolved_campaign_identity_sha256
                campaign_registered = True
                _held_campaigns.add(campaign_identity_sha256)
        campaign_mutex = _kernel32.CreateMutexW(
            ctypes.byref(security_attributes),
            False,
            f"{_NAMESPACE_ALIAS}\\campaign-{campaign_identity_sha256}",
        )
        if not campaign_mutex:
            _fail("dual_live_lock_namespace_squatted")
        _verify_private_handle(campaign_mutex, sid_text, _MUTEX_ALL_ACCESS)
        campaign_abandoned = _wait_mutex(campaign_mutex, wait_ms)
        campaign_owned = True
        if campaign_abandoned:
            _fail("dual_live_lock_abandoned")
        return ProofLocks._from_owned_handles(
            root_identity_sha256,
            campaign_identity_sha256,
            root_directory=root_directory,
            namespace_handle=int(namespace_handle),
            boundary_descriptor=int(boundary_descriptor),
            security_descriptor=int(security_descriptor.value),
            root_mutex=int(root_mutex),
            campaign_mutex=int(campaign_mutex),
        )
    except BaseException:
        _cleanup_failed_lock_acquisition(
            root_identity_sha256=root_identity_sha256,
            campaign_identity_sha256=campaign_identity_sha256,
            root_registered=root_registered,
            root_directory=root_directory,
            namespace_handle=int(namespace_handle) if namespace_handle else None,
            boundary_descriptor=(
                int(boundary_descriptor) if boundary_descriptor else None
            ),
            security_descriptor=(
                int(security_descriptor.value) if security_descriptor.value else None
            ),
            root_mutex=int(root_mutex) if root_mutex else None,
            campaign_mutex=int(campaign_mutex) if campaign_mutex else None,
            root_owned=root_owned,
            campaign_owned=campaign_owned,
            campaign_registered=campaign_registered,
        )
        raise


def _require_job_apis() -> None:
    _require_windows()
    if _iphlpapi is None or _ntdll is None:
        _fail("dual_live_job_unsupported")
    assert _kernel32 is not None
    required = (
        "CreateJobObjectW",
        "SetInformationJobObject",
        "QueryInformationJobObject",
        "InitializeProcThreadAttributeList",
        "UpdateProcThreadAttribute",
        "DeleteProcThreadAttributeList",
        "CreateProcessW",
        "GetProcessTimes",
        "OpenProcess",
        "GetProcessId",
        "QueryFullProcessImageNameW",
        "GetNamedPipeInfo",
        "GetExitCodeProcess",
        "TerminateJobObject",
        "IsProcessInJob",
    )
    if any(not callable(getattr(_kernel32, name, None)) for name in required):
        _fail("dual_live_job_unsupported")
    if any(
        not callable(getattr(_iphlpapi, name, None))
        for name in ("GetExtendedTcpTable", "GetExtendedUdpTable")
    ):
        _fail("dual_live_job_unsupported")
    if not callable(getattr(_ntdll, "NtQueryObject", None)):
        _fail("dual_live_job_unsupported")


def _handle_type_name(handle: int) -> str:
    assert _ntdll is not None
    required = wintypes.ULONG()
    status = int(
        _ntdll.NtQueryObject(
            handle,
            _OBJECT_TYPE_INFORMATION_CLASS,
            None,
            0,
            ctypes.byref(required),
        )
    ) & 0xFFFFFFFF
    if status != _STATUS_INFO_LENGTH_MISMATCH or required.value < ctypes.sizeof(
        _UNICODE_STRING
    ):
        _fail("dual_live_job_inherited_handles_invalid")
    buffer = ctypes.create_string_buffer(required.value)
    returned = wintypes.ULONG()
    status = int(
        _ntdll.NtQueryObject(
            handle,
            _OBJECT_TYPE_INFORMATION_CLASS,
            buffer,
            len(buffer),
            ctypes.byref(returned),
        )
    ) & 0xFFFFFFFF
    if status != 0 or returned.value > len(buffer):
        _fail("dual_live_job_inherited_handles_invalid")
    type_name = ctypes.cast(buffer, ctypes.POINTER(_UNICODE_STRING)).contents
    if (
        not type_name.Buffer
        or type_name.Length == 0
        or type_name.Length % ctypes.sizeof(ctypes.c_wchar)
        or type_name.MaximumLength < type_name.Length
    ):
        _fail("dual_live_job_inherited_handles_invalid")
    try:
        return ctypes.wstring_at(
            type_name.Buffer,
            type_name.Length // ctypes.sizeof(ctypes.c_wchar),
        )
    except (OSError, ValueError):
        _fail("dual_live_job_inherited_handles_invalid")


def _validate_inherited_capability(handle: int) -> None:
    assert _kernel32 is not None
    type_name = _handle_type_name(handle)
    if type_name not in _PERMITTED_INHERITED_HANDLE_TYPES:
        _fail("dual_live_job_inherited_handles_invalid")
    if type_name == "Event":
        return
    if _kernel32.GetFileType(handle) != _FILE_TYPE_PIPE:
        _fail("dual_live_job_inherited_handles_invalid")
    pipe_flags = wintypes.DWORD()
    output_size = wintypes.DWORD()
    input_size = wintypes.DWORD()
    maximum_instances = wintypes.DWORD()
    if not _kernel32.GetNamedPipeInfo(
        handle,
        ctypes.byref(pipe_flags),
        ctypes.byref(output_size),
        ctypes.byref(input_size),
        ctypes.byref(maximum_instances),
    ):
        _fail("dual_live_job_inherited_handles_invalid")
    if pipe_flags.value not in (0, 1):
        _fail("dual_live_job_inherited_handles_invalid")


_PHASE_WRAPPER_PIPE_ROLES = (
    "wrapper_control_write_handle",
    "wrapper_stdin_write_handle",
    "wrapper_app_read_handle",
    "wrapper_http_read_handle",
    "wrapper_stdout_read_handle",
    "wrapper_stderr_read_handle",
)
_PHASE_WRAPPER_EVENT_ROLES = (
    "wrapper_revocation_event_handle",
    "wrapper_send_idle_event_handle",
    "wrapper_counter_ack_event_handle",
)
_PHASE_CHILD_PIPE_ROLES = (
    "child_control_read_handle",
    "child_stdio_stdin_read_handle",
    "child_app_write_handle",
    "child_http_write_handle",
    "child_stdout_write_handle",
    "child_stdio_stdout_write_handle",
    "child_stderr_write_handle",
    "child_stdio_stderr_write_handle",
)
_PHASE_CHILD_EVENT_ROLES = (
    "child_revocation_event_handle",
    "child_send_idle_event_handle",
    "child_counter_ack_event_handle",
)
_PHASE_WRAPPER_STREAM_PIPE_ROLES = _PHASE_WRAPPER_PIPE_ROLES[1:]
_PHASE_CHILD_STREAM_PIPE_ROLES = _PHASE_CHILD_PIPE_ROLES[1:]
_PHASE_WRAPPER_ROLES = _PHASE_WRAPPER_PIPE_ROLES + _PHASE_WRAPPER_EVENT_ROLES
_PHASE_CHILD_ROLES = _PHASE_CHILD_PIPE_ROLES + _PHASE_CHILD_EVENT_ROLES
_PHASE_HANDLE_ROLES = _PHASE_CHILD_ROLES + _PHASE_WRAPPER_ROLES
_PHASE_SHARED_PIPE_ROLE_PAIRS = frozenset(
    (
        frozenset(
            (
                "child_stdout_write_handle",
                "child_stdio_stdout_write_handle",
            )
        ),
        frozenset(
            (
                "child_stderr_write_handle",
                "child_stdio_stderr_write_handle",
            )
        ),
    )
)
_PHASE_CHANNELS_FACTORY_TOKEN = object()
_PHASE_PIPE_ENDS = {
    "wrapper_control_write_handle": _PIPE_CLIENT_END,
    "wrapper_stdin_write_handle": _PIPE_CLIENT_END,
    "wrapper_app_read_handle": _PIPE_SERVER_END,
    "wrapper_http_read_handle": _PIPE_SERVER_END,
    "wrapper_stdout_read_handle": _PIPE_SERVER_END,
    "wrapper_stderr_read_handle": _PIPE_SERVER_END,
    "child_control_read_handle": _PIPE_SERVER_END,
    "child_stdio_stdin_read_handle": _PIPE_SERVER_END,
    "child_app_write_handle": _PIPE_CLIENT_END,
    "child_http_write_handle": _PIPE_CLIENT_END,
    "child_stdout_write_handle": _PIPE_CLIENT_END,
    "child_stdio_stdout_write_handle": _PIPE_CLIENT_END,
    "child_stderr_write_handle": _PIPE_CLIENT_END,
    "child_stdio_stderr_write_handle": _PIPE_CLIENT_END,
}


def _require_phase_channels_factory_token(factory_token: object) -> None:
    if factory_token is not _PHASE_CHANNELS_FACTORY_TOKEN:
        _fail("dual_live_phase_channels_factory_only")


def _refuse_unrelated_subprocess(*args: object, **kwargs: object) -> NoReturn:
    del args, kwargs
    _fail("dual_live_subprocess_refused")


def _live_non_system_python_threads() -> tuple[threading.Thread, ...]:
    current = threading.current_thread()
    return tuple(
        thread
        for thread in threading.enumerate()
        if thread is not current
        and thread.is_alive()
        and type(thread).__name__ != "_DummyThread"
    )


def _register_subprocess_gate_baseline(baseline: object) -> None:
    """Bind the exact public-wrapper Popen denial once before runtime import."""

    global _SUBPROCESS_GATE_BASELINE
    global _SUBPROCESS_GATE_BASELINE_REGISTERED
    with _child_creation_gate:
        if _SUBPROCESS_GATE_BASELINE_REGISTERED:
            _fail("dual_live_subprocess_gate_baseline_already_registered")
        if (
            not callable(baseline)
            or baseline is _refuse_unrelated_subprocess
            or subprocess.Popen is not baseline
        ):
            _fail("dual_live_subprocess_gate_baseline_invalid")
        _SUBPROCESS_GATE_BASELINE = baseline
        _SUBPROCESS_GATE_BASELINE_REGISTERED = True


@contextmanager
def _owned_child_creation_window() -> Iterator[None]:
    """Guard the complete inheritable-handle window for one owned child.

    This blocks ordinary Python ``subprocess`` creation. It does not claim to
    contain malicious same-process code that cached a prior Popen/native entry
    point or invokes CreateProcess through a native extension.
    """

    with _child_creation_gate:
        baseline = _SUBPROCESS_GATE_BASELINE
        if not callable(baseline):
            _fail("dual_live_subprocess_gate_compromised")
        if subprocess.Popen is not baseline:
            setattr(subprocess, "Popen", baseline)
            _fail("dual_live_subprocess_gate_compromised")
        setattr(subprocess, "Popen", _refuse_unrelated_subprocess)
        try:
            if _live_non_system_python_threads():
                _fail("dual_live_subprocess_gate_busy")
            yield
        finally:
            gate_compromised = (
                subprocess.Popen is not _refuse_unrelated_subprocess
            )
            setattr(subprocess, "Popen", baseline)
            if gate_compromised:
                _fail("dual_live_subprocess_gate_compromised")


def _owned_child_capsule(
    *,
    phase: str,
    child_handles: Mapping[str, int],
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
) -> str:
    roles = _PHASE_CHILD_ROLES if phase == "A" else _PHASE_CHILD_PIPE_ROLES
    payload = {
        "handles": {role: child_handles[role] for role in roles},
        "phase": phase,
        "runtime_instance_id": runtime_instance_id,
        "schema_id": _OWNED_CHILD_SCHEMA_ID,
        "wrapper_nonce_sha256": wrapper_nonce_sha256,
    }
    encoded = base64.urlsafe_b64encode(_canonical_json_bytes(payload))
    return encoded.rstrip(b"=").decode("ascii")


def _owned_child_argv(capsule: str) -> tuple[str, ...]:
    root = Path(__file__).resolve().parents[3]
    tool = root / "tools" / "dual_live_run.py"
    return (
        str(_current_process_image_path()),
        "-I",
        "-B",
        "-X",
        "pycache_prefix=NUL",
        str(tool),
        "--owned-child",
        capsule,
    )


def _owned_child_environment(
    phase: str | None = None,
    supplied: Mapping[str, str] | None = None,
) -> Mapping[str, str]:
    environment = {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    for name in ("SYSTEMROOT", "WINDIR"):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    if supplied is not None:
        validated_phase = _require_phase(phase or "")
        allowed = (
            _OWNED_PHASE_A_ENVIRONMENT
            if validated_phase == "A"
            else _OWNED_PHASE_B_ENVIRONMENT
        )
        canonical_names = tuple(name.upper() for name in supplied)
        if (
            len(canonical_names) != len(set(canonical_names))
            or set(canonical_names) != allowed
            or any(
                not isinstance(name, str)
                or name != name.upper()
                or not isinstance(value, str)
                or not value
                or "\x00" in value
                for name, value in supplied.items()
            )
        ):
            _fail("dual_live_owned_environment_invalid")
        environment.update(supplied)
    return MappingProxyType(environment)


def _require_phase_channel_apis() -> None:
    _require_windows()
    if _ntdll is None or not callable(_compare_object_handles):
        _fail("dual_live_job_unsupported")
    assert _kernel32 is not None
    required = (
        "CloseHandle",
        "CancelSynchronousIo",
        "CreateEventW",
        "CreatePipe",
        "DuplicateHandle",
        "GetCurrentProcess",
        "GetCurrentThread",
        "GetFileType",
        "GetHandleInformation",
        "GetNamedPipeInfo",
        "ReadFile",
        "ResetEvent",
        "SetEvent",
        "SetHandleInformation",
        "WaitForSingleObject",
        "WriteFile",
    )
    if any(not callable(getattr(_kernel32, name, None)) for name in required) or not callable(
        _cancel_synchronous_io
    ):
        _fail("dual_live_job_unsupported")
    if not callable(getattr(_ntdll, "NtQueryObject", None)):
        _fail("dual_live_job_unsupported")


def _require_phase(value: object) -> str:
    if not isinstance(value, str) or value not in {"A", "B"}:
        _fail("dual_live_windows_arguments_invalid")
    return value


def _validate_pipe_capability_for_comparison(handle: object) -> int:
    if isinstance(handle, bool) or not isinstance(handle, int) or handle <= 0:
        _fail("dual_live_phase_channels_invalid")
    assert _kernel32 is not None
    flags = wintypes.DWORD()
    if not _kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
        _fail("dual_live_phase_channels_invalid")
    if flags.value not in (0, _HANDLE_FLAG_INHERIT):
        _fail("dual_live_phase_channels_invalid")
    if _handle_type_name(handle) != "File":
        _fail("dual_live_phase_channels_invalid")
    if _kernel32.GetFileType(handle) != _FILE_TYPE_PIPE:
        _fail("dual_live_phase_channels_invalid")
    pipe_flags = wintypes.DWORD()
    if not _kernel32.GetNamedPipeInfo(handle, ctypes.byref(pipe_flags), None, None, None):
        _fail("dual_live_phase_channels_invalid")
    if pipe_flags.value not in (_PIPE_CLIENT_END, _PIPE_SERVER_END):
        _fail("dual_live_phase_channels_invalid")
    return handle


def pipe_capabilities_same(first_handle: int, second_handle: int) -> bool:
    """Return only whether two valid pipe handles name the same kernel object."""

    _require_phase_channel_apis()
    first = _validate_pipe_capability_for_comparison(first_handle)
    second = _validate_pipe_capability_for_comparison(second_handle)
    return _kernel_objects_same(
        first,
        second,
        indeterminate_code="dual_live_phase_pipe_identity_indeterminate",
    )


def _kernel_objects_same(
    first_handle: int,
    second_handle: int,
    *,
    indeterminate_code: str,
) -> bool:
    assert _compare_object_handles is not None
    ctypes.set_last_error(0)
    if _compare_object_handles(first_handle, second_handle):
        return True
    if ctypes.get_last_error() == _ERROR_NOT_SAME_OBJECT:
        return False
    _fail(indeterminate_code)


def _pipe_handle_from_descriptor(descriptor: object) -> int:
    if (
        isinstance(descriptor, bool)
        or not isinstance(descriptor, int)
        or descriptor < 0
    ):
        _fail("dual_live_phase_channels_invalid")
    if _msvcrt is None:
        _fail("dual_live_windows_unsupported")
    try:
        return int(_msvcrt.get_osfhandle(descriptor))
    except (OSError, OverflowError, ValueError):
        _fail("dual_live_phase_channels_invalid")


def pipe_descriptors_same(first_descriptor: int, second_descriptor: int) -> bool:
    """Return whether two valid Windows pipe descriptors name one kernel object."""

    _require_phase_channel_apis()
    first_handle = _pipe_handle_from_descriptor(first_descriptor)
    second_handle = _pipe_handle_from_descriptor(second_descriptor)
    return pipe_capabilities_same(first_handle, second_handle)


def _validate_distinct_pipe_capabilities(handles: Sequence[int]) -> None:
    for index, left in enumerate(handles):
        for right in handles[index + 1 :]:
            if pipe_capabilities_same(left, right):
                _fail("dual_live_phase_channels_invalid")


def _validate_phase_pipe_relationships(handles: Mapping[str, int]) -> None:
    items = tuple(handles.items())
    for index, (left_role, left_handle) in enumerate(items):
        for right_role, right_handle in items[index + 1 :]:
            expected_same = (
                frozenset((left_role, right_role))
                in _PHASE_SHARED_PIPE_ROLE_PAIRS
            )
            if pipe_capabilities_same(left_handle, right_handle) != expected_same:
                _fail("dual_live_phase_channels_invalid")


def _validate_phase_handle(
    role: str,
    handle: int,
    *,
    inheritable: bool,
) -> None:
    assert _kernel32 is not None
    flags = wintypes.DWORD()
    if not _kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
        _fail("dual_live_phase_channels_invalid")
    expected_flags = _HANDLE_FLAG_INHERIT if inheritable else 0
    if flags.value != expected_flags:
        _fail("dual_live_phase_channels_invalid")
    type_name = _handle_type_name(handle)
    if role in _PHASE_WRAPPER_EVENT_ROLES + _PHASE_CHILD_EVENT_ROLES:
        if type_name != "Event":
            _fail("dual_live_phase_channels_invalid")
        return
    if type_name != "File" or _kernel32.GetFileType(handle) != _FILE_TYPE_PIPE:
        _fail("dual_live_phase_channels_invalid")
    pipe_flags = wintypes.DWORD()
    if not _kernel32.GetNamedPipeInfo(handle, ctypes.byref(pipe_flags), None, None, None):
        _fail("dual_live_phase_channels_invalid")
    if pipe_flags.value != _PHASE_PIPE_ENDS[role]:
        _fail("dual_live_phase_channels_invalid")


def _validated_phase_handles(
    phase: object,
    handles: Mapping[str, int | None],
) -> tuple[str, dict[str, int | None]]:
    _require_phase_channel_apis()
    validated_phase = _require_phase(phase)
    if set(handles) != set(_PHASE_WRAPPER_ROLES + _PHASE_CHILD_ROLES):
        _fail("dual_live_phase_channels_invalid")
    event_roles = _PHASE_WRAPPER_EVENT_ROLES + _PHASE_CHILD_EVENT_ROLES
    copied = dict(handles)
    for role, handle in copied.items():
        required = validated_phase == "A" or role not in event_roles
        if required:
            if isinstance(handle, bool) or not isinstance(handle, int) or handle <= 0:
                _fail("dual_live_phase_channels_invalid")
        elif handle is not None:
            _fail("dual_live_phase_channels_invalid")
    live_handles = tuple(handle for handle in copied.values() if handle is not None)
    if len(set(live_handles)) != len(live_handles):
        _fail("dual_live_phase_channels_invalid")
    for role in _PHASE_WRAPPER_ROLES + _PHASE_CHILD_ROLES:
        handle = copied[role]
        if handle is not None:
            _validate_phase_handle(role, handle, inheritable=False)
    pipe_handles = {
        role: handle
        for role in _PHASE_WRAPPER_PIPE_ROLES + _PHASE_CHILD_PIPE_ROLES
        if (handle := copied[role]) is not None
    }
    _validate_phase_pipe_relationships(pipe_handles)
    if validated_phase == "A":
        wrapper_revocation = copied["wrapper_revocation_event_handle"]
        child_revocation = copied["child_revocation_event_handle"]
        wrapper_send_idle = copied["wrapper_send_idle_event_handle"]
        child_send_idle = copied["child_send_idle_event_handle"]
        wrapper_counter_ack = copied["wrapper_counter_ack_event_handle"]
        child_counter_ack = copied["child_counter_ack_event_handle"]
        assert isinstance(wrapper_revocation, int)
        assert isinstance(child_revocation, int)
        assert isinstance(wrapper_send_idle, int)
        assert isinstance(child_send_idle, int)
        assert isinstance(wrapper_counter_ack, int)
        assert isinstance(child_counter_ack, int)
        revocation = (
            wrapper_revocation,
            child_revocation,
        )
        send_idle = (
            wrapper_send_idle,
            child_send_idle,
        )
        counter_ack = (
            wrapper_counter_ack,
            child_counter_ack,
        )
        if not _kernel_objects_same(
            revocation[0],
            revocation[1],
            indeterminate_code="dual_live_phase_capability_identity_indeterminate",
        ) or not _kernel_objects_same(
            send_idle[0],
            send_idle[1],
            indeterminate_code="dual_live_phase_capability_identity_indeterminate",
        ):
            _fail("dual_live_phase_channels_invalid")
        if not _kernel_objects_same(
            counter_ack[0],
            counter_ack[1],
            indeterminate_code="dual_live_phase_capability_identity_indeterminate",
        ):
            _fail("dual_live_phase_channels_invalid")
        for revocation_handle in revocation:
            for send_idle_handle in send_idle:
                if _kernel_objects_same(
                    revocation_handle,
                    send_idle_handle,
                    indeterminate_code=(
                        "dual_live_phase_capability_identity_indeterminate"
                    ),
                ):
                    _fail("dual_live_phase_channels_invalid")
            for counter_ack_handle in counter_ack:
                if _kernel_objects_same(
                    revocation_handle,
                    counter_ack_handle,
                    indeterminate_code=(
                        "dual_live_phase_capability_identity_indeterminate"
                    ),
                ):
                    _fail("dual_live_phase_channels_invalid")
        for send_idle_handle in send_idle:
            for counter_ack_handle in counter_ack:
                if _kernel_objects_same(
                    send_idle_handle,
                    counter_ack_handle,
                    indeterminate_code=(
                        "dual_live_phase_capability_identity_indeterminate"
                    ),
                ):
                    _fail("dual_live_phase_channels_invalid")
    return validated_phase, copied


class PhaseChannels:
    __slots__ = ("_phase", "_handles")

    _phase: str
    _handles: dict[str, int | None]

    def __new__(cls, *args: object, **kwargs: object) -> PhaseChannels:
        _fail("dual_live_phase_channels_factory_only")

    @classmethod
    def _from_factory(
        cls,
        factory_token: object,
        *,
        phase: str,
        handles: Mapping[str, int | None],
    ) -> PhaseChannels:
        _require_phase_channels_factory_token(factory_token)
        validated_phase, validated_handles = _validated_phase_handles(phase, handles)
        instance = object.__new__(cls)
        instance._phase = validated_phase
        instance._handles = validated_handles
        return instance

    @property
    def phase(self) -> str:
        return self._phase

    def _duplicate_roles(
        self,
        roles: Sequence[str],
        *,
        inheritable: bool,
    ) -> tuple[dict[str, int], dict[str, int]]:
        _require_phase_channel_apis()
        assert _kernel32 is not None
        duplicates: dict[str, int | None] = {role: None for role in roles}
        guards: dict[str, int | None] = {role: None for role in roles}
        with _phase_handles_lock:
            originals = {role: self._handles[role] for role in roles}
            if any(handle is None for handle in originals.values()):
                _fail("dual_live_phase_channels_closed")
            current_process = _kernel32.GetCurrentProcess()
            if not current_process:
                _fail("dual_live_phase_channels_lease_failed")
            try:
                for role, source_handle in originals.items():
                    assert source_handle is not None
                    duplicate = wintypes.HANDLE()
                    created = _kernel32.DuplicateHandle(
                        current_process,
                        source_handle,
                        current_process,
                        ctypes.byref(duplicate),
                        0,
                        inheritable,
                        _DUPLICATE_SAME_ACCESS,
                    )
                    if duplicate.value:
                        duplicates[role] = int(duplicate.value)
                    if not created or not duplicate.value:
                        _fail("dual_live_phase_channels_lease_failed")
                    _validate_phase_handle(
                        role,
                        int(duplicate.value),
                        inheritable=inheritable,
                    )
                    guard = wintypes.HANDLE()
                    guarded = _kernel32.DuplicateHandle(
                        current_process,
                        source_handle,
                        current_process,
                        ctypes.byref(guard),
                        0,
                        False,
                        _DUPLICATE_SAME_ACCESS,
                    )
                    if guard.value:
                        guards[role] = int(guard.value)
                    if not guarded or not guard.value:
                        _fail("dual_live_phase_channels_lease_failed")
                    _validate_phase_handle(
                        role,
                        int(guard.value),
                        inheritable=False,
                    )
                    if not _kernel_objects_same(
                        int(duplicate.value),
                        int(guard.value),
                        indeterminate_code="dual_live_phase_channels_lease_failed",
                    ):
                        _fail("dual_live_phase_channels_lease_failed")
            except BaseException:
                cleanup_ok = _close_provisional_phase_lease_handles(
                    duplicates,
                    guards,
                )
                if not cleanup_ok:
                    cleanup_ok = _close_provisional_phase_lease_handles(
                        duplicates,
                        guards,
                    )
                if not cleanup_ok:
                    _retain_failed_phase_handle_custody(
                        duplicates,
                        guards,
                        mode="pre_yield",
                    )
                    _fail("dual_live_phase_channels_cleanup_failed")
                raise
        return (
            {
                role: int(handle)
                for role, handle in duplicates.items()
                if handle is not None
            },
            {
                role: int(handle)
                for role, handle in guards.items()
                if handle is not None
            },
        )

    @contextmanager
    def _lease_roles(
        self,
        roles: Sequence[str],
        *,
        inheritable: bool,
    ) -> Iterator[Mapping[str, int]]:
        with _native_custody_gate:
            _drain_native_custody()
            handles, guards = self._duplicate_roles(
                roles,
                inheritable=inheritable,
            )
            try:
                yield MappingProxyType(handles)
            finally:
                cleanup_ok, lease_compromised = (
                    _close_guarded_phase_lease_handles(
                        handles,
                        guards,
                    )
                )
                if not cleanup_ok:
                    cleanup_ok, retry_compromised = (
                        _close_guarded_phase_lease_handles(
                            handles,
                            guards,
                        )
                    )
                    lease_compromised = (
                        lease_compromised or retry_compromised
                    )
                if cleanup_ok:
                    handles.clear()
                    guards.clear()
                else:
                    _retain_failed_phase_handle_custody(
                        cast(dict[str, int | None], handles),
                        cast(dict[str, int | None], guards),
                        mode="guarded_yield",
                    )
                    _fail("dual_live_phase_channels_cleanup_failed")
                if lease_compromised:
                    _fail("dual_live_phase_channels_lease_compromised")

    def _lease_wrapper_handles(
        self,
        factory_token: object,
    ) -> AbstractContextManager[Mapping[str, int]]:
        """Private test seam for borrowed noninheritable wrapper handles."""

        _require_phase_channels_factory_token(factory_token)
        roles = (
            _PHASE_WRAPPER_ROLES
            if self._phase == "A"
            else _PHASE_WRAPPER_PIPE_ROLES
        )
        return self._lease_roles(roles, inheritable=False)

    def _lease_child_handles(
        self,
        factory_token: object,
    ) -> AbstractContextManager[Mapping[str, int]]:
        """Private test seam; production admission owns the complete window."""

        _require_phase_channels_factory_token(factory_token)
        roles = _PHASE_CHILD_ROLES if self._phase == "A" else _PHASE_CHILD_PIPE_ROLES
        return self._lease_roles(roles, inheritable=True)

    def validate_stream_pipe_capabilities(self) -> None:
        wrapper_roles = _PHASE_WRAPPER_STREAM_PIPE_ROLES
        child_roles = _PHASE_CHILD_STREAM_PIPE_ROLES
        with self._lease_roles(wrapper_roles, inheritable=False) as wrapper_handles:
            with self._lease_roles(child_roles, inheritable=False) as child_handles:
                _validate_phase_pipe_relationships(
                    {**wrapper_handles, **child_handles}
                )

    def _admit_owned_child(
        self,
        factory_token: object,
        *,
        runtime_instance_id: str,
        wrapper_nonce_sha256: str,
        environment: Mapping[str, str] | None = None,
    ) -> JobChild:
        """Create the exact inert owned child inside one atomic inherit window."""

        _require_phase_channels_factory_token(factory_token)
        runtime_instance_id = _require_uuid4(runtime_instance_id)
        wrapper_nonce_sha256 = _require_sha256(wrapper_nonce_sha256)
        child: JobChild | None = None
        try:
            with _owned_child_creation_window():
                with self._lease_child_handles(
                    _PHASE_CHANNELS_FACTORY_TOKEN
                ) as child_handles:
                    capsule = _owned_child_capsule(
                        phase=self._phase,
                        child_handles=child_handles,
                        runtime_instance_id=runtime_instance_id,
                        wrapper_nonce_sha256=wrapper_nonce_sha256,
                    )
                    child = create_child_in_job(
                        argv=_owned_child_argv(capsule),
                        environment=_owned_child_environment(
                            self._phase,
                            environment,
                        ),
                        inherited_handles=tuple(child_handles.values()),
                        runtime_instance_id=runtime_instance_id,
                        wrapper_nonce_sha256=wrapper_nonce_sha256,
                        standard_handles=(
                            child_handles["child_stdio_stdin_read_handle"],
                            child_handles["child_stdio_stdout_write_handle"],
                            child_handles["child_stdio_stderr_write_handle"],
                        ),
                    )
            self.close_child_handles_after_admission()
            return child
        except BaseException as admission_failure:
            if not isinstance(child, JobChild):
                raise
            custody = _OwnedCleanupCustody(child=child)
            cleanup_failure: BaseException | None = None
            for _ in range(2):
                try:
                    custody.retry()
                except BaseException as exc:
                    cleanup_failure = exc
                else:
                    raise
            _retain_failed_owned_custody(custody)
            cleanup = DualLiveWindowsError(
                "dual_live_owned_child_cleanup_failed"
            )
            cleanup.__context__ = admission_failure
            assert cleanup_failure is not None
            raise cleanup from cleanup_failure

    @property
    def closed(self) -> bool:
        with _phase_handles_lock:
            return all(handle is None for handle in self._handles.values())

    def __enter__(self) -> PhaseChannels:
        if self.closed:
            _fail("dual_live_phase_channels_closed")
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _close_roles(self, roles: Sequence[str]) -> None:
        with _phase_handles_lock:
            assert _kernel32 is not None or all(
                self._handles[role] is None for role in roles
            )
            cleanup_failed = False
            for role in roles:
                handle = self._handles[role]
                if handle is None:
                    continue
                if _kernel32 is not None and _kernel32.CloseHandle(handle):
                    self._handles[role] = None
                else:
                    cleanup_failed = True
            if cleanup_failed:
                _fail("dual_live_phase_channels_cleanup_failed")

    def close_child_handles_after_admission(self) -> None:
        self._close_roles(_PHASE_CHILD_ROLES)

    def close(self) -> None:
        self._close_roles(_PHASE_HANDLE_ROLES)


def _close_provisional_phase_handles(handles: dict[str, int | None]) -> bool:
    assert _kernel32 is not None
    cleanup_ok = True
    for handle in tuple(dict.fromkeys(value for value in handles.values() if value)):
        if _kernel32.CloseHandle(handle):
            for role, value in handles.items():
                if value == handle:
                    handles[role] = None
        else:
            cleanup_ok = False
    return cleanup_ok and all(handle is None for handle in handles.values())


def _close_provisional_phase_lease_handles(
    handles: dict[str, int | None],
    guards: dict[str, int | None],
) -> bool:
    handles_ok = _close_provisional_phase_handles(handles)
    guards_ok = _close_provisional_phase_handles(guards)
    return handles_ok and guards_ok


def _close_guarded_phase_lease_handles(
    handles: dict[str, int],
    guards: dict[str, int],
) -> tuple[bool, bool]:
    assert _kernel32 is not None
    cleanup_ok = True
    lease_compromised = False
    for role in tuple(dict.fromkeys((*handles, *guards))):
        handle = handles.get(role)
        guard = guards.get(role)
        if handle is not None:
            if guard is None:
                cleanup_ok = False
                continue
            flags = wintypes.DWORD()
            ctypes.set_last_error(0)
            if not _kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
                if ctypes.get_last_error() == _ERROR_INVALID_HANDLE:
                    handles.pop(role, None)
                    lease_compromised = True
                else:
                    cleanup_ok = False
            else:
                try:
                    same_object = _kernel_objects_same(
                        handle,
                        guard,
                        indeterminate_code="dual_live_phase_channels_cleanup_failed",
                    )
                except DualLiveWindowsError:
                    cleanup_ok = False
                else:
                    if not same_object:
                        handles.pop(role, None)
                        lease_compromised = True
                    elif _kernel32.CloseHandle(handle):
                        handles.pop(role, None)
                    else:
                        cleanup_ok = False
        if role not in handles and guard is not None:
            if _kernel32.CloseHandle(guard):
                guards.pop(role, None)
            else:
                cleanup_ok = False
    return cleanup_ok and not handles and not guards, lease_compromised


class _PhaseHandleCustody:
    __slots__ = (
        "guards",
        "handles",
        "lease_compromised",
        "mode",
    )

    def __init__(
        self,
        *,
        handles: dict[str, int | None],
        guards: dict[str, int | None] | None,
        mode: str,
    ) -> None:
        if mode not in {"build", "pre_yield", "guarded_yield"}:
            _fail("dual_live_phase_channels_cleanup_failed")
        self.handles = handles
        self.guards = guards if guards is not None else {}
        self.mode = mode
        self.lease_compromised = False

    @property
    def released(self) -> bool:
        return not any(
            handle is not None
            for handle in (*self.handles.values(), *self.guards.values())
        )

    def retry(self) -> None:
        if self.released:
            self.handles.clear()
            self.guards.clear()
            return
        if self.mode == "build":
            cleanup_ok = _close_provisional_phase_handles(self.handles)
        elif self.mode == "pre_yield":
            cleanup_ok = _close_provisional_phase_lease_handles(
                self.handles,
                self.guards,
            )
        else:
            cleanup_ok, compromised = _close_guarded_phase_lease_handles(
                cast(dict[str, int], self.handles),
                cast(dict[str, int], self.guards),
            )
            self.lease_compromised = self.lease_compromised or compromised
        if not cleanup_ok:
            _fail("dual_live_phase_channels_cleanup_failed")
        self.handles.clear()
        self.guards.clear()


_failed_phase_handle_custody_lock = threading.Lock()
_failed_phase_handle_custodies: list[_PhaseHandleCustody] = []


def _retain_failed_phase_handle_custody(
    handles: dict[str, int | None],
    guards: dict[str, int | None] | None = None,
    *,
    mode: str,
) -> None:
    custody = _PhaseHandleCustody(
        handles=handles,
        guards=guards,
        mode=mode,
    )
    if custody.released:
        return
    with _failed_phase_handle_custody_lock:
        _failed_phase_handle_custodies.append(custody)


def _retry_failed_phase_handle_custodies() -> None:
    failures: list[BaseException] = []
    lease_compromised = False
    with _native_custody_gate:
        with _failed_phase_handle_custody_lock:
            for custody in tuple(_failed_phase_handle_custodies):
                try:
                    custody.retry()
                except BaseException as exc:
                    failures.append(exc)
                else:
                    if custody.released:
                        _failed_phase_handle_custodies.remove(custody)
                    else:
                        failures.append(
                            DualLiveWindowsError(
                                "dual_live_phase_channels_cleanup_failed"
                            )
                        )
                    lease_compromised = (
                        lease_compromised or custody.lease_compromised
                    )
    if failures:
        raise DualLiveWindowsError(
            "dual_live_phase_channels_cleanup_failed"
        ) from failures[0]
    if lease_compromised:
        _fail("dual_live_phase_channels_lease_compromised")


def _create_phase_channels_locked(phase: str) -> PhaseChannels:
    _require_phase_channel_apis()
    validated_phase = _require_phase(phase)
    assert _kernel32 is not None
    handles: dict[str, int | None] = {
        role: None for role in _PHASE_WRAPPER_ROLES + _PHASE_CHILD_ROLES
    }
    current_process = _kernel32.GetCurrentProcess()
    if not current_process:
        _fail("dual_live_phase_channels_create_failed")

    def duplicate_child(source_handle: int, child_role: str) -> None:
        duplicate = wintypes.HANDLE()
        created = _kernel32.DuplicateHandle(
            current_process,
            source_handle,
            current_process,
            ctypes.byref(duplicate),
            0,
            False,
            _DUPLICATE_SAME_ACCESS,
        )
        if duplicate.value:
            handles[child_role] = int(duplicate.value)
        if not created or not duplicate.value:
            _fail("dual_live_phase_channels_create_failed")

    def create_pipe(
        wrapper_role: str,
        child_role: str,
        *,
        wrapper_reads: bool,
        shared_child_role: str | None = None,
    ) -> None:
        read_handle = wintypes.HANDLE()
        write_handle = wintypes.HANDLE()
        security = _SECURITY_ATTRIBUTES(
            ctypes.sizeof(_SECURITY_ATTRIBUTES),
            None,
            False,
        )
        source_role = f"source:{child_role}"
        read_role = wrapper_role if wrapper_reads else source_role
        write_role = source_role if wrapper_reads else wrapper_role
        created = _kernel32.CreatePipe(
            ctypes.byref(read_handle),
            ctypes.byref(write_handle),
            ctypes.byref(security),
            0,
        )
        if read_handle.value:
            handles[read_role] = int(read_handle.value)
        if write_handle.value:
            handles[write_role] = int(write_handle.value)
        if not created or not read_handle.value or not write_handle.value:
            _fail("dual_live_phase_channels_create_failed")
        source_handle = handles[source_role]
        assert source_handle is not None
        duplicate_child(source_handle, child_role)
        if shared_child_role is not None:
            duplicate_child(source_handle, shared_child_role)
        if not _kernel32.CloseHandle(source_handle):
            _fail("dual_live_phase_channels_cleanup_failed")
        del handles[source_role]

    def create_event(
        wrapper_role: str,
        child_role: str,
        *,
        initially_signaled: bool,
    ) -> None:
        event_handle = _kernel32.CreateEventW(
            None,
            True,
            initially_signaled,
            None,
        )
        if not event_handle:
            _fail("dual_live_phase_channels_create_failed")
        handles[wrapper_role] = int(event_handle)
        wrapper_handle = handles[wrapper_role]
        assert wrapper_handle is not None
        duplicate_child(wrapper_handle, child_role)

    try:
        create_pipe(
            "wrapper_control_write_handle",
            "child_control_read_handle",
            wrapper_reads=False,
        )
        create_pipe(
            "wrapper_stdin_write_handle",
            "child_stdio_stdin_read_handle",
            wrapper_reads=False,
        )
        for stream in ("app", "http"):
            create_pipe(
                f"wrapper_{stream}_read_handle",
                f"child_{stream}_write_handle",
                wrapper_reads=True,
            )
        for stream in ("stdout", "stderr"):
            create_pipe(
                f"wrapper_{stream}_read_handle",
                f"child_{stream}_write_handle",
                wrapper_reads=True,
                shared_child_role=f"child_stdio_{stream}_write_handle",
            )
        if validated_phase == "A":
            create_event(
                "wrapper_revocation_event_handle",
                "child_revocation_event_handle",
                initially_signaled=False,
            )
            create_event(
                "wrapper_send_idle_event_handle",
                "child_send_idle_event_handle",
                initially_signaled=True,
            )
            create_event(
                "wrapper_counter_ack_event_handle",
                "child_counter_ack_event_handle",
                initially_signaled=False,
            )
        channels = PhaseChannels._from_factory(
            _PHASE_CHANNELS_FACTORY_TOKEN,
            phase=validated_phase,
            handles=handles,
        )
        handles.clear()
        return channels
    except BaseException as error:
        cleanup_ok = _close_provisional_phase_handles(handles)
        if not cleanup_ok:
            cleanup_ok = _close_provisional_phase_handles(handles)
        if not cleanup_ok or (
            isinstance(error, DualLiveWindowsError)
            and error.code == "dual_live_phase_channels_cleanup_failed"
        ):
            if not cleanup_ok:
                _retain_failed_phase_handle_custody(
                    handles,
                    mode="build",
                )
            _fail("dual_live_phase_channels_cleanup_failed")
        raise


def create_phase_channels(phase: str) -> PhaseChannels:
    _require_phase_channel_apis()
    with _native_custody_gate:
        _drain_native_custody()
        return _create_phase_channels_locked(phase)


def make_inherited_handles_non_inheritable(
    inherited_handles: Sequence[int],
) -> None:
    _require_phase_channel_apis()
    if isinstance(inherited_handles, (str, bytes)) or not isinstance(
        inherited_handles,
        Sequence,
    ):
        _fail("dual_live_windows_arguments_invalid")
    handles = tuple(inherited_handles)
    if not handles or any(
        isinstance(handle, bool) or not isinstance(handle, int) or handle <= 0
        for handle in handles
    ) or len(set(handles)) != len(handles):
        _fail("dual_live_job_inherited_handles_invalid")
    assert _kernel32 is not None
    bootstrap_failed = False
    for handle in handles:
        flags = wintypes.DWORD()
        if not _kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
            bootstrap_failed = True
        elif flags.value not in (0, _HANDLE_FLAG_INHERIT):
            bootstrap_failed = True
        try:
            _validate_inherited_capability(handle)
        except DualLiveWindowsError:
            bootstrap_failed = True
    for handle in handles:
        if not _kernel32.SetHandleInformation(handle, _HANDLE_FLAG_INHERIT, 0):
            bootstrap_failed = True
    for handle in handles:
        flags = wintypes.DWORD()
        if not _kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
            bootstrap_failed = True
        elif flags.value != 0:
            bootstrap_failed = True
    if bootstrap_failed:
        _fail("dual_live_job_inherited_handles_invalid")


def _environment_block(environment: Mapping[str, str]) -> ctypes.Array[Any]:
    if not isinstance(environment, Mapping):
        _fail("dual_live_windows_arguments_invalid")
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, value in environment.items():
        if (
            not isinstance(name, str)
            or not name
            or "=" in name
            or "\0" in name
            or not isinstance(value, str)
            or "\0" in value
        ):
            _fail("dual_live_windows_arguments_invalid")
        folded = name.casefold()
        if folded in seen:
            _fail("dual_live_windows_arguments_invalid")
        seen.add(folded)
        entries.append((name, value))
    entries.sort(key=lambda item: (item[0].casefold(), item[0]))
    encoded = "\0".join(f"{name}={value}" for name, value in entries) + "\0\0"
    buffer_type = ctypes.c_wchar * len(encoded)
    buffer = buffer_type()
    buffer[:] = encoded
    return buffer


def _validated_executable_path_text(value: object) -> Path:
    if not isinstance(value, str) or not value or "\0" in value:
        _fail("dual_live_executable_invalid")
    windows_path = value.replace("/", "\\")
    folded = windows_path.casefold()
    if windows_path.startswith("\\\\") or folded.startswith(
        ("\\??\\", "\\device\\", "\\global??\\")
    ):
        _fail("dual_live_executable_invalid")
    drive, tail = os.path.splitdrive(windows_path)
    if (
        len(drive) != 2
        or drive[1] != ":"
        or not tail.startswith("\\")
        or ":" in tail
        or os.path.normpath(windows_path) != windows_path
    ):
        _fail("dual_live_executable_invalid")
    return Path(windows_path)


def _hash_file_handle(handle: int) -> str:
    assert _kernel32 is not None
    file_size = ctypes.c_longlong()
    if not _kernel32.GetFileSizeEx(handle, ctypes.byref(file_size)):
        _fail("dual_live_executable_invalid")
    if file_size.value <= 0:
        _fail("dual_live_executable_invalid")
    if not _kernel32.SetFilePointerEx(handle, 0, None, _FILE_BEGIN):
        _fail("dual_live_executable_invalid")
    digest = hashlib.sha256()
    buffer = ctypes.create_string_buffer(1024 * 1024)
    remaining = int(file_size.value)
    while remaining:
        requested = min(remaining, len(buffer))
        received = wintypes.DWORD()
        if not _kernel32.ReadFile(
            handle,
            buffer,
            requested,
            ctypes.byref(received),
            None,
        ):
            _fail("dual_live_executable_invalid")
        if not 0 < received.value <= requested:
            _fail("dual_live_executable_invalid")
        digest.update(buffer.raw[: received.value])
        remaining -= int(received.value)
    extra = wintypes.DWORD()
    if not _kernel32.ReadFile(handle, buffer, 1, ctypes.byref(extra), None):
        _fail("dual_live_executable_invalid")
    if extra.value != 0:
        _fail("dual_live_executable_invalid")
    if not _kernel32.SetFilePointerEx(handle, 0, None, _FILE_BEGIN):
        _fail("dual_live_executable_invalid")
    return digest.hexdigest()


def _git_blob_oid_from_handle(handle: int, object_format: str) -> str:
    assert _kernel32 is not None
    if object_format == "sha1":
        digest = hashlib.sha1(usedforsecurity=False)
    elif object_format == "sha256":
        digest = hashlib.sha256()
    else:
        _fail("dual_live_source_identity_invalid")
    file_size = ctypes.c_longlong()
    if (
        not _kernel32.GetFileSizeEx(handle, ctypes.byref(file_size))
        or file_size.value <= 0
        or not _kernel32.SetFilePointerEx(handle, 0, None, _FILE_BEGIN)
    ):
        _fail("dual_live_source_identity_invalid")
    digest.update(f"blob {file_size.value}\0".encode("ascii"))
    buffer = ctypes.create_string_buffer(1024 * 1024)
    remaining = int(file_size.value)
    while remaining:
        requested = min(remaining, len(buffer))
        received = wintypes.DWORD()
        if not _kernel32.ReadFile(
            handle,
            buffer,
            requested,
            ctypes.byref(received),
            None,
        ) or not 0 < received.value <= requested:
            _fail("dual_live_source_identity_invalid")
        digest.update(buffer.raw[: received.value])
        remaining -= int(received.value)
    extra = wintypes.DWORD()
    if (
        not _kernel32.ReadFile(handle, buffer, 1, ctypes.byref(extra), None)
        or extra.value != 0
        or not _kernel32.SetFilePointerEx(handle, 0, None, _FILE_BEGIN)
    ):
        _fail("dual_live_source_identity_invalid")
    return digest.hexdigest()


class _ExecutableCustody:
    __slots__ = (
        "handle",
        "final_path",
        "file_identity_sha256",
        "sha256",
    )

    def __init__(
        self,
        *,
        handle: int,
        final_path: str,
        file_identity_sha256: str,
        sha256: str,
    ) -> None:
        self.handle = handle
        self.final_path = final_path
        self.file_identity_sha256 = file_identity_sha256
        self.sha256 = sha256


@dataclass(frozen=True, slots=True)
class _ReviewedGitTree:
    code_revision: str
    wrapper_image_sha256: str


class _ReviewedSourceCustody:
    __slots__ = (
        "_closed",
        "_git_path",
        "_interpreter",
        "_repo_root",
        "_wrapper",
        "code_revision",
        "interpreter_image_sha256",
        "wrapper_image_sha256",
    )

    def __init__(
        self,
        *,
        repo_root: Path,
        git_path: Path,
        wrapper: _ExecutableCustody,
        interpreter: _ExecutableCustody,
        state: _ReviewedGitTree,
    ) -> None:
        self._repo_root = repo_root
        self._git_path = git_path
        self._wrapper = wrapper
        self._interpreter = interpreter
        self.code_revision = state.code_revision
        self.wrapper_image_sha256 = state.wrapper_image_sha256
        self.interpreter_image_sha256 = interpreter.sha256
        self._closed = False

    def assert_stable(self) -> None:
        if self._closed:
            _fail("dual_live_source_identity_invalid")
        state = _verify_reviewed_git_tree(
            self._repo_root,
            self._git_path,
            self._wrapper,
        )
        if (
            state.code_revision != self.code_revision
            or state.wrapper_image_sha256 != self.wrapper_image_sha256
            or _hash_file_handle(self._wrapper.handle)
            != self.wrapper_image_sha256
            or _hash_file_handle(self._interpreter.handle)
            != self.interpreter_image_sha256
        ):
            _fail("dual_live_source_identity_invalid")

    def close(self) -> None:
        if self._closed:
            return
        first_error: BaseException | None = None
        for custody in (self._wrapper, self._interpreter):
            try:
                _close_handle(custody.handle)
            except BaseException as exc:
                if first_error is None:
                    first_error = exc
        self._closed = True
        if first_error is not None:
            raise first_error


def _reviewed_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _trusted_git_path() -> Path:
    return Path(r"C:\Program Files\Git\cmd\git.exe")


def _reviewed_git_environment() -> dict[str, str]:
    environment = {
        name: value
        for name in ("SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP")
        if (value := os.environ.get(name))
    }
    environment.update(
        {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "NUL",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": "NUL",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
    )
    return environment


def _require_reviewed_controller_python_posture() -> None:
    if (
        sys.flags.isolated != 1
        or sys.dont_write_bytecode is not True
        or sys.pycache_prefix != "NUL"
    ):
        _fail("dual_live_source_identity_invalid")


def _runtime_ignored_path_allowed(raw_path: bytes) -> bool:
    try:
        path = raw_path.decode("ascii")
    except UnicodeDecodeError:
        return False
    parts = path.split("/")
    return (
        len(parts) >= 3
        and (path.startswith("backend/app/") or path.startswith("tools/"))
        and parts[-2] == "__pycache__"
        and parts[-1].endswith(".pyc")
        and parts[-1] != ".pyc"
    )


def _run_reviewed_git(
    git_custody: _ExecutableCustody,
    repo_root: Path,
    *arguments: str,
    allowed_codes: frozenset[int] = frozenset((0,)),
) -> tuple[int, bytes]:
    process = _REVIEWED_GIT_POPEN(
        (
            git_custody.final_path,
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            "diff.external=",
            "-c",
            "submodule.recurse=false",
            *arguments,
        ),
        cwd=str(repo_root),
        env=_reviewed_git_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    streams = (process.stdout, process.stderr)
    if any(stream is None for stream in streams):
        process.kill()
        process.wait()
        _fail("dual_live_source_identity_invalid")
    limits = (4 * 1024 * 1024, 256 * 1024)
    outputs: list[bytes | None] = [None, None]
    read_errors: list[BaseException] = []
    overflow = threading.Event()

    def read_bounded(index: int) -> None:
        stream = streams[index]
        assert stream is not None
        try:
            content = stream.read(limits[index] + 1)
            outputs[index] = bytes(content)
            if len(content) > limits[index]:
                overflow.set()
        except BaseException as exc:
            read_errors.append(exc)
            overflow.set()

    readers = tuple(
        threading.Thread(
            target=read_bounded,
            args=(index,),
            name=f"dual-live-git-{index}",
        )
        for index in range(2)
    )
    for reader in readers:
        reader.start()
    deadline = time.monotonic() + 15
    while process.poll() is None and not overflow.wait(0.05):
        if time.monotonic() >= deadline:
            overflow.set()
            break
    if overflow.is_set() and process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    for reader in readers:
        reader.join(timeout=5)
    if any(reader.is_alive() for reader in readers):
        for stream in streams:
            assert stream is not None
            stream.close()
        for reader in readers:
            reader.join(timeout=1)
    else:
        for stream in streams:
            assert stream is not None
            stream.close()
    stdout, stderr = outputs
    if (
        any(reader.is_alive() for reader in readers)
        or read_errors
        or stdout is None
        or stderr is None
        or overflow.is_set()
        or process.returncode not in allowed_codes
        or stderr
    ):
        _fail("dual_live_source_identity_invalid")
    return int(process.returncode), stdout


def _verify_reviewed_git_tree(
    repo_root: Path,
    git_path: Path,
    wrapper_custody: _ExecutableCustody,
) -> _ReviewedGitTree:
    if (
        not isinstance(repo_root, Path)
        or not isinstance(git_path, Path)
        or type(wrapper_custody) is not _ExecutableCustody
    ):
        _fail("dual_live_source_identity_invalid")
    expected_root = str(repo_root.resolve()).replace("\\", "/").casefold()
    expected_wrapper = str(
        (repo_root / "tools" / "dual_live_run.py").resolve()
    ).replace("\\", "/").casefold()
    if wrapper_custody.final_path.replace("\\", "/").casefold() != expected_wrapper:
        _fail("dual_live_source_identity_invalid")

    git_custody = _open_executable_custody(str(git_path))
    try:
        _, top_bytes = _run_reviewed_git(
            git_custody,
            repo_root,
            "rev-parse",
            "--path-format=absolute",
            "--show-toplevel",
        )
        try:
            top = top_bytes.decode("utf-8").strip().replace("\\", "/").casefold()
        except UnicodeDecodeError:
            _fail("dual_live_source_identity_invalid")
        if top != expected_root:
            _fail("dual_live_source_identity_invalid")

        worktree_config_code, worktree_config = _run_reviewed_git(
            git_custody,
            repo_root,
            "config",
            "--local",
            "--null",
            "--get-all",
            "extensions.worktreeConfig",
            allowed_codes=frozenset((0, 1)),
        )
        if worktree_config_code != 1 or worktree_config:
            _fail("dual_live_source_identity_invalid")

        config_code, dangerous_config = _run_reviewed_git(
            git_custody,
            repo_root,
            "config",
            "--local",
            "--null",
            "--get-regexp",
            (
                r"^(alias\.|core\.(attributesfile|excludesfile|fsmonitor|"
                r"sshcommand)|diff\.|filter\.|include\.|protocol\.|"
                r"submodule\..*\.update|url\.)"
            ),
            allowed_codes=frozenset((0, 1)),
        )
        if config_code != 1 or dangerous_config:
            _fail("dual_live_source_identity_invalid")

        _, revision_bytes = _run_reviewed_git(
            git_custody,
            repo_root,
            "rev-parse",
            "--verify",
            "HEAD^{commit}",
        )
        _, format_bytes = _run_reviewed_git(
            git_custody,
            repo_root,
            "rev-parse",
            "--show-object-format",
        )
        revision = revision_bytes.decode("ascii").strip()
        object_format = format_bytes.decode("ascii").strip()
        if (
            object_format not in {"sha1", "sha256"}
            or len(revision) != (40 if object_format == "sha1" else 64)
            or any(character not in "0123456789abcdef" for character in revision)
        ):
            _fail("dual_live_source_identity_invalid")

        _, tracked_flags = _run_reviewed_git(
            git_custody,
            repo_root,
            "ls-files",
            "-v",
        )
        if any(
            len(line) < 3
            or line[1:2] != b" "
            or line[:1] == b"S"
            or line[:1].islower()
            for line in tracked_flags.splitlines()
        ):
            _fail("dual_live_source_identity_invalid")

        diff_code, _ = _run_reviewed_git(
            git_custody,
            repo_root,
            "diff",
            "--quiet",
            "--no-ext-diff",
            "--ignore-submodules=none",
            "HEAD",
            "--",
            allowed_codes=frozenset((0, 1)),
        )
        if diff_code != 0:
            _fail("dual_live_source_identity_invalid")
        _, untracked = _run_reviewed_git(
            git_custody,
            repo_root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "backend/app",
            "tools",
        )
        if untracked:
            _fail("dual_live_source_identity_invalid")
        _, ignored = _run_reviewed_git(
            git_custody,
            repo_root,
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "-z",
            "--",
            "backend/app",
            "tools",
        )
        ignored_paths = tuple(path for path in ignored.split(b"\0") if path)
        if any(
            not _runtime_ignored_path_allowed(path)
            for path in ignored_paths
        ):
            _fail("dual_live_source_identity_invalid")

        _, tree_entry = _run_reviewed_git(
            git_custody,
            repo_root,
            "ls-tree",
            "-z",
            "HEAD",
            "--",
            "tools/dual_live_run.py",
        )
        prefix = b"100644 blob "
        suffix = b"\ttools/dual_live_run.py\0"
        if not tree_entry.startswith(prefix) or not tree_entry.endswith(suffix):
            _fail("dual_live_source_identity_invalid")
        expected_oid = tree_entry[len(prefix) : -len(suffix)]
        actual_oid = _git_blob_oid_from_handle(
            wrapper_custody.handle,
            object_format,
        ).encode("ascii")
        if actual_oid != expected_oid:
            _fail("dual_live_source_identity_invalid")
        return _ReviewedGitTree(
            code_revision=revision,
            wrapper_image_sha256=wrapper_custody.sha256,
        )
    except (UnicodeDecodeError, ValueError):
        _fail("dual_live_source_identity_invalid")
    finally:
        _close_handle(git_custody.handle)


def _open_executable_custody(path_text: object) -> _ExecutableCustody:
    assert _kernel32 is not None
    path = _validated_executable_path_text(path_text)
    handle = _kernel32.CreateFileW(
        str(path),
        _GENERIC_READ | _FILE_READ_ATTRIBUTES,
        _FILE_SHARE_READ,
        None,
        _OPEN_EXISTING,
        _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle in (None, ctypes.c_void_p(-1).value):
        _fail("dual_live_executable_invalid")
    owned_handle = int(handle)
    try:
        attributes = _FILE_ATTRIBUTE_TAG_INFO()
        if not _kernel32.GetFileInformationByHandleEx(
            owned_handle,
            _FILE_ATTRIBUTE_TAG_INFO_CLASS,
            ctypes.byref(attributes),
            ctypes.sizeof(attributes),
        ):
            _fail("dual_live_executable_invalid")
        if attributes.FileAttributes & (
            _FILE_ATTRIBUTE_DIRECTORY | _FILE_ATTRIBUTE_REPARSE_POINT
        ):
            _fail("dual_live_executable_invalid")
        if _kernel32.GetFileType(owned_handle) != _FILE_TYPE_DISK:
            _fail("dual_live_executable_invalid")
        file_id = _FILE_ID_INFO()
        if not _kernel32.GetFileInformationByHandleEx(
            owned_handle,
            _FILE_ID_INFO_CLASS,
            ctypes.byref(file_id),
            ctypes.sizeof(file_id),
        ):
            _fail("dual_live_executable_invalid")
        file_id_hex = bytes(file_id.FileId.Identifier).hex()
        if not file_id_hex or set(file_id_hex) == {"0"}:
            _fail("dual_live_executable_invalid")
        required = _kernel32.GetFinalPathNameByHandleW(owned_handle, None, 0, 0)
        if required == 0:
            _fail("dual_live_executable_invalid")
        final_buffer = ctypes.create_unicode_buffer(required + 1)
        written = _kernel32.GetFinalPathNameByHandleW(
            owned_handle,
            final_buffer,
            len(final_buffer),
            0,
        )
        if written == 0 or written >= len(final_buffer):
            _fail("dual_live_executable_invalid")
        handle_path = final_buffer.value
        if not handle_path.startswith("\\\\?\\") or handle_path.casefold().startswith(
            "\\\\?\\unc\\"
        ):
            _fail("dual_live_executable_invalid")
        final_path = str(_validated_executable_path_text(handle_path[4:]))
        if _kernel32.GetDriveTypeW(final_path[:3]) != _DRIVE_FIXED:
            _fail("dual_live_executable_invalid")
        sha256 = _hash_file_handle(owned_handle)
        file_identity_sha256 = hashlib.sha256(
            _canonical_json_bytes(
                {
                    "file_attributes": int(attributes.FileAttributes),
                    "file_id": file_id_hex,
                    "final_path": final_path.replace("\\", "/").casefold(),
                    "volume_serial_number": int(file_id.VolumeSerialNumber),
                }
            )
        ).hexdigest()
        return _ExecutableCustody(
            handle=owned_handle,
            final_path=final_path,
            file_identity_sha256=file_identity_sha256,
            sha256=sha256,
        )
    except BaseException:
        _close_handle(owned_handle)
        raise


def _acquire_reviewed_source_custody() -> _ReviewedSourceCustody:
    _require_windows()
    _require_reviewed_controller_python_posture()
    _drain_native_custody()
    repo_root = _reviewed_repo_root()
    git_path = _trusted_git_path()
    wrapper: _ExecutableCustody | None = None
    interpreter: _ExecutableCustody | None = None
    try:
        wrapper = _open_executable_custody(
            str(repo_root / "tools" / "dual_live_run.py")
        )
        interpreter = _open_executable_custody(
            str(_current_process_image_path())
        )
        state = _verify_reviewed_git_tree(
            repo_root,
            git_path,
            wrapper,
        )
        custody = _ReviewedSourceCustody(
            repo_root=repo_root,
            git_path=git_path,
            wrapper=wrapper,
            interpreter=interpreter,
            state=state,
        )
        custody.assert_stable()
        return custody
    except BaseException as exc:
        cleanup_error: BaseException | None = None
        for candidate in (wrapper, interpreter):
            if candidate is None:
                continue
            try:
                _close_handle(candidate.handle)
            except BaseException as close_exc:
                if cleanup_error is None:
                    cleanup_error = close_exc
        if cleanup_error is not None:
            failure = DualLiveWindowsError(
                "dual_live_source_identity_cleanup_failed"
            )
            failure.__cause__ = cleanup_error
            failure.__context__ = exc
            raise failure
        raise


def _validated_job_inputs(
    *,
    argv: Sequence[str],
    environment: Mapping[str, str],
    inherited_handles: Sequence[int],
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
) -> tuple[tuple[str, ...], ctypes.Array[Any], tuple[int, ...], str, str]:
    _require_job_apis()
    if isinstance(argv, (str, bytes)) or not isinstance(argv, Sequence) or not argv:
        _fail("dual_live_windows_arguments_invalid")
    copied_argv = tuple(argv)
    if any(not isinstance(value, str) or "\0" in value for value in copied_argv):
        _fail("dual_live_windows_arguments_invalid")
    _validated_executable_path_text(copied_argv[0])
    block = _environment_block(environment)
    if isinstance(inherited_handles, (str, bytes)) or not isinstance(
        inherited_handles, Sequence
    ):
        _fail("dual_live_windows_arguments_invalid")
    handles = tuple(inherited_handles)
    if not handles or any(
        isinstance(handle, bool) or not isinstance(handle, int) or handle <= 0
        for handle in handles
    ):
        _fail("dual_live_job_inherited_handles_invalid")
    if len(set(handles)) != len(handles):
        _fail("dual_live_job_inherited_handles_invalid")
    assert _kernel32 is not None
    for handle in handles:
        flags = wintypes.DWORD()
        if not _kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
            _fail("dual_live_job_inherited_handles_invalid")
        if not flags.value & _HANDLE_FLAG_INHERIT:
            _fail("dual_live_job_inherited_handles_invalid")
        _validate_inherited_capability(handle)
    return (
        copied_argv,
        block,
        handles,
        _require_uuid4(runtime_instance_id),
        _require_sha256(wrapper_nonce_sha256),
    )


def _validated_standard_handles(
    standard_handles: Sequence[int] | None,
    inherited_handles: tuple[int, ...],
) -> tuple[int, int, int] | None:
    if standard_handles is None:
        return None
    if isinstance(standard_handles, (str, bytes)) or not isinstance(
        standard_handles,
        Sequence,
    ):
        _fail("dual_live_windows_arguments_invalid")
    handles = tuple(standard_handles)
    if (
        len(handles) != 3
        or any(
            isinstance(handle, bool) or not isinstance(handle, int) or handle <= 0
            for handle in handles
        )
        or len(set(handles)) != 3
        or not set(handles) <= set(inherited_handles)
    ):
        _fail("dual_live_job_standard_handles_invalid")
    return handles


def _hash_open_image(path: Path) -> tuple[BinaryIO, str]:
    try:
        stream = path.open("rb")
    except OSError:
        _fail("dual_live_windows_arguments_invalid")
    digest = hashlib.sha256()
    try:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    except OSError:
        stream.close()
        _fail("dual_live_windows_arguments_invalid")
    stream.seek(0)
    return stream, digest.hexdigest()


def _configure_job(job_handle: int) -> str:
    assert _kernel32 is not None
    policy = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    policy.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not _kernel32.SetInformationJobObject(
        job_handle,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(policy),
        ctypes.sizeof(policy),
    ):
        _fail("dual_live_job_policy_invalid")
    readback = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    returned = wintypes.DWORD()
    if not _kernel32.QueryInformationJobObject(
        job_handle,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(readback),
        ctypes.sizeof(readback),
        ctypes.byref(returned),
    ):
        _fail("dual_live_job_policy_invalid")
    flags = int(readback.BasicLimitInformation.LimitFlags)
    forbidden = _JOB_OBJECT_LIMIT_BREAKAWAY_OK | _JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK
    if not flags & _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE or flags & forbidden:
        _fail("dual_live_job_policy_invalid")
    return hashlib.sha256(
        _canonical_json_bytes({"limit_flags": flags})
    ).hexdigest()


def _attribute_list_size() -> int:
    assert _kernel32 is not None
    attribute_bytes = ctypes.c_size_t()
    ctypes.set_last_error(0)
    succeeded = _kernel32.InitializeProcThreadAttributeList(
        None,
        2,
        0,
        ctypes.byref(attribute_bytes),
    )
    if (
        succeeded
        or ctypes.get_last_error() != _ERROR_INSUFFICIENT_BUFFER
        or attribute_bytes.value == 0
    ):
        _fail("dual_live_job_unsupported")
    return int(attribute_bytes.value)


def _filetime_value(value: _FILETIME) -> int:
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _process_creation_identity_sha256(pid: int, creation_filetime: int) -> str:
    if (
        isinstance(pid, bool)
        or not isinstance(pid, int)
        or pid <= 0
        or isinstance(creation_filetime, bool)
        or not isinstance(creation_filetime, int)
        or creation_filetime <= 0
    ):
        _fail("dual_live_process_identity_indeterminate")
    return hashlib.sha256(
        _canonical_json_bytes(
            {"creation_filetime": creation_filetime, "pid": pid}
        )
    ).hexdigest()


def _derive_process_boot_identity(
    *,
    pid: int,
    creation_filetime: int,
    executable_sha256: str,
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
) -> tuple[str, str]:
    process_creation_identity_sha256 = _process_creation_identity_sha256(
        pid,
        creation_filetime,
    )
    executable_sha256 = _require_sha256(executable_sha256)
    runtime_instance_id = _require_uuid4(runtime_instance_id)
    wrapper_nonce_sha256 = _require_sha256(wrapper_nonce_sha256)
    process_boot_id = hashlib.sha256(
        _canonical_json_bytes(
            {
                "executable_sha256": executable_sha256,
                "pid": pid,
                "process_creation_identity_sha256": (
                    process_creation_identity_sha256
                ),
                "runtime_instance_id": runtime_instance_id,
                "wrapper_nonce_sha256": wrapper_nonce_sha256,
            }
        )
    ).hexdigest()
    return process_creation_identity_sha256, process_boot_id


@dataclass(frozen=True, slots=True)
class JobStartEvidence:
    pid: int
    process_creation_identity_sha256: str
    process_boot_id: str
    executable_sha256: str
    job_policy_sha256: str

    def __post_init__(self) -> None:
        if isinstance(self.pid, bool) or not isinstance(self.pid, int) or self.pid <= 0:
            _fail("dual_live_windows_arguments_invalid")
        for value in (
            self.process_creation_identity_sha256,
            self.process_boot_id,
            self.executable_sha256,
            self.job_policy_sha256,
        ):
            _require_sha256(value)


class JobChild:
    __slots__ = (
        "pid",
        "process_creation_identity_sha256",
        "process_boot_id",
        "_process_handle",
        "_job_handle",
        "_creation_filetime",
        "_executable_sha256",
        "_job_policy_sha256",
        "_start_evidence",
        "_retained_processes",
        "_pretermination_retention_failure",
        "_closed",
        "_lock",
    )

    def __init__(
        self,
        pid: int,
        process_creation_identity_sha256: str,
        process_boot_id: str,
    ) -> None:
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            _fail("dual_live_windows_arguments_invalid")
        self.pid = pid
        self.process_creation_identity_sha256 = _require_sha256(
            process_creation_identity_sha256
        )
        self.process_boot_id = _require_sha256(process_boot_id)
        self._process_handle: int | None = None
        self._job_handle: int | None = None
        self._creation_filetime: int | None = None
        self._executable_sha256: str | None = None
        self._job_policy_sha256: str | None = None
        self._start_evidence: JobStartEvidence | None = None
        self._retained_processes: dict[int, tuple[int, int, str, str]] = {}
        self._pretermination_retention_failure: BaseException | None = None
        self._closed = False
        self._lock = threading.Lock()

    @classmethod
    def _from_owned_handles(
        cls,
        *,
        pid: int,
        process_creation_identity_sha256: str,
        process_boot_id: str,
        process_handle: int,
        job_handle: int,
        creation_filetime: int,
        executable_sha256: str,
        job_policy_sha256: str,
    ) -> JobChild:
        instance = cls(pid, process_creation_identity_sha256, process_boot_id)
        instance._process_handle = process_handle
        instance._job_handle = job_handle
        instance._creation_filetime = creation_filetime
        instance._executable_sha256 = executable_sha256
        instance._job_policy_sha256 = job_policy_sha256
        instance._start_evidence = JobStartEvidence(
            pid=pid,
            process_creation_identity_sha256=process_creation_identity_sha256,
            process_boot_id=process_boot_id,
            executable_sha256=executable_sha256,
            job_policy_sha256=job_policy_sha256,
        )
        instance._retained_processes[pid] = (
            process_handle,
            creation_filetime,
            executable_sha256,
            process_creation_identity_sha256,
        )
        return instance

    @property
    def start_evidence(self) -> JobStartEvidence:
        if self._start_evidence is None:
            _fail("dual_live_child_start_evidence_unavailable")
        return self._start_evidence

    def __enter__(self) -> JobChild:
        if self._closed:
            _fail("dual_live_child_closed")
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _wait_for_exit(self, timeout_seconds: float) -> int | None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds < 0
        ):
            _fail("dual_live_windows_arguments_invalid")
        milliseconds = math.ceil(timeout_seconds * 1000)
        if milliseconds >= _WAIT_FAILED:
            _fail("dual_live_windows_arguments_invalid")
        if self._closed or self._process_handle is None:
            _fail("dual_live_child_closed")
        assert _kernel32 is not None
        result = _kernel32.WaitForSingleObject(self._process_handle, milliseconds)
        if result == _WAIT_TIMEOUT:
            return None
        if result != _WAIT_OBJECT_0:
            _fail("dual_live_child_wait_failed")
        exit_code = wintypes.DWORD()
        if not _kernel32.GetExitCodeProcess(
            self._process_handle, ctypes.byref(exit_code)
        ):
            _fail("dual_live_child_wait_failed")
        return int(exit_code.value)

    def poll_exit(self, timeout_seconds: float) -> int | None:
        return self._wait_for_exit(timeout_seconds)

    def wait(self, timeout_seconds: float) -> int:
        exit_code = self._wait_for_exit(timeout_seconds)
        if exit_code is None:
            _fail("dual_live_child_timeout")
        return exit_code

    def _terminate_tree_unlocked(self) -> None:
        if self._closed or self._job_handle is None:
            _fail("dual_live_child_closed")
        assert _kernel32 is not None
        if not _kernel32.TerminateJobObject(self._job_handle, _TERMINATE_EXIT_CODE):
            _fail("dual_live_child_terminate_failed")

    def terminate_tree(self) -> None:
        with self._lock:
            self._terminate_tree_unlocked()

    def retain_then_terminate_tree(self) -> None:
        """Retain a stable pre-kill process set, then always terminate the Job."""

        with self._lock:
            if self._closed or self._job_handle is None:
                _fail("dual_live_child_closed")
            retention_failure: BaseException | None = None
            try:
                process_ids = _stable_job_process_ids(self._job_handle)
                _retain_active_job_processes(self, process_ids)
                _validate_retained_processes(self)
                if _stable_job_process_ids(self._job_handle) != process_ids:
                    _fail("dual_live_quiescence_indeterminate")
            except BaseException as exc:
                retention_failure = exc
                if self._pretermination_retention_failure is None:
                    self._pretermination_retention_failure = exc

            try:
                self._terminate_tree_unlocked()
            except BaseException as termination_failure:
                if retention_failure is not None:
                    termination_failure.__context__ = retention_failure
                raise

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            assert _kernel32 is not None or (
                self._job_handle is None and self._process_handle is None
            )
            cleanup_failed = False
            if self._job_handle is not None:
                if _kernel32 is not None and _kernel32.CloseHandle(
                    self._job_handle
                ):
                    self._job_handle = None
                else:
                    cleanup_failed = True
            for pid, retained in tuple(self._retained_processes.items()):
                if pid != self.pid:
                    if _kernel32 is not None and _kernel32.CloseHandle(
                        retained[0]
                    ):
                        del self._retained_processes[pid]
                    else:
                        cleanup_failed = True
            if self._process_handle is not None:
                if _kernel32 is not None and _kernel32.CloseHandle(
                    self._process_handle
                ):
                    self._process_handle = None
                    self._retained_processes.pop(self.pid, None)
                else:
                    cleanup_failed = True
            if cleanup_failed:
                _fail("dual_live_child_cleanup_failed")
            self._retained_processes.clear()
            self._closed = True


class _ProvisionalJobOwner:
    __slots__ = ("job_handle", "process_info")

    def __init__(
        self,
        *,
        job_handle: int,
        process_info: _PROCESS_INFORMATION,
    ) -> None:
        self.job_handle: int | None = job_handle
        self.process_info = process_info

    @property
    def process_handle(self) -> int | None:
        value = self.process_info.hProcess
        return int(value) if value else None

    @process_handle.setter
    def process_handle(self, value: int | None) -> None:
        self.process_info.hProcess = value

    @property
    def thread_handle(self) -> int | None:
        value = self.process_info.hThread
        return int(value) if value else None

    @thread_handle.setter
    def thread_handle(self, value: int | None) -> None:
        self.process_info.hThread = value

    def close_thread_checked(self) -> None:
        if self.thread_handle is None:
            return
        assert _kernel32 is not None
        if not _kernel32.CloseHandle(self.thread_handle):
            _fail("dual_live_child_cleanup_failed")
        self.thread_handle = None

    def _close_owned_handle(self, name: str) -> bool:
        handle = getattr(self, name)
        if handle is None:
            return True
        assert _kernel32 is not None
        if not _kernel32.CloseHandle(handle):
            return False
        setattr(self, name, None)
        return True

    def cleanup_after_failure(self) -> bool:
        assert _kernel32 is not None
        cleanup_ok = True
        if (
            self.job_handle is not None
            and self.process_handle is not None
            and not _kernel32.TerminateJobObject(
                self.job_handle,
                _TERMINATE_EXIT_CODE,
            )
        ):
            cleanup_ok = False
            if not self._close_owned_handle("job_handle"):
                cleanup_ok = False
        if self.process_handle is not None:
            wait_result = _kernel32.WaitForSingleObject(
                self.process_handle,
                _POST_CREATE_CLEANUP_WAIT_MS,
            )
            if wait_result != _WAIT_OBJECT_0:
                cleanup_ok = False
        for name in ("thread_handle", "process_handle", "job_handle"):
            if not self._close_owned_handle(name):
                cleanup_ok = False
        # No caller can receive a failed provisional owner. Retry once to avoid
        # orphaning a handle while retaining the failed cleanup verdict.
        for name in ("thread_handle", "process_handle", "job_handle"):
            self._close_owned_handle(name)
        return cleanup_ok and all(
            getattr(self, name) is None
            for name in ("thread_handle", "process_handle", "job_handle")
        )

    @property
    def released(self) -> bool:
        return all(
            getattr(self, name) is None
            for name in ("thread_handle", "process_handle", "job_handle")
        )

    def disown(self) -> None:
        if self.thread_handle is not None:
            _fail("dual_live_child_cleanup_failed")
        self.process_handle = None
        self.job_handle = None


_failed_provisional_owner_lock = threading.Lock()
_failed_provisional_owners: list[_ProvisionalJobOwner] = []


def _retain_failed_provisional_owner(owner: _ProvisionalJobOwner) -> None:
    if owner.released:
        return
    with _failed_provisional_owner_lock:
        if owner not in _failed_provisional_owners:
            _failed_provisional_owners.append(owner)


def _retry_failed_provisional_owners() -> None:
    failures: list[_ProvisionalJobOwner] = []
    with _native_custody_gate:
        with _failed_provisional_owner_lock:
            for owner in tuple(_failed_provisional_owners):
                if owner.cleanup_after_failure() and owner.released:
                    _failed_provisional_owners.remove(owner)
                else:
                    failures.append(owner)
    if failures:
        _fail("dual_live_child_cleanup_failed")


def _create_child_in_job_locked(
    argv: Sequence[str],
    environment: Mapping[str, str],
    inherited_handles: Sequence[int],
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
    standard_handles: Sequence[int] | None = None,
) -> JobChild:
    (
        copied_argv,
        environment_buffer,
        handles,
        runtime_instance_id,
        wrapper_nonce_sha256,
    ) = _validated_job_inputs(
        argv=argv,
        environment=environment,
        inherited_handles=inherited_handles,
        runtime_instance_id=runtime_instance_id,
        wrapper_nonce_sha256=wrapper_nonce_sha256,
    )
    std_handles = _validated_standard_handles(standard_handles, handles)
    executable_custody = _open_executable_custody(copied_argv[0])
    executable_sha256 = executable_custody.sha256
    job_handle: int | None = None
    provisional_owner: _ProvisionalJobOwner | None = None
    attribute_list: ctypes.Array[ctypes.c_char] | None = None
    attributes_initialized = False
    primary_failure: BaseException | None = None
    try:
        assert _kernel32 is not None
        job_handle = _kernel32.CreateJobObjectW(None, None)
        if not job_handle:
            _fail("dual_live_job_admission_refused")
        flags = wintypes.DWORD()
        if not _kernel32.GetHandleInformation(job_handle, ctypes.byref(flags)):
            _fail("dual_live_job_policy_invalid")
        if flags.value & _HANDLE_FLAG_INHERIT:
            _fail("dual_live_job_policy_invalid")
        job_policy_sha256 = _configure_job(job_handle)

        attribute_bytes = ctypes.c_size_t(_attribute_list_size())
        attribute_list = ctypes.create_string_buffer(attribute_bytes.value)
        if not _kernel32.InitializeProcThreadAttributeList(
            attribute_list, 2, 0, ctypes.byref(attribute_bytes)
        ):
            _fail("dual_live_job_unsupported")
        attributes_initialized = True
        job_values = (wintypes.HANDLE * 1)(job_handle)
        if not _kernel32.UpdateProcThreadAttribute(
            attribute_list,
            0,
            _PROC_THREAD_ATTRIBUTE_JOB_LIST,
            job_values,
            ctypes.sizeof(job_values),
            None,
            None,
        ):
            _fail("dual_live_job_unsupported")
        handle_values = (wintypes.HANDLE * max(1, len(handles)))(*handles)
        if not _kernel32.UpdateProcThreadAttribute(
            attribute_list,
            0,
            _PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
            handle_values,
            len(handles) * ctypes.sizeof(wintypes.HANDLE),
            None,
            None,
        ):
            _fail("dual_live_job_unsupported")

        startup = _STARTUPINFOEXW()
        startup.StartupInfo.cb = ctypes.sizeof(_STARTUPINFOEXW)
        startup.lpAttributeList = ctypes.cast(attribute_list, wintypes.LPVOID)
        if std_handles is not None:
            startup.StartupInfo.dwFlags |= _STARTF_USESTDHANDLES
            (
                startup.StartupInfo.hStdInput,
                startup.StartupInfo.hStdOutput,
                startup.StartupInfo.hStdError,
            ) = std_handles
        process_info = _PROCESS_INFORMATION()
        provisional_owner = _ProvisionalJobOwner(
            job_handle=int(job_handle),
            process_info=process_info,
        )
        job_handle = None
        command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline(copied_argv))
        if not _kernel32.CreateProcessW(
            executable_custody.final_path,
            command_line,
            None,
            None,
            True,
            _EXTENDED_STARTUPINFO_PRESENT | _CREATE_UNICODE_ENVIRONMENT,
            environment_buffer,
            None,
            ctypes.byref(startup),
            ctypes.byref(process_info),
        ):
            _fail("dual_live_job_admission_refused")
        provisional_owner.close_thread_checked()
        assert provisional_owner.process_handle is not None
        assert provisional_owner.job_handle is not None
        owned_process_handle = provisional_owner.process_handle
        owned_job_handle = provisional_owner.job_handle
        if _hash_file_handle(executable_custody.handle) != executable_sha256:
            _fail("dual_live_process_identity_indeterminate")
        membership = wintypes.BOOL()
        if not _kernel32.IsProcessInJob(
            owned_process_handle,
            owned_job_handle,
            ctypes.byref(membership),
        ) or not membership.value:
            _fail("dual_live_job_admission_refused")
        creation_filetime = _process_creation_filetime(
            owned_process_handle,
            refusal_code="dual_live_process_identity_indeterminate",
        )
        if (
            _process_image_sha256(
                owned_process_handle,
                refusal_code="dual_live_process_identity_indeterminate",
            )
            != executable_sha256
        ):
            _fail("dual_live_process_identity_indeterminate")
        pid = int(process_info.dwProcessId)
        process_creation_identity_sha256, process_boot_id = (
            _derive_process_boot_identity(
                pid=pid,
                creation_filetime=creation_filetime,
                executable_sha256=executable_sha256,
                runtime_instance_id=runtime_instance_id,
                wrapper_nonce_sha256=wrapper_nonce_sha256,
            )
        )
        if not _kernel32.CloseHandle(executable_custody.handle):
            _fail("dual_live_child_cleanup_failed")
        executable_custody.handle = 0
        child = JobChild._from_owned_handles(
            pid=pid,
            process_creation_identity_sha256=process_creation_identity_sha256,
            process_boot_id=process_boot_id,
            process_handle=owned_process_handle,
            job_handle=owned_job_handle,
            creation_filetime=creation_filetime,
            executable_sha256=executable_sha256,
            job_policy_sha256=job_policy_sha256,
        )
        provisional_owner.disown()
        return child
    except BaseException as error:
        primary_failure = error
        if provisional_owner is not None:
            cleanup_ok = provisional_owner.cleanup_after_failure()
            _retain_failed_provisional_owner(provisional_owner)
            if not cleanup_ok or (
                isinstance(error, DualLiveWindowsError)
                and error.code == "dual_live_child_cleanup_failed"
            ):
                cleanup = DualLiveWindowsError("dual_live_child_cleanup_failed")
                cleanup.__context__ = error
                primary_failure = cleanup
                raise cleanup
        raise
    finally:
        if attributes_initialized and attribute_list is not None:
            _kernel32.DeleteProcThreadAttributeList(attribute_list)
        raw_cleanup_failures: list[BaseException] = []
        for raw_handle in (job_handle, executable_custody.handle):
            try:
                _close_handle(raw_handle)
            except BaseException as exc:
                raw_cleanup_failures.append(exc)
        job_handle = None
        executable_custody.handle = 0
        if raw_cleanup_failures:
            cleanup = DualLiveWindowsError("dual_live_child_cleanup_failed")
            cleanup.__context__ = primary_failure
            raise cleanup from raw_cleanup_failures[0]


def create_child_in_job(
    argv: Sequence[str],
    environment: Mapping[str, str],
    inherited_handles: Sequence[int],
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
    standard_handles: Sequence[int] | None = None,
) -> JobChild:
    _require_windows()
    with _native_custody_gate:
        _drain_native_custody()
        return _create_child_in_job_locked(
            argv=argv,
            environment=environment,
            inherited_handles=inherited_handles,
            runtime_instance_id=runtime_instance_id,
            wrapper_nonce_sha256=wrapper_nonce_sha256,
            standard_handles=standard_handles,
        )


def _process_creation_filetime(
    process_handle: int,
    *,
    refusal_code: str = "dual_live_quiescence_indeterminate",
) -> int:
    assert _kernel32 is not None
    creation = _FILETIME()
    exit_time = _FILETIME()
    kernel_time = _FILETIME()
    user_time = _FILETIME()
    if not _kernel32.GetProcessTimes(
        process_handle,
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(kernel_time),
        ctypes.byref(user_time),
    ):
        _fail(refusal_code)
    return _filetime_value(creation)


def _current_process_image_path() -> Path:
    assert _kernel32 is not None
    process_handle = int(_kernel32.GetCurrentProcess())
    capacity = 260
    for _ in range(8):
        buffer = ctypes.create_unicode_buffer(capacity)
        size = wintypes.DWORD(capacity)
        ctypes.set_last_error(0)
        if _kernel32.QueryFullProcessImageNameW(
            process_handle,
            0,
            buffer,
            ctypes.byref(size),
        ):
            image_path = buffer.value
            if not image_path or not 0 < size.value < capacity:
                _fail("dual_live_source_identity_invalid")
            return _validated_executable_path_text(image_path)
        if ctypes.get_last_error() != _ERROR_INSUFFICIENT_BUFFER:
            _fail("dual_live_source_identity_invalid")
        capacity *= 2
    _fail("dual_live_source_identity_invalid")


def _process_image_sha256(
    process_handle: int,
    *,
    refusal_code: str = "dual_live_quiescence_indeterminate",
) -> str:
    assert _kernel32 is not None
    capacity = 260
    for _ in range(8):
        buffer = ctypes.create_unicode_buffer(capacity)
        size = wintypes.DWORD(capacity)
        ctypes.set_last_error(0)
        if _kernel32.QueryFullProcessImageNameW(
            process_handle,
            0,
            buffer,
            ctypes.byref(size),
        ):
            image_path = buffer.value
            if not image_path or not 0 < size.value < capacity:
                _fail(refusal_code)
            try:
                stream, digest = _hash_open_image(Path(image_path))
            except DualLiveWindowsError:
                _fail(refusal_code)
            try:
                return digest
            finally:
                stream.close()
        if ctypes.get_last_error() != _ERROR_INSUFFICIENT_BUFFER:
            _fail(refusal_code)
        capacity *= 2
    _fail(refusal_code)


def current_process_boot_id(
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
) -> str:
    _require_windows()
    assert _kernel32 is not None
    required = (
        "GetCurrentProcess",
        "GetProcessId",
        "GetProcessTimes",
        "QueryFullProcessImageNameW",
    )
    if any(not callable(getattr(_kernel32, name, None)) for name in required):
        _fail("dual_live_job_unsupported")
    runtime_instance_id = _require_uuid4(runtime_instance_id)
    wrapper_nonce_sha256 = _require_sha256(wrapper_nonce_sha256)
    process_handle = _kernel32.GetCurrentProcess()
    if not process_handle:
        _fail("dual_live_process_identity_indeterminate")
    pid = int(_kernel32.GetProcessId(process_handle))
    if pid <= 0:
        _fail("dual_live_process_identity_indeterminate")
    creation_filetime = _process_creation_filetime(
        process_handle,
        refusal_code="dual_live_process_identity_indeterminate",
    )
    executable_sha256 = _process_image_sha256(
        process_handle,
        refusal_code="dual_live_process_identity_indeterminate",
    )
    _, process_boot_id = _derive_process_boot_identity(
        pid=pid,
        creation_filetime=creation_filetime,
        executable_sha256=executable_sha256,
        runtime_instance_id=runtime_instance_id,
        wrapper_nonce_sha256=wrapper_nonce_sha256,
    )
    return process_boot_id


def _validate_retained_processes(child: JobChild) -> None:
    primary = child._retained_processes.get(child.pid)
    if (
        primary is None
        or primary[0] != child._process_handle
        or primary[1] != child._creation_filetime
        or primary[2] != child._executable_sha256
        or primary[3] != child.process_creation_identity_sha256
    ):
        _fail("dual_live_quiescence_indeterminate")
    for pid, retained in child._retained_processes.items():
        process_handle, creation_filetime, executable_sha256, identity = retained
        if int(_kernel32.GetProcessId(process_handle)) != pid:
            _fail("dual_live_quiescence_indeterminate")
        current_creation = _process_creation_filetime(process_handle)
        expected_identity = _process_creation_identity_sha256(
            pid,
            current_creation,
        )
        if (
            current_creation != creation_filetime
            or expected_identity != identity
            or _SHA256.fullmatch(executable_sha256) is None
        ):
            _fail("dual_live_quiescence_indeterminate")


def _validate_fresh_pid_occupancy(child: JobChild) -> None:
    assert _kernel32 is not None
    for pid, retained in child._retained_processes.items():
        ctypes.set_last_error(0)
        process_handle = _kernel32.OpenProcess(
            _PROCESS_QUERY_LIMITED_INFORMATION | _SYNCHRONIZE,
            False,
            pid,
        )
        if not process_handle:
            if ctypes.get_last_error() in (
                _ERROR_INVALID_PARAMETER,
                _ERROR_NOT_FOUND,
            ):
                continue
            _fail("dual_live_quiescence_indeterminate")
        owned_handle = int(process_handle)
        try:
            if int(_kernel32.GetProcessId(owned_handle)) != pid:
                _fail("dual_live_quiescence_indeterminate")
            if _process_creation_filetime(owned_handle) != retained[1]:
                _fail("dual_live_quiescence_indeterminate")
        finally:
            if not _kernel32.CloseHandle(owned_handle):
                _fail("dual_live_quiescence_indeterminate")


def _retain_active_job_processes(
    child: JobChild,
    process_ids: tuple[int, ...],
) -> None:
    assert _kernel32 is not None and child._job_handle is not None
    for pid in process_ids:
        if pid in child._retained_processes:
            continue
        process_handle = _kernel32.OpenProcess(
            _PROCESS_QUERY_LIMITED_INFORMATION | _SYNCHRONIZE,
            False,
            pid,
        )
        if not process_handle:
            _fail("dual_live_quiescence_indeterminate")
        owned_handle = int(process_handle)
        try:
            if int(_kernel32.GetProcessId(owned_handle)) != pid:
                _fail("dual_live_quiescence_indeterminate")
            membership = wintypes.BOOL()
            if not _kernel32.IsProcessInJob(
                owned_handle,
                child._job_handle,
                ctypes.byref(membership),
            ) or not membership.value:
                _fail("dual_live_quiescence_indeterminate")
            first_creation = _process_creation_filetime(owned_handle)
            executable_sha256 = _process_image_sha256(owned_handle)
            second_creation = _process_creation_filetime(owned_handle)
            if first_creation != second_creation:
                _fail("dual_live_quiescence_indeterminate")
            identity = _process_creation_identity_sha256(pid, first_creation)
            child._retained_processes[pid] = (
                owned_handle,
                first_creation,
                executable_sha256,
                identity,
            )
            owned_handle = 0
        finally:
            _close_handle(owned_handle)


def _query_job_process_ids_once(job_handle: int) -> tuple[int, ...]:
    assert _kernel32 is not None
    pointer_size = ctypes.sizeof(ctypes.c_size_t)
    capacity = 1
    for _ in range(10):
        buffer = ctypes.create_string_buffer(8 + capacity * pointer_size)
        returned = wintypes.DWORD()
        ctypes.set_last_error(0)
        succeeded = _kernel32.QueryInformationJobObject(
            job_handle,
            _JOB_OBJECT_BASIC_PROCESS_ID_LIST_CLASS,
            buffer,
            len(buffer),
            ctypes.byref(returned),
        )
        assigned = ctypes.c_uint32.from_buffer(buffer, 0).value
        listed = ctypes.c_uint32.from_buffer(buffer, 4).value
        if listed > capacity or listed > assigned:
            _fail("dual_live_quiescence_indeterminate")
        if succeeded and assigned == listed:
            expected_bytes = 8 + listed * pointer_size
            if not expected_bytes <= returned.value <= len(buffer):
                _fail("dual_live_quiescence_indeterminate")
            pids = tuple(
                int(ctypes.c_size_t.from_buffer(buffer, 8 + index * pointer_size).value)
                for index in range(listed)
            )
            if any(pid <= 0 for pid in pids) or len(set(pids)) != len(pids):
                _fail("dual_live_quiescence_indeterminate")
            return pids
        error = ctypes.get_last_error()
        if error != _ERROR_MORE_DATA and assigned <= listed:
            _fail("dual_live_quiescence_indeterminate")
        capacity = max(capacity * 2, int(assigned), int(listed) + 1)
    _fail("dual_live_quiescence_indeterminate")


def _stable_job_process_ids(job_handle: int) -> tuple[int, ...]:
    first = _query_job_process_ids_once(job_handle)
    second = _query_job_process_ids_once(job_handle)
    if first != second:
        _fail("dual_live_quiescence_indeterminate")
    return first


def _job_accounting(job_handle: int) -> _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION:
    assert _kernel32 is not None
    accounting = _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
    returned = wintypes.DWORD()
    if not _kernel32.QueryInformationJobObject(
        job_handle,
        _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS,
        ctypes.byref(accounting),
        ctypes.sizeof(accounting),
        ctypes.byref(returned),
    ):
        _fail("dual_live_quiescence_indeterminate")
    if returned.value not in (0, ctypes.sizeof(accounting)):
        _fail("dual_live_quiescence_indeterminate")
    return accounting


def _owner_table_rows(
    *, family: int, protocol: str
) -> tuple[tuple[Any, ...], ...]:
    assert _iphlpapi is not None
    if protocol == "tcp":
        function = _iphlpapi.GetExtendedTcpTable
        table_class = _TCP_TABLE_OWNER_PID_ALL
        row_type: type[Any] = (
            _MIB_TCPROW_OWNER_PID if family == _AF_INET else _MIB_TCP6ROW_OWNER_PID
        )
    elif protocol == "udp":
        function = _iphlpapi.GetExtendedUdpTable
        table_class = _UDP_TABLE_OWNER_PID
        row_type = (
            _MIB_UDPROW_OWNER_PID if family == _AF_INET else _MIB_UDP6ROW_OWNER_PID
        )
    else:  # pragma: no cover - private closed call set
        _fail("dual_live_quiescence_indeterminate")
    required = wintypes.ULONG()
    result = function(None, ctypes.byref(required), False, family, table_class, 0)
    if result != _ERROR_INSUFFICIENT_BUFFER or required.value < 4:
        _fail("dual_live_quiescence_indeterminate")
    for _ in range(8):
        allocated = max(int(required.value), 4)
        buffer = ctypes.create_string_buffer(allocated)
        size = wintypes.ULONG(allocated)
        result = function(buffer, ctypes.byref(size), False, family, table_class, 0)
        if result == _ERROR_INSUFFICIENT_BUFFER:
            if size.value <= allocated:
                _fail("dual_live_quiescence_indeterminate")
            required = size
            continue
        if result != 0 or size.value > allocated:
            _fail("dual_live_quiescence_indeterminate")
        count = ctypes.c_uint32.from_buffer(buffer, 0).value
        row_size = ctypes.sizeof(row_type)
        if 4 + count * row_size > size.value:
            _fail("dual_live_quiescence_indeterminate")
        rows: list[tuple[Any, ...]] = []
        for index in range(count):
            row = row_type.from_buffer_copy(buffer, 4 + index * row_size)
            if protocol == "tcp" and family == _AF_INET:
                rows.append(
                    (
                        int(row.dwState),
                        int(row.dwLocalAddr),
                        int(row.dwLocalPort),
                        int(row.dwRemoteAddr),
                        int(row.dwRemotePort),
                        int(row.dwOwningPid),
                    )
                )
            elif protocol == "tcp":
                rows.append(
                    (
                        int(row.dwState),
                        bytes(row.ucLocalAddr),
                        int(row.dwLocalScopeId),
                        int(row.dwLocalPort),
                        bytes(row.ucRemoteAddr),
                        int(row.dwRemoteScopeId),
                        int(row.dwRemotePort),
                        int(row.dwOwningPid),
                    )
                )
            elif family == _AF_INET:
                rows.append(
                    (
                        int(row.dwLocalAddr),
                        int(row.dwLocalPort),
                        int(row.dwOwningPid),
                    )
                )
            else:
                rows.append(
                    (
                        bytes(row.ucLocalAddr),
                        int(row.dwLocalScopeId),
                        int(row.dwLocalPort),
                        int(row.dwOwningPid),
                    )
                )
        return tuple(rows)
    _fail("dual_live_quiescence_indeterminate")


def _socket_sample(target_pids: frozenset[int]) -> tuple[tuple[Any, ...], ...]:
    tables = (
        _owner_table_rows(family=_AF_INET, protocol="tcp"),
        _owner_table_rows(family=_AF_INET6, protocol="tcp"),
        _owner_table_rows(family=_AF_INET, protocol="udp"),
        _owner_table_rows(family=_AF_INET6, protocol="udp"),
    )
    filtered: list[tuple[Any, ...]] = []
    for table_index, rows in enumerate(tables):
        for row in rows:
            if int(row[-1]) in target_pids:
                filtered.append((table_index, *row))
    return tuple(sorted(filtered))


def _classify_socket_sample(
    sample: tuple[tuple[Any, ...], ...],
) -> tuple[dict[str, int], dict[str, int], int, int]:
    tcp4_counts = {state: 0 for state in WINDOWS_MIB_TCP_STATES}
    tcp6_counts = {state: 0 for state in WINDOWS_MIB_TCP_STATES}
    udp4_count = 0
    udp6_count = 0
    for row in sample:
        table_index = int(row[0])
        if table_index in (0, 1):
            state_number = int(row[1])
            if not 1 <= state_number <= len(WINDOWS_MIB_TCP_STATES):
                _fail("dual_live_quiescence_indeterminate")
            state_name = WINDOWS_MIB_TCP_STATES[state_number - 1]
            counts = tcp4_counts if table_index == 0 else tcp6_counts
            counts[state_name] += 1
        elif table_index == 2:
            udp4_count += 1
        elif table_index == 3:
            udp6_count += 1
        else:
            _fail("dual_live_quiescence_indeterminate")
    disallowed_tcp = sum(
        count
        for counts in (tcp4_counts, tcp6_counts)
        for state, count in counts.items()
        if state != "MIB_TCP_STATE_TIME_WAIT"
    )
    if disallowed_tcp or udp4_count or udp6_count:
        _fail("dual_live_child_not_quiescent")
    return tcp4_counts, tcp6_counts, udp4_count, udp6_count


def _prove_child_quiescence_unlocked(child: JobChild) -> dict[str, Any]:
    if not isinstance(child, JobChild):
        _fail("dual_live_windows_arguments_invalid")
    if (
        child._closed
        or child._job_handle is None
        or child._process_handle is None
        or child._creation_filetime is None
    ):
        _fail("dual_live_child_closed")
    if child._pretermination_retention_failure is not None:
        _fail("dual_live_quiescence_indeterminate")
    _validate_retained_processes(child)
    process_ids = _stable_job_process_ids(child._job_handle)
    _retain_active_job_processes(child, process_ids)
    _validate_retained_processes(child)
    if _stable_job_process_ids(child._job_handle) != process_ids:
        _fail("dual_live_quiescence_indeterminate")
    accounting = _job_accounting(child._job_handle)
    if int(accounting.ActiveProcesses) != len(process_ids):
        _fail("dual_live_quiescence_indeterminate")
    if process_ids:
        _fail("dual_live_child_not_quiescent")
    if int(accounting.TotalProcesses) != len(child._retained_processes):
        _fail("dual_live_quiescence_indeterminate")

    target_pids = frozenset(child._retained_processes)
    _validate_fresh_pid_occupancy(child)
    first_socket_sample = _socket_sample(target_pids)
    _validate_fresh_pid_occupancy(child)
    second_socket_sample = _socket_sample(target_pids)
    _validate_fresh_pid_occupancy(child)
    if first_socket_sample != second_socket_sample:
        _fail("dual_live_quiescence_indeterminate")
    _validate_retained_processes(child)
    if _stable_job_process_ids(child._job_handle):
        _fail("dual_live_quiescence_indeterminate")
    final_accounting = _job_accounting(child._job_handle)
    if (
        int(final_accounting.ActiveProcesses) != 0
        or int(final_accounting.TotalProcesses) != len(child._retained_processes)
    ):
        _fail("dual_live_quiescence_indeterminate")

    (
        tcp4_counts,
        tcp6_counts,
        udp4_count,
        udp6_count,
    ) = _classify_socket_sample(first_socket_sample)

    retained_identity_hashes = sorted(
        hashlib.sha256(
            _canonical_json_bytes(
                {
                    "executable_sha256": retained[2],
                    "pid": pid,
                    "process_creation_identity_sha256": retained[3],
                }
            )
        ).hexdigest()
        for pid, retained in child._retained_processes.items()
    )
    process_identity_sha256 = hashlib.sha256(
        _canonical_json_bytes(retained_identity_hashes)
    ).hexdigest()
    return {
        "active_process_count": 0,
        "process_list_sha256": hashlib.sha256(
            _canonical_json_bytes([])
        ).hexdigest(),
        "tcp4_state_counts": tcp4_counts,
        "tcp6_state_counts": tcp6_counts,
        "udp4_count": udp4_count,
        "udp6_count": udp6_count,
        "process_identity_sha256": process_identity_sha256,
        "stable": True,
    }


def prove_child_quiescence(child: JobChild) -> dict[str, Any]:
    if not isinstance(child, JobChild):
        _fail("dual_live_windows_arguments_invalid")
    with child._lock:
        return _prove_child_quiescence_unlocked(child)


def _retain_owned_handle_for_retry(handle: int) -> None:
    with _retained_owned_handles_lock:
        _retained_owned_handles.add(handle)


def _retry_retained_owned_handles() -> None:
    assert _kernel32 is not None
    with _native_custody_gate:
        with _retained_owned_handles_lock:
            failed = False
            for handle in tuple(_retained_owned_handles):
                if _kernel32.CloseHandle(handle):
                    _retained_owned_handles.remove(handle)
                else:
                    failed = True
            if failed:
                _fail("dual_live_owned_handle_cleanup_failed")


def _duplicate_owned_handle_locked(source_handle: int) -> int:
    assert _kernel32 is not None
    current_process = _kernel32.GetCurrentProcess()
    duplicate = wintypes.HANDLE()
    created = bool(current_process) and bool(
        _kernel32.DuplicateHandle(
            current_process,
            source_handle,
            current_process,
            ctypes.byref(duplicate),
            0,
            False,
            _DUPLICATE_SAME_ACCESS,
        )
    )
    copied = int(duplicate.value) if duplicate.value else None
    if not created or copied is None:
        if copied is not None and not _kernel32.CloseHandle(copied):
            _retain_owned_handle_for_retry(copied)
            _fail("dual_live_owned_handle_cleanup_failed")
        _fail("dual_live_owned_handle_duplicate_failed")
    flags = wintypes.DWORD()
    if (
        not _kernel32.GetHandleInformation(copied, ctypes.byref(flags))
        or flags.value != 0
    ):
        if not _kernel32.CloseHandle(copied):
            _retain_owned_handle_for_retry(copied)
            _fail("dual_live_owned_handle_cleanup_failed")
        _fail("dual_live_owned_handle_duplicate_failed")
    return copied


def _duplicate_owned_handle(source_handle: int) -> int:
    with _native_custody_gate:
        _drain_native_custody()
        return _duplicate_owned_handle_locked(source_handle)


def _duplicate_current_thread_handle() -> int:
    assert _kernel32 is not None
    return _duplicate_owned_handle(int(_kernel32.GetCurrentThread()))


class _OwnedPipeReader:
    __slots__ = (
        "_active_thread",
        "_active_thread_handle",
        "_closed",
        "_lock",
        "_pipe_handle",
    )

    def __init__(self, pipe_handle: int) -> None:
        self._pipe_handle: int | None = pipe_handle
        self._active_thread: threading.Thread | None = None
        self._active_thread_handle: int | None = None
        self._closed = False
        self._lock = threading.Lock()

    def read(self, size: int = -1) -> bytes:
        return self._read_with_duplicate(size, _duplicate_owned_handle)

    def _read_in_native_custody_window(
        self,
        size: int,
        factory_token: object,
    ) -> bytes:
        if (
            factory_token is not _OWNED_PROCESS_FACTORY_TOKEN
            or not _owned_factory_window_active.is_set()
        ):
            _fail("dual_live_owned_process_factory_only")
        return self._read_with_duplicate(size, _duplicate_owned_handle_locked)

    def _read_with_duplicate(
        self,
        size: int,
        duplicate_handle: Callable[[int], int],
    ) -> bytes:
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            _fail("dual_live_owned_reader_size_invalid")
        with self._lock:
            if self._closed or self._pipe_handle is None:
                return b""
            if self._active_thread_handle is not None:
                _fail("dual_live_owned_reader_concurrent")
            assert _kernel32 is not None
            active_handle = duplicate_handle(int(_kernel32.GetCurrentThread()))
            self._active_thread_handle = active_handle
            self._active_thread = threading.current_thread()
            pipe_handle = self._pipe_handle
        try:
            buffer = ctypes.create_string_buffer(size)
            received = wintypes.DWORD()
            assert _kernel32 is not None
            ctypes.set_last_error(0)
            if not _kernel32.ReadFile(
                pipe_handle,
                buffer,
                size,
                ctypes.byref(received),
                None,
            ):
                error = ctypes.get_last_error()
                with self._lock:
                    closed = self._closed
                if error == _ERROR_BROKEN_PIPE or (
                    closed and error == _ERROR_OPERATION_ABORTED
                ):
                    return b""
                _fail("dual_live_owned_reader_failed")
            return bytes(buffer.raw[: received.value])
        finally:
            close_failed = False
            with self._lock:
                if self._active_thread_handle == active_handle:
                    self._active_thread = None
                    if _kernel32.CloseHandle(active_handle):
                        self._active_thread_handle = None
                    else:
                        close_failed = True
            if close_failed:
                _fail("dual_live_owned_reader_close_failed")

    def close(self) -> None:
        active_thread: threading.Thread | None
        cancel_failure: BaseException | None = None
        with self._lock:
            if (
                self._closed
                and self._pipe_handle is None
                and self._active_thread_handle is None
            ):
                return
            self._closed = True
            active_thread = self._active_thread
            active_handle = self._active_thread_handle
            if active_thread is not None and active_handle is not None:
                ctypes.set_last_error(0)
                assert _cancel_synchronous_io is not None
                cancelled = _cancel_synchronous_io(active_handle)
                error = ctypes.get_last_error()
                if not cancelled and error not in (_ERROR_NOT_FOUND,):
                    cancel_failure = DualLiveWindowsError(
                        "dual_live_owned_reader_cancel_failed"
                    )
        if active_thread is not None and active_thread is not threading.current_thread():
            active_thread.join(_OWNED_IO_TIMEOUT_SECONDS)
            if active_thread.is_alive():
                stuck = DualLiveWindowsError("dual_live_owned_reader_cancel_stuck")
                if cancel_failure is not None:
                    stuck.__context__ = cancel_failure
                raise stuck
        close_failure: BaseException | None = None
        with self._lock:
            if self._active_thread is None and self._active_thread_handle is not None:
                if _kernel32.CloseHandle(self._active_thread_handle):
                    self._active_thread_handle = None
                else:
                    close_failure = DualLiveWindowsError(
                        "dual_live_owned_reader_close_failed"
                    )
            if self._pipe_handle is not None:
                if not _kernel32.CloseHandle(self._pipe_handle):
                    pipe_failure = DualLiveWindowsError(
                        "dual_live_owned_reader_close_failed"
                    )
                    if close_failure is None:
                        close_failure = pipe_failure
                    else:
                        close_failure.__context__ = pipe_failure
                else:
                    self._pipe_handle = None
        if cancel_failure is not None:
            if close_failure is not None:
                cancel_failure.__context__ = close_failure
            raise cancel_failure
        if close_failure is not None:
            raise close_failure


class _OwnedControlWriter:
    __slots__ = (
        "_cancel_requested",
        "_cleanup_lock",
        "_done",
        "_frame",
        "_io_started",
        "_joined",
        "_lock",
        "_pipe_handle",
        "_ready",
        "_result",
        "_start_complete",
        "_start_failure",
        "_start_state",
        "_thread",
        "_thread_handle",
    )

    _cancel_requested: bool
    _cleanup_lock: threading.Lock
    _done: threading.Event
    _frame: bytes
    _io_started: bool
    _joined: bool
    _lock: threading.Lock
    _pipe_handle: int | None
    _ready: threading.Event
    _result: BaseException | int | None
    _start_complete: threading.Event
    _start_failure: BaseException | None
    _start_state: str
    _thread: threading.Thread
    _thread_handle: int | None

    def __init__(self, source_handle: int, frame: bytes) -> None:
        self._cancel_requested = False
        self._cleanup_lock = threading.Lock()
        self._done = threading.Event()
        self._frame = frame
        self._io_started = False
        self._joined = False
        self._lock = threading.Lock()
        self._pipe_handle: int | None = None
        self._ready = threading.Event()
        self._result = None
        self._start_complete = threading.Event()
        self._start_failure = None
        self._start_state = "new"
        self._thread_handle = None
        with _native_custody_gate:
            _drain_native_custody()
            self._pipe_handle = _duplicate_owned_handle_locked(source_handle)
            try:
                self._thread = threading.Thread(
                    target=self._write,
                    name="dual-live-owned-control",
                    daemon=False,
                )
            except BaseException as exc:
                failure = DualLiveWindowsError(
                    "dual_live_owned_control_start_failed"
                )
                try:
                    _close_handle(self._pipe_handle)
                except BaseException as cleanup_failure:
                    self._pipe_handle = None
                    cleanup = DualLiveWindowsError(
                        "dual_live_owned_control_cleanup_failed"
                    )
                    cleanup.__context__ = exc
                    raise cleanup from cleanup_failure
                self._pipe_handle = None
                raise failure from exc

    @property
    def custody_released(self) -> bool:
        with self._lock:
            return (
                self._joined
                and self._pipe_handle is None
                and self._thread_handle is None
            )

    def start(self) -> None:
        with self._lock:
            if self._start_state == "cancelled":
                _fail("dual_live_owned_control_start_failed")
            if self._start_state != "new":
                _fail("dual_live_owned_control_start_invalid")
            self._start_state = "starting"
        try:
            self._thread.start()
        except BaseException as exc:
            with self._lock:
                self._start_failure = exc
                self._start_state = "start_failed"
            self._start_complete.set()
            raise DualLiveWindowsError(
                "dual_live_owned_control_start_failed"
            ) from exc
        with self._lock:
            self._start_state = "started"
        self._start_complete.set()

    def _write(self) -> None:
        try:
            thread_handle = _duplicate_current_thread_handle()
        except BaseException as exc:
            with self._lock:
                self._result = exc
            self._ready.set()
            self._done.set()
            return

        with self._lock:
            self._thread_handle = thread_handle
        self._ready.set()
        with self._lock:
            if self._cancel_requested:
                self._result = DualLiveWindowsError(
                    "dual_live_owned_control_cancelled"
                )
                self._done.set()
                return
            pipe_handle = self._pipe_handle
            if pipe_handle is None:
                self._result = DualLiveWindowsError(
                    "dual_live_owned_control_custody_unproven"
                )
                self._done.set()
                return
            self._io_started = True

        try:
            written = wintypes.DWORD()
            buffer = ctypes.create_string_buffer(self._frame)
            assert _kernel32 is not None
            if not _kernel32.WriteFile(
                pipe_handle,
                buffer,
                len(self._frame),
                ctypes.byref(written),
                None,
            ):
                _fail("dual_live_owned_control_write_failed")
            result: BaseException | int = int(written.value)
        except BaseException as exc:
            result = exc
        with self._lock:
            self._io_started = False
            self._result = result
        self._done.set()

    def _close_capabilities(self) -> None:
        failures: list[BaseException] = []
        with self._cleanup_lock:
            with self._lock:
                thread_handle = self._thread_handle
                pipe_handle = self._pipe_handle
            if thread_handle is not None:
                try:
                    closed = bool(_kernel32.CloseHandle(thread_handle))
                except BaseException as exc:
                    failures.append(exc)
                else:
                    if closed:
                        with self._lock:
                            if self._thread_handle == thread_handle:
                                self._thread_handle = None
                    else:
                        failures.append(
                            DualLiveWindowsError(
                                "dual_live_owned_control_cleanup_failed"
                            )
                        )
            if pipe_handle is not None:
                try:
                    closed = bool(_kernel32.CloseHandle(pipe_handle))
                except BaseException as exc:
                    failures.append(exc)
                else:
                    if closed:
                        with self._lock:
                            if self._pipe_handle == pipe_handle:
                                self._pipe_handle = None
                    else:
                        failures.append(
                            DualLiveWindowsError(
                                "dual_live_owned_control_cleanup_failed"
                            )
                        )
        if failures:
            raise DualLiveWindowsError(
                "dual_live_owned_control_cleanup_failed"
            ) from failures[0]

    def _cancel_io(self) -> BaseException | None:
        with self._lock:
            self._cancel_requested = True
            if self._start_state == "new":
                self._start_state = "cancelled"
                self._start_complete.set()
            thread_handle = self._thread_handle if self._io_started else None
        if thread_handle is None:
            return None
        try:
            ctypes.set_last_error(0)
            assert _cancel_synchronous_io is not None
            cancelled = _cancel_synchronous_io(thread_handle)
            error = ctypes.get_last_error()
        except BaseException as exc:
            return exc
        if not cancelled and error != _ERROR_NOT_FOUND:
            return DualLiveWindowsError(
                "dual_live_owned_control_cancel_failed"
            )
        return None

    def _join_and_release(self, *, cancel: bool) -> None:
        cancel_failure = self._cancel_io() if cancel else None
        with self._lock:
            start_state = self._start_state
        if start_state == "starting":
            if not self._start_complete.wait(_OWNED_IO_TIMEOUT_SECONDS):
                stuck = DualLiveWindowsError(
                    "dual_live_owned_control_custody_unproven"
                )
                if cancel_failure is not None:
                    stuck.__context__ = cancel_failure
                raise stuck
            with self._lock:
                start_state = self._start_state
        if start_state == "cancelled":
            pass
        elif self._thread.ident is None:
            if start_state != "start_failed":
                stuck = DualLiveWindowsError(
                    "dual_live_owned_control_custody_unproven"
                )
                if cancel_failure is not None:
                    stuck.__context__ = cancel_failure
                raise stuck
        else:
            try:
                self._thread.join(_OWNED_IO_TIMEOUT_SECONDS)
            except BaseException as exc:
                stuck = DualLiveWindowsError(
                    "dual_live_owned_control_write_stuck"
                )
                stuck.__cause__ = exc
                stuck.__context__ = cancel_failure
                raise stuck
            if self._thread.is_alive():
                stuck = DualLiveWindowsError(
                    "dual_live_owned_control_write_stuck"
                )
                stuck.__context__ = cancel_failure
                raise stuck
        with self._lock:
            self._joined = True
        try:
            self._close_capabilities()
        except BaseException as cleanup_failure:
            if cancel_failure is not None:
                cleanup_failure.__context__ = cancel_failure
            raise
        if cancel_failure is not None:
            raise DualLiveWindowsError(
                "dual_live_owned_control_cancel_failed"
            ) from cancel_failure

    def cancel_and_join(self) -> None:
        self._join_and_release(cancel=True)

    def wait(self) -> None:
        if not self._ready.wait(_OWNED_IO_TIMEOUT_SECONDS):
            stuck = DualLiveWindowsError("dual_live_owned_control_write_stuck")
            try:
                self.cancel_and_join()
            except BaseException as cleanup_failure:
                stuck.__context__ = cleanup_failure
            raise stuck
        if not self._done.wait(_OWNED_IO_TIMEOUT_SECONDS):
            stuck = DualLiveWindowsError("dual_live_owned_control_write_stuck")
            try:
                self.cancel_and_join()
            except BaseException as cleanup_failure:
                stuck.__context__ = cleanup_failure
            raise stuck
        self._join_and_release(cancel=False)
        with self._lock:
            result = self._result
        if isinstance(result, BaseException):
            raise DualLiveWindowsError(
                "dual_live_owned_control_write_failed"
            ) from result
        if result is None:
            _fail("dual_live_owned_control_write_failed")
        if result != len(self._frame):
            _fail("dual_live_owned_control_short_write")


def _write_owned_control_once(writer: _OwnedControlWriter) -> None:
    writer.wait()


def _read_owned_boot(reader: _OwnedPipeReader) -> dict[str, str]:
    result: list[bytes | None | BaseException] = []

    def read_boot() -> None:
        try:
            header = reader._read_in_native_custody_window(
                4,
                _OWNED_PROCESS_FACTORY_TOKEN,
            )
            if len(header) != 4:
                _fail("dual_live_owned_boot_invalid")
            size = int.from_bytes(header, "big")
            if size <= 0 or size > 4096:
                _fail("dual_live_owned_boot_invalid")
            chunks = bytearray()
            while len(chunks) < size:
                chunk = reader._read_in_native_custody_window(
                    size - len(chunks),
                    _OWNED_PROCESS_FACTORY_TOKEN,
                )
                if not chunk:
                    _fail("dual_live_owned_boot_invalid")
                chunks.extend(chunk)
            result.append(bytes(chunks))
        except BaseException as exc:
            result.append(exc)

    worker = threading.Thread(target=read_boot, name="dual-live-owned-boot", daemon=True)
    worker.start()
    worker.join(_OWNED_IO_TIMEOUT_SECONDS)
    if worker.is_alive():
        reader.close()
        worker.join(_OWNED_IO_TIMEOUT_SECONDS)
        _fail("dual_live_owned_boot_timeout")
    if len(result) != 1 or isinstance(result[0], BaseException):
        cause = result[0] if result and isinstance(result[0], BaseException) else None
        raise DualLiveWindowsError("dual_live_owned_boot_invalid") from cause
    assert isinstance(result[0], bytes)
    try:
        value = json.loads(result[0].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise DualLiveWindowsError("dual_live_owned_boot_invalid") from exc
    expected_keys = (
        "control_nonce",
        "phase",
        "process_boot_id",
        "schema_id",
        "status_nonce_sha256",
    )
    if (
        type(value) is not dict
        or tuple(value) != expected_keys
        or _canonical_json_bytes(value) != result[0]
        or value["schema_id"] != _OWNED_BOOT_SCHEMA_ID
        or value["phase"] not in {"A", "B"}
    ):
        _fail("dual_live_owned_boot_invalid")
    for field in ("control_nonce", "process_boot_id", "status_nonce_sha256"):
        _require_sha256(value[field])
    return {key: value[key] for key in expected_keys}


def _owned_domain_nonce(
    domain: str,
    *,
    process_boot_id: str,
    wrapper_nonce_sha256: str,
) -> str:
    if domain not in {"control", "status"}:
        _fail("dual_live_owned_boot_invalid")
    return hashlib.sha256(
        _canonical_json_bytes(
            {
                "domain": f"project6.dual_live_owned.{domain}.v1",
                "process_boot_id": _require_sha256(process_boot_id),
                "wrapper_nonce_sha256": _require_sha256(wrapper_nonce_sha256),
            }
        )
    ).hexdigest()


_OWNED_PROCESS_FACTORY_TOKEN = object()


class OwnedPhaseProcess:
    __slots__ = (
        "_authority_environment_names",
        "_authority_revoked",
        "_child",
        "_counter_ack_event_handle",
        "_control_consumed",
        "_control_writer",
        "_control_write_handle",
        "_job_payloads",
        "_lock",
        "_phase",
        "_readers",
        "_revocation_event_handle",
        "_send_idle_event_handle",
        "_stopped",
        "boot_frame_sha256",
        "control_nonce",
        "executable_sha256",
        "job_policy_sha256",
        "process_boot_id",
        "process_creation_identity_sha256",
        "status_nonce_sha256",
    )

    _authority_environment_names: frozenset[str]
    _authority_revoked: bool
    _child: JobChild | None
    _counter_ack_event_handle: int | None
    _control_consumed: bool
    _control_writer: _OwnedControlWriter | None
    _control_write_handle: int | None
    _job_payloads: tuple[Mapping[str, Any], Mapping[str, Any]] | None
    _lock: threading.RLock
    _phase: str
    _readers: Mapping[str, _OwnedPipeReader]
    _revocation_event_handle: int | None
    _send_idle_event_handle: int | None
    _stopped: bool
    boot_frame_sha256: str
    control_nonce: str
    executable_sha256: str
    job_policy_sha256: str
    process_boot_id: str
    process_creation_identity_sha256: str
    status_nonce_sha256: str

    def __new__(cls, *args: object, **kwargs: object) -> OwnedPhaseProcess:
        del args, kwargs
        _fail("dual_live_owned_process_factory_only")

    @classmethod
    def _from_factory(
        cls,
        factory_token: object,
        *,
        phase: str,
        child: JobChild,
        handles: Mapping[str, int],
        boot: Mapping[str, str],
        readers: Mapping[str, _OwnedPipeReader],
        boot_frame_sha256: str,
        authority_environment_names: frozenset[str],
    ) -> OwnedPhaseProcess:
        if (
            factory_token is not _OWNED_PROCESS_FACTORY_TOKEN
            or type(authority_environment_names) is not frozenset
            or any(
                type(name) is not str
                or name not in _OWNED_PHASE_A_AUTHORITY_ENVIRONMENT
                for name in authority_environment_names
            )
            or (phase == "B" and authority_environment_names)
        ):
            _fail("dual_live_owned_process_factory_only")
        evidence = child.start_evidence
        instance: OwnedPhaseProcess = object.__new__(cls)
        instance._phase = phase
        instance._child = child
        instance._control_write_handle = handles[
            "wrapper_control_write_handle"
        ]
        instance._control_writer = None
        instance._revocation_event_handle = handles.get(
            "wrapper_revocation_event_handle"
        )
        instance._send_idle_event_handle = handles.get(
            "wrapper_send_idle_event_handle"
        )
        instance._counter_ack_event_handle = handles.get(
            "wrapper_counter_ack_event_handle"
        )
        instance._readers = MappingProxyType(dict(readers))
        instance._control_consumed = False
        instance._authority_environment_names = authority_environment_names
        instance._authority_revoked = False
        instance._stopped = False
        instance._job_payloads = None
        instance._lock = threading.RLock()
        instance.boot_frame_sha256 = _require_sha256(boot_frame_sha256)
        instance.process_boot_id = _require_sha256(boot["process_boot_id"])
        instance.process_creation_identity_sha256 = (
            evidence.process_creation_identity_sha256
        )
        instance.executable_sha256 = evidence.executable_sha256
        instance.job_policy_sha256 = evidence.job_policy_sha256
        instance.status_nonce_sha256 = _require_sha256(
            boot["status_nonce_sha256"]
        )
        instance.control_nonce = _require_sha256(boot["control_nonce"])
        return instance

    @property
    def readers(self) -> Mapping[str, _OwnedPipeReader]:
        return self._readers

    def _finalize_control_writer(self, writer: _OwnedControlWriter) -> None:
        with self._lock:
            if self._control_writer is not writer or not writer.custody_released:
                return
            handle = self._control_write_handle
            if handle is not None:
                if not _kernel32.CloseHandle(handle):
                    _fail("dual_live_owned_control_cleanup_failed")
                self._control_write_handle = None
            self._control_writer = None

    def send_control(self, frame: bytes) -> None:
        if not isinstance(frame, bytes) or not frame or len(frame) > 4096:
            _fail("dual_live_owned_control_invalid")
        writer: _OwnedControlWriter | None = None
        primary_failure: BaseException | None = None
        with self._lock:
            if self._control_consumed:
                _fail("dual_live_owned_control_consumed")
            if self._control_write_handle is None:
                _fail("dual_live_owned_process_closed")
            self._control_consumed = True
            handle = self._control_write_handle
            try:
                writer = _OwnedControlWriter(handle, frame)
                self._control_writer = writer
            except BaseException as exc:
                primary_failure = exc
        if writer is None:
            assert primary_failure is not None
            raise primary_failure
        try:
            writer.start()
        except BaseException as exc:
            primary_failure = exc
        if primary_failure is None:
            try:
                _write_owned_control_once(writer)
            except BaseException as exc:
                primary_failure = exc
        else:
            try:
                writer.cancel_and_join()
            except BaseException as cleanup_failure:
                primary_failure.__context__ = cleanup_failure
        try:
            self._finalize_control_writer(writer)
        except BaseException as cleanup_failure:
            if primary_failure is None:
                primary_failure = cleanup_failure
            else:
                primary_failure.__context__ = cleanup_failure
        if primary_failure is not None:
            raise primary_failure

    def poll_exit(self, timeout: float) -> int | None:
        with self._lock:
            child = self._child
        if child is None:
            _fail("dual_live_owned_process_closed")
        return child.poll_exit(timeout)

    def ack_http_frame(self) -> None:
        with self._lock:
            if self._phase != "A":
                _fail("dual_live_owned_counter_ack_invalid")
            handle = self._counter_ack_event_handle
            if handle is None or self._stopped:
                _fail("dual_live_owned_process_closed")
            if not _kernel32.SetEvent(handle):
                _fail("dual_live_owned_counter_ack_failed")

    def revoke_before_stop(self, reason: str) -> None:
        if not isinstance(reason, str) or not reason or len(reason) > 64:
            _fail("dual_live_owned_revocation_invalid")
        with self._lock:
            if self._phase == "B":
                return
            if self._revocation_event_handle is None:
                _fail("dual_live_owned_process_closed")
            if self._authority_revoked:
                return
            if not _kernel32.SetEvent(self._revocation_event_handle):
                _fail("dual_live_owned_revocation_failed")
            self._authority_revoked = True

    def stop(self) -> None:
        with self._lock:
            if self._stopped:
                return
            child = self._child
            if child is None:
                self._stopped = True
                return
            phase = self._phase
        primary_failure: BaseException | None = None
        if phase == "A":
            try:
                self.revoke_before_stop("owned_stop")
            except BaseException as exc:
                primary_failure = exc
            try:
                with self._lock:
                    send_idle = self._send_idle_event_handle
                if send_idle is None:
                    _fail("dual_live_owned_process_closed")
                wait_ms = int(_OWNED_IO_TIMEOUT_SECONDS * 1000)
                if (
                    _kernel32.WaitForSingleObject(send_idle, wait_ms)
                    != _WAIT_OBJECT_0
                ):
                    _fail("dual_live_owned_send_idle_unproven")
            except BaseException as exc:
                if primary_failure is None:
                    primary_failure = exc
                else:
                    primary_failure.__context__ = exc
        try:
            child.retain_then_terminate_tree()
        except BaseException as termination_failure:
            if primary_failure is not None:
                termination_failure.__context__ = primary_failure
            raise
        with self._lock:
            self._stopped = True
        if primary_failure is not None:
            raise primary_failure

    def clear_authority_coordinates(self) -> None:
        with self._lock:
            if (
                self._phase != "A"
                or not self._authority_revoked
                or not self._stopped
                or self._child is not None
                or self._job_payloads is None
            ):
                _fail("dual_live_owned_authority_not_cleared")
            self._authority_environment_names = frozenset()

    def discard_authority_coordinates(self) -> None:
        with self._lock:
            self._authority_environment_names = frozenset()

    def authority_coordinate_posture(self) -> Mapping[str, Any]:
        with self._lock:
            return MappingProxyType(
                {
                    "retained_environment_names": tuple(
                        sorted(self._authority_environment_names)
                    ),
                    "revoked": self._authority_revoked,
                    "stopped": (
                        self._stopped
                        and self._child is None
                        and self._job_payloads is not None
                    ),
                }
            )

    def authority_cleared_payload(self) -> Mapping[str, Any]:
        self.clear_authority_coordinates()
        posture_state = self.authority_coordinate_posture()
        parent_remaining = sum(
            name.upper() in _OWNED_PHASE_A_AUTHORITY_ENVIRONMENT
            for name in os.environ
        )
        posture = {
            "required_environment_names": list(
                OWNED_PHASE_A_AUTHORITY_ENVIRONMENT_NAMES
            ),
            "parent_remaining_count": parent_remaining,
            "retained_phase_a_environment_count": len(
                posture_state["retained_environment_names"]
            ),
            "child_revoked": posture_state["revoked"],
            "child_stopped": posture_state["stopped"],
        }
        all_required_absent = (
            posture["parent_remaining_count"] == 0
            and posture["retained_phase_a_environment_count"] == 0
            and posture["child_revoked"] is True
            and posture["child_stopped"] is True
        )
        return MappingProxyType(
            {
                "authority_posture_sha256": hashlib.sha256(
                    _canonical_json_bytes(posture)
                ).hexdigest(),
                "all_required_absent": all_required_absent,
            }
        )

    def quiesce_and_close(
        self,
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        with self._lock:
            if self._job_payloads is not None:
                return self._job_payloads
            if self._control_writer is not None:
                _fail("dual_live_owned_control_custody_unproven")
            child = self._child
            if child is None:
                _fail("dual_live_owned_process_closed")
            proof = prove_child_quiescence(child)
            socket_payload = MappingProxyType(
                {
                    key: proof[key]
                    for key in (
                        "tcp4_state_counts",
                        "tcp6_state_counts",
                        "udp4_count",
                        "udp6_count",
                        "process_identity_sha256",
                        "stable",
                    )
                }
            )
            job_payload = MappingProxyType(
                {
                    "active_process_count": proof["active_process_count"],
                    "process_list_sha256": proof["process_list_sha256"],
                }
            )
            child.close()
            self._child = None
            self._job_payloads = (socket_payload, job_payload)
            return self._job_payloads

    def close(self) -> None:
        failures: list[BaseException] = []
        with self._lock:
            writer = self._control_writer
            child = self._child
        if writer is not None:
            try:
                writer.cancel_and_join()
            except BaseException as exc:
                failures.append(exc)
            try:
                self._finalize_control_writer(writer)
            except BaseException as exc:
                failures.append(exc)
        if child is not None:
            try:
                self.stop()
            except BaseException as exc:
                failures.append(exc)
        for reader in self._readers.values():
            try:
                reader.close()
            except BaseException as exc:
                failures.append(exc)
        with self._lock:
            handles = (
                "_control_write_handle",
                "_counter_ack_event_handle",
                "_revocation_event_handle",
                "_send_idle_event_handle",
            )
            for name in handles:
                handle = getattr(self, name)
                if handle is not None:
                    if name == "_control_write_handle" and self._control_writer is not None:
                        continue
                    if _kernel32.CloseHandle(handle):
                        setattr(self, name, None)
                    else:
                        failures.append(
                            DualLiveWindowsError("dual_live_owned_cleanup_failed")
                        )
            child = self._child
        if child is not None:
            try:
                child.close()
            except BaseException as exc:
                failures.append(exc)
            else:
                with self._lock:
                    self._child = None
        if failures:
            raise DualLiveWindowsError("dual_live_owned_cleanup_failed") from failures[0]


def _close_owned_handles(handles: dict[str, int]) -> None:
    cleanup_failed = False
    for role, handle in tuple(handles.items()):
        if _kernel32.CloseHandle(handle):
            handles.pop(role, None)
        else:
            cleanup_failed = True
    if cleanup_failed:
        _fail("dual_live_owned_cleanup_failed")


class _OwnedCleanupCustody:
    __slots__ = ("child", "channels", "handles", "readers", "terminated")

    def __init__(
        self,
        *,
        child: JobChild | None = None,
        channels: PhaseChannels | None = None,
        handles: dict[str, int] | None = None,
        readers: dict[str, _OwnedPipeReader] | None = None,
    ) -> None:
        self.child = child
        self.channels = channels
        self.handles = handles if handles is not None else {}
        self.readers = readers if readers is not None else {}
        self.terminated = False

    @property
    def released(self) -> bool:
        return (
            self.child is None
            and self.channels is None
            and not self.handles
            and not self.readers
        )

    def retry(self) -> None:
        failures: list[BaseException] = []
        if self.child is not None and not self.terminated:
            try:
                self.child.retain_then_terminate_tree()
            except BaseException as exc:
                failures.append(exc)
            else:
                self.terminated = True
        if self.child is not None and self.terminated:
            try:
                self.child.close()
            except BaseException as exc:
                failures.append(exc)
            else:
                self.child = None
        for role, reader in tuple(self.readers.items()):
            try:
                reader.close()
            except BaseException as exc:
                failures.append(exc)
            else:
                self.readers.pop(role, None)
        try:
            _close_owned_handles(self.handles)
        except BaseException as exc:
            failures.append(exc)
        if self.channels is not None:
            try:
                self.channels.close()
            except BaseException as exc:
                failures.append(exc)
            else:
                self.channels = None
        if failures or not self.released:
            failure = DualLiveWindowsError("dual_live_owned_cleanup_failed")
            if failures:
                failure.__cause__ = failures[0]
                for current, following in zip(failures, failures[1:]):
                    current.__context__ = following
            raise failure


_failed_owned_custody_lock = threading.Lock()
_failed_owned_custodies: list[_OwnedCleanupCustody] = []


def _retain_failed_owned_custody(custody: _OwnedCleanupCustody) -> None:
    with _failed_owned_custody_lock:
        if custody not in _failed_owned_custodies:
            _failed_owned_custodies.append(custody)


def _retry_failed_owned_custodies() -> None:
    failures: list[BaseException] = []
    with _native_custody_gate:
        with _failed_owned_custody_lock:
            for custody in tuple(_failed_owned_custodies):
                try:
                    custody.retry()
                except BaseException as exc:
                    failures.append(exc)
                else:
                    _failed_owned_custodies.remove(custody)
    if failures:
        raise DualLiveWindowsError("dual_live_owned_cleanup_failed") from failures[0]


def _drain_native_custody() -> None:
    _retry_failed_phase_handle_custodies()
    _retry_retained_owned_handles()
    _retry_failed_provisional_owners()
    _retry_failed_owned_custodies()


def _create_owned_phase_process_locked(
    phase: str,
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
    environment: Mapping[str, str] | None = None,
) -> OwnedPhaseProcess:
    validated_phase = _require_phase(phase)
    runtime_instance_id = _require_uuid4(runtime_instance_id)
    wrapper_nonce_sha256 = _require_sha256(wrapper_nonce_sha256)
    _require_phase_channel_apis()
    channels: PhaseChannels | None = None
    child: JobChild | None = None
    owned_handles: dict[str, int] = {}
    readers: dict[str, _OwnedPipeReader] = {}
    try:
        channels = create_phase_channels(validated_phase)
        child = channels._admit_owned_child(
            _PHASE_CHANNELS_FACTORY_TOKEN,
            runtime_instance_id=runtime_instance_id,
            wrapper_nonce_sha256=wrapper_nonce_sha256,
            environment=environment,
        )
        with channels._lease_wrapper_handles(
            _PHASE_CHANNELS_FACTORY_TOKEN
        ) as wrapper_handles:
            for role, handle in wrapper_handles.items():
                if role == "wrapper_stdin_write_handle":
                    continue
                owned_handles[role] = _duplicate_owned_handle(handle)
        channels.close()
        for stream in ("app", "http", "stdout", "stderr"):
            role = f"wrapper_{stream}_read_handle"
            handle = owned_handles[role]
            reader = _OwnedPipeReader(handle)
            readers[stream] = reader
            owned_handles.pop(role)
        boot = _read_owned_boot(readers["app"])
        boot_payload = _canonical_json_bytes(boot)
        boot_frame_sha256 = hashlib.sha256(
            len(boot_payload).to_bytes(4, "big") + boot_payload
        ).hexdigest()
        evidence = child.start_evidence
        expected_status_nonce = _owned_domain_nonce(
            "status",
            process_boot_id=evidence.process_boot_id,
            wrapper_nonce_sha256=wrapper_nonce_sha256,
        )
        expected_control_nonce = _owned_domain_nonce(
            "control",
            process_boot_id=evidence.process_boot_id,
            wrapper_nonce_sha256=wrapper_nonce_sha256,
        )
        if (
            boot["phase"] != validated_phase
            or boot["process_boot_id"] != evidence.process_boot_id
            or boot["status_nonce_sha256"] != expected_status_nonce
            or boot["control_nonce"] != expected_control_nonce
        ):
            _fail("dual_live_owned_boot_invalid")
        return OwnedPhaseProcess._from_factory(
            _OWNED_PROCESS_FACTORY_TOKEN,
            phase=validated_phase,
            child=child,
            handles=owned_handles,
            boot=boot,
            readers=readers,
            boot_frame_sha256=boot_frame_sha256,
            authority_environment_names=frozenset(
                name.upper()
                for name in (
                    ()
                    if environment is None or validated_phase != "A"
                    else environment
                )
                if name.upper() in _OWNED_PHASE_A_AUTHORITY_ENVIRONMENT
            ),
        )
    except BaseException as primary_failure:
        custody = _OwnedCleanupCustody(
            child=child,
            channels=channels,
            handles=owned_handles,
            readers=readers,
        )
        cleanup_failure: BaseException | None = None
        for _ in range(2):
            try:
                custody.retry()
            except BaseException as exc:
                cleanup_failure = exc
            else:
                raise
        _retain_failed_owned_custody(custody)
        cleanup = DualLiveWindowsError("dual_live_owned_cleanup_failed")
        cleanup.__context__ = primary_failure
        assert cleanup_failure is not None
        raise cleanup from cleanup_failure


def _create_owned_phase_process(
    phase: str,
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
    environment: Mapping[str, str] | None = None,
) -> OwnedPhaseProcess:
    with _native_custody_gate:
        _drain_native_custody()
        if _owned_factory_window_active.is_set():
            _fail("dual_live_owned_process_factory_only")
        _owned_factory_window_active.set()
        try:
            return _create_owned_phase_process_locked(
                phase,
                runtime_instance_id,
                wrapper_nonce_sha256,
                environment,
            )
        finally:
            _owned_factory_window_active.clear()
