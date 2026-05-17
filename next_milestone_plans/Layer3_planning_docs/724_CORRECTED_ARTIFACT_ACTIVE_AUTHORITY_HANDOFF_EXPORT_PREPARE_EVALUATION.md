# 724 - Corrected Artifact Active Authority Handoff Export Prepare Evaluation

## Status

Status: branch-local runtime hardening and proof for `corrected_artifact_active_authority_handoff_export_prepare`.

Doc: `724_CORRECTED_ARTIFACT_ACTIVE_AUTHORITY_HANDOFF_EXPORT_PREPARE_EVALUATION.md`.

Predecessor current-main sync doc: `723_CORRECTED_ARTIFACT_REPLACEMENT_ACTIVATION_AUTHORITY_EVALUATION_CURRENT_MAIN_SYNC.md`.

Evaluation branch: `codex/l3-corrected-active-handoff-eval`.

Current-main checkpoint before evaluation branch: `d7513bb3e93a41b7457a76fae9b9077b4bd8ea07`.

Selected downstream reader path: `handoff_export_prepare`.

Selected route: `POST /api/v1/layer3/handoff/export/prepare`.

Selected resolver: `resolve_active_replacement_package_authority`.

Evaluation result: `corrected_artifact_active_authority_handoff_export_prepare_proven`.

Runtime behavior change in this pass: `true`.

Test/proof behavior change in this pass: `true`.

## Authority Finding

Current main already contains active package authority projection in `backend/app/services/layer3_workbench.py` for `handoff_export_prepare`.

That reader already calls `resolve_active_replacement_package_authority` from `backend/app/services/layer3_package_replacement_activation.py`, validates package kinds, source output package ids, source payload hashes, active replacement package ids, response-safe active artifact refs, and active artifact hashes, then projects active replacement refs/hashes into:

- the API response;
- the internal handoff export envelope;
- persisted `handoff_export_prepare` reconciliation state; and
- session summary state.

The corrected-artifact activation row from Doc 723 uses the same durable `L3PackageReplacementActivation` target and `L3ReplacementOutputPackage` namespace family, so no new handoff/export route or resolver is required.

## Runtime Hardening

The branch-local API proof exposed two current-main corrected-artifact recorder mismatches that prevented the real API route chain from reaching handoff/export prepare:

1. `backend/app/services/layer3_corrected_package_artifact_set.py` recorded `corrected_package_set_hash` with a corrected-artifact-specific identity schema, while downstream corrected replacement authority expects the replacement package-set identity contract.
2. The same recorder persisted `artifact_namespace: corrected-package-artifacts`, while the materialized server-owned artifacts and downstream manifest/namespace authority use `replacement-package-artifacts`.

This pass hardens only that authority bridge:

- `corrected_package_set_hash` now uses the downstream-compatible `layer3.replacement_package_set.v1` identity shape with package kind, payload ref, and payload hash rows;
- `CORRECTED_PACKAGE_ARTIFACT_NAMESPACE` is aligned to `replacement-package-artifacts`; and
- the existing corrected-artifact set basis, manifest hash, artifact verification, source package vectors, replacement authority, supersession commit, manifest recording, namespace recording, activation, and handoff/export prepare contracts remain bounded to the same server-owned artifact materialization rail.

## Added Proof

This branch adds focused API regression proof in `backend/tests/test_layer3_api.py`.

The added test `test_layer3_api_handoff_export_prepare_applies_corrected_artifact_active_authority` runs the real API chain:

1. package review submit;
2. package mutation preview;
3. server-owned replacement artifact materialization;
4. `POST /api/v1/layer3/package/corrected-artifact-set/record`;
5. `POST /api/v1/layer3/package/replacement-set/record-from-corrected-artifact-set`;
6. `POST /api/v1/layer3/package/supersession/commit-from-corrected-artifact-set-authority`;
7. `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-corrected-artifact-set-authority`;
8. `POST /api/v1/layer3/package/replacement-namespace/record-from-corrected-artifact-manifest-authority`;
9. `POST /api/v1/layer3/package/replacement-activation/commit`; and
10. `POST /api/v1/layer3/handoff/export/prepare`.

The proof verifies that handoff/export prepare:

- applies corrected-artifact active package authority;
- returns active replacement artifact refs/hashes as the effective payload refs/hashes;
- persists the same active projection into the handoff export envelope;
- persists the same active projection into reconciliation `handoff_export_prepare` state;
- preserves source `L3OutputPackage` rows;
- creates no `ConnectorRun` rows;
- creates no `ConnectorRunTarget` rows;
- performs no package payload rewrite;
- performs no source package mutation;
- performs no new file write during handoff/export prepare;
- exposes no raw temp path in active payload refs; and
- replays duplicate handoff/export prepare as `already_prepared`.

Observed branch-local validation:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_handoff_export_prepare_applies_corrected_artifact_active_authority -q
```

Result observed: `1 passed`.

Additional branch-local validation after the broader API-surface check:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py -q
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_handoff_export_prepare_applies_corrected_artifact_active_authority .\backend\tests\test_layer3_api.py::test_layer3_api_handoff_export_prepare_applies_active_replacement_authority .\backend\tests\test_layer3_package_replacement_activation.py::test_package_replacement_activation_accepts_corrected_artifact_namespace_set .\backend\tests\test_layer3_replacement_package_artifact_manifest.py::test_replacement_package_artifact_manifest_from_corrected_artifact_set_records_redacted_manifest .\backend\tests\test_layer3_replacement_package_namespace.py::test_replacement_package_namespace_from_corrected_manifest_records_complete_set -q
python -m py_compile .\backend\app\services\layer3_corrected_package_artifact_set.py .\tools\l3-progress-check.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
```

Additional results observed: `183 passed`; `5 passed`; py-compile passed; Layer 3 progress state check: `PASS`; Layer 3 target-selection validation: `PASS (frozen)`.

## Still Blocked

This pass does not add a route, DTO, model, migration, rendered UI, rendered UI authority, connector run, connector run target, connector invocation, destination write, credentials, external network egress, provider-public delivery/use, raw public URL exposure, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, delivery rerun, package mutation beyond the already-frozen corrected artifact authority bridge, source expansion, RAG/vector behavior, auth/security behavior, full mockup activation, frontend-durable authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, or hidden LLM planning.

## Next Posture

The next exact posture after this branch merges is `await_current_main_sync_for_corrected_artifact_active_authority_handoff_export_prepare_evaluation`.

After the evaluation is current-main synced, the next exact posture should be `select_next_downstream_active_package_authority_reader_after_corrected_artifact_handoff_export_prepare_sync`. The likely next reader is the first delivery/export path after handoff/export prepare that must carry corrected active package authority toward controlled outbox/export/delivery, but that must be selected in a separate current-main posture.
