# Layer 3 Descriptive Summary Gate C Admission Contract

Status: planning-only companion for `75_L3_DESCRIPTIVE_SUMMARY_GATEC_ADMISSION_FREEZE.md`.

This document defines the contract a future implementation must satisfy before `descriptive_summary` can be admitted through Layer 3 Gate C pass-entry. It is not an implementation and does not change pass-entry behavior.

## Admission Contract

The future implementation may admit `descriptive_summary` only when all are true:

- the analysis set is a single-item quantitative set
- the set already points to one existing `dataset_version_id`
- lower-level `recommend_analysis(...)` selects `descriptive_summary`
- the dataset version is loadable by the existing analysis service
- the pass path stays inside the existing wrapped quantitative engine family

The implementation must not admit `descriptive_summary` for associated cohorts, qualitative sets, multi-source sets, local upload/directory sources, connector sources, runtime snapshots, or derived package/handoff/export artifacts.

## Pass-Entry Contract

The planned pass and persisted `L3PassRun` must keep the current single-item shape:

- `pass_type`: `single_item`
- `engine_family`: `wrapped_quantitative_analysis`
- `pass_scope`: current single-item dataset-version pass scope
- `dataset_version_id`: the existing dataset version selected by Gate C
- `selected_method_name`: `descriptive_summary`
- no new row family, schema field, migration, source table, package table, or runtime table

The implementation may update only the method allowlist/selection checks needed for that existing shape.

## Execution Contract

Execution must reuse the existing selected-pass execution path:

- selected pass starts from `selected_not_started`
- `execute_selected_pass_run(...)` calls `run_analysis(...)` with `method_name="descriptive_summary"`
- the lower-level analysis service creates `descriptive_summary_result` JSON artifacts and assumption/caveat rows
- pass output metadata records the analysis run id, artifact refs, caveat/warning state, and completion status consistently with existing wrapped quantitative passes

The implementation must not create rendered UI state, package/handoff/export state, connector dispatch state, public/signed URL state, source-ingestion state, or runtime snapshot state.

## Cohort Boundary

Associated-cohort `descriptive_summary` remains blocked.

Reasons:

- the cohort path shapes multiple source dataset versions into a derived dataset
- current cohort admission is tied to `observed_at` alignment and multivariate numeric data
- allowing non-time-series descriptive summaries over derived cohorts would change the source-breadth and derived-dataset contract

A later cohort-specific freeze would need to name the derived-data semantics, provenance, manifests, failure behavior, and downstream package/review compatibility separately.

## Proof Requirements

Future implementation tests must cover:

- single-item materialization creates one pass run with `selected_method_name == "descriptive_summary"`
- execution creates one lower-level `AnalysisRun` for `descriptive_summary`
- pass output metadata includes the `descriptive_summary_result` artifact family
- caveats/warnings from lower-level descriptive summaries propagate into pass status consistently with existing wrapped quantitative execution
- associated-cohort `descriptive_summary` remains fail-closed
- existing single-item time-series and cohort time-series tests still pass
- existing unsupported/no-admissible-set tests still pass

Recommended focused command shape:

```powershell
python -m pytest .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_executes_quantitative_single_item_and_preserves_loading_closure .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_executes_quantitative_associated_cohort_with_shaped_manifest .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_fails_closed_on_unsupported_cohort_recommended_method -q
```

The future implementation should add new focused tests adjacent to the changed behavior before broadening the suite.

## Non-Goals

Still deferred:

- associated-cohort admission
- UI controls or route expansion
- source/runtime/schema widening
- package/handoff/export/download behavior
- connector dispatch, destination selection, public/signed URLs, or generic downstream dispatch
- qualitative/hybrid/RAG/vector/LLM execution
- full mockup activation

## Adequacy Check

The implementation is adequate only if a reviewer can verify that the change is equivalent to "allow the already-live lower-level method through the already-live single-item pass-entry path" and nothing broader.
