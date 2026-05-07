from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    ApsContentDocument,
    ApsContentLinkage,
    ConnectorRun,
    ConnectorRunTarget,
    DatasetSourceProvenance,
    DatasetVersion,
)
from app.services.layer3_response_contract import base_response
from app.services.layer3_source_boundary import unsupported_requested
from app.services.layer3_utils import stable_id
from app.services.layer3_workbench_error import Layer3WorkbenchError


RAW_MIXED_CORPUS_SEED_REQUEST_SCHEMA_ID = "layer3.raw_mixed_corpus_seed_request.v1"
RAW_MIXED_CORPUS_SEED_RESPONSE_SCHEMA_ID = "layer3.raw_mixed_corpus_seed_result.v1"
RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID = "layer3.raw_mixed_corpus_seed_manifest.v1"
RAW_MIXED_CORPUS_SEED_MODE = "raw_mixed_corpus_bridge_seed_only"
RAW_MIXED_CORPUS_SEED_STATE = "seeded"
RAW_MIXED_CORPUS_NEXT_ACTION = "run_layer3_preflight_with_seeded_source_ids"
RAW_MIXED_CORPUS_SOURCE_CLASSES = ("dataset_version", "aps_content_document")
RAW_MIXED_CORPUS_ALLOWED_FIELDS = frozenset(
    {
        "schema_id",
        "schema_version",
        "client_request_id",
        "seed_mode",
        "corpus_batch_id",
        "aps_run_id",
        "target_ids",
        "artifact_manifest_ref",
        "artifact_manifest_hash",
        "requested_source_classes",
        "operator_confirmation",
    }
)
RAW_MIXED_CORPUS_FORBIDDEN_FIELDS = frozenset(
    {
        "source_upload",
        "local_upload",
        "local_directory",
        "local_path",
        "directory_path",
        "broad_file_upload",
        "file_bytes",
        "file_glob",
        "web_connector",
        "connector_key",
        "connector_secret",
        "source_url",
        "provider_url",
        "public_url",
        "rag_vector_index",
        "rag_plan",
        "vector_plan",
        "embedding_model",
        "runtime_db_write",
        "unbounded_runtime_db",
        "package_payload",
        "rebuild_package",
        "rewrite_output",
        "destination_id",
        "destination_url",
        "hidden_llm_planning",
        "mockup_activation",
        "auth_policy_override",
    }
)


def seed_raw_mixed_corpus(payload: Mapping[str, Any], db: Session) -> dict[str, Any]:
    blocked = _blocked_request_fields(payload)
    if blocked:
        raise Layer3WorkbenchError(
            "raw_mixed_seed_scope_not_admitted",
            "Raw mixed corpus seeding received fields outside the seed-only bridge boundary.",
            status="blocked",
            blocked_fields=blocked,
            next_allowed_actions=["remove_non_admitted_raw_mixed_seed_fields"],
        )

    request_id = _required_string(payload, "client_request_id")
    seed_mode = _required_string(payload, "seed_mode")
    if seed_mode != RAW_MIXED_CORPUS_SEED_MODE:
        raise Layer3WorkbenchError(
            "raw_mixed_seed_mode_not_admitted",
            "seed_mode must be raw_mixed_corpus_bridge_seed_only.",
            status="blocked",
            blocked_fields=["seed_mode"],
            next_allowed_actions=["submit_raw_mixed_corpus_bridge_seed_only"],
        )
    if payload.get("operator_confirmation") is not True:
        raise Layer3WorkbenchError(
            "raw_mixed_seed_operator_confirmation_required",
            "operator_confirmation must be true for raw mixed corpus seeding.",
            status="blocked",
            blocked_fields=["operator_confirmation"],
            next_allowed_actions=["confirm_seed_only_source_authority"],
        )

    requested_source_classes = _unique_strings(payload.get("requested_source_classes"), "requested_source_classes")
    unsupported = unsupported_requested(requested_source_classes)
    if unsupported:
        raise Layer3WorkbenchError(
            "unsupported_raw_mixed_source_class",
            f"Unsupported raw mixed source class requested: {', '.join(unsupported)}.",
            status="blocked",
            blocked_fields=["requested_source_classes"],
            next_allowed_actions=["choose_supported_raw_mixed_seed_sources"],
        )
    if set(requested_source_classes) != set(RAW_MIXED_CORPUS_SOURCE_CLASSES):
        raise Layer3WorkbenchError(
            "raw_mixed_source_classes_required",
            "Raw mixed corpus seeding requires dataset_version and aps_content_document source classes.",
            status="blocked",
            blocked_fields=["requested_source_classes"],
            next_allowed_actions=["submit_dataset_version_and_aps_content_document_sources"],
        )

    corpus_batch_id = _required_string(payload, "corpus_batch_id")
    aps_run_id = _required_string(payload, "aps_run_id")
    target_ids = _unique_strings(payload.get("target_ids"), "target_ids")
    artifact_manifest_ref = _required_string(payload, "artifact_manifest_ref")
    artifact_manifest_hash = _required_sha256(payload, "artifact_manifest_hash")
    manifest = _load_seed_manifest(
        artifact_manifest_ref=artifact_manifest_ref,
        artifact_manifest_hash=artifact_manifest_hash,
    )
    _validate_manifest_payload(
        manifest,
        corpus_batch_id=corpus_batch_id,
        aps_run_id=aps_run_id,
        target_ids=target_ids,
    )

    dataset_version_ids = _unique_strings(manifest.get("dataset_version_ids"), "artifact_manifest.dataset_version_ids")
    aps_content_document_ids = _unique_strings(
        manifest.get("aps_content_document_ids"),
        "artifact_manifest.aps_content_document_ids",
    )
    if not dataset_version_ids or not aps_content_document_ids:
        raise Layer3WorkbenchError(
            "raw_mixed_manifest_sources_required",
            "Raw mixed corpus seed manifest must name dataset_version and aps_content_document source ids.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
            next_allowed_actions=["submit_mixed_source_manifest"],
        )

    _validate_aps_run_and_targets(db, aps_run_id=aps_run_id, target_ids=target_ids)
    _validate_dataset_versions(db, dataset_version_ids=dataset_version_ids, aps_run_id=aps_run_id)
    _validate_aps_content_documents(
        db,
        aps_content_document_ids=aps_content_document_ids,
        aps_run_id=aps_run_id,
        target_ids=target_ids,
    )

    source_seed_id = stable_id(
        "raw-mixed-seed",
        {
            "request_id": request_id,
            "seed_mode": seed_mode,
            "corpus_batch_id": corpus_batch_id,
            "artifact_manifest_ref": artifact_manifest_ref,
            "artifact_manifest_hash": artifact_manifest_hash,
            "dataset_version_ids": sorted(dataset_version_ids),
            "aps_content_document_ids": sorted(aps_content_document_ids),
        },
    )
    return {
        **base_response(RAW_MIXED_CORPUS_SEED_RESPONSE_SCHEMA_ID, request_id=request_id),
        "source_seed_id": source_seed_id,
        "seed_mode": RAW_MIXED_CORPUS_SEED_MODE,
        "source_seed_state": RAW_MIXED_CORPUS_SEED_STATE,
        "dataset_version_ids": dataset_version_ids,
        "aps_content_document_ids": aps_content_document_ids,
        "source_classes": list(RAW_MIXED_CORPUS_SOURCE_CLASSES),
        "artifact_manifest_ref": artifact_manifest_ref,
        "artifact_manifest_hash": artifact_manifest_hash,
        "layer3_flow_started": False,
        "next_allowed_actions": [RAW_MIXED_CORPUS_NEXT_ACTION],
    }


def _blocked_request_fields(payload: Mapping[str, Any]) -> list[str]:
    blocked = sorted(key for key in payload if key not in RAW_MIXED_CORPUS_ALLOWED_FIELDS)
    blocked.extend(sorted(key for key in payload if key in RAW_MIXED_CORPUS_FORBIDDEN_FIELDS and key not in blocked))
    return sorted(set(blocked))


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
            "raw_mixed_seed_required_field_missing",
            f"{field} is required for raw mixed corpus seeding.",
            status="blocked",
            blocked_fields=[field],
        )
    return value


def _required_sha256(payload: Mapping[str, Any], field: str) -> str:
    value = _required_string(payload, field)
    if len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise Layer3WorkbenchError(
            "raw_mixed_artifact_manifest_hash_invalid",
            "artifact_manifest_hash must be a SHA-256 hex digest.",
            status="blocked",
            blocked_fields=[field],
            next_allowed_actions=["submit_sha256_manifest_hash"],
        )
    return value.lower()


def _unique_strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise Layer3WorkbenchError(
            "raw_mixed_seed_list_required",
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
            "raw_mixed_seed_list_required",
            f"{field} must be a non-empty list of strings.",
            status="blocked",
            blocked_fields=[field],
        )
    return result


def _load_seed_manifest(*, artifact_manifest_ref: str, artifact_manifest_hash: str) -> dict[str, Any]:
    manifest_path = _server_owned_manifest_path(artifact_manifest_ref)
    manifest_bytes = manifest_path.read_bytes()
    actual_hash = hashlib.sha256(manifest_bytes).hexdigest()
    if actual_hash != artifact_manifest_hash:
        raise Layer3WorkbenchError(
            "raw_mixed_artifact_manifest_hash_mismatch",
            "artifact_manifest_hash does not match the server-owned raw mixed corpus seed manifest.",
            status="conflict",
            http_status=409,
            blocked_fields=["artifact_manifest_hash"],
            next_allowed_actions=["refresh_raw_mixed_seed_manifest_hash"],
        )
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Layer3WorkbenchError(
            "raw_mixed_artifact_manifest_malformed",
            "artifact_manifest_ref must point to a UTF-8 JSON seed manifest.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
        ) from exc
    if not isinstance(manifest, dict):
        raise Layer3WorkbenchError(
            "raw_mixed_artifact_manifest_malformed",
            "artifact_manifest_ref must point to a JSON object seed manifest.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
        )
    blocked = _blocked_manifest_paths(manifest)
    if blocked:
        raise Layer3WorkbenchError(
            "raw_mixed_seed_manifest_scope_not_admitted",
            "Raw mixed corpus seed manifest includes non-admitted capability fields.",
            status="blocked",
            blocked_fields=blocked,
            next_allowed_actions=["remove_non_admitted_manifest_fields"],
        )
    return manifest


def _server_owned_manifest_path(artifact_manifest_ref: str) -> Path:
    storage_root = Path(settings.storage_dir).resolve(strict=False)
    requested = Path(artifact_manifest_ref)
    candidate = requested if requested.is_absolute() else storage_root / requested
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(storage_root)
    except ValueError as exc:
        raise Layer3WorkbenchError(
            "raw_mixed_manifest_ref_not_server_owned",
            "artifact_manifest_ref must point under the server-owned storage root.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
            next_allowed_actions=["submit_server_owned_artifact_manifest_ref"],
        ) from exc
    if not resolved.is_file():
        raise Layer3WorkbenchError(
            "raw_mixed_manifest_ref_not_found",
            "artifact_manifest_ref was not found as a server-owned manifest file.",
            status="blocked",
            http_status=404,
            blocked_fields=["artifact_manifest_ref"],
            next_allowed_actions=["materialize_server_owned_seed_manifest"],
        )
    return resolved


def _validate_manifest_payload(
    manifest: Mapping[str, Any],
    *,
    corpus_batch_id: str,
    aps_run_id: str,
    target_ids: list[str],
) -> None:
    schema_id = str(manifest.get("schema_id") or "").strip()
    if schema_id != RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID:
        raise Layer3WorkbenchError(
            "raw_mixed_manifest_schema_not_admitted",
            "Raw mixed corpus seed manifest schema is not admitted.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
            next_allowed_actions=["submit_raw_mixed_seed_manifest_v1"],
        )
    _validate_manifest_match(manifest, "corpus_batch_id", corpus_batch_id)
    _validate_manifest_match(manifest, "aps_run_id", aps_run_id)
    manifest_target_ids = _unique_strings(manifest.get("target_ids"), "artifact_manifest.target_ids")
    if sorted(manifest_target_ids) != sorted(target_ids):
        raise Layer3WorkbenchError(
            "raw_mixed_manifest_target_mismatch",
            "Seed manifest target_ids do not match the request.",
            status="conflict",
            http_status=409,
            blocked_fields=["target_ids", "artifact_manifest_ref"],
            next_allowed_actions=["refresh_raw_mixed_seed_manifest"],
        )
    manifest_source_classes = _unique_strings(manifest.get("source_classes"), "artifact_manifest.source_classes")
    if set(manifest_source_classes) != set(RAW_MIXED_CORPUS_SOURCE_CLASSES):
        raise Layer3WorkbenchError(
            "raw_mixed_manifest_source_classes_mismatch",
            "Seed manifest must declare dataset_version and aps_content_document source classes.",
            status="blocked",
            blocked_fields=["artifact_manifest_ref"],
            next_allowed_actions=["submit_mixed_source_manifest"],
        )


def _validate_manifest_match(manifest: Mapping[str, Any], field: str, expected: str) -> None:
    actual = str(manifest.get(field) or "").strip()
    if actual != expected:
        raise Layer3WorkbenchError(
            f"raw_mixed_manifest_{field}_mismatch",
            f"Seed manifest {field} does not match the request.",
            status="conflict",
            http_status=409,
            blocked_fields=[field, "artifact_manifest_ref"],
            next_allowed_actions=["refresh_raw_mixed_seed_manifest"],
        )


def _validate_aps_run_and_targets(db: Session, *, aps_run_id: str, target_ids: list[str]) -> None:
    if db.get(ConnectorRun, aps_run_id) is None:
        raise Layer3WorkbenchError(
            "raw_mixed_aps_run_not_found",
            "APS connector run was not found for raw mixed corpus seeding.",
            status="blocked",
            http_status=404,
            blocked_fields=["aps_run_id"],
            next_allowed_actions=["seed_existing_aps_run_authority"],
        )
    rows = (
        db.query(ConnectorRunTarget)
        .filter(ConnectorRunTarget.connector_run_id == aps_run_id)
        .filter(ConnectorRunTarget.connector_run_target_id.in_(target_ids))
        .all()
    )
    found = {row.connector_run_target_id for row in rows}
    missing = sorted(set(target_ids) - found)
    if missing:
        raise Layer3WorkbenchError(
            "raw_mixed_aps_target_not_found",
            "APS connector run target was not found for raw mixed corpus seeding.",
            status="blocked",
            http_status=404,
            blocked_fields=["target_ids"],
            next_allowed_actions=["seed_existing_aps_target_authority"],
        )


def _validate_dataset_versions(db: Session, *, dataset_version_ids: list[str], aps_run_id: str) -> None:
    for dataset_version_id in dataset_version_ids:
        if db.get(DatasetVersion, dataset_version_id) is None:
            raise Layer3WorkbenchError(
                "raw_mixed_dataset_version_not_found",
                f"Dataset version '{dataset_version_id}' was not found for raw mixed corpus seeding.",
                status="blocked",
                http_status=404,
                blocked_fields=["artifact_manifest.dataset_version_ids"],
                next_allowed_actions=["seed_existing_dataset_version_authority"],
            )
        provenance_count = (
            db.query(DatasetSourceProvenance)
            .filter(DatasetSourceProvenance.dataset_version_id == dataset_version_id)
            .filter(DatasetSourceProvenance.connector_run_id == aps_run_id)
            .filter(DatasetSourceProvenance.source_system == "nrc_adams_aps")
            .count()
        )
        if provenance_count < 1:
            raise Layer3WorkbenchError(
                "raw_mixed_dataset_source_provenance_missing",
                f"Dataset version '{dataset_version_id}' is missing APS source provenance for raw mixed corpus seeding.",
                status="blocked",
                http_status=409,
                blocked_fields=["artifact_manifest.dataset_version_ids"],
                next_allowed_actions=["seed_dataset_version_aps_source_provenance"],
            )


def _validate_aps_content_documents(
    db: Session,
    *,
    aps_content_document_ids: list[str],
    aps_run_id: str,
    target_ids: list[str],
) -> None:
    for content_id in aps_content_document_ids:
        document_count = db.query(ApsContentDocument).filter(ApsContentDocument.content_id == content_id).count()
        if document_count < 1:
            raise Layer3WorkbenchError(
                "raw_mixed_aps_content_document_not_found",
                f"APS content document '{content_id}' was not found for raw mixed corpus seeding.",
                status="blocked",
                http_status=404,
                blocked_fields=["artifact_manifest.aps_content_document_ids"],
                next_allowed_actions=["seed_existing_aps_content_document_authority"],
            )
        linkage_count = (
            db.query(ApsContentLinkage)
            .filter(ApsContentLinkage.content_id == content_id)
            .filter(ApsContentLinkage.run_id == aps_run_id)
            .filter(ApsContentLinkage.target_id.in_(target_ids))
            .count()
        )
        if linkage_count < 1:
            raise Layer3WorkbenchError(
                "raw_mixed_aps_content_linkage_missing",
                f"APS content document '{content_id}' is missing APS linkage for raw mixed corpus seeding.",
                status="blocked",
                http_status=409,
                blocked_fields=["artifact_manifest.aps_content_document_ids"],
                next_allowed_actions=["seed_existing_aps_content_linkage_authority"],
            )
