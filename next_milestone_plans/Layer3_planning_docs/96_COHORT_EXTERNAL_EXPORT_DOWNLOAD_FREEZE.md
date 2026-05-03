# Layer 3 Selected-Pass Cohort External Export Download Readiness Freeze

## Status

Current-main planning-only freeze for the next bounded Layer 3 workbench tranche after PR `#466` associated-cohort APS evidence-bundle handoff dispatch.

This document does not make associated-cohort external export/download live. It selects only the next eligible governance boundary after merged selected-pass associated-cohort `descriptive_summary` APS handoff dispatch authority: a reference-only external export/download readiness descriptor over the already persisted APS evidence-bundle handoff artifact.

## Authority Boundary

Current live authority is limited to:

- PR `#424`/`#425`: service-owned associated-cohort `descriptive_summary` materialization through exact `formation_basis_json["requested_method_name"] == "descriptive_summary"`.
- PR `#432`: selected-pass associated-cohort execution-start/result-status over existing backend/API workbench surfaces.
- PR `#438`: selected-pass associated-cohort result review through the existing backend/API result-review endpoint.
- PR `#443`: rendered `/review/layer3` presentation/control for that exact associated-cohort result-review path.
- PR `#447`: read-only associated-cohort package-review preview/readiness inspection.
- PR `#451`: bounded associated-cohort package-construction commit, creating exactly one reconciliation row, three package rows, and three payload files.
- PR `#456`: bounded associated-cohort package-review submit, recording exactly one package-review decision object in existing JSON-bearing state.
- PR `#460`: bounded backend/API associated-cohort handoff/export prepare-only state.
- PR `#462`: rendered `/review/layer3` prepare-control authority projection/proof over the PR `#460` server state.
- PR `#466`: bounded backend/API associated-cohort APS evidence-bundle handoff dispatch, creating exactly one APS handoff dispatch object, one `aps_evidence_bundle_handoff` package row, and one APS evidence-bundle artifact through the existing owner-service family.

Docs `62_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md` and `63_L3_WB_EXTERNAL_EXPORT_DOWNLOAD_API_AND_STATE_CONTRACT.md` plus PRs `#269` through `#289` remain the existing general external export/download readiness, delivery, UI, and hardening chain. They are a pattern source and owner-service compatibility source, not direct authority to expose associated-cohort external export/download without the cohort-specific gates in this freeze and `97_COHORT_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT.md`.

Current `backend/app/services/layer3_workbench.py` intentionally blocks associated-cohort external export/download readiness after cohort APS dispatch state with `associated_cohort_external_export_download_prepare_not_admitted`. A future implementation may only narrow that blocker for the exact authority chain in this freeze and the companion contract.

## Frozen Decision

The next eligible planning tranche is:

> Freeze a bounded associated-cohort external export/download readiness step after one exact selected-pass associated-cohort `descriptive_summary` package set has been dispatched to the existing APS evidence-bundle handoff owner-service family by PR `#466`.

The future tranche may record one reference-only external export/download descriptor for the already persisted APS evidence-bundle handoff artifact. It must not deliver or stream the artifact, expose browser download controls, expose public/signed/local URLs, create connector or generic downstream dispatch, select destinations, mutate or copy package payloads, create new package/reconciliation/source/artifact rows, or widen schema/runtime/source behavior.

## In Scope For The Future Implementation

- Preserve the existing `POST /api/v1/layer3/handoff/export/download/prepare` route family unless implementation audit proves route reuse would make single-item and associated-cohort semantics ambiguous.
- Admit only the exact selected-pass associated-cohort `descriptive_summary` chain already proven by PR `#432`, PR `#438`, PR `#443`, PR `#447`, PR `#451`, PR `#456`, PR `#460`, PR `#462`, and PR `#466`.
- Require `pass_type == associated_cohort`, `pass_scope == quantitative_associated_cohort_dataset_version`, `method == descriptive_summary`, `source_gate == 78_COHORT_FREEZE`, `source_shape == aligned_wide_table`, and matching `source_dataset_version_ids`.
- Require package-construction source gate `88_COHORT_PACKAGE_CONSTRUCTION_FREEZE` and package-review submit schema `layer3.cohort_package_review_submit.v1`.
- Require `package_review_state == package_review_approved`, `handoff_export_state == handoff_export_prepared`, `handoff_target == internal_export_envelope`, and `export_mode == prepare_only`.
- Require `aps_handoff_state == aps_handoff_dispatched`, `aps_handoff_target == aps_evidence_bundle`, `dispatch_mode == server_side_aps_handoff`, and `aps_output_package_kind == aps_evidence_bundle_handoff`.
- Require stored package ids, package kinds, payload refs, payload hashes, package-review submit ref, prepare ref, prepared envelope ref, APS handoff ref, APS output package id, APS bundle ref, APS bundle id, APS schema id, APS bundle hash, and APS bundle size to match server-stored authority.
- Reuse the existing APS evidence-bundle validation path for the persisted APS handoff artifact.
- Record exactly one external export/download readiness summary in existing JSON-bearing workbench state.
- Keep browser delivery, rendered download controls, public/signed URLs, connector dispatch, generic downstream dispatch, destination selection, schema/runtime/source widening, retry/recovery, pass-entry changes, broader UI, qualitative/hybrid/RAG/vector, and full mockup behavior disabled.
- Preserve existing single-item external export/download readiness, delivery, and rendered download behavior unchanged.

## Decision Vocabulary

A future implementation governed by this freeze may admit only this operator decision:

| Decision | Meaning | Allowed next state |
| --- | --- | --- |
| `prepare_external_export_download` | Record a reference-only export/download readiness descriptor for the existing associated-cohort APS evidence-bundle handoff artifact. | `external_export_download_prepared` |

The decision vocabulary is readiness only. It is not a browser download command, file-streaming command, public-link command, signed-link command, connector dispatch command, generic downstream dispatch command, destination-selection command, package rebuild command, rerun command, result-review amendment, package-review amendment, or approved-plan supersession.

## Explicit Non-Goals

- No browser download route, rendered download button, rendered download link, public URL, signed URL, or local path exposure.
- No same-origin file streaming or delivery behavior by this freeze.
- No connector dispatch, connector-run creation, non-APS downstream dispatch, generic downstream dispatch, or destination selection.
- No package payload editing, copying, reconstruction, rebuild, amendment, supersession, or variant rewrite controls.
- No new `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, `L3ReconciliationRecord`, source, migration, model, runtime, connector-run, or additional `L3OutputPackage` rows.
- No new physical export artifact beyond the existing APS evidence-bundle handoff artifact.
- No changes to lower-level `descriptive_summary` execution, service-materialize admission, package construction, package-review submit, handoff/export prepare-only behavior, or APS handoff dispatch behavior outside the narrow readiness blocker.
- No rendered `/review/layer3` UI changes by this freeze alone.
- No qualitative, hybrid, RAG, vector, retry, recovery, replay beyond deterministic readiness idempotency, broader associated-cohort review, broader UI, or full mockup activation.
- No use of docs `62`/`63` as direct associated-cohort readiness authority without the cohort-specific gates in this freeze and the companion contract.

## Required Proof Before Implementation Can Be Considered Settled

- Existing single-item external export/download readiness, delivery, rendered readiness UI, and rendered delivery UI behavior remains unchanged.
- Existing associated-cohort APS handoff dispatch behavior from PR `#466` remains unchanged except for admitted external export/download readiness projection/action.
- Missing, malformed, stale, partial, non-cohort, duplicate, conflicting, or cross-session package-review submit, handoff/export prepare, APS handoff dispatch, or external export/download readiness state fails closed.
- Missing or mismatched reconciliation id, package ids, package kinds, payload refs, payload hashes, package-review submit ref, package-review state, package-review preview hash, result-review record ref, pass run, analysis run, source gate, method, cohort shape, source dataset version ids, package-construction authority, prepare ref, envelope ref, APS handoff ref, APS output package id/kind, APS bundle ref/id/schema/hash/size fails closed.
- Requests with browser download, public/signed URL, connector, generic dispatch, destination, source, schema, runtime, retry/recovery, pass-entry, package-payload override, package-variant edit, result-review amendment, package-review amendment, package-construction mutation, handoff/export mutation, APS dispatch mutation, artifact creation, or UI-only inferred readiness fields fail closed.
- Successful readiness records exactly one reference-only external export/download readiness object and no new package, reconciliation, source, `AnalysisArtifact`, connector-run, plan, pass, or run rows.
- Duplicate identical readiness requests are deterministic and do not duplicate state.
- Conflicting duplicate readiness requests fail closed.
- No source package payload refs, payload hashes, source package payload files, APS handoff package refs/hashes, or APS evidence-bundle artifact bytes change.
- If rendered UI behavior changes, both headed and headless Chrome proof are required.

## Stop Conditions

Stop and return to planning if implementation requires:

- browser delivery, file streaming, rendered download controls, public URLs, signed URLs, connector, generic downstream dispatch, or destination selection;
- package payload rewrite, copy, package reconstruction, amendment, or supersession;
- schema migration, model changes, runtime DB widening, source expansion, local upload, or directory ingestion;
- changing lower-level `descriptive_summary` analysis behavior;
- changing service-owned associated-cohort pass-entry admission from docs `78`/`79`;
- weakening existing single-item external export/download readiness or delivery gates;
- weakening existing associated-cohort APS handoff dispatch gates;
- creating package rows, source rows, reconciliation rows, analysis artifacts, connector runs, plans, passes, or runs;
- updating existing `L3OutputPackage.status`;
- rerun/recovery/cancellation/retry behavior beyond deterministic request idempotency;
- result-review or package-review amendment or supersession;
- approved-plan supersession;
- qualitative, hybrid, RAG, or vector execution;
- broader UI or full mockup activation.

