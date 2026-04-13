from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app.services.review_nrc_aps_candidate_b_trace as trace_service
from cb_trace_fixture import write_candidate_b_trace_bundle
from main import app


client = TestClient(app)


def _patch_candidate_b_trace_service(monkeypatch: pytest.MonkeyPatch, checkout_root: Path) -> None:
    monkeypatch.setattr(
        "app.api.review_nrc_aps.compose_candidate_b_trace_manifest",
        lambda *, candidate_b_bundle_id, fixture_id: trace_service.compose_candidate_b_trace_manifest(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
            checkout_root=checkout_root,
        ),
    )
    monkeypatch.setattr(
        "app.api.review_nrc_aps.resolve_candidate_b_trace_annotated_pdf_info",
        lambda *, candidate_b_bundle_id, fixture_id: trace_service.resolve_candidate_b_trace_annotated_pdf_info(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
            checkout_root=checkout_root,
        ),
    )
    monkeypatch.setattr(
        "app.api.review_nrc_aps.load_candidate_b_trace_raw_json",
        lambda *, candidate_b_bundle_id, fixture_id: trace_service.load_candidate_b_trace_raw_json(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
            checkout_root=checkout_root,
        ),
    )
    monkeypatch.setattr(
        "app.api.review_nrc_aps.load_candidate_b_trace_raw_markdown",
        lambda *, candidate_b_bundle_id, fixture_id: trace_service.load_candidate_b_trace_raw_markdown(
            candidate_b_bundle_id=candidate_b_bundle_id,
            fixture_id=fixture_id,
            checkout_root=checkout_root,
        ),
    )


def test_candidate_b_trace_api_routes_return_bundle_backed_payloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = write_candidate_b_trace_bundle(tmp_path)
    _patch_candidate_b_trace_service(monkeypatch, fixture["checkout_root"])
    params = {
        "candidate_b_bundle_id": fixture["bundle_id"],
        "fixture_id": fixture["fixture_id"],
    }

    manifest_response = client.get("/api/v1/review/nrc-aps/candidate-b-trace/manifest", params=params)
    annotated_pdf_response = client.get("/api/v1/review/nrc-aps/candidate-b-trace/annotated-pdf", params=params)
    raw_json_response = client.get("/api/v1/review/nrc-aps/candidate-b-trace/raw-json", params=params)
    raw_markdown_response = client.get("/api/v1/review/nrc-aps/candidate-b-trace/raw-markdown", params=params)

    assert manifest_response.status_code == 200
    assert annotated_pdf_response.status_code == 200
    assert raw_json_response.status_code == 200
    assert raw_markdown_response.status_code == 200

    manifest = manifest_response.json()
    assert manifest["candidate_b_bundle_id"] == fixture["bundle_id"]
    assert manifest["fixture_id"] == fixture["fixture_id"]
    assert "C:\\" not in str(manifest)
    assert annotated_pdf_response.headers["content-type"].startswith("application/pdf")
    assert annotated_pdf_response.headers["content-disposition"].startswith("inline;")
    assert raw_json_response.json()["fixture_id"] == fixture["fixture_id"]
    assert raw_markdown_response.text.startswith("# Candidate B")


def test_candidate_b_trace_api_invalid_bundle_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = write_candidate_b_trace_bundle(tmp_path)
    _patch_candidate_b_trace_service(monkeypatch, fixture["checkout_root"])

    response = client.get(
        "/api/v1/review/nrc-aps/candidate-b-trace/manifest",
        params={"candidate_b_bundle_id": "../bad", "fixture_id": fixture["fixture_id"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "candidate_b_bundle_id_invalid"


def test_candidate_b_trace_api_missing_fixture_returns_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = write_candidate_b_trace_bundle(tmp_path)
    _patch_candidate_b_trace_service(monkeypatch, fixture["checkout_root"])

    response = client.get(
        "/api/v1/review/nrc-aps/candidate-b-trace/manifest",
        params={"candidate_b_bundle_id": fixture["bundle_id"], "fixture_id": "missing-fixture"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "candidate_b_fixture_unavailable"


def test_candidate_b_trace_api_missing_annotated_pdf_returns_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = write_candidate_b_trace_bundle(tmp_path, include_annotated_pdf=False, annotated_pdf_status="missing")
    _patch_candidate_b_trace_service(monkeypatch, fixture["checkout_root"])

    response = client.get(
        "/api/v1/review/nrc-aps/candidate-b-trace/annotated-pdf",
        params={"candidate_b_bundle_id": fixture["bundle_id"], "fixture_id": fixture["fixture_id"]},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "annotated_pdf_unavailable"
