# Qualitative APS Rendered Downstream UI Freeze

Status: live bounded rendered `/review/layer3` qualitative APS package/downstream UI runtime for `qual_aps_rendered_downstream_existing_controls_only`.

This document now governs the implemented rendered UI runtime only. It does not admit backend behavior, routes, DTOs, models, migrations, source handling, package mutation, connector dispatch, provider/public URLs, RAG/vector retrieval, full mockup activation, hidden LLM planning, or auth/security behavior beyond the already-live qualitative APS backend/API chain.

## Current Live Boundary

Current `project6-origin/main` admits these backend/API qualitative APS steps for one standalone `aps_content_document` source:

- `single_aps_doc_qualitative_pass` through result review;
- `qual_aps_package_review_preview_only`;
- `qual_aps_package_construction_commit_entry`;
- `qual_aps_package_review_submit_entry`;
- `qual_aps_handoff_export_prepare_entry`;
- `qual_aps_aps_handoff_dispatch_entry`;
- `qual_aps_external_export_download_prepare_deliver`.

Current main now admits rendered qualitative package/downstream controls only through existing `/review/layer3` controls and only after API/test setup has created a server-authoritative approved qualitative APS result-review state. The rendered path drives package preview, package construction commit, package review submit, handoff/export prepare, APS handoff dispatch, and external export/download prepare. Qualitative APS same-origin delivery remains disabled and gated when the server returns `delivery_ui: null` or omits `delivery_ui`.

## Selected Live Boundary

Selected live mode: `qual_aps_rendered_downstream_existing_controls_only`.

The implementation adapts the existing rendered `/review/layer3` workbench to present and drive only the already-live qualitative APS backend/API package/downstream steps listed above. It uses server-authoritative state and existing API endpoints; it does not introduce a raw mixed manifest picker, upload control, directory picker, source adapter registry, provider URL control, connector/destination selector, RAG/vector control, full mockup control, hidden LLM control, or auth/security behavior.

The implementation uses API/test-harness setup to create deterministic admitted APS source authority and reach approved qualitative result review before opening `/review/layer3`. The rendered proof does not imply that a human-facing raw mixed corpus manifest workflow exists.

## Allowed UI Surfaces

The live implementation governed by this freeze may touch only:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_page.py` or other narrow page/static tests;
- `e2e/layer3-workbench.spec.js`;
- `e2e/layer3-handoff.spec.js`;
- `e2e/layer3-helpers.js`;
- this UI freeze/contract pack, progress/proof manifests, and the progress checker.

Backend service/API changes are not admitted by this freeze. If the rendered implementation proves a missing backend field, route, DTO, model, migration, or runtime behavior is required, stop and create a separate backend/API freeze.

## Live UI Gating

Rendered controls become enabled only when server state proves the exact qualitative APS authority chain:

1. selected source class is `aps_content_document`;
2. selected pass is `single_aps_doc_qualitative_pass`;
3. result status is terminal and result review is approved;
4. package preview reports the qualitative APS package-review preview schema and hash;
5. package construction state reports exactly the qualitative package set created by the backend;
6. package review submit state is `package_review_approved`;
7. handoff/export prepare state is `handoff_export_prepared`;
8. APS handoff dispatch state is `aps_handoff_dispatched`;
9. external export/download readiness state is `external_export_download_ready` or `external_export_download_prepared` as appropriate for the control being rendered;
10. the response state includes qualitative APS content, material snapshot, analysis unit, analysis set, output payload, package, handoff, dispatch, and APS bundle identity needed by the backend;
11. no conflicting associated-cohort, dataset-version, analysis-run, provider, connector, destination, source-expansion, RAG/vector, hidden LLM, mockup, or auth/security authority is present.

The browser may generate a fresh `client_request_id` and maintain in-flight state. The browser must not authorize missing authority, repair stale state, infer package hashes, infer APS bundle hashes, rewrite packages, or persist durable workflow truth.

## Required Theme Posture

The rendered implementation is proven under the relevant current `/review/layer3` themes. The minimum proof is:

- headless Chromium Playwright for the qualitative APS rendered path;
- headed Chromium Playwright for the same path;
- evidence that theme persistence, focus states, disabled states, status badges, panels, and responsive layout do not regress for the touched controls;
- no text overlap or unstable resizing in the touched panels at the existing tested desktop/mobile breakpoints;
- no theme-specific controls or state authority that diverges from server state.

No rendered CSS/theme files change in this runtime; headed and headless proof covers the newly activated qualitative controls inside existing themes.

## Explicit Non-Goals

This runtime does not admit:

- new backend endpoints, DTOs, models, migrations, or runtime services;
- helper/service extraction;
- raw ingestion, local upload, local-directory ingestion, broad file upload, web connector retrieval, or source adapter registry behavior;
- RAG/vector retrieval or broad qualitative/hybrid/cross-document execution;
- provider/public URLs, signed URLs for qualitative APS, object-store ACLs, external connector invocation, connector runs, destination writes, or destination selection;
- package payload mutation, reconstruction, supersession, amendment, replacement artifact generation, or package row reuse outside the already-live qualitative construction boundary;
- no frontend-only durable authority, browser-local workflow truth, or full mockup activation;
- hidden LLM planning or prompt/model controls;
- auth/security behavior changes.

## Required Proof For Runtime

The implementation PR governed by this freeze must prove:

- no backend service/API behavior changes unless a separate freeze admits them;
- API/test setup remains separated from rendered UI execution;
- the UI uses only IDs and state returned by server/API setup after that setup step;
- controls remain disabled or absent before server state proves the qualitative APS authority chain;
- request payloads contain only fields admitted by the existing backend/API qualitative APS contracts;
- negative request fields for provider URLs, signed URLs, connector/destination dispatch, source expansion, RAG/vector, hidden LLM, package mutation, mockup, and auth/security remain absent;
- recorded package, handoff, dispatch, readiness, and delivery states render read-only after success;
- associated-cohort and dataset-version rendered flows still pass;
- headed and headless Chromium proof covers the activated qualitative path and touched theme states;
- `python .\tools\l3-progress-check.py`;
- targeted backend/API qualitative APS tests still pass;
- `git diff --check`.

## Stop Conditions

Stop before implementation if any required behavior needs:

- backend service/API route or schema changes;
- a human-facing raw mixed manifest workflow;
- upload/directory/web/RAG/source-adapter controls;
- provider/public URL, signed URL, connector, destination, or object-store behavior;
- package mutation/reconstruction/supersession;
- auth/security behavior changes;
- full mockup activation or frontend-only durable authority.
