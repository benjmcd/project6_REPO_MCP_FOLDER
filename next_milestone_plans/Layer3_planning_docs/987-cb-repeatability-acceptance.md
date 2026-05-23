# 987 - Candidate B Repeatability Acceptance And UI Status Decision

## Purpose

Accept the current Candidate B full-corpus operator workflow as repeatable for a configured live server, and decide the next UI/status direction after the live HTTP proof.

Current main now has a proven `live-http` operator runner, durable workflow receipt/status inspection, runtime-root lifecycle binding, Layer 3 bridge/downstream proof, internal webhook dispatch, provider-private redacted lifecycle, same-origin delivery, artifact-family status, eligibility counts, and baseline rollback projection. That is enough to treat the runner plus status endpoint as the current operator-repeatability surface for prepared eligible-PDF corpus runs.

It is not enough to silently admit a server-side workflow-run API, a rendered run-start control, multi-user scheduling, auth/security expansion, broader corpus defaulting, or full mockup activation.

```yaml
milestone: candidate_b_operator_repeatability_acceptance_and_ui_status_decision_v1
current_main: 8b70d2f83bfc9540b9491e34c93c7fc73f650d1d
acceptance_basis_checkpoint: next_milestone_plans/Layer3_planning_docs/986-cb-live-http-runtime-proof.md
accepted_operator_execution_surface: live_http_operator_runner_plus_status_endpoint
accepted_for_scope: prepared_full_corpus_eligible_pdf_operator_runs_on_configured_live_server
server_side_operator_workflow_run_api_admitted_now: false
rendered_run_start_control_admitted_now: false
rendered_read_only_status_projection_admitted_now: false
next_rendered_status_step: candidate_b_read_only_operator_status_rendered_projection_gap_audit_v1
workflow_receipt_id: cb-full-corpus-operator-3d717f0edcbeaba69179af15
workflow_receipt_hash: 3d717f0edcbeaba69179af1582a90abf2ce087c5d35400afdb62fe7534b3266c
workflow_status_hash: d38f89a59ffe13f25c4f134e633530cd1572eefb31d28aa24241cef7c70d9b0e
bridge_receipt_id: cb-runtime-l3-0110fe894c68d6a0291f9979
downstream_proof_id: cb-runtime-downstream-proof-ee7d48afbe62ffc011fac4d3
runtime_root_lifecycle_receipt_id: cb-full-corpus-runtime-roots-ab3c4fd0b54ca670ada781f9
live_http_layer3_api_used: true
testclient_dependency_used: false
in_memory_db_used: false
durable_database_used: true
configured_internal_webhook_used: true
status_endpoint_verified: true
status_endpoint_status: available
workflow_status: proven
eligible_pdf_count: 69
skipped_pdf_count: 0
failed_pdf_count: 0
source_directory_eligible_file_count: 71
coverage_count: 17
baseline_rollback_available: true
baseline_default_changed: false
candidate_a_visual_lane_preserved: true
candidate_a_semantics_changed: false
candidate_b_default_broadened_beyond_eligible_pdf: false
selector_mutation_performed: false
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
validate_only_triplet: true
artifacts_seeded_or_generated_by_triplet_validator: false
```

## Decision

The accepted current operator path is:

```text
operator supplies prepared baseline/Candidate A/Candidate B runtime roots + durable live server config -> live-http runner calls admitted Layer 3 APIs -> durable workflow receipt is written -> operator inspects receipt through Candidate B full-corpus operator workflow status endpoint
```

No new server-side orchestration API is admitted in this decision. The `server_side_operator_workflow_run_api` remains deferred until there is a concrete need that the runner/status model cannot satisfy, such as server-owned scheduling, multi-user run ownership, durable queued execution, or a rendered operator start workflow with clear product authority.

No rendered run-start control is admitted in this decision. Starting a Candidate B full-corpus workflow remains a governed operator-runner action, not a browser-storage or frontend-only durable authority.

The next UI/status step, if selected, should be read-only: audit whether existing rendered/operator surfaces can show Candidate B workflow status, receipts, eligibility, rollback, artifact-family visibility, and blocked reasons without raw path, raw URL, artifact bytes, or restart authority. Any rendered behavior change must get headed and headless proof.

## Fail-Closed Requirements

The accepted repeatability surface remains valid only while these fail-closed checks hold:

- live mode requires `--api-base-url` and `--internal-webhook-mode configured`;
- live readiness must admit Candidate B runtime bridge, bridge source scan, downstream proof, and full-corpus operator workflow status endpoints;
- selected baseline, Candidate A, and Candidate B runtime roots must validate as one compare triplet;
- the status endpoint must reject stale, mismatched, missing, or incomplete workflow receipts;
- baseline rollback must remain explicit and independent of Candidate B artifacts;
- Candidate A visual-lane semantics must remain unchanged;
- Candidate B default scope must remain eligible/effective PDFs only;
- receipts and rendered/status surfaces must not expose raw local paths, raw URLs, provider keys, artifact bytes, or frontend-only durable authority.

## Next Exact Posture

```text
candidate_b_read_only_operator_status_rendered_projection_gap_audit_v1
```
