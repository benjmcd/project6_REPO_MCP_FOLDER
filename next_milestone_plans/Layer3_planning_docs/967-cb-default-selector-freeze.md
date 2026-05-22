# 967 - Candidate B Default Selector Freeze

## Purpose

Freeze the exact default-selector implementation slice that may be implemented after this decision is merged to current main.

This is not the implementation. It does not promote Candidate B in this branch, does not change `baseline` default behavior yet, does not weaken Candidate A, and does not reinterpret Candidate B as a `visual_lane_mode`.

## Current-main authority check

As of current main `aca29acf6fddb92fe79fdd638ef80659e79dc38a`, current main includes:

- Candidate B bundle bridge `candidate_b_bundle_curated_json_md_to_layer3_material_authority_v1`;
- Candidate B runtime bridge `candidate_b_runtime_source_to_layer3_material_authority_v1`;
- Candidate B default-promotion readiness audit `candidate_b_default_promotion_readiness_audit_v1`;
- readiness/bootstrap exposure for the readiness audit endpoint;
- explicit `candidate_b_default_promotion_selector_switch_admitted=false`.

Current prepared evidence validates:

- baseline run id `83167d91-06c0-4db3-ab8f-84109a6502d0`;
- Candidate A run id `93093b23-6a7f-4d41-80b1-f15c69077160`;
- Candidate B bundle id `tests/reports/cb-compare-cbodl2_20260522T134609Z_ecc48019`;
- Candidate B runtime run id `60ea7873-e7ba-4fcf-bdeb-dbbf6f3d0cdf`;
- bundle bridge receipt `cb-bundle-l3-60b7c76a021d5d369833bdf6`;
- runtime bridge receipt `cb-runtime-l3-48d3729c5487ae4afb66e6f7`;
- readiness audit id `cb-default-readiness-5b73ddf517d0467e7ee209b5`;
- readiness state `candidate_b_default_promotion_ready_for_separate_selection`;
- `candidate_b_default_promotion_enabled=false`;
- `default_selector_change_enabled=false`;
- `selector_mutation_performed=false`.

Validation evidence:

- `py -3.12 ./tools/validate_wb_prep.py` passed for the bundle source.
- `py -3.12 ./tools/validate_wb_prep.py --baseline-run-id 83167d91-06c0-4db3-ab8f-84109a6502d0 --candidate-a-run-id 93093b23-6a7f-4d41-80b1-f15c69077160 --candidate-b-source-kind runtime --candidate-b-run-id 60ea7873-e7ba-4fcf-bdeb-dbbf6f3d0cdf` passed for the runtime source.
- `py -3.12 -m pytest ./backend/tests/test_layer3_candidate_b_default_readiness.py ./backend/tests/test_layer3_candidate_b_bundle_bridge.py ./backend/tests/test_layer3_candidate_b_runtime_bridge.py -q` passed.
- `py -3.12 ./tools/l3-progress-check.py` passed before this freeze branch.

## Admitted implementation slice

This document admits exactly one future implementation slice after merge:

- `candidate_b_default_eligible_pdf_corpus_processing_selector_v1`

That slice may promote Candidate B only as the default upstream document-processing engine for eligible PDF/corpus processing when no explicit `document_processing_engine` is supplied.

The implementation must keep all non-PDF source families on the baseline engine by default.

## Required selector behavior

The implementation must:

- choose `candidate_b_opendataloader_pdf` by default only after the effective content type is proven to be `application/pdf`;
- keep non-PDF content types on `baseline` by default;
- preserve explicit caller `document_processing_engine="baseline"` as an immediate rollback/override path;
- preserve explicit caller `document_processing_engine="candidate_b_opendataloader_pdf"` for PDFs only;
- keep invalid or unsupported document-processing-engine values failing closed to `baseline`;
- keep `visual_lane_mode` defaulting to `baseline`;
- keep Candidate A available only through explicit `visual_lane_mode="candidate_a_page_evidence_v1"`;
- keep Candidate B out of `visual_lane_mode`;
- keep Candidate B runtime-source evidence routed through the existing runtime/document-trace path, not Candidate B Trace parity;
- keep Candidate B-derived Layer 3 material authority routed through the governed bundle/runtime bridge receipts.

## Required tests

The implementation must add or update tests proving:

- omitted `document_processing_engine` selects Candidate B for eligible PDF processing;
- omitted `document_processing_engine` remains baseline for text, CSV, XLSX, JSON, SEC EDGAR, ZIP, and image paths;
- explicit `baseline` still forces the baseline PDF parser;
- explicit `candidate_b_opendataloader_pdf` remains PDF-only and fails closed for non-PDF content;
- invalid document-processing-engine values still normalize/fail closed to baseline;
- `visual_lane_mode` semantics are unchanged;
- Candidate A tests remain unchanged except for any wording necessary to distinguish visual lane from processing engine;
- workbench compare and Candidate B runtime discovery still classify Candidate B as `document_processing_engine`, not `visual_lane_mode`;
- `validate_wb_prep.py` passes for bundle and runtime evidence after the selector implementation;
- Layer 3 Candidate B bridge/default-readiness tests still pass.

## Rollback and fail-closed requirements

The implementation must provide a server-owned rollback path to `baseline` that does not depend on Candidate B artifacts.

Acceptable rollback mechanisms:

- an explicit caller request/config value `document_processing_engine="baseline"`;
- a server-owned default-selector policy helper that can be changed back to `baseline` without touching visual-lane semantics.

The implementation must fail closed to baseline if:

- effective content type is not PDF;
- Candidate B parser admission is unavailable;
- Candidate B dependencies are unavailable;
- Candidate B runtime output cannot be produced;
- Candidate B bridge/readiness evidence is missing, stale, or contradicted by current main;
- rollback policy requests baseline;
- any caller tries to express Candidate B as a visual-lane mode.

## Excluded behavior

The implementation must not:

- change baseline parser behavior for non-PDF content;
- make Candidate A default;
- change Candidate A PageEvidence semantics;
- treat Candidate B as `visual_lane_mode`;
- make Candidate B default for images, OCR-only routes, Office, CSV, JSON, SEC EDGAR, ZIP, or arbitrary source families;
- add new source ingestion families to Layer 3;
- ingest PDFs/images directly into Layer 3 through the Candidate B bridges;
- add provider object writes;
- add connector dispatch;
- add RAG/vector/model runtime;
- add auth/security behavior;
- add browser-storage authority;
- add frontend-only durable authority;
- activate the full mockup.

## Required post-implementation proof

After implementation, current main must prove:

- Candidate B is the default only for eligible PDF/corpus processing;
- baseline remains an explicit rollback override;
- Candidate A remains the admitted PageEvidence visual-lane variant;
- non-PDF default behavior remains baseline;
- Candidate B can still be compared against baseline and Candidate A;
- bundle and runtime Candidate B to Layer 3 bridge tests pass;
- Candidate B default-promotion readiness audit still returns ready over selected evidence;
- no unauthorized Layer 3, provider, connector, RAG/model, auth/security, full-mockup, browser-storage, or frontend-only authority expansion occurred.

## Next exact posture

After this freeze is merged, the next exact posture is:

`implement_candidate_b_default_eligible_pdf_corpus_processing_selector_v1`

