"""Read-only validation of an externally provisioned worker closure.

This module never acquires, creates, copies, repairs, provisions, grants,
removes, or cleans bundle content or ACLs.  Its probes are observations only;
every missing, ambiguous, or drifting observation fails closed.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Protocol
import uuid


_SCHEMA = "project6.worker-bundle.v1"
_MANIFEST = "worker-bundle.json"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
_MONIKER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_MAX_MANIFEST_BYTES, _MAX_FILES = 262_144, 4096
_MAX_FILE_BYTES, _MAX_BUNDLE_BYTES = 536_870_912, 2_147_483_648
_MAX_INVENTORY = 8192
_RX = frozenset({"read", "execute", "traverse"})
_RX_MASK = 0x001200A9
_CONTROL_MASK = 0x001F01FF
_MUTATE = frozenset({"write", "create", "delete", "rename", "owner", "dacl"})
_CONTROL = frozenset(
    {"read", "execute", "traverse", "write", "create", "delete", "rename", "owner", "dacl"}
)
_SYSTEM = "S-1-5-18"
_ADMINISTRATORS = "S-1-5-32-544"


class BundleHold(RuntimeError):
    """A secret-free fail-closed bundle validation result."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class VolumeIdentity:
    identity: str
    fixed: bool
    local: bool


@dataclass(frozen=True)
class FileIdentity:
    volume_identity: str
    file_identity: str
    link_count: int
    reparse: bool
    directory: bool = False


@dataclass(frozen=True)
class AccessEntry:
    principal: str
    rights: frozenset[str]
    allow: bool = True
    inherited: bool = False
    inheritance_flags: int = 0
    access_mask: int = 0


@dataclass(frozen=True)
class SecurityDescriptor:
    owner_sid: str
    protected: bool
    entries: tuple[AccessEntry, ...]
    effective_entries: tuple[AccessEntry, ...] = ()


@dataclass(frozen=True)
class RuntimeContext:
    broker_sid: str
    package_sid: str
    profile_root: Path
    ambient_interpreter_root: Path
    broker_profile_root: Path
    user_data_root: Path


@dataclass(frozen=True)
class BundleBinding:
    root: Path
    provisioning_root: Path
    profile_moniker: str
    manifest_digest: str
    source_commit: str
    entrypoint: str
    interpreter: str
    python_version: str
    architecture: str
    package_sid: str
    owner_sid: str
    provisioner_sid: str
    broker_sid: str
    ambient_interpreter_root: Path
    repository_root: Path
    campaign_root: Path
    appcontainer_profile_root: Path
    broker_profile_root: Path
    user_data_root: Path


@dataclass(frozen=True)
class ValidatedWorkerBundle:
    root: Path
    interpreter: Path
    entrypoint: Path
    manifest_digest: str
    root_identity: FileIdentity
    volume_identity: VolumeIdentity
    snapshot_digest: str


class BundleProbe(Protocol):
    """Injected, read-only Windows identity/content/security observations."""

    def canonicalize(self, path: Path) -> Path: ...
    def volume(self, path: Path) -> VolumeIdentity: ...
    def identity(self, path: Path) -> FileIdentity: ...
    def inventory(self, root: Path, max_entries: int) -> tuple[str, ...]: ...
    def read_bytes(self, path: Path, max_bytes: int) -> bytes: ...
    def security_descriptor(self, path: Path) -> SecurityDescriptor: ...
    def runtime_context(self, profile_moniker: str) -> RuntimeContext: ...
    def streams(self, path: Path, max_streams: int) -> tuple[str, ...]: ...


class _FileInfo(ctypes.Structure):
    _fields_ = [
        ("attributes", wintypes.DWORD), ("creation_low", wintypes.DWORD),
        ("creation_high", wintypes.DWORD), ("access_low", wintypes.DWORD),
        ("access_high", wintypes.DWORD), ("write_low", wintypes.DWORD),
        ("write_high", wintypes.DWORD), ("volume_serial", wintypes.DWORD),
        ("size_high", wintypes.DWORD), ("size_low", wintypes.DWORD),
        ("link_count", wintypes.DWORD), ("file_index_high", wintypes.DWORD),
        ("file_index_low", wintypes.DWORD),
    ]


class _AclSize(ctypes.Structure):
    _fields_ = [("ace_count", wintypes.DWORD), ("bytes_in_use", wintypes.DWORD), ("bytes_free", wintypes.DWORD)]


class _AceHeader(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ubyte), ("flags", ctypes.c_ubyte), ("size", wintypes.WORD)]


class _AccessAce(ctypes.Structure):
    _fields_ = [("header", _AceHeader), ("mask", wintypes.DWORD), ("sid_start", wintypes.DWORD)]


class _Trustee(ctypes.Structure):
    _fields_ = [
        ("multiple", ctypes.c_void_p), ("operation", ctypes.c_int),
        ("form", ctypes.c_int), ("trustee_type", ctypes.c_int),
        ("name", ctypes.c_void_p),
    ]


class _SidAndAttributes(ctypes.Structure):
    _fields_ = [("sid", ctypes.c_void_p), ("attributes", wintypes.DWORD)]


class _Guid(ctypes.Structure):
    _fields_ = [
        ("data1", ctypes.c_uint32), ("data2", ctypes.c_uint16),
        ("data3", ctypes.c_uint16), ("data4", ctypes.c_ubyte * 8),
    ]


_LOCAL_APP_DATA = _Guid.from_buffer_copy(uuid.UUID("f1b32785-6fba-4fcf-9d55-7b8e7f157091").bytes_le)


class _StreamData(ctypes.Structure):
    _fields_ = [("size", ctypes.c_longlong), ("name", wintypes.WCHAR * 296)]


def _rights(mask: int) -> frozenset[str]:
    result: set[str] = set()
    generic_all = bool(mask & 0x10000000)
    if generic_all or mask & (0x80000000 | 0x00000001 | 0x00000008 | 0x00000080):
        result.add("read")
    if generic_all or mask & (0x20000000 | 0x00000020):
        result.update(("execute", "traverse"))
    if generic_all or mask & (0x40000000 | 0x00000002 | 0x00000004 | 0x00000010 | 0x00000100):
        result.add("write")
    if generic_all or mask & (0x00000002 | 0x00000004):
        result.add("create")
    if generic_all or mask & (0x00010000 | 0x00000040):
        result.update(("delete", "rename"))
    if generic_all or mask & 0x00080000:
        result.add("owner")
    if generic_all or mask & 0x00040000:
        result.add("dacl")
    known = 0xF01F01FF
    if mask & ~known:
        result.add(f"mask:{mask & ~known:08x}")
    return frozenset(result)


def _access_entry(principal: str, mask: int, allow: bool = True, flags: int = 0) -> AccessEntry:
    return AccessEntry(
        principal, _rights(mask), allow, bool(flags & 0x10), flags & 0x0F, mask,
    )


class WindowsBundleProbe:
    """Concrete read-only Win32 observations for one manifest binding."""

    def __init__(self, binding: BundleBinding) -> None:
        if os.name != "nt":
            raise BundleHold("bundle_windows_required")
        self._binding = binding
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        self._userenv = ctypes.WinDLL("userenv", use_last_error=True)
        self._ole32 = ctypes.WinDLL("ole32", use_last_error=True)
        self._shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        self._setup_apis()

    def _setup_apis(self) -> None:
        self._kernel.CreateFileW.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        self._kernel.CreateFileW.restype = wintypes.HANDLE
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.GetCurrentProcess.restype = wintypes.HANDLE
        self._kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.POINTER(_FileInfo)]
        self._kernel.GetVolumePathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        self._kernel.GetVolumeInformationW.argtypes = [
            wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p, ctypes.c_void_p, wintypes.LPWSTR, wintypes.DWORD,
        ]
        self._kernel.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
        self._kernel.FindFirstStreamW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self._kernel.FindFirstStreamW.restype = wintypes.HANDLE
        self._kernel.FindNextStreamW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        self._kernel.FindClose.argtypes = [wintypes.HANDLE]
        self._kernel.LocalFree.argtypes = [ctypes.c_void_p]
        self._advapi.GetNamedSecurityInfoW.argtypes = [
            wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self._advapi.GetSecurityDescriptorControl.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD),
        ]
        self._advapi.GetAclInformation.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.c_int]
        self._advapi.GetAce.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
        self._advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        self._advapi.ConvertStringSidToSidW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
        self._advapi.BuildTrusteeWithSidW.argtypes = [ctypes.POINTER(_Trustee), ctypes.c_void_p]
        self._advapi.GetEffectiveRightsFromAclW.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(_Trustee), ctypes.POINTER(wintypes.DWORD),
        ]
        self._advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        self._advapi.GetTokenInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
        ]
        self._advapi.FreeSid.argtypes = [ctypes.c_void_p]
        self._userenv.DeriveAppContainerSidFromAppContainerName.argtypes = [
            wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p),
        ]
        self._userenv.GetAppContainerFolderPath.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.LPWSTR)]
        self._userenv.GetUserProfileDirectoryW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self._ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        self._shell32.SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(_Guid), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(wintypes.LPWSTR),
        ]

    @staticmethod
    def _check(ok: object) -> None:
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())

    def canonicalize(self, path: Path) -> Path:
        return path.resolve(strict=True)

    def volume(self, path: Path) -> VolumeIdentity:
        volume_root = ctypes.create_unicode_buffer(32768)
        self._check(self._kernel.GetVolumePathNameW(str(path), volume_root, len(volume_root)))
        serial = wintypes.DWORD()
        self._check(
            self._kernel.GetVolumeInformationW(
                volume_root.value, None, 0, ctypes.byref(serial), None, None, None, 0
            )
        )
        drive_type = int(self._kernel.GetDriveTypeW(volume_root.value))
        return VolumeIdentity(f"serial:{serial.value:08x}", drive_type == 3, drive_type != 4)

    def _open_identity(self, path: Path) -> wintypes.HANDLE:
        handle = self._kernel.CreateFileW(
            str(path), 0x00000080, 0x00000001 | 0x00000002 | 0x00000004,
            None, 3, 0x00200000 | 0x02000000, None,
        )
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def identity(self, path: Path) -> FileIdentity:
        handle = self._open_identity(path)
        try:
            info = _FileInfo()
            self._check(self._kernel.GetFileInformationByHandle(handle, ctypes.byref(info)))
        finally:
            self._kernel.CloseHandle(handle)
        file_id = (int(info.file_index_high) << 32) | int(info.file_index_low)
        return FileIdentity(
            f"serial:{int(info.volume_serial):08x}", f"file:{file_id:016x}",
            int(info.link_count), bool(info.attributes & 0x400), bool(info.attributes & 0x10),
        )

    def inventory(self, root: Path, max_entries: int) -> tuple[str, ...]:
        found: list[str] = []
        pending = [root]
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    relative = Path(entry.path).relative_to(root).as_posix()
                    is_directory = entry.is_dir(follow_symlinks=False)
                    found.append(relative + "/" if is_directory else relative)
                    if len(found) > max_entries:
                        raise BundleHold("bundle_inventory_too_large")
                    if is_directory and not entry.is_symlink():
                        pending.append(Path(entry.path))
        return tuple(sorted(found))

    @staticmethod
    def read_bytes(path: Path, max_bytes: int) -> bytes:
        with path.open("rb", buffering=0) as stream:
            return stream.read(max_bytes + 1)

    def streams(self, path: Path, max_streams: int) -> tuple[str, ...]:
        data = _StreamData()
        handle = self._kernel.FindFirstStreamW(str(path), 0, ctypes.byref(data), 0)
        if handle == wintypes.HANDLE(-1).value:
            if ctypes.get_last_error() == 38:
                return ()
            raise ctypes.WinError(ctypes.get_last_error())
        found: list[str] = []
        try:
            while True:
                found.append(str(data.name))
                if len(found) > max_streams:
                    raise BundleHold("bundle_stream_invalid")
                if not self._kernel.FindNextStreamW(handle, ctypes.byref(data)):
                    if ctypes.get_last_error() != 38:
                        raise ctypes.WinError(ctypes.get_last_error())
                    break
        finally:
            self._kernel.FindClose(handle)
        return tuple(found)

    def _sid_text(self, sid: ctypes.c_void_p) -> str:
        text = wintypes.LPWSTR()
        self._check(self._advapi.ConvertSidToStringSidW(sid, ctypes.byref(text)))
        try:
            return str(text.value)
        finally:
            self._kernel.LocalFree(text)

    def _known_folder(self, folder_id: _Guid) -> Path:
        value = wintypes.LPWSTR()
        result = self._shell32.SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(value))
        if result:
            raise OSError(f"known_folder_lookup:{result & 0xFFFFFFFF:08x}")
        try:
            return Path(value.value).resolve(strict=True)
        finally:
            self._ole32.CoTaskMemFree(value)

    def runtime_context(self, profile_moniker: str) -> RuntimeContext:
        token = wintypes.HANDLE()
        self._check(self._advapi.OpenProcessToken(self._kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)))
        try:
            needed = wintypes.DWORD()
            self._advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(needed))
            if ctypes.get_last_error() != 122 or not needed.value:
                raise ctypes.WinError(ctypes.get_last_error())
            buffer = ctypes.create_string_buffer(needed.value)
            self._check(self._advapi.GetTokenInformation(token, 1, buffer, needed, ctypes.byref(needed)))
            broker_sid = self._sid_text(ctypes.cast(buffer, ctypes.POINTER(_SidAndAttributes)).contents.sid)
            profile_size = wintypes.DWORD()
            self._userenv.GetUserProfileDirectoryW(token, None, ctypes.byref(profile_size))
            if ctypes.get_last_error() != 122 or not profile_size.value:
                raise ctypes.WinError(ctypes.get_last_error())
            profile_buffer = ctypes.create_unicode_buffer(profile_size.value)
            self._check(self._userenv.GetUserProfileDirectoryW(token, profile_buffer, ctypes.byref(profile_size)))
            broker_profile = Path(profile_buffer.value).resolve(strict=True)
        finally:
            self._kernel.CloseHandle(token)

        package_sid_pointer = ctypes.c_void_p()
        result = self._userenv.DeriveAppContainerSidFromAppContainerName(
            profile_moniker, ctypes.byref(package_sid_pointer)
        )
        if result:
            raise OSError(f"appcontainer_sid_derivation:{result & 0xFFFFFFFF:08x}")
        try:
            package_sid = self._sid_text(package_sid_pointer)
        finally:
            self._advapi.FreeSid(package_sid_pointer)

        profile_path = wintypes.LPWSTR()
        result = self._userenv.GetAppContainerFolderPath(package_sid, ctypes.byref(profile_path))
        if result:
            raise OSError(f"appcontainer_profile_lookup:{result & 0xFFFFFFFF:08x}")
        try:
            if not profile_path.value or not Path(profile_path.value).is_dir():
                raise BundleHold("bundle_appcontainer_profile_missing")
            canonical_profile = Path(profile_path.value).resolve(strict=True)
        finally:
            self._ole32.CoTaskMemFree(profile_path)

        return RuntimeContext(
            broker_sid, package_sid, canonical_profile,
            Path(sys.executable).resolve(strict=True).parent,
            broker_profile, self._known_folder(_LOCAL_APP_DATA),
        )

    def _effective(self, acl: ctypes.c_void_p, sid_text: str) -> AccessEntry:
        sid = ctypes.c_void_p()
        self._check(self._advapi.ConvertStringSidToSidW(sid_text, ctypes.byref(sid)))
        try:
            trustee = _Trustee()
            self._advapi.BuildTrusteeWithSidW(ctypes.byref(trustee), sid)
            mask = wintypes.DWORD()
            error = self._advapi.GetEffectiveRightsFromAclW(acl, ctypes.byref(trustee), ctypes.byref(mask))
            if error:
                raise ctypes.WinError(error)
            return _access_entry(sid_text, int(mask.value))
        finally:
            self._kernel.LocalFree(sid)

    def _broker_access(self, path: Path) -> AccessEntry:
        attributes = self.identity(path)
        flags = 0x00200000 | 0x02000000 if attributes.directory else 0x00200000
        allowed = self._kernel.CreateFileW(
            str(path), 0x80000000 | 0x20000000, 0x00000001 | 0x00000002 | 0x00000004,
            None, 3, flags, None,
        )
        if allowed == wintypes.HANDLE(-1).value:
            raise BundleHold("bundle_broker_read_execute_denied")
        self._kernel.CloseHandle(allowed)
        mutation_rights = [0x10, 0x100, 0x10000, 0x40000, 0x80000]
        mutation_rights.extend((0x2, 0x4, 0x40) if attributes.directory else (0x2, 0x4))
        for right in mutation_rights:
            handle = self._kernel.CreateFileW(
                str(path), right, 0x00000001 | 0x00000002 | 0x00000004,
                None, 3, flags, None,
            )
            if handle != wintypes.HANDLE(-1).value:
                self._kernel.CloseHandle(handle)
                raise BundleHold("bundle_broker_mutation_capable")
            if ctypes.get_last_error() != 5:
                raise BundleHold("bundle_broker_access_ambiguous")
        return AccessEntry(self._binding.broker_sid, _RX, access_mask=_RX_MASK)

    def security_descriptor(self, path: Path) -> SecurityDescriptor:
        owner, acl, descriptor = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
        error = self._advapi.GetNamedSecurityInfoW(
            str(path), 1, 0x00000001 | 0x00000004,
            ctypes.byref(owner), None, ctypes.byref(acl), None, ctypes.byref(descriptor),
        )
        if error:
            raise ctypes.WinError(error)
        try:
            control, revision = wintypes.WORD(), wintypes.DWORD()
            self._check(self._advapi.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision)))
            size = _AclSize()
            self._check(self._advapi.GetAclInformation(acl, ctypes.byref(size), ctypes.sizeof(size), 2))
            entries: list[AccessEntry] = []
            for index in range(int(size.ace_count)):
                ace_pointer = ctypes.c_void_p()
                self._check(self._advapi.GetAce(acl, index, ctypes.byref(ace_pointer)))
                ace = ctypes.cast(ace_pointer, ctypes.POINTER(_AccessAce)).contents
                if ace.header.type not in (0, 1):
                    raise BundleHold("bundle_dacl_unsupported")
                sid = ctypes.c_void_p(ace_pointer.value + _AccessAce.sid_start.offset)
                entries.append(_access_entry(self._sid_text(sid), int(ace.mask), ace.header.type == 0, ace.header.flags))
            effective = (
                self._broker_access(path),
                self._effective(acl, self._binding.package_sid),
            )
            return SecurityDescriptor(self._sid_text(owner), bool(control.value & 0x1000), tuple(entries), effective)
        finally:
            self._kernel.LocalFree(descriptor)


def _hold(code: str) -> None:
    raise BundleHold(code) from None


def _canonical_json(raw: bytes) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        _hold("bundle_manifest_invalid")
    if not isinstance(value, dict):
        _hold("bundle_manifest_invalid")
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
    if raw != canonical:
        _hold("bundle_manifest_noncanonical")
    return value


def _relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        _hold("bundle_path_invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        _hold("bundle_path_invalid")
    return value


def _inside(path: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath((os.path.normcase(str(path)), os.path.normcase(str(parent)))) == os.path.normcase(
            str(parent)
        )
    except ValueError:
        return False


def _expected_security(binding: BundleBinding) -> SecurityDescriptor:
    protected = {binding.package_sid, binding.broker_sid, _SYSTEM, _ADMINISTRATORS}
    controllers = {binding.owner_sid, binding.provisioner_sid}
    if (
        any(not value for value in (*protected, *controllers))
        or len(protected) != 4 or protected.intersection(controllers)
    ):
        _hold("bundle_principals_ambiguous")
    controller_entries = tuple(
        AccessEntry(principal, _CONTROL, access_mask=_CONTROL_MASK)
        for principal in dict.fromkeys((binding.owner_sid, binding.provisioner_sid))
    )
    return SecurityDescriptor(
        binding.owner_sid,
        True,
        (
            AccessEntry(_SYSTEM, _CONTROL, access_mask=_CONTROL_MASK),
            AccessEntry(_ADMINISTRATORS, _CONTROL, access_mask=_CONTROL_MASK),
            *controller_entries,
            AccessEntry(binding.broker_sid, _RX, access_mask=_RX_MASK),
            AccessEntry(binding.package_sid, _RX, access_mask=_RX_MASK),
        ),
    )


def _security_matches(observed: SecurityDescriptor, binding: BundleBinding) -> bool:
    expected = _expected_security(binding)
    effective = {entry.principal: entry for entry in observed.effective_entries if entry.allow}
    broker = effective.get(binding.broker_sid)
    package = effective.get(binding.package_sid)
    return (
        observed.owner_sid == expected.owner_sid
        and observed.protected == expected.protected
        and observed.entries == expected.entries
        and package is not None and package.rights == _RX and package.access_mask == _RX_MASK
        and broker is not None and broker.rights == _RX and broker.access_mask == _RX_MASK
    )


def _ancestor_security_safe(observed: SecurityDescriptor, binding: BundleBinding, dedicated: bool) -> bool:
    effective = {entry.principal: entry.rights for entry in observed.effective_entries if entry.allow}
    broker = effective.get(binding.broker_sid, frozenset())
    package = effective.get(binding.package_sid, frozenset())
    return (
        not broker.intersection(_MUTATE)
        and not package.intersection(_MUTATE)
        and "traverse" in broker and "traverse" in package
        and (not dedicated or (observed.protected and observed.owner_sid == binding.owner_sid))
    )


def _streams_clean(probe: BundleProbe, path: Path, directory: bool) -> bool:
    streams = probe.streams(path, 2)
    return streams in (("::$DATA",), ()) if directory else streams == ("::$DATA",)


def _observe(binding: BundleBinding, probe: BundleProbe) -> ValidatedWorkerBundle:
    try:
        root = probe.canonicalize(binding.root)
        provisioner_root = probe.canonicalize(binding.provisioning_root)
        forbidden = tuple(
            probe.canonicalize(path)
            for path in (
                binding.ambient_interpreter_root, binding.repository_root, binding.campaign_root,
                binding.appcontainer_profile_root, binding.broker_profile_root, binding.user_data_root,
            )
        )
        context = probe.runtime_context(binding.profile_moniker)
        if context != RuntimeContext(
            binding.broker_sid, binding.package_sid, forbidden[3], forbidden[0], forbidden[4], forbidden[5]
        ):
            _hold("bundle_runtime_principal_mismatch")
        if (
            root != binding.root or root.parent != provisioner_root
            or any(_inside(root, path) or _inside(provisioner_root, path) for path in forbidden)
        ):
            _hold("bundle_root_forbidden")
        volume = probe.volume(root)
        root_identity = probe.identity(root)
        if not volume.fixed or not volume.local or not volume.identity:
            _hold("bundle_volume_invalid")
        if (
            root_identity.reparse or not root_identity.directory
            or root_identity.volume_identity != volume.identity or not root_identity.file_identity
            or not _streams_clean(probe, root, True)
        ):
            _hold("bundle_root_identity_invalid")

        manifest_identity = probe.identity(root / _MANIFEST)
        raw = probe.read_bytes(root / _MANIFEST, _MAX_MANIFEST_BYTES)
        if len(raw) > _MAX_MANIFEST_BYTES:
            _hold("bundle_manifest_too_large")
        if not _DIGEST.fullmatch(binding.manifest_digest) or (
            "sha256:" + hashlib.sha256(raw).hexdigest() != binding.manifest_digest
        ):
            _hold("bundle_manifest_digest_mismatch")
        if root.name != binding.manifest_digest.replace(":", "-"):
            _hold("bundle_root_unbound")
        manifest = _canonical_json(raw)
        expected_keys = {
            "architecture", "entrypoint", "files", "interpreter", "principals",
            "profile_moniker", "python_version", "schema_version", "source_commit",
        }
        if set(manifest) != expected_keys or manifest["schema_version"] != _SCHEMA:
            _hold("bundle_manifest_contract_mismatch")
        scalar_bindings = {
            "architecture": binding.architecture,
            "entrypoint": binding.entrypoint,
            "interpreter": binding.interpreter,
            "profile_moniker": binding.profile_moniker,
            "python_version": binding.python_version,
            "source_commit": binding.source_commit,
        }
        if any(manifest[key] != value for key, value in scalar_bindings.items()) or not _COMMIT.fullmatch(binding.source_commit):
            _hold("bundle_binding_mismatch")
        if (
            binding.architecture not in {"amd64", "arm64"}
            or not _VERSION.fullmatch(binding.python_version)
            or not _MONIKER.fullmatch(binding.profile_moniker)
        ):
            _hold("bundle_binding_invalid")
        expected_principals = {
            "package": binding.package_sid, "owner": binding.owner_sid,
            "provisioner": binding.provisioner_sid, "broker": binding.broker_sid,
        }
        if manifest["principals"] != expected_principals:
            _hold("bundle_principal_mismatch")
        records = manifest["files"]
        if not isinstance(records, list) or not records or len(records) > _MAX_FILES:
            _hold("bundle_files_invalid")
        expected_paths: set[str] = set()
        expected_dirs: set[str] = set()
        previous_path = ""
        aggregate_bytes = 0
        identities = {root_identity.file_identity}
        snapshot_parts: list[str] = [volume.identity, root_identity.file_identity, binding.manifest_digest]
        ancestor = provisioner_root
        first_ancestor = True
        while ancestor.parent != ancestor:
            identity = probe.identity(ancestor)
            security = probe.security_descriptor(ancestor)
            if (
                identity != probe.identity(ancestor) or security != probe.security_descriptor(ancestor)
                or identity.reparse or not identity.directory or identity.volume_identity != volume.identity
                or not identity.file_identity or not _streams_clean(probe, ancestor, True)
                or not _ancestor_security_safe(security, binding, first_ancestor)
            ):
                _hold("bundle_ancestor_invalid")
            snapshot_parts.extend((str(ancestor), identity.file_identity, repr(security)))
            first_ancestor = False
            ancestor = ancestor.parent
        for record in records:
            if not isinstance(record, dict) or set(record) != {"path", "sha256", "size"}:
                _hold("bundle_file_record_invalid")
            relative = _relative_path(record["path"])
            if relative <= previous_path:
                _hold("bundle_manifest_contract_mismatch")
            previous_path = relative
            if (
                relative in expected_paths or not isinstance(record["size"], int)
                or isinstance(record["size"], bool) or record["size"] < 0
            ):
                _hold("bundle_file_record_invalid")
            aggregate_bytes += record["size"]
            if record["size"] > _MAX_FILE_BYTES or aggregate_bytes > _MAX_BUNDLE_BYTES:
                _hold("bundle_size_invalid")
            digest = record["sha256"]
            if not isinstance(digest, str) or not _HASH.fullmatch(digest):
                _hold("bundle_file_record_invalid")
            expected_paths.add(relative)
            expected_dirs.update(
                parent.as_posix() + "/"
                for parent in PurePosixPath(relative).parents
                if parent.as_posix() != "."
            )
            path = root / Path(relative)
            identity = probe.identity(path)
            data = probe.read_bytes(path, _MAX_FILE_BYTES)
            identity_after = probe.identity(path)
            if not _streams_clean(probe, path, False):
                _hold("bundle_stream_invalid")
            if (
                identity != identity_after or identity.reparse or identity.directory
                or identity.volume_identity != volume.identity or identity.link_count != 1
                or not identity.file_identity or identity.file_identity in identities
                or len(data) != record["size"] or hashlib.sha256(data).hexdigest() != digest
            ):
                _hold("bundle_file_drift")
            identities.add(identity.file_identity)
            if not _security_matches(probe.security_descriptor(path), binding):
                _hold("bundle_dacl_mismatch")
            snapshot_parts.extend((relative, identity.file_identity, digest))

        if binding.interpreter not in expected_paths or binding.entrypoint not in expected_paths:
            _hold("bundle_launch_path_unlisted")
        inventory = tuple(probe.inventory(root, _MAX_INVENTORY))
        if inventory != tuple(sorted({_MANIFEST, *expected_dirs, *expected_paths})):
            _hold("bundle_inventory_mismatch")
        for relative in sorted(expected_dirs):
            path = root / Path(relative.rstrip("/"))
            identity = probe.identity(path)
            security = probe.security_descriptor(path)
            if (
                identity != probe.identity(path) or identity.reparse or not identity.directory
                or identity.volume_identity != volume.identity or not identity.file_identity
                or identity.file_identity in identities or not _streams_clean(probe, path, True)
                or not _security_matches(security, binding)
            ):
                _hold("bundle_directory_drift")
            identities.add(identity.file_identity)
            snapshot_parts.extend((relative, identity.file_identity))
        manifest_identity_after = probe.identity(root / _MANIFEST)
        if (
            manifest_identity != manifest_identity_after or manifest_identity.reparse or manifest_identity.directory
            or manifest_identity.volume_identity != volume.identity
            or manifest_identity.link_count != 1 or not manifest_identity.file_identity
            or manifest_identity.file_identity in identities
            or not _streams_clean(probe, root / _MANIFEST, False)
        ):
            _hold("bundle_manifest_identity_invalid")
        if (
            not _security_matches(probe.security_descriptor(root), binding)
            or not _security_matches(probe.security_descriptor(root / _MANIFEST), binding)
            or probe.identity(root) != root_identity
        ):
            _hold("bundle_dacl_mismatch")
        snapshot_parts.append(manifest_identity.file_identity)
        snapshot = hashlib.sha256("\0".join(snapshot_parts).encode("utf-8")).hexdigest()
        return ValidatedWorkerBundle(
            root, root / binding.interpreter, root / binding.entrypoint,
            binding.manifest_digest, root_identity, volume, snapshot,
        )
    except BundleHold:
        raise
    except Exception:
        raise BundleHold("bundle_observation_ambiguous") from None


def validate_worker_bundle(binding: BundleBinding, probe: BundleProbe) -> ValidatedWorkerBundle:
    """Validate and bind an already provisioned closure without mutation."""

    return _observe(binding, probe)


def revalidate_worker_bundle(
    binding: BundleBinding,
    probe: BundleProbe,
    expected: ValidatedWorkerBundle,
) -> ValidatedWorkerBundle:
    """Rebind while the child is suspended; any drift is HOLD."""

    observed = _observe(binding, probe)
    if observed != expected:
        _hold("bundle_rebind_drift")
    return observed
