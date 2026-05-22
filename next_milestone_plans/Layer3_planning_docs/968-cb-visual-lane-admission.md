# 968 - Candidate B Visual-Lane Admission Freeze

## Purpose

Freeze the smallest governed Candidate B visual-evidence admission decision that may be implemented after this document lands on current main.

This is not the implementation. It does not change `visual_lane_mode` behavior, does not change the Candidate B default PDF selector, does not weaken Candidate A, and does not collapse Candidate B bundle authority with Candidate B runtime authority.

## Current-main authority check

As of current main `5853e7e644f41eb28f2277b1177cd2b28983a008`, current main includes:

- Candidate B bundle bridge `candidate_b_bundle_curated_json_md_to_layer3_material_authority_v1`;
- Candidate B runtime bridge `candidate_b_runtime_source_to_layer3_material_authority_v1`;
- Candidate B default-promotion readiness audit `candidate_b_default_promotion_readiness_audit_v1`;
- Candidate B omitted-engine default selector for eligible PDF/corpus processing;
- readiness/bootstrap exposure for `candidate_b_default_promotion_selector_switch_admitted=true`;
- readiness/bootstrap exposure for scope `candidate_b_opendataloader_pdf_eligible_pdf_corpus_processing_only`.

Current main still does not admit Candidate B as a `visual_lane_mode`.

Current source authority:

- `backend/app/services/nrc_aps_document_processing.py` admits only `baseline` and `candidate_a_page_evidence_v1` in `_ADMITTED_VISUAL_LANE_MODES`;
- `backend/app/services/connectors_nrc_adams.py` admits only `baseline` and `candidate_a_page_evidence_v1` in `_APS_ADMITTED_VISUAL_LANE_MODES`;
- `backend/app/services/review_nrc_aps_runtime.py` exposes only `baseline` and `candidate_a_page_evidence_v1` as visible visual-lane modes;
- `backend/app/services/layer3_candidate_b_bundle_bridge.py` and `backend/app/services/layer3_candidate_b_runtime_bridge.py` report `candidate_b_visual_lane_mode_enabled=false`;
- the runtime bridge rejects Candidate B runtime evidence when metadata reports a non-baseline visual lane.

Therefore this document admits only a later implementation slice. It is the current-main admission decision required before runtime code may accept Candidate B as an explicit visual-evidence lane.

## Admitted future implementation slice

This document admits exactly one future implementation slice after merge:

- `candidate_b_visual_lane_mode_admission_v1`

The preferred admitted `visual_lane_mode` value is:

- `candidate_b_opendataloader_page_evidence_v1`

This value is intentionally specific:

- `candidate_b` ties the mode to the Candidate B path;
- `opendataloader` ties the mode to the admitted OpenDataLoader PDF processing family;
- `page_evidence` states that the mode is a visual/page evidence lane, not a replacement processing engine.

The implementation must keep Candidate B `visual_lane_mode` authority separate from `document_processing_engine="candidate_b_opendataloader_pdf"`.

## Relationship to existing selectors

The implementation must preserve these relationships:

- `baseline` remains the default visual lane and rollback posture.
- `candidate_a_page_evidence_v1` remains the admitted Candidate A visual-lane variant with unchanged semantics.
- `document_processing_engine="candidate_b_opendataloader_pdf"` remains the Candidate B corpus-processing engine and the omitted-engine default only for eligible PDF/corpus processing.
- `visual_lane_mode="candidate_b_opendataloader_page_evidence_v1"` may request Candidate B visual/page evidence only after the later implementation is landed.
- Candidate B bundle-backed evidence and Candidate B runtime-source evidence remain distinct authority families.
- Candidate B visual-lane evidence may reference Candidate B processing-engine outputs, but it must not silently reinterpret every Candidate B runtime as a visual-lane run.
- Layer 3 material-analysis authority must continue to flow through governed Candidate B bridge receipts, not raw broad source expansion.

## Artifact family classification

Candidate B artifacts are not all the same kind of Layer 3 input. The later implementation must classify them by downstream role.

### Material-analysis payloads

These artifacts may be admitted as Layer 3 text/material-analysis payloads when they match the selected bridge family and hash/receipt requirements:

- raw JSON selected by the Candidate B bridge;
- raw Markdown selected by the Candidate B bridge;
- curated JSON/Markdown material subsets;
- normalized text/material records produced by the runtime bridge;
- selected compare/proof summary fields when explicitly included in a bridge receipt.

PDFs, annotated PDFs, extracted images, and visual derivatives are not material-text payloads by default. They require a separate PDF/image material-ingestion slice before they may be treated as analysis text input.

### Visual and page evidence

These artifacts are retained visual/page evidence where present:

- source PDFs;
- annotated PDFs;
- page layout evidence;
- page references;
- bounding boxes and region metadata;
- extracted images;
- visual derivative metadata;
- Candidate B page-level trace outputs.

These artifacts support inspection, visual comparison, page provenance, and operator confidence. They must not be described as permanently excluded merely because they are outside the first text-material subset.

### Provenance and audit artifacts

These artifacts are provenance/audit authority:

- `compare.json`;
- `proof.json`;
- `retain.json`;
- `baseline-summary.json`;
- bundle file manifests;
- bundle raw-root hashes;
- admitted subset hashes;
- Candidate B bundle bridge receipts;
- Candidate B runtime bridge receipts;
- runtime trace manifests;
- validation summaries;
- readiness audit outputs.

### Product and inspection artifacts

These artifacts are product/inspection artifacts:

- source PDFs retained for operator inspection;
- annotated PDFs retained for operator inspection;
- raw Candidate B JSON and Markdown;
- compare workbench artifacts;
- rendered inspection packages;
- trace tabs and page-evidence views;
- downstream package review surfaces that expose redacted Candidate B provenance.

### Delivery artifacts

These artifacts are delivery artifacts only when separately admitted by the Layer 3 package, handoff, export, delivery, or provider-private redacted lifecycle:

- Layer 3 handoff/export packages;
- same-origin delivery artifacts;
- provider-private redacted delivery/use artifacts;
- internal webhook receipt payloads;
- packaged inspection PDFs;
- packaged JSON/Markdown material artifacts;
- redacted provenance summaries.

Delivery authority must remain server-owned. The visual-lane admission slice must not add provider object writes, public URLs, connector dispatch, credentials exposure, browser-storage authority, or frontend-only durable authority.

## Required implementation behavior

The later `candidate_b_visual_lane_mode_admission_v1` implementation must:

- add `candidate_b_opendataloader_page_evidence_v1` only to the exact current-main visual-lane allowlists that need to recognize it;
- keep `baseline` as the fallback for omitted, invalid, or unsupported visual-lane inputs unless a request explicitly selects an admitted non-baseline mode;
- keep Candidate A recognition unchanged;
- require explicit Candidate B visual-lane selection;
- keep Candidate B processing-engine selection and Candidate B visual-lane selection independently visible in runtime metadata;
- preserve Candidate B bundle and runtime authority separation;
- preserve PDFs, annotated PDFs, extracted images, and page evidence as retained evidence/product artifacts where present;
- prevent PDFs/images from becoming Layer 3 text-material payloads unless a separate material-ingestion slice admits them;
- fail closed when Candidate B page evidence, trace metadata, or retained artifact manifests are missing, stale, or hash-mismatched;
- expose operator-visible status/provenance that distinguishes processing engine, visual lane, bridge receipt, artifact family, and retained evidence.

## Required tests and proof

The implementation must add focused tests proving:

- omitted `visual_lane_mode` still resolves to `baseline`;
- invalid `visual_lane_mode` still fails closed to `baseline`;
- `candidate_a_page_evidence_v1` behavior and visible classification remain unchanged;
- `candidate_b_opendataloader_page_evidence_v1` is accepted only as an explicit visual-lane selection;
- Candidate B document-processing-engine default behavior for eligible PDFs remains unchanged;
- explicit `document_processing_engine="baseline"` remains a rollback path;
- Candidate B bundle and runtime bridges keep distinct receipt/hash authority;
- PDFs and annotated PDFs are retained as visual/product/inspection artifacts where present;
- PDFs, annotated PDFs, and extracted images are not ingested as Layer 3 text-material payloads without a separate admitted slice;
- runtime visibility reports Candidate B processing-engine authority separately from Candidate B visual-lane authority;
- downstream Layer 3 proof still covers material preview, Gate B, analysis, package/review, handoff/export, delivery/internal-webhook/provider-private-redacted paths, and final operator inspection for the selected Candidate B-derived material family;
- no broad source expansion, RAG/vector/model runtime, connector dispatch, provider object writes, auth/security change, full mockup activation, browser-storage authority, or frontend-only durable authority is introduced.

## Stop conditions

Implementation must stop if:

- current main no longer preserves `baseline` visual-lane fallback;
- Candidate A recognition cannot be preserved exactly;
- Candidate B default PDF selector evidence is stale or contradicted;
- Candidate B bundle/runtime evidence cannot be kept distinct;
- the proposed visual-lane mode would force PDFs, annotated PDFs, images, or arbitrary binaries into Layer 3 text-material analysis;
- retained Candidate B visual/product artifacts cannot be represented without raw local path, raw provider URL, credential, or frontend-only authority exposure;
- proof would depend on historical reports without current artifact roots or selected receipts;
- implementation would require broad runtime DB expansion, arbitrary source expansion, provider object writes, connector dispatch, RAG/vector/model runtime, auth/security changes, or full mockup activation.

## Excluded behavior

The implementation must not:

- change the Candidate B eligible-PDF default selector scope;
- make Candidate B default beyond eligible PDF/corpus processing;
- make Candidate B visual lane implicit;
- change baseline parser behavior for non-PDF content;
- make Candidate A default;
- change Candidate A PageEvidence semantics;
- collapse Candidate B bundle and runtime authorities;
- ingest arbitrary PDFs/images into Layer 3 text-material analysis;
- add new source ingestion families to Layer 3;
- add provider object writes;
- add connector dispatch;
- add RAG/vector/model runtime;
- add auth/security behavior;
- add browser-storage authority;
- add frontend-only durable authority;
- activate the full mockup.

## Next exact posture

After this freeze is merged, the next exact posture is:

`implement_candidate_b_visual_lane_mode_admission_v1`
