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
from app.services import (
    layer3_candidate_b_artifact_status,
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_runtime_bridge,
)
from main import app


STATUS_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/artifact-family/status"


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "layer3_candidate_b_bundle_bridge_dir", str(tmp_path / "bundle-bridge"))
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


def _artifact_family(kind: str) -> dict[str, Any]:
    visual_ref = "raw/annotated/fontish.pdf" if kind == "bundle" else "storage/input.pdf"
    image_ref = "raw/images/fontish/imageFile1.png" if kind == "bundle" else "storage/image.png"
    roles = {
        "material_analysis_payloads": [
            {
                "source_ref": "raw/fontish.json" if kind == "bundle" else "trace/fontish.json",
                "artifact_role": "material_analysis_payload",
                "category": "candidate_b_raw_json" if kind == "bundle" else "candidate_b_runtime_trace_manifest",
                "extension": ".json",
                "sha256": "1" * 64,
                "size_bytes": 12,
                "material_text_payload": True,
            }
        ],
        "visual_page_evidence": [
            {
                "source_ref": visual_ref,
                "artifact_role": "source_pdf",
                "extension": ".pdf",
                "sha256": "2" * 64,
                "size_bytes": 12,
                "material_text_payload": False,
            },
            {
                "source_ref": image_ref,
                "artifact_role": "extracted_image",
                "extension": ".png",
                "sha256": "3" * 64,
                "size_bytes": 7,
                "material_text_payload": False,
            },
        ],
        "provenance_audit_artifacts": [
            {
                "source_ref": "proof.json" if kind == "bundle" else "runtime-summary.json",
                "artifact_role": "provenance_audit",
                "extension": ".json",
                "sha256": "4" * 64,
                "size_bytes": 20,
                "material_text_payload": False,
            }
        ],
        "product_inspection_artifacts": [
            {
                "source_ref": visual_ref,
                "artifact_role": "source_pdf",
                "extension": ".pdf",
                "sha256": "2" * 64,
                "size_bytes": 12,
                "material_text_payload": False,
            }
        ],
        "delivery_artifacts": [
            {
                "source_ref": image_ref,
                "artifact_role": "extracted_image",
                "extension": ".png",
                "sha256": "3" * 64,
                "size_bytes": 7,
                "material_text_payload": False,
            }
        ],
    }
    payload = {
        "policy": "candidate_b_full_artifact_family_retained_but_text_material_payload_bounded",
        "candidate_b_source_kind": kind,
        "material_text_payload_policy": "raw_json_md_and_required_reports_only"
        if kind == "bundle"
        else "document_trace_json_md_only",
        "pdf_material_text_payload_enabled": False,
        "image_material_text_payload_enabled": False,
        "raw_url_exposure_enabled": False,
        "roles": roles,
        "role_counts": {role: len(items) for role, items in roles.items()},
    }
    hash_version = (
        layer3_candidate_b_bundle_bridge.AUTHORITY_HASH_VERSION
        if kind == "bundle"
        else layer3_candidate_b_runtime_bridge.AUTHORITY_HASH_VERSION
    )
    return {
        **payload,
        "artifact_family_hash": _stable_hash({"hash_version": hash_version, "classification": payload}),
    }


def _write_receipt(kind: str, *, family_override: dict[str, Any] | None = None) -> str:
    artifact_family = family_override or _artifact_family(kind)
    if kind == "bundle":
        receipt_input = {
            "schema_id": layer3_candidate_b_bundle_bridge.SCHEMA_ID,
            "schema_version": layer3_candidate_b_bundle_bridge.SCHEMA_VERSION,
            "bridge_mode": layer3_candidate_b_bundle_bridge.BRIDGE_MODE,
            "candidate_b_bundle_id": "tests/reports/cb-compare-demo",
            "baseline_run_id": "baseline-run",
            "candidate_a_run_id": "candidate-a-run",
            "candidate_b_source_kind": kind,
            "compare_target_set_hash": "1" * 64,
            "bundle_file_manifest_hash": "2" * 64,
            "bundle_raw_file_manifest_hash": "3" * 64,
            "admitted_file_subset_source_hash": "4" * 64,
            "admitted_file_subset_hash": "5" * 64,
            "governed_retained_artifact_family_hash": artifact_family["artifact_family_hash"],
            "redaction_policy_id": layer3_candidate_b_bundle_bridge.REDACTION_POLICY_ID,
        }
        prefix = layer3_candidate_b_bundle_bridge.BRIDGE_RECEIPT_PREFIX
    else:
        receipt_input = {
            "schema_id": layer3_candidate_b_runtime_bridge.SCHEMA_ID,
            "schema_version": layer3_candidate_b_runtime_bridge.SCHEMA_VERSION,
            "bridge_mode": layer3_candidate_b_runtime_bridge.BRIDGE_MODE,
            "candidate_b_run_id": "candidate-b-runtime-run",
            "baseline_run_id": "baseline-run",
            "candidate_a_run_id": "candidate-a-run",
            "candidate_b_source_kind": kind,
            "document_processing_engine": "candidate_b_opendataloader_pdf",
            "visual_lane_mode": layer3_candidate_b_runtime_bridge.CANDIDATE_B_VISUAL_LANE_MODE,
            "compare_target_set_hash": "6" * 64,
            "runtime_review_root_storage_authority_hash": "7" * 64,
            "admitted_file_subset_hash": "8" * 64,
            "governed_retained_artifact_family_hash": artifact_family["artifact_family_hash"],
            "candidate_b_visual_lane_evidence": {
                "visual_lane_mode": layer3_candidate_b_runtime_bridge.CANDIDATE_B_VISUAL_LANE_MODE,
                "visual_ref_total": 2,
                "candidate_b_visual_ref_total": 2,
                "candidate_b_retained_source_pdf_ref_count": 1,
                "source_pdf_material_text_payload_enabled": False,
                "image_material_text_payload_enabled": False,
            },
            "redaction_policy_id": layer3_candidate_b_runtime_bridge.REDACTION_POLICY_ID,
        }
        prefix = layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX
    receipt_hash = _stable_hash(receipt_input)
    receipt_id = f"{prefix}-{receipt_hash[:24]}"
    root = (
        Path(settings.layer3_candidate_b_bundle_bridge_dir)
        if kind == "bundle"
        else Path(settings.layer3_candidate_b_runtime_bridge_dir)
    )
    receipt = {
        **receipt_input,
        "bridge_receipt_id": receipt_id,
        "bridge_receipt_hash": receipt_hash,
        "governed_retained_artifact_family": artifact_family,
    }
    _write_json(root / receipt_id / "receipt.json", receipt)
    return receipt_id


def _payload(kind: str, receipt_id: str) -> dict[str, Any]:
    return {
        "client_request_id": f"candidate-b-{kind}-artifact-status",
        "status_mode": "candidate_b_retained_artifact_family_status_v1",
        "operator_decision": "inspect_candidate_b_governed_retained_artifact_family_status",
        "candidate_b_source_kind": kind,
        "bridge_receipt_id": receipt_id,
    }


def test_candidate_b_bundle_artifact_family_status_projects_retained_roles(client: TestClient, tmp_path: Path) -> None:
    receipt_id = _write_receipt("bundle")

    response = client.post(STATUS_ENDPOINT, json=_payload("bundle", receipt_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "available"
    assert body["candidate_b_source_kind"] == "bundle"
    assert body["bridge_receipt_id"] == receipt_id
    assert body["artifact_family_status"] == "available"
    assert body["governed_retained_artifact_family"]["role_counts"]["visual_page_evidence"] == 2
    assert body["negative_invariants"]["pdf_material_text_payload_enabled"] is False
    assert body["negative_invariants"]["image_material_text_payload_enabled"] is False
    assert body["negative_invariants"]["candidate_b_default_promotion_enabled"] is False
    visual_refs = body["operator_projection"]["role_previews"]["visual_page_evidence"]
    assert any(item["display_ref"] == "fontish.pdf" for item in visual_refs)
    assert any(item["display_ref"] == "imageFile1.png" for item in visual_refs)
    assert "raw/annotated/fontish.pdf" not in json.dumps(body["operator_projection"], sort_keys=True)
    assert "raw/images/fontish/imageFile1.png" not in json.dumps(body["operator_projection"], sort_keys=True)
    assert body["operator_projection"]["artifact_bytes_exposed"] is False
    assert str(tmp_path) not in json.dumps(body, sort_keys=True)
    assert "C:\\" not in json.dumps(body, sort_keys=True)


def test_candidate_b_artifact_family_status_allows_benign_double_dot_display_names(
    client: TestClient,
) -> None:
    family = _artifact_family("bundle")
    family["roles"]["visual_page_evidence"][0]["source_ref"] = "raw/annotated/figure..v1.pdf"
    classification = dict(family)
    classification.pop("artifact_family_hash", None)
    family["artifact_family_hash"] = _stable_hash(
        {
            "hash_version": layer3_candidate_b_bundle_bridge.AUTHORITY_HASH_VERSION,
            "classification": classification,
        }
    )
    receipt_id = _write_receipt("bundle", family_override=family)

    response = client.post(STATUS_ENDPOINT, json=_payload("bundle", receipt_id))

    assert response.status_code == 200, response.text
    previews = response.json()["operator_projection"]["role_previews"]["visual_page_evidence"]
    assert any(item["display_ref"] == "figure..v1.pdf" for item in previews)


def test_candidate_b_runtime_artifact_family_status_projects_retained_roles(client: TestClient, tmp_path: Path) -> None:
    receipt_id = _write_receipt("runtime")

    response = client.post(STATUS_ENDPOINT, json=_payload("runtime", receipt_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "available"
    assert body["candidate_b_source_kind"] == "runtime"
    assert body["governed_retained_artifact_family"]["role_counts"]["visual_page_evidence"] == 2
    visual_refs = body["operator_projection"]["role_previews"]["visual_page_evidence"]
    assert any(item["display_ref"] == "input.pdf" for item in visual_refs)
    assert any(item["display_ref"] == "image.png" for item in visual_refs)
    assert "storage/input.pdf" not in json.dumps(body["operator_projection"], sort_keys=True)
    assert "storage/image.png" not in json.dumps(body["operator_projection"], sort_keys=True)
    assert body["negative_invariants"]["pdf_material_text_payload_enabled"] is False
    assert body["negative_invariants"]["image_material_text_payload_enabled"] is False
    assert str(tmp_path) not in json.dumps(body, sort_keys=True)
    assert "C:\\" not in json.dumps(body, sort_keys=True)


def test_candidate_b_runtime_artifact_family_status_fails_closed_on_stale_hash(client: TestClient) -> None:
    family = _artifact_family("runtime")
    receipt_id = _write_receipt("runtime", family_override={**family, "artifact_family_hash": "b" * 64})
    receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["governed_retained_artifact_family_hash"] = "c" * 64
    receipt["bridge_receipt_hash"] = _stable_hash(
        {key: receipt[key] for key in layer3_candidate_b_artifact_status._RUNTIME_HASH_KEYS}
    )
    _write_json(receipt_path, receipt)

    response = client.post(STATUS_ENDPOINT, json=_payload("runtime", receipt_id))

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "candidate_b_artifact_status_governed_artifact_family_hash_mismatch"


@pytest.mark.parametrize("kind", ["bundle", "runtime"])
def test_candidate_b_artifact_family_status_fails_closed_on_stale_bridge_receipt_hash(
    client: TestClient, kind: str
) -> None:
    receipt_id = _write_receipt(kind)
    root = (
        Path(settings.layer3_candidate_b_bundle_bridge_dir)
        if kind == "bundle"
        else Path(settings.layer3_candidate_b_runtime_bridge_dir)
    )
    receipt_path = root / receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["candidate_a_run_id"] = "tampered-candidate-a-run"
    _write_json(receipt_path, receipt)

    response = client.post(STATUS_ENDPOINT, json=_payload(kind, receipt_id))

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "candidate_b_artifact_status_bridge_receipt_hash_mismatch"


def test_candidate_b_runtime_artifact_family_status_binds_visual_lane_evidence_hash(
    client: TestClient,
) -> None:
    receipt_id = _write_receipt("runtime")
    receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["candidate_b_visual_lane_evidence"]["candidate_b_visual_ref_total"] = 99
    _write_json(receipt_path, receipt)

    response = client.post(STATUS_ENDPOINT, json=_payload("runtime", receipt_id))

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "candidate_b_artifact_status_bridge_receipt_hash_mismatch"


@pytest.mark.parametrize("kind", ["bundle", "runtime"])
def test_candidate_b_artifact_family_status_fails_closed_on_stale_roles(
    client: TestClient, kind: str
) -> None:
    receipt_id = _write_receipt(kind)
    root = (
        Path(settings.layer3_candidate_b_bundle_bridge_dir)
        if kind == "bundle"
        else Path(settings.layer3_candidate_b_runtime_bridge_dir)
    )
    receipt_path = root / receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["governed_retained_artifact_family"]["roles"]["visual_page_evidence"].append(
        {
            "source_ref": "storage/extra.png",
            "artifact_role": "extracted_image",
            "extension": ".png",
            "sha256": "5" * 64,
            "size_bytes": 9,
            "material_text_payload": False,
        }
    )
    _write_json(receipt_path, receipt)

    response = client.post(STATUS_ENDPOINT, json=_payload(kind, receipt_id))

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "candidate_b_artifact_status_governed_artifact_family_stale"


@pytest.mark.parametrize(
    ("kind", "missing_role"),
    [
        ("bundle", "delivery_artifacts"),
        ("runtime", "product_inspection_artifacts"),
    ],
)
def test_candidate_b_artifact_family_status_rejects_missing_required_role_group(
    client: TestClient,
    kind: str,
    missing_role: str,
) -> None:
    family = _artifact_family(kind)
    family["roles"].pop(missing_role)
    family["role_counts"].pop(missing_role)
    hash_version = (
        layer3_candidate_b_bundle_bridge.AUTHORITY_HASH_VERSION
        if kind == "bundle"
        else layer3_candidate_b_runtime_bridge.AUTHORITY_HASH_VERSION
    )
    family_input = dict(family)
    family_input.pop("artifact_family_hash", None)
    family["artifact_family_hash"] = _stable_hash({"hash_version": hash_version, "classification": family_input})
    receipt_id = _write_receipt(kind, family_override=family)

    response = client.post(STATUS_ENDPOINT, json=_payload(kind, receipt_id))

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["error"]["code"] == "candidate_b_artifact_status_governed_artifact_roles_incomplete"
    assert body["error"]["details"]["missing_roles"] == [missing_role]


@pytest.mark.parametrize(
    ("kind", "receipt_id"),
    [
        ("bundle", "../cb-bundle-l3-proof"),
        ("runtime", "cb-bundle-l3-wrong-prefix"),
    ],
)
def test_candidate_b_artifact_family_status_rejects_path_like_or_wrong_prefix_receipt_id(
    client: TestClient, kind: str, receipt_id: str
) -> None:
    response = client.post(STATUS_ENDPOINT, json=_payload(kind, receipt_id))

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "candidate_b_artifact_status_bridge_receipt_id_invalid"


def test_candidate_b_artifact_family_status_rejects_path_and_url_fields(client: TestClient) -> None:
    receipt_id = _write_receipt("bundle")
    response = client.post(
        STATUS_ENDPOINT,
        json={**_payload("bundle", receipt_id), "local_path": "C:/private/source", "url": "https://example.test"},
    )

    assert response.status_code == 422
    schema = client.app.openapi()
    route = schema["paths"][STATUS_ENDPOINT]["post"]
    request_ref = route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]
    assert request_schema["additionalProperties"] is False
    assert "local_path" not in request_schema["properties"]
    assert "url" not in request_schema["properties"]
