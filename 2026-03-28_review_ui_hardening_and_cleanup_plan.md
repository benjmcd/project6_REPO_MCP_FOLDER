# NRC APS Review UI Hardening And Cleanup Plan

## Purpose
This plan governs one bounded pass on the live `master` frontend/review-UI surface.

The pass has three ordered goals:
1. Harden async and state handling so stale responses do not overwrite newer user intent.
2. Apply a narrow accessibility hardening pass without redesigning or changing product behavior.
3. Archive confirmed-obsolete local QA and audit artifacts after validation succeeds.

This plan is intentionally strict. It is written so that `Implement the plan "2026-03-28_review_ui_hardening_and_cleanup_plan.md"` is sufficient instruction on its own.

## Canonical Source Of Truth
The live authority for this work is the `master` branch in:
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER`

The live files for this pass are only:
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\index.html`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.css`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\review_nrc_aps.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_catalog.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_details.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_graph.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_page.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_tree.py`

Non-authority local artifacts that must not drive implementation decisions:
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\qa_live_review_ui.spec.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\qa_edge_profile`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\audit_review_tmp_20260328`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\package.json`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\playwright.config.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\e2e`

Those local files may be cleanup candidates, but they are not product authority.

## Required Repo Guardrails
- Never delete or remove files. Move anything obsolete into the repo archive area instead.
- Use the narrowest correct change.
- Separate work into audit, edit, and re-audit phases.
- Do not broaden into retrieval-plane work, connector execution work, or graph-semantic redesign.
- Do not modify `.gitignore` in this pass.
- Do not archive ambiguous files just because they are untracked.
- Re-read edited lines immediately after each patch.

## Product Intent That Must Be Preserved
This pass must preserve all accepted review-UI behavior already live on `master`.

Specifically preserve:
- exact visible labels:
  - `Pipeline Overview`
  - `Run-specific Overview (Light)`
  - `Run-specific Overview (Heavy)`
- default run selection behavior
- `Pipeline Overview` graph semantics
- `Run-specific Overview (Light)` graph semantics
- `Run-specific Overview (Heavy)` graph semantics
- pane mapping:
  - `Pipeline Overview` -> `Pipeline Layout Summary`
  - `Run-specific Overview (Light)` -> `Pipeline Layout Summary`
  - `Run-specific Overview (Heavy)` -> `Strict Filesystem Tree`
- heavy-mode file browsing and preview behavior
- light-mode node details behavior
- pipeline-mode conceptual details behavior
- all existing internal review API route shapes

This pass is hardening only. It is not a redesign.

## In-Scope Problems To Solve
### 1. Async and stale-response safety
The current frontend has no request versioning or cancellation semantics for:
- run loads
- node details loads
- file details loads
- file preview loads
- mode-switch render sequencing

This creates a stale-response risk where older requests can overwrite newer UI intent.

### 2. Narrow accessibility hardening
The current UI still has a few confirmed accessibility weaknesses:
- the view toggle radios are hidden with `display: none`
- the drawer close button has no explicit accessible name
- custom interactive controls do not have explicit focus-visible styling

This pass must harden these without changing the visible labels, layout model, or product flow.

### 3. Cleanup of confirmed-obsolete local QA artifacts
This pass must move only confirmed-obsolete local QA/audit artifacts into:
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\archive\files_to_be_trashed`

Do not guess. Classify before moving.

## Explicit Non-Goals
Do not do any of the following in this pass:
- no retrieval-plane changes
- no connector runtime changes
- no new backend routes
- no public API contract changes
- no graph projection redesign
- no visual redesign
- no drawer focus trap
- no URL/history sync
- no responsive redesign
- no splitting `review.js` into multiple modules
- no dependency changes
- no migration of Playwright scaffold files into a formal toolchain

These are all out of scope unless a repo-confirmed blocker makes one unavoidable, and no such blocker is currently known.

## Area Of Effect
### Direct edit area
- `backend/app/review_ui/static/index.html`
- `backend/app/review_ui/static/review.js`
- `backend/app/review_ui/static/review.css`
- existing tracked review UI tests in `backend/tests`

### Runtime area affected
- async run loading
- async node/file details rendering
- async file preview rendering
- mode switching
- keyboard interaction and focus visibility

### Explicitly unaffected area
- `backend/app/services/review_nrc_aps_*`
- retrieval-plane services
- connector execution
- persistence
- route registration
- vendored static libraries:
  - `backend/app/review_ui/static/vendor/mermaid.min.js`
  - `backend/app/review_ui/static/vendor/svg-pan-zoom.min.js`

## Relevant Routes And Connections
The frontend currently depends on these internal review endpoints and their shapes must remain intact:
- `GET /api/v1/review/nrc-aps/runs`
- `GET /api/v1/review/nrc-aps/pipeline-definition?run_id=...`
- `GET /api/v1/review/nrc-aps/runs/{run_id}/overview`
- `GET /api/v1/review/nrc-aps/runs/{run_id}/nodes/{node_id}`
- `GET /api/v1/review/nrc-aps/runs/{run_id}/files/{tree_id}`
- `GET /api/v1/review/nrc-aps/runs/{run_id}/files/{tree_id}/preview`

The frontend also depends on these vendored libraries and they are not to be modified in this pass:
- Mermaid
- svg-pan-zoom

## Audit Phase Requirements
Before editing:
- confirm current branch is `master`
- confirm the authoritative files listed above still exist
- trace the async call graph in `review.js`
- identify every place where a stale response can still mutate visible state
- identify every control that needs accessible naming or focus-visible treatment
- classify each cleanup candidate as:
  - `archive_now`
  - `keep_for_now`
  - `leave_unmodified_due_to_ambiguity`

### Required cleanup classification
Default `archive_now` candidates, unless a repo-confirmed current need is found:
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\qa_live_review_ui.spec.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\qa_edge_profile`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\qa_uvicorn.out`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\qa_uvicorn.err`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\claim.out`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\claim.err`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\readtask.out`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\readtask.err`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\STATE_INTERACTION_AUDIT.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\audit_review_tmp_20260328`

Default `keep_for_now` candidates in this pass:
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.github`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\package.json`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\package-lock.json`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\playwright.config.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\e2e`

Reason: those appear to form a local Playwright/CI scaffold and are more ambiguous than the clearly temporary QA/audit files.

## Edit Phase Requirements
### A. Async hardening in `review.js`
Implement stale-response protection without changing the route surface.

Required behavior:
- only the most recent `loadRun` result may update `State.pipelineDefinition`, `State.overview`, the disabled overlay, or the side pane
- only the most recent node/file details request may update the drawer
- only the most recent preview request may update the preview container
- stale responses must be ignored silently, not shown as user-facing errors
- switching modes while requests are in flight must not reintroduce old state into the newly selected mode

Acceptable implementation shapes:
- monotonic request generation counters
- per-concern request tokens
- local in-flight guards

Do not introduce:
- AbortController unless needed and kept local
- global event bus
- new dependency
- backend support changes

### B. Accessibility hardening in `index.html` and `review.css`
Required changes:
- add an explicit accessible name to the close button
- replace `display: none` on the toggle radios with a visually-hidden accessible pattern, or an equivalent pattern that preserves keyboard/screen-reader operability
- add visible focus styling for:
  - run selector
  - view toggle controls
  - tree entry buttons
  - close button

Constraints:
- exact visible labels must remain unchanged
- the current toggle layout and overall appearance should remain materially the same
- no broad CSS cleanup
- no color redesign except what is minimally needed for visible focus

### C. Test edits
Only edit tracked review UI tests as needed.

At minimum, update or add assertions for:
- three exact visible view labels
- explicit accessible close button name
- any server-rendered markup changes needed to support the accessible toggle pattern

Do not create or bless a new untracked Playwright suite in this pass.

## Re-Audit And Validation Requirements
### Required test run
Run only the tracked review test surface:
- `python -m pytest backend\\tests\\test_review_nrc_aps_page.py backend\\tests\\test_review_nrc_aps_api.py backend\\tests\\test_review_nrc_aps_graph.py backend\\tests\\test_review_nrc_aps_tree.py backend\\tests\\test_review_nrc_aps_details.py`

If additional tracked review tests are touched, include them too.

### Required live verification
Run a live local verification against:
- `http://127.0.0.1:8010/review/nrc-aps`

Verify:
- the three exact labels still render
- rapid switching between runs does not leave mismatched graph/pane/drawer state
- rapid switching between view modes does not let stale graph or stale drawer content win
- rapid heavy-mode file switching does not let old preview content overwrite newer selection
- keyboard focus is visibly apparent on the selector, toggle controls, tree buttons, and close button
- pane mapping by mode remains unchanged

### Pass criteria
The pass succeeds only if all of the following hold:
- tracked review tests pass
- live verification confirms no obvious stale-response overwrite behavior
- three-mode behavior is unchanged except for hardening
- no route contracts changed
- no new dependencies added
- cleanup moves only confirmed-obsolete local artifacts

### Fail criteria
Stop and revise if any of the following occur:
- visible label text changes
- pane mapping changes
- heavy-mode file browsing breaks
- light-mode node details behavior regresses
- pipeline-mode conceptual details behavior regresses
- backend route shape changes become necessary
- ambiguous local tooling would need to be archived to make progress

## Cleanup Phase Requirements
Only begin cleanup after the edit and validation phases pass.

Rules:
- move, never delete
- use the repo archive area
- do not touch `keep_for_now` items
- do not touch `.gitignore`
- do not archive anything because it is merely untracked; it must also be confirmed obsolete in this pass

Archive destination:
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\archive\files_to_be_trashed\2026-03-28_post_hardening_cleanup`

The cleanup commit must be separate from the hardening commit.

## Tech-Debt Notes
This plan intentionally does not solve these broader debts:
- `review.js` is still monolithic
- no focus trap in drawer
- no URL/history sync
- no formal frontend test harness integration
- no architectural split between rendering and state management

Those remain future work. Do not silently absorb them into this pass.

## Implementation Order
1. audit authoritative files and classify cleanup candidates
2. patch async hardening in `review.js`
3. patch narrow accessibility issues in `index.html` and `review.css`
4. patch only necessary tracked review tests
5. re-read edited lines
6. run tracked review tests
7. run live local verification
8. only then archive confirmed-obsolete local QA artifacts
9. make separate commits

## Deliverable Expectation
At the end of execution, report:
- what changed
- what was intentionally left unchanged
- which cleanup candidates were archived
- which ambiguous local files were intentionally left alone
- exact tests run
- exact live verification results
