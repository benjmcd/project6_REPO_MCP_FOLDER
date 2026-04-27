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
    assert 'id="authority-rail"' in response.text
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
    assert 'href="/review/layer3/static/layer3.css"' in response.text
    assert 'src="/review/layer3/static/layer3.js"' in response.text
    assert "Plan</button>" in response.text
    assert "Execution</button>" in response.text
    assert "Results</button>" in response.text
    assert "Package</button>" in response.text
    assert "Handoff</button>" in response.text


def test_layer3_static_assets_are_mounted() -> None:
    css = client.get("/review/layer3/static/layer3.css")
    js = client.get("/review/layer3/static/layer3.js")

    assert css.status_code == 200
    assert js.status_code == 200
    assert ".authority-rail" in css.text
    assert "const API_ROOT = '/api/v1/layer3';" in js.text
    assert "postJson('/gate-b/decision'" in js.text
    assert "postJson('/gate-c/preview'" in js.text
    assert "postJson('/plan/preview'" in js.text
    assert "postJson('/plan/revise'" in js.text
    assert "postJson('/plan/approve'" in js.text
    assert "postJson('/package/review/preview'" in js.text
    assert "getJson(`/session/${encodeURIComponent(sessionId)}`)" in js.text
    assert "postJson('/execution/result/status'" in js.text
    assert "postJson('/execution/result/review'" in js.text
    assert "postJson('/package/review/commit'" in js.text
    assert "postJson('/package/review/submit'" in js.text
    assert "postJson('/handoff/export/prepare'" in js.text
    assert "postJson('/handoff/aps/dispatch'" in js.text
    assert "postJson('/handoff/export/download/prepare'" in js.text
    assert "postAttachment('/handoff/export/download/deliver'" in js.text
    assert "operator_view_mode: 'status_only'" in js.text
    assert "operator_decision: elements.resultReviewDecision.value" in js.text
    assert "operator_decision: elements.packageReviewSubmitDecision.value" in js.text
    assert "operator_decision: elements.handoffExportPrepareDecision.value" in js.text
    assert "operator_decision: 'dispatch_aps_handoff'" in js.text
    assert "operator_decision: 'prepare_external_export_download'" in js.text
    assert "operator_decision: 'deliver_external_export_download'" in js.text
    package_start = js.text.find("function packageReviewSubmitPayload")
    handoff_start = js.text.find("function handoffExportPreparePayload")
    aps_start = js.text.find("function apsHandoffDispatchPayload")
    external_start = js.text.find("function externalExportDownloadPreparePayload")
    delivery_start = js.text.find("function externalExportDownloadDeliveryPayload")
    refresh_start = js.text.find("async function refreshSessionSummary")
    assert package_start != -1
    assert handoff_start != -1
    assert aps_start != -1
    assert external_start != -1
    assert delivery_start != -1
    assert refresh_start != -1
    package_submit_slice = js.text[package_start:handoff_start]
    handoff_prepare_slice = js.text[handoff_start:aps_start]
    aps_dispatch_slice = js.text[aps_start:external_start]
    external_prepare_slice = js.text[external_start:delivery_start]
    external_delivery_slice = js.text[delivery_start:refresh_start]
    assert "handoff_target" not in package_submit_slice
    assert "export_mode" not in package_submit_slice
    assert "payload_refs" not in package_submit_slice
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


def test_layer3_shell_does_not_remove_adjacent_review_pages() -> None:
    assert client.get("/review/nrc-aps").status_code == 200
    assert client.get("/review/nrc-aps/workbench-compare").status_code == 200
    assert client.get("/review/nrc-aps/candidate-b-trace").status_code == 200
    assert client.get("/review/analyst-insight").status_code == 200
