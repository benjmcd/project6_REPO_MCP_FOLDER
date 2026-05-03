# Layer 3 Selected-Pass Cohort External Export Download Delivery Contract

## Status

Current-main API/state governance paired with `98_COHORT_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_FREEZE.md`, with branch-local implementation proof on `codex/l3-cohort-delivery-impl-p17`.

This document defines the request, response, authority, and proof contract for same-origin associated-cohort external export/download delivery after PR `#479` readiness. It does not make rendered delivery controls live by itself and does not admit public URLs, signed URLs, connector dispatch, destination selection, generic downstream dispatch, package mutation/reconstruction, schema/runtime/source widening, qualitative/hybrid/RAG/vector behavior, or full mockup activation.

## Authority Order

The implementation must use this authority order:

1. server-stored Layer 3 session, approved plan, selected associated-cohort pass, result/status, result-review, package construction, package-review submit, handoff/export prepare, APS handoff dispatch, and external export/download readiness state;
2. existing `L3ReconciliationRecord.summary_json` and `L3Session.summary_json` JSON-bearing workbench state;
3. existing source `L3OutputPackage` rows and payload refs/hashes;
4. existing APS `aps_evidence_bundle_handoff` output package row;
5. existing APS evidence-bundle artifact ref/id/schema/hash/size validation through the APS owner-service contract;
6. request fields only as claims that must be revalidated server-side.

Browser state must not authorize delivery, URL generation, connector execution, destination selection, package mutation, artifact creation, rerun, recovery, schema/runtime/source widening, or payload rewriting.

## Endpoint

The endpoint is:

`POST /api/v1/layer3/handoff/export/download/deliver`

The existing endpoint may stream the validated APS evidence-bundle handoff artifact as a same-origin response after server-side authority proof. It must not create a public URL, signed URL, connector run, destination binding, copied package payload, rewritten artifact, additional package row, reconciliation row, `AnalysisArtifact` row, source-ingestion row, runtime DB row, or schema migration.

If implementation audit proves that the existing single-item delivery route already owns this path, the implementation must keep single-item and associated-cohort authority branches explicit and fail closed on ambiguity. If route reuse would blur authority, a cohort-specific route or smaller prerequisite freeze is required before coding.

Branch `codex/l3-cohort-delivery-impl-p17` takes the route-reuse branch of that decision: no new endpoint is added, and the associated-cohort proof verifies that delivery revalidates recorded readiness through `external_export_download_prepare(...)`, streams the existing artifact, leaves rows/files unchanged, and fails closed on stale associated-cohort dispatch provenance.

## Request Contract

Required request fields for the `POST` shape:

| Field | Required | Meaning |
| --- | --- | --- |
| `session_id` | yes | Workbench session id |
| `analysis_plan_id` | yes | Approved plan id bound to the selected associated-cohort pass |
| `pass_run_id` | yes | Selected terminal associated-cohort pass run id |
| `preview_id` | yes | Approved preview id |
| `preview_hash` | yes | Current approved preview hash |
| `pass_type` | yes | Must equal `associated_cohort` |
| `pass_scope` | yes | Must equal `quantitative_associated_cohort_dataset_version` |
| `method` | yes | Must equal `descriptive_summary` |
| `source_gate` | yes | Must equal `78_COHORT_FREEZE` |
| `source_shape` | yes | Must equal `aligned_wide_table` |
| `source_dataset_version_ids` | yes | Exact dataset-version ids recorded across cohort authority |
| `result_review_record_ref` | yes | Approved associated-cohort result-review record ref |
| `package_review_preview_hash` | yes | Package-review preview hash |
| `reconciliation_record_id` | yes | Existing package construction reconciliation id |
| `output_package_ids` | yes | Existing source package ids from package construction |
| `package_kinds` | yes | Existing source package kinds |
| `payload_refs` | yes | Existing source package payload refs |
| `payload_hashes` | yes | Existing source package payload hashes |
| `package_review_submit_record_ref` | yes | Approved package-review submit ref |
| `package_review_state` | yes | Must equal `package_review_approved` |
| `prepare_record_ref` | yes | Recorded handoff/export prepare ref |
| `handoff_export_state` | yes | Must equal `handoff_export_prepared` |
| `handoff_export_envelope_ref` | yes | Recorded internal envelope ref |
| `handoff_target` | yes | Must equal `internal_export_envelope` |
| `export_mode` | yes | Must equal `prepare_only` |
| `aps_handoff_record_ref` | yes | Recorded APS handoff dispatch ref |
| `aps_handoff_state` | yes | Must equal `aps_handoff_dispatched` |
| `aps_handoff_target` | yes | Must equal `aps_evidence_bundle` |
| `dispatch_mode` | yes | Must equal `server_side_aps_handoff` |
| `aps_output_package_id` | yes | Existing APS handoff output package id |
| `aps_output_package_kind` | yes | Must equal `aps_evidence_bundle_handoff` |
| `aps_bundle_ref` | yes | Existing persisted APS bundle artifact ref |
| `aps_bundle_id` | yes | Existing APS bundle identity |
| `aps_schema_id` | yes | Existing APS bundle schema id |
| `aps_bundle_hash` | yes | Existing APS bundle hash |
| `aps_bundle_size_bytes` | yes | Existing or server-derived APS bundle size |
| `external_export_download_record_ref` | yes | Recorded readiness ref |
| `export_download_descriptor_ref` | yes | Recorded readiness descriptor ref |
| `external_export_download_state` | yes | Must equal `external_export_download_prepared` |
| `export_download_target` | yes | Must equal `aps_evidence_bundle_download_reference` |
| `download_mode` | yes | Must equal `reference_only_prepare` |
| `delivery_mode` | yes | Must equal `same_origin_artifact_stream` |
| `operator_decision` | yes | Must equal `deliver_external_export_download` |
| `client_request_id` | yes | Required request correlation/idempotency key |

Optional request fields:

- `analysis_run_id`, only if already present in server authority and revalidated against the selected associated-cohort pass.
- `decision_notes`, only as operator rationale; it must not affect authority.

Forbidden request fields must fail closed:

- `download_url`
- `download_token`
- `public_url`
- `signed_url`
- `local_file_path`
- `external_target`
- `destination`
- `destination_selector`
- `destination_id`
- `connector_run_id`
- `connector_dispatch`
- `generic_dispatch`
- `dispatch`
- `send`
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
- `handoff_export_amendment`
- `aps_handoff_amendment`
- `readiness_amendment`
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
- `browser_inferred_authority`

## State Vocabulary

Allowed delivery states:

| State | Meaning |
| --- | --- |
| `associated_cohort_external_export_download_delivery_unavailable` | Required associated-cohort readiness or upstream authority is absent |
| `associated_cohort_external_export_download_delivery_ready` | Server can prove recorded readiness and validated APS bundle source |
| `associated_cohort_external_export_download_delivered` | Server streamed the validated artifact for the accepted request |
| `associated_cohort_external_export_download_delivery_blocked` | Delivery cannot proceed without widening or missing provenance |
| `associated_cohort_external_export_download_delivery_conflict` | Request conflicts with stored authority or a non-idempotent replay |

No state name may imply public URL generation, signed URL generation, connector dispatch, destination selection, generic downstream dispatch, or rendered UI activation.

## Success Response Contract

Because this boundary may stream a binary file, the successful response shape may be one of two server-authoritative forms:

1. a `FileResponse` or equivalent same-origin binary response for the validated APS bundle artifact; or
2. a small JSON preflight response only if implementation audit proves a two-step delivery handoff is needed and freezes that shape explicitly before coding.

For direct binary delivery, the response must:

- stream only the existing validated APS evidence-bundle handoff artifact;
- set a server-derived content type;
- set `Content-Disposition: attachment` with a server-derived filename;
- avoid exposing local filesystem paths;
- avoid public or signed URLs;
- avoid connector-run ids, destination ids, editable package payloads, rewritten content, or newly generated export manifests.

For blocked or conflict responses, the endpoint must use existing Layer 3 error-envelope conventions where possible and include a precise fail-closed reason.

## Write Contract

No durable Layer 3 write is admitted by default.

The endpoint must not create or mutate:

- source package rows;
- source package payload files;
- APS handoff package rows;
- APS evidence-bundle artifact files;
- `L3ReconciliationRecord` rows;
- `L3OutputPackage` rows;
- `AnalysisArtifact` rows;
- connector-run rows;
- plan/pass/analysis rows;
- runtime snapshot DB rows;
- source-ingestion rows;
- schema/migration files.

If an implementation needs persistent delivery receipts, one-shot tokens, access logs, or counters, that is a separate governance question unless the repo already has an admitted non-authoritative audit surface that can be reused without schema/runtime widening.

## Idempotency And Concurrency

- `client_request_id` is required for the planned `POST` shape.
- Delivery checks must be serialized or otherwise protected from racing against state mutation for the session.
- Exact retry with the same `client_request_id` and same authority basis may either re-stream the same artifact or return an idempotent already-delivered response, provided no durable state is mutated.
- Same `client_request_id` with changed authority, package fields, readiness fields, target, mode, or decision must fail closed.
- A different `client_request_id` may request delivery of the same recorded descriptor only if the server revalidates the same authority basis and the implementation remains read-only. If the implementation introduces any durable receipt, duplicate behavior must be frozen explicitly.

## Required Fail-Closed Cases

An implementation must fail closed when:

- `pass_type`, `pass_scope`, `method`, `source_gate`, `source_shape`, or `source_dataset_version_ids` is missing, stale, non-cohort, or mismatched;
- `external_export_download_state` is missing or not `external_export_download_prepared`;
- `external_export_download_record_ref` or `export_download_descriptor_ref` is missing or stale;
- `aps_handoff_state` is missing or not `aps_handoff_dispatched`;
- `aps_handoff_record_ref`, `aps_output_package_id`, or `aps_output_package_kind` is missing or stale;
- `aps_output_package_kind` is not `aps_evidence_bundle_handoff`;
- `aps_bundle_ref`, `aps_bundle_id`, `aps_schema_id`, `aps_bundle_hash`, or `aps_bundle_size_bytes` is missing or stale;
- the APS bundle artifact cannot be resolved and validated through the existing APS evidence-bundle contract;
- `handoff_export_state` is missing or not `handoff_export_prepared`;
- `package_review_state` is missing or not `package_review_approved`;
- package ids, kinds, payload refs, or payload hashes differ from prepared, dispatched, or readiness authority;
- `export_download_target` is not `aps_evidence_bundle_download_reference`;
- `download_mode` is not `reference_only_prepare`;
- `delivery_mode` is not `same_origin_artifact_stream`;
- `operator_decision` is not `deliver_external_export_download`;
- any forbidden field is present.

## Session Summary Contract

This packet does not require session summary to expose a persistent delivery object.

A future implementation may expose an `associated_cohort_external_export_download_delivery` object only as server-authoritative state. Minimum fields, if exposed:

- `schema_id`;
- `available`;
- `state`;
- `blocked_reason`;
- `external_export_download_record_ref`;
- `export_download_descriptor_ref`;
- `source_artifact_ref`;
- `source_artifact_schema_id`;
- `source_artifact_hash`;
- `delivery_mode`;
- `browser_download_enabled`;
- `public_url_enabled == false`;
- `signed_url_enabled == false`;
- `connector_dispatch_enabled == false`;
- `destination_selection_enabled == false`;
- `generic_downstream_dispatch_enabled == false`;
- `downstream_unavailable`;
- `next_state`.

The current branch-local proof keeps session summary persistence unchanged: readiness remains the recorded server state, while delivery is represented by the same-origin attachment response and headers rather than a durable delivered object.

## UI Contract

No rendered UI behavior is admitted by this API/state contract.

A later UI freeze is required before `/review/layer3` renders an active button, link, or browser download affordance for this endpoint. Until then, any rendered associated-cohort readiness surface must remain read-only after readiness and must not invoke the delivery endpoint.

## Proof Requirements

An implementation PR must prove:

- success only after exact recorded associated-cohort `external_export_download_prepared` state;
- stale readiness descriptor, APS dispatch, package-review submit, handoff/export prepare, package refs/hashes, APS package row, or APS bundle ref/hash/size fails closed;
- non-cohort, cross-session, forbidden-field, browser-only, public/signed URL, connector, destination, generic dispatch, package mutation, schema/runtime/source, retry/recovery, or rerun inputs fail closed;
- the delivered response contains only the validated APS evidence-bundle artifact body;
- no public or signed URL is generated;
- no connector/destination/generic dispatch occurs;
- no package, reconciliation, `AnalysisArtifact`, connector-run, plan/pass/analysis, runtime DB, source-ingestion, schema, or physical export artifact rows/files are created;
- source package payload refs/hashes/files, APS handoff package refs/hashes, and APS evidence-bundle artifact bytes do not change;
- existing single-item external export/download readiness and delivery tests still pass;
- existing associated-cohort readiness tests still pass;
- rendered UI tests are required only if a separate UI freeze admits rendered controls.
