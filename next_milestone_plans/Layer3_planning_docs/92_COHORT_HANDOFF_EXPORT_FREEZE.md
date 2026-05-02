# Layer 3 Selected-Pass Cohort Handoff Export Freeze

## Status

Planning-only freeze for the next bounded Layer 3 workbench tranche after PR `#456`.

This document does not make associated-cohort handoff/export live. It selects only the next eligible governance boundary after merged selected-pass associated-cohort `descriptive_summary` package-review submit: a bounded internal handoff/export preparation decision for one exact approved associated-cohort package set.

## Authority Boundary

Current live authority is limited to:

- PR `#424`/`#425`: service-owned associated-cohort `descriptive_summary` materialization through `materialize_pass_entry(...)` only when `formation_basis_json["requested_method_name"] == "descriptive_summary"` is an exact string.
- PR `#432`: selected-pass associated-cohort execution-start/result-status over existing backend/API workbench surfaces.
- PR `#438`: selected-pass associated-cohort result review through the existing backend/API result-review endpoint.
- PR `#443`: rendered `/review/layer3` presentation/control for that exact associated-cohort result-review path.
- PR `#447`: read-only associated-cohort package-review preview/readiness inspection through the existing package-preview route and `/review/layer3` UI.
- PR `#451`: bounded associated-cohort package-construction commit over docs `88`/`89`, creating exactly one reconciliation row, three package rows, and three payload files.
- PR `#456`: bounded associated-cohort package-review submit over docs `90`/`91`, recording exactly one package-review decision object in existing JSON-bearing state while keeping handoff/export and all downstream behavior unavailable.

Docs `54_L3_WB_HANDOFF_EXPORT_FREEZE.md` and `55_L3_WB_HANDOFF_EXPORT_API_AND_STATE_CONTRACT.md` plus their implementation chain remain single-item handoff/export authority. They are a pattern source, not direct authority to prepare handoff/export for associated-cohort packages without the cohort-specific gates in this freeze and the companion contract.

## Frozen Decision

The next eligible planning tranche is:

> Freeze a bounded associated-cohort handoff/export preparation decision after one exact selected-pass associated-cohort `descriptive_summary` package set has an approved package-review submit decision from PR `#456`.

The future tranche may record one internal handoff/export preparation decision over the approved associated-cohort package set. It must not dispatch to APS, prepare external export/download, create physical artifacts, create new rows, rewrite packages, copy payloads, or widen source/schema/runtime behavior.

## In Scope For The Future Implementation

- Preserve the existing `/api/v1/layer3/handoff/export/prepare` route family unless implementation audit proves a separate cohort-specific endpoint is required to avoid request/response ambiguity.
- Admit only the exact selected-pass associated-cohort `descriptive_summary` package set already proven by PR `#432`, PR `#438`, PR `#443`, PR `#447`, PR `#451`, and PR `#456`.
- Require the approved package-review submit state to carry package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE` and package-review submit schema `layer3.cohort_package_review_submit.v1`.
- Require exactly one reconciliation row and exactly three package rows for `canonical_internal`, `user_facing`, and `review_facing`.
- Require stored package ids, package kinds, payload refs, and payload hashes to match the request and the stored submit decision.
- Record exactly one handoff/export preparation object in existing JSON-bearing state.
- Keep APS dispatch, external export/download, connector behavior, schema/runtime/source widening, retry/recovery, pass-entry changes, broader UI, qualitative/hybrid/RAG/vector, and full mockup behavior disabled.
- Preserve the existing single-item package-review submit, handoff/export, APS dispatch, and download chains unchanged.

## Decision Vocabulary

A future implementation governed by this freeze may admit only these operator decisions:

| Decision | Meaning | Allowed next state |
| --- | --- | --- |
| `authorize_prepare` | The approved associated-cohort package set may be prepared as an internal handoff/export envelope. | `handoff_export_prepared` |
| `hold` | The package set remains approved but must not be prepared for handoff/export yet. | `handoff_export_held` |
| `decline` | The package set is not to be handed off/exported under the current authority basis. | `handoff_export_declined` |
| `blocked` | The operator cannot authorize preparation because required evidence, package visibility, or downstream policy is insufficient. | `handoff_export_blocked` |

The decision vocabulary is internal preparation only. It is not an APS handoff command, external export command, connector dispatch command, package rebuild command, rerun command, result-review amendment, package-review amendment, or approved-plan supersession.

## Explicit Non-Goals

- No APS dispatch, external export/download readiness, delivery, or connector dispatch.
- No package payload editing, copying, reconstruction, rebuild, or variant rewrite controls.
- No new `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3ReconciliationRecord`, or `L3OutputPackage` rows.
- No new handoff/export table, schema migration, model, runtime, or source widening.
- No local upload or directory ingestion.
- No qualitative, hybrid, RAG, vector, retry, recovery, replay, pass-entry, broader UI, broader associated-cohort review, or full mockup activation.
- No use of docs `54`/`55` as direct associated-cohort handoff/export authority without the cohort-specific gates in this freeze and the companion contract.

## Required Proof Before Implementation Can Be Considered Settled

- Existing single-item package-review submit, handoff/export, APS dispatch, and download behavior remains unchanged.
- Existing associated-cohort package-review submit behavior from PR `#456` remains unchanged except for admitted handoff/export preparation readiness/action.
- Missing, malformed, stale, partial, non-cohort, duplicate, conflicting, or cross-session package-review submit state fails closed.
- Missing or mismatched reconciliation id, package ids, package kinds, payload refs, payload hashes, package-review submit ref, package-review state, package-review preview hash, result-review record ref, pass run, analysis run, source gate, method, cohort shape, source dataset version ids, or package-construction authority fails closed.
- Requests with APS dispatch, external export/download, connector, source, schema, runtime, retry/recovery, pass-entry, package-payload override, package-variant edit, result-review amendment, package-review amendment, package-construction mutation, or broader UI fields fail closed.
- Successful preparation records exactly one handoff/export preparation object and no new package/reconciliation/artifact rows.
- Duplicate identical preparation requests are deterministic and do not duplicate state.
- Conflicting duplicate preparation requests fail closed.
- No package payload refs, payload hashes, or payload files change.
- If rendered UI behavior changes, both headed and headless Chrome proof are required.

## Stop Conditions

Stop and return to planning if implementation requires:

- APS dispatch, external export/download, or connector behavior;
- downstream destination selection beyond an internal prepare-only envelope;
- package payload rewrite, copy, or package reconstruction;
- schema migration or model changes;
- changing lower-level `descriptive_summary` analysis behavior;
- changing service-owned associated-cohort pass-entry admission from docs `78`/`79`;
- weakening existing single-item handoff/export gates;
- creating package rows, reconciliation rows, artifacts, plans, passes, or runs;
- updating `L3OutputPackage.status`;
- rerun/recovery/cancellation/retry behavior beyond deterministic request idempotency;
- result-review or package-review amendment or supersession;
- approved-plan supersession;
- source expansion or local ingestion;
- runtime DB widening;
- qualitative, hybrid, RAG, or vector execution;
- full mockup activation.
