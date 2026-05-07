from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

os.environ["DB_INIT_MODE"] = "none"

BACKEND = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TESTS))

from app.core.config import settings
from app.models.models import (
    AnalysisRun,
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetSourceProvenance,
    DatasetVersion,
    L3AnalysisGroup,
    L3AnalysisPlan,
    L3AnalysisSet,
    L3AnalysisUnit,
    L3Descriptor,
    L3MaterialSnapshot,
    L3OutputPackage,
    L3PassRun,
    L3ReconciliationRecord,
    L3RetrievalEvent,
    L3SelectionManifest,
    L3Session,
    L3TypingRecord,
    VariableDefinition,
    VariableProfile,
)
from app.services.layer3_raw_mixed_bridge import (
    RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID,
    RAW_MIXED_CORPUS_SEED_MODE,
    RAW_MIXED_CORPUS_SEED_RESPONSE_SCHEMA_ID,
)
from test_layer3_api import client as client
from test_layer3_aps_handoff import _seed_aps_content_fixture
from test_layer3_pass_entry import _seed_timeseries_dataset_version


@dataclass(frozen=True)
class RawMixedSeededSources:
    corpus_batch_id: str
    dataset_version_ids: tuple[str, str]
    aps_run_id: str
    aps_target_id: str
    aps_content_id: str


def test_layer3_raw_mixed_seed_reuses_existing_sources_without_flow_side_effects(
    client: TestClient,
    tmp_path: Path,
) -> None:
    seeded = _seed_raw_mixed_sources(client, tmp_path)
    manifest_ref, manifest_hash = _write_seed_manifest(seeded)
    before_counts = _counts(client)
    before_files = _storage_files()

    response = client.post(
        "/api/v1/layer3/source/mixed-corpus/seed",
        json=_seed_payload(seeded, manifest_ref=manifest_ref, manifest_hash=manifest_hash),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == RAW_MIXED_CORPUS_SEED_RESPONSE_SCHEMA_ID
    assert body["request_id"] == "raw-mixed-seed-success"
    assert body["seed_mode"] == RAW_MIXED_CORPUS_SEED_MODE
    assert body["source_seed_state"] == "seeded"
    assert sorted(body["dataset_version_ids"]) == sorted(seeded.dataset_version_ids)
    assert body["aps_content_document_ids"] == [seeded.aps_content_id]
    assert body["source_classes"] == ["dataset_version", "aps_content_document"]
    assert body["artifact_manifest_ref"] == manifest_ref
    assert body["artifact_manifest_hash"] == manifest_hash
    assert body["layer3_flow_started"] is False
    assert body["next_allowed_actions"] == ["run_layer3_preflight_with_seeded_source_ids"]
    _assert_forbidden_response_surface_absent(body)
    assert _counts(client) == before_counts
    assert _storage_files() == before_files

    duplicate = client.post(
        "/api/v1/layer3/source/mixed-corpus/seed",
        json=_seed_payload(seeded, manifest_ref=manifest_ref, manifest_hash=manifest_hash),
    )
    assert duplicate.status_code == 200, duplicate.text
    duplicate_body = duplicate.json()
    assert duplicate_body["source_seed_id"] == body["source_seed_id"]
    assert duplicate_body["dataset_version_ids"] == body["dataset_version_ids"]
    assert duplicate_body["aps_content_document_ids"] == body["aps_content_document_ids"]
    assert _counts(client) == before_counts
    assert _storage_files() == before_files

    material = _drive_preview_only_flow(client, body)
    assert len(material["material_candidates"]) == 3
    assert sorted(
        candidate["source_identity"]["dataset_version_id"]
        for candidate in material["material_candidates"]
        if candidate["source_class"] == "dataset_version"
    ) == sorted(seeded.dataset_version_ids)
    assert [
        candidate["source_identity"]["content_id"]
        for candidate in material["material_candidates"]
        if candidate["source_class"] == "aps_content_document"
    ] == [seeded.aps_content_id]
    assert _counts(client) == before_counts
    assert _storage_files() == before_files


def test_layer3_raw_mixed_seed_rejects_forbidden_fields_before_service_mutation(
    client: TestClient,
    tmp_path: Path,
) -> None:
    seeded = _seed_raw_mixed_sources(client, tmp_path)
    manifest_ref, manifest_hash = _write_seed_manifest(seeded)
    before_counts = _counts(client)
    before_files = _storage_files()
    payload = _seed_payload(seeded, manifest_ref=manifest_ref, manifest_hash=manifest_hash)
    payload["local_directory"] = str(tmp_path)

    response = client.post("/api/v1/layer3/source/mixed-corpus/seed", json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "raw_mixed_seed_scope_not_admitted"
    assert body["blocked_fields"] == ["local_directory"]
    assert _counts(client) == before_counts
    assert _storage_files() == before_files


def test_layer3_raw_mixed_seed_rejects_unsupported_source_class_without_side_effects(
    client: TestClient,
    tmp_path: Path,
) -> None:
    seeded = _seed_raw_mixed_sources(client, tmp_path)
    manifest_ref, manifest_hash = _write_seed_manifest(seeded)
    before_counts = _counts(client)
    before_files = _storage_files()
    payload = _seed_payload(seeded, manifest_ref=manifest_ref, manifest_hash=manifest_hash)
    payload["requested_source_classes"] = ["dataset_version", "web_connector"]

    response = client.post("/api/v1/layer3/source/mixed-corpus/seed", json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "unsupported_raw_mixed_source_class"
    assert body["blocked_fields"] == ["requested_source_classes"]
    assert _counts(client) == before_counts
    assert _storage_files() == before_files


def test_layer3_raw_mixed_seed_rejects_stale_manifest_hash_without_side_effects(
    client: TestClient,
    tmp_path: Path,
) -> None:
    seeded = _seed_raw_mixed_sources(client, tmp_path)
    manifest_ref, manifest_hash = _write_seed_manifest(seeded)
    before_counts = _counts(client)
    before_files = _storage_files()
    stale_hash = "0" * 64 if manifest_hash != "0" * 64 else "1" * 64

    response = client.post(
        "/api/v1/layer3/source/mixed-corpus/seed",
        json=_seed_payload(seeded, manifest_ref=manifest_ref, manifest_hash=stale_hash),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error_code"] == "raw_mixed_artifact_manifest_hash_mismatch"
    assert body["blocked_fields"] == ["artifact_manifest_hash"]
    assert _counts(client) == before_counts
    assert _storage_files() == before_files


def test_layer3_raw_mixed_seed_rejects_unknown_aps_target_without_side_effects(
    client: TestClient,
    tmp_path: Path,
) -> None:
    seeded = _seed_raw_mixed_sources(client, tmp_path)
    manifest_ref, manifest_hash = _write_seed_manifest(seeded, target_ids=("target-raw-mixed-missing",))
    before_counts = _counts(client)
    before_files = _storage_files()
    payload = _seed_payload(seeded, manifest_ref=manifest_ref, manifest_hash=manifest_hash)
    payload["target_ids"] = ["target-raw-mixed-missing"]

    response = client.post("/api/v1/layer3/source/mixed-corpus/seed", json=payload)

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "raw_mixed_aps_target_not_found"
    assert body["blocked_fields"] == ["target_ids"]
    assert _counts(client) == before_counts
    assert _storage_files() == before_files


def test_layer3_raw_mixed_seed_rejects_missing_client_request_id_before_service(
    client: TestClient,
    tmp_path: Path,
) -> None:
    seeded = _seed_raw_mixed_sources(client, tmp_path)
    manifest_ref, manifest_hash = _write_seed_manifest(seeded)
    before_counts = _counts(client)
    before_files = _storage_files()
    payload = _seed_payload(seeded, manifest_ref=manifest_ref, manifest_hash=manifest_hash)
    payload.pop("client_request_id")

    response = client.post("/api/v1/layer3/source/mixed-corpus/seed", json=payload)

    assert response.status_code == 422
    assert any(item["loc"][-1] == "client_request_id" for item in response.json()["detail"])
    assert _counts(client) == before_counts
    assert _storage_files() == before_files


def _seed_raw_mixed_sources(client: TestClient, tmp_path: Path) -> RawMixedSeededSources:
    seeded = RawMixedSeededSources(
        corpus_batch_id="batch-raw-mixed-001",
        dataset_version_ids=("dv-raw-mixed-001", "dv-raw-mixed-002"),
        aps_run_id="run-raw-mixed-001",
        aps_target_id="target-raw-mixed-001",
        aps_content_id="content-raw-mixed-001",
    )
    with client.layer3_session_factory() as db:
        _seed_aps_content_fixture(
            db,
            tmp_path,
            run_id=seeded.aps_run_id,
            target_id=seeded.aps_target_id,
            content_id=seeded.aps_content_id,
        )
        _seed_timeseries_dataset_version(
            db,
            tmp_path,
            dataset_id="ds-raw-mixed-001",
            dataset_version_id=seeded.dataset_version_ids[0],
            measure_name="raw_mixed_value_a",
            values=[20 + index for index in range(24)],
        )
        _seed_timeseries_dataset_version(
            db,
            tmp_path,
            dataset_id="ds-raw-mixed-002",
            dataset_version_id=seeded.dataset_version_ids[1],
            measure_name="raw_mixed_value_b",
            values=[200 + (index * 2) for index in range(24)],
        )
        for dataset_version_id in seeded.dataset_version_ids:
            db.add(
                DatasetSourceProvenance(
                    dataset_source_provenance_id=f"prov-{dataset_version_id}",
                    dataset_version_id=dataset_version_id,
                    connector_run_id=seeded.aps_run_id,
                    source_system="nrc_adams_aps",
                    source_mode="raw_mixed_corpus_bridge_seed_fixture",
                    source_artifact_key=f"aps://{seeded.aps_run_id}/{seeded.aps_target_id}/{dataset_version_id}",
                    artifact_surface="dataset_version",
                    artifact_locator_type="server_owned_ref",
                    downloaded_sha256=hashlib.sha256(dataset_version_id.encode("utf-8")).hexdigest(),
                    raw_storage_ref=f"dataset_version:{dataset_version_id}",
                    source_reference_json={
                        "parser_family": "csv_table",
                        "target_id": seeded.aps_target_id,
                        "content_id": seeded.aps_content_id,
                    },
                    fetch_policy_mode="seed_fixture",
                )
            )
        db.commit()
    return seeded


def _write_seed_manifest(
    seeded: RawMixedSeededSources,
    *,
    target_ids: tuple[str, ...] | None = None,
) -> tuple[str, str]:
    manifest_ref = f"raw-mixed/{seeded.corpus_batch_id}.json"
    manifest_path = Path(settings.storage_dir) / manifest_ref
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_id": RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID,
        "corpus_batch_id": seeded.corpus_batch_id,
        "aps_run_id": seeded.aps_run_id,
        "target_ids": list(target_ids or (seeded.aps_target_id,)),
        "source_classes": ["dataset_version", "aps_content_document"],
        "dataset_version_ids": list(seeded.dataset_version_ids),
        "aps_content_document_ids": [seeded.aps_content_id],
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return manifest_ref, hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def _seed_payload(
    seeded: RawMixedSeededSources,
    *,
    manifest_ref: str,
    manifest_hash: str,
) -> dict[str, Any]:
    return {
        "schema_id": "layer3.raw_mixed_corpus_seed_request.v1",
        "schema_version": 1,
        "client_request_id": "raw-mixed-seed-success",
        "seed_mode": RAW_MIXED_CORPUS_SEED_MODE,
        "corpus_batch_id": seeded.corpus_batch_id,
        "aps_run_id": seeded.aps_run_id,
        "target_ids": [seeded.aps_target_id],
        "artifact_manifest_ref": manifest_ref,
        "artifact_manifest_hash": manifest_hash,
        "requested_source_classes": ["dataset_version", "aps_content_document"],
        "operator_confirmation": True,
    }


def _drive_preview_only_flow(client: TestClient, seed: dict[str, Any]) -> dict[str, Any]:
    preflight = client.post(
        "/api/v1/layer3/preflight",
        json={
            "client_request_id": "raw-mixed-preview-preflight",
            "natural_language_intent": "Preview seeded raw mixed corpus source material.",
            "manual_constraints": {"source_classes": seed["source_classes"]},
        },
    )
    assert preflight.status_code == 200, preflight.text
    preflight_body = preflight.json()

    source = client.post(
        "/api/v1/layer3/source-preview",
        json={
            "client_request_id": "raw-mixed-preview-source",
            "preflight_id": preflight_body["preflight_id"],
            "selected_source_classes": seed["source_classes"],
        },
    )
    assert source.status_code == 200, source.text
    source_body = source.json()

    material = client.post(
        "/api/v1/layer3/material-preview",
        json={
            "client_request_id": "raw-mixed-preview-material",
            "preflight_id": preflight_body["preflight_id"],
            "source_set_id": source_body["source_set_id"],
            "source_candidate_ids": [item["source_candidate_id"] for item in source_body["source_candidates"]],
            "dataset_version_ids": seed["dataset_version_ids"],
            "aps_content_document_ids": seed["aps_content_document_ids"],
            "query_basis": {
                "terms": ["raw", "mixed", "seed"],
                "filters": {
                    "dataset_version_ids": seed["dataset_version_ids"],
                    "aps_content_document_ids": seed["aps_content_document_ids"],
                },
            },
        },
    )
    assert material.status_code == 200, material.text
    return material.json()


def _counts(client: TestClient) -> dict[str, int]:
    with client.layer3_session_factory() as db:
        return {
            "analysis_groups": db.query(L3AnalysisGroup).count(),
            "analysis_plans": db.query(L3AnalysisPlan).count(),
            "analysis_runs": db.query(AnalysisRun).count(),
            "analysis_sets": db.query(L3AnalysisSet).count(),
            "analysis_units": db.query(L3AnalysisUnit).count(),
            "aps_content_chunks": db.query(ApsContentChunk).count(),
            "aps_content_documents": db.query(ApsContentDocument).count(),
            "aps_content_linkages": db.query(ApsContentLinkage).count(),
            "connector_run_targets": db.query(ConnectorRunTarget).count(),
            "connector_runs": db.query(ConnectorRun).count(),
            "datasets": db.query(Dataset).count(),
            "dataset_source_provenance": db.query(DatasetSourceProvenance).count(),
            "dataset_versions": db.query(DatasetVersion).count(),
            "descriptors": db.query(L3Descriptor).count(),
            "material_snapshots": db.query(L3MaterialSnapshot).count(),
            "output_packages": db.query(L3OutputPackage).count(),
            "pass_runs": db.query(L3PassRun).count(),
            "reconciliations": db.query(L3ReconciliationRecord).count(),
            "retrieval_events": db.query(L3RetrievalEvent).count(),
            "selection_manifests": db.query(L3SelectionManifest).count(),
            "sessions": db.query(L3Session).count(),
            "typing_records": db.query(L3TypingRecord).count(),
            "variables": db.query(VariableDefinition).count(),
            "variable_profiles": db.query(VariableProfile).count(),
        }


def _storage_files() -> set[str]:
    storage_root = Path(settings.storage_dir)
    return {str(path.relative_to(storage_root)) for path in storage_root.rglob("*") if path.is_file()}


def _assert_forbidden_response_surface_absent(payload: Any) -> None:
    forbidden_keys = {
        "auth_policy_override",
        "browser_state",
        "connector_key",
        "destination_id",
        "destination_url",
        "file_bytes",
        "full_mockup",
        "hidden_llm_plan",
        "hidden_llm_planning",
        "local_directory",
        "local_path",
        "local_upload",
        "package_payload",
        "provider_url",
        "public_url",
        "rag_plan",
        "rag_vector_index",
        "rebuild_package",
        "rewrite_output",
        "runtime_db_write",
        "source_upload",
        "source_url",
        "unbounded_runtime_db",
        "vector_plan",
        "web_connector",
    }
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in forbidden_keys
            _assert_forbidden_response_surface_absent(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_forbidden_response_surface_absent(value)
