# Layer 3 Approved Plan Correction Freeze

Status: planning/control freeze only for `approved_plan_correction_lifecycle`. No runtime behavior is admitted by this document.

This artifact freezes the next approved-plan lifecycle question after the bounded PR `#599` pre-approval revision recovery runtime. Current main admits `plan_revision_recovery_preview_refresh_entry` only before approval. Once an `L3AnalysisPlan` is approved, cancellation, reopening, replacement, and supersession remain unavailable unless a later implementation-entry freeze selects exactly one bounded correction mode and proves the server authority for it.

## Authority Snapshot

- authority_worktree: `C:\Users\benny\Downloads\worktree_for_audits`
- baseline_ref: `project6-origin/main`
- baseline_commit: `55d90f869d1f1e49127bc1dd2e1269d056f702aa`
- predecessor recovery docs: `132_PLAN_REVISION_RECOVERY_FREEZE.md`, `133_PLAN_REVISION_RECOVERY_CONTRACT.md`, `134_PLAN_REVISION_RECOVERY_ENTRY_FREEZE.md`
- current pre-approval recovery runtime: `plan_revision_recovery_preview_refresh_entry`
- current approved-plan correction readiness label: `approved_plan_correction`
- live forbidden field: `approved_plan_supersession`
- current plan-flow request contract owner: `backend/app/services/layer3_plan_flow_contract.py`
- current readiness contract owner: `backend/app/services/layer3_readiness_contract.py`
- selected future lifecycle mode: `approved_plan_correction_lifecycle`
- selected current posture: `approved_plan_correction_not_admitted`
- evidence boundary: live source/tests and `tools/l3-progress-check.py` outrank this document

## Decision

The next approved-plan question is narrowed to exactly:

- selected_future_lifecycle_mode: `approved_plan_correction_lifecycle`
- selected_current_posture: `approved_plan_correction_not_admitted`
- required_future_selection: one of `approved_plan_cancel_without_replacement` or `approved_plan_supersession_preview_only`, not both in one implementation slice

This is not live runtime. This document does not choose an implementation route, DTO, state write, model, migration, UI behavior, package behavior, execution behavior, or downstream dispatch behavior.

The current invariant is strict: approved-plan cancellation, reopening, replacement, deletion, and supersession remain unavailable.

## Why This Outranks Broad Work

Approved plans sit upstream of execution selection, execution start, result review, package construction, handoff/export, package mutation, connector dispatch, source expansion, qualitative/hybrid/RAG behavior, and full mockup activation. Freezing approved-plan correction first prevents future slices from using broad package mutation, recovery, UI state, or downstream dispatch as an implicit way to reopen or replace an approved plan.

## Admitted Planning Scope

This freeze may specify:

- that approved-plan correction remains unavailable on current main;
- that a later implementation-entry freeze must select exactly one correction mode;
- that any future correction mode must prove current session, approved plan, preview id/hash, plan hash, and absence of downstream state before writing anything;
- that browser/local storage may request or display correction only after server authority exists;
- that pass runs, analysis runs, result review, package state, handoff/export state, connector state, source widening, qualitative/hybrid/RAG state, and package mutation block the initial correction lane by default;
- that schema widening is not allowed unless a separate implementation-entry freeze proves existing JSON-bearing state is inadequate.

## Required Future Contract

A later implementation-entry freeze must define:

- exact route or existing-route extension, if any;
- owner service;
- strict request DTO and response DTO;
- selected correction mode;
- source approved-plan id, preview id/hash, plan hash, and current state proof;
- idempotency key and authority hash basis;
- stale approved-plan, stale preview, stale package, pass-run, analysis-run, result-review, package, handoff/export, connector, and source-state behavior;
- response-safe next state and next allowed actions;
- rollback path that preserves `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, package, handoff/export, connector, source, provider, and artifact state unless that exact state is selected and proven by the future freeze.

## Positive Invariants

The future correction lane is acceptable only if:

- `approved_plan_correction_lifecycle` is the only selected lifecycle family;
- the first implementation-entry freeze selects one exact mode, not a combined cancellation-and-supersession feature;
- current main continues to treat approved-plan correction as unavailable until the later implementation-entry freeze;
- the existing `L3AnalysisPlan` remains server authority and is not silently deleted or mutated by planning docs;
- any future correction requires current server revalidation of the approved plan and its preview/hash basis;
- any future correction fails closed once execution, result, package, handoff/export, connector, source, qualitative/hybrid/RAG, or package-mutation state exists unless separately governed;
- browser/local storage remains cache-only and non-authoritative;
- all broad deferred capabilities remain blocked.

## Negative Invariants

This freeze must not accidentally admit:

- runtime behavior;
- route/API changes;
- approved-plan reopening, cancellation, deletion, replacement, or supersession;
- `L3AnalysisPlan` creation, update, or deletion;
- `L3PassRun` creation, update, cancellation, or deletion;
- `AnalysisRun` creation, update, cancellation, or deletion;
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

- correction is unavailable without an approved plan;
- stale approved-plan id/hash or preview id/hash fails closed;
- correction fails closed after pass-run creation;
- correction fails closed after analysis-run creation;
- correction fails closed after result, package, handoff/export, connector, or source-state progression unless separately selected;
- duplicate `client_request_id` behavior is deterministic;
- forbidden execution/downstream/source/package/connector/provider/mockup fields fail closed;
- no `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, package, handoff/export, connector, source, provider, or artifact state is created by any planning-only slice;
- browser state cannot correct an approved plan without server authority.

## Stop Conditions

Stop before implementation if the intended change requires:

- combining cancellation and supersession in one broad slice;
- implicit approved-plan mutation or deletion;
- automatic plan generation;
- pass-run or analysis-run mutation;
- artifact writes;
- package/handoff/export behavior;
- connector/destination behavior;
- source widening;
- broad qualitative/hybrid/RAG behavior;
- full mockup activation;
- authentication/security work while that lane remains deferred.

## Acceptance Criteria

This planning/control slice is accepted when:

- this file exists and contains `selected_future_lifecycle_mode: approved_plan_correction_lifecycle`;
- this file contains `selected_current_posture: approved_plan_correction_not_admitted`;
- `105_deferred-gates.md`, `117_L3_SYNTHESIS_AUTHORITY_BOUNDARY.md`, `118_L3_GOAL_AUDIT.md`, and `120_L3_CLOSEOUT.md` classify approved-plan correction as planning/control only;
- `layer3_progress_manifest.json`, `layer3_progress_board.md`, and `layer3_workbench_proof_manifest.json` record this slice as planning-only;
- `tools/l3-progress-check.py` fails closed if approved-plan correction is marked live or if broad execution/package/connector/source/RAG/mockup/auth behavior is admitted;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` reports no whitespace errors.
