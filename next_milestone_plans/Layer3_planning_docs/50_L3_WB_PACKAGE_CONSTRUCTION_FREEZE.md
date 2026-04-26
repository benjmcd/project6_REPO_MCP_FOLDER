# Layer 3 Workbench Package Construction Freeze

Status: planning-only freeze for the next package-construction boundary after merged PR `#235` read-only package-review preview.

This document freezes only a future bounded package-construction commit step for the current `/review/layer3` workbench chain. It does not implement package construction by itself, does not make package-review submission live, does not admit handoff/export, and does not authorize calling `materialize_package_entry(...)` as-is from the workbench selected-pass path.

## Current Live Boundary

Current `project6-origin/main` through PR `#236` includes:

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
- planning-only package-review preview governance from PR `#234`
- read-only package-review preview endpoint/UI inspection from PR `#235`
- post-PR235 docs/status sync from PR `#236`
- existing Gate D package owner service and models in `layer3_package_entry.py`, `L3OutputPackage`, and `L3ReconciliationRecord`

The current live chain still does not construct packages from the workbench path, create workbench package payload files, submit package-review decisions, trigger handoff/export, activate package variant editing, reopen result review, widen source/runtime/schema scope, or activate the full mockup target state.

## Slice Decision

The next adequate Layer 3 workbench planning boundary is:

> Freeze a bounded package-construction commit step after a server-validated read-only package-review preview is available for one approved selected-pass result review. The step may create exactly one reconciliation record, exactly three package rows, and exactly three package payload files for the existing package families. It must not submit or approve package review, hand off or export packages, create new analysis state, expand sources, widen schema/runtime behavior, or activate full mockup behavior.

This is the smallest safe step after PR `#235` because package construction is the direct missing bridge between read-only package-review preview and later package-review submission/handoff. It also keeps the write boundary narrow enough to test and audit without conflating package creation with package review approval or APS handoff.

## Canonical Owner Boundary

The repo already has a package owner service:

- `backend/app/services/layer3_package_entry.py`
- `backend/app/models/models.py` `L3OutputPackage`
- `backend/app/models/models.py` `L3ReconciliationRecord`
- `backend/tests/test_layer3_package_entry.py`

That service is the implementation truth for existing Gate D package-entry behavior. However, `materialize_package_entry(...)` expects terminal full-session Gate D inputs such as `phase1a_loading_closure` and `pass_entry`. PR `#235` deliberately showed the current workbench selected-pass path as not construction-compatible with that function as-is.

A future implementation governed by this freeze must therefore do one of the following:

| Option | Decision | Constraint |
| --- | --- | --- |
| Preferred | add a narrow owner-service helper inside `layer3_package_entry.py` for workbench selected-pass package commit | It must reuse existing package constants, row models, payload persistence conventions, and pure payload builders where compatible |
| Acceptable | refactor shared pure package builders inside the owner-service module, then call them from a workbench-specific commit helper | It must preserve existing Gate D `materialize_package_entry(...)` behavior and tests |
| Not admitted | call `materialize_package_entry(...)` as-is after fabricating `phase1a_loading_closure` or `pass_entry` | Fabricated compatibility would collapse the authority distinction between Gate D package entry and workbench selected-pass state |

The route/controller must not hand-roll durable package payload semantics outside the owner-service module.

## Admitted Future Implementation Scope

An implementation PR governed by this freeze may add only:

- one package-construction commit endpoint for one current session
- server validation that the package-review preview basis still matches current approved plan, selected pass, result/status authority, approved result-review state, preview id/hash, and result-review record reference
- a workbench-compatible owner-service helper that writes the admitted package construction artifacts
- exactly one `L3ReconciliationRecord` for the session
- exactly three `L3OutputPackage` rows for `canonical_internal`, `user_facing`, and `review_facing`
- exactly three package payload files under the existing Layer 3 artifact storage convention
- idempotent retry handling for an identical commit request
- focused backend tests proving the exact write set, no duplicate package rows, fail-closed stale authority, and no downstream handoff/export side effects
- optional `/review/layer3` UI enablement of a package commit control only after server authority marks package commit ready

## Explicit Non-Goals

This freeze does not admit:

- package-review submission, approval, rejection, or decision persistence beyond the package-construction commit itself
- handoff/export trigger policy
- APS handoff behavior
- package variant tabs as editable live controls
- raw package payload editing or rewrite controls
- result-review amendment or supersession
- approved-plan reopening, correction, or supersession
- rerun, retry, recovery, cancellation, or replay controls beyond deterministic commit idempotency
- new `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, or `AnalysisArtifact` creation
- analysis execution
- artifact manifest creation outside the package payload refs
- source expansion
- local upload or local-directory ingestion
- runtime snapshot DB writes
- schema migrations
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

## Required Preconditions

A future implementation must require all of these before package construction:

- existing `L3Session`
- current approved `L3AnalysisPlan`
- approved preview id/hash matching the request
- exactly one selected terminal `L3PassRun` matching the approved plan
- selected-pass result/status authority with readable output metadata
- existing approved selected-pass result-review state
- matching `result_review_record_ref`
- unresolved trace count of zero for the approved review
- PR `#235` package-review preview basis still available and matching the commit request
- no existing `L3ReconciliationRecord` for the session
- no existing `L3OutputPackage` rows for the session
- no forbidden package-review submission, handoff/export, source, schema, runtime, rerun, or output-rewrite fields in the request

## Write Boundary

The future implementation may write exactly:

| Target | Allowed amount | Reason |
| --- | --- | --- |
| `L3ReconciliationRecord` | one row per session | Existing model represents package-level reconciliation summary |
| `L3OutputPackage` | three rows per session | Existing package families are `canonical_internal`, `user_facing`, and `review_facing` |
| package payload files | three files per successful commit | Existing owner-service package rows store `payload_ref` and `payload_hash` |
| `L3Session.summary_json` | optional package-construction summary only | Allowed only as an index/audit pointer to created package rows; not as package-review decision state |

It must not write:

- additional package rows beyond the three admitted package kinds
- handoff/export rows or artifacts
- new analysis plan/pass/run rows
- `AnalysisArtifact` rows for package construction
- source-ingestion rows
- runtime snapshot DB rows
- schema/migration files

## UI Boundary

If rendered `/review/layer3` behavior changes, the UI may only expose:

- package commit readiness after server validation
- package candidate kind summaries for the three existing package kinds
- a single package construction commit action, gated by server state
- emitted package row ids, payload refs, hashes, and statuses after a successful commit
- package-review submit, handoff, and export as disabled or unavailable downstream actions

The UI must not expose editable package variants, package-review decision controls, handoff/export controls, rerun/recovery controls, source pickers, local upload/directory selectors, raw output editors, or qualitative/hybrid/RAG/vector controls.

## Required Proof

An implementation PR governed by this freeze must prove:

- commit requires current approved plan, preview id/hash, selected terminal pass, result/status authority, approved result-review state, and matching package-preview basis
- stale preview id/hash, stale result-review record, non-approved review state, missing output metadata, unresolved trace, foreign plan/pass/session, and existing package rows fail closed
- forbidden request fields fail closed
- successful commit creates exactly one `L3ReconciliationRecord`, exactly three `L3OutputPackage` rows, and exactly three payload files
- emitted package kinds are exactly `canonical_internal`, `user_facing`, and `review_facing`
- duplicate identical commit requests are deterministic and do not duplicate rows or payloads
- conflicting duplicate requests fail closed
- no package-review submit/decision, handoff/export, analysis execution, new plan/pass/run/artifact rows, schema/runtime/source widening, or full mockup behavior is created
- existing Gate D package-entry tests still pass
- both headed and headless Chrome browser proof pass if rendered `/review/layer3` behavior changes

## Stop Conditions

Stop before implementation if any of these becomes necessary:

- package-review submit/decision semantics
- handoff/export behavior
- schema migration
- calling `materialize_package_entry(...)` as-is from `/review/layer3`
- fabricating Gate D `phase1a_loading_closure` or `pass_entry` fields
- creating more than one reconciliation row or more than the three admitted package rows
- creating `AnalysisArtifact` rows for package construction
- rerun/recovery/cancellation/retry behavior beyond deterministic commit idempotency
- result-review amendment or supersession
- approved-plan supersession
- source expansion or local ingestion
- runtime DB widening
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

## Relationship To Existing Docs

This freeze is downstream of:

- `48_L3_WB_PACKAGE_REVIEW_FREEZE.md`
- `49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md`
- `46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`
- `44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`
- `42_L3_WB_RESULT_STATUS_FREEZE.md`
- `43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`
- `08_GATED_PACKAGE_FREEZE.md`

It narrows only the next package-construction commit boundary. It does not replace the older Gate D package-entry owner-service contract and does not make package-review submission or APS handoff live.
