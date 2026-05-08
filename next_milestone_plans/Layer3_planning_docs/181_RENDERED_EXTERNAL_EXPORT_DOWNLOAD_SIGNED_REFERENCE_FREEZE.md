# Rendered External Export Download Signed Reference Freeze

Status: planning/control freeze only for `raw_mixed_rendered_external_export_download_signed_reference`.

This document selects the next rendered downstream proof boundary after `180_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PROOF.md`. It admits no runtime behavior by itself and does not change routes, DTOs, services, models, migrations, source handling, package behavior, connector behavior, provider URL behavior, RAG/vector behavior, mockup behavior, hidden LLM behavior, auth/security behavior, or current rendered UI controls.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current live upstream proof: `180_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PROOF.md`
- selected rendered external export/download mode: `raw_mixed_rendered_external_export_download_signed_reference`
- existing signed-reference generate route to reuse later: `POST /api/v1/layer3/handoff/export/download/signed-reference/generate`
- existing signed-reference use route to reuse later: `POST /api/v1/layer3/handoff/export/download/signed-reference/use`
- existing generate request DTO: `Layer3ExternalExportDownloadDeliveryRequest`
- existing generate response schema: `layer3.external_export_download_signed_reference.v1`
- existing use response schema/header: `layer3.external_export_download_signed_reference_use.v1`
- existing rendered generate control: `#external-export-download-signed-reference-generate`
- existing rendered use control: `#external-export-download-signed-reference-use`
- existing rendered panel: `#external-export-download-signed-reference-panel`
- existing operation dock target: `[data-operation-target="external-export-download-band"]`
- existing UI shell: `backend/app/review_ui/static/layer3.html`
- existing UI runtime: `backend/app/review_ui/static/layer3.js`
- existing raw mixed browser proof file: `e2e/layer3-workbench.spec.js`

Live source, tests, routes, models, migrations, and checker behavior outrank this planning document.

## Selected Future Boundary

The next implementation-eligible UI pass is exactly:

`raw_mixed_rendered_external_export_download_signed_reference`

That pass may drive the already-rendered same-origin signed-reference controls only after the raw mixed rendered path has recorded `external_export_download_prepared` and associated-cohort delivery UI authority. It must reuse existing backend signed-reference generate/use routes and existing UI controls. It must not add a route, DTO, service, model, migration, source adapter, ingestion path, package mutation path, rendered control, provider URL behavior, connector/destination behavior, public URL behavior, or non-same-origin delivery behavior unless a repo-confirmed blocker is reported first.

## Exact Future Controls

The future implementation should use the existing controls:

- `[data-operation-target="external-export-download-band"]`: opens the existing external export/download operation band in the workbench operation dock.
- `#external-export-download-signed-reference-generate`: requests one server-owned same-origin signed reference.
- `#external-export-download-signed-reference-use`: uses the generated same-origin signed reference.
- `#external-export-download-signed-reference-panel`: displays signed-reference readiness, use, and delivered state.

No manifest picker, upload control, directory picker, source adapter selector, web connector picker, RAG/vector control, provider URL control, connector dispatch control, destination selector, hidden LLM control, auth/security control, full mockup control, package mutation control, replacement-package control, package supersession control, or public URL control may be added by this pass.

## Server Authority Gates

The signed-reference controls may be driven only when all of the following are true in current rendered state and server-returned authority:

- the normal raw mixed rendered flow has reached `external_export_download_prepared`;
- the prepare response carries `external_export_download_record_ref` and `export_download_descriptor_ref`;
- associated-cohort delivery UI authority reports `associated_cohort_external_export_download_delivery_ui_ready`;
- `LAYER3_SIGNED_REFERENCE_SECRET` is configured in the review-browser test server for browser proof;
- signed-reference generation returns durable server state with `server_hmac_with_durable_state`, `single_use`, and use count `0`;
- signed-reference use returns `external_export_download_signed_reference_delivered`;
- rendered use control disables after use so the UI does not invite a backend replay-denied action;
- no stale-preview, recovery, cancellation, rerun, provider/public URL, connector/destination, replacement, supersession, or mutation blocker is active.

The browser must not manufacture signed-reference tokens, token ids, receipt ids, provider URLs, connector authority, destination authority, or durable token authority.

## Negative Invariants

This freeze admits no:

- production backend route, DTO, service, model, or migration change;
- source-family expansion beyond `dataset_version` and `aps_content_document`;
- source adapter registry behavior;
- local upload or local-directory ingestion;
- arbitrary local path input;
- web connector retrieval;
- RAG/vector retrieval or index creation;
- provider/public URL or signed public URL generation;
- real connector or destination dispatch;
- broad package mutation or reconstruction;
- package replacement or package supersession;
- package payload rewrite outside the already-admitted package-construction commit behavior;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

There is no frontend-only durable authority.
