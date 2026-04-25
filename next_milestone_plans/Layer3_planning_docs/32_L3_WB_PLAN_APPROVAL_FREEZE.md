# Layer 3 Workbench Plan Approval Freeze

## Status

- planning-only candidate third-slice freeze
- not active implementation by itself
- outside the accepted Phase 1A normative control spine
- outside the settled later APS family packet
- subordinate to `28_L3_WB_FIRST_SLICE_FREEZE.md`, `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`, `30_L3_WB_PLAN_PREVIEW_FREEZE.md`, and `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md`

This document freezes the next narrow Layer 3 workbench slice after the landed read-only plan-preview implementation.

The slice is **plan approval only**. It admits operator approval and durable formation of the owner-service plan that was already shown through read-only plan preview. It does not admit pass execution, result review, package review, handoff, runtime snapshot DB writes, schema widening, qualitative/hybrid/RAG/vector execution, automated plan generation, or hidden LLM planning.

## Purpose

Current `main` lets the operator reach read-only plan preview after explicit Gate C typing commit. The preview is derived from `backend/app/services/layer3_pass_entry.py::preview_pass_entry(...)` and intentionally does not create `L3AnalysisPlan` or `L3PassRun`.

The next useful slice is to let the operator explicitly approve that deterministic owner-service plan and persist the approved plan boundary, while still stopping before pass-run creation and execution.

This freeze exists because the existing `materialize_pass_entry(...)` helper is too broad for this slice: it forms a plan, creates pass runs, starts execution, writes artifacts, updates session completion state, and commits. A later implementation must add a narrower owner-service helper instead of calling that execution-bearing helper.

## Authority Basis

Use this order:

1. Current `project6-origin/main` live code and tests.
2. The landed plan-preview docs: `30_L3_WB_PLAN_PREVIEW_FREEZE.md` and `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md`.
3. The landed first-slice docs: `28_L3_WB_FIRST_SLICE_FREEZE.md` and `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`.
4. The broader workbench prep docs: `24_L3_WB_FREEZE.md` and `26_L3_WB_INPUTS.md`.
5. The repo-tracked mockup spec: `next_milestone_plans/layer3-mockups/mockup-spec.txt`.

Relevant live owner surfaces:

- `backend/app/api/layer3.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`
- `backend/app/review_ui/static/layer3.js`
- `backend/tests/test_layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_page.py`
- `backend/tests/test_layer3_pass_entry.py`
- `e2e/layer3-workbench.spec.js`

## Admitted Slice

The next implementation pass may add:

- one plan-approval UI action inside the existing `/review/layer3` plan panel
- one `plan` step state that moves from preview-ready to approved only after explicit operator action
- one plan-approval API request/response family under `/api/v1/layer3/...`
- one workbench service function that delegates approval to the Layer 3 pass-entry owner service
- one owner-service helper in `layer3_pass_entry.py` that persists an approved `L3AnalysisPlan` from the same classification and plan-payload basis used by preview
- backend/API/page/browser tests proving approval-only behavior and downstream gates still disabled

The later implementation may persist:

- one `L3AnalysisPlan` row for the session
- `analysis_set_ids_json` derived from the same admitted sets as the owner-service preview
- `plan_json` derived from the same deterministic owner-service plan payload used by preview
- `status` on the plan as a non-executed approved/formed planning state
- `approved_by_operator: true`
- `approved_at`
- a session summary entry identifying the approved plan and preview basis

## Explicit Non-Admitted Scope

This freeze does not admit:

- calling `materialize_pass_entry(...)` from the workbench API or UI path
- calling `_execute_passes(...)`
- creating `L3PassRun`
- creating analysis runs
- writing input or output manifests
- persisting derived cohort datasets
- changing session status to active execution
- marking pass runs running, completed, or failed
- showing result review as active
- enabling package review or handoff
- enabling qualitative execution
- enabling hybrid execution
- enabling RAG/vector execution
- adding migrations or widening existing schema
- writing review/runtime snapshot databases
- adding generic route/UI widening outside `/review/layer3`
- route-local reimplementation of Layer 3 owner-service classification or plan-payload logic
- hidden LLM planning or unreviewed natural-language decomposition

## Required Plan-Approval Semantics

Plan approval must be deterministic with respect to the current durable Layer 3 session state.

Minimum input prerequisites:

- a valid Layer 3 session id
- Gate B-approved material persisted through the first-slice decision path
- Gate C typing explicitly committed through the owner-service path
- an owner-service plan preview that is still reproducible from current server state
- at least one admissible quantitative analysis set under the current pass-entry rules
- no existing `L3AnalysisPlan` for the session
- no existing `L3PassRun` for the session

Minimum fail-closed cases:

- unknown session
- session without approved material
- session without committed Gate C typing
- session with no admissible owner-service plan
- supplied preview id or preview hash does not match current server recomputation
- session already has an analysis plan
- session already has pass runs
- request includes execution, package, handoff, natural-language plan, or arbitrary plan-editing fields

The approval response must distinguish:

- `analysis_plan_id`
- `plan_status`
- `approved_by_operator`
- `approved_at`
- `approved_sets`
- `excluded_sets`
- `planned_passes`
- `warnings`
- `owner_service_basis`
- `approval_only: true`
- `execution_started: false`

## UI Presentation Contract

The UI may show a single plan-approval action only when a read-only plan preview is available from committed Gate C state.

After approval, the UI should show:

- approved plan id
- approved timestamp
- approved set count
- excluded set count
- planned pass summary
- owner-service basis
- explicit label that execution has not started

The `execution`, `results`, and `package` steps must remain disabled.

The UI must not show a working "run", "execute", "package", "handoff", "rerun", "auto-plan", or "LLM plan" control.

## Backend Ownership Contract

The implementation must not duplicate `layer3_pass_entry` classification semantics in `layer3_workbench.py`.

Preferred owner-service shape:

- add a public approval helper in `backend/app/services/layer3_pass_entry.py`
- recompute the preview from current durable state
- compare any submitted preview id/hash against the recomputed preview
- persist only the approved `L3AnalysisPlan`
- preserve the preview's excluded-set and warning context in `plan_json`
- do not call `_execute_passes`
- do not create `L3PassRun`
- do not call `run_analysis`
- do not write artifact manifests

`layer3_workbench.py` may translate that owner-service result into the workbench API DTO and authority rail.

## Proof Requirements

The later implementation pass must prove:

- plan approval is unavailable before Gate C commit
- plan approval is unavailable without a reproducible owner-service preview
- plan approval creates exactly one `L3AnalysisPlan`
- plan approval sets operator-approval metadata
- plan approval does not create `L3PassRun`
- plan approval does not call analysis execution
- plan approval does not write input/output manifests
- downstream execution/results/package gates remain disabled in the API and UI
- no migration files are added
- no runtime snapshot DB writes are introduced
- existing first-slice and plan-preview behavior remains intact
- headed and headless Chromium both pass the operator path

Minimum proof files:

- `backend/tests/test_layer3_pass_entry.py`
- `backend/tests/test_layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_page.py`
- `e2e/layer3-workbench.spec.js`

## Stop Conditions

Stop and reopen planning before implementation if the slice needs:

- pass execution
- `L3PassRun` creation
- analysis artifact writing
- package review
- handoff initiation
- new schema
- new migrations
- runtime snapshot DB writes
- qualitative, hybrid, or RAG/vector analysis
- plan editing
- LLM-generated plan content
- broader route or adjacent-surface redesign

## Relationship To Later Work

This freeze is the third workbench slice only. A later freeze may admit execution start/monitoring, results review, package review, or handoff. Those must remain separate until explicitly frozen.
