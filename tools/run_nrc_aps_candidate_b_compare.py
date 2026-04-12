from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
TESTS_DIR = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from support_nrc_aps_candidate_b_opendataloader import (  # noqa: E402
    baseline_summary_map,
    collect_candidate_b_findings,
    default_raw_root,
    load_baseline_summary,
    prepare_workbench_context,
    repo_rel,
    run_baseline_proof,
    run_shell_command,
    build_run_id,
    write_candidate_b_reports,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the repo-native Candidate B compare surface.")
    parser.add_argument("--run-root", default="")
    parser.add_argument("--plan-only", action="store_true")
    return parser


def build_run_plan(*, run_root: Path, run_id: str) -> dict[str, Path | str]:
    return {
        "run_id": run_id,
        "run_root": run_root.resolve(),
        "baseline_before_dir": (run_root / "baseline-before").resolve(),
        "baseline_before_runtime_root": (run_root / "baseline-before" / "runtime").resolve(),
        "baseline_before_proof_report": (run_root / "baseline-before" / "nrc_aps_document_processing_proof_report.json").resolve(),
        "baseline_before_artifact_report": (run_root / "baseline-before" / "nrc_aps_artifact_ingestion_validation_report.json").resolve(),
        "baseline_before_content_index_report": (run_root / "baseline-before" / "nrc_aps_content_index_validation_report.json").resolve(),
        "baseline_after_dir": (run_root / "baseline-after").resolve(),
        "baseline_after_runtime_root": (run_root / "baseline-after" / "runtime").resolve(),
        "baseline_after_proof_report": (run_root / "baseline-after" / "nrc_aps_document_processing_proof_report.json").resolve(),
        "baseline_after_artifact_report": (run_root / "baseline-after" / "nrc_aps_artifact_ingestion_validation_report.json").resolve(),
        "baseline_after_content_index_report": (run_root / "baseline-after" / "nrc_aps_content_index_validation_report.json").resolve(),
        "baseline_summary_path": (run_root / "baseline-summary.json").resolve(),
        "proof_report_path": (run_root / "proof.json").resolve(),
        "compare_report_path": (run_root / "compare.json").resolve(),
        "retention_manifest_path": (run_root / "retain.json").resolve(),
        "raw_root": (run_root / "raw").resolve(),
    }


def resolve_run_root(raw_value: str, *, run_id: str) -> Path:
    if str(raw_value).strip():
        return Path(raw_value).resolve()
    return (ROOT / "tests" / "reports" / f"cb-compare-{run_id}").resolve()


def ensure_compare_tools_exist() -> None:
    required_paths = [
        ROOT / "tools" / "run_nrc_aps_candidate_b_baseline.py",
        ROOT / "tests" / "support_nrc_aps_candidate_b_opendataloader.py",
        ROOT / "tools" / "run_nrc_aps_document_processing_proof.py",
    ]
    for path in required_paths:
        if not path.exists():
            raise RuntimeError(f"missing_compare_surface_tool:{path}")


def plan_payload(plan: dict[str, Path | str]) -> dict[str, Any]:
    return {
        "run_id": str(plan["run_id"]),
        "run_root": str(plan["run_root"]),
        "baseline_before_runtime_root": str(plan["baseline_before_runtime_root"]),
        "baseline_after_runtime_root": str(plan["baseline_after_runtime_root"]),
        "baseline_summary_path": str(plan["baseline_summary_path"]),
        "proof_report_path": str(plan["proof_report_path"]),
        "compare_report_path": str(plan["compare_report_path"]),
        "retention_manifest_path": str(plan["retention_manifest_path"]),
        "raw_root": str(plan["raw_root"]),
        "action_name": "compare-nrc-aps-candidate-b",
        "plan_only": True,
    }


def run_baseline_summary_tool(plan: dict[str, Path | str]) -> None:
    command = [
        sys.executable,
        "tools/run_nrc_aps_candidate_b_baseline.py",
        "--runtime-root",
        str(plan["baseline_before_runtime_root"]),
        "--proof-report",
        str(plan["baseline_before_proof_report"]),
        "--out",
        str(plan["baseline_summary_path"]),
    ]
    result = run_shell_command(command, cwd=ROOT, env=os.environ.copy())
    if not result["passed"]:
        detail = str(result.get("stderr") or "").strip() or str(result.get("stdout") or "").strip()
        raise RuntimeError(detail or "baseline_summary_generation_failed")
    load_baseline_summary(Path(plan["baseline_summary_path"]))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        ensure_compare_tools_exist()
        workbench_context = prepare_workbench_context()
        run_id = build_run_id()
        run_root = resolve_run_root(args.run_root, run_id=run_id)
        plan = build_run_plan(run_root=run_root, run_id=run_id)

        if args.plan_only:
            print(json.dumps(plan_payload(plan), indent=2, sort_keys=False))
            return 0

        started = time.perf_counter()
        Path(plan["run_root"]).mkdir(parents=True, exist_ok=True)
        Path(plan["raw_root"]).mkdir(parents=True, exist_ok=True)
        baseline_before_command, baseline_before_report = run_baseline_proof(
            label="baseline-before",
            run_root=Path(plan["run_root"]),
        )
        run_baseline_summary_tool(plan)
        baseline_summary = load_baseline_summary(Path(plan["baseline_summary_path"]))
        baseline_by_fixture = baseline_summary_map(baseline_summary)
        analysis = collect_candidate_b_findings(
            fixture_entries=workbench_context["fixture_entries"],
            label_entry_by_fixture=workbench_context["label_entry_by_fixture"],
            baseline_by_fixture=baseline_by_fixture,
            raw_root=Path(plan["raw_root"]),
        )
        baseline_after_command, baseline_after_report = run_baseline_proof(
            label="baseline-after",
            run_root=Path(plan["run_root"]),
        )
        write_candidate_b_reports(
            run_id=str(plan["run_id"]),
            proof_report_path=Path(plan["proof_report_path"]),
            compare_report_path=Path(plan["compare_report_path"]),
            retention_manifest_path=Path(plan["retention_manifest_path"]),
            raw_root=Path(plan["raw_root"]),
            workbench_context=workbench_context,
            analysis=analysis,
            baseline_before_command=baseline_before_command,
            baseline_before_report=baseline_before_report,
            baseline_after_command=baseline_after_command,
            baseline_after_report=baseline_after_report,
            baseline_source_ref=repo_rel(Path(plan["baseline_summary_path"])),
            baseline_source_kind="baseline_summary",
            execution_seconds=time.perf_counter() - started,
        )
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
