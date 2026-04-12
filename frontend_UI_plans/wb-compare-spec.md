# NRC APS Workbench Compare Workspace Specification

## 1. Objective

Design a read-only internal workbench workspace for comparing the same corpus-backed document across:

- `baseline`
- `candidate_a_page_evidence_v1`
- Candidate B OpenDataLoader workbench bundles

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

## 3. Current Repo-State Constraints

Repo-confirmed constraints that shape this feature:

- the shipped review page is run-scoped and does not support cross-run comparison
- the shipped document-trace page is also run-scoped and target-scoped
- `frontend_UI_plans\nrc_aps_document_trace_ui_spec.md` explicitly keeps multi-document comparison out of scope for document-trace v1
- `frontend_UI_plans\nrc_aps_review_ui_spec.md` explicitly keeps cross-run comparison views out of scope for review UI v1
- Candidate B is workbench-only, non-admitted, non-integrated
- the landed Candidate B compare surface intentionally added no API routes and no review UI route

Therefore the workbench compare workspace must be a separate additive page and API family.

## 4. Product Goal

The product goal is to let an operator answer this question without stitching together review runs, compare JSON, proof JSON, and corpus metadata by hand:

- how do baseline, Candidate A, and Candidate B differ for the same corpus-backed document

The page must allow a user to:

- choose one `baseline` review run
- choose one `candidate_a_page_evidence_v1` review run
- choose one Candidate B compare bundle
- choose one shared corpus-backed document
- see aligned document-level and page-level comparison outputs
- distinguish direct comparisons from derived overlays and non-equivalent fields
- jump from each variant back into the existing single-run document-trace page

## 5. Product Identity

The product name for this feature is:

- `Workbench Compare`

The page shell route for v1 should be:

- `/review/nrc-aps/workbench-compare`

The canonical workspace identity is:

- `baseline_run_id + candidate_a_run_id + candidate_b_bundle_id + fixture_id`

The page shell should use query parameters for deep-linkable state:

- `baseline_run_id`
- `candidate_a_run_id`
- `candidate_b_bundle_id`
- `fixture_id`
- optional `tab`

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
- deep links from each column into the existing document-trace page
- read-only API routes and read-only UI behavior

## 7. Out Of Scope For V1

- changing the shipped document-trace page into a compare page
- changing the shipped review page into a compare page
- arbitrary cross-run comparison outside the shared corpus-backed fixture set
- Candidate B admission, promotion, or defaulting
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
- the existing review page and document-trace page must remain behaviorally unchanged except for optional future navigation additions outside this spec

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

Candidate B remains bundle-scoped and fixture-scoped with:

- `bundle_id`
- `fixture_id`
- historical run metadata from `compare.json` / `proof.json`

### 9.4 Mapping rule

For v1, baseline and Candidate A rows are eligible only when they can be matched to a corpus-manifest entry by source-file identity.

Expected match order:

1. exact case-insensitive match on `trace.identity.source_file_name` against corpus-manifest entry basename
2. if that is absent, no v1 fallback guesswork

This is intentionally strict. A missed compare target is better than a false match.

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
- main body
  - three-column compare grid

The grid is variant-centric, not source-viewer-centric.

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
