# Rendered External Export Download Prepare Freeze

Status: planning/control freeze only for `raw_mixed_rendered_external_export_download_prepare`.

This document selects the next rendered downstream proof boundary after `174_RENDERED_APS_HANDOFF_PROOF.md`. It admits no runtime behavior by itself and does not change routes, DTOs, services, models, migrations, source handling, package behavior, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or current rendered UI controls.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current live upstream proof: `174_RENDERED_APS_HANDOFF_PROOF.md`
- selected rendered external export/download mode: `raw_mixed_rendered_external_export_download_prepare`
- existing external export/download route to reuse later: `POST /api/v1/layer3/handoff/export/download/prepare`
- existing request DTO: `Layer3ExternalExportDownloadPrepareRequest`
- existing response schema: `Layer3ExternalExportDownloadPrepareResponse`
- existing rendered control: `#external-export-download-prepare-submit`
- existing rendered panel: `#external-export-download-prepare-panel`
- existing operation dock target: `[data-operation-target="external-export-download-band"]`
- existing UI shell: `backend/app/review_ui/static/layer3.html`
- existing UI runtime: `backend/app/review_ui/static/layer3.js`
- existing raw mixed browser proof file: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this planning document.

## Selected Future Boundary

The next implementation-eligible UI pass is exactly:

`raw_mixed_rendered_external_export_download_prepare`

That pass may drive the already-rendered external export/download prepare control only after the raw mixed rendered path has recorded `aps_handoff_dispatched`. It must reuse the existing backend external export/download prepare route and existing UI controls. It must not add a route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, rendered control, provider URL behavior, connector/destination behavior, signed-reference delivery behavior, or direct delivery behavior unless a repo-confirmed blocker is reported first.

## Exact Future Controls

The future implementation should use the existing controls:

- `[data-operation-target="external-export-download-band"]`: opens the existing external export/download operation band in the workbench operation dock.
- `#external-export-download-prepare-submit`: posts external export/download readiness to `POST /api/v1/layer3/handoff/export/download/prepare`.
- `#external-export-download-prepare-panel`: displays server-returned external export/download readiness authority.

No manifest picker, upload control, directory picker, source adapter selector, web connector picker, RAG/vector control, provider URL control, connector dispatch control, destination selector, hidden LLM control, auth/security control, full mockup control, package mutation control, replacement-package control, package supersession control, signed-reference delivery control, or direct delivery implementation may be added by this pass.

## Server Authority Gates

The external export/download prepare control may be driven only when all of the following are true in current rendered state and server-returned authority:

- a current `session_id` exists from normal preflight/source/material/Gate B progression;
- Gate C typing has been committed for that session;
- a plan preview and plan approval exist for the current preview identity;
- execution selection has returned server-selected pass-run authority;
- execution start has started exactly one selected pass run;
- result/status inspection has returned `result_status_available: true`;
- result review has been recorded as `execution_result_review_approved`;
- package preview, construction, and package-review submit have recorded approved package-review authority;
- handoff/export prepare has recorded `handoff_export_prepared`, `prepare_record_ref`, and a handoff/export envelope;
- APS handoff dispatch has recorded `aps_handoff_dispatched`, `aps_handoff_record_ref`, and APS bundle authority;
- session summary reports external export/download readiness for the APS handoff bundle;
- no stale-preview, recovery, cancellation, rerun, delivery, signed-reference, source-expansion, replacement, supersession, or mutation blocker is active.

The browser must not manufacture download refs, descriptor refs, APS bundle hashes, package refs, provider URLs, connector authority, destination authority, or durable delivery authority.

## Current Readiness Nuance

Current rendered workbench behavior may enable `#external-export-download-delivery-submit` after a successful external export/download prepare response. This freeze does not make delivery part of the selected pass. The future proof may acknowledge that next-step readiness is surfaced, but it must not click the delivery control, generate/use a signed reference, or send `POST /api/v1/layer3/handoff/export/download/deliver`.

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
- external export/download deliver;
- signed-reference generation or use;
- broad package mutation or reconstruction;
- package replacement or package supersession;
- package payload rewrite outside the already-admitted package-construction commit behavior;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

There is no frontend-only durable authority.
