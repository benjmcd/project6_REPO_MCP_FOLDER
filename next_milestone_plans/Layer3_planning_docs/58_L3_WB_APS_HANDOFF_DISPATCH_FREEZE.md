# 58 L3 Workbench APS Handoff Dispatch Freeze

Status: governing freeze for the bounded Layer 3 workbench APS handoff dispatch backend/API slice now implemented on current `main` through PR `#260`, with PR `#261` post-merge fail-closed authority hardening.

This document freezes only the bounded APS handoff dispatch step from the current `/review/layer3` workbench chain into the existing repo-native APS evidence-bundle handoff family. The merged backend/API implementation adds the dispatch endpoint and server-authoritative state only; it does not add rendered APS dispatch UI controls, external export/download, connector or generic downstream dispatch, new schema, package mutation, package reconstruction, source/runtime/schema widening, or full mockup activation.

## Current Live Boundary

Current `main` includes:

- package-review preview, package construction, package-review submit, and rendered package-review controls
- backend/API handoff/export `prepare_only` state after `package_review_approved`
- rendered `/review/layer3` prepare-only controls after server-authoritative readiness
- existing non-workbench APS evidence-bundle handoff owner service in `backend/app/services/layer3_aps_handoff.py`
- backend/API workbench APS handoff dispatch through `POST /api/v1/layer3/handoff/aps/dispatch`, implemented in PR `#260` and hardened in PR `#261`

Current `main` exposes the backend/API workbench dispatch endpoint only after server-confirmed `handoff_export_prepared` authority and APS owner-service compatibility. Current `main` still does not expose a rendered `/review/layer3` APS dispatch action. The existing APS handoff owner service can materialize an `aps_evidence_bundle_handoff` package row and persisted APS evidence-bundle artifact from terminal packaged Layer 3 session/package truth, and the workbench endpoint now calls it only after the workbench-specific authority checks pass.

## Slice Decision

The adequate Layer 3 workbench boundary selected by this freeze is:

> Freeze a bounded workbench APS handoff dispatch step that dispatches exactly one already prepared internal handoff/export envelope to the existing APS evidence-bundle handoff owner service. The first target family is `aps_evidence_bundle_handoff` only. The step must require an existing `handoff_export_prepared` state, server-confirmed package-review approval, unchanged package ids/refs/hashes, and compatibility with the existing APS evidence-bundle handoff service before any write occurs.

This is the smallest coherent next boundary because current workbench state already stops at a server-authoritative internal reference envelope. The repo already has a narrower APS target family than generic external export: `layer3_aps_handoff.materialize_aps_handoff(...)` targets the APS evidence-bundle family and has existing service tests. External export/download, destination selection, connector dispatch, physical artifact manifests outside the APS evidence-bundle handoff, package amendment, and broader runtime/schema/source behavior are larger families and remain deferred.

## Admitted Implementation Scope

The implementation governed by this freeze may add only:

- a workbench-owned backend/API action for APS handoff dispatch from a prepared envelope
- server-side validation that the session has exactly one recorded `handoff_export_prepared` state
- validation that the prepared envelope authority still matches current package-review submit, reconciliation, package ids, package kinds, payload refs, and payload hashes
- a call into the existing APS evidence-bundle handoff owner service, or a narrowly factored equivalent wrapper, only after all workbench authority checks pass
- exactly one APS-facing `L3OutputPackage` row of kind `aps_evidence_bundle_handoff` when the existing owner service succeeds
- exactly one persisted APS evidence-bundle artifact produced by the existing APS evidence-bundle handoff contract
- state summary fields that identify the APS handoff row, APS bundle ref, handoff status, disabled external export/download posture, and next unavailable downstream families
- focused tests proving success, fail-closed stale authority, idempotency/conflict behavior, and unchanged package source rows

The implementation must keep the endpoint thin and delegate APS artifact/package materialization to the established owner service boundary. PR `#260` satisfied that compatibility by using the existing owner service plus a narrow workbench-source compatibility path; PR `#261` then restricted fallback behavior so malformed canonical APS provenance still fails closed. If later changes require schema changes, package rewrites, source expansion, or new package/reconciliation rows beyond the single APS handoff package row, stop and create a narrower prerequisite freeze instead.

## Explicit Non-Goals

This freeze does not admit:

- external export
- download URLs or downloadable external artifacts
- generic downstream dispatch
- destination selection
- connector-run creation, mutation, resume, cancel, or dispatch
- physical artifact manifests outside the existing APS evidence-bundle handoff artifact
- `AnalysisArtifact` row creation
- additional package rows beyond the single `aps_evidence_bundle_handoff` row produced by the existing handoff owner service
- new `L3ReconciliationRecord` rows
- mutation, copying, rewriting, rebuilding, or amendment of existing package payloads
- result-review amendment or supersession
- package-review amendment or supersession
- approved-plan supersession
- rerun, retry, recovery, cancellation, or replay controls beyond deterministic idempotency
- source expansion, local upload, or local directory ingestion
- runtime DB writes outside the existing APS evidence-bundle handoff artifact behavior
- schema migrations or new models
- execution selection/start UI expansion
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

## Required Preconditions

A workbench APS handoff dispatch request must be blocked unless the server can prove all of the following:

1. `session_id`, `analysis_plan_id`, `pass_run_id`, `preview_id`, and `preview_hash` match current workbench session authority.
2. selected-pass result/status authority still resolves to the same terminal selected pass.
3. selected-pass result-review state is still approved.
4. package-review preview hash still matches the package set being dispatched.
5. package construction still exposes the same reconciliation id, output package ids, package kinds, payload refs, and payload hashes.
6. package-review submit state is still `package_review_approved`.
7. handoff/export prepare state is exactly `handoff_export_prepared`.
8. the recorded prepare state uses `handoff_target == internal_export_envelope` and `export_mode == prepare_only`.
9. no prior APS handoff dispatch record already exists for the same authority basis unless the request is an exact idempotent replay.
10. the existing APS evidence-bundle handoff owner service can satisfy its own provenance and validation requirements.

If any precondition is missing, stale, inconsistent, or ambiguous, the implementation must fail closed before creating a row or artifact.

## Write Boundary

The only durable writes admitted by this freeze are:

- one APS handoff dispatch summary in existing JSON-bearing workbench state, if needed for session/reconciliation visibility
- one `aps_evidence_bundle_handoff` `L3OutputPackage` row created through the existing APS handoff owner service
- one persisted APS evidence-bundle artifact created by the existing APS evidence-bundle handoff contract

The implementation must not write:

- package payload files for the existing canonical, user-facing, or review-facing packages
- new package variants
- new reconciliation records
- new analysis plans, pass runs, analysis runs, or analysis artifacts
- connector-run rows
- runtime snapshot DB rows
- schema migrations

## Relationship To Existing APS Handoff Service

The existing `backend/app/services/layer3_aps_handoff.py` service remains the repo-confirmed APS evidence-bundle handoff owner. It already defines:

- `PACKAGE_KIND_APS_EVIDENCE_BUNDLE_HANDOFF == "aps_evidence_bundle_handoff"`
- `APS_HANDOFF_SCHEMA_ID == "layer3.aps_evidence_bundle_handoff.v1"`
- `materialize_aps_handoff(db, session_id=...)`
- persisted APS evidence-bundle artifact validation through the APS evidence-bundle contract

This freeze does not reopen that owner service contract. The workbench implementation may wrap or call it only after proving the workbench-specific prepared-envelope authority. If the owner service requires non-workbench terminal/session assumptions that conflict with the current workbench path, the implementation must stop and freeze a compatibility bridge before writing behavior.

## UI Boundary

This freeze does not require rendered UI changes. The current implementation keeps APS dispatch backend/API-only. If rendered `/review/layer3` behavior changes later, a separate UI-state contract or explicit UI section in the implementation PR must prove:

- dispatch controls are visible only after server-authoritative `handoff_export_prepared`
- external export/download, destination selection, connector-run controls, and package edit/rebuild controls remain absent or disabled
- successful APS handoff renders server-returned APS handoff row and bundle refs as read-only
- both headed and headless Chromium proof pass

## Required Proof For Implementation

At minimum, an implementation must prove:

- success requires `handoff_export_prepared`
- non-prepared, held, declined, blocked, missing, or stale prepare state fails closed
- stale result-review ref, package-review preview hash, submit ref, reconciliation id, package ids, package kinds, payload refs, or payload hashes fail closed
- the existing package rows and payload refs/hashes are not mutated
- exactly one `aps_evidence_bundle_handoff` row is created on success
- exactly one APS evidence-bundle artifact is persisted and validates through the existing APS evidence-bundle contract
- no `AnalysisArtifact`, connector-run, schema, runtime DB, source-ingestion, plan, pass, or analysis-run rows are created
- exact idempotent replay returns or identifies the existing handoff dispatch state
- conflicting replay fails closed
- external export/download/dispatch remains disabled

## Deferred After This Freeze

Still separate and not admitted:

- external export/download
- non-APS downstream dispatch
- destination selection and connector-run dispatch
- physical export artifact manifests outside the existing APS evidence-bundle handoff artifact
- package amendment/rebuild/supersession
- execution selection/start UI expansion
- qualitative/hybrid/RAG/vector/source/runtime/schema/full mockup work

## Evidence Basis

- current `layer3_progress_manifest.json` marks PR `#256` as live bounded rendered prepare-only UI and admits no functional next action after it
- docs `54`/`55` and `56`/`57` keep APS handoff, external export/download, downstream dispatch, physical artifacts, package mutation/reconstruction, source/schema/runtime widening, execution selection/start UI expansion, and full mockup activation out
- `backend/app/services/layer3_workbench.py` records prepare-only state with `external_handoff_enabled == false`, `external_export_enabled == false`, and `dispatch_enabled == false`
- `backend/app/services/layer3_aps_handoff.py` already owns the repo-native APS evidence-bundle handoff materialization surface
- `backend/tests/test_layer3_aps_handoff.py` already proves the existing APS handoff owner service emits and validates an APS evidence-bundle handoff row/artifact under its own contract
