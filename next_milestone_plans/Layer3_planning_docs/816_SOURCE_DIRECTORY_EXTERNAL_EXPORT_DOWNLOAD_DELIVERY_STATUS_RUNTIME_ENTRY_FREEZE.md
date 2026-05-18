# 816 - Source Directory External Export Download Delivery Status Runtime Entry Freeze

## Status

Status: branch-local runtime implementation entry for `source_directory_external_export_download_delivery_status_runtime`.

Runtime doc: `816_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_RUNTIME_ENTRY_FREEZE.md`.

Runtime branch: `codex/l3-next-gap-after-delivery`.

Predecessor current-main sync doc: `815_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_CURRENT_MAIN_SYNC.md`.

Selected from posture: `select_next_named_layer3_end_to_end_gap_after_source_directory_external_export_download_delivery_sync`.

Selected implementation action: `implement_source_directory_external_export_download_delivery_status_after_source_directory_external_export_download_delivery_sync`.

Runtime behavior change: `true`.

## Freeze

The selected slice is a read-only operator-visible JSON status reader for the already-admitted source-directory external export/download delivery authority.

Route:

`POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver/status`

Schema:

`layer3.source_directory_qualitative_analysis_external_export_download_delivery_status.v1`

Mode:

`source_directory_qualitative_analysis_external_export_download_delivery_status_authority`

Source gate:

`816_SOURCE_DIRECTORY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_RUNTIME_ENTRY_FREEZE`

The status reader accepts the same delivery request contract used by the source-directory external export/download delivery reader. It revalidates the delivery authority through the same server-side package, prepare, review, hash, and artifact checks, but returns redacted JSON status instead of streaming the package artifact.

## Admitted Behavior

The status reader may report:

- request id, schema id, schema version, server time, runtime mode, status, delivery status, delivery availability, and delivery state;
- the branch-local status source gate and the validated underlying delivery source gate;
- external export/download record reference, descriptor reference, output package id, package kind, and package payload hash;
- same-origin delivery capability flags already admitted by the source-directory delivery runtime;
- negative capability flags for provider URLs, signed URLs, connector dispatch, network egress, frontend-durable authority, package rewrite, source package row mutation, and raw path exposure;
- response headers and delivery authority only in the already redacted form produced by the delivery validator.

## Non-Admission Boundary

This freeze does not admit byte streaming through the status route, provider-public delivery/use, provider-private signed URLs, connector/destination dispatch, real connector invocation, credentials, network egress, auth/security broadening, frontend-durable authority, frontend-rendered controls, package payload writes, package payload rewrites, package mutation/reconstruction, source package row mutation, raw local path exposure, arbitrary source ingestion, a new source family, RAG/vector indexing expansion, embedding generation expansion, persistent vector store behavior, prompt/model/provider runtime, qualitative generation runtime, or full mockup activation.

## Proof Target

The targeted proof must show:

- the status route returns `ready` for a prepared source-directory external export/download package;
- the status route returns no package bytes and marks `delivery_streaming_performed` as `false`;
- the returned refs and payload hash match the prepared package authority;
- raw source and storage paths are absent from the JSON response;
- provider URLs, signed URLs, connector dispatch, network egress, package mutation, source package row mutation, and frontend-durable authority remain disabled;
- stale package payload hashes fail closed with the existing delivery payload-hash mismatch error;
- the actual delivery route still streams the same existing package artifact.

## Next Posture

After this runtime branch is review-cleared, merged, and synced to current main, the next exact posture is `await_current_main_sync_for_source_directory_external_export_download_delivery_status_runtime`.
