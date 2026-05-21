# 925 - Source-Directory Replacement Package-Set Authority Rendered Control Current-Main Sync

## Status

Status: current-main sync for `source_directory_replacement_package_set_authority_rendered_control_after_review_fix`.

Doc: `925_SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_CONTROL_CURRENT_MAIN_SYNC.md`.

Predecessor implementation doc: `924_SOURCE_DIRECTORY_REPLACEMENT_PACKAGE_SET_AUTHORITY_RENDERED_CONTROL.md`.

Implementation PR: `#1539`.

Implementation branch: `codex/l3-replacement-set-control`.

Implementation commit: `655a76563db041d523e29a4f047d9c3666f460e4`.

Implementation merge commit: `7116ed4eca19109dc972580c53a2900d6feea347`.

Review-fix PR: `#1540`.

Review-fix branch: `codex/l3-replacement-set-current-main-sync`.

Review-fix commit: `c0ae6c43176b43cce0238d5281723f2ec2cc1a5f`.

Review-fix merge commit: `0d873c11c325600dff4b08dbe6a2f14ad95a9c74`.

Sync branch: `codex/l3-replacement-set-sync-docs`.

Base authority: `project6-origin/main` at `0d873c11c325600dff4b08dbe6a2f14ad95a9c74`.

Synced target: `source_directory_replacement_package_set_authority_rendered_control`.

Synced rendered node: `/review/layer3 #replacement-package-set-authority-panel`.

Synced source authority: `State.sourceDirectoryPackageSupersessionPreview`.

Synced fallback authority: `State.packageSupersessionPreview`.

Synced materialization state: `State.replacementPackageArtifactMaterialization`.

Synced replacement authority state: `State.replacementPackageSetAuthority`.

Synced materialization route: `POST /api/v1/layer3/package/replacement-artifact/materialize`.

Synced replacement authority route: `POST /api/v1/layer3/package/replacement-set/record`.

Runtime behavior introduced by this sync: `false`.

Rendered behavior introduced by this sync: `false`.

Backend behavior introduced by this sync: `false`.

Route/API/DTO/model/migration/service behavior introduced by this sync: `false`.

Executable test behavior introduced by this sync: `false`.

Production UI behavior introduced by this sync: `false`.

Full mockup program activation selected now: `false`.

Implementation-entry allowed for full mockup activation by this sync alone: `false`.

## Current-Main Authority

Current main now includes the source-directory replacement package-set authority rendered control from PR `#1539` and the stale-response invalidation fix from PR `#1540`.

The synced behavior is:

- `/review/layer3 #replacement-package-set-authority-panel` can use `State.sourceDirectoryPackageSupersessionPreview` as the selected source authority;
- the same panel can still fall back to `State.packageSupersessionPreview` for the pre-existing generic path;
- `POST /api/v1/layer3/package/replacement-artifact/materialize` remains the only materialization route used by this rendered control;
- `POST /api/v1/layer3/package/replacement-set/record` remains the only replacement authority route used by this rendered control;
- in-flight source-directory package supersession preview responses are invalidated when the source authority input changes or source preview state is cleared; and
- stale source-directory preview responses cannot repopulate source preview state or enable replacement package-set authority after invalidation.

## Merge Gate

PR `#1539` merged at `7116ed4eca19109dc972580c53a2900d6feea347`.

PR `#1539` checks:

- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`.

PR `#1539` review caveat:

- comments: `0`;
- reviews: `1`, state `COMMENTED`;
- latestReviews: `1`, state `COMMENTED`;
- reviewThreads totalCount: `1`;
- unresolved reviewThreads totalCount: `1`;
- finding URL: `https://github.com/benjmcd/project6_REPO_MCP_FOLDER/pull/1539#discussion_r3278431627`.

PR `#1540` merged at `0d873c11c325600dff4b08dbe6a2f14ad95a9c74`.

PR `#1540` checks:

- `backend-layer3-api`: `SUCCESS`;
- `test`: `SUCCESS`.

PR `#1540` review state before merge:

- comments: `0`;
- reviews: `0`;
- latestReviews: `0`;
- reviewThreads totalCount: `0`;
- unresolved reviewThreads totalCount: `0`;
- merge state before merge: `CLEAN`.

## Validation

Branch-local implementation and review-fix validation is recorded in Doc `924`.

Current-main sync validation:

- `python .\tools\l3-progress-check.py` after PR `#1540` merge - `PASS`.

This docs-sync branch validation must additionally pass:

- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

## Non-Admission Boundary

This sync introduces no new runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, executable test behavior, production UI behavior, package supersession commit, package replacement activation, source `L3OutputPackage` row mutation, package payload write, package payload rewrite, connector dispatch, destination write, provider-public delivery, provider-private signed URL behavior, public proxy runtime, source expansion, RAG/vector/model/provider runtime, optional-tool runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, mockup-frame write controls beyond the selected rendered control, or full mockup program activation.

The current-main behavior remains one bounded rendered replacement package-set authority control over existing server routes, now guarded against stale source-directory preview response authority.

## Grill-Me Self-Check

| Question | Repo-derived answer |
| --- | --- |
| Is PR `#1539` current-main truth? | Yes. It merged at `7116ed4eca19109dc972580c53a2900d6feea347`. |
| Was PR `#1539` review-clean? | No. It had one COMMENTED review and one unresolved thread after merge. |
| Is the PR `#1539` finding still open as current-main behavior? | No. PR `#1540` merged the stale-response invalidation fix at `0d873c11c325600dff4b08dbe6a2f14ad95a9c74`. |
| Does this sync itself add behavior beyond the merged PRs? | No. It is docs/progress/checker metadata only. |
| Can full mockup activation be admitted now? | No. Package supersession commit, connector/provider/source/RAG/auth, and final readiness-audit blockers remain. |
| What comes next? | Select the next exact blocker-retirement lane from current-main evidence; the nearest package-lifecycle candidate is source-directory package supersession commit rendered authority, but it needs its own freeze before implementation. |

## Next Posture

Next exact posture: `select_next_blocker_retirement_lane_after_source_directory_replacement_package_set_authority_rendered_control_current_main_sync`.
