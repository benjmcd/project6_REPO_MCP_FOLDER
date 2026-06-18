from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = (
    ROOT
    / "diagnostics"
    / "assessment"
    / "sec-xbrl-stratified-real-filing-validation-matrix-preflight.py"
)
RUNNER_PATH = ROOT / "diagnostics" / "assessment" / "sec-xbrl-real-corpus-product-runner.py"


def _preflight_module():
    spec = importlib.util.spec_from_file_location(
        "sec_xbrl_stratified_real_filing_validation_matrix_preflight",
        PREFLIGHT_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_stratified_matrix_preflight_blocks_without_grant_or_environment(
    tmp_path: Path,
) -> None:
    module = _preflight_module()
    paths = _write_inputs(tmp_path)

    report = module.build_report(
        source_root=ROOT,
        runbook_report_path=paths["runbook"],
        default_posture_report_path=paths["default_posture"],
        real_product_runner_report_path=paths["real_product"],
        env={},
    )
    blockers = {item["reason"] for item in report["blocking_reasons"]}

    assert report["decision"] == "stratified_matrix_preflight_requires_authorization_or_environment"
    assert "stratified_matrix_preflight_explicit_live_authorization_missing" in blockers
    assert "stratified_matrix_preflight_user_agent_missing" in blockers
    assert "stratified_matrix_preflight_arelle_environment_missing" in blockers
    assert "stratified_matrix_preflight_isolated_storage_missing_or_inside_repo" in blockers
    assert report["non_goals_preserved"]["sec_network_fetch_performed"] is False
    assert report["non_goals_preserved"]["arelle_subprocess_invoked"] is False
    assert report["non_goals_preserved"]["runtime_default_changed"] is False
    assert report["next_slice"] == "sec_edgar_stratified_real_filing_validation_matrix_v1"


def test_sec_xbrl_stratified_matrix_preflight_ready_with_isolated_runtime_env(
    tmp_path: Path,
) -> None:
    module = _preflight_module()
    paths = _write_inputs(tmp_path)
    env_paths = _runtime_paths(tmp_path)
    plan_path = _write_json(tmp_path / "plan.json", _external_plan())
    user_agent = "redacted operator test agent"

    report = module.build_report(
        source_root=ROOT,
        runbook_report_path=paths["runbook"],
        default_posture_report_path=paths["default_posture"],
        real_product_runner_report_path=paths["real_product"],
        env={
            "SEC_XBRL_STRATIFIED_MATRIX_LIVE_AUTHORIZED": "true",
            "SEC_XBRL_STRATIFIED_MATRIX_STORAGE_DIR": str(env_paths["storage"]),
            "SEC_XBRL_ARELLE_PYTHON": str(env_paths["python"]),
            "SEC_XBRL_ARELLE_TAXONOMY_PACKAGES": str(env_paths["taxonomy"]),
            "SEC_XBRL_ARELLE_CACHE_DIR": str(env_paths["cache"]),
            "SEC_XBRL_STRATIFIED_MATRIX_PLAN": str(plan_path),
            "SEC_XBRL_ARELLE_INTERNET_CONNECTIVITY": "online",
            "LAYER3_SEC_EDGAR_USER_AGENT": user_agent,
        },
    )
    serialized = json.dumps(report, sort_keys=True)

    assert report["decision"] == "stratified_matrix_preflight_ready_for_explicit_live_execution"
    assert report["blocking_reasons"] == []
    assert report["runtime_preflight"]["storage"]["storage_dir_inside_repo"] is False
    assert report["runtime_preflight"]["arelle"]["taxonomy_packages_all_exist"] is True
    assert str(env_paths["storage"]) not in serialized
    assert str(env_paths["python"]) not in serialized
    assert str(env_paths["taxonomy"]) not in serialized
    assert str(env_paths["cache"]) not in serialized
    assert user_agent not in serialized
    assert report["next_slice"] == "sec_edgar_stratified_real_filing_validation_matrix_live_execution_v1"


def test_sec_xbrl_stratified_matrix_preflight_blocks_without_external_plan_when_env_otherwise_ready(
    tmp_path: Path,
) -> None:
    module = _preflight_module()
    paths = _write_inputs(tmp_path)
    env_paths = _runtime_paths(tmp_path)

    report = module.build_report(
        source_root=ROOT,
        runbook_report_path=paths["runbook"],
        default_posture_report_path=paths["default_posture"],
        real_product_runner_report_path=paths["real_product"],
        env={
            "SEC_XBRL_STRATIFIED_MATRIX_LIVE_AUTHORIZED": "true",
            "SEC_XBRL_STRATIFIED_MATRIX_STORAGE_DIR": str(env_paths["storage"]),
            "SEC_XBRL_ARELLE_PYTHON": str(env_paths["python"]),
            "SEC_XBRL_ARELLE_TAXONOMY_PACKAGES": str(env_paths["taxonomy"]),
            "SEC_XBRL_ARELLE_CACHE_DIR": str(env_paths["cache"]),
            "LAYER3_SEC_EDGAR_USER_AGENT": "redacted operator test agent",
        },
    )

    assert report["decision"] == "stratified_matrix_preflight_requires_authorization_or_environment"
    assert report["runtime_preflight"]["external_matrix_plan"]["blocked_reasons"] == ["matrix_plan_missing"]
    assert any(
        item["reason"] == "stratified_matrix_preflight_external_matrix_plan_missing_or_invalid"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_preflight_rejects_repo_storage(
    tmp_path: Path,
) -> None:
    module = _preflight_module()
    paths = _write_inputs(tmp_path)
    env_paths = _runtime_paths(tmp_path)

    report = module.build_report(
        source_root=ROOT,
        runbook_report_path=paths["runbook"],
        default_posture_report_path=paths["default_posture"],
        real_product_runner_report_path=paths["real_product"],
        env={
            "SEC_XBRL_STRATIFIED_MATRIX_LIVE_AUTHORIZED": "true",
            "SEC_XBRL_STRATIFIED_MATRIX_STORAGE_DIR": str(ROOT),
            "SEC_XBRL_ARELLE_PYTHON": str(env_paths["python"]),
            "SEC_XBRL_ARELLE_TAXONOMY_PACKAGES": str(env_paths["taxonomy"]),
            "SEC_XBRL_ARELLE_CACHE_DIR": str(env_paths["cache"]),
            "LAYER3_SEC_EDGAR_USER_AGENT": "redacted operator test agent",
        },
    )

    assert report["decision"] == "stratified_matrix_preflight_requires_authorization_or_environment"
    assert any(
        item["reason"] == "stratified_matrix_preflight_isolated_storage_missing_or_inside_repo"
        for item in report["blocking_reasons"]
    )
    assert report["runtime_preflight"]["storage"]["storage_dir_inside_repo"] is True


def test_sec_xbrl_stratified_matrix_preflight_blocks_incomplete_matrix(
    tmp_path: Path,
) -> None:
    module = _preflight_module()
    paths = _write_inputs(tmp_path)
    runbook = json.loads(paths["runbook"].read_text(encoding="utf-8"))
    runbook["selected_stratified_matrix"] = [
        row
        for row in runbook["selected_stratified_matrix"]
        if row["stratum"] != "canadian_40f"
    ]
    paths["runbook"].write_text(json.dumps(runbook), encoding="utf-8")

    report = module.build_report(
        source_root=ROOT,
        runbook_report_path=paths["runbook"],
        default_posture_report_path=paths["default_posture"],
        real_product_runner_report_path=paths["real_product"],
        env={},
    )

    assert report["selected_matrix_summary"]["missing_required_strata"] == ["canadian_40f"]
    assert any(
        item["reason"] == "stratified_matrix_preflight_selected_matrix_incomplete"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_preflight_blocks_raw_identity_in_row_field(
    tmp_path: Path,
) -> None:
    module = _preflight_module()
    paths = _write_inputs(tmp_path)
    runbook = json.loads(paths["runbook"].read_text(encoding="utf-8"))
    runbook["selected_stratified_matrix"][0]["download_url"] = "https://sec.gov/Archives/edgar/data/example"
    paths["runbook"].write_text(json.dumps(runbook), encoding="utf-8")

    report = module.build_report(
        source_root=ROOT,
        runbook_report_path=paths["runbook"],
        default_posture_report_path=paths["default_posture"],
        real_product_runner_report_path=paths["real_product"],
        env={},
    )

    assert report["selected_matrix_summary"]["raw_identity_scan_passed"] is False
    assert report["selected_matrix_summary"]["raw_identity_hit_fields"] == [
        {"field": "download_url", "kinds": ["url"]}
    ]
    assert any(
        item["reason"] == "stratified_matrix_preflight_selected_matrix_incomplete"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_preflight_blocks_raw_cik_in_row_field(
    tmp_path: Path,
) -> None:
    module = _preflight_module()

    for index, cik_value in enumerate(("789019", 789019, "37996"), start=1):
        case_dir = tmp_path / f"case-{index}"
        case_dir.mkdir()
        paths = _write_inputs(case_dir)
        runbook = json.loads(paths["runbook"].read_text(encoding="utf-8"))
        runbook["selected_stratified_matrix"][0]["cik"] = cik_value
        paths["runbook"].write_text(json.dumps(runbook), encoding="utf-8")

        report = module.build_report(
            source_root=ROOT,
            runbook_report_path=paths["runbook"],
            default_posture_report_path=paths["default_posture"],
            real_product_runner_report_path=paths["real_product"],
            env={},
        )

        assert report["selected_matrix_summary"]["raw_identity_scan_passed"] is False
        assert report["selected_matrix_summary"]["raw_identity_hit_fields"] == [
            {"field": "cik", "kinds": ["cik"]}
        ]
        assert any(
            item["reason"] == "stratified_matrix_preflight_selected_matrix_incomplete"
            for item in report["blocking_reasons"]
        )


def test_sec_xbrl_stratified_matrix_preflight_blocks_repo_arelle_paths(
    tmp_path: Path,
) -> None:
    module = _preflight_module()
    paths = _write_inputs(tmp_path)
    env_paths = _runtime_paths(tmp_path)
    plan_path = _write_json(tmp_path / "plan.json", _external_plan())

    report = module.build_report(
        source_root=ROOT,
        runbook_report_path=paths["runbook"],
        default_posture_report_path=paths["default_posture"],
        real_product_runner_report_path=paths["real_product"],
        env={
            "SEC_XBRL_STRATIFIED_MATRIX_LIVE_AUTHORIZED": "true",
            "SEC_XBRL_STRATIFIED_MATRIX_STORAGE_DIR": str(env_paths["storage"]),
            "SEC_XBRL_ARELLE_PYTHON": str(ROOT / ".gitignore"),
            "SEC_XBRL_ARELLE_TAXONOMY_PACKAGES": str(env_paths["taxonomy"]),
            "SEC_XBRL_ARELLE_CACHE_DIR": str(env_paths["cache"]),
            "SEC_XBRL_STRATIFIED_MATRIX_PLAN": str(plan_path),
            "LAYER3_SEC_EDGAR_USER_AGENT": "redacted operator test agent",
        },
    )

    assert report["runtime_preflight"]["arelle"]["python_inside_repo"] is True
    assert any(
        item["reason"] == "stratified_matrix_preflight_arelle_environment_missing"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_preflight_blocks_onedrive_arelle_paths(
    tmp_path: Path,
) -> None:
    module = _preflight_module()
    paths = _write_inputs(tmp_path)
    env_paths = _runtime_paths(tmp_path)
    plan_path = _write_json(tmp_path / "plan.json", _external_plan())
    one_drive_root = tmp_path / "OneDrive - Contoso" / "arelle"
    one_drive_python = one_drive_root / "python.exe"
    one_drive_taxonomy = one_drive_root / "taxonomy.zip"
    one_drive_cache = one_drive_root / "cache"
    one_drive_root.mkdir(parents=True)
    one_drive_python.write_text("", encoding="utf-8")
    one_drive_taxonomy.write_text("", encoding="utf-8")
    one_drive_cache.mkdir()

    report = module.build_report(
        source_root=ROOT,
        runbook_report_path=paths["runbook"],
        default_posture_report_path=paths["default_posture"],
        real_product_runner_report_path=paths["real_product"],
        env={
            "SEC_XBRL_STRATIFIED_MATRIX_LIVE_AUTHORIZED": "true",
            "SEC_XBRL_STRATIFIED_MATRIX_STORAGE_DIR": str(env_paths["storage"]),
            "SEC_XBRL_ARELLE_PYTHON": str(one_drive_python),
            "SEC_XBRL_ARELLE_TAXONOMY_PACKAGES": str(one_drive_taxonomy),
            "SEC_XBRL_ARELLE_CACHE_DIR": str(one_drive_cache),
            "SEC_XBRL_STRATIFIED_MATRIX_PLAN": str(plan_path),
            "LAYER3_SEC_EDGAR_USER_AGENT": "redacted operator test agent",
        },
    )

    arelle = report["runtime_preflight"]["arelle"]
    assert report["decision"] == "stratified_matrix_preflight_requires_authorization_or_environment"
    assert arelle["python_inside_repo"] is False
    assert arelle["python_inside_repo_or_onedrive"] is True
    assert arelle["taxonomy_packages_outside_repo"] is True
    assert arelle["taxonomy_packages_outside_repo_or_onedrive"] is False
    assert arelle["cache_dir_inside_repo"] is False
    assert arelle["cache_dir_inside_repo_or_onedrive"] is True
    assert any(
        item["reason"] == "stratified_matrix_preflight_arelle_environment_missing"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_preflight_blocks_non_executable_arelle_python(
    tmp_path: Path,
) -> None:
    module = _preflight_module()
    paths = _write_inputs(tmp_path)
    env_paths = _runtime_paths(tmp_path)
    plan_path = _write_json(tmp_path / "plan.json", _external_plan())
    non_executable = tmp_path / "python.txt"
    non_executable.write_text("", encoding="utf-8")

    report = module.build_report(
        source_root=ROOT,
        runbook_report_path=paths["runbook"],
        default_posture_report_path=paths["default_posture"],
        real_product_runner_report_path=paths["real_product"],
        env={
            "SEC_XBRL_STRATIFIED_MATRIX_LIVE_AUTHORIZED": "true",
            "SEC_XBRL_STRATIFIED_MATRIX_STORAGE_DIR": str(env_paths["storage"]),
            "SEC_XBRL_ARELLE_PYTHON": str(non_executable),
            "SEC_XBRL_ARELLE_TAXONOMY_PACKAGES": str(env_paths["taxonomy"]),
            "SEC_XBRL_ARELLE_CACHE_DIR": str(env_paths["cache"]),
            "SEC_XBRL_STRATIFIED_MATRIX_PLAN": str(plan_path),
            "LAYER3_SEC_EDGAR_USER_AGENT": "redacted operator test agent",
        },
    )

    assert report["runtime_preflight"]["arelle"]["python_exists"] is True
    assert report["runtime_preflight"]["arelle"]["python_executable"] is False
    assert any(
        item["reason"] == "stratified_matrix_preflight_arelle_environment_missing"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_preflight_blocks_zero_minimum_for_required_stratum(
    tmp_path: Path,
) -> None:
    module = _preflight_module()
    paths = _write_inputs(tmp_path)
    runbook = json.loads(paths["runbook"].read_text(encoding="utf-8"))
    runbook["selected_stratified_matrix"][0]["minimum_issuer_hashes"] = 0
    runbook["selected_stratified_matrix"][1]["minimum_issuer_hashes"] = 6
    paths["runbook"].write_text(json.dumps(runbook), encoding="utf-8")

    report = module.build_report(
        source_root=ROOT,
        runbook_report_path=paths["runbook"],
        default_posture_report_path=paths["default_posture"],
        real_product_runner_report_path=paths["real_product"],
        env={},
    )

    assert report["selected_matrix_summary"]["minimum_issuer_hash_total"] == 18
    assert report["selected_matrix_summary"]["all_minimum_issuer_hashes_positive"] is False
    assert report["selected_matrix_summary"]["strata_with_non_positive_minimum_issuer_hashes"] == [
        "large_domestic_us_gaap"
    ]
    assert any(
        item["reason"] == "stratified_matrix_preflight_selected_matrix_incomplete"
        for item in report["blocking_reasons"]
    )


def test_sec_xbrl_stratified_matrix_tracking_surfaces_require_external_plan() -> None:
    progress = _read_repo_json("next_milestone_plans/layer3_progress_manifest.json")
    proof = _read_repo_json("next_milestone_plans/layer3_workbench_proof_manifest.json")
    board = (ROOT / "next_milestone_plans" / "layer3_progress_board.md").read_text(encoding="utf-8")

    preflight_tracking = progress["sec_edgar_stratified_real_filing_validation_matrix_preflight_tracking"]
    harness_tracking = progress["sec_edgar_stratified_real_filing_validation_matrix_external_plan_harness_tracking"]
    preflight_proof = proof["sec_edgar_stratified_real_filing_validation_matrix_preflight_proof"]
    harness_proof = proof["sec_edgar_stratified_real_filing_validation_matrix_external_plan_harness_proof"]

    assert preflight_tracking["external_matrix_plan_required_for_selected_tranche"] is True
    assert harness_tracking["external_matrix_plan_required_for_selected_tranche"] is True
    assert preflight_proof["external_matrix_plan_required_for_selected_tranche"] is True
    assert harness_proof["external_matrix_plan_required_for_selected_tranche"] is True
    assert "selected tranche requires an off-repo stratified matrix plan" in board
    assert "runner accepts optional off-repo stratified matrix plan" not in json.dumps(harness_proof)


def test_sec_xbrl_value_reveal_tracking_separates_superseded_reports() -> None:
    progress = _read_repo_json("next_milestone_plans/layer3_progress_manifest.json")
    proof = _read_repo_json("next_milestone_plans/layer3_workbench_proof_manifest.json")
    board = (ROOT / "next_milestone_plans" / "layer3_progress_board.md").read_text(encoding="utf-8")

    readiness_tracking = progress["sec_edgar_arelle_value_reveal_operator_exercise_tracking"]
    readiness_proof = proof["sec_edgar_arelle_value_reveal_operator_exercise_readiness_proof"]
    authority_tracking = progress["sec_edgar_arelle_value_reveal_operator_exercise_authority_provisioning_tracking"]
    authority_proof = proof["sec_edgar_arelle_value_reveal_authority_provisioning_preflight_proof"]

    for payload in (readiness_tracking, readiness_proof):
        assert payload.get("report") is None
        assert payload["superseded_readiness_report"].endswith(
            "sec-xbrl-value-reveal-operator-exercise-run-report.json"
        )
        assert payload["authoritative_proof_report"] == payload["live_proof_report"]

    for payload in (authority_tracking, authority_proof):
        assert payload.get("preflight_report") is None
        assert payload["superseded_preflight_report"].endswith(
            "sec-xbrl-value-reveal-authority-provisioning-preflight-report.json"
        )
        assert payload["authoritative_proof_report"] == payload["live_proof_report"]

    assert "Superseded readiness report" in board
    assert "Authoritative proof report" in board
    assert "remains superseded readiness evidence only" in board


def _write_inputs(tmp_path: Path) -> dict[str, Path]:
    return {
        "runbook": _write_json(tmp_path / "runbook.json", _runbook_report()),
        "default_posture": _write_json(tmp_path / "default-posture.json", _default_posture_report()),
        "real_product": _write_json(tmp_path / "real-product.json", _real_product_report()),
    }


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return path


def _read_repo_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _runtime_paths(tmp_path: Path) -> dict[str, Path]:
    arelle_python = tmp_path / "python.exe"
    taxonomy_package = tmp_path / "taxonomy.zip"
    cache_dir = tmp_path / "cache"
    storage_dir = tmp_path / "storage"
    arelle_python.write_text("", encoding="utf-8")
    # Mark the mock interpreter executable so the preflight's os.access(X_OK)
    # check passes on POSIX CI runners. On Windows any file reads as executable
    # (no execute bit), which is why the "ready" assertion only failed under CI.
    # The preflight correctly requires an executable python; this makes the
    # isolated-env mock satisfy it portably without changing what is asserted.
    arelle_python.chmod(0o755)
    taxonomy_package.write_text("", encoding="utf-8")
    cache_dir.mkdir()
    storage_dir.mkdir()
    return {
        "python": arelle_python,
        "taxonomy": taxonomy_package,
        "cache": cache_dir,
        "storage": storage_dir,
    }


def _runner_module():
    spec = importlib.util.spec_from_file_location("sec_xbrl_real_corpus_product_runner_for_preflight_tests", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runbook_report() -> dict:
    return {
        "decision": "operator_runbook_and_stratified_matrix_selection_ready",
        "next_slice": "sec_edgar_stratified_real_filing_validation_matrix_v1",
        "selected_stratified_matrix": [
            _matrix_row("large_domestic_us_gaap", ["10-K", "10-Q"], 3),
            _matrix_row("small_mid_domestic_us_gaap", ["10-K", "10-Q"], 3),
            _matrix_row("foreign_private_ifrs_20f", ["20-F"], 2),
            _matrix_row("canadian_40f", ["40-F"], 1),
            _matrix_row("current_report_8k_sparse", ["8-K"], 3),
            _matrix_row("foreign_6k_sparse", ["6-K"], 2),
            _matrix_row("amendment_restatement", ["10-K/A", "10-Q/A", "20-F/A"], 2),
            _matrix_row("no_inline_or_zero_fact_diagnostic", ["10-K", "10-Q", "8-K", "6-K"], 2),
        ],
    }


def _matrix_row(stratum: str, forms: list[str], minimum_issuer_hashes: int) -> dict:
    return {
        "stratum": stratum,
        "forms": forms,
        "minimum_issuer_hashes": minimum_issuer_hashes,
        "raw_issuer_examples_committed": False,
    }


def _default_posture_report() -> dict:
    return {
        "decision": "explicit_operator_only_default_off_selected",
        "selected_posture": {"posture": "explicit_operator_only_default_off"},
    }


def _real_product_report() -> dict:
    return {
        "decision": "real_corpus_default_on_validated",
        "gate_verdict": "PASS",
        "summary": {"supported_record_count": 30},
    }


def _external_plan() -> dict:
    matrices = [list(matrix) for _label, matrix in _runner_module().MATRIX_CHUNKS]
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
