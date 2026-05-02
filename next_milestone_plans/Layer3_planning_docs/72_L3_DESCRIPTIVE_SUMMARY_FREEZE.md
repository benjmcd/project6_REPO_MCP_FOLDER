# Layer 3 Descriptive Summary Freeze

Status: governance freeze implemented by PR `#411` for lower-level analysis API support, with single-item Gate C admission separately implemented by PR `#417`.

This document froze the smallest safe boundary for deciding whether the existing `descriptive_summary` recommendation label could become a real supported wrapped quantitative method. PR `#411` implemented only the admitted lower-level analysis-service tranche: `descriptive_summary` is now in `ANALYSIS_METHOD_REGISTRY` and executable through `run_analysis(...)` as a deterministic JSON-artifact method. PR `#417` later admitted that already-live method only through the existing single-item Layer 3 Gate C pass-entry path. Neither PR admitted associated-cohort `descriptive_summary`, workbench UI, schema/runtime/source scope, package, handoff, export, connector dispatch, or qualitative/hybrid/RAG/vector behavior.

## Current Live Boundary After PR `#411` And PR `#417`

Current `main` has a bounded four-method analysis registry plus single-item `descriptive_summary` Gate C admission while associated-cohort and broader pass-entry remain fail-closed:

- `backend/app/services/analysis.py` supports exactly `cross_correlation`, `decomposition`, `structural_break`, and `descriptive_summary` through `ANALYSIS_METHOD_REGISTRY`.
- `recommend_analysis(...)` still returns the existing time-series method sequences for eligible datasets and returns `descriptive_summary` only when a dataset does not meet the starter time-series assumptions.
- `run_analysis(..., method_name="descriptive_summary", ...)` now dispatches a bounded deterministic runner that emits one `descriptive_summary_result` JSON artifact plus assumption/caveat rows.
- `backend/app/services/layer3_pass_entry.py` now admits `descriptive_summary` only through the existing single-item wrapped quantitative Gate C path; associated-cohort `descriptive_summary` and unknown methods remain fail-closed before creating unsupported plan/pass/run state.
- `backend/tests/test_layer3_pass_entry.py` proves single-item `descriptive_summary` materialization/execution and preserves associated-cohort fail-closed behavior.

## Problem Statement

The repo already named `descriptive_summary` as a fallback recommendation label. Treating that label as executable without governance would have blurred three boundaries at once: method admission, non-time-series dataset handling, and Layer 3 pass-entry eligibility. This freeze supplied the precise method contract that PR `#411` used for lower-level analysis-service admission while keeping Layer 3 pass-entry eligibility separately blocked.

## Slice Decision

The next safe planning boundary is:

> Freeze `descriptive_summary` as a future single-method wrapped quantitative expansion candidate, limited to deterministic summary statistics over an existing dataset version, without source/schema/runtime/UI widening.

This was intentionally governance first. It selected a concrete method-expansion candidate while preserving Layer 3 admission as a separate decision. PR `#417` later satisfied only the single-item Gate C admission decision; associated-cohort and broader admission still require separate governance.

## Implemented Scope Landed By PR `#411`

PR `#411` added only:

- one `descriptive_summary` registry entry in the existing analysis-method registry
- one deterministic runner for existing dataset-version data already loadable through `load_version_dataframe(...)`
- summary artifacts derived from existing columns, row counts, missingness, numeric distributions, categorical counts, and optional time-column coverage
- assumption and caveat rows for data availability, column typing, missingness, high cardinality, and non-time-series interpretation limits
- focused API tests proving the new method is admitted only where the lower-level contract allows it

## Explicit Non-Goals

This freeze and PR `#411` still do not admit:

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
| Layer 3 posture | lower-level method first, then separately governed single-item Gate C admission | Preserves fail-closed behavior for associated-cohort and broader admission |
| UI posture | no UI changes from this packet | Browser surfaces remain unchanged until separately governed |

## Proof Landed By PR `#411`

PR `#411` proved:

- the registry contains the existing three methods plus `descriptive_summary`, and no other new method
- `recommend_analysis(...)` still returns the existing time-series method sequences for eligible datasets
- non-time-series or otherwise unsupported starter datasets may select `descriptive_summary` only under the new contract
- `run_analysis(..., method_name="descriptive_summary", ...)` produces deterministic artifacts, assumptions, and caveats without schema/model/migration changes
- PR `#417` separately proves single-item Gate C pass-entry admission for `descriptive_summary`
- associated-cohort and broader `descriptive_summary` pass-entry still fail closed unless a separately specified Gate C rule later admits them
- focused analysis API tests, single-item Gate C admission tests, and associated-cohort fail-closed tests still pass

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

It selected only the first bounded implementation boundary for one candidate method. PR `#411` made only the lower-level analysis API method live, and PR `#417` later made only single-item Gate C pass-entry live. Associated-cohort Gate C admission, UI, source/runtime/schema, package, handoff, export, connector dispatch, qualitative/hybrid/RAG/vector execution, and full mockup behavior remain deferred.
