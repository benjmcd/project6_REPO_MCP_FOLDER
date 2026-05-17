# 679 - Source L3 Output Package Active Authority External Export Download Delivery Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `source_l3_output_package_active_authority_external_export_download_delivery_runtime`.

Doc: `679_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `678_SOURCE_L3_OUTPUT_PACKAGE_ACTIVE_AUTHORITY_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_RUNTIME_PROOF.md`.

Merged PR: `#1283`.

Runtime branch: `codex/l3-active-authority-export-delivery-impl`.

Runtime branch commit: `c11665612a10426ca83f6976f44264e0f98f8671`.

Current-main checkpoint after merge: `48933bc687ee65cf0b042c80652690de6c23003c`.

Selected reader path now synced: `external_export_download_deliver`.

Selected route now synced: `POST /api/v1/layer3/handoff/export/download/deliver`.

Selected validation seam now synced: `external_export_download_prepare` through `_external_export_download_prepare_payload_for_delivery`.

Synced result: `current_main_synced_source_l3_output_package_active_authority_external_export_download_delivery_runtime`.

Runtime behavior change synced: `false`; the merged branch added targeted proof over existing server behavior.

## Merge Gate

PR `#1283` merged doc `678`, the targeted active-authority delivery proof, and associated board, progress manifest, proof manifest, and checker wiring.

Merge gate before merge:

- GitHub `backend-layer3-api`: `SUCCESS` in `2m42s`.
- GitHub `test`: `SUCCESS` in `3m26s`.
- PR comments: empty.
- PR reviews: empty.
- PR latestReviews: empty.
- PR reviewThreads totalCount: `0`.
- PR unresolved reviewThreads: `0`.
- Mergeability: `MERGEABLE`.
- Merge state before merge: `CLEAN`.

## Current-Main Validation

Current-main checkpoint after merge: `48933bc687ee65cf0b042c80652690de6c23003c`.

Current-main validation before this sync:

```powershell
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
```

Results:

- `python .\tools\l3-progress-check.py`: `PASS`.
- `python .\tools\l3-target-selection-validate.py --expect frozen`: `PASS`.

Sync branch validation must include:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Synced Runtime Proof

Current main now proves the exact `external_export_download_deliver` active-authority reader path selected by docs `676` and `677`.

The merged proof extends `backend/tests/test_layer3_api.py::test_layer3_api_aps_handoff_dispatch_applies_active_replacement_authority` through external export/download delivery. It proves active replacement refs/hashes carry from handoff/export prepare through APS handoff dispatch and external export/download prepare into delivery; delivery streams only the APS bundle artifact authorized by recorded readiness; same-key replay returns the same artifact bytes; source `L3OutputPackage` rows and external export/download readiness state remain unchanged; no `ConnectorRun` or `ConnectorRunTarget` rows are created; response headers do not leak `download_url`, `public_url`, `signed_url`, or `connector_run_id`; and delivery writes no additional files.

No service runtime code changed. Current main satisfied the frozen delivery-reader contract through recorded readiness revalidation.

## Non-Admission Boundary

This sync admits no rendered activation controls, connector-local receipt adoption, server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, raw public URL exposure, connector/destination dispatch, ConnectorRun creation, ConnectorRunTarget creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, browser file reads, browser-supplied package bytes, browser-supplied replacement bytes, browser-supplied artifact bytes, browser-supplied delivery bytes, browser-supplied arbitrary artifact refs, browser-supplied arbitrary hashes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact current-main posture is `select_next_active_package_authority_reader_or_rendered_activation_control_after_external_export_download_delivery_runtime_sync`.

That next decision should choose exactly one implementation-bearing package-lifecycle follow-on:

- connector-local receipt active-authority adoption if current evidence shows the next delivery reader still consumes stale source authority;
- rendered activation controls if operator visibility/selection is the immediate need;
- a separately frozen package rebuild or payload rewrite action only if activation by indirection is insufficient.

Do not restart broad no-runtime audits. Server-owned local outbox adoption, provider-private handoff adoption, external local export adoption, package rebuild, package payload rewrite, direct source `L3OutputPackage` mutation, downstream invalidation, re-delivery runtime, provider-public delivery/use, connector/destination dispatch, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, and raw local path exposure remain blocked until exactly selected and frozen.
