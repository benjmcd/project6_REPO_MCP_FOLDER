# 713 - Corrected Artifact Package Supersession Commit Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `corrected_artifact_package_supersession_commit_runtime`.

Doc: `713_CORRECTED_ARTIFACT_PACKAGE_SUPERSESSION_COMMIT_RUNTIME_CURRENT_MAIN_SYNC.md`.

Synced runtime proof doc: `712_CORRECTED_ARTIFACT_PACKAGE_SUPERSESSION_COMMIT_RUNTIME_PROOF.md`.

Runtime PR: `#1317`.

Runtime branch: `codex/l3-corrected-artifact-supersession-commit`.

Runtime branch commit: `410ee98d4342887858df30b9b237a31a425d5907`.

Runtime merge commit: `0c27602358854f778d157ece163549bd1724df1f`.

Current-main checkpoint after merge: `0c27602358854f778d157ece163549bd1724df1f`.

Sync branch: `codex/l3-corrected-artifact-supersession-sync`.

Selected runtime now synced: `server_computed_package_supersession_commit_from_corrected_artifact_replacement_authority`.

Live route now synced: `POST /api/v1/layer3/package/supersession/commit-from-corrected-artifact-set-authority`.

Owner service now synced: `backend/app/services/layer3_package_supersession_commit.py`.

API owner now synced: `backend/app/api/layer3.py`.

Durable target now synced: `L3PackageSupersessionCommit`.

Source authority now synced: `L3CorrectedPackageArtifactSet`.

Replacement authority now synced: `L3ReplacementPackageSetAuthority`.

Request mode now synced: `package_supersession_commit_from_corrected_artifact_set_authority`.

Operator decision now synced: `commit_package_supersession`.

Runtime behavior already merged by the runtime PR: `true`.

Review-fix behavior change in this sync: `true`.

## Merge Gate

Before merge, PR `#1317` had:

- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- comments: `[]`;
- reviews: `[]`;
- latestReviews: `[]`;
- reviewThreads totalCount: `0`;
- unresolved current reviewThreads: `0`;
- mergeability: `MERGEABLE`.

Post-merge local validation on current main at `0c27602358854f778d157ece163549bd1724df1f` passed:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
git diff --check
```

## Review Fix Included

After PR `#1317` merged, automated review threads identified two narrow runtime-contract issues in the same selected surface:

- the request model needed to declare every schema-advertised known forbidden field so those fields reach the Layer 3 workbench error envelope instead of generic FastAPI `422`; and
- the corrected-artifact response needed to preserve the standard `layer3.authority_rail.v1` fields while adding corrected-artifact custom flags.

This sync branch fixes only those review findings. It does not add a new route, table, migration, package mutation action, manifest bridge, namespace bridge, activation bridge, handoff/export rerun, delivery rerun, connector/destination behavior, source expansion, RAG/vector behavior, auth/security behavior, rendered UI behavior, or frontend-durable authority.

## Sync Branch Validation

Validation on `codex/l3-corrected-artifact-supersession-sync` passed:

```powershell
python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json > $null
python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json > $null
python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py .\backend\app\services\layer3_package_supersession_commit.py .\backend\app\api\layer3.py
python .\tools\l3-progress-check.py
python .\tools\l3-target-selection-validate.py --expect frozen
python -m pytest .\backend\tests\test_layer3_package_supersession_commit.py -q
python -m pytest .\backend\tests\test_layer3_api.py -q -k "supersession_commit_from_corrected_artifact_set or openapi_contracts or package_supersession_commit_contract"
git diff --check
```

Observed targeted pytest results:

- `test_layer3_package_supersession_commit.py`: `4 passed`; and
- targeted `test_layer3_api.py`: `13 passed, 165 deselected`.

## Current-Main Result

Current main now contains the corrected-artifact package supersession commit bridge.

The synced runtime proves current main can record and replay `L3PackageSupersessionCommit` from corrected-artifact authority without browser/caller supplied source refs, replacement refs, downstream hash, preview hash, commit basis hash, paths, URLs, credentials, connector ids, source expansion fields, RAG/vector fields, auth/security context, browser state, or frontend-durable state.

The route derives source and replacement refs/hashes server-side from `L3CorrectedPackageArtifactSet` and corrected-artifact `L3ReplacementPackageSetAuthority`, then redacts response refs and returned commit snapshot refs.

## Still Blocked

This sync admits no new capability beyond the narrow review fixes above. Replacement artifact manifest recording from corrected-artifact supersession authority, replacement namespace row creation, package replacement activation, package payload rewrite, source `L3OutputPackage` mutation, downstream invalidation, re-running handoff/export or delivery, provider-public delivery/use, connector/destination dispatch, `ConnectorRun` creation, `ConnectorRunTarget` creation, credentials, external network egress, source expansion, RAG/vector behavior, broad qualitative/hybrid execution, auth/security behavior, full mockup activation, frontend-durable authority, rendered UI authority, caller-supplied arbitrary paths or URLs, browser-supplied refs/hashes/bytes, raw local path exposure, and hidden LLM planning remain blocked.

## Next Posture

The next exact current-main posture is `evaluate_corrected_artifact_replacement_artifact_manifest_authority_after_supersession_commit_runtime_sync`.

That evaluation must stay inside the selected package mutation/reconstruction surface and determine whether current main can safely bridge the corrected-artifact supersession commit authority into replacement artifact manifest authority without caller-supplied raw refs/paths, or whether a separate implementation-entry freeze is required. It may inspect `backend/app/services/layer3_replacement_package_artifact_manifest.py`, `backend/app/api/layer3.py`, `L3CorrectedPackageArtifactSet`, `L3ReplacementPackageSetAuthority`, `L3PackageSupersessionCommit`, and `L3ReplacementPackageArtifactManifest`, but it must not implement manifest, namespace, activation, handoff/export, delivery, connector/destination, source expansion, RAG/vector, auth/security, rendered UI, or frontend-durable behavior without a later explicit freeze.
