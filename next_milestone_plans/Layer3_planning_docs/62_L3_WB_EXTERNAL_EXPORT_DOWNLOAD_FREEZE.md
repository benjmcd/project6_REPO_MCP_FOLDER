# 62 L3 Workbench External Export Download Freeze

Status: planning-only governance for a future bounded Layer 3 workbench external export/download readiness boundary after recorded APS handoff dispatch.

This document freezes only the next admissible planning boundary after `aps_handoff_dispatched`: one server-authoritative, reference-only external export/download preparation record over the already persisted APS evidence-bundle handoff artifact. It does not implement runtime behavior by itself, does not add a browser download route, does not expose a download URL, and does not admit connector dispatch, generic downstream dispatch, destination selection, package mutation, schema/runtime/source widening, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Current Live Boundary

Current `project6-origin/main` includes:

- bounded package-review preview, package construction, package-review submit, and rendered package-review controls
- bounded backend/API handoff/export `prepare_only` state after `package_review_approved`
- bounded rendered `/review/layer3` prepare-only controls
- bounded backend/API APS handoff dispatch through `POST /api/v1/layer3/handoff/aps/dispatch`
- bounded rendered `/review/layer3` APS dispatch controls
- one APS owner-service output family: `aps_evidence_bundle_handoff`
- a persisted APS evidence-bundle handoff artifact referenced by the APS handoff package row

Current `main` still has no workbench-owned external export/download endpoint, no rendered external export/download control, no generic downstream dispatch, no connector dispatch, and no destination selection.

## Evidence Basis

The repo already contains lower-layer export/report/export-package surfaces and connector routes, but those surfaces are not adopted as the Layer 3 workbench external export/download boundary by this freeze. They sit in connector/report families with their own runtime assumptions, and they are not a safe substitute for server-authoritative workbench state after `aps_handoff_dispatched`.

The repo-confirmed workbench-compatible export source is narrower:

- `backend/app/services/layer3_aps_handoff.py` owns the `aps_evidence_bundle_handoff` package row.
- `backend/app/services/nrc_aps_evidence_bundle.py` owns persisted APS evidence-bundle artifact refs and validation.
- `backend/tests/test_layer3_aps_handoff.py` proves the APS handoff owner-service row/artifact contract.
- Docs `58`/`59` and the PR `#260` implementation make APS handoff dispatch live only after `handoff_export_prepared`.
- Docs `60`/`61` and PR `#266` render only APS dispatch readiness/submit state, with external export/download still disabled.

Because no current workbench route safely streams browser downloads, the first external export/download governance packet must be a readiness/materialization contract over existing refs, not a direct download-button or public-link contract.

## Slice Decision

The next admitted planning boundary is:

> Freeze one backend/API external export/download readiness preparation step after `aps_handoff_dispatched`. The step may record a server-authoritative reference-only export/download descriptor for the existing APS evidence-bundle handoff artifact. It must not create a browser download URL, copy or rewrite package payloads, create connector runs, select destinations, or dispatch to any downstream system.

This is the smallest coherent continuation because APS handoff dispatch already creates the repo-native evidence-bundle handoff artifact. The next server action can prove that artifact is the export/download source and record a descriptor. Actual browser download route/UI behavior remains a separate later boundary unless implementation audit proves the route can be safely added under its own freeze.

## Admitted Future Implementation Scope

A future implementation governed by this freeze may add only:

- a thin backend/API endpoint for external export/download readiness preparation after recorded APS handoff dispatch
- server-side validation that the session still has approved package-review submit state, `handoff_export_prepared` state, and `aps_handoff_dispatched` state
- validation that package ids, package kinds, payload refs, payload hashes, result-review ref, package-review preview hash, submit ref, prepare ref, APS handoff ref, and APS bundle ref still match the recorded authority basis
- a reference-only external export/download descriptor in existing JSON-bearing workbench state
- session summary projection of the recorded external export/download readiness state
- focused API/service tests proving success, fail-closed stale authority, idempotency/conflict behavior, and no forbidden side effects

The descriptor may identify the existing APS bundle artifact by internal ref, id, schema id, checksum/hash, size if already known or cheaply derived from that artifact, and a server-owned descriptor ref. It must not expose a public URL, a signed URL, a file-system path intended for browser use, a connector-run id, a destination id, or raw payload bodies.

## Explicit Non-Goals

This freeze does not admit:

- browser download routes
- rendered download buttons or links
- public, signed, or local download URLs
- external destination selection
- generic downstream dispatch
- connector-run creation, mutation, resume, cancel, or dispatch
- non-APS downstream handoff
- package payload editing, copying, rewriting, regeneration, reconstruction, rebuild, or amendment
- package-review amendment or supersession
- result-review amendment or supersession
- approved-plan supersession
- additional `L3ReconciliationRecord` rows
- additional `L3OutputPackage` rows
- `AnalysisArtifact` row creation
- new physical export artifacts beyond the existing APS evidence-bundle handoff artifact
- artifact manifests outside the existing APS evidence-bundle contract
- runtime DB writes outside existing owner-service artifact behavior
- schema migrations or new models
- execution selection/start UI expansion
- rerun, retry, recovery, cancel, or replay controls beyond deterministic idempotency
- source expansion, local upload, or local-directory ingestion
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

If a future implementation proves that a new physical artifact, a download route, a `FileResponse`, a connector run, destination selection, package mutation, schema changes, or runtime/source widening is required, stop and freeze that narrower prerequisite separately before implementing.

## Required Preconditions

A future external export/download readiness request must be blocked unless the server can prove all of the following:

1. `session_id`, `analysis_plan_id`, `pass_run_id`, `preview_id`, and `preview_hash` match current workbench authority.
2. selected-pass result/status authority still resolves to the same terminal selected pass.
3. selected-pass result-review state is still approved.
4. package-review preview hash still matches the package set.
5. package construction still exposes the same reconciliation id, output package ids, package kinds, payload refs, and payload hashes.
6. package-review submit state is exactly `package_review_approved`.
7. handoff/export prepare state is exactly `handoff_export_prepared`.
8. prepare state still uses `handoff_target == internal_export_envelope` and `export_mode == prepare_only`.
9. APS handoff dispatch state is exactly `aps_handoff_dispatched`.
10. the recorded APS output package kind is exactly `aps_evidence_bundle_handoff`.
11. the APS bundle ref/id/schema/hash still validates through the existing APS evidence-bundle contract.
12. no prior external export/download readiness record exists for the same authority basis unless the request is an exact idempotent replay.

If any authority input is absent, stale, malformed, ambiguous, or inconsistent, the implementation must fail closed before recording export/download readiness.

## Write Boundary

The only durable write admitted by this freeze is:

- one external export/download readiness summary in existing JSON-bearing workbench state.

The write must be reference-only and must not mutate source package rows, source package payload refs/hashes, APS handoff rows, APS bundle artifacts, result-review state, package-review submit state, handoff/export prepare state, plans, pass runs, analysis runs, runtime DB state, schema, or source inventory.

## Relationship To Existing Export Services

Existing connector/report/export-package services remain separate lower-layer surfaces. This freeze does not route the workbench through those connector APIs by default, does not treat connector report export packages as workbench downloads, and does not let the browser select an export family.

The future implementation must start from the recorded workbench APS handoff state. If the existing APS bundle ref cannot support a reference-only export/download descriptor without copying, rewriting, or creating a new artifact family, the implementation must stop and create a smaller artifact-materialization freeze.

## UI Boundary

This freeze does not require rendered `/review/layer3` changes. A later UI freeze is required before:

- rendering an external export/download readiness panel,
- enabling any download button,
- rendering any download link,
- exposing file names as downloadable anchors,
- offering destination selection, or
- adding connector/downstream controls.

Until a later UI freeze lands, `/review/layer3` must continue to render external export/download as disabled or unavailable after APS dispatch.

## Required Proof For Implementation

At minimum, a future implementation must prove:

- success requires recorded `aps_handoff_dispatched` state.
- missing, stale, blocked, or conflicting APS handoff dispatch authority fails closed.
- stale result-review ref, package-review preview hash, submit ref, reconciliation id, package ids, package kinds, payload refs, payload hashes, prepare ref, APS handoff ref, APS output package id/kind, or APS bundle ref/hash fails closed.
- exact idempotent replay returns the same readiness descriptor without duplication or mutation.
- conflicting replay fails closed.
- no new package rows, reconciliation rows, `AnalysisArtifact` rows, connector-run rows, schema migrations, runtime DB writes, or source-ingestion rows are created.
- existing package payload refs/hashes and APS handoff artifact refs/hashes are not mutated.
- response and session summary are reference-only and contain no raw payload bodies, download URLs, connector-run ids, destination ids, editable package payloads, or rewritten content.
- existing handoff/export prepare and APS handoff dispatch backend tests still pass.
- browser tests are required only if a later implementation changes rendered UI behavior.

## Deferred After This Freeze

Still separate and not admitted:

- actual browser download route/control
- external export file streaming
- public or signed download links
- generic downstream dispatch
- connector dispatch or connector-run handling
- destination selection
- package amendment/rebuild/supersession
- package payload mutation/reconstruction
- additional reconciliation/package/artifact rows
- `AnalysisArtifact` expansion
- schema/runtime/source widening
- execution expansion beyond already admitted work
- qualitative/hybrid/RAG/vector execution
- full mockup activation

## Relationship To Existing Docs

This freeze is downstream of:

- `60_L3_WB_APS_HANDOFF_DISPATCH_UI_FREEZE.md`
- `61_L3_WB_APS_HANDOFF_DISPATCH_UI_STATE_CONTRACT.md`
- `58_L3_WB_APS_HANDOFF_DISPATCH_FREEZE.md`
- `59_L3_WB_APS_HANDOFF_DISPATCH_API_AND_STATE_CONTRACT.md`
- `56_L3_WB_HANDOFF_EXPORT_UI_FREEZE.md`
- `57_L3_WB_HANDOFF_EXPORT_UI_STATE_CONTRACT.md`
- `54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`

It supersedes only the prior "no next functional tranche selected" posture by admitting this planning boundary. It does not make external export/download behavior live by itself.
