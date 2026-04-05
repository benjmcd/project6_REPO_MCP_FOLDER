# 00O Schema and Contract Drift Risk Narrowing

## Purpose

Sharpen the remaining schema/contract completeness risk using direct schema/contract searches.

## Verified schema/contract findings

### `visual_page_refs`
Verified in schema/contract surfaces checked:

- `backend/app/schemas/api.py`
  - `visual_page_refs` fields present

- `backend/app/services/aps_retrieval_plane_contract.py`
  - `visual_page_refs_json`
  - `canonicalize_visual_page_refs(...)`

- `backend/app/services/nrc_aps_evidence_bundle_contract.py`
  - retains `visual_page_refs`

### `visual_page_class`
Verified in schema surfaces checked:

- `backend/app/schemas/review_nrc_aps.py`
  - `NrcApsReviewVisualArtifactItemOut.visual_page_class`

And previously verified in:
- `review_nrc_aps_document_trace.py`

But not broadly found in the contract files checked.

## Narrowed conclusion

The residual schema/contract risk is now localized:

- `visual_page_refs` has broad schema/contract representation
- `visual_page_class` appears narrower and more review-specific

So the remaining risk is not that the visual surfaces are generally absent from schema/contract handling.
It is that `visual_page_class` is represented more narrowly than `visual_page_refs`, which creates a smaller but still real drift/watch item.

## Practical interpretation

This is not a major structural blocker.
It is a localized completeness asymmetry that should remain visible in the control pack.


## Correction after direct test-backed review

Additional verified evidence shows:

- `backend/tests/test_nrc_aps_advanced_adapters.py`
  proves `visual_page_class` survives persist -> deserialize -> API response roundtrip
- `backend/tests/test_nrc_aps_evidence_bundle_integration.py`
  proves evidence-group output accepts `visual_page_class` nested inside `visual_page_refs`

So the residual schema/contract item should be downgraded:
- from open risk
- to watch-note about narrower representation
