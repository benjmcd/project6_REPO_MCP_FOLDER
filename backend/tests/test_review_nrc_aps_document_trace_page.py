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
    NrcApsReviewVisualArtifactItemOut,
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
    visual_artifact_fields = set(re.findall(r"artifact\.([a-z_]+)", extracted_section))
    
    # Retrieve valid fields from the actual Pydantic schema
    valid_source_fields = set(NrcApsReviewTraceSourceOut.model_fields.keys())
    valid_identity_fields = set(NrcApsReviewTraceIdentityOut.model_fields.keys())
    valid_summary_fields = set(NrcApsReviewTraceSummaryOut.model_fields.keys())
    valid_diag_fields = set(NrcApsReviewDiagnosticsOut.model_fields.keys())
    valid_norm_fields = set(NrcApsReviewNormalizedTextOut.model_fields.keys())
    valid_chunk_item_fields = set(NrcApsReviewIndexedChunkItemOut.model_fields.keys())
    valid_extracted_meta_fields = set(NrcApsReviewExtractedUnitsOut.model_fields.keys())
    valid_extracted_item_fields = set(NrcApsReviewExtractedUnitItemOut.model_fields.keys())
    valid_visual_artifact_fields = set(NrcApsReviewVisualArtifactItemOut.model_fields.keys())
    
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
    for field in visual_artifact_fields:
        assert field in valid_visual_artifact_fields, f"JS reads non-existent visual-artifact field: {field}"


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


def test_document_trace_js_identity_aware_shell_errors() -> None:
    """Verify document_trace.js shell-level error messages include run/target identity."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    # disabledTitle element reference
    assert "disabledTitle" in js_content

    # renderShellError accepts a title parameter
    assert "function renderShellError(message, title)" in js_content

    # Shell-level messages include run identity
    assert "No document selected for run" in js_content
    assert "is not available in run" in js_content
    assert "No documents available in run" in js_content
    assert "Failed to fetch documents for run" in js_content
    assert "Failed to load trace for" in js_content

    # State-type-specific overlay titles
    assert "'No Document Selected'" in js_content
    assert "'Document Not Available'" in js_content
    assert "'No Documents Available'" in js_content
    assert "'Error Loading Trace'" in js_content
    assert "'Error Loading Documents'" in js_content


def test_document_trace_js_non_reviewable_run_guard() -> None:
    """Verify document_trace.js checks run reviewability before fetching documents."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    # Non-reviewable guard in loadRun
    assert "!runInfo.reviewable" in js_content
    assert "'Run Not Reviewable'" in js_content
    assert "is not reviewable" in js_content

    # Non-reviewable runs disabled in selector
    assert "disabled_reason_code" in js_content
    assert "not reviewable" in js_content


def test_document_trace_js_tab_error_includes_identity() -> None:
    """Verify tab-level fetch errors include run and target identity."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "Failed to load ${escapeHtml(tabId)} for ${escapeHtml(State.selectedTargetId)} in run ${escapeHtml(State.selectedRunId)}" in js_content


def test_document_trace_js_source_and_tab_unavailable_states_are_identity_aware() -> None:
    """Verify remaining source-pane and tab-level unavailable states include run/target context."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "function formatTraceContext(runId = State.selectedRunId, targetId = State.selectedTargetId)" in js_content
    assert "function formatUnavailableMessage(label, { runId, targetId, reasonCode } = {})" in js_content
    assert "function formatEmptyMessage(label, { runId, targetId, detail } = {})" in js_content

    assert "Source file', { runId, targetId }" in js_content
    assert "Source preview for ${escapeHtml(viewerKind || 'unknown')} content is not supported for ${formatTraceContext(runId, targetId)}." in js_content
    assert "Source fetch failed for ${formatTraceContext(runId, targetId)}: HTTP ${resp.status}." in js_content
    assert "Source metadata', { runId: State.selectedRunId, targetId: State.selectedTargetId }" in js_content

    assert "Diagnostics', { runId: data?.run_id, targetId: data?.target_id }" in js_content
    assert "Normalized Text', { runId: data?.run_id, targetId: data?.target_id }" in js_content
    assert "Indexed Chunks', { runId: data?.run_id, targetId: data?.target_id }" in js_content
    assert "Extracted Units', { runId: data.run_id, targetId: data.target_id, reasonCode: data.reason_code }" in js_content
    assert "formatEmptyMessage('extracted units', { runId: data.run_id, targetId: data.target_id, detail: `Page ${focusedPage}.` })" in js_content


def test_document_trace_js_visual_summary_and_diagnostics_counters_present() -> None:
    """Verify the trace UI renders visual counters and diagnostics breakdown sections."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "VISUAL PAGES" in js_content
    assert "VISUAL-DERIVED UNITS" in js_content
    assert "Visual Derivatives:" in js_content
    assert "Unit Kind Breakdown" in js_content
    assert "Object.entries(data.unit_kind_counts || {})" in js_content


def test_document_trace_js_visual_artifact_extract_units_rendering_present() -> None:
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    css_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.css"
    js_content = js_path.read_text(encoding="utf-8")
    css_content = css_path.read_text(encoding="utf-8")

    assert "Visual Artifacts on This Page" in js_content
    assert "data.visual_artifacts" in js_content
    assert "eu-visual-preview" in js_content
    assert "artifact.endpoint" in js_content
    assert ".eu-visual-preview" in css_content
    assert ".eu-visual-card" in css_content


def test_document_trace_js_scope_labels_present() -> None:
    """Verify scope labeling infrastructure exists in JS and CSS."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    css_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.css"
    js_content = js_path.read_text(encoding="utf-8")
    css_content = css_path.read_text(encoding="utf-8")

    # TAB_SCOPE constant
    assert "TAB_SCOPE" in js_content
    assert "extracted_units: 'page'" in js_content
    assert "diagnostics: 'document'" in js_content

    # Scope context bar function and content
    assert "renderScopeContextBar" in js_content
    assert "scope-context-bar" in js_content
    assert "Scope: entire document" in js_content
    assert "not affected by page navigation" in js_content

    # Tab header scope badges
    assert "tab-scope-badge" in js_content
    assert ".tab-scope-badge" in css_content
    assert ".scope-context-bar" in css_content


def test_document_trace_js_document_scoped_tabs_have_scope_context() -> None:
    """Verify each document-scoped tab renderer includes scope context."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "renderScopeContextBar('summary')" in js_content
    assert "renderScopeContextBar('diagnostics')" in js_content
    assert "renderScopeContextBar('normalized_text')" in js_content
    assert "renderScopeContextBar('indexed_chunks')" in js_content


def test_document_trace_js_scope_badges_in_tab_headers() -> None:
    """Verify tab header rendering includes scope badge markup."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "TAB_SCOPE[t.tab_id]" in js_content
    assert "scopeLabel" in js_content
    assert "'page' ? 'page' : 'doc'" in js_content


def test_document_trace_js_large_document_gating_rule_is_explicit() -> None:
    """Large-document optimization must be gated by deterministic document facts."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "const LARGE_DOC_RENDER_POLICY = Object.freeze({" in js_content
    assert "PAGE_THRESHOLD: 200" in js_content
    assert "PREFETCH_RADIUS: 2" in js_content
    assert "function shouldUseVirtualizedPageRendering(totalPages)" in js_content
    assert "totalPages >= LARGE_DOC_RENDER_POLICY.PAGE_THRESHOLD" in js_content


def test_document_trace_js_large_document_gating_has_no_document_specific_special_case() -> None:
    """The optimization path must not key off specific accession/target/title identifiers."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "LOCALAPS00035" not in js_content
    assert "9a2cdbda-e94a-4ac8-a294-a60b1c3daa61" not in js_content
    assert "ML26050A483" not in js_content


def test_document_trace_js_virtualized_render_markers_present() -> None:
    """Large-doc viewer markers should show bounded windowing and geometry handling."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    css_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.css"
    js_content = js_path.read_text(encoding="utf-8")
    css_content = css_path.read_text(encoding="utf-8")

    assert "useVirtualizedPages" in js_content
    assert "windowToken" in js_content
    assert "pageGeometryByPage" in js_content
    assert "seedViewerPageGeometryFromManifest" in js_content
    assert "source?.page_geometries" in js_content
    assert "ensureViewerPageGeometry" in js_content
    assert "pruneVirtualizedPageShells" in js_content
    assert "ensureExtractedUnitsPageIndexes" in js_content
    assert "overlayUnitsByPage" in js_content
    assert "pdf-page-placeholder" in js_content
    assert ".pdf-page-placeholder" in css_content


def test_document_trace_js_focus_tracking_uses_probe_points() -> None:
    """Large-doc focus tracking should not rely on scanning every page shell."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "PDF_FOCUS_PROBE_OFFSETS" in js_content
    assert "document.elementFromPoint" in js_content


def test_document_trace_js_focus_tracking_handles_scroll_edges_truthfully() -> None:
    """Large-doc focus tracking should clamp to the real document edges."""
    js_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.js"
    js_content = js_path.read_text(encoding="utf-8")

    assert "focusAnchorPage" in js_content
    assert "clearViewerFocusAnchor" in js_content
    assert "alignFocusAnchorPage" in js_content
    assert "PDF_SCROLL_EDGE_TOLERANCE_PX" in js_content
    assert "maxScrollTop" in js_content
    assert "remainingScroll" in js_content
    assert "const anchoredPage = State.viewer.focusAnchorPage" in js_content
    assert "return anchoredPage;" in js_content
    assert "pageShell.scrollIntoView({ behavior: 'auto', block });" in js_content
    assert "let syncGeneration = 0;" in js_content
    assert "window.requestAnimationFrame" in js_content
    assert "const settledPage = detectFocusedPdfPage(container);" in js_content
    assert "container.scrollTop <= PDF_SCROLL_EDGE_TOLERANCE_PX" in js_content
    assert "remainingScroll <= PDF_SCROLL_EDGE_TOLERANCE_PX" in js_content
    assert "candidate.pageNum === State.viewer.totalPages && candidate.offset >= 0.8" in js_content
    assert "candidate.pageNum === 1 && candidate.offset <= 0.2" in js_content
    assert "return State.viewer.totalPages > 0 ? State.viewer.totalPages : null;" in js_content


def test_document_trace_css_keeps_split_panes_shrinkable_for_large_docs() -> None:
    """Large PDF widths must not push the provenance pane off-screen."""
    css_path = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static" / "document_trace.css"
    css_content = css_path.read_text(encoding="utf-8")

    assert ".source-pane {" in css_content
    assert ".provenance-pane {" in css_content
    assert ".pane-content," in css_content
    assert ".tab-content-area {" in css_content
    assert "min-width: 0;" in css_content
    assert "min-height: 0;" in css_content
