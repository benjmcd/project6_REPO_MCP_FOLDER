# CI Performance Observability Entry Freeze

Status: planning/control entry freeze only for `ci_performance_observability_entry_freeze`.

This is a post-PR #755 entry-decision delta over docs `184` through `200`, the current GitHub workflow in `.github/workflows/playwright.yml`, the browser harness configuration in `playwright.config.js`, Layer 3 backend/API test requirements, browser harness tests, and `tools/l3-progress-check.py`. It does not implement CI workflow changes, performance budgets, timing gates, sharding, headed browser CI, new observability runtime, audit-event runtime, trace schema changes, log shipping, metrics, dashboards, route changes, DTO changes, service behavior, models, migrations, rendered UI controls, provider/public URLs, connector/destination dispatch, source expansion, package mutation, broad qualitative/hybrid/RAG behavior, hidden LLM planning, full mockup activation, auth/security behavior, or frontend-only durable authority.

## Decision

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
live_ci_profile: focused_layer3_backend_pytest_plus_serial_chromium_playwright
live_browser_harness_profile: fixed_port_8031_single_worker_trace_on_first_retry
live_artifact_profile: playwright_html_report_upload_only
reason: performance_budget_flake_policy_observability_schema_audit_event_contract_and_ci_expansion_scope_not_verified
next_follow_up: ci_performance_observability_authority_discovery_freeze_or_entry_freeze_update
```

This pass admits no CI, performance, or observability runtime change. Current main preserves only these live guardrails:

- `backend-layer3-api` runs focused `backend/tests/test_layer3_*.py` under Python 3.12 in CI;
- `test` installs npm/browser harness dependencies and runs `npx playwright test --project=chromium` under a single Chromium project;
- Playwright uses `fullyParallel: false`, `workers: 1`, fixed port `8031`, no existing server reuse, CI retries, and trace collection on first retry;
- CI uploads the Playwright HTML report artifact with 30-day retention;
- local headed/headless comparison remains a runbook/operator proof posture, not a CI-enforced headed-browser matrix;
- current progress/proof manifests and `l3-progress-check.py` provide planning/proof guardrails, not runtime telemetry or audit completeness.

Future CI/performance/observability candidate modes remain:

- `ci_observability_gap_inventory_only`;
- `layer3_ci_runtime_budget_guardrails`;
- `playwright_artifact_retention_and_trace_policy`;
- `backend_e2e_performance_budget`;
- `observability_provenance_audit_event_runtime`;
- `full_ci_performance_observability_program`.

A later freeze must choose exactly one mode before code or workflow changes.

## Evidence Ledger

```yaml
evidence_ledger:
  current_backend_layer3_api_ci_job:
    status: verified
    evidence:
      - .github/workflows/playwright.yml
      - backend/tests/requirements-layer3-api.txt
  current_playwright_ci_job:
    status: verified
    evidence:
      - .github/workflows/playwright.yml
      - playwright.config.js
      - backend/tests/requirements-browser.txt
  current_serial_browser_harness_profile:
    status: verified
    evidence:
      - playwright.config.js
      - backend/tests/review_browser_server.py
  current_progress_checker_profile:
    status: verified
    evidence:
      - tools/l3-progress-check.py
      - next_milestone_plans/layer3_progress_manifest.json
      - next_milestone_plans/layer3_workbench_proof_manifest.json
  performance_budget_model:
    status: unverified
    evidence: []
  flake_quarantine_policy:
    status: unverified
    evidence: []
  headed_headless_ci_matrix_policy:
    status: unverified
    evidence: []
  observability_event_schema:
    status: unverified
    evidence: []
  audit_trace_completeness_contract:
    status: unverified
    evidence: []
  metrics_log_shipping_dashboard_policy:
    status: unverified
    evidence: []
  artifact_retention_taxonomy:
    status: unverified
    evidence: []
```

## CI Performance Observability Exposure Model

```yaml
ci_performance_observability_exposure_model:
  selected_ci_mode: unknown
  performance_budget_authority: unknown
  test_duration_budget: unknown
  flake_policy: unknown
  headed_headless_matrix: unknown
  browser_artifact_policy: unknown
  observability_event_schema: unknown
  audit_trace_completeness_contract: unknown
  log_metric_export_target: unknown
  dashboard_or_report_authority: unknown
  retention_policy: unknown
  security_redaction_policy: unknown
  negative_side_effect_surface: unknown
```

## Capability Isolation Matrix

```yaml
capability_isolation_matrix:
  existing_backend_layer3_api_ci_job:
    change_allowed_in_this_pass: false
  existing_playwright_ci_job:
    change_allowed_in_this_pass: false
  existing_serial_browser_harness_profile:
    change_allowed_in_this_pass: false
  ci_workflow_change:
    runtime_allowed_in_this_pass: false
  performance_budget_gate:
    runtime_allowed_in_this_pass: false
  headed_browser_ci_matrix:
    runtime_allowed_in_this_pass: false
  sharding_or_parallelism_change:
    runtime_allowed_in_this_pass: false
  observability_event_runtime:
    runtime_allowed_in_this_pass: false
  audit_trace_runtime:
    runtime_allowed_in_this_pass: false
  metrics_log_shipping_dashboard:
    runtime_allowed_in_this_pass: false
  artifact_retention_policy_change:
    runtime_allowed_in_this_pass: false
  auth_security_behavior_change:
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

## Runtime Non-Admission

```yaml
runtime_admission:
  ci_workflow_change: false
  performance_budget_gate: false
  headed_browser_ci_matrix: false
  sharding_or_parallelism_change: false
  observability_event_runtime: false
  audit_trace_runtime: false
  metrics_log_shipping_dashboard: false
  artifact_retention_policy_change: false
  route_api_behavior_change: false
  model_migration_change: false
  source_expansion: false
  package_mutation_reconstruction: false
  provider_public_url_runtime: false
  connector_destination_dispatch_runtime: false
  broad_qualitative_hybrid_rag_runtime: false
  hidden_llm_planning: false
  full_mockup_activation: false
  auth_security_behavior_change: false
  frontend_only_durable_state: false
```

## Negative Invariants

- no CI workflow change;
- no Playwright configuration change;
- no backend test dependency change;
- no browser harness dependency change;
- no performance budget gate;
- no runtime timing assertion;
- no sharding or parallelism change;
- no headed browser CI matrix;
- no observability event runtime;
- no security audit-event runtime;
- no metrics, log shipping, dashboard, or external telemetry target;
- no artifact retention policy change;
- no route/API behavior change;
- no DTO change;
- no model or migration change;
- no production service behavior change;
- no test behavior change;
- no rendered UI control;
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
- no provider/public URL runtime;
- no connector or destination dispatch;
- no destination write;
- no full mockup activation;
- no auth/security behavior change;
- no frontend-only durable authority;
- no local path, provider URL, connector target, destination target, source credential, auth token, proxy header, prompt, metric payload, trace payload, or browser storage secret leakage in error bodies;
- no local path, provider URL, connector target, destination target, source credential, auth token, proxy header, prompt, metric payload, trace payload, or browser storage secret leakage in logs;
- no cross-mode privilege escalation;
- no new route, DTO, model, migration, production service behavior, test behavior, rendered UI control, or CI behavior.

## Stop Condition

Stop before implementation if a proposed change needs a performance budget, timing gate, CI sharding, headed-browser CI, observability event schema, audit trace completeness contract, metrics/log destination, artifact retention policy, security redaction policy, source expansion, package mutation, provider/public URL, connector/destination dispatch, broad qualitative/hybrid/RAG behavior, hidden LLM behavior, full mockup activation, auth/security behavior, or leakage guarantees that this entry freeze has not verified.
