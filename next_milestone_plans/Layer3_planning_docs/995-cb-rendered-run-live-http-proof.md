# 995 - Candidate B Rendered Workflow Run Live HTTP Proof

## Purpose

Prove the rendered Candidate B full-corpus workflow-run start/progress control against a configured live Layer 3 FastAPI server. This closes the next posture from `994-cb-rendered-run-start-control.md` by showing that the browser-rendered operator surface can call the server-owned workflow-run endpoint and then inspect progress through the returned status request without Playwright route stubs, TestClient, in-memory database state, raw path/URL submission, selector mutation, provider writes, connector dispatch, model runtime, or full mockup activation.

```yaml
milestone: candidate_b_rendered_operator_workflow_run_live_http_operator_proof_v1
source_rendered_control_checkpoint: next_milestone_plans/Layer3_planning_docs/994-cb-rendered-run-start-control.md
source_live_http_api_checkpoint: next_milestone_plans/Layer3_planning_docs/992-cb-server-run-live-http-proof.md
current_main_entry: 1a124dfcfd548181acb633a9cacadcc1446f3228
execution_mode: live-http-rendered-browser
live_http_layer3_api_used: true
testclient_dependency_used: false
in_memory_db_used: false
durable_database_required: true
playwright_browser_surface_used: true
selected_rendered_start_mode: rendered_candidate_b_full_corpus_operator_workflow_run_start_control
selected_rendered_progress_mode: rendered_candidate_b_full_corpus_operator_workflow_run_progress_control
selected_run_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
source_operator_workflow_receipt_id: cb-full-corpus-operator-2c365c456eea0300c60a4d99
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
baseline_run_id: 7958ca0c-d163-4c6e-a0bf-2cac4e4bfe20
candidate_a_run_id: 9b09f014-95f9-41cb-820c-8f5296a993bc
candidate_b_run_id: f644b3f6-a7a9-4889-84d9-d842f5d12e79
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
material_relative_name: text/target-00001.md
headless_chromium_proof_receipt_id: cb-rendered-run-live-http-3e92b0d89030d0d329b52c4c
headless_chromium_proof_hash: 3e92b0d89030d0d329b52c4cb6c77c3bc08adce41fd304676b76e0d02758791e
headed_chromium_proof_receipt_id: cb-rendered-run-live-http-62a856b709e3504edf1307a3
headed_chromium_proof_hash: 62a856b709e3504edf1307a33fc0275d5e8915dca7f0160563c5ec62d869869f
run_endpoint_verified: true
status_endpoint_verified_after_rendered_run: true
run_endpoint_status_request_used_for_progress: true
rendered_payload_allowed_fields_only: true
forbidden_rendered_payload_fields_present: []
frontend_durable_authority: false
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
runtime_roots_submitted_by_browser: false
source_directory_submitted_by_browser: false
bridge_dir_submitted_by_browser: false
selector_mutation_performed: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
verification_headless_rendered_live_http: passed
verification_headed_rendered_live_http: passed
verification_script_syntax: node --check .\tools\prove_candidate_b_rendered_workflow_run_live_http.js
next_exact_posture: candidate_b_operator_workflow_run_history_and_lifecycle_selection_v1
```

## Proof Notes

The proof used a live `backend/main.py` FastAPI server on current main with `DB_INIT_MODE=create_all`, a proof-local durable SQLite database, and a proof-local `STORAGE_DIR`. The configured Candidate B workflow receipt directory pointed at the current checkout's prior live HTTP server-run proof receipt family so this pass could test the rendered browser start/progress path without rerunning corpus processing or inventing source evidence.

The proof helper opens `/review/layer3`, verifies the run form advertises the admitted rendered start/progress modes and `data-frontend-durable-authority="false"`, fills only server authority identifiers from the workflow receipt, clicks the rendered start control, waits for the live run endpoint and live status endpoint, and proves the status POST body exactly equals the `status_request` returned by the run endpoint.

Headless and headed Chromium both reached a live `candidate_b_full_corpus_workflow_run_proven` rendered state. The browser-submitted run payload contained only admitted server authority fields and did not include raw runtime roots, source directories, bridge directories, local paths, raw URLs, provider refs, selector mutations, connector controls, model controls, or frontend durable authority.

## Next Posture

The next exact slice is `candidate_b_operator_workflow_run_history_and_lifecycle_selection_v1`: select the smallest separately admitted server-owned run history/progress/lifecycle surface needed after rendered live start proof. Candidate follow-on work should prefer a read/list/status history projection over broader queue scheduling, cancel/retry runtime, default-scope expansion, provider/connector behavior, RAG/model runtime, or full mockup activation unless current-main authority admits that exact expansion.
