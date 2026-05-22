from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_candidate_b_runtime_bridge
from main import app


STATUS_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/visual-lane/status"
CANDIDATE_B_RUN_ID = "candidate-b-runtime-run"
CANDIDATE_B_VISUAL_LANE_MODE = "candidate_b_opendataloader_page_evidence_v1"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "layer3_candidate_b_runtime_bridge_dir", str(tmp_path / "runtime-bridge"))
    app.openapi_schema = None
    with TestClient(app) as test_client:
        yield test_client
    app.openapi_schema = None


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_runtime_receipt(*, visual_lane_mode: str = CANDIDATE_B_VISUAL_LANE_MODE) -> str:
    receipt_input = {
        "schema_id": layer3_candidate_b_runtime_bridge.SCHEMA_ID,
        "schema_version": layer3_candidate_b_runtime_bridge.SCHEMA_VERSION,
        "bridge_mode": layer3_candidate_b_runtime_bridge.BRIDGE_MODE,
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "candidate_b_source_kind": "runtime",
        "document_processing_engine": "candidate_b_opendataloader_pdf",
        "visual_lane_mode": visual_lane_mode,
        "compare_target_set_hash": "1" * 64,
        "runtime_review_root_storage_authority_hash": "2" * 64,
        "admitted_file_subset_hash": "3" * 64,
        "governed_retained_artifact_family_hash": "4" * 64,
        "redaction_policy_id": layer3_candidate_b_runtime_bridge.REDACTION_POLICY_ID,
    }
    receipt_hash = _stable_hash(receipt_input)
    receipt_id = f"{layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX}-{receipt_hash[:24]}"
    receipt = {
        **receipt_input,
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_hash": receipt_hash,
        "candidate_b_visual_lane_evidence": {
            "visual_lane_mode": visual_lane_mode,
            "candidate_b_visual_lane_selected": visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE,
            "candidate_b_visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
            "visual_ref_total": 3 if visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE else 0,
            "candidate_b_visual_ref_total": 3 if visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE else 0,
            "candidate_b_retained_source_pdf_ref_count": (
                1 if visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE else 0
            ),
            "source_pdf_material_text_payload_enabled": False,
            "image_material_text_payload_enabled": False,
            "evidence_source": "runtime_summary_advanced_metrics",
        },
    }
    _write_json(Path(settings.layer3_candidate_b_runtime_bridge_dir) / receipt_id / "receipt.json", receipt)
    return receipt_id


def _payload(receipt_id: str) -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-visual-lane-status",
        "status_mode": "candidate_b_visual_lane_status_v1",
        "operator_decision": "inspect_candidate_b_visual_lane_evidence_status",
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "bridge_receipt_id": receipt_id,
    }


def test_candidate_b_visual_lane_status_projects_runtime_evidence(client: TestClient, tmp_path: Path) -> None:
    receipt_id = _write_runtime_receipt()

    response = client.post(STATUS_ENDPOINT, json=_payload(receipt_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "available"
    assert body["candidate_b_source_kind"] == "runtime"
    assert body["candidate_b_run_id"] == CANDIDATE_B_RUN_ID
    assert body["bridge_receipt_id"] == receipt_id
    assert body["document_processing_engine"] == "candidate_b_opendataloader_pdf"
    assert body["visual_lane_mode"] == CANDIDATE_B_VISUAL_LANE_MODE
    assert body["visual_lane_status"] == "available"
    assert body["candidate_b_visual_lane_evidence"]["candidate_b_visual_lane_selected"] is True
    assert body["candidate_b_visual_lane_evidence"]["candidate_b_visual_ref_total"] == 3
    assert body["operator_projection"]["candidate_b_visual_lane_status_projection_visible"] is True
    assert body["operator_projection"]["artifact_bytes_exposed"] is False
    assert body["material_policy"]["visual_lane_material_ingestion_enabled"] is False
    assert body["negative_invariants"]["candidate_b_default_promotion_enabled"] is False
    assert body["negative_invariants"]["source_pdf_material_text_payload_enabled"] is False
    assert body["negative_invariants"]["image_material_text_payload_enabled"] is False
    assert str(tmp_path) not in json.dumps(body, sort_keys=True)
    assert "C:\\" not in json.dumps(body, sort_keys=True)


def test_candidate_b_visual_lane_status_fails_closed_for_baseline_visual_lane(client: TestClient) -> None:
    receipt_id = _write_runtime_receipt(visual_lane_mode="baseline")

    response = client.post(STATUS_ENDPOINT, json=_payload(receipt_id))

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "candidate_b_visual_lane_status_bridge_receipt_mismatch"


def test_candidate_b_visual_lane_status_fails_closed_on_stale_hash(client: TestClient) -> None:
    receipt_id = _write_runtime_receipt()
    receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["runtime_review_root_storage_authority_hash"] = "9" * 64
    _write_json(receipt_path, receipt)

    response = client.post(STATUS_ENDPOINT, json=_payload(receipt_id))

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "candidate_b_visual_lane_status_bridge_receipt_hash_mismatch"


def test_candidate_b_visual_lane_status_rejects_selector_path_and_url_fields(client: TestClient) -> None:
    receipt_id = _write_runtime_receipt()
    response = client.post(
        STATUS_ENDPOINT,
        json={
            **_payload(receipt_id),
            "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
            "local_path": "C:/private/source",
            "url": "https://example.test",
        },
    )

    assert response.status_code == 422
    schema = client.app.openapi()
    route = schema["paths"][STATUS_ENDPOINT]["post"]
    request_ref = route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]
    assert request_schema["additionalProperties"] is False
    assert "visual_lane_mode" not in request_schema["properties"]
    assert "local_path" not in request_schema["properties"]
    assert "url" not in request_schema["properties"]
