"""Tests for the NRC APS Document Trace page shell."""
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app

client = TestClient(app)

def test_document_trace_page_route_serves() -> None:
    """The document trace page route should return 200 OK and valid HTML."""
    response = client.get("/review/nrc-aps/document-trace")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_document_trace_page_shell_content() -> None:
    """The document trace page should contain the required structural elements."""
    response = client.get("/review/nrc-aps/document-trace")
    html = response.text
    
    # Title
    assert "<title>NRC APS Document Trace</title>" in html
    
    # Back navigation
    assert 'class="back-link"' in html
    assert 'href="/review/nrc-aps"' in html
    
    # Selectors
    assert 'id="run-selector"' in html
    assert 'id="doc-selector"' in html

    # Panes
    assert 'class="pane source-pane"' in html
    assert 'class="pane provenance-pane"' in html

    # Tab labels placeholder areas
    assert 'id="tabs-header"' in html

def test_review_nrc_aps_page_regression() -> None:
    """The existing review page must not be regressed."""
    response = client.get("/review/nrc-aps")
    assert response.status_code == 200
    html = response.text
    
    # Validate the 3 view modes
    assert ">Pipeline Overview</label>" in html
    assert ">Run-specific Overview (Light)</label>" in html
    assert ">Run-specific Overview (Heavy)</label>" in html
    
    # Validate launch affordance
    assert 'id="launch-document-trace"' in html
    assert 'href="/review/nrc-aps/document-trace"' in html

import re
from app.schemas.review_nrc_aps import (
    NrcApsReviewTraceSourceOut, 
    NrcApsReviewTraceIdentityOut,
    NrcApsReviewTraceSummaryOut,
    NrcApsReviewDiagnosticsOut,
    NrcApsReviewNormalizedTextOut,
    NrcApsReviewIndexedChunkItemOut,
    NrcApsReviewExtractedUnitsOut,
    NrcApsReviewExtractedUnitItemOut,
)

def test_document_trace_js_binds_to_valid_schema() -> None:
    """Verify that document_trace.js only reads fields that actually exist in the trace manifest schema."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")
    
    # Find all source.xxx and identity.xxx reads in the JS
    source_fields = set(re.findall(r"source\.([a-z_]+)", js_content))
    identity_fields = set(re.findall(r"identity\.([a-z_]+)", js_content))
    summary_fields = set(re.findall(r"summary\.([a-z_]+)", js_content))
    diag_fields = set(re.findall(r"data\.([a-z_]+)", js_content.split("function renderDiagnosticsTab")[1].split("function renderNormalizedTextTab")[0]))
    norm_fields = set(re.findall(r"data\.([a-z_]+)", js_content.split("function renderNormalizedTextTab")[1].split("function renderIndexedChunksTab")[0]))
    chunk_section = js_content.split("function renderIndexedChunksTab")[1].split("function renderExtractedUnitsTab")[0]
    extracted_section = js_content.split("function renderExtractedUnitsTab")[1].split("window.switchTab")[0]
    chunk_meta_fields = set(re.findall(r"data\.([a-z_]+)", chunk_section))
    chunk_item_fields = set(re.findall(r"c\.([a-z_]+)", chunk_section))
    extracted_meta_fields = set(re.findall(r"data\.([a-z_]+)", extracted_section))
    extracted_item_fields = set(re.findall(r"unit\.([a-z_]+)", extracted_section))
    
    # Retrieve valid fields from the actual Pydantic schema
    valid_source_fields = set(NrcApsReviewTraceSourceOut.model_fields.keys())
    valid_identity_fields = set(NrcApsReviewTraceIdentityOut.model_fields.keys())
    valid_summary_fields = set(NrcApsReviewTraceSummaryOut.model_fields.keys())
    valid_diag_fields = set(NrcApsReviewDiagnosticsOut.model_fields.keys())
    valid_norm_fields = set(NrcApsReviewNormalizedTextOut.model_fields.keys())
    valid_chunk_item_fields = set(NrcApsReviewIndexedChunkItemOut.model_fields.keys())
    valid_extracted_meta_fields = set(NrcApsReviewExtractedUnitsOut.model_fields.keys())
    valid_extracted_item_fields = set(NrcApsReviewExtractedUnitItemOut.model_fields.keys())
    
    for field in source_fields:
        assert field in valid_source_fields, f"JS reads non-existent source field: {field}"
    for field in identity_fields:
        assert field in valid_identity_fields, f"JS reads non-existent identity field: {field}"
    for field in summary_fields:
        assert field in valid_summary_fields, f"JS reads non-existent summary field: {field}"
    for field in diag_fields:
        assert field in valid_diag_fields, f"JS reads non-existent diagnostics field: {field}"
    for field in norm_fields:
        assert field in valid_norm_fields, f"JS reads non-existent normalized text field: {field}"
    for field in extracted_meta_fields:
        assert field in valid_extracted_meta_fields, f"JS reads non-existent extracted-units field: {field}"
    for field in chunk_item_fields:
        assert field in valid_chunk_item_fields, f"JS reads non-existent chunk item field: {field}"
    for field in extracted_item_fields:
        assert field in valid_extracted_item_fields, f"JS reads non-existent extracted-unit item field: {field}"


def test_document_trace_phase6_extract_units_markers_present() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    css_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.css"

    js_content = js_path.read_text(encoding="utf-8")
    css_content = css_path.read_text(encoding="utf-8")

    assert "Source: diagnostics ordered_units" in js_content
    assert "unit (page-level jump)" in js_content
    assert "eu-page-badge" in js_content
    assert ".eu-provenance-bar" in css_content
    assert ".eu-precision-badge" in css_content

def test_document_trace_bbox_overlay_identifiers_present() -> None:
    """Verify bbox overlay identifiers exist in JS and CSS as presence/regression guards."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    css_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.css"

    js_content = js_path.read_text(encoding="utf-8")
    css_content = css_path.read_text(encoding="utf-8")

    # JS: overlay functions and DOM identifiers
    assert "syncViewerOverlays" in js_content
    assert "ensureExtractedUnitsLoaded" in js_content
    assert "pdf-page-shell" in js_content
    assert "pdf-page-overlay" in js_content
    assert "pdf-bbox-marker" in js_content
    assert "bbox-visibility-toggle" in js_content
    assert "showBboxes" in js_content

    # CSS: overlay styles
    assert ".pdf-page-shell" in css_content
    assert ".pdf-page-overlay" in css_content
    assert ".pdf-bbox-marker" in css_content
    assert ".bbox-toggle-float" in css_content


def test_document_trace_html_semantic_containers() -> None:
    """Verify the served page shell contains the semantic containers needed for source and viewer rendering."""
    response = client.get("/review/nrc-aps/document-trace")
    html = response.text
    
    # Assert structural container for the source payload exists
    assert 'id="source-content"' in html
    
    # Phase 5: Assert the PDF.js vendor script is referenced
    assert 'vendor/pdfjs/pdf.min.mjs' in html
    assert 'vendor/pdfjs/pdf.worker.min.mjs' in html


def test_document_trace_vendor_pdfjs_assets_served() -> None:
    """Verify vendored PDF.js assets are actually served by the static file mount."""
    resp_main = client.get("/review/nrc-aps/static/vendor/pdfjs/pdf.min.mjs")
    assert resp_main.status_code == 200
    
    resp_worker = client.get("/review/nrc-aps/static/vendor/pdfjs/pdf.worker.min.mjs")
    assert resp_worker.status_code == 200


def test_document_trace_js_renders_run_identity() -> None:
    """Verify that the document trace JS populates run identity in the identity summary."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    # renderTraceShell must include a RUN identity row
    assert '<strong>RUN</strong>' in js_content
    # loadTargetDoc must clear stale identity with immediate run display
    assert 'Immediately update run identity and clear stale document identity' in js_content


def test_review_js_has_run_identity_update() -> None:
    """Verify that the review JS updates the run identity bar on run selection."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "review.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert 'updateRunIdentity' in js_content
    assert 'current-run-info' in js_content
