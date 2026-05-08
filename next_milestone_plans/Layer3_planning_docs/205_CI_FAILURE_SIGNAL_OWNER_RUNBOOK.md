# CI Failure Signal And Owner Runbook

Status: planning/control runbook only for `ci_failure_signal_and_owner_runbook`.

This document is the narrow follow-up to `204_CI_OBSERVABILITY_GAP_INVENTORY.md`. It defines how to interpret current-main CI failure signals and logical owner surfaces before any flake policy, performance budget, artifact taxonomy, headed/headless matrix, observability event schema, audit-event runtime, workflow, Playwright configuration, test behavior, dependency, route, DTO, model, migration, service, rendered UI, source, package, provider, connector, RAG/vector, mockup, auth/security, or frontend durable-authority implementation.

It admits no runtime behavior, no CI workflow change, no Playwright configuration change, no executable test change, and no CODEOWNERS or GitHub protection-rule change. Owner labels below are planning/triage owners only.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- parent inventory: `204_CI_OBSERVABILITY_GAP_INVENTORY.md`
- governing freeze: `201_CI_PERFORMANCE_OBSERVABILITY_ENTRY_FREEZE.md`
- current workflow: `.github/workflows/playwright.yml`
- current browser config: `playwright.config.js`
- current browser server harness: `backend/tests/review_browser_server.py`
- current checker: `tools/l3-progress-check.py`

Live workflow files, tests, source, GitHub check results, and checker behavior outrank this runbook.

## Current Check Surface

```yaml
current_check_surface:
  backend-layer3-api:
    workflow_job: backend-layer3-api
    timeout_minutes: 20
    command: python -m pytest ./backend/tests/test_layer3_*.py -q
    logical_owner: layer3_backend_api_proof_owner
    primary_failure_meaning: backend_layer3_api_or_contract_regression_until_proven_otherwise
  test:
    workflow_job: test
    timeout_minutes: 60
    command: npx playwright test --project=chromium
    logical_owner: layer3_browser_harness_proof_owner
    primary_failure_meaning: browser_harness_or_rendered_path_regression_until_proven_otherwise
```

## Failure Signal Matrix

| Signal | First classification | Logical owner | Immediate action | Rerun allowed before fix? |
| --- | --- | --- | --- | --- |
| `backend-layer3-api` pytest assertion/error | Layer 3 backend/API contract failure | `layer3_backend_api_proof_owner` | Inspect failing test, route/service contract, fixture authority, and recent diff. | No, unless the log proves external infrastructure failure. |
| `backend-layer3-api` dependency install failure | CI dependency/infrastructure failure | `ci_dependency_owner` | Inspect pip cache/install log and requirements file authority. | Yes, once, if no repo diff can explain the failure. |
| `backend-layer3-api` timeout | Backend test runtime or infrastructure failure | `layer3_backend_api_proof_owner` plus `ci_runtime_owner` | Inspect last emitted test, known slow tests, and GitHub runner status. | No if the same test hangs reproducibly; yes once if runner stall is evident. |
| `test` npm install failure | Node dependency/infrastructure failure | `ci_dependency_owner` | Inspect `npm ci` log and lockfile authority. | Yes, once, if registry/cache failure is explicit. |
| `test` browser install failure | Playwright/browser dependency failure | `browser_harness_dependency_owner` | Inspect Playwright install log and runner dependency status. | Yes, once, if install infra failure is explicit. |
| `test` webServer health timeout | Browser harness startup failure | `layer3_browser_harness_proof_owner` | Inspect `review_browser_server.py`, port `8031`, env, DB init mode, and server traceback. | No if app startup traceback is present. |
| `test` Playwright assertion failure | Rendered workbench proof failure | `layer3_rendered_workbench_proof_owner` | Inspect trace/report, selector contract, API setup, and rendered state authority. | No, unless retry passes and logs prove a known transient browser issue. |
| `test` retry-pass after first failure | Candidate flake | `flake_triage_owner` | Preserve check URL, failed attempt signal, trace availability, and classify before merging repeated occurrences. | One rerun may be acceptable for infrastructure noise; repeated occurrences require a flake-policy freeze. |
| `test` timeout | Browser harness runtime, hanging selector, or infrastructure failure | `layer3_browser_harness_proof_owner` plus `ci_runtime_owner` | Inspect last test, trace/report if present, server logs, and runner status. | No if same test/phase repeats; yes once for clear runner stall. |

## Merge And Stop Rules

```yaml
merge_rules:
  required_before_merge:
    - backend-layer3-api conclusion is success
    - test conclusion is success
    - PR comments inspected
    - PR reviews inspected
    - PR review threads inspected
    - no unresolved actionable review debt
  rerun_rules:
    legitimate_single_rerun:
      - external package registry failure
      - GitHub runner stall or cancellation
      - transient browser install infrastructure failure
    not_legitimate_without_fix:
      - deterministic pytest failure
      - deterministic Playwright assertion failure
      - application startup traceback
      - repeated timeout in the same phase
      - checker/proof/manifest failure
  stop_before_merge:
    - failed required check without repo-external cause
    - unresolved review thread
    - code-review comment requiring amendment
    - main drift that changes the touched planning/checker surface
```

## Owner Surfaces

These are planning labels, not GitHub CODEOWNERS:

- `layer3_backend_api_proof_owner`: backend Layer 3 route/service/API contract tests and `backend/tests/test_layer3_*.py` failures.
- `layer3_browser_harness_proof_owner`: Playwright harness startup, fixed-port server, browser setup, and `/review/layer3` rendered proof failures.
- `layer3_rendered_workbench_proof_owner`: selector, rendered state, and server-authoritative UI proof failures.
- `ci_dependency_owner`: pip, npm, lockfile, and runner dependency install failures.
- `browser_harness_dependency_owner`: Playwright browser install and browser runtime dependency failures.
- `ci_runtime_owner`: timeout, runner capacity, and job runtime classification.
- `flake_triage_owner`: retry-pass, intermittent timeout, and recurrence tracking until a later flake policy exists.

## Evidence To Preserve In Reports

A CI failure report should record:

- PR number and branch;
- failing check name;
- workflow run URL;
- failing command or workflow step;
- first failing test or step;
- whether retry was used;
- whether failure was deterministic, infrastructure-bound, or unknown;
- logical owner label;
- exact next action: fix, rerun once, wait, or stop.

## Explicit Non-Admissions

This runbook admits no:

- CI workflow change;
- Playwright configuration change;
- backend or browser dependency change;
- executable test change;
- CODEOWNERS or branch protection change;
- automatic rerun bot;
- flake quarantine runtime;
- performance budget or timing gate;
- headed-browser CI matrix;
- sharding or parallelism;
- observability event runtime;
- audit-event runtime;
- metrics/log shipping or dashboard;
- artifact retention change;
- route/API/DTO/model/migration/service behavior change;
- rendered UI control;
- source expansion;
- package mutation or reconstruction;
- provider/public URL runtime;
- connector/destination dispatch;
- RAG/vector retrieval;
- hidden LLM planning;
- full mockup activation;
- auth/security behavior change;
- frontend-only durable authority.

## Stop Condition

Stop before implementation if a proposed next task changes CI workflows, Playwright config, test code, dependencies, CODEOWNERS, branch protections, artifact retention, performance gates, headed CI, sharding, observability runtime, audit-event runtime, route/DTO/model/migration/service behavior, rendered UI, source/package/provider/connector/RAG/mockup/auth behavior, or frontend durable authority without a later exact implementation-entry freeze.
