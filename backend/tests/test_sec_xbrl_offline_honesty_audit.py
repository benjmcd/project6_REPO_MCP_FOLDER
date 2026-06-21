from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "scripts" / "sec_xbrl_offline_honesty_audit.py"
MATRIX_PATH = ROOT / "config" / "support_matrix.yaml"
RELEASE_PATH = ROOT / "config" / "release_readiness.yaml"


def _audit_module() -> Any:
    spec = importlib.util.spec_from_file_location("sec_xbrl_offline_honesty_audit", AUDIT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sec_xbrl_offline_honesty_audit_reports_clean_pass(capsys) -> None:
    module = _audit_module()

    report = module.build_report(repo_root=ROOT)
    assert report["schema_id"] == module.REPORT_SCHEMA_ID
    assert report["status"] == "pass"
    assert report["errors"] == []
    assert {item["status"] for item in report["criteria"]} == {"pass"}

    assert module.main(["--repo-root", str(ROOT), "--matrix", str(MATRIX_PATH)]) == 0
    emitted = json.loads(capsys.readouterr().out)
    assert emitted["status"] == "pass"


def test_sec_xbrl_offline_honesty_audit_fails_closed_on_synthetic_status_upgrade(tmp_path) -> None:
    module = _audit_module()
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    for capability in matrix["capabilities"]:
        if capability["id"] == "sec_live_network_egress":
            capability["status"] = "supported"
            break
    else:
        raise AssertionError("sec_live_network_egress capability missing from support matrix")

    mutated = tmp_path / "support_matrix.yaml"
    mutated.write_text(json.dumps(matrix, indent=2, sort_keys=True), encoding="utf-8")

    report = module.build_report(matrix_path=mutated, repo_root=ROOT)
    assert report["status"] == "fail"
    assert any(
        "sec_live_network_egress must be experimental_default_off" in error
        for error in report["errors"]
    )

    assert module.main(["--repo-root", str(ROOT), "--matrix", str(mutated)]) == 1


def test_sec_xbrl_offline_honesty_audit_fails_closed_on_pinned_flag_list_drift(tmp_path) -> None:
    module = _audit_module()
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    matrix["pinned_false_flags"] = matrix["pinned_false_flags"][:-1]

    mutated = tmp_path / "support_matrix.yaml"
    mutated.write_text(json.dumps(matrix, indent=2, sort_keys=True), encoding="utf-8")

    report = module.build_report(matrix_path=mutated, repo_root=ROOT)
    assert report["status"] == "fail"
    assert any("pinned_false_flags must match" in error for error in report["errors"])


def test_sec_xbrl_offline_honesty_audit_fails_closed_on_default_off_status_upgrade(tmp_path) -> None:
    module = _audit_module()
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    for capability in matrix["capabilities"]:
        if capability["id"] == "analysis_product_package_inventory":
            capability["status"] = "supported"
            break
    else:
        raise AssertionError("analysis_product_package_inventory capability missing from support matrix")

    mutated = tmp_path / "support_matrix.yaml"
    mutated.write_text(json.dumps(matrix, indent=2, sort_keys=True), encoding="utf-8")

    report = module.build_report(matrix_path=mutated, repo_root=ROOT)
    assert report["status"] == "fail"
    assert any("analysis_product_package_inventory must be experimental_default_off" in error for error in report["errors"])


def test_sec_xbrl_offline_honesty_audit_fails_closed_on_local_profile_default_drift() -> None:
    module = _audit_module()
    defaults = module._load_settings_defaults(ROOT)
    defaults["DATABASE_URL"] = "postgresql://user:pass@localhost/db"
    defaults["LAYER3_ROUTE_AUTHORIZATION_MODE"] = "role_required"

    report = module.build_report(repo_root=ROOT, settings_defaults=defaults)
    assert report["status"] == "fail"
    assert any("DATABASE_URL default must resolve to sqlite" in error for error in report["errors"])
    assert any("LAYER3_ROUTE_AUTHORIZATION_MODE default must be 'identity_presence'" in error for error in report["errors"])


def test_sec_xbrl_offline_honesty_audit_fails_closed_on_release_gate_drift(tmp_path) -> None:
    module = _audit_module()
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    release["owner_selected_profile_specific_gates"] = ["operator-selected-production-profile"]

    mutated = tmp_path / "release_readiness.yaml"
    mutated.write_text(json.dumps(release, indent=2, sort_keys=True), encoding="utf-8")

    report = module.build_report(release_path=mutated, repo_root=ROOT)
    assert report["status"] == "fail"
    assert any("owner_selected_profile_specific_gates must stay []" in error for error in report["errors"])


def test_sec_xbrl_offline_honesty_audit_fails_closed_on_runtime_control_truth(monkeypatch) -> None:
    module = _audit_module()
    module._ensure_import_paths(ROOT)
    from app.services import layer3_sec_xbrl_offline_evidence_loader as loader

    def bad_loader_report(_storage_dir, **_kwargs):
        return {
            "controls": {
                "source_acquisition_performed": True,
                "arelle_invoked": False,
                "network_performed": False,
                "value_reveal_performed": False,
                "api_route_enabled": False,
                "production_readiness_claimed": False,
            }
        }

    monkeypatch.setattr(loader, "inspect_sec_xbrl_offline_evidence_storage", bad_loader_report)

    report = module.build_report(repo_root=ROOT)
    assert report["status"] == "fail"
    assert any("offline_evidence_loader source_acquisition_performed control must be False" in error for error in report["errors"])
