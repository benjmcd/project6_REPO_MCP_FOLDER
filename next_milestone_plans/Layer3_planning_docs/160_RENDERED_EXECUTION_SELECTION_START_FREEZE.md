# Rendered Execution Selection/Start Freeze

Status: planning/control freeze only for `raw_mixed_rendered_execution_selection_start_controls`.

This document selects the next implementation-entry posture after `159_RAW_MIXED_RENDERED_DOWNSTREAM_BLOCKER.md`. It admits no runtime behavior by itself and does not change routes, DTOs, services, models, migrations, source handling, package behavior, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or current rendered UI controls.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current-main blocker: `159_RAW_MIXED_RENDERED_DOWNSTREAM_BLOCKER.md`
- selected rendered execution mode: `raw_mixed_rendered_execution_selection_start_controls`
- upstream rendered mode: `raw_mixed_server_owned_manifest_ref_ui_entry`
- existing source/material route reused before this point: `POST /api/v1/layer3/source/mixed-corpus/materialize`
- existing execution routes to reuse later: `POST /api/v1/layer3/execution/select` and `POST /api/v1/layer3/execution/start`
- existing UI shell: `backend/app/review_ui/static/layer3.html`
- existing UI runtime: `backend/app/review_ui/static/layer3.js`
- existing browser proof file: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this planning document.

## Selected Future Boundary

The next implementation-eligible UI pass is exactly:

`raw_mixed_rendered_execution_selection_start_controls`

That pass may add rendered controls that let an operator continue the already-rendered raw mixed path from plan approval into execution selection and execution start. The controls must only call existing backend routes and must use server-authoritative state from the current session.

The future pass may add no backend route, DTO, service, model, or migration. It may add no new source class, source adapter registry, raw ingestion behavior, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, package mutation/reconstruction, provider/public URL generation, real connector/destination dispatch, hidden LLM planning, full mockup activation, auth/security behavior, or frontend-only durable authority.

## Exact Future Controls

The future implementation may add only these rendered controls, or equivalent stable selectors documented before code:

- `#execution-select`: posts to `POST /api/v1/layer3/execution/select`.
- `#execution-start`: posts to `POST /api/v1/layer3/execution/start`.
- `#execution-selection-start-panel`: displays selected pass-run identity, execution-start state, response errors, and next available server-backed actions.

The controls must live in the existing execution/result workband or an adjacent un-nested section that preserves the current workbench layout. They must not create a standalone raw-ingestion workflow, manifest picker expansion, upload control, directory picker, connector picker, provider URL control, RAG/vector control, package mutation control, or mockup activation control.

## Server Authority Gates

The execution-selection control must be enabled only when all of the following are true in current browser memory and server-returned state:

- a current `session_id` exists from normal preflight/source/material/Gate B progression;
- Gate C typing has been committed for that session;
- a plan preview exists with `preview_id` and `preview_hash`;
- plan approval succeeded and returned `analysis_plan_id`;
- no plan revision, cancellation, or stale-preview error is active;
- `State.sessionSummary?.execution_selection?.selected` is not already true unless the UI is displaying an existing server-selected pass-run state.

The execution-start control must be enabled only after execution selection succeeds and returns exactly the server-selected `pass_run_ids` to use. It must not manufacture a pass-run id in the browser. It must not infer selection from a visible plan card alone.

## Exact Request Fields

The future `POST /api/v1/layer3/execution/select` request must include only admitted fields:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `preview_id`
- `preview_hash`
- optional `operator_reason`

The future `POST /api/v1/layer3/execution/start` request must include only admitted fields:

- `client_request_id`
- `session_id`
- `analysis_plan_id`
- `pass_run_id`
- `preview_id`
- `preview_hash`
- optional `execution_mode` with only `synchronous_single_pass`
- optional `operator_reason`

The UI must not send known non-admitted execution fields such as `execute`, `execution`, `run`, `run_analysis`, `start_execution`, `analysis_run_id`, `analysis_run_ids`, `result_review`, `results`, `package`, `package_review`, `handoff`, `artifact_manifest`, `local_upload`, `local_directory`, `rag_plan`, `vector_plan`, `qualitative_plan`, `hybrid_plan`, `run_all`, `batch`, `approved_plan_supersession`, `schema_migration`, `source_expansion`, or `schema_widening`.

## State Transitions

The future UI must preserve this order:

1. Rendered raw mixed materialization or API setup creates admitted source authority.
2. Rendered preflight/source preview/material preview run normally.
3. Rendered Gate B and Gate C run normally.
4. Rendered plan preview and plan approval run normally.
5. Rendered execution selection creates selected `L3PassRun` state through the existing route.
6. Rendered execution start starts only one selected pass run through the existing route.
7. Existing result-status controls become eligible only from server session-summary and execution-start response authority.

Execution selection must not start execution. Execution start must not submit result review, package review, handoff/export, APS handoff, external export/download prepare, or external export/download deliver.

## Theme and Browser Requirements

The future implementation must prove the controls in the rendered `/review/layer3` UI across:

- `light` theme;
- `dark` theme;
- `workbench` theme;
- existing theme preference persistence behavior;
- headed Chromium and headless Chromium.

Because `playwright.config.js` uses fixed `SERVER_PORT = 8031`, `fullyParallel: false`, and `workers: 1`, headed and headless raw mixed checks must run sequentially unless the implementation first introduces separate ports/state with a separate freeze.

The visual proof must cover disabled, loading, success, blocked, and error states. Text must fit, focus must remain visible, controls must not overlap existing result/package/handoff sections, and no frontend-only durable authority may be introduced. Existing local/session storage can remain only for current theme, session recovery, and Gate B draft behavior; it must not become execution authority.

## Negative Invariants

The future implementation must keep all of the following absent:

- production backend route, DTO, service, model, or migration changes;
- source-family expansion beyond `dataset_version` and `aps_content_document`;
- source adapter registry behavior;
- local upload or local-directory ingestion;
- arbitrary local path input;
- web connector retrieval;
- RAG/vector retrieval or index creation;
- provider/public URL or signed public URL generation;
- real connector or destination dispatch;
- broad package mutation or reconstruction;
- package payload rewrite outside already admitted package commit behavior;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- browser/frontend-only durable authority.

## Required Future Proof

The future implementation pass must include:

- API request assertions proving `/execution/select` and `/execution/start` receive only the admitted fields above;
- rendered state assertions proving result/package/handoff controls remain disabled before execution selection/start;
- rendered state assertions proving result status becomes available only after server-authoritative execution start;
- no-side-effect assertions for source expansion, package mutation, connector/provider/RAG/mockup/auth behavior;
- a narrow Playwright test over the raw mixed rendered path through execution selection/start;
- sequential headed and headless Chromium proof;
- theme checks covering `light`, `dark`, and `workbench`.

## Stop Conditions

Stop before implementation if any of these are true:

- the current API request/response contract differs from this freeze;
- the existing session summary cannot expose enough server-authoritative execution selection/start state;
- the future test would need hidden API calls after rendered plan approval to substitute for missing rendered controls;
- the UI would need backend route, DTO, model, migration, source, provider, connector, package, RAG/vector, mockup, hidden LLM, or auth/security expansion;
- browser proof would require parallel headed/headless runs on fixed port `8031`.

## Acceptance Criteria

This freeze is accepted only when:

- this file exists and names `raw_mixed_rendered_execution_selection_start_controls`;
- `161_RENDERED_EXECUTION_SELECTION_START_CONTRACT.md` records the exact route/request/response/UI-state contract;
- progress/proof manifests and the progress board reference this freeze as planning/control only;
- `tools/l3-progress-check.py` guards this file and the companion contract;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` passes.
