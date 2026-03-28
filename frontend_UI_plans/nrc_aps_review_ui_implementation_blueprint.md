# NRC APS Review UI Implementation Blueprint

## 1. Purpose

This document converts the higher-level review UI spec into an implementation-ready repo plan.

It freezes:

- the exact implementation layers
- the exact repo files expected to change
- the exact new modules expected to be added
- the boundaries that should not be crossed in v1

This blueprint is intentionally narrow. It is designed to let implementation proceed mechanically instead of interpretively.

## 2. Canonical Source Of Truth

Live authority surfaces for this blueprint:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\main.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\router.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\core\config.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\models\models.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\schemas\api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\local_corpus_e2e_summary.json`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\`

Repo-confirmed facts that shape this blueprint:

- the existing web surface is the FastAPI app in `backend\main.py`
- the existing API router lives in `backend\app\api\router.py`
- the repo does not currently expose a generic review run-selector endpoint
- the repo does not currently contain a dedicated standalone frontend application scaffold
- the repo already mounts `/storage`, so review rendering must not assume raw filesystem access from the browser

## 3. Implementation Principles

- Keep the implementation read-only.
- Keep the implementation NRC APS specific.
- Keep the implementation additive.
- Keep the implementation modular by separating catalog, graph, tree, detail, and page concerns.
- Keep the frontend asset surface simple and build-free in v1.
- Do not introduce a Node toolchain for v1.
- Do not modify existing connector execution paths.
- Do not broaden into preview, polling, or run execution.

## 4. Layered Implementation Shape

The v1 review surface should be implemented in five layers.

### 4.1 Route Layer

Responsibilities:

- expose read-only review endpoints
- expose the review page route
- validate and route request parameters
- avoid embedding review construction logic directly in route handlers

### 4.2 Review Service Layer

Responsibilities:

- discover reviewable NRC APS runs
- build the canonical and run-specific graph payloads
- build the filesystem tree payload
- build the details drawer payload
- classify warnings, mismatches, and disabled-run reasons

### 4.3 Schema Layer

Responsibilities:

- define typed response contracts for the review routes
- keep review payloads separate from existing connector schemas
- prevent the page/controller code from depending on ad hoc dict shapes

### 4.4 UI Shell Layer

Responsibilities:

- serve the HTML shell for the review page
- load the run selector
- render the view toggle
- coordinate diagram pane, tree pane, and right-side details drawer

### 4.5 Static Asset Layer

Responsibilities:

- provide CSS for layout and interaction states
- provide browser-side controller logic
- provide vendored rendering assets for Mermaid and pan/zoom behavior

## 5. Exact Existing Files To Modify

Only these existing repo files should be touched for the first implementation slice unless a repo-confirmed blocker appears.

### 5.1 `backend\main.py`

Planned responsibility:

- mount the review UI static assets
- expose the review page route if not delegated entirely through an imported page/router helper

Expected change class:

- narrow additive import(s)
- narrow additive route/mount registration

### 5.2 `backend\app\api\router.py`

Planned responsibility:

- include the additive read-only NRC APS review router

Expected change class:

- narrow additive import
- narrow additive router include or route registration

No other existing product files should be modified in the first implementation slice unless the repo proves a concrete integration blocker.

## 6. Exact New Backend Files To Add

These are the planned new backend files for v1.

### 6.1 Route And Schema Files

- `backend\app\api\review_nrc_aps.py`
  - read-only route handlers for selector, overview, tree, and details
- `backend\app\schemas\review_nrc_aps.py`
  - Pydantic response models for the review API

### 6.2 Review Service Files

- `backend\app\services\review_nrc_aps_catalog.py`
  - run discovery, latest-run selection, disabled-run classification
- `backend\app\services\review_nrc_aps_runtime.py`
  - runtime root discovery, allowlist enforcement, path normalization
- `backend\app\services\review_nrc_aps_graph.py`
  - canonical graph registry consumption and run-specific node mapping
- `backend\app\services\review_nrc_aps_tree.py`
  - strict filesystem tree construction bounded to review-safe roots
- `backend\app\services\review_nrc_aps_details.py`
  - details drawer model construction for node selections and file selections
- `backend\app\services\review_nrc_aps_overview.py`
  - composition layer that returns the ready-to-serve overview payloads

### 6.3 UI Shell Files

- `backend\app\review_ui\page.py`
  - helper(s) for the review page HTML response if desired

### 6.4 Static Asset Files

- `backend\app\review_ui\static\index.html`
- `backend\app\review_ui\static\review.css`
- `backend\app\review_ui\static\review.js`
- `backend\app\review_ui\static\vendor\mermaid.min.js`
- `backend\app\review_ui\static\vendor\svg-pan-zoom.min.js`
- `backend\app\review_ui\static\vendor\THIRD_PARTY_NOTICES.md`

## 7. Exact New Test Files To Add

The first implementation slice should add focused tests that map directly to the review modules.

- `backend\tests\test_review_nrc_aps_catalog.py`
- `backend\tests\test_review_nrc_aps_graph.py`
- `backend\tests\test_review_nrc_aps_tree.py`
- `backend\tests\test_review_nrc_aps_details.py`
- `backend\tests\test_review_nrc_aps_api.py`
- `backend\tests\test_review_nrc_aps_page.py`

These tests should use the verified isolated runtime fixture under:

- `backend\app\storage_test_runtime\lc_e2e\20260327_062011`

## 8. File Ownership And Module Boundaries

To avoid implementation sprawl, each new module should own one concern.

### 8.1 `review_nrc_aps_catalog.py`

Owns:

- NRC APS run discovery
- default-run selection
- disabled-run reason classification

Must not own:

- tree construction
- Mermaid generation
- details extraction

### 8.2 `review_nrc_aps_runtime.py`

Owns:

- review-root discovery
- allowlisted path guards
- runtime-relative path normalization
- file existence helpers

Must not own:

- DB run listing queries
- graph composition

### 8.3 `review_nrc_aps_graph.py`

Owns:

- canonical node/edge registry loading
- general-view projection
- run-specific node materialization
- stage state and warning overlays

Must not own:

- filesystem traversal
- HTML rendering

### 8.4 `review_nrc_aps_tree.py`

Owns:

- strict filesystem tree model
- tree ids
- expansion and auto-reveal support metadata

Must not own:

- run discovery
- graph stage classification

### 8.5 `review_nrc_aps_details.py`

Owns:

- node details drawer payload
- file details drawer payload
- small structured summaries by artifact class

Must not own:

- direct page layout logic

### 8.6 `review_nrc_aps_overview.py`

Owns:

- route-facing composition of catalog, graph, tree, and details dependencies
- top-level overview payload assembly

Must not own:

- raw filesystem traversal details
- browser-specific rendering code

## 9. UI Composition Plan

The first UI should be composed from four browser-side modules inside `review.js`.

- API client
  - fetches selector, overview, tree, and details payloads
- state store
  - tracks selected run, view mode, selected node, selected file, and reveal state
- diagram renderer
  - renders Mermaid output and wires click events back to canonical node ids
- tree renderer
  - renders the strict filesystem tree and reveal state
- details renderer
  - renders the right-side details drawer
- page controller
  - coordinates initial load, default-run selection, disabled-pane behavior, and cross-highlighting

These may live in one physical `review.js` file in v1, but the code should still be structured into these logical modules.

## 10. Routing Plan

The implementation should reserve these namespaces.

### 10.1 UI Namespace

- `/review/nrc-aps`

### 10.2 API Namespace

- `/api/v1/review/nrc-aps/runs`
- `/api/v1/review/nrc-aps/pipeline-definition`
- `/api/v1/review/nrc-aps/runs/{run_id}/overview`
- `/api/v1/review/nrc-aps/runs/{run_id}/tree`
- `/api/v1/review/nrc-aps/runs/{run_id}/nodes/{node_id}`
- `/api/v1/review/nrc-aps/runs/{run_id}/files/{file_id}`

The file-details endpoint remains metadata-only in v1.

## 11. Assets And Serving Boundaries

- Serve the review page and its assets from the existing backend app.
- Keep all review assets local to the repo.
- Do not depend on CDN assets in v1.
- Do not introduce npm, Vite, Webpack, or a TypeScript build step in v1.

## 12. Explicit Non-Goals For The First Implementation Slice

The first slice should not:

- modify `project6.ps1`
- modify connector execution services
- modify gate tools
- add run execution buttons
- add preview/download behavior
- add live polling
- add a curated alternative tree mode
- generalize beyond NRC APS

## 13. Implementation Order

1. add schema models
2. add review runtime and catalog services
3. add graph, tree, and details services
4. add read-only review router
5. add review UI shell and static assets
6. wire `backend\main.py` and `backend\app\api\router.py`
7. add focused tests
8. verify against the golden runtime fixture

## 14. Completion Standard

This blueprint is satisfied only when an implementer can answer all of the following without inventing new structure:

- which existing files should be edited
- which new files should be created
- which module owns each concern
- which routes should exist
- which layers should remain untouched
- which tests should be added

