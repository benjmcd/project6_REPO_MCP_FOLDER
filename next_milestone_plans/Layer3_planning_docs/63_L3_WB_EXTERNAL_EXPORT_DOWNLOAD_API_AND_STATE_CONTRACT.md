# 63 L3 Workbench External Export Download API And State Contract

Status: planning-only API/state contract for the future bounded Layer 3 workbench external export/download readiness boundary frozen by `62_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md`.

This document defines the request, response, state, idempotency, write, and proof contract for one future backend/API external export/download readiness preparation step after `aps_handoff_dispatched`. It does not make the endpoint live by itself and does not admit a browser download route, rendered download controls, public download URLs, generic downstream dispatch, connector dispatch, destination selection, package mutation/reconstruction, schema/runtime/source widening, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Authority Order

The implementation must use this authority order:

1. server-stored Layer 3 session, approved plan, selected pass, result/status, result-review, package construction, package-review submit, handoff/export prepare, and APS handoff dispatch state
2. existing `L3ReconciliationRecord.summary_json` and `L3Session.summary_json` JSON-bearing workbench state
3. existing source `L3OutputPackage` rows and payload refs/hashes
4. existing APS `aps_evidence_bundle_handoff` output package row
5. existing APS evidence-bundle artifact ref/id/schema/hash validation through the APS owner-service contract
6. request fields only as claims that must be revalidated server-side

Browser state must not authorize export, download, dispatch, destination selection, connector execution, package mutation, artifact creation, rerun, recovery, schema/runtime/source widening, or payload rewriting.

## Planned Endpoint

The planned future endpoint is:

`POST /api/v1/layer3/handoff/export/download/prepare`

The endpoint may prepare one server-authoritative external export/download readiness descriptor for an already recorded APS evidence-bundle handoff. It must not stream a file, generate a browser download URL, dispatch to a connector, create a destination binding, copy package payloads, rewrite package content, or create additional package/reconciliation/artifact rows.

If implementation audit finds that this route name conflicts with existing router conventions, the implementation may stop and freeze an equivalent route name before coding. The behavior and state contract below remain the governing intent.

## Request Contract

Required request fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `session_id` | yes | Workbench session id |
| `analysis_plan_id` | yes | Approved plan id bound to the selected pass |
| `pass_run_id` | yes | Selected terminal pass run id |
| `preview_id` | yes | Approved preview id |
| `preview_hash` | yes | Current approved preview hash |
| `result_review_record_ref` | yes | Approved result-review record ref |
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
| `export_download_target` | yes | Must equal `aps_evidence_bundle_download_reference` |
| `download_mode` | yes | Must equal `reference_only_prepare` |
| `operator_decision` | yes | Must equal `prepare_external_export_download` |
| `client_request_id` | yes | Required idempotency key |
| `decision_notes` | optional | Operator rationale; server must store only if admitted by implementation |

Optional request fields:

- `analysis_run_id`, only if already present in server authority and revalidated against the selected pass.
- `aps_bundle_hash`, only if already present in server authority and revalidated against the APS bundle artifact.
- `aps_bundle_size_bytes`, only if already present or cheaply derived by the server from the validated APS bundle artifact.

Forbidden request fields must fail closed:

- `download`
- `download_url`
- `download_token`
- `public_url`
- `signed_url`
- `local_file_path`
- `external_target`
- `destination`
- `destination_selector`
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

## State Vocabulary

Allowed external export/download readiness states:

| State | Meaning |
| --- | --- |
| `external_export_download_unavailable` | Required APS dispatch or upstream authority is absent |
| `external_export_download_ready` | Server can prove APS dispatch authority and validated APS bundle source |
| `external_export_download_prepared` | One reference-only export/download readiness descriptor was recorded |
| `external_export_download_blocked` | Server proved readiness cannot be prepared without widening or missing provenance |
| `external_export_download_conflict` | Existing readiness record or replay conflict prevents another preparation |

No other state name is admitted by this contract.

## Minimum Success Response

A successful response must include:

- `schema_id == layer3.external_export_download_prepare.v1`
- `status`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_identity`
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
- `aps_output_package_kind == aps_evidence_bundle_handoff`
- `aps_bundle_ref`
- `aps_bundle_id`
- `aps_schema_id`
- `export_download_target == aps_evidence_bundle_download_reference`
- `download_mode == reference_only_prepare`
- `operator_decision == prepare_external_export_download`
- `external_export_download_state`
- `external_export_download_record_ref`
- `export_download_descriptor_ref`
- `source_artifact_ref == aps_bundle_ref`
- `source_artifact_schema_id == aps_schema_id`
- `source_artifact_hash` when available
- `source_artifact_size_bytes` when available
- `browser_download_enabled == false`
- `download_url_enabled == false`
- `connector_dispatch_enabled == false`
- `destination_selection_enabled == false`
- `generic_downstream_dispatch_enabled == false`
- `downstream_unavailable`, including at least `browser_download`, `download_url`, `connector_dispatch`, `destination_selection`, and `generic_downstream_dispatch`
- `next_state`

The response must be reference-only. It must not include raw package payload bodies, raw APS bundle bodies, editable package content, rewritten content, public or signed download URLs, connector-run ids, external destination refs, local file paths intended for browser use, or newly generated export file bodies.

## Write Contract

Permitted write:

- existing workbench JSON-bearing state may record one reference-only external export/download readiness summary.

Prohibited writes:

- no mutation of existing source package rows
- no mutation, copy, or rewrite of existing source package payload files
- no mutation of the APS handoff package row
- no mutation, copy, or rewrite of the APS evidence-bundle artifact
- no new package row
- no new reconciliation row
- no `AnalysisArtifact` row
- no connector-run row or mutation
- no schema migration
- no runtime snapshot DB write outside existing owner-service artifact behavior
- no new plan, pass, or analysis-run rows
- no source-ingestion rows
- no new physical export file unless a later freeze admits materialization explicitly

## Idempotency And Concurrency

- `client_request_id` is required.
- Preparation must be serialized for the session.
- Exact retry with the same `client_request_id`, same APS dispatch authority basis, same package ids/refs/hashes, same submit ref, same prepare ref, same APS handoff ref, same APS bundle ref/hash, same target, mode, and decision may return the existing readiness summary.
- Same `client_request_id` with changed authority, package fields, prepare fields, APS fields, target, mode, or decision must fail closed.
- Different `client_request_id` after an existing external export/download readiness record must fail closed unless it proves the same authority basis and a later implementation explicitly supports replay-as-inspection.
- Duplicate/conflicting external export/download preparation decisions are not admitted.

## Required Fail-Closed Cases

An implementation must fail closed when:

- `aps_handoff_state` is missing or not `aps_handoff_dispatched`
- `aps_handoff_record_ref` is missing or stale
- `aps_output_package_id` is missing or stale
- `aps_output_package_kind` is not `aps_evidence_bundle_handoff`
- `aps_bundle_ref`, `aps_bundle_id`, or `aps_schema_id` is missing or stale
- the APS bundle artifact cannot be resolved and validated through the existing APS evidence-bundle contract
- `handoff_export_state` is missing or not `handoff_export_prepared`
- `prepare_record_ref` or `handoff_export_envelope_ref` is missing or stale
- `handoff_target` is not `internal_export_envelope`
- `export_mode` is not `prepare_only`
- `package_review_state` is missing or not `package_review_approved`
- package ids, kinds, payload refs, or payload hashes differ from prepared or dispatched authority
- `export_download_target` is not `aps_evidence_bundle_download_reference`
- `download_mode` is not `reference_only_prepare`
- `operator_decision` is not `prepare_external_export_download`
- a prior external export/download readiness record already exists for the session and the request is not an exact replay
- any forbidden field is present

## Session Summary Contract

`session_summary()` may expose an `external_export_download` object only as server-authoritative state. Minimum fields:

- `schema_id`
- `available`
- `state`
- `blocked_reason`
- `aps_handoff_record_ref`
- `aps_output_package_id`
- `aps_bundle_ref`
- `aps_bundle_id`
- `aps_schema_id`
- `export_download_target`
- `download_mode`
- `external_export_download_record_ref`
- `export_download_descriptor_ref`
- `source_artifact_ref`
- `source_artifact_hash`
- `browser_download_enabled == false`
- `download_url_enabled == false`
- `connector_dispatch_enabled == false`
- `destination_selection_enabled == false`
- `generic_downstream_dispatch_enabled == false`
- `downstream_unavailable`

Before `aps_handoff_dispatched`, this summary must remain unavailable and must not cause top-level blockers to skip the active APS handoff dispatch state.

## UI Contract

This API/state contract does not require UI work. If a later implementation changes `/review/layer3`, the UI must be separately frozen to define:

- when an external export/download readiness panel renders
- whether a download button or link is admitted
- how recorded readiness is displayed read-only
- how unavailable/blocked/conflict states render
- how browser request fields are assembled from server state
- headed and headless Chromium proof requirements

Until that UI freeze exists, rendered external export/download controls remain absent or disabled.

## Verification Contract

At minimum, an implementation must run:

- focused Layer 3 API tests for external export/download readiness success and fail-closed cases
- existing APS handoff dispatch API tests
- existing handoff/export prepare tests
- existing `backend/tests/test_layer3_aps_handoff.py`
- package-review submit and package-construction regression tests
- page/browser tests only if rendered UI changes
- JSON validation for touched manifests
- `git diff --check`

## Explicit Deferred Scope

Still deferred after this contract:

- actual browser download route/control
- public, signed, or local download URL exposure
- external export file streaming
- generic downstream dispatch
- connector-run dispatch
- destination selection
- package amendment/rebuild/supersession
- package payload mutation/reconstruction
- additional reconciliation/package/artifact rows
- `AnalysisArtifact` expansion
- schema/runtime/source widening
- execution expansion beyond already admitted work
- qualitative/hybrid/RAG/vector execution
- full mockup activation
