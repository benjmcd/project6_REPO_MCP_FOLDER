# Auth Security Entry Freeze

Status: planning/control entry freeze only for `auth_security_entry_freeze`.

This is a post-PR #754 entry-decision delta over docs `184` through `198`, the current deployment-profile guardrails in `backend/app/core/config.py`, the Layer 3 route/request contracts in `backend/app/api/layer3.py`, and the existing deployment/API guard tests in `backend/tests/test_layer3_api.py`. It does not implement authentication, authorization, tenant isolation, operator permission checks, session ownership, route dependency changes, middleware, model or migration changes, rendered UI controls, provider/public URLs, connector/destination dispatch, package mutation, source expansion, broad qualitative/hybrid/RAG behavior, hidden LLM planning, full mockup activation, or frontend-only durable authority.

## Decision

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
live_deployment_profile: local_default_with_nonlocal_proxy_guardrails
live_layer3_auth_owner: none_or_proxy_config_only
live_storage_exposure_guardrail: nonlocal_direct_storage_disabled
reason: route_identity_tenant_session_permission_audit_policy_and_operator_role_model_not_verified
next_follow_up: auth_security_authority_discovery_freeze_or_entry_freeze_update
```

This pass admits no Layer 3 auth/security runtime. Current main preserves only these live guardrails:

- local development remains `AUTH_OWNER=none` by default and keeps the existing proof-harness posture;
- nonlocal deployment settings fail closed unless origins are explicit HTTPS origins, `AUTH_OWNER=proxy`, `TRUSTED_PROXY_MODE=true`, and direct storage exposure remains disabled/auto;
- Layer 3 endpoints currently depend on DB/session wiring rather than route-level user or tenant dependencies;
- request fields such as `auth_policy_override`, `auth_security_directive`, `auth_context`, and `security_context` remain forbidden/deferred on the surfaces that already declare them as blocked;
- rendered/browser state remains non-authoritative for identity, permissions, session ownership, destination access, provider access, connector credentials, or security policy.

Future auth/security candidate modes remain:

- `deployment_profile_guardrail_only`;
- `proxy_identity_read_only_projection`;
- `route_level_operator_identity_required`;
- `session_tenant_owner_authorization`;
- `package_handoff_export_permission_gates`;
- `full_layer3_security_hardening_program`;
- `auth_security_gap_inventory_only`.

A later freeze must choose exactly one mode before code.

## Evidence Ledger

```yaml
evidence_ledger:
  current_deployment_profile_guardrails:
    status: verified
    evidence:
      - backend/app/core/config.py
      - backend/tests/test_layer3_api.py
  current_layer3_route_dependency_surface:
    status: verified
    evidence:
      - backend/app/api/layer3.py
      - app.api.deps.get_db
  current_forbidden_auth_security_request_fields:
    status: verified
    evidence:
      - backend/app/api/layer3.py
      - backend/tests/test_layer3_api.py
  current_storage_exposure_guardrail:
    status: verified
    evidence:
      - backend/app/core/config.py
      - backend/main.py
      - backend/tests/test_layer3_api.py
  identity_authority_model:
    status: unverified
    evidence: []
  tenant_session_ownership_model:
    status: unverified
    evidence: []
  operator_role_permission_matrix:
    status: unverified
    evidence: []
  route_level_auth_dependency_contract:
    status: unverified
    evidence: []
  audit_log_security_event_contract:
    status: unverified
    evidence: []
  provider_connector_secret_policy:
    status: unverified
    evidence: []
  browser_identity_theme_accessibility_plan:
    status: unverified
    evidence: []
```

## Auth Security Exposure Model

```yaml
auth_security_exposure_model:
  selected_auth_mode: unknown
  identity_authority: unknown
  tenant_authority: unknown
  session_owner_authority: unknown
  operator_role_authority: unknown
  permission_matrix: unknown
  route_dependency_contract: unknown
  storage_access_contract: unknown
  provider_secret_contract: unknown
  connector_secret_contract: unknown
  audit_event_contract: unknown
  browser_identity_surface: unknown
  headed_headless_theme_proof_scope: unknown
  negative_side_effect_surface: unknown
```

## Capability Isolation Matrix

```yaml
capability_isolation_matrix:
  deployment_profile_guardrails:
    change_allowed_in_this_pass: false
  route_level_auth_dependencies:
    runtime_allowed_in_this_pass: false
  identity_session_tenant_authority:
    runtime_allowed_in_this_pass: false
  operator_permission_matrix:
    runtime_allowed_in_this_pass: false
  security_audit_event_runtime:
    runtime_allowed_in_this_pass: false
  provider_secret_handling:
    runtime_allowed_in_this_pass: false
  connector_credential_handling:
    runtime_allowed_in_this_pass: false
  browser_identity_controls:
    runtime_allowed_in_this_pass: false
  full_mockup_activation:
    runtime_allowed_in_this_pass: false
  frontend_only_durable_state:
    runtime_allowed_in_this_pass: false
  source_breadth_expansion:
    runtime_allowed_in_this_pass: false
  package_mutation_reconstruction:
    runtime_allowed_in_this_pass: false
  provider_public_url:
    runtime_allowed_in_this_pass: false
  connector_destination_dispatch:
    runtime_allowed_in_this_pass: false
  rag_vector_or_hybrid_execution:
    runtime_allowed_in_this_pass: false
  hidden_llm_planning:
    runtime_allowed_in_this_pass: false
```

## Browser And Theme Boundary

This entry freeze adds no rendered UI control and does not change `layer3.html`, `layer3.js`, or `layer3.css`. A later auth/security UI freeze must preserve `light`, `dark`, and `workbench` theme behavior, prove headed and headless Chromium consistency, prove disabled/focus/error states, and prove that browser-visible identity or permission state is projection only unless backed by a server-authoritative auth/session contract.

## Runtime Non-Admission

```yaml
runtime_admission:
  auth_security_behavior_change: false
  route_level_auth_dependency: false
  tenant_session_ownership_runtime: false
  operator_permission_runtime: false
  security_audit_event_runtime: false
  provider_secret_runtime: false
  connector_credential_runtime: false
  new_rendered_identity_controls: false
  model_migration_change: false
  source_expansion: false
  package_mutation_reconstruction: false
  provider_public_url_runtime: false
  connector_destination_dispatch_runtime: false
  broad_qualitative_hybrid_rag_runtime: false
  hidden_llm_planning: false
  full_mockup_activation: false
  frontend_only_durable_state: false
```

## Negative Invariants

- no auth/security behavior change;
- no route-level authentication dependency change;
- no authorization or permission enforcement change;
- no tenant, session-owner, or operator-role runtime admission;
- no proxy identity header trust expansion;
- no storage exposure expansion;
- no security audit-event runtime;
- no provider secret handling or provider public URL runtime;
- no connector credential handling or connector/destination dispatch;
- no destination write;
- no new rendered identity or permission controls;
- no frontend-only durable authority;
- no browser state treated as identity, permission, session-owner, or tenant authority;
- no route/API behavior change;
- no DTO change;
- no model or migration change;
- no production service behavior change;
- no test behavior change;
- no source expansion;
- no source adapter registry;
- no local upload;
- no local-directory ingestion;
- no web connector retrieval;
- no broad execution;
- no broad qualitative execution;
- no hybrid execution;
- no RAG/vector retrieval;
- no hidden LLM planning;
- no package mutation or reconstruction;
- no full mockup activation;
- no local path, provider URL, connector target, destination target, source credential, auth token, proxy header, prompt, or browser storage secret leakage in error bodies;
- no local path, provider URL, connector target, destination target, source credential, auth token, proxy header, prompt, or browser storage secret leakage in logs;
- no cross-mode privilege escalation;
- no new route, DTO, model, migration, production service behavior, test behavior, or rendered UI control.

## Stop Condition

Stop before runtime implementation if a proposed change needs identity authority, route-level auth dependency, tenant/session ownership, operator role or permission matrix, provider/connector credential policy, audit-event semantics, storage exposure changes, rendered identity controls, headed/headless theme proof, source expansion, package mutation, provider/public URL, connector/destination dispatch, broad qualitative/hybrid/RAG behavior, hidden LLM behavior, full mockup activation, or leakage guarantees that this entry freeze has not verified.
