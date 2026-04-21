from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services import nrc_aps_sync_drift
from app.services.review_nrc_aps_runtime import (
    ReviewRuntimeBinding,
    load_summary,
    resolve_runtime_binding_for_run,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SUMMARY_SCHEMA_ID = "aps.local_corpus_e2e_summary.v1"


@dataclass(frozen=True)
class GateReportSpec:
    gate_name: str
    script_name: str
    report_name: str


GATE_REPORT_SPECS: tuple[GateReportSpec, ...] = (
    GateReportSpec("artifact_ingestion", "nrc_aps_artifact_ingestion_gate.py", "artifact_ingestion.json"),
    GateReportSpec("content_index", "nrc_aps_content_index_gate.py", "content_index.json"),
    GateReportSpec("evidence_bundle", "nrc_aps_evidence_bundle_gate.py", "evidence_bundle.json"),
    GateReportSpec("evidence_citation_pack", "nrc_aps_evidence_citation_pack_gate.py", "evidence_citation_pack.json"),
    GateReportSpec("evidence_report", "nrc_aps_evidence_report_gate.py", "evidence_report.json"),
    GateReportSpec("evidence_report_export", "nrc_aps_evidence_report_export_gate.py", "evidence_report_export.json"),
    GateReportSpec("evidence_report_export_package", "nrc_aps_evidence_report_export_package_gate.py", "evidence_report_export_package.json"),
    GateReportSpec("context_packet", "nrc_aps_context_packet_gate.py", "context_packet.json"),
    GateReportSpec("context_dossier", "nrc_aps_context_dossier_gate.py", "context_dossier.json"),
    GateReportSpec("deterministic_insight_artifact", "nrc_aps_deterministic_insight_artifact_gate.py", "deterministic_insight_artifact.json"),
    GateReportSpec("deterministic_challenge_artifact", "nrc_aps_deterministic_challenge_artifact_gate.py", "deterministic_challenge_artifact.json"),
    GateReportSpec(
        "deterministic_challenge_review_packet",
        "nrc_aps_deterministic_challenge_review_packet_gate.py",
        "deterministic_challenge_review_packet.json",
    ),
)


def _sqlite_url_for_path(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_review_runtime_binding(*, run_id: str, review_root: str | Path | None = None) -> ReviewRuntimeBinding:
    binding = resolve_runtime_binding_for_run(run_id=run_id, review_root=review_root)
    if str(binding.summary.get("schema_id") or "").strip() != SUMMARY_SCHEMA_ID:
        raise ValueError(f"Review root summary is not {SUMMARY_SCHEMA_ID}: {binding.review_root}")
    return binding


def run_gate_reports_for_run(
    *,
    run_id: str,
    report_dir: str | Path,
    database_path: str | Path,
    storage_dir: str | Path,
    python_executable: str | Path | None = None,
    require_runs: bool = True,
) -> dict[str, Any]:
    requested_run_id = str(run_id or "").strip()
    if not requested_run_id:
        raise ValueError("run_id is required")

    report_root = Path(report_dir).resolve()
    report_root.mkdir(parents=True, exist_ok=True)
    resolved_database_path = Path(database_path).resolve()
    if not resolved_database_path.exists() or not resolved_database_path.is_file():
        raise FileNotFoundError(f"Runtime database is missing: {resolved_database_path}")
    resolved_storage_dir = Path(storage_dir).resolve()
    if not resolved_storage_dir.exists() or not resolved_storage_dir.is_dir():
        raise FileNotFoundError(f"Runtime storage dir is missing: {resolved_storage_dir}")

    env = dict(os.environ)
    env["DB_INIT_MODE"] = "none"
    env["DATABASE_URL"] = _sqlite_url_for_path(resolved_database_path)
    env["STORAGE_DIR"] = str(resolved_storage_dir)

    interpreter = str(Path(python_executable).resolve()) if python_executable else sys.executable
    gate_results: dict[str, Any] = {}
    overall_passed = True

    for spec in GATE_REPORT_SPECS:
        report_path = report_root / spec.report_name
        command = [
            interpreter,
            str((REPO_ROOT / "tools" / spec.script_name).resolve()),
            "--run-id",
            requested_run_id,
            "--report",
            str(report_path),
        ]
        if not require_runs:
            command.append("--allow-empty")

        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        payload = _read_json(report_path)
        passed = completed.returncode == 0 and bool(payload.get("passed"))
        overall_passed = overall_passed and passed
        gate_results[spec.gate_name] = {
            "script": spec.script_name,
            "report_path": str(report_path),
            "passed": passed,
            "checked_runs": int(payload.get("checked_runs") or 0),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    return {
        "run_id": requested_run_id,
        "report_dir": str(report_root),
        "passed": overall_passed,
        "gate_results": gate_results,
    }


def refresh_review_gate_reports(
    *,
    run_id: str,
    review_root: str | Path | None = None,
    python_executable: str | Path | None = None,
    require_runs: bool = True,
) -> dict[str, Any]:
    binding = resolve_review_runtime_binding(run_id=run_id, review_root=review_root)
    gate_report_result = run_gate_reports_for_run(
        run_id=binding.run_id,
        report_dir=binding.review_root / "gate_reports",
        database_path=binding.database_path,
        storage_dir=binding.storage_dir,
        python_executable=python_executable,
        require_runs=require_runs,
    )

    summary = dict(binding.summary)
    summary["gate_results"] = gate_report_result["gate_results"]
    nrc_aps_sync_drift.write_json_deterministic(binding.review_root / "local_corpus_e2e_summary.json", summary)

    return {
        "run_id": binding.run_id,
        "review_root": str(binding.review_root),
        "database_path": str(binding.database_path),
        "storage_dir": str(binding.storage_dir),
        "passed": gate_report_result["passed"],
        "gate_results": gate_report_result["gate_results"],
        "report_dir": gate_report_result["report_dir"],
    }
