# Rendered Execution Selection/Start Runtime

Status: live bounded runtime for `raw_mixed_rendered_execution_selection_start_controls`.

This document records the implementation-entry pass selected by `160_RENDERED_EXECUTION_SELECTION_START_FREEZE.md` and `161_RENDERED_EXECUTION_SELECTION_START_CONTRACT.md`. It makes the existing rendered `/review/layer3` workbench able to continue from approved plan authority into execution selection and execution start using only existing backend contracts.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- implementation branch: `codex/l3-rendered-execution-controls`
- selected rendered execution mode: `raw_mixed_rendered_execution_selection_start_controls`
- existing execution selection route: `POST /api/v1/layer3/execution/select`
- existing execution start route: `POST /api/v1/layer3/execution/start`
- live UI shell: `backend/app/review_ui/static/layer3.html`
- live UI runtime: `backend/app/review_ui/static/layer3.js`
- page-shell proof: `backend/tests/test_layer3_page.py`
- browser proof: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this note.

## Live Boundary

The runtime adds exactly these rendered controls:

- `#execution-select`
- `#execution-start`
- `#execution-selection-start-panel`

The controls reuse only server-authoritative session, plan approval, plan preview, and selected pass-run state. `#execution-select` sends only the admitted `Layer3ExecutionSelectionRequest` fields. `#execution-start` sends only the admitted `Layer3AnalysisExecutionStartRequest` fields and uses only `synchronous_single_pass`.

The browser does not manufacture pass-run IDs, analysis-run IDs, package authority, handoff authority, connector authority, provider URLs, or durable execution authority.

There is no frontend-only durable authority.

## Expected Rendered Flow

1. Raw mixed materialization setup supplies admitted `dataset_version` and `aps_content_document` source authority.
2. Existing rendered preflight/source/material preview controls run normally.
3. Existing rendered Gate B and Gate C controls run normally.
4. Existing rendered plan preview and plan approval controls run normally.
5. `#execution-select` becomes enabled after server-backed plan approval authority.
6. `#execution-start` remains disabled until selection returns the server-selected pass run.
7. `#execution-start` starts that single selected pass run through `POST /api/v1/layer3/execution/start`.
8. Result status becomes enabled after execution start.
9. Result review, package review, handoff, APS dispatch, and external export/download controls remain outside this pass.

## Proof Surface

The focused browser proof is:

`Layer 3 workbench drives raw mixed rendered execution selection and start`

That proof verifies:

- request payload allowlists for `/execution/select` and `/execution/start`;
- only returned server IDs are used after materialization;
- plan approval still stops before execution until the operator clicks the rendered selection/start controls;
- result status becomes available only after execution start;
- result review, package, and handoff/export routes are not called;
- light, dark, and workbench theme states keep the execution panel visible.

The page-shell proof verifies the live selectors and static `postJson('/execution/select'` / `postJson('/execution/start'` bindings.

## Negative Invariants

This runtime admits no:

- production backend route, DTO, service, model, or migration change;
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
- frontend-only durable authority.

## Next Boundary

The next pass must not assume result review, package, handoff/export, APS dispatch, or external export/download is proven by this runtime. Any deeper rendered downstream pass must first freeze the exact next rendered controls and then prove only that bounded slice.
