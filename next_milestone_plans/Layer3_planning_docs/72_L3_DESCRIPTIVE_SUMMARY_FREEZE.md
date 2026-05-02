# Layer 3 Descriptive Summary Freeze

Status: planning-only governance for a future `descriptive_summary` method-expansion decision.

This document freezes the smallest safe boundary for deciding whether the existing `descriptive_summary` recommendation label may become a real supported wrapped quantitative method. It does not implement `descriptive_summary`, add it to `ANALYSIS_METHOD_REGISTRY`, change recommendation or execution behavior, change Layer 3 workbench UI, or widen source/runtime/schema scope.

## Current Live Boundary

Current `main` has a bounded current-methods registry and a fail-closed Layer 3 pass-entry path:

- `backend/app/services/analysis.py` supports exactly `cross_correlation`, `decomposition`, and `structural_break` through `ANALYSIS_METHOD_REGISTRY`.
- `recommend_analysis(...)` returns `descriptive_summary` only as the fallback label when a dataset does not meet the starter time-series assumptions.
- `run_analysis(...)` does not dispatch a `descriptive_summary` runner; unsupported method names produce an unsupported-method caveat rather than real method artifacts.
- `backend/app/services/layer3_pass_entry.py` rejects unsupported Gate C methods before creating Layer 3 plan/pass/run state.
- `backend/tests/test_layer3_pass_entry.py` proves unsupported `descriptive_summary` recommendations fail closed for current Layer 3 pass-entry materialization.

## Problem Statement

The repo already names `descriptive_summary`, but only as a fallback recommendation label. Treating that label as executable without governance would blur three boundaries at once: method admission, non-time-series dataset handling, and Layer 3 pass-entry eligibility. Before implementation, the repo needs a precise method contract that defines what a descriptive summary is allowed to compute, persist, expose, and prove.

## Slice Decision

The next safe planning boundary is:

> Freeze `descriptive_summary` as a future single-method wrapped quantitative expansion candidate, limited to deterministic summary statistics over an existing dataset version, without source/schema/runtime/UI widening.

This is intentionally governance first. It selects a concrete method-expansion candidate while preserving the current fail-closed behavior until a separate implementation PR is admitted and proven.

## Admitted Future Implementation Scope

A later implementation PR governed by this freeze may add only:

- one `descriptive_summary` registry entry in the existing analysis-method registry
- one deterministic runner for existing dataset-version data already loadable through `load_version_dataframe(...)`
- summary artifacts derived from existing columns, row counts, missingness, numeric distributions, categorical counts, and optional time-column coverage
- assumption and caveat rows for data availability, column typing, missingness, high cardinality, and non-time-series interpretation limits
- focused API and Layer 3 pass-entry tests proving the new method is admitted only where the contract allows it

## Explicit Non-Goals

This freeze does not admit:

- implementing the method by itself
- adding more than one method
- qualitative, hybrid, RAG, vector, LLM, local upload, local directory, or new source-ingestion behavior
- new models, migrations, tables, indexes, runtime DB writes, or schema widening
- workbench UI expansion, new route families, or full mockup activation
- package, handoff, connector, destination, public/signed URL, or downstream dispatch behavior
- package mutation/reconstruction or additional package/reconciliation/artifact row families beyond existing analysis artifacts
- broad plugin architecture, DAG orchestration, retries, cancellation, background jobs, or agent-conductor behavior

## Required Decisions Frozen Here

| Gate | Decision | Reasoning |
| --- | --- | --- |
| Method identity | `descriptive_summary` is the only candidate selected | Prevents this packet from becoming general method expansion |
| Engine family | wrapped quantitative only | Keeps the method inside the existing analysis service spine |
| Source scope | existing dataset version only | Avoids local upload, directory, connector, or runtime snapshot widening |
| Output posture | deterministic summary artifacts plus assumptions/caveats only | Keeps outputs inspectable and package-compatible later without changing package behavior |
| Layer 3 posture | no pass-entry admission until implementation proves the method | Preserves current fail-closed behavior |
| UI posture | no UI changes from this packet | Browser surfaces remain unchanged until separately governed |

## Required Future Proof

A later implementation PR must prove:

- the registry contains the existing three methods plus `descriptive_summary`, and no other new method
- `recommend_analysis(...)` still returns the existing time-series method sequences for eligible datasets
- non-time-series or otherwise unsupported starter datasets may select `descriptive_summary` only under the new contract
- `run_analysis(..., method_name="descriptive_summary", ...)` produces deterministic artifacts, assumptions, and caveats without schema/model/migration changes
- Layer 3 pass-entry either continues to fail closed or admits `descriptive_summary` only through a separately specified Gate C rule
- existing analysis API tests and Layer 3 pass-entry tests still pass

## Stop Conditions

Stop and return to planning if implementation requires:

- changing database schema or adding a model
- adding a new source class, runtime DB write, local upload, or local directory path
- adding LLM, qualitative, hybrid, RAG, or vector behavior
- changing package/handoff/export behavior
- changing rendered UI behavior
- making `descriptive_summary` a catch-all for unsupported analysis requests instead of a deterministic, bounded method

## Relationship To Existing Docs

This freeze follows and narrows:

- `70_L3_ANALYSIS_METHOD_REGISTRY_FREEZE.md`
- `71_L3_ANALYSIS_METHOD_REGISTRY_CONTRACT.md`
- `next_milestone_plans/layer3_progress_board.md`
- `next_milestone_plans/layer3_progress_manifest.json`

It selects only the next planning boundary for one candidate method. It does not make that method live.
