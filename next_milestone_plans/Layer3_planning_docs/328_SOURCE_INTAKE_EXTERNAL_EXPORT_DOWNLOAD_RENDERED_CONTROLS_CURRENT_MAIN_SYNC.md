# 328 - Source Intake External Export Download Rendered Controls Current-main Sync

Status: current-main proof/control sync for `source_intake_external_export_download_rendered_controls_boundary` after PR `#920`.

Merged PR: `#920`
Implementation branch: `codex/l3-source-intake-rendered-delivery-controls`
Head commit before merge: `3a27a61d243621a264f78f7fe9d32d0507db3b2a`
Merge commit/current-main authority: `11185c51b1af4c68a8df9f28a1fd0bb66cf5cf32`
Predecessor main commit: `f17d9e2e9a6e1dacfbb86552dd94b6b9af447634`
Implemented boundary doc: `327_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_RENDERED_CONTROLS_BOUNDARY.md`
Freeze predecessor: `326_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_RENDERED_CONTROLS_BOUNDARY_FREEZE.md`
Owner UI: `backend/app/review_ui/static/layer3.js`
Rendered shell: `backend/app/review_ui/static/layer3.html`

## Current-main authority

PR `#920` is merged on `project6-origin/main` at `11185c51b1af4c68a8df9f28a1fd0bb66cf5cf32`. This sync records the branch-local rendered-controls implementation from doc `327` as current-main truth without widening the admitted behavior.

The merged behavior remains limited to rendered source-intake same-origin delivery controls over existing server prepare/readiness and same-origin delivery authority:

- source-intake rendered delivery is recognized through `layer3.source_intake_external_export_download_prepare.v1`
- `source_intake_external_export_download_delivery_ui_ready` is derived only from complete server prepare/readiness fields
- same-origin delivery continues to submit `deliver_external_export_download` with `same_origin_artifact_stream`
- signed-reference controls remain blocked for source-intake by `!isSourceIntakeExternalExportDownloadState(external)`
- provider-private signed URL controls remain blocked for source-intake by `!isSourceIntakeExternalExportDownloadState(external)`
- unknown non-associated/non-qualitative external-export families remain blocked instead of implicitly admitted
- the pre-existing APS evidence-bundle delivery path remains admitted only when the prepare record is a non-associated-cohort `aps_evidence_bundle_download_reference` over `aps.evidence_bundle.v2`

## Merge gate evidence

Before merge, PR `#920` was no longer draft, had `mergeStateStatus: CLEAN`, and had no top-level comments, no reviews, and no `reviewThreads`.

GitHub checks on the final head commit passed:

- `backend-layer3-api` -> success on run `25806253291`, job `75809717144`
- `test` -> success on run `25806253291`, job `75809717233`

Local validation before final push covered the failed CI surfaces and the progress/control guard:

- `npx playwright test e2e/layer3-workbench.spec.js --project=chromium` -> `31 passed`
- `npx playwright test e2e/layer3-handoff.spec.js --project=chromium` -> `3 passed`
- `python -m pytest .\backend\tests\test_layer3_page.py` -> `3 passed, 3 warnings`
- `python .\tools\l3-progress-check.py` -> `Layer 3 progress state check: PASS`
- `git diff --check` -> clean except expected CRLF normalization warnings

Post-merge validation on `project6-origin/main` at `11185c51b1af4c68a8df9f28a1fd0bb66cf5cf32`:

- `python .\tools\l3-progress-check.py` -> `Layer 3 progress state check: PASS`
- worktree status after detach to merged main contained only `?? .codesight/`

## Scope still blocked

This sync admits no backend runtime behavior beyond the already-merged PR `#920` rendered projection, no route/model/migration/auth/security behavior, no provider public/private URL behavior, no source-intake signed-reference generation/use, no connector/destination dispatch, no package mutation/reconstruction, no source expansion, no RAG/vector behavior, no broad qualitative behavior, and no full mockup activation.

## Next required decision

The next selected boundary is `source_intake_external_export_download_signed_reference_boundary_freeze`, documented separately in `329_SOURCE_INTAKE_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_BOUNDARY_FREEZE.md`.
