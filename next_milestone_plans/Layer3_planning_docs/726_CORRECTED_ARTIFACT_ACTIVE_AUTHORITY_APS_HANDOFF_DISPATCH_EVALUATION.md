# 726 - Corrected Artifact Active Authority APS Handoff Dispatch Evaluation

## Status

Status: branch-local proof for `corrected_artifact_active_authority_aps_handoff_dispatch`.

Doc: `726_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_APS_HANDOFF_DISPATCH_EVALUATION.md`.

Predecessor current-main sync doc: `725_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_HANDOFF_EXPORT_PREPARE_EVALUATION_CURRENT_MAIN_SYNC.md`.

Evaluation branch: `codex/l3-next-reader-select`.

Current-main checkpoint before evaluation branch: `449793c8db30b8b07bd3a08c844ca4c27aa4d49e`.

Selected downstream reader path: `aps_handoff_dispatch`.

Selected route: `POST /api/v1/layer3/handoff/aps/dispatch`.

Selected reader source: `resolve_active_replacement_package_payload_authority`.

Evaluation result: `corrected_artifact_active_authority_aps_handoff_dispatch_proven`.

Runtime behavior change in this pass: `false`.

Test/proof behavior change in this pass: `true`.

## Authority Finding

Current main already contains active package payload authority adoption in `backend/app/services/layer3_workbench.py` for `aps_handoff_dispatch`.

That reader resolves active package payload authority, validates source output package ids, package kinds, source payload hashes, response-safe active artifact refs, active artifact hashes, and matching `handoff_export_prepare` active authority state, then projects active replacement refs/hashes into:

- the APS dispatch response;
- the durable APS evidence-bundle package summary;
- persisted `aps_handoff_dispatch` reconciliation state; and
- session summary state.

The corrected-artifact activation row from Doc 724 / Doc 725 uses the same durable `L3PackageReplacementActivation` target and complete `L3ReplacementOutputPackage` namespace family consumed by the existing APS dispatch reader path. No new APS dispatch route, DTO, model, migration, or service runtime is required for this corrected-artifact bridge.

## Added Proof

This branch adds focused API regression proof in `backend/tests/test_layer3_api.py`.

The added test `test_layer3_api_aps_handoff_dispatch_applies_corrected_artifact_active_authority` runs the real API chain:

1. package review submit;
2. package mutation preview;
3. server-owned replacement artifact materialization;
4. corrected artifact-set recording;
5. corrected replacement package-set authority;
6. corrected supersession commit;
7. corrected replacement artifact manifest;
8. corrected replacement namespace recording;
9. replacement activation;
10. handoff/export prepare; and
11. APS handoff dispatch.

The proof verifies that APS handoff dispatch:

- applies corrected-artifact active package authority;
- uses active replacement artifact refs/hashes as effective payload refs/hashes;
- records the corrected active projection into APS output package summary;
- records the corrected active projection into reconciliation `aps_handoff_dispatch` state;
- preserves source `L3OutputPackage` rows;
- preserves replacement namespace rows;
- creates no `ConnectorRun` rows;
- creates no `ConnectorRunTarget` rows;
- performs no package payload rewrite;
- exposes no raw temp path in active payload refs;
- creates only the bounded APS evidence-bundle package expected by APS dispatch; and
- replays duplicate APS dispatch as `already_dispatched`.

Observed branch-local validation:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_aps_handoff_dispatch_applies_corrected_artifact_active_authority -q
```

Result observed: `1 passed`.

## Still Blocked

This pass does not add a route, DTO, model, migration, rendered UI, rendered UI authority, connector invocation, destination write, credentials, external network egress, provider-public delivery/use, raw public URL exposure, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, delivery rerun, external export/download adoption, connector-local receipt adoption, local outbox write adoption, provider-private handoff adoption, external local export adoption, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact posture after this branch merges is `await_current_main_sync_for_corrected_artifact_active_authority_aps_handoff_dispatch_evaluation`.

After the evaluation is current-main synced, the next exact posture should be `select_next_downstream_active_package_authority_reader_after_corrected_artifact_aps_handoff_dispatch_sync`.

The likely next reader is the first external export/download readiness path after APS handoff dispatch, but that must be selected in a separate current-main posture.
