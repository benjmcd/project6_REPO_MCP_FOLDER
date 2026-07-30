from __future__ import annotations

from contextlib import contextmanager
import ctypes
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
from typing import Iterator


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
_CREATE_NEW = 1
_OPEN_EXISTING = 3
_ERROR_FILE_EXISTS = 80
_ERROR_ALREADY_EXISTS = 183
_FILE_ATTRIBUTE_TAG_INFO_CLASS = 9


@dataclass(frozen=True)
class LockedRawFileSnapshot:
    canonical_ref: str
    size: int
    sha256: str


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


def _handle_identity(handle: int) -> tuple[int, int]:
    info = _ByHandleFileInformation()
    if not _get_file_information(handle, ctypes.byref(info)):
        raise StableRawStorageError("io")
    file_index = (int(info.FileIndexHigh) << 32) | int(info.FileIndexLow)
    return int(info.VolumeSerialNumber), file_index


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
    finally:
        close_error: StableRawStorageError | None = None
        for handle, _, _ in reversed(locked):
            try:
                _close_windows_handle(handle)
            except StableRawStorageError as exc:
                close_error = close_error or exc
        if close_error is not None:
            raise close_error


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
) -> tuple[int, int, int, int]:
    return (
        *_fd_identity(file_stat),
        int(file_stat.st_size),
        int(file_stat.st_mtime_ns),
    )


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
    finally:
        close_error: OSError | None = None
        for directory in reversed(locked):
            try:
                os.close(directory.fd)
            except OSError as exc:
                close_error = close_error or exc
        if close_error is not None:
            raise StableRawStorageError("io") from close_error


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
) -> tuple[int, str, bool]:
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    size = 0
    matches = True
    while True:
        chunk = os.read(fd, _READ_CHUNK_SIZE)
        if not chunk:
            break
        if expected_content is not None:
            matches = matches and (
                chunk == expected_content[size : size + len(chunk)]
            )
        size += len(chunk)
        digest.update(chunk)
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
) -> tuple[tuple[int, int], tuple[int, int, int, int], int, str]:
    before = os.fstat(fd)
    handle = msvcrt.get_osfhandle(fd)
    handle_identity = _validate_windows_handle(
        handle,
        path,
        directory=False,
    )
    size, digest, _ = _hash_fd(fd)
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
    ):
        raise StableRawStorageError("changed")
    _revalidate_windows_directories(locked)
    return handle_identity, _fd_stable_state(after), size, digest


def _read_posix_snapshot_state(
    fd: int,
    parent_fd: int,
    file_name: str,
    locked: list[_PosixDirectoryHandle],
) -> tuple[tuple[int, int, int, int], int, str]:
    before = os.fstat(fd)
    before_identity = _require_posix_regular_file(before)
    size, digest, _ = _hash_fd(fd)
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
    return _fd_stable_state(after), size, digest


@contextmanager
def _locked_windows_raw_file_snapshot(
    raw_root: Path,
    file_path: Path,
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
        try:
            identity, stable_state, size, digest = (
                _read_windows_snapshot_state(fd, output, locked)
            )
            snapshot = LockedRawFileSnapshot(
                canonical_ref=str(output.resolve(strict=True)),
                size=size,
                sha256=digest,
            )
            try:
                yield snapshot
            finally:
                (
                    exit_identity,
                    exit_state,
                    exit_size,
                    exit_digest,
                ) = _read_windows_snapshot_state(
                    fd,
                    output,
                    locked,
                )
                if (
                    exit_identity != identity
                    or exit_state != stable_state
                    or exit_size != size
                    or exit_digest != digest
                ):
                    raise StableRawStorageError("changed")
        except OSError as exc:
            raise StableRawStorageError("changed") from exc
        finally:
            os.close(fd)


@contextmanager
def _locked_posix_raw_file_snapshot(
    raw_root: Path,
    file_path: Path,
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
        try:
            stable_state, size, digest = _read_posix_snapshot_state(
                fd,
                parent_fd,
                file_name,
                locked,
            )
            snapshot = LockedRawFileSnapshot(
                canonical_ref=str(output.resolve(strict=True)),
                size=size,
                sha256=digest,
            )
            try:
                yield snapshot
            finally:
                exit_state, exit_size, exit_digest = (
                    _read_posix_snapshot_state(
                        fd,
                        parent_fd,
                        file_name,
                        locked,
                    )
                )
                if (
                    exit_state != stable_state
                    or exit_size != size
                    or exit_digest != digest
                ):
                    raise StableRawStorageError("changed")
        except OSError as exc:
            raise StableRawStorageError("changed") from exc
        finally:
            os.close(fd)


def _persist_windows_locked_raw_file(
    raw_root: Path,
    file_path: Path,
    content: bytes,
) -> tuple[int, str, str]:
    with _locked_windows_parents(
        raw_root,
        file_path,
        create=True,
    ) as (output, locked):
        try:
            handle = _open_windows_file_handle(output, create_new=True)
        except FileExistsError:
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
) -> tuple[int, str, str]:
    with _locked_windows_raw_file_snapshot(
        raw_root,
        file_path,
    ) as snapshot:
        return (
            snapshot.size,
            snapshot.sha256,
            snapshot.canonical_ref,
        )


def _persist_posix_locked_raw_file(
    raw_root: Path,
    file_path: Path,
    content: bytes,
) -> tuple[int, str, str]:
    with _locked_posix_parents(
        raw_root,
        file_path,
        create=True,
    ) as (output, file_name, locked):
        parent_fd = locked[-1].fd
        try:
            fd = _open_posix_file_fd(
                parent_fd,
                file_name,
                create_new=True,
            )
        except FileExistsError:
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
) -> tuple[int, str, str]:
    with _locked_posix_raw_file_snapshot(
        raw_root,
        file_path,
    ) as snapshot:
        return (
            snapshot.size,
            snapshot.sha256,
            snapshot.canonical_ref,
        )


@contextmanager
def locked_raw_file_snapshot(
    raw_root: Path,
    file_path: Path,
) -> Iterator[LockedRawFileSnapshot]:
    if _windows_backend_available():
        with _locked_windows_raw_file_snapshot(
            raw_root,
            file_path,
        ) as snapshot:
            yield snapshot
        return
    if _supports_posix_anchored_io():
        with _locked_posix_raw_file_snapshot(
            raw_root,
            file_path,
        ) as snapshot:
            yield snapshot
        return
    raise StableRawStorageError("unsupported")


def persist_locked_raw_file(
    raw_root: Path,
    file_path: Path,
    content: bytes,
) -> tuple[int, str, str]:
    if _windows_backend_available():
        return _persist_windows_locked_raw_file(
            raw_root,
            file_path,
            content,
        )
    if _supports_posix_anchored_io():
        return _persist_posix_locked_raw_file(
            raw_root,
            file_path,
            content,
        )
    raise StableRawStorageError("unsupported")


def hash_locked_raw_file(
    raw_root: Path,
    file_path: Path,
) -> tuple[int, str, str]:
    if _windows_backend_available():
        return _hash_windows_locked_raw_file(raw_root, file_path)
    if _supports_posix_anchored_io():
        return _hash_posix_locked_raw_file(raw_root, file_path)
    raise StableRawStorageError("unsupported")
