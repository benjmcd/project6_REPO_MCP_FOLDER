from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.core.config import settings


BATCH_SCHEMA_ID = "aps.live_validation_batch.v1"
BATCH_SCHEMA_VERSION = 1
BATCH_COLLECTOR_VERSION = "nrc_aps_live_batch_collector_v1"
LIVE_REPORT_SCHEMA_ID = "aps.live_validation_report.v1"
LIVE_REPORT_SCHEMA_VERSION = 1
BATCH_MANIFEST_CHECKSUM_ALGORITHM = "sha256"


class BatchManifestValidationError(RuntimeError):
    """Raised when a finalized manifest fails contract validation."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _payload_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: str | Path, payload: dict[str, Any]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    target.write_text(serialized, encoding="utf-8")
    return str(target)


def _manifest_hash_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    cloned = dict(manifest)
    cloned["manifest_sha256"] = None
    cloned["manifest_checksum"] = {
        **dict(cloned.get("manifest_checksum") or {}),
        "value": None,
    }
    return cloned


def _default_batch_root() -> Path:
    return Path(settings.connector_reports_dir) / "nrc_aps_live_batches"


def _default_live_script_path() -> Path:
    return Path(__file__).resolve().parents[3] / "tools" / "run_nrc_aps_live_validation.py"


def _default_cycle_runner(
    *,
    cycle_index: int,
    output_path: Path,
    timeout_seconds: int,
    pagination_max_pages: int,
    pagination_take: int,
    url_probe_bytes: int,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(_default_live_script_path()),
        "--timeout-seconds",
        str(int(timeout_seconds)),
        "--pagination-max-pages",
        str(int(pagination_max_pages)),
        "--pagination-take",
        str(int(pagination_take)),
        "--url-probe-bytes",
        str(int(url_probe_bytes)),
        "--output",
        str(output_path),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "exit_code": int(completed.returncode),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def collect_live_validation_batch(
    *,
    cycle_count: int,
    spacing_seconds: float,
    timeout_seconds: int,
    pagination_max_pages: int,
    pagination_take: int,
    url_probe_bytes: int,
    continue_on_cycle_failure: bool = True,
    batch_root: str | Path | None = None,
    cycle_runner: Callable[..., dict[str, Any]] | None = None,
    invocation_argv: list[str] | None = None,
) -> dict[str, Any]:
    planned_cycles = max(1, int(cycle_count))
    spacing = max(0.0, float(spacing_seconds))
    root = Path(batch_root) if batch_root else _default_batch_root()
    batch_id = f"aps_live_batch_{_utc_now().strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    batch_dir = root / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = batch_dir / f"{batch_id}_manifest_v1.json"
    sidecar_path = manifest_path.with_suffix(manifest_path.suffix + ".sha256")

    manifest: dict[str, Any] = {
        "schema_id": BATCH_SCHEMA_ID,
        "schema_version": BATCH_SCHEMA_VERSION,
        "batch_id": batch_id,
        "created_at_utc": _iso_utc(_utc_now()),
        "started_at_utc": None,
        "completed_at_utc": None,
        "finalized_at_utc": None,
        "collector_version": BATCH_COLLECTOR_VERSION,
        "collector_invocation_argv": [str(item) for item in (invocation_argv or [])],
        "collector_invocation": {
            "tool": "tools/nrc_aps_live_validation_batch.py",
        },
        "collector_config": {
            "cycle_count": planned_cycles,
            "spacing_seconds": spacing,
            "timeout_seconds": int(timeout_seconds),
            "pagination_max_pages": int(pagination_max_pages),
            "pagination_take": int(pagination_take),
            "url_probe_bytes": int(url_probe_bytes),
            "continue_on_cycle_failure": bool(continue_on_cycle_failure),
        },
        "cycle_spacing_seconds_requested": spacing,
        "cycle_spacing_enforced": True,
        "cycle_spacing_affects_batch_validity": False,
        "planned_cycle_count": planned_cycles,
        "attempted_cycle_count": 0,
        "completed_cycle_count": 0,
        "failed_cycle_count": 0,
        "batch_status": "running",
        "finalized": False,
        "cycle_reports": [],
        "manifest_checksum": {
            "algorithm": BATCH_MANIFEST_CHECKSUM_ALGORITHM,
            "value": None,
            "sidecar_file": sidecar_path.name,
        },
        "manifest_sha256": None,
    }

    runner = cycle_runner or _default_cycle_runner
    manifest["started_at_utc"] = _iso_utc(_utc_now())
    previous_started: datetime | None = None

    for index in range(1, planned_cycles + 1):
        started = _utc_now()
        output_path = batch_dir / f"{batch_id}_cycle_{index:03d}_aps_live_validation_v1.json"
        cycle_result = runner(
            cycle_index=index,
            output_path=output_path,
            timeout_seconds=timeout_seconds,
            pagination_max_pages=pagination_max_pages,
            pagination_take=pagination_take,
            url_probe_bytes=url_probe_bytes,
        )
        completed = _utc_now()
        manifest["attempted_cycle_count"] = int(manifest["attempted_cycle_count"]) + 1

        cycle_record: dict[str, Any] = {
            "cycle_index": index,
            "status": "failed",
            "started_at_utc": _iso_utc(started),
            "completed_at_utc": _iso_utc(completed),
            "duration_seconds": round(max(0.0, (completed - started).total_seconds()), 6),
            "requested_spacing_seconds": spacing,
            "actual_spacing_seconds_from_previous": round(max(0.0, (started - previous_started).total_seconds()), 6)
            if previous_started
            else None,
            "report_ref": str(output_path),
            "report_sha256": None,
            "report_schema_id": None,
            "report_schema_version": None,
            "v1_status": None,
            "exit_code": int(cycle_result.get("exit_code") or 0),
            "stdout_tail": str(cycle_result.get("stdout") or "")[-2000:],
            "stderr_tail": str(cycle_result.get("stderr") or "")[-2000:],
            "failure_reason_code": None,
        }
        previous_started = started

        if int(cycle_record["exit_code"]) == 0 and output_path.exists():
            try:
                report_payload = json.loads(output_path.read_text(encoding="utf-8"))
                tests_payload = dict(report_payload.get("tests") or {})
                v1_payload = dict(tests_payload.get("APS-V1_qps_ramp_test") or {})
                cycle_record["status"] = "completed"
                cycle_record["report_sha256"] = _file_sha256(output_path)
                cycle_record["report_schema_id"] = str(report_payload.get("schema_id") or "")
                cycle_record["report_schema_version"] = int(report_payload.get("schema_version") or 0)
                cycle_record["v1_status"] = str(v1_payload.get("status") or "")
                manifest["completed_cycle_count"] = int(manifest["completed_cycle_count"]) + 1
            except Exception as exc:  # noqa: BLE001
                cycle_record["status"] = "failed"
                cycle_record["failure_reason_code"] = f"report_parse_failed:{exc.__class__.__name__}"
                manifest["failed_cycle_count"] = int(manifest["failed_cycle_count"]) + 1
        else:
            cycle_record["failure_reason_code"] = "cycle_execution_failed"
            manifest["failed_cycle_count"] = int(manifest["failed_cycle_count"]) + 1

        manifest["cycle_reports"].append(cycle_record)

        if cycle_record["status"] == "failed" and not continue_on_cycle_failure:
            manifest["batch_status"] = "aborted"
            break
        if index < planned_cycles:
            time.sleep(spacing)

    if str(manifest.get("batch_status") or "") != "aborted":
        failed_count = int(manifest.get("failed_cycle_count") or 0)
        manifest["batch_status"] = "completed_with_failures" if failed_count > 0 else "completed"
    manifest["completed_at_utc"] = _iso_utc(_utc_now())
    manifest["finalized"] = True
    manifest["finalized_at_utc"] = _iso_utc(_utc_now())
    manifest_hash = _payload_sha256(_manifest_hash_payload(manifest))
    manifest["manifest_sha256"] = manifest_hash
    manifest["manifest_checksum"] = {
        "algorithm": BATCH_MANIFEST_CHECKSUM_ALGORITHM,
        "value": manifest_hash,
        "sidecar_file": sidecar_path.name,
    }

    _write_json(manifest_path, manifest)
    sidecar_path.write_text(str(manifest_hash) + "\n", encoding="utf-8")
    return {
        "batch_id": batch_id,
        "batch_dir": str(batch_dir),
        "manifest_ref": str(manifest_path),
        "manifest_sha256_ref": str(sidecar_path),
    }


def load_and_validate_finalized_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise BatchManifestValidationError("manifest_missing")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BatchManifestValidationError("manifest_not_object")
    if str(payload.get("schema_id") or "") != BATCH_SCHEMA_ID:
        raise BatchManifestValidationError("manifest_schema_id_invalid")
    if int(payload.get("schema_version") or 0) != BATCH_SCHEMA_VERSION:
        raise BatchManifestValidationError("manifest_schema_version_invalid")
    if not bool(payload.get("finalized")):
        raise BatchManifestValidationError("manifest_not_finalized")
    if str(payload.get("batch_status") or "") not in {"completed", "completed_with_failures", "aborted"}:
        raise BatchManifestValidationError("manifest_batch_status_invalid")

    manifest_hash = str(payload.get("manifest_sha256") or "").strip()
    if not manifest_hash:
        raise BatchManifestValidationError("manifest_sha256_missing")

    checksum = dict(payload.get("manifest_checksum") or {})
    checksum_algorithm = str(checksum.get("algorithm") or "").strip().lower()
    checksum_value = str(checksum.get("value") or "").strip()
    checksum_sidecar_name = str(checksum.get("sidecar_file") or "").strip()
    if checksum_algorithm != BATCH_MANIFEST_CHECKSUM_ALGORITHM:
        raise BatchManifestValidationError("manifest_checksum_algorithm_invalid")
    if checksum_value != manifest_hash:
        raise BatchManifestValidationError("manifest_checksum_value_mismatch")

    computed_hash = _payload_sha256(_manifest_hash_payload(payload))
    if manifest_hash != computed_hash:
        raise BatchManifestValidationError("manifest_sha256_mismatch")

    sidecar_path = manifest_path.with_suffix(manifest_path.suffix + ".sha256")
    if checksum_sidecar_name and checksum_sidecar_name != sidecar_path.name:
        raise BatchManifestValidationError("manifest_sidecar_name_mismatch")
    if not sidecar_path.exists():
        raise BatchManifestValidationError("manifest_sidecar_missing")
    sidecar_hash = str(sidecar_path.read_text(encoding="utf-8").strip())
    if sidecar_hash != manifest_hash:
        raise BatchManifestValidationError("manifest_sidecar_sha256_mismatch")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect isolated NRC APS live-validation batches.")
    parser.add_argument("--cycle-count", type=int, default=3)
    parser.add_argument("--spacing-seconds", type=float, default=5.0)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--pagination-max-pages", type=int, default=5)
    parser.add_argument("--pagination-take", type=int, default=50)
    parser.add_argument("--url-probe-bytes", type=int, default=262144)
    parser.add_argument("--batch-root", default=str(_default_batch_root()))
    parser.add_argument("--abort-on-failure", action="store_true")
    args = parser.parse_args(argv)

    summary = collect_live_validation_batch(
        cycle_count=args.cycle_count,
        spacing_seconds=args.spacing_seconds,
        timeout_seconds=args.timeout_seconds,
        pagination_max_pages=args.pagination_max_pages,
        pagination_take=args.pagination_take,
        url_probe_bytes=args.url_probe_bytes,
        continue_on_cycle_failure=not bool(args.abort_on_failure),
        batch_root=args.batch_root,
        invocation_argv=list(argv or sys.argv[1:]),
    )
    print(f"batch_id={summary['batch_id']}")
    print(f"manifest={summary['manifest_ref']}")
    return 0
