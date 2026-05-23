from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from review_browser_fixture import capture_review_browser_patch_state, restore_review_browser_patches
from review_browser_server import create_app
from app.services import layer3_internal_webhook_connector
from app.services import layer3_pass_entry as layer3_pass_entry_module
from app.services import layer3_workbench as layer3_workbench_module


@pytest.fixture()
def client() -> Iterator[TestClient]:
    patch_state = capture_review_browser_patch_state()
    app = create_app()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        restore_review_browser_patches(patch_state)


def test_review_browser_server_restores_layer3_patch_state_after_app_creation() -> None:
    module_key = "app.services.nrc_aps_evidence_bundle"
    module_was_present = module_key in sys.modules
    original_aps_bundle_module = sys.modules.get(module_key)
    original_recommend_analysis = layer3_pass_entry_module.recommend_analysis
    original_run_analysis = layer3_pass_entry_module.run_analysis
    original_check_aps_handoff_compatibility = layer3_workbench_module.check_aps_handoff_compatibility
    original_materialize_aps_handoff = layer3_workbench_module.materialize_aps_handoff
    original_internal_webhook_transport = layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TRANSPORT
    patch_state = capture_review_browser_patch_state()
    app = None

    try:
        app = create_app()

        assert layer3_pass_entry_module.recommend_analysis is not original_recommend_analysis
        assert layer3_pass_entry_module.run_analysis is not original_run_analysis
        assert layer3_workbench_module.check_aps_handoff_compatibility is not original_check_aps_handoff_compatibility
        assert layer3_workbench_module.materialize_aps_handoff is not original_materialize_aps_handoff
        assert layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TRANSPORT is not original_internal_webhook_transport

        restore_review_browser_patches(patch_state)

        assert layer3_pass_entry_module.recommend_analysis is original_recommend_analysis
        assert layer3_pass_entry_module.run_analysis is original_run_analysis
        assert layer3_workbench_module.check_aps_handoff_compatibility is original_check_aps_handoff_compatibility
        assert layer3_workbench_module.materialize_aps_handoff is original_materialize_aps_handoff
        assert layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TRANSPORT is original_internal_webhook_transport
        if module_was_present:
            assert sys.modules[module_key] is original_aps_bundle_module
        else:
            assert module_key not in sys.modules
    finally:
        restore_review_browser_patches(patch_state)
        if app is not None:
            app.state.review_browser_temp_dir.cleanup()


def test_review_browser_server_health_and_compare_sources(client: TestClient) -> None:
    health_response = client.get("/health")
    sources_response = client.get("/api/v1/review/nrc-aps/workbench-compare/sources")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}

    assert sources_response.status_code == 200
    payload = sources_response.json()
    assert len(payload["baseline_runs"]) == 1
    assert len(payload["candidate_a_runs"]) == 1
    assert len(payload["candidate_b_bundles"]) == 1
    assert len(payload["candidate_b_runtime_runs"]) == 1
    assert payload["candidate_b_runtime_runs"][0]["runtime_binding"]["document_processing_engine"] == "candidate_b_opendataloader_pdf"
    assert "C:\\" not in str(payload)


def test_review_browser_server_harness_info_is_versioned_and_path_redacted(client: TestClient) -> None:
    response = client.get("/__test/harness-info")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_id"] == "project6.review_browser_harness_info.v1"
    assert payload["schema_version"] == 1
    assert payload["harness_name"] == "review_browser_server"
    assert payload["fixture_version"] == "review-browser-fixture-v1"
    assert payload["test_only"] is True
    assert payload["storage_mode"] == "temporary-redacted"
    assert payload["runtime_binding_count"] == 3
    assert payload["patch_groups"] == [
        "review-runtime-bindings",
        "workbench-compare",
        "candidate-b-trace",
        "layer3-deterministic-analysis",
        "layer3-aps-handoff",
    ]
    assert "/__test/layer3/seed-quant" in payload["seed_routes"]
    assert "/__test/layer3/seed-cohort-aps-handoff" in payload["seed_routes"]
    assert "/__test/layer3/candidate-b-readiness-audit" in payload["seed_routes"]
    assert "/__test/layer3/candidate-b-realistic-readiness-audit" in payload["seed_routes"]
    assert "/__test/layer3/candidate-b-final-proof" in payload["seed_routes"]
    windows_user_prefix = "C:" + "\\" + "Users" + "\\"
    posix_user_prefix = "/" + "Users" + "/"
    assert windows_user_prefix not in str(payload)
    assert posix_user_prefix not in str(payload)


def test_review_browser_server_prepares_candidate_b_readiness_audit(client: TestClient) -> None:
    setup_response = client.post("/__test/layer3/candidate-b-readiness-audit")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_candidate_b_readiness_audit_setup.v1"
    assert setup["test_only"] is True
    assert setup["server_generated_receipts"] is True
    assert setup["candidate_b_runtime_bridge_receipt_id"].startswith("cb-runtime-l3-")
    assert setup["readiness_audit_id"]
    assert setup["readiness_audit_hash"]
    assert setup["readiness_audit"]["status"] == "ready"
    assert setup["readiness_audit"]["readiness_audit_hash"] == setup["readiness_audit_hash"]
    assert setup["final_proof_request"] == {
        "client_request_id": "candidate-b-final-proof",
        "proof_mode": "candidate_b_default_promotion_final_proof_v1",
        "operator_decision": "record_candidate_b_default_promotion_final_proof",
        "readiness_audit": setup["readiness_audit"],
        "operator_confirmation": True,
    }
    proof_response = client.post(
        "/api/v1/layer3/source/ingestion/candidate-b/default-promotion/final-proof",
        json=setup["final_proof_request"],
    )
    assert proof_response.status_code == 200, proof_response.text
    proof = proof_response.json()
    assert proof["status"] == "proven"
    assert proof["readiness_audit_hash"] == setup["readiness_audit_hash"]
    assert proof["candidate_b_default_promotion_enabled"] is True
    assert proof["rollback_selector"] == "baseline"
    assert proof["selector_mutation_performed"] is False
    assert "C:\\" not in str(proof)


def test_review_browser_server_prepares_realistic_candidate_b_readiness_audit_from_fixture_sources(
    client: TestClient,
) -> None:
    setup_response = client.post("/__test/layer3/candidate-b-realistic-readiness-audit")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_candidate_b_realistic_readiness_audit_setup.v1"
    assert setup["test_only"] is True
    assert setup["server_generated_receipts"] is True
    assert setup["bridge_receipts_from_fixture_sources"] is True
    assert setup["candidate_b_bundle_id"] == "tests/reports/cb-compare-browser-test"
    assert setup["candidate_b_run_id"] == "candidate-b-runtime-001"
    assert setup["baseline_run_id"] == "baseline-run-001"
    assert setup["candidate_a_run_id"] == "candidate-a-run-001"
    assert setup["visual_lane_mode"] == "candidate_b_opendataloader_page_evidence_v1"
    assert setup["candidate_b_bundle_bridge_receipt_id"].startswith("cb-bundle-l3-")
    assert setup["candidate_b_runtime_bridge_receipt_id"].startswith("cb-runtime-l3-")
    assert setup["readiness_audit"]["status"] == "ready"
    assert setup["readiness_audit"]["readiness_audit_hash"] == setup["readiness_audit_hash"]
    assert setup["bundle_artifact_role_counts"]["material_analysis_payloads"] > 0
    assert setup["bundle_artifact_role_counts"]["visual_page_evidence"] > 0
    assert setup["bundle_artifact_role_counts"]["product_inspection_artifacts"] > 0
    assert setup["bundle_artifact_role_counts"]["delivery_artifacts"] > 0
    assert setup["runtime_artifact_role_counts"]["material_analysis_payloads"] > 0
    assert setup["runtime_artifact_role_counts"]["visual_page_evidence"] > 0
    assert setup["runtime_artifact_role_counts"]["product_inspection_artifacts"] > 0
    assert setup["runtime_artifact_role_counts"]["delivery_artifacts"] > 0
    assert setup["bundle_authority_hashes"]["governed_retained_artifact_family_hash"]
    assert setup["runtime_authority_hashes"]["governed_retained_artifact_family_hash"]
    assert setup["final_proof_request"] == {
        "client_request_id": "candidate-b-final-proof",
        "proof_mode": "candidate_b_default_promotion_final_proof_v1",
        "operator_decision": "record_candidate_b_default_promotion_final_proof",
        "readiness_audit": setup["readiness_audit"],
        "operator_confirmation": True,
    }
    assert "C:\\" not in str(setup)

    proof_response = client.post(
        "/api/v1/layer3/source/ingestion/candidate-b/default-promotion/final-proof",
        json=setup["final_proof_request"],
    )
    assert proof_response.status_code == 200, proof_response.text
    proof = proof_response.json()
    assert proof["status"] == "proven"
    assert proof["readiness_audit_hash"] == setup["readiness_audit_hash"]
    assert proof["candidate_b_default_promotion_enabled"] is True
    assert proof["rollback_selector"] == "baseline"
    assert proof["selector_mutation_performed"] is False
    assert "C:\\" not in str(proof)


def test_review_browser_server_prepares_candidate_b_final_proof_receipt(client: TestClient) -> None:
    setup_response = client.post("/__test/layer3/candidate-b-final-proof")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_candidate_b_final_proof_setup.v1"
    assert setup["test_only"] is True
    assert setup["server_generated_receipts"] is True
    assert setup["candidate_b_runtime_bridge_receipt_id"].startswith("cb-runtime-l3-")
    assert setup["proof_receipt_id"].startswith("cb-default-final-proof-")
    assert setup["proof_hash"]
    assert setup["readiness_audit_id"]
    assert setup["readiness_audit_hash"]
    assert setup["status_request"] == {
        "client_request_id": "candidate-b-final-proof-status",
        "status_mode": "candidate_b_default_promotion_final_proof_status_v1",
        "operator_decision": "inspect_candidate_b_default_promotion_final_proof_status",
        "candidate_b_runtime_bridge_receipt_id": setup["candidate_b_runtime_bridge_receipt_id"],
        "proof_receipt_id": setup["proof_receipt_id"],
    }
    status_response = client.post(
        "/api/v1/layer3/source/ingestion/candidate-b/default-promotion/final-proof/status",
        json=setup["status_request"],
    )
    assert status_response.status_code == 200, status_response.text
    status = status_response.json()
    assert status["status"] == "available"
    assert status["proof_hash"] == setup["proof_hash"]
    assert status["proof_receipt_id"] == setup["proof_receipt_id"]
    assert status["candidate_b_default_promotion_enabled"] is True
    assert status["rollback_selector"] == "baseline"
    assert status["selector_mutation_performed"] is False
    assert "C:\\" not in str(status)


def test_review_browser_server_runs_expose_candidate_b_runtime_metadata(client: TestClient) -> None:
    runs_response = client.get("/api/v1/review/nrc-aps/runs")

    assert runs_response.status_code == 200
    payload = runs_response.json()
    runs = payload["runs"]
    assert [run["display_label"] for run in runs] == [
        "Baseline Run",
        "Candidate A Run",
        "Candidate B Runtime",
    ]

    candidate_b = next(run for run in runs if run["run_id"] == "candidate-b-runtime-001")
    assert candidate_b["runtime_binding"]["visual_lane_mode"] == "candidate_b_opendataloader_page_evidence_v1"
    assert candidate_b["runtime_binding"]["document_processing_engine"] == "candidate_b_opendataloader_pdf"
    assert candidate_b["runtime_binding"]["variant_kind"] == "candidate_b_opendataloader_pdf"


def test_review_browser_server_candidate_b_trace_defaults_to_annotated_pdf(client: TestClient) -> None:
    sources_payload = client.get("/api/v1/review/nrc-aps/workbench-compare/sources").json()
    targets_payload = client.get(
        "/api/v1/review/nrc-aps/workbench-compare/targets",
        params={
            "baseline_run_id": sources_payload["baseline_runs"][0]["run_id"],
            "candidate_a_run_id": sources_payload["candidate_a_runs"][0]["run_id"],
            "candidate_b_bundle_id": sources_payload["candidate_b_bundles"][0]["bundle_id"],
        },
    ).json()
    assert [target["fixture_id"] for target in targets_payload["targets"]] == ["fontish", "ml17123a319"]
    assert targets_payload["default_fixture_id"] is None
    fixture_id = targets_payload["targets"][0]["fixture_id"]

    manifest_response = client.get(
        "/api/v1/review/nrc-aps/candidate-b-trace/manifest",
        params={
            "candidate_b_bundle_id": sources_payload["candidate_b_bundles"][0]["bundle_id"],
            "fixture_id": fixture_id,
        },
    )

    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["default_tab"] == "annotated_pdf"
    assert manifest["artifacts"]["annotated_pdf"].startswith("/api/v1/review/nrc-aps/candidate-b-trace/annotated-pdf?")
    assert "C:\\" not in str(manifest)

    second_manifest_response = client.get(
        "/api/v1/review/nrc-aps/candidate-b-trace/manifest",
        params={
            "candidate_b_bundle_id": sources_payload["candidate_b_bundles"][0]["bundle_id"],
            "fixture_id": targets_payload["targets"][1]["fixture_id"],
        },
    )
    assert second_manifest_response.status_code == 200
    second_manifest = second_manifest_response.json()
    assert second_manifest["fixture_id"] == "ml17123a319"
    assert second_manifest["artifacts"]["annotated_pdf"].startswith(
        "/api/v1/review/nrc-aps/candidate-b-trace/annotated-pdf?"
    )
    assert "C:\\" not in str(second_manifest)


def test_review_browser_server_document_trace_routes_use_isolated_runtime_fixture(client: TestClient) -> None:
    runs_response = client.get("/api/v1/review/nrc-aps/runs")
    assert runs_response.status_code == 200
    runs_payload = runs_response.json()
    run_id = runs_payload["default_run_id"]
    assert run_id

    documents_response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/documents")
    assert documents_response.status_code == 200
    documents_payload = documents_response.json()
    assert len(documents_payload["documents"]) == 2
    target_id = documents_payload["default_target_id"]
    assert target_id

    trace_response = client.get(f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/trace")
    assert trace_response.status_code == 200
    trace_manifest = trace_response.json()
    assert trace_manifest["source"]["viewer_kind"] == "pdf"
    assert trace_manifest["source"]["source_endpoint"].endswith("/source")
    assert trace_manifest["summary"]["ordered_unit_count"] == 1
    assert trace_manifest["summary"]["indexed_chunk_count"] == 1
    assert "C:\\" not in str(trace_manifest)

    source_response = client.get(trace_manifest["source"]["source_endpoint"])
    assert source_response.status_code == 200
    assert source_response.headers["content-type"].startswith("application/pdf")
    assert source_response.content.startswith(b"%PDF")

    extracted_units_response = client.get(
        f"/api/v1/review/nrc-aps/runs/{run_id}/documents/{target_id}/extracted-units"
    )
    assert extracted_units_response.status_code == 200
    extracted_units_payload = extracted_units_response.json()
    assert extracted_units_payload["available"] is True
    assert extracted_units_payload["total_unit_count"] == 1
    assert len(extracted_units_payload["units"]) == 1
    assert "C:\\" not in str(extracted_units_payload)
