# Slice 01 Implementation Plan

## 1. Concise Implementation Plan
This slice will implement a read-only review UI for NRC APS pipeline runs. The backend will serve additive API endpoints using FastAPI and static assets without a Node toolchain. The review system will rely on hybrid DB/API and runtime artifact authority to list reviewable runs, project run results onto a canonical node graph, and map filesystem structures strictly bounded to allowed review roots. The UI will use a left-pane graph built with Mermaid, a right-pane strict tree view, and a side drawer for node/file details displaying context-aware payloads.

## 2. Exact Files to Modify
- `backend/main.py`: Additive mount for static assets and HTML page routing.
- `backend/app/api/router.py`: Additive include for the read-only review router.

## 3. Exact New Files to Add
**Routes & Schemas**
- `backend/app/api/review_nrc_aps.py`
- `backend/app/schemas/review_nrc_aps.py`

**Review Services**
- `backend/app/services/review_nrc_aps_catalog.py`
- `backend/app/services/review_nrc_aps_runtime.py`
- `backend/app/services/review_nrc_aps_graph.py`
- `backend/app/services/review_nrc_aps_tree.py`
- `backend/app/services/review_nrc_aps_details.py`
- `backend/app/services/review_nrc_aps_overview.py`

**UI Shell & Static Assets**
- `backend/app/review_ui/page.py`
- `backend/app/review_ui/static/index.html`
- `backend/app/review_ui/static/review.css`
- `backend/app/review_ui/static/review.js`
- `backend/app/review_ui/static/vendor/mermaid.min.js`
- `backend/app/review_ui/static/vendor/svg-pan-zoom.min.js`
- `backend/app/review_ui/static/vendor/THIRD_PARTY_NOTICES.md`

**Tests**
- `backend/tests/test_review_nrc_aps_catalog.py`
- `backend/tests/test_review_nrc_aps_graph.py`
- `backend/tests/test_review_nrc_aps_tree.py`
- `backend/tests/test_review_nrc_aps_details.py`
- `backend/tests/test_review_nrc_aps_api.py`
- `backend/tests/test_review_nrc_aps_page.py`

## 4. Assumptions
- The golden runtime at `backend/app/storage_test_runtime/lc_e2e/20260327_062011/` is structurally intact, and its `.json` summaries cleanly express the properties assumed by the specs.
- Mismatches (e.g., between API state and artifacts on disk) must result in explicitly flagged warning states rendered cleanly on nodes or files, rather than throwing hard 500s or collapsing paths.
- The repository runtime environment allows mounting static UI files directly via `backend/main.py` without conflicting with existing namespaces or tooling.

## 5. Likely Blockers or Risk Areas
- **Mermaid Interactivity Limitations**: Tying diagram click events back to stable node payloads from svgs nested via `svg-pan-zoom` will require careful event delegation.
- **Tree Traversal and Guarding Constraints**: Keeping the tree traversal bounded mathematically so that relative pathing doesn't permit accessing unrelated files in `backend/` could prove prickly.
- **Node Multiplicity Consistency**: Managing the exact canonical counts and branching constraints logic for upstream vs downstream nodes without inadvertently deriving states solely from filenames requires robust schema adherence.

## 6. Scope Confirmation Statement
I confirm I can stay strictly within the frozen scope. I will remain actively within the bounds of read-only reviewability, maintaining NRC APS specificity, steering clear of any CDN/Node.js/Vite adoption, honoring the 5-layer backend pattern, and deploying solely backend-served additive interaction structures.
