# Layer 3 Workbench Package Review Freeze

Status: governing planning-only freeze for the next package-review planning boundary after merged PR `#232`.

This document freezes only the next package-review preview and governance boundary for the current `/review/layer3` workbench chain. It does not implement package review by itself, does not create `L3OutputPackage` or `L3ReconciliationRecord` rows, does not call `materialize_package_entry(...)` as-is, and does not admit handoff/export, rerun/recovery, source expansion, schema/runtime widening, local upload/directory ingestion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Current Live Boundary

Current `project6-origin/main` through PR `#232` includes:

- the `/review/layer3` workbench shell from PR `#184`
- read-only plan preview from PR `#194`
- approval-only plan persistence from PR `#199`
- pre-approval plan revision-control from PR `#205` and PR `#207`
- read-only execution-readiness proof from PR `#213`
- backend execution-selection/pass-run shell creation from PR `#216`
- backend selected-pass analysis-execution start from PR `#218`
- backend selected-pass result/status inspection from PR `#222`
- backend selected-pass result-review recording from PR `#227`
- bounded result-review UI controls from PR `#232`
- existing Gate D package owner service and models in `layer3_package_entry.py`, `L3OutputPackage`, and `L3ReconciliationRecord`

The current `/review/layer3` workbench chain still does not expose package review, package construction, package rows, package variants, handoff/export, rerun/recovery, execution selection/start UI, source/schema/runtime widening, qualitative/hybrid/RAG/vector execution, or full mockup behavior.

## Package Owner-Service Boundary

The repo already has a package owner service:

- `backend/app/services/layer3_package_entry.py`
- `backend/app/models/models.py` `L3OutputPackage`
- `backend/app/models/models.py` `L3ReconciliationRecord`
- `backend/tests/test_layer3_package_entry.py`

That owner service is implementation truth for existing Gate D package-entry behavior. It is not automatically compatible with the current `/review/layer3` selected-pass chain, because `materialize_package_entry(...)` expects full terminal session/package-entry preconditions such as `phase1a_loading_closure` and `pass_entry`.

Therefore the next workbench package-review boundary must not call `materialize_package_entry(...)` as-is from `/review/layer3` unless a later implementation-specific contract proves that the current workbench session has the required owner-service inputs without fabricating or bypassing them.

## Slice Decision

The next adequate Layer 3 workbench planning boundary is:

> Freeze a bounded package-review preview/governance step after one selected-pass result-review decision is already recorded as `approved`. The step may reason about package-review readiness and package-candidate projection for the approved selected pass, but it must not create durable package/reconciliation rows, package variants, package-review decisions, handoff/export artifacts, rerun/recovery state, new execution state, source/schema/runtime widening, or full mockup behavior.

This is the smallest safe post-result-review step because it acknowledges the mockup's package-review direction and the repo's existing package owner service while avoiding an unsafe jump from one selected-pass result review into full Gate D package construction or downstream APS handoff.

## Admitted Future Implementation Scope

An implementation PR governed by this freeze may add only:

- a read-only package-review readiness or preview surface for one current session
- server validation that exactly one selected terminal pass has an already-recorded approved result-review state
- server validation that the approved plan, preview id/hash, selected pass, analysis run, result/status authority, and result-review record still match
- a package-candidate projection that lists candidate package kinds without writing package artifacts
- a compatibility assessment against the existing package owner service inputs
- disabled package construction, package review submission, and handoff controls in the UI if rendered behavior changes
- proof that no `L3OutputPackage`, `L3ReconciliationRecord`, `AnalysisArtifact`, handoff row, source-ingestion row, runtime snapshot row, or schema/migration file is created
- focused tests proving fail-closed package-review readiness behavior

The future implementation may choose a narrow read-only endpoint only if existing session summary data is insufficient. That endpoint must be frozen by `49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md` and must not write durable state.

## Explicit Non-Goals

This freeze does not admit:

- durable package construction
- package-review submission or approval
- `L3OutputPackage` row creation
- `L3ReconciliationRecord` row creation
- package payload file writes
- package variant tabs as active controls
- handoff/export UI
- handoff/export artifacts
- APS handoff behavior
- rerun, retry, recovery, cancellation, or replay controls
- result-review amendment or supersession
- batch or multi-pass package review
- free-form package source selection
- approved-plan reopening or supersession
- source-picker expansion
- local upload or local-directory ingestion
- schema migrations
- runtime snapshot DB writes
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

If implementation proves that package review cannot be usefully previewed without durable package construction, stop and create a separate package-construction freeze before writing package rows or payload files.

## Required Decisions

| Gate | Decision | Reasoning |
| --- | --- | --- |
| Review prerequisite | require an already-recorded approved selected-pass result review | Package-review preview should not promote unreviewed, rejected, blocked, or changes-requested output |
| Review unit | one current approved selected pass only | This preserves the PR `#216` through PR `#232` one-pass chain and avoids multi-pass aggregation semantics |
| Owner-service posture | treat `layer3_package_entry.py` as package owner-service truth, not as a callable shortcut | Existing owner-service preconditions are full Gate D package-entry preconditions and may not match the workbench selected-pass path |
| Package candidate kinds | preview only `canonical_internal`, `user_facing`, and `review_facing` as possible later package families | These are the existing package-entry families; previewing them does not create rows or payloads |
| Write boundary | read-only package-review preview only | Durable package/reconciliation rows need a separate construction contract |
| UI posture | show package review as unavailable or preview-only unless server authority marks it ready | Browser state cannot authorize package review or package creation |
| Downstream posture | handoff/export remains unavailable | Package review is not an APS handoff trigger |

## Required Proof

An implementation PR governed by this freeze must prove:

- package-review preview requires a current session, approved plan, approved preview id/hash, selected terminal pass, result/status authority, and approved result-review state
- missing or non-approved result review fails closed
- stale preview id/hash fails closed
- foreign-session, foreign-plan, foreign-pass, non-selected, non-terminal, missing-output, or unresolved-trace states fail closed
- the preview does not call `materialize_package_entry(...)` as-is unless a later contract proves compatibility
- no `L3OutputPackage` or `L3ReconciliationRecord` rows are created
- no package payload files, package artifacts, handoff artifacts, runtime DB rows, schema migrations, source-ingestion rows, or new execution rows are created
- package candidate projection is clearly marked preview/readiness only
- package-review submission, package construction, and handoff/export controls remain disabled or absent
- all relevant Layer 3 focused backend tests pass
- both headed and headless Chrome browser proof pass if rendered `/review/layer3` behavior changes

## Stop Conditions

Stop before implementation if any of these becomes necessary:

- writing `L3OutputPackage` or `L3ReconciliationRecord`
- writing package payload files
- creating package-review decision state
- invoking full `materialize_package_entry(...)` from `/review/layer3` without a separate compatibility contract
- activating package variant tabs as live package controls
- handoff/export behavior
- rerun/recovery/cancellation/retry behavior
- result amendment or supersession
- source expansion or local ingestion
- runtime DB or schema widening
- full mockup activation

## Relationship To Existing Docs

This freeze is downstream of:

- `46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`
- `44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`
- `42_L3_WB_RESULT_STATUS_FREEZE.md`
- `43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`
- `08_GATED_PACKAGE_FREEZE.md`

It freezes only package-review preview/governance for the workbench path after approved selected-pass result review. It does not replace the older Gate D package-entry owner-service contract and does not make package review live by itself.
