# 882 - Mockup PDF Location Projection Freeze Current-Main Sync

## Status

Status: current-main proof/control sync for `prove_mockup_pdf_location_projection_available_state_browser_fixture_without_runtime_widening`.

Sync doc: `882_MOCKUP_PDF_LOCATION_PROJECTION_FREEZE_CURRENT_MAIN_SYNC.md`.

Freeze doc: `881_MOCKUP_PDF_LOCATION_PROJECTION_FREEZE.md`.

Freeze PR: `#1495`.

Freeze branch: `codex/l3-mockup-pdf-freeze`.

Freeze branch commit: `a81daf632d4f207610a019726df343a1c07c6e0c`.

Freeze merge commit: `e6959479a785a60a20783edc37454f8f740390d5`.

Synced result: `current_main_synced_mockup_pdf_location_projection_freeze`.

Runtime behavior introduced by this sync: `false`.

Rendered behavior introduced by this sync: `false`.

Backend behavior introduced by this sync: `false`.

Route/API/DTO/model/migration/service behavior introduced by this sync: `false`.

Single mockup screen server-authoritative activation introduced by this sync: `false`.

Full mockup program activation introduced by this sync: `false`.

## Current-Main Authority

Current `main` now includes the no-runtime/no-rendered PDF-location projection freeze from PR `#1495`:

- the selected activation mode is `single_mockup_screen_read_only_projection_proof_hardening`;
- the selected target is `mockup_pdf_location_projection_read_only`;
- the selected proof action is `prove_mockup_pdf_location_projection_available_state_browser_fixture_without_runtime_widening`;
- the route contract remains existing `GET /api/v1/layer3/session/{session_id}`;
- the state contract remains `State.sessionSummary.pdf_location_projection`;
- the rendered surface remains `/review/layer3` `#mockup-pdf-location-projection`;
- the backend authority remains `backend/app/services/layer3_pdf_location.py`;
- the schema id remains `layer3.pdf_location_projection.v1`;
- the named runtime use case remains `pdf_location_from_aps_content_document_citation`;
- the server authority contract remains `aps_content_document_chunk_page_refs_and_citation_highlight_spans`.

The current-main freeze does not admit a new route, DTO field, model, migration, production service behavior, PDF stream, source behavior, package behavior, connector/destination behavior, provider URL behavior, RAG/vector behavior, auth/security behavior, browser durable authority, single-screen server-authoritative activation, or full mockup program activation.

## GitHub Proof

PR `#1495` merged at `2026-05-20T01:23:12Z` with merge commit `e6959479a785a60a20783edc37454f8f740390d5`.

Checks:

- `backend-layer3-api`: `SUCCESS`, `3m13s`;
- `test`: `SUCCESS`, `3m35s`.

Review gate:

- reviewThreads totalCount: `0`;
- PR comments: `0`;
- latest reviews: `0`;
- merge state before merge: `CLEAN`;
- mergeability before merge: `MERGEABLE`.

Post-merge local validation passed on current main at `e6959479a785a60a20783edc37454f8f740390d5`:

- `python .\tools\l3-progress-check.py`;
- `python -m pytest .\backend\tests\test_layer3_pdf_location.py .\backend\tests\test_layer3_page.py::test_layer3_page_route_serves_workbench_shell .\backend\tests\test_layer3_page.py::test_layer3_static_assets_are_mounted -q`.

## Boundaries Preserved

Do not render this sync as runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior change, UI control change, executable test behavior change, single mockup screen server-authoritative activation, full mockup program activation, raw PDF blob streaming, PDF byte download, raw output payload ref exposure, diagnostics ref exposure, provider/object-store URL exposure, local path exposure, browser-owned PDF authority, source expansion, package mutation, connector/destination dispatch, provider URL behavior, RAG/vector widening, hidden LLM planning, auth/security behavior, browser-storage authority, or frontend-only durable authority.

## Next Posture

The next exact posture is `prove_mockup_pdf_location_projection_available_state_browser_fixture_without_runtime_widening`.
