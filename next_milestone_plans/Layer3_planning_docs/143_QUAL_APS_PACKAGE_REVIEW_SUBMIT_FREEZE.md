# Layer 3 Qualitative APS Package Review Submit Freeze

Status: planning/control freeze for the next qualitative APS boundary after PR `#709`.

This document selects only a future `qual_aps_package_review_submit_entry` implementation-entry boundary. It does not implement package-review submit and does not admit handoff/export, APS handoff dispatch, external export/download, connector/destination dispatch, provider/public URLs, rendered UI controls, source expansion, broad qualitative/hybrid/RAG behavior, package mutation/reconstruction, hidden LLM planning, full mockup activation, model/migration work, or authentication/security behavior.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current-main anchor: PR `#709`, merge commit `aaf524a646946190584cf69822cde58834846b75`
- roadmap authority: `142_POST_709_ROADMAP_FREEZE.md`
- predecessor runtime: `qual_aps_package_construction_commit_entry`
- predecessor docs: `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`
- predecessor response schema: `layer3.qual_aps_package_construction_commit.v1`
- existing submit route family: `POST /api/v1/layer3/package/review/submit`
- selected future mode: `qual_aps_package_review_submit_entry`
- selected future response schema: `layer3.qual_aps_package_review_submit.v1`
- package kinds: `canonical_internal`, `user_facing`, `review_facing`
- blocker on current main: `qualitative_aps_package_review_submit_not_admitted`
- companion contract: `144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md`

Live source and tests outrank this planning document. This document is a freeze for the next possible runtime pass only.

## Decision

The selected next runtime mode is:

- `qual_aps_package_review_submit_entry`

The selected mode may record exactly one operator package-review decision over the already constructed qualitative APS package set from PR `#709`. It must require the existing qualitative APS construction authority and must stop before handoff/export, APS dispatch, external export/download, connector/destination dispatch, provider/public URL generation, rendered UI work, source expansion, broad qualitative execution, package mutation, package supersession, or package reconstruction.

## Why This Comes Next

PR `#709` made the qualitative APS package set durable: exactly one reconciliation record, exactly three output package rows, and exactly three server-owned payload files. The next downstream behavior cannot be handoff/export or APS dispatch because the qualitative package set still lacks an approved package-review submit decision.

This pass must happen before qualitative APS handoff/export prepare. It must happen after package construction because package-review submit must validate immutable package ids, kinds, payload refs, payload hashes, construction basis hash, result-review authority, and package-review preview hash.

## Decision Vocabulary

Only these operator decisions are in scope:

| Decision | Meaning | Allowed next state |
| --- | --- | --- |
| `approved` | The constructed qualitative APS package set is accepted for later separately frozen downstream consideration. | `qual_aps_package_review_approved` |
| `changes_requested` | The package set is not accepted as-is and requires a separately frozen rebuild/amendment path before downstream action. | `qual_aps_package_review_changes_requested` |
| `rejected` | The package set is not accepted and must not proceed downstream. | `qual_aps_package_review_rejected` |
| `blocked` | The operator cannot decide because required evidence or authority is insufficient. | `qual_aps_package_review_blocked` |

The decision vocabulary is review disposition only. It is not a handoff command, export command, package rebuild command, source-expansion command, rerun command, result-review amendment, approved-plan correction, or mockup activation.

## Future Runtime Shape

A later implementation may include only:

- extending or reusing `POST /api/v1/layer3/package/review/submit` for `ENGINE_FAMILY_QUAL_APS_DOCUMENT`;
- response schema `layer3.qual_aps_package_review_submit.v1`;
- strict request DTO behavior with forbidden downstream/source/provider/connector/RAG/model/auth/UI fields;
- server revalidation of session, approved plan, selected pass run, preview id/hash, approved result review, qualitative output payload, package-review preview hash, construction basis hash, reconciliation record, output package ids, package kinds, payload refs, payload hashes, APS content document, chunks, material snapshot, analysis unit, and analysis set;
- exactly one package-review decision object in existing durable JSON-bearing state;
- deterministic idempotent retry handling for duplicate `client_request_id`;
- concurrency protection so duplicate or conflicting submit attempts cannot create divergent decision state;
- focused service/API tests and one bounded E2E extension from package construction through submit.

## Allowed Writes

Only these writes are admitted:

- one qualitative APS package-review decision object in `L3ReconciliationRecord.summary_json`;
- optional `L3Session.summary_json` pointer/index fields needed for existing readiness projections.

The implementation must not create new rows or files under this freeze.

## Forbidden Writes And Effects

The future implementation must not:

- create `L3ReconciliationRecord`, `L3OutputPackage`, `L3AnalysisPlan`, `L3PassRun`, `AnalysisRun`, `AnalysisArtifact`, connector, destination, provider, source-ingestion, RAG/vector, runtime snapshot, auth, delivery, signed-reference, or handoff/export rows;
- write, delete, rewrite, or replace package payload files;
- mutate `L3OutputPackage.payload_ref`, `L3OutputPackage.payload_hash`, existing package payload bodies, result-review state, qualitative execution output, approved plan state, selected pass state, source authority rows, or construction basis fields;
- update `L3OutputPackage.status` unless a separate freeze proves it is required;
- trigger handoff/export, APS dispatch, external export/download, connector/destination dispatch, provider/public URL generation, package mutation, package reconstruction, package supersession, source expansion, RAG/vector retrieval, hidden LLM planning, full mockup activation, rendered UI behavior, theme behavior, or auth/security behavior.

## Positive Invariants

The implementation-entry boundary is acceptable only if it proves:

- admission is limited to `ENGINE_FAMILY_QUAL_APS_DOCUMENT` and `single_aps_doc_qualitative_pass`;
- submit requires an existing PR `#709` qualitative package-construction commit;
- package construction source gate is `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE`;
- package kinds are exactly `canonical_internal`, `user_facing`, and `review_facing`;
- package ids, payload refs, payload hashes, construction basis hash, package-review preview hash, and result-review record ref match persisted server authority;
- package-review submit records one decision object only;
- duplicate `client_request_id` with identical authority is deterministic;
- duplicate `client_request_id` or later request with conflicting authority fails closed;
- package-review submit does not enable handoff/export or downstream behavior by itself;
- existing quantitative selected-pass, associated-cohort, package construction, package submit, handoff/export, APS dispatch, and external export/download behavior remains unchanged;
- rendered UI and theme behavior remain unchanged unless a separate UI freeze admits them.

## Required Tests For Runtime

Minimum implementation proof for a later runtime pass:

- successful API submit for one constructed standalone APS qualitative package set;
- bounded E2E extension from package construction through submit, stopping before handoff/export;
- missing package construction fails closed;
- partial package rows or missing payload refs/hashes fail closed;
- stale preview id/hash, result-review record ref, package-review preview hash, construction basis hash, reconciliation id, package ids, package kinds, payload refs, or payload hashes fail closed;
- non-approved result review fails closed;
- invalid decision or missing notes for `changes_requested`, `rejected`, or `blocked` fails closed;
- forbidden source/downstream/provider/connector/RAG/model/auth/UI fields fail closed before mutation;
- duplicate identical request is deterministic;
- conflicting duplicate request fails closed;
- no rows or files are created on submit;
- package payload refs, hashes, and files remain unchanged;
- handoff/export, APS dispatch, external export/download, connector/destination, provider URL, source expansion, RAG/vector, hidden LLM, full mockup, rendered UI, theme, and auth/security side effects remain absent;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

Browser proof is not required for a backend/API-only package-review submit implementation. Headed and headless Chrome proof, including relevant theme checks, becomes required if rendered `/review/layer3` or theme-visible behavior changes.

## Stop Conditions

Stop before implementation if the intended change requires:

- handoff/export, APS dispatch, external export/download, connector/destination dispatch, or provider/public URL behavior;
- package payload rewrite, package reconstruction, package mutation, package supersession, or replacement namespace behavior;
- new rows, schema/model/migration changes, or `L3OutputPackage.status` mutation;
- source expansion, ingestion, local upload, local-directory ingestion, web connector retrieval, or RAG/vector retrieval;
- qualitative cohort, broad qualitative, hybrid, comparative, cross-document, hidden LLM, prompt/model behavior, or external model calls;
- rendered UI controls, document-trace controls, destination controls, package editors, or theme-visible behavior without a separate UI freeze;
- auth/security behavior.
