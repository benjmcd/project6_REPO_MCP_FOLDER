# Rendered APS Handoff Dispatch Freeze

Status: planning/control freeze only for `raw_mixed_rendered_aps_handoff_dispatch`.

This document selects the next rendered downstream proof boundary after `171_RENDERED_HANDOFF_EXPORT_PROOF.md`. It admits no runtime behavior by itself and does not change routes, DTOs, services, models, migrations, source handling, package behavior, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or current rendered UI controls.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current live upstream proof: `171_RENDERED_HANDOFF_EXPORT_PROOF.md`
- selected rendered APS handoff mode: `raw_mixed_rendered_aps_handoff_dispatch`
- existing APS handoff route to reuse later: `POST /api/v1/layer3/handoff/aps/dispatch`
- existing request DTO: `Layer3ApsHandoffDispatchRequest`
- existing response schema: `Layer3ApsHandoffDispatchResponse`
- existing rendered control: `#aps-handoff-dispatch-submit`
- existing rendered panel: `#aps-handoff-dispatch-panel`
- existing operation dock target: `[data-operation-target="aps-handoff-band"]`
- existing UI shell: `backend/app/review_ui/static/layer3.html`
- existing UI runtime: `backend/app/review_ui/static/layer3.js`
- existing raw mixed browser proof file: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this planning document.

## Selected Future Boundary

The next implementation-eligible UI pass is exactly:

`raw_mixed_rendered_aps_handoff_dispatch`

That pass may drive the already-rendered APS handoff dispatch control only after the raw mixed rendered path has recorded `handoff_export_prepared`. It must reuse the existing backend APS handoff route and existing UI controls. It must not add a route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, rendered control, external export/download behavior, provider URL behavior, or connector/destination behavior unless a repo-confirmed blocker is reported first.

## Exact Future Controls

The future implementation should use the existing controls:

- `[data-operation-target="aps-handoff-band"]`: opens the existing APS handoff operation band in the workbench operation dock.
- `#aps-handoff-dispatch-submit`: posts the APS handoff dispatch authority to `POST /api/v1/layer3/handoff/aps/dispatch`.
- `#aps-handoff-dispatch-panel`: displays server-returned APS handoff dispatch authority.

No manifest picker, upload control, directory picker, source adapter selector, web connector picker, RAG/vector control, provider URL control, connector dispatch control, destination selector, hidden LLM control, auth/security control, full mockup control, package mutation control, replacement-package control, package supersession control, or external export/download implementation may be added by this pass.

## Server Authority Gates

The APS handoff dispatch control may be driven only when all of the following are true in current rendered state and server-returned authority:

- a current `session_id` exists from normal preflight/source/material/Gate B progression;
- Gate C typing has been committed for that session;
- a plan preview and plan approval exist for the current preview identity;
- execution selection has returned server-selected pass-run authority;
- execution start has started exactly one selected pass run;
- result/status inspection has returned `result_status_available: true`;
- result review has been recorded as `execution_result_review_approved` with `operator_decision: approved`;
- package preview, construction, and package-review submit have recorded an approved package-review state;
- handoff/export prepare has recorded `handoff_export_prepared`, `prepare_record_ref`, and a handoff/export envelope;
- session summary reports APS handoff readiness for the prepared handoff/export state;
- no stale-preview, recovery, cancellation, rerun, external export/download, source-expansion, replacement, supersession, or mutation blocker is active.

The browser must not manufacture APS handoff refs, package-review submit refs, reconciliation IDs, package IDs, package kinds, payload refs, payload hashes, envelope refs, external download authority, provider URLs, connector authority, or durable handoff authority.

## State Transitions

The future UI proof must preserve this order:

1. Rendered raw mixed materialization creates admitted source authority.
2. Rendered preflight/source preview/material preview run normally.
3. Rendered Gate B and Gate C run normally.
4. Rendered plan preview and plan approval run normally.
5. Rendered execution selection and execution start run normally.
6. Rendered result/status inspection returns selected-pass result/status authority.
7. Rendered result-review submit records exactly one `approved` result review.
8. Rendered package preview, construction, and package-review submit record approved package-review authority.
9. Rendered handoff/export prepare records `handoff_export_prepared`.
10. Rendered APS handoff dispatch records exactly one `dispatch_aps_handoff` decision for `aps_evidence_bundle` and `server_side_aps_handoff`.
11. External export/download prepare, external export/download deliver, provider URL generation, connector/destination dispatch, package replacement, package supersession, and package mutation remain outside this pass.

APS handoff dispatch must not create or rewrite the three package-review source packages, prepare external export/download, invoke connectors, write destinations, create provider URLs, create RAG/vector state, create source rows, create model/migration state, or create browser-only durable authority.

## Current Readiness Nuance

Current rendered workbench behavior may enable `#external-export-download-prepare-submit` after a successful APS handoff dispatch response. This freeze does not make external export/download prepare part of the selected pass. The future proof may acknowledge that next-step readiness is surfaced, but it must not click the external export/download prepare control or send `POST /api/v1/layer3/handoff/export/download/prepare`.

## Negative Invariants

This freeze admits no:

- production backend route, DTO, service, model, or migration change;
- rendered UI control change;
- source-family expansion beyond `dataset_version` and `aps_content_document`;
- source adapter registry behavior;
- local upload or local-directory ingestion;
- arbitrary local path input;
- web connector retrieval;
- RAG/vector retrieval or index creation;
- provider/public URL or signed public URL generation;
- real connector or destination dispatch;
- external export/download prepare or deliver;
- broad package mutation or reconstruction;
- package replacement or package supersession;
- package payload rewrite outside the already-admitted package-construction commit behavior;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

There is no frontend-only durable authority.
