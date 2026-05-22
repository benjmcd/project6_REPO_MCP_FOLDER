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
    layer3_candidate_b_bundle_bridge,
    layer3_candidate_b_runtime_bridge,
)
from main import app


BASELINE_RUN_ID = "baseline-run"
CANDIDATE_A_RUN_ID = "candidate-a-run"
CANDIDATE_B_BUNDLE_ID = "tests/reports/cb-compare-demo"
CANDIDATE_B_RUN_ID = "candidate-b-runtime-run"
READY_SCOPE = "candidate_b_opendataloader_pdf_eligible_pdf_corpus_processing_only"
READY_REGRESSION = "no_unacceptable_regression_against_baseline_and_candidate_a"
READY_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/default-promotion/readiness-audit"
FULL_COVERAGE = [
    "source_directory_scan",
    "material_preview",
    "gate_b",
    "hybrid_qualitative_analysis",
    "package_commit",
    "package_review_submit",
    "handoff_export_prepare",
    "external_export_download_prepare",
    "same_origin_delivery_status",
    "same_origin_delivery",
    "provider_private_prepare",
    "provider_private_status",
    "provider_private_use",
    "provider_private_revoke",
    "internal_webhook_dispatch",
    "internal_webhook_status",
    "session_status_projection",
]


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


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_visual_lane_mode_enabled": False,
        "candidate_b_visual_lane_material_ingestion_enabled": False,
        "candidate_b_default_promotion_enabled": False,
        "pdf_ingestion_enabled": False,
        "image_ingestion_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "browser_storage_authority_enabled": False,
        "frontend_durable_authority_enabled": False,
        "full_mockup_activation_enabled": False,
    }


def _compare_target_set(kind: str) -> dict[str, Any]:
    payload = {
        "candidate_b_source_kind": kind,
        "baseline_run_id": BASELINE_RUN_ID,
        "candidate_a_run_id": CANDIDATE_A_RUN_ID,
        "candidate_b_bundle_id": CANDIDATE_B_BUNDLE_ID if kind == "bundle" else None,
        "candidate_b_run_id": CANDIDATE_B_RUN_ID if kind == "runtime" else None,
        "fixture_ids": ["fontish"],
        "target_count": 1,
        "targets": [
            {
                "fixture_id": "fontish",
                "baseline_target_id": "baseline-target",
                "candidate_a_target_id": "candidate-a-target",
                "candidate_b_target_id": "candidate-b-target",
                "comparability_state": "aligned",
            }
        ],
    }
    return {**payload, "compare_target_set_hash": _stable_hash(payload["targets"])}


def _artifact_family(kind: str) -> dict[str, Any]:
    roles = {
        "material_analysis_payloads": [
            {
                "source_ref": "raw/fontish.json" if kind == "bundle" else "trace/fontish.json",
                "artifact_role": "material_analysis_payload",
                "category": "candidate_b_raw_json" if kind == "bundle" else "candidate_b_runtime_trace_manifest",
                "extension": ".json",
                "sha256": "c" * 64,
                "size_bytes": 12,
                "material_text_payload": True,
            }
        ],
        "visual_page_evidence": [
            {
                "source_ref": "raw/annotated/fontish.pdf" if kind == "bundle" else "storage/input.pdf",
                "artifact_role": "source_pdf",
                "extension": ".pdf",
                "sha256": "d" * 64,
                "size_bytes": 12,
                "material_text_payload": False,
            }
        ],
        "provenance_audit_artifacts": [
            {
                "source_ref": "proof.json" if kind == "bundle" else "runtime-summary.json",
                "artifact_role": "provenance_audit",
                "extension": ".json",
                "sha256": "e" * 64,
                "size_bytes": 12,
                "material_text_payload": kind == "runtime",
            }
        ],
        "product_inspection_artifacts": [],
        "delivery_artifacts": [],
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
    return {**payload, "artifact_family_hash": _stable_hash(payload)}


def _write_bundle_receipt() -> str:
    artifact_family = _artifact_family("bundle")
    receipt_input = {
        "schema_id": layer3_candidate_b_bundle_bridge.SCHEMA_ID,
        "schema_version": layer3_candidate_b_bundle_bridge.SCHEMA_VERSION,
        "bridge_mode": layer3_candidate_b_bundle_bridge.BRIDGE_MODE,
        "candidate_b_bundle_id": CANDIDATE_B_BUNDLE_ID,
        "baseline_run_id": BASELINE_RUN_ID,
        "candidate_a_run_id": CANDIDATE_A_RUN_ID,
        "candidate_b_source_kind": "bundle",
        "compare_target_set_hash": "1" * 64,
        "bundle_file_manifest_hash": "2" * 64,
        "bundle_raw_file_manifest_hash": "3" * 64,
        "admitted_file_subset_source_hash": "4" * 64,
        "admitted_file_subset_hash": "5" * 64,
        "governed_retained_artifact_family_hash": artifact_family["artifact_family_hash"],
        "redaction_policy_id": layer3_candidate_b_bundle_bridge.REDACTION_POLICY_ID,
    }
    receipt_hash = _stable_hash(receipt_input)
    receipt_id = f"{layer3_candidate_b_bundle_bridge.BRIDGE_RECEIPT_PREFIX}-{receipt_hash[:24]}"
    _write_json(
        Path(settings.layer3_candidate_b_bundle_bridge_dir) / receipt_id / "receipt.json",
        {
            **receipt_input,
            "bridge_receipt_id": receipt_id,
            "bridge_receipt_hash": receipt_hash,
            "candidate_b_bundle_validation": {"status": "passed"},
            "compare_target_set": {**_compare_target_set("bundle"), "compare_target_set_hash": "1" * 64},
            "layer3_compatibility": {
                "material_preview_uses_existing_hash_checks": True,
                "gate_b_uses_existing_decision_basis_validation": True,
            },
            "governed_retained_artifact_family": artifact_family,
            "negative_invariants": _negative_invariants(),
        },
    )
    return receipt_id


def _write_runtime_receipt() -> str:
    artifact_family = _artifact_family("runtime")
    receipt_input = {
        "schema_id": layer3_candidate_b_runtime_bridge.SCHEMA_ID,
        "schema_version": layer3_candidate_b_runtime_bridge.SCHEMA_VERSION,
        "bridge_mode": layer3_candidate_b_runtime_bridge.BRIDGE_MODE,
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "baseline_run_id": BASELINE_RUN_ID,
        "candidate_a_run_id": CANDIDATE_A_RUN_ID,
        "candidate_b_source_kind": "runtime",
        "document_processing_engine": "candidate_b_opendataloader_pdf",
        "compare_target_set_hash": "6" * 64,
        "runtime_review_root_storage_authority_hash": "7" * 64,
        "admitted_file_subset_hash": "8" * 64,
        "governed_retained_artifact_family_hash": artifact_family["artifact_family_hash"],
        "redaction_policy_id": layer3_candidate_b_runtime_bridge.REDACTION_POLICY_ID,
    }
    receipt_hash = _stable_hash(receipt_input)
    receipt_id = f"{layer3_candidate_b_runtime_bridge.BRIDGE_RECEIPT_PREFIX}-{receipt_hash[:24]}"
    _write_json(
        Path(settings.layer3_candidate_b_runtime_bridge_dir) / receipt_id / "receipt.json",
        {
            **receipt_input,
            "bridge_receipt_id": receipt_id,
            "bridge_receipt_hash": receipt_hash,
            "candidate_b_runtime_validation": {"status": "passed"},
            "compare_target_set": {**_compare_target_set("runtime"), "compare_target_set_hash": "6" * 64},
            "layer3_compatibility": {
                "material_preview_uses_existing_hash_checks": True,
                "gate_b_uses_existing_decision_basis_validation": True,
            },
            "governed_retained_artifact_family": artifact_family,
            "negative_invariants": _negative_invariants(),
        },
    )
    return receipt_id


def _proof(kind: str, receipt_id: str, *, coverage: list[str] | None = None) -> dict[str, Any]:
    return {
        "candidate_b_source_kind": kind,
        "bridge_receipt_id": receipt_id,
        "proof_state": "candidate_b_layer3_downstream_e2e_proven",
        "coverage": list(FULL_COVERAGE if coverage is None else coverage),
        "proof_hash": ("a" if kind == "bundle" else "b") * 64,
        "raw_local_path_exposed": False,
        "provider_private_token_exposed": False,
        "provider_public_url_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "candidate_b_default_promotion_enabled": False,
        "visual_lane_mode_enabled": False,
    }


def _payload(bundle_receipt_id: str, runtime_receipt_id: str) -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-default-readiness-001",
        "readiness_mode": "candidate_b_default_promotion_readiness_audit_v1",
        "baseline_run_id": BASELINE_RUN_ID,
        "candidate_a_run_id": CANDIDATE_A_RUN_ID,
        "candidate_b_bundle_id": CANDIDATE_B_BUNDLE_ID,
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "candidate_b_bundle_bridge_receipt_id": bundle_receipt_id,
        "candidate_b_runtime_bridge_receipt_id": runtime_receipt_id,
        "eligible_corpus_scope": READY_SCOPE,
        "regression_disposition": READY_REGRESSION,
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
        "bundle_downstream_proof": _proof("bundle", bundle_receipt_id),
        "runtime_downstream_proof": _proof("runtime", runtime_receipt_id),
        "operator_status_evidence": {
            "operator_visible_provenance_status": True,
            "bundle_status_projection_visible": True,
            "runtime_status_projection_visible": True,
            "default_selector_change_visible_as_enabled": True,
            "raw_local_path_exposed": False,
            "provider_private_token_exposed": False,
        },
    }


def test_candidate_b_default_readiness_ready_path_is_read_only_and_non_promoting(client: TestClient, tmp_path: Path) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()

    response = client.post(READY_ENDPOINT, json=_payload(bundle_receipt_id, runtime_receipt_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready"
    assert body["readiness_state"] == "candidate_b_default_promotion_ready_for_separate_selection"
    assert body["blocked_reasons"] == []
    assert body["candidate_b_selector_evidence"]["candidate_b_is_visual_lane_mode"] is False
    assert body["candidate_b_selector_evidence"]["candidate_b_default_for_eligible_pdf_when_engine_omitted"] is True
    assert body["candidate_b_selector_evidence"]["candidate_b_runtime_selector_is_opt_in"] is True
    assert body["baseline_current_default_evidence"]["baseline_default_changed"] is False
    assert body["baseline_current_default_evidence"]["non_pdf_document_processing_engine_default"] == "baseline"
    assert body["baseline_current_default_evidence"]["explicit_baseline_rollback_preserved"] is True
    assert body["candidate_a_admitted_variant_evidence"]["visual_lane_mode"] == "candidate_a_page_evidence_v1"
    assert body["bridge_receipts"]["bundle"]["governed_retained_artifact_family_hash"]
    assert body["bridge_receipts"]["runtime"]["governed_retained_artifact_family_hash"]
    assert body["authority_hashes"]["bundle"]["governed_retained_artifact_family_hash"]
    assert body["authority_hashes"]["runtime"]["governed_retained_artifact_family_hash"]
    assert body["default_selector_change_enabled"] is True
    assert body["candidate_b_default_promotion_enabled"] is True
    assert body["selector_mutation_performed"] is False
    assert body["rollback_to_baseline"]["depends_on_candidate_b_artifacts"] is False
    assert body["next_allowed_actions"] == [
        "monitor_candidate_b_default_selector",
        "use_explicit_baseline_document_processing_engine_for_rollback",
    ]
    assert str(tmp_path) not in json.dumps(body, sort_keys=True)


def test_candidate_b_default_readiness_blocks_missing_runtime_receipt(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    payload = _payload(bundle_receipt_id, "cb-runtime-l3-missing")
    payload["runtime_downstream_proof"] = _proof("runtime", "cb-runtime-l3-missing")

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["readiness_state"] == "candidate_b_default_promotion_readiness_blocked"
    assert body["candidate_b_default_promotion_enabled"] is False
    assert body["default_selector_change_enabled"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_runtime_bridge_receipt_missing" in codes


def test_candidate_b_default_readiness_blocks_missing_artifact_family(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    runtime_receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / runtime_receipt_id / "receipt.json"
    runtime_receipt = json.loads(runtime_receipt_path.read_text(encoding="utf-8"))
    runtime_receipt.pop("governed_retained_artifact_family")
    _write_json(runtime_receipt_path, runtime_receipt)

    response = client.post(READY_ENDPOINT, json=_payload(bundle_receipt_id, runtime_receipt_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_runtime_governed_artifact_family_missing" in codes
    assert body["candidate_b_default_promotion_enabled"] is False


def test_candidate_b_default_readiness_blocks_incomplete_downstream_and_regression(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload["regression_disposition"] = "unacceptable_regression_found"
    payload["bundle_downstream_proof"] = _proof("bundle", bundle_receipt_id, coverage=["source_directory_scan"])

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_regression_disposition_not_ready" in codes
    assert "candidate_b_default_readiness_bundle_downstream_coverage_incomplete" in codes
    assert body["selector_mutation_performed"] is False


def test_candidate_b_default_readiness_rejects_forbidden_selector_and_path_fields(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = {
        **_payload(bundle_receipt_id, runtime_receipt_id),
        "local_path": "C:/private/source",
        "default_selector": "candidate_b_opendataloader_pdf",
    }

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 422
    schema = client.app.openapi()
    route = schema["paths"][READY_ENDPOINT]["post"]
    request_ref = route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]
    assert request_schema["additionalProperties"] is False
    for field in ("visual_lane_mode", "document_processing_engine", "local_path", "url", "default_selector"):
        assert field not in request_schema["properties"]

    readiness = client.get("/api/v1/layer3/readiness")
    assert readiness.status_code == 200
    readiness_body = readiness.json()
    assert readiness_body["candidate_b_default_promotion_readiness_audit_admitted"] is True
    assert readiness_body["candidate_b_default_promotion_readiness_audit_endpoint"] == READY_ENDPOINT
    assert readiness_body["candidate_b_default_promotion_selector_switch_admitted"] is True
    assert (
        readiness_body["candidate_b_default_promotion_selector_scope"]
        == "candidate_b_opendataloader_pdf_eligible_pdf_corpus_processing_only"
    )
