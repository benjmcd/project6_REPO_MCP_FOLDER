# Layer 3 Descriptive Summary Cohort Service Contract

Status: implementation contract for the service-only cohort path frozen by `78_COHORT_FREEZE.md`; satisfied on current `main` by PR `#424` and exact-gate hardening in PR `#425`.

This document did not by itself create live behavior. It does not change route/API behavior, selected-pass workbench breadth, UI, schema, runtime, source ingestion, package, handoff, export, connector dispatch, qualitative, hybrid, RAG, vector, or full mockup behavior. PR `#424`/`#425` implement only the service-owned path described here.

## Contract Scope

This contract governs only the associated-cohort `descriptive_summary` implementation in the immediate `materialize_pass_entry(...)` service flow.

The implementation and any narrow hardening under this contract may touch only:

- `backend/app/services/layer3_pass_entry.py`
- `backend/tests/test_layer3_pass_entry.py`

Any required touch outside those files is a stop condition unless a new freeze admits the wider surface first.

## Admission Contract

The implementation may create a `descriptive_summary` associated-cohort pass only for this exact contract:

- `set_type`: `associated_cohort`
- `analysis_modality`: `quantitative`
- `pass_type`: `associated_cohort`
- `engine_family`: `wrapped_quantitative_analysis`
- `pass_scope`: `quantitative_associated_cohort_dataset_version`
- `source_gate`: `78_COHORT_FREEZE`
- `cohort_shape`: `aligned_wide_table`
- `requested_method_name`: `descriptive_summary`
- `requested_method_source`: `analysis_set.formation_basis_json.requested_method_name`
- `selected_method_name`: `descriptive_summary`

The implementation must read method selection only from `L3AnalysisSet.formation_basis_json["requested_method_name"]`.
It must not infer associated-cohort `descriptive_summary` from `recommend_analysis(...)`, planned-pass JSON, pass-run summary JSON, client request fields, UI state, route parameters, or fallback order.

## Default Behavior Contract

Existing associated-cohort behavior remains the default.

When `requested_method_name` is absent or not exactly `descriptive_summary`:

- valid exact-time-aligned quantitative cohorts must continue to select `cross_correlation`
- invalid cohorts must keep the existing fail-closed behavior
- no `descriptive_summary` pass may be planned, persisted, or executed

This is the main safety boundary. The implementation must prove it with tests.

## Data Shape Contract

The selected shape is the `07_GATEC_COHORT_FREEZE.md` aligned wide-table shape:

- one `observed_at` column
- one numeric measure column per admitted analysis unit
- exact UTC timestamp intersection only
- no interpolation
- no resampling
- no gap filling
- no imputation
- no heuristic multi-measure selection

The implementation must not add `per_source_summary_bundle` or `long_source_table` behavior under this contract.

## Planning And Execution Contract

For an admitted explicit cohort `descriptive_summary` request, the implementation must:

1. shape the cohort through the existing derived dataset-version path
2. persist the input manifest before execution
3. create one `L3PassRun` for the associated cohort
4. call `run_analysis(..., method_name="descriptive_summary", ...)` on the derived dataset version
5. persist output metadata with the `descriptive_summary_result` artifact family
6. preserve existing session loading-closure summary fields

The pass summary and output manifest must include:

- `selected_method_name == "descriptive_summary"`
- `artifact_types_json == ["descriptive_summary_result"]`
- `derived_dataset_version_id`
- `source_dataset_version_ids_json`
- `column_map_json`
- `cohort_shape == "aligned_wide_table"`
- `requested_method_name == "descriptive_summary"`
- `requested_method_source == "analysis_set.formation_basis_json.requested_method_name"`

The input manifest must include enough source lineage to trace every derived column to:

- `analysis_unit_id`
- `material_snapshot_id`
- `dataset_version_id`
- `descriptor_id`
- source variable name
- derived column name

## Failure Contract

The implementation must fail closed before unsupported execution state is created when:

- method selection is missing, empty, implicit, or not from `formation_basis_json["requested_method_name"]`
- the cohort is not quantitative
- the cohort has fewer than two units
- any unit lacks exactly one dataset-version-backed material snapshot
- any source dataset version is missing or unreadable
- exact timestamp alignment is empty
- column provenance is incomplete
- selected-pass workbench execution is attempted for an associated cohort

Minimum reason codes:

- `cohort_descriptive_method_not_requested`
- `cohort_descriptive_method_source_not_admitted`
- `cohort_descriptive_shape_not_admitted`
- `cohort_descriptive_source_contract_not_admitted`
- `cohort_descriptive_manifest_incomplete`
- `cohort_descriptive_workbench_breadth_not_admitted`

The implementation may retain existing non-descriptive cohort reason codes where they are more precise, but it must not blur explicit descriptive-selection failures into generic success or unsupported-method behavior after state has been created.

## No-Go Contract

This contract does not admit:

- selected-pass associated-cohort execution-start
- selected-pass associated-cohort result/status
- `backend/app/services/layer3_workbench.py` edits
- route/API DTO changes
- rendered UI or browser controls
- schema/model/migration changes
- runtime DB writes
- source ingestion or connector-source behavior
- package, handoff, export, download, or dispatch behavior
- qualitative, hybrid, RAG, vector, or LLM execution
- full mockup activation
- changing `analysis.py` method recommendation order

## Required Test Contract

Implementation code must add or preserve focused tests proving:

- single-item `descriptive_summary` materialization still works
- single-item selected-pass `descriptive_summary` execution still works
- current associated-cohort `cross_correlation` materialization still works without explicit requested method metadata
- explicit service-only associated-cohort `descriptive_summary` materialization works with complete provenance
- malformed or absent method metadata does not select associated-cohort `descriptive_summary`
- incompatible cohort shape/source/provenance fails closed before creating plan/pass/run/analysis state
- selected-pass workbench source-breadth rejection remains unchanged

After focused tests pass, run the full `backend/tests/test_layer3_pass_entry.py` file.
Run API or browser suites only if the implementation touches API, route, UI, or workbench surfaces; those touches are no-go under this contract unless separately frozen first.

## Completion Criteria

An implementation satisfies this contract only if a reviewer can verify all of the following:

- associated-cohort `descriptive_summary` is reachable only through explicit service-owned metadata
- existing valid cohorts still default to `cross_correlation`
- selected-pass workbench breadth remains single-item-only
- manifests preserve source-to-derived-column provenance
- no no-go surface changed
- local focused and full owner-service tests pass

If any item cannot be proven, the implementation must stop before merge.
