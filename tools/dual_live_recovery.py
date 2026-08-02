from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn
from uuid import UUID


_MARKER_SCHEMA = "project6.dual_live_recovery_marker.v1"
_REPORT_SCHEMA = "project6.dual_live_recovery_report.v1"
_ARCHIVE_SCHEMA = "project6.dual_live_recovery_archive.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_CODE = re.compile(r"[a-z0-9_]+\Z")
_FALSE_VALUES = frozenset(("0", "false", "no", "off"))
_AUTHORITY_VARIABLES = frozenset(
    (
        "CONNECTOR_CAMPAIGN_DEFINITION_PATH",
        "CONNECTOR_CAMPAIGN_DEFINITION_SHA256",
        "CONNECTOR_SCIENCEBASE_GRANT_PATH",
        "CONNECTOR_SCIENCEBASE_GRANT_SHA256",
        "CONNECTOR_NRC_APS_GRANT_PATH",
        "CONNECTOR_NRC_APS_GRANT_SHA256",
        "NRC_API_SUBSCRIPTION_KEY",
    )
)
_CREDENTIAL_NAME = re.compile(
    r"(?:^|_)(?:API_KEY|ACCESS_KEY(?:_ID)?|ACCESS_TOKEN|AUTH_TOKEN|BEARER_TOKEN|"
    r"CLIENT_SECRET|PASSWORD|PRIVATE_KEY|SECRET|SESSION_TOKEN|SUBSCRIPTION_KEY|"
    r"TOKEN|CREDENTIALS?)"
    r"(?:_|$)"
)
_SQLITE_SIDECARS = ("-journal", "-shm", "-wal")
_MAX_FILES = 100_000
_MAX_MATCHES = 10_000
_MAX_ORPHANS = 10_000
_MAX_REASON_CODE_LENGTH = 128
_MAX_MARKER_BYTES = 1024
_REPARSE_POINT = 0x400
_NONCLAIMS = [
    "archive_is_preservation_not_database_repair",
    "nonempty_hot_rollback_journal_is_stop_unclassified",
    "no_connector_retry_refetch_or_transport_import",
    "unscoped_layer3_rows_are_inventory_only",
    "operator_authorization_required_before_any_later_cleanup",
    "producer_quiescence_required_hashes_detect_drift_not_atomic_snapshot",
]


class RecoveryRefusal(RuntimeError):
    """Fail-closed refusal with a stable, non-sensitive operator code."""


def _fail(code: str) -> NoReturn:
    if _SAFE_CODE.fullmatch(code) is None:
        code = "recovery_internal_error"
    raise RecoveryRefusal(code)


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _validate_identity(campaign_id: str, campaign_fingerprint: str) -> None:
    try:
        parsed = UUID(campaign_id)
    except (AttributeError, ValueError):
        _fail("campaign_id_invalid")
    if parsed.version != 4 or str(parsed) != campaign_id:
        _fail("campaign_id_invalid")
    if _SHA256.fullmatch(campaign_fingerprint) is None:
        _fail("fingerprint_invalid")


def _offline_environment(environ: Mapping[str, str]) -> None:
    normalized: dict[str, str] = {}
    for raw_name, value in environ.items():
        if not isinstance(raw_name, str) or not isinstance(value, str):
            _fail("environment_invalid")
        name = raw_name.upper()
        if name in normalized:
            _fail("environment_invalid")
        normalized[name] = value
    flag = normalized.get("CONNECTOR_LIVE_EGRESS_ENABLED", "")
    if flag.casefold() not in _FALSE_VALUES:
        _fail("egress_enabled" if flag else "egress_flag_missing")
    if any(normalized.get(name, "") for name in _AUTHORITY_VARIABLES):
        _fail("credential_environment_present")
    if any(
        value and _CREDENTIAL_NAME.search(name) for name, value in normalized.items()
    ):
        _fail("credential_environment_present")


def _has_reparse_component(path: Path) -> bool:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        if not current.exists():
            break
        try:
            current_stat = current.lstat()
        except OSError:
            return True
        attributes = int(getattr(current_stat, "st_file_attributes", 0))
        if stat.S_ISLNK(current_stat.st_mode) or attributes & _REPARSE_POINT:
            return True
    return False


def _existing_path(raw: str, *, kind: str, code: str) -> Path:
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        _fail(code)
    candidate = Path(raw)
    if not candidate.is_absolute() or raw.startswith(("\\\\", "//")):
        _fail(code)
    if _has_reparse_component(candidate):
        _fail(code)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        _fail(code)
    if _has_reparse_component(resolved):
        _fail(code)
    if kind == "file" and not resolved.is_file():
        _fail(code)
    if kind == "directory" and not resolved.is_dir():
        _fail(code)
    return resolved


def _destination_root(raw: str) -> Path:
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        _fail("archive_path_invalid")
    candidate = Path(raw)
    if not candidate.is_absolute() or raw.startswith(("\\\\", "//")):
        _fail("archive_path_invalid")
    if _has_reparse_component(candidate.parent):
        _fail("archive_path_invalid")
    try:
        resolved = candidate.resolve(strict=False)
        parent = resolved.parent.resolve(strict=True)
    except OSError:
        _fail("archive_path_invalid")
    if resolved.parent != parent or _has_reparse_component(parent):
        _fail("archive_path_invalid")
    if resolved.exists() and (
        not resolved.is_dir() or _has_reparse_component(resolved)
    ):
        _fail("archive_path_invalid")
    return resolved


def _identity(path: Path) -> tuple[int, int, int, int]:
    value = path.stat()
    if not stat.S_ISREG(value.st_mode):
        _fail("source_file_invalid")
    return value.st_mode, value.st_dev, value.st_ino, value.st_size


def _directory_identity(path: Path) -> tuple[int, int]:
    try:
        value = path.lstat()
    except OSError:
        _fail("capture_directory_changed")
    attributes = int(getattr(value, "st_file_attributes", 0))
    if (
        not stat.S_ISDIR(value.st_mode)
        or stat.S_ISLNK(value.st_mode)
        or attributes & _REPARSE_POINT
    ):
        _fail("capture_directory_changed")
    return int(value.st_dev), int(value.st_ino)


def _publish_marker_atomic(
    campaign_dir: Path,
    marker_path: Path,
    marker_bytes: bytes,
) -> dict[str, object]:
    backend_path = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "app"
        / "services"
        / "raw_storage_handles.py"
    )
    spec = importlib.util.spec_from_file_location(
        "project6_dual_live_recovery_raw_storage",
        backend_path,
    )
    if spec is None or spec.loader is None:
        _fail("poison_marker_backend_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        _fail("poison_marker_backend_unavailable")
    try:
        if module._windows_backend_available():
            handle, raw_identity = module._open_windows_directory_handle(campaign_dir)
            try:
                parent_identity = module.StableRawFileIdentity(
                    device_id=raw_identity[0],
                    file_id=raw_identity[1],
                )
            finally:
                module._close_windows_handle(handle)
        else:
            parent_stat = campaign_dir.lstat()
            parent_identity = module.StableRawFileIdentity(
                device_id=int(parent_stat.st_dev),
                file_id=int(parent_stat.st_ino),
            )
        snapshot = module.publish_atomic_strict_new_locked_raw_file(
            campaign_dir,
            marker_path,
            marker_bytes,
            max_bytes=_MAX_MARKER_BYTES,
            expected_parent_identity=parent_identity,
        )
    except (module.StableRawStorageError, OSError):
        _fail("poison_marker_write_failed")
    finally:
        sys.modules.pop(spec.name, None)
    return {
        "sha256": str(snapshot.sha256),
        "size": int(snapshot.size),
    }


def _hash_file(path: Path) -> dict[str, object]:
    before = _identity(path)
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                digest.update(block)
    except OSError:
        _fail("source_file_unreadable")
    if _identity(path) != before:
        _fail("source_file_changed")
    return {
        "absolute_path": str(path),
        "sha256": digest.hexdigest(),
        "size": before[3],
    }


def _collect_root_files(root: Path) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    try:
        candidates = sorted(root.rglob("*"), key=lambda item: item.as_posix())
    except OSError:
        _fail("source_tree_unreadable")
    if len(candidates) > _MAX_FILES:
        _fail("source_tree_too_large")
    for candidate in candidates:
        if _has_reparse_component(candidate):
            _fail("source_tree_reparse_present")
        if candidate.is_dir():
            continue
        if not candidate.is_file():
            _fail("source_tree_special_file_present")
        entry = _hash_file(candidate)
        entry["relative_path"] = candidate.relative_to(root).as_posix()
        files.append(entry)
    if not files:
        _fail("state_unclassified")
    return files


def _read_marker(
    path: Path,
    *,
    marker_kind: str,
    campaign_id: str,
    campaign_fingerprint: str,
) -> dict[str, object]:
    try:
        raw = path.read_bytes()
        decoded: object = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail("poison_marker_invalid")
    if type(decoded) is not dict or raw != _canonical_json_bytes(decoded):
        _fail("poison_marker_invalid")
    marker = decoded
    if (
        set(marker)
        != {
            "campaign_fingerprint",
            "campaign_id",
            "marker_kind",
            "reason_code",
            "schema_id",
        }
        or marker.get("schema_id") != _MARKER_SCHEMA
        or marker.get("campaign_id") != campaign_id
        or marker.get("campaign_fingerprint") != campaign_fingerprint
        or marker.get("marker_kind") != marker_kind
        or not isinstance(marker.get("reason_code"), str)
        or _SAFE_CODE.fullmatch(str(marker["reason_code"])) is None
        or len(str(marker["reason_code"])) > _MAX_REASON_CODE_LENGTH
    ):
        _fail("poison_marker_invalid")
    return _hash_file(path)


def _capture_inventory(
    evidence_root: Path,
    *,
    campaign_id: str,
    campaign_fingerprint: str,
) -> dict[str, object]:
    campaign_dir = evidence_root / "logs" / campaign_fingerprint
    seal_path = evidence_root / "log-seals" / f"{campaign_fingerprint}.json"
    if not campaign_dir.is_dir() or _has_reparse_component(campaign_dir):
        _fail("campaign_directory_missing")
    manifest_present = (campaign_dir / "manifest.json").is_file()
    seal_present = seal_path.is_file()
    if manifest_present and seal_present:
        _fail("capture_already_sealed")
    poison_path = campaign_dir / "poison.json"
    if not poison_path.is_file():
        _fail("poison_marker_missing")
    marker_kinds = ["poison"]
    markers = [
        _read_marker(
            poison_path,
            marker_kind="poison",
            campaign_id=campaign_id,
            campaign_fingerprint=campaign_fingerprint,
        )
    ]
    tombstone_path = campaign_dir / "tombstone.json"
    if tombstone_path.exists():
        if not tombstone_path.is_file():
            _fail("poison_marker_invalid")
        marker_kinds.append("tombstone")
        markers.append(
            _read_marker(
                tombstone_path,
                marker_kind="tombstone",
                campaign_id=campaign_id,
                campaign_fingerprint=campaign_fingerprint,
            )
        )
    return {
        "campaign_directory": str(campaign_dir),
        "manifest_present": manifest_present,
        "marker_kinds": marker_kinds,
        "markers": markers,
        "seal_present": seal_present,
        "seal_path": str(seal_path),
    }


def _quoted_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _row_identity(
    columns: list[tuple[Any, ...]], row: tuple[Any, ...]
) -> dict[str, object]:
    primary = sorted(
        ((int(column[5]), str(column[1])) for column in columns if int(column[5])),
        key=lambda item: item[0],
    )
    if not primary:
        _fail("layer3_schema_unclassified")
    positions = {str(column[1]): index for index, column in enumerate(columns)}
    return {name: row[positions[name]] for _ordinal, name in primary}


def _layer3_inventory(
    database_path: Path,
    *,
    campaign_id: str,
    preserved_clone: bool = False,
) -> tuple[str, dict[str, object]]:
    query = "mode=ro&cache=private" if preserved_clone else "mode=ro&immutable=1"
    try:
        database = sqlite3.connect(
            f"{database_path.as_uri()}?{query}",
            uri=True,
        )
    except sqlite3.Error:
        _fail("database_read_only_open_failed")
    try:
        database.execute("PRAGMA query_only = ON")
        database.execute("PRAGMA trusted_schema = OFF")
        integrity_rows = database.execute("PRAGMA integrity_check").fetchall()
        if integrity_rows != [("ok",)]:
            _fail("database_integrity_failed")
        tables = [
            str(row[0])
            for row in database.execute(
                "SELECT name FROM sqlite_schema "
                "WHERE type = 'table' AND name LIKE 'l3_%' ORDER BY name"
            )
        ]
        table_counts: list[dict[str, object]] = []
        campaign_scoped: list[dict[str, object]] = []
        for table in tables:
            quoted_table = _quoted_identifier(table)
            columns = database.execute(f"PRAGMA table_info({quoted_table})").fetchall()
            if not columns:
                _fail("layer3_schema_unclassified")
            names = [str(column[1]) for column in columns]
            row_count = int(
                database.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0]
            )
            table_counts.append({"row_count": row_count, "table": table})
            predicate = " OR ".join(
                f"instr(CAST({_quoted_identifier(name)} AS TEXT), ?) > 0"
                for name in names
            )
            rows = database.execute(
                f"SELECT * FROM {quoted_table} WHERE {predicate} LIMIT ?",
                (*([campaign_id] * len(names)), _MAX_MATCHES + 1),
            ).fetchall()
            if len(rows) > _MAX_MATCHES:
                _fail("campaign_inventory_too_large")
            if rows:
                campaign_scoped.append(
                    {
                        "matching_row_count": len(rows),
                        "row_count": row_count,
                        "rows": [
                            {
                                "identity": _row_identity(columns, row),
                                "matching_columns": [
                                    name
                                    for name, value in zip(names, row)
                                    if campaign_id in str(value)
                                ],
                            }
                            for row in rows
                        ],
                        "table": table,
                    }
                )
        raw_orphans = database.execute("PRAGMA foreign_key_check").fetchmany(
            _MAX_ORPHANS + 1
        )
        if len(raw_orphans) > _MAX_ORPHANS:
            _fail("orphan_inventory_too_large")
        orphans = [
            {
                "foreign_key_id": int(row[3]),
                "parent_table": str(row[2]),
                "rowid": int(row[1]),
                "table": str(row[0]),
            }
            for row in raw_orphans
            if str(row[0]).startswith("l3_")
        ]
    except (sqlite3.Error, TypeError, ValueError) as exc:
        if isinstance(exc, RecoveryRefusal):
            raise
        _fail("database_inventory_failed")
    finally:
        database.close()
    if not campaign_scoped and not orphans:
        _fail("state_unclassified")
    return "ok", {
        "campaign_scoped": campaign_scoped,
        "orphans": orphans,
        "tables": table_counts,
    }


def _database_files(database_path: Path) -> list[dict[str, object]]:
    files = [_hash_file(database_path)]
    for suffix in _SQLITE_SIDECARS:
        sidecar = Path(f"{database_path}{suffix}")
        if sidecar.exists():
            if not sidecar.is_file() or _has_reparse_component(sidecar):
                _fail("database_sidecar_invalid")
            files.append(_hash_file(sidecar))
    return files


def _recovery_sources(
    *,
    campaign_id: str,
    campaign_fingerprint: str,
    database_path: str,
    storage_root: str,
    evidence_root: str,
    environ: Mapping[str, str] | None,
) -> tuple[
    Path,
    Path,
    Path,
    dict[str, object],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    environment = os.environ if environ is None else environ
    _validate_identity(campaign_id, campaign_fingerprint)
    _offline_environment(environment)
    database = _existing_path(database_path, kind="file", code="database_path_invalid")
    storage = _existing_path(
        storage_root, kind="directory", code="storage_path_invalid"
    )
    evidence = _existing_path(
        evidence_root, kind="directory", code="evidence_path_invalid"
    )
    if len({database, storage, evidence}) != 3:
        _fail("source_paths_overlap")
    capture = _capture_inventory(
        evidence,
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
    )
    return (
        database,
        storage,
        evidence,
        capture,
        _database_files(database),
        _collect_root_files(storage),
        _collect_root_files(evidence),
    )


def poison_campaign(
    *,
    campaign_id: str,
    campaign_fingerprint: str,
    database_path: str,
    storage_root: str,
    evidence_root: str,
    reason_code: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    environment = os.environ if environ is None else environ
    _validate_identity(campaign_id, campaign_fingerprint)
    _offline_environment(environment)
    if (
        _SAFE_CODE.fullmatch(reason_code) is None
        or len(reason_code) > _MAX_REASON_CODE_LENGTH
    ):
        _fail("poison_reason_invalid")
    database = _existing_path(database_path, kind="file", code="database_path_invalid")
    storage = _existing_path(storage_root, kind="directory", code="storage_path_invalid")
    evidence = _existing_path(evidence_root, kind="directory", code="evidence_path_invalid")
    if len({database, storage, evidence}) != 3:
        _fail("source_paths_overlap")
    campaign_dir = _existing_path(
        str(evidence / "logs" / campaign_fingerprint),
        kind="directory",
        code="capture_directory_missing",
    )
    seal_path = evidence / "log-seals" / f"{campaign_fingerprint}.json"
    if (campaign_dir / "manifest.json").exists() or seal_path.exists():
        _fail("campaign_already_sealed")
    marker_path = campaign_dir / "poison.json"
    if marker_path.exists() or (campaign_dir / "tombstone.json").exists():
        _fail("poison_marker_exists")
    campaign_identity = _directory_identity(campaign_dir)

    database_before = _database_files(database)
    storage_before = _collect_root_files(storage)
    evidence_before = _collect_root_files(evidence)
    marker_bytes = _canonical_json_bytes(
        {
            "campaign_fingerprint": campaign_fingerprint,
            "campaign_id": campaign_id,
            "marker_kind": "poison",
            "reason_code": reason_code,
            "schema_id": _MARKER_SCHEMA,
        }
    )
    if (campaign_dir / "manifest.json").exists() or seal_path.exists():
        _fail("campaign_already_sealed")
    published = _publish_marker_atomic(
        campaign_dir,
        marker_path,
        marker_bytes,
    )
    marker_hash = _read_marker(
        marker_path,
        marker_kind="poison",
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
    )
    if (
        marker_hash["sha256"] != published["sha256"]
        or marker_hash["size"] != published["size"]
    ):
        _fail("poison_marker_write_failed")
    if (campaign_dir / "manifest.json").exists() or seal_path.exists():
        _fail("campaign_already_sealed")
    marker_relative = marker_path.relative_to(evidence).as_posix()
    evidence_after = [
        entry
        for entry in _collect_root_files(evidence)
        if entry["relative_path"] != marker_relative
    ]
    if (
        _database_files(database) != database_before
        or _collect_root_files(storage) != storage_before
        or evidence_after != evidence_before
        or _directory_identity(campaign_dir) != campaign_identity
    ):
        _fail("source_changed_during_poison")
    if (campaign_dir / "manifest.json").exists() or seal_path.exists():
        _fail("campaign_already_sealed")
    return {
        "action": "poison",
        "campaign_fingerprint": campaign_fingerprint,
        "campaign_id": campaign_id,
        "marker_path": str(marker_path),
        "marker_sha256": marker_hash["sha256"],
        "nonclaims": list(_NONCLAIMS),
        "reason_code": reason_code,
        "schema_id": _REPORT_SCHEMA,
        "status": "POISONED_UNSEALED",
    }


def inspect_campaign(
    *,
    campaign_id: str,
    campaign_fingerprint: str,
    database_path: str,
    storage_root: str,
    evidence_root: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    (
        database,
        _storage,
        _evidence,
        capture,
        database_files,
        storage_files,
        evidence_files,
    ) = _recovery_sources(
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
        database_path=database_path,
        storage_root=storage_root,
        evidence_root=evidence_root,
        environ=environ,
    )
    if any(
        entry["absolute_path"] == f"{database}-wal" and entry["size"] != 0
        for entry in database_files
    ):
        _fail("database_wal_uncheckpointed")
    if any(
        entry["absolute_path"] != str(database) and entry["size"] != 0
        for entry in database_files
    ):
        _fail("database_sidecar_requires_archive")
    integrity, inventory = _layer3_inventory(database, campaign_id=campaign_id)
    if _database_files(database) != database_files:
        _fail("database_changed_during_inspection")
    return {
        "action": "inspect",
        "campaign_fingerprint": campaign_fingerprint,
        "campaign_id": campaign_id,
        "capture": capture,
        "database": {
            "files": database_files,
            "integrity_check": integrity,
            "path": str(database),
        },
        "evidence_files": evidence_files,
        "inventory": inventory,
        "nonclaims": list(_NONCLAIMS),
        "schema_id": _REPORT_SCHEMA,
        "status": "POISONED_UNSEALED",
        "storage_files": storage_files,
    }


def _copy_exclusive(source: Path, destination: Path, expected_sha256: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    try:
        with source.open("rb") as reader, destination.open("xb") as writer:
            while block := reader.read(1024 * 1024):
                writer.write(block)
                digest.update(block)
            writer.flush()
            os.fsync(writer.fileno())
    except (FileExistsError, OSError):
        _fail("archive_copy_failed")
    if digest.hexdigest() != expected_sha256:
        _fail("archive_copy_hash_mismatch")


def archive_campaign(
    *,
    campaign_id: str,
    campaign_fingerprint: str,
    database_path: str,
    storage_root: str,
    evidence_root: str,
    archive_root: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    (
        database,
        storage,
        evidence,
        capture,
        database_files,
        storage_files,
        evidence_files,
    ) = _recovery_sources(
        campaign_id=campaign_id,
        campaign_fingerprint=campaign_fingerprint,
        database_path=database_path,
        storage_root=storage_root,
        evidence_root=evidence_root,
        environ=environ,
    )
    root = _destination_root(archive_root)
    if any(
        root == source or root.is_relative_to(source) for source in (storage, evidence)
    ):
        _fail("archive_path_overlaps_source")
    archive_dir = root / campaign_id
    if archive_dir.exists():
        _fail("archive_exists")
    try:
        root.mkdir(exist_ok=True)
        archive_dir.mkdir()
    except (FileExistsError, OSError):
        _fail("archive_create_failed")

    planned: list[dict[str, object]] = []
    for entry in database_files:
        planned.append(
            {
                **entry,
                "archive_relative_path": (
                    f"database/raw/{Path(entry['absolute_path']).name}"
                ),
                "scope": "database_raw",
            }
        )
    for scope, source_root, entries in (
        ("storage", storage, storage_files),
        ("evidence", evidence, evidence_files),
    ):
        for entry in entries:
            planned.append(
                {
                    **entry,
                    "archive_relative_path": f"{scope}/{entry['relative_path']}",
                    "scope": scope,
                }
            )
    planned.sort(key=lambda item: str(item["archive_relative_path"]))
    for entry in planned:
        _copy_exclusive(
            Path(str(entry["absolute_path"])),
            archive_dir / str(entry["archive_relative_path"]),
            str(entry["sha256"]),
        )
    for entry in planned:
        source = Path(str(entry["absolute_path"]))
        copied = archive_dir / str(entry["archive_relative_path"])
        if (
            _hash_file(source)["sha256"] != entry["sha256"]
            or _hash_file(copied)["sha256"] != entry["sha256"]
        ):
            _fail("archive_verification_failed")

    raw_database_dir = archive_dir / "database" / "raw"
    inspection_dir = archive_dir / "database" / "inspect"
    try:
        inspection_dir.mkdir(parents=True)
    except (FileExistsError, OSError):
        _fail("archive_create_failed")
    inspection_database = inspection_dir / database.name
    raw_by_name = {
        Path(str(entry["absolute_path"])).name: (
            archive_dir / str(entry["archive_relative_path"]),
            str(entry["sha256"]),
        )
        for entry in planned
        if entry["scope"] == "database_raw"
    }
    for suffix in ("", "-journal", "-wal"):
        name = f"{database.name}{suffix}"
        raw_entry = raw_by_name.get(name)
        if raw_entry is not None:
            _copy_exclusive(
                raw_entry[0],
                Path(f"{inspection_database}{suffix}"),
                raw_entry[1],
            )
    integrity, inventory = _layer3_inventory(
        inspection_database,
        campaign_id=campaign_id,
        preserved_clone=True,
    )
    derived_files = _collect_root_files(inspection_dir)

    if (
        _database_files(database) != database_files
        or _collect_root_files(storage) != storage_files
        or _collect_root_files(evidence) != evidence_files
    ):
        _fail("source_changed_during_archive")
    for entry in database_files:
        raw_path = raw_database_dir / Path(str(entry["absolute_path"])).name
        if _hash_file(raw_path)["sha256"] != entry["sha256"]:
            _fail("archive_verification_failed")

    for entry in derived_files:
        planned.append(
            {
                **entry,
                "archive_relative_path": (f"database/inspect/{entry['relative_path']}"),
                "scope": "derived_inspection",
            }
        )
    planned.sort(key=lambda item: str(item["archive_relative_path"]))
    manifest_files = [
        {
            "absolute_path": entry["absolute_path"],
            "archive_relative_path": entry["archive_relative_path"],
            "scope": entry["scope"],
            "sha256": entry["sha256"],
            "size": entry["size"],
        }
        for entry in planned
    ]
    manifest = {
        "campaign_fingerprint": campaign_fingerprint,
        "campaign_id": campaign_id,
        "capture": capture,
        "classification": "POISONED_UNSEALED",
        "database_integrity_check": integrity,
        "files": manifest_files,
        "inventory": inventory,
        "nonclaims": list(_NONCLAIMS),
        "schema_id": _ARCHIVE_SCHEMA,
    }
    manifest_bytes = _canonical_json_bytes(manifest)
    manifest_path = archive_dir / "manifest.json"
    try:
        with manifest_path.open("xb") as stream:
            stream.write(manifest_bytes)
            stream.flush()
            os.fsync(stream.fileno())
    except (FileExistsError, OSError):
        _fail("archive_manifest_write_failed")
    if manifest_path.read_bytes() != manifest_bytes:
        _fail("archive_manifest_verification_failed")
    return {
        "action": "archive",
        "archive_path": str(archive_dir),
        "campaign_fingerprint": campaign_fingerprint,
        "campaign_id": campaign_id,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "schema_id": _REPORT_SCHEMA,
        "status": "ARCHIVED_POISONED_UNSEALED",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dual_live_recovery")
    parser.add_argument("action", choices=("poison", "inspect", "archive"))
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--campaign-fingerprint", required=True)
    parser.add_argument("--database-path", required=True)
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--archive-root")
    parser.add_argument("--reason-code")
    return parser


def main(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    sys.dont_write_bytecode = True
    try:
        if not sys.flags.isolated:
            _fail("isolated_mode_required")
        arguments = _parser().parse_args(sys.argv[1:] if argv is None else argv)
        values = {
            "campaign_id": arguments.campaign_id,
            "campaign_fingerprint": arguments.campaign_fingerprint,
            "database_path": arguments.database_path,
            "storage_root": arguments.storage_root,
            "evidence_root": arguments.evidence_root,
            "environ": os.environ if environ is None else environ,
        }
        if arguments.action == "archive":
            if arguments.archive_root is None:
                _fail("archive_path_missing")
            if arguments.reason_code is not None:
                _fail("poison_reason_unexpected")
            result = archive_campaign(archive_root=arguments.archive_root, **values)
        elif arguments.action == "poison":
            if arguments.archive_root is not None:
                _fail("archive_path_unexpected")
            if arguments.reason_code is None:
                _fail("poison_reason_missing")
            result = poison_campaign(reason_code=arguments.reason_code, **values)
        else:
            if arguments.archive_root is not None:
                _fail("archive_path_unexpected")
            if arguments.reason_code is not None:
                _fail("poison_reason_unexpected")
            result = inspect_campaign(**values)
        os.write(1, _canonical_json_bytes(result))
        return 0
    except RecoveryRefusal as exc:
        os.write(
            2,
            _canonical_json_bytes(
                {
                    "schema_id": _REPORT_SCHEMA,
                    "status": "REFUSED",
                    "code": str(exc),
                }
            ),
        )
        return 2
    except SystemExit:
        return 2
    except BaseException:
        os.write(
            2,
            _canonical_json_bytes(
                {
                    "schema_id": _REPORT_SCHEMA,
                    "status": "REFUSED",
                    "code": "recovery_internal_error",
                }
            ),
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
