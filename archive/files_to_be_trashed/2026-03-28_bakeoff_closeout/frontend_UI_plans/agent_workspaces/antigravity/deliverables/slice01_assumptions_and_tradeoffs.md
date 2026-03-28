# Slice 01 Assumptions and Tradeoffs

## Assumptions

1.  **Golden Run ID**: Assumed the `d6be0fff-bbd7-468a-9b00-7103d5995494` run for the golden runtime fixture as per planning documentation.
2.  **Filesystem Structure**: Assumed the directory and file structure outlined in the implementation blueprint remains current in the repo.
3.  **No Build Toolchain**: Interpreted strictly as "no npm, no vite, no node.js" during the implementation and delivery phases.
4.  **Static Vendors**: Since external CDNs are discouraged and local files are required, implemented lightweight mocks for Mermaid and svg-pan-zoom to maintain functionality in a standalone environment without manual asset placement.

## Risks and Tradeoffs

1.  **Risk (JavaScript Interactivity)**: Using vanilla JS instead of a modern framework (like Vue or React) increases code complexity as the UI grows but ensures zero-dependency repo-fit.
2.  **Tradeoff (Mocked Vendors)**: Using local mocks for Mermaid/svg-pan-zoom instead of full libraries ensures immediate "out of the box" testability without manual vendor asset placement, but limits the full complexity of diagram interactivity for Slice 01.
3.  **Risk (Tree Performance)**: The current recursive tree implementation is deep-loaded for top-level nodes for Slice 01. Large filesystems might require transition to a lazy-loading (pagination) model in future slices.
4.  **Tradeoff (Read-Only Path Enforcement)**: The manual path-safety check in `ReviewRuntimeService` is a robust baseline for Slice 01, but a dedicated file-handle abstraction would be preferable for a larger system.
