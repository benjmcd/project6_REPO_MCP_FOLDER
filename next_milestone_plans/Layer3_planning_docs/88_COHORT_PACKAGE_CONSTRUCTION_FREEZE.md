# Layer 3 Selected-Pass Cohort Package Construction Freeze

## Status

Planning-only freeze for the next bounded Layer 3 workbench tranche after PR `#447`.

This document does not make associated-cohort package construction live. It selects only the next eligible implementation boundary after the read-only selected-pass associated-cohort `descriptive_summary` package-review preview/readiness path: a bounded package-construction commit for one exact associated-cohort result review that is already approved and package-preview-ready.

Implementation note: branch `codex/l3-cohort-package-construction-impl-p61` implements this exact boundary as a branch-local candidate. The document remains governance by itself; package-review submit, handoff/export, APS dispatch, external export/download, connector, schema/runtime/source, retry/recovery, pass-entry, broader UI, qualitative/hybrid/RAG/vector, and full mockup behavior remain deferred.

## Authority Boundary

Current live authority is limited to:

- PR `#424`/`#425`: service-owned associated-cohort `descriptive_summary` materialization through `materialize_pass_entry(...)` only when `formation_basis_json["requested_method_name"] == "descriptive_summary"` is an exact string.
- PR `#432`: selected-pass associated-cohort execution-start/result-status over existing backend/API workbench surfaces.
- PR `#438`: selected-pass associated-cohort result review through the existing backend/API result-review endpoint.
- PR `#443`: rendered `/review/layer3` presentation/control for that exact associated-cohort result-review path.
- PR `#447`: read-only associated-cohort package-review preview/readiness inspection through the existing package-preview route and `/review/layer3` UI.
- PR `#449`: progress-refresh classification for PR `#447` as live preview-only behavior while package construction and downstream behavior remain deferred.

Docs `50_L3_WB_PACKAGE_CONSTRUCTION_FREEZE.md` and `51_L3_WB_PACKAGE_CONSTRUCTION_API_AND_STATE_CONTRACT.md` plus their implementation chain remain single-item package-construction authority. They are a pattern source, not direct authority to construct packages for associated-cohort outputs without the cohort-specific gates in this freeze and the companion contract.

## Frozen Decision

The next eligible functional tranche is:

> Add bounded associated-cohort package-construction commit after one exact selected-pass associated-cohort `descriptive_summary` package-review preview has proven readiness over an approved result-review record.

The tranche may create exactly one reconciliation record, exactly three package rows, and exactly three package payload files for the existing `canonical_internal`, `user_facing`, and `review_facing` package kinds. It must not submit package-review decisions, prepare handoff/export state, dispatch downstream, or widen source/schema/runtime behavior.

## In Scope For The Future Implementation

- Preserve the existing `/api/v1/layer3/package/review/commit` route family unless implementation audit proves a separate cohort-specific endpoint is required to avoid request/response ambiguity.
- Admit only the exact selected-pass associated-cohort `descriptive_summary` output path already proven by PR `#432`, PR `#438`, PR `#443`, and PR `#447`.
- Require a recorded approved result-review envelope for the same session, plan, preview hash, pass run, analysis run, method, cohort source gate, source dataset version ids, and reviewed output item trace.
- Require the server-recomputed package-review preview hash from PR `#447` to match the commit request.
- Replace the current `associated_cohort_package_construction_commit_not_admitted` block only inside the frozen cohort package-construction authority chain.
- Reuse the existing package owner-service constants, row models, payload persistence conventions, and idempotency pattern where compatible.
- Create exactly one `L3ReconciliationRecord`, exactly three `L3OutputPackage` rows, and exactly three package payload files.
- Keep package-review submit, handoff/export, APS dispatch, external export/download, and connector behavior disabled.
- Preserve the current single-item package-preview, package-construction, package-review submit, handoff/export, APS dispatch, and download chains unchanged.

## Explicit Non-Goals

- No package-review submit/decision state.
- No handoff/export preparation, APS dispatch, external export/download readiness, delivery, or connector dispatch.
- No package payload editing, package reconstruction, or variant rewrite controls.
- No new `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, or `AnalysisArtifact` rows.
- No source, schema, model, migration, or runtime widening.
- No local upload or directory ingestion.
- No qualitative, hybrid, RAG, vector, retry, recovery, replay, pass-entry, broader UI, broader associated-cohort review, or full mockup activation.
- No use of docs `50`/`51` as direct associated-cohort implementation authority without the cohort-specific gates in this freeze and the companion contract.

## Required Proof Before Implementation Can Be Considered Settled

- Existing single-item package-preview, package-construction, package-review submit, handoff/export, APS dispatch, and download behavior remains unchanged.
- Existing associated-cohort result-review UI and package-review preview behavior from PR `#443` and PR `#447` remains unchanged except for the admitted package-commit readiness/action.
- Missing, malformed, stale, non-approved, duplicate, conflicting, or cross-session result-review state fails closed.
- Missing or mismatched source gate, method, cohort shape, source dataset version ids, preview hash, pass run, analysis run, reviewed output item trace, or package-review preview hash fails closed.
- Requests with package-review-submit, handoff/export, source, schema, runtime, retry/recovery, pass-entry, connector, package-payload override, package-variant edit, or broader UI fields fail closed.
- Successful commit creates exactly one reconciliation row, exactly three package rows, and exactly three package payload files.
- Duplicate identical commit requests are deterministic and do not duplicate rows or payload files.
- Conflicting duplicate commit requests fail closed.
- If rendered UI behavior changes, both headed and headless Chrome proof are required.

## Stop Conditions

Stop and return to planning if implementation requires:

- package-review submit/decision semantics;
- handoff/export behavior;
- APS dispatch, external export/download, or connector behavior;
- schema migration or model changes;
- changing lower-level `descriptive_summary` analysis behavior;
- changing service-owned associated-cohort pass-entry admission from docs `78`/`79`;
- weakening existing single-item package gates;
- creating more than one reconciliation row or more than the three admitted package rows;
- creating `AnalysisArtifact` rows for package construction;
- package payload editing or reconstruction controls;
- rerun/recovery/cancellation/retry behavior beyond deterministic commit idempotency;
- result-review amendment or supersession;
- approved-plan supersession;
- source expansion or local ingestion;
- runtime DB widening;
- qualitative, hybrid, RAG, or vector execution;
- full mockup activation.
