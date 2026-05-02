# Layer 3 Cohort Execution Contract

Status: planning-only implementation contract for the selected-pass associated-cohort execution breadth frozen by `80_COHORT_EXECUTION_FREEZE.md`.

This document is not live behavior. It does not change API/UI behavior, selected-pass cohort execution, schema, runtime, source ingestion, result review, package, handoff, export, connector dispatch, qualitative, hybrid, RAG, vector, or full mockup behavior.

## Contract Scope

This contract governs only a future backend/API implementation that widens existing selected-pass execution-start and result/status from `single_item` to the admitted associated-cohort `descriptive_summary` case.

The future implementation may touch only:

- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_pass_entry.py`
- `backend/tests/test_layer3_api.py`

Any required touch outside those files is a stop condition unless a new freeze admits the wider surface first.

## Execution-Start Contract

A future implementation may execute a selected associated-cohort pass only for this exact contract:

- `pass_type`: `associated_cohort`
- `pass_scope`: `quantitative_associated_cohort_dataset_version`
- `engine_family`: `wrapped_quantitative_analysis`
- `selected_method_name`: `descriptive_summary`
- `cohort_shape`: `aligned_wide_table`
- `method_source`: `analysis_set.formation_basis_json.requested_method_name`
- `requested_method_name`: exactly `descriptive_summary`
- `execution_surface`: `/api/v1/layer3/execution/start`
- `result_status_surface`: `/api/v1/layer3/execution/result/status`

The implementation must verify the approved planned pass, pass-run row, pass-run summary, source preview id/hash, approved plan id, and analysis set metadata agree before creating `AnalysisRun`.

## Result/Status Contract

Result/status may read selected associated-cohort `descriptive_summary` output only when:

- the pass run was executed by the admitted selected-pass execution-start path
- the pass run is terminal
- output metadata is present and readable
- selected method, pass type, pass scope, preview identity, and plan identity match the approved planned pass

Result/status must not create or mutate analysis, result-review, package, handoff, export, or UI state.

## Failure Contract

The implementation must fail closed before creating unsupported execution state when:

- method metadata is absent, malformed, trimmable, or not exactly `descriptive_summary`
- method metadata comes from an ungoverned source
- pass type or pass scope is not the admitted associated-cohort scope
- pass-run identity, approved plan identity, preview identity, or session identity does not match
- aligned wide-table provenance is missing or inconsistent
- result/status is requested before admitted execution-start state exists
- downstream result-review/package/handoff/export behavior is attempted in the same tranche

New or preserved failure reasons must distinguish source-breadth rejection, method-source rejection, method-name rejection, provenance rejection, and downstream-surface rejection.

## No-Go Contract

This contract does not admit:

- UI controls or browser behavior
- new route fields, DTO widening, or OpenAPI request-shape widening beyond existing selected-pass references
- selected-pass associated-cohort result review
- package-review preview, package construction, package-review submit, handoff, export, or download behavior
- schema, model, migration, runtime DB, or source-ingestion changes
- changing the default `cross_correlation` behavior for valid cohorts without exact descriptive metadata
- method selection from route request JSON, UI state, pass-run summary alone, or fallback order
- qualitative, hybrid, RAG, vector, LLM, agent, retry, cancellation, or full mockup behavior

## Required Test Contract

Future code must add or preserve focused tests proving:

- single-item selected-pass execution and result/status remain unchanged
- service-owned associated-cohort `materialize_pass_entry(...)` remains unchanged
- selected-pass associated-cohort execution-start succeeds only for the exact admitted `descriptive_summary` contract
- selected-pass associated-cohort result/status succeeds only after admitted terminal execution output
- malformed method metadata, wrong method source, wrong pass scope, missing provenance, mismatched preview, or mismatched plan fails closed before creating `AnalysisRun`
- result review, package, handoff, export, UI, schema, runtime, and source surfaces remain unavailable

After focused tests pass, run the full owner files:

```powershell
python -m pytest .\backend\tests\test_layer3_pass_entry.py .\backend\tests\test_layer3_api.py -q
```

## Completion Criteria

An implementation satisfies this contract only if a reviewer can verify:

- selected-pass cohort execution is reachable only for exact service-owned `descriptive_summary` metadata
- current single-item selected-pass behavior is unchanged
- current service-only associated-cohort materialization is unchanged
- result/status remains read-only and limited to admitted terminal execution output
- all no-go surfaces remain unchanged
- focused owner-file tests and CI pass
