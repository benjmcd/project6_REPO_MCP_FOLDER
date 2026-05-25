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
SELECTOR_ACTIVATION_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/selector-activation"
)
ACTIVATION_CONSUMPTION_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/activation-receipt/consume"
)
CONSUMPTION_RECEIPT_USE_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use"
)
CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/consumption-receipt/use/status"
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


def _selector_use_status(
    client: TestClient,
    runtime_selection: dict[str, object] | None = None,
    selector_use: dict[str, object] | None = None,
) -> dict[str, object]:
    runtime_selection = runtime_selection or _runtime_selection(client)
    selector_use = selector_use or _selector_use(client, runtime_selection)
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
    assert body["status"] == "available"
    return body


def _selector_activation_payload(selector_use_status: dict[str, object]) -> dict[str, object]:
    runtime_binding = selector_use_status["runtime_selection_receipt_binding"]
    return {
        "client_request_id": "cb-broader-scope-selector-activation-test",
        "activation_mode": layer3_candidate_b_broader_scope_selector_use.ACTIVATION_MODE,
        "selector_use_status_hash": selector_use_status["selector_use_status_hash"],
        "selector_use_receipt_id": selector_use_status["selector_use_receipt_id"],
        "selector_use_receipt_hash": selector_use_status["selector_use_receipt_hash"],
        "runtime_selection_receipt_id": runtime_binding["runtime_selection_receipt_id"],
        "runtime_selection_receipt_hash": runtime_binding["runtime_selection_receipt_hash"],
        "selected_scope_classes": selector_use_status["selected_scope_classes"],
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }


def _selector_activation(
    client: TestClient,
    selector_use_status: dict[str, object] | None = None,
) -> dict[str, object]:
    selector_use_status = selector_use_status or _selector_use_status(client)
    response = client.post(SELECTOR_ACTIVATION_ENDPOINT, json=_selector_activation_payload(selector_use_status))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "selected"
    return body


def _activation_consumption_payload(
    selector_use_status: dict[str, object],
    selector_activation: dict[str, object],
) -> dict[str, object]:
    runtime_binding = selector_use_status["runtime_selection_receipt_binding"]
    return {
        "client_request_id": "cb-broader-scope-activation-consumption-test",
        "consumption_mode": layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_MODE,
        "activation_receipt_id": selector_activation["activation_receipt_id"],
        "activation_receipt_hash": selector_activation["activation_receipt_hash"],
        "selector_use_status_hash": selector_use_status["selector_use_status_hash"],
        "selector_use_receipt_id": selector_use_status["selector_use_receipt_id"],
        "selector_use_receipt_hash": selector_use_status["selector_use_receipt_hash"],
        "runtime_selection_receipt_id": runtime_binding["runtime_selection_receipt_id"],
        "runtime_selection_receipt_hash": runtime_binding["runtime_selection_receipt_hash"],
        "selected_scope_classes": selector_activation["selected_scope_classes"],
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }


def _activation_consumption(
    client: TestClient,
    selector_use_status: dict[str, object] | None = None,
    selector_activation: dict[str, object] | None = None,
) -> dict[str, object]:
    selector_use_status = selector_use_status or _selector_use_status(client)
    selector_activation = selector_activation or _selector_activation(client, selector_use_status)
    response = client.post(
        ACTIVATION_CONSUMPTION_ENDPOINT,
        json=_activation_consumption_payload(selector_use_status, selector_activation),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "selected"
    return body


def _consumption_receipt_use_payload(
    selector_use_status: dict[str, object],
    activation_consumption: dict[str, object],
) -> dict[str, object]:
    runtime_binding = selector_use_status["runtime_selection_receipt_binding"]
    activation_binding = activation_consumption["activation_receipt_binding"]
    return {
        "client_request_id": "cb-broader-scope-consumption-receipt-use-test",
        "use_mode": layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_MODE,
        "consumption_receipt_id": activation_consumption["consumption_receipt_id"],
        "consumption_receipt_hash": activation_consumption["consumption_receipt_hash"],
        "activation_receipt_id": activation_binding["activation_receipt_id"],
        "activation_receipt_hash": activation_binding["activation_receipt_hash"],
        "selector_use_status_hash": selector_use_status["selector_use_status_hash"],
        "selector_use_receipt_id": selector_use_status["selector_use_receipt_id"],
        "selector_use_receipt_hash": selector_use_status["selector_use_receipt_hash"],
        "runtime_selection_receipt_id": runtime_binding["runtime_selection_receipt_id"],
        "runtime_selection_receipt_hash": runtime_binding["runtime_selection_receipt_hash"],
        "selected_scope_classes": activation_consumption["selected_scope_classes"],
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }


def _consumption_receipt_use(
    client: TestClient,
    selector_use_status: dict[str, object] | None = None,
    activation_consumption: dict[str, object] | None = None,
) -> dict[str, object]:
    selector_use_status = selector_use_status or _selector_use_status(client)
    activation_consumption = activation_consumption or _activation_consumption(client, selector_use_status)
    response = client.post(
        CONSUMPTION_RECEIPT_USE_ENDPOINT,
        json=_consumption_receipt_use_payload(selector_use_status, activation_consumption),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "selected"
    return body


def _consumption_receipt_use_status_payload(
    use_receipt: dict[str, object],
) -> dict[str, object]:
    return {
        "client_request_id": "cb-broader-scope-consumption-receipt-use-status-test",
        "status_mode": layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_STATUS_MODE,
        "operator_decision": layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_STATUS_OPERATOR_DECISION,
        "use_receipt_id": use_receipt["use_receipt_id"],
        "use_receipt_hash": use_receipt["use_receipt_hash"],
        "consumption_receipt_id": use_receipt["consumption_receipt_binding"]["consumption_receipt_id"],
        "consumption_receipt_hash": use_receipt["consumption_receipt_binding"]["consumption_receipt_hash"],
        "activation_receipt_id": use_receipt["activation_receipt_binding"]["activation_receipt_id"],
        "activation_receipt_hash": use_receipt["activation_receipt_binding"]["activation_receipt_hash"],
        "selector_use_status_hash": use_receipt["selector_use_status_binding"]["selector_use_status_hash"],
        "selector_use_receipt_id": use_receipt["selector_use_receipt_binding"]["selector_use_receipt_id"],
        "selector_use_receipt_hash": use_receipt["selector_use_receipt_binding"]["selector_use_receipt_hash"],
        "runtime_selection_receipt_id": use_receipt["runtime_selection_receipt_binding"]["runtime_selection_receipt_id"],
        "runtime_selection_receipt_hash": use_receipt["runtime_selection_receipt_binding"]["runtime_selection_receipt_hash"],
        "readiness_audit_id": use_receipt["readiness_audit_binding"]["readiness_audit_id"],
        "readiness_audit_hash": use_receipt["readiness_audit_binding"]["readiness_audit_hash"],
        "selected_scope_classes": use_receipt["selected_scope_classes"],
    }


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


def test_candidate_b_broader_scope_selector_activation_records_redacted_receipt(client: TestClient) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)

    response = client.post(SELECTOR_ACTIVATION_ENDPOINT, json=_selector_activation_payload(selector_use_status))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.ACTIVATION_SCHEMA_ID
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.ACTIVATION_MODE
    assert body["status"] == "selected"
    assert body["selector_activation_state"] == layer3_candidate_b_broader_scope_selector_use.ACTIVATION_SELECTED_STATE
    assert body["selected_scope_classes"] == [SELECTED_CLASS]
    assert body["activation_authority"]["status_revalidated"] is True
    assert body["selector_use_receipt_binding"]["binding_verified"] is True
    assert body["runtime_selection_receipt_binding"]["binding_verified"] is True
    assert body["readiness_audit_binding"]["binding_verified"] is True
    assert body["default_scope_activation_enabled"] is True
    assert body["default_scope_expansion_enabled"] is True
    assert body["non_selected_class_default"] == "baseline"
    assert body["operator_visible_activation_status"]["redacted_activation_receipt_available"] is True
    assert body["selector_activation_authority_recorded"] is True
    assert body["selector_mutation_performed"] is False
    assert body["source_expansion_admitted"] is False
    assert body["runtime_db_or_storage_expansion_admitted"] is False
    assert body["provider_object_write_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["rag_vector_model_runtime_enabled"] is False
    assert body["full_mockup_activation_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["activation_receipt_ref"].startswith("candidate-b-broader-scope-selector-activation://")
    assert "C:" not in json.dumps(body, sort_keys=True)
    assert "https://" not in json.dumps(body, sort_keys=True)

    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-selector-activation"
        / f"{body['activation_receipt_id']}.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["activation_receipt_hash"] == body["activation_receipt_hash"]
    assert receipt["selector_use_status_hash"] == selector_use_status["selector_use_status_hash"]
    assert receipt["selector_use_receipt_id"] == selector_use["selector_use_receipt_id"]
    assert receipt["runtime_selection_receipt_id"] == runtime_selection["selection_receipt_id"]
    assert receipt["selected_scope_classes"] == [SELECTED_CLASS]
    assert receipt["raw_local_path_exposed"] is False
    assert receipt["raw_url_exposed"] is False


def test_candidate_b_broader_scope_selector_activation_fails_closed_on_stale_status_hash(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    payload = _selector_activation_payload(selector_use_status)
    payload["selector_use_status_hash"] = "d" * 64

    response = client.post(SELECTOR_ACTIVATION_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["selector_activation_state"] == layer3_candidate_b_broader_scope_selector_use.ACTIVATION_BLOCKED_STATE
    assert body["activation_receipt_status"] == "not_recorded"
    assert body["activation_receipt_id"] is None
    assert body["default_scope_activation_enabled"] is False
    assert body["default_scope_expansion_enabled"] is False
    assert body["selector_activation_authority_recorded"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_selector_activation_stale_status_hash" in codes


def test_candidate_b_broader_scope_selector_activation_fails_closed_on_stale_selector_use_hash(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    payload = _selector_activation_payload(selector_use_status)
    payload["selector_use_receipt_hash"] = "e" * 64

    response = client.post(SELECTOR_ACTIVATION_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["activation_receipt_status"] == "not_recorded"
    assert body["default_scope_activation_enabled"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_selector_activation_status_authority_invalid" in codes
    authority_errors = {item["details"].get("authority_error_code") for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_selector_use_status_authority_invalid" in authority_errors


def test_candidate_b_broader_scope_selector_activation_fails_closed_on_stale_runtime_hash(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    payload = _selector_activation_payload(selector_use_status)
    payload["runtime_selection_receipt_hash"] = "f" * 64

    response = client.post(SELECTOR_ACTIVATION_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["activation_receipt_status"] == "not_recorded"
    assert body["default_scope_activation_enabled"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_selector_activation_status_authority_invalid" in codes
    authority_errors = {item["details"].get("authority_error_code") for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_selector_use_status_authority_invalid" in authority_errors


def test_candidate_b_broader_scope_selector_activation_fails_closed_on_unselected_class(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    payload = _selector_activation_payload(selector_use_status)
    payload["selected_scope_classes"] = ["office_documents"]

    response = client.post(SELECTOR_ACTIVATION_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["activation_receipt_status"] == "not_recorded"
    assert body["default_scope_activation_enabled"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_selector_activation_selected_classes_do_not_match_status" in codes
    assert "candidate_b_broader_scope_selector_activation_unselected_scope_class" in codes


def test_candidate_b_broader_scope_activation_consumption_records_redacted_receipt(client: TestClient) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    selector_activation = _selector_activation(client, selector_use_status)

    response = client.post(
        ACTIVATION_CONSUMPTION_ENDPOINT,
        json=_activation_consumption_payload(selector_use_status, selector_activation),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_SCHEMA_ID
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_MODE
    assert body["status"] == "selected"
    assert (
        body["activation_receipt_consumption_state"]
        == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_SELECTED_STATE
    )
    assert body["selected_scope_classes"] == [SELECTED_CLASS]
    assert body["consumption_authority"]["activation_receipt_reloaded"] is True
    assert body["activation_receipt_binding"]["binding_verified"] is True
    assert body["selector_use_status_binding"]["status_revalidated"] is True
    assert body["selector_use_receipt_binding"]["binding_verified"] is True
    assert body["runtime_selection_receipt_binding"]["binding_verified"] is True
    assert body["readiness_audit_binding"]["binding_verified"] is True
    assert body["default_scope_consumption_enabled"] is True
    assert body["default_scope_expansion_enabled"] is True
    assert body["non_selected_class_default"] == "baseline"
    assert body["operator_visible_consumption_status"]["redacted_consumption_receipt_available"] is True
    assert body["activation_receipt_consumption_authority_recorded"] is True
    assert body["selector_mutation_performed"] is False
    assert body["default_scope_mutation_performed"] is False
    assert body["source_expansion_admitted"] is False
    assert body["runtime_db_or_storage_expansion_admitted"] is False
    assert body["provider_object_write_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["rag_vector_model_runtime_enabled"] is False
    assert body["full_mockup_activation_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["consumption_receipt_ref"].startswith("candidate-b-broader-scope-activation-consumption://")
    assert "C:" not in json.dumps(body, sort_keys=True)
    assert "https://" not in json.dumps(body, sort_keys=True)

    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-activation-consumption"
        / f"{body['consumption_receipt_id']}.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["consumption_receipt_hash"] == body["consumption_receipt_hash"]
    assert receipt["activation_receipt_id"] == selector_activation["activation_receipt_id"]
    assert receipt["activation_receipt_hash"] == selector_activation["activation_receipt_hash"]
    assert receipt["selector_use_status_hash"] == selector_use_status["selector_use_status_hash"]
    assert receipt["selector_use_receipt_id"] == selector_use["selector_use_receipt_id"]
    assert receipt["runtime_selection_receipt_id"] == runtime_selection["selection_receipt_id"]
    assert receipt["selected_scope_classes"] == [SELECTED_CLASS]
    assert receipt["raw_local_path_exposed"] is False
    assert receipt["raw_url_exposed"] is False


def test_candidate_b_broader_scope_activation_consumption_fails_closed_on_missing_activation_receipt(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    payload = _activation_consumption_payload(
        selector_use_status,
        {
            "activation_receipt_id": f"{layer3_candidate_b_broader_scope_selector_use.ACTIVATION_RECEIPT_PREFIX}-missing",
            "activation_receipt_hash": "a" * 64,
            "selected_scope_classes": [SELECTED_CLASS],
        },
    )

    response = client.post(ACTIVATION_CONSUMPTION_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert (
        body["activation_receipt_consumption_state"]
        == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_BLOCKED_STATE
    )
    assert body["consumption_receipt_status"] == "not_recorded"
    assert body["consumption_receipt_id"] is None
    assert body["default_scope_consumption_enabled"] is False
    assert body["activation_receipt_consumption_authority_recorded"] is False
    assert body["selector_mutation_performed"] is False
    assert body["default_scope_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_activation_consumption_missing_activation_receipt" in codes


def test_candidate_b_broader_scope_activation_consumption_fails_closed_on_stale_activation_hash(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    selector_activation = _selector_activation(client, selector_use_status)
    payload = _activation_consumption_payload(selector_use_status, selector_activation)
    payload["activation_receipt_hash"] = "b" * 64

    response = client.post(ACTIVATION_CONSUMPTION_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["consumption_receipt_status"] == "not_recorded"
    assert body["default_scope_consumption_enabled"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_activation_consumption_stale_activation_receipt_hash" in codes


def test_candidate_b_broader_scope_activation_consumption_fails_closed_on_unselected_class(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    selector_activation = _selector_activation(client, selector_use_status)
    payload = _activation_consumption_payload(selector_use_status, selector_activation)
    payload["selected_scope_classes"] = ["office_documents"]

    response = client.post(ACTIVATION_CONSUMPTION_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["consumption_receipt_status"] == "not_recorded"
    assert body["default_scope_consumption_enabled"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_activation_consumption_selected_classes_do_not_match_activation" in codes
    assert "candidate_b_broader_scope_activation_consumption_unselected_scope_class" in codes


def test_candidate_b_broader_scope_consumption_receipt_use_records_redacted_receipt(client: TestClient) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    selector_activation = _selector_activation(client, selector_use_status)
    activation_consumption = _activation_consumption(client, selector_use_status, selector_activation)

    response = client.post(
        CONSUMPTION_RECEIPT_USE_ENDPOINT,
        json=_consumption_receipt_use_payload(selector_use_status, activation_consumption),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_SCHEMA_ID
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_MODE
    assert body["status"] == "selected"
    assert body["consumption_receipt_use_state"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_SELECTED_STATE
    assert body["selected_scope_classes"] == [SELECTED_CLASS]
    assert body["use_authority"]["consumption_receipt_reloaded"] is True
    assert body["consumption_receipt_binding"]["binding_verified"] is True
    assert body["activation_receipt_binding"]["binding_verified"] is True
    assert body["selector_use_status_binding"]["status_revalidated"] is True
    assert body["selector_use_receipt_binding"]["binding_verified"] is True
    assert body["runtime_selection_receipt_binding"]["binding_verified"] is True
    assert body["readiness_audit_binding"]["binding_verified"] is True
    assert body["default_scope_use_enabled"] is True
    assert body["default_scope_expansion_enabled"] is True
    assert body["default_scope_application_scope"] == "consumed_receipt_bound_selected_classes_only"
    assert body["non_selected_class_default"] == "baseline"
    assert body["operator_visible_use_status"]["redacted_default_scope_use_receipt_available"] is True
    assert body["default_scope_use_authority_recorded"] is True
    assert body["selector_mutation_performed"] is False
    assert body["default_scope_mutation_performed"] is False
    assert body["source_expansion_admitted"] is False
    assert body["runtime_db_or_storage_expansion_admitted"] is False
    assert body["provider_object_write_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["rag_vector_model_runtime_enabled"] is False
    assert body["full_mockup_activation_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["use_receipt_ref"].startswith("candidate-b-broader-scope-consumption-receipt-use://")
    assert "C:" not in json.dumps(body, sort_keys=True)
    assert "https://" not in json.dumps(body, sort_keys=True)

    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-consumption-receipt-use"
        / f"{body['use_receipt_id']}.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["use_receipt_hash"] == body["use_receipt_hash"]
    assert receipt["consumption_receipt_id"] == activation_consumption["consumption_receipt_id"]
    assert receipt["activation_receipt_id"] == selector_activation["activation_receipt_id"]
    assert receipt["selector_use_status_hash"] == selector_use_status["selector_use_status_hash"]
    assert receipt["selector_use_receipt_id"] == selector_use["selector_use_receipt_id"]
    assert receipt["runtime_selection_receipt_id"] == runtime_selection["selection_receipt_id"]
    assert receipt["selected_scope_classes"] == [SELECTED_CLASS]
    assert receipt["raw_local_path_exposed"] is False
    assert receipt["raw_url_exposed"] is False


def test_candidate_b_broader_scope_consumption_receipt_use_status_revalidates_redacted_receipt(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    selector_activation = _selector_activation(client, selector_use_status)
    activation_consumption = _activation_consumption(client, selector_use_status, selector_activation)
    use_receipt = _consumption_receipt_use(client, selector_use_status, activation_consumption)
    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-consumption-receipt-use"
        / f"{use_receipt['use_receipt_id']}.json"
    )
    before_mtime = receipt_path.stat().st_mtime_ns

    response = client.post(
        CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT,
        json=_consumption_receipt_use_status_payload(use_receipt),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_STATUS_SCHEMA_ID
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_STATUS_MODE
    assert body["status"] == "available"
    assert body["use_receipt_status"] == "recorded"
    assert body["consumption_receipt_use_state"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_SELECTED_STATE
    assert body["use_receipt_id"] == use_receipt["use_receipt_id"]
    assert body["use_receipt_hash"] == use_receipt["use_receipt_hash"]
    assert body["use_authority"]["server_owned_receipt_reloaded"] is True
    assert body["consumption_receipt_binding"]["binding_verified"] is True
    assert body["activation_receipt_binding"]["binding_verified"] is True
    assert body["selector_use_status_binding"]["status_revalidated"] is True
    assert body["selector_use_receipt_binding"]["binding_verified"] is True
    assert body["runtime_selection_receipt_binding"]["binding_verified"] is True
    assert body["readiness_audit_binding"]["binding_verified"] is True
    assert body["selected_scope_classes"] == [SELECTED_CLASS]
    assert body["default_scope_use_enabled"] is True
    assert body["operator_visible_use_status"]["redacted_default_scope_use_receipt_available"] is True
    assert body["default_scope_use_authority_recorded"] is True
    assert body["selector_mutation_performed"] is False
    assert body["default_scope_mutation_performed"] is False
    assert body["use_receipt_mutation_performed"] is False
    assert body["source_expansion_admitted"] is False
    assert body["runtime_db_or_storage_expansion_admitted"] is False
    assert body["provider_object_write_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["rag_vector_model_runtime_enabled"] is False
    assert body["full_mockup_activation_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert "C:" not in json.dumps(body, sort_keys=True)
    assert "https://" not in json.dumps(body, sort_keys=True)
    assert receipt_path.stat().st_mtime_ns == before_mtime


def test_candidate_b_broader_scope_consumption_receipt_use_status_projects_missing_use_as_not_recorded(
    client: TestClient,
) -> None:
    use_receipt = _consumption_receipt_use(client)
    payload = _consumption_receipt_use_status_payload(use_receipt)
    payload["use_receipt_id"] = f"{layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_RECEIPT_PREFIX}-missing"
    payload["use_receipt_hash"] = "e" * 64

    response = client.post(CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_STATUS_SCHEMA_ID
    assert body["status"] == "not_recorded"
    assert body["use_receipt_status"] == "not_recorded"
    assert body["use_receipt_status_hash"] is None
    assert body["default_scope_use_enabled"] is False
    assert body["default_scope_use_authority_recorded"] is False
    assert body["use_receipt_mutation_performed"] is False
    assert body["selector_mutation_performed"] is False
    assert body["default_scope_mutation_performed"] is False
    missing_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-consumption-receipt-use"
        / f"{payload['use_receipt_id']}.json"
    )
    assert not missing_path.exists()


def test_candidate_b_broader_scope_consumption_receipt_use_status_rejects_stale_use_hash(
    client: TestClient,
) -> None:
    use_receipt = _consumption_receipt_use(client)
    payload = _consumption_receipt_use_status_payload(use_receipt)
    payload["use_receipt_hash"] = "f" * 64

    response = client.post(CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_STATUS_SCHEMA_ID
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["error"]["details"]["blocked_reasons"]}
    assert "candidate_b_broader_scope_consumption_receipt_use_status_receipt_field_mismatch" in codes
    assert "candidate_b_broader_scope_consumption_receipt_use_status_stale_use_receipt_hash" in codes


def test_candidate_b_broader_scope_consumption_receipt_use_status_rejects_stale_consumption_hash(
    client: TestClient,
) -> None:
    use_receipt = _consumption_receipt_use(client)
    payload = _consumption_receipt_use_status_payload(use_receipt)
    payload["consumption_receipt_hash"] = "a" * 64

    response = client.post(CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    codes = {item["code"] for item in body["error"]["details"]["blocked_reasons"]}
    assert "candidate_b_broader_scope_consumption_receipt_use_status_use_binding_mismatch" in codes


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("activation_receipt_hash", "b" * 64),
        ("selector_use_status_hash", "c" * 64),
        ("runtime_selection_receipt_hash", "d" * 64),
        ("readiness_audit_hash", "e" * 64),
    ),
)
def test_candidate_b_broader_scope_consumption_receipt_use_status_rejects_stale_required_binding(
    client: TestClient,
    field: str,
    value: str,
) -> None:
    use_receipt = _consumption_receipt_use(client)
    payload = _consumption_receipt_use_status_payload(use_receipt)
    payload[field] = value

    response = client.post(CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    codes = {item["code"] for item in body["error"]["details"]["blocked_reasons"]}
    assert "candidate_b_broader_scope_consumption_receipt_use_status_use_binding_mismatch" in codes


def test_candidate_b_broader_scope_consumption_receipt_use_status_rejects_unselected_class(
    client: TestClient,
) -> None:
    use_receipt = _consumption_receipt_use(client)
    payload = _consumption_receipt_use_status_payload(use_receipt)
    payload["selected_scope_classes"] = ["office_documents"]

    response = client.post(CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    codes = {item["code"] for item in body["error"]["details"]["blocked_reasons"]}
    assert "candidate_b_broader_scope_consumption_receipt_use_status_selected_classes_do_not_match_use_receipt" in codes
    assert "candidate_b_broader_scope_consumption_receipt_use_status_unselected_scope_class" in codes


def test_candidate_b_broader_scope_consumption_receipt_use_fails_closed_on_missing_consumption_receipt(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    selector_activation = _selector_activation(client, selector_use_status)
    activation_consumption = _activation_consumption(client, selector_use_status, selector_activation)
    payload = _consumption_receipt_use_payload(selector_use_status, activation_consumption)
    payload["consumption_receipt_id"] = (
        f"{layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_RECEIPT_PREFIX}-missing"
    )
    payload["consumption_receipt_hash"] = "c" * 64

    response = client.post(CONSUMPTION_RECEIPT_USE_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert (
        body["consumption_receipt_use_state"]
        == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_BLOCKED_STATE
    )
    assert body["use_receipt_status"] == "not_recorded"
    assert body["use_receipt_id"] is None
    assert body["default_scope_use_enabled"] is False
    assert body["default_scope_use_authority_recorded"] is False
    assert body["selector_mutation_performed"] is False
    assert body["default_scope_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_consumption_receipt_use_missing_consumption_receipt" in codes


def test_candidate_b_broader_scope_consumption_receipt_use_fails_closed_on_stale_consumption_hash(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    selector_activation = _selector_activation(client, selector_use_status)
    activation_consumption = _activation_consumption(client, selector_use_status, selector_activation)
    payload = _consumption_receipt_use_payload(selector_use_status, activation_consumption)
    payload["consumption_receipt_hash"] = "d" * 64

    response = client.post(CONSUMPTION_RECEIPT_USE_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["use_receipt_status"] == "not_recorded"
    assert body["default_scope_use_enabled"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_consumption_receipt_use_stale_consumption_receipt_hash" in codes


def test_candidate_b_broader_scope_consumption_receipt_use_fails_closed_on_unselected_class(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    selector_activation = _selector_activation(client, selector_use_status)
    activation_consumption = _activation_consumption(client, selector_use_status, selector_activation)
    payload = _consumption_receipt_use_payload(selector_use_status, activation_consumption)
    payload["selected_scope_classes"] = ["office_documents"]

    response = client.post(CONSUMPTION_RECEIPT_USE_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["use_receipt_status"] == "not_recorded"
    assert body["default_scope_use_enabled"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_consumption_receipt_use_selected_classes_do_not_match_consumption" in codes
    assert "candidate_b_broader_scope_consumption_receipt_use_unselected_scope_class" in codes


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
    assert readiness_body["candidate_b_broader_eligible_corpus_default_scope_selector_activation_admitted"] is True
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_selector_activation_endpoint"]
        == SELECTOR_ACTIVATION_ENDPOINT
    )
    assert (
        readiness_body[
            "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_admitted"
        ]
        is True
    )
    assert (
        readiness_body[
            "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_endpoint"
        ]
        == ACTIVATION_CONSUMPTION_ENDPOINT
    )
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_admitted"] is True
    )
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_endpoint"]
        == CONSUMPTION_RECEIPT_USE_ENDPOINT
    )
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status_admitted"]
        is True
    )
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status_endpoint"]
        == CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT
    )

    assert bootstrap.status_code == 200, bootstrap.text
    bootstrap_body = bootstrap.json()
    assert bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_selector_use"] is True
    assert bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_selector_use_status"] is True
    assert (
        bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_selector_activation"] is True
    )
    assert (
        bootstrap_body["features"][
            "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption"
        ]
        is True
    )
    assert (
        bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use"] is True
    )
    assert (
        bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status"]
        is True
    )
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
    assert (
        bootstrap_body["execution_readiness"][
            "candidate_b_broader_eligible_corpus_default_scope_selector_activation_endpoint"
        ]
        == SELECTOR_ACTIVATION_ENDPOINT
    )
    assert (
        bootstrap_body["execution_readiness"][
            "candidate_b_broader_eligible_corpus_default_scope_activation_receipt_consumption_endpoint"
        ]
        == ACTIVATION_CONSUMPTION_ENDPOINT
    )
    assert (
        bootstrap_body["execution_readiness"][
            "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_endpoint"
        ]
        == CONSUMPTION_RECEIPT_USE_ENDPOINT
    )
    assert (
        bootstrap_body["execution_readiness"][
            "candidate_b_broader_eligible_corpus_default_scope_consumption_receipt_use_status_endpoint"
        ]
        == CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT
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
    activation_route = schema["paths"][SELECTOR_ACTIVATION_ENDPOINT]["post"]
    activation_request_ref = activation_route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    activation_request_schema = schema["components"]["schemas"][activation_request_ref.rsplit("/", 1)[-1]]
    assert activation_request_schema["additionalProperties"] is False
    for field in ("visual_lane_mode", "document_processing_engine", "local_path", "url", "default_selector"):
        assert field not in activation_request_schema["properties"]
    consumption_route = schema["paths"][ACTIVATION_CONSUMPTION_ENDPOINT]["post"]
    consumption_request_ref = consumption_route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    consumption_request_schema = schema["components"]["schemas"][consumption_request_ref.rsplit("/", 1)[-1]]
    assert consumption_request_schema["additionalProperties"] is False
    for field in ("visual_lane_mode", "document_processing_engine", "local_path", "url", "default_selector"):
        assert field not in consumption_request_schema["properties"]
    use_route = schema["paths"][CONSUMPTION_RECEIPT_USE_ENDPOINT]["post"]
    use_request_ref = use_route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    use_request_schema = schema["components"]["schemas"][use_request_ref.rsplit("/", 1)[-1]]
    assert use_request_schema["additionalProperties"] is False
    for field in ("visual_lane_mode", "document_processing_engine", "local_path", "url", "default_selector"):
        assert field not in use_request_schema["properties"]
    use_status_route = schema["paths"][CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT]["post"]
    use_status_request_ref = use_status_route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    use_status_request_schema = schema["components"]["schemas"][use_status_request_ref.rsplit("/", 1)[-1]]
    assert use_status_request_schema["additionalProperties"] is False
    for field in ("visual_lane_mode", "document_processing_engine", "local_path", "url", "default_selector"):
        assert field not in use_status_request_schema["properties"]
