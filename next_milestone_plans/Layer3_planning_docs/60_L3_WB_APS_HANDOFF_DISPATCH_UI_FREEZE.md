# Layer 3 Workbench APS Handoff Dispatch UI Freeze

Status: planning-only UI freeze for a future bounded `/review/layer3` APS handoff dispatch control slice over the already-live backend/API endpoint from PR `#260`, hardened by PR `#261` and PR `#263`.

This document freezes only the future rendered presentation and operator-control boundary for the existing backend/API `POST /api/v1/layer3/handoff/aps/dispatch` endpoint. It does not implement UI behavior by itself, does not change backend API behavior, and does not admit external export/download, generic downstream dispatch, connector dispatch, destination selection, package mutation or reconstruction, schema/runtime/source widening, execution selection/start UI expansion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Current Live Boundary

Current `project6-origin/main` through PR `#264` includes:

- the `/review/layer3` workbench shell and prior bounded workbench UI slices through rendered handoff/export prepare-only controls
- backend/API handoff/export `prepare_only` state after `package_review_approved`
- rendered `/review/layer3` prepare-only controls from PR `#256`
- planning docs `58`/`59` for APS handoff dispatch after `handoff_export_prepared`
- backend/API APS handoff dispatch through `POST /api/v1/layer3/handoff/aps/dispatch`
- fail-closed malformed-provenance, unexpected-package-kind, and APS package-row allowlist hardening from PR `#261` and PR `#263`
- the existing APS evidence-bundle handoff owner service in `backend/app/services/layer3_aps_handoff.py`

Current `main` exposes no rendered APS dispatch action. Operators can prepare the internal handoff/export envelope in the UI, but APS dispatch remains backend/API-only.

## Slice Decision

The next admitted UI planning boundary is:

> Present server-authoritative APS handoff dispatch readiness and recorded dispatch state on `/review/layer3`, and allow exactly one APS dispatch submit control only when the session summary proves `handoff_export_prepared`, package-review approval, unchanged package authority, and `aps_handoff_dispatch.available == true`. The UI must submit only the fields admitted by docs `58`/`59` and current backend behavior.

This is the smallest coherent UI continuation after the backend/API APS dispatch endpoint because it can reuse the existing session summary, prepare-only UI state, package evidence already rendered upstream, and the already-live dispatch endpoint without inventing browser-side authority or a parallel state model.

## Admitted UI Scope

A future implementation PR governed by this freeze may change only:

- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`
- `backend/app/review_ui/static/layer3.js`
- narrowly related page/static tests and browser tests that prove the changed `/review/layer3` behavior

The implementation may:

- read `GET /api/v1/layer3/session/{session_id}` after a session exists
- render the server-provided package-review submit, handoff/export prepare, and APS handoff dispatch summaries
- show `handoff_target == internal_export_envelope`, `export_mode == prepare_only`, `aps_handoff_target == aps_evidence_bundle`, and `dispatch_mode == server_side_aps_handoff`
- enable one operator action for `operator_decision == dispatch_aps_handoff` only when server state reports APS dispatch ready
- generate one `client_request_id` per submit attempt
- call `POST /api/v1/layer3/handoff/aps/dispatch` only with fields admitted by docs `58`/`59`
- render successful dispatch responses as server truth, including APS package id, APS bundle ref/id, schema id, disabled downstream flags, and next state
- render already-recorded dispatch state as read-only
- render unavailable, blocked, conflict, stale-authority, and server-error states without offering duplicate or conflicting dispatch controls
- keep external export/download, generic downstream dispatch, destination selection, connector dispatch, package edit/rebuild, rerun, recovery, and source/runtime/schema controls absent or disabled

Browser state may cache display data, maintain in-flight state, and generate `client_request_id`. Browser state must not authorize dispatch, infer missing authority, mutate packages, rebuild packages, export/download, create connector runs, create artifacts outside the existing APS owner-service artifact, or rewrite server state.

## Explicit Non-Goals

This freeze does not admit:

- external export or download controls
- generic downstream dispatch controls
- connector-run creation, mutation, resume, cancel, or dispatch
- destination or target-family selection
- package payload editing, copying, rewriting, regeneration, reconstruction, rebuild, or amendment
- package-review amendment or supersession
- result-review amendment or supersession
- additional package rows beyond the existing backend-admitted `aps_evidence_bundle_handoff` owner-service row
- additional reconciliation rows
- `AnalysisArtifact` row creation
- physical external export artifact manifests
- execution selection/start UI expansion
- rerun, retry, recovery, cancel, or replay controls beyond backend idempotency handling
- source expansion, local upload, or local-directory ingestion
- runtime DB or schema widening
- qualitative, hybrid, RAG, or vector execution UI
- full mockup activation

If implementation proves the UI needs new backend fields, a new endpoint, schema widening, physical external artifacts, package mutation, destination selection, connector dispatch, or generic downstream dispatch to be usable, stop and freeze that backend/API/downstream slice separately.

## Presentation Requirements

The future panel must make these distinctions visible without implying wider dispatch:

| Area | Required presentation | Must not imply |
| --- | --- | --- |
| Prepared envelope | Show server-provided prepare ref, envelope ref, target, mode, package refs, and hashes | A downloadable artifact or external export exists |
| APS dispatch readiness | Show unavailable, ready, dispatched, blocked, or conflict state from server summary | Browser can infer missing authority |
| Dispatch action | Enable exactly one `dispatch_aps_handoff` submit when server state marks dispatch available | Generic downstream dispatch or connector dispatch is live |
| APS dispatch result | Show APS output package id, APS bundle ref/id, APS schema id, and disabled downstream posture | Package payloads are editable or rewritten |
| Downstream posture | Show external export/download, connector dispatch, and non-APS dispatch as disabled/unavailable | Any external transfer or destination selection is live |

When APS dispatch is already recorded, the UI must render it as server state and avoid offering a conflicting second dispatch unless a later freeze admits inspection/replay/amendment behavior.

## State Gating

The UI may enable the APS dispatch submit control only when all of the following are true:

1. a current session id exists
2. server summary identifies approved plan and preview identity/hash
3. selected terminal pass and result/status authority are represented by server state
4. approved selected-pass result-review authority is represented by server state
5. package-review preview, package construction, package-review submit, and handoff/export prepare state are represented by server state
6. package-review submit state is exactly `package_review_approved`
7. handoff/export prepare state is exactly `handoff_export_prepared`
8. recorded prepare state uses `handoff_target == internal_export_envelope` and `export_mode == prepare_only`
9. APS handoff dispatch summary reports `available == true`
10. package ids, package kinds, payload refs, payload hashes, reconciliation id, package-review preview hash, result-review record ref, submit ref, prepare ref, and envelope ref are present from server state
11. no conflicting APS dispatch state is already recorded
12. external export/download, connector dispatch, and non-APS dispatch remain disabled

If any of these are absent, stale, inconsistent, or blocked, the UI must render unavailable/blocked state and avoid submitting APS dispatch requests.

## Backend Boundary

This UI freeze expects the implementation to use existing backend routes:

- `GET /api/v1/layer3/session/{session_id}`
- `POST /api/v1/layer3/handoff/aps/dispatch`

The UI must not duplicate backend authority checks. Request fields are claims assembled from server state and operator intent; the backend remains responsible for fail-closed validation.

## Required Proof

An implementation PR governed by this freeze must prove:

- no backend behavior changes unless a separate freeze explicitly admits them
- no APS dispatch control renders before a session exists
- no APS dispatch control renders before `handoff_export_prepared`
- unavailable, blocked, conflict, and stale-authority server states render without allowing submission
- controls are enabled only after server-authoritative `aps_handoff_dispatch.available == true`
- request payloads contain only docs `58`/`59` admitted fields
- forbidden external export/download, connector, destination, package mutation, rerun, source, schema, runtime, artifact, and full mockup fields are absent from requests
- successful dispatch responses render server state and keep external export/download, connector dispatch, and non-APS dispatch disabled
- already-recorded dispatch state renders read-only
- duplicate/conflict response renders blocked or unavailable state without local amendment controls
- existing package-review, handoff/export prepare, and APS dispatch backend tests still pass
- page/static tests cover disabled, ready, dispatched, blocked, conflict, and error UI states
- both headed and headless Chromium proof pass because rendered `/review/layer3` behavior changes

## Stop Conditions

Stop before implementation if any of these becomes necessary:

- new backend endpoint or schema field beyond a separately frozen API/state contract
- external export/download or generic downstream dispatch
- connector-run creation, mutation, or dispatch
- downstream destination or target-family selection
- package payload rewrite, copy, editing, or reconstruction
- package rebuild/amendment or package-review supersession
- additional package or reconciliation rows beyond the already admitted APS owner-service output row
- `AnalysisArtifact` creation
- execution selection/start UI expansion
- rerun/recovery/cancellation/retry controls beyond deterministic request idempotency
- source expansion or local ingestion
- runtime DB or schema widening
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

## Relationship To Existing Docs

This freeze is downstream of:

- `58_L3_WB_APS_HANDOFF_DISPATCH_FREEZE.md`
- `59_L3_WB_APS_HANDOFF_DISPATCH_API_AND_STATE_CONTRACT.md`
- `56_L3_WB_HANDOFF_EXPORT_UI_FREEZE.md`
- `57_L3_WB_HANDOFF_EXPORT_UI_STATE_CONTRACT.md`
- `54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`
- `52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md`
- `50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`
- `51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md`

It freezes only a bounded rendered UI presentation and operator dispatch control surface for current backend APS dispatch authority. It does not replace the backend APS dispatch docs and does not make UI behavior live by itself.
