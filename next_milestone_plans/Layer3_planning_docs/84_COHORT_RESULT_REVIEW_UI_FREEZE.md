# Layer 3 Cohort Result Review UI Freeze

Status: planning-only freeze for a future bounded rendered `/review/layer3` selected-pass associated-cohort `descriptive_summary` result-review UI tranche after PR `#438`.

This document does not implement UI behavior, change backend/API behavior, widen schema/runtime/source scope, or activate package, handoff, export, connector, qualitative, hybrid, RAG, vector, retry/recovery, pass-entry, or full mockup behavior. It freezes only the next eligible rendered workbench UI decision boundary over the already-live PR `#432` execution-start/result-status authority and PR `#438` backend/API result-review authority.

## Decision

The next adequate UI tranche is:

> Render the exact selected-pass associated-cohort `descriptive_summary` status/result-review state on `/review/layer3`, and allow one bounded operator result-review submission only when server-authoritative session/result-status state proves the same exact PR `#432`/PR `#438` authority. Do not add package, handoff, export, connector, schema/runtime/source, qualitative/hybrid/RAG/vector, retry/recovery, pass-entry, broader cohort review, or full mockup behavior.

This is the narrowest useful step because current `main` can execute, inspect, and review the exact selected associated-cohort result through backend/API surfaces, but the rendered workbench UI has not yet been frozen for that cohort-specific path.

## Current Live Boundary

Current repo authority for this planning branch was checked against `project6-origin/main` at `6f1a2ff4` after PR `#440`.

Live facts this freeze must preserve:

- PR `#411` makes `descriptive_summary` a lower-level analysis method.
- PR `#417` admits only single-item `descriptive_summary` through Gate C selected-pass execution.
- PR `#424`/`#425` admit only service-owned associated-cohort `descriptive_summary` through `materialize_pass_entry(...)` with exact `formation_basis_json["requested_method_name"] == "descriptive_summary"` metadata.
- PR `#432` admits only selected-pass associated-cohort `descriptive_summary` execution-start/result-status over existing backend/API surfaces.
- PR `#438` admits only exact selected-pass associated-cohort `descriptive_summary` result review over the existing backend/API result-review endpoint.
- Existing single-item result-review UI governance in docs `46`/`47` and PR `#232` may be used as a pattern, but it must not be treated as already admitting associated-cohort rendered UI behavior.

## Admitted Future UI Scope

An implementation PR governed by this freeze may touch only:

- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`
- `backend/app/review_ui/static/layer3.js`
- narrowly related page/static/browser tests that prove the changed `/review/layer3` behavior

It may do only the following:

- render server-authoritative selected-pass associated-cohort execution/result-status posture from existing session summary and result/status responses.
- call `POST /api/v1/layer3/execution/result/status` only for the server-selected terminal associated-cohort pass represented by PR `#432` authority.
- call `POST /api/v1/layer3/execution/result/review` only for the same selected terminal associated-cohort pass after PR `#438` result-review admission requirements are represented by server state.
- show pass id, analysis plan id, preview id/hash, analysis run id when available, pass status, output metadata reference, source gate, cohort shape, source dataset-version ids, requested method provenance, trace summary, unresolved trace count, review state, operator decision, and downstream-unavailable posture when provided by the server.
- provide one bounded operator decision control for `approved`, `changes_requested`, `rejected`, or `blocked`.
- provide bounded review notes/caveats.
- show package, handoff, export, connector, retry/recovery, and full mockup controls as disabled, unavailable, or absent.
- preserve the existing single-item result-review UI behavior.

The UI must rely on server state and responses as authority. Browser state may cache or display values, but browser state must not authorize review, approve a result, select passes, start execution, package output, hand off output, export output, recover/retry a pass, or infer missing cohort provenance.

## Explicit Non-Goals

This freeze does not admit:

- new backend routes or request DTO families
- execution-selection UI controls
- analysis-execution-start UI controls
- free-form pass-run id entry
- package-review preview, package construction, package-review submit, or package mutation UI
- handoff/export/download UI
- connector dispatch, destination selection, or generic downstream dispatch
- rerun, retry, recovery, cancellation, or replay controls
- result-review amendment or supersession
- multi-pass or batch associated-cohort result review
- associated-cohort result review outside exact PR `#432` selected-pass `descriptive_summary` output authority
- local upload or local-directory ingestion
- schema, model, migration, runtime DB, or source-ingestion changes
- changes to `backend/app/services/layer3_pass_entry.py`
- changes to PR `#432` execution-start/result/status gates
- changes to PR `#438` backend/API result-review admission gates
- qualitative, hybrid, RAG, vector, LLM, agent, background job, or full mockup behavior

## State Gating

The UI may enable the associated-cohort result-review submission control only when all are true:

1. a session id exists
2. the session summary identifies the approved plan and approved preview id/hash
3. the selected pass is server-confirmed for the current session and approved plan
4. the selected pass is an associated-cohort `descriptive_summary` pass with the PR `#432` source gate and provenance represented by server state
5. result/status authority is available for that selected terminal pass
6. output metadata is readable and traces to the same selected pass, analysis run, source dataset-version ids, and output payload ref
7. trace requirements are resolved or the server says the review decision is allowed for the supplied reviewed output items
8. no conflicting result-review record is already present
9. package, handoff, export, connector, retry/recovery, and full mockup controls remain disabled, unavailable, or absent

If any condition is absent, stale, malformed, or inconsistent, the UI must render a blocked or unavailable state and avoid submitting result-review requests.

## Backend Boundary

This UI freeze expects any implementation to use existing backend routes:

- `GET /api/v1/layer3/session/{session_id}`
- `POST /api/v1/layer3/execution/result/status`
- `POST /api/v1/layer3/execution/result/review`

If those routes do not provide enough data for safe associated-cohort UI gating, stop and add a separate API/state freeze before changing backend behavior. This document does not authorize new API fields, tables, migrations, artifacts, package rows, handoff rows, source-ingestion rows, runtime DB writes, or pass-entry changes by default.

## Required Proof

An implementation PR governed by this freeze must prove:

- existing single-item result-review UI behavior remains unchanged.
- associated-cohort result/status can be requested only for the server-selected terminal PR `#432` pass.
- associated-cohort result review can be submitted only after server-authoritative result/status availability.
- the UI submits only fields admitted by docs `82`/`83` and current backend behavior.
- missing/stale preview identity, wrong plan/session/pass binding, missing execution-start state, missing output metadata, malformed selected metadata, malformed provenance, wrong method, wrong pass scope, non-terminal status, unresolved trace, duplicate/conflict, or backend fail-closed response renders blocked or unavailable.
- already-recorded associated-cohort review state renders read-only unless a later freeze admits amendment or supersession.
- forbidden package/handoff/export/rerun/retry/recovery/source/schema/runtime/output-rewrite/pass-entry fields are not collected or submitted.
- package, handoff, export, connector, retry/recovery, and full mockup controls remain disabled, unavailable, or absent after all review decisions.
- relevant backend Layer 3 tests still pass.
- page/static tests cover disabled, blocked, available, recorded, and duplicate/conflict UI states.
- both headed and headless Chrome browser proof pass because rendered UI behavior changes.

Minimum local proof shape for an implementation PR:

```powershell
python -m pytest .\backend\tests\test_layer3_api.py::test_layer3_api_selected_cohort_execution_start_and_status_are_bounded .\backend\tests\test_layer3_api.py::test_layer3_api_selected_cohort_result_review_prechecks_fail_closed .\backend\tests\test_layer3_api.py::test_layer3_api_execution_result_review_records_approval_without_downstream_writes -q
python -m pytest .\backend\tests\test_layer3_api.py -q
python -m pytest .\backend\tests\test_layer3_pass_entry.py -q
```

Add page/static and headed/headless browser tests once implementation touches rendered UI files.

## Stop Conditions

Stop before implementation if any of these becomes necessary:

- editing backend service, route, schema, model, migration, runtime/source, or pass-entry files
- adding a new endpoint or new request DTO family
- activating execution selection/start UI controls
- activating package, handoff, export, connector, retry/recovery, or destination behavior
- allowing associated-cohort review outside exact PR `#432` selected-pass `descriptive_summary` output authority
- changing PR `#438` backend/API result-review gates
- changing single-item result-review UI behavior outside compatibility preservation
- accepting method selection from route request JSON, UI state, fallback order, or pass-run-only summary value
- activating qualitative/hybrid/RAG/vector/full mockup behavior

## Relationship To Existing Docs

This freeze is downstream of:

- `46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`
- `80_COHORT_EXECUTION_FREEZE.md`
- `81_COHORT_EXECUTION_CONTRACT.md`
- `82_COHORT_RESULT_REVIEW_FREEZE.md`
- `83_COHORT_RESULT_REVIEW_CONTRACT.md`

It freezes only the associated-cohort rendered UI presentation/control boundary over the already-live backend/API cohort execution and result-review path. It does not replace the backend/API docs and does not make UI behavior live by itself.
