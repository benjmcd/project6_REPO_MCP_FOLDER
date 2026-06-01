from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-default-on-runtime-report.json")
HISTORICAL_REAL_CORPUS_RUNNER_REPORT = (
    "archive/files_to_be_trashed/2026-05-31-secxbrl/sec-xbrl-real-corpus-product-runner-report.json"
)


def main() -> int:
    report = build_report()
    output = ROOT / DEFAULT_OUTPUT
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def build_report() -> dict[str, Any]:
    sources = {
        "config": _read("backend/app/core/config.py"),
        "bridge": _read("backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py"),
        "classification": _read(
            "backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.py"
        ),
        "api_tests": _read("backend/tests/test_layer3_api.py"),
        "admission": _load_json("diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json"),
        "gate": _load_json("diagnostics/assessment/sec-xbrl-default-on-gate-report.json"),
        "real_corpus_gate": _load_json(HISTORICAL_REAL_CORPUS_RUNNER_REPORT),
    }
    default_enabled = (
        'layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n        default=True,'
        in sources["config"]
    )
    criteria = [
        _criterion(
            "runtime_default_on",
            default_enabled,
            {
                "config_file": "backend/app/core/config.py",
                "config_default_enabled": default_enabled,
                "governance_remediation_default_off": not default_enabled,
                "real_corpus_gate_decision": sources["real_corpus_gate"].get("decision"),
                "real_corpus_gate_verdict": sources["real_corpus_gate"].get("gate_verdict"),
            },
            "default_on_runtime_disabled_by_governance_remediation",
        ),
        _criterion(
            "persisted_sidecar_required_without_regex_fallback",
            "arelle_sidecar_receipt_required" in sources["bridge"]
            and "regex_fallback_performed=False" in sources["bridge"],
            {
                "bridge_file": "backend/app/services/layer3_sec_edgar_html_inline_xbrl_fact_material_bridge.py",
                "synchronous_arelle_invocation_in_bridge": False,
            },
            "default_on_runtime_missing_sidecar_fail_closed_signal",
        ),
        _criterion(
            "classification_consumes_bridge_selected_sidecar_authority",
            "read_sec_edgar_arelle_resolved_fact_authority_sidecar_receipt" in sources["classification"]
            and "fact_authority_input_mode" in sources["classification"]
            and "sidecar_fact_authority_view_for_downstream" in sources["classification"],
            {
                "classification_file": (
                    "backend/app/services/"
                    "layer3_sec_edgar_html_inline_xbrl_fact_statement_classification.py"
                )
            },
            "default_on_runtime_classification_sidecar_authority_missing",
        ),
        _criterion(
            "regex_rollback_path_preserved",
            '"layer3_sec_edgar_arelle_fact_authority_cutover_enabled", False' in sources["api_tests"]
            and "test_layer3_api_bridges_sec_edgar_html_inline_xbrl_fact_material_authority" in sources["api_tests"],
            {"rollback_setting": "LAYER3_SEC_EDGAR_ARELLE_FACT_AUTHORITY_CUTOVER_ENABLED=false"},
            "default_on_runtime_regex_rollback_not_proven",
        ),
        _criterion(
            "focused_default_on_tests_present",
            all(
                test_name in sources["api_tests"]
                for test_name in (
                    "test_layer3_deployment_profile_local_defaults_keep_arelle_cutover_off",
                    "test_layer3_api_classifies_sec_edgar_arelle_sidecar_fact_authority_when_cutover_flag_enabled",
                    "test_layer3_api_blocks_sec_edgar_html_inline_xbrl_fact_material_arelle_cutover_without_sidecar",
                    "test_layer3_api_rejects_sec_edgar_html_inline_xbrl_fact_material_arelle_cutover_lineage_mismatch",
                )
            ),
            {
                "focused_tests": [
                    "test_layer3_deployment_profile_local_defaults_keep_arelle_cutover_off",
                    "test_layer3_api_classifies_sec_edgar_arelle_sidecar_fact_authority_when_cutover_flag_enabled",
                    "test_layer3_api_blocks_sec_edgar_html_inline_xbrl_fact_material_arelle_cutover_without_sidecar",
                    "test_layer3_api_rejects_sec_edgar_html_inline_xbrl_fact_material_arelle_cutover_lineage_mismatch",
                ]
            },
            "default_on_runtime_focused_tests_missing",
        ),
        _criterion(
            "standing_non_admissions_preserved",
            "financial_statement_semantics_claimed" in sources["api_tests"]
            and "cross_company_comparability_admitted" in sources["api_tests"],
            {
                "final_financial_statement_semantics_claimed": False,
                "cross_company_comparability_admitted": False,
            },
            "default_on_runtime_non_admissions_missing",
        ),
    ]
    blockers = [item for item in criteria if item["state"] != "passed"]
    gate_summary = sources["gate"].get("summary") if isinstance(sources["gate"].get("summary"), dict) else {}
    real_corpus_summary = (
        sources["real_corpus_gate"].get("summary")
        if isinstance(sources["real_corpus_gate"].get("summary"), dict)
        else {}
    )
    return {
        "schema_id": "diagnostics.sec_xbrl_default_on_runtime.v1",
        "target": "sec_edgar_arelle_fact_authority_default_on_runtime_v1",
        "decision": (
            "default_on_runtime_enabled"
            if default_enabled and not blockers
            else "default_on_runtime_disabled_by_governance_remediation"
        ),
        "headline": (
            "Arelle resolved-fact authority is now the default bridge input, with explicit persisted sidecar "
            "requirements and a reversible regex rollback flag."
            if default_enabled and not blockers
            else "Default-on Arelle runtime is disabled by governance remediation; the Arelle bridge remains flag-gated and reversible."
        ),
        "criteria": criteria,
        "blocking_reasons": blockers,
        "inherited_real_corpus_evidence": {
            "historical_real_corpus_runner_report": HISTORICAL_REAL_CORPUS_RUNNER_REPORT,
            "historical_real_corpus_runner_archived": True,
            "historical_live_matrix_reproducible_offline_from_available_inputs": False,
            "default_on_gate_decision": sources["gate"].get("decision"),
            "admission_review_decision": sources["admission"].get("decision"),
            "real_filing_count": gate_summary.get("real_filing_count"),
            "issuer_hash_count": gate_summary.get("issuer_hash_count"),
            "forms": gate_summary.get("forms"),
            "arelle_resolved_fact_count": gate_summary.get("arelle_resolved_fact_count"),
            "bridge_fact_count": gate_summary.get("bridge_fact_count"),
            "value_bridge_fact_count": gate_summary.get("value_bridge_fact_count"),
            "companyfacts_value_match_count": gate_summary.get("companyfacts_value_match_count"),
            "companyfacts_value_compared_count": gate_summary.get("companyfacts_value_compared_count"),
            "companyfacts_value_match_rate": gate_summary.get("companyfacts_value_match_rate"),
            "broader_real_corpus_gate_decision": sources["real_corpus_gate"].get("decision"),
            "broader_real_corpus_gate_verdict": sources["real_corpus_gate"].get("gate_verdict"),
            "broader_real_filing_count": real_corpus_summary.get("real_filing_count"),
            "broader_issuer_hash_count": real_corpus_summary.get("issuer_hash_count"),
            "broader_resolved_fact_count": real_corpus_summary.get("resolved_fact_count"),
            "broader_independent_inline_fact_count": real_corpus_summary.get("independent_inline_fact_count"),
            "broader_companyfacts_value_match_count": real_corpus_summary.get("companyfacts_value_match_count"),
            "broader_companyfacts_value_compared_count": real_corpus_summary.get("companyfacts_value_compared_count"),
            "broader_companyfacts_value_match_rate": real_corpus_summary.get("companyfacts_value_match_rate"),
            "broader_failure_reasons": real_corpus_summary.get("failure_reasons"),
        },
        "source_reports": {
            "default_on_gate": "diagnostics/assessment/sec-xbrl-default-on-gate-report.json",
            "admission_review": "diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json",
            "historical_real_corpus_runner": HISTORICAL_REAL_CORPUS_RUNNER_REPORT,
        },
        "runtime_posture": {
            "default_cutover_enabled": default_enabled,
            "persisted_sidecar_required": True,
            "regex_fallback_while_default_on": False if default_enabled else None,
            "synchronous_arelle_in_bridge": False,
            "regex_rollback_env_supported": True,
            "operator_value_reveal_default_enabled": False,
        },
        "non_goals_preserved": {
            "candidate_b_sec_routing_performed": False,
            "cross_company_comparability_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "gate_b_product_package_ui_redesign_performed": False,
            "rag_vector_model_provider_auth_behavior_added": False,
        },
        "next_slice": (
            "sec_edgar_operator_surface_gated_value_reveal_v1"
            if default_enabled
            else "sec_edgar_arelle_governance_remediation_followups_v1"
        ),
    }


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _load_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _criterion(
    name: str,
    passed: bool,
    evidence: dict[str, Any],
    blocked_reason: str,
) -> dict[str, Any]:
    return {
        "criterion": name,
        "state": "passed" if passed else "blocked",
        "evidence": evidence,
        "blocked_reason": None if passed else blocked_reason,
    }


if __name__ == "__main__":
    raise SystemExit(main())
