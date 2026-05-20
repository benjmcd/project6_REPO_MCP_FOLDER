# 888 - Source Directory Activation Proof Current-Main Sync

## Status

Status: current-main proof/control sync for `prove_source_directory_ingestion_scan_status_mockup_screen_server_authoritative_activation_without_runtime_widening`.

Sync doc: `888_SOURCE_DIRECTORY_ACTIVATION_PROOF_CURRENT_MAIN_SYNC.md`.

Proof doc: `887_SOURCE_DIRECTORY_ACTIVATION_PROOF.md`.

Proof PR: `#1501`.

Proof branch: `codex/l3-source-activation`.

Proof branch commit: `e351f88f79f5e69f79a2991c8b971844de8b641e`.

Proof merge commit: `39b5618b77591feeb4c7a1f405c01cbedadac166`.

Synced result: `current_main_synced_source_directory_ingestion_scan_status_mockup_screen_activation_proof`.

Runtime behavior introduced by this sync: `false`.

Rendered behavior introduced by this sync: `false`.

Backend behavior introduced by this sync: `false`.

Route/API/DTO/model/migration/service behavior introduced by this sync: `false`.

Single mockup screen server-authoritative activation current-main synced by this sync: `true`.

Full mockup program activation introduced by this sync: `false`.

## Current-Main Authority

Current `main` now includes the bounded source-directory scan/status server-authoritative activation proof from PR `#1501`:

- rendered surface: `/review/layer3` `#source-directory-ingestion-rendered-controls`;
- scan route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- status route: `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- request DTO: `Layer3SourceDirectoryIngestionScanRequest`;
- service authority: `backend/app/services/layer3_source_directory_ingestion.py`;
- durable batch state: `L3SourceDirectoryIngestionBatch`;
- durable file state: `L3SourceDirectoryIngestionFile`;
- rendered JS owner: `sourceDirectoryIngestionRenderedControls()`;
- successful scan/status authority proof remains covered;
- fail-closed HTTP 409 `source_directory_ingestion_dir_unset` proof remains covered;
- fail-closed HTTP 404 `source_directory_ingestion_batch_not_found` proof remains covered.

This sync admits the source-directory scan/status panel as the first current-main bounded single-screen server-authoritative mockup activation proof. It does not admit any other mockup control and does not admit full mockup program activation.

## GitHub Proof

PR `#1501` merged at `2026-05-20T03:15:48Z` with merge commit `39b5618b77591feeb4c7a1f405c01cbedadac166`.

Checks:

- `backend-layer3-api`: `SUCCESS`, `3m12s`;
- `test`: `SUCCESS`, `3m41s`.

Review gate:

- reviewThreads totalCount: `0`;
- PR comments: `0`;
- latest reviews: `0`;
- PR state: `MERGED`.

Post-merge local validation passed on current main at `39b5618b77591feeb4c7a1f405c01cbedadac166`:

- `node -e "JSON.parse(require('fs').readFileSync('./next_milestone_plans/layer3_progress_manifest.json','utf8')); console.log('progress manifest ok')"`;
- `node -e "JSON.parse(require('fs').readFileSync('./next_milestone_plans/layer3_workbench_proof_manifest.json','utf8')); console.log('proof manifest ok')"`;
- `node --check .\backend\app\review_ui\static\layer3.js`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `npx playwright test ./e2e/layer3-workbench.spec.js --grep "source-directory activation" --project=chromium`;
- `npx playwright test ./e2e/layer3-workbench.spec.js --grep "source-directory activation" --project=chromium --headed`.

## Boundaries Preserved

Do not render this sync as new runtime behavior, new rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior change, production UI behavior change, caller path/directory/file-byte/URL/glob/recursive-flag support, source upload or adapter expansion, package mutation/construction, connector/destination dispatch, provider URL behavior, RAG/vector widening, hidden LLM planning, optional-tool runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, any other mockup control activation, or full mockup program activation.

## Next Posture

The next exact posture is `rerun_mockup_to_live_mapping_after_source_directory_activation_proof_sync`.

That next pass must inventory the remaining mockup controls against current live routes, state, durable authority, fail-closed behavior, browser/security proof, and frontend-durable-authority exclusions before selecting another bounded activation target.
