# Layer 3 Workbench Result Status Freeze

Status: governing freeze for the bounded result/status tranche after merged PR `#218`.

Implementation note as of April 25, 2026: PR `#222` implements this freeze on `project6-origin/main` as a read-only backend endpoint. The implementation remains limited to selected-pass status/execution-proof inspection and does not admit result review, package review, handoff, source/schema/runtime widening, UI activation, qualitative/hybrid/RAG/vector execution, rerun/recovery, or full mockup behavior.

This document freezes the narrowest eligible boundary after selected-pass analysis-execution start: read-only status and execution-proof inspection for one completed or failed selected `L3PassRun`, while keeping result review, result approval, package review, handoff, source expansion, approved-plan supersession, runtime DB/schema widening, UI/full mockup activation, qualitative execution, hybrid execution, and RAG/vector retrieval out of scope.

## Current Live Boundary

Current `project6-origin/main` already ships:

- first-slice shell/API from PR `#184`, with closeout/correction passes through PR `#190`
- read-only plan preview from PR `#194`, with proof/board metadata closeouts from PRs `#195` and `#196`
- approval-only `L3AnalysisPlan` persistence from PR `#199`
- pre-approval plan rejection/revision-control from PR `#205`, hardened by PR `#207`
- execution-readiness proof/state packet from PR `#212`
- read-only readiness proof from PR `#213`
- execution-selection freeze packet from PR `#215`
- selected/not-started `L3PassRun` shell creation from PR `#216`
- analysis-execution-start freeze/API-state docs from PR `#217`
- bounded selected-pass analysis-execution-start implementation from PR `#218`

The PR `#218` live boundary is exactly one existing selected/not-started single-item wrapped quantitative `L3PassRun` shell transitioned through `POST /api/v1/layer3/execution/start`, producing one wrapped quantitative `AnalysisRun` plus selected-pass output metadata. Current `main` still does not ship result review, result approval/rejection, package review, handoff, batch execution, broad analysis execution, approved-plan correction or supersession, source-breadth expansion, runtime DB/schema widening, qualitative/hybrid/RAG/vector execution, local upload/directory ingestion, UI changes, or full mockup activation.

## Problem Statement

PR `#218` creates the first execution output that a later operator workflow will need to inspect. The current implementation deliberately leaves `downstream_unavailable` at the execution boundary and keeps result/package/handoff states closed. That means the next tranche cannot safely jump directly to result review or package construction.

The next safe planning unit is a read-only result-status boundary. It should let the workbench prove what happened to the selected pass, locate the raw execution output metadata, and report whether the selected pass completed, completed with warnings, or failed. It should not interpret the output as approved findings, package material, handoff material, or a finalized result taxonomy.

## Slice Decision

The next adequate Layer 3 workbench tranche is:

> Freeze selected-pass result/status inspection as a read-only execution-proof boundary after PR `#218`: one existing terminal selected `L3PassRun` may be inspected through server authority, exposing normalized status and raw output metadata summary only, without opening result review, package review, handoff, source expansion, schema/runtime widening, or full mockup UI behavior.

This is smaller and safer than result review because it does not require final taxonomy decisions for datum/fact/finding/insight/caveat/result/package, does not add operator approval/rejection semantics, and does not create new downstream artifacts.

## Admitted Implementation Scope

An implementation PR governed by this freeze may add only:

- one read-only selected-pass result/status endpoint under the existing Layer 3 API family
- validation that the session already has exactly one current approved `L3AnalysisPlan`
- validation that the pass belongs to the approved plan and current session
- validation that the supplied preview id/hash still match the approved plan and execution-selection state
- validation that PR `#218` analysis-execution-start state exists for the selected pass, unless the pass is terminal failed with error metadata
- validation that the requested `pass_run_id` identifies a selected pass in a terminal status: `completed`, `completed_with_warnings`, or `failed`
- read-only lookup of the associated `AnalysisRun` id when present
- read-only lookup of the pass-run `output_payload_ref` when present
- a minimal raw output metadata summary, if the existing output metadata file can be read without generating, mutating, seeding, or migrating anything
- normalized result/status fields, such as terminal pass status, output metadata presence, warnings-present flag, error metadata presence, and downstream unavailable labels
- session summary state that remains display-only if the implementation proves it does not write new durable state; any durable write requires a separate write-boundary justification
- focused backend tests proving successful status inspection, fail-closed stale preview behavior, no writes, no result review, no package/handoff, and output-metadata absence/error handling
- headed and headless browser proof only if rendered `/review/layer3` behavior changes

## Explicit Non-Goals

This freeze does not admit:

- result review UI
- result approval, rejection, editing, or operator signoff semantics
- package review UI or package artifacts
- handoff UI, handoff artifacts, export behavior, or APS downstream activation
- creating a new `AnalysisRun`
- creating a new `L3AnalysisPlan`
- creating a new `L3PassRun`
- running or rerunning analysis
- cancelling, retrying, recovering, or replaying a failed selected pass
- executing more than one selected pass run per request
- reading or comparing unrelated pass runs
- changing the approved plan or execution selection
- approved-plan cancellation, replacement, reopening, or supersession
- local upload ingestion
- local directory ingestion
- RAG/vector retrieval
- qualitative or hybrid execution
- runtime snapshot DB writes
- schema migrations
- result/package/handoff artifact manifests
- background worker queues, leases, cancellation, or retry orchestration
- full mockup activation

## Required Decisions Frozen Here

| Gate | Decision | Reasoning |
| --- | --- | --- |
| Inspection unit | inspect one selected `L3PassRun` per request | This preserves the PR `#218` one-pass execution boundary and avoids batch/result aggregation semantics |
| Authority source | use durable session, approved plan, execution-selection summary, selected pass-run state, and PR `#218` execution-start metadata | Browser state and request payloads cannot authorize post-execution interpretation |
| Endpoint posture | read-only result/status endpoint, not result review | The repo needs execution proof before product-level review semantics |
| Output boundary | expose raw output metadata summary only when the existing output reference is present and readable | The output file can prove execution without becoming a package or reviewed result |
| Failed pass handling | failed terminal passes may be inspected for status/error metadata only | Retry/recovery/cancellation require later freezes |
| Idempotency | do not require `client_request_id` for the read-only endpoint; if accepted, it must be echoed only and must not create idempotency records | No writes means duplicate reads are naturally safe; idempotency storage would widen the boundary |
| State model | allow only `result_status_inspection` after `execution_pass_completed` or `execution_pass_failed` | This names the status surface without implying result review |
| UI posture | if UI changes, show execution proof/status only | A status panel has lower blast radius than review/package/handoff UI |
| Downstream posture | result review, package, and handoff remain unavailable | Execution proof does not settle result taxonomy, operator approval, or downstream packaging |

## Required Proof

An implementation PR governed by this freeze must prove:

- result/status inspection requires prior PR `#218` execution-start state or terminal selected-pass failure metadata
- stale or mismatched approved-plan preview identity/hash fails closed
- a non-selected, non-terminal, foreign-session, or foreign-plan pass run fails closed
- the result/status endpoint creates no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, result-review, package, handoff, runtime DB, or schema state
- missing output metadata is reported as status-only, not silently treated as reviewed result material
- output metadata parsing is bounded, read-only, and fail-closed on unreadable or malformed metadata
- result review/package/handoff states remain unavailable in response and session summary posture
- source breadth does not expand beyond the approved plan/pass inputs
- all relevant Layer 3 focused tests pass
- headed and headless browser proof is run if rendered `/review/layer3` behavior changes

## Stop Conditions

Stop and return to planning if the implementation requires:

- result approval/rejection semantics
- package construction or package review
- handoff/export behavior
- new result taxonomy beyond status and raw metadata summary
- rerun, cancellation, retry, or recovery workflow
- executing additional pass runs
- modifying output artifacts
- writing runtime snapshot DB state
- changing schema
- changing source breadth
- broad UI/full mockup activation
- treating mockup visuals as permission to activate later result/package/handoff states

## Relationship To Existing Docs

This freeze depends on:

- `36_L3_WB_EXECUTION_READINESS_FREEZE.md`
- `37_L3_WB_STATE_HASH_IDEMPOTENCY_CONTRACT.md`
- `38_L3_WB_EXECUTION_SELECTION_FREEZE.md`
- `39_L3_WB_EXECUTION_SELECTION_API_AND_STATE_CONTRACT.md`
- `40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md`
- `41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md`
- `43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

It does not replace the execution-start packet. It starts from PR `#218` selected-pass execution output metadata and freezes only the next read-only result/status inspection boundary.
