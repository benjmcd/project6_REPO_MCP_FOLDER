# 988 - Candidate B Rendered Operator Workflow Status Proof

## Purpose

Prove that the existing Candidate B full-corpus operator workflow status control is a read-only rendered status projection, not merely an API/status endpoint.

The control was already present in the Layer 3 workbench. This checkpoint adds focused rendered proof that the browser can inspect a durable Candidate B full-corpus workflow receipt through the admitted status endpoint without rerunning corpus processing, mutating selectors, exposing raw paths/URLs, or creating frontend durable authority.

```yaml
milestone: candidate_b_read_only_operator_status_rendered_projection_gap_audit_v1
current_main: 9906745bdc5ff4b94146860588159481f1b8642c
selected_gap: rendered_full_corpus_operator_workflow_status_read_only_projection
selected_path: prove_existing_rendered_status_control
new_runtime_api_admitted: false
server_side_operator_workflow_run_api_admitted_now: false
rendered_run_start_control_admitted_now: false
rendered_status_control_id: candidate-b-full-corpus-workflow-status-form
rendered_status_mode: rendered_candidate_b_full_corpus_operator_workflow_status_control
status_endpoint: /api/v1/layer3/source/ingestion/candidate-b/full-corpus/operator-workflow/status
status_mode: candidate_b_full_corpus_operator_workflow_status_v1
operator_decision: inspect_candidate_b_full_corpus_operator_workflow_status
frontend_durable_authority_enabled: false
submitted_authority_fields_only: true
submitted_workflow_receipt_id: cb-full-corpus-operator-rendered-proof
submitted_bridge_receipt_id: cb-runtime-l3-rendered-proof
submitted_downstream_proof_id: cb-runtime-downstream-proof-rendered-proof
payload_raw_url_field_submitted: false
payload_local_path_field_submitted: false
payload_selector_mutation_field_submitted: false
rendered_workflow_status_visible: true
rendered_bridge_receipt_visible: true
rendered_downstream_proof_visible: true
rendered_artifact_family_projection_visible: true
rendered_visual_page_evidence_count_visible: true
rendered_raw_local_path_guardrail_visible: true
candidate_a_semantics_changed: false
baseline_default_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
provider_object_writes_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
headed_chrome_required_for_rendered_behavior_change: true
headless_chrome_required_for_rendered_behavior_change: true
focused_e2e_test: e2e/layer3-workbench.spec.js::Layer 3 workbench inspects Candidate B full-corpus workflow status through rendered read-only control
next_exact_posture: candidate_b_operator_repeatability_completion_audit_v1
```

## Evidence

The rendered control uses `data-rendered-mode="rendered_candidate_b_full_corpus_operator_workflow_status_control"` and `data-frontend-durable-authority="false"`.

The focused Playwright proof routes only the admitted full-corpus operator workflow status endpoint, submits receipt/run/proof identifiers, and verifies the panel renders:

- workflow receipt/status/hash;
- baseline, Candidate A, and Candidate B run binding;
- runtime bridge receipt and downstream proof id;
- corpus and Layer 3 status;
- retained artifact-family hash and visual page evidence count;
- validate-only triplet and no-seeding guardrails;
- raw local path, raw URL, and selector mutation guardrails.

## Boundaries

This proof does not add a server-side workflow-run API, run-start UI, corpus-processing trigger, browser-storage authority, provider write, connector dispatch, RAG/vector/model runtime, broader Candidate B default scope, or full mockup activation.
