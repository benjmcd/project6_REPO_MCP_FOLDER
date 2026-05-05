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
QUAL_HYBRID_RAG_FREEZE = PLANNING_DOCS / "124_QUAL_HYBRID_RAG_FREEZE.md"
MOCKUP_TRUTH_FREEZE = PLANNING_DOCS / "125_MOCKUP_TRUTH_STATE_FREEZE.md"
PACKAGE_COMMIT_FREEZE = PLANNING_DOCS / "126_PACKAGE_COMMIT_FREEZE.md"
PACKAGE_REPLACEMENT_SET_FREEZE = PLANNING_DOCS / "127_PACKAGE_REPLACEMENT_SET_FREEZE.md"
STATE_ACTION_CONTRACT = (
    ROOT / "backend" / "app" / "services" / "layer3_state_action_contract.py"
)
STATE_MODEL_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_state_model_contract.py"
)
PLAN_FLOW_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_plan_flow_contract.py"
)
EXECUTION_REQUEST_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_execution_request_contract.py"
)
HANDOFF_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_handoff_contract.py"
)
PACKAGE_REVIEW_CONTRACT_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_package_review_contract.py"
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
REPLACEMENT_PACKAGE_SET_AUTHORITY_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0018_layer3_replacement_package_set_authority.py"
)
PACKAGE_SUPERSESSION_COMMIT_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0019_layer3_package_supersession_commit.py"
)
LAYER3_API = ROOT / "backend" / "app" / "api" / "layer3.py"
MODELS = ROOT / "backend" / "app" / "models" / "models.py"
SOURCE_BOUNDARY_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_source_boundary.py"
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
QUAL_APS_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_qual_aps_execution.py"
MOCKUP_BOUNDARY_SERVICE = ROOT / "backend" / "app" / "services" / "layer3_mockup_boundary.py"
SOURCE_BOUNDARY_TEST = ROOT / "backend" / "tests" / "test_layer3_source_boundary.py"
QUAL_APS_TEST = ROOT / "backend" / "tests" / "test_layer3_qual_aps_execution.py"
MOCKUP_BOUNDARY_TEST = ROOT / "backend" / "tests" / "test_layer3_mockup_boundary.py"
SESSION_ENTRY_TEST = ROOT / "backend" / "tests" / "test_layer3_session_entry.py"
GATE_B_STATE_TEST = ROOT / "backend" / "tests" / "test_layer3_gate_b_state.py"
REPLACEMENT_PACKAGE_SET_AUTHORITY_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_replacement_package_set_authority.py"
)
PACKAGE_SUPERSESSION_COMMIT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_package_supersession_commit.py"
)
SIGNED_REFERENCE_STATE_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_signed_reference_state.py"
)
LAYER3_API_TEST = ROOT / "backend" / "tests" / "test_layer3_api.py"
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
LAYER3_EXECUTION_REQUEST_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_execution_request_contract.py"
)
LAYER3_HANDOFF_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_handoff_contract.py"
)
LAYER3_PACKAGE_REVIEW_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_package_review_contract.py"
)
LAYER3_EXTERNAL_EXPORT_CONTRACT_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_external_export_contract.py"
)
LAYER3_JS = ROOT / "backend" / "app" / "review_ui" / "static" / "layer3.js"
LAYER3_WORKBENCH_E2E = ROOT / "e2e" / "layer3-workbench.spec.js"
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
            "defer remaining authentication/security",
            "merged PR #533 state_action_contract hardening",
            "PR #558 qualitative owner-service error-boundary proof",
            "non-security proof/state/refactor slice",
        ]
        for term in required_terms:
            if term not in next_required:
                errors.append(f"next_required_decision missing local near-term direction term: {term}")

    allowed_actions = decision.get("next_allowed_actions")
    if not isinstance(allowed_actions, list) or not allowed_actions:
        errors.append("layer3_workbench_current_decision.next_allowed_actions must be a non-empty list")
        return
    allowed_text = "\n".join(str(item) for item in allowed_actions)
    required_allowed = [
        "progress/proof/state drift checker",
        "state/action contract drift checker",
        "preview hash/idempotency follow-up",
        "revision recovery lifecycle freeze",
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
        "\"connector_key\": {\"description\": \"Known but non-admitted; service rejects fail-closed.\"}",
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
            "Only `package_supersession_preview_only`, `replacement_package_set_authority`, and `package_supersession_commit_entry` are admitted package lifecycle runtimes",
            "Existing bounded package construction/submit is not package mutation",
        ],
        CLOSEOUT_DOC: [
            "122_PACKAGE_MUTATION_FREEZE.md",
            "package_supersession_preview_only",
            "Read-only preview route is live; package supersession commit lineage route is live; broad package mutation/reconstruction remains blocked.",
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
        "\"package_payload\": {\"description\": \"Known but non-admitted; service rejects fail-closed.\"}",
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
            "`package_supersession_preview_only`, `replacement_package_set_authority`, and `package_supersession_commit_entry`",
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
        "\"replacement_output_package_ids\": {\"description\": \"Known but non-admitted; service rejects fail-closed.\"}",
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
        "\"package_payload\": {\"description\": \"Known but non-admitted; service rejects fail-closed.\"}",
        "\"package_supersession_commit\": {\"description\": \"Known but non-admitted; service rejects fail-closed.\"}",
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
            "Status: bounded merged-main proof snapshot through PR #584 plan-flow request contract extraction.",
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
            "proof_snapshot_head: `9cdd1e88`",
            "latest_proof_boundary_pr: `#584`",
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
    api_text = _read_required_text(LAYER3_API, errors)
    for term in (
        "class Layer3PreflightRequest(BaseModel):",
        "model_config = ConfigDict(extra=\"forbid\")",
        "PREFLIGHT_REQUEST_SCHEMA: dict[str, Any] = {",
        "\"additionalProperties\": False",
        "source-widening fields are rejected before service execution",
        "payload: Layer3PreflightRequest",
        "layer3_workbench.preflight(payload.model_dump(exclude_none=True))",
    ):
        if term not in api_text:
            errors.append(f"{_rel(LAYER3_API)} missing preflight request guard term: {term}")

    test_text = _read_required_text(LAYER3_API_TEST, errors)
    for term in (
        "test_layer3_api_preflight_rejects_extra_fields_before_service_execution",
        "api-preflight-strict-extra",
        "local_directory",
        "extra_forbidden",
        "preflight service should not run when request validation rejects extra fields",
    ):
        if term not in test_text:
            errors.append(f"{_rel(LAYER3_API_TEST)} missing preflight request guard test term: {term}")

    required_doc_terms = {
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


def _check_progress_text_surfaces(errors: list[str]) -> None:
    required_by_file = {
        BOARD: [
            "As of `2026-05-05`",
            "4d2bac8f68e52f7205210d19cce64576dc0384c4",
            "remaining authentication/security work is intentionally deferred",
            "PR `#531` now makes Gate B post-commit retry idempotency and material-preview hash hardening current-main bounded behavior",
            "PR `#533` now makes server-derived `state_action_contract` hardening current-main bounded behavior",
            "prefer non-security proof/state/refactor work",
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
    decision = manifest.get("layer3_workbench_current_decision")
    if not isinstance(decision, dict):
        return
    if decision.get("state") != live_state:
        errors.append(
            "layer3_workbench_current_decision must classify exact single APS-doc "
            "qualitative execution as current-main bounded behavior"
        )

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
        "test_layer3_readiness_contract_is_shared_without_behavior_change",
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
        "test_layer3_bootstrap_contract_is_shared_without_behavior_change",
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
        "test_layer3_state_model_contract_is_shared_without_behavior_change",
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
            "proof_snapshot_head: `9cdd1e88`",
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
            "proof_snapshot_head: `9cdd1e88`",
            "Focused execution-request-contract suite: 2 passed.",
            "Focused execution request API regression: 11 passed, 118 deselected, 4 warnings.",
            "Local focused Layer 3 backend suite: 302 passed, 4 warnings.",
            "Pre-merge PR #582 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #582: 5391af4e.",
            "Post-merge full Layer 3 backend suite: 302 passed, 4 warnings.",
            "proof/refactor hardening through PR #584",
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
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing plan-flow contract extraction term: {term}")
    for stale_term in (
        "PLAN_APPROVAL_FORBIDDEN_FIELDS = frozenset(",
        "PLAN_REVISION_FORBIDDEN_FIELDS = PLAN_APPROVAL_FORBIDDEN_FIELDS | frozenset(",
        "EXECUTION_SELECTION_FORBIDDEN_FIELDS = frozenset(",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns plan-flow contract term: {stale_term}")

    test_text = _read_required_text(LAYER3_PLAN_FLOW_CONTRACT_TEST, errors)
    for term in (
        "test_plan_flow_contract_is_shared_without_behavior_change",
        "test_plan_flow_contract_blocks_same_fields_as_legacy_logic",
        "layer3_workbench.PLAN_APPROVAL_FORBIDDEN_FIELDS",
        "contract.plan_approval_blocked_fields(approval_payload)",
        "contract.plan_revision_blocked_fields(revision_payload)",
        "contract.execution_selection_blocked_fields(selection_payload)",
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
            "proof_snapshot_head: `9cdd1e88`",
            "Focused plan-flow-contract suite: 2 passed.",
            "Focused plan-flow API regression: 3 passed, 124 deselected, 3 warnings.",
            "Local focused Layer 3 backend suite: 304 passed, 4 warnings.",
            "Pre-merge PR #584 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #584: 9cdd1e88.",
            "Post-merge full Layer 3 backend suite: 304 passed, 4 warnings.",
            "proof/refactor hardening through PR #584",
            "No broad execution, package mutation/reconstruction, package payload rewrite, source widening, connector/destination dispatch, provider/public URL support, broad qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior is admitted.",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing plan-flow contract extraction doc term: {term}")


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
            "proof_snapshot_head: `9cdd1e88`",
            "Focused handoff-contract suite: 2 passed.",
            "Focused handoff API regression: 18 passed, 111 deselected, 4 warnings.",
            "Local focused Layer 3 backend suite: 298 passed, 4 warnings.",
            "Pre-merge PR #578 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #578: df2a5c14.",
            "Post-merge full Layer 3 backend suite: 298 passed, 4 warnings.",
            "proof/refactor hardening through PR #584",
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
        "PACKAGE_REVIEW_PREVIEW_ALLOWED_FIELDS",
        "PACKAGE_CONSTRUCTION_COMMIT_FORBIDDEN_FIELDS",
        "PACKAGE_REVIEW_SUBMIT_FORBIDDEN_FIELDS",
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
            "proof_snapshot_head: `9cdd1e88`",
            "Focused package-review-contract suite: 2 passed.",
            "Focused package review API regression: 13 passed, 116 deselected, 4 warnings.",
            "Local focused Layer 3 backend suite: 300 passed, 4 warnings.",
            "Pre-merge PR #580 checks: backend-layer3-api SUCCESS; test SUCCESS.",
            "Merged main head after PR #580: 6b817f94.",
            "Post-merge full Layer 3 backend suite: 300 passed, 4 warnings.",
            "proof/refactor hardening through PR #584",
            "No package mutation/reconstruction, package payload rewrite, source widening, connector/destination dispatch, provider/public URL support, broad qualitative/hybrid/RAG execution, full mockup activation, or auth/security behavior is admitted.",
        ),
    }
    for path, terms in required_doc_terms.items():
        text = _read_required_text(path, errors)
        for term in terms:
            if term not in text:
                errors.append(f"{_rel(path)} missing package review contract extraction doc term: {term}")


def _check_external_export_contract_extraction(errors: list[str]) -> None:
    service_text = _read_required_text(EXTERNAL_EXPORT_CONTRACT_SERVICE, errors)
    for term in (
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS = frozenset(",
        "EXTERNAL_EXPORT_DOWNLOAD_PREPARE_FORBIDDEN_FIELDS = frozenset(",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_ALLOWED_FIELDS = EXTERNAL_EXPORT_DOWNLOAD_PREPARE_ALLOWED_FIELDS | frozenset(",
        "EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FORBIDDEN_FIELDS = frozenset(",
        "class ExternalExportDownloadDelivery",
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
        "external_export_download_prepare_blocked_fields(payload)",
        "external_export_download_delivery_blocked_fields(payload)",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing external export contract extraction term: {term}")
    for stale_term in (
        "from dataclasses import dataclass, field",
        "@dataclass(frozen=True)\nclass ExternalExportDownloadDelivery:",
    ):
        if stale_term in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} still owns external export contract term: {stale_term!r}")

    test_text = _read_required_text(LAYER3_EXTERNAL_EXPORT_CONTRACT_TEST, errors)
    for term in (
        "test_external_export_download_contract_is_shared_without_behavior_change",
        "test_external_export_download_contract_blocks_same_fields_as_legacy_logic",
        "ExternalExportDownloadDelivery",
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
            "proof_snapshot_head: `9cdd1e88`",
            "PR #575 external export/download contract extraction proof",
            "proof/refactor hardening through PR #584",
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
            "claim_gate_b_idempotency",
            "complete_gate_b_idempotency_claim",
            "gate_b_idempotency_claim_matches",
            "gate_b_idempotency_request_hash",
            "L3GateBIdempotencyKey",
        ],
        WORKBENCH_SERVICE: [
            "claim_gate_b_idempotency",
            "complete_gate_b_idempotency_claim",
            "find_gate_b_idempotency_claim",
            "gate_b_idempotency_in_progress",
        ],
        READINESS_CONTRACT_SERVICE: [
            "\"gate_b_decision_idempotency_scope\": \"durable_claim_and_post_commit_retry\"",
            "\"gate_b_decision_concurrent_duplicate_lock\": True",
        ],
        GATE_B_STATE_TEST: [
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
        QUAL_HYBRID_RAG_FREEZE,
        MOCKUP_TRUTH_FREEZE,
        PACKAGE_COMMIT_FREEZE,
        PACKAGE_REPLACEMENT_SET_FREEZE,
        STATE_ACTION_CONTRACT,
        SESSION_ENTRY_MIGRATION,
        GATE_B_IDEMPOTENCY_MIGRATION,
        REPLACEMENT_PACKAGE_SET_AUTHORITY_MIGRATION,
        PACKAGE_SUPERSESSION_COMMIT_MIGRATION,
        LAYER3_API,
        MODELS,
        GATE_B_STATE_SERVICE,
        SOURCE_BOUNDARY_SERVICE,
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
        EXECUTION_REQUEST_CONTRACT_SERVICE,
        PACKAGE_REVIEW_CONTRACT_SERVICE,
        EXTERNAL_EXPORT_CONTRACT_SERVICE,
        CONNECTOR_DISPATCH_SERVICE,
        PACKAGE_MUTATION_SERVICE,
        REPLACEMENT_PACKAGE_SET_AUTHORITY_SERVICE,
        PACKAGE_SUPERSESSION_COMMIT_SERVICE,
        LAYER3_JS,
        SOURCE_BOUNDARY_TEST,
        QUAL_APS_TEST,
        MOCKUP_BOUNDARY_TEST,
        SESSION_ENTRY_TEST,
        GATE_B_STATE_TEST,
        REPLACEMENT_PACKAGE_SET_AUTHORITY_TEST,
        PACKAGE_SUPERSESSION_COMMIT_TEST,
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
        LAYER3_EXECUTION_REQUEST_CONTRACT_TEST,
        HANDOFF_CONTRACT_SERVICE,
        LAYER3_HANDOFF_CONTRACT_TEST,
        LAYER3_PACKAGE_REVIEW_CONTRACT_TEST,
        LAYER3_EXTERNAL_EXPORT_CONTRACT_TEST,
        LAYER3_WORKBENCH_E2E,
        MOCKUP_ASSETS,
        MOCKUP_SPEC,
    ):
        _require_file(path, errors)

    manifest = _load_json(MANIFEST, errors)
    _load_json(PROOF_MANIFEST, errors)
    if manifest:
        _check_snapshot_consistency(manifest, errors)
        _check_summary_counts(manifest, errors)
        _check_current_decision(manifest, errors)
        _check_referenced_paths(manifest, errors)
    _check_local_boundary(errors)
    _check_connector_dispatch_entry_freeze(errors)
    _check_package_mutation_freeze(errors)
    _check_package_commit_entry_freeze(errors)
    _check_package_replacement_set_freeze(errors)
    _check_qualitative_capability_boundary(errors)
    _check_source_boundary_contract(errors)
    _check_mockup_truth_state_boundary(errors)
    _check_signed_reference_state_guard(errors)
    _check_gate_b_durable_idempotency_claim(errors)
    _check_preflight_request_guard(errors)
    _check_plan_preview_request_guard(errors)
    _check_source_preview_request_guard(errors)
    _check_material_preview_request_guard(errors)
    _check_session_status_migration_constraint(errors)
    _check_progress_text_surfaces(errors)
    _check_ci_layer3_backend_guardrail(errors)
    if manifest:
        _check_qualitative_progress_sync(manifest, errors)
    _check_state_action_contract_frontend_signature(errors)
    _check_response_contract_extraction(errors)
    _check_workbench_error_extraction(errors)
    _check_authority_rail_extraction(errors)
    _check_preview_contract_extraction(errors)
    _check_readiness_contract_extraction(errors)
    _check_bootstrap_contract_extraction(errors)
    _check_state_model_contract_extraction(errors)
    _check_plan_flow_contract_extraction(errors)
    _check_execution_request_contract_extraction(errors)
    _check_handoff_contract_extraction(errors)
    _check_package_review_contract_extraction(errors)
    _check_external_export_contract_extraction(errors)

    if errors:
        print("Layer 3 progress state check: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Layer 3 progress state check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
