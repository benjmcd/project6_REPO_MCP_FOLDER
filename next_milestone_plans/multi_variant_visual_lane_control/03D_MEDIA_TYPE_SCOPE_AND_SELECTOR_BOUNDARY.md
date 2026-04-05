# 03D Media-Type Scope and Selector Boundary

## Decision

The first integrated selector scope is:

**PDF visual-lane only**

## In scope
Within PDF processing:
- shared page evidence relevant to visual significance
- visual preserve/no-op decision logic
- internal provenance/comparison hooks

## Out of scope in pass 1
- plain text path
- image path
- ZIP path
- top-level media routing
- artifact writer semantics
- report/export/review payload changes
- replay/promotion/safeguard behavior

## Why

The live owner entry point routes multiple content types. A higher seam would widen scope too early.

The live `_process_pdf(...)` function is still too broad to swap wholesale in pass 1. The safer first target remains a narrower shared-evidence + visual-decision seam.

## Boundary after seam freeze

The selector targets the PDF visual lane only.

The broader `_process_pdf(...)` owner still mixes OCR fallback, hybrid OCR, visual preservation, artifact writing, and page-summary behavior, but the first integrated selector seam is no longer unresolved.

That boundary is now frozen by `03W_EXACT_PROCESS_PDF_SEAM_FREEZE_SPECIFICATION.md`.

Implementation implication for pass 1:
- selector work may vary only the frozen visual-lane seam and any seam-internal branch behavior explicitly allowed by the control docs
- OCR fallback and hybrid OCR remain baseline-locked outside that seam in the first integrated phase
- artifact writer semantics, page-summary accumulation, top-level routing, and non-PDF media paths remain out of scope
