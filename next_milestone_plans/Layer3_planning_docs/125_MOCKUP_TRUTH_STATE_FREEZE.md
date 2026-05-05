# Layer 3 Mockup Truth State Freeze

Status: mockup truth-state implementation-entry freeze for target-state-only mockup authority on branch `codex/l3-mockup-truth-state-freeze` from `project6-origin/main=86c899c0`.

This artifact freezes the current mockup boundary and prevents the tracked mockup inventory or preplanning spec from being treated as runtime implementation truth. It does not add rendered controls, routes, UI state, browser-local persistence, models, migrations, source ingestion, provider/public URLs, connector/destination dispatch, package mutation/reconstruction, qualitative/hybrid/RAG execution, hidden LLM planning, full mockup activation, or authentication/security work.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- implementation_branch: `codex/l3-mockup-truth-state-freeze`
- baseline_ref: `project6-origin/main`
- baseline_commit: `86c899c0`
- owner service: `backend/app/services/layer3_mockup_boundary.py`
- proof test: `backend/tests/test_layer3_mockup_boundary.py`
- progress checker: `tools/l3-progress-check.py`
- mockup inventory: `next_milestone_plans/layer3-mockups/assets.md`
- mockup spec: `next_milestone_plans/layer3-mockups/mockup-spec.txt`

## Decision

The selected mockup truth-state mode is exactly:

- selected_mockup_truth_state_mode: `mockups_target_state_only`

The tracked mockup artifacts remain available only as design/specification inputs:

- `next_milestone_plans/layer3-mockups/assets.md`
- `next_milestone_plans/layer3-mockups/mockup-spec.txt`

The following capabilities remain unsupported and must fail closed:

- `full_mockup_activation`
- `frontend_only_durable_state`
- `broad_execution`
- `broad_qualitative_execution`
- `hybrid_execution`
- `rag_vector_retrieval`
- `local_upload_or_directory_source_expansion`
- `provider_public_url`
- `connector_destination_dispatch`
- `package_mutation_reconstruction`
- `hidden_llm_planning`

No full mockup activation, frontend-only durable state, broad execution, source widening, connector/destination dispatch, provider/public URL support, package mutation/reconstruction, hidden LLM planning, or broad qualitative/hybrid/RAG execution is admitted.

## Runtime Contract

`backend/app/services/layer3_mockup_boundary.py` owns a response-safe contract:

- schema: `layer3.mockup_truth_state_contract.v1`
- mode: `mockups_target_state_only`
- authority_role: `target_state_design_specification`
- mockups_are_runtime_authority: `False`
- full_mockup_activation_enabled: `False`
- frontend_only_durable_state_enabled: `False`
- broad_execution_enabled: `False`
- source_widening_enabled: `False`
- connector_destination_dispatch_enabled: `False`
- package_mutation_reconstruction_enabled: `False`
- provider_public_url_enabled: `False`
- hidden_llm_planning_enabled: `False`
- mutates_runtime_state: `False`
- requires_later_freeze: `True`
- requires_browser_proof_before_ui_activation: `True`

The runtime contract is proof metadata only. It does not add a route, mutate a database row, write an artifact, activate a mockup screen, seed browser storage, create frontend-only durable state, or change the existing `/review/layer3` UI.

## Positive Invariants

- Mockup files remain target-state design/specification artifacts only.
- `full_mockup_activation` is explicitly present in `STATE_ACTION_DEFERRED_CAPABILITIES` with `admitted: False` and reason `mockups_target_state_only`.
- `mockup_truth_state_contract()` exposes the mockup source files, deferred capabilities, forbidden runtime fields, and required evidence for any later UI activation lane.
- Any future UI activation must provide a live source owner, route/API contract, server authority contract, negative invariant proof, headed browser proof, headless browser proof, and progress checker guard.
- `tools/l3-progress-check.py` fails if the mockup boundary service, proof test, deferred state/action capability, or mockup authority terms drift.

## Negative Invariants

This freeze must prove no accidental:

- full mockup activation
- frontend-only durable state
- browser-local persistence as authority
- broad execution
- broad qualitative/hybrid/RAG execution
- source upload, local directory, or source widening
- connector/destination dispatch
- provider/public URL support
- package mutation/reconstruction
- hidden LLM planning
- `L3PassRun` creation
- `AnalysisRun` creation
- output/package/handoff/export artifact creation
- schema/model/migration change
- authentication/security scope reopening

## Test And Proof Plan

Required local proof:

- `python -m py_compile .\backend\app\services\layer3_mockup_boundary.py .\tools\l3-progress-check.py`
- `python -m pytest .\backend\tests\test_layer3_mockup_boundary.py -q`
- `python .\tools\l3-progress-check.py`
- `git diff --check`

Optional regression proof before merge:

- `python -m pytest .\backend\tests\test_layer3_mockup_boundary.py .\backend\tests\test_layer3_page.py -q`

## Acceptance Criteria

This slice is accepted only when:

- this file exists and names `mockups_target_state_only`;
- `backend/app/services/layer3_mockup_boundary.py` exposes `mockup_truth_state_contract()` with full mockup activation and frontend-only durable state flags false;
- `backend/app/services/layer3_state_action_contract.py` keeps `full_mockup_activation` admitted false;
- `backend/tests/test_layer3_mockup_boundary.py` proves the contract and blocked runtime fields;
- `tools/l3-progress-check.py` requires this freeze, the contract helper, the proof test, and the tracked mockup authority terms;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` reference this freeze without claiming full mockup activation;
- required local proof commands pass.
