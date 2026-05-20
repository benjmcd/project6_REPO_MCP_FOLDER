# 909 - Representative Mockup Scenario Source-To-Output-Handoff E2E Proof

Status: executable proof implemented for `representative_mockup_scenario_source_to_output_handoff_e2e_proof`.

Proof doc: `909_REPRESENTATIVE_MOCKUP_SCENARIO_SOURCE_TO_OUTPUT_HANDOFF_E2E_PROOF.md`.

Predecessor freeze doc: `908_REPRESENTATIVE_MOCKUP_SCENARIO_SOURCE_TO_OUTPUT_HANDOFF_E2E_PROOF_FREEZE.md`.

Current-main checkpoint before this proof: `df6c2128ba3dfcde757fb5ec53fa7634e3a7b1a3`.

Implementation branch: `codex/l3-representative-scenario-proof`.

Selected scenario identity: `representative_mockup_scenario_source_directory_hybrid_context_packet_to_output_handoff`.

Selected proof target: `representative_mockup_scenario_source_to_output_handoff_e2e_proof`.

Selected executable proof test: `backend/tests/test_layer3_source_directory_vector_retrieval.py::test_representative_mockup_scenario_source_to_output_handoff_e2e_proof`.

Runtime behavior introduced by this proof: `false`.

Rendered behavior introduced by this proof: `false`.

Backend behavior introduced by this proof: `false`.

Route/API/DTO/model/migration/service behavior introduced by this proof: `false`.

Executable test behavior introduced by this proof: `true`.

Full mockup program activation selected: `false`.

Implementation-entry allowed for full mockup activation by this proof alone: `false`.

## Proof Decision

This proof converts the Doc 908 planning/control freeze into one executable, deterministic, API-only representative scenario. It does not add a mockup-frame write control, broaden source selection, introduce caller-supplied paths or bytes, invoke a real connector or destination, widen provider/public URL behavior, add model/provider runtime, or make frontend/browser storage durable authority.

The proof stays on the existing current-main source-directory hybrid context-packet qualitative-analysis route family because that route family already spans the useful activation chain: server-configured source authority, material admission, deterministic local retrieval/context/analysis evidence, bounded package output authority, package-review approval, handoff-export preparation, reference-only external export download readiness, and same-origin delivery proof without connector dispatch or provider/public URL runtime.

## Executed Scenario Steps

The executable test covers these steps in one named representative scenario:

1. Creates an isolated runtime database and isolated source directory fixture.
2. Writes deterministic local source content under the server-configured source directory only.
3. Calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/scan`.
4. Calls `GET /api/v1/layer3/source/ingestion/server-configured-directory/status/{source_ingestion_batch_id}` and proves status is server-derived.
5. Calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/material-preview`.
6. Calls `POST /api/v1/layer3/gate-b/decision` and persists the admitted material snapshot.
7. Establishes deterministic local text/vector/hybrid context authority without provider/model/network runtime.
8. Calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis`.
9. Calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/status`.
10. Calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/commit`.
11. Calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/package/review/submit`.
12. Calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/prepare`.
13. Calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/prepare`.
14. Calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver/status`.
15. Calls `POST /api/v1/layer3/source/ingestion/server-configured-directory/hybrid-context-packet/qualitative-analysis/handoff/export/download/deliver`.
16. Verifies persisted `L3OutputPackage` and `L3ReconciliationRecord.summary_json` state after durable transitions.
17. Verifies no `ConnectorRun` or `ConnectorRunTarget` rows are created.
18. Verifies no provider/public URL, credential, network egress, frontend-storage, raw local path, raw payload ref, browser-supplied byte, glob, URL, or caller-selected recursive source expansion is admitted.
19. Verifies mockups remain target-state-only by asserting `full_mockup_activation_enabled` is `false` and `frontend_only_durable_state_enabled` is `false` from the mockup truth-state boundary.

## Proof Boundaries

The proof admits only executable test behavior. It does not admit runtime behavior, rendered behavior, backend behavior, route/API/DTO/model/migration/service behavior, production UI behavior, full mockup program activation, mockup-frame write control, broad source picker, caller path/directory/file-byte/URL/glob/recursive controls, real connector/destination dispatch, provider/public URL runtime, broad RAG/vector or hidden LLM behavior, model/provider runtime, optional-tool runtime, auth/security behavior, browser-storage authority, frontend-only durable authority, package mutation/reconstruction expansion, or source expansion beyond the existing server-configured source-directory fixture.

## Validation Basis

Required validation for this proof:

- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_representative_mockup_scenario_source_to_output_handoff_e2e_proof -q`;
- `python -m json.tool .\next_milestone_plans\layer3_progress_manifest.json`;
- `python -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json`;
- `python -m py_compile .\tools\l3-progress-check.py`;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

Branch-local validation observed during proof authoring:

- `python -m pytest .\backend\tests\test_layer3_source_directory_vector_retrieval.py::test_representative_mockup_scenario_source_to_output_handoff_e2e_proof -q` passed with `1 passed, 3 warnings`.

## Next Posture

The next exact posture is `current_main_sync_representative_mockup_scenario_source_to_output_handoff_e2e_proof_then_final_full_mockup_program_readiness_audit`.

After this proof is synced to current main, the next target is a final full mockup program readiness audit. Do not select full mockup program activation until that audit proves every critical mockup operator journey is live, read-only, excluded, or explicitly blocked against current-main evidence.
