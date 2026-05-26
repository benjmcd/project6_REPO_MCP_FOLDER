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
from app.core.config import settings
from app.services import layer3_internal_webhook_connector
from app.services import layer3_pass_entry as layer3_pass_entry_module
from app.services import layer3_sec_edgar_live_source_artifact
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
    original_sec_edgar_client = layer3_sec_edgar_live_source_artifact.SEC_EDGAR_CLIENT
    original_sec_edgar_sleep = layer3_sec_edgar_live_source_artifact.SEC_EDGAR_SLEEP
    original_sec_edgar_user_agent = settings.layer3_sec_edgar_user_agent
    original_sec_edgar_rate_limit = settings.layer3_sec_edgar_rate_limit_per_second
    patch_state = capture_review_browser_patch_state()
    app = None

    try:
        app = create_app()

        assert layer3_pass_entry_module.recommend_analysis is not original_recommend_analysis
        assert layer3_pass_entry_module.run_analysis is not original_run_analysis
        assert layer3_workbench_module.check_aps_handoff_compatibility is not original_check_aps_handoff_compatibility
        assert layer3_workbench_module.materialize_aps_handoff is not original_materialize_aps_handoff
        assert layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TRANSPORT is not original_internal_webhook_transport
        assert layer3_sec_edgar_live_source_artifact.SEC_EDGAR_CLIENT is app.state.sec_edgar_live_source_artifact_client
        assert layer3_sec_edgar_live_source_artifact.SEC_EDGAR_CLIENT is not original_sec_edgar_client
        assert layer3_sec_edgar_live_source_artifact.SEC_EDGAR_SLEEP is not original_sec_edgar_sleep

        restore_review_browser_patches(patch_state)

        assert layer3_pass_entry_module.recommend_analysis is original_recommend_analysis
        assert layer3_pass_entry_module.run_analysis is original_run_analysis
        assert layer3_workbench_module.check_aps_handoff_compatibility is original_check_aps_handoff_compatibility
        assert layer3_workbench_module.materialize_aps_handoff is original_materialize_aps_handoff
        assert layer3_internal_webhook_connector.INTERNAL_WEBHOOK_TRANSPORT is original_internal_webhook_transport
        assert layer3_sec_edgar_live_source_artifact.SEC_EDGAR_CLIENT is original_sec_edgar_client
        assert layer3_sec_edgar_live_source_artifact.SEC_EDGAR_SLEEP is original_sec_edgar_sleep
        assert settings.layer3_sec_edgar_user_agent == original_sec_edgar_user_agent
        assert settings.layer3_sec_edgar_rate_limit_per_second == original_sec_edgar_rate_limit
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
        "layer3-sec-edgar-live-source-artifact",
    ]
    assert "/__test/layer3/seed-quant" in payload["seed_routes"]
    assert "/__test/layer3/seed-cohort-aps-handoff" in payload["seed_routes"]
    assert "/__test/layer3/sec-edgar-live-source-artifact-acquisition" in payload["seed_routes"]
    assert "/__test/layer3/sec-edgar-source-acquisition-authority" in payload["seed_routes"]
    assert "/__test/layer3/sec-edgar-downstream-status" in payload["seed_routes"]
    assert "/__test/layer3/sec-edgar-live-downstream-status" in payload["seed_routes"]
    assert "/__test/layer3/sec-edgar-html-inline-xbrl-downstream-status" in payload["seed_routes"]
    assert "/__test/layer3/sec-edgar-html-inline-xbrl-fact-material-downstream-status" in payload["seed_routes"]
    assert "/__test/layer3/sec-edgar-live-repeatability-trial" in payload["seed_routes"]
    assert "/__test/layer3/sec-edgar-repeatability-trial" in payload["seed_routes"]
    assert "/__test/layer3/source-directory-fixture-reset" in payload["seed_routes"]
    assert "/__test/layer3/candidate-b-readiness-audit" in payload["seed_routes"]
    assert "/__test/layer3/candidate-b-realistic-readiness-audit" in payload["seed_routes"]
    assert "/__test/layer3/candidate-b-source-directory-authority" in payload["seed_routes"]
    assert "/__test/layer3/candidate-b-final-proof" in payload["seed_routes"]
    windows_user_prefix = "C:" + "\\" + "Users" + "\\"
    posix_user_prefix = "/" + "Users" + "/"
    assert windows_user_prefix not in str(payload)
    assert posix_user_prefix not in str(payload)


def test_review_browser_server_prepares_sec_edgar_live_source_artifact_acquisition(client: TestClient) -> None:
    setup_response = client.post("/__test/layer3/sec-edgar-live-source-artifact-acquisition")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_sec_edgar_live_source_artifact_acquisition_setup.v1"
    assert setup["test_only"] is True
    assert setup["acquisition_endpoint"] == (
        "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/acquire"
    )
    assert setup["status_endpoint_prefix"] == (
        "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/status/"
    )
    assert setup["raw_local_path_exposed"] is False
    assert setup["raw_url_exposed"] is False
    assert setup["artifact_bytes_exposed"] is False
    assert setup["server_user_agent_exposed"] is False
    assert setup["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(setup)
    assert "http://" not in str(setup)
    assert "https://" not in str(setup)
    patched_sec_client = layer3_sec_edgar_live_source_artifact.SEC_EDGAR_CLIENT
    first_request = setup["live_acquisition_request"]

    payload = {
        "client_request_id": "review-browser-sec-edgar-live-source-artifact",
        "acquisition_mode": "sec_edgar_text_table_live_source_artifact_acquisition_v1",
        "operator_decision": "acquire_sec_edgar_text_table_live_source_artifact",
        **setup["live_acquisition_request"],
        "operator_confirmation": True,
    }

    missing_confirmation_response = client.post(
        setup["acquisition_endpoint"],
        json={**payload, "operator_confirmation": False},
    )
    assert missing_confirmation_response.status_code == 409, missing_confirmation_response.text
    assert missing_confirmation_response.json()["error_code"] == (
        "sec_edgar_text_table_live_source_artifact_operator_confirmation_missing"
    )

    raw_url_response = client.post(
        setup["acquisition_endpoint"],
        json={**payload, "raw_url": "https://www.sec.gov/Archives/edgar/data/320193/raw.txt"},
    )
    assert raw_url_response.status_code == 400, raw_url_response.text
    assert raw_url_response.json()["error_code"] == "sec_edgar_text_table_live_source_artifact_forbidden_request_fields"
    assert "https://www.sec.gov" not in raw_url_response.text

    mismatch_response = client.post(
        setup["acquisition_endpoint"],
        json={**payload, "expected_content_sha256": "0" * 64},
    )
    assert mismatch_response.status_code == 409, mismatch_response.text
    assert mismatch_response.json()["error_code"] == "sec_edgar_text_table_live_source_artifact_content_hash_mismatch"

    setup_response = client.post("/__test/layer3/sec-edgar-live-source-artifact-acquisition")
    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert layer3_sec_edgar_live_source_artifact.SEC_EDGAR_CLIENT is patched_sec_client
    assert setup["expected_content_sha256"] != first_request["expected_content_sha256"]
    assert setup["live_acquisition_request"]["cik_or_filer_ref"] != first_request["cik_or_filer_ref"]
    assert setup["live_acquisition_request"]["accession_or_submission_id"] != first_request["accession_or_submission_id"]
    payload = {
        "client_request_id": "review-browser-sec-edgar-live-source-artifact-available",
        "acquisition_mode": "sec_edgar_text_table_live_source_artifact_acquisition_v1",
        "operator_decision": "acquire_sec_edgar_text_table_live_source_artifact",
        **setup["live_acquisition_request"],
        "operator_confirmation": True,
    }

    acquire_response = client.post(setup["acquisition_endpoint"], json=payload)
    assert acquire_response.status_code == 200, acquire_response.text
    acquired = acquire_response.json()
    assert acquired["schema_id"] == "layer3.sec_edgar_text_table_live_source_artifact_acquisition.v1"
    assert acquired["live_source_artifact_receipt_status"] == "available"
    assert acquired["source_artifact_receipt"]["content_sha256"] == setup["expected_content_sha256"]
    assert acquired["retained_source_artifact_manifest"]["retained_source_artifact_available"] is True
    assert acquired["cache"]["cache_status"] == "miss"
    assert acquired["cache"]["network_request_made"] is True
    assert acquired["idempotency"]["idempotent_replay"] is False
    assert acquired["operator_visible_live_source_artifact_status"]["raw_url_exposed"] is False
    assert acquired["operator_visible_live_source_artifact_status"]["raw_local_path_exposed"] is False
    assert acquired["operator_visible_live_source_artifact_status"]["artifact_bytes_exposed"] is False
    assert acquired["negative_invariants"]["frontend_durable_authority_enabled"] is False
    assert "Layer3 Review Browser" not in acquire_response.text
    assert "https://www.sec.gov" not in acquire_response.text
    assert "C:\\" not in acquire_response.text

    status_response = client.get(f"{setup['status_endpoint_prefix']}{acquired['live_source_artifact_receipt_id']}")
    assert status_response.status_code == 200, status_response.text
    status = status_response.json()
    assert status["schema_id"] == "layer3.sec_edgar_text_table_live_source_artifact_acquisition_status.v1"
    assert status["live_source_artifact_receipt_hash"] == acquired["live_source_artifact_receipt_hash"]
    assert status["cache"]["cache_status"] == "status"
    assert status["cache"]["network_request_made"] is False
    assert "Layer3 Review Browser" not in status_response.text
    assert "https://www.sec.gov" not in status_response.text
    assert "C:\\" not in status_response.text

    replay_response = client.post(
        setup["acquisition_endpoint"],
        json={**payload, "client_request_id": "review-browser-sec-edgar-live-source-artifact-replay"},
    )
    assert replay_response.status_code == 200, replay_response.text
    replay = replay_response.json()
    assert replay["cache"]["cache_status"] == "hit"
    assert replay["idempotency"]["idempotent_replay"] is True
    assert replay["live_source_artifact_receipt_hash"] == acquired["live_source_artifact_receipt_hash"]


def test_review_browser_server_prepares_sec_edgar_source_acquisition_authority(client: TestClient) -> None:
    setup_response = client.post("/__test/layer3/sec-edgar-source-acquisition-authority")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_sec_edgar_source_acquisition_authority_setup.v1"
    assert setup["test_only"] is True
    assert setup["dataset_version_id"].startswith("dv-sec-edgar-source-acq-")
    assert setup["source_acquisition_endpoint"] == (
        "/api/v1/layer3/source/sec-edgar/text-table/source-acquisition/authority"
    )
    assert setup["raw_local_path_exposed"] is False
    assert setup["raw_url_exposed"] is False
    assert setup["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(setup)
    assert "http://" not in str(setup)
    assert "https://" not in str(setup)

    missing_confirmation_response = client.post(
        setup["source_acquisition_endpoint"],
        json={**setup["source_acquisition_request"], "operator_confirmation": False},
    )
    assert missing_confirmation_response.status_code == 409, missing_confirmation_response.text
    assert missing_confirmation_response.json()["error_code"] == (
        "sec_edgar_text_table_source_acquisition_operator_confirmation_missing"
    )

    missing_receipt_request = dict(setup["source_acquisition_request"])
    missing_receipt_request.pop("source_artifact_receipt_id")
    missing_receipt_response = client.post(
        setup["source_acquisition_endpoint"],
        json=missing_receipt_request,
    )
    assert missing_receipt_response.status_code == 422, missing_receipt_response.text
    assert "source_artifact_receipt_id" in missing_receipt_response.text

    stale_response = client.post(
        setup["source_acquisition_endpoint"],
        json=setup["stale_source_acquisition_request"],
    )
    assert stale_response.status_code == 409, stale_response.text
    assert stale_response.json()["error_code"] == (
        "sec_edgar_text_table_source_acquisition_stale_or_mismatched_source_artifact_authority"
    )

    record_response = client.post(
        setup["source_acquisition_endpoint"],
        json=setup["source_acquisition_request"],
    )
    assert record_response.status_code == 200, record_response.text
    record = record_response.json()
    assert record["schema_id"] == "layer3.sec_edgar_text_table_source_acquisition_authority.v1"
    assert record["source_acquisition_authority_state"] == "available"
    assert record["source_acquisition_receipt_hash"] == setup["expected_source_acquisition_receipt_hash"]
    assert record["append_only_source_acquisition_authority_receipt"] is True
    assert record["operator_visible_source_acquisition_status"]["raw_url_exposed"] is False
    assert record["negative_invariants"]["sec_edgar_network_fetch_admitted"] is False
    assert record["negative_invariants"]["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(record)
    assert "http://" not in str(record)
    assert "https://" not in str(record)

    replay_response = client.post(
        setup["source_acquisition_endpoint"],
        json={**setup["source_acquisition_request"], "client_request_id": "review-browser-source-acq-replay"},
    )
    assert replay_response.status_code == 200, replay_response.text
    replay = replay_response.json()
    assert replay["idempotent_replay"] is True
    assert replay["source_acquisition_receipt_hash"] == record["source_acquisition_receipt_hash"]


def test_review_browser_server_prepares_sec_edgar_downstream_status_authority(client: TestClient) -> None:
    setup_response = client.post("/__test/layer3/sec-edgar-downstream-status")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_sec_edgar_downstream_status_setup.v1"
    assert setup["test_only"] is True
    assert setup["dataset_version_id"].startswith("dv-sec-edgar-status-")
    assert setup["expected_proof_hash"] == setup["proof_hash"]
    assert setup["status_endpoint"] == "/api/v1/layer3/source/sec-edgar/text-table/downstream-proof/status"
    assert setup["raw_local_path_exposed"] is False
    assert setup["raw_url_exposed"] is False
    assert setup["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(setup)

    status_response = client.post(
        setup["status_endpoint"],
        json={
            "client_request_id": "review-browser-sec-edgar-status",
            "status_mode": "sec_edgar_text_table_downstream_layer3_operator_status_v1",
            "operator_decision": "inspect_sec_edgar_text_table_downstream_layer3_operator_status",
            "downstream_proof_request": setup["downstream_proof_request"],
            "expected_proof_hash": setup["expected_proof_hash"],
        },
    )
    assert status_response.status_code == 200, status_response.text
    status = status_response.json()
    assert status["schema_id"] == "layer3.sec_edgar_text_table_downstream_operator_status.v1"
    assert status["operator_status_state"] == "available"
    assert status["proof_hash"] == setup["expected_proof_hash"]
    assert status["status_projection"]["server_revalidated"] is True
    assert status["raw_local_path_rendered"] is False
    assert status["raw_url_rendered"] is False
    assert status["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(status)


def test_review_browser_server_prepares_sec_edgar_live_downstream_status_authority(client: TestClient) -> None:
    setup_response = client.post("/__test/layer3/sec-edgar-live-downstream-status")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_sec_edgar_live_downstream_status_setup.v1"
    assert setup["test_only"] is True
    assert setup["dataset_version_id"].startswith("dv-sec-edgar-live-status-")
    assert setup["expected_proof_hash"] == setup["proof_hash"]
    assert setup["status_endpoint"] == (
        "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/downstream-proof/status"
    )
    assert setup["raw_local_path_exposed"] is False
    assert setup["raw_url_exposed"] is False
    assert setup["artifact_bytes_exposed"] is False
    assert setup["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(setup)
    assert "http://" not in str(setup)
    assert "https://" not in str(setup)

    status_response = client.post(
        setup["status_endpoint"],
        json={
            "client_request_id": "review-browser-sec-edgar-live-status",
            "status_mode": "sec_edgar_text_table_live_source_artifact_downstream_operator_status_v1",
            "operator_decision": "inspect_sec_edgar_text_table_live_source_artifact_downstream_operator_status",
            "live_downstream_proof_request": setup["live_downstream_proof_request"],
            "expected_proof_hash": setup["expected_proof_hash"],
        },
    )
    assert status_response.status_code == 200, status_response.text
    status = status_response.json()
    assert status["schema_id"] == "layer3.sec_edgar_text_table_live_source_artifact_downstream_operator_status.v1"
    assert status["operator_status_state"] == "available"
    assert status["proof_hash"] == setup["expected_proof_hash"]
    assert status["live_source_artifact_receipt_hash"] == setup["live_source_artifact_receipt_hash"]
    assert status["source_acquisition_receipt_hash"] == setup["source_acquisition_receipt_hash"]
    assert status["live_source_artifact_material_bridge_receipt_hash"] == (
        setup["live_source_artifact_material_bridge_receipt_hash"]
    )
    assert status["material_bridge_receipt_hash"] == setup["material_bridge_receipt_hash"]
    assert status["status_projection"]["server_revalidated"] is True
    assert status["status_projection"]["live_source_artifact_authority_bound"] is True
    assert status["status_projection"]["live_material_bridge_authority_bound"] is True
    assert status["raw_proof_receipt_path_rendered"] is False
    assert status["raw_local_path_rendered"] is False
    assert status["raw_url_rendered"] is False
    assert status["artifact_bytes_rendered"] is False
    assert status["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(status)
    assert "http://" not in str(status)
    assert "https://" not in str(status)


def test_review_browser_server_prepares_sec_edgar_html_inline_xbrl_downstream_status_authority(
    client: TestClient,
) -> None:
    setup_response = client.post("/__test/layer3/sec-edgar-html-inline-xbrl-downstream-status")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_sec_edgar_html_inline_xbrl_downstream_status_setup.v1"
    assert setup["test_only"] is True
    assert setup["dataset_version_id"].startswith("dv-sec-html-")
    assert setup["expected_proof_hash"] == setup["proof_hash"]
    assert setup["status_endpoint"] == "/api/v1/layer3/source/sec-edgar/html-inline-xbrl/downstream-proof/status"
    assert setup["raw_local_path_exposed"] is False
    assert setup["raw_url_exposed"] is False
    assert setup["artifact_bytes_exposed"] is False
    assert setup["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(setup)
    assert "http://" not in str(setup)
    assert "https://" not in str(setup)
    assert "aapl-20240928.htm" not in str(setup)
    assert "Company narrative" not in str(setup)

    status_response = client.post(
        setup["status_endpoint"],
        json={
            "client_request_id": "review-browser-sec-edgar-html-inline-xbrl-status",
            "status_mode": "sec_edgar_html_inline_xbrl_downstream_operator_status_v1",
            "operator_decision": "inspect_sec_edgar_html_inline_xbrl_downstream_operator_status",
            "html_inline_xbrl_downstream_proof_request": setup["html_inline_xbrl_downstream_proof_request"],
            "expected_proof_hash": setup["expected_proof_hash"],
        },
    )
    assert status_response.status_code == 200, status_response.text
    status = status_response.json()
    assert status["schema_id"] == "layer3.sec_edgar_html_inline_xbrl_downstream_operator_status.v1"
    assert status["operator_status_state"] == "available"
    assert status["proof_hash"] == setup["expected_proof_hash"]
    assert status["parser_receipt_hash"] == setup["parser_receipt_hash"]
    assert status["connector_receipt_hash"] == setup["connector_receipt_hash"]
    assert status["live_source_artifact_receipt_hash"] == setup["live_source_artifact_receipt_hash"]
    assert status["source_artifact_receipt_hash"] == setup["source_artifact_receipt_hash"]
    assert status["material_bridge_receipt_hash"] == setup["material_bridge_receipt_hash"]
    assert status["material_preview_hash"] == setup["material_preview_hash"]
    assert status["status_projection"]["server_revalidated"] is True
    assert status["status_projection"]["parser_authority_bound"] is True
    assert status["status_projection"]["material_bridge_authority_bound"] is True
    assert status["raw_proof_request_rendered"] is False
    assert status["raw_proof_receipt_path_rendered"] is False
    assert status["raw_local_path_rendered"] is False
    assert status["raw_url_rendered"] is False
    assert status["artifact_bytes_rendered"] is False
    assert status["provider_private_token_rendered"] is False
    assert status["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(status)
    assert "http://" not in str(status)
    assert "https://" not in str(status)
    assert "aapl-20240928.htm" not in str(status)
    assert "Company narrative" not in str(status)


def test_review_browser_server_prepares_sec_edgar_html_inline_xbrl_fact_material_downstream_status_authority(
    client: TestClient,
) -> None:
    setup_response = client.post("/__test/layer3/sec-edgar-html-inline-xbrl-fact-material-downstream-status")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert (
        setup["schema_id"]
        == "project6.review_browser_sec_edgar_html_inline_xbrl_fact_material_downstream_status_setup.v1"
    )
    assert setup["test_only"] is True
    assert setup["dataset_version_id"].startswith("dv-sec-ixbrl-facts-")
    assert setup["expected_proof_hash"] == setup["proof_hash"]
    assert setup["status_endpoint"] == (
        "/api/v1/layer3/source/sec-edgar/html-inline-xbrl/"
        "fact-authority/material-bridge/downstream-proof/status"
    )
    assert setup["raw_local_path_exposed"] is False
    assert setup["raw_url_exposed"] is False
    assert setup["artifact_bytes_exposed"] is False
    assert setup["raw_fact_values_rendered"] is False
    assert setup["fact_value_reconstruction_enabled"] is False
    assert setup["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(setup)
    assert "http://" not in str(setup)
    assert "https://" not in str(setup)
    assert "aapl-20240928.htm" not in str(setup)
    assert "Company narrative" not in str(setup)
    assert "value_text" not in str(setup)

    status_response = client.post(
        setup["status_endpoint"],
        json={
            "client_request_id": "review-browser-sec-edgar-html-inline-xbrl-fact-material-status",
            "status_mode": "sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status_v1",
            "operator_decision": "inspect_sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status",
            "fact_material_downstream_proof_request": setup["fact_material_downstream_proof_request"],
            "expected_proof_hash": setup["expected_proof_hash"],
        },
    )
    assert status_response.status_code == 200, status_response.text
    status = status_response.json()
    assert (
        status["schema_id"]
        == "layer3.sec_edgar_html_inline_xbrl_fact_material_downstream_operator_status.v1"
    )
    assert status["operator_status_state"] == "available"
    assert status["proof_hash"] == setup["expected_proof_hash"]
    assert status["parser_receipt_hash"] == setup["parser_receipt_hash"]
    assert status["connector_receipt_hash"] == setup["connector_receipt_hash"]
    assert status["live_source_artifact_receipt_hash"] == setup["live_source_artifact_receipt_hash"]
    assert status["source_artifact_receipt_hash"] == setup["source_artifact_receipt_hash"]
    assert status["fact_authority_receipt_hash"] == setup["fact_authority_receipt_hash"]
    assert status["fact_inventory_hash"] == setup["fact_inventory_hash"]
    assert status["diagnostics_hash"] == setup["diagnostics_hash"]
    assert status["fact_material_bridge_receipt_hash"] == setup["fact_material_bridge_receipt_hash"]
    assert status["material_bridge_receipt_hash"] == setup["fact_material_bridge_receipt_hash"]
    assert status["material_preview_hash"] == setup["material_preview_hash"]
    assert status["status_projection"]["server_revalidated"] is True
    assert status["status_projection"]["parser_authority_bound"] is True
    assert status["status_projection"]["fact_authority_bound"] is True
    assert status["status_projection"]["fact_material_bridge_authority_bound"] is True
    assert status["raw_proof_request_rendered"] is False
    assert status["raw_proof_receipt_path_rendered"] is False
    assert status["raw_local_path_rendered"] is False
    assert status["raw_url_rendered"] is False
    assert status["artifact_bytes_rendered"] is False
    assert status["raw_fact_values_rendered"] is False
    assert status["fact_value_reconstruction_enabled"] is False
    assert status["provider_private_token_rendered"] is False
    assert status["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(status)
    assert "http://" not in str(status)
    assert "https://" not in str(status)
    assert "aapl-20240928.htm" not in str(status)
    assert "Company narrative" not in str(status)
    assert "value_text" not in str(status)


def test_review_browser_server_prepares_sec_edgar_live_repeatability_trial_authority(
    client: TestClient,
) -> None:
    setup_response = client.post("/__test/layer3/sec-edgar-live-repeatability-trial")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_sec_edgar_live_repeatability_trial_setup.v1"
    assert setup["test_only"] is True
    assert setup["dataset_version_id"].startswith("dv-sec-edgar-live-status-")
    assert setup["original_operator_status_hash"] == setup["repeat_operator_status_hash"]
    assert setup["trial_endpoint"] == (
        "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/downstream/operator-repeatability/trial"
    )
    assert setup["status_endpoint"] == (
        "/api/v1/layer3/source/sec-edgar/text-table/live-source-artifact/downstream-proof/status"
    )
    assert setup["raw_local_path_exposed"] is False
    assert setup["raw_url_exposed"] is False
    assert setup["artifact_bytes_exposed"] is False
    assert setup["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(setup)
    assert "http://" not in str(setup)
    assert "https://" not in str(setup)

    trial_response = client.post(
        setup["trial_endpoint"],
        json={
            "client_request_id": "review-browser-sec-edgar-live-repeatability-trial",
            "trial_mode": (
                "append_only_trial_receipt_over_original_and_repeat_live_downstream_status_authority_"
                "without_sec_fetch_or_processing_execution"
            ),
            "operator_decision": (
                "record_sec_edgar_text_table_live_source_artifact_downstream_operator_repeatability_trial"
            ),
            "original_operator_status_request": setup["original_operator_status_request"],
            "original_operator_status_hash": setup["original_operator_status_hash"],
            "repeat_operator_status_request": setup["repeat_operator_status_request"],
            "repeat_operator_status_hash": setup["repeat_operator_status_hash"],
            "operator_repeatability_disposition": "no_regression_observed",
            "operator_confirmation": True,
        },
    )
    assert trial_response.status_code == 200, trial_response.text
    trial = trial_response.json()
    assert trial["schema_id"] == (
        "layer3.sec_edgar_text_table_live_source_artifact_downstream_operator_repeatability_trial.v1"
    )
    assert trial["operator_repeatability_trial_state"] == (
        "sec_edgar_text_table_live_source_artifact_downstream_operator_repeatability_trial_accepted"
    )
    assert trial["operator_status_hash_comparison"] == "match"
    assert trial["proof_hash_comparison"] == "match"
    assert trial["coverage_step_set_comparison"] == "match"
    assert trial["authority_bindings"]["live_source_artifact_receipt_hash"] == (
        setup["live_source_artifact_receipt_hash"]
    )
    assert trial["authority_bindings"]["source_acquisition_receipt_hash"] == (
        setup["source_acquisition_receipt_hash"]
    )
    assert trial["append_only_repeatability_trial_receipt"] is True
    assert trial["actual_sec_processing_execution_admitted"] is False
    assert trial["actual_subprocess_spawn_admitted"] is False
    assert trial["connector_dispatch_enabled"] is False
    assert trial["rag_vector_model_runtime_enabled"] is False
    assert trial["frontend_durable_authority_enabled"] is False
    assert trial["raw_local_path_exposed"] is False
    assert trial["raw_url_exposed"] is False
    assert "C:\\" not in str(trial)
    assert "http://" not in str(trial)
    assert "https://" not in str(trial)


def test_review_browser_server_prepares_sec_edgar_repeatability_trial_authority(client: TestClient) -> None:
    setup_response = client.post("/__test/layer3/sec-edgar-repeatability-trial")

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_sec_edgar_repeatability_trial_setup.v1"
    assert setup["test_only"] is True
    assert setup["dataset_version_id"].startswith("dv-sec-edgar-status-")
    assert setup["original_operator_status_hash"] == setup["repeat_operator_status_hash"]
    assert setup["trial_endpoint"] == "/api/v1/layer3/source/sec-edgar/text-table/downstream/operator-repeatability/trial"
    assert setup["status_endpoint"] == "/api/v1/layer3/source/sec-edgar/text-table/downstream-proof/status"
    assert setup["raw_local_path_exposed"] is False
    assert setup["raw_url_exposed"] is False
    assert setup["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(setup)

    trial_response = client.post(
        setup["trial_endpoint"],
        json={
            "client_request_id": "review-browser-sec-edgar-repeatability-trial",
            "trial_mode": (
                "append_only_trial_receipt_over_original_and_repeat_downstream_status_authority_"
                "without_sec_fetch_or_processing_execution"
            ),
            "operator_decision": "record_sec_edgar_text_table_downstream_operator_repeatability_trial",
            "original_operator_status_request": setup["original_operator_status_request"],
            "original_operator_status_hash": setup["original_operator_status_hash"],
            "repeat_operator_status_request": setup["repeat_operator_status_request"],
            "repeat_operator_status_hash": setup["repeat_operator_status_hash"],
            "operator_repeatability_disposition": "no_regression_observed",
            "operator_confirmation": True,
        },
    )
    assert trial_response.status_code == 200, trial_response.text
    trial = trial_response.json()
    assert trial["schema_id"] == "layer3.sec_edgar_text_table_downstream_operator_repeatability_trial.v1"
    assert trial["operator_repeatability_trial_state"] == (
        "sec_edgar_text_table_downstream_operator_repeatability_trial_accepted"
    )
    assert trial["operator_status_hash_comparison"] == "match"
    assert trial["proof_hash_comparison"] == "match"
    assert trial["coverage_step_set_comparison"] == "match"
    assert trial["actual_sec_processing_execution_admitted"] is False
    assert trial["actual_subprocess_spawn_admitted"] is False
    assert trial["raw_local_path_exposed"] is False
    assert trial["raw_url_exposed"] is False
    assert trial["frontend_durable_authority_enabled"] is False
    assert "C:\\" not in str(trial)
    assert "http://" not in str(trial)
    assert "https://" not in str(trial)


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


@pytest.mark.parametrize("candidate_b_source_kind", ["bundle", "runtime"])
def test_review_browser_server_routes_candidate_b_bridge_curated_root_to_source_directory_gate_b(
    client: TestClient,
    candidate_b_source_kind: str,
) -> None:
    setup_response = client.post(
        "/__test/layer3/candidate-b-source-directory-authority",
        json={"candidate_b_source_kind": candidate_b_source_kind},
    )

    assert setup_response.status_code == 200, setup_response.text
    setup = setup_response.json()
    assert setup["schema_id"] == "project6.review_browser_candidate_b_source_directory_authority_setup.v1"
    assert setup["test_only"] is True
    assert setup["server_generated_receipts"] is True
    assert setup["source_ingestion_dir_configured_from_bridge"] is True
    assert setup["candidate_b_source_kind"] == candidate_b_source_kind
    assert setup["curated_root_absolute_path_exposed"] is False
    assert setup["layer3_material_preview_compatible"] is True
    assert setup["gate_b_material_authority_compatible"] is True
    assert setup["expected_source_directory_file_count"] > 0
    assert setup["artifact_role_counts"]["material_analysis_payloads"] > 0
    assert "C:\\" not in str(setup)

    scan_response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json={
            "client_request_id": f"candidate-b-{candidate_b_source_kind}-source-directory-scan",
            "operator_decision": "scan_server_configured_operator_directory",
            "source_family": "server_configured_operator_directory_text_table_source_family",
            "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
        },
    )
    assert scan_response.status_code == 201, scan_response.text
    scan = scan_response.json()
    assert scan["schema_id"] == "layer3.source_directory_ingestion_batch.v1"
    assert scan["eligible_file_count"] == setup["expected_source_directory_file_count"]
    assert len(scan["files"]) == setup["expected_source_directory_file_count"]
    assert scan["source_root_absolute_path_exposed"] is False
    assert "C:\\" not in str(scan)

    file_record = scan["files"][0]
    preview_response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json={
            "client_request_id": f"candidate-b-{candidate_b_source_kind}-source-directory-preview",
            "source_ingestion_batch_id": scan["source_ingestion_batch_id"],
            "source_ingestion_file_id": file_record["source_ingestion_file_id"],
            "file_identity_hash": file_record["file_identity_hash"],
            "authority_basis_hash": file_record["authority_basis_hash"],
            "max_chars": 1000,
        },
    )
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["schema_id"] == "layer3.source_directory_material_preview.v1"
    assert preview["status"] == "available"
    assert preview["source_ingestion_batch_id"] == scan["source_ingestion_batch_id"]
    assert preview["source_ingestion_file_id"] == file_record["source_ingestion_file_id"]
    assert preview["material_candidate"]["source_class"] == "server_configured_directory_file"
    assert preview["source_gate"]["absolute_path_exposed"] is False
    assert preview["source_gate"]["rag_vector_index_enabled"] is False
    assert preview["source_gate"]["package_construction_enabled"] is False
    assert "C:\\" not in str(preview)

    candidate = preview["material_candidate"]
    gate_b_response = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "schema_id": "layer3.gate_b_decision_request.v1",
            "client_request_id": f"candidate-b-{candidate_b_source_kind}-source-directory-gate-b",
            "preflight_id": f"candidate-b-{candidate_b_source_kind}-source-directory-rendered-proof",
            "source_set_id": scan["source_ingestion_batch_id"],
            "material_preview_id": preview["material_preview_id"],
            "material_preview_hash": preview["material_preview_hash"],
            "actor": "operator",
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "operator_reason": "Candidate B bridge curated source-directory Gate B proof.",
                    "decision_basis": {
                        "source_ref": candidate["source_ref"],
                        "query_basis": candidate["query_basis"],
                        "provenance_ref": candidate["provenance_ref"],
                        "source_identity": candidate["source_identity"],
                        "source_provenance": candidate["source_provenance"],
                        "payload": candidate["payload"],
                        "load_summary": candidate["load_summary"],
                    },
                }
            ],
            "commit_reason": "candidate_b_bridge_source_directory_gate_b_proof",
        },
    )
    assert gate_b_response.status_code == 200, gate_b_response.text
    gate_b = gate_b_response.json()
    assert gate_b["schema_id"] == "layer3.gate_b_decision_result.v1"
    assert gate_b["status"] == "ok"
    assert gate_b["next_state"] == "gate_c_preview_ready"
    assert gate_b["approved_candidate_ids"] == [candidate["candidate_id"]]
    assert "C:\\" not in str(gate_b)

    reset_response = client.post("/__test/layer3/source-directory-fixture-reset")
    assert reset_response.status_code == 200, reset_response.text
    reset = reset_response.json()
    assert reset["schema_id"] == "project6.review_browser_source_directory_fixture_reset.v1"
    assert reset["source_ingestion_dir_restored"] is True
    assert reset["source_root_absolute_path_exposed"] is False

    reset_scan_response = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json={
            "client_request_id": f"candidate-b-{candidate_b_source_kind}-source-directory-reset-scan",
            "operator_decision": "scan_server_configured_operator_directory",
            "source_family": "server_configured_operator_directory_text_table_source_family",
            "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
        },
    )
    assert reset_scan_response.status_code == 201, reset_scan_response.text
    reset_scan = reset_scan_response.json()
    assert [file_record["relative_name"] for file_record in reset_scan["files"]] == ["vector-retrieval.txt"]
    assert "C:\\" not in str(reset_scan)


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
