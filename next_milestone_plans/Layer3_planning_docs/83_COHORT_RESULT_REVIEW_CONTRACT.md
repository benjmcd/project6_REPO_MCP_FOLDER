# Layer 3 Cohort Result Review Contract

Status: governing planning-only API/state companion for `82_COHORT_RESULT_REVIEW_FREEZE.md`; PR `#438` later implemented this exact bounded backend/API contract on current `main`.

This document is not live behavior by itself. It does not change API/UI behavior, make selected-pass associated-cohort result review live by itself, widen schema/runtime/source scope, or activate package, handoff, export, connector, qualitative, hybrid, RAG, vector, retry/recovery, or full mockup behavior. PR `#438` is the separate implementation authority for the exact backend/API contract below.

## Contract Scope

This contract governs only the backend/API implementation that extends the existing selected-pass result-review endpoint from single-item results to the exact associated-cohort `descriptive_summary` results admitted by PR `#432`. PR `#438` later implemented that bounded contract.

The governed implementation may touch only:

- `backend/app/services/layer3_workbench.py`
- `backend/tests/test_layer3_api.py`

Any required touch outside those files is a stop condition unless a new freeze admits the wider surface first.

## Endpoint Contract

The implementation must reuse the existing endpoint:

`POST /api/v1/layer3/execution/result/review`

It must not add a new route, route family, UI surface, or request shape beyond the existing result-review request fields already admitted for single-item result review.

Minimum request fields remain:

| Field | Required | Meaning |
| --- | --- | --- |
| `session_id` | yes | Existing Layer 3 workbench session |
| `analysis_plan_id` | yes | Current approved plan for the session |
| `pass_run_id` | yes | Existing selected terminal pass run for the session and approved plan |
| `preview_id` | yes | Approved plan and execution-selection preview identity |
| `preview_hash` | yes | Approved plan and execution-selection preview hash |
| `operator_decision` | yes | `approved`, `changes_requested`, `rejected`, or `blocked` |
| `client_request_id` | yes | Required deterministic duplicate key |
| `review_notes` | conditional | Required for non-approval decisions; optional for `approved` |
| `reviewed_output_items` | no | Optional bounded list of item-level review references, each traceable to existing output metadata |
| `analysis_run_id` | no | If supplied, must match the selected pass-run summary |

Forbidden fields remain the existing result-review forbidden set and must continue to include package, handoff, export, rerun/retry/recovery/cancel, source expansion, local upload/directory, schema migration, runtime DB write, package variants, APS handoff, edited findings, and output rewrite intent.

## Associated-Cohort Admission Contract

Associated-cohort result review may proceed only after the implementation has called the existing result/status authority and all checks below pass:

- `execution_result_status(...)` returns an available response for the same session, approved plan, pass run, preview id/hash, and optional analysis run id.
- `status_body["pass_type"] == "associated_cohort"`.
- `status_body["pass_scope"] == "quantitative_associated_cohort_dataset_version"`.
- `status_body["selected_method_name"] == "descriptive_summary"`.
- `status_body["output_metadata_summary"]["readable"] is true`.
- `status_body["output_metadata_summary"]["source_gate"] == "78_COHORT_FREEZE"`.
- the selected pass summary proves the PR `#432` admitted execution path, including `requested_method_name == "descriptive_summary"`, service-owned method source, `cohort_shape == "aligned_wide_table"`, and source dataset-version ids.
- the selected pass has prior execution-start state, terminal status, output payload ref, and matching analysis run id when supplied.

The implementation must not treat a request field, UI field, fallback recommendation, or pass-run summary value alone as authority for associated-cohort result review.

## Response Contract

The response must keep the existing result-review schema:

`layer3.execution_result_review.v1`

It may return the same response fields as single-item result review, with associated-cohort values reflected in trace/output metadata:

| Field | Requirement |
| --- | --- |
| `status` | `recorded`, `already_recorded`, or fail-closed error status |
| `result_status_available` | `true` only after result/status authority succeeds |
| `result_review_enabled` | `true` only for the bounded associated-cohort review response after all checks pass |
| `review_state` | existing `execution_result_review_*` state values only |
| `review_record_ref` | stable reference to the bounded JSON review envelope |
| `trace_summary` | must include selected pass/output metadata/analysis run references and available cohort provenance |
| `package_review_enabled` | always `false` for this tranche |
| `handoff_enabled` | always `false` for this tranche |
| `downstream_unavailable` | must continue to include package and handoff surfaces |

If the existing response schema cannot represent the associated-cohort trace summary without ambiguity, implementation must stop and create a narrower schema/update freeze instead of silently widening this contract.

## State And Write Boundary

The implementation may write only the existing result-review JSON envelope shapes:

- `L3PassRun.summary_json["execution_result_review"]`
- `L3Session.summary_json["execution_result_review"]`

The review state must remain attached to exactly one selected associated-cohort pass and must not alter:

- approved plan state
- execution-selection state
- execution-start state
- output metadata files
- package-review state
- handoff/export state
- schema/runtime/source state

The implementation must not create or update:

- `L3AnalysisPlan`
- new `L3PassRun`
- new `AnalysisRun`
- `AnalysisArtifact`
- `L3OutputPackage`
- `L3ReconciliationRecord`
- package rows, handoff rows, runtime snapshot rows, source-ingestion rows, or migration files

## Failure Contract

The endpoint must fail closed when:

- result/status is not available for the supplied selected pass
- the pass is not the exact PR `#432` admitted associated-cohort `descriptive_summary` pass
- pass type, pass scope, method name, method source, cohort shape, source gate, source dataset-version ids, plan id, preview id/hash, session id, or analysis run id is missing or inconsistent
- output metadata is missing, unreadable, or lacks required trace references for approval
- supplied reviewed output items contain unresolved trace references and the operator decision is `approved`
- duplicate identical submissions cannot be proven deterministic
- conflicting review state already exists
- the request includes fields that imply package, handoff, export, rerun/retry/recovery, source expansion, schema/runtime, output rewrite, connector dispatch, or UI/full mockup activation

Terminal failed associated-cohort pass runs must not be approvable by default. A later explicit failure-review freeze is required if failed-result non-approval review needs different handling than current result/status availability allows.

## Proof Contract

Implementation tests must cover:

- successful `approved` review for one terminal selected associated-cohort `descriptive_summary` result created by the PR `#432` path
- successful non-approval review if the existing single-item endpoint semantics allow the same status/output authority for associated cohorts
- existing single-item result-review tests unchanged
- associated-cohort review blocked before execution-start
- associated-cohort review blocked before terminal status
- associated-cohort review blocked when output metadata is missing or unreadable
- associated-cohort review blocked for wrong pass type, pass scope, method name, method source, cohort shape, source gate, source dataset-version provenance, plan binding, preview identity, session binding, or analysis run id
- associated-cohort approval blocked when reviewed output item trace is unresolved
- duplicate identical associated-cohort review behavior deterministic
- conflicting associated-cohort review behavior fail-closed
- forbidden downstream fields fail closed
- no package, handoff, export/download, UI, schema/runtime/source, connector, qualitative/hybrid/RAG/vector, or full mockup state is created or enabled

Minimum local proof after focused tests:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py -q
```

If implementation touches pass-entry behavior despite the no-touch default, it must stop unless a new freeze admits that change. If a reviewer explicitly approves pass-entry touch under a later freeze, the proof set must add:

```powershell
python -m pytest .\backend\tests\test_layer3_pass_entry.py -q
```

## Completion Criteria

An implementation satisfies this contract only if a reviewer can verify:

- associated-cohort result review is reachable only for the exact PR `#432` selected-pass `descriptive_summary` output.
- existing single-item result review is unchanged.
- PR `#432` execution-start/result-status gates are unchanged.
- the only write is the existing result-review JSON envelope on the selected pass/session.
- package review, package construction, handoff, export/download, UI, schema/runtime/source, connector, qualitative/hybrid/RAG/vector, and full mockup behavior remain unavailable.
- focused tests and CI pass.
