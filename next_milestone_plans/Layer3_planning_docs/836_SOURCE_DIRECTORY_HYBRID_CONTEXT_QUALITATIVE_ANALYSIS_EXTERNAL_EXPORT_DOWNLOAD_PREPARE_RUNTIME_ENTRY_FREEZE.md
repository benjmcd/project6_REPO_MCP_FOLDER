# 836 Source Directory Hybrid Context Qualitative Analysis External Export Download Prepare Runtime Entry Freeze

## Current-Main Selection

- Base authority: `project6-origin/main` at `7d341da135a0`.
- Predecessor sync: `835_SOURCE_DIRECTORY_HYBRID_CONTEXT_QUALITATIVE_ANALYSIS_STATUS_CURRENT_MAIN_SYNC.md`.
- Selected posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_hybrid_status_review_fix_sync`.
- Selected gap: source-directory hybrid context-packet qualitative-analysis external export/download prepare readiness.
- Selected route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare`.
- Runtime branch: `codex/l3-next-gap-after-835`.

## Admitted Runtime

This slice admits one backend/API prepare-only reader that:

- Recomputes current source-directory hybrid context-packet qualitative-analysis authority from the request payload.
- Requires existing approved package-review submit authority and existing handoff/export prepare authority.
- Requires `operator_decision: prepare_source_directory_hybrid_external_export_download`.
- Requires `external_export_download_target: source_directory_hybrid_context_packet_qualitative_analysis_package_download_reference`.
- Requires `download_mode: reference_only_prepare`.
- Validates `prepare_record_ref`, `handoff_export_state`, `handoff_export_envelope_ref`, package ids, package kinds, and payload hashes against stored current package authority.
- Records `external_export_download_prepared` readiness in the existing reconciliation/session summaries.
- Returns a redacted descriptor reference and supports idempotent replay as `already_prepared`.
- Extends the read-only status surface to report the prepared readiness state when present.

## Required Redactions And Invariants

- Package payload references remain redacted.
- No raw local path is exposed.
- No browser download, same-origin delivery, provider URL, signed URL, connector dispatch, destination write, credential use, network egress, or frontend durable authority is activated.
- The prepare reader must not create package rows, rewrite package payloads, mutate source package rows, create replacement packages, create new source rows, create retrieval rows, create context-packet rows, create qualitative-analysis rows, or create connector rows.

## Explicitly Not Admitted

- Same-origin delivery or browser download.
- Provider-public delivery/use.
- Provider-private signed URL behavior or signed-reference use.
- Connector dispatch, destination selection, real connector invocation, credentials, receipts, or network egress.
- Package payload rewrite, package mutation/reconstruction, source package row mutation, replacement authority, or supersession commit.
- Persistent vector stores, durable embedding rows, durable retrieval rows, or RAG execution.
- Prompt/model/provider qualitative generation runtime.
- New source family expansion, arbitrary local-directory ingestion, PDFs, OCR, Office documents, binaries, web connectors, or recursive ingestion.
- Frontend durable controls or rendered UI activation.
- Raw vector exposure, raw package payload exposure, or raw local path exposure.

## Proof Targets

- External export/download prepare records readiness only after handoff/export prepare authority exists and matches current recomputed hybrid qualitative-analysis authority.
- External export/download prepare rejects stale package payload authority.
- External export/download prepare supports idempotent replay as `already_prepared`.
- The read-only status route reports existing external export/download prepare readiness without enabling download or delivery.
- No forbidden downstream, provider, connector, network, frontend, package rewrite, or source mutation state is created.

## Next Posture

After merge and current-main sync, await a narrow sync pass for this runtime. Do not continue additional same-family package/export/active-authority proof loops unless current-main evidence shows a concrete unresolved defect or named downstream reader.
