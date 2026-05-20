# 884 - Mockup PDF Location Available-State Browser Proof Current-Main Sync

## Status

Status: current-main proof/control sync for `prove_mockup_pdf_location_projection_available_state_browser_fixture_without_runtime_widening`.

Sync doc: `884_MOCKUP_PDF_LOCATION_AVAILABLE_STATE_BROWSER_PROOF_CURRENT_MAIN_SYNC.md`.

Proof doc: `883_MOCKUP_PDF_LOCATION_AVAILABLE_STATE_BROWSER_PROOF.md`.

Proof PR: `#1497`.

Proof branch: `codex/l3-pdf-proof`.

Proof branch commit: `2db04d7277cceb443a53dc18b9d110a984c04996`.

Proof merge commit: `dbbd021e4229f9bbcc033f8470b59825c96329fd`.

Synced result: `current_main_synced_mockup_pdf_location_available_state_browser_proof`.

Runtime behavior introduced by this sync: `false`.

Backend behavior introduced by this sync: `false`.

Route/API/DTO/model/migration/service behavior introduced by this sync: `false`.

Rendered behavior introduced by this sync: `false`.

Single mockup screen server-authoritative activation introduced by this sync: `false`.

Full mockup program activation introduced by this sync: `false`.

## Current-Main Authority

Current `main` now includes the bounded mockup PDF-location available-state browser proof from PR `#1497`:

- rendered surface: `/review/layer3` `#mockup-pdf-location-projection`;
- route/state contract: existing `GET /api/v1/layer3/session/{session_id}` and `State.sessionSummary.pdf_location_projection`;
- backend authority: `backend/app/services/layer3_pdf_location.py`;
- schema id: `layer3.pdf_location_projection.v1`;
- named runtime use case: `pdf_location_from_aps_content_document_citation`;
- server authority contract: `aps_content_document_chunk_page_refs_and_citation_highlight_spans`;
- rendered proof behavior: available-state page labels, chunk ids, bounded text preview, and citation highlight-span counts.

This sync does not introduce additional behavior beyond the merged proof. It does not admit a new route, DTO field beyond `pdf_location_projection`, model, migration, backend service behavior, raw PDF stream, PDF download, source behavior, package behavior, connector/destination behavior, provider URL behavior, RAG/vector behavior, auth/security behavior, browser durable authority, single-screen server-authoritative activation, or full mockup program activation.

## GitHub Proof

PR `#1497` merged at `2026-05-20T02:04:54Z` with merge commit `dbbd021e4229f9bbcc033f8470b59825c96329fd`.

Checks:

- `backend-layer3-api`: `SUCCESS`, `3m24s`;
- `test`: `SUCCESS`, `3m44s`.

Review gate:

- reviewThreads totalCount: `0`;
- PR comments: `0`;
- latest reviews: `0`;
- merge state before merge: `CLEAN`;
- mergeability before merge: `MERGEABLE`.

Post-merge local validation passed on current main at `dbbd021e4229f9bbcc033f8470b59825c96329fd`:

- `python ./tools/l3-progress-check.py`;
- `python -m pytest ./backend/tests/test_layer3_pdf_location.py ./backend/tests/test_layer3_page.py::test_layer3_page_route_serves_workbench_shell ./backend/tests/test_layer3_page.py::test_layer3_static_assets_are_mounted -q --ignore=./test-results`;
- `npx playwright test ./e2e/layer3-workbench.spec.js --grep "Layer 3 mockup PDF-location projection renders available server state without runtime widening" --project=chromium`.

## Boundaries Preserved

Do not render this sync as runtime behavior, backend behavior, route/API/DTO/model/migration/service behavior change, rendered behavior introduced by sync, single mockup screen server-authoritative activation, full mockup program activation, raw PDF blob streaming, PDF byte download, raw output payload ref exposure, diagnostics ref exposure, provider/object-store URL exposure, local path exposure, browser-owned PDF authority, source expansion, package mutation, connector/destination dispatch, provider URL behavior, RAG/vector behavior, hidden LLM planning, auth/security behavior, browser-storage authority, or frontend-only durable authority.

## Next Posture

The next exact posture is `select_next_server_authoritative_mockup_screen_activation_target_after_pdf_location_available_state_sync`.
