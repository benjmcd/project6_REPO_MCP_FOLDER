# NRC APS Review UI Dependency And Asset Strategy

## 1. Purpose

This document freezes the dependency, asset, and delivery strategy for the NRC APS review UI so the implementation does not accidentally grow a new frontend platform.

## 2. Canonical Source Of Truth

Authority surfaces:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\main.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\requirements.txt`
- the current repo shape, which does not contain a dedicated frontend application scaffold for this surface

Repo-confirmed facts:

- the backend already serves HTTP responses and static files
- the repo already uses Python package management for the backend
- the repo does not require Node tooling for the existing backend app

## 3. Frozen V1 Policy

### 3.1 No New Build Toolchain

Do not add in v1:

- `package.json`
- npm or pnpm
- Vite
- Webpack
- TypeScript compilation
- React or another SPA framework

### 3.2 No CDN Dependencies

Do not load Mermaid, pan/zoom libraries, CSS frameworks, or icon packs from a CDN in v1.

All browser assets should be vendored into the repo.

### 3.3 No New Python Dependency Requirement

Do not add new Python package dependencies for the review UI in v1 unless a repo-confirmed blocker appears.

The backend surface should remain compatible with the current `backend\requirements.txt`.

## 4. Static Asset Strategy

The review UI should be delivered as backend-served static assets.

### 4.1 Planned Asset Paths

- `backend\app\review_ui\static\index.html`
- `backend\app\review_ui\static\review.css`
- `backend\app\review_ui\static\review.js`
- `backend\app\review_ui\static\vendor\mermaid.min.js`
- `backend\app\review_ui\static\vendor\svg-pan-zoom.min.js`
- `backend\app\review_ui\static\vendor\THIRD_PARTY_NOTICES.md`

### 4.2 HTML Strategy

V1 should use a simple static HTML shell.

Do not introduce a templating system unless a concrete backend integration blocker appears.

## 5. Diagram Rendering Strategy

### 5.1 Primary Renderer

Use Mermaid in v1 because:

- it matches the intended visual language
- it supports the conceptual and run-specific graph shapes needed for the first cut

### 5.2 Renderer Boundary

Mermaid is the renderer only.

It is not the source of truth for:

- node ids
- edges
- state
- file mappings
- details behavior

Those must come from the review model and canonical graph registry.

### 5.3 Pan/Zoom Strategy

Use a vendored `svg-pan-zoom` browser asset against the Mermaid-rendered SVG.

If that proves incompatible with a specific Mermaid output, the fallback is:

- a minimal in-house pan/zoom wrapper around the SVG container

The fallback should not trigger a new framework decision.

## 6. Browser Code Structure

Even if `review.js` is one physical file in v1, it should be logically structured into:

- API client
- state store
- Mermaid graph adapter
- pan/zoom adapter
- tree renderer
- details drawer renderer
- page controller

This structure is required for modularity and non-fragility.

## 7. CSS Strategy

The CSS should:

- define the three-pane page layout
- support a cleaner conceptual pipeline view and a denser run-specific view
- support disabled shell states
- support selection/highlight states across diagram and tree
- avoid framework coupling

Do not add a CSS framework in v1.

## 8. Asset Governance Rules

- vendored third-party assets must include provenance and notices
- asset versions should be pinned by the committed files themselves
- browser code should not silently fetch alternate runtime assets from the internet

## 9. Security And Safety Rules

- the browser must never receive arbitrary filesystem browsing capability
- asset loading must stay within the backend-served review UI surface
- file preview remains deferred, so no preview parser stack should be introduced in v1

## 10. Future-Compatible Hooks

These are allowed later without invalidating the v1 strategy:

- JSON/text preview
- safe image preview for visual page PNGs
- curated review-tree mode
- live polling

These are not allowed to distort the initial asset strategy now.

## 11. Completion Standard

The dependency and asset strategy is complete for v1 only if an implementer can answer:

- whether to add a build toolchain
- whether to add npm dependencies
- whether to use CDN assets
- which exact browser assets to vendor
- how Mermaid and pan/zoom fit into the page

The correct v1 answer to the first three questions is `no`.

