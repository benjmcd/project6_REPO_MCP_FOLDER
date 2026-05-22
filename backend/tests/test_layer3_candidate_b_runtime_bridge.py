from __future__ import annotations

from contextlib import contextmanager
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
from app.services import layer3_candidate_b_runtime_bridge
from app.services.review_nrc_aps_runtime import ReviewRuntimeBinding
from main import app


BRIDGE_MODE = "candidate_b_runtime_source_to_layer3_material_authority_v1"
RUN_ID = "candidate-b-runtime-run"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    bridge_dir = tmp_path / "bridge"
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))
    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", "")
    monkeypatch.setattr(settings, "layer3_candidate_b_runtime_bridge_dir", str(bridge_dir))
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
        yield test_client
    app.dependency_overrides.clear()
    app.openapi_schema = None


class _FakeModel:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        return self.payload


class _FakeCompareTargets:
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        return {
            "baseline_run_id": "baseline-run",
            "candidate_a_run_id": "candidate-a-run",
            "candidate_b_source_kind": "runtime",
            "candidate_b_run_id": RUN_ID,
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


def _runtime_binding(tmp_path: Path) -> ReviewRuntimeBinding:
    review_root = tmp_path / "runtime"
    storage_dir = review_root / "storage"
    storage_dir.mkdir(parents=True)
    database_path = review_root / "lc.db"
    database_path.write_bytes(b"candidate-b-runtime-db")
    (storage_dir / "input.pdf").write_bytes(b"%PDF-1.4")
    (storage_dir / "image.png").write_bytes(b"\x89PNG\r\n")
    (storage_dir / "raw.bin").write_bytes(b"binary")
    (storage_dir / "normalized.txt").write_text("Candidate B runtime normalized text", encoding="utf-8")
    summary = {
        "schema_id": "aps.local_corpus_e2e_summary.v1",
        "schema_version": 1,
        "run_id": RUN_ID,
        "runtime_root": str(review_root),
        "database_path": str(database_path),
        "database_url": f"sqlite:///{database_path.as_posix()}",
        "storage_dir": str(storage_dir),
        "visual_lane_mode": "baseline",
        "document_processing_engine": "candidate_b_opendataloader_pdf",
        "passed": True,
        "run_detail": {"status": "completed"},
    }
    return ReviewRuntimeBinding(
        run_id=RUN_ID,
        review_root=review_root,
        summary=summary,
        database_path=database_path,
        storage_dir=storage_dir,
    )


def _patch_runtime_bridge(monkeypatch, binding: ReviewRuntimeBinding, *, variant: str | None = None) -> None:
    def fake_compare(**kwargs):
        assert kwargs["candidate_b_source_kind"] == "runtime"
        assert kwargs["candidate_b_run_id"] == RUN_ID
        assert "candidate_b_bundle_id" not in kwargs or kwargs["candidate_b_bundle_id"] is None
        return _FakeCompareTargets()

    @contextmanager
    def fake_runtime_session(binding_arg):
        assert binding_arg == binding
        yield object()

    def fake_trace(session, run_id, target_id, root):
        assert run_id == RUN_ID
        assert target_id == "candidate-b-target"
        assert root == binding.review_root
        return _FakeModel(
            {
                "identity": {
                    "document_title": str(binding.review_root / "private-source.pdf"),
                    "source_file_name": "fontish.pdf",
                    "accession_number": "ML000000001",
                },
                "summary": {"page_count": 1, "quality_status": "ok"},
            }
        )

    def fake_normalized(session, run_id, target_id, root):
        return _FakeModel(
            {
                "available": True,
                "run_id": run_id,
                "target_id": target_id,
                "text": "Candidate B runtime normalized text",
                "char_count": 35,
                "mapping_precision": "best_effort",
            }
        )

    monkeypatch.setattr(layer3_candidate_b_runtime_bridge, "find_runtime_binding_for_run", lambda run_id: binding)
    monkeypatch.setattr(
        layer3_candidate_b_runtime_bridge,
        "classify_runtime_binding_variant",
        lambda binding_arg: variant or "candidate_b_opendataloader_pdf",
    )
    monkeypatch.setattr(
        layer3_candidate_b_runtime_bridge,
        "runtime_binding_request_metadata",
        lambda binding_arg: {
            "visual_lane_mode": "baseline",
            "document_processing_engine": "candidate_b_opendataloader_pdf",
            "variant_kind": "candidate_b_opendataloader_pdf",
        },
    )
    monkeypatch.setattr(layer3_candidate_b_runtime_bridge, "compose_workbench_compare_targets", fake_compare)
    monkeypatch.setattr(layer3_candidate_b_runtime_bridge, "runtime_db_session_for_binding", fake_runtime_session)
    monkeypatch.setattr(layer3_candidate_b_runtime_bridge, "compose_trace_manifest", fake_trace)
    monkeypatch.setattr(layer3_candidate_b_runtime_bridge, "compose_normalized_text_payload", fake_normalized)


def _bridge_payload() -> dict[str, Any]:
    return {
        "client_request_id": "candidate-b-runtime-bridge-001",
        "bridge_mode": BRIDGE_MODE,
        "candidate_b_run_id": RUN_ID,
        "baseline_run_id": "baseline-run",
        "candidate_a_run_id": "candidate-a-run",
        "operator_confirmation": True,
    }


def _scan_payload() -> dict[str, str]:
    return {
        "client_request_id": "candidate-b-runtime-bridge-source-scan",
        "operator_decision": "scan_server_configured_operator_directory",
        "source_family": "server_configured_operator_directory_text_table_source_family",
        "ingestion_mode": "server_configured_operator_directory_text_table_ingestion",
    }


def _material_preview_payload(scan_body: dict[str, Any], relative_name: str) -> dict[str, str]:
    file_record = next(item for item in scan_body["files"] if item["relative_name"] == relative_name)
    return {
        "client_request_id": f"candidate-b-runtime-preview-{relative_name.replace('/', '-')}",
        "source_ingestion_batch_id": scan_body["source_ingestion_batch_id"],
        "source_ingestion_file_id": file_record["source_ingestion_file_id"],
        "file_identity_hash": file_record["file_identity_hash"],
        "authority_basis_hash": file_record["authority_basis_hash"],
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


def test_candidate_b_runtime_bridge_materializes_trace_text_and_reaches_gate_b(
    client: TestClient,
    tmp_path: Path,
    monkeypatch,
) -> None:
    binding = _runtime_binding(tmp_path)
    _patch_runtime_bridge(monkeypatch, binding)

    response = layer3_candidate_b_runtime_bridge.prepare_candidate_b_runtime_material_bridge(_bridge_payload())

    assert response["status"] == "prepared"
    assert response["candidate_b_source_kind"] == "runtime"
    assert response["document_processing_engine"] == "candidate_b_opendataloader_pdf"
    assert response["curated_root_absolute_path_exposed"] is False
    assert response["layer3_material_preview_compatible"] is True
    assert response["gate_b_material_authority_compatible"] is True
    assert response["negative_invariants"]["candidate_b_default_promotion_enabled"] is False
    assert response["negative_invariants"]["candidate_b_visual_lane_mode_enabled"] is False
    assert response["negative_invariants"]["broad_runtime_db_ingestion_enabled"] is False
    assert response["admitted_artifact_subset"]["top_level_files"] == [
        "compare-targets.json",
        "runtime-summary.json",
    ]
    assert response["admitted_artifact_subset"]["trace_files"] == ["trace/fontish.json"]
    assert response["admitted_artifact_subset"]["normalized_files"] == ["normalized/fontish.json"]
    assert response["admitted_artifact_subset"]["text_files"] == ["text/fontish.md"]
    assert response["excluded_artifact_subset"]["excluded_extension_counts"][".db"] == 1
    assert response["excluded_artifact_subset"]["excluded_extension_counts"][".pdf"] == 1
    assert response["excluded_artifact_subset"]["excluded_extension_counts"][".png"] == 1
    assert response["excluded_artifact_subset"]["excluded_extension_counts"][".txt"] == 1
    _assert_no_absolute_path_strings(response, str(binding.review_root))

    curated_root = Path(settings.layer3_candidate_b_runtime_bridge_dir) / response["bridge_receipt_id"] / "curated"
    assert sorted(path.relative_to(curated_root).as_posix() for path in curated_root.rglob("*") if path.is_file()) == [
        "compare-targets.json",
        "normalized/fontish.json",
        "runtime-summary.json",
        "text/fontish.md",
        "trace/fontish.json",
    ]
    curated_summary = json.loads((curated_root / "runtime-summary.json").read_text(encoding="utf-8"))
    assert curated_summary["runtime_root"].startswith("redacted://sha256/")
    assert curated_summary["database_url"].startswith("redacted://sha256/")
    curated_trace = json.loads((curated_root / "trace" / "fontish.json").read_text(encoding="utf-8"))
    assert curated_trace["identity"]["document_title"].startswith("redacted://sha256/")
    assert curated_trace["identity"]["source_file_name"].startswith("redacted://sha256/")
    assert str(binding.review_root) not in json.dumps(curated_trace)

    monkeypatch.setattr(settings, "layer3_source_ingestion_dir", str(curated_root))
    scan = client.post("/api/v1/layer3/source/ingestion/server-configured-directory/scan", json=_scan_payload())
    assert scan.status_code == 201
    scan_body = scan.json()
    assert scan_body["eligible_file_count"] == 5

    preview = client.post(
        "/api/v1/layer3/source/ingestion/server-configured-directory/material-preview",
        json=_material_preview_payload(scan_body, "text/fontish.md"),
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    candidate = preview_body["material_candidate"]
    gate_b = client.post(
        "/api/v1/layer3/gate-b/decision",
        json={
            "client_request_id": "candidate-b-runtime-gate-b",
            "preflight_id": "candidate-b-runtime-preflight",
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


def test_candidate_b_runtime_bridge_rejects_bundle_and_local_path_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "layer3_candidate_b_runtime_bridge_dir", str(tmp_path / "bridge"))
    binding = _runtime_binding(tmp_path)
    _patch_runtime_bridge(monkeypatch, binding)
    payload = {
        **_bridge_payload(),
        "candidate_b_bundle_id": "tests/reports/cb-compare-demo",
        "local_path": str(binding.review_root),
    }

    with pytest.raises(layer3_candidate_b_runtime_bridge.CandidateBRuntimeBridgeError) as exc_info:
        layer3_candidate_b_runtime_bridge.prepare_candidate_b_runtime_material_bridge(payload)

    assert exc_info.value.code == "candidate_b_runtime_bridge_forbidden_request_fields"
    assert exc_info.value.details["blocked_fields"] == ["candidate_b_bundle_id", "local_path"]


def test_candidate_b_runtime_bridge_rejects_non_candidate_b_runtime_variant(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "layer3_candidate_b_runtime_bridge_dir", str(tmp_path / "bridge"))
    binding = _runtime_binding(tmp_path)
    _patch_runtime_bridge(monkeypatch, binding, variant="baseline")

    with pytest.raises(layer3_candidate_b_runtime_bridge.CandidateBRuntimeBridgeError) as exc_info:
        layer3_candidate_b_runtime_bridge.prepare_candidate_b_runtime_material_bridge(_bridge_payload())

    assert exc_info.value.code == "candidate_b_runtime_bridge_run_variant_invalid"


def test_candidate_b_runtime_bridge_openapi_contract(client: TestClient) -> None:
    schema = client.app.openapi()
    route = schema["paths"]["/api/v1/layer3/source/ingestion/candidate-b/runtime/material-bridge"]["post"]
    request_ref = route["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]

    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {
        "client_request_id",
        "bridge_mode",
        "candidate_b_run_id",
        "baseline_run_id",
        "candidate_a_run_id",
        "operator_confirmation",
    }
    assert "candidate_b_bundle_id" not in request_schema["properties"]
    assert "document_processing_engine" not in request_schema["properties"]
    assert "visual_lane_mode" not in request_schema["properties"]
    assert "local_path" not in request_schema["properties"]
    assert "url" not in request_schema["properties"]

    readiness = client.get("/api/v1/layer3/readiness")
    assert readiness.status_code == 200
    readiness_body = readiness.json()
    assert readiness_body["candidate_b_runtime_material_bridge_admitted"] is True
    assert readiness_body["candidate_b_runtime_material_bridge_endpoint"] == (
        "/api/v1/layer3/source/ingestion/candidate-b/runtime/material-bridge"
    )
