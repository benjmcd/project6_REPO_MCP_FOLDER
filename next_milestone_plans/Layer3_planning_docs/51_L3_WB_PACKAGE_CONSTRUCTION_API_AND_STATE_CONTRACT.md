# Layer 3 Workbench Package Construction API And State Contract

Status: planning-only API/state companion for `50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`.

This document defines the endpoint, request, response, state, idempotency, and proof contract for a future bounded workbench package-construction commit after PR `#235` read-only package-review preview. It does not make package construction live by itself and does not admit package-review submission, handoff/export, rerun/recovery, source expansion, schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Authority Order

Package construction must use this authority order:

1. durable `L3Session` state returned by the Layer 3 API
2. approved `L3AnalysisPlan` identity and approved preview id/hash from server state
3. execution-selection summary from server state
4. selected `L3PassRun` identity, terminal status, and selected-pass output metadata from server state
5. result/status authority for the selected terminal pass
6. approved selected-pass result-review state from server state
7. read-only package-review preview basis from PR `#235`
8. package owner-service module contracts in `layer3_package_entry.py`
9. request payload as commit intent only
10. browser state as display/cache only

Browser state must not approve, revise, select, run, retry, cancel, package, export, hand off, recover, or rewrite output.

## Endpoint

A future implementation may add at most one write endpoint:

`POST /api/v1/layer3/package/review/commit`

The endpoint commits package construction for one current approved selected-pass result review. The endpoint name is intentionally downstream of the existing package-review preview route, but the write itself is package construction only. It must not persist package-review submit/decision state or trigger handoff/export.

## Request Contract

Minimum request fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `session_id` | yes | Existing Layer 3 workbench session |
| `analysis_plan_id` | yes | Current approved plan for the session |
| `pass_run_id` | yes | Existing selected terminal pass run for the session and approved plan |
| `preview_id` | yes | Must match approved plan, selected-pass, and package-preview basis |
| `preview_hash` | yes | Must match approved plan, selected-pass, and package-preview basis |
| `result_review_record_ref` | yes | Must match the recorded approved selected-pass result-review record |
| `package_review_preview_hash` | yes | Stable hash or identity returned by the read-only package-review preview response |
| `client_request_id` | yes | Required idempotency key for the write |

Optional request fields:

| Field | Constraint |
| --- | --- |
| `analysis_run_id` | If supplied, must match selected pass state |
| `expected_package_kinds` | If supplied, must equal `canonical_internal`, `user_facing`, and `review_facing` as a set |

Forbidden request fields include:

- `package_review_decision`
- `submit_package_review`
- `approve_package`
- `reject_package`
- `handoff`
- `export`
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
- `aps_handoff`
- `edited_findings`
- `rewrite_output`
- `package_payload`
- `package_variant_content`

## Response Contract

Minimum success response fields:

| Field | Meaning |
| --- | --- |
| `schema_id` | `layer3.package_construction_commit.v1` or later frozen replacement |
| `status` | `committed` or deterministic idempotent replay status |
| `session_id` | session authority |
| `analysis_plan_id` | approved-plan authority |
| `pass_run_id` | selected pass-run authority |
| `preview_identity` | matched preview id/hash metadata |
| `result_review_record_ref` | matched approved result-review record |
| `package_review_preview_hash` | matched read-only package-review preview identity |
| `reconciliation_record_id` | id of the single created or replayed reconciliation record |
| `output_packages` | exactly three package summaries |
| `package_kinds` | exactly `canonical_internal`, `user_facing`, and `review_facing` |
| `payload_refs` | package payload references created by the owner-service helper |
| `payload_hashes` | hashes for created package payloads |
| `package_review_submit_enabled` | always `false` in this tranche |
| `handoff_enabled` | always `false` in this tranche |
| `downstream_unavailable` | must include `package_review_submit`, `handoff`, and `export` |
| `next_state` | `package_constructed` |

Each `output_packages` entry must include:

- `output_package_id`
- `package_kind`
- `status`
- `payload_ref`
- `payload_hash`
- bounded `summary_json`

The response must not include package-review decision state, handoff/export ids, generated downstream artifacts, or editable package payload bodies.

## State Model Delta

The implementation may add only these state meanings:

| State | Authority source | Allowed next actions | Forbidden downstream actions |
| --- | --- | --- | --- |
| `package_commit_unavailable` | missing session, plan, selected pass, result/status, approved result review, or preview basis | inspect upstream state | package construction, package-review submit, handoff |
| `package_commit_blocked` | server fail-closed check, stale authority, missing output, unresolved trace, existing package rows, forbidden payload, or owner-service incompatibility | inspect block reasons | package-review submit, handoff, rerun |
| `package_commit_ready` | server-validated package-preview basis and no existing package rows | submit one commit request | package-review submit, handoff/export |
| `package_constructing` | server owns an in-flight write transaction | wait or retry with same `client_request_id` | duplicate conflicting commit, package-review submit, handoff |
| `package_constructed` | one reconciliation row, three package rows, and three payload files exist for the session | inspect created package summary | package-review submit, handoff/export until separately frozen |

These states authorize package construction only. They do not authorize package-review submission, handoff/export, result amendment, rerun/recovery, source expansion, schema/runtime widening, or full mockup activation.

## Write Contract

The endpoint may create or update only:

- one `L3ReconciliationRecord`
- three `L3OutputPackage` rows
- three package payload files
- optional `L3Session.summary_json` package-commit summary fields that point to the created rows

The endpoint must not create or update:

- `L3AnalysisPlan`
- `L3PassRun`
- `AnalysisRun`
- `AnalysisArtifact`
- package-review decision rows or state
- handoff/export rows or artifacts
- runtime snapshot DB rows
- source-ingestion rows
- schema/migration files

If implementation requires schema widening, the endpoint must not be implemented under this contract.

## Idempotency And Concurrency

`client_request_id` is required.

Rules:

- the server must serialize package construction for the session
- first valid request may create the package write set
- exact retry with the same `client_request_id`, same session, same plan, same pass, same result-review record, same preview id/hash, and same package-preview hash may return the existing package summary
- a retry with the same `client_request_id` but different authority fields must fail closed
- a second request with a different `client_request_id` after package rows exist must fail closed or return deterministic already-constructed status only if the stored package summary proves the same authority basis
- duplicate rows or duplicate payload writes are not admitted

## Owner-Service Adapter Contract

The implementation must keep package payload construction inside `backend/app/services/layer3_package_entry.py` or a directly owned helper module if one already exists for that service family.

The workbench helper must:

- reuse `PACKAGE_KIND_CANONICAL_INTERNAL`, `PACKAGE_KIND_USER_FACING`, and `PACKAGE_KIND_REVIEW_FACING`
- reuse existing `L3OutputPackage` and `L3ReconciliationRecord` models
- reuse existing payload-ref/hash persistence conventions where possible
- keep existing `materialize_package_entry(...)` behavior unchanged
- fail closed rather than fabricating Gate D `phase1a_loading_closure` or `pass_entry`
- expose enough summary metadata for API tests to prove the exact write set

## Failure Behavior

The endpoint must fail closed when:

- approved plan or preview identity is missing or stale
- selected pass is missing, foreign, non-selected, or non-terminal
- result/status authority is unavailable
- result review is missing, not approved, blocked, rejected, or changes requested
- `result_review_record_ref` mismatches stored review state
- package-review preview hash or identity mismatches current preview basis
- selected-pass output metadata is missing or unreadable
- approved result review still has unresolved trace references
- existing package/reconciliation rows already exist for the session and cannot be proven to be the same idempotent request
- owner-service adapter cannot construct all three package families
- request payload asks for package-review submission, handoff/export, rerun, recovery, source expansion, schema migration, runtime DB write, output rewrite, package payload override, or full mockup activation

For server errors, the UI must preserve existing upstream state and display the block reason. It must not replace missing authority with browser-local guesses.

## UI Boundary

If a later implementation changes `/review/layer3`, the UI may only expose:

- package commit readiness after package-review preview inspection
- one package construction commit action
- read-only post-commit summaries for the reconciliation record and three package rows
- disabled package-review submit, handoff, and export indicators

The UI must not expose:

- package-review decision controls
- editable package variants
- handoff/export controls
- rerun/retry/recovery/cancel controls
- source-expansion pickers
- local upload or directory selectors
- raw output editing or rewrite controls
- qualitative/hybrid/RAG/vector controls

## Tests Required Before Merge

Implementation tests must cover:

- no package commit before a session exists
- no package commit before approved plan, selected terminal pass, result/status authority, approved result review, and package-preview basis exist
- non-approved result-review states fail closed
- stale preview id/hash fails closed
- stale or mismatched `result_review_record_ref` fails closed
- stale or mismatched `package_review_preview_hash` fails closed
- missing output metadata and unresolved trace fail closed
- forbidden package-review/handoff/rerun/source/schema/runtime/output-rewrite fields fail closed
- existing package rows block conflicting commits
- identical idempotent retry does not duplicate rows or payload files
- successful commit creates exactly one `L3ReconciliationRecord`, exactly three `L3OutputPackage` rows, and exactly three payload files
- package kinds are limited to `canonical_internal`, `user_facing`, and `review_facing`
- no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, handoff artifact, runtime DB row, schema migration, or source-ingestion row is created
- existing Gate D `materialize_package_entry(...)` tests still pass
- existing result/status, result-review, and package-review preview flows still pass
- both headed and headless Chrome browser proof pass if rendered UI behavior changes

## Still Deferred

Still deferred after this contract:

- package-review submission or decision state
- package variant tabs as editable live controls
- handoff/export trigger policy
- APS handoff behavior
- result-review amendment or supersession
- rerun, retry, cancellation, or recovery workflows beyond deterministic commit idempotency
- approved-plan correction or supersession
- source-breadth expansion
- local upload or local-directory ingestion
- qualitative/hybrid/RAG/vector execution
- broad UI/full mockup activation
