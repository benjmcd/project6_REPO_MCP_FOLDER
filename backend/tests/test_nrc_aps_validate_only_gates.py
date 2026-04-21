from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import connectors_sciencebase
from app.services import nrc_aps_validate_only_gates as validate_only_runtime
from app.services import nrc_aps_validate_only_gates_contract as validate_only_contract
from app.services import nrc_aps_validate_only_gates_gate as validate_only_gate
from app.services import review_nrc_aps_gate_reports
from app.services.review_nrc_aps_graph import (
    build_file_to_node_map,
    build_pipeline_projection,
    build_run_projection,
)
from app.services.review_nrc_aps_tree import build_pipeline_layout


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_runtime_db(runtime_root: Path, *, run_id: str) -> None:
    database_path = runtime_root / "lc.db"
    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute(
            """
            CREATE TABLE connector_run (
                connector_run_id TEXT PRIMARY KEY,
                connector_key TEXT,
                status TEXT,
                query_plan_json TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO connector_run (connector_run_id, connector_key, status, query_plan_json)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, "nrc_adams_aps", "completed", json.dumps({})),
        )
        connection.commit()
    finally:
        connection.close()


def _load_query_plan(runtime_root: Path, *, run_id: str) -> dict:
    connection = sqlite3.connect(str(runtime_root / "lc.db"))
    try:
        row = connection.execute(
            """
            SELECT query_plan_json
            FROM connector_run
            WHERE connector_run_id = ?
              AND connector_key = ?
            LIMIT 1
            """,
            (run_id, "nrc_adams_aps"),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    raw_query_plan = str(row[0] or "")
    return json.loads(raw_query_plan) if raw_query_plan else {}


def _create_review_runtime(
    tmp_path: Path,
    *,
    run_id: str = "run/validate only:001",
) -> tuple[Path, Path]:
    storage_root = tmp_path / "storage_test_runtime"
    runtime_root = storage_root / "lc_e2e" / "runtime_validate_only"
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "storage" / "connectors" / "reports").mkdir(parents=True, exist_ok=True)

    gate_report_root = runtime_root / "gate_reports"
    gate_results: dict[str, dict] = {}
    for spec in review_nrc_aps_gate_reports.GATE_REPORT_SPECS:
        report_path = gate_report_root / spec.report_name
        _write_json(report_path, {"passed": True, "checked_runs": 1})
        gate_results[spec.gate_name] = {
            "script": spec.script_name,
            "report_path": str(report_path.resolve()),
            "passed": True,
            "checked_runs": 1,
            "stdout": "",
            "stderr": "",
        }

    _write_json(
        runtime_root / "local_corpus_e2e_summary.json",
        {
            "schema_id": review_nrc_aps_gate_reports.SUMMARY_SCHEMA_ID,
            "schema_version": 1,
            "run_id": run_id,
            "passed": True,
            "generated_at_utc": "2026-04-21T00:05:00Z",
            "database_path": "lc.db",
            "storage_dir": "storage",
            "submission": {
                "submitted_at": "2026-04-21T00:00:00Z",
                "selected_count": 0,
                "downloaded_count": 0,
                "failed_count": 0,
            },
            "run_detail": {
                "status": "completed",
                "completed_at": "2026-04-21T00:05:00Z",
                "selected_count": 0,
                "downloaded_count": 0,
                "failed_count": 0,
                "report_refs": {},
            },
            "gate_results": gate_results,
            "selected_branch_rows": [],
            "downstream_artifacts": {},
        },
    )
    _write_runtime_db(runtime_root, run_id=run_id)
    return storage_root, runtime_root


def test_refresh_validate_only_gates_persists_registry_and_gate(monkeypatch, tmp_path: Path) -> None:
    run_id = "run/validate only:001"
    storage_root, runtime_root = _create_review_runtime(tmp_path, run_id=run_id)
    monkeypatch.setattr(settings, "storage_dir", str(storage_root))

    result = validate_only_runtime.refresh_validate_only_gates(
        run_id=run_id,
        review_root=runtime_root,
    )

    assert result["persisted"] is True
    artifact_ref = str(result["validate_only_gates_ref"] or "")
    assert artifact_ref

    query_plan = _load_query_plan(runtime_root, run_id=run_id)
    report_refs = dict(query_plan.get("aps_validate_only_gates_report_refs") or {})
    assert report_refs["aps_validate_only_gates_artifacts"] == [artifact_ref]
    assert report_refs["aps_validate_only_gates_failures"] == []
    summaries = list(query_plan.get("aps_validate_only_gates_summaries") or [])
    assert len(summaries) == 1
    assert summaries[0]["ref"] == artifact_ref
    assert summaries[0]["owner_run_id"] == run_id

    gate_report = validate_only_gate.validate_validate_only_gates_gate(
        run_ids=[run_id],
        limit=1,
        report_path=tmp_path / "validate_only_gates_gate.json",
        require_runs=True,
    )
    assert gate_report["passed"] is True
    assert gate_report["checks"][0]["validate_only_gates_refs"] == [artifact_ref]

    flattened_refs = connectors_sciencebase._connector_report_refs_for_run(
        SimpleNamespace(
            connector_run_id=run_id,
            query_plan_json=query_plan,
            report_ref=None,
        )
    )
    assert flattened_refs["aps_validate_only_gates_artifacts"] == [artifact_ref]
    assert flattened_refs["aps_validate_only_gates_failures"] == []


def test_review_graph_and_layout_surface_validate_only_artifact(tmp_path: Path) -> None:
    _storage_root, runtime_root = _create_review_runtime(tmp_path)
    run_id = "run/validate only:001"

    refreshed = validate_only_runtime.refresh_validate_only_gates(
        run_id=run_id,
        review_root=runtime_root,
    )
    artifact_path = Path(str(refreshed["validate_only_gates_ref"]))
    artifact_name = artifact_path.name

    pipeline = build_pipeline_projection(run_id, runtime_root)
    run_graph = build_run_projection(run_id, runtime_root)
    file_map = build_file_to_node_map(run_graph)
    validate_pipeline = next(node for node in pipeline.nodes if node.projection_id == "validate_only_gates")
    validate_run = next(node for node in run_graph.nodes if node.projection_id == "validate_only_gates")

    assert validate_pipeline.structured_summary["has_validate_only_artifact"] is True
    assert validate_run.structured_summary["has_validate_only_artifact"] is True
    assert any(ref.endswith(artifact_name) for ref in validate_pipeline.mapped_file_refs)
    assert any(ref.endswith(artifact_name) for ref in validate_run.mapped_file_refs)
    artifact_rel = next(ref for ref in validate_run.mapped_file_refs if ref.endswith(artifact_name))
    assert file_map[artifact_rel] == ["validate_only_gates"]

    layout = build_pipeline_layout(run_id, runtime_root)
    downstream = next(section for section in layout.sections if section.title == "Downstream")
    validate_entry = next(entry for entry in downstream.entries if entry.label == "Validate-only artifact")
    assert validate_entry.value == "present"
    assert str(validate_entry.path or "").endswith(artifact_name)


def test_refresh_validate_only_gates_fails_closed_on_summary_gate_report_drift(tmp_path: Path) -> None:
    _storage_root, runtime_root = _create_review_runtime(tmp_path, run_id="run-validate-only-drift")
    summary_path = runtime_root / "local_corpus_e2e_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    first_gate_name = next(iter(summary["gate_results"].keys()))
    summary["gate_results"][first_gate_name]["report_path"] = str((runtime_root / "gate_reports" / "wrong.json").resolve())
    _write_json(summary_path, summary)

    with pytest.raises(validate_only_runtime.ValidateOnlyGatesError) as excinfo:
        validate_only_runtime.refresh_validate_only_gates(
            run_id="run-validate-only-drift",
            review_root=runtime_root,
        )

    assert excinfo.value.code == validate_only_contract.APS_RUNTIME_FAILURE_GATE_REPORTS_MISMATCH
    failure_path = validate_only_runtime.validate_only_gates_failure_path(
        owner_run_id="run-validate-only-drift",
        error_code=validate_only_contract.APS_RUNTIME_FAILURE_GATE_REPORTS_MISMATCH,
        review_root=runtime_root,
    )
    assert failure_path.exists()
    failure_payload = json.loads(failure_path.read_text(encoding="utf-8"))
    assert failure_payload["error_code"] == validate_only_contract.APS_RUNTIME_FAILURE_GATE_REPORTS_MISMATCH
