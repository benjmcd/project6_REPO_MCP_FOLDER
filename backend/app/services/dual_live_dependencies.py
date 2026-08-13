from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import stat
import sys
import sysconfig
from importlib import metadata
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Callable, Mapping, NoReturn, Protocol, Sequence, cast


DEPENDENCY_SET_SCHEMA_ID = "project6.dual_live_dependency_set.v1"
DEPENDENCY_PROVENANCE_NONCLAIM = (
    "same-version package bytes and RECORD rewritten by the owning account "
    "are not independently authenticated"
)
_DEPENDENCY_ERROR = "dual_live_dependency_provenance_invalid"
_LOCK_PATH = Path(__file__).resolve().parents[2] / "requirements.lock.txt"
_LOCK_SHA256 = "bfbe472253f2b1350222ef4d27de075dbda913bef33ac33dad34267720429a02"
_EXPECTED_DEPENDENCY_VERSIONS: Mapping[str, str] = MappingProxyType(
    {
        "certifi": "2026.6.17",
        "chardet": "7.4.3",
        "charset-normalizer": "3.4.7",
        "idna": "3.18",
        "requests": "2.34.2",
        "urllib3": "2.7.0",
    }
)
_DEPENDENCY_IMPORT_ROOTS: Mapping[str, str] = MappingProxyType(
    {
        "certifi": "certifi",
        "chardet": "chardet",
        "charset-normalizer": "charset_normalizer",
        "idna": "idna",
        "requests": "requests",
        "urllib3": "urllib3",
    }
)
_MAX_LOCK_BYTES = 1024 * 1024
_MAX_DISTRIBUTION_FILES = 10_000
_MAX_DEPENDENCY_FILE_BYTES = 32 * 1024 * 1024
_MAX_DEPENDENCY_SET_BYTES = 128 * 1024 * 1024
_WINDOWS_REPARSE_POINT = 0x400


class DualLiveDependencyError(RuntimeError):
    __slots__ = ("code",)

    def __init__(self) -> None:
        self.code = _DEPENDENCY_ERROR
        super().__init__(self.code)


class _RecordHash(Protocol):
    @property
    def mode(self) -> str: ...

    @property
    def value(self) -> str: ...


class _RecordPath(Protocol):
    @property
    def hash(self) -> _RecordHash | None: ...

    def __str__(self) -> str: ...


class _Distribution(Protocol):
    @property
    def files(self) -> Sequence[_RecordPath] | None: ...

    @property
    def metadata(self) -> Mapping[str, str]: ...

    @property
    def version(self) -> str: ...

    def locate_file(self, path: object) -> os.PathLike[str] | str: ...


def _fail() -> NoReturn:
    raise DualLiveDependencyError


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DualLiveDependencyError from exc


def _canonical_distribution_name(value: object) -> str:
    if not isinstance(value, str) or not value:
        _fail()
    canonical = re.sub(r"[-_.]+", "-", value).lower()
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", canonical) is None:
        _fail()
    return canonical


def _is_reparse_or_symlink(path: Path) -> bool:
    try:
        metadata_value = os.lstat(path)
    except OSError as exc:
        raise DualLiveDependencyError from exc
    return stat.S_ISLNK(metadata_value.st_mode) or bool(
        getattr(metadata_value, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT
    )


def _read_regular_file(path: Path, *, maximum_bytes: int) -> bytes:
    try:
        if _is_reparse_or_symlink(path):
            _fail()
        metadata_value = os.lstat(path)
        if (
            not stat.S_ISREG(metadata_value.st_mode)
            or metadata_value.st_size < 0
            or metadata_value.st_size > maximum_bytes
        ):
            _fail()
        with path.open("rb", buffering=0) as source:
            content = source.read(maximum_bytes + 1)
        if len(content) != metadata_value.st_size or len(content) > maximum_bytes:
            _fail()
        current_metadata = os.lstat(path)
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(
            getattr(current_metadata, field) != getattr(metadata_value, field)
            for field in stable_fields
        ):
            _fail()
        return content
    except DualLiveDependencyError:
        raise
    except OSError as exc:
        raise DualLiveDependencyError from exc


def _record_digest(value: object) -> bytes:
    encoded = getattr(value, "value", None)
    if (
        value is None
        or getattr(value, "mode", None) != "sha256"
        or not isinstance(encoded, str)
    ):
        _fail()
    if re.fullmatch(r"[A-Za-z0-9_-]{43}", encoded) is None:
        _fail()
    try:
        decoded = base64.b64decode(
            (encoded + "=").encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
    except (UnicodeEncodeError, ValueError) as exc:
        raise DualLiveDependencyError from exc
    if (
        len(decoded) != hashlib.sha256().digest_size
        or base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
        != encoded
    ):
        _fail()
    return decoded


def _canonical_record_path(value: object, *, import_root: str) -> str | None:
    raw = str(value).replace("\\", "/")
    path = PurePosixPath(raw)
    if (
        not raw
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        _fail()
    if not path.parts or path.parts[0] != import_root:
        return None
    if len(path.parts) > 64 or any(len(part) > 255 for part in path.parts):
        _fail()
    return path.as_posix()


def _distribution_manifest(
    distribution: _Distribution,
    *,
    expected_name: str,
    expected_version: str,
    approved_roots: frozenset[Path],
) -> tuple[dict[str, object], int]:
    if (
        _canonical_distribution_name(distribution.metadata.get("Name"))
        != expected_name
        or distribution.version != expected_version
        or type(distribution.files) not in {list, tuple}
    ):
        _fail()
    files = distribution.files
    assert files is not None
    if not files or len(files) > _MAX_DISTRIBUTION_FILES:
        _fail()
    import_root = _DEPENDENCY_IMPORT_ROOTS[expected_name]
    try:
        distribution_root = Path(distribution.locate_file(".")).absolute()
        resolved_root = distribution_root.resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise DualLiveDependencyError from exc
    if (
        resolved_root != distribution_root
        or resolved_root not in approved_roots
        or not resolved_root.is_dir()
        or _is_reparse_or_symlink(resolved_root)
    ):
        _fail()

    package_root = resolved_root / import_root
    try:
        if (
            package_root.resolve(strict=True) != package_root
            or not package_root.is_dir()
            or _is_reparse_or_symlink(package_root)
        ):
            _fail()
    except (OSError, RuntimeError) as exc:
        raise DualLiveDependencyError from exc

    manifest_files: list[dict[str, str]] = []
    recorded_paths: set[str] = set()
    total_bytes = 0
    for record_path in files:
        canonical_path = _canonical_record_path(
            record_path,
            import_root=import_root,
        )
        if canonical_path is None:
            continue
        case_key = canonical_path.casefold()
        if case_key in recorded_paths:
            _fail()
        recorded_paths.add(case_key)
        try:
            located = Path(distribution.locate_file(record_path)).absolute()
            resolved = located.resolve(strict=True)
            resolved.relative_to(package_root)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise DualLiveDependencyError from exc
        if located != resolved:
            _fail()
        content = _read_regular_file(
            resolved,
            maximum_bytes=_MAX_DEPENDENCY_FILE_BYTES,
        )
        total_bytes += len(content)
        if total_bytes > _MAX_DEPENDENCY_SET_BYTES:
            _fail()
        digest = hashlib.sha256(content).digest()
        if digest != _record_digest(record_path.hash):
            _fail()
        manifest_files.append(
            {
                "path": canonical_path,
                "sha256": digest.hex(),
            }
        )

    discovered_paths: set[str] = set()
    discovered_count = 0
    for directory, child_directories, child_files in os.walk(
        package_root,
        topdown=True,
        followlinks=False,
    ):
        current = Path(directory)
        if current != package_root and _is_reparse_or_symlink(current):
            _fail()
        retained_directories: list[str] = []
        for child in child_directories:
            if child == "__pycache__":
                continue
            child_path = current / child
            if _is_reparse_or_symlink(child_path):
                _fail()
            retained_directories.append(child)
        child_directories[:] = retained_directories
        for child in child_files:
            if child.endswith((".pyc", ".pyo")):
                continue
            discovered_count += 1
            if discovered_count > _MAX_DISTRIBUTION_FILES:
                _fail()
            path = current / child
            if _is_reparse_or_symlink(path):
                _fail()
            try:
                relative = path.relative_to(resolved_root).as_posix()
            except ValueError as exc:
                raise DualLiveDependencyError from exc
            discovered_paths.add(relative.casefold())
    if not manifest_files or discovered_paths != recorded_paths:
        _fail()
    manifest_files.sort(key=lambda item: item["path"])
    return (
        {
            "files": manifest_files,
            "name": expected_name,
            "version": expected_version,
        },
        total_bytes,
    )


def _verify_dependency_set(
    *,
    lock_path: Path,
    distribution_provider: Callable[[str], Sequence[_Distribution]],
    approved_distribution_roots: Sequence[Path],
    python_version: tuple[int, int],
    dont_write_bytecode: bool,
    pycache_prefix: str | None,
) -> str:
    if (
        not isinstance(lock_path, Path)
        or not callable(distribution_provider)
        or type(approved_distribution_roots) not in {list, tuple}
        or not approved_distribution_roots
        or len(approved_distribution_roots) > 2
        or python_version != (3, 12)
        or dont_write_bytecode is not True
        or pycache_prefix != "NUL"
    ):
        _fail()
    approved_roots: set[Path] = set()
    for root in approved_distribution_roots:
        try:
            absolute_root = root.absolute()
            resolved_root = absolute_root.resolve(strict=True)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise DualLiveDependencyError from exc
        if (
            resolved_root != absolute_root
            or not resolved_root.is_dir()
            or _is_reparse_or_symlink(resolved_root)
        ):
            _fail()
        approved_roots.add(resolved_root)
    if not approved_roots or len(approved_roots) > 2:
        _fail()
    lock_bytes = _read_regular_file(lock_path, maximum_bytes=_MAX_LOCK_BYTES)
    if hashlib.sha256(lock_bytes).hexdigest() != _LOCK_SHA256:
        _fail()
    try:
        lock_text = lock_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DualLiveDependencyError from exc
    lock_lines = lock_text.splitlines()
    for name, version in _EXPECTED_DEPENDENCY_VERSIONS.items():
        if lock_lines.count(f"{name}=={version} \\") != 1:
            _fail()

    manifests: list[dict[str, object]] = []
    total_bytes = 0
    for name, version in _EXPECTED_DEPENDENCY_VERSIONS.items():
        try:
            candidates = distribution_provider(name)
        except BaseException as exc:
            raise DualLiveDependencyError from exc
        if type(candidates) not in {list, tuple} or len(candidates) != 1:
            _fail()
        manifest, distribution_bytes = _distribution_manifest(
            candidates[0],
            expected_name=name,
            expected_version=version,
            approved_roots=frozenset(approved_roots),
        )
        total_bytes += distribution_bytes
        if total_bytes > _MAX_DEPENDENCY_SET_BYTES:
            _fail()
        manifests.append(manifest)
    payload = {
        "dependencies": manifests,
        "lock_sha256": _LOCK_SHA256,
        "python_version": "3.12",
        "schema_id": DEPENDENCY_SET_SCHEMA_ID,
    }
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def verify_dual_live_dependencies() -> str:
    """Verify the exact reviewed requests stack without importing its packages."""

    runtime_paths = sysconfig.get_paths()
    approved_roots = tuple(
        dict.fromkeys(
            Path(runtime_paths[name])
            for name in ("purelib", "platlib")
            if isinstance(runtime_paths.get(name), str)
        )
    )
    return _verify_dependency_set(
        lock_path=_LOCK_PATH,
        distribution_provider=lambda name: cast(
            Sequence[_Distribution],
            tuple(metadata.distributions(name=name)),
        ),
        approved_distribution_roots=approved_roots,
        python_version=(sys.version_info.major, sys.version_info.minor),
        dont_write_bytecode=sys.dont_write_bytecode,
        pycache_prefix=sys.pycache_prefix,
    )
