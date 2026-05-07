# Layer 3 Qualitative APS APS Handoff Dispatch Freeze

Status: current-main runtime boundary for `qual_aps_aps_handoff_dispatch_entry`.

This document now records the bounded qualitative APS downstream runtime after the live `qual_aps_handoff_export_prepare_entry` runtime. Current main admits only server-side APS evidence-bundle handoff dispatch over an already prepared qualitative APS handoff/export envelope.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- latest live qualitative APS boundary: `qual_aps_aps_handoff_dispatch_entry`
- latest live qualitative APS response schema: `layer3.qual_aps_aps_handoff_dispatch.v1`
- predecessor docs: `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md` and `146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md`
- package-review submit docs: `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md`
- package construction docs: `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`
- package preview docs: `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md` and `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`
- qualitative execution docs: `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, and `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`
- selected live route: `POST /api/v1/layer3/handoff/aps/dispatch`
- selected live response schema: `layer3.qual_aps_aps_handoff_dispatch.v1`
- selected live mode: `qual_aps_aps_handoff_dispatch_entry`
- current deferred next blocker in live session summary after dispatch: `qualitative_aps_external_export_download_not_admitted`
- companion contract: `148_QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT.md`

Live source, tests, models, migrations, routes, and proof-checker behavior outrank this planning document. Current main removes only the exact `qualitative_aps_aps_handoff_dispatch_not_admitted` blocker for this authority chain and still blocks qualitative APS external export/download with `qualitative_aps_external_export_download_not_admitted`.

## Decision

The implemented boundary is:

- `qual_aps_aps_handoff_dispatch_entry`

The runtime reuses the existing `POST /api/v1/layer3/handoff/aps/dispatch` route family only for an already prepared standalone APS qualitative package set. It materializes exactly one APS evidence-bundle handoff package through the existing APS handoff owner-service contract, then records exactly one qualitative APS APS handoff dispatch object in existing JSON-bearing state.

The runtime stops before external export/download prepare or deliver, connector/destination dispatch, provider/public URLs, rendered UI controls, source expansion, RAG/vector retrieval, package mutation/reconstruction, hidden LLM planning, full mockup activation, model/migration work, and authentication/security behavior.

## Why This Comes Next

Current main can produce a qualitative APS internal handoff/export envelope and can now hand that envelope to the APS evidence-bundle handoff owner service for the qualitative APS path. Qualitative APS external export/download remains deferred until a separate freeze admits readiness and delivery over the dispatched APS bundle identity.

The pass must remain narrower than generic connector dispatch. It is not a destination send, public URL generation, provider upload, broad package mutation, or external delivery pass.

## Decision Vocabulary

Only this operator decision is in scope for the current implementation:

| Decision | Meaning | Allowed next state |
| --- | --- | --- |
| `dispatch_aps_handoff` | The prepared qualitative APS internal envelope may be materialized as an APS evidence-bundle handoff package through the server-side owner service. | `qual_aps_aps_handoff_dispatched` |

The decision vocabulary is APS evidence-bundle handoff only. It is not an external export/download command, connector dispatch command, destination send command, provider/public URL request, package rebuild command, result-review amendment, package-review amendment, source-expansion command, or retry/recovery command.

## Runtime Shape

The implementation includes only:

- reusing or narrowly extending `POST /api/v1/layer3/handoff/aps/dispatch` for `ENGINE_FAMILY_QUAL_APS_DOCUMENT`;
- response schema `layer3.qual_aps_aps_handoff_dispatch.v1`;
- strict request DTO behavior with forbidden downstream/source/provider/connector/RAG/model/auth/UI/theme fields;
- server revalidation of session, approved plan, selected pass run, preview id/hash, approved result review, qualitative package-review preview hash, construction basis hash, package-review submit state, handoff/export prepare state, prepare record ref, envelope ref, reconciliation record, output package ids, package kinds, payload refs, payload hashes, APS content document, chunks, material snapshot, analysis unit, analysis set, qualitative output payload authority, and package payload authority;
- exactly one APS evidence-bundle handoff package row through the existing `layer3_aps_handoff.py` owner service;
- exactly one dispatch state object in existing `L3ReconciliationRecord.summary_json`;
- optional `L3Session.summary_json` pointer/index fields needed for existing readiness projections;
- deterministic idempotent retry handling for duplicate `client_request_id`;
- concurrency protection so duplicate or conflicting dispatch attempts cannot create divergent decision state;
- focused service/API tests and one bounded E2E extension from qualitative APS handoff/export prepare through APS handoff dispatch.

## Allowed Writes

Only these writes are admitted for the current runtime:

- one APS evidence-bundle handoff package row created by the existing APS handoff owner service;
- one qualitative APS APS handoff dispatch object in `L3ReconciliationRecord.summary_json`;
- optional `L3Session.summary_json` pointer/index fields needed for existing readiness projections;
- one server-owned APS bundle artifact file required by the owner service.

The implementation must not create new reconciliation rows, source rows, analysis rows, connector rows, destination rows, provider rows, delivery rows, signed-reference rows, auth rows, RAG/vector rows, or model/migration state under this freeze.

## Forbidden Writes And Effects

The current implementation must not:

- create `L3ReconciliationRecord`, `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, connector, destination, provider, source-ingestion, RAG/vector, runtime snapshot, auth, external export/download, signed-reference, or delivery rows;
- write, delete, rewrite, copy, or replace the existing qualitative APS package payload files;
- mutate the existing `canonical_internal`, `user_facing`, or `review_facing` package rows, payload refs, payload hashes, package payload bodies, result-review state, package-review preview state, package construction state, package-review submit state, handoff/export prepare state, construction basis hash, submit basis fields, source authority rows, or qualitative execution output;
- trigger external export/download prepare or deliver, connector/destination dispatch, provider/public URL generation, package mutation, package reconstruction, package supersession, source expansion, RAG/vector retrieval, hidden LLM planning, full mockup activation, rendered UI behavior, theme behavior, model/migration work, or auth/security behavior.

## Positive Invariants

The current boundary is acceptable only if it proves:

- admission is limited to `ENGINE_FAMILY_QUAL_APS_DOCUMENT` and `single_aps_doc_qualitative_pass`;
- dispatch requires live qualitative APS handoff/export prepare authority;
- prepare state is `qual_aps_handoff_export_prepared` and has an internal envelope ref;
- package-review submit schema is `layer3.qual_aps_package_review_submit.v1`;
- package construction source gate is `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE`;
- package kinds are exactly `canonical_internal`, `user_facing`, and `review_facing`;
- package ids, payload refs, payload hashes, package-review preview hash, construction basis hash, package-review submit record ref, prepare record ref, envelope ref, and result-review record ref match persisted server authority;
- `analysis_run_id` is absent or null for qualitative APS;
- owner-service APS handoff compatibility is satisfied by persisted package/source/material provenance, not client-provided package bytes;
- duplicate `client_request_id` with identical authority is deterministic;
- duplicate `client_request_id` or later request with conflicting authority fails closed;
- dispatch does not enable external export/download, connector/destination dispatch, or provider/public URLs by itself;
- existing quantitative single-item, associated-cohort, package construction, package submit, handoff/export, APS dispatch, external export/download, replacement package, and connector record behavior remains unchanged;
- rendered UI and theme behavior remain unchanged unless a separate UI freeze admits them.

## Required Tests

Minimum implementation proof for the current runtime:

- successful API dispatch after one prepared standalone APS qualitative handoff/export envelope;
- bounded E2E extension from qualitative APS handoff/export prepare through APS handoff dispatch, stopping before external export/download;
- missing handoff/export prepare state fails closed;
- non-prepared handoff/export state fails closed;
- missing or stale prepare record ref fails closed;
- missing or stale handoff/export envelope ref fails closed;
- missing package-review submit fails closed;
- missing package construction fails closed;
- partial package rows or missing payload refs/hashes fail closed;
- stale preview id/hash, result-review record ref, package-review preview hash, construction basis hash, reconciliation id, package ids, package kinds, payload refs, payload hashes, or submit record ref fail closed;
- wrong engine family and wrong source shape fail closed;
- APS owner-service compatibility failure fails closed before recording dispatch state;
- forbidden source/downstream/provider/connector/RAG/model/auth/UI/theme fields fail closed before mutation;
- duplicate identical request is deterministic;
- conflicting duplicate request fails closed;
- exactly one APS handoff package row and exactly one APS bundle artifact are created on success;
- no rows or files are created on failure;
- existing package payload refs, hashes, rows, and files remain unchanged;
- external export/download, connector/destination, provider URL, source expansion, RAG/vector, hidden LLM, full mockup, rendered UI, theme, model/migration, and auth/security side effects remain absent;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

Browser proof is not required for a backend/API-only APS handoff dispatch implementation. Headed and headless Chrome proof, including relevant theme checks, becomes required if rendered `/review/layer3` or theme-visible behavior changes.

## Stop Conditions

Stop before implementation if the intended change requires:

- external export/download prepare/deliver, connector/destination dispatch, or provider/public URL behavior;
- package payload rewrite, package reconstruction, package mutation, package supersession, or replacement namespace behavior;
- new reconciliation/source/analysis/connector/destination/provider/auth rows, schema/model/migration changes, or existing package row mutation;
- source expansion, ingestion, local upload, local-directory ingestion, web connector retrieval, or RAG/vector retrieval;
- qualitative cohort, broad qualitative, hybrid, comparative, cross-document, hidden LLM, prompt/model behavior, or external model calls;
- rendered UI controls, document-trace controls, destination controls, package editors, or theme-visible behavior without a separate UI freeze;
- auth/security behavior.
