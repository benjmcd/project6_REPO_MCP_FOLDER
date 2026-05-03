from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import inspect_harness_logs


def test_inspect_logs_filters_files_without_matching_lines(tmp_path: Path) -> None:
    (tmp_path / ".project6_api_stdout.log").write_text("alpha\n", encoding="utf-8")
    (tmp_path / ".project6_api_stderr.log").write_text("beta\nneedle\n", encoding="utf-8")

    summaries = inspect_harness_logs.inspect_logs(tmp_path, [], tail=10, contains="needle")

    assert [summary.path for summary in summaries] == [".project6_api_stderr.log"]
    assert summaries[0].lines == ["needle"]


def test_inspect_logs_accepts_extra_repo_relative_path(tmp_path: Path) -> None:
    log_path = tmp_path / "custom.log"
    log_path.write_text("one\ntwo\nthree\n", encoding="utf-8")

    summaries = inspect_harness_logs.inspect_logs(tmp_path, ["custom.log"], tail=2, contains=None)

    assert [summary.path for summary in summaries] == ["custom.log"]
    assert summaries[0].lines == ["two", "three"]
