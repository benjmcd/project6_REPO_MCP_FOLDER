# Rendered Package Review Contract

Status: planning/control UI and API contract for `166_RENDERED_PACKAGE_REVIEW_FREEZE.md`.

This contract specifies the only future rendered control proof currently selected for moving the raw mixed `/review/layer3` UI past approved result-review authority. It is not an implementation and admits no runtime behavior by itself.

## Contract Scope

Selected mode: `raw_mixed_rendered_package_review_preview_commit_submit`.

The future implementation may only drive existing rendered operator controls for:

- `POST /api/v1/layer3/package/review/preview`
- `POST /api/v1/layer3/package/review/commit`
- `POST /api/v1/layer3/package/review/submit`

It must reuse the existing backend contracts:

- request DTO `Layer3PackageReviewPreviewRequest`
- request DTO `Layer3PackageConstructionCommitRequest`
- request DTO `Layer3PackageReviewSubmitRequest`
- response schema `Layer3PackageReviewPreviewResponse`
- response schema `Layer3PackageConstructionCommitResponse`
- response schema `Layer3PackageReviewSubmitResponse`

It must not introduce a new route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, connector dispatch path, provider URL path, RAG/vector path, hidden LLM path, full mockup path, or auth/security behavior.

## Package Preview Request

The rendered package-preview request must be assembled from server-backed state:

- `client_request_id`: new browser-generated request id for this operator action;
- `session_id`: current server-created Layer 3 session id;
- `analysis_plan_id`: id returned by plan approval for the current session;
- `pass_run_id`: selected pass run returned by execution selection and started by execution start;
- `preview_id`: current approved plan preview id;
- `preview_hash`: current approved plan preview hash;
- `result_review_record_ref`: server-returned ref from an approved selected-pass result review;
- `analysis_run_id`: optional id returned by execution start or result/status authority.

The browser must not include or infer deferred fields: `package`, `package_review_decision`, `create_package`, `package_variant`, `output_package_id`, `reconciliation_record_id`, `handoff`, `export`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, `schema_migration`, `runtime_db_write`, `artifact_manifest`, `aps_handoff`, `edited_findings`, or `rewrite_output`.

Expected `Layer3PackageReviewPreviewResponse` fields that the UI may consume:

- `schema_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_identity`
- `package_review_preview_hash`
- `analysis_run_id`
- `result_status_available`
- `result_review_state`
- `result_review_record_ref`
- `package_review_preview_enabled`
- `package_commit_enabled`
- `package_review_enabled`
- `package_review_submit_enabled`
- `candidate_package_kinds`
- `package_owner_compatibility`
- `blocked_reasons`
- `downstream_unavailable`
- `next_state`
- `output_metadata_summary`
- optional trace, pass, source, and output payload summary fields
- `authority_rail`

## Package Construction Request

The rendered package-construction request must be assembled from server-backed preview state:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `result_review_record_ref`
- `package_review_preview_hash`
- `expected_package_kinds`
- optional `analysis_run_id`

The browser must not include or infer deferred fields: `package_review_decision`, `submit_package_review`, `approve_package`, `reject_package`, `handoff`, `export`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, `schema_migration`, `runtime_db_write`, `artifact_manifest`, `analysis_artifact`, `aps_handoff`, `edited_findings`, `rewrite_output`, `package_payload`, or `package_variant_content`.

Expected `Layer3PackageConstructionCommitResponse` fields that the UI may consume:

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
- `output_packages`
- `output_package_ids`
- `package_kinds`
- `payload_refs`
- `payload_hashes`
- source and pass summary fields
- `package_commit_enabled`
- `package_review_submit_enabled`
- `handoff_enabled`
- `downstream_unavailable`
- `next_allowed_actions`
- `next_state`
- `authority_rail`

## Package Review Submit Request

The rendered package-review submit request must be assembled from server-backed construction state:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `result_review_record_ref`
- `package_review_preview_hash`
- `reconciliation_record_id`
- `output_package_ids`
- `payload_refs`
- `payload_hashes`
- `operator_decision`
- `decision_notes`
- `expected_package_kinds`
- optional `construction_basis_hash`
- optional `analysis_run_id` when the server-authoritative package path admits it

The browser must not include or infer deferred fields: `handoff`, `export`, `aps_handoff`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `edited_findings`, `result_review_amendment`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, `schema_migration`, `runtime_db_write`, `artifact_manifest`, or `analysis_artifact`.

Expected `Layer3PackageReviewSubmitResponse` fields that the UI may consume:

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
- `operator_decision`
- `decision_notes`
- `package_review_state`
- `submit_record_ref`
- `package_review_submit_enabled`
- `handoff_enabled`
- `export_enabled`
- `downstream_unavailable`
- `next_state`
- `authority_rail`

The response is authoritative for recorded package-review state. Browser state may display the response, but there must be no frontend-only durable authority.

## Rendered State Model

The future UI proof must use these phases:

- `not_ready`: no approved selected-pass result-review authority for the current session;
- `approved_result_review_ready`: `recordedApprovedResultReview()` is true for the current selected pass;
- `preview_ready`: `#package-review-preview-inspect` is enabled by server-backed state;
- `preview_loaded`: preview response supplies `package_review_preview_hash`;
- `construction_ready`: preview response supplies `package_review_preview_enabled: true` and `package_commit_enabled: true`;
- `constructed`: construction response supplies `reconciliation_record_id`, output package ids, package kinds, payload refs, and payload hashes;
- `submit_ready`: construction/session state reports `package_review_submit_enabled: true`;
- `notes_required`: a non-approved package decision is selected without notes;
- `submitting`: request to `/package/review/submit` is pending;
- `submitted`: response supplies `package_review_state` and `submit_record_ref`;
- `blocked`: server error, stale preview, missing session, missing plan, missing selected pass run, missing result/status authority, missing approved result review, missing preview hash, missing reconciliation id, missing package ids/refs/hashes, cancellation/recovery/rerun state, forbidden field, source expansion, package mutation, or unsupported downstream scope.

The UI must preserve existing disabled states for handoff/export, APS dispatch, and external export/download controls unless a separate later freeze admits that next downstream path. An error in package review must not unlock downstream controls.

## Selector and Layout Contract

Future proof must use stable existing selectors:

- `#package-review-preview-inspect`
- `#package-construction-commit`
- `#package-review-submit-decision`
- `#package-review-submit-notes`
- `#package-review-submit`
- `#package-review-preview-panel`

The controls must remain keyboard focusable, visibly labeled, and readable in the existing package-review workband. They must not overlap result-review controls, handoff controls, APS dispatch controls, external export/download controls, step chips, or mockup sections across desktop and mobile viewports.

## Theme Contract

The proof must inherit the existing Layer 3 theme system:

- shared `light`;
- shared `dark`;
- Layer 3 `workbench`;
- existing `system` resolution;
- no change to `claude` prototype routing.

The implementation must not create a new theme family or alter existing theme preference storage semantics. It must prove visible focus, disabled contrast, ready state, commit state, notes-required state, submitting state, submitted state, blocked/error state, and text fit in `light`, `dark`, and `workbench` where practical.

## Browser Proof Contract

The future browser proof must:

- drive raw mixed source materialization through rendered controls or approved API setup before opening `/review/layer3`;
- use only returned source IDs after materialization/seed setup;
- drive rendered preflight, source preview, material preview, Gate B, Gate C, plan preview, and plan approval;
- drive rendered execution selection and execution start through existing controls from doc `162`;
- inspect rendered result/status;
- submit rendered result review as `approved`;
- inspect package review preview through `#package-review-preview-inspect`;
- commit package construction through `#package-construction-commit`;
- submit package review through `#package-review-submit`;
- assert all package route requests contain only admitted fields;
- assert no handoff/export, APS dispatch, external export/download, provider URL, connector dispatch, RAG/vector, upload, directory, hidden LLM, mockup, auth/security, package mutation, replacement, or supersession behavior appears;
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
- broad package mutation or reconstruction;
- package replacement, supersession, amendment, or payload rewrite;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

## Required Validation for Future Implementation

At minimum, the future implementation must run:

- `python .\tools\l3-progress-check.py`
- `python -m pytest .\backend\tests\test_layer3_page.py -q`
- a focused Playwright test proving rendered raw mixed package preview, construction commit, and package review submit;
- the same focused Playwright test in headed Chromium;
- `npx playwright test e2e/layer3-workbench.spec.js` if feasible;
- `git diff --check`

The future pass should stop at package-review submitted state unless a separate freeze admits handoff/export prepare for the raw mixed rendered path.

## Acceptance Criteria

This contract is accepted only when:

- this file exists and names `Layer3PackageReviewPreviewRequest`, `Layer3PackageConstructionCommitRequest`, and `Layer3PackageReviewSubmitRequest`;
- it names `Layer3PackageReviewPreviewResponse`, `Layer3PackageConstructionCommitResponse`, and `Layer3PackageReviewSubmitResponse`;
- it names `POST /api/v1/layer3/package/review/preview`, `POST /api/v1/layer3/package/review/commit`, and `POST /api/v1/layer3/package/review/submit`;
- it records exact admitted request fields and deferred forbidden fields;
- it records the `light`, `dark`, and `workbench` theme proof obligation;
- progress/proof manifests, progress board, and `tools/l3-progress-check.py` reference it;
- `python .\tools\l3-progress-check.py` passes.
