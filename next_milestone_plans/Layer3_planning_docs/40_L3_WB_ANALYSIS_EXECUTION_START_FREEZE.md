# Layer 3 Workbench Analysis Execution Start Freeze

Status: planning-only freeze for the next Layer 3 workbench analysis-execution tranche after execution selection.

This document freezes the narrowest eligible execution boundary after PR `#216`: starting and completing one already selected `L3PassRun` shell through the existing wrapped quantitative analysis family, while keeping result review, package review, handoff, source expansion, approved-plan supersession, runtime DB/schema widening, UI/full mockup activation, qualitative execution, hybrid execution, and RAG/vector retrieval out of scope.

## Current Live Boundary

Current `main` already ships:

- first-slice shell/API from PR `#184`, with closeout/correction passes through PR `#190`
- read-only plan preview from PR `#194`, with proof/board metadata closeouts from PRs `#195` and `#196`
- approval-only `L3AnalysisPlan` persistence from PR `#199`
- pre-approval plan rejection/revision-control from PR `#205`, hardened by PR `#207`
- execution-readiness proof/state packet from PR `#212`
- read-only readiness proof from PR `#213`
- execution-selection freeze packet from PR `#215`
- selected/not-started `L3PassRun` shell creation from PR `#216`

Current `main` does not ship analysis execution from selected workbench pass-run shells, result review, package review, handoff, approved-plan correction or supersession, source-breadth expansion, runtime DB/schema widening, qualitative/hybrid/RAG/vector execution, local upload/directory ingestion, or full mockup activation.

## Problem Statement

PR `#216` deliberately stops at selected/not-started `L3PassRun` shells. The next risk is crossing from durable selection into actual analysis execution without a frozen start boundary.

The repo already has an execution-bearing helper, `backend/app/services/layer3_pass_entry.py::materialize_pass_entry(...)`, but that helper is too broad for the workbench path as-is. It creates or updates plan state, creates pass runs, marks the session as active execution, calls `run_analysis(...)`, writes output manifests, updates pass-run completion state, and closes the session. A workbench implementation must not call that helper wholesale against an already approved plan and already selected shell state.

## Slice Decision

The next adequate Layer 3 workbench tranche is:

> Freeze analysis execution start as a selected-pass-run execution boundary: one existing selected/not-started `L3PassRun` may be transitioned through wrapped quantitative analysis under server authority, without opening result review, package review, handoff, source expansion, or full mockup UI behavior.

This is smaller and safer than broad execution because it reuses the already selected pass-run shell as the durable authority, executes at most one selected pass per request, and leaves all downstream interpretation/review/package/handoff states for later freezes.

## Admitted Future Implementation Scope

A later implementation PR governed by this freeze may add only:

- one server-authoritative analysis-execution-start endpoint under the existing Layer 3 API family
- validation that the session already has exactly one current approved `L3AnalysisPlan`
- validation that execution selection already exists for that approved plan and preview id/hash
- validation that the requested `pass_run_id` identifies an existing `L3PassRun` shell with status `selected_not_started`
- serialized state transition authority around the session, approved plan, and selected pass run
- deterministic `client_request_id` idempotency for retries
- a narrow owner-service helper that executes one selected pass run without creating a new `L3AnalysisPlan` or a new `L3PassRun`
- wrapped quantitative `AnalysisRun` creation for the selected pass only
- pass-run status transitions for that selected pass only: `selected_not_started` -> `running` -> `completed`, `completed_with_warnings`, or `failed`
- one pass-run output payload reference for raw execution output metadata if the existing artifact storage path is reused
- focused backend tests proving success, duplicate handling, stale selection blocking, pass-run mismatch blocking, no duplicate `L3PassRun`, and downstream no-go preservation
- headed and headless browser proof only if rendered UI behavior changes

## Explicit Non-Goals

This freeze does not admit:

- calling `materialize_pass_entry(...)` as-is from the workbench path
- creating a new `L3AnalysisPlan`
- creating additional `L3PassRun` rows
- executing more than one selected pass run per request
- executing an unselected pass run
- executing a selected pass run whose approved plan or preview id/hash no longer matches session execution-selection state
- result review UI or result-approval semantics
- package review UI or package artifacts
- handoff UI, handoff artifacts, export behavior, or APS downstream activation
- approved-plan cancellation, replacement, reopening, or supersession
- execution against `plan_rejected` or `plan_revision_requested`
- local upload ingestion
- local directory ingestion
- RAG/vector retrieval
- qualitative or hybrid execution
- runtime snapshot DB writes
- schema migrations unless a later implementation proof shows the existing `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, and JSON metadata fields cannot hold the bounded state
- background worker queues, leases, cancellation, or retry orchestration beyond synchronous/idempotent selected-pass execution
- full mockup activation

## Required Decisions Frozen Here

| Gate | Decision | Reasoning |
| --- | --- | --- |
| Execution unit | execute one selected `L3PassRun` per request | This limits blast radius and avoids inventing orchestration semantics for multiple pass runs |
| Authority source | use durable session, approved plan, execution-selection summary, and selected pass-run shell state | Browser state and request payloads cannot authorize execution |
| Helper posture | split or wrap `materialize_pass_entry(...)`; do not call it as-is | The existing helper creates plans/pass runs and closes the session, which conflicts with the workbench-selected shell contract |
| Analysis engine | admit only wrapped quantitative analysis already represented by the approved planned pass | Qualitative, hybrid, RAG/vector, and source-expansion paths remain deferred |
| Output boundary | raw execution output metadata may be written for the selected pass; result review/package/handoff remain unavailable | Actual analysis needs output refs, but downstream product states require separate freezes |
| Idempotency | require `client_request_id`; same id and same selected pass return existing execution state, conflicting duplicate ids fail closed | This prevents duplicate analysis runs and ambiguous retries |
| Concurrency | serialize session, approved plan, and selected pass-run transition server-side | UI in-flight locks are not authoritative |
| Session status | do not close or package the session as part of this slice unless the API/state contract explicitly proves that all selected pass runs are terminal | Single-pass execution must not accidentally finish the entire workbench workflow |
| Failure behavior | a failed selected pass may move only that pass to failed with error metadata | Result recovery, rerun, cancellation, and package behavior need later freezes |

## Required Future Proof

A later implementation PR governed by this freeze must prove:

- execution start requires prior PR `#216` execution selection
- stale or mismatched approved-plan preview identity/hash fails closed before `AnalysisRun` creation
- an unselected, already running, completed, failed, or foreign-session pass run cannot be executed
- duplicate `client_request_id` behavior is deterministic and does not create duplicate `AnalysisRun`
- exactly one selected pass run is executed per request
- no new `L3AnalysisPlan` is created
- no new `L3PassRun` row is created by analysis execution start
- `AnalysisRun` creation is tied to the selected pass-run summary and output metadata
- result/package/handoff artifacts and UI states remain unavailable
- source breadth does not expand beyond the approved plan/pass inputs
- all relevant Layer 3 focused tests pass
- headed and headless browser proof is run if rendered UI behavior changes

## Stop Conditions

Stop and return to planning if the implementation requires:

- running all selected pass runs as a batch
- adding background workers, queues, cancellation, or lease recovery
- changing schema without a separate schema proof
- reopening or superseding approved plans
- changing the workbench UI beyond selected/running/completed status display
- introducing result taxonomy, package review, handoff, local upload, local directory, RAG/vector, qualitative, or hybrid execution
- treating mockup visuals as permission to activate later UI states

## Relationship To Existing Docs

This freeze depends on:

- `36_L3_WB_EXECUTION_READINESS_FREEZE.md`
- `37_L3_WB_STATE_HASH_IDEMPOTENCY_CONTRACT.md`
- `38_L3_WB_EXECUTION_SELECTION_FREEZE.md`
- `39_L3_WB_EXECUTION_SELECTION_API_AND_STATE_CONTRACT.md`
- `41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

It does not replace the execution-selection packet. It starts from PR `#216` selected/not-started pass-run shells and freezes only the next analysis-execution-start boundary.
