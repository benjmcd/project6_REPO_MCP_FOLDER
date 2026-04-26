# 59 L3 Workbench APS Handoff Dispatch API And State Contract

Status: planning-only API/state contract for a future bounded workbench APS handoff dispatch endpoint.

This document defines the request, response, state, idempotency, write, and proof contract for a future workbench APS handoff dispatch step after `handoff_export_prepared`. It does not implement an endpoint by itself and does not admit external export/download, generic downstream dispatch, destination selection, connector dispatch, package mutation/rebuild, source/runtime/schema widening, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Authority Order

A future implementation must use the following authority order:

1. server-stored Layer 3 session, plan, pass, result/status, result-review, package construction, package-review submit, and handoff/export prepare state
2. existing `L3ReconciliationRecord.summary_json` and `L3Session.summary_json` state for workbench review/prepare authority
3. existing `L3OutputPackage` rows and payload refs/hashes
4. existing APS evidence-bundle handoff owner service contract in `layer3_aps_handoff.py`
5. browser request fields only as claimed authority inputs that must be revalidated server-side

Browser state must not authorize APS handoff, export, dispatch, package mutation, artifact creation, connector execution, rerun, recovery, or schema/runtime/source widening.

## Endpoint

If implemented later, the endpoint should be:

`POST /api/v1/layer3/handoff/aps/dispatch`

The endpoint may dispatch exactly one prepared internal handoff/export envelope to the existing APS evidence-bundle handoff owner service. It must not dispatch to arbitrary downstream systems and must not create external export/download artifacts.

## Request Contract

Required request fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `session_id` | yes | Workbench session id |
| `analysis_plan_id` | yes | Approved plan id bound to the selected pass |
| `pass_run_id` | yes | Selected terminal pass run id |
| `preview_id` | yes | Approved plan/result preview id used by the workbench chain |
| `preview_hash` | yes | Current preview hash |
| `result_review_record_ref` | yes | Approved result-review record ref |
| `package_review_preview_hash` | yes | Package-review preview hash used for construction |
| `reconciliation_record_id` | yes | Existing package construction reconciliation id |
| `output_package_ids` | yes | Existing package ids from package construction |
| `package_kinds` | yes | Expected existing package kinds |
| `payload_refs` | yes | Existing package payload refs |
| `payload_hashes` | yes | Existing package payload hashes |
| `package_review_submit_record_ref` | yes | Approved package-review submit ref |
| `package_review_state` | yes | Must equal `package_review_approved` |
| `prepare_record_ref` | yes | Recorded handoff/export prepare ref |
| `handoff_export_state` | yes | Must equal `handoff_export_prepared` |
| `handoff_export_envelope_ref` | yes | Recorded internal envelope ref |
| `handoff_target` | yes | Must equal `internal_export_envelope` |
| `export_mode` | yes | Must equal `prepare_only` |
| `aps_handoff_target` | yes | Must equal `aps_evidence_bundle` |
| `dispatch_mode` | yes | Must equal `server_side_aps_handoff` |
| `operator_decision` | yes | Must equal `dispatch_aps_handoff` |
| `client_request_id` | yes | Required idempotency key |
| `decision_notes` | conditional | Required if the future implementation admits any non-dispatch decision state |

Optional request field:

- `analysis_run_id`, only if already present in server authority and revalidated against the selected pass.

Forbidden request fields must fail closed:

- `external_export`
- `external_target`
- `download`
- `download_url`
- `destination`
- `destination_selector`
- `connector_run_id`
- `connector_dispatch`
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

Allowed future APS handoff dispatch states:

| State | Meaning |
| --- | --- |
| `aps_handoff_unavailable` | Required prepared-envelope or package authority is absent |
| `aps_handoff_ready` | Server can prove prepared-envelope authority and APS handoff compatibility |
| `aps_handoff_dispatched` | One APS evidence-bundle handoff row/artifact was created |
| `aps_handoff_blocked` | Server proved dispatch cannot occur without widening or missing provenance |
| `aps_handoff_conflict` | Existing handoff or replay conflict prevents another dispatch |

No other state name is admitted by this contract.

## Minimum Success Response

A successful future response must include:

- `schema_id`
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
- `aps_handoff_target`
- `dispatch_mode`
- `operator_decision`
- `aps_handoff_state`
- `aps_handoff_record_ref`
- `aps_output_package_id`
- `aps_output_package_kind == aps_evidence_bundle_handoff`
- `aps_bundle_ref`
- `aps_bundle_id`
- `aps_schema_id`
- `source_package_refs`
- `source_package_hashes`
- `external_export_enabled == false`
- `download_enabled == false`
- `connector_dispatch_enabled == false`
- `downstream_unavailable`, including at least `external_export`, `download`, `connector_dispatch`, and `non_aps_dispatch`
- `next_state`

The response must be reference-first. It may identify the APS evidence-bundle handoff artifact produced by the existing owner service, but it must not include raw package payload bodies, editable package content, download URLs, connector-run ids, external destination refs, or rewritten package content.

## Write Contract

Permitted future writes:

- existing workbench JSON-bearing state may record one APS handoff dispatch summary
- the existing APS handoff owner service may create one `L3OutputPackage` row of kind `aps_evidence_bundle_handoff`
- the existing APS evidence-bundle handoff contract may persist one APS evidence-bundle artifact

Prohibited writes:

- no mutation of existing package rows
- no mutation, copy, or rewrite of existing package payload files
- no additional reconciliation row
- no `AnalysisArtifact` row
- no connector-run row or mutation
- no schema migration
- no runtime snapshot DB write outside the existing APS evidence-bundle handoff artifact behavior
- no new plan, pass, or analysis-run rows
- no source-ingestion rows

## Idempotency And Concurrency

- `client_request_id` is required.
- Dispatch must be serialized for the session.
- Exact retry with the same `client_request_id`, same prepared-envelope authority basis, same package ids/refs/hashes, same submit ref, same prepare ref, and same dispatch decision may return the existing APS handoff summary.
- Same `client_request_id` with changed authority, package fields, prepare fields, target, mode, or decision must fail closed.
- Different `client_request_id` after an existing APS handoff dispatch must fail closed unless it proves the same authority basis and the future implementation explicitly supports replay-as-inspection.
- Duplicate/conflicting APS handoff dispatch decisions are not admitted.

## Required Fail-Closed Cases

A future implementation must fail closed when:

- `handoff_export_state` is missing or not `handoff_export_prepared`
- `prepare_record_ref` is missing or stale
- `handoff_export_envelope_ref` is missing or stale
- `handoff_target` is not `internal_export_envelope`
- `export_mode` is not `prepare_only`
- `aps_handoff_target` is not `aps_evidence_bundle`
- `dispatch_mode` is not `server_side_aps_handoff`
- `operator_decision` is not `dispatch_aps_handoff`
- package-review submit state is missing or not `package_review_approved`
- package ids, kinds, payload refs, or payload hashes differ from prepared authority
- the existing APS handoff owner service reports missing APS provenance
- the existing APS evidence-bundle contract fails validation
- a prior APS handoff row already exists for the session and the request is not an exact replay
- any forbidden field is present

## Session Summary Contract

If implemented later, `session_summary()` may expose an `aps_handoff_dispatch` object only as server-authoritative state. Minimum fields:

- `schema_id`
- `available`
- `state`
- `blocked_reason`
- `prepare_record_ref`
- `handoff_export_envelope_ref`
- `aps_handoff_target`
- `dispatch_mode`
- `aps_output_package_id`
- `aps_bundle_ref`
- `aps_bundle_id`
- `external_export_enabled == false`
- `download_enabled == false`
- `connector_dispatch_enabled == false`
- `downstream_unavailable`

Before `handoff_export_prepared`, this summary must remain unavailable and must not cause top-level blockers to skip the active handoff/export prepare state.

## UI Contract

This API/state contract does not require UI work. If a later implementation changes `/review/layer3`, the UI must:

- render APS handoff dispatch only after server reports `aps_handoff_ready`
- keep external export/download, destination selection, and connector dispatch absent or disabled
- render dispatched state as read-only server truth
- avoid package edit, rebuild, amendment, rerun, retry, recover, or cancel controls
- generate one `client_request_id` per submit attempt
- include only admitted fields in the request
- pass both headless and headed Chromium proof

## Verification Contract

At minimum, a later implementation must run:

- focused Layer 3 API tests for APS handoff dispatch success and fail-closed cases
- existing handoff/export prepare tests
- existing `backend/tests/test_layer3_aps_handoff.py`
- package-review submit and package-construction regression tests
- page/browser tests if rendered UI changes
- `git diff --check`

If JSON manifests are touched, validate them with `python -m json.tool`.

## Explicit Deferred Scope

Still deferred after this contract:

- external export/download
- non-APS downstream dispatch
- connector-run dispatch
- destination selection
- package amendment/rebuild/supersession
- schema/runtime/source widening
- qualitative/hybrid/RAG/vector execution
- execution selection/start UI expansion
- full mockup activation
