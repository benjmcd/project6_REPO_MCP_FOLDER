# Layer 3 Workbench Execution Readiness Freeze

Status: current-main planning-only freeze for the next Layer 3 workbench readiness pass.

This document freezes a non-execution preparation slice after the landed first-slice shell/API, read-only plan preview, approval-only plan persistence, and bounded pre-approval revision-control path.

The slice is **execution-readiness only**. It does not admit pass-run creation, analysis execution, result review, package review, handoff, runtime snapshot DB writes, schema widening, qualitative/hybrid/RAG/vector execution, local upload ingestion, or hidden LLM planning.

## Current Live Boundary

Current `main` already ships the bounded workbench surface through:

- first-slice shell/API from PR `#184`, with closeout/correction passes through PR `#190`
- read-only plan preview from PR `#194`, with proof/board metadata closeouts from PRs `#195` and `#196`
- approval-only `L3AnalysisPlan` persistence from PR `#199`
- pre-approval plan rejection/revision-control from PR `#205`, hardened by PR `#207`
- docs/progress cohesion syncs through PRs `#208` and `#209`, plus later wording syncs through current `main`

Current `main` does not ship execution, `L3PassRun` creation from the workbench, result/package/handoff review, approved-plan supersession, runtime DB/schema widening, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Problem Statement

The repo now has enough workbench surface to make execution feel adjacent, but not enough frozen contract detail to make execution safe. The remaining risk is not that current behavior is broken; it is that a future execution slice could accidentally rely on scattered prose, browser-only state, stale proof claims, or under-specified preview identity semantics.

Before execution can be selected, the repo needs a single readiness packet that:

- keeps proof claims machine-checkable instead of only prose-bound
- freezes canonical state, preview-hash, idempotency, and concurrency semantics
- defines how revision-requested previews can return to an approvable preview basis
- keeps approved-plan correction/supersession separate from current terminal approved-plan behavior
- defines minimum output provenance terms before result/package UI exists

## Slice Decision

The next adequate Layer 3 workbench slice is:

> Add an execution-readiness control packet and proof manifest that define the preconditions for any later execution implementation, while keeping all runtime execution behavior unavailable.

This is the correct next slice because it reduces ambiguity and future blast radius without introducing new backend side effects.

## Admitted Scope

The PR `#212` readiness slice added planning/control artifacts only:

- an execution-readiness freeze
- a state/hash/idempotency companion contract
- a machine-readable proof/readiness manifest
- progress/front-door references that identify the packet as planning-only
- validation rules that fail closed when required proof or no-go boundaries are missing

A later bounded implementation-readiness slice may add a read-only readiness-contract API surface or preview-identity metadata only if it still does not create execution, pass runs, result/package/handoff state, migrations, runtime artifact writes, or source-breadth expansion.

## Explicit Non-Goals

This slice must not:

- create `L3PassRun`
- call `materialize_pass_entry(...)` from the workbench path
- run analysis
- write manifests, result artifacts, package artifacts, or handoff artifacts
- add migrations
- add runtime DB writes
- change `/review/layer3` behavior
- change `/api/v1/layer3/...` runtime behavior
- implement RAG/vector/local upload/source-ingestion expansion
- implement qualitative or hybrid execution
- reopen or supersede approved plans
- treat the mockup spec as implementation permission

## Readiness Gates Before Execution

A later execution slice is not eligible until a separate implementation freeze can cite all of the following as already satisfied or explicitly deferred with a no-go reason:

| Gate | Required decision | Why it blocks execution |
| --- | --- | --- |
| Proof manifest | Exact proof commands, expected results, and source files are machine-readable | Prevents prose-only proof drift |
| State model | Every workbench state has an allowed next action and blocked downstream posture | Prevents browser-only or dead-end state transitions |
| Preview hash | The canonical hash basis and mismatch behavior are frozen | Prevents stale preview approval or execution |
| Idempotency | Client request ids and duplicate/retry behavior are defined per endpoint | Prevents duplicate execution or ambiguous writes |
| Concurrency | Concurrent approval/revision/execution attempts have a serialized authority rule | Prevents racing state transitions |
| Revision recovery | `plan_revision_requested` has an explicit return-to-preview rule | Prevents a dead-end operator state |
| Approved-plan correction | Pre-execution cancellation/supersession is either frozen or explicitly unavailable | Prevents hidden lifecycle mutation |
| Output taxonomy | Datum/fact/finding/insight/caveat/result/package terms are defined or deferred | Prevents result UI from inventing semantics |
| Source breadth | RAG/vector/upload/local-directory scope is frozen or explicitly unavailable | Prevents source expansion inside execution |
| Browser proof | Headed and headless proof requirements are named for any future UI behavior | Prevents UI-only readiness claims |

## Proof Requirements For PR #212 Planning Slice

The PR `#212` planning-only readiness slice must prove:

- JSON validity for the proof/readiness manifest
- all manifest-declared repo paths exist
- no current live-scope wording claims execution, results, package review, handoff, qualitative/hybrid execution, RAG/vector execution, runtime DB writes, schema widening, or full mockup activation
- focused Layer 3 backend/page tests still pass
- `git diff --check` passes

Browser proof is not required for the PR `#212` docs-only readiness slice because it changes no runtime UI behavior. A backend-only implementation-readiness metadata slice also does not require browser proof if rendered UI behavior is unchanged. A later UI or execution slice must run both headed and headless browser proof when browser behavior changes.

## Stop Conditions

Stop and return to planning if a slice requires:

- execution-bearing code behavior changes
- route/API response changes beyond read-only readiness metadata or preview identity/hash metadata
- database migration
- runtime artifact generation
- execution semantics
- approved-plan mutation
- source-ingestion expansion
- replacing the current progress artifact rather than adding an explicit readiness companion

## Relationship To Existing Docs

This freeze depends on:

- `34_L3_WB_PLAN_REVISION_FREEZE.md`
- `35_L3_WB_PLAN_REVISION_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3-mockups/mockup-spec.txt`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

It does not replace those documents. It adds the missing execution-readiness layer between revision-control and any future execution implementation.
