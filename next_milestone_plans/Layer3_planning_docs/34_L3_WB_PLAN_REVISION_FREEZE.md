# Layer 3 Workbench Plan Revision Freeze

Status: planning-only freeze for the fourth Layer 3 workbench slice.

This document freezes the next narrow Layer 3 workbench slice after the landed first-slice shell/API, read-only plan preview, and approval-only plan persistence.

The slice is **plan revision control only**. It admits explicit operator rejection of the current server-backed plan preview and an explicit request to revise the plan basis before approval. It does not admit pass-run creation, analysis execution, result review, package review, handoff, runtime snapshot DB writes, schema widening, qualitative/hybrid/RAG/vector execution, automated plan generation, or hidden LLM planning.

This freeze does not make the behavior live by itself. A later implementation PR must satisfy this freeze and the companion API/state contract before any route, service, UI, or test behavior changes are claimed as live.

## Current Live Boundary

Current `main` already ships:

- the bounded first-slice `/review/layer3` shell/API from PR `#184`, with closeout/correction passes through PR `#190`
- read-only server-backed plan preview from PR `#194`, with proof/board metadata closeouts from PRs `#195` and `#196`
- approval-only `L3AnalysisPlan` persistence from PR `#199`

Current `main` does not ship:

- plan rejection
- plan revision request state
- approved-plan reopening
- approved-plan supersession
- pass-run creation
- analysis execution
- result review
- package review
- handoff
- runtime snapshot DB writes
- schema widening
- qualitative/hybrid/RAG/vector execution
- hidden LLM planning

## Problem Statement

The existing workbench plan panel lets the operator preview a deterministic owner-service plan and then approve that exact current preview. Once approved, the API stores an approval-only `L3AnalysisPlan` and blocks duplicate approval with `plan_already_approved`.

That is correct for the third slice, but it leaves a control-loop gap before any execution slice is considered:

- the operator cannot explicitly reject a preview that is admissible but not acceptable
- the operator cannot record that the plan basis needs revision before approval
- the progress/control packet has only named plan rejection/revision as a candidate, not as a frozen next slice
- without a freeze, a future implementation could accidentally mix rejection/revision with execution, approved-plan reopening, or broader planning semantics

## Slice Decision

The fourth workbench slice is:

> Add explicit operator rejection and revision-request semantics for the current server-backed plan preview before approval, while preserving the approval-only and no-execution boundaries.

This is the next adequate slice because it completes the operator control loop around preview/approval without crossing into execution.

## Admitted Scope

The implementation may add:

- a plan-preview rejection action after a server-backed preview is available
- a revision-request action after a server-backed preview is available
- deterministic request/response DTOs for rejection and revision request
- UI state that records the plan as rejected or revision-requested
- clear disabled/blocked states for approve after rejection or revision request
- summary/readiness fields that expose the revision-control state
- tests proving rejection/revision does not create `L3PassRun`, run analysis, or write artifacts

The implementation may persist rejection/revision state only in the narrowest existing state surface that can represent the decision without schema widening. If the existing state model cannot represent the decision without ambiguity, implementation must stop and return to planning rather than adding migrations by implication.

## Explicit Non-Goals

This slice must not:

- call `materialize_pass_entry(...)`
- create `L3PassRun`
- execute analysis passes
- write input/output manifests
- write package, result, handoff, export, or review-packet artifacts
- add migrations or widen schema unless a later freeze explicitly admits that change
- alter Gate B or Gate C typing semantics
- introduce qualitative, hybrid, RAG/vector, or LLM planning
- replace the owner-service deterministic preview with browser-side planning
- treat rejection as deletion of already persisted approved plans
- reopen or supersede an already approved plan
- infer execution readiness from approval, rejection, or revision-request state

## Approved-Plan Boundary

Already approved plans remain out of scope for this slice.

The current approved-plan implementation deliberately blocks duplicate approval once an approved `L3AnalysisPlan` exists. This freeze does not change that behavior. Reopening, replacing, superseding, or invalidating an already approved plan requires a separate freeze because it would define a new lifecycle for persisted approval records.

## Expected Operator Flow

The target operator flow is:

1. Operator completes the existing first-slice workbench gates through explicit Gate C typing commit.
2. Operator requests read-only plan preview.
3. Workbench shows the server-backed deterministic preview.
4. Operator chooses one of the admitted plan-control actions:
   - approve current preview
   - reject current preview
   - request revision of the current preview basis
5. If operator rejects or requests revision:
   - approval is no longer available for that preview instance
   - downstream execution remains unavailable
   - the UI explains the blocked state without offering execution, package, or handoff controls
6. A later implementation may define how the operator returns to prior gates or refreshes preview state, but this slice does not admit automatic plan regeneration.

## Backend Requirements

Any later implementation must:

- use the current server-recomputed preview id/hash as the decision target
- reject stale preview ids/hashes with a conflict response
- reject requests before Gate C typing commit
- reject requests after an approved plan already exists
- reject requests if pass runs already exist
- reject execution-bearing fields in the request body
- return deterministic blocked reasons and next allowed actions
- keep owner-service preview as the authority for plan basis
- commit no pass-run, execution, package, handoff, or artifact state

## UI Requirements

Any later implementation may extend the existing plan panel only.

The UI must:

- keep approval, rejection, and revision-request actions visibly tied to a current server-backed preview
- disable or hide all downstream execution/result/package/handoff controls
- show a clear terminal preview-state after rejection or revision request
- avoid implying that revision has generated a new plan
- require an explicit preview refresh or earlier-gate change before another approval attempt
- continue to show approval-only persisted state if a plan has already been approved

## Proof Requirements

A later implementation PR must include:

- API tests for unavailable-before-Gate-C behavior
- API tests for preview id/hash mismatch
- API tests for rejection and revision-request success
- API tests proving no `L3PassRun` is created
- API tests proving an already approved plan cannot be rejected or revised by this slice
- UI/page tests for action visibility and disabled downstream state
- headed and headless browser proof for the plan panel, if browser testing is run

## Stop Conditions

Stop and return to planning if implementation requires:

- schema migration
- approved-plan supersession
- deletion of `L3AnalysisPlan`
- pass-run creation
- execution scheduling
- artifact/manifests writes
- qualitative/hybrid/RAG/vector/LLM planning
- changes outside the Layer 3 workbench route/service/UI/test surfaces

## Relationship To Prior Slices

This slice depends on:

- `30_L3_WB_PLAN_PREVIEW_FREEZE.md`
- `31_L3_WB_PLAN_PREVIEW_API_AND_STATE_CONTRACT.md`
- `32_L3_WB_PLAN_APPROVAL_FREEZE.md`
- `33_L3_WB_PLAN_APPROVAL_API_AND_STATE_CONTRACT.md`

It does not replace or weaken those freezes. It only adds pre-execution operator control around an unapproved preview.
