from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REVIEW_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-default-on-admission-review.py"


def _review_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_default_on_admission_review", REVIEW_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _gate_report(tmp_path: Path, *, admitted: bool) -> Path:
    path = tmp_path / "gate.json"
    path.write_text(
        json.dumps(
            {
                "decision": "default_on_admitted_candidate" if admitted else "default_on_not_admitted",
                "ready_for_default_on": admitted,
                "summary": {
                    "real_filing_count": 12,
                    "companyfacts_value_match_rate": 0.9923,
                    "value_bridge_fact_count": 23102,
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_sec_xbrl_default_on_admission_review_passes_when_default_stays_off(tmp_path: Path) -> None:
    module = _review_module()

    report = module.build_report(gate_report_path=_gate_report(tmp_path, admitted=True), source_root=ROOT)

    assert report["decision"] == "admission_review_passed"
    assert report["ready_for_default_on_runtime_slice"] is True
    assert report["blocking_reasons"] == []
    assert report["non_goals_preserved"]["runtime_default_enabled_by_follow_on_runtime_slice"] is False


def test_sec_xbrl_default_on_admission_review_blocks_when_gate_is_not_admitted(tmp_path: Path) -> None:
    module = _review_module()

    report = module.build_report(gate_report_path=_gate_report(tmp_path, admitted=False), source_root=ROOT)

    assert report["decision"] == "admission_review_blocked"
    assert report["ready_for_default_on_runtime_slice"] is False
    assert report["blocking_reasons"][0]["reason"] == "admission_review_gate_not_admitted"
