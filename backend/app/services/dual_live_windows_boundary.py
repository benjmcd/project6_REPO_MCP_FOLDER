"""Classic zero-capability AppContainer worker boundary for Windows.

The broker keeps the root/campaign mutex and a kill-on-close, one-process Job
Object for the entire worker lifetime.  Creation uses one ``CreateProcessW``
call with the security-capabilities, job-list, and exact inherited-handle
attributes installed together.  There is intentionally no weaker fallback.
"""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import ntpath
import os
import struct
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Iterator, Protocol, Sequence

from app.services import dual_live_worker_bundle as _bundle

from app.services.dual_live_effect_guard import (
    MAX_FRAME_BYTES,
    EffectBoundaryHold,
    WorkerIdentity,
    decode_frame,
    read_frame,
    write_frame,
)


ERROR_ALREADY_EXISTS = 183
ERROR_INSUFFICIENT_BUFFER = 122
ERROR_NOT_FOUND = 1168
ERROR_MORE_DATA = 234
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
HANDLE_FLAG_INHERIT = 0x00000001
STARTF_USESTDHANDLES = 0x00000100
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
CREATE_NO_WINDOW = 0x08000000
CREATE_SUSPENDED = 0x00000004
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
PROC_THREAD_ATTRIBUTE_JOB_LIST = 0x0002000D
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_BASIC_PROCESS_ID_LIST = 3
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
TOKEN_QUERY = 0x0008
TOKEN_IS_APP_CONTAINER = 29
TOKEN_CAPABILITIES = 30
TOKEN_APP_CONTAINER_SID = 31
AF_INET = 2
AF_INET6 = 23
TCP_TABLE_OWNER_PID_ALL = 5
UDP_TABLE_OWNER_PID = 1
SYNCHRONIZE = 0x00100000
THREAD_TERMINATE = 0x0001
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
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
    ]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class SECURITY_CAPABILITIES(ctypes.Structure):
    _fields_ = [
        ("AppContainerSid", ctypes.c_void_p),
        ("Capabilities", ctypes.c_void_p),
        ("CapabilityCount", wintypes.DWORD),
        ("Reserved", wintypes.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class TOKEN_APPCONTAINER_INFORMATION(ctypes.Structure):
    _fields_ = [("TokenAppContainer", ctypes.c_void_p)]


def _mutex_name(canonical_root: str, campaign_id: str) -> str:
    if not isinstance(canonical_root, str) or not ntpath.isabs(canonical_root):
        raise EffectBoundaryHold("root_not_canonical")
    if not isinstance(campaign_id, str) or not campaign_id or len(campaign_id) > 128:
        raise EffectBoundaryHold("campaign_invalid")
    root = ntpath.normcase(ntpath.abspath(canonical_root))
    digest = hashlib.sha256(f"{root}\0{campaign_id}".encode("utf-8")).hexdigest()
    return f"Local\\Project6DualLive-{digest}"


def _validate_launch_handles(handles: tuple[int, ...]) -> tuple[int, int]:
    if (
        not isinstance(handles, tuple)
        or len(handles) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in handles)
        or handles[0] == handles[1]
    ):
        raise EffectBoundaryHold("pipe_handles_invalid")
    return handles


def _quote_windows_arg(value: str) -> str:
    if not value:
        return '""'
    if not any(character in value for character in ' \t"'):
        return value
    result = ['"']
    slashes = 0
    for character in value:
        if character == "\\":
            slashes += 1
        elif character == '"':
            result.append("\\" * (slashes * 2 + 1))
            result.append('"')
            slashes = 0
        else:
            result.append("\\" * slashes)
            result.append(character)
            slashes = 0
    result.append("\\" * (slashes * 2))
    result.append('"')
    return "".join(result)


def _command_line(interpreter: str, args: Sequence[str]) -> str:
    if not isinstance(interpreter, str) or not ntpath.isabs(interpreter):
        raise EffectBoundaryHold("interpreter_not_absolute")
    if any(not isinstance(arg, str) or "\x00" in arg for arg in args):
        raise EffectBoundaryHold("worker_args_invalid")
    return " ".join(_quote_windows_arg(item) for item in (interpreter, *args))


def _open_pipe_stream(handle: int, mode: str) -> Any:
    if mode not in {"rb", "wb"} or isinstance(handle, bool) or not isinstance(handle, int) or handle <= 0:
        raise EffectBoundaryHold("pipe_handle_invalid")
    try:
        import msvcrt

        flags = os.O_BINARY | (os.O_RDONLY if mode == "rb" else os.O_WRONLY)
        descriptor = msvcrt.open_osfhandle(handle, flags)
        return os.fdopen(descriptor, mode, buffering=0, closefd=True)
    except (OSError, ValueError):
        raise EffectBoundaryHold("pipe_open_failed") from None


def open_pipe_reader(handle: int) -> Any:
    """Transfer one broker pipe handle into an unbuffered binary reader."""

    return _open_pipe_stream(handle, "rb")


def open_pipe_writer(handle: int) -> Any:
    """Transfer one broker pipe handle into an unbuffered binary writer."""

    return _open_pipe_stream(handle, "wb")


def _clear_inherited_pipe_handles(
    kernel32: Any,
    handles: tuple[int, int],
    job_handle: int,
) -> None:
    failed = False
    for handle in handles:
        if not kernel32.SetHandleInformation(handle, HANDLE_FLAG_INHERIT, 0):
            failed = True
    if failed:
        kernel32.TerminateJobObject(job_handle, 1)
        for handle in handles:
            kernel32.CloseHandle(handle)
        raise EffectBoundaryHold("pipe_inheritance_clear_failed")


class _Backend(Protocol):
    def acquire_mutex(self, name: str) -> int: ...
    def create_job(self) -> int: ...
    def launch_appcontainer_suspended(
        self,
        interpreter: str,
        args: tuple[str, ...],
        inherited_handles: tuple[int, ...],
        job_handle: int,
        *,
        profile_moniker: str,
        expected_package_sid: str,
        creation_flags: int,
    ) -> tuple[int, str, int, int, int]: ...
    def resume_thread(self, handle: int) -> int: ...
    def query_job_pids(self, job_handle: int) -> tuple[int, ...]: ...
    def query_sockets(self, pids: tuple[int, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]: ...
    def is_loopback_exempt(self, sid: str) -> bool: ...
    def create_probe_pipes(self) -> tuple[int, int, int, int]: ...
    def read_probe_frame(self, handle: int, timeout_ms: int) -> dict[str, Any]: ...
    def wait_process(self, process_handle: int, timeout_ms: int) -> int: ...
    def current_identity(self) -> WorkerIdentity: ...
    def probe_denials(self) -> tuple[int, int, int]: ...
    def open_current_thread(self) -> int: ...
    def cancel_synchronous_io(self, thread_handle: int) -> None: ...
    def close_handle(self, handle: int) -> None: ...
    def terminate_job(self, handle: int) -> None: ...


class _CtypesBackend:
    """Small stdlib-only binding to the exact Windows primitives we admit."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise EffectBoundaryHold("windows_required")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        self.userenv = ctypes.WinDLL("userenv", use_last_error=True)
        self.ole32 = ctypes.OleDLL("ole32")
        self.iphlpapi = ctypes.WinDLL("iphlpapi", use_last_error=True)
        self.firewallapi = ctypes.WinDLL("FirewallAPI", use_last_error=True)
        self._bind()

    def _bind(self) -> None:
        k32 = self.kernel32
        k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        k32.CreateMutexW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        k32.CloseHandle.restype = wintypes.BOOL
        k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        k32.SetInformationJobObject.restype = wintypes.BOOL
        k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        k32.QueryInformationJobObject.restype = wintypes.BOOL
        k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k32.TerminateJobObject.restype = wintypes.BOOL
        k32.GetCurrentThreadId.argtypes = []
        k32.GetCurrentThreadId.restype = wintypes.DWORD
        k32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenThread.restype = wintypes.HANDLE
        k32.CancelSynchronousIo.argtypes = [wintypes.HANDLE]
        k32.CancelSynchronousIo.restype = wintypes.BOOL
        k32.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)]
        k32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
        k32.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
        k32.UpdateProcThreadAttribute.restype = wintypes.BOOL
        k32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
        k32.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
        k32.CreateProcessW.restype = wintypes.BOOL
        k32.ResumeThread.argtypes = [wintypes.HANDLE]
        k32.ResumeThread.restype = wintypes.DWORD
        k32.CreatePipe.argtypes = [ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p, wintypes.DWORD]
        k32.CreatePipe.restype = wintypes.BOOL
        k32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
        k32.SetHandleInformation.restype = wintypes.BOOL
        k32.PeekNamedPipe.argtypes = [
            wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        k32.PeekNamedPipe.restype = wintypes.BOOL
        k32.ReadFile.argtypes = [
            wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
        ]
        k32.ReadFile.restype = wintypes.BOOL
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.WaitForSingleObject.restype = wintypes.DWORD
        k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k32.GetExitCodeProcess.restype = wintypes.BOOL
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.GetCurrentProcessId.restype = wintypes.DWORD
        k32.GetProcessHeap.restype = wintypes.HANDLE
        k32.HeapFree.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p]
        k32.HeapFree.restype = wintypes.BOOL
        self.advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        self.advapi32.OpenProcessToken.restype = wintypes.BOOL
        self.advapi32.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        self.advapi32.GetTokenInformation.restype = wintypes.BOOL
        self.advapi32.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        self.advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
        self.advapi32.EqualSid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.advapi32.EqualSid.restype = wintypes.BOOL
        self.advapi32.FreeSid.argtypes = [ctypes.c_void_p]
        self.advapi32.FreeSid.restype = ctypes.c_void_p
        self.userenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long
        self.iphlpapi.GetExtendedTcpTable.restype = wintypes.DWORD
        self.iphlpapi.GetExtendedUdpTable.restype = wintypes.DWORD

    def _win_error(self, code: str) -> EffectBoundaryHold:
        value = ctypes.get_last_error()
        digest = hashlib.sha256(f"win32:{value}".encode("ascii")).hexdigest()
        return EffectBoundaryHold(code, fact_digest=digest)

    def acquire_mutex(self, name: str) -> int:
        ctypes.set_last_error(0)
        handle = self.kernel32.CreateMutexW(None, False, name)
        if not handle:
            raise self._win_error("mutex_create_failed")
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            self.kernel32.CloseHandle(handle)
            raise EffectBoundaryHold("mutex_owned")
        return int(handle)

    def create_job(self) -> int:
        job = self.kernel32.CreateJobObjectW(None, None)
        if not job:
            raise self._win_error("job_create_failed")
        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limits.BasicLimitInformation.LimitFlags = (
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        )
        limits.BasicLimitInformation.ActiveProcessLimit = 1
        if not self.kernel32.SetInformationJobObject(
            job,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            self.kernel32.CloseHandle(job)
            raise self._win_error("job_configure_failed")
        return int(job)

    def _appcontainer_sid(
        self,
        profile_moniker: str,
        expected_package_sid: str,
    ) -> tuple[ctypes.c_void_p, str]:
        sid = ctypes.c_void_p()
        derive = self.userenv.DeriveAppContainerSidFromAppContainerName
        derive.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
        hr = int(derive(profile_moniker, ctypes.byref(sid)))
        unsigned_hr = ctypes.c_ulong(hr).value
        if unsigned_hr != 0 or not sid.value:
            digest = hashlib.sha256(f"hresult:{unsigned_hr:08x}".encode("ascii")).hexdigest()
            raise EffectBoundaryHold("appcontainer_profile_failed", fact_digest=digest)
        try:
            sid_text = self._sid_string(sid.value)
        except BaseException:
            self.advapi32.FreeSid(sid)
            raise
        if sid_text != expected_package_sid:
            self.advapi32.FreeSid(sid)
            raise EffectBoundaryHold("worker_sid_mismatch")
        return sid, sid_text

    def _sid_string(self, sid: int) -> str:
        text = wintypes.LPWSTR()
        if not self.advapi32.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise self._win_error("sid_format_failed")
        try:
            return str(text.value)
        finally:
            self.kernel32.LocalFree(text)

    def _attribute_list(
        self,
        security: SECURITY_CAPABILITIES,
        job_handle: int,
        inherited_handles: tuple[int, int],
    ) -> tuple[ctypes.Array[Any], Any, Any]:
        size = ctypes.c_size_t()
        self.kernel32.InitializeProcThreadAttributeList(None, 3, 0, ctypes.byref(size))
        if ctypes.get_last_error() != ERROR_INSUFFICIENT_BUFFER or not size.value:
            raise self._win_error("attribute_size_failed")
        buffer = ctypes.create_string_buffer(size.value)
        pointer = ctypes.cast(buffer, ctypes.c_void_p)
        if not self.kernel32.InitializeProcThreadAttributeList(pointer, 3, 0, ctypes.byref(size)):
            raise self._win_error("attribute_init_failed")
        jobs = (wintypes.HANDLE * 1)(job_handle)
        handles = (wintypes.HANDLE * 2)(*inherited_handles)
        updates = (
            (
                PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
                ctypes.byref(security),
                ctypes.sizeof(security),
            ),
            (PROC_THREAD_ATTRIBUTE_JOB_LIST, jobs, ctypes.sizeof(jobs)),
            (PROC_THREAD_ATTRIBUTE_HANDLE_LIST, handles, ctypes.sizeof(handles)),
        )
        try:
            for attribute, value, value_size in updates:
                if not self.kernel32.UpdateProcThreadAttribute(
                    pointer,
                    0,
                    attribute,
                    value,
                    value_size,
                    None,
                    None,
                ):
                    raise self._win_error("attribute_update_failed")
        except BaseException:
            self.kernel32.DeleteProcThreadAttributeList(pointer)
            raise
        return buffer, jobs, handles

    def _windows_directory(self) -> str:
        windows = ctypes.create_unicode_buffer(32768)
        length = self.kernel32.GetWindowsDirectoryW(windows, len(windows))
        if length <= 0 or length >= len(windows):
            raise self._win_error("windows_directory_failed")
        return str(windows.value)

    def _appcontainer_folder(self, sid_text: str) -> str:
        value = wintypes.LPWSTR()
        getter = self.userenv.GetAppContainerFolderPath
        getter.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.LPWSTR)]
        getter.restype = ctypes.c_long
        hr = int(getter(sid_text, ctypes.byref(value)))
        unsigned_hr = ctypes.c_ulong(hr).value
        if unsigned_hr != 0 or not value.value:
            digest = hashlib.sha256(f"hresult:{unsigned_hr:08x}".encode("ascii")).hexdigest()
            raise EffectBoundaryHold("appcontainer_folder_failed", fact_digest=digest)
        try:
            return str(value.value)
        finally:
            self.ole32.CoTaskMemFree(value)

    def _minimal_environment(
        self,
        windows_directory: str,
        appcontainer_folder: str,
    ) -> ctypes.Array[Any]:
        entries = {
            "LOCALAPPDATA": appcontainer_folder,
            "PATH": f"{windows_directory}\\System32",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONUTF8": "1",
            "SYSTEMROOT": windows_directory,
            "WINDIR": windows_directory,
        }
        block = "\0".join(f"{key}={entries[key]}" for key in sorted(entries)) + "\0\0"
        return ctypes.create_unicode_buffer(block)

    def launch_appcontainer_suspended(
        self,
        interpreter: str,
        args: tuple[str, ...],
        inherited_handles: tuple[int, ...],
        job_handle: int,
        *,
        profile_moniker: str,
        expected_package_sid: str,
        creation_flags: int,
    ) -> tuple[int, str, int, int]:
        if creation_flags != CREATE_SUSPENDED:
            raise EffectBoundaryHold("suspended_create_required")
        read_handle, write_handle = _validate_launch_handles(inherited_handles)
        sid: ctypes.c_void_p | None = None
        attributes: ctypes.Array[Any] | None = None
        process = PROCESS_INFORMATION()
        transfer_process_handles = False
        inheritance_clear_error: EffectBoundaryHold | None = None
        try:
            for handle in (read_handle, write_handle):
                if not self.kernel32.SetHandleInformation(
                    handle, HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT,
                ):
                    raise self._win_error("pipe_inherit_failed")
            sid, sid_text = self._appcontainer_sid(profile_moniker, expected_package_sid)
            security = SECURITY_CAPABILITIES(sid.value, None, 0, 0)
            attributes, jobs, handles = self._attribute_list(
                security,
                job_handle,
                (read_handle, write_handle),
            )
            startup = STARTUPINFOEXW()
            startup.StartupInfo.cb = ctypes.sizeof(startup)
            startup.lpAttributeList = ctypes.cast(attributes, ctypes.c_void_p)
            command = ctypes.create_unicode_buffer(_command_line(interpreter, args))
            windows_directory = self._windows_directory()
            appcontainer_folder = self._appcontainer_folder(sid_text)
            environment = self._minimal_environment(windows_directory, appcontainer_folder)
            created = self.kernel32.CreateProcessW(
                interpreter,
                command,
                None,
                None,
                True,
                EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW | creation_flags,
                environment,
                windows_directory,
                ctypes.byref(startup.StartupInfo),
                ctypes.byref(process),
            )
            if not created:
                raise self._win_error("appcontainer_launch_failed")
            pid = int(process.dwProcessId)
            process_handle = int(process.hProcess)
            observed_sid = self._process_appcontainer_sid(process_handle)
            if observed_sid != expected_package_sid:
                raise EffectBoundaryHold("worker_sid_mismatch")
            thread = int(process.hThread)
            transfer_process_handles = True
            capability_count = self._process_capability_count(process_handle)
            return pid, observed_sid, capability_count, process_handle, thread
        finally:
            try:
                _clear_inherited_pipe_handles(
                    self.kernel32, (read_handle, write_handle), job_handle
                )
            except EffectBoundaryHold as exc:
                inheritance_clear_error = exc
            if transfer_process_handles and inheritance_clear_error is not None:
                transfer_process_handles = False
            if transfer_process_handles:
                process.hProcess = None
                process.hThread = None
            if attributes is not None:
                self.kernel32.DeleteProcThreadAttributeList(ctypes.cast(attributes, ctypes.c_void_p))
            if process.hThread:
                self.kernel32.CloseHandle(process.hThread)
            if process.hProcess:
                self.kernel32.CloseHandle(process.hProcess)
            if sid is not None:
                self.advapi32.FreeSid(sid)
            if inheritance_clear_error is not None:
                raise inheritance_clear_error

    def resume_thread(self, handle: int) -> int:
        previous = int(self.kernel32.ResumeThread(handle))
        if previous == 0xFFFFFFFF:
            raise self._win_error("worker_resume_failed")
        return previous

    def query_job_pids(self, job_handle: int) -> tuple[int, ...]:
        capacity = 8 + (ctypes.sizeof(ctypes.c_size_t) * 4)
        buffer = ctypes.create_string_buffer(capacity)
        returned = wintypes.DWORD()
        if not self.kernel32.QueryInformationJobObject(
            job_handle,
            JOB_OBJECT_BASIC_PROCESS_ID_LIST,
            buffer,
            capacity,
            ctypes.byref(returned),
        ):
            raise self._win_error("job_census_failed")
        assigned, count = struct.unpack_from("<II", buffer.raw)
        if assigned != count or count > 1:
            if count > 1:
                values = struct.unpack_from(
                    f"<{count}{'Q' if ctypes.sizeof(ctypes.c_size_t) == 8 else 'I'}",
                    buffer.raw,
                    8,
                )
                return tuple(int(value) for value in values)
            raise EffectBoundaryHold("job_census_ambiguous")
        if count == 0:
            return ()
        value = ctypes.c_size_t.from_buffer_copy(buffer.raw[8 : 8 + ctypes.sizeof(ctypes.c_size_t)])
        return (int(value.value),)

    @staticmethod
    def _port(value: int) -> int:
        return ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)

    def _socket_table(self, protocol: str, family: int) -> tuple[tuple[int, str], ...]:
        getter = self.iphlpapi.GetExtendedTcpTable if protocol == "tcp" else self.iphlpapi.GetExtendedUdpTable
        size = wintypes.DWORD(0)
        table_class = TCP_TABLE_OWNER_PID_ALL if protocol == "tcp" else UDP_TABLE_OWNER_PID
        result = getter(None, ctypes.byref(size), False, family, table_class, 0)
        if result not in (ERROR_INSUFFICIENT_BUFFER, ERROR_MORE_DATA) or not size.value:
            raise EffectBoundaryHold("socket_census_ambiguous")
        buffer = ctypes.create_string_buffer(size.value)
        result = getter(buffer, ctypes.byref(size), False, family, table_class, 0)
        if result != 0:
            raise EffectBoundaryHold("socket_census_ambiguous")
        count = struct.unpack_from("<I", buffer.raw)[0]
        if count > 1_000_000:
            raise EffectBoundaryHold("socket_census_ambiguous")
        rows: list[tuple[int, str]] = []
        offset = 4
        if family == AF_INET and protocol == "tcp":
            row_size = 24
            for _ in range(count):
                state, local_addr, local_port, remote_addr, remote_port, pid = struct.unpack_from("<6I", buffer.raw, offset)
                rows.append((pid, f"tcp4:{local_addr:08x}:{self._port(local_port)}:{state}"))
                offset += row_size
        elif family == AF_INET and protocol == "udp":
            row_size = 12
            for _ in range(count):
                local_addr, local_port, pid = struct.unpack_from("<3I", buffer.raw, offset)
                rows.append((pid, f"udp4:{local_addr:08x}:{self._port(local_port)}"))
                offset += row_size
        elif family == AF_INET6 and protocol == "tcp":
            row_size = 56
            for _ in range(count):
                local = buffer.raw[offset : offset + 16].hex()
                local_port = struct.unpack_from("<I", buffer.raw, offset + 20)[0]
                state, pid = struct.unpack_from("<II", buffer.raw, offset + 48)
                rows.append((pid, f"tcp6:{local}:{self._port(local_port)}:{state}"))
                offset += row_size
        else:
            row_size = 28
            for _ in range(count):
                local = buffer.raw[offset : offset + 16].hex()
                local_port, pid = struct.unpack_from("<II", buffer.raw, offset + 20)
                rows.append((pid, f"udp6:{local}:{self._port(local_port)}"))
                offset += row_size
        if offset > len(buffer):
            raise EffectBoundaryHold("socket_census_ambiguous")
        return tuple(rows)

    def query_sockets(self, pids: tuple[int, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        wanted = set(pids)
        try:
            tcp_rows = self._socket_table("tcp", AF_INET) + self._socket_table("tcp", AF_INET6)
            udp_rows = self._socket_table("udp", AF_INET) + self._socket_table("udp", AF_INET6)
        except (OSError, ValueError, struct.error) as exc:
            raise EffectBoundaryHold("socket_census_ambiguous") from exc
        tcp = tuple(sorted(value for pid, value in tcp_rows if pid in wanted))
        udp = tuple(sorted(value for pid, value in udp_rows if pid in wanted))
        return tcp, udp

    def _sid_pointer(self, sid_text: str) -> ctypes.c_void_p:
        pointer = ctypes.c_void_p()
        convert = self.advapi32.ConvertStringSidToSidW
        convert.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
        convert.restype = wintypes.BOOL
        if not convert(sid_text, ctypes.byref(pointer)):
            raise self._win_error("sid_parse_failed")
        return pointer

    def is_loopback_exempt(self, sid: str) -> bool:
        count = wintypes.DWORD()
        entries = ctypes.POINTER(SID_AND_ATTRIBUTES)()
        get_config = self.firewallapi.NetworkIsolationGetAppContainerConfig
        get_config.argtypes = [ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(ctypes.POINTER(SID_AND_ATTRIBUTES))]
        get_config.restype = wintypes.DWORD
        candidate = self._sid_pointer(sid)
        try:
            result = get_config(ctypes.byref(count), ctypes.byref(entries))
            if result != 0:
                raise EffectBoundaryHold("loopback_census_ambiguous")
            if count.value > 100_000:
                raise EffectBoundaryHold("loopback_census_ambiguous")
            return any(
                bool(self.advapi32.EqualSid(candidate, entries[index].Sid))
                for index in range(count.value)
            )
        finally:
            self.kernel32.LocalFree(candidate)
            if entries:
                heap = self.kernel32.GetProcessHeap()
                for index in range(count.value):
                    if entries[index].Sid:
                        self.kernel32.HeapFree(heap, 0, entries[index].Sid)
                self.kernel32.HeapFree(heap, 0, entries)

    def current_identity(self) -> WorkerIdentity:
        process = self.kernel32.GetCurrentProcess()
        token = wintypes.HANDLE()
        if not self.advapi32.OpenProcessToken(process, TOKEN_QUERY, ctypes.byref(token)):
            raise self._win_error("token_open_failed")
        try:
            is_container = wintypes.DWORD()
            returned = wintypes.DWORD()
            if not self.advapi32.GetTokenInformation(
                token,
                TOKEN_IS_APP_CONTAINER,
                ctypes.byref(is_container),
                ctypes.sizeof(is_container),
                ctypes.byref(returned),
            ):
                raise self._win_error("token_query_failed")
            needed = wintypes.DWORD()
            self.advapi32.GetTokenInformation(
                token,
                TOKEN_APP_CONTAINER_SID,
                None,
                0,
                ctypes.byref(needed),
            )
            if ctypes.get_last_error() != ERROR_INSUFFICIENT_BUFFER or not needed.value:
                raise self._win_error("token_sid_size_failed")
            buffer = ctypes.create_string_buffer(needed.value)
            if not self.advapi32.GetTokenInformation(
                token,
                TOKEN_APP_CONTAINER_SID,
                buffer,
                needed,
                ctypes.byref(needed),
            ):
                raise self._win_error("token_sid_query_failed")
            info = ctypes.cast(buffer, ctypes.POINTER(TOKEN_APPCONTAINER_INFORMATION)).contents
            if not info.TokenAppContainer:
                sid_text = ""
                exempt = False
            else:
                sid_text = self._sid_string(info.TokenAppContainer)
                exempt = self.is_loopback_exempt(sid_text)
            pid = int(self.kernel32.GetCurrentProcessId())
            tcp, udp = self.query_sockets((pid,))
            return WorkerIdentity(
                pid=pid,
                appcontainer_sid=sid_text,
                is_appcontainer=bool(is_container.value),
                loopback_exempt=exempt,
                job_pids=(pid,),
                tcp_sockets=tcp,
                udp_sockets=udp,
            )
        finally:
            self.kernel32.CloseHandle(token)

    def probe_denials(self) -> tuple[int, int, int]:
        import socket
        import subprocess

        mutation_code = 0
        try:
            with open(os.path.abspath(sys.argv[0]), "ab"):
                pass
        except OSError as exc:
            mutation_code = int(getattr(exc, "winerror", 0) or 0)

        network_code = 0
        probe_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            network_code = int(probe_socket.connect_ex(("127.0.0.1", 9)))
        finally:
            probe_socket.close()

        child_code = 0
        try:
            subprocess.run(
                [sys.executable, "-I", "-S", "-c", "pass"],
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except OSError as exc:
            child_code = int(getattr(exc, "winerror", 0) or 0)
        except subprocess.TimeoutExpired:
            child_code = 0
        return mutation_code, network_code, child_code

    def open_current_thread(self) -> int:
        handle = self.kernel32.OpenThread(
            THREAD_TERMINATE, False, self.kernel32.GetCurrentThreadId()
        )
        if not handle:
            raise self._win_error("broker_thread_open_failed")
        return int(handle)

    def cancel_synchronous_io(self, thread_handle: int) -> None:
        if not self.kernel32.CancelSynchronousIo(thread_handle):
            error = ctypes.get_last_error()
            if error != ERROR_NOT_FOUND:
                raise self._win_error("broker_io_cancel_failed")

    def _process_appcontainer_sid(self, process_handle: int) -> str:
        token = wintypes.HANDLE()
        if not self.advapi32.OpenProcessToken(process_handle, TOKEN_QUERY, ctypes.byref(token)):
            raise self._win_error("worker_token_open_failed")
        try:
            is_container = wintypes.DWORD()
            returned = wintypes.DWORD()
            if not self.advapi32.GetTokenInformation(
                token, TOKEN_IS_APP_CONTAINER, ctypes.byref(is_container),
                ctypes.sizeof(is_container), ctypes.byref(returned),
            ):
                raise self._win_error("worker_token_query_failed")
            if is_container.value != 1:
                raise EffectBoundaryHold("worker_not_appcontainer")
            needed = wintypes.DWORD()
            self.advapi32.GetTokenInformation(
                token, TOKEN_APP_CONTAINER_SID, None, 0, ctypes.byref(needed),
            )
            if ctypes.get_last_error() != ERROR_INSUFFICIENT_BUFFER or not needed.value:
                raise self._win_error("worker_token_sid_size_failed")
            buffer = ctypes.create_string_buffer(needed.value)
            if not self.advapi32.GetTokenInformation(
                token, TOKEN_APP_CONTAINER_SID, buffer, needed, ctypes.byref(needed),
            ):
                raise self._win_error("worker_token_sid_query_failed")
            info = ctypes.cast(buffer, ctypes.POINTER(TOKEN_APPCONTAINER_INFORMATION)).contents
            if not info.TokenAppContainer:
                raise EffectBoundaryHold("worker_sid_mismatch")
            return self._sid_string(info.TokenAppContainer)
        finally:
            self.kernel32.CloseHandle(token)

    def _process_capability_count(self, process_handle: int) -> int:
        token = wintypes.HANDLE()
        if not self.advapi32.OpenProcessToken(process_handle, TOKEN_QUERY, ctypes.byref(token)):
            raise self._win_error("process_token_open_failed")
        try:
            required = wintypes.DWORD()
            self.advapi32.GetTokenInformation(token, TOKEN_CAPABILITIES, None, 0, ctypes.byref(required))
            if not required.value:
                raise self._win_error("process_capabilities_query_failed")
            buffer = ctypes.create_string_buffer(required.value)
            if not self.advapi32.GetTokenInformation(token, TOKEN_CAPABILITIES, buffer, required, ctypes.byref(required)):
                raise self._win_error("process_capabilities_query_failed")
            return int(ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD)).contents.value)
        finally:
            self.kernel32.CloseHandle(token)

    def create_probe_pipes(self) -> tuple[int, int, int, int]:
        parent_read = wintypes.HANDLE()
        child_write = wintypes.HANDLE()
        child_read = wintypes.HANDLE()
        parent_write = wintypes.HANDLE()
        if not self.kernel32.CreatePipe(ctypes.byref(parent_read), ctypes.byref(child_write), None, 0):
            raise self._win_error("pipe_create_failed")
        try:
            if not self.kernel32.CreatePipe(ctypes.byref(child_read), ctypes.byref(parent_write), None, 0):
                raise self._win_error("pipe_create_failed")
            if not self.kernel32.SetHandleInformation(parent_read, HANDLE_FLAG_INHERIT, 0):
                raise self._win_error("pipe_inherit_failed")
            if not self.kernel32.SetHandleInformation(parent_write, HANDLE_FLAG_INHERIT, 0):
                raise self._win_error("pipe_inherit_failed")
            return (
                int(parent_read.value),
                int(parent_write.value),
                int(child_read.value),
                int(child_write.value),
            )
        except BaseException:
            self.kernel32.CloseHandle(parent_read)
            if child_write:
                self.kernel32.CloseHandle(child_write)
            if child_read:
                self.kernel32.CloseHandle(child_read)
            if parent_write:
                self.kernel32.CloseHandle(parent_write)
            raise

    def read_probe_frame(self, handle: int, timeout_ms: int) -> dict[str, Any]:
        deadline = time.monotonic() + (timeout_ms / 1000)
        while True:
            header = ctypes.create_string_buffer(4)
            peeked = wintypes.DWORD()
            available = wintypes.DWORD()
            if not self.kernel32.PeekNamedPipe(
                handle, header, 4, ctypes.byref(peeked), ctypes.byref(available), None,
            ):
                raise self._win_error("worker_probe_read_failed")
            if peeked.value == 4:
                size = struct.unpack(">I", header.raw)[0]
                if size > MAX_FRAME_BYTES:
                    raise EffectBoundaryHold("frame_too_large")
                total = size + 4
                if available.value >= total:
                    frame = ctypes.create_string_buffer(total)
                    read = wintypes.DWORD()
                    if not self.kernel32.ReadFile(
                        handle, frame, total, ctypes.byref(read), None,
                    ) or read.value != total:
                        raise self._win_error("worker_probe_read_failed")
                    return decode_frame(frame.raw[:total])
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise EffectBoundaryHold("worker_attestation_timeout")
            time.sleep(min(0.01, remaining))

    def wait_process(self, process_handle: int, timeout_ms: int) -> int:
        result = self.kernel32.WaitForSingleObject(process_handle, timeout_ms)
        if result == WAIT_TIMEOUT:
            raise EffectBoundaryHold("worker_attestation_timeout")
        if result != WAIT_OBJECT_0:
            raise self._win_error("worker_wait_failed")
        exit_code = wintypes.DWORD()
        if not self.kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code)):
            raise self._win_error("worker_exit_query_failed")
        return int(exit_code.value)

    def close_handle(self, handle: int) -> None:
        if handle and not self.kernel32.CloseHandle(handle):
            raise self._win_error("handle_close_failed")

    def terminate_job(self, handle: int) -> None:
        if handle and not self.kernel32.TerminateJobObject(handle, 1):
            error = ctypes.get_last_error()
            if error != ERROR_NOT_FOUND:
                raise self._win_error("job_terminate_failed")


def _validate_probe_denials(
    mutation_code: int, network_code: int, child_code: int,
) -> None:
    if (mutation_code, network_code, child_code) != (5, 10013, 1816):
        raise EffectBoundaryHold("worker_denial_proof_failed")


def run_probe_worker(
    reader: Any,
    writer: Any,
    *,
    backend: _Backend | None = None,
) -> None:
    """Emit actual worker OS identity, then require the broker's exact release."""

    worker_backend = backend if backend is not None else _CtypesBackend()
    try:
        observed = worker_backend.current_identity()
        if not isinstance(observed, WorkerIdentity):
            raise EffectBoundaryHold("worker_identity_ambiguous")
        _validate_probe_denials(*worker_backend.probe_denials())
        write_frame(writer, observed.to_frame())
        if read_frame(reader) != {"type": "probe_release"}:
            raise EffectBoundaryHold("probe_release_malformed")
    except EffectBoundaryHold:
        raise
    except BaseException:
        raise EffectBoundaryHold("worker_probe_failed") from None


class WindowsEffectBoundary:
    """Own one root/campaign mutex, one job, and at most one worker."""

    def __init__(
        self,
        canonical_root: str,
        campaign_id: str,
        *,
        bundle_binding: _bundle.BundleBinding,
        bundle_probe: _bundle.BundleProbe,
        bundle_validator: Any = _bundle,
        backend: _Backend | None = None,
    ) -> None:
        self._mutex_name = _mutex_name(canonical_root, campaign_id)
        self._backend: _Backend = backend if backend is not None else _CtypesBackend()
        self._bundle_binding = bundle_binding
        self._bundle_probe = bundle_probe
        self._bundle_validator = bundle_validator
        self._mutex_handle: int | None = None
        self._job_handle: int | None = None
        self._worker_pid: int | None = None
        self._worker_sid: str | None = None
        self._process_handle: int | None = None
        self._closed = False

    @contextlib.contextmanager
    def acquire(self) -> Iterator["WindowsEffectBoundary"]:
        if self._closed or self._mutex_handle is not None:
            raise EffectBoundaryHold("boundary_state_invalid")
        mutex = self._backend.acquire_mutex(self._mutex_name)
        self._mutex_handle = mutex
        try:
            try:
                self._job_handle = self._backend.create_job()
            except BaseException:
                self._backend.close_handle(mutex)
                self._mutex_handle = None
                raise
            yield self
        finally:
            self.close()

    def _require_owned(self) -> int:
        if self._closed or self._mutex_handle is None or self._job_handle is None:
            raise EffectBoundaryHold("boundary_not_owned")
        return self._job_handle

    def create_worker_pipes(self) -> tuple[int, int, int, int]:
        """Allocate broker read/write and exact inheritable worker read/write handles."""

        self._require_owned()
        try:
            return self._backend.create_probe_pipes()
        except EffectBoundaryHold:
            raise
        except BaseException:
            raise EffectBoundaryHold("worker_pipe_create_failed") from None

    def close_pipe_handle(self, handle: int) -> None:
        """Close one raw pipe handle that has not transferred into a Python stream."""

        if isinstance(handle, bool) or not isinstance(handle, int) or handle <= 0:
            raise EffectBoundaryHold("pipe_handle_invalid")
        self._backend.close_handle(handle)

    def read_worker_frame(self, handle: int, timeout_ms: int) -> dict[str, Any]:
        """Read one bounded frame; ambiguity contains the worker before returning."""

        job = self._require_owned()
        if self._worker_pid is None:
            raise EffectBoundaryHold("worker_not_launched")
        try:
            return self._backend.read_probe_frame(handle, timeout_ms)
        except EffectBoundaryHold:
            self._backend.terminate_job(job)
            if self._process_handle is not None:
                self._backend.close_handle(self._process_handle)
                self._process_handle = None
            raise
        except BaseException:
            self._backend.terminate_job(job)
            if self._process_handle is not None:
                self._backend.close_handle(self._process_handle)
                self._process_handle = None
            raise EffectBoundaryHold("worker_frame_read_failed") from None

    @contextlib.contextmanager
    def broker_session_deadline(self, timeout_ms: int) -> Iterator[None]:
        """Bound all synchronous broker pipe I/O to one fail-closed deadline."""

        job = self._require_owned()
        if (
            isinstance(timeout_ms, bool)
            or not isinstance(timeout_ms, int)
            or not 1 <= timeout_ms <= 15 * 60 * 1000
        ):
            raise EffectBoundaryHold("broker_session_timeout_invalid")
        thread_handle = self._backend.open_current_thread()
        done = threading.Event()
        expired = threading.Event()
        watchdog_errors: list[BaseException] = []

        def watchdog() -> None:
            if done.wait(timeout_ms / 1000):
                return
            expired.set()
            try:
                self._backend.terminate_job(job)
            except BaseException as exc:
                watchdog_errors.append(exc)
            try:
                self._backend.cancel_synchronous_io(thread_handle)
            except BaseException as exc:
                watchdog_errors.append(exc)

        monitor = threading.Thread(
            target=watchdog,
            name=f"p6-b0-session-{threading.get_ident()}",
            daemon=False,
        )
        monitor.start()
        body_error: BaseException | None = None
        try:
            yield
        except BaseException as exc:
            body_error = exc
        finally:
            done.set()
            monitor.join()
            try:
                self._backend.close_handle(thread_handle)
            except BaseException as exc:
                watchdog_errors.append(exc)
            if expired.is_set() and self._process_handle is not None:
                try:
                    self._backend.close_handle(self._process_handle)
                except BaseException as exc:
                    watchdog_errors.append(exc)
                self._process_handle = None
        if expired.is_set():
            raise EffectBoundaryHold("broker_session_deadline") from None
        if watchdog_errors:
            raise EffectBoundaryHold("broker_session_cleanup_failed") from None
        if body_error is not None:
            raise body_error

    def launch_worker(
        self,
        pipe_handles: tuple[int, ...],
        *,
        mode: str = "probe",
    ) -> WorkerIdentity:
        job = self._require_owned()
        if self._worker_pid is not None:
            raise EffectBoundaryHold("worker_already_launched")
        handles = _validate_launch_handles(pipe_handles)
        process: int | None = None
        thread: int | None = None
        try:
            expected = self._bundle_validator.validate_worker_bundle(
                self._bundle_binding, self._bundle_probe
            )
            interpreter, entrypoint = expected.interpreter, expected.entrypoint
            if not isinstance(interpreter, Path) or not interpreter.is_absolute():
                raise EffectBoundaryHold("bundle_interpreter_invalid")
            if not isinstance(entrypoint, Path) or not entrypoint.is_absolute():
                raise EffectBoundaryHold("bundle_entrypoint_invalid")
            if mode not in {"probe", "sciencebase"}:
                raise EffectBoundaryHold("worker_mode_invalid")
            worker_switch = (
                "--worker-probe" if mode == "probe" else "--worker-sciencebase"
            )
            arguments = (
                "-I", "-S", str(entrypoint),
                worker_switch, str(handles[0]), str(handles[1]),
            )
            pid, sid, capability_count, process, thread = self._backend.launch_appcontainer_suspended(
                str(interpreter), arguments, handles, job,
                profile_moniker=self._bundle_binding.profile_moniker,
                expected_package_sid=self._bundle_binding.package_sid,
                creation_flags=CREATE_SUSPENDED,
            )
            if (
                isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0
                or not isinstance(sid, str) or not sid
                or isinstance(process, bool) or not isinstance(process, int) or process <= 0
                or isinstance(thread, bool) or not isinstance(thread, int) or thread <= 0
            ):
                raise EffectBoundaryHold("worker_identity_ambiguous")
            if sid != self._bundle_binding.package_sid:
                raise EffectBoundaryHold("worker_sid_mismatch")
            if capability_count != 0:
                raise EffectBoundaryHold("worker_capabilities_present")
            self._worker_pid, self._worker_sid = pid, sid
            rebound = self._bundle_validator.revalidate_worker_bundle(
                self._bundle_binding, self._bundle_probe, expected
            )
            if rebound != expected:
                raise EffectBoundaryHold("bundle_rebind_mismatch")
            self.census()
            try:
                previous = self._backend.resume_thread(thread)
            except BaseException as exc:
                raise EffectBoundaryHold("worker_resume_failed") from exc
            if previous != 1:
                raise EffectBoundaryHold("worker_suspend_count_invalid")
            self._backend.close_handle(thread)
            thread = None
            observed = self.census()
            self._process_handle = process
            process = None
            return observed
        except _bundle.BundleHold as exc:
            self._backend.terminate_job(job)
            raise EffectBoundaryHold(exc.code) from exc
        except EffectBoundaryHold:
            self._backend.terminate_job(job)
            raise
        except BaseException as exc:
            self._backend.terminate_job(job)
            raise EffectBoundaryHold("bundle_validation_ambiguous") from exc
        finally:
            if thread is not None:
                self._backend.close_handle(thread)
            if process is not None:
                self._backend.close_handle(process)

    def _validate_observation(self, observed: WorkerIdentity) -> WorkerIdentity:
        if self._worker_pid is None or self._worker_sid is None:
            raise EffectBoundaryHold("worker_not_launched")
        if not observed.is_appcontainer:
            raise EffectBoundaryHold("worker_not_appcontainer")
        if observed.appcontainer_sid != self._worker_sid:
            raise EffectBoundaryHold("worker_sid_mismatch")
        if observed.loopback_exempt:
            raise EffectBoundaryHold("worker_loopback_exempt")
        if observed.pid != self._worker_pid:
            raise EffectBoundaryHold("worker_pid_mismatch")
        if not observed.job_pids:
            raise EffectBoundaryHold("job_empty")
        if observed.job_pids != (self._worker_pid,):
            raise EffectBoundaryHold("job_descendant_present")
        if observed.tcp_sockets or observed.udp_sockets:
            raise EffectBoundaryHold("worker_socket_present")
        return observed

    def attest(self, identity: WorkerIdentity) -> WorkerIdentity:
        self._require_owned()
        worker = self._validate_observation(identity)
        broker = self.census()
        if worker != broker:
            raise EffectBoundaryHold("attestation_census_mismatch")
        return worker

    def census(self) -> WorkerIdentity:
        job = self._require_owned()
        if self._worker_pid is None or self._worker_sid is None:
            raise EffectBoundaryHold("worker_not_launched")
        pids = self._backend.query_job_pids(job)
        tcp, udp = self._backend.query_sockets(pids)
        exempt = self._backend.is_loopback_exempt(self._worker_sid)
        observed = WorkerIdentity(
            pid=self._worker_pid,
            appcontainer_sid=self._worker_sid,
            is_appcontainer=True,
            loopback_exempt=exempt,
            job_pids=pids,
            tcp_sockets=tcp,
            udp_sockets=udp,
        )
        return self._validate_observation(observed)

    def wait_worker(self, timeout_ms: int) -> int:
        """Require one exact zero worker exit and release its process handle."""

        job = self._require_owned()
        if (
            isinstance(timeout_ms, bool)
            or not isinstance(timeout_ms, int)
            or not 1 <= timeout_ms <= 120_000
        ):
            raise EffectBoundaryHold("worker_wait_timeout_invalid")
        process = self._process_handle
        if process is None:
            raise EffectBoundaryHold("worker_process_handle_missing")
        try:
            try:
                exit_code = self._backend.wait_process(process, timeout_ms)
            except BaseException:
                self._backend.terminate_job(job)
                raise EffectBoundaryHold("worker_wait_failed") from None
            if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code != 0:
                self._backend.terminate_job(job)
                raise EffectBoundaryHold("worker_exit_nonzero")
            return exit_code
        finally:
            self._backend.close_handle(process)
            self._process_handle = None

    def prove_worker(self) -> WorkerIdentity:
        self._require_owned()
        if not isinstance(self._backend, _CtypesBackend):
            raise EffectBoundaryHold("real_backend_required")
        parent_read, parent_write, child_read, child_write = self._backend.create_probe_pipes()
        try:
            self.launch_worker((child_read, child_write))
            self._backend.close_handle(child_read)
            child_read = 0
            self._backend.close_handle(child_write)
            child_write = 0
            worker = WorkerIdentity.from_frame(
                self._backend.read_probe_frame(parent_read, 15_000)
            )
            attested = self.attest(worker)
            import msvcrt

            descriptor = msvcrt.open_osfhandle(parent_write, os.O_WRONLY | os.O_BINARY)
            parent_write = 0
            with os.fdopen(descriptor, "wb", closefd=True) as writer:
                write_frame(writer, {"type": "probe_release"})
            if self._process_handle is None:
                raise EffectBoundaryHold("worker_process_handle_missing")
            exit_code = self._backend.wait_process(self._process_handle, 15_000)
            if exit_code != 0:
                digest = hashlib.sha256(f"exit:{exit_code:08x}".encode("ascii")).hexdigest()
                raise EffectBoundaryHold("python_appcontainer_inaccessible", fact_digest=digest)
            return attested
        except EffectBoundaryHold:
            if self._job_handle is not None:
                self._backend.terminate_job(self._job_handle)
            if self._process_handle is not None:
                self._backend.close_handle(self._process_handle)
                self._process_handle = None
            raise
        except (OSError, ValueError) as exc:
            if self._job_handle is not None:
                self._backend.terminate_job(self._job_handle)
            if self._process_handle is not None:
                self._backend.close_handle(self._process_handle)
                self._process_handle = None
            raise EffectBoundaryHold("worker_probe_failed") from exc
        finally:
            for handle in (parent_read, parent_write, child_read, child_write):
                if handle:
                    self._backend.close_handle(handle)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        errors: list[BaseException] = []
        if self._job_handle is not None:
            try:
                self._backend.terminate_job(self._job_handle)
            except BaseException as exc:
                errors.append(exc)
            try:
                self._backend.close_handle(self._job_handle)
            except BaseException as exc:
                errors.append(exc)
            self._job_handle = None
        if self._process_handle is not None:
            try:
                self._backend.close_handle(self._process_handle)
            except BaseException as exc:
                errors.append(exc)
            self._process_handle = None
        if self._mutex_handle is not None:
            try:
                self._backend.close_handle(self._mutex_handle)
            except BaseException as exc:
                errors.append(exc)
            self._mutex_handle = None
        if errors:
            raise EffectBoundaryHold("boundary_close_failed")
