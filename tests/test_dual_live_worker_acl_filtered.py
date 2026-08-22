"""Real Windows filtered-token proof for the retained B0 worker bundle.

The externally provisioned bundle is never changed.  These tests only create
in-memory access tokens and impersonate them on the current thread while the
production bundle validator and a regular Python file read exercise NTFS.
"""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import errno
import hashlib
import json
import os
from pathlib import Path
from typing import Iterator

import pytest


_BINDING_ENV = "PROJECT6_B0_BUNDLE_BINDING"
_MANIFEST = "worker-bundle.json"
_SYSTEM_SID = "S-1-5-18"
_ADMINISTRATORS_SID = "S-1-5-32-544"
_ANONYMOUS_SID = "S-1-5-7"
_CONTROL_MASK = 0x001F01FF
_RX_MASK = 0x001200A9

_TOKEN_DUPLICATE = 0x0002
_TOKEN_IMPERSONATE = 0x0004
_TOKEN_QUERY = 0x0008
_TOKEN_ADJUST_PRIVILEGES = 0x0020
_DISABLE_MAX_PRIVILEGE = 0x00000001
_SE_GROUP_ENABLED = 0x00000004
_SE_GROUP_USE_FOR_DENY_ONLY = 0x00000010
_SE_PRIVILEGE_ENABLED = 0x00000002
_TOKEN_USER = 1
_TOKEN_GROUPS = 2
_TOKEN_PRIVILEGES = 3
_TOKEN_RESTRICTED_SIDS = 11
_TOKEN_ELEVATION = 20
_ERROR_INSUFFICIENT_BUFFER = 122


class _SidAndAttributes(ctypes.Structure):
    _fields_ = [("sid", ctypes.c_void_p), ("attributes", wintypes.DWORD)]


class _TokenUser(ctypes.Structure):
    _fields_ = [("user", _SidAndAttributes)]


class _TokenGroups(ctypes.Structure):
    _fields_ = [("count", wintypes.DWORD), ("groups", _SidAndAttributes * 1)]


class _Luid(ctypes.Structure):
    _fields_ = [("low", wintypes.DWORD), ("high", wintypes.LONG)]


class _LuidAndAttributes(ctypes.Structure):
    _fields_ = [("luid", _Luid), ("attributes", wintypes.DWORD)]


class _TokenPrivileges(ctypes.Structure):
    _fields_ = [
        ("count", wintypes.DWORD),
        ("privileges", _LuidAndAttributes * 1),
    ]


if os.name == "nt":
    _KERNEL = ctypes.WinDLL("kernel32", use_last_error=True)
    _ADVAPI = ctypes.WinDLL("advapi32", use_last_error=True)

    _KERNEL.GetCurrentProcess.restype = wintypes.HANDLE
    _KERNEL.GetCurrentThread.restype = wintypes.HANDLE
    _KERNEL.CloseHandle.argtypes = [wintypes.HANDLE]
    _KERNEL.CloseHandle.restype = wintypes.BOOL
    _KERNEL.LocalFree.argtypes = [ctypes.c_void_p]
    _KERNEL.LocalFree.restype = ctypes.c_void_p

    _ADVAPI.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    _ADVAPI.OpenProcessToken.restype = wintypes.BOOL
    _ADVAPI.OpenThreadToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.BOOL,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    _ADVAPI.OpenThreadToken.restype = wintypes.BOOL
    _ADVAPI.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    _ADVAPI.GetTokenInformation.restype = wintypes.BOOL
    _ADVAPI.CreateRestrictedToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_SidAndAttributes),
        wintypes.DWORD,
        ctypes.POINTER(_LuidAndAttributes),
        wintypes.DWORD,
        ctypes.POINTER(_SidAndAttributes),
        ctypes.POINTER(wintypes.HANDLE),
    ]
    _ADVAPI.CreateRestrictedToken.restype = wintypes.BOOL
    _ADVAPI.AdjustTokenPrivileges.argtypes = [
        wintypes.HANDLE,
        wintypes.BOOL,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    _ADVAPI.AdjustTokenPrivileges.restype = wintypes.BOOL
    _ADVAPI.ImpersonateLoggedOnUser.argtypes = [wintypes.HANDLE]
    _ADVAPI.ImpersonateLoggedOnUser.restype = wintypes.BOOL
    _ADVAPI.RevertToSelf.restype = wintypes.BOOL
    _ADVAPI.ImpersonateAnonymousToken.argtypes = [wintypes.HANDLE]
    _ADVAPI.ImpersonateAnonymousToken.restype = wintypes.BOOL
    _ADVAPI.IsTokenRestricted.argtypes = [wintypes.HANDLE]
    _ADVAPI.IsTokenRestricted.restype = wintypes.BOOL
    _ADVAPI.ConvertSidToStringSidW.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.LPWSTR),
    ]
    _ADVAPI.ConvertSidToStringSidW.restype = wintypes.BOOL
    _ADVAPI.ConvertStringSidToSidW.argtypes = [
        wintypes.LPCWSTR,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    _ADVAPI.ConvertStringSidToSidW.restype = wintypes.BOOL
else:  # pragma: no cover - collection guard for non-Windows jobs
    _KERNEL = None
    _ADVAPI = None


pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires Win32 tokens")


def _check(ok: object) -> None:
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())


def _close(handle: wintypes.HANDLE) -> None:
    if handle and handle.value:
        assert _KERNEL is not None
        _check(_KERNEL.CloseHandle(handle))


@contextmanager
def _process_token() -> Iterator[wintypes.HANDLE]:
    assert _KERNEL is not None and _ADVAPI is not None
    token = wintypes.HANDLE()
    _check(
        _ADVAPI.OpenProcessToken(
            _KERNEL.GetCurrentProcess(),
            _TOKEN_QUERY
            | _TOKEN_DUPLICATE
            | _TOKEN_IMPERSONATE
            | _TOKEN_ADJUST_PRIVILEGES,
            ctypes.byref(token),
        )
    )
    try:
        yield token
    finally:
        _close(token)


def _token_information(
    token: wintypes.HANDLE, information_class: int
) -> ctypes.Array[ctypes.c_char]:
    assert _ADVAPI is not None
    needed = wintypes.DWORD()
    ctypes.set_last_error(0)
    ok = _ADVAPI.GetTokenInformation(
        token, information_class, None, 0, ctypes.byref(needed)
    )
    if ok or ctypes.get_last_error() != _ERROR_INSUFFICIENT_BUFFER or not needed.value:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_string_buffer(needed.value)
    _check(
        _ADVAPI.GetTokenInformation(
            token,
            information_class,
            buffer,
            needed.value,
            ctypes.byref(needed),
        )
    )
    return buffer


def _sid_text(sid: ctypes.c_void_p) -> str:
    assert _KERNEL is not None and _ADVAPI is not None
    value = wintypes.LPWSTR()
    _check(_ADVAPI.ConvertSidToStringSidW(sid, ctypes.byref(value)))
    try:
        return str(value.value)
    finally:
        _KERNEL.LocalFree(value)


def _token_user_sid(token: wintypes.HANDLE) -> str:
    buffer = _token_information(token, _TOKEN_USER)
    user = ctypes.cast(buffer, ctypes.POINTER(_TokenUser)).contents
    return _sid_text(user.user.sid)


def _token_sid_entries(
    token: wintypes.HANDLE, information_class: int
) -> tuple[tuple[str, int], ...]:
    buffer = _token_information(token, information_class)
    groups = ctypes.cast(buffer, ctypes.POINTER(_TokenGroups)).contents
    base = ctypes.addressof(buffer) + _TokenGroups.groups.offset
    entries = []
    for index in range(int(groups.count)):
        entry = _SidAndAttributes.from_address(
            base + index * ctypes.sizeof(_SidAndAttributes)
        )
        entries.append((_sid_text(entry.sid), int(entry.attributes)))
    return tuple(entries)


def _enabled_sids(token: wintypes.HANDLE) -> frozenset[str]:
    groups = _token_sid_entries(token, _TOKEN_GROUPS)
    enabled_groups = {
        sid
        for sid, attributes in groups
        if attributes & _SE_GROUP_ENABLED
        and not attributes & _SE_GROUP_USE_FOR_DENY_ONLY
    }
    return frozenset({_token_user_sid(token), *enabled_groups})


def _privileges_are_disabled(token: wintypes.HANDLE) -> bool:
    buffer = _token_information(token, _TOKEN_PRIVILEGES)
    privileges = ctypes.cast(buffer, ctypes.POINTER(_TokenPrivileges)).contents
    base = ctypes.addressof(buffer) + _TokenPrivileges.privileges.offset
    return all(
        not (
            _LuidAndAttributes.from_address(
                base + index * ctypes.sizeof(_LuidAndAttributes)
            ).attributes
            & _SE_PRIVILEGE_ENABLED
        )
        for index in range(int(privileges.count))
    )


def _token_dword(token: wintypes.HANDLE, information_class: int) -> int:
    assert _ADVAPI is not None
    value = wintypes.DWORD()
    returned = wintypes.DWORD()
    _check(
        _ADVAPI.GetTokenInformation(
            token,
            information_class,
            ctypes.byref(value),
            ctypes.sizeof(value),
            ctypes.byref(returned),
        )
    )
    assert returned.value == ctypes.sizeof(value)
    return int(value.value)


@contextmanager
def _sid_array(values: tuple[str, ...]) -> Iterator[object]:
    assert _KERNEL is not None and _ADVAPI is not None
    allocated: list[ctypes.c_void_p] = []
    array_type = _SidAndAttributes * len(values)
    entries = array_type()
    try:
        for index, value in enumerate(values):
            pointer = ctypes.c_void_p()
            _check(_ADVAPI.ConvertStringSidToSidW(value, ctypes.byref(pointer)))
            allocated.append(pointer)
            entries[index] = _SidAndAttributes(pointer, 0)
        yield entries
    finally:
        for pointer in allocated:
            _KERNEL.LocalFree(pointer)


def _filtered_impersonation_token(
    source: wintypes.HANDLE,
    *,
    disable_sids: tuple[str, ...] = (),
    restrict_sids: tuple[str, ...] = (),
) -> wintypes.HANDLE:
    """Create a restricted token and disable every remaining privilege."""

    assert _ADVAPI is not None
    restricted = wintypes.HANDLE()
    with _sid_array(disable_sids) as disabled, _sid_array(restrict_sids) as restricted_sids:
        _check(
            _ADVAPI.CreateRestrictedToken(
                source,
                _DISABLE_MAX_PRIVILEGE,
                len(disable_sids),
                disabled if disable_sids else None,
                0,
                None,
                len(restrict_sids),
                restricted_sids if restrict_sids else None,
                ctypes.byref(restricted),
            )
        )

    try:
        _check(
            _ADVAPI.AdjustTokenPrivileges(
                restricted,
                True,
                None,
                0,
                None,
                None,
            )
        )
        assert bool(_ADVAPI.IsTokenRestricted(restricted))
        assert _privileges_are_disabled(restricted)
        return restricted
    except BaseException:
        _close(restricted)
        raise


def _anonymous_restricted_token() -> wintypes.HANDLE:
    assert _KERNEL is not None and _ADVAPI is not None
    anonymous = wintypes.HANDLE()
    _check(_ADVAPI.ImpersonateAnonymousToken(_KERNEL.GetCurrentThread()))
    try:
        _check(
            _ADVAPI.OpenThreadToken(
                _KERNEL.GetCurrentThread(),
                _TOKEN_QUERY
                | _TOKEN_DUPLICATE
                | _TOKEN_IMPERSONATE
                | _TOKEN_ADJUST_PRIVILEGES,
                True,
                ctypes.byref(anonymous),
            )
        )
    finally:
        _check(_ADVAPI.RevertToSelf())
    try:
        return _filtered_impersonation_token(
            anonymous, restrict_sids=(_ANONYMOUS_SID,)
        )
    finally:
        _close(anonymous)


@contextmanager
def _impersonate(token: wintypes.HANDLE) -> Iterator[None]:
    assert _ADVAPI is not None
    _check(_ADVAPI.ImpersonateLoggedOnUser(token))
    try:
        yield
    finally:
        _check(_ADVAPI.RevertToSelf())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _binding_fixture() -> tuple[object, dict[str, object], str]:
    from app.services.dual_live_worker_bundle import BundleBinding

    binding_file = os.environ.get(_BINDING_ENV)
    if not binding_file:
        pytest.skip(f"externally pre-provisioned {_BINDING_ENV} required")
    document = json.loads(
        Path(binding_file).resolve(strict=True).read_text(encoding="utf-8")
    )
    path_fields = {
        "root",
        "provisioning_root",
        "ambient_interpreter_root",
        "repository_root",
        "campaign_root",
        "appcontainer_profile_root",
        "broker_profile_root",
        "user_data_root",
    }
    binding = BundleBinding(
        **{
            key: Path(value) if key in path_fields else value
            for key, value in document.items()
        }
    )
    manifest = json.loads(
        (binding.root / _MANIFEST).read_text(encoding="ascii")
    )
    matches = [
        record
        for record in manifest["files"]
        if record["path"] == binding.interpreter
    ]
    assert len(matches) == 1
    return binding, manifest, str(matches[0]["sha256"])


def _expected_aces(binding: object) -> dict[str, int]:
    return {
        _SYSTEM_SID: _CONTROL_MASK,
        _ADMINISTRATORS_SID: _CONTROL_MASK,
        binding.owner_sid: _CONTROL_MASK,
        binding.provisioner_sid: _CONTROL_MASK,
        binding.broker_sid: _RX_MASK,
        binding.package_sid: _RX_MASK,
    }


def _assert_exact_six_aces(descriptor: object, binding: object) -> None:
    expected = _expected_aces(binding)
    assert len(expected) == 6
    assert descriptor.owner_sid == binding.owner_sid
    assert descriptor.protected is True
    assert len(descriptor.entries) == 6
    actual = {entry.principal: entry for entry in descriptor.entries}
    assert len(actual) == 6
    assert set(actual) == set(expected)
    for principal, mask in expected.items():
        entry = actual[principal]
        assert entry.allow is True
        assert entry.inherited is False
        assert entry.inheritance_flags == 0
        assert entry.access_mask == mask


def test_filtered_broker_token_validates_and_hashes_exact_six_ace_bundle() -> None:
    from app.services.dual_live_worker_bundle import (
        WindowsBundleProbe,
        validate_worker_bundle,
    )

    binding, manifest, interpreter_sha256 = _binding_fixture()
    assert binding.interpreter == "python.exe"
    expected_principals = frozenset(_expected_aces(binding))
    profile_broker_sid = manifest["principals"]["broker"]
    with _process_token() as source:
        current_sid = _token_user_sid(source)
        assert current_sid == profile_broker_sid == binding.broker_sid
        assert _token_dword(source, _TOKEN_ELEVATION) == 0
        source_enabled_sids = _enabled_sids(source)
        other_matching_sids = tuple(
            sorted((source_enabled_sids & expected_principals) - {current_sid})
        )
        filtered = _filtered_impersonation_token(
            source,
            disable_sids=other_matching_sids,
            restrict_sids=tuple(
                sorted(source_enabled_sids - set(other_matching_sids))
            ),
        )

    try:
        assert _token_user_sid(filtered) == current_sid
        assert _enabled_sids(filtered) & expected_principals == {current_sid}
        assert {
            sid
            for sid, _ in _token_sid_entries(filtered, _TOKEN_RESTRICTED_SIDS)
        } & expected_principals == {current_sid}
        assert _token_dword(filtered, _TOKEN_ELEVATION) == 0
        assert _privileges_are_disabled(filtered)
        with _impersonate(filtered):
            probe = WindowsBundleProbe(binding)
            validated = validate_worker_bundle(binding, probe)
            _assert_exact_six_aces(
                probe.security_descriptor(validated.interpreter), binding
            )
            observed_sha256 = _sha256(validated.interpreter)
    finally:
        _close(filtered)

    assert observed_sha256 == interpreter_sha256


def test_restricted_token_without_matching_principal_cannot_validate_or_hash() -> None:
    from app.services.dual_live_worker_bundle import (
        BundleHold,
        WindowsBundleProbe,
        validate_worker_bundle,
    )

    binding, _, _ = _binding_fixture()
    expected_principals = frozenset(_expected_aces(binding))
    baseline = validate_worker_bundle(binding, WindowsBundleProbe(binding))
    denied = _anonymous_restricted_token()
    try:
        assert _enabled_sids(denied).isdisjoint(expected_principals)
        assert {
            sid for sid, _ in _token_sid_entries(denied, _TOKEN_RESTRICTED_SIDS)
        }.isdisjoint(expected_principals)
        assert _privileges_are_disabled(denied)
        with _impersonate(denied):
            with pytest.raises(BundleHold) as validation_denied:
                validate_worker_bundle(binding, WindowsBundleProbe(binding))
            with pytest.raises(PermissionError) as hash_denied:
                _sha256(baseline.interpreter)
    finally:
        _close(denied)

    assert validation_denied.value.code.startswith(
        "bundle_observation_ambiguous_"
    ) or validation_denied.value.code == "bundle_broker_read_execute_denied"
    assert hash_denied.value.errno == errno.EACCES
