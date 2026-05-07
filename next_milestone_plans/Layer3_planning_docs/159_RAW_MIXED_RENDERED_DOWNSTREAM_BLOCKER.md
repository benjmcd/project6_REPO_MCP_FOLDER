# Layer 3 Raw Mixed Rendered Downstream Blocker

Status: current-main planning/control blocker report for deeper rendered raw mixed downstream proof.

This document records why the next test-only rendered downstream pass cannot honestly proceed beyond plan approval on current main without widening UI scope. It does not add or admit route, DTO, service, model, migration, UI control, source, ingestion, package, connector, provider, RAG/vector, mockup, hidden LLM, or auth/security behavior.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current-main anchor: PR `#732`, merge commit `d6a70a86eac76c7931822a1cda66bdfaff99bb36`
- readiness reference: `158_POST_730_PRACTICAL_READINESS.md`
- rendered raw mixed mode: `raw_mixed_server_owned_manifest_ref_ui_entry`
- live rendered source/material proof: `e2e/layer3-workbench.spec.js` test `Layer 3 workbench materializes raw mixed manifest through rendered controls`
- relevant UI shell: `backend/app/review_ui/static/layer3.html`
- relevant UI runtime: `backend/app/review_ui/static/layer3.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this report.

## Blocker Decision

The deeper rendered raw mixed downstream path is blocked at rendered plan approval on current main.

The current rendered UI can:

- call the live raw mixed materialization route through bounded server-owned manifest-ref controls;
- refresh candidates and select returned `dataset_version` and `aps_content_document` IDs;
- drive existing rendered source preview, material preview, Gate B, Gate C, plan preview, and plan approval.

The current rendered UI cannot honestly drive:

- execution selection;
- execution start;
- result status/review for the just-approved raw mixed associated-cohort path;
- package preview/commit/submit for that same rendered-started path;
- handoff/export prepare, APS dispatch, or external export/download for that same rendered-started path.

The missing first downstream link is rendered execution selection/start. Current main has downstream result/package/handoff controls, but no rendered controls that create the selected `L3PassRun` shell or start execution after plan approval.

Short blocker phrase: no rendered execution selection/start controls.

## Source Evidence

Evidence from source inspection:

- `backend/app/review_ui/static/layer3.html` has result, package, handoff, APS handoff, external export/download, delivery, and signed-reference controls, but no `execution-select` or `execution-start` rendered controls.
- `backend/app/review_ui/static/layer3.js` enables the execution step only from `State.sessionSummary?.execution_selection?.selected`; it does not expose a rendered control that posts to `/api/v1/layer3/execution/select` or `/api/v1/layer3/execution/start`.
- `e2e/layer3-workbench.spec.js` helper `assertRenderedPlanApprovalStopsBeforeExecution` explicitly asserts after rendered plan approval that `#result-status-inspect`, `#result-review-submit`, and `#package-review-preview-inspect` are disabled, the execution/results/package step chips are unavailable, `pass_run_count` is `0`, `execution_selection.selected` is `false`, and no `/execution/select`, `/execution/start`, `/execution/result/*`, `/package/review/`, or `/handoff/` paths were called.
- The current raw mixed rendered materialization smoke calls `assertRenderedPlanApprovalStopsBeforeExecution` after plan approval.

## Invalid Workaround

Using API calls to `/execution/select` and `/execution/start` after rendered materialization and plan approval would not satisfy the current next-pass boundary from `158_POST_730_PRACTICAL_READINESS.md`, because that boundary says after materialization the test should drive the rendered UI only through server-backed existing controls.

API setup remains appropriate for deterministic server-owned manifest files and source authority. It is not appropriate as a hidden substitute for missing rendered execution selection/start controls in this specific deeper rendered downstream proof.

## Required Future Freeze

A future rendered downstream implementation needs a separate UI/theme freeze before code if the selected path is to add controls. That freeze must name one exact mode, such as:

- `raw_mixed_rendered_execution_selection_start_controls`

That freeze must specify:

- exact rendered controls for execution selection and execution start;
- exact route calls and request DTO fields;
- server-authoritative state that enables each control;
- disabled/loading/success/error states;
- headed and headless Chrome proof across relevant themes;
- stable selectors;
- no frontend-only durable authority;
- no source expansion, package mutation, provider/public URL, connector/destination dispatch, RAG/vector, hidden LLM, mockup, model/migration, or auth/security expansion.

## Next Pass Recommendation

The next safe pass is a planning/control freeze for rendered execution selection/start controls, not a deeper rendered downstream implementation.

If the project decides not to add rendered execution controls yet, the alternative is to keep current UI proof stopped at plan approval and continue broader work in API-level E2E or non-UI lanes.

## Validation Performed

Current-main baseline validation before this blocker decision:

- `python .\tools\l3-progress-check.py`: PASS
- `python -m pytest .\backend\tests\test_layer3_page.py -q`: PASS, `3 passed`
- `npx playwright test e2e/layer3-workbench.spec.js --grep "materializes raw mixed manifest through rendered controls"`: PASS

## Negative Invariants

This blocker report keeps all of the following blocked:

- arbitrary local path input;
- local upload or local-directory ingestion;
- web connector retrieval;
- RAG/vector retrieval or index creation;
- source adapter registry or source-family expansion;
- provider/public URL or signed public URL generation;
- real connector or destination dispatch;
- broad package mutation or reconstruction;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

## Acceptance Criteria

This blocker report is accepted only when:

- this file exists and names PR `#732`, merge commit `d6a70a86eac76c7931822a1cda66bdfaff99bb36`, and `raw_mixed_server_owned_manifest_ref_ui_entry`;
- progress/proof manifests and the progress board reference this as planning/control blocker evidence;
- `tools/l3-progress-check.py` guards this file and the current-main references;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` passes.
