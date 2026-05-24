# Candidate B Operator Workflow Production Auth Storage Hardening Selection

```yaml
milestone: candidate_b_operator_workflow_production_auth_storage_hardening_selection_v1
source_operator_workflow_rendered_identity_status_controls_runtime: next_milestone_plans/Layer3_planning_docs/1065-cb-operator-workflow-rendered-identity-status-controls-runtime.md
current_main_entry: 9214366ac68d9f7331f15b019d4dd379f72c4239
entry_decision: freeze_only
runtime_status: not_implemented
selected_next_runtime_target: candidate_b_operator_workflow_proxy_owner_storage_policy_runtime_v1
selected_hardening_scope: candidate_b_operator_workflow_proxy_owner_tenant_storage_audit_policy
selected_auth_owner_mode: AUTH_OWNER_proxy_with_TRUSTED_PROXY_MODE_true
selected_identity_authority: server_request_context_configured_proxy_identity_header_hash_only
selected_tenant_workspace_authority: server_request_context_configured_proxy_groups_header_hash_only
selected_role_matrix: owner_mutating_workflow_receipt_actions,auditor_read_only_status_history_review_audit_projection
selected_owner_binding_policy: workflow_receipt_owner_binding_required_for_AUTH_OWNER_proxy
selected_storage_access_policy: configured_workflow_receipt_root_only_receipt_bound_refs_only_no_client_supplied_paths
selected_audit_event_policy: append_only_redacted_policy_receipt_under_configured_workflow_root
selected_stale_authority_policy: reject_missing_identity_missing_tenant_untrusted_proxy_cross_owner_stale_policy_hash_forbidden_request_fields
selected_local_compatibility: AUTH_OWNER_none_single_operator_dev_profile_unchanged
implementation_admitted_after_current_main_sync: true
runtime_behavior_change_introduced_by_selection: false
api_service_behavior_change_introduced_by_selection: false
rendered_behavior_change_introduced_by_selection: false
auth_security_runtime_admitted_now: false
multi_user_runtime_admitted_now: false
storage_policy_runtime_admitted_now: false
audit_event_runtime_admitted_now: false
model_migration_admitted_now: false
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
required_runtime_proof: AUTH_OWNER_proxy_positive_owner_auditor_paths,missing_identity_fail_closed,missing_tenant_fail_closed,untrusted_proxy_fail_closed,cross_owner_fail_closed,stale_policy_hash_fail_closed,storage_root_escape_fail_closed,audit_redaction,AUTH_OWNER_none_compatibility
next_exact_posture: candidate_b_operator_workflow_proxy_owner_storage_policy_runtime_v1
```

This selection freezes the next production-hardening runtime boundary after rendered Candidate B ownership policy controls. The next implementation may harden only the existing Candidate B full-corpus operator workflow receipt, status, history, review, audit, and rendered control surfaces under proxy-owned server identity and configured receipt storage policy.

The runtime target must use server request context as the identity source, hash any configured proxy identity and tenant/workspace values before response or audit projection, bind workflow receipts to owner authority in `AUTH_OWNER=proxy`, and reject stale or cross-owner authority fail-closed. Storage access remains limited to the configured workflow receipt root and receipt-bound refs; clients still cannot supply raw storage roots, filesystem paths, URLs, provider refs, connector secrets, or browser/local-storage identity.

This selection does not add broad auth UI, user management, DB model or migration changes, provider object writes, connector dispatch, RAG/vector/model runtime, full mockup activation, broader Candidate B default scope, browser-storage authority, frontend durable authority, or arbitrary source/runtime expansion. The local single-operator proof harness remains valid under `AUTH_OWNER=none`.

## Coherence Check

- Why not broaden to a full auth system? Recommended answer: the current admitted surface is Candidate B workflow authority, not platform-wide authentication or user management.
- What is the exact next runtime? Recommended answer: `candidate_b_operator_workflow_proxy_owner_storage_policy_runtime_v1`.
- What has to fail closed? Recommended answer: missing identity, missing tenant/workspace, untrusted proxy mode, cross-owner receipts, stale policy hashes, forbidden request fields, and storage-root escape attempts.
- What remains after this selection? Recommended answer: implement and prove the proxy-owner/storage-policy runtime, then decide separately on broader eligible corpus scope, full mockup readiness, and semantic/RAG/model runtime only if current main admits those lanes.
