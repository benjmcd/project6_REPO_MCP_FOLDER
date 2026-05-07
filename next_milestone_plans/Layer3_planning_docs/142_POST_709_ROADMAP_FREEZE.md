# Layer 3 Qualitative APS Post-Submit Roadmap Freeze

Status: current-main planning/control reference after qualitative APS handoff/export prepare freeze.

This document is the referenceable roadmap for the remaining bounded Layer 3 work after qualitative APS package-review submit became live and the qualitative APS handoff/export prepare boundary was frozen. It does not implement or admit any new runtime behavior by itself. It exists to keep intended future passes scoped, ordered, and auditable before any new implementation branch starts.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current-main anchor: qualitative APS package-review submit runtime branch
- latest live qualitative APS boundary: `qual_aps_package_review_submit_entry`
- latest live qualitative APS response schema: `layer3.qual_aps_package_review_submit.v1`
- governing construction docs: `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`
- governing submit docs: `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md`
- governing handoff/export prepare docs: `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md` and `146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md`
- broader deferred-gate control: `105_deferred-gates.md`
- proof/progress surfaces: `layer3_progress_board.md`, `layer3_progress_manifest.json`, `layer3_workbench_proof_manifest.json`, and `tools/l3-progress-check.py`

Live source, tests, migrations, models, routes, and proof-checker behavior outrank this roadmap. This roadmap must not be used as proof that any future pass is live.

## Current Main Boundary

Current main admits:

- deterministic `dataset_version` bounded API E2E through same-origin external export/download delivery where the admitted quantitative/mixed provenance path supports it;
- seed-only raw mixed bridge setup through existing admitted `dataset_version` and `aps_content_document` authority rows;
- rendered `/review/layer3` proof through the admitted dataset-version Gate B, Gate C, plan preview, and plan approval UI path after API setup;
- standalone `aps_content_document` qualitative execution through result review for `single_aps_doc_qualitative_pass`;
- read-only qualitative APS package-review preview;
- qualitative APS package construction commit, creating exactly one reconciliation record, exactly three package rows, and exactly three server-owned package payload files;
- qualitative APS package-review submit over the constructed package set, recording the operator decision in existing summary state without creating rows or files.

Current main still does not admit qualitative APS handoff/export, qualitative APS APS dispatch, qualitative APS external export/download, rendered qualitative package controls, provider/public URLs, real connector/destination dispatch, raw ingestion, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, source adapter registry expansion, broad qualitative/hybrid execution, hidden LLM planning, full mockup activation, auth/security behavior changes, or broad package mutation/reconstruction.

## Required Ordering

Future work must proceed in this order unless a later live audit proves a different blocker:

1. qualitative APS handoff/export prepare runtime;
2. qualitative APS APS handoff dispatch freeze and contract;
3. qualitative APS APS handoff dispatch runtime;
4. qualitative APS external export/download prepare/deliver freeze and contract;
5. qualitative APS external export/download prepare/deliver runtime;
6. rendered qualitative APS package/downstream UI freeze;
7. rendered qualitative APS package/downstream UI runtime, including theme proof;
8. source-breadth freeze before any ingestion/source-adapter expansion;
9. raw ingestion implementation only after source-breadth freeze;
10. broader qualitative, hybrid, RAG/vector, and cross-document execution freezes before runtime work;
11. output taxonomy and package lifecycle expansion freezes before package mutation/reconstruction work;
12. connector/destination dispatch and provider/public URL freezes before any external delivery expansion;
13. browser/full mockup activation freeze before any mockup-derived UI activation;
14. auth/security hardening freeze before behavior changes in authorization, tenancy, credentials, or public access;
15. CI/performance/observability hardening once the admitted runtime path is broad enough to stress runtime cost or audit trace completeness.

## Future Pass Specifications

### 1. Qualitative APS Handoff/Export Prepare Runtime

- goal: implement only the prepared internal envelope for qualitative APS package-review-approved packages.
- current blocker: docs `145`/`146` are frozen and current main explicitly fails closed with `qualitative_aps_handoff_export_prepare_not_admitted`, but runtime has not yet implemented the qualitative APS authority branch.
- implementation-entry freeze required: yes.
- likely files: `backend/app/services/layer3_workbench.py`, handoff/export response helpers, API DTOs, bounded E2E, qualitative APS tests, checker/proof metadata.
- required tests: prepare success; stale submit/package authority fail closed; no APS dispatch/external export; no package payload rewrite.
- negative invariants: no APS dispatch, external export/download, connector/destination dispatch, provider/public URL, source/RAG expansion, UI/theme change, auth/security, hidden LLM.
- priority: P1.

### 2. Qualitative APS APS Handoff Dispatch Freeze

- goal: freeze exactly one APS dispatch mode from a prepared qualitative APS handoff/export envelope.
- current blocker: qualitative APS handoff/export prepare is not live.
- implementation-entry freeze required: yes.
- likely files: new planning docs and progress/proof metadata.
- required tests: later runtime must prove dispatch authority, bundle identity, provenance, idempotency, fail-closed stale package/prepare state, and absence of real connector/destination behavior.
- negative invariants: no generic connector dispatch, provider URL, external download delivery, package mutation, source/RAG expansion, UI unless separately frozen.
- priority: P2.

### 3. Qualitative APS APS Handoff Dispatch Runtime

- goal: implement only the frozen APS handoff dispatch for qualitative APS packages.
- current blocker: pass 2 freeze and pass 1 runtime.
- implementation-entry freeze required: yes.
- likely files: APS handoff owner service, workbench route logic, API DTOs, bounded E2E, qualitative APS tests, checker/proof metadata.
- required tests: dispatch success; stale/malformed bundle authority fail closed; no connector/destination/provider behavior; no extra reconciliation/package rows outside admitted dispatch state.
- negative invariants: no external export/download delivery, connector/destination dispatch, provider URL, source/RAG expansion, package mutation, UI/theme change unless separately frozen.
- priority: P2.

### 4. Qualitative APS External Export/Download Freeze And Runtime

- goal: freeze and then implement same-origin prepare/deliver behavior for qualitative APS after exact APS dispatch authority.
- current blocker: qualitative APS APS dispatch is not live.
- implementation-entry freeze required: yes.
- likely files: external export/download contract/response helpers, workbench/API DTOs, bounded E2E, qualitative APS tests, checker/proof metadata.
- required tests: readiness, delivery, malformed token/payload fail-closed, same-origin artifact hash validation, no provider/public URL, no connector/destination dispatch.
- negative invariants: no provider/public URLs, no external object-store ACL, no destination write, no package mutation, no UI/theme change unless separately frozen.
- priority: P2 after APS dispatch.

### 5. Rendered Qualitative APS UI Freeze And Runtime

- goal: decide and implement only the rendered controls needed for already-live qualitative APS backend/API steps.
- current blocker: no dedicated rendered UI freeze exists after qualitative package construction.
- implementation-entry freeze required: yes.
- likely files: `backend/app/review_ui/static/layer3.html`, `backend/app/review_ui/static/layer3.js`, `e2e/layer3-workbench.spec.js`, `e2e/layer3-handoff.spec.js`, `e2e/layer3-helpers.js`, UI runbook docs.
- required tests: Playwright headed and headless Chrome for relevant existing themes; stable selectors; no frontend-only durable authority; API setup separated from rendered actions; theme persistence/isolation/responsive/focus behavior where visible controls are touched.
- negative invariants: no new source/ingestion controls, no manifest picker, no upload/directory controls, no RAG/vector/provider/connector controls unless separately frozen, no browser state as authority.
- priority: P3, after backend/API authority exists for the controls being rendered.

### 6. Source Breadth And Raw Ingestion

- goal: freeze then implement any source-class expansion beyond existing admitted authority rows.
- current blocker: doc `123` keeps source expansion blocked and seed-only bridge writes no rows/files.
- implementation-entry freeze required: yes.
- likely files: source services, API DTOs, migrations/models only if frozen, source-boundary tests, raw bridge tests, bounded E2E.
- required tests: upload/path traversal/hash/storage-root/authority-row behavior; fail-closed unsupported source families; no Layer 3 flow started by ingestion alone.
- negative invariants: no local-directory traversal, no arbitrary local paths, no web connector retrieval, no RAG/vector indexing, no connector dispatch, no provider URL, no hidden LLM.
- priority: P4, after bounded downstream qualitative path is proven or if source breadth becomes the explicit product blocker.

### 7. Broad Execution, RAG, Output Taxonomy, Package Lifecycle, External Delivery, Mockup, Security, And Observability

- goal: each broad category must get its own freeze before implementation.
- current blocker: existing deferred docs keep these categories blocked.
- implementation-entry freeze required: yes for every category.
- likely files: category-specific services, tests, models/migrations only after schema freeze, UI only after UI/theme freeze.
- required tests: category-specific success and fail-closed proofs plus regression proof that current bounded paths remain unchanged.
- negative invariants: never combine broad execution, source expansion, package mutation, connector dispatch, provider URL, UI mockup activation, or auth/security in one unbounded pass.
- priority: P5 until narrower qualitative APS downstream path and source breadth decisions are settled.

## Cross-Cutting Rules

- Every runtime pass needs a current-main preflight and an implementation-entry freeze unless the pass is docs-only.
- Every implementation must separate seeding/setup from Layer 3 flow execution, API drivers from DB/artifact assertions, and browser state from durable authority.
- Every visible UI/theme change must include headed and headless Chrome proof for the relevant existing themes.
- Every manifest/index update must first classify whether the file is exhaustive or intentionally scoped.
- Every claim must be tied to live source/tests, proof checker behavior, progress/proof manifests, or a planning document with explicit planning-only status.
- Stop before code if the intended change requires an unfrozen category from the negative invariants above.
