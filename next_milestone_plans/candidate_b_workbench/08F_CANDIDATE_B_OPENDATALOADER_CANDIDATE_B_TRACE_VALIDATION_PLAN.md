# 08F - Candidate B OpenDataLoader Candidate B Trace Validation Plan

## Purpose

Define the validate-only and operator verification burden for the Candidate B Trace lane.

This plan assumes the compare surface is already landed and that Candidate B Trace is a separate additive inspection surface.

Status note:

- this document froze the validation burden before implementation
- the current merged-main code now implements the additive Candidate B Trace lane and this plan is the validation authority for that surface
- the merged post-PR50 shipped baseline now implements the first-pass trace lane described here
- the repo now also carries repo-native browser regression coverage for the shipped compare + Candidate B Trace flow via:
  - `e2e/nrc-aps-review.spec.js`
  - `playwright.config.js`
  - `.github/workflows/playwright.yml`
  - `backend/tests/review_browser_fixture.py`
  - `backend/tests/review_browser_server.py`
  - `backend/tests/requirements-browser.txt`
- that landed hardening covers the minimum browser assertions frozen below without widening runtime admission or document-trace scope
- the repo now also carries a validate-only same-checkout prep gate for populated operator validation via:
  - `tools/validate_wb_prep.py`
  - `tests/test_validate_wb_prep.py`
- populated operator validation should now treat that prep gate as the canonical readiness check before opening the compare or Candidate B Trace pages

---

## Validation principles

- validate-only tests must not generate new ODL artifacts during normal pytest runs
- path-safety tests must fail closed on invalid or unavailable bundle ids
- current review/document-trace behavior must remain unchanged
- compare-surface regressions must remain green after the new deep-link additions

---

## Required validate-only test surfaces

### 1. Candidate B support harness tests

Scope:

- `tests/support_nrc_aps_candidate_b_opendataloader.py`
- existing Candidate B pytest surfaces under `tests/`

Validate:

- the ODL command requests annotated PDF output in addition to the current retained formats
- the harness canonicalizes the annotated PDF into the stable repo contract path
- missing annotated PDF output after a requested run fails closed
- compare-report payloads include:
  - `annotated_pdf_ref`
  - `annotated_pdf_sha256`
  - `annotated_pdf_status`

### 2. Candidate B Trace service tests

Scope:

- `backend/tests/test_review_nrc_aps_candidate_b_trace_service.py`

Validate:

- manifest composition for a valid bundle + fixture
- annotated PDF resolution from validated bundle metadata only
- raw JSON and raw Markdown resolution from validated bundle metadata only
- invalid `candidate_b_bundle_id` rejects cleanly
- unavailable fixture id rejects cleanly
- missing annotated PDF degrades to explicit unavailable state rather than 500

### 3. Candidate B Trace API tests

Scope:

- `backend/tests/test_review_nrc_aps_candidate_b_trace_api.py`

Validate:

- `manifest` returns 200 for a valid prepared bundle
- `annotated-pdf` streams the expected file type for a valid prepared bundle
- `annotated-pdf` uses inline content disposition suitable for embedded viewing rather than forced download
- `raw-json` returns structured JSON for a valid prepared bundle
- `raw-markdown` returns text for a valid prepared bundle
- invalid bundle ids and invalid fixtures fail closed
- no absolute local paths leak into JSON responses

### 4. Candidate B Trace page tests

Scope:

- `backend/tests/test_review_nrc_aps_candidate_b_trace_page.py`

Validate:

- page shell loads
- JS expects only schema-backed manifest fields
- tab ids align with the frozen page model
- no accidental dependency on `document_trace.js` or `document_trace.css`

### 5. Compare regression tests

Scope:

- existing `backend/tests/test_review_nrc_aps_workbench_compare_*.py`

Validate:

- compare manifest exposes `candidate_b_trace` when available
- Candidate B column deep links populate
- baseline and Candidate A deep links remain unchanged
- compare page still functions when Candidate B trace artifacts are unavailable

---

## Required operator validation

Operator validation must use a same-checkout prepared environment that already contains:

- one eligible baseline run
- one eligible Candidate A run
- one eligible Candidate B bundle with the new annotated PDF artifact present for at least one fixture

Then verify:

1. Workbench Compare still loads with the populated three-source state.
2. Candidate B deep-link affordances are visible where expected.
3. Clicking the Candidate B deep link opens `/review/nrc-aps/candidate-b-trace`.
4. The Candidate B Trace page loads `annotated_pdf` by default when available.
5. The annotated PDF renders inline in the Candidate B Trace page rather than forcing a download response.
6. The annotated PDF visibly reflects ODL classifications/regions rather than baseline/Candidate A owner-path rendering.
7. `summary`, `raw_json`, and `raw_markdown` tabs load coherently.
8. Query-state reload preserves `candidate_b_bundle_id`, `fixture_id`, and `tab`.
9. No compare query params leak into baseline/Candidate A document trace pages.
10. No browser-visible absolute local paths appear in the DOM, network payloads, or console.

Minimum fixture coverage:

- `fontish`
- `ml17123a319`
- one additional fixture with a distinct structure regime

---

## Short failure list that must block merge

- Candidate B Trace requires arbitrary filesystem path entry from the browser
- Candidate B Trace widens `document-trace` instead of remaining separate
- Candidate B Trace depends on `visual_lane_mode` admission
- Candidate B Trace leaks absolute local paths
- Candidate B Trace 500s when annotated PDF is missing for a selected fixture
- compare deep-link additions break current baseline/Candidate A trace behavior

---

## Regression gate

At minimum, these existing surfaces must remain green after implementation:

- `backend/tests/test_review_nrc_aps_api.py`
- `backend/tests/test_review_nrc_aps_document_trace_api.py`
- `backend/tests/test_review_nrc_aps_document_trace_service.py`
- `backend/tests/test_review_nrc_aps_document_trace_page.py`
- `backend/tests/test_review_nrc_aps_workbench_compare_api.py`
- `backend/tests/test_review_nrc_aps_workbench_compare_service.py`
- `backend/tests/test_review_nrc_aps_workbench_compare_page.py`

No new validation action should reseed or regenerate Candidate B bundles as part of ordinary pytest runs.

---

## Current repo-native browser coverage baseline

The shipped baseline now includes repo-native browser coverage for the already-landed compare + Candidate B Trace flow.

Current minimum covered assertions:

- Workbench Compare deep-links into Candidate B Trace
- Candidate B Trace first-load defaults to `annotated_pdf` when present
- annotated PDF route is requested with inline disposition rather than forced download
- baseline and Candidate A deep links still route to `document-trace`
- no query/path leakage reaches browser-visible surfaces in the covered flow

Future browser work should therefore be framed as explicit coverage expansion or refinement, not as a first introduction of repo-native browser enforcement.
