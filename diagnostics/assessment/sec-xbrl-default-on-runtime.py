from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-default-on-runtime-report.json")
REAL_CORPUS_RUNNER_REPORT = (
    "diagnostics/assessment/sec-xbrl-real-corpus-product-runner-report.json"
)
ADMISSION_RESTATEMENT_REPORT = (
    "diagnostics/assessment/sec-xbrl-default-on-admission-restatement-report.json"
)
DEFAULT_ON_FOCUSED_TESTS = (
    "test_layer3_deployment_profile_local_defaults_enable_arelle_cutover_without_value_reveal",
    "test_layer3_api_bridges_sec_edgar_html_inline_xbrl_fact_material_from_arelle_sidecar_by_default",
    "test_layer3_api_classifies_sec_edgar_arelle_sidecar_fact_authority_by_default",
    "test_layer3_api_blocks_sec_edgar_html_inline_xbrl_fact_material_default_on_without_sidecar",
    "test_layer3_api_rejects_sec_edgar_html_inline_xbrl_fact_material_default_on_lineage_mismatch",
    "test_layer3_api_rejects_sec_edgar_html_inline_xbrl_fact_material_default_on_toggle_fields",
)
REQUEST_CLASSES_WITHOUT_DEFAULT_ON_TOGGLE = (
    "Layer3SecEdgarHtmlInlineXbrlFactMaterialBridgeRequest",
    "Layer3SecXbrlOperatorReviewWorkflowStatusRequest",
    "Layer3SecXbrlOperatorReviewDecisionSubmitRequest",
    "Layer3SecXbrlOperatorReviewDecisionStatusRequest",
    "Layer3SecXbrlValueRevealAuthorityPrepareRequest",
    "Layer3SecXbrlControlledValueRevealSubmitRequest",
)
DEFAULT_ON_TOGGLE_TOKENS = (
    "arelle_fact_authority_cutover_enabled",
    "default_on_enabled",
    "runtime_default_enabled",
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
        "api": _read("backend/app/api/layer3.py"),
        "api_tests": _read("backend/tests/test_layer3_api.py"),
        "admission": _load_json("diagnostics/assessment/sec-xbrl-default-on-admission-review-report.json"),
        "admission_restatement": _load_json(ADMISSION_RESTATEMENT_REPORT),
        "gate": _load_json("diagnostics/assessment/sec-xbrl-default-on-gate-report.json"),
        "real_corpus_gate": _load_json(REAL_CORPUS_RUNNER_REPORT),
    }
    default_enabled = _contains(
        sources["config"],
        'layer3_sec_edgar_arelle_fact_authority_cutover_enabled: bool = Field(\n        default=True,',
    )
    value_reveal_defaults_off = (
        _contains(
            sources["config"],
            'layer3_sec_edgar_arelle_value_reveal_enabled: bool = Field(\n        default=False,',
        )
        and _contains(
            sources["config"],
            'layer3_sec_xbrl_controlled_value_reveal_submit_enabled: bool = Field(\n        default=False,',
        )
    )
    no_runtime_toggle_fields = _request_classes_exclude_default_on_toggles(sources["api"])
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
                "admission_restatement_decision": sources["admission_restatement"].get("decision"),
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
            all(test_name in sources["api_tests"] for test_name in DEFAULT_ON_FOCUSED_TESTS),
            {"focused_tests": list(DEFAULT_ON_FOCUSED_TESTS)},
            "default_on_runtime_focused_tests_missing",
        ),
        _criterion(
            "server_policy_no_request_toggle",
            no_runtime_toggle_fields
            and "test_layer3_api_rejects_sec_edgar_html_inline_xbrl_fact_material_default_on_toggle_fields"
            in sources["api_tests"],
            {
                "request_classes_checked": list(REQUEST_CLASSES_WITHOUT_DEFAULT_ON_TOGGLE),
                "toggle_tokens_absent_from_request_classes": no_runtime_toggle_fields,
                "api_or_operator_request_toggle_admitted": False,
                "rendered_ui_or_browser_toggle_admitted": False,
                "production_or_nonlocal_authorization_claimed": False,
            },
            "default_on_runtime_request_toggle_admitted",
        ),
        _criterion(
            "value_reveal_and_controlled_submit_defaults_remain_off",
            value_reveal_defaults_off
            and "profile.layer3_sec_edgar_arelle_value_reveal_enabled is False" in sources["api_tests"]
            and "profile.layer3_sec_xbrl_controlled_value_reveal_submit_enabled is False" in sources["api_tests"],
            {
                "value_reveal_default_enabled": False,
                "controlled_value_reveal_submit_default_enabled": False,
                "value_reveal_default_on_claimed": False,
            },
            "default_on_runtime_value_reveal_default_regressed",
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
            "real_corpus_runner_report": REAL_CORPUS_RUNNER_REPORT,
            "real_corpus_runner_archived": False,
            "current_run_live_sec_network_used": sources["real_corpus_gate"].get("current_run_live_sec_network_used"),
            "inherited_live_sec_network_used": sources["real_corpus_gate"].get("live_sec_network_used"),
            "offline_redacted_product_report_import": sources["real_corpus_gate"].get(
                "offline_redacted_product_report_import"
            ),
            "default_on_gate_decision": sources["gate"].get("decision"),
            "admission_review_decision": sources["admission"].get("decision"),
            "admission_restatement_decision": sources["admission_restatement"].get("decision"),
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
            "admission_restatement": ADMISSION_RESTATEMENT_REPORT,
            "real_corpus_runner": REAL_CORPUS_RUNNER_REPORT,
        },
        "runtime_posture": {
            "default_cutover_enabled": default_enabled,
            "persisted_sidecar_required": True,
            "regex_fallback_while_default_on": False if default_enabled else None,
            "synchronous_arelle_in_bridge": False,
            "regex_rollback_env_supported": True,
            "operator_value_reveal_default_enabled": False,
            "controlled_value_reveal_submit_default_enabled": False,
            "server_deployment_policy_owned": True,
            "api_or_operator_request_toggle_admitted": False,
            "rendered_ui_or_browser_toggle_admitted": False,
            "production_or_nonlocal_authorization_claimed": False,
        },
        "non_goals_preserved": {
            "candidate_b_sec_routing_performed": False,
            "cross_company_comparability_claimed": False,
            "final_financial_statement_semantics_claimed": False,
            "gate_b_product_package_ui_redesign_performed": False,
            "rag_vector_model_provider_auth_behavior_added": False,
            "source_acquisition_performed": False,
            "arelle_subprocess_invoked_by_runtime_switch": False,
            "delivery_export_enabled": False,
            "production_readiness_claimed": False,
            "value_reveal_default_on_claimed": False,
        },
        "next_slice": (
            "sec_xbrl_next_downstream_gate_design_selection_before_any_default_on_export_or_production_implementation"
            if default_enabled
            else "sec_edgar_arelle_governance_remediation_followups_v1"
        ),
    }


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _load_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _request_classes_exclude_default_on_toggles(api_source: str) -> bool:
    return all(
        all(token not in _class_source(api_source, class_name) for token in DEFAULT_ON_TOGGLE_TOKENS)
        for class_name in REQUEST_CLASSES_WITHOUT_DEFAULT_ON_TOGGLE
    )


def _class_source(source: str, class_name: str) -> str:
    marker = f"class {class_name}("
    start = source.find(marker)
    if start < 0:
        return ""
    next_class = source.find("\nclass ", start + len(marker))
    return source[start:] if next_class < 0 else source[start:next_class]


def _contains(source: str, text: str) -> bool:
    return text.replace("\r\n", "\n") in source.replace("\r\n", "\n")


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
