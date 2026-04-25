# Layer 3 Workbench Result Status API And State Contract

Status: governing API/state companion for `42_L3_WB_RESULT_STATUS_FREEZE.md`.

This document defines the route, state, read-boundary, response contract, and proof requirements for the selected-pass result/status implementation. It does not make result review, package review, or handoff live by itself.

Implementation note as of April 25, 2026: branch `codex/l3-result-status` implements the read-only endpoint described here. Until that branch is merged and re-audited on `project6-origin/main`, current-main live truth remains PR `#221` planning-only governance plus PR `#218` bounded analysis-execution-start behavior.

## Authority Order

Selected-pass result/status inspection must use this authority order:

1. durable `L3Session` state
2. durable committed Gate B and Gate C state
3. server-side owner-service plan preview identity/hash stored on the approved plan
4. durable approved `L3AnalysisPlan`
5. durable execution-selection summary from PR `#216`
6. durable selected `L3PassRun` shell state
7. PR `#218` analysis-execution-start state stored on the selected pass/session
8. associated wrapped quantitative `AnalysisRun` id, when present
9. existing selected-pass output metadata reference, when present
10. browser state as display/cache only

Browser state must not approve, revise, select, run, retry, cancel, interpret, review, complete, package, or hand off result/status output.

## Endpoint

The bounded implementation may add one endpoint:

`POST /api/v1/layer3/execution/result/status`

The endpoint may inspect exactly one terminal selected pass-run execution. It must not create result review, package review, handoff, source-expansion, or full mockup state.

Minimum request fields:

| Field | Required | Rule |
| --- | --- | --- |
| `session_id` | yes | Must identify an existing Layer 3 workbench session |
| `analysis_plan_id` | yes | Must identify the current approved plan for the session |
| `pass_run_id` | yes | Must identify an existing selected pass run for the session and approved plan |
| `preview_id` | yes | Must match the approved plan and execution-selection preview identity |
| `preview_hash` | yes | Must match the approved plan and execution-selection preview hash |
| `analysis_run_id` | no | If supplied, must match the selected pass-run summary; required only if a later implementation proves ambiguity without it |
| `operator_view_mode` | no | If supplied, must be `status_only` for this tranche |
| `client_request_id` | no | Optional echo-only trace value; must not create idempotency or audit rows because this endpoint is read-only |

Forbidden request fields include:

- `approve_result`
- `reject_result`
- `result_review`
- `result_decision`
- `edited_findings`
- `package`
- `package_review`
- `handoff`
- `export`
- `rerun`
- `retry`
- `cancel`
- `run_all`
- `batch`
- `local_upload`
- `local_directory`
- `rag_plan`
- `vector_plan`
- `qualitative_plan`
- `hybrid_plan`
- `approved_plan_supersession`
- `schema_migration`
- `runtime_db_write`

Minimum response fields:

| Field | Meaning |
| --- | --- |
| `schema_id` | `layer3.execution_result_status.v1` or later frozen replacement |
| `status` | `available`, `blocked`, `missing_output_metadata`, `failed`, or fail-closed error status |
| `session_id` | session authority |
| `analysis_plan_id` | approved-plan authority |
| `pass_run_id` | selected pass-run authority |
| `preview_identity` | matched preview id/hash metadata |
| `execution_started` | `true` only if PR `#218` execution-start state exists or terminal failed metadata proves attempted execution |
| `analysis_run_id` | wrapped quantitative `AnalysisRun` id for the selected pass, when present |
| `pass_run_status` | terminal status of the selected pass run |
| `output_payload_ref` | raw pass-run output metadata reference if present |
| `output_metadata_summary` | bounded read-only summary of the raw output metadata, if readable |
| `warnings_present` | whether output metadata or pass status indicates warnings |
| `error_present` | whether pass status or summary indicates failure/error metadata |
| `result_status_available` | `true` only for this read-only status surface |
| `result_review_enabled` | always `false` for this tranche |
| `package_review_enabled` | always `false` for this tranche |
| `handoff_enabled` | always `false` for this tranche |
| `downstream_unavailable` | must include `result_review`, `package`, and `handoff`; it may continue to include broader `results` until labels are split by a later implementation |

## State Model Delta

The implementation may add only these state meanings:

| State | Authority source | Allowed next actions | Forbidden downstream actions |
| --- | --- | --- | --- |
| `execution_result_status_available` | terminal selected `L3PassRun` plus PR `#218` execution-start metadata and/or output reference | inspect status again; later result-review freeze may consume this state | result approval/rejection, package, handoff, source expansion, approved-plan supersession |
| `execution_result_status_blocked` | selected pass is missing, non-terminal, stale, mismatched, or lacks required execution-start authority | fix upstream state through a later admitted recovery path | result review, package, handoff, source expansion, approved-plan supersession |
| `execution_result_status_missing_output` | selected pass is terminal but output metadata is absent or unreadable | inspect status/error only; later recovery freeze may address missing output | result review, package, handoff, source expansion, approved-plan supersession |

Existing states keep their current behavior:

- `execution_selected_not_started` is eligible only for PR `#218` execution start, not result/status inspection.
- `execution_pass_running` is not eligible for result/status inspection except as a blocked response.
- `execution_pass_completed` or `execution_pass_failed` may be eligible for read-only result/status inspection after all authority checks pass.
- `plan_approved`, `plan_rejected`, and `plan_revision_requested` are not result/status states.

## Read Boundary

The implementation may read only:

- `L3Session`
- `L3AnalysisPlan`
- selected `L3PassRun`
- the associated `AnalysisRun`, when referenced by selected pass-run summary
- existing selected-pass output metadata file referenced by `output_payload_ref`, if present
- existing JSON summary fields already written by prior admitted slices

The implementation must not write:

- `L3Session`
- `L3AnalysisPlan`
- `L3PassRun`
- `AnalysisRun`
- `AnalysisArtifact`
- result review state
- package review state
- handoff state
- runtime snapshot DB rows
- source-ingestion rows for local upload, local directory, RAG, or vector retrieval
- schema migrations
- approved-plan replacement/supersession data
- new artifact manifests or modified output payload files

If a later implementation believes a durable read receipt or audit row is required, that is a separate write boundary and must be frozen before implementation.

## Selected-Pass Result/Status Contract

The selected pass run must:

- belong to the supplied `session_id`
- reference the supplied approved `analysis_plan_id`
- have originated from execution selection for the current approved preview id/hash
- have PR `#218` execution-start state recorded, unless it is terminal failed with error metadata that proves attempted execution
- have terminal status `completed`, `completed_with_warnings`, or `failed`
- have no status that implies in-progress execution
- have `engine_family` limited to wrapped quantitative analysis for this tranche
- have no source-breadth requirements beyond the approved plan/pass inputs

The endpoint must treat these as blocked:

- missing session
- missing approved plan
- plan mismatch
- stale preview id/hash
- missing execution-selection state
- missing selected pass
- foreign-session pass
- foreign-plan pass
- non-terminal pass status
- unsupported engine family
- missing or mismatched `analysis_run_id` when an id is supplied
- request fields that imply review, package, handoff, rerun, source expansion, schema migration, or runtime DB writes

## Output Metadata Summary

If `output_payload_ref` is present, the implementation may parse only enough metadata to summarize execution proof.

Permitted summary fields include:

- output metadata file exists
- output metadata file path or stable reference
- analysis run id in metadata
- analysis set id
- dataset version id
- selected method name
- artifact count
- warnings-present flag
- error-present flag
- generated/completed timestamp if already present

Forbidden summary behavior includes:

- converting raw output into reviewed findings
- extracting or ranking conclusions as approved results
- building package sections
- writing normalized result rows
- modifying the output metadata file
- reading unrelated artifact trees
- using local upload, local directory, RAG, vector, qualitative, or hybrid sources

Malformed or unreadable output metadata must fail closed into a status-only response and must not be treated as reviewed result material.

## Idempotency And Concurrency

Because this endpoint is read-only, it must not require `client_request_id` and must not write idempotency records.

Rules:

- repeated identical reads return the current server-authoritative status
- optional `client_request_id` may be echoed only
- no duplicate read may create or update execution, result, package, handoff, or audit state
- the implementation should use normal read consistency for the repo's database/session patterns
- if an implementation cannot safely inspect an in-progress pass without locks, it must return `execution_result_status_blocked` for non-terminal statuses rather than widening into execution orchestration

## Failure Behavior

Fail closed with no writes when:

- authority checks fail
- preview identity/hash is stale
- the pass is not terminal
- output metadata is absent but the response would need metadata to satisfy the requested view
- output metadata is malformed or unreadable
- supplied `analysis_run_id` does not match the selected pass
- request payload asks for result review, result decision, package, handoff, rerun, cancellation, source expansion, schema migration, runtime DB write, or UI/full mockup activation

For terminal failed selected passes, the response may report status and error metadata only. It must not expose a retry/recovery action unless a later freeze admits that behavior.

## UI Boundary

If a later implementation changes `/review/layer3`, the UI may only expose:

- a status/proof panel for one selected terminal pass
- terminal pass status
- `AnalysisRun` id if present
- raw output metadata reference if present
- warning/error indicators
- blocked states for stale preview, non-terminal pass, missing output metadata, unsupported source breadth, or authority mismatch

The UI must not show:

- result approval or rejection buttons
- editable findings
- package review controls
- handoff/export controls
- rerun, retry, or cancel controls
- RAG/vector retrieval controls
- local upload/local directory controls
- qualitative/hybrid execution controls
- full mockup stages as live

Any UI change requires headed and headless Chrome proof for the affected `/review/layer3` flow.

## Test Requirements

Implementation tests must cover:

- successful result/status inspection for a completed selected pass
- successful status-only inspection for a failed selected pass, if supported
- no database writes during status inspection
- no new `L3AnalysisPlan` rows
- no new `L3PassRun` rows
- no new `AnalysisRun` rows
- stale approved-plan preview id/hash fails closed
- missing execution selection fails closed
- missing execution-start metadata fails closed unless terminal failure metadata is explicitly admitted
- non-terminal selected pass fails closed
- foreign-session or foreign-plan pass fails closed
- unreadable/malformed output metadata fails closed into status-only behavior
- forbidden result review/package/handoff/rerun/source/schema/runtime fields fail closed
- response keeps result review, package, and handoff disabled
- all relevant Layer 3 focused backend tests pass
- headed and headless browser proof if UI changes

## Deferred Decisions

Still deferred after this contract:

- result taxonomy beyond status and raw output metadata summary
- result review UI
- result approval/rejection/editing
- package review
- handoff/export
- result/package artifact manifests
- rerun, retry, cancellation, or recovery workflows
- source-breadth expansion
- approved-plan cancellation/supersession after execution
- runtime DB/schema widening
- qualitative execution
- hybrid execution
- RAG/vector retrieval

These require later freezes before implementation.
