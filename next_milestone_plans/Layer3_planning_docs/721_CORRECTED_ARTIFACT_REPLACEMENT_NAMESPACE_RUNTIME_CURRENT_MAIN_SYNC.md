# 721 - Corrected Artifact Replacement Namespace Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `corrected_artifact_replacement_namespace_runtime`.

Doc: `721_CORRECTED_ARTIFACT_REPLACEMENT_NAMESPACE_RUNTIME_CURRENT_MAIN_SYNC.md`.

Synced runtime proof doc: `720_CORRECTED_ARTIFACT_REPLACEMENT_NAMESPACE_RUNTIME_PROOF.md`.

Runtime PR: `#1325`.

Runtime branch: `codex/l3-corrected-artifact-namespace-runtime`.

Runtime branch commit: `2c4b7d9d126c7fdb0b6d74925d5faefd13b3c18e`.

Runtime merge commit: `c73f1ee92eb12450718b9fb4cd83fdde567c5431`.

Current-main checkpoint after merge: `c73f1ee92eb12450718b9fb4cd83fdde567c5431`.

Sync branch: `codex/l3-corrected-artifact-namespace-runtime-sync`.

Selected runtime now synced: `server_computed_replacement_namespace_from_corrected_artifact_manifest_authority`.

Live route now synced: `POST /api/v1/layer3/package/replacement-namespace/record-from-corrected-artifact-manifest-authority`.

Owner service now synced: `backend/app/services/layer3_replacement_package_namespace.py`.

API owner now synced: `backend/app/api/layer3.py`.

Durable target now synced: `L3ReplacementOutputPackage` / `l3_replacement_output_package`.

Source authority now synced: `L3CorrectedPackageArtifactSet`.

Replacement authority now synced: `L3ReplacementPackageSetAuthority`.

Supersession authority now synced: `L3PackageSupersessionCommit`.

Manifest authority now synced: `L3ReplacementPackageArtifactManifest`.

Request mode now synced: `replacement_package_namespace_from_corrected_artifact_manifest_authority`.

Operator decision now synced: `record_replacement_package_namespace_from_corrected_artifact_manifest_authority`.

Runtime behavior already merged by the runtime PR: `true`.

Runtime behavior in this sync: `false`.

## Merge Gate

Before merge, PR `#1325` had:

- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `[]`;
- reviews: one automated `COMMENTED` review from `chatgpt-codex-connector` on original commit `57dece6f97f634338bcccc56978aac7fd80deffb`;
- latestReviews: one automated `COMMENTED` review from `chatgpt-codex-connector`;
- reviewThreads totalCount: `3`;
- unresolved current reviewThreads: `0`;
- resolved reviewThreads: `3`;
- mergeability: `MERGEABLE`; and
- merge state: `CLEAN`.

The automated review threads were addressed before merge:

- atomic namespace-set recording now flushes per row and commits once at the complete set boundary;
- corrected-artifact namespace recording now binds source/corrected artifact vectors back to `L3CorrectedPackageArtifactSet`; and
- `source_expansion` is defined as a forbidden request property in the corrected-manifest namespace API/schema boundary.

Post-merge validation for current main checkpoint `c73f1ee92eb12450718b9fb4cd83fdde567c5431` and this docs-only sync branch:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py .\backend\app\services\layer3_replacement_package_namespace.py .\backend\app\api\layer3.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
python -m pytest .\backend\tests\test_layer3_replacement_package_namespace.py -q
python -m pytest .\backend\tests\test_layer3_api.py -q -k "external_export_download_openapi_contracts or package_openapi_contracts or replacement_package_namespace_from_corrected_manifest"
python -m pytest .\backend\tests\test_layer3_api.py -q
git diff --check
```

Observed targeted pytest results:

- `test_layer3_replacement_package_namespace.py`: `8 passed`;
- targeted `test_layer3_api.py`: `4 passed, 178 deselected`; and
- full `test_layer3_api.py`: `182 passed`.

## Current-Main Result

Current main now contains the corrected-artifact replacement namespace bridge.

The synced runtime proves current main can derive and persist the complete `L3ReplacementOutputPackage` namespace set from a server-verified corrected-artifact authority chain: `L3CorrectedPackageArtifactSet`, corrected-artifact `L3ReplacementPackageSetAuthority`, corrected-artifact `L3PackageSupersessionCommit`, and corrected-artifact `L3ReplacementPackageArtifactManifest`.

The route accepts only authority ids and basis hashes, computes response-safe artifact refs, package schema ids, artifact hashes, authority basis hashes, and deterministic per-kind row idempotency keys server-side, then records or replays namespace rows as one complete transactional set.

## Still Blocked

This sync admits no new capability beyond recording current-main state for PR `#1325`. Package replacement activation, package payload rewrite, package payload writes, source `L3OutputPackage` mutation, downstream invalidation, handoff/export rerun, delivery rerun, provider-public delivery/use, connector/destination dispatch, `ConnectorRun` creation, `ConnectorRunTarget` creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, rendered UI authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, and hidden LLM planning remain blocked.

## Next Posture

The next exact current-main posture is `evaluate_package_replacement_activation_authority_after_corrected_artifact_namespace_runtime_sync`.

That evaluation must stay inside the selected package mutation/reconstruction surface and determine whether current main can safely bridge the corrected-artifact replacement namespace into a governed package replacement activation authority, or whether a separate implementation-entry freeze is required. It may inspect `backend/app/services/layer3_replacement_package_namespace.py`, `backend/app/services/layer3_replacement_package_artifact_manifest.py`, `backend/app/api/layer3.py`, `L3ReplacementOutputPackage`, `L3CorrectedPackageArtifactSet`, `L3ReplacementPackageSetAuthority`, `L3PackageSupersessionCommit`, `L3ReplacementPackageArtifactManifest`, and any existing package activation authority. It must not implement activation rows, package payload rewrite, source package row mutation, handoff/export reruns, delivery reruns, connector/destination behavior, source expansion, RAG/vector, auth/security, rendered UI, or frontend-durable behavior without a later explicit freeze.
