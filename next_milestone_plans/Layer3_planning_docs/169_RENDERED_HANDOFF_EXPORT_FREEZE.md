# Rendered Handoff Export Prepare Freeze

Status: planning/control freeze only for `raw_mixed_rendered_handoff_export_prepare`.

This document selects the next rendered downstream proof boundary after `168_RENDERED_PACKAGE_REVIEW_PROOF.md`. It admits no runtime behavior by itself and does not change routes, DTOs, services, models, migrations, source handling, package behavior, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or current rendered UI controls.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current live upstream proof: `168_RENDERED_PACKAGE_REVIEW_PROOF.md`
- selected rendered handoff mode: `raw_mixed_rendered_handoff_export_prepare`
- existing handoff route to reuse later: `POST /api/v1/layer3/handoff/export/prepare`
- existing request DTO: `Layer3HandoffExportPrepareRequest`
- existing response schema: `Layer3HandoffExportPrepareResponse`
- existing rendered controls: `#handoff-export-prepare-decision`, `#handoff-export-prepare-notes`, and `#handoff-export-prepare-submit`
- existing rendered panel: `#handoff-export-prepare-panel`
- existing operation dock target: `[data-operation-target="handoff-export-band"]`
- existing UI shell: `backend/app/review_ui/static/layer3.html`
- existing UI runtime: `backend/app/review_ui/static/layer3.js`
- existing raw mixed browser proof file: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this planning document.

## Selected Future Boundary

The next implementation-eligible UI pass is exactly:

`raw_mixed_rendered_handoff_export_prepare`

That pass may drive the already-rendered handoff/export prepare controls only after the raw mixed rendered path has recorded an approved package-review submit. It must reuse the existing backend handoff/export prepare route and existing UI controls. It must not add a route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, rendered control, APS dispatch behavior, external export/download behavior, provider URL behavior, or connector/destination behavior unless a repo-confirmed blocker is reported first.

The future pass may add or adjust only focused Playwright proof code if current controls are sufficient. If the rendered handoff/export controls cannot consume the approved raw mixed package-review authority without production or UI changes, the pass must stop and report the exact blocker before patching.

## Exact Future Controls

The future implementation should use the existing controls:

- `[data-operation-target="handoff-export-band"]`: opens the existing handoff/export operation band in the workbench operation dock.
- `#handoff-export-prepare-decision`: selects one admitted handoff/export prepare decision.
- `#handoff-export-prepare-notes`: records optional notes for `authorize_prepare` and required notes for `hold`, `decline`, or `blocked`.
- `#handoff-export-prepare-submit`: posts the handoff/export prepare decision to `POST /api/v1/layer3/handoff/export/prepare`.
- `#handoff-export-prepare-panel`: displays server-returned handoff/export prepare authority.

No manifest picker, upload control, directory picker, source adapter selector, web connector picker, RAG/vector control, provider URL control, connector dispatch control, destination selector, hidden LLM control, auth/security control, full mockup control, package mutation control, replacement-package control, package supersession control, APS dispatch implementation, or external export/download implementation may be added by this pass.

## Server Authority Gates

The handoff/export prepare controls may be driven only when all of the following are true in current rendered state and server-returned authority:

- a current `session_id` exists from normal preflight/source/material/Gate B progression;
- Gate C typing has been committed for that session;
- a plan preview and plan approval exist for the current preview identity;
- execution selection has returned server-selected pass-run authority;
- execution start has started exactly one selected pass run;
- result/status inspection has returned `result_status_available: true`;
- result review has been recorded as `execution_result_review_approved` with `operator_decision: approved`;
- package preview, construction, and package-review submit have recorded an approved package-review state;
- session summary reports handoff/export prepare readiness for the approved package-review submit state;
- no stale-preview, recovery, cancellation, rerun, APS dispatch, external export/download, source-expansion, replacement, supersession, or mutation blocker is active.

The browser must not manufacture handoff/export prepare refs, package-review submit refs, reconciliation IDs, package IDs, package kinds, payload refs, payload hashes, envelope refs, APS dispatch authority, external download authority, provider URLs, connector authority, or durable handoff authority.

## Exact Request Fields

The future `POST /api/v1/layer3/handoff/export/prepare` request must include only admitted fields:

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
- `package_review_submit_record_ref`
- `package_review_state`
- `package_review_submit_schema_id`
- `handoff_target`
- `export_mode`
- `operator_decision`
- `expected_package_kinds`
- optional `decision_notes`
- optional `analysis_run_id` when the server-authoritative associated-cohort path admits it
- optional `construction_basis_hash` only for paths where current server authority requires it

The UI must not send known non-admitted fields such as `aps_handoff`, `dispatch`, `send`, `external_export`, `external_target`, `download`, `connector_run_id`, `runtime_db_write`, `analysis_artifact`, `artifact_manifest`, `create_package`, `rebuild_package`, `package_payload`, `package_variant_content`, `rewrite_output`, `edited_findings`, `result_review_amendment`, `package_review_amendment`, `rerun`, `retry`, `recover`, `cancel`, `selected_pass_ids`, `pass_run_ids`, `new_analysis_plan`, `plan_revision`, `source_expansion`, `local_upload`, `local_directory`, or `schema_migration`.

## State Transitions

The future UI proof must preserve this order:

1. Rendered raw mixed materialization creates admitted source authority.
2. Rendered preflight/source preview/material preview run normally.
3. Rendered Gate B and Gate C run normally.
4. Rendered plan preview and plan approval run normally.
5. Rendered execution selection and execution start run normally.
6. Rendered result/status inspection returns selected-pass result/status authority.
7. Rendered result-review submit records exactly one `approved` result review.
8. Rendered package preview, construction, and package-review submit record approved package-review authority.
9. Rendered handoff/export prepare records exactly one `authorize_prepare` decision for `internal_export_envelope` and `prepare_only`.
10. APS handoff dispatch, external export/download prepare, external export/download deliver, provider URL generation, connector/destination dispatch, package replacement, package supersession, and package mutation remain outside this pass.

Handoff/export prepare must not create package rows, rewrite payload refs or hashes, start APS dispatch, prepare external export/download, invoke connectors, write destinations, create provider URLs, create RAG/vector state, create source rows, create model/migration state, or create browser-only durable authority.

## Current Readiness Nuance

Current rendered workbench behavior may enable `#aps-handoff-dispatch-submit` after a successful handoff/export prepare response. This freeze does not make APS handoff dispatch part of the selected pass. The future proof may acknowledge that next-step readiness is surfaced, but it must not click the APS dispatch control or send `POST /api/v1/layer3/handoff/aps/dispatch`.

## Theme and Browser Requirements

The future proof must preserve the current theme and browser posture:

- `light` theme already covered by package-preview/result-status portions of the upstream path;
- `dark` theme already covered by package-construction/execution portions of the upstream path;
- `workbench` theme required for operation-dock navigation to `handoff-export-band`;
- existing theme preference persistence behavior;
- headed Chromium and headless Chromium, run sequentially on fixed port `8031` unless a separate freeze changes the harness.

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
- APS handoff dispatch request execution;
- external export/download prepare or deliver;
- broad package mutation or reconstruction;
- package replacement, supersession, amendment, or payload rewrite;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- browser/frontend-only durable authority.

There is no frontend-only durable authority.

## Required Future Proof

The future implementation pass must include:

- API request assertions proving `/handoff/export/prepare` receives only the admitted fields above;
- rendered state assertions proving handoff/export prepare is unavailable before approved package-review authority;
- rendered state assertions proving `handoff_export_prepared`, `prepare_record_ref`, and `handoff_export_envelope`;
- server response assertions for package-review submit ref, package ids, package kinds, payload refs, payload hashes, reconciliation id, handoff target, export mode, disabled provider/connector/external flags, and downstream unavailable values;
- no-side-effect assertions for source expansion, package mutation/reconstruction beyond admitted construction, APS dispatch request, external export/download request, connector/provider/RAG/mockup/auth behavior;
- a narrow Playwright test over the raw mixed rendered path through handoff/export prepare;
- sequential headed and headless Chromium proof;
- theme checks covering `light`, `dark`, and `workbench` across the full upstream path.

## Stop Conditions

Stop before implementation if any of these are true:

- the current API request/response contracts differ from this freeze;
- the existing rendered handoff/export controls cannot consume approved raw mixed package-review authority;
- the future test would need hidden API calls after rendered package-review submit to substitute for missing rendered controls;
- the UI would need backend route, DTO, model, migration, source, provider, connector, package mutation, RAG/vector, mockup, hidden LLM, or auth/security expansion;
- handoff/export prepare cannot be driven without APS dispatch or external export/download semantics;
- browser proof would require parallel headed/headless runs on fixed port `8031`.

## Acceptance Criteria

This freeze is accepted only when:

- this file exists and names `raw_mixed_rendered_handoff_export_prepare`;
- `170_RENDERED_HANDOFF_EXPORT_CONTRACT.md` records the exact route/request/response/UI-state contract;
- progress/proof manifests and the progress board reference this freeze as planning/control only;
- `tools/l3-progress-check.py` guards this file and the companion contract;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` passes.
