from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.deps import get_db
from main import app

def override_get_db():
    from unittest.mock import MagicMock
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    yield db

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@patch('app.api.review_nrc_aps.discover_candidate_runs')
def test_api_runs(mock_discover):
    from app.schemas.review_nrc_aps import NrcApsReviewRunSelectorItemOut, NrcApsReviewRunSelectorOut

    mock_discover.return_value = NrcApsReviewRunSelectorOut(
        default_run_id="d6be0fff-bbd7-468a-9b00-7103d5995494",
        runs=[NrcApsReviewRunSelectorItemOut(
            run_id="d6be0fff-bbd7-468a-9b00-7103d5995494",
            submitted_at="2026-03-27T06:20:11Z",
            reviewable=True,
        )]
    )
    response = client.get("/api/v1/review/nrc-aps/runs")
    assert response.status_code == 200
    data = response.json()
    assert "default_run_id" in data
    assert "runs" in data
    assert len(data["runs"]) > 0

def test_api_pipeline_definition():
    response = client.get("/api/v1/review/nrc-aps/pipeline-definition")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data

def test_api_overview():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/overview")
    assert response.status_code == 200
    data = response.json()
    assert "graph" in data
    assert "tree" in data

def test_api_tree():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/tree")
    assert response.status_code == 200
    data = response.json()
    assert "root" in data

def test_api_node_details():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    node_id = "source_corpus"
    response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/nodes/{node_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["node_id"] == node_id


def test_api_file_details():
    run_id = "d6be0fff-bbd7-468a-9b00-7103d5995494"
    tree_response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/tree")
    assert tree_response.status_code == 200
    summary_child = next(item for item in tree_response.json()["root"]["children"] if item["name"] == "local_corpus_e2e_summary.json")
    file_response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/files/{summary_child['tree_id']}")
    assert file_response.status_code == 200
    assert file_response.json()["name"] == "local_corpus_e2e_summary.json"
