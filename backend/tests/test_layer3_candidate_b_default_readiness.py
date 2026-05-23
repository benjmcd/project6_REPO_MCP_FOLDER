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
    layer3_candidate_b_final_proof,
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
CLOSURE_EVIDENCE_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/default-promotion/closure-evidence"
FINAL_PROOF_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/default-promotion/final-proof"
FINAL_PROOF_STATUS_ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/default-promotion/final-proof/status"
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


def _artifact_family_hash(kind: str, payload: dict[str, Any]) -> str:
    hash_version = (
        layer3_candidate_b_bundle_bridge.AUTHORITY_HASH_VERSION
        if kind == "bundle"
        else layer3_candidate_b_runtime_bridge.AUTHORITY_HASH_VERSION
    )
    return _stable_hash({"hash_version": hash_version, "classification": payload})


def _artifact_family(kind: str) -> dict[str, Any]:
    visual_ref = "raw/annotated/fontish.pdf" if kind == "bundle" else "storage/input.pdf"
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
                "source_ref": visual_ref,
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
        "product_inspection_artifacts": [
            {
                "source_ref": visual_ref,
                "artifact_role": "source_pdf",
                "extension": ".pdf",
                "sha256": "d" * 64,
                "size_bytes": 12,
                "material_text_payload": False,
            }
        ],
        "delivery_artifacts": [
            {
                "source_ref": visual_ref,
                "artifact_role": "source_pdf",
                "extension": ".pdf",
                "sha256": "d" * 64,
                "size_bytes": 12,
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
    return {**payload, "artifact_family_hash": _artifact_family_hash(kind, payload)}


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


DELIVERY_ARTIFACT_AUTHORITY_COVERAGE = {
    "external_export_download_prepare",
    "same_origin_delivery_status",
    "same_origin_delivery",
    "provider_private_prepare",
    "provider_private_status",
    "provider_private_use",
    "provider_private_revoke",
    "internal_webhook_dispatch",
    "internal_webhook_status",
}


def _coverage_evidence(
    coverage: list[str] | None = None,
    *,
    retained_artifact_family_hash: str | None = None,
) -> dict[str, Any]:
    steps = FULL_COVERAGE if coverage is None else coverage
    result = {}
    for step in steps:
        entry = {
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
        if step in DELIVERY_ARTIFACT_AUTHORITY_COVERAGE:
            entry["candidate_b_retained_artifact_family_hash"] = retained_artifact_family_hash or "f" * 64
            entry["candidate_b_delivery_artifact_roles_bound"] = True
        result[step] = entry
    return result


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
    coverage_evidence = _coverage_evidence(
        coverage,
        retained_artifact_family_hash=receipt["governed_retained_artifact_family_hash"],
    )
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
    receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / runtime_receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "client_request_id": "candidate-b-downstream-proof",
        "proof_mode": "candidate_b_visual_lane_runtime_downstream_e2e_proof_v1",
        "operator_decision": "record_candidate_b_visual_lane_runtime_downstream_e2e_proof",
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "bridge_receipt_id": runtime_receipt_id,
        "candidate_b_visual_lane_status_evidence": visual_lane_status,
        "coverage_evidence": _coverage_evidence(
            retained_artifact_family_hash=receipt["governed_retained_artifact_family_hash"]
        ),
        "operator_confirmation": True,
    }


def _bundle_downstream_proof_request(bundle_receipt_id: str, *, coverage: list[str] | None = None) -> dict[str, Any]:
    receipt_path = Path(settings.layer3_candidate_b_bundle_bridge_dir) / bundle_receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "client_request_id": "candidate-b-bundle-downstream-proof",
        "proof_mode": "candidate_b_bundle_downstream_e2e_proof_v1",
        "operator_decision": "record_candidate_b_bundle_downstream_e2e_proof",
        "candidate_b_bundle_id": CANDIDATE_B_BUNDLE_ID,
        "bridge_receipt_id": bundle_receipt_id,
        "coverage_evidence": _coverage_evidence(
            coverage,
            retained_artifact_family_hash=receipt["governed_retained_artifact_family_hash"],
        ),
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


def _closure_evidence_request(
    bundle_receipt_id: str,
    runtime_receipt_id: str,
    bundle_downstream_proof: dict[str, Any],
    runtime_downstream_proof: dict[str, Any],
    operator_status: dict[str, Any],
) -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-closure-evidence",
        "closure_mode": "candidate_b_default_promotion_closure_evidence_v1",
        "operator_decision": "record_candidate_b_default_promotion_closure_evidence",
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
        "bundle_downstream_proof": bundle_downstream_proof,
        "runtime_downstream_proof": runtime_downstream_proof,
        "operator_status_evidence": operator_status,
    }


def _final_proof_request(readiness_audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-final-proof",
        "proof_mode": "candidate_b_default_promotion_final_proof_v1",
        "operator_decision": "record_candidate_b_default_promotion_final_proof",
        "readiness_audit": readiness_audit,
        "operator_confirmation": True,
    }


def _final_proof_status_request(runtime_receipt_id: str, proof_receipt_id: str) -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-final-proof-status",
        "status_mode": "candidate_b_default_promotion_final_proof_status_v1",
        "operator_decision": "inspect_candidate_b_default_promotion_final_proof_status",
        "candidate_b_runtime_bridge_receipt_id": runtime_receipt_id,
        "proof_receipt_id": proof_receipt_id,
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
        "closure_evidence": {
            "eligible_corpus_scope": READY_SCOPE,
            "regression_disposition": READY_REGRESSION,
            "rollback_to_baseline_confirmation": True,
            "operator_confirmation": True,
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
    closure_response = client.post(
        CLOSURE_EVIDENCE_ENDPOINT,
        json=_closure_evidence_request(
            bundle_receipt_id,
            runtime_receipt_id,
            bundle_proof_response.json(),
            proof_response.json(),
            operator_status_response.json(),
        ),
    )
    assert closure_response.status_code == 200, closure_response.text
    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload["bundle_downstream_proof"] = bundle_proof_response.json()
    payload["candidate_b_visual_lane_status_evidence"] = status
    payload["runtime_downstream_proof"] = proof_response.json()
    payload["operator_status_evidence"] = operator_status_response.json()
    payload["closure_evidence"] = closure_response.json()
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
    assert (
        body["operator_status_evidence"]["runtime_delivery_artifact_authority_hash"]
        == body["authority_hashes"]["runtime"]["governed_retained_artifact_family_hash"]
    )
    assert body["operator_status_evidence"]["runtime_delivery_artifact_coverage_steps"] == sorted(
        DELIVERY_ARTIFACT_AUTHORITY_COVERAGE
    )
    assert body["operator_status_evidence"]["runtime_delivery_artifact_role_previews"] == [
        {
            "display_ref": "input.pdf",
            "artifact_role": "source_pdf",
            "category": None,
            "extension": ".pdf",
            "sha256": "d" * 64,
            "material_text_payload": False,
        }
    ]
    assert body["operator_status_evidence"]["runtime_delivery_artifact_projection_visible"] is True
    assert body["operator_status_evidence"]["runtime_delivery_artifact_roles_bound"] is True
    assert (
        body["closure_evidence"]["candidate_b_operator_status_evidence"]
        == body["operator_status_evidence"]
    )
    assert (
        body["closure_evidence"]["candidate_b_operator_status_evidence"]["runtime_delivery_artifact_authority_hash"]
        == body["authority_hashes"]["runtime"]["governed_retained_artifact_family_hash"]
    )
    inspection = body["candidate_b_final_operator_inspection_evidence"]
    assert inspection["status"] == "available"
    assert inspection["final_operator_inspection_hash"]
    assert inspection["bundle"]["visual_page_evidence_count"] == 1
    assert inspection["bundle"]["product_inspection_artifact_count"] == 1
    assert inspection["bundle"]["delivery_artifact_count"] == 1
    assert inspection["runtime"]["visual_page_evidence_count"] == 1
    assert inspection["runtime"]["product_inspection_artifact_count"] == 1
    assert inspection["runtime"]["delivery_artifact_count"] == 1
    assert inspection["bundle"]["role_previews"]["visual_page_evidence"] == [
        {
            "display_ref": "fontish.pdf",
            "artifact_role": "source_pdf",
            "category": None,
            "extension": ".pdf",
            "sha256": "d" * 64,
            "material_text_payload": False,
        }
    ]
    assert inspection["runtime"]["role_previews"]["delivery_artifacts"] == [
        {
            "display_ref": "input.pdf",
            "artifact_role": "source_pdf",
            "category": None,
            "extension": ".pdf",
            "sha256": "d" * 64,
            "material_text_payload": False,
        }
    ]
    assert "storage/input.pdf" not in json.dumps(inspection, sort_keys=True)
    assert "raw/annotated/fontish.pdf" not in json.dumps(inspection, sort_keys=True)
    assert inspection["raw_local_path_exposed"] is False
    assert inspection["raw_url_exposed"] is False
    assert inspection["artifact_bytes_exposed"] is False
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
    final_proof_response = client.post(FINAL_PROOF_ENDPOINT, json=_final_proof_request(body))
    assert final_proof_response.status_code == 200, final_proof_response.text
    final_proof = final_proof_response.json()
    assert final_proof["status"] == "proven"
    assert final_proof["proof_state"] == "candidate_b_default_promotion_final_proven"
    assert final_proof["readiness_audit_hash"] == body["readiness_audit_hash"]
    assert final_proof["candidate_b_default_promotion_enabled"] is True
    assert final_proof["rollback_selector"] == "baseline"
    assert final_proof["final_operator_inspection_complete"] is True
    assert final_proof["final_operator_inspection_hash"] == inspection["final_operator_inspection_hash"]
    assert final_proof["operator_status_hash"] == body["operator_status_evidence"]["operator_status_hash"]
    assert final_proof["candidate_b_operator_status_evidence"] == body["operator_status_evidence"]
    assert final_proof["candidate_b_operator_status_evidence"]["runtime_delivery_artifact_role_previews"] == [
        {
            "display_ref": "input.pdf",
            "artifact_role": "source_pdf",
            "category": None,
            "extension": ".pdf",
            "sha256": "d" * 64,
            "material_text_payload": False,
        }
    ]
    assert final_proof["candidate_b_final_operator_inspection_evidence"] == inspection
    assert final_proof["selector_mutation_performed"] is False
    status_response = client.post(
        FINAL_PROOF_STATUS_ENDPOINT,
        json=_final_proof_status_request(runtime_receipt_id, final_proof["proof_receipt_id"]),
    )
    assert status_response.status_code == 200, status_response.text
    final_status = status_response.json()
    assert final_status["status"] == "available"
    assert final_status["proof_hash"] == final_proof["proof_hash"]
    assert final_status["candidate_b_default_promotion_enabled"] is True
    assert final_status["rollback_selector"] == "baseline"
    assert final_status["final_operator_inspection_complete"] is True
    assert final_status["operator_status_hash"] == body["operator_status_evidence"]["operator_status_hash"]
    assert final_status["candidate_b_operator_status_evidence"] == body["operator_status_evidence"]
    assert final_status["candidate_b_operator_status_evidence"]["runtime_delivery_artifact_role_previews"][0][
        "display_ref"
    ] == "input.pdf"
    assert final_status["candidate_b_final_operator_inspection_evidence"] == inspection
    assert final_status["selector_mutation_performed"] is False
    assert str(tmp_path) not in json.dumps(final_status, sort_keys=True)
    proof_receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / runtime_receipt_id
        / "default-promotion-final-proof"
        / f"{final_proof['proof_receipt_id']}.json"
    )
    assert proof_receipt_path.is_file()
    assert str(tmp_path) not in json.dumps(body, sort_keys=True)


def test_candidate_b_readiness_does_not_echo_role_previews_when_roles_are_missing(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    receipt_path = Path(settings.layer3_candidate_b_bundle_bridge_dir) / bundle_receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    artifact_family = receipt["governed_retained_artifact_family"]
    artifact_family.pop("roles")
    artifact_family["role_previews"] = {
        "visual_page_evidence": [{"display_ref": "raw/annotated/fontish.pdf"}],
        "product_inspection_artifacts": [{"display_ref": "raw/annotated/fontish.pdf"}],
        "delivery_artifacts": [{"display_ref": "raw/annotated/fontish.pdf"}],
    }
    _write_json(receipt_path, receipt)

    response = client.post(READY_ENDPOINT, json=_payload(bundle_receipt_id, runtime_receipt_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_bundle_governed_artifact_roles_missing" in codes
    inspection = body["candidate_b_final_operator_inspection_evidence"]
    assert inspection["status"] == "blocked"
    assert inspection["bundle"]["role_previews"] == {}
    assert "raw/annotated/fontish.pdf" not in json.dumps(body, sort_keys=True)


def test_candidate_b_final_proof_rejects_stale_runtime_bridge_receipt(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    readiness_payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    readiness_response = client.post(READY_ENDPOINT, json=readiness_payload)
    assert readiness_response.status_code == 200, readiness_response.text
    runtime_receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / runtime_receipt_id / "receipt.json"
    runtime_receipt = json.loads(runtime_receipt_path.read_text(encoding="utf-8"))
    runtime_receipt["bridge_receipt_hash"] = "0" * 64
    _write_json(runtime_receipt_path, runtime_receipt)

    response = client.post(FINAL_PROOF_ENDPOINT, json=_final_proof_request(readiness_response.json()))

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_final_proof_runtime_bridge_receipt_hash_mismatch"


def test_candidate_b_final_proof_rejects_stale_bundle_bridge_receipt(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    readiness_payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    readiness_response = client.post(READY_ENDPOINT, json=readiness_payload)
    assert readiness_response.status_code == 200, readiness_response.text
    bundle_receipt_path = Path(settings.layer3_candidate_b_bundle_bridge_dir) / bundle_receipt_id / "receipt.json"
    bundle_receipt = json.loads(bundle_receipt_path.read_text(encoding="utf-8"))
    bundle_receipt["bridge_receipt_hash"] = "0" * 64
    _write_json(bundle_receipt_path, bundle_receipt)

    response = client.post(FINAL_PROOF_ENDPOINT, json=_final_proof_request(readiness_response.json()))

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_final_proof_bundle_bridge_receipt_hash_mismatch"


def test_candidate_b_final_proof_status_rejects_stale_runtime_bridge_receipt(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    readiness_payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    readiness_response = client.post(READY_ENDPOINT, json=readiness_payload)
    assert readiness_response.status_code == 200, readiness_response.text
    final_proof_response = client.post(FINAL_PROOF_ENDPOINT, json=_final_proof_request(readiness_response.json()))
    assert final_proof_response.status_code == 200, final_proof_response.text
    final_proof = final_proof_response.json()
    runtime_receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / runtime_receipt_id / "receipt.json"
    runtime_receipt = json.loads(runtime_receipt_path.read_text(encoding="utf-8"))
    runtime_receipt["bridge_receipt_hash"] = "0" * 64
    _write_json(runtime_receipt_path, runtime_receipt)

    response = client.post(
        FINAL_PROOF_STATUS_ENDPOINT,
        json=_final_proof_status_request(runtime_receipt_id, final_proof["proof_receipt_id"]),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_final_proof_runtime_bridge_receipt_hash_mismatch"


def test_candidate_b_operator_delivery_projection_fields_are_declared_in_openapi(client: TestClient) -> None:
    openapi = client.app.openapi()
    schemas = openapi["components"]["schemas"]
    operator_props = schemas["Layer3CandidateBDefaultPromotionOperatorStatusResponse"]["properties"]
    final_proof_props = schemas["Layer3CandidateBDefaultPromotionFinalProofResponse"]["properties"]
    final_status_props = schemas["Layer3CandidateBDefaultPromotionFinalProofStatusResponse"]["properties"]

    for field in (
        "runtime_delivery_artifact_authority_hash",
        "runtime_delivery_artifact_coverage_steps",
        "runtime_delivery_artifact_projection_visible",
        "runtime_delivery_artifact_roles_bound",
    ):
        assert field in operator_props
    assert "candidate_b_operator_status_evidence" in final_proof_props
    assert "operator_status_hash" in final_status_props
    assert "candidate_b_operator_status_evidence" in final_status_props
    closure_props = schemas["Layer3CandidateBDefaultPromotionClosureEvidenceResponse"]["properties"]
    assert "candidate_b_operator_status_evidence" in closure_props


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
    closure_response = client.post(
        CLOSURE_EVIDENCE_ENDPOINT,
        json=_closure_evidence_request(
            bundle_receipt_id,
            runtime_receipt_id,
            bundle_proof,
            proof,
            operator_status_response.json(),
        ),
    )
    assert closure_response.status_code == 200, closure_response.text
    payload["operator_status_evidence"] = operator_status_response.json()
    payload["closure_evidence"] = closure_response.json()
    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ready"
    assert body["closure_evidence"]["closure_evidence_hash"] == closure_response.json()["closure_evidence_hash"]
    assert body["downstream_proofs"]["bundle"]["proof_hash"] == bundle_proof["proof_hash"]
    assert body["downstream_proofs"]["runtime"]["proof_hash"] == proof["proof_hash"]
    assert body["candidate_b_default_promotion_enabled"] is True
    assert str(tmp_path) not in json.dumps(body, sort_keys=True)


@pytest.mark.parametrize(
    "field",
    ["visual_ref_total", "candidate_b_visual_ref_total", "candidate_b_retained_source_pdf_ref_count"],
)
def test_candidate_b_runtime_downstream_proof_blocks_empty_visual_lane_status_counts(
    client: TestClient,
    field: str,
) -> None:
    runtime_receipt_id = _write_runtime_receipt()
    visual_status_response = client.post(VISUAL_STATUS_ENDPOINT, json=_visual_lane_status_request(runtime_receipt_id))
    assert visual_status_response.status_code == 200, visual_status_response.text
    visual_status = visual_status_response.json()
    visual_status["candidate_b_visual_lane_evidence"][field] = 0

    response = client.post(
        DOWNSTREAM_PROOF_ENDPOINT,
        json=_downstream_proof_request(runtime_receipt_id, visual_status),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_downstream_proof_visual_lane_status_evidence_count_missing"
    assert body["error"]["details"]["field"] == field


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


def test_candidate_b_default_readiness_blocks_loose_closure_evidence(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    payload["closure_evidence"] = {
        "eligible_corpus_scope": READY_SCOPE,
        "regression_disposition": READY_REGRESSION,
        "rollback_to_baseline_confirmation": True,
        "operator_confirmation": True,
    }

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_closure_schema_id_mismatch" in codes
    assert "candidate_b_default_readiness_closure_authority_field_missing" in codes
    assert body["candidate_b_default_promotion_enabled"] is False


def test_candidate_b_default_readiness_blocks_stale_closure_operator_status_projection(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    payload["closure_evidence"]["candidate_b_operator_status_evidence"]["runtime_delivery_artifact_roles_bound"] = False

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_closure_operator_status_projection_incomplete" in codes
    assert body["candidate_b_default_promotion_enabled"] is False


def test_candidate_b_default_readiness_blocks_mismatched_closure_operator_status_authority(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    payload["closure_evidence"]["candidate_b_operator_status_evidence"][
        "runtime_delivery_artifact_authority_hash"
    ] = "stale-authority-hash"

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_closure_operator_status_projection_mismatch" in codes
    assert body["candidate_b_default_promotion_enabled"] is False


def test_candidate_b_final_proof_rejects_blocked_readiness_audit(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    payload["regression_disposition"] = "unacceptable_regression_found"
    readiness_response = client.post(READY_ENDPOINT, json=payload)
    assert readiness_response.status_code == 200, readiness_response.text
    assert readiness_response.json()["status"] == "blocked"

    response = client.post(FINAL_PROOF_ENDPOINT, json=_final_proof_request(readiness_response.json()))

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_final_proof_readiness_audit_not_ready"


def test_candidate_b_final_proof_status_rejects_path_like_receipt_id(client: TestClient) -> None:
    response = client.post(
        FINAL_PROOF_STATUS_ENDPOINT,
        json=_final_proof_status_request("cb-runtime-l3-placeholder", "../proof"),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_final_proof_status_proof_receipt_id_invalid"


def test_candidate_b_final_proof_rejects_unredacted_operator_inspection_preview(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    readiness_payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    readiness_response = client.post(READY_ENDPOINT, json=readiness_payload)
    assert readiness_response.status_code == 200, readiness_response.text
    readiness = readiness_response.json()
    inspection = readiness["candidate_b_final_operator_inspection_evidence"]
    inspection["runtime"]["role_previews"]["delivery_artifacts"][0]["display_ref"] = "storage/input.pdf"
    inspection["final_operator_inspection_hash"] = layer3_candidate_b_final_proof._final_operator_inspection_hash(
        inspection
    )

    response = client.post(FINAL_PROOF_ENDPOINT, json=_final_proof_request(readiness))

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_final_proof_operator_inspection_role_preview_not_redacted"


def test_candidate_b_final_proof_status_rejects_stale_operator_inspection_evidence(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    readiness_payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    readiness_response = client.post(READY_ENDPOINT, json=readiness_payload)
    assert readiness_response.status_code == 200, readiness_response.text
    final_proof_response = client.post(FINAL_PROOF_ENDPOINT, json=_final_proof_request(readiness_response.json()))
    assert final_proof_response.status_code == 200, final_proof_response.text
    final_proof = final_proof_response.json()
    proof_receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / runtime_receipt_id
        / "default-promotion-final-proof"
        / f"{final_proof['proof_receipt_id']}.json"
    )
    stored = json.loads(proof_receipt_path.read_text(encoding="utf-8"))
    stored["candidate_b_final_operator_inspection_evidence"]["runtime"]["delivery_artifact_count"] = 0
    _write_json(proof_receipt_path, stored)

    response = client.post(
        FINAL_PROOF_STATUS_ENDPOINT,
        json=_final_proof_status_request(runtime_receipt_id, final_proof["proof_receipt_id"]),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_final_proof_status_operator_inspection_hash_mismatch"


def test_candidate_b_final_proof_status_rejects_stale_operator_status_evidence(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    readiness_payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    readiness_response = client.post(READY_ENDPOINT, json=readiness_payload)
    assert readiness_response.status_code == 200, readiness_response.text
    final_proof_response = client.post(FINAL_PROOF_ENDPOINT, json=_final_proof_request(readiness_response.json()))
    assert final_proof_response.status_code == 200, final_proof_response.text
    final_proof = final_proof_response.json()
    proof_receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / runtime_receipt_id
        / "default-promotion-final-proof"
        / f"{final_proof['proof_receipt_id']}.json"
    )
    stored = json.loads(proof_receipt_path.read_text(encoding="utf-8"))
    stored["candidate_b_operator_status_evidence"]["runtime_delivery_artifact_roles_bound"] = False
    _write_json(proof_receipt_path, stored)

    response = client.post(
        FINAL_PROOF_STATUS_ENDPOINT,
        json=_final_proof_status_request(runtime_receipt_id, final_proof["proof_receipt_id"]),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_final_proof_status_operator_status_delivery_projection_missing"
    assert body["error"]["details"]["field"] == "runtime_delivery_artifact_roles_bound"


def test_candidate_b_final_proof_status_rejects_unredacted_operator_status_delivery_preview(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    readiness_payload = _payload_with_live_runtime_proof(client, bundle_receipt_id, runtime_receipt_id)
    readiness_response = client.post(READY_ENDPOINT, json=readiness_payload)
    assert readiness_response.status_code == 200, readiness_response.text
    final_proof_response = client.post(FINAL_PROOF_ENDPOINT, json=_final_proof_request(readiness_response.json()))
    assert final_proof_response.status_code == 200, final_proof_response.text
    final_proof = final_proof_response.json()
    proof_receipt_path = (
        Path(settings.layer3_candidate_b_runtime_bridge_dir)
        / runtime_receipt_id
        / "default-promotion-final-proof"
        / f"{final_proof['proof_receipt_id']}.json"
    )
    stored = json.loads(proof_receipt_path.read_text(encoding="utf-8"))
    stored["candidate_b_operator_status_evidence"]["runtime_delivery_artifact_role_previews"][0][
        "display_ref"
    ] = "storage/input.pdf"
    _write_json(proof_receipt_path, stored)

    response = client.post(
        FINAL_PROOF_STATUS_ENDPOINT,
        json=_final_proof_status_request(runtime_receipt_id, final_proof["proof_receipt_id"]),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_final_proof_status_operator_status_delivery_preview_not_redacted"
    assert body["error"]["details"]["index"] == 0


def test_candidate_b_operator_status_rejects_path_like_receipt_id(client: TestClient) -> None:
    response = client.post(
        OPERATOR_STATUS_ENDPOINT,
        json=_operator_status_request("../bundle", "cb-runtime-bridge-placeholder", {}, {}),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_operator_status_storage_id_invalid"


def test_candidate_b_operator_status_rejects_unprojected_delivery_artifact_authority(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    visual_status_response = client.post(VISUAL_STATUS_ENDPOINT, json=_visual_lane_status_request(runtime_receipt_id))
    assert visual_status_response.status_code == 200, visual_status_response.text
    proof_response = client.post(
        DOWNSTREAM_PROOF_ENDPOINT,
        json=_downstream_proof_request(runtime_receipt_id, visual_status_response.json()),
    )
    assert proof_response.status_code == 200, proof_response.text
    proof = proof_response.json()
    proof["coverage_evidence"]["provider_private_use"].pop("candidate_b_retained_artifact_family_hash")

    response = client.post(
        OPERATOR_STATUS_ENDPOINT,
        json=_operator_status_request(bundle_receipt_id, runtime_receipt_id, visual_status_response.json(), proof),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_operator_status_runtime_delivery_artifact_authority_mismatch"
    assert body["error"]["details"]["coverage_step"] == "provider_private_use"


def test_candidate_b_operator_status_rejects_stale_runtime_artifact_family(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    visual_status_response = client.post(VISUAL_STATUS_ENDPOINT, json=_visual_lane_status_request(runtime_receipt_id))
    assert visual_status_response.status_code == 200, visual_status_response.text
    proof_response = client.post(
        DOWNSTREAM_PROOF_ENDPOINT,
        json=_downstream_proof_request(runtime_receipt_id, visual_status_response.json()),
    )
    assert proof_response.status_code == 200, proof_response.text
    receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / runtime_receipt_id / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["governed_retained_artifact_family"]["roles"]["delivery_artifacts"][0][
        "source_ref"
    ] = "storage/tampered.pdf"
    _write_json(receipt_path, receipt)

    response = client.post(
        OPERATOR_STATUS_ENDPOINT,
        json=_operator_status_request(
            bundle_receipt_id,
            runtime_receipt_id,
            visual_status_response.json(),
            proof_response.json(),
        ),
    )

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_operator_status_runtime_artifact_family_stale"


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


def test_candidate_b_bundle_downstream_proof_rejects_raw_url_evidence_ref(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    payload = _bundle_downstream_proof_request(bundle_receipt_id)
    payload["coverage_evidence"]["gate_b"]["evidence_ref"] = "https://example.test/raw-proof"

    response = client.post(BUNDLE_PROOF_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_bundle_downstream_proof_coverage_exposes_forbidden_reference"
    assert body["error"]["details"]["coverage_step"] == "gate_b"


def test_candidate_b_bundle_downstream_proof_preserves_safe_evidence_refs(client: TestClient) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    payload = _bundle_downstream_proof_request(bundle_receipt_id)
    payload["coverage_evidence"]["gate_b"]["evidence_ref"] = "candidate-b-bundle-downstream-proof://gate_b"

    response = client.post(BUNDLE_PROOF_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "proven"
    assert body["coverage_evidence"]["gate_b"]["evidence_ref"] == "candidate-b-bundle-downstream-proof://gate_b"
    assert "https://" not in json.dumps(body["coverage_evidence"], sort_keys=True)
    assert "file://" not in json.dumps(body["coverage_evidence"], sort_keys=True)


def test_candidate_b_runtime_downstream_proof_rejects_unbound_delivery_artifact_authority(
    client: TestClient,
) -> None:
    runtime_receipt_id = _write_runtime_receipt()
    visual_status_response = client.post(VISUAL_STATUS_ENDPOINT, json=_visual_lane_status_request(runtime_receipt_id))
    assert visual_status_response.status_code == 200, visual_status_response.text
    payload = _downstream_proof_request(runtime_receipt_id, visual_status_response.json())
    payload["coverage_evidence"]["provider_private_use"].pop("candidate_b_retained_artifact_family_hash")

    response = client.post(DOWNSTREAM_PROOF_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_downstream_proof_delivery_artifact_authority_mismatch"
    assert body["error"]["details"]["coverage_step"] == "provider_private_use"


def test_candidate_b_bundle_downstream_proof_rejects_unbound_delivery_artifact_roles(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    payload = _bundle_downstream_proof_request(bundle_receipt_id)
    payload["coverage_evidence"]["internal_webhook_dispatch"]["candidate_b_delivery_artifact_roles_bound"] = False

    response = client.post(BUNDLE_PROOF_ENDPOINT, json=payload)

    assert response.status_code == 409, response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_bundle_downstream_proof_delivery_artifact_roles_not_bound"
    assert body["error"]["details"]["coverage_step"] == "internal_webhook_dispatch"


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


def test_candidate_b_default_readiness_blocks_missing_runtime_inspection_delivery_artifacts(
    client: TestClient,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    runtime_receipt_path = Path(settings.layer3_candidate_b_runtime_bridge_dir) / runtime_receipt_id / "receipt.json"
    runtime_receipt = json.loads(runtime_receipt_path.read_text(encoding="utf-8"))
    family = runtime_receipt["governed_retained_artifact_family"]
    family["roles"]["product_inspection_artifacts"] = []
    family["roles"]["delivery_artifacts"] = []
    family["role_counts"] = {role: len(items) for role, items in family["roles"].items()}
    family_input = dict(family)
    family_input.pop("artifact_family_hash", None)
    family["artifact_family_hash"] = _artifact_family_hash("runtime", family_input)
    runtime_receipt["governed_retained_artifact_family_hash"] = family["artifact_family_hash"]
    runtime_receipt_input = {
        key: runtime_receipt[key]
        for key in (
            "schema_id",
            "schema_version",
            "bridge_mode",
            "candidate_b_run_id",
            "baseline_run_id",
            "candidate_a_run_id",
            "candidate_b_source_kind",
            "document_processing_engine",
            "visual_lane_mode",
            "compare_target_set_hash",
            "runtime_review_root_storage_authority_hash",
            "admitted_file_subset_hash",
            "governed_retained_artifact_family_hash",
            "redaction_policy_id",
        )
    }
    runtime_receipt["bridge_receipt_hash"] = _stable_hash(runtime_receipt_input)
    _write_json(runtime_receipt_path, runtime_receipt)

    response = client.post(READY_ENDPOINT, json=_payload(bundle_receipt_id, runtime_receipt_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_runtime_product_inspection_artifacts_missing" in codes
    assert "candidate_b_default_readiness_runtime_delivery_artifacts_missing" in codes
    assert body["candidate_b_final_operator_inspection_evidence"]["status"] == "blocked"
    assert body["candidate_b_final_operator_inspection_evidence"]["runtime"]["delivery_artifact_count"] == 0
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


@pytest.mark.parametrize(
    "field",
    ["visual_ref_total", "candidate_b_visual_ref_total", "candidate_b_retained_source_pdf_ref_count"],
)
def test_candidate_b_default_readiness_blocks_empty_visual_lane_status_counts(
    client: TestClient,
    field: str,
) -> None:
    bundle_receipt_id = _write_bundle_receipt()
    runtime_receipt_id = _write_runtime_receipt()
    payload = _payload(bundle_receipt_id, runtime_receipt_id)
    payload["candidate_b_visual_lane_status_evidence"]["candidate_b_visual_lane_evidence"][field] = 0
    payload["candidate_b_visual_lane_status_evidence"]["operator_projection"][field] = 0

    response = client.post(READY_ENDPOINT, json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "blocked"
    codes = {item["code"] for item in body["blocked_reasons"]}
    assert "candidate_b_default_readiness_visual_lane_status_evidence_count_missing" in codes
    assert "candidate_b_default_readiness_visual_lane_status_projection_count_missing" in codes
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
