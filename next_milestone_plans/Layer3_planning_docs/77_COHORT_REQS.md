# Layer 3 Descriptive Summary Cohort Requirements

Status: requirements gate for associated-cohort `descriptive_summary`; the service-only subset is live through PR `#424`/`#425`, while selected-pass cohort breadth remains future work.

This document did not by itself make associated-cohort `descriptive_summary` live, select an implementation branch, change `backend/app/services/layer3_pass_entry.py`, widen the workbench execution-start path, change UI, add schema/runtime/source behavior, or activate package, handoff, export, connector dispatch, qualitative, hybrid, RAG, vector, or full mockup behavior. PR `#424`/`#425` later implemented only the service-owned `materialize_pass_entry(...)` subset governed by docs `78`/`79`.

Follow-on docs `78_COHORT_FREEZE.md` and `79_COHORT_CONTRACT.md` select the narrow `service_materialize_only` path with the `aligned_wide_table` shape and an explicit service-owned method-selection gate. PR `#424` implements that path and PR `#425` hardens exact matching; those PRs still do not admit selected-pass cohort execution breadth.

## Current Live Boundary

Current `main` has these relevant truths:

- PR `#411` made `descriptive_summary` a lower-level `ANALYSIS_METHOD_REGISTRY` method in `backend/app/services/analysis.py`.
- PR `#417` admitted `descriptive_summary` only through the existing single-item wrapped quantitative Gate C path.
- `07_GATEC_COHORT_FREEZE.md` governs the already-landed quantitative associated-cohort path for exact-time-aligned dataset-version-backed cohorts.
- `backend/app/services/layer3_pass_entry.py` currently chooses `cross_correlation` for shaped cohorts with `observed_at` plus at least two numeric series unless exact service-owned `formation_basis_json["requested_method_name"] == "descriptive_summary"` metadata admits the PR `#424`/`#425` service path.
- `backend/app/services/layer3_pass_entry.py::execute_selected_pass_run(...)` and `backend/app/services/layer3_workbench.py` still admit selected-pass execution-start/result-status only for `single_item` pass runs.

Therefore, associated-cohort `descriptive_summary` is not a small allowlist change. It crosses both a derived-data semantics boundary and a selected-pass/source-breadth boundary.

## Required Decision 1: Cohort Data Shape

A future freeze must choose exactly one cohort input model before implementation.

Admissible options to evaluate:

- `aligned_wide_table`: reuse the existing `07_GATEC_COHORT_FREEZE.md` derived dataset-version shape: one `observed_at` column plus one numeric series column per analysis unit.
- `per_source_summary_bundle`: run or derive deterministic summaries for each source dataset version and persist a cohort-level manifest that aggregates those summaries without pretending the cohort is one time-aligned table.
- `long_source_table`: shape rows as source/member observations with explicit source identifiers, preserving uneven or non-time-series source breadth without exact timestamp intersection.

This requirements document did not select a default shape. The follow-on service freeze in `78_COHORT_FREEZE.md` selects only `aligned_wide_table` for the first service-only candidate and preserves the requirement that unaligned or non-time-series cohorts must not be coerced into misleading time-series semantics.

## Required Decision 2: Method Selection Rule

A future freeze must define when a shaped associated cohort selects `descriptive_summary` instead of the already-live cohort `cross_correlation` path.

It must answer:

- Does `descriptive_summary` apply only when the cohort cannot satisfy exact-time-aligned multivariate numeric requirements?
- Does it apply to exact-time-aligned cohorts only by explicit operator/method selection, not recommendation fallback?
- Does it summarize the derived cohort as one table, each source member independently, or both?
- What machine-readable exclusion reason is emitted when the cohort shape cannot support the selected descriptive summary contract?

The freeze must not silently prepend `descriptive_summary` ahead of `cross_correlation` for existing valid time-aligned multivariate cohorts.

## Required Decision 3: Execution Surface

A future freeze must choose the execution surface explicitly.

Allowed planning choices:

- `service_materialize_only`: admit associated-cohort `descriptive_summary` only through the older immediate `materialize_pass_entry(...)` service flow. This avoids route/UI widening but does not make the newer selected-pass workbench execution-start path support cohorts.
- `selected_pass_workbench_breadth`: widen selected-pass execution-start, result/status, and downstream result-review/package gates to support associated-cohort pass runs. This is a larger API/workbench tranche and must update `layer3_workbench.py`, API tests, and possibly rendered UI/docs.

Do not mix these choices in one implementation PR. The follow-on docs `78_COHORT_FREEZE.md` and `79_COHORT_CONTRACT.md` select `service_materialize_only` only. If workbench selected-pass breadth is later selected, it is not a docs-only or owner-service-only change and requires a separate freeze.

## Required Contract Before Implementation

Before code changes, the cohort-specific freeze must name:

- exact admitted `set_type`, `pass_type`, `pass_scope`, and `source_gate`
- selected cohort data shape and provenance manifest fields
- method selection and fallback rules
- whether `run_analysis(..., method_name="descriptive_summary", ...)` receives one derived dataset version or multiple source-derived summary artifacts
- required `L3PassRun.summary_json`, input manifest, and output manifest keys
- fail-closed exclusion reason codes
- downstream result/status/review/package compatibility expectations
- no-go surfaces and stop conditions

Minimum fail-closed reason codes to consider:

- `cohort_descriptive_shape_not_selected`
- `cohort_descriptive_source_contract_not_admitted`
- `cohort_descriptive_method_not_selected`
- `cohort_descriptive_workbench_breadth_not_admitted`
- `cohort_descriptive_manifest_incomplete`

The exact names may change in the later freeze, but the failure modes must remain machine-readable.

## Expected Touch Surfaces By Future Choice

For `service_materialize_only`:

- `backend/app/services/layer3_pass_entry.py`
- `backend/tests/test_layer3_pass_entry.py`

For `selected_pass_workbench_breadth`:

- `backend/app/services/layer3_pass_entry.py`
- `backend/app/services/layer3_workbench.py`
- adjacent API/schema tests for execution-start/result-status/review compatibility
- rendered UI tests only if the browser surface changes

No future choice may edit schema, migrations, source ingestion, runtime DB helpers, package/handoff/export behavior, connector dispatch, qualitative/hybrid/RAG/vector execution, or full mockup files unless a separate freeze admits that surface.

## Required Proof For Service Or Follow-On Implementation

Any implementation must prove:

- existing single-item `descriptive_summary` Gate C behavior remains unchanged
- existing time-aligned quantitative associated-cohort `cross_correlation` behavior remains unchanged unless explicitly and narrowly governed
- associated-cohort `descriptive_summary` succeeds only for the selected cohort data shape
- incompatible cohorts fail closed before creating unsupported execution state
- provenance links every derived summary/input field back to source `analysis_unit_id`, `material_snapshot_id`, `dataset_version_id`, and `descriptor_id`
- output manifests record `selected_method_name == "descriptive_summary"` and the expected `descriptive_summary_result` artifact family or explicitly selected summary-bundle equivalent
- selected-pass workbench APIs remain single-item-only unless the implementation freeze explicitly widens them

Minimum local proof shape:

```powershell
python -m pytest .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_executes_descriptive_summary_single_item_without_widening_scope .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_executes_quantitative_associated_cohort_with_shaped_manifest .\backend\tests\test_layer3_pass_entry.py::test_gatec_pass_entry_fails_closed_on_unsupported_cohort_recommended_method -q
```

Add new focused tests adjacent to the selected behavior before broadening to larger suites.

## Stop Conditions

Stop and return to planning if implementation requires:

- changing `analysis.py` recommendation order for existing time-series cohorts without an explicit method-selection contract
- admitting selected-pass associated-cohort execution-start without updating result/status and downstream compatibility
- hiding derived cohort provenance inside an opaque artifact
- adding schema/model/migration behavior
- adding source ingestion, local upload, local directory, connector input, runtime snapshot, public/signed URL, or generic dispatch behavior
- adding UI behavior without headed and headless browser proof
- using docs-only requirements as evidence of live behavior

## Readiness Judgment

Associated-cohort `descriptive_summary` was a valid future candidate when this requirements gate landed. The service-only candidate is now live through PR `#424`/`#425` under `78_COHORT_FREEZE.md` and `79_COHORT_CONTRACT.md`; selected-pass associated-cohort execution remains not implementation-ready and requires a separate freeze that proves downstream result/status compatibility and no-go boundaries.
