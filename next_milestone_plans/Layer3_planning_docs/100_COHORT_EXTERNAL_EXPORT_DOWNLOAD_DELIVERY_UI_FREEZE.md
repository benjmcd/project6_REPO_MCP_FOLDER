# Layer 3 Selected-Pass Cohort External Export Download Delivery UI Freeze

## Status

Current-main planning/control freeze for the rendered `/review/layer3` associated-cohort external export/download delivery controls now implemented by PR `#487`.

This document still does not change runtime behavior by itself. It records the boundary introduced by PR `#485` and satisfied by PR `#487`: the repo already contained a generic rendered delivery form and browser-managed same-origin attachment path from the earlier single-item delivery UI slice, and PR `#487` admits selected-pass associated-cohort `descriptive_summary` readiness only through an explicit server-authoritative delivery UI gate.

The existing backend/API proof remains valid, but browser activation must not rely on incidental reuse of generic UI state. Associated-cohort rendered delivery is live only when the server emits the explicit `delivery_ui` readiness object and the rendered control verifies that object before submitting.

## Current Live Baseline

Current `project6-origin/main` includes:

- docs `98`/`99` as associated-cohort same-origin delivery governance;
- PR `#483` as backend/API proof that the existing `POST /api/v1/layer3/handoff/export/download/deliver` endpoint can stream the associated-cohort APS evidence-bundle artifact after full server-side revalidation;
- the older generic `/review/layer3` delivery form, panel, and `submitAttachmentForm('/handoff/export/download/deliver', ...)` browser-managed delivery path from docs `68`/`69` and PR `#282`/`#285`/`#286`;
- session-summary readiness state that still exposes `browser_download_enabled: false` for external export/download readiness;
- PR `#487` as the bounded rendered delivery UI gate implementation that adds a server-side associated-cohort `delivery_ui` authority object and requires that object before enabling the existing form.

The generic UI code still is not authority by itself. PR `#487` makes the associated-cohort gate explicit rather than inheriting behavior accidentally from the single-item delivery UI.

## Slice Decision

The admitted boundary is a rendered-control settlement over existing UI and backend surfaces:

> Make associated-cohort delivery UI activation explicit and server-authoritative, otherwise keep the existing rendered control disabled for associated-cohort readiness.

PR `#487` implements the first option. It may:

- reuse the existing `/review/layer3` delivery form and same-origin attachment submission path;
- add or expose an explicit server-authoritative delivery UI availability field/object for associated-cohort readiness;
- require the rendered control to check that explicit server authority before enabling delivery;
- submit only the existing backend-admitted `POST /api/v1/layer3/handoff/export/download/deliver` request shape;
- render read-only associated-cohort delivery basis fields and disabled downstream flags;
- show browser-local in-flight/completed/error attempt state only as presentation, never as authority.

Future changes must not treat existing rendered code, browser-local state, or generic single-item delivery precedent as sufficient authority by itself.

## Required Server Gate

Before the rendered control may be enabled for associated-cohort delivery, the server summary or response state must prove:

1. exact PR `#479` associated-cohort readiness is recorded;
2. PR `#483` backend/API delivery authority remains available through the existing endpoint;
3. `pass_type == associated_cohort`;
4. `pass_scope == quantitative_associated_cohort_dataset_version`;
5. `method == descriptive_summary`;
6. `source_gate == 78_COHORT_FREEZE`;
7. `source_shape == aligned_wide_table`;
8. `source_dataset_version_ids` match package, prepare, APS dispatch, readiness, and delivery authority;
9. package-review submit, handoff/export prepare, APS dispatch, and readiness refs match stored authority;
10. APS bundle ref/id/schema/hash/size validates through the existing APS evidence-bundle owner-service contract;
11. public URL, signed URL, connector dispatch, destination selection, generic downstream dispatch, package mutation, schema/runtime/source widening, retry/recovery/rerun, and broader UI flags remain disabled.

PR `#487` uses `delivery_ui` as the replacement server-authoritative delivery UI gate while preserving `browser_download_enabled: false`. If that explicit gate is absent or unavailable, the UI must render associated-cohort delivery unavailable.

## UI Boundary

The implemented UI may activate only one action:

- `deliver_external_export_download`

The action may call only:

- `POST /api/v1/layer3/handoff/export/download/deliver`

The UI must not add:

- a new route;
- a public or signed URL flow;
- a file-streaming route outside the existing endpoint;
- connector or generic dispatch controls;
- destination selection;
- package edit, rebuild, copy, rewrite, amendment, or supersession controls;
- retry/recovery/rerun controls;
- schema/runtime/source/model/migration changes;
- broader associated-cohort review or full mockup activation.

## Required Proof For Implementation

PR `#487` proves:

- the rendered control is disabled when the server does not explicitly admit associated-cohort delivery UI activation;
- the rendered control is enabled only after exact associated-cohort readiness and delivery authority are server-proven;
- request construction uses server-confirmed fields plus a fresh `client_request_id`;
- forbidden URL, connector, destination, dispatch, package mutation, schema/runtime/source, retry/recovery/rerun, and browser-only authority fields are not sent;
- stale or mismatched associated-cohort authority renders unavailable and fails closed if submitted;
- successful delivery remains a same-origin browser-managed attachment and exposes no public/signed URL;
- no package, reconciliation, artifact, connector-run, plan/pass/analysis, runtime DB, source, model, migration, or physical export rows/files are created by the UI;
- existing backend/API delivery tests still pass;
- relevant static/page tests prove the new gate;
- headed and headless Chromium tests prove unavailable, ready, and same-origin attachment response behavior.

## Deferred After This Freeze

Still separate and not admitted:

- public URL generation;
- signed URL generation;
- connector dispatch or connector-run handling;
- destination selection;
- generic downstream dispatch;
- package amendment, rebuild, copy, rewrite, or supersession;
- additional reconciliation/package/artifact rows;
- `AnalysisArtifact` expansion;
- schema/runtime/source/model/migration widening;
- qualitative/hybrid/RAG/vector behavior;
- broader UI or full mockup activation.
