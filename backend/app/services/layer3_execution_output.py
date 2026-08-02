from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import stat
from typing import Any, BinaryIO, NoReturn
import uuid

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine, URL
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings
from app.models.models import AnalysisArtifact, L3PassRun


MAX_OUTPUT_FILE_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_ARTIFACTS = 128
MAX_OUTPUT_AGGREGATE_BYTES = 256 * 1024 * 1024
CONNECTOR_ORIGIN_INTEGRITY_SCHEMA_ID = "layer3.connector_origin_integrity.v1"
CONNECTOR_OUTPUT_INTEGRITY_SCHEMA_ID = "layer3.connector_output_integrity.v1"
CONNECTOR_ORIGIN_INTEGRITY_KEY = "connector_origin_integrity_v1"
CONNECTOR_OUTPUT_INTEGRITY_KEY = "connector_output_integrity_v1"
_WINDOWS_REPARSE_POINT = int(
    getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
)
_WINDOWS_RESERVED_COMPONENTS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)


class Layer3ExecutionOutputIntegrityError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _integrity_fail(code: str, message: str) -> NoReturn:
    raise Layer3ExecutionOutputIntegrityError(code, message)


def _required_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        _integrity_fail(
            "layer3_output_binding_invalid",
            f"{field} must be one non-empty canonical string.",
        )
    return value


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _validate_local_component(component: str, *, field: str) -> None:
    normalized = component.rstrip(" .")
    stem = normalized.split(".", 1)[0].upper()
    if (
        component in {"", ".", ".."}
        or component != normalized
        or ":" in component
        or stem in _WINDOWS_RESERVED_COMPONENTS
    ):
        _integrity_fail(
            "layer3_output_binding_invalid",
            f"{field} contains an unsafe path component.",
        )


def _managed_root(root: Path, *, field: str) -> Path:
    raw = os.fspath(root)
    normalized = raw.replace("\\", "/")
    if (
        "\x00" in raw
        or not root.is_absolute()
        or normalized.startswith("//")
    ):
        _integrity_fail(
            "layer3_output_binding_invalid",
            f"{field} must be an absolute local managed root.",
        )
    canonical = _lexical_absolute(root)
    for component in canonical.parts:
        if component != canonical.anchor:
            _validate_local_component(component, field=field)
    current = Path(canonical.anchor)
    for component in canonical.parts[1:]:
        current /= component
        try:
            info = current.lstat()
        except OSError as exc:
            raise Layer3ExecutionOutputIntegrityError(
                "layer3_output_binding_invalid",
                f"{field} is missing or inaccessible.",
            ) from exc
        attributes = int(getattr(info, "st_file_attributes", 0))
        if (
            stat.S_ISLNK(info.st_mode)
            or attributes & _WINDOWS_REPARSE_POINT
            or not stat.S_ISDIR(info.st_mode)
        ):
            _integrity_fail(
                "layer3_output_binding_invalid",
                f"{field} has unsafe ancestry.",
            )
    return canonical


def _managed_storage_path(
    value: object,
    *,
    field: str,
    root: Path,
    logical_prefix: str | None = None,
) -> tuple[Path, Path]:
    raw_ref = _required_text(value, field=field)
    normalized_ref = raw_ref.replace("\\", "/")
    if (
        "\x00" in raw_ref
        or normalized_ref.startswith("//")
        or normalized_ref.startswith("/?/")
    ):
        _integrity_fail(
            "layer3_output_binding_invalid",
            f"{field} is not a managed local path.",
        )
    canonical_root = _managed_root(root, field="configured output root")
    if logical_prefix and normalized_ref.startswith(logical_prefix):
        relative = PurePosixPath(normalized_ref[len(logical_prefix) :])
        if (
            not relative.parts
            or relative.is_absolute()
            or ".." in relative.parts
        ):
            _integrity_fail(
                "layer3_output_binding_invalid",
                f"{field} escapes managed storage.",
            )
        candidate = canonical_root.joinpath(*relative.parts)
    else:
        raw_path = Path(raw_ref)
        candidate = (
            _lexical_absolute(raw_path)
            if raw_path.is_absolute()
            else _lexical_absolute(canonical_root / raw_path)
        )
    candidate = _lexical_absolute(candidate)
    try:
        relative = candidate.relative_to(canonical_root)
    except ValueError:
        _integrity_fail(
            "layer3_output_binding_invalid",
            f"{field} escapes managed storage.",
        )
    if not relative.parts:
        _integrity_fail(
            "layer3_output_binding_invalid",
            f"{field} is not a canonical managed path.",
        )
    for part in relative.parts:
        _validate_local_component(part, field=field)
    return canonical_root, candidate


def _managed_regular_file(root: Path, path: Path) -> os.stat_result:
    relative = path.relative_to(root)
    components = (
        root,
        *(
            root.joinpath(*relative.parts[:index])
            for index in range(1, len(relative.parts) + 1)
        ),
    )
    for index, current in enumerate(components):
        try:
            info = current.lstat()
        except OSError as exc:
            raise Layer3ExecutionOutputIntegrityError(
                "layer3_output_file_invalid",
                "The authoritative output file is missing or inaccessible.",
            ) from exc
        attributes = int(getattr(info, "st_file_attributes", 0))
        if stat.S_ISLNK(info.st_mode) or attributes & _WINDOWS_REPARSE_POINT:
            _integrity_fail(
                "layer3_output_binding_invalid",
                "Managed output paths cannot contain a reparse component.",
            )
        if index < len(components) - 1 and not stat.S_ISDIR(info.st_mode):
            _integrity_fail(
                "layer3_output_file_invalid",
                "A managed output parent is not a directory.",
            )
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_OUTPUT_FILE_BYTES:
        _integrity_fail(
            "layer3_output_file_invalid",
            "The authoritative output path is not a bounded regular file.",
        )
    return info


def _file_fingerprint(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        info.st_mode,
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return _file_fingerprint(info)[:4]


def _bounded_hash_stream(
    handle: BinaryIO,
    *,
    max_bytes: int,
    capture_bytes: bool,
) -> tuple[int, str, bytes | None]:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 0:
        _integrity_fail(
            "layer3_output_file_invalid",
            "The authoritative output byte bound is invalid.",
        )
    digest = hashlib.sha256()
    captured = bytearray() if capture_bytes else None
    size = 0
    while True:
        remaining = max_bytes - size
        chunk = handle.read(min(1024 * 1024, remaining + 1))
        if not chunk:
            break
        if len(chunk) > remaining:
            _integrity_fail(
                "layer3_output_file_invalid",
                "The authoritative output file exceeds its bounded size.",
            )
        size += len(chunk)
        digest.update(chunk)
        if captured is not None:
            captured.extend(chunk)
    return size, digest.hexdigest(), bytes(captured) if captured is not None else None


def _stable_managed_file(
    root: Path,
    path: Path,
    *,
    initial: os.stat_result | None = None,
    read_bytes: bool = False,
) -> tuple[int, str, bytes | None]:
    initial = initial or _managed_regular_file(root, path)
    expected_identity = _file_identity(initial)
    try:
        with path.open("rb") as handle:
            opened_before = os.fstat(handle.fileno())
            if (
                _file_identity(opened_before) != expected_identity
                or not stat.S_ISREG(opened_before.st_mode)
            ):
                _integrity_fail(
                    "layer3_output_file_changed",
                    "The authoritative output file changed during hashing.",
                )
            try:
                first = _bounded_hash_stream(
                    handle,
                    max_bytes=initial.st_size,
                    capture_bytes=read_bytes,
                )
                handle.seek(0)
                second = _bounded_hash_stream(
                    handle,
                    max_bytes=initial.st_size,
                    capture_bytes=False,
                )
            except Layer3ExecutionOutputIntegrityError as exc:
                if exc.code == "layer3_output_file_invalid":
                    _integrity_fail(
                        "layer3_output_file_changed",
                        "The authoritative output file changed during reading.",
                    )
                raise
            opened_after = os.fstat(handle.fileno())
        final = _managed_regular_file(root, path)
        if (
            _file_identity(opened_after) != expected_identity
            or _file_identity(final) != expected_identity
            or first[:2] != second[:2]
            or first[0] != initial.st_size
        ):
            _integrity_fail(
                "layer3_output_file_changed",
                "The authoritative output file changed during reading.",
            )
        with path.open("rb") as final_handle:
            final_opened_before = os.fstat(final_handle.fileno())
            if (
                _file_identity(final_opened_before) != expected_identity
                or not stat.S_ISREG(final_opened_before.st_mode)
            ):
                _integrity_fail(
                    "layer3_output_file_changed",
                    "The authoritative output file changed after reading.",
                )
            try:
                final_content = _bounded_hash_stream(
                    final_handle,
                    max_bytes=initial.st_size,
                    capture_bytes=False,
                )
            except Layer3ExecutionOutputIntegrityError as exc:
                if exc.code == "layer3_output_file_invalid":
                    _integrity_fail(
                        "layer3_output_file_changed",
                        "The authoritative output file changed after reading.",
                    )
                raise
            final_opened_after = os.fstat(final_handle.fileno())
        final_after = _managed_regular_file(root, path)
        if (
            _file_identity(final_opened_after) != expected_identity
            or _file_identity(final_after) != expected_identity
            or first[:2] != final_content[:2]
        ):
            _integrity_fail(
                "layer3_output_file_changed",
                "The authoritative output file changed after reading.",
            )
    except Layer3ExecutionOutputIntegrityError:
        raise
    except OSError as exc:
        raise Layer3ExecutionOutputIntegrityError(
            "layer3_output_file_unreadable",
            "The authoritative output file could not be read.",
        ) from exc
    return first


def _artifact_storage_path(storage_ref: object) -> tuple[Path, Path]:
    return _managed_storage_path(
        storage_ref,
        field="AnalysisArtifact.storage_ref",
        root=Path(settings.artifact_storage_dir),
        logical_prefix="/storage/artifacts/",
    )


def _output_manifest_path(output_manifest_ref: object) -> tuple[Path, Path]:
    return _managed_storage_path(
        output_manifest_ref,
        field="output_manifest_ref",
        root=Path(settings.artifact_storage_dir) / "layer3",
    )


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
        raise Layer3ExecutionOutputIntegrityError(
            "layer3_output_noncanonical_value",
            "Output-integrity evidence is not canonical JSON.",
        ) from exc


def persist_output_manifest(
    *,
    pass_run_id: str,
    payload: Mapping[str, Any],
) -> str:
    normalized_pass_run_id = _required_text(
        pass_run_id,
        field="pass_run_id",
    )
    filename = f"l3_pass_run_{normalized_pass_run_id}.json"
    _validate_local_component(filename, field="output manifest filename")
    payload_bytes = _canonical_json_bytes(payload)
    storage_root = _managed_root(
        Path(settings.storage_dir),
        field="storage_dir",
    )
    configured_artifact_root = Path(settings.artifact_storage_dir)
    if configured_artifact_root != storage_root / "artifacts":
        _integrity_fail(
            "layer3_output_binding_invalid",
            "artifact_storage_dir does not equal managed artifact storage.",
        )
    try:
        configured_artifact_root.mkdir(exist_ok=True)
    except OSError as exc:
        raise Layer3ExecutionOutputIntegrityError(
            "layer3_output_file_unreadable",
            "The managed artifact directory is unavailable.",
        ) from exc
    artifact_root = _managed_root(
        configured_artifact_root,
        field="artifact_storage_dir",
    )
    layer3_root = artifact_root / "layer3"
    try:
        layer3_root.mkdir(exist_ok=True)
    except OSError as exc:
        raise Layer3ExecutionOutputIntegrityError(
            "layer3_output_file_unreadable",
            "The managed output-manifest directory is unavailable.",
        ) from exc
    canonical_root = _managed_root(
        layer3_root,
        field="layer3 output manifest root",
    )
    output_path = canonical_root / filename
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    created = False
    try:
        try:
            descriptor = os.open(output_path, flags, 0o600)
        except FileExistsError:
            initial = _managed_regular_file(
                canonical_root,
                output_path,
            )
            if int(getattr(initial, "st_nlink", 1)) != 1:
                _integrity_fail(
                    "layer3_output_file_invalid",
                    "An existing output manifest has multiple filesystem links.",
                )
            _, _, existing_bytes = _stable_managed_file(
                canonical_root,
                output_path,
                initial=initial,
                read_bytes=True,
            )
            if existing_bytes != payload_bytes:
                _integrity_fail(
                    "layer3_output_integrity_mismatch",
                    "An existing output manifest has conflicting bytes.",
                )
            return str(output_path)
        created = True
        with os.fdopen(descriptor, "wb") as handle:
            written = handle.write(payload_bytes)
            if written != len(payload_bytes):
                raise OSError("short output-manifest write")
            handle.flush()
            os.fsync(handle.fileno())
            opened = os.fstat(handle.fileno())
        if int(getattr(opened, "st_nlink", 1)) != 1:
            _integrity_fail(
                "layer3_output_file_invalid",
                "The new output manifest has multiple filesystem links.",
            )
        initial = _managed_regular_file(
            canonical_root,
            output_path,
        )
        if _file_identity(initial) != _file_identity(opened):
            _integrity_fail(
                "layer3_output_file_changed",
                "The new output manifest changed during publication.",
            )
        _, _, published_bytes = _stable_managed_file(
            canonical_root,
            output_path,
            initial=initial,
            read_bytes=True,
        )
        if published_bytes != payload_bytes:
            _integrity_fail(
                "layer3_output_file_changed",
                "Published output-manifest bytes are not stable.",
            )
    except Exception:
        if created:
            try:
                archive_root = canonical_root / "archive"
                archive_root.mkdir(exist_ok=True)
                safe_archive_root = _managed_root(
                    archive_root,
                    field="output manifest archive root",
                )
                os.rename(
                    output_path,
                    safe_archive_root
                    / f"{uuid.uuid4().hex}.manifest",
                )
            except OSError:
                pass
        raise
    return str(output_path)


_ArtifactPreflight = tuple[
    str,
    str,
    Path,
    Path,
    os.stat_result,
]
_FilePreflight = tuple[Path, Path, os.stat_result]


def _work_bound(*, count: int, total_bytes: int) -> None:
    if (
        count > MAX_OUTPUT_ARTIFACTS
        or total_bytes > MAX_OUTPUT_AGGREGATE_BYTES
    ):
        _integrity_fail(
            "layer3_output_work_bound_exceeded",
            "Output-integrity work exceeds cardinality or byte bounds.",
        )


def _preflight_artifacts(
    artifacts: Sequence[AnalysisArtifact],
) -> tuple[list[_ArtifactPreflight], int]:
    _work_bound(count=len(artifacts), total_bytes=0)
    identities: list[tuple[AnalysisArtifact, str, str]] = []
    artifact_ids: set[str] = set()
    for artifact in artifacts:
        artifact_id = _required_text(
            artifact.artifact_id,
            field="AnalysisArtifact.artifact_id",
        )
        artifact_type = _required_text(
            artifact.artifact_type,
            field="AnalysisArtifact.artifact_type",
        )
        if artifact_id in artifact_ids:
            _integrity_fail(
                "layer3_output_artifact_duplicate",
                "Artifact receipts require unique artifact IDs.",
            )
        artifact_ids.add(artifact_id)
        identities.append((artifact, artifact_id, artifact_type))
    preflight: list[_ArtifactPreflight] = []
    total_bytes = 0
    for artifact, artifact_id, artifact_type in identities:
        root, path = _artifact_storage_path(artifact.storage_ref)
        initial = _managed_regular_file(root, path)
        total_bytes += initial.st_size
        _work_bound(
            count=len(artifacts),
            total_bytes=total_bytes,
        )
        preflight.append(
            (
                artifact_id,
                artifact_type,
                root,
                path,
                initial,
            )
        )
    return preflight, total_bytes


def _preflight_manifest(output_manifest_ref: object) -> _FilePreflight:
    root, path = _output_manifest_path(output_manifest_ref)
    return root, path, _managed_regular_file(root, path)


def _artifact_receipts_from_preflight(
    preflight: Sequence[_ArtifactPreflight],
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for artifact_id, artifact_type, root, path, initial in preflight:
        artifact_size, artifact_sha256, _ = _stable_managed_file(
            root,
            path,
            initial=initial,
        )
        receipts.append(
            {
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "artifact_sha256": artifact_sha256,
                "artifact_size_bytes": artifact_size,
            }
        )
    return sorted(
        receipts,
        key=lambda receipt: (
            receipt["artifact_type"],
            receipt["artifact_id"],
        ),
    )


def artifact_receipts(
    artifacts: Sequence[AnalysisArtifact],
) -> list[dict[str, Any]]:
    preflight, _ = _preflight_artifacts(artifacts)
    return _artifact_receipts_from_preflight(
        preflight
    )


def artifact_set_hash(receipts: Sequence[Mapping[str, Any]]) -> str:
    _work_bound(count=len(receipts), total_bytes=0)
    expected_fields = {
        "artifact_id",
        "artifact_type",
        "artifact_sha256",
        "artifact_size_bytes",
    }
    normalized: list[dict[str, Any]] = []
    artifact_ids: set[str] = set()
    receipt_bytes = 0
    for receipt in receipts:
        if not isinstance(receipt, Mapping) or set(receipt) != expected_fields:
            _integrity_fail(
                "layer3_output_artifact_receipt_invalid",
                "Artifact receipts require the exact canonical fields.",
            )
        artifact_id = _required_text(
            receipt["artifact_id"],
            field="artifact_receipt.artifact_id",
        )
        artifact_type = _required_text(
            receipt["artifact_type"],
            field="artifact_receipt.artifact_type",
        )
        artifact_sha256 = receipt["artifact_sha256"]
        artifact_size = receipt["artifact_size_bytes"]
        if (
            artifact_id in artifact_ids
            or not isinstance(artifact_sha256, str)
            or len(artifact_sha256) != 64
            or any(char not in "0123456789abcdef" for char in artifact_sha256)
            or isinstance(artifact_size, bool)
            or not isinstance(artifact_size, int)
            or artifact_size < 0
        ):
            _integrity_fail(
                "layer3_output_artifact_receipt_invalid",
                "Artifact receipt values are malformed or duplicated.",
            )
        artifact_ids.add(artifact_id)
        receipt_bytes += artifact_size
        _work_bound(
            count=len(receipts),
            total_bytes=receipt_bytes,
        )
        normalized.append(
            {
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "artifact_sha256": artifact_sha256,
                "artifact_size_bytes": artifact_size,
            }
        )
    normalized.sort(
        key=lambda receipt: (
            receipt["artifact_type"],
            receipt["artifact_id"],
        )
    )
    return hashlib.sha256(_canonical_json_bytes(normalized)).hexdigest()


def output_manifest_sha256(output_manifest_ref: str) -> str:
    root, path, initial = _preflight_manifest(output_manifest_ref)
    _work_bound(count=0, total_bytes=initial.st_size)
    _, digest, _ = _stable_managed_file(
        root,
        path,
        initial=initial,
    )
    return digest


def compute_output_integrity(
    artifacts: Sequence[AnalysisArtifact],
    *,
    output_manifest_ref: str,
) -> dict[str, Any]:
    artifact_preflight, artifact_bytes = _preflight_artifacts(
        artifacts
    )
    manifest_root, manifest_path, manifest_initial = (
        _preflight_manifest(output_manifest_ref)
    )
    _work_bound(
        count=len(artifacts),
        total_bytes=artifact_bytes + manifest_initial.st_size,
    )
    ordered_receipts = _artifact_receipts_from_preflight(
        artifact_preflight
    )
    _, manifest_digest, _ = _stable_managed_file(
        manifest_root,
        manifest_path,
        initial=manifest_initial,
    )
    return {
        "artifact_receipts": ordered_receipts,
        "artifact_set_hash": artifact_set_hash(ordered_receipts),
        "output_manifest_sha256": manifest_digest,
    }


def _normalized_connector_origin_integrity(
    value: object,
) -> dict[str, str]:
    fields = {
        "schema_id",
        "connector_key",
        "connector_run_target_id",
        "connector_origin_receipt_hash",
        "proof_class",
    }
    if not isinstance(value, Mapping) or set(value) != fields:
        _integrity_fail(
            "layer3_output_integrity_mismatch",
            "Connector origin integrity is missing or malformed.",
        )
    normalized = {
        field: _required_text(value.get(field), field=field)
        for field in fields
    }
    receipt_hash = normalized["connector_origin_receipt_hash"]
    if (
        normalized["schema_id"] != CONNECTOR_ORIGIN_INTEGRITY_SCHEMA_ID
        or normalized["connector_key"]
        not in {"sciencebase_mcs", "nrc_adams_aps"}
        or normalized["proof_class"] not in {"fresh_live", "offline_fixture"}
        or len(receipt_hash) != 64
        or any(char not in "0123456789abcdef" for char in receipt_hash)
    ):
        _integrity_fail(
            "layer3_output_integrity_mismatch",
            "Connector origin integrity contains invalid canonical values.",
        )
    return {
        "schema_id": normalized["schema_id"],
        "connector_key": normalized["connector_key"],
        "connector_run_target_id": normalized["connector_run_target_id"],
        "connector_origin_receipt_hash": receipt_hash,
        "proof_class": normalized["proof_class"],
    }


def build_connector_output_integrity(
    artifacts: Sequence[AnalysisArtifact],
    *,
    output_manifest_ref: str,
    connector_origin_integrity: Mapping[str, Any],
) -> dict[str, Any]:
    origin = _normalized_connector_origin_integrity(
        connector_origin_integrity
    )
    output = compute_output_integrity(
        artifacts,
        output_manifest_ref=output_manifest_ref,
    )
    return {
        "schema_id": CONNECTOR_OUTPUT_INTEGRITY_SCHEMA_ID,
        "connector_key": origin["connector_key"],
        "connector_run_target_id": origin["connector_run_target_id"],
        "connector_origin_receipt_hash": (
            origin["connector_origin_receipt_hash"]
        ),
        "proof_class": origin["proof_class"],
        "artifact_receipts": output["artifact_receipts"],
        "artifact_set_hash": output["artifact_set_hash"],
        "output_manifest_sha256": output["output_manifest_sha256"],
    }


def _reject_pending_output_authority(
    db: Session,
    *,
    pass_run_id: str,
    analysis_run_id: str | None = None,
) -> None:
    for item in (*db.new, *db.dirty, *db.deleted):
        if (
            isinstance(item, L3PassRun)
            and item.pass_run_id == pass_run_id
        ) or (
            analysis_run_id is not None
            and isinstance(item, AnalysisArtifact)
            and item.analysis_run_id == analysis_run_id
        ):
            _integrity_fail(
                "layer3_output_pending_authority",
                "Output integrity requires clean durable authority.",
            )


def _output_engine_url_admitted(url: URL) -> bool:
    if url.get_backend_name().casefold() != "sqlite":
        return True
    database = str(url.database or "").strip()
    folded_database = database.casefold()
    query_values = {
        str(key).casefold(): (
            tuple(str(item).strip().casefold() for item in value)
            if isinstance(value, (list, tuple))
            else (str(value).strip().casefold(),)
        )
        for key, value in url.query.items()
    }
    return bool(
        database
        and folded_database != ":memory:"
        and not folded_database.startswith("file::memory:")
        and "mode=memory" not in folded_database
        and "memory" not in query_values.get("mode", ())
        and "memdb" not in query_values.get("vfs", ())
    )


def _output_committed_engine(db: Session) -> Engine:
    bind = db.get_bind()
    engine = (
        bind
        if isinstance(bind, Engine)
        else bind.engine
        if isinstance(bind, Connection)
        else None
    )
    if (
        engine is None
        or not isinstance(engine.pool, (QueuePool, NullPool))
        or not _output_engine_url_admitted(engine.url)
    ):
        _integrity_fail(
            "layer3_output_committed_authority_invalid",
            "Output integrity requires an independently readable committed engine.",
        )
    return engine


def _output_authority_state(
    db: Session,
    *,
    pass_run_id: str,
) -> tuple[bytes, tuple[tuple[str, str, str, bytes], ...]]:
    pass_run = db.execute(
        select(L3PassRun)
        .where(L3PassRun.pass_run_id == pass_run_id)
        .execution_options(populate_existing=True)
    ).scalar_one_or_none()
    if pass_run is None:
        _integrity_fail(
            "layer3_output_integrity_mismatch",
            "The authoritative pass run is missing.",
        )
    summary = pass_run.summary_json
    if not isinstance(summary, Mapping):
        _integrity_fail(
            "layer3_output_integrity_mismatch",
            "The authoritative pass summary is malformed.",
        )
    analysis_run_value = summary.get("analysis_run_id")
    analysis_run_id = (
        _required_text(
            analysis_run_value,
            field="summary_json.analysis_run_id",
        )
        if analysis_run_value is not None
        else None
    )
    artifacts = (
        db.execute(
            select(AnalysisArtifact)
            .where(
                AnalysisArtifact.analysis_run_id == analysis_run_id
            )
            .order_by(
                AnalysisArtifact.artifact_type.asc(),
                AnalysisArtifact.artifact_id.asc(),
            )
            .execution_options(populate_existing=True)
        )
        .scalars()
        .all()
        if analysis_run_id is not None
        else []
    )
    pass_state = _canonical_json_bytes(
        {
            "pass_run_id": pass_run.pass_run_id,
            "output_payload_ref": pass_run.output_payload_ref,
            "summary_json": summary,
        }
    )
    artifact_state = tuple(
        (
            artifact.artifact_id,
            artifact.artifact_type,
            artifact.storage_ref,
            _canonical_json_bytes(artifact.metadata_json),
        )
        for artifact in artifacts
    )
    return pass_state, artifact_state


def _manifest_payload(output_manifest_ref: str) -> dict[str, Any]:
    root, path, initial = _preflight_manifest(output_manifest_ref)
    _, _, payload_bytes = _stable_managed_file(
        root,
        path,
        initial=initial,
        read_bytes=True,
    )
    if payload_bytes is None:
        _integrity_fail(
            "layer3_output_integrity_mismatch",
            "The output manifest could not be read.",
        )

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def reject_constant(value: str) -> NoReturn:
        raise ValueError(f"invalid JSON constant: {value}")

    try:
        payload = json.loads(
            payload_bytes.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (
        RecursionError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        raise Layer3ExecutionOutputIntegrityError(
            "layer3_output_integrity_mismatch",
            "The output manifest is not a strict UTF-8 JSON object.",
        ) from exc
    if not isinstance(payload, dict):
        _integrity_fail(
            "layer3_output_integrity_mismatch",
            "The output manifest is not a JSON object.",
        )
    return payload


def _assert_pass_output_integrity_in_session(
    db: Session,
    *,
    pass_run_id: str,
) -> dict[str, Any]:
    with db.no_autoflush:
        _reject_pending_output_authority(
            db,
            pass_run_id=pass_run_id,
        )
        pass_run = db.execute(
            select(L3PassRun)
            .where(L3PassRun.pass_run_id == pass_run_id)
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if pass_run is None:
            _integrity_fail(
                "layer3_output_integrity_mismatch",
                "The authoritative pass run is missing.",
            )
        summary = pass_run.summary_json
        if not isinstance(summary, Mapping):
            _integrity_fail(
                "layer3_output_integrity_mismatch",
                "The authoritative pass summary is malformed.",
            )
        origin = _normalized_connector_origin_integrity(
            summary.get(CONNECTOR_ORIGIN_INTEGRITY_KEY)
        )
        stored = summary.get(CONNECTOR_OUTPUT_INTEGRITY_KEY)
        analysis_run_value = summary.get("analysis_run_id")
        analysis_run_id = (
            _required_text(
                analysis_run_value,
                field="summary_json.analysis_run_id",
            )
            if analysis_run_value is not None
            else None
        )
        _reject_pending_output_authority(
            db,
            pass_run_id=pass_run_id,
            analysis_run_id=analysis_run_id,
        )
        artifacts = (
            db.execute(
                select(AnalysisArtifact)
                .where(
                    AnalysisArtifact.analysis_run_id == analysis_run_id
                )
                .order_by(
                    AnalysisArtifact.artifact_type.asc(),
                    AnalysisArtifact.artifact_id.asc(),
                )
                .execution_options(populate_existing=True)
            )
            .scalars()
            .all()
            if analysis_run_id is not None
            else []
        )
        output_ref = _required_text(
            pass_run.output_payload_ref,
            field="L3PassRun.output_payload_ref",
        )
        manifest = _manifest_payload(output_ref)
        refs = manifest.get("artifact_refs_json")
        types = manifest.get("artifact_types_json")
        if (
            manifest.get("analysis_run_id") != analysis_run_id
            or not isinstance(refs, list)
            or not isinstance(types, list)
            or len(refs) != len(types)
            or not all(isinstance(item, str) for item in (*refs, *types))
            or sorted(zip(refs, types, strict=True))
            != sorted(
                (artifact.storage_ref, artifact.artifact_type)
                for artifact in artifacts
            )
        ):
            _integrity_fail(
                "layer3_output_integrity_mismatch",
                "The output manifest does not cover the durable artifact set.",
            )
        recomputed = build_connector_output_integrity(
            artifacts,
            output_manifest_ref=output_ref,
            connector_origin_integrity=origin,
        )
        if not isinstance(stored, Mapping) or dict(stored) != recomputed:
            _integrity_fail(
                "layer3_output_integrity_mismatch",
                "Stored output integrity contradicts durable output authority.",
            )
        receipts = {
            receipt["artifact_id"]: receipt
            for receipt in recomputed["artifact_receipts"]
        }
        for artifact in artifacts:
            metadata = artifact.metadata_json
            receipt = receipts[artifact.artifact_id]
            if (
                not isinstance(metadata, Mapping)
                or metadata.get("artifact_sha256")
                != receipt["artifact_sha256"]
                or metadata.get("artifact_size_bytes")
                != receipt["artifact_size_bytes"]
                or metadata.get("connector_origin_receipt_hash")
                != origin["connector_origin_receipt_hash"]
                or metadata.get("proof_class") != origin["proof_class"]
            ):
                _integrity_fail(
                    "layer3_output_integrity_mismatch",
                    "Artifact metadata contradicts durable output bytes.",
                )
        return recomputed


def assert_pass_output_integrity(
    db: Session,
    *,
    pass_run_id: str,
) -> dict[str, Any]:
    normalized_pass_run_id = _required_text(
        pass_run_id,
        field="pass_run_id",
    )
    engine = _output_committed_engine(db)
    with db.no_autoflush:
        _reject_pending_output_authority(
            db,
            pass_run_id=normalized_pass_run_id,
        )
        caller_before = _output_authority_state(
            db,
            pass_run_id=normalized_pass_run_id,
        )
        caller_connection = db.connection()
        caller_driver = caller_connection.connection.dbapi_connection
        with engine.connect() as committed_connection:
            committed_driver = (
                committed_connection.connection.dbapi_connection
            )
            if committed_driver is caller_driver:
                _integrity_fail(
                    "layer3_output_committed_authority_invalid",
                    "Committed output authority did not use a distinct connection.",
                )
            isolation = (
                committed_connection.get_isolation_level()
                .replace("_", " ")
                .strip()
                .upper()
            )
            if isolation == "READ UNCOMMITTED":
                _integrity_fail(
                    "layer3_output_committed_authority_invalid",
                    "READ UNCOMMITTED cannot prove output authority.",
                )
            with Session(
                bind=committed_connection,
                autoflush=False,
                expire_on_commit=False,
            ) as committed_db:
                with committed_db.begin():
                    committed_before = _output_authority_state(
                        committed_db,
                        pass_run_id=normalized_pass_run_id,
                    )
                    if committed_before != caller_before:
                        _integrity_fail(
                            "layer3_output_uncommitted_authority",
                            "Output authority is not independently committed-readable.",
                        )
                    result = _assert_pass_output_integrity_in_session(
                        committed_db,
                        pass_run_id=normalized_pass_run_id,
                    )
                    committed_after = _output_authority_state(
                        committed_db,
                        pass_run_id=normalized_pass_run_id,
                    )
                    if committed_after != committed_before:
                        _integrity_fail(
                            "layer3_output_integrity_mismatch",
                            "Committed output authority changed during verification.",
                        )
        caller_after = _output_authority_state(
            db,
            pass_run_id=normalized_pass_run_id,
        )
        if caller_after != caller_before:
            _integrity_fail(
                "layer3_output_integrity_mismatch",
                "Caller output authority changed during verification.",
            )
        return result


def assert_output_integrity(
    artifacts: Sequence[AnalysisArtifact],
    *,
    output_manifest_ref: str,
    expected_integrity: Mapping[str, Any],
) -> dict[str, Any]:
    expected_fields = {
        "artifact_receipts",
        "artifact_set_hash",
        "output_manifest_sha256",
    }
    if (
        not isinstance(expected_integrity, Mapping)
        or set(expected_integrity) != expected_fields
    ):
        _integrity_fail(
            "layer3_output_integrity_mismatch",
            "Stored output-integrity evidence is missing or malformed.",
        )
    recomputed = compute_output_integrity(
        artifacts,
        output_manifest_ref=output_manifest_ref,
    )
    if any(
        expected_integrity.get(field) != recomputed[field]
        for field in (
            "artifact_receipts",
            "artifact_set_hash",
            "output_manifest_sha256",
        )
    ):
        _integrity_fail(
            "layer3_output_integrity_mismatch",
            "Stored output-integrity evidence contradicts authoritative bytes.",
        )
    return recomputed


def output_metadata_summary(pass_run: L3PassRun) -> tuple[dict[str, Any] | None, str | None]:
    output_ref = str(pass_run.output_payload_ref or "").strip()
    if not output_ref:
        return None, "output_payload_ref_missing"
    try:
        root, output_path = _output_manifest_path(output_ref)
    except Layer3ExecutionOutputIntegrityError:
        return None, "output_metadata_unreadable"
    try:
        path_info = output_path.lstat()
    except OSError:
        return None, "output_metadata_file_missing"
    attributes = int(getattr(path_info, "st_file_attributes", 0))
    if (
        not stat.S_ISREG(path_info.st_mode)
        and not stat.S_ISLNK(path_info.st_mode)
        and not attributes & _WINDOWS_REPARSE_POINT
    ):
        return None, "output_metadata_file_missing"
    try:
        initial = _managed_regular_file(root, output_path)
        _, _, payload_bytes = _stable_managed_file(
            root,
            output_path,
            initial=initial,
            read_bytes=True,
        )
        if payload_bytes is None:
            return None, "output_metadata_unreadable"
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (
        Layer3ExecutionOutputIntegrityError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
    ):
        return None, "output_metadata_unreadable"
    if not isinstance(payload, dict):
        return None, "output_metadata_malformed"
    artifact_refs = payload.get("artifact_refs_json")
    artifact_types = payload.get("artifact_types_json")
    return (
        {
            "present": True,
            "readable": True,
            "output_payload_ref": output_ref,
            "analysis_run_id": payload.get("analysis_run_id"),
            "analysis_set_id": payload.get("analysis_set_id"),
            "dataset_version_id": payload.get("dataset_version_id"),
            "selected_method_name": payload.get("selected_method_name"),
            "artifact_count": len(artifact_refs) if isinstance(artifact_refs, list) else 0,
            "artifact_refs": list(artifact_refs or []) if isinstance(artifact_refs, list) else [],
            "artifact_types": list(artifact_types or []) if isinstance(artifact_types, list) else [],
            "source_gate": payload.get("source_gate"),
            "pass_scope": payload.get("pass_scope"),
            "source_dataset_version_ids": (
                list(payload.get("source_dataset_version_ids_json"))
                if isinstance(payload.get("source_dataset_version_ids_json"), list)
                else None
            ),
            "cohort_shape": payload.get("cohort_shape"),
            "requested_method_name": payload.get("requested_method_name"),
            "requested_method_source": payload.get("requested_method_source"),
            "engine_family": payload.get("engine_family"),
            "pass_type": payload.get("pass_type"),
            "source_shape": payload.get("source_shape"),
            "material_snapshot_id": payload.get("material_snapshot_id"),
            "analysis_unit_id": payload.get("analysis_unit_id"),
            "content_id": (
                payload.get("content_id")
                or (
                    payload.get("document_identity", {}).get("content_id")
                    if isinstance(payload.get("document_identity"), dict)
                    else None
                )
            ),
            "chunk_ids": (
                list(payload.get("chunk_summary", {}).get("chunk_ids"))
                if isinstance(payload.get("chunk_summary"), dict)
                and isinstance(payload.get("chunk_summary", {}).get("chunk_ids"), list)
                else None
            ),
            "chunk_hashes": (
                list(payload.get("chunk_summary", {}).get("chunk_hashes"))
                if isinstance(payload.get("chunk_summary"), dict)
                and isinstance(payload.get("chunk_summary", {}).get("chunk_hashes"), list)
                else None
            ),
        },
        None,
    )
