from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_source_directory_ingestion
from app.services.review_nrc_aps_document_trace import (
    compose_normalized_text_payload,
    compose_trace_manifest,
)
from app.services.review_nrc_aps_runtime import (
    ReviewRuntimeBinding,
    classify_runtime_binding_variant,
    find_runtime_binding_for_run,
    runtime_binding_request_metadata,
)
from app.services.review_nrc_aps_runtime_db import runtime_db_session_for_binding
from app.services.review_nrc_aps_workbench_compare import compose_workbench_compare_targets


SCHEMA_ID = "layer3.candidate_b_runtime_material_authority_bridge.v1"
SCHEMA_VERSION = 1
BRIDGE_MODE = "candidate_b_runtime_source_to_layer3_material_authority_v1"
CANDIDATE_B_RUNTIME_VARIANT = "candidate_b_opendataloader_pdf"
CONFIG_AUTHORITY = "LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR"
SOURCE_INGESTION_CONFIG_AUTHORITY = "LAYER3_SOURCE_INGESTION_DIR"
SOURCE_INGESTION_MODE = layer3_source_directory_ingestion.MODE
BRIDGE_RECEIPT_PREFIX = "cb-runtime-l3"
REDACTION_POLICY_ID = "candidate_b_runtime_document_trace_redaction_v1"
AUTHORITY_HASH_VERSION = "candidate_b_runtime_layer3_bridge_hash_v1"

_FORBIDDEN_REQUEST_FIELDS = {
    "path",
    "paths",
    "directory",
    "local_directory",
    "local_path",
    "url",
    "urls",
    "glob",
    "recursive",
    "file",
    "files",
    "file_bytes",
    "candidate_b_bundle_id",
    "visual_lane_mode",
    "document_processing_engine",
    "runtime_database_path",
    "runtime_storage_dir",
    "database_path",
    "storage_dir",
    "provider_public_url",
    "provider_private_url",
    "connector_dispatch",
    "rag_vector_index",
    "browser_storage",
}
_SENSITIVE_KEY_PARTS = {
    "absolute",
    "database_url",
    "checkout_root",
    "database_path",
    "repo_root",
    "review_root",
    "runtime_root",
    "storage_dir",
    "storage_root",
    "python_executable",
    "document_title",
    "source_file_name",
    "accession_number",
}
_EXCLUDED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".bin",
    ".db",
    ".sqlite",
    ".txt",
}


class CandidateBRuntimeBridgeError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def response_body(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            "request_id": "candidate-b-runtime-bridge-error",
            "server_time": _server_time(),
            "mode": BRIDGE_MODE,
            "status": "blocked",
            "error": {"code": self.code, "message": self.message, "details": self.details},
        }


def prepare_candidate_b_runtime_material_bridge(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    bridge_mode = _required(fields, "bridge_mode")
    if bridge_mode != BRIDGE_MODE:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_mode_not_admitted",
            "Only the frozen Candidate B runtime-source bridge mode is admitted.",
            details={"expected_bridge_mode": BRIDGE_MODE, "received_bridge_mode": bridge_mode},
        )
    if fields.get("operator_confirmation") is not True:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_operator_confirmation_required",
            "operator_confirmation=true is required before preparing a Candidate B runtime material bridge.",
            details={"operator_confirmation_required": True},
        )

    bridge_base = _configured_bridge_base()
    candidate_b_run_id = _required(fields, "candidate_b_run_id")
    baseline_run_id = _required(fields, "baseline_run_id")
    candidate_a_run_id = _required(fields, "candidate_a_run_id")
    binding = _candidate_b_runtime_binding(candidate_b_run_id)
    compare_target_set = _load_compare_target_set(
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_run_id=candidate_b_run_id,
    )
    material_files = _material_files(binding, compare_target_set)
    if not material_files:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_no_admitted_material",
            "The selected Candidate B runtime run produced no admitted Document Trace JSON/MD material.",
            http_status=409,
            details={"candidate_b_run_id": candidate_b_run_id},
        )

    curated_files = [_curated_record(item) for item in material_files]
    _assert_source_directory_compatible(curated_files)
    runtime_authority_hash = _runtime_authority_hash(binding, material_files)
    admitted_file_subset_hash = _stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "files": [_curated_manifest_entry(item) for item in curated_files],
        }
    )
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "bridge_mode": BRIDGE_MODE,
        "candidate_b_run_id": candidate_b_run_id,
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_source_kind": "runtime",
        "document_processing_engine": CANDIDATE_B_RUNTIME_VARIANT,
        "compare_target_set_hash": compare_target_set["compare_target_set_hash"],
        "runtime_review_root_storage_authority_hash": runtime_authority_hash,
        "admitted_file_subset_hash": admitted_file_subset_hash,
        "redaction_policy_id": REDACTION_POLICY_ID,
    }
    bridge_receipt_hash = _stable_hash(receipt_input)
    bridge_receipt_id = f"{BRIDGE_RECEIPT_PREFIX}-{bridge_receipt_hash[:24]}"
    bridge_root = bridge_base / bridge_receipt_id
    curated_root = bridge_root / "curated"
    receipt_path = bridge_root / "receipt.json"
    receipt = {
        **receipt_input,
        "bridge_receipt_id": bridge_receipt_id,
        "bridge_receipt_hash": bridge_receipt_hash,
        "candidate_b_runtime_validation": _runtime_validation(binding),
        "compare_target_set": compare_target_set,
        "admitted_artifact_subset": _admitted_subset_summary(curated_files),
        "excluded_artifact_subset": _excluded_artifact_summary(binding),
        "curated_artifact_manifest": [_curated_manifest_entry(item) for item in curated_files],
        "provenance": {
            "candidate_b_source_kind": "runtime",
            "candidate_b_run_id": candidate_b_run_id,
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "document_processing_engine": CANDIDATE_B_RUNTIME_VARIANT,
            "source_labels_redacted": True,
            "absolute_paths_redacted": True,
            "raw_url_exposure_enabled": False,
        },
        "layer3_compatibility": _layer3_compatibility_summary(),
        "negative_invariants": _negative_invariants(),
    }

    response_status = _write_bridge_receipt(
        bridge_root=bridge_root,
        curated_root=curated_root,
        receipt_path=receipt_path,
        receipt=receipt,
        curated_files=curated_files,
    )
    return _response(
        request_id=request_id,
        response_status=response_status,
        receipt=receipt,
        bridge_receipt_id=bridge_receipt_id,
    )


def _normalise_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    blocked = sorted(key for key in fields if key in _FORBIDDEN_REQUEST_FIELDS and fields.get(key) is not None)
    if blocked:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_forbidden_request_fields",
            "The Candidate B runtime bridge does not admit caller paths, bundles, connectors, or browser authority.",
            details={"blocked_fields": blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_required_field_missing",
            "A required Candidate B runtime bridge field is missing or empty.",
            details={"field": key},
        )
    return value


def _configured_bridge_base() -> Path:
    configured = str(settings.layer3_candidate_b_runtime_bridge_dir or "").strip()
    if not configured:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_dir_unset",
            f"{CONFIG_AUTHORITY} must be set before Candidate B runtime bridge preparation can run.",
            http_status=409,
            details={"config_authority": CONFIG_AUTHORITY},
        )
    root = Path(configured)
    if not root.is_absolute():
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_dir_not_absolute",
            f"{CONFIG_AUTHORITY} must be an absolute server-owned directory.",
            http_status=409,
            details={"config_authority": CONFIG_AUTHORITY},
        )
    resolved = root.resolve()
    for blocked_root in _blocked_roots():
        if _same_or_child(resolved, blocked_root):
            raise CandidateBRuntimeBridgeError(
                "candidate_b_runtime_bridge_dir_not_admitted",
                "The Candidate B runtime bridge output directory must not overlap app-owned storage or export staging.",
                http_status=409,
                details={"config_authority": CONFIG_AUTHORITY, "blocked_root": blocked_root.name},
            )
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _blocked_roots() -> list[Path]:
    roots = [
        Path(settings.storage_dir),
        Path(settings.raw_storage_dir),
        Path(settings.artifact_storage_dir),
        Path(settings.layer3_local_outbox_dir),
    ]
    if settings.layer3_external_local_export_dir:
        roots.append(Path(settings.layer3_external_local_export_dir))
    return [root.resolve() for root in roots if str(root)]


def _same_or_child(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _candidate_b_runtime_binding(run_id: str) -> ReviewRuntimeBinding:
    binding = find_runtime_binding_for_run(run_id)
    if binding is None:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_run_unavailable",
            "The selected Candidate B runtime run is not discoverable through current-main runtime discovery.",
            http_status=404,
            details={"candidate_b_run_id": run_id},
        )
    if classify_runtime_binding_variant(binding) != CANDIDATE_B_RUNTIME_VARIANT:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_run_variant_invalid",
            "The selected runtime run is not the opt-in Candidate B OpenDataLoader PDF processing-engine path.",
            http_status=409,
            details={"candidate_b_run_id": run_id, "required_variant": CANDIDATE_B_RUNTIME_VARIANT},
        )
    metadata = runtime_binding_request_metadata(binding)
    if metadata.get("visual_lane_mode") != "baseline":
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_visual_lane_mode_not_admitted",
            "Candidate B runtime runs must not reinterpret Candidate B as a visual-lane mode.",
            http_status=409,
            details={"candidate_b_run_id": run_id, "visual_lane_mode": metadata.get("visual_lane_mode")},
        )
    if binding.database_path is None or not binding.database_path.is_file():
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_database_missing",
            "The selected Candidate B runtime run has no available review database.",
            http_status=409,
            details={"candidate_b_run_id": run_id},
        )
    if binding.storage_dir is None or not binding.storage_dir.is_dir():
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_storage_missing",
            "The selected Candidate B runtime run has no available runtime storage root.",
            http_status=409,
            details={"candidate_b_run_id": run_id},
        )
    summary_visual_lane = str(binding.summary.get("visual_lane_mode") or "baseline").strip().lower()
    summary_engine = str(binding.summary.get("document_processing_engine") or "").strip().lower()
    if summary_visual_lane != "baseline" or summary_engine != CANDIDATE_B_RUNTIME_VARIANT:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_summary_metadata_invalid",
            "The selected Candidate B runtime summary does not match the admitted runtime-source posture.",
            http_status=409,
            details={"candidate_b_run_id": run_id},
        )
    return binding


def _load_compare_target_set(*, baseline_run_id: str, candidate_a_run_id: str, candidate_b_run_id: str) -> dict[str, Any]:
    try:
        compare_targets = compose_workbench_compare_targets(
            baseline_run_id=baseline_run_id,
            candidate_a_run_id=candidate_a_run_id,
            candidate_b_source_kind="runtime",
            candidate_b_run_id=candidate_b_run_id,
        )
    except ValueError as exc:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_compare_targets_unavailable",
            "Baseline, Candidate A, and Candidate B runtime compare targets are not usable for this bridge.",
            http_status=409,
            details={"candidate_b_run_id": candidate_b_run_id, "reason": str(exc)},
        ) from exc
    payload = _model_dump(compare_targets)
    raw_targets = payload.get("targets") if isinstance(payload, dict) else None
    compact = []
    for item in raw_targets if isinstance(raw_targets, list) else []:
        if not isinstance(item, dict):
            continue
        record = {
            "fixture_id": str(item.get("fixture_id") or "").strip(),
            "baseline_target_id": str(item.get("baseline_target_id") or "").strip(),
            "candidate_a_target_id": str(item.get("candidate_a_target_id") or "").strip(),
            "candidate_b_target_id": str(item.get("candidate_b_target_id") or "").strip(),
            "comparability_state": str(item.get("comparability_state") or "").strip(),
        }
        if all(record.values()):
            compact.append(record)
    compact.sort(key=lambda item: item["fixture_id"])
    if not compact:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_compare_targets_empty",
            "The Candidate B runtime run is not comparable with the selected baseline and Candidate A runs.",
            http_status=409,
            details={"candidate_b_run_id": candidate_b_run_id},
        )
    return {
        "candidate_b_source_kind": "runtime",
        "candidate_b_run_id": candidate_b_run_id,
        "fixture_ids": [item["fixture_id"] for item in compact],
        "target_count": len(compact),
        "targets": compact,
        "compare_target_set_hash": _stable_hash({"targets": compact, "candidate_b_run_id": candidate_b_run_id}),
    }


def _material_files(binding: ReviewRuntimeBinding, compare_target_set: Mapping[str, Any]) -> list[dict[str, Any]]:
    files = [
        _json_material("runtime-summary.json", _redact_json_value(binding.summary)[0], "candidate_b_runtime_summary"),
        _json_material("compare-targets.json", compare_target_set, "candidate_b_runtime_compare_targets"),
    ]
    session_cm = runtime_db_session_for_binding(binding) if binding.database_path else nullcontext(None)
    with session_cm as session:
        for target in compare_target_set["targets"]:
            fixture_id = target["fixture_id"]
            target_id = target["candidate_b_target_id"]
            trace_payload = _redact_json_value(
                _model_dump(compose_trace_manifest(session, binding.run_id, target_id, binding.review_root))
            )[0]
            normalized_payload = _redact_json_value(
                _model_dump(compose_normalized_text_payload(session, binding.run_id, target_id, binding.review_root))
            )[0]
            if not normalized_payload.get("available"):
                raise CandidateBRuntimeBridgeError(
                    "candidate_b_runtime_bridge_normalized_text_unavailable",
                    "A comparable Candidate B runtime target lacks normalized-text material authority.",
                    http_status=409,
                    details={"candidate_b_run_id": binding.run_id, "fixture_id": fixture_id},
                )
            files.append(_json_material(f"trace/{fixture_id}.json", trace_payload, "candidate_b_runtime_trace"))
            files.append(
                _json_material(
                    f"normalized/{fixture_id}.json",
                    normalized_payload,
                    "candidate_b_runtime_normalized_text",
                )
            )
            files.append(
                _bytes_material(
                    f"text/{fixture_id}.md",
                    _markdown_for_target(binding.run_id, target, normalized_payload).encode("utf-8"),
                    "candidate_b_runtime_text_markdown",
                )
            )
    return files


def _json_material(relative_name: str, payload: Mapping[str, Any], category: str) -> dict[str, Any]:
    return _bytes_material(relative_name, json.dumps(payload, sort_keys=True, indent=2).encode("utf-8") + b"\n", category)


def _bytes_material(relative_name: str, content: bytes, category: str) -> dict[str, Any]:
    return {
        "relative_name": relative_name,
        "category": category,
        "extension": Path(relative_name).suffix.lower(),
        "content_bytes": content,
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "content_size_bytes": len(content),
        "source_ref": f"candidate-b-runtime-trace://{relative_name}",
    }


def _markdown_for_target(run_id: str, target: Mapping[str, Any], normalized_payload: Mapping[str, Any]) -> str:
    text = str(normalized_payload.get("text") or "")
    return (
        f"# Candidate B runtime material: {target['fixture_id']}\n\n"
        f"- candidate_b_run_id: {run_id}\n"
        f"- candidate_b_target_id: {target['candidate_b_target_id']}\n"
        f"- document_processing_engine: {CANDIDATE_B_RUNTIME_VARIANT}\n"
        f"- mapping_precision: {normalized_payload.get('mapping_precision') or 'unknown'}\n"
        f"- normalized_char_count: {normalized_payload.get('char_count') or 0}\n\n"
        "## Normalized Text\n\n"
        f"{text}\n"
    )


def _curated_record(item: Mapping[str, Any]) -> dict[str, Any]:
    return dict(item)


def _assert_source_directory_compatible(curated_files: list[dict[str, Any]]) -> None:
    for item in curated_files:
        relative_name = str(item["relative_name"])
        parts = PurePosixPath(relative_name).parts
        extension = str(item["extension"])
        if extension not in layer3_source_directory_ingestion.ALLOWED_EXTENSIONS:
            raise CandidateBRuntimeBridgeError(
                "candidate_b_runtime_bridge_extension_not_admitted",
                "A runtime bridge material file is not compatible with source-directory ingestion.",
                details={"relative_name": relative_name, "extension": extension},
            )
        if len(parts) > layer3_source_directory_ingestion.MAX_RELATIVE_PATH_SEGMENTS:
            raise CandidateBRuntimeBridgeError(
                "candidate_b_runtime_bridge_relative_path_too_deep",
                "A runtime bridge material file exceeds source-directory relative path limits.",
                details={"relative_name": relative_name},
            )


def _runtime_authority_hash(binding: ReviewRuntimeBinding, material_files: list[dict[str, Any]]) -> str:
    return _stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "run_id": binding.run_id,
            "database_content_sha256": _file_sha256(binding.database_path) if binding.database_path else None,
            "summary_hash": _stable_hash(_redact_json_value(binding.summary)[0]),
            "material_hashes": [_curated_manifest_entry(item) for item in material_files],
        }
    )


def _runtime_validation(binding: ReviewRuntimeBinding) -> dict[str, Any]:
    return {
        "status": "passed",
        "validated_by": [
            "current_main_runtime_discovery",
            "candidate_b_opendataloader_pdf_variant_classification",
            "workbench_compare_target_set",
            "document_trace_normalized_text_materialization",
        ],
        "candidate_b_run_id": binding.run_id,
        "document_processing_engine": CANDIDATE_B_RUNTIME_VARIANT,
        "visual_lane_mode": "baseline",
    }


def _excluded_artifact_summary(binding: ReviewRuntimeBinding) -> dict[str, Any]:
    extension_counts: dict[str, int] = {}
    excluded_refs: list[dict[str, Any]] = []
    root = binding.review_root.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        extension = path.suffix.lower() or "<none>"
        if extension not in _EXCLUDED_EXTENSIONS:
            continue
        extension_counts[extension] = extension_counts.get(extension, 0) + 1
        try:
            relative_ref = path.resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        excluded_refs.append({"path": relative_ref, "extension": extension})
    return {
        "policy": "omit_source_pdfs_images_binaries_txt_runtime_db_and_broad_runtime_storage",
        "excluded_file_count": len(excluded_refs),
        "excluded_extension_counts": dict(sorted(extension_counts.items())),
        "excluded_refs": excluded_refs[:50],
        "excluded_refs_truncated": len(excluded_refs) > 50,
    }


def _write_bridge_receipt(
    *,
    bridge_root: Path,
    curated_root: Path,
    receipt_path: Path,
    receipt: Mapping[str, Any],
    curated_files: list[dict[str, Any]],
) -> str:
    if bridge_root.exists():
        if not receipt_path.is_file():
            raise CandidateBRuntimeBridgeError(
                "candidate_b_runtime_bridge_receipt_conflict",
                "A bridge receipt directory already exists without the expected durable receipt.",
                http_status=409,
                details={"bridge_receipt_id": receipt["bridge_receipt_id"]},
            )
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("bridge_receipt_hash") != receipt["bridge_receipt_hash"]:
            raise CandidateBRuntimeBridgeError(
                "candidate_b_runtime_bridge_receipt_conflict",
                "A bridge receipt directory already exists for a different authority basis.",
                http_status=409,
                details={"bridge_receipt_id": receipt["bridge_receipt_id"]},
            )
        _assert_curated_files_match(curated_root, curated_files)
        return "already_prepared"
    curated_root.mkdir(parents=True, exist_ok=False)
    for item in curated_files:
        target = curated_root / Path(*PurePosixPath(str(item["relative_name"])).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item["content_bytes"])
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return "prepared"


def _assert_curated_files_match(curated_root: Path, curated_files: list[dict[str, Any]]) -> None:
    for item in curated_files:
        target = curated_root / Path(*PurePosixPath(str(item["relative_name"])).parts)
        if not target.is_file() or _file_sha256(target) != item["content_sha256"]:
            raise CandidateBRuntimeBridgeError(
                "candidate_b_runtime_bridge_curated_file_mismatch",
                "An existing bridge receipt has stale or missing curated material.",
                http_status=409,
                details={"relative_name": item["relative_name"]},
            )


def _response(
    *,
    request_id: str,
    response_status: str,
    receipt: Mapping[str, Any],
    bridge_receipt_id: str,
) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "server_time": _server_time(),
        "status": response_status,
        "mode": BRIDGE_MODE,
        "bridge_receipt_id": bridge_receipt_id,
        "bridge_receipt_ref": f"candidate-b-runtime-bridge://{bridge_receipt_id}/receipt.json",
        "curated_material_root_ref": f"candidate-b-runtime-bridge://{bridge_receipt_id}/curated",
        "curated_root_absolute_path_exposed": False,
        "bridge_config_authority": CONFIG_AUTHORITY,
        "source_ingestion_config_authority": SOURCE_INGESTION_CONFIG_AUTHORITY,
        "source_ingestion_required_root_ref": f"candidate-b-runtime-bridge://{bridge_receipt_id}/curated",
        "source_ingestion_mode": SOURCE_INGESTION_MODE,
        "candidate_b_run_id": receipt["candidate_b_run_id"],
        "baseline_run_id": receipt["baseline_run_id"],
        "candidate_a_run_id": receipt["candidate_a_run_id"],
        "candidate_b_source_kind": "runtime",
        "document_processing_engine": CANDIDATE_B_RUNTIME_VARIANT,
        "candidate_b_runtime_validation": receipt["candidate_b_runtime_validation"],
        "compare_target_set": receipt["compare_target_set"],
        "admitted_artifact_subset": receipt["admitted_artifact_subset"],
        "excluded_artifact_subset": receipt["excluded_artifact_subset"],
        "authority_hashes": {
            "bridge_receipt_hash": receipt["bridge_receipt_hash"],
            "compare_target_set_hash": receipt["compare_target_set_hash"],
            "runtime_review_root_storage_authority_hash": receipt["runtime_review_root_storage_authority_hash"],
            "admitted_file_subset_hash": receipt["admitted_file_subset_hash"],
        },
        "provenance": receipt["provenance"],
        "layer3_material_preview_compatible": True,
        "gate_b_material_authority_compatible": True,
        "layer3_compatibility": receipt["layer3_compatibility"],
        "negative_invariants": receipt["negative_invariants"],
        "next_allowed_actions": [
            "set LAYER3_SOURCE_INGESTION_DIR to the server-owned curated material root for this receipt",
            "run source-directory scan",
            "run source-directory material preview",
            "submit Gate B material authority decision",
        ],
    }


def _admitted_subset_summary(curated_files: list[dict[str, Any]]) -> dict[str, Any]:
    names = sorted(str(item["relative_name"]) for item in curated_files)
    return {
        "policy": "runtime_document_trace_json_md_only",
        "file_count": len(names),
        "top_level_files": [name for name in names if "/" not in name],
        "trace_files": [name for name in names if name.startswith("trace/")],
        "normalized_files": [name for name in names if name.startswith("normalized/")],
        "text_files": [name for name in names if name.startswith("text/")],
        "allowed_extensions": [".json", ".md"],
    }


def _layer3_compatibility_summary() -> dict[str, Any]:
    return {
        "source_directory_scan_policy_id": layer3_source_directory_ingestion.RUNTIME_POLICY_ID,
        "source_directory_config_authority": SOURCE_INGESTION_CONFIG_AUTHORITY,
        "allowed_extensions": list(layer3_source_directory_ingestion.ALLOWED_EXTENSIONS),
        "max_recursion_depth": layer3_source_directory_ingestion.MAX_RECURSION_DEPTH,
        "max_relative_path_segments": layer3_source_directory_ingestion.MAX_RELATIVE_PATH_SEGMENTS,
        "material_preview_uses_existing_hash_checks": True,
        "gate_b_uses_existing_decision_basis_validation": True,
        "source_directory_policy_widened": False,
    }


def _negative_invariants() -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_visual_lane_mode_enabled": False,
        "candidate_b_default_promotion_enabled": False,
        "candidate_b_bundle_bridge_weakened": False,
        "pdf_ingestion_enabled": False,
        "image_ingestion_enabled": False,
        "broad_runtime_db_ingestion_enabled": False,
        "broad_runtime_storage_ingestion_enabled": False,
        "caller_supplied_local_paths_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "browser_storage_authority_enabled": False,
        "frontend_durable_authority_enabled": False,
        "full_mockup_activation_enabled": False,
    }


def _curated_manifest_entry(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "relative_name": item["relative_name"],
        "category": item["category"],
        "extension": item["extension"],
        "content_sha256": item["content_sha256"],
        "content_size_bytes": item["content_size_bytes"],
        "source_ref": item["source_ref"],
    }


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except TypeError:
            return value.model_dump()
    if isinstance(value, dict):
        return dict(value)
    return json.loads(json.dumps(value, default=str))


def _redact_json_value(value: Any, *, key: str = "") -> tuple[Any, int]:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        count = 0
        for child_key, child_value in value.items():
            next_value, next_count = _redact_json_value(child_value, key=str(child_key))
            redacted[str(child_key)] = next_value
            count += next_count
        return redacted, count
    if isinstance(value, list):
        redacted_list = []
        count = 0
        for item in value:
            next_value, next_count = _redact_json_value(item, key=key)
            redacted_list.append(next_value)
            count += next_count
        return redacted_list, count
    if isinstance(value, str) and (_sensitive_key(key) or _looks_like_absolute_path(value)):
        return f"redacted://sha256/{hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]}", 1
    return value, 0


def _sensitive_key(key: str) -> bool:
    normalised = key.strip().lower()
    return any(part in normalised for part in _SENSITIVE_KEY_PARTS)


def _looks_like_absolute_path(value: str) -> bool:
    stripped = value.strip()
    if not stripped or "://" in stripped:
        return False
    return PureWindowsPath(stripped).is_absolute() or PurePosixPath(stripped).is_absolute()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _server_time() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
