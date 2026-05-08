# CI Performance Observability Entry Contract

Status: planning/control contract paired with `201_CI_PERFORMANCE_OBSERVABILITY_ENTRY_FREEZE.md`.

This contract defines requirements for moving beyond the deferred `ci_performance_observability_entry_freeze` decision. It admits no CI workflow change, Playwright configuration change, test dependency change, performance budget, timing gate, sharding, headed browser CI matrix, observability event runtime, audit trace runtime, metrics/log shipping, dashboard, artifact retention policy change, route, DTO, service behavior, model, migration, rendered UI control, source expansion, package mutation, provider/public URL runtime, connector/destination dispatch, broad qualitative/hybrid/RAG behavior, hidden LLM planning, full mockup activation, auth/security behavior, or frontend-only durable authority.

Docs `184` through `200` remain authority for downstream, provider, connector, package, source, qualitative/RAG, mockup, and auth/security entry boundaries. This contract is the narrower post-PR #755 entry-decision layer for CI/performance/observability expansion.

## Authority Order

1. live `project6-origin/main` source, tests, models, migrations, routes, service code, static UI files, Playwright tests, workflow files, and checker behavior;
2. `.github/workflows/playwright.yml` and `playwright.config.js`;
3. `backend/tests/requirements-layer3-api.txt`, `backend/tests/requirements-browser.txt`, and `backend/tests/review_browser_server.py`;
4. progress/proof manifests and `tools/l3-progress-check.py`;
5. docs `184` through `200`;
6. this contract and `201_CI_PERFORMANCE_OBSERVABILITY_ENTRY_FREEZE.md`.

Planning prose, manually observed runtime duration, local terminal timing, unretained logs, browser screenshots, copied console text, prior PR titles, and generated reports without a frozen retention/authority contract are not sufficient authority for runtime implementation.

## Entry Decision Contract

```yaml
entry_decision: deferred
selected_mode: null
runtime_status: not_implemented
live_ci_profile: focused_layer3_backend_pytest_plus_serial_chromium_playwright
live_browser_harness_profile: fixed_port_8031_single_worker_trace_on_first_retry
live_artifact_profile: playwright_html_report_upload_only
receipt_family: no_receipt_planning_only
```

The decision may change only in a later freeze if all of these are repo-confirmed: selected CI/observability mode, performance budget authority, duration measurement method, flake policy, headed/headless matrix, browser artifact policy, observability schema, audit-trace completeness contract, log/metric export target, retention policy, redaction policy, negative invariant proof, and no-cross-mode privilege escalation proof.

## Allowed Future Modes

A later runtime freeze must choose exactly one of:

- `ci_observability_gap_inventory_only`;
- `layer3_ci_runtime_budget_guardrails`;
- `playwright_artifact_retention_and_trace_policy`;
- `backend_e2e_performance_budget`;
- `observability_provenance_audit_event_runtime`;
- `full_ci_performance_observability_program`.

The selected mode must not rename transient local timings, browser state, ad hoc logs, screenshots, or unfrozen reports as authoritative performance or observability evidence.

## Request Or Configuration Contract For Later Runtime

A future CI/configuration change must be explicit about changed workflow jobs, commands, environment variables, timeout/retry/worker settings, artifact outputs, redaction behavior, and compatibility with the fixed-port review browser harness.

A future observability runtime request or event must be server-authority based. It may include or derive server-side run refs, session refs, route refs, deterministic hashes, duration measurements, policy refs, and response-safe event labels only if the future freeze admits those fields.

The change must not accept browser-local workflow state, local filesystem paths, credentials, provider URLs, connector targets, destination targets, auth tokens, prompt/model fields, package payload bodies, or arbitrary telemetry blobs unless a later freeze explicitly admits one narrow server-authoritative mode.

## Response Or Artifact Contract For Later Runtime

A future response/artifact may expose only response-safe metadata admitted by the later freeze: selected mode, run refs, policy refs/hashes, duration summary, response-safe failure code, response-safe failure reason, and next actions.

The response/artifact must not expose local filesystem paths, credentials, bearer tokens, proxy header values, provider URLs, connector targets, destination targets, prompt text, model/provider internals, package payload bodies, auth internals, metric secrets, trace secrets, or browser storage as authority.

## Existing Runtime Compatibility Contract

This entry freeze must preserve existing behavior:

- CI continues to run the current focused backend Layer 3 pytest job and serial Chromium Playwright job;
- Playwright remains single-worker, fixed-port, no-reuse, and trace-on-first-retry under the current config;
- browser artifacts remain the current HTML report upload only;
- progress/proof manifests and `l3-progress-check.py` remain structural proof/checker guardrails, not telemetry or audit-event runtime;
- no existing Layer 3 route, service, model, migration, UI, or test behavior changes under this freeze.

## Browser And Theme Contract

This entry freeze adds no rendered UI control. If a later freeze admits headed/headless CI expansion, visual evidence collection, or rendered observability UI, it must preserve `light`, `dark`, and `workbench` theme behavior, prove headed and headless Chromium consistency, prove responsive and disabled/focus/error states where UI changes occur, and avoid browser-state-only durable workflow truth.

## Test Contract For Later Runtime

Runtime or CI implementation remains blocked until a later freeze names tests for measurement stability, timeout/retry/worker behavior, flake policy, no broad source/package/provider/connector/RAG/mockup/auth expansion, no unintended DB/file/package/provider/connector/destination side effects, no frontend-only durable authority, no path/credential/token/browser-storage leakage, headed/headless proof if CI/browser scope changes, and theme/accessibility coverage if UI changes are admitted.

## Checker Contract

`tools/l3-progress-check.py` should verify structural guardrails only: docs `201` and `202` exist and are referenced; entry decision is `deferred`; selected mode is null; runtime status is `not_implemented`; current CI/browser/artifact profiles are acknowledged without changing them; evidence ledger exists and unverified performance budget, flake policy, headed/headless CI policy, observability event schema, audit trace contract, metrics/log/dashboard policy, and artifact retention taxonomy force deferral; exposure model exists and unknown values force deferral; capability isolation matrix exists and all runtime flags remain false; negative invariants are present; docs do not claim CI/performance/observability hardening is live.

The checker must not pretend to validate actual CI capacity, performance stability, flake rate, observability completeness, log redaction, telemetry security, artifact retention, headed browser reliability, or route/API correctness in this planning-only pass.

## Stop Conditions

Stop and return to planning if a future implementation proposal tries to activate more than one CI/performance/observability mode, change CI workflows without explicit job/timeout/retry/artifact contracts, use transient local timings as performance authority, collect telemetry without a schema and redaction policy, add headed CI without harness/port isolation proof, treat browser reports as durable product authority, or admit source/package/provider/connector/RAG/mockup/auth behavior under CI/performance/observability scope.
