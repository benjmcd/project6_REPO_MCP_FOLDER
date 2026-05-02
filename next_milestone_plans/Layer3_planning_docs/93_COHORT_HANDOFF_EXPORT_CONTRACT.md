# Layer 3 Selected-Pass Cohort Handoff Export Contract

## Status

Planning-only API/state contract for the bounded associated-cohort handoff/export tranche selected by `92_COHORT_HANDOFF_EXPORT_FREEZE.md`.

This contract does not make runtime behavior live by itself. It defines the future proof boundary for admitting associated-cohort handoff/export preparation after PR `#456` package-review submit.

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
9. PR `#456` associated-cohort package-review submit decision object and response metadata.
10. Cohort package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE` and cohort submit schema `layer3.cohort_package_review_submit.v1`.
11. Source gate and cohort provenance: `78_COHORT_FREEZE`, `aligned_wide_table`, exact `descriptive_summary`, matching `source_dataset_version_ids`, and reviewed trace references.
12. Handoff/export preparation request as operator preparation intent only.

If any earlier authority is absent, stale, malformed, mismatched, partial, or not approved where approval is required, handoff/export preparation must fail closed.

## Route Contract

Default implementation target:

- `POST /api/v1/layer3/handoff/export/prepare`

The existing route may be extended only if the audit proves the associated-cohort path can preserve single-item handoff/export behavior and keep request/response semantics unambiguous. A new route is allowed only if route reuse would make single-item and associated-cohort authority ambiguous.

Current main intentionally reports associated-cohort handoff/export as unavailable with `handoff_export_deferred_for_associated_cohort_package_review_submit`, and direct preparation remains blocked for cohort state. A future implementation may remove or narrow that rejection only for the exact authority chain in this contract.

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
- `payload_refs`
- `payload_hashes`
- `expected_package_kinds`
- `package_review_submit_record_ref`
- `package_review_state`
- `handoff_target`
- `export_mode`
- `operator_decision`
- `decision_notes`
- `client_request_id`

`expected_package_kinds`, if supplied, must equal `canonical_internal`, `user_facing`, and `review_facing` as a set. `package_review_state` must equal `package_review_approved`. `handoff_target` must equal `internal_export_envelope`. `export_mode` must equal `prepare_only`. `operator_decision` must be one of `authorize_prepare`, `hold`, `decline`, or `blocked`. `decision_notes` are required for `hold`, `decline`, and `blocked`.

Forbidden request fields include, but are not limited to:

- APS handoff fields, dispatch fields, external export/download fields, connector targets, package payload overrides, package variant content, package reconstruction flags, source overrides, schema/runtime overrides, retry/recovery fields, pass-entry mutation fields, result-review amendment fields, package-review amendment fields, package-construction mutation fields, artifact creation fields, and UI-only inferred readiness flags.

The server must derive handoff/export readiness from recorded state. The client must not be trusted to restate or amend reviewed output items, package payloads, package refs, package hashes, submit readiness, or preparation readiness.

## Response Contract

The success response should identify:

- `schema_id`, preferably `layer3.cohort_handoff_export_prepare.v1` if the existing schema cannot safely distinguish single-item and associated-cohort preparation state;
- `session_id`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`, `preview_id`, and `preview_hash`;
- `result_review_record_ref`;
- `package_review_preview_hash`;
- pass scope `associated_cohort`;
- method `descriptive_summary`;
- source gate `78_COHORT_FREEZE`;
- package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE`;
- package-review submit schema `layer3.cohort_package_review_submit.v1`;
- source shape `aligned_wide_table`;
- source dataset version ids;
- exactly one `reconciliation_record_id`;
- exactly three output package summaries for `canonical_internal`, `user_facing`, and `review_facing`;
- payload refs and payload hashes for the three existing package payload files;
- package-review submit record ref and approved package-review state;
- operator decision and resulting handoff/export preparation state;
- deterministic replay status when the same request is retried;
- downstream unavailable state for APS dispatch, external export/download, connectors, and generic downstream dispatch.

If `operator_decision == "authorize_prepare"`, the response may include an internal `handoff_export_envelope` object. That object may contain only envelope identity, upstream authority refs, package ids/kinds, payload refs/hashes, prepared timestamp, and downstream disabled flags.

The response must not include APS handoff refs, connector dispatch refs, generated downstream artifacts, external export files, download URLs, editable package payload bodies, rewritten package content, or any field implying downstream dispatch has already happened.

## State Contract

Allowed state effects:

- read existing session, plan, pass, result, result-review, package-review preview, package-construction, package-review submit, reconciliation, and package state;
- write one handoff/export preparation object in existing JSON-bearing state;
- optionally update `L3Session.summary_json` with preparation pointers only.

Forbidden state effects:

- creating APS dispatch, external export/download, connector, source, schema, runtime, migration, or artifact rows;
- creating or mutating package rows or package payload files;
- mutating package payload refs or payload hashes;
- mutating reviewed output items, result-review decisions, package-review submit decisions, pass-entry state, source datasets, execution results, or package-construction authority;
- updating `L3OutputPackage.status` unless separately frozen.

## Idempotency And Concurrency

`client_request_id` is required.

Rules:

- the server must serialize handoff/export preparation for the session;
- the first valid request may record the preparation decision;
- exact retry with the same `client_request_id`, session, plan, pass, analysis run, result-review record, preview id/hash, package-review preview hash, reconciliation id, package ids, payload refs, payload hashes, package-review submit ref, and operator decision may return the existing preparation summary;
- retry with the same `client_request_id` but different authority fields or decision fields must fail closed;
- a second request with a different `client_request_id` after a preparation decision exists must fail closed or return deterministic already-prepared state only if stored preparation authority proves the same basis and same decision;
- partial handoff/export preparation state must fail closed.

## UI Contract

If the rendered `/review/layer3` UI is touched in the future implementation:

- enable associated-cohort handoff/export preparation only after server-authoritative preparation readiness exists;
- submit only admitted request fields;
- require notes for non-authorization decisions;
- display server-provided blocked reasons;
- display internal envelope state read-only after preparation;
- keep APS dispatch, external export/download, connector, retry/recovery, package reconstruction, and broader UI controls disabled;
- preserve existing single-item UI behavior;
- prove the rendered flow in headed and headless Chrome.

## Test Contract

Minimum future implementation proof:

- focused backend/API tests for successful associated-cohort handoff/export preparation after PR `#456` approved package-review submit;
- focused regression tests proving single-item handoff/export and downstream single-item flow are unchanged;
- tests proving no reconciliation rows, package rows, package payload files, artifact rows, plan rows, pass rows, or run rows are created;
- tests proving no package payload refs, payload hashes, or package payload files change;
- tests for duplicate identical retry, conflicting duplicate retry, partial-state failure, forbidden fields, missing notes, invalid decisions, non-approved submit states, and mismatched provenance;
- rendered page/static tests if UI changes;
- headed and headless browser proof if rendered UI changes.

## Still Deferred

Still deferred after this contract:

- APS handoff behavior;
- external export/download behavior;
- connector dispatch;
- package rebuild or amendment after `changes_requested`;
- package payload editing or copying;
- result-review amendment or supersession;
- package-review amendment or supersession;
- approved-plan correction or supersession;
- source-breadth expansion;
- local upload or local-directory ingestion;
- qualitative/hybrid/RAG/vector execution;
- broad UI/full mockup activation.
