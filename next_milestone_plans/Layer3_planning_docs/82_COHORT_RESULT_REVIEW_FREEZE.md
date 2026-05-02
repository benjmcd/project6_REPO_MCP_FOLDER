# Layer 3 Cohort Result Review Freeze

Status: governing planning-only freeze for the selected-pass associated-cohort `descriptive_summary` result-review tranche after PR `#432`; PR `#438` later implemented this exact bounded backend/API slice on current `main`.

This document does not change code, make associated-cohort result review live by itself, change UI behavior, widen schema/runtime/source scope, or activate package, handoff, export, connector, qualitative, hybrid, RAG, vector, retry/recovery, or full mockup behavior. It freezes only the backend/API decision boundary after the PR `#432` selected-pass associated-cohort execution-start/result-status path. PR `#438` is the separate implementation authority for that boundary.

## Decision

The next adequate tranche is:

> Admit one bounded operator result-review decision for one terminal selected-pass associated-cohort `descriptive_summary` result that was produced by the exact PR `#432` execution-start path and is available through the existing `/api/v1/layer3/execution/result/status` authority.

This was the narrowest useful step because current main after PR `#432` could execute and inspect the exact selected associated-cohort result, while `/api/v1/layer3/execution/result/review` still failed closed with `associated_cohort_result_review_not_admitted`. PR `#438` later implemented this exact backend/API admission while preserving the no-go boundaries below.

## Current Live Boundary

Current repo authority for the original planning branch was checked against `project6-origin/main` at `5fc75c42` after PR `#433`. Current `main` later includes PR `#438`, which implemented this exact result-review backend/API boundary.

Live facts this freeze must preserve:

- PR `#411` makes `descriptive_summary` a lower-level analysis method.
- PR `#417` admits only single-item `descriptive_summary` through Gate C selected-pass execution.
- PR `#424`/`#425` admit only service-owned associated-cohort `descriptive_summary` through `materialize_pass_entry(...)` with exact `formation_basis_json["requested_method_name"] == "descriptive_summary"` metadata.
- PR `#432` admits only selected-pass associated-cohort `descriptive_summary` execution-start/result-status over existing backend/API surfaces.
- `backend/app/services/layer3_workbench.py::execution_result_status(...)` can inspect the admitted selected associated-cohort result while keeping `result_review_enabled`, `package_review_enabled`, and `handoff_enabled` false.
- Before PR `#438`, `backend/app/services/layer3_workbench.py::execution_result_review(...)` called `_ensure_result_status_downstream_source_admitted(...)`, which blocked associated-cohort result review with `associated_cohort_result_review_not_admitted`.
- PR `#438` later added the exact result-review admission gate for this freeze while preserving package, handoff, export/download, UI, schema/runtime/source, connector, qualitative/hybrid/RAG/vector, retry/recovery, pass-entry, and full mockup no-go boundaries.

## Admitted Implementation Scope

An implementation PR governed by this freeze may touch only:

- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_api.py`

It may do only the following:

- allow the existing `/api/v1/layer3/execution/result/review` endpoint to accept an associated-cohort pass only when the result/status body proves the exact PR `#432` admitted `descriptive_summary` associated-cohort execution-start/result-status path.
- reuse the existing single-item result-review decision values, request fields, idempotency behavior, trace-summary shape, response schema, and JSON write boundary unless a contract line below explicitly narrows them further.
- record exactly one bounded review decision for one selected terminal associated-cohort pass.
- write only the existing `execution_result_review` JSON envelope on the selected `L3PassRun` and `L3Session`, matching the current single-item result-review owner boundary.
- preserve package review, handoff, export/download, UI, schema/runtime/source, connector, qualitative/hybrid/RAG/vector, retry/recovery, and full mockup unavailable posture.

## Admission Requirements

Associated-cohort result review may be admitted only when all are true:

- the request satisfies the existing result-review required fields and forbidden-field checks.
- `execution_result_status(...)` returns `status == "available"` and `result_status_available is true` for the same session, approved plan, pass run, preview id/hash, and optional analysis run id.
- the selected pass has `pass_type == "associated_cohort"`.
- the selected pass has `pass_scope == "quantitative_associated_cohort_dataset_version"`.
- the selected method is exactly `descriptive_summary`.
- the pass summary proves the PR `#432` admitted associated-cohort execution path, including exact service-owned method metadata, `aligned_wide_table` cohort shape, source dataset-version provenance, and the governed cohort source gate.
- output metadata is readable and traces back to the same selected pass, analysis run, derived dataset version, source dataset-version ids, and output payload ref.
- the review decision and reviewed item trace references are compatible with the existing result-review trace rules.

If any condition is absent, malformed, stale, or inconsistent, result review must fail closed before writing review state.

## Explicit Non-Goals

This freeze does not admit:

- a new route or request DTO family
- rendered UI controls or browser behavior
- package-review preview, package construction, package-review submit, package mutation, or package payload writes
- APS handoff, external export/download, connector dispatch, destination selection, or generic downstream dispatch
- new `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3OutputPackage`, or `L3ReconciliationRecord` rows
- schema, model, migration, runtime DB, or source-ingestion changes
- changing `backend/app/services/layer3_pass_entry.py`
- changing PR `#432` execution-start/result-status gates
- review amendment, supersession, rerun, retry, recovery, cancellation, or replay
- result aggregation across multiple pass runs
- broad output taxonomy work beyond the existing result-review projection
- qualitative, hybrid, RAG, vector, LLM, agent, background job, or full mockup behavior

## Required Proof

An implementation PR governed by this freeze must prove:

- single-item selected-pass result review remains unchanged.
- service-owned associated-cohort `materialize_pass_entry(...)` remains unchanged.
- PR `#432` selected-pass associated-cohort execution-start/result-status remains unchanged.
- associated-cohort result review succeeds only for an exact admitted selected-pass `descriptive_summary` terminal output.
- associated-cohort result review fails closed for missing or stale preview identity, wrong plan/session/pass binding, missing execution-start state, missing or unreadable output metadata, malformed selected metadata, malformed provenance, wrong method, wrong pass scope, or non-terminal status.
- approved associated-cohort review requires resolved trace references for supplied reviewed output items.
- duplicate identical associated-cohort review submissions are deterministic.
- conflicting associated-cohort review submissions fail closed.
- forbidden package/handoff/export/rerun/source/schema/runtime/output-rewrite fields fail closed.
- no package, handoff, export/download, UI, schema/runtime/source, connector, qualitative/hybrid/RAG/vector, or full mockup state is created or enabled.

Minimum local proof shape:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_selected_cohort_execution_start_and_status_are_bounded .\backend\tests\test_layer3_api.py::test_layer3_api_execution_result_review_records_approval_without_downstream_writes -q
python -m pytest .\backend\tests\test_layer3_api.py -q
```

Add `backend/tests/test_layer3_pass_entry.py` to the proof set if implementation touches pass-entry behavior; otherwise pass-entry remains a no-touch source-of-truth boundary.

Run browser proof only if a later implementation changes rendered UI; UI is no-go under this freeze.

## Stop Conditions

Stop and create a new freeze if implementation requires:

- editing frontend/static UI files
- editing `backend/app/services/layer3_pass_entry.py`
- adding a new route instead of reusing `/api/v1/layer3/execution/result/review`
- creating schema/model/migration/runtime/source behavior
- activating package review, package construction, handoff, export/download, connector dispatch, or destination selection
- allowing result review for associated cohorts not produced by the exact PR `#432` selected-pass execution-start path
- changing single-item result-review behavior outside compatibility preservation
- accepting method selection from route request JSON, UI state, fallback order, or pass-run summary alone
