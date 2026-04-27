# 64 L3 Workbench External Export Download Readiness UI Freeze

## Status

Planning-only UI freeze for a future bounded rendered `/review/layer3` continuation over the already-live Layer 3 external export/download readiness backend/API slice.

This document does not implement UI, backend behavior, browser downloads, public URLs, connector dispatch, destination selection, package mutation, or runtime/schema/source expansion. It admits only the next UI planning boundary: render server-authoritative external export/download readiness and allow one server-gated readiness action over the existing `POST /api/v1/layer3/handoff/export/download/prepare` endpoint.

## Current Live Baseline

Current main already contains these bounded Layer 3 workbench slices:

- package construction and package-review submit;
- handoff/export prepare-only backend/API and rendered `/review/layer3` UI;
- APS handoff dispatch backend/API and rendered `/review/layer3` UI;
- external export/download readiness backend/API from PR #269.

The live external export/download readiness backend/API is still reference-only. It prepares and records server-authoritative readiness state after recorded APS handoff dispatch. It does not create a browser download route, public or signed URL, streamed file response, connector run, destination dispatch, generic downstream dispatch, package mutation, package rebuild, schema migration, source expansion, or full mockup activation.

## Slice Decision

The next admitted planning boundary is a rendered `/review/layer3` UI slice for external export/download readiness, not actual download delivery.

The future implementation may:

- render the server-authoritative `external_export_download` summary from the Layer 3 session response;
- show the current external export/download target and mode as server truth;
- show recorded readiness descriptors read-only after the backend records readiness;
- enable exactly one server-gated `prepare_external_export_download` action only when `external_export_download.available == true`;
- submit only fields already admitted by docs 62/63 and the current backend endpoint;
- render browser download, download URL, connector dispatch, destination selection, and generic downstream dispatch as unavailable or disabled.

The future implementation must not infer readiness from browser-local state. Browser state may cache display and in-flight submission state, but the server remains authoritative for availability, recorded readiness, conflict, and blocker state.

## Governing Backend Contract

The UI must treat the docs 62/63 backend/API contract as authoritative. A future UI implementation may only call:

- `GET /api/v1/layer3/session/{session_id}/summary` or the existing `/review/layer3` session-summary refresh path already used by the page;
- `POST /api/v1/layer3/handoff/export/download/prepare`.

The UI must not call or introduce:

- a browser download route;
- a public or signed URL route;
- file streaming;
- connector-run creation or mutation;
- generic downstream dispatch;
- destination selection;
- package edit, rebuild, mutation, supersession, or amendment routes.

## Required UI Inputs

The rendered control must be driven by server-provided state. The UI may collect only operator-visible decision intent and notes, then submit the existing backend-admitted request fields.

The UI must use server state for:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- result review identity;
- package-review submit identity and approval state;
- handoff/export prepare identity and prepared state;
- APS handoff dispatch identity and dispatched state;
- external export/download readiness availability;
- external export/download target and mode;
- source APS handoff package row identity;
- source artifact reference, hash, and package hash basis;
- downstream disabled flags;
- previous recorded external export/download readiness state, if any.

The UI may generate a fresh `client_request_id` for each submit attempt. It must not reuse a prior `client_request_id` after the browser starts a distinct submit attempt.

## Required UI States

The future UI must distinguish these presentation states without treating them as independent backend authority:

- unavailable because upstream package/review/handoff/APS dispatch gates are incomplete;
- ready because the server reports `external_export_download.available == true`;
- submitting one in-flight `prepare_external_export_download` request;
- prepared or recorded, shown read-only from server response or refreshed session summary;
- conflict or stale-authority failure returned by the backend;
- blocked/error failure returned by the backend.

The UI must preserve the existing package-review submit, handoff/export prepare, and APS handoff dispatch panels and state progression. External export/download readiness UI must be downstream of recorded APS handoff dispatch.

## Required Request Shape

The future UI must submit only the request fields admitted by docs 62/63 and current backend behavior. At minimum, the request must include the server-confirmed authority basis required by the backend and:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- package-review submit record reference and approved state;
- handoff/export prepare record reference and prepared state;
- APS handoff dispatch record reference and dispatched state;
- source APS handoff package identity and package basis;
- external export/download target and mode;
- `operator_decision == prepare_external_export_download`;
- `client_request_id`.

The UI must fail closed client-side before submit when the server summary does not provide the required authority basis, but the backend remains the final authority and must still revalidate all request claims.

## Required Display After Success

After a successful response or refreshed recorded state, the UI must display reference-only readiness descriptors, including only server-returned identifiers, package kinds, package refs, payload refs, payload hashes, state names, target/mode, disabled downstream flags, and next-state guidance.

The UI must not display or manufacture:

- package payload bodies;
- generated external files;
- browser download links;
- public URLs;
- signed URLs;
- connector-run IDs;
- destination choices;
- editable package payloads;
- rewritten content.

## Disabled Downstream Presentation

The UI must render the following as unavailable or disabled:

- browser download;
- download URL;
- public or signed URL generation;
- file streaming;
- external export delivery;
- connector dispatch;
- destination selection;
- generic downstream dispatch.

Disabled downstream presentation must not be a control that can submit a live request. It must be a server-state explanation only.

## Explicit Non-Goals

This governance packet does not admit:

- actual browser download route or control;
- public URL generation;
- signed URL generation;
- file streaming;
- connector dispatch or connector-run handling;
- destination selection;
- generic downstream dispatch;
- package amendment, rebuild, supersession, mutation, copying, or reconstruction;
- additional reconciliation rows;
- additional package rows beyond already admitted contracts;
- `AnalysisArtifact` expansion;
- schema migration;
- runtime DB widening;
- source expansion;
- local upload or local-directory ingestion;
- qualitative, hybrid, RAG, or vector execution;
- execution-start expansion beyond already admitted work;
- full mockup activation.

## Stop Conditions For Future Implementation

A future implementation must stop and create a narrower prerequisite backend/API or governance slice if the UI cannot render the panel from current session-summary state without:

- duplicating backend business logic in browser code;
- inferring missing authority from local state;
- requiring new backend rows or schema;
- creating downloadable artifacts or URLs;
- mutating package payloads;
- introducing connector dispatch or destination selection.

## Proof Required Before Implementation Can Land

A future implementation PR must prove:

- the panel remains hidden or disabled until the server reports external export/download readiness availability;
- exactly one readiness action is enabled and it posts only to `/api/v1/layer3/handoff/export/download/prepare`;
- the request contains only backend-admitted fields;
- held, stale, conflict, and blocked responses render as server truth;
- recorded readiness renders read-only after success;
- browser download, download URL, connector dispatch, destination selection, and generic dispatch remain unavailable;
- existing package-review submit, handoff/export prepare, and APS handoff dispatch UI behavior does not regress.

Expected validation for that future implementation includes focused Layer 3 API tests, page/static tests, JavaScript syntax checks, and both headless and headed Chromium checks for `/review/layer3`.
