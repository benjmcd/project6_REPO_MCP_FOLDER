# Source-Directory Hybrid Context Packet To Output-Handoff Rendered Status Extension Freeze

Freeze doc: `911_SOURCE_DIRECTORY_HYBRID_CONTEXT_PACKET_TO_OUTPUT_HANDOFF_RENDERED_STATUS_EXTENSION_FREEZE.md`.

Status: source-directory hybrid context packet-to-output-handoff rendered status extension frozen for `source_directory_hybrid_context_packet_to_output_handoff_rendered_status_extension_freeze`.

Predecessor audit doc: `910_FINAL_FULL_MOCKUP_PROGRAM_READINESS_AUDIT_AFTER_REPRESENTATIVE_SCENARIO_PROOF.md`.

Current-main checkpoint before this freeze: `f870d00a089b8c7f976a611eb1f4b44476a1c621`.

Freeze branch: `codex/l3-source-handoff-rendered-status-freeze`.

Selected freeze mode: `single_existing_rendered_control_extension_freeze`.

Selected target: `source_directory_hybrid_context_packet_to_output_handoff_rendered_status_extension`.

Selected implementation action after freeze sync: `implement_source_directory_hybrid_context_packet_to_output_handoff_rendered_status_extension_after_freeze_sync`.

## Why This Target

Doc 910 rejected full mockup program activation because the program still lacks per-control route, state, durable authority, headed browser proof, headless browser proof, and security proof for every critical mockup operator journey. It selected one bounded next pass: extend an already-rendered source-directory hybrid control with status visibility over the current-main source-to-output-to-handoff route/state chain.

This freeze keeps that selection narrow. The follow-up implementation may expose status/readiness facts already admitted by current-main server authority, but it must not create a new backend route, mutate packages, widen source selection, dispatch connectors, introduce provider/public URL runtime, or promote the mockup frame into durable authority.

Grill-me challenge outcome: the first question was whether the next target should be full-program activation, a new mockup write screen, a new backend route, or a rendered extension over existing source-directory hybrid authority. Repo inspection answers that without user input: current main already has the representative API proof and already has the rendered delivery control, while full-program activation still lacks complete per-control proof. The adequate target is therefore this single existing rendered control extension.

## Canonical Authority

Canonical source of truth remains current repo runtime behavior, not the mockup asset:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`
- `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/status`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/commit`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/review/submit`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/prepare`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status`
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver`
- `LAYER3_SOURCE_INGESTION_DIR`
- `L3SourceDirectoryIngestionBatch`
- `L3SourceDirectoryIngestionFile`
- `L3MaterialSnapshot`
- `L3OutputPackage`
- `L3ReconciliationRecord.summary_json`

## Rendered Surface Contract

The future rendered extension is allowed to attach only to the existing Layer 3 workbench surface:

- `/review/layer3 #source-directory-ingestion-rendered-controls`
- `/review/layer3 #source-directory-hybrid-external-export-download-delivery-form`
- `/review/layer3 #source-directory-hybrid-external-export-download-delivery-panel`
- `/review/layer3 #source-directory-hybrid-external-export-download-delivery-authority`
- `/review/layer3 #source-directory-hybrid-external-export-download-delivery-status`
- `/review/layer3 #source-directory-hybrid-external-export-download-delivery-submit`
- `/review/layer3 #mockup-output-review-package-handoff-projection`, read-only reference only if status is mirrored into the mockup frame
- `/review/layer3 #mockup-execution-lanes`, read-only reference only if status is mirrored into the mockup frame
- `/review/layer3 #mockup-fixture-scenario`, static scenario context only

Permitted state inputs are limited to:

- `State.sourceDirectoryHybridExternalExportDownloadDeliveryStatus`
- `State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusError`
- `State.sourceDirectoryHybridExternalExportDownloadDeliveryStatusPending`
- `State.sourceDirectoryHybridExternalExportDownloadDelivery`
- `State.sourceDirectoryHybridExternalExportDownloadDeliveryError`
- `State.sourceDirectoryHybridExternalExportDownloadDeliveryPending`
- existing source-directory hybrid authority packet parsing in `sourceDirectoryHybridExternalExportDownloadDeliveryPayload`
- existing session/package/handoff/export state only when already present in `State.sessionSummary` or the existing package/handoff/export panels

## Future Implementation Proof Contract

The follow-up implementation must prove all of these before it can be considered complete:

1. Page-level static proof preserves `test_layer3_source_directory_hybrid_delivery_control_is_bounded`.
2. A focused page test proves the new rendered status extension names the server-authoritative route/state sources and remains fail-closed when authority is missing.
3. Focused headless Chromium proof covers the status extension in unavailable, status-ready, and delivery-submitted states.
4. Focused headed Chromium proof covers the same states and reports no divergence from headless behavior.
5. Browser proof reports no console errors, no page errors, and no mobile overflow for the status extension.
6. The rendered extension does not expose raw local paths, raw payload refs, package payload bytes, provider/public URLs, signed URLs, connector destinations, credentials, browser supplied bytes, or browser-storage authority.
7. No frontend-only durable authority is introduced; browser state remains a transient projection of server authority.
8. The implementation does not create a new backend route, DTO, model, migration, service behavior, or runtime action.
9. The implementation does not mutate `L3OutputPackage`, package payload files, or `L3ReconciliationRecord.summary_json`.
10. The implementation does not enable provider-public delivery, provider-private signed URL runtime, connector dispatch, destination write, network egress, package payload rewrite, source package row mutation, broad RAG/vector/model/provider runtime, or full mockup activation.

## Deferred Scope

Still blocked after this freeze:

- full mockup program activation
- mockup-frame write controls without complete route/state/proof contracts
- broad source picker and caller path/directory/file-byte/URL/glob/recursive controls
- real connector/destination dispatch
- provider/public URL runtime
- broad RAG/vector/hidden LLM/model/provider runtime
- optional-tool runtime
- auth/security behavior
- browser-storage authority and frontend-only durable authority
- package mutation/reconstruction expansion

## Whole-Program Road Map

Immediate next pass after this freeze is synced to current main: implement `source_directory_hybrid_context_packet_to_output_handoff_rendered_status_extension` as a bounded rendered status extension over existing routes and state.

Next proof pass: run page tests plus focused headless and headed Chromium proof, including no console/page errors, no mobile overflow, and no sensitive authority leakage.

Next sync pass: merge the rendered extension only if checks and review surfaces are clean, then re-run post-merge JSON, checker, page, browser, and diff validation from current main.

Mid-term blocker retirement lanes: freeze and retire source expansion, package mutation/reconstruction, connector/destination dispatch, provider/public URL runtime, broad RAG/vector/model/provider runtime, browser-storage authority, and auth/security as separate lanes with exact contracts.

Program readiness pass: rerun full mockup-to-live coverage/readiness after the rendered extension and blocker lanes are current-main synced; every critical mockup journey must be classified as live, read-only, excluded, or explicitly blocked.

Full activation freeze: only after the readiness pass is clean, create a dedicated full mockup program activation freeze naming every admitted route, state object, durable authority, DOM control, headed/headless browser proof, security proof, and no-go boundary.

Full activation implementation: implement only the controls admitted by the freeze, with server authority for every write/control and no frontend-only durable state.

Post-activation audit: prove all critical journeys from source intake through output review, package, handoff, export/download, and rendered mockup projection; then mark full mockup activation ready only if the entire route/state/browser/security contract passes.

## Explicit Non-Changes

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Executable test behavior introduced by this freeze: `false`.

Production UI behavior introduced by this freeze: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed by this freeze: `false`.

The next exact posture is `current_main_sync_source_directory_hybrid_context_packet_to_output_handoff_rendered_status_extension_freeze_then_implement_rendered_extension`.
