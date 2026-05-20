# 908 - Representative Mockup Scenario Source-To-Output-Handoff E2E Proof Freeze

Status: planning/control freeze for `freeze_representative_mockup_scenario_source_to_output_handoff_e2e_proof_before_full_program_activation`.

Freeze doc: `908_REPRESENTATIVE_MOCKUP_SCENARIO_SOURCE_TO_OUTPUT_HANDOFF_E2E_PROOF_FREEZE.md`.

Predecessor audit doc: `907_FULL_MOCKUP_TO_LIVE_COVERAGE_READINESS_AUDIT_AFTER_OUTPUT_REVIEW_PACKAGE_HANDOFF_PROJECTION_SYNC.md`.

Current-main checkpoint before this freeze: `ca195b117ece8704eba04c242aa69ba90b7f61a6`.

Selected freeze mode: `representative_mockup_scenario_e2e_proof_freeze`.

Selected scenario identity: `representative_mockup_scenario_source_directory_hybrid_context_packet_to_output_handoff`.

Selected proof target: `representative_mockup_scenario_source_to_output_handoff_e2e_proof`.

Selected proof action after freeze sync: `implement_representative_mockup_scenario_source_to_output_handoff_e2e_proof_after_freeze_sync`.

Runtime behavior introduced by this freeze: `false`.

Rendered behavior introduced by this freeze: `false`.

Backend behavior introduced by this freeze: `false`.

Route/API/DTO/model/migration/service behavior introduced by this freeze: `false`.

Executable test behavior introduced by this freeze: `false`.

Full mockup program activation selected: `false`.

Implementation-entry allowed by this freeze: `false`.

## Freeze Decision

The representative proof must exercise one deterministic source-to-output-to-handoff path using existing current-main authority. It must not create a new mockup-frame write control, broaden source selection, introduce caller-supplied paths or bytes, invoke a real connector or destination, widen provider/public URL behavior, add model/provider runtime, or make frontend/browser storage durable authority.

The selected representative path is the current-main source-directory hybrid context-packet qualitative-analysis route family. It is adequate because it starts from server-configured source-directory ingestion, produces deterministic local retrieval/context/analysis evidence, writes bounded output package authority, records package-review approval, prepares handoff/export evidence, prepares reference-only external export download readiness, and proves delivery/status behavior without connector dispatch or provider/public URL runtime.

## Canonical Source Of Truth

The canonical source of truth for the proof is current repo runtime behavior, not the mockup visual frame:

- Source authority: `LAYER3_SOURCE_INGESTION_DIR`, `L3SourceDirectoryIngestionBatch`, `L3SourceDirectoryIngestionFile`, and `L3MaterialSnapshot`.
- Retrieval/context authority: deterministic local source-directory text/vector/hybrid context authority, including deterministic local source-directory text/vector index and hybrid context packet authority.
- Output authority: `L3OutputPackage` rows written by the bounded source-directory hybrid context-packet package commit path.
- Review/handoff authority: `L3ReconciliationRecord.summary_json` package-review, handoff-export, and external-export-download state.
- Rendered/mockup authority: `/review/layer3 projection-only mockup surfaces` may project status, but `/review/layer3` must not become durable authority for this proof.

## Required Scenario Steps

The future executable proof must cover these steps as one named representative scenario:

1. Create an isolated runtime database and isolated source directory fixture.
2. Write deterministic local source content under the server-configured source directory only.
3. Call `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`.
4. Call `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}` and prove status is server-derived.
5. Call `POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview`.
6. Call `POST /api/v1/layer3/gate-b/decision` and persist the admitted material snapshot.
7. Establish deterministic local text/vector/hybrid context authority without provider/model/network runtime.
8. Call `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis`.
9. Call `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/status`.
10. Call `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/commit`.
11. Call `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/review/submit`.
12. Call `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/prepare`.
13. Call `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare`.
14. Call `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status`.
15. Call `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver`.
16. Verify persisted `L3OutputPackage` and `L3ReconciliationRecord.summary_json` state after each durable transition.
17. Verify no `ConnectorRun` or `ConnectorRunTarget` rows are created.
18. Verify no provider/public URL, credential, network egress, frontend-storage, raw local path, raw payload ref, browser-supplied byte, glob, URL, or recursive source expansion is admitted.
19. Verify `/review/layer3` mockup projections remain projection-only if rendered proof is added; the mockup frame must not introduce a write control or durable authority.

## Proof Obligations

The representative proof must prove all of these invariants:

- `full_mockup_activation_enabled` remains `false`.
- `frontend durable authority false` remains true for the scenario.
- `representative_mockup_scenario_source_to_output_handoff_e2e_proof` is the proof identity.
- Server-configured source-directory ingestion remains the only source input path.
- Package commit writes bounded `L3OutputPackage` authority only.
- Package-review submit records approval authority without package payload rewrite.
- Handoff export prepare records internal export-envelope authority only.
- External export download prepare remains reference-only readiness.
- Delivery/status proof does not admit provider/public URL runtime or real connector/destination dispatch.
- Headed and headless Chromium are required only if the follow-up proof asserts rendered `/review/layer3` behavior; API-only proof must not imply rendered mockup activation.

## Checker Labels

The progress checker must preserve these exact proof-step labels:

- `isolated runtime database and isolated source directory fixture`;
- `server-configured source-directory scan/status`;
- `material-preview and Gate B decision`;
- `deterministic local text/vector/hybrid context authority`;
- `hybrid context-packet qualitative-analysis/status`;
- `package commit`;
- `package-review submit`;
- `handoff export prepare`;
- `external export download prepare`;
- `delivery status and delivery`;
- `persisted L3OutputPackage verification`;
- `persisted L3ReconciliationRecord.summary_json verification`;
- `negative ConnectorRun and ConnectorRunTarget verification`;
- `negative provider/public URL, network egress, browser-storage, frontend durable authority, raw path, raw payload ref, browser bytes, URL/glob/recursive source expansion verification`;
- `full_mockup_activation_enabled false`;
- `frontend durable authority false`.

## Non-Admission Boundary

This freeze admits no runtime behavior, no rendered behavior, no backend behavior, no route/API/DTO/model/migration/service behavior change, no executable test behavior, no production UI behavior, no full mockup program activation, no mockup-frame write control, no broad source picker, no caller path/directory/file-byte/URL/glob/recursive controls, no real connector/destination dispatch, no provider/public URL runtime, no broad RAG/vector or hidden LLM behavior, no model/provider runtime, no optional-tool runtime, no auth/security behavior, no browser-storage authority, no frontend-only durable authority, no package mutation/reconstruction expansion, and no source expansion beyond the existing server-configured source-directory fixture.

## Validation Basis

Required validation for this freeze:

- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

No API, runtime, browser, or Playwright proof is required for this freeze because it changes no runtime behavior, rendered UI behavior, route, dependency, session-summary field, executable test, or browser behavior.

Additional current-state sanity check observed during freeze authoring:

- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_source_directory_hybrid_context_packet_qualitative_analysis_external_export_download_delivers_selected_package -q` passed with `1 passed, 3 warnings`.

## Next Posture

The next exact posture is `current_main_sync_representative_mockup_scenario_source_to_output_handoff_e2e_proof_freeze_then_implement_proof`.

After current-main sync, the next implementation target is `implement_representative_mockup_scenario_source_to_output_handoff_e2e_proof_after_freeze_sync`.

Do not select full mockup program activation until this representative proof, its current-main sync, and a final full-program readiness audit pass with current-main evidence.
