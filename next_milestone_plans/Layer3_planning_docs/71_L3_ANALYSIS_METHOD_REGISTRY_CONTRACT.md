# Layer 3 Analysis Method Registry Contract

Status: planning-only companion for `70_L3_ANALYSIS_METHOD_REGISTRY_FREEZE.md`.

This document defines the current-methods-only registry contract for the existing wrapped quantitative analysis spine. It is not an implementation and does not add methods.

## Registry Entry Shape

A future registry entry should describe each supported method with plain metadata:

| Field | Rule |
| --- | --- |
| `method_id` | Stable runtime id used by `run_analysis(...)` |
| `label` | Human-readable method name |
| `engine_family` | `wrapped_quantitative` for this packet |
| `input_scope` | Existing dataset-version and optional annotation-window scope |
| `required_dataset_features` | Time column, numeric columns, profiles, or other current prerequisites |
| `parameters` | Accepted parameter names, types, defaults, and bounds where currently enforced |
| `assumption_checks` | Current assumption families emitted by the method |
| `caveats` | Current caveat families emitted by the method |
| `artifact_types` | Current `AnalysisArtifact.artifact_type` values the method may create |
| `runner` | Existing callable or dispatcher target |
| `provenance_notes` | Source of method inputs, profile context, and output interpretation limits |

The registry must be code-owned by the analysis service or a directly adjacent support module. It must not depend on browser state, generated docs, or runtime operator text as authority.

## Current Method Entries

### `cross_correlation`

Current behavior:

- accepted through `run_analysis(..., method_name="cross_correlation", ...)`
- recommended for multivariate time-indexed datasets
- uses numeric columns except the dataset time column
- accepts `max_lag`, defaulting to `10`
- emits assumption checks for ordered time observations and stationarity profile context
- may emit caveats for interpretation, insufficient variables, or degenerate pairs
- may create `cross_correlation_result` and `cross_correlation_plot` artifacts

### `decomposition`

Current behavior:

- accepted through `run_analysis(..., method_name="decomposition", ...)`
- recommended for time-indexed data with one or more numeric variables
- uses dataset time/frequency/profile context to choose an STL period
- currently has no separately admitted operator parameter surface in the starter path
- emits assumption checks for sufficient observations, time regularity, and residual stationarity
- may emit caveats for insufficient observations, irregular time index, missing period, inferred period, or no artifacts
- may create `decomposition_components` and `decomposition_plot` artifacts

### `structural_break`

Current behavior:

- accepted through `run_analysis(..., method_name="structural_break", ...)`
- recommended after or alongside time-series decomposition/break inspection
- uses numeric time-series frames and may reuse cached decomposition residuals
- accepts current parameters:
  - `penalty`, default `8.0`
  - `minimum_segment_flag`, default `12`
  - `min_size`, default `3`
  - `model`, default `l2`
- emits assumption checks for segment length and stationarity profile context
- may emit caveats for missing time index, penalty sensitivity, model choice, insufficient observations, degenerate series, nonstationary interpretation, no breakpoints, or no artifacts
- may create `structural_break_result` and `structural_break_plot` artifacts

## Recommendation Contract

The future registry should let recommendation code derive supported method ids instead of duplicating method lists.

Current recommendation rules must remain equivalent:

- multivariate time-indexed data: `cross_correlation`, `decomposition`, `structural_break`
- single numeric time-indexed data: `decomposition`, `structural_break`
- datasets outside starter time-series assumptions: `descriptive_summary` remains a recommendation label only unless separately implemented as a real method

If future implementation discovers that `descriptive_summary` must be formalized as a supported method, stop and create a separate governance decision before treating it as executable.

## Execution Contract

The future registry implementation must preserve:

- existing `AnalysisRun` creation semantics
- existing artifact persistence helpers and storage refs
- existing assumption and caveat row families
- existing optional `annotation_window_id` scope
- existing fail/skip behavior inside method runners

Unsupported method behavior must not be broadened into silent support for new method ids. If unsupported-method behavior is tightened, that must be tested and described as a behavior change.

## API And Layer 3 Integration

Any future API or Layer 3 workbench integration may use the registry to display or validate supported method ids, but must not:

- infer execution authority from the browser
- start execution without existing plan/selection/execution gates
- widen source classes or runtime DB scope
- expose qualitative, hybrid, RAG, vector, local upload, or local directory methods
- add new package, handoff, connector, or destination behavior

## Proof Requirements

Future implementation tests should cover:

- registry contains exactly `cross_correlation`, `decomposition`, and `structural_break`
- each registry entry includes method id, parameters, prerequisites, artifacts, assumptions, and caveats
- recommendation output remains unchanged for existing tested dataset shapes
- execution dispatch reaches the same current method runners
- current analysis API tests still pass
- current Layer 3 pass-entry tests using wrapped quantitative methods still pass
- no schema/model/migration/UI/docs-overclaim drift is introduced

## Deferred Scope

Still deferred after this contract:

- any new quantitative method
- qualitative/hybrid/RAG/vector execution
- DAG orchestration, background jobs, retries, cancellation, and recovery
- plugin architecture or agent conductor
- new dependencies for method execution
- source/schema/runtime widening
- workbench UI expansion beyond already admitted execution/result/package/handoff slices
