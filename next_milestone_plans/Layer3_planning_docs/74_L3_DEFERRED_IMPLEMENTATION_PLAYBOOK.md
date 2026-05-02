# Layer 3 Deferred Implementation Playbook

Status: planning-only operational playbook for activating and implementing remaining deferred Layer 3 scope.

This document does not by itself select a new implementation lane, make deferred behavior live, change Gate C pass-entry behavior, widen schema/runtime/source scope, change UI, or activate package, handoff, connector, qualitative, hybrid, RAG, vector, or full mockup behavior. PR `#411` later used this playbook to land only the lower-level `descriptive_summary` analysis-service tranche.

## Purpose

The active progress packet has two distinct future-work concepts:

- `descriptive_summary` lower-level analysis-service support is now landed on current `main` by PR `#411`, governed by `72_L3_DESCRIPTIVE_SUMMARY_FREEZE.md` and `73_L3_DESCRIPTIVE_SUMMARY_CONTRACT.md`.
- The eight `deferred_scope` categories remain blocked unless their activation contracts are satisfied by live repo truth and a separately explicit freeze.

This playbook defines the operational requirements for moving any remaining deferred item from planning to implementation without over-claiming, silently widening scope, or accumulating uncontrolled tech debt.

## Current Authority

Use this order before selecting or implementing any deferred item:

1. Live `project6-origin/main` and the current branch diff.
2. The active progress/control packet:
   - `next_milestone_plans/layer3_progress_manifest.json`
   - `next_milestone_plans/layer3_progress_board.md`
   - `next_milestone_plans/layer3_progress_refresh_spec.md`
   - `next_milestone_plans/progress-prompt.md`
   - `next_milestone_plans/progress-ui-spec.md`
   - `next_milestone_plans/layer3_workbench_proof_manifest.json`
3. The governing freeze/contract docs for the exact candidate.
4. Actual source, tests, route maps, schema, and UI files.
5. GitHub PR/check/review state when a change is being landed.

Do not use branch names, older worktree names, memory, or prose summaries as implementation authority without rechecking the live files.

## Current Live Boundary

Current `main` supports these analysis method ids through `ANALYSIS_METHOD_REGISTRY`:

- `cross_correlation`
- `decomposition`
- `structural_break`
- `descriptive_summary`

`descriptive_summary` exists as a bounded lower-level analysis API method for datasets outside starter time-series assumptions, but it must not pass Gate C by implication.

Current Layer 3 pass-entry behavior rejects unsupported Gate C methods before creating Layer 3 plan/pass/run state. That fail-closed behavior remains the default unless a later Gate C admission freeze explicitly changes it.

## Non-Negotiable Operating Practices

- Start from a clean branch based on current `project6-origin/main`.
- Re-run live authority checks if `main` moves before merge.
- Separate audit, edit, testing/verification, and re-audit phases.
- Keep each implementation PR to one deferred item and one bounded tranche.
- Prefer additive owner-service code over shared contract/runtime reopening unless the activation contract proves shared-surface edits are necessary.
- Do not edit schema, migrations, runtime DB behavior, source ingestion, UI, package/handoff/export, or route families unless the active freeze explicitly admits that surface.
- Any validate-only action must be validate-only, fail closed on empty runtime, and must not seed or generate artifacts.
- Use isolated runtime/test state where possible; do not rely on shared seeded state.
- If a manifest or index is edited, first classify it as exhaustive or intentionally scoped, then verify declared entries and intentional exclusions.
- Browser proof is required for rendered UI behavior changes; use both headed and headless Chrome when the change affects user-visible browser behavior.

## End-To-End Lifecycle

### 0. Authority Check

Before planning implementation:

- Fetch `project6-origin/main`.
- Record the exact main commit.
- Confirm the working tree is clean or isolate a fresh worktree/branch.
- Read the relevant freeze/contract docs and actual source files.
- Verify whether the proposed item is current-main planning-only, current-main live bounded, branch-local, or not present.

Stop if the proposed item depends on a branch-local claim that is not confirmed on current `main`.

### 1. Candidate Activation

A deferred item may become a candidate only when all are true:

- Live repo truth proves a concrete gap.
- The gap maps to exactly one deferred category.
- Existing bounded surfaces cannot satisfy the need without widening.
- A governing freeze names the precise files, APIs, state transitions, no-go list, and proof plan.
- The progress/control packet can represent the candidate without changing existing settled history.

Stop if the candidate is only a broad product desire, generic "future work", or a convenience refactor.

### 2. Freeze Or Contract Update

Before code implementation, create or update planning docs only when the existing docs do not already govern the tranche.

The freeze must include:

- exact current live boundary
- exact admitted implementation scope
- explicit non-goals
- source/runtime/schema/UI/package/handoff constraints
- owner files expected to change
- tests required before merge
- stop conditions
- post-merge docs/control sync requirements

### 3. Implementation Branch

Implementation must be narrow:

- one owner module or a directly adjacent support module when possible
- focused tests before broad suites
- no opportunistic cleanup outside the tranche
- no changes to unrelated manifests, archives, generated files, or UI assets
- no schema/migration change unless explicitly admitted

If a needed change crosses into a deferred no-go category, stop and create a new freeze instead of continuing inside the same PR.

### 4. Verification

Run the smallest proof set that covers the changed surfaces, then add broader checks only when justified.

Minimum expected proof by change class:

- docs/control only: JSON parse where applicable, exact path declaration checks, stale-marker scan, `git diff --check`, CI checks.
- analysis service behavior: focused analysis API tests, method-registry tests, artifact/assumption/caveat tests, unsupported-method tests.
- Layer 3 pass-entry behavior: pass-entry preview/materialization/execution tests plus fail-closed unsupported-method tests.
- route/API behavior: OpenAPI contract tests, request validation tests, status/error envelope tests.
- rendered UI behavior: unit/static tests where present, Playwright/headless proof, headed Chrome proof, screenshot or DOM state proof when useful.
- schema or migration behavior: migration upgrade/downgrade or equivalent project-standard migration proof, schema-specific tests, rollback risk review.
- validate-only behavior: empty-runtime fail-closed proof, no artifact seeding/generation proof, CLI/operator proof if a tool is changed.

### 5. PR Landing

Before merge:

- Push the branch.
- Open a PR with scope and validation evidence.
- Wait for GitHub checks.
- Inspect comments, reviews, and review-thread state when available.
- Recheck mergeability and base commit drift.

If `main` moves, inspect the drift. If drift touches related authority surfaces, rebase or merge current main into the branch and rerun relevant validation before merge.

### 6. Post-Merge Re-Audit

After merge:

- Fetch `project6-origin/main`.
- Record the merge commit.
- Confirm merged-main contains the expected files and no unexpected diff remains.
- Re-run stale-marker and path-declaration checks for docs/control changes.
- Update progress/control packet metadata only if the merge changes active authority, counts, current focus, or tracked PR lineage.

## Current Next Functional Candidate

The only currently specified method-expansion candidate, `descriptive_summary`, has landed its first lower-level analysis-service tranche in PR `#411`.

That first implementation tranche stayed within docs `72`/`73` and added:

- one `descriptive_summary` registry entry
- one deterministic runner over already loaded dataset-version data
- one deterministic JSON artifact family only
- assumption/caveat rows for data availability, column classification, missingness, high cardinality, non-time-series interpretation, and empty/degenerate input
- unchanged recommendation sequences for time-series datasets
- preserved Layer 3 pass-entry fail-closed behavior unless a separate Gate C admission freeze is created

Landed implementation surfaces:

- `backend/app/services/analysis.py`
- `tests/test_api.py`

PR `#411` did not include UI, schema, migration, source ingestion, package/handoff/export, connector dispatch, or runtime DB changes in the first `descriptive_summary` implementation tranche.

## Deferred Category Gates

| Deferred item | Activation requirement | Default blocker | Required proof if activated |
| --- | --- | --- | --- |
| shared export-package contract/runtime reopening | Live downstream need cannot be solved by additive consumer code or existing exact-run gate hardening | Shared upstream blast radius is too high without a named contract/gate gap | shared contract/gate tests, owner-service tests, no package-context/schema/UI widening proof |
| package-derived context beyond bounded handoff | A named next package-context consumer or continuation is proven necessary | Current dossier input rule still uses paired export-derived context packets | package-context owner-service/gate tests, provenance tests, dossier-boundary non-regression |
| validate-only top-chain expansion | Repo graph/tree proves a concrete named validate-only family beyond current gates | Current later APS family decision is settled | validate-only empty-runtime fail-closed tests, CLI/operator tests, no seeding/artifact generation proof |
| future workbench route family | Operator/browser/product evidence proves shipped workbench surfaces are insufficient | Existing route/UI surfaces already cover many bounded workbench states | API/OpenAPI tests, state/idempotency tests, headed and headless browser proof |
| broader qualitative/hybrid/comparative/cross-modal breadth | Separate governance proves a bounded engine family and source contract | Current Layer 3 spine is wrapped quantitative only | new engine contract tests, source-boundary tests, no LLM/vector/RAG creep unless admitted |
| runtime DB writes | A freeze names exact runtime tables, write transactions, cleanup, and rollback behavior | Runtime DB boundary is read-only by default | isolated runtime-state tests, write/rollback tests, cleanup verification |
| schema widening | A freeze proves new schema is unavoidable and names migration/compatibility behavior | Current method candidate requires no schema/model/migration change | migration proof, model/API compatibility tests, rollback risk review |
| route/UI widening | A freeze names exact route, page, API, state, and browser behavior | Docs `72`/`73` admit no UI or route changes | API/OpenAPI tests, static/UI tests, headed/headless browser proof |

## Descriptive Summary Proof Status

PR `#411` added or updated tests proving:

- registry contains exactly the existing three methods plus `descriptive_summary`
- current three registry entries remain unchanged
- time-series recommendation output remains unchanged
- non-time-series recommendation can select `descriptive_summary`
- `run_analysis(..., method_name="descriptive_summary", ...)` creates deterministic JSON artifacts only
- assumptions/caveats are created for data availability, column classification, missingness, high cardinality, and degenerate input
- unsupported or empty input does not silently succeed as meaningful analysis
- current Layer 3 pass-entry fail-closed tests remain unless a separate Gate C freeze changes admission
- no schema/model/migration/UI/source/runtime widening occurs

Focused commands for the landed tranche:

```powershell
python -m pytest .\tests\test_api.py::test_analysis_method_registry_describes_current_methods_only .\tests\test_api.py::test_descriptive_summary_runs_deterministic_json_without_widening_scope .\tests\test_api.py::test_descriptive_summary_column_summary_handles_nested_values_deterministically .\tests\test_api.py::test_decomposition_and_break_detection_persist_artifacts .\tests\test_api.py::test_structural_break_zero_breakpoint_path_returns_caveat_not_blank_artifact .\tests\test_api.py::test_decomposition_short_series_returns_caveat_not_exception .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_fails_closed_on_unsupported_cohort_recommended_method .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_excludes_unsupported_recommended_method_and_fails_closed -q
```

Add new focused tests adjacent to any future changed behavior before broadening to larger suites.

## Stop Conditions

Stop and return to planning if any implementation requires:

- adding or changing database schema
- writing runtime DB state
- adding a rendered UI or route
- changing package/handoff/export/download behavior
- adding source ingestion, local upload, local directory, connector input, public/signed URL, or generic dispatch behavior
- adding qualitative, hybrid, RAG, vector, LLM, DAG, background job, retry, cancellation, or agent-conductor behavior
- allowing `descriptive_summary` through Layer 3 pass-entry without a separate Gate C admission rule
- treating docs-only governance as live implementation

## Posture Summary

The adequate next posture is not "implement all deferred items." It is:

1. Keep the eight deferred categories blocked behind their activation contracts.
2. Treat `descriptive_summary` lower-level analysis API support as landed by PR `#411`, with Gate C admission still deferred.
3. Treat docs `75`/`76` as the planning-only boundary for the next possible single-item Gate C admission tranche; they do not implement pass-entry behavior.
4. Preserve Layer 3 pass-entry fail-closed behavior until separately governed.
5. Land any implementation with focused tests, CI, review-state checks, and a post-merge progress/control sync.
