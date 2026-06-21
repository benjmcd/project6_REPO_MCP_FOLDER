from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_SCHEMA_ID = "aps.full_corpus_compare_triplet_validation.v1"
SUMMARY_SCHEMA_VERSION = 1
LOCAL_CORPUS_SUMMARY_SCHEMA_ID = "aps.local_corpus_e2e_summary.v1"
DEFAULT_RUNTIME_PARENT = ROOT / "backend" / "app" / "storage_test_runtime" / "lc_e2e"
ADMITTED_CORPUS_ROOT_RELATIVE = Path("data_demo") / "nrc_adams_documents_for_testing"
ADMITTED_TARGET_SET_AUTHORITY = "tracked_nrc_aps_local_corpus_pdf_filenames_v1"
EXPECTED_CORPUS_PDF_COUNT = 69
BASELINE_ENGINE = "baseline"
CANDIDATE_A_VISUAL_LANE = "candidate_a_page_evidence_v1"
CANDIDATE_B_ENGINE = "candidate_b_opendataloader_pdf"
CANDIDATE_B_VISUAL_LANE = "candidate_b_opendataloader_page_evidence_v1"
REQUIRED_GATE_NAMES = (
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


class ValidationError(RuntimeError):
    def __init__(self, code: str, detail: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.context = context or {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate same-checkout baseline, Candidate A, and Candidate B full-corpus "
            "NRC APS local-corpus proof receipts without seeding or generating artifacts."
        )
    )
    parser.add_argument(
        "--checkout-root",
        default="",
        help="Optional checkout root override. Defaults to the repository containing this tool.",
    )
    parser.add_argument(
        "--baseline-run-root",
        default="",
        help="Optional explicit runtime root for the baseline full-corpus receipt.",
    )
    parser.add_argument(
        "--candidate-a-run-root",
        default="",
        help="Optional explicit runtime root for the Candidate A PageEvidence full-corpus receipt.",
    )
    parser.add_argument(
        "--candidate-b-run-root",
        default="",
        help="Optional explicit runtime root for the Candidate B OpenDataLoader full-corpus receipt.",
    )
    parser.add_argument(
        "--corpus-root",
        default=os.environ.get("NRC_CORPUS_ROOT", ""),
        help=(
            "Override the admitted corpus root directory. "
            f"Defaults to <checkout-root>/{ADMITTED_CORPUS_ROOT_RELATIVE} "
            "(or NRC_CORPUS_ROOT env if set). The directory must exist. "
            "Requires --allow-unadmitted-corpus when the path differs from the default."
        ),
    )
    parser.add_argument(
        "--allow-unadmitted-corpus",
        action="store_true",
        default=False,
        help=(
            "Permit validation against a non-admitted corpus root. "
            "Required when --corpus-root (or NRC_CORPUS_ROOT) points to a path other than the "
            f"default admitted corpus (<checkout-root>/{ADMITTED_CORPUS_ROOT_RELATIVE})."
        ),
    )
    return parser


def _checkout_root(raw_value: str) -> Path:
    candidate = Path(raw_value).resolve() if str(raw_value).strip() else ROOT.resolve()
    if not candidate.exists() or not candidate.is_dir():
        raise ValidationError("checkout_root_missing", f"Checkout root is unavailable: {candidate}")
    return candidate


def _runtime_parent(checkout_root: Path) -> Path:
    return checkout_root / "backend" / "app" / "storage_test_runtime" / "lc_e2e"


def _admitted_corpus_root(checkout_root: Path) -> Path:
    return checkout_root / ADMITTED_CORPUS_ROOT_RELATIVE


def _repo_rel(checkout_root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(checkout_root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError("summary_missing", f"Summary file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError("summary_invalid_json", f"Summary file is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValidationError("summary_not_object", f"Summary file is not a JSON object: {path}")
    return payload


def _summary_path(runtime_root: Path) -> Path:
    return runtime_root / "local_corpus_e2e_summary.json"


def _walk_admitted_corpus_pdfs(corpus_root: Path) -> list[Path]:
    pdfs: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(str(corpus_root)):
        dirnames.sort(key=str.lower)
        for filename in sorted(filenames, key=str.lower):
            if Path(filename).suffix.lower() == ".pdf":
                pdfs.append(Path(dirpath) / filename)
    return pdfs


def _extract_admitted_accession(stem: str, *, ordinal: int, seen: set[str]) -> str:
    match = re.search(r"\b(ML\d{6,})\b", stem, flags=re.IGNORECASE)
    accession = match.group(1).upper() if match else f"LOCALAPS{ordinal:05d}"
    if accession in seen:
        raise ValidationError(
            "admitted_corpus_accession_duplicate",
            "The admitted NRC APS local-corpus source has duplicate accession numbers.",
            context={"accession_number": accession},
        )
    seen.add(accession)
    return accession


def _admitted_accession_identities(checkout_root: Path, *, corpus_root: Path | None = None) -> list[dict[str, Any]]:
    resolved_corpus_root = corpus_root if corpus_root is not None else _admitted_corpus_root(checkout_root)
    if not resolved_corpus_root.is_dir():
        raise ValidationError(
            "admitted_corpus_root_missing",
            "The admitted NRC APS full-corpus source directory is unavailable.",
            context={"admitted_corpus_root": _repo_rel(checkout_root, resolved_corpus_root)},
        )
    grouped: dict[str, list[Path]] = {}
    for pdf_path in _walk_admitted_corpus_pdfs(resolved_corpus_root.resolve()):
        relative = pdf_path.relative_to(resolved_corpus_root.resolve())
        group_name = relative.parts[0] if len(relative.parts) > 1 else "__corpus_root__"
        grouped.setdefault(group_name, []).append(pdf_path)

    identities: list[dict[str, Any]] = []
    seen: set[str] = set()
    ordinal = 0
    for group_name in sorted(grouped, key=str.lower):
        for pdf_path in grouped[group_name]:
            ordinal += 1
            identities.append(
                {
                    "ordinal": ordinal,
                    "accession_number": _extract_admitted_accession(
                        pdf_path.stem,
                        ordinal=ordinal,
                        seen=seen,
                    ),
                }
            )
    if len(identities) != EXPECTED_CORPUS_PDF_COUNT:
        raise ValidationError(
            "admitted_corpus_target_count_invalid",
            "The admitted NRC APS full-corpus source must contain exactly 69 PDF targets.",
            context={"target_count": len(identities), "expected": EXPECTED_CORPUS_PDF_COUNT},
        )
    return identities


def _admitted_target_set_authority(checkout_root: Path, *, corpus_root: Path | None = None) -> dict[str, Any]:
    identities = _admitted_accession_identities(checkout_root, corpus_root=corpus_root)
    return {
        "authority": ADMITTED_TARGET_SET_AUTHORITY,
        "target_count": EXPECTED_CORPUS_PDF_COUNT,
        "target_set_hash": _target_set_hash(identities),
        "accession_head": [item["accession_number"] for item in identities[:3]],
        "accession_tail": [item["accession_number"] for item in identities[-3:]],
    }


def _resolve_explicit_runtime_root(raw_value: str, *, checkout_root: Path, label: str) -> Path | None:
    if not str(raw_value).strip():
        return None
    candidate = Path(raw_value)
    if not candidate.is_absolute():
        candidate = checkout_root / candidate
    candidate = candidate.resolve()
    runtime_parent = _runtime_parent(checkout_root)
    if not _is_within(candidate, runtime_parent):
        raise ValidationError(
            f"{label}_runtime_root_outside_admitted_parent",
            f"Explicit {label} runtime root is outside the same-checkout full-corpus runtime parent.",
            context={"runtime_root": str(candidate), "admitted_runtime_parent": str(runtime_parent.resolve())},
        )
    if not _summary_path(candidate).is_file():
        raise ValidationError(
            "explicit_summary_missing",
            f"Explicit runtime root has no local_corpus_e2e_summary.json: {candidate}",
        )
    return candidate


def _summary_sort_key(summary: dict[str, Any], runtime_root: Path) -> tuple[str, float]:
    generated = str(summary.get("generated_at_utc") or "")
    try:
        mtime = _summary_path(runtime_root).stat().st_mtime
    except OSError:
        mtime = 0.0
    return generated, mtime


def _summary_matches_variant(summary: dict[str, Any], *, engine: str, visual_lane: str) -> bool:
    if str(summary.get("schema_id") or "") != LOCAL_CORPUS_SUMMARY_SCHEMA_ID:
        return False
    if summary.get("passed") is not True:
        return False
    if str(summary.get("document_processing_engine") or BASELINE_ENGINE) != engine:
        return False
    return str(summary.get("visual_lane_mode") or BASELINE_ENGINE) == visual_lane


def _summary_matches_full_corpus_targets(summary: dict[str, Any], *, label: str) -> bool:
    try:
        _require_int(summary, "corpus_pdf_count", expected=EXPECTED_CORPUS_PDF_COUNT, label=label)
        _target_identity(summary, label=label)
    except ValidationError:
        return False
    return True


def _discover_latest_runtime_root(
    checkout_root: Path,
    *,
    label: str,
    engine: str,
    visual_lane: str,
) -> Path:
    parent = _runtime_parent(checkout_root)
    if not parent.is_dir():
        raise ValidationError(
            f"{label}_runtime_parent_missing",
            f"Full-corpus runtime parent is unavailable: {parent}",
        )
    matches: list[tuple[tuple[str, float], Path]] = []
    for candidate in parent.iterdir():
        if not candidate.is_dir():
            continue
        resolved_candidate = candidate.resolve()
        if not _is_within(resolved_candidate, parent):
            raise ValidationError(
                f"{label}_runtime_root_outside_admitted_parent",
                f"Discovered {label} runtime root is outside the same-checkout full-corpus runtime parent.",
                context={"runtime_root": str(resolved_candidate), "admitted_runtime_parent": str(parent.resolve())},
            )
        summary_file = _summary_path(candidate)
        if not summary_file.is_file():
            continue
        try:
            summary = _load_json(summary_file)
        except ValidationError:
            continue
        if _summary_matches_variant(
            summary,
            engine=engine,
            visual_lane=visual_lane,
        ) and _summary_matches_full_corpus_targets(summary, label=label):
            matches.append((_summary_sort_key(summary, candidate), candidate.resolve()))
    if not matches:
        raise ValidationError(
            f"{label}_run_missing",
            f"No passed full-corpus {label} receipt is available in {parent}",
        )
    matches.sort(key=lambda item: item[0])
    return matches[-1][1]


def _run_root(
    explicit_root: str,
    *,
    checkout_root: Path,
    label: str,
    engine: str,
    visual_lane: str,
) -> Path:
    explicit = _resolve_explicit_runtime_root(explicit_root, checkout_root=checkout_root, label=label)
    if explicit is not None:
        summary = _load_json(_summary_path(explicit))
        if not _summary_matches_variant(summary, engine=engine, visual_lane=visual_lane):
            raise ValidationError(
                f"{label}_variant_mismatch",
                f"Explicit {label} runtime root does not match the required full-corpus variant.",
                context={
                    "required_document_processing_engine": engine,
                    "required_visual_lane_mode": visual_lane,
                    "observed_document_processing_engine": summary.get("document_processing_engine"),
                    "observed_visual_lane_mode": summary.get("visual_lane_mode"),
                },
            )
        return explicit
    return _discover_latest_runtime_root(checkout_root, label=label, engine=engine, visual_lane=visual_lane)


def _require_int(summary: dict[str, Any], key: str, *, expected: int, label: str) -> None:
    observed = summary.get(key)
    if observed != expected:
        raise ValidationError(
            f"{label}_{key}_mismatch",
            f"{label} expected {key}={expected}; observed {observed}",
            context={"observed": observed, "expected": expected},
        )


def _status_counts(targets: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(item.get("status") or "") for item in targets).items()))


def _target_identity(summary: dict[str, Any], *, label: str) -> list[dict[str, Any]]:
    raw_targets = summary.get("target_outcomes")
    if not isinstance(raw_targets, list):
        raise ValidationError(f"{label}_target_outcomes_missing", f"{label} summary has no target_outcomes list.")
    identities: list[dict[str, Any]] = []
    for item in raw_targets:
        if not isinstance(item, dict):
            raise ValidationError(f"{label}_target_outcome_invalid", f"{label} target_outcomes contains a non-object.")
        accession_number = str(item.get("accession_number") or "").strip()
        ordinal = item.get("ordinal")
        status = str(item.get("status") or "").strip()
        if not accession_number or not isinstance(ordinal, int):
            raise ValidationError(
                f"{label}_target_identity_incomplete",
                f"{label} target_outcomes contains a target without accession_number or ordinal.",
            )
        identities.append({"ordinal": ordinal, "accession_number": accession_number, "status": status})
    identities.sort(key=lambda item: int(item["ordinal"]))
    if len(identities) != EXPECTED_CORPUS_PDF_COUNT:
        raise ValidationError(
            f"{label}_target_count_mismatch",
            f"{label} expected {EXPECTED_CORPUS_PDF_COUNT} target outcomes; observed {len(identities)}.",
        )
    counts = _status_counts(identities)
    if counts != {"recommended": EXPECTED_CORPUS_PDF_COUNT}:
        raise ValidationError(
            f"{label}_target_status_mismatch",
            f"{label} expected every target to be recommended.",
            context={"status_counts": counts},
        )
    return identities


def _stable_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _target_set_hash(identities: list[dict[str, Any]]) -> str:
    compact = [
        {"ordinal": item["ordinal"], "accession_number": item["accession_number"]}
        for item in identities
    ]
    return _stable_hash(compact)


def _validate_gate_results(summary: dict[str, Any], *, label: str) -> dict[str, str]:
    raw_gates = summary.get("gate_results")
    if not isinstance(raw_gates, dict):
        raise ValidationError(f"{label}_gate_results_missing", f"{label} summary has no gate_results object.")
    status: dict[str, str] = {}
    for gate_name in REQUIRED_GATE_NAMES:
        payload = raw_gates.get(gate_name)
        if not isinstance(payload, dict):
            raise ValidationError(
                f"{label}_gate_missing",
                f"{label} is missing required validate-only gate: {gate_name}",
            )
        if payload.get("passed") is not True:
            raise ValidationError(
                f"{label}_gate_failed",
                f"{label} validate-only gate did not pass: {gate_name}",
                context={"gate": gate_name},
            )
        status[gate_name] = "passed"
    return status


def _database_path(summary: dict[str, Any], *, runtime_root: Path, label: str) -> Path:
    raw_database_path = str(summary.get("database_path") or "").strip()
    database_path = Path(raw_database_path) if raw_database_path else runtime_root / "lc.db"
    if not database_path.is_absolute():
        database_path = runtime_root / database_path
    database_path = database_path.resolve()
    if not _is_within(database_path, runtime_root):
        raise ValidationError(
            f"{label}_database_outside_runtime_root",
            f"{label} summary database_path is outside the selected same-checkout runtime root.",
            context={"database_path": str(database_path), "runtime_root": str(runtime_root.resolve())},
        )
    return database_path


def _read_request_config(summary: dict[str, Any], *, runtime_root: Path, label: str) -> dict[str, Any]:
    database_path = _database_path(summary, runtime_root=runtime_root, label=label)
    run_id = str(summary.get("run_id") or "").strip()
    if not run_id:
        raise ValidationError(f"{label}_run_id_missing", f"{label} summary has no run_id.")
    if not database_path.is_file():
        raise ValidationError(f"{label}_database_missing", f"{label} runtime database is missing.")
    try:
        with sqlite3.connect(database_path) as connection:
            row = connection.execute(
                "select status, request_config_json from connector_run where connector_run_id = ?",
                (run_id,),
            ).fetchone()
    except sqlite3.Error as exc:
        raise ValidationError(f"{label}_database_unreadable", f"{label} runtime database is unreadable.") from exc
    if row is None:
        raise ValidationError(
            f"{label}_connector_run_missing",
            f"{label} connector_run row is missing for the summary run_id.",
        )
    status, raw_config = row
    if str(status or "") != "completed":
        raise ValidationError(
            f"{label}_connector_run_not_completed",
            f"{label} connector_run status is not completed.",
            context={"status": status},
        )
    try:
        config = json.loads(raw_config) if isinstance(raw_config, str) else dict(raw_config or {})
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{label}_request_config_invalid", f"{label} request_config_json is invalid.") from exc
    if not isinstance(config, dict):
        raise ValidationError(f"{label}_request_config_not_object", f"{label} request_config_json is not an object.")
    return config


def _validate_request_config(
    config: dict[str, Any],
    *,
    label: str,
    engine: str,
    visual_lane: str,
    require_explicit_engine: bool,
) -> dict[str, Any]:
    observed_engine = str(config.get("document_processing_engine") or BASELINE_ENGINE)
    observed_visual = str(config.get("visual_lane_mode") or BASELINE_ENGINE)
    engine_explicit = config.get("document_processing_engine_explicit") is True
    if observed_engine != engine:
        raise ValidationError(
            f"{label}_request_engine_mismatch",
            f"{label} request_config_json has the wrong document_processing_engine.",
            context={"observed": observed_engine, "expected": engine},
        )
    if require_explicit_engine and not engine_explicit:
        raise ValidationError(
            f"{label}_request_engine_not_explicit",
            f"{label} must prove explicit document_processing_engine selection.",
        )
    if observed_visual != visual_lane:
        raise ValidationError(
            f"{label}_request_visual_lane_mismatch",
            f"{label} request_config_json has the wrong visual_lane_mode.",
            context={"observed": observed_visual, "expected": visual_lane},
        )
    return {
        "document_processing_engine": observed_engine,
        "document_processing_engine_explicit": engine_explicit,
        "visual_lane_mode": observed_visual,
    }


def _metrics(summary: dict[str, Any], *, label: str) -> dict[str, Any]:
    raw_metrics = summary.get("advanced_metrics")
    if not isinstance(raw_metrics, dict):
        raise ValidationError(f"{label}_advanced_metrics_missing", f"{label} summary has no advanced_metrics object.")
    return raw_metrics


def _optional_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _validate_metrics(metrics: dict[str, Any], *, label: str, engine: str) -> dict[str, int]:
    payload = {
        "ocr_file_count": _optional_int(metrics.get("ocr_file_count")),
        "table_file_count": _optional_int(metrics.get("table_file_count")),
        "candidate_b_extractor_file_count": _optional_int(metrics.get("candidate_b_extractor_file_count")),
        "candidate_b_ordered_unit_file_count": _optional_int(metrics.get("candidate_b_ordered_unit_file_count")),
        "candidate_b_ordered_unit_total": _optional_int(metrics.get("candidate_b_ordered_unit_total")),
        "candidate_b_visual_ref_total": _optional_int(metrics.get("candidate_b_visual_ref_total")),
        "candidate_b_retained_source_pdf_ref_count": _optional_int(
            metrics.get("candidate_b_retained_source_pdf_ref_count")
        ),
    }
    if engine == BASELINE_ENGINE:
        if payload["ocr_file_count"] <= 0:
            raise ValidationError(f"{label}_ocr_not_exercised", f"{label} did not exercise OCR-derived extraction.")
        if payload["table_file_count"] <= 0:
            raise ValidationError(f"{label}_table_not_exercised", f"{label} did not exercise table extraction.")
        if payload["candidate_b_extractor_file_count"] != 0:
            raise ValidationError(f"{label}_candidate_b_extractor_leak", f"{label} used Candidate B extractors.")
        return payload
    if payload["candidate_b_extractor_file_count"] != EXPECTED_CORPUS_PDF_COUNT:
        raise ValidationError(
            f"{label}_candidate_b_extractor_count_mismatch",
            f"{label} did not use Candidate B extraction for every corpus PDF.",
            context={"metrics": payload},
        )
    if payload["candidate_b_ordered_unit_file_count"] <= 0 or payload["candidate_b_ordered_unit_total"] <= 0:
        raise ValidationError(
            f"{label}_candidate_b_ordered_units_missing",
            f"{label} produced no Candidate B ordered-unit evidence.",
        )
    if payload["candidate_b_visual_ref_total"] <= 0 or payload["candidate_b_retained_source_pdf_ref_count"] <= 0:
        raise ValidationError(
            f"{label}_candidate_b_visual_refs_missing",
            f"{label} produced no retained Candidate B visual/source-PDF refs.",
        )
    return payload


def _validate_summary(
    runtime_root: Path,
    *,
    checkout_root: Path,
    label: str,
    engine: str,
    visual_lane: str,
    require_explicit_engine: bool,
) -> dict[str, Any]:
    summary = _load_json(_summary_path(runtime_root))
    if not _summary_matches_variant(summary, engine=engine, visual_lane=visual_lane):
        raise ValidationError(f"{label}_summary_variant_invalid", f"{label} summary variant is not valid.")
    _require_int(summary, "corpus_pdf_count", expected=EXPECTED_CORPUS_PDF_COUNT, label=label)
    identities = _target_identity(summary, label=label)
    gates = _validate_gate_results(summary, label=label)
    request_config = _validate_request_config(
        _read_request_config(summary, runtime_root=runtime_root, label=label),
        label=label,
        engine=engine,
        visual_lane=visual_lane,
        require_explicit_engine=require_explicit_engine,
    )
    metrics = _validate_metrics(_metrics(summary, label=label), label=label, engine=engine)
    return {
        "label": label,
        "run_id": str(summary.get("run_id") or ""),
        "runtime_root": _repo_rel(checkout_root, runtime_root),
        "document_processing_engine": engine,
        "visual_lane_mode": visual_lane,
        "target_identity": identities,
        "target_set_hash": _target_set_hash(identities),
        "target_status_counts": _status_counts(identities),
        "gate_results": gates,
        "request_config": request_config,
        "metrics": metrics,
    }


def validate_triplet(
    *,
    checkout_root: Path,
    baseline_run_root: Path,
    candidate_a_run_root: Path,
    candidate_b_run_root: Path,
    corpus_root: Path | None = None,
) -> dict[str, Any]:
    baseline = _validate_summary(
        baseline_run_root,
        checkout_root=checkout_root,
        label="baseline",
        engine=BASELINE_ENGINE,
        visual_lane=BASELINE_ENGINE,
        require_explicit_engine=True,
    )
    candidate_a = _validate_summary(
        candidate_a_run_root,
        checkout_root=checkout_root,
        label="candidate_a",
        engine=BASELINE_ENGINE,
        visual_lane=CANDIDATE_A_VISUAL_LANE,
        require_explicit_engine=True,
    )
    candidate_b = _validate_summary(
        candidate_b_run_root,
        checkout_root=checkout_root,
        label="candidate_b",
        engine=CANDIDATE_B_ENGINE,
        visual_lane=CANDIDATE_B_VISUAL_LANE,
        require_explicit_engine=True,
    )
    _validate_distinct_run_ids(
        {
            "baseline": baseline["run_id"],
            "candidate_a": candidate_a["run_id"],
            "candidate_b": candidate_b["run_id"],
        }
    )

    baseline_hash = baseline["target_set_hash"]
    mismatched = [
        label
        for label, payload in (("candidate_a", candidate_a), ("candidate_b", candidate_b))
        if payload["target_set_hash"] != baseline_hash
    ]
    if mismatched:
        raise ValidationError(
            "triplet_target_set_mismatch",
            "Baseline, Candidate A, and Candidate B do not share the same full-corpus target set.",
            context={"mismatched": mismatched},
        )
    admitted_target_set = _admitted_target_set_authority(checkout_root, corpus_root=corpus_root)
    if baseline_hash != admitted_target_set["target_set_hash"]:
        raise ValidationError(
            "triplet_target_set_not_admitted",
            "Baseline, Candidate A, and Candidate B share a target set that is not the admitted NRC APS full corpus.",
            context={
                "received_target_set_hash": baseline_hash,
                "admitted_target_set_hash": admitted_target_set["target_set_hash"],
                "admitted_target_set_authority": admitted_target_set["authority"],
            },
        )

    selected_runs = {
        "baseline": {key: baseline[key] for key in ("run_id", "runtime_root", "document_processing_engine", "visual_lane_mode")},
        "candidate_a": {
            key: candidate_a[key]
            for key in ("run_id", "runtime_root", "document_processing_engine", "visual_lane_mode")
        },
        "candidate_b": {
            key: candidate_b[key]
            for key in ("run_id", "runtime_root", "document_processing_engine", "visual_lane_mode")
        },
    }
    metrics = {
        "baseline": baseline["metrics"],
        "candidate_a": candidate_a["metrics"],
        "candidate_b": candidate_b["metrics"],
    }
    request_configs = {
        "baseline": baseline["request_config"],
        "candidate_a": candidate_a["request_config"],
        "candidate_b": candidate_b["request_config"],
    }
    gate_results = {
        "baseline": baseline["gate_results"],
        "candidate_a": candidate_a["gate_results"],
        "candidate_b": candidate_b["gate_results"],
    }

    return {
        "schema_id": SUMMARY_SCHEMA_ID,
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "passed": True,
        "validation_mode": "candidate_b_full_corpus_compare_triplet_v1",
        "validate_only": True,
        "artifacts_seeded_or_generated": False,
        "selected_runs": selected_runs,
        "corpus_pdf_count": EXPECTED_CORPUS_PDF_COUNT,
        "compare_target_set": {
            "target_count": EXPECTED_CORPUS_PDF_COUNT,
            "target_set_hash": baseline_hash,
            "admitted_target_set_hash": admitted_target_set["target_set_hash"],
            "admitted_target_set_authority": admitted_target_set["authority"],
            "accession_head": [
                item["accession_number"]
                for item in baseline["target_identity"][:3]
            ],
            "accession_tail": [
                item["accession_number"]
                for item in baseline["target_identity"][-3:]
            ],
        },
        "target_status_counts": {
            "baseline": baseline["target_status_counts"],
            "candidate_a": candidate_a["target_status_counts"],
            "candidate_b": candidate_b["target_status_counts"],
        },
        "request_configs": request_configs,
        "metrics": metrics,
        "gate_results": gate_results,
        "bridge_readiness": {
            "candidate_b_full_corpus_compare_triplet_v1": "validated",
            "candidate_b_full_corpus_runtime_to_layer3_material_authority_v1": (
                "requires_separate_current_main_admission"
            ),
            "existing_layer3_candidate_b_runtime_bridge_scope": "workbench_fixture_target_set",
        },
        "negative_invariants": {
            "baseline_default_changed": False,
            "candidate_a_semantics_changed": False,
            "candidate_b_default_broadened_beyond_eligible_pdf": False,
            "runtime_artifacts_seeded_by_validator": False,
        },
    }


def _validate_distinct_run_ids(run_ids: Mapping[str, str]) -> None:
    by_run_id: dict[str, list[str]] = {}
    for label, run_id in run_ids.items():
        normalized = str(run_id or "").strip()
        by_run_id.setdefault(normalized, []).append(label)
    duplicates = {
        run_id: labels
        for run_id, labels in by_run_id.items()
        if run_id and len(labels) > 1
    }
    if duplicates:
        raise ValidationError(
            "triplet_run_ids_not_distinct",
            "Baseline, Candidate A, and Candidate B summaries must use distinct run IDs.",
            context={"duplicates": duplicates},
        )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        checkout_root = _checkout_root(args.checkout_root)
        baseline_root = _run_root(
            args.baseline_run_root,
            checkout_root=checkout_root,
            label="baseline",
            engine=BASELINE_ENGINE,
            visual_lane=BASELINE_ENGINE,
        )
        candidate_a_root = _run_root(
            args.candidate_a_run_root,
            checkout_root=checkout_root,
            label="candidate_a",
            engine=BASELINE_ENGINE,
            visual_lane=CANDIDATE_A_VISUAL_LANE,
        )
        candidate_b_root = _run_root(
            args.candidate_b_run_root,
            checkout_root=checkout_root,
            label="candidate_b",
            engine=CANDIDATE_B_ENGINE,
            visual_lane=CANDIDATE_B_VISUAL_LANE,
        )
        _corpus_root_arg: str = args.corpus_root or ""
        corpus_root_override: Path | None = Path(_corpus_root_arg).resolve() if _corpus_root_arg else None
        effective_corpus_root = corpus_root_override if corpus_root_override is not None else _admitted_corpus_root(checkout_root)
        if corpus_root_override is not None and corpus_root_override.resolve() != _admitted_corpus_root(checkout_root).resolve():
            if not args.allow_unadmitted_corpus:
                raise ValidationError(
                    "unadmitted_corpus_root_requires_explicit_opt_in",
                    "pass --allow-unadmitted-corpus to validate against a non-admitted corpus root",
                    context={"effective_corpus_root": str(corpus_root_override), "admitted_corpus_root": str(_admitted_corpus_root(checkout_root))},
                )
            print(
                f"[validate_full_corpus_triplet] WARNING: corpus root overridden to {corpus_root_override} "
                f"(admitted default: {_admitted_corpus_root(checkout_root)})",
                file=sys.stderr,
            )
        payload = validate_triplet(
            checkout_root=checkout_root,
            baseline_run_root=baseline_root,
            candidate_a_run_root=candidate_a_root,
            candidate_b_run_root=candidate_b_root,
            corpus_root=corpus_root_override,
        )
    except ValidationError as exc:
        payload = {
            "schema_id": SUMMARY_SCHEMA_ID,
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "passed": False,
            "validate_only": True,
            "artifacts_seeded_or_generated": False,
            "error": {"code": exc.code, "detail": exc.detail, "context": exc.context},
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
