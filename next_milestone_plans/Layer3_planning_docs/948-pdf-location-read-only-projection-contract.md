# 948 - PDF Location Read-Only Projection Contract

## Status

Status: branch-local activation-readiness projection contract for `pdf_location_read_only_live_projection_contract`.

Predecessor sync: `947-output-review-package-handoff-activation-current-main-sync.md`.

Current main authority: `project6-origin/main` at `f2c6100d904dda20b51fc3b467db5ed160136792` (`f2c6100d Sync output handoff activation contract`).

Implementation branch: `codex/l3-pdf-location-projection-contract`.

Selected projection slice: `pdf_location_read_only_live_projection_contract`.

## Scope

This slice makes the existing PDF-location mockup journey explicit as a read-only live projection contract. It does not promote PDF-location to an interactive journey.

The contract is grounded in:

- `State.sessionSummary.pdf_location_projection`;
- `layer3.pdf_location_projection.v1`;
- `aps_content_document_chunk_page_refs_and_citation_highlight_spans`;
- `#mockup-pdf-location-projection`.

## Non-Admission Boundary

This slice does not admit browser-owned PDF-location authority, raw PDF blob streaming, PDF byte download, provider or object-store URL exposure, frontend-only durable authority, route/model/migration changes, connector/provider writes, or full mockup program activation.

## Verification

Targeted verification for this branch must prove:

- the activation-readiness bootstrap contract exposes `selected_projection_slice`;
- the `pdf_location` journey remains `read_only`;
- the rendered activation-readiness dashboard shows the PDF-location projection contract;
- the existing PDF-location projection continues to render available and unavailable server state without controls, links, local storage authority, or forbidden URL/file/path leakage.

## Next Posture

After this branch is merged and synced to current main, select the next still-read-only projection journey only from current-main evidence. The likely candidates are Sublayers 3A/3B and Sublayer 3C execution lanes; neither should be promoted to interactive without a separately selected server-owned control.
