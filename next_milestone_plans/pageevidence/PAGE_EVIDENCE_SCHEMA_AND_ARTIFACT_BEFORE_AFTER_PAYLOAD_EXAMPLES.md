# PageEvidence Schema and Artifact Before/After Payload Examples

## Purpose

Provide implementation-facing examples of how PageEvidence payloads and workbench artifacts may evolve under the strengthening lane without leaving compatibility ambiguous.

These are **illustrative planning examples**, not frozen final payloads and not binding compatibility fixtures by themselves. Final implementation must still comply with the schema/artifact compatibility policy. An example becomes binding only if a later repo-inserted control doc explicitly promotes it to compatibility-fixture status.

---



## Example status rule

Use these examples to reduce ambiguity during planning and implementation review.

Do **not** treat them as authoritative over:
- the live repo control docs before any later control-spine promotion, or
- the schema/artifact compatibility policy after any later control-spine promotion.

If an implementation needs binding payload fixtures, those should be created as explicit compatibility artifacts or tests, not inferred from this example doc alone.


## Example A — current fused PageEvidence payload (conceptual)

```json
{
  "schema_id": "aps.page_evidence.v1",
  "candidate_id": "candidate_a_page_evidence",
  "source_name": "example.pdf",
  "config": {
    "text_word_threshold": 20,
    "visual_coverage_threshold": 0.15
  },
  "pages": [
    {
      "page_number": 1,
      "word_count": 72,
      "image_count": 1,
      "drawing_count": 5,
      "combined_visual_coverage_ratio": 0.042,
      "projected_visual_page_class": "diagram_or_visual"
    }
  ]
}
```

---

## Example B — strengthened shared-evidence payload (conceptual)

```json
{
  "schema_id": "aps.page_evidence.v1",
  "source_name": "example.pdf",
  "config": {
    "text_word_threshold": 20,
    "visual_coverage_threshold": 0.15
  },
  "pages": [
    {
      "page_number": 1,
      "word_count": 72,
      "image_count": 1,
      "drawing_count": 5,
      "combined_visual_coverage_ratio": 0.042,
      "largest_image_bbox_ratio": 0.031,
      "largest_drawing_bbox_ratio": 0.012,
      "dominant_visual_region_present": true,
      "text_visual_overlap_ratio": 0.08,
      "meaningful_visual_region_count": 1
    }
  ]
}
```

Interpretation:
- shared evidence remains the center
- no candidate identity is required in the core payload
- no candidate-policy class is required in the core payload

---

## Example C — derived Candidate A projection payload (conceptual)

```json
{
  "candidate_id": "candidate_a_page_evidence",
  "policy_version": "candidate_a_page_evidence_v1",
  "source_name": "example.pdf",
  "pages": [
    {
      "page_number": 1,
      "candidate_a_projected_visual_class": "diagram_or_visual",
      "projection_reasoning": {
        "sparse_text": false,
        "dominant_visual_region_present": true
      }
    }
  ]
}
```

Interpretation:
- candidate-policy output is layered on top of shared evidence
- behavior-changing changes should attach here, not silently mutate shared evidence semantics

---

## Example D — compatibility bridge during migration (conceptual)

```json
{
  "schema_id": "aps.page_evidence.v1",
  "source_name": "example.pdf",
  "pages": [
    {
      "page_number": 1,
      "combined_visual_coverage_ratio": 0.042,
      "legacy_projected_visual_page_class": "diagram_or_visual",
      "candidate_a_projected_visual_class": "diagram_or_visual"
    }
  ]
}
```

Interpretation:
- use only if a temporary bridge is necessary
- do not keep redundant dual fields longer than needed

---

## Use rule

If implementation changes payload meaning or field ownership, include a before/after example in the implementation record and ensure the final artifact shape is explainable in the same style as these examples.
