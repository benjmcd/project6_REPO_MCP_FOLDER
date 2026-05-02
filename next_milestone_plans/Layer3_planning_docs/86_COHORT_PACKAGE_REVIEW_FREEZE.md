# Layer 3 Selected-Pass Cohort Package-Review Preview Freeze

## Status

Planning-only freeze for the next bounded Layer 3 workbench tranche after PR #443.

This document does not make package-review preview behavior live. It selects the smallest future implementation boundary that can follow the already-live selected-pass associated-cohort `descriptive_summary` result-review UI path: read-only package-review preview/readiness inspection for one exact associated-cohort result review that is already approved.

## Authority Boundary

Current live authority is limited to:

- PR #424/#425: service-owned associated-cohort `descriptive_summary` materialization through `materialize_pass_entry(...)` only when `formation_basis_json["requested_method_name"] == "descriptive_summary"` is an exact string.
- PR #432: selected-pass associated-cohort execution-start/result-status over existing backend/API workbench surfaces.
- PR #438: selected-pass associated-cohort result review through the existing backend/API result-review endpoint.
- PR #443: rendered `/review/layer3` presentation/control for that exact associated-cohort result-review path, with package/handoff/export controls still unavailable for associated-cohort review state.

Docs `48_L3_WB_PACKAGE_REVIEW_FREEZE.md` and `49_L3_WB_PACKAGE_REVIEW_API_AND_STATE_CONTRACT.md` plus their implementation chain remain single-item package-review authority. They are a pattern source, not direct authority to package associated-cohort outputs.

## Frozen Decision

The next eligible functional tranche is:

> Add read-only associated-cohort package-review preview/readiness inspection after one exact selected-pass associated-cohort `descriptive_summary` result review has been recorded and approved.

The tranche may only determine whether the reviewed associated-cohort output is package-preview-ready. It must not construct packages, submit package-review decisions, prepare handoff/export state, dispatch downstream, or widen source/schema/runtime behavior.

## In Scope For The Future Implementation

- Preserve the existing `/api/v1/layer3/package/review/preview` endpoint as the default route family unless implementation audit proves a separate endpoint is required to avoid contract ambiguity.
- Admit only the exact selected-pass associated-cohort `descriptive_summary` output path already proven by PR #432, PR #438, and PR #443.
- Require a recorded approved result-review envelope for the same session, plan, preview hash, pass run, analysis run, method, cohort source gate, source dataset version ids, and reviewed output item trace.
- Return read-only package-review preview/readiness state that the UI can inspect.
- Keep associated-cohort package construction, package-review submit, handoff/export, APS dispatch, external export/download, and connector behavior disabled.
- Preserve the current single-item package-preview, package-construction, package-review submit, handoff/export, APS dispatch, and download chains unchanged.

## Explicit Non-Goals

- No `L3OutputPackage` rows.
- No `L3ReconciliationRecord` rows.
- No package payload files.
- No package construction or package commit.
- No package-review submit/decision state.
- No handoff/export preparation, APS dispatch, external export/download readiness, delivery, or connector dispatch.
- No source, schema, model, migration, or runtime widening.
- No local upload or directory ingestion.
- No qualitative, hybrid, RAG, vector, retry, recovery, replay, pass-entry, broader UI, broader associated-cohort review, or full mockup activation.
- No use of docs 48/49 as direct associated-cohort authority without the cohort-specific gates in this freeze and the companion contract.

## Required Proof Before Implementation Can Be Considered Settled

- Existing single-item package-review preview behavior remains unchanged.
- Existing associated-cohort result-review UI behavior from PR #443 remains unchanged.
- Missing, malformed, stale, non-approved, duplicate, conflicting, or cross-session result-review state fails closed.
- Missing or mismatched source gate, method, cohort shape, source dataset version ids, preview hash, pass run, analysis run, or reviewed output item trace fails closed.
- Requests with package-construction, package-review-submit, handoff/export, source, schema, runtime, retry/recovery, pass-entry, connector, or broader UI fields fail closed.
- The preview path creates no rows and writes no files.
- If rendered UI behavior changes, both headed and headless Chrome proof are required.

## Stop Conditions

Stop and return to planning if implementation requires:

- changing package construction, package-review submit, handoff/export, APS dispatch, external export/download, connector, source/schema/runtime, migration/model, retry/recovery, or pass-entry behavior;
- weakening existing single-item package gates;
- treating docs 48/49 as direct associated-cohort implementation authority;
- enabling package/handoff/export controls before the server proves cohort package-preview readiness.
