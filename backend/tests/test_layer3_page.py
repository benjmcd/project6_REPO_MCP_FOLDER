from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app

client = TestClient(app)


def _js_slice(js_text: str, start_marker: str, end_marker: str) -> str:
    start = js_text.find(start_marker)
    end = js_text.find(end_marker, start + len(start_marker))
    assert start != -1
    assert end != -1
    return js_text[start:end]


def test_layer3_page_route_serves_workbench_shell() -> None:
    response = client.get("/review/layer3")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Layer 3 Workbench</title>" in response.text
    assert '<body class="layer3-page">' in response.text
    assert '<option value="workbench">Workbench</option>' in response.text
    assert '<option value="layer3_mockup_workbench_theme">Mockup Workbench</option>' in response.text
    assert "layer3_workbench_theme" in response.text
    assert 'id="mockup-theme-shell"' in response.text
    assert 'data-theme-target="layer3_mockup_workbench_theme"' in response.text
    assert 'data-first-slice="mockup_theme_shell_and_fixture_projection"' in response.text
    assert 'id="mockup-fixture-scenario"' in response.text
    assert 'id="mockup-query-source-setup-projection"' in response.text
    assert 'aria-label="Read-only query/source setup live state projection"' in response.text
    assert "Read-only query/source setup projection pending" in response.text
    assert 'id="mockup-execution-lanes"' in response.text
    assert 'id="mockup-execution-lanes-projection"' in response.text
    assert 'aria-label="Read-only Sublayer 3C execution lanes live state projection"' in response.text
    assert "Read-only 3C server state projection pending" in response.text
    assert 'id="mockup-output-review-package-handoff-projection"' in response.text
    assert 'aria-label="Read-only output review package handoff live state projection"' in response.text
    assert "Read-only output review package handoff projection pending" in response.text
    assert 'id="mockup-userflow-board"' in response.text
    assert 'id="mockup-pdf-location-card"' in response.text
    assert 'id="mockup-pdf-location-projection"' in response.text
    assert 'data-projection-state="unavailable"' in response.text
    assert 'id="mockup-sublayers-ab-board"' in response.text
    assert 'id="mockup-sublayers-ab-projection"' in response.text
    assert 'data-read-only="true"' in response.text
    assert 'data-visual-source="userflow/layer3_user-flow-overview1.png"' in response.text
    assert 'data-usecase-source="clear-screenshots/userflow_slide1_specific_usecase-example_zoomed-in.png"' in response.text
    assert 'data-pdf-location-source="example-use-case-location-in-pdf.png"' in response.text
    assert 'data-visual-source="focus_on_these/sublayer3A_and_sublayer3B.png"' in response.text
    assert 'data-visual-source="focus_on_these/sublayer3C.png"' in response.text
    assert "semiconductor_infrastructure_auto_supply_chain" in response.text
    assert "Analysis Execution Environments" in response.text
    assert "User Natural Language Query Input" in response.text
    assert "Layer manually chooses the specific, relevant, logic/context/thematic data" in response.text
    assert "PDF evidence location" in response.text
    assert "Gate B / Session Entry / Material Ledger" in response.text
    assert "Hybrid/Mixed Data" in response.text
    assert "Quantitative (and/or/AKA 'Deterministic') Environment/Container/Plane" in response.text
    assert "Qualitative Data Analysis Environment/Container/Plane" in response.text
    assert "browser storage presentation only" in response.text
    assert "localStorage.removeItem(sharedStorageKey)" in response.text
    assert 'id="authority-rail"' in response.text
    assert 'id="sublayer-map-band"' in response.text
    assert 'id="sublayer-map-panel"' in response.text
    assert 'class="sublayer-map-panel diagram-canvas"' in response.text
    assert "Sublayer Material And Analysis Map" in response.text
    assert 'data-step-target="intent-band"' in response.text
    assert 'aria-current="step"' in response.text
    assert 'data-step-target="source-fieldset"' in response.text
    assert 'data-step-target="gate-b-band"' in response.text
    assert 'aria-controls="result-review-band"' in response.text
    assert 'data-available="false"' in response.text
    assert 'id="intent-band"' in response.text
    assert 'id="source-fieldset"' in response.text
    assert 'id="source-intake-rendered-controls"' in response.text
    assert 'data-rendered-mode="operator_source_intake_rendered_controls"' in response.text
    assert 'id="source-intake-upload-form"' in response.text
    assert 'id="source-intake-file"' in response.text
    assert 'id="source-intake-refresh"' in response.text
    assert 'id="source-intake-inventory-list"' in response.text
    assert 'id="source-intake-preview-panel"' in response.text
    assert 'id="source-intake-gate-b-status"' in response.text
    assert 'id="source-directory-ingestion-rendered-controls"' in response.text
    assert (
        'data-rendered-mode="rendered_server_configured_source_directory_ingestion_control"'
        in response.text
    )
    assert 'id="source-directory-ingestion-scan-form"' in response.text
    assert 'id="source-directory-ingestion-client-request-id"' in response.text
    assert 'id="source-directory-ingestion-batch-id"' in response.text
    assert 'id="source-directory-ingestion-status"' in response.text
    assert 'id="source-directory-ingestion-scan-submit"' in response.text
    assert 'id="source-directory-ingestion-panel"' in response.text
    assert 'id="raw-mixed-corpus-batch-id"' in response.text
    assert 'id="raw-mixed-manifest-ref"' in response.text
    assert 'id="raw-mixed-manifest-hash"' in response.text
    assert 'id="raw-mixed-operator-confirmation"' in response.text
    assert 'id="raw-mixed-materialize"' in response.text
    assert 'id="dataset-version-candidates"' in response.text
    assert 'id="dataset-version-ids"' in response.text
    assert "APS-derived DatasetVersion selection" in response.text
    assert "CSV, XLSX, JSON recordset, or bounded SEC/EDGAR text tables" in response.text
    assert 'id="aps-content-document-candidates"' in response.text
    assert 'id="aps-content-document-ids"' in response.text
    assert "APS content document selection" in response.text
    assert "ApsContentDocument" in response.text
    assert 'id="gate-b-band"' in response.text
    assert 'id="result-review-band"' in response.text
    assert 'id="execution-select"' in response.text
    assert 'id="execution-start"' in response.text
    assert 'id="execution-selection-start-panel"' in response.text
    assert 'id="intent-form"' in response.text
    assert 'id="material-ledger-body"' in response.text
    assert 'id="gate-c-panel"' in response.text
    assert 'id="plan-panel"' in response.text
    assert 'id="plan-preview"' in response.text
    assert 'id="plan-reject"' in response.text
    assert 'id="plan-request-revision"' in response.text
    assert 'id="plan-approve"' in response.text
    assert 'id="execution-step-chip"' in response.text
    assert 'id="results-step-chip"' in response.text
    assert 'id="package-step-chip"' in response.text
    assert 'id="result-review-panel"' in response.text
    assert 'id="result-review-refresh"' in response.text
    assert 'id="result-status-inspect"' in response.text
    assert 'id="result-review-decision"' in response.text
    assert 'id="result-review-notes"' in response.text
    assert 'id="result-review-submit"' in response.text
    assert 'id="package-review-preview-panel"' in response.text
    assert 'id="package-review-preview-inspect"' in response.text
    assert 'id="package-construction-commit"' in response.text
    assert 'id="package-supersession-preview-submit"' in response.text
    assert 'id="replacement-package-set-authority-submit"' in response.text
    assert 'id="package-supersession-commit-submit"' in response.text
    assert 'id="replacement-package-artifact-manifest-submit"' in response.text
    assert 'id="replacement-package-namespace-submit"' in response.text
    assert 'id="replacement-package-namespace-panel"' in response.text
    assert 'id="package-review-submit-form"' in response.text
    assert 'id="package-supersession-preview-panel"' in response.text
    assert 'data-rendered-mode="rendered_package_supersession_preview_control"' in response.text
    assert 'id="source-directory-package-supersession-preview-submit"' in response.text
    assert 'id="source-directory-package-supersession-preview-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_source_directory_package_supersession_preview_control"'
        in response.text
    )
    assert 'id="source-directory-package-supersession-preview-authority"' in response.text
    assert 'id="replacement-package-set-authority-panel"' in response.text
    assert 'data-rendered-mode="rendered_replacement_package_set_authority_control"' in response.text
    assert 'id="package-supersession-commit-panel"' in response.text
    assert 'data-rendered-mode="rendered_package_supersession_commit_control"' in response.text
    assert 'id="replacement-package-artifact-manifest-panel"' in response.text
    assert 'data-rendered-mode="rendered_replacement_package_artifact_manifest_control"' in response.text
    assert 'id="package-review-submit-decision"' in response.text
    assert 'id="package-review-submit-notes"' in response.text
    assert 'id="package-review-submit"' in response.text
    assert 'id="handoff-step-chip"' in response.text
    assert 'id="handoff-export-prepare-form"' in response.text
    assert 'id="handoff-export-prepare-panel"' in response.text
    assert 'id="handoff-export-prepare-decision"' in response.text
    assert 'id="handoff-export-prepare-notes"' in response.text
    assert 'id="handoff-export-prepare-submit"' in response.text
    assert 'id="aps-handoff-dispatch-form"' in response.text
    assert 'id="aps-handoff-dispatch-panel"' in response.text
    assert 'id="aps-handoff-dispatch-submit"' in response.text
    assert 'id="authority-matrix-review-panel"' in response.text
    assert 'data-rendered-mode="rendered_authority_matrix_read_only_review_surface"' in response.text
    assert 'id="candidate-b-default-promotion-status-panel"' in response.text
    assert 'data-rendered-mode="rendered_candidate_b_default_promotion_read_only_status_surface"' in response.text
    assert 'data-frontend-durable-authority="false"' in response.text
    assert 'id="sec-edgar-source-acquisition-authority-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_sec_edgar_text_table_source_acquisition_authority_control"'
        in response.text
    )
    assert "SEC EDGAR source-acquisition authority bootstrap contract is not available." in response.text
    assert 'id="sec-edgar-live-source-artifact-acquisition-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_sec_edgar_text_table_live_source_artifact_acquisition_control"'
        in response.text
    )
    assert "SEC EDGAR live source-artifact acquisition bootstrap contract is not available." in response.text
    assert 'id="sec-edgar-downstream-operator-status-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_sec_edgar_text_table_downstream_layer3_operator_status_control"'
        in response.text
    )
    assert "SEC EDGAR downstream operator-status bootstrap contract is not available." in response.text
    assert 'id="sec-edgar-live-downstream-operator-status-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_sec_edgar_text_table_live_source_artifact_downstream_operator_status_control"'
        in response.text
    )
    assert "SEC EDGAR live downstream operator-status bootstrap contract is not available." in response.text
    assert 'id="sec-edgar-html-inline-xbrl-downstream-operator-status-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_sec_edgar_html_inline_xbrl_downstream_operator_status_control"'
        in response.text
    )
    assert "SEC EDGAR HTML/iXBRL downstream operator-status bootstrap contract is not available." in response.text
    assert 'id="sec-edgar-html-inline-xbrl-fact-material-downstream-operator-status-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_control"'
        in response.text
    )
    assert (
        "SEC EDGAR HTML/iXBRL fact-material downstream operator-status bootstrap contract is not available."
        in response.text
    )
    assert 'id="sec-edgar-html-inline-xbrl-fact-material-downstream-repeatability-trial-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_control"'
        in response.text
    )
    assert (
        "SEC EDGAR HTML/iXBRL fact-material downstream repeatability-trial bootstrap contract is not available."
        in response.text
    )
    assert 'id="sec-edgar-live-downstream-repeatability-trial-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_sec_edgar_text_table_live_source_artifact_downstream_operator_repeatability_trial_control"'
        in response.text
    )
    assert "SEC EDGAR live downstream repeatability-trial bootstrap contract is not available." in response.text
    assert 'id="sec-edgar-downstream-repeatability-trial-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_sec_edgar_text_table_downstream_operator_repeatability_trial_control"'
        in response.text
    )
    assert "SEC EDGAR downstream repeatability-trial bootstrap contract is not available." in response.text
    assert 'id="mockup-activation-readiness-panel"' in response.text
    assert 'data-rendered-mode="rendered_mockup_activation_readiness_dashboard"' in response.text
    assert 'data-frontend-durable-authority="false"' in response.text
    assert 'id="layer3-e2e-governance-lifecycle-dashboard-panel"' in response.text
    assert 'data-rendered-mode="rendered_layer3_end_to_end_governance_lifecycle_read_only_dashboard"' in response.text
    assert 'id="downstream-access-lifecycle-dashboard-panel"' in response.text
    assert 'data-rendered-mode="rendered_downstream_access_lifecycle_read_only_dashboard"' in response.text
    assert 'id="external-export-download-prepare-form"' in response.text
    assert 'id="external-export-download-prepare-panel"' in response.text
    assert 'id="external-export-download-prepare-submit"' in response.text
    assert 'id="external-export-download-delivery-form"' in response.text
    assert 'id="external-export-download-delivery-panel"' in response.text
    assert 'id="external-export-download-delivery-submit"' in response.text
    assert 'id="source-directory-hybrid-middle-lifecycle-form"' in response.text
    assert (
        'data-rendered-mode="rendered_source_directory_hybrid_middle_lifecycle_control"'
        in response.text
    )
    assert 'id="source-directory-hybrid-middle-lifecycle-panel"' in response.text
    assert 'id="source-directory-hybrid-middle-lifecycle-authority"' in response.text
    assert 'id="source-directory-hybrid-authority-prepare"' in response.text
    assert 'id="source-directory-hybrid-middle-lifecycle-submit"' in response.text
    assert 'id="source-directory-hybrid-external-export-download-delivery-form"' in response.text
    assert (
        'data-rendered-mode="rendered_source_directory_hybrid_external_export_download_delivery_control"'
        in response.text
    )
    assert 'id="source-directory-hybrid-external-export-download-delivery-authority"' in response.text
    assert 'id="source-directory-hybrid-external-export-download-delivery-status"' in response.text
    assert 'id="source-directory-hybrid-external-export-download-delivery-submit"' in response.text
    assert 'id="source-directory-hybrid-internal-webhook-form"' in response.text
    assert (
        'data-rendered-mode="rendered_source_directory_hybrid_internal_webhook_dispatch_control"'
        in response.text
    )
    assert 'data-frontend-durable-authority="false"' in response.text
    assert 'id="source-directory-hybrid-internal-webhook-panel"' in response.text
    assert 'id="source-directory-hybrid-internal-webhook-authority"' in response.text
    assert 'id="source-directory-hybrid-internal-webhook-status"' in response.text
    assert 'id="source-directory-hybrid-internal-webhook-submit"' in response.text
    assert 'id="external-export-download-signed-reference-form"' in response.text
    assert 'id="external-export-download-signed-reference-panel"' in response.text
    assert 'id="external-export-download-signed-reference-generate"' in response.text
    assert 'id="external-export-download-signed-reference-use"' in response.text
    assert 'id="connector-local-destination-receipt-panel"' in response.text
    assert 'data-rendered-mode="rendered_connector_local_destination_receipt_read_only_status_surface"' in response.text
    assert 'id="server-owned-local-outbox-target-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_server_owned_local_outbox_fake_target_read_only_status_surface"'
        in response.text
    )
    assert 'id="server-owned-local-outbox-write-panel"' in response.text
    assert 'data-rendered-mode="rendered_server_owned_local_outbox_write_read_only_status_surface"' in response.text
    assert 'id="local-outbox-provider-private-handoff-panel"' in response.text
    assert (
        'data-rendered-mode="rendered_local_outbox_provider_private_handoff_read_only_status_surface"'
        in response.text
    )
    assert 'id="external-local-export-panel"' in response.text
    assert 'data-rendered-mode="rendered_external_local_export_read_only_status_surface"' in response.text
    assert 'id="internal-webhook-dispatch-panel"' in response.text
    assert 'data-rendered-mode="rendered_internal_webhook_dispatch_read_only_status_surface"' in response.text
    assert 'id="provider-public-url-form"' in response.text
    assert 'data-rendered-mode="provider_public_url_prepare_status_revoke_controls"' in response.text
    assert 'data-rendered-extension="provider_public_url_delivery_use_rendered_control_extension"' in response.text
    assert 'id="provider-public-url-panel"' in response.text
    assert 'id="provider-public-url-prepare"' in response.text
    assert 'id="provider-public-url-status"' in response.text
    assert 'id="provider-public-url-use"' in response.text
    assert 'id="provider-public-url-revoke"' in response.text
    assert 'id="provider-public-url-deliver"' not in response.text
    assert "The use control records only a server-returned redacted allow/deny decision." in response.text
    assert 'href="/review/layer3/static/layer3.css"' in response.text
    assert 'src="/review/layer3/static/layer3.js"' in response.text
    assert "Plan</button>" in response.text
    assert "Execution</button>" in response.text
    assert "Results</button>" in response.text
    assert "Package</button>" in response.text
    assert "Handoff</button>" in response.text


def test_layer3_static_assets_are_mounted() -> None:
    review_css = client.get("/review/layer3/static/review.css")
    css = client.get("/review/layer3/static/layer3.css")
    js = client.get("/review/layer3/static/layer3.js")
    workbench = client.get("/review/layer3/static/workbench.html")

    assert review_css.status_code == 200
    assert css.status_code == 200
    assert js.status_code == 200
    assert workbench.status_code == 200
    js_text = js.text.replace("\r\n", "\n")
    assert "mockup spec §8A plus one bounded APS content document trace sample" in workbench.text
    assert "APS content document<br>selection" in workbench.text
    assert "aps-doc-operator-evidence-001" in workbench.text
    assert "ML26001A001" in workbench.text
    assert "aps_content_units_v2" in workbench.text
    assert "traceable_aps_content_document" in workbench.text
    assert "No corpus-backed manual/custom specification loaded." in workbench.text
    assert "const SPEC_CHIPS = [];" in workbench.text
    assert "Manual spec choices are intentionally empty" in workbench.text
    assert "Manual source classes<br>and intent chips" not in workbench.text
    assert "String(MATERIALS.length)" in workbench.text
    assert 'html[data-theme="workbench"]' in review_css.text
    assert ".authority-rail" in css.text
    assert "body.layer3-page" in css.text
    assert "overflow: visible" in css.text
    assert 'html[data-theme-variant="layer3_mockup_workbench_theme"] body.layer3-page .mockup-theme-shell' in css.text
    assert ".mockup-theme-flow" in css.text
    assert ".mockup-execution-lanes" in css.text
    assert ".mockup-execution-lanes-projection" in css.text
    assert ".mockup-execution-lanes-live-grid" in css.text
    assert ".mockup-execution-lane-plane-counts" in css.text
    assert ".mockup-execution-lanes-source-list" in css.text
    assert ".mockup-output-review-package-handoff-projection" in css.text
    assert ".mockup-output-review-live-grid" in css.text
    assert ".mockup-output-review-source-list" in css.text
    assert ".mockup-userflow-board" in css.text
    assert ".mockup-sublayers-ab-board" in css.text
    assert ".mockup-sublayers-ab-projection" in css.text
    assert ".mockup-sublayers-ab-live-grid" in css.text
    assert ".mockup-sublayers-ab-modality-counts" in css.text
    assert ".mockup-sublayers-ab-source-list" in css.text
    assert ".mockup-ab-ledger" in css.text
    assert ".mockup-ab-group" in css.text
    assert ".mockup-pdf-location-card" in css.text
    assert ".mockup-pdf-intent-card" in css.text
    assert ".mockup-pdf-location-projection" in css.text
    assert ".mockup-pdf-summary-card" in css.text
    assert '.mockup-pdf-location-projection[data-projection-state="available"]' in css.text
    assert ".mockup-pdf-location-item" in css.text
    assert ".mockup-query-source-setup-projection" in css.text
    assert ".mockup-query-source-live-grid" in css.text
    assert ".mockup-query-source-source-list" in css.text
    assert ".mockup-userflow-stage" in css.text
    assert ".mockup-canvas-title" in css.text
    assert ".mockup-process-note" in css.text
    assert ".mockup-ingress-stack::after" in css.text
    assert ".mockup-output-card" in css.text
    assert ".mockup-disabled-control" in css.text
    assert ".step-chip.current" in css.text
    assert ".step-chip:focus-visible" in css.text
    assert ".workband:focus" in css.text
    assert "outline: 3px solid var(--primary-color)" in css.text
    assert 'html[data-theme="workbench"] body.layer3-page' in css.text
    assert "--l3-stage-accent" in css.text
    assert ".diagram-canvas::before" in css.text
    assert ".sublayer-map-panel" in css.text
    assert ".sublayer-region" in css.text
    assert ".canvas-intake-spec" in css.text
    assert ".source-spec-chip-grid" in css.text
    assert ".source-intake-panel" in css.text
    assert ".source-intake-inventory-item" in css.text
    assert ".source-intake-preview-text" in css.text
    assert ".source-intake-gate-b-admission" in css.text
    assert ".source-intake-proof-list" in css.text
    assert ".raw-mixed-materialization" in css.text
    assert ".raw-mixed-materialization-grid" in css.text
    assert ".dataset-version-selector" in css.text
    assert ".dataset-version-candidate" in css.text
    assert ".aps-content-document-selector" in css.text
    assert ".aps-content-document-candidate" in css.text
    assert ".source-family-summary" in css.text
    assert ".source-family-trace" in css.text
    assert ".refused-artifact-traces" in css.text
    assert ".refused-artifact-trace" in css.text
    assert ".unsupported-material-trace" in css.text
    assert ".ledger-chip-field" in css.text
    assert ".diagram-chip-grid" in css.text
    assert ".plane-arrow" in css.text
    assert ".plane-bracket" in css.text
    assert ".analysis-plane" in css.text
    assert ".modality-quantitative" in css.text
    assert "border: 1px dashed #7d7d7d" in css.text
    assert ".layer3-header .header-right select" in css.text
    assert "const API_ROOT = '/api/v1/layer3';" in js.text
    assert "const LAYER3_THEME_STORAGE_KEY = 'layer3_workbench_theme';" in js.text
    assert "const LAYER3_MOCKUP_WORKBENCH_THEME = 'layer3_mockup_workbench_theme';" in js.text
    assert "const LAYER3_MOCKUP_THEME_FIRST_SLICE = 'mockup_theme_shell_and_fixture_projection';" in js.text
    assert "function renderMockupThemeShell" in js.text
    assert "function renderMockupPdfLocationProjection" in js.text
    assert "function renderMockupQuerySourceSetupProjection" in js.text
    assert "function mockupQuerySourceSetupServerSources" in js.text
    assert "function renderMockupSublayersAbLiveProjection" in js.text
    assert "function mockupSublayersAbServerSources" in js.text
    assert "function mockupSublayersAbGateLabel" in js.text
    assert "function renderMockupExecutionLanesLiveProjection" in js.text
    assert "function mockupExecutionLanesServerSources" in js.text
    assert "function mockupExecutionLanesSafeState" in js.text
    assert "function mockupPdfLocationHighlightSpanCount" in js.text
    assert "State.sessionSummary?.pdf_location_projection" in js.text
    assert "State.preflight" in js.text
    assert "State.sourcePreview" in js.text
    assert "State.sessionSummary?.sublayer_visualization" in js.text
    assert "SUBLAYER_VISUALIZATION_COLLECTION_PAGE_SIZE = 500" in js.text
    assert "function hydrateSublayerVisualizationCollections" in js.text
    assert "sublayer-visualization/${encodeURIComponent(collection)}" in js.text
    assert "hydrated_from_paged_sublayer_visualization_collection" in js.text
    assert "State.materialPreview" in js.text
    assert "State.gateB" in js.text
    assert "State.gateC" in js.text
    assert "Server Sublayers 3A/3B projection unavailable" in js.text
    assert "Server-owned Sublayers 3A/3B projection" in js.text
    assert "Server-owned Sublayer 3C execution-lanes projection" in js.text
    assert "Server Sublayer 3C execution-lanes projection unavailable" in js.text
    assert "dataset.liveProjectionReadOnly = 'true'" in js.text
    assert "State.sessionSummary?.analysis_environment_projection" in js.text
    assert "dataset.liveProjectionReadOnly = 'true'" in js.text
    assert "mockup-pdf-location-highlight" in js.text
    assert "Read-only server projection pending" in js.text
    assert "dataset.themeVariant = LAYER3_MOCKUP_WORKBENCH_THEME" in js.text
    assert "userflow/layer3_user-flow-overview1.png" in js.text
    assert "focus_on_these/sublayer3C.png" in js.text
    assert "example-use-case-location-in-pdf.png" in js.text
    assert "const LAYER3_SESSION_RECOVERY_STORAGE_KEY = 'layer3_workbench_session_recovery_v1';" in js.text
    assert "const LAYER3_GATE_B_DRAFT_STORAGE_KEY = 'layer3_workbench_gate_b_draft_v1';" in js.text
    assert "const LAYER3_PROVIDER_PRIVATE_RECEIPT_STORAGE_KEY = 'layer3_provider_private_receipt_v1';" in js.text
    assert "LAYER3_SESSION_RECOVERY_SCHEMA_ID = 'layer3.browser_session_recovery.v1'" in js.text
    assert "LAYER3_GATE_B_DRAFT_SCHEMA_ID = 'layer3.gate_b_draft_snapshot.v1'" in js.text
    assert "LAYER3_PROVIDER_PRIVATE_RECEIPT_SCHEMA_ID = 'layer3.provider_private_receipt_recovery.v1'" in js.text
    assert "browser_receipt_handle_only_server_revalidated_on_status_or_revoke" in js.text
    assert "PROVIDER_PRIVATE_SIGNED_URL_REPLACEABLE_STATES" in js.text
    assert "provider_private_signed_url_expired" in js.text
    assert "function providerPrivateSignedUrlBlocksPrepare" in js.text
    assert "function providerPrivateSignedUrlPrepareRequestId" in js.text
    assert "client_request_id: providerPrivateSignedUrlPrepareRequestId()" in js.text
    assert "PROVIDER_PUBLIC_URL_REPLACEABLE_STATES" in js.text
    assert "function providerPublicUrlPrepareRequestId" in js.text
    assert "client_request_id: providerPublicUrlPrepareRequestId()" in js.text
    assert "function providerPublicUrlUsePayload" in js.text
    assert "function providerPublicUrlLatestSnapshot" in js.text
    assert "function canUseProviderPublicUrl" in js.text
    assert "&& !State.providerPublicUrlUse" in js.text
    assert "State.providerPublicUrlStatus?.provider_public_url_state" in js.text
    assert "State.providerPublicUrlUse?.provider_public_url_state" in js.text
    assert "State.providerPublicUrlUse = await postJson" in js.text
    assert "delivery_use_mode: 'fake_provider_redacted_use_decision'" in js.text
    assert "operator_decision: 'use_provider_public_url_redacted_fake_provider'" in js.text
    assert "provider_public_url_redacted" in js.text
    assert "raw_public_url_exposed" in js.text
    assert "public_url_enabled" in js.text
    assert "provider_network_enabled" in js.text
    assert "frontend_durable_authority_enabled" in js.text
    assert "browser_durable_authority: 'blocked_not_persisted'" in js.text
    assert "AUTHORITY_MATRIX_REVIEW_RENDERED_MODE = 'rendered_authority_matrix_read_only_review_surface'" in js.text
    assert "AUTHORITY_MATRIX_REVIEW_USE_CASE = 'operator_reviews_exposed_layer3_authority_matrix_in_rendered_review_surface_without_mutation_or_dispatch'" in js.text
    assert "AUTHORITY_MATRIX_REVIEW_RESPONSE_AUTHORITY = 'State.bootstrap.authority_matrix_contract'" in js.text
    assert "PACKAGE_SUPERSESSION_PREVIEW_RENDERED_MODE = 'rendered_package_supersession_preview_control'" in js.text
    assert "PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION = 'preview_package_supersession'" in js.text
    assert "function packageSupersessionPreviewPayload" in js.text
    assert "postJson('/package/mutation/preview'" in js.text
    assert "package_supersession_preview_ready" in js.text
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RENDERED_MODE = 'rendered_source_directory_package_supersession_preview_control'" in js.text
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_RESPONSE_AUTHORITY = 'State.sourceDirectoryPackageSupersessionPreview'" in js.text
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION = 'preview_source_directory_package_supersession'" in js.text
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_PATH = '/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/preview'" in js.text
    assert "layer3.source_directory_qualitative_analysis_package_supersession_preview.v1" in js.text
    assert "source_directory_qualitative_analysis_package_supersession_preview_authority" in js.text
    assert "function sourceDirectoryPackageSupersessionPreviewPayload" in js.text
    assert "postJson(\n            SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_PATH" in js_text
    assert "source_directory_package_supersession_preview_ready" in js.text
    assert "redacted_local_payload_ref" in js.text
    assert "function authorityMatrixContract" in js.text
    assert "function authorityMatrixReviewState" in js.text
    assert "function renderAuthorityMatrixReviewPanel" in js.text
    assert "renderAuthorityMatrixReviewPanel()" in js.text
    assert "State.bootstrap?.authority_matrix_contract" in js.text
    assert "authority_matrix_bootstrap_contract_unavailable" in js.text
    assert "authority_matrix_fail_closed_read_only" in js.text
    assert "additional matrix route" in js.text
    assert "/authority-matrix" not in js.text
    assert "CANDIDATE_B_DEFAULT_PROMOTION_STATUS_RENDERED_MODE = 'rendered_candidate_b_default_promotion_read_only_status_surface'" in js.text
    assert "CANDIDATE_B_DEFAULT_PROMOTION_STATUS_USE_CASE = 'operator_reviews_candidate_b_default_promotion_status_without_selector_mutation_or_dispatch'" in js.text
    assert "CANDIDATE_B_DEFAULT_PROMOTION_STATUS_RESPONSE_AUTHORITY = 'State.bootstrap.execution_readiness'" in js.text
    assert "CANDIDATE_B_DEFAULT_PROMOTION_FINAL_PROOF_RENDERED_MODE = 'rendered_candidate_b_default_promotion_final_proof_recording_control'" in js.text
    assert "CANDIDATE_B_DEFAULT_PROMOTION_FINAL_PROOF_MODE = 'candidate_b_default_promotion_final_proof_v1'" in js.text
    assert "CANDIDATE_B_DEFAULT_PROMOTION_FINAL_PROOF_OPERATOR_DECISION = 'record_candidate_b_default_promotion_final_proof'" in js.text
    assert "CANDIDATE_B_DEFAULT_PROMOTION_FINAL_PROOF_STATUS_RENDERED_MODE = 'rendered_candidate_b_default_promotion_final_proof_status_inspection_control'" in js.text
    assert "CANDIDATE_B_DEFAULT_PROMOTION_FINAL_PROOF_STATUS_MODE = 'candidate_b_default_promotion_final_proof_status_v1'" in js.text
    assert "CANDIDATE_B_DEFAULT_PROMOTION_FINAL_PROOF_STATUS_OPERATOR_DECISION = 'inspect_candidate_b_default_promotion_final_proof_status'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_STATUS_RENDERED_MODE = 'rendered_candidate_b_full_corpus_operator_workflow_status_control'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_STATUS_MODE = 'candidate_b_full_corpus_operator_workflow_status_v1'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_STATUS_OPERATOR_DECISION = 'inspect_candidate_b_full_corpus_operator_workflow_status'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_EXECUTION_BOUNDARY_RENDERED_MODE = 'rendered_candidate_b_full_corpus_operator_workflow_execution_boundary_control'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_EXECUTION_BOUNDARY_MODE = 'append_only_execution_boundary_receipt_without_process_start_or_job_execution'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_EXECUTION_BOUNDARY_OPERATOR_DECISION = 'record_candidate_b_async_background_job_execution_boundary'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_PROCESS_EXECUTION_RENDERED_MODE = 'rendered_candidate_b_full_corpus_operator_workflow_process_execution_control'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_PROCESS_EXECUTION_MODE = 'server_owned_allowlisted_process_start_with_redacted_receipt_and_no_browser_command_authority'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_PROCESS_EXECUTION_OPERATOR_DECISION = 'record_candidate_b_async_background_process_execution'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_PROCESS_COMPLETION_RESULT_RENDERED_MODE = 'rendered_candidate_b_full_corpus_operator_workflow_process_completion_result_control'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_PROCESS_COMPLETION_RESULT_MODE = 'append_only_process_completion_result_adoption_receipt_without_source_run_mutation_or_raw_output_exposure'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_PROCESS_COMPLETION_RESULT_OPERATOR_DECISION = 'record_candidate_b_async_process_completion_result_adoption'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_ADOPTED_RESULT_DOWNSTREAM_PROOF_RENDERED_MODE = 'rendered_candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_control'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_ADOPTED_RESULT_DOWNSTREAM_PROOF_MODE = 'read_only_adopted_process_result_downstream_operator_proof_without_result_mutation_or_reexecution'" in js.text
    assert "CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_ADOPTED_RESULT_DOWNSTREAM_PROOF_OPERATOR_DECISION = 'record_candidate_b_async_adopted_process_result_downstream_operator_proof'" in js.text
    assert "function candidateBDefaultPromotionReadinessContract" in js.text
    assert "function candidateBDefaultPromotionStatusState" in js.text
    assert "function candidateBDefaultPromotionFinalProofPayload" in js.text
    assert "async function recordCandidateBDefaultPromotionFinalProof" in js.text
    assert "function candidateBDefaultPromotionFinalProofStatusPayload" in js.text
    assert "async function inspectCandidateBDefaultPromotionFinalProofStatus" in js.text
    assert "function candidateBFinalOperatorInspectionRows" in js.text
    assert "function candidateBOperatorStatusDeliveryPreviewRows" in js.text
    assert (
        "SEC_EDGAR_SOURCE_ACQUISITION_AUTHORITY_RENDERED_MODE = "
        "'rendered_sec_edgar_text_table_source_acquisition_authority_control'"
        in js.text
    )
    assert "SEC_EDGAR_SOURCE_ACQUISITION_AUTHORITY_MODE = 'sec_edgar_text_table_source_acquisition_authority_v1'" in js.text
    assert "function secEdgarSourceAcquisitionAuthorityPayload" in js.text
    assert "function renderSecEdgarSourceAcquisitionAuthorityPanel" in js.text
    assert "async function recordSecEdgarSourceAcquisitionAuthority" in js.text
    assert "sec-edgar-source-acquisition-authority-form" in js.text
    assert "raw source artifact ref rendered" in js.text
    assert (
        "SEC_EDGAR_LIVE_SOURCE_ARTIFACT_ACQUISITION_RENDERED_MODE = "
        "'rendered_sec_edgar_text_table_live_source_artifact_acquisition_control'"
        in js.text
    )
    assert (
        "SEC_EDGAR_LIVE_SOURCE_ARTIFACT_ACQUISITION_MODE = "
        "'sec_edgar_text_table_live_source_artifact_acquisition_v1'"
        in js.text
    )
    assert (
        "SEC_EDGAR_LIVE_SOURCE_ARTIFACT_ACQUISITION_OPERATOR_DECISION = "
        "'acquire_sec_edgar_text_table_live_source_artifact'"
        in js.text
    )
    assert "function secEdgarLiveSourceArtifactAcquisitionPayload" in js.text
    assert "function renderSecEdgarLiveSourceArtifactAcquisitionPanel" in js.text
    assert "async function acquireSecEdgarLiveSourceArtifact" in js.text
    assert "async function inspectSecEdgarLiveSourceArtifactStatus" in js.text
    assert "sec-edgar-live-source-artifact-acquisition-form" in js.text
    assert "sec-edgar-live-source-artifact-acquisition-submit" in js.text
    assert "sec-edgar-live-source-artifact-acquisition-status-submit" in js.text
    assert "sec-edgar-live-source-artifact-acquisition-request-json" in js.text
    assert "sec-edgar-live-source-artifact-acquisition-status-receipt-id" in js.text
    assert "sec-edgar-live-source-artifact-acquisition-operator-confirmation" in js.text
    assert "request JSON contains non-admitted fields" in js.text
    assert "server-derived URL hash" in js.text
    assert "browser supplied raw URL rejected" in js.text
    assert "SEC_EDGAR_DOWNSTREAM_OPERATOR_STATUS_RENDERED_MODE = 'rendered_sec_edgar_text_table_downstream_layer3_operator_status_control'" in js.text
    assert "SEC_EDGAR_DOWNSTREAM_OPERATOR_STATUS_MODE = 'sec_edgar_text_table_downstream_layer3_operator_status_v1'" in js.text
    assert "function secEdgarDownstreamOperatorStatusPayload" in js.text
    assert "function renderSecEdgarDownstreamOperatorStatusPanel" in js.text
    assert "async function inspectSecEdgarDownstreamOperatorStatus" in js.text
    assert "sec-edgar-downstream-operator-status-form" in js.text
    assert "raw proof receipt path rendered" in js.text
    assert (
        "SEC_EDGAR_LIVE_DOWNSTREAM_OPERATOR_STATUS_RENDERED_MODE = "
        "'rendered_sec_edgar_text_table_live_source_artifact_downstream_operator_status_control'"
    ) in js.text
    assert (
        "SEC_EDGAR_LIVE_DOWNSTREAM_OPERATOR_STATUS_MODE = "
        "'sec_edgar_text_table_live_source_artifact_downstream_operator_status_v1'"
    ) in js.text
    assert "function secEdgarLiveDownstreamOperatorStatusPayload" in js.text
    assert "function renderSecEdgarLiveDownstreamOperatorStatusPanel" in js.text
    assert "async function inspectSecEdgarLiveDownstreamOperatorStatus" in js.text
    assert "sec-edgar-live-downstream-operator-status-form" in js.text
    assert "live_downstream_proof_request" in js.text
    assert "live source artifact authority bound" in js.text
    assert (
        "SEC_EDGAR_HTML_INLINE_XBRL_DOWNSTREAM_OPERATOR_STATUS_RENDERED_MODE = "
        "'rendered_sec_edgar_html_inline_xbrl_downstream_operator_status_control'"
    ) in js.text
    assert (
        "SEC_EDGAR_HTML_INLINE_XBRL_DOWNSTREAM_OPERATOR_STATUS_MODE = "
        "'sec_edgar_html_inline_xbrl_downstream_operator_status_v1'"
    ) in js.text
    assert "function secEdgarHtmlInlineXbrlDownstreamOperatorStatusPayload" in js.text
    assert "function renderSecEdgarHtmlInlineXbrlDownstreamOperatorStatusPanel" in js.text
    assert "async function inspectSecEdgarHtmlInlineXbrlDownstreamOperatorStatus" in js.text
    assert "sec-edgar-html-inline-xbrl-downstream-operator-status-form" in js.text
    assert "html_inline_xbrl_downstream_proof_request" in js.text
    assert "parser authority bound" in js.text
    assert "material bridge authority bound" in js.text
    assert (
        "SEC_EDGAR_HTML_INLINE_XBRL_FACT_MATERIAL_DOWNSTREAM_OPERATOR_STATUS_RENDERED_MODE = "
        "'rendered_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_control'"
    ) in js.text
    assert (
        "SEC_EDGAR_HTML_INLINE_XBRL_FACT_MATERIAL_DOWNSTREAM_OPERATOR_STATUS_MODE = "
        "'sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_v1'"
    ) in js.text
    assert "function secEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatusPayload" in js.text
    assert "function renderSecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatusPanel" in js.text
    assert "async function inspectSecEdgarHtmlInlineXbrlFactMaterialDownstreamOperatorStatus" in js.text
    assert "sec-edgar-html-inline-xbrl-fact-material-downstream-operator-status-form" in js.text
    assert "fact_material_downstream_proof_request" in js.text
    assert "fact authority bound" in js.text
    assert "fact material bridge authority bound" in js.text
    assert "raw fact values rendered" in js.text
    assert "fact value reconstruction enabled" in js.text
    assert (
        "SEC_EDGAR_HTML_INLINE_XBRL_FACT_MATERIAL_REPEATABILITY_TRIAL_RENDERED_MODE = "
        "'rendered_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_repeatability_trial_control'"
        in js.text
    )
    assert (
        "SEC_EDGAR_HTML_INLINE_XBRL_FACT_MATERIAL_REPEATABILITY_TRIAL_MODE = "
        "'append_only_trial_receipt_over_original_and_repeat_fact_material_downstream_status_authority_without_sec_fetch_or_processing_execution'"
        in js.text
    )
    assert "function secEdgarHtmlInlineXbrlFactMaterialDownstreamRepeatabilityTrialPayload" in js.text
    assert "function renderSecEdgarHtmlInlineXbrlFactMaterialDownstreamRepeatabilityTrialPanel" in js.text
    assert "async function recordSecEdgarHtmlInlineXbrlFactMaterialDownstreamRepeatabilityTrial" in js.text
    assert "sec-edgar-html-inline-xbrl-fact-material-downstream-repeatability-trial-form" in js.text
    assert "fact inventory hash comparison" in js.text
    assert "raw fact values exposed" in js.text
    assert "SEC_EDGAR_REPEATABILITY_TRIAL_RENDERED_MODE = 'rendered_sec_edgar_text_table_downstream_operator_repeatability_trial_control'" in js.text
    assert "SEC_EDGAR_REPEATABILITY_TRIAL_MODE = 'append_only_trial_receipt_over_original_and_repeat_downstream_status_authority_without_sec_fetch_or_processing_execution'" in js.text
    assert "function secEdgarDownstreamRepeatabilityTrialPayload" in js.text
    assert "function renderSecEdgarDownstreamRepeatabilityTrialPanel" in js.text
    assert "async function recordSecEdgarDownstreamRepeatabilityTrial" in js.text
    assert "sec-edgar-downstream-repeatability-trial-form" in js.text
    assert "operator status hash comparison" in js.text
    assert "function candidateBFullCorpusOperatorWorkflowStatusRows" in js.text
    assert "async function inspectCandidateBFullCorpusOperatorWorkflowStatus" in js.text
    assert "function candidateBFullCorpusOperatorWorkflowExecutionBoundaryRows" in js.text
    assert "function candidateBExecutionBoundaryProjectionItems" in js.text
    assert "async function recordCandidateBFullCorpusOperatorWorkflowExecutionBoundary" in js.text
    assert "Operator Status Delivery Preview" in js.text
    assert "Full-Corpus Operator Workflow Status" in js.text
    assert "Full-Corpus Operator Workflow Execution Boundary" in js.text
    assert "execution_boundary_projection" in js.text
    assert "Full-Corpus Operator Workflow Process Execution" in js.text
    assert "process_execution_projection" in js.text
    assert "process_completion_result_projection" in js.text
    assert "adopted_result_downstream_proof_projection" in js.text
    assert "Full-Corpus Operator Workflow Adopted Result Downstream Proof" in js.text
    assert "function candidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProofPayload" in js.text
    assert "async function recordCandidateBFullCorpusOperatorWorkflowAdoptedResultDownstreamProof" in js.text
    assert "Redacted retained role previews" in js.text
    assert "Redacted runtime delivery artifact previews" in js.text
    assert "function renderCandidateBDefaultPromotionStatusPanel" in js.text
    assert "renderCandidateBDefaultPromotionStatusPanel()" in js.text
    assert "candidate_b_default_promotion_status_contract_visible" in js.text
    assert "candidate-b-final-proof-form" in js.text
    assert "candidate-b-final-proof-submit" in js.text
    assert "candidate-b-final-proof-status-form" in js.text
    assert "candidate-b-final-proof-status-submit" in js.text
    assert "candidate_b_opendataloader_pdf_eligible_pdf_corpus_processing_only" in js.text
    assert "selector mutation from this panel" in js.text
    assert "Server records final proof from readiness-audit authority; this control performs no selector mutation." in js.text
    assert "Server revalidates the final proof receipt; this control records no selector mutation." in js.text
    assert "State.bootstrap?.execution_readiness" in js.text
    assert "candidate_b_default_promotion_operator_status_endpoint" in js.text
    assert "sec_edgar_text_table_downstream_operator_status_endpoint" in js.text
    assert "candidate_b_full_corpus_operator_workflow_status_endpoint" in js.text
    assert "candidate_b_full_corpus_operator_workflow_execution_boundary_endpoint" in js.text
    assert "candidate_b_full_corpus_operator_workflow_process_execution_endpoint" in js.text
    assert "candidate_b_full_corpus_operator_workflow_process_completion_result_endpoint" in js.text
    assert "candidate_b_full_corpus_operator_workflow_adopted_result_downstream_proof_endpoint" in js.text
    assert "candidate_b_broader_eligible_corpus_default_scope_default_promotion_endpoint" in js.text
    assert "candidate-b-broader-scope-default-promotion-form" in js.text
    assert "candidate-b-broader-scope-default-promotion-submit" in js.text
    assert "rendered_candidate_b_broader_eligible_corpus_default_scope_default_promotion_control" in js.text
    assert "candidateBBroaderScopeDefaultPromotionPayload" in js.text
    assert "Server records broader-scope default promotion only from a ready promotion-readiness audit" in js.text
    assert "candidate_b_default_promotion_final_proof_endpoint" in js.text
    assert "candidate_b_default_promotion_final_proof_status_endpoint" in js.text
    assert "/source/ingestion/candidate-b/default-promotion/operator-status" not in js.text
    assert "/source/ingestion/candidate-b/full-corpus/operator-workflow/status" not in js.text
    assert "/source/ingestion/candidate-b/full-corpus/operator-workflow/execution/boundary" not in js.text
    assert "/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/default-promotion" not in js.text
    assert "/source/ingestion/candidate-b/default-promotion/final-proof" not in js.text
    assert "/source/ingestion/candidate-b/default-promotion/final-proof/status" not in js.text
    assert "LAYER3_E2E_GOVERNANCE_LIFECYCLE_DASHBOARD_MODE = 'rendered_layer3_end_to_end_governance_lifecycle_read_only_dashboard'" in js.text
    assert "LAYER3_E2E_GOVERNANCE_LIFECYCLE_USE_CASE = 'operator_inspects_layer3_end_to_end_governance_lifecycle_without_mutation_or_dispatch'" in js.text
    assert "function layer3E2EGovernanceLifecycleRows" in js.text
    assert "function renderLayer3E2EGovernanceLifecycleDashboardPanel" in js.text
    assert "renderLayer3E2EGovernanceLifecycleDashboardPanel()" in js.text
    assert "DOWNSTREAM_ACCESS_LIFECYCLE_DASHBOARD_MODE = 'rendered_downstream_access_lifecycle_read_only_dashboard'" in js.text
    assert "DOWNSTREAM_ACCESS_LIFECYCLE_USE_CASE = 'operator_inspects_downstream_access_lifecycle_without_dispatch_or_raw_url_use'" in js.text
    assert "function downstreamAccessLifecycleRows" in js.text
    assert "function renderDownstreamAccessLifecycleDashboardPanel" in js.text
    assert "renderDownstreamAccessLifecycleDashboardPanel()" in js.text
    assert "CONNECTOR_LOCAL_RECEIPT_STATUS_SURFACE_MODE = 'rendered_connector_local_destination_receipt_read_only_status_surface'" in js.text
    assert "CONNECTOR_LOCAL_RECEIPT_STATUS_USE_CASE = 'operator_reviews_connector_local_destination_receipt_status_without_real_connector_invocation_or_destination_write'" in js.text
    assert "CONNECTOR_LOCAL_RECEIPT_STATUS_RESPONSE_AUTHORITY = 'State.sessionSummary.connector_local_destination_receipt'" in js.text
    assert "function connectorLocalDestinationReceiptStatusState" in js.text
    assert "SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATUS_SURFACE_MODE = 'rendered_server_owned_local_outbox_fake_target_read_only_status_surface'" in js.text
    assert "SERVER_OWNED_LOCAL_OUTBOX_TARGET_STATUS_RESPONSE_AUTHORITY = 'State.sessionSummary.server_owned_local_outbox_target'" in js.text
    assert "function serverOwnedLocalOutboxTargetStatusState" in js.text
    assert "function renderServerOwnedLocalOutboxTargetStatusPanel" in js.text
    assert "renderServerOwnedLocalOutboxTargetStatusPanel()" in js.text
    assert "SERVER_OWNED_LOCAL_OUTBOX_WRITE_STATUS_SURFACE_MODE = 'rendered_server_owned_local_outbox_write_read_only_status_surface'" in js.text
    assert "LOCAL_OUTBOX_PROVIDER_PRIVATE_HANDOFF_STATUS_SURFACE_MODE = 'rendered_local_outbox_provider_private_handoff_read_only_status_surface'" in js.text
    assert "EXTERNAL_LOCAL_EXPORT_STATUS_SURFACE_MODE = 'rendered_external_local_export_read_only_status_surface'" in js.text
    assert "EXTERNAL_LOCAL_EXPORT_STATUS_RESPONSE_AUTHORITY = 'State.sessionSummary.external_local_export'" in js.text
    assert "function externalLocalExportStatusState" in js.text
    assert "function renderExternalLocalExportStatusPanel" in js.text
    assert "renderExternalLocalExportStatusPanel()" in js.text
    assert "INTERNAL_WEBHOOK_DISPATCH_STATUS_SURFACE_MODE = 'rendered_internal_webhook_dispatch_read_only_status_surface'" in js.text
    assert "INTERNAL_WEBHOOK_DISPATCH_STATUS_RESPONSE_AUTHORITY = 'State.sessionSummary.internal_webhook_dispatch'" in js.text
    assert "SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_RENDERED_MODE = 'rendered_source_directory_hybrid_internal_webhook_dispatch_control'" in js.text
    assert "SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_DISPATCH_PATH = '/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/dispatch'" in js.text
    assert "SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_STATUS_PATH = '/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/status'" in js.text
    assert "SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_OPERATOR_DECISION = 'dispatch_source_directory_hybrid_internal_webhook'" in js.text
    assert "function sourceDirectoryHybridInternalWebhookPayload" in js.text
    assert "function renderSourceDirectoryHybridInternalWebhookPanel" in js.text
    assert "async function submitSourceDirectoryHybridInternalWebhook" in js.text
    assert "async function inspectSourceDirectoryHybridInternalWebhookStatus" in js.text
    assert "renderSourceDirectoryHybridInternalWebhookPanel()" in js.text
    assert "function internalWebhookDispatchStatusState" in js.text
    assert "function renderInternalWebhookDispatchStatusPanel" in js.text
    assert "renderInternalWebhookDispatchStatusPanel()" in js.text
    assert "function renderConnectorLocalDestinationReceiptStatusPanel" in js.text
    assert "function connectorLocalDestinationReceiptHistoryRows" in js.text
    assert "function renderConnectorLocalDestinationReceiptFailureProjection" in js.text
    assert "same_key_different_payload_conflict" in js.text
    assert "Lifecycle Policy" in js.text
    assert "Guardrail Projection" in js.text
    assert "renderConnectorLocalDestinationReceiptStatusPanel()" in js.text
    assert "renderReplacementPackageSetAuthorityPanel()" in js.text
    assert "SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_MODE = 'rendered_source_directory_replacement_package_set_authority_control'" in js.text
    assert "SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_SOURCE_AUTHORITY = 'State.sourceDirectoryPackageSupersessionPreview'" in js.text
    assert "function replacementPackageSetAuthorityPreviewState" in js.text
    assert "return packagePreview || sourceDirectoryPreview || null" in js.text
    assert "function replacementPackageSetAuthoritySourcePackageSetHash" in js.text
    assert "replacementPackageArtifactMaterializationPayload()" in js.text
    assert "replacementPackageSetAuthorityPayload(materialization)" in js.text
    assert "/package/replacement-artifact/materialize" in js.text
    assert "/package/replacement-set/record" in js.text
    assert "record_replacement_package_set_authority" in js.text
    assert "connector_local_destination_receipt_recorded" in js.text
    assert "connector_local_destination_receipt_ready" in js.text
    assert "real_destination_integration" in js.text
    assert "/handoff/connector/local-destination/receipt" not in js.text
    assert "provider_public_url_redacted ? 'redacted_receipt_only'" in js.text
    assert "raw public URL display/use" in js.text
    assert "MOCKUP_ACTIVATION_READINESS_RENDERED_MODE = 'rendered_mockup_activation_readiness_dashboard'" in js.text
    assert "MOCKUP_ACTIVATION_READINESS_RESPONSE_AUTHORITY = 'State.bootstrap.mockup_activation_readiness'" in js.text
    assert "function renderMockupActivationReadinessPanel" in js.text
    assert "query_source_setup_interactive_live_classification" in js.text
    assert "output_review_package_handoff_interactive_live_contract" in js.text
    assert "selected projection slice" in js.text
    assert "selected_projection_slices" in js.text
    assert "projection.contract_id" in js.text
    assert "projection.schema_id" in js.text
    assert "projection.status_projection" in js.text
    assert "projection.negative_boundaries" in js.text
    assert "selected next slice" in js.text
    assert "unapproved_provider_object_or_network_write" in js.text
    assert "broad_source_family_expansion" in js.text
    assert "broad_model_provider_rag_expansion" in js.text
    assert "broad_source_model_rag_expansion" not in js.text
    assert "full mockup activation" in js.text
    assert "frontend durable authority" in js.text
    assert ".authority-matrix-review-panel" in css.text
    assert ".authority-matrix-review-grid" in css.text
    assert ".authority-matrix-review-rows" in css.text
    assert ".candidate-b-default-promotion-status-panel" in css.text
    assert ".candidate-b-default-promotion-status-grid" in css.text
    assert ".candidate-b-final-proof-status-card" in css.text
    assert ".candidate-b-final-proof-status-form" in css.text
    assert ".candidate-b-final-proof-status-form textarea" in css.text
    assert ".candidate-b-final-proof-status-grid" in css.text
    assert ".candidate-b-default-promotion-status-rows" in css.text
    assert ".mockup-activation-readiness-panel" in css.text
    assert ".mockup-activation-readiness-grid" in css.text
    assert ".mockup-activation-journey-rows" in css.text
    assert ".package-supersession-preview-panel" in css.text
    assert ".package-supersession-preview-grid" in css.text
    assert ".package-supersession-preview-rows" in css.text
    assert ".replacement-package-set-authority-panel" in css.text
    assert ".replacement-package-set-authority-grid" in css.text
    assert ".replacement-package-set-authority-rows" in css.text
    assert ".package-supersession-commit-panel" in css.text
    assert ".package-supersession-commit-grid" in css.text
    assert ".package-supersession-commit-rows" in css.text
    assert ".replacement-package-artifact-manifest-panel" in css.text
    assert ".replacement-package-artifact-manifest-grid" in css.text
    assert ".replacement-package-artifact-manifest-rows" in css.text
    assert ".replacement-package-namespace-panel" in css.text
    assert ".replacement-package-namespace-grid" in css.text
    assert ".replacement-package-namespace-rows" in css.text
    assert ".layer3-e2e-governance-lifecycle-panel" in css.text
    assert ".layer3-e2e-governance-lifecycle-rows" in css.text
    assert ".downstream-access-lifecycle-dashboard-panel" in css.text
    assert ".downstream-access-lifecycle-rows" in css.text
    assert "/handoff/export/download/provider-public-url/prepare" in js.text
    assert "/handoff/export/download/provider-public-url/status/" in js.text
    assert "/handoff/export/download/provider-public-url/revoke" in js.text
    assert "/handoff/export/download/provider-public-url/use" in js.text
    assert "redacted use decision recorded without raw URL exposure" in js.text
    assert "/handoff/export/download/provider-public-url/deliver" not in js.text
    assert "provider-public-url-deliver" not in js.text
    assert "LAYER3_PROVIDER_PUBLIC" not in js.text
    assert "function stateActionContractSignature" in js.text
    assert "state_action_contract_signature: stateActionContractSignature(State.sessionSummary)" in js.text
    assert "state_action_contract_signature: stateActionContractSignature()" in js.text
    assert "anchor.state_action_contract_signature !== currentContract" in js.text
    assert "draft.state_action_contract_signature !== currentContract" in js.text
    assert "isSharedThemePreference" in js.text
    assert "value === 'workbench'" in js.text
    assert "value === 'workbench' || value === LAYER3_MOCKUP_WORKBENCH_THEME" in js.text
    assert "localStorage.removeItem(LAYER3_THEME_STORAGE_KEY)" in js.text
    assert "localStorage.removeItem(THEME_STORAGE_KEY)" in js.text
    assert "localStorage, LAYER3_SESSION_RECOVERY_STORAGE_KEY" in js.text
    assert "sessionStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY" in js.text
    assert "browser_restore_only_server_revalidated_on_commit" in js.text
    assert "async function recoverSessionFromStorage" in js.text
    assert "State.sessionSummary = summary" in js.text
    assert "restoreGateBDraftSnapshot" in js.text
    assert "client_request_id: gateBRequestId()" in js.text
    assert "State.gateB?.session_id && State.gateC?.authority_rail?.typing_status === 'committed'" not in js.text
    assert "localStorage, LAYER3_GATE_B_DRAFT_STORAGE_KEY" not in js.text
    assert "navigateToStep" in js.text
    assert "scrollIntoView" in js.text
    assert "renderSublayerMap" in js.text
    assert "selectedSourceClassLabels" in js.text
    assert "RAW_MIXED_MATERIALIZE_REQUEST_SCHEMA_ID = 'layer3.raw_mixed_corpus_materialize_request.v1'" in js.text
    assert "RAW_MIXED_MATERIALIZE_MODE = 'raw_mixed_existing_source_materialization_entry'" in js.text
    assert "rawMixedMaterializationPayload" in js.text
    assert "postJson('/source/mixed-corpus/materialize'" in js.text
    assert "materializedSourceIdsVisible" in js.text
    assert "selectedDatasetVersionIds" in js.text
    assert "selectedApsContentDocumentIds" in js.text
    assert "postJson('/material-preview'" in js.text
    assert "dataset_version_ids: datasetVersionIds" in js.text
    assert "aps_content_document_ids: apsContentDocumentIds" in js.text
    assert "getJson('/dataset-version-candidates')" in js.text
    assert "getJson('/aps-content-document-candidates')" in js.text
    assert "getJson('/aps-refused-artifact-traces')" in js.text
    assert "loadApsRefusedArtifactTraces" in js.text
    assert "renderSourceFamilySummary" in js.text
    assert "function sourceIntakeRenderedControls" in js.text
    assert "{ id: 'source-intake-rendered-controls', key: 'source_intake'" in js.text
    assert "step.key !== 'source_intake'" in js.text
    assert "pendingUpload: false" in js.text
    assert "Upload already in progress" in js.text
    assert "Inventory refresh failed" in js.text
    assert "source-intake-ui-" in js.text
    assert "source/intake/upload" in js.text
    assert "source/intake/inventory?limit=10" in js.text
    assert "sourceIntakeJson" in js.text
    assert "sourceIntakeGateBPayload" in js.text
    assert "source_intake_gate_b_rendered_admission" in js.text
    assert "detail?.error_code" in js.text
    assert "Commit Preview To Gate B" in js.text
    assert "source-intake-gate-b-submit" in js.text
    assert "not_admitted_or_deferred_families" in js.text
    assert "trace_detail" in js.text
    assert "source-family-trace" in js.text
    assert "Parser-level refused artifacts" in js.text
    assert "trace.materialization_state" in js.text
    assert "trace.admission_state" in js.text
    assert "unsupported-material-trace" in js.text
    assert "unsupported_material" in js.text
    assert "renderMaterialTrace" in js.text
    assert "source_trace" in js.text
    assert "content_units_ref" in js.text
    assert ".material-trace-card" in css.text
    assert "User Natural Language Query Input" in js.text
    assert "ledger-chip-field" in js.text
    assert "diagram-chip" in js.text
    assert "plane-arrow-process" in js.text
    assert "plane-bracket" in js.text
    assert "Sublayer 3A" in js.text
    assert "Sublayer 3B" in js.text
    assert "Sublayer 3C" in js.text
    assert "sessionSublayerState" in js.text
    assert "sublayer_visualization" in js.text
    assert "currentMaterialObjects" in js.text
    assert "currentTypingObjects" in js.text
    assert "element.disabled = false" in js.text
    assert "postJson('/gate-b/decision'" in js.text
    assert "postJson('/gate-c/preview'" in js.text
    assert "postJson('/plan/preview'" in js.text
    assert "postJson('/plan/revise'" in js.text
    assert "postJson('/plan/approve'" in js.text
    assert "postJson('/execution/select'" in js.text
    assert "postJson('/execution/start'" in js.text
    assert "postJson('/package/review/preview'" in js.text
    assert "getJson(`/session/${encodeURIComponent(sessionId)}`)" in js.text
    assert "postJson('/execution/result/status'" in js.text
    assert "postJson('/execution/result/review'" in js.text
    assert "associatedCohortProjection" in js.text
    assert "associatedCohortReviewedOutputItems" in js.text
    assert "cohort_result_review_ui_review_ready" in js.text
    assert "cohort_result_review_ui_recorded" in js.text
    assert "ASSOCIATED_COHORT_SOURCE_GATE = '78_COHORT_FREEZE'" in js.text
    assert "ASSOCIATED_COHORT_METHOD = 'descriptive_summary'" in js.text
    assert "payload.reviewed_output_items = reviewedOutputItems" in js.text
    assert "postJson('/package/review/commit'" in js.text
    assert "postJson('/package/review/submit'" in js.text
    assert "PACKAGE_SUPERSESSION_COMMIT_RENDERED_MODE = 'rendered_package_supersession_commit_control'" in js.text
    assert (
        "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_RENDERED_MODE = "
        "'rendered_source_directory_package_supersession_commit_control'"
    ) in js.text
    assert "SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_PATH" in js.text
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_PATH" in js.text
    assert "PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION = 'commit_package_supersession'" in js.text
    assert "REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_RENDERED_MODE = 'rendered_replacement_package_artifact_manifest_control'" in js.text
    assert (
        "REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_OPERATOR_DECISION = "
        "'record_replacement_package_artifact_manifest_from_authority'"
    ) in js.text
    assert "REPLACEMENT_PACKAGE_NAMESPACE_RENDERED_MODE = 'rendered_replacement_package_namespace_control'" in js.text
    assert "REPLACEMENT_PACKAGE_NAMESPACE_RESPONSE_AUTHORITY = 'State.replacementPackageNamespace'" in js.text
    assert "REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION = 'record_replacement_package_namespace'" in js.text
    assert "function stableHash" in js.text
    assert "window.crypto.subtle.digest('SHA-256'" in js.text
    assert "function packageSupersessionCommitPayload" in js.text
    assert "State.packageSupersessionCommit = await postJson(" in js.text
    assert "'/package/supersession/commit'" in js.text
    assert "function replacementPackageArtifactManifestPayload" in js.text
    assert "State.replacementPackageArtifactManifest = await postJson(" in js.text
    assert "'/package/replacement-artifact/manifest/record-from-authority'" in js.text
    assert "function replacementPackageNamespacePayload" in js.text
    assert "State.replacementPackageNamespace = await postJson(" in js.text
    assert "'/package/replacement-namespace/record'" in js.text
    assert "package_supersession_commit_ready" in js.text
    assert "replacement_package_artifact_manifest_ready" in js.text
    assert "replacement_package_namespace_ready" in js.text
    assert "renderPackageSupersessionCommitPanel()" in js.text
    assert "renderReplacementPackageArtifactManifestPanel()" in js.text
    assert "renderReplacementPackageNamespacePanel()" in js.text
    assert "'/handoff/export/prepare'" in js.text
    assert "postJson('/handoff/aps/dispatch'" in js.text
    assert "'/handoff/export/download/prepare'" in js.text
    assert "'/handoff/export/download/deliver'" in js.text
    assert "'/handoff/export/download/signed-reference/generate'" in js.text
    assert "handoff/export/download/signed-reference/use" in js.text
    assert "same_origin_signed_delivery_reference" in js.text
    assert "external_export_download_signed_reference_ui_ready" in js.text
    assert "provider_signed_url" in js.text
    assert "durable_token_state" in js.text
    assert "function externalExportDownloadDeliveryUiAdmitted" in js.text
    assert "function isQualitativeApsExternalExportDownloadState" in js.text
    assert "if (isAssociatedCohortExternalExportDownloadState(external)) return false;" in js.text
    assert "external.package_construction_source_gate === QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE" in js.text
    assert "serverExternalExportDownloadDeliveryUiState(external)" in js.text
    assert "function qualitativeApsDeliveryUiState" in js.text
    assert "qualitativeApsDeliveryUiState(external)" in js.text
    assert "SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = 'layer3.source_intake_external_export_download_prepare.v1'" in js.text
    assert "SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = 'layer3.source_intake_external_export_download_delivery.v1'" in js.text
    assert "function isSourceIntakeExternalExportDownloadState" in js.text
    assert "function sourceIntakeDeliveryUiState" in js.text
    assert "source_intake_external_export_download_delivery_ui_ready" in js.text
    assert "sourceDirectoryIngestionRenderedControls" in js.text
    assert "SOURCE_DIRECTORY_INGESTION_SCAN_PATH" in js.text
    assert "SOURCE_DIRECTORY_INGESTION_STATUS_PATH_PREFIX" in js.text
    assert "scan_server_configured_operator_directory" in js.text
    assert "server_configured_operator_directory_text_table_ingestion" in js.text
    assert "server_configured_operator_directory_text_table_source_family" in js.text
    assert "postJson(SOURCE_DIRECTORY_INGESTION_SCAN_PATH" in js.text
    assert "getJson(`${SOURCE_DIRECTORY_INGESTION_STATUS_PATH_PREFIX}" in js.text
    signed_reference_start = js.text.find("function canGenerateExternalExportDownloadSignedReference")
    provider_signed_url_start = js.text.find("function canPrepareProviderPrivateSignedUrl")
    assert signed_reference_start != -1
    assert provider_signed_url_start != -1
    signed_reference_gate = js.text[signed_reference_start:provider_signed_url_start]
    assert "!isSourceIntakeExternalExportDownloadState(external)" not in signed_reference_gate
    provider_signed_url_gate_end = js.text.find("function canInspectProviderPrivateSignedUrl")
    assert provider_signed_url_gate_end != -1
    provider_signed_url_gate = js.text[provider_signed_url_start:provider_signed_url_gate_end]
    assert "&& !isSourceIntakeExternalExportDownloadState(external)" not in provider_signed_url_gate
    assert (
        "&& (!isSourceIntakeExternalExportDownloadState(external) || State.externalExportDownloadSignedReferenceUse)"
        in provider_signed_url_gate
    )
    assert "State.externalExportDownloadSignedReferenceUse" in provider_signed_url_gate
    assert "signedReferenceReceiptId: res.headers.get('x-layer3-signed-reference-receipt-id')" in js.text
    assert "signed_reference_receipt_id: State.externalExportDownloadSignedReferenceUse?.signedReferenceReceiptId" in js.text
    assert "serverExternalExportDownloadDeliveryUiState(external)" in js.text
    assert "return false;" in js.text
    assert "if (isQualitativeApsExternalExportDownloadState(external))" in js.text
    assert "function deliveryUiStateAdmitted" in js.text
    assert "deliveryUiStateAdmitted(deliveryUi" in js.text
    assert "'associated_cohort_external_export_download_delivery_ui_ready'" in js.text
    assert "external_export_download_delivery_ui_unavailable" in js.text
    assert "external_export_download_signed_reference_ui_blocked" in js.text
    assert "serverExternalExportDownloadDeliveryUiState(external)" in js.text
    assert "source_artifact_size_bytes ?? summary.source_artifact_size_bytes" not in js.text
    assert "deliveryUi.browser_managed_same_origin_attachment_enabled === true" in js.text
    assert "deliveryUi.public_url_enabled === false" in js.text
    assert ".blob()" not in js.text
    assert "SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID" in js.text
    assert "SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_SCHEMA_ID" in js.text
    assert "SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH" in js.text
    assert "function sourceDirectoryHybridExternalExportDownloadDeliveryPayload" in js.text
    assert "inspectSourceDirectoryHybridExternalExportDownloadDelivery" in js.text
    assert "submitSourceDirectoryHybridExternalExportDownloadDelivery" in js.text
    assert "deliver_source_directory_hybrid_external_export_download" in js.text
    assert (
        "postJson(\n            SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH"
        in js_text
    )
    assert (
        "submitAttachmentForm(\n            SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH"
        in js_text
    )
    assert "operator_view_mode: 'status_only'" in js.text
    assert "operator_decision: elements.resultReviewDecision.value" in js.text
    assert "operator_decision: elements.packageReviewSubmitDecision.value" in js.text
    assert "function packageReviewPreviewHash" in js.text
    assert "function packageConstructionBasisHash" in js.text
    assert "package_review_preview_hash: previewHash" in js.text
    assert "payload.construction_basis_hash = constructionBasisHash" in js.text
    assert "submit.result_review_record_ref || construction.result_review_record_ref" in js.text
    assert "handoffState === 'handoff_export_prepared'" in js.text
    assert "state: 'aps_handoff_ready'" in js.text
    assert "apsHandoffDispatchState()?.available === true" in js.text
    assert "operator_decision: elements.handoffExportPrepareDecision.value" in js.text
    assert "operator_decision: 'dispatch_aps_handoff'" in js.text
    assert "operator_decision: 'prepare_external_export_download'" in js.text
    assert "operator_decision: 'deliver_external_export_download'" in js.text
    assert "function externalExportDownloadSignedReferencePayload" in js.text
    review_start = js.text.find("function resultReviewPayload")
    review_end = js.text.find("function packageReviewPreviewPayload")
    package_start = js.text.find("function packageReviewSubmitPayload")
    source_directory_handoff_start = js.text.find("function sourceDirectoryQualitativePackageReviewBasePayload")
    handoff_start = js.text.find("function handoffExportPreparePayload")
    aps_start = js.text.find("function apsHandoffDispatchPayload")
    external_start = js.text.find("function externalExportDownloadPreparePayload")
    delivery_start = js.text.find("function externalExportDownloadDeliveryPayload")
    refresh_start = js.text.find("async function refreshSessionSummary")
    assert review_start != -1
    assert review_end != -1
    assert package_start != -1
    assert source_directory_handoff_start != -1
    assert handoff_start != -1
    assert aps_start != -1
    assert external_start != -1
    assert delivery_start != -1
    assert refresh_start != -1
    result_review_slice = js.text[review_start:review_end]
    package_submit_slice = js.text[package_start:source_directory_handoff_start]
    handoff_prepare_slice = js.text[handoff_start:aps_start]
    aps_dispatch_slice = js.text[aps_start:external_start]
    external_prepare_slice = js.text[external_start:delivery_start]
    external_delivery_slice = js.text[delivery_start:refresh_start]
    assert "payload.reviewed_output_items = reviewedOutputItems" in result_review_slice
    assert "package" not in result_review_slice
    assert "handoff" not in result_review_slice
    assert "rerun" not in result_review_slice
    assert "pass_run_ids" not in result_review_slice
    assert "artifact_manifest" not in result_review_slice
    assert "handoff_target" not in package_submit_slice
    assert "export_mode" not in package_submit_slice
    assert "payload_refs: packagePayloadRefs()" in package_submit_slice
    assert "payload.construction_basis_hash = constructionBasisHash" in package_submit_slice
    assert "authority.analysisRunId && !qualitativeAps" in package_submit_slice
    assert "handoff_target: 'internal_export_envelope'" in handoff_prepare_slice
    assert "export_mode: 'prepare_only'" in handoff_prepare_slice
    assert "payload_refs: packagePayloadRefs()" in handoff_prepare_slice
    for forbidden in (
        "aps_handoff",
        "dispatch",
        "send",
        "external_export",
        "download",
        "connector_run_id",
        "runtime_db_write",
        "analysis_artifact",
        "artifact_manifest",
        "create_package",
        "rebuild_package",
        "package_payload",
        "rewrite_output",
    ):
        assert forbidden not in handoff_prepare_slice
    assert "handoff_target: 'internal_export_envelope'" in aps_dispatch_slice
    assert "export_mode: 'prepare_only'" in aps_dispatch_slice
    assert "aps_handoff_target: 'aps_evidence_bundle'" in aps_dispatch_slice
    assert "dispatch_mode: 'server_side_aps_handoff'" in aps_dispatch_slice
    assert "operator_decision: 'dispatch_aps_handoff'" in aps_dispatch_slice
    assert "prepare_record_ref: handoff.prepare_record_ref" in aps_dispatch_slice
    assert "handoff_export_envelope_ref: handoffExportEnvelopeRef(handoff)" in aps_dispatch_slice
    assert "package_kinds: packageKindsFromState()" in aps_dispatch_slice
    for forbidden in (
        "external_export",
        "external_target",
        "download",
        "download_url",
        "destination",
        "destination_selector",
        "connector_run_id",
        "connector_dispatch",
        "dispatch",
        "send",
        "runtime_db_write",
        "analysis_artifact",
        "artifact_manifest",
        "create_package",
        "rebuild_package",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "edited_findings",
        "result_review_amendment",
        "package_review_amendment",
        "rerun",
        "retry",
        "recover",
        "cancel",
        "selected_pass_ids",
        "pass_run_ids",
        "new_analysis_plan",
        "plan_revision",
        "source_expansion",
        "local_upload",
        "local_directory",
        "schema_migration",
        "expected_package_kinds",
    ):
        assert f"{forbidden}:" not in aps_dispatch_slice
    assert "handoff_target: external.handoff_target || 'internal_export_envelope'" in external_prepare_slice
    assert "export_mode: external.export_mode || 'prepare_only'" in external_prepare_slice
    assert "aps_handoff_target: external.aps_handoff_target || aps.aps_handoff_target || 'aps_evidence_bundle'" in external_prepare_slice
    assert "dispatch_mode: external.dispatch_mode || aps.dispatch_mode || 'server_side_aps_handoff'" in external_prepare_slice
    assert "export_download_target: external.export_download_target || 'aps_evidence_bundle_download_reference'" in external_prepare_slice
    assert "download_mode: external.download_mode || 'reference_only_prepare'" in external_prepare_slice
    assert "operator_decision: 'prepare_external_export_download'" in external_prepare_slice
    assert "aps_bundle_hash = external.source_artifact_hash" in external_prepare_slice
    assert "aps_bundle_size_bytes = external.source_artifact_size_bytes" in external_prepare_slice
    for forbidden in (
        "download_url",
        "public_url",
        "signed_url",
        "stream_file",
        "browser_download",
        "connector_run_id",
        "connector_dispatch",
        "destination",
        "destination_id",
        "external_target",
        "generic_dispatch",
        "runtime_db_write",
        "analysis_artifact",
        "artifact_manifest",
        "create_package",
        "rebuild_package",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "edited_findings",
        "result_review_amendment",
        "package_review_amendment",
        "handoff_export_amendment",
        "aps_handoff_amendment",
        "rerun",
        "retry",
        "recover",
        "cancel",
        "selected_pass_ids",
        "pass_run_ids",
        "new_analysis_plan",
        "plan_revision",
        "source_expansion",
        "local_upload",
        "local_directory",
        "schema_migration",
    ):
        assert f"{forbidden}:" not in external_prepare_slice
    assert "external_export_download_record_ref: external.external_export_download_record_ref" in external_delivery_slice
    assert "export_download_descriptor_ref: external.export_download_descriptor_ref" in external_delivery_slice
    assert "external_export_download_state: externalExportDownloadStateName(external)" in external_delivery_slice
    assert "delivery_mode: 'same_origin_artifact_stream'" in external_delivery_slice
    assert "operator_decision: 'deliver_external_export_download'" in external_delivery_slice
    assert "delivery_ui:" not in external_delivery_slice
    for forbidden in (
        "download_url",
        "download_token",
        "public_url",
        "signed_url",
        "local_file_path",
        "connector_run_id",
        "connector_dispatch",
        "destination",
        "destination_id",
        "external_target",
        "generic_dispatch",
        "runtime_db_write",
        "analysis_artifact",
        "artifact_manifest",
        "create_package",
        "rebuild_package",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "edited_findings",
        "result_review_amendment",
        "package_review_amendment",
        "handoff_export_amendment",
        "aps_handoff_amendment",
        "rerun",
        "retry",
        "recover",
        "cancel",
        "selected_pass_ids",
        "pass_run_ids",
        "new_analysis_plan",
        "plan_revision",
        "source_expansion",
        "local_upload",
        "local_directory",
        "schema_migration",
    ):
        assert f"{forbidden}:" not in external_delivery_slice
    assert "planRevisionPending" in js.text
    assert "State.planRevisionPending = true" in js.text
    signed_start = js.text.find("function externalExportDownloadSignedReferencePayload")
    signed_end = js.text.find("async function refreshSessionSummary")
    assert signed_start != -1
    assert signed_end != -1
    signed_slice = js.text[signed_start:signed_end]
    assert "externalExportDownloadDeliveryPayload(authority)" in signed_slice
    assert "signed_reference_token" in signed_slice
    assert "download_url:" not in signed_slice
    assert "public_url:" not in signed_slice
    assert "signed_url:" not in signed_slice
    assert "connector_run_id:" not in signed_slice
    assert "destination:" not in signed_slice
    assert "runtime_db_write:" not in signed_slice
    assert "schema_migration:" not in signed_slice


def test_layer3_mixed_source_rendered_handoff_prepare_uses_material_authority() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    assert js.status_code == 200
    js_text = js.text.replace("\r\n", "\n")

    authority_slice = _js_slice(
        js_text,
        "function mixedSourceHandoffExportPrepareAuthorityPacket",
        "function isMixedSourceHandoffExportPrepareAuthority",
    )
    gate_slice = _js_slice(
        js_text,
        "function canSubmitHandoffExportPrepare",
        "function canSubmitApsHandoffDispatch",
    )
    payload_slice = _js_slice(
        js_text,
        "function mixedSourceHandoffExportPreparePayload",
        "function apsHandoffDispatchPayload",
    )
    panel_slice = _js_slice(
        js_text,
        "function handoffExportPanelState",
        "function apsHandoffPanelState",
    )
    submit_slice = _js_slice(
        js_text,
        "async function submitHandoffExportPrepare",
        "async function submitApsHandoffDispatch",
    )
    operation_dock_slice = _js_slice(
        js_text,
        "function operationDockStatus",
        "function renderOperationDockSummary",
    )
    controls_slice = _js_slice(
        js_text,
        "function setGateControls",
        "function renderAll",
    )

    for required in (
        "MIXED_SOURCE_HANDOFF_EXPORT_PREPARE_SCHEMA_ID",
        "MIXED_SOURCE_HANDOFF_EXPORT_TARGET",
        "MIXED_SOURCE_HANDOFF_EXPORT_MODE",
        "handoff.package_family === 'mixed_dataset_document'",
        "handoff.handoff_export_prepare_schema_id === MIXED_SOURCE_HANDOFF_EXPORT_PREPARE_SCHEMA_ID",
        "packet.package_review_state !== 'package_review_approved'",
        "packet.handoff_target !== MIXED_SOURCE_HANDOFF_EXPORT_TARGET",
        "packet.export_mode !== MIXED_SOURCE_HANDOFF_EXPORT_MODE",
        "exactPackageKinds(packageKinds)",
    ):
        assert required in authority_slice or required in js_text
    assert "packageKindsFromState()" not in authority_slice
    assert "const mixedSourcePacket = mixedSourceHandoffExportPrepareAuthorityPacket()" in gate_slice
    assert gate_slice.find("const mixedSourcePacket = mixedSourceHandoffExportPrepareAuthorityPacket()") < gate_slice.find("handoff.available === true")
    assert "mixedSourceMode" in submit_slice
    assert "mixedSourceHandoffExportPreparePayload()" in submit_slice
    assert "Mixed-source handoff/export preparation recorded." in submit_slice
    assert "const mixedSourceHandoffExportControlsEnabled = Boolean(mixedSourceHandoffExportPrepareAuthorityPacket())" in controls_slice
    assert "|| mixedSourceHandoffExportControlsEnabled" in controls_slice
    assert "elements.handoffExportPrepareDecision.disabled = !handoffExportControlsEnabled" in controls_slice
    assert "elements.handoffExportPrepareNotes.disabled = !handoffExportControlsEnabled" in controls_slice
    assert "rendered_mixed_source_handoff_export_prepare_control" in panel_slice
    assert "State.sessionSummary.handoff_export_prepare material authority" in panel_slice
    assert "mixed_source_handoff_export_material_authority_ready" in panel_slice
    assert "material authority ready" in operation_dock_slice
    assert operation_dock_slice.find("mixedSourceHandoffExportPrepareAuthorityPacket()") < operation_dock_slice.find("State.sessionSummary?.handoff_export_prepare?.available === true")
    for required in (
        "material_preview_id: packet.material_preview_id",
        "material_preview_hash: packet.material_preview_hash",
        "package_review_preview_hash: packet.package_review_preview_hash",
        "contract_hash: packet.contract_hash",
        "construction_basis_hash: packet.construction_basis_hash",
        "reconciliation_record_id: packet.reconciliation_record_id",
        "output_package_ids: packet.output_package_ids",
        "payload_hashes: packet.payload_hashes",
        "package_review_submit_record_ref: packet.package_review_submit_record_ref",
        "package_review_state: packet.package_review_state",
        "handoff_target: MIXED_SOURCE_HANDOFF_EXPORT_TARGET",
        "export_mode: MIXED_SOURCE_HANDOFF_EXPORT_MODE",
        "expected_package_kinds: packet.package_kinds",
    ):
        assert required in payload_slice
    for forbidden in (
        "analysis_plan_id:",
        "pass_run_id:",
        "preview_id:",
        "preview_hash:",
        "result_review_record_ref:",
        "payload_refs:",
        "provider_public_url",
        "connector_run_id",
        "destination",
        "local_file_path",
        "package_payload",
        "schema_migration",
        "source_expansion",
    ):
        assert f"\n        {forbidden}" not in payload_slice


def test_layer3_mixed_source_rendered_aps_and_readiness_use_material_authority() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    assert js.status_code == 200
    js_text = js.text.replace("\r\n", "\n")

    aps_authority_slice = _js_slice(
        js_text,
        "function mixedSourceApsHandoffDispatchAuthorityPacket",
        "function mixedSourceExternalExportDownloadReadinessAuthorityPacket",
    )
    readiness_authority_slice = _js_slice(
        js_text,
        "function mixedSourceExternalExportDownloadReadinessAuthorityPacket",
        "function mixedSourceExternalExportDownloadReadinessState",
    )
    aps_state_slice = _js_slice(
        js_text,
        "function apsHandoffDispatchState",
        "function apsHandoffStateName",
    )
    aps_gate_slice = _js_slice(
        js_text,
        "function canSubmitApsHandoffDispatch",
        "function canSubmitExternalExportDownloadPrepare",
    )
    readiness_gate_slice = _js_slice(
        js_text,
        "function canSubmitExternalExportDownloadPrepare",
        "function canSubmitExternalExportDownloadDelivery",
    )
    aps_payload_slice = _js_slice(
        js_text,
        "function mixedSourceApsHandoffDispatchPayload",
        "function mixedSourceExternalExportDownloadReadinessPayload",
    )
    readiness_payload_slice = _js_slice(
        js_text,
        "function mixedSourceExternalExportDownloadReadinessPayload",
        "function externalExportDownloadSignedReferencePayload",
    )
    aps_panel_slice = _js_slice(
        js_text,
        "function apsHandoffPanelState",
        "function externalExportDownloadPanelState",
    )
    readiness_panel_slice = _js_slice(
        js_text,
        "function externalExportDownloadPanelState",
        "function externalExportDownloadDeliveryPanelState",
    )
    controls_slice = _js_slice(
        js_text,
        "function setGateControls",
        "function renderAll",
    )
    aps_submit_slice = _js_slice(
        js_text,
        "async function submitApsHandoffDispatch",
        "async function submitExternalExportDownloadPrepare",
    )
    readiness_submit_slice = _js_slice(
        js_text,
        "async function submitExternalExportDownloadPrepare",
        "async function submitExternalExportDownloadDelivery",
    )

    for required in (
        "MIXED_SOURCE_APS_HANDOFF_OPERATOR_DECISION",
        "packet.handoff_export_state !== 'handoff_export_prepared'",
        "dispatchPacket.prepare_record_ref",
        "dispatchPacket.handoff_export_envelope_ref",
        "downstream_unavailable: handoff.downstream_unavailable",
        "aps_handoff_target: MIXED_SOURCE_APS_HANDOFF_TARGET",
        "dispatch_mode: MIXED_SOURCE_APS_HANDOFF_MODE",
    ):
        assert required in aps_authority_slice or required in js_text
    for required in (
        "readinessPacket.aps_handoff_record_ref",
        "readinessPacket.aps_handoff_state !== 'aps_handoff_dispatched'",
        "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_READINESS_OPERATOR_DECISION",
    ):
        assert required in readiness_authority_slice or required in js_text

    assert "const mixedSourcePacket = mixedSourceApsHandoffDispatchAuthorityPacket()" in aps_state_slice
    assert "const handoff = handoffExportPrepareState()" in aps_state_slice
    assert "downstream_unavailable: mixedSourcePacket.downstream_unavailable" in aps_state_slice
    assert "rendered_mixed_source_aps_handoff_dispatch_control" in aps_panel_slice
    assert "State.handoffExportPrepare mixed-source material authority" in aps_panel_slice
    assert "mixed_source_aps_handoff_ready" in aps_panel_slice
    assert "MIXED_SOURCE_APS_HANDOFF_OPERATOR_DECISION" in aps_panel_slice
    assert "const mixedSourcePacket = mixedSourceApsHandoffDispatchAuthorityPacket()" in aps_gate_slice
    assert aps_gate_slice.find("const mixedSourcePacket = mixedSourceApsHandoffDispatchAuthorityPacket()") < aps_gate_slice.find("hasResultAuthorityIdentity(authority)")
    assert "mixedSourceApsHandoffDispatchPayload()" in js_text
    assert "Mixed-source APS handoff dispatch recorded." in aps_submit_slice

    assert "const mixedSourcePacket = mixedSourceExternalExportDownloadReadinessAuthorityPacket()" in readiness_gate_slice
    assert readiness_gate_slice.find("const mixedSourcePacket = mixedSourceExternalExportDownloadReadinessAuthorityPacket()") < readiness_gate_slice.find("isSourceDirectoryQualitativeHandoffExportPrepareState(handoff)")
    assert "mixedSourceExternalExportDownloadReadinessState()" in readiness_gate_slice
    assert "rendered_mixed_source_external_export_download_readiness_control" in readiness_panel_slice
    assert "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_READINESS_PATH" in readiness_panel_slice
    assert "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_READINESS_OPERATOR_DECISION" in readiness_panel_slice
    assert "mixed_source_external_export_download_readiness_ready" in readiness_panel_slice
    assert "|| mixedSourceExternalExportDownloadReadinessAuthorityPacket()" in controls_slice
    assert "&& !mixedSourceExternalExportDownloadReadinessState()" in controls_slice
    assert "mixedSourceExternalExportDownloadReadinessPayload()" in js_text
    assert "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_READINESS_PATH" in readiness_submit_slice
    assert "Mixed-source external export/download readiness recorded." in readiness_submit_slice
    assert "&& !recordedMixedSourceExternalExportDownloadDelivery()" in js_text

    for required in (
        "material_preview_id: packet.material_preview_id",
        "material_preview_hash: packet.material_preview_hash",
        "package_review_preview_hash: packet.package_review_preview_hash",
        "contract_hash: packet.contract_hash",
        "construction_basis_hash: packet.construction_basis_hash",
        "reconciliation_record_id: packet.reconciliation_record_id",
        "output_package_ids: packet.output_package_ids",
        "payload_hashes: packet.payload_hashes",
        "package_review_submit_record_ref: packet.package_review_submit_record_ref",
        "package_review_state: packet.package_review_state",
        "prepare_record_ref: packet.prepare_record_ref",
        "handoff_export_state: packet.handoff_export_state",
        "handoff_export_envelope_ref: packet.handoff_export_envelope_ref",
        "handoff_target: MIXED_SOURCE_HANDOFF_EXPORT_TARGET",
        "export_mode: MIXED_SOURCE_HANDOFF_EXPORT_MODE",
        "aps_handoff_target: MIXED_SOURCE_APS_HANDOFF_TARGET",
        "dispatch_mode: MIXED_SOURCE_APS_HANDOFF_MODE",
        "operator_decision: MIXED_SOURCE_APS_HANDOFF_OPERATOR_DECISION",
        "expected_package_kinds: packet.package_kinds",
    ):
        assert required in aps_payload_slice
    for required in (
        "aps_handoff_record_ref: packet.aps_handoff_record_ref",
        "aps_handoff_state: packet.aps_handoff_state",
        "operator_decision: MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_READINESS_OPERATOR_DECISION",
    ):
        assert required in readiness_payload_slice
    for forbidden in (
        "analysis_plan_id:",
        "pass_run_id:",
        "preview_id:",
        "preview_hash:",
        "result_review_record_ref:",
        "payload_refs:",
        "download_url:",
        "public_url:",
        "signed_url:",
        "connector_run_id:",
        "destination:",
        "local_file_path:",
        "package_payload:",
        "schema_migration:",
        "source_expansion:",
    ):
        assert f"\n        {forbidden}" not in aps_payload_slice
        assert f"\n        {forbidden}" not in readiness_payload_slice


def test_layer3_mixed_source_rendered_delivery_uses_p19_material_authority() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    assert js.status_code == 200
    js_text = js.text.replace("\r\n", "\n")

    authority_slice = _js_slice(
        js_text,
        "function mixedSourceExternalExportDownloadDeliveryAuthorityPacket",
        "function mixedSourceExternalExportDownloadDeliveryUiState",
    )
    ui_slice = _js_slice(
        js_text,
        "function mixedSourceExternalExportDownloadDeliveryUiState",
        "function mixedSourceExternalExportDownloadDeliveryUiAdmitted",
    )
    gate_slice = _js_slice(
        js_text,
        "function canSubmitExternalExportDownloadDelivery",
        "function isPackageActive",
    )
    payload_slice = _js_slice(
        js_text,
        "function mixedSourceExternalExportDownloadDeliveryPayload",
        "function externalExportDownloadDeliveryPayload",
    )
    delivery_state_slice = _js_slice(
        js_text,
        "function mixedSourceExternalExportDownloadDeliveryState",
        "function mixedSourceExternalExportDownloadDeliveryStateName",
    )
    panel_slice = _js_slice(
        js_text,
        "function externalExportDownloadDeliveryPanelState",
        "function externalExportDownloadSignedReferencePanelState",
    )
    signed_slice = _js_slice(
        js_text,
        "function externalExportDownloadSignedReferencePanelState",
        "function renderExternalExportDownloadSignedReferencePanel",
    )
    signed_render_slice = _js_slice(
        js_text,
        "function renderExternalExportDownloadSignedReferencePanel",
        "function sourceDirectoryHybridExternalExportDownloadDeliveryPayload",
    )
    submit_slice = _js_slice(
        js_text,
        "async function submitExternalExportDownloadDelivery",
        "async function prepareSourceDirectoryHybridAuthority",
    )
    controls_slice = _js_slice(
        js_text,
        "function setGateControls",
        "function renderAll",
    )
    attachment_slice = _js_slice(
        js_text,
        "function submitAttachmentForm",
        "function addEvent",
    )

    for required in (
        "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID",
        "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE",
        "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION",
        "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PACKAGE_KIND = 'review_facing'",
        "State.sessionSummary?.external_export_download_readiness",
        "readiness.package_family !== 'mixed_dataset_document'",
        "packet.handoff_target !== MIXED_SOURCE_HANDOFF_EXPORT_TARGET",
        "packet.export_mode !== MIXED_SOURCE_HANDOFF_EXPORT_MODE",
        "packet.aps_handoff_target !== MIXED_SOURCE_APS_HANDOFF_TARGET",
        "packet.dispatch_mode !== MIXED_SOURCE_APS_HANDOFF_MODE",
        "packet.external_export_download_readiness_state !== MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_READINESS_STATE",
        "packet.package_kind !== MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PACKAGE_KIND",
        "exactPackageKinds(packageKinds)",
    ):
        assert required in authority_slice or required in js_text
    assert "const mixedSourceReadiness = mixedSourceExternalExportDownloadReadinessState()" in gate_slice
    assert gate_slice.find("const mixedSourceReadiness = mixedSourceExternalExportDownloadReadinessState()") < gate_slice.find("isSourceDirectoryQualitativeExternalExportDownloadPrepareState(external)")
    assert "mixedSourceExternalExportDownloadDeliveryAuthorityPacket()" in gate_slice
    assert "mixedSourceExternalExportDownloadDeliveryUiAdmitted()" in gate_slice
    assert "mixed_source_external_export_download_delivery_ui_ready" in ui_slice
    assert "package_payload_rewrite_enabled: false" in ui_slice
    assert "schema_runtime_source_widening_enabled: false" in ui_slice
    assert "server_authority: 'State.sessionSummary.external_export_download_readiness'" in ui_slice
    assert (
        delivery_state_slice.find("State.sessionSummary?.external_export_download_delivery")
        < delivery_state_slice.find("State.externalExportDownloadDelivery")
    )
    assert "|| mixedSourceExternalExportDownloadDeliveryAuthorityPacket()" in controls_slice
    assert "rendered_mixed_source_external_export_download_delivery_control" in panel_slice
    assert "State.sessionSummary.external_export_download_readiness" in panel_slice
    assert "mixed_source_external_export_download_delivery_submitted" in panel_slice
    assert "mixed_source_external_export_download_delivered" in panel_slice
    assert "rendered_mixed_source_external_export_download_signed_reference_control" in signed_render_slice
    assert "mixed_source_external_export_download_signed_reference_ui_ready" in signed_slice
    assert "mixed_source_external_export_download_signed_reference_gate" in js_text
    assert "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_OPERATOR_DECISION" in js_text
    assert "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_USE_OPERATOR_DECISION" in js_text
    assert "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_SERVER_AUTHORITY" in js_text
    assert "mixedSourceExternalExportDownloadSignedReferenceAuthorityAdmitted" in signed_render_slice
    assert "provider_public_url_enabled: false" in js_text
    assert "provider_private_signed_url_enabled: false" in js_text
    assert "connector_dispatch_enabled: false" in js_text
    assert "body.operator_decision === MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION" in attachment_slice
    assert "MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID" in attachment_slice
    assert "const mixedSourceMode = Boolean(mixedSourceExternalExportDownloadDeliveryAuthorityPacket())" in submit_slice
    assert "mixedSourceExternalExportDownloadDeliveryPayload()" in submit_slice
    assert "!mixedSourceMode && sourceDirectoryMode" in panel_slice
    assert "!mixedSourceMode && sourceDirectoryMode" in submit_slice
    assert "'/handoff/export/download/deliver'" in submit_slice
    assert "Mixed-source external export/download package submitted as browser-managed same-origin attachment." in submit_slice
    assert "&& !mixedSourceExternalExportDownloadReadinessState()" in controls_slice

    for required in (
        "material_preview_id: packet.material_preview_id",
        "material_preview_hash: packet.material_preview_hash",
        "package_review_preview_hash: packet.package_review_preview_hash",
        "contract_hash: packet.contract_hash",
        "construction_basis_hash: packet.construction_basis_hash",
        "reconciliation_record_id: packet.reconciliation_record_id",
        "output_package_id: packet.output_package_id",
        "package_kind: packet.package_kind",
        "package_payload_hash: packet.package_payload_hash",
        "package_review_submit_record_ref: packet.package_review_submit_record_ref",
        "package_review_state: packet.package_review_state",
        "prepare_record_ref: packet.prepare_record_ref",
        "handoff_export_state: packet.handoff_export_state",
        "handoff_export_envelope_ref: packet.handoff_export_envelope_ref",
        "handoff_target: MIXED_SOURCE_HANDOFF_EXPORT_TARGET",
        "export_mode: MIXED_SOURCE_HANDOFF_EXPORT_MODE",
        "aps_handoff_target: MIXED_SOURCE_APS_HANDOFF_TARGET",
        "dispatch_mode: MIXED_SOURCE_APS_HANDOFF_MODE",
        "aps_handoff_record_ref: packet.aps_handoff_record_ref",
        "aps_handoff_state: packet.aps_handoff_state",
        "external_export_download_readiness_record_ref: packet.external_export_download_readiness_record_ref",
        "external_export_download_readiness_ref: packet.external_export_download_readiness_ref",
        "external_export_download_readiness_state: MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_READINESS_STATE",
        "delivery_mode: MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_MODE",
        "operator_decision: MIXED_SOURCE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION",
        "expected_package_kinds: packet.package_kinds",
    ):
        assert required in payload_slice
    for forbidden in (
        "analysis_plan_id:",
        "pass_run_id:",
        "preview_id:",
        "preview_hash:",
        "result_review_record_ref:",
        "output_package_ids:",
        "package_kinds:",
        "payload_refs:",
        "payload_hashes:",
        "external_export_download_record_ref:",
        "export_download_descriptor_ref:",
        "external_export_download_state:",
        "export_download_target:",
        "download_mode:",
        "aps_output_package_id:",
        "aps_output_package_kind:",
        "aps_bundle_ref:",
        "aps_bundle_id:",
        "aps_schema_id:",
        "download_url:",
        "public_url:",
        "signed_url:",
        "connector_run_id:",
        "destination:",
        "local_file_path:",
        "package_payload:",
        "schema_migration:",
        "source_expansion:",
    ):
        assert f"\n        {forbidden}" not in payload_slice


def test_layer3_mixed_source_product_authority_checkpoint_is_read_only() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    assert js.status_code == 200
    js_text = js.text.replace("\r\n", "\n")

    checkpoint_slice = _js_slice(
        js_text,
        "function mixedSourceProductAuthorityCheckpoint",
        "function packageLifecycleOutputRows",
    )
    renderer_slice = _js_slice(
        js_text,
        "function renderMixedSourceProductAuthorityCheckpointRows",
        "function handoffExportEnvelopeRef",
    )
    dashboard_slice = _js_slice(
        js_text,
        "function renderLayer3E2EGovernanceLifecycleDashboardPanel",
        "function handoffExportPanelState",
    )

    for required in (
        "MIXED_SOURCE_PRODUCT_AUTHORITY_CHECKPOINT_MODE",
        "MIXED_SOURCE_PRODUCT_AUTHORITY_CHECKPOINT_USE_CASE",
        "MIXED_SOURCE_PRODUCT_AUTHORITY_CHECKPOINT_RESPONSE_AUTHORITY",
        "mixedSourceApsHandoffDispatchAuthorityPacket()",
        "mixedSourceExternalExportDownloadReadinessAuthorityPacket()",
        "mixedSourceExternalExportDownloadReadinessState()",
        "mixedSourceExternalExportDownloadDeliveryAuthorityPacket()",
        "mixedSourceExternalExportDownloadSignedReferenceUiState()",
        "mixedSourceExternalExportDownloadSignedReferenceAuthorityAdmitted(p22)",
        "mixed_source_product_authority_checkpoint_ready",
        "mixed_source_product_authority_checkpoint_blocked",
        "steps.every((step) => step.ready === true)",
        "real_export_dispatch_admitted: false",
        "provider_public_url_enabled: false",
        "provider_private_signed_url_enabled: false",
        "connector_dispatch_enabled: false",
        "destination_write_enabled: false",
        "local_outbox_enabled: false",
        "package_payload_rewrite_enabled: false",
        "schema_runtime_source_widening_enabled: false",
        "production_readiness_claimed: false",
    ):
        assert required in checkpoint_slice

    for required in (
        "mixed-source-product-authority-checkpoint",
        'data-rendered-mode="${escapeHtml(productAuthorityCheckpoint.mode)}"',
        'data-product-authority-checkpoint-state="${escapeHtml(productAuthorityCheckpoint.state)}"',
        'data-production-readiness-claimed="false"',
        "renderMixedSourceProductAuthorityCheckpointRows(productAuthorityCheckpoint)",
        "renderMixedSourceProductAuthorityCheckpointBoundaries(productAuthorityCheckpoint)",
    ):
        assert required in dashboard_slice
    assert "data-product-authority-checkpoint-step" in renderer_slice
    assert "data-ready" in renderer_slice

    for forbidden in (
        "postJson(",
        "submitAttachmentForm",
        "localStorage",
        "requestSubmit",
        "form.submit",
        "/handoff/export/download/prepare",
        "/handoff/export/download/readiness",
        "/handoff/export/download/deliver",
        "/handoff/export/download/signed-reference/generate",
        "download_url:",
        "public_url:",
        "signed_url:",
        "connector_run_id:",
        "destination:",
        "package_payload:",
        "schema_migration:",
    ):
        assert forbidden not in checkpoint_slice
        assert forbidden not in renderer_slice


def test_layer3_provider_public_url_use_rendered_control_is_bounded() -> None:
    html = client.get("/review/layer3").text
    js = client.get("/review/layer3/static/layer3.js").text

    assert 'data-rendered-extension="provider_public_url_delivery_use_rendered_control_extension"' in html
    assert 'id="provider-public-url-use"' in html
    assert 'id="provider-public-url-deliver"' not in html

    payload_start = js.index("function providerPublicUrlUsePayload")
    payload_end = js.index("function providerPublicUrlRevokePayload")
    payload_source = js[payload_start:payload_end]
    assert "client_request_id: requestId()" in payload_source
    assert "provider_public_url_receipt_id: providerPublicUrlReceiptId()" in payload_source
    assert "delivery_use_mode: 'fake_provider_redacted_use_decision'" in payload_source
    assert "operator_decision: 'use_provider_public_url_redacted_fake_provider'" in payload_source
    assert "expected_authority_hash" in payload_source
    assert "expected_source_artifact_hash" in payload_source
    assert "expected_source_artifact_size_bytes" in payload_source
    assert "provider_network_enabled" not in payload_source
    assert "connector_dispatch_enabled" not in payload_source
    assert "package_mutation_enabled" not in payload_source

    use_start = js.index("async function useProviderPublicUrlDecision")
    use_end = js.index("async function revokeProviderPublicUrl")
    use_source = js[use_start:use_end]
    latest_start = js.index("function providerPublicUrlLatestState")
    latest_end = js.index("function providerPublicUrlLatestSnapshot")
    latest_source = js[latest_start:latest_end]
    snapshot_start = js.index("function providerPublicUrlLatestSnapshot")
    snapshot_end = js.index("function providerPublicUrlAuthorityState")
    snapshot_source = js[snapshot_start:snapshot_end]
    gate_start = js.index("function canUseProviderPublicUrl")
    gate_end = js.index("function downstreamAccessLifecycleRows")
    gate_source = js[gate_start:gate_end]
    assert "State.providerPublicUrlStatus?.provider_public_url_state" in latest_source
    assert latest_source.index("State.providerPublicUrlStatus?.provider_public_url_state") < latest_source.index("State.providerPublicUrlUse?.provider_public_url_state")
    assert snapshot_source.index("State.providerPublicUrlStatus") < snapshot_source.index("State.providerPublicUrlUse")
    assert "&& !State.providerPublicUrlUse" in gate_source
    assert "'/handoff/export/download/provider-public-url/use'" in use_source
    assert "const payload = providerPublicUrlUsePayload()" in use_source
    assert "State.providerPublicUrlStatus = null" in use_source
    assert "payload" in use_source
    assert "localStorage" not in use_source
    assert "sessionStorage" not in use_source
    assert "provider-public-url/deliver" not in use_source


def test_layer3_source_directory_hybrid_delivery_control_is_bounded() -> None:
    js = client.get("/review/layer3/static/layer3.js")

    assert js.status_code == 200
    payload_start = js.text.find("function sourceDirectoryHybridExternalExportDownloadDeliveryPayload")
    payload_end = js.text.find("function sourceDirectoryHybridExternalExportDownloadDeliveryPayloadOrNull")
    status_start = js.text.find("function sourceDirectoryHybridExternalExportDownloadDeliveryStatusMatches")
    inspect_start = js.text.find("async function inspectSourceDirectoryHybridExternalExportDownloadDelivery")
    submit_start = js.text.find("async function submitSourceDirectoryHybridExternalExportDownloadDelivery")
    signed_start = js.text.find("async function submitExternalExportDownloadSignedReference")
    assert payload_start != -1
    assert payload_end != -1
    assert status_start != -1
    assert inspect_start != -1
    assert submit_start != -1
    assert signed_start != -1

    payload_slice = js.text[payload_start:payload_end]
    inspect_slice = js.text[inspect_start:submit_start]
    submit_slice = js.text[submit_start:signed_start]
    status_slice = js.text[status_start:submit_start]
    assert "operator_decision: 'deliver_source_directory_hybrid_external_export_download'" in payload_slice
    assert "external_export_download_target: SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_TARGET" in payload_slice
    assert "delivery_mode: 'same_origin_artifact_stream'" in payload_slice
    assert "SOURCE_DIRECTORY_HYBRID_DELIVERY_PAYLOAD_FIELDS.forEach" in payload_slice
    assert "postJson(" in inspect_slice
    assert "SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH" in inspect_slice
    assert "submitAttachmentForm(" in submit_slice
    assert "SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH" in submit_slice
    assert "status.provider_public_delivery_enabled === false" in status_slice
    assert "status.provider_private_signed_url_enabled === false" in status_slice
    assert "status.connector_dispatch_enabled === false" in status_slice
    assert "status.network_egress_enabled === false" in status_slice
    assert "status.frontend_durable_authority_enabled === false" in status_slice
    assert "status.raw_local_path_exposed === false" in status_slice
    for forbidden in (
        "payload_refs",
        "raw_payload_path",
        "local_file_path",
        "download_url",
        "public_url",
        "signed_url",
        "connector_run_id",
        "destination_id",
        "provider_credentials",
        "network_egress:",
        "package_payload_rewrite:",
        "source_package_row_mutation:",
        "raw_vector",
    ):
        assert forbidden not in payload_slice


def test_layer3_source_directory_hybrid_internal_webhook_control_is_bounded() -> None:
    html = client.get("/review/layer3")
    js = client.get("/review/layer3/static/layer3.js")
    js_text = js.text.replace("\r\n", "\n")

    assert html.status_code == 200
    assert js.status_code == 200
    assert 'id="source-directory-hybrid-internal-webhook-form"' in html.text
    assert (
        'data-rendered-mode="rendered_source_directory_hybrid_internal_webhook_dispatch_control"'
        in html.text
    )
    assert 'data-frontend-durable-authority="false"' in html.text

    payload_start = js_text.find("function sourceDirectoryHybridInternalWebhookPayload")
    payload_end = js_text.find("function sourceDirectoryHybridInternalWebhookPayloadOrNull")
    match_start = js_text.find("function sourceDirectoryHybridInternalWebhookStatusMatches")
    render_start = js_text.find("function renderSourceDirectoryHybridInternalWebhookPanel")
    render_end = js_text.find("function sourceDirectoryHybridExternalExportDownloadDeliveryPanelState")
    submit_start = js_text.find("async function submitSourceDirectoryHybridInternalWebhook")
    status_start = js_text.find("async function inspectSourceDirectoryHybridInternalWebhookStatus")
    status_end = js_text.find("async function submitExternalExportDownloadSignedReference")
    assert payload_start != -1
    assert payload_end != -1
    assert match_start != -1
    assert render_start != -1
    assert render_end != -1
    assert submit_start != -1
    assert status_start != -1
    assert status_end != -1

    payload_slice = js_text[payload_start:payload_end]
    match_slice = js_text[match_start:render_start]
    render_slice = js_text[render_start:render_end]
    submit_slice = js_text[submit_start:status_start]
    status_slice = js_text[status_start:status_end]
    request_slices = payload_slice + submit_slice + status_slice

    assert "operator_decision: SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_OPERATOR_DECISION" in payload_slice
    assert "external_export_download_target: SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_TARGET" in payload_slice
    assert "download_mode: 'reference_only_prepare'" in payload_slice
    assert "external_export_download_state: 'external_export_download_prepared'" in payload_slice
    assert "target_identity: 'server_configured_internal_webhook_destination'" in payload_slice
    assert "target_class: 'real_connector_invocation'" in payload_slice
    assert "dispatch_mode: 'server_configured_allowlisted_internal_webhook_post'" in payload_slice
    assert "SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_PAYLOAD_FIELDS.forEach" in payload_slice
    assert "SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_REQUIRED_FIELDS.filter" in payload_slice
    assert "postJson(\n            SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_DISPATCH_PATH" in submit_slice
    assert "getJson(\n            `${SOURCE_DIRECTORY_HYBRID_INTERNAL_WEBHOOK_STATUS_PATH}/" in status_slice
    assert "persistSessionRecoveryAnchor('source_directory_hybrid_internal_webhook_dispatch')" in submit_slice
    assert "persistSessionRecoveryAnchor('source_directory_hybrid_internal_webhook_status')" in status_slice
    assert "dataset.frontendDurableAuthority = 'false'" in render_slice
    assert "renderDownstreamLocks(downstream)" in render_slice
    assert "source_directory_internal_webhook_dispatched" in js_text
    assert "source_directory_internal_webhook_dispatch_history" in js_text
    assert "source_directory_internal_webhook_dispatch_receipt_id" in js_text
    for required_guard in (
        "status.source_directory_internal_webhook_post_performed === true",
        "status.connector_dispatch_enabled === false",
        "status.provider_public_url_enabled === false",
        "status.provider_private_signed_url_enabled === false",
        "status.raw_target_url_exposed === false",
        "status.raw_package_payload_exposed === false",
        "status.raw_package_bytes_exposed === false",
    ):
        assert required_guard in match_slice
    for forbidden in (
        "output_package_id",
        "package_kind",
        "package_payload_hash",
        "destination_url",
        "raw_target_url:",
        "token",
        "headers",
        "raw_package_payload:",
        "raw_package_bytes:",
        "provider_credentials",
        "localStorage",
        "sessionStorage",
        "browser_state",
        "rendered_control_state",
    ):
        assert forbidden not in request_slices


def test_layer3_source_directory_package_supersession_preview_control_is_bounded() -> None:
    html = client.get("/review/layer3")
    js = client.get("/review/layer3/static/layer3.js")
    js_text = js.text.replace("\r\n", "\n")

    assert html.status_code == 200
    assert js.status_code == 200
    assert 'id="source-directory-package-supersession-preview-submit"' in html.text
    assert 'id="source-directory-package-supersession-preview-authority"' in html.text
    assert (
        'data-rendered-mode="rendered_source_directory_package_supersession_preview_control"'
        in html.text
    )
    assert 'data-read-only="true"' in html.text
    assert 'data-frontend-durable-authority="false"' in html.text

    payload_start = js_text.find("function sourceDirectoryPackageSupersessionPreviewPayload")
    payload_end = js_text.find("function sourceDirectoryPackageSupersessionPreviewPayloadOrNull")
    render_start = js_text.find("function renderSourceDirectoryPackageSupersessionPreviewPanel")
    render_end = js_text.find("function renderReplacementPackageSetAuthorityPanel")
    submit_start = js_text.find("async function submitSourceDirectoryPackageSupersessionPreview")
    submit_end = js_text.find("async function submitReplacementPackageSetAuthority")
    assert payload_start != -1
    assert payload_end != -1
    assert render_start != -1
    assert render_end != -1
    assert submit_start != -1
    assert submit_end != -1

    payload_slice = js_text[payload_start:payload_end]
    render_slice = js_text[render_start:render_end]
    submit_slice = js_text[submit_start:submit_end]
    assert "operator_decision: SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION" in payload_slice
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_PAYLOAD_FIELDS.forEach" in payload_slice
    assert "payload[field].length !== 3" in payload_slice
    assert "payload.package_review_state !== 'package_review_approved'" in payload_slice
    assert "postJson(\n            SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_PATH" in submit_slice
    assert "const preview = await postJson" in submit_slice
    assert "State.sourceDirectoryPackageSupersessionPreview = preview" in submit_slice
    assert "dataset.readOnly = 'true'" in render_slice
    assert "dataset.frontendDurableAuthority = 'false'" in render_slice
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_SCHEMA_ID" in render_slice
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PREVIEW_MODE" in render_slice
    for forbidden in (
        "payload_refs",
        "raw_payload_path",
        "local_file_path",
        "download_url",
        "public_url",
        "signed_url",
        "connector_run_id",
        "destination_id",
        "provider_credentials",
        "localStorage",
        "sessionStorage",
        "/package/mutation/preview",
        "/package/supersession/commit",
        "/package/replacement",
    ):
        assert forbidden not in payload_slice
        assert forbidden not in submit_slice


def test_layer3_source_directory_handoff_export_controls_are_bounded() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    js_text = js.text.replace("\r\n", "\n")

    assert js.status_code == 200
    for required in (
        "SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_PATH",
        "SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH",
        "SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH",
        "SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH",
        "rendered_source_directory_qualitative_handoff_export_prepare_control",
        "rendered_source_directory_qualitative_external_export_download_prepare_control",
        "rendered_source_directory_qualitative_external_export_download_delivery_control",
        "source_directory_external_export_download_delivery_ui_ready",
    ):
        assert required in js_text

    payload_start = js_text.find("function sourceDirectoryQualitativePackageReviewBasePayload")
    payload_end = js_text.find("function replacementPackageArtifactMaterializationPayload")
    status_start = js_text.find("function sourceDirectoryQualitativeExternalExportDownloadDeliveryStatusMatches")
    status_end = js_text.find("function replacementPackageSetAuthorityState")
    submit_handoff_start = js_text.find("async function submitHandoffExportPrepare")
    submit_handoff_end = js_text.find("async function submitApsHandoffDispatch")
    submit_external_start = js_text.find("async function submitExternalExportDownloadPrepare")
    submit_external_end = js_text.find("async function submitExternalExportDownloadDelivery")
    submit_delivery_start = submit_external_end
    submit_delivery_end = js_text.find("async function inspectSourceDirectoryHybridExternalExportDownloadDelivery")
    assert payload_start != -1
    assert payload_end != -1
    assert status_start != -1
    assert status_end != -1
    assert submit_handoff_start != -1
    assert submit_handoff_end != -1
    assert submit_external_start != -1
    assert submit_external_end != -1
    assert submit_delivery_end != -1

    payload_slice = js_text[payload_start:payload_end]
    status_slice = js_text[status_start:status_end]
    submit_handoff_slice = js_text[submit_handoff_start:submit_handoff_end]
    submit_external_slice = js_text[submit_external_start:submit_external_end]
    submit_delivery_slice = js_text[submit_delivery_start:submit_delivery_end]

    assert "operator_decision: elements.handoffExportPrepareDecision.value" in payload_slice
    assert "handoff_target: 'internal_export_envelope'" in payload_slice
    assert "export_mode: 'prepare_only'" in payload_slice
    assert "operator_decision: 'prepare_source_directory_external_export_download'" in payload_slice
    assert "external_export_download_target: SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_TARGET" in payload_slice
    assert "operator_decision: 'deliver_source_directory_external_export_download'" in payload_slice
    assert "delivery_mode: 'same_origin_artifact_stream'" in payload_slice
    assert "sourceDirectoryQualitativeExternalExportDownloadSelectedPackage(external)" in payload_slice
    assert "SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_PATH" in submit_handoff_slice
    assert "sourceDirectoryQualitativeHandoffExportPreparePayload()" in submit_handoff_slice
    assert "SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH" in submit_external_slice
    assert "sourceDirectoryQualitativeExternalExportDownloadPreparePayload()" in submit_external_slice
    assert "SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH" in submit_delivery_slice
    assert "SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH" in submit_delivery_slice
    assert "sourceDirectoryQualitativeExternalExportDownloadDeliveryPayload()" in submit_delivery_slice
    assert "sourceDirectoryStatusValidated = true" in submit_delivery_slice
    for required in (
        "status.same_origin_delivery_enabled === true",
        "status.browser_managed_same_origin_attachment_enabled === true",
        "status.provider_public_delivery_enabled === false",
        "status.provider_private_signed_url_enabled === false",
        "status.connector_dispatch_enabled === false",
        "status.network_egress_enabled === false",
        "status.frontend_durable_authority_enabled === false",
        "status.raw_local_path_exposed === false",
    ):
        assert required in status_slice
    for forbidden in (
        "payload_refs",
        "source_payload_refs",
        "replacement_payload_refs",
        "artifact_manifest",
        "raw_payload_path",
        "local_file_path",
        "download_url",
        "public_url",
        "signed_url",
        "connector_run_id",
        "destination_id",
        "provider_credentials",
        "localStorage",
        "sessionStorage",
    ):
        assert forbidden not in payload_slice


def test_layer3_source_directory_replacement_package_set_authority_control_is_bounded() -> None:
    html = client.get("/review/layer3")
    js = client.get("/review/layer3/static/layer3.js")
    js_text = js.text.replace("\r\n", "\n")

    assert html.status_code == 200
    assert js.status_code == 200
    assert 'id="replacement-package-set-authority-submit"' in html.text
    assert 'id="replacement-package-set-authority-panel"' in html.text
    assert (
        'data-rendered-mode="rendered_replacement_package_set_authority_control"'
        in html.text
    )
    assert 'data-frontend-durable-authority="false"' in html.text

    state_start = js_text.find("function replacementPackageSetAuthorityPreviewState")
    state_end = js_text.find("function replacementPackageArtifactMaterializationState")
    gate_start = js_text.find("function canSubmitReplacementPackageSetAuthority")
    gate_end = js_text.find("function canSubmitPackageSupersessionCommit")
    render_start = js_text.find("function renderReplacementPackageSetAuthorityPanel")
    generic_payload_start = js_text.find("function replacementPackageArtifactMaterializationPayload")
    generic_payload_end = js_text.find("function replacementPackageSetAuthorityPayload")
    source_payload_start = js_text.find("function sourceDirectoryReplacementPackageSetAuthorityPayload")
    source_payload_end = js_text.find("async function packageSupersessionCommitPayload")
    commit_gate_start = js_text.find("function canSubmitPackageSupersessionCommit")
    commit_gate_end = js_text.find("function canSubmitReplacementPackageArtifactManifest")
    commit_render_start = js_text.find("function renderPackageSupersessionCommitPanel")
    commit_render_end = js_text.find("function renderReplacementPackageArtifactManifestPanel")
    commit_payload_start = js_text.find("function sourceDirectoryPackageSupersessionCommitPayload")
    commit_payload_end = js_text.find("function replacementPackageArtifactManifestPayload")
    clear_start = js_text.find("function clearSourceDirectoryPackageSupersessionPreviewState")
    clear_end = js_text.find("function safePackagePayloadRefForDisplay")
    source_submit_start = js_text.find("async function submitSourceDirectoryPackageSupersessionPreview")
    source_submit_end = js_text.find("async function submitReplacementPackageSetAuthority")
    submit_start = js_text.find("async function submitReplacementPackageSetAuthority")
    submit_end = js_text.find("async function submitPackageSupersessionCommit")
    input_start = js_text.find("elements.sourceDirectoryPackageSupersessionPreviewAuthority.addEventListener")
    input_end = js_text.find("elements.replacementPackageSetAuthoritySubmit.addEventListener")
    assert state_start != -1
    assert state_end != -1
    assert gate_start != -1
    assert gate_end != -1
    assert render_start != -1
    assert generic_payload_start != -1
    assert generic_payload_end != -1
    assert source_payload_start != -1
    assert source_payload_end != -1
    assert commit_gate_start != -1
    assert commit_gate_end != -1
    assert commit_render_start != -1
    assert commit_render_end != -1
    assert commit_payload_start != -1
    assert commit_payload_end != -1
    assert clear_start != -1
    assert clear_end != -1
    assert source_submit_start != -1
    assert source_submit_end != -1
    assert submit_start != -1
    assert submit_end != -1
    assert input_start != -1
    assert input_end != -1

    state_slice = js_text[state_start:state_end]
    gate_slice = js_text[gate_start:gate_end]
    render_slice = js_text[render_start:commit_render_start]
    generic_payload_slice = js_text[generic_payload_start:generic_payload_end]
    source_payload_slice = js_text[source_payload_start:source_payload_end]
    commit_gate_slice = js_text[commit_gate_start:commit_gate_end]
    commit_render_slice = js_text[commit_render_start:commit_render_end]
    commit_payload_slice = js_text[commit_payload_start:commit_payload_end]
    clear_slice = js_text[clear_start:clear_end]
    source_submit_slice = js_text[source_submit_start:source_submit_end]
    submit_slice = js_text[submit_start:submit_end]
    input_slice = js_text[input_start:input_end]

    assert "sourceDirectoryPackageSupersessionPreviewRequestToken: 0" in js_text
    assert "sourceDirectoryPackageSupersessionPreviewPendingRequestToken: null" in js_text
    assert "function nextSourceDirectoryPackageSupersessionPreviewRequestToken" in js_text
    assert "function isCurrentSourceDirectoryPackageSupersessionPreviewRequest" in js_text
    assert "nextSourceDirectoryPackageSupersessionPreviewRequestToken()" in clear_slice
    assert "State.sourceDirectoryPackageSupersessionPreviewPending = false" in clear_slice
    assert "State.sourceDirectoryPackageSupersessionPreviewPendingRequestToken = null" in clear_slice
    assert "const requestToken = nextSourceDirectoryPackageSupersessionPreviewRequestToken()" in source_submit_slice
    assert "State.sourceDirectoryPackageSupersessionPreviewPendingRequestToken = requestToken" in source_submit_slice
    assert "if (!isCurrentSourceDirectoryPackageSupersessionPreviewRequest(requestToken)) return" in source_submit_slice
    assert "State.sourceDirectoryPackageSupersessionPreviewPendingRequestToken === requestToken" in source_submit_slice
    assert "function isSourceDirectoryPackageSupersessionPreviewSelected" in state_slice
    assert "if (sourceDirectoryPreview && isSourceDirectoryQualitativePackageAuthoritySelected())" in state_slice
    assert "return packagePreview || sourceDirectoryPreview || null" in state_slice
    assert "SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_SOURCE_AUTHORITY" in state_slice
    assert "preview?.source_package_set_hash || preview?.package_set_hash || null" in state_slice
    assert "const preview = replacementPackageSetAuthorityPreviewState() || {}" in gate_slice
    assert "const sourcePackageSetHash = replacementPackageSetAuthoritySourcePackageSetHash(preview)" in gate_slice
    assert "sourceMode === 'source_directory_package_supersession_preview'" in gate_slice
    assert "preview.session_id" in gate_slice
    assert "&& sourcePackageSetHash" in gate_slice
    assert "!packagePreviewSubmissionPending()" in gate_slice
    assert "dataset.renderedMode = renderedMode" in render_slice
    assert "dataset.sourceAuthority = sourceAuthority" in render_slice
    assert "dataset.sourceMode = sourceMode" in render_slice
    assert "SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_MODE" in render_slice
    assert "SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_USE_CASE" in render_slice
    assert "SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_PATH" in render_slice
    assert "fieldItem('selected source authority', sourceAuthority" in render_slice
    assert "fieldItem('selected source mode', sourceMode" in render_slice
    assert "const preview = replacementPackageSetAuthorityPreviewState() || {}" in generic_payload_slice
    assert "source_package_set_hash: sourcePackageSetHash" in generic_payload_slice
    assert "function sourceDirectoryReplacementPackageSetAuthorityPayload" in source_payload_slice
    assert "session_id: preview.session_id" in source_payload_slice
    assert "source_package_set_hash: preview.source_package_set_hash" in source_payload_slice
    assert "operator_decision: REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION" in source_payload_slice
    assert "materialization = await postJson(\n                '/package/replacement-artifact/materialize'" in submit_slice
    assert "SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_PATH" in submit_slice
    assert "sourceDirectoryReplacementPackageSetAuthorityPayload()" in submit_slice
    assert "State.replacementPackageArtifactMaterialization = materialization" in submit_slice
    assert "State.replacementPackageSetAuthority = await postJson(" in submit_slice
    assert ": '/package/replacement-set/record'" in submit_slice
    assert "source_directory_package_supersession_preview" in commit_gate_slice
    assert "replacementAuthority.replacement_package_set_authority_id" in commit_gate_slice
    assert "replacementAuthority.authority_basis_hash" in commit_gate_slice
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_RENDERED_MODE" in commit_render_slice
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_USE_CASE" in commit_render_slice
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_PATH" in commit_render_slice
    assert "function sourceDirectoryPackageSupersessionCommitPayload" in commit_payload_slice
    assert "replacement_package_set_authority_id: replacementAuthority.replacement_package_set_authority_id" in commit_payload_slice
    assert "replacement_authority_basis_hash: replacementAuthority.authority_basis_hash" in commit_payload_slice
    assert "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_PATH" in js_text[submit_end:js_text.find("async function submitReplacementPackageArtifactManifest")]
    assert "sourceDirectoryPackageSupersessionCommitPayload()" in js_text[submit_end:js_text.find("async function submitReplacementPackageArtifactManifest")]
    assert "clearSourceDirectoryPackageSupersessionPreviewState()" in input_slice
    assert "clearReplacementPackageSetAuthorityState()" in input_slice
    for forbidden in (
        "localStorage",
        "sessionStorage",
        "/package/supersession/commit",
        "download_url",
        "public_url",
        "signed_url",
        "provider_credentials",
    ):
        assert forbidden not in state_slice
        assert forbidden not in gate_slice
        assert forbidden not in source_payload_slice
        assert forbidden not in commit_payload_slice
        assert forbidden not in submit_slice
    for forbidden in (
        "source_output_package_ids",
        "source_payload_refs",
        "replacement_payload_refs",
        "commit_basis_hash",
        "downstream_dependency_hash",
        "frontend_state",
        "browser_state",
        "rendered_control_state",
    ):
        assert forbidden not in source_payload_slice
        assert forbidden not in commit_payload_slice


def test_layer3_source_directory_package_supersession_provider_private_control_is_bounded() -> None:
    js = client.get("/review/layer3/static/layer3.js")

    assert js.status_code == 200
    js_text = js.text
    constants_start = js_text.find("SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PROVIDER_PRIVATE_SIGNED_URL_PATH")
    ready_start = js_text.find("function sourceDirectoryPackageSupersessionProviderPrivateSignedUrlReady")
    base_payload_start = js_text.find("function sourceDirectoryPackageSupersessionProviderPrivateSignedUrlBasePayload")
    base_payload_end = js_text.find("function providerPrivateSignedUrlPreparePayload")
    provider_payload_end = js_text.find("function providerPublicUrlPrepareRequestId")
    inspect_start = js_text.find("async function inspectProviderPrivateSignedUrlStatus")
    use_handler_start = js_text.find("async function useProviderPrivateSignedUrl")
    controls_start = js_text.find("const providerPrivateSignedUrlControlsEnabled")
    controls_end = js_text.find("elements.gateBSubmit.disabled")
    assert constants_start != -1
    assert ready_start != -1
    assert base_payload_start != -1
    assert base_payload_end != -1
    assert provider_payload_end != -1
    assert inspect_start != -1
    assert use_handler_start != -1
    assert controls_start != -1
    assert controls_end != -1

    constants_slice = js_text[constants_start:ready_start]
    ready_slice = js_text[ready_start:base_payload_start]
    base_payload_slice = js_text[base_payload_start:base_payload_end]
    provider_payload_slice = js_text[base_payload_end:provider_payload_end]
    inspect_slice = js_text[inspect_start:use_handler_start]
    controls_slice = js_text[controls_start:controls_end]
    snapshot_slice = _js_slice(
        js_text,
        "function providerPrivateReceiptSnapshot",
        "function persistProviderPrivateReceiptSnapshot",
    )
    authority_slice = _js_slice(
        js_text,
        "function providerPrivateSignedUrlAuthorityState",
        "function providerPrivateSignedUrlSelectedArtifactFamily",
    )
    family_slice = _js_slice(
        js_text,
        "function providerPrivateSignedUrlActiveArtifactFamily",
        "function providerPrivateSignedUrlUsesSourceDirectoryHybridFamily",
    )
    gate_slice = _js_slice(
        js_text,
        "function sourceDirectoryProviderPrivateSignedUrlAuthorityReady",
        "function canInspectProviderPrivateSignedUrl",
    )
    for required in (
        "/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/provider-private-signed-url",
        "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PROVIDER_PRIVATE_SIGNED_URL_PREPARE_PATH",
        "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PROVIDER_PRIVATE_SIGNED_URL_STATUS_PATH",
        "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PROVIDER_PRIVATE_SIGNED_URL_USE_PATH",
        "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_PATH",
        "prepare_source_directory_package_supersession_provider_private_signed_url",
        "inspect_source_directory_package_supersession_provider_private_signed_url_status",
        "use_source_directory_package_supersession_provider_private_signed_url",
        "revoke_source_directory_package_supersession_provider_private_signed_url",
    ):
        assert required in constants_slice
    for required in (
        "isSourceDirectoryPackageSupersessionCommitState(commit)",
        "commit.package_supersession_commit_id",
        "commit.commit_basis_hash",
        "commit.replacement_package_set_authority_id",
        "commit.replacement_authority_basis_hash",
    ):
        assert required in ready_slice
    for required in (
        "package_supersession_commit_id: commit.package_supersession_commit_id",
        "package_supersession_commit_basis_hash: commit.commit_basis_hash",
        "replacement_package_set_authority_id: commit.replacement_package_set_authority_id",
        "replacement_authority_basis_hash: commit.replacement_authority_basis_hash",
        "delivery_mode: 'provider_private_signed_url'",
    ):
        assert required in base_payload_slice
    for required in (
        "providerPrivateSignedUrlUsesSourceDirectoryPackageFamily()",
        "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PROVIDER_PRIVATE_SIGNED_URL_OPERATOR_DECISION",
        "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PROVIDER_PRIVATE_SIGNED_URL_STATUS_OPERATOR_DECISION",
        "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PROVIDER_PRIVATE_SIGNED_URL_USE_OPERATOR_DECISION",
        "SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_PROVIDER_PRIVATE_SIGNED_URL_REVOKE_OPERATOR_DECISION",
        "provider_signed_url_receipt_id: providerPrivateSignedUrlReceiptId()",
    ):
        assert required in provider_payload_slice
    assert "providerPrivateSignedUrlUsesSourceDirectoryPackageFamily()" in inspect_slice
    assert "sourceDirectoryPackageSupersessionProviderPrivateSignedUrlReady()" in controls_slice
    assert "source_directory_hybrid_provider_private_signed_url_enabled" in snapshot_slice
    assert "source_directory_package_supersession_provider_private_signed_url_enabled" in snapshot_slice
    assert "source_directory_package_supersession_authority" in snapshot_slice
    assert "State.providerPrivateSignedUrlStatus" in authority_slice
    assert "State.providerPrivateSignedUrlUse" in authority_slice
    assert authority_slice.find("State.providerPrivateSignedUrlStatus") < authority_slice.find("State.providerPrivateSignedUrlUse")
    assert "State.providerPrivateSignedUrlReceiptRecovery" in authority_slice
    assert family_slice.find("isSourceDirectoryHybridExternalExportDownloadPrepareState") < family_slice.find("isSourceDirectoryPackageSupersessionProviderPrivateState")
    assert "sourceDirectoryHybridProviderPrivateSignedUrlReady()" in family_slice
    assert "sourceDirectoryProviderPrivateSignedUrlAuthorityReady()" in js_text[
        js_text.find("function canInspectProviderPrivateSignedUrl"):
        js_text.find("function canUseProviderPrivateSignedUrl")
    ]
    assert "sourceDirectoryProviderPrivateSignedUrlAuthorityReady()" in js_text[
        js_text.find("function canRevokeProviderPrivateSignedUrl"):
        js_text.find("function providerPublicUrlReceiptId")
    ]
    assert "sourceDirectoryPackageSupersessionProviderPrivateSignedUrlReady()" in gate_slice
    for forbidden in (
        "raw_provider_url",
        "provider_credentials",
        "provider_secret",
        "provider_public_url",
        "public_url",
        "download_url",
        "package_payload",
        "source_payload_refs",
        "replacement_payload_refs",
        "connector_run_id",
        "destination_url",
        "frontend_state",
        "browser_state",
    ):
        assert forbidden not in base_payload_slice


def test_layer3_package3_candidate_b_ui_payload_and_gating_contracts() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    assert js.status_code == 200
    js_text = js.text.replace("\r\n", "\n")

    runtime_payload = _js_slice(
        js_text,
        "function candidateBRuntimeDownstreamProofPayload",
        "function canInspectCandidateBArtifactFamilyStatus",
    )
    final_status_inputs = _js_slice(
        js_text,
        "function candidateBDefaultPromotionFinalProofStatusInputValues",
        "function candidateBOperatorStatusInputValues",
    )
    operator_status_gate = _js_slice(
        js_text,
        "function candidateBOperatorStatusEvidenceMatches",
        "function canRecordSecEdgarSourceAcquisitionAuthority",
    )
    closeout_gate = _js_slice(
        js_text,
        "function canRecordCandidateBFullCorpusRepeatabilityAcceptanceCloseout",
        "function canInspectCandidateBFullCorpusRepeatabilityAcceptanceCloseoutStatus",
    )
    namespace_slice = _js_slice(
        js_text,
        "function replacementPackageNamespaceRecordedKinds",
        "function renderReplacementPackageRows",
    )
    selector_activation = _js_slice(
        js_text,
        "function candidateBBroaderScopeSelectorActivationDefaults",
        "function candidateBBroaderScopeSelectorActivationPayload",
    )
    selector_input_handler = _js_slice(
        js_text,
        "target.id === 'candidate-b-broader-scope-selector-use-receipt-id'",
        "target.id === 'candidate-b-broader-scope-selector-use-status-receipt-id'",
    )
    package_preview_submit = _js_slice(
        js_text,
        "async function submitPackageSupersessionPreview",
        "async function submitSourceDirectoryPackageSupersessionPreview",
    )

    assert "candidate_b_visual_lane_status_evidence: State.candidateBVisualLaneStatus" in runtime_payload
    assert "coverage_evidence: JSON.parse(values.coverageEvidenceJson)" in runtime_payload
    assert "renderedInputValue(" in final_status_inputs
    assert "candidateBOperatorStatusEvidenceMatches(values)" in operator_status_gate
    assert "visual.candidate_b_run_id === values.candidateBRunId" in operator_status_gate
    assert "runtimeProof.proof_receipt_id" in operator_status_gate
    assert "runtimeProof.proof_hash" in operator_status_gate
    assert "!closeoutReceipt.repeatability_acceptance_operator_closeout_receipt_id" in closeout_gate
    assert "State.sessionSummary?.replacement_package_namespace" in namespace_slice
    assert "return rows.find((row) => row.package_kind && !recordedKinds.has(row.package_kind)) || null" in namespace_slice
    assert "candidateBBroaderScopeSelectorActivationDefaults" in selector_activation
    assert "preferStatusAuthority" in selector_activation
    assert "input?.value || storedValue || authorityValue" in selector_activation
    assert "State.candidateBBroaderScopeSelectorUseStatus = null" in selector_input_handler
    assert "State.candidateBBroaderScopeSelectorActivation = null" in selector_input_handler
    assert "State.packageSupersessionPreview = null" in package_preview_submit


def test_layer3_package3_remaining_ui_state_contracts() -> None:
    response = client.get("/review/layer3")
    js = client.get("/review/layer3/static/layer3.js")
    assert response.status_code == 200
    assert js.status_code == 200
    html = response.text
    js_text = js.text.replace("\r\n", "\n")

    operation_steps = _js_slice(js_text, "const OPERATION_DOCK_STEPS", "function escapeHtml")
    operation_status = _js_slice(js_text, "function operationDockStatus", "function renderOperationDockSummary")
    supersession_payload = _js_slice(
        js_text,
        "function packageSupersessionPreviewPayload",
        "function sourceDirectoryPackageSupersessionPreviewAuthorityPacket",
    )
    provider_use = _js_slice(
        js_text,
        "async function useProviderPublicUrlDecision",
        "async function revokeProviderPublicUrl",
    )
    lifecycle_state = _js_slice(
        js_text,
        "function packageLifecycleDashboardState",
        "function renderPackageLifecycleRows",
    )
    package_panel_state = _js_slice(
        js_text,
        "function packageReviewPanelState",
        "function renderPackageReviewPreviewPanel",
    )
    final_proof_clear = _js_slice(
        js_text,
        "function clearCandidateBFinalProofInspectionState",
        "function clearResultReviewState",
    )
    result_clear = _js_slice(
        js_text,
        "function clearResultReviewState",
        "function selectedResultAuthority",
    )
    visual_lane_inspection = _js_slice(
        js_text,
        "async function inspectCandidateBVisualLaneStatus",
        "async function recordCandidateBBundleDownstreamProof",
    )
    candidate_b_input_handler = _js_slice(
        js_text,
        "elements.candidateBDefaultPromotionStatusPanel.addEventListener('input'",
        "elements.resultReviewDecision.addEventListener",
    )

    assert '<option value="prototype">Prototype</option>' in html
    for target in ("quantitative", "qualitative", "hybrid-mixed"):
        assert f'data-transfer-target="{target}"' in html
    for object_index in range(1, 21):
        assert f"Gate B Ingress Object #{object_index}" in html
    assert 'id="run-preflight" class="primary-btn" type="submit"' in html
    assert "preventRawMixedManifestEnterSubmit" in js_text

    assert "source-directory-ingestion-rendered-controls" in operation_steps
    assert "key: 'source_directory'" in operation_steps
    assert "case 'source_directory':" in operation_status
    assert "State.sourceDirectoryIngestionBatchStatus?.source_ingestion_batch_id" in operation_status

    assert "State.sessionSummary?.connector_local_destination_receipt" in supersession_payload
    assert supersession_payload.index("State.sessionSummary?.connector_local_destination_receipt") < supersession_payload.index("State.sessionSummary?.connector_dispatch_record")
    assert provider_use.index("State.providerPublicUrlUse = await postJson") < provider_use.index("State.providerPublicUrlStatus = null")

    assert "const hasLifecycleRows = packageLifecycleOutputRows().length > 0" in lifecycle_state
    assert "package_lifecycle_rows_unavailable" in lifecycle_state
    assert "submitState === 'package_review_approved' ? 'ok' : 'blocked'" in package_panel_state

    assert "State.candidateBDefaultPromotionFinalProof = null" in final_proof_clear
    assert "State.candidateBDefaultPromotionFinalProofStatus = null" in final_proof_clear
    assert "clearCandidateBFinalProofInspectionState()" in result_clear
    assert visual_lane_inspection.index("State.candidateBRuntimeDownstreamProof = null") < visual_lane_inspection.index("State.candidateBVisualLaneStatus = await postJson")

    assert "function updateCandidateBDefaultPromotionStatusControls" in js_text
    assert "updateCandidateBDefaultPromotionStatusControls()" in candidate_b_input_handler
    assert "renderCandidateBDefaultPromotionStatusPanel()" not in candidate_b_input_handler


def test_layer3_source_directory_routing_and_preview_state_contracts() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    assert js.status_code == 200
    js_text = js.text.replace("\r\n", "\n")

    hybrid_prepare = _js_slice(
        js_text,
        "function sourceDirectoryHybridExternalExportDownloadPrepareState",
        "function isSourceDirectoryHybridExternalExportDownloadPrepareState",
    )
    signed_reference_gate = _js_slice(
        js_text,
        "function canGenerateExternalExportDownloadSignedReference",
        "function canUseExternalExportDownloadSignedReference",
    )
    gate_controls = _js_slice(
        js_text,
        "const externalExportDownloadSignedReferenceControlsEnabled",
        "const providerPrivateSignedUrlControlsEnabled",
    )
    lifecycle_state = _js_slice(
        js_text,
        "State.sourceDirectoryHybridMiddleLifecycle = {",
        "try {\n            State.sessionSummary",
    )
    downstream_gates = _js_slice(
        js_text,
        "function packagePreviewSubmissionPending",
        "function isPackageActive",
    )

    assert "sourceSessionId && activeSessionId && sourceSessionId !== activeSessionId" in hybrid_prepare
    assert "lifecycleSessionId && activeSessionId && lifecycleSessionId !== activeSessionId" in hybrid_prepare
    assert "!isSourceDirectoryQualitativeExternalExportDownloadPrepareState(external)" in signed_reference_gate
    assert "!isSourceDirectoryHybridExternalExportDownloadPrepareState(external)" in signed_reference_gate
    assert "!isSourceDirectoryQualitativeExternalExportDownloadPrepareState(externalPrepare)" in gate_controls
    assert "!isSourceDirectoryHybridExternalExportDownloadPrepareState(externalPrepare)" in gate_controls
    assert "session_id: currentSessionId()" in lifecycle_state
    assert "function packagePreviewSubmissionPending" in downstream_gates
    assert downstream_gates.count("!packagePreviewSubmissionPending()") >= 6


def test_layer3_source_directory_hybrid_rendered_status_extension_is_bounded() -> None:
    response = client.get("/review/layer3")
    js = client.get("/review/layer3/static/layer3.js")

    assert response.status_code == 200
    assert js.status_code == 200
    assert 'id="source-directory-hybrid-rendered-status-extension"' in response.text
    assert (
        'data-rendered-mode="source_directory_hybrid_context_packet_to_output_handoff_rendered_status_extension"'
        in response.text
    )
    assert 'data-read-only="true"' in response.text
    assert 'data-frontend-durable-authority="false"' in response.text

    state_start = js.text.find("function sourceDirectoryHybridRenderedStatusExtensionState")
    render_start = js.text.find("function renderSourceDirectoryHybridRenderedStatusExtension")
    panel_start = js.text.find("function renderSourceDirectoryHybridExternalExportDownloadDeliveryPanel")
    assert state_start != -1
    assert render_start != -1
    assert panel_start != -1
    assert state_start < render_start < panel_start
    extension_slice = js.text[state_start:panel_start]

    assert "source_directory_hybrid_status_unavailable" in extension_slice
    assert "source_directory_hybrid_status_ready" in extension_slice
    assert "source_directory_hybrid_delivery_submitted" in extension_slice
    assert "SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH" in extension_slice
    assert "SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH" in extension_slice
    assert "State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus" in extension_slice
    assert "State.sourceDirectoryHybridExternalExportDownloadDelivery" in extension_slice
    assert "sourceDirectoryHybridExternalExportDownloadDeliveryStatusMatches" in extension_slice
    assert "frontendDurableAuthority = 'false'" in extension_slice
    assert "full mockup activation" in extension_slice
    assert "blocked" in extension_slice
    assert "postJson(" not in extension_slice
    assert "submitAttachmentForm(" not in extension_slice
    assert "localStorage" not in extension_slice
    assert "sessionStorage" not in extension_slice
    for forbidden in (
        "payload_refs",
        "raw_payload_path",
        "local_file_path",
        "file_bytes",
        "download_url:",
        "public_url:",
        "signed_url:",
        "connector_run_id:",
        "destination_id:",
        "provider_credentials",
        "runtime_db_write:",
        "schema_migration:",
    ):
        assert forbidden not in extension_slice


def test_layer3_source_directory_hybrid_middle_lifecycle_rendered_control_is_bounded() -> None:
    response = client.get("/review/layer3")
    js = client.get("/review/layer3/static/layer3.js")

    assert response.status_code == 200
    assert js.status_code == 200
    assert 'id="source-directory-hybrid-middle-lifecycle-form"' in response.text
    assert 'id="source-directory-hybrid-middle-lifecycle-panel"' in response.text
    assert 'id="source-directory-hybrid-middle-lifecycle-authority"' in response.text
    assert 'id="source-directory-hybrid-authority-prepare"' in response.text
    assert 'id="source-directory-hybrid-middle-lifecycle-submit"' in response.text
    assert (
        'data-rendered-mode="rendered_source_directory_hybrid_middle_lifecycle_control"'
        in response.text
    )
    assert 'data-frontend-durable-authority="false"' in response.text

    authority_start = js.text.find("function sourceDirectoryHybridMiddleLifecycleAuthorityPacket")
    authority_end = js.text.find("function sourceDirectoryHybridExternalExportDownloadSelectedPackage")
    render_start = js.text.find("function renderSourceDirectoryHybridMiddleLifecyclePanel")
    render_end = js.text.find("function sourceDirectoryHybridInternalWebhookPanelState")
    submit_start = js.text.find("async function submitSourceDirectoryHybridMiddleLifecycle")
    next_submit_start = js.text.find("async function inspectSourceDirectoryHybridExternalExportDownloadDelivery")
    assert authority_start != -1
    assert authority_end != -1
    assert render_start != -1
    assert render_end != -1
    assert submit_start != -1
    assert next_submit_start != -1
    assert authority_start < authority_end < render_start < render_end < submit_start < next_submit_start
    authority_slice = js.text[authority_start:authority_end]
    render_slice = js.text[render_start:render_end]
    submit_slice = js.text[submit_start:next_submit_start]

    assert "SOURCE_DIRECTORY_HYBRID_AUTHORITY_PREPARE_PATH" in render_slice
    assert "SOURCE_DIRECTORY_HYBRID_VECTOR_RETRIEVAL_PATH" in render_slice
    assert "SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_PATH" in render_slice
    assert "SOURCE_DIRECTORY_HYBRID_ANALYSIS_PATH" in render_slice
    assert "SOURCE_DIRECTORY_HYBRID_PACKAGE_COMMIT_PATH" in render_slice
    assert "SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH" in render_slice
    assert "postJson(SOURCE_DIRECTORY_HYBRID_VECTOR_RETRIEVAL_PATH" in submit_slice
    assert "postJson(SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_PATH" in submit_slice
    assert "postJson(SOURCE_DIRECTORY_HYBRID_ANALYSIS_PATH" in submit_slice
    assert "postJson(SOURCE_DIRECTORY_HYBRID_PACKAGE_COMMIT_PATH" in submit_slice
    assert "SOURCE_DIRECTORY_HYBRID_PACKAGE_REVIEW_SUBMIT_PATH" in submit_slice
    assert "SOURCE_DIRECTORY_HYBRID_HANDOFF_EXPORT_PREPARE_PATH" in submit_slice
    assert "SOURCE_DIRECTORY_HYBRID_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH" in submit_slice
    assert "postJson(SOURCE_DIRECTORY_HYBRID_AUTHORITY_PREPARE_PATH" in js.text
    assert submit_slice.count("postJson(") >= 8
    middle_slice = authority_slice + render_slice + submit_slice
    assert "source_directory_hybrid_middle_lifecycle_prepared" in middle_slice
    assert "State.sourceDirectoryHybridMiddleLifecycle" in render_slice
    assert "State.sourceDirectoryHybridMiddleLifecycle" in submit_slice
    assert "function sourceDirectoryHybridPackageSupersessionPreviewAuthority" in middle_slice
    assert "elements.sourceDirectoryPackageSupersessionPreviewAuthority.value = JSON.stringify" in submit_slice
    assert "sourceDirectoryPackageSupersessionAuthority" in submit_slice
    assert "clearSourceDirectoryPackageSupersessionPreviewState()" in submit_slice
    assert "clearReplacementPackageSetAuthorityState()" in submit_slice
    assert "elements.sourceDirectoryHybridExternalExportDownloadDeliveryAuthority.value = deliveryAuthorityText" in submit_slice
    assert "elements.sourceDirectoryHybridInternalWebhookAuthority.value = deliveryAuthorityText" in submit_slice
    assert "frontendDurableAuthority = 'false'" in render_slice
    assert "submitAttachmentForm(" not in submit_slice
    assert "localStorage" not in middle_slice
    assert "sessionStorage" not in middle_slice
    for forbidden in (
        "download_url",
        "public_url",
        "signed_url:",
        "provider_credentials",
        "frontend_state",
        "browser_state",
    ):
        assert forbidden not in middle_slice


def test_layer3_analysis_environment_projection_rendered_reader_is_bounded() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    css = client.get("/review/layer3/static/layer3.css")

    assert js.status_code == 200
    assert css.status_code == 200
    helper_start = js.text.find("function currentAnalysisEnvironmentProjection")
    status_start = js.text.find("function analysisEnvironmentProjectionStatus")
    readiness_start = js.text.find("function analysisEnvironmentPlaneReadiness")
    model_start = js.text.find("function currentSublayerVisualizationModel")
    render_start = js.text.find("function renderAnalysisEnvironmentProjectionStatus")
    plane_start = js.text.find("function renderAnalysisPlane")
    source_family_start = js.text.find("function renderSourceFamilySummary")
    assert helper_start != -1
    assert status_start != -1
    assert readiness_start != -1
    assert model_start != -1
    assert render_start != -1
    assert plane_start != -1
    assert source_family_start != -1

    helper_slice = js.text[helper_start:status_start]
    status_slice = js.text[status_start:readiness_start]
    model_slice = js.text[model_start:render_start]
    render_slice = js.text[render_start:source_family_start]
    assert "State.sessionSummary?.analysis_environment_projection" in helper_slice
    assert "layer3.analysis_environment_projection.v1" in status_slice
    assert "analysis_environment_projection_missing" in status_slice
    assert "analysis_environment_projection_schema_invalid" in status_slice
    assert "analysis_environment_projection_not_read_only" in status_slice
    assert "analysisEnvironmentPlaneReadiness(" in model_slice
    assert "analysisEnvironmentProjectionStatus:" in model_slice
    assert 'class="analysis-environment-projection"' in render_slice
    assert "data-projection-available" in render_slice
    assert "forbidden_runtime_authority" in status_slice
    assert "projection_state" in status_slice
    assert "available_for_downstream_analysis" in status_slice
    assert "plane_readiness" in js.text
    assert "package_authority" not in helper_slice
    for forbidden in (
        "postJson(",
        "submitAttachmentForm(",
        "localStorage",
        "download_url",
        "public_url",
        "signed_url",
        "connector_run_id",
        "destination_id",
        "provider_credentials",
        "network_egress:",
        "package_mutation:",
        "source_promotion:",
        "vector_store:",
        "optional_tool:",
    ):
        assert forbidden not in render_slice

    assert ".analysis-environment-projection" in css.text
    assert ".analysis-environment-projection-head" in css.text
    assert 'data-projection-available="true"' in css.text


def test_layer3_analysis_product_inventory_projection_rendered_reader_is_bounded() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    css = client.get("/review/layer3/static/layer3.css")

    assert js.status_code == 200
    assert css.status_code == 200
    helper_start = js.text.find("function currentAnalysisProductInventoryProjection")
    status_start = js.text.find("function analysisProductInventoryProjectionStatus")
    render_start = js.text.find("function renderMockupAnalysisProductInventoryProjection")
    end_bound = js.text.find("function mockupOutputReviewPackageHandoffServerSources")
    assert helper_start != -1
    assert status_start != -1
    assert render_start != -1
    assert end_bound != -1
    assert helper_start < status_start < render_start < end_bound

    helper_slice = js.text[helper_start:status_start]
    status_slice = js.text[status_start:render_start]
    render_slice = js.text[render_start:end_bound]
    reader_block = js.text[helper_start:end_bound]

    assert "State.sessionSummary?.analysis_product_inventory_projection" in helper_slice
    assert "layer3.analysis_product_inventory_projection.v1" in status_slice
    assert "analysis_product_inventory_projection_missing" in status_slice
    assert "analysis_product_inventory_projection_schema_invalid" in status_slice
    assert "analysis_product_inventory_projection_not_read_only" in status_slice
    assert "inventory_state" in status_slice
    assert "product_count" in status_slice
    assert "package_product_count" in status_slice
    assert "downstream_eligibility" in status_slice
    assert "reconciliation" in status_slice
    assert 'class="mockup-analysis-product-inventory-projection-head"' in render_slice
    assert 'class="mockup-analysis-product-inventory-rollup"' in render_slice
    assert 'class="mockup-analysis-product-list"' in render_slice
    assert "data-product-class=" in render_slice
    assert "renderMockupAnalysisProductInventoryProjection(active)" in js.text
    assert "dataset.readOnly = 'true'" in render_slice
    # Safe ids and content/basis hashes (source_refs, provenance, payload_hash) are
    # intentionally surfaced in the per-product drill-down. Raw server-local refs/paths,
    # URLs, credentials, and any write/dispatch path remain forbidden.
    for forbidden in (
        "postJson(",
        "getJson(",
        "submitAttachmentForm(",
        "localStorage",
        "download_url",
        "public_url",
        "signed_url",
        "payload_ref",
        "output_payload_available",
        "connector_run_id",
        "destination_id",
        "provider_credentials",
        "network_egress:",
        "package_mutation:",
        "source_promotion:",
        "vector_store:",
        "optional_tool:",
    ):
        assert forbidden not in reader_block

    # Per-product drill-down: native <details> disclosure (no JS handlers) exposing
    # safe source refs / basis hashes. Assert both product-class branches render so a
    # dropped branch is caught: pass-run provenance + package basis hash.
    assert "<details" in reader_block
    assert "<summary>" in reader_block
    assert "mockup-analysis-product-detail-grid" in reader_block
    assert "source_refs" in reader_block
    assert "material_snapshot_ids" in reader_block
    assert "source_basis_hashes" in reader_block
    assert "payload_hash" in reader_block

    assert ".mockup-analysis-product-inventory-projection" in css.text
    assert ".mockup-analysis-product-inventory-projection-head" in css.text
    assert ".mockup-analysis-product-list" in css.text
    assert ".mockup-analysis-product-detail-grid" in css.text


def test_layer3_mockup_execution_lanes_projection_reader_is_bounded() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    css = client.get("/review/layer3/static/layer3.css")

    assert js.status_code == 200
    assert css.status_code == 200
    source_start = js.text.find("function mockupExecutionLanesServerSources")
    state_start = js.text.find("function mockupExecutionLanesSafeState")
    render_start = js.text.find("function renderMockupExecutionLanesLiveProjection")
    parse_start = js.text.find("async function parseResponse")
    assert source_start != -1
    assert state_start != -1
    assert render_start != -1
    assert parse_start != -1

    source_slice = js.text[source_start:state_start]
    render_slice = js.text[render_start:parse_start]
    for required in (
        "State.sessionSummary.sublayer_visualization",
        "State.sessionSummary.analysis_environment_projection",
        "State.sessionSummary.plan_preview",
        "State.sessionSummary.plan_approval",
        "State.sessionSummary.execution_selection",
        "State.sessionSummary.analysis_execution_start",
        "State.sessionSummary.execution_result_review",
        "State.planPreview",
        "State.planApproval",
        "State.executionSelection",
        "State.executionStart",
        "State.resultStatus",
        "State.resultReview",
    ):
        assert required in source_slice
    for required in (
        "currentSublayerVisualizationModel()",
        "mockup-execution-lanes-projection-head",
        "mockup-execution-lanes-live-grid",
        "mockup-execution-lane-plane-counts",
        "mockup-execution-lanes-source-list",
        "dataset.projectionState",
        "dataset.liveProjectionReadOnly = 'true'",
        "Read-only 3C server state projection pending",
    ):
        assert required in render_slice
    for forbidden in (
        "postJson(",
        "getJson(",
        "submitAttachmentForm(",
        "localStorage",
        "download_url",
        "public_url",
        "signed_url",
        "connector_run_id",
        "destination_id",
        "provider_credentials",
        "output_payload_ref",
        "diagnostics_ref",
        "package_payload",
        "raw_payload_path",
        "local_file_path",
        "source_directory",
        "vector_store",
        "optional_tool",
    ):
        assert forbidden not in render_slice

    assert ".mockup-execution-lanes-projection" in css.text
    assert ".mockup-execution-lanes-live-grid" in css.text
    assert ".mockup-execution-lane-plane-counts" in css.text
    assert ".mockup-execution-lanes-source-list" in css.text


def test_layer3_mockup_output_review_package_handoff_projection_reader_is_bounded() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    css = client.get("/review/layer3/static/layer3.css")

    assert js.status_code == 200
    assert css.status_code == 200
    source_start = js.text.find("function mockupOutputReviewPackageHandoffServerSources")
    state_start = js.text.find("function mockupOutputReviewPackageHandoffState")
    render_start = js.text.find("function renderMockupOutputReviewPackageHandoffProjection")
    parse_start = js.text.find("async function parseResponse")
    assert source_start != -1
    assert state_start != -1
    assert render_start != -1
    assert parse_start != -1

    source_slice = js.text[source_start:state_start]
    render_slice = js.text[source_start:parse_start]
    for required in (
        "State.resultStatus",
        "State.resultReview",
        "State.packageReviewPreview",
        "State.packageConstruction",
        "State.packageReviewSubmit",
        "State.packageSupersessionPreview",
        "State.replacementPackageSetAuthority",
        "State.packageSupersessionCommit",
        "State.replacementPackageArtifactManifest",
        "State.replacementPackageNamespace",
        "State.handoffExportPrepare",
        "State.apsHandoffDispatch",
        "State.externalExportDownloadPrepare",
        "State.externalExportDownloadDelivery",
        "State.externalExportDownloadSignedReference",
        "State.sessionSummary",
    ):
        assert required in source_slice
    for required in (
        "mockup-output-review-projection-head",
        "mockup-output-review-live-grid",
        "mockup-output-review-source-list",
        "dataset.outputReviewPackageHandoffProjectionState",
        "dataset.outputReviewPackageHandoffProjectionReadOnly = 'true'",
        "dataset.readOnly = 'true'",
        "Read-only output review package handoff projection pending",
        "Server output review package handoff projection unavailable",
    ):
        assert required in render_slice
    for forbidden in (
        "postJson(",
        "getJson(",
        "fetch(",
        "submitAttachmentForm(",
        "localStorage",
        "sessionStorage",
        "execution/result/status",
        "execution/result/review",
        "package/review",
        "package/mutation",
        "handoff/",
        "connector_run_id",
        "destination_id",
        "provider_credentials",
        "public_url",
        "signed_url",
        "raw_payload_path",
        "local_file_path",
        "browser_file",
        "file_bytes",
        "package_payload",
        "payload_ref",
        "download_url",
        "provider_url",
        "vector_store",
        "optional_tool",
    ):
        assert forbidden not in render_slice

    assert ".mockup-output-review-package-handoff-projection" in css.text
    assert ".mockup-output-review-live-grid" in css.text
    assert ".mockup-output-review-source-list" in css.text


def test_layer3_mockup_query_source_setup_projection_reader_is_bounded() -> None:
    js = client.get("/review/layer3/static/layer3.js")
    css = client.get("/review/layer3/static/layer3.css")

    assert js.status_code == 200
    assert css.status_code == 200
    helper_start = js.text.find("function mockupQuerySourceArrayCount")
    source_start = js.text.find("function mockupQuerySourceSetupServerSources")
    state_start = js.text.find("function mockupQuerySourceSetupState")
    render_start = js.text.find("function renderMockupQuerySourceSetupProjection")
    next_start = js.text.find("function mockupSublayersAbServerSources")
    assert helper_start != -1
    assert source_start != -1
    assert state_start != -1
    assert render_start != -1
    assert next_start != -1

    source_slice = js.text[source_start:state_start]
    render_slice = js.text[helper_start:next_start]
    for required in (
        "State.preflight",
        "State.sourcePreview",
        "State.materialPreview",
        "source-intake rendered control state",
        "source-directory rendered control state",
        "State.sessionSummary",
    ):
        assert required in source_slice
    for required in (
        "selectedSourceClasses()",
        "mockup-query-source-projection-head",
        "mockup-query-source-live-grid",
        "mockup-query-source-source-list",
        "dataset.querySourceProjectionState",
        "dataset.querySourceProjectionReadOnly = 'true'",
        "Read-only query/source setup projection pending",
        "Server query/source setup projection unavailable",
    ):
        assert required in render_slice
    for forbidden in (
        "postJson(",
        "getJson(",
        "fetch(",
        "submitAttachmentForm(",
        "localStorage",
        "sessionStorage",
        "source/intake/upload",
        "source/intake/inventory",
        "source/ingestion/server-configured-directory/scan",
        "source/ingestion/server-configured-directory/status",
        "gate-b/decision",
        "gate-c/preview",
        "package/",
        "handoff/",
        "connector_run_id",
        "destination_id",
        "provider_credentials",
        "public_url",
        "signed_url",
        "raw_payload_path",
        "local_file_path",
        "file_bytes",
        "browser_file",
        "vector_store",
        "optional_tool",
    ):
        assert forbidden not in render_slice

    assert ".mockup-query-source-setup-projection" in css.text
    assert ".mockup-query-source-live-grid" in css.text
    assert ".mockup-query-source-source-list" in css.text


def test_layer3_source_directory_ingestion_rendered_control_is_bounded() -> None:
    js = client.get("/review/layer3/static/layer3.js")

    assert js.status_code == 200
    payload_start = js.text.find("function sourceDirectoryIngestionPayload")
    forbidden_start = js.text.find("function sourceDirectoryIngestionForbiddenPayloadTerms")
    material_payload_start = js.text.find("function sourceDirectoryMaterialPreviewPayload")
    gate_b_basis_start = js.text.find("function sourceDirectoryGateBDecisionBasis")
    gate_b_payload_start = js.text.find("function sourceDirectoryGateBPayload")
    render_start = js.text.find("function renderDirectoryPanel")
    scan_start = js.text.find("async function scanSourceDirectory")
    status_start = js.text.find("async function inspectSourceDirectoryBatch")
    bind_start = js.text.find("function bindSourceDirectoryIngestionControls")
    assert payload_start != -1
    assert forbidden_start != -1
    assert material_payload_start != -1
    assert gate_b_basis_start != -1
    assert gate_b_payload_start != -1
    assert render_start != -1
    assert scan_start != -1
    assert status_start != -1
    assert bind_start != -1

    payload_slice = js.text[payload_start:forbidden_start]
    material_payload_slice = js.text[material_payload_start:gate_b_basis_start]
    gate_b_payload_slice = js.text[gate_b_payload_start:render_start]
    render_slice = js.text[render_start:scan_start]
    scan_slice = js.text[scan_start:status_start]
    status_slice = js.text[status_start:bind_start]
    assert "operator_decision: SOURCE_DIRECTORY_INGESTION_OPERATOR_DECISION" in payload_slice
    assert "source_family: SOURCE_DIRECTORY_INGESTION_SOURCE_FAMILY" in payload_slice
    assert "ingestion_mode: SOURCE_DIRECTORY_INGESTION_MODE" in payload_slice
    assert "postJson(SOURCE_DIRECTORY_INGESTION_SCAN_PATH" in scan_slice
    assert "getJson(`${SOURCE_DIRECTORY_INGESTION_STATUS_PATH_PREFIX}" in status_slice
    assert "SOURCE_DIRECTORY_MATERIAL_PREVIEW_PATH" in js.text
    assert "'/source/ingestion/server-configured-directory/material-preview'" in js.text
    assert "source_directory_ingestion_gate_b_material_admission" in js.text
    assert "source-directory-material-preview-button" in js.text
    assert "source-directory-gate-b-submit" in js.text
    assert "postJson(SOURCE_DIRECTORY_MATERIAL_PREVIEW_PATH" in js.text
    assert "postJson('/gate-b/decision'" in js.text
    assert "source_directory_gate_b_rendered_admission" in gate_b_payload_slice
    assert "persistSessionRecoveryAnchor('source_directory_gate_b_commit')" in js.text
    assert "source_root_absolute_path_exposed === false ? 'blocked'" in render_slice
    assert "preview.source_gate?.absolute_path_exposed === false ? 'blocked'" in js.text
    assert "preview.source_gate?.rag_vector_index_enabled === false ? 'blocked'" in js.text
    assert "preview.source_gate?.package_construction_enabled === false ? 'blocked'" in js.text
    assert "function directoryAuthorityStatus" in js.text
    assert "already_recorded: idempotent replay of existing server authority" in js.text
    assert "response schema:" in render_slice
    assert "response status:" in render_slice
    assert "idempotency:" in render_slice
    assert "payload.runtime_policy_id" in render_slice
    assert "payload.recursive_traversal_admitted" in render_slice
    assert "payload.max_recursion_depth" in render_slice
    assert "payload.max_relative_path_segments" in render_slice
    assert "payload.caller_selected_recursive_flag_allowed === false ? 'blocked'" in render_slice
    assert "invariants.caller_selected_recursive_flag_enabled === false ? 'blocked'" in render_slice
    assert "'caller_supplied_path'" in render_slice
    assert "'caller_selected_recursive_flag'" in render_slice
    assert "'browser_file_bytes'" in render_slice
    assert "'web_connector'" in render_slice
    assert "'rag_vector_index'" in render_slice
    assert "'frontend_durable_authority'" in render_slice
    for forbidden in (
        "path:",
        "paths:",
        "directory:",
        "local_path:",
        "url:",
        "urls:",
        "glob:",
        "recursive:",
        "file:",
        "files:",
        "file_bytes:",
        "rag_vector_index:",
        "web_connector:",
        "connector_run_id:",
        "provider_credentials:",
        "raw_vector:",
        "package_payload_rewrite:",
    ):
        assert forbidden not in payload_slice
        assert forbidden not in material_payload_slice


def test_layer3_sec_xbrl_runtime_posture_rendered_control_is_read_only() -> None:
    html = client.get("/review/layer3")
    js = client.get("/review/layer3/static/layer3.js")

    assert html.status_code == 200
    assert js.status_code == 200
    assert 'id="sec-xbrl-runtime-posture-panel"' in html.text
    assert 'data-rendered-mode="rendered_sec_xbrl_runtime_posture_projection_control"' in html.text
    assert 'data-read-only="true"' in html.text
    assert 'data-value-reveal-enabled="false"' in html.text
    assert 'data-delivery-export-enabled="false"' in html.text
    assert 'data-source-acquisition-enabled="false"' in html.text
    assert 'data-arelle-invocation-enabled="false"' in html.text
    assert 'data-runtime-default-enabled="false"' in html.text
    assert 'data-production-readiness-claimed="false"' in html.text

    rows_start = js.text.find("function secXbrlRuntimePostureRows")
    surface_helper_start = js.text.find("function secXbrlRuntimePostureActivationSurfaceItems")
    render_start = js.text.find("function renderSecXbrlRuntimePosturePanel")
    async_start = js.text.find("async function inspectSecXbrlRuntimePosture")
    workflow_async_start = js.text.find("async function inspectSecXbrlOperatorReviewWorkflowStatus")
    assert rows_start != -1
    assert surface_helper_start != -1
    assert render_start != -1
    assert async_start != -1
    assert workflow_async_start != -1

    surface_helper_slice = js.text[surface_helper_start:rows_start]
    rows_slice = js.text[rows_start:render_start]
    render_slice = js.text[render_start:async_start]
    async_slice = js.text[async_start:workflow_async_start]
    assert "const SEC_XBRL_RUNTIME_POSTURE_RENDERED_MODE = 'rendered_sec_xbrl_runtime_posture_projection_control'" in js.text
    assert "const SEC_XBRL_RUNTIME_POSTURE_ENDPOINT = '/sec-xbrl/runtime/posture'" in js.text
    assert "sec_xbrl_runtime_posture" in async_slice
    assert "getJson(SEC_XBRL_RUNTIME_POSTURE_ENDPOINT)" in async_slice
    assert "postJson" not in async_slice
    assert "data-read-only=\"true\"" in render_slice
    assert "data-value-reveal-enabled=\"false\"" in render_slice
    assert "data-delivery-export-enabled=\"false\"" in render_slice
    assert "data-source-acquisition-enabled=\"false\"" in render_slice
    assert "data-arelle-invocation-enabled=\"false\"" in render_slice
    assert "data-runtime-default-enabled=\"false\"" in render_slice
    assert "data-production-readiness-claimed=\"false\"" in render_slice
    assert "sec-xbrl-runtime-posture-output-grid" in rows_slice
    assert "secXbrlRuntimePostureActivationSurfaceItems" in rows_slice
    assert "Activation Surfaces" in rows_slice
    assert "sec-xbrl-runtime-posture-activation-card" in rows_slice
    assert "current_posture_performs_side_effect" in surface_helper_slice
    assert "rendered_panel_id" in surface_helper_slice
    assert "api_routes" in surface_helper_slice
    assert "required_configuration" in surface_helper_slice
    assert "production readiness claimed" in rows_slice
    assert "source acquisition performed" in rows_slice
    assert "Arelle invoked" in rows_slice
    assert "value reveal performed" in rows_slice
    assert "raw operator identity exposed" in rows_slice
    assert "raw value exposed" in rows_slice
    for forbidden in (
        "sidecar_receipt_id:",
        "dataset_version_id:",
        "value_store_hash:",
        "source_acquisition_request:",
        "operator_identity:",
        "raw_value:",
        "local_path:",
        "sec_url:",
        "runtime_default_override:",
    ):
        assert forbidden not in render_slice
        assert forbidden not in async_slice


def test_layer3_sec_xbrl_controlled_value_reveal_rendered_control_is_bounded() -> None:
    html = client.get("/review/layer3")
    js = client.get("/review/layer3/static/layer3.js")

    assert html.status_code == 200
    assert js.status_code == 200
    assert 'id="sec-xbrl-controlled-value-reveal-panel"' in html.text
    assert 'data-rendered-mode="rendered_sec_xbrl_controlled_value_reveal_ui_control"' in html.text
    assert 'data-controlled-value-reveal-only="true"' in html.text
    assert 'data-delivery-export-enabled="false"' in html.text
    assert 'data-source-acquisition-enabled="false"' in html.text
    assert 'data-arelle-invocation-enabled="false"' in html.text
    assert 'data-runtime-default-enabled="false"' in html.text
    assert 'data-production-readiness-claimed="false"' in html.text

    authority_payload_start = js.text.find("function secXbrlValueRevealAuthorityPreparePayload")
    submit_payload_start = js.text.find("function secXbrlControlledValueRevealSubmitPayload")
    status_path_start = js.text.find("function secXbrlControlledValueRevealStatusPath")
    render_start = js.text.find("function renderSecXbrlControlledValueRevealPanel")
    async_start = js.text.find("async function prepareSecXbrlValueRevealAuthority")
    submit_async_start = js.text.find("async function submitSecXbrlControlledValueReveal")
    assert authority_payload_start != -1
    assert submit_payload_start != -1
    assert status_path_start != -1
    assert render_start != -1
    assert async_start != -1
    assert submit_async_start != -1

    authority_payload_slice = js.text[authority_payload_start:submit_payload_start]
    submit_payload_slice = js.text[submit_payload_start:status_path_start]
    status_path_slice = js.text[status_path_start:render_start]
    render_slice = js.text[render_start:async_start]
    async_slice = js.text[async_start:submit_async_start]
    assert "const SEC_XBRL_LOWERCASE_SHA256_RE = /^[0-9a-f]{64}$/" in js.text
    assert "const SEC_XBRL_RAW_ACCESSION_RE = /\\b\\d{10}-\\d{2}-\\d{6}\\b/" in js.text
    assert "const SEC_XBRL_RAW_CIK_RE = /\\b\\d{10}\\b/" in js.text
    assert "authority_mode: SEC_XBRL_VALUE_REVEAL_AUTHORITY_MODE" in authority_payload_slice
    assert "operator_decision: SEC_XBRL_VALUE_REVEAL_AUTHORITY_OPERATOR_DECISION" in authority_payload_slice
    assert "sec_xbrl_operator_review_decision_id: values.decisionId" in authority_payload_slice
    assert "decision_basis_hash: values.decisionBasisHash" in authority_payload_slice
    assert "operator_attestation" in authority_payload_slice
    assert "SEC_XBRL_LOWERCASE_SHA256_RE.test(values.decisionBasisHash)" in authority_payload_slice
    assert "secXbrlValueRevealAttestationLooksRaw(values.operatorAttestation)" in authority_payload_slice
    assert "submit_mode: SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_MODE" in submit_payload_slice
    assert "operator_decision: SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_OPERATOR_DECISION" in submit_payload_slice
    assert "sec_xbrl_value_reveal_authority_receipt_id: values.authorityReceiptId" in submit_payload_slice
    assert "authority_basis_hash: values.authorityBasisHash" in submit_payload_slice
    assert "operator_reveal_confirmation: true" in submit_payload_slice
    assert "SEC_XBRL_LOWERCASE_SHA256_RE.test(values.authorityBasisHash)" in submit_payload_slice
    assert "getJson(path)" in js.text
    assert "SEC_XBRL_CONTROLLED_VALUE_REVEAL_STATUS_ENDPOINT_PREFIX" in status_path_slice
    assert "secXbrlControlledValueRevealStatusReceiptIdLooksRaw(values.submitReceiptId)" in status_path_slice
    assert "data-status-values-rendered=\"false\"" in render_slice
    assert "data-delivery-export-enabled=\"false\"" in render_slice
    assert "data-source-acquisition-enabled=\"false\"" in render_slice
    assert "data-arelle-invocation-enabled=\"false\"" in render_slice
    assert "data-runtime-default-enabled=\"false\"" in render_slice
    assert "State.secXbrlControlledValueRevealSubmit = null" in async_slice
    assert "State.secXbrlControlledValueRevealStatus = null" in async_slice
    assert "applySecXbrlControlledValueRevealAuthorityInputState(authority)" in async_slice
    assert "operatorRevealConfirmation: false" in js.text
    assert "statusReceiptInput.value = ''" in js.text
    for forbidden in (
        "sidecar_receipt_id:",
        "sidecar_receipt_hash:",
        "dataset_version_id:",
        "dataset_version_hash:",
        "value_store_hash:",
        "source_acquisition_request:",
        "arelle:",
        "export:",
        "delivery:",
        "default_on:",
    ):
        assert forbidden not in authority_payload_slice
        assert forbidden not in submit_payload_slice


def test_layer3_legacy_arelle_value_reveal_rendered_ui_is_disabled() -> None:
    js = client.get("/review/layer3/static/layer3.js")

    assert js.status_code == 200
    assert "const SEC_EDGAR_ARELLE_VALUE_REVEAL_RENDERED_UI_ENABLED = false;" in js.text

    can_reveal_start = js.text.find("function canRevealSecEdgarArelleValues")
    render_start = js.text.find("function renderSecEdgarOperatorProductSurfacePanel")
    update_start = js.text.find("function updateSecEdgarOperatorProductSurfaceControls")
    async_start = js.text.find("async function revealSecEdgarArelleValues")
    archive_start = js.text.find("async function inspectSecEdgarDurableDeliveryArchiveStatus")
    assert can_reveal_start != -1
    assert render_start != -1
    assert update_start != -1
    assert async_start != -1
    assert archive_start != -1

    can_reveal_slice = js.text[can_reveal_start:render_start]
    render_slice = js.text[render_start:update_start]
    async_slice = js.text[async_start:archive_start]
    assert "SEC_EDGAR_ARELLE_VALUE_REVEAL_RENDERED_UI_ENABLED" in can_reveal_slice
    assert 'data-rendered-value-reveal-enabled="false"' in render_slice
    assert 'data-controlled-value-reveal-replacement="true"' in render_slice
    assert 'fieldset disabled data-legacy-sibling-reveal-rendered-disabled="true"' in render_slice
    assert 'id="sec-edgar-arelle-value-reveal-submit" type="submit" disabled' in render_slice
    assert "sec_edgar_arelle_value_reveal_rendered_ui_replaced_by_controlled_submit" in async_slice
    assert "SEC_EDGAR_ARELLE_VALUE_REVEAL_ENDPOINT" in async_slice
    assert async_slice.find("sec_edgar_arelle_value_reveal_rendered_ui_replaced_by_controlled_submit") < async_slice.find(
        "SEC_EDGAR_ARELLE_VALUE_REVEAL_ENDPOINT"
    )


def test_layer3_shell_does_not_remove_adjacent_review_pages() -> None:
    assert client.get("/review/nrc-aps").status_code == 200
    assert client.get("/review/nrc-aps/workbench-compare").status_code == 200
    assert client.get("/review/nrc-aps/candidate-b-trace").status_code == 200
    assert client.get("/review/analyst-insight").status_code == 200


def test_layer3_public_dataset_version_is_hidden_and_bootstrap_flag_gated() -> None:
    html = client.get("/review/layer3")
    js = client.get("/review/layer3/static/layer3.js")

    assert html.status_code == 200
    assert js.status_code == 200
    assert '<section id="public-sciencebase-panel"' in html.text
    assert '<div id="public-sciencebase-connector-form"' in html.text
    assert '<form id="public-sciencebase-connector-form"' not in html.text
    assert '<button id="public-sciencebase-retrieve"' in html.text
    assert 'id="public-sciencebase-retrieve" class="secondary-btn" type="button"' in html.text
    panel_start = html.text.find('<section id="public-sciencebase-panel"')
    panel_end = html.text.find('>', panel_start)
    assert panel_start != -1
    assert panel_end != -1
    assert ' hidden ' in f" {html.text[panel_start:panel_end]} "
    for required in (
        'id="public-sciencebase-connector-form"',
        'id="public-sciencebase-retrieve"',
        'id="public-sciencebase-dataset-version-candidates"',
        'id="public-sciencebase-dataset-version-ids"',
        'id="public-sciencebase-run-status"',
    ):
        assert required in html.text

    state_start = js.text.find("const State = {")
    state_end = js.text.find("};", state_start)
    gate_start = js.text.find("function publicScienceBaseControlsEnabled")
    gate_end = js.text.find("function ", gate_start + 1)
    init_start = js.text.find("async function init()")
    init_end = js.text.find("if (elements.themeSelector)", init_start)
    assert state_start != -1
    assert state_end != -1
    assert gate_start != -1
    assert gate_end != -1
    assert init_start != -1
    assert init_end != -1

    state_slice = js.text[state_start:state_end]
    gate_slice = js.text[gate_start:gate_end]
    init_slice = js.text[init_start:init_end]
    assert "publicDatasetVersionCandidates" in state_slice
    assert "publicScienceBaseRun" in state_slice
    assert "publicScienceBaseControlsEnabled" in gate_slice
    assert "State.bootstrap?.layer3_public_dataset_analysis_enabled === true" in gate_slice
    assert "value_reveal" not in gate_slice
    assert "if (publicScienceBaseControlsEnabled())" in init_slice
    assert "loadPublicDatasetVersionCandidates()" in init_slice
    assert "loadPublicScienceBaseRunTargets" not in init_slice


def test_layer3_public_sciencebase_connector_uses_api_root_and_bounded_status_projection() -> None:
    js = client.get("/review/layer3/static/layer3.js")

    assert js.status_code == 200
    connector_start = js.text.find("const CONNECTOR_API_ROOT = '/api/v1';")
    payload_start = js.text.find("function publicScienceBaseConnectorPayload")
    status_start = js.text.find("function renderPublicScienceBaseRunStatus")
    targets_start = js.text.find("async function loadPublicScienceBaseRunTargets")
    bind_start = js.text.find("function bindPublicScienceBaseControls")
    assert connector_start != -1
    assert payload_start != -1
    assert status_start != -1
    assert targets_start != -1
    assert bind_start != -1

    connector_slice = js.text[connector_start:payload_start]
    payload_slice = js.text[payload_start:status_start]
    status_slice = js.text[status_start:targets_start]
    targets_slice = js.text[targets_start:bind_start]
    for required in (
        "'/connectors/sciencebase-public/runs'",
        "'/connectors/runs/'",
        "PUBLIC_CONNECTOR_TARGETS_PATH",
        "devInjectedFetchHeaders()",
        "PUBLIC_CONNECTOR_TERMINAL_STATUSES",
        "PUBLIC_CONNECTOR_MAX_POLLS",
        "PUBLIC_CONNECTOR_STALE_RUN_MS",
    ):
        assert required in connector_slice or required in targets_slice
    assert "const PUBLIC_CONNECTOR_MAX_POLLS = 300;" in connector_slice
    for required in (
        "q:",
        "scope_mode:",
        "scope_values:",
        "filters:",
        "postConnectorJson(",
        "PUBLIC_SCIENCEBASE_RUNS_PATH",
    ):
        assert required in payload_slice
    for required in (
        "current_phase",
        "discovered_count",
        "downloaded_count",
        "ingested_count",
        "recommended_count",
        "stale",
    ):
        assert required in status_slice
    assert "materialized_count" not in status_slice
    assert "admitted_count" not in status_slice
    for forbidden in ("raw_value", "numeric_value", "data_value", "values:"):
        assert forbidden not in status_slice
    assert "getConnectorJson(" in js.text
    assert "PUBLIC_CONNECTOR_RUN_PATH" in js.text
    assert "getConnectorJson(" in targets_slice
    assert "PUBLIC_CONNECTOR_TARGETS_PATH" in targets_slice
    assert "/targets" in targets_slice
    assert "if (PUBLIC_CONNECTOR_TERMINAL_STATUSES.has(terminalStatus))" in js.text
    assert "terminalStatus === 'completed' || terminalStatus === 'completed_with_errors'" in js.text


def test_layer3_public_dataset_selection_refreshes_admitted_ids_without_gate_approval() -> None:
    js = client.get("/review/layer3/static/layer3.js")

    assert js.status_code == 200
    load_start = js.text.find("async function loadPublicDatasetVersionCandidates")
    select_start = js.text.find("function selectPublicDatasetVersionCandidate")
    render_start = js.text.find("function renderPublicDatasetVersionCandidates")
    next_start = js.text.find("function ", render_start + 1)
    bind_start = js.text.find("function bindPublicScienceBaseControls")
    assert load_start != -1
    assert select_start != -1
    assert render_start != -1
    assert bind_start != -1
    assert next_start != -1

    load_slice = js.text[load_start:select_start]
    select_slice = js.text[select_start:render_start]
    render_slice = js.text[render_start:bind_start]
    assert "'/public-dataset-version-candidates'" in load_slice
    assert "source_admission_state === 'admitted_materialized_dataset_version'" in js.text
    assert "dataset_version_id" in select_slice
    assert "syncPublicDatasetVersionSelection()" in select_slice
    assert "elements.datasetVersionIds.value" in js.text
    assert "gateB" not in select_slice
    assert "planApprove" not in select_slice
    assert "renderPublicScienceBaseRunStatus" in render_slice
    assert "public-dataset-version-candidate" in render_slice
    assert "source_admission_state" in render_slice
    assert "publicScienceBaseRetrieve.addEventListener('click'" in js.text


def test_layer3_public_picker_is_tied_to_run_targets_and_not_aps_labeled() -> None:
    js = client.get("/review/layer3/static/layer3.js")

    assert js.status_code == 200
    target_helper_start = js.text.find("function publicScienceBaseRunTargetDatasetVersionIds")
    render_start = js.text.find("function renderPublicDatasetVersionCandidates")
    render_end = js.text.find("function renderPublicScienceBasePanel", render_start)
    labels_start = js.text.find("function selectedSourceClassLabels")
    labels_end = js.text.find("function currentIntentText", labels_start)
    sync_start = js.text.find("function syncPublicDatasetVersionSelection")
    sync_end = js.text.find("async function retrievePublicScienceBaseRun", sync_start)
    targets_start = js.text.find("async function loadPublicScienceBaseRunTargets")
    targets_end = js.text.find("function parseDatasetVersionIds", targets_start)
    assert target_helper_start != -1
    assert render_start != -1
    assert render_end != -1
    assert labels_start != -1
    assert labels_end != -1
    assert sync_start != -1
    assert sync_end != -1
    assert targets_start != -1
    assert targets_end != -1

    target_helper_slice = js.text[target_helper_start:render_start]
    render_slice = js.text[render_start:render_end]
    labels_slice = js.text[labels_start:labels_end]
    sync_slice = js.text[sync_start:sync_end]
    targets_slice = js.text[targets_start:targets_end]
    assert "State.publicScienceBaseRunTargets?.targets" in target_helper_slice
    assert "target.dataset_version_id" in target_helper_slice
    assert "targetDatasetVersionIds" in render_slice
    assert "targetDatasetVersionIds.has(String(candidate.dataset_version_id" in render_slice
    assert "State.publicScienceBaseSelectedIds" in labels_slice
    assert ".filter((id) => !selectedPublicIds.has(id))" in labels_slice
    assert "APS-derived DatasetVersion ID" in labels_slice
    assert "ScienceBase-derived public DatasetVersion ID" in labels_slice
    assert "clearLayer3FlowStateForSourceChange()" in sync_slice
    assert "?limit=500&offset=${offset}" in targets_slice
    assert "offset < total" in targets_slice


def test_layer3_public_sciencebase_value_reveal_markup_and_two_flag_gate() -> None:
    html = client.get("/review/layer3")
    js = client.get("/review/layer3/static/layer3.js")
    css = client.get("/review/layer3/static/layer3.css")

    assert html.status_code == 200
    assert js.status_code == 200
    assert css.status_code == 200
    panel_start = html.text.find('<section id="public-sciencebase-panel"')
    panel_end = html.text.find("</section>", panel_start)
    assert panel_start != -1
    assert panel_end != -1
    panel_slice = html.text[panel_start:panel_end]
    for required in (
        'id="public-sciencebase-values-inspect"',
        'type="button"',
        "Inspect result values",
        'id="public-sciencebase-values-status"',
        'id="public-sciencebase-values"',
        'class="public-sciencebase-values"',
    ):
        assert required in panel_slice
    assert "No dataset values are rendered here." not in panel_slice
    assert "both public-analysis and value-reveal gates" in panel_slice
    assert '<a ' not in panel_slice
    assert '<img ' not in panel_slice
    assert " download" not in panel_slice
    assert ".public-sciencebase-values[hidden]" in css.text
    assert "display: none;" in css.text[css.text.find(".public-sciencebase-values[hidden]"):][:120]

    gate_slice = _js_slice(
        js.text,
        "function publicScienceBaseValueRevealEnabled",
        "function publicScienceBaseLineValues",
    )
    assert "State.bootstrap?.layer3_public_dataset_analysis_enabled === true" in gate_slice
    assert "State.bootstrap?.layer3_public_connector_value_reveal_enabled === true" in gate_slice
    assert "publicScienceBaseControlsEnabled()" not in gate_slice
    state_slice = _js_slice(js.text, "const State = {", "const elements = {")
    for required in (
        "publicScienceBaseValues:",
        "publicScienceBaseValuesError:",
        "publicScienceBaseValuesPending:",
        "publicScienceBaseValuesRequestToken:",
    ):
        assert required in state_slice
    for required in (
        "publicScienceBaseValuesInspect:",
        "publicScienceBaseValuesStatus:",
        "publicScienceBaseValues:",
    ):
        assert required in js.text
    assert "max_items: 25" in js.text
    assert "max_files: 1" in js.text


def test_layer3_public_sciencebase_value_reveal_uses_exact_authority_and_safe_renderer() -> None:
    js = client.get("/review/layer3/static/layer3.js")

    assert js.status_code == 200
    payload_slice = _js_slice(
        js.text,
        "function publicScienceBaseResultValuesPayload",
        "function resultReviewPayload",
    )
    assert payload_slice.count("session_id:") == 1
    assert payload_slice.count("analysis_plan_id:") == 1
    assert payload_slice.count("pass_run_id:") == 1
    assert payload_slice.count("preview_id:") == 1
    assert payload_slice.count("preview_hash:") == 1
    for forbidden in ("client_request_id", "analysis_run_id", "operator_view_mode"):
        assert forbidden not in payload_slice

    render_slice = _js_slice(
        js.text,
        "function renderPublicScienceBaseValues",
        "function renderPublicScienceBasePanel",
    )
    for required in (
        "Values",
        "Provenance",
        "variable_profiles",
        "cross_correlation",
        "decomposition",
        "structural_break",
        "descriptive_summary",
        "sciencebase_item_id",
        "sciencebase_item_url",
        "sciencebase_download_uri",
        "sciencebase_file_name",
        "downloaded_sha256",
        "downloaded_at",
        "escapeHtml(",
        "fieldItem(",
        '<table class="material-table">',
        "<th>Variable</th>",
    ):
        assert required in render_slice
    for forbidden in (
        "Object.entries(State.publicScienceBaseValues",
        "storage_ref",
        "raw_storage_ref",
        "innerHTML = State.publicScienceBaseValues",
        "<a ",
        "<img ",
        "download=",
    ):
        assert forbidden not in render_slice

    inspect_slice = _js_slice(
        js.text,
        "async function inspectPublicScienceBaseResultValues",
        "async function inspectPackageReviewPreview",
    )
    for required in (
        "publicScienceBaseValueRevealEnabled()",
        "publicScienceBaseResultValuesPayload(authority)",
        "'/execution/result/public-values'",
        "State.publicScienceBaseValuesRequestToken",
        "publicScienceBaseAuthorityKey",
        "State.publicScienceBaseValues = result",
        "State.publicScienceBaseValues = null",
    ):
        assert required in inspect_slice

    values_clear_slice = _js_slice(
        js.text,
        "function clearPublicScienceBaseValuesState",
        "function clearResultReviewState",
    )
    assert "setBusy(elements.publicScienceBaseValuesInspect, false, 'Inspect result values')" in values_clear_slice
    assert "elements.publicScienceBaseValues.hidden = true" in values_clear_slice
    assert "elements.publicScienceBaseValues.innerHTML = ''" in values_clear_slice
    clear_slice = _js_slice(js.text, "function clearResultReviewState", "function selectedResultAuthority")
    assert "clearPublicScienceBaseValuesState()" in clear_slice
    panel_slice = _js_slice(js.text, "function renderPublicScienceBasePanel", "function bindPublicScienceBaseControls")
    assert "renderPublicScienceBaseValues()" in panel_slice
    assert "publicScienceBaseResultAuthorityKey(result)" in render_slice
    bind_slice = _js_slice(js.text, "function bindPublicScienceBaseControls", "async function loadApsContentDocumentCandidates")
    assert "publicScienceBaseValuesInspect.addEventListener('click', inspectPublicScienceBaseResultValues)" in bind_slice

    status_start = js.text.find("function renderPublicScienceBaseRunStatus")
    targets_start = js.text.find("async function loadPublicScienceBaseRunTargets")
    renderer_start = js.text.find("function renderPublicScienceBaseValues")
    assert -1 not in (status_start, targets_start, renderer_start)
    assert not status_start < renderer_start < targets_start
