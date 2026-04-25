# Layer 3 Workbench Execution Selection Freeze

Status: planning-only freeze for the next Layer 3 workbench execution-selection tranche.

This document freezes the narrowest eligible execution-bearing boundary after the landed first-slice shell/API, read-only plan preview, approval-only plan persistence, pre-approval revision-control, and read-only readiness proof.

The selected future implementation target is not full execution. It is an execution-selection/pass-run shell boundary that may create the first durable execution-selection record only after an approved plan is proven current. It still must not run analysis, generate results, create package review state, create handoff state, widen runtime DB/schema behavior, admit qualitative/hybrid/RAG/vector execution, ingest local uploads/directories, or activate the full mockup target state.

## Current Live Boundary

Current `main` already ships:

- first-slice shell/API from PR `#184`, with closeout/correction passes through PR `#190`
- read-only plan preview from PR `#194`, with proof/board metadata closeouts from PRs `#195` and `#196`
- approval-only `L3AnalysisPlan` persistence from PR `#199`
- pre-approval plan rejection/revision-control from PR `#205`, hardened by PR `#207`
- execution-readiness proof/state packet from PR `#212`
- read-only readiness proof from PR `#213`
- post-merge progress/proof sync from PR `#214`

Current `main` does not ship workbench execution selection, `L3PassRun` creation from an approved workbench plan, analysis execution, result/package/handoff review, approved-plan correction or supersession, runtime DB/schema widening, qualitative/hybrid/RAG/vector execution, source-ingestion expansion, or full mockup activation.

## Problem Statement

The readiness proof now exposes the state/hash/idempotency/concurrency contract, but it intentionally keeps several decisions unresolved. The repo needs one more planning-only freeze before any code can create an execution-bearing object from the workbench path.

The risk to avoid is a jump from approved-plan persistence directly into `materialize_pass_entry(...)` or analysis execution. That would bypass the workbench-specific approved-plan authority, preview-hash proof, idempotency behavior, and no-go boundaries that the readiness packet was created to protect.

## Slice Decision

The next adequate Layer 3 workbench tranche is:

> Freeze execution selection as a separate pass-run shell boundary after approved-plan validation, before analysis execution or result/package/handoff behavior.

This is the smallest safe step because it lets a future implementation prove that an approved plan can be selected for execution under server authority without also running analysis or inventing result semantics.

## Admitted Future Implementation Scope

A later implementation PR governed by this freeze may add only:

- one server-authoritative execution-selection endpoint under the existing Layer 3 API family
- server-side validation that the session has exactly one current approved plan
- preview identity/hash validation against the approved plan's stored preview basis
- serialized state transition authority for execution selection
- deterministic idempotency behavior for duplicate execution-selection requests
- creation of `L3PassRun` shell rows only for approved plan sets that are already present in `L3AnalysisPlan.plan_json`
- summary/status metadata that records execution selection as selected/not-started, not running or completed
- focused backend tests proving creation, duplicate handling, stale hash blocking, revision/rejection blocking, and no analysis execution
- headed and headless browser proof only if rendered UI behavior changes

## Explicit Non-Goals

This freeze does not admit:

- calling the existing `materialize_pass_entry(...)` workbench path as-is
- creating `AnalysisRun`
- running analysis
- writing result artifacts, package artifacts, handoff artifacts, or artifact manifests
- result review UI
- package review UI
- handoff UI or export behavior
- approved-plan cancellation, replacement, reopening, or supersession
- execution against `plan_rejected` or `plan_revision_requested`
- local upload ingestion
- local directory ingestion
- RAG/vector retrieval
- qualitative or hybrid execution
- runtime snapshot DB writes
- schema migrations unless a later implementation freeze proves the existing schema cannot hold the selected shell state
- full mockup activation

## Required Decisions Frozen Here

| Gate | Decision | Reasoning |
| --- | --- | --- |
| Revision recovery | `plan_revision_requested` remains non-executable; execution selection requires a fresh approved plan after the operator returns through the existing Gate C/plan-preview/approval path or a later freeze defines a narrower refresh path | This avoids hidden regeneration and keeps the current revision-control slice bounded |
| Approved-plan correction | approved plans remain terminal for this tranche; cancellation, replacement, and supersession remain unavailable | This avoids lifecycle mutation before execution locking and output semantics are frozen |
| Execution write boundary | the first execution-bearing write may create `L3PassRun` shell rows only; it must not create `AnalysisRun` or artifacts | This gives the next code slice a narrow, testable durable side effect |
| Idempotency | execution-selection requests require a `client_request_id`; duplicate ids for the same approved plan return the existing selection state, while conflicting duplicate payloads fail closed | This prevents duplicate pass-run shells and ambiguous retry behavior |
| Concurrency | execution selection must be serialized by server transaction/row lock around the session and approved plan | Browser in-flight state is useful UX but cannot be authority |
| Preview hash | stale or missing approved-plan preview identity/hash blocks execution selection with `preview_mismatch` or equivalent fail-closed error | This prevents execution from stale previews |
| Output taxonomy | result/package taxonomy remains deferred because this tranche does not produce results | This avoids inventing result semantics before result UI exists |
| Source breadth | source breadth remains the current approved-plan source set only | This prevents RAG/vector/upload/local-directory expansion inside execution selection |

## Required Future Proof

A later implementation PR governed by this freeze must prove:

- no `AnalysisRun` is created by execution selection
- no artifact, result, package, or handoff files are written
- duplicate `client_request_id` behavior is deterministic
- stale preview identity/hash fails closed
- rejected or revision-requested sessions cannot be selected for execution
- approved-plan terminal behavior is preserved
- row-lock or equivalent serialization is used for the write boundary
- all relevant Layer 3 focused tests pass
- browser proof is run in both headed and headless Chrome if the UI changes

## Stop Conditions

Stop and return to planning if the implementation requires:

- running analysis in the same tranche
- introducing result/package/handoff semantics
- reopening or superseding approved plans
- adding source breadth
- adding migrations without a separate schema-widening proof
- using browser state as authority
- treating the mockup visuals as permission to activate all later UI states

## Relationship To Existing Docs

This freeze depends on:

- `36_L3_WB_EXECUTION_READINESS_FREEZE.md`
- `37_L3_WB_STATE_HASH_IDEMPOTENCY_CONTRACT.md`
- `39_L3_WB_EXECUTION_SELECTION_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

It does not replace the readiness proof packet. It narrows the next eligible implementation target from broad execution to execution selection/pass-run shell creation only.
