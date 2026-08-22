"""Windows custody controls for ScienceBase SQLite reservation writes."""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
from typing import Any, Iterator

from app.services.sciencebase_spent_marker import (
    MarkerIdentity,
    WindowsMarkerBackend,
)


class ReservationSecurityHold(RuntimeError):
    """A reservation database or transient journal cannot be trusted."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _Acl(ctypes.Structure):
    _fields_ = [
        ("revision", ctypes.c_ubyte),
        ("sbz1", ctypes.c_ubyte),
        ("acl_size", ctypes.c_ushort),
        ("ace_count", ctypes.c_ushort),
        ("sbz2", ctypes.c_ushort),
    ]


class _AceHeader(ctypes.Structure):
    _fields_ = [
        ("ace_type", ctypes.c_ubyte),
        ("ace_flags", ctypes.c_ubyte),
        ("ace_size", ctypes.c_ushort),
    ]


class _TokenOwner(ctypes.Structure):
    _fields_ = [("owner", ctypes.c_void_p)]


class _TokenDefaultDacl(ctypes.Structure):
    _fields_ = [("default_dacl", ctypes.c_void_p)]


class _Luid(ctypes.Structure):
    _fields_ = [("low_part", wintypes.DWORD), ("high_part", wintypes.LONG)]


class _TokenStatistics(ctypes.Structure):
    _fields_ = [
        ("token_id", _Luid),
        ("authentication_id", _Luid),
        ("expiration_time", ctypes.c_longlong),
        ("token_type", ctypes.c_int),
        ("impersonation_level", ctypes.c_int),
        ("dynamic_charged", wintypes.DWORD),
        ("dynamic_available", wintypes.DWORD),
        ("group_count", wintypes.DWORD),
        ("privilege_count", wintypes.DWORD),
        ("modified_id", _Luid),
    ]


class WindowsReservationSecurity:
    """Birth-time token scope plus durable and transient ACL oracles."""

    TOKEN_DUPLICATE = 0x0002
    TOKEN_IMPERSONATE = 0x0004
    TOKEN_QUERY = 0x0008
    TOKEN_ADJUST_DEFAULT = 0x0080
    TOKEN_USER = 1
    TOKEN_OWNER = 4
    TOKEN_DEFAULT_DACL = 6
    TOKEN_STATISTICS = 10
    SECURITY_IMPERSONATION = 2
    TOKEN_IMPERSONATION = 2
    ACL_REVISION = 2
    ERROR_FILE_NOT_FOUND = 2
    ERROR_PATH_NOT_FOUND = 3
    ERROR_NO_TOKEN = 1008

    def __init__(self, canonical_root: Path) -> None:
        self.root = Path(canonical_root)
        try:
            if (
                not self.root.is_absolute()
                or self.root.resolve(strict=True) != self.root
                or not self.root.is_dir()
            ):
                raise OSError("reservation root binding invalid")
            self.backend = WindowsMarkerBackend()
            self._configure_token_functions()
            self._owner_sid = self.backend._owner_sid
            self._system_sid = self.backend._system_sid
            self._owner_text = self.backend._sid_to_string(self._owner_sid)
            self._system_text = self.backend._sid_to_string(self._system_sid)
            root_handle = self.backend.open_existing_directory(self.root)
            try:
                identity = self.backend.identity(root_handle)
                if (
                    not self._valid_identity(identity, directory=True)
                    or self.backend.secure(root_handle) != (True, True, True)
                ):
                    raise OSError("reservation root custody invalid")
                self._root_identity = identity
            finally:
                self.backend.close(root_handle)
        except BaseException:
            raise ReservationSecurityHold("reservation_birth_token_invalid") from None

    def _configure_token_functions(self) -> None:
        void_p = ctypes.c_void_p
        dword_p = ctypes.POINTER(wintypes.DWORD)
        handle_p = ctypes.POINTER(wintypes.HANDLE)
        self.backend.kernel32.GetCurrentThread.argtypes = []
        self.backend.kernel32.GetCurrentThread.restype = wintypes.HANDLE
        self.backend.advapi32.OpenThreadToken.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.BOOL,
            handle_p,
        ]
        self.backend.advapi32.OpenThreadToken.restype = wintypes.BOOL
        self.backend.advapi32.DuplicateTokenEx.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            void_p,
            ctypes.c_int,
            ctypes.c_int,
            handle_p,
        ]
        self.backend.advapi32.DuplicateTokenEx.restype = wintypes.BOOL
        self.backend.advapi32.SetTokenInformation.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            void_p,
            wintypes.DWORD,
        ]
        self.backend.advapi32.SetTokenInformation.restype = wintypes.BOOL
        self.backend.advapi32.SetThreadToken.argtypes = [
            handle_p,
            wintypes.HANDLE,
        ]
        self.backend.advapi32.SetThreadToken.restype = wintypes.BOOL
        self.backend.advapi32.InitializeAcl.argtypes = [
            void_p,
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        self.backend.advapi32.InitializeAcl.restype = wintypes.BOOL
        self.backend.advapi32.AddAccessAllowedAceEx.argtypes = [
            void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            void_p,
        ]
        self.backend.advapi32.AddAccessAllowedAceEx.restype = wintypes.BOOL
        self.backend.advapi32.GetTokenInformation.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            void_p,
            wintypes.DWORD,
            dword_p,
        ]

    @staticmethod
    def _valid_identity(identity: MarkerIdentity, *, directory: bool) -> bool:
        return (
            identity.volume not in (None, "")
            and identity.file_id not in (None, "")
            and identity.link_count == 1
            and not identity.reparse
            and identity.directory is directory
        )

    def _token_buffer(self, token: int, information_class: int) -> ctypes.Array[Any]:
        size = wintypes.DWORD()
        self.backend.advapi32.GetTokenInformation(
            token, information_class, None, 0, ctypes.byref(size)
        )
        if not size.value:
            raise OSError(ctypes.get_last_error(), "GetTokenInformation(size)")
        buffer = ctypes.create_string_buffer(size.value)
        if not self.backend.advapi32.GetTokenInformation(
            token,
            information_class,
            buffer,
            size,
            ctypes.byref(size),
        ):
            raise OSError(ctypes.get_last_error(), "GetTokenInformation")
        return buffer

    def _token_sid(
        self, token: int, information_class: int
    ) -> tuple[int, ctypes.Array[Any]]:
        buffer = self._token_buffer(token, information_class)
        pointer = ctypes.c_void_p.from_buffer(buffer).value
        if not pointer:
            raise OSError("token SID missing")
        length = self.backend.advapi32.GetLengthSid(pointer)
        copied = ctypes.create_string_buffer(length)
        if not self.backend.advapi32.CopySid(length, copied, pointer):
            raise OSError(ctypes.get_last_error(), "CopySid")
        return ctypes.addressof(copied), copied

    def _token_id(self, token: int) -> tuple[int, int]:
        buffer = self._token_buffer(token, self.TOKEN_STATISTICS)
        statistics = ctypes.cast(buffer, ctypes.POINTER(_TokenStatistics)).contents
        return statistics.token_id.low_part, statistics.token_id.high_part

    def _ace_tuples(self, dacl: int) -> tuple[tuple[str, int, int, int], ...]:
        acl = ctypes.cast(dacl, ctypes.POINTER(_Acl)).contents
        values: list[tuple[str, int, int, int]] = []
        for index in range(acl.ace_count):
            ace = ctypes.c_void_p()
            if not self.backend.advapi32.GetAce(dacl, index, ctypes.byref(ace)):
                raise OSError(ctypes.get_last_error(), "GetAce")
            header = ctypes.cast(ace, ctypes.POINTER(_AceHeader)).contents
            sid = ctypes.c_void_p(ace.value + 8)
            mask = ctypes.c_uint32.from_address(ace.value + 4).value
            values.append(
                (
                    self.backend._sid_to_string(sid),
                    header.ace_type,
                    header.ace_flags,
                    mask,
                )
            )
        return tuple(sorted(values))

    def _token_default_dacl(
        self, token: int
    ) -> tuple[tuple[str, int, int, int], ...]:
        buffer = self._token_buffer(token, self.TOKEN_DEFAULT_DACL)
        dacl = ctypes.c_void_p.from_buffer(buffer).value
        if not dacl:
            raise OSError("token default DACL missing")
        return self._ace_tuples(dacl)

    def _token_snapshot(
        self, token: int
    ) -> tuple[str, str, tuple[tuple[str, int, int, int], ...]]:
        user_pointer, user = self._token_sid(token, self.TOKEN_USER)
        owner_pointer, owner = self._token_sid(token, self.TOKEN_OWNER)
        user_text = self.backend._sid_to_string(user_pointer)
        owner_text = self.backend._sid_to_string(owner_pointer)
        del user, owner
        return (
            user_text,
            owner_text,
            self._token_default_dacl(token),
        )

    def _build_exact_dacl(self) -> ctypes.Array[Any]:
        owner_length = self.backend.advapi32.GetLengthSid(self._owner_sid)
        system_length = self.backend.advapi32.GetLengthSid(self._system_sid)
        ace_fixed = 8
        size = ctypes.sizeof(_Acl) + ace_fixed * 2 + owner_length + system_length
        acl = ctypes.create_string_buffer(size)
        if not self.backend.advapi32.InitializeAcl(acl, size, self.ACL_REVISION):
            raise OSError(ctypes.get_last_error(), "InitializeAcl")
        for sid in (self._owner_sid, self._system_sid):
            if not self.backend.advapi32.AddAccessAllowedAceEx(
                acl,
                self.ACL_REVISION,
                0,
                self.backend.FILE_ALL_ACCESS,
                sid,
            ):
                raise OSError(ctypes.get_last_error(), "AddAccessAllowedAceEx")
        return acl

    def _exact_aces(self) -> tuple[tuple[str, int, int, int], ...]:
        return tuple(
            sorted(
                (
                    (self._owner_text, self.backend.ACCESS_ALLOWED_ACE_TYPE, 0, self.backend.FILE_ALL_ACCESS),
                    (self._system_text, self.backend.ACCESS_ALLOWED_ACE_TYPE, 0, self.backend.FILE_ALL_ACCESS),
                )
            )
        )

    def _open_process_token(self) -> int:
        token = wintypes.HANDLE()
        if not self.backend.advapi32.OpenProcessToken(
            self.backend.kernel32.GetCurrentProcess(),
            self.TOKEN_DUPLICATE | self.TOKEN_QUERY,
            ctypes.byref(token),
        ):
            raise OSError(ctypes.get_last_error(), "OpenProcessToken")
        return token.value

    def _open_thread_token(self, access: int) -> int | None:
        token = wintypes.HANDLE()
        if self.backend.advapi32.OpenThreadToken(
            self.backend.kernel32.GetCurrentThread(),
            access,
            True,
            ctypes.byref(token),
        ):
            return token.value
        error = ctypes.get_last_error()
        if error == self.ERROR_NO_TOKEN:
            return None
        raise OSError(error, "OpenThreadToken")

    def _duplicate_birth_token(self, source: int) -> int:
        duplicate = wintypes.HANDLE()
        if not self.backend.advapi32.DuplicateTokenEx(
            source,
            self.TOKEN_QUERY | self.TOKEN_IMPERSONATE | self.TOKEN_ADJUST_DEFAULT,
            None,
            self.SECURITY_IMPERSONATION,
            self.TOKEN_IMPERSONATION,
            ctypes.byref(duplicate),
        ):
            raise OSError(ctypes.get_last_error(), "DuplicateTokenEx")
        return duplicate.value

    def _prepare_birth_token(self, token: int) -> None:
        user_pointer, user = self._token_sid(token, self.TOKEN_USER)
        try:
            if not self.backend.advapi32.EqualSid(user_pointer, self._owner_sid):
                raise OSError("birth token user does not own reservation root")
        finally:
            del user
        owner = _TokenOwner(ctypes.cast(self._owner_sid, ctypes.c_void_p))
        if not self.backend.advapi32.SetTokenInformation(
            token,
            self.TOKEN_OWNER,
            ctypes.byref(owner),
            ctypes.sizeof(owner),
        ):
            raise OSError(ctypes.get_last_error(), "SetTokenInformation(TokenOwner)")
        acl = self._build_exact_dacl()
        default_dacl = _TokenDefaultDacl(ctypes.cast(acl, ctypes.c_void_p))
        if not self.backend.advapi32.SetTokenInformation(
            token,
            self.TOKEN_DEFAULT_DACL,
            ctypes.byref(default_dacl),
            ctypes.sizeof(default_dacl),
        ):
            raise OSError(
                ctypes.get_last_error(), "SetTokenInformation(TokenDefaultDacl)"
            )
        if self._token_snapshot(token) != (
            self._owner_text,
            self._owner_text,
            self._exact_aces(),
        ):
            raise OSError("birth token security verification failed")

    def _set_thread_token(self, token: int | None) -> None:
        if not self.backend.advapi32.SetThreadToken(None, token):
            raise OSError(ctypes.get_last_error(), "SetThreadToken")

    @contextmanager
    def birth_scope(self) -> Iterator[None]:
        source: int | None = None
        prior: int | None = None
        duplicate: int | None = None
        source_snapshot: tuple[
            str, str, tuple[tuple[str, int, int, int], ...]
        ] | None = None
        prior_id: tuple[int, int] | None = None
        assigned = False
        try:
            source = self._open_process_token()
            source_snapshot = self._token_snapshot(source)
            if source_snapshot[0] != self._owner_text:
                raise OSError("process token user binding invalid")
            prior = self._open_thread_token(self.TOKEN_QUERY | self.TOKEN_IMPERSONATE)
            prior_id = self._token_id(prior) if prior is not None else None
            duplicate = self._duplicate_birth_token(source)
            self._prepare_birth_token(duplicate)
            self._set_thread_token(duplicate)
            assigned = True
            observed = self._open_thread_token(self.TOKEN_QUERY)
            try:
                if observed is None or self._token_id(observed) != self._token_id(duplicate):
                    raise OSError("birth token assignment verification failed")
            finally:
                if observed is not None:
                    self.backend.kernel32.CloseHandle(observed)
        except BaseException:
            restore_failed = False
            if assigned:
                try:
                    self._set_thread_token(prior)
                    observed = self._open_thread_token(self.TOKEN_QUERY)
                    try:
                        restored_id = (
                            self._token_id(observed) if observed is not None else None
                        )
                        restore_failed = restored_id != prior_id
                    finally:
                        if observed is not None:
                            self.backend.kernel32.CloseHandle(observed)
                except BaseException:
                    restore_failed = True
            for handle in (duplicate, prior, source):
                if handle is not None:
                    self.backend.kernel32.CloseHandle(handle)
            if restore_failed:
                raise ReservationSecurityHold(
                    "reservation_birth_token_restore_failed"
                ) from None
            raise ReservationSecurityHold("reservation_birth_token_invalid") from None
        try:
            yield
        finally:
            restore_failed = False
            try:
                if assigned:
                    self._set_thread_token(prior)
                observed = self._open_thread_token(self.TOKEN_QUERY)
                try:
                    restored_id = self._token_id(observed) if observed is not None else None
                    restore_failed = restored_id != prior_id
                finally:
                    if observed is not None:
                        self.backend.kernel32.CloseHandle(observed)
                restore_failed = (
                    restore_failed
                    or source is None
                    or source_snapshot is None
                    or self._token_snapshot(source) != source_snapshot
                )
            except BaseException:
                restore_failed = True
            finally:
                for handle in (duplicate, prior, source):
                    if handle is not None:
                        self.backend.kernel32.CloseHandle(handle)
            if restore_failed:
                raise ReservationSecurityHold(
                    "reservation_birth_token_restore_failed"
                ) from None

    @staticmethod
    def _normalized_path(path: Path | str) -> str:
        value = str(path)
        if value.startswith("\\\\?\\UNC\\"):
            value = "\\\\" + value[8:]
        elif value.startswith("\\\\?\\"):
            value = value[4:]
        return os.path.normcase(os.path.abspath(value))

    def _final_path(self, handle: int) -> str:
        buffer = ctypes.create_unicode_buffer(32768)
        length = self.backend.kernel32.GetFinalPathNameByHandleW(
            handle, buffer, len(buffer), 0
        )
        if not length or length >= len(buffer):
            raise OSError(ctypes.get_last_error(), "GetFinalPathNameByHandleW")
        return self._normalized_path(buffer.value)

    def _open_no_delete_share(self, path: Path) -> int:
        handle = self.backend.kernel32.CreateFileW(
            str(path),
            self.backend.GENERIC_READ,
            self.backend.FILE_SHARE_READ_WRITE,
            None,
            self.backend.OPEN_EXISTING,
            self.backend.FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )
        if handle == self.backend.INVALID_HANDLE:
            raise OSError(ctypes.get_last_error(), "CreateFileW(reservation-security)")
        return handle

    def _security_posture(
        self, handle: int
    ) -> tuple[bool, bool, tuple[tuple[str, int, int, int], ...]]:
        owner = ctypes.c_void_p()
        dacl = ctypes.c_void_p()
        descriptor = ctypes.c_void_p()
        result = self.backend.advapi32.GetSecurityInfo(
            handle,
            self.backend.SE_FILE_OBJECT,
            self.backend.OWNER_SECURITY_INFORMATION
            | self.backend.DACL_SECURITY_INFORMATION,
            ctypes.byref(owner),
            None,
            ctypes.byref(dacl),
            None,
            ctypes.byref(descriptor),
        )
        if result:
            raise OSError(result, "GetSecurityInfo")
        try:
            control = wintypes.WORD()
            revision = wintypes.DWORD()
            if not self.backend.advapi32.GetSecurityDescriptorControl(
                descriptor, ctypes.byref(control), ctypes.byref(revision)
            ):
                raise OSError(
                    ctypes.get_last_error(), "GetSecurityDescriptorControl"
                )
            return (
                bool(self.backend.advapi32.EqualSid(owner, self._owner_sid)),
                bool(control.value & self.backend.SE_DACL_PROTECTED),
                self._ace_tuples(dacl) if dacl else (),
            )
        finally:
            self.backend.kernel32.LocalFree(descriptor)

    def _binding_valid(self, database: Path, journal: Path) -> bool:
        return (
            database.is_absolute()
            and journal.is_absolute()
            and database.parent == self.root
            and journal.parent == self.root
            and journal == database.with_name(database.name + "-journal")
        )

    def verify_database(self, database: Path) -> None:
        path = Path(database)
        handle: int | None = None
        try:
            if not path.is_absolute() or path.parent != self.root:
                raise OSError("durable database binding invalid")
            handle = self._open_no_delete_share(path)
            identity = self.backend.identity(handle)
            if (
                not self._valid_identity(identity, directory=False)
                or self._final_path(handle) != self._normalized_path(path)
                or self.backend.secure(handle) != (True, True, True)
                or self.backend.identity(handle) != identity
            ):
                raise OSError("durable database security invalid")
        except BaseException:
            raise ReservationSecurityHold(
                "reservation_database_security_invalid"
            ) from None
        finally:
            if handle is not None:
                self.backend.close(handle)

    def verify_transient_journal(self, database: Path, journal: Path) -> None:
        database = Path(database)
        journal = Path(journal)
        root_handle: Any = None
        database_handle: int | None = None
        journal_handle: int | None = None
        try:
            if not self._binding_valid(database, journal):
                raise ReservationSecurityHold("reservation_journal_binding_invalid")
            root_handle = self.backend.open_existing_directory(self.root)
            database_handle = self._open_no_delete_share(database)
            try:
                journal_handle = self._open_no_delete_share(journal)
            except OSError as exc:
                if exc.errno in (self.ERROR_FILE_NOT_FOUND, self.ERROR_PATH_NOT_FOUND):
                    raise ReservationSecurityHold("reservation_journal_missing") from None
                raise
            root_identity = self.backend.identity(root_handle)
            database_identity = self.backend.identity(database_handle)
            journal_identity = self.backend.identity(journal_handle)
            if (
                root_identity != self._root_identity
                or not self._valid_identity(root_identity, directory=True)
                or self.backend.secure(root_handle) != (True, True, True)
                or not self._valid_identity(database_identity, directory=False)
                or not self._valid_identity(journal_identity, directory=False)
                or database_identity.volume != root_identity.volume
                or journal_identity.volume != root_identity.volume
                or self._final_path(database_handle) != self._normalized_path(database)
                or self._final_path(journal_handle) != self._normalized_path(journal)
            ):
                raise ReservationSecurityHold("reservation_journal_binding_invalid")
            owner, protected, aces = self._security_posture(journal_handle)
            if not owner or protected or aces != self._exact_aces():
                raise ReservationSecurityHold("reservation_journal_security_invalid")
            if (
                self.backend.identity(root_handle) != root_identity
                or self.backend.secure(root_handle) != (True, True, True)
                or self.backend.identity(database_handle) != database_identity
                or self.backend.identity(journal_handle) != journal_identity
                or self._security_posture(journal_handle)
                != (True, False, self._exact_aces())
            ):
                raise ReservationSecurityHold("reservation_journal_binding_invalid")
        except ReservationSecurityHold:
            raise
        except BaseException:
            raise ReservationSecurityHold("reservation_journal_binding_invalid") from None
        finally:
            for handle in (journal_handle, database_handle, root_handle):
                if handle is not None:
                    self.backend.close(handle)

    def verify_journal_absent(self, journal: Path) -> None:
        journal = Path(journal)
        handle: int | None = None
        try:
            if (
                not journal.is_absolute()
                or journal.parent != self.root
                or not journal.name.endswith("-journal")
            ):
                raise OSError("journal cleanup binding invalid")
            try:
                handle = self._open_no_delete_share(journal)
            except OSError as exc:
                if exc.errno in (self.ERROR_FILE_NOT_FOUND, self.ERROR_PATH_NOT_FOUND):
                    return
                raise
            raise OSError("rollback journal residue remains")
        except BaseException:
            raise ReservationSecurityHold(
                "reservation_journal_cleanup_indeterminate"
            ) from None
        finally:
            if handle is not None:
                self.backend.close(handle)
