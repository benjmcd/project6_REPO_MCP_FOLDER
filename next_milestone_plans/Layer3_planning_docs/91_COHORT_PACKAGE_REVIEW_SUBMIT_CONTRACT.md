# Layer 3 Selected-Pass Cohort Package Review Submit Contract

## Status

Planning-only API/state contract for the bounded associated-cohort package-review submit tranche selected by `90_COHORT_PACKAGE_REVIEW_SUBMIT_FREEZE.md`.

This contract does not make runtime behavior live by itself. It defines the future proof boundary for admitting associated-cohort package-review submit after PR `#451` package construction.

## Authority Order

Future implementation must resolve authority in this order:

1. Current `L3Session` state.
2. Approved `L3AnalysisPlan` and matching preview id/hash.
3. Selected terminal `L3PassRun`.
4. PR `#432` associated-cohort execution-start/result-status metadata and output authority.
5. PR `#438` associated-cohort result-review backend/API envelope.
6. PR `#443` rendered result-review UI provenance, including `reviewed_output_items`.
7. PR `#447` read-only package-review preview/readiness response and server-recomputed package-review preview hash.
8. PR `#451` associated-cohort package-construction summary, reconciliation row, package rows, payload refs, and payload hashes.
9. Cohort package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE`.
10. Source gate and cohort provenance: `78_COHORT_FREEZE`, `aligned_wide_table`, exact `descriptive_summary`, matching `source_dataset_version_ids`, and reviewed trace references.
11. Package-review submit request as operator decision intent only.

If any earlier authority is absent, stale, malformed, mismatched, partial, or not approved where approval is required, package-review submit must fail closed.

## Route Contract

Default implementation target:

- `POST /api/v1/layer3/package/review/submit`

The existing route may be extended only if the audit proves the associated-cohort path can preserve single-item package-review submit behavior and keep request/response semantics unambiguous. A new route is allowed only if route reuse would make single-item and associated-cohort authority ambiguous.

Current main intentionally rejects this path with `associated_cohort_package_review_submit_not_admitted`. A future implementation may remove or narrow that rejection only for the exact authority chain in this contract.

## Request Fields

Allowed request fields:

- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `analysis_run_id`
- `result_review_record_ref`
- `package_review_preview_hash`
- `reconciliation_record_id`
- `output_package_ids`
- `payload_hashes`
- `expected_package_kinds`
- `operator_decision`
- `decision_notes`
- `client_request_id`

`expected_package_kinds`, if supplied, must equal `canonical_internal`, `user_facing`, and `review_facing` as a set. `operator_decision` must be one of `approved`, `changes_requested`, `rejected`, or `blocked`. `decision_notes` are required for `changes_requested`, `rejected`, and `blocked`.

Forbidden request fields include, but are not limited to:

- handoff/export fields, APS dispatch fields, external export/download fields, connector targets, package payload overrides, package variant content, package reconstruction flags, source overrides, schema/runtime overrides, retry/recovery fields, pass-entry mutation fields, result-review amendment fields, package-construction mutation fields, and UI-only inferred readiness flags.

The server must derive package-review submit readiness from recorded state. The client must not be trusted to restate or amend reviewed output items, package payloads, package refs, package hashes, or submit readiness.

## Response Contract

The success response should identify:

- `schema_id`, preferably `layer3.cohort_package_review_submit.v1` if the existing schema cannot safely distinguish single-item and associated-cohort submit state;
- `session_id`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`, `preview_id`, and `preview_hash`;
- `result_review_record_ref`;
- `package_review_preview_hash`;
- pass scope `associated_cohort`;
- method `descriptive_summary`;
- source gate `78_COHORT_FREEZE`;
- package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE`;
- source shape `aligned_wide_table`;
- source dataset version ids;
- exactly one `reconciliation_record_id`;
- exactly three output package summaries for `canonical_internal`, `user_facing`, and `review_facing`;
- payload refs and payload hashes for the three existing package payload files;
- operator decision and resulting package-review state;
- deterministic replay status when the same request is retried;
- downstream unavailable state for handoff/export, APS dispatch, external export/download, and connectors.

The response must not include handoff/export refs, connector dispatch refs, generated downstream artifacts, editable package payload bodies, rewritten package content, or any field implying handoff/export has already happened.

## State Contract

Allowed state effects:

- read existing session, plan, pass, result, result-review, package-review preview, package-construction, reconciliation, and package state;
- write one package-review decision object in existing JSON-bearing state;
- optionally update `L3Session.summary_json` with package-review decision pointers only.

Forbidden state effects:

- creating handoff/export, APS dispatch, external export/download, connector, source, schema, runtime, migration, or artifact rows;
- creating or mutating package rows or package payload files;
- mutating package payload refs or payload hashes;
- mutating reviewed output items, result-review decisions, pass-entry state, source datasets, execution results, or package-construction authority;
- updating `L3OutputPackage.status` unless separately frozen.

## Idempotency And Concurrency

`client_request_id` is required.

Rules:

- the server must serialize package-review submit for the session;
- the first valid request may record the package-review decision;
- exact retry with the same `client_request_id`, session, plan, pass, analysis run, result-review record, preview id/hash, package-review preview hash, reconciliation id, package ids, payload hashes, and operator decision may return the existing decision summary;
- retry with the same `client_request_id` but different authority fields or decision fields must fail closed;
- a second request with a different `client_request_id` after a decision exists must fail closed or return deterministic already-submitted state only if stored package-review authority proves the same basis and same decision;
- partial package-review decision state must fail closed.

## UI Contract

If the rendered `/review/layer3` UI is touched in the future implementation:

- enable associated-cohort package-review submit only after server-authoritative submit readiness exists;
- submit only admitted request fields;
- require notes for non-approval decisions;
- display server-provided blocked reasons;
- display decision state read-only after submit;
- keep handoff/export, APS dispatch, external export/download, connector, retry/recovery, package reconstruction, and broader UI controls disabled;
- preserve existing single-item UI behavior;
- prove the rendered flow in headed and headless Chrome.

## Test Contract

Minimum future implementation proof:

- focused backend/API tests for successful associated-cohort package-review submit after PR `#451` package construction;
- focused regression tests proving single-item package-review submit and downstream single-item flow are unchanged;
- tests proving no reconciliation rows, package rows, package payload files, artifact rows, plan rows, pass rows, or run rows are created;
- tests proving no package payload refs, payload hashes, or package payload files change;
- tests for duplicate identical retry, conflicting duplicate retry, partial-state failure, forbidden fields, missing notes, invalid decisions, and mismatched provenance;
- rendered page/static tests if UI changes;
- headed and headless browser proof if rendered UI changes.

## Still Deferred

Still deferred after this contract:

- handoff/export trigger policy;
- APS handoff behavior;
- external export/download behavior;
- connector dispatch;
- package rebuild or amendment after `changes_requested`;
- package payload editing;
- result-review amendment or supersession;
- approved-plan correction or supersession;
- source-breadth expansion;
- local upload or local-directory ingestion;
- qualitative/hybrid/RAG/vector execution;
- broad UI/full mockup activation.
