# Layer 3 Post-709 Roadmap Freeze

Status: current-main planning/control reference after PR `#709`.

This document is the referenceable roadmap for the remaining bounded Layer 3 work after qualitative APS package construction became live. It does not implement or admit any new runtime behavior. It exists to keep intended future passes scoped, ordered, and auditable before any new implementation branch starts.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current-main anchor: PR `#709`, merge commit `aaf524a646946190584cf69822cde58834846b75`
- latest live qualitative APS boundary: `qual_aps_package_construction_commit_entry`
- latest live qualitative APS response schema: `layer3.qual_aps_package_construction_commit.v1`
- governing construction docs: `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`
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
- qualitative APS package construction commit, creating exactly one reconciliation record, exactly three package rows, and exactly three server-owned package payload files.

Current main still does not admit qualitative APS package-review submit, qualitative APS handoff/export, qualitative APS APS dispatch, qualitative APS external export/download, rendered qualitative package controls, provider/public URLs, real connector/destination dispatch, raw ingestion, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, source adapter registry expansion, broad qualitative/hybrid execution, hidden LLM planning, full mockup activation, auth/security behavior changes, or broad package mutation/reconstruction.

## Required Ordering

Future work must proceed in this order unless a later live audit proves a different blocker:

1. qualitative APS package-review submit freeze and contract;
2. qualitative APS package-review submit runtime;
3. qualitative APS handoff/export prepare freeze and contract;
4. qualitative APS handoff/export prepare runtime;
5. qualitative APS APS handoff dispatch freeze and contract;
6. qualitative APS APS handoff dispatch runtime;
7. qualitative APS external export/download prepare/deliver freeze and contract;
8. qualitative APS external export/download prepare/deliver runtime;
9. rendered qualitative APS package/downstream UI freeze;
10. rendered qualitative APS package/downstream UI runtime, including theme proof;
11. source-breadth freeze before any ingestion/source-adapter expansion;
12. raw ingestion implementation only after source-breadth freeze;
13. broader qualitative, hybrid, RAG/vector, and cross-document execution freezes before runtime work;
14. output taxonomy and package lifecycle expansion freezes before package mutation/reconstruction work;
15. connector/destination dispatch and provider/public URL freezes before any external delivery expansion;
16. browser/full mockup activation freeze before any mockup-derived UI activation;
17. auth/security hardening freeze before behavior changes in authorization, tenancy, credentials, or public access;
18. CI/performance/observability hardening once the admitted runtime path is broad enough to stress runtime cost or audit trace completeness.

## Future Pass Specifications

### 1. Qualitative APS Package-Review Submit Freeze

- goal: freeze exactly one operator submit/approval decision over the already constructed qualitative APS package set.
- current blocker: submit is intentionally blocked with `qualitative_aps_package_review_submit_not_admitted`.
- implementation-entry freeze required: yes.
- likely files: new docs `143`/`144`, `105_deferred-gates.md`, `README_LAYER3_PHASE1A_PACK.md`, progress/proof manifests.
- required tests: no runtime tests unless a later implementation pass starts; the freeze must specify request fields, response fields, stale authority, idempotency, concurrency, and negative invariants.
- negative invariants: no handoff/export, APS dispatch, external export/download, connector/destination dispatch, provider/public URL, source expansion, RAG/vector, package mutation, UI, theme, auth/security, model/migration, or hidden LLM behavior.
- priority: P0 because every qualitative APS downstream path requires an approved package-review decision.

### 2. Qualitative APS Package-Review Submit Runtime

- goal: implement only the frozen submit decision over the constructed qualitative APS package set.
- current blocker: no dedicated submit freeze/contract exists yet.
- implementation-entry freeze required: yes, from pass 1.
- likely files: `backend/app/services/layer3_workbench.py`, package state/submit helpers, `backend/app/api/layer3.py`, `backend/tests/test_layer3_bounded_e2e.py`, `backend/tests/test_layer3_qual_aps_execution.py`, progress checker, progress/proof manifests.
- required tests: API success; stale package ids/hashes fail closed; duplicate client request behavior; no row/file mutation beyond submit state; bounded E2E reaches submit and stops.
- negative invariants: no handoff/export state, APS dispatch, external export/download, connector/destination dispatch, provider/public URL, source/RAG expansion, package mutation/reconstruction, rendered UI, theme behavior, auth/security, or hidden LLM behavior.
- priority: P0.

### 3. Qualitative APS Handoff/Export Prepare Freeze

- goal: freeze a prepare-only internal handoff/export envelope after qualitative APS package-review submit approval.
- current blocker: no qualitative APS package-review submit authority exists yet.
- implementation-entry freeze required: yes.
- likely files: new planning docs, `105_deferred-gates.md`, README/progress/proof metadata.
- required tests: later runtime must prove prepare-only state and no physical export, APS dispatch, external download, connector dispatch, provider URL, or package rewrite.
- negative invariants: no downstream dispatch, no external files unless explicitly frozen, no package mutation, no source/RAG expansion, no UI unless separately frozen.
- priority: P1, after submit.

### 4. Qualitative APS Handoff/Export Prepare Runtime

- goal: implement only the prepared internal envelope for qualitative APS package-review-approved packages.
- current blocker: pass 3 freeze and pass 2 runtime.
- implementation-entry freeze required: yes.
- likely files: `backend/app/services/layer3_workbench.py`, handoff/export response helpers, API DTOs, bounded E2E, qualitative APS tests, checker/proof metadata.
- required tests: prepare success; stale submit/package authority fail closed; no APS dispatch/external export; no package payload rewrite.
- negative invariants: no APS dispatch, external export/download, connector/destination dispatch, provider/public URL, source/RAG expansion, UI/theme change, auth/security, hidden LLM.
- priority: P1.

### 5. Qualitative APS APS Handoff Dispatch Freeze

- goal: freeze exactly one APS dispatch mode from a prepared qualitative APS handoff/export envelope.
- current blocker: qualitative APS handoff/export prepare is not live.
- implementation-entry freeze required: yes.
- likely files: new planning docs and progress/proof metadata.
- required tests: later runtime must prove dispatch authority, bundle identity, provenance, idempotency, fail-closed stale package/prepare state, and absence of real connector/destination behavior.
- negative invariants: no generic connector dispatch, provider URL, external download delivery, package mutation, source/RAG expansion, UI unless separately frozen.
- priority: P2.

### 6. Qualitative APS APS Handoff Dispatch Runtime

- goal: implement only the frozen APS handoff dispatch for qualitative APS packages.
- current blocker: pass 5 freeze and pass 4 runtime.
- implementation-entry freeze required: yes.
- likely files: APS handoff owner service, workbench route logic, API DTOs, bounded E2E, qualitative APS tests, checker/proof metadata.
- required tests: dispatch success; stale/malformed bundle authority fail closed; no connector/destination/provider behavior; no extra reconciliation/package rows outside admitted dispatch state.
- negative invariants: no external export/download delivery, connector/destination dispatch, provider URL, source/RAG expansion, package mutation, UI/theme change unless separately frozen.
- priority: P2.

### 7. Qualitative APS External Export/Download Freeze And Runtime

- goal: freeze and then implement same-origin prepare/deliver behavior for qualitative APS after exact APS dispatch authority.
- current blocker: qualitative APS APS dispatch is not live.
- implementation-entry freeze required: yes.
- likely files: external export/download contract/response helpers, workbench/API DTOs, bounded E2E, qualitative APS tests, checker/proof metadata.
- required tests: readiness, delivery, malformed token/payload fail-closed, same-origin artifact hash validation, no provider/public URL, no connector/destination dispatch.
- negative invariants: no provider/public URLs, no external object-store ACL, no destination write, no package mutation, no UI/theme change unless separately frozen.
- priority: P2 after APS dispatch.

### 8. Rendered Qualitative APS UI Freeze And Runtime

- goal: decide and implement only the rendered controls needed for already-live qualitative APS backend/API steps.
- current blocker: no dedicated rendered UI freeze exists after qualitative package construction.
- implementation-entry freeze required: yes.
- likely files: `backend/app/review_ui/static/layer3.html`, `backend/app/review_ui/static/layer3.js`, `e2e/layer3-workbench.spec.js`, `e2e/layer3-handoff.spec.js`, `e2e/layer3-helpers.js`, UI runbook docs.
- required tests: Playwright headed and headless Chrome for relevant existing themes; stable selectors; no frontend-only durable authority; API setup separated from rendered actions; theme persistence/isolation/responsive/focus behavior where visible controls are touched.
- negative invariants: no new source/ingestion controls, no manifest picker, no upload/directory controls, no RAG/vector/provider/connector controls unless separately frozen, no browser state as authority.
- priority: P3, after backend/API authority exists for the controls being rendered.

### 9. Source Breadth And Raw Ingestion

- goal: freeze then implement any source-class expansion beyond existing admitted authority rows.
- current blocker: doc `123` keeps source expansion blocked and seed-only bridge writes no rows/files.
- implementation-entry freeze required: yes.
- likely files: source services, API DTOs, migrations/models only if frozen, source-boundary tests, raw bridge tests, bounded E2E.
- required tests: upload/path traversal/hash/storage-root/authority-row behavior; fail-closed unsupported source families; no Layer 3 flow started by ingestion alone.
- negative invariants: no local-directory traversal, no arbitrary local paths, no web connector retrieval, no RAG/vector indexing, no connector dispatch, no provider URL, no hidden LLM.
- priority: P4, after bounded downstream qualitative path is proven or if source breadth becomes the explicit product blocker.

### 10. Broad Execution, RAG, Output Taxonomy, Package Lifecycle, External Delivery, Mockup, Security, And Observability

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
