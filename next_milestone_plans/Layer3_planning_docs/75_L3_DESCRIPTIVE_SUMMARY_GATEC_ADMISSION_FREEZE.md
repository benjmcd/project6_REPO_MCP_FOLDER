# Layer 3 Descriptive Summary Gate C Admission Freeze

Status: planning-only governance for a future `descriptive_summary` Gate C admission implementation.

This document freezes the smallest safe Layer 3 pass-entry boundary after PR `#411` made `descriptive_summary` live only as a lower-level analysis API method. It does not implement Gate C admission, change `SUPPORTED_WRAPPED_QUANTITATIVE_METHODS`, create pass/run state, change execution-start behavior, change UI, widen schema/runtime/source scope, or activate package, handoff, export, connector dispatch, qualitative, hybrid, RAG, vector, or full mockup behavior.

## Current Live Boundary

Current `main` has two distinct truths:

- `backend/app/services/analysis.py` supports `descriptive_summary` through `ANALYSIS_METHOD_REGISTRY` and `run_analysis(...)`.
- `backend/app/services/layer3_pass_entry.py` still rejects `descriptive_summary` before Layer 3 pass/run state because `SUPPORTED_WRAPPED_QUANTITATIVE_METHODS` includes only `cross_correlation`, `decomposition`, and `structural_break`.
- `execute_selected_pass_run(...)` also rejects selected pass runs whose `selected_method_name` is not in `SUPPORTED_WRAPPED_QUANTITATIVE_METHODS`.
- `backend/tests/test_layer3_pass_entry.py` still proves unsupported `descriptive_summary` recommendations fail closed.

That means current `main` can run `descriptive_summary` through the lower-level analysis API, but cannot materialize or execute it through Gate C pass-entry.

## Slice Decision

The next safe planning boundary is:

> Freeze single-item `descriptive_summary` Gate C admission only for already materialized dataset-version analysis sets whose lower-level recommendation selects `descriptive_summary`, while keeping associated-cohort admission and all broader workbench/package/source/runtime/UI scope blocked.

This boundary is intentionally narrower than "allow `descriptive_summary` everywhere." The existing single-item path already carries one `dataset_version_id`, one selected method, one wrapped quantitative pass run, and one `run_analysis(...)` call. Associated-cohort admission crosses a separate shaping and derived-dataset boundary, so it remains blocked until separately governed.

## Admitted Future Implementation Scope

A future implementation PR governed by this freeze may add only:

- single-item Gate C pass-entry admission for `descriptive_summary`
- the minimum allowlist/selection changes needed for `_choose_method_name_or_raise(...)`, `materialize_pass_entry(...)`, and `execute_selected_pass_run(...)` to accept the already-supported method
- pass-plan/pass-run metadata that records `selected_method_name: "descriptive_summary"` without changing existing row families
- focused tests proving single-item materialization and selected-pass execution can run `descriptive_summary`
- focused tests proving associated-cohort `descriptive_summary` remains fail-closed

Expected implementation surfaces:

- `backend/app/services/layer3_pass_entry.py`
- `backend/tests/test_layer3_pass_entry.py`

## Explicit Non-Goals

This freeze does not admit:

- associated-cohort `descriptive_summary` pass-entry admission
- changes to `backend/app/services/analysis.py`
- new analysis methods or method parameters
- source ingestion, local upload, local directory, connector input, or runtime snapshot writes
- schema/model/migration changes
- rendered UI changes or new route families
- package, handoff, export, download, connector dispatch, public/signed URL, destination selection, or generic downstream dispatch behavior
- qualitative, hybrid, RAG, vector, LLM, DAG, background job, retry, cancellation, or agent-conductor behavior
- package mutation/reconstruction or additional package/reconciliation/artifact row families

## Required Decisions Frozen Here

| Gate | Decision | Reasoning |
| --- | --- | --- |
| Admission class | single-item only | Reuses the existing one dataset-version pass path without derived cohort shaping |
| Method | `descriptive_summary` only | Prevents this admission from becoming a general method expansion |
| Engine family | existing wrapped quantitative pass-entry spine | Avoids a new engine family or orchestration layer |
| Source scope | existing dataset version only | Preserves PR `#411` source boundary |
| Cohort posture | still blocked | Cohort shaping/derived datasets need separate governance |
| UI posture | no UI changes | Existing backend path is enough to prove admission before rendering controls |

## Required Future Proof

A future implementation PR must prove:

- single-item Gate C materialization can select `descriptive_summary` when lower-level recommendation returns it
- selected-pass execution can call `run_analysis(..., method_name="descriptive_summary", ...)`
- output metadata records the `AnalysisRun`, selected method, artifact refs, and completed/with-warnings status consistently with existing wrapped quantitative passes
- associated-cohort `descriptive_summary` remains unsupported and fail-closed
- existing `cross_correlation`, `decomposition`, and `structural_break` Gate C tests still pass
- no schema/model/migration/UI/source/runtime/package/handoff/export widening occurs

## Stop Conditions

Stop and return to planning if implementation requires:

- changing cohort shaping or admitting associated-cohort `descriptive_summary`
- adding or changing database schema
- writing runtime DB state outside existing pass-entry rows
- changing lower-level `descriptive_summary` semantics in `analysis.py`
- adding source ingestion, local upload, local directory, connector input, or public/signed URL behavior
- changing rendered UI behavior
- changing package/handoff/export/download behavior
- adding qualitative, hybrid, RAG, vector, LLM, DAG, background job, retry, cancellation, or agent-conductor behavior

## Relationship To Existing Docs

This freeze follows:

- `72_L3_DESCRIPTIVE_SUMMARY_FREEZE.md`
- `73_L3_DESCRIPTIVE_SUMMARY_CONTRACT.md`
- `74_L3_DEFERRED_IMPLEMENTATION_PLAYBOOK.md`

It selects only the next planning boundary for Gate C admission. It does not make Gate C admission live.
