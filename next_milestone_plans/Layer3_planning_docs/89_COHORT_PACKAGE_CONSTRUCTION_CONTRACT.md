# Layer 3 Selected-Pass Cohort Package Construction Contract

## Status

Planning-only API/state contract for the bounded associated-cohort package-construction tranche selected by `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE.md`.

This contract does not make runtime behavior live by itself. It defines the future proof boundary for admitting associated-cohort package construction after PR `#447` read-only package-review preview/readiness.

Implementation note: branch `codex/l3-cohort-package-construction-impl-p61` implements this contract as a bounded branch-local candidate by reusing the existing package-review commit route, requiring the server-recomputed package-review preview hash, and keeping package-review submit plus all downstream behavior disabled.

## Authority Order

Future implementation must resolve authority in this order:

1. Current `L3Session` state.
2. Approved `L3AnalysisPlan` and matching preview id/hash.
3. Selected terminal `L3PassRun`.
4. PR `#432` associated-cohort execution-start/result-status metadata and output authority.
5. PR `#438` associated-cohort result-review backend/API envelope.
6. PR `#443` rendered result-review UI provenance, including `reviewed_output_items`.
7. PR `#447` read-only package-review preview/readiness response and server-recomputed package-review preview hash.
8. Source gate and cohort provenance: `78_COHORT_FREEZE`, `aligned_wide_table`, exact `descriptive_summary`, matching `source_dataset_version_ids`, and reviewed trace references.
9. Existing package owner-service constants, row models, payload persistence conventions, and idempotency pattern.
10. Package-construction request as operator commit intent only.

If any earlier authority is absent, stale, malformed, mismatched, or not approved where approval is required, package construction must fail closed.

## Route Contract

Default implementation target:

- `POST /api/v1/layer3/package/review/commit`

The existing route may be extended only if the audit proves the associated-cohort path can preserve single-item package-construction behavior and keep request/response semantics unambiguous. A new route is allowed only if route reuse would make single-item and associated-cohort authority ambiguous.

Current main intentionally rejects this path with `associated_cohort_package_construction_commit_not_admitted`. A future implementation may remove or narrow that rejection only for the exact authority chain in this contract.

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
- `expected_package_kinds`
- `client_request_id`

`expected_package_kinds`, if supplied, must equal `canonical_internal`, `user_facing`, and `review_facing` as a set.

Forbidden request fields include, but are not limited to:

- package-review submit decisions, handoff/export fields, APS dispatch fields, external export/download fields, connector targets, package payload overrides, package variant content, package reconstruction flags, source overrides, schema/runtime overrides, retry/recovery fields, pass-entry mutation fields, result-review amendment fields, and UI-only inferred readiness flags.

The server must derive reviewed output traces and package-preview readiness from recorded state. The client must not be trusted to restate or amend reviewed output items, package payloads, or commit readiness.

## Response Contract

The success response should identify:

- `schema_id`, preferably cohort-specific if the existing schema cannot safely distinguish single-item and associated-cohort construction state;
- `session_id`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`, `preview_id`, and `preview_hash`;
- `result_review_record_ref`;
- `package_review_preview_hash`;
- pass scope `associated_cohort`;
- method `descriptive_summary`;
- source gate `78_COHORT_FREEZE`;
- source shape `aligned_wide_table`;
- source dataset version ids;
- reviewed output item trace summary;
- exactly one `reconciliation_record_id`;
- exactly three output package summaries for `canonical_internal`, `user_facing`, and `review_facing`;
- payload refs and payload hashes for the three created package payload files;
- deterministic replay status when the same request is retried;
- downstream unavailable state for package-review submit, handoff/export, APS dispatch, external export/download, and connectors.

The response must not include package-review decision state, handoff/export refs, connector dispatch refs, generated downstream artifacts, editable package payload bodies, or any field implying submit/handoff/export has already happened.

## State Contract

Allowed state effects:

- read existing session, plan, pass, result, result-review, and package-review preview state;
- create one `L3ReconciliationRecord`;
- create three `L3OutputPackage` rows;
- write three package payload files through the package owner-service persistence convention;
- optionally update `L3Session.summary_json` with package-construction summary pointers only.

Forbidden state effects:

- creating or mutating package-review submit/decision state;
- creating handoff/export, APS dispatch, external export/download, connector, source, schema, runtime, migration, or artifact rows;
- mutating reviewed output items, result-review decisions, pass-entry state, source datasets, or execution results;
- writing package payload edits beyond the initial three constructed payload files.

## Idempotency And Concurrency

`client_request_id` is required.

Rules:

- the server must serialize package construction for the session;
- the first valid request may create the package write set;
- exact retry with the same `client_request_id`, session, plan, pass, analysis run, result-review record, preview id/hash, and package-review preview hash may return the existing package summary;
- retry with the same `client_request_id` but different authority fields must fail closed;
- a second request with a different `client_request_id` after package rows exist must fail closed or return deterministic already-constructed state only if stored package authority proves the same basis;
- partial package construction state must fail closed.

## UI Contract

If the rendered `/review/layer3` UI is touched in the future implementation:

- enable associated-cohort package construction only after server-authoritative package-preview readiness exists;
- submit only admitted request fields;
- display server-provided blocked reasons;
- display created reconciliation/package refs, payload refs, payload hashes, and downstream disabled state after commit;
- keep package-review submit, handoff/export, APS dispatch, external export/download, connector, retry/recovery, and broader UI controls disabled;
- preserve existing single-item UI behavior;
- prove the rendered flow in headed and headless Chrome.

## Test Contract

Minimum future implementation proof:

- focused backend/API tests for successful associated-cohort package construction after approved result review and package-preview readiness;
- focused regression tests proving single-item package construction and downstream single-item flow are unchanged;
- tests proving exactly one reconciliation row, exactly three package rows, and exactly three package payload files are created;
- tests proving no package-review submit, handoff/export, APS dispatch, external export/download, connector, source, schema, runtime, migration, pass-entry, or artifact rows are created;
- tests for duplicate identical retry, conflicting duplicate retry, partial-state failure, forbidden fields, and mismatched provenance;
- rendered page/static tests if UI changes;
- headed and headless browser proof if rendered UI changes.
