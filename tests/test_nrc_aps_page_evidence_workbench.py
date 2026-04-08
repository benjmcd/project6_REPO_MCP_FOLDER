from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "nrc_aps_docs" / "v1"


def _run_workbench(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/run_nrc_aps_page_evidence_workbench.py", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_workbench_runner_analyzes_fixture_ids(tmp_path: Path) -> None:
    report_path = tmp_path / "page_evidence_report.json"
    completed = _run_workbench(
        "--report",
        str(report_path),
        "--fixture-id",
        "born_digital",
        "--fixture-id",
        "scanned",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["schema_id"] == "aps.page_evidence_workbench_report.v1"
    assert payload["candidate_stage"] == "pre_admission"
    assert payload["passed"] is True
    assert payload["document_count"] == 2

    by_fixture = {item["fixture_id"]: item["analysis"] for item in payload["documents"]}
    assert by_fixture["born_digital"]["pages"][0]["projected_visual_page_class"] == "text_heavy_or_empty"
    assert by_fixture["scanned"]["pages"][0]["projected_visual_page_class"] == "diagram_or_visual"


def test_workbench_runner_analyzes_explicit_pdf_path(tmp_path: Path) -> None:
    report_path = tmp_path / "single_report.json"
    pdf_path = FIXTURE_DIR / "scanned.pdf"
    completed = _run_workbench(
        "--report",
        str(report_path),
        "--input-pdf",
        str(pdf_path),
        "--text-word-threshold",
        "5",
        "--visual-coverage-threshold",
        "0.10",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["config"]["text_word_threshold"] == 5
    assert payload["config"]["visual_coverage_threshold"] == 0.1
    assert payload["documents"][0]["source_kind"] == "path"
    assert payload["documents"][0]["analysis"]["pages"][0]["image_count"] >= 1


def test_workbench_runner_fails_closed_on_unknown_fixture(tmp_path: Path) -> None:
    report_path = tmp_path / "failure_report.json"
    completed = _run_workbench(
        "--report",
        str(report_path),
        "--fixture-id",
        "does_not_exist",
    )

    assert completed.returncode == 2
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["failure_reason"] == "unknown_fixture_id:does_not_exist"
