from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "next_milestone_plans" / "layer3_progress_manifest.json"
BOARD = ROOT / "next_milestone_plans" / "layer3_progress_board.md"
REFRESH_SPEC = ROOT / "next_milestone_plans" / "layer3_progress_refresh_spec.md"
PROGRESS_PROMPT = ROOT / "next_milestone_plans" / "progress-prompt.md"
PROOF_MANIFEST = ROOT / "next_milestone_plans" / "layer3_workbench_proof_manifest.json"
PLAYWRIGHT_WORKFLOW = ROOT / ".github" / "workflows" / "playwright.yml"
PLAYWRIGHT_CONFIG = ROOT / "playwright.config.js"
LAYER3_API_REQUIREMENTS = ROOT / "backend" / "tests" / "requirements-layer3-api.txt"
BROWSER_REQUIREMENTS = ROOT / "backend" / "tests" / "requirements-browser.txt"
PHASE1A_README = ROOT / "next_milestone_plans" / "README_LAYER3_PHASE1A_PACK.md"
PLANNING_DOCS = ROOT / "next_milestone_plans" / "Layer3_planning_docs"
DEFERRED_GATES = PLANNING_DOCS / "105_deferred-gates.md"
QUAL_APS_FREEZE = PLANNING_DOCS / "114_QUAL_APS_EXEC_FREEZE.md"
LOCAL_BOUNDARY = PLANNING_DOCS / "116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md"
SYNTHESIS_BOUNDARY = PLANNING_DOCS / "117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md"
GOAL_AUDIT = PLANNING_DOCS / "118_L3_GOAL_AUDIT.md"
QUAL_APS_ENTRY_FREEZE = PLANNING_DOCS / "119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md"
CLOSEOUT_DOC = PLANNING_DOCS / "120_L3_CLOSEOUT.md"
CONNECTOR_ENTRY_FREEZE = PLANNING_DOCS / "121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md"
PACKAGE_MUTATION_FREEZE = PLANNING_DOCS / "122_PACKAGE_MUTATION_FREEZE.md"
SOURCE_EXPANSION_FREEZE = PLANNING_DOCS / "123_SOURCE_EXPANSION_FREEZE.md"
RAW_MIXED_BRIDGE_FREEZE = PLANNING_DOCS / "137_RAW_MIXED_BRIDGE_FREEZE.md"
QUAL_APS_PACKAGE_REVIEW_FREEZE = (
    PLANNING_DOCS / "138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md"
)
QUAL_APS_PACKAGE_REVIEW_CONTRACT = (
    PLANNING_DOCS / "139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md"
)
QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE = (
    PLANNING_DOCS / "140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md"
)
QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT = (
    PLANNING_DOCS / "141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md"
)
POST_709_ROADMAP_FREEZE = PLANNING_DOCS / "142_POST_709_ROADMAP_FREEZE.md"
QUAL_APS_PACKAGE_SUBMIT_FREEZE = (
    PLANNING_DOCS / "143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md"
)
QUAL_APS_PACKAGE_SUBMIT_CONTRACT = (
    PLANNING_DOCS / "144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md"
)
QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE = (
    PLANNING_DOCS / "145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md"
)
QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT = (
    PLANNING_DOCS / "146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md"
)
QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE = (
    PLANNING_DOCS / "147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md"
)
QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT = (
    PLANNING_DOCS / "148_QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT.md"
)
QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE = (
    PLANNING_DOCS / "149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md"
)
QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT = (
    PLANNING_DOCS / "150_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT.md"
)
QUAL_APS_RENDERED_UI_FREEZE = PLANNING_DOCS / "151_QUAL_APS_RENDERED_UI_FREEZE.md"
QUAL_APS_RENDERED_UI_CONTRACT = PLANNING_DOCS / "152_QUAL_APS_RENDERED_UI_CONTRACT.md"
SOURCE_BREADTH_FREEZE = PLANNING_DOCS / "153_SOURCE_BREADTH_FREEZE.md"
RAW_INGESTION_MATERIALIZATION_FREEZE = (
    PLANNING_DOCS / "154_RAW_INGESTION_MATERIALIZATION_FREEZE.md"
)
RAW_MIXED_RENDERED_UI_FREEZE = PLANNING_DOCS / "155_RAW_MIXED_RENDERED_UI_FREEZE.md"
RAW_MIXED_RENDERED_UI_CONTRACT = PLANNING_DOCS / "156_RAW_MIXED_RENDERED_UI_CONTRACT.md"
POST_730_ROADMAP_SYNC = PLANNING_DOCS / "157_POST_730_ROADMAP_SYNC.md"
POST_730_PRACTICAL_READINESS = PLANNING_DOCS / "158_POST_730_PRACTICAL_READINESS.md"
RAW_MIXED_RENDERED_DOWNSTREAM_BLOCKER = (
    PLANNING_DOCS / "159_RAW_MIXED_RENDERED_DOWNSTREAM_BLOCKER.md"
)
RENDERED_EXECUTION_SELECTION_START_FREEZE = (
    PLANNING_DOCS / "160_RENDERED_EXECUTION_SELECTION_START_FREEZE.md"
)
RENDERED_EXECUTION_SELECTION_START_CONTRACT = (
    PLANNING_DOCS / "161_RENDERED_EXECUTION_SELECTION_START_CONTRACT.md"
)
RENDERED_EXECUTION_SELECTION_START_RUNTIME = (
    PLANNING_DOCS / "162_RENDERED_EXECUTION_SELECTION_START_RUNTIME.md"
)
RENDERED_RESULT_REVIEW_FREEZE = (
    PLANNING_DOCS / "163_RENDERED_RESULT_REVIEW_FREEZE.md"
)
RENDERED_RESULT_REVIEW_CONTRACT = (
    PLANNING_DOCS / "164_RENDERED_RESULT_REVIEW_CONTRACT.md"
)
RENDERED_RESULT_REVIEW_PROOF = (
    PLANNING_DOCS / "165_RENDERED_RESULT_REVIEW_PROOF.md"
)
RENDERED_PACKAGE_REVIEW_FREEZE = (
    PLANNING_DOCS / "166_RENDERED_PACKAGE_REVIEW_FREEZE.md"
)
RENDERED_PACKAGE_REVIEW_CONTRACT = (
    PLANNING_DOCS / "167_RENDERED_PACKAGE_REVIEW_CONTRACT.md"
)
RENDERED_PACKAGE_REVIEW_PROOF = (
    PLANNING_DOCS / "168_RENDERED_PACKAGE_REVIEW_PROOF.md"
)
RENDERED_HANDOFF_EXPORT_FREEZE = (
    PLANNING_DOCS / "169_RENDERED_HANDOFF_EXPORT_FREEZE.md"
)
RENDERED_HANDOFF_EXPORT_CONTRACT = (
    PLANNING_DOCS / "170_RENDERED_HANDOFF_EXPORT_CONTRACT.md"
)
RENDERED_HANDOFF_EXPORT_PROOF = (
    PLANNING_DOCS / "171_RENDERED_HANDOFF_EXPORT_PROOF.md"
)
RENDERED_APS_HANDOFF_FREEZE = (
    PLANNING_DOCS / "172_RENDERED_APS_HANDOFF_FREEZE.md"
)
RENDERED_APS_HANDOFF_CONTRACT = (
    PLANNING_DOCS / "173_RENDERED_APS_HANDOFF_CONTRACT.md"
)
RENDERED_APS_HANDOFF_PROOF = (
    PLANNING_DOCS / "174_RENDERED_APS_HANDOFF_PROOF.md"
)
RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FREEZE = (
    PLANNING_DOCS / "175_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FREEZE.md"
)
RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_CONTRACT = (
    PLANNING_DOCS / "176_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_CONTRACT.md"
)
RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PROOF = (
    PLANNING_DOCS / "177_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PROOF.md"
)
RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE = (
    PLANNING_DOCS / "178_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md"
)
RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT = (
    PLANNING_DOCS / "179_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT.md"
)
RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PROOF = (
    PLANNING_DOCS / "180_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PROOF.md"
)
RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_FREEZE = (
    PLANNING_DOCS / "181_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_FREEZE.md"
)
RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_CONTRACT = (
    PLANNING_DOCS / "182_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_CONTRACT.md"
)
RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF = (
    PLANNING_DOCS / "183_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF.md"
)
POST_745_DOWNSTREAM_EXPANSION_FREEZE = (
    PLANNING_DOCS / "184_POST_745_DOWNSTREAM_EXPANSION_FREEZE.md"
)
POST_745_DOWNSTREAM_EXPANSION_CONTRACT = (
    PLANNING_DOCS / "185_POST_745_DOWNSTREAM_EXPANSION_CONTRACT.md"
)
PROVIDER_PUBLIC_URL_ENTRY_FREEZE = (
    PLANNING_DOCS / "187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md"
)
PROVIDER_PUBLIC_URL_ENTRY_CONTRACT = (
    PLANNING_DOCS / "188_PROVIDER_PUBLIC_URL_ENTRY_CONTRACT.md"
)
QUAL_HYBRID_RAG_FREEZE = PLANNING_DOCS / "124_QUAL_HYBRID_RAG_FREEZE.md"
MOCKUP_TRUTH_FREEZE = PLANNING_DOCS / "125_MOCKUP_TRUTH_STATE_FREEZE.md"
PACKAGE_COMMIT_FREEZE = PLANNING_DOCS / "126_PACKAGE_COMMIT_FREEZE.md"
PACKAGE_REPLACEMENT_SET_FREEZE = PLANNING_DOCS / "127_PACKAGE_REPLACEMENT_SET_FREEZE.md"
PACKAGE_REPLACEMENT_ARTIFACT_FREEZE = (
    PLANNING_DOCS / "128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md"
)
PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE = (
    PLANNING_DOCS / "129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md"
)
PACKAGE_REPLACEMENT_NAMESPACE_FREEZE = (
    PLANNING_DOCS / "130_PACKAGE_REPLACEMENT_NAMESPACE_FREEZE.md"
)
PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE = (
    PLANNING_DOCS / "131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE.md"
)
PLAN_REVISION_RECOVERY_FREEZE = (
    PLANNING_DOCS / "132_PLAN_REVISION_RECOVERY_FREEZE.md"
)
PLAN_REVISION_RECOVERY_CONTRACT = (
    PLANNING_DOCS / "133_PLAN_REVISION_RECOVERY_CONTRACT.md"
)
PLAN_REVISION_RECOVERY_ENTRY_FREEZE = (
    PLANNING_DOCS / "134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md"
)
PLAN_REVISION_RECOVERY_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_plan_revision_recovery.py"
)
APPROVED_PLAN_CORRECTION_FREEZE = (
    PLANNING_DOCS / "135_APPROVED_PLAN_CORRECTION_FREEZE.md"
)
APPROVED_PLAN_CANCEL_ENTRY_FREEZE = (
    PLANNING_DOCS / "136_APPROVED_PLAN_CANCEL_ENTRY_FREEZE.md"
)
APPROVED_PLAN_CORRECTION_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_approved_plan_correction.py"
)
APPROVED_PLAN_CORRECTION_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_approved_plan_correction.py"
)
STATE_ACTION_CONTRACT = (
    ROOT / "backend" / "app" / "services" / "layer3_state_action_contract.py"
)
STATE_MODEL_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_state_model_contract.py"
)
PLAN_FLOW_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_plan_flow_contract.py"
)
PLAN_FLOW_STATE_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_plan_flow_state.py"
PLAN_FLOW_READINESS_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_plan_flow_readiness.py"
)
SUBLAYER_STATE_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_sublayer_state.py"
EXECUTION_STATE_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_execution_state.py"
EXECUTION_OUTPUT_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_execution_output.py"
EXECUTION_REVIEW_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_execution_review.py"
EXECUTION_SELECTION_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_execution_selection.py"
EXECUTION_START_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_execution_start.py"
EXECUTION_STATUS_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_execution_status.py"
EXECUTION_REQUEST_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_execution_request_contract.py"
)
HANDOFF_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_handoff_contract.py"
)
APS_HANDOFF_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_aps_handoff.py"
PACKAGE_REVIEW_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_package_review_contract.py"
)
PACKAGE_SUBMIT_RESPONSE_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_package_submit_response.py"
)
HANDOFF_EXPORT_RESPONSE_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_handoff_export_response.py"
)
EXTERNAL_EXPORT_RESPONSE_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_external_export_response.py"
)
WORKBENCH_PACKAGE_STATE_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_workbench_package_state.py"
)
PLAN_ERROR_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_plan_errors.py"
)
EXECUTION_ERROR_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_execution_errors.py"
)
EXTERNAL_EXPORT_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_external_export_contract.py"
)
SESSION_ENTRY_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0012_layer3_session_entry.py"
)
GATE_B_IDEMPOTENCY_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0017_layer3_gate_b_idempotency.py"
)
PASS_ENTRY_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0014_layer3_pass_entry.py"
)
REPLACEMENT_PACKAGE_SET_AUTHORITY_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0018_layer3_replacement_package_set_authority.py"
)
PACKAGE_SUPERSESSION_COMMIT_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0019_layer3_package_supersession_commit.py"
)
PACKAGE_ENTRY_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0015_layer3_package_entry.py"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0020_layer3_replacement_package_artifact_manifest.py"
)
REPLACEMENT_PACKAGE_NAMESPACE_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0021_layer3_replacement_output_package.py"
)
LAYER3_API = ROOT / "backend" / "app" / "api" / "layer3.py"
MODELS = ROOT / "backend" / "app" / "models" / "models.py"
SOURCE_BOUNDARY_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_source_boundary.py"
)
RAW_MIXED_BRIDGE_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_raw_mixed_bridge.py"
)
RAW_MIXED_MATERIALIZATION_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_raw_mixed_materialization.py"
)
PREFLIGHT_REQUEST_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_preflight_request_contract.py"
)
APS_SOURCE_FAMILY_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_aps_source_family.py"
)
GATE_B_STATE_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_gate_b_state.py"
)
SIGNED_REFERENCE_STATE_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_signed_reference_state.py"
)
WORKBENCH_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_workbench.py"
)
PACKAGE_ENTRY_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_package_entry.py"
)
RESPONSE_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_response_contract.py"
)
WORKBENCH_ERROR_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_workbench_error.py"
)
AUTHORITY_RAIL_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_authority_rail.py"
)
PREVIEW_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_preview_contract.py"
)
READINESS_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_readiness_contract.py"
)
BOOTSTRAP_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_bootstrap_contract.py"
)
CONNECTOR_DISPATCH_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_connector_dispatch_entry.py"
)
PACKAGE_MUTATION_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_package_mutation_entry.py"
)
REPLACEMENT_PACKAGE_SET_AUTHORITY_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_replacement_package_set_authority.py"
)
PACKAGE_SUPERSESSION_COMMIT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_package_supersession_commit.py"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_replacement_package_artifact_manifest.py"
)
REPLACEMENT_PACKAGE_NAMESPACE_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_replacement_package_namespace.py"
)
QUAL_APS_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_qual_aps_execution.py"
MOCKUP_BOUNDARY_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_mockup_boundary.py"
SOURCE_BOUNDARY_TEST = ROOT / "backend" / "tests" / "test_layer3_source_boundary.py"
PREFLIGHT_REQUEST_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_preflight_request_contract.py"
)
APS_SOURCE_FAMILY_TEST = ROOT / "backend" / "tests" / "test_layer3_aps_source_family.py"
RAW_MIXED_BRIDGE_TEST = ROOT / "backend" / "tests" / "test_layer3_raw_mixed_bridge.py"
RAW_MIXED_MATERIALIZATION_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_raw_mixed_materialization.py"
)
QUAL_APS_TEST = ROOT / "backend" / "tests" / "test_layer3_qual_aps_execution.py"
MOCKUP_BOUNDARY_TEST = ROOT / "backend" / "tests" / "test_layer3_mockup_boundary.py"
SESSION_ENTRY_TEST = ROOT / "backend" / "tests" / "test_layer3_session_entry.py"
PLAN_PASS_STATUS_CONSTRAINT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_plan_pass_status_constraints.py"
)
GATE_B_STATE_TEST = ROOT / "backend" / "tests" / "test_layer3_gate_b_state.py"
REPLACEMENT_PACKAGE_SET_AUTHORITY_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_replacement_package_set_authority.py"
)
PACKAGE_SUPERSESSION_COMMIT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_package_supersession_commit.py"
)
REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_replacement_package_artifact_manifest.py"
)
REPLACEMENT_PACKAGE_NAMESPACE_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_replacement_package_namespace.py"
)
SIGNED_REFERENCE_STATE_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_signed_reference_state.py"
)
LAYER3_API_TEST = ROOT / "backend" / "tests" / "test_layer3_api.py"
LAYER3_BOUNDED_E2E_TEST = ROOT / "backend" / "tests" / "test_layer3_bounded_e2e.py"
LAYER3_PAGE_TEST = ROOT / "backend" / "tests" / "test_layer3_page.py"
LAYER3_RESPONSE_CONTRACT_TEST = ROOT / "backend" / "tests" / "test_layer3_response_contract.py"
LAYER3_WORKBENCH_ERROR_TEST = ROOT / "backend" / "tests" / "test_layer3_workbench_error.py"
LAYER3_AUTHORITY_RAIL_TEST = ROOT / "backend" / "tests" / "test_layer3_authority_rail.py"
LAYER3_PREVIEW_CONTRACT_TEST = ROOT / "backend" / "tests" / "test_layer3_preview_contract.py"
LAYER3_READINESS_CONTRACT_TEST = ROOT / "backend" / "tests" / "test_layer3_readiness_contract.py"
LAYER3_BOOTSTRAP_CONTRACT_TEST = ROOT / "backend" / "tests" / "test_layer3_bootstrap_contract.py"
LAYER3_STATE_MODEL_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_state_model_contract.py"
)
LAYER3_PLAN_FLOW_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_plan_flow_contract.py"
)
LAYER3_PLAN_FLOW_STATE_TEST = ROOT / "backend" / "tests" / "test_layer3_plan_flow_state.py"
LAYER3_PLAN_FLOW_READINESS_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_plan_flow_readiness.py"
)
LAYER3_SUBLAYER_STATE_TEST = ROOT / "backend" / "tests" / "test_layer3_sublayer_state.py"
LAYER3_EXECUTION_STATE_TEST = ROOT / "backend" / "tests" / "test_layer3_execution_state.py"
LAYER3_EXECUTION_OUTPUT_TEST = ROOT / "backend" / "tests" / "test_layer3_execution_output.py"
LAYER3_EXECUTION_REVIEW_TEST = ROOT / "backend" / "tests" / "test_layer3_execution_review.py"
LAYER3_EXECUTION_SELECTION_TEST = ROOT / "backend" / "tests" / "test_layer3_execution_selection.py"
LAYER3_EXECUTION_START_TEST = ROOT / "backend" / "tests" / "test_layer3_execution_start.py"
LAYER3_EXECUTION_STATUS_TEST = ROOT / "backend" / "tests" / "test_layer3_execution_status.py"
LAYER3_EXECUTION_REQUEST_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_execution_request_contract.py"
)
LAYER3_HANDOFF_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_handoff_contract.py"
)
LAYER3_PACKAGE_REVIEW_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_package_review_contract.py"
)
LAYER3_PACKAGE_SUBMIT_RESPONSE_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_package_submit_response.py"
)
LAYER3_HANDOFF_EXPORT_RESPONSE_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_handoff_export_response.py"
)
LAYER3_EXTERNAL_EXPORT_RESPONSE_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_external_export_response.py"
)
LAYER3_WORKBENCH_PACKAGE_STATE_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_workbench_package_state.py"
)
LAYER3_PLAN_ERROR_TEST = ROOT / "backend" / "tests" / "test_layer3_plan_errors.py"
LAYER3_EXECUTION_ERROR_TEST = ROOT / "backend" / "tests" / "test_layer3_execution_errors.py"
LAYER3_EXTERNAL_EXPORT_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_external_export_contract.py"
)
LAYER3_STATIC = ROOT / "backend" / "app" / "review_ui" / "static"
LAYER3_HTML = LAYER3_STATIC / "layer3.html"
LAYER3_CSS = LAYER3_STATIC / "layer3.css"
LAYER3_JS = LAYER3_STATIC / "layer3.js"
LAYER3_WORKBENCH_E2E = ROOT / "e2e" / "layer3-workbench.spec.js"
LAYER3_FLOW_E2E = ROOT / "e2e" / "layer3-flow.spec.js"
LAYER3_HANDOFF_E2E = ROOT / "e2e" / "layer3-handoff.spec.js"
LAYER3_HELPERS_E2E = ROOT / "e2e" / "layer3-helpers.js"
REVIEW_BROWSER_SERVER = ROOT / "backend" / "tests" / "review_browser_server.py"
MOCKUP_ASSETS = ROOT / "next_milestone_plans" / "layer3-mockups" / "assets.md"
MOCKUP_SPEC = ROOT / "next_milestone_plans" / "layer3-mockups" / "mockup-spec.txt"

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing required JSON file: {_rel(path)}")
        return {}
    if path.stat().st_size == 0:
        errors.append(f"empty required JSON file: {_rel(path)}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {_rel(path)}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"JSON root must be an object: {_rel(path)}")
        return {}
    return payload


def _read_required_text(path: Path, errors: list[str]) -> str:
    if not path.exists():
        errors.append(f"missing required text file: {_rel(path)}")
        return ""
    if path.is_file() and path.stat().st_size == 0:
        errors.append(f"empty required text file: {_rel(path)}")
        return ""
    return path.read_text(encoding="utf-8")


def _load_literal_assignment(path: Path, name: str, errors: list[str]) -> Any:
    text = _read_required_text(path, errors)
    if not text:
        return None
    try:
        module = ast.parse(text, filename=_rel(path))
    except SyntaxError as exc:
        errors.append(f"cannot parse Python source for {_rel(path)}: {exc}")
        return None

    for node in module.body:
        value_node = None
        target_names: list[str] = []
        if isinstance(node, ast.Assign):
            value_node = node.value
            target_names = [
                target.id for target in node.targets if isinstance(target, ast.Name)
            ]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value_node = node.value
            target_names = [node.target.id]
        if name not in target_names or value_node is None:
            continue
        try:
            return ast.literal_eval(value_node)
        except (SyntaxError, ValueError) as exc:
            errors.append(f"{_rel(path)} {name} must be a literal assignment: {exc}")
            return None

    errors.append(f"{_rel(path)} missing literal assignment: {name}")
    return None


def _capability_map(value: Any, name: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        errors.append(f"{name} must be a list or tuple of capability objects")
        return {}

    capabilities: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict):
            errors.append(f"{name} contains a non-object entry: {item!r}")
            continue
        capability = item.get("capability")
        if not isinstance(capability, str) or not capability:
            errors.append(f"{name} contains an entry without a capability id: {item!r}")
            continue
        if capability in capabilities:
            errors.append(f"{name} contains duplicate capability id: {capability}")
        capabilities[capability] = item
    return capabilities


def _require_file(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"missing required file: {_rel(path)}")
    elif path.is_file() and path.stat().st_size == 0:
        errors.append(f"empty required file: {_rel(path)}")


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _markdown_section(text: str, heading: str) -> str | None:
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        return None
    body_start = start + len(marker)
    next_heading = text.find("\n## ", body_start)
    if next_heading == -1:
        return text[body_start:]
    return text[body_start:next_heading]


def _check_snapshot_consistency(manifest: dict[str, Any], errors: list[str]) -> None:
    snapshot_values = {
        "snapshot_base_main_commit": manifest.get("snapshot_base_main_commit"),
        "artifact_scope.snapshot_base_main_commit": _nested(
            manifest, "artifact_scope", "snapshot_base_main_commit"
        ),
        "current_snapshot.snapshot_base_main_commit": _nested(
            manifest, "current_snapshot", "snapshot_base_main_commit"
        ),
    }
    missing = [name for name, value in snapshot_values.items() if not value]
    if missing:
        errors.append("missing snapshot commit fields: " + ", ".join(missing))
        return

    bad_shape = [
        f"{name}={value}"
        for name, value in snapshot_values.items()
        if not isinstance(value, str) or not COMMIT_RE.match(value)
    ]
    if bad_shape:
        errors.append("snapshot commit fields must be 40-char lowercase SHA values: " + "; ".join(bad_shape))

    unique_values = {str(value) for value in snapshot_values.values()}
    if len(unique_values) != 1:
        detail = ", ".join(f"{name}={value}" for name, value in snapshot_values.items())
        errors.append("snapshot commit fields disagree: " + detail)


def _check_latest_progress_sync(
    manifest: dict[str, Any], errors: list[str]
) -> None:
    expected_commit = "ad51b1c6736cd51ec3dd30de914e59ddb4c66158"
    snapshot_values = {
        "snapshot_base_main_commit": manifest.get("snapshot_base_main_commit"),
        "artifact_scope.snapshot_base_main_commit": _nested(
            manifest, "artifact_scope", "snapshot_base_main_commit"
        ),
        "current_snapshot.snapshot_base_main_commit": _nested(
            manifest, "current_snapshot", "snapshot_base_main_commit"
        ),
    }
    for name, value in snapshot_values.items():
        if value != expected_commit:
            errors.append(
                f"{name} must identify the post-PR609 current-main "
                f"APS source-family extraction proof boundary {expected_commit}"
            )

    for name, source in (
        (
            "artifact_scope.snapshot_base_main_commit_source",
            _nested(manifest, "artifact_scope", "snapshot_base_main_commit_source"),
        ),
        (
            "current_snapshot.snapshot_base_main_commit_source",
            _nested(manifest, "current_snapshot", "snapshot_base_main_commit_source"),
        ),
    ):
        if not isinstance(source, str):
            errors.append(f"{name} must be present after PR609 APS source-family extraction")
            continue
        for term in (
            expected_commit,
            "after PR #609",
            "APS source-family extraction",
            "codex/l3-synth-ref-sync",
        ):
            if term not in source:
                errors.append(f"{name} missing PR609 progress-sync term: {term}")

    namespace_runtime = manifest.get("package_replacement_namespace_runtime")
    if not isinstance(namespace_runtime, dict):
        errors.append("manifest missing package_replacement_namespace_runtime object")
    else:
        expected_fields = {
            "mode": "replacement_package_namespace_rows",
            "source_gate": "131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE",
            "live_behavior_change": True,
            "route": "/api/v1/layer3/package/replacement-namespace/record",
            "owner_service": "backend/app/services/layer3_replacement_package_namespace.py",
            "model": "L3ReplacementOutputPackage",
            "table": "l3_replacement_output_package",
            "migration": "backend/alembic/versions/0021_layer3_replacement_output_package.py",
            "request_dto": "Layer3ReplacementPackageNamespaceRecordRequest",
            "response_dto": "Layer3ReplacementPackageNamespaceRecordResponse",
            "implementation_pr": "#593",
        }
        for key, expected in expected_fields.items():
            if namespace_runtime.get(key) != expected:
                errors.append(
                    "package_replacement_namespace_runtime."
                    f"{key}={namespace_runtime.get(key)!r} but expected {expected!r}"
                )
        blocked_scope = namespace_runtime.get("blocked_scope")
        if not isinstance(blocked_scope, list):
            errors.append("package_replacement_namespace_runtime missing blocked_scope")
        else:
            for blocked in (
                "source L3OutputPackage row creation, update, or deletion",
                "package payload write",
                "package payload rewrite",
                "replacement package artifact generation",
                "provider/public URL support",
                "connector/destination dispatch",
                "broad qualitative/hybrid/RAG execution",
                "full mockup activation",
                "authentication/security hardening",
                "broad package mutation/reconstruction",
            ):
                if blocked not in blocked_scope:
                    errors.append(
                        "package_replacement_namespace_runtime.blocked_scope "
                        f"missing {blocked}"
                    )

    stale_scope_text = "\n".join(
        str(item)
        for collection in (
            _nested(manifest, "artifact_scope", "notes"),
            _nested(manifest, "artifact_scope", "state_notes"),
        )
        if isinstance(collection, list)
        for item in collection
    )
    for stale in (
        "future contract terms only",
        "does not admit runtime route creation",
        "This implementation-entry slice adds `131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE.md`",
    ):
        if stale in stale_scope_text:
            errors.append(
                "artifact_scope package namespace runtime notes still contain "
                f"stale future-only wording: {stale}"
            )

    required_summary_terms = {
        "branch_state_summary": manifest.get("branch_state_summary"),
        "current_snapshot.branch_state_summary": _nested(
            manifest, "current_snapshot", "branch_state_summary"
        ),
    }
    for name, summary in required_summary_terms.items():
        if not isinstance(summary, str):
            errors.append(f"{name} must be present after package namespace runtime sync")
            continue
        for term in (
            "PR #593",
            "bounded live `replacement_package_namespace_rows` runtime",
            "separate `l3_replacement_output_package` metadata rows",
            "broad package mutation/reconstruction remains blocked",
        ):
            if term not in summary:
                errors.append(f"{name} missing package namespace runtime sync term: {term}")
        for stale in (
            "namespace implementation-entry freeze",
            "replacement_package_namespace_rows` as implementation-entry",
            "doc `131` governs only implementation-entry",
        ):
            if stale in summary:
                errors.append(f"{name} still describes namespace runtime as implementation-entry: {stale}")
        for term in (
            "bounded live `approved_plan_cancel_without_replacement` runtime",
            "POST /api/v1/layer3/plan/approved/cancel",
            "existing approved `L3AnalysisPlan` row",
            "no replacement plan",
        ):
            if term not in summary:
                errors.append(f"{name} missing approved-plan cancel runtime sync term: {term}")


def _check_summary_counts(manifest: dict[str, Any], errors: list[str]) -> None:
    summary = manifest.get("summary_counts")
    slices = manifest.get("layer3_workbench_slices")
    if not isinstance(summary, dict):
        errors.append("summary_counts must be present as an object")
        return
    if not isinstance(slices, list) or not slices:
        errors.append("layer3_workbench_slices must be a non-empty list")
        return

    planning = 0
    live = 0
    branch_only_implementation = 0
    malformed = 0
    for item in slices:
        if not isinstance(item, dict):
            malformed += 1
            continue
        state = item.get("main_state")
        if not isinstance(state, str):
            malformed += 1
            continue
        if "planning_only" in state:
            planning += 1
        if "live_bounded" in state:
            live += 1
        if state.startswith("branch_only_implementation"):
            branch_only_implementation += 1

    if malformed:
        errors.append(f"layer3_workbench_slices contains malformed records: {malformed}")

    expected = {
        "workbench_slice_records": len(slices),
        "workbench_planning_only_slices": planning,
        "workbench_live_bounded_slices": live,
        "workbench_branch_only_implementation_slices": branch_only_implementation,
    }
    for key, actual in expected.items():
        recorded = summary.get(key)
        if recorded != actual:
            errors.append(f"summary_counts.{key}={recorded!r} but computed {actual}")


def _check_current_decision(manifest: dict[str, Any], errors: list[str]) -> None:
    decision = manifest.get("layer3_workbench_current_decision")
    slices = manifest.get("layer3_workbench_slices")
    if not isinstance(decision, dict):
        errors.append("layer3_workbench_current_decision must be present as an object")
        return
    if not isinstance(slices, list):
        return

    state = decision.get("state")
    if not isinstance(state, str) or not state:
        errors.append("layer3_workbench_current_decision.state must be a non-empty string")
        return

    matching = [
        item
        for item in slices
        if isinstance(item, dict) and item.get("main_state") == state
    ]
    if len(matching) != 1:
        errors.append(
            "layer3_workbench_current_decision.state must match exactly one "
            f"layer3_workbench_slices main_state; found {len(matching)} for {state!r}"
        )

    next_required = decision.get("next_required_decision")
    if not isinstance(next_required, str) or not next_required:
        errors.append("layer3_workbench_current_decision.next_required_decision must be a non-empty string")
    else:
        required_terms = [
            (
                "After direct owner-service proof hardening for "
                "plan_revision_recovery_preview_refresh_entry and "
                "approved_plan_cancel_without_replacement"
            ),
            "keep remaining authentication/security",
            "approved-plan supersession runtime",
            "no-behavior-change service extraction",
            "proof/state drift checker",
        ]
        for term in required_terms:
            if term not in next_required:
                errors.append(f"next_required_decision missing local near-term direction term: {term}")
        stale_terms = [
            "future runtime implementation for exactly approved_plan_cancel_without_replacement",
            "approved_plan_cancel_without_replacement as implementation-entry only",
        ]
        for term in stale_terms:
            if term in next_required:
                errors.append(f"next_required_decision still contains stale cancel-runtime wording: {term}")

    allowed_actions = decision.get("next_allowed_actions")
    if not isinstance(allowed_actions, list) or not allowed_actions:
        errors.append("layer3_workbench_current_decision.next_allowed_actions must be a non-empty list")
        return
    allowed_text = "\n".join(str(item) for item in allowed_actions)
    required_allowed = [
        "progress/proof/state drift checker",
        "state/action contract drift checker",
        "preview hash/idempotency follow-up",
        (
            "plan revision recovery or approved-plan cancel owner-service "
            "proof maintenance only if fresh drift appears"
        ),
        "no-behavior-change service extraction",
        "future implementation-entry freeze",
    ]
    for term in required_allowed:
        if term not in allowed_text:
            errors.append(f"next_allowed_actions missing non-security option: {term}")
    blocked_allowed = [
        "provider/public URL implementation-entry",
        "connector/destination implementation-entry",
        "qualitative APS execution implementation-entry",
        "auth implementation",
        "upload security hardening",
        "signed-reference security hardening",
    ]
    for term in blocked_allowed:
        if term in allowed_text:
            errors.append(f"next_allowed_actions still includes blocked near-term option: {term}")
    stale_allowed = [
        "future runtime implementation for exactly approved_plan_cancel_without_replacement",
    ]
    for term in stale_allowed:
        if term in allowed_text:
            errors.append(f"next_allowed_actions still treats approved-plan cancel runtime as future: {term}")


def _check_plan_revision_recovery_freeze(manifest: dict[str, Any], errors: list[str]) -> None:
    freeze_text = _read_required_text(PLAN_REVISION_RECOVERY_FREEZE, errors)
    contract_text = _read_required_text(PLAN_REVISION_RECOVERY_CONTRACT, errors)

    required_freeze_terms = [
        "Status: planning/control freeze only for `plan_revision_recovery_lifecycle`",
        "selected_future_lifecycle_mode: `plan_revision_recovery_lifecycle`",
        "selected_recovery_posture: `server_authorized_preview_refresh_only`",
        "No runtime behavior is admitted by this document.",
        "must not reopen, replace, supersede, or delete an already approved `L3AnalysisPlan`",
        "plan_rejected",
        "plan_revision_requested",
        "allowed_next_actions: []",
        "frontend-only durable state",
        "authentication/security hardening",
    ]
    for term in required_freeze_terms:
        if term not in freeze_text:
            errors.append(f"{_rel(PLAN_REVISION_RECOVERY_FREEZE)} missing recovery freeze term: {term}")

    required_contract_terms = [
        "Status: planning/control API and state contract for `132_PLAN_REVISION_RECOVERY_FREEZE.md`",
        "POST /api/v1/layer3/plan/revision/recover",
        "layer3.plan_revision_recovery_request.v1",
        "recover_for_preview_refresh",
        "layer3.plan_revision_recovery_result.v1",
        "plan_revision_recovery_not_available",
        "plan_revision_state_mismatch",
        "plan_already_approved",
        "pass_runs_already_exist",
        "frontend-only durable state",
        "authentication/security hardening",
    ]
    for term in required_contract_terms:
        if term not in contract_text:
            errors.append(f"{_rel(PLAN_REVISION_RECOVERY_CONTRACT)} missing recovery contract term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: [
            "132_PLAN_REVISION_RECOVERY_FREEZE.md",
            "133_PLAN_REVISION_RECOVERY_CONTRACT.md",
            "planning/control authority for `plan_revision_recovery_lifecycle`",
            "doc `134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md` now governs only the live bounded `plan_revision_recovery_preview_refresh_entry` runtime",
        ],
        SYNTHESIS_BOUNDARY: [
            "132_PLAN_REVISION_RECOVERY_FREEZE.md",
            "133_PLAN_REVISION_RECOVERY_CONTRACT.md",
            "planning/control authority for the broader `plan_revision_recovery_lifecycle` question",
            "134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md` now governs the live bounded `plan_revision_recovery_preview_refresh_entry` runtime",
        ],
        GOAL_AUDIT: [
            "132_PLAN_REVISION_RECOVERY_FREEZE.md",
            "Plan revision recovery lifecycle",
            "Bounded preview-refresh runtime live",
            "Only `plan_revision_recovery_preview_refresh_entry` is admitted",
        ],
        CLOSEOUT_DOC: [
            "planning/control plan revision recovery freeze",
            "plan_revision_recovery_lifecycle",
            "bounded plan revision recovery preview-refresh runtime",
            "approved-plan supersession",
        ],
        BOARD: [
            "plan_revision_recovery_lifecycle",
            "Plan revision recovery lifecycle freeze",
            "Plan revision recovery preview-refresh runtime",
            "doc `134` runtime",
        ],
        PROOF_MANIFEST: [
            "plan_revision_recovery_freeze_proof",
            "latest_plan_revision_recovery_freeze_pr",
            "15c8ab17a42718da549974bea97073d5d4b940b4",
            "planning/control authority for `plan_revision_recovery_lifecycle` only",
            "no runtime recovery",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing revision recovery term: {term}")

    next_required = manifest.get("next_required_decision")
    if not isinstance(next_required, str):
        errors.append("manifest next_required_decision missing for revision recovery freeze")
    else:
        for term in (
            "After the bounded plan_revision_recovery_preview_refresh_entry runtime",
            "approved-plan supersession",
            "separate freeze and proof plan",
        ):
            if term not in next_required:
                errors.append(f"manifest next_required_decision missing revision recovery term: {term}")

    slices = manifest.get("layer3_workbench_slices")
    if not isinstance(slices, list):
        errors.append("layer3_workbench_slices missing for revision recovery freeze")
    else:
        matches = [
            item
            for item in slices
            if isinstance(item, dict)
            and item.get("slice_id") == "plan-revision-recovery-lifecycle-freeze"
        ]
        if len(matches) != 1:
            errors.append(
                "layer3_workbench_slices must contain exactly one "
                "plan-revision-recovery-lifecycle-freeze record"
            )
        else:
            item = matches[0]
            if (
                item.get("main_state")
                != "planning_only_plan_revision_recovery_lifecycle_with_bounded_preview_refresh_runtime"
            ):
                errors.append(
                    "revision recovery lifecycle slice must acknowledge bounded preview-refresh runtime"
                )
            docs = item.get("governing_docs")
            if not isinstance(docs, list):
                errors.append("revision recovery slice missing governing_docs")
            else:
                for doc in (
                    "next_milestone_plans/Layer3_planning_docs/132_PLAN_REVISION_RECOVERY_FREEZE.md",
                    "next_milestone_plans/Layer3_planning_docs/133_PLAN_REVISION_RECOVERY_CONTRACT.md",
                    "tools/l3-progress-check.py",
                ):
                    if doc not in docs:
                        errors.append(f"revision recovery slice governing_docs missing {doc}")
            explicit_non_goals = item.get("explicit_non_goals")
            if not isinstance(explicit_non_goals, list):
                errors.append("revision recovery slice missing explicit_non_goals")
            else:
                for blocked in (
                    "approved-plan reopening, cancellation, deletion, replacement, or supersession",
                    "L3PassRun creation",
                    "AnalysisRun creation",
                    "connector/destination dispatch",
                    "broad qualitative/hybrid/RAG execution",
                    "authentication/security hardening",
                ):
                    if blocked not in explicit_non_goals:
                        errors.append(f"revision recovery explicit_non_goals missing {blocked}")

    state_model_text = _read_required_text(STATE_MODEL_CONTRACT_SERVICE, errors)
    for state in ("plan_rejected", "plan_revision_requested"):
        marker = f'"state": "{state}"'
        location = state_model_text.find(marker)
        if location == -1:
            errors.append(f"state model missing revision terminal state {state}")
            continue
        window = state_model_text[location : location + 350]
        if '"allowed_next_actions": ["plan_revision_recover"]' not in window:
            errors.append(f"state model must expose only plan_revision_recover from {state}")


def _check_plan_revision_recovery_entry_freeze(
    manifest: dict[str, Any], errors: list[str]
) -> None:
    entry_text = _read_required_text(PLAN_REVISION_RECOVERY_ENTRY_FREEZE, errors)
    required_entry_terms = [
        "Status: bounded runtime contract for `plan_revision_recovery_preview_refresh_entry`",
        "POST /api/v1/layer3/plan/revision/recover",
        "backend/app/services/layer3_plan_revision_recovery.py",
        "Layer3PlanRevisionRecoveryRequest",
        "Layer3PlanRevisionRecoveryResponse",
        "layer3.plan_revision_recovery_request.v1",
        "layer3.plan_revision_recovery_result.v1",
        "layer3.plan_revision_recovery_preview_refresh.v1",
        "existing `L3Session.summary_json` only",
        "allowed_next_actions: [\"plan_revision_recover\"]",
        "plan_revision_recovery_not_available",
        "pass_runs_already_exist",
        "fresh server-backed plan preview",
        "authentication/security hardening",
    ]
    for term in required_entry_terms:
        if term not in entry_text:
            errors.append(f"{_rel(PLAN_REVISION_RECOVERY_ENTRY_FREEZE)} missing entry-freeze term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: [
            "134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md",
            "bounded runtime contract for `plan_revision_recovery_preview_refresh_entry`",
            "summary-state recovery metadata in existing `L3Session.summary_json`",
        ],
        SYNTHESIS_BOUNDARY: [
            "134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md",
            "plan_revision_recovery_preview_refresh_entry",
            "live bounded `plan_revision_recovery_preview_refresh_entry` runtime",
            "allowed_next_actions: [\"plan_revision_recover\"]",
        ],
        GOAL_AUDIT: [
            "134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md",
            "bounded runtime for `plan_revision_recovery_preview_refresh_entry`",
            "Bounded preview-refresh runtime live",
            "Only `plan_revision_recovery_preview_refresh_entry` is admitted",
        ],
        CLOSEOUT_DOC: [
            "134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md",
            "plan_revision_recovery_preview_refresh_entry",
            "Bounded preview-refresh runtime live",
            "PR `#605` merge commit `db7c7a0811a8e1a1343a4b285dec050a03e4361b`",
        ],
        BOARD: [
            "Plan revision recovery preview-refresh runtime",
            "live bounded runtime",
            "134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md",
            "POST /api/v1/layer3/plan/revision/recover",
            "backend/app/services/layer3_plan_revision_recovery.py",
            "PR `#605`",
            "db7c7a0811a8e1a1343a4b285dec050a03e4361b",
            "doc `134` runtime, PR `#605` proof",
        ],
        PROOF_MANIFEST: [
            "plan_revision_recovery_runtime_proof",
            "latest_plan_revision_recovery_runtime_branch",
            "latest_plan_revision_recovery_runtime_pr",
            "#599",
            "51e5abcbcdd2070c47b3aeba73032db081be41f7",
            "1e74a739a07623b7d91d405d946e6b1d221be6ff",
            "Bounded runtime for plan_revision_recovery_preview_refresh_entry",
            "summary-state recovery metadata",
            "latest_plan_revision_recovery_service_proof_pr",
            "#605",
            "95b597a22ac7fa89d0df27ae1e3952b2f691e065",
            "db7c7a0811a8e1a1343a4b285dec050a03e4361b",
            "owner authority row-count stability",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing revision recovery entry term: {term}")

    proof_manifest = _load_json(PROOF_MANIFEST, errors)
    proof_scope = proof_manifest.get("scope") if isinstance(proof_manifest, dict) else None
    if not isinstance(proof_scope, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} scope missing for revision recovery runtime")
    else:
        expected_top_scope = {
            "merged_pr": "#609",
            "merge_commit": "ad51b1c6736cd51ec3dd30de914e59ddb4c66158",
            "source_branch": "codex/l3-synth-ref-sync",
            "base_commit": "ad51b1c6736cd51ec3dd30de914e59ddb4c66158",
            "source_base_commit": "ad51b1c6736cd51ec3dd30de914e59ddb4c66158",
        }
        for key, value in expected_top_scope.items():
            if proof_scope.get(key) != value:
                errors.append(f"{_rel(PROOF_MANIFEST)} scope.{key} must be {value!r}")
        expected_runtime_scope = {
            "latest_plan_revision_recovery_runtime_branch": "codex/l3-revision-recovery-runtime",
            "latest_plan_revision_recovery_runtime_pr": "#599",
            "latest_plan_revision_recovery_runtime_merge_commit": "1e74a739a07623b7d91d405d946e6b1d221be6ff",
            "latest_plan_revision_recovery_runtime_base_commit": "47aef2ee13e173121c3738e63bafbe86e360c280",
            "latest_plan_revision_recovery_runtime_head_commit": "51e5abcbcdd2070c47b3aeba73032db081be41f7",
            "latest_plan_revision_recovery_runtime_live_behavior_change": True,
        }
        for key, value in expected_runtime_scope.items():
            if proof_scope.get(key) != value:
                errors.append(f"{_rel(PROOF_MANIFEST)} scope.{key} must be {value!r}")
        latest_summary = proof_scope.get("latest_plan_revision_recovery_runtime_summary")
        if not isinstance(latest_summary, str) or "Bounded runtime for plan_revision_recovery_preview_refresh_entry" not in latest_summary:
            errors.append(f"{_rel(PROOF_MANIFEST)} scope.latest_plan_revision_recovery_runtime_summary must describe runtime behavior")
        expected_service_proof_scope = {
            "latest_plan_revision_recovery_service_proof_branch": "codex/l3-plan-revision-recovery-service-proof",
            "latest_plan_revision_recovery_service_proof_pr": "#605",
            "latest_plan_revision_recovery_service_proof_base_commit": "b399de4e5388cd96492dde50f98c90c6713af789",
            "latest_plan_revision_recovery_service_proof_head_commit": "95b597a22ac7fa89d0df27ae1e3952b2f691e065",
            "latest_plan_revision_recovery_service_proof_merge_commit": "db7c7a0811a8e1a1343a4b285dec050a03e4361b",
            "latest_plan_revision_recovery_service_proof_live_behavior_change": False,
        }
        for key, value in expected_service_proof_scope.items():
            if proof_scope.get(key) != value:
                errors.append(f"{_rel(PROOF_MANIFEST)} scope.{key} must be {value!r}")
        proof_summary = proof_scope.get("latest_plan_revision_recovery_service_proof_summary")
        if not isinstance(proof_summary, str) or "owner authority row-count stability" not in proof_summary:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} scope.latest_plan_revision_recovery_service_proof_summary "
                "must describe PR #605 owner-service proof hardening"
            )

    seed_checkout_hint = _nested(manifest, "artifact_scope", "seed_checkout_hint")
    if not isinstance(seed_checkout_hint, str):
        errors.append("artifact_scope.seed_checkout_hint must be present for PR #609 proof/progress sync")
    else:
        for term in (
            "codex/l3-synth-ref-sync",
            "ad51b1c6736cd51ec3dd30de914e59ddb4c66158",
            "PR #609 APS source-family extraction",
            "external multi-audit synthesis/adjudication reference only",
        ):
            if term not in seed_checkout_hint:
                errors.append(f"artifact_scope.seed_checkout_hint missing PR #609 sync term: {term}")

    top_level = manifest.get("plan_revision_recovery_runtime")
    if not isinstance(top_level, dict):
        errors.append("manifest missing plan_revision_recovery_runtime object")
    else:
        expected = {
            "mode": "plan_revision_recovery_preview_refresh_entry",
            "source_gate": "134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE",
            "live_behavior_change": True,
            "route": "/api/v1/layer3/plan/revision/recover",
            "owner_service": "backend/app/services/layer3_plan_revision_recovery.py",
            "request_dto": "Layer3PlanRevisionRecoveryRequest",
            "response_dto": "Layer3PlanRevisionRecoveryResponse",
            "persistence": "existing L3Session.summary_json only",
            "implementation_pr": "#599",
            "implementation_base_commit": "47aef2ee13e173121c3738e63bafbe86e360c280",
            "implementation_head_commit": "51e5abcbcdd2070c47b3aeba73032db081be41f7",
            "implementation_merge_commit": "1e74a739a07623b7d91d405d946e6b1d221be6ff",
        }
        for key, value in expected.items():
            if top_level.get(key) != value:
                errors.append(f"plan_revision_recovery_runtime.{key} must be {value!r}")
        blocked_scope = top_level.get("blocked_scope")
        if not isinstance(blocked_scope, list):
            errors.append("plan_revision_recovery_runtime.blocked_scope must be a list")
        else:
            for blocked in (
                "approved-plan reopening, cancellation, deletion, replacement, or supersession",
                "L3AnalysisPlan creation, update, or deletion",
                "L3PassRun creation",
                "AnalysisRun creation",
                "output/package/handoff/export artifact creation",
                "connector/destination dispatch",
                "source/schema/runtime widening",
                "authentication/security hardening",
            ):
                if blocked not in blocked_scope:
                    errors.append(f"plan_revision_recovery_runtime.blocked_scope missing {blocked}")
        service_proof = top_level.get("service_proof")
        if not isinstance(service_proof, list):
            errors.append("plan_revision_recovery_runtime.service_proof must be a list after PR #605")
        else:
            service_proof_text = "\n".join(str(item) for item in service_proof)
            for term in (
                "PR #605",
                "owner authority row-count stability",
                "forbidden-field",
                "zero downstream AnalysisRun",
            ):
                if term not in service_proof_text:
                    errors.append(f"plan_revision_recovery_runtime.service_proof missing PR #605 term: {term}")

    next_required = manifest.get("next_required_decision")
    if not isinstance(next_required, str):
        errors.append("manifest next_required_decision missing for revision recovery runtime")
    else:
        for term in (
            "After the bounded plan_revision_recovery_preview_refresh_entry runtime",
            "approved-plan supersession",
            "separate freeze and proof plan",
        ):
            if term not in next_required:
                errors.append(f"manifest next_required_decision missing revision runtime term: {term}")

    slices = manifest.get("layer3_workbench_slices")
    if not isinstance(slices, list):
        errors.append("layer3_workbench_slices missing for revision recovery entry freeze")
    else:
        matches = [
            item
            for item in slices
            if isinstance(item, dict)
            and item.get("slice_id") == "plan-revision-recovery-preview-refresh-runtime"
        ]
        if len(matches) != 1:
            errors.append(
                "layer3_workbench_slices must contain exactly one "
                "plan-revision-recovery-preview-refresh-runtime record"
            )
        else:
            item = matches[0]
            if item.get("main_state") != "live_bounded_plan_revision_recovery_preview_refresh_runtime":
                errors.append(
                    "revision recovery runtime slice must be "
                    "live_bounded_plan_revision_recovery_preview_refresh_runtime"
                )
            if "#599" not in item.get("key_prs", []):
                errors.append("revision recovery runtime slice key_prs must include #599")
            if item.get("merge_commit") != "1e74a739a07623b7d91d405d946e6b1d221be6ff":
                errors.append("revision recovery runtime slice merge_commit must identify PR #599 merge")
            counting_rule = item.get("counting_rule")
            if not isinstance(counting_rule, str) or "live bounded workbench slice" not in counting_rule:
                errors.append("revision recovery runtime slice counting_rule must classify the slice as live bounded")
            elif "Counts as one planning-only" in counting_rule:
                errors.append("revision recovery runtime slice counting_rule must not classify the merged runtime as planning-only")
            docs = item.get("governing_docs")
            if not isinstance(docs, list):
                errors.append("revision recovery runtime slice missing governing_docs")
            else:
                for doc in (
                    "next_milestone_plans/Layer3_planning_docs/134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md",
                    "next_milestone_plans/Layer3_planning_docs/132_PLAN_REVISION_RECOVERY_FREEZE.md",
                    "next_milestone_plans/Layer3_planning_docs/133_PLAN_REVISION_RECOVERY_CONTRACT.md",
                    "backend/app/services/layer3_plan_revision_recovery.py",
                    "backend/app/services/layer3_plan_revision_state.py",
                    "backend/tests/test_layer3_plan_revision_recovery.py",
                    "backend/tests/test_layer3_plan_flow_contract.py",
                    "backend/tests/test_layer3_state_model_contract.py",
                    "backend/tests/test_layer3_readiness_contract.py",
                    "backend/tests/test_layer3_bootstrap_contract.py",
                    "tools/l3-progress-check.py",
                ):
                    if doc not in docs:
                        errors.append(f"revision recovery runtime governing_docs missing {doc}")
            explicit_non_goals = item.get("explicit_non_goals")
            if not isinstance(explicit_non_goals, list):
                errors.append("revision recovery runtime slice missing explicit_non_goals")
            else:
                for blocked in (
                    "approved-plan reopening, cancellation, deletion, replacement, or supersession",
                    "L3PassRun creation",
                    "AnalysisRun creation",
                    "AnalysisArtifact creation",
                    "L3OutputPackage creation, update, or deletion",
                    "L3ReconciliationRecord creation, update, or deletion",
                    "ConnectorRun creation",
                    "output/package/handoff/export artifact creation",
                    "connector/destination dispatch",
                    "broad qualitative/hybrid/RAG execution",
                    "authentication/security hardening",
                    "broad package mutation/reconstruction",
                ):
                    if blocked not in explicit_non_goals:
                        errors.append(f"revision recovery runtime explicit_non_goals missing {blocked}")

    api_text = _read_required_text(LAYER3_API, errors)
    recovery_service_text = _read_required_text(
        ROOT / "backend" / "app" / "services" / "layer3_plan_revision_recovery.py",
        errors,
    )
    recovery_service_test_text = _read_required_text(PLAN_REVISION_RECOVERY_TEST, errors)
    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    readiness_text = _read_required_text(
        ROOT / "backend" / "app" / "services" / "layer3_readiness_contract.py",
        errors,
    )
    bootstrap_text = _read_required_text(
        ROOT / "backend" / "app" / "services" / "layer3_bootstrap_contract.py",
        errors,
    )
    api_terms = (
        "Layer3PlanRevisionRecoveryRequest",
        "Layer3PlanRevisionRecoveryResponse",
        "PLAN_REVISION_RECOVERY_REQUEST_SCHEMA",
        '"/plan/revision/recover"',
        "plan_revision_recovery",
    )
    for term in api_terms:
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing recovery runtime API term: {term}")
    service_terms = (
        "PLAN_REVISION_RECOVERY_RESULT_SCHEMA_ID",
        "PLAN_REVISION_RECOVERY_PREVIEW_MARKER_SCHEMA_ID",
        "recover_plan_revision_for_preview_refresh",
        "plan_revision_recovery_preview_marker",
        "recovery_lifecycle_only",
        "pass_runs_already_exist",
        "plan_already_approved",
    )
    for term in service_terms:
        if term not in recovery_service_text:
            errors.append(f"layer3_plan_revision_recovery.py missing runtime term: {term}")
    for term in (
        "plan_revision_recovery_from_session",
        "plan_revision_recovery_preview_marker",
        "plan_preview_payload[\"revision_recovery\"]",
        "plan_revision_recovery(db",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing recovery runtime wiring term: {term}")
    if '"revision-recovery"' not in readiness_text or "plan_revision_recovery_admitted" not in readiness_text:
        errors.append("readiness contract must expose admitted revision-recovery runtime")
    if '"plan_revision_recovery": True' not in bootstrap_text:
        errors.append("bootstrap contract must expose plan_revision_recovery feature flag")

    for term in (
        "test_recover_plan_revision_for_preview_refresh_records_summary_state_only_and_is_idempotent",
        "test_recover_plan_revision_for_preview_refresh_rejects_non_admitted_fields_before_mutation",
        "test_recover_plan_revision_for_preview_refresh_prechecks_fail_closed_before_mutation",
        "test_recover_plan_revision_for_preview_refresh_blocks_plan_and_pass_run_state_without_recovery_mutation",
        "test_plan_revision_recovery_preview_marker_requires_recovery_state",
        "recover_plan_revision_for_preview_refresh",
        "plan_revision_recovery_preview_marker",
        "plan_revision_recovery_from_session",
        "_owner_authority_row_counts",
        "db.query(L3AnalysisPlan).count() == 0",
        "db.query(L3PassRun).count() == 0",
        "db.query(AnalysisRun).count() == 0",
        "db.query(AnalysisArtifact).count() == 0",
        "db.query(L3OutputPackage).count() == 0",
        "db.query(L3ReconciliationRecord).count() == 0",
        "db.query(ConnectorRun).count() == 0",
    ):
        if term not in recovery_service_test_text:
            errors.append(f"{_rel(PLAN_REVISION_RECOVERY_TEST)} missing recovery service proof term: {term}")


def _check_approved_plan_correction_freeze(
    manifest: dict[str, Any], errors: list[str]
) -> None:
    freeze_text = _read_required_text(APPROVED_PLAN_CORRECTION_FREEZE, errors)
    required_freeze_terms = [
        "Status: planning/control freeze only for `approved_plan_correction_lifecycle`",
        "selected_future_lifecycle_mode: `approved_plan_correction_lifecycle`",
        "selected_current_posture: `approved_plan_correction_not_admitted`",
        "approved_plan_cancel_without_replacement",
        "approved_plan_supersession_preview_only",
        "No runtime behavior is admitted by this document.",
        "approved-plan cancellation, reopening, replacement, deletion, and supersession remain unavailable",
    ]
    for term in required_freeze_terms:
        if term not in freeze_text:
            errors.append(f"{_rel(APPROVED_PLAN_CORRECTION_FREEZE)} missing approved-plan correction freeze term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: [
            "135_APPROVED_PLAN_CORRECTION_FREEZE.md",
            "approved_plan_correction_lifecycle",
            "broader `approved_plan_correction_lifecycle`",
            "approved-plan reopening, replacement, deletion, supersession",
        ],
        SYNTHESIS_BOUNDARY: [
            "135_APPROVED_PLAN_CORRECTION_FREEZE.md",
            "approved_plan_correction_lifecycle",
            "planning/control only",
            "replacement-plan creation",
        ],
        GOAL_AUDIT: [
            "Approved plan correction lifecycle",
            "Exact cancel-without-replacement runtime is live",
            "broader correction lifecycle remains blocked",
            "supersession",
        ],
        CLOSEOUT_DOC: [
            "planning/control approved-plan correction freeze",
            "135_APPROVED_PLAN_CORRECTION_FREEZE.md",
            "Exact approved-plan cancel-without-replacement runtime live",
            "broader correction lifecycle blocked",
        ],
        BOARD: [
            "Current approved-plan correction planning/control freeze",
            "approved_plan_correction_lifecycle",
            "Approved plan correction freeze",
        ],
        PROOF_MANIFEST: [
            "approved_plan_correction_freeze_proof",
            "latest_approved_plan_correction_freeze_branch",
            "55d90f869d1f1e49127bc1dd2e1269d056f702aa",
            "approved_plan_correction_lifecycle",
            "approved_plan_cancel_runtime_proof",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing approved-plan correction term: {term}")

    readiness_text = _read_required_text(READINESS_CONTRACT_SERVICE, errors)
    plan_flow_text = _read_required_text(PLAN_FLOW_CONTRACT_SERVICE, errors)
    for term in (
        '"approved_plan_correction": "only approved_plan_cancel_without_replacement is admitted',
        '"revision_recovery": "admitted only as preview-refresh recovery',
    ):
        if term not in readiness_text:
            errors.append(f"{_rel(READINESS_CONTRACT_SERVICE)} missing approved-plan correction readiness term: {term}")
    if '"approved_plan_supersession"' not in plan_flow_text:
        errors.append(f"{_rel(PLAN_FLOW_CONTRACT_SERVICE)} must keep approved_plan_supersession forbidden")

    top_level = manifest.get("approved_plan_correction_freeze")
    if not isinstance(top_level, dict):
        errors.append("manifest missing approved_plan_correction_freeze object")
    else:
        expected = {
            "mode": "approved_plan_correction_lifecycle",
            "source_gate": "135_APPROVED_PLAN_CORRECTION_FREEZE",
            "live_behavior_change": False,
            "planning_branch": "codex/l3-approved-plan-supersession-freeze",
            "base_commit": "55d90f869d1f1e49127bc1dd2e1269d056f702aa",
            "selected_current_posture": "approved_plan_correction_not_admitted",
        }
        for key, value in expected.items():
            if top_level.get(key) != value:
                errors.append(f"approved_plan_correction_freeze.{key} must be {value!r}")
        blocked_scope = top_level.get("blocked_scope")
        if not isinstance(blocked_scope, list):
            errors.append("approved_plan_correction_freeze.blocked_scope must be a list")
        else:
            for blocked in (
                "runtime behavior",
                "route/API changes",
                "approved-plan cancellation, reopening, replacement, deletion, or supersession",
                "L3AnalysisPlan creation, update, or deletion",
                "L3PassRun creation, update, cancellation, or deletion",
                "AnalysisRun creation, update, cancellation, or deletion",
                "output/package/handoff/export artifact creation",
                "connector/destination dispatch",
                "source/schema/runtime widening",
                "authentication/security hardening",
            ):
                if blocked not in blocked_scope:
                    errors.append(f"approved_plan_correction_freeze.blocked_scope missing {blocked}")

    slices = manifest.get("layer3_workbench_slices")
    if not isinstance(slices, list):
        errors.append("layer3_workbench_slices missing for approved-plan correction freeze")
    else:
        matches = [
            item
            for item in slices
            if isinstance(item, dict)
            and item.get("slice_id") == "approved-plan-correction-freeze"
        ]
        if len(matches) != 1:
            errors.append("layer3_workbench_slices must contain exactly one approved-plan-correction-freeze record")
        else:
            item = matches[0]
            if item.get("main_state") != "planning_only_approved_plan_correction_lifecycle":
                errors.append("approved-plan correction slice must remain planning_only_approved_plan_correction_lifecycle")
            if item.get("base_commit") != "55d90f869d1f1e49127bc1dd2e1269d056f702aa":
                errors.append("approved-plan correction slice base_commit must identify PR #600 merge")
            counting_rule = item.get("counting_rule")
            if not isinstance(counting_rule, str) or "planning-only workbench slice" not in counting_rule:
                errors.append("approved-plan correction slice counting_rule must classify the slice as planning-only")
            docs = item.get("governing_docs")
            if not isinstance(docs, list):
                errors.append("approved-plan correction slice missing governing_docs")
            else:
                for doc in (
                    "next_milestone_plans/Layer3_planning_docs/135_APPROVED_PLAN_CORRECTION_FREEZE.md",
                    "next_milestone_plans/Layer3_planning_docs/105_deferred-gates.md",
                    "next_milestone_plans/Layer3_planning_docs/117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md",
                    "next_milestone_plans/Layer3_planning_docs/118_L3_GOAL_AUDIT.md",
                    "next_milestone_plans/Layer3_planning_docs/120_L3_CLOSEOUT.md",
                    "backend/app/services/layer3_readiness_contract.py",
                    "backend/app/services/layer3_plan_flow_contract.py",
                    "tools/l3-progress-check.py",
                ):
                    if doc not in docs:
                        errors.append(f"approved-plan correction governing_docs missing {doc}")


def _check_approved_plan_cancel_entry_freeze(
    manifest: dict[str, Any], errors: list[str]
) -> None:
    freeze_text = _read_required_text(APPROVED_PLAN_CANCEL_ENTRY_FREEZE, errors)
    required_freeze_terms = [
        "Status: implementation-entry freeze only for `approved_plan_cancel_without_replacement`",
        "selected_entry_mode: `approved_plan_cancel_without_replacement`",
        "POST /api/v1/layer3/plan/approved/cancel",
        "backend/app/services/layer3_approved_plan_correction.py",
        "Layer3ApprovedPlanCancelRequest",
        "Layer3ApprovedPlanCancelResponse",
        "layer3.approved_plan_cancel_request.v1",
        "layer3.approved_plan_cancel_result.v1",
        "No runtime behavior is admitted by this document.",
        "`approved_plan_cancel_without_replacement` is the only selected correction mode",
        "Cancellation creates no replacement plan.",
        "authentication/security hardening",
    ]
    for term in required_freeze_terms:
        if term not in freeze_text:
            errors.append(f"{_rel(APPROVED_PLAN_CANCEL_ENTRY_FREEZE)} missing approved-plan cancel entry term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: [
            "136_APPROVED_PLAN_CANCEL_ENTRY_FREEZE.md",
            "approved_plan_cancel_without_replacement",
            "admits no runtime behavior by itself",
            "approved-plan supersession",
        ],
        SYNTHESIS_BOUNDARY: [
            "136_APPROVED_PLAN_CANCEL_ENTRY_FREEZE.md",
            "approved_plan_cancel_without_replacement",
            "entry freeze",
            "bounded runtime",
        ],
        GOAL_AUDIT: [
            "136_APPROVED_PLAN_CANCEL_ENTRY_FREEZE.md",
            "approved_plan_cancel_without_replacement",
            "runtime is live",
            "no approved-plan supersession",
        ],
        CLOSEOUT_DOC: [
            "approved-plan cancel-without-replacement runtime",
            "136_APPROVED_PLAN_CANCEL_ENTRY_FREEZE.md",
            "supersession",
        ],
        BOARD: [
            "Current approved-plan cancel runtime",
            "83 structured records",
            "Approved plan cancel runtime",
            "approved_plan_cancel_without_replacement",
        ],
        PROOF_MANIFEST: [
            "approved_plan_cancel_entry_freeze_proof",
            "approved_plan_cancel_runtime_proof",
            "latest_approved_plan_cancel_entry_freeze_branch",
            "codex/l3-approved-plan-cancel-entry-freeze",
            "codex/l3-approved-plan-cancel-runtime",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing approved-plan cancel entry term: {term}")

    readiness_text = _read_required_text(READINESS_CONTRACT_SERVICE, errors)
    plan_flow_text = _read_required_text(PLAN_FLOW_CONTRACT_SERVICE, errors)
    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    models_text = _read_required_text(MODELS, errors)
    for term in (
        '"approved_plan_cancel": "admitted only as cancellation without replacement of the current approved plan before pass-run creation"',
        '"revision_recovery": "admitted only as preview-refresh recovery',
    ):
        if term not in readiness_text:
            errors.append(f"{_rel(READINESS_CONTRACT_SERVICE)} missing cancel-entry readiness term: {term}")
    if '"approved_plan_supersession"' not in plan_flow_text:
        errors.append(f"{_rel(PLAN_FLOW_CONTRACT_SERVICE)} must keep approved_plan_supersession forbidden")
    for term in (
        '"approved_plan_cancelled"',
        '"pass_runs_already_exist"',
        "L3AnalysisPlan.status == PLAN_STATUS_APPROVED",
        "L3AnalysisPlan.approved_by_operator.is_(True)",
        "approved_by_operator=True",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing approved-plan authority term: {term}")
    for term in (
        "class L3AnalysisPlan",
        "analysis_plan_id",
        "status: Mapped[str]",
        "approved_by_operator",
        "approved_at",
        "plan_json",
    ):
        if term not in models_text:
            errors.append(f"{_rel(MODELS)} missing approved-plan model authority term: {term}")

    top_level = manifest.get("approved_plan_cancel_entry_freeze")
    if not isinstance(top_level, dict):
        errors.append("manifest missing approved_plan_cancel_entry_freeze object")
    else:
        expected = {
            "mode": "approved_plan_cancel_without_replacement",
            "source_gate": "136_APPROVED_PLAN_CANCEL_ENTRY_FREEZE",
            "predecessor_gate": "135_APPROVED_PLAN_CORRECTION_FREEZE",
            "live_behavior_change": False,
            "planning_branch": "codex/l3-approved-plan-cancel-entry-freeze",
            "base_commit": "d60b01aabf394ee36f4fbcffb13e932d931e996c",
            "selected_entry_mode": "approved_plan_cancel_without_replacement",
            "future_route": "/api/v1/layer3/plan/approved/cancel",
            "future_owner_service": "backend/app/services/layer3_approved_plan_correction.py",
            "future_request_dto": "Layer3ApprovedPlanCancelRequest",
            "future_response_dto": "Layer3ApprovedPlanCancelResponse",
            "future_request_schema_id": "layer3.approved_plan_cancel_request.v1",
            "future_response_schema_id": "layer3.approved_plan_cancel_result.v1",
        }
        for key, value in expected.items():
            if top_level.get(key) != value:
                errors.append(f"approved_plan_cancel_entry_freeze.{key} must be {value!r}")
        blocked_scope = top_level.get("blocked_scope")
        if not isinstance(blocked_scope, list):
            errors.append("approved_plan_cancel_entry_freeze.blocked_scope must be a list")
        else:
            for blocked in (
                "runtime behavior by this document alone",
                "approved-plan supersession, replacement, reopening, or deletion",
                "L3AnalysisPlan creation",
                "L3PassRun creation, update, cancellation, or deletion",
                "AnalysisRun creation, update, cancellation, or deletion",
                "output/package/handoff/export artifact creation",
                "connector/destination dispatch",
                "source/schema/runtime widening",
                "authentication/security hardening",
                "broad package mutation/reconstruction",
            ):
                if blocked not in blocked_scope:
                    errors.append(f"approved_plan_cancel_entry_freeze.blocked_scope missing {blocked}")

    slices = manifest.get("layer3_workbench_slices")
    if not isinstance(slices, list):
        errors.append("layer3_workbench_slices missing for approved-plan cancel entry freeze")
    else:
        matches = [
            item
            for item in slices
            if isinstance(item, dict)
            and item.get("slice_id") == "approved-plan-cancel-entry-freeze"
        ]
        if len(matches) != 1:
            errors.append("layer3_workbench_slices must contain exactly one approved-plan-cancel-entry-freeze record")
        else:
            item = matches[0]
            if item.get("main_state") != "planning_only_approved_plan_cancel_without_replacement_entry":
                errors.append("approved-plan cancel entry slice must remain planning-only")
            if item.get("base_commit") != "d60b01aabf394ee36f4fbcffb13e932d931e996c":
                errors.append("approved-plan cancel entry slice base_commit must identify PR #601 merge")
            counting_rule = item.get("counting_rule")
            if not isinstance(counting_rule, str) or "planning-only workbench slice" not in counting_rule:
                errors.append("approved-plan cancel entry slice counting_rule must classify the slice as planning-only")
            docs = item.get("governing_docs")
            if not isinstance(docs, list):
                errors.append("approved-plan cancel entry slice missing governing_docs")
            else:
                for doc in (
                    "next_milestone_plans/Layer3_planning_docs/136_APPROVED_PLAN_CANCEL_ENTRY_FREEZE.md",
                    "next_milestone_plans/Layer3_planning_docs/135_APPROVED_PLAN_CORRECTION_FREEZE.md",
                    "next_milestone_plans/Layer3_planning_docs/105_deferred-gates.md",
                    "next_milestone_plans/Layer3_planning_docs/117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md",
                    "next_milestone_plans/Layer3_planning_docs/118_L3_GOAL_AUDIT.md",
                    "next_milestone_plans/Layer3_planning_docs/120_L3_CLOSEOUT.md",
                    "backend/app/services/layer3_readiness_contract.py",
                    "backend/app/services/layer3_plan_flow_contract.py",
                    "backend/app/services/layer3_workbench.py",
                    "backend/app/models/models.py",
                    "tools/l3-progress-check.py",
                ):
                    if doc not in docs:
                        errors.append(f"approved-plan cancel entry governing_docs missing {doc}")


def _check_approved_plan_cancel_runtime(
    manifest: dict[str, Any], errors: list[str]
) -> None:
    runtime = manifest.get("approved_plan_cancel_runtime")
    if not isinstance(runtime, dict):
        errors.append("manifest missing approved_plan_cancel_runtime object")
    else:
        expected = {
            "mode": "approved_plan_cancel_without_replacement",
            "source_gate": "136_APPROVED_PLAN_CANCEL_ENTRY_FREEZE",
            "live_behavior_change": True,
            "implementation_branch": "codex/l3-approved-plan-cancel-runtime",
            "base_commit": "9bb11820bc5b12292cbc43d1a2c326e61df80d2e",
            "route": "/api/v1/layer3/plan/approved/cancel",
            "owner_service": "backend/app/services/layer3_approved_plan_correction.py",
            "request_dto": "Layer3ApprovedPlanCancelRequest",
            "response_dto": "Layer3ApprovedPlanCancelResponse",
            "request_schema_id": "layer3.approved_plan_cancel_request.v1",
            "response_schema_id": "layer3.approved_plan_cancel_result.v1",
            "state_schema_id": "layer3.approved_plan_cancel_state.v1",
            "next_state": "approved_plan_cancelled",
            "plan_status": "cancelled",
        }
        for key, value in expected.items():
            if runtime.get(key) != value:
                errors.append(f"approved_plan_cancel_runtime.{key} must be {value!r}")
        for key in ("positive_proof", "negative_proof", "blocked_scope", "governing_docs"):
            if not isinstance(runtime.get(key), list) or not runtime.get(key):
                errors.append(f"approved_plan_cancel_runtime.{key} must be a non-empty list")
        blocked_scope = runtime.get("blocked_scope") if isinstance(runtime.get("blocked_scope"), list) else []
        for blocked in (
            "replacement plan creation",
            "approved-plan supersession, replacement, reopening, or deletion",
            "L3AnalysisPlan creation",
            "L3PassRun creation",
            "AnalysisRun creation",
            "output/package/handoff/export artifact creation",
            "connector/destination dispatch",
            "source/schema/runtime widening",
            "provider/public URL support",
            "broad qualitative/hybrid/RAG execution",
            "frontend-only durable state",
            "hidden LLM planning",
            "full mockup activation",
            "authentication/security hardening",
            "broad package mutation/reconstruction",
        ):
            if blocked not in blocked_scope:
                errors.append(f"approved_plan_cancel_runtime.blocked_scope missing {blocked}")

    service_text = _read_required_text(APPROVED_PLAN_CORRECTION_SERVICE, errors)
    api_text = _read_required_text(LAYER3_API, errors)
    plan_flow_text = _read_required_text(PLAN_FLOW_CONTRACT_SERVICE, errors)
    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    state_action_text = _read_required_text(STATE_ACTION_CONTRACT, errors)
    state_model_text = _read_required_text(STATE_MODEL_CONTRACT_SERVICE, errors)
    readiness_text = _read_required_text(READINESS_CONTRACT_SERVICE, errors)
    bootstrap_text = _read_required_text(BOOTSTRAP_CONTRACT_SERVICE, errors)
    api_test_text = _read_required_text(LAYER3_API_TEST, errors)
    service_test_text = _read_required_text(APPROVED_PLAN_CORRECTION_TEST, errors)

    required_terms_by_surface = {
        APPROVED_PLAN_CORRECTION_SERVICE: (
            "cancel_approved_plan_without_replacement",
            "APPROVED_PLAN_CANCEL_REQUEST_SCHEMA_ID",
            "APPROVED_PLAN_CANCEL_RESULT_SCHEMA_ID",
            "APPROVED_PLAN_CANCEL_STATE_SCHEMA_ID",
            "APPROVED_PLAN_CANCEL_NEXT_STATE",
            "APPROVED_PLAN_CANCELLED_STATUS",
            "approved_plan_cancel_blocked_fields",
            "with_for_update()",
            "pass_runs_already_exist",
            "downstream_state_already_exists",
            "L3ReconciliationRecord.session_id",
            "L3OutputPackage.session_id",
            "multiple_approved_plans",
            "replacement_plan_created",
        ),
        LAYER3_API: (
            "Layer3ApprovedPlanCancelRequest",
            "Layer3ApprovedPlanCancelResponse",
            "APPROVED_PLAN_CANCEL_REQUEST_SCHEMA",
            '"/plan/approved/cancel"',
            "layer3_workbench.approved_plan_cancel",
        ),
        PLAN_FLOW_CONTRACT_SERVICE: (
            "APPROVED_PLAN_CANCEL_FORBIDDEN_FIELDS",
            "approved_plan_cancel_blocked_fields",
            '"approved_plan_supersession"',
            '"replacement_plan"',
        ),
        WORKBENCH_SERVICE: (
            "approved_plan_cancel",
            "approved_plan_cancelled",
            "APPROVED_PLAN_CANCEL_DOWNSTREAM_UNAVAILABLE",
        ),
        STATE_ACTION_CONTRACT: (
            "approved_plan_cancel_without_replacement",
            "approved_plan_cancel",
            "backend/app/services/layer3_approved_plan_correction.py",
        ),
        STATE_MODEL_CONTRACT_SERVICE: (
            "approved_plan_cancelled",
            "inspect_approved_plan_cancel",
            '"approved_plan_cancel", "execution_select"',
        ),
        READINESS_CONTRACT_SERVICE: (
            "approved_plan_cancel_admitted",
            "approved_plan_cancel_endpoint",
            "client_request_id_required_for_approved_plan_cancel",
            "duplicate_approved_plan_cancel",
            "approved_plan_cancel_uses_session_and_plan_locks",
            "approved_plan_cancel_without_replacement_only",
        ),
        BOOTSTRAP_CONTRACT_SERVICE: (
            '"approved_plan_cancel": True',
            "approved_plan_cancel_admitted",
        ),
        LAYER3_API_TEST: (
            "test_layer3_api_approved_plan_cancel_without_replacement_updates_existing_plan_only",
            "test_layer3_api_approved_plan_cancel_prechecks_fail_closed",
            "db.query(L3PassRun).count() == 0",
            "db.query(AnalysisRun).count() == 0",
            "db.query(AnalysisArtifact).count() == 0",
            "db.query(L3OutputPackage).count() == 0",
        ),
        APPROVED_PLAN_CORRECTION_TEST: (
            "test_cancel_approved_plan_without_replacement_updates_existing_plan_only_and_is_idempotent",
            "test_cancel_approved_plan_without_replacement_rejects_non_admitted_fields_before_mutation",
            "test_cancel_approved_plan_without_replacement_prechecks_fail_closed_before_mutation",
            "test_cancel_approved_plan_without_replacement_rejects_orphan_downstream_package_state_before_mutation",
            "test_approved_plan_cancel_from_session_requires_current_schema",
            "cancel_approved_plan_without_replacement",
            "approved_plan_cancel_from_session",
            "downstream_state_already_exists",
            "inspect_existing_downstream_state",
            "db.query(L3PassRun).count() == 0",
            "db.query(AnalysisRun).count() == 0",
            "db.query(AnalysisArtifact).count() == 0",
            "db.query(L3OutputPackage).count() == 0",
            "db.query(L3ReconciliationRecord).count() == 0",
            "db.query(ConnectorRun).count() == 0",
        ),
    }
    text_by_surface = {
        APPROVED_PLAN_CORRECTION_SERVICE: service_text,
        LAYER3_API: api_text,
        PLAN_FLOW_CONTRACT_SERVICE: plan_flow_text,
        WORKBENCH_SERVICE: workbench_text,
        STATE_ACTION_CONTRACT: state_action_text,
        STATE_MODEL_CONTRACT_SERVICE: state_model_text,
        READINESS_CONTRACT_SERVICE: readiness_text,
        BOOTSTRAP_CONTRACT_SERVICE: bootstrap_text,
        LAYER3_API_TEST: api_test_text,
        APPROVED_PLAN_CORRECTION_TEST: service_test_text,
    }
    for path, terms in required_terms_by_surface.items():
        text = text_by_surface[path]
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing approved-plan cancel runtime term: {term}")

    forbidden_service_terms = (
        "AnalysisRun(",
        "AnalysisArtifact(",
        "L3OutputPackage(",
        "L3ReconciliationRecord(",
        "ConnectorRun(",
        "materialize_pass_entry",
        "materialize_package_entry",
        "provider_public",
    )
    for term in forbidden_service_terms:
        if term in service_text:
            errors.append(f"{_rel(APPROVED_PLAN_CORRECTION_SERVICE)} contains forbidden runtime expansion term: {term}")

    slices = manifest.get("layer3_workbench_slices")
    if not isinstance(slices, list):
        errors.append("layer3_workbench_slices missing for approved-plan cancel runtime")
    else:
        matches = [
            item
            for item in slices
            if isinstance(item, dict)
            and item.get("slice_id") == "approved-plan-cancel-runtime"
        ]
        if len(matches) != 1:
            errors.append("layer3_workbench_slices must contain exactly one approved-plan-cancel-runtime record")
        else:
            item = matches[0]
            if item.get("main_state") != "live_bounded_approved_plan_cancel_without_replacement_runtime":
                errors.append("approved-plan cancel runtime slice must be live_bounded approved-plan cancel runtime")
            if item.get("base_commit") != "9bb11820bc5b12292cbc43d1a2c326e61df80d2e":
                errors.append("approved-plan cancel runtime slice base_commit must identify PR #602 merge")
            counting_rule = item.get("counting_rule")
            if not isinstance(counting_rule, str) or "live bounded workbench slice" not in counting_rule:
                errors.append("approved-plan cancel runtime slice counting_rule must classify the slice as live bounded")

    hardening = manifest.get("approved_plan_cancel_downstream_state_hardening")
    if not isinstance(hardening, dict):
        errors.append("manifest missing approved_plan_cancel_downstream_state_hardening object")
    else:
        expected_hardening = {
            "mode": "approved_plan_cancel_without_replacement",
            "implementation_branch": "codex/l3-cancel-proof",
            "implementation_pr": "#612",
            "merge_commit": "01023e82",
            "post_merge_authority": "project6-origin/main at 01023e82",
            "error_code": "downstream_state_already_exists",
            "owner_service": "backend/app/services/layer3_approved_plan_correction.py",
        }
        for key, value in expected_hardening.items():
            if hardening.get(key) != value:
                errors.append(f"approved_plan_cancel_downstream_state_hardening.{key} must be {value!r}")
        blocked_state = hardening.get("blocked_state")
        if not isinstance(blocked_state, list):
            errors.append("approved_plan_cancel_downstream_state_hardening.blocked_state must be a list")
        else:
            for term in ("L3ReconciliationRecord", "L3OutputPackage"):
                if term not in blocked_state:
                    errors.append(f"approved_plan_cancel_downstream_state_hardening.blocked_state missing {term}")

    proof_manifest_text = _read_required_text(PROOF_MANIFEST, errors)
    for term in (
        "approved_plan_cancel_downstream_state_hardening_proof",
        '"implementation_pr": "#612"',
        '"merge_commit": "01023e82"',
        "same-session orphan reconciliation/package state fail-closed behavior",
    ):
        if term not in proof_manifest_text:
            errors.append(f"{_rel(PROOF_MANIFEST)} missing PR #612 approved-plan cancel hardening proof term: {term}")


def _check_referenced_paths(manifest: dict[str, Any], errors: list[str]) -> None:
    refs = manifest.get("authoritative_file_refs")
    if not isinstance(refs, list) or not refs:
        errors.append("authoritative_file_refs must be a non-empty list")
    else:
        for ref in refs:
            if isinstance(ref, str):
                candidate = ref
            elif isinstance(ref, dict):
                candidate = ref.get("path")
            else:
                candidate = None
            if not candidate:
                errors.append(f"malformed authoritative_file_refs entry: {ref!r}")
                continue
            path = ROOT / str(candidate)
            if not path.exists():
                errors.append(f"authoritative_file_refs path is missing: {candidate}")

    slices = manifest.get("layer3_workbench_slices")
    if not isinstance(slices, list):
        return
    for item in slices:
        if not isinstance(item, dict):
            continue
        slice_id = item.get("slice_id", "<unknown>")
        docs = item.get("governing_docs", [])
        if docs is None:
            continue
        if not isinstance(docs, list):
            errors.append(f"{slice_id}: governing_docs must be a list")
            continue
        for doc in docs:
            if not isinstance(doc, str) or not doc:
                errors.append(f"{slice_id}: malformed governing doc entry: {doc!r}")
                continue
            if not (ROOT / doc).exists():
                errors.append(f"{slice_id}: governing doc is missing: {doc}")


def _check_local_boundary(errors: list[str]) -> None:
    if not LOCAL_BOUNDARY.exists():
        return
    text = LOCAL_BOUNDARY.read_text(encoding="utf-8")
    document_terms = [
        "near_term_direction: remaining authentication/security work is intentionally deferred",
    ]
    for term in document_terms:
        if term not in text:
            errors.append(f"local boundary doc missing required term: {term}")

    allowed = _markdown_section(text, "Allowed Next Slices")
    if allowed is None:
        errors.append("local boundary doc missing section: Allowed Next Slices")
        return

    allowed_intro = "Allowed near-term next slices are narrow and proof-oriented, but not authentication/security work"
    if allowed_intro not in allowed:
        errors.append("Allowed Next Slices section no longer records near-term auth/security deferral")
    if "PR `#533` already merged server-derived `state_action_contract` hardening" not in allowed:
        errors.append("Allowed Next Slices section no longer records merged PR #533 state/action contract hardening status")

    allowed_part, _, blocked_part = allowed.partition("Not allowed as immediate next slices from this freeze:")
    if not blocked_part:
        errors.append("Allowed Next Slices section missing immediate no-go list")
        return

    required_near_term = [
        "Gate B idempotency/hash follow-up only if fresh proof finds a missed edge after merged PR `#531`",
        "Frontend server-contract consumption, session recovery, and Gate B draft-loss hardening",
        "State/action contract drift checker only if fresh proof shows post-PR533 contract drift",
        "Preview hash/idempotency contract hardening beyond merged PR `#531`",
        "Progress/proof/state drift checker",
        "No-behavior-change service extraction",
    ]
    for term in required_near_term:
        if term not in allowed_part:
            errors.append(f"Allowed Next Slices section missing non-security near-term option: {term}")

    blocked_terms = [
        "in-app auth implementation",
        "external proxy proof harness",
        "upload security hardening",
        "signed-reference revocation/concurrency/security hardening",
        "`LAYER3_SIGNED_REFERENCE_SECRET` deployment/runbook work",
        "provider/public URL implementation",
        "connector/destination dispatch",
        "broad upload/source expansion",
        "broad qualitative/hybrid/RAG execution",
        "package mutation/reconstruction",
        "full mockup activation",
    ]
    for term in blocked_terms:
        if term in allowed_part:
            errors.append(f"blocked term appears in allowed near-term list: {term}")
        if term not in blocked_part:
            errors.append(f"immediate no-go list missing blocked term: {term}")


def _check_connector_dispatch_entry_freeze(errors: list[str]) -> None:
    entry_text = _read_required_text(CONNECTOR_ENTRY_FREEZE, errors)
    required_entry_terms = [
        "Status: implementation-entry freeze plus bounded runtime contract for `internal_dispatch_record_only`",
        "selected_dispatch_mode: `internal_dispatch_record_only`",
        "Runtime implementation scope is limited to `/api/v1/layer3/handoff/connector/record`",
        "- external connector invocation",
        "- destination write",
        "- connector-run creation",
        "- provider/public URL support",
        "- package mutation/reconstruction",
        "- broad source/upload expansion",
        "- qualitative/hybrid/RAG execution",
        "- full mockup activation",
        "L3ReconciliationRecord.summary_json",
        "backend/app/services/layer3_connector_dispatch_entry.py",
        "layer3.connector_dispatch_record.v1",
        "connector_dispatch_recorded",
        "operator_decision` must be exactly `record_internal_connector_dispatch`",
        "must reject these before service mutation",
        "authentication/security scope reopening",
    ]
    for term in required_entry_terms:
        if term not in entry_text:
            errors.append(f"{_rel(CONNECTOR_ENTRY_FREEZE)} missing connector entry term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: [
            "121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md",
            "`internal_dispatch_record_only` runtime is live only as an internal record",
            "`connector_destination_dispatch` remains deferred",
            "`single_named_connector_dispatch` and `single_named_destination_dispatch` remain blocked",
        ],
        GOAL_AUDIT: [
            "121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md",
            "Internal record-only implementation is live and tested",
            "Only `internal_dispatch_record_only` is admitted",
            "External connector invocation, destination writes, generic downstream dispatch",
        ],
        CLOSEOUT_DOC: [
            "Internal connector dispatch record",
            "generic connector/destination dispatch",
            "package mutation/reconstruction",
            "broad source/upload expansion",
            "full mockup activation",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing connector entry term: {term}")

    admitted = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_ADMITTED_CAPABILITIES", errors),
        "STATE_ACTION_ADMITTED_CAPABILITIES",
        errors,
    )
    deferred = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_DEFERRED_CAPABILITIES", errors),
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        errors,
    )
    connector = deferred.get("connector_destination_dispatch")
    if connector is None:
        errors.append("deferred capabilities missing connector_destination_dispatch")
    elif connector.get("admitted") is not False:
        errors.append("connector_destination_dispatch must remain admitted false after exact internal record runtime")
    if "connector_destination_dispatch" in admitted:
        errors.append("connector_destination_dispatch must not appear in admitted capabilities for the internal record slice")
    internal = admitted.get("internal_dispatch_record_only")
    if internal is None:
        errors.append("admitted capabilities missing internal_dispatch_record_only")
    else:
        if internal.get("admitted") is not True:
            errors.append("internal_dispatch_record_only must be admitted true")
        if internal.get("source_gate") != "121_CONNECTOR_DISPATCH_ENTRY_FREEZE":
            errors.append("internal_dispatch_record_only source_gate drifted")
        if internal.get("owner_service") != "backend/app/services/layer3_connector_dispatch_entry.py":
            errors.append("internal_dispatch_record_only owner_service drifted")
        blocked = internal.get("blocked_downstream")
        if not isinstance(blocked, list):
            errors.append("internal_dispatch_record_only missing blocked_downstream list")
        else:
            for term in (
                "connector_destination_dispatch",
                "single_named_connector_dispatch",
                "single_named_destination_dispatch",
                "provider_public_url",
                "package_mutation_reconstruction",
                "local_upload_or_directory_source_expansion",
                "broad_qualitative_execution",
                "hybrid_execution",
                "rag_vector_retrieval",
                "full_mockup_activation",
            ):
                if term not in blocked:
                    errors.append(f"internal_dispatch_record_only blocked_downstream missing {term}")

    service_text = _read_required_text(CONNECTOR_DISPATCH_SERVICE, errors)
    for term in (
        "CONNECTOR_DISPATCH_RECORD_MODE = \"internal_dispatch_record_only\"",
        "CONNECTOR_DISPATCH_RECORD_OPERATOR_DECISION = \"record_internal_connector_dispatch\"",
        "CONNECTOR_DISPATCH_RECORD_STATE = \"connector_dispatch_recorded\"",
        "CONNECTOR_DISPATCH_RECORD_FORBIDDEN_FIELDS",
        "connector_dispatch_record_scope_not_admitted",
        "connector_dispatch_record_already_recorded",
        "connector_dispatch_record_source_not_admitted",
        "\"connector_dispatch_record\": record_state",
        "PASS_TYPE_ASSOCIATED_COHORT",
        "PASS_SCOPE_QUANT_ASSOCIATED_COHORT",
        "\"external_connector_invocation_enabled\": False",
        "\"destination_write_enabled\": False",
        "\"connector_run_created\": False",
        "\"package_mutation_enabled\": False",
        "\"source_widening_enabled\": False",
        "\"qualitative_hybrid_rag_execution_enabled\": False",
    ):
        if term not in service_text:
            errors.append(f"{_rel(CONNECTOR_DISPATCH_SERVICE)} missing connector runtime proof term: {term}")
    forbidden_service_terms = ("db.add(", "ConnectorRun(", "AnalysisRun(", "L3PassRun(", "L3OutputPackage(")
    for term in forbidden_service_terms:
        if term in service_text:
            errors.append(f"{_rel(CONNECTOR_DISPATCH_SERVICE)} contains forbidden creation term: {term}")

    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "Layer3ConnectorDispatchRecordRequest",
        "Layer3ConnectorDispatchRecordResponse",
        "CONNECTOR_DISPATCH_RECORD_REQUEST_SCHEMA",
        "\"/handoff/connector/record\"",
        "record_internal_connector_dispatch",
        "\"connector_key\": _forbidden_request_field_schema()",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing connector API term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    bootstrap_text = _read_required_text(BOOTSTRAP_CONTRACT_SERVICE, errors)
    contract_text = f"{workbench_text}\n{bootstrap_text}"
    for term in (
        "CONNECTOR_DISPATCH_RECORDED_STATE = \"connector_dispatch_recorded\"",
        "\"internal_connector_dispatch_record\"",
        "\"internal_connector_dispatch_record_admitted\": True",
        "\"internal_connector_dispatch_record_endpoint\": f\"{api_root}/handoff/connector/record\"",
        "\"dispatch_admitted\": False",
    ):
        if term not in contract_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} or {_rel(BOOTSTRAP_CONTRACT_SERVICE)} missing connector readiness term: {term}")

    test_text = _read_required_text(LAYER3_API_TEST, errors)
    for term in (
        "test_layer3_api_connector_dispatch_record_records_internal_receipt_without_side_effects",
        "test_layer3_api_connector_dispatch_record_prechecks_fail_closed",
        "test_layer3_connector_dispatch_record_api_boundary_returns_workbench_error_envelope",
        "connector_dispatch_record_already_recorded",
        "connector_dispatch_record_source_not_admitted",
        "ConnectorRun).count()",
        "L3PassRun).count()",
        "L3OutputPackage).count()",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_API_TEST)} missing connector proof term: {term}")


def _check_package_mutation_freeze(errors: list[str]) -> None:
    freeze_text = _read_required_text(PACKAGE_MUTATION_FREEZE, errors)
    required_freeze_terms = [
        "Status: implementation-entry freeze plus bounded runtime contract for `package_supersession_preview_only`",
        "selected_package_lifecycle_mode: `package_supersession_preview_only`",
        "immutable_package_rule: existing `L3OutputPackage` rows and package payload files are immutable",
        "Runtime implementation scope is limited to `/api/v1/layer3/package/mutation/preview`",
        "backend/app/services/layer3_package_mutation_entry.py",
        "layer3.package_supersession_preview.v1",
        "no database writes and no filesystem writes",
        "operator_decision` must be exactly `preview_package_supersession`",
        "must reject these before mutation or downstream side effects",
        "- `package_payload`",
        "- `package_variant_content`",
        "- `rewrite_output`",
        "- `rebuild_package`",
        "- `mutate_package`",
        "- `replace_package`",
        "- `delete_package`",
        "- `provider_public_url`",
        "- `source_upload`",
        "- `rag_vector_index`",
        "- `hybrid_execution`",
        "- `rag_execution`",
        "- `schema_migration`",
        "- `approved_plan_supersession`",
        "- `result_review_amendment`",
        "- `package_review_amendment`",
        "- authentication/security scope reopening",
        "no `L3OutputPackage`, `L3ReconciliationRecord`, `AnalysisArtifact`, `AnalysisRun`, `L3PassRun`, connector, source, handoff/export, delivery, provider URL, or payload file side effect occurs",
    ]
    for term in required_freeze_terms:
        if term not in freeze_text:
            errors.append(f"{_rel(PACKAGE_MUTATION_FREEZE)} missing package mutation freeze term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: [
            "122_PACKAGE_MUTATION_FREEZE.md",
            "`package_supersession_preview_only` runtime is live only as a read-only preview",
            "broad runtime package mutation/reconstruction remains not admitted",
            "no database writes, no package payload writes, and no in-place mutation",
        ],
        GOAL_AUDIT: [
            "122_PACKAGE_MUTATION_FREEZE.md",
            "Read-only supersession preview implementation is live and tested",
            "Only `package_supersession_preview_only`, `replacement_package_set_authority`, `package_supersession_commit_entry`, `replacement_package_artifact_manifest_only`, and `replacement_package_namespace_rows` are admitted package lifecycle runtimes",
            "128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md",
            "Existing bounded package construction/submit is not package mutation",
        ],
        CLOSEOUT_DOC: [
            "122_PACKAGE_MUTATION_FREEZE.md",
            "package_supersession_preview_only",
            "Read-only preview route is live; replacement package-set metadata authority is live; package supersession commit lineage route is live; package replacement artifact authority is planning/control only; package replacement artifact manifest-only verification is live; package replacement namespace rows are live only in `l3_replacement_output_package`; broad package mutation/reconstruction remains blocked.",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package mutation freeze term: {term}")

    admitted = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_ADMITTED_CAPABILITIES", errors),
        "STATE_ACTION_ADMITTED_CAPABILITIES",
        errors,
    )
    deferred = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_DEFERRED_CAPABILITIES", errors),
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        errors,
    )
    package_mutation = deferred.get("package_mutation_reconstruction")
    if package_mutation is None:
        errors.append("deferred capabilities missing package_mutation_reconstruction")
    elif package_mutation.get("admitted") is not False:
        errors.append("package_mutation_reconstruction must remain admitted false for the preview-only freeze")
    if "package_mutation_reconstruction" in admitted:
        errors.append("package_mutation_reconstruction must not appear in admitted capabilities for the preview-only freeze")
    preview = admitted.get("package_supersession_preview_only")
    if preview is None:
        errors.append("admitted capabilities missing package_supersession_preview_only")
    else:
        if preview.get("admitted") is not True:
            errors.append("package_supersession_preview_only must be admitted true")
        if preview.get("source_gate") != "122_PACKAGE_MUTATION_FREEZE":
            errors.append("package_supersession_preview_only source_gate drifted")
        if preview.get("owner_service") != "backend/app/services/layer3_package_mutation_entry.py":
            errors.append("package_supersession_preview_only owner_service drifted")
        blocked = preview.get("blocked_downstream")
        if not isinstance(blocked, list):
            errors.append("package_supersession_preview_only missing blocked_downstream list")
        else:
            for term in (
                "package_mutation_reconstruction",
                "package_row_mutation",
                "package_payload_rewrite",
                "package_supersession_commit_without_replacement_authority",
                "provider_public_url",
                "connector_destination_dispatch",
                "local_upload_or_directory_source_expansion",
                "broad_qualitative_execution",
                "hybrid_execution",
                "rag_vector_retrieval",
                "full_mockup_activation",
            ):
                if term not in blocked:
                    errors.append(f"package_supersession_preview_only blocked_downstream missing {term}")

    package_mutation_text = _read_required_text(PACKAGE_MUTATION_SERVICE, errors)
    for term in (
        "PACKAGE_SUPERSESSION_PREVIEW_MODE = \"package_supersession_preview_only\"",
        "PACKAGE_SUPERSESSION_PREVIEW_OPERATOR_DECISION = \"preview_package_supersession\"",
        "PACKAGE_SUPERSESSION_PREVIEW_FORBIDDEN_FIELDS",
        "package_supersession_preview_scope_not_admitted",
        "package_supersession_preview_requires_complete_package_set",
        "package_supersession_preview_payload_refs_unavailable",
        "package_supersession_preview_package_review_submit_record_ref_required",
        "\"package_row_mutation_enabled\": False",
        "\"package_payload_rewrite_enabled\": False",
        "\"package_supersession_commit_enabled\": False",
        "\"database_write_enabled\": False",
        "\"filesystem_write_enabled\": False",
        "\"broad_package_mutation_enabled\": False",
        "\"source_widening_enabled\": False",
        "\"connector_dispatch_enabled\": False",
        "\"provider_public_url_enabled\": False",
        "\"qualitative_hybrid_rag_execution_enabled\": False",
    ):
        if term not in package_mutation_text:
            errors.append(f"{_rel(PACKAGE_MUTATION_SERVICE)} missing package supersession preview proof term: {term}")
    for term in (
        "db.add(",
        "db.commit(",
        "L3OutputPackage(",
        "L3ReconciliationRecord(",
        "AnalysisArtifact(",
        "AnalysisRun(",
        "L3PassRun(",
        "ConnectorRun(",
        "write_bytes(",
    ):
        if term in package_mutation_text:
            errors.append(f"{_rel(PACKAGE_MUTATION_SERVICE)} contains forbidden mutation/creation term: {term}")

    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "Layer3PackageSupersessionPreviewRequest",
        "Layer3PackageSupersessionPreviewResponse",
        "PACKAGE_SUPERSESSION_PREVIEW_REQUEST_SCHEMA",
        "\"/package/mutation/preview\"",
        "preview_package_supersession",
        "\"package_payload\": _forbidden_request_field_schema()",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing package supersession preview API term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    readiness_text = _read_required_text(READINESS_CONTRACT_SERVICE, errors)
    bootstrap_text = _read_required_text(BOOTSTRAP_CONTRACT_SERVICE, errors)
    external_export_text = _read_required_text(EXTERNAL_EXPORT_CONTRACT_SERVICE, errors)
    contract_text = f"{workbench_text}\n{readiness_text}\n{bootstrap_text}\n{external_export_text}"
    for term in (
        "\"package_supersession_preview\"",
        "\"package_supersession_preview_admitted\": True",
        "\"package_supersession_preview_endpoint\": f\"{api_root}/package/mutation/preview\"",
        "\"package_supersession_preview_is_read_only\": True",
        "\"rebuild_package\"",
        "\"package_payload\"",
        "\"package_variant_content\"",
        "\"rewrite_output\"",
        "\"result_review_amendment\"",
        "\"package_review_amendment\"",
        "\"handoff_export_amendment\"",
        "\"aps_handoff_amendment\"",
    ):
        if term not in contract_text:
            errors.append(
                f"{_rel(WORKBENCH_SERVICE)}, {_rel(READINESS_CONTRACT_SERVICE)}, "
                f"or {_rel(EXTERNAL_EXPORT_CONTRACT_SERVICE)} missing package mutation blocked-field term: {term}"
            )

    test_text = _read_required_text(LAYER3_API_TEST, errors)
    for term in (
        "test_layer3_api_package_supersession_preview_inspects_immutable_package_set_without_side_effects",
        "test_layer3_api_package_supersession_preview_prechecks_fail_closed",
        "test_layer3_api_package_supersession_preview_detects_downstream_dependencies",
        "test_layer3_package_supersession_preview_api_boundary_returns_workbench_error_envelope",
        "package_supersession_preview_scope_not_admitted",
        "package_supersession_preview_package_review_submit_record_ref_required",
        "package_supersession_preview_connector_dispatch_record_ref_mismatch",
        "package_construction_commit_scope_not_admitted",
        "package_review_submit_scope_not_admitted",
        "package_review_preview_scope_not_admitted",
        "\"package_payload\"",
        "\"package_variant_content\"",
        "\"rewrite_output\"",
        "\"package_mutation_reconstruction\"",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_API_TEST)} missing package mutation blocked proof term: {term}")


def _check_package_commit_entry_freeze(errors: list[str]) -> None:
    freeze_text = _read_required_text(PACKAGE_COMMIT_FREEZE, errors)
    required_freeze_terms = [
        "Status: implementation-entry freeze plus bounded runtime contract for `package_supersession_commit_entry`.",
        "selected_package_lifecycle_mode: `package_supersession_commit_entry`",
        "selected runtime route: `/api/v1/layer3/package/supersession/commit`",
        "owner service: `backend/app/services/layer3_package_supersession_commit.py`",
        "lineage model: `L3PackageSupersessionCommit`",
        "migration: `0019_layer3_package_supersession_commit.py`",
        "`package_mutation_reconstruction` remains deferred",
        "current admitted package lifecycle runtimes: `package_supersession_preview_only`, `replacement_package_set_authority`, and `package_supersession_commit_entry`",
        "response schema: `layer3.package_supersession_commit.v1`",
        "persistence: `L3PackageSupersessionCommit` via `0019_layer3_package_supersession_commit.py`, not existing package row mutation",
        "`operator_decision` must be exactly `commit_package_supersession`",
        "`replacement_package_set_authority_id`",
        "`replacement_authority_basis_hash`",
        "`commit_basis_hash`",
        "concurrent duplicate commit attempts cannot create duplicate lineage records",
        "no UI control, package row mutation, package payload write, replacement package row creation",
        "authentication/security hardening",
    ]
    for term in required_freeze_terms:
        if term not in freeze_text:
            errors.append(f"{_rel(PACKAGE_COMMIT_FREEZE)} missing package commit freeze term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: [
            "126_PACKAGE_COMMIT_FREEZE.md",
            "package_supersession_commit_entry",
            "durable immutable lineage record",
            "broad runtime package mutation/reconstruction remains not admitted",
        ],
        PACKAGE_MUTATION_FREEZE: [
            "126_PACKAGE_COMMIT_FREEZE.md",
            "package_supersession_commit_entry",
            "durable immutable lineage record",
            "Broad `package_mutation_reconstruction` remains unadmitted after the separate lineage-only commit freeze.",
        ],
        GOAL_AUDIT: [
            "126_PACKAGE_COMMIT_FREEZE.md",
            "bounded package supersession commit lineage runtime is live and tested on current main",
            "L3PackageSupersessionCommit",
            "PR #556 established `L3PackageSupersessionCommit`",
            "`package_supersession_preview_only`, `replacement_package_set_authority`, `package_supersession_commit_entry`, and `replacement_package_artifact_manifest_only`",
        ],
        CLOSEOUT_DOC: [
            "Package supersession commit entry",
            "Implemented and guarded as bounded lineage-only runtime",
            "PR #556 package supersession commit lineage proof",
            "Merged main head after PR #556: 93fe525b.",
            "No package row mutation, package payload write, replacement package row creation",
        ],
        PACKAGE_REPLACEMENT_SET_FREEZE: [
            "selected_package_lifecycle_mode: `replacement_package_set_authority`",
            "/api/v1/layer3/package/replacement-set/record",
            "`package_supersession_commit_entry`",
            "package supersession commit lineage must consume an existing replacement package-set authority",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package commit entry term: {term}")

    admitted = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_ADMITTED_CAPABILITIES", errors),
        "STATE_ACTION_ADMITTED_CAPABILITIES",
        errors,
    )
    deferred = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_DEFERRED_CAPABILITIES", errors),
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        errors,
    )
    commit_entry = admitted.get("package_supersession_commit_entry")
    if commit_entry is None:
        errors.append("admitted capabilities missing package_supersession_commit_entry")
    else:
        if commit_entry.get("admitted") is not True:
            errors.append("package_supersession_commit_entry must be admitted true")
        if commit_entry.get("source_gate") != "126_PACKAGE_COMMIT_FREEZE":
            errors.append("package_supersession_commit_entry source_gate drifted")
        if commit_entry.get("owner_service") != "backend/app/services/layer3_package_supersession_commit.py":
            errors.append("package_supersession_commit_entry owner_service drifted")
        blocked = commit_entry.get("blocked_downstream")
        if not isinstance(blocked, list):
            errors.append("package_supersession_commit_entry missing blocked_downstream list")
        else:
            for term in (
                "package_mutation_reconstruction",
                "package_row_mutation",
                "package_payload_rewrite",
                "provider_public_url",
                "connector_destination_dispatch",
                "local_upload_or_directory_source_expansion",
                "broad_qualitative_execution",
                "hybrid_execution",
                "rag_vector_retrieval",
                "full_mockup_activation",
            ):
                if term not in blocked:
                    errors.append(f"package_supersession_commit_entry blocked_downstream missing {term}")
    package_mutation = deferred.get("package_mutation_reconstruction")
    if package_mutation is None:
        errors.append("deferred capabilities missing package_mutation_reconstruction")
    elif package_mutation.get("admitted") is not False:
        errors.append("package_mutation_reconstruction must remain admitted false after package commit entry freeze")
    preview = admitted.get("package_supersession_preview_only")
    if preview is None or preview.get("admitted") is not True:
        errors.append("package_supersession_preview_only must remain admitted true")
    else:
        blocked = preview.get("blocked_downstream")
        if not isinstance(blocked, list) or "package_supersession_commit_without_replacement_authority" not in blocked:
            errors.append("package_supersession_preview_only must still block commit without replacement authority")

    models_text = _read_required_text(MODELS, errors)
    for term in (
        "class L3PackageSupersessionCommit",
        "UniqueConstraint(\"client_request_id\", name=\"uq_l3_package_supersession_commit_client_request\")",
        "UniqueConstraint(\"commit_basis_hash\", name=\"uq_l3_package_supersession_commit_basis_hash\")",
        "ck_l3_package_supersession_commit_operator_decision",
        "commit_package_supersession",
        "ck_l3_package_supersession_commit_status",
        "ix_l3_package_supersession_commit_replacement_authority",
    ):
        if term not in models_text:
            errors.append(f"{_rel(MODELS)} missing package supersession commit model term: {term}")

    migration_text = _read_required_text(PACKAGE_SUPERSESSION_COMMIT_MIGRATION, errors)
    for term in (
        "revision = \"0019_layer3_package_supersession_commit\"",
        "down_revision = \"0018_layer3_replacement_package_set_authority\"",
        "\"l3_package_supersession_commit\"",
        "sa.UniqueConstraint(\"client_request_id\", name=\"uq_l3_package_supersession_commit_client_request\")",
        "sa.UniqueConstraint(\"commit_basis_hash\", name=\"uq_l3_package_supersession_commit_basis_hash\")",
        "commit_package_supersession",
        "\"ix_l3_package_supersession_commit_session\"",
        "\"ix_l3_package_supersession_commit_reconciliation\"",
        "\"ix_l3_package_supersession_commit_replacement_authority\"",
    ):
        if term not in migration_text:
            errors.append(f"{_rel(PACKAGE_SUPERSESSION_COMMIT_MIGRATION)} missing package supersession commit migration term: {term}")

    service_text = _read_required_text(PACKAGE_SUPERSESSION_COMMIT_SERVICE, errors)
    for term in (
        "PACKAGE_SUPERSESSION_COMMIT_MODE = \"package_supersession_commit_entry\"",
        "PACKAGE_SUPERSESSION_COMMIT_OPERATOR_DECISION = \"commit_package_supersession\"",
        "PACKAGE_SUPERSESSION_COMMIT_FORBIDDEN_FIELDS",
        "package_supersession_downstream_dependency_hash",
        "package_supersession_commit_basis_hash",
        "commit_package_supersession",
        "package_supersession_commit_scope_not_admitted",
        "package_supersession_commit_preview_hash_mismatch",
        "package_supersession_commit_replacement_authority_basis_hash_mismatch",
        "package_supersession_commit_downstream_dependency_hash_mismatch",
        "package_supersession_commit_basis_hash_mismatch",
        "package_supersession_commit_in_progress",
        "\"package_supersession_commit_record_persisted\": True",
        "\"package_row_mutation_enabled\": False",
        "\"package_payload_write_enabled\": False",
        "\"l3_output_package_write_enabled\": False",
        "\"connector_dispatch_enabled\": False",
        "\"provider_public_url_enabled\": False",
        "\"qualitative_hybrid_rag_execution_enabled\": False",
        "\"frontend_only_durable_state_enabled\": False",
    ):
        if term not in service_text:
            errors.append(f"{_rel(PACKAGE_SUPERSESSION_COMMIT_SERVICE)} missing package supersession commit service term: {term}")
    for forbidden in (
        "L3OutputPackage(",
        "AnalysisRun(",
        "AnalysisArtifact(",
        "L3PassRun(",
        "ConnectorRun(",
        "write_bytes(",
    ):
        if forbidden in service_text:
            errors.append(f"{_rel(PACKAGE_SUPERSESSION_COMMIT_SERVICE)} contains forbidden creation/write term: {forbidden}")

    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "Layer3PackageSupersessionCommitRequest",
        "Layer3PackageSupersessionCommitResponse",
        "PACKAGE_SUPERSESSION_COMMIT_REQUEST_SCHEMA",
        "\"/package/supersession/commit\"",
        "commit_package_supersession",
        "\"replacement_output_package_ids\": _forbidden_request_field_schema()",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing package supersession commit API term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    readiness_text = _read_required_text(READINESS_CONTRACT_SERVICE, errors)
    bootstrap_text = _read_required_text(BOOTSTRAP_CONTRACT_SERVICE, errors)
    contract_text = f"{workbench_text}\n{readiness_text}\n{bootstrap_text}"
    for term in (
        "\"package_supersession_commit\"",
        "\"commit_package_supersession\"",
        "\"package_supersession_commit_admitted\": True",
        "\"package_supersession_commit_endpoint\"",
        "\"client_request_id_required_for_package_supersession_commit\": True",
        "\"duplicate_package_supersession_commit\"",
        "\"package_supersession_commit_uses_unique_request_and_basis\": True",
        "durable immutable lineage record",
    ):
        if term not in contract_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} or {_rel(READINESS_CONTRACT_SERVICE)} missing package supersession commit workbench term: {term}")

    state_contract_text = _read_required_text(STATE_ACTION_CONTRACT, errors)
    for term in (
        "\"package_supersession_commit_entry\"",
        "\"owner_service\": \"backend/app/services/layer3_package_supersession_commit.py\"",
        "\"source_gate\": \"126_PACKAGE_COMMIT_FREEZE\"",
        "\"package_supersession_commit\": [package_supersession_commit_operator_decision]",
    ):
        if term not in state_contract_text:
            errors.append(f"{_rel(STATE_ACTION_CONTRACT)} missing package supersession commit state/action term: {term}")

    for path, terms in {
        LAYER3_API_TEST: (
            "test_layer3_api_package_supersession_commit_records_lineage_without_package_mutation",
            "test_layer3_api_package_supersession_commit_prechecks_fail_closed",
            "package_supersession_commit_scope_not_admitted",
            "package_supersession_commit_preview_hash_mismatch",
            "package_supersession_commit_basis_hash_mismatch",
            "package_supersession_commit_record_persisted",
        ),
        PACKAGE_SUPERSESSION_COMMIT_TEST: (
            "test_package_supersession_commit_migration_defines_durable_lineage_constraints",
            "test_package_supersession_commit_concurrent_duplicate_request_records_one_lineage",
            "uq_l3_package_supersession_commit_client_request",
            "uq_l3_package_supersession_commit_basis_hash",
            "package_supersession_commit_in_progress",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package supersession commit proof term: {term}")


def _check_package_replacement_set_freeze(errors: list[str]) -> None:
    freeze_text = _read_required_text(PACKAGE_REPLACEMENT_SET_FREEZE, errors)
    required_freeze_terms = [
        "Status: implementation-entry freeze plus bounded runtime contract for `replacement_package_set_authority`.",
        "selected_package_lifecycle_mode: `replacement_package_set_authority`",
        "current uniqueness blocker: `uq_l3_output_package_session_kind` keeps one output package per `(session_id, package_kind)`",
        "selected runtime route: `/api/v1/layer3/package/replacement-set/record`",
        "owner service: `backend/app/services/layer3_replacement_package_set_authority.py`",
        "authority model: `L3ReplacementPackageSetAuthority`",
        "migration: `0018_layer3_replacement_package_set_authority.py`",
        "current admitted package lifecycle runtimes: `package_supersession_preview_only`, `replacement_package_set_authority`, and `package_supersession_commit_entry`",
        "`package_mutation_reconstruction` remains deferred",
        "This slice selects option A from the freeze",
        "Option B and option C remain deferred",
        "`operator_decision` must be exactly `record_replacement_package_set_authority`",
        "This runtime is acceptable only when tests prove",
        "test_layer3_api_replacement_package_set_authority_records_without_package_row_or_payload_mutation",
        "test_layer3_api_replacement_package_set_authority_prechecks_fail_closed",
        "test_replacement_package_set_authority_concurrent_duplicate_request_records_one_authority",
        "replacement package row creation",
        "replacement package payload creation",
        "authentication/security hardening",
    ]
    for term in required_freeze_terms:
        if term not in freeze_text:
            errors.append(f"{_rel(PACKAGE_REPLACEMENT_SET_FREEZE)} missing replacement package-set term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: [
            "127_PACKAGE_REPLACEMENT_SET_FREEZE.md",
            "replacement_package_set_authority",
            "durable metadata authority record with no replacement package rows",
            "durable immutable lineage record",
        ],
        PACKAGE_COMMIT_FREEZE: [
            "127_PACKAGE_REPLACEMENT_SET_FREEZE.md",
            "bounded metadata-authority runtime",
            "replacement package-set authority prerequisite",
            "broad package mutation/reconstruction remains blocked after this lineage runtime",
        ],
        GOAL_AUDIT: [
            "127_PACKAGE_REPLACEMENT_SET_FREEZE.md",
            "bounded replacement package-set authority runtime is live and tested",
            "unique by `(session_id, package_kind)`",
        ],
        CLOSEOUT_DOC: [
            "Replacement package-set authority",
            "Implemented and guarded as bounded metadata authority runtime",
            "No replacement `L3OutputPackage` rows, replacement payload writes",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing replacement package-set term: {term}")

    models_text = _read_required_text(MODELS, errors)
    for term in (
        "class L3OutputPackage",
        "UniqueConstraint(\"session_id\", \"package_kind\", name=\"uq_l3_output_package_session_kind\")",
        "payload_ref: Mapped[str]",
        "payload_hash: Mapped[str]",
        "class L3ReplacementPackageSetAuthority",
        "UniqueConstraint(\"client_request_id\", name=\"uq_l3_replacement_package_set_client_request\")",
        "UniqueConstraint(\"authority_basis_hash\", name=\"uq_l3_replacement_package_set_basis_hash\")",
        "CheckConstraint(",
        "record_replacement_package_set_authority",
    ):
        if term not in models_text:
            errors.append(f"{_rel(MODELS)} missing replacement package-set model term: {term}")
    for forbidden in (
        "class L3ReplacementPackageSet(",
        "class L3PackageReplacementSet(",
    ):
        if forbidden in models_text:
            errors.append(f"{_rel(MODELS)} contains broad replacement package-set model term: {forbidden}")

    migration_text = _read_required_text(REPLACEMENT_PACKAGE_SET_AUTHORITY_MIGRATION, errors)
    for term in (
        "revision = \"0018_layer3_replacement_package_set_authority\"",
        "down_revision = \"0017_layer3_gate_b_idempotency\"",
        "\"l3_replacement_package_set_authority\"",
        "sa.UniqueConstraint(\"client_request_id\", name=\"uq_l3_replacement_package_set_client_request\")",
        "sa.UniqueConstraint(\"authority_basis_hash\", name=\"uq_l3_replacement_package_set_basis_hash\")",
        "sa.CheckConstraint(",
        "record_replacement_package_set_authority",
        "\"ix_l3_replacement_package_set_session\"",
        "\"ix_l3_replacement_package_set_reconciliation\"",
    ):
        if term not in migration_text:
            errors.append(f"{_rel(REPLACEMENT_PACKAGE_SET_AUTHORITY_MIGRATION)} missing replacement authority migration term: {term}")

    service_text = _read_required_text(REPLACEMENT_PACKAGE_SET_AUTHORITY_SERVICE, errors)
    for term in (
        "REPLACEMENT_PACKAGE_SET_AUTHORITY_MODE = \"replacement_package_set_authority\"",
        "REPLACEMENT_PACKAGE_SET_AUTHORITY_OPERATOR_DECISION = \"record_replacement_package_set_authority\"",
        "REPLACEMENT_PACKAGE_SET_AUTHORITY_FORBIDDEN_FIELDS",
        "replacement_package_set_hash",
        "replacement_package_set_authority_basis_hash",
        "record_replacement_package_set_authority",
        "replacement_package_set_authority_scope_not_admitted",
        "replacement_package_set_authority_source_package_set_hash_mismatch",
        "replacement_package_set_authority_replacement_package_set_hash_mismatch",
        "replacement_package_set_authority_basis_hash_mismatch",
        "replacement_package_set_authority_reuses_source_payload_ref",
        "replacement_package_set_authority_in_progress",
        "\"package_row_mutation_enabled\": False",
        "\"package_payload_write_enabled\": False",
        "\"package_supersession_commit_enabled\": False",
        "\"provider_public_url_enabled\": False",
        "\"qualitative_hybrid_rag_execution_enabled\": False",
    ):
        if term not in service_text:
            errors.append(f"{_rel(REPLACEMENT_PACKAGE_SET_AUTHORITY_SERVICE)} missing replacement authority service term: {term}")
    for forbidden in (
        "L3OutputPackage(",
        "AnalysisRun(",
        "AnalysisArtifact(",
        "L3PassRun(",
        "ConnectorRun(",
        "write_bytes(",
    ):
        if forbidden in service_text:
            errors.append(f"{_rel(REPLACEMENT_PACKAGE_SET_AUTHORITY_SERVICE)} contains forbidden creation/write term: {forbidden}")

    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "Layer3ReplacementPackageSetAuthorityRequest",
        "Layer3ReplacementPackageSetAuthorityResponse",
        "REPLACEMENT_PACKAGE_SET_AUTHORITY_REQUEST_SCHEMA",
        "\"/package/replacement-set/record\"",
        "record_replacement_package_set_authority",
        "\"package_payload\": _forbidden_request_field_schema()",
        "\"package_supersession_commit\": _forbidden_request_field_schema()",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing replacement authority API term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    readiness_text = _read_required_text(READINESS_CONTRACT_SERVICE, errors)
    bootstrap_text = _read_required_text(BOOTSTRAP_CONTRACT_SERVICE, errors)
    contract_text = f"{workbench_text}\n{readiness_text}\n{bootstrap_text}"
    for term in (
        "\"replacement_package_set_authority\"",
        "\"record_replacement_package_set_authority\"",
        "\"replacement_package_set_authority_admitted\": True",
        "\"client_request_id_required_for_replacement_package_set_authority\": True",
        "\"duplicate_replacement_package_set_authority\"",
        "\"replacement_package_set_authority_uses_unique_request_and_basis\": True",
        "record_replacement_package_set_authority",
        "package row mutation, payload writes, and broad package mutation remain blocked",
    ):
        if term not in contract_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} or {_rel(READINESS_CONTRACT_SERVICE)} missing replacement authority workbench term: {term}")

    admitted = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_ADMITTED_CAPABILITIES", errors),
        "STATE_ACTION_ADMITTED_CAPABILITIES",
        errors,
    )
    deferred = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_DEFERRED_CAPABILITIES", errors),
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        errors,
    )
    replacement_authority = admitted.get("replacement_package_set_authority")
    if replacement_authority is None:
        errors.append("admitted capabilities missing replacement_package_set_authority")
    else:
        if replacement_authority.get("admitted") is not True:
            errors.append("replacement_package_set_authority must be admitted true")
        if replacement_authority.get("source_gate") != "127_PACKAGE_REPLACEMENT_SET_FREEZE":
            errors.append("replacement_package_set_authority source_gate drifted")
        if replacement_authority.get("owner_service") != "backend/app/services/layer3_replacement_package_set_authority.py":
            errors.append("replacement_package_set_authority owner_service drifted")
        blocked = replacement_authority.get("blocked_downstream")
        if not isinstance(blocked, list):
            errors.append("replacement_package_set_authority missing blocked_downstream list")
        else:
            for term in (
                "package_mutation_reconstruction",
                "package_supersession_commit_without_dedicated_lineage",
                "package_row_mutation",
                "package_payload_rewrite",
                "provider_public_url",
                "connector_destination_dispatch",
                "local_upload_or_directory_source_expansion",
                "broad_qualitative_execution",
                "hybrid_execution",
                "rag_vector_retrieval",
                "full_mockup_activation",
            ):
                if term not in blocked:
                    errors.append(f"replacement_package_set_authority blocked_downstream missing {term}")
    if "package_supersession_commit" in admitted:
        errors.append("package_supersession_commit action id must not be admitted as a capability")
    package_mutation = deferred.get("package_mutation_reconstruction")
    if package_mutation is None:
        errors.append("deferred capabilities missing package_mutation_reconstruction")
    elif package_mutation.get("admitted") is not False:
        errors.append("package_mutation_reconstruction must remain admitted false after replacement package-set freeze")

    state_contract_text = _read_required_text(STATE_ACTION_CONTRACT, errors)
    for term in (
        "\"replacement_package_set_authority\"",
        "\"owner_service\": \"backend/app/services/layer3_replacement_package_set_authority.py\"",
        "\"source_gate\": \"127_PACKAGE_REPLACEMENT_SET_FREEZE\"",
        "\"record_replacement_package_set_authority\": [replacement_package_set_authority_operator_decision]",
    ):
        if term not in state_contract_text:
            errors.append(f"{_rel(STATE_ACTION_CONTRACT)} missing replacement authority state/action term: {term}")

    for path, terms in {
        LAYER3_API_TEST: (
            "test_layer3_api_replacement_package_set_authority_records_without_package_row_or_payload_mutation",
            "test_layer3_api_replacement_package_set_authority_prechecks_fail_closed",
            "package_row_mutation_enabled",
            "package_payload_write_enabled",
            "package_supersession_commit_enabled",
            "replacement_package_set_authority_scope_not_admitted",
            "replacement_package_set_authority_basis_hash_mismatch",
        ),
        REPLACEMENT_PACKAGE_SET_AUTHORITY_TEST: (
            "test_replacement_package_set_authority_migration_defines_durable_unique_authority",
            "test_replacement_package_set_authority_concurrent_duplicate_request_records_one_authority",
            "uq_l3_replacement_package_set_client_request",
            "uq_l3_replacement_package_set_basis_hash",
            "replacement_package_set_authority_in_progress",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing replacement authority proof term: {term}")


def _check_package_replacement_artifact_freeze(errors: list[str]) -> None:
    freeze_text = _read_required_text(PACKAGE_REPLACEMENT_ARTIFACT_FREEZE, errors)
    required_freeze_terms = (
        "# Layer 3 Package Replacement Artifact Authority Freeze",
        "Status: planning/control freeze only. No runtime behavior is admitted by this document.",
        "baseline_commit: `c8226f74b7e904c931150cce0ef495fd564cf4a4`",
        "`package_supersession_preview_only`, `replacement_package_set_authority`, and `package_supersession_commit_entry`",
        "It does not prove the replacement payload refs exist, were generated by a repo-owned owner service, are readable, or hash to the claimed payload hashes.",
        "selected_future_package_lifecycle_mode: `replacement_package_artifact_authority_only`",
        "This is not live runtime.",
        "replacement package artifacts are server-owned or server-verified immutable artifacts",
        "`replacement_package_artifact_manifest_only`",
        "`replacement_package_artifact_generation_only`",
        "`replacement_package_namespace_rows`",
        "This document selects no runtime option by itself.",
        "exact owner service for replacement artifact generation or verification",
        "replacement payload refs and hashes are server-generated or server-verified before use as package-set authority",
        "package row creation, update, or deletion",
        "replacement `L3OutputPackage` row creation",
        "package payload creation, rewrite, overwrite, deletion, or reconstruction",
        "package payload bytes accepted from the browser",
        "rendered package mutation controls",
        "`L3PassRun` creation",
        "`AnalysisRun` creation",
        "`AnalysisArtifact` creation",
        "`L3ReconciliationRecord` creation, update, or deletion",
        "authentication/security hardening",
        "tools/l3-progress-check.py` fails closed if this freeze is missing",
    )
    for term in required_freeze_terms:
        if term not in freeze_text:
            errors.append(f"{_rel(PACKAGE_REPLACEMENT_ARTIFACT_FREEZE)} missing package artifact freeze term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: (
            "128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md",
            "replacement_package_artifact_authority_only",
            "planning/control prerequisite",
            "server-owned or server-verified",
        ),
        SYNTHESIS_BOUNDARY: (
            "128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md",
            "planning/control freeze only",
            "Current `replacement_package_set_authority` metadata is not proof",
            "replacement_package_artifact_authority_only",
        ),
        GOAL_AUDIT: (
            "Doc `128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md` is planning/control only.",
            "planning-only `replacement_package_artifact_authority_only`",
            "future package lifecycle freeze for replacement package artifact generation",
        ),
        CLOSEOUT_DOC: (
            "package replacement artifact authority row is planning/control only",
            "128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md",
            "replacement_package_artifact_authority_only",
            "planning-only prerequisite for artifact generation",
        ),
        MANIFEST: (
            "128_PACKAGE_REPLACEMENT_ARTIFACT_FREEZE.md",
            "replacement_package_artifact_authority_only",
            "Docs 122, 126, 127, and 129 govern the current package lifecycle runtimes only",
            "blocks replacement package artifact generation until a later freeze names that surface",
        ),
        BOARD: (
            "Current package planning/control correction",
            "Package replacement artifact authority freeze",
            "replacement_package_artifact_authority_only",
            "not proof that replacement payload bytes exist",
        ),
        PROOF_MANIFEST: (
            "package_replacement_artifact_authority_planning_control_proof",
            "latest_package_replacement_artifact_freeze_branch",
            "replacement_package_artifact_authority_only",
            "does not prove replacement payload bytes exist",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package artifact freeze term: {term}")

    admitted = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_ADMITTED_CAPABILITIES", errors),
        "STATE_ACTION_ADMITTED_CAPABILITIES",
        errors,
    )
    deferred = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_DEFERRED_CAPABILITIES", errors),
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        errors,
    )
    if "replacement_package_artifact_authority_only" in admitted:
        errors.append("replacement_package_artifact_authority_only must not be admitted as a live capability")
    package_mutation = deferred.get("package_mutation_reconstruction")
    if package_mutation is None:
        errors.append("deferred capabilities missing package_mutation_reconstruction")
    elif package_mutation.get("admitted") is not False:
        errors.append("package_mutation_reconstruction must remain admitted false after package artifact freeze")
    for capability in (
        "package_supersession_preview_only",
        "replacement_package_set_authority",
        "package_supersession_commit_entry",
    ):
        item = admitted.get(capability)
        if item is None or item.get("admitted") is not True:
            errors.append(f"{capability} must remain the only admitted package lifecycle capability set")


def _check_package_replacement_artifact_manifest_freeze(errors: list[str]) -> None:
    freeze_text = _read_required_text(PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE, errors)
    required_freeze_terms = (
        "# Layer 3 Replacement Package Artifact Manifest Freeze",
        "Status: implementation-entry freeze only for `replacement_package_artifact_manifest_only`. No runtime behavior is admitted by this document.",
        "baseline_commit: `156e18517352d844da43afa457264908a6c2f525`",
        "selected_package_artifact_authority_mode: `replacement_package_artifact_manifest_only`",
        "future runtime route: `/api/v1/layer3/package/replacement-artifact/manifest/record`",
        "future owner service: `backend/app/services/layer3_replacement_package_artifact_manifest.py`",
        "future authority model: `L3ReplacementPackageArtifactManifest`",
        "future migration: `0020_layer3_replacement_package_artifact_manifest.py`",
        "manifest-only",
        "It must not create, rewrite, upload, or reconstruct package bytes.",
        "replacement package artifacts are server-side manifest verified",
        "`replacement_package_artifact_manifest_only` is the only selected artifact authority mode",
        "no replacement `L3OutputPackage` rows are created",
        "no replacement package payload files are created or rewritten",
        "no browser-provided package bytes are accepted",
        "replacement package artifact generation",
        "replacement `L3OutputPackage` row creation",
        "package payload creation, rewrite, overwrite, deletion, or reconstruction",
        "`L3PassRun` creation",
        "`AnalysisRun` creation",
        "`AnalysisArtifact` creation",
        "`L3ReconciliationRecord` creation, update, or deletion",
        "authentication/security hardening",
        "tools/l3-progress-check.py` fails closed if this freeze is missing",
    )
    for term in required_freeze_terms:
        if term not in freeze_text:
            errors.append(f"{_rel(PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE)} missing package artifact manifest freeze term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: (
            "129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md",
            "replacement_package_artifact_manifest_only",
            "server-side manifest verification through `/api/v1/layer3/package/replacement-artifact/manifest/record`",
            "no package payload write, no replacement package row, no artifact generation",
        ),
        SYNTHESIS_BOUNDARY: (
            "129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md",
            "replacement_package_artifact_manifest_only",
            "live runtime is bounded to `/api/v1/layer3/package/replacement-artifact/manifest/record`",
            "backend/tests/test_layer3_replacement_package_artifact_manifest.py",
            "keep `replacement_package_artifact_manifest_only` live only as the exact server-verified manifest-only runtime",
            "Latest merged-main authority rechecked before this namespace runtime slice: `project6-origin/main` at `c208c424` after PR #592.",
        ),
        GOAL_AUDIT: (
            "Doc `129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md` remains the implementation-entry planning authority",
            "replacement_package_artifact_manifest_only",
            "bounded runtime now adds `/api/v1/layer3/package/replacement-artifact/manifest/record`",
        ),
        CLOSEOUT_DOC: (
            "package replacement artifact manifest row admits only the exact `/api/v1/layer3/package/replacement-artifact/manifest/record`",
            "129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md",
            "replacement_package_artifact_manifest_only",
            "The manifest route records immutable server-side verification only",
        ),
        MANIFEST: (
            "129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE.md",
            "package_replacement_artifact_manifest_runtime",
            "replacement_package_artifact_manifest_only",
            "backend/app/services/layer3_replacement_package_artifact_manifest.py",
        ),
        BOARD: (
            "Current package manifest runtime correction",
            "Package replacement artifact manifest runtime",
            "replacement_package_artifact_manifest_only",
            "live bounded implementation",
        ),
        PROOF_MANIFEST: (
            "package_replacement_artifact_manifest_runtime_proof",
            "latest_package_replacement_artifact_manifest_runtime_branch",
            "replacement_package_artifact_manifest_only",
            "without generating payload bytes or creating replacement package rows",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package artifact manifest freeze term: {term}")
        if path == SYNTHESIS_BOUNDARY:
            for stale_term in (
                "keep `replacement_package_artifact_manifest_only` planning-only until a later implementation PR",
                "Current merged-main authority after PR #584",
                "proof against `9cdd1e88`",
            ):
                if stale_term in text:
                    errors.append(f"{_rel(path)} contains stale package artifact manifest guardrail term: {stale_term}")

    proof_manifest = _load_json(PROOF_MANIFEST, errors)
    if isinstance(proof_manifest, dict):
        status = proof_manifest.get("status")
        if not isinstance(status, str) or "package replacement artifact manifest-only runtime" not in status:
            errors.append(f"{_rel(PROOF_MANIFEST)} status must name the package artifact manifest runtime proof boundary")
        proof_scope = proof_manifest.get("scope")
        if not isinstance(proof_scope, dict):
            errors.append(f"{_rel(PROOF_MANIFEST)} missing scope metadata")
        else:
            expected_scope = {
                "latest_package_replacement_artifact_manifest_runtime_pr": "#588",
                "latest_package_replacement_artifact_manifest_runtime_merge_commit": "e17e22afce24a69a300bd90f1af13046edf6b246",
            }
            for key, expected_value in expected_scope.items():
                if proof_scope.get(key) != expected_value:
                    errors.append(f"{_rel(PROOF_MANIFEST)} scope.{key} must be {expected_value}")
        manifest_proof = proof_manifest.get("package_replacement_artifact_manifest_runtime_proof")
        if not isinstance(manifest_proof, dict):
            errors.append(f"{_rel(PROOF_MANIFEST)} missing package artifact manifest runtime proof metadata")
        else:
            expected_proof = {
                "implementation_branch": "codex/l3-package-artifact-manifest-runtime",
                "implementation_pr": "#588",
                "base_commit": "c4186ae3a7fe0be2ba97defd743777ff14bc381d",
                "implementation_commit": "947adcd337722a0bec31e87c1b7e361ba8ed7908",
                "merge_commit": "e17e22afce24a69a300bd90f1af13046edf6b246",
            }
            for key, expected_value in expected_proof.items():
                if manifest_proof.get(key) != expected_value:
                    errors.append(
                        f"{_rel(PROOF_MANIFEST)} package_replacement_artifact_manifest_runtime_proof.{key} "
                        f"must be {expected_value}"
                    )

    admitted = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_ADMITTED_CAPABILITIES", errors),
        "STATE_ACTION_ADMITTED_CAPABILITIES",
        errors,
    )
    deferred = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_DEFERRED_CAPABILITIES", errors),
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        errors,
    )
    manifest_capability = admitted.get("replacement_package_artifact_manifest_only")
    if manifest_capability is None:
        errors.append("replacement_package_artifact_manifest_only must be admitted after manifest runtime implementation")
    else:
        if manifest_capability.get("admitted") is not True:
            errors.append("replacement_package_artifact_manifest_only admitted flag must be true after implementation")
        if manifest_capability.get("source_gate") != "129_PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE":
            errors.append("replacement_package_artifact_manifest_only source_gate drifted")
        if (
            manifest_capability.get("owner_service")
            != "backend/app/services/layer3_replacement_package_artifact_manifest.py"
        ):
            errors.append("replacement_package_artifact_manifest_only owner_service drifted")
        blocked = manifest_capability.get("blocked_downstream")
        if not isinstance(blocked, list):
            errors.append("replacement_package_artifact_manifest_only missing blocked_downstream list")
        else:
            for blocked_capability in (
                "package_mutation_reconstruction",
                "replacement_package_artifact_generation",
                "replacement_output_package_rows",
                "package_payload_rewrite",
                "provider_public_url",
                "connector_destination_dispatch",
                "local_upload_or_directory_source_expansion",
                "broad_qualitative_execution",
                "full_mockup_activation",
            ):
                if blocked_capability not in blocked:
                    errors.append(
                        "replacement_package_artifact_manifest_only missing blocked downstream "
                        f"capability: {blocked_capability}"
                    )
    package_mutation = deferred.get("package_mutation_reconstruction")
    if package_mutation is None:
        errors.append("deferred capabilities missing package_mutation_reconstruction")
    elif package_mutation.get("admitted") is not False:
        errors.append("package_mutation_reconstruction must remain admitted false after package artifact manifest freeze")
    for capability in (
        "package_supersession_preview_only",
        "replacement_package_set_authority",
        "package_supersession_commit_entry",
        "replacement_package_artifact_manifest_only",
    ):
        item = admitted.get(capability)
        if item is None or item.get("admitted") is not True:
            errors.append(f"{capability} must remain admitted while artifact manifest runtime is live")

    required_runtime_terms = {
        REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_SERVICE: (
            "REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_MODE",
            "record_replacement_package_artifact_manifest",
            "replacement_package_artifact_manifest_authority_basis_hash",
            "artifact_generation_enabled",
            "package_row_mutation_enabled",
            "provider_public_url_enabled",
            "connector_dispatch_enabled",
        ),
        REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_MIGRATION: (
            "0020_layer3_replacement_package_artifact_manifest",
            "l3_replacement_package_artifact_manifest",
            "uq_l3_replacement_artifact_manifest_client_request",
            "uq_l3_replacement_artifact_manifest_basis_hash",
        ),
        MODELS: (
            "class L3ReplacementPackageArtifactManifest",
            "uq_l3_replacement_artifact_manifest_client_request",
            "ck_l3_replacement_artifact_manifest_operator_decision",
            "verified_artifact_refs_json",
        ),
        LAYER3_API: (
            "Layer3ReplacementPackageArtifactManifestRequest",
            "Layer3ReplacementPackageArtifactManifestResponse",
            '"/package/replacement-artifact/manifest/record"',
            "record_replacement_package_artifact_manifest",
        ),
        REPLACEMENT_PACKAGE_ARTIFACT_MANIFEST_TEST: (
            "test_replacement_package_artifact_manifest_records_server_verified_manifest_only",
            "test_replacement_package_artifact_manifest_prechecks_fail_closed",
            "test_replacement_package_artifact_manifest_rejects_hash_mismatch_outside_namespace_and_source_ref_reuse",
            "test_replacement_package_artifact_manifest_concurrent_duplicate_request_records_one_manifest",
        ),
    }
    for path, terms in required_runtime_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package artifact manifest runtime term: {term}")


def _check_package_replacement_namespace_freeze(errors: list[str]) -> None:
    freeze_text = _read_required_text(PACKAGE_REPLACEMENT_NAMESPACE_FREEZE, errors)
    required_freeze_terms = (
        "# Layer 3 Replacement Package Namespace Freeze",
        "Status: planning/control freeze only for `replacement_package_namespace_rows`",
        "baseline_commit: `f4698f7cdc1cb1ddd01511eb47de5ad37f1b8b56`",
        "current output package model: `backend/app/models/models.py` `L3OutputPackage`",
        "current uniqueness blocker: `uq_l3_output_package_session_kind`",
        "selected_future_package_lifecycle_mode: `replacement_package_namespace_rows`",
        "selected_namespace_design: `separate_replacement_output_package_table`",
        "future owner surface: package namespace authority only; no payload generation or payload rewrite",
        "This is not live runtime.",
        "separate replacement table",
        "must not weaken, remove, or reinterpret `uq_l3_output_package_session_kind`",
        "existing `L3OutputPackage` rows remain immutable source authority",
        "replacement package row authority uses a separate table",
        "replacement row creation is impossible without an existing verified replacement artifact manifest",
        "replacement row creation is impossible without existing package supersession lineage",
        "runtime behavior",
        "replacement `L3OutputPackage` row creation in the source table",
        "weakening or removing `uq_l3_output_package_session_kind`",
        "package payload creation, rewrite, overwrite, deletion, or reconstruction",
        "connector/destination dispatch changes",
        "provider/public URL support",
        "source/upload/local-directory/RAG/vector expansion",
        "qualitative/hybrid/RAG execution",
        "`L3PassRun` creation",
        "`AnalysisRun` creation",
        "`AnalysisArtifact` creation",
        "`L3ReconciliationRecord` creation, update, or deletion",
        "frontend-only durable state",
        "hidden LLM planning",
        "full mockup activation",
        "authentication/security hardening",
        "tools/l3-progress-check.py` fails closed if this freeze is missing",
    )
    for term in required_freeze_terms:
        if term not in freeze_text:
            errors.append(f"{_rel(PACKAGE_REPLACEMENT_NAMESPACE_FREEZE)} missing package namespace freeze term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: (
            "130_PACKAGE_REPLACEMENT_NAMESPACE_FREEZE.md",
            "selected_namespace_design: separate_replacement_output_package_table",
            "preserving `uq_l3_output_package_session_kind`",
            "selected `replacement_package_namespace_rows` with `selected_namespace_design: separate_replacement_output_package_table`",
        ),
        SYNTHESIS_BOUNDARY: (
            "130_PACKAGE_REPLACEMENT_NAMESPACE_FREEZE.md",
            "replacement_package_namespace_rows",
            "preserves the existing `L3OutputPackage` source-row authority",
            "planning/control predecessor for `replacement_package_namespace_rows`",
            "uq_l3_output_package_session_kind",
        ),
        GOAL_AUDIT: (
            "Doc `130_PACKAGE_REPLACEMENT_NAMESPACE_FREEZE.md` is planning/control only.",
            "`selected_namespace_design: separate_replacement_output_package_table`",
            "selected_namespace_design: separate_replacement_output_package_table",
            "future package lifecycle freeze for replacement package artifact generation",
        ),
        CLOSEOUT_DOC: (
            "package replacement namespace design row is planning/control only",
            "selected_namespace_design: separate_replacement_output_package_table",
            "planning/control-only replacement package namespace rows freeze",
            "uq_l3_output_package_session_kind",
        ),
        MANIFEST: (
            "package_replacement_namespace_freeze",
            "replacement_package_namespace_rows",
            "selected_namespace_design",
            "separate_replacement_output_package_table",
            "\"live_behavior_change\": false",
            "uq_l3_output_package_session_kind",
        ),
        BOARD: (
            "Current package namespace planning/control correction",
            "Package replacement namespace freeze",
            "replacement_package_namespace_rows",
            "uq_l3_output_package_session_kind",
        ),
        PROOF_MANIFEST: (
            "package_replacement_namespace_freeze_proof",
            "latest_package_replacement_namespace_freeze_branch",
            "codex/l3-package-namespace-freeze",
            "replacement_package_namespace_rows",
            "uq_l3_output_package_session_kind",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package namespace freeze term: {term}")

    models_text = _read_required_text(MODELS, errors)
    for term in (
        "class L3OutputPackage",
        "UniqueConstraint(\"session_id\", \"package_kind\", name=\"uq_l3_output_package_session_kind\")",
    ):
        if term not in models_text:
            errors.append(f"{_rel(MODELS)} missing source output-package namespace term: {term}")
    package_entry_migration_text = _read_required_text(PACKAGE_ENTRY_MIGRATION, errors)
    for term in (
        "\"l3_output_package\"",
        "sa.UniqueConstraint(\"session_id\", \"package_kind\", name=\"uq_l3_output_package_session_kind\")",
    ):
        if term not in package_entry_migration_text:
            errors.append(f"{_rel(PACKAGE_ENTRY_MIGRATION)} missing source output-package migration term: {term}")

    admitted = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_ADMITTED_CAPABILITIES", errors),
        "STATE_ACTION_ADMITTED_CAPABILITIES",
        errors,
    )
    deferred = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_DEFERRED_CAPABILITIES", errors),
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        errors,
    )
    for capability in (
        "replacement_output_package_rows",
        "package_mutation_reconstruction",
    ):
        if capability in admitted:
            errors.append(f"{capability} must not be admitted by package namespace planning/control freeze")
    package_mutation = deferred.get("package_mutation_reconstruction")
    if package_mutation is None:
        errors.append("deferred capabilities missing package_mutation_reconstruction")
    elif package_mutation.get("admitted") is not False:
        errors.append("package_mutation_reconstruction must remain admitted false after package namespace freeze")


def _check_package_replacement_namespace_entry_freeze(errors: list[str]) -> None:
    freeze_text = _read_required_text(PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE, errors)
    required_freeze_terms = (
        "# Layer 3 Replacement Package Namespace Entry Freeze",
        "Status: live bounded runtime for `replacement_package_namespace_rows`",
        "baseline_commit: `c208c424bda012892c0dab7412fd2cb6a1fbb460`",
        "selected_package_lifecycle_mode: `replacement_package_namespace_rows`",
        "selected_namespace_design: `separate_replacement_output_package_table`",
        "runtime route: `/api/v1/layer3/package/replacement-namespace/record`",
        "owner service: `backend/app/services/layer3_replacement_package_namespace.py`",
        "authority model: `L3ReplacementOutputPackage`",
        "table: `l3_replacement_output_package`",
        "migration: `0021_layer3_replacement_output_package.py`",
        "request DTO: `Layer3ReplacementPackageNamespaceRecordRequest`",
        "response DTO: `Layer3ReplacementPackageNamespaceRecordResponse`",
        "This document now governs the bounded runtime route, service, model, migration, DTOs, and row contract.",
        "uq_l3_replacement_output_package_manifest_kind",
        "uq_l3_replacement_output_package_client_request",
        "uq_l3_replacement_output_package_basis_hash",
        "operator_decision == \"record_replacement_package_namespace\"",
        "duplicate `client_request_id` with the same basis is deterministic",
        "duplicate `client_request_id` with a different basis fails closed",
        "package_mutation_reconstruction` remains deferred",
        "replacement package row creation",
        "source `L3OutputPackage` row creation, update, or deletion",
        "weakening or removing `uq_l3_output_package_session_kind`",
        "package payload creation, rewrite, overwrite, deletion, or reconstruction",
        "replacement package artifact generation",
        "connector/destination dispatch changes",
        "provider/public URL support",
        "source/upload/local-directory/RAG/vector expansion",
        "qualitative/hybrid/RAG execution",
        "`L3PassRun` creation",
        "`AnalysisRun` creation",
        "`AnalysisArtifact` creation",
        "`L3ReconciliationRecord` creation, update, or deletion",
        "authentication/security hardening",
        "tools/l3-progress-check.py` fails closed if this runtime contract is missing",
    )
    for term in required_freeze_terms:
        if term not in freeze_text:
            errors.append(f"{_rel(PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE)} missing package namespace entry term: {term}")

    required_doc_terms = {
        DEFERRED_GATES: (
            "131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE.md",
            "live bounded `replacement_package_namespace_rows` runtime",
            "/api/v1/layer3/package/replacement-namespace/record",
            "no source `L3OutputPackage` row mutation",
            "broad package mutation/reconstruction remains blocked",
        ),
        SYNTHESIS_BOUNDARY: (
            "131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE.md",
            "/api/v1/layer3/package/replacement-namespace/record",
            "L3ReplacementOutputPackage",
            "live bounded runtime",
            "no source package row mutation",
        ),
        GOAL_AUDIT: (
            "Doc `131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE.md` now governs the live bounded `replacement_package_namespace_rows` runtime.",
            "Layer3ReplacementPackageNamespaceRecordRequest",
            "Layer3ReplacementPackageNamespaceRecordResponse",
            "broad package mutation/reconstruction remains blocked",
        ),
        CLOSEOUT_DOC: (
            "package replacement namespace rows are live only in `l3_replacement_output_package`",
            "route/service/model/table/migration/DTO/idempotency/test contracts",
            "bounded replacement package namespace runtime",
        ),
        MANIFEST: (
            "package_replacement_namespace_runtime",
            "131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE",
            "/api/v1/layer3/package/replacement-namespace/record",
            "Layer3ReplacementPackageNamespaceRecordRequest",
            "\"live_behavior_change\": true",
        ),
        BOARD: (
            "Current package namespace runtime correction",
            "Package replacement namespace runtime",
            "live bounded runtime",
            "L3ReplacementOutputPackage",
        ),
        PROOF_MANIFEST: (
            "package_replacement_namespace_runtime_proof",
            "latest_package_replacement_namespace_runtime_branch",
            "codex/l3-package-namespace-runtime",
            "Layer3ReplacementPackageNamespaceRecordResponse",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package namespace entry term: {term}")

    models_text = _read_required_text(MODELS, errors)
    package_entry_migration_text = _read_required_text(PACKAGE_ENTRY_MIGRATION, errors)
    for path, text, term in (
        (MODELS, models_text, "UniqueConstraint(\"session_id\", \"package_kind\", name=\"uq_l3_output_package_session_kind\")"),
        (PACKAGE_ENTRY_MIGRATION, package_entry_migration_text, "sa.UniqueConstraint(\"session_id\", \"package_kind\", name=\"uq_l3_output_package_session_kind\")"),
    ):
        if term not in text:
            errors.append(f"{_rel(path)} missing preserved source package uniqueness term: {term}")

    admitted = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_ADMITTED_CAPABILITIES", errors),
        "STATE_ACTION_ADMITTED_CAPABILITIES",
        errors,
    )
    deferred = _capability_map(
        _load_literal_assignment(STATE_ACTION_CONTRACT, "STATE_ACTION_DEFERRED_CAPABILITIES", errors),
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        errors,
    )
    namespace_capability = admitted.get("replacement_package_namespace_rows")
    if namespace_capability is None:
        errors.append("replacement_package_namespace_rows must be admitted after namespace runtime implementation")
    else:
        if namespace_capability.get("admitted") is not True:
            errors.append("replacement_package_namespace_rows admitted flag must be true after implementation")
        if namespace_capability.get("source_gate") != "131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE":
            errors.append("replacement_package_namespace_rows source_gate drifted")
        if (
            namespace_capability.get("owner_service")
            != "backend/app/services/layer3_replacement_package_namespace.py"
        ):
            errors.append("replacement_package_namespace_rows owner_service drifted")
        blocked_downstream = namespace_capability.get("blocked_downstream")
        if not isinstance(blocked_downstream, list):
            errors.append("replacement_package_namespace_rows missing blocked_downstream list")
        else:
            for blocked in (
                "package_mutation_reconstruction",
                "package_payload_rewrite",
                "replacement_package_artifact_generation",
                "source_l3_output_package_mutation",
                "provider_public_url",
                "connector_destination_dispatch",
                "local_upload_or_directory_source_expansion",
                "broad_qualitative_execution",
                "hybrid_execution",
                "rag_vector_retrieval",
                "full_mockup_activation",
            ):
                if blocked not in blocked_downstream:
                    errors.append(
                        "replacement_package_namespace_rows missing blocked downstream "
                        f"capability: {blocked}"
                    )
    package_mutation = deferred.get("package_mutation_reconstruction")
    if package_mutation is None:
        errors.append("deferred capabilities missing package_mutation_reconstruction")
    elif package_mutation.get("admitted") is not False:
        errors.append("package_mutation_reconstruction must remain admitted false after namespace entry freeze")

    required_runtime_terms = {
        MODELS: (
            "class L3ReplacementOutputPackage",
            "__tablename__ = \"l3_replacement_output_package\"",
            "uq_l3_replacement_output_package_manifest_kind",
            "uq_l3_replacement_output_package_client_request",
            "uq_l3_replacement_output_package_basis_hash",
            "record_replacement_package_namespace",
        ),
        REPLACEMENT_PACKAGE_NAMESPACE_MIGRATION: (
            "0021_layer3_replacement_output_package",
            "0020_layer3_replacement_package_artifact_manifest",
            "\"l3_replacement_output_package\"",
            "uq_l3_replacement_output_package_manifest_kind",
            "uq_l3_replacement_output_package_client_request",
            "uq_l3_replacement_output_package_basis_hash",
            "record_replacement_package_namespace",
        ),
        REPLACEMENT_PACKAGE_NAMESPACE_SERVICE: (
            "REPLACEMENT_PACKAGE_NAMESPACE_MODE = \"replacement_package_namespace_rows\"",
            "REPLACEMENT_PACKAGE_NAMESPACE_SOURCE_GATE = \"131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE\"",
            "REPLACEMENT_PACKAGE_NAMESPACE_OPERATOR_DECISION = \"record_replacement_package_namespace\"",
            "replacement_package_namespace_authority_basis_hash",
            "record_replacement_package_namespace",
            "L3ReplacementOutputPackage",
            "replacement_package_namespace_source_payload_mismatch",
            "replacement_package_namespace_scope_not_admitted",
        ),
        LAYER3_API: (
            "Layer3ReplacementPackageNamespaceRecordRequest",
            "Layer3ReplacementPackageNamespaceRecordResponse",
            "\"/package/replacement-namespace/record\"",
            "layer3_replacement_package_namespace.record_replacement_package_namespace",
        ),
        STATE_MODEL_CONTRACT_SERVICE: (
            "\"replacement_package_namespace\"",
        ),
        STATE_ACTION_CONTRACT: (
            "\"capability\": \"replacement_package_namespace_rows\"",
            "\"source_gate\": \"131_PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE\"",
            "\"owner_service\": \"backend/app/services/layer3_replacement_package_namespace.py\"",
            "\"replacement_package_namespace\": [replacement_package_namespace_operator_decision]",
        ),
        READINESS_CONTRACT_SERVICE: (
            "replacement_package_namespace_admitted",
            "replacement_package_namespace_endpoint",
            "client_request_id_required_for_replacement_package_namespace",
            "duplicate_replacement_package_namespace",
            "replacement_package_namespace_uses_separate_replacement_table",
        ),
        BOOTSTRAP_CONTRACT_SERVICE: (
            "\"replacement_package_namespace\": True",
            "replacement_package_namespace_admitted",
            "replacement_package_namespace_endpoint",
        ),
        REPLACEMENT_PACKAGE_NAMESPACE_TEST: (
            "test_replacement_package_namespace_migration_defines_durable_namespace_constraints",
            "test_replacement_package_namespace_records_separate_row_without_package_mutation",
            "test_replacement_package_namespace_prechecks_fail_closed",
            "test_replacement_package_namespace_concurrent_duplicate_request_records_one_row",
        ),
        LAYER3_API_TEST: (
            "test_layer3_replacement_package_namespace_api_boundary_returns_workbench_error_envelope",
            "/api/v1/layer3/package/replacement-namespace/record",
            "replacement_package_namespace_rows",
            "record_replacement_package_namespace",
        ),
    }
    for path, terms in required_runtime_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package namespace runtime term: {term}")


def _check_qualitative_capability_boundary(errors: list[str]) -> None:
    admitted = _capability_map(
        _load_literal_assignment(
            STATE_ACTION_CONTRACT, "STATE_ACTION_ADMITTED_CAPABILITIES", errors
        ),
        "STATE_ACTION_ADMITTED_CAPABILITIES",
        errors,
    )
    deferred = _capability_map(
        _load_literal_assignment(
            STATE_ACTION_CONTRACT, "STATE_ACTION_DEFERRED_CAPABILITIES", errors
        ),
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        errors,
    )

    exact = admitted.get("single_aps_doc_qualitative_execution")
    if exact is None:
        errors.append(
            "state/action contract missing admitted exact capability: "
            "single_aps_doc_qualitative_execution"
        )
    else:
        if exact.get("admitted") is not True:
            errors.append("single_aps_doc_qualitative_execution must be admitted true")
        if exact.get("source_gate") != "119_L3_QUAL_APS_EXEC_ENTRY_FREEZE":
            errors.append("single_aps_doc_qualitative_execution source_gate drifted")
        if exact.get("owner_service") != "backend/app/services/layer3_qual_aps_execution.py":
            errors.append("single_aps_doc_qualitative_execution owner_service drifted")
        blocked = exact.get("blocked_downstream")
        if not isinstance(blocked, list):
            errors.append("single_aps_doc_qualitative_execution missing blocked_downstream list")
        else:
            for term in (
                "qualitative_package_handoff_export",
                "broad_qualitative_execution",
                "hybrid_execution",
                "rag_vector_retrieval",
                "full_mockup_activation",
            ):
                if term not in blocked:
                    errors.append(
                        "single_aps_doc_qualitative_execution blocked_downstream "
                        f"missing {term}"
                    )

    if "qualitative_execution" in deferred:
        errors.append(
            "deferred capabilities must use broad_qualitative_execution, "
            "not ambiguous qualitative_execution"
        )

    expected_deferred = {
        "broad_qualitative_execution": "single_aps_doc_qualitative_pass_only",
        "hybrid_execution": None,
        "rag_vector_retrieval": None,
        "local_upload_or_directory_source_expansion": None,
        "provider_public_url": None,
        "connector_destination_dispatch": None,
        "package_mutation_reconstruction": None,
        "frontend_only_durable_state": None,
        "full_mockup_activation": "mockups_target_state_only",
        "hidden_llm_planning": None,
        "auth_security_hardening": "deferred_by_operator_instruction",
    }
    for capability, expected_reason in expected_deferred.items():
        item = deferred.get(capability)
        if item is None:
            errors.append(f"deferred capabilities missing {capability}")
            continue
        if item.get("admitted") is not False:
            errors.append(f"{capability} must remain admitted false")
        if expected_reason is not None and item.get("reason") != expected_reason:
            errors.append(f"{capability} reason drifted from {expected_reason}")
        if capability in admitted:
            errors.append(f"{capability} must not also appear as an admitted capability")

    expected_qual_deferred = (
        "broad_qualitative_execution",
        "qualitative_associated_cohort_execution",
        "comparative_qualitative_execution",
        "cross_document_synthesis",
        "hybrid_execution",
        "rag_vector_retrieval",
        "hidden_llm_planning",
        "qualitative_package_handoff_export",
    )
    expected_qual_forbidden_fields = (
        "qualitative_plan",
        "hybrid_plan",
        "rag_plan",
        "vector_plan",
        "run_all",
        "artifact_manifest",
        "package_payload",
        "package_variant_content",
        "rewrite_output",
        "connector_id",
        "destination_id",
        "provider_url",
        "public_url",
        "source_upload",
        "schema_migration",
        "runtime_db_write",
        "hidden_llm_plan",
    )
    qual_deferred = _load_literal_assignment(
        QUAL_APS_SERVICE, "QUALITATIVE_BOUNDARY_DEFERRED_CAPABILITIES", errors
    )
    qual_forbidden = _load_literal_assignment(
        QUAL_APS_SERVICE, "QUALITATIVE_BOUNDARY_FORBIDDEN_RUNTIME_FIELDS", errors
    )
    if qual_deferred != expected_qual_deferred:
        errors.append(
            "qualitative boundary deferred capabilities drifted: "
            f"expected {expected_qual_deferred!r}, found {qual_deferred!r}"
        )
    if qual_forbidden != expected_qual_forbidden_fields:
        errors.append(
            "qualitative boundary forbidden runtime fields drifted: "
            f"expected {expected_qual_forbidden_fields!r}, found {qual_forbidden!r}"
        )

    qual_service_text = _read_required_text(QUAL_APS_SERVICE, errors)
    for term in (
        "QUALITATIVE_BOUNDARY_CONTRACT_SCHEMA_ID = \"layer3.qualitative_hybrid_rag_boundary_contract.v1\"",
        "QUALITATIVE_BOUNDARY_MODE = \"single_aps_doc_qualitative_pass_only\"",
        "def qualitative_hybrid_rag_boundary_contract(",
        "\"single_aps_doc_qualitative_execution_enabled\": True",
        "\"broad_qualitative_execution_enabled\": False",
        "\"qualitative_associated_cohort_execution_enabled\": False",
        "\"comparative_qualitative_execution_enabled\": False",
        "\"cross_document_synthesis_enabled\": False",
        "\"hybrid_execution_enabled\": False",
        "\"rag_vector_retrieval_enabled\": False",
        "\"hidden_llm_planning_enabled\": False",
        "\"qualitative_package_handoff_export_enabled\": False",
        "\"source_widening_enabled\": False",
        "\"connector_destination_dispatch_enabled\": False",
        "\"package_mutation_reconstruction_enabled\": False",
        "\"requires_later_freeze\": True",
    ):
        if term not in qual_service_text:
            errors.append(f"{_rel(QUAL_APS_SERVICE)} missing qualitative contract term: {term}")

    qual_test_text = _read_required_text(QUAL_APS_TEST, errors)
    for term in expected_qual_deferred + expected_qual_forbidden_fields:
        if term not in qual_test_text:
            errors.append(f"{_rel(QUAL_APS_TEST)} missing qualitative boundary proof term: {term}")
    if "test_qualitative_hybrid_rag_boundary_contract_keeps_broad_execution_fail_closed" not in qual_test_text:
        errors.append(f"{_rel(QUAL_APS_TEST)} missing qualitative boundary contract proof")
    for term in (
        "test_single_aps_doc_qualitative_owner_error_maps_without_side_effects",
        "Layer3QualApsExecutionError",
        "analysis_execution_start_not_admitted",
        "} == counts_before",
    ):
        if term not in qual_test_text:
            errors.append(f"{_rel(QUAL_APS_TEST)} missing qualitative owner-service error proof term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    readiness_text = _read_required_text(READINESS_CONTRACT_SERVICE, errors)
    bootstrap_text = _read_required_text(BOOTSTRAP_CONTRACT_SERVICE, errors)
    contract_text = f"{workbench_text}\n{readiness_text}\n{bootstrap_text}"
    for term in (
        '"single_aps_doc_qualitative_execution_admitted": True',
        '"single_aps_doc_qualitative_execution": True',
        '"broad_qualitative_execution": False',
        '"hybrid_execution": False',
        '"rag_vector_retrieval": False',
    ):
        if term not in contract_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} or {_rel(READINESS_CONTRACT_SERVICE)} or {_rel(BOOTSTRAP_CONTRACT_SERVICE)} missing qualitative boundary term: {term}")

    required_doc_terms = {
        QUAL_APS_FREEZE: [
            "exact branch-local `single_aps_doc_qualitative_pass` lane",
            "all other qualitative/hybrid/cohort paths still fail closed",
        ],
        LOCAL_BOUNDARY: [
            "single APS-document qualitative pass",
            "broad qualitative execution outside the admitted single APS-document qualitative pass",
            "broad qualitative/hybrid/RAG execution",
        ],
        SYNTHESIS_BOUNDARY: [
            "single_aps_doc_qualitative_execution",
            "broad_qualitative_execution",
            "broad qualitative or hybrid execution outside the admitted single APS-document qualitative pass",
            "test_single_aps_doc_qualitative_owner_error_maps_without_side_effects",
            "analysis_execution_start_not_admitted",
            "PR #558",
        ],
        GOAL_AUDIT: [
            "The active goal is not complete.",
            "Only `single_aps_doc_qualitative_pass` is admitted",
            "broad qualitative execution beyond the single APS-document qualitative pass",
            "test_single_aps_doc_qualitative_owner_error_maps_without_side_effects",
            "qualitative owner-service error-boundary proof merged after PR #558",
            "5831ff2f",
        ],
        CLOSEOUT_DOC: [
            "PR #558 qualitative owner-service error-boundary proof",
            "test_single_aps_doc_qualitative_owner_error_maps_without_side_effects",
            "qualitative owner-service errors are proof-hardened",
            "Merged main head after PR #558: 5831ff2f.",
        ],
        QUAL_APS_ENTRY_FREEZE: [
            "selected the single APS content-document qualitative lane",
            "No other qualitative, hybrid, RAG, vector, cohort, comparative, cross-document, connector, provider, package, or full-mockup behavior is admitted.",
        ],
        QUAL_HYBRID_RAG_FREEZE: [
            "selected_qualitative_hybrid_rag_mode: `single_aps_doc_qualitative_pass_only`",
            "layer3.qualitative_hybrid_rag_boundary_contract.v1",
            "broad_qualitative_execution_enabled: `False`",
            "hybrid_execution_enabled: `False`",
            "rag_vector_retrieval_enabled: `False`",
            "hidden_llm_planning_enabled: `False`",
            "No broad qualitative execution, qualitative cohort execution, comparative execution, cross-document synthesis, hybrid execution, RAG/vector retrieval, hidden LLM planning, qualitative package/handoff/export, source widening, connector/destination dispatch, or package mutation/reconstruction is admitted.",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing qualitative boundary term: {term}")


def _check_qualitative_aps_package_review_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        QUAL_APS_PACKAGE_REVIEW_FREEZE: (
            "Status: current-main runtime boundary for `qual_aps_package_review_preview_only`",
            "selected mode: `qual_aps_package_review_preview_only`",
            "layer3.qual_aps_package_review_preview.v1",
            "qual_aps_package_construction_commit_entry",
            "qual_aps_package_review_submit_entry",
            "backend/tests/test_layer3_bounded_e2e.py::test_layer3_standalone_aps_content_document_qualitative_e2e_reaches_read_only_package_preview",
            "This mode adds only read-only package-review preview/readiness",
            "The runtime may not write durable package or downstream state.",
            "existing quantitative single-item and associated-cohort package preview behavior remains unchanged",
            "Browser proof is not required for a backend/API-only preview implementation.",
        ),
        QUAL_APS_PACKAGE_REVIEW_CONTRACT: (
            "Status: current runtime contract paired with `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md`.",
            "live `qual_aps_package_review_preview_only` implementation",
            "Live route target:",
            "`POST /api/v1/layer3/package/review/preview`",
            "Route reuse is admitted because the existing request/response envelope now distinguishes",
            "`analysis_run_id`, but it must be absent or null for qualitative APS execution",
            "The server must derive source, document, unit, set, chunk, output, and package-compatibility authority",
            "Any missing, stale, malformed, mismatched, non-approved, or cross-session authority must fail closed before row or file mutation.",
            "`schema_id`, preferably `layer3.qual_aps_package_review_preview.v1`",
            "package_commit_enabled",
            "external_export_download_enabled",
            "provider_public_url_enabled",
            "Forbidden state effects:",
            "create or mutate `L3OutputPackage`",
            "package-review submit is admitted only by the separate docs `143`/`144` boundary",
            "Those names are preview descriptors until the separate package-construction boundary creates qualitative APS package rows and payloads.",
            "headed and headless Chrome proof if UI changes",
        ),
        PHASE1A_README: (
            "138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md",
            "139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md",
            "live read-only `qual_aps_package_review_preview_only` boundary",
            "live `qual_aps_package_construction_commit_entry` boundary",
            "live bounded `qual_aps_package_review_submit_entry` boundary",
        ),
        DEFERRED_GATES: (
            "Docs `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md` and `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`",
            "live read-only `qual_aps_package_review_preview_only` runtime boundary",
            "live bounded `qual_aps_package_construction_commit_entry` runtime boundary",
            "live bounded `qual_aps_package_review_submit_entry` runtime boundary",
        ),
        BOARD: (
            "Qualitative APS package-review preview runtime",
            "current-main bounded runtime/API proof",
            "qual_aps_package_review_preview_only",
            "layer3.qual_aps_package_review_preview.v1",
            "qual_aps_package_construction_commit_entry",
            "qual_aps_package_review_submit_entry",
        ),
        MANIFEST: (
            "latest_qual_aps_package_review_preview_branch",
            "latest_qual_aps_package_review_preview_pr",
            "qual_aps_package_review_preview",
            "qual_aps_package_review_preview_only",
            "layer3.qual_aps_package_review_preview.v1",
            "qual_aps_package_construction_commit_entry",
            "qual_aps_package_review_submit_entry",
        ),
        PROOF_MANIFEST: (
            "latest_qual_aps_package_review_preview_branch",
            "latest_qual_aps_package_review_preview_pr",
            "latest_qual_aps_package_review_preview_live_behavior_change",
            "latest_qual_aps_package_review_preview_summary",
            "qual_aps_package_review_preview_proof",
            "qual_aps_package_review_preview_only",
            "layer3.qual_aps_package_review_preview.v1",
            "qual_aps_package_construction_commit_entry",
            "qual_aps_package_review_submit_entry",
            "no rendered controls or theme behavior change",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing qualitative APS package-review freeze term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "QUAL_APS_PACKAGE_REVIEW_PREVIEW_SCHEMA_ID = \"layer3.qual_aps_package_review_preview.v1\"",
        "QUAL_APS_PREVIEW_DOWNSTREAM_UNAVAILABLE = (",
        "def _require_qualitative_aps_package_review_authority(",
        "def _qualitative_aps_package_review_candidate_projection(",
        "def _raise_if_qualitative_aps_downstream_not_admitted(",
        "status_body.get(\"engine_family\") != ENGINE_FAMILY_QUAL_APS_DOCUMENT",
        "QUAL_APS_PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID = \"layer3.qual_aps_package_construction_commit.v1\"",
        "QUAL_APS_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing qualitative APS package-review runtime term: {term}")

    qual_test_text = _read_required_text(QUAL_APS_TEST, errors)
    for term in (
        "test_single_aps_doc_qualitative_package_preview_construction_and_submit_guard",
        "layer3.qual_aps_package_construction_commit.v1",
        "layer3.qual_aps_package_review_submit.v1",
        "140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE",
    ):
        if term not in qual_test_text:
            errors.append(f"{_rel(QUAL_APS_TEST)} missing qualitative APS submit guard proof term: {term}")

    e2e_test_text = _read_required_text(LAYER3_BOUNDED_E2E_TEST, errors)
    for term in (
        "test_layer3_standalone_aps_content_document_qualitative_e2e_reaches_read_only_package_preview",
        "ENGINE_FAMILY_QUAL_APS_DOCUMENT",
        "layer3.qual_aps_package_review_preview.v1",
        "layer3.qual_aps_package_construction_commit.v1",
        "layer3.qual_aps_package_review_submit.v1",
        "allowed_output_packages=3",
        "allowed_reconciliations=1",
    ):
        if term not in e2e_test_text:
            errors.append(f"{_rel(LAYER3_BOUNDED_E2E_TEST)} missing qualitative APS package-review proof term: {term}")


def _check_qualitative_aps_package_construction_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE: (
            "Status: current-main runtime boundary for `qual_aps_package_construction_commit_entry`.",
            "selected future route: `POST /api/v1/layer3/package/review/commit`",
            "selected future response schema: `layer3.qual_aps_package_construction_commit.v1`",
            "package kinds: `canonical_internal`, `user_facing`, `review_facing`",
            "live behavior: `backend/app/services/layer3_workbench.py` admits qualitative APS package construction",
            "exactly one `L3ReconciliationRecord`",
            "exactly three `L3OutputPackage` rows",
            "package payload files under the existing server-owned artifact/storage root",
            "qual_aps_package_review_submit_entry",
            "Browser proof is not required for a backend/API-only package construction implementation.",
        ),
        QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT: (
            "Status: current runtime contract paired with `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md`.",
            "Current main admits qualitative APS package construction through `layer3.qual_aps_package_construction_commit.v1`",
            "`POST /api/v1/layer3/package/review/commit`",
            "`layer3.qual_aps_package_construction_commit.v1`",
            "`expected_package_kinds` must equal:",
            "create exactly one `L3ReconciliationRecord`",
            "create exactly three `L3OutputPackage` rows",
            "duplicate `client_request_id` with the same construction basis",
            "package-review submit is admitted only by the separate docs `143`/`144` boundary",
            "headed and headless Chrome proof only if rendered UI changes",
        ),
        PHASE1A_README: (
            "140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md",
            "141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md",
            "qual_aps_package_construction_commit_entry",
            "canonical_internal",
            "user_facing",
            "review_facing",
        ),
        DEFERRED_GATES: (
            "140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md",
            "141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md",
            "qual_aps_package_construction_commit_entry",
            "qual_aps_package_review_submit_entry",
        ),
        BOARD: (
            "Qualitative APS package-construction runtime",
            "current-main bounded runtime/API proof",
            "qual_aps_package_construction_commit_entry",
            "exactly one `L3ReconciliationRecord`",
            "exactly three `L3OutputPackage` rows",
            "exactly three server-owned payload files",
            "rendered controls/theme behavior",
        ),
        MANIFEST: (
            "latest_qual_aps_package_construction_runtime_branch",
            "latest_qual_aps_package_construction_runtime_pr",
            "qual_aps_package_construction_runtime",
            "qual_aps_package_construction_commit_entry",
            "exactly one L3ReconciliationRecord",
            "exactly three L3OutputPackage rows",
        ),
        PROOF_MANIFEST: (
            "qual_aps_package_construction_commit_proof",
            "selected_mode",
            "qual_aps_package_construction_commit_entry",
            "exactly one L3ReconciliationRecord",
            "exactly three L3OutputPackage rows",
            "exactly three server-owned package payload files",
            "no rendered controls or theme behavior change",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing qualitative APS package-construction freeze term: {term}")

    package_entry_text = _read_required_text(PACKAGE_ENTRY_SERVICE, errors)
    for term in (
        "SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE = \"140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE\"",
        "authority_schema_id: str = \"layer3.workbench_package_construction_authority.v1\"",
        "authority_basis_extra: dict[str, Any] | None = None",
        "package_payload_extras_by_kind: dict[str, dict[str, Any]] | None = None",
        "\"construction_basis_hash\"",
    ):
        if term not in package_entry_text:
            errors.append(f"{_rel(PACKAGE_ENTRY_SERVICE)} missing qualitative APS package-construction helper term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "QUAL_APS_PACKAGE_CONSTRUCTION_COMMIT_SCHEMA_ID = \"layer3.qual_aps_package_construction_commit.v1\"",
        "QUAL_APS_PACKAGE_CONSTRUCTION_DOWNSTREAM_UNAVAILABLE = (",
        "def _qualitative_aps_package_review_preview_hash(",
        "def _qualitative_aps_package_payload_extras(",
        "SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE",
        "authority_schema_id = \"layer3.qual_aps_package_construction_authority.v1\"",
        "package_payload_extras_by_kind = _qualitative_aps_package_payload_extras(",
        "QUAL_APS_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing qualitative APS package-construction runtime term: {term}")

    e2e_test_text = _read_required_text(LAYER3_BOUNDED_E2E_TEST, errors)
    for term in (
        "def qualitative_package_commit(",
        "def qualitative_package_submit(",
        "layer3.qual_aps_package_construction_commit.v1",
        "140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE",
        "allowed_output_packages=3",
        "allowed_reconciliations=1",
        "layer3.qual_aps_package_review_submit.v1",
    ):
        if term not in e2e_test_text:
            errors.append(f"{_rel(LAYER3_BOUNDED_E2E_TEST)} missing qualitative APS package-construction proof term: {term}")


def _check_qualitative_aps_package_submit_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        POST_709_ROADMAP_FREEZE: (
            "Layer 3 Qualitative APS Post-Submit Roadmap Freeze",
            "qualitative APS handoff/export prepare over the approved package-review submit state",
            "qualitative APS package-review submit over the constructed package set",
            "governing handoff/export prepare docs: `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md`",
        ),
        QUAL_APS_PACKAGE_SUBMIT_FREEZE: (
            "Status: current-main runtime boundary for `qual_aps_package_review_submit_entry`.",
            "selected live mode: `qual_aps_package_review_submit_entry`",
            "selected live response schema: `layer3.qual_aps_package_review_submit.v1`",
            "former blocker removed by the live runtime: `qualitative_aps_package_review_submit_not_admitted`",
            "Allowed Writes",
            "one qualitative APS package-review decision object in `L3ReconciliationRecord.summary_json`",
            "The implementation must not create new rows or files under this freeze.",
            "Browser proof is not required for a backend/API-only package-review submit implementation.",
        ),
        QUAL_APS_PACKAGE_SUBMIT_CONTRACT: (
            "Status: current runtime API and state contract paired with `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md`.",
            "Selected route:",
            "`POST /api/v1/layer3/package/review/submit`",
            "Selected response schema:",
            "`layer3.qual_aps_package_review_submit.v1`",
            "`construction_basis_hash`",
            "`payload_refs`",
            "`operator_decision`",
            "Allowed state effects on successful submit:",
            "Current main admits qualitative APS package-review submit through `POST /api/v1/layer3/package/review/submit`",
        ),
        PHASE1A_README: (
            "143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md",
            "144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md",
            "qual_aps_package_review_submit_entry",
            "They select reuse of the package-review submit route family",
        ),
        DEFERRED_GATES: (
            "143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md",
            "144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md",
            "live bounded `qual_aps_package_review_submit_entry` runtime boundary",
            "creates no rows or files",
        ),
        BOARD: (
            "Qualitative APS package-review submit runtime",
            "current-main bounded runtime/API proof",
            "qual_aps_package_review_submit_entry",
            "POST /api/v1/layer3/package/review/submit",
            "creates no rows or files",
        ),
        MANIFEST: (
            "latest_qual_aps_package_review_submit_runtime_branch",
            "latest_qual_aps_package_review_submit_runtime_live_behavior_change",
            "qual_aps_package_review_submit_runtime",
            "qual_aps_package_review_submit_entry",
            "creates no rows or files",
        ),
        PROOF_MANIFEST: (
            "latest_qual_aps_package_review_submit_runtime_branch",
            "latest_qual_aps_package_review_submit_runtime_live_behavior_change",
            "latest_qual_aps_package_review_submit_runtime_summary",
            "qual_aps_package_review_submit_runtime_proof",
            "qual_aps_package_review_submit_entry",
            "creates no rows or files",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing qualitative APS package-submit freeze term: {term}")

    layer3_js_text = _read_required_text(LAYER3_JS, errors)
    for term in (
        "QUAL_APS_PACKAGE_CONSTRUCTION_SOURCE_GATE = '140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE'",
        "function isQualitativeApsPackageSubmitState(",
        "payload_refs: packagePayloadRefs()",
        "payload.construction_basis_hash = constructionBasisHash",
        "authority.analysisRunId && !qualitativeAps",
    ):
        if term not in layer3_js_text:
            errors.append(f"{_rel(LAYER3_JS)} missing qualitative APS package-submit UI authority term: {term}")

    workbench_e2e_text = _read_required_text(LAYER3_WORKBENCH_E2E, errors)
    for term in (
        "Layer 3 workbench submits qualitative APS package review without analysis-run authority",
        "expect(packageSubmitPayload).not.toHaveProperty('analysis_run_id')",
        "expect(packageSubmitPayload.payload_refs).toEqual(fixture.payloadRefs)",
        "expect(packageSubmitPayload.construction_basis_hash).toBe(fixture.constructionBasisHash)",
    ):
        if term not in workbench_e2e_text:
            errors.append(f"{_rel(LAYER3_WORKBENCH_E2E)} missing qualitative APS package-submit UI proof term: {term}")


def _check_qualitative_aps_handoff_export_prepare_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE: (
            "Status: current-main runtime boundary for `qual_aps_handoff_export_prepare_entry`.",
            "selected live mode: `qual_aps_handoff_export_prepare_entry`",
            "selected live response schema: `layer3.qual_aps_handoff_export_prepare.v1`",
            "`POST /api/v1/layer3/handoff/export/prepare`",
            "former blocker `qualitative_aps_handoff_export_prepare_not_admitted` has been removed",
            "The implementation explicitly validates qualitative APS authority",
            "The implementation must not create new rows or files under this freeze.",
            "Browser proof is not required for a backend/API-only handoff/export prepare implementation.",
        ),
        QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT: (
            "Status: current-main API and state contract paired with `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md`.",
            "Default route:",
            "`POST /api/v1/layer3/handoff/export/prepare`",
            "Selected response schema:",
            "`layer3.qual_aps_handoff_export_prepare.v1`",
            "`package_review_submit_schema_id`",
            "`layer3.qual_aps_package_review_submit.v1`",
            "Allowed state effects for a successful prepare:",
            "Qualitative APS attempts that lack the exact persisted package-preview",
        ),
        POST_709_ROADMAP_FREEZE: (
            "Status: current-main planning/control reference after qualitative APS external export/download runtime and rendered UI runtime.",
            "governing handoff/export prepare docs: `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md`",
            "qualitative APS handoff/export prepare over the approved package-review submit state",
            "governing APS handoff dispatch runtime docs: `147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md`",
        ),
        PHASE1A_README: (
            "145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md",
            "146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md",
            "qual_aps_handoff_export_prepare_entry",
            "They reuse the handoff/export prepare route family",
        ),
        DEFERRED_GATES: (
            "145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md",
            "146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md",
            "live bounded `qual_aps_handoff_export_prepare_entry` runtime boundary",
            "current-main code records exactly one qualitative APS prepare-only handoff/export decision/envelope object",
        ),
        BOARD: (
            "Qualitative APS handoff/export prepare runtime",
            "current-main bounded backend/API runtime",
            "qual_aps_handoff_export_prepare_entry",
            "POST /api/v1/layer3/handoff/export/prepare",
            "creates no rows or files",
        ),
        MANIFEST: (
            "latest_qual_aps_handoff_export_prepare_freeze_branch",
            "latest_qual_aps_handoff_export_prepare_freeze_live_behavior_change",
            "qual_aps_handoff_export_prepare_freeze",
            "qual_aps_handoff_export_prepare_entry",
            "creates no rows or files",
        ),
        PROOF_MANIFEST: (
            "latest_qual_aps_handoff_export_prepare_freeze_branch",
            "latest_qual_aps_handoff_export_prepare_freeze_live_behavior_change",
            "latest_qual_aps_handoff_export_prepare_freeze_summary",
            "qual_aps_handoff_export_prepare_freeze_proof",
            "qual_aps_handoff_export_prepare_entry",
            "layer3.qual_aps_handoff_export_prepare.v1",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing qualitative APS handoff/export prepare freeze term: {term}"
                )
    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "qualitative_aps_prepare = (",
        "status_body.get(\"engine_family\") == ENGINE_FAMILY_QUAL_APS_DOCUMENT",
        "status_body.get(\"pass_scope\") == PASS_SCOPE_SINGLE_APS_DOC_QUALITATIVE",
        "output_metadata_summary.get(\"source_gate\") == QUAL_APS_SOURCE_GATE",
        "QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID",
        "SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE",
        "\"qualitative_aps_handoff_export_prepare_construction_basis_mismatch\"",
        "\"qualitative_aps_aps_handoff_dispatch_not_admitted\"",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing qualitative APS handoff/export prepare runtime term: {term}")
    response_text = _read_required_text(HANDOFF_EXPORT_RESPONSE_SERVICE, errors)
    for term in (
        "QUAL_APS_HANDOFF_EXPORT_PREPARE_SCHEMA_ID = \"layer3.qual_aps_handoff_export_prepare.v1\"",
        "QUAL_APS_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID",
        "\"provider_public_url_enabled\": False",
    ):
        if term not in response_text:
            errors.append(f"{_rel(HANDOFF_EXPORT_RESPONSE_SERVICE)} missing qualitative APS handoff/export prepare response term: {term}")
    bounded_e2e_text = _read_required_text(LAYER3_BOUNDED_E2E_TEST, errors)
    for term in (
        "def qualitative_handoff_prepare(",
        "aps-qual-e2e-handoff-prepare",
        "\"layer3.qual_aps_handoff_export_prepare.v1\"",
        "\"provider_public_url_enabled\"",
    ):
        if term not in bounded_e2e_text:
            errors.append(f"{_rel(LAYER3_BOUNDED_E2E_TEST)} missing qualitative APS handoff/export prepare runtime proof term: {term}")


def _check_qualitative_aps_aps_handoff_dispatch_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE: (
            "Status: current-main runtime boundary for `qual_aps_aps_handoff_dispatch_entry`.",
            "selected live route: `POST /api/v1/layer3/handoff/aps/dispatch`",
            "selected live response schema: `layer3.qual_aps_aps_handoff_dispatch.v1`",
            "selected live mode: `qual_aps_aps_handoff_dispatch_entry`",
            "current downstream readiness after dispatch: `external_export_download_ready`",
            "exactly one APS evidence-bundle handoff package row",
            "one server-owned APS bundle artifact",
            "`aps_handoff_dispatched`",
            "`handoff_export_prepared`",
            "Browser proof is required when backend readiness or session-summary changes make existing rendered `/review/layer3` controls newly available",
        ),
        QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT: (
            "Status: current-main API and state contract paired with `147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md`.",
            "Current main admits qualitative APS APS handoff dispatch",
            "`POST /api/v1/layer3/handoff/aps/dispatch`",
            "`layer3.qual_aps_aps_handoff_dispatch.v1`",
            "`dispatch_aps_handoff`",
            "`handoff_export_prepared` for qualitative APS",
            "docs `149` and `150`",
            "Allowed state effects for successful dispatch:",
            "create exactly one APS evidence-bundle handoff package row",
            "owner-service APS handoff compatibility fails",
        ),
        POST_709_ROADMAP_FREEZE: (
            "governing APS handoff dispatch runtime docs: `147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md`",
            "qualitative APS APS handoff dispatch over the prepared qualitative envelope",
            "governing qualitative APS external export/download freeze docs: `149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`",
            "qual_aps_external_export_download_prepare_deliver",
        ),
        PHASE1A_README: (
            "147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md",
            "148_QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT.md",
            "qual_aps_aps_handoff_dispatch_entry",
            "qual_aps_external_export_download_prepare_deliver",
        ),
        DEFERRED_GATES: (
            "147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md",
            "148_QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT.md",
            "live qualitative APS APS handoff dispatch boundary",
            "docs `149` and `150`",
        ),
        BOARD: (
            "Qualitative APS APS handoff dispatch runtime",
            "current-main bounded backend/API runtime",
            "qual_aps_aps_handoff_dispatch_entry",
            "POST /api/v1/layer3/handoff/aps/dispatch",
            "qual_aps_external_export_download_prepare_deliver",
        ),
        MANIFEST: (
            "latest_qual_aps_aps_handoff_dispatch_freeze_branch",
            "latest_qual_aps_aps_handoff_dispatch_freeze_live_behavior_change",
            "qual_aps_aps_handoff_dispatch_freeze",
            "external_export_download_ready",
            "exactly one APS evidence-bundle handoff package row",
        ),
        PROOF_MANIFEST: (
            "latest_qual_aps_aps_handoff_dispatch_freeze_branch",
            "latest_qual_aps_aps_handoff_dispatch_freeze_live_behavior_change",
            "latest_qual_aps_aps_handoff_dispatch_freeze_summary",
            "qual_aps_aps_handoff_dispatch_freeze_proof",
            "layer3.qual_aps_aps_handoff_dispatch.v1",
            "external_export_download_ready",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing qualitative APS APS handoff dispatch freeze term: {term}"
                )

    for path in (QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE, QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT):
        text = _read_required_text(path, errors)
        for stale_term in ("qual_aps_aps_handoff_dispatched", "qual_aps_handoff_export_prepared"):
            if stale_term in text:
                errors.append(f"{_rel(path)} contains stale qualitative APS dispatch state term: {stale_term}")

    manifest = _load_json(MANIFEST, errors)
    current_status = manifest.get("current_status") if isinstance(manifest, dict) else None
    if not isinstance(current_status, dict):
        errors.append(f"{_rel(MANIFEST)} current_status missing for qualitative APS dispatch metadata")
    else:
        for key in (
            "latest_qual_aps_aps_handoff_dispatch_freeze_branch",
            "latest_qual_aps_aps_handoff_dispatch_freeze_live_behavior_change",
            "qual_aps_aps_handoff_dispatch_freeze",
        ):
            if key not in current_status:
                errors.append(f"{_rel(MANIFEST)} current_status missing qualitative APS dispatch key: {key}")
    top_level_scope = manifest.get("scope") if isinstance(manifest, dict) else None
    if isinstance(top_level_scope, dict):
        for key in top_level_scope:
            if "qual_aps_aps_handoff_dispatch" in key or "qual_aps_external_export_download" in key:
                errors.append(f"{_rel(MANIFEST)} has misplaced qualitative APS current-status key under top-level scope: {key}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "QUAL_APS_APS_HANDOFF_DISPATCH_SCHEMA_ID = \"layer3.qual_aps_aps_handoff_dispatch.v1\"",
        "def _qualitative_aps_aps_dispatch_source_admitted(",
        "def _qualitative_aps_aps_dispatch_prepare_state_admitted(",
        "\"qualitative_aps_aps_handoff_dispatch_not_admitted\"",
        "def _aps_handoff_dispatch_summary(",
        "def aps_handoff_dispatch(",
        "materialize_aps_handoff(db, session_id=session_id)",
        "APS_HANDOFF_DISPATCH_DOWNSTREAM_UNAVAILABLE",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing APS handoff dispatch reference term: {term}")

    handoff_contract_text = _read_required_text(HANDOFF_CONTRACT_SERVICE, errors)
    for term in (
        "APS_HANDOFF_DISPATCH_ALLOWED_FIELDS",
        "APS_HANDOFF_DISPATCH_FORBIDDEN_FIELDS",
        "def aps_handoff_dispatch_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        "\"connector_dispatch\"",
        "\"download_url\"",
    ):
        if term not in handoff_contract_text:
            errors.append(f"{_rel(HANDOFF_CONTRACT_SERVICE)} missing APS handoff dispatch contract term: {term}")

    aps_handoff_text = _read_required_text(APS_HANDOFF_SERVICE, errors)
    for term in (
        "PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF = \"aps_evidence_bundle_handoff\"",
        "APS_HANDOFF_SCHEMA_ID = \"layer3.aps_evidence_bundle_handoff.v1\"",
        "def check_aps_handoff_compatibility(",
        "def materialize_aps_handoff(",
        "SOURCE_WORKBENCH_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE",
    ):
        if term not in aps_handoff_text:
            errors.append(f"{_rel(APS_HANDOFF_SERVICE)} missing APS handoff owner-service term: {term}")

    bounded_e2e_text = _read_required_text(LAYER3_BOUNDED_E2E_TEST, errors)
    for term in (
        "def qualitative_aps_dispatch(",
        "aps-qual-e2e-aps-dispatch",
        "\"layer3.qual_aps_aps_handoff_dispatch.v1\"",
        "\"layer3.qual_aps_external_export_download_prepare.v1\"",
        "allowed_output_packages=4",
    ):
        if term not in bounded_e2e_text:
            errors.append(f"{_rel(LAYER3_BOUNDED_E2E_TEST)} missing qualitative APS APS handoff dispatch proof term: {term}")


def _check_qualitative_aps_external_export_download_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE: (
            "Status: current-main runtime boundary for `qual_aps_external_export_download_prepare_deliver`.",
            "selected live prepare route: `POST /api/v1/layer3/handoff/export/download/prepare`",
            "selected live prepare response schema: `layer3.qual_aps_external_export_download_prepare.v1`",
            "selected live deliver route: `POST /api/v1/layer3/handoff/export/download/deliver`",
            "selected live delivery schema/header: `layer3.qual_aps_external_export_download_delivery.v1`",
            "current live readiness state: `external_export_download_ready`",
            "same-origin artifact streaming",
            "successful qualitative APS prepare after `aps_handoff_dispatched`",
            "Browser proof is required when backend readiness, delivery, or session-summary changes make existing rendered `/review/layer3` controls newly available",
        ),
        QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT: (
            "Status: current-main API and state contract paired with `149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`.",
            "Current main admits the qualitative APS path only after exact qualitative APS APS handoff dispatch authority",
            "`POST /api/v1/layer3/handoff/export/download/prepare`",
            "`POST /api/v1/layer3/handoff/export/download/deliver`",
            "`layer3.qual_aps_external_export_download_prepare.v1`",
            "`layer3.qual_aps_external_export_download_delivery.v1`",
            "excluding prepare-only intent fields (`operator_decision` and `decision_notes`)",
            "Delivery overrides prepare intent.",
            "must not inherit `prepare_external_export_download`",
            "except for the single admitted qualitative APS external export/download readiness object",
            "Allowed state effects for successful prepare:",
            "Allowed state effects for successful delivery:",
        ),
        POST_709_ROADMAP_FREEZE: (
            "governing qualitative APS external export/download freeze docs: `149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`",
            "qualitative APS external export/download prepare/deliver runtime, governed by docs `149` and `150`",
            "qualitative APS external export/download prepare/deliver over the dispatched APS bundle",
            "The live qualitative APS external export/download path is limited to `qual_aps_external_export_download_prepare_deliver`",
        ),
        PHASE1A_README: (
            "149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md",
            "150_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT.md",
            "qual_aps_external_export_download_prepare_deliver",
            "same-origin artifact streaming",
        ),
        DEFERRED_GATES: (
            "149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md",
            "150_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT.md",
            "live qualitative APS external export/download prepare/deliver boundary only",
            "qual_aps_external_export_download_prepare_deliver",
        ),
        BOARD: (
            "Qualitative APS external export/download runtime",
            "current-main bounded backend/API runtime",
            "qual_aps_external_export_download_prepare_deliver",
            "POST /api/v1/layer3/handoff/export/download/prepare",
            "same-origin APS bundle delivery",
        ),
        MANIFEST: (
            "latest_qual_aps_external_export_download_freeze_branch",
            "latest_qual_aps_external_export_download_freeze_live_behavior_change",
            "qual_aps_external_export_download_freeze",
            "layer3.qual_aps_external_export_download_delivery.v1",
            "zero DB/file writes",
        ),
        PROOF_MANIFEST: (
            "latest_qual_aps_external_export_download_freeze_branch",
            "latest_qual_aps_external_export_download_freeze_live_behavior_change",
            "latest_qual_aps_external_export_download_freeze_summary",
            "qual_aps_external_export_download_freeze_proof",
            "layer3.qual_aps_external_export_download_prepare.v1",
            "layer3.qual_aps_external_export_download_delivery.v1",
            "external_export_download_ready",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing qualitative APS external export/download freeze term: {term}"
                )

    manifest = _load_json(MANIFEST, errors)
    current_status = manifest.get("current_status") if isinstance(manifest, dict) else None
    if not isinstance(current_status, dict):
        errors.append(f"{_rel(MANIFEST)} current_status missing for qualitative APS external export/download metadata")
    else:
        for key in (
            "latest_qual_aps_external_export_download_freeze_branch",
            "latest_qual_aps_external_export_download_freeze_live_behavior_change",
            "qual_aps_external_export_download_freeze",
        ):
            if key not in current_status:
                errors.append(f"{_rel(MANIFEST)} current_status missing qualitative APS external export/download key: {key}")
    top_level_scope = manifest.get("scope") if isinstance(manifest, dict) else None
    if isinstance(top_level_scope, dict):
        for key in top_level_scope:
            if "qual_aps_aps_handoff_dispatch" in key or "qual_aps_external_export_download" in key:
                errors.append(f"{_rel(MANIFEST)} has misplaced qualitative APS current-status key under top-level scope: {key}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "def external_export_download_prepare(",
        "def external_export_download_deliver(",
        "qualitative_aps_external_export_download_analysis_run_not_admitted",
        "_qualitative_aps_external_export_submit_state_admitted(",
        "EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_OPERATOR_DECISION",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing external export/download reference term: {term}")

    response_text = _read_required_text(EXTERNAL_EXPORT_RESPONSE_SERVICE, errors)
    for term in (
        "def qualitative_aps_external_export_download_deferred(",
        "def qualitative_aps_external_export_download_admitted(",
        "def aps_bundle_identity_for_external_export_download(",
        "def external_export_download_prepare_summary(",
        "\"qualitative_aps_external_export_download_not_admitted\"",
        "QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID",
        "QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID",
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = \"layer3.external_export_download_prepare.v1\"",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = \"layer3.external_export_download_delivery.v1\"",
    ):
        if term not in response_text:
            errors.append(f"{_rel(EXTERNAL_EXPORT_RESPONSE_SERVICE)} missing external export/download response term: {term}")

    contract_text = _read_required_text(EXTERNAL_EXPORT_CONTRACT_SERVICE, errors)
    for term in (
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS",
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ALLOWED_FIELDS",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS",
        "def external_export_download_delivery_readiness_mismatches(",
    ):
        if term not in contract_text:
            errors.append(f"{_rel(EXTERNAL_EXPORT_CONTRACT_SERVICE)} missing external export/download contract term: {term}")


def _check_qualitative_aps_rendered_ui_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        QUAL_APS_RENDERED_UI_FREEZE: (
            "Status: live bounded rendered `/review/layer3` qualitative APS package/downstream UI runtime",
            "qual_aps_rendered_downstream_existing_controls_only",
            "Current main now admits rendered qualitative package/downstream controls only through existing `/review/layer3` controls",
            "Qualitative APS same-origin delivery remains disabled and gated when the server returns `delivery_ui: null` or omits `delivery_ui`.",
            "Required Theme Posture",
            "headless Chromium Playwright",
            "headed Chromium Playwright",
            "does not introduce a raw mixed manifest picker",
            "no frontend-only durable authority",
        ),
        QUAL_APS_RENDERED_UI_CONTRACT: (
            "Status: live UI/state contract paired with `151_QUAL_APS_RENDERED_UI_FREEZE.md`.",
            "qual_aps_rendered_downstream_existing_controls_only",
            "Server state is the only durable authority",
            "Delivery UI Gate",
            "The UI must not enable delivery from `delivery_ui: null`.",
            "Response-Derived Readiness Contract",
            "external_export_download_delivery_ui_unavailable",
            "external_export_download_signed_reference_ui_blocked",
            "headed and headless Chromium runs for the same qualitative APS rendered path",
        ),
        POST_709_ROADMAP_FREEZE: (
            "governing rendered qualitative APS UI runtime docs: `151_QUAL_APS_RENDERED_UI_FREEZE.md`",
            "rendered `/review/layer3` qualitative APS downstream UI runtime, governed by docs `151` and `152`",
            "qual_aps_rendered_downstream_existing_controls_only",
            "next work should move to source breadth",
        ),
        PHASE1A_README: (
            "151_QUAL_APS_RENDERED_UI_FREEZE.md",
            "152_QUAL_APS_RENDERED_UI_CONTRACT.md",
            "qual_aps_rendered_downstream_existing_controls_only",
            "headed/headless Chromium theme proof",
            "qualitative delivery stays disabled from `delivery_ui: null`",
        ),
        DEFERRED_GATES: (
            "151_QUAL_APS_RENDERED_UI_FREEZE.md",
            "152_QUAL_APS_RENDERED_UI_CONTRACT.md",
            "qual_aps_rendered_downstream_existing_controls_only",
            "rendered qualitative delivery without server `delivery_ui`",
        ),
        BOARD: (
            "Qualitative APS rendered downstream UI runtime",
            "current-main bounded rendered UI proof",
            "qual_aps_rendered_downstream_existing_controls_only",
            "headless and headed Chromium",
            "qualitative delivery disabled when `delivery_ui` is null or absent",
        ),
        MANIFEST: (
            "latest_qual_aps_rendered_ui_freeze_branch",
            "latest_qual_aps_rendered_ui_freeze_live_behavior_change",
            "qual_aps_rendered_ui_freeze",
            "no frontend-only durable authority",
        ),
        PROOF_MANIFEST: (
            "latest_qual_aps_rendered_ui_freeze_branch",
            "latest_qual_aps_rendered_ui_freeze_live_behavior_change",
            "latest_qual_aps_rendered_ui_freeze_summary",
            "qual_aps_rendered_ui_freeze_proof",
            "required_future_browser_proof",
        ),
    }
    stale_doc_terms = {
        QUAL_APS_RENDERED_UI_FREEZE: (
            "Status: planning-only implementation-entry freeze",
            "Current main still does not admit rendered qualitative package/downstream controls",
            "Selected Future Boundary",
        ),
        QUAL_APS_RENDERED_UI_CONTRACT: (
            "Status: planning-only UI/state contract",
            "This contract specifies the future rendered `/review/layer3` behavior",
            "The first future implementation should start",
        ),
        BOARD: (
            "Qualitative APS rendered downstream UI freeze | planning/control docs",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing qualitative APS rendered UI freeze term: {term}"
                )
        for term in stale_doc_terms.get(path, ()):
            if term in text:
                errors.append(
                    f"{_rel(path)} still contains stale qualitative APS rendered UI planning-only term: {term}"
                )

    required_source_terms = {
        LAYER3_JS: (
            "function packageReviewPreviewHash()",
            "function packageConstructionBasisHash()",
            "function apsHandoffDispatchState()",
            "const qualitativeAps = handoff?.schema_id === 'layer3.qual_aps_handoff_export_prepare.v1'",
            "state: 'aps_handoff_ready'",
            "function isQualitativeApsExternalExportDownloadState",
            "external_export_download_delivery_ui_unavailable",
            "external_export_download_signed_reference_ui_blocked",
            "deliveryUi.state === 'external_export_download_delivery_ui_ready'",
            "if (!isAssociatedCohortExternalExportDownloadState(external))",
            "payload.construction_basis_hash = constructionBasisHash",
            "apsHandoffDispatchState()?.available === true",
        ),
        LAYER3_PAGE_TEST: (
            "function packageReviewPreviewHash",
            "function packageConstructionBasisHash",
            "function isQualitativeApsExternalExportDownloadState",
            "external_export_download_delivery_ui_unavailable",
            "external_export_download_signed_reference_ui_blocked",
            "source_artifact_size_bytes ?? summary.source_artifact_size_bytes",
            "apsHandoffDispatchState()?.available === true",
        ),
        LAYER3_HELPERS_E2E: (
            "prepareQualitativeApsResultReviewSession",
            "approvedLayer3CandidateDecision",
            "aps_content_document_ids: [seed.content_id]",
            "attachSessionToWorkbench(page, sessionId, sourceClasses = ['dataset_version'])",
        ),
        LAYER3_HANDOFF_E2E: (
            "Layer 3 workbench drives qualitative APS package handoff to external readiness with delivery UI gated",
            "prepareQualitativeApsResultReviewSession",
            "external_export_download_delivery_ui_unavailable",
            "external_export_download_signed_reference_ui_blocked",
            "expect(external.delivery_ui).toBeNull()",
            "expectOnlyPayloadKeys",
            "expect(submitPayload).not.toHaveProperty('analysis_run_id')",
            "expect(externalPayload).not.toHaveProperty('public_url')",
        ),
    }
    for path, terms in required_source_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing qualitative APS rendered UI runtime term: {term}"
                )
    js_text = _read_required_text(LAYER3_JS, errors)
    for term in (
        "source_artifact_size_bytes ?? summary.source_artifact_size_bytes",
        "state: 'associated_cohort_external_export_download_delivery_ui_ready',",
    ):
        if term in js_text:
            errors.append(
                f"{_rel(LAYER3_JS)} still contains synthetic associated-cohort delivery UI term: {term}"
            )

    manifest = _load_json(MANIFEST, errors)
    current_status = manifest.get("current_status") if isinstance(manifest, dict) else None
    if isinstance(current_status, dict):
        for key in (
            "latest_qual_aps_rendered_ui_freeze_branch",
            "latest_qual_aps_rendered_ui_freeze_live_behavior_change",
            "qual_aps_rendered_ui_freeze",
        ):
            if key not in current_status:
                errors.append(f"{_rel(MANIFEST)} current_status missing rendered UI key: {key}")
        if current_status.get("latest_qual_aps_rendered_ui_freeze_branch") != "codex/l3-qual-aps-ui-runtime":
            errors.append(
                f"{_rel(MANIFEST)} current_status has stale rendered UI branch: "
                "latest_qual_aps_rendered_ui_freeze_branch"
            )
        if current_status.get("latest_qual_aps_rendered_ui_freeze_live_behavior_change") is not True:
            errors.append(
                f"{_rel(MANIFEST)} current_status must mark rendered UI runtime as a live behavior change"
            )


def _check_source_boundary_contract(errors: list[str]) -> None:
    supported = _load_literal_assignment(
        SOURCE_BOUNDARY_SERVICE, "SUPPORTED_SOURCE_CLASSES", errors
    )
    unsupported = _load_literal_assignment(
        SOURCE_BOUNDARY_SERVICE, "UNSUPPORTED_SOURCE_CLASSES", errors
    )
    deferred_capabilities = _load_literal_assignment(
        SOURCE_BOUNDARY_SERVICE, "SOURCE_EXPANSION_DEFERRED_CAPABILITIES", errors
    )
    forbidden_fields = _load_literal_assignment(
        SOURCE_BOUNDARY_SERVICE, "SOURCE_BOUNDARY_FORBIDDEN_RUNTIME_FIELDS", errors
    )

    expected_supported = ("dataset_version", "aps_content_document")
    expected_unsupported = (
        "rag_vector_index",
        "arbitrary_local_directory",
        "broad_file_upload",
        "web_connector",
        "unbounded_runtime_db",
    )
    expected_deferred = (
        "local_upload_or_directory_source_expansion",
        "broad_file_upload_source_expansion",
        "web_connector_source_expansion",
        "rag_vector_retrieval",
        "unbounded_runtime_db_source_expansion",
    )
    expected_forbidden_fields = (
        "source_upload",
        "local_upload",
        "local_directory",
        "rag_vector_index",
        "rag_plan",
        "vector_plan",
        "web_connector",
        "runtime_db_write",
        "source_expansion",
        "schema_widening",
    )
    if supported != expected_supported:
        errors.append(
            "source boundary supported classes drifted: "
            f"expected {expected_supported!r}, found {supported!r}"
        )
    if unsupported != expected_unsupported:
        errors.append(
            "source boundary unsupported classes drifted: "
            f"expected {expected_unsupported!r}, found {unsupported!r}"
        )
    if deferred_capabilities != expected_deferred:
        errors.append(
            "source expansion deferred capabilities drifted: "
            f"expected {expected_deferred!r}, found {deferred_capabilities!r}"
        )
    if forbidden_fields != expected_forbidden_fields:
        errors.append(
            "source boundary forbidden runtime fields drifted: "
            f"expected {expected_forbidden_fields!r}, found {forbidden_fields!r}"
        )

    service_text = _read_required_text(SOURCE_BOUNDARY_SERVICE, errors)
    for term in (
        "SOURCE_BOUNDARY_CONTRACT_SCHEMA_ID = \"layer3.source_boundary_contract.v1\"",
        "SOURCE_BOUNDARY_MODE = \"supported_source_classes_only\"",
        "def requested_source_classes(",
        "def unsupported_requested(",
        "def source_class_from_source_candidate_id(",
        "def source_class_from_material_candidate_id(",
        "def source_boundary_contract(",
        "\"source_upload_enabled\": False",
        "\"local_directory_enabled\": False",
        "\"broad_file_upload_enabled\": False",
        "\"web_connector_enabled\": False",
        "\"rag_vector_enabled\": False",
        "\"unbounded_runtime_db_enabled\": False",
        "\"requires_later_freeze\": True",
    ):
        if term not in service_text:
            errors.append(f"{_rel(SOURCE_BOUNDARY_SERVICE)} missing helper: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    required_imports = (
        "from app.services.layer3_source_boundary import",
        "requested_source_classes as _requested_source_classes",
        "unsupported_requested as _unsupported_requested",
        "source_class_from_source_candidate_id as _source_class_from_source_candidate_id",
        "source_class_from_material_candidate_id as _source_class_from_material_candidate_id",
    )
    for term in required_imports:
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing source-boundary import: {term}")
    for assignment in ("SUPPORTED_SOURCE_CLASSES", "UNSUPPORTED_SOURCE_CLASSES"):
        if re.search(rf"^{assignment}\s*=", workbench_text, re.MULTILINE):
            errors.append(
                f"{_rel(WORKBENCH_SERVICE)} must not redeclare {assignment}; "
                "source boundary owns it"
            )

    test_text = _read_required_text(SOURCE_BOUNDARY_TEST, errors)
    for term in expected_supported + expected_unsupported + expected_deferred + expected_forbidden_fields:
        if term not in test_text:
            errors.append(f"{_rel(SOURCE_BOUNDARY_TEST)} missing source class proof term: {term}")
    if "test_source_boundary_contract_keeps_deferred_source_expansion_fail_closed" not in test_text:
        errors.append(f"{_rel(SOURCE_BOUNDARY_TEST)} missing source boundary contract proof")

    required_doc_terms = {
        SOURCE_EXPANSION_FREEZE: [
            "Status: source expansion implementation-entry freeze for supported-source-only runtime",
            "selected_source_expansion_mode: `supported_source_classes_only`",
            "layer3.source_boundary_contract.v1",
            "source_upload_enabled: `False`",
            "local_directory_enabled: `False`",
            "web_connector_enabled: `False`",
            "rag_vector_enabled: `False`",
            "unbounded_runtime_db_enabled: `False`",
            "No source upload, local directory ingestion, broad file upload, web connector source, RAG/vector retrieval, or unbounded runtime DB source is admitted.",
        ],
        DEFERRED_GATES: [
            "123_SOURCE_EXPANSION_FREEZE.md",
            "supported_source_classes_only",
            "source upload, local directory, broad file upload, web connector, RAG/vector, and unbounded runtime DB source expansion remain blocked",
        ],
        SYNTHESIS_BOUNDARY: [
            "backend/app/services/layer3_source_boundary.py",
            "SUPPORTED_SOURCE_CLASSES",
            "UNSUPPORTED_SOURCE_CLASSES",
            "123_SOURCE_EXPANSION_FREEZE.md",
            "backend/tests/test_layer3_source_boundary.py",
        ],
        GOAL_AUDIT: [
            "current-main completion audit after PR #538 merged",
            "123_SOURCE_EXPANSION_FREEZE.md",
            "backend/app/services/layer3_source_boundary.py",
            "backend/tests/test_layer3_source_boundary.py",
            "does not widen source classes",
            "267 passed",
        ],
        CLOSEOUT_DOC: [
            "Status: bounded proof snapshot through PR #607 package-state helper proof hardening after PR #584 plan-flow request contract extraction",
            "123_SOURCE_EXPANSION_FREEZE.md",
            "post-merge documentation/proof synchronization only",
            "PR #538",
            "post-merge `main` workflow",
            "backend-layer3-api",
            "current-main proof after PR #538",
            "backend/app/services/layer3_source_boundary.py",
            "267 passed, 4 warnings",
            "Layer 3 progress state check: PASS",
            "generic connector/destination dispatch",
            "package mutation/reconstruction",
            "broad source/upload expansion",
            "broad qualitative execution outside `single_aps_doc_qualitative_pass`",
            "full mockup activation",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing source-boundary term: {term}")


def _check_raw_mixed_bridge_freeze(errors: list[str]) -> None:
    doc_text = _read_required_text(RAW_MIXED_BRIDGE_FREEZE, errors)
    for term in (
        "Status: implementation-entry freeze plus bounded runtime contract for `raw_mixed_corpus_bridge_seed_only`",
        "selected_raw_mixed_bridge_mode: `raw_mixed_corpus_bridge_seed_only`",
        "Runtime implementation scope is limited to `POST /api/v1/layer3/source/mixed-corpus/seed`",
        "owner service: `backend/app/services/layer3_raw_mixed_bridge.py`",
        "request DTO: `Layer3RawMixedCorpusSeedRequest`",
        "response DTO: `Layer3RawMixedCorpusSeedResponse`",
        "layer3.raw_mixed_corpus_seed_request.v1",
        "layer3.raw_mixed_corpus_seed_result.v1",
        "layer3.raw_mixed_corpus_seed_manifest.v1",
        "Source seeding remains separate from Layer 3 flow execution.",
        "writes no database rows",
        "server-owned storage-root manifest",
        "`dataset_version` and `aps_content_document`",
        "`local_upload`",
        "`local_directory`",
        "`web_connector`",
        "`rag_vector_index`",
        "`unbounded_runtime_db`",
        "no Layer 3 session, descriptor, material snapshot, typing, plan, pass, execution, result, package, handoff, APS dispatch, export/download, connector, provider URL, vector index, package mutation, mockup, or auth/security side effect occurs",
    ):
        if term not in doc_text:
            errors.append(f"{_rel(RAW_MIXED_BRIDGE_FREEZE)} missing raw mixed bridge freeze term: {term}")

    service_text = _read_required_text(RAW_MIXED_BRIDGE_SERVICE, errors)
    for term in (
        "RAW_MIXED_CORPUS_SEED_REQUEST_SCHEMA_ID = \"layer3.raw_mixed_corpus_seed_request.v1\"",
        "RAW_MIXED_CORPUS_SEED_RESPONSE_SCHEMA_ID = \"layer3.raw_mixed_corpus_seed_result.v1\"",
        "RAW_MIXED_CORPUS_SEED_MANIFEST_SCHEMA_ID = \"layer3.raw_mixed_corpus_seed_manifest.v1\"",
        "RAW_MIXED_CORPUS_SEED_MODE = \"raw_mixed_corpus_bridge_seed_only\"",
        "RAW_MIXED_CORPUS_ALLOWED_FIELDS = frozenset(",
        "RAW_MIXED_CORPUS_FORBIDDEN_FIELDS = frozenset(",
        "def seed_raw_mixed_corpus(payload: Mapping[str, Any], db: Session) -> dict[str, Any]:",
        "def _server_owned_manifest_path(artifact_manifest_ref: str) -> Path:",
        "Path(settings.storage_dir)",
        "db.get(DatasetVersion, dataset_version_id)",
        "DatasetSourceProvenance.connector_run_id == aps_run_id",
        "ApsContentLinkage.run_id == aps_run_id",
        "\"layer3_flow_started\": False",
        "RAW_MIXED_CORPUS_NEXT_ACTION",
    ):
        if term not in service_text:
            errors.append(f"{_rel(RAW_MIXED_BRIDGE_SERVICE)} missing raw mixed bridge runtime term: {term}")
    for forbidden_service_term in ("db.add(", "db.commit(", "open(", "glob(", "rglob("):
        if forbidden_service_term in service_text:
            errors.append(
                f"{_rel(RAW_MIXED_BRIDGE_SERVICE)} contains forbidden seed-only service term: {forbidden_service_term}"
            )

    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "layer3_raw_mixed_bridge",
        "class Layer3RawMixedCorpusSeedRequest",
        "class Layer3RawMixedCorpusSeedResponse",
        "RAW_MIXED_CORPUS_SEED_REQUEST_SCHEMA",
        "\"/source/mixed-corpus/seed\"",
        "layer3_raw_mixed_bridge.seed_raw_mixed_corpus",
        "payload.model_dump(exclude_unset=True)",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing raw mixed bridge API term: {term}")

    test_text = _read_required_text(RAW_MIXED_BRIDGE_TEST, errors)
    for term in (
        "test_layer3_raw_mixed_seed_reuses_existing_sources_without_flow_side_effects",
        "test_layer3_raw_mixed_seed_rejects_forbidden_fields_before_service_mutation",
        "test_layer3_raw_mixed_seed_rejects_unsupported_source_class_without_side_effects",
        "test_layer3_raw_mixed_seed_rejects_stale_manifest_hash_without_side_effects",
        "test_layer3_raw_mixed_seed_rejects_unknown_aps_target_without_side_effects",
        "test_layer3_raw_mixed_seed_rejects_missing_client_request_id_before_service",
        "_drive_preview_only_flow",
        "_counts(client)",
        "_storage_files()",
        "/api/v1/layer3/source/mixed-corpus/seed",
        "DatasetSourceProvenance",
        "raw_mixed_artifact_manifest_hash_mismatch",
        "raw_mixed_aps_target_not_found",
    ):
        if term not in test_text:
            errors.append(f"{_rel(RAW_MIXED_BRIDGE_TEST)} missing raw mixed bridge proof term: {term}")

    service_text = _read_required_text(SOURCE_BOUNDARY_SERVICE, errors)
    for term in (
        "SOURCE_BOUNDARY_MODE = \"supported_source_classes_only\"",
        "SUPPORTED_SOURCE_CLASSES = (\"dataset_version\", \"aps_content_document\")",
    ):
        if term not in service_text:
            errors.append(f"{_rel(SOURCE_BOUNDARY_SERVICE)} drifted before raw mixed bridge implementation: {term}")

    for path, terms in {
        BOARD: (
            "Raw mixed-corpus seed-only bridge runtime",
            "live bounded runtime",
            "raw_mixed_corpus_bridge_seed_only",
            "POST /api/v1/layer3/source/mixed-corpus/seed",
            "server-owned storage-root manifest",
            "local upload, local-directory ingestion",
            "flow execution inside seeding",
        ),
        MANIFEST: (
            "latest_raw_mixed_bridge_seed_branch",
            "raw_mixed_bridge_seed",
            "137_RAW_MIXED_BRIDGE_FREEZE.md",
            "backend/app/services/layer3_raw_mixed_bridge.py",
            "backend/tests/test_layer3_raw_mixed_bridge.py",
            "raw_mixed_corpus_bridge_seed_only",
            "seed-only route",
        ),
        PROOF_MANIFEST: (
            "latest_raw_mixed_bridge_seed_branch",
            "latest_raw_mixed_bridge_seed_input_main_commit",
            "latest_raw_mixed_bridge_seed_live_behavior_change",
            "latest_raw_mixed_bridge_seed_summary",
            "doc 137 raw mixed bridge governance now admits only raw_mixed_corpus_bridge_seed_only",
            "broad raw mixed-corpus ingestion beyond raw_mixed_corpus_bridge_seed_only",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing raw mixed bridge proof term: {term}")


def _check_source_breadth_freeze(errors: list[str]) -> None:
    doc_text = _read_required_text(SOURCE_BREADTH_FREEZE, errors)
    for term in (
        "Status: current-main source-breadth implementation-entry freeze",
        "selected_source_breadth_mode: `current_admitted_classes_with_server_owned_raw_materialization_only`",
        "`dataset_version`",
        "`aps_content_document`",
        "No new source class is admitted by this freeze.",
        "`rag_vector_index`",
        "`arbitrary_local_directory`",
        "`broad_file_upload`",
        "`web_connector`",
        "`unbounded_runtime_db`",
        "server-owned storage-root",
        "SHA-256 checked",
        "no Layer 3 flow state created by source materialization alone",
        "no rendered UI control is added unless a separate UI/theme freeze admits it",
        "This document freezes the next source-breadth posture without making raw ingestion live.",
    ):
        if term not in doc_text:
            errors.append(f"{_rel(SOURCE_BREADTH_FREEZE)} missing source-breadth term: {term}")

    service_text = _read_required_text(SOURCE_BOUNDARY_SERVICE, errors)
    for term in (
        "SOURCE_BOUNDARY_MODE = \"supported_source_classes_only\"",
        "SUPPORTED_SOURCE_CLASSES = (\"dataset_version\", \"aps_content_document\")",
    ):
        if term not in service_text:
            errors.append(f"{_rel(SOURCE_BOUNDARY_SERVICE)} drifted before source breadth freeze: {term}")

    required_terms = {
        POST_709_ROADMAP_FREEZE: (
            "153_SOURCE_BREADTH_FREEZE.md",
            "current_admitted_classes_with_server_owned_raw_materialization_only",
            "broader source-family expansion still requires a separate freeze and validation",
        ),
        PHASE1A_README: (
            "153_SOURCE_BREADTH_FREEZE.md",
            "current_admitted_classes_with_server_owned_raw_materialization_only",
            "does not make raw ingestion live",
        ),
        BOARD: (
            "Source breadth freeze",
            "current_admitted_classes_with_server_owned_raw_materialization_only",
            "does not make raw ingestion live",
            "theme behavior change",
        ),
        MANIFEST: (
            "latest_source_breadth_freeze_branch",
            "source_breadth_freeze",
            "current_admitted_classes_with_server_owned_raw_materialization_only",
            "server-owned storage-root, hash-checked materialization",
        ),
        PROOF_MANIFEST: (
            "source_breadth_freeze_proof",
            "selected_source_breadth_mode",
            "current_admitted_classes_with_server_owned_raw_materialization_only",
            "no rendered UI control or theme behavior change",
        ),
    }
    for path, terms in required_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing source-breadth proof term: {term}")


def _check_raw_ingestion_materialization_freeze(errors: list[str]) -> None:
    doc_text = _read_required_text(RAW_INGESTION_MATERIALIZATION_FREEZE, errors)
    for term in (
        "Status: bounded runtime contract",
        "selected_raw_ingestion_mode: `raw_mixed_existing_source_materialization_entry`",
        "owner service: `backend/app/services/layer3_raw_mixed_materialization.py`",
        "route: `POST /api/v1/layer3/source/mixed-corpus/materialize`",
        "request DTO: `Layer3RawMixedCorpusMaterializeRequest`",
        "response DTO: `Layer3RawMixedCorpusMaterializeResponse`",
        "layer3.raw_mixed_corpus_materialize_request.v1",
        "layer3.raw_mixed_corpus_materialize_result.v1",
        "layer3.raw_mixed_corpus_materialization_manifest.v1",
        "The existing `POST /api/v1/layer3/source/mixed-corpus/seed` route remains seed-only and must continue to write no database rows or files.",
        "The implementation must write no files.",
        "Partial materialization on failure is not admitted.",
        "No Layer 3 flow state during materialization",
    ):
        if term not in doc_text:
            errors.append(
                f"{_rel(RAW_INGESTION_MATERIALIZATION_FREEZE)} missing raw ingestion materialization term: {term}"
            )

    seed_doc_text = _read_required_text(RAW_MIXED_BRIDGE_FREEZE, errors)
    for term in (
        "writes no database rows",
        "file write behavior: writes no files",
        "successful seed action returns existing deterministic `DatasetVersion` and `ApsContentDocument` source authority only and writes no database rows or files",
    ):
        if term not in seed_doc_text:
            errors.append(f"{_rel(RAW_MIXED_BRIDGE_FREEZE)} missing seed-only no-write distinction: {term}")

    required_terms = {
        SOURCE_BREADTH_FREEZE: (
            "current_admitted_classes_with_server_owned_raw_materialization_only",
            "`dataset_version`",
            "`aps_content_document`",
        ),
        POST_709_ROADMAP_FREEZE: (
            "154_RAW_INGESTION_MATERIALIZATION_FREEZE.md",
            "raw_mixed_existing_source_materialization_entry",
            "broader source-family expansion still requires a separate freeze and validation",
        ),
        PHASE1A_README: (
            "154_RAW_INGESTION_MATERIALIZATION_FREEZE.md",
            "raw_mixed_existing_source_materialization_entry",
            "the existing seed route remains no-write and seed-only",
        ),
        BOARD: (
            "Raw ingestion materialization runtime",
            "Raw ingestion materialization bounded E2E",
            "Raw ingestion materialization rendered UI smoke",
            "raw_mixed_existing_source_materialization_entry",
            "leaves the seed route no-write and seed-only",
            "DatasetVersion.storage_ref",
        ),
        MANIFEST: (
            "latest_raw_ingestion_materialization_runtime_branch",
            "latest_raw_ingestion_materialization_bounded_e2e_branch",
            "latest_raw_ingestion_materialization_rendered_ui_smoke_branch",
            "raw_ingestion_materialization_runtime",
            "raw_ingestion_materialization_bounded_e2e",
            "raw_ingestion_materialization_rendered_ui_smoke",
            "raw_mixed_existing_source_materialization_entry",
            "writes no files, starts no Layer 3 flow",
            "DatasetVersion.storage_ref",
        ),
        PROOF_MANIFEST: (
            "raw_ingestion_materialization_runtime_proof",
            "raw_ingestion_materialization_bounded_e2e_proof",
            "raw_ingestion_materialization_rendered_ui_smoke_proof",
            "selected_raw_ingestion_mode",
            "raw_mixed_existing_source_materialization_entry",
            "POST /api/v1/layer3/source/mixed-corpus/materialize",
            "test_layer3_raw_mixed_materialization_drives_bounded_e2e_path",
            "Layer 3 workbench uses raw mixed materialization setup through rendered Gate C and plan approval",
        ),
    }
    for path, terms in required_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing raw ingestion materialization proof term: {term}")

    service_text = _read_required_text(RAW_MIXED_MATERIALIZATION_SERVICE, errors)
    for term in (
        'RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA_ID = "layer3.raw_mixed_corpus_materialize_request.v1"',
        'RAW_MIXED_CORPUS_MATERIALIZE_RESPONSE_SCHEMA_ID = "layer3.raw_mixed_corpus_materialize_result.v1"',
        'RAW_MIXED_CORPUS_MATERIALIZE_MANIFEST_SCHEMA_ID = "layer3.raw_mixed_corpus_materialization_manifest.v1"',
        'RAW_MIXED_CORPUS_MATERIALIZE_MODE = "raw_mixed_existing_source_materialization_entry"',
        "materialize_raw_mixed_corpus",
        "RAW_MIXED_CORPUS_FORBIDDEN_FIELDS",
        "unsupported_requested",
        "db.begin_nested()",
        "db.commit()",
        "files_written",
        "layer3_flow_started",
        "DatasetRow",
        "ApsContentLinkage",
        '_check_storage_ref(storage_ref, storage_hash, "artifact_manifest.dataset_versions[].storage_ref")',
        '"storage_ref": storage_ref',
    ):
        if term not in service_text:
            errors.append(f"{_rel(RAW_MIXED_MATERIALIZATION_SERVICE)} missing materialization runtime term: {term}")
    for forbidden_service_term in ("open(", "glob(", "rglob("):
        if forbidden_service_term in service_text:
            errors.append(
                f"{_rel(RAW_MIXED_MATERIALIZATION_SERVICE)} contains forbidden materialization service term: {forbidden_service_term}"
            )

    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "layer3_raw_mixed_materialization",
        "class Layer3RawMixedCorpusMaterializeRequest",
        "class Layer3RawMixedCorpusMaterializeResponse",
        "RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA",
        '"/source/mixed-corpus/materialize"',
        "layer3_raw_mixed_materialization.materialize_raw_mixed_corpus",
        "payload.model_dump(exclude_unset=True)",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing materialization API term: {term}")

    test_text = _read_required_text(RAW_MIXED_MATERIALIZATION_TEST, errors)
    for term in (
        "test_layer3_raw_mixed_materialize_creates_admitted_sources_for_bounded_preview",
        "test_layer3_raw_mixed_materialize_rejects_bad_manifest_hash_without_side_effects",
        "test_layer3_raw_mixed_materialize_rejects_manifest_outside_storage_root_without_side_effects",
        "test_layer3_raw_mixed_materialize_rejects_forbidden_request_and_manifest_fields",
        "test_layer3_raw_mixed_materialize_rejects_unsupported_source_classes_without_side_effects",
        "test_layer3_raw_mixed_materialize_rolls_back_existing_authority_conflicts",
        "_drive_preview_only_flow",
        "_assert_no_layer3_flow_delta",
        "dataset_storage_refs",
        "_month_period",
        "database_rows_written",
        "files_written",
    ):
        if term not in test_text:
            errors.append(f"{_rel(RAW_MIXED_MATERIALIZATION_TEST)} missing materialization proof term: {term}")

    bounded_e2e_text = _read_required_text(LAYER3_BOUNDED_E2E_TEST, errors)
    for term in (
        "test_layer3_raw_mixed_materialization_drives_bounded_e2e_path",
        "raw_mixed_materialize",
        "_seeded_sources_from_raw_mixed_materialization_response",
        "_source_authority_delta",
        "_drive_bounded_e2e_api_associated_cohort_to_download_delivery",
        "run_layer3_preflight_with_materialized_source_ids",
        "RAW_MIXED_CORPUS_MATERIALIZE_RESPONSE_SCHEMA_ID",
    ):
        if term not in bounded_e2e_text:
            errors.append(f"{_rel(LAYER3_BOUNDED_E2E_TEST)} missing materialization bounded E2E proof term: {term}")

    workbench_e2e_text = _read_required_text(LAYER3_WORKBENCH_E2E, errors)
    for term in (
        "Layer 3 workbench uses raw mixed materialization setup through rendered Gate C and plan approval",
        "materializeRawMixedSetup",
        "openRawMixedMaterializedWorkbench",
        "/api/v1/layer3/source/mixed-corpus/materialize",
        "/__test/layer3/materialize-raw-mixed",
        "raw_mixed_existing_source_materialization_entry",
        "run_layer3_preflight_with_materialized_source_ids",
        "expectNoDeferredRawMixedControls",
    ):
        if term not in workbench_e2e_text:
            errors.append(f"{_rel(LAYER3_WORKBENCH_E2E)} missing materialization rendered UI smoke term: {term}")

    review_browser_text = _read_required_text(REVIEW_BROWSER_SERVER, errors)
    for term in (
        "project6.review_browser_raw_mixed_materialization_setup.v1",
        "/__test/layer3/materialize-raw-mixed",
        "_build_browser_raw_mixed_materialization_setup",
        "RAW_MIXED_CORPUS_MATERIALIZE_MANIFEST_SCHEMA_ID",
        "RAW_MIXED_CORPUS_MATERIALIZE_REQUEST_SCHEMA_ID",
        "RAW_MIXED_CORPUS_MATERIALIZE_MODE",
    ):
        if term not in review_browser_text:
            errors.append(f"{_rel(REVIEW_BROWSER_SERVER)} missing materialization rendered UI setup term: {term}")


def _check_raw_mixed_rendered_ui_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        RAW_MIXED_RENDERED_UI_FREEZE: (
            "Status: live bounded rendered `/review/layer3` raw mixed materialization workflow",
            "selected_raw_mixed_rendered_ui_mode: `raw_mixed_server_owned_manifest_ref_ui_entry`",
            "POST /api/v1/layer3/source/mixed-corpus/materialize",
            "The UI collects a server-owned materialization manifest reference and hash",
            "Current main now admits the bounded server-owned manifest-ref controls described here.",
            "Backend service/API changes are not admitted by this freeze.",
            "The rendered request may include only fields already admitted by `Layer3RawMixedCorpusMaterializeRequest`",
            "server-owned storage-root ref, not as a local path",
            "Theme Posture",
            "headless Chromium for the raw mixed rendered manifest path",
            "headed Chromium for the same path",
            "no frontend-only durable authority",
        ),
        RAW_MIXED_RENDERED_UI_CONTRACT: (
            "Status: live rendered UI contract paired with `155_RAW_MIXED_RENDERED_UI_FREEZE.md`.",
            "raw_mixed_server_owned_manifest_ref_ui_entry",
            "Server state is the only durable authority.",
            "The rendered UI may call only the already-live materialization route",
            "refresh source candidate APIs and select only the returned IDs",
            "The UI must reject or omit every field outside the live DTO.",
            "Success state may enable downstream rendered source selection only after candidate refresh confirms the returned source IDs.",
            "Theme And Accessibility Contract",
            "headed and headless Chromium run the same raw mixed rendered manifest workflow",
            "frontend-only durable authority",
        ),
        BOARD: (
            "Raw mixed rendered manifest UI runtime",
            "raw_mixed_server_owned_manifest_ref_ui_entry",
            "bounded rendered materialization controls",
            "frontend-only durable authority",
        ),
        MANIFEST: (
            "latest_raw_mixed_rendered_ui_freeze_branch",
            "latest_raw_mixed_rendered_ui_freeze_live_behavior_change",
            "raw_mixed_rendered_ui_freeze",
            "raw_mixed_server_owned_manifest_ref_ui_entry",
            "live raw_mixed_server_owned_manifest_ref_ui_entry",
            "theme behavior",
        ),
        PROOF_MANIFEST: (
            "raw_mixed_rendered_ui_freeze_proof",
            "selected_raw_mixed_rendered_ui_mode",
            "raw_mixed_server_owned_manifest_ref_ui_entry",
            "browser_proof",
            "headed Chromium",
            "headless Chromium",
            "no production backend route, DTO, service, model, or migration change",
        ),
        LAYER3_HTML: (
            "raw-mixed-corpus-batch-id",
            "raw-mixed-manifest-ref",
            "raw-mixed-manifest-hash",
            "raw-mixed-operator-confirmation",
            "raw-mixed-materialize",
            "Materialize Source IDs",
        ),
        LAYER3_CSS: (
            ".raw-mixed-materialization",
            ".raw-mixed-materialization-grid",
            ".raw-mixed-materialization-status",
            "html[data-theme=\"workbench\"] body.layer3-page .raw-mixed-materialization",
        ),
        LAYER3_JS: (
            "RAW_MIXED_MATERIALIZE_REQUEST_SCHEMA_ID",
            "RAW_MIXED_MATERIALIZE_MODE",
            "rawMixedMaterializationPayload",
            "postJson('/source/mixed-corpus/materialize'",
            "materializedSourceIdsVisible",
            "applyMaterializedSourceIds",
            "clearLayer3FlowStateForSourceChange",
        ),
        LAYER3_PAGE_TEST: (
            "raw-mixed-corpus-batch-id",
            "raw-mixed-materialization",
            "rawMixedMaterializationPayload",
            "postJson('/source/mixed-corpus/materialize'",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench materializes raw mixed manifest through rendered controls",
            "materializeRawMixedThroughRenderedControls",
            "expectOnlyPayloadKeys(requestPayload",
            "raw_mixed_existing_source_materialization_entry",
            "selected after candidate refresh",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing raw mixed rendered UI freeze term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_raw_mixed_rendered_ui_freeze_branch") != "codex/l3-raw-mixed-rendered-ui":
            errors.append(f"{_rel(MANIFEST)} current_status has stale raw mixed rendered UI freeze branch")
        if current_status.get("latest_raw_mixed_rendered_ui_freeze_live_behavior_change") is not True:
            errors.append(f"{_rel(MANIFEST)} current_status must mark raw mixed rendered UI freeze as live")


def _check_post_730_roadmap_sync(errors: list[str]) -> None:
    required_doc_terms = {
        POST_730_ROADMAP_SYNC: (
            "Status: current-main planning/control reference after raw mixed rendered materialization controls became live.",
            "PR `#730`, merge commit `ec160cb3e5b829bb314498131a149b206378c3f7`",
            "raw_mixed_server_owned_manifest_ref_ui_entry",
            "Current main admits these bounded Layer 3 paths:",
            "post-PR730 practical readiness audit",
            "deeper rendered raw mixed UI path using the live controls",
            "source-family expansion beyond `dataset_version` and `aps_content_document`",
            "This roadmap sync is accepted only when:",
        ),
        BOARD: (
            "Post-PR730 roadmap sync",
            "157_POST_730_ROADMAP_SYNC.md",
            "ec160cb3e5b829bb314498131a149b206378c3f7",
            "planning/control only",
            "post-PR730 practical readiness audit",
        ),
        MANIFEST: (
            "latest_post_730_roadmap_sync_branch",
            "latest_post_730_roadmap_sync_live_behavior_change",
            "post_730_roadmap_sync",
            "Doc 157 records the post-PR730 current-main roadmap posture",
            "post-PR730 practical readiness audit",
        ),
        PROOF_MANIFEST: (
            "post_730_roadmap_sync_proof",
            "157_POST_730_ROADMAP_SYNC.md",
            "PR #730 merge commit ec160cb3e5b829bb314498131a149b206378c3f7",
            "raw_mixed_server_owned_manifest_ref_ui_entry",
            "no runtime behavior change",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing post-730 roadmap sync term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_post_730_roadmap_sync_branch") != "codex/l3-post730-roadmap-sync":
            errors.append(f"{_rel(MANIFEST)} current_status has stale post-730 roadmap sync branch")
        if current_status.get("latest_post_730_roadmap_sync_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark post-730 roadmap sync as planning-only")


def _check_post_730_practical_readiness(errors: list[str]) -> None:
    required_doc_terms = {
        POST_730_PRACTICAL_READINESS: (
            "Status: current-main practical readiness checkpoint after PR `#730` and roadmap sync PR `#731`.",
            "df018510607bbcc9d07bcebdb7ec6b7701cf1c8d",
            "ec160cb3e5b829bb314498131a149b206378c3f7",
            "raw_mixed_server_owned_manifest_ref_ui_entry",
            "fixed `SERVER_PORT = 8031`, `fullyParallel: false`, and `workers: 1`",
            "run headed and headless browser validation sequentially",
            "The next implementation-eligible pass is:",
            "deeper rendered raw mixed downstream path",
        ),
        BOARD: (
            "Post-PR730 practical readiness audit",
            "158_POST_730_PRACTICAL_READINESS.md",
            "fixed-port `8031` shared Playwright harness",
            "sequential headless and headed raw mixed rendered smoke",
            "deeper rendered raw mixed downstream path",
        ),
        MANIFEST: (
            "latest_post_730_practical_readiness_branch",
            "latest_post_730_practical_readiness_live_behavior_change",
            "post_730_practical_readiness",
            "fixed-port 8031 shared harness",
            "test-only deeper rendered raw mixed downstream path",
        ),
        PROOF_MANIFEST: (
            "post_730_practical_readiness_proof",
            "158_POST_730_PRACTICAL_READINESS.md",
            "fixed-port 8031 sequential-run caveat",
            "no runtime behavior change",
            "test-only deeper rendered raw mixed downstream path",
        ),
        PLAYWRIGHT_CONFIG: (
            "const SERVER_PORT = 8031;",
            "fullyParallel: false",
            "workers: 1",
            "reuseExistingServer: false",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing post-730 practical readiness term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_post_730_practical_readiness_branch") != "codex/l3-post730-readiness-audit":
            errors.append(f"{_rel(MANIFEST)} current_status has stale post-730 practical readiness branch")
        if current_status.get("latest_post_730_practical_readiness_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark post-730 practical readiness as report-only")


def _check_raw_mixed_rendered_downstream_blocker(errors: list[str]) -> None:
    required_doc_terms = {
        RAW_MIXED_RENDERED_DOWNSTREAM_BLOCKER: (
            "Status: current-main planning/control blocker report for deeper rendered raw mixed downstream proof.",
            "d6a70a86eac76c7931822a1cda66bdfaff99bb36",
            "raw_mixed_server_owned_manifest_ref_ui_entry",
            "The deeper rendered raw mixed downstream path is blocked at rendered plan approval on current main.",
            "no rendered execution selection/start controls",
            "Using API calls to `/execution/select` and `/execution/start` after rendered materialization and plan approval would not satisfy",
            "raw_mixed_rendered_execution_selection_start_controls",
        ),
        BOARD: (
            "Raw mixed rendered downstream blocker",
            "159_RAW_MIXED_RENDERED_DOWNSTREAM_BLOCKER.md",
            "no rendered execution selection/start controls",
            "planning/control freeze for rendered execution selection/start controls",
        ),
        MANIFEST: (
            "latest_raw_mixed_rendered_downstream_blocker_branch",
            "latest_raw_mixed_rendered_downstream_blocker_live_behavior_change",
            "raw_mixed_rendered_downstream_blocker",
            "no rendered execution selection/start controls",
        ),
        PROOF_MANIFEST: (
            "raw_mixed_rendered_downstream_blocker_proof",
            "159_RAW_MIXED_RENDERED_DOWNSTREAM_BLOCKER.md",
            "no rendered execution selection/start controls",
            "no hidden API substitute for missing rendered execution controls",
        ),
        LAYER3_HTML: (
            "result-status-inspect",
            "package-review-preview-inspect",
            "handoff-export-prepare-submit",
            "external-export-download-prepare-submit",
        ),
        LAYER3_JS: (
            "postJson('/execution/result/status'",
            "postJson('/package/review/preview'",
        ),
        LAYER3_WORKBENCH_E2E: (
            "assertRenderedPlanApprovalStopsBeforeExecution",
            "expect(sessionSummary.execution_selection.selected).toBe(false)",
            "'/execution/select'",
            "'/execution/start'",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing raw mixed rendered downstream blocker term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_raw_mixed_rendered_downstream_blocker_branch") != "codex/l3-raw-mixed-rendered-downstream":
            errors.append(f"{_rel(MANIFEST)} current_status has stale raw mixed rendered downstream blocker branch")
        if current_status.get("latest_raw_mixed_rendered_downstream_blocker_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark raw mixed rendered downstream blocker as planning-only")


def _check_rendered_execution_selection_start_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_EXECUTION_SELECTION_START_FREEZE: (
            "Status: planning/control freeze only for `raw_mixed_rendered_execution_selection_start_controls`.",
            "selected rendered execution mode: `raw_mixed_rendered_execution_selection_start_controls`",
            "POST /api/v1/layer3/execution/select",
            "POST /api/v1/layer3/execution/start",
            "#execution-select",
            "#execution-start",
            "#execution-selection-start-panel",
            "The future pass may add no backend route, DTO, service, model, or migration.",
            "frontend-only durable authority",
            "fixed `SERVER_PORT = 8031`, `fullyParallel: false`, and `workers: 1`",
            "light` theme",
            "dark` theme",
            "workbench` theme",
        ),
        RENDERED_EXECUTION_SELECTION_START_CONTRACT: (
            "Status: planning/control UI and API contract for `160_RENDERED_EXECUTION_SELECTION_START_FREEZE.md`.",
            "Selected mode: `raw_mixed_rendered_execution_selection_start_controls`.",
            "Layer3ExecutionSelectionRequest",
            "Layer3ExecutionSelectionResponse",
            "Layer3AnalysisExecutionStartRequest",
            "Layer3AnalysisExecutionStartResponse",
            "POST /api/v1/layer3/execution/select",
            "POST /api/v1/layer3/execution/start",
            "`synchronous_single_pass`",
            "`light`",
            "`dark`",
            "`workbench`",
            "no frontend-only durable authority",
        ),
        BOARD: (
            "Rendered execution selection/start freeze",
            "160_RENDERED_EXECUTION_SELECTION_START_FREEZE.md",
            "161_RENDERED_EXECUTION_SELECTION_START_CONTRACT.md",
            "raw_mixed_rendered_execution_selection_start_controls",
            "POST /api/v1/layer3/execution/select",
            "POST /api/v1/layer3/execution/start",
            "headed and headless Chromium sequentially on fixed port `8031`",
        ),
        MANIFEST: (
            "latest_rendered_execution_selection_start_freeze_branch",
            "latest_rendered_execution_selection_start_freeze_live_behavior_change",
            "rendered_execution_selection_start_freeze",
            "raw_mixed_rendered_execution_selection_start_controls",
            "fixed port 8031",
            "light, dark, and workbench theme states",
        ),
        PROOF_MANIFEST: (
            "rendered_execution_selection_start_freeze_proof",
            "160_RENDERED_EXECUTION_SELECTION_START_FREEZE.md",
            "161_RENDERED_EXECUTION_SELECTION_START_CONTRACT.md",
            "raw_mixed_rendered_execution_selection_start_controls",
            "Layer3ExecutionSelectionRequest",
            "Layer3AnalysisExecutionStartRequest",
            "headless Chromium",
            "headed Chromium",
            "no runtime behavior change",
        ),
        LAYER3_API: (
            "class Layer3ExecutionSelectionRequest(BaseModel):",
            "class Layer3AnalysisExecutionStartRequest(BaseModel):",
            "class Layer3ExecutionSelectionResponse(Layer3BaseResponse):",
            "class Layer3AnalysisExecutionStartResponse(Layer3BaseResponse):",
            '"/execution/select"',
            '"/execution/start"',
            '"synchronous_single_pass"',
        ),
        LAYER3_HTML: (
            "result-status-inspect",
            "package-review-preview-inspect",
            "handoff-export-prepare-submit",
            "external-export-download-prepare-submit",
            "theme-selector",
        ),
        LAYER3_JS: (
            "setStepChip(elements.executionStep, Boolean(State.executionSelection || State.sessionSummary?.execution_selection?.selected))",
            "postJson('/execution/result/status'",
            "postJson('/package/review/preview'",
            "THEME_STORAGE_KEY",
            "LAYER3_THEME_STORAGE_KEY",
        ),
        LAYER3_WORKBENCH_E2E: (
            "assertRenderedPlanApprovalStopsBeforeExecution",
            "'/execution/select'",
            "'/execution/start'",
            "Layer 3 workbench materializes raw mixed manifest through rendered controls",
            "Layer 3 workbench exposes visible keyboard focus across themes",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing rendered execution selection/start freeze term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_execution_selection_start_freeze_branch") != "codex/l3-rendered-execution-freeze":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered execution selection/start freeze branch")
        if current_status.get("latest_rendered_execution_selection_start_freeze_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered execution selection/start freeze as planning-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_execution_selection_start_freeze_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_execution_selection_start_freeze_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered execution selection/start freeze proof must be planning-only")
    if proof.get("selected_rendered_execution_mode") != "raw_mixed_rendered_execution_selection_start_controls":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered execution selection/start freeze proof has stale selected mode")
    for selector in ("#execution-select", "#execution-start", "#execution-selection-start-panel"):
        if selector not in proof.get("future_selectors", []):
            errors.append(f"{_rel(PROOF_MANIFEST)} future_selectors missing {selector}")


def _check_rendered_execution_selection_start_runtime(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_EXECUTION_SELECTION_START_RUNTIME: (
            "Status: live bounded runtime for `raw_mixed_rendered_execution_selection_start_controls`.",
            "POST /api/v1/layer3/execution/select",
            "POST /api/v1/layer3/execution/start",
            "#execution-select",
            "#execution-start",
            "#execution-selection-start-panel",
            "Layer 3 workbench drives raw mixed rendered execution selection and start",
            "no frontend-only durable authority",
            "light, dark, and workbench theme states",
        ),
        BOARD: (
            "Rendered execution selection/start runtime",
            "162_RENDERED_EXECUTION_SELECTION_START_RUNTIME.md",
            "raw_mixed_rendered_execution_selection_start_controls",
            "Layer 3 workbench drives raw mixed rendered execution selection and start",
        ),
        MANIFEST: (
            "latest_rendered_execution_selection_start_runtime_branch",
            "latest_rendered_execution_selection_start_runtime_live_behavior_change",
            "rendered_execution_selection_start_runtime",
            "raw_mixed_rendered_execution_selection_start_controls",
            "Layer 3 workbench drives raw mixed rendered execution selection and start",
        ),
        PROOF_MANIFEST: (
            "rendered_execution_selection_start_runtime_proof",
            "162_RENDERED_EXECUTION_SELECTION_START_RUNTIME.md",
            "raw_mixed_rendered_execution_selection_start_controls",
            "Layer 3 workbench drives raw mixed rendered execution selection and start",
            "no frontend-only durable authority",
        ),
        LAYER3_HTML: (
            "execution-select",
            "execution-start",
            "execution-selection-start-panel",
        ),
        LAYER3_JS: (
            "State.executionSelection",
            "State.executionStart",
            "executionSelectionState",
            "executionPlanAuthority",
            "canSelectExecution",
            "canStartExecution",
            "renderExecutionSelectionStartPanel",
            "executionSelectionPayload",
            "executionStartPayload",
            "postJson('/execution/select'",
            "postJson('/execution/start'",
            "execution_mode: 'synchronous_single_pass'",
            "setStepChip(elements.executionStep, Boolean(State.executionSelection || State.sessionSummary?.execution_selection?.selected))",
        ),
        LAYER3_PAGE_TEST: (
            "execution-select",
            "execution-start",
            "execution-selection-start-panel",
            "postJson('/execution/select'",
            "postJson('/execution/start'",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench drives raw mixed rendered execution selection and start",
            "reloadRecoveredExecutionSession",
            "selectAndStartRenderedExecution",
            "inspectRenderedResultStatus",
            "expectOnlyPayloadKeys(selectionPayload",
            "expectOnlyPayloadKeys(startPayload",
            "expectNoRequestsToLayer3Paths(layer3ApiRequests",
            "cohort_result_review_ui_review_ready",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing rendered execution selection/start runtime term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_execution_selection_start_runtime_branch") != "codex/l3-rendered-execution-controls":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered execution selection/start runtime branch")
        if current_status.get("latest_rendered_execution_selection_start_runtime_live_behavior_change") is not True:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered execution selection/start runtime as live")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_execution_selection_start_runtime_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_execution_selection_start_runtime_proof object")
        return
    if proof.get("live_behavior_change") is not True:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered execution selection/start runtime proof must be live")
    if proof.get("selected_rendered_execution_mode") != "raw_mixed_rendered_execution_selection_start_controls":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered execution selection/start runtime proof has stale selected mode")
    selectors = proof.get("live_selectors")
    if not isinstance(selectors, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered execution selection/start runtime proof missing live_selectors")
    else:
        for selector in ("#execution-select", "#execution-start", "#execution-selection-start-panel"):
            if selector not in selectors:
                errors.append(f"{_rel(PROOF_MANIFEST)} live_selectors missing {selector}")


def _check_rendered_result_review_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_RESULT_REVIEW_FREEZE: (
            "Status: planning/control freeze only for `raw_mixed_rendered_result_review_submit`.",
            "POST /api/v1/layer3/execution/result/review",
            "Layer3ExecutionResultReviewRequest",
            "Layer3ExecutionResultReviewResponse",
            "#result-review-decision",
            "#result-review-notes",
            "#result-review-submit",
            "#package-review-preview-inspect",
            "cohort_result_review_ui_review_ready",
            "light`, `dark`, and `workbench`",
            "no frontend-only durable authority",
        ),
        RENDERED_RESULT_REVIEW_CONTRACT: (
            "Selected mode: `raw_mixed_rendered_result_review_submit`.",
            "POST /api/v1/layer3/execution/result/review",
            "Layer3ExecutionResultReviewRequest",
            "Layer3ExecutionResultReviewResponse",
            "#result-review-decision",
            "#result-review-notes",
            "#result-review-submit",
            "#result-review-panel",
            "#package-review-preview-inspect",
            "light`, `dark`, and `workbench`",
            "frontend-only durable authority",
        ),
        BOARD: (
            "Rendered result-review freeze",
            "163_RENDERED_RESULT_REVIEW_FREEZE.md",
            "164_RENDERED_RESULT_REVIEW_CONTRACT.md",
            "raw_mixed_rendered_result_review_submit",
            "POST /api/v1/layer3/execution/result/review",
        ),
        MANIFEST: (
            "latest_rendered_result_review_freeze_branch",
            "latest_rendered_result_review_freeze_live_behavior_change",
            "rendered_result_review_freeze",
            "raw_mixed_rendered_result_review_submit",
            "/execution/result/review request allowlist",
        ),
        PROOF_MANIFEST: (
            "rendered_result_review_freeze_proof",
            "163_RENDERED_RESULT_REVIEW_FREEZE.md",
            "164_RENDERED_RESULT_REVIEW_CONTRACT.md",
            "raw_mixed_rendered_result_review_submit",
            "#result-review-submit",
            "no frontend-only durable authority",
        ),
        LAYER3_API: (
            "class Layer3ExecutionResultReviewRequest(BaseModel):",
            "class Layer3ExecutionResultReviewResponse(Layer3BaseResponse):",
            '"/execution/result/review"',
            "package_variant: Any | None = None",
            "rewrite_output: Any | None = None",
        ),
        LAYER3_HTML: (
            "result-review-decision",
            "result-review-notes",
            "result-review-submit",
            "package-review-preview-inspect",
        ),
        LAYER3_JS: (
            "function canSubmitResultReview",
            "function resultReviewPayload",
            "postJson('/execution/result/review'",
            "cohort_result_review_ui_review_ready",
            "cohort_result_review_ui_recorded",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench drives raw mixed rendered execution selection and start",
            "inspectRenderedResultStatus",
            "cohort_result_review_ui_review_ready",
            "/execution/result/review",
            "/package/review/",
            "/handoff/",
        ),
        LAYER3_FLOW_E2E: (
            "Layer 3 workbench records selected-pass result review only after status authority",
            "#result-review-decision",
            "#result-review-notes",
            "#result-review-submit",
            "expectOnlyPayloadKeys(reviewPayload",
            "changes_requested",
            "package_review_enabled",
            "handoff_enabled",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing rendered result-review freeze term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_result_review_freeze_branch") != "codex/l3-rendered-result-review-freeze":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered result-review freeze branch")
        if current_status.get("latest_rendered_result_review_freeze_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered result-review freeze as planning-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_result_review_freeze_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_result_review_freeze_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered result-review freeze proof must be planning-only")
    if proof.get("selected_rendered_result_review_mode") != "raw_mixed_rendered_result_review_submit":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered result-review freeze proof has stale selected mode")
    for selector in (
        "#result-review-decision",
        "#result-review-notes",
        "#result-review-submit",
        "#result-review-panel",
        "#package-review-preview-inspect",
    ):
        if selector not in proof.get("future_selectors", []):
            errors.append(f"{_rel(PROOF_MANIFEST)} future_selectors missing {selector}")


def _check_rendered_result_review_proof(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_RESULT_REVIEW_PROOF: (
            "Status: live rendered browser proof for `raw_mixed_rendered_result_review_submit`.",
            "POST /api/v1/layer3/execution/result/review",
            "Layer3ExecutionResultReviewRequest",
            "Layer3ExecutionResultReviewResponse",
            "Layer 3 workbench drives raw mixed rendered result-review submit",
            "submitRenderedResultReview",
            "#result-review-decision",
            "#result-review-notes",
            "#result-review-submit",
            "#package-review-preview-inspect",
            "light` from rendered result/status inspection",
            "no frontend-only durable authority",
        ),
        BOARD: (
            "Rendered result-review proof",
            "165_RENDERED_RESULT_REVIEW_PROOF.md",
            "raw_mixed_rendered_result_review_submit",
            "Layer 3 workbench drives raw mixed rendered result-review submit",
        ),
        MANIFEST: (
            "latest_rendered_result_review_proof_branch",
            "latest_rendered_result_review_proof_live_behavior_change",
            "rendered_result_review_proof",
            "Layer 3 workbench drives raw mixed rendered result-review submit",
            "notes-required changes_requested branch",
        ),
        PROOF_MANIFEST: (
            "rendered_result_review_proof",
            "165_RENDERED_RESULT_REVIEW_PROOF.md",
            "raw_mixed_rendered_result_review_submit",
            "Layer 3 workbench drives raw mixed rendered result-review submit",
            "submitRenderedResultReview",
            "no frontend-only durable authority",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench drives raw mixed rendered result-review submit",
            "submitRenderedResultReview",
            "cohort_result_review_ui_review_ready",
            "cohort_result_review_ui_recorded",
            "expectOnlyPayloadKeys(reviewPayload",
            "expect(reviewPayload.operator_decision).toBe('changes_requested')",
            "expect(reviewPayload).not.toHaveProperty('artifact_manifest')",
            "expect(review.package_review_enabled).toBe(false)",
            "expect(review.handoff_enabled).toBe(false)",
            "expectNoRequestsToLayer3Paths(layer3ApiRequests",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing rendered result-review proof term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_result_review_proof_branch") != "codex/l3-rendered-result-review-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered result-review proof branch")
        if current_status.get("latest_rendered_result_review_proof_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered result-review proof as test-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_result_review_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_result_review_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered result-review proof must be test-only")
    if proof.get("selected_rendered_result_review_mode") != "raw_mixed_rendered_result_review_submit":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered result-review proof has stale selected mode")
    selectors = proof.get("live_selectors")
    if not isinstance(selectors, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered result-review proof missing live_selectors")
    else:
        for selector in (
            "#result-review-decision",
            "#result-review-notes",
            "#result-review-submit",
            "#result-review-panel",
            "#package-review-preview-inspect",
        ):
            if selector not in selectors:
                errors.append(f"{_rel(PROOF_MANIFEST)} live_selectors missing {selector}")


def _check_rendered_package_review_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_PACKAGE_REVIEW_FREEZE: (
            "Status: planning/control freeze only for `raw_mixed_rendered_package_review_preview_commit_submit`.",
            "POST /api/v1/layer3/package/review/preview",
            "POST /api/v1/layer3/package/review/commit",
            "POST /api/v1/layer3/package/review/submit",
            "Layer3PackageReviewPreviewRequest",
            "Layer3PackageConstructionCommitRequest",
            "Layer3PackageReviewSubmitRequest",
            "Layer3PackageReviewPreviewResponse",
            "Layer3PackageConstructionCommitResponse",
            "Layer3PackageReviewSubmitResponse",
            "#package-review-preview-inspect",
            "#package-construction-commit",
            "#package-review-submit-decision",
            "#package-review-submit-notes",
            "#package-review-submit",
            "approved` result-review",
            "light`, `dark`, and `workbench`",
            "no frontend-only durable authority",
        ),
        RENDERED_PACKAGE_REVIEW_CONTRACT: (
            "Selected mode: `raw_mixed_rendered_package_review_preview_commit_submit`.",
            "POST /api/v1/layer3/package/review/preview",
            "POST /api/v1/layer3/package/review/commit",
            "POST /api/v1/layer3/package/review/submit",
            "Layer3PackageReviewPreviewRequest",
            "Layer3PackageConstructionCommitRequest",
            "Layer3PackageReviewSubmitRequest",
            "Layer3PackageReviewPreviewResponse",
            "Layer3PackageConstructionCommitResponse",
            "Layer3PackageReviewSubmitResponse",
            "#package-review-preview-inspect",
            "#package-construction-commit",
            "#package-review-submit-decision",
            "#package-review-submit-notes",
            "#package-review-submit",
            "#package-review-preview-panel",
            "light`, `dark`, and `workbench`",
            "frontend-only durable authority",
        ),
        BOARD: (
            "Rendered package-review freeze",
            "166_RENDERED_PACKAGE_REVIEW_FREEZE.md",
            "167_RENDERED_PACKAGE_REVIEW_CONTRACT.md",
            "raw_mixed_rendered_package_review_preview_commit_submit",
            "POST /api/v1/layer3/package/review/submit",
        ),
        MANIFEST: (
            "latest_rendered_package_review_freeze_branch",
            "latest_rendered_package_review_freeze_live_behavior_change",
            "rendered_package_review_freeze",
            "raw_mixed_rendered_package_review_preview_commit_submit",
            "/package/review/preview request allowlist",
        ),
        PROOF_MANIFEST: (
            "rendered_package_review_freeze_proof",
            "166_RENDERED_PACKAGE_REVIEW_FREEZE.md",
            "167_RENDERED_PACKAGE_REVIEW_CONTRACT.md",
            "raw_mixed_rendered_package_review_preview_commit_submit",
            "#package-review-submit",
            "no frontend-only durable authority",
        ),
        LAYER3_API: (
            "class Layer3PackageReviewPreviewRequest(BaseModel):",
            "class Layer3PackageConstructionCommitRequest(BaseModel):",
            "class Layer3PackageReviewSubmitRequest(BaseModel):",
            "class Layer3PackageReviewPreviewResponse(Layer3BaseResponse):",
            "class Layer3PackageConstructionCommitResponse(Layer3BaseResponse):",
            "class Layer3PackageReviewSubmitResponse(Layer3BaseResponse):",
            '"/package/review/preview"',
            '"/package/review/commit"',
            '"/package/review/submit"',
            "package_payload: Any | None = None",
            "package_variant_content: Any | None = None",
        ),
        LAYER3_HTML: (
            "package-review-preview-inspect",
            "package-construction-commit",
            "package-review-submit-form",
            "package-review-submit-decision",
            "package-review-submit-notes",
            "package-review-submit",
            "package-review-preview-panel",
        ),
        LAYER3_JS: (
            "function recordedApprovedResultReview",
            "function canInspectPackageReviewPreview",
            "function canCommitPackageConstruction",
            "function canSubmitPackageReview",
            "function packageReviewPreviewPayload",
            "function packageConstructionPayload",
            "function packageReviewSubmitPayload",
            "postJson('/package/review/preview'",
            "postJson('/package/review/commit'",
            "postJson('/package/review/submit'",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench drives raw mixed rendered result-review submit",
            "submitRenderedResultReview",
            "expect(reviewPayload.operator_decision).toBe('changes_requested')",
            "expect(review.package_review_enabled).toBe(false)",
            "expectNoRequestsToLayer3Paths(layer3ApiRequests",
            "/package/review/",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing rendered package-review freeze term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_package_review_freeze_branch") != "codex/l3-package-freeze":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered package-review freeze branch")
        if current_status.get("latest_rendered_package_review_freeze_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered package-review freeze as planning-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_package_review_freeze_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_package_review_freeze_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered package-review freeze proof must be planning-only")
    if proof.get("selected_rendered_package_review_mode") != "raw_mixed_rendered_package_review_preview_commit_submit":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered package-review freeze proof has stale selected mode")
    routes = proof.get("routes_to_reuse")
    if not isinstance(routes, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered package-review freeze proof missing routes_to_reuse")
    else:
        for route in (
            "POST /api/v1/layer3/package/review/preview",
            "POST /api/v1/layer3/package/review/commit",
            "POST /api/v1/layer3/package/review/submit",
        ):
            if route not in routes:
                errors.append(f"{_rel(PROOF_MANIFEST)} routes_to_reuse missing {route}")
    selectors = proof.get("future_selectors")
    if not isinstance(selectors, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered package-review freeze proof missing future_selectors")
    else:
        for selector in (
            "#package-review-preview-inspect",
            "#package-construction-commit",
            "#package-review-submit-decision",
            "#package-review-submit-notes",
            "#package-review-submit",
            "#package-review-preview-panel",
        ):
            if selector not in selectors:
                errors.append(f"{_rel(PROOF_MANIFEST)} future_selectors missing {selector}")


def _check_rendered_package_review_proof(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_PACKAGE_REVIEW_PROOF: (
            "Status: live test-only rendered browser proof for `raw_mixed_rendered_package_review_preview_commit_submit`.",
            "Layer 3 workbench drives raw mixed rendered package-review preview commit and submit",
            "inspectRenderedPackagePreview",
            "commitRenderedPackageConstruction",
            "submitRenderedPackageReview",
            "POST /api/v1/layer3/package/review/preview",
            "POST /api/v1/layer3/package/review/commit",
            "POST /api/v1/layer3/package/review/submit",
            "layer3.package_review_preview.v1",
            "layer3.package_construction_commit.v1",
            "layer3.cohort_package_review_submit.v1",
            "server-returned `package_review_preview_hash`",
            "server-returned `reconciliation_record_id`",
            "package-review submit state `package_review_approved`",
            "`construction_basis_hash` null",
            "[data-operation-target=\"package-review-band\"]",
            "no frontend-only durable authority",
        ),
        BOARD: (
            "Rendered package-review proof",
            "168_RENDERED_PACKAGE_REVIEW_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered package-review preview commit and submit",
            "raw_mixed_rendered_package_review_preview_commit_submit",
            "package_review_approved",
        ),
        MANIFEST: (
            "latest_rendered_package_review_proof_branch",
            "latest_rendered_package_review_proof_live_behavior_change",
            "rendered_package_review_proof",
            "168_RENDERED_PACKAGE_REVIEW_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered package-review preview commit and submit",
        ),
        PROOF_MANIFEST: (
            "rendered_package_review_proof",
            "168_RENDERED_PACKAGE_REVIEW_PROOF.md",
            "raw_mixed_rendered_package_review_preview_commit_submit",
            "inspectRenderedPackagePreview",
            "commitRenderedPackageConstruction",
            "submitRenderedPackageReview",
            "Layer 3 workbench drives raw mixed rendered package-review preview commit and submit",
            "layer3.cohort_package_review_submit.v1",
            "no frontend-only durable authority",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench drives raw mixed rendered package-review preview commit and submit",
            "inspectRenderedPackagePreview",
            "commitRenderedPackageConstruction",
            "submitRenderedPackageReview",
            "expect(previewPayload.result_review_record_ref).toBe(review.review_record_ref)",
            "expect(commitPayload.expected_package_kinds).toEqual(EXPECTED_PACKAGE_REVIEW_KINDS)",
            "expect(submitPayload.operator_decision).toBe('approved')",
            "expect(packageSubmit.package_review_state).toBe('package_review_approved')",
            "expectNoRequestsToLayer3Paths(layer3ApiRequests",
            "/handoff/",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing rendered package-review proof term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_package_review_proof_branch") != "codex/l3-rendered-package-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered package-review proof branch")
        if current_status.get("latest_rendered_package_review_proof_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered package-review proof as test-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_package_review_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_package_review_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered package-review proof must be test-only")
    if proof.get("selected_rendered_package_review_mode") != "raw_mixed_rendered_package_review_preview_commit_submit":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered package-review proof has stale selected mode")
    routes = proof.get("routes_reused")
    if not isinstance(routes, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered package-review proof missing routes_reused")
    else:
        for route in (
            "POST /api/v1/layer3/package/review/preview",
            "POST /api/v1/layer3/package/review/commit",
            "POST /api/v1/layer3/package/review/submit",
        ):
            if route not in routes:
                errors.append(f"{_rel(PROOF_MANIFEST)} rendered package-review routes_reused missing {route}")
    browser_proof = proof.get("browser_proof")
    if not isinstance(browser_proof, list) or "Layer 3 workbench drives raw mixed rendered package-review preview commit and submit" not in browser_proof:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered package-review proof missing browser proof test name")


def _check_rendered_handoff_export_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_HANDOFF_EXPORT_FREEZE: (
            "Status: planning/control freeze only for `raw_mixed_rendered_handoff_export_prepare`.",
            "POST /api/v1/layer3/handoff/export/prepare",
            "Layer3HandoffExportPrepareRequest",
            "Layer3HandoffExportPrepareResponse",
            "#handoff-export-prepare-submit",
            "[data-operation-target=\"handoff-export-band\"]",
            "Current rendered workbench behavior may enable `#aps-handoff-dispatch-submit`",
            "no frontend-only durable authority",
        ),
        RENDERED_HANDOFF_EXPORT_CONTRACT: (
            "Selected mode: `raw_mixed_rendered_handoff_export_prepare`.",
            "POST /api/v1/layer3/handoff/export/prepare",
            "Layer3HandoffExportPrepareRequest",
            "Layer3HandoffExportPrepareResponse",
            "operator_decision",
            "expected_package_kinds",
            "#handoff-export-prepare-panel",
            "The operation-dock tab for `handoff-export-band` is a workbench-mode rendered control",
        ),
        BOARD: (
            "Rendered handoff/export prepare proof",
            "169_RENDERED_HANDOFF_EXPORT_FREEZE.md",
            "170_RENDERED_HANDOFF_EXPORT_CONTRACT.md",
            "raw_mixed_rendered_handoff_export_prepare",
        ),
        MANIFEST: (
            "latest_rendered_handoff_export_freeze_branch",
            "latest_rendered_handoff_export_freeze_live_behavior_change",
            "rendered_handoff_export_freeze",
            "raw_mixed_rendered_handoff_export_prepare",
        ),
        PROOF_MANIFEST: (
            "rendered_handoff_export_freeze_proof",
            "169_RENDERED_HANDOFF_EXPORT_FREEZE.md",
            "170_RENDERED_HANDOFF_EXPORT_CONTRACT.md",
            "raw_mixed_rendered_handoff_export_prepare",
            "#handoff-export-prepare-submit",
            "no frontend-only durable authority",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing rendered handoff/export freeze term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_handoff_export_freeze_branch") != "codex/l3-rendered-handoff-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered handoff/export freeze branch")
        if current_status.get("latest_rendered_handoff_export_freeze_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered handoff/export freeze as planning-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_handoff_export_freeze_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_handoff_export_freeze_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered handoff/export freeze proof must be planning-only")
    if proof.get("selected_rendered_handoff_mode") != "raw_mixed_rendered_handoff_export_prepare":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered handoff/export freeze proof has stale selected mode")
    routes = proof.get("routes_to_reuse")
    if not isinstance(routes, list) or "POST /api/v1/layer3/handoff/export/prepare" not in routes:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered handoff/export freeze proof missing route to reuse")
    selectors = proof.get("future_selectors")
    if not isinstance(selectors, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered handoff/export freeze proof missing future_selectors")
    else:
        for selector in (
            "[data-operation-target=\"handoff-export-band\"]",
            "#handoff-export-prepare-submit",
            "#handoff-export-prepare-panel",
        ):
            if selector not in selectors:
                errors.append(f"{_rel(PROOF_MANIFEST)} rendered handoff/export future_selectors missing {selector}")


def _check_rendered_handoff_export_proof(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_HANDOFF_EXPORT_PROOF: (
            "Status: live test-only rendered browser proof for `raw_mixed_rendered_handoff_export_prepare`.",
            "Layer 3 workbench drives raw mixed rendered handoff export prepare",
            "submitRenderedHandoffExportPrepare",
            "POST /api/v1/layer3/handoff/export/prepare",
            "layer3.cohort_handoff_export_prepare.v1",
            "handoff_export_prepared",
            "server-returned `prepare_record_ref`",
            "server-returned `handoff_export_envelope`",
            "`#aps-handoff-dispatch-submit` as enabled",
            "no `/handoff/aps/dispatch` request is made",
            "no frontend-only durable authority",
        ),
        BOARD: (
            "Rendered handoff/export prepare proof",
            "171_RENDERED_HANDOFF_EXPORT_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered handoff export prepare",
            "raw_mixed_rendered_handoff_export_prepare",
            "handoff_export_prepared",
        ),
        MANIFEST: (
            "latest_rendered_handoff_export_proof_branch",
            "latest_rendered_handoff_export_proof_live_behavior_change",
            "rendered_handoff_export_proof",
            "171_RENDERED_HANDOFF_EXPORT_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered handoff export prepare",
        ),
        PROOF_MANIFEST: (
            "rendered_handoff_export_proof",
            "171_RENDERED_HANDOFF_EXPORT_PROOF.md",
            "raw_mixed_rendered_handoff_export_prepare",
            "submitRenderedHandoffExportPrepare",
            "Layer 3 workbench drives raw mixed rendered handoff export prepare",
            "readiness_nuance",
            "no frontend-only durable authority",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench drives raw mixed rendered handoff export prepare",
            "submitRenderedHandoffExportPrepare",
            "expect(preparePayload.handoff_target).toBe('internal_export_envelope')",
            "expect(preparePayload.export_mode).toBe('prepare_only')",
            "expect(handoffPrepare.handoff_export_state).toBe('handoff_export_prepared')",
            "expect(page.locator('#aps-handoff-dispatch-submit')).toBeEnabled()",
            "/handoff/aps/dispatch",
            "/handoff/export/download",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing rendered handoff/export proof term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_handoff_export_proof_branch") != "codex/l3-rendered-handoff-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered handoff/export proof branch")
        if current_status.get("latest_rendered_handoff_export_proof_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered handoff/export proof as test-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_handoff_export_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_handoff_export_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered handoff/export proof must be test-only")
    if proof.get("selected_rendered_handoff_mode") != "raw_mixed_rendered_handoff_export_prepare":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered handoff/export proof has stale selected mode")
    routes = proof.get("routes_reused")
    if not isinstance(routes, list) or "POST /api/v1/layer3/handoff/export/prepare" not in routes:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered handoff/export proof missing route reused")
    browser_proof = proof.get("browser_proof")
    if not isinstance(browser_proof, list) or "Layer 3 workbench drives raw mixed rendered handoff export prepare" not in browser_proof:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered handoff/export proof missing browser proof test name")


def _check_rendered_aps_handoff_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_APS_HANDOFF_FREEZE: (
            "Status: planning/control freeze only for `raw_mixed_rendered_aps_handoff_dispatch`.",
            "POST /api/v1/layer3/handoff/aps/dispatch",
            "Layer3ApsHandoffDispatchRequest",
            "Layer3ApsHandoffDispatchResponse",
            "#aps-handoff-dispatch-submit",
            "[data-operation-target=\"aps-handoff-band\"]",
            "Current rendered workbench behavior may enable `#external-export-download-prepare-submit`",
            "no frontend-only durable authority",
        ),
        RENDERED_APS_HANDOFF_CONTRACT: (
            "Selected mode: `raw_mixed_rendered_aps_handoff_dispatch`.",
            "POST /api/v1/layer3/handoff/aps/dispatch",
            "Layer3ApsHandoffDispatchRequest",
            "Layer3ApsHandoffDispatchResponse",
            "operator_decision",
            "server_side_aps_handoff",
            "#aps-handoff-dispatch-panel",
            "The future browser proof must",
        ),
        BOARD: (
            "Rendered APS handoff dispatch proof",
            "172_RENDERED_APS_HANDOFF_FREEZE.md",
            "173_RENDERED_APS_HANDOFF_CONTRACT.md",
            "raw_mixed_rendered_aps_handoff_dispatch",
        ),
        MANIFEST: (
            "latest_rendered_aps_handoff_freeze_branch",
            "latest_rendered_aps_handoff_freeze_live_behavior_change",
            "rendered_aps_handoff_freeze",
            "raw_mixed_rendered_aps_handoff_dispatch",
        ),
        PROOF_MANIFEST: (
            "rendered_aps_handoff_freeze_proof",
            "172_RENDERED_APS_HANDOFF_FREEZE.md",
            "173_RENDERED_APS_HANDOFF_CONTRACT.md",
            "raw_mixed_rendered_aps_handoff_dispatch",
            "#aps-handoff-dispatch-submit",
            "no frontend-only durable authority",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing rendered APS handoff freeze term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_aps_handoff_freeze_branch") != "codex/l3-rendered-aps-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered APS handoff freeze branch")
        if current_status.get("latest_rendered_aps_handoff_freeze_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered APS handoff freeze as planning-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_aps_handoff_freeze_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_aps_handoff_freeze_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered APS handoff freeze proof must be planning-only")
    if proof.get("selected_rendered_aps_handoff_mode") != "raw_mixed_rendered_aps_handoff_dispatch":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered APS handoff freeze proof has stale selected mode")
    routes = proof.get("routes_to_reuse")
    if not isinstance(routes, list) or "POST /api/v1/layer3/handoff/aps/dispatch" not in routes:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered APS handoff freeze proof missing route to reuse")
    selectors = proof.get("future_selectors")
    if not isinstance(selectors, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered APS handoff freeze proof missing future_selectors")
    else:
        for selector in (
            "[data-operation-target=\"aps-handoff-band\"]",
            "#aps-handoff-dispatch-submit",
            "#aps-handoff-dispatch-panel",
        ):
            if selector not in selectors:
                errors.append(f"{_rel(PROOF_MANIFEST)} rendered APS handoff future_selectors missing {selector}")


def _check_rendered_aps_handoff_proof(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_APS_HANDOFF_PROOF: (
            "Status: live test-only rendered browser proof for `raw_mixed_rendered_aps_handoff_dispatch`.",
            "Layer 3 workbench drives raw mixed rendered APS handoff dispatch",
            "submitRenderedApsHandoffDispatch",
            "POST /api/v1/layer3/handoff/aps/dispatch",
            "layer3.aps_handoff_dispatch.v1",
            "aps_handoff_dispatched",
            "server-returned `aps_handoff_record_ref`",
            "server-returned `aps_bundle_ref`",
            "`#external-export-download-prepare-submit` as enabled",
            "no `/handoff/export/download` request is made",
            "no frontend-only durable authority",
        ),
        BOARD: (
            "Rendered APS handoff dispatch proof",
            "174_RENDERED_APS_HANDOFF_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered APS handoff dispatch",
            "raw_mixed_rendered_aps_handoff_dispatch",
            "aps_handoff_dispatched",
        ),
        MANIFEST: (
            "latest_rendered_aps_handoff_proof_branch",
            "latest_rendered_aps_handoff_proof_live_behavior_change",
            "rendered_aps_handoff_proof",
            "174_RENDERED_APS_HANDOFF_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered APS handoff dispatch",
        ),
        PROOF_MANIFEST: (
            "rendered_aps_handoff_proof",
            "174_RENDERED_APS_HANDOFF_PROOF.md",
            "raw_mixed_rendered_aps_handoff_dispatch",
            "submitRenderedApsHandoffDispatch",
            "Layer 3 workbench drives raw mixed rendered APS handoff dispatch",
            "readiness_nuance",
            "no frontend-only durable authority",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench drives raw mixed rendered APS handoff dispatch",
            "submitRenderedApsHandoffDispatch",
            "expect(dispatchPayload.aps_handoff_target).toBe('aps_evidence_bundle')",
            "expect(dispatchPayload.dispatch_mode).toBe('server_side_aps_handoff')",
            "expect(apsDispatch.aps_handoff_state).toBe('aps_handoff_dispatched')",
            "expect(page.locator('#external-export-download-prepare-submit')).toBeEnabled()",
            "/handoff/aps/dispatch",
            "/handoff/export/download",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing rendered APS handoff proof term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_aps_handoff_proof_branch") != "codex/l3-rendered-aps-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered APS handoff proof branch")
        if current_status.get("latest_rendered_aps_handoff_proof_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered APS handoff proof as test-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_aps_handoff_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_aps_handoff_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered APS handoff proof must be test-only")
    if proof.get("selected_rendered_aps_handoff_mode") != "raw_mixed_rendered_aps_handoff_dispatch":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered APS handoff proof has stale selected mode")
    routes = proof.get("routes_reused")
    if not isinstance(routes, list) or "POST /api/v1/layer3/handoff/aps/dispatch" not in routes:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered APS handoff proof missing route reused")
    browser_proof = proof.get("browser_proof")
    if not isinstance(browser_proof, list) or "Layer 3 workbench drives raw mixed rendered APS handoff dispatch" not in browser_proof:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered APS handoff proof missing browser proof test name")


def _check_rendered_external_export_download_prepare_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FREEZE: (
            "Status: planning/control freeze only for `raw_mixed_rendered_external_export_download_prepare`.",
            "POST /api/v1/layer3/handoff/export/download/prepare",
            "Layer3ExternalExportDownloadPrepareRequest",
            "Layer3ExternalExportDownloadPrepareResponse",
            "#external-export-download-prepare-submit",
            "[data-operation-target=\"external-export-download-band\"]",
            "Current rendered workbench behavior may enable `#external-export-download-delivery-submit`",
            "no frontend-only durable authority",
        ),
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_CONTRACT: (
            "Selected mode: `raw_mixed_rendered_external_export_download_prepare`.",
            "POST /api/v1/layer3/handoff/export/download/prepare",
            "Layer3ExternalExportDownloadPrepareRequest",
            "Layer3ExternalExportDownloadPrepareResponse",
            "aps_evidence_bundle_download_reference",
            "reference_only_prepare",
            "prepare_external_export_download",
            "The future browser proof must",
        ),
        BOARD: (
            "Rendered external export/download prepare proof",
            "175_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FREEZE.md",
            "176_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_CONTRACT.md",
            "raw_mixed_rendered_external_export_download_prepare",
        ),
        MANIFEST: (
            "latest_rendered_external_export_download_prepare_freeze_branch",
            "latest_rendered_external_export_download_prepare_freeze_live_behavior_change",
            "rendered_external_export_download_prepare_freeze",
            "raw_mixed_rendered_external_export_download_prepare",
        ),
        PROOF_MANIFEST: (
            "rendered_external_export_download_prepare_freeze_proof",
            "175_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FREEZE.md",
            "176_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_CONTRACT.md",
            "raw_mixed_rendered_external_export_download_prepare",
            "#external-export-download-prepare-submit",
            "no frontend-only durable authority",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing rendered external export/download prepare freeze term: {term}"
                )

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_external_export_download_prepare_freeze_branch") != "codex/l3-rendered-download-prepare-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered external export/download prepare freeze branch")
        if current_status.get("latest_rendered_external_export_download_prepare_freeze_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered external export/download prepare freeze as planning-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_external_export_download_prepare_freeze_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_external_export_download_prepare_freeze_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download prepare freeze proof must be planning-only")
    if proof.get("selected_rendered_external_export_download_mode") != "raw_mixed_rendered_external_export_download_prepare":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download prepare freeze proof has stale selected mode")
    routes = proof.get("routes_to_reuse")
    if not isinstance(routes, list) or "POST /api/v1/layer3/handoff/export/download/prepare" not in routes:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download prepare freeze proof missing route to reuse")
    selectors = proof.get("future_selectors")
    if not isinstance(selectors, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download prepare freeze proof missing future_selectors")
    else:
        for selector in (
            "[data-operation-target=\"external-export-download-band\"]",
            "#external-export-download-prepare-submit",
            "#external-export-download-prepare-panel",
        ):
            if selector not in selectors:
                errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download prepare future_selectors missing {selector}")


def _check_rendered_external_export_download_prepare_proof(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PROOF: (
            "Status: live test-only rendered browser proof for `raw_mixed_rendered_external_export_download_prepare`.",
            "Layer 3 workbench drives raw mixed rendered external export download prepare",
            "submitRenderedExternalExportDownloadPrepare",
            "POST /api/v1/layer3/handoff/export/download/prepare",
            "layer3.external_export_download_prepare.v1",
            "external_export_download_prepared",
            "server-returned `external_export_download_record_ref`",
            "server-returned `export_download_descriptor_ref`",
            "`#external-export-download-delivery-submit` as enabled",
            "no `/handoff/export/download/deliver` or `/handoff/export/download/signed-reference` request is made",
            "no frontend-only durable authority",
        ),
        BOARD: (
            "Rendered external export/download prepare proof",
            "177_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered external export download prepare",
            "raw_mixed_rendered_external_export_download_prepare",
            "external_export_download_prepared",
        ),
        MANIFEST: (
            "latest_rendered_external_export_download_prepare_proof_branch",
            "latest_rendered_external_export_download_prepare_proof_live_behavior_change",
            "rendered_external_export_download_prepare_proof",
            "177_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered external export download prepare",
        ),
        PROOF_MANIFEST: (
            "rendered_external_export_download_prepare_proof",
            "177_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PROOF.md",
            "raw_mixed_rendered_external_export_download_prepare",
            "submitRenderedExternalExportDownloadPrepare",
            "Layer 3 workbench drives raw mixed rendered external export download prepare",
            "readiness_nuance",
            "no frontend-only durable authority",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench drives raw mixed rendered external export download prepare",
            "submitRenderedExternalExportDownloadPrepare",
            "expect(preparePayload.export_download_target).toBe('aps_evidence_bundle_download_reference')",
            "expect(preparePayload.download_mode).toBe('reference_only_prepare')",
            "expect(downloadPrepare.external_export_download_state).toBe('external_export_download_prepared')",
            "expect(page.locator('#external-export-download-delivery-submit')).toBeEnabled()",
            "/handoff/export/download/prepare",
            "/handoff/export/download/deliver",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing rendered external export/download prepare proof term: {term}"
                )

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_external_export_download_prepare_proof_branch") != "codex/l3-rendered-download-prepare-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered external export/download prepare proof branch")
        if current_status.get("latest_rendered_external_export_download_prepare_proof_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered external export/download prepare proof as test-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_external_export_download_prepare_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_external_export_download_prepare_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download prepare proof must be test-only")
    if proof.get("selected_rendered_external_export_download_mode") != "raw_mixed_rendered_external_export_download_prepare":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download prepare proof has stale selected mode")
    routes = proof.get("routes_reused")
    if not isinstance(routes, list) or "POST /api/v1/layer3/handoff/export/download/prepare" not in routes:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download prepare proof missing route reused")
    browser_proof = proof.get("browser_proof")
    if not isinstance(browser_proof, list) or "Layer 3 workbench drives raw mixed rendered external export download prepare" not in browser_proof:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download prepare proof missing browser proof test name")


def _check_rendered_external_export_download_delivery_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE: (
            "Status: planning/control freeze only for `raw_mixed_rendered_external_export_download_delivery`.",
            "POST /api/v1/layer3/handoff/export/download/deliver",
            "Layer3ExternalExportDownloadDeliveryRequest",
            "layer3.external_export_download_delivery.v1",
            "#external-export-download-delivery-submit",
            "[data-operation-target=\"external-export-download-band\"]",
            "Current rendered workbench behavior may enable same-origin signed-reference controls",
            "no frontend-only durable authority",
        ),
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT: (
            "Selected mode: `raw_mixed_rendered_external_export_download_delivery`.",
            "POST /api/v1/layer3/handoff/export/download/deliver",
            "Layer3ExternalExportDownloadDeliveryRequest",
            "layer3.external_export_download_delivery.v1",
            "same_origin_artifact_stream",
            "deliver_external_export_download",
            "external_export_download_prepared",
            "The future browser proof must",
        ),
        BOARD: (
            "Rendered external export/download delivery proof",
            "178_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md",
            "179_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT.md",
            "raw_mixed_rendered_external_export_download_delivery",
        ),
        MANIFEST: (
            "latest_rendered_external_export_download_delivery_freeze_branch",
            "latest_rendered_external_export_download_delivery_freeze_live_behavior_change",
            "rendered_external_export_download_delivery_freeze",
            "raw_mixed_rendered_external_export_download_delivery",
        ),
        PROOF_MANIFEST: (
            "rendered_external_export_download_delivery_freeze_proof",
            "178_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md",
            "179_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT.md",
            "raw_mixed_rendered_external_export_download_delivery",
            "#external-export-download-delivery-submit",
            "no frontend-only durable authority",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing rendered external export/download delivery freeze term: {term}"
                )

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_external_export_download_delivery_freeze_branch") != "codex/l3-rendered-download-delivery-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered external export/download delivery freeze branch")
        if current_status.get("latest_rendered_external_export_download_delivery_freeze_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered external export/download delivery freeze as planning-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_external_export_download_delivery_freeze_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_external_export_download_delivery_freeze_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download delivery freeze proof must be planning-only")
    if proof.get("selected_rendered_external_export_download_mode") != "raw_mixed_rendered_external_export_download_delivery":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download delivery freeze proof has stale selected mode")
    routes = proof.get("routes_to_reuse")
    if not isinstance(routes, list) or "POST /api/v1/layer3/handoff/export/download/deliver" not in routes:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download delivery freeze proof missing route to reuse")
    selectors = proof.get("future_selectors")
    if not isinstance(selectors, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download delivery freeze proof missing future_selectors")
    else:
        for selector in (
            "[data-operation-target=\"external-export-download-band\"]",
            "#external-export-download-delivery-submit",
            "#external-export-download-delivery-panel",
        ):
            if selector not in selectors:
                errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download delivery future_selectors missing {selector}")


def _check_rendered_external_export_download_delivery_proof(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PROOF: (
            "Status: live test-only rendered browser proof for `raw_mixed_rendered_external_export_download_delivery`.",
            "Layer 3 workbench drives raw mixed rendered external export download delivery",
            "submitRenderedExternalExportDownloadDelivery",
            "POST /api/v1/layer3/handoff/export/download/deliver",
            "layer3.external_export_download_delivery.v1",
            "external_export_download_delivered",
            "x-layer3-delivery-state",
            "x-layer3-source-artifact-hash",
            "no `/handoff/export/download/signed-reference`",
            "no frontend-only durable authority",
        ),
        BOARD: (
            "Rendered external export/download delivery proof",
            "180_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered external export download delivery",
            "raw_mixed_rendered_external_export_download_delivery",
            "external_export_download_delivered",
        ),
        MANIFEST: (
            "latest_rendered_external_export_download_delivery_proof_branch",
            "latest_rendered_external_export_download_delivery_proof_live_behavior_change",
            "rendered_external_export_download_delivery_proof",
            "180_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered external export download delivery",
        ),
        PROOF_MANIFEST: (
            "rendered_external_export_download_delivery_proof",
            "180_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PROOF.md",
            "raw_mixed_rendered_external_export_download_delivery",
            "submitRenderedExternalExportDownloadDelivery",
            "Layer 3 workbench drives raw mixed rendered external export download delivery",
            "readiness_nuance",
            "no frontend-only durable authority",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench drives raw mixed rendered external export download delivery",
            "submitRenderedExternalExportDownloadDelivery",
            "expect(deliveryPayload.operator_decision).toBe('deliver_external_export_download')",
            "expect(deliveryPayload.delivery_mode).toBe('same_origin_artifact_stream')",
            "expect(headers['x-layer3-delivery-state']).toBe('external_export_download_delivered')",
            "expect(headers['x-layer3-source-artifact-hash']).toBe(downloadPrepare.source_artifact_hash)",
            "/handoff/export/download/deliver",
            "/handoff/export/download/signed-reference",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing rendered external export/download delivery proof term: {term}"
                )

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_external_export_download_delivery_proof_branch") != "codex/l3-rendered-download-delivery-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered external export/download delivery proof branch")
        if current_status.get("latest_rendered_external_export_download_delivery_proof_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered external export/download delivery proof as test-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_external_export_download_delivery_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_external_export_download_delivery_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download delivery proof must be test-only")
    if proof.get("selected_rendered_external_export_download_mode") != "raw_mixed_rendered_external_export_download_delivery":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download delivery proof has stale selected mode")
    routes = proof.get("routes_reused")
    if not isinstance(routes, list) or "POST /api/v1/layer3/handoff/export/download/deliver" not in routes:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download delivery proof missing route reused")
    browser_proof = proof.get("browser_proof")
    if not isinstance(browser_proof, list) or "Layer 3 workbench drives raw mixed rendered external export download delivery" not in browser_proof:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download delivery proof missing browser proof test name")


def _check_rendered_external_export_download_signed_reference_freeze(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_FREEZE: (
            "Status: planning/control freeze only for `raw_mixed_rendered_external_export_download_signed_reference`.",
            "POST /api/v1/layer3/handoff/export/download/signed-reference/generate",
            "POST /api/v1/layer3/handoff/export/download/signed-reference/use",
            "Layer3ExternalExportDownloadDeliveryRequest",
            "layer3.external_export_download_signed_reference.v1",
            "layer3.external_export_download_signed_reference_use.v1",
            "#external-export-download-signed-reference-generate",
            "#external-export-download-signed-reference-use",
            "[data-operation-target=\"external-export-download-band\"]",
            "no frontend-only durable authority",
        ),
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_CONTRACT: (
            "Selected mode: `raw_mixed_rendered_external_export_download_signed_reference`.",
            "POST /api/v1/layer3/handoff/export/download/signed-reference/generate",
            "POST /api/v1/layer3/handoff/export/download/signed-reference/use",
            "Layer3ExternalExportDownloadDeliveryRequest",
            "layer3.external_export_download_signed_reference.v1",
            "layer3.external_export_download_signed_reference_use.v1",
            "server_hmac_with_durable_state",
            "single_use",
            "The future browser proof must",
        ),
        BOARD: (
            "Rendered external export/download signed-reference proof",
            "181_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_FREEZE.md",
            "182_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_CONTRACT.md",
            "raw_mixed_rendered_external_export_download_signed_reference",
        ),
        MANIFEST: (
            "latest_rendered_external_export_download_signed_reference_freeze_branch",
            "latest_rendered_external_export_download_signed_reference_freeze_live_behavior_change",
            "rendered_external_export_download_signed_reference_freeze",
            "raw_mixed_rendered_external_export_download_signed_reference",
        ),
        PROOF_MANIFEST: (
            "rendered_external_export_download_signed_reference_freeze_proof",
            "181_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_FREEZE.md",
            "182_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_CONTRACT.md",
            "raw_mixed_rendered_external_export_download_signed_reference",
            "#external-export-download-signed-reference-generate",
            "#external-export-download-signed-reference-use",
            "no frontend-only durable authority",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing rendered external export/download signed-reference freeze term: {term}"
                )

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_external_export_download_signed_reference_freeze_branch") != "codex/l3-rendered-signed-reference-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered external export/download signed-reference freeze branch")
        if current_status.get("latest_rendered_external_export_download_signed_reference_freeze_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered external export/download signed-reference freeze as planning-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_external_export_download_signed_reference_freeze_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_external_export_download_signed_reference_freeze_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download signed-reference freeze proof must be planning-only")
    if proof.get("selected_rendered_external_export_download_mode") != "raw_mixed_rendered_external_export_download_signed_reference":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download signed-reference freeze proof has stale selected mode")
    routes = proof.get("routes_to_reuse")
    expected_routes = {
        "POST /api/v1/layer3/handoff/export/download/signed-reference/generate",
        "POST /api/v1/layer3/handoff/export/download/signed-reference/use",
    }
    if not isinstance(routes, list) or not expected_routes.issubset(set(routes)):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download signed-reference freeze proof missing routes to reuse")
    selectors = proof.get("future_selectors")
    if not isinstance(selectors, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download signed-reference freeze proof missing future_selectors")
    else:
        for selector in (
            "[data-operation-target=\"external-export-download-band\"]",
            "#external-export-download-signed-reference-generate",
            "#external-export-download-signed-reference-use",
            "#external-export-download-signed-reference-panel",
        ):
            if selector not in selectors:
                errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download signed-reference future_selectors missing {selector}")


def _check_rendered_external_export_download_signed_reference_proof(errors: list[str]) -> None:
    required_doc_terms = {
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF: (
            "Status: live rendered browser proof for `raw_mixed_rendered_external_export_download_signed_reference`.",
            "Layer 3 workbench drives raw mixed rendered external export download signed reference",
            "submitRenderedExternalExportDownloadSignedReference",
            "POST /api/v1/layer3/handoff/export/download/signed-reference/generate",
            "POST /api/v1/layer3/handoff/export/download/signed-reference/use",
            "layer3.external_export_download_signed_reference.v1",
            "layer3.external_export_download_signed_reference_use.v1",
            "external_export_download_signed_reference_ready",
            "external_export_download_signed_reference_delivered",
            "server_hmac_with_durable_state",
            "single_use",
            "canUseExternalExportDownloadSignedReference()",
            "no frontend-only durable authority",
        ),
        BOARD: (
            "Rendered external export/download signed-reference proof",
            "183_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered external export download signed reference",
            "raw_mixed_rendered_external_export_download_signed_reference",
            "external_export_download_signed_reference_delivered",
        ),
        MANIFEST: (
            "latest_rendered_external_export_download_signed_reference_proof_branch",
            "latest_rendered_external_export_download_signed_reference_proof_live_behavior_change",
            "rendered_external_export_download_signed_reference_proof",
            "183_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF.md",
            "Layer 3 workbench drives raw mixed rendered external export download signed reference",
        ),
        PROOF_MANIFEST: (
            "rendered_external_export_download_signed_reference_proof",
            "183_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF.md",
            "raw_mixed_rendered_external_export_download_signed_reference",
            "submitRenderedExternalExportDownloadSignedReference",
            "Layer 3 workbench drives raw mixed rendered external export download signed reference",
            "ui_hardening",
            "test_harness_env",
            "no frontend-only durable authority",
        ),
        LAYER3_WORKBENCH_E2E: (
            "Layer 3 workbench drives raw mixed rendered external export download signed reference",
            "submitRenderedExternalExportDownloadSignedReference",
            "expect(signedPayload.operator_decision).toBe('deliver_external_export_download')",
            "expect(signedPayload.delivery_mode).toBe('same_origin_artifact_stream')",
            "expect(signedReference.signed_reference_state).toBe('external_export_download_signed_reference_ready')",
            "expect(useHeaders['x-layer3-signed-reference-state']).toBe(",
            "external_export_download_signed_reference_delivered",
            "/handoff/export/download/signed-reference/generate",
            "/handoff/export/download/signed-reference/use",
            "/handoff/export/download/deliver",
        ),
        LAYER3_JS: (
            "function canUseExternalExportDownloadSignedReference()",
            "&& !State.externalExportDownloadSignedReferenceUse",
            "external-export-download-signed-reference-use",
        ),
        PLAYWRIGHT_CONFIG: (
            "LAYER3_SIGNED_REFERENCE_SECRET",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(
                    f"{_rel(path)} missing rendered external export/download signed-reference proof term: {term}"
                )

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_rendered_external_export_download_signed_reference_proof_branch") != "codex/l3-rendered-signed-reference-proof":
            errors.append(f"{_rel(MANIFEST)} current_status has stale rendered external export/download signed-reference proof branch")
        if current_status.get("latest_rendered_external_export_download_signed_reference_proof_live_behavior_change") is not True:
            errors.append(f"{_rel(MANIFEST)} current_status must mark rendered external export/download signed-reference proof as a narrow rendered UI behavior hardening")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("rendered_external_export_download_signed_reference_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing rendered_external_export_download_signed_reference_proof object")
        return
    if proof.get("live_behavior_change") is not True:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download signed-reference proof must record the narrow rendered UI behavior hardening")
    if proof.get("selected_rendered_external_export_download_mode") != "raw_mixed_rendered_external_export_download_signed_reference":
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download signed-reference proof has stale selected mode")
    routes = proof.get("routes_reused")
    expected_routes = {
        "POST /api/v1/layer3/handoff/export/download/signed-reference/generate",
        "POST /api/v1/layer3/handoff/export/download/signed-reference/use",
    }
    if not isinstance(routes, list) or not expected_routes.issubset(set(routes)):
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download signed-reference proof missing routes reused")
    browser_proof = proof.get("browser_proof")
    if not isinstance(browser_proof, list) or "Layer 3 workbench drives raw mixed rendered external export download signed reference" not in browser_proof:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download signed-reference proof missing browser proof test name")
    ui_hardening = proof.get("ui_hardening")
    if not isinstance(ui_hardening, str) or "State.externalExportDownloadSignedReferenceUse" not in ui_hardening:
        errors.append(f"{_rel(PROOF_MANIFEST)} rendered external export/download signed-reference proof missing UI hardening summary")


def _check_post_745_downstream_expansion_freeze(errors: list[str]) -> None:
    required_terms = {
        POST_745_DOWNSTREAM_EXPANSION_FREEZE: (
            "Status: planning/control freeze only for `post_745_raw_mixed_rendered_downstream_expansion_governance`.",
            "183_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF.md",
            "provider_public_url_entry_freeze",
            "connector_destination_dispatch_entry_freeze",
            "package_mutation_reconstruction_rendered_entry_freeze",
            "source_breadth_entry_freeze",
            "qual_hybrid_rag_vector_entry_freeze",
            "browser_full_mockup_activation_freeze",
            "auth_security_entry_freeze",
            "exact light, dark, and workbench theme obligations",
            "No future implementation may start from this freeze alone.",
            "no frontend-only durable authority",
        ),
        POST_745_DOWNSTREAM_EXPANSION_CONTRACT: (
            "Selected mode: `post_745_raw_mixed_rendered_downstream_expansion_governance`.",
            "Provider/Public URL Entry Contract",
            "Connector/Destination Dispatch Entry Contract",
            "Package Mutation/Reconstruction Entry Contract",
            "Source Breadth Entry Contract",
            "Qualitative/Hybrid/RAG/Vector Entry Contract",
            "UI Theme Contract",
            "headed and headless Chromium behavior is consistent",
            "no provider/public URL behavior",
            "no connector/destination dispatch",
            "no frontend-only durable authority",
        ),
        BOARD: (
            "Post-745 downstream expansion freeze",
            "184_POST_745_DOWNSTREAM_EXPANSION_FREEZE.md",
            "185_POST_745_DOWNSTREAM_EXPANSION_CONTRACT.md",
            "post_745_raw_mixed_rendered_downstream_expansion_governance",
        ),
        MANIFEST: (
            "latest_post_745_downstream_expansion_freeze_branch",
            "latest_post_745_downstream_expansion_freeze_live_behavior_change",
            "post_745_downstream_expansion_freeze",
            "post_745_raw_mixed_rendered_downstream_expansion_governance",
        ),
        PROOF_MANIFEST: (
            "post_745_downstream_expansion_freeze_proof",
            "184_POST_745_DOWNSTREAM_EXPANSION_FREEZE.md",
            "185_POST_745_DOWNSTREAM_EXPANSION_CONTRACT.md",
            "post_745_raw_mixed_rendered_downstream_expansion_governance",
            "provider_public_url_entry_freeze",
            "connector_destination_dispatch_entry_freeze",
            "no frontend-only durable authority",
        ),
    }
    for path, terms in required_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing post-745 downstream expansion freeze term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if isinstance(current_status, dict):
        if current_status.get("latest_post_745_downstream_expansion_freeze_branch") != "codex/l3-post-745-next":
            errors.append(f"{_rel(MANIFEST)} current_status has stale post-745 downstream expansion freeze branch")
        if current_status.get("latest_post_745_downstream_expansion_freeze_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark post-745 downstream expansion freeze as planning-only")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("post_745_downstream_expansion_freeze_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing post_745_downstream_expansion_freeze_proof object")
        return
    if proof.get("live_behavior_change") is not False:
        errors.append(f"{_rel(PROOF_MANIFEST)} post-745 downstream expansion freeze proof must be planning-only")
    if proof.get("selected_planning_mode") != "post_745_raw_mixed_rendered_downstream_expansion_governance":
        errors.append(f"{_rel(PROOF_MANIFEST)} post-745 downstream expansion freeze proof has stale selected planning mode")
    expected_ranked_future_passes = [
        "provider_public_url_entry_freeze",
        "connector_destination_dispatch_entry_freeze",
        "package_mutation_reconstruction_rendered_entry_freeze",
        "source_breadth_entry_freeze",
        "qual_hybrid_rag_vector_entry_freeze",
        "browser_full_mockup_activation_freeze",
        "auth_security_entry_freeze",
    ]
    ranked = proof.get("ranked_future_passes")
    if not isinstance(ranked, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} post-745 downstream expansion freeze proof missing ranked_future_passes")
    elif ranked != expected_ranked_future_passes:
        errors.append(f"{_rel(PROOF_MANIFEST)} post-745 ranked_future_passes must match the frozen future-pass order")
    expected_negative_invariants = [
        "no provider/public URL behavior",
        "no provider object-store URL, signed URL, public ACL, object-store write, or URL revocation behavior",
        "no connector-run creation, connector invocation, destination selection, destination write, or generic downstream dispatch",
        "no package payload mutation, reconstruction, replacement, supersession, or rendered package mutation control",
        "no source-family expansion beyond dataset_version and aps_content_document",
        "no source adapter registry",
        "no local upload, local-directory ingestion, arbitrary local path input, web connector retrieval, or unbounded runtime DB source read",
        "no RAG/vector retrieval, vector index creation, broad qualitative execution, hybrid execution, or hidden LLM planning",
        "no new route, DTO, model, migration, or production service behavior",
        "no new rendered UI control",
        "no frontend-only durable authority",
        "no full mockup activation",
        "no auth/security behavior change",
    ]
    negative_invariants = proof.get("negative_invariants")
    if not isinstance(negative_invariants, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} post-745 downstream expansion freeze proof missing negative_invariants")
    elif negative_invariants != expected_negative_invariants:
        errors.append(f"{_rel(PROOF_MANIFEST)} post-745 negative_invariants must match the frozen structural list")



def _check_provider_public_url_entry_freeze(errors: list[str]) -> None:
    required_terms = {
        PROVIDER_PUBLIC_URL_ENTRY_FREEZE: (
            "Status: planning/control entry freeze only for `provider_public_url_entry_freeze`.",
            "entry_decision: deferred",
            "selected_mode: null",
            "runtime_status: not_implemented",
            "provider_storage_authority_named_use_case_exposure_model_revocation_contract_and_security_posture_not_yet_verified",
            "provider_public_url_authority_discovery_freeze_or_entry_freeze_update",
            "Evidence Ledger",
            "Threat Model Minimum",
            "Exposure Model",
            "Capability Isolation Matrix",
            "no_cross_mode_privilege_escalation",
            "Provider/public URL admission, if later selected, is a URL exposure mode over already-authorized server-owned artifacts",
            "signed_reference_semantics_change_allowed: false",
            "provider_credentials_in_browser: forbidden",
            "runtime_header_behavior_admitted: false",
            "receipt_family: no_receipt_planning_only",
            "real_provider_credentials_in_ci: forbidden_by_default",
            "post_748_checkpoint",
            "no provider/public URL runtime",
            "no provider object write or copy",
            "no auth/security behavior change",
        ),
        PROVIDER_PUBLIC_URL_ENTRY_CONTRACT: (
            "Status: planning/control contract paired with `187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md`.",
            "entry_decision: deferred",
            "selected_mode: null",
            "runtime_status: not_implemented",
            "provider_private_signed_url",
            "provider_public_url",
            "public_proxy_url",
            "A same-origin signed reference must not be renamed or represented as a provider/public URL.",
            "Provider/public URL work is not provider object materialization.",
            "Real provider credentials are forbidden in CI by default.",
            "Checker Contract",
            "The checker must not pretend to validate real provider configuration",
            "no-cross-mode privilege escalation proof",
        ),
        BOARD: (
            "Provider/Public URL Entry Freeze",
            "187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md",
            "188_PROVIDER_PUBLIC_URL_ENTRY_CONTRACT.md",
            "provider_public_url_entry_freeze",
            "selected_mode` is `null`",
            "runtime_status` is `not_implemented`",
        ),
        MANIFEST: (
            "latest_provider_public_url_entry_freeze_branch",
            "latest_provider_public_url_entry_freeze_live_behavior_change",
            "provider_public_url_entry_freeze",
            "entry_decision is deferred",
            "selected_mode is null",
            "runtime_status is not_implemented",
        ),
        PROOF_MANIFEST: (
            "provider_public_url_entry_freeze_proof",
            "187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md",
            "188_PROVIDER_PUBLIC_URL_ENTRY_CONTRACT.md",
            "provider_public_url_entry_freeze",
            "no provider/public URL runtime",
            "no existing same-origin signed-reference semantics change",
        ),
    }
    for path, terms in required_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing provider/public URL entry freeze term: {term}")

    manifest_data = _load_json(MANIFEST, errors)
    current_status = manifest_data.get("current_status") if isinstance(manifest_data, dict) else None
    if not isinstance(current_status, dict):
        errors.append(f"{_rel(MANIFEST)} current_status missing for provider/public URL entry freeze")
    else:
        if current_status.get("latest_provider_public_url_entry_freeze_branch") != "codex/l3-provider-url-entry-freeze":
            errors.append(f"{_rel(MANIFEST)} current_status has stale provider/public URL entry freeze branch")
        if current_status.get("latest_provider_public_url_entry_freeze_live_behavior_change") is not False:
            errors.append(f"{_rel(MANIFEST)} current_status must mark provider/public URL entry freeze as planning-only")
        summary = current_status.get("provider_public_url_entry_freeze")
        if not isinstance(summary, str) or "entry_decision is deferred" not in summary or "selected_mode is null" not in summary:
            errors.append(f"{_rel(MANIFEST)} current_status.provider_public_url_entry_freeze must record deferred/null entry decision")

    proof_data = _load_json(PROOF_MANIFEST, errors)
    proof = proof_data.get("provider_public_url_entry_freeze_proof") if isinstance(proof_data, dict) else None
    if not isinstance(proof, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} missing provider_public_url_entry_freeze_proof object")
        return
    expected_scalars = {
        "implementation_branch": "codex/l3-provider-url-entry-freeze",
        "live_behavior_change": False,
        "selected_planning_mode": "provider_public_url_entry_freeze",
        "entry_decision": "deferred",
        "selected_mode": None,
        "runtime_status": "not_implemented",
        "receipt_family": "no_receipt_planning_only",
    }
    for key, expected in expected_scalars.items():
        if proof.get(key) != expected:
            errors.append(f"{_rel(PROOF_MANIFEST)} provider_public_url_entry_freeze_proof.{key} must be {expected!r}")
    governing_docs = proof.get("governing_docs")
    if not isinstance(governing_docs, list):
        errors.append(f"{_rel(PROOF_MANIFEST)} provider_public_url_entry_freeze_proof missing governing_docs")
    else:
        for doc in (
            "next_milestone_plans/Layer3_planning_docs/187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md",
            "next_milestone_plans/Layer3_planning_docs/188_PROVIDER_PUBLIC_URL_ENTRY_CONTRACT.md",
            "next_milestone_plans/Layer3_planning_docs/184_POST_745_DOWNSTREAM_EXPANSION_FREEZE.md",
            "next_milestone_plans/Layer3_planning_docs/185_POST_745_DOWNSTREAM_EXPANSION_CONTRACT.md",
        ):
            if doc not in governing_docs:
                errors.append(f"{_rel(PROOF_MANIFEST)} provider_public_url_entry_freeze_proof governing_docs missing {doc}")
    ledger = proof.get("evidence_ledger")
    if not isinstance(ledger, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} provider_public_url_entry_freeze_proof missing evidence_ledger")
    else:
        verified = ledger.get("current_same_origin_signed_reference_proof")
        if not isinstance(verified, dict) or verified.get("status") != "verified":
            errors.append(f"{_rel(PROOF_MANIFEST)} provider_public_url_entry_freeze_proof must verify current signed-reference evidence")
        for key in (
            "provider_storage_authority",
            "named_use_case",
            "exposure_classification",
            "revocation_contract",
        ):
            item = ledger.get(key)
            if not isinstance(item, dict) or item.get("status") != "unverified" or item.get("evidence") != []:
                errors.append(f"{_rel(PROOF_MANIFEST)} evidence_ledger.{key} must remain unverified with no evidence")
    exposure = proof.get("exposure_model")
    if not isinstance(exposure, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} provider_public_url_entry_freeze_proof missing exposure_model")
    else:
        for key in ("audience", "artifact_sensitivity", "url_bearer_risk", "revocation_model", "auth_dependency"):
            if exposure.get(key) != "unknown":
                errors.append(f"{_rel(PROOF_MANIFEST)} exposure_model.{key} must remain unknown while decision is deferred")
    matrix = proof.get("capability_isolation_matrix")
    if not isinstance(matrix, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} provider_public_url_entry_freeze_proof missing capability_isolation_matrix")
    else:
        for key, flag in (
            ("same_origin_attachment_delivery", "change_allowed_in_this_pass"),
            ("same_origin_signed_reference_delivery", "change_allowed_in_this_pass"),
            ("provider_private_signed_url", "runtime_allowed_in_this_pass"),
            ("provider_public_url", "runtime_allowed_in_this_pass"),
            ("public_proxy_url", "runtime_allowed_in_this_pass"),
            ("provider_object_write_or_copy", "runtime_allowed_in_this_pass"),
            ("connector_destination_dispatch", "runtime_allowed_in_this_pass"),
            ("package_mutation_reconstruction", "runtime_allowed_in_this_pass"),
            ("source_breadth_expansion", "runtime_allowed_in_this_pass"),
            ("rag_vector_or_hybrid_execution", "runtime_allowed_in_this_pass"),
            ("auth_security_behavior_change", "runtime_allowed_in_this_pass"),
        ):
            item = matrix.get(key)
            if not isinstance(item, dict) or item.get(flag) is not False:
                errors.append(f"{_rel(PROOF_MANIFEST)} capability_isolation_matrix.{key}.{flag} must be false")
    expected_negative_invariants = [
        "no provider/public URL runtime",
        "no provider private signed URL runtime",
        "no public proxy URL runtime",
        "no provider object ACL change",
        "no provider object write or copy",
        "no connector or destination dispatch",
        "no generic downstream dispatch",
        "no package mutation or reconstruction",
        "no package payload rewrite",
        "no source expansion",
        "no local upload",
        "no local-directory ingestion",
        "no arbitrary local path input",
        "no web connector retrieval",
        "no RAG/vector retrieval",
        "no broad qualitative execution",
        "no hybrid execution",
        "no full mockup activation",
        "no hidden LLM planning",
        "no frontend-only durable state",
        "no auth/security behavior change",
        "no existing same-origin signed-reference semantics change",
        "no provider credentials in browser or request",
        "no provider URL or token leakage in error bodies",
        "no provider URL or token leakage in logs",
        "no cross-mode privilege escalation",
        "no new route, DTO, model, migration, production service behavior, test behavior, or rendered UI control",
    ]
    if proof.get("negative_invariants") != expected_negative_invariants:
        errors.append(f"{_rel(PROOF_MANIFEST)} provider_public_url_entry_freeze_proof negative_invariants must match the frozen structural list")

def _check_mockup_truth_state_boundary(errors: list[str]) -> None:
    deferred = _capability_map(
        _load_literal_assignment(
            STATE_ACTION_CONTRACT, "STATE_ACTION_DEFERRED_CAPABILITIES", errors
        ),
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        errors,
    )
    full_mockup = deferred.get("full_mockup_activation")
    if full_mockup is None:
        errors.append("deferred capabilities missing full_mockup_activation")
    else:
        if full_mockup.get("admitted") is not False:
            errors.append("full_mockup_activation must remain admitted false")
        if full_mockup.get("reason") != "mockups_target_state_only":
            errors.append("full_mockup_activation reason drifted from mockups_target_state_only")

    expected_deferred = (
        "full_mockup_activation",
        "frontend_only_durable_state",
        "broad_execution",
        "broad_qualitative_execution",
        "hybrid_execution",
        "rag_vector_retrieval",
        "local_upload_or_directory_source_expansion",
        "provider_public_url",
        "connector_destination_dispatch",
        "package_mutation_reconstruction",
        "hidden_llm_planning",
    )
    expected_forbidden_fields = (
        "mockup_activation",
        "frontend_only_state",
        "browser_local_persistence",
        "rag_plan",
        "vector_plan",
        "source_upload",
        "local_directory",
        "connector_id",
        "destination_id",
        "provider_url",
        "public_url",
        "package_payload",
        "hidden_llm_plan",
    )
    expected_evidence = (
        "live_source_owner",
        "route_api_contract",
        "server_authority_contract",
        "negative_invariant_proof",
        "headed_browser_proof",
        "headless_browser_proof",
        "progress_check_guard",
    )
    mockup_deferred = _load_literal_assignment(
        MOCKUP_BOUNDARY_SERVICE, "MOCKUP_DEFERRED_CAPABILITIES", errors
    )
    mockup_forbidden = _load_literal_assignment(
        MOCKUP_BOUNDARY_SERVICE, "MOCKUP_FORBIDDEN_RUNTIME_FIELDS", errors
    )
    mockup_evidence = _load_literal_assignment(
        MOCKUP_BOUNDARY_SERVICE, "MOCKUP_REQUIRED_ACTIVATION_EVIDENCE", errors
    )
    if mockup_deferred != expected_deferred:
        errors.append(
            "mockup deferred capabilities drifted: "
            f"expected {expected_deferred!r}, found {mockup_deferred!r}"
        )
    if mockup_forbidden != expected_forbidden_fields:
        errors.append(
            "mockup forbidden runtime fields drifted: "
            f"expected {expected_forbidden_fields!r}, found {mockup_forbidden!r}"
        )
    if mockup_evidence != expected_evidence:
        errors.append(
            "mockup required activation evidence drifted: "
            f"expected {expected_evidence!r}, found {mockup_evidence!r}"
        )

    service_text = _read_required_text(MOCKUP_BOUNDARY_SERVICE, errors)
    for term in (
        "MOCKUP_TRUTH_STATE_CONTRACT_SCHEMA_ID = \"layer3.mockup_truth_state_contract.v1\"",
        "MOCKUP_TRUTH_STATE_MODE = \"mockups_target_state_only\"",
        "MOCKUP_AUTHORITY_ROLE = \"target_state_design_specification\"",
        "def mockup_truth_state_contract(",
        "\"mockups_are_runtime_authority\": False",
        "\"full_mockup_activation_enabled\": False",
        "\"frontend_only_durable_state_enabled\": False",
        "\"broad_execution_enabled\": False",
        "\"source_widening_enabled\": False",
        "\"connector_destination_dispatch_enabled\": False",
        "\"package_mutation_reconstruction_enabled\": False",
        "\"provider_public_url_enabled\": False",
        "\"hidden_llm_planning_enabled\": False",
        "\"mutates_runtime_state\": False",
        "\"requires_later_freeze\": True",
        "\"requires_browser_proof_before_ui_activation\": True",
    ):
        if term not in service_text:
            errors.append(f"{_rel(MOCKUP_BOUNDARY_SERVICE)} missing mockup contract term: {term}")

    test_text = _read_required_text(MOCKUP_BOUNDARY_TEST, errors)
    for term in expected_deferred + expected_forbidden_fields + expected_evidence:
        if term not in test_text:
            errors.append(f"{_rel(MOCKUP_BOUNDARY_TEST)} missing mockup boundary proof term: {term}")
    if "test_mockup_truth_state_contract_keeps_full_mockup_activation_fail_closed" not in test_text:
        errors.append(f"{_rel(MOCKUP_BOUNDARY_TEST)} missing mockup boundary contract proof")

    mockup_assets_text = _read_required_text(MOCKUP_ASSETS, errors)
    for term in (
        "Status: source inventory for operator-local mockup assets.",
        "bitmap and SVG mockup assets are recorded by path",
        "rather than copied into the repo",
    ):
        if term not in mockup_assets_text:
            errors.append(f"{_rel(MOCKUP_ASSETS)} missing mockup inventory term: {term}")

    mockup_spec_text = _read_required_text(MOCKUP_SPEC, errors)
    for term in (
        "Status: pre-implementation design/specification draft",
        "target-state/design-intent authority only",
        "Do not treat this specification as activation permission for the entire mockup.",
        "Do not claim the full mockup workbench exists",
    ):
        if term not in mockup_spec_text:
            errors.append(f"{_rel(MOCKUP_SPEC)} missing mockup spec authority term: {term}")

    required_doc_terms = {
        MOCKUP_TRUTH_FREEZE: [
            "selected_mockup_truth_state_mode: `mockups_target_state_only`",
            "layer3.mockup_truth_state_contract.v1",
            "full_mockup_activation_enabled: `False`",
            "frontend_only_durable_state_enabled: `False`",
            "mockups_are_runtime_authority: `False`",
            "No full mockup activation, frontend-only durable state, broad execution, source widening, connector/destination dispatch, provider/public URL support, package mutation/reconstruction, hidden LLM planning, or broad qualitative/hybrid/RAG execution is admitted.",
        ],
        DEFERRED_GATES: [
            "125_MOCKUP_TRUTH_STATE_FREEZE.md",
            "mockups_target_state_only",
            "full mockup activation and frontend-only durable state remain blocked",
        ],
        SYNTHESIS_BOUNDARY: [
            "125_MOCKUP_TRUTH_STATE_FREEZE.md",
            "mockup_truth_state_contract()",
            "layer3.mockup_truth_state_contract.v1",
        ],
        GOAL_AUDIT: [
            "125_MOCKUP_TRUTH_STATE_FREEZE.md",
            "full_mockup_activation",
            "mockups_target_state_only",
            "PR #544 separately established the `mockups_target_state_only` truth-state boundary with `274 passed`",
            "PR #545 was docs/proof synchronization only",
            "36526ee1",
            "PR #547 established `Layer3PreflightRequest`",
            "54c5d8ef",
            "PR #550 established `L3GateBIdempotencyKey`",
            "4793d8d1",
        ],
        CLOSEOUT_DOC: [
            "Functional boundary evidence still targets PR #556 at `project6-origin/main=93fe525b`",
            "This file is post-merge documentation/proof synchronization only.",
            "bounded snapshot, not an evergreen manifest",
            "snapshot_target_ref: `project6-origin/main`",
            "functional_boundary_head: `93fe525b`",
            "functional_boundary_role: last runtime-affecting Layer 3 boundary captured in this snapshot",
            "proof_snapshot_head: `f1cba09a84a47d0095a7fd682b835316ebde5496`",
            "latest_proof_boundary_pr: `#607`",
            "not a self-updating current-main marker",
            "latest_functional_boundary_pr: `#556`",
            "docs_sync_reference_pr: `#551`",
            "do not infer the live `project6-origin/main` SHA from this field",
            "current_main_rule: re-read live git and rerun `python .\\tools\\l3-progress-check.py` before new work",
            "Durable Gate B idempotency claim",
            "test_gate_b_decision_concurrent_duplicate_client_request_id_uses_durable_claim",
            "125_MOCKUP_TRUTH_STATE_FREEZE.md",
            "mockup_truth_state_contract()",
            "full mockup activation remains blocked",
            "Pre-merge PR #544 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #544: 005ef212753adf2feb859b28362a0bee3d7d72d1.",
            "Pre-merge PR #545 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #545: 36526ee1.",
            "Pre-merge PR #547 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #547: 54c5d8ef.",
            "Pre-merge PR #548 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #548: e0183721.",
            "Pre-merge PR #550 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #550: 4793d8d1.",
            "PR #564 authority rail extraction proof",
            "Merged main head after PR #564: 3418d429.",
            "PR #566 preview hash/identity contract extraction proof",
            "Merged main head after PR #566: ac367350.",
            "PR #568 readiness contract extraction proof",
            "Merged main head after PR #568: 6b1a12f0.",
            "PR #569 workbench error extraction proof",
            "Merged main head after PR #569: 5e09187e.",
            "PR #571 bootstrap contract extraction proof",
            "Merged main head after PR #571: 47351763.",
            "PR #573 state-model contract extraction proof",
            "Merged main head after PR #573: ebb6d9c2.",
            "Bootstrap contract extraction focused proof",
            "State-model contract extraction focused proof",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        if path == CLOSEOUT_DOC:
            for stale_term in (
                "latest_merged_pr:",
                "current_branch:",
                "merged_main_head: `005ef212`",
                "snapshot_target_head:",
                "latest_docs_sync_pr:",
                "current baseline ref:",
                "local authority was read from",
            ):
                if stale_term in text:
                    errors.append(f"{_rel(path)} retains stale evergreen closeout term: {stale_term}")
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing mockup truth-state term: {term}")


def _check_signed_reference_state_guard(errors: list[str]) -> None:
    service_text = _read_required_text(SIGNED_REFERENCE_STATE_SERVICE, errors)
    for term in (
        "def record_used_signed_reference(",
        "L3SignedReferenceToken.state == SIGNED_REFERENCE_TOKEN_STATE_READY",
        "L3SignedReferenceToken.use_count < L3SignedReferenceToken.max_use_count",
        "synchronize_session=False",
        "external_export_download_signed_reference_replay_denied",
    ):
        if term not in service_text:
            errors.append(f"{_rel(SIGNED_REFERENCE_STATE_SERVICE)} missing signed-reference guard term: {term}")

    test_text = _read_required_text(SIGNED_REFERENCE_STATE_TEST, errors)
    for term in (
        "test_record_generated_signed_reference_persists_sanitized_durable_state",
        "test_single_use_reference_records_one_delivery_and_rejects_replay",
        "test_revoked_reference_fails_closed_and_records_rejected_audit",
        "test_expired_reference_fails_closed_and_marks_token_expired",
        "test_concurrent_single_use_reference_does_not_double_deliver",
        "INTERNAL_ARTIFACT_REF_PLACEHOLDER",
    ):
        if term not in test_text:
            errors.append(f"{_rel(SIGNED_REFERENCE_STATE_TEST)} missing signed-reference proof term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: [
            "backend/app/services/layer3_signed_reference_state.py",
            "backend/tests/test_layer3_signed_reference_state.py",
            "atomic conditional update",
        ],
        GOAL_AUDIT: [
            "backend/app/services/layer3_signed_reference_state.py",
            "backend/tests/test_layer3_signed_reference_state.py",
            "concurrent single-use proof",
            "267 passed",
        ],
        CLOSEOUT_DOC: [
            "backend/app/services/layer3_signed_reference_state.py",
            "backend/tests/test_layer3_signed_reference_state.py",
            "267 passed, 4 warnings",
            "same-origin signed-reference service proof",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing signed-reference guard term: {term}")


def _check_preflight_request_guard(errors: list[str]) -> None:
    contract_text = _read_required_text(PREFLIGHT_REQUEST_CONTRACT_SERVICE, errors)
    for term in (
        "PREFLIGHT_MANUAL_CONSTRAINT_ALLOWED_FIELDS = frozenset(",
        "PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS = frozenset(",
        "def manual_constraints_from_payload(",
        "def preflight_manual_constraint_blocked_fields(",
        "\"auth_security_hardening\"",
        "\"connector_destination_dispatch\"",
        "\"full_mockup_activation\"",
        "\"local_upload\"",
        "\"local_upload_or_directory_source_expansion\"",
        "\"package_mutation_reconstruction\"",
    ):
        if term not in contract_text:
            errors.append(f"{_rel(PREFLIGHT_REQUEST_CONTRACT_SERVICE)} missing preflight contract term: {term}")

    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "class Layer3PreflightRequest(BaseModel):",
        "model_config = ConfigDict(extra=\"forbid\")",
        "PREFLIGHT_REQUEST_SCHEMA: dict[str, Any] = {",
        "\"additionalProperties\": False",
        "source-widening fields are rejected before service execution",
        "PREFLIGHT_MANUAL_CONSTRAINT_FORBIDDEN_FIELDS",
        "payload: Layer3PreflightRequest",
        "layer3_workbench.preflight(payload.model_dump(exclude_none=True))",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing preflight request guard term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_preflight_request_contract import",
        "manual_constraints_from_payload as _manual_constraints",
        "preflight_manual_constraint_blocked_fields",
        "preflight_manual_constraint_scope_not_admitted",
        "remove_non_admitted_manual_constraints",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing preflight contract delegation term: {term}")
    if "def _manual_constraints(" in workbench_text:
        errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns preflight manual constraints helper")

    contract_test_text = _read_required_text(PREFLIGHT_REQUEST_CONTRACT_TEST, errors)
    for term in (
        "test_preflight_manual_constraints_preserve_known_open_shape",
        "test_preflight_manual_constraints_block_deferred_capability_sentinels_recursively",
        "test_preflight_manual_constraints_block_every_state_action_deferred_capability",
        "STATE_ACTION_DEFERRED_CAPABILITIES",
        "manual_constraints.conflict.auth_security_hardening",
        "manual_constraints.connector_destination_dispatch",
        "manual_constraints.date_bounds.provider_public_url",
        "manual_constraints.package_mutation_reconstruction",
        "manual_constraints.required_artifacts[0].local_upload_or_directory_source_expansion",
        "manual_constraints.topics[0].rag_plan",
        "manual_constraints.topics[1].full_mockup_activation",
    ):
        if term not in contract_test_text:
            errors.append(f"{_rel(PREFLIGHT_REQUEST_CONTRACT_TEST)} missing preflight contract proof term: {term}")

    test_text = _read_required_text(LAYER3_API_TEST, errors)
    for term in (
        "test_layer3_api_preflight_rejects_extra_fields_before_service_execution",
        "test_layer3_api_preflight_rejects_forbidden_manual_constraint_sentinels",
        "api-preflight-strict-extra",
        "api-preflight-forbidden-manual-constraints",
        "connector_destination_dispatch",
        "full_mockup_activation",
        "local_directory",
        "package_mutation_reconstruction",
        "preflight_manual_constraint_scope_not_admitted",
        "extra_forbidden",
        "preflight service should not run when request validation rejects extra fields",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_API_TEST)} missing preflight request guard test term: {term}")

    required_doc_terms = {
        BOARD: [
            "PR `#634` hardens the preflight `manual_constraints` request contract",
            "PR `#639` closes the residual exact deferred-sentinel gap",
            "STATE_ACTION_DEFERRED_CAPABILITIES",
            "backend/app/services/layer3_preflight_request_contract.py",
            "connector_destination_dispatch",
            "package_mutation_reconstruction",
            "full_mockup_activation",
            "auth_security_hardening",
            "preflight_manual_constraint_scope_not_admitted",
            "admits no L3PassRun or AnalysisRun creation",
        ],
        MANIFEST: [
            "merged_live_preflight_manual_constraints_request_contract",
            "preflight_exact_deferred_sentinel_hardening_pr639",
            "PR #634 implements bounded API request-contract hardening",
            "PR #639 closes the residual PR #634 preflight manual_constraints gap",
            "STATE_ACTION_DEFERRED_CAPABILITIES",
            "layer3_preflight_request_contract.py owns manual-constraint normalization",
            "preflight_manual_constraint_scope_not_admitted",
        ],
        PROOF_MANIFEST: [
            "preflight_manual_constraints_request_contract_proof",
            "latest_preflight_manual_constraints_request_contract_pr",
            "latest_preflight_exact_deferred_sentinel_hardening_pr",
            "latest_preflight_exact_deferred_sentinel_hardening_summary",
            "backend/tests/test_layer3_preflight_request_contract.py",
            "STATE_ACTION_DEFERRED_CAPABILITIES",
            "no L3PassRun, AnalysisRun, or L3OutputPackage side effects",
        ],
        SYNTHESIS_BOUNDARY: [
            "Layer3PreflightRequest",
            "test_layer3_api_preflight_rejects_extra_fields_before_service_execution",
            "preflight DTO boundary",
        ],
        GOAL_AUDIT: [
            "Layer3PreflightRequest",
            "test_layer3_api_preflight_rejects_extra_fields_before_service_execution",
            "preflight DTO boundary",
        ],
        CLOSEOUT_DOC: [
            "Preflight DTO boundary",
            "Layer3PreflightRequest",
            "test_layer3_api_preflight_rejects_extra_fields_before_service_execution",
            "PR #547 preflight DTO boundary proof",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing preflight request guard term: {term}")


def _check_plan_preview_request_guard(errors: list[str]) -> None:
    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "class Layer3PlanPreviewRequest(BaseModel):",
        "model_config = ConfigDict(extra=\"forbid\")",
        "PLAN_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {",
        "\"additionalProperties\": False",
        "source-widening fields are rejected before service mutation",
        "payload: Layer3PlanPreviewRequest",
        "layer3_workbench.plan_preview(db, payload.model_dump(exclude_none=True))",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing plan-preview request guard term: {term}")

    test_text = _read_required_text(LAYER3_API_TEST, errors)
    for term in (
        "test_layer3_api_plan_preview_rejects_extra_fields_before_service_mutation",
        "api-plan-preview-strict-extra",
        "extra_forbidden",
        "db.query(L3AnalysisPlan).count() == 0",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_API_TEST)} missing plan-preview proof term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: [
            "Layer3PlanPreviewRequest",
            "test_layer3_api_plan_preview_rejects_extra_fields_before_service_mutation",
            "plan-preview DTO boundary",
        ],
        GOAL_AUDIT: [
            "Layer3PlanPreviewRequest",
            "test_layer3_api_plan_preview_rejects_extra_fields_before_service_mutation",
            "267 passed",
        ],
        CLOSEOUT_DOC: [
            "Layer3PlanPreviewRequest",
            "test_layer3_api_plan_preview_rejects_extra_fields_before_service_mutation",
            "267 passed, 4 warnings",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing plan-preview guard term: {term}")


def _check_source_preview_request_guard(errors: list[str]) -> None:
    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "class Layer3SourcePreviewRequest(BaseModel):",
        "model_config = ConfigDict(extra=\"forbid\")",
        "SOURCE_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {",
        "\"additionalProperties\": False",
        "source expansion fields are rejected before service execution",
        "payload: Layer3SourcePreviewRequest",
        "layer3_workbench.source_preview(payload.model_dump(exclude_none=True))",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing source-preview request guard term: {term}")

    test_text = _read_required_text(LAYER3_API_TEST, errors)
    for term in (
        "test_layer3_api_source_preview_rejects_extra_fields_before_service_execution",
        "api-source-preview-strict-extra",
        "local_directory",
        "extra_forbidden",
        "db.query(L3Session).count() == 0",
        "db.query(L3PassRun).count() == 0",
        "db.query(AnalysisRun).count() == 0",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_API_TEST)} missing source-preview request proof term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: [
            "Layer3SourcePreviewRequest",
            "test_layer3_api_source_preview_rejects_extra_fields_before_service_execution",
            "source-preview DTO boundary",
        ],
        GOAL_AUDIT: [
            "Layer3SourcePreviewRequest",
            "test_layer3_api_source_preview_rejects_extra_fields_before_service_execution",
            "267 passed",
        ],
        CLOSEOUT_DOC: [
            "Layer3SourcePreviewRequest",
            "test_layer3_api_source_preview_rejects_extra_fields_before_service_execution",
            "267 passed, 4 warnings",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing source-preview request guard term: {term}")


def _check_material_preview_request_guard(errors: list[str]) -> None:
    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "class Layer3MaterialPreviewRequest(BaseModel):",
        "model_config = ConfigDict(extra=\"forbid\")",
        "MATERIAL_PREVIEW_REQUEST_SCHEMA: dict[str, Any] = {",
        "\"additionalProperties\": False",
        "source expansion fields are rejected before service execution",
        "payload: Layer3MaterialPreviewRequest",
        "layer3_workbench.material_preview(payload.model_dump(exclude_none=True), db)",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing material-preview request guard term: {term}")

    test_text = _read_required_text(LAYER3_API_TEST, errors)
    for term in (
        "test_layer3_api_material_preview_rejects_extra_fields_before_service_execution",
        "api-material-preview-strict-extra",
        "local_directory",
        "extra_forbidden",
        "db.query(L3Session).count() == 0",
        "db.query(L3PassRun).count() == 0",
        "db.query(AnalysisRun).count() == 0",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_API_TEST)} missing material-preview request proof term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: [
            "Layer3MaterialPreviewRequest",
            "test_layer3_api_material_preview_rejects_extra_fields_before_service_execution",
            "material-preview DTO boundary",
        ],
        GOAL_AUDIT: [
            "Layer3MaterialPreviewRequest",
            "test_layer3_api_material_preview_rejects_extra_fields_before_service_execution",
            "267 passed",
        ],
        CLOSEOUT_DOC: [
            "Layer3MaterialPreviewRequest",
            "test_layer3_api_material_preview_rejects_extra_fields_before_service_execution",
            "267 passed, 4 warnings",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing material-preview request guard term: {term}")


def _check_gate_c_override_request_guard(errors: list[str]) -> None:
    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "class Layer3GateCOverrideUnavailableRequest(BaseModel):",
        "model_config = ConfigDict(extra=\"forbid\")",
        "payload: Layer3GateCOverrideUnavailableRequest",
        "layer3_workbench.gate_c_override_unavailable(payload.model_dump(exclude_none=True))",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing Gate C override request guard term: {term}")
    if "def post_gate_c_override(payload: dict[str, Any])" in api_text:
        errors.append(f"{_rel(LAYER3_API)} regressed Gate C override to a raw dict request boundary")

    test_text = _read_required_text(LAYER3_API_TEST, errors)
    for term in (
        "test_layer3_api_gate_c_override_rejects_unknown_fields_before_unavailable_response",
        "api-override-extra",
        "hidden_llm_plan",
        "provider_public_url",
        "assert response.status_code == 422",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_API_TEST)} missing Gate C override request proof term: {term}")

    proof_text = _read_required_text(PROOF_MANIFEST, errors)
    for term in (
        "gate_c_override_unavailable_request_contract_proof",
        "Layer3GateCOverrideUnavailableRequest",
        "test_layer3_api_gate_c_override_rejects_unknown_fields_before_unavailable_response",
        "Signed-reference raw dict routes are auth/security/delivery-adjacent and remain deferred",
        "\"implementation_pr\": \"#614\"",
        "\"merge_commit\": \"840a86fb\"",
    ):
        if term not in proof_text:
            errors.append(f"{_rel(PROOF_MANIFEST)} missing Gate C override request proof term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: [
            "PR #614 / merge commit `840a86fb`",
            "Layer3GateCOverrideUnavailableRequest",
            "test_layer3_api_gate_c_override_rejects_unknown_fields_before_unavailable_response",
            "Gate C override unavailable DTO boundary",
        ],
        GOAL_AUDIT: [
            "PR #614 / merge commit `840a86fb`",
            "Layer3GateCOverrideUnavailableRequest",
            "test_layer3_api_gate_c_override_rejects_unknown_fields_before_unavailable_response",
            "Gate C override unavailable DTO hardening",
        ],
        CLOSEOUT_DOC: [
            "PR #614 / merge commit 840a86fb",
            "Gate C override unavailable DTO boundary proof",
            "Focused override request-boundary suite: 3 passed",
            "No typing override persistence",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing Gate C override request guard term: {term}")


def _check_session_status_migration_constraint(errors: list[str]) -> None:
    migration_text = _read_required_text(SESSION_ENTRY_MIGRATION, errors)
    for term in (
        "sa.CheckConstraint(",
        "ck_l3_session_status",
        "active_loading",
        "active_planning",
        "active_execution",
        "completed",
        "completed_with_warnings",
        "failed",
    ):
        if term not in migration_text:
            errors.append(f"{_rel(SESSION_ENTRY_MIGRATION)} missing session-status migration term: {term}")

    test_text = _read_required_text(SESSION_ENTRY_TEST, errors)
    for term in (
        "test_layer3_session_entry_migration_defines_status_check_constraint",
        "SESSION_ENTRY_MIGRATION",
        "ck_l3_session_status",
        "L3_SESSION_STATUS_VALUES",
    ):
        if term not in test_text:
            errors.append(f"{_rel(SESSION_ENTRY_TEST)} missing session-status migration proof term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: [
            "0012_layer3_session_entry.py",
            "test_layer3_session_entry_migration_defines_status_check_constraint",
            "session-status migration constraint",
        ],
        GOAL_AUDIT: [
            "0012_layer3_session_entry.py",
            "test_layer3_session_entry_migration_defines_status_check_constraint",
            "267 passed",
        ],
        CLOSEOUT_DOC: [
            "0012_layer3_session_entry.py",
            "test_layer3_session_entry_migration_defines_status_check_constraint",
            "267 passed, 4 warnings",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing session-status migration term: {term}")


def _check_plan_pass_status_migration_constraints(errors: list[str]) -> None:
    models_text = _read_required_text(MODELS, errors)
    pass_entry_text = _read_required_text(ROOT / "backend" / "app" / "services" / "layer3_pass_entry.py", errors)
    approved_plan_cancel_text = _read_required_text(APPROVED_PLAN_CORRECTION_SERVICE, errors)
    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "L3_ANALYSIS_PLAN_STATUS_VALUES",
        "L3_PASS_RUN_STATUS_VALUES",
        "ck_l3_analysis_plan_status",
        "ck_l3_pass_run_status",
    ):
        if term not in models_text:
            errors.append(f"{_rel(MODELS)} missing plan/pass status model term: {term}")
    for term in (
        "PLAN_STATUS_FORMED = L3_ANALYSIS_PLAN_STATUS_FORMED",
        "PLAN_STATUS_APPROVED = L3_ANALYSIS_PLAN_STATUS_APPROVED",
        "PASS_STATUS_PLANNED = L3_PASS_RUN_STATUS_PLANNED",
        "PASS_STATUS_SELECTED_NOT_STARTED = L3_PASS_RUN_STATUS_SELECTED_NOT_STARTED",
        "PASS_STATUS_RUNNING = L3_PASS_RUN_STATUS_RUNNING",
        "PASS_STATUS_COMPLETED = L3_PASS_RUN_STATUS_COMPLETED",
        "PASS_STATUS_COMPLETED_WITH_WARNINGS = L3_PASS_RUN_STATUS_COMPLETED_WITH_WARNINGS",
        "PASS_STATUS_FAILED = L3_PASS_RUN_STATUS_FAILED",
    ):
        if term not in pass_entry_text:
            errors.append(f"backend/app/services/layer3_pass_entry.py missing plan/pass status alias term: {term}")
    if "APPROVED_PLAN_APPROVED_STATUS = L3_ANALYSIS_PLAN_STATUS_APPROVED" not in approved_plan_cancel_text:
        errors.append(
            "backend/app/services/layer3_approved_plan_correction.py missing approved-status model alias"
        )
    if "APPROVED_PLAN_CANCELLED_STATUS = L3_ANALYSIS_PLAN_STATUS_CANCELLED" not in approved_plan_cancel_text:
        errors.append(
            "backend/app/services/layer3_approved_plan_correction.py missing cancelled-status model alias"
        )
    if 'L3AnalysisPlan.status == "approved"' in approved_plan_cancel_text:
        errors.append(
            "backend/app/services/layer3_approved_plan_correction.py retains raw approved-plan status literal"
        )
    for term in (
        "PLAN_STATUS_APPROVED",
        "APPROVED_PLAN_CANCELLED_STATUS",
        "status=PASS_STATUS_SELECTED_NOT_STARTED",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing plan/pass status alias term: {term}")
    for literal in (
        'status == "approved"',
        'status == "cancelled"',
        'status="selected_not_started"',
        'plan_status") == "approved"',
    ):
        if literal in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} retains raw plan/pass status literal: {literal}")

    migration_text = _read_required_text(PASS_ENTRY_MIGRATION, errors)
    for term in (
        "ck_l3_analysis_plan_status",
        "ck_l3_pass_run_status",
        "'formed'",
        "'approved'",
        "'cancelled'",
        "'planned'",
        "'selected_not_started'",
        "'running'",
        "'completed'",
        "'completed_with_warnings'",
        "'failed'",
    ):
        if term not in migration_text:
            errors.append(f"{_rel(PASS_ENTRY_MIGRATION)} missing plan/pass status migration term: {term}")

    test_text = _read_required_text(PLAN_PASS_STATUS_CONSTRAINT_TEST, errors)
    for term in (
        "test_layer3_plan_status_check_constraint_rejects_unknown_status",
        "test_layer3_pass_run_status_check_constraint_rejects_unknown_status",
        "test_layer3_plan_and_pass_status_vocabularies_match_owner_services",
        "test_layer3_pass_entry_migration_defines_plan_and_pass_status_constraints",
        "APPROVED_PLAN_CANCELLED_STATUS",
        "PASS_STATUS_SELECTED_NOT_STARTED",
        "L3_ANALYSIS_PLAN_STATUS_VALUES",
        "L3_PASS_RUN_STATUS_VALUES",
        "ck_l3_analysis_plan_status",
        "ck_l3_pass_run_status",
        "IntegrityError",
    ):
        if term not in test_text:
            errors.append(f"{_rel(PLAN_PASS_STATUS_CONSTRAINT_TEST)} missing plan/pass status proof term: {term}")

    progress_text = _read_required_text(MANIFEST, errors)
    proof_text = _read_required_text(PROOF_MANIFEST, errors)
    for path, text, terms in (
        (
            MANIFEST,
            progress_text,
            (
                "plan_pass_status_constraint_alignment",
                "ck_l3_analysis_plan_status",
                "ck_l3_pass_run_status",
                "test_layer3_plan_pass_status_constraints.py",
                "fresh schema/model status constraints only",
                "\"implementation_pr\": \"#616\"",
                "\"merge_commit\": \"652df83e\"",
                "\"owner_service_constant_alignment_pr\": \"#618\"",
                "\"owner_service_constant_alignment_merge_commit\": \"c5ae1b8f\"",
                "\"workbench_status_constant_alignment_pr\": \"#620\"",
                "\"workbench_status_constant_alignment_merge_commit\": \"93215740\"",
            ),
        ),
        (
            PROOF_MANIFEST,
            proof_text,
            (
                "plan_pass_status_constraint_alignment_proof",
                "ck_l3_analysis_plan_status",
                "ck_l3_pass_run_status",
                "test_layer3_plan_pass_status_constraints.py",
                "No retrofit migration for already-upgraded SQLite databases",
                "\"implementation_pr\": \"#616\"",
                "\"merge_commit\": \"652df83e\"",
                "\"owner_service_alias_pr\": \"#618\"",
                "\"owner_service_alias_merge_commit\": \"c5ae1b8f\"",
                "\"workbench_status_alias_pr\": \"#620\"",
                "\"workbench_status_alias_merge_commit\": \"93215740\"",
            ),
        ),
    ):
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing plan/pass status proof term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: [
            "test_layer3_plan_pass_status_constraints.py",
            "ck_l3_analysis_plan_status",
            "ck_l3_pass_run_status",
            "fresh-schema/model status constraint",
            "PR #616 / merge commit `652df83e`",
            "PR #618 / merge commit `c5ae1b8f`",
            "PR #620 / merge commit `93215740`",
        ],
        GOAL_AUDIT: [
            "PR #616 / merge commit `652df83e`",
            "test_layer3_plan_pass_status_constraints.py",
            "plan/pass status constraint alignment",
            "No retrofit migration for already-upgraded SQLite databases",
        ],
        CLOSEOUT_DOC: [
            "PR #616 / merge commit 652df83e",
            "PR #618 / merge commit c5ae1b8f",
            "PR #620 / merge commit 93215740",
            "Plan/pass status constraint alignment proof",
            "test_layer3_plan_pass_status_constraints.py",
            "Focused status-constraint proof: 5 passed",
            "No retrofit migration for already-upgraded SQLite databases",
        ],
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing plan/pass status doc term: {term}")


def _check_progress_text_surfaces(errors: list[str]) -> None:
    required_by_file = {
        BOARD: [
            "As of `2026-05-06`",
            "ad51b1c6736cd51ec3dd30de914e59ddb4c66158",
            "remaining authentication/security work is intentionally deferred",
            "PR `#531` now makes Gate B post-commit retry idempotency and material-preview hash hardening current-main bounded behavior",
            "PR `#533` now makes server-derived `state_action_contract` hardening current-main bounded behavior",
            "PR `#609` now makes APS source-family extraction current-main no-behavior-change refactor/proof",
            "C:\\Users\\benny\\Downloads\\audit\\AUDIT_SYNTHESIS_ADJUDICATION.md",
            "API request-contract hardening for forbidden sentinel fields second",
        ],
        REFRESH_SPEC: [
            "Post-PR533 `2026-05-05` progress/proof sync",
            "4d2bac8f68e52f7205210d19cce64576dc0384c4",
            "confirmed the PR `#533` implementation commit is merged",
            "remaining authentication/security work is still intentionally deferred",
            "PR `#533` makes server-derived `state_action_contract` metadata current-main bounded behavior",
            "near-term work should stay on non-security proof/state/refactor surfaces",
            "python .\\tools\\l3-progress-check.py",
        ],
        PROGRESS_PROMPT: [
            "post-PR533 progress/proof sync on `2026-05-05`",
            "4d2bac8f68e52f7205210d19cce64576dc0384c4",
            "remaining authentication/security work",
            "current main includes PR `#533` as bounded server-derived `state_action_contract` hardening",
            "Prefer non-security progress/proof/state/refactor work",
            "python .\\tools\\l3-progress-check.py",
        ],
    }
    for path, terms in required_by_file.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing local sync term: {term}")


def _check_ci_layer3_backend_guardrail(errors: list[str]) -> None:
    if not PLAYWRIGHT_WORKFLOW.exists():
        errors.append(f"missing required workflow file: {_rel(PLAYWRIGHT_WORKFLOW)}")
        return
    text = PLAYWRIGHT_WORKFLOW.read_text(encoding="utf-8")
    required = "python -m pytest ./backend/tests/test_layer3_*.py -q"
    if required not in text:
        errors.append(
            "backend Layer 3 CI guardrail must run the focused test_layer3_*.py family"
        )
    old_single_file = "python -m pytest ./backend/tests/test_layer3_api.py -q"
    if old_single_file in text:
        errors.append("backend Layer 3 CI guardrail regressed to the single API test file")
    required_name = "Run focused Layer 3 backend pytest guardrail"
    if required_name not in text:
        errors.append("backend Layer 3 CI guardrail step name must reflect focused coverage")
    if "requirements-layer3-api.txt" not in text:
        errors.append("Layer 3 CI workflow must track requirements-layer3-api.txt dependency changes")

    api_requirements = _read_required_text(LAYER3_API_REQUIREMENTS, errors)
    if "pyarrow" not in api_requirements:
        errors.append("Layer 3 API test requirements must include a parquet engine such as pyarrow")

    browser_requirements = _read_required_text(BROWSER_REQUIREMENTS, errors)
    if "-r requirements-layer3-api.txt" not in browser_requirements:
        errors.append("browser harness requirements must include focused Layer 3 API requirements")


def _check_qualitative_progress_sync(manifest: dict[str, Any], errors: list[str]) -> None:
    live_state = "merged_live_bounded_single_aps_doc_qualitative_execution"
    state_model = manifest.get("state_model")
    if not isinstance(state_model, dict) or live_state not in state_model:
        errors.append(f"state_model missing {live_state}")

    slices = manifest.get("layer3_workbench_slices")
    if isinstance(slices, list):
        matching = [
            item
            for item in slices
            if isinstance(item, dict) and item.get("main_state") == live_state
        ]
        if len(matching) != 1:
            errors.append(f"layer3_workbench_slices must contain exactly one {live_state}")

    proof_manifest = _load_json(PROOF_MANIFEST, errors)
    proof_scope = proof_manifest.get("scope") if isinstance(proof_manifest, dict) else {}
    if isinstance(proof_scope, dict):
        expected = {
            "latest_qualitative_aps_execution_implementation_pr": "#535",
            "latest_qualitative_aps_execution_error_proof_pr": "#558",
        }
        for key, value in expected.items():
            if proof_scope.get(key) != value:
                errors.append(f"{_rel(PROOF_MANIFEST)} {key} must be {value}")
    if "single_aps_doc_qualitative_execution_current_boundary_proof" not in proof_manifest:
        errors.append(f"{_rel(PROOF_MANIFEST)} missing qualitative current-boundary proof object")

    progress_surfaces = (
        MANIFEST,
        BOARD,
        PROOF_MANIFEST,
        REFRESH_SPEC,
        PROGRESS_PROMPT,
        PHASE1A_README,
    )
    stale_terms = (
        "Do not implement qualitative APS content document execution until a later implementation-entry freeze chooses exactly single_aps_doc_qualitative_pass.",
        "qualitative-only sets still fail closed",
        "qualitative APS content document execution remains blocked by default",
        "current live APS document support stops at selection",
    )
    for path in progress_surfaces:
        text = _read_required_text(path, errors)
        for term in stale_terms:
            if term in text:
                errors.append(f"{_rel(path)} contains stale qualitative progress wording: {term}")

    required_terms = {
        MANIFEST: (
            live_state,
            "PR #558 qualitative owner-service error-boundary proof",
            "PR #559 docs/proof sync",
        ),
        BOARD: (
            "Single APS-document qualitative execution boundary",
            "PR `#558` proof-hardened qualitative owner-service error mapping",
        ),
        PROOF_MANIFEST: (
            "latest_qualitative_aps_execution_implementation_pr",
            "single_aps_doc_qualitative_execution_current_boundary_proof",
        ),
        REFRESH_SPEC: (
            "119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md",
            "classify only `single_aps_doc_qualitative_pass` as live bounded behavior",
        ),
        PROGRESS_PROMPT: (
            "119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md",
            "render only the exact `single_aps_doc_qualitative_pass` as live bounded behavior",
        ),
        PHASE1A_README: (
            "exact `single_aps_doc_qualitative_pass` is now the only admitted qualitative APS execution mode",
            "broad qualitative",
        ),
    }
    for path, terms in required_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing qualitative progress sync term: {term}")


def _check_state_action_contract_frontend_signature(errors: list[str]) -> None:
    js_text = _read_required_text(LAYER3_JS, errors)
    required_js_terms = (
        "function stateActionContractSignature(source = null)",
        "state_action_contract_signature: stateActionContractSignature(State.sessionSummary)",
        "state_action_contract_signature: stateActionContractSignature()",
        "anchor.state_action_contract_signature !== currentContract",
        "draft.state_action_contract_signature !== currentContract",
        "const summaryContract = stateActionContractSignature(summary)",
        "state_action_matrix: stateActionMatrixSignatureItems(contract.state_action_matrix)",
        "admitted_capabilities: capabilitySignatureItems(contract.admitted_capabilities)",
        "deferred_capabilities: capabilitySignatureItems(contract.deferred_capabilities)",
    )
    for term in required_js_terms:
        if term not in js_text:
            errors.append(f"{_rel(LAYER3_JS)} missing state/action contract signature term: {term}")

    stale_js_terms = (
        "anchor.state_action_contract_schema_id !== currentContract",
        "draft.state_action_contract_schema_id !== currentContract",
        "const summaryContract = stateActionContractSchemaId(summary)",
    )
    for term in stale_js_terms:
        if term in js_text:
            errors.append(f"{_rel(LAYER3_JS)} still compares frontend recovery using schema-id-only term: {term}")

    required_test_terms = {
        LAYER3_PAGE_TEST: (
            "function stateActionContractSignature",
            "state_action_contract_signature: stateActionContractSignature(State.sessionSummary)",
            "anchor.state_action_contract_signature !== currentContract",
            "draft.state_action_contract_signature !== currentContract",
        ),
        LAYER3_WORKBENCH_E2E: (
            "clears schema-id-only Gate B drafts after contract signature hardening",
            "stale-schema-id-only-draft",
            "draftBeforeReload.state_action_contract_signature",
            "storageAfterCommit.recovery.state_action_contract_signature",
            '"schema_id":"layer3.state_action_contract.v1"',
        ),
    }
    for path, terms in required_test_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing state/action contract signature proof term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "state_action_contract_signature",
            "frontend recovery with state/action contract signature invalidation",
        ),
        GOAL_AUDIT: (
            "state/action contract signature hardening",
            "schema-id-only stale Gate B drafts clear on load",
        ),
        CLOSEOUT_DOC: (
            "state_action_contract_signature",
            "Contract-signature invalidation rejects stale browser snapshots",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing state/action contract signature doc term: {term}")


def _check_response_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(RESPONSE_CONTRACT_SERVICE, errors)
    for term in (
        "LAYER3_SCHEMA_VERSION = 1",
        "def base_response(",
        '"schema_version": LAYER3_SCHEMA_VERSION',
        '"request_id": request_id or uuid_str()',
        '"server_time": utcnow_iso_z()',
    ):
        if term not in service_text:
            errors.append(f"{_rel(RESPONSE_CONTRACT_SERVICE)} missing response contract term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_response_contract import",
        "LAYER3_SCHEMA_VERSION as SCHEMA_VERSION",
        "base_response as _base_response",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing response contract extraction term: {term}")
    if "SCHEMA_VERSION = 1" in workbench_text:
        errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns the Layer 3 schema version constant")
    if "def _base_response(" in workbench_text:
        errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns _base_response instead of importing it")

    test_text = _read_required_text(LAYER3_RESPONSE_CONTRACT_TEST, errors)
    for term in (
        "test_layer3_base_response_contract_is_shared_without_behavior_change",
        "base_response(\"layer3.test_response.v1\"",
        "bootstrap = layer3_workbench.bootstrap()",
        "assert bootstrap[\"schema_version\"] == LAYER3_SCHEMA_VERSION",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_RESPONSE_CONTRACT_TEST)} missing response contract test term: {term}")

    required_doc_terms = {
        GOAL_AUDIT: (
            "response envelope extraction",
            "layer3_response_contract.py",
            "response envelope extraction proof merged after PR #562",
            "369e4131",
        ),
        CLOSEOUT_DOC: (
            "layer3_response_contract.py",
            "Response envelope extraction",
            "PR #562 response envelope extraction proof",
            "Merged main head after PR #562: 369e4131.",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing response contract extraction doc term: {term}")


def _check_workbench_error_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(WORKBENCH_ERROR_SERVICE, errors)
    for term in (
        "class Layer3WorkbenchError(ValueError):",
        "def workbench_error_response(",
        'base_response("layer3.workbench_error.v1"',
        '"error_code": exc.error_code',
        '"blocked_fields": list(exc.blocked_fields)',
        '"next_allowed_actions": list(exc.next_allowed_actions)',
    ):
        if term not in service_text:
            errors.append(f"{_rel(WORKBENCH_ERROR_SERVICE)} missing workbench error term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_workbench_error import Layer3WorkbenchError",
        "raise Layer3WorkbenchError",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing workbench error extraction term: {term}")
    for stale_term in (
        "class Layer3WorkbenchError(ValueError):",
        "def workbench_error_response(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns workbench error term: {stale_term}")

    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "from app.services.layer3_workbench_error import Layer3WorkbenchError, workbench_error_response",
        "content=workbench_error_response(exc)",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing workbench error extraction term: {term}")
    if "from app.services.layer3_workbench import Layer3WorkbenchError" in api_text:
        errors.append(f"{_rel(LAYER3_API)} still imports Layer3WorkbenchError from layer3_workbench")

    test_text = _read_required_text(LAYER3_WORKBENCH_ERROR_TEST, errors)
    for term in (
        "test_layer3_workbench_error_contract_is_shared_without_behavior_change",
        "Layer3WorkbenchError(",
        "workbench_error_response(exc, request_id=\"fixed-request\")",
        '"schema_id": "layer3.workbench_error.v1"',
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_WORKBENCH_ERROR_TEST)} missing workbench error test term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "workbench error extraction",
            "layer3_workbench_error.py",
            "test_layer3_workbench_error.py",
        ),
        GOAL_AUDIT: (
            "workbench error extraction",
            "layer3_workbench_error.py",
            "test_layer3_workbench_error.py",
            "PR #569 established `backend/app/services/layer3_workbench_error.py`",
            "5e09187e",
            "292 passed",
            "does not change emitted error envelopes",
        ),
        CLOSEOUT_DOC: (
            "workbench error extraction",
            "layer3_workbench_error.py",
            "layer3.workbench_error.v1",
            "PR #569 workbench error extraction proof",
            "Pre-merge PR #569 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #569: 5e09187e.",
            "Workbench error extraction keeps the shared error envelope outside the workbench without changing emitted error envelopes",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing workbench error extraction doc term: {term}")


def _check_plan_error_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(PLAN_ERROR_SERVICE, errors)
    for term in (
        "def plan_preview_workbench_error(",
        "def plan_approval_workbench_error(",
        "Layer3PassEntryError",
        "Layer3WorkbenchError",
        '"operator_confirmation_required"',
        'blocked_fields=["operator_confirmation"]',
        'next_allowed_actions=["confirm_plan_approval"]',
    ):
        if term not in service_text:
            errors.append(f"{_rel(PLAN_ERROR_SERVICE)} missing plan-error extraction term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_plan_errors import plan_approval_workbench_error, plan_preview_workbench_error",
        "raise plan_preview_workbench_error(exc) from exc",
        "raise plan_approval_workbench_error(exc) from exc",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing plan-error extraction delegation term: {term}")
    readiness_text = _read_required_text(PLAN_FLOW_READINESS_SERVICE, errors)
    if "blocked_reason = plan_preview_workbench_error(exc).error_code" not in readiness_text:
        errors.append(
            f"{_rel(PLAN_FLOW_READINESS_SERVICE)} missing plan-error extraction delegation term: "
            "blocked_reason = plan_preview_workbench_error(exc).error_code"
        )
    for stale_term in (
        "def _plan_preview_error(",
        "def _plan_approval_error(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns plan-error extraction term: {stale_term}")

    test_text = _read_required_text(LAYER3_PLAN_ERROR_TEST, errors)
    for term in (
        "test_plan_preview_workbench_error_mapping_is_preserved",
        "test_plan_approval_workbench_error_mapping_is_preserved",
        "owner_service_error",
        "operator_confirmation_required",
        "pass_runs_already_exist",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_PLAN_ERROR_TEST)} missing plan-error extraction proof term: {term}")

    board_text = _read_required_text(BOARD, errors)
    for term in (
        "PR `#624`",
        "f4b3ab80",
        "layer3_plan_errors.py",
        "test_layer3_plan_errors.py",
        "| Plan error mapping extraction | current-main no-behavior-change refactor/proof |",
        "PR `#624`, commit `f4b3ab80`",
        "without changing emitted error codes, statuses, HTTP statuses, blocked fields, or next allowed actions",
        "no-behavior-change plan preview/approval error-mapping extraction proof",
        "does not admit route, DTO, model, migration, UI, execution, package, connector, provider, source, qualitative/RAG, mockup, or auth/security behavior",
    ):
        if term not in board_text:
            errors.append(f"{_rel(BOARD)} missing plan-error extraction board term: {term}")


def _check_execution_error_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(EXECUTION_ERROR_SERVICE, errors)
    for term in (
        "def analysis_execution_start_workbench_error(",
        "Layer3PassEntryError | Layer3QualApsExecutionError",
        "Layer3WorkbenchError(",
        '"analysis_execution_start_not_admitted"',
        'status="conflict"',
        "http_status=409",
    ):
        if term not in service_text:
            errors.append(f"{_rel(EXECUTION_ERROR_SERVICE)} missing execution-error extraction term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_execution_errors import analysis_execution_start_workbench_error",
        "raise analysis_execution_start_workbench_error(exc) from exc",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing execution-error extraction delegation term: {term}")
    stale_block = (
        'Layer3WorkbenchError(\n'
        '            "analysis_execution_start_not_admitted",\n'
        "            str(exc),\n"
        '            status="conflict",\n'
        "            http_status=409,\n"
        "        )"
    )
    if stale_block in workbench_text:
        errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns analysis execution start error mapping")

    test_text = _read_required_text(LAYER3_EXECUTION_ERROR_TEST, errors)
    for term in (
        "test_analysis_execution_start_maps_pass_entry_error_without_behavior_change",
        "test_analysis_execution_start_maps_qual_aps_error_without_behavior_change",
        "analysis_execution_start_not_admitted",
        "pass entry blocked",
        "qualitative pass blocked",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_EXECUTION_ERROR_TEST)} missing execution-error extraction proof term: {term}")

    board_text = _read_required_text(BOARD, errors)
    for term in (
        "PR `#628`",
        "ca8831df",
        "layer3_execution_errors.py",
        "test_layer3_execution_errors.py",
        "| Analysis execution-start error mapping extraction | current-main no-behavior-change refactor/proof |",
        "PR `#628`, commit `ca8831df`",
        "without changing emitted error code, status, HTTP status, recoverability defaults, blocked fields, or next allowed actions",
        "no-behavior-change analysis execution-start error-mapping extraction proof",
        "does not admit new execution behavior, broad qualitative/RAG behavior, route, DTO, model, migration, UI, package, connector, provider, source, mockup, or auth/security behavior",
    ):
        if term not in board_text:
            errors.append(f"{_rel(BOARD)} missing execution-error extraction board term: {term}")


def _check_authority_rail_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(AUTHORITY_RAIL_SERVICE, errors)
    for term in (
        'DEFAULT_DOWNSTREAM_UNAVAILABLE = ("plan", "execution", "results", "package")',
        "def authority_rail(",
        '"schema_id": "layer3.authority_rail.v1"',
        '"schema_version": LAYER3_SCHEMA_VERSION',
        '"downstream_unavailable": list(downstream_unavailable or DEFAULT_DOWNSTREAM_UNAVAILABLE)',
    ):
        if term not in service_text:
            errors.append(f"{_rel(AUTHORITY_RAIL_SERVICE)} missing authority rail term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    import_term = "from app.services.layer3_authority_rail import authority_rail as _authority_rail"
    if import_term not in workbench_text:
        errors.append(f"{_rel(WORKBENCH_SERVICE)} missing authority rail extraction import")
    if "def _authority_rail(" in workbench_text:
        errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns _authority_rail instead of importing it")

    test_text = _read_required_text(LAYER3_AUTHORITY_RAIL_TEST, errors)
    for term in (
        "test_layer3_authority_rail_contract_is_shared_without_behavior_change",
        'bootstrap_rail = layer3_workbench.bootstrap()["authority_rail"]',
        'assert bootstrap_rail["schema_version"] == LAYER3_SCHEMA_VERSION',
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_AUTHORITY_RAIL_TEST)} missing authority rail test term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "authority rail extraction",
            "layer3_authority_rail.py",
            "test_layer3_authority_rail.py",
        ),
        GOAL_AUDIT: (
            "authority rail extraction",
            "layer3_authority_rail.py",
            "PR #564 established `backend/app/services/layer3_authority_rail.py`",
            "3418d429",
            "289 passed",
        ),
        CLOSEOUT_DOC: (
            "authority rail extraction",
            "layer3_authority_rail.py",
            "layer3.authority_rail.v1",
            "PR #564 authority rail extraction proof",
            "Merged main head after PR #564: 3418d429.",
            "Focused authority-rail/response/workbench/API suite: 146 passed, 5 warnings.",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing authority rail extraction doc term: {term}")


def _check_preview_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(PREVIEW_CONTRACT_SERVICE, errors)
    for term in (
        'PLAN_PREVIEW_IDENTITY_SCHEMA_ID = "layer3.plan_preview_identity.v1"',
        'MATERIAL_PREVIEW_HASH_SCHEMA_ID = "layer3.material_preview_hash.v1"',
        "def plan_preview_hash_contract(",
        '"owner_service_plan_version"',
        '"query_basis"',
        '"source_identity"',
        '"source_provenance"',
        '"payload"',
        '"load_summary"',
        '"supplied_hash_required_current_slice": False',
        "def preview_identity(",
        '"stale_preview_writes_blocked": True',
    ):
        if term not in service_text:
            errors.append(f"{_rel(PREVIEW_CONTRACT_SERVICE)} missing preview contract term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_preview_contract import",
        "plan_preview_hash_contract as _plan_preview_hash_contract",
        "preview_identity as _preview_identity",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing preview contract extraction import term: {term}")
    for stale_term in (
        "def _plan_preview_hash_contract(",
        "def _material_preview_hash_contract(",
        "def _preview_identity(",
        "PLAN_PREVIEW_HASH_INCLUDED_INPUTS = (",
        "MATERIAL_PREVIEW_HASH_INCLUDED_INPUTS = (",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns preview contract term: {stale_term}")

    test_text = _read_required_text(LAYER3_PREVIEW_CONTRACT_TEST, errors)
    for term in (
        "test_layer3_preview_contracts_are_shared_without_behavior_change",
        "readiness = layer3_workbench.readiness_contract()",
        'assert readiness["preview_hash_contract"] == plan_contract',
        'assert readiness["material_preview_hash_contract"] == material_contract',
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_PREVIEW_CONTRACT_TEST)} missing preview contract test term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "preview hash/identity contract extraction",
            "layer3_preview_contract.py",
            "test_layer3_preview_contract.py",
        ),
        GOAL_AUDIT: (
            "preview hash/identity contract extraction",
            "layer3_preview_contract.py",
            "PR #566 established `backend/app/services/layer3_preview_contract.py`",
            "ac367350",
            "290 passed",
        ),
        CLOSEOUT_DOC: (
            "preview hash/identity contract extraction",
            "layer3_preview_contract.py",
            "preview identity envelopes",
            "PR #566 preview hash/identity contract extraction proof",
            "Merged main head after PR #566: ac367350.",
            "Focused preview-contract/authority-rail/response/workbench/API suite: 147 passed, 5 warnings.",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing preview contract extraction doc term: {term}")


def _check_readiness_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(READINESS_CONTRACT_SERVICE, errors)
    for term in (
        'EXECUTION_READINESS_SCHEMA_ID = "layer3.execution_readiness_contract.v1"',
        "READINESS_REQUIRED_GATES = (",
        "READINESS_IMPLEMENTED_GATES = (",
        "READINESS_DEFERRED_GATES = (",
        "def build_readiness_contract(",
        "plan_preview_hash_contract()",
        "material_preview_hash_contract()",
        '"dispatch_admitted": False',
        '"source_breadth": "requires later freeze before RAG/vector/upload/local-directory expansion"',
    ):
        if term not in service_text:
            errors.append(f"{_rel(READINESS_CONTRACT_SERVICE)} missing readiness contract term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_readiness_contract import",
        "build_readiness_contract",
        "def readiness_contract(",
        "return build_readiness_contract(",
        "state_model=_workbench_state_model()",
        "state_action_contract=_workbench_state_action_contract()",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing readiness contract extraction term: {term}")
    for stale_term in (
        "READINESS_REQUIRED_GATES = (",
        "READINESS_IMPLEMENTED_GATES = (",
        "READINESS_DEFERRED_GATES = (",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns readiness contract term: {stale_term}")

    test_text = _read_required_text(LAYER3_READINESS_CONTRACT_TEST, errors)
    for term in (
        "test_layer3_readiness_contract_is_shared",
        "build_readiness_contract(",
        "direct_body == workbench_body",
        'assert direct["dispatch_admitted"] is False',
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_READINESS_CONTRACT_TEST)} missing readiness contract test term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "readiness contract extraction",
            "layer3_readiness_contract.py",
            "test_layer3_readiness_contract.py",
        ),
        GOAL_AUDIT: (
            "readiness contract extraction",
            "layer3_readiness_contract.py",
            "test_layer3_readiness_contract.py",
            "PR #568 established `backend/app/services/layer3_readiness_contract.py`",
            "6b1a12f0",
            "291 passed",
            "does not change emitted readiness contracts",
        ),
        CLOSEOUT_DOC: (
            "readiness contract extraction",
            "layer3_readiness_contract.py",
            "layer3.execution_readiness_contract.v1",
            "PR #568 readiness contract extraction proof",
            "Pre-merge PR #568 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #568: 6b1a12f0.",
            "Readiness contract extraction keeps the shared readiness contract outside the workbench without changing emitted readiness envelopes",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing readiness contract extraction doc term: {term}")


def _check_bootstrap_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(BOOTSTRAP_CONTRACT_SERVICE, errors)
    for term in (
        'BOOTSTRAP_SCHEMA_ID = "layer3.workbench_bootstrap.v1"',
        "BOOTSTRAP_FEATURE_FLAGS",
        "def build_bootstrap_contract(",
        '"single_aps_doc_qualitative_execution": True',
        '"broad_qualitative_execution": False',
        '"rag_vector_retrieval": False',
        '"dispatch": False',
        '"dispatch_admitted": False',
        '"readiness_endpoint": f"{api_root}/readiness"',
    ):
        if term not in service_text:
            errors.append(f"{_rel(BOOTSTRAP_CONTRACT_SERVICE)} missing bootstrap contract term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_bootstrap_contract import build_bootstrap_contract",
        "def bootstrap(",
        "return build_bootstrap_contract(",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing bootstrap contract extraction term: {term}")
    if '**_base_response("layer3.workbench_bootstrap.v1")' in workbench_text:
        errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns bootstrap base response literal")

    test_text = _read_required_text(LAYER3_BOOTSTRAP_CONTRACT_TEST, errors)
    for term in (
        "test_layer3_bootstrap_contract_is_shared",
        "build_bootstrap_contract(",
        "direct_body == workbench_body",
        'direct_body["features"]["broad_qualitative_execution"] is False',
        'direct_body["execution_readiness"]["dispatch_admitted"] is False',
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_BOOTSTRAP_CONTRACT_TEST)} missing bootstrap contract test term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "bootstrap contract extraction",
            "layer3_bootstrap_contract.py",
            "test_layer3_bootstrap_contract.py",
        ),
        GOAL_AUDIT: (
            "bootstrap contract extraction",
            "layer3_bootstrap_contract.py",
            "test_layer3_bootstrap_contract.py",
            "PR #571 established `backend/app/services/layer3_bootstrap_contract.py`",
            "bootstrap contract extraction proof merged after PR #571",
            "293 passed",
            "does not change emitted bootstrap envelopes",
        ),
        CLOSEOUT_DOC: (
            "bootstrap contract extraction",
            "layer3_bootstrap_contract.py",
            "layer3.workbench_bootstrap.v1",
            "PR #571 bootstrap contract extraction proof",
            "Bootstrap contract extraction focused proof",
            "Focused bootstrap-contract suite: 1 passed.",
            "Local focused Layer 3 backend suite: 293 passed, 4 warnings.",
            "Post-merge full Layer 3 backend suite: 293 passed, 4 warnings.",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing bootstrap contract extraction doc term: {term}")


def _check_state_model_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(STATE_MODEL_CONTRACT_SERVICE, errors)
    for term in (
        'STATE_MODEL_SCHEMA_ID = "layer3.workbench_state_model.v1"',
        "def build_workbench_state_model(",
        '\"authority_order\": [',
        '\"states\": [',
        '_state(state_names, "EXECUTION_SELECTION_STATE")',
        '_state(state_names, "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_READY_STATE")',
        '\"execution_readiness_blocked\"',
    ):
        if term not in service_text:
            errors.append(f"{_rel(STATE_MODEL_CONTRACT_SERVICE)} missing state-model contract term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_state_model_contract import build_workbench_state_model",
        "WORKBENCH_STATE_MODEL_STATE_NAMES",
        "def _workbench_state_model(",
        "return build_workbench_state_model(state_names=WORKBENCH_STATE_MODEL_STATE_NAMES)",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing state-model contract extraction term: {term}")
    if 'STATE_MODEL_SCHEMA_ID = "layer3.workbench_state_model.v1"' in workbench_text:
        errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns state-model schema id literal")

    test_text = _read_required_text(LAYER3_STATE_MODEL_CONTRACT_TEST, errors)
    for term in (
        "test_layer3_state_model_contract_is_shared",
        "build_workbench_state_model(",
        "direct_state_model == readiness_state_model",
        'readiness_state_model["schema_id"] == STATE_MODEL_SCHEMA_ID',
        '"external_export_download_delivery_ready"',
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_STATE_MODEL_CONTRACT_TEST)} missing state-model contract test term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "state-model contract extraction",
            "layer3_state_model_contract.py",
            "test_layer3_state_model_contract.py",
        ),
        GOAL_AUDIT: (
            "state-model contract extraction",
            "layer3_state_model_contract.py",
            "test_layer3_state_model_contract.py",
            "PR #573 established `backend/app/services/layer3_state_model_contract.py`",
            "state-model contract extraction proof merged after PR #573",
            "current-main proof with `294 passed, 4 warnings`",
            "does not change emitted state models",
        ),
        CLOSEOUT_DOC: (
            "PR #573 state-model contract extraction proof",
            "layer3_state_model_contract.py",
            "layer3.workbench_state_model.v1",
            "proof_snapshot_head: `f1cba09a84a47d0095a7fd682b835316ebde5496`",
            "State-model contract extraction focused proof",
            "Focused state-model-contract suite: 1 passed.",
            "Local focused Layer 3 backend suite: 294 passed, 4 warnings.",
            "Post-merge full Layer 3 backend suite: 294 passed, 4 warnings.",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing state-model contract extraction doc term: {term}")


def _check_execution_request_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(EXECUTION_REQUEST_CONTRACT_SERVICE, errors)
    for term in (
        "ANALYSIS_EXECUTION_START_ALLOWED_FIELDS = frozenset(",
        "ANALYSIS_EXECUTION_START_FORBIDDEN_FIELDS = frozenset(",
        "EXECUTION_RESULT_STATUS_ALLOWED_FIELDS = frozenset(",
        "EXECUTION_RESULT_STATUS_FORBIDDEN_FIELDS = frozenset(",
        "EXECUTION_RESULT_REVIEW_ALLOWED_FIELDS = frozenset(",
        "EXECUTION_RESULT_REVIEW_FORBIDDEN_FIELDS = frozenset(",
        "def analysis_execution_start_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        "def execution_result_status_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        "def execution_result_review_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        '"run_all"',
        '"result_review"',
        '"package_review"',
        '"source_expansion"',
    ):
        if term not in service_text:
            errors.append(f"{_rel(EXECUTION_REQUEST_CONTRACT_SERVICE)} missing execution request contract term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_execution_request_contract import (",
        "ANALYSIS_EXECUTION_START_ALLOWED_FIELDS",
        "EXECUTION_RESULT_STATUS_FORBIDDEN_FIELDS",
        "EXECUTION_RESULT_REVIEW_FORBIDDEN_FIELDS",
        "blocked_payload_fields = analysis_execution_start_blocked_fields(payload)",
        "blocked_payload_fields = execution_result_status_blocked_fields(payload)",
        "blocked_payload_fields = execution_result_review_blocked_fields(payload)",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing execution request contract extraction term: {term}")
    for stale_term in (
        "ANALYSIS_EXECUTION_START_FORBIDDEN_FIELDS = frozenset(",
        "ANALYSIS_EXECUTION_START_ALLOWED_FIELDS = frozenset(",
        "EXECUTION_RESULT_STATUS_FORBIDDEN_FIELDS = frozenset(",
        "EXECUTION_RESULT_STATUS_ALLOWED_FIELDS = frozenset(",
        "EXECUTION_RESULT_REVIEW_FORBIDDEN_FIELDS = frozenset(",
        "EXECUTION_RESULT_REVIEW_ALLOWED_FIELDS = frozenset(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns execution request contract term: {stale_term}")

    test_text = _read_required_text(LAYER3_EXECUTION_REQUEST_CONTRACT_TEST, errors)
    for term in (
        "test_execution_request_contract_is_shared_without_behavior_change",
        "test_execution_request_contract_blocks_same_fields_as_legacy_logic",
        "layer3_workbench.ANALYSIS_EXECUTION_START_ALLOWED_FIELDS",
        "contract.analysis_execution_start_blocked_fields(start_payload)",
        "contract.execution_result_status_blocked_fields(status_payload)",
        "contract.execution_result_review_blocked_fields(review_payload)",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_EXECUTION_REQUEST_CONTRACT_TEST)} missing execution request contract test term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "execution request/result contract extraction",
            "layer3_execution_request_contract.py",
            "test_layer3_execution_request_contract.py",
        ),
        GOAL_AUDIT: (
            "PR #582 execution request/result contract extraction",
            "layer3_execution_request_contract.py",
            "test_layer3_execution_request_contract.py",
            "PR #582 established `backend/app/services/layer3_execution_request_contract.py`",
            "execution request/result contract extraction proof merged after PR #582",
            "with `302 passed, 4 warnings` current-main proof",
            "does not change analysis execution start, execution result status, or execution result review allowlists, denylists, blocked-field behavior, emitted execution responses, or any deferred broad capability",
        ),
        CLOSEOUT_DOC: (
            "PR #582 execution request/result contract extraction proof",
            "layer3_execution_request_contract.py",
            "test_layer3_execution_request_contract.py",
            "proof_snapshot_head: `f1cba09a84a47d0095a7fd682b835316ebde5496`",
            "Focused execution-request-contract suite: 2 passed.",
            "Focused execution request API regression: 11 passed, 118 deselected, 4 warnings.",
            "Local focused Layer 3 backend suite: 302 passed, 4 warnings.",
            "Pre-merge PR #582 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #582: 5391af4e.",
            "Post-merge full Layer 3 backend suite: 302 passed, 4 warnings.",
            "proof/refactor hardening through PR #607",
            "No broad execution, package mutation/reconstruction, package payload rewrite, source widening, connector/destination dispatch, provider/public URL support, broad qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior is admitted.",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing execution request contract extraction doc term: {term}")


def _check_plan_flow_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(PLAN_FLOW_CONTRACT_SERVICE, errors)
    for term in (
        "PLAN_APPROVAL_FORBIDDEN_FIELDS = frozenset(",
        "PLAN_REVISION_FORBIDDEN_FIELDS = PLAN_APPROVAL_FORBIDDEN_FIELDS | frozenset(",
        "EXECUTION_SELECTION_FORBIDDEN_FIELDS = frozenset(",
        "def plan_approval_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        "def plan_revision_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        "def execution_selection_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        "def source_classes_from_plan_preview(plan_preview: Mapping[str, Any]) -> list[str]:",
        "def approved_set_payload(item: Mapping[str, Any]) -> dict[str, Any]:",
        "def approved_planned_pass_payload(item: Mapping[str, Any]) -> dict[str, Any]:",
        '"llm_plan"',
        '"create_pass_runs"',
        '"start_execution"',
        '"local_upload"',
    ):
        if term not in service_text:
            errors.append(f"{_rel(PLAN_FLOW_CONTRACT_SERVICE)} missing plan-flow contract term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_plan_flow_contract import (",
        "PLAN_APPROVAL_FORBIDDEN_FIELDS",
        "PLAN_REVISION_FORBIDDEN_FIELDS",
        "EXECUTION_SELECTION_FORBIDDEN_FIELDS",
        "forbidden = plan_approval_blocked_fields(payload)",
        "forbidden = plan_revision_blocked_fields(payload)",
        "forbidden = execution_selection_blocked_fields(payload)",
        "source_classes_from_plan_preview as _source_classes_from_plan_preview",
        "approved_set_payload as _approved_set_payload",
        "approved_planned_pass_payload as _approved_planned_pass_payload",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing plan-flow contract extraction term: {term}")
    for stale_term in (
        "PLAN_APPROVAL_FORBIDDEN_FIELDS = frozenset(",
        "PLAN_REVISION_FORBIDDEN_FIELDS = PLAN_APPROVAL_FORBIDDEN_FIELDS | frozenset(",
        "EXECUTION_SELECTION_FORBIDDEN_FIELDS = frozenset(",
        "def _source_classes_from_plan_preview(",
        "def _approved_set_payload(",
        "def _approved_planned_pass_payload(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns plan-flow contract term: {stale_term}")

    test_text = _read_required_text(LAYER3_PLAN_FLOW_CONTRACT_TEST, errors)
    for term in (
        "test_plan_flow_contract_is_shared",
        "test_plan_flow_contract_blocks_same_fields_as_legacy_logic",
        "layer3_workbench.PLAN_APPROVAL_FORBIDDEN_FIELDS",
        "contract.plan_approval_blocked_fields(approval_payload)",
        "contract.plan_revision_blocked_fields(revision_payload)",
        "contract.execution_selection_blocked_fields(selection_payload)",
        "test_source_classes_from_plan_preview_preserves_workbench_authority_ordering",
        "test_workbench_delegates_plan_preview_source_classes_to_contract",
        "test_approved_plan_payload_helpers_clone_and_mark_approval_state",
        "test_workbench_delegates_approved_plan_payload_helpers_to_contract",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_PLAN_FLOW_CONTRACT_TEST)} missing plan-flow contract test term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "scoped live proof for the no-behavior-change plan-flow request contract extraction added by PR #584",
            "layer3_plan_flow_contract.py",
            "test_layer3_plan_flow_contract.py",
            "does not change plan approval, plan revision, or execution selection blocked-field behavior",
        ),
        GOAL_AUDIT: (
            "PR #584 plan-flow request contract extraction",
            "layer3_plan_flow_contract.py",
            "test_layer3_plan_flow_contract.py",
            "PR #584 established `backend/app/services/layer3_plan_flow_contract.py`",
            "plan-flow request contract extraction proof merged after PR #584",
            "with `304 passed, 4 warnings` current-main proof",
            "does not change plan approval, plan revision, or execution selection forbidden-field contracts, blocked-field behavior, emitted plan-flow responses, execution behavior, or any deferred broad capability",
        ),
        CLOSEOUT_DOC: (
            "PR #584 plan-flow request contract extraction proof",
            "layer3_plan_flow_contract.py",
            "test_layer3_plan_flow_contract.py",
            "proof_snapshot_head: `f1cba09a84a47d0095a7fd682b835316ebde5496`",
            "Focused plan-flow-contract suite: 2 passed.",
            "Focused plan-flow API regression: 3 passed, 124 deselected, 3 warnings.",
            "Local focused Layer 3 backend suite: 304 passed, 4 warnings.",
            "Pre-merge PR #584 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #584: 9cdd1e88.",
            "Post-merge full Layer 3 backend suite: 304 passed, 4 warnings.",
            "proof/refactor hardening through PR #607",
            "No broad execution, package mutation/reconstruction, package payload rewrite, source widening, connector/destination dispatch, provider/public URL support, broad qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior is admitted.",
        ),
        MANIFEST: (
            "PR #584/commit 9cdd1e88 as no-behavior-change plan-flow request contract extraction proof",
            "merged_live_bounded_plan_flow_request_contract_extraction",
            "merged_live_plan_preview_source_class_extraction",
            "merged_live_approved_plan_payload_projection_extraction",
            "merged_live_plan_flow_state_lookup_extraction",
            "PR #635 as a no-behavior-change plan-preview source-class extraction",
            "PR #636 as a no-behavior-change approved-plan payload projection extraction",
            "PR #637 as a no-behavior-change plan-flow state lookup extraction",
            "source_classes_from_plan_preview",
            "approved_set_payload",
            "approved_planned_pass_payload",
            "layer3_plan_flow_state.py",
            "Post-PR584 sync: local git verified project6-origin/main at 9cdd1e88593d21e269d00dda50eae98ab852d219",
            "Post-PR584 current-main progress/proof sync",
            "does not admit broad execution, package mutation/reconstruction, package payload rewrite, source widening, connector/destination dispatch, provider/public URL support, broad qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior",
        ),
        BOARD: (
            "Plan-flow request contract extraction",
            "PR `#584`/commit `9cdd1e88`",
            "PR `#635` extends the same no-behavior-change plan-flow contract extraction posture",
            "PR `#636` continues the no-behavior-change plan-flow extraction posture",
            "PR `#637` adds no-behavior-change plan-flow state lookup extraction proof",
            "_source_classes_from_plan_preview",
            "_approved_set_payload",
            "_approved_planned_pass_payload",
            "_latest_analysis_plan",
            "_plan_revision_control",
            "backend/app/services/layer3_plan_flow_contract.py",
            "backend/app/services/layer3_plan_flow_state.py",
            "merged live no-behavior-change refactor/proof",
            "full focused Layer 3 suite with `304 passed, 4 warnings`",
        ),
        PROOF_MANIFEST: (
            "no-behavior-change plan-flow request contract extraction proof from PR #584",
            "latest_plan_flow_request_contract_extraction_pr",
            "latest_plan_preview_source_class_extraction_pr",
            "latest_approved_plan_payload_projection_extraction_pr",
            "latest_plan_flow_state_lookup_extraction_pr",
            "PR #635 moves plan-preview source-class derivation",
            "PR #636 moves approved-plan set/pass payload projection",
            "PR #637 moves latest analysis-plan lookup ordering",
            "source_classes_from_plan_preview",
            "approved_set_payload",
            "approved_planned_pass_payload",
            "latest_analysis_plan",
            "plan_revision_control_for_session",
            "plan_flow_request_contract_extraction_current_boundary_proof",
            "9cdd1e88593d21e269d00dda50eae98ab852d219",
            "no-behavior-change plan-flow request contract extraction proof",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing plan-flow contract extraction doc term: {term}")


def _check_plan_flow_state_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(PLAN_FLOW_STATE_SERVICE, errors)
    for term in (
        "def latest_analysis_plan(db: Session, *, session_id: str) -> L3AnalysisPlan | None:",
        "def plan_revision_control_for_session(db: Session, *, session_id: str) -> dict[str, Any] | None:",
        "L3AnalysisPlan.created_at.desc(), L3AnalysisPlan.analysis_plan_id.asc()",
        "plan_revision_control_from_session(session)",
    ):
        if term not in service_text:
            errors.append(f"{_rel(PLAN_FLOW_STATE_SERVICE)} missing plan-flow state term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_plan_flow_state import (",
        "latest_analysis_plan as _latest_analysis_plan",
        "plan_revision_control_for_session as _plan_revision_control",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing plan-flow state delegation term: {term}")
    for stale_term in (
        "def _latest_analysis_plan(",
        "def _plan_revision_control(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns plan-flow state term: {stale_term}")

    test_text = _read_required_text(LAYER3_PLAN_FLOW_STATE_TEST, errors)
    for term in (
        "test_latest_analysis_plan_preserves_workbench_ordering",
        "test_plan_revision_control_for_session_filters_recovery_state",
        "layer3_workbench._latest_analysis_plan",
        "layer3_workbench._plan_revision_control",
        "PLAN_REVISION_RECOVERY_STATE",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_PLAN_FLOW_STATE_TEST)} missing plan-flow state proof term: {term}")


def _check_plan_flow_readiness_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(PLAN_FLOW_READINESS_SERVICE, errors)
    for term in (
        "def plan_preview_readiness(",
        "def plan_approval_summary(db: Session, *, session_id: str) -> dict[str, Any]:",
        "def plan_revision_summary(db: Session, *, session_id: str) -> dict[str, Any]:",
        "preview_pass_entry(db, session_id=session_id)",
        "plan_revision_control_for_session(db, session_id=session_id)",
        "json_clone(cancellation) if cancellation is not None else None",
    ):
        if term not in service_text:
            errors.append(f"{_rel(PLAN_FLOW_READINESS_SERVICE)} missing plan-flow readiness term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_plan_flow_readiness import (",
        "plan_approval_summary as _plan_approval_summary",
        "plan_preview_readiness as _plan_preview_readiness",
        "plan_revision_summary as _plan_revision_summary",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing plan-flow readiness delegation term: {term}")
    for stale_term in (
        "def _plan_preview_readiness(",
        "def _plan_approval_summary(",
        "def _plan_revision_summary(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns plan-flow readiness term: {stale_term}")

    test_text = _read_required_text(LAYER3_PLAN_FLOW_READINESS_TEST, errors)
    for term in (
        "test_plan_preview_readiness_blocks_cancelled_plan_and_workbench_delegates",
        "test_plan_approval_summary_clones_cancel_state_and_workbench_delegates",
        "test_plan_revision_summary_uses_control_record_and_workbench_delegates",
        "layer3_workbench._plan_preview_readiness",
        "layer3_workbench._plan_approval_summary",
        "layer3_workbench._plan_revision_summary",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_PLAN_FLOW_READINESS_TEST)} missing plan-flow readiness proof term: {term}")

    for path, terms in {
        BOARD: (
            "plan-flow readiness summary extraction",
            "layer3_plan_flow_readiness.py",
            "test_layer3_plan_flow_readiness.py",
            "does not admit route, DTO, model, migration, UI, execution, package, connector",
        ),
        MANIFEST: (
            "plan_flow_readiness_summary_extraction_pr638",
            "plan-flow readiness summary extraction",
            "layer3_plan_flow_readiness.py",
            "test_layer3_plan_flow_readiness.py",
        ),
        PROOF_MANIFEST: (
            "latest_plan_flow_readiness_summary_extraction_branch",
            "latest_plan_flow_readiness_summary_extraction_live_behavior_change",
            "plan-flow readiness summary extraction",
            "backend/app/services/layer3_plan_flow_readiness.py",
            "backend/tests/test_layer3_plan_flow_readiness.py",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing plan-flow readiness extraction doc term: {term}")


def _check_sublayer_state_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(SUBLAYER_STATE_SERVICE, errors)
    for term in (
        "SUBLAYER_VISUALIZATION_STATE_SCHEMA_ID = \"layer3.sublayer_visualization_state.v1\"",
        "def snapshot_projection(",
        "def serialize_typing_record(",
        "def serialize_analysis_unit(",
        "def serialize_analysis_group(",
        "def serialize_analysis_set(",
        "def session_sublayer_visualization_state(db: Session, *, session_id: str) -> dict[str, Any]:",
        "\"authority_source\": \"read_only_persisted_layer3_rows\"",
        "\"no_side_effects\": True",
        "latest_analysis_plan(db, session_id=session_id)",
    ):
        if term not in service_text:
            errors.append(f"{_rel(SUBLAYER_STATE_SERVICE)} missing sublayer state extraction term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_sublayer_state import (",
        "serialize_analysis_group as _serialize_analysis_group",
        "serialize_analysis_set as _serialize_analysis_set",
        "serialize_analysis_unit as _serialize_analysis_unit",
        "serialize_typing_record as _serialize_typing_record",
        "session_sublayer_visualization_state as _session_sublayer_visualization_state",
        "snapshot_projection as _snapshot_projection",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing sublayer state delegation term: {term}")
    for stale_term in (
        "SUBLAYER_VISUALIZATION_STATE_SCHEMA_ID =",
        "def _snapshot_projection(",
        "def _serialize_typing_record(",
        "def _serialize_analysis_unit(",
        "def _serialize_analysis_group(",
        "def _serialize_analysis_set(",
        "def _session_sublayer_visualization_state(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns sublayer state term: {stale_term}")

    test_text = _read_required_text(LAYER3_SUBLAYER_STATE_TEST, errors)
    for term in (
        "test_snapshot_projection_reports_unsupported_shape_without_side_effects",
        "test_session_sublayer_visualization_state_preserves_workbench_projection",
        "layer3_workbench._snapshot_projection",
        "layer3_workbench._session_sublayer_visualization_state",
        "SUBLAYER_VISUALIZATION_STATE_SCHEMA_ID",
        "analysis-run-sublayer-state",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_SUBLAYER_STATE_TEST)} missing sublayer state proof term: {term}")

    for path, terms in {
        BOARD: (
            "sublayer visualization state extraction",
            "layer3_sublayer_state.py",
            "test_layer3_sublayer_state.py",
            "does not admit route, DTO, model, migration, UI, execution",
        ),
        MANIFEST: (
            "sublayer_visualization_state_extraction_pr",
            "sublayer visualization state extraction",
            "layer3_sublayer_state.py",
            "test_layer3_sublayer_state.py",
        ),
        PROOF_MANIFEST: (
            "latest_sublayer_visualization_state_extraction_branch",
            "latest_sublayer_visualization_state_extraction_live_behavior_change",
            "backend/app/services/layer3_sublayer_state.py",
            "backend/tests/test_layer3_sublayer_state.py",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing sublayer state extraction doc term: {term}")


def _check_execution_state_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(EXECUTION_STATE_SERVICE, errors)
    for term in (
        "EXECUTION_SELECTION_STATE_SCHEMA_ID = \"layer3.execution_selection_state.v1\"",
        "ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID = \"layer3.analysis_execution_start_state.v1\"",
        "def execution_selection_from_session(",
        "def execution_selection_pass_runs(db: Session, *, session_id: str) -> list[L3PassRun]:",
        "def pass_run_analysis_run_id(",
        "def pass_run_execution_started(",
        "def execution_state_for_pass_runs(",
        "def analysis_execution_start_from_pass_run(",
        "PASS_STATUS_SELECTED_NOT_STARTED",
    ):
        if term not in service_text:
            errors.append(f"{_rel(EXECUTION_STATE_SERVICE)} missing execution state extraction term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_execution_state import (",
        "analysis_execution_start_from_pass_run as _analysis_execution_start_from_pass_run",
        "execution_selection_from_session as _execution_selection_from_session",
        "execution_selection_pass_runs as _execution_selection_pass_runs",
        "execution_state_for_pass_runs as _execution_state_for_pass_runs",
        "pass_run_analysis_run_id as _pass_run_analysis_run_id",
        "pass_run_execution_started as _pass_run_execution_started",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing execution state delegation term: {term}")
    for stale_term in (
        "EXECUTION_SELECTION_STATE_SCHEMA_ID =",
        "ANALYSIS_EXECUTION_START_STATE_SCHEMA_ID =",
        "EXECUTION_PASS_RUNNING_STATE =",
        "def _execution_selection_from_session(",
        "def _execution_selection_pass_runs(",
        "def _pass_run_analysis_run_id(",
        "def _pass_run_execution_started(",
        "def _execution_state_for_pass_runs(",
        "def _analysis_execution_start_from_pass_run(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns execution state term: {stale_term}")

    test_text = _read_required_text(LAYER3_EXECUTION_STATE_TEST, errors)
    for term in (
        "test_execution_selection_from_session_preserves_workbench_projection",
        "test_pass_run_projection_helpers_preserve_existing_state_semantics",
        "test_analysis_execution_start_from_pass_run_preserves_workbench_projection",
        "test_execution_selection_pass_runs_orders_by_creation_then_id",
        "layer3_workbench._execution_state_for_pass_runs",
        "layer3_workbench._execution_selection_pass_runs",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_EXECUTION_STATE_TEST)} missing execution state proof term: {term}")

    for path, terms in {
        BOARD: (
            "execution state extraction",
            "layer3_execution_state.py",
            "test_layer3_execution_state.py",
            "does not admit route, DTO, model, migration, UI, execution behavior",
        ),
        MANIFEST: (
            "execution_state_extraction_pr",
            "execution state extraction",
            "layer3_execution_state.py",
            "test_layer3_execution_state.py",
        ),
        PROOF_MANIFEST: (
            "latest_execution_state_extraction_branch",
            "latest_execution_state_extraction_live_behavior_change",
            "backend/app/services/layer3_execution_state.py",
            "backend/tests/test_layer3_execution_state.py",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing execution state extraction doc term: {term}")


def _check_execution_output_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(EXECUTION_OUTPUT_SERVICE, errors)
    for term in (
        "def output_metadata_summary(pass_run: L3PassRun) -> tuple[dict[str, Any] | None, str | None]:",
        "output_payload_ref_missing",
        "output_metadata_file_missing",
        "output_metadata_unreadable",
        "output_metadata_malformed",
        "artifact_refs_json",
        "source_dataset_version_ids_json",
        "chunk_summary",
    ):
        if term not in service_text:
            errors.append(f"{_rel(EXECUTION_OUTPUT_SERVICE)} missing execution output extraction term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_execution_output import output_metadata_summary as _output_metadata_summary",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing execution output delegation term: {term}")
    if "def _output_metadata_summary(" in workbench_text:
        errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns execution output metadata projection")

    test_text = _read_required_text(LAYER3_EXECUTION_OUTPUT_TEST, errors)
    for term in (
        "test_output_metadata_summary_preserves_missing_and_invalid_error_semantics",
        "test_output_metadata_summary_preserves_workbench_projection",
        "layer3_workbench._output_metadata_summary",
        "output_metadata_file_missing",
        "output_metadata_malformed",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_EXECUTION_OUTPUT_TEST)} missing execution output proof term: {term}")

    for path, terms in {
        BOARD: (
            "execution output metadata extraction",
            "layer3_execution_output.py",
            "test_layer3_execution_output.py",
            "does not admit route, DTO, model, migration, UI, execution behavior",
        ),
        MANIFEST: (
            "execution_output_metadata_extraction_pr",
            "execution output metadata extraction",
            "layer3_execution_output.py",
            "test_layer3_execution_output.py",
        ),
        PROOF_MANIFEST: (
            "latest_execution_output_metadata_extraction_branch",
            "latest_execution_output_metadata_extraction_live_behavior_change",
            "backend/app/services/layer3_execution_output.py",
            "backend/tests/test_layer3_execution_output.py",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing execution output extraction doc term: {term}")


def _check_execution_review_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(EXECUTION_REVIEW_SERVICE, errors)
    for term in (
        "EXECUTION_RESULT_REVIEW_STATE_SCHEMA_ID = \"layer3.execution_result_review_state.v1\"",
        "EXECUTION_RESULT_REVIEW_ITEM_TYPES = frozenset(",
        "def execution_result_review_from_pass_run(",
        "def normalize_result_review_items(",
        "reviewed_output_items_malformed",
        "reviewed_output_items_too_large",
        "def result_review_trace_summary(",
        "source_dataset_version_ids_json",
        "EXECUTION_RESULT_REVIEW_SCHEMA_ID = \"layer3.execution_result_review.v1\"",
        "EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE = (\"package\", \"handoff\", \"package_review\")",
        "def execution_result_review_response(",
        "base_response(EXECUTION_RESULT_REVIEW_SCHEMA_ID",
        "preview_identity(preview_id=preview_id, preview_hash=preview_hash)",
        "json_clone(review_state[\"trace_summary\"])",
    ):
        if term not in service_text:
            errors.append(f"{_rel(EXECUTION_REVIEW_SERVICE)} missing execution review extraction term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_execution_review import (",
        "execution_result_review_from_pass_run as _execution_result_review_from_pass_run",
        "normalize_result_review_items as _normalize_result_review_items",
        "result_review_trace_summary as _result_review_trace_summary",
        "EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE",
        "EXECUTION_RESULT_REVIEW_SCHEMA_ID",
        "execution_result_review_response as _execution_result_review_response",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing execution review delegation term: {term}")
    for stale_term in (
        "EXECUTION_RESULT_REVIEW_ITEM_TYPES = frozenset(",
        "def _execution_result_review_from_pass_run(",
        "def _normalize_result_review_items(",
        "def _result_review_trace_summary(",
        "EXECUTION_RESULT_REVIEW_SCHEMA_ID = \"layer3.execution_result_review.v1\"",
        "EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE = (\"package\", \"handoff\", \"package_review\")",
        "def _execution_result_review_response(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns execution review term: {stale_term}")

    test_text = _read_required_text(LAYER3_EXECUTION_REVIEW_TEST, errors)
    for term in (
        "test_execution_result_review_from_pass_run_preserves_workbench_projection",
        "test_normalize_result_review_items_preserves_trace_semantics",
        "test_normalize_result_review_items_preserves_fail_closed_errors",
        "test_result_review_trace_summary_preserves_workbench_projection",
        "test_execution_result_review_response_preserves_workbench_projection",
        "layer3_workbench._normalize_result_review_items",
        "layer3_workbench._execution_result_review_response",
        "reviewed_output_items_too_large",
        "EXECUTION_RESULT_REVIEW_DOWNSTREAM_UNAVAILABLE",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_EXECUTION_REVIEW_TEST)} missing execution review proof term: {term}")

    for path, terms in {
        BOARD: (
            "execution result-review extraction",
            "execution result-review response extraction",
            "layer3_execution_review.py",
            "test_layer3_execution_review.py",
            "does not admit route, DTO, model, migration, UI, execution behavior",
        ),
        MANIFEST: (
            "execution_result_review_extraction_pr",
            "execution_result_review_response_extraction_pr",
            "execution result-review extraction",
            "execution result-review response extraction",
            "layer3_execution_review.py",
            "test_layer3_execution_review.py",
        ),
        PROOF_MANIFEST: (
            "latest_execution_result_review_extraction_branch",
            "latest_execution_result_review_response_extraction_branch",
            "latest_execution_result_review_extraction_live_behavior_change",
            "latest_execution_result_review_response_extraction_live_behavior_change",
            "backend/app/services/layer3_execution_review.py",
            "backend/tests/test_layer3_execution_review.py",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing execution review extraction doc term: {term}")


def _check_execution_selection_summary_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(EXECUTION_SELECTION_SERVICE, errors)
    for term in (
        "EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE = (\"results\", \"package\", \"handoff\")",
        "def execution_selection_summary(db: Session, *, session_id: str) -> dict[str, Any]:",
        "execution_selection_from_session(session)",
        "execution_selection_pass_runs(db, session_id=session_id)",
        "plan_revision_control_for_session(db, session_id=session_id)",
        "PLAN_STATUS_APPROVED",
        "execution_selection_already_exists",
        "pass_runs_already_exist",
        "EXECUTION_SELECTION_SCHEMA_ID = \"layer3.execution_selection.v1\"",
        "def execution_selection_response(",
        "base_response(EXECUTION_SELECTION_SCHEMA_ID",
        "preview_identity(preview_id=preview_id, preview_hash=preview_hash)",
        "execution_state_for_pass_runs(pass_runs)",
    ):
        if term not in service_text:
            errors.append(f"{_rel(EXECUTION_SELECTION_SERVICE)} missing execution selection summary term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_execution_selection import (",
        "EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE",
        "EXECUTION_SELECTION_SCHEMA_ID",
        "execution_selection_response as _execution_selection_response",
        "execution_selection_summary as _execution_selection_summary",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing execution selection delegation term: {term}")
    for stale_term in (
        "EXECUTION_SELECTION_DOWNSTREAM_UNAVAILABLE = (\"results\", \"package\", \"handoff\")",
        "def _execution_selection_summary(",
        "def _execution_selection_response(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns execution selection summary term: {stale_term}")

    test_text = _read_required_text(LAYER3_EXECUTION_SELECTION_TEST, errors)
    for term in (
        "test_execution_selection_summary_reports_available_approved_plan",
        "test_execution_selection_summary_preserves_existing_selection_projection",
        "test_execution_selection_summary_preserves_blocked_reasons",
        "test_execution_selection_response_preserves_workbench_projection",
        "layer3_workbench._execution_selection_summary",
        "layer3_workbench._execution_selection_response",
        "EXECUTION_PASS_COMPLETED_STATE",
        "pass_runs_already_exist",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_EXECUTION_SELECTION_TEST)} missing execution selection summary proof term: {term}")

    for path, terms in {
        BOARD: (
            "execution selection summary extraction",
            "execution selection response extraction",
            "layer3_execution_selection.py",
            "test_layer3_execution_selection.py",
            "does not admit route, DTO, model, migration, UI, execution behavior",
        ),
        MANIFEST: (
            "execution_selection_summary_extraction_pr",
            "execution_selection_response_extraction_pr",
            "execution selection summary extraction",
            "execution selection response extraction",
            "layer3_execution_selection.py",
            "test_layer3_execution_selection.py",
        ),
        PROOF_MANIFEST: (
            "latest_execution_selection_summary_extraction_branch",
            "latest_execution_selection_response_extraction_branch",
            "latest_execution_selection_summary_extraction_live_behavior_change",
            "latest_execution_selection_response_extraction_live_behavior_change",
            "backend/app/services/layer3_execution_selection.py",
            "backend/tests/test_layer3_execution_selection.py",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing execution selection summary doc term: {term}")


def _check_execution_start_response_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(EXECUTION_START_SERVICE, errors)
    for term in (
        "ANALYSIS_EXECUTION_START_SCHEMA_ID = \"layer3.analysis_execution_start.v1\"",
        "ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE = (\"results\", \"package\", \"handoff\")",
        "def analysis_execution_start_response(",
        "base_response(ANALYSIS_EXECUTION_START_SCHEMA_ID",
        "preview_identity(preview_id=preview_id, preview_hash=preview_hash)",
        "pass_run_execution_started(pass_run)",
        "pass_run_analysis_run_id(pass_run)",
        "execution_state_for_pass_runs([pass_run])",
        "selected_method_name",
        "dataset_version_id",
    ):
        if term not in service_text:
            errors.append(f"{_rel(EXECUTION_START_SERVICE)} missing execution start response term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_execution_start import (",
        "ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE",
        "ANALYSIS_EXECUTION_START_SCHEMA_ID",
        "analysis_execution_start_response as _analysis_execution_start_response",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing execution start delegation term: {term}")
    for stale_term in (
        "ANALYSIS_EXECUTION_START_SCHEMA_ID = \"layer3.analysis_execution_start.v1\"",
        "ANALYSIS_EXECUTION_START_DOWNSTREAM_UNAVAILABLE = (\"results\", \"package\", \"handoff\")",
        "def _analysis_execution_start_response(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns execution start response term: {stale_term}")

    test_text = _read_required_text(LAYER3_EXECUTION_START_TEST, errors)
    for term in (
        "test_analysis_execution_start_response_preserves_workbench_projection",
        "layer3_workbench._analysis_execution_start_response",
        "EXECUTION_PASS_COMPLETED_STATE",
        "analysis-run-start-response",
        "payload://pass-run-start-response/output",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_EXECUTION_START_TEST)} missing execution start proof term: {term}")

    for path, terms in {
        BOARD: (
            "analysis execution-start response extraction",
            "layer3_execution_start.py",
            "test_layer3_execution_start.py",
            "does not admit route, DTO, model, migration, UI, execution behavior",
        ),
        MANIFEST: (
            "analysis_execution_start_response_extraction_pr",
            "analysis execution-start response extraction",
            "layer3_execution_start.py",
            "test_layer3_execution_start.py",
        ),
        PROOF_MANIFEST: (
            "latest_analysis_execution_start_response_extraction_branch",
            "latest_analysis_execution_start_response_extraction_live_behavior_change",
            "backend/app/services/layer3_execution_start.py",
            "backend/tests/test_layer3_execution_start.py",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing execution start response doc term: {term}")


def _check_execution_status_response_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(EXECUTION_STATUS_SERVICE, errors)
    for term in (
        "EXECUTION_RESULT_STATUS_SCHEMA_ID = \"layer3.execution_result_status.v1\"",
        "EXECUTION_RESULT_STATUS_DOWNSTREAM_UNAVAILABLE = (\"result_review\", \"package\", \"handoff\")",
        "def execution_result_status_response(",
        "base_response(EXECUTION_RESULT_STATUS_SCHEMA_ID",
        "analysis_execution_start_from_pass_run(pass_run)",
        "pass_run_analysis_run_id(pass_run)",
        "PASS_STATUS_COMPLETED_WITH_WARNINGS",
        "PASS_STATUS_FAILED",
        "EXECUTION_RESULT_STATUS_AVAILABLE_STATE",
        "EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE",
        "EXECUTION_RESULT_STATUS_BLOCKED_STATE",
        "operator_view_mode",
    ):
        if term not in service_text:
            errors.append(f"{_rel(EXECUTION_STATUS_SERVICE)} missing execution status response term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_execution_status import (",
        "EXECUTION_RESULT_STATUS_AVAILABLE_STATE",
        "EXECUTION_RESULT_STATUS_BLOCKED_STATE",
        "EXECUTION_RESULT_STATUS_DOWNSTREAM_UNAVAILABLE",
        "EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE",
        "EXECUTION_RESULT_STATUS_SCHEMA_ID",
        "execution_result_status_response as _execution_result_status_response",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing execution status delegation term: {term}")
    for stale_term in (
        "EXECUTION_RESULT_STATUS_SCHEMA_ID = \"layer3.execution_result_status.v1\"",
        "EXECUTION_RESULT_STATUS_AVAILABLE_STATE = \"execution_result_status_available\"",
        "EXECUTION_RESULT_STATUS_BLOCKED_STATE = \"execution_result_status_blocked\"",
        "EXECUTION_RESULT_STATUS_MISSING_OUTPUT_STATE = \"execution_result_status_missing_output\"",
        "EXECUTION_RESULT_STATUS_DOWNSTREAM_UNAVAILABLE = (\"result_review\", \"package\", \"handoff\")",
        "def _execution_result_status_response(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns execution status response term: {stale_term}")

    test_text = _read_required_text(LAYER3_EXECUTION_STATUS_TEST, errors)
    for term in (
        "test_execution_result_status_response_preserves_workbench_available_projection",
        "test_execution_result_status_response_preserves_failed_projection",
        "layer3_workbench._execution_result_status_response",
        "execution_result_status_available",
        "execution_result_status_blocked",
        "payload://pass-run-status-response/output",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_EXECUTION_STATUS_TEST)} missing execution status proof term: {term}")

    for path, terms in {
        BOARD: (
            "execution result/status response extraction",
            "layer3_execution_status.py",
            "test_layer3_execution_status.py",
            "does not admit route, DTO, model, migration, UI, execution behavior",
        ),
        MANIFEST: (
            "execution_result_status_response_extraction_pr",
            "execution result/status response extraction",
            "layer3_execution_status.py",
            "test_layer3_execution_status.py",
        ),
        PROOF_MANIFEST: (
            "latest_execution_result_status_response_extraction_branch",
            "latest_execution_result_status_response_extraction_live_behavior_change",
            "backend/app/services/layer3_execution_status.py",
            "backend/tests/test_layer3_execution_status.py",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing execution status response doc term: {term}")


def _check_handoff_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(HANDOFF_CONTRACT_SERVICE, errors)
    for term in (
        "HANDOFF_EXPORT_PREPARE_ALLOWED_FIELDS = frozenset(",
        "HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS = frozenset(",
        "APS_HANDOFF_DISPATCH_ALLOWED_FIELDS = frozenset(",
        "APS_HANDOFF_DISPATCH_FORBIDDEN_FIELDS = frozenset(",
        "def handoff_export_prepare_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        "def aps_handoff_dispatch_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        '"connector_dispatch"',
        '"source_expansion"',
        '"local_upload"',
        '"schema_migration"',
    ):
        if term not in service_text:
            errors.append(f"{_rel(HANDOFF_CONTRACT_SERVICE)} missing handoff contract term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_handoff_contract import (",
        "HANDOFF_EXPORT_PREPARE_ALLOWED_FIELDS",
        "APS_HANDOFF_DISPATCH_FORBIDDEN_FIELDS",
        "blocked_payload_fields = handoff_export_prepare_blocked_fields(payload)",
        "blocked_payload_fields = aps_handoff_dispatch_blocked_fields(payload)",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing handoff contract extraction term: {term}")
    for stale_term in (
        "HANDOFF_EXPORT_PREPARE_FORBIDDEN_FIELDS = frozenset(",
        "HANDOFF_EXPORT_PREPARE_ALLOWED_FIELDS = frozenset(",
        "APS_HANDOFF_DISPATCH_FORBIDDEN_FIELDS = frozenset(",
        "APS_HANDOFF_DISPATCH_ALLOWED_FIELDS = frozenset(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns handoff contract term: {stale_term}")

    test_text = _read_required_text(LAYER3_HANDOFF_CONTRACT_TEST, errors)
    for term in (
        "test_handoff_contract_is_shared_without_behavior_change",
        "test_handoff_contract_blocks_same_fields_as_legacy_logic",
        "layer3_workbench.HANDOFF_EXPORT_PREPARE_ALLOWED_FIELDS",
        "contract.handoff_export_prepare_blocked_fields(prepare_payload)",
        "contract.aps_handoff_dispatch_blocked_fields(dispatch_payload)",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_HANDOFF_CONTRACT_TEST)} missing handoff contract test term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "handoff/export and APS handoff contract extraction",
            "layer3_handoff_contract.py",
            "test_layer3_handoff_contract.py",
        ),
        GOAL_AUDIT: (
            "PR #578 handoff/export and APS handoff contract extraction",
            "layer3_handoff_contract.py",
            "test_layer3_handoff_contract.py",
            "PR #578 established `backend/app/services/layer3_handoff_contract.py`",
            "handoff/export and APS handoff contract extraction proof merged after PR #578",
            "does not change handoff/export or APS handoff allowlists, denylists, blocked-field behavior, emitted handoff/export responses, emitted APS handoff responses, or any deferred broad capability",
        ),
        CLOSEOUT_DOC: (
            "PR #578 handoff/export and APS handoff contract extraction proof",
            "layer3_handoff_contract.py",
            "test_layer3_handoff_contract.py",
            "proof_snapshot_head: `f1cba09a84a47d0095a7fd682b835316ebde5496`",
            "Focused handoff-contract suite: 2 passed.",
            "Focused handoff API regression: 18 passed, 111 deselected, 4 warnings.",
            "Local focused Layer 3 backend suite: 298 passed, 4 warnings.",
            "Pre-merge PR #578 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #578: df2a5c14.",
            "Post-merge full Layer 3 backend suite: 298 passed, 4 warnings.",
            "proof/refactor hardening through PR #607",
            "No broad `layer3_workbench.py` rewrite and no behavior change beyond extracted ownership.",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing handoff contract extraction doc term: {term}")


def _check_package_review_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(PACKAGE_REVIEW_CONTRACT_SERVICE, errors)
    for term in (
        "PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS = frozenset(",
        "PACKAGE_REVIEW_PREVIEW_FORBIDDEN_FIELDS = frozenset(",
        "PACKAGE_CONSTRUCTION_COMMIT_ALLOWED_FIELDS = frozenset(",
        "PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS = frozenset(",
        "PACKAGE_REVIEW_SUBMIT_ALLOWED_FIELDS = frozenset(",
        "PACKAGE_REVIEW_SUBMIT_FORBIDDEN_FIELDS = frozenset(",
        "def package_review_preview_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        "def package_construction_commit_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        "def package_review_submit_blocked_fields(payload: Mapping[str, Any]) -> list[str]:",
        '"package_payload"',
        '"source_expansion"',
        '"local_upload"',
        '"schema_migration"',
    ):
        if term not in service_text:
            errors.append(f"{_rel(PACKAGE_REVIEW_CONTRACT_SERVICE)} missing package review contract term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_package_review_contract import (",
        "from app.services.layer3_workbench_package_state import (",
        "PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS",
        "PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS",
        "PACKAGE_REVIEW_SUBMIT_FORBIDDEN_FIELDS",
        "PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID",
        "PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS",
        "PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID",
        "HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID",
        "APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID",
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID",
        "package_review_preview_summary(",
        "package_review_preview_hash as _package_review_preview_hash",
        "package_review_candidate_projection(",
        "review_state_is_admitted_associated_cohort(",
        "packages_in_review_order as _packages_in_review_order",
        "review_source_packages as _review_source_packages",
        "canonical_payload_hashes as _canonical_payload_hashes",
        "canonical_payload_refs as _canonical_payload_refs",
        "package_review_submit_from_reconciliation as _package_review_submit_from_reconciliation",
        "package_source_dataset_version_ids as _package_source_dataset_version_ids",
        "package_source_shape as _package_source_shape",
        "handoff_export_prepare_from_reconciliation as _handoff_export_prepare_from_reconciliation",
        "aps_handoff_dispatch_from_reconciliation as _aps_handoff_dispatch_from_reconciliation",
        "external_export_download_prepare_from_reconciliation as _external_export_download_prepare_from_reconciliation",
        "blocked_payload_fields = package_review_preview_blocked_fields(payload)",
        "blocked_payload_fields = package_construction_commit_blocked_fields(payload)",
        "blocked_payload_fields = package_review_submit_blocked_fields(payload)",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing package review contract extraction term: {term}")
    for stale_term in (
        "PACKAGE_REVIEW_PREVIEW_FORBIDDEN_FIELDS = frozenset(",
        "PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS = frozenset(",
        "PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS = frozenset(",
        "PACKAGE_CONSTRUCTION_COMMIT_ALLOWED_FIELDS = frozenset(",
        "PACKAGE_REVIEW_SUBMIT_FORBIDDEN_FIELDS = frozenset(",
        "PACKAGE_REVIEW_SUBMIT_ALLOWED_FIELDS = frozenset(",
        "PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID = \"layer3.package_review_preview_state.v1\"",
        "PACKAGE_REVIEW_PREVIEW_READY_STATE = \"package_review_preview_ready\"",
        "PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE = (",
        "COHORT_PACKAGE_REVIEW_PREVIEW_DOWNSTREAM_UNAVAILABLE = (",
        "PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS = (",
        "def _package_review_preview_summary(",
        "def _package_review_preview_hash(",
        "def _package_review_candidate_projection(",
        "def _review_state_is_admitted_associated_cohort(",
        "def _packages_in_review_order(",
        "def _review_source_packages(",
        "def _canonical_payload_hashes(",
        "def _canonical_payload_refs(",
        "PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID = \"layer3.package_review_submit_state.v1\"",
        "HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID = \"layer3.handoff_export_prepare_state.v1\"",
        "APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID = \"layer3.aps_handoff_dispatch_state.v1\"",
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID = \"layer3.external_export_download_prepare_state.v1\"",
        "def _package_review_submit_from_reconciliation(",
        "def _handoff_export_prepare_from_reconciliation(",
        "def _aps_handoff_dispatch_from_reconciliation(",
        "def _external_export_download_prepare_from_reconciliation(",
        "def _package_source_shape(",
        "def _package_source_dataset_version_ids(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns package review contract term: {stale_term}")

    test_text = _read_required_text(LAYER3_PACKAGE_REVIEW_CONTRACT_TEST, errors)
    for term in (
        "test_package_review_contract_is_shared_without_behavior_change",
        "test_package_review_contract_blocks_same_fields_as_legacy_logic",
        "layer3_workbench.PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS",
        "contract.package_review_preview_blocked_fields(preview_payload)",
        "contract.package_construction_commit_blocked_fields(commit_payload)",
        "contract.package_review_submit_blocked_fields(submit_payload)",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_PACKAGE_REVIEW_CONTRACT_TEST)} missing package review contract test term: {term}")

    package_state_text = _read_required_text(WORKBENCH_PACKAGE_STATE_SERVICE, errors)
    for term in (
        "def packages_in_kind_order(",
        "def packages_with_kinds(",
        "def dispatched_package_id(",
        "def unexpected_package_kinds(",
        "def canonical_payload_values(",
        "PACKAGE_REVIEW_PREVIEW_STATE_SCHEMA_ID = \"layer3.package_review_preview_state.v1\"",
        "PACKAGE_REVIEW_PREVIEW_CANDIDATE_KINDS = (",
        "def package_review_preview_summary(",
        "def package_review_preview_hash(",
        "def package_review_candidate_projection(",
        "def review_state_is_admitted_associated_cohort(",
        "def packages_in_review_order(",
        "def review_source_packages(",
        "def canonical_payload_hashes(",
        "def canonical_payload_refs(",
        "PACKAGE_REVIEW_SUBMIT_STATE_SCHEMA_ID = \"layer3.package_review_submit_state.v1\"",
        "HANDOFF_EXPORT_PREPARE_STATE_SCHEMA_ID = \"layer3.handoff_export_prepare_state.v1\"",
        "APS_HANDOFF_DISPATCH_STATE_SCHEMA_ID = \"layer3.aps_handoff_dispatch_state.v1\"",
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_STATE_SCHEMA_ID = \"layer3.external_export_download_prepare_state.v1\"",
        "def reconciliation_state(",
        "def package_review_submit_from_reconciliation(",
        "def handoff_export_prepare_from_reconciliation(",
        "def aps_handoff_dispatch_from_reconciliation(",
        "def external_export_download_prepare_from_reconciliation(",
        "def package_source_shape(",
        "def package_source_dataset_version_ids(",
        "def package_owner_compatibility(",
        "def legacy_package_review_submit_record_ref(",
        "def cohort_package_construction_source(",
        "def package_review_submit_downstream_unavailable(",
        "def review_package_ref_map(",
        "def review_package_hash_map(",
    ):
        if term not in package_state_text:
            errors.append(f"{_rel(WORKBENCH_PACKAGE_STATE_SERVICE)} missing package-state helper term: {term}")

    package_state_test_text = _read_required_text(LAYER3_WORKBENCH_PACKAGE_STATE_TEST, errors)
    for term in (
        "test_packages_in_kind_order_returns_canonical_order",
        "test_packages_with_kinds_filters_without_mutating_order",
        "test_dispatched_package_id_requires_dispatched_state_and_expected_kind",
        "test_unexpected_package_kinds_allows_source_kinds_and_exact_dispatched_aps_package",
        "test_canonical_payload_values_accepts_list_and_dict_identity_forms",
        "test_package_review_candidate_projection_preserves_candidate_contract",
        "test_package_review_preview_summary_reports_unavailable_without_review_state",
        "test_package_review_preview_summary_preserves_approved_projection_and_clones_source_ids",
        "test_package_review_preview_summary_uses_cohort_downstream_for_admitted_associated_cohort",
        "test_review_state_is_admitted_associated_cohort_requires_exact_source_authority",
        "test_review_source_packages_filters_to_package_review_candidate_kinds",
        "test_packages_in_review_order_uses_package_review_candidate_order",
        "test_canonical_payload_hashes_and_refs_use_review_package_identity_forms",
        "test_reconciliation_state_requires_dict_and_matching_schema",
        "test_package_reconciliation_state_readers_preserve_matching_states",
        "test_package_reconciliation_state_readers_reject_wrong_schema",
        "test_package_source_shape_prefers_cohort_shape_then_dataset_version",
        "test_package_source_dataset_version_ids_prefers_list_then_dataset_version",
        "test_package_review_preview_hash_uses_stable_identity_basis",
        "test_package_owner_compatibility_reports_missing_gate_d_inputs_for_default_preview",
        "test_package_owner_compatibility_reports_ready_default_preview_without_calling_owner_service",
        "test_package_owner_compatibility_associated_cohort_preview_skips_gate_d_inputs",
        "test_legacy_package_review_submit_record_ref_preserves_legacy_identity_basis",
        "test_legacy_package_review_submit_record_ref_rejects_missing_or_provenance_authority",
        "test_cohort_package_construction_source_requires_exact_source_gate",
        "test_package_review_submit_downstream_unavailable_preserves_state_priority",
        "test_review_package_identity_maps_use_package_review_order_and_string_values",
    ):
        if term not in package_state_test_text:
            errors.append(f"{_rel(LAYER3_WORKBENCH_PACKAGE_STATE_TEST)} missing package-state proof test term: {term}")

    package_submit_response_text = _read_required_text(PACKAGE_SUBMIT_RESPONSE_SERVICE, errors)
    for term in (
        "PACKAGE_REVIEW_SUBMIT_SCHEMA_ID = \"layer3.package_review_submit.v1\"",
        "COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID = \"layer3.cohort_package_review_submit.v1\"",
        "def package_review_submit_response(",
        "base_response(PACKAGE_REVIEW_SUBMIT_SCHEMA_ID",
        "preview_identity(preview_id=preview_id, preview_hash=preview_hash)",
        "packages_in_review_order(packages)",
        "package_review_submit_downstream_unavailable(",
        "authority_rail(",
    ):
        if term not in package_submit_response_text:
            errors.append(f"{_rel(PACKAGE_SUBMIT_RESPONSE_SERVICE)} missing package submit response term: {term}")
    for term in (
        "from app.services.layer3_package_submit_response import (",
        "COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID",
        "PACKAGE_REVIEW_SUBMIT_SCHEMA_ID",
        "package_review_submit_response as _package_review_submit_response",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing package submit response delegation term: {term}")
    for stale_term in (
        "PACKAGE_REVIEW_SUBMIT_SCHEMA_ID = \"layer3.package_review_submit.v1\"",
        "COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID = \"layer3.cohort_package_review_submit.v1\"",
        "def _package_review_submit_response(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns package submit response term: {stale_term}")
    package_submit_response_test_text = _read_required_text(LAYER3_PACKAGE_SUBMIT_RESPONSE_TEST, errors)
    for term in (
        "test_package_review_submit_response_preserves_workbench_projection",
        "test_package_review_submit_response_preserves_cohort_schema_and_blocks_export",
        "layer3_workbench._package_review_submit_response",
        "COHORT_PACKAGE_REVIEW_SUBMIT_DOWNSTREAM_UNAVAILABLE",
        "HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE",
    ):
        if term not in package_submit_response_test_text:
            errors.append(
                f"{_rel(LAYER3_PACKAGE_SUBMIT_RESPONSE_TEST)} missing package submit response proof term: {term}"
            )
    handoff_response_text = _read_required_text(HANDOFF_EXPORT_RESPONSE_SERVICE, errors)
    for term in (
        "HANDOFF_EXPORT_PREPARE_SCHEMA_ID = \"layer3.handoff_export_prepare.v1\"",
        "COHORT_HANDOFF_EXPORT_PREPARE_SCHEMA_ID = \"layer3.cohort_handoff_export_prepare.v1\"",
        "def handoff_export_prepare_response(",
        "base_response(HANDOFF_EXPORT_PREPARE_SCHEMA_ID",
        "preview_identity(preview_id=preview_id, preview_hash=preview_hash)",
        "packages_in_review_order(packages)",
        "authority_rail(",
        "external_handoff_enabled",
        "external_export_enabled",
        "dispatch_enabled",
        "COHORT_PACKAGE_REVIEW_SUBMIT_SCHEMA_ID",
    ):
        if term not in handoff_response_text:
            errors.append(f"{_rel(HANDOFF_EXPORT_RESPONSE_SERVICE)} missing handoff response term: {term}")
    for term in (
        "from app.services.layer3_handoff_export_response import (",
        "COHORT_HANDOFF_EXPORT_PREPARE_SCHEMA_ID",
        "HANDOFF_EXPORT_PREPARE_SCHEMA_ID",
        "handoff_export_prepare_response as _handoff_export_prepare_response",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing handoff response delegation term: {term}")
    for stale_term in (
        "def _handoff_export_prepare_response(",
        "**_base_response(HANDOFF_EXPORT_PREPARE_SCHEMA_ID",
        "body[\"schema_id\"] = COHORT_HANDOFF_EXPORT_PREPARE_SCHEMA_ID",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns handoff response term: {stale_term}")
    handoff_response_test_text = _read_required_text(LAYER3_HANDOFF_EXPORT_RESPONSE_TEST, errors)
    for term in (
        "test_handoff_export_prepare_response_preserves_workbench_projection",
        "test_handoff_export_prepare_response_preserves_cohort_schema_and_provenance",
        "layer3_workbench._handoff_export_prepare_response",
        "HANDOFF_EXPORT_PREPARE_DOWNSTREAM_UNAVAILABLE",
        "COHORT_HANDOFF_EXPORT_PREPARE_SCHEMA_ID",
        "external_handoff_enabled",
        "external_export_enabled",
        "dispatch_enabled",
    ):
        if term not in handoff_response_test_text:
            errors.append(
                f"{_rel(LAYER3_HANDOFF_EXPORT_RESPONSE_TEST)} missing handoff response proof term: {term}"
            )
    external_response_text = _read_required_text(EXTERNAL_EXPORT_RESPONSE_SERVICE, errors)
    for term in (
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID = \"layer3.external_export_download_prepare.v1\"",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID = \"layer3.external_export_download_delivery.v1\"",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_SCHEMA_ID = \"layer3.external_export_download_delivery_ui.v1\"",
        "def external_export_download_prepare_response(",
        "def external_export_download_delivery_response(",
        "def associated_cohort_delivery_ui_state(",
        "def safe_download_token(",
        "def external_export_download_prepare_payload_for_delivery(",
        "def aps_bundle_identity_for_external_export_download(",
        "def external_export_download_prepare_summary(",
        "def _aps_handoff_package_for_dispatch(",
        "QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID",
        "QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID",
        "preview_identity(preview_id=preview_id, preview_hash=preview_hash)",
        "packages_in_review_order(packages)",
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS",
        "EXTERNAL_EXPORT_DOWNLOAD_OPERATOR_DECISION = \"prepare_external_export_download\"",
        "EXTERNAL_EXPORT_DOWNLOAD_READY_STATE = \"external_export_download_ready\"",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE = \"external_export_download_delivered\"",
        "APS_HANDOFF_SCHEMA_ID",
        "load_persisted_bundle_artifact",
        "Layer3WorkbenchError",
        "aps_handoff_dispatch_from_reconciliation",
        "external_export_download_prepare_from_reconciliation",
        "authority_rail(",
        "public_url_enabled",
        "connector_dispatch_enabled",
        "package_mutation_enabled",
    ):
        if term not in external_response_text:
            errors.append(f"{_rel(EXTERNAL_EXPORT_RESPONSE_SERVICE)} missing external export response term: {term}")
    for term in (
        "from app.services.layer3_external_export_response import (",
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID",
        "external_export_download_prepare_response as _external_export_download_prepare_response",
        "external_export_download_prepare_payload_for_delivery as _external_export_download_prepare_payload_for_delivery",
        "associated_cohort_delivery_ui_state as _associated_cohort_delivery_ui_state",
        "cohort_readiness_identity as _cohort_readiness_identity",
        "safe_download_token as _safe_download_token",
        "aps_bundle_identity_for_external_export_download as _aps_bundle_identity_for_external_export_download",
        "external_export_download_prepare_summary as _external_export_download_prepare_summary",
        "external_export_download_delivery_response as _external_export_download_delivery_response",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing external export response delegation term: {term}")
    for stale_term in (
        "def _external_export_download_prepare_response(",
        "def _associated_cohort_delivery_ui_state(",
        "def _cohort_readiness_identity(",
        "def _safe_download_token(",
        "def _external_export_download_prepare_payload_for_delivery(",
        "def _aps_bundle_identity_for_external_export_download(",
        "def _aps_handoff_package_for_dispatch(",
        "def _external_export_download_prepare_summary(",
        "def _external_export_download_delivery_response(",
        "external_export_download_delivery_artifact_validator_unavailable",
        "load_persisted_bundle_artifact(bundle_ref=source_artifact_ref)",
        "**_base_response(EXTERNAL_EXPORT_DOWNLOAD_PREPARE_SCHEMA_ID",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns external export response term: {stale_term}")
    external_response_test_text = _read_required_text(LAYER3_EXTERNAL_EXPORT_RESPONSE_TEST, errors)
    for term in (
        "test_external_export_download_prepare_response_preserves_workbench_projection",
        "test_external_export_download_prepare_response_preserves_cohort_delivery_ui_projection",
        "test_external_export_delivery_helpers_are_shared_with_workbench",
        "layer3_workbench._external_export_download_prepare_response",
        "layer3_workbench._safe_download_token",
        "layer3_workbench._external_export_download_prepare_payload_for_delivery",
        "export_response.safe_download_token",
        "export_response.external_export_download_prepare_payload_for_delivery",
        "test_external_export_bundle_identity_helper_is_shared_with_workbench",
        "layer3_workbench._aps_bundle_identity_for_external_export_download",
        "export_response.aps_bundle_identity_for_external_export_download",
        "validate_source_artifact=False",
        "test_external_export_summary_helper_is_shared_with_workbench",
        "layer3_workbench._external_export_download_prepare_summary",
        "export_response.external_export_download_prepare_summary",
        "external_export_download_ready",
        "test_external_export_delivery_response_helper_is_shared_with_workbench",
        "layer3_workbench._external_export_download_delivery_response",
        "export_response.external_export_download_delivery_response",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_SCHEMA_ID",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERED_STATE",
        "\"public_url\" not in prepare_payload",
        "EXTERNAL_EXPORT_DOWNLOAD_DOWNSTREAM_UNAVAILABLE",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_UI_SCHEMA_ID",
        "public_url_enabled",
        "connector_dispatch_enabled",
        "package_mutation_enabled",
    ):
        if term not in external_response_test_text:
            errors.append(
                f"{_rel(LAYER3_EXTERNAL_EXPORT_RESPONSE_TEST)} missing external export response proof term: {term}"
            )
    layer3_api_test_text = _read_required_text(LAYER3_API_TEST, errors)
    for term in (
        "test_layer3_api_external_export_download_deliver_streams_validated_bundle_without_side_effects",
        "test_layer3_api_external_export_download_deliver_fails_closed_when_bundle_artifact_missing",
        "test_layer3_api_external_export_download_deliver_malformed_json_fails_closed",
        "test_layer3_api_external_export_download_deliver_prechecks_fail_closed",
        "/api/v1/layer3/handoff/export/download/deliver",
        "external_export_download_delivered",
        "external_export_download_delivery_scope_not_admitted",
        "external_export_download_delivery_requires_prepared_readiness",
        "external_export_download_delivery_source_artifact_unavailable",
        "test_layer3_api_external_export_download_prepare_records_reference_only_descriptor",
        "test_layer3_api_cohort_aps_handoff_dispatch_materializes_bundle_with_companion_provenance",
        "test_layer3_api_session_summary_fails_closed_on_manifest_mismatch",
    ):
        if term not in layer3_api_test_text:
            errors.append(f"{_rel(LAYER3_API_TEST)} missing external export delivery API proof term: {term}")

    proof_manifest = _load_json(PROOF_MANIFEST, errors)
    proof_scope = proof_manifest.get("scope") if isinstance(proof_manifest, dict) else None
    if not isinstance(proof_scope, dict):
        errors.append(f"{_rel(PROOF_MANIFEST)} scope missing for package-state helper proof")
    else:
        expected_package_state_scope = {
            "latest_workbench_package_state_helper_proof_branch": "codex/l3-package-state-proof",
            "latest_workbench_package_state_helper_proof_pr": "#607",
            "latest_workbench_package_state_helper_proof_base_commit": "a5bd14f0b35e1aa7d35fdafe1f9b2b4d5ff90105",
            "latest_workbench_package_state_helper_proof_head_commit": "c1448bbd799c003b172514da1b04ac70495a4dca",
            "latest_workbench_package_state_helper_proof_merge_commit": "f1cba09a84a47d0095a7fd682b835316ebde5496",
            "latest_workbench_package_state_helper_proof_live_behavior_change": False,
        }
        for key, value in expected_package_state_scope.items():
            if proof_scope.get(key) != value:
                errors.append(f"{_rel(PROOF_MANIFEST)} scope.{key} must be {value!r}")
        proof_summary = proof_scope.get("latest_workbench_package_state_helper_proof_summary")
        for term in (
            "PR #607",
            "package ordering",
            "canonical payload matching",
            "without changing package behavior",
            "activating package mutation/reconstruction",
        ):
            if not isinstance(proof_summary, str) or term not in proof_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} scope.latest_workbench_package_state_helper_proof_summary "
                    f"missing package-state proof term: {term}"
                )
        if proof_scope.get("latest_package_review_preview_state_extraction_branch") != (
            "codex/l3-package-preview-state"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} scope.latest_package_review_preview_state_extraction_branch "
                "must be 'codex/l3-package-preview-state'"
            )
        preview_state_pr = proof_scope.get("latest_package_review_preview_state_extraction_pr")
        if preview_state_pr != "pending" and not (
            isinstance(preview_state_pr, str) and re.fullmatch(r"#\d+", preview_state_pr)
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} scope.latest_package_review_preview_state_extraction_pr "
                "must be 'pending' or a PR number"
            )
        preview_state_head = proof_scope.get("latest_package_review_preview_state_extraction_head_commit")
        if preview_state_head != "pending" and not (
            isinstance(preview_state_head, str) and re.fullmatch(r"[0-9a-f]{40}", preview_state_head)
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} scope.latest_package_review_preview_state_extraction_head_commit "
                "must be 'pending' or a 40-character commit"
            )
        if proof_scope.get("latest_package_review_preview_state_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_review_preview_state_extraction_live_behavior_change must be False"
            )
        preview_state_summary = proof_scope.get("latest_package_review_preview_state_extraction_summary")
        for term in (
            "package-review preview state",
            "candidate projection",
            "associated-cohort review-state admission",
            "without activating package mutation/reconstruction",
            "connector/destination dispatch",
        ):
            if not isinstance(preview_state_summary, str) or term not in preview_state_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_package_review_preview_state_extraction_summary "
                    f"missing package preview state extraction term: {term}"
                )
        if proof_scope.get("latest_package_review_package_set_helper_extraction_branch") != (
            "codex/l3-package-summary-state"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_review_package_set_helper_extraction_branch "
                "must be 'codex/l3-package-summary-state'"
            )
        package_set_pr = proof_scope.get("latest_package_review_package_set_helper_extraction_pr")
        if package_set_pr != "pending" and not (
            isinstance(package_set_pr, str) and re.fullmatch(r"#\d+", package_set_pr)
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_review_package_set_helper_extraction_pr "
                "must be 'pending' or a PR number"
            )
        if proof_scope.get("latest_package_review_package_set_helper_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_review_package_set_helper_extraction_live_behavior_change must be False"
            )
        package_set_summary = proof_scope.get("latest_package_review_package_set_helper_extraction_summary")
        for term in (
            "package-set helper extraction",
            "packages_in_review_order",
            "review_source_packages",
            "canonical_payload_hashes",
            "canonical_payload_refs",
            "without activating package mutation/reconstruction",
        ):
            if not isinstance(package_set_summary, str) or term not in package_set_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_package_review_package_set_helper_extraction_summary "
                    f"missing package set helper extraction term: {term}"
                )
        if proof_scope.get("latest_package_reconciliation_state_extraction_branch") != (
            "codex/l3-package-reconciliation-state"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_reconciliation_state_extraction_branch "
                "must be 'codex/l3-package-reconciliation-state'"
            )
        reconciliation_state_pr = proof_scope.get("latest_package_reconciliation_state_extraction_pr")
        if reconciliation_state_pr != "#653":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_reconciliation_state_extraction_pr must be '#653'"
            )
        if (
            proof_scope.get("latest_package_reconciliation_state_extraction_head_commit")
            != "fe547dfd89e848bd933158a9183582f5a9f03915"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_reconciliation_state_extraction_head_commit must be "
                "'fe547dfd89e848bd933158a9183582f5a9f03915'"
            )
        if (
            proof_scope.get("latest_package_reconciliation_state_extraction_merge_commit")
            != "39ed6564171373ad21789291813b8e3711debe98"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_reconciliation_state_extraction_merge_commit must be "
                "'39ed6564171373ad21789291813b8e3711debe98'"
            )
        if proof_scope.get("latest_package_reconciliation_state_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_reconciliation_state_extraction_live_behavior_change must be False"
            )
        reconciliation_state_summary = proof_scope.get("latest_package_reconciliation_state_extraction_summary")
        for term in (
            "PR #653",
            "merge commit 39ed6564171373ad21789291813b8e3711debe98",
            "reconciliation state extraction",
            "package_review_submit_from_reconciliation",
            "handoff_export_prepare_from_reconciliation",
            "aps_handoff_dispatch_from_reconciliation",
            "external_export_download_prepare_from_reconciliation",
            "without activating package mutation/reconstruction",
        ):
            if not isinstance(reconciliation_state_summary, str) or term not in reconciliation_state_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_package_reconciliation_state_extraction_summary "
                    f"missing reconciliation state extraction term: {term}"
                )
        if proof_scope.get("latest_package_source_projection_extraction_branch") != (
            "codex/l3-package-source-projection"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_source_projection_extraction_branch "
                "must be 'codex/l3-package-source-projection'"
            )
        source_projection_pr = proof_scope.get("latest_package_source_projection_extraction_pr")
        if source_projection_pr != "#655":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_source_projection_extraction_pr must be '#655'"
            )
        if (
            proof_scope.get("latest_package_source_projection_extraction_head_commit")
            != "dd616519bf6b10fb6e1a0e81eaad9d6facaa7fc6"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_source_projection_extraction_head_commit must be "
                "'dd616519bf6b10fb6e1a0e81eaad9d6facaa7fc6'"
            )
        if (
            proof_scope.get("latest_package_source_projection_extraction_merge_commit")
            != "0c797452fd66886f277424171956e6f9e75063fc"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_source_projection_extraction_merge_commit must be "
                "'0c797452fd66886f277424171956e6f9e75063fc'"
            )
        if proof_scope.get("latest_package_source_projection_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_source_projection_extraction_live_behavior_change must be False"
            )
        source_projection_summary = proof_scope.get("latest_package_source_projection_extraction_summary")
        for term in (
            "PR #655",
            "merge commit 0c797452fd66886f277424171956e6f9e75063fc",
            "package source projection extraction",
            "package_source_shape",
            "package_source_dataset_version_ids",
            "without activating package mutation/reconstruction",
        ):
            if not isinstance(source_projection_summary, str) or term not in source_projection_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_package_source_projection_extraction_summary "
                    f"missing package source projection extraction term: {term}"
                )
        if proof_scope.get("latest_package_review_preview_hash_extraction_branch") != (
            "codex/l3-package-preview-hash"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_review_preview_hash_extraction_branch "
                "must be 'codex/l3-package-preview-hash'"
            )
        preview_hash_pr = proof_scope.get("latest_package_review_preview_hash_extraction_pr")
        if preview_hash_pr != "#657":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_review_preview_hash_extraction_pr must be '#657'"
            )
        if (
            proof_scope.get("latest_package_review_preview_hash_extraction_head_commit")
            != "cf75c465ae31e03f5c9e25ab6b27ed8a725864cd"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_review_preview_hash_extraction_head_commit must be "
                "'cf75c465ae31e03f5c9e25ab6b27ed8a725864cd'"
            )
        if (
            proof_scope.get("latest_package_review_preview_hash_extraction_merge_commit")
            != "0a77ab6edc43c6e9426bbc20d58e6ebb6b05a333"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_review_preview_hash_extraction_merge_commit must be "
                "'0a77ab6edc43c6e9426bbc20d58e6ebb6b05a333'"
            )
        if proof_scope.get("latest_package_review_preview_hash_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_review_preview_hash_extraction_live_behavior_change must be False"
            )
        preview_hash_summary = proof_scope.get("latest_package_review_preview_hash_extraction_summary")
        for term in (
            "PR #657",
            "merge commit 0a77ab6edc43c6e9426bbc20d58e6ebb6b05a333",
            "package-review preview hash extraction",
            "package_review_preview_hash",
            "stable identity basis",
            "without activating package mutation/reconstruction",
        ):
            if not isinstance(preview_hash_summary, str) or term not in preview_hash_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_package_review_preview_hash_extraction_summary "
                    f"missing package-review preview hash extraction term: {term}"
                )
        if proof_scope.get("latest_package_owner_compatibility_extraction_branch") != (
            "codex/l3-package-owner-compatibility"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_owner_compatibility_extraction_branch "
                "must be 'codex/l3-package-owner-compatibility'"
            )
        owner_compat_pr = proof_scope.get("latest_package_owner_compatibility_extraction_pr")
        if owner_compat_pr != "#659":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_owner_compatibility_extraction_pr must be '#659'"
            )
        if (
            proof_scope.get("latest_package_owner_compatibility_extraction_head_commit")
            != "64c31111015bdaf3e5d096c0ae678c611f260b1d"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_owner_compatibility_extraction_head_commit "
                "must be '64c31111015bdaf3e5d096c0ae678c611f260b1d'"
            )
        if (
            proof_scope.get("latest_package_owner_compatibility_extraction_merge_commit")
            != "f435b5b00662646c44081f38e6e2328183ceeaf6"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_owner_compatibility_extraction_merge_commit "
                "must be 'f435b5b00662646c44081f38e6e2328183ceeaf6'"
            )
        if proof_scope.get("latest_package_owner_compatibility_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_owner_compatibility_extraction_live_behavior_change must be False"
            )
        owner_compat_summary = proof_scope.get("latest_package_owner_compatibility_extraction_summary")
        for term in (
            "PR #659",
            "merge commit f435b5b00662646c44081f38e6e2328183ceeaf6",
            "package owner compatibility extraction",
            "package_owner_compatibility",
            "read-only owner-service compatibility projection",
            "without activating package mutation/reconstruction",
        ):
            if not isinstance(owner_compat_summary, str) or term not in owner_compat_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_package_owner_compatibility_extraction_summary "
                    f"missing package owner compatibility extraction term: {term}"
                )
        if proof_scope.get("latest_package_submit_state_helper_extraction_branch") != (
            "codex/l3-package-submit-state"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_submit_state_helper_extraction_branch "
                "must be 'codex/l3-package-submit-state'"
            )
        submit_state_pr = proof_scope.get("latest_package_submit_state_helper_extraction_pr")
        if submit_state_pr != "#661":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_submit_state_helper_extraction_pr must be '#661'"
            )
        if (
            proof_scope.get("latest_package_submit_state_helper_extraction_head_commit")
            != "ac5afc1492e79d5b78baa300f8bb96cc3692bab3"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_submit_state_helper_extraction_head_commit "
                "must be 'ac5afc1492e79d5b78baa300f8bb96cc3692bab3'"
            )
        if (
            proof_scope.get("latest_package_submit_state_helper_extraction_merge_commit")
            != "a1c8df7c2ca20e26ccbc3bf5e875b910abd69166"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_submit_state_helper_extraction_merge_commit "
                "must be 'a1c8df7c2ca20e26ccbc3bf5e875b910abd69166'"
            )
        if proof_scope.get("latest_package_submit_state_helper_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_submit_state_helper_extraction_live_behavior_change must be False"
            )
        submit_state_summary = proof_scope.get("latest_package_submit_state_helper_extraction_summary")
        for term in (
            "PR #661",
            "merge commit a1c8df7c2ca20e26ccbc3bf5e875b910abd69166",
            "package submit state helper extraction",
            "legacy_package_review_submit_record_ref",
            "cohort_package_construction_source",
            "package_review_submit_downstream_unavailable",
            "without activating package mutation/reconstruction",
        ):
            if not isinstance(submit_state_summary, str) or term not in submit_state_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_package_submit_state_helper_extraction_summary "
                    f"missing package submit state helper extraction term: {term}"
                )
        if proof_scope.get("latest_package_identity_map_extraction_branch") != (
            "codex/l3-package-identity-maps"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_identity_map_extraction_branch must be 'codex/l3-package-identity-maps'"
            )
        identity_map_pr = proof_scope.get("latest_package_identity_map_extraction_pr")
        if identity_map_pr != "#663":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_identity_map_extraction_pr must be '#663'"
            )
        identity_map_head = proof_scope.get("latest_package_identity_map_extraction_head_commit")
        if identity_map_head != "e41ba5cfed255d1ab4bc3c1e1bb9e77c445c259d":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_identity_map_extraction_head_commit must match PR #663 head commit"
            )
        identity_map_merge = proof_scope.get("latest_package_identity_map_extraction_merge_commit")
        if identity_map_merge != "a3e9305a716fd9a07c5d0340ce54dd85ece7fa44":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_identity_map_extraction_merge_commit must match PR #663 merge commit"
            )
        if proof_scope.get("latest_package_identity_map_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_identity_map_extraction_live_behavior_change must be False"
            )
        identity_map_summary = proof_scope.get("latest_package_identity_map_extraction_summary")
        for term in (
            "package identity map extraction",
            "PR #663",
            "merge commit a3e9305a716fd9a07c5d0340ce54dd85ece7fa44",
            "review_package_ref_map",
            "review_package_hash_map",
            "without activating package mutation/reconstruction",
        ):
            if not isinstance(identity_map_summary, str) or term not in identity_map_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_package_identity_map_extraction_summary "
                    f"missing package identity map extraction term: {term}"
                )
        if proof_scope.get("latest_package_submit_response_extraction_branch") != (
            "codex/l3-package-submit-response"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_submit_response_extraction_branch must be 'codex/l3-package-submit-response'"
            )
        submit_response_pr = proof_scope.get("latest_package_submit_response_extraction_pr")
        if submit_response_pr != "#665":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_submit_response_extraction_pr must be '#665'"
            )
        submit_response_head = proof_scope.get("latest_package_submit_response_extraction_head_commit")
        if submit_response_head != "0f93aa075844e6c08f1fb80fe72e78c8ea3d9b20":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_submit_response_extraction_head_commit must match PR #665 head commit"
            )
        submit_response_merge = proof_scope.get("latest_package_submit_response_extraction_merge_commit")
        if submit_response_merge != "6eab6c4dc04ad3cddb677a7af4782d00f3e62f46":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_submit_response_extraction_merge_commit must match PR #665 merge commit"
            )
        if proof_scope.get("latest_package_submit_response_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_package_submit_response_extraction_live_behavior_change must be False"
            )
        submit_response_summary = proof_scope.get("latest_package_submit_response_extraction_summary")
        for term in (
            "package submit response extraction",
            "PR #665",
            "merge commit 6eab6c4dc04ad3cddb677a7af4782d00f3e62f46",
            "package_review_submit_response",
            "layer3_package_submit_response.py",
            "without activating package mutation/reconstruction",
        ):
            if not isinstance(submit_response_summary, str) or term not in submit_response_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_package_submit_response_extraction_summary "
                    f"missing package submit response extraction term: {term}"
                )
        if proof_scope.get("latest_handoff_export_prepare_response_extraction_branch") != (
            "codex/l3-handoff-export-prepare-response"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_handoff_export_prepare_response_extraction_branch "
                "must be 'codex/l3-handoff-export-prepare-response'"
            )
        handoff_response_pr = proof_scope.get("latest_handoff_export_prepare_response_extraction_pr")
        if handoff_response_pr != "#667":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_handoff_export_prepare_response_extraction_pr must be '#667'"
            )
        handoff_response_head = proof_scope.get("latest_handoff_export_prepare_response_extraction_head_commit")
        if handoff_response_head != "20608d1917e1c85d43699f78519712bb65d62f0d":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_handoff_export_prepare_response_extraction_head_commit "
                "must match PR #667 head commit"
            )
        handoff_response_merge = proof_scope.get("latest_handoff_export_prepare_response_extraction_merge_commit")
        if handoff_response_merge != "dddb481af930b9af260488d2bb4a357982b32aa7":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_handoff_export_prepare_response_extraction_merge_commit "
                "must match PR #667 merge commit"
            )
        if proof_scope.get("latest_handoff_export_prepare_response_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_handoff_export_prepare_response_extraction_live_behavior_change must be False"
            )
        handoff_response_summary = proof_scope.get(
            "latest_handoff_export_prepare_response_extraction_summary"
        )
        for term in (
            "handoff export prepare response extraction",
            "PR #667",
            "merge commit dddb481af930b9af260488d2bb4a357982b32aa7",
            "handoff_export_prepare_response",
            "layer3_handoff_export_response.py",
            "without activating package mutation/reconstruction",
            "broad handoff/export behavior",
        ):
            if not isinstance(handoff_response_summary, str) or term not in handoff_response_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_handoff_export_prepare_response_extraction_summary "
                    f"missing handoff export response extraction term: {term}"
                )
        if proof_scope.get("latest_external_export_prepare_response_extraction_branch") != (
            "codex/l3-external-export-response"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_prepare_response_extraction_branch "
                "must be 'codex/l3-external-export-response'"
            )
        external_response_pr = proof_scope.get("latest_external_export_prepare_response_extraction_pr")
        if external_response_pr != "#669":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_prepare_response_extraction_pr must be '#669'"
            )
        external_response_head = proof_scope.get("latest_external_export_prepare_response_extraction_head_commit")
        if external_response_head != "b1270f4aed7b5d20aec7122705fe8774eabf69a3":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_prepare_response_extraction_head_commit "
                "must match PR #669 head commit"
            )
        external_response_merge = proof_scope.get("latest_external_export_prepare_response_extraction_merge_commit")
        if external_response_merge != "f6e51567009a077ea226e1d3b4147ac29b05e3bb":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_prepare_response_extraction_merge_commit "
                "must match PR #669 merge commit"
            )
        if proof_scope.get("latest_external_export_prepare_response_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_prepare_response_extraction_live_behavior_change must be False"
            )
        external_response_summary = proof_scope.get(
            "latest_external_export_prepare_response_extraction_summary"
        )
        for term in (
            "external export/download prepare response extraction",
            "PR #669",
            "merge commit f6e51567009a077ea226e1d3b4147ac29b05e3bb",
            "external_export_download_prepare_response",
            "layer3_external_export_response.py",
            "associated-cohort delivery UI projection",
            "without activating provider/public URLs",
            "connector/destination dispatch",
            "package mutation/reconstruction",
        ):
            if not isinstance(external_response_summary, str) or term not in external_response_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_external_export_prepare_response_extraction_summary "
                    f"missing external export response extraction term: {term}"
                )
        if proof_scope.get("latest_external_export_delivery_helper_extraction_branch") != (
            "codex/l3-external-export-delivery-helper"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_helper_extraction_branch "
                "must be 'codex/l3-external-export-delivery-helper'"
            )
        if proof_scope.get("latest_external_export_delivery_helper_extraction_pr") != "#671":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_helper_extraction_pr must be '#671'"
            )
        if proof_scope.get("latest_external_export_delivery_helper_extraction_head_commit") != (
            "83a070c48ebca2193ce7249cb9865f54c88ea39b"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_helper_extraction_head_commit "
                "must match PR #671 head commit"
            )
        if proof_scope.get("latest_external_export_delivery_helper_extraction_merge_commit") != (
            "6e1a55bb389d948fd0d60a4b87dca1d9b1e8717c"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_helper_extraction_merge_commit "
                "must match PR #671 merge commit"
            )
        if proof_scope.get("latest_external_export_delivery_helper_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_helper_extraction_live_behavior_change must be False"
            )
        delivery_helper_summary = proof_scope.get(
            "latest_external_export_delivery_helper_extraction_summary"
        )
        for term in (
            "external export/download delivery helper extraction",
            "PR #671",
            "merge commit 6e1a55bb389d948fd0d60a4b87dca1d9b1e8717c",
            "safe_download_token",
            "external_export_download_prepare_payload_for_delivery",
            "layer3_external_export_response.py",
            "_safe_download_token",
            "_external_export_download_prepare_payload_for_delivery",
            "without activating provider/public URLs",
            "connector/destination dispatch",
            "package mutation/reconstruction",
        ):
            if not isinstance(delivery_helper_summary, str) or term not in delivery_helper_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_external_export_delivery_helper_extraction_summary "
                    f"missing external export delivery helper extraction term: {term}"
                )
        if proof_scope.get("latest_external_export_bundle_identity_extraction_branch") != (
            "codex/l3-external-export-bundle-identity"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_bundle_identity_extraction_branch "
                "must be 'codex/l3-external-export-bundle-identity'"
            )
        if proof_scope.get("latest_external_export_bundle_identity_extraction_pr") != "#673":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_bundle_identity_extraction_pr must be '#673'"
            )
        if proof_scope.get("latest_external_export_bundle_identity_extraction_head_commit") != (
            "d8c273346eff5a624ef7ed3987fd124cd1dd06ff"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_bundle_identity_extraction_head_commit "
                "must match PR #673 head commit"
            )
        if proof_scope.get("latest_external_export_bundle_identity_extraction_merge_commit") != (
            "563b34618dedc7453dd02ade4d48ce424267fbaf"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_bundle_identity_extraction_merge_commit "
                "must match PR #673 merge commit"
            )
        if proof_scope.get("latest_external_export_bundle_identity_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_bundle_identity_extraction_live_behavior_change must be False"
            )
        bundle_identity_summary = proof_scope.get(
            "latest_external_export_bundle_identity_extraction_summary"
        )
        for term in (
            "external export/download APS bundle identity extraction",
            "PR #673",
            "merge commit 563b34618dedc7453dd02ade4d48ce424267fbaf",
            "aps_bundle_identity_for_external_export_download",
            "layer3_external_export_response.py",
            "_aps_bundle_identity_for_external_export_download",
            "route-level external_export_download_prepare",
            "external_export_download_deliver proof",
            "without activating provider/public URLs",
            "connector/destination dispatch",
            "package mutation/reconstruction",
        ):
            if not isinstance(bundle_identity_summary, str) or term not in bundle_identity_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_external_export_bundle_identity_extraction_summary "
                    f"missing external export bundle identity extraction term: {term}"
                )
        if proof_scope.get("latest_external_export_summary_extraction_branch") != (
            "codex/l3-external-export-summary"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_summary_extraction_branch "
                "must be 'codex/l3-external-export-summary'"
            )
        if proof_scope.get("latest_external_export_summary_extraction_pr") != "#675":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_summary_extraction_pr must be '#675'"
            )
        if proof_scope.get("latest_external_export_summary_extraction_head_commit") != (
            "d3741bd5ac0d640cb4194a343a45b86b1704f72b"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_summary_extraction_head_commit "
                "must match PR #675 head commit"
            )
        if proof_scope.get("latest_external_export_summary_extraction_merge_commit") != (
            "e54584d263faa3b539c294a413211286bfb9caa1"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_summary_extraction_merge_commit "
                "must match PR #675 merge commit"
            )
        if proof_scope.get("latest_external_export_summary_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_summary_extraction_live_behavior_change must be False"
            )
        external_summary = proof_scope.get(
            "latest_external_export_summary_extraction_summary"
        )
        for term in (
            "external export/download prepare summary extraction",
            "PR #675",
            "merge commit e54584d263faa3b539c294a413211286bfb9caa1",
            "external_export_download_prepare_summary",
            "layer3_external_export_response.py",
            "_external_export_download_prepare_summary",
            "route-level external_export_download_prepare",
            "external_export_download_deliver",
            "session_summary proof",
            "without activating provider/public URLs",
            "connector/destination dispatch",
            "package mutation/reconstruction",
        ):
            if not isinstance(external_summary, str) or term not in external_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_external_export_summary_extraction_summary "
                    f"missing external export summary extraction term: {term}"
                )
        if proof_scope.get("latest_external_export_delivery_response_extraction_branch") != (
            "codex/l3-external-export-delivery-response"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_response_extraction_branch "
                "must be 'codex/l3-external-export-delivery-response'"
            )
        if proof_scope.get("latest_external_export_delivery_response_extraction_pr") != "#677":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_response_extraction_pr must be '#677'"
            )
        if proof_scope.get("latest_external_export_delivery_response_extraction_head_commit") != (
            "1060f9e9754b7559e33df29d48aef597aa755458"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_response_extraction_head_commit "
                "must match PR #677 head commit"
            )
        if proof_scope.get("latest_external_export_delivery_response_extraction_merge_commit") != (
            "cc415cfe502322f47cbb2c708827c454e981d70a"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_response_extraction_merge_commit "
                "must match PR #677 merge commit"
            )
        if proof_scope.get("latest_external_export_delivery_response_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_response_extraction_live_behavior_change must be False"
            )
        delivery_response_summary = proof_scope.get(
            "latest_external_export_delivery_response_extraction_summary"
        )
        for term in (
            "external export/download delivery response extraction",
            "PR #677",
            "merge commit cc415cfe502322f47cbb2c708827c454e981d70a",
            "external_export_download_delivery_response",
            "layer3_external_export_response.py",
            "_external_export_download_delivery_response",
            "route-level external_export_download_prepare",
            "external_export_download_deliver proof",
            "without activating provider/public URLs",
            "connector/destination dispatch",
            "package mutation/reconstruction",
        ):
            if not isinstance(delivery_response_summary, str) or term not in delivery_response_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_external_export_delivery_response_extraction_summary "
                    f"missing external export delivery response extraction term: {term}"
                )
        if proof_scope.get("latest_external_export_delivery_input_extraction_branch") != (
            "codex/l3-external-export-delivery-input"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_input_extraction_branch "
                "must be 'codex/l3-external-export-delivery-input'"
            )
        if proof_scope.get("latest_external_export_delivery_input_extraction_pr") != "#679":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_input_extraction_pr must be '#679'"
            )
        if proof_scope.get("latest_external_export_delivery_input_extraction_head_commit") != (
            "dbd7224ce5991f74d26be481bac5557e9d211018"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_input_extraction_head_commit "
                "must match PR #679 head commit"
            )
        if proof_scope.get("latest_external_export_delivery_input_extraction_merge_commit") != (
            "a9d21dad5751ab08d849c8d18ab9e6583b877abc"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_input_extraction_merge_commit "
                "must match PR #679 merge commit"
            )
        if proof_scope.get("latest_external_export_delivery_input_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_input_extraction_live_behavior_change must be False"
            )
        delivery_input_summary = proof_scope.get(
            "latest_external_export_delivery_input_extraction_summary"
        )
        for term in (
            "external export/download delivery input parsing extraction",
            "PR #679",
            "merge commit a9d21dad5751ab08d849c8d18ab9e6583b877abc",
            "external_export_download_delivery_request_fields",
            "layer3_external_export_contract.py",
            "workbench delegation",
            "route-level external_export_download_prepare",
            "external_export_download_deliver proof",
            "without activating provider/public URLs",
            "connector/destination dispatch",
            "package mutation/reconstruction",
            "signed-reference behavior",
        ):
            if not isinstance(delivery_input_summary, str) or term not in delivery_input_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_external_export_delivery_input_extraction_summary "
                    f"missing external export delivery input extraction term: {term}"
                )
        if proof_scope.get("latest_external_export_delivery_match_extraction_branch") != (
            "codex/l3-external-export-delivery-match"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_match_extraction_branch "
                "must be 'codex/l3-external-export-delivery-match'"
            )
        if proof_scope.get("latest_external_export_delivery_match_extraction_pr") != "#681":
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_match_extraction_pr must be '#681'"
            )
        if proof_scope.get("latest_external_export_delivery_match_extraction_head_commit") != (
            "6c4288c44d71881fac969e889b970ae87e5c806c"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_match_extraction_head_commit "
                "must match PR #681 head commit"
            )
        if proof_scope.get("latest_external_export_delivery_match_extraction_merge_commit") != (
            "c13e96214f58b475e2027f066294701ad99df0de"
        ):
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_match_extraction_merge_commit "
                "must match PR #681 merge commit"
            )
        if proof_scope.get("latest_external_export_delivery_match_extraction_live_behavior_change") is not False:
            errors.append(
                f"{_rel(PROOF_MANIFEST)} "
                "scope.latest_external_export_delivery_match_extraction_live_behavior_change must be False"
            )
        delivery_match_summary = proof_scope.get(
            "latest_external_export_delivery_match_extraction_summary"
        )
        for term in (
            "external export/download delivery readiness matching extraction",
            "PR #681",
            "merge commit c13e96214f58b475e2027f066294701ad99df0de",
            "external_export_download_delivery_readiness_mismatches",
            "layer3_external_export_contract.py",
            "workbench-owned error construction",
            "route-level external_export_download_prepare",
            "external_export_download_deliver proof",
            "without activating provider/public URLs",
            "connector/destination dispatch",
            "package mutation/reconstruction",
            "signed-reference behavior",
        ):
            if not isinstance(delivery_match_summary, str) or term not in delivery_match_summary:
                errors.append(
                    f"{_rel(PROOF_MANIFEST)} "
                    "scope.latest_external_export_delivery_match_extraction_summary "
                    f"missing external export delivery match extraction term: {term}"
                )

    for path, terms in {
        MANIFEST: (
            "latest_package_owner_compatibility_extraction_branch",
            "package_owner_compatibility_extraction",
            "package_owner_compatibility",
            "latest_package_submit_state_helper_extraction_branch",
            "package_submit_state_helper_extraction",
            "legacy_package_review_submit_record_ref",
            "latest_package_identity_map_extraction_branch",
            "package_identity_map_extraction",
            "PR #663/merge commit a3e9305a",
            "review_package_ref_map",
            "latest_package_submit_response_extraction_branch",
            "package_submit_response_extraction",
            "PR #665/merge commit 6eab6c4d",
            "layer3_package_submit_response.py",
            "without activating package mutation/reconstruction",
            "latest_handoff_export_prepare_response_extraction_branch",
            "handoff_export_prepare_response_extraction",
            "PR #667/merge commit dddb481a",
            "layer3_handoff_export_response.py",
            "broad handoff/export behavior",
            "external_export_response_extraction",
            "PR #669/merge commit f6e51567",
            "layer3_external_export_response.py",
            "provider/public URLs",
            "external_export_delivery_helper_extraction",
            "PR #671/merge commit 6e1a55bb",
            "safe_download_token",
            "external_export_download_prepare_payload_for_delivery",
            "external_export_bundle_identity_extraction",
            "PR #673/merge commit 563b3461",
            "aps_bundle_identity_for_external_export_download",
            "external_export_summary_extraction",
            "PR #675/merge commit e54584d",
            "external_export_download_prepare_summary",
            "external_export_delivery_response_extraction",
            "PR #677/merge commit cc415cfe",
            "external_export_download_delivery_response",
            "external_export_delivery_input_extraction",
            "PR #679/merge commit a9d21dad",
            "external_export_download_delivery_request_fields",
            "external_export_delivery_match_extraction",
            "PR #681/merge commit c13e9621",
            "external_export_download_delivery_readiness_mismatches",
        ),
        BOARD: (
            "Package owner compatibility extraction",
            "package_owner_compatibility",
            "Package submit state helper extraction",
            "package_review_submit_downstream_unavailable",
            "Package identity map extraction",
            "PR `#663`, merge commit `a3e9305a`",
            "review_package_hash_map",
            "without changing package handoff/export identity-map behavior",
            "Package submit response extraction",
            "PR `#665`, merge commit `6eab6c4d`",
            "layer3_package_submit_response.py",
            "without changing package-review submit response behavior",
            "Handoff export prepare response extraction",
            "PR `#667`, merge commit `dddb481a`",
            "layer3_handoff_export_response.py",
            "without changing handoff/export prepare response behavior",
            "External export/download prepare response extraction",
            "PR `#669`, merge commit `f6e51567`",
            "layer3_external_export_response.py",
            "without changing external export/download prepare response behavior",
            "External export/download delivery helper extraction",
            "PR `#671`, merge commit `6e1a55bb`",
            "safe_download_token",
            "external_export_download_prepare_payload_for_delivery",
            "without changing external export/download delivery behavior",
            "External export/download APS bundle identity extraction",
            "PR `#673`, merge commit `563b3461`",
            "aps_bundle_identity_for_external_export_download",
            "without changing external export/download prepare, delivery, or source-artifact validation behavior",
            "External export/download prepare summary extraction",
            "PR `#675`, merge commit `e54584d2`",
            "external_export_download_prepare_summary",
            "without changing external export/download session-summary behavior",
            "External export/download delivery response extraction",
            "PR `#677`, merge commit `cc415cfe`",
            "external_export_download_delivery_response",
            "without changing same-origin external export/download delivery behavior",
            "External export/download delivery input parsing extraction",
            "PR `#679`, merge commit `a9d21dad`",
            "external_export_download_delivery_request_fields",
            "without changing same-origin external export/download delivery precheck behavior",
            "External export/download delivery readiness matching extraction",
            "PR `#681`, merge commit `c13e9621`",
            "external_export_download_delivery_readiness_mismatches",
            "without changing same-origin external export/download delivery readiness-mismatch behavior",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package owner compatibility extraction term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "package review/construction/submit contract extraction",
            "layer3_package_review_contract.py",
            "test_layer3_package_review_contract.py",
        ),
        GOAL_AUDIT: (
            "PR #580 package review/construction/submit contract extraction",
            "layer3_package_review_contract.py",
            "test_layer3_package_review_contract.py",
            "PR #580 established `backend/app/services/layer3_package_review_contract.py`",
            "package review/construction/submit contract extraction proof merged after PR #580",
            "current-main proof with `300 passed, 4 warnings`",
            "does not change package review preview, package construction commit, package review submit allowlists, denylists, blocked-field behavior, emitted package-review responses, emitted package-construction responses, or any deferred broad capability",
        ),
        CLOSEOUT_DOC: (
            "PR #580 package review/construction/submit contract extraction proof",
            "layer3_package_review_contract.py",
            "test_layer3_package_review_contract.py",
            "test_layer3_workbench_package_state.py",
            "package-state helper proof",
            "proof_snapshot_head: `f1cba09a84a47d0095a7fd682b835316ebde5496`",
            "PR #607 package-state helper proof hardening",
            "project6-origin/main=f1cba09a84a47d0095a7fd682b835316ebde5496",
            "Focused package-review-contract suite: 2 passed.",
            "Focused package review API regression: 13 passed, 116 deselected, 4 warnings.",
            "Local focused Layer 3 backend suite: 300 passed, 4 warnings.",
            "Pre-merge PR #580 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #580: 6b817f94.",
            "Post-merge full Layer 3 backend suite: 300 passed, 4 warnings.",
            "proof/refactor hardening through PR #607",
            "No package mutation/reconstruction, package payload rewrite, source widening, connector/destination dispatch, provider/public URL support, broad qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior is admitted.",
        ),
        MANIFEST: (
            "PR #607",
            "f1cba09a84a47d0095a7fd682b835316ebde5496",
            "latest_workbench_package_state_helper_proof_pr",
            "latest_package_review_preview_state_extraction_branch",
            "latest_package_review_package_set_helper_extraction_branch",
            "latest_package_reconciliation_state_extraction_branch",
            "latest_package_source_projection_extraction_branch",
            "latest_package_review_preview_hash_extraction_branch",
            "PR #653/merge commit 39ed6564",
            "PR #655/merge commit 0c797452",
            "PR #657/merge commit 0a77ab6e",
            "c1448bbd799c003b172514da1b04ac70495a4dca",
            "test_layer3_workbench_package_state.py",
            "package-state helper proof",
            "package-review preview state extraction",
            "package-set helper extraction",
            "reconciliation state extraction",
            "package source projection extraction",
            "package-review preview hash extraction",
            "without activating package mutation",
        ),
        BOARD: (
            "PR `#607`",
            "f1cba09a84a47d0095a7fd682b835316ebde5496",
            "test_layer3_workbench_package_state.py",
            "package-state helper proof hardening",
            "package-review preview state extraction",
            "package-set helper extraction",
            "reconciliation state extraction",
            "package source projection extraction",
            "package-review preview hash extraction",
            "merge commit `39ed6564`",
            "merge commit `0c797452`",
            "merge commit `0a77ab6e`",
            "without activating package mutation/reconstruction",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package review contract extraction doc term: {term}")


def _check_aps_source_family_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(APS_SOURCE_FAMILY_SERVICE, errors)
    for term in (
        "APS_ADMITTED_TABLE_SOURCE_FAMILIES",
        "APS_NOT_ADMITTED_SOURCE_FAMILIES",
        "APS_ADMITTED_SOURCE_FAMILY_BY_PARSER",
        "def source_family_for_parser(",
        "def source_family_summary(",
        "\"csv_table\"",
        "\"xlsx_workbook\"",
        "\"json_recordset\"",
        "\"sec_edgar_filing\"",
        "\"xml_html_inline_xbrl\"",
        "\"broad_workbook_semantics\"",
        "refused/deferred families are explanatory guardrails, not selectable source classes",
    ):
        if term not in service_text:
            errors.append(f"{_rel(APS_SOURCE_FAMILY_SERVICE)} missing APS source-family extraction term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_aps_source_family import",
        "source_family_for_parser as _source_family_for_parser",
        "source_family_summary as _source_family_summary",
        "_source_family_for_parser(provenance.get(\"parser_family\"))",
        "\"source_family_summary\": _source_family_summary(candidates)",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing APS source-family import/use term: {term}")
    for stale_term in (
        "APS_ADMITTED_TABLE_SOURCE_FAMILIES = (",
        "APS_NOT_ADMITTED_SOURCE_FAMILIES = (",
        "APS_ADMITTED_SOURCE_FAMILY_BY_PARSER = {",
        "def _source_family_for_parser(",
        "def _source_family_summary(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns APS source-family term: {stale_term}")

    test_text = _read_required_text(APS_SOURCE_FAMILY_TEST, errors)
    for term in (
        "test_source_family_for_parser_maps_admitted_aps_table_families",
        "test_source_family_for_parser_returns_unknown_metadata_copy",
        "test_source_family_summary_counts_observed_parsers_and_returns_copies",
        "APS_ADMITTED_TABLE_SOURCE_FAMILIES[0][\"source_family\"] == \"csv\"",
    ):
        if term not in test_text:
            errors.append(f"{_rel(APS_SOURCE_FAMILY_TEST)} missing APS source-family proof test term: {term}")

    required_doc_terms = {
        CLOSEOUT_DOC: (
            "APS source-family extraction",
            "backend/app/services/layer3_aps_source_family.py",
            "backend/tests/test_layer3_aps_source_family.py",
            "no-behavior-change",
            "does not admit broad source/upload expansion",
        ),
        MANIFEST: (
            "layer3_aps_source_family.py",
            "test_layer3_aps_source_family.py",
            "APS source-family extraction",
            "PR #609",
            "ad51b1c6736cd51ec3dd30de914e59ddb4c66158",
            "no-behavior-change",
            "does not admit broad source/upload expansion",
        ),
        BOARD: (
            "APS source-family extraction",
            "PR `#609`",
            "ad51b1c6736cd51ec3dd30de914e59ddb4c66158",
            "layer3_aps_source_family.py",
            "test_layer3_aps_source_family.py",
            "without admitting broad source/upload expansion",
        ),
        PROOF_MANIFEST: (
            "latest_aps_source_family_extraction_branch",
            "latest_aps_source_family_extraction_pr",
            "#609",
            "ad51b1c6736cd51ec3dd30de914e59ddb4c66158",
            "codex/l3-aps-source-family-extraction",
            "layer3_aps_source_family.py",
            "test_layer3_aps_source_family.py",
            "no runtime behavior change",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing APS source-family extraction doc term: {term}")


def _check_external_export_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(EXTERNAL_EXPORT_CONTRACT_SERVICE, errors)
    for term in (
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS = frozenset(",
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS = frozenset(",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ALLOWED_FIELDS = EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS | frozenset(",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS = frozenset(",
        "class ExternalExportDownloadDelivery",
        "class ExternalExportDownloadDeliveryRequestFields",
        "def external_export_download_delivery_request_fields(",
        "def external_export_download_delivery_readiness_mismatches(",
        "def external_export_download_prepare_blocked_fields(",
        "def external_export_download_delivery_blocked_fields(",
        '"public_url"',
        '"connector_run_id"',
        '"local_directory"',
    ):
        if term not in service_text:
            errors.append(f"{_rel(EXTERNAL_EXPORT_CONTRACT_SERVICE)} missing external export contract term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "from app.services.layer3_external_export_contract import",
        "ExternalExportDownloadDelivery",
        "external_export_download_delivery_request_fields",
        "external_export_download_delivery_readiness_mismatches",
        "delivery_request = external_export_download_delivery_request_fields(payload)",
        "external_export_download_delivery_readiness_mismatches(",
        "missing = delivery_request.missing_fields",
        "external_export_download_prepare_blocked_fields(payload)",
        "external_export_download_delivery_blocked_fields(payload)",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing external export contract extraction term: {term}")
    for stale_term in (
        "from dataclasses import dataclass, field",
        "@dataclass(frozen=True)\nclass ExternalExportDownloadDelivery:",
        "def external_export_download_delivery_readiness_mismatches(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns external export contract term: {stale_term!r}")

    test_text = _read_required_text(LAYER3_EXTERNAL_EXPORT_CONTRACT_TEST, errors)
    for term in (
        "test_external_export_download_contract_is_shared_without_behavior_change",
        "test_external_export_download_contract_blocks_same_fields_as_legacy_logic",
        "test_external_export_download_delivery_request_fields_match_legacy_missing_order",
        "test_external_export_download_delivery_readiness_mismatches_match_legacy_comparison",
        "ExternalExportDownloadDelivery",
        "ExternalExportDownloadDeliveryRequestFields",
        "external_export_download_delivery_request_fields",
        "external_export_download_delivery_readiness_mismatches",
        "missing_fields",
        "external_export_download_prepare_blocked_fields",
        "external_export_download_delivery_blocked_fields",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_EXTERNAL_EXPORT_CONTRACT_TEST)} missing external export contract test term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: (
            "external export/download contract extraction",
            "layer3_external_export_contract.py",
            "test_layer3_external_export_contract.py",
        ),
        GOAL_AUDIT: (
            "external export/download contract extraction",
            "layer3_external_export_contract.py",
            "test_layer3_external_export_contract.py",
            "test_external_export_download_contract_is_shared_without_behavior_change",
            "PR #575 established `backend/app/services/layer3_external_export_contract.py`",
            "external export/download contract extraction proof merged after PR #575",
            "current-main proof with `296 passed, 4 warnings`",
            "does not change external export/download allowlists, denylists, blocked-field behavior, delivery value object shape, emitted delivery responses, or any deferred broad capability",
        ),
        CLOSEOUT_DOC: (
            "PR #575 external export/download contract extraction proof",
            "layer3_external_export_contract.py",
            "test_layer3_external_export_contract.py",
            "proof_snapshot_head: `f1cba09a84a47d0095a7fd682b835316ebde5496`",
            "PR #575 external export/download contract extraction proof",
            "proof/refactor hardening through PR #607",
            "external export/download contract extraction;",
            "Focused external-export-contract suite: 2 passed.",
            "Pre-merge PR #575 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #575: 6be9b127.",
            "Post-merge full Layer 3 backend suite: 296 passed, 4 warnings.",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing external export contract extraction doc term: {term}")


def _check_gate_b_durable_idempotency_claim(errors: list[str]) -> None:
    required_terms = {
        MODELS: [
            "class L3GateBIdempotencyKey",
            "uq_l3_gate_b_idempotency_client_request",
            "ck_l3_gate_b_idempotency_status",
            "L3_GATE_B_IDEMPOTENCY_STATUS_CLAIMED",
            "L3_GATE_B_IDEMPOTENCY_STATUS_COMMITTED",
        ],
        GATE_B_IDEMPOTENCY_MIGRATION: [
            "revision = \"0017_layer3_gate_b_idempotency\"",
            "down_revision = \"0016_layer3_signed_reference_state\"",
            "l3_gate_b_idempotency_key",
            "uq_l3_gate_b_idempotency_client_request",
            "ck_l3_gate_b_idempotency_status",
        ],
        GATE_B_STATE_SERVICE: [
            'GATE_B_DECISIONS = ("approved", "denied", "isolated", "flagged")',
            'GATE_B_DECISION_MANIFEST_SCHEMA_ID = "layer3.gate_b_decision_manifest.v1"',
            'MATERIAL_PREVIEW_BASIS_SCHEMA_ID = "layer3.material_preview_basis.v1"',
            "def gate_b_counts(",
            "def gate_b_summary_from_session(",
            "def material_candidate_basis_from_preview(",
            "def material_candidate_basis_from_decision(",
            "def material_preview_basis(",
            "def material_preview_hash(",
            "def candidate_decision_manifest(",
            "def gate_b_decision_manifest_id(",
            "claim_gate_b_idempotency",
            "complete_gate_b_idempotency_claim",
            "gate_b_idempotency_claim_matches",
            "gate_b_idempotency_request_hash",
            "L3GateBIdempotencyKey",
        ],
        WORKBENCH_SERVICE: [
            "candidate_decision_manifest as build_candidate_decision_manifest",
            "claim_gate_b_idempotency",
            "complete_gate_b_idempotency_claim",
            "find_gate_b_idempotency_claim",
            "gate_b_counts",
            "gate_b_decision_manifest_id as build_gate_b_decision_manifest_id",
            "gate_b_summary_from_session",
            "material_candidate_basis_from_decision as gate_b_material_candidate_basis_from_decision",
            "material_candidate_basis_from_preview as gate_b_material_candidate_basis_from_preview",
            "material_preview_hash as compute_material_preview_hash",
            "gate_b_idempotency_in_progress",
        ],
        READINESS_CONTRACT_SERVICE: [
            "\"gate_b_decision_idempotency_scope\": \"durable_claim_and_post_commit_retry\"",
            "\"gate_b_decision_concurrent_duplicate_lock\": True",
        ],
        GATE_B_STATE_TEST: [
            "test_gate_b_counts_preserve_workbench_decision_vocabulary",
            "test_gate_b_summary_from_session_prefers_summary_json_counts",
            "test_gate_b_summary_from_session_falls_back_to_decision_manifest",
            "test_material_candidate_basis_helpers_preserve_workbench_projection_and_defaults",
            "test_material_preview_basis_sorts_clones_and_hashes_canonically",
            "test_candidate_decision_manifest_sorts_clones_and_builds_stable_id",
            "test_gate_b_idempotency_migration_defines_durable_unique_claim",
            "test_gate_b_idempotency_claim_round_trips_and_matches",
            "test_gate_b_decision_concurrent_duplicate_client_request_id_uses_durable_claim",
            "ThreadPoolExecutor",
        ],
        LAYER3_API_TEST: [
            "L3GateBIdempotencyKey",
            "\"durable_claim_and_post_commit_retry\"",
            "gate_b_decision_concurrent_duplicate_lock",
        ],
        SYNTHESIS_BOUNDARY: [
            "0017_layer3_gate_b_idempotency.py",
            "test_gate_b_decision_concurrent_duplicate_client_request_id_uses_durable_claim",
            "without admitting execution, source widening, package mutation/reconstruction, connector/destination dispatch",
        ],
        GOAL_AUDIT: [
            "durable Gate B idempotency claim proof",
            "L3GateBIdempotencyKey",
            "test_gate_b_decision_concurrent_duplicate_client_request_id_uses_durable_claim",
        ],
    }
    for path, terms in required_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing Gate B durable idempotency term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for stale_term in (
        "def _gate_b_counts(",
        "def _gate_b_summary_from_session(",
        "def _material_candidate_basis_from_preview(",
        "def _material_candidate_basis_from_decision(",
        "def _material_preview_basis(",
        "def _material_preview_hash(",
        "def _candidate_decision_manifest(",
        "def _gate_b_decision_manifest_id(",
        "GATE_B_DECISIONS = (\"approved\", \"denied\", \"isolated\", \"flagged\")",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns Gate B summary helper term: {stale_term}")

    board_text = _read_required_text(BOARD, errors)
    for term in (
        "Gate B summary state extraction",
        "PR `#630`, commit `a71e3cf5`",
        "| Gate B summary state extraction | current-main no-behavior-change refactor/proof |",
        "layer3_gate_b_state.py",
        "test_layer3_gate_b_state.py",
        "decision counts, and session-summary reconstruction",
        "without changing emitted Gate B, Gate C, plan, or session-summary count behavior",
        "does not admit execution behavior, route, DTO, model, migration, UI, package, connector, provider, source, qualitative/RAG, mockup, or auth/security behavior",
        "Gate B material/decision basis extraction",
        "PR `#632`, commit `56f2ea7b`, merge commit `58f33a33`",
        "material-preview hash basis, candidate-decision manifest, and Gate B decision manifest ID construction",
        "| Gate B material/decision basis extraction | current-main no-behavior-change refactor/proof |",
    ):
        if term not in board_text:
            errors.append(f"{_rel(BOARD)} missing Gate B summary extraction board term: {term}")
    for stale_term in (
        "Branch-local proof/refactor continuation: branch `codex/l3-gate-b-material-basis-extract`",
        "| Gate B material/decision basis extraction | in-progress no-behavior-change refactor/proof |",
        "branch `codex/l3-gate-b-material-basis-extract`, base `8509a6f0`",
    ):
        if stale_term in board_text:
            errors.append(f"{_rel(BOARD)} still contains stale Gate B material basis branch-local term: {stale_term}")
    for path in (MANIFEST, PROOF_MANIFEST):
        text = _read_required_text(path, errors)
        for stale_term in (
            "branch_local_gate_b_material",
            "Branch codex/l3-gate-b-material-basis-extract, base 8509a6f0",
            "Branch-local no-behavior-change Gate B extraction",
        ):
            if stale_term in text:
                errors.append(f"{_rel(path)} still contains stale Gate B material basis branch-local term: {stale_term}")


def _check_gate_b_decision_basis_openapi_guard(errors: list[str]) -> None:
    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "GATE_B_DECISION_ITEM_SCHEMA",
        '"source_identity": {"type": "object", "additionalProperties": True}',
        '"source_provenance": {"type": "object", "additionalProperties": True}',
        '"payload": {"type": "object", "additionalProperties": True}',
        '"load_summary": {"type": "object", "additionalProperties": True}',
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing Gate B decision-basis OpenAPI guard term: {term}")

    api_test_text = _read_required_text(LAYER3_API_TEST, errors)
    for term in (
        "decision_basis_properties = decision_basis_schema[\"properties\"]",
        "\"source_identity\"",
        "\"source_provenance\"",
        "\"payload\"",
        "\"load_summary\"",
        "decision_basis_properties[basis_key][\"additionalProperties\"] is True",
    ):
        if term not in api_test_text:
            errors.append(f"{_rel(LAYER3_API_TEST)} missing Gate B decision-basis OpenAPI test term: {term}")


def _check_bounded_e2e_current_main_sync(errors: list[str]) -> None:
    for path, terms in {
        BOARD: (
            "Bounded Layer 3 API E2E current-main closeout",
            "PR #688-era proof/control sync before mixed APS bridge",
            "PR `#682` through PR `#687`, current main `342c71e5`",
            "aps_handoff_dispatch_blocked",
            "no admitted `aps_content_document` material-snapshot provenance",
            "separately admitted exact `single_aps_doc_qualitative_pass`",
            "Mixed APS provenance bridge bounded E2E extension",
            "aps_handoff_companion_provenance",
            "external_export_download_delivered",
        ),
        MANIFEST: (
            "latest_bounded_e2e_current_main_sync_branch",
            "bounded_e2e_current_main_sync",
            "PR #682 through PR #687",
            "API-created dataset-version cohort method authority",
            "aps_handoff_dispatch_blocked",
            "no admitted aps_content_document material-snapshot provenance",
            "exact single_aps_doc_qualitative_pass",
            "latest_mixed_aps_provenance_bridge_branch",
            "mixed_aps_provenance_bridge",
            "aps_handoff_companion_provenance",
            "external_export_download_delivered",
        ),
        PROOF_MANIFEST: (
            "latest_bounded_e2e_current_main_sync_branch",
            "latest_bounded_e2e_current_main_sync_prs",
            "#682-#687",
            "latest_bounded_e2e_current_main_sync_input_main_commit",
            "342c71e5f8c7a88d5cadd274a525811399cfb151",
            "latest_bounded_e2e_current_main_sync_live_behavior_change",
            "latest_bounded_e2e_current_main_sync_summary",
            "aps_handoff_dispatch_blocked",
            "exact single APS-document qualitative execution through single_aps_doc_qualitative_pass only",
            "broad qualitative execution beyond the exact single_aps_doc_qualitative_pass boundary",
            "latest_mixed_aps_provenance_bridge_branch",
            "latest_mixed_aps_provenance_bridge_input_main_commit",
            "latest_mixed_aps_provenance_bridge_live_behavior_change",
            "latest_mixed_aps_provenance_bridge_summary",
            "API-created mixed dataset-version associated-cohort plus APS content-document companion provenance",
            "aps_handoff_companion_provenance",
            "external_export_download_delivered",
        ),
    }.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing bounded E2E current-main sync term: {term}")

    test_text = _read_required_text(LAYER3_BOUNDED_E2E_TEST, errors)
    for term in (
        "test_layer3_bounded_e2e_api_associated_cohort_reaches_download_delivery",
        "Layer3ApiDriver",
        "Layer3StateAssertions",
        "_seed_sources",
        "_patch_cohort_dataframe_persistence",
        "assert_forbidden_side_effects_absent",
        "aps_dispatch",
        "external_export_download_prepare",
        "external_export_download_deliver",
        "aps_handoff_companion_provenance",
        "qualitative_aps_companion_provenance_not_pass_candidate",
        "external_export_download_delivered",
        "requested_method_name\"] == \"descriptive_summary\"",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_BOUNDED_E2E_TEST)} missing bounded E2E proof term: {term}")

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        "_stamp_api_dataset_cohort_method_authority",
        "gate-b-dataset-version-cohort-",
        "\"requested_method_name\": \"descriptive_summary\"",
        "_gate_b_snapshot_material_basis",
        "APS_HANDOFF_COMPANION_ANALYSIS_ROLE",
        "mixed_dataset_version_aps_handoff_provenance_bridge",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing API cohort method-authority term: {term}")

    qual_aps_text = _read_required_text(QUAL_APS_SERVICE, errors)
    for term in (
        "APS_HANDOFF_COMPANION_ANALYSIS_ROLE = \"aps_handoff_companion_provenance\"",
        "qualitative_aps_companion_provenance_not_pass_candidate",
    ):
        if term not in qual_aps_text:
            errors.append(f"{_rel(QUAL_APS_SERVICE)} missing mixed APS companion guard term: {term}")


def main() -> int:
    errors: list[str] = []
    for path in (
        MANIFEST,
        BOARD,
        REFRESH_SPEC,
        PROGRESS_PROMPT,
        PROOF_MANIFEST,
        PLAYWRIGHT_WORKFLOW,
        LAYER3_API_REQUIREMENTS,
        BROWSER_REQUIREMENTS,
        DEFERRED_GATES,
        QUAL_APS_FREEZE,
        LOCAL_BOUNDARY,
        SYNTHESIS_BOUNDARY,
        GOAL_AUDIT,
        QUAL_APS_ENTRY_FREEZE,
        CLOSEOUT_DOC,
        CONNECTOR_ENTRY_FREEZE,
        PACKAGE_MUTATION_FREEZE,
        SOURCE_EXPANSION_FREEZE,
        RAW_MIXED_BRIDGE_FREEZE,
        QUAL_APS_PACKAGE_REVIEW_FREEZE,
        QUAL_APS_PACKAGE_REVIEW_CONTRACT,
        QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE,
        QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT,
        POST_709_ROADMAP_FREEZE,
        QUAL_APS_PACKAGE_SUBMIT_FREEZE,
        QUAL_APS_PACKAGE_SUBMIT_CONTRACT,
        QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE,
        QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT,
        QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE,
        QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT,
        QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE,
        QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT,
        QUAL_APS_RENDERED_UI_FREEZE,
        QUAL_APS_RENDERED_UI_CONTRACT,
        SOURCE_BREADTH_FREEZE,
        RAW_INGESTION_MATERIALIZATION_FREEZE,
        RAW_MIXED_RENDERED_UI_FREEZE,
        RAW_MIXED_RENDERED_UI_CONTRACT,
        POST_730_ROADMAP_SYNC,
        POST_730_PRACTICAL_READINESS,
        RAW_MIXED_RENDERED_DOWNSTREAM_BLOCKER,
        RENDERED_EXECUTION_SELECTION_START_FREEZE,
        RENDERED_EXECUTION_SELECTION_START_CONTRACT,
        RENDERED_EXECUTION_SELECTION_START_RUNTIME,
        RENDERED_RESULT_REVIEW_FREEZE,
        RENDERED_RESULT_REVIEW_CONTRACT,
        RENDERED_RESULT_REVIEW_PROOF,
        RENDERED_PACKAGE_REVIEW_FREEZE,
        RENDERED_PACKAGE_REVIEW_CONTRACT,
        RENDERED_PACKAGE_REVIEW_PROOF,
        RENDERED_HANDOFF_EXPORT_FREEZE,
        RENDERED_HANDOFF_EXPORT_CONTRACT,
        RENDERED_HANDOFF_EXPORT_PROOF,
        RENDERED_APS_HANDOFF_FREEZE,
        RENDERED_APS_HANDOFF_CONTRACT,
        RENDERED_APS_HANDOFF_PROOF,
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FREEZE,
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_CONTRACT,
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PROOF,
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE,
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_CONTRACT,
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PROOF,
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_FREEZE,
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_CONTRACT,
        RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF,
        POST_745_DOWNSTREAM_EXPANSION_FREEZE,
        POST_745_DOWNSTREAM_EXPANSION_CONTRACT,
        QUAL_HYBRID_RAG_FREEZE,
        MOCKUP_TRUTH_FREEZE,
        PACKAGE_COMMIT_FREEZE,
        PACKAGE_REPLACEMENT_SET_FREEZE,
        PACKAGE_REPLACEMENT_ARTIFACT_FREEZE,
        PACKAGE_REPLACEMENT_ARTIFACT_MANIFEST_FREEZE,
        PACKAGE_REPLACEMENT_NAMESPACE_FREEZE,
        PACKAGE_REPLACEMENT_NAMESPACE_ENTRY_FREEZE,
        PLAN_REVISION_RECOVERY_FREEZE,
        PLAN_REVISION_RECOVERY_CONTRACT,
        PLAN_REVISION_RECOVERY_ENTRY_FREEZE,
        PLAN_REVISION_RECOVERY_TEST,
        APPROVED_PLAN_CORRECTION_FREEZE,
        APPROVED_PLAN_CANCEL_ENTRY_FREEZE,
        APPROVED_PLAN_CORRECTION_SERVICE,
        APPROVED_PLAN_CORRECTION_TEST,
        STATE_ACTION_CONTRACT,
        SESSION_ENTRY_MIGRATION,
        PASS_ENTRY_MIGRATION,
        PACKAGE_ENTRY_MIGRATION,
        GATE_B_IDEMPOTENCY_MIGRATION,
        REPLACEMENT_PACKAGE_SET_AUTHORITY_MIGRATION,
        PACKAGE_SUPERSESSION_COMMIT_MIGRATION,
        REPLACEMENT_PACKAGE_NAMESPACE_MIGRATION,
        LAYER3_API,
        MODELS,
        GATE_B_STATE_SERVICE,
        SOURCE_BOUNDARY_SERVICE,
        RAW_MIXED_BRIDGE_SERVICE,
        RAW_MIXED_MATERIALIZATION_SERVICE,
        PREFLIGHT_REQUEST_CONTRACT_SERVICE,
        APS_SOURCE_FAMILY_SERVICE,
        QUAL_APS_SERVICE,
        MOCKUP_BOUNDARY_SERVICE,
        WORKBENCH_SERVICE,
        RESPONSE_CONTRACT_SERVICE,
        WORKBENCH_ERROR_SERVICE,
        AUTHORITY_RAIL_SERVICE,
        PREVIEW_CONTRACT_SERVICE,
        READINESS_CONTRACT_SERVICE,
        BOOTSTRAP_CONTRACT_SERVICE,
        STATE_MODEL_CONTRACT_SERVICE,
        PLAN_FLOW_STATE_SERVICE,
        PLAN_FLOW_READINESS_SERVICE,
        SUBLAYER_STATE_SERVICE,
        EXECUTION_STATE_SERVICE,
        EXECUTION_OUTPUT_SERVICE,
        EXECUTION_REVIEW_SERVICE,
        EXECUTION_SELECTION_SERVICE,
        EXECUTION_START_SERVICE,
        EXECUTION_STATUS_SERVICE,
        EXECUTION_REQUEST_CONTRACT_SERVICE,
        PACKAGE_REVIEW_CONTRACT_SERVICE,
        PACKAGE_SUBMIT_RESPONSE_SERVICE,
        HANDOFF_EXPORT_RESPONSE_SERVICE,
        EXTERNAL_EXPORT_RESPONSE_SERVICE,
        EXTERNAL_EXPORT_CONTRACT_SERVICE,
        CONNECTOR_DISPATCH_SERVICE,
        PACKAGE_MUTATION_SERVICE,
        REPLACEMENT_PACKAGE_SET_AUTHORITY_SERVICE,
        PACKAGE_SUPERSESSION_COMMIT_SERVICE,
        REPLACEMENT_PACKAGE_NAMESPACE_SERVICE,
        LAYER3_HTML,
        LAYER3_CSS,
        LAYER3_JS,
        SOURCE_BOUNDARY_TEST,
        PREFLIGHT_REQUEST_CONTRACT_TEST,
        APS_SOURCE_FAMILY_TEST,
        RAW_MIXED_BRIDGE_TEST,
        RAW_MIXED_MATERIALIZATION_TEST,
        QUAL_APS_TEST,
        MOCKUP_BOUNDARY_TEST,
        SESSION_ENTRY_TEST,
        PLAN_PASS_STATUS_CONSTRAINT_TEST,
        GATE_B_STATE_TEST,
        REPLACEMENT_PACKAGE_SET_AUTHORITY_TEST,
        PACKAGE_SUPERSESSION_COMMIT_TEST,
        REPLACEMENT_PACKAGE_NAMESPACE_TEST,
        SIGNED_REFERENCE_STATE_SERVICE,
        SIGNED_REFERENCE_STATE_TEST,
        LAYER3_API_TEST,
        LAYER3_PAGE_TEST,
        LAYER3_RESPONSE_CONTRACT_TEST,
        LAYER3_WORKBENCH_ERROR_TEST,
        LAYER3_AUTHORITY_RAIL_TEST,
        LAYER3_PREVIEW_CONTRACT_TEST,
        LAYER3_READINESS_CONTRACT_TEST,
        LAYER3_BOOTSTRAP_CONTRACT_TEST,
        LAYER3_STATE_MODEL_CONTRACT_TEST,
        LAYER3_PLAN_FLOW_STATE_TEST,
        LAYER3_PLAN_FLOW_READINESS_TEST,
        LAYER3_SUBLAYER_STATE_TEST,
        LAYER3_EXECUTION_STATE_TEST,
        LAYER3_EXECUTION_OUTPUT_TEST,
        LAYER3_EXECUTION_REVIEW_TEST,
        LAYER3_EXECUTION_SELECTION_TEST,
        LAYER3_EXECUTION_START_TEST,
        LAYER3_EXECUTION_STATUS_TEST,
        LAYER3_EXECUTION_REQUEST_CONTRACT_TEST,
        HANDOFF_CONTRACT_SERVICE,
        APS_HANDOFF_SERVICE,
        LAYER3_HANDOFF_CONTRACT_TEST,
        LAYER3_PACKAGE_REVIEW_CONTRACT_TEST,
        LAYER3_PACKAGE_SUBMIT_RESPONSE_TEST,
        LAYER3_HANDOFF_EXPORT_RESPONSE_TEST,
        LAYER3_EXTERNAL_EXPORT_RESPONSE_TEST,
        WORKBENCH_PACKAGE_STATE_SERVICE,
        LAYER3_WORKBENCH_PACKAGE_STATE_TEST,
        PLAN_ERROR_SERVICE,
        LAYER3_PLAN_ERROR_TEST,
        EXECUTION_ERROR_SERVICE,
        LAYER3_EXECUTION_ERROR_TEST,
        LAYER3_EXTERNAL_EXPORT_CONTRACT_TEST,
        LAYER3_WORKBENCH_E2E,
        LAYER3_FLOW_E2E,
        MOCKUP_ASSETS,
        MOCKUP_SPEC,
        REVIEW_BROWSER_SERVER,
    ):
        _require_file(path, errors)

    manifest = _load_json(MANIFEST, errors)
    _load_json(PROOF_MANIFEST, errors)
    if manifest:
        _check_snapshot_consistency(manifest, errors)
        _check_latest_progress_sync(manifest, errors)
        _check_summary_counts(manifest, errors)
        _check_current_decision(manifest, errors)
        _check_plan_revision_recovery_freeze(manifest, errors)
        _check_plan_revision_recovery_entry_freeze(manifest, errors)
        _check_approved_plan_correction_freeze(manifest, errors)
        _check_approved_plan_cancel_entry_freeze(manifest, errors)
        _check_approved_plan_cancel_runtime(manifest, errors)
        _check_referenced_paths(manifest, errors)
    _check_local_boundary(errors)
    _check_connector_dispatch_entry_freeze(errors)
    _check_package_mutation_freeze(errors)
    _check_package_commit_entry_freeze(errors)
    _check_package_replacement_set_freeze(errors)
    _check_package_replacement_artifact_freeze(errors)
    _check_package_replacement_artifact_manifest_freeze(errors)
    _check_package_replacement_namespace_freeze(errors)
    _check_package_replacement_namespace_entry_freeze(errors)
    _check_qualitative_capability_boundary(errors)
    _check_qualitative_aps_package_review_freeze(errors)
    _check_qualitative_aps_package_construction_freeze(errors)
    _check_qualitative_aps_package_submit_freeze(errors)
    _check_qualitative_aps_handoff_export_prepare_freeze(errors)
    _check_qualitative_aps_aps_handoff_dispatch_freeze(errors)
    _check_qualitative_aps_external_export_download_freeze(errors)
    _check_qualitative_aps_rendered_ui_freeze(errors)
    _check_source_boundary_contract(errors)
    _check_raw_mixed_bridge_freeze(errors)
    _check_source_breadth_freeze(errors)
    _check_raw_ingestion_materialization_freeze(errors)
    _check_raw_mixed_rendered_ui_freeze(errors)
    _check_post_730_roadmap_sync(errors)
    _check_post_730_practical_readiness(errors)
    _check_raw_mixed_rendered_downstream_blocker(errors)
    _check_rendered_execution_selection_start_freeze(errors)
    _check_rendered_execution_selection_start_runtime(errors)
    _check_rendered_result_review_freeze(errors)
    _check_rendered_result_review_proof(errors)
    _check_rendered_package_review_freeze(errors)
    _check_rendered_package_review_proof(errors)
    _check_rendered_handoff_export_freeze(errors)
    _check_rendered_handoff_export_proof(errors)
    _check_rendered_aps_handoff_freeze(errors)
    _check_rendered_aps_handoff_proof(errors)
    _check_rendered_external_export_download_prepare_freeze(errors)
    _check_rendered_external_export_download_prepare_proof(errors)
    _check_rendered_external_export_download_delivery_freeze(errors)
    _check_rendered_external_export_download_delivery_proof(errors)
    _check_rendered_external_export_download_signed_reference_freeze(errors)
    _check_rendered_external_export_download_signed_reference_proof(errors)
    _check_post_745_downstream_expansion_freeze(errors)
    _check_provider_public_url_entry_freeze(errors)
    _check_mockup_truth_state_boundary(errors)
    _check_signed_reference_state_guard(errors)
    _check_gate_b_durable_idempotency_claim(errors)
    _check_gate_b_decision_basis_openapi_guard(errors)
    _check_preflight_request_guard(errors)
    _check_plan_preview_request_guard(errors)
    _check_source_preview_request_guard(errors)
    _check_material_preview_request_guard(errors)
    _check_gate_c_override_request_guard(errors)
    _check_session_status_migration_constraint(errors)
    _check_plan_pass_status_migration_constraints(errors)
    _check_progress_text_surfaces(errors)
    _check_ci_layer3_backend_guardrail(errors)
    if manifest:
        _check_qualitative_progress_sync(manifest, errors)
    _check_state_action_contract_frontend_signature(errors)
    _check_response_contract_extraction(errors)
    _check_workbench_error_extraction(errors)
    _check_plan_error_extraction(errors)
    _check_execution_error_extraction(errors)
    _check_authority_rail_extraction(errors)
    _check_preview_contract_extraction(errors)
    _check_readiness_contract_extraction(errors)
    _check_bootstrap_contract_extraction(errors)
    _check_state_model_contract_extraction(errors)
    _check_plan_flow_contract_extraction(errors)
    _check_plan_flow_state_extraction(errors)
    _check_plan_flow_readiness_extraction(errors)
    _check_sublayer_state_extraction(errors)
    _check_execution_state_extraction(errors)
    _check_execution_output_extraction(errors)
    _check_execution_review_extraction(errors)
    _check_execution_selection_summary_extraction(errors)
    _check_execution_start_response_extraction(errors)
    _check_execution_status_response_extraction(errors)
    _check_execution_request_contract_extraction(errors)
    _check_handoff_contract_extraction(errors)
    _check_package_review_contract_extraction(errors)
    _check_aps_source_family_extraction(errors)
    _check_external_export_contract_extraction(errors)
    _check_bounded_e2e_current_main_sync(errors)

    if errors:
        print("Layer 3 progress state check: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Layer 3 progress state check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
