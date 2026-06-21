from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPORT_SCHEMA_ID = "project6.sec_xbrl_offline_honesty_audit.v1"

PINNED_FALSE_FLAGS = [
    "LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    "LAYER3_MODEL_EGRESS_ENABLED",
    "SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED",
    "LAYER3_ANALYSIS_PRODUCT_PACKAGE_INVENTORY_ENABLED",
]

RC3_OVERLAYS = ["public_connectors", "sec_xbrl_offline"]
RC3_BOUNDARY_TOKENS = {
    "no live SEC egress",
    "no value-reveal default-on",
    "no agent egress",
    "no nonlocal",
}

UNSUPPORTED_CAPABILITIES = {
    "sec_live_network_egress",
    "real_provider_delivery",
    "model_agent_egress",
    "nonlocal_multi_trust_multi_identity",
    "high_availability",
    "keyed_connectors",
    "signed_reference_export",
}

SEC_EXPERIMENTAL_DEFAULT_OFF_FLAGS = {
    "sec_value_reveal": "LAYER3_SEC_EDGAR_ARELLE_VALUE_REVEAL_ENABLED",
    "sec_controlled_value_reveal_submit": "LAYER3_SEC_XBRL_CONTROLLED_VALUE_REVEAL_SUBMIT_ENABLED",
    "arelle_internal_value_store": "LAYER3_SEC_EDGAR_ARELLE_INTERNAL_VALUE_STORE_ENABLED",
    "arelle_corpus_validation": "LAYER3_SEC_EDGAR_ARELLE_CORPUS_VALIDATION_ENABLED",
    "sec_xbrl_production_admission_evaluator": "SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED",
}

SEC_XBRL_SIMULATION_CAPABILITIES = {
    "sec_offline_replay_path",
    "layer3_sec_xbrl_offline_evidence_loader",
    "layer3_sec_xbrl_offline_companyfacts_stage",
    "layer3_sec_xbrl_offline_companyfacts_oracle_packet",
    "layer3_sec_xbrl_e2e_offline_orchestrator",
    "layer3_sec_xbrl_offline_evidence_proof_capability",
    "offline_staged_redaction_value_store_resolution",
}

OFFLINE_CONTROL_FALSE_KEYS = {
    "source_acquisition_performed",
    "arelle_invoked",
    "network_performed",
    "value_reveal_performed",
    "api_route_enabled",
    "production_readiness_claimed",
}

CONTROL_SOURCE_FILES = {
    "offline_evidence_loader": "backend/app/services/layer3_sec_xbrl_offline_evidence_loader.py",
    "offline_companyfacts_oracle_packet": (
        "backend/app/services/layer3_sec_xbrl_offline_companyfacts_oracle_packet.py"
    ),
    "e2e_offline_orchestrator": "backend/app/services/layer3_sec_xbrl_e2e_offline_orchestrator.py",
    "offline_evidence_proof_capability": (
        "backend/app/services/layer3_sec_xbrl_offline_evidence_proof_capability.py"
    ),
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
    repo_root: Path | None = None,
    settings_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = (repo_root or default_repo_root()).resolve()
    matrix_file = (matrix_path or root / "config" / "support_matrix.yaml").resolve()
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
    _check_offline_control_sources(root, criteria, errors)

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
    for capability_id in sorted(SEC_EXPERIMENTAL_DEFAULT_OFF_FLAGS):
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
    }
    for key, expected in expected_profile.items():
        if defaults.get(key) != expected:
            messages.append(f"{key} default must be {expected!r}")
    _add_criterion(
        criteria,
        errors,
        "config_defaults_preserve_local_expert_floor",
        not messages,
        "; ".join(messages),
        details={"pinned_false_flags": pinned},
    )


def _check_offline_control_sources(
    repo_root: Path,
    criteria: list[dict[str, Any]],
    errors: list[str],
) -> None:
    messages: list[str] = []
    for name, rel_path in CONTROL_SOURCE_FILES.items():
        path = repo_root / rel_path
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            messages.append(f"{name} source missing: {rel_path}")
            continue
        required_false_keys = set(OFFLINE_CONTROL_FALSE_KEYS)
        if name == "e2e_offline_orchestrator":
            required_false_keys.remove("network_performed")
        for key in required_false_keys:
            if f'"{key}": False' not in text:
                messages.append(f"{name} missing {key}=False control")
        if name == "e2e_offline_orchestrator" and '"offline_evidence_input_only": True' not in text:
            messages.append("e2e_offline_orchestrator missing offline_evidence_input_only=True control")
    stage_path = repo_root / "backend/app/services/layer3_sec_xbrl_offline_companyfacts_stage.py"
    try:
        stage_text = stage_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        messages.append("companyfacts_stage source missing")
    else:
        for key in STAGE_FALSE_KEYS:
            if f'"{key}": False' not in stage_text:
                messages.append(f"companyfacts_stage missing {key}=False response field")
    _add_criterion(
        criteria,
        errors,
        "offline_service_controls_preserve_no_egress_floor",
        not messages,
        "; ".join(messages),
    )


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
        "--repo-root",
        default=str(default_repo_root()),
        help="Repository root used for source and config-default checks.",
    )
    args = parser.parse_args(argv)

    report = build_report(matrix_path=Path(args.matrix), repo_root=Path(args.repo_root))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
