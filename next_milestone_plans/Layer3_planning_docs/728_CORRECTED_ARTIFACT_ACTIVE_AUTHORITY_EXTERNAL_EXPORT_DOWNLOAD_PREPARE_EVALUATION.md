# 728 - Corrected Artifact Active Authority External Export Download Prepare Evaluation

## Status

Status: branch-local proof for `corrected_artifact_active_authority_external_export_download_prepare`.

Doc: `728_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_EVALUATION.md`.

Predecessor current-main sync doc: `727_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_APS_HANDOFF_DISPATCH_EVALUATION_CURRENT_MAIN_SYNC.md`.

Evaluation branch: `codex/l3-corrected-download-prepare`.

Current-main checkpoint before evaluation branch: `77b9419670c1b83e95103d3ccb10573a0b64fe51`.

Selected downstream reader path: `external_export_download_prepare`.

Selected route: `POST /api/v1/layer3/handoff/export/download/prepare`.

Selected reader source: `resolve_active_replacement_package_payload_authority`.

Evaluation result: `corrected_artifact_active_authority_external_export_download_prepare_proven`.

Runtime behavior change in this pass: `false`.

Test/proof behavior change in this pass: `true`.

## Authority Finding

Current main already contains active package payload authority adoption in `backend/app/services/layer3_workbench.py` for `external_export_download_prepare`.

That reader resolves active package payload authority, validates source output package ids, package kinds, source payload hashes, response-safe active artifact refs, active artifact hashes, and recorded APS dispatch authority, then projects active replacement refs/hashes into:

- the external export/download prepare response;
- persisted `external_export_download_prepare` reconciliation state; and
- the session summary projection returned by `GET /api/v1/layer3/session/{session_id}`.

The corrected-artifact activation row from Doc 724 through Doc 727 uses the same durable `L3PackageReplacementActivation` target and complete `L3ReplacementOutputPackage` namespace family consumed by the existing external export/download prepare reader path. No new external export/download route, DTO, model, migration, or service runtime is required for this corrected-artifact bridge.

## Added Proof

This branch adds focused API regression proof in `backend/tests/test_layer3_api.py`.

The added test `test_layer3_api_external_export_download_prepare_applies_corrected_artifact_active_authority` runs the real API chain:

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
11. APS handoff dispatch; and
12. external export/download prepare.

The proof verifies that external export/download prepare:

- applies corrected-artifact active package authority;
- uses active replacement artifact refs/hashes as effective payload refs/hashes;
- records the corrected active projection into `external_export_download_prepare` reconciliation state;
- projects the corrected active state through the session summary surface;
- preserves source `L3OutputPackage` rows;
- preserves replacement namespace rows;
- creates no `AnalysisArtifact` rows;
- creates no `ConnectorRun` rows;
- creates no `ConnectorRunTarget` rows;
- creates no package payload rewrite;
- exposes response-safe active artifact refs rather than raw temp paths;
- keeps browser download, download URL, connector dispatch, destination selection, and generic downstream dispatch disabled; and
- replays duplicate external export/download prepare as `already_prepared`.

Observed branch-local validation:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_external_export_download_prepare_applies_corrected_artifact_active_authority -q
```

Result observed: `1 passed`.

## Still Blocked

This pass does not add a route, DTO, model, migration, rendered UI, rendered UI authority, connector invocation, destination write, credentials, external network egress, provider-public delivery/use, raw public URL exposure, signed URL generation, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, delivery rerun, external export/download delivery adoption, connector-local receipt adoption, local outbox write adoption, provider-private handoff adoption, external local export adoption, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact posture after this branch merges is `await_current_main_sync_for_corrected_artifact_active_authority_external_export_download_prepare_evaluation`.

After the evaluation is current-main synced, the next exact posture should be `select_next_downstream_active_package_authority_reader_after_corrected_artifact_external_export_download_prepare_sync`.

The likely next reader is `external_export_download_deliver`, but that must be selected in a separate current-main posture.
