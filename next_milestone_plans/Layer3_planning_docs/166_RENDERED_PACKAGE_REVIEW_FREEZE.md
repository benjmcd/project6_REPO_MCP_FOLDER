# Rendered Package Review Freeze

Status: planning/control freeze only for `raw_mixed_rendered_package_review_preview_commit_submit`.

This document selects the next rendered downstream implementation-entry posture after `165_RENDERED_RESULT_REVIEW_PROOF.md`. It admits no runtime behavior by itself and does not change routes, DTOs, services, models, migrations, source handling, package runtime behavior, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or current rendered UI controls.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current live upstream proof: `165_RENDERED_RESULT_REVIEW_PROOF.md`
- selected rendered package-review mode: `raw_mixed_rendered_package_review_preview_commit_submit`
- existing package preview route to reuse later: `POST /api/v1/layer3/package/review/preview`
- existing package commit route to reuse later: `POST /api/v1/layer3/package/review/commit`
- existing package submit route to reuse later: `POST /api/v1/layer3/package/review/submit`
- existing request DTOs: `Layer3PackageReviewPreviewRequest`, `Layer3PackageConstructionCommitRequest`, and `Layer3PackageReviewSubmitRequest`
- existing response schemas: `Layer3PackageReviewPreviewResponse`, `Layer3PackageConstructionCommitResponse`, and `Layer3PackageReviewSubmitResponse`
- existing rendered controls: `#package-review-preview-inspect`, `#package-construction-commit`, `#package-review-submit-decision`, `#package-review-submit-notes`, and `#package-review-submit`
- existing rendered panel: `#package-review-preview-panel`
- existing UI shell: `backend/app/review_ui/static/layer3.html`
- existing UI runtime: `backend/app/review_ui/static/layer3.js`
- existing raw mixed browser proof file: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this planning document.

## Selected Future Boundary

The next implementation-eligible UI pass is exactly:

`raw_mixed_rendered_package_review_preview_commit_submit`

That pass may drive the already-rendered package preview, package construction commit, and package review submit controls only after the raw mixed rendered path has recorded an `approved` result review. It must reuse the existing backend package-review routes and existing UI controls. It must not add a route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, rendered control, or downstream handoff/export behavior unless a repo-confirmed blocker is reported first.

The future pass may add or adjust only focused Playwright proof code if current controls are sufficient. If the rendered package controls cannot consume the raw mixed approved result-review authority without production or UI changes, the pass must stop and report the exact blocker before patching.

## Exact Future Controls

The future implementation should use the existing controls:

- `#package-review-preview-inspect`: posts package-preview readiness inspection to `POST /api/v1/layer3/package/review/preview`.
- `#package-construction-commit`: posts package construction to `POST /api/v1/layer3/package/review/commit`.
- `#package-review-submit-decision`: selects one admitted package-review decision.
- `#package-review-submit-notes`: records optional notes for `approved` and required notes for non-approved decisions.
- `#package-review-submit`: posts the package-review decision to `POST /api/v1/layer3/package/review/submit`.
- `#package-review-preview-panel`: displays server-returned preview, construction, and submit authority.

The future proof must use an `approved` result-review decision before entering this package-review path. The current raw mixed rendered result-review proof intentionally uses `changes_requested` and therefore proves that package controls remain disabled, not that package review is live for raw mixed UI.

No manifest picker, upload control, directory picker, source adapter selector, web connector picker, RAG/vector control, provider URL control, connector dispatch control, destination selector, hidden LLM control, auth/security control, full mockup control, package mutation control, replacement-package control, or package supersession control may be added by this pass.

## Server Authority Gates

The package-review controls may be driven only when all of the following are true in current rendered state and server-returned authority:

- a current `session_id` exists from normal preflight/source/material/Gate B progression;
- Gate C typing has been committed for that session;
- a plan preview and plan approval exist for the current preview identity;
- execution selection has returned server-selected pass-run authority;
- execution start has started exactly one selected pass run;
- result/status inspection has returned `result_status_available: true`;
- result review has been recorded as `execution_result_review_approved` with `operator_decision: approved`;
- package preview returns `package_review_preview_enabled: true`, `package_commit_enabled: true`, and a server `package_review_preview_hash`;
- package construction returns a server `reconciliation_record_id`, exactly the admitted output package ids, package kinds, payload refs, and payload hashes;
- package review submit returns `package_review_state` and `submit_record_ref`;
- no stale-preview, recovery, cancellation, rerun, handoff, export, source-expansion, replacement, supersession, or mutation blocker is active.

The browser must not manufacture package-review preview hashes, reconciliation IDs, package IDs, package kinds, payload refs, payload hashes, construction basis hashes, submit refs, handoff authority, export authority, connector authority, provider URLs, or durable package-review authority.

## Exact Request Fields

The future `POST /api/v1/layer3/package/review/preview` request must include only admitted fields:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- `result_review_record_ref`
- optional `analysis_run_id`

The future `POST /api/v1/layer3/package/review/commit` request must include only admitted fields:

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

The future `POST /api/v1/layer3/package/review/submit` request must include only admitted fields:

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

The UI must not send known non-admitted package fields such as `handoff`, `export`, `aps_handoff`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `edited_findings`, `result_review_amendment`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, `schema_migration`, `runtime_db_write`, `artifact_manifest`, `analysis_artifact`, package replacement fields, or package supersession fields.

## State Transitions

The future UI proof must preserve this order:

1. Rendered raw mixed materialization creates admitted source authority.
2. Rendered preflight/source preview/material preview run normally.
3. Rendered Gate B and Gate C run normally.
4. Rendered plan preview and plan approval run normally.
5. Rendered execution selection and execution start run through the live controls from doc `162`.
6. Rendered result/status inspection returns selected-pass result/status authority.
7. Rendered result-review submit records exactly one `approved` result review.
8. Rendered package review preview inspects server package readiness.
9. Rendered package construction commit creates only the admitted package set through the existing route.
10. Rendered package review submit records exactly one package-review decision.
11. Handoff/export prepare, APS dispatch, external export/download prepare, external export/download deliver, package replacement, package supersession, and package mutation remain outside this pass.

Package preview must not create rows or files. Package commit may create only the package rows and payload files admitted by the existing backend package construction contract. Package review submit must not mutate package rows, rewrite payload refs or hashes, create additional package rows or files, start handoff/export, dispatch APS handoff, prepare external export/download, invoke connectors, write destinations, create provider URLs, create RAG/vector state, create source rows, create model/migration state, or create browser-only durable authority.

## Theme and Browser Requirements

The future proof must preserve the current theme and browser posture:

- `light` theme;
- `dark` theme;
- `workbench` theme;
- existing theme preference persistence behavior;
- headed Chromium and headless Chromium, run sequentially on fixed port `8031` unless a separate freeze changes the harness.

The visual proof must cover preview-ready, preview-loaded, commit-ready, constructed, notes-required, submitting, submitted, and blocked/error states where practical. Text must fit, focus must remain visible, controls must not overlap existing result, handoff, APS dispatch, external export/download, or mockup sections, and no frontend-only durable authority may be introduced.

## Negative Invariants

The future implementation must keep all of the following absent:

- production backend route, DTO, service, model, or migration changes;
- new rendered controls unless a blocker is reported first;
- source-family expansion beyond `dataset_version` and `aps_content_document`;
- source adapter registry behavior;
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
- browser/frontend-only durable authority.

## Required Future Proof

The future implementation pass must include:

- API request assertions proving `/package/review/preview`, `/package/review/commit`, and `/package/review/submit` receive only the admitted fields above;
- rendered state assertions proving package controls are unavailable before approved result-review authority;
- rendered state assertions proving preview, construction, and submit state after each package phase;
- server response assertions for package preview hash, reconciliation ID, package IDs, package kinds, payload refs, payload hashes, package-review state, and submit ref;
- no-side-effect assertions for source expansion, package mutation/reconstruction beyond admitted construction, connector/provider/RAG/mockup/auth behavior;
- rendered assertions proving handoff/export, APS dispatch, and external export/download remain out of scope after package review submit unless a separate freeze admits that next downstream slice;
- a narrow Playwright test over the raw mixed rendered path through package review submit;
- sequential headed and headless Chromium proof;
- theme checks covering `light`, `dark`, and `workbench`.

## Stop Conditions

Stop before implementation if any of these are true:

- the current API request/response contracts differ from this freeze;
- the existing rendered package controls cannot consume approved raw mixed result-review authority;
- the future test would need hidden API calls after rendered approved result review to substitute for missing rendered controls;
- the UI would need backend route, DTO, model, migration, source, provider, connector, package mutation, RAG/vector, mockup, hidden LLM, or auth/security expansion;
- package construction cannot be driven without broad package mutation/reconstruction semantics;
- browser proof would require parallel headed/headless runs on fixed port `8031`.

## Acceptance Criteria

This freeze is accepted only when:

- this file exists and names `raw_mixed_rendered_package_review_preview_commit_submit`;
- `167_RENDERED_PACKAGE_REVIEW_CONTRACT.md` records the exact route/request/response/UI-state contract;
- progress/proof manifests and the progress board reference this freeze as planning/control only;
- `tools/l3-progress-check.py` guards this file and the companion contract;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` passes.
