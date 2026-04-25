# Layer 3 Workbench Execution Selection API And State Contract

Status: planning-only companion for `38_L3_WB_EXECUTION_SELECTION_FREEZE.md`.

This document defines the route, state, write-boundary, idempotency, and proof requirements for the future execution-selection/pass-run shell implementation. It does not make execution live.

## Authority Order

Execution selection must use this authority order:

1. durable `L3Session` state
2. durable committed Gate B and Gate C state
3. server-side owner-service plan preview identity/hash
4. durable approved `L3AnalysisPlan`
5. future durable `L3PassRun` shell state
6. browser state as display/cache only

Browser state must not approve, revise, select, run, retry, or cancel execution.

## Candidate Endpoint

The future implementation may add one endpoint:

`POST /api/v1/layer3/execution/select`

The endpoint may return an execution-selection response only. It must not start analysis.

Minimum request fields:

| Field | Required | Rule |
| --- | --- | --- |
| `session_id` | yes | Must identify an existing Layer 3 workbench session |
| `analysis_plan_id` | yes | Must identify the current approved plan for the session |
| `preview_id` | yes | Must match the approved plan preview identity |
| `preview_hash` | yes | Must match the approved plan preview hash |
| `client_request_id` | yes | Required for duplicate/retry safety |
| `operator_reason` | no | Optional audit text only; not semantic execution input |

Minimum response fields:

| Field | Meaning |
| --- | --- |
| `schema_id` | `layer3.execution_selection.v1` or later frozen replacement |
| `status` | `selected_not_started`, `already_selected`, or fail-closed error status |
| `session_id` | session authority |
| `analysis_plan_id` | approved-plan authority |
| `preview_identity` | matched preview id/hash metadata |
| `pass_run_ids` | shell pass-run ids created or already selected |
| `execution_started` | always `false` for this tranche |
| `analysis_run_ids` | always empty for this tranche |
| `downstream_unavailable` | must still include `results`, `package`, and `handoff` |

## State Model Delta

The future implementation may add one state:

| State | Authority source | Allowed next actions | Forbidden downstream actions |
| --- | --- | --- | --- |
| `execution_selected_not_started` | server-created `L3PassRun` shell rows tied to an approved `L3AnalysisPlan` | later execution start only after a separate freeze | analysis execution, results, package, handoff, source expansion, approved-plan supersession |

Existing states keep their current behavior:

- `plan_approved` is eligible for execution selection only after preview identity/hash validation.
- `plan_rejected` is not eligible.
- `plan_revision_requested` is not eligible.
- `execution_readiness_blocked` remains non-executing until all required selection gates are satisfied.

## Write Boundary

The future implementation may write only:

- `L3PassRun` shell rows for already approved plan sets
- session summary metadata that records execution selection as selected/not-started
- idempotency/audit metadata if an existing table/JSON field can hold it without migration

The future implementation must not write:

- `AnalysisRun`
- result artifacts
- package artifacts
- handoff artifacts
- artifact manifests
- runtime snapshot DB rows
- schema migrations unless separately frozen
- approved-plan replacement/supersession data

## L3PassRun Shell Contract

Each created `L3PassRun` shell must:

- reference the current `session_id`
- reference the approved `analysis_plan_id`
- reference an analysis set already present in the approved plan
- set status to a not-started/selected state
- record the approved preview id/hash in JSON metadata if no dedicated columns exist
- record `execution_started: false`
- record no `AnalysisRun` id
- preserve the approved plan's source/material boundary

The existing `materialize_pass_entry(...)` function is not automatically admitted. If reused, a later implementation must first split or wrap it so execution selection can create pass-run shells without creating `AnalysisRun` or running analysis.

## Idempotency

The future endpoint must require `client_request_id`.

Rules:

- same `client_request_id`, same approved plan, same preview identity/hash: return existing selection state
- same `client_request_id`, different approved plan or preview identity/hash: fail closed with an idempotency conflict
- missing `client_request_id`: fail closed
- duplicate request after selection already exists without a matching request id: fail closed or return a deterministic conflict; do not create more pass-run shells

## Concurrency

The future implementation must:

- lock the `L3Session` row or equivalent session authority
- verify approved-plan state inside the same transaction
- verify no conflicting revision/rejection state exists inside the same transaction
- verify no existing execution selection exists unless resolving an idempotent retry
- commit pass-run shell rows atomically

UI in-flight locking is allowed only as a user-experience guard.

## Failure Behavior

Fail closed with no durable write when:

- the session does not exist
- no approved plan exists
- more than one current approved plan exists
- the approved plan does not match the supplied preview identity/hash
- the session is rejected or revision-requested
- execution selection already exists with conflicting request data
- the selected plan has no admissible analysis sets
- source breadth or output taxonomy would need to expand to satisfy the request

## UI Boundary

If the future implementation changes `/review/layer3`, the UI may only expose:

- an execution-selection affordance after approved-plan state is visible
- selected/not-started status after server confirmation
- fail-closed error states for stale preview, revision requested, rejected plan, duplicate request, or unsupported source breadth

The UI must not show analysis running, results, package review, handoff, RAG/vector retrieval, local upload, or full mockup stages as live.

## Test Requirements

Future implementation tests must cover:

- successful selection from one approved plan without `AnalysisRun`
- duplicate `client_request_id` returns existing selection
- conflicting duplicate request fails closed
- stale preview id/hash fails closed
- rejected state fails closed
- revision-requested state fails closed
- existing selection prevents duplicate pass-run shell creation
- no result/package/handoff artifacts are written
- headed and headless browser proof if UI changes

## Deferred Decisions

Still deferred after this contract:

- actual analysis execution start
- analysis worker ownership and leases
- result taxonomy and result review UI
- package review
- handoff/export
- source-breadth expansion
- approved-plan cancellation/supersession after selection
- runtime DB/schema widening

These require later freezes before implementation.
