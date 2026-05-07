from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    ApsContentChunk,
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
    Dataset,
    DatasetRow,
    DatasetSourceProvenance,
    DatasetVersion,
    VariableDefinition,
    VariableProfile,
)
from app.services.layer3_raw_mixed_bridge import (
    RAW_MIXED_CORPUS_FORBIDDEN_FIELDS,
    RAW_MIXED_CORPUS_SOURCE_CLASSES,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_source_boundary import unsupported_requested
from app.services.layer3_utils import stable_id
from app.services.layer3_workbench_error import Layer3WorkbenchError


RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA_ID = "layer3.raw_mixed_corpus_materialize_request.v1"
RAW_MIXED_CORPUS_MATERIALIZE_RESPONSE_SCHEMA_ID = "layer3.raw_mixed_corpus_materialize_result.v1"
RAW_MIXED_CORPUS_MATERIALIZE_MANIFEST_SCHEMA_ID = "layer3.raw_mixed_corpus_materialization_manifest.v1"
RAW_MIXED_CORPUS_MATERIALIZE_MODE = "raw_mixed_existing_source_materialization_entry"
RAW_MIXED_CORPUS_MATERIALIZE_STATE = "materialized"
RAW_MIXED_CORPUS_MATERIALIZE_NEXT_ACTION = "run_layer3_preflight_with_materialized_source_ids"
RAW_MIXED_CORPUS_MATERIALIZE_ALLOWED_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "client_request_id",
        "materialization_mode",
        "corpus_batch_id",
        "artifact_manifest_ref",
        "artifact_manifest_hash",
        "requested_source_classes",
        "operator_confirmation",
    }
)


def materialize_raw_mixed_corpus(payload: Mapping[str, Any], db: Session) -> dict[str, Any]:
    blocked = _blocked_request_fields(payload)
    if blocked:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_scope_not_admitted",
            "Raw mixed corpus materialization received fields outside the admitted boundary.",
            status="blocked",
            blocked_fields=blocked,
            next_allowed_actions=["remove_non_admitted_raw_mixed_materialization_fields"],
        )

    request_id = _required_string(payload, "client_request_id")
    mode = _required_string(payload, "materialization_mode")
    if mode != RAW_MIXED_CORPUS_MATERIALIZE_MODE:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_mode_not_admitted",
            "materialization_mode must be raw_mixed_existing_source_materialization_entry.",
            status="blocked",
            blocked_fields=["materialization_mode"],
            next_allowed_actions=["submit_raw_mixed_existing_source_materialization_entry"],
        )
    if payload.get("operator_confirmation") is not True:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_operator_confirmation_required",
            "operator_confirmation must be true for raw mixed corpus materialization.",
            status="blocked",
            blocked_fields=["operator_confirmation"],
            next_allowed_actions=["confirm_raw_mixed_materialization_authority"],
        )

    requested_source_classes = _unique_strings(payload.get("requested_source_classes"), "requested_source_classes")
    unsupported = unsupported_requested(requested_source_classes)
    if unsupported:
        raise Layer3WorkbenchError(
            "unsupported_raw_mixed_materialize_source_class",
            f"Unsupported raw mixed materialization source class requested: {', '.join(unsupported)}.",
            status="blocked",
            blocked_fields=["requested_source_classes"],
            next_allowed_actions=["choose_supported_raw_mixed_materialization_sources"],
        )
    if set(requested_source_classes) != set(RAW_MIXED_CORPUS_SOURCE_CLASSES):
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_source_classes_required",
            "Raw mixed corpus materialization requires dataset_version and aps_content_document source classes.",
            status="blocked",
            blocked_fields=["requested_source_classes"],
            next_allowed_actions=["submit_dataset_version_and_aps_content_document_sources"],
        )

    corpus_batch_id = _required_string(payload, "corpus_batch_id")
    manifest_ref = _required_string(payload, "artifact_manifest_ref")
    manifest_hash = _required_sha256(payload, "artifact_manifest_hash")
    manifest = _load_manifest(manifest_ref=manifest_ref, manifest_hash=manifest_hash)
    _validate_manifest_header(manifest, corpus_batch_id=corpus_batch_id)

    written = {
        "datasets": 0,
        "dataset_versions": 0,
        "variables": 0,
        "dataset_rows": 0,
        "variable_profiles": 0,
        "dataset_source_provenance": 0,
        "connector_runs": 0,
        "connector_run_targets": 0,
        "aps_content_documents": 0,
        "aps_content_chunks": 0,
        "aps_content_linkages": 0,
    }
    dataset_version_ids: list[str] = []
    aps_content_document_ids: list[str] = []

    try:
        with db.begin_nested():
            for entry in _required_list(manifest.get("dataset_versions"), "artifact_manifest.dataset_versions"):
                dataset_version_ids.append(_materialize_dataset_version(db, entry, written))
            for entry in _required_list(
                manifest.get("aps_content_documents"),
                "artifact_manifest.aps_content_documents",
            ):
                aps_content_document_ids.append(_materialize_aps_content_document(db, entry, written))
        db.commit()
    except Layer3WorkbenchError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise Layer3WorkbenchError(
            "raw_mixed_materialization_failed",
            "Raw mixed corpus materialization failed before commit.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
        ) from exc

    source_materialization_id = stable_id(
        "raw-mixed-materialization",
        {
            "request_id": request_id,
            "mode": mode,
            "corpus_batch_id": corpus_batch_id,
            "artifact_manifest_ref": manifest_ref,
            "artifact_manifest_hash": manifest_hash,
            "dataset_version_ids": sorted(dataset_version_ids),
            "aps_content_document_ids": sorted(aps_content_document_ids),
        },
    )
    return {
        **base_response(RAW_MIXED_CORPUS_MATERIALIZE_RESPONSE_SCHEMA_ID, request_id=request_id),
        "source_materialization_id": source_materialization_id,
        "materialization_mode": RAW_MIXED_CORPUS_MATERIALIZE_MODE,
        "source_materialization_state": RAW_MIXED_CORPUS_MATERIALIZE_STATE,
        "dataset_version_ids": dataset_version_ids,
        "aps_content_document_ids": aps_content_document_ids,
        "source_classes": list(RAW_MIXED_CORPUS_SOURCE_CLASSES),
        "artifact_manifest_ref": manifest_ref,
        "artifact_manifest_hash": manifest_hash,
        "database_rows_written": written,
        "files_written": [],
        "layer3_flow_started": False,
        "next_allowed_actions": [RAW_MIXED_CORPUS_MATERIALIZE_NEXT_ACTION],
    }


def _materialize_dataset_version(db: Session, entry: Mapping[str, Any], written: dict[str, int]) -> str:
    dataset_id = _entry_string(entry, "dataset_id", "artifact_manifest.dataset_versions[].dataset_id")
    dataset_version_id = _entry_string(
        entry,
        "dataset_version_id",
        "artifact_manifest.dataset_versions[].dataset_version_id",
    )
    storage_ref = _entry_string(entry, "storage_ref", "artifact_manifest.dataset_versions[].storage_ref")
    storage_hash = _entry_sha256(entry, "storage_sha256", "artifact_manifest.dataset_versions[].storage_sha256")
    _check_storage_ref(storage_ref, storage_hash, "artifact_manifest.dataset_versions[].storage_ref")

    dataset_values = {
        "name": str(entry.get("name") or f"Dataset {dataset_id}"),
        "description": entry.get("description"),
        "domain_pack": entry.get("domain_pack"),
        "frequency_hint": entry.get("frequency_hint"),
        "time_column": entry.get("time_column"),
    }
    if _ensure_row(db, Dataset, dataset_id, "dataset_id", dataset_values):
        written["datasets"] += 1

    version_values = {
        "dataset_id": dataset_id,
        "parent_version_id": entry.get("parent_version_id"),
        "version_label": str(entry.get("version_label") or "v1"),
        "version_type": str(entry.get("version_type") or "raw_mixed_materialized"),
        "status": str(entry.get("status") or "ready"),
        "storage_ref": storage_ref,
        "row_count": int(entry.get("row_count") or 0),
        "notes": entry.get("notes"),
    }
    if _ensure_row(db, DatasetVersion, dataset_version_id, "dataset_version_id", version_values):
        written["dataset_versions"] += 1

    for variable in _required_list(entry.get("variables"), "artifact_manifest.dataset_versions[].variables"):
        variable_id = _entry_string(variable, "variable_id", "artifact_manifest.dataset_versions[].variables[].variable_id")
        variable_name = _entry_string(
            variable,
            "variable_name",
            "artifact_manifest.dataset_versions[].variables[].variable_name",
        )
        _ensure_unique_identity(
            db,
            VariableDefinition,
            variable_id,
            "variable_id",
            {"dataset_version_id": dataset_version_id, "variable_name": variable_name},
        )
        variable_values = {
            "dataset_version_id": dataset_version_id,
            "variable_name": variable_name,
            "dtype": str(variable.get("dtype") or "string"),
            "role": str(variable.get("role") or "measure"),
            "is_numeric": bool(variable.get("is_numeric", False)),
            "is_time_index": bool(variable.get("is_time_index", False)),
            "ordinal_position": int(variable.get("ordinal_position") or 0),
        }
        if _ensure_row(db, VariableDefinition, variable_id, "variable_id", variable_values):
            written["variables"] += 1

    for row in _required_list(entry.get("rows"), "artifact_manifest.dataset_versions[].rows"):
        row_id = _entry_string(row, "dataset_row_id", "artifact_manifest.dataset_versions[].rows[].dataset_row_id")
        _ensure_unique_identity(
            db,
            DatasetRow,
            row_id,
            "dataset_row_id",
            {"dataset_version_id": dataset_version_id, "row_number": int(row.get("row_number") or 0)},
        )
        row_values = {
            "dataset_version_id": dataset_version_id,
            "row_number": int(row.get("row_number") or 0),
            "observed_at": _parse_datetime(row.get("observed_at")),
            "values_json": dict(row.get("values_json") or {}),
        }
        if _ensure_row(db, DatasetRow, row_id, "dataset_row_id", row_values):
            written["dataset_rows"] += 1

    for profile in entry.get("variable_profiles") or []:
        profile_id = _entry_string(
            profile,
            "variable_profile_id",
            "artifact_manifest.dataset_versions[].variable_profiles[].variable_profile_id",
        )
        profile_values = {
            "dataset_version_id": dataset_version_id,
            "variable_id": _entry_string(
                profile,
                "variable_id",
                "artifact_manifest.dataset_versions[].variable_profiles[].variable_id",
            ),
            "seasonality_flag": profile.get("seasonality_flag"),
            "stationarity_hint": profile.get("stationarity_hint"),
            "summary_json": dict(profile.get("summary_json") or {}),
        }
        if _ensure_row(db, VariableProfile, profile_id, "variable_profile_id", profile_values):
            written["variable_profiles"] += 1

    provenance = _required_mapping(
        entry.get("source_provenance"),
        "artifact_manifest.dataset_versions[].source_provenance",
    )
    provenance_id = _entry_string(provenance, "dataset_source_provenance_id", "source_provenance.dataset_source_provenance_id")
    provenance_values = {
        "dataset_version_id": dataset_version_id,
        "connector_run_id": provenance.get("connector_run_id"),
        "source_system": str(provenance.get("source_system") or "nrc_adams_aps"),
        "source_mode": str(provenance.get("source_mode") or "raw_mixed_materialized"),
        "source_artifact_key": _entry_string(provenance, "source_artifact_key", "source_provenance.source_artifact_key"),
        "artifact_surface": provenance.get("artifact_surface") or "dataset_version",
        "artifact_locator_type": provenance.get("artifact_locator_type") or "server_owned_ref",
        "downloaded_sha256": storage_hash,
        "raw_storage_ref": storage_ref,
        "source_reference_json": dict(provenance.get("source_reference_json") or {}),
        "fetch_policy_mode": provenance.get("fetch_policy_mode") or "server_owned_manifest",
    }
    if _ensure_row(db, DatasetSourceProvenance, provenance_id, "dataset_source_provenance_id", provenance_values):
        written["dataset_source_provenance"] += 1

    return dataset_version_id


def _materialize_aps_content_document(db: Session, entry: Mapping[str, Any], written: dict[str, int]) -> str:
    run = _required_mapping(entry.get("connector_run"), "artifact_manifest.aps_content_documents[].connector_run")
    run_id = _entry_string(run, "connector_run_id", "connector_run.connector_run_id")
    run_values = {
        "connector_key": str(run.get("connector_key") or "nrc_adams_aps"),
        "source_system": str(run.get("source_system") or "nrc_adams_aps"),
        "source_mode": str(run.get("source_mode") or "server_owned_manifest"),
        "status": str(run.get("status") or "completed"),
        "request_config_json": dict(run.get("request_config_json") or {}),
        "query_plan_json": dict(run.get("query_plan_json") or {}),
    }
    if _ensure_row(db, ConnectorRun, run_id, "connector_run_id", run_values):
        written["connector_runs"] += 1

    target = _required_mapping(entry.get("target"), "artifact_manifest.aps_content_documents[].target")
    target_id = _entry_string(target, "connector_run_target_id", "target.connector_run_target_id")
    target_values = {
        "connector_run_id": run_id,
        "ordinal": int(target.get("ordinal") or 0),
        "artifact_surface": str(target.get("artifact_surface") or "files"),
        "selection_source": target.get("selection_source"),
        "selection_scope": target.get("selection_scope"),
        "artifact_locator_type": target.get("artifact_locator_type") or "server_owned_ref",
        "source_artifact_key": target.get("source_artifact_key"),
        "canonical_artifact_key": target.get("canonical_artifact_key"),
        "downloaded_sha256": target.get("downloaded_sha256"),
        "raw_storage_ref": target.get("raw_storage_ref"),
        "fetch_policy_mode": target.get("fetch_policy_mode") or "server_owned_manifest",
        "status": str(target.get("status") or "completed"),
    }
    if _ensure_row(db, ConnectorRunTarget, target_id, "connector_run_target_id", target_values):
        written["connector_run_targets"] += 1

    document = _required_mapping(entry.get("document"), "artifact_manifest.aps_content_documents[].document")
    content_id = _entry_string(document, "content_id", "document.content_id")
    document_id = str(document.get("aps_content_document_id") or stable_id("aps-doc", content_id))
    normalized_hash = _entry_sha256(document, "normalized_text_sha256", "document.normalized_text_sha256")
    _ensure_unique_identity(
        db,
        ApsContentDocument,
        document_id,
        "aps_content_document_id",
        {
            "content_id": content_id,
            "content_contract_id": _entry_string(document, "content_contract_id", "document.content_contract_id"),
            "chunking_contract_id": _entry_string(document, "chunking_contract_id", "document.chunking_contract_id"),
        },
    )
    document_values = {
        "content_id": content_id,
        "content_contract_id": _entry_string(document, "content_contract_id", "document.content_contract_id"),
        "chunking_contract_id": _entry_string(document, "chunking_contract_id", "document.chunking_contract_id"),
        "normalization_contract_id": document.get("normalization_contract_id"),
        "normalized_text_sha256": normalized_hash,
        "normalized_char_count": int(document.get("normalized_char_count") or 0),
        "chunk_count": int(document.get("chunk_count") or 0),
        "content_status": str(document.get("content_status") or "indexed"),
        "media_type": document.get("media_type"),
        "document_class": document.get("document_class"),
        "quality_status": document.get("quality_status"),
        "page_count": int(document.get("page_count") or 0),
        "diagnostics_ref": document.get("diagnostics_ref"),
        "visual_page_refs_json": json.dumps(document.get("visual_page_refs_json") or []),
    }
    if _ensure_row(db, ApsContentDocument, document_id, "aps_content_document_id", document_values):
        written["aps_content_documents"] += 1

    for chunk in _required_list(entry.get("chunks"), "artifact_manifest.aps_content_documents[].chunks"):
        chunk_id = _entry_string(chunk, "aps_content_chunk_id", "chunks[].aps_content_chunk_id")
        chunk_text = str(chunk.get("chunk_text") or "")
        chunk_lookup = {
            "content_id": content_id,
            "chunk_id": _entry_string(chunk, "chunk_id", "chunks[].chunk_id"),
            "content_contract_id": document_values["content_contract_id"],
            "chunking_contract_id": document_values["chunking_contract_id"],
        }
        _ensure_unique_identity(db, ApsContentChunk, chunk_id, "aps_content_chunk_id", chunk_lookup)
        chunk_values = {
            "content_id": content_id,
            "chunk_id": chunk_lookup["chunk_id"],
            "content_contract_id": document_values["content_contract_id"],
            "chunking_contract_id": document_values["chunking_contract_id"],
            "chunk_ordinal": int(chunk.get("chunk_ordinal") or 0),
            "start_char": int(chunk.get("start_char") or 0),
            "end_char": int(chunk.get("end_char") or len(chunk_text)),
            "chunk_text": chunk_text,
            "chunk_text_sha256": _entry_sha256(chunk, "chunk_text_sha256", "chunks[].chunk_text_sha256"),
            "page_start": chunk.get("page_start"),
            "page_end": chunk.get("page_end"),
            "unit_kind": chunk.get("unit_kind"),
            "quality_status": chunk.get("quality_status"),
        }
        expected = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
        if chunk_values["chunk_text_sha256"] != expected:
            raise Layer3WorkbenchError(
                "raw_mixed_materialize_chunk_hash_mismatch",
                "APS chunk text hash does not match manifest chunk_text.",
                status="conflict",
                http_status=409,
                blocked_fields=["artifact_manifest.aps_content_documents[].chunks"],
            )
        if _ensure_row(db, ApsContentChunk, chunk_id, "aps_content_chunk_id", chunk_values):
            written["aps_content_chunks"] += 1

    linkage = _required_mapping(entry.get("linkage"), "artifact_manifest.aps_content_documents[].linkage")
    linkage_id = _entry_string(linkage, "aps_content_linkage_id", "linkage.aps_content_linkage_id")
    normalized_ref = _entry_string(linkage, "normalized_text_ref", "linkage.normalized_text_ref")
    blob_ref = _entry_string(linkage, "blob_ref", "linkage.blob_ref")
    _check_storage_ref(normalized_ref, normalized_hash, "linkage.normalized_text_ref")
    blob_hash = _entry_sha256(linkage, "blob_sha256", "linkage.blob_sha256")
    _check_storage_ref(blob_ref, blob_hash, "linkage.blob_ref")
    _ensure_unique_identity(
        db,
        ApsContentLinkage,
        linkage_id,
        "aps_content_linkage_id",
        {
            "content_id": content_id,
            "run_id": run_id,
            "target_id": target_id,
            "content_contract_id": document_values["content_contract_id"],
            "chunking_contract_id": document_values["chunking_contract_id"],
        },
    )
    linkage_values = {
        "content_id": content_id,
        "run_id": run_id,
        "target_id": target_id,
        "accession_number": linkage.get("accession_number"),
        "content_contract_id": document_values["content_contract_id"],
        "chunking_contract_id": document_values["chunking_contract_id"],
        "content_units_ref": linkage.get("content_units_ref"),
        "normalized_text_ref": normalized_ref,
        "normalized_text_sha256": normalized_hash,
        "blob_ref": blob_ref,
        "blob_sha256": blob_hash,
        "download_exchange_ref": linkage.get("download_exchange_ref"),
        "discovery_ref": linkage.get("discovery_ref"),
        "selection_ref": linkage.get("selection_ref"),
        "diagnostics_ref": linkage.get("diagnostics_ref"),
    }
    if _ensure_row(db, ApsContentLinkage, linkage_id, "aps_content_linkage_id", linkage_values):
        written["aps_content_linkages"] += 1
    return content_id


def _blocked_request_fields(payload: Mapping[str, Any]) -> list[str]:
    blocked = sorted(key for key in payload if key not in RAW_MIXED_CORPUS_MATERIALIZE_ALLOWED_FIELDS)
    blocked.extend(sorted(key for key in payload if key in RAW_MIXED_CORPUS_FORBIDDEN_FIELDS and key not in blocked))
    return sorted(set(blocked))


def _load_manifest(*, manifest_ref: str, manifest_hash: str) -> dict[str, Any]:
    manifest_path = _server_owned_path(manifest_ref, "artifact_manifest_ref")
    manifest_bytes = manifest_path.read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != manifest_hash:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_manifest_hash_mismatch",
            "artifact_manifest_hash does not match the server-owned materialization manifest.",
            status="conflict",
            http_status=409,
            blocked_fields=["artifact_manifest_hash"],
            next_allowed_actions=["refresh_raw_mixed_materialization_manifest_hash"],
        )
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_manifest_malformed",
            "artifact_manifest_ref must point to a UTF-8 JSON materialization manifest.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
        ) from exc
    if not isinstance(manifest, dict):
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_manifest_malformed",
            "artifact_manifest_ref must point to a JSON object materialization manifest.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
        )
    blocked = _blocked_manifest_paths(manifest)
    if blocked:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_manifest_scope_not_admitted",
            "Raw mixed corpus materialization manifest includes non-admitted capability fields.",
            status="blocked",
            blocked_fields=blocked,
            next_allowed_actions=["remove_non_admitted_manifest_fields"],
        )
    return manifest


def _validate_manifest_header(manifest: Mapping[str, Any], *, corpus_batch_id: str) -> None:
    if str(manifest.get("schema_id") or "").strip() != RAW_MIXED_CORPUS_MATERIALIZE_MANIFEST_SCHEMA_ID:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_manifest_schema_not_admitted",
            "Raw mixed corpus materialization manifest schema is not admitted.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
            next_allowed_actions=["submit_raw_mixed_materialization_manifest_v1"],
        )
    if str(manifest.get("corpus_batch_id") or "").strip() != corpus_batch_id:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_manifest_batch_mismatch",
            "Materialization manifest corpus_batch_id does not match the request.",
            status="conflict",
            http_status=409,
            blocked_fields=["corpus_batch_id", "artifact_manifest_ref"],
        )
    source_classes = _unique_strings(manifest.get("source_classes"), "artifact_manifest.source_classes")
    if set(source_classes) != set(RAW_MIXED_CORPUS_SOURCE_CLASSES):
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_manifest_source_classes_mismatch",
            "Materialization manifest must declare dataset_version and aps_content_document source classes.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
        )


def _ensure_row(
    db: Session,
    model: type[Any],
    identity: str,
    identity_field: str,
    values: Mapping[str, Any],
) -> bool:
    existing = db.get(model, identity)
    if existing is None:
        db.add(model(**{identity_field: identity}, **dict(values)))
        return True
    mismatched = [
        field
        for field, expected in values.items()
        if not _same_value(getattr(existing, field), expected)
    ]
    if mismatched:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_existing_authority_mismatch",
            f"Existing {model.__name__} row conflicts with the materialization manifest.",
            status="conflict",
            http_status=409,
            blocked_fields=[f"{model.__tablename__}.{field}" for field in mismatched],
            next_allowed_actions=["use_matching_materialization_manifest_authority"],
        )
    return False


def _ensure_unique_identity(
    db: Session,
    model: type[Any],
    identity: str,
    identity_field: str,
    lookup: Mapping[str, Any],
) -> None:
    existing = db.query(model).filter_by(**dict(lookup)).one_or_none()
    if existing is None or getattr(existing, identity_field) == identity:
        return
    blocked = [f"{model.__tablename__}.{field}" for field in lookup]
    blocked.append(f"{model.__tablename__}.{identity_field}")
    raise Layer3WorkbenchError(
        "raw_mixed_materialize_existing_authority_mismatch",
        f"Existing {model.__name__} row conflicts with the materialization manifest deterministic identity.",
        status="conflict",
        http_status=409,
        blocked_fields=blocked,
        next_allowed_actions=["use_matching_materialization_manifest_authority"],
    )


def _same_value(actual: Any, expected: Any) -> bool:
    if isinstance(actual, datetime) and isinstance(expected, datetime):
        return actual.isoformat() == expected.isoformat()
    return actual == expected


def _check_storage_ref(ref: str, expected_sha256: str, field: str) -> None:
    path = _server_owned_path(ref, field)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_storage_hash_mismatch",
            "Server-owned storage ref hash does not match the materialization manifest.",
            status="conflict",
            http_status=409,
            blocked_fields=[field],
            next_allowed_actions=["refresh_raw_mixed_materialization_storage_hash"],
        )


def _server_owned_path(ref: str, field: str) -> Path:
    storage_root = Path(settings.storage_dir).resolve(strict=False)
    requested = Path(ref)
    candidate = requested if requested.is_absolute() else storage_root / requested
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(storage_root)
    except ValueError as exc:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_ref_not_server_owned",
            "Raw mixed materialization refs must point under the server-owned storage root.",
            status="blocked",
            blocked_fields=[field],
            next_allowed_actions=["submit_server_owned_materialization_refs"],
        ) from exc
    if not resolved.is_file():
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_ref_not_found",
            "Raw mixed materialization ref was not found under the server-owned storage root.",
            status="blocked",
            http_status=404,
            blocked_fields=[field],
            next_allowed_actions=["prepare_server_owned_materialization_ref"],
        )
    return resolved


def _blocked_manifest_paths(value: Any, *, prefix: str = "artifact_manifest") -> list[str]:
    blocked: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = f"{prefix}.{key}"
            if str(key) in RAW_MIXED_CORPUS_FORBIDDEN_FIELDS:
                blocked.append(path)
            blocked.extend(_blocked_manifest_paths(child, prefix=path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            blocked.extend(_blocked_manifest_paths(child, prefix=f"{prefix}[{index}]"))
    return sorted(blocked)


def _required_string(payload: Mapping[str, Any], field: str) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_required_field_missing",
            f"{field} is required for raw mixed corpus materialization.",
            status="blocked",
            blocked_fields=[field],
        )
    return value


def _required_sha256(payload: Mapping[str, Any], field: str) -> str:
    value = _required_string(payload, field)
    if len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_hash_invalid",
            f"{field} must be a SHA-256 hex digest.",
            status="blocked",
            blocked_fields=[field],
            next_allowed_actions=["submit_sha256_materialization_hash"],
        )
    return value.lower()


def _unique_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_list_required",
            f"{field} must be a non-empty list of strings.",
            status="blocked",
            blocked_fields=[field],
        )
    result: list[str] = []
    for item in value:
        normalized = str(item or "").strip()
        if normalized and normalized not in result:
            result.append(normalized)
    if not result:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_list_required",
            f"{field} must be a non-empty list of strings.",
            status="blocked",
            blocked_fields=[field],
        )
    return result


def _required_list(value: Any, field: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_list_required",
            f"{field} must be a non-empty list.",
            status="blocked",
            blocked_fields=[field],
        )
    if not all(isinstance(item, Mapping) for item in value):
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_list_required",
            f"{field} must contain JSON objects.",
            status="blocked",
            blocked_fields=[field],
        )
    return value


def _required_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_object_required",
            f"{field} must be a JSON object.",
            status="blocked",
            blocked_fields=[field],
        )
    return value


def _entry_string(entry: Mapping[str, Any], key: str, field: str) -> str:
    value = str(entry.get(key) or "").strip()
    if not value:
        raise Layer3WorkbenchError(
            "raw_mixed_materialize_required_field_missing",
            f"{field} is required for raw mixed corpus materialization.",
            status="blocked",
            blocked_fields=[field],
        )
    return value


def _entry_sha256(entry: Mapping[str, Any], key: str, field: str) -> str:
    return _required_sha256({field: entry.get(key)}, field)


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
