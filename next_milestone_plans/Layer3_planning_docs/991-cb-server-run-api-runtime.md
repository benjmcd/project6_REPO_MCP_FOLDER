# 991 - Candidate B Server-Owned Workflow Run API Runtime

## Purpose

Implement the runtime slice admitted by `990-cb-server-run-api-freeze.md`: a server-owned Candidate B full-corpus workflow-run endpoint that starts from configured server receipt authority, writes a durable status-compatible workflow receipt, and keeps rendered run-start/progress controls deferred.

```yaml
milestone: candidate_b_server_owned_workflow_run_api_runtime_v1
source_authority_freeze: next_milestone_plans/Layer3_planning_docs/990-cb-server-run-api-freeze.md
current_main_entry: c0f8df9b4bf53b653197b505eec1a9f454948fae
runtime_status: implemented
selected_run_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
run_schema_id: layer3.candidate_b_full_corpus_operator_workflow_run.v1
run_mode: candidate_b_full_corpus_operator_workflow_run_v1
operator_decision: start_candidate_b_full_corpus_operator_workflow
accepted_scope: prepared_full_corpus_eligible_pdf_operator_runs_on_configured_live_server
source_authority_model: server_owned_runtime_root_lifecycle_receipt_plus_compare_target_set
server_resolves_source_workflow_receipt_from_configured_receipt_dir: true
workflow_receipt_binding_required: true
runtime_root_lifecycle_receipt_required: true
baseline_run_id_required: true
candidate_a_run_id_required: true
candidate_b_run_id_required: true
compare_target_set_hash_required: true
idempotency_key_required: true
idempotency_basis: client_request_id_plus_authority_basis_hash
state_machine: accepted,running,proven,blocked,cancelled,expired
durable_run_receipt_written: true
status_endpoint_compatibility: proven
status_endpoint_request_returned: true
baseline_rollback_preserved: true
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
selector_mutation_allowed: false
client_supplied_raw_runtime_roots_admitted: false
browser_supplied_runtime_roots_admitted: false
raw_api_base_url_persisted: false
raw_local_path_exposed: false
raw_url_exposed: false
artifact_bytes_exposed: false
frontend_durable_authority_enabled: false
provider_object_writes_enabled: false
provider_public_url_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
auth_security_expansion_enabled: false
broader_corpus_default_scope_enabled: false
rendered_run_start_control_admitted: false
rendered_progress_control_admitted: false
next_exact_posture: candidate_b_server_owned_workflow_run_api_live_http_proof_v1
```

## Implemented Behavior

`POST /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run` accepts only:

- `client_request_id`
- `run_mode`
- `operator_decision`
- `runtime_root_lifecycle_receipt_id`
- `baseline_run_id`
- `candidate_a_run_id`
- `candidate_b_run_id`
- `compare_target_set_hash`
- optional bounded `material_relative_name`

The server scans the configured Candidate B workflow receipt directory for exactly one matching proven source workflow receipt. It rejects missing, ambiguous, stale, raw-leaking, or mismatched authority before writing a run receipt. The written run receipt remains compatible with the existing read-only status endpoint and returns the exact status request payload needed for operator inspection.

## Verification

```text
python -m pytest .\backend\tests\test_layer3_candidate_b_full_corpus_operator_workflow_run.py .\backend\tests\test_layer3_candidate_b_full_corpus_operator_workflow_status.py .\backend\tests\test_layer3_readiness_contract.py .\backend\tests\test_layer3_bootstrap_contract.py -q
14 passed
```

Covered checks:

- run endpoint persists a durable server-owned workflow receipt;
- returned run receipt is compatible with the existing read-only status endpoint;
- idempotency is bound by `client_request_id` plus authority-basis hash;
- stale compare-target authority fails closed;
- raw local path exposure in source receipt authority fails closed;
- caller-submitted raw runtime roots are rejected;
- readiness/bootstrap expose the run endpoint without enabling rendered run-start/progress controls.

## Not Admitted Here

This runtime slice does not add a rendered start button, browser-owned durable authority, queue scheduling beyond contract-only state, cancel runtime behavior, broader Candidate B default scope, provider writes, connector dispatch, RAG/vector/model runtime, auth/security expansion, full mockup activation, or arbitrary source/runtime-root selection.
