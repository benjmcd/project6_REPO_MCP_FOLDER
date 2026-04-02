from __future__ import annotations

import os
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
