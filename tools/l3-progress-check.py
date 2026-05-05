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
STATE_ACTION_CONTRACT = (
    ROOT / "backend" / "app" / "services" / "layer3_state_action_contract.py"
)
SESSION_ENTRY_MIGRATION = (
    ROOT / "backend" / "alembic" / "versions" / "0012_layer3_session_entry.py"
)
LAYER3_API = ROOT / "backend" / "app" / "api" / "layer3.py"
SOURCE_BOUNDARY_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_source_boundary.py"
)
SIGNED_REFERENCE_STATE_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_signed_reference_state.py"
)
WORKBENCH_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_workbench.py"
)
CONNECTOR_DISPATCH_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_connector_dispatch_entry.py"
)
PACKAGE_MUTATION_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_package_mutation_entry.py"
)
SOURCE_BOUNDARY_TEST = ROOT / "backend" / "tests" / "test_layer3_source_boundary.py"
SESSION_ENTRY_TEST = ROOT / "backend" / "tests" / "test_layer3_session_entry.py"
SIGNED_REFERENCE_STATE_TEST = (
    ROOT / "backend" / "tests" / "test_layer3_signed_reference_state.py"
)
LAYER3_API_TEST = ROOT / "backend" / "tests" / "test_layer3_api.py"

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
        "frontend server-contract consumption",
        "no-behavior-change service extraction",
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
    for term in (
        "CONNECTOR_DISPATCH_RECORDED_STATE = \"connector_dispatch_recorded\"",
        "\"internal_connector_dispatch_record\"",
        "\"internal_connector_dispatch_record_admitted\": True",
        "\"internal_connector_dispatch_record_endpoint\": f\"{API_ROOT}/handoff/connector/record\"",
        "\"dispatch_admitted\": False",
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing connector readiness term: {term}")

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
            "runtime package mutation/reconstruction commit remains not admitted",
            "no database writes, no package payload writes, and no in-place mutation",
        ],
        GOAL_AUDIT: [
            "122_PACKAGE_MUTATION_FREEZE.md",
            "Read-only supersession preview implementation is live and tested",
            "Only `package_supersession_preview_only` is admitted",
            "Existing bounded package construction/submit is not package mutation",
        ],
        CLOSEOUT_DOC: [
            "122_PACKAGE_MUTATION_FREEZE.md",
            "package_supersession_preview_only",
            "Read-only preview route is live; package mutation/reconstruction commit remains blocked.",
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
                "package_supersession_commit",
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
    for term in (
        "\"package_supersession_preview\"",
        "\"package_supersession_preview_admitted\": True",
        "\"package_supersession_preview_endpoint\": f\"{API_ROOT}/package/mutation/preview\"",
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
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing package mutation blocked-field term: {term}")

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

    workbench_text = _read_required_text(WORKBENCH_SERVICE, errors)
    for term in (
        '"single_aps_doc_qualitative_execution_admitted": True',
        '"single_aps_doc_qualitative_execution": True',
        '"broad_qualitative_execution": False',
        '"hybrid_execution": False',
        '"rag_vector_retrieval": False',
    ):
        if term not in workbench_text:
            errors.append(f"{_rel(WORKBENCH_SERVICE)} missing qualitative boundary term: {term}")

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
        ],
        GOAL_AUDIT: [
            "The active goal is not complete.",
            "Only `single_aps_doc_qualitative_pass` is admitted",
            "broad qualitative execution beyond the single APS-document qualitative pass",
        ],
        QUAL_APS_ENTRY_FREEZE: [
            "selected the single APS content-document qualitative lane",
            "No other qualitative, hybrid, RAG, vector, cohort, comparative, cross-document, connector, provider, package, or full-mockup behavior is admitted.",
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

    expected_supported = ("dataset_version", "aps_content_document")
    expected_unsupported = (
        "rag_vector_index",
        "arbitrary_local_directory",
        "broad_file_upload",
        "web_connector",
        "unbounded_runtime_db",
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

    service_text = _read_required_text(SOURCE_BOUNDARY_SERVICE, errors)
    for term in (
        "def requested_source_classes(",
        "def unsupported_requested(",
        "def source_class_from_source_candidate_id(",
        "def source_class_from_material_candidate_id(",
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
    for term in expected_supported + expected_unsupported:
        if term not in test_text:
            errors.append(f"{_rel(SOURCE_BOUNDARY_TEST)} missing source class proof term: {term}")

    required_doc_terms = {
        SYNTHESIS_BOUNDARY: [
            "backend/app/services/layer3_source_boundary.py",
            "SUPPORTED_SOURCE_CLASSES",
            "UNSUPPORTED_SOURCE_CLASSES",
            "backend/tests/test_layer3_source_boundary.py",
        ],
        GOAL_AUDIT: [
            "current-main completion audit after PR #538 merged",
            "backend/app/services/layer3_source_boundary.py",
            "backend/tests/test_layer3_source_boundary.py",
            "does not widen source classes",
            "267 passed",
        ],
        CLOSEOUT_DOC: [
            "Status: current-main closeout after PR #538 merged at `project6-origin/main=329fc6d5`",
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
        STATE_ACTION_CONTRACT,
        SESSION_ENTRY_MIGRATION,
        LAYER3_API,
        SOURCE_BOUNDARY_SERVICE,
        WORKBENCH_SERVICE,
        CONNECTOR_DISPATCH_SERVICE,
        PACKAGE_MUTATION_SERVICE,
        SOURCE_BOUNDARY_TEST,
        SESSION_ENTRY_TEST,
        SIGNED_REFERENCE_STATE_SERVICE,
        SIGNED_REFERENCE_STATE_TEST,
        LAYER3_API_TEST,
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
    _check_qualitative_capability_boundary(errors)
    _check_source_boundary_contract(errors)
    _check_signed_reference_state_guard(errors)
    _check_plan_preview_request_guard(errors)
    _check_source_preview_request_guard(errors)
    _check_material_preview_request_guard(errors)
    _check_session_status_migration_constraint(errors)
    _check_progress_text_surfaces(errors)
    _check_ci_layer3_backend_guardrail(errors)

    if errors:
        print("Layer 3 progress state check: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Layer 3 progress state check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
