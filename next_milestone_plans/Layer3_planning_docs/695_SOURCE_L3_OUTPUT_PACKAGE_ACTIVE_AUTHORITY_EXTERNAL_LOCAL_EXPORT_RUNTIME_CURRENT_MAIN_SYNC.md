# 695 - Source L3 Output Package Active Authority External Local Export Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_l3_output_package_active_authority_external_local_export_runtime`.

Doc: `695_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_EXTERNAL_LOCAL_EXPORT_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `694_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_EXTERNAL_LOCAL_EXPORT_RUNTIME_PROOF.md`.

Runtime PR: `#1299`.

Runtime branch: `codex/l3-active-authority-external-export-impl`.

Runtime branch commit: `065498cfb12c26a5a0e9e8d2cf8fbeb94a399762`.

Runtime merge commit: `bfe78692c3272aecf30e5b64d1f21b1751f37119`.

Selected reader path now synced: `external_local_export`.

Selected route now synced: `POST /api/v1/layer3/handoff/connector/local-outbox/external-local-export/write`.

Selected operator action now synced: `adopt_active_replacement_package_authority_for_external_local_export`.

Selected validation seam now synced: recorded `local_outbox_provider_private_handoff`, `server_owned_local_outbox_write`, `server_owned_local_outbox_target`, `connector_local_destination_receipt`, `connector_dispatch_record`, `external_export_download_prepare`, local outbox artifact and manifest hash/size validation, and server-configured `LAYER3_EXTERNAL_LOCAL_EXPORT_DIR` target authority.

Synced result: `current_main_synced_source_l3_output_package_active_authority_external_local_export_runtime`.

Runtime behavior change synced: `false`.

## Merge Gate

GitHub checks before merge:

- `backend-layer3-api`: `SUCCESS` in `2m59s`;
- `test`: `SUCCESS` in `3m34s`.

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

Result: both passed on `project6-origin/main` at `bfe78692c3272aecf30e5b64d1f21b1751f37119`.

## Synced Runtime State

Current main now proves `external_local_export` consumes active replacement package authority on the admitted associated-cohort APS evidence-bundle path after local-outbox provider-private handoff. It carries active replacement refs/hashes from handoff/export prepare through APS handoff dispatch, external export/download prepare, external export/download delivery, connector dispatch record, connector-local receipt, fake target, server-owned local outbox write, local-outbox provider-private handoff, and external local export while preserving source `L3OutputPackage` rows and `uq_l3_output_package_session_kind`.

The synced proof shows external local export writes only durable local outbox artifact and manifest bytes authorized by recorded active-authority local outbox write and provider-private handoff state. It preserves redacted `external-local-export://...` refs, keeps raw storage paths, configured external local export paths, raw `source_artifact_ref`, and `destination_path` out of responses and authority snapshots, creates only the durable `L3ExternalLocalExportReceipt` plus one audit event, creates no `ConnectorRun`, `ConnectorRunTarget`, provider-private signed URL receipt, or provider-public delivery state, enables no real connector invocation or external provider/object-store write, leaks no provider token or provider object key, and changes no service runtime behavior.

## Non-Admission Boundary

This sync admits no rendered activation controls, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch beyond the selected external local export write, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, raw provider token exposure, raw provider object key exposure, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact posture is `select_package_mutation_reconstruction_named_operator_action_after_source_l3_output_package_active_authority_external_local_export_runtime_sync`.

The next current-main decision should select exactly one package mutation/reconstruction operator action, such as revise package, supersede package, or rebuild package from corrected artifacts. It should not start runtime until that action is named, frozen, and bounded. Source expansion, RAG/vector behavior, provider-public delivery/use, real connector invocation, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, broad auth/security, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, and raw local path exposure remain blocked.
