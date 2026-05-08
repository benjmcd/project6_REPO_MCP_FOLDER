# Connector/Destination Dispatch Entry Freeze

Status: planning/control entry freeze only for `connector_destination_dispatch_entry_freeze`.

This document is a post-PR #749 entry-decision delta over docs `112_CONNECTOR_DISPATCH_FREEZE.md`, `113_CONNECTOR_DISPATCH_CONTRACT.md`, `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md`, `184_POST_745_DOWNSTREAM_EXPANSION_FREEZE.md`, `185_POST_745_DOWNSTREAM_EXPANSION_CONTRACT.md`, `187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md`, and `188_PROVIDER_PUBLIC_URL_ENTRY_CONTRACT.md`. It does not replace those docs and does not implement external connector invocation, destination writes, generic downstream dispatch, connector-run creation, provider/public URLs, provider object writes, provider object copies, provider ACL changes, package mutation, source expansion, RAG/vector retrieval, full mockup activation, hidden LLM planning, auth/security behavior, route, DTO, model, migration, production service behavior, test behavior, or rendered UI controls.

## Decision

The selected entry decision is:

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
live_internal_record_only_status: already_admitted_by_doc_121
reason: external_connector_destination_authority_named_use_case_destination_access_lifecycle_retry_receipt_and_security_posture_not_yet_verified
next_follow_up: connector_destination_authority_discovery_freeze_or_entry_freeze_update
```

This pass admits no new connector/destination runtime. The already-live `internal_dispatch_record_only` path remains governed by `121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md`, `/api/v1/layer3/handoff/connector/record`, and `backend/app/services/layer3_connector_dispatch_entry.py`. That existing internal record-only behavior is not expanded here.

The only future external dispatch candidate modes remain:

- `single_named_connector_dispatch`;
- `single_named_destination_dispatch`;
- `internal_dispatch_record_only_extension` only if a later freeze proves the existing record-only behavior needs a bounded receipt/audit extension without external invocation.

A later runtime implementation-entry freeze must choose exactly one mode before code. The current evidence does not justify selecting any external connector or destination mode now.

## Evidence Ledger

```yaml
evidence_ledger:
  current_internal_dispatch_record_only:
    status: verified
    evidence:
      - next_milestone_plans/Layer3_planning_docs/121_CONNECTOR_DISPATCH_ENTRY_FREEZE.md
      - backend/app/services/layer3_connector_dispatch_entry.py
      - backend/app/api/layer3.py
      - backend/tests/test_layer3_api.py
      - tools/l3-progress-check.py
  current_provider_public_url_entry_freeze:
    status: verified
    evidence:
      - next_milestone_plans/Layer3_planning_docs/187_PROVIDER_PUBLIC_URL_ENTRY_FREEZE.md
      - next_milestone_plans/Layer3_planning_docs/188_PROVIDER_PUBLIC_URL_ENTRY_CONTRACT.md
  external_connector_authority:
    status: unverified
    evidence: []
  destination_authority:
    status: unverified
    evidence: []
  named_downstream_use_case:
    status: unverified
    evidence: []
  credential_and_access_model:
    status: unverified
    evidence: []
  lifecycle_retry_cancel_contract:
    status: unverified
    evidence: []
  receipt_and_audit_contract:
    status: unverified
    evidence: []
```

Because external connector authority, destination authority, named downstream use case, credential/access model, lifecycle semantics, and receipt/audit contract are unverified, the entry decision is deferred.

## Current Live Boundary

Current main has one bounded connector-adjacent runtime: `internal_dispatch_record_only`. It records an operator-approved internal dispatch intent in existing Layer 3 control-plane state. It does not invoke an external connector, write to a destination, create a connector-run row, generate a provider/public URL, mutate package bytes, widen source classes, activate rendered controls, or change auth/security behavior.

Current main also has same-origin attachment delivery, same-origin signed-reference generation/use, durable signed-reference state, rendered signed-reference proof, and a deferred provider/public URL entry freeze. None of those surfaces make external connector/destination dispatch live.

## Threat Model Minimum

| Risk | Freeze status |
| --- | --- |
| connector credential leakage | blocked by credential/access model required before runtime |
| destination secret or target leakage | blocked by response/log redaction requirements |
| wrong connector or destination selection | blocked by server allowlist and authority binding required |
| cross-session or wrong-package dispatch | blocked by exact authority binding required |
| stale artifact, package, handoff, APS, export, delivery, or signed-reference authority | blocked by stale-authority tests required before runtime |
| duplicate dispatch, replay, retry, cancel, or timeout ambiguity | blocked by lifecycle and idempotency contract required before runtime |
| provider/public URL side-channel dispatch | blocked by provider URL non-admission and cross-mode isolation |
| external side effects in CI | blocked by fake connector/destination adapter required by default |

## Dispatch Exposure Model

```yaml
dispatch_exposure_model:
  connector_family: unknown
  destination_family: unknown
  destination_audience: unknown
  artifact_sensitivity: unknown
  credential_authority: unknown
  operator_authorization_model: unknown
  retry_cancel_policy: unknown
  receipt_visibility: unknown
```

Deferral rules:

- if `connector_family` and `destination_family` are both `unknown`, entry remains deferred;
- if `artifact_sensitivity` is `unknown`, runtime implementation remains blocked;
- if `credential_authority` is `unknown`, runtime implementation remains blocked;
- if `operator_authorization_model` is `unknown`, runtime implementation remains blocked unless a later auth/security freeze exists;
- if `retry_cancel_policy` is `unknown`, runtime implementation must not admit retry, cancel, queue, or recovery behavior.

## Capability Isolation Matrix

```yaml
capability_isolation_matrix:
  internal_dispatch_record_only:
    relationship: existing_bounded_runtime_from_doc_121
    change_allowed_in_this_pass: false
  single_named_connector_dispatch:
    relationship: candidate_mode_but_deferred
    runtime_allowed_in_this_pass: false
  single_named_destination_dispatch:
    relationship: candidate_mode_but_deferred
    runtime_allowed_in_this_pass: false
  generic_downstream_dispatch:
    relationship: not_candidate_for_first_external_dispatch_lane
    runtime_allowed_in_this_pass: false
  provider_public_url:
    relationship: separate_deferred_entry_freeze
    runtime_allowed_in_this_pass: false
  provider_object_write_or_copy:
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
  rendered_connector_destination_controls:
    relationship: later_rendered_freeze_required
    runtime_allowed_in_this_pass: false
```

## Cross-Mode Privilege Escalation Guard

Connector/destination work must not upgrade, extend, revive, or bypass same-origin attachment delivery, same-origin signed-reference delivery, provider/public URL governance, package review, handoff/export prepare, APS handoff dispatch, external export/download readiness, or artifact hash/size authority.

```yaml
no_cross_mode_privilege_escalation:
  internal_record_can_invoke_external_connector: false
  internal_record_can_write_destination: false
  provider_url_can_enable_connector_dispatch: false
  expired_signed_reference_can_dispatch: false
  failed_same_origin_delivery_can_dispatch: false
  stale_package_review_can_dispatch: false
  stale_artifact_hash_can_dispatch: false
  connector_dispatch_can_mutate_package: false
  connector_dispatch_can_expand_source: false
```

## Runtime Non-Admission

```yaml
runtime_admission:
  new_connector_destination_runtime: false
  external_connector_invocation: false
  destination_write: false
  connector_run_creation: false
  generic_downstream_dispatch: false
  provider_public_url_runtime: false
  provider_object_write_or_copy: false
  provider_object_acl_change: false
  package_mutation_reconstruction: false
  source_expansion: false
  rag_vector_retrieval: false
  auth_security_behavior_change: false
  rendered_ui_control_change: false
```

## Connector And Destination Boundary

Connector/destination dispatch, if later selected, is a downstream side-effect mode over already-authorized server-owned artifacts. It is not provider URL generation, provider object materialization, package mutation, source ingestion, RAG/vector execution, hidden LLM planning, auth/security hardening, or full mockup activation.

The first external lane must not be generic dispatch. It must choose exactly one named connector or destination family and one artifact family.

## Configuration And Secret Posture

```yaml
connector_destination_config_posture:
  connector_credentials_in_browser: forbidden
  destination_credentials_in_browser: forbidden
  connector_credentials_in_request_payload: forbidden
  destination_credentials_in_request_payload: forbidden
  connector_key_from_client: forbidden_unless_later_freeze_admits_server_allowlisted_alias
  destination_id_from_client: forbidden_unless_later_freeze_admits_server_allowlisted_alias
  default_fake_config_as_runtime_authority: forbidden
  missing_connector_or_destination_config_behavior: fail_closed
  secret_leak_to_production_config: forbidden
  config_name_redaction_in_error_bodies: required_if_sensitive
  connector_destination_token_redaction_in_logs: required
```

## Artifact And Receipt Family

```yaml
artifact_family: null
receipt_family: no_receipt_planning_only
```

Blocked receipt families without later freezes:

- `external_connector_receipt`;
- `destination_write_receipt`;
- `provider_object_receipt`;
- `provider_public_url_receipt`;
- `package_mutation_receipt`;
- `public_access_receipt_if_auth_security_not_frozen`.

A later runtime freeze must distinguish server-internal audit records, operator-visible receipts, connector receipts, destination receipts, and provider receipts.

## Lifecycle, Retry, Cancel, Timeout, And Idempotency

```yaml
lifecycle_contract:
  lifecycle_selected: false
  retry_supported: unknown
  cancel_supported: unknown
  timeout_policy: unknown
  idempotency_key_policy: required_for_runtime
  terminal_states_required: true
  duplicate_dispatch_policy: required_for_runtime
```

Implementation remains blocked while lifecycle, retry, cancel, timeout, and duplicate-dispatch behavior are unknown.

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
- `stale_same_origin_delivery_authority`;
- `stale_signed_reference_authority_if_used`;
- `stale_internal_dispatch_record_if_used`;
- `stale_artifact_ref`;
- `stale_artifact_hash`;
- `stale_artifact_size`.

## Leak-Control Checklist

```yaml
leak_control_checklist:
  app_logs: must_not_log_credentials_tokens_targets_or_full_receipts
  error_bodies: must_not_include_credentials_tokens_targets_or_destination_secrets
  audit_records: redacted_or_hash_only_unless_later_admitted
  connector_logs: considered_if_connector_mode_selected
  destination_logs: considered_if_destination_mode_selected
  screenshots_and_traces: considered_for_playwright
  rendered_destination_labels: rendered_only_if_later_admitted
leak_controls_runtime_implemented: false
```

## Test Architecture Boundary

```yaml
test_architecture_boundary:
  real_connector_credentials_in_ci: forbidden_by_default
  real_destination_credentials_in_ci: forbidden_by_default
  fake_connector_or_destination_adapter: required_if_runtime_admitted
  connector_error_simulation: required_if_runtime_admitted
  destination_error_simulation: required_if_runtime_admitted
  missing_config_test: required_if_runtime_admitted
  stale_authority_test: required_if_runtime_admitted
  no_secret_or_target_leakage_test: required_if_runtime_admitted
  headed_and_headless_rendered_proof: required_if_rendered_controls_admitted
```

## Dependency Graph

```text
post_749_provider_public_url_entry_freeze
  -> connector_destination_dispatch_entry_freeze
    -> connector_destination_authority_discovery, if needed
      -> connector_destination_runtime_freeze
        -> connector_destination_runtime_implementation, if admitted
```

Connector/destination work remains independent from provider/public URL runtime, package mutation/reconstruction, source breadth expansion, qualitative/hybrid/RAG/vector expansion, browser/full mockup activation, and auth/security hardening. Auth/security may block runtime connector/destination implementation, but this freeze does not change auth/security behavior.

## Negative Invariants

- no new connector/destination runtime;
- no external connector invocation;
- no destination write;
- no connector-run creation;
- no generic downstream dispatch;
- no provider/public URL runtime;
- no provider object ACL change;
- no provider object write or copy;
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
- no existing internal_dispatch_record_only behavior change;
- no connector or destination credentials in browser or request;
- no connector/destination secrets, targets, URLs, or tokens in error bodies;
- no connector/destination secrets, targets, URLs, or tokens in logs;
- no cross-mode privilege escalation;
- no new route, DTO, model, migration, production service behavior, test behavior, or rendered UI control.

## Stop Condition

Stop before runtime implementation if any proposed change needs connector authority, destination authority, a named use case, artifact-family selection, credential/access model, lifecycle/retry/cancel/timeout behavior, receipt/audit behavior, stale-authority tests, fake connector/destination architecture, rendered controls, or auth/security posture that this entry freeze has not verified.
