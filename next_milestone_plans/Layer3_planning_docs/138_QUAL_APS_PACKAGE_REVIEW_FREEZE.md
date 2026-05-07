# Layer 3 Qualitative APS Package-Review Freeze

Status: current-main runtime boundary for `qual_aps_package_review_preview_only`.

This document governs the now-live read-only package-review preview boundary for one approved standalone APS content-document qualitative result through `POST /api/v1/layer3/package/review/preview`. A later bounded boundary, docs `140`/`141`, now admits qualitative APS package construction through `POST /api/v1/layer3/package/review/commit`. This preview document still does not admit package-review submit, handoff/export, APS handoff dispatch, external export/download, connector/destination dispatch, provider/public URLs, rendered UI controls, model/migration changes, source widening, broad qualitative/hybrid/RAG behavior, hidden LLM planning, full mockup activation, or authentication/security behavior.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current-main baseline for this freeze: PR `#703` merge commit `a813ac265fd8c737dc55cccf572eef79213b86a1`
- planning PR: `#704`
- implementation branch: `codex/l3-qual-aps-package-preview`
- latest upstream proof: PR `#702` standalone APS content-document qualitative API E2E proof
- execution owner: `backend/app/services/layer3_qual_aps_execution.py`
- package-preview route: `POST /api/v1/layer3/package/review/preview`
- package-preview schema: `layer3.qual_aps_package_review_preview.v1`
- package-construction successor: docs `140`/`141` and the live commit runtime now admit `qual_aps_package_construction_commit_entry` for `ENGINE_FAMILY_QUAL_APS_DOCUMENT`
- package-review-submit successor: docs `143`/`144` and the live submit runtime now admit `qual_aps_package_review_submit_entry` after construction authority exists
- proof surface: `backend/tests/test_layer3_bounded_e2e.py::test_layer3_standalone_aps_content_document_qualitative_e2e_reaches_read_only_package_preview`
- companion contract: `139_QUAL_APS_PACKAGE_REVIEW_CONTRACT.md`

Live source and tests outrank this planning document. This document freezes the narrow runtime boundary and the negative invariants around it.

## Current Live Boundary

Current main admits exactly one qualitative APS execution mode:

- `single_aps_doc_qualitative_pass`
- one committed Layer 3 session
- one `aps_content_document` material snapshot
- one qualitative `L3AnalysisUnit` and one matching single-document `L3AnalysisSet`
- one selected `L3PassRun`
- execution through `backend/app/services/layer3_qual_aps_execution.py`
- output payload metadata on the pass run, without `AnalysisRun`
- API result/status and result-review visibility through the existing Layer 3 workbench API path
- read-only package-review preview for the approved qualitative result through `layer3.qual_aps_package_review_preview.v1`

PR `#702` proved that path could be driven through result review. The preview runtime boundary advanced one step beyond that: package-review preview is inspectable/read-only. The later construction runtime now consumes that preview authority, and docs `143`/`144` now admit the bounded submit successor. Handoff/export, APS dispatch, external export/download, connector/destination dispatch, and provider/public URLs remain blocked.

## Decision

The selected runtime boundary is:

- selected mode: `qual_aps_package_review_preview_only`

This mode adds only read-only package-review preview/readiness for one approved standalone APS content-document qualitative result. Package construction is admitted only by the separate docs `140`/`141` runtime boundary; this preview mode itself must not construct packages or make downstream handoff/export behavior live.

The preview runtime stops at preview/readiness; the later separate construction boundary consumes the preview hash. This mirrors the earlier quantitative selected-pass progression: preview first, construction later, submit later, handoff/export later.

## Why This Comes Next

This lane comes before qualitative package construction because current main has no qualitative package shape, no qualitative package payload contract, no qualitative citation rendering contract, and no qualitative package owner compatibility proof.

This lane comes before handoff/export, APS dispatch, external export/download, connector/destination dispatch, and provider/public URLs because all of those require package or delivery authority that does not yet exist for qualitative APS output.

This lane comes before broader qualitative/hybrid/RAG work because broad qualitative expansion is still blocked by `124_QUAL_HYBRID_RAG_FREEZE.md`, while the standalone APS document path is already live and proof-covered.

This lane does not supersede source-breadth or raw-ingestion planning. Source expansion remains blocked; this package-review preview boundary uses only existing admitted `aps_content_document` authority.

## In-Scope Runtime

The runtime may include only:

- extending the existing `POST /api/v1/layer3/package/review/preview` path for qualitative APS preview;
- strict request DTO and forbidden-field guard if route-level request shape changes;
- server revalidation of session, plan, preview id/hash, pass run, qualitative execution output metadata, and approved result-review state;
- a read-only package compatibility projection for qualitative APS output;
- response-safe candidate package descriptors, not durable packages;
- deterministic preview hash or compatibility hash if useful for idempotent preview;
- focused API/service tests;
- progress-check/proof guard to preserve this boundary.

The runtime may read existing rows and artifacts:

- `L3Session`
- `L3AnalysisPlan`
- `L3PassRun`
- `L3MaterialSnapshot`
- `L3TypingRecord`
- `L3AnalysisUnit`
- `L3AnalysisSet`
- `ApsContentDocument`
- `ApsContentChunk`
- `ApsContentLinkage`
- qualitative APS output metadata/payload refs already produced by execution

The runtime may not write durable package or downstream state.

## Explicit Non-Goals

This freeze does not admit:

- `L3OutputPackage` rows;
- `L3ReconciliationRecord` rows;
- package payload file writes;
- package construction or commit;
- package-review submit decisions;
- package mutation, reconstruction, amendment, supersession, replacement artifact generation, or replacement namespace rows;
- handoff/export prepare;
- APS handoff dispatch;
- external export/download prepare, deliver, or signed reference behavior;
- connector run creation or destination writes;
- provider/public URL generation;
- new `AnalysisRun` rows for qualitative APS execution;
- `DatasetVersion` creation or conversion for APS chunks;
- RAG/vector retrieval;
- local upload, local-directory ingestion, web connector retrieval, or source adapter registry behavior;
- rendered package controls or document-trace UI changes;
- hidden LLM planning, prompt/model flags, or raw prompt traces;
- model/migration changes unless separately frozen;
- full mockup activation;
- authentication/security behavior.

## Positive Invariants

The runtime boundary is acceptable only if it proves:

- package preview admission is limited to `ENGINE_FAMILY_QUAL_APS_DOCUMENT` plus `single_aps_doc_qualitative_pass`;
- the result-review state is approved and belongs to the same session, plan, preview id/hash, pass run, source document, analysis unit, and analysis set;
- qualitative output metadata is readable and binds to content id, content contract id, chunking contract id, chunk ids, chunk hashes, material snapshot id, analysis unit id, and analysis set id;
- missing, stale, malformed, cross-session, wrong-source, wrong-modality, wrong-engine, non-approved, or mismatched authority fails closed;
- preview response marks downstream package construction, package-review submit, handoff/export, APS dispatch, external export/download, connector/destination dispatch, and provider/public URL behavior unavailable;
- no package rows, reconciliation rows, downstream state, provider URLs, connector runs, destination writes, source rows, schema rows, or package payload files are created;
- existing quantitative single-item and associated-cohort package preview behavior remains unchanged.

## Negative Invariants

The runtime boundary must prove absence of:

- broad qualitative, hybrid, RAG, vector, comparative, cross-document, or qualitative cohort execution;
- conversion of APS content into `DatasetVersion`;
- wrapped quantitative `run_analysis(..., dataset_version_id=...)` calls for qualitative APS output;
- package payload generation, mutation, or reconstruction;
- handoff/export, APS handoff, external export/download, connector/destination, or provider/public URL side effects;
- frontend-only durable authority;
- browser-supplied raw document text, local paths, provider paths, package bytes, connector ids, destination ids, prompt flags, or model flags;
- auth/security behavior changes.

## Runtime Proof Required

Minimum proof:

- service/API success for one approved standalone APS qualitative result-review preview;
- missing approved result review fails closed;
- wrong pass engine or wrong source shape fails closed;
- stale preview hash fails closed;
- mismatched content id, material snapshot id, analysis unit id, analysis set id, or output payload hash fails closed;
- forbidden package/handoff/export/source/provider/connector/RAG/model fields fail closed;
- existing quantitative package preview tests still pass;
- standalone APS qualitative E2E reaches read-only package preview and then the separate construction commit boundary;
- package-review submit is admitted only by the separate docs `143`/`144` boundary after construction authority exists;
- no DB row or file side effects beyond admitted read-only preview metadata, if any;
- `python .\tools\l3-progress-check.py`;
- `git diff --check`.

Browser proof is not required for a backend/API-only preview implementation. Headed and headless Chrome proof become required if rendered `/review/layer3`, document trace, or theme-visible behavior changes.

## Stop Conditions

Stop before implementation if the intended change requires:

- constructing packages;
- writing `L3OutputPackage` or `L3ReconciliationRecord`;
- writing package payload files;
- admitting handoff/export, APS dispatch, external export/download, provider/public URL, connector/destination, source expansion, RAG/vector, or UI controls;
- changing qualitative execution semantics;
- adding model/migration work without a separate schema freeze;
- relying on mockup state, browser state, planning prose, or PR title text as runtime authority.
