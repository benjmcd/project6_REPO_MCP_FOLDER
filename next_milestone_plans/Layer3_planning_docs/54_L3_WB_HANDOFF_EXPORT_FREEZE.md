# Layer 3 Workbench Handoff Export Freeze

Status: planning-only freeze for the next handoff/export governance boundary after merged package-review submit UI hardening.

This document freezes only a future bounded handoff/export preparation and authorization step for the current `/review/layer3` workbench chain. It does not implement handoff/export by itself, does not make APS handoff live, does not transfer packages to a downstream consumer, does not create `AnalysisArtifact` rows, and does not authorize package payload mutation, package reconstruction, schema/runtime/source widening, or full mockup activation.

## Current Live Boundary

Current `project6-origin/main` at planning base commit `ec58ac80ab5033f8a815195bdf9f44f41e42d532` includes:

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
- planning-only package-review submit governance from PR `#241`
- bounded backend package-review submit from PR `#243`
- bounded rendered package-review controls from PR `#245`
- PR `#247` fallback hardening for package-review submit readiness after package construction commit
- PR `#248` and PR `#249` docs/proof/metadata syncs for that current package-review UI state

The current live chain can inspect package-review preview, commit the bounded package set, and submit one bounded package-review decision. A successful package-review submit may record `package_review_approved`, but the live backend still sets `handoff_enabled` and `export_enabled` to `false` and reports `handoff` and `export` as downstream unavailable. There is no workbench-specific handoff/export endpoint, model, route, rendered control, APS dispatch, or external transfer live in this boundary.

## Slice Decision

The next adequate Layer 3 workbench planning boundary is:

> Freeze a bounded handoff/export preparation and authorization step after package-review approval. The step may prepare one server-authoritative internal export envelope over the already reviewed package set and record one operator handoff/export disposition. It must not dispatch to APS or any external consumer, create new package or artifact rows, mutate package payloads, rewrite package refs or hashes, widen schema/runtime/source behavior, or enable broad mockup behavior.

This is the smallest safe step after PR `#245`/`#247` because package-review approval proves package acceptability, not downstream transfer semantics. Handoff/export has different risks than package review: target selection, envelope identity, idempotency, dispatch semantics, failure behavior, and downstream compatibility all need explicit governance before any live transfer behavior exists.

## Decision Vocabulary

A future implementation governed by this freeze may admit only these operator handoff/export decisions:

| Decision | Meaning | Allowed next state |
| --- | --- | --- |
| `authorize_prepare` | The approved package-review result may be prepared as an internal handoff/export envelope. | `handoff_export_prepared` |
| `hold` | The package set remains approved but must not be prepared for handoff/export yet. | `handoff_export_held` |
| `decline` | The package set is not to be handed off/exported under the current authority basis. | `handoff_export_declined` |
| `blocked` | The operator cannot authorize preparation because required evidence, package visibility, or downstream policy is insufficient. | `handoff_export_blocked` |

The decision vocabulary is intentionally about internal preparation and authorization only. It is not an APS handoff command, external export command, package rebuild command, rerun command, result-review amendment, approved-plan supersession, or downstream-dispatch command.

## Admitted Future Implementation Scope

An implementation PR governed by this freeze may add only:

- one handoff/export preparation submit endpoint for one current session
- server validation that a package-review submit decision already exists and is exactly `package_review_approved`
- server validation that the approved package-review decision still matches the approved plan, selected terminal pass, result-review record, package-preview hash, reconciliation record, package ids, package kinds, payload refs, and payload hashes
- server validation that exactly one `L3ReconciliationRecord` and exactly three `L3OutputPackage` rows exist for the session
- server validation that package kinds remain exactly `canonical_internal`, `user_facing`, and `review_facing`
- one internal handoff/export envelope summary that references existing package ids, kinds, payload refs, payload hashes, and package-review submit authority
- one durable handoff/export preparation decision object in existing JSON-bearing state, if no schema widening is required
- idempotent retry handling for an identical preparation request
- focused backend tests proving exact write boundaries, immutable package payload refs/hashes, fail-closed stale authority, and no downstream dispatch side effects
- optional `/review/layer3` UI enablement of internal preparation controls only after server authority marks handoff/export preparation available

The admitted envelope is an internal, server-authoritative reference envelope. It must not contain package payload bodies and must not copy package payload files.

## Persistence Boundary

Preferred implementation should persist the bounded handoff/export preparation decision in existing durable JSON fields:

- `L3ReconciliationRecord.summary_json`
- optional `L3Session.summary_json` pointer/index summary

The implementation must not add a schema migration under this freeze. If durable audit/query requirements cannot be met without a new handoff/export table, model, artifact table usage, or migration, stop and create a separate schema/persistence freeze.

The implementation must not mutate:

- package payload files
- `L3OutputPackage.payload_ref`
- `L3OutputPackage.payload_hash`
- `L3OutputPackage.status`
- package payload bodies
- result-review record state
- package-review submit state
- approved plan state
- selected pass output metadata

Creating a physical export file, `AnalysisArtifact` row, downstream APS row, or additional `L3OutputPackage` row is not admitted by default. If implementation proves that a physical file or row is required for the first handoff/export step, that must be frozen separately because the current live workbench has no handoff/export persistence model.

## Explicit Non-Goals

This freeze does not admit:

- APS handoff behavior
- external export or downstream dispatch
- actual transfer to a downstream system
- handoff target-family selection beyond the internal preparation envelope
- package payload rewrite, copy, or regeneration
- package reconstruction or rebuild/amendment
- new `L3OutputPackage` rows
- new `L3ReconciliationRecord` rows
- `AnalysisArtifact` creation
- new handoff/export tables or schema migrations
- runtime snapshot DB writes
- connector-run mutation
- result-review amendment or supersession
- package-review decision amendment or supersession
- approved-plan reopening, correction, or supersession
- rerun, retry, recovery, cancellation, or replay controls beyond deterministic request idempotency
- new `L3AnalysisPlan`, `L3PassRun`, or `AnalysisRun` creation
- analysis execution
- source expansion
- local upload or local-directory ingestion
- editable package variants or package payload editors
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

## Required Preconditions

A future implementation must require all of these before handoff/export preparation:

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
- existing package-review submit decision with `package_review_state == "package_review_approved"`
- matching package-review submit record ref or equivalent stable authority basis
- no existing conflicting handoff/export preparation decision state
- no forbidden APS handoff, external export, package rewrite, source, schema, runtime, rerun, or output-rewrite fields in the request

## Write Boundary

The future implementation may write exactly:

| Target | Allowed amount | Reason |
| --- | --- | --- |
| `L3ReconciliationRecord.summary_json` | one handoff/export preparation object | Existing reconciliation record is the durable package-set anchor |
| `L3Session.summary_json` | optional preparation pointer/index | Allows session summary to report preparation state without creating new rows |

It must not write:

- additional `L3ReconciliationRecord` rows
- additional `L3OutputPackage` rows
- package payload files
- `AnalysisArtifact` rows
- APS handoff rows or artifacts
- external export files
- new analysis plan/pass/run rows
- source-ingestion rows
- runtime snapshot DB rows
- schema/migration files

## UI Boundary

If rendered `/review/layer3` behavior changes, the UI may only expose:

- read-only approved package-review state
- package ids, kinds, payload refs, payload hashes, and package-review submit ref as server-provided evidence
- one handoff/export preparation decision form gated by server state
- allowed decisions from this freeze only
- disabled external handoff/export/dispatch indicators after preparation
- read-only post-preparation summary

The UI must not expose package payload editors, package rebuild controls, external destination selectors, APS handoff controls, export-download controls, dispatch buttons, rerun/recovery controls, source pickers, local upload/directory selectors, raw output editors, qualitative/hybrid/RAG/vector controls, or full mockup-only controls.

## Required Proof

An implementation PR governed by this freeze must prove:

- handoff/export preparation requires current approved plan, preview id/hash, selected terminal pass, result/status authority, approved result-review state, matching package-preview basis, constructed package rows, and package-review submit state `package_review_approved`
- missing package-review submit state fails closed
- non-approved package-review submit states fail closed
- stale package-review submit refs, package ids, package kinds, payload refs, or payload hashes fail closed
- forbidden request fields fail closed
- successful preparation records exactly one handoff/export preparation object in existing JSON-bearing state
- identical idempotent retry does not duplicate or alter preparation state
- conflicting duplicate requests fail closed
- no package payload refs or hashes change
- no package payload files are created, deleted, copied, or rewritten
- no new `L3ReconciliationRecord`, `L3OutputPackage`, `AnalysisArtifact`, APS handoff, external export, runtime DB, schema, source-ingestion, plan, pass, or run rows are created
- external handoff/export/dispatch remains disabled after internal preparation
- existing package construction and package-review submit tests still pass
- both headed and headless Chrome browser proof pass if rendered `/review/layer3` behavior changes

## Stop Conditions

Stop before implementation if any of these becomes necessary:

- actual APS handoff
- external export/download/dispatch behavior
- downstream destination or target-family selection beyond the internal preparation envelope
- package payload rewrite, copy, or package reconstruction
- schema migration
- new handoff/export table/model
- creating more package rows or reconciliation rows
- creating `AnalysisArtifact` rows
- rerun/recovery/cancellation/retry behavior beyond deterministic request idempotency
- result-review or package-review amendment/supersession
- approved-plan supersession
- source expansion or local ingestion
- runtime DB widening
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

## Relationship To Existing Docs

This freeze is downstream of:

- `52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md`
- `50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`
- `51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md`
- `48_L3_WB_PACKAGE_REVIEW_FREEZE.md`
- `49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md`
- `46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`
- `44_L3_WB_RESULT_REVIEW_FREEZE.md`
- `45_L3_WB_RESULT_REVIEW_API_AND_STATE_CONTRACT.md`

It narrows only the next handoff/export preparation boundary. It does not replace the package-review submit contract and does not make APS handoff, external export, or downstream dispatch live.

## Evidence Basis

Repo-local anchors used most directly:

- `R|backend/app/api/layer3.py|Current live Layer 3 workbench endpoints include package preview, package commit, and package-review submit, but no handoff/export endpoint|110-131`
- `R|backend/app/services/layer3_workbench.py|Current package-review submit decisions and states|135-142`
- `R|backend/app/services/layer3_workbench.py|Package-review submit forbids handoff/export fields|399-427`
- `R|backend/app/services/layer3_workbench.py|Package-review submit downstream unavailable is handoff/export|466-466`
- `R|backend/app/services/layer3_workbench.py|Successful package-review submit writes existing reconciliation/session JSON and leaves handoff/export disabled|4558-4649`
- `R|backend/app/services/layer3_workbench.py|Session summary keeps handoff/export disabled after package-review submit state|4671-4765`
- `R|backend/app/models/models.py|Current L3 persistence surfaces include sessions, plans, pass runs, reconciliation records, and output packages but no workbench-specific handoff/export model|742-960`
- `R|backend/tests/test_layer3_api.py|Current tests prove package-review submit records approval while handoff/export remain disabled|1830-1842`
- `R|backend/tests/test_layer3_api.py|Current tests prove forbidden package-review submit handoff/package-payload fields fail closed|2014-2020`
