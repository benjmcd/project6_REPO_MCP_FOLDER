from __future__ import annotations

from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import sqlite3
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
FULL_CORPUS_BRIDGE_MODE = "candidate_b_full_corpus_runtime_to_layer3_material_authority_v1"
ADMITTED_BRIDGE_MODES: frozenset[str] = frozenset({BRIDGE_MODE, FULL_CORPUS_BRIDGE_MODE})
CANDIDATE_B_RUNTIME_VARIANT = "candidate_b_opendataloader_pdf"
CANDIDATE_B_VISUAL_LANE_MODE = "candidate_b_opendataloader_page_evidence_v1"
BASELINE_ENGINE = "baseline"
CANDIDATE_A_VISUAL_LANE_MODE = "candidate_a_page_evidence_v1"
_ADMITTED_CANDIDATE_B_RUNTIME_VISUAL_LANE_MODES: frozenset[str] = frozenset({"baseline", CANDIDATE_B_VISUAL_LANE_MODE})
CONFIG_AUTHORITY = "LAYER3_CANDIDATE_B_RUNTIME_BRIDGE_DIR"
SOURCE_INGESTION_CONFIG_AUTHORITY = "LAYER3_SOURCE_INGESTION_DIR"
SOURCE_INGESTION_MODE = layer3_source_directory_ingestion.MODE
BRIDGE_RECEIPT_PREFIX = "cb-runtime-l3"
REDACTION_POLICY_ID = "candidate_b_runtime_document_trace_redaction_v1"
AUTHORITY_HASH_VERSION = "candidate_b_runtime_layer3_bridge_hash_v1"
FULL_CORPUS_VALIDATION_SCHEMA_ID = "aps.full_corpus_compare_triplet_validation.v1"
FULL_CORPUS_TARGET_COUNT = 69
REQUIRED_FULL_CORPUS_GATE_NAMES = (
    "artifact_ingestion",
    "content_index",
    "context_dossier",
    "context_packet",
    "deterministic_challenge_artifact",
    "deterministic_challenge_review_packet",
    "deterministic_insight_artifact",
    "evidence_bundle",
    "evidence_citation_pack",
    "evidence_report",
    "evidence_report_export",
    "evidence_report_export_package",
)

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
    if bridge_mode not in ADMITTED_BRIDGE_MODES:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_mode_not_admitted",
            "Only frozen Candidate B runtime bridge modes are admitted.",
            details={"expected_bridge_modes": sorted(ADMITTED_BRIDGE_MODES), "received_bridge_mode": bridge_mode},
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
    runtime_validation = _runtime_validation(binding, bridge_mode=bridge_mode)
    visual_lane_mode = str(runtime_validation.get("visual_lane_mode") or "baseline")
    compare_target_set = _load_compare_target_set(
        bridge_mode=bridge_mode,
        baseline_run_id=baseline_run_id,
        candidate_a_run_id=candidate_a_run_id,
        candidate_b_run_id=candidate_b_run_id,
        candidate_b_binding=binding,
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
    governed_retained_artifact_family = _governed_retained_artifact_family(binding, curated_files)
    receipt_input = {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "bridge_mode": bridge_mode,
        "candidate_b_run_id": candidate_b_run_id,
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_source_kind": "runtime",
        "document_processing_engine": CANDIDATE_B_RUNTIME_VARIANT,
        "visual_lane_mode": visual_lane_mode,
        "compare_target_set_hash": compare_target_set["compare_target_set_hash"],
        "runtime_review_root_storage_authority_hash": runtime_authority_hash,
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
        "candidate_b_runtime_validation": runtime_validation,
        "candidate_b_visual_lane_evidence": _candidate_b_visual_lane_evidence(binding),
        "compare_target_set": compare_target_set,
        "admitted_artifact_subset": _admitted_subset_summary(curated_files),
        "excluded_artifact_subset": _excluded_artifact_summary(binding),
        "governed_retained_artifact_family": governed_retained_artifact_family,
        "curated_artifact_manifest": [_curated_manifest_entry(item) for item in curated_files],
        "provenance": {
            "candidate_b_source_kind": "runtime",
            "candidate_b_run_id": candidate_b_run_id,
            "baseline_run_id": baseline_run_id,
            "candidate_a_run_id": candidate_a_run_id,
            "document_processing_engine": CANDIDATE_B_RUNTIME_VARIANT,
            "visual_lane_mode": visual_lane_mode,
            "source_labels_redacted": True,
            "absolute_paths_redacted": True,
            "raw_url_exposure_enabled": False,
        },
        "layer3_compatibility": _layer3_compatibility_summary(),
        "negative_invariants": _negative_invariants(visual_lane_mode=visual_lane_mode),
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
    metadata_visual_lane = str(metadata.get("visual_lane_mode") or "baseline").strip().lower()
    if metadata_visual_lane not in _ADMITTED_CANDIDATE_B_RUNTIME_VISUAL_LANE_MODES:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_visual_lane_mode_not_admitted",
            "Candidate B runtime runs may only use baseline or the admitted Candidate B page-evidence visual lane.",
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
    if summary_visual_lane not in _ADMITTED_CANDIDATE_B_RUNTIME_VISUAL_LANE_MODES or summary_engine != CANDIDATE_B_RUNTIME_VARIANT:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_summary_metadata_invalid",
            "The selected Candidate B runtime summary does not match the admitted runtime-source posture.",
            http_status=409,
            details={"candidate_b_run_id": run_id},
        )
    return binding


def _load_compare_target_set(
    *,
    bridge_mode: str,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_run_id: str,
    candidate_b_binding: ReviewRuntimeBinding,
) -> dict[str, Any]:
    if bridge_mode == FULL_CORPUS_BRIDGE_MODE:
        return _load_full_corpus_compare_target_set(
            baseline_run_id=baseline_run_id,
            candidate_a_run_id=candidate_a_run_id,
            candidate_b_run_id=candidate_b_run_id,
            candidate_b_binding=candidate_b_binding,
        )
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


def _load_full_corpus_compare_target_set(
    *,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_run_id: str,
    candidate_b_binding: ReviewRuntimeBinding,
) -> dict[str, Any]:
    baseline_binding = _runtime_binding_for_run(baseline_run_id, label="baseline")
    candidate_a_binding = _runtime_binding_for_run(candidate_a_run_id, label="candidate_a")
    _validate_full_corpus_binding(
        baseline_binding,
        label="baseline",
        expected_engine=BASELINE_ENGINE,
        expected_visual_lane=BASELINE_ENGINE,
        require_candidate_b_metrics=False,
    )
    _validate_full_corpus_binding(
        candidate_a_binding,
        label="candidate_a",
        expected_engine=BASELINE_ENGINE,
        expected_visual_lane=CANDIDATE_A_VISUAL_LANE_MODE,
        require_candidate_b_metrics=False,
    )
    _validate_full_corpus_binding(
        candidate_b_binding,
        label="candidate_b",
        expected_engine=CANDIDATE_B_RUNTIME_VARIANT,
        expected_visual_lane=CANDIDATE_B_VISUAL_LANE_MODE,
        require_candidate_b_metrics=True,
    )

    baseline_targets = _full_corpus_targets(baseline_binding, label="baseline")
    candidate_a_targets = _full_corpus_targets(candidate_a_binding, label="candidate_a")
    candidate_b_targets = _full_corpus_targets(candidate_b_binding, label="candidate_b")
    baseline_identity = _target_identity_for_hash(baseline_targets)
    if _target_identity_for_hash(candidate_a_targets) != baseline_identity:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_full_corpus_bridge_candidate_a_target_set_mismatch",
            "Candidate A does not share the baseline full-corpus target set.",
            http_status=409,
            details={"candidate_a_run_id": candidate_a_run_id},
        )
    if _target_identity_for_hash(candidate_b_targets) != baseline_identity:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_full_corpus_bridge_candidate_b_target_set_mismatch",
            "Candidate B does not share the baseline full-corpus target set.",
            http_status=409,
            details={"candidate_b_run_id": candidate_b_run_id},
        )

    targets = []
    for baseline_target, candidate_a_target, candidate_b_target in zip(
        baseline_targets,
        candidate_a_targets,
        candidate_b_targets,
    ):
        target_key = f"target-{int(baseline_target['ordinal']):05d}"
        accession_number = str(baseline_target["accession_number"])
        targets.append(
            {
                "target_key": target_key,
                "ordinal": baseline_target["ordinal"],
                "accession_ref": _redacted_ref(accession_number),
                "baseline_target_id": baseline_target["target_id"],
                "candidate_a_target_id": candidate_a_target["target_id"],
                "candidate_b_target_id": candidate_b_target["target_id"],
                "comparability_state": "full_corpus_aligned",
            }
        )

    target_set_hash = _stable_hash(
        [
            {"ordinal": item["ordinal"], "accession_number": item["accession_number"]}
            for item in baseline_targets
        ]
    )
    return {
        "schema_id": FULL_CORPUS_VALIDATION_SCHEMA_ID,
        "schema_version": 1,
        "candidate_b_source_kind": "runtime",
        "compare_scope": "full_corpus",
        "bridge_mode": FULL_CORPUS_BRIDGE_MODE,
        "baseline_run_id": baseline_run_id,
        "candidate_a_run_id": candidate_a_run_id,
        "candidate_b_run_id": candidate_b_run_id,
        "target_count": len(targets),
        "target_set_hash": target_set_hash,
        "compare_target_set_hash": target_set_hash,
        "targets": targets,
        "accession_head_redacted": [_redacted_ref(item["accession_number"]) for item in baseline_targets[:3]],
        "accession_tail_redacted": [_redacted_ref(item["accession_number"]) for item in baseline_targets[-3:]],
        "validated_by": [
            "same_checkout_runtime_discovery",
            "local_corpus_summary_target_outcomes",
            "connector_run_request_config_json",
            "local_corpus_validate_only_gate_results",
            "candidate_b_full_corpus_compare_triplet_v1",
        ],
    }


def _runtime_binding_for_run(run_id: str, *, label: str) -> ReviewRuntimeBinding:
    binding = find_runtime_binding_for_run(run_id)
    if binding is None:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_run_unavailable",
            "A required full-corpus comparison run is not discoverable through current-main runtime discovery.",
            http_status=404,
            details={"run_id": run_id, "label": label},
        )
    if binding.database_path is None or not binding.database_path.is_file():
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_database_missing",
            "A required full-corpus comparison run has no available review database.",
            http_status=409,
            details={"run_id": run_id, "label": label},
        )
    if binding.storage_dir is None or not binding.storage_dir.is_dir():
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_storage_missing",
            "A required full-corpus comparison run has no available runtime storage root.",
            http_status=409,
            details={"run_id": run_id, "label": label},
        )
    return binding


def _validate_full_corpus_binding(
    binding: ReviewRuntimeBinding,
    *,
    label: str,
    expected_engine: str,
    expected_visual_lane: str,
    require_candidate_b_metrics: bool,
) -> None:
    summary = binding.summary
    if str(summary.get("schema_id") or "") != "aps.local_corpus_e2e_summary.v1":
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_summary_schema_invalid",
            "A required full-corpus comparison summary has the wrong schema.",
            http_status=409,
            details={"run_id": binding.run_id, "schema_id": summary.get("schema_id")},
        )
    if summary.get("passed") is not True:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_summary_not_passed",
            "A required full-corpus comparison summary has not passed.",
            http_status=409,
            details={"run_id": binding.run_id},
        )
    if int(summary.get("corpus_pdf_count") or 0) != FULL_CORPUS_TARGET_COUNT:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_corpus_count_mismatch",
            "A required full-corpus comparison summary does not cover the admitted 69-PDF corpus.",
            http_status=409,
            details={"run_id": binding.run_id, "corpus_pdf_count": summary.get("corpus_pdf_count")},
        )
    observed_engine = str(summary.get("document_processing_engine") or BASELINE_ENGINE).strip()
    observed_visual_lane = str(summary.get("visual_lane_mode") or BASELINE_ENGINE).strip()
    if observed_engine != expected_engine or observed_visual_lane != expected_visual_lane:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_variant_mismatch",
            "A required full-corpus comparison summary does not match the admitted variant.",
            http_status=409,
            details={
                "run_id": binding.run_id,
                "expected_document_processing_engine": expected_engine,
                "observed_document_processing_engine": observed_engine,
                "expected_visual_lane_mode": expected_visual_lane,
                "observed_visual_lane_mode": observed_visual_lane,
            },
        )
    request_config = _connector_run_request_config(binding, label=label)
    _validate_full_corpus_request_config(
        request_config,
        label=label,
        run_id=binding.run_id,
        expected_engine=expected_engine,
        expected_visual_lane=expected_visual_lane,
    )
    _validate_full_corpus_gate_results(summary, label=label, run_id=binding.run_id)
    _validate_full_corpus_metrics(
        summary,
        label=label,
        run_id=binding.run_id,
        require_candidate_b_metrics=require_candidate_b_metrics,
    )


def _connector_run_request_config(binding: ReviewRuntimeBinding, *, label: str) -> dict[str, Any]:
    try:
        with sqlite3.connect(str(binding.database_path)) as connection:
            row = connection.execute(
                "select status, request_config_json from connector_run where connector_run_id = ?",
                (binding.run_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_request_config_unreadable",
            "A required full-corpus comparison run request config could not be read.",
            http_status=409,
            details={"run_id": binding.run_id, "reason": str(exc)},
        ) from exc
    if row is None:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_connector_run_missing",
            "A required full-corpus comparison connector_run row is missing.",
            http_status=409,
            details={"run_id": binding.run_id},
        )
    status, raw_config = row
    if str(status or "") != "completed":
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_connector_run_not_completed",
            "A required full-corpus comparison connector_run is not completed.",
            http_status=409,
            details={"run_id": binding.run_id, "status": status},
        )
    try:
        config = json.loads(raw_config) if isinstance(raw_config, str) else dict(raw_config or {})
    except (TypeError, json.JSONDecodeError) as exc:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_request_config_invalid",
            "A required full-corpus comparison request config is invalid.",
            http_status=409,
            details={"run_id": binding.run_id},
        ) from exc
    if not isinstance(config, dict):
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_request_config_not_object",
            "A required full-corpus comparison request config is not an object.",
            http_status=409,
            details={"run_id": binding.run_id},
        )
    return config


def _validate_full_corpus_request_config(
    request_config: Mapping[str, Any],
    *,
    label: str,
    run_id: str,
    expected_engine: str,
    expected_visual_lane: str,
) -> None:
    observed_engine = str(request_config.get("document_processing_engine") or BASELINE_ENGINE).strip()
    observed_visual_lane = str(request_config.get("visual_lane_mode") or BASELINE_ENGINE).strip()
    if observed_engine != expected_engine:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_request_engine_mismatch",
            "A required full-corpus comparison request config has the wrong document-processing engine.",
            http_status=409,
            details={"run_id": run_id, "observed": observed_engine, "expected": expected_engine},
        )
    if request_config.get("document_processing_engine_explicit") is not True:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_request_engine_not_explicit",
            "A required full-corpus comparison run must prove explicit document-processing engine selection.",
            http_status=409,
            details={"run_id": run_id},
        )
    if observed_visual_lane != expected_visual_lane:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_request_visual_lane_mismatch",
            "A required full-corpus comparison request config has the wrong visual-lane mode.",
            http_status=409,
            details={"run_id": run_id, "observed": observed_visual_lane, "expected": expected_visual_lane},
        )


def _validate_full_corpus_gate_results(summary: Mapping[str, Any], *, label: str, run_id: str) -> None:
    gate_results = summary.get("gate_results")
    if not isinstance(gate_results, dict):
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_gate_results_missing",
            "A required full-corpus comparison summary has no validate-only gate results.",
            http_status=409,
            details={"run_id": run_id},
        )
    missing_or_failed = [
        gate_name
        for gate_name in REQUIRED_FULL_CORPUS_GATE_NAMES
        if not isinstance(gate_results.get(gate_name), dict) or gate_results[gate_name].get("passed") is not True
    ]
    if missing_or_failed:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_gate_results_failed",
            "A required full-corpus comparison summary has missing or failed validate-only gates.",
            http_status=409,
            details={"run_id": run_id, "missing_or_failed": missing_or_failed},
        )


def _validate_full_corpus_metrics(
    summary: Mapping[str, Any],
    *,
    label: str,
    run_id: str,
    require_candidate_b_metrics: bool,
) -> None:
    metrics = summary.get("advanced_metrics")
    if not isinstance(metrics, dict):
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_metrics_missing",
            "A required full-corpus comparison summary has no advanced metrics.",
            http_status=409,
            details={"run_id": run_id},
        )
    candidate_b_extractor_count = _int_metric(metrics.get("candidate_b_extractor_file_count"))
    if require_candidate_b_metrics:
        if candidate_b_extractor_count != FULL_CORPUS_TARGET_COUNT:
            raise CandidateBRuntimeBridgeError(
                "candidate_b_full_corpus_bridge_candidate_b_extractor_count_mismatch",
                "Candidate B did not use the admitted runtime extractor for every full-corpus target.",
                http_status=409,
                details={"run_id": run_id, "candidate_b_extractor_file_count": candidate_b_extractor_count},
            )
        if _int_metric(metrics.get("candidate_b_ordered_unit_total")) <= 0:
            raise CandidateBRuntimeBridgeError(
                "candidate_b_full_corpus_bridge_candidate_b_ordered_units_missing",
                "Candidate B full-corpus evidence has no ordered-unit material.",
                http_status=409,
                details={"run_id": run_id},
            )
        if _int_metric(metrics.get("candidate_b_visual_ref_total")) <= 0:
            raise CandidateBRuntimeBridgeError(
                "candidate_b_full_corpus_bridge_candidate_b_visual_refs_missing",
                "Candidate B full-corpus evidence has no visual refs.",
                http_status=409,
                details={"run_id": run_id},
            )
        if _int_metric(metrics.get("candidate_b_retained_source_pdf_ref_count")) <= 0:
            raise CandidateBRuntimeBridgeError(
                "candidate_b_full_corpus_bridge_candidate_b_source_pdf_refs_missing",
                "Candidate B full-corpus evidence has no retained source-PDF refs.",
                http_status=409,
                details={"run_id": run_id},
            )
    elif candidate_b_extractor_count != 0:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_candidate_b_extractor_leak",
            "Baseline/Candidate A comparison evidence unexpectedly used Candidate B extractors.",
            http_status=409,
            details={"run_id": run_id, "candidate_b_extractor_file_count": candidate_b_extractor_count},
        )


def _full_corpus_targets(binding: ReviewRuntimeBinding, *, label: str) -> list[dict[str, Any]]:
    raw_targets = binding.summary.get("target_outcomes")
    if not isinstance(raw_targets, list):
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_targets_missing",
            "A required full-corpus comparison summary has no target outcomes.",
            http_status=409,
            details={"run_id": binding.run_id},
        )
    targets: list[dict[str, Any]] = []
    for item in raw_targets:
        if not isinstance(item, dict):
            raise CandidateBRuntimeBridgeError(
                f"candidate_b_full_corpus_bridge_{label}_target_invalid",
                "A required full-corpus comparison target outcome is invalid.",
                http_status=409,
                details={"run_id": binding.run_id},
            )
        target_id = str(item.get("target_id") or "").strip()
        accession_number = str(item.get("accession_number") or "").strip()
        ordinal = _optional_int(item.get("ordinal"))
        status = str(item.get("status") or "").strip()
        if not target_id or not accession_number or ordinal <= 0:
            raise CandidateBRuntimeBridgeError(
                f"candidate_b_full_corpus_bridge_{label}_target_identity_incomplete",
                "A required full-corpus comparison target lacks target id, accession, or ordinal.",
                http_status=409,
                details={"run_id": binding.run_id},
            )
        targets.append(
            {
                "target_id": target_id,
                "ordinal": ordinal,
                "accession_number": accession_number,
                "status": status,
            }
        )
    targets.sort(key=lambda item: int(item["ordinal"]))
    if len(targets) != FULL_CORPUS_TARGET_COUNT:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_target_count_mismatch",
            "A required full-corpus comparison summary does not have 69 target outcomes.",
            http_status=409,
            details={"run_id": binding.run_id, "target_count": len(targets)},
        )
    status_counts = dict(sorted(Counter(item["status"] for item in targets).items()))
    if status_counts != {"recommended": FULL_CORPUS_TARGET_COUNT}:
        raise CandidateBRuntimeBridgeError(
            f"candidate_b_full_corpus_bridge_{label}_target_status_mismatch",
            "A required full-corpus comparison summary does not recommend every target.",
            http_status=409,
            details={"run_id": binding.run_id, "status_counts": status_counts},
        )
    return targets


def _target_identity_for_hash(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"ordinal": item["ordinal"], "accession_number": item["accession_number"]}
        for item in targets
    ]


def _optional_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _int_metric(value: Any) -> int:
    return _optional_int(value)


def _redacted_ref(value: str) -> str:
    return f"redacted://sha256/{hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:24]}"


def _material_files(binding: ReviewRuntimeBinding, compare_target_set: Mapping[str, Any]) -> list[dict[str, Any]]:
    files = [
        _json_material("runtime-summary.json", _redact_json_value(binding.summary)[0], "candidate_b_runtime_summary"),
        _json_material("compare-targets.json", compare_target_set, "candidate_b_runtime_compare_targets"),
    ]
    full_corpus_material_subset = str(compare_target_set.get("compare_scope") or "") == "full_corpus"
    session_cm = runtime_db_session_for_binding(binding) if binding.database_path else nullcontext(None)
    with session_cm as session:
        for target in compare_target_set["targets"]:
            target_key = _target_material_key(target)
            target_id = target["candidate_b_target_id"]
            trace_payload = None
            if not full_corpus_material_subset:
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
                    details={"candidate_b_run_id": binding.run_id, "target_key": target_key},
                )
            if not full_corpus_material_subset:
                files.append(
                    _json_material(f"trace/{target_key}.json", trace_payload or {}, "candidate_b_runtime_trace")
                )
                files.append(
                    _json_material(
                        f"normalized/{target_key}.json",
                        normalized_payload,
                        "candidate_b_runtime_normalized_text",
                    )
                )
            files.append(
                _bytes_material(
                    f"text/{target_key}.md",
                    _markdown_for_target(binding.run_id, target, normalized_payload).encode("utf-8"),
                    "candidate_b_runtime_text_markdown",
                )
            )
    return files


def _target_material_key(target: Mapping[str, Any]) -> str:
    raw = str(target.get("fixture_id") or target.get("target_key") or "").strip()
    if not raw:
        raise CandidateBRuntimeBridgeError(
            "candidate_b_runtime_bridge_target_key_missing",
            "A comparable Candidate B runtime target is missing a material key.",
            http_status=409,
        )
    return raw.replace("\\", "-").replace("/", "-")


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
    target_key = _target_material_key(target)
    return (
        f"# Candidate B runtime material: {target_key}\n\n"
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


def _runtime_validation(binding: ReviewRuntimeBinding, *, bridge_mode: str = BRIDGE_MODE) -> dict[str, Any]:
    metadata = runtime_binding_request_metadata(binding)
    validated_by = [
        "current_main_runtime_discovery",
        "candidate_b_opendataloader_pdf_variant_classification",
        "document_trace_normalized_text_materialization",
    ]
    if bridge_mode == FULL_CORPUS_BRIDGE_MODE:
        validated_by.append("candidate_b_full_corpus_compare_triplet_v1")
    else:
        validated_by.append("workbench_compare_target_set")
    return {
        "status": "passed",
        "validated_by": validated_by,
        "candidate_b_run_id": binding.run_id,
        "document_processing_engine": CANDIDATE_B_RUNTIME_VARIANT,
        "visual_lane_mode": metadata.get("visual_lane_mode", "baseline"),
    }


def _candidate_b_visual_lane_evidence(binding: ReviewRuntimeBinding) -> dict[str, Any]:
    metadata = runtime_binding_request_metadata(binding)
    visual_lane_mode = str(metadata.get("visual_lane_mode") or "baseline").strip().lower() or "baseline"
    metrics = dict(binding.summary.get("advanced_metrics") or {})
    candidate_b_visual_lane_selected = visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE
    return {
        "visual_lane_mode": visual_lane_mode,
        "candidate_b_visual_lane_selected": candidate_b_visual_lane_selected,
        "candidate_b_visual_lane_mode": CANDIDATE_B_VISUAL_LANE_MODE,
        "visual_ref_total": int(metrics.get("visual_ref_total") or 0),
        "candidate_b_visual_ref_total": int(metrics.get("candidate_b_visual_ref_total") or 0),
        "candidate_b_retained_source_pdf_ref_count": int(
            metrics.get("candidate_b_retained_source_pdf_ref_count") or 0
        ),
        "source_pdf_material_text_payload_enabled": False,
        "image_material_text_payload_enabled": False,
        "evidence_source": "runtime_summary_advanced_metrics",
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
        "policy": "not_material_text_payload_retained_in_governed_artifact_family",
        "excluded_file_count": len(excluded_refs),
        "excluded_extension_counts": dict(sorted(extension_counts.items())),
        "excluded_refs": excluded_refs[:50],
        "excluded_refs_truncated": len(excluded_refs) > 50,
    }


def _governed_retained_artifact_family(
    binding: ReviewRuntimeBinding,
    curated_files: list[dict[str, Any]],
) -> dict[str, Any]:
    material_payloads = [
        _curated_artifact_ref(item)
        for item in sorted(curated_files, key=lambda item: str(item["relative_name"]))
    ]
    retained_runtime_refs = _retained_runtime_refs(binding)
    visual_evidence = [
        item
        for item in retained_runtime_refs
        if item["artifact_role"] in {"source_pdf", "extracted_image", "visual_page_evidence"}
    ]
    provenance_artifacts = material_payloads + retained_runtime_refs
    product_artifacts = [
        item
        for item in retained_runtime_refs
        if item["artifact_role"] in {"source_pdf", "extracted_image", "normalized_text_source"}
    ]
    delivery_artifacts = [
        item
        for item in retained_runtime_refs
        if item["artifact_role"] in {"source_pdf", "extracted_image", "normalized_text_source"}
    ]
    classification = {
        "policy": "candidate_b_full_artifact_family_retained_but_text_material_payload_bounded",
        "candidate_b_source_kind": "runtime",
        "material_text_payload_policy": "document_trace_json_md_only",
        "pdf_material_text_payload_enabled": False,
        "image_material_text_payload_enabled": False,
        "raw_url_exposure_enabled": False,
        "roles": {
            "material_analysis_payloads": material_payloads,
            "visual_page_evidence": visual_evidence,
            "provenance_audit_artifacts": provenance_artifacts,
            "product_inspection_artifacts": product_artifacts,
            "delivery_artifacts": delivery_artifacts,
        },
    }
    classification["role_counts"] = {
        role: len(items) for role, items in classification["roles"].items()
    }
    classification["artifact_family_hash"] = _stable_hash(
        {"hash_version": AUTHORITY_HASH_VERSION, "classification": classification}
    )
    return classification


def _curated_artifact_ref(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_ref": item["source_ref"],
        "relative_name": item["relative_name"],
        "artifact_role": "material_analysis_payload",
        "category": item["category"],
        "extension": item["extension"],
        "sha256": item["content_sha256"],
        "size_bytes": item["content_size_bytes"],
        "material_text_payload": True,
    }


def _retained_runtime_refs(binding: ReviewRuntimeBinding) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    root = binding.review_root.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            relative_ref = path.resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        extension = path.suffix.lower() or "<none>"
        refs.append(
            {
                "source_ref": relative_ref,
                "artifact_role": _runtime_artifact_role(relative_ref, extension),
                "extension": extension,
                "sha256": _file_sha256(path),
                "size_bytes": path.stat().st_size,
                "material_text_payload": False,
            }
        )
    return refs


def _runtime_artifact_role(relative_ref: str, extension: str) -> str:
    if extension == ".pdf":
        return "source_pdf"
    if extension in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}:
        return "extracted_image"
    if extension in {".db", ".sqlite"}:
        return "runtime_database"
    if extension == ".txt":
        return "normalized_text_source"
    if relative_ref.startswith("storage/"):
        return "runtime_storage_blob"
    return "runtime_review_artifact"


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
        "mode": receipt["bridge_mode"],
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
        "visual_lane_mode": receipt["visual_lane_mode"],
        "candidate_b_runtime_validation": receipt["candidate_b_runtime_validation"],
        "candidate_b_visual_lane_evidence": receipt["candidate_b_visual_lane_evidence"],
        "compare_target_set": receipt["compare_target_set"],
        "admitted_artifact_subset": receipt["admitted_artifact_subset"],
        "excluded_artifact_subset": receipt["excluded_artifact_subset"],
        "governed_retained_artifact_family": receipt["governed_retained_artifact_family"],
        "authority_hashes": {
            "bridge_receipt_hash": receipt["bridge_receipt_hash"],
            "compare_target_set_hash": receipt["compare_target_set_hash"],
            "runtime_review_root_storage_authority_hash": receipt["runtime_review_root_storage_authority_hash"],
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


def _negative_invariants(*, visual_lane_mode: str = "baseline") -> dict[str, bool]:
    return {
        "baseline_default_changed": False,
        "candidate_a_semantics_changed": False,
        "candidate_b_visual_lane_mode_enabled": visual_lane_mode == CANDIDATE_B_VISUAL_LANE_MODE,
        "candidate_b_visual_lane_material_ingestion_enabled": False,
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
