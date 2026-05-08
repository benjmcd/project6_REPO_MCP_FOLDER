# Provider/Public URL Entry Freeze

Status: planning/control entry freeze only for `provider_public_url_entry_freeze`.

This document is a post-PR #748 entry-decision delta over docs `110_PROVIDER_URL_FREEZE.md`, `111_PROVIDER_URL_CONTRACT.md`, `184_POST_745_DOWNSTREAM_EXPANSION_FREEZE.md`, and `185_POST_745_DOWNSTREAM_EXPANSION_CONTRACT.md`. It does not replace those docs and does not implement provider URLs, public URLs, provider object writes, provider object copies, provider ACL changes, connector dispatch, destination writes, package mutation, source expansion, RAG/vector retrieval, full mockup activation, hidden LLM planning, auth/security behavior, route, DTO, model, migration, service behavior, tests, or rendered UI controls.

The external V6 assurance pack at `C:\Users\benny\Downloads\layer3_provider_public_url_entry_freeze_v6_final_assurance_pack.md` was used only as reference context. Live source, tests, progress manifests, proof manifests, and `tools/l3-progress-check.py` remain authority.

## Decision

The selected entry decision is:

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
reason: provider_storage_authority_named_use_case_exposure_model_revocation_contract_and_security_posture_not_yet_verified
next_follow_up: provider_public_url_authority_discovery_freeze_or_entry_freeze_update
```

No provider/public URL runtime is admitted by this pass.

The only future candidate modes remain:

- `provider_private_signed_url`;
- `provider_public_url`;
- `public_proxy_url`.

A later runtime implementation-entry freeze must choose exactly one mode before code. The current evidence does not justify selecting any mode now. In particular, `provider_public_url` and `public_proxy_url` remain deferred by default because they carry stronger public exposure, caching, indexing, proxy, and security implications.

## Evidence Ledger

```yaml
evidence_ledger:
  current_same_origin_signed_reference_proof:
    status: verified
    evidence:
      - e2e/layer3-workbench.spec.js
      - next_milestone_plans/Layer3_planning_docs/181_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_FREEZE.md
      - next_milestone_plans/Layer3_planning_docs/182_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_CONTRACT.md
      - next_milestone_plans/Layer3_planning_docs/183_RENDERED_EXTERNAL_EXPORT_DOWNLOAD_SIGNED_REFERENCE_PROOF.md
      - next_milestone_plans/Layer3_planning_docs/184_POST_745_DOWNSTREAM_EXPANSION_FREEZE.md
      - next_milestone_plans/Layer3_planning_docs/185_POST_745_DOWNSTREAM_EXPANSION_CONTRACT.md
  provider_storage_authority:
    status: unverified
    evidence: []
  named_use_case:
    status: unverified
    evidence: []
  exposure_classification:
    status: unverified
    evidence: []
  revocation_contract:
    status: unverified
    evidence: []
```

Because `provider_storage_authority`, `named_use_case`, `exposure_classification`, and `revocation_contract` are unverified, the entry decision is deferred.

## Threat Model Minimum

| Risk | Freeze status |
| --- | --- |
| bearer URL leakage through copy, logs, browser history, cache, or referrer | deferred until exposure model is defined |
| cross-session or wrong-package access | blocked by required authority binding |
| stale authority reuse after package, handoff, export, readiness, or artifact state changes | blocked by stale-authority tests required before runtime |
| provider object key, bucket, container, local path, or credential leakage | blocked by response and log redaction requirements |
| public indexing or cache persistence | deferred for `provider_public_url` and `public_proxy_url` modes |
| replay after revocation or expiry | blocked by TTL and revocation contract required before runtime |

## Exposure Model

```yaml
exposure_model:
  audience: unknown
  artifact_sensitivity: unknown
  url_bearer_risk: unknown
  revocation_model: unknown
  auth_dependency: unknown
```

Deferral rules:

- if `artifact_sensitivity` is `unknown`, entry remains deferred;
- if `audience` is `public_anonymous`, entry remains deferred unless a later auth/security public-exposure freeze exists;
- if `revocation_model` is `unknown`, implementation remains blocked;
- if `auth_dependency` is `new_auth_required` or `unknown`, implementation remains blocked unless a later auth/security entry freeze exists.

## Capability Isolation Matrix

```yaml
capability_isolation_matrix:
  same_origin_attachment_delivery:
    relationship: prerequisite_or_parallel_mode
    change_allowed_in_this_pass: false
  same_origin_signed_reference_delivery:
    relationship: prerequisite_or_parallel_mode
    change_allowed_in_this_pass: false
  provider_private_signed_url:
    relationship: candidate_mode
    runtime_allowed_in_this_pass: false
  provider_public_url:
    relationship: candidate_mode_but_deferred_by_default
    runtime_allowed_in_this_pass: false
  public_proxy_url:
    relationship: candidate_mode_but_deferred_by_default
    runtime_allowed_in_this_pass: false
  provider_object_write_or_copy:
    relationship: later_freeze_required
    runtime_allowed_in_this_pass: false
  connector_destination_dispatch:
    relationship: later_freeze_required
    runtime_allowed_in_this_pass: false
  package_mutation_reconstruction:
    relationship: later_freeze_required
    runtime_allowed_in_this_pass: false
  source_breadth_expansion:
    relationship: later_freeze_required
    runtime_allowed_in_this_pass: false
  rag_vector_or_hybrid_execution:
    relationship: later_freeze_required
    runtime_allowed_in_this_pass: false
  auth_security_behavior_change:
    relationship: prerequisite_for_some_modes_but_later_freeze_required
    runtime_allowed_in_this_pass: false
```

## Cross-Mode Privilege Escalation Guard

Provider/public URL work must not upgrade, extend, revive, or bypass same-origin attachment delivery, same-origin signed-reference delivery, package review, handoff/export prepare, APS handoff dispatch, external export/download readiness, or artifact hash/size authority.

```yaml
no_cross_mode_privilege_escalation:
  signed_reference_to_provider_url_upgrade_allowed: false
  expired_signed_reference_can_create_provider_url: false
  failed_same_origin_delivery_can_create_provider_url: false
  stale_package_review_can_create_provider_url: false
  stale_artifact_hash_can_create_provider_url: false
  provider_url_can_enable_connector_dispatch: false
```

## Runtime Non-Admission

```yaml
runtime_admission:
  provider_public_url_runtime: false
  provider_private_signed_url_runtime: false
  public_proxy_url_runtime: false
  provider_object_write_or_copy: false
  provider_object_acl_change: false
  connector_destination_dispatch: false
  package_mutation_reconstruction: false
  source_expansion: false
  rag_vector_retrieval: false
  auth_security_behavior_change: false
  rendered_ui_control_change: false
```

## Provider Object Boundary

Provider/public URL admission, if later selected, is a URL exposure mode over already-authorized server-owned artifacts; it is not provider object write, object copy, object mutation, object ACL change, or object lifecycle management.

If future implementation needs to write, copy, mutate, publish, or revoke provider objects directly, it must first create a separate provider object materialization freeze and contract.

## Signed-Reference Compatibility

Provider/public URL work must preserve same-origin signed-reference generation, single-use semantics, replay denial, signed-reference secret requirements, and rendered proof behavior unless a later freeze explicitly admits a replacement.

```yaml
signed_reference_relationship: parallel_delivery_mode
signed_reference_semantics_change_allowed: false
```

## Connector, Package, Source, RAG, Mockup, And Auth Isolation

Provider/public URL generation does not select a connector, invoke a connector, create a connector run, write a destination, or create a generic downstream dispatch record.

Provider/public URL work may only expose an already-authorized artifact. It must not change package payloads, reconstruct packages, supersede packages, rewrite manifests, or invalidate receipts unless a later package mutation freeze admits that behavior.

This freeze does not admit source-family expansion, local upload, local-directory ingestion, arbitrary local path input, web connector retrieval, RAG/vector retrieval, broad qualitative execution, hybrid execution, hidden LLM planning, full mockup activation, auth/security behavior change, or frontend-only durable authority.

## Configuration And Secret Posture

```yaml
provider_config_posture:
  provider_credentials_in_browser: forbidden
  provider_credentials_in_request_payload: forbidden
  provider_object_namespace_from_client: forbidden_unless_later_freeze_admits_safe_alias
  default_provider_config_in_tests_as_runtime_authority: forbidden
  missing_provider_config_behavior: fail_closed
  test_secret_leak_to_production_config: forbidden
  config_name_redaction_in_error_bodies: required_if_sensitive
  provider_url_token_redaction_in_logs: required
```

## Browser Network Posture For Later Runtime

```yaml
browser_network_posture_required_for_runtime:
  cache_control: required
  referrer_policy: required_if_url_can_leave_origin
  content_disposition: required_for_download_artifacts
  cors_policy: required_if_proxy_or_cross_origin_mode_selected
  csp_impact_review: required_if_rendered_controls_added
  url_display_redaction: required_if_sensitive
runtime_header_behavior_admitted: false
```

## Artifact And Receipt Family

```yaml
artifact_family: null
receipt_family: no_receipt_planning_only
```

Blocked receipt families without later freezes:

- `provider_object_receipt`;
- `connector_dispatch_receipt`;
- `destination_write_receipt`;
- `package_mutation_receipt`;
- `public_access_receipt_if_auth_security_not_frozen`;
- `proxy_access_receipt`.

A later runtime freeze must distinguish server-internal audit records, operator-visible receipts, and external provider or connector receipts.

## Time, TTL, Expiry, And Revocation

```yaml
time_authority:
  server_clock_authoritative: required
  client_clock_authority: forbidden
  clock_skew_policy: required_for_runtime
  ttl_unit: required_for_runtime
  max_ttl: required_for_runtime
  expiry_error_code: required_for_runtime
  revocation_error_code: required_if_active_revocation_admitted
revocation_contract:
  active_revocation_supported: unknown
  ttl_only_if_no_active_revocation: true
  replay_semantics: not_applicable_planning_only
  reissue_policy: not_selected
```

Implementation remains blocked while active revocation, TTL, expiry, replay, and reissue behavior are unknown.

## Stale-Authority Failure List

Future runtime freeze must require fail-closed behavior for stale:

- `stale_session`;
- `stale_analysis_plan`;
- `stale_pass_run`;
- `stale_result_review`;
- `stale_package_review`;
- `stale_package_construction`;
- `stale_package_submit`;
- `stale_handoff_export_prepare`;
- `stale_aps_handoff_dispatch`;
- `stale_external_export_download_prepare`;
- `stale_artifact_ref`;
- `stale_artifact_hash`;
- `stale_artifact_size`;
- `stale_signed_reference_authority_if_used`.

## Leak-Control Checklist

```yaml
leak_control_checklist:
  app_logs: must_not_log_full_url_or_token
  browser_history: considered
  referrer_headers: considered
  error_bodies: must_not_include_full_url_or_token
  audit_records: redacted_or_hash_only_unless_later_admitted
  provider_logs: considered_if_provider_mode_selected
  screenshots_and_traces: considered_for_playwright
  copied_url_ui: rendered_only_if_later_admitted
leak_controls_runtime_implemented: false
```

## Test Architecture Boundary

```yaml
test_architecture_boundary:
  real_provider_credentials_in_ci: forbidden_by_default
  fake_provider_adapter_or_contract_double: required_if_runtime_admitted
  provider_error_simulation: required_if_runtime_admitted
  missing_config_test: required_if_runtime_admitted
  stale_authority_test: required_if_runtime_admitted
  no_url_leakage_test: required_if_runtime_admitted
  headed_and_headless_rendered_proof: required_if_rendered_controls_admitted
```

## Dependency Graph

```text
post_748_checkpoint
  -> provider_public_url_entry_freeze
    -> provider_public_url_authority_discovery, if needed
      -> provider_public_url_runtime_freeze
        -> provider_public_url_runtime_implementation, if admitted
```

Provider/public URL work remains independent from connector/destination dispatch, package mutation/reconstruction, source breadth expansion, qualitative/hybrid/RAG/vector expansion, browser/full mockup activation, and auth/security hardening. Auth/security may block runtime provider/public URL implementation, but this freeze does not change auth/security behavior.

## Negative Invariants

- no provider/public URL runtime;
- no provider private signed URL runtime;
- no public proxy URL runtime;
- no provider object ACL change;
- no provider object write or copy;
- no connector or destination dispatch;
- no generic downstream dispatch;
- no package mutation or reconstruction;
- no package payload rewrite;
- no source expansion;
- no local upload;
- no local-directory ingestion;
- no arbitrary local path input;
- no web connector retrieval;
- no RAG/vector retrieval;
- no broad qualitative execution;
- no hybrid execution;
- no full mockup activation;
- no hidden LLM planning;
- no frontend-only durable state;
- no auth/security behavior change;
- no existing same-origin signed-reference semantics change;
- no provider credentials in browser or request;
- no provider URL or token leakage in error bodies;
- no provider URL or token leakage in logs;
- no cross-mode privilege escalation;
- no new route, DTO, model, migration, production service behavior, test behavior, or rendered UI control.

## Stop Condition

Stop before runtime implementation if any proposed change needs provider/storage authority, a named use case, artifact-family selection, exposure classification, TTL/revocation/audit behavior, access authority, leak controls, stale-authority tests, fake-provider architecture, or auth/security posture that this entry freeze has not verified.
