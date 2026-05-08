# Rendered External Export Download Delivery Freeze

Status: planning/control freeze only for `raw_mixed_rendered_external_export_download_delivery`.

This document selects the next rendered downstream proof boundary after `177_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PROOF.md`. It admits no runtime behavior by itself and does not change routes, DTOs, services, models, migrations, source handling, package behavior, connector behavior, provider URL behavior, signed-reference behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or current rendered UI controls.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current live upstream proof: `177_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PROOF.md`
- selected rendered external export/download mode: `raw_mixed_rendered_external_export_download_delivery`
- existing external export/download delivery route to reuse later: `POST /api/v1/layer3/handoff/export/download/deliver`
- existing request DTO: `Layer3ExternalExportDownloadDeliveryRequest`
- existing delivery response schema/header: `layer3.external_export_download_delivery.v1`
- existing rendered control: `#external-export-download-delivery-submit`
- existing rendered panel: `#external-export-download-delivery-panel`
- existing operation dock target: `[data-operation-target="external-export-download-band"]`
- existing UI shell: `backend/app/review_ui/static/layer3.html`
- existing UI runtime: `backend/app/review_ui/static/layer3.js`
- existing raw mixed browser proof file: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this planning document.

## Selected Future Boundary

The next implementation-eligible UI pass is exactly:

`raw_mixed_rendered_external_export_download_delivery`

That pass may drive the already-rendered external export/download delivery control only after the raw mixed rendered path has recorded `external_export_download_prepared`. It must reuse the existing backend same-origin delivery route and existing UI controls. It must not add a route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, rendered control, provider URL behavior, connector/destination behavior, signed-reference behavior, or direct non-browser delivery behavior unless a repo-confirmed blocker is reported first.

## Exact Future Controls

The future implementation should use the existing controls:

- `[data-operation-target="external-export-download-band"]`: opens the existing external export/download operation band in the workbench operation dock.
- `#external-export-download-delivery-submit`: submits same-origin external export/download delivery to `POST /api/v1/layer3/handoff/export/download/deliver`.
- `#external-export-download-delivery-panel`: displays same-origin delivery readiness and submitted/delivered browser-managed attachment state.

No manifest picker, upload control, directory picker, source adapter selector, web connector picker, RAG/vector control, provider URL control, connector dispatch control, destination selector, hidden LLM control, auth/security control, full mockup control, package mutation control, replacement-package control, package supersession control, or signed-reference control may be added by this pass.

## Server Authority Gates

The external export/download delivery control may be driven only when all of the following are true in current rendered state and server-returned authority:

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
- external export/download prepare has recorded `external_export_download_prepared`, `external_export_download_record_ref`, and `export_download_descriptor_ref`;
- associated-cohort delivery UI authority reports `associated_cohort_external_export_download_delivery_ui_ready`;
- no stale-preview, recovery, cancellation, rerun, signed-reference, provider/public URL, source-expansion, replacement, supersession, or mutation blocker is active.

The browser must not manufacture delivery refs, descriptor refs, APS bundle hashes, package refs, provider URLs, connector authority, destination authority, signed-reference tokens, or durable delivery authority.

## Current Readiness Nuance

Current rendered workbench behavior may enable same-origin signed-reference controls after a successful external export/download prepare response. This freeze does not make signed-reference generation or use part of the selected pass. The future proof may acknowledge that signed-reference readiness is surfaced, but it must not click signed-reference controls, generate/use a signed reference, or send `POST /api/v1/layer3/handoff/export/download/signed-reference/generate` or `POST /api/v1/layer3/handoff/export/download/signed-reference/use`.

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
- signed-reference generation or use;
- broad package mutation or reconstruction;
- package replacement or package supersession;
- package payload rewrite outside the already-admitted package-construction commit behavior;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

There is no frontend-only durable authority.
