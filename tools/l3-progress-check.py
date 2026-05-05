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
PLANNING_DOCS = ROOT / "next_milestone_plans" / "Layer3_planning_docs"
QUAL_APS_FREEZE = PLANNING_DOCS / "114_QUAL_APS_EXEC_FREEZE.md"
LOCAL_BOUNDARY = PLANNING_DOCS / "116_SECURITY_SOURCE_DELIVERY_BOUNDARY_FREEZE.md"
SYNTHESIS_BOUNDARY = PLANNING_DOCS / "117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md"
GOAL_AUDIT = PLANNING_DOCS / "118_L3_GOAL_AUDIT.md"
QUAL_APS_ENTRY_FREEZE = PLANNING_DOCS / "119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md"
STATE_ACTION_CONTRACT = (
    ROOT / "backend" / "app" / "services" / "layer3_state_action_contract.py"
)
WORKBENCH_SERVICE = (
    ROOT / "backend" / "app" / "services" / "layer3_workbench.py"
)

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


def main() -> int:
    errors: list[str] = []
    for path in (
        MANIFEST,
        BOARD,
        REFRESH_SPEC,
        PROGRESS_PROMPT,
        PROOF_MANIFEST,
        PLAYWRIGHT_WORKFLOW,
        QUAL_APS_FREEZE,
        LOCAL_BOUNDARY,
        SYNTHESIS_BOUNDARY,
        GOAL_AUDIT,
        QUAL_APS_ENTRY_FREEZE,
        STATE_ACTION_CONTRACT,
        WORKBENCH_SERVICE,
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
    _check_qualitative_capability_boundary(errors)
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
