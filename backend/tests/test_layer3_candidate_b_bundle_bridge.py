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
from app.services import layer3_candidate_b_bundle_bridge
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
