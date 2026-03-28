# NRC APS Document Trace UI Implementation Blueprint

## 1. Purpose

This document converts the document-trace UI spec into an implementation-ready repo plan.

It freezes:

- the exact implementation layers
- the exact repo files expected to change
- the exact new modules expected to be added
- the order of implementation, validation, freeze, and commit
- the boundaries that must not be crossed in v1

## 2. Canonical Source Of Truth

Live authority surfaces for this blueprint:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\main.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\review_nrc_aps.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\schemas\review_nrc_aps.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_runtime.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\models\models.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\index.html`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.css`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260328_150207\`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260328_150207\lc.db`

Repo-confirmed facts that shape this blueprint:

- the current review page shell is served directly by `backend\main.py`
- the current review router already owns the additive review API surface
- the current review page has no document-trace sibling yet
- the current review API has no binary/source stream route
- the review tree is runtime-root oriented, not a document selector
- the durable source contract for this feature is `blob_ref`
- fine-grained extracted units should come from diagnostics `ordered_units`
- chunk/index data should come from `aps_content_chunk`
- retrieval is not available in the audited runtime and cannot be required

## 3. Implementation Principles

- Keep the implementation read-only.
- Keep the implementation NRC APS specific.
- Keep the implementation run-scoped.
- Keep the implementation additive.
- Keep existing review behavior stable and backward compatible.
- Keep the implementation modular by separating trace assembly, source streaming, page shell, and page controller concerns.
- Keep the frontend build-free in v1.
- Vendor any required PDF viewer assets instead of introducing a Node build toolchain.
- Do not modify connector execution paths.
- Do not overload the existing `review.js` controller with the full document-trace page logic.

## 4. Layered Implementation Shape

The v1 document-trace surface should be implemented in six layers.

### 4.1 Page Route Layer

Responsibilities:

- expose the document-trace HTML shell route
- keep the current review page route intact

### 4.2 Review API Layer

Responsibilities:

- expose read-only document-trace API routes
- validate request parameters
- keep route handlers thin

### 4.3 Trace Assembly Service Layer

Responsibilities:

- resolve the document trace bundle for `run_id + target_id`
- assemble identity, completeness, units, chunks, diagnostics, normalized text, and downstream usage summary
- keep provenance logic out of the frontend

### 4.4 Source Streaming Layer

Responsibilities:

- resolve the run-scoped `blob_ref`
- validate bounded path access
- stream the source object safely

### 4.5 UI Shell Layer

Responsibilities:

- serve the document-trace HTML shell
- coordinate run selector, document selector, source viewer, tabs, and theme

### 4.6 Static Asset Layer

Responsibilities:

- provide document-trace-specific CSS and JS
- provide vendored PDF rendering assets
- preserve theme and accessibility behavior already established by the main review UI

## 5. Exact Existing Files To Modify

Only these existing repo files should be touched for the first implementation slice unless a repo-confirmed blocker appears.

### 5.1 `backend\main.py`

Planned responsibility:

- add the document-trace page shell route
- serve the new document-trace HTML file from the existing static directory

Expected change class:

- narrow additive route

### 5.2 `backend\app\api\review_nrc_aps.py`

Planned responsibility:

- add document selector, trace, source, and tab routes

Expected change class:

- narrow additive route handlers

### 5.3 `backend\app\schemas\review_nrc_aps.py`

Planned responsibility:

- add Pydantic models for the document-trace contract

Expected change class:

- narrow additive schemas

### 5.4 `backend\app\services\review_nrc_aps_runtime.py`

Planned responsibility:

- reuse or narrowly extend path normalization/path safety helpers for source streaming

Expected change class:

- narrow additive helper logic only if current helpers are insufficient

### 5.5 Main Review UI Shell Files

These may need a narrow navigation addition so users can enter `Document Trace` from the existing review page:

- `backend\app\review_ui\static\index.html`
- `backend\app\review_ui\static\review.css`
- `backend\app\review_ui\static\review.js`

Expected change class:

- small launch/control additions only

No other live product files should be modified in the first slice unless the repo proves a concrete integration blocker.

## 6. Area Of Effect

### 6.1 Direct Edit Area

The implementation should be expected to touch only:

- `backend\main.py`
- `backend\app\api\review_nrc_aps.py`
- `backend\app\schemas\review_nrc_aps.py`
- `backend\app\services\review_nrc_aps_runtime.py` only if path-safety helpers require narrow extension
- the new `backend\app\services\review_nrc_aps_document_trace.py`
- the new `backend\app\review_ui\static\document_trace.html`
- the new `backend\app\review_ui\static\document_trace.css`
- the new `backend\app\review_ui\static\document_trace.js`
- narrow launch additions to:
  - `backend\app\review_ui\static\index.html`
  - `backend\app\review_ui\static\review.css`
  - `backend\app\review_ui\static\review.js`
- vendored PDF viewer assets under `backend\app\review_ui\static\vendor\`
- new focused tests under `backend\tests\`

### 6.2 Adjacent Runtime And Behavior Impact

These areas are affected indirectly and must be treated as regression-sensitive:

- main review page route and shell loading
- the existing three review modes and their pane mappings
- existing graph zoom-preservation behavior
- existing node/file details and safe preview behavior
- existing review API route family under `/api/v1/review/nrc-aps/...`
- theme behavior shared between the existing review page and the new document-trace page
- browser-side static asset serving under `/review/nrc-aps/static`
- review-root path safety and runtime allowlisting

### 6.3 Explicit Non-Effect Area

This implementation must not intentionally modify:

- connector execution paths
- retrieval-plane generation behavior
- downstream artifact production behavior
- corpus ingestion or run execution commands
- runtime artifact contents
- unrelated repo-level tooling and untracked local scaffolding

### 6.4 Change-Risk Hotspots

The most regression-sensitive areas are:

- `backend\main.py` route additions
- `backend\app\api\review_nrc_aps.py` route-family consistency
- any shared CSS variables or shared JS launch/navigation added to the current review page
- any path-normalization logic reused for source streaming

### 6.5 Preservation Requirements

The implementation must preserve these existing user-visible behaviors:

- the current `/review/nrc-aps` shell route
- current run selector behavior
- current three-mode review toggle behavior
- current review graph rendering and state overlays
- current file-tree interactions
- current details drawer interactions
- current dark-mode behavior
- current zoom-preservation behavior on the existing review page

If a shared file must be edited, the change must be:

- narrow
- additive
- covered by regression validation
- justified by a repo-confirmed integration need

## 7. Exact New Files To Add

### 7.1 Backend Service Files

- `backend\app\services\review_nrc_aps_document_trace.py`
  - document-trace assembly

### 7.2 Static Page Files

- `backend\app\review_ui\static\document_trace.html`
- `backend\app\review_ui\static\document_trace.css`
- `backend\app\review_ui\static\document_trace.js`

### 7.3 Vendored Viewer Assets

Under:

- `backend\app\review_ui\static\vendor\`

Planned additions:

- PDF viewer runtime assets from the official PDF.js distribution
- license/notice update if required

### 7.4 Test Files

- `backend\tests\test_review_nrc_aps_document_trace_service.py`
- `backend\tests\test_review_nrc_aps_document_trace_api.py`
- `backend\tests\test_review_nrc_aps_document_trace_page.py`

Existing review tests may also receive narrow regression assertions if the current review page gains a launch control.

## 8. Module Boundaries

### 8.1 `review_nrc_aps_document_trace.py`

Owns:

- run-target lookup
- linkage lookup
- content/document/chunk lookup
- diagnostics and normalized-text loading
- completeness classification
- downstream usage summary assembly

Must not own:

- route registration
- HTML generation
- PDF rendering

### 8.2 `review_nrc_aps_runtime.py`

Owns:

- bounded path validation
- runtime-root discovery

Must not own:

- document-trace business logic

### 8.3 `document_trace.js`

Owns:

- page bootstrapping from query params
- run/document selector coordination
- tab loading
- source-viewer state
- synchronization handling

Must not own:

- provenance reconstruction from raw backend rows

## 9. Resolution Algorithm

The backend assembly algorithm for `run_id + target_id` should be:

1. resolve the review root for `run_id`
2. load the `connector_run_target` row for `run_id + target_id`
3. load the `aps_content_linkage` row for `run_id + target_id`
4. if linkage exists:
   - load the `aps_content_document` row by `content_id`
   - load `aps_content_chunk` rows by `content_id`
   - load diagnostics JSON via `diagnostics_ref` when present
   - load normalized text via `normalized_text_ref` when present
   - resolve `blob_ref` when present
5. derive:
   - identity bundle
   - completeness flags
   - extracted units from diagnostics `ordered_units`
   - indexed chunk list
   - downstream usage summary
6. return a stable trace model even when one or more layers are missing

The service must not derive document identity from filename guessing alone if stronger run-target/linkage metadata exists.

## 10. Source Viewer Strategy

### 10.1 PDF Viewer Choice

Use vendored PDF.js-style client rendering for v1.

Reason:

- page navigation and highlight control are needed
- native embedded PDF viewers do not provide reliable programmatic alignment behavior
- the repo already uses vendored frontend assets for Mermaid and pan/zoom, so vendored PDF rendering fits the existing build-free strategy

### 10.2 Page Rendering Strategy

- render only needed pages eagerly
- preserve zoom and page position during same-document tab interaction
- allow page jumps from right-side selection
- do not attempt exact text-layer mapping unless data supports it cleanly

## 11. Frontend Page Behavior

### 11.1 Boot Sequence

1. read `run_id` and `target_id` from query params
2. load available runs if needed
3. load the document selector for the chosen run
4. load the trace manifest for the chosen target
5. bootstrap the left viewer and the default right-side tab

### 11.2 Selector Behavior

- changing `run_id` resets `target_id` to the selector default for that run
- changing `target_id` reloads the trace manifest
- query params update on both changes

### 11.3 Tab Behavior

- tabs load lazily
- unavailable tabs remain visible but disabled or empty with explanation
- the page should not fetch every tab payload on initial load

### 11.4 Sync Behavior

- extracted-unit click -> source page jump is required
- source page change -> page-scoped filtering/highlighting on the right is required
- all stronger sync modes are conditional on trace precision metadata

## 12. Representative Implementation Scenarios

The implementation is not complete unless it can handle these concrete scenarios coherently.

### 12.1 Strong PDF With Full Core Layers

- source blob present
- diagnostics present
- normalized text present
- indexed chunks present

Implementation expectation:

- all primary tabs work
- page-level sync works
- no fallback messaging appears for available layers

### 12.2 PDF With Missing Optional Layers

- source blob present
- one or more optional layers missing

Implementation expectation:

- missingness is explicit
- the page remains usable
- the implementation does not attempt regeneration

### 12.3 Deduplicated Content

- two targets share one `content_id`

Implementation expectation:

- selector and routing remain target-scoped
- the backend contract still surfaces `content_id`

### 12.4 Retrieval-Absent Runtime

- zero retrieval rows for the run

Implementation expectation:

- no required route, tab, or page behavior fails because retrieval is unavailable

### 12.5 Non-PDF Fallback

- source type is text-like or unsupported by the PDF viewer

Implementation expectation:

- source rendering falls back cleanly
- right-side tabs remain trace-driven, not source-viewer-driven

## 13. Security And Read-Only Boundaries

- all new routes must be GET-only
- source streaming must validate bounded paths under the review runtime
- no route may expose arbitrary absolute file paths from user input
- no route may mutate runtime artifacts or regenerate missing outputs
- empty or partially missing trace states must fail closed and render explicit unavailability rather than triggering new work

## 14. Implementation Phases

### 14.1 Audit Phase

- confirm the live authority files above
- confirm the document-trace runtime assumptions against the current audited runtime
- confirm there is no existing reusable PDF/document viewer pattern in the live review surface

### 14.2 Backend Contract Phase

- add trace schemas
- add trace assembly service
- add source-stream route
- add tab routes

### 14.3 Frontend Shell Phase

- add the page shell and page assets
- add narrow entry navigation from the main review UI
- preserve current review behavior

### 14.4 Viewer Phase

- vendor PDF viewer assets
- render source PDFs and text-like fallbacks
- add page navigation and zoom

### 14.5 Trace Workspace Phase

- implement summary tab
- implement extracted-units tab
- implement normalized-text tab
- implement indexed-chunks tab
- implement diagnostics tab
- implement downstream-usage tab

### 14.6 Synchronization Phase

- implement required page-level sync
- add unit-level sync where diagnostics data supports it
- keep unsupported mappings explicit

### 14.7 Hardening Phase

- loading, empty, and error states
- stale-request protection
- theme consistency
- accessibility and keyboard support

### 14.8 Re-Audit And Closeout Phase

- rerun focused tests
- perform live manual QA against the audited runtime
- verify no regression of the main review page
- commit in narrow logical units

## 15. Commit Plan

The preferred closeout shape is:

1. backend trace assembly, schemas, and routes
2. frontend document-trace page plus vendored viewer assets
3. tests and hardening, unless the previous two commits already include them narrowly

If the implementation remains small and coherent, commits 2 and 3 may be combined. The backend contract and the frontend page should not be mixed into one undifferentiated commit if they can be separated cleanly.

The closeout is not complete unless regression-sensitive shared-file edits, if any, are explicitly called out in the final implementation summary.

## 16. Non-Negotiable Guardrails

- do not treat the current local corpus path as the durable source contract
- do not require retrieval rows
- do not use `aps_content_units_v2` as the sole fine-grained extraction source
- do not permanently embed this feature under the existing review page body
- do not broaden into multi-document comparison or editing
- do not create a Node-based frontend build pipeline
