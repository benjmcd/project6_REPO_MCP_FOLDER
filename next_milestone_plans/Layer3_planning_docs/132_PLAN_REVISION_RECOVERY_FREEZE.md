# Layer 3 Plan Revision Recovery Freeze

Status: planning/control freeze only for `plan_revision_recovery_lifecycle`. No runtime behavior is admitted by this document.

This artifact narrows the next state-machine question after the live pre-approval plan revision-control path. Current main can record `plan_rejected` and `plan_revision_requested` in `L3Session.summary_json`, and the state model intentionally leaves both states with `allowed_next_actions: []`. That terminal posture is safe, but it leaves the operator recovery lifecycle unspecified before any broader work is considered.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- baseline_commit: `b8b1c000e85a0ae119139d5b7328e68437d143eb`
- predecessor plan revision freeze: `34_L3_WB_PLAN_REVISION_FREEZE.md`
- predecessor plan revision contract: `35_L3_WB_PLAN_REVISION_API_AND_STATE_CONTRACT.md`
- live plan revision route: `/api/v1/layer3/plan/revise`
- live terminal states: `plan_rejected`, `plan_revision_requested`
- current state-model owner: `backend/app/services/layer3_state_model_contract.py`
- current plan-flow request contract owner: `backend/app/services/layer3_plan_flow_contract.py`
- selected future lifecycle mode: `plan_revision_recovery_lifecycle`
- evidence boundary: live source/tests and `tools/l3-progress-check.py` outrank this document

## Decision

The next revision-control question is narrowed to exactly:

- selected_future_lifecycle_mode: `plan_revision_recovery_lifecycle`
- selected_recovery_posture: `server_authorized_preview_refresh_only`

This is not live runtime. A later implementation-entry freeze may define one recovery action from a pre-approval terminal revision-control state back to a server-authorized preview-refresh posture. It must not reopen, replace, supersede, or delete an already approved `L3AnalysisPlan`.

## Why Recovery Freeze Outranks Broad Work

Broad package mutation, connector dispatch, source expansion, broad qualitative/hybrid/RAG execution, and full mockup activation would all build on longer-lived workbench state. The current revision-control terminal states are safe but intentionally closed. Freezing the recovery lifecycle first prevents future work from smuggling in approved-plan supersession, hidden planning, browser-only state authority, execution, or downstream package behavior as a convenience path out of `plan_rejected` or `plan_revision_requested`.

## Admitted Planning Scope

This freeze may specify:

- how a future implementation-entry freeze proves the source revision-control state;
- which existing server authority must be revalidated before recovery;
- that recovery may only move toward a fresh server plan preview, not toward execution;
- that the browser may request recovery but cannot be durable authority for it;
- that approved plans, pass runs, analysis runs, package state, and handoff/export state block this recovery lane;
- required DTO, service, state, UI, and test boundaries for a later implementation-entry freeze.

## Required Future Contract

A later implementation-entry freeze must define:

- exact route or existing-route extension, if any;
- owner service;
- strict request DTO and response DTO;
- source `plan_revision_control` state proof;
- preview id/hash and Gate C authority revalidation;
- idempotency key and authority hash basis;
- stale revision state, stale preview, approved-plan, pass-run, and existing execution behavior;
- response-safe next state and next allowed actions;
- rollback path that leaves `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, package, handoff, export, source, and artifact state unchanged.

## Positive Invariants

The future recovery lane is acceptable only if:

- `plan_revision_recovery_lifecycle` is the only selected lifecycle mode;
- recovery is available only from `plan_rejected` or `plan_revision_requested`;
- no approved `L3AnalysisPlan` exists for the session;
- no `L3PassRun` exists for the session;
- no `AnalysisRun` is created or modified;
- recovery requires server revalidation of Gate C and the recorded revision-control basis;
- recovery only enables a fresh server-backed plan preview path;
- approval remains unavailable until a new server-backed preview is produced and explicitly approved;
- browser/local storage remains cache-only and non-authoritative;
- all broad deferred capabilities remain blocked.

## Negative Invariants

This freeze must not accidentally admit:

- runtime behavior;
- approved-plan reopening, replacement, cancellation, deletion, or supersession;
- `L3AnalysisPlan` creation, update, or deletion;
- `L3PassRun` creation;
- `AnalysisRun` creation;
- result review, package review, package construction, package mutation, handoff, export, or connector dispatch;
- output/package/handoff/export artifact creation;
- source/upload/local-directory/RAG/vector expansion;
- broad qualitative/hybrid/RAG execution;
- provider/public URL support;
- frontend-only durable state;
- hidden LLM planning or automatic plan generation;
- package mutation/reconstruction;
- full mockup activation;
- authentication/security hardening.

## Required Future Tests

A later implementation-entry PR must prove:

- recovery is unavailable before a recorded `plan_rejected` or `plan_revision_requested` state;
- recovery succeeds only from the matching recorded terminal revision-control state;
- stale preview id/hash or stale revision-control basis fails closed;
- approved plans block recovery;
- existing pass runs block recovery;
- no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, package, handoff, export, or artifact state is created;
- duplicate `client_request_id` behavior is deterministic;
- browser state cannot recover without server authority;
- UI keeps execution/package/handoff controls unavailable after recovery until a fresh server preview and approval path is completed.

## Stop Conditions

Stop before implementation if the intended change requires:

- schema migration;
- approved-plan supersession, cancellation, or deletion;
- automatic plan generation;
- pass-run creation;
- analysis execution;
- artifact writes;
- package/handoff/export behavior;
- connector/destination behavior;
- source widening;
- broad qualitative/hybrid/RAG behavior;
- full mockup activation;
- authentication/security work while that lane remains deferred.

## Acceptance Criteria

This planning/control slice is accepted when:

- this file exists and contains `selected_future_lifecycle_mode: plan_revision_recovery_lifecycle`;
- `133_PLAN_REVISION_RECOVERY_CONTRACT.md` defines the future API/state contract without making runtime claims;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` classify revision recovery as planning/control only;
- `tools/l3-progress-check.py` fails closed if these docs are missing, if recovery is marked live, or if broad execution/package/connector/source/RAG/mockup/auth behavior is admitted;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` reports no whitespace errors.
