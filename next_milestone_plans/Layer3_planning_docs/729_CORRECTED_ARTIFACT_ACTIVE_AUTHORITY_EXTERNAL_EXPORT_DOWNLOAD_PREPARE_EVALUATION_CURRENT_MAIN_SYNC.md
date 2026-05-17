# 729 - Corrected Artifact Active Authority External Export Download Prepare Evaluation Current-Main Sync

## Status

Status: current-main proof/control sync for `corrected_artifact_active_authority_external_export_download_prepare_evaluation`.

Doc: `729_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_EVALUATION_CURRENT_MAIN_SYNC.md`.

Synced evaluation doc: `728_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_EVALUATION.md`.

Evaluation PR: `#1333`.

Evaluation branch: `codex/l3-corrected-download-prepare`.

Evaluation branch commit: `9242a471a249aa53724044a9217f4e037ce753b6`.

Evaluation merge commit: `826e1df03c5e0440a62e4fe9f365b46a8a7291de`.

Current-main checkpoint after merge: `826e1df03c5e0440a62e4fe9f365b46a8a7291de`.

Sync branch: `codex/l3-corrected-download-prepare-sync`.

Synced result: `current_main_synced_corrected_artifact_active_authority_external_export_download_prepare_evaluation`.

Evaluation result now synced: `corrected_artifact_active_authority_external_export_download_prepare_proven`.

Runtime behavior introduced by evaluation: `false`.

Runtime behavior in this sync: `false`.

## Merge Gate

Before merge, PR `#1333` had:

- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- merge state: `CLEAN`; and
- merge commit: `826e1df03c5e0440a62e4fe9f365b46a8a7291de`.

Post-merge current-main validation at `826e1df03c5e0440a62e4fe9f365b46a8a7291de` passed:

```powershell
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
```

Observed results: Layer 3 progress state check `PASS`; Layer 3 target-selection validation `PASS (frozen)`.

## Current-Main Result

Current main now records that corrected-artifact active package authority reaches `external_export_download_prepare` through the existing active package payload authority reader path.

PR `#1333` adds proof that the real corrected-artifact API route chain reaches `POST /api/v1/layer3/handoff/export/download/prepare` after handoff/export prepare and APS handoff dispatch, and that external export/download prepare consumes active replacement artifact refs/hashes without adding service runtime behavior.

The synced proof verifies that external export/download prepare applies corrected active package authority and projects active replacement refs/hashes into the response, persisted `external_export_download_prepare` reconciliation state, and session summary state.

## Still Blocked

This sync admits no additional runtime or rendered behavior. Connector invocation, connector-run creation, destination write, credentials, external network egress, provider-public delivery/use, raw public URL exposure, signed URL generation, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, delivery rerun, external export/download delivery adoption, connector-local receipt adoption, local outbox write adoption, provider-private handoff adoption, external local export adoption, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, rendered UI authority, auth/security behavior, frontend-durable authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, and hidden LLM planning remain blocked.

## Next Posture

The next exact current-main posture is `select_next_downstream_active_package_authority_reader_after_corrected_artifact_external_export_download_prepare_sync`.

That selection should choose exactly one downstream reader after external export/download prepare to continue carrying corrected active package authority toward same-origin delivery, local receipt, local outbox, provider-private handoff, and external local export.

The likely next target is `external_export_download_deliver`. That selection must not implement connector invocation, destination write, provider-public delivery/use, package payload rewrite, downstream invalidation, delivery rerun beyond the selected reader, source expansion, RAG/vector behavior, rendered controls, auth/security behavior, or frontend-durable authority unless a separate exact freeze first admits that one slice.
