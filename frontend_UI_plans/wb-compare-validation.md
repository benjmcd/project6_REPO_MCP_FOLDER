# NRC APS Workbench Compare Validation Plan

## 1. Purpose

Define the validate-only and operator verification work required for the workbench compare workspace.

This plan is only for the future compare page/API lane.
It must not trigger new Candidate B runs or seed runtime artifacts during normal validation.

## 2. Canonical Validation Sources

Use these files as authority when implementing and validating:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_service.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_page.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\test_nrc_aps_candidate_b_opendataloader_compare.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\archive\20260412-cb-proof\README.md`

## 3. Required Automated Coverage

### 3.1 Service tests

Add a dedicated service test surface covering at minimum:

- baseline run classification
- Candidate A run classification
- Candidate B bundle discovery from allowlisted roots only
- strict `fixture_id` mapping from review-run source file name to corpus manifest
- omission of unmappable rows
- target intersection across the three selected sources
- comparability class assignment:
  - `direct`
  - `derived_only`
  - `non_equivalent`
  - `missing`
- fail-closed behavior when a required bundle artifact is absent

### 3.2 API tests

Add API tests covering at minimum:

- `sources` returns only allowed source classes
- `sources` returns an empty `candidate_b_bundles` list without error when the current checkout has no allowlisted bundle roots
- `targets` rejects invalid source combinations
- `manifest` rejects invalid or unmappable `fixture_id`
- `tabs/{tab_id}` rejects unsupported tabs
- tab payload includes all three required columns even when one column is unavailable

### 3.3 Page test

Add a page-route test covering at minimum:

- `/review/nrc-aps/workbench-compare` returns the expected shell
- the shell loads the dedicated compare JS/CSS assets

## 4. Manual Operator Validation

After automated tests are green, verify manually:

1. the page loads with no Candidate B bundle selected and surfaces a clear unavailable state
2. selecting valid baseline + Candidate A + Candidate B sources yields a non-empty target list
3. selecting incompatible sources yields an explicit empty-state explanation
4. the shared source header shows the expected fixture/document identity
5. each compare tab renders three columns
6. Candidate B limitation badges remain visible, including footer-related warnings when present
7. direct, derived-only, non-equivalent, and missing states are visually distinct
8. deep links open the correct baseline and Candidate A document-trace routes
9. no network call attempts to pass arbitrary filesystem paths from the browser

## 5. Validate-Only Rules

The workbench compare validation lane must:

- use validate-only tests
- fail closed when required local operator evidence is absent
- generate no new Candidate B bundle artifacts
- mutate no review runtime state

The compare page may read already-existing local archived bundles, but test and page validation must not invoke a new Candidate B compare run.

## 6. Known Risk Checks

The implementation must explicitly check for:

- baseline/Candidate A misclassification because visual-lane mode is missing or ambiguous
- stale or moved local Candidate B bundle roots
- false fixture mapping caused by friendly document titles
- overclaiming of Candidate B fields that are only derived overlays
- UI drift that makes the compare page look like a canonical production review surface rather than a workbench page

## 7. Re-Audit Checklist

After implementation and validation:

- re-read the final compare schemas
- re-read the final compare service mapping rules
- re-read the final page shell and client fetch graph
- confirm no existing document-trace files were widened accidentally
- update `frontend_UI_plans/README.md` if the touched file inventory changes
