# PageEvidence Module, Component, Dependency, and Touchpoint Inventory

## Purpose

Provide an explicit implementation-oriented inventory of the modules, components, dependencies, data touchpoints, and connection surfaces relevant to a PageEvidence strengthening lane.

This document exists so the strengthening lane does not remain architecturally vague. It is the pack's concrete map of:

- what code is central
- what code is adjacent
- what libraries/dependencies are part of the intended lane
- what contracts and data fields are touched
- and what connections/endpoints should remain untouched by default

---

## Pack implementation posture

Within this separate pack, the prepared implementation posture is:

- Lane Class A only
- Passes 1-4 only
- small fixed Pass 3 field set only
- no production touch to `nrc_aps_document_processing.py` in Pass 1
- optional analysis-only scratch copy of `nrc_aps_document_processing.py` allowed outside `backend`, provided it is non-authoritative and non-runtime

Current branch adequacy note:

- Pass 1 is already complete and closure-validated on this branch
- fresh truth re-establishment found no residual Pass 2 helper-extraction or compatibility-bridge obligation
- further work should therefore begin only from a newly proven insufficiency, not from stale assumptions about unfinished separation

## Core service / runner modules

### Primary owner surfaces

1. `backend/app/services/nrc_aps_page_evidence.py`
   - current owner of shared evidence extraction
   - now also contains an in-file Candidate A projection layer via the Pass 1 split
   - no separate projection/helper module is currently required
2. `tools/run_nrc_aps_page_evidence_workbench.py`
   - current standalone runner / report writer
3. `backend/tests/test_nrc_aps_page_evidence.py`
   - core service behavior tests
4. `tests/test_nrc_aps_page_evidence_workbench.py`
   - runner/report behavior tests

### Conditional seam-adjacent surfaces

5. `backend/app/services/nrc_aps_document_processing.py`
   - integrated seam that currently consumes Candidate A behavior
6. `tests/test_nrc_aps_document_processing.py`
   - seam-adjacent regression surface

## Pass-scoped owner interpretation

### Pass 1 realized owner set on this branch

- `backend/app/services/nrc_aps_page_evidence.py`
- `backend/tests/test_nrc_aps_page_evidence.py`

### Pass 2 owner set only if a real insufficiency is proven later

- `backend/app/services/nrc_aps_page_evidence.py`
- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`
- one narrow helper file under `backend/app/services/` if needed

### Pass 3 default owner set

- `backend/app/services/nrc_aps_page_evidence.py`
- `backend/tests/test_nrc_aps_page_evidence.py`

### Pass 4 default owner set

- `tools/run_nrc_aps_page_evidence_workbench.py`
- `tests/test_nrc_aps_page_evidence_workbench.py`
- one narrow evaluation/disagreement helper under `tools/` if needed

---

## Recommended component split

### Component 1 — shared evidence extraction

Responsibilities:
- deterministic PyMuPDF-derived page evidence
- page/region evidence field construction
- evidence normalization / validation
- no candidate-policy truth claims as conceptual center

### Component 2 — candidate projection

Responsibilities:
- Candidate A projection logic
- candidate-specific thresholds / projection rules
- projection-only derived fields

### Component 3 — workbench / evaluation orchestration

Responsibilities:
- fixture/path resolution
- artifact/report generation
- stable timestamp/path handling
- disagreement/evaluation summaries

### Component 4 — compatibility / regression checks

Responsibilities:
- service tests
- runner tests
- seam-adjacent regression checks
- hidden-consumer verification summaries

---

## Dependency inventory

### In-scope default dependencies

- Python stdlib
- `PyMuPDF` / `fitz` already present in the repo

### Explicitly out-of-scope new dependencies for this lane

- `shapely`
- `opencv` / `opencv-python-headless`
- OCR/layout-model packages
- any new ML/vision model dependency

### Rationale

This lane is intended to improve architecture, calibration, and evidence richness within the existing lightweight posture. Introducing geometry/model dependencies would convert the lane into a materially different dependency-adoption decision.

---

## Data / contract touchpoints

### Core PageEvidence artifact touchpoints

Current/likely touchpoints include:
- core page-evidence schema id/version handling
- page-level evidence fields
- projected-class-like derived fields
- candidate identity in artifact metadata

### Workbench artifact touchpoints

Current/likely touchpoints include:
- workbench report schema id/version
- report-level metadata (`generated_at_utc`, `candidate_stage`, config)
- per-document analysis blocks
- pinned historical workbench artifact compatibility

### Downstream touchpoints that must remain explicitly checked

- diagnostics payloads / refs written by artifact-ingestion and consumed downstream
- content indexing / stored refs, including persisted `visual_page_refs_json`
- retrieval-plane serializers/deserializers and retrieval canonicalizers
- evidence bundles and bundle-contract shaping
- review schemas, review service expectations, and document-trace / visual-artifact readers
- report/export/package persistence surfaces that depend indirectly on indexed or bundled payloads

---

## Connection / flow map

### Current main flow

1. workbench runner -> PageEvidence service -> workbench artifact
2. integrated Candidate A seam -> PageEvidence-derived behavior inside `nrc_aps_document_processing.py`

### What should remain untouched by default

- connector request normalization surfaces
- artifact-ingestion ownership boundaries
- review/runtime visibility classification
- report/export/package persistence semantics

Unless a widening trigger is explicitly satisfied, the strengthening lane should not alter those connection surfaces.

---

## Endpoint / interface interpretation note

This repo does not expose PageEvidence through a dedicated public API endpoint. The relevant “endpoints/connections” for this lane are therefore:

- internal service-call seams
- runner/report artifact boundaries
- hidden-consumer contract surfaces
- integrated visual-lane consumption inside document processing

The planning pack should continue to use this repo-native notion of touchpoint/interface rather than inventing external endpoint scope that does not exist.

---

## Default change envelope

### Safe-by-default changes

- extraction/projection separation
- additive internal evidence fields
- candidate-id decoupling from core evidence
- cleanup/resource hygiene
- stronger disagreement reports

### Escalation-required changes

- changes to admitted Candidate A runtime behavior
- schema-breaking artifact changes
- new dependency adoption
- broad hidden-consumer widening
- new candidate-selector activation or registry work

---

## Result

The strengthening lane now has an explicit implementation-oriented map of modules, components, dependencies, and touchpoints, reducing ambiguity and making simpler, less fragile implementation more likely.


## Internal evidence-field governance

If new internal evidence fields are added, they must be frozen by the field-definition register before or alongside implementation.

Each new field should have:

- exact meaning
- unit / range
- derivation rule
- nullability / missing-data rule
- whether it is substrate-only or candidate-policy-facing
- compatibility expectation for artifacts and tests
