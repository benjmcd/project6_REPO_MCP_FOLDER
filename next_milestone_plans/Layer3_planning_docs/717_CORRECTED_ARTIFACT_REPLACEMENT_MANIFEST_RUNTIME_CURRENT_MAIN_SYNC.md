# 717 - Corrected Artifact Replacement Manifest Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `corrected_artifact_replacement_manifest_runtime`.

Doc: `717_CORRECTED_ARTIFACT_REPLACEMENT_MANIFEST_RUNTIME_CURRENT_MAIN_SYNC.md`.

Synced runtime proof doc: `716_CORRECTED_ARTIFACT_REPLACEMENT_MANIFEST_RUNTIME_PROOF.md`.

Runtime PR: `#1321`.

Runtime branch: `codex/l3-corrected-artifact-manifest-runtime`.

Runtime branch commit: `7317dc621e1886e9f5103a3fa841fa1bbef1e2c7`.

Runtime merge commit: `9e8ae363994e279e6744b0f4e309f6444856880f`.

Current-main checkpoint after merge: `9e8ae363994e279e6744b0f4e309f6444856880f`.

Sync branch: `codex/l3-corrected-artifact-manifest-runtime-sync`.

Selected runtime now synced: `corrected_artifact_replacement_manifest_from_supersession_authority`.

Live route now synced: `POST /api/v1/layer3/package/replacement-artifact/manifest/record-from-corrected-artifact-set-authority`.

Owner service now synced: `backend/app/services/layer3_replacement_package_artifact_manifest.py`.

API owner now synced: `backend/app/api/layer3.py`.

Durable target now synced: `L3ReplacementPackageArtifactManifest`.

Source authority now synced: `L3CorrectedPackageArtifactSet`.

Replacement authority now synced: `L3ReplacementPackageSetAuthority`.

Supersession authority now synced: `L3PackageSupersessionCommit`.

Request mode now synced: `replacement_package_artifact_manifest_from_corrected_artifact_set_authority`.

Operator decision now synced: `record_replacement_package_artifact_manifest_from_corrected_artifact_set_authority`.

Runtime behavior already merged by the runtime PR: `true`.

Runtime behavior in this sync: `false`.

## Merge Gate

Before merge, PR `#1321` had:

- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `[]`;
- reviews: `[]`;
- latestReviews: `[]`;
- reviewThreads totalCount: `0`;
- unresolved current reviewThreads: `0`;
- mergeability: `MERGEABLE`; and
- merge state: `CLEAN`.

Post-merge local validation on current main at `9e8ae363994e279e6744b0f4e309f6444856880f` passed:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py .\backend\app\services\layer3_replacement_package_artifact_manifest.py .\backend\app\api\layer3.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
python -m pytest .\backend\tests\test_layer3_replacement_package_artifact_manifest.py -q
python -m pytest .\backend\tests\test_layer3_api.py -q -k "corrected_artifact_set or openapi_contracts or workbench_error_responses"
git diff --check
```

Observed targeted pytest results:

- `test_layer3_replacement_package_artifact_manifest.py`: `7 passed`; and
- targeted `test_layer3_api.py`: `16 passed, 164 deselected`.

## Current-Main Result

Current main now contains the corrected-artifact replacement manifest bridge.

The synced runtime proves current main can record and replay `L3ReplacementPackageArtifactManifest` from `L3CorrectedPackageArtifactSet`, corrected-artifact `L3ReplacementPackageSetAuthority`, and corrected-artifact `L3PackageSupersessionCommit` without browser/caller supplied replacement refs, hashes, byte sizes, manifest hash, authority basis hash, paths, URLs, credentials, connector ids, source expansion fields, RAG/vector fields, auth/security context, browser state, or frontend-durable state.

The route derives replacement artifact refs/hashes, verified byte sizes, artifact manifest hash, and authority basis hash server-side, then returns redacted artifact refs and a redacted returned manifest snapshot.

## Still Blocked

This sync admits no new capability beyond recording current-main state for PR `#1321`. Replacement namespace row creation, package replacement activation, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, re-running handoff/export or delivery, provider-public delivery/use, connector/destination dispatch, `ConnectorRun` creation, `ConnectorRunTarget` creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, rendered UI authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, and hidden LLM planning remain blocked.

## Next Posture

The next exact current-main posture is `evaluate_corrected_artifact_replacement_namespace_authority_after_manifest_runtime_sync`.

That evaluation must stay inside the selected package mutation/reconstruction surface and determine whether current main can safely bridge the corrected-artifact replacement manifest authority into replacement namespace or active-package authority, or whether a separate implementation-entry freeze is required. It may inspect `backend/app/services/layer3_replacement_package_namespace.py`, `backend/app/services/layer3_replacement_package_artifact_manifest.py`, `backend/app/api/layer3.py`, `L3CorrectedPackageArtifactSet`, `L3ReplacementPackageSetAuthority`, `L3PackageSupersessionCommit`, `L3ReplacementPackageArtifactManifest`, and any existing package activation authority. It must not implement namespace rows, activation rows, package payload rewrite, source package row mutation, handoff/export reruns, delivery reruns, connector/destination behavior, source expansion, RAG/vector, auth/security, rendered UI, or frontend-durable behavior without a later explicit freeze.
