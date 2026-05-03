# Layer 3 Selected-Pass Cohort External Export Download Readiness Contract

## Status

Current-main API/state contract for the bounded associated-cohort external export/download readiness tranche selected by `96_COHORT_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md` and implemented by PR `#479`.

This contract did not make runtime behavior live by itself. PR `#479` is the separate implementation proof for admitting associated-cohort reference-only external export/download readiness after PR `#466` associated-cohort APS evidence-bundle handoff dispatch.

## Authority Order

The implementation must resolve authority in this order:

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
12. PR `#466` associated-cohort APS handoff dispatch object, `aps_evidence_bundle_handoff` package row, APS bundle ref/id/schema/hash, and persisted APS evidence-bundle artifact.
13. Cohort package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE` and cohort submit schema `layer3.cohort_package_review_submit.v1`.
14. Source gate and cohort provenance: `78_COHORT_FREEZE`, `aligned_wide_table`, exact `descriptive_summary`, matching `source_dataset_version_ids`, and reviewed trace references.
15. Existing external export/download readiness descriptor pattern from docs `62`/`63` and current `external_export_download_prepare(...)` behavior.
16. External export/download readiness request as operator readiness intent only.

If any earlier authority is absent, stale, malformed, mismatched, partial, or not approved/prepared/dispatched where required, readiness preparation must fail closed before writing state.

## Route Contract

Default implementation target:

- `POST /api/v1/layer3/handoff/export/download/prepare`

The existing route may be extended only if the audit proves the associated-cohort path can preserve single-item readiness/delivery behavior and keep request/response semantics unambiguous. A new route is allowed only if route reuse would make single-item and associated-cohort authority ambiguous.

PR `#479` narrows the associated-cohort `associated_cohort_external_export_download_prepare_not_admitted` rejection only for the exact authority chain in this contract. All stale, partial, mismatched, non-cohort, or downstream-widening states remain fail-closed.

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
- `aps_handoff_record_ref`
- `aps_handoff_state`
- `aps_handoff_target`
- `dispatch_mode`
- `aps_output_package_id`
- `aps_output_package_kind`
- `aps_bundle_ref`
- `aps_bundle_id`
- `aps_schema_id`
- `aps_bundle_hash`
- `aps_bundle_size_bytes`
- `export_download_target`
- `download_mode`
- `operator_decision`
- `decision_notes`
- `client_request_id`

`package_kinds` must equal `canonical_internal`, `user_facing`, and `review_facing` as a set. `package_review_state` must equal `package_review_approved`. `handoff_export_state` must equal `handoff_export_prepared`. `handoff_target` must equal `internal_export_envelope`. `export_mode` must equal `prepare_only`. `aps_handoff_state` must equal `aps_handoff_dispatched`. `aps_handoff_target` must equal `aps_evidence_bundle`. `dispatch_mode` must equal `server_side_aps_handoff`. `aps_output_package_kind` must equal `aps_evidence_bundle_handoff`. `export_download_target` must equal `aps_evidence_bundle_download_reference`. `download_mode` must equal `reference_only_prepare`. `operator_decision` must equal `prepare_external_export_download`.

Forbidden request fields include, but are not limited to:

- download fields, browser delivery fields, public URL fields, signed URL fields, local file path fields, connector targets, generic dispatch targets, destination selectors, package payload overrides, package variant content, package reconstruction flags, source overrides, schema/runtime overrides, retry/recovery fields, pass-entry mutation fields, result-review amendment fields, package-review amendment fields, package-construction mutation fields, handoff/export mutation fields, APS dispatch mutation fields, artifact creation fields, and UI-only inferred readiness flags.

The server must derive readiness from recorded state. The client must not be trusted to restate or amend reviewed output items, package payloads, package refs, package hashes, submit readiness, preparation readiness, APS dispatch readiness, APS artifact compatibility, or download readiness.

## Response Contract

The success response should identify:

- `schema_id == layer3.external_export_download_prepare.v1` unless implementation audit proves a cohort-specific schema id is required for compatibility;
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
- APS handoff state, target, mode, record ref, output package id/kind, bundle ref/id/schema/hash/size;
- export/download target `aps_evidence_bundle_download_reference`;
- download mode `reference_only_prepare`;
- operator decision `prepare_external_export_download`;
- external export/download state;
- external export/download record ref;
- export/download descriptor ref;
- source artifact ref/hash/size derived from the existing APS evidence-bundle handoff artifact;
- deterministic replay status when the same request is retried;
- downstream unavailable state for browser download, download URLs, connectors, destination selection, and generic downstream dispatch.

The response must be reference-only. It may identify the existing APS evidence-bundle handoff artifact, but it must not include raw package payload bodies, raw APS bundle bodies, editable package content, download URLs, connector-run ids, external destination refs, local file paths intended for browser use, or rewritten package content.

## State Contract

Allowed state effects:

- read existing session, plan, pass, result, result-review, package-review preview, package-construction, package-review submit, handoff/export prepare, APS handoff dispatch, reconciliation, package, and APS bundle state;
- write one external export/download readiness object in existing JSON-bearing workbench state;
- optionally update `L3Session.summary_json` with readiness pointers only.

Forbidden state effects:

- creating browser delivery, connector, generic downstream, destination, source, schema, runtime, migration, `AnalysisArtifact`, connector-run, package, reconciliation, plan, pass, or run rows;
- creating or mutating source package rows or source package payload files;
- mutating APS handoff package rows, APS bundle refs, APS bundle hashes, or APS bundle artifact bytes;
- mutating reviewed output items, result-review decisions, package-review submit decisions, handoff/export prepare decisions, APS handoff dispatch decisions, pass-entry state, source datasets, execution results, or package-construction authority;
- updating existing `L3OutputPackage.status` unless separately frozen.

## Idempotency And Concurrency

`client_request_id` is required.

Rules:

- the server must serialize external export/download readiness preparation for the session;
- the first valid request may record the readiness descriptor;
- exact retry with the same `client_request_id`, session, plan, pass, analysis run, result-review record, preview id/hash, package-review preview hash, reconciliation id, source package ids/kinds, payload refs, payload hashes, package-review submit ref, prepare ref, envelope ref, APS handoff ref, APS output package id/kind, APS bundle ref/id/schema/hash/size, target, mode, and operator decision may return the existing readiness summary;
- retry with the same `client_request_id` but different authority fields or decision fields must fail closed;
- a second request with a different `client_request_id` after readiness exists must fail closed or return deterministic already-prepared state only if stored readiness authority proves the same basis and same decision;
- partial external export/download readiness state must fail closed.

## UI Contract

This contract does not require rendered UI work.

If the rendered `/review/layer3` UI is touched in the future implementation:

- enable associated-cohort external export/download readiness only after server-authoritative readiness exists;
- submit only admitted request fields;
- display server-provided blocked reasons;
- display readiness descriptors read-only after preparation;
- keep browser delivery, public/signed URLs, connector dispatch, destination selection, retry/recovery, package reconstruction, and broader UI controls disabled unless separately frozen;
- preserve existing single-item UI behavior;
- prove the rendered flow in headed and headless Chrome.

## Test Contract

Minimum PR `#479` implementation proof:

- focused backend/API tests for successful associated-cohort external export/download readiness after PR `#466` APS handoff dispatch state;
- focused regression tests proving single-item external export/download readiness, delivery, rendered readiness UI, and rendered delivery UI behavior are unchanged;
- tests proving no package rows, source package rows, source package payload files, reconciliation rows, `AnalysisArtifact` rows, connector-run rows, plan rows, pass rows, or run rows are created;
- tests proving no source package payload refs, payload hashes, source package payload files, APS handoff package refs/hashes, or APS bundle bytes change;
- tests for exact duplicate retry, conflicting duplicate retry, partial-state failure, forbidden fields, invalid decisions, non-approved submit states, non-prepared handoff states, non-dispatched APS handoff states, missing APS output package, malformed APS provenance, orphan APS package rows, missing APS artifact, and mismatched provenance;
- replace the prior associated-cohort `associated_cohort_external_export_download_prepare_not_admitted` regression with success plus fail-closed cohort-specific proof;
- rendered page/static tests if UI changes;
- headed and headless browser proof if rendered UI changes.

## Still Deferred

Still deferred after this contract:

- browser download route and delivery;
- rendered download controls;
- public or signed URLs;
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

