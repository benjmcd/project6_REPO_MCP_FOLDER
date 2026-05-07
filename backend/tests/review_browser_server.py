from __future__ import annotations

import hashlib
from itertools import count
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


os.environ["DB_INIT_MODE"] = "none"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.api import layer3, review_nrc_aps
from app.api.deps import get_db
from app.core.config import bootstrap_storage_tree, settings
from app.db.session import Base
from app.models.models import (
    AnalysisArtifact,
    AnalysisRun,
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetSourceProvenance,
    DatasetVersion,
    L3OutputPackage,
    L3ReconciliationRecord,
    VariableDefinition,
    VariableProfile,
    uuid_str,
)
from app.services import layer3_pass_entry as layer3_pass_entry_module
from app.services.layer3_raw_mixed_bridge import (
    RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID,
    RAW_MIXED_CORPUS_SEED_MODE,
)
from app.services.layer3_raw_mixed_materialization import (
    RAW_MIXED_CORPUS_MATERIALIZE_MANIFEST_SCHEMA_ID,
    RAW_MIXED_CORPUS_MATERIALIZE_MODE,
    RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA_ID,
)
from app.services.layer3_session_entry import (
    SessionEntryRequest,
    SnapshotMaterial,
    commit_selection,
    expand_descriptors,
    finalize_session,
    record_retrieval_event,
)
from app.services.layer3_typing_entry import materialize_typing_entry
from review_browser_fixture import build_review_browser_fixture, install_review_browser_patches

APS_EVIDENCE_BUNDLE_SCHEMA_ID = "aps.evidence_bundle.v2"
APS_EVIDENCE_BUNDLE_SCHEMA_VERSION = 2
APS_MODE_BROWSE = "browse"
APS_CONTENT_CONTRACT_ID = "aps_content_units_v2"
APS_CHUNKING_CONTRACT_ID = "aps_chunking_v2"
APS_NORMALIZATION_CONTRACT_ID = "aps_text_normalization_v2"
PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF = "aps_evidence_bundle_handoff"
HARNESS_INFO_SCHEMA_ID = "project6.review_browser_harness_info.v1"
HARNESS_INFO_SCHEMA_VERSION = 1
HARNESS_FIXTURE_VERSION = "review-browser-fixture-v1"
HARNESS_PATCH_GROUPS = (
    "review-runtime-bindings",
    "workbench-compare",
    "candidate-b-trace",
    "layer3-deterministic-analysis",
    "layer3-aps-handoff",
)


def _canonical_json_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def _compute_aps_bundle_checksum(payload: dict[str, object]) -> str:
    clean = dict(payload)
    clean.pop("bundle_checksum", None)
    clean.pop("_bundle_ref", None)
    clean.pop("_persisted", None)
    return hashlib.sha256(_canonical_json_bytes(clean)).hexdigest()


def _install_layer3_browser_patches(temp_path: Path) -> None:
    class _BrowserEvidenceBundleError(RuntimeError):
        def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
            super().__init__(message)
            self.code = code
            self.message = message
            self.status_code = status_code

    def _load_browser_persisted_bundle_artifact(*, bundle_ref: str | Path):
        bundle_path = Path(bundle_ref)
        if not bundle_path.exists():
            raise _BrowserEvidenceBundleError("invalid_request", "bundle not found", status_code=404)
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        if payload.get("schema_id") != APS_EVIDENCE_BUNDLE_SCHEMA_ID:
            raise _BrowserEvidenceBundleError("schema_mismatch", "bundle schema mismatch", status_code=409)
        expected_checksum = _compute_aps_bundle_checksum(payload)
        if payload.get("bundle_checksum") != expected_checksum:
            raise _BrowserEvidenceBundleError("checksum_mismatch", "bundle checksum mismatch", status_code=409)
        return payload, bundle_path

    aps_bundle_module = ModuleType("app.services.nrc_aps_evidence_bundle")
    aps_bundle_module.EvidenceBundleError = _BrowserEvidenceBundleError
    aps_bundle_module.load_persisted_bundle_artifact = _load_browser_persisted_bundle_artifact
    sys.modules["app.services.nrc_aps_evidence_bundle"] = aps_bundle_module

    def _recommend_analysis(*args, **kwargs) -> dict[str, object]:
        dataset_version_id = str(kwargs.get("dataset_version_id") or (args[1] if len(args) > 1 else ""))
        return {
            "dataset_version_id": dataset_version_id,
            "recommended_sequence": ["decomposition", "structural_break"],
            "rationale": "browser harness deterministic quantitative recommendation",
            "profile_context": {
                "stationary_like_variables": ["value"],
                "mixed_or_nonstationary_variables": [],
                "seasonal_like_variables": ["value"],
            },
        }

    def _run_analysis(db, *, dataset_version_id, method_name, goal_type=None, parameters=None, annotation_window_id=None):
        now = datetime.now(timezone.utc)
        run = AnalysisRun(
            analysis_run_id=uuid_str(),
            dataset_version_id=dataset_version_id,
            method_name=method_name,
            goal_type=goal_type,
            status="completed",
            route_reason="browser harness deterministic quantitative run",
            parameters_json=parameters or {},
            window_scope_json={"annotation_window_id": annotation_window_id} if annotation_window_id else {},
            started_at=now,
            completed_at=now,
        )
        db.add(run)
        db.flush()
        db.add(
            AnalysisArtifact(
                artifact_id=uuid_str(),
                analysis_run_id=run.analysis_run_id,
                artifact_type="summary_json",
                title="Browser harness deterministic output",
                storage_ref=f"layer3-browser://artifact/{run.analysis_run_id}/summary.json",
                summary="Deterministic Layer 3 browser harness output.",
                metadata_json={"source": "review_browser_server", "method_name": method_name},
            )
        )
        db.flush()
        return run

    layer3_pass_entry_module.recommend_analysis = _recommend_analysis
    layer3_pass_entry_module.run_analysis = _run_analysis

    from app.services import layer3_workbench as layer3_workbench_module

    def _check_aps_handoff_compatibility(db, *, session_id):
        return SimpleNamespace(compatible=True, blocked_reason=None)

    def _materialize_aps_handoff(db, *, session_id):
        reconciliation = (
            db.query(L3ReconciliationRecord)
            .filter(L3ReconciliationRecord.session_id == session_id)
            .one()
        )
        output_package_id = uuid_str()
        payload_path = temp_path / "aps-dispatch" / f"{output_package_id}.json"
        bundle_id = f"browser-aps-bundle-{output_package_id}"
        payload = {
            "schema_id": APS_EVIDENCE_BUNDLE_SCHEMA_ID,
            "schema_version": APS_EVIDENCE_BUNDLE_SCHEMA_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "bundle_id": bundle_id,
            "mode": APS_MODE_BROWSE,
            "session_id": session_id,
            "reconciliation_record_id": reconciliation.reconciliation_record_id,
            "results": [],
        }
        payload["bundle_checksum"] = _compute_aps_bundle_checksum(payload)
        payload_ref = _write_json(payload_path, payload)
        package = L3OutputPackage(
            output_package_id=output_package_id,
            session_id=session_id,
            reconciliation_record_id=reconciliation.reconciliation_record_id,
            package_kind=PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF,
            status="package_complete",
            payload_ref=payload_ref,
            payload_hash=hashlib.sha256(Path(payload_ref).read_bytes()).hexdigest(),
            summary_json={
                "bundle_id": payload["bundle_id"],
                "aps_schema_id": payload["schema_id"],
            },
        )
        db.add(package)
        db.flush()
        return SimpleNamespace(output_package=package)

    layer3_workbench_module.check_aps_handoff_compatibility = _check_aps_handoff_compatibility
    layer3_workbench_module.materialize_aps_handoff = _materialize_aps_handoff


def _write_json(path: Path, payload: dict[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return str(path)


def _write_text(path: Path, payload: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return str(path)


def _seed_browser_dataset_version(db, temp_path: Path, *, seed_id: str, dataset_id: str, dataset_version_id: str) -> Path:
    dataset = Dataset(
        dataset_id=dataset_id,
        name=f"Dataset {seed_id}",
        description="Layer 3 browser harness dataset",
        frequency_hint="MS",
        time_column="observed_at",
    )
    version = DatasetVersion(
        dataset_version_id=dataset_version_id,
        dataset_id=dataset_id,
        version_label="v1",
        version_type="baseline",
        status="ready",
        notes="layer3-browser-harness",
    )
    observed_at = VariableDefinition(
        variable_id=f"var-time-{seed_id}",
        dataset_version_id=dataset_version_id,
        variable_name="observed_at",
        dtype="datetime64[ns]",
        role="time_index",
        is_numeric=False,
        is_time_index=True,
        ordinal_position=0,
    )
    value = VariableDefinition(
        variable_id=f"var-value-{seed_id}",
        dataset_version_id=dataset_version_id,
        variable_name="value",
        dtype="float64",
        role="measure",
        is_numeric=True,
        is_time_index=False,
        ordinal_position=1,
    )
    value_profile = VariableProfile(
        variable_profile_id=f"profile-value-{seed_id}",
        dataset_version_id=dataset_version_id,
        variable_id=value.variable_id,
        seasonality_flag=True,
        stationarity_hint="likely_stationary",
        summary_json={},
    )
    db.add_all([dataset, version, observed_at, value, value_profile])
    db.flush()

    dataset_dir = temp_path / "datasets"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / f"{dataset_version_id}.csv"
    rows = ["observed_at,value"]
    for index in range(24):
        year = 2020 + (index // 12)
        month = 1 + (index % 12)
        rows.append(f"{year:04d}-{month:02d}-01T00:00:00+00:00,{100 + index}")
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    version.storage_ref = str(csv_path)
    version.row_count = 24
    db.flush()
    return csv_path


def _seed_browser_aps_dataset_version_candidate(db, temp_path: Path) -> dict[str, str]:
    seed_id = uuid_str()
    dataset_id = f"ds-aps-{seed_id}"
    dataset_version_id = f"dv-aps-{seed_id}"
    csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=f"aps-{seed_id}",
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
    )
    db.add(
        DatasetSourceProvenance(
            dataset_version_id=dataset_version_id,
            connector_run_id=None,
            source_system="nrc_adams_aps",
            source_mode="artifact_csv_parser",
            source_artifact_key=f"aps-target-artifacts/run-{seed_id}/target-{seed_id}/extraction.json",
            sciencebase_file_name="browser-fixture.csv",
            downloaded_sha256="1" * 64,
            raw_storage_ref=f"aps-target-artifacts/run-{seed_id}/target-{seed_id}/blob.csv",
            source_reference_json={
                "target_id": f"target-{seed_id}",
                "accession_number": "ML26001A777",
                "table_index": 0,
                "table_hash": f"hash-table-{seed_id}",
                "parser_family": "csv_table",
                "parser_contract_id": "aps_csv_parser_v1",
                "typed_content_contract_id": "aps_csv_table_units_v1",
                "diagnostics_ref": f"aps-target-artifacts/run-{seed_id}/target-{seed_id}/diagnostics.json",
            },
        )
    )
    db.commit()
    return {
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "storage_ref": str(csv_path),
    }


def _seed_browser_raw_mixed_authority(db, temp_path: Path, *, seed_id: str) -> dict[str, object]:
    dataset_version_ids = (f"dv-{seed_id}-a", f"dv-{seed_id}-b")
    dataset_ids = (f"ds-{seed_id}-a", f"ds-{seed_id}-b")
    run_id = f"run-{seed_id}"
    target_id = f"target-{seed_id}"
    content_id = f"content-{seed_id}"
    corpus_batch_id = f"batch-{seed_id}"

    for index, dataset_version_id in enumerate(dataset_version_ids):
        _seed_browser_dataset_version(
            db,
            temp_path,
            seed_id=f"{seed_id}-{index + 1}",
            dataset_id=dataset_ids[index],
            dataset_version_id=dataset_version_id,
        )

    _seed_browser_aps_content_fixture(db, temp_path, run_id=run_id, target_id=target_id, content_id=content_id)

    for dataset_version_id in dataset_version_ids:
        db.add(
            DatasetSourceProvenance(
                dataset_version_id=dataset_version_id,
                connector_run_id=run_id,
                source_system="nrc_adams_aps",
                source_mode="raw_mixed_corpus_bridge_seed_fixture",
                source_artifact_key=f"aps://{run_id}/{target_id}/{dataset_version_id}",
                sciencebase_file_name="browser-raw-mixed-fixture.csv",
                downloaded_sha256=hashlib.sha256(dataset_version_id.encode("utf-8")).hexdigest(),
                raw_storage_ref=f"dataset_version:{dataset_version_id}",
                source_reference_json={
                    "target_id": target_id,
                    "content_id": content_id,
                    "accession_number": "ML26001A777",
                    "parser_family": "csv_table",
                    "parser_contract_id": "aps_csv_parser_v1",
                    "typed_content_contract_id": "aps_csv_table_units_v1",
                },
                fetch_policy_mode="seed_fixture",
            )
        )

    manifest_ref = f"raw-mixed/{seed_id}.json"
    manifest_path = Path(settings.storage_dir) / manifest_ref
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_id": RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID,
        "corpus_batch_id": corpus_batch_id,
        "aps_run_id": run_id,
        "target_ids": [target_id],
        "source_classes": ["dataset_version", "aps_content_document"],
        "dataset_version_ids": list(dataset_version_ids),
        "aps_content_document_ids": [content_id],
    }
    manifest_path.write_bytes(_canonical_json_bytes(manifest))
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    db.commit()

    return {
        "schema_id": "project6.review_browser_raw_mixed_seed_setup.v1",
        "schema_version": 1,
        "seed_request": {
            "schema_id": "layer3.raw_mixed_corpus_seed_request.v1",
            "schema_version": 1,
            "client_request_id": f"browser-raw-mixed-seed-{seed_id}",
            "seed_mode": RAW_MIXED_CORPUS_SEED_MODE,
            "corpus_batch_id": corpus_batch_id,
            "aps_run_id": run_id,
            "target_ids": [target_id],
            "artifact_manifest_ref": manifest_ref,
            "artifact_manifest_hash": manifest_hash,
            "requested_source_classes": ["dataset_version", "aps_content_document"],
            "operator_confirmation": True,
        },
    }


def _write_browser_storage_ref(ref: str, content: str) -> tuple[str, str]:
    path = Path(settings.storage_dir) / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ref, hashlib.sha256(path.read_bytes()).hexdigest()


def _browser_materialized_dataset_entry(
    *,
    seed_id: str,
    corpus_batch_id: str,
    run_id: str,
    target_id: str,
    content_id: str,
    index: int,
) -> dict[str, object]:
    dataset_version_id = f"dv-materialized-{seed_id}-{index + 1}"
    dataset_id = f"ds-materialized-{seed_id}-{index + 1}"
    rows = [
        {
            "dataset_row_id": f"row-materialized-{seed_id}-{index + 1}-{row_index + 1}",
            "row_number": row_index + 1,
            "values_json": {
                "period": f"2026-{row_index + 1:02d}",
                "value": 10 + index + (row_index * 0.5),
            },
        }
        for row_index in range(24)
    ]
    csv_rows = "\n".join(f"{row['values_json']['period']},{row['values_json']['value']}" for row in rows)
    storage_ref, storage_hash = _write_browser_storage_ref(
        f"raw-materialized/{corpus_batch_id}/dataset-{index + 1}.csv",
        f"period,value\n{csv_rows}\n",
    )
    value_variable_id = f"var-materialized-value-{seed_id}-{index + 1}"
    return {
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "name": f"Browser Raw Materialized Dataset {index + 1}",
        "description": "Deterministic browser harness materialized dataset.",
        "domain_pack": "nrc_aps",
        "frequency_hint": "monthly",
        "time_column": "period",
        "version_label": "v1",
        "version_type": "raw_mixed_materialized",
        "status": "ready",
        "storage_ref": storage_ref,
        "storage_sha256": storage_hash,
        "row_count": 24,
        "variables": [
            {
                "variable_id": f"var-materialized-period-{seed_id}-{index + 1}",
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
                "variable_profile_id": f"profile-materialized-value-{seed_id}-{index + 1}",
                "variable_id": value_variable_id,
                "seasonality_flag": False,
                "stationarity_hint": "not_evaluated",
                "summary_json": {"min": 10 + index, "max": 21.5 + index},
            }
        ],
        "source_provenance": {
            "dataset_source_provenance_id": f"prov-materialized-{seed_id}-{index + 1}",
            "source_system": "nrc_adams_aps",
            "source_mode": "raw_mixed_materialized",
            "source_artifact_key": f"aps://{run_id}/{target_id}/{dataset_version_id}",
            "source_reference_json": {
                "content_id": content_id,
                "parser_family": "csv_table",
                "parser_contract_id": "aps_csv_parser_v1",
                "typed_content_contract_id": "aps_csv_table_units_v1",
            },
        },
    }


def _build_browser_raw_mixed_materialization_setup(*, seed_id: str) -> dict[str, object]:
    corpus_batch_id = f"batch-materialized-{seed_id}"
    run_id = f"run-materialized-{seed_id}"
    target_id = f"target-materialized-{seed_id}"
    content_id = f"content-materialized-{seed_id}"
    normalized_text = "Browser materialized APS content confirms inspection follow-up."
    normalized_ref, normalized_hash = _write_browser_storage_ref(
        f"raw-materialized/{corpus_batch_id}/aps-normalized.txt",
        normalized_text,
    )
    content_units_ref, _content_units_hash = _write_browser_storage_ref(
        f"raw-materialized/{corpus_batch_id}/aps-content-units.json",
        json.dumps(
            [
                {"unit_id": "unit-001", "text": "Browser materialized APS content confirms inspection."},
                {"unit_id": "unit-002", "text": "Follow-up is recorded for rendered selection proof."},
            ],
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    blob_ref, blob_hash = _write_browser_storage_ref(
        f"raw-materialized/{corpus_batch_id}/aps-source.txt",
        "browser raw materialization source bytes",
    )
    chunk_texts = [
        "Browser materialized APS content confirms inspection.",
        "Follow-up is recorded for rendered selection proof.",
    ]
    manifest = {
        "schema_id": RAW_MIXED_CORPUS_MATERIALIZE_MANIFEST_SCHEMA_ID,
        "corpus_batch_id": corpus_batch_id,
        "source_classes": ["dataset_version", "aps_content_document"],
        "dataset_versions": [
            _browser_materialized_dataset_entry(
                seed_id=seed_id,
                corpus_batch_id=corpus_batch_id,
                run_id=run_id,
                target_id=target_id,
                content_id=content_id,
                index=index,
            )
            for index in range(2)
        ],
        "aps_content_documents": [
            {
                "connector_run": {
                    "connector_run_id": run_id,
                    "source_system": "nrc_adams_aps",
                    "source_mode": "server_owned_manifest",
                    "status": "completed",
                    "request_config_json": {"fixture": "browser_raw_mixed_materialization"},
                    "query_plan_json": {"corpus_batch_id": corpus_batch_id},
                },
                "target": {
                    "connector_run_target_id": target_id,
                    "connector_run_id": run_id,
                    "ordinal": 0,
                    "artifact_surface": "files",
                    "selection_source": "browser_materialization_manifest",
                    "selection_scope": "single_aps_document",
                    "artifact_locator_type": "server_owned_ref",
                    "source_artifact_key": f"aps://{run_id}/{target_id}/{content_id}",
                    "canonical_artifact_key": f"aps://{run_id}/{target_id}/canonical",
                    "downloaded_sha256": blob_hash,
                    "raw_storage_ref": blob_ref,
                    "fetch_policy_mode": "server_owned_manifest",
                    "status": "completed",
                },
                "document": {
                    "aps_content_document_id": f"aps-doc-materialized-{seed_id}",
                    "content_id": content_id,
                    "content_contract_id": APS_CONTENT_CONTRACT_ID,
                    "chunking_contract_id": APS_CHUNKING_CONTRACT_ID,
                    "normalization_contract_id": APS_NORMALIZATION_CONTRACT_ID,
                    "normalized_text_sha256": normalized_hash,
                    "normalized_char_count": len(normalized_text),
                    "chunk_count": len(chunk_texts),
                    "content_status": "indexed",
                    "media_type": "application/pdf",
                    "document_class": "inspection_report",
                    "quality_status": "strong",
                    "page_count": 2,
                    "diagnostics_ref": f"raw-materialized/{corpus_batch_id}/diagnostics.json",
                    "visual_page_refs_json": [],
                },
                "chunks": [
                    {
                        "aps_content_chunk_id": f"aps-chunk-materialized-{seed_id}-{index + 1}",
                        "chunk_id": f"{content_id}-chunk-{index + 1}",
                        "chunk_ordinal": index,
                        "chunk_text": chunk_text,
                        "chunk_text_sha256": hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                        "start_char": index * 64,
                        "end_char": (index * 64) + len(chunk_text),
                        "page_start": index + 1,
                        "page_end": index + 1,
                        "unit_kind": "pdf_paragraph",
                        "quality_status": "strong",
                    }
                    for index, chunk_text in enumerate(chunk_texts)
                ],
                "linkage": {
                    "aps_content_linkage_id": f"aps-linkage-materialized-{seed_id}",
                    "accession_number": "MLRAWBROWSER001",
                    "content_units_ref": content_units_ref,
                    "normalized_text_ref": normalized_ref,
                    "normalized_text_sha256": normalized_hash,
                    "blob_ref": blob_ref,
                    "blob_sha256": blob_hash,
                    "download_exchange_ref": f"raw-materialized/{corpus_batch_id}/download-exchange.json",
                    "discovery_ref": f"raw-materialized/{corpus_batch_id}/discovery.json",
                    "selection_ref": f"raw-materialized/{corpus_batch_id}/selection.json",
                    "diagnostics_ref": f"raw-materialized/{corpus_batch_id}/diagnostics.json",
                },
            }
        ],
    }
    manifest_ref = f"raw-materialized/{corpus_batch_id}/manifest.json"
    manifest_path = Path(settings.storage_dir) / manifest_ref
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(_canonical_json_bytes(manifest))
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return {
        "schema_id": "project6.review_browser_raw_mixed_materialization_setup.v1",
        "schema_version": 1,
        "materialize_request": {
            "schema_id": RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA_ID,
            "schema_version": 1,
            "client_request_id": f"browser-raw-mixed-materialize-{seed_id}",
            "materialization_mode": RAW_MIXED_CORPUS_MATERIALIZE_MODE,
            "corpus_batch_id": corpus_batch_id,
            "artifact_manifest_ref": manifest_ref,
            "artifact_manifest_hash": manifest_hash,
            "requested_source_classes": ["dataset_version", "aps_content_document"],
            "operator_confirmation": True,
        },
    }


def _seed_browser_aps_content_fixture(
    db,
    temp_path: Path,
    *,
    run_id: str,
    target_id: str,
    content_id: str,
) -> None:
    db.add(
        ConnectorRun(
            connector_run_id=run_id,
            connector_key="nrc_adams_aps",
            status="completed",
        )
    )
    db.add(
        ConnectorRunTarget(
            connector_run_target_id=target_id,
            connector_run_id=run_id,
            status="completed",
            ordinal=0,
        )
    )

    artifact_root = temp_path / "aps"
    chunk_texts = [
        "Inspection findings confirm stable cooling performance.",
        "No safety-significant degradation was identified during the interval.",
    ]
    normalized_text = "\n".join(chunk_texts)
    content_units_ref = _write_json(
        artifact_root / f"{content_id}_content_units.json",
        {
            "content_id": content_id,
            "run_id": run_id,
            "target_id": target_id,
            "chunk_count": len(chunk_texts),
        },
    )
    normalized_text_ref = _write_text(artifact_root / f"{content_id}_normalized.txt", normalized_text)
    blob_ref = _write_text(artifact_root / f"{content_id}.pdf", "pdf-placeholder")
    selection_ref = _write_json(artifact_root / f"{content_id}_selection.json", {"run_id": run_id, "target_id": target_id})
    discovery_ref = _write_json(artifact_root / f"{content_id}_discovery.json", {"run_id": run_id, "target_id": target_id})
    diagnostics_ref = _write_json(artifact_root / f"{content_id}_diagnostics.json", {"quality_status": "strong"})

    db.add(
        ApsContentDocument(
            content_id=content_id,
            content_contract_id=APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
            normalization_contract_id=APS_NORMALIZATION_CONTRACT_ID,
            normalized_text_sha256=hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
            normalized_char_count=len(normalized_text),
            chunk_count=len(chunk_texts),
            content_status="indexed",
            media_type="application/pdf",
            document_class="inspection_report",
            quality_status="strong",
            page_count=2,
            diagnostics_ref=diagnostics_ref,
            visual_page_refs_json=json.dumps([]),
        )
    )
    for ordinal, chunk_text in enumerate(chunk_texts):
        db.add(
            ApsContentChunk(
                content_id=content_id,
                chunk_id=f"{content_id}-chunk-{ordinal + 1}",
                content_contract_id=APS_CONTENT_CONTRACT_ID,
                chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
                chunk_ordinal=ordinal,
                start_char=ordinal * 64,
                end_char=(ordinal * 64) + len(chunk_text),
                chunk_text=chunk_text,
                chunk_text_sha256=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                page_start=ordinal + 1,
                page_end=ordinal + 1,
                unit_kind="pdf_paragraph",
                quality_status="strong",
            )
        )
    db.add(
        ApsContentLinkage(
            content_id=content_id,
            run_id=run_id,
            target_id=target_id,
            accession_number="ML26001A001",
            content_contract_id=APS_CONTENT_CONTRACT_ID,
            chunking_contract_id=APS_CHUNKING_CONTRACT_ID,
            content_units_ref=content_units_ref,
            normalized_text_ref=normalized_text_ref,
            normalized_text_sha256=hashlib.sha256(normalized_text.encode("utf-8")).hexdigest(),
            blob_ref=blob_ref,
            blob_sha256=hashlib.sha256(Path(blob_ref).read_bytes()).hexdigest(),
            download_exchange_ref="aps/download_exchange.json",
            discovery_ref=discovery_ref,
            selection_ref=selection_ref,
            diagnostics_ref=diagnostics_ref,
        )
    )
    db.flush()


def _build_browser_quant_ready_session(db, temp_path: Path) -> str:
    seed_id = uuid_str()
    dataset_id = f"ds-{seed_id}"
    dataset_version_id = f"dv-{seed_id}"
    csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=seed_id,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
    )
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": f"sel-{seed_id}"},
                "expansion_reason": "committed_selection",
            }
        ],
        source_plane_hints={"plane_a": ["dataset_version"]},
        commit_reason="layer3-browser-harness",
        entry_route_context={"entrypoint": "playwright"},
        operator_context={"operator": "playwright"},
        summary={"phase": "gate_c_pass"},
    )
    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": dataset_version_id},
                source_provenance={"dataset_id": dataset_id, "storage_ref": str(csv_path)},
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 24, "failed_records": 0},
            )
        ],
        storage_root=temp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id


def _build_browser_aps_handoff_ready_session(db, temp_path: Path) -> str:
    seed_id = uuid_str()
    dataset_id = f"ds-{seed_id}"
    dataset_version_id = f"dv-{seed_id}"
    run_id = f"run-{seed_id}"
    target_id = f"target-{seed_id}"
    content_id = f"content-{seed_id}"
    csv_path = _seed_browser_dataset_version(
        db,
        temp_path,
        seed_id=seed_id,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
    )
    _seed_browser_aps_content_fixture(db, temp_path, run_id=run_id, target_id=target_id, content_id=content_id)
    request = SessionEntryRequest(
        manifest_items=[
            {
                "source_plane": "plane_a",
                "descriptor_type": "dataset_version",
                "selector_payload": {"dataset_version_id": dataset_version_id},
                "selection_basis": {"selection_id": f"sel-{seed_id}-quant"},
                "expansion_reason": "committed_selection",
            },
            {
                "source_plane": "plane_b",
                "descriptor_type": "aps_content_document",
                "selector_payload": {"run_id": run_id, "target_id": target_id},
                "selection_basis": {"selection_id": f"sel-{seed_id}-aps-doc"},
                "expansion_reason": "committed_selection",
            },
        ],
        source_plane_hints={"plane_a": ["dataset_version"], "plane_b": ["aps_content_document"]},
        commit_reason="layer3-browser-aps-handoff-harness",
        entry_route_context={"entrypoint": "playwright"},
        operator_context={"operator": "playwright"},
        summary={"phase": "aps_handoff_dispatch"},
    )
    session, manifest = commit_selection(db, request)
    descriptors = expand_descriptors(db, session=session, manifest=manifest)
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[0],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="dataset_version",
                source_identity={"dataset_version_id": dataset_version_id},
                source_provenance={"dataset_id": dataset_id, "storage_ref": str(csv_path)},
                payload={"dataset_version_id": dataset_version_id},
                load_summary={"loaded_records": 24, "failed_records": 0},
            )
        ],
        storage_root=temp_path,
    )
    record_retrieval_event(
        db,
        session=session,
        descriptor=descriptors[1],
        outcome="loaded",
        reason_code="loaded",
        loaded_materials=[
            SnapshotMaterial(
                source_shape="aps_content_document",
                source_identity={"content_id": content_id, "run_id": run_id, "target_id": target_id},
                source_provenance={"linkage_ref": f"aps/linkage/{content_id}"},
                payload={"content": "browser APS handoff companion"},
                load_summary={"loaded_records": 1, "failed_records": 0},
            )
        ],
        storage_root=temp_path,
    )
    finalize_session(db, session=session)
    db.commit()
    materialize_typing_entry(db, session_id=session.session_id)
    db.commit()
    return session.session_id


def create_app() -> FastAPI:
    temp_dir = TemporaryDirectory(prefix="review-browser-", ignore_cleanup_errors=True)
    temp_path = Path(temp_dir.name)
    raw_mixed_seed_counter = count(1)
    raw_mixed_materialization_counter = count(1)
    fixture = build_review_browser_fixture(temp_path)
    install_review_browser_patches(fixture)
    _install_layer3_browser_patches(temp_path)
    settings.storage_dir = str(temp_path / "storage")
    bootstrap_storage_tree(settings.storage_dir)
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    review_ui_static_dir = Path(__file__).resolve().parents[1] / "app" / "review_ui" / "static"

    app = FastAPI(title="NRC APS Review Browser Server")
    app.state.review_browser_temp_dir = temp_dir
    app.state.review_browser_fixture = fixture
    app.state.layer3_engine = engine
    app.include_router(review_nrc_aps.router, prefix="/api/v1/review/nrc-aps")
    app.include_router(layer3.router, prefix="/api/v1/layer3")
    app.mount("/review/nrc-aps/static", StaticFiles(directory=review_ui_static_dir), name="review_ui_static")
    app.mount("/review/layer3/static", StaticFiles(directory=review_ui_static_dir), name="layer3_ui_static")

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/review/nrc-aps", response_class=HTMLResponse)
    def review_nrc_aps_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "index.html").read_text(encoding="utf-8"))

    @app.get("/review/nrc-aps/document-trace", response_class=HTMLResponse)
    def review_nrc_aps_document_trace_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "document_trace.html").read_text(encoding="utf-8"))

    @app.get("/review/nrc-aps/workbench-compare", response_class=HTMLResponse)
    def review_nrc_aps_workbench_compare_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "workbench_compare.html").read_text(encoding="utf-8"))

    @app.get("/review/nrc-aps/candidate-b-trace", response_class=HTMLResponse)
    def review_nrc_aps_candidate_b_trace_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "candidate_b_trace.html").read_text(encoding="utf-8"))

    @app.get("/review/layer3", response_class=HTMLResponse)
    def layer3_workbench_page() -> HTMLResponse:
        return HTMLResponse(content=(review_ui_static_dir / "layer3.html").read_text(encoding="utf-8"))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/__test/harness-info")
    def harness_info() -> dict[str, object]:
        return {
            "schema_id": HARNESS_INFO_SCHEMA_ID,
            "schema_version": HARNESS_INFO_SCHEMA_VERSION,
            "harness_name": "review_browser_server",
            "fixture_version": HARNESS_FIXTURE_VERSION,
            "test_only": True,
            "storage_mode": "temporary-redacted",
            "patch_groups": list(HARNESS_PATCH_GROUPS),
            "runtime_binding_count": len(fixture.selector.runs),
            "seed_routes": [
                "/__test/layer3/seed-quant",
                "/__test/layer3/seed-aps-dataset",
                "/__test/layer3/seed-aps-document",
                "/__test/layer3/seed-aps-handoff",
                "/__test/layer3/seed-raw-mixed",
                "/__test/layer3/materialize-raw-mixed",
            ],
        }

    @app.post("/__test/layer3/seed-quant")
    def seed_layer3_quant() -> dict[str, str]:
        db = SessionLocal()
        try:
            session_id = _build_browser_quant_ready_session(db, temp_path)
            return {"session_id": session_id}
        finally:
            db.close()

    @app.post("/__test/layer3/seed-aps-dataset")
    def seed_layer3_aps_dataset() -> dict[str, str]:
        db = SessionLocal()
        try:
            return _seed_browser_aps_dataset_version_candidate(db, temp_path)
        finally:
            db.close()

    @app.post("/__test/layer3/seed-aps-document")
    def seed_layer3_aps_document() -> dict[str, str]:
        db = SessionLocal()
        try:
            seed_id = uuid_str()
            run_id = f"run-{seed_id}"
            target_id = f"target-{seed_id}"
            content_id = f"content-{seed_id}"
            _seed_browser_aps_content_fixture(
                db,
                temp_path,
                run_id=run_id,
                target_id=target_id,
                content_id=content_id,
            )
            db.commit()
            return {"run_id": run_id, "target_id": target_id, "content_id": content_id}
        finally:
            db.close()

    @app.post("/__test/layer3/seed-aps-handoff")
    def seed_layer3_aps_handoff() -> dict[str, str]:
        db = SessionLocal()
        try:
            session_id = _build_browser_aps_handoff_ready_session(db, temp_path)
            return {"session_id": session_id}
        finally:
            db.close()

    @app.post("/__test/layer3/seed-raw-mixed")
    def seed_layer3_raw_mixed() -> dict[str, object]:
        db = SessionLocal()
        try:
            seed_id = f"raw-mixed-browser-{next(raw_mixed_seed_counter):03d}"
            return _seed_browser_raw_mixed_authority(db, temp_path, seed_id=seed_id)
        finally:
            db.close()

    @app.post("/__test/layer3/materialize-raw-mixed")
    def materialize_layer3_raw_mixed_setup() -> dict[str, object]:
        seed_id = f"raw-mixed-materialize-browser-{next(raw_mixed_materialization_counter):03d}"
        return _build_browser_raw_mixed_materialization_setup(seed_id=seed_id)

    return app
