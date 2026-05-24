# 992 - Candidate B Server-Owned Workflow Run API Live HTTP Proof

## Purpose

Prove the server-owned Candidate B full-corpus workflow-run endpoint through a configured live FastAPI server, durable SQLite database, and the existing read-only status endpoint. This closes the live proof slice selected by `991-cb-server-run-api-runtime.md` without admitting rendered run-start/progress controls or broader runtime scope.

```yaml
milestone: candidate_b_server_owned_workflow_run_api_live_http_proof_v1
source_runtime_checkpoint: next_milestone_plans/Layer3_planning_docs/991-cb-server-run-api-runtime.md
current_main_entry: 35b5613e3cfa7c5155ce2e25f097f298eae7b9df
execution_mode: live-http
live_http_layer3_api_used: true
testclient_dependency_used: false
in_memory_db_used: false
durable_database_used: true
server_run_endpoint_verification_required: true
selected_run_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
run_schema_id: layer3.candidate_b_full_corpus_operator_workflow_run.v1
run_mode: candidate_b_full_corpus_operator_workflow_run_v1
operator_decision: start_candidate_b_full_corpus_operator_workflow
server_run_endpoint_verified: true
status_endpoint_verified_after_server_run: true
server_run_state: proven
workflow_status_after_server_run: proven
operator_workflow_receipt_id: cb-full-corpus-operator-run-a281171ae1718620ff0dfdb8
operator_workflow_receipt_hash: 2c365c456eea0300c60a4d99c8ff28b8c3b79413087d6df03ffe962d292a9d87
source_operator_workflow_receipt_id: cb-full-corpus-operator-2c365c456eea0300c60a4d99
source_operator_workflow_receipt_hash: 2c365c456eea0300c60a4d99c8ff28b8c3b79413087d6df03ffe962d292a9d87
authority_basis_hash: b10068440d99e496dbace35fd004eb3d7b0e6b46bc703b3f2bdd435e3cac98b9
idempotency_key_hash: a281171ae1718620ff0dfdb8625d1561aa034fe750b9e164037999114353de5b
workflow_status_hash_after_server_run: 0e6005881f8b10f454fb40a0b06c298a8f4922c9da5343c5e9b21e051a5c002f
source_workflow_status_hash: 96ff73f0aed18ff8f4e4b68809314b378b2ac0ed317a8a9b16bce9d50098f9fd
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
bridge_receipt_hash: 0110fe894c68d6a0291f997998616c7dacff8bbd2897bdcb68d5f877dbc8de62
downstream_proof_id: cb-runtime-downstream-proof-b63d0968304450c4031312ba
downstream_proof_hash: b63d0968304450c4031312baf7ed81fdf29502d12dbc1e6e3735d16a9f491e77
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
runtime_root_lifecycle_receipt_hash: ab3c4fd0b54ca670ada781f9d3797bda562fa53c0416399c8c2c38c20360f45d
compare_target_set_hash: 1052eea1153d6fdb21abd18384abc5c2db73497c9d34f18ecf52239f71c82a2f
corpus_pdf_count: 69
eligible_pdf_count: 69
failed_pdf_count: 0
skipped_pdf_count: 0
curated_file_count: 71
governed_retained_artifact_family_hash: bc32ee4f789f078b9f1d1e46dd9402df5b92aeb4afbde369fbd00553e6a61380
live_http_runtime_dirs_isolated: true
bridge_dir_outside_storage_root_required: true
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
baseline_rollback_preserved: true
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
frontend_durable_authority_enabled: false
provider_object_writes_enabled: false
provider_public_url_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
rendered_run_start_control_admitted: false
rendered_progress_control_admitted: false
verification: python .\tools\run_candidate_b_full_corpus_operator_workflow.py --execution-mode live-http --api-base-url http://127.0.0.1:8098/api/v1/layer3 --http-timeout-seconds 120 --internal-webhook-mode configured --baseline-run-root .\backend\app\storage_test_runtime\lc_e2e\baseline-full-corpus-v2 --candidate-a-run-root .\backend\app\storage_test_runtime\lc_e2e\candidate-a-full-corpus-v1 --candidate-b-run-root .\backend\app\storage_test_runtime\lc_e2e\cb-full-corpus-v1 --bridge-dir .\backend\app\storage_test_runtime\cb-srun-bridge2 --receipt-dir .\backend\app\storage_test_runtime\lc_e2e\cb-srun-workflow2 --runtime-root-lifecycle-dir .\backend\app\storage_test_runtime\lc_e2e\cb-srun-rrl2 --layer3-storage-dir .\backend\app\storage_test_runtime\lc_e2e\cb-live-http-storage
verification_result: proven
next_exact_posture: candidate_b_rendered_operator_workflow_run_start_control_freeze_v1
```

## Proof Notes

The proof used a configured live server with `DB_INIT_MODE=create_all`, a durable SQLite database, the existing full-corpus baseline/Candidate A/Candidate B runtime roots, and an isolated proof-local workflow receipt directory. The Candidate B runtime bridge directory was kept outside the live `STORAGE_DIR` because the current runtime bridge guard correctly fails closed when the bridge output directory overlaps app-owned storage/export staging.

The live runner first created the source Candidate B full-corpus workflow receipt through the existing runtime bridge/downstream path, verified the read-only status endpoint, then called the server-owned run endpoint. The run endpoint returned a status request, and the runner used that returned request to re-read the durable server-owned run receipt through the status endpoint.

The proof did not persist the raw API base URL, expose raw local paths or raw URLs, submit browser-owned runtime roots, mutate selectors, enable rendered run-start/progress controls, add provider writes, dispatch arbitrary connectors, enable RAG/vector/model runtime, or activate the full mockup.

## Next Posture

The next exact slice is a no-runtime or bounded-runtime decision for `candidate_b_rendered_operator_workflow_run_start_control_freeze_v1`: decide whether and how a rendered operator start/progress surface may call the already-proven server-owned run endpoint while preserving server authority, redaction, rollback, and fail-closed behavior.
