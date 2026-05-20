# 877 - Source Directory Extension Freeze

## Status

Status: no-runtime/no-rendered implementation-entry freeze for `extend_source_directory_ingestion_scan_status_rendered_control`.

Freeze doc: `877_SOURCE_DIRECTORY_EXTENSION_FREEZE.md`.

Predecessor selection doc: `876_MOCKUP_MAPPING_SELECTION.md`.

Current-main checkpoint before this freeze: `4a715e4c57206a0b3c30adbde9a27f9c94863bb9`.

Selected activation mode: `single_existing_rendered_control_extension`.

Selected target: `source_directory_ingestion_scan_status_rendered_control`.

Selected implementation action: `extend_source_directory_ingestion_scan_status_rendered_control`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Implementation-entry allowed next: `false` until this freeze is current-main synced.

## Source Of Truth

The canonical source of truth for the future rendered-control extension is existing server authority only:

- service: `backend/app/services/layer3_source_directory_ingestion.py`;
- route owner: `backend/app/api/layer3.py`;
- scan route: `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`;
- status route: `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}`;
- durable state: `L3SourceDirectoryIngestionBatch` and `L3SourceDirectoryIngestionFile`;
- rendered route: `/review/layer3`;
- rendered DOM: `#source-directory-ingestion-rendered-controls`;
- rendered JS owner: `sourceDirectoryIngestionRenderedControls()` in `backend/app/review_ui/static/layer3.js`;
- backend/API proof: `backend/tests/test_layer3_source_directory_ingestion.py`;
- rendered/static proof: `backend/tests/test_layer3_page.py`.

Mockup files, SVG frames, screenshots, browser-local state, local storage, copied output, and operator-entered paths are not authority for this target.

## Selected Future Implementation Scope

The future implementation may change only the existing `/review/layer3` source-directory rendered control to make the already-server-owned scan/status authority more complete and operator-auditable.

Allowed future rendered-control extension:

- display `runtime_policy_id`;
- display `recursive_traversal_admitted`;
- display `max_recursion_depth`;
- display `max_relative_path_segments`;
- display `caller_selected_recursive_flag_allowed`;
- display status/schema distinction between scan and status responses;
- preserve redacted `source_root_ref` and `source_root_absolute_path_exposed === false`;
- show idempotency/replay status without changing backend behavior;
- show fail-closed states for unset server configuration, missing batch, blocked status lookup, and blocked scan;
- keep all source-directory authority display derived from scan/status responses;
- add or tighten static page tests and headed/headless browser proof for the existing rendered control.

No backend, route, model, migration, storage, source traversal, package, connector, provider, RAG/vector, auth/security, or optional-tool behavior may be changed by the future implementation under this freeze.

## Required Future Write Scope

The later implementation should be limited to:

- `backend/app/review_ui/static/layer3.html`;
- `backend/app/review_ui/static/layer3.js`;
- `backend/app/review_ui/static/layer3.css` only if layout or responsive proof requires it;
- `backend/tests/test_layer3_page.py`;
- `e2e/layer3-workbench.spec.js` only for headed/headless proof of the existing rendered control;
- progress/proof docs and manifests needed to record the implementation.

Any change outside those files requires a new freeze unless it is only a checker/progress guard update for this exact implementation.

## No-Go Surface

The future implementation must not admit:

- caller-supplied paths;
- caller-supplied directories;
- browser file bytes;
- URL input;
- glob input;
- caller-selected recursive flag;
- new source upload behavior;
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
- auth/security behavior change;
- browser-storage authority;
- frontend-only durable state.

## Pressure-Tested Decisions

The `grill-me` decision tree was resolved from repo authority rather than user interruption:

| Question | Answer | Justification |
| --- | --- | --- |
| Should the next pass activate the full mockup program? | No | `layer3_mockup_boundary.py` still keeps mockups target-state-only, and full-program scope would cross unresolved source, package, connector, provider, RAG, browser-state, and auth/security boundaries. |
| Should the next pass promote a mockup screen directly? | No | A single mockup screen still lacks an exact route/state/test contract. |
| Should the next pass use a read-only alternate target? | No, unless source-directory work blocks | Internal webhook and Analysis Environment surfaces are safe but read-only; they do not exercise the first action-capable control path. |
| Should the next pass extend the source-directory rendered control? | Yes | It already has server-configured scan/status APIs, durable batch/file authority, redaction behavior, idempotency tests, rendered controls, and bounded page tests. |
| Should the extension change backend behavior? | No | The current scan/status response already contains enough authority fields for the first rendered extension. |

## Immediate Milestone

Milestone 1: current-main sync this freeze, then implement `extend_source_directory_ingestion_scan_status_rendered_control`.

Exit criteria:

- the source-directory rendered control displays the selected authority fields;
- unset/missing/blocked server states fail closed in UI and tests;
- no forbidden request fields are introduced;
- no backend/API/model/migration behavior changes occur;
- headed and headless Chromium proof pass for `/review/layer3`;
- `python .\tools\l3-progress-check.py` passes.

## Mid-Term Milestones

Milestone 2: source-directory rendered extension runtime proof and current-main sync.

Milestone 3: choose one `single_mockup_screen_read_only_projection` candidate only after mapping its fields to server-owned state.

Milestone 4: implement that read-only projection with headed/headless/theme/responsive proof and no browser-local authority.

Milestone 5: choose one `single_mockup_screen_server_authoritative_activation` candidate only after exact route/API/state/durable-owner/idempotency/stale-recovery contracts exist.

Milestone 6: implement the first server-authoritative mockup-screen activation as a bounded workflow, not a full-program activation.

Milestone 7: repeat bounded screen/control activations until the mockup-to-live matrix has no unmapped critical operator journey.

## Long-Term Milestones

Milestone 8: resolve remaining source breadth, package mutation, connector/destination, provider URL, qualitative/hybrid/RAG, optional-tool, browser-state, and auth/security blockers as separately frozen server-authoritative lanes.

Milestone 9: run a full mockup activation readiness audit proving every mockup control is one of:

- live and server-authoritative;
- live and read-only projection only;
- intentionally excluded;
- still blocked with a named blocker.

Milestone 10: admit `full_mockup_program_activation` only after the readiness audit proves full route/state/test/browser/security coverage and no frontend-only durable authority.

## Required Proof For Later Implementation

The future implementation must provide:

- static page tests for DOM/JS contract;
- negative tests that forbidden request fields do not appear in rendered payload construction;
- no raw local path exposure in rendered output;
- headed Chromium proof;
- headless Chromium proof;
- responsive no-horizontal-overflow proof;
- theme compatibility proof for the existing `/review/layer3` theme model;
- progress-check guard for the exact implemented scope;
- proof manifest entry tying the implementation back to this freeze.

## Non-Admission Boundary

This freeze admits no runtime behavior, no rendered behavior, no route/API/DTO/model/migration/service behavior change, no UI control change now, no test behavior change now, no full mockup activation, no single mockup screen activation, no frontend-only durable state, no browser-storage authority, no caller path/file/URL/glob/recursive flag support, no source expansion, no package mutation, no connector/destination dispatch, no provider URL behavior, no RAG/vector widening, no hidden LLM planning, no optional-tool runtime, and no auth/security behavior.

## Validation Basis

Required validation for this freeze:

- `python .\tools\l3-progress-check.py`;
- JSON validation for `next_milestone_plans/layer3_progress_manifest.json`;
- JSON validation for `next_milestone_plans/layer3_workbench_proof_manifest.json`;
- `git diff --check`.

No runtime, API, or browser test is required for this freeze because it changes no runtime behavior, route, dependency, session-summary field, rendered UI, or browser behavior.

## Next Posture

The next exact posture is `current_main_sync_source_directory_extension_freeze_then_implementation`.

After that sync, the only admitted implementation action is `extend_source_directory_ingestion_scan_status_rendered_control`.
