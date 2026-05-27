from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-default-on-gate.py"


def _gate_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_default_on_gate", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _reports(tmp_path: Path, *, expanded_value_corpus: bool, include_ten_q_value_oracle: bool) -> dict[str, Path]:
    forms = {"10-K": 4, "10-Q": 1, "20-F": 1, "40-F": 1, "6-K": 2, "8-K": 3}
    return {
        "sidecar": _write_json(
            tmp_path / "sidecar.json",
            {
                "corpus_summary": {
                    "real_filing_count": 12,
                    "issuer_hash_count": 6,
                    "forms": forms,
                }
            },
        ),
        "completeness": _write_json(
            tmp_path / "completeness.json",
            {
                "summary": {
                    "real_filing_count": 12,
                    "arelle_resolved_fact_count": 18156,
                    "independent_inline_fact_count": 18156,
                    "independent_count_all_reconciled": True,
                    "concept_unresolved_from_dts_count": 0,
                    "taxonomy_package_loaded_all_ready_rows": True,
                }
            },
        ),
        "bridge": _write_json(
            tmp_path / "bridge.json",
            {
                "verdict": "trustworthy_for_gated_cutover",
                "summary": {
                    "real_filing_count": 12,
                    "inline_bridge_ready_count": 10,
                    "zero_inline_not_applicable_count": 2,
                    "blocked_count": 0,
                    "bridge_fact_count": 18156,
                    "sidecar_resolved_fact_count": 18156,
                    "bridge_matches_sidecar_all_ready_rows": True,
                    "required_typed_fields_present_all_ready_rows": True,
                },
            },
        ),
        "value_bridge": _write_json(
            tmp_path / "value-bridge.json",
            {
                "verdict": "trustworthy_for_gated_cutover",
                "summary": {
                    "real_filing_count": 12 if expanded_value_corpus else 8,
                    "sidecar_resolved_fact_count": 18156 if expanded_value_corpus else 10872,
                    "bridge_fact_count": 18156 if expanded_value_corpus else 10872,
                    "blocked_count": 0,
                    "bridge_matches_sidecar_all_ready_rows": True,
                    "effective_value_nonempty_count": 18140 if expanded_value_corpus else 10863,
                    "effective_value_empty_count": 16 if expanded_value_corpus else 9,
                },
                "per_fixture": [
                    {"form": "10-K"},
                    {"form": "10-Q"} if expanded_value_corpus else {"form": "10-K"},
                    {"form": "20-F"} if expanded_value_corpus else {"form": "8-K"},
                    {"form": "40-F"} if expanded_value_corpus else {"form": "10-K"},
                    {"form": "6-K"} if expanded_value_corpus else {"form": "8-K"},
                    {"form": "8-K"},
                ],
            },
        ),
        "value": _write_json(
            tmp_path / "value.json",
            {
                "companyfacts_effective_value_correctness": {
                    "oracle": "primary_companyfacts_us_gaap_dei_accession_scope_non_dimensional_numeric_intersection",
                    "match_count": 1500 if include_ten_q_value_oracle else 1022,
                    "compared_count": 1500 if include_ten_q_value_oracle else 1028,
                    "match_rate": 1.0 if include_ten_q_value_oracle else 0.9942,
                },
                "per_fixture": [
                    {"form": "10-K", "companyfacts_effective_value_compared_count": 900},
                    {
                        "form": "10-Q",
                        "companyfacts_effective_value_compared_count": 600 if include_ten_q_value_oracle else 0,
                    },
                ],
            },
        ),
    }


def test_sec_xbrl_default_on_gate_blocks_when_values_do_not_cover_expanded_corpus(tmp_path: Path) -> None:
    module = _gate_module()
    reports = _reports(tmp_path, expanded_value_corpus=False, include_ten_q_value_oracle=False)

    report = module.build_report(
        sidecar_report_path=reports["sidecar"],
        completeness_report_path=reports["completeness"],
        bridge_report_path=reports["bridge"],
        value_report_paths=[reports["value"]],
        value_bridge_report_path=reports["value_bridge"],
    )

    assert report["decision"] == "default_on_not_admitted"
    assert [item["state"] for item in report["criteria"][:3]] == ["passed", "passed", "passed"]
    reasons = {item["reason"] for item in report["blocking_reasons"]}
    assert reasons == {
        "default_on_gate_internal_values_not_proven_on_expanded_corpus",
        "default_on_gate_companyfacts_value_correctness_incomplete",
    }


def test_sec_xbrl_default_on_gate_admits_when_all_criteria_are_proven(tmp_path: Path) -> None:
    module = _gate_module()
    reports = _reports(tmp_path, expanded_value_corpus=True, include_ten_q_value_oracle=True)

    report = module.build_report(
        sidecar_report_path=reports["sidecar"],
        completeness_report_path=reports["completeness"],
        bridge_report_path=reports["bridge"],
        value_report_paths=[reports["value"]],
        value_bridge_report_path=reports["value_bridge"],
    )

    assert report["decision"] == "default_on_admitted_candidate"
    assert report["ready_for_default_on"] is True
    assert report["blocking_reasons"] == []
