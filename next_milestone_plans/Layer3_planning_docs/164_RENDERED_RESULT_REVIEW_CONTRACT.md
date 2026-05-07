# Rendered Result Review Contract

Status: planning/control UI and API contract for `163_RENDERED_RESULT_REVIEW_FREEZE.md`.

This contract specifies the only future rendered control proof currently selected for moving the raw mixed `/review/layer3` UI past execution result/status readiness. It is not an implementation and admits no runtime behavior by itself.

## Contract Scope

Selected mode: `raw_mixed_rendered_result_review_submit`.

The future implementation may only drive existing rendered operator controls for:

- `POST /api/v1/layer3/execution/result/review`

It must reuse the existing backend contracts:

- request DTO `Layer3ExecutionResultReviewRequest`
- response schema `Layer3ExecutionResultReviewResponse`

It must not introduce a new route, DTO, service, model, migration, source adapter, ingestion path, package lifecycle, connector dispatch path, provider URL path, RAG/vector path, hidden LLM path, full mockup path, or auth/security behavior.

## Result Review Request

The rendered result-review request must be assembled from server-backed state:

- `client_request_id`: new browser-generated request id for this operator action;
- `session_id`: current server-created Layer 3 session id;
- `analysis_plan_id`: id returned by plan approval for the current session;
- `pass_run_id`: selected pass run returned by execution selection and started by execution start;
- `preview_id`: current approved plan preview id;
- `preview_hash`: current approved plan preview hash;
- `operator_decision`: one admitted decision from the existing `#result-review-decision` control;
- `review_notes`: optional for `approved`, required for `changes_requested`, `rejected`, or `blocked`;
- `reviewed_output_items`: optional reviewed-output list only if existing UI/runtime authority supplies it;
- `analysis_run_id`: optional id returned by execution start or result/status authority.

The browser must not include or infer deferred fields: `package`, `package_review`, `handoff`, `export`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, `schema_migration`, `runtime_db_write`, `artifact_manifest`, `package_variant`, `aps_handoff`, `edited_findings`, or `rewrite_output`.

Expected response fields that the UI may consume:

- `schema_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_identity`
- `analysis_run_id`
- `result_status_available`
- `result_review_enabled`
- `review_state`
- `operator_decision`
- `review_record_ref`
- `trace_summary`
- `reviewed_output_items`
- `unresolved_trace_count`
- `package_review_enabled`
- `handoff_enabled`
- `downstream_unavailable`
- `review_notes_recorded`
- `engine_family`
- optional `pass_type`, `pass_scope`, `selected_method_name`, `source_gate`, `source_dataset_version_ids`, and `cohort_shape`

The response is authoritative for recorded result-review state. Browser state may display the response, but there must be no frontend-only durable authority.

## Rendered State Model

The future UI proof must use these phases:

- `not_ready`: no selected pass-run result/status authority for the current session;
- `ready_to_review`: `cohort_result_review_ui_review_ready` or an equivalent server-backed ready state is displayed;
- `notes_required`: a non-approved decision is selected without notes;
- `submitting`: request to `/execution/result/review` is pending;
- `recorded`: response supplies `review_state`, `operator_decision`, and `review_record_ref`;
- `blocked`: server error, stale preview, missing session, missing plan, missing selected pass run, missing result/status authority, already-recorded review, cancellation/recovery/rerun state, forbidden field, or unsupported downstream scope.

The UI must preserve existing disabled states for package/handoff/export controls unless a separate later freeze admits that next downstream path. An error in result review must not unlock downstream controls.

## Selector and Layout Contract

Future proof must use stable existing selectors:

- `#result-review-decision`
- `#result-review-notes`
- `#result-review-submit`
- `#result-review-panel`
- `#package-review-preview-inspect`

The controls must remain keyboard focusable, visibly labeled, and readable in the existing result-review workband. They must not overlap step chips, execution controls, package controls, handoff controls, or external export/download controls across desktop and mobile viewports.

## Theme Contract

The proof must inherit the existing Layer 3 theme system:

- shared `light`;
- shared `dark`;
- Layer 3 `workbench`;
- existing `system` resolution;
- no change to `claude` prototype routing.

The implementation must not create a new theme family or alter existing theme preference storage semantics. It must prove visible focus, disabled contrast, ready state, notes-required state, submitting state, recorded state, blocked/error state, and text fit in `light`, `dark`, and `workbench` where practical.

## Browser Proof Contract

The future browser proof must:

- drive raw mixed source materialization through rendered controls or approved API setup before opening `/review/layer3`;
- use only returned source IDs after materialization/seed setup;
- drive rendered preflight, source preview, material preview, Gate B, Gate C, plan preview, and plan approval;
- drive rendered execution selection and execution start through existing controls from doc `162`;
- inspect rendered result/status;
- submit rendered result review through `#result-review-submit`;
- assert `/execution/result/review` request contains only admitted fields;
- assert no package, handoff, APS dispatch, external export/download, provider URL, connector dispatch, RAG/vector, upload, directory, hidden LLM, mockup, or auth/security behavior appears;
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
- package payload rewrite or package row creation from this pass;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

## Required Validation for Future Implementation

At minimum, the future implementation must run:

- `python .\tools\l3-progress-check.py`
- `python -m pytest .\backend\tests\test_layer3_page.py -q`
- a focused Playwright test proving rendered raw mixed result-review submit;
- the same focused Playwright test in headed Chromium;
- `npx playwright test e2e/layer3-workbench.spec.js` if feasible;
- `git diff --check`

The future pass should stop at result-review recorded state unless a separate freeze admits package review preview/commit/submit for the raw mixed rendered path.

## Acceptance Criteria

This contract is accepted only when:

- this file exists and names `Layer3ExecutionResultReviewRequest` and `Layer3ExecutionResultReviewResponse`;
- it names `POST /api/v1/layer3/execution/result/review`;
- it records exact admitted request fields and deferred forbidden fields;
- it records the `light`, `dark`, and `workbench` theme proof obligation;
- progress/proof manifests, progress board, and `tools/l3-progress-check.py` reference it;
- `python .\tools\l3-progress-check.py` passes.
