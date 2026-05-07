# Qualitative APS Rendered Downstream UI Freeze

Status: planning-only implementation-entry freeze for a future bounded rendered `/review/layer3` qualitative APS package/downstream UI slice after PR `#720`.

This document does not implement UI behavior, backend behavior, routes, DTOs, models, migrations, source handling, package mutation, connector dispatch, provider/public URLs, RAG/vector retrieval, full mockup activation, hidden LLM planning, or auth/security behavior. It selects only the next rendered UI planning boundary over the already-live qualitative APS backend/API chain.

## Current Live Boundary

Current `project6-origin/main` after PR `#720` admits these backend/API qualitative APS steps for one standalone `aps_content_document` source:

- `single_aps_doc_qualitative_pass` through result review;
- `qual_aps_package_review_preview_only`;
- `qual_aps_package_construction_commit_entry`;
- `qual_aps_package_review_submit_entry`;
- `qual_aps_handoff_export_prepare_entry`;
- `qual_aps_aps_handoff_dispatch_entry`;
- `qual_aps_external_export_download_prepare_deliver`.

Current main still does not admit rendered qualitative package/downstream controls. Existing rendered `/review/layer3` controls are server-state driven and already include associated-cohort package, handoff, APS handoff, external readiness, delivery, and signed-reference surfaces, but qualitative APS downstream activation must not be inferred from those surfaces without an explicit rendered UI freeze and proof.

## Selected Future Boundary

Selected future mode: `qual_aps_rendered_downstream_existing_controls_only`.

The future implementation may adapt the existing rendered `/review/layer3` workbench to present and drive only the already-live qualitative APS backend/API package/downstream steps listed above. It must use server-authoritative state and existing API endpoints; it must not introduce a raw mixed manifest picker, upload control, directory picker, source adapter registry, provider URL control, connector/destination selector, RAG/vector control, full mockup control, hidden LLM control, or auth/security behavior.

The implementation may use API/test-harness setup to create deterministic admitted APS source authority and reach the latest supported server state before opening `/review/layer3`. The rendered proof must not imply that a human-facing raw mixed corpus manifest workflow exists.

## Allowed UI Surfaces

A future implementation governed by this freeze may touch only:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.css`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/tests/test_layer3_page.py` or other narrow page/static tests;
- `e2e/layer3-workbench.spec.js`;
- `e2e/layer3-handoff.spec.js`;
- `e2e/layer3-helpers.js`;
- this UI freeze/contract pack, progress/proof manifests, and the progress checker.

Backend service/API changes are not admitted by this freeze. If the rendered implementation proves a missing backend field, route, DTO, model, migration, or runtime behavior is required, stop and create a separate backend/API freeze.

## Required UI Gating

Rendered controls may become enabled only when server state proves the exact qualitative APS authority chain:

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

Any future rendered implementation must be proven under the relevant current `/review/layer3` themes. The minimum proof is:

- headless Chromium Playwright for the qualitative APS rendered path;
- headed Chromium Playwright for the same path;
- evidence that theme persistence, focus states, disabled states, status badges, panels, and responsive layout do not regress for the touched controls;
- no text overlap or unstable resizing in the touched panels at the existing tested desktop/mobile breakpoints;
- no theme-specific controls or state authority that diverges from server state.

If no rendered CSS/theme files change, the implementation still needs headed and headless proof that the newly activated qualitative controls render correctly inside existing themes.

## Explicit Non-Goals

This freeze does not admit:

- new backend endpoints, DTOs, models, migrations, or runtime services;
- helper/service extraction;
- raw ingestion, local upload, local-directory ingestion, broad file upload, web connector retrieval, or source adapter registry behavior;
- RAG/vector retrieval or broad qualitative/hybrid/cross-document execution;
- provider/public URLs, signed URLs for qualitative APS, object-store ACLs, external connector invocation, connector runs, destination writes, or destination selection;
- package payload mutation, reconstruction, supersession, amendment, replacement artifact generation, or package row reuse outside the already-live qualitative construction boundary;
- no frontend-only durable authority, browser-local workflow truth, or full mockup activation;
- hidden LLM planning or prompt/model controls;
- auth/security behavior changes.

## Required Proof For Future Implementation

A future implementation PR governed by this freeze must prove:

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
