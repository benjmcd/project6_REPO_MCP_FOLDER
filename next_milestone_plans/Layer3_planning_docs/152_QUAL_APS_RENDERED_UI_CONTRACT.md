# Qualitative APS Rendered Downstream UI Contract

Status: live UI/state contract paired with `151_QUAL_APS_RENDERED_UI_FREEZE.md`.

This contract specifies the live rendered `/review/layer3` behavior for `qual_aps_rendered_downstream_existing_controls_only`. It admits only existing-control UI activation over already-live qualitative APS backend/API steps and does not admit backend, source, package mutation, connector, provider, RAG/vector, mockup, model/migration, or auth/security expansion.

## Route And State Authority

The UI implementation may use only existing Layer 3 API routes that are already live for the qualitative APS backend/API chain:

- `GET /api/v1/layer3/session/{session_id}`;
- `POST /api/v1/layer3/package/review/preview`;
- `POST /api/v1/layer3/package/review/commit`;
- `POST /api/v1/layer3/package/review/submit`;
- `POST /api/v1/layer3/handoff/export/prepare`;
- `POST /api/v1/layer3/handoff/aps/dispatch`;
- `POST /api/v1/layer3/handoff/export/download/prepare`;
- `POST /api/v1/layer3/handoff/export/download/deliver`.

API/test setup may use existing admitted setup endpoints or test-only helpers to seed deterministic source authority and reach the rendered entry point. Setup remains separate from rendered UI execution.

Server state is the only durable authority. Browser state may cache display data, generate a `client_request_id`, hold in-flight state, and preserve a recovery anchor. Browser state must not create or repair authority.

## Live UI Entry Point

The live implementation starts at the smallest rendered point that proves value without broadening scope:

1. seed or create deterministic admitted `aps_content_document` source authority through existing test/API setup;
2. drive the backend/API qualitative APS path to approved result review;
3. open `/review/layer3`;
4. use only server-returned qualitative APS IDs/state after setup;
5. drive rendered package/downstream controls through package preview, package construction commit, package review submit, handoff/export prepare, APS handoff dispatch, and external export/download prepare;
6. keep qualitative APS same-origin delivery disabled when the server returns `delivery_ui: null` or omits `delivery_ui`;
7. stop before any missing backend/UI control would require new source, provider, connector, package mutation, mockup, auth, model, migration, or broad execution behavior.

The implementation does not imply a human-facing raw mixed manifest UI exists.

## Request Contracts

Rendered requests must be assembled from server-returned state plus operator intent. They must not include:

- local paths, upload references, directory paths, web connector references, RAG/vector index fields, adapter registry fields, prompt/model fields, hidden LLM fields, provider/public URL fields, signed URL fields, connector ids, destination ids, credentials, auth/security fields, mockup fields, package mutation fields, package reconstruction fields, package supersession fields, replacement package fields, or browser-only durable authority fields.

Package preview requests may include only the existing qualitative APS preview authority fields admitted by the backend.

Package commit requests may include only the qualitative preview hash, package review authority, and existing package commit intent admitted by the backend.

Package submit requests may include only the constructed qualitative package-set authority and operator package-review decision admitted by the backend.

Handoff/export prepare requests may include only the qualitative package submit and handoff/export prepare authority admitted by the backend.

APS dispatch requests may include only the qualitative handoff/export prepare and APS dispatch authority admitted by the backend.

External export/download prepare requests may include only the qualitative APS dispatch, APS bundle, and reference-only prepare authority admitted by the backend. Qualitative APS delivery requests stay disabled unless a server-authoritative `delivery_ui` object explicitly proves same-origin delivery eligibility; delivery must not request provider/public URL, signed URL, connector dispatch, destination write, or package rewrite behavior.

## Rendered States

The UI distinguishes these states for every activated qualitative APS downstream panel:

- unavailable because required upstream server state is absent;
- ready because server state marks the next qualitative APS step available;
- submitting one in-flight request;
- recorded/succeeded, rendered read-only from server response or refreshed session state;
- blocked because server returned a fail-closed blocker;
- conflict/stale authority because server rejected mismatched state;
- error because the request or refresh failed.

The UI must not treat browser-local state as equivalent to recorded server state after refresh failure. It may show a recovery prompt or local pending/error display, but it must not unlock downstream controls without server authority.

## Delivery UI Gate

Qualitative APS same-origin delivery may be rendered only for the already-live `qual_aps_external_export_download_prepare_deliver` backend/API path and only when server state proves qualitative APS readiness and explicit delivery eligibility for the same-origin APS bundle artifact.

Current qualitative APS external export/download prepare returns or summarizes `delivery_ui: null`; the rendered UI therefore shows `external_export_download_delivery_ui_unavailable`, disables delivery, blocks signed-reference generation with `external_export_download_signed_reference_ui_blocked`, and does not synthesize qualitative delivery readiness. The UI must not enable delivery from `delivery_ui: null`.

## Response-Derived Readiness Contract

The rendered UI may use the successful in-memory response from the immediately preceding server action as the current readiness source for the next rendered control, while the browser refreshes session summary state. This is allowed only when the response contains the server-authored identifiers and hashes needed by the next route.

For this runtime:

- package review submit readiness may use the qualitative package construction commit response to carry `package_review_preview_hash`, `construction_basis_hash`, package ids, refs, and hashes;
- handoff/export prepare readiness may use the package review submit response;
- APS handoff dispatch readiness may use the handoff/export prepare response and may derive `aps_handoff_ready` only from `handoff_export_prepared`, `prepare_record_ref`, `handoff_export_envelope_ref`, and `package_review_submit_record_ref`;
- external export/download prepare readiness may use the APS handoff dispatch response and server summary readiness.

This response-derived readiness is not frontend-only durable authority. It cannot fabricate missing hashes, missing refs, missing package identity, provider fields, connector fields, destination fields, source-expansion fields, package mutation fields, or delivery UI eligibility.

## Theme And Accessibility Contract

The implementation preserves existing theme behavior and proves the touched controls under the current theme set. Required checks:

- stable selectors for every newly activated control and panel;
- disabled, focus, hover, loading, success, blocked, and error states visible in both default and persisted theme contexts when those contexts are currently supported;
- no text overlap, clipping, or layout shift in touched controls across the existing tested desktop/mobile breakpoints;
- no theme-specific state authority or theme-specific request payload differences;
- headed and headless Chromium runs for the same qualitative APS rendered path.

## Negative Invariants

The future UI implementation must keep all of these absent:

- raw ingestion, local upload, local-directory ingestion, web connector retrieval, source adapter registry expansion;
- RAG/vector retrieval, broad qualitative/hybrid/cross-document execution, hidden LLM planning;
- provider/public URLs, signed URLs for qualitative APS unless separately frozen, connector/destination dispatch, connector runs, destination writes;
- package payload mutation, reconstruction, supersession, amendment, replacement package generation, package row reuse outside the admitted construction boundary;
- browser-local durable authority, full mockup activation, auth/security behavior changes;
- backend service/API changes unless separately frozen.

## Required Tests For Runtime

The runtime PR must include:

- focused page/static tests for gating and request payload construction;
- Playwright headless proof for the qualitative APS rendered path;
- Playwright headed proof for the same path;
- regression proof for existing associated-cohort delivery UI authority and dataset-version rendered flow;
- backend/API qualitative APS regression tests for the live endpoints being driven;
- progress checker updates that guard the selected rendered UI contract and stale blocked/future wording;
- `git diff --check`.
