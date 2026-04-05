# 00P Visual Page Class Roundtrip Support Note

## Purpose

Correct the remaining schema/contract-risk statement using direct test-backed evidence.

## Verified evidence

### Search-response roundtrip
`backend/tests/test_nrc_aps_advanced_adapters.py`
- `test_visual_page_refs_roundtrips_through_search_response_surface`
- proves `visual_page_class` survives:
  - JSON serialization
  - DB-style persistence representation
  - deserialization
  - API response model validation

### Evidence-group acceptance
`backend/tests/test_nrc_aps_evidence_bundle_integration.py`
- `test_group_accepts_visual_page_refs`
- passes a `visual_page_refs` item containing:
  - `visual_page_class`
  - artifact metadata
- evidence-group output accepts it successfully

## Interpretation

`visual_page_class` is indeed narrower in direct production-file search than `visual_page_refs`.
But it is not a weak or unsupported field.
It already has direct roundtrip/validation evidence through:
- adapter/search-response surface
- evidence-bundle output surface
- review-oriented schema/trace surfaces

## Revised conclusion

The earlier residual item should not remain phrased as an open schema/contract risk.

The defensible statement is:

- `visual_page_class` is narrower and more review-oriented than `visual_page_refs`
- but current evidence supports it sufficiently as a nested field
- so this is now a **watch-note**, not a remaining open blocker-level item
