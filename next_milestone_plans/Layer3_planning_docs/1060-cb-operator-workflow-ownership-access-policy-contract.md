# Candidate B Operator Workflow Ownership Access Policy Contract

```yaml
milestone: candidate_b_operator_workflow_ownership_access_policy_contract_v1
source_operator_workflow_ownership_access_policy_freeze: next_milestone_plans/Layer3_planning_docs/1059-cb-operator-workflow-ownership-access-policy-freeze.md
current_main_entry: ea8f4b56cacb559bbf43157d63ccb98bc8c7a18e
contract_status: frozen_no_runtime
runtime_status: not_implemented
selected_runtime_target: candidate_b_operator_workflow_ownership_access_policy_runtime_v1
implementation_admitted_after_current_main_sync: true
selected_auth_mode: session_tenant_owner_authorization
selected_policy_scope: candidate_b_full_corpus_operator_workflow_receipts_and_rendered_operator_controls
selected_named_security_behavior: candidate_b_operator_workflow_owner_scoped_access_decision_v1
policy_decision_schema_id: layer3.candidate_b.operator_workflow.owner_access_policy_decision.v1
policy_hash_basis: selected_auth_mode,protected_route_family,protected_rendered_surface,actor_ref_hash,tenant_or_workspace_ref_hash,workflow_receipt_hash,authority_basis_hash,storage_policy_hash,audit_contract_hash
identity_authority_contract: server_derived_operator_identity_ref_only
tenant_or_workspace_authority_contract: server_derived_tenant_or_workspace_ref_only
operator_role_contract: owner_can_mutate_own_workflow,auditor_can_read_projection_only
workflow_receipt_owner_binding_contract: actor_ref_hash,tenant_or_workspace_ref_hash,workflow_receipt_id,workflow_receipt_hash,authority_basis_hash,policy_hash
storage_root_access_contract: receipt_bound_storage_refs_only_no_client_supplied_paths_no_storage_root_escape
audit_event_contract: append_only_policy_decision_event
audit_event_required_fields: event_id,policy_schema_id,policy_hash,actor_ref_hash,tenant_or_workspace_ref_hash,workflow_receipt_id,workflow_receipt_hash,route_family,rendered_surface,decision,reason_code,request_id,created_at
audit_event_forbidden_fields: raw_operator_identity,raw_proxy_header,raw_tenant_id,raw_workspace_id,raw_local_path,raw_url,raw_token,provider_secret,connector_secret,artifact_bytes
request_admitted_fields: workflow_receipt_id,workflow_receipt_hash,actor_ref_hash,tenant_or_workspace_ref_hash,operator_role,route_family,rendered_surface,client_request_id,policy_hash
request_forbidden_fields: auth_policy_override,auth_security_directive,security_context,browser_identity,local_storage_identity,proxy_identity_header,raw_operator_identity,raw_tenant_id,raw_workspace_id,operator_role_override,permission_override,raw_storage_root,raw_receipt_path,raw_url,provider_secret,connector_secret
response_admitted_fields: policy_schema_id,policy_hash,decision,reason_code,workflow_receipt_id,workflow_receipt_hash,actor_ref_hash,tenant_or_workspace_ref_hash,route_family,rendered_surface,audit_event_id,next_actions
response_forbidden_fields: raw_operator_identity,raw_proxy_header,raw_tenant_id,raw_workspace_id,raw_local_path,raw_url,raw_token,provider_secret,connector_secret,artifact_bytes,permission_internals
owner_allowed_decisions: workflow_run,queue_scheduler_worker_progress_completion_retry,lifecycle_expiry,process_execution,completion_result_adoption,downstream_proof,repeatability_checkpoint,rerun_trial,acceptance_checkpoint,acceptance_closeout
auditor_allowed_decisions: workflow_history,workflow_status,completion_monitor,closeout_status,rendered_history,rendered_status,rendered_progress,rendered_review
cross_owner_receipt_access_policy: reject_fail_closed
missing_identity_policy: reject_fail_closed_for_nonlocal_runtime
missing_tenant_or_workspace_policy: reject_fail_closed_for_nonlocal_runtime
stale_policy_hash_policy: reject_fail_closed
browser_identity_policy: never_authority
local_storage_identity_policy: never_authority
untrusted_proxy_header_policy: reject_fail_closed
local_proof_harness_compatibility: AUTH_OWNER_none_single_operator_dev_profile_unchanged
nonlocal_runtime_prerequisite: AUTH_OWNER_proxy,TRUSTED_PROXY_MODE_true,explicit_trusted_header_contract,storage_exposure_auto_or_disabled
backwards_compatibility_policy: current_local_default_routes_remain_unchanged_until_runtime_contract_lands
rollback_fail_closed_behavior: disabling_policy_runtime_reverts_to_current_receipt_validated_workflow_without_owner_enforcement
negative_tests_required: rejects_missing_identity_authority,rejects_untrusted_proxy_identity,rejects_cross_owner_receipt,rejects_stale_policy_hash,rejects_browser_storage_identity,rejects_raw_path_url_token_response,rejects_storage_root_escape,rejects_provider_connector_secret_exposure,rejects_operator_role_override,rejects_permission_override
runtime_behavior_change_introduced_by_contract: false
route_api_dto_model_migration_service_behavior_change_introduced_by_contract: false
rendered_behavior_change_introduced_by_contract: false
auth_security_runtime_admitted_now: false
multi_user_runtime_admitted_now: false
storage_policy_runtime_admitted_now: false
audit_event_runtime_admitted_now: false
route_level_auth_dependency_admitted_now: false
model_migration_admitted_now: false
rendered_identity_control_admitted_now: false
provider_object_write_enabled: false
connector_dispatch_enabled: false
rag_vector_model_runtime_enabled: false
full_mockup_activation_enabled: false
default_scope_expansion_enabled: false
frontend_durable_authority_enabled: false
browser_storage_authority_enabled: false
baseline_rollback_preserved: true
candidate_a_semantics_preserved: true
candidate_b_default_scope_preserved: eligible_effective_pdfs_only
next_exact_posture: candidate_b_operator_workflow_ownership_access_policy_runtime_v1
```

## Purpose

This contract turns the 1059 ownership/access policy freeze into an exact future-runtime contract for Candidate B operator workflow receipts and rendered controls. It still introduces no runtime behavior. The next runtime slice may implement only this policy decision layer if current main still admits it after sync.

The contract protects the already-proven Candidate B workflow surfaces without changing their current local proof-harness behavior. Local `AUTH_OWNER=none` remains a single-operator development profile. Nonlocal enforcement remains blocked unless proxy-owned identity is explicitly configured, trusted proxy mode is enabled, storage exposure remains safe, and the runtime slice proves the negative tests named here.

## Contract Requirements

| Area | Contract |
| --- | --- |
| Identity authority | Use only server-derived operator identity refs. Browser state, local storage, request-provided identity, screenshots, and untrusted proxy headers are never authority. |
| Tenant/workspace authority | Use only server-derived tenant or workspace refs. Raw tenant/workspace identifiers must not be accepted or rendered. |
| Roles | `owner` may create/mutate own workflow receipts when runtime is admitted. `auditor` may read status, history, review, and audit projections only. |
| Receipt binding | Every policy decision binds actor hash, tenant/workspace hash, workflow receipt id/hash, authority basis hash, and policy hash. |
| Storage access | Storage access is by receipt-bound refs only. Client-supplied paths, raw receipt paths, raw URLs, and storage-root escapes fail closed. |
| Audit events | Runtime must append a redacted policy-decision event before returning an admitted decision. Audit failure must fail closed unless a later freeze explicitly changes that. |
| Responses | Responses may expose only response-safe hashes, ids, decision, reason code, audit event id, and next actions. Raw identity, proxy headers, tokens, paths, URLs, provider/connector secrets, artifact bytes, and permission internals are forbidden. |
| Rollback | Disabling policy runtime returns to the current receipt-validated Candidate B workflow behavior without owner enforcement. |

## Required Runtime Proof

The runtime slice must prove:

1. missing nonlocal identity rejects fail closed;
2. untrusted proxy identity rejects fail closed;
3. cross-owner workflow receipt access rejects fail closed;
4. stale policy hash rejects fail closed;
5. browser/local-storage identity is ignored as authority;
6. raw path, URL, token, provider secret, connector secret, and artifact bytes do not appear in responses, logs, rendered projections, or audit events;
7. storage-root escape attempts reject fail closed;
8. operator-role and permission override fields reject before service mutation;
9. audit event write failure rejects fail closed;
10. local default proof-harness behavior remains compatible until enforcement is explicitly enabled.

## Coherence Check

- Does this contract implement owner-scoped auth? Recommended answer: no. It defines the exact runtime contract and proof requirements.
- Does this contract require model or migration work? Recommended answer: not by itself. A future runtime may need a separately admitted durable audit-event implementation if existing receipt storage cannot support append-only policy events.
- Does this contract weaken local proof harness behavior? Recommended answer: no. `AUTH_OWNER=none` remains unchanged until a runtime contract lands.
- What comes next? Recommended answer: `candidate_b_operator_workflow_ownership_access_policy_runtime_v1`.
