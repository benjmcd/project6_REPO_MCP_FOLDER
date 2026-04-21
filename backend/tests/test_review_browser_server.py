from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from review_browser_fixture import capture_review_browser_patch_state, restore_review_browser_patches
from review_browser_server import create_app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    patch_state = capture_review_browser_patch_state()
    app = create_app()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        restore_review_browser_patches(patch_state)


def test_review_browser_server_health_and_compare_sources(client: TestClient) -> None:
    health_response = client.get("/health")
    sources_response = client.get("/api/v1/review/nrc-aps/workbench-compare/sources")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}

    assert sources_response.status_code == 200
    payload = sources_response.json()
    assert len(payload["baseline_runs"]) == 1
    assert len(payload["candidate_a_runs"]) == 1
    assert len(payload["candidate_b_bundles"]) == 1
    assert "C:\\" not in str(payload)


def test_review_browser_server_candidate_b_trace_defaults_to_annotated_pdf(client: TestClient) -> None:
    sources_payload = client.get("/api/v1/review/nrc-aps/workbench-compare/sources").json()
    targets_payload = client.get(
        "/api/v1/review/nrc-aps/workbench-compare/targets",
        params={
            "baseline_run_id": sources_payload["baseline_runs"][0]["run_id"],
            "candidate_a_run_id": sources_payload["candidate_a_runs"][0]["run_id"],
            "candidate_b_bundle_id": sources_payload["candidate_b_bundles"][0]["bundle_id"],
        },
    ).json()
    fixture_id = targets_payload["targets"][0]["fixture_id"]

    manifest_response = client.get(
        "/api/v1/review/nrc-aps/candidate-b-trace/manifest",
        params={
            "candidate_b_bundle_id": sources_payload["candidate_b_bundles"][0]["bundle_id"],
            "fixture_id": fixture_id,
        },
    )

    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["default_tab"] == "annotated_pdf"
    assert manifest["artifacts"]["annotated_pdf"].startswith("/api/v1/review/nrc-aps/candidate-b-trace/annotated-pdf?")
    assert "C:\\" not in str(manifest)


def test_review_browser_server_document_trace_routes_use_isolated_runtime_fixture(client: TestClient) -> None:
    runs_response = client.get("/api/v1/review/nrc-aps/runs")
    assert runs_response.status_code == 200
    runs_payload = runs_response.json()
    run_id = runs_payload["default_run_id"]
    assert run_id

    documents_response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/documents")
    assert documents_response.status_code == 200
    documents_payload = documents_response.json()
    assert len(documents_payload["documents"]) == 1
    target_id = documents_payload["default_target_id"]
    assert target_id

    trace_response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/trace")
    assert trace_response.status_code == 200
    trace_manifest = trace_response.json()
    assert trace_manifest["source"]["viewer_kind"] == "pdf"
    assert trace_manifest["source"]["source_endpoint"].endswith("/source")
    assert trace_manifest["summary"]["ordered_unit_count"] == 1
    assert trace_manifest["summary"]["indexed_chunk_count"] == 1
    assert "C:\\" not in str(trace_manifest)

    source_response = client.get(trace_manifest["source"]["source_endpoint"])
    assert source_response.status_code == 200
    assert source_response.headers["content-type"].startswith("application/pdf")
    assert source_response.content.startswith(b"%PDF")

    extracted_units_response = client.get(
        f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/extracted-units"
    )
    assert extracted_units_response.status_code == 200
    extracted_units_payload = extracted_units_response.json()
    assert extracted_units_payload["available"] is True
    assert extracted_units_payload["total_unit_count"] == 1
    assert len(extracted_units_payload["units"]) == 1
    assert "C:\\" not in str(extracted_units_payload)
