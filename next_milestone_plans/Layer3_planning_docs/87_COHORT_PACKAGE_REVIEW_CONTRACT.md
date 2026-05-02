# Layer 3 Selected-Pass Cohort Package-Review Preview Contract

## Status

Planning-only API/state contract for the bounded associated-cohort package-review preview/readiness tranche selected by `86_COHORT_PACKAGE_REVIEW_FREEZE.md`.

This contract does not make runtime behavior live by itself.

## Authority Order

Future implementation must resolve authority in this order:

1. Current `L3Session` state.
2. Approved `L3AnalysisPlan` and matching preview id/hash.
3. Selected terminal `L3PassRun`.
4. PR #432 associated-cohort execution-start/result-status metadata and output authority.
5. PR #438 associated-cohort result-review backend/API envelope.
6. PR #443 rendered result-review UI provenance, including `reviewed_output_items`.
7. Source gate and cohort provenance: `78_COHORT_FREEZE`, `aligned_wide_table`, exact `descriptive_summary`, matching `source_dataset_version_ids`, and reviewed trace references.
8. Package-review preview request as operator intent only.

If any earlier authority is absent, stale, malformed, mismatched, or not approved where approval is required, the preview must fail closed.

## Route Contract

Default implementation target:

- `POST /api/v1/layer3/package/review/preview`

The existing route should be extended only if the audit proves the cohort path can preserve single-item behavior and keep request/response semantics unambiguous. A new route is allowed only if the implementation audit proves route reuse would make single-item and cohort authority ambiguous.

## Request Fields

Allowed request fields:

- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `analysis_run_id`
- `result_review_record_ref`
- `client_request_id`

Forbidden request fields include, but are not limited to:

- package ids, package kinds, package payload refs, package hashes, package commit flags, package-review submit decisions, handoff/export fields, APS dispatch fields, external export/download fields, source overrides, schema/runtime overrides, retry/recovery fields, pass-entry mutation fields, connector targets, and UI-only inferred readiness flags.

The server must derive reviewed output traces from recorded result-review state. The client must not be trusted to restate or amend reviewed output items for preview admission.

## Response Contract

The response should be read-only and should identify:

- schema id, preferably cohort-specific if the existing schema cannot safely distinguish single-item and associated-cohort preview state;
- `session_id`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`, `preview_id`, and `preview_hash`;
- `result_review_record_ref`;
- pass scope `associated_cohort`;
- method `descriptive_summary`;
- source gate `78_COHORT_FREEZE`;
- source shape `aligned_wide_table`;
- source dataset version ids;
- reviewed output item trace summary;
- package-preview readiness;
- blocked reasons when readiness is unavailable;
- candidate package kinds only as preview descriptors, not as constructed packages;
- downstream unavailable state for package commit, package-review submit, handoff/export, APS dispatch, external export/download, and connectors.

The response must not include live package ids, durable package payload refs, durable reconciliation ids, handoff/export refs, connector dispatch refs, or any field that implies construction has already happened.

## State Contract

Allowed state effects:

- read existing session, plan, pass, result, and result-review state;
- optionally record idempotent read-only preview metadata only if the existing package-preview owner pattern already does so for single-item state and the implementation proves it remains non-constructive.

Forbidden state effects:

- creating or mutating `L3OutputPackage`;
- creating or mutating `L3ReconciliationRecord`;
- writing package payload files;
- creating handoff/export, APS dispatch, external export/download, connector, source, schema, runtime, migration, or artifact rows;
- mutating reviewed output items, result-review decisions, pass-entry state, source datasets, or execution results.

## UI Contract

If the rendered `/review/layer3` UI is touched in the future implementation:

- enable associated-cohort package-preview inspection only after server-authoritative approved result-review state exists;
- submit only admitted request fields;
- display server-provided blocked reasons;
- keep package construction, package-review submit, handoff/export, APS dispatch, external export/download, connector, retry/recovery, and broader UI controls disabled;
- preserve existing single-item UI behavior;
- prove the rendered flow in headed and headless Chrome.

## Test Contract

Minimum future implementation proof:

- focused backend/API tests for success and fail-closed cohort preview admission;
- focused regression tests proving single-item package-preview behavior is unchanged;
- tests proving no package/reconciliation rows or payload files are created;
- tests for forbidden fields and mismatched provenance;
- rendered page/static tests if UI changes;
- headed and headless browser proof if rendered UI changes.
