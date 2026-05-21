# Layer 3 Source-Directory Package And Handoff Export Current-Main Sync

Doc: `932-post1550-sync.md`.

Status: current-main sync for `source_directory_package_lifecycle_handoff_export_rendered_path_after_pr1550`.

Predecessor current-main sync doc: `931-lifecycle-sync.md`.

Base authority: `project6-origin/main` at `d6e44a74e99bb4d449af410929bd14343a59c5a6`.

Synced backend contract PR: `#1548`.

Synced backend contract merge commit: `c5ae8229`.

Synced rendered package lifecycle control PR: `#1549`.

Synced rendered package lifecycle control merge commit: `e8fcc09a`.

Synced source-directory handoff export UI PR: `#1550`.

Synced source-directory handoff export UI merge commit: `d6e44a74e99bb4d449af410929bd14343a59c5a6`.

Synced branch set: `codex/l3-package-lifecycle-contract`, `codex/l3-package-lifecycle-ui`, and `codex/l3-handoff-export-ui`.

GitHub gate for PR `#1550`: merge state `CLEAN`, checks `SUCCESS`, comments `0`, reviews `0`, reviewThreads totalCount `0`, unresolved reviewThreads totalCount `0`.

Post-merge current-main validation:

- `python ./tools/l3-progress-check.py`: `PASS`.
- `node --check ./backend/app/review_ui/static/layer3.js`: `PASS`.
- `python -m pytest ./backend/tests/test_layer3_page.py -q`: `14 passed, 3 warnings`.
- `python -m pytest ./backend/tests/test_layer3_source_directory_qualitative_analysis.py -q`: `13 passed, 3 warnings`.
- `npm run test:e2e:chromium -- ./e2e/layer3-workbench.spec.js -g "Layer 3 workbench drives source-directory qualitative handoff export rendered controls"`: `1 passed`.
- `npm run test:e2e:headed -- ./e2e/layer3-workbench.spec.js -g "Layer 3 workbench drives source-directory qualitative handoff export rendered controls"`: `1 passed`.

Synced backend/API authority:

- `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/replacement-set/record-from-supersession-preview`.
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/package/supersession/commit`.
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/prepare`.
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/prepare`.
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver/status`.
- `POST /api/v1/layer3/source/ingestion/server-configured-directory/qualitative-hybrid-analysis/handoff/export/download/deliver`.

Synced rendered authority:

- `/review/layer3 #replacement-package-set-authority-panel` submits source-directory replacement authority through the server-owned route.
- `/review/layer3 #package-supersession-commit-panel` submits source-directory package supersession through the server-owned route.
- `/review/layer3 #handoff-export-prepare-panel` submits source-directory qualitative handoff/export prepare through the source-directory route.
- `/review/layer3 #external-export-download-prepare-panel` submits source-directory qualitative external export/download prepare through the source-directory route.
- `/review/layer3 #external-export-download-delivery-panel` first verifies source-directory delivery status and then submits same-origin source-directory delivery.

Synced schema and state authority:

- `layer3.source_directory_qualitative_analysis_handoff_export_prepare.v1`.
- `layer3.source_directory_qualitative_analysis_external_export_download_prepare.v1`.
- `layer3.source_directory_qualitative_analysis_external_export_download_delivery_status.v1`.
- `layer3.source_directory_qualitative_analysis_external_export_download_delivery.v1`.
- `State.sourceDirectoryPackageSupersessionPreview`.
- `State.replacementPackageSetAuthority`.
- `sourceDirectoryPackageSupersessionPreviewPayload`.
- `State.handoffExportPrepare`.

Synced rendered checker anchors:

- `SOURCE_DIRECTORY_PACKAGE_SUPERSESSION_COMMIT_PATH`.
- `SOURCE_DIRECTORY_QUALITATIVE_HANDOFF_EXPORT_PREPARE_PATH`.
- `SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_PREPARE_PATH`.
- `SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_STATUS_PATH`.
- `SOURCE_DIRECTORY_QUALITATIVE_EXTERNAL_EXPORT_DOWNLOAD_DELIVERY_PATH`.
- `rendered_source_directory_qualitative_handoff_export_prepare_control`.
- `rendered_source_directory_qualitative_external_export_download_prepare_control`.
- `rendered_source_directory_qualitative_external_export_download_delivery_control`.

Runtime behavior introduced by this sync doc: `false`.

Rendered behavior introduced by this sync doc: `false`.

Backend behavior introduced by this sync doc: `false`.

Route/API/DTO/model/migration/service behavior introduced by this sync doc: `false`.

Executable test behavior introduced by this sync doc: `false`.

Production UI behavior introduced by this sync doc: `false`.

Frontend-only durable authority enabled by this sync doc: `false`.

Full mockup program activation selected now: `false`.

Current bounded live-path status: source-directory qualitative package lifecycle and handoff/export rendered controls are now current-main synced through same-origin external export/download delivery.

Remaining proof gap: the current rendered handoff/export E2E proof starts from injected source-directory package authority, not a single source-directory operator run from scan/status through material preview, Gate B admission, retrieval/context, qualitative analysis, package lifecycle, handoff/export, delivery/use, internal webhook status, and Analysis Environment/mockup projection.

Next exact posture: `prove_source_directory_scan_to_handoff_export_bounded_operator_path_and_record_trial_usable_checkpoint`.

Blocked until that proof or a narrower freeze: full mockup activation, frontend-only durable authority, package payload mutation/rewrite, source `L3OutputPackage` row mutation, connector/destination dispatch beyond already admitted internal record/status behavior, provider/public URL expansion beyond admitted redacted delivery/use surfaces, broad source expansion, broad RAG/vector behavior, prompt/model/provider qualitative expansion, and auth/security expansion.
