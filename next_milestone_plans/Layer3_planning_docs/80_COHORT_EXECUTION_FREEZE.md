# Layer 3 Cohort Execution Freeze

Status: planning-only freeze for a future selected-pass associated-cohort `descriptive_summary` execution-start and result/status tranche.

This document does not change code, admit selected-pass cohort execution, change API/UI behavior, widen schema/runtime/source scope, or activate result review, package, handoff, export, connector, qualitative, hybrid, RAG, vector, or full mockup behavior. PR `#424`/`#425` remain the only live associated-cohort `descriptive_summary` path, and only through service-owned `materialize_pass_entry(...)`.

## Decision

This freeze selects the next possible selected-pass cohort breadth as:

- cohort data shape: `aligned_wide_table`
- method: `descriptive_summary`
- execution surface: existing selected-pass `/api/v1/layer3/execution/start`
- inspection surface: existing read-only `/api/v1/layer3/execution/result/status`
- owner services: `backend/app/services/layer3_pass_entry.py` and `backend/app/services/layer3_workbench.py`
- proof files: `backend/tests/test_layer3_pass_entry.py` and `backend/tests/test_layer3_api.py`

No route, rendered UI, schema, migration, runtime DB, source ingestion, result-review, package, handoff, export, connector, qualitative, hybrid, RAG, vector, or full mockup surface is admitted by this freeze.

## Current Live Boundary

Current repo authority for this planning branch was checked against `project6-origin/main` at `e6ef73f1`.

Live facts this freeze must preserve:

- PR `#411` makes `descriptive_summary` a lower-level analysis method.
- PR `#417` admits only single-item `descriptive_summary` through Gate C selected-pass execution.
- PR `#424`/`#425` admit only service-owned associated-cohort `descriptive_summary` through `materialize_pass_entry(...)` with exact `formation_basis_json["requested_method_name"] == "descriptive_summary"` metadata.
- `backend/app/services/layer3_pass_entry.py::execute_selected_pass_run(...)` currently rejects planned pass types outside `single_item`.
- `backend/app/services/layer3_workbench.py` currently rejects non-`single_item` pass types in both execution-start and result/status.
- `backend/tests/test_layer3_pass_entry.py::test_gatec_pass_entry_selected_pass_execution_still_rejects_associated_cohort` proves the current blocked boundary.

## Admission Requirements

A future implementation governed by this freeze may start one selected associated-cohort pass only when all are true:

- `L3PassRun.status == "selected_not_started"`
- `L3PassRun.engine_family == "wrapped_quantitative_analysis"`
- approved planned pass and pass-run summary both trace to the current session, approved plan, preview id, and preview hash
- `planned_pass["pass_type"] == "associated_cohort"`
- `planned_pass["pass_scope"] == "quantitative_associated_cohort_dataset_version"`
- `planned_pass["selected_method_name"] == "descriptive_summary"`
- method admission traces back to exact service-owned `formation_basis_json["requested_method_name"] == "descriptive_summary"` metadata, not a UI field, route field, inferred recommendation, or pass-run-only summary value
- the input payload and manifests preserve the aligned wide-table source-to-derived-column provenance required by docs `78`/`79`

If any condition is absent, malformed, or inconsistent, execution-start must fail closed before creating a new `AnalysisRun` or output metadata.

## Result/Status Requirements

The same tranche may widen read-only result/status only enough to inspect a terminal selected associated-cohort `descriptive_summary` pass produced by the admitted execution-start path.

Result/status must:

- remain `status_only`
- remain read-only
- require prior selected-pass execution-start state
- require readable output metadata
- preserve current single-item result/status behavior unchanged
- fail closed for associated-cohort pass runs not produced by the admitted selected-pass execution-start path

## No-Go

This freeze does not admit:

- selected-pass associated-cohort result review
- package-review preview, package construction, package-review submit, handoff, export, or download behavior for associated cohorts
- rendered UI controls or browser behavior
- schema, migration, runtime DB, or source-ingestion changes
- `cross_correlation` default changes for valid associated cohorts without exact descriptive metadata
- method selection from client request fields, route parameters, UI state, pass-run summary alone, or fallback order
- qualitative, hybrid, RAG, vector, LLM, agent, retry, cancellation, or full mockup behavior

## Required Proof

Any implementation PR governed by this freeze must add focused tests proving:

- current single-item selected-pass `descriptive_summary` execution still works
- current service-owned associated-cohort `materialize_pass_entry(...)` `descriptive_summary` still works
- current associated-cohort `cross_correlation` materialization still works when exact descriptive metadata is absent
- selected-pass execution-start succeeds for one admitted associated-cohort `descriptive_summary` pass with complete provenance
- selected-pass execution-start fails closed before creating `AnalysisRun` when method metadata, pass scope, provenance, preview identity, or plan/pass-run binding is invalid
- selected-pass result/status can inspect only admitted terminal associated-cohort `descriptive_summary` execution output
- result review, package, handoff, export, UI, schema, runtime, and source surfaces remain unchanged

Minimum local proof shape:

```powershell
python -m pytest .\backend\tests\test_layer3_pass_entry.py .\backend\tests\test_layer3_api.py -q
```

Run browser tests only if a future implementation touches rendered UI; UI is no-go under this freeze.

## Stop Conditions

Stop and create a new freeze if implementation requires:

- editing frontend/static UI files
- adding or changing API request fields beyond accepting the existing selected pass references
- creating new schema, model, migration, runtime DB, or source-ingestion behavior
- making associated-cohort result review, package, handoff, export, or download live
- changing package/handoff/export downstream assumptions to accept associated cohorts in the same tranche
- accepting method selection from any source other than the governed service-owned metadata
- weakening the current single-item protections for unrelated selected-pass execution
