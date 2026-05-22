# 964 - Candidate B Bundle Bridge Freeze

## Purpose

Freeze the smallest governed Candidate B to Layer 3 bridge that may be implemented after this decision is merged to current main.

This is a no-runtime bridge decision. It does not promote Candidate B to default and does not reinterpret Candidate B as a `visual_lane_mode`.

## Current-main authority check

As of current main `b04e4fd4513288adfb116e02335ee8bc4b503b3a`, existing Layer 3 control docs preserve Workbench Compare and Candidate B Trace as adjacent bundle-scoped inspection surfaces, not Layer 3 material authority. Current main does not already admit a Candidate B bundle to Layer 3 material bridge.

This document admits exactly one future implementation slice after merge:

- `candidate_b_bundle_curated_json_md_to_layer3_material_authority_v1`

## Preserved upstream posture

- `baseline` remains the default corpus-processing posture.
- Candidate A remains the admitted `candidate_a_page_evidence_v1` visual-lane variant.
- Candidate B remains either bundle-backed workbench evidence or the opt-in `document_processing_engine="candidate_b_opendataloader_pdf"` processing-engine path.
- Candidate B is not a `visual_lane_mode`.
- Candidate B default promotion is not admitted by this freeze.

## Admitted first bridge

The first bridge may accept one validated Candidate B bundle id and produce a server-owned, Layer 3 source-directory-compatible curated material root.

The bridge must record:

- validated Candidate B bundle id;
- baseline run id;
- Candidate A run id;
- Candidate B bundle validation result;
- strict compare target fixture set;
- bundle raw-root/file manifest hash;
- admitted-file subset hash;
- redacted provenance and source labels;
- bridge receipt id;
- bridge mode `candidate_b_bundle_curated_json_md_to_layer3_material_authority_v1`;
- downstream compatibility with Layer 3 source-directory material preview and Gate B material authority.

## Admitted artifact subset

Only these Candidate B bundle artifacts are admitted into the curated Layer 3 material root:

- `compare.json`
- `proof.json`
- `retain.json`
- `baseline-summary.json`
- raw `.json`
- raw `.md`

Raw `.json` and `.md` files must come from the validated bundle raw root and remain bounded by the bundle retention manifest. The bridge must not invent missing files or silently ignore a missing retained artifact that the selected receipt declares.

## Excluded artifacts

The first bridge must reject or omit:

- source PDFs;
- annotated PDFs;
- PNGs or extracted images;
- arbitrary nested binary artifacts;
- Candidate B runtime DB rows;
- Candidate B runtime storage rows;
- broad raw-root ingestion;
- arbitrary local directory input;
- web connector input;
- RAG/vector/model runtime;
- provider object writes;
- connector dispatch;
- browser storage authority;
- frontend-only durable authority;
- full mockup activation.

## Compatibility rule

The curated root must be consumable by the existing Layer 3 server-configured source-directory ingestion policy without widening that policy. That means the bridge output must contain only admitted `.json` and `.md` files, within the existing relative-path and recursion-depth constraints.

Layer 3 source-directory preview and Gate B must continue to use their existing authority checks. The bridge does not bypass material-preview hash checks, Gate B decision-basis validation, or source-directory live-file matching.

## Runtime bridge remains blocked

The next bridge, `candidate_b_runtime_source_to_layer3_material_authority_v1`, remains blocked until separately selected and frozen.

Runtime Candidate B currently routes through existing review runtime and Document Trace authority. This freeze does not admit runtime DB expansion, runtime storage ingestion, Candidate B Trace parity for runtime runs, or direct runtime-row material authority in Layer 3.

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

- the selected Candidate B bundle is not discoverable through current-main bundle discovery;
- `tools/validate_wb_prep.py` fails for the selected bundle;
- baseline or Candidate A run linkage is missing;
- the strict compare target set is empty;
- the bundle raw root is absent;
- a declared retained raw JSON/MD file is absent;
- any excluded PDF, image, binary, runtime DB, or runtime storage path is requested for Layer 3 ingestion;
- the curated root cannot pass existing Layer 3 source-directory scan, material preview, and Gate B authority checks without widening those checks.

