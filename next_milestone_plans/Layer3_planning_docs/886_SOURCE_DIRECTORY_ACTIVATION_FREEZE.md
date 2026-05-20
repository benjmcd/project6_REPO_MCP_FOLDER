# 886 - Source Directory Activation Freeze

## Status

Status: no-runtime/no-rendered implementation-entry freeze for `prove_source_directory_ingestion_scan_status_mockup_screen_server_authoritative_activation_without_runtime_widening`.

Freeze doc: `886_SOURCE_DIRECTORY_ACTIVATION_FREEZE.md`.

Predecessor selection doc: `885_SOURCE_DIRECTORY_ACTIVATION_SELECTION.md`.

Current-main checkpoint before this freeze: `16b9fa74479bbadf641ac8f78c3af409e48fd2b9`.

Selected activation mode: `single_mockup_screen_server_authoritative_activation_freeze`.

Selected target: `source_directory_ingestion_scan_status_mockup_screen_activation`.

Selected activation action: `prove_source_directory_ingestion_scan_status_mockup_screen_server_authoritative_activation_without_runtime_widening`.

Selected live activation surface: `/review/layer3` `#source-directory-ingestion-rendered-controls`.

Rendered surface decision: `reuse_existing_source_directory_ingestion_rendered_controls`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Single mockup screen server-authoritative activation introduced by this freeze: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed next: `false` until this freeze is current-main synced.

## Canonical Source Of Truth

The canonical source of truth for the future source-directory activation proof is the existing server-owned scan/status contract:

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
- rendered JS owner: `sourceDirectoryIngestionRenderedControls()` in `backend/app/review_ui/static/layer3.js`;
- static/API proof: `backend/tests/test_layer3_source_directory_ingestion.py` and `backend/tests/test_layer3_page.py`;
- browser proof seam: `e2e/layer3-workbench.spec.js` test `Layer 3 workbench renders source-directory scan and status authority fields`.

Mockup files, screenshots, browser-local state, local storage, copied output, operator-entered paths, and any frontend-only state are target-state aids only. They are not authority for activation.

## Activation Surface Decision

The future activation proof must reuse the existing `/review/layer3` source-directory scan/status control as the first server-authoritative mockup-screen activation surface.

A separate mockup-only panel is not admitted for this target because it would duplicate an already-server-authoritative control and create a second place where frontend state could appear authoritative. The existing rendered control is already tied to the admitted scan/status route family, durable batch/file authority, redacted response fields, idempotency/replay state, and headed/headless proof seam.

The future proof may classify the existing control as the live activation surface only after it proves the complete action contract below. This freeze does not itself activate the screen.

## Frozen Action Contract

The only admitted operator actions for the future activation proof are:

- submit a scan through `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- inspect an existing server batch through `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`.

The scan request may contain only:

- `client_request_id`;
- `operator_decision`;
- optional `source_family`;
- optional `ingestion_mode`.

The required operator decision is `scan_server_configured_operator_directory`.

The required source family is `server_configured_operator_directory_text_table_source_family`.

The required ingestion mode is `server_configured_operator_directory_text_table_ingestion`.

The status request may contain only the server-issued `source_ingestion_batch_id` path parameter. A batch id is a server receipt reference, not a source selector and not a local path authority.

The rendered control must not construct, submit, store, or infer caller paths, directories, file bytes, URLs, globs, caller-selected recursive flags, web connector targets, RAG/vector inputs, package mutation inputs, connector/destination dispatch inputs, provider URL inputs, browser-storage authority, or frontend-only durable authority.

## Frozen State Contract

The future activation proof must treat these server response fields as the activation state contract:

- `schema_id`;
- `request_id`;
- `status`;
- `source_ingestion_batch_id`;
- `runtime_policy_id`;
- `source_family`;
- `ingestion_mode`;
- `config_authority`;
- `source_root_ref`;
- `source_root_absolute_path_exposed`;
- `direct_child_only`;
- `recursive_traversal_admitted`;
- `max_recursion_depth`;
- `max_relative_path_segments`;
- `caller_selected_recursive_flag_allowed`;
- `allowed_extensions`;
- `eligible_file_count`;
- `total_size_bytes`;
- `directory_fingerprint_hash`;
- `authority_basis_hash`;
- `files[]` with `relative_name`, `extension`, `media_type`, `content_size_bytes`, `content_sha256`, `file_identity_hash`, and `absolute_path_exposed`;
- `negative_invariants`.

The rendered panel must prove both `layer3.source_directory_ingestion_batch.v1` and `layer3.source_directory_ingestion_status.v1` states where the browser proof fixture exercises both scan and status.

## Frozen Durable Authority Contract

The durable authority owner is the database state represented by `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`.

The future proof must preserve these durable-state invariants:

- `client_request_id`, `authority_basis_hash`, and `directory_fingerprint_hash` uniqueness remain server-side;
- repeated equivalent authority may return `already_recorded`;
- conflicting authority for the same client request fails with `source_directory_ingestion_idempotency_conflict`;
- file rows remain relative-name and hash authority only;
- raw absolute paths are not response authority and must remain redacted from browser output.

## Frozen Failure Contract

The future activation proof must include fail-closed behavior for:

- unset `LAYER3_SOURCE_INGESTION_DIR` returning `source_directory_ingestion_dir_unset` with HTTP 409;
- unavailable or non-admitted configured source root returning a server-owned block state;
- caller-controlled fields rejected by the request DTO before service execution;
- unsupported file or recursive-policy violations rejected by the service;
- missing `source_ingestion_batch_id` returning `source_directory_ingestion_batch_id_required`;
- missing batch returning `source_directory_ingestion_batch_not_found` with HTTP 404;
- blocked scan and blocked status states rendering as blocked, not as successful activation.

## Required Future Write Scope

The later activation proof should be limited to:

- `e2e/layer3-workbench.spec.js`;
- `backend/tests/test_layer3_page.py` only if the static DOM/JS contract needs tighter proof;
- progress/proof docs and manifests needed to record the activation proof;
- `tools/l3-progress-check.py` guard terms for the exact proof.

No production backend, route, DTO, model, migration, service, source traversal, package, connector, provider, RAG/vector, auth/security, or browser-storage behavior may change under this freeze.

No production rendered change is expected. A rendered change is admitted only if the proof audit shows a missing activation-state field in the existing control, and any such change must stay inside `backend/app/review_ui/static/layer3.html`, `backend/app/review_ui/static/layer3.js`, and `backend/app/review_ui/static/layer3.css` with no backend/API widening.

## Required Future Proof

The future activation proof must provide:

- static or browser proof that the scan payload contains exactly `client_request_id`, `operator_decision`, optional `source_family`, and optional `ingestion_mode`;
- negative proof that payloads do not contain `path`, `paths`, `directory`, `local_path`, `url`, `urls`, `glob`, `recursive`, `file`, `files`, `file_bytes`, `rag_vector_index`, or `web_connector`;
- browser proof that scan and status use only the admitted route family;
- browser proof that no raw Windows path, Unix user path, provider/object-store URL, raw local path, or browser file byte authority renders;
- browser proof that scan success, idempotent replay/status, 409 blocked scan, and 404 missing batch states render coherently;
- browser proof that package/source-mixed/connector/provider/execution side-effect routes are not requested;
- headed Chromium proof;
- headless Chromium proof;
- responsive no-horizontal-overflow proof;
- no console errors and no page errors;
- progress-check guard coverage for this exact freeze and the later activation proof.

## No-Go Surface

The future activation proof must not admit:

- caller-supplied paths;
- caller-supplied directories;
- browser file bytes;
- URL input;
- glob input;
- caller-selected recursive flags;
- source upload behavior;
- source adapter registry expansion;
- web connector retrieval;
- connector or destination dispatch;
- `ConnectorRun` or `ConnectorRunTarget` creation;
- package mutation or package construction;
- provider-private signed URL behavior;
- provider-public URL behavior;
- cloud object-store writes;
- RAG/vector widening;
- prompt/model/provider qualitative generation;
- hidden LLM planning;
- optional-tool runtime;
- auth/security behavior change;
- browser-storage authority;
- frontend-only durable state;
- full mockup program activation.

## Immediate Milestone

Milestone 1: current-main sync this freeze, then prove `source_directory_ingestion_scan_status_mockup_screen_activation` as the first single-screen server-authoritative activation without runtime widening.

Exit criteria for the later proof:

- the existing `/review/layer3` source-directory panel is proven as the live activation surface;
- scan and status route/state contracts are proven;
- durable batch/file authority is proven;
- fail-closed states are proven;
- forbidden payload/rendering leakage is proven absent;
- headed and headless Chromium proof pass;
- no backend/API/model/migration/service/source/package/connector/provider/RAG/auth/browser-storage behavior changes occur;
- `python .\tools\l3-progress-check.py` passes.

## Mid-Term Milestones

Milestone 2: current-main sync the source-directory activation proof.

Milestone 3: rerun the mockup-to-live activation mapping and select the next control or screen whose route/state/durable/test contract is complete enough to freeze.

Milestone 4: repeat bounded read-only projections or server-authoritative activations until each critical mockup operator journey is live, read-only, intentionally excluded, or blocked with a named unresolved boundary.

## Long-Term Milestones

Milestone 5: retire remaining source breadth, package mutation, connector/destination, provider URL, qualitative/hybrid/RAG, optional-tool, browser-state, and auth/security blockers in separately frozen lanes.

Milestone 6: run a full mockup activation readiness audit proving every critical mockup control is one of:

- live and server-authoritative;
- live and read-only projection only;
- intentionally excluded;
- still blocked with a named blocker.

Milestone 7: admit `full_mockup_program_activation` only after the readiness audit proves complete route/state/test/browser/security coverage and no frontend-only durable authority.

## Non-Admission Boundary

This freeze admits no runtime behavior, no rendered behavior, no backend behavior, no route/API/DTO/model/migration/service behavior change, no UI control change now, no executable test behavior change now, no single mockup screen server-authoritative activation, no full mockup program activation, no caller path/file/URL/glob/recursive flag support, no source expansion, no package mutation/construction, no connector/destination dispatch, no provider URL behavior, no RAG/vector widening, no hidden LLM planning, no optional-tool runtime, no auth/security behavior change, no browser-storage authority, and no frontend-only durable authority.

## Validation Basis

Required validation for this no-runtime freeze:

- `python .\tools\l3-progress-check.py`;
- JSON validation for `next_milestone_plans/layer3_progress_manifest.json`;
- JSON validation for `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `git diff --check`.

No runtime, API, or browser test is required for this freeze because it changes no runtime behavior, route, dependency, session-summary field, rendered UI, browser behavior, or executable test.

## Next Posture

The next exact posture is `current_main_sync_source_directory_activation_freeze_then_activation_proof`.

After that sync, the only admitted implementation/proof action is `prove_source_directory_ingestion_scan_status_mockup_screen_server_authoritative_activation_without_runtime_widening`.
