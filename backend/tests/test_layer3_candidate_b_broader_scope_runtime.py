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
)
from main import app


READINESS_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/scope-readiness-audit"
RUNTIME_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/default-scope/runtime"
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


def _readiness_payload() -> dict[str, object]:
    return {
        "client_request_id": "cb-broader-scope-runtime-readiness-test",
        "audit_mode": layer3_candidate_b_broader_scope_readiness.AUDIT_MODE,
        "exact_corpus_class_list": SCOPE_CLASSES,
        "explicit_exclusion_list": EXCLUSIONS,
        "proposed_default_scope_classes": [SELECTED_CLASS],
        "scope_evidence": _ready_scope_evidence(),
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }


def _ready_audit(client: TestClient) -> dict[str, object]:
    response = client.post(READINESS_ENDPOINT, json=_readiness_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready"
    return body


def _runtime_payload(readiness_audit: dict[str, object]) -> dict[str, object]:
    return {
        "client_request_id": "cb-broader-scope-runtime-test",
        "runtime_mode": layer3_candidate_b_broader_scope_runtime.RUNTIME_MODE,
        "readiness_audit_id": readiness_audit["audit_id"],
        "readiness_audit_hash": readiness_audit["audit_hash"],
        "readiness_audit": readiness_audit,
        "selected_scope_classes": [SELECTED_CLASS],
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }


def test_candidate_b_broader_scope_runtime_records_redacted_selection_receipt(client: TestClient) -> None:
    readiness_audit = _ready_audit(client)

    response = client.post(RUNTIME_ENDPOINT, json=_runtime_payload(readiness_audit))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_runtime.SCHEMA_ID
    assert body["mode"] == layer3_candidate_b_broader_scope_runtime.RUNTIME_MODE
    assert body["status"] == "selected"
    assert body["runtime_state"] == layer3_candidate_b_broader_scope_runtime.SELECTED_STATE
    assert body["runtime_state"] == "candidate_b_broader_eligible_corpus_default_scope_runtime_selected"
    assert body["selected_scope_classes"] == [SELECTED_CLASS]
    assert body["current_default_scope_preserved"] == "eligible_effective_pdfs_only"
    assert body["non_pdf_default_preserved"] == "baseline"
    assert body["readiness_audit_binding"]["binding_verified"] is True
    assert body["default_scope_expansion_enabled"] is True
    assert body["selector_mutation_performed"] is False
    assert body["source_expansion_admitted"] is False
    assert body["runtime_db_or_storage_expansion_admitted"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["operator_visible_scope_status"]["redacted_selection_receipt_available"] is True
    assert body["selection_receipt_ref"].startswith("candidate-b-broader-scope-runtime://")
    assert "://" in body["selection_receipt_ref"]
    assert "C:" not in json.dumps(body, sort_keys=True)
    assert "https://" not in json.dumps(body, sort_keys=True)

    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-runtime"
        / f"{body['selection_receipt_id']}.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["selection_receipt_hash"] == body["selection_receipt_hash"]
    assert receipt["selected_scope_classes"] == [SELECTED_CLASS]
    assert receipt["raw_local_path_exposed"] is False
    assert receipt["raw_url_exposed"] is False


def test_candidate_b_broader_scope_runtime_fails_closed_without_ready_audit(client: TestClient) -> None:
    response = client.post(
        RUNTIME_ENDPOINT,
        json={
            "client_request_id": "cb-broader-scope-runtime-missing-audit",
            "runtime_mode": layer3_candidate_b_broader_scope_runtime.RUNTIME_MODE,
            "readiness_audit_id": "cb-broader-scope-readiness-missing",
            "readiness_audit_hash": "a" * 64,
            "readiness_audit": {},
            "selected_scope_classes": [SELECTED_CLASS],
            "rollback_to_baseline_confirmation": True,
            "operator_confirmation": True,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["runtime_state"] == layer3_candidate_b_broader_scope_runtime.BLOCKED_STATE
    assert body["runtime_state"] == "candidate_b_broader_eligible_corpus_default_scope_runtime_blocked"
    assert body["selection_receipt_status"] == "not_recorded"
    assert body["selection_receipt_id"] is None
    assert body["default_scope_expansion_enabled"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_runtime_ready_audit_field_mismatch" in codes
    assert "candidate_b_broader_scope_runtime_server_ready_audit_receipt_unavailable" in codes


def test_candidate_b_broader_scope_runtime_rejects_fabricated_non_server_audit(
    client: TestClient,
    monkeypatch,
) -> None:
    runtime_dir = settings.layer3_candidate_b_runtime_bridge_dir
    monkeypatch.setattr(settings, "layer3_candidate_b_runtime_bridge_dir", "")
    fabricated_audit = layer3_candidate_b_broader_scope_readiness.evaluate_candidate_b_broader_scope_readiness(
        _readiness_payload()
    )
    assert fabricated_audit["status"] == "ready"
    assert fabricated_audit["audit_receipt_status"] == "not_recorded"
    monkeypatch.setattr(settings, "layer3_candidate_b_runtime_bridge_dir", runtime_dir)

    response = client.post(RUNTIME_ENDPOINT, json=_runtime_payload(fabricated_audit))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["readiness_audit_binding"]["server_issued_receipt_required"] is True
    assert body["readiness_audit_binding"]["binding_verified"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_runtime_server_ready_audit_receipt_unavailable" in codes
    assert body["selection_receipt_status"] == "not_recorded"


def test_candidate_b_broader_scope_runtime_rejects_persisted_semantic_drift(client: TestClient) -> None:
    readiness_audit = _ready_audit(client)
    drifted_audit = json.loads(json.dumps(readiness_audit))
    drifted_audit["candidate_a_semantics"]["visual_lane_mode"] = "candidate_a_semantic_drift"
    drifted_hash = layer3_candidate_b_broader_scope_runtime._readiness_audit_hash(drifted_audit)
    drifted_audit["audit_hash"] = drifted_hash
    drifted_audit["audit_id"] = f"cb-broader-scope-readiness-{drifted_hash[:24]}"
    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-readiness"
        / f"{drifted_audit['audit_id']}.json"
    )
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {
                "schema_id": "layer3.candidate_b_broader_eligible_corpus_scope_readiness_audit_receipt.v1",
                "schema_version": 1,
                "audit_id": drifted_audit["audit_id"],
                "audit_hash": drifted_hash,
                "readiness_audit": drifted_audit,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    response = client.post(RUNTIME_ENDPOINT, json=_runtime_payload(drifted_audit))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["selection_receipt_status"] == "not_recorded"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_runtime_ready_audit_semantic_authority_drift" in codes


def test_candidate_b_broader_scope_runtime_rejects_stale_hash_and_unproposed_class(client: TestClient) -> None:
    readiness_audit = _ready_audit(client)
    payload = _runtime_payload(readiness_audit)
    payload["readiness_audit_hash"] = "b" * 64
    payload["selected_scope_classes"] = ["office_documents"]

    response = client.post(RUNTIME_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["selection_receipt_status"] == "not_recorded"
    assert body["default_scope_expansion_enabled"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_runtime_server_ready_audit_receipt_unavailable" in codes
    assert "candidate_b_broader_scope_runtime_ready_audit_field_mismatch" in codes
    assert "candidate_b_broader_scope_runtime_stale_audit_hash" in codes


def test_candidate_b_broader_scope_runtime_rejects_unproposed_class_from_server_audit(client: TestClient) -> None:
    readiness_audit = _ready_audit(client)
    payload = _runtime_payload(readiness_audit)
    payload["selected_scope_classes"] = ["office_documents"]

    response = client.post(RUNTIME_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["selection_receipt_status"] == "not_recorded"
    assert body["default_scope_expansion_enabled"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_runtime_selected_classes_do_not_match_ready_audit" in codes
    assert "candidate_b_broader_scope_runtime_unproposed_scope_class" in codes


def test_candidate_b_broader_scope_runtime_rejects_nested_path_authority(client: TestClient) -> None:
    readiness_audit = _ready_audit(client)
    readiness_audit["scope_class_results"][0]["local_path"] = "C:/private/source"
    payload = _runtime_payload(readiness_audit)

    response = client.post(RUNTIME_ENDPOINT, json=payload)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_broader_scope_runtime_forbidden_request_fields"
    assert "readiness_audit.scope_class_results[0].local_path" in body["error"]["details"]["blocked_fields"]


def test_candidate_b_broader_scope_runtime_is_exposed_in_contracts(client: TestClient) -> None:
    readiness = client.get("/api/v1/layer3/readiness")
    bootstrap = client.get("/api/v1/layer3/bootstrap")

    assert readiness.status_code == 200, readiness.text
    readiness_body = readiness.json()
    assert readiness_body["candidate_b_broader_eligible_corpus_default_scope_runtime_admitted"] is True
    assert readiness_body["candidate_b_broader_eligible_corpus_default_scope_runtime_endpoint"] == RUNTIME_ENDPOINT

    assert bootstrap.status_code == 200, bootstrap.text
    bootstrap_body = bootstrap.json()
    assert bootstrap_body["features"]["candidate_b_broader_eligible_corpus_default_scope_runtime"] is True
    assert (
        bootstrap_body["execution_readiness"]["candidate_b_broader_eligible_corpus_default_scope_runtime_endpoint"]
        == RUNTIME_ENDPOINT
    )

    schema = client.app.openapi()
    route = schema["paths"][RUNTIME_ENDPOINT]["post"]
    request_ref = route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]
    assert request_schema["additionalProperties"] is False
    for field in ("visual_lane_mode", "document_processing_engine", "local_path", "url", "default_selector"):
        assert field not in request_schema["properties"]
