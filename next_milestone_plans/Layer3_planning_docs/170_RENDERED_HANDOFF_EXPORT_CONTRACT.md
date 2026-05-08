# Rendered Handoff Export Prepare Contract

Status: planning/control UI and API contract for `169_RENDERED_HANDOFF_EXPORT_FREEZE.md`.

This contract specifies the only future rendered control proof currently selected for moving the raw mixed `/review/layer3` UI past approved package-review authority. It is not an implementation and admits no runtime behavior by itself.

## Contract Scope

Selected mode: `raw_mixed_rendered_handoff_export_prepare`.

The future implementation may only drive existing rendered operator controls for:

- `POST /api/v1/layer3/handoff/export/prepare`

It must reuse the existing backend contracts:

- request DTO `Layer3HandoffExportPrepareRequest`
- response schema `Layer3HandoffExportPrepareResponse`

It must not introduce a new route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, connector dispatch path, provider URL path, RAG/vector path, hidden LLM path, full mockup path, APS dispatch runtime, external export/download runtime, or auth/security behavior.

## Handoff Export Prepare Request

The rendered handoff/export prepare request must be assembled from server-backed package-review state:

- `client_request_id`: new browser-generated request id for this operator action;
- `session_id`: current server-created Layer 3 session id;
- `analysis_plan_id`: id returned by plan approval for the current session;
- `pass_run_id`: selected pass run returned by execution selection and started by execution start;
- `preview_id`: current approved plan preview id;
- `preview_hash`: current approved plan preview hash;
- `result_review_record_ref`: server-returned ref from an approved selected-pass result review;
- `package_review_preview_hash`: server-returned package review preview hash;
- `reconciliation_record_id`: server-returned package reconciliation id;
- `output_package_ids`: package ids returned by package construction/package submit;
- `payload_refs`: payload refs returned by package construction/package submit;
- `payload_hashes`: payload hashes returned by package construction/package submit;
- `package_review_submit_record_ref`: server-returned package-review submit ref;
- `package_review_state`: `package_review_approved`;
- `package_review_submit_schema_id`: server-returned package-review submit schema id;
- `handoff_target`: exactly `internal_export_envelope`;
- `export_mode`: exactly `prepare_only`;
- `operator_decision`: one of the current admitted decisions, with the proof using `authorize_prepare`;
- `expected_package_kinds`: exactly `canonical_internal`, `user_facing`, and `review_facing`;
- `decision_notes`: optional for `authorize_prepare`, required by UI state for `hold`, `decline`, and `blocked`;
- `analysis_run_id`: optional id returned by execution start or result/status authority when the associated-cohort path admits it;
- `construction_basis_hash`: optional only where the server-authoritative path admits or requires it.

The browser must not include or infer deferred fields: `aps_handoff`, `dispatch`, `send`, `external_export`, `external_target`, `download`, `connector_run_id`, `runtime_db_write`, `analysis_artifact`, `artifact_manifest`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `edited_findings`, `result_review_amendment`, `package_review_amendment`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, or `schema_migration`.

## Handoff Export Prepare Response

Expected `Layer3HandoffExportPrepareResponse` fields that the UI may consume:

- `schema_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_identity`
- `analysis_run_id`
- `result_review_record_ref`
- `package_review_preview_hash`
- optional `construction_basis_hash`
- `reconciliation_record_id`
- `output_package_ids`
- `package_kinds`
- `payload_refs`
- `payload_hashes`
- pass, scope, method, source-gate, source-shape, and source-dataset summary fields
- `package_review_submit_schema_id`
- `package_review_submit_record_ref`
- `package_review_state`
- `operator_decision`
- `decision_notes`
- `handoff_export_state`
- `handoff_target`
- `export_mode`
- `external_handoff_enabled`
- `external_export_enabled`
- `dispatch_enabled`
- `aps_handoff_enabled`
- `external_export_download_enabled`
- `connector_dispatch_enabled`
- `provider_public_url_enabled`
- `downstream_unavailable`
- `next_state`
- `prepare_record_ref`
- `handoff_export_envelope`
- `authority_rail`

The response is authoritative for recorded handoff/export prepare state. Browser state may display the response, but there must be no frontend-only durable authority.

## Rendered State Model

The future UI proof must use these phases:

- `not_ready`: no approved package-review authority for the current session;
- `package_review_approved_ready`: session summary exposes handoff/export prepare readiness;
- `notes_required`: `hold`, `decline`, or `blocked` is selected without notes;
- `submitting`: request to `/handoff/export/prepare` is pending;
- `prepared`: response supplies `handoff_export_state: handoff_export_prepared`, `prepare_record_ref`, and a handoff/export envelope;
- `next_ready`: the UI may surface APS dispatch readiness after preparation, but the proof must not drive it;
- `blocked`: server error, stale preview, missing session, missing plan, missing selected pass run, missing result/status authority, missing approved result review, missing approved package review, missing reconciliation id, missing package ids/refs/hashes, cancellation/recovery/rerun state, forbidden field, source expansion, package mutation, APS dispatch, external export/download, or unsupported downstream scope.

The UI must preserve existing disabled states for external export/download controls until APS dispatch/external readiness is separately proved. An error in handoff/export prepare must not unlock external export/download controls.

## Selector and Layout Contract

Future proof must use stable existing selectors:

- `[data-operation-target="handoff-export-band"]`
- `#handoff-export-prepare-decision`
- `#handoff-export-prepare-notes`
- `#handoff-export-prepare-submit`
- `#handoff-export-prepare-panel`

The controls must remain keyboard focusable, visibly labeled, and readable in the existing handoff/export workband. They must not overlap result-review controls, package controls, APS dispatch controls, external export/download controls, step chips, or mockup sections across desktop and mobile viewports.

## Theme Contract

The proof must inherit the existing Layer 3 theme system:

- shared `light`;
- shared `dark`;
- Layer 3 `workbench`;
- existing `system` resolution;
- no change to `claude` prototype routing.

The operation-dock tab for `handoff-export-band` is a workbench-mode rendered control; the proof must not assume it is visible in `light` or `dark`. The full upstream path must still exercise light, dark, and workbench theme states where existing controls support them.

## Browser Proof Contract

The future browser proof must:

- drive raw mixed source materialization through rendered controls or approved API setup before opening `/review/layer3`;
- use only returned source IDs after materialization/seed setup;
- drive rendered preflight, source preview, material preview, Gate B, Gate C, plan preview, and plan approval;
- drive rendered execution selection and execution start through existing controls;
- inspect rendered result/status;
- submit rendered result review as `approved`;
- inspect package review preview, commit package construction, and submit package review through existing controls;
- submit handoff/export prepare as `authorize_prepare` through existing controls;
- assert the handoff/export prepare route request contains only admitted fields;
- assert no APS dispatch request, external export/download request, provider URL, connector dispatch, RAG/vector, upload, directory, hidden LLM, mockup, auth/security, package mutation, replacement, or supersession behavior appears;
- run headed and headless Chromium sequentially on the fixed-port `8031` harness unless a later freeze changes the harness.

## Negative Invariants

The implementation must keep these blocked:

- backend route, DTO, service, model, or migration change;
- new rendered controls unless a blocker is reported first;
- source family expansion beyond current admitted classes;
- source adapter registry;
- local upload or local-directory ingestion;
- arbitrary local path input;
- web connector retrieval;
- RAG/vector retrieval or index creation;
- provider/public URL or signed public URL generation;
- real connector or destination dispatch;
- APS handoff dispatch request execution;
- external export/download prepare or deliver;
- broad package mutation or reconstruction;
- package replacement, supersession, amendment, or payload rewrite;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

## Required Validation for Future Implementation

At minimum, the future implementation must run:

- `python .\tools\l3-progress-check.py`
- a focused Playwright test proving rendered raw mixed handoff/export prepare;
- the same focused Playwright test in headed Chromium;
- `npx playwright test e2e/layer3-workbench.spec.js` if feasible;
- `python -m pytest .\backend\tests -k layer3 -q` if feasible;
- `git diff --check`

The future pass should stop at handoff/export prepared state unless a separate freeze admits APS dispatch for the raw mixed rendered path.

## Acceptance Criteria

This contract is accepted only when:

- this file exists and names `Layer3HandoffExportPrepareRequest`;
- it names `Layer3HandoffExportPrepareResponse`;
- it names `POST /api/v1/layer3/handoff/export/prepare`;
- it records exact admitted request fields and deferred forbidden fields;
- it records the `light`, `dark`, and `workbench` theme proof obligation;
- progress/proof manifests, progress board, and `tools/l3-progress-check.py` reference it;
- `python .\tools\l3-progress-check.py` passes.
