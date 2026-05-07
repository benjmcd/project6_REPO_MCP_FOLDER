# Layer 3 Qualitative APS Handoff Export Prepare Freeze

Status: planning/control freeze for future `qual_aps_handoff_export_prepare_entry`.

This document selects the next eligible qualitative APS downstream boundary after the live `qual_aps_package_review_submit_entry` runtime. It admits no runtime behavior by itself. It freezes only a future internal handoff/export prepare decision over an already approved standalone APS qualitative package-review submit state.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- predecessor runtime: `qual_aps_package_review_submit_entry`
- predecessor response schema: `layer3.qual_aps_package_review_submit.v1`
- predecessor docs: `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md`
- package construction docs: `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`
- package preview docs: `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md` and `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`
- qualitative execution docs: `114_QUAL_APS_EXEC_FREEZE.md`, `115_QUAL_APS_EXEC_CONTRACT.md`, and `119_L3_QUAL_APS_EXEC_ENTRY_FREEZE.md`
- current route family to audit first: `POST /api/v1/layer3/handoff/export/prepare`
- selected future mode: `qual_aps_handoff_export_prepare_entry`
- selected future response schema: `layer3.qual_aps_handoff_export_prepare.v1`
- companion contract: `146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md`

Live source and tests outrank this planning document. This document is not proof that qualitative APS handoff/export prepare is live.

## Decision

The next implementation-entry candidate is:

- `qual_aps_handoff_export_prepare_entry`

The future runtime may record exactly one internal prepare-only handoff/export decision over the already submitted qualitative APS package set. It must reuse the existing handoff/export route family unless implementation audit proves that route reuse would make qualitative APS, quantitative single-item, or associated-cohort authority ambiguous.

The future runtime must stop before APS handoff dispatch, external export/download, connector/destination dispatch, provider/public URLs, rendered UI controls, source expansion, RAG/vector retrieval, package mutation/reconstruction, hidden LLM planning, full mockup activation, model/migration work, and authentication/security behavior.

## Why This Comes Next

Current main now has a durable qualitative APS package set and a package-review submit decision, but it still has no qualitative APS internal export envelope. APS dispatch and external export/download require a prepared handoff/export envelope first.

This pass must precede qualitative APS APS dispatch and external export/download. It must follow package-review submit because prepare authority must prove that the package set is both constructed and approved for downstream consideration.

## Current Blocker

Current main has generic and associated-cohort handoff/export prepare behavior, but no qualitative APS-specific prepare freeze/runtime authority. Direct reuse of the generic route is not sufficient by itself because qualitative APS package preview, construction, and submit use distinct qualitative authority hashes, source-shape fields, and no `AnalysisRun`.

The future implementation must explicitly validate qualitative APS authority rather than relying on the generic single-item path.

## Decision Vocabulary

Only these operator decisions are in scope for a future implementation:

| Decision | Meaning | Allowed next state |
| --- | --- | --- |
| `authorize_prepare` | The approved qualitative APS package set may be prepared as an internal handoff/export envelope. | `qual_aps_handoff_export_prepared` |
| `hold` | The package set remains approved but must not be prepared yet. | `qual_aps_handoff_export_held` |
| `decline` | The package set is not to be handed off/exported under the current authority basis. | `qual_aps_handoff_export_declined` |
| `blocked` | The operator cannot authorize preparation because evidence, policy, or package authority is insufficient. | `qual_aps_handoff_export_blocked` |

The decision vocabulary is internal preparation only. It is not an APS dispatch command, external export/download command, connector dispatch command, package rebuild command, result-review amendment, package-review amendment, package mutation, rerun, recovery, source-expansion command, or provider URL request.

## Future Runtime Shape

The future implementation may include only:

- extending or reusing `POST /api/v1/layer3/handoff/export/prepare` for `ENGINE_FAMILY_QUAL_APS_DOCUMENT`;
- response schema `layer3.qual_aps_handoff_export_prepare.v1`;
- strict request DTO behavior with forbidden downstream/source/provider/connector/RAG/model/auth/UI fields;
- server revalidation of session, approved plan, selected pass run, preview id/hash, approved result review, qualitative package-review preview hash, construction basis hash, package-review submit record ref, package-review submit schema, reconciliation record, output package ids, package kinds, payload refs, payload hashes, APS content document, chunks, material snapshot, analysis unit, analysis set, and qualitative output payload authority;
- exactly one handoff/export prepare object in existing durable JSON-bearing state;
- optional internal handoff/export envelope identity when `operator_decision == "authorize_prepare"`;
- deterministic idempotent retry handling for duplicate `client_request_id`;
- concurrency protection so duplicate or conflicting prepare attempts cannot create divergent decision state;
- focused service/API tests and one bounded E2E extension from qualitative APS package-review submit through handoff/export prepare.

## Allowed Writes

Only these writes are admitted for a future runtime:

- one qualitative APS handoff/export prepare decision object in `L3ReconciliationRecord.summary_json`;
- optional `L3Session.summary_json` pointer/index fields needed for existing readiness projections.

The future implementation must not create new rows or files under this freeze.

## Forbidden Writes And Effects

The future implementation must not:

- create `L3ReconciliationRecord`, `L3OutputPackage`, `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, connector, destination, provider, source-ingestion, RAG/vector, runtime snapshot, auth, delivery, signed-reference, APS dispatch, or external export/download rows;
- write, delete, rewrite, copy, or replace package payload files;
- mutate `L3OutputPackage.payload_ref`, `L3OutputPackage.payload_hash`, package payload bodies, result-review state, package-review preview state, package construction state, package-review submit state, approved plan state, selected pass state, source authority rows, or construction/submit basis fields;
- update `L3OutputPackage.status` unless a separate freeze proves it is required;
- trigger APS dispatch, external export/download, connector/destination dispatch, provider/public URL generation, package mutation, package reconstruction, package supersession, source expansion, RAG/vector retrieval, hidden LLM planning, full mockup activation, rendered UI behavior, theme behavior, or auth/security behavior.

## Positive Invariants

The future boundary is acceptable only if it proves:

- admission is limited to `ENGINE_FAMILY_QUAL_APS_DOCUMENT` and `single_aps_doc_qualitative_pass`;
- handoff/export prepare requires live qualitative APS package-review submit authority;
- package-review submit schema is `layer3.qual_aps_package_review_submit.v1`;
- package construction source gate is `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE`;
- package kinds are exactly `canonical_internal`, `user_facing`, and `review_facing`;
- package ids, payload refs, payload hashes, construction basis hash, package-review preview hash, package-review submit record ref, and result-review record ref match persisted server authority;
- `analysis_run_id` is absent or null for qualitative APS;
- prepare records one decision object only;
- duplicate `client_request_id` with identical authority is deterministic;
- duplicate `client_request_id` or later request with conflicting authority fails closed;
- prepare does not enable APS dispatch, external export/download, connector/destination dispatch, or provider/public URLs by itself;
- existing quantitative single-item, associated-cohort, package construction, package submit, handoff/export, APS dispatch, and external export/download behavior remains unchanged;
- rendered UI and theme behavior remain unchanged unless a separate UI freeze admits them.

## Required Tests For Future Runtime

Minimum implementation proof for a later runtime pass:

- successful API prepare for one approved standalone APS qualitative package-review submit state;
- bounded E2E extension from qualitative APS submit through handoff/export prepare, stopping before APS dispatch;
- missing package-review submit fails closed;
- missing package construction fails closed;
- partial package rows or missing payload refs/hashes fail closed;
- stale preview id/hash, result-review record ref, package-review preview hash, construction basis hash, reconciliation id, package ids, package kinds, payload refs, payload hashes, or submit record ref fail closed;
- non-approved package-review submit fails closed;
- invalid decision or missing notes for `hold`, `decline`, or `blocked` fails closed;
- forbidden source/downstream/provider/connector/RAG/model/auth/UI fields fail closed before mutation;
- duplicate identical request is deterministic;
- conflicting duplicate request fails closed;
- no rows or files are created on prepare;
- package payload refs, hashes, and files remain unchanged;
- APS dispatch, external export/download, connector/destination, provider URL, source expansion, RAG/vector, hidden LLM, full mockup, rendered UI, theme, and auth/security side effects remain absent;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

Browser proof is not required for a backend/API-only handoff/export prepare implementation. Headed and headless Chrome proof, including relevant theme checks, becomes required if rendered `/review/layer3` or theme-visible behavior changes.

## Stop Conditions

Stop before implementation if the intended change requires:

- APS dispatch, external export/download prepare/deliver, connector/destination dispatch, or provider/public URL behavior;
- package payload rewrite, package reconstruction, package mutation, package supersession, or replacement namespace behavior;
- new rows, schema/model/migration changes, or `L3OutputPackage.status` mutation;
- source expansion, ingestion, local upload, local-directory ingestion, web connector retrieval, or RAG/vector retrieval;
- qualitative cohort, broad qualitative, hybrid, comparative, cross-document, hidden LLM, prompt/model behavior, or external model calls;
- rendered UI controls, document-trace controls, destination controls, package editors, or theme-visible behavior without a separate UI freeze;
- auth/security behavior.
