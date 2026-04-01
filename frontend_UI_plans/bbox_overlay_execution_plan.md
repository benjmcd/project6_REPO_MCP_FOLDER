# BBox Overlay Execution Plan for Document Trace

## Purpose

Add bbox overlays to the existing PDF source viewer on the `Document Trace` page by editing only the current `main` baseline and using live worktrees as donor evidence. This is a bounded frontend-only addendum to the existing document-trace effort. It is not a donor merge, not a viewer rewrite, and not a backend contract change.

This plan is the governing implementation spec for the bbox-overlay pass unless live repo evidence contradicts it during the mandatory preflight gates below.

## Project Alignment

This pass must stay aligned with the repo's existing document-trace goals and phase structure:

- preserve `/review/nrc-aps` as the system entry surface
- preserve the separate two-pane `Document Trace` page
- remain frontend-only
- keep the work narrow and additive
- avoid generic annotation abstractions
- avoid broader viewer or product refactors

Treat this as a bounded Phase 6 / Phase 8 addendum to the existing planning docs:

- `frontend_UI_plans/nrc_aps_document_trace_ui_spec.md`
- `frontend_UI_plans/nrc_aps_document_trace_ui_data_contract.md`
- `frontend_UI_plans/nrc_aps_document_trace_ui_implementation_blueprint.md`
- `frontend_UI_plans/nrc_aps_document_trace_ui_validation_plan.md`
- `frontend_UI_plans/nrc_aps_document_trace_ui_phase_partition_plan.md`

## Authority Order

1. This execution plan
2. The current live `main` baseline
3. The existing document-trace planning docs listed above
4. Live donor worktrees only as donor evidence:
   - `zwl`
   - `zli`
   - `zag`
   - `mro`
5. Older synthesis or adjudication artifacts only as background, not authority

## Current Reference Snapshot

These are planning-time reference values and must be revalidated during Gate 0:

- `main` planning-time HEAD: `679eb59a0d2010b016bd53817c30ebf644abb61c`
- recommended fresh implementation branch: `codex/bbox-overlay-main-implementation`
- recommended fresh implementation worktree path: `C:\Users\benny\OneDrive\Desktop\project6-wt-bbox-overlay-main`

Planning-time donor references:

- `zwl`: `cursor/document-trace-bbox-overlay` @ `7f3910b7979a5eb18f4a9b7ac10676b3d04f2512`, dirty
- `zli`: `feature/document-trace-metadata-bbox-overlays` @ `b4e8eeb683c6dc66059efe225903c54d3f698f7f`, dirty
- `zag`: `feature/document-trace-bbox-overlays` @ `7f3910b7979a5eb18f4a9b7ac10676b3d04f2512`, dirty
- `mro`: `fix-document-trace-ui` @ `96bb38b9d71db265036927c81fa152847527bcd5`, dirty

## Hard Preconditions

### State Preservation Gate -1

Before Gate 0, preserve the exact current repo/worktree state and do not implement in the current dirty `main` checkout.

Required:

- create a fresh implementation branch from the frozen current `main` commit
- create a fresh implementation worktree rooted at that branch
- perform all implementation in the fresh worktree only
- treat the current `main` checkout and all donor worktrees as read-only evidence surfaces

Stop and return a blocker report instead of coding if:

- a fresh isolated implementation worktree cannot be established cleanly
- the worktree path or branch name collides with an existing active worktree and no equally narrow replacement is chosen and reported
- execution would mutate the current dirty `main` checkout or donor worktrees directly

### Gate 0: Donor Freeze and Authority Adjudication

This gate is mandatory and must complete before any edit.

Must capture:

- exact `main` HEAD commit and working-tree status
- exact donor worktree HEAD commits and working-tree statuses for `zwl`, `zli`, `zag`, and `mro`
- exact dirty diffs for the relevant donor files only:
  - `backend/app/review_ui/static/document_trace.js`
  - `backend/app/review_ui/static/document_trace.css`
  - `backend/tests/test_review_nrc_aps_document_trace_page.py` where present
- whether any untracked files matter to implementation

Must record a short rejection memo:

- why `zwl` remains the host donor even though `zli` is the newer committed overlay branch
- why `zli` is coordinate-seam donor only
- why `zag` and `mro` are not acceptable hosts

Required host-donor rationale:

- `zwl` is the preferred host donor because it provides:
  - shared extracted-units flow
  - in-flight request dedup
  - reactive overlay sync
  - page-coverage suppression
  - localized DOM overlay rendering
- `zli` is coordinate donor only because its committed implementation shape introduces:
  - a separate viewer-side fetch path
  - a persistent `bboxByPage` state shape
- `zag` is rejected because it introduces:
  - `State.bboxOverlay`
  - a second fetch path
  - a separate overlay state domain
- `mro` is rejected because it is low-maturity and manual-scale driven

Hard stop conditions:

- `main` drifted materially from planning assumptions
- donor evidence drifted materially during the pass
- a newer extant overlay surface appears beyond the known donors
- `zwl`'s dirty donor state is materially incomplete, internally inconsistent, or dependent on untracked local context
- implementation would require backend changes, broader viewer restructuring, a second overlay state/fetch/cache path, or scope expansion beyond this plan

If Gate 0 fails because `zwl` is incoherent, stop and return a blocker report recommending replanning around committed `zli` as the baseline evidence source. Do not improvise a fallback implementation.

## Scope Locks

### In Scope

- `backend/app/review_ui/static/document_trace.js`
- `backend/app/review_ui/static/document_trace.css`
- `backend/tests/test_review_nrc_aps_document_trace_page.py`
- only narrow shared-file regression fixes if a verified blocker forces them

### Out of Scope

- all backend, API, schema, and route changes
- any new extracted-units fields or precision semantics
- any storage or retrieval changes
- non-PDF overlays
- eager-page-rendering refactors or virtualization
- generic annotation systems
- unrelated document-trace polish
- main review page redesign

## Public Interface Contract

No public API, schema, route, or payload changes are allowed.

Continue to rely on the existing extracted-units contract already exposed by the trace model:

- `page_number`
- optional `bbox`
- `source_precision`

The overlay feature must not cause the UI to imply greater precision than the payload already supports.

## Implementation Contract

### State and Data Flow

Implement this exactly:

- `State.tabData.extracted_units` is the sole source of truth for overlay content
- `State.tabRequests.extracted_units` is the sole in-flight request holder
- `State.viewer.showBboxes` is the only overlay-specific viewer state
- derived per-page grouping must be recomputed during overlay sync and not stored persistently
- do not introduce a second overlay state domain
- do not introduce `State.bboxOverlay`
- do not introduce `bboxByPage`
- do not introduce a second extracted-units fetch path

`ensureExtractedUnitsLoaded(seq)` contract:

- return the shared extracted-units payload or `null` if stale
- use cached `State.tabData.extracted_units` when already present
- use the same in-flight promise when already requested
- mutate shared state only if the request still matches the current `run_id`, `target_id`, and `_actionSeq`
- clear the in-flight promise in `finally`

### Prewarm Contract

After `renderTraceShell()`, prewarm extracted units because overlays become a source-pane dependency.

Rules:

- reuse the same shared promise/path as the Extracted Units tab
- do not create repeated churn for the same target
- prewarm failure must not replace shell content or tab content
- prewarm failure must not create a noisy shell-level error

Overlay behavior while extracted units are:

- loading: overlays absent, no shell-level error
- stale: ignore the stale result
- failed: overlays absent, no shell-level error
- empty or no bbox-capable units: overlays absent; toggle remains visible and inert rather than disappearing

### Overlay Rendering Eligibility

Render boxes only for units with:

- a valid numeric `page_number`
- the same page-number convention already used by current document-trace navigation and jump logic
- a valid renderable `bbox`

Do not invent new page-number normalization rules in this pass.

### DOM and Geometry Contract

The page shell is the canonical page identity node.

Required:

- each PDF page gets a `.pdf-page-shell`
- the canonical page identity attribute used by scroll, jump, focus, and overlay lookup lives on the shell
- the canvas and overlay layer are sibling children inside the shell
- scroll, jump, and focus selectors move to the shell consistently
- overlay sync runs only after the shell has final rendered viewport geometry for that render cycle
- overlay geometry is derived relative to the shell, not raw outer containers
- do not leave mixed selector usage where old logic still targets raw canvases and new logic targets shells

### Overlay Behavior and Accessibility

Use DOM markers, not SVG.

Required:

- overlay layer `pointer-events: none`
- overlay layer `aria-hidden="true"`
- markers are not focusable
- toggle has an explicit accessible label
- purely visual markers do not create noisy accessibility output
- light and dark theme legibility must remain acceptable

BBox handling rules:

- reject invalid bbox arrays
- normalize inverted coordinates
- suppress zero or near-zero extents
- do not add interaction semantics to markers in this pass

### Suppression Rule

Apply suppression only after final pixel mapping.

Rule:

- suppress when `mapped_rect_area / page_shell_area >= 0.98`

Where:

- `page_shell_area` means rendered viewport width x height for that page
- do not use outer container or flex space
- do not tune the threshold ad hoc during this pass

### Coordinate Seam

Default:

- use scale-based mapping first

Allowed change only after verification:

- if reproducible coordinate drift is proven, replace only the mapping seam with `viewport.convertToViewportRectangle()`
- do not import any additional `zli` architecture

## Sequential Execution Slices

### Slice 00: Preflight Freeze

Files edited:

- none

Deliverables:

- donor freeze snapshot
- `zwl`-over-`zli` rejection memo
- stop conditions recorded

Gate:

- donor authority fully closed

### Slice 01: Shared Extracted-Units Data Flow

Files:

- `backend/app/review_ui/static/document_trace.js`
- `backend/tests/test_review_nrc_aps_document_trace_page.py`

Changes:

- add `State.tabRequests.extracted_units`
- add `ensureExtractedUnitsLoaded(seq)`
- route the Extracted Units tab through the shared loader
- clear loader state on target changes
- prewarm extracted units after trace-shell render

Gate:

- document-trace tests pass
- one extracted-units fetch path exists
- no overlay DOM yet
- no backend files changed

### Slice 02: Overlay DOM, Toggle, and Sync

Files:

- `backend/app/review_ui/static/document_trace.js`
- `backend/app/review_ui/static/document_trace.css`
- `backend/tests/test_review_nrc_aps_document_trace_page.py`

Changes:

- add `State.viewer.showBboxes`
- create page shell and overlay layer
- make the shell the canonical page node
- add bbox marker rendering and visibility toggle
- add overlay clearing, sync, invalidation, and suppression
- update scroll and focus logic to use shell selectors consistently

Gate:

- static tests pass
- no stale or duplicate overlays
- no regression in page focus tracking, page jumps, or theme behavior

### Slice 03: Coordinate Verification Gate

Files:

- `backend/app/review_ui/static/document_trace.js`
- `backend/app/review_ui/static/document_trace.css` only if a strict anchoring fix is required

Verification matrix:

- born-digital multi-page PDF
- mixed-geometry or layout-complex PDF
- rotated-page case if available
- OCR-heavy noisy-bbox case if available
- repeated zoom in and out
- existing fit-width control on `main` only
- page revisit
- target switch during in-flight extracted-units load

Decision rule:

- keep scale mapping if it holds
- if reproducible coordinate drift appears, replace only the mapping seam

Gate:

- automated tests still pass
- any observed coordinate defect is fixed without architecture expansion
- no second fetch/cache/state path appears

### Slice 04: Hardening and Regression Closure

Files:

- `backend/app/review_ui/static/document_trace.js`
- `backend/app/review_ui/static/document_trace.css`
- `backend/tests/test_review_nrc_aps_document_trace_page.py`
- only narrow shared-file regression fixes if required

Changes:

- finalize empty, loading, and failure overlay behavior
- verify silent prewarm behavior
- verify accessibility minimums
- re-audit edited files for donor leakage and scope drift

Gate:

- focused document-trace tests pass
- existing review-page regression tests pass
- live manual QA passes for document trace and `/review/nrc-aps`

## Testing and Verification

### Automated

- keep existing document-trace route, schema, and static-asset tests green
- add static assertions only for presence of new overlay identifiers and styles
- static tests are presence/regression guards only, not proof of behavioral correctness

At minimum run:

- `backend/tests/test_review_nrc_aps_document_trace_page.py`
- `backend/tests/test_review_nrc_aps_page.py`

Expand the regression set only if scope expansion forces shared-file edits.

### Manual

Manual verification must include:

- born-digital multi-page PDF
- mixed-geometry or layout-complex PDF
- rotated-page case if available
- OCR-heavy noisy-bbox case if available
- repeated zoom in and out
- existing fit-width control on `main` only
- page revisit
- target switch during in-flight extracted-units load
- absence, empty, and failure cases
- overlay non-interference
- theme legibility
- basic performance sanity check for repeated zoom rerenders

If rotated or OCR-heavy cases are unavailable in the audited runtime, report them as unavailable and do not infer pass status for them.

If live browser verification is unavailable in the session, do not change the coordinate seam.

## Required Reporting

At the start of implementation:

1. restate the execution plan in your own words
2. identify any unresolved contradiction before coding
3. complete State Preservation Gate -1
4. complete Gate 0
5. only then proceed slice by slice

After each slice, report exactly:

- files changed
- what contract points were satisfied
- what was intentionally deferred
- whether any stop condition was triggered
- whether the next slice is still justified

At the end, report:

- final files changed
- exact tests run and results
- exact manual verification scenarios completed
- which scenarios were unavailable
- any remaining risks
- whether implementation remained fully within this plan
- whether any deviation occurred and why

## Non-Negotiable Stop Rule

If any step would require:

- backend changes
- broader viewer restructuring
- a second overlay state, fetch, or cache path
- or scope expansion beyond this plan

stop and return a blocker report instead of improvising.
