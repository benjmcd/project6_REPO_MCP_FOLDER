from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA_ID = "project6.local_profile_acceptance.v1"
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
CHILD_TIMEOUT_SECONDS = 150

CSV_BYTES = (
    b"date,revenue,traffic,temperature\n"
    b"2024-01-01,100,200,50\n"
    b"2024-01-02,102,210,51\n"
    b"2024-01-03,300,230,49\n"
    b"2024-01-04,110,220,52\n"
    b"2024-01-05,108,218,48\n"
    b"2024-01-06,112,225,47\n"
    b",,,\n"
)

PINNED_FALSE_ENV = (
    "LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED",
    "LAYER3_MODEL_EGRESS_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    "SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def _sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise AssertionError(f"expected sqlite database URL, got {database_url!r}")
    return Path(database_url[len(prefix) :]).resolve()


def _artifact_path(storage_dir: Path, storage_ref: str) -> Path:
    normalized = storage_ref.replace("\\", "/").lstrip("/")
    if normalized.startswith("storage/"):
        normalized = normalized[len("storage/") :]
    return (storage_dir / normalized).resolve()


def _artifact_hashes(storage_dir: Path, analysis: dict[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for artifact in analysis.get("artifacts", []):
        storage_ref = str(artifact.get("storage_ref") or "")
        if not storage_ref:
            raise AssertionError(f"artifact is missing storage_ref: {artifact}")
        path = _artifact_path(storage_dir, storage_ref)
        try:
            path.relative_to(storage_dir.resolve())
        except ValueError as exc:
            raise AssertionError(f"artifact escaped storage dir: {storage_ref}") from exc
        if not path.is_file():
            raise AssertionError(f"artifact file missing for {storage_ref}: {path}")
        hashes[storage_ref] = _sha256_file(path)
    if not hashes:
        raise AssertionError("analysis produced no artifact files")
    return hashes


def _sorted_records(records: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        raise AssertionError(f"analysis {label} is not a list")
    return sorted(
        records,
        key=lambda item: json.dumps(item, sort_keys=True, default=str),
    )


def _assert_same_records(actual: Any, expected: Any, label: str) -> None:
    if _sorted_records(actual, label) != _sorted_records(expected, label):
        raise AssertionError(f"analysis {label} changed after restart/restore")


def _local_env(db_path: Path, storage_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": _sqlite_url(db_path),
            "STORAGE_DIR": str(storage_dir.resolve()),
            "DB_INIT_MODE": "migrate",
            "DEPLOYMENT_MODE": "local",
            "AUTH_OWNER": "none",
            "TRUSTED_PROXY_MODE": "false",
            "LAYER3_ROUTE_AUTHORIZATION_MODE": "identity_presence",
            "STORAGE_EXPOSURE": "auto",
            "PROXY_IDENTITY_HEADER": "",
            "PROXY_ROLES_HEADER": "",
        }
    )
    for key in PINNED_FALSE_ENV:
        env[key] = "false"
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(BACKEND)
        if not existing_pythonpath
        else str(BACKEND) + os.pathsep + existing_pythonpath
    )
    return env


def _assert_local_settings(settings: Any, db_path: Path, storage_dir: Path) -> None:
    assert settings.deployment_mode == "local", settings.deployment_mode
    assert settings.auth_owner == "none", settings.auth_owner
    assert settings.trusted_proxy_mode is False, settings.trusted_proxy_mode
    assert settings.layer3_route_authorization_mode == "identity_presence"
    assert _sqlite_path(settings.database_url) == db_path.resolve()
    assert Path(settings.storage_dir).resolve() == storage_dir.resolve()


def _load_client(db_path: Path, storage_dir: Path) -> Any:
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from fastapi.testclient import TestClient
    from main import app
    from app.core.config import settings

    _assert_local_settings(settings, db_path, storage_dir)
    return TestClient(app, raise_server_exceptions=False)


def _require_status(response: Any, status_code: int, label: str) -> Any:
    if response.status_code != status_code:
        raise AssertionError(
            f"{label} returned {response.status_code}, expected {status_code}: {response.text}"
        )
    return response.json()


def _raw_version(dataset: dict[str, Any], version_id: str) -> dict[str, Any]:
    for version in dataset.get("versions", []):
        if version.get("dataset_version_id") == version_id:
            return version
    raise AssertionError(f"raw dataset version not found: {version_id}")


def _profile_count(
    client: Any,
    dataset_id: str,
    version_id: str,
    label: str,
    *,
    detect_stationarity: bool,
) -> int:
    profiles = _require_status(
        client.post(
            f"/api/v1/datasets/{dataset_id}/versions/{version_id}/profile",
            json={
                "detect_seasonality": False,
                "detect_stationarity": detect_stationarity,
            },
        ),
        200,
        f"POST profile {label} version",
    )
    count = len(profiles)
    if count <= 0:
        raise AssertionError(f"profile {label} version returned no variable profiles")
    return count


def _seed(db_path: Path, storage_dir: Path) -> dict[str, Any]:
    client = _load_client(db_path, storage_dir)
    ready = _require_status(client.get("/ready"), 200, "GET /ready")
    if ready.get("status") != "ready":
        raise AssertionError(f"GET /ready did not report ready: {ready}")

    expected_hash = _sha256_bytes(CSV_BYTES)
    upload = _require_status(
        client.post(
            "/api/v1/sources/upload",
            files={"file": ("demo.csv", io.BytesIO(CSV_BYTES), "text/csv")},
            data={
                "name": "Local Profile Demo",
                "description": "Local profile operational acceptance fixture",
                "domain_pack": "macro",
                "primary_time_column": "date",
            },
        ),
        200,
        "POST /api/v1/sources/upload",
    )
    dataset_id = upload["dataset_id"]
    version_id = upload["dataset_version_id"]
    if upload.get("content_hash") != expected_hash:
        raise AssertionError("upload content_hash does not match raw CSV bytes")
    if upload.get("source_row_count") != 7 or upload.get("dropped_row_count") != 1:
        raise AssertionError(f"unexpected source-fidelity fields: {upload}")

    _require_status(
        client.post(
            f"/api/v1/datasets/{dataset_id}/versions/{version_id}/profile",
            json={"detect_seasonality": False, "detect_stationarity": False},
        ),
        200,
        "POST profile raw version",
    )
    _require_status(
        client.post(f"/api/v1/datasets/{dataset_id}/versions/{version_id}/transformations/recommend"),
        200,
        "POST transformation recommend",
    )
    transformed = _require_status(
        client.post(
            f"/api/v1/datasets/{dataset_id}/versions/{version_id}/transformations/apply",
            json={
                "version_label": "scaled_v1",
                "rationale": "local profile operational acceptance",
                "steps": [
                    {"variable_name": "revenue", "method_name": "robust", "parameters": {}},
                    {"variable_name": "traffic", "method_name": "z_score", "parameters": {}},
                    {"variable_name": "temperature", "method_name": "min_max", "parameters": {}},
                ],
            },
        ),
        200,
        "POST transformation apply",
    )
    transformed_version_id = transformed["output_dataset_version_id"]
    _require_status(
        client.post(
            f"/api/v1/datasets/{dataset_id}/versions/{transformed_version_id}/profile",
            json={"detect_seasonality": False, "detect_stationarity": True},
        ),
        200,
        "POST profile transformed version",
    )
    annotation = _require_status(
        client.post(
            f"/api/v1/datasets/{dataset_id}/versions/{transformed_version_id}/annotations",
            json={
                "label": "shock window",
                "annotation_type": "event_window",
                "start_time": "2024-01-02T00:00:00",
                "end_time": "2024-01-05T00:00:00",
                "notes": "local profile restart/restore proof",
            },
        ),
        200,
        "POST annotation",
    )
    analysis = _require_status(
        client.post(
            "/api/v1/analysis-runs",
            json={
                "dataset_version_id": transformed_version_id,
                "method_name": "cross_correlation",
                "goal_type": "exploratory",
                "parameters": {"max_lag": 2},
                "annotation_window_id": annotation["annotation_window_id"],
            },
        ),
        200,
        "POST /api/v1/analysis-runs",
    )
    if not analysis.get("artifacts") or not analysis.get("assumptions") or not analysis.get("caveats"):
        raise AssertionError("analysis did not produce artifacts, assumptions, and caveats")
    stationarity = next(
        item for item in analysis["assumptions"]
        if item.get("assumption_name") == "series_stationarity"
    )
    if stationarity.get("notes") == "no_profile_data":
        raise AssertionError("analysis did not use transformed-version profile data")

    dataset = _require_status(
        client.get(f"/api/v1/datasets/{dataset_id}"),
        200,
        "GET /api/v1/datasets/{id}",
    )
    raw = _raw_version(dataset, version_id)
    source_fidelity = {
        "content_hash": raw.get("content_hash"),
        "row_count": raw.get("row_count"),
        "source_row_count": raw.get("source_row_count"),
        "dropped_row_count": raw.get("dropped_row_count"),
    }
    if source_fidelity != {
        "content_hash": expected_hash,
        "row_count": 6,
        "source_row_count": 7,
        "dropped_row_count": 1,
    }:
        raise AssertionError(f"unexpected persisted source fidelity: {source_fidelity}")

    return {
        "dataset_id": dataset_id,
        "raw_version_id": version_id,
        "transformed_version_id": transformed_version_id,
        "analysis_run_id": analysis["analysis_run_id"],
        "analysis": analysis,
        "dataset": dataset,
        "source_fidelity": source_fidelity,
        "artifact_hashes": _artifact_hashes(storage_dir, analysis),
    }


def _verify(
    db_path: Path,
    storage_dir: Path,
    expected: dict[str, Any],
    *,
    require_dataframe_reads: bool = False,
) -> dict[str, Any]:
    client = _load_client(db_path, storage_dir)
    _require_status(client.get("/ready"), 200, "GET /ready")

    analysis = _require_status(
        client.get(f"/api/v1/analysis-runs/{expected['analysis_run_id']}"),
        200,
        "GET /api/v1/analysis-runs/{id}",
    )
    for key in ("artifacts", "assumptions", "caveats"):
        _assert_same_records(analysis.get(key), expected["analysis"].get(key), key)

    dataset = _require_status(
        client.get(f"/api/v1/datasets/{expected['dataset_id']}"),
        200,
        "GET /api/v1/datasets/{id}",
    )
    raw = _raw_version(dataset, expected["raw_version_id"])
    source_fidelity = {
        "content_hash": raw.get("content_hash"),
        "row_count": raw.get("row_count"),
        "source_row_count": raw.get("source_row_count"),
        "dropped_row_count": raw.get("dropped_row_count"),
    }
    if source_fidelity != expected["source_fidelity"]:
        raise AssertionError(
            f"source fidelity changed: expected {expected['source_fidelity']}, got {source_fidelity}"
        )

    artifact_hashes = _artifact_hashes(storage_dir, analysis)
    if artifact_hashes != expected["artifact_hashes"]:
        raise AssertionError(
            f"artifact hashes changed: expected {expected['artifact_hashes']}, got {artifact_hashes}"
        )
    dataframe_reads: dict[str, int] = {}
    if require_dataframe_reads:
        dataframe_reads = {
            "raw_profile_count": _profile_count(
                client,
                expected["dataset_id"],
                expected["raw_version_id"],
                "raw",
                detect_stationarity=False,
            ),
            "transformed_profile_count": _profile_count(
                client,
                expected["dataset_id"],
                expected["transformed_version_id"],
                "transformed",
                detect_stationarity=True,
            ),
        }
    return {
        "analysis_run_id": analysis["analysis_run_id"],
        "dataset_id": expected["dataset_id"],
        "content_hash": source_fidelity["content_hash"],
        "artifact_hashes": artifact_hashes,
        "dataframe_reads": dataframe_reads,
    }


def _run_child(
    mode: str,
    db_path: Path,
    storage_dir: Path,
    snapshot_path: Path | None = None,
    *,
    require_dataframe_reads: bool = False,
) -> dict[str, Any]:
    args = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child-mode",
        mode,
        "--db-path",
        str(db_path),
        "--storage-dir",
        str(storage_dir),
    ]
    if snapshot_path is not None:
        args.extend(["--snapshot", str(snapshot_path)])
    if require_dataframe_reads:
        args.append("--require-dataframe-reads")
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=_local_env(db_path, storage_dir),
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"child {mode} failed with {result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
    stdout_lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not stdout_lines:
        raise RuntimeError(
            f"child {mode} produced no JSON output\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
    return json.loads(stdout_lines[-1])


def _ensure_clean_work_dir(work_dir: Path) -> None:
    if work_dir.exists() and any(work_dir.iterdir()):
        raise ValueError("work directory must be empty")
    work_dir.mkdir(parents=True, exist_ok=True)


def _copy_file(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _run_acceptance(work_dir: Path) -> dict[str, Any]:
    _ensure_clean_work_dir(work_dir)
    runtime_dir = work_dir / "runtime"
    backup_dir = work_dir / "backup"
    archive_dir = work_dir / "archive"
    runtime_dir.mkdir(parents=True)
    db_path = runtime_dir / "method_aware.db"
    storage_dir = runtime_dir / "storage"

    seeded = _run_child("seed", db_path, storage_dir)
    snapshot_path = work_dir / "snapshot.json"
    snapshot_path.write_text(json.dumps(seeded, indent=2, sort_keys=True), encoding="utf-8")

    restart = _run_child("verify", db_path, storage_dir, snapshot_path)

    backup_dir.mkdir(parents=True)
    db_backup = backup_dir / "method_aware.db"
    storage_backup = backup_dir / "storage"
    _copy_file(db_path, db_backup)
    shutil.copytree(storage_dir, storage_backup)

    offline_runtime = archive_dir / "original-runtime"
    archive_dir.mkdir(parents=True)
    shutil.move(str(runtime_dir), str(offline_runtime))
    if runtime_dir.exists():
        raise AssertionError(f"runtime was not relocated before restore: {runtime_dir}")
    _copy_file(db_backup, db_path)
    shutil.copytree(storage_backup, storage_dir)
    restored = _run_child(
        "verify",
        db_path,
        storage_dir,
        snapshot_path,
        require_dataframe_reads=True,
    )

    return {
        "schema_id": SCHEMA_ID,
        "profile": {
            "DEPLOYMENT_MODE": "local",
            "AUTH_OWNER": "none",
            "database": "sqlite",
            "proxy": "none",
        },
        "claims": {
            "install_run": "passed",
            "restart_survival": "passed",
            "backup_restore": "passed",
            "upgrade": "not_claimed",
        },
        "work_dir": str(work_dir.resolve()),
        "source_fidelity": seeded["source_fidelity"],
        "restart": restart,
        "restored": restored,
        "artifact_hashes": seeded["artifact_hashes"],
        "backup": {
            "sqlite_sha256": _sha256_file(db_backup),
            "storage_manifest": sorted(seeded["artifact_hashes"].keys()),
            "original_runtime_relocated": True,
            "original_runtime_archive": str(offline_runtime.resolve()),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Local profile operational acceptance proof")
    parser.add_argument("--work-dir", type=Path, help="empty directory for isolated runtime state")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--child-mode", choices=("seed", "verify"), help=argparse.SUPPRESS)
    parser.add_argument("--db-path", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--storage-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--snapshot", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--require-dataframe-reads", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    try:
        if args.child_mode:
            if args.db_path is None or args.storage_dir is None:
                raise ValueError("--db-path and --storage-dir are required for child mode")
            db_path = args.db_path.resolve()
            storage_dir = args.storage_dir.resolve()
            if args.child_mode == "seed":
                payload = _seed(db_path, storage_dir)
            else:
                if args.snapshot is None:
                    raise ValueError("--snapshot is required for verify child mode")
                expected = json.loads(args.snapshot.read_text(encoding="utf-8"))
                payload = _verify(
                    db_path,
                    storage_dir,
                    expected,
                    require_dataframe_reads=args.require_dataframe_reads,
                )
            print(json.dumps(payload, sort_keys=True))
            return 0

        if args.work_dir is None:
            raise ValueError("--work-dir is required")
        payload = _run_acceptance(args.work_dir.resolve())
        text = json.dumps(payload, indent=None if args.json else 2, sort_keys=True)
        print(text)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
