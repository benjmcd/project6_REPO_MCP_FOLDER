# Layer 3 Workbench Handoff Export UI Freeze

Status: planning-only UI freeze for the bounded `/review/layer3` handoff/export preparation presentation slice after merged PR `#251` and PR `#252`.

This document freezes only the future rendered presentation and operator-control boundary for the already-live backend/API handoff/export `prepare_only` endpoint. It does not implement UI behavior by itself, does not change backend API behavior, and does not admit APS handoff, external export, downstream dispatch, physical export artifact creation, `AnalysisArtifact` creation, package payload mutation, package reconstruction, schema/runtime/source widening, execution selection/start UI expansion, qualitative/hybrid/RAG/vector execution, or full mockup activation.

## Current Live Boundary

Current `project6-origin/main` through PR `#254` includes:

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
- bounded backend package-review submit from PR `#243`
- bounded rendered package-review controls from PR `#245`
- PR `#247` fallback hardening for package-review submit readiness after package construction commit
- planning-only docs `54`/`55` handoff/export preparation governance from PR `#250`
- bounded backend/API `POST /api/v1/layer3/handoff/export/prepare` from PR `#251`
- PR `#252` downstream blocker vocabulary and active package-substate session-summary hardening
- PR `#253`/`#254` docs/progress and manifest seed-checkout syncs

The live backend can record one `prepare_only` handoff/export preparation decision over an approved package-review submit state. The rendered `/review/layer3` UI does not yet expose handoff/export preparation controls. APS handoff, external export, downstream dispatch, physical artifact creation, and package mutation/reconstruction remain unavailable.

## Slice Decision

The next admitted UI planning boundary is:

> Present the server-authoritative handoff/export preparation readiness and recorded preparation state on `/review/layer3`, and allow one bounded operator preparation decision only when the session summary proves package-review submit state `package_review_approved` and the backend exposes `handoff_export_prepare.available == true`. Do not add APS handoff, external export/download, downstream destination selection, package editing/rebuild, source/runtime/schema widening, execution selection/start expansion, or full mockup behavior.

This is the smallest safe UI step after the backend prepare-only endpoint because the UI can reuse existing session-summary state and the existing `POST /api/v1/layer3/handoff/export/prepare` contract without inventing browser-side authority or new backend semantics.

## Admitted UI Scope

A future implementation PR governed by this freeze may change only:

- `backend/app/review_ui/static/layer3.html`
- `backend/app/review_ui/static/layer3.css`
- `backend/app/review_ui/static/layer3.js`
- narrowly related page/static tests or browser tests that prove the changed `/review/layer3` behavior

The implementation may:

- read `GET /api/v1/layer3/session/{session_id}` after a session exists
- render the existing package-review submit state and handoff/export prepare summary from server state
- call `POST /api/v1/layer3/handoff/export/prepare` only with fields admitted by docs `54`/`55`
- show approved package-review state, package-review submit record ref, reconciliation record id, output package ids, package kinds, payload refs, payload hashes, package-review preview hash, and result-review record ref as server-provided evidence
- provide one operator decision control for `authorize_prepare`, `hold`, `decline`, or `blocked`
- require decision notes for `hold`, `decline`, and `blocked`
- show `handoff_target == internal_export_envelope` and `export_mode == prepare_only`
- render read-only prepared/held/declined/blocked state returned by the server
- render the internal envelope summary after `authorize_prepare` as reference-only metadata
- keep APS handoff, external export, downstream dispatch, download, destination selection, and connector-run indicators disabled or absent

The UI must rely on server summary and endpoint responses as authority. Browser state may cache display values and generate a `client_request_id`, but browser state must not authorize preparation, mutate package content, rebuild packages, infer missing authority fields, dispatch, export, download, or create artifacts.

## Explicit Non-Goals

This freeze does not admit:

- APS handoff behavior or controls
- external export/download behavior or controls
- downstream destination or target-family selectors
- physical export artifact creation
- `AnalysisArtifact` usage
- package payload editing, copying, rewriting, regeneration, or reconstruction
- package rebuild/amendment controls
- editable package variant tabs
- additional package or reconciliation rows
- result-review amendment or supersession
- package-review amendment or supersession
- execution selection/start UI expansion
- rerun, retry, recovery, cancel, or replay controls beyond backend idempotency handling
- source expansion
- local upload or local-directory ingestion
- schema migrations or runtime DB widening
- connector-run mutation or dispatch
- qualitative, hybrid, RAG, or vector execution UI
- full mockup activation

If implementation proves the UI needs new backend fields, a new endpoint, schema widening, physical artifacts, package mutation, or downstream dispatch to be usable, stop and freeze that backend/persistence/downstream slice separately.

## Presentation Requirements

The future panel must make these distinctions visible without implying downstream activation:

| Area | Required presentation | Must not imply |
| --- | --- | --- |
| Package-review submit | Show current server-authoritative submit state and submit record ref | Package approval dispatched anything downstream |
| Handoff/export readiness | Show unavailable, ready, prepared, held, declined, or blocked state from server summary | Browser can infer missing authority |
| Preparation decision | Enable exactly one decision form only when server state marks preparation available | UI can prepare without package_review_approved authority |
| Internal envelope | Show reference-only ids/kinds/refs/hashes and disabled downstream flags | Payload bodies, downloads, APS ids, connector runs, or external artifacts exist |
| Downstream posture | Show APS handoff, external export, and downstream dispatch as disabled/unavailable | Any external transfer is live |

When a handoff/export preparation decision is already recorded, the UI must render it as existing server state and avoid offering a conflicting second decision unless a later freeze admits amendment or supersession.

## State Gating

The UI may enable the handoff/export preparation submit control only when all of the following are true:

1. a session id exists
2. the session summary identifies an approved plan and approved preview id/hash
3. one selected terminal pass and result/status authority are represented by server state
4. approved selected-pass result-review authority is represented by server state
5. package-review preview, package-construction commit, and package-review submit state are represented by server state
6. package-review submit state is exactly `package_review_approved`
7. the handoff/export prepare summary reports `available == true`
8. package ids, kinds, payload refs, payload hashes, reconciliation id, package-review preview hash, result-review record ref, and submit record ref are present from server state
9. no conflicting handoff/export preparation decision is already recorded
10. APS handoff, external export, and downstream dispatch remain disabled

If any of these are absent, the UI must show a blocked or unavailable state and avoid submitting handoff/export preparation requests.

## Backend Boundary

This UI freeze expects the implementation to use existing backend routes:

- `GET /api/v1/layer3/session/{session_id}`
- `POST /api/v1/layer3/handoff/export/prepare`

If these routes do not provide enough data for a safe UI implementation, the implementation must stop and add a separate API/state freeze before changing backend behavior. This document does not authorize new API fields, tables, migrations, artifact rows, package rows, reconciliation rows, package payload writes, source-ingestion rows, runtime DB writes, APS handoff, external export, or dispatch behavior by default.

## Required Proof

An implementation PR governed by this freeze must prove:

- no backend behavior changes unless a separate freeze explicitly admits them
- no handoff/export controls render before a session exists
- no handoff/export controls render before approved package-review submit authority exists
- unavailable and blocked server states render without allowing submission
- the UI uses only server-provided package ids, kinds, refs, hashes, result-review record ref, reconciliation id, preview hash, and submit ref
- successful `authorize_prepare`, `hold`, `decline`, and `blocked` responses render as server truth
- decision notes are required in the UI for `hold`, `decline`, and `blocked`
- request payloads contain only docs `54`/`55` admitted fields and never contain forbidden handoff/export, package mutation, rerun, source, schema, runtime, artifact, or dispatch fields
- the reference envelope display contains no package payload bodies, download URLs, downstream APS ids, connector-run ids, editable payloads, or rewritten content
- APS handoff, external export, and downstream dispatch indicators remain disabled after every decision
- already-recorded preparation state renders without offering conflicting amendment controls
- relevant backend Layer 3 tests still pass
- page/static tests cover disabled, ready, prepared, held, declined, and blocked UI states
- both headed and headless Chrome browser proof pass because rendered `/review/layer3` behavior changes

## Stop Conditions

Stop before implementation if any of these becomes necessary:

- new backend endpoint or schema field beyond a separately frozen API/state contract
- APS handoff, external export/download, or downstream dispatch
- downstream destination or target-family selection
- physical export artifact persistence
- `AnalysisArtifact` creation
- package payload rewrite, copy, editing, or reconstruction
- package rebuild/amendment
- additional package or reconciliation rows
- execution selection/start UI expansion
- rerun/recovery/cancellation/retry controls beyond deterministic request idempotency
- result-review or package-review amendment/supersession
- source expansion or local ingestion
- runtime DB or schema widening
- qualitative, hybrid, RAG, or vector execution
- full mockup activation

## Relationship To Existing Docs

This freeze is downstream of:

- `54_L3_WB_HANDOFF_EXPORT_FREEZE.md`
- `55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md`
- `52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md`
- `53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md`
- `50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md`
- `51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md`
- `48_L3_WB_PACKAGE_REVIEW_FREEZE.md`
- `49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md`
- `46_L3_WB_RESULT_REVIEW_UI_FREEZE.md`
- `47_L3_WB_RESULT_REVIEW_UI_STATE_CONTRACT.md`

It freezes only a bounded UI presentation and handoff/export preparation control surface for current backend prepare-only state. It does not replace the backend handoff/export preparation docs and does not make UI behavior live by itself.
