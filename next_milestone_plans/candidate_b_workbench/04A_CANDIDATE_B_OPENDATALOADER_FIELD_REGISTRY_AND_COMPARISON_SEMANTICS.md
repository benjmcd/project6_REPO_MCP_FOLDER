# 04A — Candidate B OpenDataLoader Field Registry and Comparison Semantics

## Purpose

Define exactly how OpenDataLoader outputs are translated into Candidate B comparison evidence,
and how those outputs are compared against current lower-layer repo truth.

v6 strengthens this by separating:
- direct comparable fields
- derived comparable fields
- explicit non-equivalent fields

---

## A. OpenDataLoader raw fields in scope

### Root/document fields
- `file name`
- `number of pages`
- `kids`

### Common content fields
- `type`
- `id`
- `level`
- `page number`
- `bounding box`

### Text-node fields
- `content`
- `hidden text`

### Heading/list/table/image/caption fields
- heading level
- list counts / linked list ids
- table counts / row and cell structure
- image source / format
- caption-linked content ids

These are the authoritative raw Candidate B inputs.

---

## B. Current lower-layer repo-truth outputs Candidate B must compare against

From the live `process_document()` surface,
Candidate B comparison must be organized against these current outputs:
- `document_processing_contract_id`
- `extractor_family`
- `document_class`
- `quality_status`
- `degradation_codes`
- `page_summaries`
- `visual_page_refs`
- `normalized_text`
- `normalized_text_sha256`
- `normalized_char_count`

Candidate B must not invent a comparison scheme that ignores those current outputs.

---

## C. Required derived Candidate B per-document summary

Candidate B must derive at least:
- `document_ref`
- `document_sha256`
- `odl_page_count`
- `struct_tree_state`
- `element_counts_by_type`
- `heading_count`
- `list_count`
- `table_count`
- `image_count`
- `caption_count`
- `hidden_text_node_count`
- `hidden_text_present`
- `processing_status`
- `limitation_flags`
- `warning_flags`
- `candidate_b_normalized_text`
- `candidate_b_normalized_char_count`

`candidate_b_normalized_text` is a comparison-support derivation only.
It must never replace current repo-truth `normalized_text`.

---

## D. Required per-page summary

For each page Candidate B must derive:
- `page_number`
- `element_type_counts`
- `heading_count`
- `list_count`
- `table_count`
- `image_count`
- `hidden_text_present`
- `hidden_text_count`
- `struct_tree_state`
- `semantic_gain_hypotheses`
- `limitation_tags`
- `non_equivalence_tags`

---

## E. Comparison semantics

### Allowed Candidate B value claims
Candidate B may claim value only when its evidence supports one of these:
- clearer heading/list/table structure than current lower-layer evidence makes visible
- tag-aware semantic structure on tagged PDFs
- clearer multi-column reading-order evidence
- hidden-text-noise exposure that helps explain current lower-layer degradation or ambiguity

### Forbidden Candidate B value claims in v1
Candidate B may not claim program-relevant value merely because it has:
- more semantic element types in the abstract
- richer markdown formatting alone
- more images extracted alone
- more text emitted alone
- different document-level text hashes alone

Program-relevant value must be tied back to current lower-layer comparison needs.

---

## F. Vector-control rule

Because OpenDataLoader JSON does not include vector graphics / line art in standard output,
Candidate B must not infer “no visual significance” merely from missing vector elements.

Instead, vector-heavy pages must be labeled from the corpus/control taxonomy as:
- `vector_limitation_control`
- `vector_non_equivalence`

Those labels come from the comparison harness,
not from absent ODL JSON evidence.

---

## G. OCR strictness rule

Candidate B must not override or dilute the current OCR strictness invariant.
If the live lower-layer baseline requires `ocr_required_but_unavailable`,
Candidate B may only report semantic/layout observations around that outcome.
It may not redefine the outcome.

---

## H. Non-equivalence rule

If a current repo-truth field has no clean ODL counterpart,
that must be reported as `non_equivalent_owner_field` rather than silently mapped.
The exact mappings and non-mappings are frozen in `04C`.
