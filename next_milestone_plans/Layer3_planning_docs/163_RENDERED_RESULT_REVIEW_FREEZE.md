# Rendered Result Review Freeze

Status: planning/control freeze only for `raw_mixed_rendered_result_review_submit`.

This document selects the next implementation-entry posture after `162_RENDERED_EXECUTION_SELECTION_START_RUNTIME.md`. It admits no runtime behavior by itself and does not change routes, DTOs, services, models, migrations, source handling, package behavior, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or current rendered UI controls.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current live upstream runtime: `162_RENDERED_EXECUTION_SELECTION_START_RUNTIME.md`
- selected rendered result-review mode: `raw_mixed_rendered_result_review_submit`
- existing result-review route to reuse later: `POST /api/v1/layer3/execution/result/review`
- existing request DTO: `Layer3ExecutionResultReviewRequest`
- existing response schema: `Layer3ExecutionResultReviewResponse`
- existing rendered controls: `#result-review-decision`, `#result-review-notes`, and `#result-review-submit`
- existing rendered stop-before-package control: `#package-review-preview-inspect`
- existing UI shell: `backend/app/review_ui/static/layer3.html`
- existing UI runtime: `backend/app/review_ui/static/layer3.js`
- existing raw mixed browser proof file: `e2e/layer3-workbench.spec.js`
- existing selected-pass result-review browser proof file: `e2e/layer3-flow.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this planning document.

## Selected Future Boundary

The next implementation-eligible UI pass is exactly:

`raw_mixed_rendered_result_review_submit`

That pass may drive the already-rendered result-review controls after the raw mixed rendered path has reached server-authoritative execution result/status readiness. It must reuse the existing backend result-review route and existing UI controls. It must not add a new result-review route, DTO, service, model, migration, or rendered control unless a repo-confirmed blocker is reported first.

The future pass may add or adjust only focused Playwright proof code if current controls are sufficient. If the rendered result-review controls cannot consume the raw mixed execution result/status authority without production or UI changes, the pass must stop and report the exact blocker before patching.

## Exact Future Controls

The future implementation should use the existing controls:

- `#result-review-decision`: selects one admitted operator decision.
- `#result-review-notes`: records optional notes for `approved` and required notes for `changes_requested`, `rejected`, or `blocked`.
- `#result-review-submit`: posts to `POST /api/v1/layer3/execution/result/review`.

The first proof should prefer `changes_requested` with nonempty notes because the existing `e2e/layer3-flow.spec.js` result-review proof already exercises the required-notes branch. If the raw mixed associated-cohort result-review path requires a different admitted decision, the future pass must cite the live API/UI behavior and keep the request allowlist unchanged.

No manifest picker, upload control, directory picker, source adapter selector, web connector picker, RAG/vector control, package mutation control, provider URL control, connector dispatch control, destination selector, hidden LLM control, auth/security control, or full mockup control may be added by this pass.

## Server Authority Gates

The result-review submit control may be driven only when all of the following are true in current rendered state and server-returned authority:

- a current `session_id` exists from normal preflight/source/material/Gate B progression;
- Gate C typing has been committed for that session;
- a plan preview and plan approval exist for the current preview identity;
- execution selection has returned server-selected pass-run authority;
- execution start has started exactly one selected pass run;
- result/status inspection has returned `result_status_available: true`;
- the result-review panel reports `cohort_result_review_ui_review_ready` for the raw mixed associated-cohort path, or a directly equivalent server-backed ready state;
- no result review has already been recorded for the selected pass run;
- no stale-preview, recovery, cancellation, rerun, package, handoff, export, or source-expansion blocker is active.

The browser must not manufacture pass-run IDs, analysis-run IDs, review refs, package authority, handoff authority, connector authority, provider URLs, or durable result-review authority.

## Exact Request Fields

The future `POST /api/v1/layer3/execution/result/review` request must include only admitted fields:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `operator_decision`
- optional `review_notes`
- optional `reviewed_output_items`
- optional `analysis_run_id`

The UI must not send known non-admitted result-review fields such as `package`, `package_review`, `handoff`, `export`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, `schema_migration`, `runtime_db_write`, `artifact_manifest`, `package_variant`, `aps_handoff`, `edited_findings`, or `rewrite_output`.

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

## State Transitions

The future UI proof must preserve this order:

1. Rendered raw mixed materialization creates admitted source authority.
2. Rendered preflight/source preview/material preview run normally.
3. Rendered Gate B and Gate C run normally.
4. Rendered plan preview and plan approval run normally.
5. Rendered execution selection and execution start run through the live controls from doc `162`.
6. Rendered result/status inspection returns selected-pass result/status authority.
7. Rendered result-review submit records exactly one operator review through the existing route.
8. Package preview, package commit, package submit, handoff/export prepare, APS dispatch, external export/download prepare, and external export/download deliver remain outside this pass.

Result review must not create package rows, package artifacts, handoff/export state, APS dispatch state, external export/download readiness, connector runs, destination writes, provider URLs, RAG/vector state, source rows, model/migration state, or browser-only durable authority.

## Theme and Browser Requirements

The future proof must preserve the current theme and browser posture:

- `light` theme;
- `dark` theme;
- `workbench` theme;
- existing theme preference persistence behavior;
- headed Chromium and headless Chromium, run sequentially on fixed port `8031` unless a separate freeze changes the harness.

The visual proof must cover ready, disabled, notes-required, submitting, recorded, and blocked/error states where practical. Text must fit, focus must remain visible, controls must not overlap existing package/handoff/export sections, and no frontend-only durable authority may be introduced.

## Negative Invariants

The future implementation must keep all of the following absent:

- production backend route, DTO, service, model, or migration changes;
- new rendered result-review controls unless a blocker is reported first;
- source-family expansion beyond `dataset_version` and `aps_content_document`;
- source adapter registry behavior;
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
- browser/frontend-only durable authority.

## Required Future Proof

The future implementation pass must include:

- API request assertions proving `/execution/result/review` receives only the admitted fields above;
- rendered state assertions proving the result-review submit is unavailable before result/status authority;
- rendered state assertions proving one recorded result review after submit;
- rendered state assertions proving package/handoff/export remain out of scope after result-review submit unless existing backend state explicitly says otherwise and a separate freeze admits that step;
- no-side-effect assertions for source expansion, package mutation, connector/provider/RAG/mockup/auth behavior;
- a narrow Playwright test over the raw mixed rendered path through result-review submit;
- sequential headed and headless Chromium proof;
- theme checks covering `light`, `dark`, and `workbench`.

## Stop Conditions

Stop before implementation if any of these are true:

- the current API request/response contract differs from this freeze;
- the existing rendered result-review controls cannot consume raw mixed result/status authority;
- the future test would need hidden API calls after rendered result/status inspection to substitute for missing rendered controls;
- the UI would need backend route, DTO, model, migration, source, provider, connector, package, RAG/vector, mockup, hidden LLM, or auth/security expansion;
- browser proof would require parallel headed/headless runs on fixed port `8031`.

## Acceptance Criteria

This freeze is accepted only when:

- this file exists and names `raw_mixed_rendered_result_review_submit`;
- `164_RENDERED_RESULT_REVIEW_CONTRACT.md` records the exact route/request/response/UI-state contract;
- progress/proof manifests and the progress board reference this freeze as planning/control only;
- `tools/l3-progress-check.py` guards this file and the companion contract;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` passes.
