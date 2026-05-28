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
    layer3_candidate_b_broader_scope_default_promotion,
    layer3_candidate_b_broader_scope_promotion_readiness,
    layer3_candidate_b_broader_scope_readiness,
    layer3_candidate_b_broader_scope_repeatability_trial,
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
OPERATOR_REPEATABILITY_TRIAL_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/operator-repeatability/trial"
)
PROMOTION_READINESS_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/promotion-readiness"
)
DEFAULT_PROMOTION_ENDPOINT = (
    "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/default-promotion"
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


def _consumption_receipt_use_status(
    client: TestClient,
    use_receipt: dict[str, object] | None = None,
) -> dict[str, object]:
    use_receipt = use_receipt or _consumption_receipt_use(client)
    response = client.post(
        CONSUMPTION_RECEIPT_USE_STATUS_ENDPOINT,
        json=_consumption_receipt_use_status_payload(use_receipt),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "available"
    return body


def _operator_repeatability_status_fields(prefix: str, status: dict[str, object]) -> dict[str, object]:
    consumption_binding = status["consumption_receipt_binding"]
    activation_binding = status["activation_receipt_binding"]
    selector_use_status_binding = status["selector_use_status_binding"]
    selector_use_receipt_binding = status["selector_use_receipt_binding"]
    runtime_binding = status["runtime_selection_receipt_binding"]
    readiness_binding = status["readiness_audit_binding"]
    return {
        f"{prefix}_use_receipt_status_hash": status["use_receipt_status_hash"],
        f"{prefix}_use_receipt_id": status["use_receipt_id"],
        f"{prefix}_use_receipt_hash": status["use_receipt_hash"],
        f"{prefix}_consumption_receipt_id": consumption_binding["consumption_receipt_id"],
        f"{prefix}_consumption_receipt_hash": consumption_binding["consumption_receipt_hash"],
        f"{prefix}_activation_receipt_id": activation_binding["activation_receipt_id"],
        f"{prefix}_activation_receipt_hash": activation_binding["activation_receipt_hash"],
        f"{prefix}_selector_use_status_hash": selector_use_status_binding["selector_use_status_hash"],
        f"{prefix}_selector_use_receipt_id": selector_use_receipt_binding["selector_use_receipt_id"],
        f"{prefix}_selector_use_receipt_hash": selector_use_receipt_binding["selector_use_receipt_hash"],
        f"{prefix}_runtime_selection_receipt_id": runtime_binding["runtime_selection_receipt_id"],
        f"{prefix}_runtime_selection_receipt_hash": runtime_binding["runtime_selection_receipt_hash"],
        f"{prefix}_readiness_audit_id": readiness_binding["readiness_audit_id"],
        f"{prefix}_readiness_audit_hash": readiness_binding["readiness_audit_hash"],
    }


def _operator_repeatability_trial_payload(
    original_status: dict[str, object],
    repeat_status: dict[str, object] | None = None,
    *,
    disposition: str = "no_regression_observed",
) -> dict[str, object]:
    repeat_status = repeat_status or original_status
    payload: dict[str, object] = {
        "client_request_id": "cb-broader-scope-operator-repeatability-trial-test",
        "trial_mode": layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_MODE,
        "operator_decision": layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_OPERATOR_DECISION,
        "operator_repeatability_disposition": disposition,
        "selected_scope_classes": original_status["selected_scope_classes"],
        "operator_confirmation": True,
    }
    payload.update(_operator_repeatability_status_fields("original", original_status))
    payload.update(_operator_repeatability_status_fields("repeat", repeat_status))
    return payload


def _operator_repeatability_trial(
    client: TestClient,
    status: dict[str, object] | None = None,
    *,
    disposition: str = "no_regression_observed",
) -> dict[str, object]:
    status = status or _consumption_receipt_use_status(client)
    response = client.post(
        OPERATOR_REPEATABILITY_TRIAL_ENDPOINT,
        json=_operator_repeatability_trial_payload(status, disposition=disposition),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _production_ownership_storage_policy() -> dict[str, object]:
    required_policy = layer3_candidate_b_broader_scope_promotion_readiness.REQUIRED_PRODUCTION_OWNERSHIP_STORAGE_POLICY
    return {
        "policy_runtime": required_policy,
        "storage_access_policy": (
            layer3_candidate_b_broader_scope_promotion_readiness.REQUIRED_STORAGE_ACCESS_POLICY
        ),
        "policy_status": "admitted",
        "policy_hash": "e" * 64,
    }


def _promotion_readiness_payload(
    trial: dict[str, object],
    *,
    operator_visible_status_confirmed: bool = True,
    production_ownership_storage_policy: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "client_request_id": "cb-broader-scope-promotion-readiness-test",
        "readiness_mode": layer3_candidate_b_broader_scope_promotion_readiness.READINESS_MODE,
        "operator_decision": layer3_candidate_b_broader_scope_promotion_readiness.OPERATOR_DECISION,
        "trial_receipt_id": trial["trial_receipt_id"],
        "trial_receipt_hash": trial["trial_receipt_hash"],
        "trial_authority_hash": trial["trial_authority_hash"],
        "authority_pair_hash": trial["authority_pair_hash"],
        "selected_scope_classes": trial["selected_scope_classes"],
        "production_ownership_storage_policy": (
            production_ownership_storage_policy
            if production_ownership_storage_policy is not None
            else _production_ownership_storage_policy()
        ),
        "operator_visible_status_confirmed": operator_visible_status_confirmed,
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }


def _promotion_readiness(
    client: TestClient,
    trial: dict[str, object] | None = None,
    *,
    operator_visible_status_confirmed: bool = True,
    production_ownership_storage_policy: dict[str, object] | None = None,
) -> dict[str, object]:
    trial = trial or _operator_repeatability_trial(client)
    response = client.post(
        PROMOTION_READINESS_ENDPOINT,
        json=_promotion_readiness_payload(
            trial,
            operator_visible_status_confirmed=operator_visible_status_confirmed,
            production_ownership_storage_policy=production_ownership_storage_policy,
        ),
    )
    assert response.status_code == 200, response.text
    return response.json()


def _default_promotion_payload(readiness: dict[str, object]) -> dict[str, object]:
    trial_binding = readiness["trial_receipt_binding"]
    policy = readiness["production_ownership_storage_policy"]
    return {
        "client_request_id": "cb-broader-scope-default-promotion-test",
        "promotion_mode": layer3_candidate_b_broader_scope_default_promotion.PROMOTION_MODE,
        "operator_decision": layer3_candidate_b_broader_scope_default_promotion.OPERATOR_DECISION,
        "promotion_readiness_audit_id": readiness["promotion_readiness_audit_id"],
        "promotion_readiness_audit_hash": readiness["promotion_readiness_audit_hash"],
        "promotion_readiness_audit": readiness,
        "trial_receipt_id": trial_binding["trial_receipt_id"],
        "trial_receipt_hash": trial_binding["trial_receipt_hash"],
        "selected_scope_classes": readiness["selected_scope_classes"],
        "production_policy_hash": policy["policy_hash"],
        "operator_visible_status_confirmed": True,
        "promotion_readiness_rendered_status_confirmed": True,
        "promotion_readiness_closeout_confirmed": True,
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
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


def test_candidate_b_broader_scope_selector_use_rejects_runtime_receipt_path_traversal(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    payload = _selector_use_payload(runtime_selection)
    payload["runtime_selection_receipt_id"] = "../cb-broader-scope-runtime-escape"

    response = client.post(SELECTOR_USE_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.SCHEMA_ID
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_broader_scope_selector_use_storage_id_invalid"
    assert body["error"]["details"]["field"] == "runtime_selection_receipt_id"


def test_candidate_b_broader_scope_selector_use_status_rejects_runtime_receipt_path_traversal(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)

    response = client.post(
        SELECTOR_USE_STATUS_ENDPOINT,
        json={
            "client_request_id": "cb-broader-scope-selector-use-status-traversal",
            "status_mode": layer3_candidate_b_broader_scope_selector_use.STATUS_MODE,
            "operator_decision": layer3_candidate_b_broader_scope_selector_use.STATUS_OPERATOR_DECISION,
            "selector_use_receipt_id": selector_use["selector_use_receipt_id"],
            "selector_use_receipt_hash": selector_use["selector_use_receipt_hash"],
            "runtime_selection_receipt_id": "..\\cb-broader-scope-runtime-escape",
            "runtime_selection_receipt_hash": runtime_selection["selection_receipt_hash"],
        },
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.STATUS_SCHEMA_ID
    assert body["status"] == "blocked"
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.STATUS_MODE
    assert body["error"]["code"] == "candidate_b_broader_scope_selector_use_storage_id_invalid"
    assert body["error"]["details"]["field"] == "runtime_selection_receipt_id"


def test_candidate_b_broader_scope_selector_use_status_uses_status_error_for_unreadable_runtime_receipt(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    runtime_receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-runtime"
        / f"{runtime_selection['selection_receipt_id']}.json"
    )
    runtime_receipt_path.write_text("{", encoding="utf-8")

    response = client.post(
        SELECTOR_USE_STATUS_ENDPOINT,
        json={
            "client_request_id": "cb-broader-scope-selector-use-status-unreadable-runtime",
            "status_mode": layer3_candidate_b_broader_scope_selector_use.STATUS_MODE,
            "operator_decision": layer3_candidate_b_broader_scope_selector_use.STATUS_OPERATOR_DECISION,
            "selector_use_receipt_id": selector_use["selector_use_receipt_id"],
            "selector_use_receipt_hash": selector_use["selector_use_receipt_hash"],
            "runtime_selection_receipt_id": runtime_selection["selection_receipt_id"],
            "runtime_selection_receipt_hash": runtime_selection["selection_receipt_hash"],
        },
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.STATUS_SCHEMA_ID
    assert body["status"] == "blocked"
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.STATUS_MODE
    assert body["error"]["code"] == "candidate_b_broader_scope_selector_use_receipt_unreadable"


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


def test_candidate_b_broader_scope_activation_consumption_uses_consumption_error_for_unreadable_existing_receipt(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    selector_activation = _selector_activation(client, selector_use_status)
    payload = _activation_consumption_payload(selector_use_status, selector_activation)
    first_response = client.post(ACTIVATION_CONSUMPTION_ENDPOINT, json=payload)
    assert first_response.status_code == 200, first_response.text
    first_body = first_response.json()
    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-activation-consumption"
        / f"{first_body['consumption_receipt_id']}.json"
    )
    receipt_path.write_text("{", encoding="utf-8")

    response = client.post(ACTIVATION_CONSUMPTION_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_SCHEMA_ID
    assert body["status"] == "blocked"
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_MODE
    assert body["error"]["code"] == "candidate_b_broader_scope_selector_use_receipt_unreadable"


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


def test_candidate_b_broader_scope_consumption_receipt_use_uses_use_error_for_unreadable_activation_receipt(
    client: TestClient,
) -> None:
    runtime_selection = _runtime_selection(client)
    selector_use = _selector_use(client, runtime_selection)
    selector_use_status = _selector_use_status(client, runtime_selection, selector_use)
    selector_activation = _selector_activation(client, selector_use_status)
    activation_consumption = _activation_consumption(client, selector_use_status, selector_activation)
    activation_receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-selector-activation"
        / f"{selector_activation['activation_receipt_id']}.json"
    )
    activation_receipt_path.write_text("{", encoding="utf-8")

    response = client.post(
        CONSUMPTION_RECEIPT_USE_ENDPOINT,
        json=_consumption_receipt_use_payload(selector_use_status, activation_consumption),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_SCHEMA_ID
    assert body["status"] == "blocked"
    assert body["mode"] == layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_MODE
    assert body["error"]["code"] == "candidate_b_broader_scope_selector_use_receipt_unreadable"


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


def test_candidate_b_broader_scope_operator_repeatability_trial_records_redacted_receipt(
    client: TestClient,
) -> None:
    use_receipt = _consumption_receipt_use(client)
    original_status = _consumption_receipt_use_status(client, use_receipt)
    repeat_status = _consumption_receipt_use_status(client, use_receipt)

    response = client.post(
        OPERATOR_REPEATABILITY_TRIAL_ENDPOINT,
        json=_operator_repeatability_trial_payload(original_status, repeat_status),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_repeatability_trial.SCHEMA_ID
    assert body["mode"] == layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_MODE
    assert body["status"] == "accepted"
    assert (
        body["operator_repeatability_trial_state"]
        == layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_ACCEPTED_STATE
    )
    assert body["operator_repeatability_disposition"] == "no_regression_observed"
    assert body["append_only_repeatability_trial_receipt"] is True
    assert body["exclusive_trial_per_original_repeat_authority_pair"] is True
    assert body["idempotent_replay"] is False
    assert body["selected_scope_classes"] == [SELECTED_CLASS]
    assert body["use_status_hash_comparison"] == "match"
    assert body["receipt_chain_hash_comparison"] == "match"
    assert body["selected_scope_classes_hash_comparison"] == "match"
    assert body["negative_invariants_hash_comparison"] == "match"
    assert body["readiness_audit_binding"]["binding_verified"] is True
    assert body["runtime_selection_receipt_binding"]["binding_verified"] is True
    assert body["selector_use_receipt_binding"]["binding_verified"] is True
    assert body["activation_receipt_binding"]["binding_verified"] is True
    assert body["consumption_receipt_binding"]["binding_verified"] is True
    assert body["trial_authority"]["process_execution_admitted"] is False
    assert body["default_scope_expansion_admitted"] is False
    assert body["actual_corpus_processing_execution_admitted"] is False
    assert body["actual_subprocess_spawn_admitted"] is False
    assert body["selector_mutation_performed"] is False
    assert body["default_scope_mutation_performed"] is False
    assert body["provider_object_write_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["rag_vector_model_runtime_enabled"] is False
    assert body["full_mockup_activation_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["artifact_bytes_exposed"] is False
    assert "C:" not in json.dumps(body, sort_keys=True)
    assert "https://" not in json.dumps(body, sort_keys=True)

    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-operator-repeatability-trial"
        / f"{body['trial_receipt_id']}.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["trial_receipt_hash"] == body["trial_receipt_hash"]
    assert receipt["operator_repeatability_disposition"] == "no_regression_observed"
    assert receipt["default_scope_expansion_admitted"] is False
    assert receipt["actual_corpus_processing_execution_admitted"] is False
    assert receipt["raw_local_path_exposed"] is False
    assert receipt["raw_url_exposed"] is False

    replay = client.post(
        OPERATOR_REPEATABILITY_TRIAL_ENDPOINT,
        json=_operator_repeatability_trial_payload(original_status, repeat_status),
    )
    assert replay.status_code == 200, replay.text
    replay_body = replay.json()
    assert replay_body["trial_receipt_id"] == body["trial_receipt_id"]
    assert replay_body["idempotent_replay"] is True


def test_candidate_b_broader_scope_operator_repeatability_trial_rejects_stale_repeat_status_hash(
    client: TestClient,
) -> None:
    use_receipt = _consumption_receipt_use(client)
    original_status = _consumption_receipt_use_status(client, use_receipt)
    payload = _operator_repeatability_trial_payload(original_status)
    payload["repeat_use_receipt_status_hash"] = "a" * 64

    response = client.post(OPERATOR_REPEATABILITY_TRIAL_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_repeatability_trial.SCHEMA_ID
    assert body["status"] == "blocked"
    assert body["mode"] == layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_MODE
    assert (
        body["error"]["code"]
        == "candidate_b_broader_scope_operator_repeatability_trial_stale_repeat_use_status_hash"
    )


def test_candidate_b_broader_scope_operator_repeatability_trial_rejects_missing_repeat_use_receipt(
    client: TestClient,
) -> None:
    use_receipt = _consumption_receipt_use(client)
    original_status = _consumption_receipt_use_status(client, use_receipt)
    payload = _operator_repeatability_trial_payload(original_status)
    payload["repeat_use_receipt_id"] = (
        f"{layer3_candidate_b_broader_scope_selector_use.CONSUMPTION_USE_RECEIPT_PREFIX}-missing"
    )
    payload["repeat_use_receipt_hash"] = "b" * 64
    payload["repeat_use_receipt_status_hash"] = "c" * 64

    response = client.post(OPERATOR_REPEATABILITY_TRIAL_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    assert (
        body["error"]["code"]
        == "candidate_b_broader_scope_operator_repeatability_trial_repeat_use_status_not_available"
    )


def test_candidate_b_broader_scope_operator_repeatability_trial_rejects_mismatched_readiness_authority(
    client: TestClient,
) -> None:
    use_receipt = _consumption_receipt_use(client)
    original_status = _consumption_receipt_use_status(client, use_receipt)
    payload = _operator_repeatability_trial_payload(original_status)
    payload["repeat_readiness_audit_hash"] = "d" * 64

    response = client.post(OPERATOR_REPEATABILITY_TRIAL_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    assert (
        body["error"]["code"]
        == "candidate_b_broader_scope_operator_repeatability_trial_repeat_use_status_invalid"
    )
    assert (
        body["error"]["details"]["authority_error_code"]
        == "candidate_b_broader_scope_consumption_receipt_use_status_authority_invalid"
    )


def test_candidate_b_broader_scope_operator_repeatability_trial_records_blocked_disposition(
    client: TestClient,
) -> None:
    use_receipt = _consumption_receipt_use(client)
    original_status = _consumption_receipt_use_status(client, use_receipt)

    response = client.post(
        OPERATOR_REPEATABILITY_TRIAL_ENDPOINT,
        json=_operator_repeatability_trial_payload(
            original_status,
            disposition=layer3_candidate_b_broader_scope_repeatability_trial.BLOCKED_DISPOSITION,
        ),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert (
        body["operator_repeatability_trial_state"]
        == layer3_candidate_b_broader_scope_repeatability_trial.TRIAL_BLOCKED_STATE
    )
    assert body["operator_repeatability_disposition"] == "regression_detected_blocked"
    assert body["trial_receipt_status"] == "recorded"
    assert body["default_scope_expansion_admitted"] is False
    assert body["selector_mutation_performed"] is False
    assert body["default_scope_mutation_performed"] is False


def test_candidate_b_broader_scope_promotion_readiness_accepts_receipt_bound_trial(
    client: TestClient,
) -> None:
    trial = _operator_repeatability_trial(client)

    response = client.post(PROMOTION_READINESS_ENDPOINT, json=_promotion_readiness_payload(trial))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_promotion_readiness.SCHEMA_ID
    assert body["status"] == "ready"
    assert (
        body["promotion_readiness_state"]
        == layer3_candidate_b_broader_scope_promotion_readiness.READY_STATE
    )
    assert body["promotion_readiness_audit_id"].startswith("cb-broader-scope-promotion-readiness-")
    assert body["blocked_reasons"] == []
    assert body["selected_scope_classes"] == [SELECTED_CLASS]
    assert body["trial_receipt_binding"]["binding_verified"] is True
    assert body["trial_receipt_binding"]["trial_receipt_id"] == trial["trial_receipt_id"]
    assert body["trial_receipt_binding"]["operator_repeatability_disposition"] == "no_regression_observed"
    assert body["production_ownership_storage_policy"]["binding_verified"] is True
    required_policy = layer3_candidate_b_broader_scope_promotion_readiness.REQUIRED_PRODUCTION_OWNERSHIP_STORAGE_POLICY
    assert (
        body["production_ownership_storage_policy"]["policy_runtime"]
        == required_policy
    )
    assert body["operator_visible_status_evidence"]["operator_visible_status_confirmed"] is True
    assert body["baseline_rollback"]["selector"] == "baseline"
    assert body["candidate_a_semantics"]["preserved"] is True
    assert body["default_scope_promotion_ready_for_separate_selection"] is True
    assert body["selector_mutation_admitted_now"] is False
    assert body["selector_mutation_performed"] is False
    assert body["default_scope_expansion_admitted"] is False
    assert body["default_scope_mutation_performed"] is False
    assert body["source_expansion_admitted"] is False
    assert body["provider_object_write_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["rag_vector_model_runtime_enabled"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False


def test_candidate_b_broader_scope_promotion_readiness_blocks_blocked_repeatability_trial(
    client: TestClient,
) -> None:
    trial = _operator_repeatability_trial(
        client,
        disposition=layer3_candidate_b_broader_scope_repeatability_trial.BLOCKED_DISPOSITION,
    )

    response = client.post(PROMOTION_READINESS_ENDPOINT, json=_promotion_readiness_payload(trial))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert (
        body["promotion_readiness_state"]
        == layer3_candidate_b_broader_scope_promotion_readiness.BLOCKED_STATE
    )
    codes = {reason["code"] for reason in body["blocked_reasons"]}
    assert (
        "candidate_b_broader_scope_promotion_readiness_repeatability_trial_not_accepted"
        in codes
    )
    assert (
        "candidate_b_broader_scope_promotion_readiness_repeatability_disposition_not_ready"
        in codes
    )
    assert body["default_scope_promotion_ready_for_separate_selection"] is False
    assert body["selector_mutation_performed"] is False
    assert body["default_scope_mutation_performed"] is False


def test_candidate_b_broader_scope_promotion_readiness_blocks_stale_trial_hash(
    client: TestClient,
) -> None:
    trial = _operator_repeatability_trial(client)
    payload = _promotion_readiness_payload(trial)
    payload["trial_receipt_hash"] = "a" * 64

    response = client.post(PROMOTION_READINESS_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {reason["code"] for reason in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_promotion_readiness_trial_receipt_field_mismatch" in codes
    assert body["trial_receipt_binding"]["binding_verified"] is False
    assert body["default_scope_promotion_ready_for_separate_selection"] is False


def test_candidate_b_broader_scope_promotion_readiness_blocks_missing_policy_and_status(
    client: TestClient,
) -> None:
    trial = _operator_repeatability_trial(client)
    payload = _promotion_readiness_payload(trial, operator_visible_status_confirmed=False)
    payload["production_ownership_storage_policy"] = None

    response = client.post(PROMOTION_READINESS_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {reason["code"] for reason in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_promotion_readiness_operator_visible_status_missing" in codes
    assert "candidate_b_broader_scope_promotion_readiness_production_policy_missing" in codes
    assert body["production_ownership_storage_policy"]["binding_verified"] is False
    assert body["default_scope_promotion_ready_for_separate_selection"] is False
    assert body["selector_mutation_performed"] is False


def test_candidate_b_broader_scope_default_promotion_records_redacted_receipt(
    client: TestClient,
) -> None:
    readiness = _promotion_readiness(client)

    response = client.post(DEFAULT_PROMOTION_ENDPOINT, json=_default_promotion_payload(readiness))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_default_promotion.SCHEMA_ID
    assert body["mode"] == layer3_candidate_b_broader_scope_default_promotion.PROMOTION_MODE
    assert body["status"] == "selected"
    assert (
        body["default_promotion_state"]
        == layer3_candidate_b_broader_scope_default_promotion.SELECTED_STATE
    )
    assert body["default_promotion_receipt_id"].startswith("cb-broader-scope-default-promotion-")
    assert body["default_promotion_receipt_status"] == "recorded"
    assert body["idempotent_replay"] is False
    assert body["promotion_readiness_audit_binding"]["binding_verified"] is True
    assert body["trial_receipt_binding"]["binding_verified"] is True
    assert body["production_ownership_storage_policy"]["binding_verified"] is True
    assert body["selected_scope_classes"] == [SELECTED_CLASS]
    assert body["default_scope_promotion_enabled_for_selected_classes"] is True
    assert body["default_scope_policy_mutation_performed"] is True
    assert body["default_scope_expansion_mutation_performed"] is True
    assert body["non_selected_class_default"] == "baseline"
    assert body["baseline_rollback"]["available"] is True
    assert body["candidate_a_semantics"]["preserved"] is True
    assert body["candidate_b_scope_authority"]["bundle_and_runtime_authority_remain_distinct"] is True
    assert body["operator_visible_status_evidence"]["redacted_default_promotion_receipt_available"] is True
    assert body["selector_mutation_performed"] is False
    assert body["source_expansion_admitted"] is False
    assert body["runtime_db_or_storage_expansion_admitted"] is False
    assert body["provider_object_write_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["rag_vector_model_runtime_enabled"] is False
    assert body["frontend_durable_authority_enabled"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["artifact_bytes_exposed"] is False
    assert body["default_promotion_receipt_ref"].startswith(
        "candidate-b-broader-scope-default-promotion://"
    )
    assert "C:" not in json.dumps(body, sort_keys=True)
    assert "https://" not in json.dumps(body, sort_keys=True)

    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-default-promotion"
        / f"{body['default_promotion_receipt_id']}.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["default_promotion_receipt_hash"] == body["default_promotion_receipt_hash"]
    assert receipt["promotion_readiness_audit_hash"] == readiness["promotion_readiness_audit_hash"]
    assert receipt["trial_receipt_hash"] == readiness["trial_receipt_binding"]["trial_receipt_hash"]
    assert receipt["selected_scope_classes"] == [SELECTED_CLASS]
    assert receipt["default_scope_promotion_enabled_for_selected_classes"] is True
    assert receipt["raw_local_path_exposed"] is False
    assert receipt["raw_url_exposed"] is False

    replay = client.post(DEFAULT_PROMOTION_ENDPOINT, json=_default_promotion_payload(readiness))
    assert replay.status_code == 200, replay.text
    replay_body = replay.json()
    assert replay_body["default_promotion_receipt_id"] == body["default_promotion_receipt_id"]
    assert replay_body["default_promotion_receipt_status"] == "idempotent_replay"
    assert replay_body["idempotent_replay"] is True


def test_candidate_b_broader_scope_default_promotion_blocks_blocked_readiness(
    client: TestClient,
) -> None:
    trial = _operator_repeatability_trial(
        client,
        disposition=layer3_candidate_b_broader_scope_repeatability_trial.BLOCKED_DISPOSITION,
    )
    readiness = _promotion_readiness(client, trial)

    response = client.post(DEFAULT_PROMOTION_ENDPOINT, json=_default_promotion_payload(readiness))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert (
        body["default_promotion_state"]
        == layer3_candidate_b_broader_scope_default_promotion.BLOCKED_STATE
    )
    assert body["default_promotion_receipt_status"] == "not_recorded"
    assert body["default_promotion_receipt_id"] is None
    assert body["default_scope_promotion_enabled_for_selected_classes"] is False
    assert body["default_scope_policy_mutation_performed"] is False
    codes = {reason["code"] for reason in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_default_promotion_readiness_audit_blocked" in codes
    assert "candidate_b_broader_scope_default_promotion_readiness_not_ready" in codes


def test_candidate_b_broader_scope_default_promotion_blocks_stale_readiness_hash(
    client: TestClient,
) -> None:
    readiness = _promotion_readiness(client)
    payload = _default_promotion_payload(readiness)
    payload["promotion_readiness_audit_hash"] = "a" * 64

    response = client.post(DEFAULT_PROMOTION_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["default_promotion_receipt_status"] == "not_recorded"
    codes = {reason["code"] for reason in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_default_promotion_readiness_audit_field_mismatch" in codes
    assert "candidate_b_broader_scope_default_promotion_stale_readiness_audit_hash" in codes


def test_candidate_b_broader_scope_default_promotion_rejects_browser_default_authority(
    client: TestClient,
) -> None:
    readiness = _promotion_readiness(client)
    payload = _default_promotion_payload(readiness)
    payload["default_selector"] = "candidate_b"

    response = client.post(DEFAULT_PROMOTION_ENDPOINT, json=payload)

    assert response.status_code == 422, response.text


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
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial_admitted"]
        is True
    )
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial_endpoint"]
        == OPERATOR_REPEATABILITY_TRIAL_ENDPOINT
    )
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_promotion_readiness_admitted"]
        is True
    )
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_promotion_readiness_endpoint"]
        == PROMOTION_READINESS_ENDPOINT
    )
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_default_promotion_admitted"]
        is True
    )
    assert (
        readiness_body["candidate_b_broader_eligible_corpus_default_scope_default_promotion_endpoint"]
        == DEFAULT_PROMOTION_ENDPOINT
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
        bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial"]
        is True
    )
    assert (
        bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_promotion_readiness"]
        is True
    )
    assert (
        bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_default_promotion"]
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
    assert (
        bootstrap_body["execution_readiness"][
            "candidate_b_broader_eligible_corpus_default_scope_operator_repeatability_trial_endpoint"
        ]
        == OPERATOR_REPEATABILITY_TRIAL_ENDPOINT
    )
    assert (
        bootstrap_body["execution_readiness"][
            "candidate_b_broader_eligible_corpus_default_scope_promotion_readiness_endpoint"
        ]
        == PROMOTION_READINESS_ENDPOINT
    )
    assert (
        bootstrap_body["execution_readiness"][
            "candidate_b_broader_eligible_corpus_default_scope_default_promotion_endpoint"
        ]
        == DEFAULT_PROMOTION_ENDPOINT
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
    trial_route = schema["paths"][OPERATOR_REPEATABILITY_TRIAL_ENDPOINT]["post"]
    trial_request_ref = trial_route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    trial_request_schema = schema["components"]["schemas"][trial_request_ref.rsplit("/", 1)[-1]]
    assert trial_request_schema["additionalProperties"] is False
    for field in (
        "visual_lane_mode",
        "document_processing_engine",
        "local_path",
        "url",
        "default_selector",
        "process_command",
    ):
        assert field not in trial_request_schema["properties"]
    promotion_route = schema["paths"][PROMOTION_READINESS_ENDPOINT]["post"]
    promotion_request_ref = promotion_route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    promotion_request_schema = schema["components"]["schemas"][promotion_request_ref.rsplit("/", 1)[-1]]
    assert promotion_request_schema["additionalProperties"] is False
    for field in (
        "visual_lane_mode",
        "document_processing_engine",
        "local_path",
        "url",
        "default_selector",
        "process_command",
        "provider_private_signed_url_token",
    ):
        assert field not in promotion_request_schema["properties"]
    default_promotion_route = schema["paths"][DEFAULT_PROMOTION_ENDPOINT]["post"]
    default_promotion_request_ref = default_promotion_route["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ]
    default_promotion_request_schema = schema["components"]["schemas"][
        default_promotion_request_ref.rsplit("/", 1)[-1]
    ]
    assert default_promotion_request_schema["additionalProperties"] is False
    for field in (
        "visual_lane_mode",
        "document_processing_engine",
        "local_path",
        "url",
        "default_selector",
        "process_command",
        "provider_private_signed_url_token",
        "runtime_storage_dir",
    ):
        assert field not in default_promotion_request_schema["properties"]
