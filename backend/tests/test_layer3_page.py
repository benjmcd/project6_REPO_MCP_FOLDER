from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app

client = TestClient(app)


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
    assert 'id="source-directory-hybrid-external-export-download-delivery-form"' in response.text
    assert (
        'data-rendered-mode="rendered_source_directory_hybrid_external_export_download_delivery_control"'
        in response.text
    )
    assert 'id="source-directory-hybrid-external-export-download-delivery-authority"' in response.text
    assert 'id="source-directory-hybrid-external-export-download-delivery-status"' in response.text
    assert 'id="source-directory-hybrid-external-export-download-delivery-submit"' in response.text
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
    claude = client.get("/review/layer3/static/claude.html")

    assert review_css.status_code == 200
    assert css.status_code == 200
    assert js.status_code == 200
    assert claude.status_code == 200
    js_text = js.text.replace("\r\n", "\n")
    assert "mockup spec §8A plus one bounded APS content document trace sample" in claude.text
    assert "APS content document<br>selection" in claude.text
    assert "aps-doc-operator-evidence-001" in claude.text
    assert "ML26001A001" in claude.text
    assert "aps_content_units_v2" in claude.text
    assert "traceable_aps_content_document" in claude.text
    assert "No corpus-backed manual/custom specification loaded." in claude.text
    assert "const SPEC_CHIPS = [];" in claude.text
    assert "Manual spec choices are intentionally empty" in claude.text
    assert "Manual source classes<br>and intent chips" not in claude.text
    assert "String(MATERIALS.length)" in claude.text
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
    assert "return sourceDirectoryPackageSupersessionPreviewState() || packageSupersessionPreviewState() || null" in js.text
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
    assert ".authority-matrix-review-panel" in css.text
    assert ".authority-matrix-review-grid" in css.text
    assert ".authority-matrix-review-rows" in css.text
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
    assert "postJson('/handoff/export/prepare'" in js.text
    assert "postJson('/handoff/aps/dispatch'" in js.text
    assert "postJson('/handoff/export/download/prepare'" in js.text
    assert "submitAttachmentForm('/handoff/export/download/deliver'" in js.text
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
    handoff_start = js.text.find("function handoffExportPreparePayload")
    aps_start = js.text.find("function apsHandoffDispatchPayload")
    external_start = js.text.find("function externalExportDownloadPreparePayload")
    delivery_start = js.text.find("function externalExportDownloadDeliveryPayload")
    refresh_start = js.text.find("async function refreshSessionSummary")
    assert review_start != -1
    assert review_end != -1
    assert package_start != -1
    assert handoff_start != -1
    assert aps_start != -1
    assert external_start != -1
    assert delivery_start != -1
    assert refresh_start != -1
    result_review_slice = js.text[review_start:review_end]
    package_submit_slice = js.text[package_start:handoff_start]
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
    assert "function nextSourceDirectoryPackageSupersessionPreviewRequestToken" in js_text
    assert "function isCurrentSourceDirectoryPackageSupersessionPreviewRequest" in js_text
    assert "nextSourceDirectoryPackageSupersessionPreviewRequestToken()" in clear_slice
    assert "const requestToken = nextSourceDirectoryPackageSupersessionPreviewRequestToken()" in source_submit_slice
    assert "if (!isCurrentSourceDirectoryPackageSupersessionPreviewRequest(requestToken)) return" in source_submit_slice
    assert "function isSourceDirectoryPackageSupersessionPreviewSelected" in state_slice
    assert "sourceDirectoryPackageSupersessionPreviewState() || packageSupersessionPreviewState() || null" in state_slice
    assert "SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_SOURCE_AUTHORITY" in state_slice
    assert "preview?.source_package_set_hash || preview?.package_set_hash || null" in state_slice
    assert "const preview = replacementPackageSetAuthorityPreviewState() || {}" in gate_slice
    assert "const sourcePackageSetHash = replacementPackageSetAuthoritySourcePackageSetHash(preview)" in gate_slice
    assert "sourceMode === 'source_directory_package_supersession_preview'" in gate_slice
    assert "preview.session_id" in gate_slice
    assert "&& sourcePackageSetHash" in gate_slice
    assert "!State.sourceDirectoryPackageSupersessionPreviewPending" in gate_slice
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


def test_layer3_shell_does_not_remove_adjacent_review_pages() -> None:
    assert client.get("/review/nrc-aps").status_code == 200
    assert client.get("/review/nrc-aps/workbench-compare").status_code == 200
    assert client.get("/review/nrc-aps/candidate-b-trace").status_code == 200
    assert client.get("/review/analyst-insight").status_code == 200
