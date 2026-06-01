from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path("diagnostics/assessment/sec-xbrl-auth-owner-binding-strategy-report.json")
TARGET = "sec_xbrl_nonlocal_in_app_auth_owner_binding_strategy_v1"
SCHEMA_ID = "diagnostics.sec_xbrl_nonlocal_in_app_auth_owner_binding_strategy.v1"
POLICY_SCHEMA_ID = "layer3.sec_xbrl.repo_owned_in_app_operator_auth_owner_binding_strategy.v1"
SELECTED_STRATEGY = "separate_hash_only_auth_binding_receipt_table"
NEXT_SLICE = "sec_xbrl_nonlocal_in_app_auth_owner_binding_table_design_v1"

MODELS_FILE = "backend/app/models/models.py"
API_FILE = "backend/app/api/layer3.py"
AUTH_DESIGN_DOC = "next_milestone_plans/Layer3_planning_docs/1321-in-app-auth.md"
AUTH_POLICY_DOC = "next_milestone_plans/Layer3_planning_docs/1322-in-app-auth-policy-validation.md"
AUTH_POLICY_REPORT = "diagnostics/assessment/sec-xbrl-in-app-auth-policy-validation-report.json"


RECEIPT_SURFACES: tuple[dict[str, Any], ...] = (
    {
        "receipt_kind": "operator_review_workflow",
        "model_class": "L3SecXbrlOperatorReviewWorkflow",
        "table_name": "l3_sec_xbrl_operator_review_workflow",
        "id_column": "sec_xbrl_operator_review_workflow_id",
        "basis_hash_column": "workflow_basis_hash",
        "migration_file": "backend/alembic/versions/0040_layer3_sec_xbrl_operator_review_workflow.py",
        "service_file": "backend/app/services/layer3_sec_xbrl_operator_review_workflow.py",
        "route_families": (
            "sec_xbrl_operator_review_workflow_status_read",
            "sec_xbrl_operator_review_decision_submit_write",
        ),
    },
    {
        "receipt_kind": "operator_review_decision",
        "model_class": "L3SecXbrlOperatorReviewDecision",
        "table_name": "l3_sec_xbrl_operator_review_decision",
        "id_column": "sec_xbrl_operator_review_decision_id",
        "basis_hash_column": "decision_basis_hash",
        "migration_file": "backend/alembic/versions/0042_layer3_sec_xbrl_operator_review_decision.py",
        "service_file": "backend/app/services/layer3_sec_xbrl_operator_review_workflow.py",
        "route_families": (
            "sec_xbrl_operator_review_decision_submit_write",
            "sec_xbrl_operator_review_decision_status_read",
            "sec_xbrl_value_reveal_authority_prepare_write",
        ),
    },
    {
        "receipt_kind": "value_reveal_authority",
        "model_class": "L3SecXbrlValueRevealAuthorityReceipt",
        "table_name": "l3_sec_xbrl_value_reveal_authority_receipt",
        "id_column": "sec_xbrl_value_reveal_authority_receipt_id",
        "basis_hash_column": "authority_basis_hash",
        "migration_file": "backend/alembic/versions/0044_layer3_sec_xbrl_value_reveal_authority_receipt.py",
        "service_file": "backend/app/services/layer3_sec_xbrl_value_reveal_authority.py",
        "route_families": (
            "sec_xbrl_value_reveal_authority_prepare_write",
            "sec_xbrl_controlled_value_reveal_submit_write",
        ),
    },
    {
        "receipt_kind": "controlled_value_reveal_submit",
        "model_class": "L3SecXbrlControlledValueRevealSubmitReceipt",
        "table_name": "l3_sec_xbrl_controlled_value_reveal_submit_receipt",
        "id_column": "sec_xbrl_controlled_value_reveal_submit_receipt_id",
        "basis_hash_column": "submit_basis_hash",
        "migration_file": "backend/alembic/versions/0045_layer3_sec_xbrl_controlled_value_reveal_submit.py",
        "service_file": "backend/app/services/layer3_sec_xbrl_controlled_value_reveal_submit.py",
        "route_families": (
            "sec_xbrl_controlled_value_reveal_submit_write",
            "sec_xbrl_controlled_value_reveal_submit_status_read",
        ),
    },
)


PROPOSED_BINDING_FIELDS: tuple[str, ...] = (
    "sec_xbrl_auth_binding_receipt_id",
    "source_receipt_kind",
    "source_receipt_id",
    "source_receipt_basis_hash",
    "route_family",
    "actor_ref_hash",
    "workspace_ref_hash",
    "policy_hash",
    "binding_basis_hash",
    "binding_state",
    "binding_schema_id",
    "created_at",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate-only SEC XBRL owner-binding strategy diagnostic. This script "
            "reads repo source and emits a redacted strategy report; it does not "
            "change models, migrations, routes, services, persistence, auth runtime, "
            "source acquisition, Arelle behavior, value reveal, export, or defaults."
        )
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    report = build_report()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {_repo_path(output)}")
    print(f"decision={report['decision']}")
    return 0


def build_report(
    *,
    root: Path = ROOT,
    receipt_surfaces: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    surfaces = list(RECEIPT_SURFACES if receipt_surfaces is None else receipt_surfaces)
    surface_evidence = [_receipt_surface_evidence(root, surface) for surface in surfaces]
    strategy_options = _strategy_options(surface_evidence)
    selected_option = next(item for item in strategy_options if item["strategy"] == SELECTED_STRATEGY)

    criteria = [
        _criterion(
            "receipt_surface_inventory_nonempty",
            bool(surface_evidence),
            {"receipt_surface_count": len(surface_evidence)},
            "sec_xbrl_auth_owner_binding_strategy_receipt_surface_inventory_empty",
        ),
        _criterion(
            "current_receipt_surfaces_present",
            bool(surface_evidence) and all(item["surface_present"] for item in surface_evidence),
            {
                "receipt_surface_count": len(surface_evidence),
                "missing_receipt_surfaces": [
                    item["receipt_kind"] for item in surface_evidence if not item["surface_present"]
                ],
            },
            "sec_xbrl_auth_owner_binding_strategy_receipt_surface_missing",
        ),
        _criterion(
            "current_owner_binding_not_uniform",
            bool(surface_evidence) and any(item["owner_binding_state"] != "complete" for item in surface_evidence),
            {
                "complete_binding_count": sum(
                    1 for item in surface_evidence if item["owner_binding_state"] == "complete"
                ),
                "partial_binding_count": sum(
                    1 for item in surface_evidence if item["owner_binding_state"] == "partial"
                ),
                "absent_binding_count": sum(
                    1 for item in surface_evidence if item["owner_binding_state"] == "absent"
                ),
            },
            "sec_xbrl_auth_owner_binding_strategy_current_receipts_already_uniform",
        ),
        _criterion(
            "auth_policy_traceability_current",
            _auth_policy_traceability_holds(root),
            {
                "auth_design_doc": AUTH_DESIGN_DOC,
                "auth_policy_doc": AUTH_POLICY_DOC,
                "auth_policy_report": AUTH_POLICY_REPORT,
                "prior_next_slice": TARGET,
            },
            "sec_xbrl_auth_owner_binding_strategy_prior_policy_trace_missing",
        ),
        _criterion(
            "selected_strategy_is_separate_hash_only_binding_table",
            selected_option["recommended"] is True and selected_option["strategy"] == SELECTED_STRATEGY,
            {
                "selected_strategy": selected_option["strategy"],
                "reason_codes": selected_option["reason_codes"],
            },
            "sec_xbrl_auth_owner_binding_strategy_selection_not_admitted",
        ),
        _criterion(
            "tier2_boundary_preserved",
            selected_option["future_tier"] == "Tier 2" and selected_option["implemented_now"] is False,
            {
                "future_tier": selected_option["future_tier"],
                "implemented_now": selected_option["implemented_now"],
                "requires_independent_review_when_practical": True,
            },
            "sec_xbrl_auth_owner_binding_strategy_tier2_boundary_regressed",
        ),
        _criterion(
            "redacted_strategy_output_contract",
            _redacted_output_contract_holds(surface_evidence, strategy_options),
            {
                "raw_identity_exposed": False,
                "local_path_exposed": False,
                "raw_value_exposed": False,
                "residual_magnitude_exposed": False,
            },
            "sec_xbrl_auth_owner_binding_strategy_redaction_contract_failed",
        ),
        _criterion(
            "standing_non_admissions_preserved",
            True,
            _non_goals_preserved(),
            "sec_xbrl_auth_owner_binding_strategy_non_admission_regressed",
        ),
    ]
    blocking_reasons = [
        criterion["blocked_reason"]
        for criterion in criteria
        if criterion["state"] == "blocked" and criterion["blocked_reason"]
    ]

    return {
        "schema_id": SCHEMA_ID,
        "target": TARGET,
        "decision": (
            "sec_xbrl_auth_owner_binding_strategy_selected"
            if not blocking_reasons
            else "sec_xbrl_auth_owner_binding_strategy_blocked"
        ),
        "headline": (
            "SEC XBRL owner-binding strategy selected as a separate hash-only binding receipt table."
            if not blocking_reasons
            else "SEC XBRL owner-binding strategy is blocked; do not implement owner binding on this basis."
        ),
        "criteria": criteria,
        "blocking_reasons": blocking_reasons,
        "selected_strategy": SELECTED_STRATEGY,
        "policy_schema_id": POLICY_SCHEMA_ID,
        "receipt_surface_inventory": surface_evidence,
        "strategy_options": strategy_options,
        "proposed_binding_contract": {
            "table_name": "l3_sec_xbrl_auth_binding_receipt",
            "model_class": "L3SecXbrlAuthBindingReceipt",
            "fields": list(PROPOSED_BINDING_FIELDS),
            "unique_constraints": [
                "source_receipt_kind + source_receipt_id",
                "binding_basis_hash",
            ],
            "required_indexes": [
                "source_receipt_kind + source_receipt_basis_hash",
                "actor_ref_hash + workspace_ref_hash",
                "policy_hash",
            ],
            "redaction_policy": "hash_only_actor_workspace_policy_refs_v1",
        },
        "next_slice": NEXT_SLICE,
        "non_goals_preserved": _non_goals_preserved(),
        "source_documents": {
            "models": MODELS_FILE,
            "api": API_FILE,
            "auth_design_doc": AUTH_DESIGN_DOC,
            "auth_policy_doc": AUTH_POLICY_DOC,
            "auth_policy_report": AUTH_POLICY_REPORT,
        },
    }


def _receipt_surface_evidence(root: Path, surface: Mapping[str, Any]) -> dict[str, Any]:
    models_source = _read(root / MODELS_FILE)
    migration_source = _read(root / str(surface["migration_file"]))
    service_source = _read(root / str(surface["service_file"]))
    class_block = _class_block(models_source, str(surface["model_class"]))

    actor_column_present = any(
        token in class_block for token in ("actor_ref_hash", "operator_actor_hash", "operator_principal_hash")
    )
    workspace_column_present = any(
        token in class_block
        for token in (
            "workspace_ref_hash",
            "tenant_or_workspace_ref_hash",
            "workspace_hash",
            "operator_workspace_hash",
        )
    )
    if actor_column_present and workspace_column_present:
        owner_binding_state = "complete"
    elif actor_column_present or workspace_column_present:
        owner_binding_state = "partial"
    else:
        owner_binding_state = "absent"

    required_model_tokens = (
        f"class {surface['model_class']}",
        f'__tablename__ = "{surface["table_name"]}"',
        str(surface["id_column"]),
        str(surface["basis_hash_column"]),
    )
    required_migration_tokens = (
        str(surface["table_name"]),
        str(surface["id_column"]),
        str(surface["basis_hash_column"]),
    )
    surface_present = (
        bool(class_block)
        and all(token in models_source for token in required_model_tokens)
        and all(token in migration_source for token in required_migration_tokens)
        and str(surface["model_class"]) in service_source
    )

    return {
        "receipt_kind": str(surface["receipt_kind"]),
        "model_class": str(surface["model_class"]),
        "table_name": str(surface["table_name"]),
        "id_column": str(surface["id_column"]),
        "basis_hash_column": str(surface["basis_hash_column"]),
        "migration_file": str(surface["migration_file"]),
        "service_file": str(surface["service_file"]),
        "route_families": list(surface["route_families"]),
        "surface_present": surface_present,
        "actor_binding_column_present": actor_column_present,
        "workspace_binding_column_present": workspace_column_present,
        "owner_binding_state": owner_binding_state,
    }


def _strategy_options(surface_evidence: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    incomplete = [item["receipt_kind"] for item in surface_evidence if item["owner_binding_state"] != "complete"]
    return [
        {
            "strategy": "add_columns_to_each_existing_sec_xbrl_receipt_table",
            "recommended": False,
            "future_tier": "Tier 2",
            "implemented_now": False,
            "reason_codes": [
                "touches_multiple_existing_receipt_contracts",
                "requires_per_receipt_backfill_and_service_propagation",
                "current_receipt_owner_binding_is_mixed_partial_and_absent",
            ],
            "affected_receipt_kinds": [item["receipt_kind"] for item in surface_evidence],
        },
        {
            "strategy": SELECTED_STRATEGY,
            "recommended": bool(surface_evidence) and bool(incomplete),
            "future_tier": "Tier 2",
            "implemented_now": False,
            "reason_codes": [
                "centralizes_hash_only_actor_workspace_binding",
                "avoids_rewriting_existing_receipt_contracts",
                "supports_uniform_cross_receipt_owner_checks",
                "keeps_export_delivery_and_value_reveal_as_separate_gates",
            ],
            "affected_receipt_kinds": [item["receipt_kind"] for item in surface_evidence],
        },
    ]


def _auth_policy_traceability_holds(root: Path) -> bool:
    design_doc = _read(root / AUTH_DESIGN_DOC)
    policy_doc = _read(root / AUTH_POLICY_DOC)
    report = _read(root / AUTH_POLICY_REPORT)
    required = (
        TARGET in policy_doc,
        "owner-binding persistence strategy" in policy_doc,
        "bind mutating authority receipts" in design_doc,
        "sec_xbrl_in_app_auth_policy_validation_passed" in report,
        '"owner_binding_strategy_selected_for_runtime": false' in report,
    )
    return all(required)


def _redacted_output_contract_holds(
    surface_evidence: Sequence[Mapping[str, Any]],
    strategy_options: Sequence[Mapping[str, Any]],
) -> bool:
    text = json.dumps(
        {
            "surface_evidence": list(surface_evidence),
            "strategy_options": list(strategy_options),
        },
        sort_keys=True,
    )
    forbidden_fragments = (
        "operator@example",
        "C:/",
        "\\Users\\",
        "/workspace/",
        "0000123456",
        "https://www.sec.gov/",
        "123.45",
        "raw_value",
    )
    return not any(fragment in text for fragment in forbidden_fragments)


def _non_goals_preserved() -> dict[str, bool]:
    return {
        "runtime_auth_dependency_installed_by_diagnostic": False,
        "api_route_behavior_changed_by_diagnostic": False,
        "config_default_changed_by_diagnostic": False,
        "schema_models_changed_by_diagnostic": False,
        "migration_changed_by_diagnostic": False,
        "durable_persistence_changed_by_diagnostic": False,
        "owner_binding_persistence_implemented_by_diagnostic": False,
        "value_reveal_default_enabled_by_diagnostic": False,
        "controlled_value_reveal_submit_default_enabled_by_diagnostic": False,
        "raw_internal_value_store_default_enabled_by_diagnostic": False,
        "source_acquisition_performed_by_diagnostic": False,
        "arelle_subprocess_invoked_by_diagnostic": False,
        "live_sec_network_run_performed_by_diagnostic": False,
        "export_or_delivery_enabled_by_diagnostic": False,
        "provider_or_connector_dispatch_enabled_by_diagnostic": False,
        "raw_runtime_artifacts_added_by_diagnostic": False,
        "redaction_posture_changed_by_diagnostic": False,
        "production_readiness_claimed": False,
        "final_financial_statement_semantics_claimed": False,
        "cross_company_comparability_claimed": False,
    }


def _class_block(source: str, class_name: str) -> str:
    marker = f"class {class_name}("
    start = source.find(marker)
    if start == -1:
        return ""
    next_class = source.find("\n\nclass ", start + len(marker))
    if next_class == -1:
        return source[start:]
    return source[start:next_class]


def _criterion(name: str, passed: bool, evidence: dict[str, Any], blocked_reason: str) -> dict[str, Any]:
    return {
        "criterion": name,
        "state": "passed" if passed else "blocked",
        "blocked_reason": None if passed else blocked_reason,
        "evidence": evidence,
    }


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
