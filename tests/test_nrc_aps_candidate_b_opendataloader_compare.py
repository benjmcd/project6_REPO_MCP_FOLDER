from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


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
    approved_output_prefixes,
    compare_surface_auxiliary_inventory,
    load_baseline_source,
    outputs_outside_allowed_paths,
    repo_rel,
    run_cli,
)
from tools import run_nrc_aps_candidate_b_baseline as baseline_tool  # noqa: E402
from tools import run_nrc_aps_candidate_b_compare as compare_tool  # noqa: E402


def test_load_baseline_source_requires_exactly_one_source(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="baseline_source_contract_violation"):
        load_baseline_source(baseline_summary_path=None, first_run_compare_path=None)

    baseline_summary_path = tmp_path / "baseline-summary.json"
    baseline_summary_path.write_text(
        json.dumps({"schema_id": "aps.candidate_b_baseline_summary.v1", "documents": []}),
        encoding="utf-8",
    )
    first_run_compare_path = tmp_path / "compare.json"
    first_run_compare_path.write_text(json.dumps({"documents": []}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="baseline_source_contract_violation"):
        load_baseline_source(
            baseline_summary_path=baseline_summary_path,
            first_run_compare_path=first_run_compare_path,
        )


def test_load_and_validate_proof_report_fails_closed_on_runtime_mismatch(tmp_path: Path) -> None:
    proof_report_path = tmp_path / "proof.json"
    proof_report_path.write_text(
        json.dumps(
            {
                "schema_id": "aps.document_processing_proof.v1",
                "passed": True,
                "ocr_mode": "required",
                "runtime_root": str((tmp_path / "other-runtime").resolve()),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="proof_runtime_root_mismatch"):
        baseline_tool.load_and_validate_proof_report(
            runtime_root=tmp_path / "runtime",
            proof_report_path=proof_report_path,
        )


def test_build_baseline_summary_payload_emits_frozen_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_root = tmp_path / "runtime"
    proof_report_path = tmp_path / "proof.json"
    proof_report_path.write_text(
        json.dumps(
            {
                "schema_id": "aps.document_processing_proof.v1",
                "passed": True,
                "ocr_mode": "required",
                "runtime_root": str(runtime_root.resolve()),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        baseline_tool,
        "build_baseline_documents",
        lambda **_kwargs: [
            {
                "fixture_id": "layout",
                "document_ref": "tests/fixtures/nrc_aps_docs/v1/layout.pdf",
                "document_sha256": "abc",
                "baseline": {
                    "page_count": 2,
                    "normalized_char_count": 123,
                    "document_class": "layout_complex_pdf",
                    "degradation_codes": [],
                },
            }
        ],
    )

    payload = baseline_tool.build_baseline_summary_payload(
        runtime_root=runtime_root,
        proof_report_path=proof_report_path,
    )

    assert payload["schema_id"] == "aps.candidate_b_baseline_summary.v1"
    assert payload["proof_report_ref"].endswith("proof.json")
    assert payload["runtime_root"] == str(runtime_root.resolve())
    assert payload["documents"][0]["baseline"]["page_count"] == 2
    assert payload["documents"][0]["baseline"]["document_class"] == "layout_complex_pdf"


def test_compare_runner_plan_only_stays_validate_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = tmp_path / "cb-run"
    monkeypatch.setattr(compare_tool, "ensure_compare_tools_exist", lambda: None)
    monkeypatch.setattr(compare_tool, "prepare_workbench_context", lambda: {"status": "ok"})
    monkeypatch.setattr(compare_tool, "build_run_id", lambda: "cb-fixed")

    result = compare_tool.main(["--run-root", str(run_root), "--plan-only"])

    assert result == 0
    assert not run_root.exists()


def test_compare_runner_plan_only_returns_clean_error_for_missing_prereq(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_root = tmp_path / "cb-run"
    monkeypatch.setattr(compare_tool, "ensure_compare_tools_exist", lambda: None)
    monkeypatch.setattr(compare_tool, "prepare_workbench_context", lambda: (_ for _ in ()).throw(RuntimeError("odl_package_not_installed")))

    result = compare_tool.main(["--run-root", str(run_root), "--plan-only"])

    captured = capsys.readouterr()
    assert result == 1
    assert "odl_package_not_installed" in captured.err
    assert not run_root.exists()


def test_compare_runner_build_plan_uses_frozen_paths(tmp_path: Path) -> None:
    run_root = tmp_path / "cb-run"
    plan = compare_tool.build_run_plan(run_root=run_root, run_id="cb-fixed")

    assert Path(plan["baseline_summary_path"]).name == "baseline-summary.json"
    assert Path(plan["proof_report_path"]).name == "proof.json"
    assert Path(plan["compare_report_path"]).name == "compare.json"
    assert Path(plan["retention_manifest_path"]).name == "retain.json"
    assert Path(plan["raw_root"]).name == "raw"


def test_compare_surface_output_boundary_covers_baseline_artifacts(tmp_path: Path) -> None:
    run_root = tmp_path / "cb-run"
    plan = compare_tool.build_run_plan(run_root=run_root, run_id="cb-fixed")
    baseline_before_dir = Path(plan["baseline_before_dir"])
    baseline_after_dir = Path(plan["baseline_after_dir"])
    baseline_before_runtime_root = Path(plan["baseline_before_runtime_root"])
    baseline_after_runtime_root = Path(plan["baseline_after_runtime_root"])
    baseline_before_runtime_root.mkdir(parents=True, exist_ok=True)
    baseline_after_runtime_root.mkdir(parents=True, exist_ok=True)
    baseline_summary_path = Path(plan["baseline_summary_path"])
    baseline_summary_path.write_text(
        json.dumps({"schema_id": "aps.candidate_b_baseline_summary.v1", "documents": []}),
        encoding="utf-8",
    )
    (Path(plan["baseline_before_proof_report"])).write_text(json.dumps({"passed": True}), encoding="utf-8")
    (Path(plan["baseline_after_proof_report"])).write_text(json.dumps({"passed": True}), encoding="utf-8")
    (baseline_before_runtime_root / "runtime.db").write_text("x", encoding="utf-8")
    (baseline_after_runtime_root / "runtime.db").write_text("y", encoding="utf-8")

    approved = approved_output_prefixes(
        raw_root=Path(plan["raw_root"]),
        proof_report_path=Path(plan["proof_report_path"]),
        compare_report_path=Path(plan["compare_report_path"]),
        retention_manifest_path=Path(plan["retention_manifest_path"]),
        run_root=Path(plan["run_root"]),
    )
    baseline_inventory = compare_surface_auxiliary_inventory(
        run_root=Path(plan["run_root"]),
        raw_root=Path(plan["raw_root"]),
    )

    assert [entry["path"] for entry in baseline_inventory]
    assert outputs_outside_allowed_paths(
        [entry["path"] for entry in baseline_inventory] + [repo_rel(Path(plan["retention_manifest_path"]))],
        approved_prefixes=approved,
    ) == []
    assert repo_rel(baseline_before_dir).rstrip("/") + "/" in approved
    assert repo_rel(baseline_after_dir).rstrip("/") + "/" in approved
    assert repo_rel(baseline_summary_path) in approved


def test_baseline_tool_returns_clean_error_for_invalid_proof(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    proof_report_path = tmp_path / "proof.json"
    out_path = tmp_path / "baseline-summary.json"
    proof_report_path.write_text(
        json.dumps(
            {
                "schema_id": "aps.document_processing_proof.v1",
                "passed": False,
                "ocr_mode": "required",
                "runtime_root": str((tmp_path / "runtime").resolve()),
            }
        ),
        encoding="utf-8",
    )

    result = baseline_tool.main(
        [
            "--runtime-root",
            str(tmp_path / "runtime"),
            "--proof-report",
            str(proof_report_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "proof_report_failed" in captured.err


def test_support_cli_returns_clean_error_for_missing_baseline_source(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run_cli([])

    captured = capsys.readouterr()
    assert result == 1
    assert "baseline_source_contract_violation" in captured.err
