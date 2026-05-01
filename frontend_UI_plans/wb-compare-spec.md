# NRC APS Workbench Compare Workspace Specification

## 1. Objective

Design a read-only internal workbench workspace for comparing the same corpus-backed document across:

- `baseline`
- `candidate_a_page_evidence_v1`
- Candidate B OpenDataLoader workbench bundles
- admitted Candidate B OpenDataLoader PDF runtime runs

This feature is not a broad cross-run explorer and it is not an extension of the shipped single-run document-trace page.

## 2. Repo-Fit Authority Model

This specification relies on the following repo-confirmed authority surfaces:

- live web entrypoint:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\main.py`
- live review API routes:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\review_nrc_aps.py`
- live review schemas:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\schemas\review_nrc_aps.py`
- live review runtime/path helpers:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_runtime.py`
- live single-run document-trace model:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_document_trace.py`
- live review UI assets:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\index.html`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.css`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.js`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\document_trace.html`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\document_trace.css`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\document_trace.js`
- current lower-layer compare/workbench authority:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\run_nrc_aps_candidate_b_compare.py`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tools\run_nrc_aps_candidate_b_baseline.py`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\support_nrc_aps_candidate_b_opendataloader.py`
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\next_milestone_plans\candidate_b_workbench\04C_CANDIDATE_B_OPENDATALOADER_OUTPUT_CROSSWALK_AND_NON_EQUIVALENCE_MAP.md`
- corpus identity authority:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\fixtures\nrc_aps_docs\v1\manifest.json`

Current local operator-evidence note:

- the first explicit Candidate B proof bundle is archived locally under `archive\20260412-cb-proof\`
- that archive is useful as an example bundle shape for this workspace
- it is not canonical runtime authority and must not be presented as if it were a tracked mainline artifact set
- that archive is not guaranteed to exist in every fresh worktree checkout, so zero discovered Candidate B bundles must be treated as a normal fail-closed state rather than an implementation error

## 3. Current Repo-State Constraints

Repo-confirmed constraints that shape this feature:

- the shipped review page is run-scoped and does not support cross-run comparison
- the shipped document-trace page is also run-scoped and target-scoped
- `frontend_UI_plans\nrc_aps_document_trace_ui_spec.md` explicitly keeps multi-document comparison out of scope for document-trace v1
- `frontend_UI_plans\nrc_aps_review_ui_spec.md` explicitly keeps cross-run comparison views out of scope for review UI v1
- Candidate B originally shipped as workbench-only bundle evidence, but a later explicit runtime-admission reopen now admits `document_processing_engine="candidate_b_opendataloader_pdf"` as an opt-in runtime path
- the Workbench Compare runtime-source tranche preserves the bundle path and adds runtime Candidate B as an explicit source kind instead of reusing `candidate_b_bundle_id`
- fresh isolated checkouts may legitimately have no eligible baseline runs, no eligible Candidate A runs, no eligible Candidate B bundles, and no admitted Candidate B runtime runs

Therefore the workbench compare workspace must be a separate additive page and API family.

## 4. Product Goal

The product goal is to let an operator answer this question without stitching together review runs, compare JSON, proof JSON, and corpus metadata by hand:

- how do baseline, Candidate A, and Candidate B differ for the same corpus-backed document

The page must allow a user to:

- choose one `baseline` review run
- choose one `candidate_a_page_evidence_v1` review run
- choose one Candidate B source: either an allowlisted compare bundle or an admitted Candidate B runtime run
- choose one shared corpus-backed document
- see aligned document-level and page-level comparison outputs
- distinguish direct comparisons from derived overlays and non-equivalent fields
- jump from baseline and Candidate A back into the existing single-run document-trace page
- jump from bundle-sourced Candidate B into the separate additive `Candidate B Trace` page
- jump from runtime-sourced Candidate B into the existing document-trace page for that admitted runtime target
- keep Candidate B Trace parity and document-trace parity expansion separate from the runtime-source Compare tranche

## 5. Product Identity

The product name for this feature is:

- `Workbench Compare`

The page shell route for v1 should be:

- `/review/nrc-aps/workbench-compare`

The canonical workspace identity is:

- `baseline_run_id + candidate_a_run_id + candidate_b_source_kind + (candidate_b_bundle_id or candidate_b_run_id) + fixture_id`

The page shell should use query parameters for deep-linkable state:

- `baseline_run_id`
- `candidate_a_run_id`
- `candidate_b_source_kind`
- `candidate_b_bundle_id`
- `candidate_b_run_id`
- `fixture_id`
- optional `tab`

Those query parameters are page-local to `/review/nrc-aps/workbench-compare`.
They do not extend or modify the existing document-trace query-string contract.
For v1, `candidate_b_bundle_id` should be serialized in URL-safe POSIX-style relative-path form rather than Windows backslash form.
When `candidate_b_source_kind=runtime`, the page must use `candidate_b_run_id` and must clear stale `candidate_b_bundle_id` state.

## 6. In Scope For V1

- NRC APS only
- separate workbench compare page
- explicit source selection for baseline, Candidate A, and Candidate B
- same-corpus compare only
- compare target intersection based on a shared corpus fixture identity
- a shared source/identity header rather than three duplicate source viewers
- three comparison columns:
  - `baseline`
  - `candidate_a`
  - `candidate_b`
- compare tabs:
  - `summary`
  - `normalized_text`
  - `diagnostics`
  - `structure`
- explicit comparability badges:
  - `direct`
  - `derived_only`
  - `non_equivalent`
  - `missing`
- deep links for baseline and Candidate A into the existing document-trace page
- deep links for bundle-sourced Candidate B into the separate `Candidate B Trace` page
- deep links for runtime-sourced Candidate B into the existing document-trace page
- read-only API routes and read-only UI behavior
- explicit unavailable states when any required source class is absent in the current checkout
- review-page header navigation affordance into the compare page
- no new navigation added inside the document-trace page itself

## 7. Out Of Scope For V1

- changing the shipped document-trace page into a compare page
- changing the shipped review page into a compare page
- arbitrary cross-run comparison outside the shared corpus-backed fixture set
- Candidate B promotion or defaulting
- Candidate B Trace parity for admitted runtime runs
- widening Candidate B into the `visual_lane_mode` family
- run execution from the browser
- editing, annotation, or mutation
- direct browser reads from arbitrary filesystem paths
- treating Candidate B structure output as equivalent to baseline/Candidate A owner-path extraction fields
- tri-view source PDF rendering

## 8. Required Invariants

- the feature must be strictly read-only
- the feature must remain workbench-only
- the frontend must not assemble the compare model by calling three unrelated variant endpoints and inventing correspondence client-side
- the backend must construct a single compare model per selected `fixture_id`
- the compare target key for v1 must be `fixture_id`
- if a selected baseline or Candidate A run cannot be mapped to a shared `fixture_id`, that target must be excluded rather than guessed
- Candidate B fields marked `derived only` or `non-equivalent` by the committed Candidate B crosswalk must remain marked that way in the UI
- Candidate B local archived bundles must be treated as optional operator evidence, not guaranteed mainline data
- Candidate B runtime runs must be selected through explicit `candidate_b_source_kind=runtime`, not by overloading `candidate_b_bundle_id`
- a fresh isolated implementation or test worktree may legitimately have no Candidate B bundle roots at all
- a fresh isolated implementation or test worktree may legitimately have no admitted Candidate B runtime runs
- a fresh isolated implementation or test worktree may also legitimately have no eligible baseline runs or no eligible Candidate A runs
- the existing document-trace page must remain behaviorally unchanged
- the existing review page may add only the narrow header navigation affordance into `Workbench Compare`; no other review-page behavior change is in scope
- deep links back into document trace must remain limited to `run_id`, `target_id`, and optional `tab`
- deep links into `Candidate B Trace` must remain limited to bundle-sourced `candidate_b_bundle_id`, `fixture_id`, and optional `tab`

## 9. Compare Identity Model

The compare workspace models identity in layers:

### 9.1 Shared compare identity

- `fixture_id`

This is the only valid v1 compare target key.

### 9.2 Baseline and Candidate A identity

Baseline and Candidate A remain run-scoped review surfaces with:

- `run_id`
- `target_id`
- `content_id`

Those identities are retained in the compare payload, but they do not replace `fixture_id` as the compare key.

### 9.3 Candidate B identity

Bundle-sourced Candidate B remains bundle-scoped and fixture-scoped with:

- `bundle_id`
- `fixture_id`
- historical run metadata from `compare.json` / `proof.json`

Runtime-sourced Candidate B remains an admitted review runtime source selected by `candidate_b_source_kind=runtime` plus `candidate_b_run_id`; it retains `run_id`, `target_id`, and `content_id` in the compare payload while still using `fixture_id` as the shared compare key.

### 9.4 Mapping rule

For v1, baseline and Candidate A rows are eligible only when they can be matched to a corpus-manifest entry by source-file identity.

Expected match order:

1. exact case-insensitive match on `trace.identity.source_file_name` against corpus-manifest entry basename
2. if that is absent, no v1 fallback guesswork

This is intentionally strict. A missed compare target is better than a false match.
If multiple manifest entries share the same case-insensitive basename, the mapping is ambiguous and the fixture must be excluded.

For bundle-sourced Candidate B, the effective three-way target set for v1 is constrained by Candidate B bundle coverage, not by the full corpus manifest.
If a selected Candidate B bundle covers only a subset of corpus fixtures, only that surviving subset may appear in the compare target list.
For runtime-sourced Candidate B, the effective target set is constrained by the strict intersection of the selected baseline run, Candidate A run, and Candidate B runtime run after corpus-manifest mapping.

## 10. Workspace Layout

The page should use a stable three-zone structure:

- header
  - back link to the main review page
  - source selectors for baseline, Candidate A, and Candidate B
  - fixture selector
  - theme control
- shared context rail
  - canonical source identity
  - fixture metadata
  - comparability summary badges
- deep links to single-run document trace for baseline and Candidate A
- deep links to the separate `Candidate B Trace` page for Candidate B
- main body
  - three-column compare grid

The grid is variant-centric, not source-viewer-centric.
In the landed implementation, operators may reach this page either by direct URL or by the review-page header navigation affordance.
The compare lane still does not add new navigation inside the document-trace page itself.

Reason:

- the source document is the same corpus-backed document across all three variants
- rendering three duplicate PDF viewers would add complexity without adding equivalent comparison value
- the existing single-run document-trace page already provides the richer source-viewer experience

## 11. Compare Semantics

The workspace must preserve the Candidate B comparison classes already frozen in the committed Candidate B planning pack:

- direct document-level comparisons:
  - page count
  - text presence
  - broad character-count delta
- derived-only overlays:
  - structural density
  - hidden-text signals
  - multi-column and table signals
  - image extraction signals
- non-equivalent owner-path fields:
  - owner-path document class / degradation / extractor metadata that Candidate B cannot replace

The UI must make those categories visible instead of flattening them into a generic "different" state.
