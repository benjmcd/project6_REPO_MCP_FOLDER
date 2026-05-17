# 683 - Source L3 Output Package Active Authority Connector Local Receipt Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_l3_output_package_active_authority_connector_local_receipt_runtime`.

Doc: `683_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_CONNECTOR_LOCAL_RECEIPT_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `682_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_CONNECTOR_LOCAL_RECEIPT_RUNTIME_PROOF.md`.

Runtime PR: `#1287`.

Runtime branch: `codex/l3-active-authority-local-receipt-impl`.

Runtime branch commit: `1290507eff93c0a03be4bcdbfe08ba1b2e7b8529`.

Runtime merge commit: `3603115d70f53974eb464856827e8c19bf7966c5`.

Selected reader path now synced: `connector_local_destination_receipt`.

Selected route now synced: `POST /api/v1/layer3/handoff/connector/local-destination/receipt`.

Selected validation seam now synced: `external_export_download_delivery` authority revalidation through `external_export_download_prepare` and `_external_export_download_prepare_payload_for_delivery`.

Synced result: `current_main_synced_source_l3_output_package_active_authority_connector_local_receipt_runtime`.

Runtime behavior change synced: `false`.

## Merge Gate

GitHub checks before merge:

- `backend-layer3-api`: `SUCCESS` in `2m45s`;
- `test`: `SUCCESS` in `3m22s`.

Review and thread gate before merge:

- PR comments: empty.
- PR reviews: empty.
- PR latestReviews: empty.
- PR reviewThreads totalCount: `0`.
- PR unresolved reviewThreads: `0`.
- Mergeability before merge: `MERGEABLE`.
- Merge state before merge: `CLEAN`.

Post-merge current-main validation:

```powershell
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
```

Result: both passed on `project6-origin/main` at `3603115d70f53974eb464856827e8c19bf7966c5`.

## Synced Runtime State

Current main now proves `connector_local_destination_receipt` consumes active replacement package authority for `POST /api/v1/layer3/handoff/connector/local-destination/receipt` on the admitted associated-cohort APS evidence-bundle authority path.

The synced proof carries active replacement refs/hashes from handoff/export prepare through APS handoff dispatch, external export/download prepare, external export/download delivery, connector dispatch record, and connector-local receipt. The receipt accepts only the APS bundle artifact hash and size authorized by recorded active-authority readiness/delivery and connector dispatch state. The accepted artifact ref remains response-safe as `artifact://layer3-internal-fake-local-destination-redacted`.

Source `L3OutputPackage` rows, source payload refs/hashes, package ids, package summaries, and `uq_l3_output_package_session_kind` remain unchanged. `L3ConnectorLocalDestinationReceipt` remains durable receipt/status authority and does not expose `source_artifact_ref` in the authority snapshot. No `ConnectorRun` or `ConnectorRunTarget` rows are created. No external connector invocation or destination write is enabled. No `download_url`, `public_url`, `signed_url`, or `local_path` is exposed. No additional files are written by connector-local receipt.

The single-item APS path remains outside connector dispatch admission; connector dispatch remains associated-cohort APS evidence-bundle only.

## Non-Admission Boundary

This sync admits no rendered activation controls, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied delivery bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact posture is `select_next_active_package_authority_reader_or_rendered_activation_control_after_connector_local_receipt_runtime_sync`.

The next current-main decision should select exactly one follow-on: server-owned local outbox active-authority adoption if receipt proof shows the next stale reader is downstream local outbox creation, rendered activation controls if operator review/selection is the immediate need, or package rebuild/payload rewrite only if activation by indirection is insufficient.
