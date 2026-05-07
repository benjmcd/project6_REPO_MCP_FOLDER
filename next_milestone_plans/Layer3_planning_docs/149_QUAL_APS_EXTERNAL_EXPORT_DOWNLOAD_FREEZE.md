# Layer 3 Qualitative APS External Export/Download Freeze

Status: planning/control implementation-entry freeze for future `qual_aps_external_export_download_prepare_deliver`.

This document freezes the next bounded qualitative APS downstream pass after the live `qual_aps_aps_handoff_dispatch_entry` runtime. Current main still blocks qualitative APS external export/download with `qualitative_aps_external_export_download_not_admitted`; this freeze does not remove that blocker by itself.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- latest live qualitative APS boundary: `qual_aps_aps_handoff_dispatch_entry`
- latest live qualitative APS response schema: `layer3.qual_aps_aps_handoff_dispatch.v1`
- predecessor docs: `147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md` and `148_QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT.md`
- selected future prepare route: `POST /api/v1/layer3/handoff/export/download/prepare`
- selected future prepare response schema: `layer3.qual_aps_external_export_download_prepare.v1`
- selected future deliver route: `POST /api/v1/layer3/handoff/export/download/deliver`
- selected future delivery schema/header: `layer3.qual_aps_external_export_download_delivery.v1`
- selected future mode: `qual_aps_external_export_download_prepare_deliver`
- current live blocker: `qualitative_aps_external_export_download_not_admitted`
- companion contract: `150_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT.md`

Live source, tests, models, migrations, routes, and proof-checker behavior outrank this planning document. The existing associated-cohort external export/download path is pattern evidence only; it does not prove qualitative APS delivery is live.

## Decision

The next eligible implementation boundary is:

- `qual_aps_external_export_download_prepare_deliver`

The implementation may remove only the exact qualitative APS external export/download blocker after a recorded qualitative APS APS handoff dispatch. It must reuse the existing external export/download prepare and deliver route family unless source inspection proves reuse would make associated-cohort and qualitative APS authority ambiguous.

The admitted target is same-origin delivery of the server-owned APS evidence-bundle artifact that was already materialized by the APS handoff owner service. It is not a provider upload, public URL generation, signed URL generation, connector run, destination write, package rebuild, package mutation, raw ingestion, RAG/vector operation, rendered UI pass, hidden LLM pass, model/migration pass, or auth/security pass.

## Runtime Shape

The future implementation may include only:

- qualitative APS readiness admission in `external_export_download_prepare`;
- qualitative APS delivery admission in `external_export_download_deliver`;
- a qualitative response schema for prepare, such as `layer3.qual_aps_external_export_download_prepare.v1`;
- a qualitative delivery schema/header, such as `layer3.qual_aps_external_export_download_delivery.v1`;
- persisted readiness state in the existing `external_export_download_prepare` summary object on the existing reconciliation/session JSON surfaces;
- same-origin artifact streaming of the already persisted APS bundle artifact;
- strict server-side revalidation of session, approved plan, selected qualitative pass run, preview id/hash, result-review approval, package-review preview hash, package construction, package-review submit, handoff/export prepare, APS handoff dispatch, APS output package, APS bundle ref/id/schema, payload hash, bundle file hash, bundle file size, APS content document, chunks, material snapshot, analysis unit, analysis set, and output payload identity;
- focused API and bounded E2E tests that extend the qualitative APS path from APS handoff dispatch through external export/download prepare and deliver.

## Allowed Writes

Only these writes are eligible for the future implementation:

- one qualitative APS external export/download readiness object in existing `L3ReconciliationRecord.summary_json`;
- optional `L3Session.summary_json` pointer/index fields needed for current session-summary projections.

Delivery must stream the existing server-owned APS bundle artifact and must not persist a new delivery row unless a later explicit delivery-state freeze admits one. The implementation must not write or rewrite package payload files, APS bundle files, source files, destination artifacts, provider objects, connector rows, signed-reference rows, auth rows, RAG/vector rows, or model/migration state.

## Forbidden Writes And Effects

The future implementation must not:

- create new `L3ReconciliationRecord`, `L3OutputPackage`, `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, connector, destination, provider, delivery, signed-reference, auth, source-ingestion, RAG/vector, runtime snapshot, or mockup rows;
- mutate existing qualitative package rows, APS handoff package rows, payload refs, payload hashes, package payload bodies, APS bundle artifacts, result-review state, package-review preview state, package construction state, package-review submit state, handoff/export prepare state, APS handoff dispatch state, source authority rows, or qualitative execution output;
- generate public URLs, signed URLs, provider URLs, external object-store ACLs, connector dispatches, destination writes, package mutations, package reconstructions, package supersessions, source expansion, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, hidden LLM planning, full mockup activation, rendered UI controls, theme behavior, model/migration changes, or auth/security behavior.

## Positive Invariants

The future implementation is acceptable only if it proves:

- admission is limited to `ENGINE_FAMILY_QUAL_APS_DOCUMENT` and `single_aps_doc_qualitative_pass`;
- readiness requires recorded qualitative APS APS handoff dispatch state;
- readiness uses the APS handoff package row and server-owned APS bundle artifact as authority;
- `analysis_run_id` remains absent or null for qualitative APS;
- APS bundle ref, bundle id, schema id, package id, package kind, source artifact hash, source artifact size, payload refs, payload hashes, package-review submit record ref, prepare record ref, handoff/export envelope ref, APS handoff record ref, and result-review record ref all match persisted server authority;
- delivery revalidates readiness by rerunning prepare validation with source artifact hash/size checks before streaming;
- delivery mode is `same_origin_artifact_stream`;
- browser/download fields remain same-origin and do not imply a public URL, signed URL, provider URL, connector run, destination send, or external object-store delivery;
- existing associated-cohort external export/download prepare, deliver, delivery UI, and signed-reference behavior remains unchanged;
- all forbidden source/downstream/provider/connector/RAG/model/auth/UI/theme fields fail closed before mutation.

## Required Tests

Minimum implementation proof for the future runtime:

- successful qualitative APS prepare after `qual_aps_aps_handoff_dispatched`;
- successful same-origin qualitative APS delivery from the prepared readiness object;
- session summary changes from `qualitative_aps_external_export_download_not_admitted` to qualitative readiness only after prepare;
- delivery revalidates current readiness before streaming;
- stale or missing external export/download record ref fails closed;
- stale or missing export download descriptor ref fails closed;
- stale or missing APS bundle ref/id/schema fails closed;
- stale package ids, package kinds, payload refs, payload hashes, result-review record ref, package-review preview hash, submit record ref, prepare record ref, envelope ref, or APS handoff record ref fails closed;
- missing APS handoff package row fails closed;
- missing APS bundle artifact fails closed;
- APS bundle file hash or size mismatch fails closed;
- wrong engine family, wrong source shape, or non-qualitative APS pass fails closed;
- forbidden provider/public URL, signed URL, connector, destination, package mutation, source expansion, RAG/vector, hidden LLM, UI, theme, auth, model, and migration fields fail closed before mutation;
- exactly zero new rows/files beyond the admitted readiness JSON state on prepare;
- exactly zero rows/files are written by delivery;
- existing associated-cohort external export/download prepare/deliver and signed-reference behavior remains unchanged;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

Browser proof is not required for a backend/API-only same-origin delivery implementation. Headed and headless Chrome proof, including relevant theme checks, becomes required if rendered `/review/layer3` or theme-visible behavior changes.

## Stop Conditions

Stop before implementation if the intended change requires:

- provider/public URL behavior, signed URL behavior, external object-store ACLs, connector/destination dispatch, or real destination writes;
- package payload rewrite, package reconstruction, package mutation, package supersession, or replacement namespace behavior;
- new rows outside existing summary JSON readiness state;
- source expansion, ingestion, local upload, local-directory ingestion, web connector retrieval, source adapter registry behavior, or RAG/vector retrieval;
- qualitative cohort, broad qualitative, hybrid, comparative, cross-document, hidden LLM, prompt/model behavior, or external model calls;
- rendered UI controls, destination controls, package editors, or theme-visible behavior without a separate UI freeze;
- auth/security behavior.
