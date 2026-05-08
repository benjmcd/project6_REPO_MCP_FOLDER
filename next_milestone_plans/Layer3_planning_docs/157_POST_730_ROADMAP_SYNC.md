# Layer 3 Post-730 Roadmap Sync

Status: current-main planning/control reference after raw mixed rendered materialization controls became live.

This document is a roadmap and scope-control sync only. It does not add or admit route, DTO, service, model, migration, UI, source, ingestion, package, connector, provider, RAG/vector, mockup, hidden LLM, or auth/security behavior by itself.

## Authority Snapshot

- authoritative remote: `project6-origin/main`
- current-main anchor: PR `#730`, merge commit `ec160cb3e5b829bb314498131a149b206378c3f7`
- latest raw mixed rendered mode: `raw_mixed_server_owned_manifest_ref_ui_entry`
- governing source-breadth freeze: `153_SOURCE_BREADTH_FREEZE.md`
- governing raw materialization runtime contract: `154_RAW_INGESTION_MATERIALIZATION_FREEZE.md`
- governing rendered raw mixed UI docs: `155_RAW_MIXED_RENDERED_UI_FREEZE.md` and `156_RAW_MIXED_RENDERED_UI_CONTRACT.md`
- broader deferred-gate control: `105_deferred-gates.md`
- proof/progress surfaces: `layer3_progress_board.md`, `layer3_progress_manifest.json`, `layer3_workbench_proof_manifest.json`, and `tools/l3-progress-check.py`

Live source, tests, routes, models, migrations, and checker behavior outrank this document. This document must not be used as proof that future work is live.

## Current Main Boundary

Current main admits these bounded Layer 3 paths:

- associated-cohort `dataset_version` API E2E through execution, package review/commit/submit, handoff/export prepare, APS handoff dispatch where companion APS provenance is admitted, external export/download prepare, and same-origin delivery;
- seed-only raw mixed bridge setup through `POST /api/v1/layer3/source/mixed-corpus/seed`, reading a hash-checked server-owned manifest and existing source authority rows while writing no DB rows or files;
- raw mixed source-authority materialization through `POST /api/v1/layer3/source/mixed-corpus/materialize`, creating deterministic admitted `dataset_version` and `aps_content_document` source-authority plus required backing authority rows (`Dataset`, `DatasetVersion`, `VariableDefinition`, `DatasetRow`, `VariableProfile`, `DatasetSourceProvenance`, `ConnectorRun`, `ConnectorRunTarget`, `ApsContentDocument`, `ApsContentChunk`, and `ApsContentLinkage`) from server-owned, hash-checked refs, writing no files, and starting no Layer 3 flow;
- bounded API E2E consumption of materialization response IDs through the existing associated-cohort path to same-origin external export/download delivery;
- rendered `/review/layer3` API-setup smoke proving materialized IDs can be consumed through existing rendered source/material/Gate B/Gate C/plan approval controls;
- rendered `/review/layer3` raw mixed server-owned manifest controls that call only the materialization route, refresh candidates, select only returned IDs, and continue through existing rendered source/material/Gate B/Gate C/plan approval controls;
- standalone `aps_content_document` qualitative execution through result review;
- qualitative APS package preview, construction, submit, handoff/export prepare, APS handoff dispatch, external export/download prepare, and same-origin delivery for the exact admitted qualitative APS authority chain;
- rendered qualitative APS downstream UI over existing controls through external export/download prepare where server response state admits it.

Current main still does not admit local upload, local-directory ingestion, web connector retrieval, arbitrary local path input, broad source adapter registry behavior, source-family expansion beyond `dataset_version` and `aps_content_document`, RAG/vector retrieval or indexing, broad qualitative/hybrid execution, provider/public URLs, real connector/destination dispatch, package mutation/reconstruction beyond already admitted package commit behavior, full mockup activation, hidden LLM planning, auth/security behavior changes, model/migration expansion for source breadth, or frontend-only durable authority.

## Completed Source And UI Sequence

The post-source-breadth chain is now:

1. `153_SOURCE_BREADTH_FREEZE.md` froze source breadth to `current_admitted_classes_with_server_owned_raw_materialization_only`.
2. `154_RAW_INGESTION_MATERIALIZATION_FREEZE.md` froze `raw_mixed_existing_source_materialization_entry`.
3. The raw materialization runtime made that boundary live through the existing admitted source families.
4. The materialization bounded API E2E proved returned IDs can drive the existing associated-cohort path.
5. The rendered UI smoke proved API-created materialized IDs can be consumed by existing `/review/layer3` controls.
6. `155_RAW_MIXED_RENDERED_UI_FREEZE.md` and `156_RAW_MIXED_RENDERED_UI_CONTRACT.md` now govern the live rendered server-owned manifest-ref controls from PR `#730`.

This sequence is not raw local ingestion, not a source adapter registry, not a connector/web fetch, and not RAG/vector activation.

## Next Pass Order

Future work should proceed in this order unless a later live audit proves a stricter blocker:

1. post-PR730 practical readiness audit for the live raw mixed rendered controls;
2. deeper rendered raw mixed UI path using the live controls and existing downstream controls only if the current UI can drive beyond plan approval without new controls;
3. source-breadth follow-up freeze only if a new source family is required; otherwise preserve the current admitted classes;
4. raw ingestion implementation freeze for any non-manifest server-owned ingestion behavior;
5. broad qualitative/hybrid/RAG/vector freeze before runtime work;
6. output taxonomy and package lifecycle freeze before package mutation/reconstruction work;
7. connector/destination dispatch and provider/public URL freezes before external delivery expansion;
8. browser/full mockup activation freeze before mockup-derived UI activation;
9. auth/security freeze before authorization, tenancy, credential, or public-access behavior changes;
10. CI/performance/observability hardening once runtime breadth or audit trace volume warrants it.

## Immediate Candidate Passes

### 1. Post-PR730 Practical Readiness Audit

- goal: verify current-main runtime, manual runbook implications, selectors, themes, and proof claims after PR `#730`.
- current blocker: no blocker; this is the safest next check after a visible UI change.
- implementation-entry freeze needed: no, report-only or docs-only.
- likely files: rendered UI static files, Playwright specs, browser harness, docs `155`/`156`, progress/proof manifests, `tools/l3-progress-check.py`.
- required tests: progress checker, page shell test, headless and headed Chromium raw mixed rendered smoke, optional full Layer 3 UI spec if feasible.
- negative invariants: no production backend changes, no new UI controls, no source/provider/connector/RAG/mockup/auth expansion.
- priority: P0.

### 2. Deeper Rendered Raw Mixed Downstream Path

- goal: prove the live raw mixed rendered controls can continue through existing rendered execution/package/handoff/export controls as far as current main genuinely supports.
- current blocker: current PR `#730` proof intentionally stops at rendered plan approval.
- implementation-entry freeze needed: no if test-only and existing controls are sufficient; yes if new controls or behavior are required.
- likely files: `e2e/layer3-workbench.spec.js`, `e2e/layer3-handoff.spec.js`, `e2e/layer3-helpers.js`, possibly static UI tests only if selectors need proof.
- required tests: one focused Playwright flow using API/harness setup only for server-owned manifest files, then rendered actions only after materialization.
- negative invariants: no new backend route/DTO/service/model/migration, no new source ingestion controls, no provider/public URLs, no real connector dispatch, no package mutation, no hidden LLM, no frontend-only durable authority.
- priority: P1 after practical readiness audit.

### 3. Source-Family Expansion Freeze

- goal: decide whether any source family beyond `dataset_version` and `aps_content_document` is actually needed.
- current blocker: no repo-proven product requirement or authority contract for a third family.
- implementation-entry freeze needed: yes.
- likely files: planning docs, source boundary tests, progress/proof manifests, checker.
- required tests: fail-closed unsupported family proof and explicit authority contract tests for the selected family before runtime.
- negative invariants: no generic adapter registry, no arbitrary local path, no web/RAG/provider/connector behavior by implication.
- priority: P2 only after current admitted-class UI/API posture is audited.

### 4. Broad Runtime Expansion Categories

- goal: separately freeze broad qualitative/hybrid/RAG, package lifecycle, connector/provider delivery, mockup, auth/security, and observability work.
- current blocker: each category remains explicitly deferred.
- implementation-entry freeze needed: yes for each category.
- likely files: category-specific services, tests, docs/proof manifests, and models/migrations only after schema freeze.
- required tests: success and fail-closed category proofs plus regression proof for current bounded paths.
- negative invariants: do not combine source expansion, RAG/vector, package mutation, connector/provider, mockup, or auth/security in one unbounded pass.
- priority: P3+ until narrower readiness and current admitted-class path proof are settled.

## Stop Conditions

Stop before implementation if the proposed next pass requires:

- accepting arbitrary local paths, file bytes, local uploads, or directory inputs;
- fetching web connector or external URL content;
- creating a source adapter registry;
- adding or changing models/migrations without a schema freeze;
- starting a Layer 3 flow inside source seeding or materialization;
- adding provider/public URLs, signed public delivery, connector/destination dispatch, RAG/vector, mockup, hidden LLM, or auth/security behavior;
- adding rendered controls outside docs `155` and `156` without a new UI/theme freeze.

## Acceptance Criteria

This roadmap sync is accepted only when:

- this file exists and names PR `#730`, merge commit `ec160cb3e5b829bb314498131a149b206378c3f7`, and `raw_mixed_server_owned_manifest_ref_ui_entry`;
- progress/proof manifests and the progress board reference this as a planning/control roadmap sync;
- `tools/l3-progress-check.py` guards this file and the current-main references;
- `python .\tools\l3-progress-check.py` passes;
- `git diff --check` passes.
