from __future__ import annotations

from contextlib import contextmanager
import ctypes
from dataclasses import dataclass, field
import errno
import hashlib
import os
from pathlib import Path
import stat
from typing import BinaryIO, Iterator


class StableRawStorageError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


_READ_CHUNK_SIZE = 1024 * 1024
_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_FILE_ATTRIBUTE_NORMAL = 0x00000080
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_LIST_DIRECTORY = 0x00000001
_FILE_READ_ATTRIBUTES = 0x00000080
_SYNCHRONIZE = 0x00100000
_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_FILE_SHARE_DELETE = 0x00000004
_CREATE_NEW = 1
_OPEN_EXISTING = 3
_ERROR_FILE_EXISTS = 80
_ERROR_ALREADY_EXISTS = 183
_FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
_MOVEFILE_WRITE_THROUGH = 0x00000008


@dataclass(frozen=True)
class StableRawFileIdentity:
    device_id: int
    file_id: int


@dataclass(frozen=True)
class LockedRawFileSnapshot:
    canonical_ref: str
    size: int
    sha256: str
    identity: StableRawFileIdentity | None = field(
        default=None,
        compare=False,
        repr=False,
    )
    link_count: int | None = field(
        default=None,
        compare=False,
        repr=False,
    )
    parent_identity: StableRawFileIdentity | None = field(
        default=None,
        compare=False,
        repr=False,
    )


class OwnedLockedRawFileWriter:
    __slots__ = (
        "_file",
        "_raw_root",
        "_canonical_ref",
        "_identity",
        "_link_count",
        "_parent_identity",
    )

    def __init__(
        self,
        file: BinaryIO,
        *,
        raw_root: Path,
        canonical_ref: str,
        identity: StableRawFileIdentity,
        link_count: int,
        parent_identity: StableRawFileIdentity,
    ) -> None:
        self._file = file
        self._raw_root = raw_root
        self._canonical_ref = canonical_ref
        self._identity = identity
        self._link_count = link_count
        self._parent_identity = parent_identity

    @property
    def closed(self) -> bool:
        return self._file.closed

    @property
    def identity(self) -> StableRawFileIdentity:
        return self._identity

    @property
    def link_count(self) -> int:
        return self._link_count

    @property
    def parent_identity(self) -> StableRawFileIdentity:
        return self._parent_identity

    def write(self, content: bytes | bytearray | memoryview) -> int:
        return self._file.write(content)

    def flush(self) -> None:
        self._file.flush()

    def fileno(self) -> int:
        return self._file.fileno()

    def close(self) -> None:
        self._file.close()


if os.name == "nt":
    import msvcrt
    from ctypes import wintypes

    class _FileAttributeTagInfo(ctypes.Structure):
        _fields_ = [
            ("FileAttributes", wintypes.DWORD),
            ("ReparseTag", wintypes.DWORD),
        ]

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("FileAttributes", wintypes.DWORD),
            ("CreationTimeLow", wintypes.DWORD),
            ("CreationTimeHigh", wintypes.DWORD),
            ("LastAccessTimeLow", wintypes.DWORD),
            ("LastAccessTimeHigh", wintypes.DWORD),
            ("LastWriteTimeLow", wintypes.DWORD),
            ("LastWriteTimeHigh", wintypes.DWORD),
            ("VolumeSerialNumber", wintypes.DWORD),
            ("FileSizeHigh", wintypes.DWORD),
            ("FileSizeLow", wintypes.DWORD),
            ("NumberOfLinks", wintypes.DWORD),
            ("FileIndexHigh", wintypes.DWORD),
            ("FileIndexLow", wintypes.DWORD),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _create_file = _kernel32.CreateFileW
    _create_file.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _create_file.restype = wintypes.HANDLE
    _close_handle = _kernel32.CloseHandle
    _close_handle.argtypes = [wintypes.HANDLE]
    _close_handle.restype = wintypes.BOOL
    _get_attribute_tag = _kernel32.GetFileInformationByHandleEx
    _get_attribute_tag.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    _get_attribute_tag.restype = wintypes.BOOL
    _get_file_information = _kernel32.GetFileInformationByHandle
    _get_file_information.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ByHandleFileInformation),
    ]
    _get_file_information.restype = wintypes.BOOL
    _get_final_path = _kernel32.GetFinalPathNameByHandleW
    _get_final_path.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    _get_final_path.restype = wintypes.DWORD
    _move_file_ex = _kernel32.MoveFileExW
    _move_file_ex.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
    ]
    _move_file_ex.restype = wintypes.BOOL
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _windows_backend_available() -> bool:
    return os.name == "nt"


def _supports_posix_anchored_io() -> bool:
    return (
        os.name == "posix"
        and all(
            function in os.supports_dir_fd
            for function in (os.mkdir, os.open, os.stat)
        )
        and os.stat in os.supports_follow_symlinks
        and all(
            hasattr(os, constant)
            for constant in ("O_CLOEXEC", "O_DIRECTORY", "O_NOFOLLOW")
        )
    )


def _normalise_windows_handle_path(path: str) -> str:
    if path.startswith("\\\\?\\UNC\\"):
        path = "\\\\" + path[8:]
    elif path.startswith("\\\\?\\"):
        path = path[4:]
    return os.path.normcase(os.path.normpath(path))


def _handle_file_information(handle: int) -> _ByHandleFileInformation:
    info = _ByHandleFileInformation()
    if not _get_file_information(handle, ctypes.byref(info)):
        raise StableRawStorageError("io")
    return info


def _handle_identity(handle: int) -> tuple[int, int]:
    info = _handle_file_information(handle)
    file_index = (int(info.FileIndexHigh) << 32) | int(info.FileIndexLow)
    return int(info.VolumeSerialNumber), file_index


def _handle_link_count(handle: int) -> int:
    return int(_handle_file_information(handle).NumberOfLinks)


def _validate_windows_handle(
    handle: int,
    expected_path: Path,
    *,
    directory: bool,
) -> tuple[int, int]:
    attributes = _FileAttributeTagInfo()
    if not _get_attribute_tag(
        handle,
        _FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(attributes),
        ctypes.sizeof(attributes),
    ):
        raise StableRawStorageError("io")
    is_directory = bool(
        int(attributes.FileAttributes) & _FILE_ATTRIBUTE_DIRECTORY
    )
    if (
        bool(int(attributes.FileAttributes) & _FILE_ATTRIBUTE_REPARSE_POINT)
        or is_directory != directory
    ):
        raise StableRawStorageError("unsafe")

    buffer = ctypes.create_unicode_buffer(32768)
    length = int(_get_final_path(handle, buffer, len(buffer), 0))
    if length <= 0 or length >= len(buffer):
        raise StableRawStorageError("io")
    expected = _normalise_windows_handle_path(
        str(expected_path.resolve(strict=True))
    )
    actual = _normalise_windows_handle_path(buffer.value)
    if actual != expected:
        raise StableRawStorageError("unsafe")
    return _handle_identity(handle)


def _open_windows_directory_handle(path: Path) -> tuple[int, tuple[int, int]]:
    handle = _create_file(
        str(path),
        _FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES | _SYNCHRONIZE,
        _FILE_SHARE_READ | _FILE_SHARE_WRITE,
        None,
        _OPEN_EXISTING,
        _FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        raise StableRawStorageError("unsafe")
    try:
        identity = _validate_windows_handle(
            handle,
            path,
            directory=True,
        )
    except Exception:
        _close_handle(handle)
        raise
    return int(handle), identity


def _open_windows_file_handle(
    path: Path,
    *,
    create_new: bool,
) -> int:
    handle = _create_file(
        str(path),
        _GENERIC_READ | (_GENERIC_WRITE if create_new else 0),
        _FILE_SHARE_READ,
        None,
        _CREATE_NEW if create_new else _OPEN_EXISTING,
        _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        error = ctypes.get_last_error()
        if create_new and error in {_ERROR_FILE_EXISTS, _ERROR_ALREADY_EXISTS}:
            raise FileExistsError(error, "raw file already exists", str(path))
        raise StableRawStorageError("unsafe")
    try:
        _validate_windows_handle(handle, path, directory=False)
    except Exception:
        _close_handle(handle)
        raise
    return int(handle)


def _open_windows_move_handle(path: Path) -> int:
    handle = _create_file(
        str(path),
        _GENERIC_READ | _FILE_READ_ATTRIBUTES,
        _FILE_SHARE_READ | _FILE_SHARE_DELETE,
        None,
        _OPEN_EXISTING,
        _FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        raise StableRawStorageError("unsafe")
    try:
        _validate_windows_handle(handle, path, directory=False)
    except Exception:
        _close_handle(handle)
        raise
    return int(handle)


def _close_windows_handle(handle: int) -> None:
    if not _close_handle(handle):
        raise StableRawStorageError("io")


@contextmanager
def _locked_windows_parents(
    raw_root: Path,
    file_path: Path,
    *,
    create: bool,
) -> Iterator[tuple[Path, list[tuple[int, Path, tuple[int, int]]]]]:
    root = _lexical_absolute(raw_root)
    output = _lexical_absolute(file_path)
    try:
        relative = output.relative_to(root)
    except ValueError as exc:
        raise StableRawStorageError("unsafe") from exc
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise StableRawStorageError("unsafe")

    if create:
        root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise StableRawStorageError("unsafe")

    locked: list[tuple[int, Path, tuple[int, int]]] = []
    primary: BaseException | None = None
    close_error: StableRawStorageError | None = None
    try:
        try:
            root_handle, root_identity = _open_windows_directory_handle(root)
            locked.append((root_handle, root, root_identity))
            current = root
            for component in relative.parts[:-1]:
                current = current / component
                if create:
                    current.mkdir(exist_ok=True)
                handle, identity = _open_windows_directory_handle(current)
                locked.append((handle, current, identity))
            yield output, locked
        except BaseException as exc:
            primary = exc
    finally:
        for handle, _, _ in reversed(locked):
            try:
                _close_windows_handle(handle)
            except StableRawStorageError as exc:
                close_error = close_error or exc
    _raise_snapshot_errors(
        primary=primary,
        exit_error=None,
        close_error=close_error,
    )


def _revalidate_windows_directories(
    locked: list[tuple[int, Path, tuple[int, int]]],
) -> None:
    for handle, path, identity in locked:
        if (
            _validate_windows_handle(handle, path, directory=True)
            != identity
        ):
            raise StableRawStorageError("changed")


def _fd_identity(file_stat: os.stat_result) -> tuple[int, int]:
    return int(file_stat.st_dev), int(file_stat.st_ino)


def _fd_stable_state(
    file_stat: os.stat_result,
) -> tuple[int, int, int, int, int]:
    return (
        *_fd_identity(file_stat),
        int(file_stat.st_size),
        int(file_stat.st_mtime_ns),
        int(file_stat.st_nlink),
    )


def _stable_identity(value: tuple[int, int]) -> StableRawFileIdentity:
    return StableRawFileIdentity(device_id=value[0], file_id=value[1])


def _fd_file_identity(fd: int) -> tuple[StableRawFileIdentity, int]:
    if _windows_backend_available():
        handle = msvcrt.get_osfhandle(fd)
        return _stable_identity(_handle_identity(handle)), _handle_link_count(
            handle
        )
    file_stat = os.fstat(fd)
    return _stable_identity(_fd_identity(file_stat)), int(file_stat.st_nlink)


@dataclass(frozen=True)
class _PosixDirectoryHandle:
    fd: int
    parent_fd: int | None
    component: str | None
    path: Path
    identity: tuple[int, int]


def _require_posix_directory(
    file_stat: os.stat_result,
) -> tuple[int, int]:
    if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISDIR(
        file_stat.st_mode
    ):
        raise StableRawStorageError("unsafe")
    return _fd_identity(file_stat)


def _require_posix_regular_file(
    file_stat: os.stat_result,
) -> tuple[int, int]:
    if stat.S_ISLNK(file_stat.st_mode) or not stat.S_ISREG(
        file_stat.st_mode
    ):
        raise StableRawStorageError("unsafe")
    return _fd_identity(file_stat)


def _posix_directory_flags() -> int:
    return (
        os.O_RDONLY
        | os.O_CLOEXEC
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
    )


def _open_posix_root(path: Path) -> _PosixDirectoryHandle:
    try:
        before = path.lstat()
        before_identity = _require_posix_directory(before)
        fd = os.open(path, _posix_directory_flags())
    except (OSError, StableRawStorageError) as exc:
        raise StableRawStorageError("unsafe") from exc
    try:
        opened_identity = _require_posix_directory(os.fstat(fd))
        after_identity = _require_posix_directory(path.lstat())
        if not (
            before_identity == opened_identity == after_identity
        ):
            raise StableRawStorageError("changed")
    except Exception:
        os.close(fd)
        raise
    return _PosixDirectoryHandle(
        fd=fd,
        parent_fd=None,
        component=None,
        path=path,
        identity=opened_identity,
    )


def _open_posix_child_directory(
    parent: _PosixDirectoryHandle,
    component: str,
    path: Path,
) -> _PosixDirectoryHandle:
    try:
        before = os.stat(
            component,
            dir_fd=parent.fd,
            follow_symlinks=False,
        )
        before_identity = _require_posix_directory(before)
        fd = os.open(
            component,
            _posix_directory_flags(),
            dir_fd=parent.fd,
        )
    except (OSError, StableRawStorageError) as exc:
        raise StableRawStorageError("unsafe") from exc
    try:
        opened_identity = _require_posix_directory(os.fstat(fd))
        after = os.stat(
            component,
            dir_fd=parent.fd,
            follow_symlinks=False,
        )
        after_identity = _require_posix_directory(after)
        if not (
            before_identity == opened_identity == after_identity
        ):
            raise StableRawStorageError("changed")
    except Exception:
        os.close(fd)
        raise
    return _PosixDirectoryHandle(
        fd=fd,
        parent_fd=parent.fd,
        component=component,
        path=path,
        identity=opened_identity,
    )


def _revalidate_posix_directories(
    locked: list[_PosixDirectoryHandle],
) -> None:
    for directory in locked:
        try:
            if directory.parent_fd is None:
                current = directory.path.lstat()
            else:
                current = os.stat(
                    str(directory.component),
                    dir_fd=directory.parent_fd,
                    follow_symlinks=False,
                )
            current_identity = _require_posix_directory(current)
            opened_identity = _require_posix_directory(
                os.fstat(directory.fd)
            )
        except (OSError, StableRawStorageError) as exc:
            raise StableRawStorageError("changed") from exc
        if not (
            current_identity
            == opened_identity
            == directory.identity
        ):
            raise StableRawStorageError("changed")


@contextmanager
def _locked_posix_parents(
    raw_root: Path,
    file_path: Path,
    *,
    create: bool,
) -> Iterator[
    tuple[Path, str, list[_PosixDirectoryHandle]]
]:
    root = _lexical_absolute(raw_root)
    output = _lexical_absolute(file_path)
    try:
        relative = output.relative_to(root)
    except ValueError as exc:
        raise StableRawStorageError("unsafe") from exc
    if (
        not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise StableRawStorageError("unsafe")

    try:
        if create:
            root.mkdir(parents=True, exist_ok=True)
        root_handle = _open_posix_root(root)
    except OSError as exc:
        raise StableRawStorageError("io") from exc

    locked = [root_handle]
    primary: BaseException | None = None
    close_error: StableRawStorageError | None = None
    try:
        try:
            current = root
            for component in relative.parts[:-1]:
                parent = locked[-1]
                current = current / component
                if create:
                    try:
                        os.mkdir(component, 0o700, dir_fd=parent.fd)
                    except FileExistsError:
                        pass
                    except OSError as exc:
                        raise StableRawStorageError("io") from exc
                locked.append(
                    _open_posix_child_directory(
                        parent,
                        component,
                        current,
                    )
                )
            yield output, relative.parts[-1], locked
        except BaseException as exc:
            primary = exc
    finally:
        raw_close_error: OSError | None = None
        for directory in reversed(locked):
            try:
                os.close(directory.fd)
            except OSError as exc:
                raw_close_error = raw_close_error or exc
        if raw_close_error is not None:
            close_error = _stable_snapshot_error("io", raw_close_error)
    _raise_snapshot_errors(
        primary=primary,
        exit_error=None,
        close_error=close_error,
    )


def _open_posix_file_fd(
    parent_fd: int,
    file_name: str,
    *,
    create_new: bool,
) -> int:
    flags = os.O_CLOEXEC | os.O_NOFOLLOW
    if create_new:
        flags |= os.O_CREAT | os.O_EXCL | os.O_RDWR
        before_identity = None
    else:
        flags |= os.O_RDONLY
        try:
            before = os.stat(
                file_name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
            before_identity = _require_posix_regular_file(before)
        except (OSError, StableRawStorageError) as exc:
            raise StableRawStorageError("unsafe") from exc
    try:
        fd = os.open(
            file_name,
            flags,
            0o600,
            dir_fd=parent_fd,
        )
    except FileExistsError:
        raise
    except OSError as exc:
        raise StableRawStorageError("unsafe") from exc
    try:
        opened_identity = _require_posix_regular_file(os.fstat(fd))
        after = os.stat(
            file_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        after_identity = _require_posix_regular_file(after)
        if opened_identity != after_identity or (
            before_identity is not None
            and opened_identity != before_identity
        ):
            raise StableRawStorageError("changed")
    except Exception:
        os.close(fd)
        raise
    return fd


def _use_posix_file_fd(
    fd: int,
    parent_fd: int,
    file_name: str,
    locked: list[_PosixDirectoryHandle],
    *,
    write_content: bytes | None,
    expected_content: bytes | None,
) -> tuple[int, str, bool]:
    try:
        before = os.fstat(fd)
        before_identity = _require_posix_regular_file(before)
        if write_content is not None:
            _write_fd(fd, write_content)
        size, digest, matches = _hash_fd(
            fd,
            expected_content=expected_content,
        )
        after = os.fstat(fd)
        after_identity = _require_posix_regular_file(after)
        if before_identity != after_identity:
            raise StableRawStorageError("changed")
        if (
            write_content is None
            and _fd_stable_state(before) != _fd_stable_state(after)
        ):
            raise StableRawStorageError("changed")
        if int(after.st_size) != size:
            raise StableRawStorageError("changed")
        path_after = os.stat(
            file_name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if _require_posix_regular_file(path_after) != after_identity:
            raise StableRawStorageError("changed")
        if _fd_stable_state(path_after) != _fd_stable_state(after):
            raise StableRawStorageError("changed")
        _revalidate_posix_directories(locked)
        return size, digest, matches
    except OSError as exc:
        raise StableRawStorageError("changed") from exc
    finally:
        os.close(fd)


def _hash_fd(
    fd: int,
    *,
    expected_content: bytes | None = None,
    max_bytes: int | None = None,
) -> tuple[int, str, bool]:
    if max_bytes is not None and (
        isinstance(max_bytes, bool)
        or not isinstance(max_bytes, int)
        or max_bytes < 0
    ):
        raise ValueError("max_bytes must be a non-negative integer")
    initial_size = int(os.fstat(fd).st_size)
    if max_bytes is not None and initial_size > max_bytes:
        raise StableRawStorageError("oversized")
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    size = 0
    matches = True
    while size < initial_size:
        chunk = os.read(
            fd,
            min(_READ_CHUNK_SIZE, initial_size - size),
        )
        if not chunk:
            raise StableRawStorageError("changed")
        if expected_content is not None:
            matches = matches and (
                chunk == expected_content[size : size + len(chunk)]
            )
        size += len(chunk)
        digest.update(chunk)
    final_size = int(os.fstat(fd).st_size)
    if max_bytes is not None and final_size > max_bytes:
        raise StableRawStorageError("oversized")
    if final_size != initial_size:
        raise StableRawStorageError("changed")
    if expected_content is not None:
        matches = matches and size == len(expected_content)
    return size, digest.hexdigest(), matches


def _write_fd(fd: int, content: bytes) -> None:
    offset = 0
    while offset < len(content):
        written = os.write(fd, content[offset:])
        if written <= 0:
            raise StableRawStorageError("io")
        offset += written
    os.fsync(fd)


def _use_windows_file_handle(
    handle: int,
    path: Path,
    locked: list[tuple[int, Path, tuple[int, int]]],
    *,
    write_content: bytes | None,
    expected_content: bytes | None,
) -> tuple[int, str, bool]:
    flags = os.O_BINARY | (
        os.O_RDWR if write_content is not None else os.O_RDONLY
    )
    try:
        fd = msvcrt.open_osfhandle(handle, flags)
    except OSError as exc:
        _close_windows_handle(handle)
        raise StableRawStorageError("io") from exc

    try:
        before = os.fstat(fd)
        handle_identity = _validate_windows_handle(
            msvcrt.get_osfhandle(fd),
            path,
            directory=False,
        )
        if write_content is not None:
            _write_fd(fd, write_content)
        size, digest, matches = _hash_fd(
            fd,
            expected_content=expected_content,
        )
        after = os.fstat(fd)
        if _fd_identity(before) != _fd_identity(after):
            raise StableRawStorageError("changed")
        if (
            write_content is None
            and _fd_stable_state(before) != _fd_stable_state(after)
        ):
            raise StableRawStorageError("changed")
        if int(after.st_size) != size:
            raise StableRawStorageError("changed")
        if (
            _validate_windows_handle(
                msvcrt.get_osfhandle(fd),
                path,
                directory=False,
            )
            != handle_identity
        ):
            raise StableRawStorageError("changed")
        _revalidate_windows_directories(locked)
        return size, digest, matches
    except OSError as exc:
        raise StableRawStorageError("io") from exc
    finally:
        os.close(fd)


def _read_windows_snapshot_state(
    fd: int,
    path: Path,
    locked: list[tuple[int, Path, tuple[int, int]]],
    *,
    max_bytes: int | None,
) -> tuple[
    StableRawFileIdentity,
    int,
    tuple[int, int, int, int, int],
    int,
    str,
]:
    before = os.fstat(fd)
    handle = msvcrt.get_osfhandle(fd)
    handle_identity = _validate_windows_handle(
        handle,
        path,
        directory=False,
    )
    link_count = _handle_link_count(handle)
    size, digest, _ = _hash_fd(fd, max_bytes=max_bytes)
    after = os.fstat(fd)
    if (
        _fd_identity(before) != _fd_identity(after)
        or _fd_stable_state(before) != _fd_stable_state(after)
        or int(after.st_size) != size
        or _validate_windows_handle(
            handle,
            path,
            directory=False,
        )
        != handle_identity
        or _handle_link_count(handle) != link_count
    ):
        raise StableRawStorageError("changed")
    _revalidate_windows_directories(locked)
    return (
        _stable_identity(handle_identity),
        link_count,
        _fd_stable_state(after),
        size,
        digest,
    )


def _read_posix_snapshot_state(
    fd: int,
    parent_fd: int,
    file_name: str,
    locked: list[_PosixDirectoryHandle],
    *,
    max_bytes: int | None,
) -> tuple[
    StableRawFileIdentity,
    int,
    tuple[int, int, int, int, int],
    int,
    str,
]:
    before = os.fstat(fd)
    before_identity = _require_posix_regular_file(before)
    size, digest, _ = _hash_fd(fd, max_bytes=max_bytes)
    after = os.fstat(fd)
    after_identity = _require_posix_regular_file(after)
    path_after = os.stat(
        file_name,
        dir_fd=parent_fd,
        follow_symlinks=False,
    )
    if (
        before_identity != after_identity
        or _fd_stable_state(before) != _fd_stable_state(after)
        or int(after.st_size) != size
        or _require_posix_regular_file(path_after) != after_identity
        or _fd_stable_state(path_after) != _fd_stable_state(after)
    ):
        raise StableRawStorageError("changed")
    _revalidate_posix_directories(locked)
    return (
        _stable_identity(after_identity),
        int(after.st_nlink),
        _fd_stable_state(after),
        size,
        digest,
    )


def _stable_snapshot_error(
    reason: str,
    cause: BaseException,
) -> StableRawStorageError:
    error = StableRawStorageError(reason)
    error.__cause__ = cause
    return error


def _raise_snapshot_errors(
    *,
    primary: BaseException | None,
    exit_error: BaseException | None,
    close_error: BaseException | None,
) -> None:
    if primary is not None:
        if exit_error is not None:
            primary.add_note(
                f"Secondary raw snapshot exit failure: {exit_error}"
            )
        if close_error is not None:
            primary.add_note(
                f"Secondary raw snapshot close failure: {close_error}"
            )
        secondary = exit_error or close_error
        if secondary is not None:
            raise primary from secondary
        raise primary
    if exit_error is not None:
        if close_error is not None:
            exit_error.add_note(
                f"Secondary raw snapshot close failure: {close_error}"
            )
            raise exit_error from close_error
        raise exit_error
    if close_error is not None:
        raise close_error


@contextmanager
def _locked_windows_raw_file_snapshot(
    raw_root: Path,
    file_path: Path,
    *,
    max_bytes: int | None,
) -> Iterator[LockedRawFileSnapshot]:
    with _locked_windows_parents(
        raw_root,
        file_path,
        create=False,
    ) as (output, locked):
        handle = _open_windows_file_handle(output, create_new=False)
        try:
            fd = msvcrt.open_osfhandle(
                handle,
                os.O_BINARY | os.O_RDONLY,
            )
        except OSError as exc:
            _close_windows_handle(handle)
            raise StableRawStorageError("io") from exc
        primary: BaseException | None = None
        exit_error: BaseException | None = None
        close_error: BaseException | None = None
        try:
            try:
                identity, link_count, stable_state, size, digest = (
                    _read_windows_snapshot_state(
                        fd,
                        output,
                        locked,
                        max_bytes=max_bytes,
                    )
                )
                snapshot = LockedRawFileSnapshot(
                    canonical_ref=str(output.resolve(strict=True)),
                    size=size,
                    sha256=digest,
                    identity=identity,
                    link_count=link_count,
                    parent_identity=_stable_identity(locked[-1][2]),
                )
            except OSError as exc:
                primary = _stable_snapshot_error("changed", exc)
            except BaseException as exc:
                primary = exc
            if primary is None:
                try:
                    yield snapshot
                except BaseException as exc:
                    primary = exc
                try:
                    (
                        exit_identity,
                        exit_link_count,
                        exit_state,
                        exit_size,
                        exit_digest,
                    ) = _read_windows_snapshot_state(
                        fd,
                        output,
                        locked,
                        max_bytes=max_bytes,
                    )
                    if (
                        exit_identity != identity
                        or exit_link_count != link_count
                        or exit_state != stable_state
                        or exit_size != size
                        or exit_digest != digest
                    ):
                        raise StableRawStorageError("changed")
                except OSError as exc:
                    exit_error = _stable_snapshot_error("changed", exc)
                except BaseException as exc:
                    exit_error = exc
        finally:
            try:
                os.close(fd)
            except OSError as exc:
                close_error = _stable_snapshot_error("io", exc)
        _raise_snapshot_errors(
            primary=primary,
            exit_error=exit_error,
            close_error=close_error,
        )


@contextmanager
def _locked_posix_raw_file_snapshot(
    raw_root: Path,
    file_path: Path,
    *,
    max_bytes: int | None,
) -> Iterator[LockedRawFileSnapshot]:
    with _locked_posix_parents(
        raw_root,
        file_path,
        create=False,
    ) as (output, file_name, locked):
        parent_fd = locked[-1].fd
        fd = _open_posix_file_fd(
            parent_fd,
            file_name,
            create_new=False,
        )
        primary: BaseException | None = None
        exit_error: BaseException | None = None
        close_error: BaseException | None = None
        try:
            try:
                (
                    identity,
                    link_count,
                    stable_state,
                    size,
                    digest,
                ) = _read_posix_snapshot_state(
                    fd,
                    parent_fd,
                    file_name,
                    locked,
                    max_bytes=max_bytes,
                )
                snapshot = LockedRawFileSnapshot(
                    canonical_ref=str(output.resolve(strict=True)),
                    size=size,
                    sha256=digest,
                    identity=identity,
                    link_count=link_count,
                    parent_identity=_stable_identity(
                        locked[-1].identity
                    ),
                )
            except OSError as exc:
                primary = _stable_snapshot_error("changed", exc)
            except BaseException as exc:
                primary = exc
            if primary is None:
                try:
                    yield snapshot
                except BaseException as exc:
                    primary = exc
                try:
                    (
                        exit_identity,
                        exit_link_count,
                        exit_state,
                        exit_size,
                        exit_digest,
                    ) = (
                        _read_posix_snapshot_state(
                            fd,
                            parent_fd,
                            file_name,
                            locked,
                            max_bytes=max_bytes,
                        )
                    )
                    if (
                        exit_identity != identity
                        or exit_link_count != link_count
                        or exit_state != stable_state
                        or exit_size != size
                        or exit_digest != digest
                    ):
                        raise StableRawStorageError("changed")
                except OSError as exc:
                    exit_error = _stable_snapshot_error("changed", exc)
                except BaseException as exc:
                    exit_error = exc
        finally:
            try:
                os.close(fd)
            except OSError as exc:
                close_error = _stable_snapshot_error("io", exc)
        _raise_snapshot_errors(
            primary=primary,
            exit_error=exit_error,
            close_error=close_error,
        )


def _require_snapshot_constraints(
    snapshot: LockedRawFileSnapshot,
    *,
    expected_identity: StableRawFileIdentity | None,
    expected_parent_identity: StableRawFileIdentity | None,
    required_link_count: int | None,
) -> None:
    if (
        expected_identity is not None
        and snapshot.identity != expected_identity
    ):
        raise StableRawStorageError("changed")
    if (
        expected_parent_identity is not None
        and snapshot.parent_identity != expected_parent_identity
    ):
        raise StableRawStorageError("changed")
    if required_link_count is not None:
        if (
            isinstance(required_link_count, bool)
            or not isinstance(required_link_count, int)
            or required_link_count < 1
        ):
            raise ValueError(
                "required_link_count must be a positive integer"
            )
        if snapshot.link_count != required_link_count:
            raise StableRawStorageError("unsafe")


def _windows_writer_from_handle(
    handle: int,
    *,
    raw_root: Path,
    output: Path,
    locked: list[tuple[int, Path, tuple[int, int]]],
) -> OwnedLockedRawFileWriter:
    identity = _stable_identity(
        _validate_windows_handle(handle, output, directory=False)
    )
    link_count = _handle_link_count(handle)
    if link_count != 1:
        _close_windows_handle(handle)
        raise StableRawStorageError("unsafe")
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_BINARY | os.O_RDWR)
    except OSError as exc:
        _close_windows_handle(handle)
        raise StableRawStorageError("io") from exc
    try:
        file = os.fdopen(fd, "w+b", buffering=0)
    except OSError as exc:
        os.close(fd)
        raise StableRawStorageError("io") from exc
    try:
        opened_identity, opened_links = _fd_file_identity(file.fileno())
        if opened_identity != identity or opened_links != link_count:
            raise StableRawStorageError("changed")
        if (
            _stable_identity(
                _validate_windows_handle(
                    msvcrt.get_osfhandle(file.fileno()),
                    output,
                    directory=False,
                )
            )
            != identity
        ):
            raise StableRawStorageError("changed")
        _revalidate_windows_directories(locked)
        parent_identity = _stable_identity(locked[-1][2])
        return OwnedLockedRawFileWriter(
            file,
            raw_root=raw_root,
            canonical_ref=str(output.resolve(strict=True)),
            identity=identity,
            link_count=link_count,
            parent_identity=parent_identity,
        )
    except BaseException:
        file.close()
        raise


def _open_windows_owned_writer(
    raw_root: Path,
    file_path: Path,
    *,
    create_immediate_parent_exclusive: bool,
    expected_parent_identity: StableRawFileIdentity | None,
) -> OwnedLockedRawFileWriter:
    writer: OwnedLockedRawFileWriter | None = None
    try:
        parent_target = (
            file_path.parent
            if create_immediate_parent_exclusive
            else file_path
        )
        with _locked_windows_parents(
            raw_root,
            parent_target,
            create=False,
        ) as (_, locked):
            output = _lexical_absolute(file_path)
            if create_immediate_parent_exclusive:
                parent = output.parent
                try:
                    parent.mkdir()
                except FileExistsError as exc:
                    raise StableRawStorageError("conflict") from exc
                parent_handle, parent_raw_identity = (
                    _open_windows_directory_handle(parent)
                )
                locked.append(
                    (parent_handle, parent, parent_raw_identity)
                )
            parent_identity = _stable_identity(locked[-1][2])
            if (
                expected_parent_identity is not None
                and parent_identity != expected_parent_identity
            ):
                raise StableRawStorageError("changed")
            try:
                handle = _open_windows_file_handle(
                    output,
                    create_new=True,
                )
            except FileExistsError as exc:
                raise StableRawStorageError("conflict") from exc
            writer = _windows_writer_from_handle(
                handle,
                raw_root=_lexical_absolute(raw_root),
                output=output,
                locked=locked,
            )
        return writer
    except BaseException:
        if writer is not None:
            writer.close()
        raise


def _posix_writer_from_fd(
    fd: int,
    *,
    raw_root: Path,
    output: Path,
    file_name: str,
    locked: list[_PosixDirectoryHandle],
) -> OwnedLockedRawFileWriter:
    try:
        file_stat = os.fstat(fd)
        raw_identity = _require_posix_regular_file(file_stat)
        identity = _stable_identity(raw_identity)
        link_count = int(file_stat.st_nlink)
        if link_count != 1:
            raise StableRawStorageError("unsafe")
        path_stat = os.stat(
            file_name,
            dir_fd=locked[-1].fd,
            follow_symlinks=False,
        )
        if (
            _require_posix_regular_file(path_stat) != raw_identity
            or _fd_stable_state(path_stat) != _fd_stable_state(file_stat)
        ):
            raise StableRawStorageError("changed")
        _revalidate_posix_directories(locked)
        file = os.fdopen(fd, "w+b", buffering=0)
    except BaseException:
        os.close(fd)
        raise
    return OwnedLockedRawFileWriter(
        file,
        raw_root=raw_root,
        canonical_ref=str(output),
        identity=identity,
        link_count=link_count,
        parent_identity=_stable_identity(locked[-1].identity),
    )


def _open_posix_owned_writer(
    raw_root: Path,
    file_path: Path,
    *,
    create_immediate_parent_exclusive: bool,
    expected_parent_identity: StableRawFileIdentity | None,
) -> OwnedLockedRawFileWriter:
    writer: OwnedLockedRawFileWriter | None = None
    try:
        parent_target = (
            file_path.parent
            if create_immediate_parent_exclusive
            else file_path
        )
        with _locked_posix_parents(
            raw_root,
            parent_target,
            create=False,
        ) as (_, parent_name, locked):
            output = _lexical_absolute(file_path)
            if create_immediate_parent_exclusive:
                try:
                    os.mkdir(
                        parent_name,
                        0o700,
                        dir_fd=locked[-1].fd,
                    )
                except FileExistsError as exc:
                    raise StableRawStorageError("conflict") from exc
                locked.append(
                    _open_posix_child_directory(
                        locked[-1],
                        parent_name,
                        output.parent,
                    )
                )
            parent_identity = _stable_identity(locked[-1].identity)
            if (
                expected_parent_identity is not None
                and parent_identity != expected_parent_identity
            ):
                raise StableRawStorageError("changed")
            try:
                fd = _open_posix_file_fd(
                    locked[-1].fd,
                    output.name,
                    create_new=True,
                )
            except FileExistsError as exc:
                raise StableRawStorageError("conflict") from exc
            writer = _posix_writer_from_fd(
                fd,
                raw_root=_lexical_absolute(raw_root),
                output=output,
                file_name=output.name,
                locked=locked,
            )
        return writer
    except BaseException:
        if writer is not None:
            writer.close()
        raise


def _persist_windows_locked_raw_file(
    raw_root: Path,
    file_path: Path,
    content: bytes,
    *,
    strict_new: bool = False,
) -> tuple[int, str, str]:
    with _locked_windows_parents(
        raw_root,
        file_path,
        create=not strict_new,
    ) as (output, locked):
        try:
            handle = _open_windows_file_handle(output, create_new=True)
        except FileExistsError as exc:
            if strict_new:
                raise StableRawStorageError("conflict") from exc
            handle = _open_windows_file_handle(output, create_new=False)
            size, digest, matches = _use_windows_file_handle(
                handle,
                output,
                locked,
                write_content=None,
                expected_content=content,
            )
            if (
                not matches
                or digest != hashlib.sha256(content).hexdigest()
                or size != len(content)
            ):
                raise StableRawStorageError("conflict")
            return size, digest, str(output.resolve(strict=True))

        if strict_new and _handle_link_count(handle) != 1:
            _close_windows_handle(handle)
            raise StableRawStorageError("unsafe")
        size, digest, matches = _use_windows_file_handle(
            handle,
            output,
            locked,
            write_content=content,
            expected_content=content,
        )
        if not matches:
            raise StableRawStorageError("changed")
        return size, digest, str(output.resolve(strict=True))


def _hash_windows_locked_raw_file(
    raw_root: Path,
    file_path: Path,
    *,
    max_bytes: int | None = None,
    expected_identity: StableRawFileIdentity | None = None,
    required_link_count: int | None = None,
) -> tuple[int, str, str]:
    with _locked_windows_raw_file_snapshot(
        raw_root,
        file_path,
        max_bytes=max_bytes,
    ) as snapshot:
        _require_snapshot_constraints(
            snapshot,
            expected_identity=expected_identity,
            expected_parent_identity=None,
            required_link_count=required_link_count,
        )
        return (
            snapshot.size,
            snapshot.sha256,
            snapshot.canonical_ref,
        )


def _persist_posix_locked_raw_file(
    raw_root: Path,
    file_path: Path,
    content: bytes,
    *,
    strict_new: bool = False,
) -> tuple[int, str, str]:
    with _locked_posix_parents(
        raw_root,
        file_path,
        create=not strict_new,
    ) as (output, file_name, locked):
        parent_fd = locked[-1].fd
        try:
            fd = _open_posix_file_fd(
                parent_fd,
                file_name,
                create_new=True,
            )
        except FileExistsError as exc:
            if strict_new:
                raise StableRawStorageError("conflict") from exc
            fd = _open_posix_file_fd(
                parent_fd,
                file_name,
                create_new=False,
            )
            size, digest, matches = _use_posix_file_fd(
                fd,
                parent_fd,
                file_name,
                locked,
                write_content=None,
                expected_content=content,
            )
            if (
                not matches
                or digest != hashlib.sha256(content).hexdigest()
                or size != len(content)
            ):
                raise StableRawStorageError("conflict")
            return size, digest, str(output)

        if strict_new and int(os.fstat(fd).st_nlink) != 1:
            os.close(fd)
            raise StableRawStorageError("unsafe")
        size, digest, matches = _use_posix_file_fd(
            fd,
            parent_fd,
            file_name,
            locked,
            write_content=content,
            expected_content=content,
        )
        if not matches:
            raise StableRawStorageError("changed")
        return size, digest, str(output)


def _hash_posix_locked_raw_file(
    raw_root: Path,
    file_path: Path,
    *,
    max_bytes: int | None = None,
    expected_identity: StableRawFileIdentity | None = None,
    required_link_count: int | None = None,
) -> tuple[int, str, str]:
    with _locked_posix_raw_file_snapshot(
        raw_root,
        file_path,
        max_bytes=max_bytes,
    ) as snapshot:
        _require_snapshot_constraints(
            snapshot,
            expected_identity=expected_identity,
            expected_parent_identity=None,
            required_link_count=required_link_count,
        )
        return (
            snapshot.size,
            snapshot.sha256,
            snapshot.canonical_ref,
        )


def _assert_publication_targets_absent(
    raw_root: Path,
    final_path: Path,
    stage_path: Path,
    *,
    expected_parent_identity: StableRawFileIdentity | None = None,
) -> None:
    if final_path.parent != stage_path.parent:
        raise StableRawStorageError("unsafe")
    if _windows_backend_available():
        with _locked_windows_parents(
            raw_root,
            final_path,
            create=False,
        ) as (output, locked):
            if (
                expected_parent_identity is not None
                and _stable_identity(locked[-1][2])
                != expected_parent_identity
            ):
                raise StableRawStorageError("changed")
            forbidden = {
                final_path.name.casefold(),
                stage_path.name.casefold(),
            }
            if any(
                child.name.casefold() in forbidden
                for child in output.parent.iterdir()
            ):
                raise StableRawStorageError("conflict")
            _revalidate_windows_directories(locked)
        return
    if _supports_posix_anchored_io():
        with _locked_posix_parents(
            raw_root,
            final_path,
            create=False,
        ) as (_, _, locked):
            if (
                expected_parent_identity is not None
                and _stable_identity(locked[-1].identity)
                != expected_parent_identity
            ):
                raise StableRawStorageError("changed")
            for name in (final_path.name, stage_path.name):
                try:
                    os.stat(
                        name,
                        dir_fd=locked[-1].fd,
                        follow_symlinks=False,
                    )
                except FileNotFoundError:
                    continue
                except OSError as exc:
                    raise StableRawStorageError("unsafe") from exc
                raise StableRawStorageError("conflict")
            _revalidate_posix_directories(locked)
        return
    raise StableRawStorageError("unsupported")


def _assert_publication_stage_absent(
    raw_root: Path,
    final_path: Path,
    stage_path: Path,
    *,
    expected_parent_identity: StableRawFileIdentity | None,
) -> None:
    if _windows_backend_available():
        with _locked_windows_parents(
            raw_root,
            final_path,
            create=False,
        ) as (output, locked):
            if (
                expected_parent_identity is not None
                and _stable_identity(locked[-1][2])
                != expected_parent_identity
            ):
                raise StableRawStorageError("changed")
            if any(
                child.name.casefold() == stage_path.name.casefold()
                for child in output.parent.iterdir()
            ):
                raise StableRawStorageError("conflict")
            _revalidate_windows_directories(locked)
        return
    if _supports_posix_anchored_io():
        with _locked_posix_parents(
            raw_root,
            final_path,
            create=False,
        ) as (_, _, locked):
            if (
                expected_parent_identity is not None
                and _stable_identity(locked[-1].identity)
                != expected_parent_identity
            ):
                raise StableRawStorageError("changed")
            try:
                os.stat(
                    stage_path.name,
                    dir_fd=locked[-1].fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise StableRawStorageError("unsafe") from exc
            else:
                raise StableRawStorageError("conflict")
            _revalidate_posix_directories(locked)
        return
    raise StableRawStorageError("unsupported")


def _atomic_no_replace_windows(
    raw_root: Path,
    stage_path: Path,
    final_path: Path,
    *,
    expected_identity: StableRawFileIdentity,
    expected_parent_identity: StableRawFileIdentity | None,
) -> None:
    with _locked_windows_parents(
        raw_root,
        final_path,
        create=False,
    ) as (output, locked):
        if (
            expected_parent_identity is not None
            and _stable_identity(locked[-1][2])
            != expected_parent_identity
        ):
            raise StableRawStorageError("changed")
        try:
            os.lstat(output)
        except FileNotFoundError:
            pass
        else:
            raise StableRawStorageError("conflict")
        handle = _open_windows_move_handle(stage_path)
        try:
            identity = _stable_identity(_handle_identity(handle))
            if (
                identity != expected_identity
                or _handle_link_count(handle) != 1
            ):
                raise StableRawStorageError("changed")
            if not _move_file_ex(
                str(stage_path),
                str(output),
                _MOVEFILE_WRITE_THROUGH,
            ):
                move_error = ctypes.get_last_error()
                try:
                    os.lstat(output)
                except FileNotFoundError:
                    raise StableRawStorageError("io") from OSError(
                        move_error,
                        "atomic no-replace move failed",
                    )
                raise StableRawStorageError("conflict")
            if (
                _stable_identity(
                    _validate_windows_handle(
                        handle,
                        output,
                        directory=False,
                    )
                )
                != identity
                or _handle_link_count(handle) != 1
            ):
                raise StableRawStorageError("changed")
            _revalidate_windows_directories(locked)
        finally:
            _close_windows_handle(handle)


def _renameat2_no_replace(
    parent_fd: int,
    stage_name: str,
    final_name: str,
) -> None:
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except AttributeError as exc:
        raise StableRawStorageError("unsupported") from exc
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        parent_fd,
        os.fsencode(stage_name),
        parent_fd,
        os.fsencode(final_name),
        1,
    )
    if result == 0:
        return
    error = ctypes.get_errno()
    if error == errno.EEXIST:
        raise StableRawStorageError("conflict")
    if error in {errno.ENOSYS, errno.EINVAL}:
        raise StableRawStorageError("unsupported")
    raise StableRawStorageError("io")


def _atomic_no_replace_posix(
    raw_root: Path,
    stage_path: Path,
    final_path: Path,
    *,
    expected_identity: StableRawFileIdentity,
    expected_parent_identity: StableRawFileIdentity | None,
) -> None:
    with _locked_posix_parents(
        raw_root,
        final_path,
        create=False,
    ) as (_, final_name, locked):
        if (
            expected_parent_identity is not None
            and _stable_identity(locked[-1].identity)
            != expected_parent_identity
        ):
            raise StableRawStorageError("changed")
        parent_fd = locked[-1].fd
        try:
            os.stat(
                final_name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            raise StableRawStorageError("conflict")
        stage_fd = _open_posix_file_fd(
            parent_fd,
            stage_path.name,
            create_new=False,
        )
        try:
            stage_stat = os.fstat(stage_fd)
            if (
                _stable_identity(_require_posix_regular_file(stage_stat))
                != expected_identity
                or int(stage_stat.st_nlink) != 1
            ):
                raise StableRawStorageError("changed")
            _renameat2_no_replace(
                parent_fd,
                stage_path.name,
                final_name,
            )
            final_stat = os.stat(
                final_name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
            if (
                _stable_identity(_require_posix_regular_file(final_stat))
                != expected_identity
                or int(final_stat.st_nlink) != 1
            ):
                raise StableRawStorageError("changed")
            os.fsync(parent_fd)
            _revalidate_posix_directories(locked)
        finally:
            os.close(stage_fd)


def open_new_locked_raw_file_writer(
    raw_root: Path,
    file_path: Path,
    *,
    create_immediate_parent_exclusive: bool = False,
    expected_parent_identity: StableRawFileIdentity | None = None,
) -> OwnedLockedRawFileWriter:
    if _windows_backend_available():
        return _open_windows_owned_writer(
            raw_root,
            file_path,
            create_immediate_parent_exclusive=(
                create_immediate_parent_exclusive
            ),
            expected_parent_identity=expected_parent_identity,
        )
    if _supports_posix_anchored_io():
        return _open_posix_owned_writer(
            raw_root,
            file_path,
            create_immediate_parent_exclusive=(
                create_immediate_parent_exclusive
            ),
            expected_parent_identity=expected_parent_identity,
        )
    raise StableRawStorageError("unsupported")


def snapshot_open_locked_raw_file(
    writer: OwnedLockedRawFileWriter,
    *,
    max_bytes: int,
    expected_identity: StableRawFileIdentity | None = None,
    expected_parent_identity: StableRawFileIdentity | None = None,
    required_link_count: int | None = None,
) -> LockedRawFileSnapshot:
    if not isinstance(writer, OwnedLockedRawFileWriter) or writer.closed:
        raise StableRawStorageError("unsafe")
    writer.flush()
    os.fsync(writer.fileno())
    output = Path(writer._canonical_ref)
    if _windows_backend_available():
        with _locked_windows_parents(
            writer._raw_root,
            output,
            create=False,
        ) as (locked_output, locked):
            identity, link_count, _, size, digest = (
                _read_windows_snapshot_state(
                    writer.fileno(),
                    locked_output,
                    locked,
                    max_bytes=max_bytes,
                )
            )
    elif _supports_posix_anchored_io():
        with _locked_posix_parents(
            writer._raw_root,
            output,
            create=False,
        ) as (locked_output, file_name, locked):
            identity, link_count, _, size, digest = (
                _read_posix_snapshot_state(
                    writer.fileno(),
                    locked[-1].fd,
                    file_name,
                    locked,
                    max_bytes=max_bytes,
                )
            )
    else:
        raise StableRawStorageError("unsupported")
    snapshot = LockedRawFileSnapshot(
        canonical_ref=str(locked_output.resolve(strict=True)),
        size=size,
        sha256=digest,
        identity=identity,
        link_count=link_count,
        parent_identity=(
            _stable_identity(locked[-1][2])
            if _windows_backend_available()
            else _stable_identity(locked[-1].identity)
        ),
    )
    _require_snapshot_constraints(
        snapshot,
        expected_identity=expected_identity or writer.identity,
        expected_parent_identity=(
            expected_parent_identity or writer.parent_identity
        ),
        required_link_count=required_link_count,
    )
    if identity != writer.identity:
        raise StableRawStorageError("changed")
    return snapshot


def publish_atomic_strict_new_locked_raw_file(
    raw_root: Path,
    file_path: Path,
    content: bytes,
    *,
    max_bytes: int,
    expected_parent_identity: StableRawFileIdentity | None = None,
) -> LockedRawFileSnapshot:
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    if (
        isinstance(max_bytes, bool)
        or not isinstance(max_bytes, int)
        or max_bytes < 0
    ):
        raise ValueError("max_bytes must be a non-negative integer")
    if len(content) > max_bytes:
        raise StableRawStorageError("oversized")
    final_path = _lexical_absolute(file_path)
    stage_path = final_path.with_name(f".{final_path.name}.stage")
    _assert_publication_targets_absent(
        raw_root,
        final_path,
        stage_path,
        expected_parent_identity=expected_parent_identity,
    )
    writer = open_new_locked_raw_file_writer(
        raw_root,
        stage_path,
        expected_parent_identity=expected_parent_identity,
    )
    stage_snapshot: LockedRawFileSnapshot | None = None
    try:
        offset = 0
        while offset < len(content):
            written = writer.write(content[offset:])
            if written is None or written <= 0:
                raise StableRawStorageError("io")
            offset += written
        writer.flush()
        os.fsync(writer.fileno())
        stage_snapshot = snapshot_open_locked_raw_file(
            writer,
            max_bytes=max_bytes,
            expected_identity=writer.identity,
            expected_parent_identity=(
                expected_parent_identity or writer.parent_identity
            ),
            required_link_count=1,
        )
        if (
            stage_snapshot.size != len(content)
            or stage_snapshot.sha256
            != hashlib.sha256(content).hexdigest()
        ):
            raise StableRawStorageError("changed")
    finally:
        writer.close()
    if stage_snapshot is None:  # pragma: no cover - defensive narrowing
        raise StableRawStorageError("io")
    if _windows_backend_available():
        _atomic_no_replace_windows(
            _lexical_absolute(raw_root),
            stage_path,
            final_path,
            expected_identity=writer.identity,
            expected_parent_identity=(
                expected_parent_identity or writer.parent_identity
            ),
        )
    elif _supports_posix_anchored_io():
        _atomic_no_replace_posix(
            _lexical_absolute(raw_root),
            stage_path,
            final_path,
            expected_identity=writer.identity,
            expected_parent_identity=(
                expected_parent_identity or writer.parent_identity
            ),
        )
    else:
        raise StableRawStorageError("unsupported")
    with locked_raw_file_snapshot(
        raw_root,
        final_path,
        max_bytes=max_bytes,
        expected_identity=writer.identity,
        expected_parent_identity=(
            expected_parent_identity or writer.parent_identity
        ),
        required_link_count=1,
    ) as final_snapshot:
        if (
            final_snapshot.size != stage_snapshot.size
            or final_snapshot.sha256 != stage_snapshot.sha256
        ):
            raise StableRawStorageError("changed")
        _assert_publication_stage_absent(
            raw_root,
            final_path,
            stage_path,
            expected_parent_identity=(
                expected_parent_identity or writer.parent_identity
            ),
        )
        return final_snapshot


@contextmanager
def locked_raw_file_snapshot(
    raw_root: Path,
    file_path: Path,
    *,
    max_bytes: int | None = None,
    expected_identity: StableRawFileIdentity | None = None,
    expected_parent_identity: StableRawFileIdentity | None = None,
    required_link_count: int | None = None,
) -> Iterator[LockedRawFileSnapshot]:
    if _windows_backend_available():
        with _locked_windows_raw_file_snapshot(
            raw_root,
            file_path,
            max_bytes=max_bytes,
        ) as snapshot:
            _require_snapshot_constraints(
                snapshot,
                expected_identity=expected_identity,
                expected_parent_identity=expected_parent_identity,
                required_link_count=required_link_count,
            )
            yield snapshot
        return
    if _supports_posix_anchored_io():
        with _locked_posix_raw_file_snapshot(
            raw_root,
            file_path,
            max_bytes=max_bytes,
        ) as snapshot:
            _require_snapshot_constraints(
                snapshot,
                expected_identity=expected_identity,
                expected_parent_identity=expected_parent_identity,
                required_link_count=required_link_count,
            )
            yield snapshot
        return
    raise StableRawStorageError("unsupported")


def persist_locked_raw_file(
    raw_root: Path,
    file_path: Path,
    content: bytes,
    *,
    strict_new: bool = False,
) -> tuple[int, str, str]:
    if _windows_backend_available():
        if strict_new:
            return _persist_windows_locked_raw_file(
                raw_root,
                file_path,
                content,
                strict_new=True,
            )
        return _persist_windows_locked_raw_file(
            raw_root,
            file_path,
            content,
        )
    if _supports_posix_anchored_io():
        if strict_new:
            return _persist_posix_locked_raw_file(
                raw_root,
                file_path,
                content,
                strict_new=True,
            )
        return _persist_posix_locked_raw_file(
            raw_root,
            file_path,
            content,
        )
    raise StableRawStorageError("unsupported")


def hash_locked_raw_file(
    raw_root: Path,
    file_path: Path,
    *,
    max_bytes: int | None = None,
    expected_identity: StableRawFileIdentity | None = None,
    required_link_count: int | None = None,
) -> tuple[int, str, str]:
    if _windows_backend_available():
        if (
            max_bytes is not None
            or expected_identity is not None
            or required_link_count is not None
        ):
            return _hash_windows_locked_raw_file(
                raw_root,
                file_path,
                max_bytes=max_bytes,
                expected_identity=expected_identity,
                required_link_count=required_link_count,
            )
        return _hash_windows_locked_raw_file(raw_root, file_path)
    if _supports_posix_anchored_io():
        if (
            max_bytes is not None
            or expected_identity is not None
            or required_link_count is not None
        ):
            return _hash_posix_locked_raw_file(
                raw_root,
                file_path,
                max_bytes=max_bytes,
                expected_identity=expected_identity,
                required_link_count=required_link_count,
            )
        return _hash_posix_locked_raw_file(raw_root, file_path)
    raise StableRawStorageError("unsupported")
