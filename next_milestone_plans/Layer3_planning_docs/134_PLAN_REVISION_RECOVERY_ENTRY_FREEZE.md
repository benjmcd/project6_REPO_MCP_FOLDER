# Layer 3 Plan Revision Recovery Entry Freeze

Status: implementation-entry freeze only for `plan_revision_recovery_preview_refresh_entry`. No runtime behavior is admitted by this document.

This artifact narrows docs `132`/`133` into one future implementation entry. It selects an exact server-authorized recovery route from the current pre-approval terminal revision-control states back to a fresh plan-preview-ready posture, while preserving the hard block on approved-plan supersession, execution, package, handoff/export, connector, source-widening, broad qualitative/hybrid/RAG, full mockup, and authentication/security work.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- baseline_commit: `4809ac0aa61aac3a51a92f4070ff1d92d67591c5`
- predecessor freeze: `132_PLAN_REVISION_RECOVERY_FREEZE.md`
- predecessor contract: `133_PLAN_REVISION_RECOVERY_CONTRACT.md`
- selected implementation entry: `plan_revision_recovery_preview_refresh_entry`
- exact route: `POST /api/v1/layer3/plan/revision/recover`
- owner service: `backend/app/services/layer3_plan_revision_recovery.py`
- API request DTO: `Layer3PlanRevisionRecoveryRequest`
- API response DTO: `Layer3PlanRevisionRecoveryResponse`
- request schema id: `layer3.plan_revision_recovery_request.v1`
- response schema id: `layer3.plan_revision_recovery_result.v1`
- persistence target: existing `L3Session.summary_json` only, if adequate
- source terminal states: `plan_rejected`, `plan_revision_requested`
- evidence boundary: live source/tests and `tools/l3-progress-check.py` outrank this document

## Selected Runtime Shape For A Later PR

A later implementation PR may add only:

- `POST /api/v1/layer3/plan/revision/recover`;
- a strict request DTO and response DTO in the existing Layer 3 API module;
- `backend/app/services/layer3_plan_revision_recovery.py`;
- tests proving the route, owner service, and UI recovery posture remain bounded;
- optional rendered controls only if they call this route and keep browser state cache-only.

The later PR must not add a model, migration, package artifact, handoff/export artifact, connector dispatch, provider/public URL, source ingestion path, hidden LLM planner, or broad mockup activation.

## Required Behavior

The future runtime must:

- accept only `operator_decision == "recover_for_preview_refresh"`;
- require `client_request_id`;
- require source state proof from recorded `plan_revision_control`;
- require source preview id/hash proof;
- revalidate current Gate C typing authority;
- fail closed if any approved `L3AnalysisPlan` exists;
- fail closed if any `L3PassRun` exists;
- create no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, package, handoff/export, connector, provider, source, or artifact state;
- record only summary-state recovery metadata if existing `L3Session.summary_json` is adequate;
- keep approval unavailable until a fresh server-backed plan preview is generated after recovery;
- keep downstream controls unavailable after recovery.

## Required Fail-Closed Errors

- `plan_revision_recovery_not_available`
- `plan_revision_state_mismatch`
- `preview_mismatch`
- `gate_c_not_committed`
- `plan_already_approved`
- `plan_already_materialized`
- `pass_runs_already_exist`
- `execution_not_admitted`
- `unsupported_revision_recovery_decision`

## Positive Invariants

- `plan_revision_recovery_preview_refresh_entry` is the only selected entry.
- Recovery is available only from `plan_rejected` or `plan_revision_requested`.
- The only selected route is `POST /api/v1/layer3/plan/revision/recover`.
- The owner service is separate from `layer3_workbench.py`.
- Browser/local storage remains non-authoritative.
- The next usable plan action is fresh server-backed plan preview, not approval or execution.

## Negative Invariants

This entry freeze must not admit:

- runtime recovery implementation in this PR;
- approved-plan reopening, cancellation, deletion, replacement, or supersession;
- `L3AnalysisPlan` creation, update, or deletion;
- `L3PassRun` creation;
- `AnalysisRun` creation;
- output/package/handoff/export artifact creation;
- package mutation/reconstruction;
- connector/destination dispatch;
- provider/public URL support;
- source/upload/local-directory/RAG/vector expansion;
- broad qualitative/hybrid/RAG execution;
- frontend-only durable state;
- hidden LLM planning;
- full mockup activation;
- authentication/security hardening.

## Required Future Proof

A later runtime PR must include:

- API success from `plan_rejected`;
- API success from `plan_revision_requested`;
- API blocked without recorded revision-control state;
- API conflict for source revision state mismatch;
- API conflict for stale preview id/hash;
- API conflict for approved plans;
- API conflict for existing pass runs;
- forbidden-field fail-closed coverage;
- duplicate `client_request_id` determinism;
- database proof of no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, package, handoff/export, connector, provider, source, or artifact writes;
- frontend proof only if rendered controls are changed.

## Acceptance Criteria

This freeze is accepted when:

- this file exists and names `plan_revision_recovery_preview_refresh_entry`;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, `120_L3_CLOSEOUT.md`, `layer3_progress_manifest.json`, `layer3_progress_board.md`, and `layer3_workbench_proof_manifest.json` classify this as implementation-entry only;
- `tools/l3-progress-check.py` fails closed if this freeze is removed or if it is represented as runtime behavior;
- `python .\tools\l3-progress-check.py` passes;
- JSON/progress proof remains valid.
