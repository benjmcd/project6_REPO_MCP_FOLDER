from __future__ import annotations

import argparse
import ast
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from support_matrix_constants import (
    EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES as EXPERIMENTAL_DEFAULT_OFF_STATUS_CAPABILITIES,
    PINNED_FALSE_FLAGS,
    RC3_BOUNDARY_TOKENS,
    RC3_OVERLAYS,
    SEC_XBRL_ONLY_SIMULATION_CAPABILITIES as SEC_XBRL_SIMULATION_CAPABILITIES,
    UNSUPPORTED_CAPABILITIES,
)


REPORT_SCHEMA_ID = "project6.sec_xbrl_offline_honesty_audit.v1"

OFFLINE_CONTROL_FALSE_KEYS = {
    "source_acquisition_performed",
    "arelle_invoked",
    "network_performed",
    "value_reveal_performed",
    "api_route_enabled",
    "production_readiness_claimed",
}

STAGE_FALSE_KEYS = {
    "operator_surface_exposure",
    "raw_cik_exposed",
    "raw_values_exposed",
    "raw_accession_exposed",
    "raw_issuer_name_exposed",
}


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_report(
    *,
    matrix_path: Path | None = None,
    release_path: Path | None = None,
    repo_root: Path | None = None,
    settings_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = (repo_root or default_repo_root()).resolve()
    matrix_file = (matrix_path or root / "config" / "support_matrix.yaml").resolve()
    release_file = (release_path or root / "config" / "release_readiness.yaml").resolve()
    criteria: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        matrix = _load_json_object(matrix_file)
    except Exception as exc:
        matrix = {}
        _add_criterion(
            criteria,
            errors,
            "support_matrix_loads",
            False,
            f"support matrix could not be loaded: {exc}",
        )

    defaults = settings_defaults
    if defaults is None:
        try:
            defaults = _load_settings_defaults(root)
        except Exception as exc:
            defaults = {}
            _add_criterion(
                criteria,
                errors,
                "settings_defaults_load",
                False,
                f"Settings defaults could not be loaded: {exc}",
            )

    if matrix:
        _check_profile_and_boundary(matrix, criteria, errors)
        _check_capability_statuses(matrix, criteria, errors)
        _check_evidence_pointers(matrix, root, criteria, errors)
    if defaults is not None:
        _check_defaults(defaults, criteria, errors)
    try:
        release_readiness = _load_json_object(release_file)
    except Exception as exc:
        _add_criterion(
            criteria,
            errors,
            "release_readiness_profile_neutral",
            False,
            f"release readiness could not be loaded: {exc}",
        )
    else:
        _check_release_readiness(release_readiness, criteria, errors)
    _check_offline_runtime_controls(root, criteria, errors)

    return {
        "schema_id": REPORT_SCHEMA_ID,
        "status": "pass" if not errors else "fail",
        "matrix_path": str(matrix_file),
        "profile": matrix.get("profile"),
        "overlays": matrix.get("overlays"),
        "criteria": criteria,
        "errors": errors,
    }


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("JSON document must be an object")
    return payload


def _load_settings_defaults(repo_root: Path) -> dict[str, Any]:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from scripts.support_matrix_check import _settings_defaults

    return _settings_defaults(repo_root)


def _check_profile_and_boundary(
    matrix: dict[str, Any],
    criteria: list[dict[str, Any]],
    errors: list[str],
) -> None:
    passed = True
    messages: list[str] = []
    if matrix.get("profile") != "local_expert":
        passed = False
        messages.append("profile must be local_expert")
    if matrix.get("overlays") != RC3_OVERLAYS:
        passed = False
        messages.append("overlays must be ['public_connectors', 'sec_xbrl_offline']")
    if matrix.get("release_readiness_manifest") != "profile-neutral; do not populate owner_selected_profile_specific_gates":
        passed = False
        messages.append("release_readiness_manifest boundary statement is missing or changed")
    if matrix.get("pinned_false_flags") != PINNED_FALSE_FLAGS:
        passed = False
        messages.append("pinned_false_flags must match the selected local_expert pin set")
    boundary_note = str(matrix.get("boundary_note") or "")
    missing_tokens = sorted(token for token in RC3_BOUNDARY_TOKENS if token not in boundary_note)
    if missing_tokens:
        passed = False
        messages.append("boundary_note missing token(s): " + ", ".join(missing_tokens))
    _add_criterion(
        criteria,
        errors,
        "rc3_profile_and_boundary_tokens",
        passed,
        "; ".join(messages) if messages else "",
    )


def _check_capability_statuses(
    matrix: dict[str, Any],
    criteria: list[dict[str, Any]],
    errors: list[str],
) -> None:
    capabilities = matrix.get("capabilities")
    if not isinstance(capabilities, list):
        _add_criterion(criteria, errors, "capability_status_floor", False, "capabilities must be a list")
        return
    by_id = {item.get("id"): item for item in capabilities if isinstance(item, dict)}
    messages: list[str] = []
    for capability_id in sorted(UNSUPPORTED_CAPABILITIES):
        if by_id.get(capability_id, {}).get("status") != "unsupported":
            messages.append(f"{capability_id} must be unsupported")
    for capability_id in sorted(EXPERIMENTAL_DEFAULT_OFF_STATUS_CAPABILITIES):
        if by_id.get(capability_id, {}).get("status") != "experimental_default_off":
            messages.append(f"{capability_id} must be experimental_default_off")
    for capability_id in sorted(SEC_XBRL_SIMULATION_CAPABILITIES):
        if by_id.get(capability_id, {}).get("status") != "simulation":
            messages.append(f"{capability_id} must be simulation")
    _add_criterion(
        criteria,
        errors,
        "capability_status_floor",
        not messages,
        "; ".join(messages),
    )


def _check_evidence_pointers(
    matrix: dict[str, Any],
    repo_root: Path,
    criteria: list[dict[str, Any]],
    errors: list[str],
) -> None:
    missing: list[str] = []
    for capability in matrix.get("capabilities") or []:
        if not isinstance(capability, dict):
            continue
        for pointer in _evidence_file_pointers(str(capability.get("evidence") or "")):
            if not (repo_root / pointer).exists():
                missing.append(f"{capability.get('id')}: {pointer}")
    _add_criterion(
        criteria,
        errors,
        "evidence_pointers_resolve",
        not missing,
        "; ".join(missing),
    )


def _check_defaults(
    defaults: dict[str, Any],
    criteria: list[dict[str, Any]],
    errors: list[str],
) -> None:
    messages: list[str] = []
    pinned = {flag: defaults.get(flag) for flag in PINNED_FALSE_FLAGS}
    for flag, value in pinned.items():
        if value is not False:
            messages.append(f"{flag} default must be False")
    expected_profile = {
        "DEPLOYMENT_MODE": "local",
        "AUTH_OWNER": "none",
        "TRUSTED_PROXY_MODE": False,
        "NRC_ADAMS_APS_SUBSCRIPTION_KEY": "",
        "SENATE_LDA_API_KEY": "",
        "LAYER3_ROUTE_AUTHORIZATION_MODE": "identity_presence",
    }
    for key, expected in expected_profile.items():
        if defaults.get(key) != expected:
            messages.append(f"{key} default must be {expected!r}")
    if _database_kind(defaults.get("DATABASE_URL", "")) != "sqlite":
        messages.append("DATABASE_URL default must resolve to sqlite")
    _add_criterion(
        criteria,
        errors,
        "config_defaults_preserve_local_expert_floor",
        not messages,
        "; ".join(messages),
        details={"pinned_false_flags": pinned},
    )


def _check_release_readiness(
    release_readiness: dict[str, Any],
    criteria: list[dict[str, Any]],
    errors: list[str],
) -> None:
    messages: list[str] = []
    release = release_readiness.get("release")
    if not isinstance(release, dict):
        messages.append("release_readiness release must be an object")
    else:
        if release.get("version") != "0.3.0-rc1":
            messages.append("release_readiness version must be 0.3.0-rc1")
        if release.get("milestone") != "M-RC3-SEC-XBRL-OFFLINE-ACCEPTANCE":
            messages.append("release_readiness milestone must be M-RC3-SEC-XBRL-OFFLINE-ACCEPTANCE")
    if release_readiness.get("owner_selected_profile_specific_gates") != []:
        messages.append("release_readiness owner_selected_profile_specific_gates must stay []")
    _add_criterion(
        criteria,
        errors,
        "release_readiness_profile_neutral",
        not messages,
        "; ".join(messages),
    )


def _check_offline_runtime_controls(
    repo_root: Path,
    criteria: list[dict[str, Any]],
    errors: list[str],
) -> None:
    messages: list[str] = []
    try:
        control_payloads = _offline_runtime_control_payloads(repo_root)
    except Exception as exc:
        messages.append(f"offline runtime controls could not be exercised: {exc}")
        control_payloads = {}
    for name, controls in control_payloads.items():
        required_false_keys = set(OFFLINE_CONTROL_FALSE_KEYS)
        if name == "e2e_offline_orchestrator":
            required_false_keys.remove("network_performed")
        for key in required_false_keys:
            if key not in controls:
                messages.append(f"{name} missing {key} control")
            elif controls[key] is not False:
                messages.append(f"{name} {key} control must be False")
        if controls.get("network_performed", False) is not False:
            messages.append(f"{name} network_performed control must be False or absent")
        if name == "e2e_offline_orchestrator" and controls.get("offline_evidence_input_only") is not True:
            messages.append("e2e_offline_orchestrator missing offline_evidence_input_only=True control")
    stage_path = repo_root / "backend/app/services/layer3_sec_xbrl_offline_companyfacts_stage.py"
    try:
        stage_fields = _literal_return_dict_from_function(stage_path, "_build_stage_response")
    except Exception as exc:
        messages.append(f"companyfacts_stage response contract could not be parsed: {exc}")
    if "stage_fields" in locals():
        for key in STAGE_FALSE_KEYS:
            if stage_fields.get(key) is not False:
                messages.append(f"companyfacts_stage {key} response field must be False")
    _add_criterion(
        criteria,
        errors,
        "offline_service_controls_preserve_no_egress_floor",
        not messages,
        "; ".join(messages),
    )


def _offline_runtime_control_payloads(repo_root: Path) -> dict[str, dict[str, Any]]:
    _ensure_import_paths(repo_root)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.session import Base
    from app.services import layer3_sec_xbrl_e2e_offline_orchestrator as orchestrator
    from app.services import layer3_sec_xbrl_offline_companyfacts_oracle_packet as oracle_packet
    from app.services import layer3_sec_xbrl_offline_evidence_loader as loader
    from app.services import layer3_sec_xbrl_offline_evidence_proof_capability as proof_capability

    with tempfile.TemporaryDirectory(prefix="sec-xbrl-honesty-audit-") as tmp_dir:
        missing_storage = Path(tmp_dir) / "missing-storage"
        loader_report = loader.inspect_sec_xbrl_offline_evidence_storage(missing_storage)
        oracle_report = oracle_packet.inspect_sec_xbrl_offline_companyfacts_oracle_packet(missing_storage)
        proof_report = proof_capability.inspect_sec_xbrl_offline_evidence_proof_capability(
            storage_dir=missing_storage
        )

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    session = Session()
    try:
        orchestrator_report = orchestrator.open_redacted_operator_review_from_offline_evidence(
            session,
            client_request_id="sec-xbrl-honesty-audit-controls",
            evidence=_offline_evidence(),
            period_limit=2,
        )
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()

    return {
        "offline_evidence_loader": dict(loader_report.get("controls") or {}),
        "offline_companyfacts_oracle_packet": dict(oracle_report.get("controls") or {}),
        "offline_evidence_proof_capability": dict(proof_report.get("controls") or {}),
        "e2e_offline_orchestrator": dict(orchestrator_report.get("controls") or {}),
    }


def _ensure_import_paths(repo_root: Path) -> None:
    for path in (repo_root, repo_root / "backend"):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


def _literal_return_dict_from_function(path: Path, function_name: str) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            for child in ast.walk(node):
                if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                    values: dict[str, Any] = {}
                    for key_node, value_node in zip(child.value.keys, child.value.values):
                        if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                            values[key_node.value] = (
                                value_node.value if isinstance(value_node, ast.Constant) else None
                            )
                    return values
            raise ValueError(f"{function_name} has no literal dict return")
    raise ValueError(f"{function_name} not found in {path}")


def _database_kind(value: object) -> str:
    raw = str(value)
    if raw == "DEFAULT_DATABASE_URL" or raw.startswith("sqlite"):
        return "sqlite"
    if raw.startswith("postgres"):
        return "postgres"
    return "other"


def _offline_evidence() -> dict[str, Any]:
    from app.services.layer3_utils import json_clone, stable_hash

    sidecar_records = [
        _record("rf-revenue-old", "RevenueFromContractWithCustomerExcludingAssessedTax", start="start-1", end="end-1"),
        _record("rf-assets-old", "Assets", end="end-1", instant=True),
        _record("rf-cashflow-old", "NetCashProvidedByUsedInOperatingActivities", start="start-1", end="end-1"),
        _record("rf-revenue-fy", "RevenueFromContractWithCustomerExcludingAssessedTax", start="start-2", end="end-2"),
        _record("rf-assets-fy", "Assets", end="end-2", instant=True),
        _record("rf-cashflow-fy", "NetCashProvidedByUsedInOperatingActivities", start="start-2", end="end-2"),
        _record("rf-period-end", "DocumentPeriodEndDate", taxonomy="dei", unit="unitless", end="end-2", instant=True),
    ]
    value_records = [
        _value("rf-revenue-old", "90"),
        _value("rf-assets-old", "180"),
        _value("rf-cashflow-old", "30"),
        _value("rf-revenue-fy", "100"),
        _value("rf-assets-fy", "200"),
        _value("rf-cashflow-fy", "40"),
        _value("rf-period-end", "end-2"),
    ]
    value_store_hash = stable_hash(value_records)
    resolved_fact_projection = [_redacted_fact(record, json_clone=json_clone) for record in sidecar_records]
    return {
        "companyfacts": _companyfacts_periods(),
        "sidecar_receipt": {
            "sidecar_receipt_id": "sidecar-receipt-redacted",
            "sidecar_receipt_hash": _hash("b"),
            "resolved_fact_records": sidecar_records,
            "resolved_fact_projection": resolved_fact_projection,
            "resolved_fact_inventory_hash": stable_hash(resolved_fact_projection),
            "internal_value_store": {
                "value_store_hash": value_store_hash,
                "value_record_count": len(value_records),
            },
            "authority_hashes": {
                "internal_value_store_hash": value_store_hash,
                "sidecar_receipt_hash": _hash("b"),
            },
        },
        "value_store": {"value_records": value_records, "value_store_hash": value_store_hash},
        "statement_role_view_records": [
            {"fact_id_or_order_key": "rf-revenue-old", "statement_candidate_role": "income_statement"},
            {"fact_id_or_order_key": "rf-assets-old", "statement_candidate_role": "balance_sheet"},
            {"fact_id_or_order_key": "rf-cashflow-old", "statement_candidate_role": "cash_flow_statement"},
            {"fact_id_or_order_key": "rf-revenue-fy", "statement_candidate_role": "income_statement"},
            {"fact_id_or_order_key": "rf-assets-fy", "statement_candidate_role": "balance_sheet"},
            {"fact_id_or_order_key": "rf-cashflow-fy", "statement_candidate_role": "cash_flow_statement"},
        ],
        "dataset_version_id": "dataset-redacted",
    }


def _companyfacts_periods() -> dict[str, Any]:
    entries = [
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "90", "USD", "start-1", "end-1", False),
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "100", "USD", "start-2", "end-2", False),
        ("Assets", "180", "USD", "", "end-1", True),
        ("Assets", "200", "USD", "", "end-2", True),
        ("NetCashProvidedByUsedInOperatingActivities", "30", "USD", "start-1", "end-1", False),
        ("NetCashProvidedByUsedInOperatingActivities", "40", "USD", "start-2", "end-2", False),
    ]
    facts: dict[str, dict[str, Any]] = {}
    for local_name, value, unit, start, end, instant in entries:
        facts.setdefault("us-gaap", {}).setdefault(local_name, {"units": {}})
        fact: dict[str, Any] = {"fp": "FY", "fy": "", "val": value, "end": end}
        if not instant:
            fact["start"] = start
        facts["us-gaap"][local_name]["units"].setdefault(unit, []).append(fact)
    return facts


def _record(
    fact_id: str,
    local_name: str,
    *,
    taxonomy: str = "us-gaap",
    unit: str = "USD",
    start: str = "start-2",
    end: str = "end-2",
    instant: bool = False,
) -> dict[str, Any]:
    period = {"type": "instant", "instant": end} if instant else {"type": "duration", "start": start, "end": end}
    namespace = "xbrl.sec.gov/dei/test" if taxonomy == "dei" else "fasb.org/us-gaap/test"
    unit_payload = {"measures": []} if unit == "unitless" else {"currency": f"iso4217:{unit}", "measures": [f"iso4217:{unit}"]}
    return {
        "resolved_fact_id": fact_id,
        "concept": {"namespace": namespace, "local_name": local_name, "standard": True},
        "unit": unit_payload,
        "period": period,
        "dimensions": {"explicit": [], "typed": []},
    }


def _value(fact_id: str, effective_value: str) -> dict[str, Any]:
    return {"resolved_fact_id": fact_id, "effective_value": effective_value}


def _redacted_fact(record: dict[str, Any], *, json_clone: Any) -> dict[str, Any]:
    value = json_clone(record)
    value["value_redacted"] = True
    return value


def _hash(char: str) -> str:
    return char * 64


def _evidence_file_pointers(evidence: str) -> list[Path]:
    pointers: list[Path] = []
    for part in [item.strip() for item in evidence.split(";") if item.strip()]:
        token = part.split("::", 1)[0].strip()
        if token.startswith("PR-"):
            continue
        if ":" in token:
            token = token.split(":", 1)[0].strip()
        path = Path(token)
        if path.suffix in {".py", ".md", ".json", ".yaml", ".yml", ".html", ".js", ".css", ".ps1", ".example"}:
            pointers.append(path)
    return pointers


def _add_criterion(
    criteria: list[dict[str, Any]],
    errors: list[str],
    name: str,
    passed: bool,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> None:
    item = {
        "name": name,
        "status": "pass" if passed else "fail",
    }
    if message:
        item["message"] = message
    if details:
        item["details"] = details
    criteria.append(item)
    if not passed:
        errors.append(message or name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the RC3 SEC XBRL offline honesty ceiling.")
    parser.add_argument(
        "--matrix",
        default=str(default_repo_root() / "config" / "support_matrix.yaml"),
        help="Path to the JSON-compatible support matrix.",
    )
    parser.add_argument(
        "--release",
        default=str(default_repo_root() / "config" / "release_readiness.yaml"),
        help="Path to the JSON-compatible release readiness manifest.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(default_repo_root()),
        help="Repository root used for source and config-default checks.",
    )
    args = parser.parse_args(argv)

    report = build_report(
        matrix_path=Path(args.matrix),
        release_path=Path(args.release),
        repo_root=Path(args.repo_root),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
