from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
TESTS_DIR = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from app.services.review_nrc_aps_candidate_b_trace import compose_candidate_b_trace_manifest  # noqa: E402
from app.services.review_nrc_aps_runtime import (  # noqa: E402
    ReviewRuntimeBinding,
    _binding_sort_key,
    binding_is_baseline_visible,
    classify_runtime_binding_variant,
    is_summary_backed,
    load_summary,
    resolve_runtime_database_path,
    resolve_runtime_storage_dir,
)
from app.services.review_nrc_aps_runtime_roots import candidate_review_runtime_roots  # noqa: E402
from app.services.review_nrc_aps_workbench_compare import (  # noqa: E402
    _bundle_documents_by_fixture,
    _candidate_b_trace_link,
    _canonical_bundle_id,
    _load_bundle_artifacts,
    _load_runtime_targets,
    _manifest_entries_by_basename,
    _trace_link,
    discover_candidate_b_bundle_roots,
)
from support_nrc_aps_candidate_b_opendataloader import FROZEN_FIXTURE_IDS  # noqa: E402


WORKBENCH_SEED_KIND = "workbench_compare_fixture_seed"
REQUIRED_FOLLOW_THROUGH_FIXTURES: tuple[str, ...] = ("fontish", "ml17123a319")
MIN_SHARED_FIXTURE_COUNT = 3
_CANDIDATE_B_RUNTIME_VARIANT = "candidate_b_opendataloader_pdf"
_CANDIDATE_B_SOURCE_KIND_BUNDLE = "bundle"
_CANDIDATE_B_SOURCE_KIND_RUNTIME = "runtime"
_POWERSHELL_SAFE_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.\\/=:")


class PreparedStateError(RuntimeError):
    def __init__(self, code: str, detail: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.context = context or {}


def _optional_int(value: Any) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the current checkout's same-checkout NRC APS workbench compare prep state."
    )
    parser.add_argument(
        "--checkout-root",
        default="",
        help="Optional checkout root override for isolated validation or tests.",
    )
    parser.add_argument(
        "--baseline-run-id",
        default="",
        help="Optional explicit baseline run id when multiple eligible seeded baseline runs exist.",
    )
    parser.add_argument(
        "--candidate-a-run-id",
        default="",
        help="Optional explicit Candidate A run id when multiple eligible seeded Candidate A runs exist.",
    )
    parser.add_argument(
        "--candidate-b-source-kind",
        choices=(_CANDIDATE_B_SOURCE_KIND_BUNDLE, _CANDIDATE_B_SOURCE_KIND_RUNTIME),
        default=_CANDIDATE_B_SOURCE_KIND_BUNDLE,
        help="Candidate B source to validate. Bundle mode remains the default Candidate B Trace prep gate.",
    )
    parser.add_argument(
        "--candidate-b-bundle-id",
        default="",
        help="Optional explicit Candidate B bundle id when multiple eligible bundles exist in bundle mode.",
    )
    parser.add_argument(
        "--candidate-b-run-id",
        default="",
        help="Required Candidate B runtime run id when --candidate-b-source-kind runtime is selected.",
    )
    parser.add_argument(
        "--fixture-id",
        default="",
        help="Optional explicit follow-through fixture id when multiple eligible fixtures exist.",
    )
    return parser


def _checkout_root(raw_value: str) -> Path:
    candidate = Path(raw_value).resolve() if str(raw_value).strip() else ROOT.resolve()
    if not candidate.exists() or not candidate.is_dir():
        raise PreparedStateError(
            "checkout_root_invalid",
            f"Checkout root is unavailable: {candidate}",
        )
    return candidate


def _repo_rel(checkout_root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    resolved = path.resolve()
    try:
        return resolved.relative_to(checkout_root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _checkout_root_display(checkout_root: Path) -> str:
    return str(checkout_root.resolve())


def _normalize_candidate_b_source_kind(value: str | None) -> str:
    normalized = str(value or _CANDIDATE_B_SOURCE_KIND_BUNDLE).strip().lower()
    if normalized not in {_CANDIDATE_B_SOURCE_KIND_BUNDLE, _CANDIDATE_B_SOURCE_KIND_RUNTIME}:
        raise PreparedStateError(
            "candidate_b_source_kind_invalid",
            f"Unsupported Candidate B source kind: {value}",
        )
    return normalized


def _binding_is_same_checkout(binding: ReviewRuntimeBinding, checkout_root: Path) -> bool:
    try:
        binding.review_root.resolve().relative_to(checkout_root.resolve())
    except ValueError:
        return False
    return True


def _normalized_fixture_ids(binding: ReviewRuntimeBinding) -> list[str]:
    raw_fixture_ids = binding.summary.get("corpus_fixture_ids")
    if not isinstance(raw_fixture_ids, list):
        return []
    return [str(item).strip().lower() for item in raw_fixture_ids if str(item).strip()]


def _binding_is_workbench_seed(
    binding: ReviewRuntimeBinding,
    *,
    expected_variant: str,
    checkout_root: Path,
) -> bool:
    if not _binding_is_same_checkout(binding, checkout_root):
        return False
    if classify_runtime_binding_variant(binding) != expected_variant:
        return False
    if str(binding.summary.get("seed_kind") or "").strip() != WORKBENCH_SEED_KIND:
        return False
    if binding.database_path is None or not binding.database_path.exists():
        return False
    if binding.storage_dir is None or not binding.storage_dir.exists():
        return False
    normalized_fixture_ids = _normalized_fixture_ids(binding)
    if normalized_fixture_ids != [fixture_id.lower() for fixture_id in FROZEN_FIXTURE_IDS]:
        return False
    corpus_pdf_count = _optional_int(binding.summary.get("corpus_pdf_count"))
    if corpus_pdf_count != len(FROZEN_FIXTURE_IDS):
        return False

    summary_visual_lane = str(binding.summary.get("visual_lane_mode") or "").strip().lower()
    summary_document_engine = str(binding.summary.get("document_processing_engine") or "").strip().lower()
    if expected_variant == "candidate_a_page_evidence_v1":
        return summary_visual_lane == "candidate_a_page_evidence_v1" and summary_document_engine in {"", "baseline"}
    if expected_variant == _CANDIDATE_B_RUNTIME_VARIANT:
        return summary_visual_lane in {"", "baseline"} and summary_document_engine == _CANDIDATE_B_RUNTIME_VARIANT
    return summary_visual_lane in {"", "baseline"} and summary_document_engine in {"", "baseline"}


def _discover_runtime_bindings_for_checkout(checkout_root: Path) -> list[ReviewRuntimeBinding]:
    app_root = checkout_root / "backend" / "app"
    backend_root = checkout_root / "backend"
    runtime_roots = candidate_review_runtime_roots(
        app_root=app_root,
        backend_root=backend_root,
        storage_dir=None,
    )

    bindings_by_run_id: dict[str, ReviewRuntimeBinding] = {}
    for runtime_base_root in runtime_roots:
        if not runtime_base_root.exists() or not runtime_base_root.is_dir():
            continue
        for candidate_root in runtime_base_root.iterdir():
            if not candidate_root.is_dir() or not is_summary_backed(candidate_root):
                continue
            try:
                summary = load_summary(candidate_root)
            except (OSError, json.JSONDecodeError):
                continue

            run_id = str(summary.get("run_id") or "").strip()
            if not run_id:
                continue

            binding = ReviewRuntimeBinding(
                run_id=run_id,
                review_root=candidate_root.resolve(),
                summary=summary,
                database_path=resolve_runtime_database_path(candidate_root, summary),
                storage_dir=resolve_runtime_storage_dir(candidate_root, summary),
            )
            existing = bindings_by_run_id.get(run_id)
            if existing is None or _binding_sort_key(binding.summary) > _binding_sort_key(existing.summary):
                bindings_by_run_id[run_id] = binding

    return [binding for binding in bindings_by_run_id.values() if binding_is_baseline_visible(binding)]


def _source_display(source: Any, *, checkout_root: Path | None = None) -> dict[str, Any]:
    if isinstance(source, ReviewRuntimeBinding):
        run_detail = source.summary.get("run_detail") or {}
        submission = source.summary.get("submission") or {}
        return {
            "run_id": source.run_id,
            "variant_kind": classify_runtime_binding_variant(source),
            "completed_at": (
                str(run_detail.get("completed_at") or "").strip()
                or str(submission.get("submitted_at") or "").strip()
                or str(source.summary.get("generated_at_utc") or "").strip()
                or None
            ),
            "review_root": _repo_rel(checkout_root, source.review_root) if checkout_root else str(source.review_root),
        }

    if isinstance(source, dict):
        payload: dict[str, Any] = {}
        for key in ("bundle_id", "display_label", "generated_at_utc", "decision_recommendation"):
            value = source.get(key)
            if value is not None:
                payload[key] = value
        return payload

    payload = {}
    for key in ("run_id", "bundle_id", "display_label", "completed_at", "generated_at_utc"):
        value = getattr(source, key, None)
        if value is not None:
            payload[key] = value
    return payload


def _command_spec(*args: str, copy_paste_ready: bool = True, note: str = "") -> dict[str, Any]:
    argv = [str(item) for item in args if str(item)]
    payload: dict[str, Any] = {
        "argv": argv,
        "powershell": " ".join(_powershell_arg(item) for item in argv),
        "copy_paste_ready": copy_paste_ready,
    }
    if note:
        payload["note"] = note
    return payload


def _powershell_arg(value: str) -> str:
    if value and all(char in _POWERSHELL_SAFE_CHARS for char in value):
        return value
    return "'" + value.replace("'", "''") + "'"


def _canonical_prep_sequences(*, candidate_b_run_id: str = "") -> dict[str, list[dict[str, Any]]]:
    runtime_run_value = candidate_b_run_id or "CANDIDATE_B_RUNTIME_RUN_ID"
    runtime_validation_note = (
        ""
        if candidate_b_run_id
        else "Replace CANDIDATE_B_RUNTIME_RUN_ID with the run_id from the preceding Candidate B runtime seed summary."
    )
    return {
        "bundle_source": [
            _command_spec("py", "-3.12", ".\\tools\\seed_wb_compare.py", "--visual-lane-mode", "baseline"),
            _command_spec(
                "py",
                "-3.12",
                ".\\tools\\seed_wb_compare.py",
                "--visual-lane-mode",
                "candidate_a_page_evidence_v1",
            ),
            _command_spec(".\\project6.ps1", "-Action", "compare-nrc-aps-candidate-b"),
            _command_spec("py", "-3.12", ".\\tools\\validate_wb_prep.py"),
        ],
        "runtime_source": [
            _command_spec("py", "-3.12", ".\\tools\\seed_wb_compare.py", "--visual-lane-mode", "baseline"),
            _command_spec(
                "py",
                "-3.12",
                ".\\tools\\seed_wb_compare.py",
                "--visual-lane-mode",
                "candidate_a_page_evidence_v1",
            ),
            _command_spec(
                "py",
                "-3.12",
                ".\\tools\\seed_wb_compare.py",
                "--document-processing-engine",
                _CANDIDATE_B_RUNTIME_VARIANT,
            ),
            _command_spec(
                "py",
                "-3.12",
                ".\\tools\\validate_wb_prep.py",
                "--candidate-b-source-kind",
                _CANDIDATE_B_SOURCE_KIND_RUNTIME,
                "--candidate-b-run-id",
                runtime_run_value,
                copy_paste_ready=bool(candidate_b_run_id),
                note=runtime_validation_note,
            ),
        ],
    }


def _selected_validation_command(
    *,
    source_kind: str,
    baseline_run_id: str,
    candidate_a_run_id: str,
    candidate_b_bundle_id: str = "",
    candidate_b_run_id: str = "",
    fixture_id: str = "",
) -> dict[str, Any]:
    command = ["py", "-3.12", ".\\tools\\validate_wb_prep.py"]
    if baseline_run_id:
        command.extend(["--baseline-run-id", baseline_run_id])
    if candidate_a_run_id:
        command.extend(["--candidate-a-run-id", candidate_a_run_id])
    if source_kind == _CANDIDATE_B_SOURCE_KIND_RUNTIME:
        command.extend(["--candidate-b-source-kind", _CANDIDATE_B_SOURCE_KIND_RUNTIME])
        if candidate_b_run_id:
            command.extend(["--candidate-b-run-id", candidate_b_run_id])
    elif candidate_b_bundle_id:
        command.extend(["--candidate-b-bundle-id", candidate_b_bundle_id])
    if fixture_id:
        command.extend(["--fixture-id", fixture_id])
    return _command_spec(*command)


def _operator_handoff(
    *,
    checkout_root: Path,
    source_kind: str,
    rerun_validation_command: dict[str, Any],
    candidate_b_run_id: str = "",
) -> dict[str, Any]:
    return {
        "working_directory": _checkout_root_display(checkout_root),
        "selected_source_kind": source_kind,
        "rerun_selected_validation": rerun_validation_command,
        "canonical_prep_sequences": _canonical_prep_sequences(candidate_b_run_id=candidate_b_run_id),
        "validation_boundaries": [
            "tools/validate_wb_prep.py is validate-only and must not seed or generate artifacts.",
            "Seed commands are an explicit operator prep step outside validate-only test execution.",
            "Bundle-sourced Candidate B opens Candidate B Trace; runtime-sourced Candidate B opens the existing document-trace route.",
            "Runtime-sourced Candidate B is not Candidate B Trace parity and must keep using an explicit candidate_b_run_id.",
        ],
    }


def _attempted_validation_command(args: argparse.Namespace) -> dict[str, Any]:
    command = ["py", "-3.12", ".\\tools\\validate_wb_prep.py"]
    if str(args.checkout_root or "").strip():
        command.extend(["--checkout-root", str(args.checkout_root).strip()])
    if str(args.baseline_run_id or "").strip():
        command.extend(["--baseline-run-id", str(args.baseline_run_id).strip()])
    if str(args.candidate_a_run_id or "").strip():
        command.extend(["--candidate-a-run-id", str(args.candidate_a_run_id).strip()])
    if str(args.candidate_b_source_kind or "").strip() != _CANDIDATE_B_SOURCE_KIND_BUNDLE:
        command.extend(["--candidate-b-source-kind", str(args.candidate_b_source_kind).strip()])
    if str(args.candidate_b_bundle_id or "").strip():
        command.extend(["--candidate-b-bundle-id", str(args.candidate_b_bundle_id).strip()])
    if str(args.candidate_b_run_id or "").strip():
        command.extend(["--candidate-b-run-id", str(args.candidate_b_run_id).strip()])
    if str(args.fixture_id or "").strip():
        command.extend(["--fixture-id", str(args.fixture_id).strip()])
    return _command_spec(*command)


def _failure_operator_handoff(*, checkout_root: Path, args: argparse.Namespace) -> dict[str, Any]:
    source_kind = _normalize_candidate_b_source_kind(args.candidate_b_source_kind)
    handoff = _operator_handoff(
        checkout_root=checkout_root,
        source_kind=source_kind,
        rerun_validation_command=_attempted_validation_command(args),
    )
    handoff["failure_next_steps"] = [
        "Inspect error.context for eligible same-checkout runs or bundles before choosing explicit ids.",
        "If required prep is absent or incoherent, run the matching canonical prep sequence, then rerun validation.",
        "Do not reuse donor checkout runtimes or stale query-string run ids to force a populated compare state.",
    ]
    return handoff


def _select_binding(
    *,
    label: str,
    bindings: list[ReviewRuntimeBinding],
    expected_variant: str,
    explicit_run_id: str,
    checkout_root: Path,
) -> ReviewRuntimeBinding:
    label_code = label.replace("-", "_")
    eligible: list[ReviewRuntimeBinding] = []
    for binding in bindings:
        if _binding_is_workbench_seed(binding, expected_variant=expected_variant, checkout_root=checkout_root):
            eligible.append(binding)

    if str(explicit_run_id).strip():
        requested = str(explicit_run_id).strip()
        for binding in eligible:
            if binding.run_id == requested:
                return binding
        raise PreparedStateError(
            f"{label_code}_run_unavailable",
            f"Requested {label} run is not an eligible same-checkout workbench seed: {requested}",
            context={
                "requested_run_id": requested,
                "eligible_runs": [_source_display(item, checkout_root=checkout_root) for item in eligible],
            },
        )

    if not eligible:
        raise PreparedStateError(
            f"{label_code}_run_missing",
            f"No eligible same-checkout {label} workbench seed was discovered.",
        )
    if len(eligible) > 1:
        raise PreparedStateError(
            f"{label_code}_run_ambiguous",
            f"Multiple eligible same-checkout {label} workbench seeds were discovered; pass --{label}-run-id explicitly or use a clean checkout.",
            context={"eligible_runs": [_source_display(item, checkout_root=checkout_root) for item in eligible]},
        )
    return eligible[0]


def _discover_candidate_b_bundle_sources(checkout_root: Path) -> list[dict[str, Any]]:
    bundle_sources: list[dict[str, Any]] = []
    for bundle_root in discover_candidate_b_bundle_roots(checkout_root):
        bundle_id = _canonical_bundle_id(bundle_root, checkout_root)
        try:
            bundle = _load_bundle_artifacts(bundle_id, checkout_root)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            continue
        decision_recommendation = str(bundle.compare.get("decision_recommendation") or "").strip() or None
        bundle_sources.append(
            {
                "bundle_id": bundle_id,
                "display_label": f"{bundle_root.name} | {decision_recommendation or 'unknown'}",
                "generated_at_utc": str(bundle.compare.get("generated_at_utc") or "").strip() or None,
                "decision_recommendation": decision_recommendation,
            }
        )
    bundle_sources.sort(
        key=lambda item: ((item.get("generated_at_utc") or ""), str(item.get("bundle_id") or "")),
        reverse=True,
    )
    return bundle_sources


def _select_bundle_id(
    *,
    bundle_sources: list[dict[str, Any]],
    explicit_bundle_id: str,
) -> str:
    eligible = list(bundle_sources)
    if str(explicit_bundle_id).strip():
        requested = str(explicit_bundle_id).strip()
        for item in eligible:
            if item["bundle_id"] == requested:
                return item["bundle_id"]
        raise PreparedStateError(
            "candidate_b_bundle_unavailable",
            f"Requested Candidate B bundle is not an eligible discovered bundle: {requested}",
            context={
                "requested_bundle_id": requested,
                "eligible_bundles": [_source_display(item) for item in eligible],
            },
        )

    if not eligible:
        raise PreparedStateError(
            "candidate_b_bundle_missing",
            "No eligible same-checkout Candidate B bundle was discovered.",
        )
    if len(eligible) > 1:
        raise PreparedStateError(
            "candidate_b_bundle_ambiguous",
            "Multiple eligible same-checkout Candidate B bundles were discovered; pass --candidate-b-bundle-id explicitly or use a clean checkout.",
            context={"eligible_bundles": [_source_display(item) for item in eligible]},
        )
    return eligible[0]["bundle_id"]


def _select_follow_through_fixture_id(
    *,
    shared_fixture_ids: list[str],
    explicit_fixture_id: str,
    annotated_fixture_ids: list[str],
) -> str:
    if str(explicit_fixture_id).strip():
        requested = str(explicit_fixture_id).strip()
        if requested in shared_fixture_ids:
            return requested
        raise PreparedStateError(
            "fixture_id_unavailable",
            f"Requested follow-through fixture is not shared across the prepared sources: {requested}",
            context={
                "requested_fixture_id": requested,
                "shared_fixture_ids": shared_fixture_ids,
            },
        )

    preferred_annotated_order = [
        fixture_id for fixture_id in REQUIRED_FOLLOW_THROUGH_FIXTURES if fixture_id in annotated_fixture_ids
    ]
    if preferred_annotated_order:
        return preferred_annotated_order[0]

    if annotated_fixture_ids:
        return annotated_fixture_ids[0]

    if REQUIRED_FOLLOW_THROUGH_FIXTURES[0] in shared_fixture_ids:
        return REQUIRED_FOLLOW_THROUGH_FIXTURES[0]

    return shared_fixture_ids[0]


def _validate_shared_fixtures(shared_fixture_ids: list[str]) -> None:
    missing_required = [
        fixture_id for fixture_id in REQUIRED_FOLLOW_THROUGH_FIXTURES if fixture_id not in shared_fixture_ids
    ]
    if missing_required:
        raise PreparedStateError(
            "shared_fixture_required_missing",
            "The prepared source intersection is missing one or more required follow-through fixtures.",
            context={
                "missing_fixture_ids": missing_required,
                "shared_fixture_ids": shared_fixture_ids,
            },
        )
    if len(shared_fixture_ids) < MIN_SHARED_FIXTURE_COUNT:
        raise PreparedStateError(
            "shared_fixture_count_insufficient",
            f"The prepared source intersection must contain at least {MIN_SHARED_FIXTURE_COUNT} shared fixtures.",
            context={"shared_fixture_ids": shared_fixture_ids},
        )


def validate_prepared_state(
    *,
    checkout_root: Path,
    baseline_run_id: str = "",
    candidate_a_run_id: str = "",
    candidate_b_source_kind: str = _CANDIDATE_B_SOURCE_KIND_BUNDLE,
    candidate_b_bundle_id: str = "",
    candidate_b_run_id: str = "",
    fixture_id: str = "",
) -> dict[str, Any]:
    source_kind = _normalize_candidate_b_source_kind(candidate_b_source_kind)
    bindings = _discover_runtime_bindings_for_checkout(checkout_root)

    baseline_binding = _select_binding(
        label="baseline",
        bindings=bindings,
        expected_variant="baseline",
        explicit_run_id=baseline_run_id,
        checkout_root=checkout_root,
    )
    candidate_a_binding = _select_binding(
        label="candidate-a",
        bindings=bindings,
        expected_variant="candidate_a_page_evidence_v1",
        explicit_run_id=candidate_a_run_id,
        checkout_root=checkout_root,
    )
    if source_kind == _CANDIDATE_B_SOURCE_KIND_RUNTIME:
        if not str(candidate_b_run_id or "").strip():
            eligible_candidate_b_runs = [
                _source_display(binding, checkout_root=checkout_root)
                for binding in bindings
                if _binding_is_workbench_seed(
                    binding,
                    expected_variant=_CANDIDATE_B_RUNTIME_VARIANT,
                    checkout_root=checkout_root,
                )
            ]
            raise PreparedStateError(
                "candidate_b_run_id_missing",
                "Pass --candidate-b-run-id explicitly for runtime Candidate B validation.",
                context={"eligible_runs": eligible_candidate_b_runs},
            )
        manifest_by_basename = _manifest_entries_by_basename(checkout_root)
        baseline_targets = _load_runtime_targets(baseline_binding, manifest_by_basename)
        candidate_a_targets = _load_runtime_targets(candidate_a_binding, manifest_by_basename)
        candidate_b_binding = _select_binding(
            label="candidate-b",
            bindings=bindings,
            expected_variant=_CANDIDATE_B_RUNTIME_VARIANT,
            explicit_run_id=candidate_b_run_id,
            checkout_root=checkout_root,
        )
        candidate_b_targets = _load_runtime_targets(candidate_b_binding, manifest_by_basename)
        shared_fixture_ids = sorted(set(baseline_targets) & set(candidate_a_targets) & set(candidate_b_targets))
        _validate_shared_fixtures(shared_fixture_ids)
        follow_through_fixture_id = _select_follow_through_fixture_id(
            shared_fixture_ids=shared_fixture_ids,
            explicit_fixture_id=fixture_id,
            annotated_fixture_ids=[],
        )
        compare_params = urlencode(
            {
                "baseline_run_id": baseline_binding.run_id,
                "candidate_a_run_id": candidate_a_binding.run_id,
                "candidate_b_source_kind": _CANDIDATE_B_SOURCE_KIND_RUNTIME,
                "candidate_b_run_id": candidate_b_binding.run_id,
                "fixture_id": follow_through_fixture_id,
            }
        )
        rerun_validation_command = _selected_validation_command(
            source_kind=_CANDIDATE_B_SOURCE_KIND_RUNTIME,
            baseline_run_id=baseline_binding.run_id,
            candidate_a_run_id=candidate_a_binding.run_id,
            candidate_b_run_id=candidate_b_binding.run_id,
            fixture_id=follow_through_fixture_id,
        )
        return {
            "schema_id": "aps.workbench_prep_validation.v1",
            "passed": True,
            "checkout_root": _checkout_root_display(checkout_root),
            "selection": {
                "candidate_b_source_kind": _CANDIDATE_B_SOURCE_KIND_RUNTIME,
                "baseline_run_id": baseline_binding.run_id,
                "candidate_a_run_id": candidate_a_binding.run_id,
                "candidate_b_run_id": candidate_b_binding.run_id,
                "follow_through_fixture_id": follow_through_fixture_id,
            },
            "review_roots": {
                "baseline_review_root": _repo_rel(checkout_root, baseline_binding.review_root),
                "candidate_a_review_root": _repo_rel(checkout_root, candidate_a_binding.review_root),
                "candidate_b_review_root": _repo_rel(checkout_root, candidate_b_binding.review_root),
            },
            "shared_fixture_ids": shared_fixture_ids,
            "required_follow_through_fixture_ids": list(REQUIRED_FOLLOW_THROUGH_FIXTURES),
            "required_follow_through_fixture_ids_present": [
                fixture_value for fixture_value in REQUIRED_FOLLOW_THROUGH_FIXTURES if fixture_value in shared_fixture_ids
            ],
            "recommended_urls": {
                "workbench_compare": f"/review/nrc-aps/workbench-compare?{compare_params}",
                "baseline_trace": _trace_link(
                    baseline_binding.run_id,
                    baseline_targets[follow_through_fixture_id].target_id,
                ),
                "candidate_a_trace": _trace_link(
                    candidate_a_binding.run_id,
                    candidate_a_targets[follow_through_fixture_id].target_id,
                ),
                "candidate_b_runtime_trace": _trace_link(
                    candidate_b_binding.run_id,
                    candidate_b_targets[follow_through_fixture_id].target_id,
                ),
            },
            "operator_handoff": _operator_handoff(
                checkout_root=checkout_root,
                source_kind=_CANDIDATE_B_SOURCE_KIND_RUNTIME,
                rerun_validation_command=rerun_validation_command,
                candidate_b_run_id=candidate_b_binding.run_id,
            ),
            "sources_snapshot": {
                "baseline_runs": [
                    _source_display(binding, checkout_root=checkout_root)
                    for binding in bindings
                    if _binding_is_workbench_seed(
                        binding,
                        expected_variant="baseline",
                        checkout_root=checkout_root,
                    )
                ],
                "candidate_a_runs": [
                    _source_display(binding, checkout_root=checkout_root)
                    for binding in bindings
                    if _binding_is_workbench_seed(
                        binding,
                        expected_variant="candidate_a_page_evidence_v1",
                        checkout_root=checkout_root,
                    )
                ],
                "candidate_b_runtime_runs": [
                    _source_display(binding, checkout_root=checkout_root)
                    for binding in bindings
                    if _binding_is_workbench_seed(
                        binding,
                        expected_variant=_CANDIDATE_B_RUNTIME_VARIANT,
                        checkout_root=checkout_root,
                    )
                ],
            },
        }

    candidate_b_bundle_sources = _discover_candidate_b_bundle_sources(checkout_root)
    selected_bundle_id = _select_bundle_id(
        bundle_sources=candidate_b_bundle_sources,
        explicit_bundle_id=candidate_b_bundle_id,
    )

    manifest_by_basename = _manifest_entries_by_basename(checkout_root)
    baseline_targets = _load_runtime_targets(baseline_binding, manifest_by_basename)
    candidate_a_targets = _load_runtime_targets(candidate_a_binding, manifest_by_basename)
    bundle = _load_bundle_artifacts(selected_bundle_id, checkout_root)
    bundle_documents = _bundle_documents_by_fixture(bundle.compare)
    shared_fixture_ids = sorted(set(baseline_targets) & set(candidate_a_targets) & set(bundle_documents))
    _validate_shared_fixtures(shared_fixture_ids)

    annotated_fixture_ids: list[str] = []
    for current_fixture_id in shared_fixture_ids:
        trace_manifest = compose_candidate_b_trace_manifest(
            candidate_b_bundle_id=selected_bundle_id,
            fixture_id=current_fixture_id,
            checkout_root=checkout_root,
        )
        if trace_manifest.default_tab == "annotated_pdf" and trace_manifest.artifacts.annotated_pdf:
            annotated_fixture_ids.append(current_fixture_id)
    if not annotated_fixture_ids:
        raise PreparedStateError(
            "candidate_b_annotated_pdf_missing",
            "No shared fixture exposes an annotated PDF through Candidate B Trace.",
            context={"shared_fixture_ids": shared_fixture_ids},
        )

    follow_through_fixture_id = _select_follow_through_fixture_id(
        shared_fixture_ids=shared_fixture_ids,
        explicit_fixture_id=fixture_id,
        annotated_fixture_ids=annotated_fixture_ids,
    )
    trace_manifest = compose_candidate_b_trace_manifest(
        candidate_b_bundle_id=selected_bundle_id,
        fixture_id=follow_through_fixture_id,
        checkout_root=checkout_root,
    )
    if trace_manifest.default_tab != "annotated_pdf":
        raise PreparedStateError(
            "candidate_b_default_tab_incoherent",
            "The selected follow-through fixture does not default to annotated_pdf in Candidate B Trace.",
            context={
                "fixture_id": follow_through_fixture_id,
                "default_tab": trace_manifest.default_tab,
            },
        )

    compare_params = urlencode(
        {
            "baseline_run_id": baseline_binding.run_id,
            "candidate_a_run_id": candidate_a_binding.run_id,
            "candidate_b_bundle_id": selected_bundle_id,
            "fixture_id": follow_through_fixture_id,
        }
    )
    baseline_trace = _trace_link(
        baseline_binding.run_id,
        baseline_targets[follow_through_fixture_id].target_id,
    )
    candidate_a_trace = _trace_link(
        candidate_a_binding.run_id,
        candidate_a_targets[follow_through_fixture_id].target_id,
    )
    candidate_b_trace = _candidate_b_trace_link(selected_bundle_id, follow_through_fixture_id)
    rerun_validation_command = _selected_validation_command(
        source_kind=_CANDIDATE_B_SOURCE_KIND_BUNDLE,
        baseline_run_id=baseline_binding.run_id,
        candidate_a_run_id=candidate_a_binding.run_id,
        candidate_b_bundle_id=selected_bundle_id,
        fixture_id=follow_through_fixture_id,
    )
    return {
        "schema_id": "aps.workbench_prep_validation.v1",
        "passed": True,
        "checkout_root": _checkout_root_display(checkout_root),
        "selection": {
            "candidate_b_source_kind": _CANDIDATE_B_SOURCE_KIND_BUNDLE,
            "baseline_run_id": baseline_binding.run_id,
            "candidate_a_run_id": candidate_a_binding.run_id,
            "candidate_b_bundle_id": selected_bundle_id,
            "follow_through_fixture_id": follow_through_fixture_id,
        },
        "review_roots": {
            "baseline_review_root": _repo_rel(checkout_root, baseline_binding.review_root),
            "candidate_a_review_root": _repo_rel(checkout_root, candidate_a_binding.review_root),
        },
        "shared_fixture_ids": shared_fixture_ids,
        "annotated_fixture_ids": annotated_fixture_ids,
        "required_follow_through_fixture_ids": list(REQUIRED_FOLLOW_THROUGH_FIXTURES),
        "required_follow_through_fixture_ids_present": [
            fixture_value for fixture_value in REQUIRED_FOLLOW_THROUGH_FIXTURES if fixture_value in shared_fixture_ids
        ],
        "recommended_urls": {
            "workbench_compare": f"/review/nrc-aps/workbench-compare?{compare_params}",
            "baseline_trace": baseline_trace,
            "candidate_a_trace": candidate_a_trace,
            "candidate_b_trace": candidate_b_trace,
        },
        "candidate_b_trace": {
            "default_tab": trace_manifest.default_tab,
            "available_tabs": [tab.tab_id for tab in trace_manifest.tabs if tab.available],
            "annotated_pdf_endpoint": trace_manifest.artifacts.annotated_pdf,
            "raw_json_endpoint": trace_manifest.artifacts.raw_json,
            "raw_markdown_endpoint": trace_manifest.artifacts.raw_markdown,
        },
        "operator_handoff": _operator_handoff(
            checkout_root=checkout_root,
            source_kind=_CANDIDATE_B_SOURCE_KIND_BUNDLE,
            rerun_validation_command=rerun_validation_command,
        ),
        "sources_snapshot": {
            "baseline_runs": [
                _source_display(binding, checkout_root=checkout_root)
                for binding in bindings
                if _binding_is_workbench_seed(
                    binding,
                    expected_variant="baseline",
                    checkout_root=checkout_root,
                )
            ],
            "candidate_a_runs": [
                _source_display(binding, checkout_root=checkout_root)
                for binding in bindings
                if _binding_is_workbench_seed(
                    binding,
                    expected_variant="candidate_a_page_evidence_v1",
                    checkout_root=checkout_root,
                )
            ],
            "candidate_b_bundles": [_source_display(item) for item in candidate_b_bundle_sources],
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checkout_root = _checkout_root(args.checkout_root)
    try:
        payload = validate_prepared_state(
            checkout_root=checkout_root,
            baseline_run_id=args.baseline_run_id,
            candidate_a_run_id=args.candidate_a_run_id,
            candidate_b_source_kind=args.candidate_b_source_kind,
            candidate_b_bundle_id=args.candidate_b_bundle_id,
            candidate_b_run_id=args.candidate_b_run_id,
            fixture_id=args.fixture_id,
        )
    except PreparedStateError as exc:
        failure_payload = {
            "schema_id": "aps.workbench_prep_validation.v1",
            "passed": False,
            "checkout_root": _checkout_root_display(checkout_root),
            "error": {
                "code": exc.code,
                "detail": exc.detail,
                "context": exc.context,
            },
            "operator_handoff": _failure_operator_handoff(checkout_root=checkout_root, args=args),
        }
        print(json.dumps(failure_payload, indent=2, sort_keys=False), file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
