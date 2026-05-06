# Layer 3 Approved Plan Cancel Entry Freeze

Status: implementation-entry freeze only for `approved_plan_cancel_without_replacement`. No runtime behavior is admitted by this document.

This artifact narrows `135_APPROVED_PLAN_CORRECTION_FREEZE.md` to one future approved-plan correction mode: cancel the current approved plan without replacement. It does not implement cancellation, reopen an approved plan, create a replacement plan, supersede a plan, start execution, mutate packages, dispatch connectors, widen sources, or activate any UI/full-mockup behavior.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- baseline_commit: `d60b01aabf394ee36f4fbcffb13e932d931e996c`
- predecessor freeze: `135_APPROVED_PLAN_CORRECTION_FREEZE.md`
- selected correction mode: `approved_plan_cancel_without_replacement`
- current approved-plan row authority: `L3AnalysisPlan`
- current approved-plan fields: `status`, `approved_by_operator`, `approved_at`, `plan_json`
- current approval route: `POST /api/v1/layer3/plan/approve`
- current approval owner: `backend/app/services/layer3_workbench.py`
- current plan-flow request contract owner: `backend/app/services/layer3_plan_flow_contract.py`
- future owner service: `backend/app/services/layer3_approved_plan_correction.py`
- future route: `POST /api/v1/layer3/plan/approved/cancel`
- future request DTO: `Layer3ApprovedPlanCancelRequest`
- future response DTO: `Layer3ApprovedPlanCancelResponse`
- future request schema id: `layer3.approved_plan_cancel_request.v1`
- future response schema id: `layer3.approved_plan_cancel_result.v1`
- evidence boundary: live source/tests and `tools/l3-progress-check.py` outrank this document

## Selected Entry Mode

The only selected future correction mode is:

- selected_entry_mode: `approved_plan_cancel_without_replacement`
- selected_route: `POST /api/v1/layer3/plan/approved/cancel`
- selected_owner_service: `backend/app/services/layer3_approved_plan_correction.py`
- selected_persistence: existing `L3AnalysisPlan` row plus existing `L3Session.summary_json` only

The future runtime may mark exactly one current approved plan as cancelled and record response-safe cancellation metadata. It must not create or approve a replacement plan in the same action. A later preview/approval path must remain separate and server-authorized.

## Future Request Contract

Future request shape:

```json
{
  "schema_id": "layer3.approved_plan_cancel_request.v1",
  "session_id": "string",
  "analysis_plan_id": "string",
  "source_preview_id": "string",
  "source_preview_hash": "string",
  "operator_decision": "cancel_approved_plan_without_replacement",
  "operator_note": "optional string",
  "client_request_id": "string"
}
```

The request must fail closed if it contains replacement, supersession, execution, package, handoff/export, connector, provider, source, qualitative/hybrid/RAG, mockup, or browser-authority fields.

## Future Response Contract

Successful response shape:

```json
{
  "schema_id": "layer3.approved_plan_cancel_result.v1",
  "request_id": "string",
  "session_id": "string",
  "analysis_plan_id": "string",
  "next_state": "approved_plan_cancelled",
  "approved_plan_cancelled": true,
  "replacement_plan_created": false,
  "approval_available": false,
  "execution_started": false,
  "source_preview_id": "string",
  "source_preview_hash": "string",
  "operator_decision": "cancel_approved_plan_without_replacement",
  "authority_rail": {},
  "downstream_unavailable": ["execution", "results", "package", "handoff"]
}
```

The response must not include a replacement `analysis_plan_id`, pass-run ids, analysis-run ids, package ids, handoff ids, export ids, generated plan alternatives, connector ids, provider URLs, file bytes, or artifact refs.

## Required Future Behavior

The future runtime must:

- require `client_request_id`;
- require `operator_decision == "cancel_approved_plan_without_replacement"`;
- lock the session and the current approved `L3AnalysisPlan`;
- require exactly one `L3AnalysisPlan` for the session with `status == "approved"` and `approved_by_operator == true`;
- require the request `analysis_plan_id` to match that approved plan;
- require the request preview id/hash to match the approved plan's stored source preview id/hash;
- fail closed if any `L3PassRun` exists for the session;
- fail closed if any `AnalysisRun` exists for the session;
- fail closed if result review, package, handoff/export, connector, source-widening, provider/public URL, qualitative/hybrid/RAG, or package-mutation state exists;
- update only the existing approved plan row and existing session summary state;
- preserve approved-plan audit data in `plan_json`;
- record cancellation metadata without deleting the plan row;
- keep approval unavailable until a later fresh server-backed preview/approval path is explicitly invoked;
- keep downstream controls unavailable after cancellation.

## Required Fail-Closed Errors

- `session_not_found`
- `approved_plan_not_found`
- `multiple_approved_plans`
- `approved_plan_mismatch`
- `approved_plan_preview_mismatch`
- `approved_plan_cancel_not_available`
- `pass_runs_already_exist`
- `analysis_runs_already_exist`
- `downstream_state_already_exists`
- `approved_plan_supersession_not_admitted`
- `replacement_plan_not_admitted`
- `execution_not_admitted`
- `unsupported_approved_plan_cancel_decision`

## Positive Invariants

- `approved_plan_cancel_without_replacement` is the only selected correction mode.
- Exactly one current approved plan is required.
- The approved plan is cancelled only by server authority.
- Cancellation preserves the plan row and audit metadata.
- Cancellation creates no replacement plan.
- Cancellation creates no pass run, analysis run, package, handoff/export, connector, provider, source, qualitative/hybrid/RAG, package mutation, artifact, or mockup state.
- Browser/local storage remains cache-only and non-authoritative.
- A later fresh plan preview/approval path remains separate.

## Negative Invariants

This implementation-entry freeze must not accidentally admit:

- runtime behavior by this document alone;
- approved-plan replacement or supersession;
- approved-plan deletion;
- automatic plan generation;
- `L3AnalysisPlan` creation;
- `L3PassRun` creation, update, cancellation, or deletion;
- `AnalysisRun` creation, update, cancellation, or deletion;
- result review, package review, package construction, package mutation, handoff, export, or connector dispatch;
- output/package/handoff/export artifact creation;
- source/upload/local-directory/RAG/vector expansion;
- broad qualitative/hybrid/RAG execution;
- provider/public URL support;
- frontend-only durable state;
- hidden LLM planning;
- package mutation/reconstruction;
- full mockup activation;
- authentication/security hardening.

## Required Future Tests

A later implementation PR must prove:

- cancel is unavailable without an approved plan;
- cancel succeeds for exactly one current approved plan when no downstream state exists;
- stale `analysis_plan_id` fails closed;
- stale preview id/hash fails closed;
- multiple approved plans fail closed;
- existing pass runs fail closed;
- existing analysis runs fail closed;
- result/package/handoff/export/connector/source/provider state progression fails closed;
- duplicate `client_request_id` behavior is deterministic;
- forbidden replacement/supersession/execution/downstream/source/package/connector/provider/mockup fields fail closed;
- no replacement `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, package, handoff/export, connector, source, provider, or artifact state is created;
- browser state cannot cancel an approved plan without server authority.

## Stop Conditions

Stop before implementation if the intended change requires:

- approved-plan supersession or replacement;
- deleting approved-plan rows;
- automatic plan generation;
- pass-run or analysis-run mutation;
- artifact writes;
- package/handoff/export behavior;
- connector/destination behavior;
- source widening;
- broad qualitative/hybrid/RAG behavior;
- full mockup activation;
- authentication/security work while that lane remains deferred.

## Acceptance Criteria

This implementation-entry freeze is accepted when:

- this file exists and contains `selected_entry_mode: approved_plan_cancel_without_replacement`;
- this file names exactly one future route, owner service, request DTO, response DTO, request schema id, and response schema id;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` classify this as implementation-entry only, not runtime;
- `layer3_progress_manifest.json`, `layer3_progress_board.md`, and `layer3_workbench_proof_manifest.json` record this slice as planning-only;
- `tools/l3-progress-check.py` fails closed if this slice is marked live or if supersession/replacement/package/connector/source/RAG/mockup/auth behavior is admitted;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` reports no whitespace errors.
