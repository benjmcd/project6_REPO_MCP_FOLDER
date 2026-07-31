from __future__ import annotations

import ctypes
import hashlib
import math
import os
import re
import subprocess
import threading
from collections.abc import Mapping, Sequence
from ctypes import wintypes
from pathlib import Path
from typing import Any, BinaryIO
from uuid import UUID

from app.services.connector_egress_authorization import canonical_json_bytes
from app.services.dual_live_runtime import WINDOWS_MIB_TCP_STATES


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_WAIT_OBJECT_0 = 0
_WAIT_ABANDONED_0 = 0x80
_WAIT_TIMEOUT = 0x102
_WAIT_FAILED = 0xFFFFFFFF
_ERROR_ALREADY_EXISTS = 183
_ERROR_INSUFFICIENT_BUFFER = 122
_ERROR_INVALID_PARAMETER = 87
_ERROR_NOT_FOUND = 1168
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


class DualLiveWindowsError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise DualLiveWindowsError(code)


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
else:  # pragma: no cover - exercised by platform-refusal tests
    _kernel32 = None
    _advapi32 = None
    _iphlpapi = None
    _ntdll = None


_held_lock = threading.Lock()
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
        _kernel32.CloseHandle(handle)


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


def _open_evidence_root(path: Path) -> tuple[int, str]:
    assert _kernel32 is not None
    handle = _kernel32.CreateFileW(
        str(path),
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
        identity = hashlib.sha256(
            canonical_json_bytes(
                {
                    "file_id": bytes(file_id.FileId.Identifier).hex(),
                    "final_path": final_path.value.replace("\\", "/").casefold(),
                    "security_descriptor_sha256": security_sha256,
                    "volume_serial_number": file_id.VolumeSerialNumber,
                }
            )
        ).hexdigest()
        return int(handle), identity
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
    if root_registered:
        with _held_lock:
            _held_roots.discard(root_identity_sha256)
            _held_campaigns.discard(campaign_identity_sha256)


def acquire_proof_locks(
    evidence_root: Path,
    campaign_id: str,
    campaign_fingerprint: str,
    campaign_definition_sha256: str,
    wait_ms: int = 0,
) -> ProofLocks:
    _require_windows()
    if not isinstance(evidence_root, Path) or not evidence_root.is_absolute():
        _fail("dual_live_windows_arguments_invalid")
    campaign_id = _require_uuid4(campaign_id)
    campaign_fingerprint = _require_sha256(campaign_fingerprint)
    campaign_definition_sha256 = _require_sha256(campaign_definition_sha256)
    if isinstance(wait_ms, bool) or not isinstance(wait_ms, int) or not 0 <= wait_ms < 2**32:
        _fail("dual_live_windows_arguments_invalid")

    root_directory, root_identity_sha256 = _open_evidence_root(evidence_root)
    campaign_identity_sha256 = hashlib.sha256(
        canonical_json_bytes(
            {
                "campaign_definition_sha256": campaign_definition_sha256,
                "campaign_fingerprint": campaign_fingerprint,
                "campaign_id": campaign_id,
            }
        )
    ).hexdigest()
    sid_buffer: ctypes.Array[ctypes.c_char] | None = None
    security_descriptor = wintypes.LPVOID()
    boundary_descriptor: int | None = None
    namespace_handle: int | None = None
    root_mutex: int | None = None
    campaign_mutex: int | None = None
    root_owned = False
    campaign_owned = False
    root_registered = False
    try:
        with _held_lock:
            if (
                root_identity_sha256 in _held_roots
                or campaign_identity_sha256 in _held_campaigns
            ):
                _fail("dual_live_lock_busy")
            _held_roots.add(root_identity_sha256)
            _held_campaigns.add(campaign_identity_sha256)
            root_registered = True
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
            canonical_json_bytes(
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
        canonical_json_bytes({"limit_flags": flags})
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
        "_retained_processes",
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
        self._retained_processes: dict[int, tuple[int, int, str, str]] = {}
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
        instance._retained_processes[pid] = (
            process_handle,
            creation_filetime,
            executable_sha256,
            process_creation_identity_sha256,
        )
        return instance

    def __enter__(self) -> JobChild:
        if self._closed:
            _fail("dual_live_child_closed")
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def wait(self, timeout_seconds: float) -> int:
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
            _fail("dual_live_child_timeout")
        if result != _WAIT_OBJECT_0:
            _fail("dual_live_child_wait_failed")
        exit_code = wintypes.DWORD()
        if not _kernel32.GetExitCodeProcess(
            self._process_handle, ctypes.byref(exit_code)
        ):
            _fail("dual_live_child_wait_failed")
        return int(exit_code.value)

    def terminate_tree(self) -> None:
        if self._closed or self._job_handle is None:
            _fail("dual_live_child_closed")
        assert _kernel32 is not None
        if not _kernel32.TerminateJobObject(self._job_handle, _TERMINATE_EXIT_CODE):
            _fail("dual_live_child_terminate_failed")

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
    __slots__ = ("job_handle", "process_handle", "thread_handle")

    def __init__(
        self,
        *,
        job_handle: int,
        process_handle: int,
        thread_handle: int,
    ) -> None:
        self.job_handle: int | None = job_handle
        self.process_handle: int | None = process_handle
        self.thread_handle: int | None = thread_handle

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
        if self.job_handle is not None and not _kernel32.TerminateJobObject(
            self.job_handle,
            _TERMINATE_EXIT_CODE,
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

    def disown(self) -> None:
        if self.thread_handle is not None:
            _fail("dual_live_child_cleanup_failed")
        self.process_handle = None
        self.job_handle = None


def create_child_in_job(
    argv: Sequence[str],
    environment: Mapping[str, str],
    inherited_handles: Sequence[int],
    runtime_instance_id: str,
    wrapper_nonce_sha256: str,
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
    executable_custody = _open_executable_custody(copied_argv[0])
    executable_sha256 = executable_custody.sha256
    job_handle: int | None = None
    provisional_owner: _ProvisionalJobOwner | None = None
    attribute_list: ctypes.Array[ctypes.c_char] | None = None
    attributes_initialized = False
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
        process_info = _PROCESS_INFORMATION()
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
        provisional_owner = _ProvisionalJobOwner(
            job_handle=int(job_handle),
            process_handle=int(process_info.hProcess),
            thread_handle=int(process_info.hThread),
        )
        job_handle = None
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
        creation = _FILETIME()
        exit_time = _FILETIME()
        kernel_time = _FILETIME()
        user_time = _FILETIME()
        if not _kernel32.GetProcessTimes(
            owned_process_handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            _fail("dual_live_process_identity_indeterminate")
        creation_filetime = _filetime_value(creation)
        if (
            _process_image_sha256(
                owned_process_handle,
                refusal_code="dual_live_process_identity_indeterminate",
            )
            != executable_sha256
        ):
            _fail("dual_live_process_identity_indeterminate")
        pid = int(process_info.dwProcessId)
        process_creation_identity_sha256 = hashlib.sha256(
            canonical_json_bytes(
                {"creation_filetime": creation_filetime, "pid": pid}
            )
        ).hexdigest()
        process_boot_id = hashlib.sha256(
            canonical_json_bytes(
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
        if provisional_owner is not None:
            cleanup_ok = provisional_owner.cleanup_after_failure()
            if not cleanup_ok or (
                isinstance(error, DualLiveWindowsError)
                and error.code == "dual_live_child_cleanup_failed"
            ):
                _fail("dual_live_child_cleanup_failed")
        raise
    finally:
        if attributes_initialized and attribute_list is not None:
            _kernel32.DeleteProcThreadAttributeList(attribute_list)
        _close_handle(job_handle)
        _close_handle(executable_custody.handle)


def _process_creation_filetime(process_handle: int) -> int:
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
        _fail("dual_live_quiescence_indeterminate")
    return _filetime_value(creation)


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
        expected_identity = hashlib.sha256(
            canonical_json_bytes(
                {"creation_filetime": current_creation, "pid": pid}
            )
        ).hexdigest()
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
            identity = hashlib.sha256(
                canonical_json_bytes(
                    {"creation_filetime": first_creation, "pid": pid}
                )
            ).hexdigest()
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
        row_type = _MIB_TCPROW_OWNER_PID if family == _AF_INET else _MIB_TCP6ROW_OWNER_PID
    elif protocol == "udp":
        function = _iphlpapi.GetExtendedUdpTable
        table_class = _UDP_TABLE_OWNER_PID
        row_type = _MIB_UDPROW_OWNER_PID if family == _AF_INET else _MIB_UDP6ROW_OWNER_PID
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


def prove_child_quiescence(child: JobChild) -> dict[str, Any]:
    if not isinstance(child, JobChild):
        _fail("dual_live_windows_arguments_invalid")
    if (
        child._closed
        or child._job_handle is None
        or child._process_handle is None
        or child._creation_filetime is None
    ):
        _fail("dual_live_child_closed")
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
            canonical_json_bytes(
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
        canonical_json_bytes(retained_identity_hashes)
    ).hexdigest()
    return {
        "active_process_count": 0,
        "process_list_sha256": hashlib.sha256(
            canonical_json_bytes([])
        ).hexdigest(),
        "tcp4_state_counts": tcp4_counts,
        "tcp6_state_counts": tcp6_counts,
        "udp4_count": udp4_count,
        "udp6_count": udp6_count,
        "process_identity_sha256": process_identity_sha256,
        "stable": True,
    }
