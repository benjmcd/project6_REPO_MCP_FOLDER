# Layer 3 Qualitative APS Post-Submit Roadmap Freeze

Status: current-main planning/control reference after qualitative APS APS handoff dispatch runtime.

This document is the referenceable roadmap for the remaining bounded Layer 3 work after qualitative APS package-review submit, qualitative APS handoff/export prepare, and qualitative APS APS handoff dispatch became live. It does not implement or admit any new runtime behavior by itself. It exists to keep intended future passes scoped, ordered, and auditable before any new implementation branch starts.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current-main anchor: qualitative APS APS handoff dispatch runtime branch
- latest live qualitative APS boundary: `qual_aps_aps_handoff_dispatch_entry`
- latest live qualitative APS response schema: `layer3.qual_aps_aps_handoff_dispatch.v1`
- governing construction docs: `140_QUAL_APS_PACKAGE_CONSTRUCTION_FREEZE.md` and `141_QUAL_APS_PACKAGE_CONSTRUCTION_CONTRACT.md`
- governing submit docs: `143_QUAL_APS_PACKAGE_REVIEW_SUBMIT_FREEZE.md` and `144_QUAL_APS_PACKAGE_REVIEW_SUBMIT_CONTRACT.md`
- governing handoff/export prepare docs: `145_QUAL_APS_HANDOFF_EXPORT_PREPARE_FREEZE.md` and `146_QUAL_APS_HANDOFF_EXPORT_PREPARE_CONTRACT.md`
- governing APS handoff dispatch runtime docs: `147_QUAL_APS_APS_HANDOFF_DISPATCH_FREEZE.md` and `148_QUAL_APS_APS_HANDOFF_DISPATCH_CONTRACT.md`
- governing qualitative APS external export/download freeze docs: `149_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_FREEZE.md` and `150_QUAL_APS_EXTERNAL_EXPORT_DOWNLOAD_CONTRACT.md`
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
- qualitative APS package-review submit over the constructed package set, recording the operator decision in existing summary state without creating rows or files;
- qualitative APS handoff/export prepare over the approved package-review submit state, recording one prepare-only decision/envelope in existing summary state without creating rows or files;
- qualitative APS APS handoff dispatch over the prepared qualitative envelope, creating exactly one APS evidence-bundle handoff package row, writing one server-owned APS bundle artifact, and recording dispatch state;
- qualitative APS external export/download prepare/deliver runtime, governed by docs `149` and `150`; this is qualitative APS external export/download prepare/deliver over the dispatched APS bundle, recording one readiness object and streaming the existing server-owned APS bundle artifact.

Current main still does not admit rendered qualitative package controls, provider/public URLs, real connector/destination dispatch, raw ingestion, local upload, local-directory ingestion, web connector retrieval, RAG/vector retrieval, source adapter registry expansion, broad qualitative/hybrid execution, hidden LLM planning, full mockup activation, auth/security behavior changes, or broad package mutation/reconstruction. The live qualitative APS external export/download path is limited to `qual_aps_external_export_download_prepare_deliver`.

## Required Ordering

Future work must proceed in this order unless a later live audit proves a different blocker:

1. rendered qualitative APS package/downstream UI freeze;
2. rendered qualitative APS package/downstream UI runtime, including theme proof;
3. source-breadth freeze before any ingestion/source-adapter expansion;
4. raw ingestion implementation only after source-breadth freeze;
5. broader qualitative, hybrid, RAG/vector, and cross-document execution freezes before runtime work;
6. output taxonomy and package lifecycle expansion freezes before package mutation/reconstruction work;
7. connector/destination dispatch and provider/public URL freezes before any external delivery expansion;
8. browser/full mockup activation freeze before any mockup-derived UI activation;
9. auth/security hardening freeze before behavior changes in authorization, tenancy, credentials, or public access;
10. CI/performance/observability hardening once the admitted runtime path is broad enough to stress runtime cost or audit trace completeness.

## Future Pass Specifications

### 1. Rendered Qualitative APS UI Freeze And Runtime

- goal: decide and implement only the rendered controls needed for already-live qualitative APS backend/API steps.
- current blocker: no dedicated rendered UI freeze exists after qualitative package construction/submit/prepare/dispatch.
- implementation-entry freeze required: yes.
- likely files: `backend/app/review_ui/static/layer3.html`, `backend/app/review_ui/static/layer3.js`, `e2e/layer3-workbench.spec.js`, `e2e/layer3-handoff.spec.js`, `e2e/layer3-helpers.js`, UI runbook docs.
- required tests: Playwright headed and headless Chrome for relevant existing themes; stable selectors; no frontend-only durable authority; API setup separated from rendered actions; theme persistence/isolation/responsive/focus behavior where visible controls are touched.
- negative invariants: no new source/ingestion controls, no manifest picker, no upload/directory controls, no RAG/vector/provider/connector controls unless separately frozen, no browser state as authority.
- priority: P3, after backend/API authority exists for the controls being rendered.

### 3. Source Breadth And Raw Ingestion

- goal: freeze then implement any source-class expansion beyond existing admitted authority rows.
- current blocker: doc `123` keeps source expansion blocked and seed-only bridge writes no rows/files.
- implementation-entry freeze required: yes.
- likely files: source services, API DTOs, migrations/models only if frozen, source-boundary tests, raw bridge tests, bounded E2E.
- required tests: upload/path traversal/hash/storage-root/authority-row behavior; fail-closed unsupported source families; no Layer 3 flow started by ingestion alone.
- negative invariants: no local-directory traversal, no arbitrary local paths, no web connector retrieval, no RAG/vector indexing, no connector dispatch, no provider URL, no hidden LLM.
- priority: P4, after bounded downstream qualitative path is proven or if source breadth becomes the explicit product blocker.

### 4. Broad Execution, RAG, Output Taxonomy, Package Lifecycle, External Delivery, Mockup, Security, And Observability

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
