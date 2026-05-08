# Named Runtime Use Case Selection Gate

Status: current-main planning/control gate for `named_runtime_use_case_selection_gate`.

This document follows `221_CURRENT_MAIN_RUNTIME_ENTRY_READINESS_REPORT.md`. It is a decision-control artifact only. It does not implement runtime behavior, change routes, DTOs, models, migrations, services, executable tests, rendered UI controls, Playwright configuration, CI workflow, source handling, package behavior, connector behavior, provider/public URL behavior, RAG/vector behavior, mockup behavior, auth/security behavior, hidden LLM behavior, or frontend-only durable authority.

## Decision

```yaml
selected_planning_mode: named_runtime_use_case_selection_gate
entry_decision: selection_gate_only
selected_runtime_family: null
selected_runtime_mode: null
named_use_case_selected: false
runtime_status: not_implemented
implementation_entry_freeze_required: true
```

No runtime family is selected in this pass. The repo is not ready for direct implementation until a later pass names exactly one product/operator use case and proves the implementation-entry authority for that one use case.

## Current Authority

The live authority remains the bounded current-main Layer 3 behavior recorded by docs `213` through `221` and guarded by `tools/l3-progress-check.py`:

- bounded Layer 3 API flow;
- raw mixed seed-only and materialization boundaries over admitted source authority;
- exact single APS document qualitative chain;
- rendered workbench controls for already-admitted backend/API paths;
- same-origin delivery and signed-reference behavior;
- progress/proof/checker guardrails.

These are implementation authority only for their current bounded behavior. They do not authorize provider/public URL runtime, external connector/destination runtime, source breadth runtime, rendered package mutation runtime, broad qualitative/hybrid/RAG runtime, browser/full mockup activation, auth/security runtime, or CI/performance/observability runtime.

## Selection Gate

A future runtime implementation-entry freeze must provide all of:

1. exactly one selected runtime family;
2. exactly one selected runtime mode;
3. one named operator/product use case;
4. evidence that existing bounded behavior is insufficient for that use case;
5. canonical source of truth and authority order;
6. route/API request and response contract;
7. owner service/function and state-transition contract;
8. DB rows read and written;
9. files/artifacts read and written;
10. idempotency, concurrency, stale-state, replay, and recovery semantics;
11. failure-mode and forbidden-side-effect contract;
12. required tests, including negative invariants;
13. theme, accessibility, headed, and headless proof plan if rendered UI changes are admitted;
14. auth/security/leakage posture for the selected surface;
15. explicit stop condition for any unresolved authority.

If any item is missing, the correct action is to stop at planning and not implement runtime behavior.

## Candidate Families

```yaml
candidate_runtime_families:
  provider_public_url_runtime:
    current_status: not_selected
    prior_closeout: 213_PROVIDER_PUBLIC_URL_AUTHORITY_DISCOVERY_CLOSEOUT.md
    blocker: named_downstream_use_case_and_provider_storage_authority_not_selected
  external_connector_destination_runtime:
    current_status: not_selected
    prior_closeout: 214_CONNECTOR_DESTINATION_AUTHORITY_DISCOVERY_CLOSEOUT.md
    blocker: connector_destination_family_credentials_lifecycle_and_receipt_contract_not_selected
  source_breadth_runtime:
    current_status: not_selected
    prior_closeout: 215_SOURCE_BREADTH_AUTHORITY_DISCOVERY_CLOSEOUT.md
    blocker: source_family_adapter_input_security_and_provenance_contract_not_selected
  package_mutation_rendered_runtime:
    current_status: not_selected
    prior_closeout: 216_PACKAGE_MUTATION_RENDERED_AUTHORITY_DISCOVERY_CLOSEOUT.md
    blocker: operator_package_revision_use_case_mutation_mode_and_downstream_invalidation_contract_not_selected
  broad_qual_hybrid_rag_runtime:
    current_status: not_selected
    prior_closeout: 217_QUAL_HYBRID_RAG_AUTHORITY_DISCOVERY_CLOSEOUT.md
    blocker: broad_qualitative_hybrid_retrieval_prompt_model_output_taxonomy_and_leakage_authority_not_selected
  browser_full_mockup_runtime:
    current_status: not_selected
    prior_closeout: 218_BROWSER_FULL_MOCKUP_AUTHORITY_DISCOVERY_CLOSEOUT.md
    blocker: mockup_source_owner_route_api_mapping_server_authority_and_theme_headed_headless_plan_not_selected
  auth_security_runtime:
    current_status: not_selected
    prior_closeout: 219_AUTH_SECURITY_AUTHORITY_DISCOVERY_CLOSEOUT.md
    blocker: identity_tenant_session_operator_permission_route_dependency_secret_policy_and_threat_model_not_selected
  ci_performance_observability_runtime:
    current_status: not_selected
    prior_closeout: 212_CI_OBSERVABILITY_NO_RUNTIME_CLOSEOUT.md
    blocker: ci_runtime_should_only_start_if_ci_itself_becomes_the_concrete_blocker
```

## Ranking Rule

Future selection must rank candidates by:

- user/operator value of the named use case;
- current bounded behavior insufficiency evidence;
- dependency ordering;
- safety and leakage risk;
- non-fragility of tests and fixtures;
- modularity of the owner service and API surface;
- scalability of state, artifacts, and authority contracts;
- chance of accidental scope widening.

The ranking must not select a runtime family solely because it is next in a roadmap list.

## Non-Fragility Requirements

A later implementation freeze must avoid:

- relying on planning prose as implementation proof;
- using browser state as durable authority;
- hardcoding non-contractual timestamps, row order, paths, provider URLs, connector destinations, model names, or generated IDs;
- silently treating test fixtures as production authority;
- combining multiple runtime families in one pass;
- adding rendered controls without light, dark, workbench, headed, and headless proof when applicable;
- omitting forbidden-side-effect assertions;
- creating broad source, package, connector, provider, RAG, mockup, or auth behavior behind an unrelated fix.

## Negative Invariants

- no provider/public URL runtime;
- no external connector invocation;
- no destination write;
- no generic downstream dispatch;
- no source adapter registry;
- no local upload;
- no local-directory ingestion;
- no web connector retrieval;
- no broad source expansion;
- no package mutation or reconstruction;
- no broad qualitative/hybrid/RAG runtime;
- no vector index creation;
- no embedding generation;
- no hidden LLM planning;
- no prompt/model/provider runtime;
- no full mockup activation;
- no frontend-only durable authority;
- no auth/security behavior change;
- no route/API behavior change;
- no DTO behavior change;
- no model or migration change;
- no production service behavior change;
- no executable test behavior change;
- no rendered UI control;
- no Playwright configuration change;
- no CI workflow change.

## Recommended Next Action

```yaml
recommended_next_action: choose_exact_named_runtime_use_case_before_any_runtime_implementation
if_exact_named_use_case_exists: write_one_implementation_entry_freeze_for_that_use_case
if_exact_named_use_case_does_not_exist: stop_at_planning
if_review_or_checker_drift_appears: reconcile_before_any_new_runtime_selection
```

## Stop Condition

Stop before implementation if the next task does not name one runtime family, one runtime mode, one concrete operator/product use case, and the implementation-entry authority required to make that use case safe.
