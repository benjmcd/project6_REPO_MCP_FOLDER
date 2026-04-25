# Layer 3 Workbench Result Review Freeze

Status: governing planning-only freeze for the bounded result-review tranche after merged PR `#222`.

Post-freeze status note: PR `#227` later implemented this backend result-review boundary on current `main`; PR `#232` later implemented the separately frozen bounded result-review UI presentation/control surface. This document remains the backend result-review planning freeze; it does not make package review, handoff/export, rerun/recovery, source/schema/runtime widening, or full mockup behavior live.

This document freezes the narrowest eligible boundary after selected-pass result/status inspection: operator review of one terminal selected pass result that has already passed the PR `#222` read-only result/status authority checks. It does not implement result review by itself and does not admit package review, handoff, rerun/recovery, source expansion, schema/runtime widening, UI/full mockup activation, qualitative/hybrid/RAG/vector execution, local upload/directory ingestion, or broad result taxonomy finalization.

## Current Live Boundary

Current `project6-origin/main` through PR `#222` ships:

- first-slice `/review/layer3` shell/API from PR `#184`
- read-only plan preview from PR `#194`
- approval-only `L3AnalysisPlan` persistence from PR `#199`
- pre-approval plan-revision control from PR `#205` hardened by PR `#207`
- read-only execution-readiness proof from PR `#213`
- execution-selection/pass-run shell creation from PR `#216`
- bounded selected-pass analysis-execution start from PR `#218`
- read-only selected-pass result/status inspection from PR `#222`

The live PR `#222` boundary can report whether one selected terminal pass has status/output metadata authority. It still keeps `result_review_enabled`, `package_review_enabled`, and `handoff_enabled` false. That means result review must be frozen as a separate write boundary before implementation.

## Mockup Implication Boundary

The mockup/spec context expects later Layer 3 output to become inspectable, traceable, and reviewable before handoff. The same mockup spec also records unresolved details for:

- exact output taxonomy beyond visible "insights/facts/data"
- output-to-ingress trace UI and backend reference structure
- package review behavior for `canonical_internal`, `user_facing`, `review_facing`, and handoff variants
- downstream handoff triggers

This freeze therefore admits only the first review unit: review of one already-produced selected-pass result. It does not treat the mockup visuals as permission to activate package review, handoff, or a complete output taxonomy.

## Slice Decision

The next adequate Layer 3 workbench tranche is:

> Freeze a bounded selected-pass result-review decision after PR `#222`: one terminal selected pass whose result/status is available may receive one operator review decision, recorded against existing Layer 3 workbench authority, without creating packages, handoff artifacts, new execution runs, source expansion, schema/runtime widening, UI/full mockup activation, qualitative/hybrid/RAG/vector behavior, or downstream APS activation.

This is the smallest useful post-status step because it lets the operator decide whether a specific generated result is acceptable for later packaging work while still preventing package construction and handoff.

## Admitted Future Implementation Scope

An implementation PR governed by this freeze may add only:

- one result-review endpoint under the existing Layer 3 API family
- validation that the session has exactly one current approved `L3AnalysisPlan`
- validation that the approved plan and execution-selection preview id/hash still match the request
- validation that the requested `pass_run_id` belongs to the approved plan and current session
- validation that the pass is selected, terminal, and already eligible through PR `#222` result/status authority
- validation that readable selected-pass output metadata exists for approval; failed or missing-output passes may be blocked or reviewed only with an explicit non-approval decision
- one bounded operator review decision for the selected pass
- bounded operator notes/caveats tied to that review decision
- bounded trace summary back to existing selected-pass output metadata, pass-run state, analysis run id, and available material/unit/set references
- durable review metadata only in an already-owned Layer 3 workbench JSON summary field, if implementation proves no schema migration or unrelated table write is required
- focused backend tests proving authority checks, idempotency, duplicate behavior, no package/handoff side effects, and no new execution artifacts
- headed and headless browser proof only if rendered `/review/layer3` behavior changes

If implementation proves a new table, migration, package artifact, review artifact manifest, or cross-service audit table is required, that is a separate freeze and must not be smuggled into this tranche.

## Explicit Non-Goals

This freeze does not admit:

- package review UI
- package artifact creation
- APS handoff UI or handoff artifacts
- export behavior
- new `AnalysisRun` creation
- new `L3AnalysisPlan` creation
- new `L3PassRun` creation
- rerun, retry, recovery, cancellation, or replay
- editing raw output artifacts
- rewriting selected-pass output metadata files
- result aggregation across multiple pass runs
- batch or multi-pass review
- approved-plan reopening or supersession
- new source ingestion or source-breadth expansion
- local upload or local-directory ingestion
- runtime snapshot DB writes
- schema migrations
- result/package/handoff artifact manifests
- qualitative, hybrid, RAG, or vector execution
- background worker queues, leases, cancellation, or retry orchestration
- full mockup activation

## Required Decisions

| Gate | Decision | Reasoning |
| --- | --- | --- |
| Review unit | review one selected terminal `L3PassRun` per request | This preserves the PR `#216`/`#218`/`#222` one-pass chain and avoids result aggregation semantics |
| Authority source | durable session, approved plan, preview hash, execution-selection summary, selected pass, execution-start summary, result/status response, and existing output metadata | Browser state and request payloads cannot authorize post-execution review |
| Endpoint posture | result review, not package review | The operator decision is useful before packaging, but package variants and handoff triggers remain unresolved |
| Decision values | `approved`, `changes_requested`, `rejected`, or `blocked` | These values express review posture without implying package construction or APS handoff |
| Approval meaning | `approved` means acceptable for a later separately frozen package step | It does not create a package, export, handoff, or downstream artifact |
| Output taxonomy | use a minimal review projection: `datum`, `fact`, `finding`, `insight`, `caveat`, `contradiction`, `unsupported_claim`, and `generated_narrative` where present in existing metadata | This reflects the mockup/spec recommended vocabulary without requiring a complete taxonomy engine in this slice |
| Traceability | every reviewed output item must retain available references to selected pass, output metadata, analysis run, source/material/unit/group/set ids when present; missing required trace blocks approval | This keeps result review auditable and prevents untraceable output from being promoted |
| Write boundary | write only bounded review metadata in an existing Layer 3 workbench-owned JSON envelope unless a later freeze admits a schema/table change | This gives a durable operator decision without widening schema or creating package/handoff state |
| UI posture | if UI changes, show result review controls only after result/status is available and keep package/handoff controls disabled | The visual workflow can advance one step without activating later mockup states |
| Downstream posture | package review and handoff remain unavailable | Result approval does not settle package variants, audience surfaces, or APS handoff triggers |

## Required Proof

An implementation PR governed by this freeze must prove:

- result review requires prior PR `#222` result/status availability for the same session, plan, preview hash, and selected pass
- stale preview id/hash fails closed
- non-selected, non-terminal, foreign-session, or foreign-plan pass runs fail closed
- unreadable or missing output metadata cannot be approved
- failed terminal passes cannot be approved unless a later explicit failure-review policy admits it
- duplicate review submissions are idempotent or fail closed without creating duplicate state
- conflicting review submissions fail closed
- forbidden package/handoff/rerun/source/schema/runtime fields fail closed
- the endpoint creates no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3OutputPackage`, `L3ReconciliationRecord`, package-review, handoff, runtime snapshot DB, or schema state
- result review state remains limited to the selected pass and does not alter the approved plan
- package review and handoff remain disabled in response/session summary posture
- all relevant Layer 3 focused backend tests pass
- headed and headless browser proof is run if rendered `/review/layer3` behavior changes

## Stop Conditions

Stop and write a later freeze before implementing any of the following:

- package construction or package review
- handoff/export behavior
- final package variant tabs or package audience surfaces
- new schema/table/migration requirements
- normalized result rows outside the existing Layer 3 workbench JSON boundary
- result aggregation across multiple pass runs
- approved-plan supersession or correction
- rerun, retry, cancellation, or recovery workflow
- qualitative/hybrid/RAG/vector execution
- source-breadth expansion
- local upload or local-directory ingestion
- broad UI/full mockup activation

## Relationship To Existing Docs

This freeze is governed by and must remain consistent with:

- `42_L3_WB_RESULT_STATUS_FREEZE.md`
- `43_L3_WB_RESULT_STATUS_API_AND_STATE_CONTRACT.md`
- `40_L3_WB_ANALYSIS_EXECUTION_START_FREEZE.md`
- `41_L3_WB_ANALYSIS_EXECUTION_START_API_AND_STATE_CONTRACT.md`
- `38_L3_WB_EXECUTION_SELECTION_FREEZE.md`
- `39_L3_WB_EXECUTION_SELECTION_API_AND_STATE_CONTRACT.md`
- `next_milestone_plans/layer3_workbench_proof_manifest.json`
- `next_milestone_plans/layer3_progress_manifest.json`
- `next_milestone_plans/layer3_progress_board.md`
- `docs/nrc_adams/nrc_aps_status_handoff.md`

It starts from PR `#222` selected-pass result/status authority and freezes only the next bounded result-review decision. It does not replace the result/status packet and does not make result review live by itself.
