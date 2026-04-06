from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.api.deps import get_db
from app.services.review_nrc_aps_runtime_roots import candidate_review_runtime_roots
from main import app
from review_nrc_aps_runtime_fixture import discover_passed_runtimes


RUN_ID = "d6be0fff-bbd7-468a-9b00-7103d5995494"
MULTI_RUNTIME_RUN_IDS = {runtime.run_id for runtime in discover_passed_runtimes()[:3]}


def override_get_db():
    from unittest.mock import MagicMock

    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    yield db


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _write_runtime_summary(runtime_dir: Path, *, run_id: str) -> None:
    payload = {
        "schema_id": "aps.local_corpus_e2e_summary.v1",
        "schema_version": 1,
        "run_id": run_id,
        "passed": True,
        "generated_at_utc": "2026-04-05T20:00:00Z",
        "submission": {"submitted_at": "2026-04-05T19:50:00Z"},
        "run_detail": {
            "status": "completed",
            "completed_at": "2026-04-05T20:00:00Z",
            "selected_count": 1,
            "downloaded_count": 1,
            "failed_count": 0,
            "report_refs": {
                "aps_artifact_ingestion": "present",
                "aps_content_index": "present",
            },
        },
    }
    (runtime_dir / "local_corpus_e2e_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _write_runtime_db(runtime_dir: Path, *, run_id: str, visual_lane_mode: str | None, include_connector_run_row: bool) -> None:
    database_path = runtime_dir / "lc.db"
    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute(
            """
            CREATE TABLE connector_run (
                connector_run_id TEXT PRIMARY KEY,
                connector_key TEXT,
                request_config_json TEXT,
                status TEXT
            )
            """
        )
        connection.execute("CREATE TABLE connector_run_target (connector_run_target_id TEXT PRIMARY KEY)")
        connection.execute("CREATE TABLE aps_content_linkage (content_id TEXT)")
        connection.execute("CREATE TABLE aps_content_document (content_id TEXT)")
        connection.execute("CREATE TABLE aps_content_chunk (chunk_id TEXT)")
        if include_connector_run_row:
            request_config_json = json.dumps({"visual_lane_mode": visual_lane_mode}) if visual_lane_mode is not None else json.dumps({})
            connection.execute(
                """
                INSERT INTO connector_run (connector_run_id, connector_key, request_config_json, status)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, "nrc_adams_aps", request_config_json, "completed"),
            )
        connection.commit()
    finally:
        connection.close()


def _create_temp_review_runtime(
    base_storage_root: Path,
    *,
    runtime_name: str,
    run_id: str,
    visual_lane_mode: str | None,
    include_connector_run_row: bool,
) -> Path:
    runtime_dir = base_storage_root / "lc_e2e" / runtime_name
    runtime_dir.mkdir(parents=True, exist_ok=True)
    _write_runtime_summary(runtime_dir, run_id=run_id)
    _write_runtime_db(
        runtime_dir,
        run_id=run_id,
        visual_lane_mode=visual_lane_mode,
        include_connector_run_row=include_connector_run_row,
    )
    return runtime_dir


@patch("app.api.review_nrc_aps.discover_candidate_runs")
def test_api_runs(mock_discover):
    from app.schemas.review_nrc_aps import NrcApsReviewRunSelectorItemOut, NrcApsReviewRunSelectorOut

    mock_discover.return_value = NrcApsReviewRunSelectorOut(
        default_run_id=RUN_ID,
        runs=[NrcApsReviewRunSelectorItemOut(run_id=RUN_ID, submitted_at="2026-03-27T06:20:11Z", reviewable=True)],
    )
    response = client.get("/api/v1/review/nrc-aps/runs")
    assert response.status_code == 200
    assert response.json()["default_run_id"] == RUN_ID


def test_api_pipeline_definition_returns_projection():
    response = client.get(f"/api/v1/review/nrc-aps/pipeline-definition?run_id={RUN_ID}")
    assert response.status_code == 200
    data = response.json()
    assert "canonical_graph" in data
    assert "pipeline_projection" in data
    projection_ids = {node["projection_id"] for node in data["pipeline_projection"]["nodes"]}
    assert "branch_a" in projection_ids
    assert "branch_b" in projection_ids
    assert "branch_a_bundle" not in projection_ids


def test_api_overview_returns_run_projection_pipeline_layout_and_tree():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/overview")
    assert response.status_code == 200
    data = response.json()
    assert "run_summary" in data
    assert "run_projection" in data
    assert "pipeline_layout" in data
    assert "tree" in data
    assert any(node["projection_id"] == "branch_a_bundle" for node in data["run_projection"]["nodes"])
    assert data["pipeline_layout"]["sections"][0]["title"] == "Source"


def test_api_tree():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/tree")
    assert response.status_code == 200
    assert "root" in response.json()


def test_api_node_details():
    response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/nodes/source_corpus")
    assert response.status_code == 200
    data = response.json()
    assert data["node_id"] == "source_corpus"
    assert data["state"] == "complete"


def test_api_file_details_and_preview():
    tree_response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/tree")
    summary_child = next(item for item in tree_response.json()["root"]["children"] if item["name"] == "local_corpus_e2e_summary.json")
    file_response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/files/{summary_child['tree_id']}")
    assert file_response.status_code == 200
    assert file_response.json()["preview_available"] is True
    preview_response = client.get(f"/api/v1/review/nrc-aps/runs/{RUN_ID}/files/{summary_child['tree_id']}/preview")
    assert preview_response.status_code == 200
    assert '"schema_id": "aps.local_corpus_e2e_summary.v1"' in preview_response.json()["content"]


def test_api_runs_lists_multiple_runtime_backed_candidates():
    assert MULTI_RUNTIME_RUN_IDS, "Expected at least one passed local-corpus runtime for /runs validation"
    response = client.get("/api/v1/review/nrc-aps/runs")
    assert response.status_code == 200
    data = response.json()
    returned_run_ids = {item["run_id"] for item in data["runs"]}
    assert MULTI_RUNTIME_RUN_IDS.issubset(returned_run_ids)


def test_candidate_review_runtime_roots_use_deterministic_local_roots(tmp_path):
    app_root = tmp_path / "backend" / "app"
    backend_root = app_root.parent
    app_root.mkdir(parents=True)

    roots = candidate_review_runtime_roots(app_root=app_root, backend_root=backend_root)

    assert roots == [
        (app_root / "storage_test_runtime" / "lc_e2e").resolve(),
        (backend_root / "storage_test_runtime" / "lc_e2e").resolve(),
    ]


def test_candidate_review_runtime_roots_accept_configured_storage_test_runtime(tmp_path):
    app_root = tmp_path / "backend" / "app"
    backend_root = app_root.parent
    app_root.mkdir(parents=True)

    configured_storage_root = tmp_path / "shared" / "storage_test_runtime"
    roots = candidate_review_runtime_roots(
        app_root=app_root,
        backend_root=backend_root,
        storage_dir=configured_storage_root,
    )

    assert (configured_storage_root / "lc_e2e").resolve() in roots


def test_candidate_review_runtime_roots_reject_arbitrary_configured_root(tmp_path):
    app_root = tmp_path / "backend" / "app"
    backend_root = app_root.parent
    app_root.mkdir(parents=True)

    configured_storage_root = tmp_path / "shared" / "experimental_runtime_root"
    roots = candidate_review_runtime_roots(
        app_root=app_root,
        backend_root=backend_root,
        storage_dir=configured_storage_root,
    )

    assert configured_storage_root.resolve() not in roots
    assert (configured_storage_root / "lc_e2e").resolve() not in roots


def test_api_runs_omit_experiment_hidden_runtime_and_keep_legacy_runtime_visible(tmp_path, monkeypatch):
    storage_root = tmp_path / "storage_test_runtime"
    hidden_run_id = "00000000-0000-0000-0000-00000000a501"
    legacy_run_id = "00000000-0000-0000-0000-00000000a502"
    _create_temp_review_runtime(
        storage_root,
        runtime_name="hidden_runtime",
        run_id=hidden_run_id,
        visual_lane_mode="variant_a",
        include_connector_run_row=True,
    )
    _create_temp_review_runtime(
        storage_root,
        runtime_name="legacy_runtime",
        run_id=legacy_run_id,
        visual_lane_mode=None,
        include_connector_run_row=False,
    )

    monkeypatch.setattr("app.services.review_nrc_aps_runtime.settings.storage_dir", str(storage_root))
    response = client.get("/api/v1/review/nrc-aps/runs")

    assert response.status_code == 200
    data = response.json()
    returned_run_ids = {item["run_id"] for item in data["runs"]}
    assert hidden_run_id not in returned_run_ids
    assert legacy_run_id in returned_run_ids


def test_api_documents_404_for_experiment_hidden_runtime(tmp_path, monkeypatch):
    storage_root = tmp_path / "storage_test_runtime"
    hidden_run_id = "00000000-0000-0000-0000-00000000a503"
    _create_temp_review_runtime(
        storage_root,
        runtime_name="hidden_runtime_docs",
        run_id=hidden_run_id,
        visual_lane_mode="variant_b",
        include_connector_run_row=True,
    )

    monkeypatch.setattr("app.services.review_nrc_aps_runtime.settings.storage_dir", str(storage_root))
    response = client.get(f"/api/v1/review/nrc-aps/runs/{hidden_run_id}/documents")

    assert response.status_code == 404
