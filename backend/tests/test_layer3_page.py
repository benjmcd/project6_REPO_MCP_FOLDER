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
    assert "layer3_workbench_theme" in response.text
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
    assert 'id="package-review-submit-form"' in response.text
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
    assert 'id="external-export-download-prepare-form"' in response.text
    assert 'id="external-export-download-prepare-panel"' in response.text
    assert 'id="external-export-download-prepare-submit"' in response.text
    assert 'id="external-export-download-delivery-form"' in response.text
    assert 'id="external-export-download-delivery-panel"' in response.text
    assert 'id="external-export-download-delivery-submit"' in response.text
    assert 'id="external-export-download-signed-reference-form"' in response.text
    assert 'id="external-export-download-signed-reference-panel"' in response.text
    assert 'id="external-export-download-signed-reference-generate"' in response.text
    assert 'id="external-export-download-signed-reference-use"' in response.text
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
    assert "mockup spec §8A plus one bounded APS content document trace sample" in claude.text
    assert "APS content document<br>selection" in claude.text
    assert "aps-doc-operator-evidence-001" in claude.text
    assert "ML26001A001" in claude.text
    assert "aps_content_units_v2" in claude.text
    assert "traceable_aps_content_document" in claude.text
    assert "No corpus-backed manual/custom specification loaded." in claude.text
    assert "const SPEC_CHIPS = [];" in claude.text
    assert "Manual spec choices are intentionally empty" in claude.text
    assert "String(MATERIALS.length)" in claude.text
    assert 'html[data-theme="workbench"]' in review_css.text
    assert ".authority-rail" in css.text
    assert "body.layer3-page" in css.text
    assert "overflow: visible" in css.text
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
    assert "const LAYER3_SESSION_RECOVERY_STORAGE_KEY = 'layer3_workbench_session_recovery_v1';" in js.text
    assert "const LAYER3_GATE_B_DRAFT_STORAGE_KEY = 'layer3_workbench_gate_b_draft_v1';" in js.text
    assert "LAYER3_SESSION_RECOVERY_SCHEMA_ID = 'layer3.browser_session_recovery.v1'" in js.text
    assert "LAYER3_GATE_B_DRAFT_SCHEMA_ID = 'layer3.gate_b_draft_snapshot.v1'" in js.text
    assert "function stateActionContractSignature" in js.text
    assert "state_action_contract_signature: stateActionContractSignature(State.sessionSummary)" in js.text
    assert "state_action_contract_signature: stateActionContractSignature()" in js.text
    assert "anchor.state_action_contract_signature !== currentContract" in js.text
    assert "draft.state_action_contract_signature !== currentContract" in js.text
    assert "isSharedThemePreference" in js.text
    assert "value === 'workbench'" in js.text
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
    assert "if (isQualitativeApsExternalExportDownloadState(external))" in js.text
    assert "deliveryUi.state === 'external_export_download_delivery_ui_ready'" in js.text
    assert "deliveryUi.state === 'associated_cohort_external_export_download_delivery_ui_ready'" in js.text
    assert "external_export_download_delivery_ui_unavailable" in js.text
    assert "external_export_download_signed_reference_ui_blocked" in js.text
    assert "if (!isAssociatedCohortExternalExportDownloadState(external))" in js.text
    assert "source_artifact_size_bytes ?? summary.source_artifact_size_bytes" not in js.text
    assert "deliveryUi.browser_managed_same_origin_attachment_enabled === true" in js.text
    assert "deliveryUi.public_url_enabled === false" in js.text
    assert ".blob()" not in js.text
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


def test_layer3_shell_does_not_remove_adjacent_review_pages() -> None:
    assert client.get("/review/nrc-aps").status_code == 200
    assert client.get("/review/nrc-aps/workbench-compare").status_code == 200
    assert client.get("/review/nrc-aps/candidate-b-trace").status_code == 200
    assert client.get("/review/analyst-insight").status_code == 200
