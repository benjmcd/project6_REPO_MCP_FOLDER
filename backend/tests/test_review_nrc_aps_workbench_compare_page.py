"""Tests for the NRC APS workbench compare page shell."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.review_nrc_aps import (
    NrcApsWorkbenchCompareManifestOut,
    NrcApsWorkbenchCompareSourcesOut,
    NrcApsWorkbenchCompareTabOut,
    NrcApsWorkbenchCompareTargetsOut,
)
from main import app


client = TestClient(app)


def test_workbench_compare_page_route_serves() -> None:
    response = client.get("/review/nrc-aps/workbench-compare")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_workbench_compare_page_shell_content() -> None:
    response = client.get("/review/nrc-aps/workbench-compare")
    html = response.text

    assert "<title>NRC APS Workbench Compare</title>" in html
    assert 'href="/review/nrc-aps"' in html
    assert 'id="baseline-run-selector"' in html
    assert 'id="candidate-a-run-selector"' in html
    assert 'id="candidate-b-bundle-selector"' in html
    assert 'id="target-selector"' in html
    assert 'id="tabs-header"' in html
    assert 'id="compare-tab-content"' in html
    assert '/review/nrc-aps/static/workbench_compare.css' in html
    assert '/review/nrc-aps/static/workbench_compare.js' in html


def test_workbench_compare_static_assets_are_served() -> None:
    css_response = client.get("/review/nrc-aps/static/workbench_compare.css")
    js_response = client.get("/review/nrc-aps/static/workbench_compare.js")

    assert css_response.status_code == 200
    assert js_response.status_code == 200


def test_workbench_compare_css_styles_identity_summary_metadata() -> None:
    css_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "workbench_compare.css"
    css_content = css_path.read_text(encoding="utf-8")

    assert ".identity-summary" in css_content
    assert ".identity-summary .meta-item" in css_content
    assert ".identity-summary .meta-label" in css_content


def test_workbench_compare_js_uses_only_compare_schema_fields() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "workbench_compare.js"
    js_content = js_path.read_text(encoding="utf-8")

    sources_fields = set(re.findall(r"state\.sources\.([a-z_]+)", js_content))
    manifest_fields = set(re.findall(r"state\.manifest\.([a-z_]+)", js_content))
    tab_fields = set(re.findall(r"state\.tabPayload\.([a-z_]+)", js_content))

    valid_sources_fields = set(NrcApsWorkbenchCompareSourcesOut.model_fields.keys())
    valid_manifest_fields = set(NrcApsWorkbenchCompareManifestOut.model_fields.keys())
    valid_tab_fields = set(NrcApsWorkbenchCompareTabOut.model_fields.keys())

    for field in sources_fields:
        assert field in valid_sources_fields, f"JS reads non-existent compare-sources field: {field}"
    for field in manifest_fields:
        assert field in valid_manifest_fields, f"JS reads non-existent compare-manifest field: {field}"
    for field in tab_fields:
        assert field in valid_tab_fields, f"JS reads non-existent compare-tab field: {field}"


def test_workbench_compare_js_uses_page_local_query_params_and_compare_routes() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "workbench_compare.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "baseline_run_id" in js_content
    assert "candidate_a_run_id" in js_content
    assert "candidate_b_bundle_id" in js_content
    assert "fixture_id" in js_content
    assert "tab" in js_content
    assert "const API_ROOT = '/api/v1/review/nrc-aps/workbench-compare';" in js_content
    assert "${API_ROOT}/sources" in js_content
    assert "baseline_trace" in js_content
    assert "candidate_a_trace" in js_content
    assert "document-trace?run_id=" not in js_content


def test_workbench_compare_js_renders_required_compare_columns() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "workbench_compare.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "baseline" in js_content
    assert "candidate_a" in js_content
    assert "candidate_b" in js_content
    assert "compare-grid" in js_content
    assert "comparability_legend" in js_content
    assert "summary_badges" in js_content
