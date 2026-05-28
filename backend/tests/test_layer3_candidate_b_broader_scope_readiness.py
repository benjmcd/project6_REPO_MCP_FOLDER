from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_candidate_b_broader_scope_readiness
from main import app


ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/broader-eligible-corpus/scope-readiness-audit"
SCOPE_CLASSES = list(layer3_candidate_b_broader_scope_readiness.SCOPE_CLASSES)
EXCLUSIONS = list(layer3_candidate_b_broader_scope_readiness.REQUIRED_EXCLUSIONS)


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


def _payload() -> dict[str, object]:
    return {
        "client_request_id": "cb-broader-scope-readiness-test",
        "audit_mode": layer3_candidate_b_broader_scope_readiness.AUDIT_MODE,
        "exact_corpus_class_list": SCOPE_CLASSES,
        "explicit_exclusion_list": EXCLUSIONS,
        "proposed_default_scope_classes": ["structured_json_or_csv_or_xlsx"],
        "scope_evidence": _ready_scope_evidence(),
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }


def test_candidate_b_broader_scope_readiness_audit_ready_for_separate_selection(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "layer3_candidate_b_runtime_bridge_dir", str(tmp_path / "runtime-bridge"))

    with TestClient(app) as client:
        response = client.post(ENDPOINT, json=_payload())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == layer3_candidate_b_broader_scope_readiness.SCHEMA_ID
    assert body["mode"] == layer3_candidate_b_broader_scope_readiness.AUDIT_MODE
    assert body["status"] == "ready"
    assert body["audit_state"] == "candidate_b_broader_eligible_corpus_scope_ready_for_separate_selection"
    assert body["audit_state"] == layer3_candidate_b_broader_scope_readiness.READY_STATE
    assert body["current_default_scope"] == "eligible_effective_pdfs_only"
    assert body["proposed_default_scope_classes"] == ["structured_json_or_csv_or_xlsx"]
    assert body["default_scope_expansion_admitted"] is False
    assert body["selector_mutation_performed"] is False
    assert body["source_expansion_admitted"] is False
    assert body["runtime_db_or_storage_expansion_admitted"] is False
    assert body["provider_object_write_enabled"] is False
    assert body["connector_dispatch_enabled"] is False
    assert body["rag_vector_model_runtime_enabled"] is False
    assert body["full_mockup_activation_enabled"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["audit_receipt_status"] == "recorded"
    assert body["audit_receipt_ref"].startswith("candidate-b-broader-scope-readiness://")
    ready_rows = [
        row
        for row in body["scope_class_results"]
        if row["scope_readiness"] == "ready_for_separate_selection"
    ]
    assert [row["scope_class"] for row in ready_rows] == ["structured_json_or_csv_or_xlsx"]
    receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / "broader-scope-readiness"
        / f"{body['audit_id']}.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["audit_hash"] == body["audit_hash"]
    assert receipt["readiness_audit"]["audit_id"] == body["audit_id"]
    assert receipt["readiness_audit"]["candidate_a_semantics"]["visual_lane_mode"] == "candidate_a_page_evidence_v1"


def test_candidate_b_broader_scope_readiness_blocks_missing_scope_evidence() -> None:
    payload = _payload()
    payload["scope_evidence"] = _ready_scope_evidence()
    del payload["scope_evidence"]["structured_json_or_csv_or_xlsx"]  # type: ignore[index]

    with TestClient(app) as client:
        response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["audit_state"] == layer3_candidate_b_broader_scope_readiness.BLOCKED_STATE
    assert body["default_scope_expansion_admitted"] is False
    assert body["selector_mutation_performed"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_broader_scope_readiness_scope_class_evidence_missing" in codes


def test_candidate_b_broader_scope_readiness_rejects_nested_path_and_selector_fields() -> None:
    payload = _payload()
    scope_evidence = dict(payload["scope_evidence"])  # type: ignore[arg-type]
    structured = dict(scope_evidence["structured_json_or_csv_or_xlsx"])
    structured["local_path"] = "C:/private/source"
    scope_evidence["structured_json_or_csv_or_xlsx"] = structured
    payload["scope_evidence"] = scope_evidence

    with TestClient(app) as client:
        response = client.post(ENDPOINT, json=payload)
        schema = client.app.openapi()

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_broader_scope_readiness_forbidden_request_fields"
    assert "scope_evidence.structured_json_or_csv_or_xlsx.local_path" in body["error"]["details"]["blocked_fields"]

    route = schema["paths"][ENDPOINT]["post"]
    request_ref = route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]
    assert request_schema["additionalProperties"] is False
    for field in ("visual_lane_mode", "document_processing_engine", "local_path", "url", "default_selector"):
        assert field not in request_schema["properties"]


def test_candidate_b_broader_scope_readiness_is_exposed_in_readiness_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/layer3/readiness")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidate_b_broader_eligible_corpus_scope_readiness_audit_admitted"] is True
    assert body["candidate_b_broader_eligible_corpus_scope_readiness_audit_endpoint"] == ENDPOINT
