from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-operator-runbook-matrix-selection.py"


def _load_runbook():
    spec = importlib.util.spec_from_file_location("sec_xbrl_operator_runbook_matrix_selection", RUNBOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_operator_runbook_matrix_selection_ready(tmp_path: Path) -> None:
    module = _load_runbook()
    paths = _write_inputs(tmp_path)

    report = module.build_report(
        default_posture_report_path=paths["default_posture"],
        broader_reliability_report_path=paths["broader"],
        real_product_runner_report_path=paths["real_product"],
        value_reveal_live_proof_report_path=paths["live_proof"],
    )

    assert report["decision"] == "operator_runbook_and_stratified_matrix_selection_ready"
    assert report["blocking_reasons"] == []
    assert report["operator_policy"]["posture"] == "explicit_operator_only_default_off"
    assert report["operator_policy"]["runtime_default_change_allowed"] is False
    assert report["operator_policy"]["raw_issuer_examples_committed"] is False
    assert report["next_slice"] == "sec_edgar_stratified_real_filing_validation_matrix_v1"
    assert {item["stratum"] for item in report["selected_stratified_matrix"]} >= {
        "large_domestic_us_gaap",
        "foreign_private_ifrs_20f",
        "canadian_40f",
        "amendment_restatement",
        "no_inline_or_zero_fact_diagnostic",
    }


def test_sec_xbrl_operator_runbook_matrix_selection_accepts_superseded_default_on_runtime_posture(
    tmp_path: Path,
) -> None:
    module = _load_runbook()
    paths = _write_inputs(tmp_path, default_posture=_default_posture_report(superseded=True))

    report = module.build_report(
        default_posture_report_path=paths["default_posture"],
        broader_reliability_report_path=paths["broader"],
        real_product_runner_report_path=paths["real_product"],
        value_reveal_live_proof_report_path=paths["live_proof"],
    )

    assert report["decision"] == "operator_runbook_and_stratified_matrix_selection_ready"
    assert report["blocking_reasons"] == []
    assert report["criteria"][0]["evidence"]["superseded_by_default_on_runtime"] is True
    assert report["operator_policy"]["runtime_default_change_allowed"] is False
    assert report["non_goals_preserved"]["runtime_default_changed"] is False


def test_sec_xbrl_operator_runbook_blocks_without_default_posture(tmp_path: Path) -> None:
    module = _load_runbook()
    paths = _write_inputs(tmp_path)
    default_posture = json.loads(paths["default_posture"].read_text(encoding="utf-8"))
    default_posture["decision"] = "default_posture_decision_blocked"
    paths["default_posture"].write_text(json.dumps(default_posture), encoding="utf-8")

    report = module.build_report(
        default_posture_report_path=paths["default_posture"],
        broader_reliability_report_path=paths["broader"],
        real_product_runner_report_path=paths["real_product"],
        value_reveal_live_proof_report_path=paths["live_proof"],
    )

    assert report["decision"] == "operator_runbook_and_stratified_matrix_selection_blocked"
    assert any(
        item["reason"] == "operator_runbook_default_posture_not_selected"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_operator_runbook_blocks_without_live_value_reveal_proof(tmp_path: Path) -> None:
    module = _load_runbook()
    paths = _write_inputs(tmp_path)
    live_proof = json.loads(paths["live_proof"].read_text(encoding="utf-8"))
    live_proof["attempts"] = []
    paths["live_proof"].write_text(json.dumps(live_proof), encoding="utf-8")

    report = module.build_report(
        default_posture_report_path=paths["default_posture"],
        broader_reliability_report_path=paths["broader"],
        real_product_runner_report_path=paths["real_product"],
        value_reveal_live_proof_report_path=paths["live_proof"],
    )

    assert report["decision"] == "operator_runbook_and_stratified_matrix_selection_blocked"
    assert any(
        item["reason"] == "operator_runbook_current_evidence_not_ready"
        for item in report["blocking_reasons"]
    )


def _write_inputs(tmp_path: Path, *, default_posture: dict | None = None) -> dict[str, Path]:
    return {
        "default_posture": _write_json(
            tmp_path / "default-posture.json",
            default_posture or _default_posture_report(),
        ),
        "broader": _write_json(tmp_path / "broader.json", _broader_report()),
        "real_product": _write_json(tmp_path / "real-product.json", _real_product_report()),
        "live_proof": _write_json(tmp_path / "live-proof.json", _live_proof_report()),
    }


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _default_posture_report(*, superseded: bool = False) -> dict:
    return {
        "decision": (
            "explicit_operator_only_default_off_superseded_by_default_on_runtime"
            if superseded
            else "explicit_operator_only_default_off_selected"
        ),
        "selected_posture": {
            "posture": "explicit_operator_only_default_off",
            "arelle_fact_authority_cutover_default_enabled": False,
            "arelle_fact_authority_cutover_default_on_supersedes_selected_posture": superseded,
            "arelle_value_reveal_default_enabled": False,
            "sec_live_network_default_enabled": False,
        },
    }


def _broader_report() -> dict:
    return {"decision": "broader_corpus_reliability_admitted"}


def _real_product_report() -> dict:
    return {
        "decision": "real_corpus_default_on_validated",
        "gate_verdict": "PASS",
        "summary": {
            "supported_record_count": 30,
        },
    }


def _live_proof_report() -> dict:
    return {
        "decision": "value_reveal_live_authority_and_operator_exercise_proven_for_two_bounded_filings",
        "attempts": [{"attempt_label": "first"}, {"attempt_label": "second"}],
    }
