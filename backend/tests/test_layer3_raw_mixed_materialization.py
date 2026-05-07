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
    DatasetRow,
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
from app.services import nrc_aps_evidence_bundle_contract as aps_contract
from app.services.layer3_raw_mixed_materialization import (
    RAW_MIXED_CORPUS_MATERIALIZE_MANIFEST_SCHEMA_ID,
    RAW_MIXED_CORPUS_MATERIALIZE_MODE,
    RAW_MIXED_CORPUS_MATERIALIZE_RESPONSE_SCHEMA_ID,
)
from test_layer3_api import client as client
from test_layer3_raw_mixed_bridge import (
    _assert_forbidden_response_surface_absent,
    _drive_preview_only_flow,
    _storage_files,
)


@dataclass(frozen=True)
class RawMixedMaterializationFixture:
    corpus_batch_id: str
    dataset_id: str
    dataset_version_id: str
    dataset_version_ids: tuple[str, ...]
    aps_run_id: str
    aps_target_id: str
    aps_content_id: str
    manifest_ref: str
    manifest_hash: str


def test_layer3_raw_mixed_materialize_creates_admitted_sources_for_bounded_preview(
    client: TestClient,
) -> None:
    fixture = _write_materialization_manifest()
    before_counts = _counts(client)
    before_files = _storage_files()

    response = client.post(
        "/api/v1/layer3/source/mixed-corpus/materialize",
        json=_materialize_payload(fixture),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_id"] == RAW_MIXED_CORPUS_MATERIALIZE_RESPONSE_SCHEMA_ID
    assert body["request_id"] == "raw-mixed-materialize-success"
    assert body["materialization_mode"] == RAW_MIXED_CORPUS_MATERIALIZE_MODE
    assert body["source_materialization_state"] == "materialized"
    assert body["dataset_version_ids"] == [fixture.dataset_version_id]
    assert body["aps_content_document_ids"] == [fixture.aps_content_id]
    assert body["source_classes"] == ["dataset_version", "aps_content_document"]
    assert body["artifact_manifest_ref"] == fixture.manifest_ref
    assert body["artifact_manifest_hash"] == fixture.manifest_hash
    assert body["files_written"] == []
    assert body["layer3_flow_started"] is False
    assert body["next_allowed_actions"] == ["run_layer3_preflight_with_materialized_source_ids"]
    assert body["database_rows_written"] == {
        "datasets": 1,
        "dataset_versions": 1,
        "variables": 2,
        "dataset_rows": 2,
        "variable_profiles": 1,
        "dataset_source_provenance": 1,
        "connector_runs": 1,
        "connector_run_targets": 1,
        "aps_content_documents": 1,
        "aps_content_chunks": 2,
        "aps_content_linkages": 1,
    }
    _assert_forbidden_response_surface_absent(body)

    after_counts = _counts(client)
    assert _count_delta(before_counts, after_counts) == {
        "datasets": 1,
        "dataset_versions": 1,
        "variables": 2,
        "dataset_rows": 2,
        "variable_profiles": 1,
        "dataset_source_provenance": 1,
        "connector_runs": 1,
        "connector_run_targets": 1,
        "aps_content_documents": 1,
        "aps_content_chunks": 2,
        "aps_content_linkages": 1,
    }
    _assert_no_layer3_flow_delta(before_counts, after_counts)
    assert _storage_files() == before_files

    duplicate = client.post(
        "/api/v1/layer3/source/mixed-corpus/materialize",
        json=_materialize_payload(fixture),
    )
    assert duplicate.status_code == 200, duplicate.text
    duplicate_body = duplicate.json()
    assert duplicate_body["source_materialization_id"] == body["source_materialization_id"]
    assert duplicate_body["database_rows_written"] == {
        key: 0 for key in body["database_rows_written"]
    }
    assert _counts(client) == after_counts
    assert _storage_files() == before_files

    material = _drive_preview_only_flow(client, body)
    assert len(material["material_candidates"]) == 2
    assert [
        candidate["source_identity"]["dataset_version_id"]
        for candidate in material["material_candidates"]
        if candidate["source_class"] == "dataset_version"
    ] == [fixture.dataset_version_id]
    assert [
        candidate["source_identity"]["content_id"]
        for candidate in material["material_candidates"]
        if candidate["source_class"] == "aps_content_document"
    ] == [fixture.aps_content_id]


def test_layer3_raw_mixed_materialize_rejects_bad_manifest_hash_without_side_effects(
    client: TestClient,
) -> None:
    fixture = _write_materialization_manifest()
    payload = _materialize_payload(fixture)
    payload["artifact_manifest_hash"] = "0" * 64 if fixture.manifest_hash != "0" * 64 else "1" * 64

    response, body = _post_materialize_failure(client, payload)

    assert response.status_code == 409
    assert body["error_code"] == "raw_mixed_materialize_manifest_hash_mismatch"
    assert body["blocked_fields"] == ["artifact_manifest_hash"]


def test_layer3_raw_mixed_materialize_rejects_manifest_outside_storage_root_without_side_effects(
    client: TestClient,
    tmp_path: Path,
) -> None:
    fixture = _write_materialization_manifest()
    outside = tmp_path / "outside-materialization.json"
    outside.write_text("{}", encoding="utf-8")
    payload = _materialize_payload(fixture)
    payload["artifact_manifest_ref"] = str(outside)
    payload["artifact_manifest_hash"] = hashlib.sha256(outside.read_bytes()).hexdigest()

    response, body = _post_materialize_failure(client, payload)

    assert response.status_code == 400
    assert body["error_code"] == "raw_mixed_materialize_ref_not_server_owned"
    assert body["blocked_fields"] == ["artifact_manifest_ref"]


def test_layer3_raw_mixed_materialize_rejects_forbidden_request_and_manifest_fields(
    client: TestClient,
    tmp_path: Path,
) -> None:
    fixture = _write_materialization_manifest()
    payload = _materialize_payload(fixture)
    payload["local_directory"] = str(tmp_path)

    response, body = _post_materialize_failure(client, payload)

    assert response.status_code == 400
    assert body["error_code"] == "raw_mixed_materialize_scope_not_admitted"
    assert body["blocked_fields"] == ["local_directory"]

    fixture = _write_materialization_manifest(manifest_overrides={"web_connector": {"url": "https://example.invalid"}})
    response, body = _post_materialize_failure(client, _materialize_payload(fixture))

    assert response.status_code == 400
    assert body["error_code"] == "raw_mixed_materialize_manifest_scope_not_admitted"
    assert body["blocked_fields"] == ["artifact_manifest.web_connector"]


def test_layer3_raw_mixed_materialize_rejects_unsupported_source_classes_without_side_effects(
    client: TestClient,
) -> None:
    fixture = _write_materialization_manifest(source_classes=("dataset_version", "web_connector"))

    response, body = _post_materialize_failure(client, _materialize_payload(fixture))

    assert response.status_code == 400
    assert body["error_code"] == "raw_mixed_materialize_manifest_source_classes_mismatch"
    assert body["blocked_fields"] == ["artifact_manifest_ref"]

    payload = _materialize_payload(_write_materialization_manifest())
    payload["requested_source_classes"] = ["dataset_version", "web_connector"]
    response, body = _post_materialize_failure(client, payload)

    assert response.status_code == 400
    assert body["error_code"] == "unsupported_raw_mixed_materialize_source_class"
    assert body["blocked_fields"] == ["requested_source_classes"]


def test_layer3_raw_mixed_materialize_rolls_back_existing_authority_conflicts(
    client: TestClient,
) -> None:
    fixture = _write_materialization_manifest()
    response = client.post(
        "/api/v1/layer3/source/mixed-corpus/materialize",
        json=_materialize_payload(fixture),
    )
    assert response.status_code == 200, response.text

    conflicting = _write_materialization_manifest(
        dataset_version_id=fixture.dataset_version_id,
        dataset_version_overrides={"version_label": "conflicting-v2"},
    )
    before_counts = _counts(client)
    before_files = _storage_files()
    response = client.post(
        "/api/v1/layer3/source/mixed-corpus/materialize",
        json=_materialize_payload(conflicting),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error_code"] == "raw_mixed_materialize_existing_authority_mismatch"
    assert body["blocked_fields"] == ["dataset_version.version_label"]
    assert _counts(client) == before_counts
    assert _storage_files() == before_files

    conflicting = _write_materialization_manifest(
        dataset_version_id=fixture.dataset_version_id,
        value_variable_id="var-raw-materialized-value-conflict",
    )
    before_counts = _counts(client)
    before_files = _storage_files()
    response = client.post(
        "/api/v1/layer3/source/mixed-corpus/materialize",
        json=_materialize_payload(conflicting),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error_code"] == "raw_mixed_materialize_existing_authority_mismatch"
    assert body["blocked_fields"] == [
        "variable_definition.dataset_version_id",
        "variable_definition.variable_name",
        "variable_definition.variable_id",
    ]
    assert _counts(client) == before_counts
    assert _storage_files() == before_files


def _write_materialization_manifest(
    *,
    dataset_version_id: str = "dv-raw-materialized-001",
    additional_dataset_version_ids: tuple[str, ...] = (),
    value_variable_id: str = "var-raw-materialized-value",
    row_count: int = 2,
    source_classes: tuple[str, ...] = ("dataset_version", "aps_content_document"),
    dataset_version_overrides: dict[str, Any] | None = None,
    manifest_overrides: dict[str, Any] | None = None,
) -> RawMixedMaterializationFixture:
    corpus_batch_id = "batch-raw-materialized-001"
    dataset_id = "ds-raw-materialized-001"
    aps_run_id = "run-raw-materialized-001"
    aps_target_id = "target-raw-materialized-001"
    aps_content_id = "content-raw-materialized-001"
    dataset_version_ids = (dataset_version_id, *additional_dataset_version_ids)
    normalized_text = "Pump replacement notes show valve inspection and containment follow-up."
    normalized_ref, normalized_hash = _write_storage_ref(
        f"raw-materialized/{corpus_batch_id}/aps-normalized.txt",
        normalized_text,
    )
    content_units_ref, _content_units_hash = _write_storage_ref(
        f"raw-materialized/{corpus_batch_id}/aps-content-units.json",
        json.dumps(
            [
                {"unit_id": "unit-001", "text": "Pump replacement notes show valve inspection."},
                {"unit_id": "unit-002", "text": "Containment follow-up is scheduled after inspection."},
            ],
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    blob_ref, blob_hash = _write_storage_ref(
        f"raw-materialized/{corpus_batch_id}/aps-source.txt",
        "source attachment bytes for deterministic APS content",
    )
    chunk_texts = (
        "Pump replacement notes show valve inspection.",
        "Containment follow-up is scheduled after inspection.",
    )

    dataset_versions = [
        _dataset_version_manifest_entry(
            corpus_batch_id=corpus_batch_id,
            aps_run_id=aps_run_id,
            aps_target_id=aps_target_id,
            aps_content_id=aps_content_id,
            dataset_id=dataset_id if index == 0 else f"ds-raw-materialized-{index + 1:03d}",
            dataset_version_id=current_dataset_version_id,
            value_variable_id=value_variable_id if index == 0 else f"var-raw-materialized-value-{index + 1:03d}",
            index=index,
            row_count=row_count,
            overrides=dataset_version_overrides if index == 0 else None,
        )
        for index, current_dataset_version_id in enumerate(dataset_version_ids)
    ]
    manifest = {
        "schema_id": RAW_MIXED_CORPUS_MATERIALIZE_MANIFEST_SCHEMA_ID,
        "corpus_batch_id": corpus_batch_id,
        "source_classes": list(source_classes),
        "dataset_versions": dataset_versions,
        "aps_content_documents": [
            {
                "connector_run": {
                    "connector_run_id": aps_run_id,
                    "source_system": "nrc_adams_aps",
                    "source_mode": "server_owned_manifest",
                    "status": "completed",
                    "request_config_json": {"mode": "materialized-fixture"},
                    "query_plan_json": {"query": "pump valve containment"},
                },
                "target": {
                    "connector_run_target_id": aps_target_id,
                    "ordinal": 1,
                    "artifact_surface": "files",
                    "selection_source": "server_owned_manifest",
                    "selection_scope": "bounded",
                    "artifact_locator_type": "server_owned_ref",
                    "source_artifact_key": "aps://raw-materialized/source",
                    "canonical_artifact_key": "aps://raw-materialized/canonical",
                    "downloaded_sha256": blob_hash,
                    "raw_storage_ref": blob_ref,
                    "fetch_policy_mode": "server_owned_manifest",
                    "status": "completed",
                },
                "document": {
                    "aps_content_document_id": "aps-doc-raw-materialized-001",
                    "content_id": aps_content_id,
                    "content_contract_id": aps_contract.APS_CONTENT_CONTRACT_ID,
                    "chunking_contract_id": aps_contract.APS_CHUNKING_CONTRACT_ID,
                    "normalization_contract_id": aps_contract.APS_NORMALIZATION_CONTRACT_ID,
                    "normalized_text_sha256": normalized_hash,
                    "normalized_char_count": len(normalized_text),
                    "chunk_count": 2,
                    "content_status": "indexed",
                    "media_type": "text/plain",
                    "document_class": "inspection_note",
                    "quality_status": "deterministic",
                    "page_count": 1,
                },
                "chunks": [
                    {
                        "aps_content_chunk_id": "aps-chunk-raw-materialized-001",
                        "chunk_id": "chunk-001",
                        "chunk_ordinal": 0,
                        "start_char": 0,
                        "end_char": len(chunk_texts[0]),
                        "chunk_text": chunk_texts[0],
                        "chunk_text_sha256": hashlib.sha256(chunk_texts[0].encode("utf-8")).hexdigest(),
                        "page_start": 1,
                        "page_end": 1,
                        "unit_kind": "sentence",
                        "quality_status": "deterministic",
                    },
                    {
                        "aps_content_chunk_id": "aps-chunk-raw-materialized-002",
                        "chunk_id": "chunk-002",
                        "chunk_ordinal": 1,
                        "start_char": len(chunk_texts[0]) + 1,
                        "end_char": len(normalized_text),
                        "chunk_text": chunk_texts[1],
                        "chunk_text_sha256": hashlib.sha256(chunk_texts[1].encode("utf-8")).hexdigest(),
                        "page_start": 1,
                        "page_end": 1,
                        "unit_kind": "sentence",
                        "quality_status": "deterministic",
                    },
                ],
                "linkage": {
                    "aps_content_linkage_id": "aps-linkage-raw-materialized-001",
                    "accession_number": "MLRAW000001",
                    "content_units_ref": content_units_ref,
                    "normalized_text_ref": normalized_ref,
                    "normalized_text_sha256": normalized_hash,
                    "blob_ref": blob_ref,
                    "blob_sha256": blob_hash,
                    "selection_ref": "server-owned-selection-ref",
                    "diagnostics_ref": "server-owned-diagnostics-ref",
                },
            }
        ],
    }
    manifest.update(manifest_overrides or {})
    variant = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:12]
    manifest_ref = f"raw-materialized/{corpus_batch_id}/manifest-{variant}.json"
    manifest_path = Path(settings.storage_dir) / manifest_ref
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return RawMixedMaterializationFixture(
        corpus_batch_id=corpus_batch_id,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
        dataset_version_ids=dataset_version_ids,
        aps_run_id=aps_run_id,
        aps_target_id=aps_target_id,
        aps_content_id=aps_content_id,
        manifest_ref=manifest_ref,
        manifest_hash=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    )


def _dataset_version_manifest_entry(
    *,
    corpus_batch_id: str,
    aps_run_id: str,
    aps_target_id: str,
    aps_content_id: str,
    dataset_id: str,
    dataset_version_id: str,
    value_variable_id: str,
    index: int,
    row_count: int,
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    suffix = "" if index == 0 else f"-{index + 1:03d}"
    rows = [
        {
            "dataset_row_id": f"row-raw-materialized-{row_index + 1:03d}"
            if index == 0
            else f"row-raw-materialized-{index + 1:03d}-{row_index + 1:03d}",
            "row_number": row_index + 1,
            "values_json": {
                "period": f"2026-{row_index + 1:02d}",
                "value": 4.5 + index + (row_index * 0.25),
            },
        }
        for row_index in range(row_count)
    ]
    csv_rows = "\n".join(f"{row['values_json']['period']},{row['values_json']['value']}" for row in rows)
    dataset_ref, dataset_hash = _write_storage_ref(
        f"raw-materialized/{corpus_batch_id}/dataset{suffix}.csv",
        f"period,value\n{csv_rows}\n",
    )
    entry = {
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "name": "Raw Materialized Dataset" if index == 0 else f"Raw Materialized Dataset {index + 1}",
        "description": "Deterministic materialized dataset for Layer 3 tests.",
        "domain_pack": "nrc_aps",
        "frequency_hint": "monthly",
        "time_column": "period",
        "version_label": "v1",
        "version_type": "raw_mixed_materialized",
        "status": "ready",
        "storage_ref": dataset_ref,
        "storage_sha256": dataset_hash,
        "row_count": row_count,
        "variables": [
            {
                "variable_id": "var-raw-materialized-period" if index == 0 else f"var-raw-materialized-period-{index + 1:03d}",
                "variable_name": "period",
                "dtype": "string",
                "role": "time",
                "is_numeric": False,
                "is_time_index": True,
                "ordinal_position": 0,
            },
            {
                "variable_id": value_variable_id,
                "variable_name": "value",
                "dtype": "float",
                "role": "measure",
                "is_numeric": True,
                "is_time_index": False,
                "ordinal_position": 1,
            },
        ],
        "rows": rows,
        "variable_profiles": [
            {
                "variable_profile_id": "profile-raw-materialized-value" if index == 0 else f"profile-raw-materialized-value-{index + 1:03d}",
                "variable_id": value_variable_id,
                "seasonality_flag": False,
                "stationarity_hint": "not_evaluated",
                "summary_json": {"min": 4.5 + index, "max": 5.25 + index},
            }
        ],
        "source_provenance": {
            "dataset_source_provenance_id": "prov-raw-materialized-001" if index == 0 else f"prov-raw-materialized-{index + 1:03d}",
            "source_system": "nrc_adams_aps",
            "source_mode": "raw_mixed_materialized",
            "source_artifact_key": f"aps://{aps_run_id}/{aps_target_id}/{dataset_version_id}",
            "source_reference_json": {
                "content_id": aps_content_id,
                "parser_family": "csv_table",
            },
        },
    }
    entry.update(overrides or {})
    return entry


def _write_storage_ref(ref: str, content: str) -> tuple[str, str]:
    path = Path(settings.storage_dir) / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ref, hashlib.sha256(path.read_bytes()).hexdigest()


def _materialize_payload(fixture: RawMixedMaterializationFixture) -> dict[str, Any]:
    return {
        "schema_id": "layer3.raw_mixed_corpus_materialize_request.v1",
        "schema_version": 1,
        "client_request_id": "raw-mixed-materialize-success",
        "materialization_mode": RAW_MIXED_CORPUS_MATERIALIZE_MODE,
        "corpus_batch_id": fixture.corpus_batch_id,
        "artifact_manifest_ref": fixture.manifest_ref,
        "artifact_manifest_hash": fixture.manifest_hash,
        "requested_source_classes": ["dataset_version", "aps_content_document"],
        "operator_confirmation": True,
    }


def _post_materialize_failure(
    client: TestClient,
    payload: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    before_counts = _counts(client)
    before_files = _storage_files()

    response = client.post("/api/v1/layer3/source/mixed-corpus/materialize", json=payload)

    body = response.json()
    assert "layer3_flow_started" not in body
    assert "source_materialization_id" not in body
    assert _counts(client) == before_counts
    assert _storage_files() == before_files
    return response, body


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
            "dataset_rows": db.query(DatasetRow).count(),
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


def _count_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {
        key: after[key] - before[key]
        for key in [
            "datasets",
            "dataset_versions",
            "variables",
            "dataset_rows",
            "variable_profiles",
            "dataset_source_provenance",
            "connector_runs",
            "connector_run_targets",
            "aps_content_documents",
            "aps_content_chunks",
            "aps_content_linkages",
        ]
    }


def _assert_no_layer3_flow_delta(before: dict[str, int], after: dict[str, int]) -> None:
    for key in [
        "analysis_groups",
        "analysis_plans",
        "analysis_runs",
        "analysis_sets",
        "analysis_units",
        "descriptors",
        "material_snapshots",
        "output_packages",
        "pass_runs",
        "reconciliations",
        "retrieval_events",
        "selection_manifests",
        "sessions",
        "typing_records",
    ]:
        assert after[key] == before[key]
