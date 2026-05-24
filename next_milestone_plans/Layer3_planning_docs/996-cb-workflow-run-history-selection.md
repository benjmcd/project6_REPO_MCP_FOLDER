# 996 - Candidate B Workflow Run History and Lifecycle Selection

## Purpose

Select the smallest next Candidate B workflow-run history/lifecycle slice after the rendered live HTTP start/progress proof in `995-cb-rendered-run-live-http-proof.md`. This is a no-runtime selection/freeze: it admits one bounded read-only history projection target for a later implementation pass and keeps lifecycle mutation, queue scheduling, retry/resume/cancel runtime, default-scope expansion, provider/connector behavior, RAG/model runtime, and full mockup activation out of scope.

```yaml
milestone: candidate_b_operator_workflow_run_history_and_lifecycle_selection_v1
source_rendered_live_http_proof: next_milestone_plans/Layer3_planning_docs/995-cb-rendered-run-live-http-proof.md
current_main_entry: e35d04ce35e1db16c5a159cf42bf29359b9cce50
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_operator_workflow_run_history_read_only_projection_v1
selected_history_scope: server_owned_candidate_b_full_corpus_operator_workflow_run_receipts
selected_history_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/history
selected_rendered_history_mode: rendered_candidate_b_full_corpus_operator_workflow_run_history_control
selected_source_authority: configured_L3_CANDIDATE_B_FULL_CORPUS_OPERATOR_WORKFLOW_DIR
browser_supplied_receipt_root_admitted: false
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_bridge_dir_admitted: false
operator_supplied_local_path_admitted: false
operator_supplied_raw_url_admitted: false
read_only_history_projection_admitted_after_sync: true
single_run_status_endpoint_reused_for_detail: true
history_rows_must_be_redacted: true
history_rows_must_bind_authority_basis_hash: true
history_rows_must_bind_source_workflow_receipt_id: true
history_rows_must_bind_runtime_root_lifecycle_receipt_id: true
history_rows_must_bind_compare_target_set_hash: true
history_rows_must_bind_run_state: true
history_rows_must_bind_status_request: true
invalid_or_stale_receipts_fail_closed: true
missing_configured_receipt_root_fails_closed: true
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
implementation_admitted_after_current_main_sync: true
next_exact_posture: candidate_b_operator_workflow_run_history_read_only_projection_v1
```

## Selected Target

The selected next implementation is `candidate_b_operator_workflow_run_history_read_only_projection_v1`: a server-owned, read-only workflow-run history projection over Candidate B full-corpus workflow-run receipts written by the existing run endpoint. The server must resolve history only from configured receipt authority, not from browser-supplied roots, local paths, raw URLs, source directories, bridge directories, runtime roots, or storage selectors.

The history rows should expose only redacted/operator-safe metadata:

- run receipt id and receipt hash;
- source operator workflow receipt id and hash;
- authority basis hash;
- runtime-root lifecycle receipt id;
- baseline, Candidate A, and Candidate B run ids;
- compare target set hash;
- material relative name;
- run state and lifecycle states;
- status request for the existing read-only status endpoint;
- created/server time where available;
- negative-invariant summary.

The rendered operator surface should be read-only and should use the history row's server-provided status request to inspect a selected run through the existing status endpoint. It must not implement cancel, retry, resume, expiry mutation, queue scheduling, arbitrary corpus processing start, selector changes, provider writes, connector dispatch, RAG/vector/model runtime, full mockup activation, browser storage authority, or frontend durable authority.

## Non-Admission Boundaries

This freeze does not admit broad lifecycle mutation. `cancelled` and `expired` remain lifecycle states that can be reported from server authority, not states the browser can set. Any later cancel/retry/resume/expiry enforcement must be selected and proven separately with stale-authority rejection, audit receipts, and rollback/fail-closed behavior.
