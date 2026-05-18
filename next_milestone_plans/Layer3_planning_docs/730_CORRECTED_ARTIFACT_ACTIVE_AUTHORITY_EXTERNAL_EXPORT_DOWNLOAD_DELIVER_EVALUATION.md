# 730 - Corrected Artifact Active Authority External Export Download Deliver Evaluation

## Status

Status: branch-local proof for `corrected_artifact_active_authority_external_export_download_deliver`.

Doc: `730_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_EXTERNAL_EXPORT_DOWNLOAD_DELIVER_EVALUATION.md`.

Predecessor current-main sync doc: `729_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_EVALUATION_CURRENT_MAIN_SYNC.md`.

Evaluation branch: `codex/l3-corrected-download-deliver`.

Current-main checkpoint before evaluation branch: `8a99731d7504a5efe8362d9777a8e1f97d853bc0`.

Selected downstream reader path: `external_export_download_deliver`.

Selected route: `POST /api/v1/layer3/handoff/export/download/deliver`.

Selected reader source: recorded `external_export_download_prepare` state via `_external_export_download_prepare_from_reconciliation`, revalidated through `external_export_download_prepare`.

Evaluation result: `corrected_artifact_active_authority_external_export_download_deliver_proven`.

Runtime behavior change in this pass: `false`.

Test/proof behavior change in this pass: `true`.

## Authority Finding

Current main already contains same-origin external export/download delivery in `backend/app/services/layer3_workbench.py`.

The delivery reader reloads the recorded `external_export_download_prepare` reconciliation state, rejects mismatched delivery request fields, revalidates readiness by calling `external_export_download_prepare` with source artifact validation disabled, rolls back the read transaction before artifact validation, then streams only the existing APS bundle artifact through the bounded same-origin delivery response.

Because Doc 728 and Doc 729 prove corrected-artifact active package authority reaches and persists in `external_export_download_prepare`, the next required proof is that delivery consumes that recorded readiness authority and returns the same-origin APS bundle without widening runtime behavior.

No new external export/download route, DTO, model, migration, rendered UI, or service runtime is required for this corrected-artifact delivery bridge.

## Added Proof

This branch adds focused API regression proof in `backend/tests/test_layer3_api.py`.

The added test `test_layer3_api_external_export_download_deliver_applies_corrected_artifact_active_authority` runs the real API chain:

1. package review submit;
2. package mutation preview;
3. server-owned replacement artifact materialization;
4. corrected artifact-set recording;
5. corrected replacement package-set authority;
6. corrected supersession commit;
7. corrected replacement artifact manifest;
8. corrected replacement namespace recording;
9. replacement activation;
10. handoff/export prepare;
11. APS handoff dispatch;
12. external export/download prepare; and
13. external export/download deliver.

The proof verifies that external export/download deliver:

- consumes corrected-artifact active package authority through recorded external export/download prepare state;
- revalidates readiness through `external_export_download_prepare`;
- keeps active replacement artifact refs/hashes as effective payload refs/hashes in direct delivery authority;
- streams the same-origin APS bundle artifact bytes;
- returns same-origin delivery headers for delivery state, source artifact hash, and readiness record ref;
- exposes response-safe active artifact refs rather than raw temp paths in delivery authority;
- preserves source `L3OutputPackage` rows;
- preserves replacement namespace rows;
- preserves recorded `external_export_download_prepare` readiness state;
- creates no `AnalysisArtifact` rows;
- creates no `ConnectorRun` rows;
- creates no `ConnectorRunTarget` rows;
- creates no new `L3OutputPackage` or `L3ReconciliationRecord` rows;
- creates no files during direct delivery, API delivery, or replay;
- creates no package payload rewrite; and
- replays duplicate external export/download delivery as the same bounded same-origin artifact stream.

Observed branch-local validation:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_external_export_download_deliver_applies_corrected_artifact_active_authority -q
```

Result observed: `1 passed`.

## Still Blocked

This pass does not add a route, DTO, model, migration, service runtime behavior, rendered UI, rendered UI authority, connector invocation, connector-run creation, connector target creation, destination write, credentials, external network egress, provider-public delivery/use, raw public URL exposure, signed URL generation, provider-private signed URL generation, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, external export/download prepare rerun beyond delivery revalidation, connector-local receipt adoption, local outbox write adoption, provider-private handoff adoption, external local export adoption, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact posture after this branch merges is `await_current_main_sync_for_corrected_artifact_active_authority_external_export_download_deliver_evaluation`.

After the evaluation is current-main synced, the next exact posture should be `select_next_downstream_active_package_authority_reader_after_corrected_artifact_external_export_download_deliver_sync`.

The likely next reader is `connector_local_destination_receipt`, but that must be selected in a separate current-main posture.
