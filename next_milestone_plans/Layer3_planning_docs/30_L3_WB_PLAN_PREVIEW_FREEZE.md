# Layer 3 Workbench Plan Preview Freeze

## Status

- planning-only second-slice freeze merged by PR `#191`
- not active implementation by itself
- outside the accepted Phase 1A normative control spine
- outside the settled later APS family packet
- subordinate to `24_L3_WB_FREEZE.md`, `26_L3_WB_INPUTS.md`, `28_L3_WB_FIRST_SLICE_FREEZE.md`, and `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`

This document freezes the next narrow Layer 3 workbench slice after the landed PR `#184` first-slice shell/API and its closeouts through PR `#189`.

The slice is **plan preview only**. It admits a read-only operator-visible plan-review step after Gate C typing has been explicitly committed through the existing first-slice API. It does not admit execution, results, package review, handoff, runtime snapshot DB writes, schema widening, qualitative/hybrid/RAG/vector execution, or automated plan generation.

## Purpose

The live first slice proves the workbench can take an operator from intent/preflight through source preview, material preview, Gate B material decisions, Gate C typing preview, explicit Gate C typing materialization when `commit_typing` is true, and session summary.

The next useful slice is to let the operator see what the already-landed Layer 3 pass-entry owner service would consider admissible for a bounded quantitative plan, without actually creating `L3AnalysisPlan`, creating `L3PassRun`, executing analysis, writing artifacts, or moving into package/reconciliation.

This freeze exists so the later implementation pass can enable the `plan` step without silently reopening downstream execution.

## Authority Basis

Use this order:

1. Current `project6-origin/main` live code and tests.
2. The landed first-slice planning docs: `28_L3_WB_FIRST_SLICE_FREEZE.md` and `29_L3_WB_FIRST_SLICE_API_AND_STATE_CONTRACT.md`.
3. The broader workbench prep docs: `24_L3_WB_FREEZE.md` and `26_L3_WB_INPUTS.md`.
4. The repo-tracked mockup spec: `next_milestone_plans/layer3-mockups/mockup-spec.txt`.

Relevant live owner surfaces:

- `backend/app/api/layer3.py`
- `backend/app/services/layer3_workbench.py`
- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/layer3_typing_entry.py`
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

- one plan-preview UI section inside the existing `/review/layer3` shell
- one `plan` step state that becomes available only after explicit Gate C typing commit
- one plan-preview API request/response family under `/api/v1/layer3/...`
- one workbench service function that delegates plan-preview computation to a public owner-service helper rather than duplicating pass-entry logic in browser or route code
- one read-only owner-service helper in `layer3_pass_entry.py` if no existing public helper can produce the required preview without side effects
- backend/API/page/browser tests proving preview-only behavior and downstream gates still disabled

The later implementation may expose:

- admitted analysis sets
- excluded analysis sets with reason codes
- planned pass count and pass-type summary
- candidate pass scopes currently supported by the owner service
- source material and typing provenance needed to explain why each set is admissible or excluded
- warnings for partial, unsupported, or incomplete typed material

## Explicit Non-Admitted Scope

This freeze does not admit:

- calling `materialize_pass_entry(...)` from the workbench API, because that function currently creates plans, creates pass runs, executes passes, and commits state
- creating `L3AnalysisPlan`
- creating `L3PassRun`
- creating analysis runs
- writing input or output manifests
- changing session status to active execution
- changing package/reconciliation state
- enabling package review or handoff
- enabling qualitative execution
- enabling hybrid execution
- enabling RAG/vector execution
- adding migrations or widening existing schema
- writing review/runtime snapshot databases
- adding generic route/UI widening outside `/review/layer3`
- reusing Candidate B, compare, review, document-trace, or analyst-insight surfaces as the Layer 3 plan-review owner
- route-local reimplementation of Layer 3 owner-service logic
- hidden LLM planning or unreviewed natural-language decomposition

## Required Plan-Preview Semantics

The plan preview must be deterministic with respect to the existing durable Layer 3 session state.

Minimum input prerequisites:

- a valid Layer 3 session id
- Gate B-approved material already persisted through the first-slice decision path
- Gate C typing explicitly committed through the owner-service path
- at least one durable analysis set that the pass-entry owner-service rules can classify

Minimum fail-closed cases:

- unknown session
- session without approved material
- session without committed Gate C typing
- session with no analysis sets
- session whose typed material is not admissible for the currently supported quantitative pass-entry rules
- session that already has a materialized plan or pass run, unless a later freeze admits existing-plan review

The preview response must distinguish:

- `admitted_sets`
- `excluded_sets`
- `planned_passes`
- `warnings`
- `owner_service_basis`
- `preview_only: true`

## UI Presentation Contract

The existing workflow stepper may enable `plan` only when a preview can be requested from a committed Gate C session.

The `execution`, `results`, and `package` steps must remain disabled.

The UI should show:

- a compact plan summary band
- a table or dense list of admitted sets
- an adjacent list of exclusions and warnings
- source and typing provenance for each planned pass
- explicit labels that the plan is preview-only and not executed
- disabled or absent execution controls

The UI must not show a working "run", "execute", "package", "handoff", "rerun", "auto-plan", or "LLM plan" control.

## Backend Ownership Contract

The later implementation should not duplicate `layer3_pass_entry` classification semantics in `layer3_workbench.py`.

Preferred owner-service shape:

- add a public read-only helper in `backend/app/services/layer3_pass_entry.py`
- reuse the same classification and plan-payload basis as pass entry
- do not call `_materialize_analysis_plan`
- do not call `_execute_passes`
- do not call `db.add` for plan or pass-run rows
- do not call `db.commit`

`layer3_workbench.py` may translate that owner-service result into the workbench API DTO and authority rail.

## Proof Requirements

The later implementation pass must prove:

- plan preview is unavailable before Gate C commit
- plan preview is available after explicit Gate C commit for an admissible quantitative session
- plan preview returns admitted and excluded sets without creating `L3AnalysisPlan` or `L3PassRun`
- downstream execution/results/package gates remain disabled in the API and UI
- no migration files are added
- no runtime snapshot DB writes are introduced
- existing first-slice API and page behavior remains intact
- headed and headless Chromium both pass the operator path

Minimum proof files:

- `backend/tests/test_layer3_workbench.py`
- `backend/tests/test_layer3_api.py`
- `backend/tests/test_layer3_page.py`
- `backend/tests/test_layer3_pass_entry.py` if a new owner-service preview helper is added
- `e2e/layer3-workbench.spec.js`

## Stop Conditions

Stop and reopen planning before implementation if the slice needs:

- actual pass execution
- persistent plan approval
- package review
- handoff initiation
- new schema
- new migrations
- runtime snapshot DB writes
- qualitative, hybrid, or RAG/vector analysis
- existing-plan editing
- LLM-generated plan content
- broader route or adjacent-surface redesign

## Relationship To Later Work

This freeze is the second workbench slice only. A later freeze may admit plan approval, plan materialization, execution monitoring, results review, package review, or handoff. Those must remain separate until explicitly frozen.
