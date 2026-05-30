from __future__ import annotations

import importlib.util
import json
from pathlib import Path


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

    report = module.build_report(
        live=True,
        storage_dir=tmp_path,
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
    assert report["runtime_default_decision"]["resulting_default_enabled"] is True
    assert report["next_slice"] == "sec_edgar_operator_surface_gated_value_reveal_v1"


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


def _plan_chunk(matrix_label: str, company_matrix: list[str], strata: list[str]) -> dict:
    return {
        "matrix_label": matrix_label,
        "company_matrix": company_matrix,
        "strata": strata,
    }
