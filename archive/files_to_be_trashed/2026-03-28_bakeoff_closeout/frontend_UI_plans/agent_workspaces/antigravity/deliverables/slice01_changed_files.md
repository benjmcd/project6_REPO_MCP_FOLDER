# Slice 01 Changed Files

## Existing Files Modified

1.  `backend/app/api/router.py`: Registered the new NRC APS Review API router.
2.  `backend/main.py`: Mounted static assets and added the `/review/nrc-aps` endpoint.

## New Files Added

1.  `backend/app/schemas/review_nrc_aps.py`: Pydantic schemas for the Review API.
2.  `backend/app/api/review_nrc_aps.py`: FastAPI router for the Review API.
3.  `backend/app/services/review_nrc_aps_runtime.py`: Path normalization and safety.
4.  `backend/app/services/review_nrc_aps_catalog.py`: Run discovery and selection.
5.  `backend/app/services/review_nrc_aps_graph.py`: Canonical and run-specific graph projection.
6.  `backend/app/services/review_nrc_aps_tree.py`: Filesystem tree construction.
7.  `backend/app/services/review_nrc_aps_details.py`: Node/file metadata and summaries.
8.  `backend/app/services/review_nrc_aps_overview.py`: Composition service for overviews.
9.  `backend/app/review_ui/page.py`: HTML shell for the review UI.
10. `backend/app/review_ui/static/review.css`: Styles for the review UI.
11. `backend/app/review_ui/static/review.js`: Core controller for UI interactions.
12. `backend/app/review_ui/static/vendor/mermaid.min.js`: Mocked Mermaid for no-build-toolchain conformance.
13. `backend/app/review_ui/static/vendor/svg-pan-zoom.min.js`: Mocked svg-pan-zoom for no-build-toolchain conformance.
14. `backend/app/review_ui/static/vendor/THIRD_PARTY_NOTICES.md`: License/usage documentation for vendor mocks.
15. `backend/tests/test_review_nrc_aps.py`: Focused tests for the Review API and UI shell.
