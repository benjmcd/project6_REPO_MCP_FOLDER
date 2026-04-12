# NRC APS Workbench Compare API and Data Contract

## 1. Purpose

Freeze the additive backend contract for the workbench compare workspace so the frontend does not need to invent source discovery, fixture mapping, or compare semantics client-side.

## 2. Authority Surfaces

Use these files as authority before implementation:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\review_nrc_aps.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\schemas\review_nrc_aps.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_runtime.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_document_trace.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\tests\fixtures\nrc_aps_docs\v1\manifest.json`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\archive\20260412-cb-proof\README.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\next_milestone_plans\candidate_b_workbench\04C_CANDIDATE_B_OPENDATALOADER_OUTPUT_CROSSWALK_AND_NON_EQUIVALENCE_MAP.md`

## 3. Source Discovery Contract

### 3.1 Endpoint

- `GET /api/v1/review/nrc-aps/workbench-compare/sources`

### 3.2 Purpose

Return the selectable source sets for:

- baseline review runs
- Candidate A review runs
- Candidate B compare bundles

### 3.3 Required behavior

- baseline and Candidate A sources are discovered from reviewable runtime bindings
- variant classification for review runs must come from runtime request config / visual lane mode, not UI guesswork
- Candidate B bundle discovery must be limited to allowlisted local roots
- no endpoint may accept an arbitrary filesystem path from the client
- absence of Candidate B bundles in the current checkout is a valid state, not a backend error

### 3.4 Candidate B bundle discovery roots

The first implementation pass should discover bundles only from allowlisted local roots under the repo workspace:

- `archive/*/cb-proof-*`
- `tests/reports/cb-compare-*`

Those roots are relative to the current checkout root only.
The service must not scan sibling worktrees, user-profile directories, or arbitrary machine paths.
If none of those roots exist in the current checkout, the endpoint must return an empty `candidate_b_bundles[]` set without error.

A bundle is selectable only if all required files are present:

- `baseline-summary.json`
- `compare.json`
- `proof.json`
- `retain.json`

### 3.5 Source item shape

The endpoint should return:

- `baseline_runs[]`
- `candidate_a_runs[]`
- `candidate_b_bundles[]`
- optional defaults when uniquely resolvable

Baseline/Candidate A source item minimum fields:

- `run_id`
- `display_label`
- `completed_at`
- `variant_kind`

Candidate B bundle item minimum fields:

- `bundle_id`
- `display_label`
- `bundle_root`
- `generated_at_utc`
- `decision_recommendation`
- `local_only`

## 4. Compare Target Identity Contract

### 4.1 Endpoint

- `GET /api/v1/review/nrc-aps/workbench-compare/targets`

Required query params:

- `baseline_run_id`
- `candidate_a_run_id`
- `candidate_b_bundle_id`

### 4.2 Purpose

Return only the compare targets that can be strictly aligned across the three selected sources.

### 4.3 Compare key

The compare key is:

- `fixture_id`

### 4.4 Mapping rules

Candidate B side:

- `fixture_id` comes directly from `baseline-summary.json`, `compare.json`, and `proof.json`

Baseline/Candidate A side:

- resolve candidate document rows from the selected run
- resolve source-file identity from trace metadata
- map that source-file identity to a corpus-manifest entry basename
- if the run row cannot be mapped to a single manifest entry, exclude it

### 4.5 Target item minimum fields

- `fixture_id`
- `display_label`
- `source_file_name`
- `baseline_target_id`
- `candidate_a_target_id`
- `candidate_b_available`
- `comparability_state`

## 5. Compare Manifest Contract

### 5.1 Endpoint

- `GET /api/v1/review/nrc-aps/workbench-compare/targets/{fixture_id}/manifest`

Required query params:

- `baseline_run_id`
- `candidate_a_run_id`
- `candidate_b_bundle_id`

### 5.2 Purpose

Return the shared identity and tab availability model for one selected compare target.

### 5.3 Manifest minimum fields

- `fixture_id`
- `source_identity`
- `variant_bindings`
- `summary_badges`
- `tabs`
- `warnings`
- `limitations`
- `deep_links`

Required `variant_bindings` content:

- baseline:
  - `run_id`
  - `target_id`
  - `content_id`
- candidate_a:
  - `run_id`
  - `target_id`
  - `content_id`
- candidate_b:
  - `bundle_id`
  - `candidate_b_run_id`

Required `tabs` ids:

- `summary`
- `normalized_text`
- `diagnostics`
- `structure`

## 6. Compare Tab Contract

### 6.1 Endpoint

- `GET /api/v1/review/nrc-aps/workbench-compare/targets/{fixture_id}/tabs/{tab_id}`

Required query params:

- `baseline_run_id`
- `candidate_a_run_id`
- `candidate_b_bundle_id`

### 6.2 Purpose

Return one aligned compare tab payload that already contains all three variant columns.

The frontend must not fan out into three unrelated variant endpoints for the same tab and invent alignment client-side.

### 6.3 Common payload shape

Each tab payload must include:

- `fixture_id`
- `tab_id`
- `columns`
- `comparability_legend`
- `warnings`
- `limitations`

`columns` must contain exactly:

- `baseline`
- `candidate_a`
- `candidate_b`

Each column payload must include:

- `variant_id`
- `available`
- `comparability_class`
- `label`
- `data`
- `warnings`
- `limitations`
- optional `deep_link`

Allowed `comparability_class` values:

- `direct`
- `derived_only`
- `non_equivalent`
- `missing`

## 7. Tab-Specific Requirements

### 7.1 `summary`

Must include aligned document-level metrics:

- page count
- normalized char count
- document class
- degradation / limitation flags
- struct-tree state when present
- decision recommendation for Candidate B when relevant

### 7.2 `normalized_text`

Must include:

- baseline normalized text
- Candidate A normalized text
- Candidate B normalized text
- explicit notice that Candidate B text is not a replacement for owner-path normalized text

### 7.3 `diagnostics`

Must include:

- baseline diagnostics summary
- Candidate A diagnostics summary
- Candidate B limitation flags, semantic-gain hints, and non-equivalence notices

### 7.4 `structure`

Must include:

- baseline extracted-unit summary / page-level extraction cues
- Candidate A extracted-unit summary / page-level extraction cues
- Candidate B structural element summary, image signals, page summaries, footer warnings, and hidden-text signals

## 8. Fail-Closed Rules

- if the selected baseline run is not classified as `baseline`, reject it
- if the selected Candidate A run is not classified as `candidate_a_page_evidence_v1`, reject it
- if the selected Candidate B bundle lacks any required top-level artifact, reject it
- if `fixture_id` cannot be resolved across all three selected sources, omit it from the target list
- if a tab lacks valid data for a column, return `available = false` with a concrete warning rather than fabricating an empty aligned record

## 9. No-Mutation Rule

These compare endpoints must:

- read only from existing review runtimes and local Candidate B bundles
- create no artifacts
- mutate no runtime state
- fail closed when required local operator evidence is absent
