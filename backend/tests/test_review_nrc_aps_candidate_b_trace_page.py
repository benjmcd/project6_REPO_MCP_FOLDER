"""Tests for the NRC APS Candidate B Trace page shell."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.review_nrc_aps import (
    NrcApsCandidateBTraceArtifactEndpointsOut,
    NrcApsCandidateBTraceIdentityOut,
    NrcApsCandidateBTraceManifestOut,
    NrcApsCandidateBTraceSummaryOut,
)
from main import app


client = TestClient(app)


def test_candidate_b_trace_page_route_serves() -> None:
    response = client.get("/review/nrc-aps/candidate-b-trace")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_candidate_b_trace_page_shell_content() -> None:
    response = client.get("/review/nrc-aps/candidate-b-trace")
    html = response.text

    assert "<title>NRC APS Candidate B Trace</title>" in html
    assert 'href="/review/nrc-aps/workbench-compare"' in html
    assert 'id="theme-selector"' in html
    assert 'id="identity-summary"' in html
    assert 'id="tabs-header"' in html
    assert 'id="tab-content-area"' in html
    assert "/review/nrc-aps/static/candidate_b_trace.css" in html
    assert "/review/nrc-aps/static/candidate_b_trace.js" in html
    assert "/review/nrc-aps/static/document_trace.css" not in html
    assert "/review/nrc-aps/static/document_trace.js" not in html


def test_candidate_b_trace_static_assets_are_served() -> None:
    css_response = client.get("/review/nrc-aps/static/candidate_b_trace.css")
    js_response = client.get("/review/nrc-aps/static/candidate_b_trace.js")

    assert css_response.status_code == 200
    assert js_response.status_code == 200


def test_candidate_b_trace_js_uses_schema_backed_manifest_fields() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "candidate_b_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    manifest_fields = set(re.findall(r"manifest\.([a-z_]+)", js_content))
    identity_fields = set(re.findall(r"identity\.([a-z_]+)", js_content))
    summary_fields = set(re.findall(r"summary\.([a-z_]+)", js_content))
    artifact_fields = set(re.findall(r"artifacts\.([a-z_]+)", js_content))

    valid_manifest_fields = set(NrcApsCandidateBTraceManifestOut.model_fields.keys())
    valid_identity_fields = set(NrcApsCandidateBTraceIdentityOut.model_fields.keys())
    valid_summary_fields = set(NrcApsCandidateBTraceSummaryOut.model_fields.keys())
    valid_artifact_fields = set(NrcApsCandidateBTraceArtifactEndpointsOut.model_fields.keys())

    for field in manifest_fields:
        assert field in valid_manifest_fields, f"JS reads non-existent candidate-b-trace manifest field: {field}"
    for field in identity_fields:
        assert field in valid_identity_fields, f"JS reads non-existent candidate-b-trace identity field: {field}"
    for field in summary_fields:
        assert field in valid_summary_fields, f"JS reads non-existent candidate-b-trace summary field: {field}"
    for field in artifact_fields:
        assert field in valid_artifact_fields, f"JS reads non-existent candidate-b-trace artifact field: {field}"


def test_candidate_b_trace_js_uses_page_local_query_params_and_routes() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "candidate_b_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "candidate_b_bundle_id" in js_content
    assert "fixture_id" in js_content
    assert "tab" in js_content
    assert "const API_ROOT = '/api/v1/review/nrc-aps/candidate-b-trace';" in js_content
    assert "annotated_pdf" in js_content
    assert "raw_json" in js_content
    assert "raw_markdown" in js_content
    assert "document-trace?run_id=" not in js_content


def test_candidate_b_trace_css_styles_local_shell_elements() -> None:
    css_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "candidate_b_trace.css"
    css_content = css_path.read_text(encoding="utf-8")

    assert ".candidate-b-trace-summary-band" in css_content
    assert ".identity-summary" in css_content
    assert ".tabs-header" in css_content
    assert ".tab-btn" in css_content
    assert ".placeholder" in css_content
    assert ".artifact-frame" in css_content
