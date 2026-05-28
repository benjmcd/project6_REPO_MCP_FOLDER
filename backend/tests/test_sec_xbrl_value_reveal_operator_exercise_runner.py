from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-value-reveal-operator-exercise-runner.py"


def _runner_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_value_reveal_operator_exercise_runner", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_value_reveal_operator_exercise_runner_blocks_without_authority(tmp_path: Path) -> None:
    module = _runner_module()

    report = module.build_report(source_root=ROOT, storage_dir=tmp_path)

    assert report["decision"] == "value_reveal_operator_exercise_blocked_missing_authority"
    assert report["operator_exercise_performed"] is False
    assert report["ready_to_run_operator_exercise"] is False
    assert report["next_slice"] == "sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1"
    assert [item["blocked_reason"] for item in report["blocking_reasons"]] == [
        "value_reveal_operator_exercise_ready_sidecar_authority_missing",
        "value_reveal_operator_exercise_bridge_dataset_authority_missing",
    ]
    assert report["redacted_inventory"]["storage_exists"] is True
    assert report["redacted_inventory"]["storage_file_count"] == 0
    assert report["non_goals_preserved"]["raw_values_returned"] is False
    assert report["non_goals_preserved"]["arelle_subprocess_invoked"] is False
