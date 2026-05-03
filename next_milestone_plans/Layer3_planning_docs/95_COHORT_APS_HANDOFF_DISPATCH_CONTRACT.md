# Layer 3 Selected-Pass Cohort APS Handoff Dispatch Contract

## Status

Current-main planning-only API/state contract from PR `#464` for the bounded associated-cohort APS handoff dispatch tranche selected by `94_COHORT_APS_HANDOFF_DISPATCH_FREEZE.md`.

This contract does not make runtime behavior live by itself. It defines the future proof boundary for admitting associated-cohort APS evidence-bundle handoff dispatch after PR `#460` handoff/export prepare-only state and PR `#462` rendered prepare authority projection/proof.

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
10. PR `#460` associated-cohort handoff/export prepare-only object, prepare ref, and internal envelope ref.
11. PR `#462` rendered prepare proof if the future implementation relies on rendered operator flow.
12. Cohort package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE` and cohort submit schema `layer3.cohort_package_review_submit.v1`.
13. Source gate and cohort provenance: `78_COHORT_FREEZE`, `aligned_wide_table`, exact `descriptive_summary`, matching `source_dataset_version_ids`, and reviewed trace references.
14. Existing APS evidence-bundle handoff owner-service compatibility in `backend/app/services/layer3_aps_handoff.py`.
15. APS handoff dispatch request as operator dispatch intent only.

If any earlier authority is absent, stale, malformed, mismatched, partial, or not approved/prepared where required, APS handoff dispatch must fail closed before writing state, package rows, or artifacts.

## Route Contract

Default implementation target:

- `POST /api/v1/layer3/handoff/aps/dispatch`

The existing route may be extended only if the audit proves the associated-cohort path can preserve single-item APS dispatch behavior and keep request/response semantics unambiguous. A new route is allowed only if route reuse would make single-item and associated-cohort authority ambiguous.

Current main intentionally reports associated-cohort APS dispatch as unavailable with `associated_cohort_aps_handoff_dispatch_not_admitted`, and direct dispatch remains blocked for cohort prepare state. A future implementation may remove or narrow that rejection only for the exact authority chain in this contract.

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
- `package_kinds`
- `payload_refs`
- `payload_hashes`
- `package_review_submit_record_ref`
- `package_review_state`
- `prepare_record_ref`
- `handoff_export_state`
- `handoff_export_envelope_ref`
- `handoff_target`
- `export_mode`
- `aps_handoff_target`
- `dispatch_mode`
- `operator_decision`
- `decision_notes`
- `client_request_id`

`package_kinds` must equal `canonical_internal`, `user_facing`, and `review_facing` as a set. `package_review_state` must equal `package_review_approved`. `handoff_export_state` must equal `handoff_export_prepared`. `handoff_target` must equal `internal_export_envelope`. `export_mode` must equal `prepare_only`. `aps_handoff_target` must equal `aps_evidence_bundle`. `dispatch_mode` must equal `server_side_aps_handoff`. `operator_decision` must equal `dispatch_aps_handoff`.

Forbidden request fields include, but are not limited to:

- external export/download fields, connector targets, generic dispatch targets, destination selectors, package payload overrides, package variant content, package reconstruction flags, source overrides, schema/runtime overrides, retry/recovery fields, pass-entry mutation fields, result-review amendment fields, package-review amendment fields, package-construction mutation fields, handoff/export mutation fields, artifact creation fields, and UI-only inferred readiness flags.

The server must derive APS dispatch readiness from recorded state. The client must not be trusted to restate or amend reviewed output items, package payloads, package refs, package hashes, submit readiness, preparation readiness, APS compatibility, or dispatch readiness.

## Response Contract

The success response should identify:

- `schema_id`, preferably `layer3.cohort_aps_handoff_dispatch.v1` if the existing schema cannot safely distinguish single-item and associated-cohort dispatch state;
- `session_id`, `analysis_plan_id`, `pass_run_id`, `analysis_run_id`, `preview_id`, and `preview_hash`;
- `result_review_record_ref`;
- `package_review_preview_hash`;
- pass type `associated_cohort`;
- pass scope `quantitative_associated_cohort_dataset_version`;
- method `descriptive_summary`;
- source gate `78_COHORT_FREEZE`;
- package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE`;
- package-review submit schema `layer3.cohort_package_review_submit.v1`;
- source shape `aligned_wide_table`;
- source dataset version ids;
- exactly one `reconciliation_record_id`;
- exactly three source package summaries for `canonical_internal`, `user_facing`, and `review_facing`;
- payload refs and payload hashes for the three existing package payload files;
- package-review submit record ref and approved package-review state;
- prepare record ref, prepared handoff/export state, and internal envelope ref;
- APS handoff target `aps_evidence_bundle`;
- dispatch mode `server_side_aps_handoff`;
- operator decision `dispatch_aps_handoff`;
- APS handoff dispatch state;
- APS handoff record ref;
- one APS output package id with kind `aps_evidence_bundle_handoff`;
- APS bundle ref, bundle id, schema id, and validation state;
- deterministic replay status when the same request is retried;
- downstream unavailable state for external export/download, connectors, destination selection, and non-APS downstream dispatch.

The response must be reference-first. It may identify the APS evidence-bundle handoff artifact produced by the existing owner service, but it must not include raw package payload bodies, editable package content, download URLs, connector-run ids, external destination refs, or rewritten package content.

## State Contract

Allowed state effects:

- read existing session, plan, pass, result, result-review, package-review preview, package-construction, package-review submit, handoff/export prepare, reconciliation, and package state;
- write one APS handoff dispatch object in existing JSON-bearing workbench state;
- create one `L3OutputPackage` row of kind `aps_evidence_bundle_handoff` only through the existing APS handoff owner-service contract;
- persist one APS evidence-bundle artifact only through the existing APS evidence-bundle handoff contract;
- optionally update `L3Session.summary_json` with dispatch pointers only.

Forbidden state effects:

- creating external export/download, connector, generic downstream, source, schema, runtime, migration, or `AnalysisArtifact` rows;
- creating or mutating source package rows or source package payload files;
- mutating source package payload refs or payload hashes;
- mutating reviewed output items, result-review decisions, package-review submit decisions, handoff/export prepare decisions, pass-entry state, source datasets, execution results, or package-construction authority;
- updating existing `L3OutputPackage.status` unless separately frozen.

## Idempotency And Concurrency

`client_request_id` is required.

Rules:

- the server must serialize APS handoff dispatch for the session;
- the first valid request may record the dispatch decision and materialize the APS evidence-bundle handoff row/artifact;
- exact retry with the same `client_request_id`, session, plan, pass, analysis run, result-review record, preview id/hash, package-review preview hash, reconciliation id, source package ids/kinds, payload refs, payload hashes, package-review submit ref, prepare ref, envelope ref, and operator decision may return the existing dispatch summary;
- retry with the same `client_request_id` but different authority fields or decision fields must fail closed;
- a second request with a different `client_request_id` after dispatch exists must fail closed or return deterministic already-dispatched state only if stored dispatch authority proves the same basis and same decision;
- partial APS handoff dispatch state must fail closed.

## UI Contract

This contract does not require rendered UI work.

If the rendered `/review/layer3` UI is touched in the future implementation:

- enable associated-cohort APS dispatch only after server-authoritative dispatch readiness exists;
- submit only admitted request fields;
- display server-provided blocked reasons;
- display APS output package and bundle refs read-only after dispatch;
- keep external export/download, browser delivery, connector, destination selection, retry/recovery, package reconstruction, and broader UI controls disabled unless separately frozen;
- preserve existing single-item UI behavior;
- prove the rendered flow in headed and headless Chrome.

## Test Contract

Minimum future implementation proof:

- focused backend/API tests for successful associated-cohort APS handoff dispatch after PR `#460` prepared handoff/export state;
- focused regression tests proving single-item APS dispatch, external export/download readiness, delivery, and rendered APS dispatch UI behavior are unchanged;
- tests proving exactly one APS handoff package row and exactly one APS evidence-bundle artifact are created on success;
- tests proving no source package rows, source package payload files, reconciliation rows, `AnalysisArtifact` rows, plan rows, pass rows, or run rows are created;
- tests proving no source package payload refs, payload hashes, or source package payload files change;
- tests for duplicate identical retry, conflicting duplicate retry, partial-state failure, forbidden fields, invalid decisions, non-approved submit states, non-prepared handoff states, owner-service provenance missing, malformed APS provenance, orphan APS package rows, and mismatched provenance;
- update the current associated-cohort `associated_cohort_aps_handoff_dispatch_not_admitted` regression only when implementation lands, and replace it with success plus fail-closed cohort-specific proof;
- rendered page/static tests if UI changes;
- headed and headless browser proof if rendered UI changes.

## Still Deferred

Still deferred after this contract:

- external export/download readiness and delivery;
- connector dispatch;
- non-APS downstream dispatch;
- destination selection;
- package rebuild or amendment after `changes_requested`;
- package payload editing, copying, or reconstruction;
- result-review amendment or supersession;
- package-review amendment or supersession;
- approved-plan correction or supersession;
- source-breadth expansion;
- local upload or local-directory ingestion;
- qualitative/hybrid/RAG/vector execution;
- broad UI/full mockup activation.
