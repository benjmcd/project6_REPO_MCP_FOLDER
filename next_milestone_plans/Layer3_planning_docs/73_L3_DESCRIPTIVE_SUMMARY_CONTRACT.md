# Layer 3 Descriptive Summary Contract

Status: contract companion for `72_L3_DESCRIPTIVE_SUMMARY_FREEZE.md`, partially satisfied by PR `#411`.

This document defines the contract the PR `#411` lower-level `descriptive_summary` implementation satisfies before the existing recommendation label becomes a real supported analysis method. The contract still does not admit Layer 3 Gate C pass-entry, UI, schema/runtime/source, package, handoff, export, connector dispatch, qualitative/hybrid/RAG/vector, or full mockup behavior.

## Registry Entry Shape

The current registry entry describes `descriptive_summary` with the same plain metadata shape used by the existing method registry:

| Field | Rule |
| --- | --- |
| `method_id` | `descriptive_summary` |
| `label` | `Descriptive summary` |
| `engine_family` | `wrapped_quantitative` |
| `input_scope` | existing dataset version with optional annotation-window scope only if already supported by the analysis spine |
| `required_dataset_features` | loadable dataset frame with at least one data column |
| `parameters` | empty unless a separate implementation packet proves a deterministic, bounded parameter |
| `assumption_checks` | data availability, column classification, missingness, and optional time-column coverage |
| `caveats` | high missingness, high cardinality, unsupported nested values, non-time-series interpretation limits, and empty/degenerate data |
| `artifact_types` | deterministic JSON summary artifact; plot artifacts are not admitted by this planning packet |
| `runner` | existing analysis-service callable or dispatcher target owned adjacent to current method runners |

The registry entry is code-owned by `backend/app/services/analysis.py`. It must not depend on browser state, generated docs, runtime operator text, external connectors, or LLM output as authority.

## Method Semantics

The method may summarize only the already-loaded dataset frame:

- row count and column count
- column names and inferred primitive column classes
- missing-value counts and percentages
- numeric column min, max, mean, median, standard deviation, and non-null counts
- categorical or text-like top-value counts bounded to a small deterministic limit
- boolean counts when applicable
- time-column coverage if the dataset already declares a time column

The method must not infer causal claims, generate narrative analysis, call external services, retrieve additional documents, mutate source data, or treat missing prerequisite data as success.

## Recommendation Contract

Current recommendation behavior is:

- multivariate time-indexed data: `cross_correlation`, `decomposition`, `structural_break`
- single numeric time-indexed data: `decomposition`, `structural_break`
- datasets outside starter time-series assumptions: `descriptive_summary` as the bounded lower-level analysis method

PR `#411` formalized that fallback into a supported lower-level analysis method because:

- existing time-series recommendation sequences remain unchanged
- `descriptive_summary` is not prepended to every recommendation by default
- the fallback rationale remains explicit that the dataset does not meet starter time-series assumptions
- unsupported or empty datasets still fail closed or emit high-severity caveats instead of silent success

## Execution Contract

The runner must preserve:

- existing `AnalysisRun` creation semantics
- existing artifact persistence helpers and storage refs
- existing `AssumptionCheck` and `CaveatNote` row families
- existing optional `annotation_window_id` scope if the current analysis spine supports it
- current fail-closed Layer 3 behavior until Layer 3 pass-entry admission is separately specified

The runner may create only deterministic artifacts from local dataframe content. It must not create package, handoff, connector, destination, public/signed URL, runtime snapshot, migration, or UI state.

## Layer 3 Integration

Layer 3 pass-entry integration must be explicit. PR `#411` uses the first safe option; the second remains a future option only after separate governance:

- keep Layer 3 pass-entry fail-closed for `descriptive_summary` while making the method available only through the lower-level analysis API
- separately govern a Gate C admission rule that allows `descriptive_summary` pass creation for a named dataset class and proves package/review/handoff downstream compatibility

Do not silently allow `descriptive_summary` through `materialize_pass_entry(...)` just because the method exists in the registry.

## Proof Requirements

PR `#411` implementation tests cover:

- registry contains exactly `cross_correlation`, `decomposition`, `structural_break`, and `descriptive_summary`
- existing registry metadata for the current three methods remains unchanged
- recommendation output remains unchanged for existing time-series dataset shapes
- non-time-series recommendation can select `descriptive_summary` under the contract
- execution creates deterministic JSON artifacts and bounded assumption/caveat rows
- unsupported/empty/degenerate input remains explicit and fail-closed or high-caveat
- current Layer 3 pass-entry fail-closed tests are preserved unless a separate Gate C packet changes them
- no schema/model/migration/UI/source/runtime widening is introduced

## Deferred Scope

Still deferred after this contract:

- Layer 3 Gate C admission for `descriptive_summary`
- any other quantitative method
- qualitative/hybrid/RAG/vector execution
- LLM-generated narrative summaries
- source-breadth expansion, local upload, local directory, connector input, or runtime snapshot writes
- schema/model/migration changes
- workbench UI expansion beyond already admitted execution/result/package/handoff slices
- package/handoff/export/download behavior
