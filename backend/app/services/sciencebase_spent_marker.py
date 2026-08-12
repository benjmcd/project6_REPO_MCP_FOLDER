"""Fail-closed Windows store for one-use ScienceBase GO markers."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Protocol
from uuid import UUID


_MARKER_FIELDS = frozenset({"schema", "go_id", "envelope_digest"})
_MARKER_SCHEMA = "project6.sciencebase_live_go_spent.v1"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


class SpentMarkerHold(RuntimeError):
    """The marker's state cannot safely establish a one-use claim."""


@dataclass(frozen=True)
class MarkerIdentity:
    volume: object
    file_id: object
    link_count: int
    reparse: bool
    directory: bool


class MarkerBackend(Protocol):
    def open_directory(self, path: Path) -> Any: ...
    def open_file(self, path: Path) -> tuple[Any, bool]: ...
    def identity(self, handle: Any) -> MarkerIdentity: ...
    def secure(self, handle: Any) -> tuple[bool, bool, bool]: ...
    def lock(self, handle: Any) -> None: ...
    def unlock(self, handle: Any) -> None: ...
    def read(self, handle: Any, limit: int) -> bytes: ...
    def append(self, handle: Any, value: bytes) -> None: ...
    def flush(self, handle: Any) -> None: ...
    def close(self, handle: Any) -> None: ...


def _canonical(document: object) -> bytes:
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _parse_line(raw: bytes) -> dict[str, object]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    document = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
    if (
        not isinstance(document, dict)
        or set(document) != _MARKER_FIELDS
        or document.get("schema") != _MARKER_SCHEMA
        or _canonical(document) != raw
    ):
        raise ValueError("noncanonical marker")
    try:
        if str(UUID(str(document["go_id"]))) != document["go_id"]:
            raise ValueError("noncanonical UUID")
    except (ValueError, TypeError, AttributeError):
        raise ValueError("invalid UUID") from None
    if not isinstance(document["envelope_digest"], str) or not _DIGEST.fullmatch(
        document["envelope_digest"]
    ):
        raise ValueError("invalid digest")
    return document


def _valid_identity(identity: MarkerIdentity, *, directory: bool) -> bool:
    return (
        identity.volume not in (None, "")
        and identity.file_id not in (None, "")
        and identity.directory is directory
        and not identity.reparse
        and identity.link_count == 1
    )


class SpentMarkerStore:
    """Atomically claim a canonical marker while its exact file handle is locked."""

    def __init__(
        self,
        path: Path,
        *,
        max_bytes: int,
        backend: MarkerBackend | None = None,
    ) -> None:
        self._path = Path(path)
        self._max_bytes = max_bytes
        self._backend = backend if backend is not None else WindowsMarkerBackend()

    def claim_exact(self, marker: bytes) -> str:
        try:
            proposed = _parse_line(marker)
        except (UnicodeError, json.JSONDecodeError, ValueError, TypeError):
            raise SpentMarkerHold("spent_marker_invalid") from None
        if not self._path.is_absolute() or self._max_bytes <= 0:
            raise SpentMarkerHold("spent_marker_binding_invalid")
        directory_handle: Any = None
        file_handle: Any = None
        locked = False
        try:
            directory_handle = self._backend.open_directory(self._path.parent)
            directory_identity = self._backend.identity(directory_handle)
            if not _valid_identity(directory_identity, directory=True):
                raise SpentMarkerHold("spent_marker_directory_invalid")
            if self._backend.secure(directory_handle) != (True, True, True):
                raise SpentMarkerHold("spent_marker_security_invalid")

            file_handle, _created = self._backend.open_file(self._path)
            file_identity = self._backend.identity(file_handle)
            if not _valid_identity(file_identity, directory=False):
                raise SpentMarkerHold("spent_marker_file_invalid")
            if self._backend.secure(file_handle) != (True, True, True):
                raise SpentMarkerHold("spent_marker_security_invalid")
            if file_identity.volume != directory_identity.volume:
                raise SpentMarkerHold("spent_marker_volume_changed")

            self._backend.lock(file_handle)
            locked = True
            if self._backend.identity(directory_handle) != directory_identity:
                raise SpentMarkerHold("spent_marker_directory_changed")
            if self._backend.identity(file_handle) != file_identity:
                raise SpentMarkerHold("spent_marker_file_changed")
            if self._backend.secure(directory_handle) != (True, True, True):
                raise SpentMarkerHold("spent_marker_security_changed")
            if self._backend.secure(file_handle) != (True, True, True):
                raise SpentMarkerHold("spent_marker_security_changed")
            existing = self._backend.read(file_handle, self._max_bytes)
            if len(existing) > self._max_bytes or (existing and not existing.endswith(b"\n")):
                raise SpentMarkerHold("spent_marker_malformed")
            for line in existing.splitlines():
                observed = _parse_line(line)
                if (
                    observed["go_id"] == proposed["go_id"]
                    or observed["envelope_digest"] == proposed["envelope_digest"]
                ):
                    return "EXISTS"
            appended = marker + b"\n"
            if len(existing) + len(appended) > self._max_bytes:
                raise SpentMarkerHold("spent_marker_too_large")
            self._backend.append(file_handle, appended)
            self._backend.flush(file_handle)
            if self._backend.identity(file_handle) != file_identity:
                raise SpentMarkerHold("spent_marker_file_changed")
            if self._backend.secure(directory_handle) != (True, True, True):
                raise SpentMarkerHold("spent_marker_security_changed")
            if self._backend.secure(file_handle) != (True, True, True):
                raise SpentMarkerHold("spent_marker_security_changed")
            observed = self._backend.read(file_handle, self._max_bytes)
            if len(observed) > self._max_bytes or not observed.endswith(appended):
                raise SpentMarkerHold("spent_marker_write_indeterminate")
            return "RECORDED"
        except SpentMarkerHold:
            raise
        except BaseException as exc:
            raise SpentMarkerHold("spent_marker_indeterminate") from exc
        finally:
            cleanup_error: BaseException | None = None
            if locked and file_handle is not None:
                try:
                    self._backend.unlock(file_handle)
                except BaseException as exc:
                    cleanup_error = exc
            if file_handle is not None:
                try:
                    self._backend.close(file_handle)
                except BaseException as exc:
                    cleanup_error = cleanup_error or exc
            if directory_handle is not None:
                try:
                    self._backend.close(directory_handle)
                except BaseException as exc:
                    cleanup_error = cleanup_error or exc
            if cleanup_error is not None:
                raise SpentMarkerHold("spent_marker_cleanup_indeterminate") from cleanup_error


class _ByHandleFileInformation(ctypes.Structure):
    _fields_ = [
        ("attributes", wintypes.DWORD),
        ("creation_low", wintypes.DWORD),
        ("creation_high", wintypes.DWORD),
        ("access_low", wintypes.DWORD),
        ("access_high", wintypes.DWORD),
        ("write_low", wintypes.DWORD),
        ("write_high", wintypes.DWORD),
        ("volume_serial", wintypes.DWORD),
        ("size_high", wintypes.DWORD),
        ("size_low", wintypes.DWORD),
        ("link_count", wintypes.DWORD),
        ("file_index_high", wintypes.DWORD),
        ("file_index_low", wintypes.DWORD),
    ]


class _SecurityAttributes(ctypes.Structure):
    _fields_ = [
        ("length", wintypes.DWORD),
        ("descriptor", ctypes.c_void_p),
        ("inherit", wintypes.BOOL),
    ]


class _Overlapped(ctypes.Structure):
    _fields_ = [
        ("internal", ctypes.c_void_p),
        ("internal_high", ctypes.c_void_p),
        ("offset", wintypes.DWORD),
        ("offset_high", wintypes.DWORD),
        ("event", wintypes.HANDLE),
    ]


class _Acl(ctypes.Structure):
    _fields_ = [
        ("revision", wintypes.BYTE),
        ("sbz1", wintypes.BYTE),
        ("size", wintypes.WORD),
        ("ace_count", wintypes.WORD),
        ("sbz2", wintypes.WORD),
    ]


class _AceHeader(ctypes.Structure):
    _fields_ = [
        ("ace_type", wintypes.BYTE),
        ("ace_flags", wintypes.BYTE),
        ("ace_size", wintypes.WORD),
    ]


@dataclass(frozen=True)
class _DirectoryHandles:
    primary: int
    pinned: tuple[int, ...]


class WindowsMarkerBackend:
    """Stdlib-only bindings to the required Windows handle primitives."""

    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ_WRITE = 0x00000003
    CREATE_NEW = 1
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_DIRECTORY = 0x10
    FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    ERROR_ALREADY_EXISTS = 183
    ERROR_FILE_EXISTS = 80
    LOCKFILE_EXCLUSIVE_LOCK = 0x2
    OWNER_SECURITY_INFORMATION = 0x1
    DACL_SECURITY_INFORMATION = 0x4
    SE_FILE_OBJECT = 1
    SE_DACL_PROTECTED = 0x1000
    INHERITED_ACE = 0x10
    ACCESS_ALLOWED_ACE_TYPE = 0
    TOKEN_QUERY = 0x8
    TOKEN_USER = 1
    SDDL_REVISION_1 = 1
    SECURITY_DESCRIPTOR_REVISION = 1
    FILE_ALL_ACCESS = 0x001F01FF
    INVALID_HANDLE = ctypes.c_void_p(-1).value

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise SpentMarkerHold("windows_required")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        self._configure_functions()
        self._overlapped: dict[int, _Overlapped] = {}
        self._owner_sid = self._token_user_sid()
        self._system_sid = self._sid_from_string("S-1-5-18")
        owner_text = self._sid_to_string(self._owner_sid)
        self._sddl = f"O:{owner_text}D:P(A;;FA;;;{owner_text})(A;;FA;;;SY)"

    def _configure_functions(self) -> None:
        void_p = ctypes.c_void_p
        dword_p = ctypes.POINTER(wintypes.DWORD)
        self.kernel32.GetCurrentProcess.argtypes = []
        self.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.LocalFree.argtypes = [void_p]
        self.kernel32.LocalFree.restype = void_p
        self.kernel32.CreateDirectoryW.argtypes = [wintypes.LPCWSTR, void_p]
        self.kernel32.CreateDirectoryW.restype = wintypes.BOOL
        self.kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, void_p,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE
        self.kernel32.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, void_p]
        self.kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
        self.kernel32.LockFileEx.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            wintypes.DWORD, wintypes.DWORD, void_p,
        ]
        self.kernel32.LockFileEx.restype = wintypes.BOOL
        self.kernel32.UnlockFileEx.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            wintypes.DWORD, void_p,
        ]
        self.kernel32.UnlockFileEx.restype = wintypes.BOOL
        self.kernel32.SetFilePointerEx.argtypes = [
            wintypes.HANDLE, ctypes.c_longlong,
            ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD,
        ]
        self.kernel32.SetFilePointerEx.restype = wintypes.BOOL
        self.kernel32.ReadFile.argtypes = [
            wintypes.HANDLE, void_p, wintypes.DWORD, dword_p, void_p,
        ]
        self.kernel32.ReadFile.restype = wintypes.BOOL
        self.kernel32.WriteFile.argtypes = [
            wintypes.HANDLE, void_p, wintypes.DWORD, dword_p, void_p,
        ]
        self.kernel32.WriteFile.restype = wintypes.BOOL
        self.kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
        self.kernel32.FlushFileBuffers.restype = wintypes.BOOL
        self.advapi32.OpenProcessToken.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE),
        ]
        self.advapi32.OpenProcessToken.restype = wintypes.BOOL
        self.advapi32.GetTokenInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, void_p, wintypes.DWORD, dword_p,
        ]
        self.advapi32.GetTokenInformation.restype = wintypes.BOOL
        self.advapi32.GetLengthSid.argtypes = [void_p]
        self.advapi32.GetLengthSid.restype = wintypes.DWORD
        self.advapi32.CopySid.argtypes = [wintypes.DWORD, void_p, void_p]
        self.advapi32.CopySid.restype = wintypes.BOOL
        self.advapi32.EqualSid.argtypes = [void_p, void_p]
        self.advapi32.EqualSid.restype = wintypes.BOOL
        self.advapi32.ConvertStringSidToSidW.argtypes = [
            wintypes.LPCWSTR, ctypes.POINTER(void_p),
        ]
        self.advapi32.ConvertStringSidToSidW.restype = wintypes.BOOL
        self.advapi32.ConvertSidToStringSidW.argtypes = [void_p, ctypes.POINTER(wintypes.LPWSTR)]
        self.advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
        self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(void_p), dword_p,
        ]
        self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
        self.advapi32.GetSecurityInfo.argtypes = [
            wintypes.HANDLE, ctypes.c_int, wintypes.DWORD,
            ctypes.POINTER(void_p), ctypes.POINTER(void_p), ctypes.POINTER(void_p),
            ctypes.POINTER(void_p), ctypes.POINTER(void_p),
        ]
        self.advapi32.GetSecurityInfo.restype = wintypes.DWORD
        self.advapi32.GetSecurityDescriptorControl.argtypes = [
            void_p, ctypes.POINTER(wintypes.WORD), dword_p,
        ]
        self.advapi32.GetSecurityDescriptorControl.restype = wintypes.BOOL
        self.advapi32.GetAce.argtypes = [void_p, wintypes.DWORD, ctypes.POINTER(void_p)]
        self.advapi32.GetAce.restype = wintypes.BOOL

    def _raise(self, operation: str) -> None:
        raise OSError(ctypes.get_last_error(), operation)

    def _token_user_sid(self) -> ctypes.Array[Any]:
        token = wintypes.HANDLE()
        if not self.advapi32.OpenProcessToken(
            self.kernel32.GetCurrentProcess(), self.TOKEN_QUERY, ctypes.byref(token)
        ):
            self._raise("OpenProcessToken")
        try:
            size = wintypes.DWORD()
            self.advapi32.GetTokenInformation(token, self.TOKEN_USER, None, 0, ctypes.byref(size))
            buffer = ctypes.create_string_buffer(size.value)
            if not self.advapi32.GetTokenInformation(
                token, self.TOKEN_USER, buffer, size, ctypes.byref(size)
            ):
                self._raise("GetTokenInformation")
            sid_pointer = ctypes.c_void_p.from_buffer(buffer).value
            length = self.advapi32.GetLengthSid(sid_pointer)
            sid = ctypes.create_string_buffer(length)
            if not self.advapi32.CopySid(length, sid, sid_pointer):
                self._raise("CopySid")
            return sid
        finally:
            self.kernel32.CloseHandle(token)

    def _sid_from_string(self, value: str) -> ctypes.Array[Any]:
        pointer = ctypes.c_void_p()
        if not self.advapi32.ConvertStringSidToSidW(value, ctypes.byref(pointer)):
            self._raise("ConvertStringSidToSidW")
        try:
            length = self.advapi32.GetLengthSid(pointer)
            sid = ctypes.create_string_buffer(length)
            if not self.advapi32.CopySid(length, sid, pointer):
                self._raise("CopySid")
            return sid
        finally:
            self.kernel32.LocalFree(pointer)

    def _sid_to_string(self, sid: Any) -> str:
        pointer = ctypes.c_wchar_p()
        if not self.advapi32.ConvertSidToStringSidW(sid, ctypes.byref(pointer)):
            self._raise("ConvertSidToStringSidW")
        try:
            return pointer.value
        finally:
            self.kernel32.LocalFree(pointer)

    def _security_attributes(self) -> tuple[_SecurityAttributes, ctypes.c_void_p]:
        descriptor = ctypes.c_void_p()
        if not self.advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            self._sddl, self.SDDL_REVISION_1, ctypes.byref(descriptor), None
        ):
            self._raise("ConvertStringSecurityDescriptorToSecurityDescriptorW")
        return _SecurityAttributes(ctypes.sizeof(_SecurityAttributes), descriptor, False), descriptor

    def _open_directory_handle(self, path: Path) -> int:
        handle = self.kernel32.CreateFileW(
            str(path), self.GENERIC_READ, self.FILE_SHARE_READ_WRITE, None,
            self.OPEN_EXISTING,
            self.FILE_FLAG_BACKUP_SEMANTICS | self.FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )
        if handle == self.INVALID_HANDLE:
            self._raise("CreateFileW(directory)")
        return handle

    def open_directory(self, path: Path) -> _DirectoryHandles:
        attributes, descriptor = self._security_attributes()
        try:
            missing: list[Path] = []
            cursor = path
            while not cursor.exists():
                missing.append(cursor)
                cursor = cursor.parent
            for directory in reversed(missing):
                if not self.kernel32.CreateDirectoryW(str(directory), ctypes.byref(attributes)):
                    if ctypes.get_last_error() != self.ERROR_ALREADY_EXISTS:
                        self._raise("CreateDirectoryW")
        finally:
            self.kernel32.LocalFree(descriptor)
        paths = [path]
        if path.parent.name.casefold() == "project6":
            paths.append(path.parent)
        handles: list[int] = []
        try:
            handles = [self._open_directory_handle(directory) for directory in paths]
            return _DirectoryHandles(handles[0], tuple(handles))
        except BaseException:
            for handle in handles:
                self.kernel32.CloseHandle(handle)
            raise

    def open_file(self, path: Path) -> tuple[int, bool]:
        attributes, descriptor = self._security_attributes()
        created = True
        try:
            handle = self.kernel32.CreateFileW(
                str(path), self.GENERIC_READ | self.GENERIC_WRITE,
                self.FILE_SHARE_READ_WRITE, ctypes.byref(attributes), self.CREATE_NEW,
                self.FILE_FLAG_OPEN_REPARSE_POINT, None,
            )
            if handle == self.INVALID_HANDLE and ctypes.get_last_error() in (
                self.ERROR_ALREADY_EXISTS, self.ERROR_FILE_EXISTS
            ):
                created = False
                handle = self.kernel32.CreateFileW(
                    str(path), self.GENERIC_READ | self.GENERIC_WRITE,
                    self.FILE_SHARE_READ_WRITE, None, self.OPEN_EXISTING,
                    self.FILE_FLAG_OPEN_REPARSE_POINT, None,
                )
            if handle == self.INVALID_HANDLE:
                self._raise("CreateFileW(marker)")
            return handle, created
        finally:
            self.kernel32.LocalFree(descriptor)

    def identity(self, handle: int | _DirectoryHandles) -> MarkerIdentity:
        if isinstance(handle, _DirectoryHandles):
            identities = tuple(self.identity(item) for item in handle.pinned)
            primary = identities[0]
            if any(
                identity.volume != primary.volume
                or not _valid_identity(identity, directory=True)
                for identity in identities
            ):
                raise OSError("managed marker ancestor invalid")
            return MarkerIdentity(
                primary.volume,
                tuple(identity.file_id for identity in identities),
                1,
                False,
                True,
            )
        info = _ByHandleFileInformation()
        if not self.kernel32.GetFileInformationByHandle(handle, ctypes.byref(info)):
            self._raise("GetFileInformationByHandle")
        return MarkerIdentity(
            info.volume_serial,
            (info.file_index_high << 32) | info.file_index_low,
            info.link_count,
            bool(info.attributes & self.FILE_ATTRIBUTE_REPARSE_POINT),
            bool(info.attributes & self.FILE_ATTRIBUTE_DIRECTORY),
        )

    def secure(self, handle: int | _DirectoryHandles) -> tuple[bool, bool, bool]:
        if isinstance(handle, _DirectoryHandles):
            results = tuple(self.secure(item) for item in handle.pinned)
            return tuple(all(result[index] for result in results) for index in range(3))  # type: ignore[return-value]
        owner = ctypes.c_void_p()
        dacl = ctypes.c_void_p()
        descriptor = ctypes.c_void_p()
        result = self.advapi32.GetSecurityInfo(
            handle, self.SE_FILE_OBJECT,
            self.OWNER_SECURITY_INFORMATION | self.DACL_SECURITY_INFORMATION,
            ctypes.byref(owner), None, ctypes.byref(dacl), None,
            ctypes.byref(descriptor),
        )
        if result:
            raise OSError(result, "GetSecurityInfo")
        try:
            control = wintypes.WORD()
            revision = wintypes.DWORD()
            if not self.advapi32.GetSecurityDescriptorControl(
                descriptor, ctypes.byref(control), ctypes.byref(revision)
            ):
                self._raise("GetSecurityDescriptorControl")
            owner_matches = bool(self.advapi32.EqualSid(owner, self._owner_sid))
            protected = bool(control.value & self.SE_DACL_PROTECTED)
            if not dacl:
                return owner_matches, protected, False
            acl = ctypes.cast(dacl, ctypes.POINTER(_Acl)).contents
            admitted_owner = False
            admitted_system = False
            only = acl.ace_count > 0
            for index in range(acl.ace_count):
                ace = ctypes.c_void_p()
                if not self.advapi32.GetAce(dacl, index, ctypes.byref(ace)):
                    self._raise("GetAce")
                header = ctypes.cast(ace, ctypes.POINTER(_AceHeader)).contents
                if header.ace_type != self.ACCESS_ALLOWED_ACE_TYPE or header.ace_flags & self.INHERITED_ACE:
                    only = False
                    continue
                sid = ctypes.c_void_p(ace.value + 8)
                mask = ctypes.c_uint32.from_address(ace.value + 4).value
                is_owner = bool(self.advapi32.EqualSid(sid, self._owner_sid))
                is_system = bool(self.advapi32.EqualSid(sid, self._system_sid))
                admitted_owner |= is_owner
                admitted_system |= is_system
                only &= (is_owner or is_system) and mask == self.FILE_ALL_ACCESS
            return owner_matches, protected, only and admitted_owner and admitted_system
        finally:
            self.kernel32.LocalFree(descriptor)

    def lock(self, handle: int) -> None:
        overlapped = _Overlapped()
        if not self.kernel32.LockFileEx(
            handle, self.LOCKFILE_EXCLUSIVE_LOCK, 0, 0xFFFFFFFF, 0xFFFFFFFF,
            ctypes.byref(overlapped),
        ):
            self._raise("LockFileEx")
        self._overlapped[handle] = overlapped

    def unlock(self, handle: int) -> None:
        overlapped = self._overlapped.pop(handle)
        if not self.kernel32.UnlockFileEx(
            handle, 0, 0xFFFFFFFF, 0xFFFFFFFF, ctypes.byref(overlapped)
        ):
            self._raise("UnlockFileEx")

    def _seek(self, handle: int, offset: int, method: int) -> None:
        position = ctypes.c_longlong()
        if not self.kernel32.SetFilePointerEx(handle, offset, ctypes.byref(position), method):
            self._raise("SetFilePointerEx")

    def read(self, handle: int, limit: int) -> bytes:
        self._seek(handle, 0, 0)
        buffer = ctypes.create_string_buffer(limit + 1)
        count = wintypes.DWORD()
        if not self.kernel32.ReadFile(handle, buffer, limit + 1, ctypes.byref(count), None):
            self._raise("ReadFile")
        return buffer.raw[: count.value]

    def append(self, handle: int, value: bytes) -> None:
        self._seek(handle, 0, 2)
        buffer = ctypes.create_string_buffer(value)
        count = wintypes.DWORD()
        if not self.kernel32.WriteFile(handle, buffer, len(value), ctypes.byref(count), None):
            self._raise("WriteFile")
        if count.value != len(value):
            raise OSError("short marker write")

    def flush(self, handle: int) -> None:
        if not self.kernel32.FlushFileBuffers(handle):
            self._raise("FlushFileBuffers")

    def close(self, handle: int | _DirectoryHandles) -> None:
        if isinstance(handle, _DirectoryHandles):
            errors = []
            for item in reversed(handle.pinned):
                if not self.kernel32.CloseHandle(item):
                    errors.append(ctypes.get_last_error())
            if errors:
                raise OSError(errors[0], "CloseHandle")
            return
        if not self.kernel32.CloseHandle(handle):
            self._raise("CloseHandle")
