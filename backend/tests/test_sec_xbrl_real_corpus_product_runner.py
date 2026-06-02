from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from app.services import layer3_sec_xbrl_canonical_concepts as canonical
from app.services.layer3_utils import stable_hash


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-real-corpus-product-runner.py"


def _runner_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_real_corpus_product_runner", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_real_corpus_product_runner_blocks_without_live_preflight(monkeypatch) -> None:
    module = _runner_module()
    for name in module.REQUIRED_ARELLE_ENV:
        monkeypatch.delenv(name, raising=False)

    report = module.build_report(live=False, user_agent="")

    assert report["decision"] == "real_corpus_default_on_blocked"
    assert report["gate_verdict"] == "FAIL_OR_INCONCLUSIVE"
    assert report["live_sec_network_used"] is False
    assert report["fake_sec_client_used"] is False
    assert report["preflight"]["blocked_reasons"] == [
        "live_execution_not_requested",
        "sec_user_agent_not_configured",
        "arelle_environment_not_configured",
        "arelle_python_unavailable",
        "taxonomy_package_files_unavailable",
        "arelle_cache_dir_unavailable",
    ]
    assert report["summary"]["real_filing_count"] == 0
    assert report["next_slice"] == "sec_edgar_real_corpus_product_path_runner_live_execution_v1"
    family_gate = report["sector_family_activation_validation"]
    assert family_gate["dimension_id"] == "sec_xbrl_sector_family_real_filer_validation_v1"
    assert family_gate["available_dimension_passed"] is True
    assert family_gate["full_gate_satisfied"] is False
    assert family_gate["us_gaap_bank_insurer_subgate_state"] == "pending_operator_offline_filings"
    serialized = json.dumps(report, sort_keys=True)
    for forbidden in (
        "MSFT",
        "STLD",
        "SONY",
        "CCJ",
        "JPM",
        "MET",
        "PLD",
        "FIZZ",
        "XOM",
        "PFE",
        "UAL",
        "AAPL",
        "NVDA",
        "AMZN",
        "TSLA",
        "https://",
        "http://",
    ):
        assert forbidden not in serialized


def test_sec_xbrl_real_corpus_product_runner_counts_ifrs_full_companyfacts() -> None:
    module = _runner_module()
    accession = "ACCESSION-TEST"
    cache = {
        "0000000123": {
            "oracle_used": True,
            "confidence": "primary_companyfacts_standard_taxonomy_accession_scope",
            "_payload": {
                "facts": {
                    "ifrs-full": {
                        "Revenue": {
                            "units": {
                                "CAD": [
                                    {"accn": accession, "val": "123.45"},
                                    {"accn": "OTHER-ACCESSION", "val": "999"},
                                ]
                            }
                        }
                    }
                }
            },
        }
    }

    result = module._companyfacts_count(cik="123", accession=accession, user_agent="ua", cache=cache)

    assert result["oracle_used"] is True
    assert result["confidence"] == "primary_companyfacts_standard_taxonomy_accession_scope"
    assert result["fact_count"] == 1
    assert result["_value_keys"] == [("Revenue", "CAD", "123.45")]
    assert result["_value_keys_period_aware"] == [("Revenue", "CAD", ("i", ""), "123.45")]


def test_sec_xbrl_real_corpus_product_runner_matches_ifrs_full_sidecar_values(monkeypatch) -> None:
    module = _runner_module()
    sidecar = {
        "resolved_fact_records": [
            {
                "resolved_fact_id": "fact-1",
                "concept": {
                    "namespace": "https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full",
                    "local_name": "Revenue",
                    "standard": True,
                },
                "unit": {"currency": "iso4217:CAD", "measures": ["iso4217:CAD"]},
                "dimensions": {"explicit": [], "typed": []},
                "decimals": "0",
            }
        ]
    }
    monkeypatch.setattr(
        module.layer3_sec_xbrl_sidecar,
        "read_sec_edgar_arelle_resolved_fact_authority_internal_value_store",
        lambda _sidecar: {"value_records": [{"resolved_fact_id": "fact-1", "effective_value": "123"}]},
    )

    result = module._companyfacts_value_match(
        sidecar=sidecar,
        companyfacts={"_value_keys": [("Revenue", "CAD", "123")]},
    )

    assert result == {"match_count": 1, "compared_count": 1, "match_rate": 1.0}


def test_sec_xbrl_real_corpus_product_runner_adds_period_aware_value_match(monkeypatch) -> None:
    module = _runner_module()
    sidecar = {
        "resolved_fact_records": [
            _resolved_fact(
                "fact-extra",
                local_name="CashAndCashEquivalentsAtCarryingValue",
                period={"type": "instant", "instant": "prior-extra-period"},
            ),
            _resolved_fact(
                "fact-current",
                local_name="CashAndCashEquivalentsAtCarryingValue",
                period={"type": "instant", "instant": "current-period"},
            ),
            _resolved_fact(
                "fact-prior",
                local_name="CashAndCashEquivalentsAtCarryingValue",
                period={"type": "instant", "instant": "prior-period"},
            ),
        ]
    }
    monkeypatch.setattr(
        module.layer3_sec_xbrl_sidecar,
        "read_sec_edgar_arelle_resolved_fact_authority_internal_value_store",
        lambda _sidecar: {
            "value_records": [
                {"resolved_fact_id": "fact-extra", "effective_value": "300"},
                {"resolved_fact_id": "fact-current", "effective_value": "200"},
                {"resolved_fact_id": "fact-prior", "effective_value": "100"},
            ]
        },
    )
    companyfacts = {
        "_value_keys": [
            ("CashAndCashEquivalentsAtCarryingValue", "USD", "200"),
            ("CashAndCashEquivalentsAtCarryingValue", "USD", "100"),
        ],
        "_value_keys_period_aware": [
            ("CashAndCashEquivalentsAtCarryingValue", "USD", ("i", "current-period"), "200"),
            ("CashAndCashEquivalentsAtCarryingValue", "USD", ("i", "prior-period"), "100"),
        ],
    }

    period_blind = module._companyfacts_value_match(sidecar=sidecar, companyfacts=companyfacts)
    period_aware = module._companyfacts_value_match_period_aware(sidecar=sidecar, companyfacts=companyfacts)

    assert period_blind == {"match_count": 2, "compared_count": 3, "match_rate": 0.6667}
    assert period_aware == {"match_count": 2, "compared_count": 2, "match_rate": 1.0}


def test_sec_xbrl_real_corpus_product_runner_period_aware_includes_divided_units(monkeypatch) -> None:
    module = _runner_module()
    sidecar = {
        "resolved_fact_records": [
            _resolved_fact(
                "fact-eps",
                local_name="EarningsPerShareBasic",
                period={"type": "duration", "start": "eps-start", "end": "eps-end"},
                unit={
                    "currency": "iso4217:USD",
                    "measures": ["iso4217:USD"],
                    "numerator": ["iso4217:USD"],
                    "denominator": ["xbrli:shares"],
                },
                decimals="2",
            )
        ]
    }
    monkeypatch.setattr(
        module.layer3_sec_xbrl_sidecar,
        "read_sec_edgar_arelle_resolved_fact_authority_internal_value_store",
        lambda _sidecar: {"value_records": [{"resolved_fact_id": "fact-eps", "effective_value": "2.50"}]},
    )
    companyfacts = {
        "_value_keys": [("EarningsPerShareBasic", "USD/shares", "2.50")],
        "_value_keys_period_aware": [
            ("EarningsPerShareBasic", "USD/shares", ("d", "eps-start", "eps-end"), "2.50")
        ],
    }

    period_blind = module._companyfacts_value_match(sidecar=sidecar, companyfacts=companyfacts)
    period_aware = module._companyfacts_value_match_period_aware(sidecar=sidecar, companyfacts=companyfacts)

    assert period_blind == {"match_count": 0, "compared_count": 0, "match_rate": None}
    assert period_aware == {"match_count": 1, "compared_count": 1, "match_rate": 1.0}


def test_sec_xbrl_real_corpus_product_runner_admits_when_existing_chain_reaches_archive(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))

    def per_filing(start: int, count: int, forms: list[str]) -> list[dict]:
        return [
            {
                "fixture_hash": f"{start + index:024x}"[-24:],
                "form": forms[index % len(forms)],
                "issuer_by_hash": f"{start + index:024x}"[-24:],
                "record_state": "supported",
                "zero_fact_status": "not_zero",
                "production_factauthority_fact_count": 100,
                "arelle_resolved_fact_count": 100,
                "independent_inline_fact_count": 100,
                "completeness_guard": "passed",
                "companyfacts_oracle_used": True,
                "companyfacts_effective_value_match_count": 99,
                "companyfacts_effective_value_compared_count": 100,
                "companyfacts_effective_value_mismatch_count": 1,
                "taxonomy_package_count": 7,
                "taxonomy_package_invalid_count": 6,
                "taxonomy_package_invalid_hashes": ["1" * 64],
            }
            for index in range(count)
        ]

    ready_rows = [
        {
            "matrix_label": "core",
            "matrix_ref_hash": "a" * 24,
            "strata": ["large_domestic_us_gaap", "small_mid_domestic_us_gaap"],
            "pipeline_state": "ready",
            "filing_count": 8,
            "supported_count": 8,
            "blocked_or_degraded_count": 0,
            "forms": {"10-K": 4, "10-Q": 3, "8-K": 1},
            "issuer_hash_count": 4,
            "records_with_arelle_sidecar_output": 8,
            "records_with_selected_fact_authority_equal_to_sidecar": 8,
            "records_with_handoff_export_prepare": 8,
            "resolved_fact_count": 800,
            "independent_inline_fact_count": 800,
            "per_filing": per_filing(100, 8, ["10-K", "10-Q", "8-K"]),
            "delivery_status": module.layer3_sec_edgar_delivery_status_provenance.READY_STATE,
            "operator_inspection_status": module.layer3_sec_edgar_operator_inspection.READY_STATE,
            "operator_product_surface_status": module.layer3_sec_edgar_operator_product_surface.READY_STATE,
            "durable_delivery_archive_status": module.layer3_sec_edgar_durable_delivery_archive.READY_STATE,
            "operator_surface_values_exposed": False,
        },
        {
            "matrix_label": "breadth",
            "matrix_ref_hash": "b" * 24,
            "strata": ["foreign_private_ifrs_20f", "canadian_40f", "foreign_6k_sparse"],
            "pipeline_state": "ready",
            "filing_count": 8,
            "supported_count": 8,
            "blocked_or_degraded_count": 0,
            "forms": {"20-F": 1, "40-F": 1, "6-K": 2, "10-K": 2, "10-Q": 2},
            "issuer_hash_count": 4,
            "records_with_arelle_sidecar_output": 8,
            "records_with_selected_fact_authority_equal_to_sidecar": 8,
            "records_with_handoff_export_prepare": 8,
            "resolved_fact_count": 800,
            "independent_inline_fact_count": 800,
            "per_filing": per_filing(200, 8, ["20-F", "40-F", "6-K", "10-K", "10-Q"]),
            "delivery_status": "not_required_for_broader_extraction_gate",
            "operator_inspection_status": "not_required_for_broader_extraction_gate",
            "operator_product_surface_status": "not_required_for_broader_extraction_gate",
            "durable_delivery_archive_status": "not_required_for_broader_extraction_gate",
            "operator_surface_values_exposed": False,
        },
        {
            "matrix_label": "expansion",
            "matrix_ref_hash": "c" * 24,
            "strata": ["current_report_8k_sparse", "amendment_restatement"],
            "pipeline_state": "ready",
            "filing_count": 8,
            "supported_count": 8,
            "blocked_or_degraded_count": 0,
            "forms": {"10-K": 4, "10-Q": 2, "8-K": 2},
            "issuer_hash_count": 4,
            "records_with_arelle_sidecar_output": 8,
            "records_with_selected_fact_authority_equal_to_sidecar": 8,
            "records_with_handoff_export_prepare": 8,
            "resolved_fact_count": 800,
            "independent_inline_fact_count": 800,
            "per_filing": per_filing(300, 8, ["10-K", "10-Q", "8-K"]),
            "delivery_status": module.layer3_sec_edgar_delivery_status_provenance.READY_STATE,
            "operator_inspection_status": module.layer3_sec_edgar_operator_inspection.READY_STATE,
            "operator_product_surface_status": module.layer3_sec_edgar_operator_product_surface.READY_STATE,
            "durable_delivery_archive_status": module.layer3_sec_edgar_durable_delivery_archive.READY_STATE,
            "operator_surface_values_exposed": False,
        },
        {
            "matrix_label": "large-cap-extension",
            "matrix_ref_hash": "d" * 24,
            "strata": ["no_inline_or_zero_fact_diagnostic"],
            "pipeline_state": "ready",
            "filing_count": 8,
            "supported_count": 8,
            "blocked_or_degraded_count": 0,
            "forms": {"10-K": 4, "10-Q": 4},
            "issuer_hash_count": 4,
            "records_with_arelle_sidecar_output": 8,
            "records_with_selected_fact_authority_equal_to_sidecar": 8,
            "records_with_handoff_export_prepare": 8,
            "resolved_fact_count": 800,
            "independent_inline_fact_count": 800,
            "per_filing": per_filing(400, 8, ["10-K", "10-Q"]),
            "delivery_status": "not_required_for_broader_extraction_gate",
            "operator_inspection_status": "not_required_for_broader_extraction_gate",
            "operator_product_surface_status": "not_required_for_broader_extraction_gate",
            "durable_delivery_archive_status": "not_required_for_broader_extraction_gate",
            "operator_surface_values_exposed": False,
        },
    ]

    storage = _offline_sector_family_storage(tmp_path)
    report = module.build_report(
        live=True,
        storage_dir=storage,
        matrix_plan=_stratified_plan(),
        user_agent="Layer3 diagnostics contact@example.com",
        runner=lambda _storage, _agent, _namespace, _taxonomy: ready_rows,
    )

    assert report["decision"] == "real_corpus_default_on_validated"
    assert report["gate_verdict"] == "PASS"
    assert report["summary"]["real_filing_count"] == 32
    assert report["summary"]["issuer_hash_count"] == 32
    assert report["summary"]["required_forms_present"] is True
    assert report["summary"]["records_with_arelle_sidecar_output"] == 32
    assert report["summary"]["companyfacts_value_match_rate"] == 0.99
    assert report["summary"]["filings_with_invalid_taxonomy_package_entries"] == 32
    assert report["summary"]["taxonomy_package_invalid_count"] == 192
    assert report["sector_family_activation_validation"]["status"] == "sector_family_real_filer_validation_satisfied"
    assert report["sector_family_activation_validation"]["full_gate_satisfied"] is True
    assert report["sector_family_evidence_provenance"] == {
        "live_matrix_storage_marker": module._storage_marker(storage),
        "operator_supplied_sector_family_storage": False,
        "paths_redacted": True,
        "provenance_mode": "single_storage_root",
        "raw_local_paths_committed": False,
        "sector_family_offline_storage_marker": module._storage_marker(storage),
        "storage_markers_match": True,
    }
    assert report["runtime_default_decision"]["resulting_default_enabled"] is True
    assert report["next_slice"] == "sec_edgar_operator_surface_gated_value_reveal_v1"

    incomplete_storage = _offline_sector_family_storage(
        tmp_path,
        storage_dir=tmp_path / "incomplete-offline-storage",
        insurer_qnames=["us-gaap:PremiumsEarnedNet"],
    )
    blocked_report = module.build_report(
        live=True,
        storage_dir=incomplete_storage,
        matrix_plan=_stratified_plan(),
        user_agent="Layer3 diagnostics contact@example.com",
        runner=lambda _storage, _agent, _namespace, _taxonomy: ready_rows,
    )
    assert blocked_report["gate_verdict"] == "FAIL_OR_INCONCLUSIVE"
    assert blocked_report["runtime_default_decision"]["resulting_default_enabled"] is False
    assert blocked_report["next_slice"] == "sec_xbrl_sector_family_us_gaap_bank_insurer_subgate_v1"
    assert any(
        item["reason"] == "sector_family_available_filer_activation_dimension_not_satisfied"
        for item in blocked_report["blocking_reasons"]
    )

    default_live_storage = tmp_path / "default-live-storage"
    monkeypatch.setattr(module, "DEFAULT_LIVE_STORAGE", default_live_storage)

    def runner_writes_sector_family_storage(storage_path, _agent, _namespace, _taxonomy):
        _offline_sector_family_storage(tmp_path, storage_dir=storage_path)
        return ready_rows

    default_storage_report = module.build_report(
        live=True,
        matrix_plan=_stratified_plan(),
        user_agent="Layer3 diagnostics contact@example.com",
        runner=runner_writes_sector_family_storage,
    )
    assert default_storage_report["sector_family_activation_validation"]["status"] == (
        "sector_family_real_filer_validation_satisfied"
    )
    assert default_storage_report["sector_family_activation_validation"]["full_gate_satisfied"] is True

    separate_live_storage = tmp_path / "separate-live-storage"
    separate_sector_family_storage = _offline_sector_family_storage(
        tmp_path,
        storage_dir=tmp_path / "separate-sector-family-storage",
    )
    separate_storage_report = module.build_report(
        live=True,
        storage_dir=separate_live_storage,
        sector_family_storage_dir=separate_sector_family_storage,
        matrix_plan=_stratified_plan(),
        user_agent="Layer3 diagnostics contact@example.com",
        runner=lambda _storage, _agent, _namespace, _taxonomy: ready_rows,
    )
    separate_provenance = separate_storage_report["sector_family_evidence_provenance"]
    assert separate_storage_report["decision"] == "real_corpus_default_on_validated"
    assert separate_provenance == {
        "live_matrix_storage_marker": module._storage_marker(separate_live_storage),
        "operator_supplied_sector_family_storage": True,
        "paths_redacted": True,
        "provenance_mode": "separate_operator_offline_sector_family_evidence",
        "raw_local_paths_committed": False,
        "sector_family_offline_storage_marker": module._storage_marker(separate_sector_family_storage),
        "storage_markers_match": False,
    }
    assert str(separate_live_storage) not in json.dumps(separate_provenance, sort_keys=True)
    assert str(separate_sector_family_storage) not in json.dumps(separate_provenance, sort_keys=True)


def test_sec_xbrl_real_corpus_product_runner_sector_family_report_is_reproducible_scope(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(tmp_path)

    report = module.build_sector_family_validation_report(offline_storage_dir=storage)
    repeated = module.build_sector_family_validation_report(offline_storage_dir=storage)

    assert report == repeated
    assert report["schema_id"] == "diagnostics.sec_xbrl_sector_family_real_filer_validation_report.v1"
    assert report["gate_verdict"] == "PASS"
    assert report["storage_dir_marker"] == module._storage_marker(storage)
    assert report["live_sec_network_used"] is False
    assert report["arelle_invoked"] is False
    assert report["report_scope"]["sector_family_subgate_in_scope"] is True
    assert report["report_scope"]["broader_live_matrix_product_gate_in_scope"] is False
    assert report["matrix_execution_plan"]["state"] == "not_in_scope"
    assert report["stratified_matrix_required_strata_readiness"]["state"] == "not_in_scope"
    assert report["sector_family_evidence_provenance"] == {
        "provenance_mode": "single_reproducible_sector_family_storage_root",
        "storage_dir_marker": module._storage_marker(storage),
        "sector_family_offline_storage_marker": module._storage_marker(storage),
        "storage_markers_match": True,
        "operator_supplied_sector_family_storage": True,
        "paths_redacted": True,
        "raw_local_paths_committed": False,
    }
    assert [item["criterion"] for item in report["criteria"]] == [
        "sector_family_available_filer_activation_dimension"
    ]
    assert report["sector_family_activation_validation"]["full_gate_satisfied"] is True


def test_sec_xbrl_real_corpus_product_runner_scaffolds_sector_family_activation_dimension() -> None:
    module = _runner_module()

    gate = module._sector_family_activation_validation()
    references = {
        item["reference_role"]: item
        for item in gate["available_reference_results"]
    }
    pending_sub_gate = gate["pending_sub_gates"][0]
    serialized = json.dumps(gate, sort_keys=True)

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert gate["available_dimension_passed"] is True
    assert gate["available_reference_filer_count"] == 3
    assert gate["validated_available_family_ids"] == ["banking", "extractive", "insurance"]
    assert gate["ifrs_anchor_activation_passed"] is True
    assert gate["supporting_only_control_passed"] is True
    assert gate["universal_only_control_passed"] is True
    assert gate["full_gate_satisfied"] is False
    assert references["available_ifrs_financial_services_activation_reference"]["actual_present_family_ids"] == [
        "banking",
        "insurance",
    ]
    assert references["available_ifrs_extractive_activation_reference"]["actual_present_family_ids"] == [
        "extractive"
    ]
    assert references["available_universal_only_control_reference"]["actual_present_family_ids"] == []
    assert gate["supporting_only_control"]["reported_concepts"] == ["us-gaap:InterestExpense"]
    assert gate["supporting_only_control"]["actual_present_family_ids"] == []
    assert gate["supporting_only_control"]["supporting_only_family_ids"] == ["banking"]
    assert pending_sub_gate["state"] == "pending_operator_offline_filings"
    assert pending_sub_gate["validated"] is False
    assert pending_sub_gate["required_activation_anchor_concepts"] == [
        "us-gaap:Deposits",
        "us-gaap:LiabilityForClaimsAndClaimsAdjustmentExpense",
        "us-gaap:PremiumsEarnedNet",
    ]
    assert pending_sub_gate["supporting_headline_concepts_tracked"] == [
        "us-gaap:InterestAndDividendIncomeOperating",
        "us-gaap:InterestExpense",
    ]
    assert gate["projection_row_shape"]["stable_across_available_references"] is True
    assert gate["projection_row_shape"]["unique_row_shape_hash_count"] == 1
    for forbidden in ("SONY", "CCJ", "FIZZ", "313838", "1009001", "69891", "contact@nexonpvp.net"):
        assert forbidden not in serialized


def test_sec_xbrl_real_corpus_product_runner_closes_sector_family_gate_from_offline_storage(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(tmp_path)

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]
    class_results = {
        item["reference_class"]: item
        for item in sub_gate["class_results"]
    }
    serialized = json.dumps(gate, sort_keys=True)

    assert gate["status"] == "sector_family_real_filer_validation_satisfied"
    assert gate["full_gate_satisfied"] is True
    assert gate["pending_sub_gates"] == []
    assert sub_gate["state"] == "validated"
    assert sub_gate["validated"] is True
    assert sub_gate["offline_storage_evidence"]["offline_storage_used"] is True
    assert sub_gate["offline_storage_evidence"]["paths_redacted"] is True
    assert class_results["real_us_gaap_bank_filing"]["passed"] is True
    assert class_results["real_us_gaap_bank_filing"]["activation_anchor_concepts_present"] == ["us-gaap:Deposits"]
    assert class_results["real_us_gaap_bank_filing"]["missing_supporting_headline_concepts"] == [
        "us-gaap:InterestAndDividendIncomeOperating",
        "us-gaap:InterestExpense",
    ]
    assert class_results["real_us_gaap_insurer_filing"]["passed"] is True
    assert class_results["real_us_gaap_insurer_filing"]["activation_anchor_concepts_present"] == [
        "us-gaap:LiabilityForClaimsAndClaimsAdjustmentExpense",
        "us-gaap:PremiumsEarnedNet",
    ]
    for forbidden in (str(storage), "b" * 64, "c" * 64):
        assert forbidden not in serialized


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_fails_closed_without_insurer_anchor(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        insurer_qnames=["us-gaap:PremiumsEarnedNet"],
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert gate["full_gate_satisfied"] is False
    assert gate["pending_sub_gates"] == [sub_gate]
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert "real_us_gaap_insurer_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_rejects_ungoverned_sidecar_json(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        sidecar_metadata_valid=False,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert sub_gate["offline_storage_evidence"]["sidecar_reference_count"] == 0
    assert "real_us_gaap_bank_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]
    assert "real_us_gaap_insurer_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_rejects_handwritten_sidecar_hash_shape(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        sidecar_receipt_shape_valid=False,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert sub_gate["offline_storage_evidence"]["sidecar_reference_count"] == 0
    assert "real_us_gaap_bank_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]
    assert "real_us_gaap_insurer_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_rejects_connector_hash_mismatch(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        connector_receipt_valid=False,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert sub_gate["offline_storage_evidence"]["connector_reference_count"] == 0
    assert "real_us_gaap_bank_filing_annual_reference_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]
    assert "real_us_gaap_insurer_filing_annual_reference_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_rejects_sidecar_inventory_mismatch(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        sidecar_inventory_valid=False,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert sub_gate["offline_storage_evidence"]["sidecar_reference_count"] == 0
    assert "real_us_gaap_bank_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]
    assert "real_us_gaap_insurer_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_rejects_sidecar_missing_projection(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        sidecar_projection_present=False,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert sub_gate["offline_storage_evidence"]["sidecar_reference_count"] == 0
    assert "real_us_gaap_bank_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]
    assert "real_us_gaap_insurer_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_rejects_sidecar_hash_basis_mismatch(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        sidecar_hash_basis_valid=False,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert sub_gate["offline_storage_evidence"]["sidecar_reference_count"] == 0
    assert "real_us_gaap_bank_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]
    assert "real_us_gaap_insurer_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_rejects_sidecars_with_raw_values(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        sidecar_raw_values=True,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert sub_gate["offline_storage_evidence"]["sidecar_reference_count"] == 0
    assert "real_us_gaap_bank_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]
    assert "real_us_gaap_insurer_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_requires_standard_non_dimensional_anchors(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        sidecar_standard_concepts=False,
        sidecar_dimensional_facts=True,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]
    evidence = sub_gate["offline_storage_evidence"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert evidence["sidecar_reference_count"] == 2
    assert "real_us_gaap_bank_filing_activation_anchor_missing" in evidence["blocked_reasons"]
    assert "real_us_gaap_insurer_filing_activation_anchor_missing" in evidence["blocked_reasons"]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_rejects_nested_acquisition_hash_mismatch(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        nested_acquisition_valid=False,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert sub_gate["offline_storage_evidence"]["connector_reference_count"] == 0
    assert "real_us_gaap_bank_filing_annual_reference_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]
    assert "real_us_gaap_insurer_filing_annual_reference_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_rejects_split_sidecar_anchor_union(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        split_insurer_sidecars=True,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]
    class_results = {
        item["reference_class"]: item
        for item in sub_gate["offline_storage_evidence"]["class_results"]
    }

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert class_results["real_us_gaap_insurer_filing"]["accepted_sidecar_candidate_count"] == 2
    assert class_results["real_us_gaap_insurer_filing"]["passed"] is False
    assert "real_us_gaap_insurer_filing_activation_anchor_missing" in sub_gate["offline_storage_evidence"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_sector_family_gate_requires_distinct_bank_and_insurer_filings(
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = _offline_sector_family_storage(
        tmp_path,
        shared_bank_insurer_source=True,
    )

    gate = module._sector_family_activation_validation(offline_storage_dir=storage)
    sub_gate = gate["us_gaap_bank_insurer_subgate"]
    evidence = sub_gate["offline_storage_evidence"]

    assert gate["status"] == "partially_satisfied_us_gaap_subgate_pending"
    assert sub_gate["state"] == "blocked_offline_artifacts_incomplete"
    assert evidence["distinct_source_artifact_marker_count"] == 1
    assert evidence["required_distinct_source_artifact_count"] == 2
    assert "us_gaap_bank_insurer_distinct_source_artifact_required" in evidence["blocked_reasons"]


def test_sec_xbrl_real_corpus_product_runner_projection_row_shape_matches_canonical_projection() -> None:
    module = _runner_module()
    report = canonical.build_redacted_projection_report(
        issuer_bundles=[_projection_bundle(module)],
        include_sector_families=True,
    )

    assert module._sector_family_projection_row_shape(1)["public_row_keys"] == sorted(report["per_issuer"][0])


def test_sec_xbrl_real_corpus_product_runner_blocks_live_without_external_matrix_plan(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))

    report = module.build_report(
        live=True,
        storage_dir=tmp_path,
        user_agent="redacted operator test agent",
        runner=lambda _storage, _agent, _namespace, _taxonomy: [
            {"matrix_label": "should-not-run", "pipeline_state": "ready"}
        ],
    )

    assert report["live_sec_network_used"] is False
    assert report["matrix_execution_plan"]["state"] == "blocked"
    assert report["matrix_execution_plan"]["blocked_reasons"] == ["matrix_plan_required_for_selected_tranche"]
    assert report["per_matrix"] == []
    assert any(
        item["reason"] == "real_corpus_product_path_matrix_plan_not_satisfied"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_real_corpus_product_runner_executes_external_stratified_plan_redacted(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))
    plan = _stratified_plan()
    observed: list[tuple[str, tuple[str, ...]]] = []
    forms = ["10-K", "10-Q", "20-F", "40-F", "8-K", "6-K", "10-K/A", "10-Q/A"]

    def fake_run_matrix_chunk(label, matrix, *, strata, db, request_namespace, user_agent):
        del db, request_namespace, user_agent
        observed.append((label, tuple(strata)))
        start = len(observed) * 100
        return {
            "matrix_label": label,
            "matrix_ref_hash": module.stable_hash({"matrix": list(matrix)})[:24],
            "strata": list(strata),
            "pipeline_state": "ready",
            "filing_count": 5,
            "supported_count": 5,
            "blocked_or_degraded_count": 0,
            "forms": {forms[(len(observed) - 1) % len(forms)]: 5},
            "issuer_hash_count": 4,
            "records_with_arelle_sidecar_output": 5,
            "records_with_selected_fact_authority_equal_to_sidecar": 5,
            "records_with_handoff_export_prepare": 5,
            "resolved_fact_count": 500,
            "independent_inline_fact_count": 500,
            "per_filing": [
                {
                    "fixture_hash": f"{start + index:024x}"[-24:],
                    "form": forms[(len(observed) + index - 1) % len(forms)],
                    "issuer_by_hash": f"{start + index:024x}"[-24:],
                    "record_state": "supported",
                    "zero_fact_status": "not_zero",
                    "arelle_resolved_fact_count": 100,
                    "independent_inline_fact_count": 100,
                    "completeness_guard": "passed",
                    "companyfacts_oracle_used": True,
                    "companyfacts_effective_value_match_count": 100,
                    "companyfacts_effective_value_compared_count": 100,
                    "companyfacts_effective_value_mismatch_count": 0,
                }
                for index in range(5)
            ],
            "delivery_status": "not_required_for_broader_extraction_gate",
            "operator_inspection_status": "not_required_for_broader_extraction_gate",
            "operator_product_surface_status": "not_required_for_broader_extraction_gate",
            "durable_delivery_archive_status": "not_required_for_broader_extraction_gate",
            "operator_surface_values_exposed": False,
        }

    monkeypatch.setattr(module, "_run_matrix_chunk", fake_run_matrix_chunk)
    _offline_sector_family_storage(tmp_path, storage_dir=tmp_path)

    report = module.build_report(
        live=True,
        storage_dir=tmp_path,
        matrix_plan=plan,
        user_agent="Layer3 diagnostics contact@example.com",
    )
    serialized = json.dumps(report, sort_keys=True)

    assert report["decision"] == "real_corpus_default_on_validated"
    assert report["matrix_execution_plan"]["mode"] == "external_stratified_matrix_plan"
    assert report["matrix_execution_plan"]["missing_required_strata"] == []
    assert report["matrix_execution_plan"]["chunk_count"] == 6
    assert [label for label, _strata in observed] == [
        chunk["matrix_label"] for chunk in plan["chunks"]
    ]
    assert set(report["matrix_execution_plan"]["covered_strata"]) == set(module.REQUIRED_STRATA)
    assert report["summary"]["real_filing_count"] == 30
    assert report["summary"]["strata_readiness"]["all_required_strata_ready"] is True
    assert report["summary"]["required_forms_present"] is True
    raw_plan_identities = {
        ticker
        for chunk in plan["chunks"]
        for ticker in chunk["company_matrix"]
    }
    for forbidden in (*raw_plan_identities, str(tmp_path), "Layer3 diagnostics contact@example.com"):
        assert forbidden not in serialized


def test_sec_xbrl_real_corpus_product_runner_imports_redacted_product_report_offline(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage, plan, source_report = _redacted_product_report_fixture(module, monkeypatch, tmp_path)
    monkeypatch.setattr(
        module,
        "_run_live_product_path",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live runner invoked")),
    )

    report = module.build_report(
        live=False,
        storage_dir=storage,
        sector_family_storage_dir=storage,
        matrix_plan=plan,
        redacted_product_runner_report=source_report,
        user_agent="",
    )
    serialized = json.dumps(report, sort_keys=True)

    assert report["decision"] == "real_corpus_default_on_validated"
    assert report["gate_verdict"] == "PASS"
    assert report["live_sec_network_used"] is True
    assert report["current_run_live_sec_network_used"] is False
    assert report["preflight"]["live_requested"] is False
    assert report["offline_redacted_product_report_import"]["state"] == "passed"
    assert report["offline_redacted_product_report_import"]["evidence"]["inherited_live_sec_network_used"] is True
    assert report["offline_redacted_product_report_import"]["evidence"]["current_run_arelle_subprocess_invoked"] is False
    assert report["summary"]["real_filing_count"] == 30
    assert report["summary"]["strata_readiness"]["all_required_strata_ready"] is True
    assert [item["criterion"] for item in report["criteria"] if item["state"] != "passed"] == []
    for forbidden in (str(storage), "MSFT", "AAPL", "https://sec.gov", "0000123456-26-000001"):
        assert forbidden not in serialized


def test_sec_xbrl_real_corpus_product_runner_import_direct_call_does_not_report_current_live_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage, plan, source_report = _redacted_product_report_fixture(module, monkeypatch, tmp_path)
    monkeypatch.setattr(
        module,
        "_run_live_product_path",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live runner invoked")),
    )

    report = module.build_report(
        live=True,
        storage_dir=storage,
        sector_family_storage_dir=storage,
        matrix_plan=plan,
        redacted_product_runner_report=source_report,
        user_agent="operator@example.com",
    )

    assert report["decision"] == "real_corpus_default_on_validated"
    assert report["live_sec_network_used"] is True
    assert report["current_run_live_sec_network_used"] is False
    assert report["offline_redacted_product_report_import"]["evidence"]["current_run_arelle_subprocess_invoked"] is False


def test_sec_xbrl_real_corpus_product_runner_reports_current_live_run_without_import(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    _storage, _plan, source_report = _redacted_product_report_fixture(module, monkeypatch, tmp_path)

    assert source_report["live_sec_network_used"] is True
    assert source_report["current_run_live_sec_network_used"] is True
    assert source_report["offline_redacted_product_report_import"]["state"] == "not_requested"


def test_sec_xbrl_real_corpus_product_runner_rejects_import_cli_default_write(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage = tmp_path / "storage"
    storage.mkdir()
    report_path = tmp_path / "report.json"
    report_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sec-xbrl-real-corpus-product-runner.py",
            "--redacted-product-runner-report",
            str(report_path),
            "--storage-dir",
            str(storage),
            "--apply-default-decision",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert exc.value.code == 2


def test_sec_xbrl_real_corpus_product_runner_rejects_imported_report_storage_marker_mismatch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage, plan, source_report = _redacted_product_report_fixture(module, monkeypatch, tmp_path)
    mismatched_storage = tmp_path / "mismatched-storage"
    mismatched_storage.mkdir()

    report = module.build_report(
        live=False,
        storage_dir=mismatched_storage,
        sector_family_storage_dir=storage,
        matrix_plan=plan,
        redacted_product_runner_report=source_report,
        user_agent="",
    )

    assert report["decision"] == "real_corpus_default_on_blocked"
    assert report["live_sec_network_used"] is False
    assert report["per_matrix"] == []
    assert "offline_product_report_storage_marker_mismatch" in report["offline_redacted_product_report_import"][
        "blocked_reasons"
    ]
    assert any(
        item["criterion"] == "offline_redacted_product_report_import"
        and item["state"] == "blocked"
        for item in report["criteria"]
    )


def test_sec_xbrl_real_corpus_product_runner_rejects_imported_report_raw_identity(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage, plan, source_report = _redacted_product_report_fixture(module, monkeypatch, tmp_path)
    source_report["raw_cik"] = "123456"

    report = module.build_report(
        live=False,
        storage_dir=storage,
        sector_family_storage_dir=storage,
        matrix_plan=plan,
        redacted_product_runner_report=source_report,
        user_agent="",
    )

    assert report["decision"] == "real_corpus_default_on_blocked"
    assert report["offline_redacted_product_report_import"]["evidence"]["redaction_scan"]["raw_cik_found"] is True
    assert "offline_product_report_redaction_scan_failed" in report["offline_redacted_product_report_import"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_import_scan_rejects_common_url_and_path_forms(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    storage, plan, source_report = _redacted_product_report_fixture(module, monkeypatch, tmp_path)
    source_report["raw_sec_url_variant"] = "www.sec.gov/Archives/edgar/data/redacted"
    source_report["raw_local_path_variant"] = "C:/Users/operator/sec-storage"

    report = module.build_report(
        live=False,
        storage_dir=storage,
        sector_family_storage_dir=storage,
        matrix_plan=plan,
        redacted_product_runner_report=source_report,
        user_agent="",
    )

    scan = report["offline_redacted_product_report_import"]["evidence"]["redaction_scan"]
    assert report["decision"] == "real_corpus_default_on_blocked"
    assert scan["raw_sec_url_found"] is True
    assert scan["raw_local_path_found"] is True
    assert "offline_product_report_redaction_scan_failed" in report["offline_redacted_product_report_import"][
        "blocked_reasons"
    ]


def test_sec_xbrl_real_corpus_product_runner_blocks_invalid_external_stratified_plan(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))

    report = module.build_report(
        live=True,
        matrix_plan={
            "schema_id": module.MATRIX_PLAN_SCHEMA_ID,
            "matrix_mode": module.MATRIX_PLAN_MODE,
            "chunks": [
                {
                    "matrix_label": "bad",
                    "company_matrix": ["UNADMITTED"],
                    "strata": ["large_domestic_us_gaap"],
                }
            ],
        },
        user_agent="Layer3 diagnostics contact@example.com",
    )

    assert report["live_sec_network_used"] is False
    assert report["matrix_execution_plan"]["state"] == "blocked"
    assert "matrix_plan_chunk_company_matrix_invalid" in report["matrix_execution_plan"]["blocked_reasons"]
    assert "matrix_plan_required_strata_missing" in report["matrix_execution_plan"]["blocked_reasons"]
    assert any(
        item["reason"] == "real_corpus_product_path_matrix_plan_not_satisfied"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_real_corpus_product_runner_blocks_duplicate_external_plan_issuers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))

    matrices = [
        list(matrix)
        for _label, matrix in module.MATRIX_CHUNKS
    ]
    plan = {
        "schema_id": module.MATRIX_PLAN_SCHEMA_ID,
        "matrix_mode": module.MATRIX_PLAN_MODE,
        "chunks": [
            _plan_chunk("first", matrices[0][:2], ["large_domestic_us_gaap"]),
            _plan_chunk("second", matrices[0][1:2] + matrices[1][3:], ["small_mid_domestic_us_gaap"]),
        ],
    }

    report = module.build_report(
        live=True,
        matrix_plan=plan,
        user_agent="Layer3 diagnostics contact@example.com",
    )

    assert report["live_sec_network_used"] is False
    assert report["matrix_execution_plan"]["state"] == "blocked"
    assert "matrix_plan_duplicate_company_matrix_issuer" in report["matrix_execution_plan"]["blocked_reasons"]


def test_sec_xbrl_real_corpus_product_runner_blocks_raw_identity_in_matrix_label(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))

    plan = _stratified_plan()
    raw_label = "https://sec.gov/Archives/edgar/data/core"
    plan["chunks"][0]["matrix_label"] = raw_label

    report = module.build_report(
        live=True,
        matrix_plan=plan,
        user_agent="Layer3 diagnostics contact@example.com",
    )
    serialized = json.dumps(report, sort_keys=True)

    assert report["live_sec_network_used"] is False
    assert report["matrix_execution_plan"]["state"] == "blocked"
    assert "matrix_plan_chunk_label_raw_identity_not_admitted" in report["matrix_execution_plan"]["blocked_reasons"]
    assert raw_label not in serialized


def test_sec_xbrl_real_corpus_product_runner_blocks_raw_cik_in_matrix_label(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))

    for raw_label in ("789019", "cik-789019", "CIK0000789019", "cik-0000123456", "123456"):
        plan = _stratified_plan()
        plan["chunks"][0]["matrix_label"] = raw_label

        report = module.build_report(
            live=True,
            matrix_plan=plan,
            user_agent="redacted operator test agent",
        )
        serialized = json.dumps(report, sort_keys=True)

        assert report["live_sec_network_used"] is False
        assert report["matrix_execution_plan"]["state"] == "blocked"
        assert "matrix_plan_chunk_label_raw_identity_not_admitted" in report["matrix_execution_plan"][
            "blocked_reasons"
        ]
        assert raw_label not in serialized


def test_sec_xbrl_real_corpus_product_runner_matrix_label_allows_non_identity_words() -> None:
    module = _runner_module()

    assert module._matrix_label_contains_raw_identity("amendment-restatement") is False
    assert module._matrix_label_contains_raw_identity("issuer-T") is True
    assert module._matrix_label_contains_raw_identity("core-MSFT") is True
    assert module._matrix_label_contains_raw_identity("issuer.T") is True
    assert module._matrix_label_contains_raw_identity("core.MSFT") is True


def test_sec_xbrl_real_corpus_product_runner_blocks_onedrive_arelle_python(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    one_drive_python = tmp_path / "OneDrive - Contoso" / "tools" / "python.exe"
    one_drive_python.parent.mkdir(parents=True)
    one_drive_python.write_text("", encoding="utf-8")
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(one_drive_python))

    result = module._arelle_python_preflight()

    assert result["configured"] is False
    assert result["inside_repo_or_onedrive"] is True


def test_sec_xbrl_real_corpus_product_runner_blocks_non_object_plan_json(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    plan_path = tmp_path / "plan.json"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    plan_path.write_text(json.dumps(["not-an-object"]), encoding="utf-8")
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))

    report = module.build_report(
        live=True,
        matrix_plan_path=plan_path,
        user_agent="Layer3 diagnostics contact@example.com",
    )

    assert report["live_sec_network_used"] is False
    assert report["matrix_execution_plan"]["state"] == "blocked"
    assert report["matrix_execution_plan"]["plan_top_level_type"] == "list"
    assert "matrix_plan_top_level_not_object" in report["matrix_execution_plan"]["blocked_reasons"]


def test_sec_xbrl_real_corpus_product_runner_requires_ready_external_strata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))

    plan = _stratified_plan()

    def blocked_run_matrix_chunk(label, matrix, *, strata, db, request_namespace, user_agent):
        del db, request_namespace, user_agent
        ready = "no_inline_or_zero_fact_diagnostic" not in strata
        return {
            "matrix_label": label,
            "matrix_ref_hash": module.stable_hash({"matrix": list(matrix)})[:24],
            "strata": list(strata),
            "pipeline_state": "ready" if ready else "blocked",
            "filing_count": 5,
            "supported_count": 5 if ready else 0,
            "blocked_or_degraded_count": 0 if ready else 5,
            "forms": {"10-K": 5},
            "issuer_hash_count": 4,
            "records_with_arelle_sidecar_output": 5 if ready else 0,
            "records_with_selected_fact_authority_equal_to_sidecar": 5 if ready else 0,
            "records_with_handoff_export_prepare": 5 if ready else 0,
            "resolved_fact_count": 500 if ready else 0,
            "independent_inline_fact_count": 500 if ready else 0,
            "per_filing": [],
            "operator_surface_values_exposed": False,
            "blocked_reasons": [] if ready else ["synthetic_stratum_blocked"],
        }

    monkeypatch.setattr(module, "_run_matrix_chunk", blocked_run_matrix_chunk)

    report = module.build_report(
        live=True,
        storage_dir=tmp_path,
        matrix_plan=plan,
        user_agent="Layer3 diagnostics contact@example.com",
    )

    reasons = {item["reason"] for item in report["blocking_reasons"]}
    assert "stratified_matrix_required_strata_not_ready" in reasons
    assert "no_inline_or_zero_fact_diagnostic" in report["summary"]["strata_readiness"]["blocked_strata"]


def test_sec_xbrl_real_corpus_product_runner_rolls_default_decision_false_on_failed_gate(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _runner_module()
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))

    row = {
        "matrix_label": "core",
        "matrix_ref_hash": "a" * 24,
        "pipeline_state": "ready",
        "filing_count": 30,
        "supported_count": 30,
        "blocked_or_degraded_count": 0,
        "forms": {"10-K": 10, "10-Q": 10, "20-F": 2, "40-F": 2, "6-K": 3, "8-K": 3},
        "issuer_hash_count": 15,
        "records_with_arelle_sidecar_output": 30,
        "records_with_selected_fact_authority_equal_to_sidecar": 30,
        "records_with_handoff_export_prepare": 30,
        "resolved_fact_count": 3000,
        "independent_inline_fact_count": 3000,
        "per_filing": [
            {
                "fixture_hash": f"{index:024x}"[-24:],
                "form": "10-K",
                "issuer_by_hash": f"{index:024x}"[-24:],
                "record_state": "supported",
                "zero_fact_status": "not_zero",
                "arelle_resolved_fact_count": 100,
                "independent_inline_fact_count": 100,
                "completeness_guard": "passed",
                "companyfacts_oracle_used": True,
                "companyfacts_effective_value_match_count": 90,
                "companyfacts_effective_value_compared_count": 100,
                "companyfacts_effective_value_mismatch_count": 10,
            }
            for index in range(30)
        ],
        "delivery_status": "not_required_for_broader_extraction_gate",
        "operator_inspection_status": "not_required_for_broader_extraction_gate",
        "operator_product_surface_status": "not_required_for_broader_extraction_gate",
        "durable_delivery_archive_status": "not_required_for_broader_extraction_gate",
        "operator_surface_values_exposed": False,
    }

    report = module.build_report(
        live=True,
        storage_dir=tmp_path,
        user_agent="Layer3 diagnostics contact@example.com",
        runner=lambda _storage, _agent, _namespace, _taxonomy: [row],
    )

    assert report["decision"] == "real_corpus_default_on_blocked"
    assert report["runtime_default_decision"]["resulting_default_enabled"] is False
    reasons = {item["reason"] for item in report["blocking_reasons"]}
    assert "companyfacts_effective_value_correctness_not_proven_on_broader_corpus" in reasons


def test_sec_xbrl_real_corpus_product_runner_reads_independent_tally_from_sidecar_diagnostics(monkeypatch) -> None:
    module = _runner_module()
    observed_identity = {}
    monkeypatch.setattr(module, "_connector_receipt", lambda _validation: {})
    monkeypatch.setattr(
        module,
        "_source_identities_for_validation",
        lambda *_args, **_kwargs: {
            "example-1": {"cik_or_filer_ref": "123456", "accession_or_submission_id": "0000123456-26-000001"}
        },
    )

    def companyfacts_count(**kwargs):
        observed_identity.update(kwargs)
        return {"oracle_used": True, "confidence": "primary_companyfacts_standard_taxonomy_accession_scope", "fact_count": 2}

    monkeypatch.setattr(module, "_companyfacts_count", companyfacts_count)
    monkeypatch.setattr(module, "_companyfacts_value_match", lambda **_kwargs: {"match_count": None, "compared_count": 0, "match_rate": None})
    monkeypatch.setattr(
        module,
        "_sidecar_receipt_by_hash",
        lambda _hash: {
            "resolved_fact_count": 12,
            "coverage": {"resolved_fact_count": 12},
            "diagnostics": {
                "independent_inline_fact_count": 12,
                "independent_inline_fact_count_reconciled": True,
                "independent_inline_fact_document_count": 2,
                "independent_inline_fact_scanned_document_count": 3,
                "independent_inline_fact_document_tally": [
                    {"document_index": 1, "inline_fact_count": 5},
                    {"document_index": 2, "inline_fact_count": 7},
                ],
                "taxonomy_package_count": 7,
                "taxonomy_package_invalid_count": 6,
                "taxonomy_package_invalid_hashes": ["1" * 64],
            },
        },
    )
    validation = {
        "filing_validation_records": [
            {
                "example_id": "example-1",
                "record_hash": "a" * 64,
                "form_type": "10-K",
                "cik_hash": "b" * 64,
                "supported_degraded_blocked": "supported",
                "quality_evidence": {
                    "quality_metrics": {
                        "arelle_sidecar_receipt_hash": "c" * 64,
                        "resolved_fact_count": 12,
                    }
                },
            }
        ]
    }

    row = module._per_filing_projection(validation, user_agent="Layer3 diagnostics contact@example.com")[0]

    assert row["independent_inline_fact_count"] == 12
    assert row["completeness_guard"] == "passed"
    assert row["multi_document_inline_document_count"] == 2
    assert row["multi_document_scanned_document_count"] == 3
    assert row["taxonomy_package_invalid_count"] == 6
    assert row["companyfacts_oracle_used"] is True
    assert observed_identity["cik"] == "123456"
    assert observed_identity["accession"] == "0000123456-26-000001"


def _resolved_fact(
    fact_id: str,
    *,
    local_name: str,
    period: dict,
    unit: dict | None = None,
    decimals: str = "0",
) -> dict:
    return {
        "resolved_fact_id": fact_id,
        "concept": {
            "namespace": "xbrl.ifrs.org/test",
            "local_name": local_name,
            "standard": True,
        },
        "unit": unit or {"currency": "iso4217:USD", "measures": ["iso4217:USD"]},
        "period": period,
        "dimensions": {"explicit": [], "typed": []},
        "decimals": decimals,
    }


def test_sec_xbrl_real_corpus_product_runner_allows_delivery_block_for_no_inline_records() -> None:
    module = _runner_module()

    assert module._delivery_block_allowed_for_no_inline_records(
        {
            "supported_unblocked_or_no_inline_count": 8,
            "filing_count": 8,
            "records_with_handoff_export_prepare": 6,
            "supported_count": 6,
            "blocked_or_degraded_count": 2,
            "failure_reasons": {
                "sec_edgar_html_inline_xbrl_fact_authority_no_inline_xbrl_markers": 2,
            },
        },
        ["sec_edgar_delivery_status_provenance_missing_handoff_export_prepare_output"],
    )


def test_sec_xbrl_real_corpus_product_runner_default_action_reflects_gate_effect() -> None:
    module = _runner_module()

    assert module._runtime_default_action(pass_gate=True, current_default=False) == "set_default_true"
    assert module._runtime_default_action(pass_gate=True, current_default=True) == "keep_default_true"
    assert module._runtime_default_action(pass_gate=False, current_default=True) == "roll_back_default_false"
    assert module._runtime_default_action(pass_gate=False, current_default=False) == "keep_default_false"


def test_sec_xbrl_real_corpus_product_runner_displays_external_output_without_path(
    tmp_path: Path,
) -> None:
    module = _runner_module()

    external_output = tmp_path / "product-runner-report.json"
    assert module._display_output_path(external_output) == "<external>/product-runner-report.json"


def _stratified_plan() -> dict:
    matrices = [
        list(matrix)
        for _label, matrix in _runner_module().MATRIX_CHUNKS
    ]
    return {
        "schema_id": "diagnostics.sec_xbrl_stratified_real_filing_validation_matrix_plan.v1",
        "matrix_mode": "sec_edgar_stratified_real_filing_validation_matrix_v1",
        "chunks": [
            _plan_chunk("large-domestic", matrices[3][:2], ["large_domestic_us_gaap"]),
            _plan_chunk("small-mid-domestic", matrices[0][1:2] + matrices[1][3:], ["small_mid_domestic_us_gaap"]),
            _plan_chunk(
                "foreign-annual-current",
                matrices[0][2:],
                ["foreign_private_ifrs_20f", "canadian_40f", "foreign_6k_sparse"],
            ),
            _plan_chunk("sparse-8k", matrices[1][:2], ["current_report_8k_sparse"]),
            _plan_chunk("amendment", matrices[2][:2], ["amendment_restatement"]),
            _plan_chunk("no-inline", matrices[2][2:] + matrices[3][2:], ["no_inline_or_zero_fact_diagnostic"]),
        ],
    }


def _redacted_product_report_fixture(module, monkeypatch, tmp_path: Path) -> tuple[Path, dict, dict]:
    arelle_python = tmp_path / "arelle-python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "arelle-cache"
    arelle_python.write_text("", encoding="utf-8")
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    monkeypatch.setenv("SEC_XBRL_ARELLE_PYTHON", str(arelle_python))
    monkeypatch.setenv("SEC_XBRL_ARELLE_TAXONOMY_PACKAGES", str(taxonomy_package))
    monkeypatch.setenv("SEC_XBRL_ARELLE_CACHE_DIR", str(cache_dir))
    plan = _stratified_plan()
    storage = _offline_sector_family_storage(tmp_path, storage_dir=tmp_path / "offline-storage")
    observed: list[tuple[str, tuple[str, ...]]] = []
    forms = ["10-K", "10-Q", "20-F", "40-F", "8-K", "6-K", "10-K/A", "10-Q/A"]

    def fake_run_matrix_chunk(label, matrix, *, strata, db, request_namespace, user_agent):
        del db, request_namespace, user_agent
        observed.append((label, tuple(strata)))
        start = len(observed) * 100
        return {
            "matrix_label": label,
            "matrix_ref_hash": module.stable_hash({"matrix": list(matrix)})[:24],
            "strata": list(strata),
            "pipeline_state": "ready",
            "filing_count": 5,
            "supported_count": 5,
            "blocked_or_degraded_count": 0,
            "forms": {forms[(len(observed) - 1) % len(forms)]: 5},
            "issuer_hash_count": 4,
            "records_with_arelle_sidecar_output": 5,
            "records_with_selected_fact_authority_equal_to_sidecar": 5,
            "records_with_handoff_export_prepare": 5,
            "resolved_fact_count": 500,
            "independent_inline_fact_count": 500,
            "per_filing": [
                {
                    "fixture_hash": f"{start + index:024x}"[-24:],
                    "form": forms[(len(observed) + index - 1) % len(forms)],
                    "issuer_by_hash": f"{start + index:024x}"[-24:],
                    "record_state": "supported",
                    "zero_fact_status": "not_zero",
                    "arelle_resolved_fact_count": 100,
                    "independent_inline_fact_count": 100,
                    "completeness_guard": "passed",
                    "companyfacts_oracle_used": True,
                    "companyfacts_effective_value_match_count": 100,
                    "companyfacts_effective_value_compared_count": 100,
                    "companyfacts_effective_value_mismatch_count": 0,
                }
                for index in range(5)
            ],
            "delivery_status": "not_required_for_broader_extraction_gate",
            "operator_inspection_status": "not_required_for_broader_extraction_gate",
            "operator_product_surface_status": "not_required_for_broader_extraction_gate",
            "durable_delivery_archive_status": "not_required_for_broader_extraction_gate",
            "operator_surface_values_exposed": False,
        }

    monkeypatch.setattr(module, "_run_matrix_chunk", fake_run_matrix_chunk)
    report = module.build_report(
        live=True,
        storage_dir=storage,
        sector_family_storage_dir=storage,
        matrix_plan=plan,
        user_agent="redacted operator test agent",
    )
    assert report["decision"] == "real_corpus_default_on_validated"
    return storage, plan, report


def _plan_chunk(matrix_label: str, company_matrix: list[str], strata: list[str]) -> dict:
    return {
        "matrix_label": matrix_label,
        "company_matrix": company_matrix,
        "strata": strata,
    }


def _offline_sector_family_storage(
    tmp_path: Path,
    *,
    storage_dir: Path | None = None,
    bank_qnames: list[str] | None = None,
    insurer_qnames: list[str] | None = None,
    sidecar_metadata_valid: bool = True,
    sidecar_receipt_shape_valid: bool = True,
    sidecar_inventory_valid: bool = True,
    sidecar_hash_basis_valid: bool = True,
    sidecar_projection_present: bool = True,
    connector_receipt_valid: bool = True,
    nested_acquisition_valid: bool = True,
    split_insurer_sidecars: bool = False,
    shared_bank_insurer_source: bool = False,
    sidecar_raw_values: bool = False,
    sidecar_standard_concepts: bool = True,
    sidecar_dimensional_facts: bool = False,
) -> Path:
    storage = storage_dir or tmp_path / "offline-storage"
    connector_dir = storage / "layer3-sec-edgar-real-filing-acquisition-connector" / "receipts"
    sidecar_dir = storage / "layer3-sec-edgar-arelle-resolved-fact-authority" / "receipts"
    connector_dir.mkdir(parents=True)
    sidecar_dir.mkdir(parents=True)
    if shared_bank_insurer_source:
        examples = [_offline_example("shared-bank-insurer-example", ["financial_institution", "insurance"])]
        acquisitions = [
            _offline_acquisition(
                examples[0],
                live_hash="4" * 64,
                content_hash="6" * 64,
                nested_valid=nested_acquisition_valid,
            )
        ]
        bank_hash = acquisitions[0]["source_artifact_receipt"]["source_artifact_receipt_hash"]
        insurer_hash = bank_hash
    else:
        examples = [
            _offline_example("bank-example", "financial_institution"),
            _offline_example("insurer-example", "insurance"),
        ]
        acquisitions = [
            _offline_acquisition(
                examples[0],
                live_hash="4" * 64,
                content_hash="6" * 64,
                nested_valid=nested_acquisition_valid,
            ),
            _offline_acquisition(
                examples[1],
                live_hash="5" * 64,
                content_hash="7" * 64,
                nested_valid=nested_acquisition_valid,
            ),
        ]
        bank_hash = acquisitions[0]["source_artifact_receipt"]["source_artifact_receipt_hash"]
        insurer_hash = acquisitions[1]["source_artifact_receipt"]["source_artifact_receipt_hash"]
    connector = _offline_connector_receipt(
        examples=examples,
        acquisitions=acquisitions,
        receipt_valid=connector_receipt_valid,
    )
    (connector_dir / "connector.json").write_text(json.dumps(connector), encoding="utf-8")
    _write_sidecar(
        sidecar_dir / "bank-sidecar.json",
        bank_hash,
        bank_qnames
        or (
            [
                "us-gaap:Deposits",
                "us-gaap:PremiumsEarnedNet",
                "us-gaap:LiabilityForClaimsAndClaimsAdjustmentExpense",
            ]
            if shared_bank_insurer_source
            else ["us-gaap:Deposits"]
        ),
        metadata_valid=sidecar_metadata_valid,
        receipt_shape_valid=sidecar_receipt_shape_valid,
        inventory_valid=sidecar_inventory_valid,
        hash_basis_valid=sidecar_hash_basis_valid,
        projection_present=sidecar_projection_present,
        raw_values=sidecar_raw_values,
        standard_concepts=sidecar_standard_concepts,
        dimensional_facts=sidecar_dimensional_facts,
    )
    if not shared_bank_insurer_source:
        if split_insurer_sidecars:
            _write_sidecar(
                sidecar_dir / "insurer-sidecar-premiums.json",
                insurer_hash,
                ["us-gaap:PremiumsEarnedNet"],
                metadata_valid=sidecar_metadata_valid,
                receipt_shape_valid=sidecar_receipt_shape_valid,
                inventory_valid=sidecar_inventory_valid,
                hash_basis_valid=sidecar_hash_basis_valid,
                projection_present=sidecar_projection_present,
                raw_values=sidecar_raw_values,
                standard_concepts=sidecar_standard_concepts,
                dimensional_facts=sidecar_dimensional_facts,
            )
            _write_sidecar(
                sidecar_dir / "insurer-sidecar-claims.json",
                insurer_hash,
                ["us-gaap:LiabilityForClaimsAndClaimsAdjustmentExpense"],
                metadata_valid=sidecar_metadata_valid,
                receipt_shape_valid=sidecar_receipt_shape_valid,
                inventory_valid=sidecar_inventory_valid,
                hash_basis_valid=sidecar_hash_basis_valid,
                projection_present=sidecar_projection_present,
                raw_values=sidecar_raw_values,
                standard_concepts=sidecar_standard_concepts,
                dimensional_facts=sidecar_dimensional_facts,
            )
        else:
            _write_sidecar(
                sidecar_dir / "insurer-sidecar.json",
                insurer_hash,
                insurer_qnames
                or [
                    "us-gaap:PremiumsEarnedNet",
                    "us-gaap:LiabilityForClaimsAndClaimsAdjustmentExpense",
                ],
                metadata_valid=sidecar_metadata_valid,
                receipt_shape_valid=sidecar_receipt_shape_valid,
                inventory_valid=sidecar_inventory_valid,
                hash_basis_valid=sidecar_hash_basis_valid,
                projection_present=sidecar_projection_present,
                raw_values=sidecar_raw_values,
                standard_concepts=sidecar_standard_concepts,
                dimensional_facts=sidecar_dimensional_facts,
            )
    return storage


def _offline_connector_receipt(
    *,
    examples: list[dict],
    acquisitions: list[dict],
    receipt_valid: bool,
) -> dict:
    diagnostics = {
        "html_inline_xbrl_explicitly_classified": False,
        "generic_text_downgrade_performed": False,
        "full_sec_support_claimed": False,
        "unsupported_or_degraded_requires_future_parser_slice": True,
    }
    source_family_inventory = {
        "source_family": "sec_edgar",
        "example_count": len(examples),
        "role_counts": {},
        "complete_submission_text_examples": 0,
    }
    example_set_hash = "a" * 64
    basis = {
        "hash_version": "sec_edgar_real_filing_acquisition_connector_receipt_hash_v1",
        "schema_id": "layer3.sec_edgar_real_filing_acquisition_connector.v1",
        "schema_version": 1,
        "connector_mode": "sec_edgar_real_filing_acquisition_connector_v1",
        "operator_decision": "acquire_sec_edgar_real_filing_validation_corpus",
        "example_set_hash": example_set_hash,
        "sec_user_agent_hash": "d" * 64,
        "source_family_inventory_hash": stable_hash(source_family_inventory),
        "acquisition_receipt_hashes": [
            str(item["live_source_artifact_receipt_hash"])
            for item in acquisitions
        ],
        "artifact_hashes": [
            str(item["source_artifact_receipt"]["content_sha256"])
            for item in acquisitions
        ],
        "classification_hashes": [stable_hash(item) for item in examples],
        "diagnostics_hash": stable_hash(diagnostics),
    }
    connector_hash = stable_hash(basis)
    if not receipt_valid:
        basis = {**basis, "diagnostics_hash": "0" * 64}
    return {
        "schema_id": "layer3.sec_edgar_real_filing_acquisition_connector.v1",
        "schema_version": 1,
        "connector_mode": "sec_edgar_real_filing_acquisition_connector_v1",
        "operator_decision": "acquire_sec_edgar_real_filing_validation_corpus",
        "connector_receipt_id": (
            f"sec-edgar-real-filing-acquisition-connector-{example_set_hash[:24]}-{connector_hash[:24]}"
        ),
        "connector_receipt_hash": connector_hash,
        "connector_state": "available",
        "example_set": {
            "example_set_hash": example_set_hash,
        },
        "corpus_manifest": {
            "schema_id": "layer3.sec_edgar_real_filing_validation_corpus_manifest.v1",
            "schema_version": 1,
            "example_count": len(examples),
            "example_records": examples,
            "source_family_inventory": source_family_inventory,
            "manifest_hash": stable_hash(
                {
                    "examples": examples,
                    "acquisition_receipts": acquisitions,
                    "diagnostics": diagnostics,
                }
            ),
        },
        "acquisition_receipts": acquisitions,
        "diagnostics": diagnostics,
        "receipt_hash_basis": basis,
    }


def _offline_example(example_id: str, class_tags: str | list[str]) -> dict:
    tags = [class_tags] if isinstance(class_tags, str) else list(class_tags)
    return {
        "example_id": example_id,
        "cik_hash": stable_hash({"fixture_cik": example_id}),
        "accession_or_submission_id_hash": stable_hash({"fixture_accession": example_id}),
        "form_type": "10-K",
        "filing_date": "2026-01-31",
        "issuer_profile_tags": tags + ["domestic_large_cap", "annual_form_family"],
        "primary_document_family": "inline_xbrl",
        "source_family": "complete_submission_text",
        "source_family_roles": ["complete_submission_text", "html_inline_xbrl"],
        "expected_support_status": "supported",
        "selection_policy": "explicit_form_types_v1",
        "parser_family": "sec_edgar_filing",
        "parser_contract_id": "aps_sec_edgar_filing_parser_v1",
        "artifact_role_set": ["complete_submission_text"],
        "diagnostics": {},
    }


def _offline_acquisition(
    example: dict,
    *,
    live_hash: str,
    content_hash: str,
    nested_valid: bool = True,
) -> dict:
    artifact_ref_hash = stable_hash({"fixture_artifact_ref": example["example_id"]})
    content_length = 1000 + len(str(example["example_id"]))
    source_receipt_id = f"sec-edgar-text-table-source-artifact-{artifact_ref_hash[:24]}"
    source_hash = stable_hash(
        {
            "schema_id": "layer3.sec_edgar_text_table_source_artifact_receipt.v1",
            "schema_version": 1,
            "source_artifact_receipt_id": source_receipt_id,
            "source_artifact_ref_hash": artifact_ref_hash,
            "content_sha256": content_hash,
            "content_length": content_length,
            "accession_or_submission_id_hash": example["accession_or_submission_id_hash"],
            "cik_or_filer_ref_hash": example["cik_hash"],
            "form_type": example["form_type"],
            "filing_date": example["filing_date"],
            "parser_family": "sec_edgar_filing",
            "parser_contract_id": "aps_sec_edgar_filing_parser_v1",
            "typed_content_contract_id": "aps_sec_edgar_filing_units_v1",
            "source_mode": "artifact_sec_edgar_filing_parser",
        }
    )
    if not nested_valid:
        source_hash = "f" * 64
    source_identity_hash = stable_hash(
        {
            "hash_version": "sec_edgar_live_source_identity_hash_v1",
            "cik_or_filer_ref_hash": example["cik_hash"],
            "accession_or_submission_id_hash": example["accession_or_submission_id_hash"],
            "form_type": example["form_type"],
            "filing_date": example["filing_date"],
        }
    )
    return {
        "example_id": example["example_id"],
        "live_source_artifact_receipt_id": (
            f"sec-edgar-text-table-live-source-artifact-{source_identity_hash[:24]}-{live_hash[:24]}"
        ),
        "live_source_artifact_receipt_hash": live_hash,
        "live_source_artifact_receipt_status": "available",
        "source_artifact_receipt": {
            "schema_id": "layer3.sec_edgar_text_table_source_artifact_receipt.v1",
            "schema_version": 1,
            "source_artifact_receipt_id": source_receipt_id,
            "source_artifact_receipt_hash": source_hash,
            "source_artifact_ref_hash": artifact_ref_hash,
            "content_sha256": content_hash,
            "content_length": content_length,
            "parser_family": "sec_edgar_filing",
            "parser_contract_id": "aps_sec_edgar_filing_parser_v1",
            "typed_content_contract_id": "aps_sec_edgar_filing_units_v1",
            "source_mode": "artifact_sec_edgar_filing_parser",
            "server_owned_source_artifact_authority": True,
            "raw_source_artifact_ref_exposed": False,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
        "retained_source_artifact_manifest": {
            "source_artifact_family": "complete_submission_text_filing_artifact",
            "artifact_ref_hash": artifact_ref_hash,
            "content_sha256": content_hash,
            "content_length": content_length,
            "retained_source_artifact_available": True,
            "raw_local_path_exposed": False,
            "raw_url_exposed": False,
            "artifact_bytes_exposed": False,
        },
    }


def _write_sidecar(
    path: Path,
    source_hash: str,
    qnames: list[str],
    *,
    metadata_valid: bool = True,
    receipt_shape_valid: bool = True,
    inventory_valid: bool = True,
    hash_basis_valid: bool = True,
    projection_present: bool = True,
    raw_values: bool = False,
    standard_concepts: bool = True,
    dimensional_facts: bool = False,
) -> None:
    records = []
    for index, qname in enumerate(qnames, start=1):
        record = {
            "concept": {"qname": qname, "standard": standard_concepts},
            "dimensions": {
                "explicit": [{"axis": "fixture:Axis", "member": "fixture:Member"}] if dimensional_facts else [],
                "typed": [],
            },
            "resolved_fact_id": f"fact-{index}",
            "value_hash": stable_hash({"source_hash": source_hash, "qname": qname, "index": index}),
        }
        if raw_values:
            record["value"] = "123.45"
        records.append(record)
    projection = [_redacted_sidecar_record(record) for record in records]
    if receipt_shape_valid:
        inventory_hash = stable_hash(projection) if inventory_valid else "0" * 64
        local_value_inventory_hash = stable_hash([record["value_hash"] for record in projection])
        diagnostics = {"adapter_execution": "isolated_subprocess_cli", "test_fixture": True}
        parity = {
            "arelle_resolved_fact_count": len(records),
            "regex_fact_authority_count": len(records),
        }
        diagnostics_hash = stable_hash(diagnostics)
        sidecar_hash = stable_hash(
            {
                "hash_version": "sec_edgar_arelle_resolved_fact_authority_sidecar_hash_v1",
                "sidecar_mode": "sec_edgar_arelle_resolved_fact_authority_sidecar_v1",
                "adapter_version": "arelle_resolved_fact_authority_adapter:arelle-release==2.41.3",
                "parser_receipt_hash": "1" * 64,
                "connector_receipt_hash": "2" * 64,
                "live_source_artifact_receipt_hash": "3" * 64,
                "source_artifact_receipt_hash": source_hash,
                "content_sha256": "4" * 64,
                "primary_document_hash": "5" * 64,
                "document_inventory_hash": "6" * 64,
                "content_order_hash": "7" * 64,
                "table_candidate_inventory_hash": "8" * 64,
                "inline_xbrl_marker_inventory_hash": "9" * 64,
                "resolved_fact_inventory_hash": inventory_hash,
                "local_value_inventory_hash": local_value_inventory_hash,
                "internal_value_store_enabled": False,
                "internal_value_store_hash": None,
                "diagnostics_hash": diagnostics_hash,
                "parity_hash": stable_hash(parity),
            }
        )
        if not hash_basis_valid:
            sidecar_hash = "f" * 64
    else:
        sidecar_hash = f"{source_hash}-sidecar"
        inventory_hash = f"{source_hash}-inventory"
        local_value_inventory_hash = f"{source_hash}-local-values"
        diagnostics = {}
        parity = {}
        diagnostics_hash = f"{source_hash}-diagnostics"
    payload = {
        "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_sidecar.v1",
        "schema_version": 1,
        "sidecar_mode": "sec_edgar_arelle_resolved_fact_authority_sidecar_v1",
        "operator_decision": "derive_sec_edgar_arelle_resolved_fact_authority_sidecar",
        "source_artifact_receipt_hash": source_hash,
        "resolved_fact_records": records,
        "resolved_fact_count": len(records),
        "local_value_inventory_hash": local_value_inventory_hash,
        "internal_value_store": {
            "schema_id": "layer3.sec_edgar_arelle_resolved_fact_authority_internal_value_store.v1",
            "store_state": "not_created_internal_value_store_flag_off",
            "creation_gated_by_internal_value_store_flag": True,
            "consumption_gated_by_internal_value_store_flag": True,
            "value_record_count": 0,
            "values_exposed_in_status_projection": False,
            "retention_policy": "not_created_without_internal_value_store_flag",
        },
        "diagnostics": diagnostics,
        "diagnostics_hash": diagnostics_hash,
        "parity": parity,
    }
    if projection_present:
        payload["resolved_fact_projection"] = projection
    if metadata_valid:
        payload.update(
            {
                "adapter_id": "arelle_resolved_fact_authority_adapter",
                "adapter_version": "arelle_resolved_fact_authority_adapter:arelle-release==2.41.3",
                "parser_receipt_hash": "1" * 64,
                "connector_receipt_hash": "2" * 64,
                "live_source_artifact_receipt_hash": "3" * 64,
                "content_sha256": "4" * 64,
                "primary_document_hash": "5" * 64,
                "document_inventory_hash": "6" * 64,
                "content_order_hash": "7" * 64,
                "table_candidate_inventory_hash": "8" * 64,
                "inline_xbrl_marker_inventory_hash": "9" * 64,
                "resolved_fact_inventory_hash": inventory_hash,
                "sidecar_receipt_id": f"sec-edgar-arelle-resolved-fact-authority-{sidecar_hash[:24]}",
                "sidecar_receipt_hash": sidecar_hash,
                "sidecar_receipt_ref": f"sec-edgar-arelle-resolved-fact-authority:{sidecar_hash[:24]}",
                "sidecar_state": "sec_edgar_arelle_resolved_fact_authority_sidecar_ready",
                "authority_hashes": {
                    "parser_receipt_hash": "1" * 64,
                    "connector_receipt_hash": "2" * 64,
                    "live_source_artifact_receipt_hash": "3" * 64,
                    "content_sha256": "4" * 64,
                    "primary_document_hash": "5" * 64,
                    "document_inventory_hash": "6" * 64,
                    "content_order_hash": "7" * 64,
                    "table_candidate_inventory_hash": "8" * 64,
                    "inline_xbrl_marker_inventory_hash": "9" * 64,
                    "resolved_fact_inventory_hash": inventory_hash,
                    "local_value_inventory_hash": local_value_inventory_hash,
                    "diagnostics_hash": diagnostics_hash,
                    "source_artifact_receipt_hash": source_hash,
                    "sidecar_receipt_hash": sidecar_hash,
                },
            }
        )
    path.write_text(json.dumps(payload), encoding="utf-8")


def _redacted_sidecar_record(record: dict) -> dict:
    return {
        key: value
        for key, value in record.items()
        if key not in {"value", "effective_value", "lexical_value"}
    } | {"value_redacted": True}


def _projection_bundle(module) -> dict:
    value_records = [
        _projection_value("rf-period-end", "end-2"),
        _projection_value("rf-assets", "200"),
        _projection_value("rf-gross-loan-commitments", "900"),
    ]
    return {
        "issuer_ref": "redacted-sector-family-row-shape-reference",
        "companyfacts": {},
        "sidecar_records": [
            _projection_record("rf-period-end", "dei", "DocumentPeriodEndDate", "unitless", instant=True),
            _projection_record("rf-assets", "ifrs-full", "Assets", "USD", instant=True),
            _projection_record(
                "rf-gross-loan-commitments",
                "ifrs-full",
                "GrossLoanCommitments",
                "USD",
                instant=True,
            ),
        ],
        "value_records": value_records,
        "sidecar_receipt_id": "sidecar-ref",
        "sidecar_receipt_hash": "sidecar-hash",
        "value_store_hash": module.stable_hash(value_records),
        "dataset_version_id": "dataset-ref",
    }


def _projection_record(
    fact_id: str,
    taxonomy: str,
    local_name: str,
    unit_name: str,
    *,
    instant: bool = False,
) -> dict:
    return {
        "resolved_fact_id": fact_id,
        "concept": {
            "namespace": _projection_namespace(taxonomy),
            "local_name": local_name,
            "standard": True,
        },
        "unit": _projection_unit(unit_name),
        "period": {"type": "instant", "instant": "end-2"}
        if instant
        else {"type": "duration", "start": "start-2", "end": "end-2"},
        "dimensions": {"explicit": [], "typed": []},
    }


def _projection_value(fact_id: str, effective_value: str) -> dict:
    return {"resolved_fact_id": fact_id, "effective_value": effective_value}


def _projection_namespace(taxonomy: str) -> str:
    if taxonomy == "ifrs-full":
        return "xbrl.ifrs.org/test"
    if taxonomy == "dei":
        return "xbrl.sec.gov/dei/test"
    return "fasb.org/us-gaap/test"


def _projection_unit(unit_name: str) -> dict:
    if unit_name == "unitless":
        return {"measures": []}
    return {"currency": f"iso4217:{unit_name}", "measures": [f"iso4217:{unit_name}"]}
