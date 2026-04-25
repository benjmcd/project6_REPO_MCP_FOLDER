# Layer 3 Workbench Result Review UI Freeze

Status: governing planning-only freeze for a future bounded `/review/layer3` result-review presentation slice after merged PR `#227`.

This document freezes only the user-facing presentation and control boundary for the already-live backend selected-pass result-review state. It does not implement UI behavior by itself, does not change backend API behavior, and does not admit execution selection/start UI, package review, handoff/export, rerun/recovery, source expansion, schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Current Live Boundary

Current `project6-origin/main` through PR `#229` includes:

- the `/review/layer3` workbench shell from PR `#184`
- read-only plan preview from PR `#194`
- approval-only plan persistence from PR `#199`
- pre-approval plan revision-control from PR `#205` and PR `#207`
- read-only execution-readiness proof from PR `#213`
- backend execution-selection/pass-run shell creation from PR `#216`
- backend selected-pass analysis-execution start from PR `#218`
- backend selected-pass result/status inspection from PR `#222`
- backend selected-pass result-review recording from PR `#227`
- result-review progress-state vocabulary/render declaration from PR `#229`

The rendered `/review/layer3` UI still stops at the intent/source/material/Gate B/Gate C/plan interaction path. The page contains disabled execution/results/package step chips, but it does not expose execution selection controls, execution-start controls, result/status inspection controls, or result-review controls. Current UI JavaScript does not currently consume the session summary endpoint as a state-rehydration source for post-plan execution/result state.

## Slice Decision

The next admitted UI planning boundary is:

> Present the already-live selected-pass result/status and result-review state on `/review/layer3`, and allow a bounded result-review operator decision only when server-authoritative session summary and result/status authority prove one selected terminal pass is eligible. Do not add execution selection/start controls, package review, handoff/export, rerun/recovery, source/schema/runtime widening, or full mockup behavior.

This is the smallest safe UI step after PR `#227` because it can make the existing backend result-review endpoint operable from the workbench surface without inventing new backend semantics or jumping to package/handoff workflow.

## Admitted Future UI Scope

A future implementation PR governed by this freeze may change only:

- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`
- `backend/app/review_ui/static/layer3.js`
- narrowly related page tests or browser tests that prove the changed `/review/layer3` behavior

The implementation may:

- read `GET /api/v1/layer3/session/{session_id}` after a session exists
- render server-authoritative execution-selection, analysis-execution-start, result/status, and result-review posture when the session summary exposes it
- call `POST /api/v1/layer3/execution/result/status` only for the selected terminal pass represented by server authority
- call `POST /api/v1/layer3/execution/result/review` only for the same selected terminal pass after result/status availability is proven
- show selected pass id, analysis plan id, preview id/hash, analysis run id when available, terminal pass status, output metadata reference, result/status availability, trace summary, review state, operator decision, and downstream-unavailable posture
- provide a bounded operator decision control for `approved`, `changes_requested`, `rejected`, or `blocked`
- provide bounded review notes/caveats
- show package review and handoff as disabled or unavailable after result review
- keep execution/results/package step chips accurate to server state without treating stepper state as authority

The UI must rely on server state and responses as authority. Browser state may cache or display values, but browser state must not authorize review, approve a result, select passes, start execution, package output, hand off output, or recover/rerun a pass.

## Explicit Non-Goals

This freeze does not admit:

- execution-selection UI controls
- analysis-execution-start UI controls
- free-form pass-run id entry by the operator
- package review UI
- package artifact creation
- package variant tabs
- handoff/export UI
- handoff/export artifacts
- rerun, retry, recovery, cancellation, or replay controls
- raw output editing
- output-file rewrite behavior
- result-review amendment or supersession
- multi-pass result review
- batch result review
- source-picker expansion
- local upload or local-directory ingestion
- schema migrations
- runtime snapshot DB writes
- new backend endpoint creation by default
- qualitative, hybrid, RAG, or vector execution UI
- full mockup activation

If implementation proves that execution selection/start UI must exist before result review can be operated safely, stop and freeze that UI slice separately. This document does not authorize filling that gap opportunistically.

## Presentation Requirements

The future panel must make these distinctions visible without implying downstream activation:

| Area | Required presentation | Must not imply |
| --- | --- | --- |
| Execution selection | Show selected-pass state only when provided by server summary | Operator can freely select or batch passes |
| Execution start | Show prior execution-start state when present | UI can start or rerun execution |
| Result/status | Show terminal status and output metadata authority | Result approval has happened |
| Result review | Show available/recorded/blocked review state | Package construction or handoff is unlocked |
| Trace | Show available trace summary and unresolved trace count when present | Missing trace can be invented in browser |
| Package/handoff | Show disabled or unavailable posture | Approved result creates package/handoff state |

When a review is already recorded, the UI must render it as existing server state and avoid offering conflicting review submission controls unless a later freeze admits amendment or supersession.

## State Gating

The UI may enable the result-review submission control only when all of the following are true:

1. a session id exists
2. the session summary identifies an approved plan and approved preview id/hash
3. execution selection is server-confirmed for the session
4. the selected pass is terminal and belongs to the session and approved plan
5. result/status authority is available for that pass
6. no conflicting result-review record is already present
7. package review and handoff remain disabled

If any of these are absent, the UI must show a blocked or unavailable state and avoid submitting result-review requests.

## Backend Boundary

This UI freeze expects the implementation to use existing backend routes:

- `GET /api/v1/layer3/session/{session_id}`
- `POST /api/v1/layer3/execution/result/status`
- `POST /api/v1/layer3/execution/result/review`

If these routes do not provide enough data for a safe UI implementation, the implementation must stop and add a separate API/state freeze before changing backend behavior. This document does not authorize new API fields, tables, migrations, artifacts, package rows, handoff rows, source-ingestion rows, or runtime DB writes by default.

## Required Proof

An implementation PR governed by this freeze must prove:

- no backend behavior changes unless a separate freeze explicitly admits them
- disabled execution, result, package, and handoff states render correctly before server authority is available
- result/status can be requested only for a server-selected terminal pass
- result review can be submitted only after result/status availability
- already-recorded review state renders without offering conflicting amendment controls
- package review and handoff remain unavailable after approval, rejection, changes-requested, or blocked review decisions
- stale preview/hash, missing output metadata, unresolved trace, unsupported source breadth, duplicate conflict, foreign pass, or authority mismatch render as blocked or unavailable
- the UI does not collect or submit forbidden fields such as package, handoff, export, rerun, retry, recovery, source expansion, local upload, schema migration, runtime DB write, output rewrite, or multi-pass ids
- relevant backend Layer 3 tests still pass
- page/static tests cover disabled and available UI states
- both headed and headless Chrome browser proof pass because rendered UI behavior changes

## Stop Conditions

Stop before implementation if any of these becomes necessary:

- new backend endpoint or schema field beyond a separately frozen API/state contract
- execution selection/start UI controls
- package construction or package review
- handoff/export behavior
- rerun/recovery/cancellation/retry behavior
- result amendment or supersession
- source expansion or local ingestion
- runtime DB or schema widening
- full mockup activation

## Relationship To Existing Docs

This freeze is downstream of:

- `44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`
- `42_L3_WB_RESULT_STATUS_FREEZE.md`
- `43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`
- `40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md`
- `41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md`
- `38_L3_WB_EXECUTION_SELECTION_FREEZE.md`
- `39_L3_WB_EXECUTION_SELECTION_API_AND_STATE_CONTRACT.md`

It freezes only a future UI presentation and bounded result-review control surface for current backend result-review state. It does not replace the backend result-review docs and does not make UI behavior live by itself.
