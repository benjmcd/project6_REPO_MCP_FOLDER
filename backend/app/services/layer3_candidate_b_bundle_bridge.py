from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping

from app.core.config import settings
from app.services import layer3_source_directory_ingestion
from app.services.review_nrc_aps_workbench_compare import (
    compose_workbench_compare_targets,
    resolve_candidate_b_bundle_root,
)


SCHEMA_ID = "layer3.candidate_b_bundle_material_authority_bridge.v1"
SCHEMA_VERSION = 1
BRIDGE_MODE = "candidate_b_bundle_curated_json_md_to_layer3_material_authority_v1"
CONFIG_AUTHORITY = "LAYER3_CANDIDATE_B_BUNDLE_BRIDGE_DIR"
SOURCE_INGESTION_CONFIG_AUTHORITY = "LAYER3_SOURCE_INGESTION_DIR"
SOURCE_INGESTION_MODE = layer3_source_directory_ingestion.MODE
REQUIRED_BUNDLE_FILES = ("compare.json", "proof.json", "retain.json", "baseline-summary.json")
ADMITTED_RAW_EXTENSIONS = (".json", ".md")
BRIDGE_RECEIPT_PREFIX = "cb-bundle-l3"
REDACTION_POLICY_ID = "candidate_b_bundle_json_md_provenance_redaction_v1"
AUTHORITY_HASH_VERSION = "candidate_b_bundle_layer3_bridge_hash_v1"

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
    "candidate_b_run_id",
    "document_processing_engine",
    "visual_lane_mode",
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
    "checkout_root",
    "database_path",
    "repo_root",
    "review_root",
    "runtime_root",
    "storage_dir",
    "storage_root",
    "python_executable",
}
_EXCLUDED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".bin", ".db", ".sqlite"}


class CandidateBBundleBridgeError(Exception):
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
            "request_id": "candidate-b-bundle-bridge-error",
            "server_time": _server_time(),
            "mode": BRIDGE_MODE,
            "status": "blocked",
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
        }


def prepare_candidate_b_bundle_material_bridge(
    payload: Mapping[str, Any],
    *,
    checkout_root: Path | None = None,
) -> dict[str, Any]:
    fields = _normalise_payload(payload)
    request_id = _required(fields, "client_request_id")
    bridge_mode = _required(fields, "bridge_mode")
    if bridge_mode != BRIDGE_MODE:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_mode_not_admitted",
            "Only the frozen Candidate B bundle JSON/MD bridge mode is admitted.",
            details={"expected_bridge_mode": BRIDGE_MODE, "received_bridge_mode": bridge_mode},
        )
    if fields.get("operator_confirmation") is not True:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_operator_confirmation_required",
            "operator_confirmation=true is required before preparing a Candidate B material bridge.",
            details={"operator_confirmation_required": True},
        )

    root = (checkout_root or _checkout_root()).resolve()
    bridge_base = _configured_bridge_base()
    candidate_b_bundle_id = _required(fields, "candidate_b_bundle_id")
    baseline_run_id = _required(fields, "baseline_run_id")
    candidate_a_run_id = _required(fields, "candidate_a_run_id")

    try:
        bundle_root = resolve_candidate_b_bundle_root(candidate_b_bundle_id, root)
    except ValueError as exc:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_bundle_unavailable",
            "The selected Candidate B bundle is not discoverable through current-main bundle discovery.",
            http_status=404,
            details={"candidate_b_bundle_id": candidate_b_bundle_id},
        ) from exc

    canonical_bundle_id = _repo_ref(root, bundle_root)
    if canonical_bundle_id != candidate_b_bundle_id:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_bundle_id_not_canonical",
            "The selected Candidate B bundle id must match its canonical repo-relative bundle id.",
            details={"candidate_b_bundle_id": candidate_b_bundle_id, "canonical_bundle_id": canonical_bundle_id},
        )

    bundle_payloads = _load_bundle_payloads(bundle_root)
    compare_targets = _load_compare_targets(
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_bundle_id=canonical_bundle_id,
        checkout_root=root,
    )
    compare_target_set = _compare_target_set(compare_targets)
    if not compare_target_set["fixture_ids"]:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_compare_targets_empty",
            "The Candidate B bundle is not comparable with the selected baseline and Candidate A runs.",
            http_status=409,
            details={"candidate_b_bundle_id": canonical_bundle_id},
        )

    raw_root = _raw_root_from_bundle(root, bundle_root, bundle_payloads["compare"], bundle_payloads["retain"])
    raw_inventory = _raw_inventory(bundle_payloads["retain"])
    admitted_sources = _admitted_sources(root, bundle_root, raw_root, raw_inventory)
    excluded_artifacts = _excluded_artifact_summary(raw_inventory)
    if not admitted_sources:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_no_admitted_raw_materials",
            "The selected Candidate B bundle has no retained raw JSON or MD artifacts.",
            http_status=409,
            details={"candidate_b_bundle_id": canonical_bundle_id},
        )

    top_level_sources = [
        _source_record(root, bundle_root / file_name, curated_relative_name=file_name)
        for file_name in REQUIRED_BUNDLE_FILES
    ]
    all_sources = top_level_sources + admitted_sources
    for source in all_sources:
        _assert_source_matches_retention_inventory(source, bundle_payloads["retain"])

    curated_files = [_curated_record(source) for source in all_sources]
    _assert_source_directory_compatible(curated_files)

    bundle_file_manifest_hash = _stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "files": [_manifest_entry(source) for source in top_level_sources],
        }
    )
    bundle_raw_file_manifest_hash = _stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "raw_output_root_ref": _repo_ref(root, raw_root),
            "raw_file_inventory": _normalised_inventory(raw_inventory),
        }
    )
    admitted_file_subset_source_hash = _stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "files": [_manifest_entry(source) for source in all_sources],
        }
    )
    admitted_file_subset_hash = _stable_hash(
        {
            "hash_version": AUTHORITY_HASH_VERSION,
            "files": [_curated_manifest_entry(item) for item in curated_files],
        }
    )
    governed_retained_artifact_family = _governed_retained_artifact_family(raw_inventory, curated_files)

    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "bridge_mode": BRIDGE_MODE,
        "candidate_b_bundle_id": canonical_bundle_id,
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_source_kind": "bundle",
        "compare_target_set_hash": compare_target_set["compare_target_set_hash"],
        "bundle_file_manifest_hash": bundle_file_manifest_hash,
        "bundle_raw_file_manifest_hash": bundle_raw_file_manifest_hash,
        "admitted_file_subset_source_hash": admitted_file_subset_source_hash,
        "admitted_file_subset_hash": admitted_file_subset_hash,
        "governed_retained_artifact_family_hash": governed_retained_artifact_family["artifact_family_hash"],
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
        "candidate_b_bundle_validation": {
            "status": "passed",
            "validated_by": [
                "current_main_candidate_b_bundle_discovery",
                "required_bundle_file_hashes",
                "retained_raw_json_md_manifest",
                "workbench_compare_target_set",
            ],
            "candidate_b_bundle_id": canonical_bundle_id,
        },
        "compare_target_set": compare_target_set,
        "admitted_artifact_subset": _admitted_subset_summary(curated_files),
        "excluded_artifact_subset": excluded_artifacts,
        "governed_retained_artifact_family": governed_retained_artifact_family,
        "source_artifact_manifest": [_manifest_entry(source) for source in all_sources],
        "curated_artifact_manifest": [_curated_manifest_entry(item) for item in curated_files],
        "provenance": {
            "candidate_b_source_kind": "bundle",
            "candidate_b_bundle_ref": canonical_bundle_id,
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
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
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_forbidden_request_fields",
            "The Candidate B bundle bridge does not admit caller paths, runtime rows, connectors, or browser authority.",
            details={"blocked_fields": blocked},
        )
    return fields


def _required(fields: Mapping[str, Any], key: str) -> str:
    value = str(fields.get(key) or "").strip()
    if not value:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_required_field_missing",
            "A required Candidate B bundle bridge field is missing or empty.",
            details={"field": key},
        )
    return value


def _configured_bridge_base() -> Path:
    configured = str(settings.layer3_candidate_b_bundle_bridge_dir or "").strip()
    if not configured:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_dir_unset",
            f"{CONFIG_AUTHORITY} must be set before Candidate B bundle bridge preparation can run.",
            http_status=409,
            details={"config_authority": CONFIG_AUTHORITY},
        )
    root = Path(configured)
    if not root.is_absolute():
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_dir_not_absolute",
            f"{CONFIG_AUTHORITY} must be an absolute server-owned directory.",
            http_status=409,
            details={"config_authority": CONFIG_AUTHORITY},
        )
    resolved = root.resolve()
    for blocked_root in _blocked_roots():
        if _same_or_child(resolved, blocked_root):
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_dir_not_admitted",
                "The Candidate B bridge output directory must not overlap app-owned storage or export staging.",
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


def _checkout_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_bundle_payloads(bundle_root: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for file_name in REQUIRED_BUNDLE_FILES:
        path = bundle_root / file_name
        if not path.is_file():
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_required_bundle_file_missing",
                "The selected Candidate B bundle is missing a required bridge artifact.",
                http_status=409,
                details={"file_name": file_name},
            )
        payloads[file_name.removesuffix(".json").replace("-", "_")] = _read_json(path)
    return payloads


def _load_compare_targets(
    *,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_bundle_id: str,
    checkout_root: Path,
) -> Any:
    try:
        return compose_workbench_compare_targets(
            baseline_run_id=baseline_run_id,
            candidate_a_run_id=candidate_a_run_id,
            candidate_b_source_kind="bundle",
            candidate_b_bundle_id=candidate_b_bundle_id,
            checkout_root=checkout_root,
        )
    except ValueError as exc:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_compare_targets_unavailable",
            "Baseline, Candidate A, and Candidate B bundle compare targets are not usable for this bridge.",
            http_status=409,
            details={"candidate_b_bundle_id": candidate_b_bundle_id, "reason": str(exc)},
        ) from exc


def _compare_target_set(compare_targets: Any) -> dict[str, Any]:
    payload = _model_dump(compare_targets)
    targets = payload.get("targets")
    if not isinstance(targets, list):
        targets = []
    compact_targets = [
        {
            "fixture_id": str(item.get("fixture_id") or "").strip(),
            "baseline_target_id": str(item.get("baseline_target_id") or "").strip(),
            "candidate_a_target_id": str(item.get("candidate_a_target_id") or "").strip(),
            "candidate_b_target_id": str(item.get("candidate_b_target_id") or "").strip(),
            "comparability_state": str(item.get("comparability_state") or "").strip(),
        }
        for item in targets
        if isinstance(item, dict) and str(item.get("fixture_id") or "").strip()
    ]
    compact_targets.sort(key=lambda item: item["fixture_id"])
    fixture_ids = [item["fixture_id"] for item in compact_targets]
    return {
        "candidate_b_source_kind": payload.get("candidate_b_source_kind"),
        "candidate_b_bundle_id": payload.get("candidate_b_bundle_id"),
        "candidate_b_run_id": payload.get("candidate_b_run_id"),
        "baseline_run_id": payload.get("baseline_run_id"),
        "candidate_a_run_id": payload.get("candidate_a_run_id"),
        "fixture_ids": fixture_ids,
        "target_count": len(fixture_ids),
        "targets": compact_targets,
        "compare_target_set_hash": _stable_hash(compact_targets),
    }


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
    elif isinstance(value, dict):
        dumped = value
    else:
        dumped = {}
    return dumped if isinstance(dumped, dict) else {}


def _raw_root_from_bundle(
    checkout_root: Path,
    bundle_root: Path,
    compare_payload: Mapping[str, Any],
    retain_payload: Mapping[str, Any],
) -> Path:
    compare_raw = str(compare_payload.get("raw_output_root") or "").strip().replace("\\", "/")
    retain_raw = str(retain_payload.get("raw_output_root") or "").strip().replace("\\", "/")
    if not compare_raw:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_raw_root_missing",
            "The Candidate B compare report does not declare a raw output root.",
            http_status=409,
        )
    if retain_raw and retain_raw != compare_raw:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_raw_root_mismatch",
            "The Candidate B compare and retention manifests disagree on the raw output root.",
            http_status=409,
            details={"compare_raw_output_root": compare_raw, "retain_raw_output_root": retain_raw},
        )
    raw_rel = _safe_repo_relative_path(compare_raw, "raw_output_root")
    raw_root = (checkout_root / Path(*raw_rel.parts)).resolve()
    if not _same_or_child(raw_root, bundle_root):
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_raw_root_not_bundle_scoped",
            "The Candidate B raw output root must remain inside the selected bundle.",
            http_status=409,
            details={"raw_output_root": compare_raw},
        )
    if raw_root.name != "raw" or raw_root.parent != bundle_root:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_raw_root_not_admitted",
            "Only the selected bundle's direct raw root is admitted for this bridge.",
            http_status=409,
            details={"raw_output_root": compare_raw},
        )
    if not raw_root.is_dir():
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_raw_root_unavailable",
            "The Candidate B bundle raw output root is unavailable.",
            http_status=409,
            details={"raw_output_root": compare_raw},
        )
    return raw_root


def _safe_repo_relative_path(value: str, field_name: str) -> PurePosixPath:
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_repo_ref_invalid",
            "Candidate B bundle references must be repo-relative and traversal-free.",
            http_status=409,
            details={"field": field_name, "value": value},
        )
    return pure


def _raw_inventory(retain_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    inventory = retain_payload.get("raw_file_inventory")
    if not isinstance(inventory, list):
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_raw_inventory_missing",
            "The Candidate B retention manifest does not include a raw file inventory.",
            http_status=409,
        )
    out = [item for item in inventory if isinstance(item, dict)]
    if not out:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_raw_inventory_empty",
            "The Candidate B retention manifest raw file inventory is empty.",
            http_status=409,
        )
    return out


def _admitted_sources(
    checkout_root: Path,
    bundle_root: Path,
    raw_root: Path,
    raw_inventory: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for item in _normalised_inventory(raw_inventory):
        source_ref = str(item.get("path") or "")
        extension = Path(source_ref).suffix.lower()
        if extension not in ADMITTED_RAW_EXTENSIONS:
            continue
        source_rel = _safe_repo_relative_path(source_ref, "raw_file_inventory.path")
        source_path = (checkout_root / Path(*source_rel.parts)).resolve()
        if not _same_or_child(source_path, raw_root):
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_raw_artifact_not_raw_root_scoped",
                "Retained raw JSON/MD artifacts must remain inside the selected raw root.",
                http_status=409,
                details={"path": source_ref},
            )
        if source_path.parent != raw_root:
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_nested_raw_artifact_not_admitted",
                "Nested raw JSON/MD artifacts are not admitted by the first Candidate B bundle bridge.",
                http_status=409,
                details={"path": source_ref},
            )
        source = _source_record(
            checkout_root,
            source_path,
            curated_relative_name=f"raw/{source_path.name}",
            inventory_entry=item,
        )
        if not _same_or_child(source_path, bundle_root):
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_raw_artifact_not_bundle_scoped",
                "Retained raw JSON/MD artifacts must remain inside the selected bundle.",
                http_status=409,
                details={"path": source_ref},
            )
        sources.append(source)
    sources.sort(key=lambda item: str(item["curated_relative_name"]).casefold())
    return sources


def _source_record(
    checkout_root: Path,
    source_path: Path,
    *,
    curated_relative_name: str,
    inventory_entry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not source_path.is_file():
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_source_file_missing",
            "A declared Candidate B bundle artifact is missing from disk.",
            http_status=409,
            details={"source_ref": _repo_ref(checkout_root, source_path)},
        )
    source_sha256 = _file_sha256(source_path)
    expected_sha256 = str((inventory_entry or {}).get("sha256") or "").strip()
    if expected_sha256 and expected_sha256 != source_sha256:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_source_hash_mismatch",
            "A declared Candidate B bundle artifact does not match its retained hash.",
            http_status=409,
            details={"source_ref": _repo_ref(checkout_root, source_path)},
        )
    expected_size = (inventory_entry or {}).get("size_bytes")
    size_bytes = source_path.stat().st_size
    if expected_size is not None and int(expected_size) != size_bytes:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_source_size_mismatch",
            "A declared Candidate B bundle artifact does not match its retained byte size.",
            http_status=409,
            details={"source_ref": _repo_ref(checkout_root, source_path)},
        )
    return {
        "source_ref": _repo_ref(checkout_root, source_path),
        "source_path": source_path,
        "source_sha256": source_sha256,
        "source_size_bytes": size_bytes,
        "source_extension": source_path.suffix.lower(),
        "curated_relative_name": curated_relative_name,
        "category": str((inventory_entry or {}).get("category") or _category_for_source(source_path)).strip(),
    }


def _assert_source_matches_retention_inventory(source: Mapping[str, Any], retain_payload: Mapping[str, Any]) -> None:
    if source["curated_relative_name"].startswith("raw/"):
        return
    source_ref = source["source_ref"]
    inventories = (
        retain_payload.get("durable_report_inventory"),
        retain_payload.get("baseline_output_inventory"),
    )
    for inventory in inventories:
        if not isinstance(inventory, list):
            continue
        for item in inventory:
            if not isinstance(item, dict) or item.get("path") != source_ref:
                continue
            expected_sha256 = str(item.get("sha256") or "").strip()
            expected_size = item.get("size_bytes")
            if expected_sha256 and expected_sha256 != source["source_sha256"]:
                raise CandidateBBundleBridgeError(
                    "candidate_b_bundle_bridge_bundle_file_hash_mismatch",
                    "A Candidate B bundle report does not match its retention manifest hash.",
                    http_status=409,
                    details={"source_ref": source_ref},
                )
            if expected_size is not None and int(expected_size) != source["source_size_bytes"]:
                raise CandidateBBundleBridgeError(
                    "candidate_b_bundle_bridge_bundle_file_size_mismatch",
                    "A Candidate B bundle report does not match its retention manifest byte size.",
                    http_status=409,
                    details={"source_ref": source_ref},
                )
            return
    if source["source_ref"].endswith("/retain.json"):
        return
    raise CandidateBBundleBridgeError(
        "candidate_b_bundle_bridge_bundle_file_not_retained",
        "Required Candidate B bundle reports must be represented in the retention manifest.",
        http_status=409,
        details={"source_ref": source_ref},
    )


def _curated_record(source: Mapping[str, Any]) -> dict[str, Any]:
    source_path = source["source_path"]
    relative_name = str(source["curated_relative_name"])
    if str(source_path).lower().endswith(".json"):
        payload = _read_json(source_path)
        redacted_payload, redaction_count = _redact_json_value(payload)
        content_bytes = (json.dumps(redacted_payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    else:
        content_bytes = source_path.read_bytes()
        redaction_count = 0
    return {
        "relative_name": relative_name,
        "extension": Path(relative_name).suffix.lower(),
        "content_bytes": content_bytes,
        "content_sha256": hashlib.sha256(content_bytes).hexdigest(),
        "content_size_bytes": len(content_bytes),
        "source_ref": source["source_ref"],
        "source_sha256": source["source_sha256"],
        "source_size_bytes": source["source_size_bytes"],
        "category": source["category"],
        "redacted_value_count": redaction_count,
    }


def _assert_source_directory_compatible(curated_files: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for item in curated_files:
        relative_name = str(item["relative_name"])
        normalized = relative_name.casefold()
        if normalized in seen:
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_duplicate_curated_relative_name",
                "The Candidate B bridge would create duplicate curated relative names.",
                http_status=409,
                details={"relative_name": relative_name},
            )
        seen.add(normalized)
        relative_path = PurePosixPath(relative_name)
        if relative_path.is_absolute() or any(part in {"", ".", ".."} for part in relative_path.parts):
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_curated_relative_name_invalid",
                "Curated Candidate B material names must be relative and traversal-free.",
                http_status=409,
                details={"relative_name": relative_name},
            )
        if len(relative_path.parts) > layer3_source_directory_ingestion.MAX_RELATIVE_PATH_SEGMENTS:
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_curated_relative_name_too_deep",
                "Curated Candidate B material exceeds the source-directory relative path policy.",
                http_status=409,
                details={"relative_name": relative_name},
            )
        if len(relative_path.parts) - 1 > layer3_source_directory_ingestion.MAX_RECURSION_DEPTH:
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_curated_recursion_depth_exceeded",
                "Curated Candidate B material exceeds the source-directory recursion policy.",
                http_status=409,
                details={"relative_name": relative_name},
            )
        if Path(relative_name).suffix.lower() not in ADMITTED_RAW_EXTENSIONS:
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_curated_extension_not_admitted",
                "Only JSON and MD files are admitted for the first Candidate B bundle bridge.",
                http_status=409,
                details={"relative_name": relative_name},
            )


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
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_receipt_conflict",
                "A bridge receipt directory already exists without the expected durable receipt.",
                http_status=409,
                details={"bridge_receipt_id": receipt["bridge_receipt_id"]},
            )
        existing = _read_json(receipt_path)
        if existing.get("bridge_receipt_hash") != receipt["bridge_receipt_hash"]:
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_receipt_conflict",
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
        if target.exists():
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_curated_file_conflict",
                "A curated Candidate B material file already exists before bridge writing.",
                http_status=409,
                details={"relative_name": item["relative_name"]},
            )
        target.write_bytes(item["content_bytes"])
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return "prepared"


def _assert_curated_files_match(curated_root: Path, curated_files: list[dict[str, Any]]) -> None:
    for item in curated_files:
        target = curated_root / Path(*PurePosixPath(str(item["relative_name"])).parts)
        if not target.is_file() or _file_sha256(target) != item["content_sha256"]:
            raise CandidateBBundleBridgeError(
                "candidate_b_bundle_bridge_curated_file_mismatch",
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
        "bridge_receipt_ref": f"candidate-b-bundle-bridge://{bridge_receipt_id}/receipt.json",
        "curated_material_root_ref": f"candidate-b-bundle-bridge://{bridge_receipt_id}/curated",
        "curated_root_absolute_path_exposed": False,
        "bridge_config_authority": CONFIG_AUTHORITY,
        "source_ingestion_config_authority": SOURCE_INGESTION_CONFIG_AUTHORITY,
        "source_ingestion_required_root_ref": f"candidate-b-bundle-bridge://{bridge_receipt_id}/curated",
        "source_ingestion_mode": SOURCE_INGESTION_MODE,
        "candidate_b_bundle_id": receipt["candidate_b_bundle_id"],
        "baseline_run_id": receipt["baseline_run_id"],
        "candidate_a_run_id": receipt["candidate_a_run_id"],
        "candidate_b_source_kind": "bundle",
        "candidate_b_bundle_validation": receipt["candidate_b_bundle_validation"],
        "compare_target_set": receipt["compare_target_set"],
        "admitted_artifact_subset": receipt["admitted_artifact_subset"],
        "excluded_artifact_subset": receipt["excluded_artifact_subset"],
        "governed_retained_artifact_family": receipt["governed_retained_artifact_family"],
        "authority_hashes": {
            "bridge_receipt_hash": receipt["bridge_receipt_hash"],
            "compare_target_set_hash": receipt["compare_target_set_hash"],
            "bundle_file_manifest_hash": receipt["bundle_file_manifest_hash"],
            "bundle_raw_file_manifest_hash": receipt["bundle_raw_file_manifest_hash"],
            "admitted_file_subset_source_hash": receipt["admitted_file_subset_source_hash"],
            "admitted_file_subset_hash": receipt["admitted_file_subset_hash"],
            "governed_retained_artifact_family_hash": receipt["governed_retained_artifact_family_hash"],
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
    relative_names = sorted(str(item["relative_name"]) for item in curated_files)
    top_level = [name for name in relative_names if "/" not in name]
    raw = [name for name in relative_names if name.startswith("raw/")]
    return {
        "policy": "required_bundle_reports_plus_retained_raw_json_md_only",
        "file_count": len(relative_names),
        "top_level_files": top_level,
        "raw_files": raw,
        "allowed_extensions": list(ADMITTED_RAW_EXTENSIONS),
    }


def _excluded_artifact_summary(raw_inventory: list[dict[str, Any]]) -> dict[str, Any]:
    excluded: list[dict[str, Any]] = []
    extension_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for item in _normalised_inventory(raw_inventory):
        source_ref = str(item.get("path") or "")
        extension = Path(source_ref).suffix.lower()
        category = str(item.get("category") or "unknown").strip() or "unknown"
        if extension in ADMITTED_RAW_EXTENSIONS and "/raw/" in source_ref.replace("\\", "/"):
            continue
        extension_counts[extension or "<none>"] = extension_counts.get(extension or "<none>", 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1
        if extension in _EXCLUDED_EXTENSIONS or category.startswith("candidate_b_"):
            excluded.append({"path": source_ref, "category": category, "extension": extension or None})
    excluded.sort(key=lambda item: item["path"])
    return {
        "policy": "not_material_text_payload_retained_in_governed_artifact_family",
        "excluded_file_count": len(excluded),
        "excluded_extension_counts": dict(sorted(extension_counts.items())),
        "excluded_category_counts": dict(sorted(category_counts.items())),
        "excluded_refs": excluded[:50],
        "excluded_refs_truncated": len(excluded) > 50,
    }


def _governed_retained_artifact_family(
    raw_inventory: list[dict[str, Any]],
    curated_files: list[dict[str, Any]],
) -> dict[str, Any]:
    material_payloads = [
        _artifact_ref(item, source_ref_key="source_ref", relative_key="relative_name")
        for item in sorted(curated_files, key=lambda item: str(item["relative_name"]))
        if str(item["relative_name"]).startswith("raw/")
    ]
    provenance_artifacts = [
        _artifact_ref(item, source_ref_key="source_ref", relative_key="relative_name")
        for item in sorted(curated_files, key=lambda item: str(item["relative_name"]))
        if not str(item["relative_name"]).startswith("raw/")
    ]
    retained_inventory_refs: list[dict[str, Any]] = []
    visual_evidence: list[dict[str, Any]] = []
    product_artifacts: list[dict[str, Any]] = []
    delivery_artifacts: list[dict[str, Any]] = []
    for item in _normalised_inventory(raw_inventory):
        ref = _retained_inventory_ref(item)
        retained_inventory_refs.append(ref)
        category = str(item.get("category") or "")
        extension = str(ref.get("extension") or "")
        if category in {"candidate_b_annotated_pdf", "candidate_b_extracted_image", "candidate_b_source_pdf"}:
            visual_evidence.append(ref)
        if extension in {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".json", ".md"}:
            product_artifacts.append(ref)
        if extension in {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".json", ".md"}:
            delivery_artifacts.append(ref)
    classification = {
        "policy": "candidate_b_full_artifact_family_retained_but_text_material_payload_bounded",
        "candidate_b_source_kind": "bundle",
        "material_text_payload_policy": "raw_json_md_and_required_reports_only",
        "pdf_material_text_payload_enabled": False,
        "image_material_text_payload_enabled": False,
        "raw_url_exposure_enabled": False,
        "roles": {
            "material_analysis_payloads": material_payloads,
            "visual_page_evidence": sorted(visual_evidence, key=lambda item: item["source_ref"]),
            "provenance_audit_artifacts": provenance_artifacts
            + sorted(retained_inventory_refs, key=lambda item: item["source_ref"]),
            "product_inspection_artifacts": sorted(product_artifacts, key=lambda item: item["source_ref"]),
            "delivery_artifacts": sorted(delivery_artifacts, key=lambda item: item["source_ref"]),
        },
    }
    classification["role_counts"] = {
        role: len(items) for role, items in classification["roles"].items()
    }
    classification["artifact_family_hash"] = _stable_hash(
        {"hash_version": AUTHORITY_HASH_VERSION, "classification": classification}
    )
    return classification


def _artifact_ref(
    item: Mapping[str, Any],
    *,
    source_ref_key: str,
    relative_key: str,
) -> dict[str, Any]:
    return {
        "source_ref": item[source_ref_key],
        "relative_name": item[relative_key],
        "category": item["category"],
        "extension": item["extension"],
        "sha256": item["content_sha256"],
        "size_bytes": item["content_size_bytes"],
        "material_text_payload": True,
    }


def _retained_inventory_ref(item: Mapping[str, Any]) -> dict[str, Any]:
    source_ref = str(item.get("path") or "")
    extension = Path(source_ref).suffix.lower() or None
    return {
        "source_ref": source_ref,
        "category": item.get("category") or "unknown",
        "extension": extension,
        "sha256": item.get("sha256") or "",
        "size_bytes": item.get("size_bytes"),
        "material_text_payload": extension in ADMITTED_RAW_EXTENSIONS,
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
        "candidate_b_runtime_db_rows_enabled": False,
        "candidate_b_runtime_storage_rows_enabled": False,
        "pdf_ingestion_enabled": False,
        "image_ingestion_enabled": False,
        "broad_raw_root_ingestion_enabled": False,
        "caller_supplied_local_paths_enabled": False,
        "provider_object_writes_enabled": False,
        "connector_dispatch_enabled": False,
        "rag_vector_model_runtime_enabled": False,
        "browser_storage_authority_enabled": False,
        "frontend_durable_authority_enabled": False,
        "full_mockup_activation_enabled": False,
    }


def _manifest_entry(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_ref": source["source_ref"],
        "curated_relative_name": source["curated_relative_name"],
        "category": source["category"],
        "extension": source["source_extension"],
        "source_sha256": source["source_sha256"],
        "source_size_bytes": source["source_size_bytes"],
    }


def _curated_manifest_entry(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "relative_name": item["relative_name"],
        "category": item["category"],
        "extension": item["extension"],
        "content_sha256": item["content_sha256"],
        "content_size_bytes": item["content_size_bytes"],
        "source_ref": item["source_ref"],
        "source_sha256": item["source_sha256"],
        "redacted_value_count": item["redacted_value_count"],
    }


def _normalised_inventory(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in inventory:
        source_ref = str(item.get("path") or "").strip().replace("\\", "/")
        if not source_ref:
            continue
        out.append(
            {
                "category": str(item.get("category") or "").strip(),
                "path": source_ref,
                "sha256": str(item.get("sha256") or "").strip(),
                "size_bytes": item.get("size_bytes"),
            }
        )
    out.sort(key=lambda item: item["path"])
    return out


def _category_for_source(path: Path) -> str:
    name = path.name
    if name == "baseline-summary.json":
        return "baseline_summary"
    if name in {"compare.json", "proof.json", "retain.json"}:
        return "candidate_b_bundle_report"
    return "candidate_b_bundle_artifact"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_json_unreadable",
            "A Candidate B bundle JSON artifact could not be read.",
            http_status=409,
            details={"source_ref": path.name},
        ) from exc
    if not isinstance(payload, dict):
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_json_shape_invalid",
            "Candidate B bundle JSON artifacts must be objects.",
            http_status=409,
            details={"source_ref": path.name},
        )
    return payload


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


def _repo_ref(checkout_root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(checkout_root.resolve()).as_posix()
    except ValueError as exc:
        raise CandidateBBundleBridgeError(
            "candidate_b_bundle_bridge_path_outside_checkout",
            "Candidate B bundle artifacts must remain inside the current checkout.",
            http_status=409,
        ) from exc


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
