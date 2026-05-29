from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import L3SourceDirectoryIngestionBatch, L3SourceDirectoryIngestionFile


SCHEMA_ID = "layer3.source_directory_ingestion_batch.v1"
STATUS_SCHEMA_ID = "layer3.source_directory_ingestion_status.v1"
MODE = "server_configured_operator_directory_text_table_ingestion"
SOURCE_FAMILY = "server_configured_operator_directory_text_table_source_family"
CONFIG_AUTHORITY = "LAYER3_SOURCE_INGESTION_DIR"
OPERATOR_DECISION = "scan_server_configured_operator_directory"
STATUS_RECORDED = "recorded"
RUNTIME_POLICY_ID = "recursive_server_configured_directory_text_table_policy_v1"
ALLOWED_EXTENSIONS = (".csv", ".json", ".txt", ".md")
MAX_BATCH_FILES = 100
MAX_RECURSION_DEPTH = 2
MAX_RELATIVE_PATH_SEGMENTS = 3
DIRECT_CHILD_ONLY = False
RECURSIVE_TRAVERSAL_ADMITTED = True
_WINDOWS_FILE_ATTRIBUTE_HIDDEN = 0x2
_WINDOWS_FILE_ATTRIBUTE_SYSTEM = 0x4
_WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT = 0x400

_MEDIA_TYPES = {
    ".csv": "text/csv",
    ".json": "application/json",
    ".txt": "text/plain",
    ".md": "text/markdown",
}
_FORBIDDEN_REQUEST_FIELDS = {
    "path",
    "paths",
    "directory",
    "local_directory",
    "local_path",
    "url",
    "urls",
    "glob",
    "recursive",
    "file",
    "files",
    "file_bytes",
    "rag_vector_index",
    "web_connector",
}


@dataclass(frozen=True)
class _FileObservation:
    relative_name: str
    extension: str
    media_type: str
    content_size_bytes: int
    mtime_ns: int
    content_sha256: str
    file_identity_hash: str
    authority_basis_hash: str


class SourceDirectoryIngestionError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": 1,
            "request_id": "source-directory-ingestion-error",
            "server_time": _server_time(),
            "mode": MODE,
            "status": "blocked",
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }


def scan_server_configured_directory(
    db: Session,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_scan_payload(payload, operator_decision=OPERATOR_DECISION)
    root = _configured_root()
    return _scan_observed_directory(
        db,
        fields,
        root=root,
        config_authority=CONFIG_AUTHORITY,
        source_root_ref=_source_root_ref(),
        source_authority={},
    )


def scan_server_owned_directory_root(
    db: Session,
    payload: Mapping[str, Any],
    *,
    root: Path,
    config_authority: str,
    source_root_ref: str,
    operator_decision: str,
    source_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    fields = _normalise_scan_payload(payload, operator_decision=operator_decision)
    resolved_root = _validate_server_owned_root(root, config_authority=config_authority)
    return _scan_observed_directory(
        db,
        fields,
        root=resolved_root,
        config_authority=config_authority,
        source_root_ref=source_root_ref,
        source_authority=source_authority or {},
    )


def _normalise_scan_payload(payload: Mapping[str, Any], *, operator_decision: str) -> dict[str, str]:
    fields = _normalise_payload(payload)
    client_request_id = _required(fields, "client_request_id")
    if len(client_request_id) > 255:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_client_request_id_too_long",
            "client_request_id must be 255 characters or fewer.",
            details={"client_request_id_length": len(client_request_id)},
        )
    received_operator_decision = _required(fields, "operator_decision")
    if received_operator_decision != operator_decision:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_operator_decision_not_admitted",
            "operator_decision is not admitted for server-configured directory ingestion.",
            details={
                "expected_operator_decision": operator_decision,
                "received_operator_decision": received_operator_decision,
            },
        )
    source_family = fields.get("source_family") or SOURCE_FAMILY
    if source_family != SOURCE_FAMILY:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_source_family_not_admitted",
            "Only the selected server-configured text/table source family is admitted.",
            details={"expected_source_family": SOURCE_FAMILY, "received_source_family": source_family},
        )
    ingestion_mode = fields.get("ingestion_mode") or MODE
    if ingestion_mode != MODE:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_mode_not_admitted",
            "Only the selected server-configured directory ingestion mode is admitted.",
            details={"expected_ingestion_mode": MODE, "received_ingestion_mode": ingestion_mode},
        )
    return fields


def _scan_observed_directory(
    db: Session,
    fields: Mapping[str, str],
    *,
    root: Path,
    config_authority: str,
    source_root_ref: str,
    source_authority: Mapping[str, Any],
) -> dict[str, Any]:
    client_request_id = fields["client_request_id"]
    observations = _observe_recursive_files(root)
    total_size = sum(item.content_size_bytes for item in observations)
    directory_fingerprint_hash = _stable_hash(
        {
            "runtime_policy_id": RUNTIME_POLICY_ID,
            "mode": MODE,
            "source_family": SOURCE_FAMILY,
            "config_authority": config_authority,
            "source_root_ref": source_root_ref,
            "allowed_extensions": list(ALLOWED_EXTENSIONS),
            "max_recursion_depth": MAX_RECURSION_DEPTH,
            "files": [
                {
                    "relative_name": item.relative_name,
                    "extension": item.extension,
                    "content_size_bytes": item.content_size_bytes,
                    "mtime_ns": item.mtime_ns,
                    "content_sha256": item.content_sha256,
                    "file_identity_hash": item.file_identity_hash,
                }
                for item in observations
            ],
        }
    )
    authority_basis = {
        "schema_id": SCHEMA_ID,
        "runtime_policy_id": RUNTIME_POLICY_ID,
        "mode": MODE,
        "source_family": SOURCE_FAMILY,
        "config_authority": config_authority,
        "source_root_ref": source_root_ref,
        "directory_fingerprint_hash": directory_fingerprint_hash,
    }
    authority_basis_hash = _stable_hash(authority_basis)

    existing = _existing_batch(db, client_request_id, authority_basis_hash)
    if existing is not None:
        if existing.client_request_id == client_request_id and existing.authority_basis_hash != authority_basis_hash:
            raise SourceDirectoryIngestionError(
                "source_directory_ingestion_idempotency_conflict",
                "The client_request_id conflicts with a different directory authority basis.",
                http_status=409,
                details={"client_request_id": client_request_id},
            )
        return _batch_response(db, existing, response_status="already_recorded", request_id=client_request_id)

    authority_snapshot = {
        "schema_id": SCHEMA_ID,
        "runtime_policy_id": RUNTIME_POLICY_ID,
        "mode": MODE,
        "source_family": SOURCE_FAMILY,
        "config_authority": config_authority,
        "source_root_ref": source_root_ref,
        "source_root_ref_hash": _stable_hash({"source_root_ref": source_root_ref}),
        "configured_root_hash": _stable_hash({"configured_root": str(root)}),
        "direct_child_only": DIRECT_CHILD_ONLY,
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "recursive_traversal_admitted": RECURSIVE_TRAVERSAL_ADMITTED,
        "max_recursion_depth": MAX_RECURSION_DEPTH,
        "max_relative_path_segments": MAX_RELATIVE_PATH_SEGMENTS,
        "caller_selected_recursive_flag_allowed": False,
        "caller_supplied_paths_admitted": False,
        "browser_supplied_file_bytes_admitted": False,
        "directory_fingerprint_hash": directory_fingerprint_hash,
        "source_authority": dict(source_authority),
    }
    batch = L3SourceDirectoryIngestionBatch(
        client_request_id=client_request_id,
        source_family=SOURCE_FAMILY,
        ingestion_mode=MODE,
        config_authority=config_authority,
        directory_fingerprint_hash=directory_fingerprint_hash,
        authority_basis_hash=authority_basis_hash,
        eligible_file_count=len(observations),
        total_size_bytes=total_size,
        authority_snapshot_json=authority_snapshot,
        summary_json={
            "authority_basis": authority_basis,
            "negative_invariants": _negative_invariants(),
            "source_root_ref": source_root_ref,
            "source_authority": dict(source_authority),
            "files": [],
        },
        status=STATUS_RECORDED,
    )
    db.add(batch)
    db.flush()
    file_summaries: list[dict[str, Any]] = []
    for item in observations:
        file_authority_basis_hash = _file_authority_basis_hash(
            item,
            source_ingestion_batch_id=batch.source_ingestion_batch_id,
        )
        file_summary = _file_summary(item, authority_basis_hash=file_authority_basis_hash)
        file_summaries.append(file_summary)
        db.add(
            L3SourceDirectoryIngestionFile(
                source_ingestion_batch_id=batch.source_ingestion_batch_id,
                relative_name=item.relative_name,
                extension=item.extension,
                media_type=item.media_type,
                content_size_bytes=item.content_size_bytes,
                mtime_ns=item.mtime_ns,
                content_sha256=item.content_sha256,
                file_identity_hash=item.file_identity_hash,
                authority_basis_hash=file_authority_basis_hash,
                summary_json=file_summary,
                status=STATUS_RECORDED,
            )
        )
    batch.summary_json = {**(batch.summary_json or {}), "files": file_summaries}
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing_after_race = _existing_batch(db, client_request_id, authority_basis_hash)
        if existing_after_race is not None:
            return _batch_response(
                db,
                existing_after_race,
                response_status="already_recorded",
                request_id=client_request_id,
            )
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_record_conflict",
            "The source directory ingestion batch conflicts with an existing persisted authority row.",
            http_status=409,
            details={"client_request_id": client_request_id},
        ) from exc
    db.refresh(batch)
    return _batch_response(db, batch, request_id=client_request_id)


def source_directory_ingestion_status(
    db: Session,
    source_ingestion_batch_id: str,
) -> dict[str, Any]:
    batch_id = str(source_ingestion_batch_id or "").strip()
    if not batch_id:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_batch_id_required",
            "source_ingestion_batch_id is required.",
            details={"field": "source_ingestion_batch_id"},
        )
    batch = db.get(L3SourceDirectoryIngestionBatch, batch_id)
    if batch is None:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_batch_not_found",
            "No source directory ingestion batch exists for the requested status.",
            http_status=404,
            details={"source_ingestion_batch_id": batch_id},
        )
    body = _batch_response(db, batch)
    body["schema_id"] = STATUS_SCHEMA_ID
    body["mode"] = "server_configured_operator_directory_text_table_ingestion_status"
    return body


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, str]:
    fields = {str(key): value for key, value in dict(payload or {}).items() if value is not None}
    forbidden = sorted(set(fields) & _FORBIDDEN_REQUEST_FIELDS)
    if forbidden:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_forbidden_field",
            "The source directory ingestion request includes caller-controlled source selection fields.",
            details={"forbidden_fields": forbidden},
        )
    allowed = {"client_request_id", "operator_decision", "source_family", "ingestion_mode"}
    unknown = sorted(set(fields) - allowed)
    if unknown:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_unknown_field",
            "The source directory ingestion request contract is intentionally scoped.",
            details={"unknown_fields": unknown},
        )
    return {key: str(value).strip() for key, value in fields.items()}


def _configured_root() -> Path:
    configured = str(settings.layer3_source_ingestion_dir or "").strip()
    if not configured:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_dir_unset",
            f"{CONFIG_AUTHORITY} must be set before server-configured directory ingestion can run.",
            http_status=409,
            details={"config_authority": CONFIG_AUTHORITY},
        )
    return _validate_server_owned_root(Path(configured), config_authority=CONFIG_AUTHORITY)


def _validate_server_owned_root(root: Path, *, config_authority: str) -> Path:
    if not root.is_absolute():
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_dir_not_absolute",
            f"{config_authority} must be an absolute server-owned directory.",
            http_status=409,
            details={"config_authority": config_authority},
        )
    if not root.exists() or not root.is_dir():
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_dir_unavailable",
            f"{config_authority} must resolve to an existing directory.",
            http_status=409,
            details={"config_authority": config_authority},
        )
    resolved = root.resolve()
    for blocked_root in _blocked_roots():
        if _same_or_child(resolved, blocked_root):
            raise SourceDirectoryIngestionError(
                "source_directory_ingestion_dir_not_admitted",
                "The configured source ingestion directory overlaps app-owned storage or export staging.",
                http_status=409,
                details={"config_authority": config_authority, "blocked_root": blocked_root.name},
            )
    return resolved


def _observe_direct_child_files(root: Path) -> list[_FileObservation]:
    try:
        children = sorted(root.iterdir(), key=lambda item: item.name.lower())
    except OSError as exc:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_directory_unreadable",
            "The configured source ingestion directory could not be enumerated.",
            http_status=409,
            details={"relative_name": "."},
        ) from exc
    if not children:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_empty_directory",
            "The configured source ingestion directory has no eligible direct child files.",
        )
    seen_names: set[str] = set()
    candidates: list[tuple[Path, str, str]] = []
    for child in children:
        relative_name = child.name
        normalized_name = relative_name.lower()
        if normalized_name in seen_names:
            raise SourceDirectoryIngestionError(
                "source_directory_ingestion_duplicate_relative_name",
                "The configured source ingestion directory has duplicate conflicting relative names.",
                details={"relative_name": relative_name},
            )
        seen_names.add(normalized_name)
        if child.is_symlink():
            raise SourceDirectoryIngestionError(
                "source_directory_ingestion_symlink_not_admitted",
                "Symlinks are not admitted for source directory ingestion.",
                details={"relative_name": relative_name},
            )
        if not child.is_file():
            raise SourceDirectoryIngestionError(
                "source_directory_ingestion_non_file_not_admitted",
                "Only direct child files are admitted; directories and device paths are blocked.",
                details={"relative_name": relative_name},
            )
        extension = child.suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise SourceDirectoryIngestionError(
                "source_directory_ingestion_extension_not_admitted",
                "Only CSV, JSON, TXT, and MD files are admitted.",
                details={"relative_name": relative_name, "extension": extension},
            )
        candidates.append((child, relative_name, extension))
    if not candidates:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_empty_eligible_directory",
            "The configured source ingestion directory has no eligible direct child files.",
        )
    if len(candidates) > MAX_BATCH_FILES:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_batch_too_large",
            "The configured source ingestion directory exceeds the maximum admitted file count.",
            details={"max_batch_files": MAX_BATCH_FILES, "received_file_count": len(candidates)},
        )
    observations = [_observe_file(child, relative_name, extension) for child, relative_name, extension in candidates]
    max_batch_bytes = _max_file_bytes() * MAX_BATCH_FILES
    total_size = sum(item.content_size_bytes for item in observations)
    if total_size > max_batch_bytes:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_batch_bytes_too_large",
            "The configured source ingestion directory exceeds the maximum admitted batch size.",
            details={"max_batch_bytes": max_batch_bytes, "received_bytes": total_size},
        )
    return observations


def _observe_recursive_files(root: Path) -> list[_FileObservation]:
    candidates: list[tuple[Path, str, str]] = []
    seen_names: set[str] = set()
    stack = [root]
    root_children_seen = False

    while stack:
        directory = stack.pop()
        try:
            children = sorted(directory.iterdir(), key=lambda item: _relative_name(root, item).lower())
        except OSError as exc:
            raise SourceDirectoryIngestionError(
                "source_directory_ingestion_directory_unreadable",
                "The configured source ingestion directory could not be enumerated.",
                http_status=409,
                details={"relative_name": _relative_name(root, directory) if directory != root else "."},
            ) from exc
        if directory == root:
            root_children_seen = bool(children)
        for child in reversed(children):
            relative_name = _relative_name(root, child)
            relative_parts = tuple(part for part in Path(relative_name).parts if part)
            _assert_relative_path_shape(child, relative_name, relative_parts)
            _assert_path_within_root(root, child, relative_name)
            if _is_disallowed_filesystem_entry(child):
                raise SourceDirectoryIngestionError(
                    "source_directory_ingestion_reparse_or_device_not_admitted",
                    "Symlinks, reparse points, device paths, sockets, pipes, and non-regular filesystem entries are blocked.",
                    details={"relative_name": relative_name},
                )
            if _is_hidden_path(child, relative_parts):
                raise SourceDirectoryIngestionError(
                    "source_directory_ingestion_hidden_path_not_admitted",
                    "Hidden source-directory file or directory segments are blocked.",
                    details={"relative_name": relative_name},
                )
            if child.is_dir():
                if len(relative_parts) > MAX_RECURSION_DEPTH:
                    raise SourceDirectoryIngestionError(
                        "source_directory_ingestion_recursion_depth_exceeded",
                        "The recursive source directory policy does not admit traversal beyond depth 2.",
                        details={"relative_name": relative_name, "max_recursion_depth": MAX_RECURSION_DEPTH},
                    )
                stack.append(child)
                continue
            if not child.is_file():
                raise SourceDirectoryIngestionError(
                    "source_directory_ingestion_non_file_not_admitted",
                    "Only regular files are admitted; directories, sockets, pipes, and device paths are blocked.",
                    details={"relative_name": relative_name},
                )
            normalized_name = relative_name.casefold()
            if normalized_name in seen_names:
                raise SourceDirectoryIngestionError(
                    "source_directory_ingestion_duplicate_relative_name",
                    "The configured source ingestion directory has duplicate conflicting relative names.",
                    details={"relative_name": relative_name},
                )
            seen_names.add(normalized_name)
            extension = child.suffix.lower()
            if extension not in ALLOWED_EXTENSIONS:
                raise SourceDirectoryIngestionError(
                    "source_directory_ingestion_extension_not_admitted",
                    "Only CSV, JSON, TXT, and MD files are admitted.",
                    details={"relative_name": relative_name, "extension": extension},
                )
            candidates.append((child, relative_name, extension))

    if not root_children_seen:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_empty_directory",
            "The configured source ingestion directory has no eligible files under the recursive policy.",
        )
    if not candidates:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_empty_eligible_directory",
            "The configured source ingestion directory has no eligible files under the recursive policy.",
        )
    if len(candidates) > MAX_BATCH_FILES:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_batch_too_large",
            "The configured source ingestion directory exceeds the maximum admitted file count.",
            details={"max_batch_files": MAX_BATCH_FILES, "received_file_count": len(candidates)},
        )
    observations = [_observe_file(child, relative_name, extension) for child, relative_name, extension in candidates]
    observations.sort(key=lambda item: item.relative_name.lower())
    max_batch_bytes = _max_file_bytes() * MAX_BATCH_FILES
    total_size = sum(item.content_size_bytes for item in observations)
    if total_size > max_batch_bytes:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_batch_bytes_too_large",
            "The configured source ingestion directory exceeds the maximum admitted batch size.",
            details={"max_batch_bytes": max_batch_bytes, "received_bytes": total_size},
        )
    return observations


def _observe_file(path: Path, relative_name: str, extension: str) -> _FileObservation:
    try:
        before = path.stat()
    except OSError as exc:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_file_unreadable",
            "A source directory file could not be read for durable authority hashing.",
            http_status=409,
            details={"relative_name": relative_name},
        ) from exc
    if before.st_size <= 0:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_empty_file",
            "Empty files are not admitted for source directory ingestion.",
            details={"relative_name": relative_name},
        )
    max_file_bytes = _max_file_bytes()
    if before.st_size > max_file_bytes:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_file_too_large",
            "A source directory file exceeds the configured maximum file size.",
            details={"relative_name": relative_name, "max_file_bytes": max_file_bytes, "received_bytes": before.st_size},
        )
    try:
        data = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_file_unreadable",
            "A source directory file could not be read for durable authority hashing.",
            http_status=409,
            details={"relative_name": relative_name},
        ) from exc
    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_stale_file_identity",
            "A source directory file changed while ingestion identity was being computed.",
            http_status=409,
            details={"relative_name": relative_name},
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_text_decode_failed",
            "Source directory files must decode as UTF-8 text.",
            details={"relative_name": relative_name},
        ) from exc
    if extension == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            raise SourceDirectoryIngestionError(
                "source_directory_ingestion_json_parse_failed",
                "JSON source directory files must parse as JSON.",
                details={"relative_name": relative_name},
            ) from exc
    content_sha256 = hashlib.sha256(data).hexdigest()
    file_identity = {
        "relative_name": relative_name,
        "extension": extension,
        "content_size_bytes": after.st_size,
        "mtime_ns": after.st_mtime_ns,
        "content_sha256": content_sha256,
    }
    file_identity_hash = _stable_hash(file_identity)
    return _FileObservation(
        relative_name=relative_name,
        extension=extension,
        media_type=_MEDIA_TYPES[extension],
        content_size_bytes=after.st_size,
        mtime_ns=after.st_mtime_ns,
        content_sha256=content_sha256,
        file_identity_hash=file_identity_hash,
        authority_basis_hash=_stable_hash({"schema_id": SCHEMA_ID, "file_identity": file_identity}),
    )


def _relative_name(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_path_escape",
            "A source directory entry is outside the configured server-owned root.",
            http_status=409,
        ) from exc


def _assert_relative_path_shape(path: Path, relative_name: str, relative_parts: tuple[str, ...]) -> None:
    del path
    if not relative_name or relative_name.startswith("/") or "\\" in relative_name:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_relative_path_not_admitted",
            "Recursive source-directory file authority must use normalized relative paths.",
            details={"relative_name": relative_name},
        )
    if any(part in {"", ".", ".."} for part in relative_parts):
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_relative_path_not_admitted",
            "Recursive source-directory file authority must not include empty, current, or parent path segments.",
            details={"relative_name": relative_name},
        )
    if len(relative_parts) > MAX_RELATIVE_PATH_SEGMENTS:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_relative_path_too_deep",
            "The recursive source directory policy does not admit more than 3 relative path segments including filename.",
            details={
                "relative_name": relative_name,
                "max_relative_path_segments": MAX_RELATIVE_PATH_SEGMENTS,
            },
        )


def _assert_path_within_root(root: Path, path: Path, relative_name: str) -> None:
    resolved_root = root.resolve()
    try:
        resolved_path = path.resolve()
    except OSError as exc:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_path_unreadable",
            "A source directory entry could not be resolved for traversal safety.",
            http_status=409,
            details={"relative_name": relative_name},
        ) from exc
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_path_escape",
            "A source directory entry resolves outside the configured server-owned root.",
            http_status=409,
            details={"relative_name": relative_name},
        )


def _is_disallowed_filesystem_entry(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        stat_result = path.stat(follow_symlinks=False)
    except OSError:
        return True
    attrs = int(getattr(stat_result, "st_file_attributes", 0) or 0)
    return bool(attrs & _WINDOWS_FILE_ATTRIBUTE_REPARSE_POINT)


def _is_hidden_path(path: Path, relative_parts: tuple[str, ...]) -> bool:
    if any(part.startswith(".") for part in relative_parts):
        return True
    try:
        stat_result = path.stat(follow_symlinks=False)
    except OSError:
        return True
    attrs = int(getattr(stat_result, "st_file_attributes", 0) or 0)
    hidden_or_system = _WINDOWS_FILE_ATTRIBUTE_HIDDEN | _WINDOWS_FILE_ATTRIBUTE_SYSTEM
    return bool(attrs & hidden_or_system)


def _existing_batch(
    db: Session,
    client_request_id: str,
    authority_basis_hash: str,
) -> L3SourceDirectoryIngestionBatch | None:
    existing_for_request = (
        db.query(L3SourceDirectoryIngestionBatch)
        .filter(L3SourceDirectoryIngestionBatch.client_request_id == client_request_id)
        .one_or_none()
    )
    if existing_for_request is not None:
        return existing_for_request
    return (
        db.query(L3SourceDirectoryIngestionBatch)
        .filter(L3SourceDirectoryIngestionBatch.authority_basis_hash == authority_basis_hash)
        .one_or_none()
    )


def _batch_response(
    db: Session,
    batch: L3SourceDirectoryIngestionBatch,
    *,
    response_status: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    authority_snapshot = batch.authority_snapshot_json or {}
    files = (
        db.query(L3SourceDirectoryIngestionFile)
        .filter(L3SourceDirectoryIngestionFile.source_ingestion_batch_id == batch.source_ingestion_batch_id)
        .order_by(L3SourceDirectoryIngestionFile.relative_name.asc())
        .all()
    )
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": 1,
        "request_id": request_id or batch.client_request_id,
        "server_time": _server_time(),
        "mode": MODE,
        "status": response_status or batch.status,
        "message": "Layer 3 server-configured source directory ingestion recorded durable file authority.",
        "source_ingestion_batch_id": batch.source_ingestion_batch_id,
        "runtime_policy_id": authority_snapshot.get("runtime_policy_id", RUNTIME_POLICY_ID),
        "source_family": batch.source_family,
        "ingestion_mode": batch.ingestion_mode,
        "config_authority": batch.config_authority,
        "source_root_ref": _batch_source_root_ref(batch),
        "source_root_absolute_path_exposed": False,
        "direct_child_only": authority_snapshot.get("direct_child_only", True),
        "recursive_traversal_admitted": authority_snapshot.get("recursive_traversal_admitted", False),
        "max_recursion_depth": authority_snapshot.get("max_recursion_depth"),
        "max_relative_path_segments": authority_snapshot.get("max_relative_path_segments"),
        "caller_selected_recursive_flag_allowed": authority_snapshot.get("caller_selected_recursive_flag_allowed", False),
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "eligible_file_count": batch.eligible_file_count,
        "total_size_bytes": batch.total_size_bytes,
        "directory_fingerprint_hash": batch.directory_fingerprint_hash,
        "authority_basis_hash": batch.authority_basis_hash,
        "authority_snapshot": authority_snapshot,
        "files": [_stored_file_response(item) for item in files],
        "negative_invariants": _negative_invariants(),
        "next_allowed_actions": [
            "use_source_directory_ingestion_batch_as_inventory_authority",
            "define_later_freeze_before_material_admission_package_rag_or_rendered_controls",
        ],
    }


def _stored_file_response(file_record: L3SourceDirectoryIngestionFile) -> dict[str, Any]:
    return {
        "source_ingestion_file_id": file_record.source_ingestion_file_id,
        "relative_name": file_record.relative_name,
        "extension": file_record.extension,
        "media_type": file_record.media_type,
        "content_size_bytes": file_record.content_size_bytes,
        "content_sha256": file_record.content_sha256,
        "file_identity_hash": file_record.file_identity_hash,
        "authority_basis_hash": file_record.authority_basis_hash,
        "status": file_record.status,
        "absolute_path_exposed": False,
    }


def _file_authority_basis_hash(item: _FileObservation, *, source_ingestion_batch_id: str) -> str:
    return _stable_hash(
        {
            "schema_id": "layer3.source_directory_ingestion_file_authority.v1",
            "source_ingestion_batch_id": source_ingestion_batch_id,
            "relative_name": item.relative_name,
            "extension": item.extension,
            "content_size_bytes": item.content_size_bytes,
            "mtime_ns": item.mtime_ns,
            "content_sha256": item.content_sha256,
            "file_identity_hash": item.file_identity_hash,
        }
    )


def _file_summary(item: _FileObservation, *, authority_basis_hash: str | None = None) -> dict[str, Any]:
    return {
        "relative_name": item.relative_name,
        "extension": item.extension,
        "media_type": item.media_type,
        "content_size_bytes": item.content_size_bytes,
        "content_sha256": item.content_sha256,
        "file_identity_hash": item.file_identity_hash,
        "authority_basis_hash": authority_basis_hash or item.authority_basis_hash,
        "absolute_path_exposed": False,
    }


def _blocked_roots() -> list[Path]:
    roots = [
        Path(settings.storage_dir),
        Path(settings.raw_storage_dir),
        Path(settings.artifact_storage_dir),
        Path(settings.layer3_local_outbox_dir),
    ]
    if settings.layer3_external_local_export_dir:
        roots.append(Path(settings.layer3_external_local_export_dir))
    return [root.resolve() for root in roots if str(root)]


def _same_or_child(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _max_file_bytes() -> int:
    return int(settings.max_upload_mb) * 1024 * 1024


def _required(fields: Mapping[str, str], key: str) -> str:
    value = fields.get(key, "").strip()
    if not value:
        raise SourceDirectoryIngestionError(
            "source_directory_ingestion_required_field_missing",
            "A required source directory ingestion field is missing or empty.",
            details={"field": key},
        )
    return value


def _negative_invariants() -> dict[str, bool]:
    return {
        "caller_supplied_paths_enabled": False,
        "recursive_traversal_enabled": True,
        "caller_selected_recursive_flag_enabled": False,
        "browser_file_upload_enabled": False,
        "pdf_ocr_office_binary_enabled": False,
        "web_connector_enabled": False,
        "rag_vector_index_enabled": False,
        "package_construction_enabled": False,
        "connector_dispatch_enabled": False,
        "provider_public_delivery_enabled": False,
        "frontend_durable_authority_enabled": False,
    }


def _source_root_ref() -> str:
    return "server-configured://LAYER3_SOURCE_INGESTION_DIR"


def _batch_source_root_ref(batch: L3SourceDirectoryIngestionBatch) -> str:
    summary = batch.summary_json or {}
    authority_snapshot = batch.authority_snapshot_json or {}
    return str(summary.get("source_root_ref") or authority_snapshot.get("source_root_ref") or _source_root_ref())


def resolve_batch_source_root(batch: L3SourceDirectoryIngestionBatch) -> Path:
    source_root_ref = _batch_source_root_ref(batch)
    if source_root_ref == _source_root_ref():
        return _configured_root()
    if source_root_ref.startswith("candidate-b-runtime-bridge://"):
        from app.services import layer3_candidate_b_runtime_bridge

        try:
            return layer3_candidate_b_runtime_bridge.resolve_candidate_b_runtime_bridge_curated_root_ref(source_root_ref)
        except layer3_candidate_b_runtime_bridge.CandidateBRuntimeBridgeError as exc:
            raise SourceDirectoryIngestionError(
                exc.code,
                exc.message,
                http_status=exc.http_status,
                details=exc.details,
            ) from exc
    raise SourceDirectoryIngestionError(
        "source_directory_ingestion_source_root_ref_not_resolvable",
        "The persisted source-directory root reference is not admitted for live material reads.",
        http_status=409,
        details={"source_root_ref": source_root_ref},
    )


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
