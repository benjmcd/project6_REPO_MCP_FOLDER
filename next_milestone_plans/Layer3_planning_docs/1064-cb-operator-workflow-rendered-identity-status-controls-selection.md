# Candidate B Operator Workflow Rendered Identity Status Controls Selection

```yaml
milestone: candidate_b_operator_workflow_rendered_identity_status_controls_selection_v1
source_operator_workflow_ownership_access_policy_projections: next_milestone_plans/Layer3_planning_docs/1063-cb-operator-workflow-ownership-access-policy-projections.md
current_main_entry: cd23835141aee3e984e7bb93900ded6024973a1c
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_operator_workflow_rendered_identity_status_controls_runtime_v1
selected_rendered_control_scope: candidate_b_operator_workflow_policy_status_identity_projection_controls
selected_rendered_surfaces: workflow_run,workflow_history,workflow_status,completion_monitor,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout,acceptance_closeout_status
selected_policy_response_projection: ownership_access_policy,policy_status,policy_hash,route_family,rendered_surface,audit_event_ref,actor_ref_hash,tenant_or_workspace_ref_hash
selected_request_role_projection: owner_for_mutating_workflow_receipt_actions,auditor_for_read_only_status_history_review_audit_projection
selected_closeout_status_request_change: add_operator_role_auditor_to_rendered_payload
selected_error_projection: missing_identity_authority,missing_tenant_or_workspace_authority,untrusted_proxy_identity,cross_owner_receipt,stale_policy_hash,forbidden_request_fields
selected_status_copy: server_derived_identity_only_browser_storage_never_authority
selected_headed_rendered_proof: required_before_runtime_closeout
selected_headless_rendered_proof: required_before_runtime_closeout
implementation_admitted_after_current_main_sync: true
runtime_behavior_change_introduced_by_selection: false
api_service_behavior_change_introduced_by_selection: false
rendered_behavior_change_introduced_by_selection: false
auth_security_runtime_admitted_now: false
multi_user_runtime_admitted_now: false
storage_policy_runtime_admitted_now: false
audit_event_runtime_admitted_now: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
raw_proxy_header_exposed: false
raw_operator_identity_exposed: false
raw_tenant_or_workspace_exposed: false
raw_local_path_exposed: false
raw_url_exposed: false
provider_or_connector_secret_exposed: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
next_exact_posture: candidate_b_operator_workflow_rendered_identity_status_controls_runtime_v1
```

This selection freezes the next rendered Candidate B operator workflow hardening slice. The selected runtime may only make the already-admitted ownership/access policy visible and operable through rendered status controls: redacted policy hashes, route families, rendered surfaces, audit event refs, actor/tenant hash refs, admitted role labels, and fail-closed error states. It may also add the explicit rendered `operator_role: auditor` request field for read-only closeout-status inspection.

This selection does not admit broad authentication UI, user management, browser/local-storage identity, proxy header display, raw operator identity display, model or migration changes, provider writes, connector dispatch, RAG/vector/model runtime, full mockup activation, broader Candidate B default scope, frontend durable authority, or any source/runtime expansion. Runtime implementation must prove headed and headless rendered behavior before claiming completion.

## Coherence Check

- Does this implement the rendered controls now? Recommended answer: no. It freezes the exact rendered-control runtime target and boundaries.
- Why is this next after policy projection coverage? Recommended answer: the server now emits redacted policy decisions and audit refs; operators need a governed rendered way to inspect those decisions without treating browser state as authority.
- Can the future UI display raw proxy headers or raw identity? Recommended answer: no. It may display only server-derived hashes, redacted refs, route families, rendered surfaces, and fail-closed status.
- What comes next? Recommended answer: `candidate_b_operator_workflow_rendered_identity_status_controls_runtime_v1`.
