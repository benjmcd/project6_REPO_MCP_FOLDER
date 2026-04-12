# 06A - Candidate B OpenDataLoader Corpus Manifest and Labeling Guide

## Purpose

Anchor Candidate B to the repo's existing lower-layer proof corpus instead of inventing a new free-floating corpus,
and freeze the regime labels before outcomes are seen.

v6 strengthens this by making the regime taxonomy more explicit and more operational.

---

## A. Base corpus source

Candidate B v1 must use the existing lower-layer proof corpus as its base source:
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`

The root README also names a representative real NRC PDF fixture already included there:
- `tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf`

---

## B. Mutation rule for the base manifest

Do **not** mutate the base manifest in Candidate B v1.

If Candidate B needs additional page/document labels,
add them via a sidecar file:
- `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`

Use a sidecar manifest only if the label file is truly insufficient.

---

## C. Frozen first-run scope

The first Candidate B run is now frozen to the representative lower-bound PDF cohort only:
- `ml17123a319`
- `layout`
- `fontish`
- `scanned`
- `mixed`

Why this exact scope is frozen:
- it is the manifest-defined representative lower-bound PDF cohort on current `main`
- it matches the historically authoritative pinned Candidate A workbench artifact fixture set
- it avoids silently widening into non-PDF fixtures, regression-only extras, or parser-failure controls during the first Candidate B run

First-run exclusions are explicit:
- `txt_utf8`, `txt_utf16`, `mismatch_pdf_body` -> non-PDF fixtures
- `born_digital`, `corrupt`, `truncated` -> not in the representative lower-bound PDF cohort frozen for the first run

The exact first-run labels are frozen in:
- `tests/fixtures/nrc_aps_docs/v1/candidate_b_opendataloader_labels.json`

Do not mutate that file after the first Candidate B run starts.

---

## D. Required label buckets

Each document/page candidate should be labeled into one or more of the following:
- `tagged_pdf_expected_gain`
- `untagged_pdf_control`
- `multi_column_expected_gain`
- `table_list_heading_expected_gain`
- `hidden_text_noise_expected_gain`
- `header_footer_noise_control`
- `vector_limitation_control`
- `scanned_ocr_control`
- `password_control`
- `ordinary_text_control`
- `mixed_visual_semantic_control`

---

## E. Required label fields

Each label entry should record at minimum:
- `document_ref`
- `document_sha256` when available
- `page_scope` (`all` or explicit page list)
- `regime_labels`
- `expected_gain_claims`
- `expected_non_equivalences`
- `review_notes`

---

## F. Labeling rules

### `vector_limitation_control`
Use when the page/document has value tied to vector graphics / line art / chart geometry that standard ODL JSON will not capture.

### `scanned_ocr_control`
Use when the current lower-layer OCR strictness is central.
Candidate B may observe but must not redefine the outcome.

### `password_control`
Use when encrypted/password-protected handling is relevant.
If such a control is included,
password handling must be explicitly frozen before execution.

### `tagged_pdf_expected_gain`
Use when a structure tree is present or strongly expected.

### `multi_column_expected_gain`
Use when reading order is plausibly the main question.

### `table_list_heading_expected_gain`
Use when structural recovery matters more than the current visual-preservation owner path.

### `hidden_text_noise_expected_gain`
Use when ODL's hidden-text visibility is expected to clarify lower-layer ambiguity or noise.

---

## G. Corpus decision rule

Candidate B v1 must not cherry-pick only "good for ODL" pages.
The corpus must include:
- expected gain classes
- limitation controls
- OCR controls
- neutral controls

Otherwise the comparison is not honest.

---

## H. Timing rule

Labels must be frozen before the first Candidate B proof run.
Do not backfill labels after seeing results.
That converts evaluation into narrative fitting and is forbidden.
