# Layer 3 Workbench Package Review Submit Freeze

Status: planning-only freeze for the next package-review submit/decision boundary after merged PR `#238` package construction.

This document freezes only a future bounded package-review submit/decision step for the current `/review/layer3` workbench chain. It does not implement package-review submission by itself, does not make handoff/export live, does not admit package reconstruction, and does not authorize package payload mutation or package variant editing.

## Current Live Boundary

Current `project6-origin/main` through PR `#238` includes:

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
- read-only package-review preview endpoint/UI inspection from PR `#235`
- bounded package-construction commit from PR `#238`

The current live chain may construct exactly one reconciliation row, exactly three output-package rows, and exactly three package payload files after approved selected-pass result-review authority and matching package-preview hash. It still does not submit package-review decisions, approve or reject package review, trigger handoff/export, activate editable package variants, reopen result review, widen source/runtime/schema scope, or activate the full mockup target state.

## Slice Decision

The next adequate Layer 3 workbench planning boundary is:

> Freeze a bounded package-review submit/decision step after package construction has produced a complete, hash-stable package set. The step may record one operator package-review decision over the constructed reconciliation record and its three output packages. It must not rewrite packages, create new packages, trigger handoff/export, create artifacts, reopen result review, widen source/schema/runtime behavior, or activate full mockup behavior.

This is the smallest safe step after PR `#238` because package-review decision state is the direct missing bridge between constructed packages and any later handoff/export policy. Keeping the decision separate from handoff/export prevents an approval click from silently becoming an APS handoff or downstream export.

## Decision Vocabulary

A future implementation governed by this freeze may admit only these operator package-review decisions:

| Decision | Meaning | Allowed next state |
| --- | --- | --- |
| `approved` | The constructed package set is accepted for later downstream handoff/export consideration. | `package_review_approved` |
| `changes_requested` | The package set is not accepted as-is and requires a separately frozen rebuild/amendment path before handoff. | `package_review_changes_requested` |
| `rejected` | The package set is not accepted and must not proceed to handoff/export. | `package_review_rejected` |
| `blocked` | The operator cannot decide because required evidence, package visibility, or authority is insufficient. | `package_review_blocked` |

The decision vocabulary is intentionally about review disposition only. It is not a package rebuild command, handoff command, export command, rerun command, result-review amendment, or approved-plan supersession.

## Admitted Future Implementation Scope

An implementation PR governed by this freeze may add only:

- one package-review submit/decision endpoint for one current session
- server validation that `package_constructed` state exists and is complete
- server validation that exactly one `L3ReconciliationRecord` and exactly three `L3OutputPackage` rows exist for the session
- server validation that package kinds are exactly `canonical_internal`, `user_facing`, and `review_facing`
- server validation that supplied package ids and payload hashes match stored package rows
- server validation that the package construction authority basis still matches the approved plan, selected pass, result-review record, preview identity, and package-preview hash
- one durable package-review decision summary in existing JSON-bearing state, if no schema widening is required
- idempotent retry handling for an identical decision request
- focused backend tests proving exact write boundaries, immutable package payload refs/hashes, fail-closed stale authority, and no handoff/export side effects
- optional `/review/layer3` UI enablement of package-review decision controls only after server authority marks the constructed package set reviewable

## Persistence Boundary

Preferred implementation should persist the bounded package-review decision in existing durable JSON fields:

- `L3ReconciliationRecord.summary_json`
- optional `L3Session.summary_json` pointer/index summary

The implementation must not add a schema migration under this freeze. If durable audit/query requirements cannot be met without a new package-review model or migration, stop and create a separate schema/persistence freeze.

The implementation must not mutate:

- package payload files
- `L3OutputPackage.payload_ref`
- `L3OutputPackage.payload_hash`
- package payload bodies
- result-review record state
- approved plan state
- selected pass output metadata

Updating `L3OutputPackage.status` is not admitted by default. If implementation proves that package status changes are required, that must be frozen separately because the current package statuses already encode package construction output state.

## Explicit Non-Goals

This freeze does not admit:

- handoff/export trigger policy
- APS handoff behavior
- package payload rewrite or regeneration
- package variant tabs as editable live controls
- result-review amendment or supersession
- approved-plan reopening, correction, or supersession
- rerun, retry, recovery, cancellation, or replay controls beyond deterministic decision idempotency
- new `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, or `AnalysisArtifact` creation
- analysis execution
- new package rows or reconciliation rows
- artifact manifest creation
- source expansion
- local upload or local-directory ingestion
- runtime snapshot DB writes
- schema migrations
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

## Required Preconditions

A future implementation must require all of these before package-review submit/decision:

- existing `L3Session`
- current approved `L3AnalysisPlan`
- approved preview id/hash matching the request
- exactly one selected terminal `L3PassRun` matching the approved plan
- selected-pass result/status authority with readable output metadata
- existing approved selected-pass result-review state
- matching `result_review_record_ref`
- existing package-review preview basis
- existing bounded package-construction commit summary
- exactly one `L3ReconciliationRecord` for the session
- exactly three `L3OutputPackage` rows for the session
- package rows whose `payload_ref` and `payload_hash` are present and match the request
- no existing conflicting package-review decision state
- no forbidden handoff/export, package rewrite, source, schema, runtime, rerun, or output-rewrite fields in the request

## Write Boundary

The future implementation may write exactly:

| Target | Allowed amount | Reason |
| --- | --- | --- |
| `L3ReconciliationRecord.summary_json` | one package-review decision object | Existing reconciliation record is the durable package-set anchor |
| `L3Session.summary_json` | optional decision pointer/index | Allows session summary to report review state without creating new rows |

It must not write:

- additional `L3ReconciliationRecord` rows
- additional `L3OutputPackage` rows
- package payload files
- `AnalysisArtifact` rows
- handoff/export rows or artifacts
- new analysis plan/pass/run rows
- source-ingestion rows
- runtime snapshot DB rows
- schema/migration files

## UI Boundary

If rendered `/review/layer3` behavior changes, the UI may only expose:

- read-only constructed package summary
- package ids, kinds, payload refs, payload hashes, and statuses as server-provided evidence
- one package-review decision form gated by server state
- allowed decisions from this freeze only
- disabled handoff and export indicators after decision submission
- read-only post-decision summary

The UI must not expose editable package variants, package payload editors, handoff/export controls, rerun/recovery controls, source pickers, local upload/directory selectors, raw output editors, qualitative/hybrid/RAG/vector controls, or full mockup-only controls.

## Required Proof

An implementation PR governed by this freeze must prove:

- submit requires current approved plan, preview id/hash, selected terminal pass, result/status authority, approved result-review state, matching package-preview basis, and constructed package rows
- missing or partial package construction fails closed
- stale package ids, package kinds, payload refs, or payload hashes fail closed
- non-approved result-review state fails closed
- forbidden request fields fail closed
- successful submit records exactly one package-review decision object
- duplicate identical decision requests are deterministic and do not duplicate decision state
- conflicting duplicate requests fail closed
- no package payload refs or hashes change
- no package payload files are created, deleted, or rewritten
- no new `L3ReconciliationRecord`, `L3OutputPackage`, `AnalysisArtifact`, handoff/export, runtime DB, schema, source-ingestion, plan, pass, or run rows are created
- handoff/export remains disabled after `package_review_approved`
- existing package construction tests still pass
- both headed and headless Chrome browser proof pass if rendered `/review/layer3` behavior changes

## Stop Conditions

Stop before implementation if any of these becomes necessary:

- handoff/export behavior
- package payload rewrite or package reconstruction
- schema migration
- new package-review table/model
- updating `L3OutputPackage.status`
- creating more package rows or reconciliation rows
- creating `AnalysisArtifact` rows
- rerun/recovery/cancellation/retry behavior beyond deterministic decision idempotency
- result-review amendment or supersession
- approved-plan supersession
- source expansion or local ingestion
- runtime DB widening
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

## Relationship To Existing Docs

This freeze is downstream of:

- `50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`
- `51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md`
- `48_L3_WB_PACKAGE_REVIEW_FREEZE.md`
- `49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md`
- `46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`
- `44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`

It narrows only the next package-review submit/decision boundary. It does not replace the package-construction contract and does not make APS handoff or export live.
