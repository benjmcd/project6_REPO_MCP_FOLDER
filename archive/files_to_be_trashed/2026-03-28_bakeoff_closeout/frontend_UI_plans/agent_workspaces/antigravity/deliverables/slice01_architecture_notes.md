# Slice 01 Architecture Notes

## Layered Design

Implementation follows a strictly decoupled 5-layer backend pattern:

1.  **Route Layer**: `backend/app/api/review_nrc_aps.py`.
    -   Handles FastAPI routing, DI, and Pydantic model response serialization.
2.  **Service Layer**: Modular services in `backend/app/services/`.
    -   **Catalog**: Logic for discovering reviewable runs.
    -   **Runtime**: Implements path-safety guards and run-root normalization.
    -   **Graph**: Registry-based canonical pipeline graph and artifact-state projection.
    -   **Tree**: Bounded recursive filesystem tree traversal.
    -   **Details**: Construction of structured metadata and warnings for nodes/files.
3.  **Composition Layer**: `ReviewOverviewService` coordinates the graph, tree, and selectors for unified UI state.
4.  **Schema Layer**: `backend/app/schemas/review_nrc_aps.py`.
    -   Central source of truth for the API contract.
5.  **UI Shell Layer**: `backend/app/review_ui/`.
    -   Vanilla JS/CSS, backend-served to meet the zero-Node toolchain constraint.

## Module Boundaries

-   **Backend Independence**: The review services are designed to be independent of the main data persistence layer (SQLAlchemy) where possible, relying on filesystem artifacts for run state.
-   **No-Build UI**: All UI assets are served directly from the backend as static files. The JavaScript uses standard browser APIs and avoids build-time dependencies.
-   **Security Boundaries**: `ReviewRuntimeService` acts as a central guard for all filesystem access, preventing path traversal outside of authorized review roots.
