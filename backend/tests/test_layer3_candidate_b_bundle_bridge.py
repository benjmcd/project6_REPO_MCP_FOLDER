from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    AnalysisRun,
    ConnectorRun,
    ConnectorRunTarget,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3ProviderPrivateSignedUrlReceipt,
    L3ProviderPublicUrlReceipt,
    L3ReconciliationRecord,
    L3SourceDirectoryInternalWebhookDispatchReceipt,
)
from app.services import layer3_candidate_b_bundle_bridge, layer3_internal_webhook_connector
from app.services.layer3_source_directory_text_index import source_directory_material_text_index
from app.services.layer3_source_directory_vector_index import (
    source_directory_material_embedding_vector_index,
)
from main import app


BRIDGE_MODE = "candidate_b_bundle_curated_json_md_to_layer3_material_authority_v1"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    bridge_dir = tmp_path / "bridge"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", "")
    monkeypatch.setattr(settings, "layer3_candidate_b_bundle_bridge_dir", str(bridge_dir))
    bootstrap_storage_tree(storage_dir)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.openapi_schema = None
    with TestClient(app) as test_client:
        test_client.layer3_session_factory = session_local
        yield test_client
    app.dependency_overrides.clear()
    app.openapi_schema = None


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return _sha256(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_ref(checkout_root: Path, path: Path) -> str:
    return path.resolve().relative_to(checkout_root.resolve()).as_posix()


def _source_entry(checkout_root: Path, path: Path, category: str) -> dict[str, Any]:
    return {
        "category": category,
        "path": _repo_ref(checkout_root, path),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }


def _create_bundle(
    tmp_path: Path,
    *,
    omit_raw_json: bool = False,
) -> tuple[Path, str]:
    checkout_root = tmp_path / "checkout"
    bundle_root = checkout_root / "tests" / "reports" / "cb-compare-demo"
    raw_root = bundle_root / "raw"
    raw_root.mkdir(parents=True)
    bundle_id = _repo_ref(checkout_root, bundle_root)

    raw_json = raw_root / "fontish.json"
    if not omit_raw_json:
        _write_json(
            raw_json,
            {
                "fixture_id": "fontish",
                "text": "Candidate B JSON material",
                "source_path": str(checkout_root / "private" / "source.pdf"),
            },
        )
    raw_md = raw_root / "fontish.md"
    raw_md.write_text("# Candidate B markdown\n\nText material.\n", encoding="utf-8")
    (raw_root / "annotated").mkdir()
    (raw_root / "annotated" / "fontish.pdf").write_bytes(b"%PDF-1.4")
    image_dir = raw_root / "images" / "fontish"
    image_dir.mkdir(parents=True)
    (image_dir / "imageFile1.png").write_bytes(b"\x89PNG\r\n")

    compare = {
        "schema_id": "aps.candidate_b_opendataloader.compare_report.v2",
        "run_id": "cb-demo",
        "repo_root": str(checkout_root),
        "python_executable": str(checkout_root / "venv" / "Scripts" / "python.exe"),
        "raw_output_root": f"{bundle_id}/raw",
        "documents": [{"fixture_id": "fontish"}],
    }
    proof = {
        "schema_id": "aps.candidate_b_opendataloader.proof.v2",
        "checkout_root": str(checkout_root),
        "status": "passed",
    }
    baseline_summary = {"schema_id": "baseline.summary.v1", "status": "passed"}
    _write_json(bundle_root / "compare.json", compare)
    _write_json(bundle_root / "proof.json", proof)
    _write_json(bundle_root / "baseline-summary.json", baseline_summary)

    raw_json_entry = {
        "category": "candidate_b_raw_json",
        "path": f"{bundle_id}/raw/fontish.json",
        "sha256": _sha256(raw_json) if raw_json.exists() else "0" * 64,
        "size_bytes": raw_json.stat().st_size if raw_json.exists() else 17,
    }
    raw_inventory = [
        {
            "category": "candidate_b_annotated_pdf",
            "path": f"{bundle_id}/raw/annotated/fontish.pdf",
            "sha256": _sha256(raw_root / "annotated" / "fontish.pdf"),
            "size_bytes": (raw_root / "annotated" / "fontish.pdf").stat().st_size,
        },
        raw_json_entry,
        _source_entry(checkout_root, raw_md, "candidate_b_raw_markdown"),
        {
            "category": "candidate_b_extracted_image",
            "path": f"{bundle_id}/raw/images/fontish/imageFile1.png",
            "sha256": _sha256(image_dir / "imageFile1.png"),
            "size_bytes": (image_dir / "imageFile1.png").stat().st_size,
        },
    ]
    retain = {
        "schema_id": "aps.candidate_b_opendataloader.retention_manifest.v2",
        "run_id": "cb-demo",
        "repo_root": str(checkout_root),
        "raw_output_root": f"{bundle_id}/raw",
        "durable_report_inventory": [
            _source_entry(checkout_root, bundle_root / "proof.json", "durable_report"),
            _source_entry(checkout_root, bundle_root / "compare.json", "durable_report"),
        ],
        "baseline_output_inventory": [
            _source_entry(checkout_root, bundle_root / "baseline-summary.json", "baseline_summary")
        ],
        "raw_file_inventory": raw_inventory,
    }
    _write_json(bundle_root / "retain.json", retain)
    return checkout_root, bundle_id


class _FakeCompareTargets:
    def __init__(self, *, bundle_id: str) -> None:
        self.bundle_id = bundle_id

    def model_dump(self) -> dict[str, Any]:
        return {
            "baseline_run_id": "baseline-run",
            "candidate_a_run_id": "candidate-a-run",
            "candidate_b_source_kind": "bundle",
            "candidate_b_bundle_id": self.bundle_id,
            "candidate_b_run_id": None,
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


def _patch_compare_targets(monkeypatch, expected_bundle_id: str) -> None:
    def fake_compose(**kwargs):
        assert kwargs["candidate_b_source_kind"] == "bundle"
        assert kwargs["candidate_b_bundle_id"] == expected_bundle_id
        assert "candidate_b_run_id" not in kwargs or kwargs["candidate_b_run_id"] is None
        return _FakeCompareTargets(bundle_id=expected_bundle_id)

    monkeypatch.setattr(layer3_candidate_b_bundle_bridge, "compose_workbench_compare_targets", fake_compose)


def _bridge_payload(bundle_id: str) -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-bridge-001",
        "bridge_mode": BRIDGE_MODE,
        "candidate_b_bundle_id": bundle_id,
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "operator_confirmation": True,
    }


def _scan_payload() -> dict[str, str]:
    return {
        "client_request_id": "candidate-b-bridge-source-scan",
        "operator_decision": "scan_server_configured_operator_directory",
        "source_family": "server_configured_operator_directory_text_table_source_family",
        "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
    }


def _material_preview_payload(scan_body: dict[str, Any], relative_name: str) -> dict[str, str]:
    file_record = next(item for item in scan_body["files"] if item["relative_name"] == relative_name)
    return {
        "client_request_id": f"candidate-b-bridge-material-preview-{relative_name.replace('/', '-')}",
        "source_ingestion_batch_id": scan_body["source_ingestion_batch_id"],
        "source_ingestion_file_id": file_record["source_ingestion_file_id"],
        "file_identity_hash": file_record["file_identity_hash"],
        "authority_basis_hash": file_record["authority_basis_hash"],
    }


def _approved_candidate_b_material(
    client: TestClient,
    scan_body: dict[str, Any],
    *,
    relative_name: str,
) -> dict[str, str]:
    preview = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=_material_preview_payload(scan_body, relative_name),
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    candidate = preview_body["material_candidate"]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": f"candidate-b-bridge-downstream-gate-b-{relative_name.replace('/', '-')}",
            "preflight_id": "candidate-b-bridge-downstream-preflight",
            "source_set_id": scan_body["source_ingestion_batch_id"],
            "material_preview_id": preview_body["material_preview_id"],
            "material_preview_hash": preview_body["material_preview_hash"],
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "decision_basis": candidate,
                }
            ],
        },
    )
    assert gate_b.status_code == 200, gate_b.text
    db = client.layer3_session_factory()
    try:
        snapshot = (
            db.query(L3MaterialSnapshot)
            .filter(L3MaterialSnapshot.session_id == gate_b.json()["session_id"])
            .one()
        )
        return {
            "material_snapshot_id": snapshot.material_snapshot_id,
            "payload_hash": snapshot.payload_hash,
            "source_ingestion_batch_id": scan_body["source_ingestion_batch_id"],
            "source_ingestion_file_id": candidate["payload"]["source_ingestion_file_id"],
            "content_sha256": candidate["payload"]["content_sha256"],
            "file_identity_hash": candidate["payload"]["file_identity_hash"],
            "authority_basis_hash": candidate["payload"]["authority_basis_hash"],
        }
    finally:
        db.close()


def _candidate_b_bundle_external_export_download_authority(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    checkout_root, bundle_id = _create_bundle(tmp_path)
    _patch_compare_targets(monkeypatch, bundle_id)
    bridge = layer3_candidate_b_bundle_bridge.prepare_candidate_b_bundle_material_bridge(
        _bridge_payload(bundle_id),
        checkout_root=checkout_root,
    )
    assert bridge["candidate_b_source_kind"] == "bundle"
    assert bridge["baseline_run_id"] == "baseline-run"
    assert bridge["candidate_a_run_id"] == "candidate-a-run"
    assert bridge["layer3_material_preview_compatible"] is True
    assert bridge["gate_b_material_authority_compatible"] is True
    assert bridge["negative_invariants"]["baseline_default_changed"] is False
    assert bridge["negative_invariants"]["candidate_a_semantics_changed"] is False
    assert bridge["negative_invariants"]["candidate_b_default_promotion_enabled"] is False

    curated_root = Path(settings.layer3_candidate_b_bundle_bridge_dir) / bridge["bridge_receipt_id"] / "curated"
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(curated_root))
    scan = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/scan",
        json={**_scan_payload(), "client_request_id": "candidate-b-bridge-downstream-source-scan"},
    )
    assert scan.status_code == 201, scan.text
    scan_body = scan.json()
    assert scan_body["eligible_file_count"] == 6
    assert "raw/fontish.md" in {item["relative_name"] for item in scan_body["files"]}

    snapshot_info = _approved_candidate_b_material(client, scan_body, relative_name="raw/fontish.md")
    db = client.layer3_session_factory()
    try:
        text_index = source_directory_material_text_index(
            db,
            {
                "client_request_id": "candidate-b-bridge-downstream-text-index",
                **snapshot_info,
            },
        )
        vector_index = source_directory_material_embedding_vector_index(
            db,
            {
                "client_request_id": "candidate-b-bridge-downstream-vector-index",
                **snapshot_info,
                "index_authority_hash": text_index["index_authority_hash"],
            },
        )
    finally:
        db.close()

    analysis_payload = {
        "client_request_id": "candidate-b-bridge-downstream-analysis",
        **snapshot_info,
        "index_authority_hash": text_index["index_authority_hash"],
        "embedding_index_authority_hash": vector_index["embedding_index_authority_hash"],
        "query_text": "Candidate B markdown material",
        "analysis_question": "What Candidate B markdown material is available?",
        "analysis_focus": "Candidate B bundle curated markdown downstream bridge proof",
        "limit": 2,
        "offset": 0,
        "top_k": 2,
    }
    analysis = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis"
        ),
        json=analysis_payload,
    )
    assert analysis.status_code == 200, analysis.text
    analysis_body = analysis.json()
    assert analysis_body["status"] == "available"
    assert analysis_body["source_directory_package_review_preview_enabled"] is True
    assert analysis_body["negative_invariants"]["rag_execution_enabled"] is False
    assert analysis_body["negative_invariants"]["prompt_model_provider_runtime_enabled"] is False
    assert str(checkout_root) not in analysis.text

    commit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/commit"
        ),
        json={
            **analysis_payload,
            "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
            "source_directory_hybrid_package_review_preview_hash": (
                analysis_body["source_directory_hybrid_package_review_preview_hash"]
            ),
            "operator_decision": "commit_source_directory_hybrid_context_packet_qualitative_analysis_package",
        },
    )
    assert commit.status_code == 200, commit.text
    commit_body = commit.json()

    submit_payload = {
        **analysis_payload,
        "qualitative_analysis_hash": analysis_body["qualitative_analysis_hash"],
        "source_directory_hybrid_package_review_preview_hash": (
            analysis_body["source_directory_hybrid_package_review_preview_hash"]
        ),
        "construction_basis_hash": commit_body["construction_basis_hash"],
        "reconciliation_record_id": commit_body["reconciliation_record_id"],
        "output_package_ids": commit_body["output_package_ids"],
        "package_kinds": commit_body["package_kinds"],
        "payload_hashes": commit_body["payload_hashes"],
        "operator_decision": "approved",
        "decision_notes": "Candidate B bundle downstream proof package approved.",
    }
    submit = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/package/review/submit"
        ),
        json=submit_payload,
    )
    assert submit.status_code == 200, submit.text
    submit_body = submit.json()

    handoff_payload = {
        **submit_payload,
        "operator_decision": "authorize_prepare",
        "package_review_submit_record_ref": submit_body["submit_record_ref"],
        "package_review_state": "package_review_approved",
        "handoff_target": "internal_export_envelope",
        "export_mode": "prepare_only",
    }
    handoff = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/prepare"
        ),
        json=handoff_payload,
    )
    assert handoff.status_code == 200, handoff.text
    handoff_body = handoff.json()

    prepare_payload = {
        **handoff_payload,
        "operator_decision": "prepare_source_directory_hybrid_external_export_download",
        "prepare_record_ref": handoff_body["prepare_record_ref"],
        "handoff_export_state": "handoff_export_prepared",
        "handoff_export_envelope_ref": handoff_body["handoff_export_envelope"]["envelope_ref"],
        "external_export_download_target": (
            "source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference"
        ),
        "download_mode": "reference_only_prepare",
    }
    prepare = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare"
        ),
        json=prepare_payload,
    )
    assert prepare.status_code == 200, prepare.text
    prepare_body = prepare.json()
    assert prepare_body["status"] == "prepared"
    assert str(checkout_root) not in prepare.text
    return bridge, analysis_payload, analysis_body, prepare_payload, prepare_body, checkout_root


def _source_directory_internal_webhook_payload(
    prepare_body: dict[str, Any],
    prepare_payload: dict[str, Any],
    *,
    request_id: str,
) -> dict[str, Any]:
    return {
        **prepare_payload,
        "client_request_id": request_id,
        "operator_decision": "dispatch_source_directory_hybrid_internal_webhook",
        "external_export_download_record_ref": prepare_body["external_export_download_record_ref"],
        "export_download_descriptor_ref": prepare_body["export_download_descriptor_ref"],
        "external_export_download_state": "external_export_download_prepared",
        "target_identity": "server_configured_internal_webhook_destination",
        "target_class": "real_connector_invocation",
        "dispatch_mode": "server_configured_allowlisted_internal_webhook_post",
    }


def _assert_no_absolute_path_strings(value: Any, forbidden_fragment: str) -> None:
    if isinstance(value, dict):
        for child in value.values():
            _assert_no_absolute_path_strings(child, forbidden_fragment)
    elif isinstance(value, list):
        for child in value:
            _assert_no_absolute_path_strings(child, forbidden_fragment)
    elif isinstance(value, str):
        assert forbidden_fragment not in value
        assert "C:\\" not in value


def test_candidate_b_bundle_bridge_curates_json_md_and_reaches_gate_b(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    checkout_root, bundle_id = _create_bundle(tmp_path)
    _patch_compare_targets(monkeypatch, bundle_id)

    response = layer3_candidate_b_bundle_bridge.prepare_candidate_b_bundle_material_bridge(
        _bridge_payload(bundle_id),
        checkout_root=checkout_root,
    )

    assert response["status"] == "prepared"
    assert response["candidate_b_source_kind"] == "bundle"
    assert response["curated_root_absolute_path_exposed"] is False
    assert response["layer3_material_preview_compatible"] is True
    assert response["gate_b_material_authority_compatible"] is True
    assert response["negative_invariants"]["candidate_b_default_promotion_enabled"] is False
    assert response["negative_invariants"]["candidate_b_visual_lane_mode_enabled"] is False
    assert response["admitted_artifact_subset"]["top_level_files"] == [
        "baseline-summary.json",
        "compare.json",
        "proof.json",
        "retain.json",
    ]
    assert response["admitted_artifact_subset"]["raw_files"] == ["raw/fontish.json", "raw/fontish.md"]
    assert response["excluded_artifact_subset"]["excluded_extension_counts"][".pdf"] == 1
    assert response["excluded_artifact_subset"]["excluded_extension_counts"][".png"] == 1
    artifact_family = response["governed_retained_artifact_family"]
    assert artifact_family["policy"] == "candidate_b_full_artifact_family_retained_but_text_material_payload_bounded"
    assert artifact_family["candidate_b_source_kind"] == "bundle"
    assert artifact_family["pdf_material_text_payload_enabled"] is False
    assert artifact_family["image_material_text_payload_enabled"] is False
    assert response["authority_hashes"]["governed_retained_artifact_family_hash"] == artifact_family["artifact_family_hash"]
    assert {item["category"] for item in artifact_family["roles"]["material_analysis_payloads"]} == {
        "candidate_b_raw_json",
        "candidate_b_raw_markdown",
    }
    assert {item["category"] for item in artifact_family["roles"]["visual_page_evidence"]} == {
        "candidate_b_annotated_pdf",
        "candidate_b_extracted_image",
    }
    assert any(
        item["source_ref"].endswith("/raw/annotated/fontish.pdf") and item["material_text_payload"] is False
        for item in artifact_family["roles"]["product_inspection_artifacts"]
    )
    assert any(
        item["source_ref"].endswith("/raw/annotated/fontish.pdf") and item["material_text_payload"] is False
        for item in artifact_family["roles"]["provenance_audit_artifacts"]
    )
    assert any(
        item["source_ref"].endswith("/raw/images/fontish/imageFile1.png") and item["material_text_payload"] is False
        for item in artifact_family["roles"]["delivery_artifacts"]
    )
    _assert_no_absolute_path_strings(response, str(checkout_root))

    curated_root = Path(settings.layer3_candidate_b_bundle_bridge_dir) / response["bridge_receipt_id"] / "curated"
    assert sorted(path.relative_to(curated_root).as_posix() for path in curated_root.rglob("*") if path.is_file()) == [
        "baseline-summary.json",
        "compare.json",
        "proof.json",
        "raw/fontish.json",
        "raw/fontish.md",
        "retain.json",
    ]
    curated_compare = json.loads((curated_root / "compare.json").read_text(encoding="utf-8"))
    assert curated_compare["repo_root"].startswith("redacted://sha256/")
    assert str(checkout_root) not in json.dumps(curated_compare)

    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(curated_root))
    scan = client.post("/api/v1/layer3/source/ingestion/server-configured-directory/scan", json=_scan_payload())
    assert scan.status_code == 201
    scan_body = scan.json()
    assert scan_body["eligible_file_count"] == 6
    assert {item["relative_name"] for item in scan_body["files"]} == {
        "baseline-summary.json",
        "compare.json",
        "proof.json",
        "raw/fontish.json",
        "raw/fontish.md",
        "retain.json",
    }

    preview = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=_material_preview_payload(scan_body, "compare.json"),
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    candidate = preview_body["material_candidate"]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "candidate-b-bridge-gate-b",
            "preflight_id": "candidate-b-bridge-preflight",
            "source_set_id": scan_body["source_ingestion_batch_id"],
            "material_preview_id": preview_body["material_preview_id"],
            "material_preview_hash": preview_body["material_preview_hash"],
            "candidate_decisions": [
                {
                    "candidate_id": candidate["candidate_id"],
                    "decision": "approved",
                    "decision_basis": candidate,
                }
            ],
        },
    )
    assert gate_b.status_code == 200


def test_candidate_b_bundle_curated_markdown_completes_layer3_downstream_path(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "layer3_internal_webhook_url", "http://127.0.0.1/source-directory-webhook")
    monkeypatch.setattr(settings, "layer3_internal_webhook_display_name", "candidate-b-source-directory-webhook")
    bridge, analysis_payload, analysis_body, prepare_payload, prepare_body, checkout_root = (
        _candidate_b_bundle_external_export_download_authority(client, tmp_path, monkeypatch)
    )
    selected_package = next(
        package for package in prepare_body["output_packages"] if package["package_kind"] == "user_facing"
    )
    delivery_payload = {
        **prepare_payload,
        "operator_decision": "deliver_source_directory_hybrid_external_export_download",
        "external_export_download_record_ref": prepare_body["external_export_download_record_ref"],
        "export_download_descriptor_ref": prepare_body["export_download_descriptor_ref"],
        "external_export_download_state": "external_export_download_prepared",
        "delivery_mode": "same_origin_artifact_stream",
        "output_package_id": selected_package["output_package_id"],
        "package_kind": selected_package["package_kind"],
        "package_payload_hash": selected_package["payload_hash"],
    }

    delivery_status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status"
        ),
        json=delivery_payload,
    )
    assert delivery_status.status_code == 200, delivery_status.text
    assert delivery_status.json()["delivery_available"] is True
    assert delivery_status.json()["same_origin_delivery_enabled"] is True
    assert delivery_status.json()["provider_private_signed_url_enabled"] is False

    delivery = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver"
        ),
        json=delivery_payload,
    )
    assert delivery.status_code == 200, delivery.text
    assert delivery.headers["X-Layer3-Delivery-State"] == "external_export_download_delivered"
    assert "Candidate B markdown" in delivery.text
    assert str(checkout_root) not in delivery.text

    provider_private_prepare = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/"
            "provider-private-signed-url/prepare"
        ),
        json={
            **delivery_payload,
            "client_request_id": "candidate-b-provider-private-prepare",
            "operator_decision": "prepare_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "recipient_scope": "candidate-b-redacted-delivery-proof",
            "requested_ttl_seconds": 300,
        },
    )
    assert provider_private_prepare.status_code == 200, provider_private_prepare.text
    provider_private_body = provider_private_prepare.json()
    assert provider_private_body["provider_signed_url_state"] == "provider_private_signed_url_prepared"
    assert provider_private_body["provider_url_redacted"] == "provider-private-signed-url:redacted"
    assert provider_private_body["source_artifact_hash"] == selected_package["payload_hash"]
    assert provider_private_body["provider_network_enabled"] is False
    assert provider_private_body["provider_object_write_enabled"] is False
    assert provider_private_body["raw_provider_private_signed_url_token_exposed"] is False

    provider_private_status_payload = {
        **delivery_payload,
        "client_request_id": "candidate-b-provider-private-status",
        "operator_decision": "inspect_source_directory_hybrid_provider_private_signed_url_status",
        "delivery_mode": "provider_private_signed_url",
        "provider_signed_url_receipt_id": provider_private_body["provider_signed_url_receipt_id"],
    }
    provider_private_status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/"
            "provider-private-signed-url/status"
        ),
        json=provider_private_status_payload,
    )
    assert provider_private_status.status_code == 200, provider_private_status.text
    assert provider_private_status.json()["provider_url_redacted"] == "provider-private-signed-url:redacted"
    assert provider_private_status.json()["raw_provider_private_signed_url_token_exposed"] is False

    provider_private_use = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/"
            "provider-private-signed-url/use"
        ),
        json={
            **delivery_payload,
            "client_request_id": "candidate-b-provider-private-use",
            "operator_decision": "use_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "provider_signed_url_receipt_id": provider_private_body["provider_signed_url_receipt_id"],
        },
    )
    assert provider_private_use.status_code == 200, provider_private_use.text
    assert provider_private_use.json()["delivery_use_mode"] == "server_owned_redacted_provider_private_use"
    assert provider_private_use.json()["provider_url_redacted"] == "provider-private-signed-url:redacted"
    assert provider_private_use.json()["provider_network_enabled"] is False
    assert "provider_private_signed_url_token" not in provider_private_use.json()

    revoke_prepare = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/"
            "provider-private-signed-url/prepare"
        ),
        json={
            **delivery_payload,
            "client_request_id": "candidate-b-provider-private-revoke-prepare",
            "operator_decision": "prepare_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "recipient_scope": "candidate-b-redacted-revoke-proof",
            "requested_ttl_seconds": 300,
        },
    )
    assert revoke_prepare.status_code == 200, revoke_prepare.text
    provider_private_revoke = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/download/"
            "provider-private-signed-url/revoke"
        ),
        json={
            **delivery_payload,
            "client_request_id": "candidate-b-provider-private-revoke",
            "operator_decision": "revoke_source_directory_hybrid_provider_private_signed_url",
            "delivery_mode": "provider_private_signed_url",
            "provider_signed_url_receipt_id": revoke_prepare.json()["provider_signed_url_receipt_id"],
            "idempotency_key": "candidate-b-provider-private-revoke",
            "revoked_by": "candidate-b-layer3-test",
            "revocation_reason": "Candidate B downstream proof revoke.",
        },
    )
    assert provider_private_revoke.status_code == 200, provider_private_revoke.text
    assert provider_private_revoke.json()["provider_signed_url_state"] == "provider_private_signed_url_revoked"
    assert provider_private_revoke.json()["raw_provider_private_signed_url_token_exposed"] is False

    webhook_calls: list[dict[str, Any]] = []

    def fake_transport(url, envelope, headers, timeout):
        webhook_calls.append({"url": url, "envelope": envelope, "headers": headers, "timeout": timeout})
        return 202, {"accepted": True, "receipt": "candidate-b-source-directory-ok"}

    monkeypatch.setattr(layer3_internal_webhook_connector, "INTERNAL_WEBHOOK_TRANSPORT", fake_transport)
    webhook_payload = _source_directory_internal_webhook_payload(
        prepare_body,
        prepare_payload,
        request_id="candidate-b-internal-webhook-dispatch",
    )
    webhook = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/dispatch"
        ),
        json=webhook_payload,
    )
    assert webhook.status_code == 200, webhook.text
    webhook_body = webhook.json()
    assert webhook_body["source_directory_internal_webhook_dispatch_state"] == (
        "source_directory_internal_webhook_dispatched"
    )
    assert webhook_body["connector_dispatch_enabled"] is False
    assert webhook_body["provider_private_signed_url_enabled"] is False
    assert len(webhook_calls) == 1
    assert webhook_calls[0]["envelope"]["raw_package_payload_included"] is False
    assert str(checkout_root) not in json.dumps(webhook_calls[0]["envelope"], sort_keys=True)

    webhook_status = client.get(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/handoff/export/internal-webhook/status/"
            f"{webhook_body['source_directory_internal_webhook_dispatch_receipt_id']}"
        )
    )
    assert webhook_status.status_code == 200, webhook_status.text
    assert webhook_status.json()["source_directory_internal_webhook_dispatch_state"] == (
        "source_directory_internal_webhook_dispatched"
    )

    status_payload = {
        key: value
        for key, value in analysis_payload.items()
        if key != "client_request_id"
    }
    downstream_status = client.post(
        (
            "/api/v1/layer3/source/ingestion/server-configured-directory/"
            "hybrid-context-packet/qualitative-analysis/status"
        ),
        json={**status_payload, "client_request_id": "candidate-b-downstream-status"},
    )
    assert downstream_status.status_code == 200, downstream_status.text
    downstream_status_body = downstream_status.json()
    assert downstream_status_body["qualitative_analysis_hash"] == analysis_body["qualitative_analysis_hash"]
    assert downstream_status_body["source_directory_hybrid_package_commit_available"] is True
    assert downstream_status_body["source_directory_hybrid_package_review_submit_available"] is True
    assert downstream_status_body["source_directory_hybrid_handoff_export_prepare_available"] is True

    session = client.get(f"/api/v1/layer3/session/{webhook_body['session_id']}")
    assert session.status_code == 200, session.text
    session_body = session.json()
    assert session_body["internal_webhook_dispatch"]["state"] == "source_directory_internal_webhook_dispatched"
    assert session_body["internal_webhook_dispatch"]["raw_package_payload_exposed"] is False

    response_text = json.dumps(
        {
            "bridge": bridge,
            "delivery_status": delivery_status.json(),
            "provider_private": provider_private_body,
            "webhook": webhook_body,
            "session": session_body,
        },
        sort_keys=True,
    )
    assert str(checkout_root) not in response_text
    assert bridge["negative_invariants"]["candidate_b_default_promotion_enabled"] is False

    db = client.layer3_session_factory()
    try:
        assert db.query(L3OutputPackage).count() == 3
        assert db.query(L3ProviderPrivateSignedUrlReceipt).count() == 2
        assert db.query(L3ProviderPublicUrlReceipt).count() == 0
        assert db.query(L3SourceDirectoryInternalWebhookDispatchReceipt).count() == 1
        assert db.query(AnalysisRun).count() == 0
        assert db.query(ConnectorRun).count() == 0
        assert db.query(ConnectorRunTarget).count() == 0
        reconciliation = db.query(L3ReconciliationRecord).one()
        assert reconciliation.summary_json["external_export_download_prepare"][
            "external_export_download_state"
        ] == (
            "external_export_download_prepared"
        )
        assert reconciliation.summary_json["source_directory_internal_webhook_dispatch"]["state"] == (
            "source_directory_internal_webhook_dispatched"
        )
    finally:
        db.close()


def test_candidate_b_bundle_bridge_fails_closed_on_missing_retained_raw_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "layer3_candidate_b_bundle_bridge_dir", str(tmp_path / "bridge"))
    checkout_root, bundle_id = _create_bundle(tmp_path, omit_raw_json=True)
    _patch_compare_targets(monkeypatch, bundle_id)

    with pytest.raises(layer3_candidate_b_bundle_bridge.CandidateBBundleBridgeError) as exc_info:
        layer3_candidate_b_bundle_bridge.prepare_candidate_b_bundle_material_bridge(
            _bridge_payload(bundle_id),
            checkout_root=checkout_root,
        )

    assert exc_info.value.code == "candidate_b_bundle_bridge_source_file_missing"


def test_candidate_b_bundle_bridge_rejects_runtime_and_local_path_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    checkout_root, bundle_id = _create_bundle(tmp_path)
    _patch_compare_targets(monkeypatch, bundle_id)
    payload = {
        **_bridge_payload(bundle_id),
        "candidate_b_run_id": "runtime-run",
        "local_path": str(checkout_root),
    }

    with pytest.raises(layer3_candidate_b_bundle_bridge.CandidateBBundleBridgeError) as exc_info:
        layer3_candidate_b_bundle_bridge.prepare_candidate_b_bundle_material_bridge(
            payload,
            checkout_root=checkout_root,
        )

    assert exc_info.value.code == "candidate_b_bundle_bridge_forbidden_request_fields"
    assert exc_info.value.details["blocked_fields"] == ["candidate_b_run_id", "local_path"]


def test_candidate_b_bundle_bridge_openapi_contract(client: TestClient) -> None:
    schema = client.app.openapi()
    route = schema["paths"]["/api/v1/layer3/source/ingestion/candidate-b/bundle/material-bridge"]["post"]
    request_ref = route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]

    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {
        "client_request_id",
        "bridge_mode",
        "candidate_b_bundle_id",
        "baseline_run_id",
        "candidate_a_run_id",
        "operator_confirmation",
    }
    assert "candidate_b_run_id" not in request_schema["properties"]
    assert "document_processing_engine" not in request_schema["properties"]
    assert "visual_lane_mode" not in request_schema["properties"]
    assert "local_path" not in request_schema["properties"]
    assert "url" not in request_schema["properties"]

    readiness = client.get("/api/v1/layer3/readiness")
    assert readiness.status_code == 200
    readiness_body = readiness.json()
    assert readiness_body["candidate_b_bundle_material_bridge_admitted"] is True
    assert readiness_body["candidate_b_bundle_material_bridge_endpoint"] == (
        "/api/v1/layer3/source/ingestion/candidate-b/bundle/material-bridge"
    )
