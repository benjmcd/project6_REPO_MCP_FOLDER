from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


SCHEMA_ID = "project6.support_matrix.v1"
REPORT_SCHEMA_ID = "project6.support_matrix_check.v1"
STATUS_VOCABULARY = {
    "supported",
    "experimental_default_off",
    "simulation",
    "unsupported",
}
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
REQUIRED_UNSUPPORTED = {
    "real_provider_delivery",
    "model_agent_egress",
    "nonlocal_multi_trust_multi_identity",
    "high_availability",
    "keyed_connectors",
    "signed_reference_export",
}
BASE_SUPPORTED_CAPABILITIES = {
    "method_aware_analytics_vertical",
    "layer3_workbench_ui",
    "health_readiness_openapi",
}
PUBLIC_CONNECTOR_CAPABILITIES = {
    "sciencebase_public_connector_slice",
    "senate_lda_anonymous_connector_slice",
    "connector_run_observability",
}
SUPPORTED_CAPABILITIES = BASE_SUPPORTED_CAPABILITIES | PUBLIC_CONNECTOR_CAPABILITIES
EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES = {
    "sec_live_network_egress",
    "sec_value_reveal",
    "sec_controlled_value_reveal_submit",
    "arelle_internal_value_store",
    "arelle_corpus_validation",
    "sec_xbrl_production_admission_evaluator",
    "analysis_product_package_inventory",
    "ocr_external_engine",
}
PUBLIC_CONNECTOR_DEFERRAL_CAPABILITIES = {
    "sciencebase_public_connector_slice",
    "senate_lda_anonymous_connector_slice",
    "connector_run_observability",
}
PUBLIC_CONNECTORS_OVERLAY = ["public_connectors"]
RC3_SEC_XBRL_OFFLINE_OVERLAY = ["public_connectors", "sec_xbrl_offline"]
PUBLIC_CONNECTORS_REQUIRED_EVIDENCE = ["PR-1", "PR-2", "PR-3", "PR-4", "PR-5"]
SEC_XBRL_OFFLINE_SIMULATION_CAPABILITIES = {
    "layer3_sec_xbrl_offline_evidence_loader",
    "layer3_sec_xbrl_offline_companyfacts_stage",
    "layer3_sec_xbrl_offline_companyfacts_oracle_packet",
    "layer3_sec_xbrl_e2e_offline_orchestrator",
    "layer3_sec_xbrl_offline_evidence_proof_capability",
    "nrc_aps_replay_corpus_gate",
    "offline_staged_redaction_value_store_resolution",
    "sec_offline_replay_path",
}
SIMULATION_CAPABILITIES = SEC_XBRL_OFFLINE_SIMULATION_CAPABILITIES
EXPECTED_STATUS_BY_ID = {
    **{capability_id: "supported" for capability_id in SUPPORTED_CAPABILITIES},
    **{capability_id: "experimental_default_off" for capability_id in EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES},
    **{capability_id: "simulation" for capability_id in SIMULATION_CAPABILITIES},
    **{capability_id: "unsupported" for capability_id in REQUIRED_UNSUPPORTED},
}
RC3_BOUNDARY_TOKENS = {
    "live SEC egress explicit default-off",
    "no value-reveal default-on",
    "no agent egress",
    "no nonlocal",
}


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json_compatible_yaml(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} must remain JSON-compatible YAML") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return loaded


def _load_release_owner_gates(repo_root: Path) -> list[Any]:
    release_manifest = _load_json_compatible_yaml(repo_root / "config" / "release_readiness.yaml")
    gates = release_manifest.get("owner_selected_profile_specific_gates")
    if not isinstance(gates, list):
        raise ValueError("release_readiness owner_selected_profile_specific_gates must be a list")
    return gates


def _ast_literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _settings_defaults(repo_root: Path) -> dict[str, Any]:
    config_path = repo_root / "backend" / "app" / "core" / "config.py"
    tree = ast.parse(config_path.read_text(encoding="utf-8"), filename=str(config_path))
    settings_class = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Settings"
        ),
        None,
    )
    if settings_class is None:
        raise ValueError("Settings class not found in backend/app/core/config.py")

    defaults: dict[str, Any] = {}
    for statement in settings_class.body:
        if not isinstance(statement, ast.AnnAssign):
            continue
        if not isinstance(statement.target, ast.Name):
            continue
        if not isinstance(statement.value, ast.Call):
            continue
        field_call = statement.value
        if not isinstance(field_call.func, ast.Name) or field_call.func.id != "Field":
            continue

        alias = statement.target.id
        default: Any = None
        for keyword in field_call.keywords:
            if keyword.arg == "alias":
                alias_value = _ast_literal(keyword.value)
                if isinstance(alias_value, str):
                    alias = alias_value
            if keyword.arg == "default":
                default = _ast_literal(keyword.value)
        defaults[alias] = default
    return defaults


def _database_kind(value: object) -> str:
    raw = str(value)
    if raw == "DEFAULT_DATABASE_URL" or raw.startswith("sqlite"):
        return "sqlite"
    if raw.startswith("postgres"):
        return "postgres"
    return "other"


def _validate_matrix_shape(matrix: dict[str, Any], errors: list[str]) -> None:
    if matrix.get("schema_id") != SCHEMA_ID:
        errors.append(f"schema_id must be {SCHEMA_ID!r}")
    if matrix.get("profile") != "local_expert":
        errors.append("profile must be local_expert")
    overlays = matrix.get("overlays")
    if (
        overlays != "none"
        and overlays != PUBLIC_CONNECTORS_OVERLAY
        and overlays != RC3_SEC_XBRL_OFFLINE_OVERLAY
    ):
        errors.append("overlays must be none, ['public_connectors'], or ['public_connectors', 'sec_xbrl_offline']")
    if matrix.get("release_readiness_manifest") != "profile-neutral; do not populate owner_selected_profile_specific_gates":
        errors.append("release_readiness_manifest boundary statement is missing or changed")
    if matrix.get("pinned_false_flags") != PINNED_FALSE_FLAGS:
        errors.append("pinned_false_flags must match the selected local_expert pin set")

    capabilities = matrix.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("capabilities must be a non-empty list")
        return

    seen: set[str] = set()
    for item in capabilities:
        if not isinstance(item, dict):
            errors.append("each capability must be a mapping")
            continue
        if set(item) != {"id", "status", "evidence"}:
            errors.append(f"capability {item.get('id')!r} must have only id/status/evidence")
        capability_id = item.get("id")
        if not isinstance(capability_id, str) or not capability_id.strip():
            errors.append("each capability needs a non-empty id")
        elif capability_id in seen:
            errors.append(f"duplicate capability id {capability_id!r}")
        else:
            seen.add(capability_id)
        if item.get("status") not in STATUS_VOCABULARY:
            errors.append(f"capability {capability_id!r} has invalid status {item.get('status')!r}")
        if not isinstance(item.get("evidence"), str) or not item["evidence"].strip():
            errors.append(f"capability {capability_id!r} needs evidence")

    by_id = {item.get("id"): item for item in capabilities if isinstance(item, dict)}
    for capability_id in REQUIRED_UNSUPPORTED:
        if by_id.get(capability_id, {}).get("status") != "unsupported":
            errors.append(f"{capability_id} must be unsupported in local_expert")
    for capability_id in BASE_SUPPORTED_CAPABILITIES:
        if by_id.get(capability_id, {}).get("status") != "supported":
            errors.append(f"{capability_id} must be supported in local_expert")
    for capability_id in EXPERIMENTAL_DEFAULT_OFF_CAPABILITIES:
        if by_id.get(capability_id, {}).get("status") != "experimental_default_off":
            errors.append(f"{capability_id} must remain experimental_default_off in local_expert")
    if overlays == "none":
        for capability_id in PUBLIC_CONNECTOR_DEFERRAL_CAPABILITIES:
            item = by_id.get(capability_id, {})
            if item.get("status") != "experimental_default_off":
                errors.append(f"{capability_id} must be experimental_default_off in analytics-only local_expert")
            evidence = str(item.get("evidence") or "")
            if "RC2-targeted" not in evidence:
                errors.append(f"{capability_id} evidence must note RC2-targeted connector deferral")
    elif overlays == PUBLIC_CONNECTORS_OVERLAY or overlays == RC3_SEC_XBRL_OFFLINE_OVERLAY:
        for capability_id in PUBLIC_CONNECTOR_CAPABILITIES:
            item = by_id.get(capability_id, {})
            if item.get("status") != "supported":
                errors.append(f"{capability_id} must be supported when public_connectors overlay is selected")
            evidence = str(item.get("evidence") or "")
            missing = [
                marker
                for marker in PUBLIC_CONNECTORS_REQUIRED_EVIDENCE
                if marker not in evidence
            ]
            if missing:
                errors.append(f"{capability_id} evidence missing public connector PR markers: {', '.join(missing)}")
    if overlays == RC3_SEC_XBRL_OFFLINE_OVERLAY:
        boundary_note = str(matrix.get("boundary_note") or "")
        for token in sorted(RC3_BOUNDARY_TOKENS):
            if token not in boundary_note:
                errors.append(f"boundary_note missing RC3 token {token!r}")
        for capability_id in SIMULATION_CAPABILITIES:
            item = by_id.get(capability_id, {})
            if item.get("status") != "simulation":
                errors.append(f"{capability_id} must be simulation when sec_xbrl_offline overlay is selected")
    else:
        for capability_id in SIMULATION_CAPABILITIES:
            item = by_id.get(capability_id, {})
            if item.get("status") == "simulation":
                errors.append(f"{capability_id} cannot be simulation without sec_xbrl_offline overlay")


def run_support_matrix_check(
    matrix_path: Path | str | None = None,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = (repo_root or default_repo_root()).resolve()
    path = Path(matrix_path) if matrix_path is not None else root / "config" / "support_matrix.yaml"
    errors: list[str] = []

    try:
        matrix = _load_json_compatible_yaml(path)
    except Exception as exc:
        return {
            "schema_id": REPORT_SCHEMA_ID,
            "status": "fail",
            "error": str(exc),
        }

    _validate_matrix_shape(matrix, errors)

    try:
        owner_gates = _load_release_owner_gates(root)
    except Exception as exc:
        owner_gates = None
        errors.append(str(exc))
    if owner_gates != []:
        errors.append("release_readiness owner_selected_profile_specific_gates must stay []")

    try:
        defaults = _settings_defaults(root)
    except Exception as exc:
        defaults = {}
        errors.append(f"could not load Settings defaults: {exc}")

    default_profile = {
        "deployment_mode": defaults.get("DEPLOYMENT_MODE"),
        "auth_owner": defaults.get("AUTH_OWNER"),
        "route_authorization_mode": defaults.get("LAYER3_ROUTE_AUTHORIZATION_MODE"),
        "database": _database_kind(defaults.get("DATABASE_URL", "")),
    }
    if default_profile != {
        "deployment_mode": "local",
        "auth_owner": "none",
        "route_authorization_mode": "identity_presence",
        "database": "sqlite",
    }:
        errors.append("Settings defaults do not match local_expert local/no-auth/sqlite posture")

    pinned_results = {
        flag: defaults.get(flag)
        for flag in PINNED_FALSE_FLAGS
    }
    bad_flags = [flag for flag, value in pinned_results.items() if value is not False]
    if bad_flags:
        errors.append("pinned false flag default is not false: " + ", ".join(bad_flags))

    if defaults.get("NRC_ADAMS_APS_SUBSCRIPTION_KEY", None) not in {"", None}:
        errors.append("NRC_ADAMS_APS_SUBSCRIPTION_KEY must default empty for local_expert")
    if defaults.get("SENATE_LDA_API_KEY", None) not in {"", None}:
        errors.append("SENATE_LDA_API_KEY must default empty for local_expert")
    if defaults.get("TRUSTED_PROXY_MODE", None) is not False:
        errors.append("TRUSTED_PROXY_MODE must default false for local_expert")

    return {
        "schema_id": REPORT_SCHEMA_ID,
        "status": "pass" if not errors else "fail",
        "profile": matrix.get("profile"),
        "overlays": matrix.get("overlays"),
        "default_profile": default_profile,
        "pinned_false_flags_status": "pass" if not bad_flags else "fail",
        "pinned_false_flags": pinned_results,
        "release_readiness_owner_selected_profile_specific_gates": owner_gates,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the selected local_expert support matrix.")
    parser.add_argument(
        "--matrix",
        default=str(default_repo_root() / "config" / "support_matrix.yaml"),
        help="Path to the JSON-compatible support matrix.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(default_repo_root()),
        help="Repository root used for config/default checks.",
    )
    args = parser.parse_args(argv)
    report = run_support_matrix_check(Path(args.matrix), repo_root=Path(args.repo_root))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
