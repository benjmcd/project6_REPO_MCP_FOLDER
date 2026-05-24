# Candidate B Workflow Run Lifecycle Mutation Selection

```yaml
milestone: candidate_b_operator_workflow_lifecycle_mutation_selection_v1
source_history_projection: next_milestone_plans/Layer3_planning_docs/997-cb-workflow-run-history-projection.md
current_main_entry: 0b48b12da7d48f8faefdb46d93d955130041ab13
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_operator_workflow_run_expiry_closeout_receipt_v1
selected_lifecycle_scope: server_owned_candidate_b_full_corpus_operator_workflow_run_receipts
selected_lifecycle_action: expire_or_close_server_owned_workflow_run_receipt
selected_lifecycle_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/lifecycle/expire
selected_source_authority: configured_L3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR
existing_history_endpoint_reused_for_list: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
existing_status_endpoint_reused_for_detail: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_lifecycle_receipt_model: append_only_lifecycle_receipt_without_mutating_source_run_receipt
selected_lifecycle_receipt_binding: operator_workflow_receipt_id,operator_workflow_receipt_hash,row_hash,authority_basis_hash,history_hash
selected_idempotency_basis: client_request_id_plus_lifecycle_authority_hash
stale_run_receipt_rejected: true
stale_history_row_rejected: true
missing_run_receipt_rejected: true
source_run_receipt_mutation_admitted: false
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
cancel_runtime_selected_now: false
retry_runtime_selected_now: false
resume_runtime_selected_now: false
queue_scheduler_runtime_selected_now: false
expiry_closeout_runtime_selected_after_sync: true
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
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_operator_workflow_run_expiry_closeout_receipt_v1
```

The selected next runtime slice is an append-only expiry/closeout receipt for an already server-owned Candidate B full-corpus operator workflow run. This is the smallest lifecycle mutation that moves the platform toward production-grade workflow authority without introducing an async scheduler or pretending that synchronous proven runs can be cancelled or resumed.

The first runtime implementation must validate the current run receipt, history row, authority basis, and source workflow receipt before writing any lifecycle receipt. It must fail closed on stale or missing authority and must not mutate the original workflow-run receipt. The rendered/operator path should refresh history, select one run, submit only bounded receipt/hash authority plus an admitted operator decision, then inspect the resulting lifecycle state without exposing raw paths, URLs, credentials, provider refs, connector destinations, browser storage authority, or frontend durable authority.

Cancel, retry, resume, and queue scheduling remain intentionally unselected. They require separately admitted async workflow runtime authority, scheduler semantics, and operator rollback behavior.
