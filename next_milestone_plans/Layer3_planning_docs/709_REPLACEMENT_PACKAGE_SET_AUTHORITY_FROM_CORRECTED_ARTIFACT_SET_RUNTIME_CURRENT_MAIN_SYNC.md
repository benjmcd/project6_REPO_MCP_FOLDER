# 709 - Replacement Package Set Authority From Corrected Artifact Set Runtime Current-Main Sync

## Status

Status: current-main proof/control sync for `replacement_package_set_authority_from_corrected_artifact_set_runtime`.

Doc: `709_REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_RUNTIME_CURRENT_MAIN_SYNC.md`.

Runtime proof doc: `708_REPLACEMENT_PACKAGE_SET_AUTHORITY_FROM_CORRECTED_ARTIFACT_SET_RUNTIME_PROOF.md`.

Runtime PR: `#1313`.

Runtime branch: `codex/l3-corrected-artifact-replacement-authority-runtime`.

Runtime branch commit: `2df2913a81245dca2c23e39555c2c08060e0af5d`.

Runtime merge commit: `73e102d87788bd9b376ea4d2effab40e853f48b1`.

Sync branch: `codex/l3-corrected-artifact-replacement-authority-runtime-sync`.

Current-main checkpoint after merge: `73e102d87788bd9b376ea4d2effab40e853f48b1`.

Runtime behavior change in synced PR: true.

Runtime status: `implemented_and_current_main_synced`.

## Merge Gate

PR `#1313` merged after:

- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`;
- PR comments before merge: empty;
- PR reviews before merge: empty;
- PR latestReviews before merge: empty;
- PR reviewThreads totalCount before merge: `0`;
- unresolved current reviewThreads before merge: `0`;
- mergeability before merge: `MERGEABLE`;
- merge state before merge: `CLEAN`; and
- merge commit: `73e102d87788bd9b376ea4d2effab40e853f48b1`.

Post-merge validation on `project6-origin/main` at `73e102d87788bd9b376ea4d2effab40e853f48b1`:

- `python -m py_compile .\tools\l3-progress-check.py .\tools\l3-target-selection-validate.py` passed;
- `python .\tools\l3-progress-check.py` passed; and
- `python .\tools\l3-target-selection-validate.py --expect frozen` passed.

## Synced Current-Main Authority

Current main now contains the corrected-artifact replacement package-set authority bridge:

- route: `POST /api/v1/layer3/package/replacement-set/record-from-corrected-artifact-set`;
- owner service: `backend/app/services/layer3_replacement_package_set_authority.py`;
- API owner: `backend/app/api/layer3.py`;
- durable target: `L3ReplacementPackageSetAuthority` / `l3_replacement_package_set_authority`;
- source authority: `L3CorrectedPackageArtifactSet` / `l3_corrected_package_artifact_set`;
- request mode: `replacement_package_set_authority_from_corrected_artifact_set`;
- operator decision: `record_replacement_package_set_authority`; and
- response schema id: `layer3.replacement_package_set_authority.v1`.

The current-main runtime validates corrected artifact set identity and basis, derives replacement package-set identity and payload vectors server-side from `L3CorrectedPackageArtifactSet`, records or replays `L3ReplacementPackageSetAuthority`, and returns redacted source/replacement payload refs with no raw local paths exposed.

Current-main proof covers same-key/same-basis replay, same-basis/new-key replay, stale corrected artifact basis hash failure, missing corrected artifact set failure, wrong session/source-package basis failure, forbidden adjacent fields failing closed, OpenAPI exposure, API error-envelope behavior, and no adjacent package mutation side effects.

## Boundary Still Blocked

This sync admits no new behavior beyond the already-merged runtime.

Direct source `L3OutputPackage` row mutation, package payload rewrite, package activation, replacement namespace row creation, replacement artifact manifest recording, package supersession commit, downstream invalidation, handoff/export rerun, provider-public delivery/use, connector/destination dispatch, `ConnectorRun` creation, `ConnectorRunTarget` creation, credentials, external network egress, source expansion, RAG/vector behavior, auth/security behavior, frontend-durable authority, browser/operator path editing, caller-supplied arbitrary paths or URLs, raw local path exposure, hidden LLM planning, and rendered UI authority remain blocked unless a later current-main freeze explicitly admits the exact slice.

## Next Posture

The next exact posture is `evaluate_corrected_artifact_package_rebuild_downstream_existing_authority_after_replacement_authority_runtime_sync`.

That next pass should inspect the already-landed package supersession commit, replacement artifact manifest, replacement namespace, rendered controls, and activation lanes against the corrected-artifact replacement authority now on current main. If existing current-main authority already satisfies a downstream step, record that satisfied state. If a bridge is missing, write only the next exact implementation-entry freeze for the missing package rebuild posture before runtime work.
