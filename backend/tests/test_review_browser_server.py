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

from tests.review_browser_fixture import capture_review_browser_patch_state, restore_review_browser_patches
from tests.review_browser_server import create_app


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
