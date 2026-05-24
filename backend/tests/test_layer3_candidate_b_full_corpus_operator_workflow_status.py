from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from fastapi.testclient import TestClient
import pytest

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.services import layer3_candidate_b_operator_workflow_access_policy as access_policy
from app.services import layer3_candidate_b_full_corpus_operator_workflow_status as workflow_status
from main import app


ENDPOINT = "/api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status"
BASELINE_RUN_ID = "baseline-run"
CANDIDATE_A_RUN_ID = "candidate-a-run"
CANDIDATE_B_RUN_ID = "candidate-b-run"
BRIDGE_RECEIPT_ID = "cb-runtime-l3-aaaaaaaaaaaaaaaaaaaaaaaa"
DOWNSTREAM_PROOF_ID = "cb-runtime-downstream-proof-bbbbbbbbbbbbbbbbbbbbbbbb"
COMPARE_TARGET_SET_HASH = "1" * 64
BRIDGE_RECEIPT_HASH = "2" * 64
DOWNSTREAM_PROOF_HASH = "3" * 64


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        settings,
        "layer3_candidate_b_full_corpus_operator_workflow_dir",
        str(tmp_path / "workflow-receipts"),
    )
    monkeypatch.setattr(settings, "auth_owner", "none")
    monkeypatch.setattr(settings, "trusted_proxy_mode", False)
    app.openapi_schema = None
    with TestClient(app) as test_client:
        yield test_client
    app.openapi_schema = None


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_receipt(extra: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    receipt_input = {
        "schema_id": workflow_status.WORKFLOW_SCHEMA_ID,
        "schema_version": workflow_status.SCHEMA_VERSION,
        "workflow_mode": workflow_status.WORKFLOW_MODE,
        "baseline_run_id": BASELINE_RUN_ID,
        "candidate_a_run_id": CANDIDATE_A_RUN_ID,
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "compare_target_set_hash": COMPARE_TARGET_SET_HASH,
        "bridge_receipt_id": BRIDGE_RECEIPT_ID,
        "bridge_receipt_hash": BRIDGE_RECEIPT_HASH,
        "downstream_proof_id": DOWNSTREAM_PROOF_ID,
        "downstream_proof_hash": DOWNSTREAM_PROOF_HASH,
        "coverage_count": 17,
    }
    receipt_hash = _stable_hash(receipt_input)
    receipt_id = f"{workflow_status.WORKFLOW_RECEIPT_PREFIX}-{receipt_hash[:24]}"
    receipt = {
        **receipt_input,
        "receipt_id": receipt_id,
        "receipt_hash": receipt_hash,
        "status": "proven",
        "server_time": "2026-05-23T00:00:00Z",
        "validate_only_triplet": True,
        "artifacts_seeded_or_generated_by_triplet_validator": False,
        "corpus": {
            "corpus_pdf_count": 69,
            "eligible_file_count": 71,
            "material_relative_name": "text/target-00001.md",
            "target_status_counts": {
                "baseline": {"recommended": 69},
                "candidate_a": {"recommended": 69},
                "candidate_b": {"recommended": 69},
            },
            "eligibility_summary": {
                "corpus_pdf_count": 69,
                "eligible_pdf_count": 69,
                "skipped_pdf_count": 0,
                "failed_pdf_count": 0,
                "source_directory_eligible_file_count": 71,
                "source_directory_extra_material_file_count": 2,
                "all_eligible_pdfs_processed": True,
                "candidate_b_target_status_counts": {"recommended": 69},
            },
        },
        "baseline_rollback": {
            "available": True,
            "selector": "baseline",
            "explicit_document_processing_engine": "baseline",
            "depends_on_candidate_b_artifacts": False,
            "candidate_a_visual_lane_preserved": True,
            "rollback_requires_selector_mutation": False,
        },
        "refs": {
            "baseline_runtime_root": "repo://artifacts/baseline",
            "candidate_a_runtime_root": "repo://artifacts/candidate-a",
            "candidate_b_runtime_root": "repo://artifacts/candidate-b",
            "bridge_dir": "repo://backend/app/storage_test_runtime/cb-full-corpus-operator-bridge",
            "curated_root": f"candidate-b-runtime-bridge://{BRIDGE_RECEIPT_ID}/curated",
            "receipt_dir": "repo://backend/app/storage_test_runtime/cb-full-corpus-operator-workflow",
        },
        "layer3": {
            "bridge_status": "prepared",
            "source_directory_scan_status": "available",
            "source_directory_eligible_file_count": 71,
            "qualitative_analysis_status": "completed",
            "external_export_download_status": "prepared",
            "same_origin_delivery_available": True,
            "provider_private_state": "provider_private_signed_url_ready",
            "provider_private_revoke_state": "provider_private_signed_url_revoked",
            "internal_webhook_state": "internal_webhook_dispatch_recorded",
            "visual_lane_status": "available",
            "downstream_proof_status": "proven",
        },
        "artifact_family": {
            "governed_retained_artifact_family_hash": "4" * 64,
            "role_counts": {
                "material_analysis_payloads": 71,
                "visual_page_evidence": 69,
                "provenance_audit_artifacts": 3,
                "product_inspection_artifacts": 69,
                "delivery_artifacts": 69,
            },
            "curated_file_count": 71,
            "text_file_count": 71,
        },
        "runtime_root_lifecycle": {
            "schema_id": "candidate_b.full_corpus_runtime_root_lifecycle.v1",
            "lifecycle_mode": "candidate_b_full_corpus_runtime_root_lifecycle_v1",
            "lifecycle_receipt_id": "cb-full-corpus-runtime-roots-cccccccccccccccccccccccc",
            "lifecycle_receipt_hash": "5" * 64,
            "runtime_parent_ref": "redacted://sha256/runtime-parent",
            "root_count": 3,
            "receipt_file": "repo://backend/app/storage_test_runtime/lifecycle/receipt.json",
            "validate_only_triplet": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
        },
        "negative_invariants": {
            "baseline_default_changed": False,
            "candidate_a_semantics_changed": False,
            "candidate_b_default_broadened_beyond_eligible_pdf": False,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "provider_public_url_enabled": False,
            "provider_object_writes_enabled": False,
            "connector_dispatch_enabled": False,
            "rag_vector_model_runtime_enabled": False,
            "frontend_durable_authority_enabled": False,
            "full_mockup_activation_enabled": False,
        },
    }
    if extra:
        receipt.update(extra)
    root = Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir)
    target = root / receipt_id / "receipt.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt_id, receipt


def _request(receipt_id: str, **overrides: str) -> dict[str, str]:
    payload = {
        "client_request_id": "candidate-b-full-corpus-workflow-status",
        "status_mode": workflow_status.STATUS_MODE,
        "operator_decision": workflow_status.OPERATOR_DECISION,
        "operator_workflow_receipt_id": receipt_id,
        "baseline_run_id": BASELINE_RUN_ID,
        "candidate_a_run_id": CANDIDATE_A_RUN_ID,
        "candidate_b_run_id": CANDIDATE_B_RUN_ID,
        "bridge_receipt_id": BRIDGE_RECEIPT_ID,
        "downstream_proof_id": DOWNSTREAM_PROOF_ID,
    }
    payload.update(overrides)
    return payload


def test_candidate_b_full_corpus_operator_workflow_status_is_read_only_and_redacted(client: TestClient) -> None:
    receipt_id, receipt = _write_receipt()

    response = client.post(ENDPOINT, json=_request(receipt_id))

    assert response.status_code == 200
    body = response.json()
    serialized = json.dumps(body, sort_keys=True)
    assert body["schema_id"] == workflow_status.SCHEMA_ID
    assert body["status"] == "available"
    assert body["workflow_status"] == "proven"
    assert body["workflow_receipt_id"] == receipt_id
    assert body["workflow_receipt_hash"] == receipt["receipt_hash"]
    assert body["bridge_receipt_id"] == BRIDGE_RECEIPT_ID
    assert body["downstream_proof_id"] == DOWNSTREAM_PROOF_ID
    assert body["coverage_count"] == 17
    assert body["corpus"]["eligible_file_count"] == 71
    assert body["eligibility_summary"] == receipt["corpus"]["eligibility_summary"]
    assert body["baseline_rollback"] == receipt["baseline_rollback"]
    assert body["artifact_family"]["role_counts"]["delivery_artifacts"] == 69
    assert body["runtime_root_lifecycle"]["available"] is True
    assert body["runtime_root_lifecycle"]["lifecycle_receipt_id"].startswith("cb-full-corpus-runtime-roots-")
    assert body["runtime_root_lifecycle"]["root_count"] == 3
    assert body["operator_projection"]["workflow_status_visible"] is True
    assert body["operator_projection"]["eligibility_summary_projection_visible"] is True
    assert body["operator_projection"]["baseline_rollback_projection_visible"] is True
    assert body["operator_projection"]["runtime_root_lifecycle_projection_visible"] is True
    assert body["operator_projection"]["process_execution_projection_visible"] is True
    policy = body["ownership_access_policy"]
    assert policy["policy_schema_id"] == access_policy.POLICY_SCHEMA_ID
    assert policy["policy_status"] == "admitted"
    assert policy["decision"] == "allow"
    assert policy["route_family"] == "workflow_status"
    assert policy["rendered_surface"] == "status"
    assert policy["audit_event_id"].startswith(access_policy.POLICY_RECEIPT_PREFIX)
    audit_path = (
        Path(settings.layer3_candidate_b_full_corpus_operator_workflow_dir)
        / policy["audit_event_id"]
        / "receipt.json"
    )
    assert audit_path.is_file()
    audit_event = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_event["schema_id"] == access_policy.POLICY_AUDIT_SCHEMA_ID
    assert audit_event["raw_operator_identity_exposed"] is False
    assert audit_event["raw_proxy_header_exposed"] is False
    assert audit_event["raw_local_path_exposed"] is False
    assert body["process_execution_projection"]["process_execution_projection_state"] == "not_started"
    assert body["operator_projection"]["raw_local_path_exposed"] is False
    assert body["validate_only_triplet"] is True
    assert body["artifacts_seeded_or_generated_by_triplet_validator"] is False
    assert body["raw_local_path_exposed"] is False
    assert body["raw_url_exposed"] is False
    assert body["selector_mutation_performed"] is False
    assert "C:\\" not in serialized
    assert "file:///" not in serialized
    assert "https://" not in serialized


def test_candidate_b_full_corpus_operator_workflow_status_rejects_stale_policy_hash(
    client: TestClient,
) -> None:
    receipt_id, _receipt = _write_receipt()

    response = client.post(ENDPOINT, json=_request(receipt_id, policy_hash="9" * 64))

    assert response.status_code == 409
    body = response.json()
    assert body["policy_status"] == "rejected"
    assert body["error"]["code"] == "candidate_b_operator_workflow_access_policy_stale_policy_hash"


def test_candidate_b_full_corpus_operator_workflow_status_proxy_requires_server_identity(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt_id, _receipt = _write_receipt()
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)

    response = client.post(ENDPOINT, json=_request(receipt_id))

    assert response.status_code == 401
    body = response.json()
    assert body["policy_status"] == "rejected"
    assert body["error"]["code"] == "candidate_b_operator_workflow_access_policy_missing_identity_authority"


def test_candidate_b_full_corpus_operator_workflow_status_proxy_rejects_cross_owner_receipt(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor_ref_hash = access_policy._stable_hash({"auth_owner": "proxy", "actor_ref": "alice"})
    tenant_ref_hash = access_policy._stable_hash(
        {"auth_owner": "proxy", "tenant_or_workspace_ref": "tenant-a"}
    )
    receipt_id, _receipt = _write_receipt(
        {
            "workflow_receipt_owner_binding": {
                "actor_ref_hash": actor_ref_hash,
                "tenant_or_workspace_ref_hash": tenant_ref_hash,
                "policy_hash": "8" * 64,
            }
        }
    )
    monkeypatch.setattr(settings, "auth_owner", "proxy")
    monkeypatch.setattr(settings, "trusted_proxy_mode", True)

    allowed = client.post(
        ENDPOINT,
        json=_request(receipt_id),
        headers={"X-Forwarded-User": "alice", "X-Forwarded-Groups": "tenant-a"},
    )
    rejected = client.post(
        ENDPOINT,
        json=_request(receipt_id),
        headers={"X-Forwarded-User": "bob", "X-Forwarded-Groups": "tenant-a"},
    )

    assert allowed.status_code == 200
    assert allowed.json()["ownership_access_policy"]["actor_ref_hash"] == actor_ref_hash
    assert rejected.status_code == 403
    body = rejected.json()
    assert body["policy_status"] == "rejected"
    assert body["error"]["code"] == "candidate_b_operator_workflow_access_policy_cross_owner_receipt"


def test_candidate_b_full_corpus_operator_workflow_status_rejects_incomplete_eligibility(
    client: TestClient,
) -> None:
    receipt_id, _receipt = _write_receipt(
        {
            "corpus": {
                "corpus_pdf_count": 69,
                "eligible_file_count": 71,
                "material_relative_name": "text/target-00001.md",
                "target_status_counts": {
                    "baseline": {"recommended": 69},
                    "candidate_a": {"recommended": 69},
                    "candidate_b": {"recommended": 68, "failed": 1},
                },
            }
        }
    )

    response = client.post(ENDPOINT, json=_request(receipt_id))

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_eligibility_not_complete"
    assert body["error"]["details"]["eligibility_summary"]["failed_pdf_count"] == 1


def test_candidate_b_full_corpus_operator_workflow_status_rejects_stale_rollback(
    client: TestClient,
) -> None:
    receipt_id, _receipt = _write_receipt(
        {
            "baseline_rollback": {
                "available": True,
                "selector": "baseline",
                "explicit_document_processing_engine": "baseline",
                "depends_on_candidate_b_artifacts": True,
                "candidate_a_visual_lane_preserved": True,
                "rollback_requires_selector_mutation": False,
            }
        }
    )

    response = client.post(ENDPOINT, json=_request(receipt_id))

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_baseline_rollback_mismatch"


def test_candidate_b_full_corpus_operator_workflow_status_rejects_stale_binding(client: TestClient) -> None:
    receipt_id, _receipt = _write_receipt()

    response = client.post(ENDPOINT, json=_request(receipt_id, candidate_b_run_id="stale-candidate-b-run"))

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_receipt_mismatch"


def test_candidate_b_full_corpus_operator_workflow_status_rejects_raw_authority_leak(client: TestClient) -> None:
    receipt_id, _receipt = _write_receipt(
        {
            "refs": {
                "baseline_runtime_root": "repo://artifacts/baseline",
                "candidate_a_runtime_root": "repo://artifacts/candidate-a",
                "candidate_b_runtime_root": "C:\\operator\\private\\candidate-b",
            }
        }
    )

    response = client.post(ENDPOINT, json=_request(receipt_id))

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_receipt_exposes_raw_authority"


def test_candidate_b_full_corpus_operator_workflow_status_rejects_invalid_runtime_root_lifecycle(
    client: TestClient,
) -> None:
    receipt_id, _receipt = _write_receipt(
        {
            "runtime_root_lifecycle": {
                "schema_id": "candidate_b.full_corpus_runtime_root_lifecycle.v1",
                "lifecycle_mode": "candidate_b_full_corpus_runtime_root_lifecycle_v1",
                "lifecycle_receipt_id": "cb-full-corpus-runtime-roots-cccccccccccccccccccccccc",
                "lifecycle_receipt_hash": "5" * 64,
                "runtime_parent_ref": "redacted://sha256/runtime-parent",
                "root_count": 2,
                "validate_only_triplet": True,
                "raw_local_path_exposed": False,
                "raw_url_exposed": False,
            }
        }
    )

    response = client.post(ENDPOINT, json=_request(receipt_id))

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_runtime_root_lifecycle_count_invalid"


def test_candidate_b_full_corpus_operator_workflow_status_requires_configured_receipt_root(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "layer3_candidate_b_full_corpus_operator_workflow_dir", "")

    response = client.post(ENDPOINT, json=_request("cb-full-corpus-operator-aaaaaaaaaaaaaaaaaaaaaaaa"))

    assert response.status_code == 409
    body = response.json()
    assert body["status"] == "blocked"
    assert body["error"]["code"] == "candidate_b_full_corpus_operator_workflow_status_dir_invalid"
