# 68 L3 Workbench External Export Download Delivery UI Freeze

## Status

Planning-only UI freeze for a future bounded rendered `/review/layer3` continuation over the already-live Layer 3 same-origin external export/download delivery backend/API slice from PR #278.

This document does not implement UI, backend behavior, public URLs, signed URLs, connector dispatch, destination selection, generic downstream dispatch, package mutation, runtime/schema/source expansion, or full mockup activation. It admits only the next UI planning boundary: render a server-gated browser download control that invokes the existing `POST /api/v1/layer3/handoff/export/download/deliver` endpoint after the server proves recorded delivery readiness.

## Current Live Baseline

Current main already contains these bounded Layer 3 workbench slices:

- package construction and package-review submit;
- handoff/export prepare-only backend/API and rendered `/review/layer3` UI;
- APS handoff dispatch backend/API and rendered `/review/layer3` UI;
- external export/download readiness backend/API from PR #269;
- rendered `/review/layer3` external export/download readiness UI from PR #275;
- same-origin external export/download delivery backend/API from PR #278.

The live delivery endpoint streams only the existing validated APS evidence-bundle handoff artifact after server-side authority proof. It does not create public or signed URLs, connector runs, destination bindings, generic downstream dispatch, package mutations, additional rows, schema/runtime/source widening, or full mockup behavior. It also does not render an active `/review/layer3` download control by itself.

## Slice Decision

The next admitted planning boundary is a rendered `/review/layer3` delivery UI slice over the existing same-origin delivery endpoint, not a broader external export system.

The future implementation may:

- render server-authoritative delivery availability from session summary and recorded external export/download readiness state;
- show recorded readiness and delivery basis descriptors read-only;
- enable exactly one server-gated `deliver_external_export_download` browser action only when server state proves delivery is available;
- invoke only `POST /api/v1/layer3/handoff/export/download/deliver`;
- submit only fields admitted by docs 66/67 and current backend behavior;
- handle a same-origin attachment response as a browser download;
- render blocked, stale, conflict, error, and completed-download presentation states without treating browser state as authority.

The future implementation must not infer delivery readiness from browser-local state. Browser state may track display, in-flight request, and last-attempt result only. The server remains authoritative for availability, identity, hash basis, stream authorization, stale/conflict state, and downstream enablement.

## Governing Backend Contract

The UI must treat docs 66/67 and the live PR #278 backend/API endpoint as authoritative. A future UI implementation may only call:

- the existing `/review/layer3` session-summary refresh path already used by the page;
- `POST /api/v1/layer3/handoff/export/download/deliver`.

The UI must not call or introduce:

- public or signed URL routes;
- file-streaming routes outside the PR #278 endpoint;
- connector-run creation or mutation;
- destination selection;
- generic downstream dispatch;
- package edit, rebuild, mutation, supersession, or amendment routes.

## Required UI Inputs

The rendered control must be driven by server-provided state. The UI may collect only operator-visible intent to download and optional notes if already admitted by the backend; all authority fields must come from server summary or server response state.

The UI must use server state for:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- result-review identity;
- package-review submit identity and approval state;
- handoff/export prepare identity and prepared state;
- APS handoff dispatch identity and dispatched state;
- external export/download readiness identity and prepared state;
- delivery availability and mode;
- source APS handoff package row identity;
- source artifact reference, hash, schema, and package hash basis;
- downstream disabled flags;
- previous recorded readiness state, if any.

The UI may generate a fresh `client_request_id` for each submit attempt. It must not reuse a prior `client_request_id` after the browser starts a distinct delivery attempt.

## Required UI States

The future UI must distinguish these presentation states without treating them as independent backend authority:

- unavailable because upstream package/review/handoff/APS/readiness gates are incomplete;
- ready because the server reports delivery availability for the recorded descriptor;
- downloading because one browser-local delivery request is in flight;
- completed because the same-origin response completed without client-side error;
- blocked or unavailable because the server returned a fail-closed response;
- conflict because the backend rejected stale, duplicate-conflicting, or authority-mismatched claims;
- error because the request could not complete.

The UI must preserve existing package-review submit, handoff/export prepare, APS handoff dispatch, and external export/download readiness panels and state progression. Delivery UI must be downstream of recorded external export/download readiness.

## Required Request Shape

The future UI must submit only the request fields admitted by docs 66/67 and current backend behavior. At minimum, the request must include the server-confirmed authority basis required by the backend and:

- `session_id`;
- `analysis_plan_id`;
- `pass_run_id`;
- package-review submit record reference and approved state;
- handoff/export prepare record reference and prepared state;
- APS handoff dispatch record reference and dispatched state;
- external export/download readiness record reference and prepared state;
- source APS handoff package identity and package basis;
- APS bundle reference/hash/schema basis;
- `export_download_target == aps_evidence_bundle_download_reference`;
- `download_mode == reference_only_prepare`;
- `delivery_mode == same_origin_artifact_stream`;
- `operator_decision == deliver_external_export_download`;
- `client_request_id`.

The UI must fail closed client-side before submit when the server summary does not provide the required authority basis, but the backend remains the final authority and must still revalidate all request claims.

## Required Display After Completion

After a successful browser download response or refreshed server state, the UI may display only non-authoritative attempt status and server-returned reference descriptors, including identifiers, package kinds, package refs, artifact refs, hashes, state names, target/mode, disabled downstream flags, and next-state guidance.

The UI must not display or manufacture:

- public URLs;
- signed URLs;
- local filesystem paths;
- connector-run IDs;
- destination choices;
- editable package payloads;
- rewritten content;
- new export manifests.

## Explicit Non-Goals

This freeze does not admit:

- public or signed URL generation;
- connector dispatch or connector-run handling;
- destination selection;
- generic downstream dispatch;
- package amendment, rebuild, supersession, mutation, copying, or reconstruction;
- additional reconciliation rows;
- additional package rows;
- `AnalysisArtifact` expansion;
- schema migration;
- runtime DB widening;
- source expansion;
- local upload or local-directory ingestion;
- qualitative, hybrid, RAG, or vector execution;
- execution-start expansion beyond already admitted work;
- full mockup activation.

## Required Proof For Implementation

At minimum, a future implementation must prove:

- the rendered control is disabled until server state proves delivery availability;
- the UI submits only docs 66/67 admitted fields to the PR #278 endpoint;
- stale or missing readiness, APS dispatch, handoff/export prepare, package-review, package refs/hashes, APS package row, or APS bundle state renders unavailable and fails closed if submitted;
- forbidden request fields are not sent by the UI;
- a successful response is handled as a same-origin browser download without exposing public/signed URLs;
- no connector/destination/generic dispatch occurs;
- no package, reconciliation, `AnalysisArtifact`, runtime DB, source-ingestion, schema, or physical export artifact rows/files are created by the UI;
- existing delivery backend/API tests still pass;
- headed and headless browser tests prove the rendered control behavior.

## Deferred After This Freeze

Still separate and not admitted:

- public URL generation;
- signed URL generation;
- connector dispatch or connector-run handling;
- destination selection;
- generic downstream dispatch;
- package amendment/rebuild/supersession;
- package payload mutation/reconstruction;
- additional reconciliation/package/artifact rows;
- `AnalysisArtifact` expansion;
- schema/runtime/source widening;
- qualitative/hybrid/RAG/vector execution;
- full mockup activation.
