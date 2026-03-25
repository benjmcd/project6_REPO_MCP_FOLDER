from __future__ import annotations

from pathlib import Path

from app.core.config import settings


def report_refs(connector_run_id: str) -> dict[str, str]:
    base = Path(settings.connector_reports_dir)
    return {
        "run_summary": str(base / f"{connector_run_id}_run_summary.json"),
        "targets_failures": str(base / f"{connector_run_id}_targets_failures.csv"),
        "targets_selected": str(base / f"{connector_run_id}_targets_selected.csv"),
        "versioning_decisions": str(base / f"{connector_run_id}_versioning_decisions.csv"),
        "checkpoint_history": str(base / f"{connector_run_id}_checkpoint_history.json"),
        "artifact_dedup_report": str(base / f"{connector_run_id}_artifact_dedup_report.json"),
        "event_log": str(base / f"{connector_run_id}_event_log.ndjson"),
        "aps_sync_delta": str(base / f"{connector_run_id}_aps_sync_delta_v1.json"),
        "aps_sync_drift": str(base / f"{connector_run_id}_aps_sync_drift_v1.json"),
        "aps_sync_drift_failure": str(base / f"{connector_run_id}_aps_sync_drift_failure_v1.json"),
        "aps_safeguard": str(base / f"{connector_run_id}_aps_safeguard_v1.json"),
    }


def report_status(connector_run_id: str) -> dict[str, bool]:
    refs = report_refs(connector_run_id)
    return {name: Path(path).exists() for name, path in refs.items()}
