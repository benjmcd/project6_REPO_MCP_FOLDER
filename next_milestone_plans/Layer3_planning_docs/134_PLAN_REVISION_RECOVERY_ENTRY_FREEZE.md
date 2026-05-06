# Layer 3 Plan Revision Recovery Entry Freeze

Status: bounded runtime contract for `plan_revision_recovery_preview_refresh_entry`.

This artifact narrows docs `132`/`133` into one live server-authorized recovery entry. It admits only a pre-approval preview-refresh recovery route from existing terminal revision-control states back to fresh server-backed plan-preview readiness. It does not admit approved-plan reopening, cancellation, deletion, replacement, or supersession; execution; package, handoff, or export behavior; connector or destination dispatch; provider/public URLs; source widening; broad qualitative/hybrid/RAG behavior; full mockup activation; or authentication/security work.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- runtime_branch_base_commit: `47aef2ee13e173121c3738e63bafbe86e360c280`
- predecessor freeze: `132_PLAN_REVISION_RECOVERY_FREEZE.md`
- predecessor contract: `133_PLAN_REVISION_RECOVERY_CONTRACT.md`
- selected runtime entry: `plan_revision_recovery_preview_refresh_entry`
- exact route: `POST /api/v1/layer3/plan/revision/recover`
- owner service: `backend/app/services/layer3_plan_revision_recovery.py`
- API request DTO: `Layer3PlanRevisionRecoveryRequest`
- API response DTO: `Layer3PlanRevisionRecoveryResponse`
- request schema id: `layer3.plan_revision_recovery_request.v1`
- response schema id: `layer3.plan_revision_recovery_result.v1`
- recovery marker schema id: `layer3.plan_revision_recovery_preview_refresh.v1`
- persistence target: existing `L3Session.summary_json` only
- source terminal states: `plan_rejected`, `plan_revision_requested`
- state/action next action: `plan_revision_recover`
- state/action allowed_next_actions: ["plan_revision_recover"]
- evidence boundary: live source/tests and `tools/l3-progress-check.py` outrank this document

## Selected Runtime Shape

The admitted runtime adds only:

- `POST /api/v1/layer3/plan/revision/recover`;
- strict request/response DTOs in `backend/app/api/layer3.py`;
- `backend/app/services/layer3_plan_revision_recovery.py` as owner service;
- summary-state recovery metadata in existing `L3Session.summary_json`;
- a `plan_preview` recovery marker that forces a fresh server-backed `preview_id` after recovery while preserving the owner preview hash for the unchanged plan content;
- readiness/session-summary state that reports approval unavailable until the refreshed preview is generated.

This runtime adds no model, migration, package artifact, handoff/export artifact, connector dispatch, provider/public URL, source ingestion path, hidden LLM planner, frontend-only durable state, broad mockup activation, or authentication/security behavior.

## Required Behavior

The runtime must:

- accept only `operator_decision == "recover_for_preview_refresh"`;
- require `client_request_id`;
- require source state proof from recorded `plan_revision_control`;
- require source preview id/hash proof;
- revalidate current Gate C typing authority;
- fail closed if any approved `L3AnalysisPlan` exists;
- fail closed if any `L3AnalysisPlan` already materialized for the session;
- fail closed if any `L3PassRun` exists;
- create no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3OutputPackage`, `L3ReconciliationRecord`, `ConnectorRun`, package, handoff/export, connector, provider, source, or artifact state;
- record only summary-state recovery metadata in `L3Session.summary_json`;
- preserve original `plan_revision_control` evidence while marking it recovered;
- report `approval_available: false`, `execution_started: false`, and `recovery_lifecycle_only: true`;
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

- `plan_revision_recovery_preview_refresh_entry` is the only admitted recovery entry.
- Recovery is available only from `plan_rejected` or `plan_revision_requested`.
- `plan_rejected` and `plan_revision_requested` expose only `plan_revision_recover` as their recovery next action.
- The only selected route is `POST /api/v1/layer3/plan/revision/recover`.
- The owner service is separate from `layer3_workbench.py`.
- Browser/local storage remains non-authoritative.
- The next usable plan action is fresh server-backed plan preview, not stale approval or execution.
- Stale pre-recovery preview approval fails with `preview_mismatch`.
- A fresh post-recovery preview produces a different `preview_id` while preserving the unchanged owner `preview_hash`.

## Negative Invariants

This runtime must not admit:

- approved-plan reopening, cancellation, deletion, replacement, or supersession;
- `L3AnalysisPlan` creation, update, or deletion;
- `L3PassRun` creation;
- `AnalysisRun` creation;
- `AnalysisArtifact` creation;
- `L3OutputPackage` creation, update, or deletion;
- `L3ReconciliationRecord` creation, update, or deletion;
- `ConnectorRun` creation;
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

## Required Proof

Runtime proof must include:

- API success from `plan_rejected`;
- API success from `plan_revision_requested`;
- API blocked without recorded revision-control state;
- API conflict for source revision state mismatch;
- API conflict for stale preview id/hash;
- API conflict for approved plans;
- API conflict for existing pass runs;
- forbidden-field fail-closed coverage;
- duplicate `client_request_id` determinism;
- stale pre-recovery preview approval fails closed;
- fresh post-recovery preview has a changed `preview_id`;
- database proof of no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3OutputPackage`, `L3ReconciliationRecord`, `ConnectorRun`, package, handoff/export, connector, provider, source, or artifact writes;
- frontend proof only if rendered controls are changed.

## Acceptance Criteria

This runtime is accepted when:

- this file names `plan_revision_recovery_preview_refresh_entry` as bounded runtime;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, `120_L3_CLOSEOUT.md`, `layer3_progress_manifest.json`, `layer3_progress_board.md`, and `layer3_workbench_proof_manifest.json` classify only this preview-refresh route as live;
- `tools/l3-progress-check.py` fails closed if this runtime is represented as approved-plan supersession or broader recovery;
- `python .\tools\l3-progress-check.py` passes;
- focused API and contract tests pass;
- JSON/progress proof remains valid.
