# 881 - Mockup PDF Location Projection Freeze

## Status

Status: no-runtime/no-rendered implementation-entry freeze for `prove_mockup_pdf_location_projection_available_state_browser_fixture_without_runtime_widening`.

Freeze doc: `881_MOCKUP_PDF_LOCATION_PROJECTION_FREEZE.md`.

Predecessor selection doc: `880_MOCKUP_SCREEN_PROJECTION_SELECTION.md`.

Current-main checkpoint before this freeze: `1447f12a5566eddad52583937c5bce99d1ffff7c`.

Selected activation mode: `single_mockup_screen_read_only_projection_proof_hardening`.

Selected target: `mockup_pdf_location_projection_read_only`.

Selected proof action: `prove_mockup_pdf_location_projection_available_state_browser_fixture_without_runtime_widening`.

Selected route contract: `GET /api/v1/layer3/session/{session_id}`.

Selected response/state contract: `State.sessionSummary.pdf_location_projection`.

Selected rendered surface: `/review/layer3` `#mockup-pdf-location-projection`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Implementation-entry allowed next: `false` until this freeze is current-main synced.

Full mockup program activation selected: `false`.

Single mockup screen server-authoritative activation selected: `false`.

## Canonical Source Of Truth

The canonical source of truth for this projection is existing server authority only:

- backend projection owner: `backend/app/services/layer3_pdf_location.py`;
- schema id: `layer3.pdf_location_projection.v1`;
- named runtime use case: `pdf_location_from_aps_content_document_citation`;
- server authority contract: `aps_content_document_chunk_page_refs_and_citation_highlight_spans`;
- route: existing `GET /api/v1/layer3/session/{session_id}`;
- session-summary field: `pdf_location_projection: dict[str, Any]`;
- rendered reader: `renderMockupPdfLocationProjection()` in `backend/app/review_ui/static/layer3.js`;
- rendered DOM: `#mockup-pdf-location-projection` under `#mockup-pdf-location-card`;
- service proof: `backend/tests/test_layer3_pdf_location.py`;
- static/page proof: `backend/tests/test_layer3_page.py`;
- current browser proof seam: `e2e/layer3-workbench.spec.js`.

Mockup frames, copied screenshots, browser local storage, browser-only state, raw PDF bytes, raw payload refs, provider/object-store URLs, diagnostics refs, local paths, and operator-entered paths are not authority for this target.

## Audit Result

Current source already contains the route/state/rendered contract selected by doc `880`:

- `backend/app/services/layer3_workbench.py` projects `pdf_location_projection` into `session_summary(...)`;
- `backend/app/api/layer3.py` exposes it through `Layer3SessionSummaryResponse` on `GET /api/v1/layer3/session/{session_id}`;
- `backend/app/review_ui/static/layer3.js` reads only `State.sessionSummary?.pdf_location_projection`;
- `backend/app/review_ui/static/layer3.html` provides `#mockup-pdf-location-projection`;
- `backend/tests/test_layer3_pdf_location.py` covers available-state authority and fail-closed missing/stale/malformed authority;
- `backend/tests/test_layer3_page.py` covers the static rendered contract;
- `e2e/layer3-workbench.spec.js` currently proves the rendered unavailable state.

The remaining gap before any stronger activation claim is available-state browser proof, not missing backend runtime. The next pass should prove that an available server-owned projection renders correctly and redacts forbidden authority, without changing the API, database, production service behavior, source behavior, package behavior, connector behavior, provider behavior, auth/security behavior, or browser durable authority.

## Selected Future Proof Scope

The next implementation/proof pass may only harden proof for the existing read-only projection:

- create or extend a browser fixture that supplies `State.sessionSummary.pdf_location_projection.available === true`;
- prove `#mockup-pdf-location-projection` renders server-authoritative page labels, chunk ids, bounded text preview, and citation highlight-span counts;
- prove the unavailable state remains fail-closed with a blocked reason;
- prove no raw PDF bytes, provider/object-store URLs, diagnostics refs, raw payload refs, local paths, browser-owned PDF authority, or frontend-only durable authority are rendered;
- prove no new buttons, submit controls, operation-dock actions, write requests, source expansion, package mutation, connector dispatch, provider URL behavior, RAG/vector behavior, or auth/security behavior are introduced;
- preserve the existing route/state/DOM/renderer contract exactly.

No backend route, DTO, model, migration, production service, PDF byte stream, source-ingestion behavior, package mutation behavior, connector/destination behavior, provider URL behavior, RAG/vector behavior, auth/security behavior, browser storage authority, or frontend-only durable state may be changed under this freeze.

## Required Future Write Scope

The later proof-hardening pass should be limited to:

- `e2e/layer3-workbench.spec.js`;
- browser fixture helpers already used by that spec, if a fixture helper is required;
- `backend/tests/test_layer3_page.py` only if static contract wording must be tightened;
- progress/proof docs and manifests needed to record the proof.

Any production change outside those files requires a new freeze unless the audit proves this contract is absent on current main.

## No-Go Surface

The future proof pass must not admit:

- a new route;
- a new DTO field beyond the existing `pdf_location_projection`;
- a new model or migration;
- a production service behavior change;
- raw PDF blob streaming;
- PDF byte download;
- raw output payload ref exposure;
- diagnostics ref exposure;
- provider or object-store URL exposure;
- browser-owned authoritative PDF location;
- local upload;
- local directory ingestion;
- arbitrary local path input;
- caller-supplied source path, URL, glob, or recursive flag;
- source adapter registry expansion;
- package mutation or package construction;
- connector or destination dispatch;
- `ConnectorRun` or `ConnectorRunTarget` creation;
- cloud object-store writes;
- RAG/vector retrieval;
- prompt/model/provider qualitative generation;
- hidden LLM planning;
- auth/security behavior change;
- browser-storage authority;
- frontend-only durable state;
- single mockup screen server-authoritative activation;
- full mockup program activation.

## Pressure-Tested Decisions

The `grill-me` decision tree was resolved from repo authority rather than user interruption:

| Question | Answer | Justification |
| --- | --- | --- |
| Is the canonical source of truth the mockup frame? | No | The live contract is the existing session-summary projection from `layer3_pdf_location.py`; mockup assets are visual targets only. |
| Is a new backend implementation needed before proof hardening? | No | The route, state field, service projection, rendered reader, and service/static tests already exist on current main. |
| Is the next pass a server-authoritative mockup-screen activation? | No | The target is still read-only; it has no operator action, write route, idempotency contract, stale-authority recovery, or authorization boundary. |
| Is full mockup activation now adequate? | No | Full-program scope still crosses unresolved source, package, connector, provider, RAG/vector, browser-state, auth/security, and proof boundaries. |
| What is the smallest useful next pass? | Available-state browser proof | Existing browser proof covers unavailable state only; available-state rendering and leakage constraints remain the narrow proof gap. |

## Immediate Milestone

Milestone 1: current-main sync this freeze, then prove the available-state PDF-location rendered projection without runtime widening.

Exit criteria:

- `#mockup-pdf-location-projection` renders an available server projection from `State.sessionSummary.pdf_location_projection`;
- unavailable state remains fail-closed;
- forbidden raw refs, URLs, local paths, PDF bytes, write controls, and browser-owned authority do not render;
- no production backend/API/model/migration/service behavior changes occur;
- headed and headless Chromium proof pass if browser proof files are changed;
- `python .\tools\l3-progress-check.py` passes.

## Mid-Term Milestones

Milestone 2: current-main sync the available-state browser proof.

Milestone 3: decide whether the same PDF-location target has enough operator-action authority for `single_mockup_screen_server_authoritative_activation`; if not, select another single screen/control with a complete action route, durable owner, idempotency, stale-state, authorization, and negative-test contract.

Milestone 4: implement one server-authoritative mockup-screen activation as a bounded workflow only after that exact action contract exists.

Milestone 5: repeat bounded read-only projections and server-authoritative activations until every critical mockup operator journey is mapped, live, intentionally excluded, or blocked by a named unresolved boundary.

## Long-Term Milestones

Milestone 6: resolve remaining source breadth, package mutation, connector/destination, provider URL, qualitative/hybrid/RAG, optional-tool, browser-state, and auth/security blockers as separately frozen server-authoritative lanes.

Milestone 7: run a full mockup activation readiness audit proving every mockup control is one of:

- live and server-authoritative;
- live and read-only projection only;
- intentionally excluded;
- still blocked with a named blocker.

Milestone 8: admit `full_mockup_program_activation` only after the readiness audit proves complete route/state/test/browser/security coverage and no frontend-only durable authority.

## Non-Admission Boundary

This freeze admits no runtime behavior, no rendered behavior, no backend behavior, no route/API/DTO/model/migration/service behavior change, no UI control change now, no test behavior change now, no single mockup screen server-authoritative activation, no full mockup program activation, no source expansion, no package mutation, no connector/destination dispatch, no provider URL behavior, no RAG/vector widening, no hidden LLM planning, no auth/security behavior, no browser-storage authority, and no frontend-only durable authority.

## Validation Basis

Required validation for this freeze:

- `python .\tools\l3-progress-check.py`;
- JSON validation for `next_milestone_plans/layer3_progress_manifest.json`;
- JSON validation for `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `git diff --check`.

No runtime, API, or browser test is required for this freeze because it changes no runtime behavior, route, dependency, session-summary field, rendered UI, browser behavior, or executable test.

## Next Posture

The next exact posture is `current_main_sync_mockup_pdf_location_projection_freeze_then_available_state_browser_proof`.

After that sync, the only admitted proof action is `prove_mockup_pdf_location_projection_available_state_browser_fixture_without_runtime_widening`.
