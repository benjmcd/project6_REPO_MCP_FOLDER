from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = (
    ROOT
    / "diagnostics"
    / "assessment"
    / "sec-xbrl-value-reveal-authority-provisioning-preflight.py"
)


def _preflight_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_value_reveal_authority_provisioning_preflight", PREFLIGHT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_report(tmp_path: Path) -> Path:
    path = tmp_path / "run-report.json"
    path.write_text(
        json.dumps(
            {
                "decision": "value_reveal_operator_exercise_blocked_missing_authority",
                "ready_to_run_operator_exercise": False,
                "redacted_inventory": {"sidecar_receipt_count": 0, "bridge_receipt_count": 0},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_sec_xbrl_value_reveal_authority_provisioning_preflight_requires_grant_or_environment(
    tmp_path: Path,
) -> None:
    module = _preflight_module()

    report = module.build_report(source_root=ROOT, run_report_path=_run_report(tmp_path), env={})

    assert report["decision"] == "authority_provisioning_preflight_requires_explicit_grant_or_environment"
    assert report["operator_exercise_run_report_summary"]["decision"] == (
        "value_reveal_operator_exercise_blocked_missing_authority"
    )
    assert report["non_goals_preserved"]["sec_network_fetch_performed"] is False
    assert report["non_goals_preserved"]["arelle_subprocess_invoked"] is False
    assert report["non_goals_preserved"]["raw_values_committed"] is False
    assert report["next_slice"] == "sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_v1"
