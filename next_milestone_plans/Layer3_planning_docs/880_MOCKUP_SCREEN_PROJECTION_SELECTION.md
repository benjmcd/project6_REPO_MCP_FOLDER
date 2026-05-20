# 880 - Mockup Screen Projection Selection

## Status

Status: no-runtime first read-only mockup-screen projection selection after `current_main_synced_source_directory_extension_runtime`.

Selection doc: `880_MOCKUP_SCREEN_PROJECTION_SELECTION.md`.

Predecessor current-main sync doc: `879_SOURCE_DIRECTORY_EXTENSION_RUNTIME_CURRENT_MAIN_SYNC.md`.

Current-main checkpoint before this selection: `d523bf37fc7b0a582995d8522066f343cce4fdd5`.

Selected activation mode: `single_mockup_screen_read_only_projection`.

Selected target: `mockup_pdf_location_projection_read_only`.

Selected route contract: `GET /api/v1/layer3/session/{session_id}`.

Selected response/state contract: `State.sessionSummary.pdf_location_projection`.

Selected rendered surface: `/review/layer3` `#mockup-pdf-location-projection`.

Runtime behavior introduced by this selection: `false`.

Rendered behavior introduced by this selection: `false`.

Backend behavior introduced by this selection: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed next: `false`.

## Current-Main Authority

The selected target already has a complete current-main route/state/rendering contract:

- backend projection owner: `backend/app/services/layer3_pdf_location.py`;
- schema id: `layer3.pdf_location_projection.v1`;
- named runtime use case: `pdf_location_from_aps_content_document_citation`;
- server authority contract: `aps_content_document_chunk_page_refs_and_citation_highlight_spans`;
- durable source authority: `ApsContentDocument` plus `ApsContentChunk.page_start`, `ApsContentChunk.page_end`, `chunk_text_sha256`, and admitted `L3PassRun.output_payload_ref`;
- route: existing `GET /api/v1/layer3/session/{session_id}`;
- session-summary field: `pdf_location_projection: dict[str, Any]`;
- rendered reader: `renderMockupPdfLocationProjection()` in `backend/app/review_ui/static/layer3.js`;
- rendered DOM: `#mockup-pdf-location-projection` under `#mockup-pdf-location-card`;
- static/page proof: `backend/tests/test_layer3_page.py`;
- service proof: `backend/tests/test_layer3_pdf_location.py`;
- browser proof seam: `e2e/layer3-workbench.spec.js`.

This selection does not create a new route, field, model, migration, service, control, button, write path, upload path, connector path, provider URL path, package path, RAG/vector path, auth/security path, browser-storage authority, or frontend-only durable authority.

## Target Ranking

| Rank | Target | Current live authority | Decision |
| ---: | --- | --- | --- |
| 1 | `mockup_pdf_location_projection_read_only` | Existing session-summary projection from `layer3_pdf_location.py`, rendered by `renderMockupPdfLocationProjection()` into `#mockup-pdf-location-projection` | Selected first read-only mockup-screen projection |
| 2 | `mockup_sublayers_ab_projection_read_only` | Static target-state shell plus current `sublayer_visualization` server summary | Later projection candidate; needs a narrower exact mapping |
| 3 | `mockup_sublayer3c_execution_lane_projection_read_only` | Current Analysis Environment projection and Sublayer 3C rendered panels | Already partially covered by previous Analysis Environment rendered projection; not the first literal mockup-screen target |
| 4 | `single_mockup_screen_server_authoritative_activation` | Requires an exact operator action, route, stale-authority, idempotency, and negative-test contract | Deferred |
| 5 | `full_mockup_program_activation` | Crosses source, package, connector, provider, RAG/vector, browser-state, auth/security, and proof boundaries | Rejected for now |

The selected PDF-location target is optimal because it is the smallest literal mockup-screen element that already reads server-owned state and already has fail-closed projection semantics.

## Required Next Freeze

The next freeze must be `freeze_mockup_pdf_location_projection_read_only_before_runtime`.

That freeze must decide whether the next implementation pass is only proof/control sync, a rendered proof hardening pass, or a narrowly bounded available-state browser fixture. It must preserve the current server-authoritative route/state contract and must not add backend runtime behavior unless a specific missing proof gap is found.

The freeze must require:

- exact route: `GET /api/v1/layer3/session/{session_id}`;
- exact state: `State.sessionSummary.pdf_location_projection`;
- exact DOM: `#mockup-pdf-location-projection`;
- exact renderer: `renderMockupPdfLocationProjection()`;
- fail-closed empty-runtime behavior with `available: false`, `state: "unavailable"`, and a blocked reason;
- available-state behavior only from `ApsContentDocument`, `ApsContentChunk`, admitted pass-run output payload, chunk hash matching, page refs, and citation highlight spans;
- leakage proof that raw PDF blobs, provider/object-store URLs, diagnostics refs, local paths, raw payload refs, and browser-owned authority are not rendered;
- no new buttons, submit controls, operation dock steps, writes, package mutation, source expansion, provider URL behavior, connector/destination dispatch, RAG/vector behavior, auth/security behavior, or frontend-only durable state;
- static proof in `backend/tests/test_layer3_page.py`;
- service proof in `backend/tests/test_layer3_pdf_location.py`;
- headed Chromium and headless Chromium proof if rendered behavior is changed or re-proven.

## Non-Admission Boundary

This selection admits no runtime behavior, no rendered behavior, no backend behavior, no route/API/DTO/model/migration/service behavior change, no UI control change, no test behavior change, no single mockup screen server-authoritative activation, no full mockup program activation, no source expansion, no package mutation, no connector/destination dispatch, no provider URL behavior, no RAG/vector widening, no hidden LLM planning, no auth/security behavior, no browser-storage authority, and no frontend-only durable authority.

## Validation Basis

Required validation for this no-runtime selection:

- `python .\tools\l3-progress-check.py`;
- JSON validation for `next_milestone_plans/layer3_progress_manifest.json`;
- JSON validation for `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `git diff --check`.

No browser test is required for this selection because this pass does not change rendered behavior.

## Next Posture

The next exact posture is `freeze_mockup_pdf_location_projection_read_only_before_runtime`.

Do not promote a server-authoritative mockup screen activation or full mockup program activation until this read-only projection freeze is current-main selected, review-cleared, and checker-backed.
