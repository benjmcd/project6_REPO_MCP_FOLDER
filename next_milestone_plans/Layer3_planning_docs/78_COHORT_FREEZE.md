# Layer 3 Descriptive Summary Cohort Service Freeze

Status: service-only associated-cohort `descriptive_summary` freeze; satisfied on current `main` by PR `#424` and exact-gate hardening in PR `#425`.

This document did not by itself make associated-cohort `descriptive_summary` live, change `backend/app/services/layer3_pass_entry.py`, widen selected-pass workbench execution, change API, change UI, add schema/runtime/source behavior, or activate package, handoff, export, connector dispatch, qualitative, hybrid, RAG, vector, or full mockup behavior. PR `#424`/`#425` implement only the service-owned path admitted here.

## Decision

This freeze selects exactly one path from `77_COHORT_REQS.md`:

- cohort data shape: `aligned_wide_table`
- execution surface: `service_materialize_only`
- method-selection gate: explicit service-owned request metadata on `L3AnalysisSet.formation_basis_json["requested_method_name"] == "descriptive_summary"`
- owner module for the implementation: `backend/app/services/layer3_pass_entry.py`
- proof file for the implementation: `backend/tests/test_layer3_pass_entry.py`

No selected-pass workbench breadth is admitted by this freeze.
No route, API DTO, rendered UI, schema, migration, runtime DB, source ingestion, package, handoff, export, connector, qualitative, hybrid, RAG, vector, or full mockup surface is admitted by this freeze.

## Current Live Boundary

Current repo authority for this live-state sync was checked against `project6-origin/main` at `7c93bebb`.

Live facts this freeze must preserve:

- PR `#411` added lower-level `descriptive_summary` support in `backend/app/services/analysis.py`.
- PR `#417` admitted `descriptive_summary` only through the existing single-item Gate C path.
- PR `#422` added `77_COHORT_REQS.md` as requirements-only governance for associated-cohort `descriptive_summary` work.
- `07_GATEC_COHORT_FREEZE.md` governs the already-live exact-time-aligned quantitative associated-cohort path.
- `backend/app/services/layer3_pass_entry.py` currently selects `cross_correlation` for shaped quantitative cohorts that have `observed_at` plus at least two numeric series.
- `backend/app/services/layer3_pass_entry.py::execute_selected_pass_run(...)` admits only `single_item` selected-pass execution.
- `backend/app/services/layer3_workbench.py` rejects non-`single_item` execution-start and result/status source breadth.

Therefore, this freeze must not silently reinterpret existing valid cohorts as `descriptive_summary` cohorts.

## Frozen Admission

The implementation governed by this freeze may admit associated-cohort `descriptive_summary` only when all are true:

- `analysis_set.set_type == "associated_cohort"`
- `analysis_set.formation_basis_json["analysis_modality"] == "quantitative"`
- `analysis_set.formation_basis_json["requested_method_name"] == "descriptive_summary"`
- the cohort satisfies the exact `07_GATEC_COHORT_FREEZE.md` aligned wide-table shape
- each member unit has exactly one dataset-version-backed material snapshot
- each source dataset version is loadable
- each source contributes exactly one admitted non-time numeric measure series
- exact UTC `observed_at` intersection creates a non-empty derived dataset
- the implementation preserves column-to-unit provenance in the input manifest and pass summary

If `requested_method_name` is absent, empty, not exactly `descriptive_summary`, or supplied from any ungoverned location, the implementation must preserve current behavior. Existing valid associated cohorts must continue to select `cross_correlation`.

## Frozen Service Surface

The only admitted execution surface is the immediate service flow:

- `materialize_pass_entry(db, session_id=...)`
- `backend/app/services/layer3_pass_entry.py`
- `backend/tests/test_layer3_pass_entry.py`

The implementation must not use selected-pass workbench execution as a shortcut.
It must not touch `backend/app/services/layer3_workbench.py`.
It must not add route/API/UI method-selection controls in the same tranche.

## Provenance And Manifest Requirements

The implementation must reuse the existing derived dataset-version posture from `07_GATEC_COHORT_FREEZE.md` and record at minimum:

- `selected_method_name == "descriptive_summary"`
- `requested_method_name == "descriptive_summary"`
- `requested_method_source == "analysis_set.formation_basis_json.requested_method_name"`
- `cohort_shape == "aligned_wide_table"`
- `derived_dataset_version_id`
- `source_dataset_version_ids_json`
- `column_map_json`
- `analysis_unit_id`
- `material_snapshot_id`
- `dataset_version_id`
- `descriptor_id`
- `pass_scope == "quantitative_associated_cohort_dataset_version"`
- output `artifact_types_json == ["descriptive_summary_result"]`

The derived dataset version remains execution context only.
It does not replace Layer 3 unit, snapshot, set, plan, or pass truth.

## Fail-Closed Requirements

Any implementation or follow-up hardening under this freeze must use machine-readable failure or exclusion reasons. Minimum names:

- `cohort_descriptive_method_not_requested`
- `cohort_descriptive_method_source_not_admitted`
- `cohort_descriptive_shape_not_admitted`
- `cohort_descriptive_source_contract_not_admitted`
- `cohort_descriptive_manifest_incomplete`
- `cohort_descriptive_workbench_breadth_not_admitted`

Unsupported associated-cohort `descriptive_summary` requests must fail closed before creating unsupported `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, package, handoff, export, route, UI, schema, runtime, or source-ingestion state.

## Required Proof

Any implementation PR governed by this freeze must prove:

- existing single-item `descriptive_summary` Gate C materialization still passes
- existing single-item selected-pass `descriptive_summary` execution still passes
- existing exact-aligned associated-cohort `cross_correlation` materialization remains unchanged when no explicit `requested_method_name == "descriptive_summary"` is present
- an explicit service-only associated-cohort `descriptive_summary` request succeeds through `materialize_pass_entry(...)`
- malformed, absent, or non-explicit method-selection metadata does not select associated-cohort `descriptive_summary`
- incompatible cohort shape/source/provenance fails closed before unsupported execution state is created
- selected-pass workbench execution-start and result/status remain single-item-only

Minimum focused command shape:

```powershell
python -m pytest .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_executes_descriptive_summary_single_item_without_widening_scope .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_selected_pass_execution_runs_descriptive_summary .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_executes_quantitative_associated_cohort_with_shaped_manifest .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_fails_closed_on_unsupported_cohort_recommended_method -q
```

Implementation and hardening PRs under this freeze must add or preserve the cohort-specific positive and negative tests next to those existing tests before broadening to larger suites.

## Stop Conditions

Stop and return to planning if implementation requires:

- changing `backend/app/services/analysis.py` recommendation order
- treating `descriptive_summary` as the default for existing valid exact-aligned cohorts
- editing `backend/app/services/layer3_workbench.py`
- widening selected-pass execution-start or result/status to associated cohorts
- adding API, route, rendered UI, browser control, schema, migration, runtime DB, source ingestion, package, handoff, export, connector, qualitative, hybrid, RAG, vector, or full mockup behavior
- accepting method selection from an ungoverned request field or inferred recommendation fallback
- hiding column-to-unit provenance in an opaque artifact
- using this freeze document alone as evidence of live behavior without the merged PR `#424`/`#425` implementation proof

## Readiness Judgment

This freeze was implementation-entry governance for the smallest safe associated-cohort `descriptive_summary` tranche.
PR `#424`/`#425` satisfy only that service-owned path. Any further code-bearing step, including selected-pass cohort breadth, requires a separate freeze unless it is narrow hardening inside `backend/app/services/layer3_pass_entry.py` and `backend/tests/test_layer3_pass_entry.py` that preserves the explicit method-selection gate and all no-go surfaces above.
