# Layer 3 Workbench Handoff Export API And State Contract

Status: planning-only API/state companion for `54_L3_WB_HANDOFF_EXPORT_FREEZE.md`.

This document defines the endpoint, request, response, state, idempotency, and proof contract for a future bounded handoff/export preparation step after package-review approval. It does not make handoff/export live by itself and does not admit APS dispatch, external export, package reconstruction, package payload mutation/copying, new package/reconciliation/artifact rows, source expansion, schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Authority Order

Handoff/export preparation must use this authority order:

1. durable `L3Session` state returned by the Layer 3 API
2. approved `L3AnalysisPlan` identity and approved preview id/hash from server state
3. execution-selection summary from server state
4. selected `L3PassRun` identity, terminal status, and selected-pass output metadata from server state
5. result/status authority for the selected terminal pass
6. approved selected-pass result-review state from server state
7. read-only package-review preview basis from PR `#235`
8. package-construction commit state from PR `#238`
9. stored `L3ReconciliationRecord` and `L3OutputPackage` rows
10. package-review submit state from PR `#243`
11. request payload as preparation intent only
12. browser state as display/cache only

Browser state must not approve, revise, select, run, retry, cancel, package, export, hand off, recover, rewrite, regenerate, or dispatch output.

## Endpoint

A future implementation may add at most one write endpoint:

`POST /api/v1/layer3/handoff/export/prepare`

The endpoint records one operator handoff/export preparation decision for one already approved package-review submit state and may return one internal handoff/export envelope that references the reviewed package set. It must not dispatch to APS, create external export artifacts, create packages, rewrite packages, or trigger downstream behavior.

## Request Contract

Minimum request fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `session_id` | yes | Existing Layer 3 workbench session |
| `analysis_plan_id` | yes | Current approved plan for the session |
| `pass_run_id` | yes | Existing selected terminal pass run for the session and approved plan |
| `preview_id` | yes | Must match approved plan, selected pass, result review, package construction, and package-review submit basis |
| `preview_hash` | yes | Must match approved plan, selected pass, result review, package construction, and package-review submit basis |
| `result_review_record_ref` | yes | Must match the recorded approved selected-pass result-review record |
| `package_review_preview_hash` | yes | Must match the package-review preview basis used for construction and submit |
| `reconciliation_record_id` | yes | Must match the constructed and reviewed package set |
| `output_package_ids` | yes | Must identify exactly the three reviewed package rows |
| `payload_hashes` | yes | Must match stored package payload hashes |
| `package_review_submit_record_ref` | yes | Must match the stored package-review submit decision |
| `package_review_state` | yes | Must equal `package_review_approved` |
| `handoff_target` | yes | Must equal `internal_export_envelope` in this tranche |
| `export_mode` | yes | Must equal `prepare_only` in this tranche |
| `operator_decision` | yes | One of `authorize_prepare`, `hold`, `decline`, or `blocked` |
| `client_request_id` | yes | Required idempotency key for the write |

Conditional request fields:

| Field | Constraint |
| --- | --- |
| `decision_notes` | Required for `hold`, `decline`, or `blocked`; optional but recommended for `authorize_prepare` |
| `analysis_run_id` | If supplied, must match selected pass state |
| `expected_package_kinds` | If supplied, must equal `canonical_internal`, `user_facing`, and `review_facing` as a set |

Forbidden request fields include:

- `aps_handoff`
- `dispatch`
- `send`
- `external_export`
- `external_target`
- `download`
- `connector_run_id`
- `runtime_db_write`
- `analysis_artifact`
- `artifact_manifest`
- `create_package`
- `rebuild_package`
- `package_payload`
- `package_variant_content`
- `rewrite_output`
- `edited_findings`
- `result_review_amendment`
- `package_review_amendment`
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

## Response Contract

Minimum success response fields:

| Field | Meaning |
| --- | --- |
| `schema_id` | `layer3.handoff_export_prepare.v1` or later frozen replacement |
| `status` | `prepared`, `held`, `declined`, `blocked`, or deterministic idempotent replay status |
| `session_id` | session authority |
| `analysis_plan_id` | approved-plan authority |
| `pass_run_id` | selected pass-run authority |
| `preview_identity` | matched preview id/hash metadata |
| `result_review_record_ref` | matched approved result-review record |
| `package_review_preview_hash` | matched package-preview identity |
| `reconciliation_record_id` | reviewed package-set anchor |
| `output_package_ids` | exactly three reviewed package ids |
| `package_kinds` | exactly `canonical_internal`, `user_facing`, and `review_facing` |
| `payload_refs` | stored package payload refs proved unchanged |
| `payload_hashes` | stored package payload hashes proved unchanged |
| `package_review_submit_record_ref` | package-review approval authority |
| `package_review_state` | must be `package_review_approved` |
| `operator_decision` | submitted handoff/export preparation decision |
| `handoff_export_state` | `handoff_export_prepared`, `handoff_export_held`, `handoff_export_declined`, or `handoff_export_blocked` |
| `handoff_target` | `internal_export_envelope` |
| `export_mode` | `prepare_only` |
| `external_handoff_enabled` | always `false` in this tranche |
| `external_export_enabled` | always `false` in this tranche |
| `dispatch_enabled` | always `false` in this tranche |
| `downstream_unavailable` | must include `aps_handoff`, `external_export`, and `downstream_dispatch` |
| `next_state` | the handoff/export preparation state produced by the submitted decision |

If `operator_decision == "authorize_prepare"`, the response may include a deterministic `handoff_export_envelope` object. That object may include only:

- envelope schema id
- envelope id/ref
- session id
- analysis plan id
- pass run id
- result review record ref
- package-review preview hash
- package-review submit record ref
- reconciliation record id
- output package ids
- package kinds
- payload refs
- payload hashes
- created/prepared timestamp
- downstream disabled flags

The response must not include package payload bodies, downstream APS ids, generated external artifacts, download URLs, connector-run ids, editable package payloads, or rewritten package content.

## State Model Delta

The implementation may add only these state meanings:

| State | Authority source | Allowed next actions | Forbidden downstream actions |
| --- | --- | --- | --- |
| `handoff_export_unavailable` | missing approved package-review submit state or upstream authority | inspect upstream state | handoff/export preparation, APS dispatch, external export |
| `handoff_export_blocked` | stale authority, partial package set, hash mismatch, forbidden payload, or operator block | inspect block reasons | APS dispatch, external export, package rewrite |
| `handoff_export_ready` | server-validated approved package-review submit state and immutable reviewed package set | submit one preparation decision | APS dispatch, external export |
| `handoff_export_prepared` | operator authorized internal preparation and server recorded envelope summary | inspect internal envelope; await separate dispatch/export freeze | APS dispatch, external export |
| `handoff_export_held` | operator held the approved package set from preparation | inspect decision; optionally await a separately frozen reconsideration path | APS dispatch, external export |
| `handoff_export_declined` | operator declined handoff/export under the current authority basis | inspect decision | APS dispatch, external export, package rewrite |

These states authorize internal preparation only. They do not authorize APS handoff, external export, package reconstruction, package payload mutation/copying, result-review amendment, package-review amendment, rerun/recovery, source expansion, schema/runtime widening, or full mockup activation.

## Write Contract

The endpoint may create or update only:

- one handoff/export preparation object in `L3ReconciliationRecord.summary_json`
- optional `L3Session.summary_json` handoff/export preparation pointer/index fields

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
- `L3OutputPackage.status`
- package-review submit state
- APS handoff rows or artifacts
- external export files
- runtime snapshot DB rows
- connector-run state
- source-ingestion rows
- schema/migration files

If implementation requires schema widening, physical export artifact persistence, `AnalysisArtifact` usage, package row mutation, or downstream dispatch, the endpoint must not be implemented under this contract.

## Idempotency And Concurrency

`client_request_id` is required.

Rules:

- the server must serialize handoff/export preparation for the session
- first valid request may record the preparation state
- exact retry with the same `client_request_id`, same authority basis, same package ids/hashes, same package-review submit ref, and same operator decision may return the existing preparation summary
- a retry with the same `client_request_id` but different authority fields or decision fields must fail closed
- a second request with a different `client_request_id` after preparation state exists must fail closed unless the stored decision proves the same authority basis and same decision
- duplicate or conflicting handoff/export preparation decisions are not admitted

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
- package-review submit state is missing, stale, conflicting, or not `package_review_approved`
- `package_review_submit_record_ref` mismatches stored package-review submit state
- `handoff_target` is not `internal_export_envelope`
- `export_mode` is not `prepare_only`
- decision notes are missing for `hold`, `decline`, or `blocked`
- request payload asks for APS handoff, external export, dispatch, package reconstruction, package payload copy/rewrite, rerun, recovery, source expansion, schema migration, runtime DB write, output rewrite, or full mockup activation

For server errors, the UI must preserve existing upstream, package, and package-review state and display the block reason. It must not replace missing authority with browser-local guesses.

## UI Boundary

If a later implementation changes `/review/layer3`, the UI may only expose:

- approved package-review state returned by the server
- handoff/export preparation readiness
- one decision form with the four admitted decisions
- required notes for non-authorization decisions
- read-only internal envelope summary after `authorize_prepare`
- disabled external handoff/export/dispatch indicators

The UI must not expose:

- APS handoff controls
- external export/download controls
- downstream destination selectors
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

- no handoff/export preparation before package-review submit exists
- non-approved package-review submit states fail closed
- missing or stale package-review submit ref fails closed
- stale preview id/hash fails closed
- stale or mismatched `result_review_record_ref` fails closed
- stale or mismatched `package_review_preview_hash` fails closed
- stale or mismatched reconciliation id, package ids, package kinds, payload refs, or payload hashes fail closed
- wrong `handoff_target` or `export_mode` fails closed
- missing notes for `hold`, `decline`, and `blocked` fail closed
- forbidden APS handoff/external export/dispatch/package-rewrite/rerun/source/schema/runtime/output-rewrite fields fail closed
- successful preparation records exactly one preparation object
- identical idempotent retry does not duplicate or alter preparation state
- conflicting duplicate request fails closed
- payload refs and hashes remain unchanged
- no package payload file is created, copied, deleted, or rewritten
- no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, APS handoff artifact, external export file, runtime DB row, schema migration, source-ingestion row, additional reconciliation row, or additional package row is created
- existing package construction and package-review submit flows still pass
- both headed and headless Chrome browser proof pass if rendered UI behavior changes

## Still Deferred

Still deferred after this contract:

- APS handoff behavior
- external export/download/dispatch
- downstream target-family selection
- physical export artifact persistence
- package rebuild or amendment after `changes_requested`
- package payload editing/copying
- result-review amendment or supersession
- package-review amendment or supersession
- approved-plan correction or supersession
- source-breadth expansion
- local upload or local-directory ingestion
- qualitative/hybrid/RAG/vector execution
- broad UI/full mockup activation
