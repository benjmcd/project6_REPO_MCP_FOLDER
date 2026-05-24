# 993 - Candidate B Rendered Workflow Run Start Control Freeze

## Purpose

Select the next bounded Candidate B operator slice after `992-cb-server-run-live-http-proof.md`: a rendered start/progress control that calls the already-proven server-owned workflow-run endpoint, then inspects the returned status request through the existing read-only workflow status endpoint.

This checkpoint is a no-runtime authority freeze. It does not add rendered behavior yet. It admits the next implementation slice only after this freeze lands on current main.

```yaml
milestone: candidate_b_rendered_operator_workflow_run_start_control_freeze_v1
source_live_http_proof: next_milestone_plans/Layer3_planning_docs/992-cb-server-run-live-http-proof.md
current_main_entry: 45c93d83bb9b99aad6c993bca36ba3241a618902
selected_next_slice: candidate_b_rendered_operator_workflow_run_start_control_authority_v1
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_runtime_target: candidate_b_rendered_operator_workflow_run_start_control_v1
selected_run_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
selected_rendered_start_mode: rendered_candidate_b_full_corpus_operator_workflow_run_start_control
selected_rendered_progress_mode: rendered_candidate_b_full_corpus_operator_workflow_run_progress_control
run_schema_id: layer3.candidate_b_full_corpus_operator_workflow_run.v1
run_mode: candidate_b_full_corpus_operator_workflow_run_v1
operator_decision: start_candidate_b_full_corpus_operator_workflow
status_mode: candidate_b_full_corpus_operator_workflow_status_v1
status_operator_decision: inspect_candidate_b_full_corpus_operator_workflow_status
accepted_scope: prepared_full_corpus_eligible_pdf_operator_runs_on_configured_live_server
source_authority_model: server_owned_runtime_root_lifecycle_receipt_plus_compare_target_set
server_resolves_source_workflow_receipt_from_configured_receipt_dir: true
rendered_start_control_admitted_after_sync: true
rendered_progress_control_admitted_after_sync: true
rendered_status_control_already_admitted: true
status_endpoint_reused_after_run: true
run_endpoint_status_request_must_be_used: true
allowed_browser_supplied_run_fields: client_request_id,run_mode,operator_decision,runtime_root_lifecycle_receipt_id,baseline_run_id,candidate_a_run_id,candidate_b_run_id,compare_target_set_hash,material_relative_name
browser_supplied_runtime_roots_admitted: false
browser_supplied_source_directory_admitted: false
browser_supplied_workflow_receipt_path_admitted: false
browser_supplied_bridge_dir_admitted: false
browser_storage_authority_admitted: false
frontend_durable_authority_enabled: false
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
selector_mutation_allowed: false
baseline_rollback_preserved: true
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
provider_object_writes_enabled: false
provider_public_url_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
queue_scheduler_runtime_admitted: false
cancel_runtime_admitted: false
arbitrary_corpus_processing_start_admitted: false
proof_required_headless_chrome: true
proof_required_headed_chrome: true
proof_must_show_run_endpoint_called_once: true
proof_must_show_status_endpoint_called_with_returned_status_request: true
proof_must_show_no_raw_path_or_url_payload_fields: true
proof_must_show_no_frontend_durable_authority: true
next_exact_posture: candidate_b_rendered_operator_workflow_run_start_control_v1
```

## Admitted Next Runtime Slice

The admitted implementation may add a rendered control inside the existing Candidate B full-corpus operator workflow panel. The rendered control may:

- collect the server authority identifiers required by the run endpoint;
- generate a browser request id for the run request;
- post to the server-owned run endpoint;
- store only the returned redacted response in transient UI state;
- immediately inspect progress/status by posting the returned `status_request` to the existing status endpoint;
- display run state, workflow status, receipt ids/hashes, redaction flags, and blocked-state details.

The implementation must keep the existing read-only workflow status control available for direct receipt inspection.

## Not Admitted

This freeze does not admit broad corpus processing start, source-root selection, browser-owned durable authority, local path submission, raw URL submission, provider object writes, arbitrary connector dispatch, RAG/vector/model runtime, full mockup activation, queue scheduling, cancel runtime, broader Candidate B default scope, baseline default removal, or Candidate A semantic changes.

## Required Proof

The implementation proof must include both headless and headed Chrome coverage when practical. It must prove the rendered start/progress control calls only:

1. `POST /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run`
2. `POST /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status`

The proof must also assert that the run payload omits raw local paths, raw URLs, selector mutation fields, provider refs, connector destinations, frontend durable authority, and arbitrary runtime-root/source-directory fields. The status payload must be the `status_request` returned by the run endpoint.
