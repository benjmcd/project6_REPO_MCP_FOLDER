from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECK_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-value-reveal-operator-exercise.py"


def _operator_exercise_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_value_reveal_operator_exercise", CHECK_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_value_reveal_operator_exercise_is_ready_without_running_exercise() -> None:
    module = _operator_exercise_module()

    report = module.build_report(source_root=ROOT)

    assert report["decision"] == "value_reveal_operator_exercise_ready"
    assert report["ready_for_operator_exercise"] is True
    assert report["operator_exercise_performed"] is False
    assert report["blocking_reasons"] == []
    assert report["next_slice"] == "sec_edgar_arelle_value_reveal_operator_exercise_v1"
    assert report["non_goals_preserved"]["fact_authority_cutover_default_enabled"] is True
    assert report["non_goals_preserved"]["value_reveal_default_enabled"] is False
    assert report["non_goals_preserved"]["controlled_value_reveal_submit_default_enabled"] is False
    assert report["non_goals_preserved"]["raw_values_committed"] is False
    assert report["non_goals_preserved"]["cross_company_comparability_claimed"] is False
