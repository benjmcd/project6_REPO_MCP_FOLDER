# Layer 3 Workbench Package Review Submit API And State Contract

Status: planning-only API/state companion for `52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md`.

This document defines the endpoint, request, response, state, idempotency, and proof contract for a future bounded package-review submit/decision step after PR `#238` package construction. It does not make package-review submission live by itself and does not admit handoff/export, package reconstruction, package payload mutation, source expansion, schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Authority Order

Package-review submit/decision must use this authority order:

1. durable `L3Session` state returned by the Layer 3 API
2. approved `L3AnalysisPlan` identity and approved preview id/hash from server state
3. execution-selection summary from server state
4. selected `L3PassRun` identity, terminal status, and selected-pass output metadata from server state
5. result/status authority for the selected terminal pass
6. approved selected-pass result-review state from server state
7. read-only package-review preview basis from PR `#235`
8. package-construction commit state from PR `#238`
9. stored `L3ReconciliationRecord` and `L3OutputPackage` rows
10. request payload as decision intent only
11. browser state as display/cache only

Browser state must not approve, revise, select, run, retry, cancel, package, export, hand off, recover, rewrite, or regenerate output.

## Endpoint

A future implementation may add at most one write endpoint:

`POST /api/v1/layer3/package/review/submit`

The endpoint records one operator package-review decision for one already constructed package set. It must not create packages, rewrite packages, approve handoff/export, or trigger downstream APS behavior.

## Request Contract

Minimum request fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `session_id` | yes | Existing Layer 3 workbench session |
| `analysis_plan_id` | yes | Current approved plan for the session |
| `pass_run_id` | yes | Existing selected terminal pass run for the session and approved plan |
| `preview_id` | yes | Must match approved plan, selected pass, and package construction basis |
| `preview_hash` | yes | Must match approved plan, selected pass, and package construction basis |
| `result_review_record_ref` | yes | Must match the recorded approved selected-pass result-review record |
| `package_review_preview_hash` | yes | Must match the read-only package-review preview basis |
| `reconciliation_record_id` | yes | Must match the constructed package set |
| `output_package_ids` | yes | Must identify exactly the three constructed package rows |
| `payload_hashes` | yes | Must match stored package payload hashes |
| `operator_decision` | yes | One of `approved`, `changes_requested`, `rejected`, or `blocked` |
| `client_request_id` | yes | Required idempotency key for the write |

Conditional request fields:

| Field | Constraint |
| --- | --- |
| `decision_notes` | Required for `changes_requested`, `rejected`, or `blocked`; optional but recommended for `approved` |
| `analysis_run_id` | If supplied, must match selected pass state |
| `expected_package_kinds` | If supplied, must equal `canonical_internal`, `user_facing`, and `review_facing` as a set |

Forbidden request fields include:

- `handoff`
- `export`
- `aps_handoff`
- `create_package`
- `rebuild_package`
- `package_payload`
- `package_variant_content`
- `rewrite_output`
- `edited_findings`
- `result_review_amendment`
- `rerun`
- `retry`
- `recover`
- `cancel`
- `selected_pass_ids`
- `pass_run_ids`
- `new_analysis_plan`
- `plan_revision`
- `source_expansion`
- `local_upload`
- `local_directory`
- `schema_migration`
- `runtime_db_write`
- `artifact_manifest`
- `analysis_artifact`

## Response Contract

Minimum success response fields:

| Field | Meaning |
| --- | --- |
| `schema_id` | `layer3.package_review_submit.v1` or later frozen replacement |
| `status` | `submitted` or deterministic idempotent replay status |
| `session_id` | session authority |
| `analysis_plan_id` | approved-plan authority |
| `pass_run_id` | selected pass-run authority |
| `preview_identity` | matched preview id/hash metadata |
| `result_review_record_ref` | matched approved result-review record |
| `package_review_preview_hash` | matched package-preview identity |
| `reconciliation_record_id` | reviewed package-set anchor |
| `output_package_ids` | exactly three reviewed package ids |
| `package_kinds` | exactly `canonical_internal`, `user_facing`, and `review_facing` |
| `payload_hashes` | stored package payload hashes proved unchanged |
| `operator_decision` | submitted package-review decision |
| `package_review_state` | `package_review_approved`, `package_review_changes_requested`, `package_review_rejected`, or `package_review_blocked` |
| `handoff_enabled` | always `false` in this tranche |
| `export_enabled` | always `false` in this tranche |
| `downstream_unavailable` | must include `handoff` and `export` |
| `next_state` | the package-review state produced by the submitted decision |

The response must not include handoff/export ids, generated downstream artifacts, editable package payload bodies, or rewritten package content.

## State Model Delta

The implementation may add only these state meanings:

| State | Authority source | Allowed next actions | Forbidden downstream actions |
| --- | --- | --- | --- |
| `package_review_submit_unavailable` | missing constructed package state or upstream authority | inspect upstream state | package-review submit, handoff/export |
| `package_review_submit_blocked` | stale authority, partial package set, hash mismatch, forbidden payload, or existing conflicting decision | inspect block reasons | package-review submit, handoff/export |
| `package_review_submit_ready` | server-validated constructed package set and no existing conflicting review decision | submit one package-review decision | handoff/export |
| `package_review_approved` | operator approved the constructed package set | inspect approved decision; await separate handoff/export freeze | handoff/export until separately frozen |
| `package_review_changes_requested` | operator requested changes to the constructed package set | inspect decision; await separate rebuild/amendment freeze | handoff/export, package rewrite |
| `package_review_rejected` | operator rejected the constructed package set | inspect decision | handoff/export, package rewrite |
| `package_review_blocked` | operator blocked decision because evidence is insufficient | inspect decision and upstream evidence | handoff/export, package rewrite |

These states authorize package-review disposition only. They do not authorize handoff/export, package reconstruction, package payload mutation, result-review amendment, rerun/recovery, source expansion, schema/runtime widening, or full mockup activation.

## Write Contract

The endpoint may create or update only:

- one package-review decision object in `L3ReconciliationRecord.summary_json`
- optional `L3Session.summary_json` package-review decision pointer/index fields

The endpoint must not create or update:

- `L3AnalysisPlan`
- `L3PassRun`
- `AnalysisRun`
- `AnalysisArtifact`
- additional `L3ReconciliationRecord` rows
- additional `L3OutputPackage` rows
- package payload files
- `L3OutputPackage.payload_ref`
- `L3OutputPackage.payload_hash`
- handoff/export rows or artifacts
- runtime snapshot DB rows
- source-ingestion rows
- schema/migration files

If implementation requires schema widening or package row status mutation, the endpoint must not be implemented under this contract.

## Idempotency And Concurrency

`client_request_id` is required.

Rules:

- the server must serialize package-review submit for the session
- first valid request may record the decision state
- exact retry with the same `client_request_id`, same authority basis, same package ids/hashes, and same operator decision may return the existing decision summary
- a retry with the same `client_request_id` but different authority fields or decision fields must fail closed
- a second request with a different `client_request_id` after a decision exists must fail closed unless the stored decision proves the same authority basis and the same decision
- duplicate or conflicting package-review decisions are not admitted

## Failure Behavior

The endpoint must fail closed when:

- approved plan or preview identity is missing or stale
- selected pass is missing, foreign, non-selected, or non-terminal
- result/status authority is unavailable
- result review is missing, not approved, blocked, rejected, or changes requested
- `result_review_record_ref` mismatches stored review state
- package-review preview hash or identity mismatches current preview basis
- package construction is missing, partial, or not tied to the expected authority basis
- reconciliation record id mismatches the session
- package ids do not identify exactly three stored rows for the session
- package kinds are not exactly `canonical_internal`, `user_facing`, and `review_facing`
- payload refs or hashes are missing or mismatched
- an existing package-review decision conflicts with the request
- decision notes are missing for `changes_requested`, `rejected`, or `blocked`
- request payload asks for package reconstruction, handoff/export, rerun, recovery, source expansion, schema migration, runtime DB write, output rewrite, or full mockup activation

For server errors, the UI must preserve existing upstream and package state and display the block reason. It must not replace missing authority with browser-local guesses.

## UI Boundary

If a later implementation changes `/review/layer3`, the UI may only expose:

- constructed package evidence returned by the server
- package-review submit readiness
- one decision form with the four admitted decisions
- required notes for non-approval decisions
- read-only post-decision state
- disabled handoff/export indicators

The UI must not expose:

- handoff/export controls
- package payload editors
- package rebuild controls
- editable package variant tabs
- rerun/retry/recovery/cancel controls
- source-expansion pickers
- local upload or directory selectors
- raw output editing or rewrite controls
- qualitative/hybrid/RAG/vector controls

## Tests Required Before Merge

Implementation tests must cover:

- no package-review submit before package construction exists
- partial package construction fails closed
- stale preview id/hash fails closed
- stale or mismatched `result_review_record_ref` fails closed
- stale or mismatched `package_review_preview_hash` fails closed
- stale or mismatched reconciliation id, package ids, package kinds, payload refs, or payload hashes fail closed
- non-approved result-review states fail closed
- missing notes for `changes_requested`, `rejected`, and `blocked` fail closed
- forbidden handoff/export/package-rewrite/rerun/source/schema/runtime/output-rewrite fields fail closed
- successful submit records exactly one decision object
- identical idempotent retry does not duplicate or alter decision state
- conflicting duplicate request fails closed
- payload refs and hashes remain unchanged
- no package payload file is created, deleted, or rewritten
- no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, handoff/export artifact, runtime DB row, schema migration, source-ingestion row, additional reconciliation row, or additional package row is created
- existing package construction tests still pass
- existing result/status, result-review, package-review preview, and package-construction flows still pass
- both headed and headless Chrome browser proof pass if rendered UI behavior changes

## Still Deferred

Still deferred after this contract:

- handoff/export trigger policy
- APS handoff behavior
- package rebuild or amendment after `changes_requested`
- package payload editing
- result-review amendment or supersession
- approved-plan correction or supersession
- source-breadth expansion
- local upload or local-directory ingestion
- qualitative/hybrid/RAG/vector execution
- broad UI/full mockup activation
