# 887 - Source Directory Activation Proof

## Status

Status: branch-local server-authoritative activation proof for `prove_source_directory_ingestion_scan_status_mockup_screen_server_authoritative_activation_without_runtime_widening`.

Proof doc: `887_SOURCE_DIRECTORY_ACTIVATION_PROOF.md`.

Predecessor freeze doc: `886_SOURCE_DIRECTORY_ACTIVATION_FREEZE.md`.

Current-main checkpoint before this proof: `d1db95e0b0db9b06ddb1eeda4e2f6a10616c8b95`.

Implemented activation mode: `single_mockup_screen_server_authoritative_activation_proof`.

Implemented target: `source_directory_ingestion_scan_status_mockup_screen_activation`.

Implemented proof action: `prove_source_directory_ingestion_scan_status_mockup_screen_server_authoritative_activation_without_runtime_widening`.

Live activation surface proved: `/review/layer3` `#source-directory-ingestion-rendered-controls`.

Rendered surface decision: `reuse_existing_source_directory_ingestion_rendered_controls`.

Runtime behavior introduced by this proof: `false`.

Rendered behavior introduced by this proof: `false`.

Backend behavior introduced by this proof: `false`.

Route/API/DTO/model/migration/service behavior introduced by this proof: `false`.

Executable browser proof introduced by this proof: `true`.

Single mockup screen server-authoritative activation proved by this proof: `true`.

Full mockup program activation selected: `false`.

## Proven Authority

The proof keeps the canonical authority from doc `886`:

- scan route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- status route: `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- request DTO: `Layer3SourceDirectoryIngestionScanRequest`;
- service authority: `backend/app/services/layer3_source_directory_ingestion.py`;
- runtime policy: `recursive_server_configured_directory_text_table_policy_v1`;
- configuration authority: `LAYER3_SOURCE_INGESTION_DIR`;
- durable batch state: `L3SourceDirectoryIngestionBatch`;
- durable file state: `L3SourceDirectoryIngestionFile`;
- rendered route: `/review/layer3`;
- rendered surface: `#source-directory-ingestion-rendered-controls`;
- rendered JS owner: `sourceDirectoryIngestionRenderedControls()` in `backend/app/review_ui/static/layer3.js`.

The proof does not create a parallel mockup-only panel and does not move durable authority into browser state.

## Implemented Proof

The existing E2E proof `Layer 3 workbench renders source-directory scan and status authority fields` continues to prove the successful scan/status path:

- scan request contains only `client_request_id`, `operator_decision`, optional `source_family`, and optional `ingestion_mode`;
- scan response renders `layer3.source_directory_ingestion_batch.v1`;
- status response renders `layer3.source_directory_ingestion_status.v1`;
- idempotent replay renders as server replay accepted;
- raw Windows and Unix user paths do not render;
- package/source-mixed/connector/provider/execution side-effect requests are absent;
- no horizontal overflow, no console errors, and no page errors occur for the positive path.

This proof adds `Layer 3 source-directory activation proof renders blocked scan and missing batch states` in `e2e/layer3-workbench.spec.js`.

The added proof exercises:

- HTTP 409 scan block with `source_directory_ingestion_dir_unset`;
- HTTP 404 status block with `source_directory_ingestion_batch_not_found`;
- exact scan payload-key restriction;
- negative proof for `path`, `paths`, `directory`, `local_path`, `url`, `urls`, `glob`, `recursive`, `file`, `files`, `file_bytes`, `rag_vector_index`, and `web_connector`;
- the existing status button using only the server batch-id receipt field;
- no raw Windows path, Unix user path, `file_bytes`, or provider URL text in the rendered panel;
- exactly one scan request and exactly one status request;
- no package/source-mixed/connector/provider/execution side-effect requests;
- no horizontal overflow;
- no page errors;
- exact expected browser resource notices for the intentional HTTP 409 and HTTP 404 blocked-route proof.

The expected browser resource notices are scoped to the two intentional blocked-route responses and are not treated as application console defects. Unexpected console errors remain blocked by the proof.

## Validation

Branch-local validation passed:

- `npx playwright test ./e2e/layer3-workbench.spec.js --grep "source-directory activation" --project=chromium` PASS;
- `npx playwright test ./e2e/layer3-workbench.spec.js --grep "source-directory activation" --project=chromium --headed` PASS;
- `npx playwright test ./e2e/layer3-workbench.spec.js --grep "source-directory" --project=chromium` PASS.

The recurring `RequestsDependencyWarning` and `NO_COLOR` / `FORCE_COLOR` Node warnings appeared during browser runs but did not fail the proof and were not caused by this activation proof.

## Non-Admission Boundary

This proof admits no runtime behavior change, no rendered behavior change, no backend behavior change, no route/API/DTO/model/migration/service behavior change, no production UI control change, no caller path/file/URL/glob/recursive flag support, no source upload or adapter expansion, no package mutation/construction, no connector/destination dispatch, no provider URL behavior, no cloud object-store write, no RAG/vector widening, no hidden LLM planning, no optional-tool runtime, no auth/security behavior change, no browser-storage authority, and no frontend-only durable authority.

This proof proves only the first bounded single-screen server-authoritative activation target. It does not select or complete `full_mockup_program_activation`.

## Next Posture

The next exact posture is `current_main_sync_source_directory_activation_proof`.

After current-main sync, rerun the mockup-to-live activation mapping and choose the next bounded target whose route, state, durable owner, fail-closed behavior, browser/security proof, and no-frontend-durable-authority boundary can be frozen.
