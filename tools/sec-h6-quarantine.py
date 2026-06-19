from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from typing import Any


SCHEMA_ID = "tools.sec_xbrl_raw_at_rest_quarantine.v1"
ARCHIVE_NAME = "sec-h6"
ARCHIVE_RELATIVE_DIR = Path("backend") / "app" / "storage_archive"
MAX_SCAN_BYTES = 4 * 1024 * 1024

FILE_SINKS = (
    ("live_source_receipts", Path("layer3-sec-edgar-live-source-artifact-acquisition") / "receipts", "*.json"),
    ("live_source_request_bindings", Path("layer3-sec-edgar-live-source-artifact-acquisition") / "requests", "*.json"),
    ("live_source_artifacts", Path("layer3-sec-edgar-live-source-artifact-acquisition") / "artifacts", "*"),
    ("companyfacts_receipts", Path("layer3-sec-xbrl-companyfacts") / "receipts", "*.json"),
    ("companyfacts_artifacts", Path("layer3-sec-xbrl-companyfacts") / "companyfacts-store", "*.json"),
    ("sidecar_receipts", Path("layer3-sec-edgar-arelle-resolved-fact-authority") / "receipts", "*.json"),
    ("sidecar_request_bindings", Path("layer3-sec-edgar-arelle-resolved-fact-authority") / "request-bindings", "*.json"),
    ("sidecar_internal_value_stores", Path("layer3-sec-edgar-arelle-resolved-fact-authority") / "internal-value-stores", "*.json"),
    ("value_reveal_receipts", Path("layer3-sec-edgar-arelle-value-reveal") / "receipts", "*.json"),
)

DB_TABLES = (
    "l3_sec_xbrl_auth_binding_receipt",
    "l3_sec_xbrl_value_reveal_authority_receipt",
    "l3_sec_xbrl_controlled_value_reveal_submit_receipt",
    "connector_run",
    "dataset_source_provenance",
    "dataset",
    "dataset_version",
)


@dataclass(frozen=True)
class FileCandidate:
    kind: str
    path: Path
    storage_relative_path: str
    sha256: str
    byte_count: int
    matched_by: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": str(self.path),
            "storage_relative_path": self.storage_relative_path,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
            "matched_by": list(self.matched_by),
        }


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_text(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            return handle.read(MAX_SCAN_BYTES).decode("utf-8", errors="ignore")
    except OSError:
        return ""


def match_tokens(value: str, *, run_id: str, run_id_hash: str) -> list[str]:
    matches: list[str] = []
    if run_id and run_id in value:
        matches.append("run_id")
    if run_id_hash and run_id_hash in value:
        matches.append("run_id_sha256")
    return matches


def build_inventory(
    *,
    run_id: str,
    storage_root: Path,
    sqlite_db: Path | None = None,
) -> dict[str, Any]:
    storage_root = storage_root.resolve()
    run_id_hash = sha256_text(run_id)
    candidates: dict[Path, FileCandidate] = {}
    sink_counts = {kind: 0 for kind, _relative_dir, _pattern in FILE_SINKS}
    for kind, relative_dir, pattern in FILE_SINKS:
        directory = storage_root / relative_dir
        if not directory.exists():
            continue
        for path in sorted(item for item in directory.glob(pattern) if item.is_file()):
            sink_counts[kind] += 1
            matches = match_tokens(path.name, run_id=run_id, run_id_hash=run_id_hash)
            matches.extend(match_tokens(scan_text(path), run_id=run_id, run_id_hash=run_id_hash))
            if matches:
                _add_candidate(
                    candidates,
                    kind=kind,
                    path=path,
                    storage_root=storage_root,
                    matched_by=tuple(sorted(set(matches))),
                )
    _add_linked_file_candidates(candidates, storage_root=storage_root)
    db_rows = scan_sqlite_rows(sqlite_db, run_id=run_id, run_id_hash=run_id_hash) if sqlite_db else []
    file_candidates = sorted(candidates.values(), key=lambda item: item.storage_relative_path)
    return {
        "schema_id": SCHEMA_ID,
        "mode": "dry_run",
        "generated_at": utc_now(),
        "run_id_hash": run_id_hash,
        "storage_root": str(storage_root),
        "file_candidate_count": len(file_candidates),
        "db_row_candidate_count": len(db_rows),
        "sink_file_counts": sink_counts,
        "files": [candidate.as_dict() for candidate in file_candidates],
        "db_rows": db_rows,
        "zero_mutation": True,
        "mutation_performed": False,
        "default_off": True,
        "source_acquisition_performed": False,
        "sec_egress_performed": False,
        "arelle_invoked": False,
        "value_reveal_performed": False,
        "db_mutation_performed": False,
        "next_allowed_actions": ["rerun_with_execute_and_double_confirmation_to_quarantine_files"],
    }


def _add_candidate(
    candidates: dict[Path, FileCandidate],
    *,
    kind: str,
    path: Path,
    storage_root: Path,
    matched_by: tuple[str, ...],
) -> None:
    path = path.resolve()
    if path in candidates or not path.exists() or not path.is_file():
        return
    try:
        relative_path = path.relative_to(storage_root.resolve()).as_posix()
    except ValueError:
        relative_path = path.name
    candidates[path] = FileCandidate(
        kind=kind,
        path=path,
        storage_relative_path=relative_path,
        sha256=file_sha256(path),
        byte_count=path.stat().st_size,
        matched_by=matched_by,
    )


def _add_linked_file_candidates(candidates: dict[Path, FileCandidate], *, storage_root: Path) -> None:
    changed = True
    while changed:
        changed = False
        for candidate in list(candidates.values()):
            payload = read_json_file(candidate.path)
            if payload is None:
                continue
            for kind, path in _linked_paths(payload, storage_root=storage_root):
                before = len(candidates)
                _add_candidate(
                    candidates,
                    kind=kind,
                    path=path,
                    storage_root=storage_root,
                    matched_by=(f"linked_from:{candidate.kind}",),
                )
                changed = changed or len(candidates) > before
    _add_value_reveal_receipts_for_sidecars(candidates, storage_root=storage_root)


def _linked_paths(payload: dict[str, Any], *, storage_root: Path) -> list[tuple[str, Path]]:
    linked: list[tuple[str, Path]] = []
    live_receipt_id = _text(payload.get("live_source_artifact_receipt_id"))
    if live_receipt_id:
        live_root = storage_root / "layer3-sec-edgar-live-source-artifact-acquisition"
        linked.append(("live_source_receipts", live_root / "receipts" / f"{live_receipt_id}.json"))
        linked.append(("live_source_artifacts", live_root / "artifacts" / f"{live_receipt_id}.txt"))
    companyfacts_receipt_id = _text(payload.get("companyfacts_receipt_id"))
    if companyfacts_receipt_id:
        companyfacts_root = storage_root / "layer3-sec-xbrl-companyfacts"
        linked.append(("companyfacts_receipts", companyfacts_root / "receipts" / f"{companyfacts_receipt_id}.json"))
        linked.append(("companyfacts_artifacts", companyfacts_root / "companyfacts-store" / f"{companyfacts_receipt_id}.json"))
    sidecar_receipt_id = _text(payload.get("sidecar_receipt_id"))
    if sidecar_receipt_id:
        sidecar_root = storage_root / "layer3-sec-edgar-arelle-resolved-fact-authority"
        linked.append(("sidecar_receipts", sidecar_root / "receipts" / f"{sidecar_receipt_id}.json"))
        linked.append(("sidecar_internal_value_stores", sidecar_root / "internal-value-stores" / f"{sidecar_receipt_id}.json"))
    return linked


def _add_value_reveal_receipts_for_sidecars(candidates: dict[Path, FileCandidate], *, storage_root: Path) -> None:
    sidecar_ids = _sidecar_receipt_ids(candidates)
    if not sidecar_ids:
        return
    directory = storage_root / "layer3-sec-edgar-arelle-value-reveal" / "receipts"
    if not directory.exists():
        return
    for path in sorted(item for item in directory.glob("*.json") if item.is_file()):
        text = scan_text(path)
        if any(sidecar_id in text for sidecar_id in sidecar_ids):
            _add_candidate(
                candidates,
                kind="value_reveal_receipts",
                path=path,
                storage_root=storage_root,
                matched_by=("linked_from:sidecar_receipt_id",),
            )


def _sidecar_receipt_ids(candidates: dict[Path, FileCandidate]) -> set[str]:
    sidecar_ids: set[str] = set()
    for candidate in candidates.values():
        payload = read_json_file(candidate.path)
        if payload is None:
            continue
        sidecar_id = _text(payload.get("sidecar_receipt_id"))
        if sidecar_id:
            sidecar_ids.add(sidecar_id)
    return sidecar_ids


def scan_sqlite_rows(sqlite_db: Path, *, run_id: str, run_id_hash: str) -> list[dict[str, Any]]:
    sqlite_db = sqlite_db.resolve()
    if not sqlite_db.exists():
        return [
            {
                "database": str(sqlite_db),
                "status": "sqlite_db_missing",
                "db_mutation_performed": False,
            }
        ]
    rows: list[dict[str, Any]] = []
    conn = sqlite3.connect(str(sqlite_db))
    conn.row_factory = sqlite3.Row
    try:
        existing_tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        for table in DB_TABLES:
            if table not in existing_tables:
                continue
            columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]  # noqa: S608
            for row in conn.execute(f"SELECT * FROM {table}"):  # noqa: S608
                row_dict = {column: row[column] for column in columns}
                serial = json.dumps(row_dict, default=str, sort_keys=True)
                matches = match_tokens(serial, run_id=run_id, run_id_hash=run_id_hash)
                if matches:
                    rows.append(
                        {
                            "database": str(sqlite_db),
                            "table": table,
                            "row_ref": _row_ref(row_dict),
                            "row_sha256": sha256_text(serial),
                            "matched_by": sorted(set(matches)),
                            "db_mutation_performed": False,
                        }
                    )
    finally:
        conn.close()
    return rows


def quarantine_files(
    inventory: dict[str, Any],
    *,
    run_id: str,
    storage_root: Path,
    repo_root: Path,
    confirm_run_id: str,
    confirm_quarantine: bool,
    ack_outside_repo_onedrive: bool,
) -> dict[str, Any]:
    run_id_hash = sha256_text(run_id)
    report = dict(inventory)
    report["mode"] = "quarantine"
    report["zero_mutation"] = False
    report["mutation_performed"] = False
    report["db_mutation_performed"] = False
    report["confirmations"] = {
        "confirm_run_id_matches": confirm_run_id == run_id,
        "confirm_quarantine": bool(confirm_quarantine),
        "ack_outside_repo_onedrive": bool(ack_outside_repo_onedrive),
    }
    files = [Path(item["path"]).resolve() for item in inventory.get("files", [])]
    refusals = _preflight_refusals(
        files,
        run_id=run_id,
        storage_root=storage_root.resolve(),
        repo_root=repo_root.resolve(),
        confirm_run_id=confirm_run_id,
        confirm_quarantine=confirm_quarantine,
        ack_outside_repo_onedrive=ack_outside_repo_onedrive,
    )
    archive_dir = (repo_root / ARCHIVE_RELATIVE_DIR).resolve()
    move_plan = _move_plan(files, storage_root=storage_root.resolve(), archive_dir=archive_dir, run_id_hash=run_id_hash)
    manifest = archive_dir / f"{ARCHIVE_NAME}-{run_id_hash[:16]}-manifest.json"
    if manifest.exists():
        refusals.append({"code": "archive_manifest_exists", "path": str(manifest)})
    for target in move_plan.values():
        if target.exists():
            refusals.append({"code": "archive_target_exists", "path": str(target)})
    if refusals:
        report["status"] = "refused"
        report["refusals"] = refusals
        report["moved_files"] = []
        return report
    archive_dir.mkdir(parents=True, exist_ok=True)
    moved_files: list[dict[str, str]] = []
    for source, target in move_plan.items():
        shutil.move(str(source), str(target))
        moved_files.append({"source": str(source), "archive_path": str(target)})
    report["status"] = "quarantined"
    report["mutation_performed"] = bool(moved_files)
    report["moved_files"] = moved_files
    report["archive_manifest"] = str(manifest)
    manifest.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def _preflight_refusals(
    files: list[Path],
    *,
    run_id: str,
    storage_root: Path,
    repo_root: Path,
    confirm_run_id: str,
    confirm_quarantine: bool,
    ack_outside_repo_onedrive: bool,
) -> list[dict[str, str]]:
    refusals: list[dict[str, str]] = []
    if not files:
        refusals.append({"code": "empty_inventory_no_quarantine", "path": ""})
    if not run_id or confirm_run_id != run_id:
        refusals.append({"code": "confirm_run_id_mismatch", "path": ""})
    if not confirm_quarantine:
        refusals.append({"code": "confirm_quarantine_missing", "path": ""})
    onedrive_roots = _onedrive_roots()
    for path in files:
        if not is_relative_to(path, storage_root):
            refusals.append({"code": "candidate_outside_storage_root", "path": str(path)})
        inside_repo_or_onedrive = is_relative_to(path, repo_root) or any(is_relative_to(path, root) for root in onedrive_roots)
        if not inside_repo_or_onedrive and not ack_outside_repo_onedrive:
            refusals.append({"code": "candidate_outside_repo_or_onedrive_without_ack", "path": str(path)})
    return refusals


def _move_plan(files: list[Path], *, storage_root: Path, archive_dir: Path, run_id_hash: str) -> dict[Path, Path]:
    plan: dict[Path, Path] = {}
    for source in sorted(files):
        try:
            relative = source.relative_to(storage_root).as_posix()
        except ValueError:
            relative = source.name
        name_hash = sha256_text(relative)[:16]
        suffix = source.suffix if source.suffix else ".bin"
        flattened_name = f"{ARCHIVE_NAME}-{run_id_hash[:12]}-{name_hash}{suffix.lower()}"
        plan[source] = archive_dir / flattened_name
    return plan


def _onedrive_roots() -> list[Path]:
    roots: list[Path] = []
    for key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        raw = os.environ.get(key)
        if raw:
            roots.append(Path(raw).resolve())
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        default = Path(user_profile) / "OneDrive"
        if default.exists():
            roots.append(default.resolve())
    return roots


def _row_ref(row: dict[str, Any]) -> str:
    for key in sorted(row):
        if key.endswith("_id") and row.get(key):
            return f"{key}:{row[key]}"
    for key in sorted(row):
        if key.endswith("_hash") and row.get(key):
            return f"{key}:{row[key]}"
    return "row"


def _text(value: Any) -> str:
    return str(value or "").strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SEC XBRL H6 raw-at-rest dry-run inventory and guarded quarantine helper.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--storage-root", required=True)
    parser.add_argument("--sqlite-db", default="")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-run-id", default="")
    parser.add_argument("--confirm-quarantine", action="store_true")
    parser.add_argument("--ack-outside-repo-onedrive", action="store_true")
    args = parser.parse_args(argv)
    inventory = build_inventory(
        run_id=args.run_id,
        storage_root=Path(args.storage_root),
        sqlite_db=Path(args.sqlite_db) if args.sqlite_db else None,
    )
    if args.execute:
        report = quarantine_files(
            inventory,
            run_id=args.run_id,
            storage_root=Path(args.storage_root),
            repo_root=Path(args.repo_root),
            confirm_run_id=args.confirm_run_id,
            confirm_quarantine=args.confirm_quarantine,
            ack_outside_repo_onedrive=args.ack_outside_repo_onedrive,
        )
    else:
        report = inventory
    print(json.dumps(report, sort_keys=True, indent=2))
    return 2 if report.get("status") == "refused" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
