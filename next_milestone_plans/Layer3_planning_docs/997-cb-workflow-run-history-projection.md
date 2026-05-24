# Candidate B Workflow Run History Read-Only Projection

```yaml
milestone: candidate_b_operator_workflow_run_history_read_only_projection_v1
source_selection: next_milestone_plans/Layer3_planning_docs/996-cb-workflow-run-history-selection.md
current_main_entry: dbadb7a35f61fffbb3ddf85118c0e00e06599b8f
runtime_status: implemented
selected_history_scope: server_owned_candidate_b_full_corpus_operator_workflow_run_receipts
selected_history_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
selected_rendered_history_mode: rendered_candidate_b_full_corpus_operator_workflow_run_history_control
history_schema_id: layer3.candidate_b_full_corpus_operator_workflow_history.v1
history_mode: candidate_b_full_corpus_operator_workflow_history_v1
history_service: backend/app/services/layer3_candidate_b_full_corpus_operator_workflow_history.py
history_api_route: backend/app/api/layer3.py
history_rendered_surface: backend/app/review_ui/static/layer3.js
history_e2e_proof: e2e/layer3-workbench.spec.js
selected_source_authority: configured_L3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR
configured_receipt_authority_used: true
read_only_history_projection: true
single_run_status_endpoint_reused_for_detail: true
history_rows_bind_authority_basis_hash: true
history_rows_bind_status_request: true
invalid_or_stale_receipts_fail_closed: true
missing_configured_receipt_root_fails_closed: true
non_run_receipts_fail_closed: true
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
cancel_runtime_admitted: false
retry_runtime_admitted: false
resume_runtime_admitted: false
queue_scheduler_runtime_admitted: false
expiry_mutation_runtime_admitted: false
default_scope_expansion_admitted: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
frontend_durable_authority_enabled: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_performed: false
verification_node_check: passed
verification_backend_py_compile: passed
verification_backend_pytest: 10 passed
verification_headless_rendered_e2e: passed
verification_headed_rendered_e2e: passed
next_exact_posture: candidate_b_operator_workflow_lifecycle_mutation_selection_v1
```

The implemented history projection lists only server-owned Candidate B full-corpus operator workflow-run receipts from configured backend receipt authority. Each row exposes redacted operator-safe identifiers, receipt hashes, authority binding, and the exact server-produced status request needed to inspect that run through the existing read-only status endpoint.

The projection intentionally does not admit browser-provided receipt roots, runtime roots, source directories, bridge directories, raw local paths, raw URLs, queue scheduling, cancel/retry/resume/expiry runtime, default-scope expansion, provider object writes, connector dispatch, RAG/vector/model runtime, full mockup activation, browser-storage authority, or frontend durable authority.

The next candidate slice is a separate lifecycle-mutation selection, not implementation by implication. Any cancel, retry, resume, expiry enforcement, queue scheduling, or broader workflow orchestration must be frozen separately against current-main evidence.
