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
    assert 'id="workbench-return-link"' in html
    assert 'id="theme-selector"' in html
    assert 'id="identity-summary"' in html
    assert 'id="tabs-header"' in html
    assert 'id="tab-content-area"' in html
    assert 'id="fixture-navigation"' in html
    assert 'id="artifact-status-strip"' in html
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
    assert "candidate_b_source_kind" in js_content
    assert "fixture_id" in js_content
    assert "tab" in js_content
    assert "const API_ROOT = '/api/v1/review/nrc-aps/candidate-b-trace';" in js_content
    assert "const WORKBENCH_API_ROOT = '/api/v1/review/nrc-aps/workbench-compare';" in js_content
    assert "const WORKBENCH_ROUTE = '/review/nrc-aps/workbench-compare';" in js_content
    assert "annotated_pdf" in js_content
    assert "raw_json" in js_content
    assert "raw_markdown" in js_content
    assert "document-trace?run_id=" not in js_content


def test_candidate_b_trace_js_preserves_bundle_context_for_workbench_return() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "candidate_b_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "baseline_run_id" in js_content
    assert "candidate_a_run_id" in js_content
    assert "candidate_b_source_kind', 'bundle'" in js_content
    assert js_content.count("params.set('baseline_run_id', state.baselineRunId)") >= 2
    assert js_content.count("params.set('candidate_a_run_id', state.candidateARunId)") >= 2
    assert "params.get('candidate_b_run_id')" not in js_content
    assert "params.set('candidate_b_run_id'" not in js_content
    assert "syncReturnLink();" in js_content


def test_candidate_b_trace_js_loads_bundle_fixture_navigation_from_workbench_targets() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "candidate_b_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "fixtureNavigation" in js_content
    assert "function buildWorkbenchTargetsUrl()" in js_content
    assert "`${WORKBENCH_API_ROOT}/targets?${params.toString()}`" in js_content
    assert "function renderFixtureNavigation(payload" in js_content
    assert "Only one comparable fixture is available" in js_content
    assert "Open from Workbench Compare with baseline and Candidate A context" in js_content
    assert "data-direction" in js_content
    assert "loadFixtureNavigation();" in js_content


def test_candidate_b_trace_js_defers_blank_query_tab_to_manifest_default() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "candidate_b_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "tabId: ''" in js_content
    assert "state.tabId = params.get('tab') || '';" in js_content
    assert "state.tabId = state.manifest.default_tab || 'summary';" in js_content
    assert "state.tabId = params.get('tab') || 'summary';" not in js_content


def test_candidate_b_trace_js_surfaces_artifact_availability_states() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "candidate_b_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "artifactStatusStrip" in js_content
    assert "function renderArtifactStatusStrip(manifest)" in js_content
    assert "artifactTabAvailable(manifest, 'annotated_pdf')" in js_content
    assert "artifactTabAvailable(manifest, 'raw_json')" in js_content
    assert "artifactTabAvailable(manifest, 'raw_markdown')" in js_content
    assert "No artifact was retained for this fixture; validation remains read-only." in js_content
    assert "`${tab.label} (Unavailable)`" in js_content
    assert "function renderArtifactUnavailable(label, detail)" in js_content
    assert "does not generate or seed replacement artifacts" in js_content


def test_candidate_b_trace_css_styles_local_shell_elements() -> None:
    css_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "candidate_b_trace.css"
    css_content = css_path.read_text(encoding="utf-8")

    assert ".candidate-b-trace-summary-band" in css_content
    assert ".identity-summary" in css_content
    assert ".tabs-header" in css_content
    assert ".tab-btn" in css_content
    assert ".placeholder" in css_content
    assert ".artifact-frame" in css_content
    assert ".artifact-status-strip" in css_content
    assert ".artifact-status-card" in css_content
    assert ".artifact-empty-state" in css_content
    assert ".fixture-navigation" in css_content
    assert ".fixture-nav-link.disabled" in css_content
