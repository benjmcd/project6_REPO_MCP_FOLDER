# Layer 3 Selected-Pass Cohort Package Review Submit Freeze

## Status

Planning-only freeze for the next bounded Layer 3 workbench tranche after PR `#451`.

This document does not make associated-cohort package-review submit live. It selects only the next eligible governance boundary after merged selected-pass associated-cohort `descriptive_summary` package construction: a bounded package-review submit/decision step for one exact associated-cohort package set that was constructed by PR `#451`.

## Authority Boundary

Current live authority is limited to:

- PR `#424`/`#425`: service-owned associated-cohort `descriptive_summary` materialization through `materialize_pass_entry(...)` only when `formation_basis_json["requested_method_name"] == "descriptive_summary"` is an exact string.
- PR `#432`: selected-pass associated-cohort execution-start/result-status over existing backend/API workbench surfaces.
- PR `#438`: selected-pass associated-cohort result review through the existing backend/API result-review endpoint.
- PR `#443`: rendered `/review/layer3` presentation/control for that exact associated-cohort result-review path.
- PR `#447`: read-only associated-cohort package-review preview/readiness inspection through the existing package-preview route and `/review/layer3` UI.
- PR `#451`: bounded associated-cohort package-construction commit over docs `88`/`89`, creating exactly one reconciliation row, three package rows, and three payload files while keeping submit/downstream behavior disabled.

Docs `52_L3_WB_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `53_L3_WB_PACKAGE_REVIEW_SUBMIT_API_AND_STATE_CONTRACT.md` plus their implementation chain remain single-item package-review submit authority. They are a pattern source, not direct authority to submit package-review decisions for associated-cohort packages without the cohort-specific gates in this freeze and the companion contract.

## Frozen Decision

The next eligible planning tranche is:

> Freeze a bounded associated-cohort package-review submit/decision step after one exact selected-pass associated-cohort `descriptive_summary` package set has been constructed by PR `#451`.

The future tranche may record one operator package-review decision over the constructed associated-cohort package set. It must not rewrite packages, create packages, prepare handoff/export state, dispatch downstream, or widen source/schema/runtime behavior.

## In Scope For The Future Implementation

- Preserve the existing `/api/v1/layer3/package/review/submit` route family unless implementation audit proves a separate cohort-specific endpoint is required to avoid request/response ambiguity.
- Admit only the exact selected-pass associated-cohort `descriptive_summary` package set already proven by PR `#432`, PR `#438`, PR `#443`, PR `#447`, and PR `#451`.
- Require the constructed package set to carry cohort package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE`.
- Require exactly one reconciliation row and exactly three package rows for `canonical_internal`, `user_facing`, and `review_facing`.
- Require stored package ids, package kinds, payload refs, and payload hashes to match the request.
- Record exactly one package-review decision object in existing JSON-bearing state.
- Keep handoff/export, APS dispatch, external export/download, connector behavior, schema/runtime/source widening, retry/recovery, pass-entry changes, broader UI, qualitative/hybrid/RAG/vector, and full mockup behavior disabled.
- Preserve the existing single-item package-review submit, handoff/export, APS dispatch, and download chains unchanged.

## Decision Vocabulary

A future implementation governed by this freeze may admit only these operator decisions:

| Decision | Meaning | Allowed next state |
| --- | --- | --- |
| `approved` | The constructed associated-cohort package set is accepted for later separately frozen handoff/export consideration. | `package_review_approved` |
| `changes_requested` | The package set is not accepted as-is and requires a separately frozen rebuild/amendment path before any downstream action. | `package_review_changes_requested` |
| `rejected` | The package set is not accepted and must not proceed downstream. | `package_review_rejected` |
| `blocked` | The operator cannot decide because required evidence, package visibility, or authority is insufficient. | `package_review_blocked` |

The decision vocabulary is review disposition only. It is not a rebuild command, handoff command, export command, rerun command, result-review amendment, or approved-plan supersession.

## Explicit Non-Goals

- No handoff/export preparation.
- No APS dispatch, external export/download readiness, delivery, or connector dispatch.
- No package payload editing, package reconstruction, or variant rewrite controls.
- No new `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3ReconciliationRecord`, or `L3OutputPackage` rows.
- No source, schema, model, migration, or runtime widening.
- No local upload or directory ingestion.
- No qualitative, hybrid, RAG, vector, retry, recovery, replay, pass-entry, broader UI, broader associated-cohort review, or full mockup activation.
- No use of docs `52`/`53` as direct associated-cohort submit authority without the cohort-specific gates in this freeze and the companion contract.

## Required Proof Before Implementation Can Be Considered Settled

- Existing single-item package-review submit, handoff/export, APS dispatch, and download behavior remains unchanged.
- Existing associated-cohort package-construction behavior from PR `#451` remains unchanged except for the admitted package-review submit readiness/action.
- Missing, malformed, stale, partial, non-cohort, duplicate, conflicting, or cross-session package state fails closed.
- Missing or mismatched reconciliation id, package ids, package kinds, payload refs, payload hashes, result-review record ref, package-review preview hash, pass run, analysis run, source gate, method, cohort shape, source dataset version ids, or package-construction authority fails closed.
- Requests with handoff/export, APS dispatch, external export/download, connector, source, schema, runtime, retry/recovery, pass-entry, package-payload override, package-variant edit, result-review amendment, or broader UI fields fail closed.
- Successful submit records exactly one package-review decision object and no new package/reconciliation/artifact rows.
- Duplicate identical submit requests are deterministic and do not duplicate state.
- Conflicting duplicate submit requests fail closed.
- No package payload refs, payload hashes, or payload files change.
- If rendered UI behavior changes, both headed and headless Chrome proof are required.

## Stop Conditions

Stop and return to planning if implementation requires:

- handoff/export behavior;
- APS dispatch, external export/download, or connector behavior;
- package payload rewrite or package reconstruction;
- schema migration or model changes;
- changing lower-level `descriptive_summary` analysis behavior;
- changing service-owned associated-cohort pass-entry admission from docs `78`/`79`;
- weakening existing single-item package gates;
- creating package rows, reconciliation rows, artifacts, plans, passes, or runs;
- updating `L3OutputPackage.status`;
- rerun/recovery/cancellation/retry behavior beyond deterministic submit idempotency;
- result-review amendment or supersession;
- approved-plan supersession;
- source expansion or local ingestion;
- runtime DB widening;
- qualitative, hybrid, RAG, or vector execution;
- full mockup activation.
