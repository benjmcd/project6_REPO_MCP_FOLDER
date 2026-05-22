# 965 - Candidate B Runtime Bridge Freeze

## Purpose

Freeze the smallest governed Candidate B runtime-source to Layer 3 bridge that may be implemented after this decision is merged to current main.

This is a runtime-source bridge decision for the opt-in `document_processing_engine="candidate_b_opendataloader_pdf"` path only. It does not promote Candidate B to default and does not reinterpret Candidate B as a `visual_lane_mode`.

## Current-main authority check

As of current main `083131e428f5f907ddb0837cac44265704533ccc`, the Candidate B bundle-backed bridge is implemented and merged through `candidate_b_bundle_curated_json_md_to_layer3_material_authority_v1`.

Current main still blocks the next bridge in `964-cb-bridge.md`:

- `candidate_b_runtime_source_to_layer3_material_authority_v1`

This document admits exactly that one future implementation slice after merge.

## Preserved upstream posture

- `baseline` remains the default corpus-processing posture.
- Candidate A remains the admitted `candidate_a_page_evidence_v1` visual-lane variant.
- Candidate B remains an opt-in processing-engine path when runtime-sourced: `document_processing_engine="candidate_b_opendataloader_pdf"`.
- Candidate B is not a `visual_lane_mode`.
- Candidate B default promotion is not admitted by this freeze.

## Admitted runtime bridge

The runtime bridge may accept one validated Candidate B runtime run id and produce a server-owned, Layer 3 source-directory-compatible curated material root.

The bridge must record:

- Candidate B runtime run id;
- baseline run id;
- Candidate A run id;
- Candidate B runtime validation result;
- strict compare target fixture set;
- runtime review-root/storage authority hash;
- admitted runtime artifact subset hash;
- redacted provenance and source labels;
- bridge receipt id;
- bridge mode `candidate_b_runtime_source_to_layer3_material_authority_v1`;
- downstream compatibility with Layer 3 source-directory material preview and Gate B material authority.

## Admitted runtime artifact subset

Only deterministic Candidate B runtime-source textual/material authority is admitted into the curated Layer 3 material root.

The implementation must choose the narrowest current-main runtime artifact family that is already produced by the opt-in Candidate B processing engine and already tied to Document Trace or workbench compare evidence. Admitted files must be copied or materialized as `.json` or `.md` only, within the existing Layer 3 source-directory relative-path and recursion-depth constraints.

The first runtime bridge must not ingest the runtime DB as a broad source. It may read existing runtime rows or storage artifacts only as authority inputs needed to identify and hash the selected Candidate B runtime outputs, then write a bounded curated JSON/MD material root and durable receipt.

## Required linkage and validation

The runtime bridge must prove:

- the selected Candidate B runtime run exists in the current checkout runtime discovery;
- the selected run classifies as `candidate_b_opendataloader_pdf`;
- the selected run summary does not set Candidate B as a visual-lane mode;
- the selected run has an available runtime database and storage root;
- baseline, Candidate A, and Candidate B runtime-source compare targets are non-empty;
- required follow-through fixtures remain present;
- runtime-source validation passes through the same validate-only prep path used for operator workbench readiness;
- the curated root can pass existing Layer 3 source-directory scan, material preview, and Gate B without widening those checks.

## Excluded artifacts

The runtime bridge must reject or omit:

- source PDFs;
- annotated PDFs;
- PNGs or extracted images;
- arbitrary nested binary artifacts;
- broad runtime DB ingestion;
- broad runtime storage ingestion;
- Candidate B Trace parity for runtime runs;
- arbitrary local directory input;
- web connector input;
- RAG/vector/model runtime;
- provider object writes;
- connector dispatch;
- browser storage authority;
- frontend-only durable authority;
- full mockup activation.

## Compatibility rule

The runtime bridge output must be consumable by the existing Layer 3 server-configured source-directory ingestion policy without widening that policy.

Layer 3 source-directory preview and Gate B must continue to use their existing authority checks. The bridge does not bypass material-preview hash checks, Gate B decision-basis validation, source-directory live-file matching, or stale-authority rejection.

## Bundle bridge remains current first proof

The bundle bridge remains the already-implemented first proof path for Candidate B-derived Layer 3 material authority. The runtime bridge must not weaken or reinterpret the bundle bridge receipt model.

If runtime-source evidence disagrees with bundle-backed evidence, the runtime bridge must fail closed or report a blocked comparison state rather than promoting Candidate B or rewriting bundle receipts.

## Default-promotion gate remains blocked

Candidate B default promotion remains blocked until a later readiness gate proves:

- baseline, Candidate A, and Candidate B comparison evidence;
- no unacceptable regression against baseline/Candidate A;
- bundle and runtime bridge validation;
- full Candidate B to Layer 3 downstream proof;
- operator-visible provenance and status;
- rollback to baseline;
- fail-closed stale/missing artifact behavior;
- exact eligible corpus scope;
- no unauthorized source, runtime, provider, connector, RAG, model, or full-mockup expansion.

## Stop conditions

Implementation must stop if:

- the selected Candidate B runtime run is not discoverable through current-main runtime discovery;
- the selected Candidate B runtime run does not classify as `candidate_b_opendataloader_pdf`;
- the selected Candidate B runtime run uses Candidate B as a visual-lane mode;
- `tools/validate_wb_prep.py` fails for the selected runtime run;
- baseline or Candidate A run linkage is missing;
- the strict compare target set is empty;
- the selected runtime artifact family is ambiguous or cannot be bounded to JSON/MD material authority;
- a declared retained or selected runtime JSON/MD artifact is absent;
- any excluded PDF, image, binary, broad runtime DB, broad runtime storage, connector, provider, RAG, model, or frontend-only authority path is requested for Layer 3 ingestion;
- the curated root cannot pass existing Layer 3 source-directory scan, material preview, and Gate B authority checks without widening those checks.
