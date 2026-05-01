# NRC APS Workbench Compare Validation Plan

## 1. Purpose

Define the validate-only and operator verification work required for the workbench compare workspace.

This plan is the validation reference for the compare page/API lane.
It must not trigger new Candidate B runs or seed runtime artifacts during normal validation.

## 1A. Document Role

This is the canonical same-checkout prep and populated compare-validation document for the shipped Option 1 flow.

Use [docs/nrc_adams/nrc_aps_ui_launch_runbook.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/docs/nrc_adams/nrc_aps_ui_launch_runbook.md) for:

- the canonical launch contract
- current-main runtime preconditions
- explicit backend binding rules

Use [frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/nrc_aps_review_ui_startup_and_smoke_test.md) for:

- the concise startup walkthrough
- route/page-shell bring-up
- shell-level reachability checks

Use this document for:

- same-checkout prep
- `tools/validate_wb_prep.py`
- populated Workbench Compare validation
- Candidate B Trace follow-through from compare

Use [frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md](/C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/frontend_UI_plans/nrc_aps_frontend_ui_operator_validation_guide.md) for the broader manual validation pass after launch and prep succeed.

## 2. Canonical Validation Sources

Use these files as authority when implementing and validating:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_api.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_service.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_document_trace_page.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\tests\test_review_nrc_aps_page.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\seed_wb_compare.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\validate_wb_prep.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\test_seed_wb_compare.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\test_validate_wb_prep.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\test_nrc_aps_candidate_b_opendataloader_compare.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\archive\20260412-cb-proof\README.md`

## 3. Required Automated Coverage

### 3.1 Service tests

Add a dedicated service test surface covering at minimum:

- baseline run classification
- Candidate A run classification
- blank or missing `visual_lane_mode` normalizes to `baseline`
- Candidate B bundle discovery from allowlisted roots only
- Candidate B runtime source discovery from reviewable `candidate_b_opendataloader_pdf` runtime bindings only
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
- `sources` returns an empty `baseline_runs` list without error when the current checkout has no eligible baseline runs
- `sources` returns an empty `candidate_a_runs` list without error when the current checkout has no eligible Candidate A runs
- `sources` returns an empty `candidate_b_bundles` list without error when the current checkout has no allowlisted bundle roots
- `sources` returns an empty `candidate_b_bundles` list without error in a git worktree where `archive/*/cb-proof-*` is absent
- `sources` emits `candidate_b_bundle_id` values in canonical POSIX-style relative-path form
- `sources` emits admitted Candidate B runtime runs separately in `candidate_b_runtime_runs[]` and does not leak them into `baseline_runs[]` or `candidate_a_runs[]`
- `targets` rejects invalid source combinations
- `targets` rejects crafted `candidate_b_bundle_id` values containing traversal or non-discovered bundle roots
- `targets` rejects missing or invalid `candidate_b_run_id` values when `candidate_b_source_kind=runtime`
- `manifest` rejects invalid or unmappable `fixture_id`
- `manifest` rejects crafted `candidate_b_bundle_id` values containing traversal or non-discovered bundle roots
- `manifest` keeps `candidate_b_trace` bundle-only and emits `candidate_b_runtime_trace` for admitted runtime sources
- `tabs/{tab_id}` rejects unsupported tabs
- `tabs/{tab_id}` rejects crafted `candidate_b_bundle_id` values containing traversal or non-discovered bundle roots
- tab payload includes all three required columns even when one column is unavailable

### 3.3 Page test

Add a page-route test covering at minimum:

- `/review/nrc-aps/workbench-compare` returns the expected shell
- the shell loads the dedicated compare JS/CSS assets

## 4. Manual Operator Validation

After automated tests are green, verify manually:

0. populate and validate the same checkout with the canonical bundle-source prep sequence:
   - `py -3.12 .\tools\seed_wb_compare.py --visual-lane-mode baseline`
   - `py -3.12 .\tools\seed_wb_compare.py --visual-lane-mode candidate_a_page_evidence_v1`
   - `.\project6.ps1 -Action compare-nrc-aps-candidate-b`
   - `py -3.12 .\tools\validate_wb_prep.py`
   - do not proceed with populated operator validation unless `tools/validate_wb_prep.py` exits `0`
   - baseline and Candidate A review roots must be seeded with `tools/seed_wb_compare.py`, not `tools/run_nrc_aps_local_corpus_e2e.py`
   - the seeded review roots must use the fixed five-fixture PDF set shared with the Candidate B workbench bundle
   - any Candidate B bundle used for validation must be discovered from the same checkout root as the compare page
0. for runtime-sourced Candidate B operator proof, use the same fixed five-fixture seed tool and validate the explicit Candidate B runtime run id:
   - `py -3.12 .\tools\seed_wb_compare.py --visual-lane-mode baseline`
   - `py -3.12 .\tools\seed_wb_compare.py --visual-lane-mode candidate_a_page_evidence_v1`
   - `py -3.12 .\tools\seed_wb_compare.py --document-processing-engine candidate_b_opendataloader_pdf`
   - `py -3.12 .\tools\validate_wb_prep.py --candidate-b-source-kind runtime --candidate-b-run-id <candidate_b_runtime_run_id>`
   - runtime-source validation is validate-only, must use same-checkout fixed-fixture seeds, and must fail closed rather than infer a stale Candidate B runtime id
1. the review page header shows `Workbench Compare` immediately before `Document Trace`
2. the new header link opens `/review/nrc-aps/workbench-compare`
3. the page loads with no Candidate B bundle selected and surfaces a clear unavailable state
4. the page also surfaces clear unavailable states when no eligible baseline runs or no eligible Candidate A runs exist
5. selecting valid baseline + Candidate A + Candidate B sources yields a non-empty target list
6. selecting incompatible sources yields an explicit empty-state explanation
7. the shared source header shows the expected fixture/document identity with readable label/value separation
8. on a high-noise fixture such as `ml17123a319`, the summary band stays bounded and scrolls internally instead of collapsing the tab pane
9. at a shorter-height viewport around 700px, the tab strip remains visible and the compare tab content retains useful vertical depth
10. each compare tab renders three columns
11. Candidate B limitation badges remain visible, including footer-related warnings when present
12. direct, derived-only, non-equivalent, and missing states are visually distinct
13. baseline and Candidate A deep links open the correct document-trace routes
14. bundle-sourced Candidate B deep links open the separate `Candidate B Trace` page rather than `document-trace`
15. runtime-sourced Candidate B deep links use the existing `document-trace` route for the admitted Candidate B runtime target and do not masquerade as Candidate B Trace parity
16. when annotated PDF output is present, bundle-sourced `Candidate B Trace` defaults to `annotated_pdf` rather than `summary`
17. the Candidate B annotated PDF renders inline in the page rather than forcing a download response
18. no network call attempts to pass arbitrary filesystem paths from the browser

## 5. Validate-Only Rules

The workbench compare validation lane must:

- use validate-only tests
- fail closed when required local operator evidence is absent
- generate no new Candidate B bundle artifacts
- mutate no review runtime state

The compare page may read already-existing local archived bundles, but test and page validation must not invoke a new Candidate B compare run.
The separate same-corpus prep step may seed baseline, Candidate A, and Candidate B runtime review roots for operator validation, but that prep step is outside validate-only test execution and must use the dedicated fixture-corpus seed tool rather than the 69-document local-corpus demo runner.
The canonical same-checkout prep check is now `tools/validate_wb_prep.py`; it is validate-only, defaults to the bundle/Candidate B Trace source path, supports explicit runtime-source validation by run id, fails closed on empty or incoherent prep state, and should gate populated operator validation rather than ad hoc manual prep guesses.

Existing review and document-trace regression suites must continue to pass after implementation, including:

- `backend/tests/test_review_nrc_aps_api.py`
- `backend/tests/test_review_nrc_aps_document_trace_api.py`
- `backend/tests/test_review_nrc_aps_document_trace_service.py`
- `backend/tests/test_review_nrc_aps_document_trace_page.py`

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
