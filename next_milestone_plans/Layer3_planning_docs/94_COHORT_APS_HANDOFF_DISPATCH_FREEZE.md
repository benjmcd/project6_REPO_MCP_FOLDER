# Layer 3 Selected-Pass Cohort APS Handoff Dispatch Freeze

## Status

Current-main planning-only freeze from PR `#464` for the next bounded Layer 3 workbench tranche after PR `#460` and PR `#462`.

This document does not make associated-cohort APS handoff dispatch live. It selects only the next eligible governance boundary after merged selected-pass associated-cohort `descriptive_summary` handoff/export prepare-only authority: a bounded APS evidence-bundle handoff dispatch decision for one exact prepared associated-cohort internal envelope.

## Authority Boundary

Current live authority is limited to:

- PR `#424`/`#425`: service-owned associated-cohort `descriptive_summary` materialization through `materialize_pass_entry(...)` only when `formation_basis_json["requested_method_name"] == "descriptive_summary"` is an exact string.
- PR `#432`: selected-pass associated-cohort execution-start/result-status over existing backend/API workbench surfaces.
- PR `#438`: selected-pass associated-cohort result review through the existing backend/API result-review endpoint.
- PR `#443`: rendered `/review/layer3` presentation/control for that exact associated-cohort result-review path.
- PR `#447`: read-only associated-cohort package-review preview/readiness inspection through the existing package-preview route and `/review/layer3` UI.
- PR `#451`: bounded associated-cohort package-construction commit over docs `88`/`89`, creating exactly one reconciliation row, three package rows, and three payload files.
- PR `#456`: bounded associated-cohort package-review submit over docs `90`/`91`, recording exactly one package-review decision object in existing JSON-bearing state.
- PR `#458`: docs `92`/`93` current-main planning-only associated-cohort handoff/export governance.
- PR `#460`: bounded backend/API associated-cohort handoff/export prepare-only state.
- PR `#462`: rendered `/review/layer3` prepare-control authority projection/proof over the PR `#460` server state.

Docs `58_L3_WB_APS_HANDOFF_DISPATCH_FREEZE.md` and `59_L3_WB_APS_HANDOFF_DISPATCH_API_AND_STATE_CONTRACT.md` plus PR `#260`/`#261`/`#263` remain single-item APS dispatch authority. They are a pattern source and owner-service compatibility source, not direct authority to dispatch associated-cohort packages without the cohort-specific gates in this freeze and the companion contract.

Current `backend/app/services/layer3_workbench.py` intentionally blocks associated-cohort APS dispatch after cohort prepare state with `associated_cohort_aps_handoff_dispatch_not_admitted`. A future implementation may only narrow or remove that blocker for the exact authority chain in this freeze and `95_COHORT_APS_HANDOFF_DISPATCH_CONTRACT.md`.

## Frozen Decision

The next eligible planning tranche is:

> Freeze a bounded associated-cohort APS handoff dispatch step after one exact selected-pass associated-cohort `descriptive_summary` package set has been prepared as an internal handoff/export envelope by PR `#460`, with rendered prepare authority projected and browser-proven by PR `#462`.

The future tranche may dispatch one prepared associated-cohort internal envelope into the existing APS evidence-bundle handoff owner-service family. It must not prepare external export/download, create connector or generic downstream dispatch, mutate or copy package payloads, create new reconciliation/package/source rows beyond the one APS handoff package row admitted by the existing owner service, or widen schema/runtime/source behavior.

## In Scope For The Future Implementation

- Preserve the existing `POST /api/v1/layer3/handoff/aps/dispatch` route family unless implementation audit proves a separate cohort-specific endpoint is required to avoid request/response ambiguity.
- Admit only the exact selected-pass associated-cohort `descriptive_summary` package set already proven by PR `#432`, PR `#438`, PR `#443`, PR `#447`, PR `#451`, PR `#456`, PR `#460`, and PR `#462`.
- Require `handoff_export_state == handoff_export_prepared`, `handoff_target == internal_export_envelope`, and `export_mode == prepare_only`.
- Require `pass_type == associated_cohort`, `pass_scope == quantitative_associated_cohort_dataset_version`, `method == descriptive_summary`, `source_gate == 78_COHORT_FREEZE`, and `source_shape == aligned_wide_table`.
- Require package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE` and package-review submit schema `layer3.cohort_package_review_submit.v1`.
- Require exactly one reconciliation row and exactly three existing source package rows for `canonical_internal`, `user_facing`, and `review_facing`.
- Require stored package ids, package kinds, payload refs, payload hashes, package-review submit ref, prepare ref, and prepared envelope ref to match server-stored authority.
- Call or wrap the existing APS evidence-bundle handoff owner service only after all cohort-specific authority checks pass.
- Record exactly one APS handoff dispatch summary in existing JSON-bearing workbench state, if needed for session/reconciliation visibility.
- Allow exactly one APS-facing `L3OutputPackage` row of kind `aps_evidence_bundle_handoff` when the existing owner service succeeds.
- Allow exactly one persisted APS evidence-bundle artifact produced by the existing APS evidence-bundle handoff contract.
- Keep external export/download, connector dispatch, generic downstream dispatch, destination selection, schema/runtime/source widening, retry/recovery, pass-entry changes, broader UI, qualitative/hybrid/RAG/vector, and full mockup behavior disabled.
- Preserve existing single-item APS dispatch, external export/download readiness, delivery, and rendered APS dispatch UI behavior unchanged.

## Decision Vocabulary

A future implementation governed by this freeze may admit only this operator decision:

| Decision | Meaning | Allowed next state |
| --- | --- | --- |
| `dispatch_aps_handoff` | Dispatch the prepared associated-cohort internal envelope to the existing APS evidence-bundle handoff owner-service family. | `aps_handoff_dispatched` |

The decision vocabulary is APS evidence-bundle handoff only. It is not an external export command, download command, connector dispatch command, generic downstream dispatch command, destination-selection command, package rebuild command, rerun command, result-review amendment, package-review amendment, or approved-plan supersession.

## Explicit Non-Goals

- No external export/download readiness, same-origin delivery, browser download controls, public URLs, or signed URLs.
- No connector dispatch, connector-run creation, non-APS downstream dispatch, or destination selection.
- No package payload editing, copying, reconstruction, rebuild, amendment, supersession, or variant rewrite controls.
- No new `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, or `L3ReconciliationRecord` rows.
- No new source rows, local upload, directory ingestion, schema migration, model, or runtime DB widening.
- No new package rows except the single `aps_evidence_bundle_handoff` row produced by the existing APS handoff owner-service contract on successful dispatch.
- No changes to lower-level `descriptive_summary` execution, service-materialize admission, package-construction, package-review submit, or handoff/export prepare-only behavior outside the narrow dispatch blocker.
- No rendered `/review/layer3` UI changes by this freeze alone.
- No qualitative, hybrid, RAG, vector, retry, recovery, replay beyond deterministic dispatch idempotency, broader associated-cohort review, broader UI, or full mockup activation.
- No use of docs `58`/`59` as direct associated-cohort dispatch authority without the cohort-specific gates in this freeze and the companion contract.

## Required Proof Before Implementation Can Be Considered Settled

- Existing single-item APS dispatch, external export/download readiness, delivery, and rendered APS dispatch UI behavior remains unchanged.
- Existing associated-cohort handoff/export prepare-only behavior from PR `#460` and rendered prepare projection from PR `#462` remains unchanged except for admitted APS dispatch readiness/action.
- Missing, malformed, stale, partial, non-cohort, duplicate, conflicting, or cross-session package-review submit, handoff/export prepare, or APS dispatch state fails closed.
- Missing or mismatched reconciliation id, package ids, package kinds, payload refs, payload hashes, package-review submit ref, package-review state, package-review preview hash, result-review record ref, pass run, analysis run, source gate, method, cohort shape, source dataset version ids, package-construction authority, prepare ref, or envelope ref fails closed.
- Requests with external export/download, connector, generic dispatch, destination, source, schema, runtime, retry/recovery, pass-entry, package-payload override, package-variant edit, result-review amendment, package-review amendment, package-construction mutation, handoff/export mutation, artifact creation, or UI-only inferred readiness fields fail closed.
- Successful dispatch records exactly one APS handoff dispatch object, exactly one APS handoff package row, exactly one APS evidence-bundle artifact, and no new source package/reconciliation/artifact/plan/pass/run rows.
- Duplicate identical dispatch requests are deterministic and do not duplicate state.
- Conflicting duplicate dispatch requests fail closed.
- No source package payload refs, payload hashes, or payload files change.
- If rendered UI behavior changes, both headed and headless Chrome proof are required.

## Stop Conditions

Stop and return to planning if implementation requires:

- external export/download, browser delivery, connector, generic downstream dispatch, or destination selection;
- package payload rewrite, copy, package reconstruction, amendment, or supersession;
- schema migration, model changes, runtime DB widening, source expansion, local upload, or directory ingestion;
- changing lower-level `descriptive_summary` analysis behavior;
- changing service-owned associated-cohort pass-entry admission from docs `78`/`79`;
- weakening existing single-item APS dispatch, external export/download, or delivery gates;
- creating source package rows, reconciliation rows, analysis artifacts, plans, passes, or runs;
- updating existing `L3OutputPackage.status`;
- rerun/recovery/cancellation/retry behavior beyond deterministic request idempotency;
- result-review or package-review amendment or supersession;
- approved-plan supersession;
- qualitative, hybrid, RAG, or vector execution;
- broader UI or full mockup activation.
