from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import (
    layer3_candidate_b_broader_scope_readiness,
    layer3_candidate_b_broader_scope_runtime,
    layer3_candidate_b_broader_scope_selector_use,
)
from main import app


READINESS_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/scope-readiness-audit"
RUNTIME_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime"
SELECTOR_USE_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use"
)
SELECTOR_USE_STATUS_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-use/status"
)
SCOPE_CLASSES = list(layer3_candidate_b_broader_scope_readiness.SCOPE_CLASSES)
EXCLUSIONS = list(layer3_candidate_b_broader_scope_readiness.REQUIRED_EXCLUSIONS)
SELECTED_CLASS = "structured_json_or_csv_or_xlsx"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "layer3_candidate_b_runtime_bridge_dir", str(tmp_path / "runtime-bridge"))
    app.openapi_schema = None
    with TestClient(app) as test_client:
        yield test_client
    app.openapi_schema = None


def _ready_scope_evidence() -> dict[str, dict[str, object]]:
    return {
        scope_class: {
            "current_parser_or_engine_authority": f"current-main-authority:{scope_class}",
            "baseline_rollback_behavior": "baseline_preserved",
            "candidate_a_interaction": "candidate_a_semantics_preserved",
            "candidate_b_runtime_compatibility": "compatible_for_separate_selection",
            "layer3_material_authority_bridge_compatibility": "compatible_for_separate_selection",
            "artifact_family_preservation": "preserved",
            "redaction_and_status_projection": "redacted_operator_visible",
            "corpus_scale_proof": "available",
            "fail_closed_stale_or_missing_authority": "proven",
            "regression_disposition": "no_unacceptable_regression_identified",
            "selector_mutation_required_now": False,
            "source_expansion_required_now": False,
            "runtime_db_or_storage_expansion_required_now": False,
        }
        for scope_class in SCOPE_CLASSES
    }


def _ready_audit(client: TestClient) -> dict[str, object]:
    response = client.post(
        READINESS_ENDPOINT,
        json={
            "client_request_id": "cb-broader-scope-selector-use-readiness-test",
            "audit_mode": layer3_candidate_b_broader_scope_readiness.AUDIT_MODE,
            "exact_corpus_class_list": SCOPE_CLASSES,
            "explicit_exclusion_list": EXCLUSIONS,
            "proposed_default_scope_classes": [SELECTED_CLASS],
            "scope_evidence": _ready_scope_evidence(),
            "rollback_to_baseline_confirmation": True,
            "operator_confirmation": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready"
    return body


def _runtime_selection(client: TestClient) -> dict[str, object]:
    readiness_audit = _ready_audit(client)
    response = client.post(
        RUNTIME_ENDPOINT,
        json={
            "client_request_id": "cb-broader-scope-selector-use-runtime-test",
            "runtime_mode": layer3_candidate_b_broader_scope_runtime.RUNTIME_MODE,
            "readiness_audit_id": readiness_audit["audit_id"],
            "readiness_audit_hash": readiness_audit["audit_hash"],
            "readiness_audit": readiness_audit,
            "selected_scope_classes": [SELECTED_CLASS],
            "rollback_to_baseline_confirmation": True,
            "operator_confirmation": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "selected"
    return body


def _selector_use_payload(runtime_selection: dict[str, object]) -> dict[str, object]:
    return {
        "client_request_id": "cb-broader-scope-selector-use-test",
        "selector_use_mode": layer3_candidate_b_broader_scope_selector_use.RUNTIME_MODE,
        "runtime_selection_receipt_id": runtime_selection["selection_receipt_id"],
        "runtime_selection_receipt_hash": runtime_selection["selection_receipt_hash"],
        "selected_scope_classes": [SELECTED_CLASS],
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }


def _selector_use(client: TestClient, runtime_selection: dict[str, object] | None = None) -> dict[str, object]:
    runtime_selection = runtime_selection or _runtime_selection(client)
    response = client.post(SELECTOR_USE_ENDPOINT, json=_selector_use_payload(runtime_selection))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "selected"
    return body


def test_candidate_b_broader_scope_selector_use_records_redacted_receipt(client: TestClient) -> None:
    runtime_selection = _runtime_selection(client)

    response = client.post(SELECTOR_USE_ENDPOINT, json=_selector_use_payload(runtime_selection))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.SCHEMA_ID
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.RUNTIME_MODE
    assert body["status"] == "selected"
    assert body["selector_use_state"] == layer3_candidate_b_broader_scope_selector_use.SELECTED_STATE
    assert body["selector_use_state"] == "candidate_b_broader_eligible_corpus_default_scope_selector_use_selected"
    assert body["selected_scope_classes"] == [SELECTED_CLASS]
    assert body["runtime_selection_receipt_binding"]["binding_verified"] is True
    assert body["default_scope_enabled_for_selected_classes"] is True
    assert body["non_selected_class_default_preserved"] == "baseline"
    assert body["default_scope_expansion_enabled"] is True
    assert body["selector_use_authority_recorded"] is True
    assert body["selector_mutation_performed"] is False
    assert body["source_expansion_admitted"] is False
    assert body["runtime_db_or_storage_expansion_admitted"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["selector_use_receipt_ref"].startswith("candidate-b-broader-scope-selector-use://")
    assert "C:" not in json.dumps(body, sort_keys=True)
    assert "https://" not in json.dumps(body, sort_keys=True)

    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-selector-use"
        / f"{body['selector_use_receipt_id']}.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["selector_use_receipt_hash"] == body["selector_use_receipt_hash"]
    assert receipt["runtime_selection_receipt_id"] == runtime_selection["selection_receipt_id"]
    assert receipt["selected_scope_classes"] == [SELECTED_CLASS]
    assert receipt["raw_local_path_exposed"] is False
    assert receipt["raw_url_exposed"] is False


def test_candidate_b_broader_scope_selector_use_status_revalidates_redacted_receipt(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)

    response = client.post(
        SELECTOR_USE_STATUS_ENDPOINT,
        json={
            "client_request_id": "cb-broader-scope-selector-use-status-test",
            "status_mode": layer3_candidate_b_broader_scope_selector_use.STATUS_MODE,
            "operator_decision": layer3_candidate_b_broader_scope_selector_use.STATUS_OPERATOR_DECISION,
            "selector_use_receipt_id": selector_use["selector_use_receipt_id"],
            "selector_use_receipt_hash": selector_use["selector_use_receipt_hash"],
            "runtime_selection_receipt_id": runtime_selection["selection_receipt_id"],
            "runtime_selection_receipt_hash": runtime_selection["selection_receipt_hash"],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.STATUS_SCHEMA_ID
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.STATUS_MODE
    assert body["status"] == "available"
    assert body["selector_use_state"] == layer3_candidate_b_broader_scope_selector_use.SELECTED_STATE
    assert body["selector_use_receipt_id"] == selector_use["selector_use_receipt_id"]
    assert body["runtime_selection_receipt_binding"]["binding_verified"] is True
    assert body["operator_visible_selector_status"]["selector_use_recorded"] is True
    assert body["operator_visible_selector_status"]["redacted_selector_use_receipt_available"] is True
    assert body["selected_scope_classes"] == [SELECTED_CLASS]
    assert body["default_scope_enabled_for_selected_classes"] is True
    assert body["non_selected_class_default_preserved"] == "baseline"
    assert body["selector_mutation_performed"] is False
    assert body["source_expansion_admitted"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert "C:" not in json.dumps(body, sort_keys=True)
    assert "https://" not in json.dumps(body, sort_keys=True)


def test_candidate_b_broader_scope_selector_use_status_rejects_stale_receipt_hash(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)

    response = client.post(
        SELECTOR_USE_STATUS_ENDPOINT,
        json={
            "client_request_id": "cb-broader-scope-selector-use-status-stale-hash",
            "status_mode": layer3_candidate_b_broader_scope_selector_use.STATUS_MODE,
            "operator_decision": layer3_candidate_b_broader_scope_selector_use.STATUS_OPERATOR_DECISION,
            "selector_use_receipt_id": selector_use["selector_use_receipt_id"],
            "selector_use_receipt_hash": "c" * 64,
            "runtime_selection_receipt_id": runtime_selection["selection_receipt_id"],
            "runtime_selection_receipt_hash": runtime_selection["selection_receipt_hash"],
        },
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.STATUS_SCHEMA_ID
    assert body["status"] == "blocked"
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.STATUS_MODE
    reasons = body["error"]["details"]["blocked_reasons"]
    codes = {item["code"] for item in reasons}
    assert "candidate_b_broader_scope_selector_use_status_receipt_field_mismatch" in codes
    assert "candidate_b_broader_scope_selector_use_status_stale_receipt_hash" in codes


def test_candidate_b_broader_scope_selector_use_fails_closed_without_runtime_receipt(
    client: TestClient,
) -> None:
    response = client.post(
        SELECTOR_USE_ENDPOINT,
        json={
            "client_request_id": "cb-broader-scope-selector-use-missing-runtime-receipt",
            "selector_use_mode": layer3_candidate_b_broader_scope_selector_use.RUNTIME_MODE,
            "runtime_selection_receipt_id": "cb-broader-scope-runtime-missing",
            "runtime_selection_receipt_hash": "a" * 64,
            "selected_scope_classes": [SELECTED_CLASS],
            "rollback_to_baseline_confirmation": True,
            "operator_confirmation": True,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["selector_use_state"] == layer3_candidate_b_broader_scope_selector_use.BLOCKED_STATE
    assert body["selector_use_receipt_status"] == "not_recorded"
    assert body["selector_use_receipt_id"] is None
    assert body["default_scope_expansion_enabled"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_selector_use_runtime_receipt_missing" in codes


def test_candidate_b_broader_scope_selector_use_rejects_stale_hash_and_unselected_class(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    payload = _selector_use_payload(runtime_selection)
    payload["runtime_selection_receipt_hash"] = "b" * 64
    payload["selected_scope_classes"] = ["office_documents"]

    response = client.post(SELECTOR_USE_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["selector_use_receipt_status"] == "not_recorded"
    assert body["default_scope_expansion_enabled"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_selector_use_runtime_receipt_field_mismatch" in codes
    assert "candidate_b_broader_scope_selector_use_stale_runtime_receipt_hash" in codes
    assert "candidate_b_broader_scope_selector_use_selected_classes_do_not_match_runtime_receipt" in codes
    assert "candidate_b_broader_scope_selector_use_unselected_scope_class" in codes


def test_candidate_b_broader_scope_selector_use_rejects_forbidden_browser_authority(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    payload = _selector_use_payload(runtime_selection)
    payload["local_path"] = "C:/private/source"

    response = client.post(SELECTOR_USE_ENDPOINT, json=payload)

    assert response.status_code == 422, response.text


def test_candidate_b_broader_scope_selector_use_is_exposed_in_contracts(client: TestClient) -> None:
    readiness = client.get("/api/v1/layer3/readiness")
    bootstrap = client.get("/api/v1/layer3/bootstrap")

    assert readiness.status_code == 200, readiness.text
    readiness_body = readiness.json()
    assert readiness_body["candidate_b_broader_eligible_corpus_default_scope_selector_use_admitted"] is True
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_selector_use_endpoint"]
        == SELECTOR_USE_ENDPOINT
    )
    assert readiness_body["candidate_b_broader_eligible_corpus_default_scope_selector_use_status_admitted"] is True
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_selector_use_status_endpoint"]
        == SELECTOR_USE_STATUS_ENDPOINT
    )

    assert bootstrap.status_code == 200, bootstrap.text
    bootstrap_body = bootstrap.json()
    assert bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_selector_use"] is True
    assert bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_selector_use_status"] is True
    assert (
        bootstrap_body["execution_readiness"]["candidate_b_broader_eligible_corpus_default_scope_selector_use_endpoint"]
        == SELECTOR_USE_ENDPOINT
    )
    assert (
        bootstrap_body["execution_readiness"][
            "candidate_b_broader_eligible_corpus_default_scope_selector_use_status_endpoint"
        ]
        == SELECTOR_USE_STATUS_ENDPOINT
    )

    schema = client.app.openapi()
    route = schema["paths"][SELECTOR_USE_ENDPOINT]["post"]
    request_ref = route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]
    assert request_schema["additionalProperties"] is False
    for field in ("visual_lane_mode", "document_processing_engine", "local_path", "url", "default_selector"):
        assert field not in request_schema["properties"]
    status_route = schema["paths"][SELECTOR_USE_STATUS_ENDPOINT]["post"]
    status_request_ref = status_route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    status_request_schema = schema["components"]["schemas"][status_request_ref.rsplit("/", 1)[-1]]
    assert status_request_schema["additionalProperties"] is False
    for field in ("visual_lane_mode", "document_processing_engine", "local_path", "url", "default_selector"):
        assert field not in status_request_schema["properties"]
