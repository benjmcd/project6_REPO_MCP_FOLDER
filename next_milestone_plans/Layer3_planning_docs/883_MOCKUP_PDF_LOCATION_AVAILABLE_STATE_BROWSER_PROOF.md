# 883 - Mockup PDF Location Available-State Browser Proof

## Status

Status: branch-local available-state browser proof and rendered read-only control extension for `prove_mockup_pdf_location_projection_available_state_browser_fixture_without_runtime_widening`.

Proof doc: `883_MOCKUP_PDF_LOCATION_AVAILABLE_STATE_BROWSER_PROOF.md`.

Predecessor sync doc: `882_MOCKUP_PDF_LOCATION_PROJECTION_FREEZE_CURRENT_MAIN_SYNC.md`.

Implementation branch: `codex/l3-pdf-proof`.

Current-main checkpoint before proof: `fad74dc39ec686b03ec42e0c768d5c96d7c374d6`.

Implemented proof action: `prove_mockup_pdf_location_projection_available_state_browser_fixture_without_runtime_widening`.

Selected target: `mockup_pdf_location_projection_read_only`.

Rendered surface: `/review/layer3` `#mockup-pdf-location-projection`.

Route/state contract: existing `GET /api/v1/layer3/session/{session_id}` and `State.sessionSummary.pdf_location_projection`.

Backend authority: `backend/app/services/layer3_pdf_location.py`.

Runtime behavior introduced by this proof: `false`.

Backend behavior introduced by this proof: `false`.

Route/API/DTO/model/migration/service behavior introduced by this proof: `false`.

Rendered behavior introduced by this proof: `true`.

Single mockup screen server-authoritative activation introduced by this proof: `false`.

Full mockup program activation introduced by this proof: `false`.

## Canonical Source Of Truth

The canonical source of truth remains the existing server-owned PDF-location session-summary projection:

- schema id: `layer3.pdf_location_projection.v1`;
- named runtime use case: `pdf_location_from_aps_content_document_citation`;
- server authority contract: `aps_content_document_chunk_page_refs_and_citation_highlight_spans`;
- route: existing `GET /api/v1/layer3/session/{session_id}`;
- state field: `State.sessionSummary.pdf_location_projection`;
- backend service: `backend/app/services/layer3_pdf_location.py`.

Mockup screenshots, browser local storage, raw PDF bytes, output payload refs, diagnostics refs, provider/object-store URLs, local paths, and frontend-only durable state remain non-authoritative.

## Implementation

This pass adds only a read-only rendered extension and browser proof:

- `backend/app/review_ui/static/layer3.js` now renders the server-supplied citation highlight-span count for each available `pdf_location_projection.location_items[]` entry;
- `backend/tests/test_layer3_page.py` tightens the static asset contract for the highlight-span count renderer;
- `e2e/layer3-workbench.spec.js` adds an available-state browser fixture for `State.sessionSummary.pdf_location_projection`;
- no backend route, DTO, model, migration, service behavior, source behavior, package behavior, connector/destination behavior, provider URL behavior, RAG/vector behavior, auth/security behavior, browser-storage authority, or frontend-only durable authority is introduced.

The rendered extension is intentionally limited to data already present in the server projection: page label, chunk id, bounded text preview, and `highlight_spans.length`.

## Browser Proof

The focused browser proof verifies:

- `#mockup-pdf-location-projection` renders `data-projection-state="available"` from `State.sessionSummary.pdf_location_projection.available === true`;
- the panel renders page label `Page 4`;
- the panel renders chunk id `chunk-pdf-location-1`;
- the panel renders the bounded text preview;
- the panel renders `2 citation highlight spans`;
- the unavailable state still fails closed with `pdf_location_highlight_authority_missing`;
- the panel has no buttons, inputs, selects, textareas, or links;
- no raw PDF blob, PDF byte download, output payload ref, diagnostics ref, provider/object-store URL, local path, browser-owned authority, or frontend-only durable authority string is rendered;
- no PDF-location durable browser storage key is created;
- no package mutation, source mixed-corpus materialization, source-directory scan, connector handoff, provider URL, or execution-start request is made by the proof.

## Validation

Local focused validation passed before this proof record:

- `node --check ./backend/app/review_ui/static/layer3.js`;
- `python -m pytest ./backend/tests/test_layer3_page.py::test_layer3_static_assets_are_mounted -q`;
- `npx playwright test ./e2e/layer3-workbench.spec.js --grep "Layer 3 mockup PDF-location projection renders available server state without runtime widening" --project=chromium`.

Required final validation before merge:

- `python ./tools/l3-progress-check.py`;
- JSON validation for `next_milestone_plans/layer3_progress_manifest.json`;
- JSON validation for `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- focused backend tests for PDF-location/static page contracts;
- focused headless Chromium proof;
- focused headed Chromium proof;
- `git diff --check`.

## Boundary

This proof does not admit a new route, DTO field beyond the existing `pdf_location_projection`, model, migration, production service behavior, raw PDF blob streaming, PDF byte download, raw output payload ref exposure, diagnostics ref exposure, provider/object-store URL exposure, local path exposure, browser-owned PDF authority, new buttons/submit controls, write request, source expansion, package mutation, connector/destination dispatch, provider URL behavior, RAG/vector behavior, hidden LLM planning, auth/security behavior, browser-storage authority, frontend-only durable authority, single mockup screen server-authoritative activation, or full mockup program activation.

## Next Posture

The next exact posture is `current_main_sync_mockup_pdf_location_available_state_browser_proof`.
