# 04C — Candidate B OpenDataLoader Output Crosswalk and Non-Equivalence Map

## Purpose

Prevent false equivalence between OpenDataLoader semantic/layout output and the repo’s current lower-layer owner-path output.

This doc answers one narrow question:
what can Candidate B honestly compare,
what must remain derived only,
and what has no valid first-pass equivalence.

---

## A. Directly comparable fields

### 1. Page count
- ODL: `number of pages`
- Repo truth: `page_count`

Allowed comparison:
- exact match / mismatch at document level

### 2. Page identity
- ODL: `page number`
- Repo truth: `page_summaries[*].page_number`

Allowed comparison:
- page indexing consistency only

### 3. Document text presence
- ODL: derived aggregate from text-node `content`
- Repo truth: `normalized_text`, `normalized_char_count`

Allowed comparison:
- presence/absence
- broad character-count delta
- whether Candidate B exposes structural segmentation that explains differences

Not allowed:
- replacing repo-truth normalized text with ODL text

---

## B. Structural overlay comparisons

These are comparison overlays, not owner-path replacements.

### 1. Headings / lists / tables
- ODL: semantic elements in JSON
- Repo truth: no direct owner-path semantic hierarchy field

Allowed use:
- evidence that a page/document belongs to a structural-gain regime
- explanation for why Candidate B may be useful as a workbench comparator

### 2. Hidden text
- ODL: `hidden text`
- Repo truth: degradation/quality/ambiguity interpretation only

Allowed use:
- explanatory evidence for noise or OCR-layer ambiguity

Not allowed:
- direct rewrite of current degradation codes

### 3. Images
- ODL: image nodes / image file references
- Repo truth: `visual_page_refs`

Allowed use:
- supporting evidence that a page has extracted image content

Not allowed:
- treating ODL image extraction as equivalent to preserve-lane `visual_page_refs`

---

## C. Fields that require derived-only comparison

These may be compared only through a Candidate B derived summary:
- document text segmentation quality
- page-level structural density
- hidden-text incidence
- tagged-PDF benefit
- multi-column evidence

The compare report must explicitly mark these as `derived_comparison_only`.

---

## D. Fields with no valid v1 equivalence

These current repo-truth fields have no valid first-pass ODL equivalent and must remain owner-path truth:
- `document_processing_contract_id`
- `extractor_family`
- `extractor_id`
- `extractor_version`
- `normalization_contract_id`
- `quality_status`
- `degradation_codes`
- `document_class`
- `visual_page_refs[*].status`
- `visual_page_refs[*].visual_page_class`
- `visual_page_refs[*].artifact_ref`

Also non-equivalent in standard ODL JSON:
- vector graphics / path-operator evidence
- preserve-lane artifact semantics
- OCR-owner-path decision semantics

These must be reported as non-equivalent, not approximated.

---

## E. Required compare-report outputs

The compare report must include, at minimum:
- `page_count_match`
- `page_index_consistency`
- `text_presence_delta`
- `candidate_b_structural_gain_signals`
- `candidate_b_hidden_text_signals`
- `candidate_b_non_equivalent_fields`
- `vector_control_findings`
- `ocr_control_findings`
- `interference_check_passed`

---

## F. Why this doc matters

Without this crosswalk,
OpenDataLoader’s richer semantic output can easily be mistaken for owner-path superiority.
That would be a category error.

The goal of Candidate B v1 is comparison,
not silent substitution.
