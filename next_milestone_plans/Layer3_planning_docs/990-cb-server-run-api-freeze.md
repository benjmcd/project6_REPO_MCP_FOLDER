# 990 - Candidate B Server-Owned Workflow Run API Freeze

## Purpose

Select the first post-repeatability expansion slice after Candidate B operator-repeatability completion: a server-owned workflow-run API authority for prepared full-corpus eligible-PDF Candidate B runs.

Current main proves Candidate B repeatability through the live HTTP operator runner, durable workflow receipts, the server-revalidated status endpoint, and rendered read-only status control. It still does not admit server-side run/start authority. This freeze selects that exact next slice and defines the implementation boundary before any runtime API or rendered run-start control is added.

```yaml
milestone: candidate_b_server_owned_workflow_run_api_authority_freeze_v1
current_main: c6c0c481794098b984792bbc49ae84a63a9b2a4e
source_posture_checkpoint: next_milestone_plans/Layer3_planning_docs/989-cb-repeatability-completion-audit.md
previous_next_exact_posture: candidate_b_post_repeatability_operator_workflow_expansion_selection_v1
selected_next_slice: candidate_b_server_owned_workflow_run_api_authority_v1
entry_decision: freeze_only
runtime_status: not_implemented
implementation_admitted_after_current_main_sync: true
selected_runtime_target: candidate_b_server_owned_workflow_run_api_runtime_v1
selected_route_family: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow
selected_run_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
existing_status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
run_mode: candidate_b_full_corpus_operator_workflow_run_v1
operator_decision: start_candidate_b_full_corpus_operator_workflow
accepted_scope: prepared_full_corpus_eligible_pdf_operator_runs_on_configured_live_server
source_authority_model: server_owned_runtime_root_lifecycle_receipt_plus_compare_target_set
client_supplied_raw_runtime_roots_admitted: false
browser_supplied_runtime_roots_admitted: false
server_resolves_runtime_roots_from_receipt_authority: true
workflow_receipt_binding_required: true
runtime_root_lifecycle_receipt_required: true
baseline_run_id_required: true
candidate_a_run_id_required: true
candidate_b_run_id_required: true
compare_target_set_hash_required: true
idempotency_key_required: true
idempotency_basis: client_request_id_plus_authority_basis_hash
state_machine_required: true
required_states: accepted,running,proven,blocked,cancelled,expired
cancel_endpoint_admitted_now: contract_only
queue_scheduler_admitted_now: contract_only
rendered_run_start_control_admitted_now: false
rendered_progress_control_admitted_now: false
rendered_status_control_remains_read_only: true
status_endpoint_must_revalidate_server_receipts: true
baseline_rollback_required: true
baseline_default_changed: false
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
selector_mutation_allowed: false
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
next_exact_posture: candidate_b_server_owned_workflow_run_api_runtime_v1
```

## Selected Contract

The next runtime slice should add a server-owned run endpoint under the existing Candidate B full-corpus operator workflow route family:

```text
POST /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/run
```

The endpoint should accept only server-authority identifiers and operator intent:

- `client_request_id`
- `run_mode: candidate_b_full_corpus_operator_workflow_run_v1`
- `operator_decision: start_candidate_b_full_corpus_operator_workflow`
- `runtime_root_lifecycle_receipt_id`
- `baseline_run_id`
- `candidate_a_run_id`
- `candidate_b_run_id`
- `compare_target_set_hash`
- optional `material_relative_name` when it is bounded to the already admitted material subset

The endpoint must not accept local filesystem paths, raw URLs, provider object refs, provider credentials, artifact bytes, selector mutation fields, document-processing default mutation fields, connector destinations, model/RAG/vector controls, browser-storage authority, or full mockup activation flags.

## Required Behavior

The runtime implementation must:

1. Revalidate the runtime-root lifecycle receipt and compare target set before creating or resuming a run.
2. Bind every run to baseline, Candidate A, Candidate B, runtime-root lifecycle, compare target set, and authority-basis hash.
3. Enforce idempotency by `client_request_id` plus authority-basis hash.
4. Produce durable server-owned workflow receipts compatible with the existing status endpoint.
5. Report a bounded state machine: `accepted`, `running`, `proven`, `blocked`, `cancelled`, or `expired`.
6. Fail closed for missing, stale, mismatched, incomplete, or raw-leaking authority.
7. Preserve baseline rollback and Candidate A semantics.
8. Keep Candidate B default scope limited to eligible/effective PDFs.
9. Preserve the existing rendered status control as read-only until a later rendered run-start slice is selected.
10. Avoid provider writes, connector dispatch, RAG/vector/model runtime, auth/security expansion, broader corpus defaulting, and full mockup activation.

## Deferred From This Slice

This freeze does not admit:

- a rendered run-start control;
- browser-owned workflow authority;
- arbitrary source expansion or arbitrary runtime-root selection;
- queue scheduling beyond the explicit contract requirements;
- multi-user/auth/security expansion;
- provider object writes or provider-public URLs;
- connector dispatch;
- RAG/vector/model runtime;
- broader corpus default behavior;
- full mockup activation.

## Grill-Me Coherence Check

1. Why not build rendered start UI first?
   Recommended answer: rendered start UI before server-run authority would create a frontend-authority shortcut. The server-owned API has to exist first.

2. Why not let the browser submit runtime root paths?
   Recommended answer: current evidence is deliberately redacted and receipt-bound. Browser-supplied paths would reopen raw local path authority and weaken the status endpoint's stale-authority checks.

3. Is this selecting broader Candidate B default scope?
   Recommended answer: no. The scope remains prepared full-corpus eligible-PDF runs on a configured live server.

4. Is this a runtime implementation?
   Recommended answer: no. It is the authority freeze that admits the next runtime slice after current-main sync.

## Next Exact Posture

```text
candidate_b_server_owned_workflow_run_api_runtime_v1
```
