# Layer 3 Qualitative APS Package Construction Freeze

Status: current-main runtime boundary for `qual_aps_package_construction_commit_entry`.

This document governs the bounded runtime tranche after the live read-only `qual_aps_package_review_preview_only` boundary. It admits only package-construction commit for one approved standalone APS content-document qualitative result that already passed package-review preview. It does not admit package-review submit, handoff/export, APS handoff dispatch, external export/download, connector/destination dispatch, provider/public URLs, rendered UI controls, source expansion, broad qualitative/hybrid/RAG behavior, hidden LLM planning, full mockup activation, model/migration work beyond existing package rows, or authentication/security behavior.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current-main baseline for this freeze: PR `#707` merge commit `74624df4cbd1a000c1d47fea95a83aed0aa23949`
- implementation-entry branch: `codex/l3-qual-aps-package-construction-freeze`
- planning PR: `#708`
- implementation PR: `#709`
- implementation merge commit: `aaf524a646946190584cf69822cde58834846b75`
- predecessor runtime: `qual_aps_package_review_preview_only`
- predecessor docs: `138_QUAL_APS_PACKAGE_REVIEW_FREEZE.md` and `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`
- predecessor runtime PR: `#706`
- predecessor review-debt closeout: `#707`
- package route family: `POST /api/v1/layer3/package/review/preview`, `POST /api/v1/layer3/package/review/commit`, and `POST /api/v1/layer3/package/review/submit`
- selected future route: `POST /api/v1/layer3/package/review/commit`
- selected future mode: `qual_aps_package_construction_commit_entry`
- selected future response schema: `layer3.qual_aps_package_construction_commit.v1`
- package kinds: `canonical_internal`, `user_facing`, `review_facing`
- live behavior: `backend/app/services/layer3_workbench.py` admits qualitative APS package construction through `layer3.qual_aps_package_construction_commit.v1`
- submit successor: docs `143`/`144` and the live submit runtime now admit `qual_aps_package_review_submit_entry` after construction
- companion contract: `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`
- next roadmap reference: `142_POST_709_ROADMAP_FREEZE.md`

Live source and tests outrank this planning document. This document now tracks the bounded runtime boundary only.

## Decision

The selected next runtime mode is:

- `qual_aps_package_construction_commit_entry`

The selected mode constructs the first durable qualitative APS package set from an already approved standalone APS qualitative result and an already available qualitative package-review preview. It creates exactly one reconciliation authority record and exactly three package rows for the candidate package kinds. It writes exactly the package payload files needed for those rows. It must stop before package-review submit and all downstream delivery behavior.

This is not package mutation, package supersession, connector dispatch, external export/download, provider URL generation, rendered UI work, source expansion, or broad qualitative execution.

## Why This Comes Next

PR `#702` proved the standalone APS qualitative path through result review. PR `#706` made read-only package-review preview live. PR `#707` kept package construction and submit fail-closed before this boundary. PR `#708` froze the construction entry. The current implementation now admits the first package-construction commit boundary and still stops before package-review submit.

This pass must come before package-review submit, handoff/export, APS dispatch, external export/download, connector/destination dispatch, and provider/public URL behavior because those depend on a durable package set that does not yet exist for qualitative APS output.

This pass must come after the preview boundary because package construction needs server-derived package-review preview authority, deterministic preview hash binding, qualitative output payload authority, and chunk/citation trace completeness checks.

## Runtime Shape

The implementation includes only:

- extending the existing `POST /api/v1/layer3/package/review/commit` route for `ENGINE_FAMILY_QUAL_APS_DOCUMENT`;
- a qualitative-specific response schema `layer3.qual_aps_package_construction_commit.v1`;
- strict request DTO behavior with forbidden downstream/source/provider/connector/model fields;
- server revalidation of session, plan, pass run, preview id/hash, approved result review, qualitative output payload, package-review preview hash, APS content document, chunks, material snapshot, analysis unit, and analysis set;
- deterministic package construction basis hashing;
- idempotent handling of duplicate `client_request_id`;
- concurrency protection around reconciliation and package row creation;
- package payload generation from existing qualitative APS output, chunk trace, and citation trace only;
- exactly one `L3ReconciliationRecord` for the constructed qualitative package set;
- exactly three `L3OutputPackage` rows for `canonical_internal`, `user_facing`, and `review_facing`;
- exactly the package payload files referenced by those rows;
- focused service/API tests and one bounded E2E extension from package-review preview through construction commit.

## Package Payload Boundary

The first qualitative APS package taxonomy is:

- `canonical_internal`: machine-readable package preserving qualitative output, source authority, chunk/citation trace, content contract ids, output hash, and package construction basis.
- `user_facing`: response-safe summary package suitable for non-authoritative operator review, without raw prompts, credentials, local paths, provider URLs, hidden model metadata, or editable package instructions.
- `review_facing`: reviewer/audit package preserving the qualitative result, cited APS chunks, trace ids, package basis hash, source authority ids, and negative capability markers.

The implementation must derive every payload from existing persisted state and the qualitative execution output artifact. It must not call an LLM, run RAG/vector retrieval, fetch connectors, read arbitrary local paths, or accept package bytes from the client.

## Allowed Writes

Only these writes are admitted:

- one `L3ReconciliationRecord` for the qualitative APS constructed package set;
- three `L3OutputPackage` rows, one for each admitted package kind;
- package payload files under the existing server-owned artifact/storage root;
- session/operator summary state only if needed to expose the same constructed package state through existing readiness surfaces.

All writes must be deterministic, idempotent, and bound to the same session, plan, pass run, preview, result review, output payload, material snapshot, analysis unit, analysis set, content id, content contract id, chunking contract id, chunk ids, and chunk hashes.

## Explicit Non-Goals

This freeze does not admit:

- package-review submit;
- handoff/export prepare;
- APS handoff dispatch;
- external export/download prepare, deliver, or signed reference behavior;
- connector run creation or destination writes;
- provider/public URL generation;
- package mutation, reconstruction, supersession, replacement package-set authority, replacement artifact generation, or namespace updates;
- qualitative cohort execution, broad qualitative execution, hybrid execution, comparative execution, cross-document synthesis, RAG/vector retrieval, hidden LLM planning, or prompt/model controls;
- raw ingestion, local upload, local-directory ingestion, web connector retrieval, source adapter registry behavior, or unbounded runtime DB source expansion;
- conversion of APS content into `DatasetVersion`;
- new `AnalysisRun` rows for qualitative APS execution;
- model/migration work beyond existing package/reconciliation tables unless a separate schema freeze proves it is required;
- rendered UI controls, document-trace controls, package editors, package mutation controls, destination controls, or theme-visible behavior changes;
- authentication/security behavior.

## Positive Invariants

The implementation-entry boundary is acceptable only if it proves:

- admission is limited to `ENGINE_FAMILY_QUAL_APS_DOCUMENT` and `single_aps_doc_qualitative_pass`;
- package construction requires approved result-review state and available qualitative package-review preview state;
- `package_review_preview_hash` binds to the same package candidate basis used at preview;
- package construction basis binds source, execution output, result review, chunk/citation trace, package kinds, and payload hashes;
- the package payloads are server-derived and deterministic;
- duplicate `client_request_id` returns the existing constructed package set or fails closed without duplicate rows/files;
- concurrent duplicate construction attempts cannot create duplicate reconciliation/package rows or divergent payload files;
- package-review submit is admitted only by the separate docs `143`/`144` boundary and must preserve this construction authority;
- downstream handoff/export, APS dispatch, external export/download, connector/destination dispatch, provider/public URL, source expansion, RAG/vector, hidden LLM, mockup, UI, and auth/security behavior remains unavailable;
- existing quantitative selected-pass and associated-cohort package construction behavior remains unchanged.

## Required Tests

Minimum implementation proof for a later runtime pass:

- service/API success for one approved standalone APS qualitative package construction commit;
- bounded E2E extension from package-review preview through construction commit;
- missing approved result review fails closed;
- missing or stale package-review preview hash fails closed;
- stale preview id/hash fails closed;
- stale output payload ref/hash fails closed;
- mismatched content id, material snapshot id, analysis unit id, analysis set id, chunk ids, or chunk hashes fail closed;
- wrong engine family and wrong source shape fail closed without changing quantitative package behavior;
- forbidden source/downstream/provider/connector/RAG/model/auth/UI fields fail closed before mutation;
- duplicate `client_request_id` behavior is deterministic;
- concurrency proof for duplicate construction requests;
- exactly one reconciliation row and exactly three output package rows are created on success;
- package payload files exist, hashes match rows, and no extra files are written;
- no package-review submit, handoff/export, APS dispatch, external export/download, connector/destination, provider URL, source, RAG/vector, model/migration, hidden LLM, full mockup, rendered UI, theme, or auth/security side effects occur;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

Browser proof is not required for a backend/API-only package construction implementation. Headed and headless Chrome proof, including relevant theme checks, becomes required if rendered `/review/layer3`, document trace, or theme-visible behavior changes.

## Stop Conditions

Stop before implementation if the intended change requires:

- package-review submit or any downstream delivery state;
- package mutation/reconstruction rather than first construction;
- connector/destination dispatch;
- provider/public URL behavior;
- source expansion or ingestion;
- RAG/vector retrieval or hidden LLM planning;
- rendered UI controls or theme-visible behavior without a separate UI freeze;
- auth/security hardening;
- schema/model/migration changes not explicitly frozen for this package construction boundary.
