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
VISUAL_STATUS_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/visual-lane/status"
BUNDLE_PROOF_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/bundle/downstream-proof"
DOWNSTREAM_PROOF_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/runtime/downstream-proof"
OPERATOR_STATUS_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/default-promotion/operator-status"
CANDIDATE_B_VISUAL_LANE_MODE = "candidate_b_opendataloader_page_evidence_v1"
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


def _negative_invariants(*, candidate_b_visual_lane_mode_enabled: bool = False) -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_visual_lane_mode_enabled": candidate_b_visual_lane_mode_enabled,
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


def _write_runtime_receipt(*, visual_lane_mode: str = CANDIDATE_B_VISUAL_LANE_MODE) -> str:
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
        "visual_lane_mode": visual_lane_mode,
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
            "candidate_b_visual_lane_evidence": {
                "visual_lane_mode": visual_lane_mode,
                "candidate_b_visual_lane_selected": visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE,
                "candidate_b_visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
                "visual_ref_total": 1 if visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE else 0,
                "candidate_b_visual_ref_total": 1 if visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE else 0,
                "candidate_b_retained_source_pdf_ref_count": (
                    1 if visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE else 0
                ),
                "source_pdf_material_text_payload_enabled": False,
                "image_material_text_payload_enabled": False,
                "evidence_source": "runtime_summary_advanced_metrics",
            },
            "negative_invariants": _negative_invariants(
                candidate_b_visual_lane_mode_enabled=visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE
            ),
        },
    )
    return receipt_id


def _proof(kind: str, receipt_id: str, *, coverage: list[str] | None = None) -> dict[str, Any]:
    if kind == "runtime":
        return _runtime_downstream_proof(receipt_id, coverage=coverage)
    visual_lane_enabled = kind == "runtime"
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
        "visual_lane_mode_enabled": visual_lane_enabled,
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE if visual_lane_enabled else "baseline",
    }


def _coverage_evidence(coverage: list[str] | None = None) -> dict[str, Any]:
    steps = FULL_COVERAGE if coverage is None else coverage
    return {
        step: {
            "status": "proven",
            "evidence_ref": f"candidate-b-downstream-proof://{step}",
            "evidence_hash": _stable_hash({"step": step, "status": "proven"}),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_private_token_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
        }
        for step in steps
    }


def _downstream_negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "source_expansion_enabled": False,
        "candidate_b_default_promotion_enabled": False,
        "candidate_b_visual_lane_material_ingestion_enabled": False,
        "source_pdf_material_text_payload_enabled": False,
        "image_material_text_payload_enabled": False,
        "raw_local_path_exposed": False,
        "raw_url_exposure_enabled": False,
        "provider_private_token_exposed": False,
        "provider_public_url_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "browser_storage_authority_enabled": False,
        "frontend_durable_authority_enabled": False,
        "full_mockup_activation_enabled": False,
    }


def _runtime_downstream_proof(
    runtime_receipt_id: str,
    *,
    coverage: list[str] | None = None,
    visual_lane_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / runtime_receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    coverage_evidence = _coverage_evidence(coverage)
    negative_invariants = _downstream_negative_invariants()
    status_evidence = visual_lane_status or _visual_lane_status_evidence(runtime_receipt_id)
    proof_input = {
        "schema_id": "layer3.candidate_b_runtime_downstream_proof.v1",
        "schema_version": 1,
        "mode": "candidate_b_visual_lane_runtime_downstream_e2e_proof_v1",
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "bridge_receipt_id": runtime_receipt_id,
        "bridge_receipt_hash": receipt["bridge_receipt_hash"],
        "document_processing_engine": "candidate_b_opendataloader_pdf",
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
        "candidate_b_visual_lane_status_hash": _stable_hash(status_evidence),
        "coverage_evidence_hash": _stable_hash(coverage_evidence),
        "negative_invariants_hash": _stable_hash(negative_invariants),
        "operator_confirmation": True,
    }
    proof_hash = _stable_hash(proof_input)
    return {
        **proof_input,
        "request_id": "candidate-b-downstream-proof",
        "server_time": "2026-05-22T00:00:00Z",
        "status": "proven",
        "proof_state": "candidate_b_layer3_downstream_e2e_proven",
        "proof_hash": proof_hash,
        "proof_receipt_id": f"cb-runtime-downstream-proof-{proof_hash[:24]}",
        "proof_receipt_ref": (
            f"candidate-b-runtime-downstream-proof://{runtime_receipt_id}/"
            f"cb-runtime-downstream-proof-{proof_hash[:24]}.json"
        ),
        "coverage": list(FULL_COVERAGE if coverage is None else coverage),
        "coverage_evidence": coverage_evidence,
        "raw_local_path_exposed": False,
        "provider_private_token_exposed": False,
        "provider_public_url_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "candidate_b_default_promotion_enabled": False,
        "visual_lane_mode_enabled": True,
        "negative_invariants": negative_invariants,
        "next_allowed_actions": [
            "use this proof as Candidate B runtime downstream proof evidence",
            "run Candidate B default-promotion readiness audit with the matching runtime bridge receipt",
        ],
    }


def _visual_lane_status_evidence(runtime_receipt_id: str) -> dict[str, Any]:
    receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / runtime_receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    visual_evidence = dict(receipt["candidate_b_visual_lane_evidence"])
    return {
        "schema_id": "layer3.candidate_b_visual_lane_status.v1",
        "schema_version": 1,
        "request_id": "candidate-b-visual-lane-status",
        "server_time": "2026-05-22T00:00:00Z",
        "status": "available",
        "mode": "candidate_b_visual_lane_status_v1",
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "bridge_receipt_id": runtime_receipt_id,
        "bridge_receipt_ref": f"candidate-b-runtime-bridge://{runtime_receipt_id}/receipt.json",
        "bridge_receipt_hash": receipt["bridge_receipt_hash"],
        "document_processing_engine": "candidate_b_opendataloader_pdf",
        "visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
        "visual_lane_status": "available",
        "candidate_b_visual_lane_evidence": visual_evidence,
        "operator_projection": {
            "candidate_b_visual_lane_status_projection_visible": True,
            "candidate_b_visual_lane_selected": True,
            "visual_ref_total": int(visual_evidence.get("visual_ref_total") or 0),
            "candidate_b_visual_ref_total": int(visual_evidence.get("candidate_b_visual_ref_total") or 0),
            "candidate_b_retained_source_pdf_ref_count": int(
                visual_evidence.get("candidate_b_retained_source_pdf_ref_count") or 0
            ),
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "material_policy": {
            "source_pdf_material_text_payload_enabled": False,
            "image_material_text_payload_enabled": False,
            "visual_lane_material_ingestion_enabled": False,
        },
        "negative_invariants": {
            "baseline_default_changed": False,
            "candidate_a_semantics_changed": False,
            "candidate_b_default_promotion_enabled": False,
            "candidate_b_visual_lane_material_ingestion_enabled": False,
            "source_pdf_material_text_payload_enabled": False,
            "image_material_text_payload_enabled": False,
            "raw_url_exposure_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "browser_storage_authority_enabled": False,
            "frontend_durable_authority_enabled": False,
        },
        "next_allowed_actions": [
            "use this status as Candidate B visual-lane operator projection evidence",
            "run Candidate B default-promotion readiness audit after downstream proof is current",
        ],
    }


def _visual_lane_status_request(runtime_receipt_id: str) -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-visual-lane-status",
        "status_mode": "candidate_b_visual_lane_status_v1",
        "operator_decision": "inspect_candidate_b_visual_lane_evidence_status",
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "bridge_receipt_id": runtime_receipt_id,
    }


def _downstream_proof_request(runtime_receipt_id: str, visual_lane_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-downstream-proof",
        "proof_mode": "candidate_b_visual_lane_runtime_downstream_e2e_proof_v1",
        "operator_decision": "record_candidate_b_visual_lane_runtime_downstream_e2e_proof",
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "bridge_receipt_id": runtime_receipt_id,
        "candidate_b_visual_lane_status_evidence": visual_lane_status,
        "coverage_evidence": _coverage_evidence(),
        "operator_confirmation": True,
    }


def _bundle_downstream_proof_request(bundle_receipt_id: str, *, coverage: list[str] | None = None) -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-bundle-downstream-proof",
        "proof_mode": "candidate_b_bundle_downstream_e2e_proof_v1",
        "operator_decision": "record_candidate_b_bundle_downstream_e2e_proof",
        "candidate_b_bundle_id": CANDIDATE_B_BUNDLE_ID,
        "bridge_receipt_id": bundle_receipt_id,
        "coverage_evidence": _coverage_evidence(coverage),
        "operator_confirmation": True,
    }


def _operator_status_request(
    bundle_receipt_id: str,
    runtime_receipt_id: str,
    visual_lane_status: dict[str, Any],
    runtime_downstream_proof: dict[str, Any],
) -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-operator-status",
        "status_mode": "candidate_b_default_promotion_operator_status_v1",
        "operator_decision": "inspect_candidate_b_default_promotion_operator_status",
        "baseline_run_id": BASELINE_RUN_ID,
        "candidate_a_run_id": CANDIDATE_A_RUN_ID,
        "candidate_b_bundle_id": CANDIDATE_B_BUNDLE_ID,
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "candidate_b_bundle_bridge_receipt_id": bundle_receipt_id,
        "candidate_b_runtime_bridge_receipt_id": runtime_receipt_id,
        "candidate_b_visual_lane_status_evidence": visual_lane_status,
        "runtime_downstream_proof": runtime_downstream_proof,
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
        "candidate_b_visual_lane_status_evidence": _visual_lane_status_evidence(runtime_receipt_id),
        "operator_status_evidence": {
            "operator_visible_provenance_status": True,
            "bundle_status_projection_visible": True,
            "runtime_status_projection_visible": True,
            "default_selector_change_visible_as_enabled": True,
            "raw_local_path_exposed": False,
            "provider_private_token_exposed": False,
        },
    }


def _payload_with_live_runtime_proof(
    client: TestClient,
    bundle_receipt_id: str,
    runtime_receipt_id: str,
    *,
    visual_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle_proof_response = client.post(
        BUNDLE_PROOF_ENDPOINT,
        json=_bundle_downstream_proof_request(bundle_receipt_id),
    )
    assert bundle_proof_response.status_code == 200, bundle_proof_response.text
    status = visual_status
    if status is None:
        visual_status_response = client.post(
            VISUAL_STATUS_ENDPOINT,
            json=_visual_lane_status_request(runtime_receipt_id),
        )
        assert visual_status_response.status_code == 200, visual_status_response.text
        status = visual_status_response.json()
    proof_response = client.post(
        DOWNSTREAM_PROOF_ENDPOINT,
        json=_downstream_proof_request(runtime_receipt_id, status),
    )
    assert proof_response.status_code == 200, proof_response.text
    operator_status_response = client.post(
        OPERATOR_STATUS_ENDPOINT,
        json=_operator_status_request(bundle_receipt_id, runtime_receipt_id, status, proof_response.json()),
    )
    assert operator_status_response.status_code == 200, operator_status_response.text
    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload["bundle_downstream_proof"] = bundle_proof_response.json()
    payload["candidate_b_visual_lane_status_evidence"] = status
    payload["runtime_downstream_proof"] = proof_response.json()
    payload["operator_status_evidence"] = operator_status_response.json()
    return payload


def test_candidate_b_default_readiness_ready_path_is_read_only_and_non_promoting(client: TestClient, tmp_path: Path) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()

    payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready"
    assert body["readiness_state"] == "candidate_b_default_promotion_ready_for_separate_selection"
    assert body["blocked_reasons"] == []
    assert body["candidate_b_selector_evidence"]["candidate_b_is_visual_lane_mode"] is True
    assert body["candidate_b_selector_evidence"]["candidate_b_visual_lane_mode"] == CANDIDATE_B_VISUAL_LANE_MODE
    assert body["candidate_b_selector_evidence"]["candidate_b_visual_lane_mode_admitted"] is True
    assert body["candidate_b_selector_evidence"]["candidate_b_is_default_visual_lane_mode"] is False
    assert body["candidate_b_selector_evidence"]["candidate_b_visual_lane_selector_is_explicit"] is True
    assert body["candidate_b_selector_evidence"]["candidate_b_default_for_eligible_pdf_when_engine_omitted"] is True
    assert body["candidate_b_selector_evidence"]["candidate_b_runtime_selector_is_opt_in"] is True
    assert body["candidate_b_selector_evidence"]["candidate_b_visual_lane_material_ingestion_enabled"] is False
    assert body["baseline_current_default_evidence"]["baseline_default_changed"] is False
    assert body["baseline_current_default_evidence"]["non_pdf_document_processing_engine_default"] == "baseline"
    assert body["baseline_current_default_evidence"]["explicit_baseline_rollback_preserved"] is True
    assert body["candidate_a_admitted_variant_evidence"]["visual_lane_mode"] == "candidate_a_page_evidence_v1"
    assert body["bridge_receipts"]["bundle"]["governed_retained_artifact_family_hash"]
    assert body["bridge_receipts"]["runtime"]["governed_retained_artifact_family_hash"]
    assert body["bridge_receipts"]["runtime"]["visual_lane_mode"] == CANDIDATE_B_VISUAL_LANE_MODE
    assert (
        body["bridge_receipts"]["runtime"]["candidate_b_visual_lane_evidence"]["candidate_b_visual_lane_selected"]
        is True
    )
    assert body["authority_hashes"]["bundle"]["governed_retained_artifact_family_hash"]
    assert body["authority_hashes"]["runtime"]["governed_retained_artifact_family_hash"]
    assert body["downstream_proofs"]["runtime"]["visual_lane_mode_enabled"] is True
    assert body["downstream_proofs"]["runtime"]["visual_lane_mode"] == CANDIDATE_B_VISUAL_LANE_MODE
    assert (
        body["candidate_b_visual_lane_status_evidence"]["candidate_b_visual_lane_status_projection_visible"]
        is True
    )
    assert body["candidate_b_visual_lane_status_evidence"]["bridge_receipt_id"] == runtime_receipt_id
    assert body["candidate_b_visual_lane_status_evidence"]["visual_lane_mode"] == CANDIDATE_B_VISUAL_LANE_MODE
    assert body["candidate_b_visual_lane_status_evidence"]["status_hash"]
    assert body["default_selector_change_enabled"] is True
    assert body["candidate_b_default_promotion_enabled"] is True
    assert body["negative_invariants"]["candidate_b_visual_lane_mode_enabled"] is True
    assert body["negative_invariants"]["candidate_b_visual_lane_default_enabled"] is False
    assert body["negative_invariants"]["candidate_b_visual_lane_material_ingestion_enabled"] is False
    assert body["selector_mutation_performed"] is False
    assert body["rollback_to_baseline"]["depends_on_candidate_b_artifacts"] is False
    assert body["next_allowed_actions"] == [
        "monitor_candidate_b_default_selector",
        "use_explicit_baseline_document_processing_engine_for_rollback",
    ]
    assert str(tmp_path) not in json.dumps(body, sort_keys=True)


def test_candidate_b_default_readiness_accepts_live_visual_lane_status_response(
    client: TestClient,
    tmp_path: Path,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    bundle_proof_response = client.post(
        BUNDLE_PROOF_ENDPOINT,
        json=_bundle_downstream_proof_request(bundle_receipt_id),
    )
    assert bundle_proof_response.status_code == 200, bundle_proof_response.text
    bundle_proof = bundle_proof_response.json()
    assert bundle_proof["status"] == "proven"
    assert bundle_proof["candidate_b_source_kind"] == "bundle"
    assert bundle_proof["visual_lane_mode_enabled"] is False
    visual_status_response = client.post(VISUAL_STATUS_ENDPOINT, json=_visual_lane_status_request(runtime_receipt_id))
    assert visual_status_response.status_code == 200, visual_status_response.text

    payload = _payload_with_live_runtime_proof(
        client,
        bundle_receipt_id,
        runtime_receipt_id,
        visual_status=visual_status_response.json(),
    )

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready"
    assert body["candidate_b_default_promotion_enabled"] is True
    assert (
        body["candidate_b_visual_lane_status_evidence"]["bridge_receipt_hash"]
        == visual_status_response.json()["bridge_receipt_hash"]
    )
    assert (
        body["candidate_b_visual_lane_status_evidence"]["candidate_b_visual_lane_status_projection_visible"]
        is True
    )
    assert str(tmp_path) not in json.dumps(body, sort_keys=True)


def test_candidate_b_default_readiness_blocks_unpersisted_runtime_downstream_proof(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()

    response = client.post(READY_ENDPOINT, json=_payload(bundle_receipt_id, runtime_receipt_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["candidate_b_default_promotion_enabled"] is False
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_runtime_downstream_proof_receipt_missing" in codes


def test_candidate_b_default_readiness_accepts_live_runtime_downstream_proof_response(
    client: TestClient,
    tmp_path: Path,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    bundle_proof_response = client.post(
        BUNDLE_PROOF_ENDPOINT,
        json=_bundle_downstream_proof_request(bundle_receipt_id),
    )
    assert bundle_proof_response.status_code == 200, bundle_proof_response.text
    bundle_proof = bundle_proof_response.json()
    assert bundle_proof["status"] == "proven"
    assert bundle_proof["candidate_b_source_kind"] == "bundle"
    assert bundle_proof["visual_lane_mode_enabled"] is False
    visual_status_response = client.post(VISUAL_STATUS_ENDPOINT, json=_visual_lane_status_request(runtime_receipt_id))
    assert visual_status_response.status_code == 200, visual_status_response.text

    proof_response = client.post(
        DOWNSTREAM_PROOF_ENDPOINT,
        json=_downstream_proof_request(runtime_receipt_id, visual_status_response.json()),
    )
    assert proof_response.status_code == 200, proof_response.text
    proof = proof_response.json()
    assert proof["status"] == "proven"
    assert proof["candidate_b_source_kind"] == "runtime"
    assert proof["visual_lane_mode_enabled"] is True
    assert proof["visual_lane_mode"] == CANDIDATE_B_VISUAL_LANE_MODE
    assert sorted(proof["coverage"]) == sorted(FULL_COVERAGE)
    assert proof["raw_local_path_exposed"] is False
    assert proof["provider_public_url_enabled"] is False
    proof_receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / runtime_receipt_id
        / "downstream-proof"
        / f"{proof['proof_receipt_id']}.json"
    )
    assert proof_receipt_path.is_file()

    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload["bundle_downstream_proof"] = bundle_proof
    payload["candidate_b_visual_lane_status_evidence"] = visual_status_response.json()
    payload["runtime_downstream_proof"] = proof
    operator_status_response = client.post(
        OPERATOR_STATUS_ENDPOINT,
        json=_operator_status_request(bundle_receipt_id, runtime_receipt_id, visual_status_response.json(), proof),
    )
    assert operator_status_response.status_code == 200, operator_status_response.text
    payload["operator_status_evidence"] = operator_status_response.json()
    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready"
    assert body["downstream_proofs"]["bundle"]["proof_hash"] == bundle_proof["proof_hash"]
    assert body["downstream_proofs"]["runtime"]["proof_hash"] == proof["proof_hash"]
    assert body["candidate_b_default_promotion_enabled"] is True
    assert str(tmp_path) not in json.dumps(body, sort_keys=True)


def test_candidate_b_default_readiness_blocks_loose_operator_status_evidence(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    visual_status_response = client.post(VISUAL_STATUS_ENDPOINT, json=_visual_lane_status_request(runtime_receipt_id))
    assert visual_status_response.status_code == 200, visual_status_response.text
    proof_response = client.post(
        DOWNSTREAM_PROOF_ENDPOINT,
        json=_downstream_proof_request(runtime_receipt_id, visual_status_response.json()),
    )
    assert proof_response.status_code == 200, proof_response.text
    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload["candidate_b_visual_lane_status_evidence"] = visual_status_response.json()
    payload["runtime_downstream_proof"] = proof_response.json()

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_operator_status_schema_id_mismatch" in codes
    assert "candidate_b_default_readiness_operator_status_authority_field_missing" in codes
    assert body["candidate_b_default_promotion_enabled"] is False


def test_candidate_b_operator_status_rejects_path_like_receipt_id(client: TestClient) -> None:
    response = client.post(
        OPERATOR_STATUS_ENDPOINT,
        json=_operator_status_request("../bundle", "cb-runtime-bridge-placeholder", {}, {}),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_operator_status_storage_id_invalid"


def test_candidate_b_runtime_downstream_proof_rejects_nested_path_authority(client: TestClient) -> None:
    runtime_receipt_id = _write_runtime_receipt()
    visual_status_response = client.post(VISUAL_STATUS_ENDPOINT, json=_visual_lane_status_request(runtime_receipt_id))
    assert visual_status_response.status_code == 200, visual_status_response.text
    payload = _downstream_proof_request(runtime_receipt_id, visual_status_response.json())
    payload["coverage_evidence"]["gate_b"]["local_path"] = "C:/private/source.pdf"

    response = client.post(DOWNSTREAM_PROOF_ENDPOINT, json=payload)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_downstream_proof_forbidden_request_fields"
    assert "coverage_evidence.gate_b.local_path" in body["error"]["details"]["blocked_nested_fields"]


def test_candidate_b_bundle_downstream_proof_rejects_nested_path_authority(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    payload = _bundle_downstream_proof_request(bundle_receipt_id)
    payload["coverage_evidence"]["gate_b"]["local_path"] = "C:/private/source.pdf"

    response = client.post(BUNDLE_PROOF_ENDPOINT, json=payload)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_bundle_downstream_proof_forbidden_request_fields"
    assert "coverage_evidence.gate_b.local_path" in body["error"]["details"]["blocked_nested_fields"]


def test_candidate_b_default_readiness_blocks_missing_runtime_receipt(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload["candidate_b_runtime_bridge_receipt_id"] = "cb-runtime-l3-missing"
    payload["runtime_downstream_proof"]["bridge_receipt_id"] = "cb-runtime-l3-missing"

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


def test_candidate_b_default_readiness_blocks_baseline_visual_lane_runtime_receipt(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt(visual_lane_mode="baseline")

    response = client.post(READY_ENDPOINT, json=_payload(bundle_receipt_id, runtime_receipt_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_runtime_receipt_visual_lane_mode_mismatch" in codes
    assert "candidate_b_default_readiness_runtime_visual_lane_not_selected" in codes
    assert body["candidate_b_default_promotion_enabled"] is False


def test_candidate_b_default_readiness_blocks_runtime_proof_without_visual_lane(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload["runtime_downstream_proof"]["visual_lane_mode_enabled"] = False
    payload["runtime_downstream_proof"]["visual_lane_mode"] = "baseline"

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_runtime_downstream_visual_lane_mode_not_enabled" in codes
    assert "candidate_b_default_readiness_runtime_downstream_visual_lane_mode_mismatch" in codes
    assert body["candidate_b_default_promotion_enabled"] is False


def test_candidate_b_default_readiness_blocks_missing_visual_lane_status_evidence(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload.pop("candidate_b_visual_lane_status_evidence")

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 422, response.text


def test_candidate_b_default_readiness_blocks_stale_visual_lane_status_evidence(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload["candidate_b_visual_lane_status_evidence"]["bridge_receipt_hash"] = "9" * 64

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_visual_lane_status_bridge_receipt_hash_mismatch" in codes
    assert body["candidate_b_default_promotion_enabled"] is False


def test_candidate_b_default_readiness_blocks_visual_lane_status_projection_exposure(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload["candidate_b_visual_lane_status_evidence"]["operator_projection"]["raw_url_exposed"] = True

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_visual_lane_status_raw_url_exposed_not_false" in codes
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
