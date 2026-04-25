# Layer 3 Workbench Analysis Execution Start API And State Contract

Status: planning-only companion for `40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md`.

This document defines the route, state, write-boundary, idempotency, and proof requirements for a future selected-pass-run analysis-execution-start implementation. It does not make analysis execution live by itself.

## Authority Order

Analysis execution start must use this authority order:

1. durable `L3Session` state
2. durable committed Gate B and Gate C state
3. server-side owner-service plan preview identity/hash stored on the approved plan
4. durable approved `L3AnalysisPlan`
5. durable execution-selection summary from PR `#216`
6. durable selected/not-started `L3PassRun` shell state
7. existing wrapped quantitative analysis engine behavior
8. browser state as display/cache only

Browser state must not approve, revise, select, run, retry, cancel, complete, or package execution.

## Candidate Endpoint

The future implementation may add one endpoint:

`POST /api/v1/layer3/execution/start`

The endpoint may start and complete exactly one selected pass-run execution. It must not create result review, package review, handoff, source-expansion, or full mockup state.

Minimum request fields:

| Field | Required | Rule |
| --- | --- | --- |
| `session_id` | yes | Must identify an existing Layer 3 workbench session |
| `analysis_plan_id` | yes | Must identify the current approved plan for the session |
| `pass_run_id` | yes | Must identify an existing selected/not-started pass-run shell for the session and approved plan |
| `preview_id` | yes | Must match the approved plan and execution-selection preview identity |
| `preview_hash` | yes | Must match the approved plan and execution-selection preview hash |
| `client_request_id` | yes | Required for duplicate/retry safety |
| `execution_mode` | no | If present, must be `synchronous_single_pass` for this tranche |
| `operator_reason` | no | Optional audit text only; not semantic execution input |

Forbidden request fields include:

- `run_all`
- `batch`
- `package`
- `package_review`
- `handoff`
- `result_review`
- `local_upload`
- `local_directory`
- `rag_plan`
- `vector_plan`
- `qualitative_plan`
- `hybrid_plan`
- `approved_plan_supersession`
- `schema_migration`

Minimum response fields:

| Field | Meaning |
| --- | --- |
| `schema_id` | `layer3.analysis_execution_start.v1` or later frozen replacement |
| `status` | `completed`, `completed_with_warnings`, `failed`, `already_completed`, or fail-closed error status |
| `session_id` | session authority |
| `analysis_plan_id` | approved-plan authority |
| `pass_run_id` | selected pass-run authority |
| `preview_identity` | matched preview id/hash metadata |
| `execution_started` | `true` only after the selected pass-run transition has been admitted |
| `analysis_run_id` | wrapped quantitative `AnalysisRun` id for the selected pass, when execution reaches the engine |
| `pass_run_status` | terminal or current status of the selected pass run |
| `output_payload_ref` | raw pass-run output metadata reference if execution produced output metadata |
| `downstream_unavailable` | must still include `results`, `package`, and `handoff` |

## State Model Delta

The future implementation may add these execution-state meanings:

| State | Authority source | Allowed next actions | Forbidden downstream actions |
| --- | --- | --- | --- |
| `execution_pass_running` | server-locked `L3PassRun` status transition for one selected pass | complete/fail the same pass within the admitted execution path | result review, package, handoff, source expansion, approved-plan supersession |
| `execution_pass_completed` | selected pass run has a wrapped quantitative `AnalysisRun` and terminal output metadata | later result review only after a separate freeze | package, handoff, source expansion, approved-plan supersession |
| `execution_pass_failed` | selected pass run failed with error metadata | later retry/recovery only after a separate freeze | result review, package, handoff, source expansion, approved-plan supersession |

Existing states keep their current behavior:

- `execution_selected_not_started` is eligible for one selected-pass execution start only after preview identity/hash validation.
- `plan_approved` is not directly executable without execution selection.
- `plan_rejected` is not executable.
- `plan_revision_requested` is not executable.

## Write Boundary

The future implementation may write only:

- status/timestamp/summary updates for the selected `L3PassRun`
- one wrapped quantitative `AnalysisRun` and its normal `AnalysisArtifact` rows if the existing analysis engine creates them
- one raw selected-pass output metadata reference, such as the existing `settings.artifact_storage_dir/layer3/l3_pass_run_<pass_run_id>.json` shape, if a split helper reuses that output contract
- session summary metadata that records selected-pass execution progress without enabling results/package/handoff
- idempotency/audit metadata if existing JSON fields can hold it without migration

The future implementation must not write:

- new `L3AnalysisPlan` rows
- new `L3PassRun` rows
- result review state
- package review state
- handoff state
- runtime snapshot DB rows
- source-ingestion rows for local upload, local directory, RAG, or vector retrieval
- schema migrations unless separately frozen
- approved-plan replacement/supersession data

## Selected-Pass Execution Contract

The selected pass run must:

- belong to the supplied `session_id`
- reference the supplied approved `analysis_plan_id`
- have status `selected_not_started` before the first admitted execution start
- match execution-selection preview id/hash metadata in its summary or session selection state
- have `engine_family` limited to wrapped quantitative analysis for this tranche
- have no existing `analysis_run_id` before first execution
- have `output_payload_ref` unset before first execution
- transition through server authority only

The future implementation must not call `materialize_pass_entry(...)` as-is. If code is reused from `layer3_pass_entry.py`, it must be split or wrapped so it:

- does not create a new plan
- does not create new pass-run shells
- does not classify or reselect sets
- does not execute more than the requested pass run
- does not close/package the whole session as part of one selected-pass execution

## Idempotency

The future endpoint must require `client_request_id`.

Rules:

- same `client_request_id`, same session, same approved plan, same pass run, same preview identity/hash: return existing execution state
- same `client_request_id`, different pass run, approved plan, or preview identity/hash: fail closed with an idempotency conflict
- missing `client_request_id`: fail closed
- duplicate request after a selected pass already has an `analysis_run_id` from a different request: fail closed or return deterministic already-started conflict; do not create another `AnalysisRun`

## Concurrency

The future implementation must:

- lock the `L3Session` row or equivalent session authority
- lock the approved `L3AnalysisPlan` row or equivalent approved-plan authority
- lock the selected `L3PassRun` row before status transition
- verify execution-selection summary inside the same transaction
- verify no conflicting revision/rejection state exists inside the same transaction
- verify no selected pass is already running for the same session unless the implementation proves same-pass idempotent retry
- commit selected-pass status and output metadata atomically around the admitted execution behavior

UI in-flight locking is allowed only as a user-experience guard.

## Failure Behavior

Fail closed with no new `AnalysisRun` when:

- the session does not exist
- the approved plan does not exist or is not the current approved plan
- execution selection does not exist
- the supplied preview id/hash does not match the approved plan and execution-selection state
- the pass run does not exist
- the pass run belongs to another session or plan
- the pass run is not `selected_not_started`
- the pass run already has an `analysis_run_id` from a conflicting request
- the pass run requires qualitative, hybrid, RAG/vector, local upload, or local directory behavior
- the request asks for batch execution, result review, package review, handoff, approved-plan supersession, or schema widening

If wrapped quantitative analysis raises after the pass has been admitted, the selected pass may be marked `failed` with error metadata. That failure state must not create result/package/handoff state.

## UI Boundary

If the future implementation changes `/review/layer3`, the UI may only expose:

- a start-execution affordance for selected/not-started pass runs after server-confirmed execution selection
- selected/running/completed/completed-with-warnings/failed status for the selected pass
- `AnalysisRun` id and raw output metadata only as execution proof, not as result review/package/handoff
- fail-closed error states for stale preview, unselected pass, already-started pass, unsupported source breadth, or duplicate request

The UI must not show result review, package review, handoff, RAG/vector retrieval, local upload, local directory, qualitative/hybrid execution, or full mockup stages as live.

## Test Requirements

Future implementation tests must cover:

- successful execution start from one selected/not-started pass shell
- no new `L3AnalysisPlan` rows
- no new `L3PassRun` rows
- exactly one `AnalysisRun` for the selected pass
- duplicate `client_request_id` returns existing execution state without another `AnalysisRun`
- conflicting duplicate request fails closed
- stale approved-plan preview id/hash fails closed before `AnalysisRun`
- missing execution selection fails closed
- unselected pass run fails closed
- already running/completed/failed pass run fails closed or returns deterministic same-request state without rerun
- unsupported qualitative/hybrid/RAG/vector/local-source request fields fail closed
- result/package/handoff state remains unavailable
- all relevant Layer 3 focused tests pass
- headed and headless browser proof if UI changes

## Deferred Decisions

Still deferred after this contract:

- executing all selected pass runs as a batch
- background workers, leases, cancellation, retry queues, and recovery workflows
- result taxonomy and result review UI
- package review
- handoff/export
- source-breadth expansion
- approved-plan cancellation/supersession after selection or execution
- runtime DB/schema widening
- qualitative execution
- hybrid execution
- RAG/vector retrieval

These require later freezes before implementation.
