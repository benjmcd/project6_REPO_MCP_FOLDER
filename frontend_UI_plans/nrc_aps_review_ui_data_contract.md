# NRC APS Review UI Data Contract

## 1. Purpose

This document defines the additive read-only route and response-model plan for the NRC APS review UI.

The contract here is intentionally separate from the visual layer so that:

- the review model is the authority
- the renderer can change later without changing data semantics

## 2. Route Family

Recommended route families:

- UI route:
  - `/review/nrc-aps`
- review API routes:
  - `/api/v1/review/nrc-aps/...`

All review API routes in v1 should be GET-only.

## 3. Proposed Read-Only Endpoints

### 3.1 Run Selector

`GET /api/v1/review/nrc-aps/runs`

Purpose:

- populate the run selector
- identify the latest completed reviewable run

Response model:

```json
{
  "default_run_id": "string|null",
  "runs": [
    {
      "run_id": "string",
      "display_label": "string",
      "connector_key": "nrc_adams_aps",
      "status": "completed",
      "submitted_at": "iso8601|null",
      "completed_at": "iso8601|null",
      "reviewable": true,
      "disabled_reason_code": null,
      "summary_counters": {
        "selected_count": 0,
        "downloaded_count": 0,
        "failed_count": 0
      }
    }
  ]
}
```

### 3.2 Canonical Pipeline Definition

`GET /api/v1/review/nrc-aps/pipeline-definition`

Purpose:

- drive the `Pipeline Overview`
- expose stable stage/node ids and edges

Response model:

```json
{
  "pipeline_id": "nrc_aps_review_v1",
  "version": "1",
  "nodes": [
    {
      "node_id": "content_index",
      "label": "Content index",
      "stage_family": "core_pipeline",
      "expected_artifact_classes": [
        "run_report",
        "content_units",
        "diagnostics"
      ]
    }
  ],
  "edges": [
    {
      "from_node_id": "artifact_ingestion",
      "to_node_id": "content_index"
    }
  ]
}
```

### 3.3 Run-Specific Overview

`GET /api/v1/review/nrc-aps/runs/{run_id}/overview`

Purpose:

- drive the `Run-specific Overview`
- map real artifact outputs onto the canonical nodes

Response model:

```json
{
  "run_id": "string",
  "pipeline_id": "nrc_aps_review_v1",
  "viewability": {
    "reviewable": true,
    "warnings": []
  },
  "run_summary": {
    "status": "completed",
    "submitted_at": "iso8601|null",
    "completed_at": "iso8601|null"
  },
  "nodes": [
    {
      "node_id": "content_index",
      "state": "complete",
      "summary_metrics": {
        "indexed_content_units": 43,
        "indexing_failures_count": 0
      },
      "artifact_refs": [
        {
          "artifact_id": "string",
          "artifact_class": "run_report",
          "display_path": "review-root-relative-path"
        }
      ],
      "mapped_tree_entry_ids": [
        "tree-123"
      ]
    }
  ]
}
```

### 3.4 Artifact Tree

`GET /api/v1/review/nrc-aps/runs/{run_id}/tree`

Purpose:

- drive the right-hand artifact tree
- expose only bounded review-safe paths

Response model:

```json
{
  "run_id": "string",
  "roots": [
    {
      "tree_entry_id": "root-runtime",
      "label": "20260327_062011",
      "display_path": ".",
      "entry_kind": "directory",
      "children_loaded": false,
      "children": []
    }
  ]
}
```

Optional lazy child route if needed later:

`GET /api/v1/review/nrc-aps/runs/{run_id}/tree/{tree_entry_id}/children`

### 3.5 Node Details

`GET /api/v1/review/nrc-aps/runs/{run_id}/nodes/{node_id}`

Purpose:

- populate details panel when a diagram node is selected

Response model:

```json
{
  "run_id": "string",
  "node_id": "content_index",
  "label": "Content index",
  "stage_family": "core_pipeline",
  "state": "complete",
  "summary_metrics": {},
  "structured_summary": {},
  "artifact_refs": [],
  "mapped_tree_entry_ids": [],
  "warnings": []
}
```

### 3.6 File Details

`GET /api/v1/review/nrc-aps/runs/{run_id}/files/{tree_entry_id}`

Purpose:

- populate details panel when a tree node is selected

Response model:

```json
{
  "run_id": "string",
  "tree_entry_id": "string",
  "absolute_path": "absolute-path",
  "display_path": "review-root-relative-path",
  "entry_kind": "file",
  "file_class": "diagnostics",
  "mapped_node_id": "content_index",
  "metadata": {
    "size_bytes": 0,
    "modified_at": "iso8601|null"
  },
  "structured_summary": {},
  "warnings": []
}
```

Recommended semantics:

- `metadata` contains stable file/node identity and lightweight facts
- `structured_summary` contains a small stage-aware or artifact-aware summary when available
- neither field should be treated as a raw file preview in v1

## 4. Selector Semantics

Recommended defaults:

- selector shows latest completed reviewable NRC APS run by default
- non-reviewable NRC APS runs should appear as disabled items with reasons when practical
- selector should not include unrelated connector families in v1

Fallback:

- if disabled-row handling materially complicates the first implementation, the selector may temporarily return reviewable runs only

## 5. Reviewability Rules

The review service should determine reviewability before the UI renders.

Recommended rule set:

- connector key must be `nrc_adams_aps`
- status must be `completed`
- run-level summary/report artifacts must be present
- node/file mappings must be buildable

Example non-reviewable reasons:

- `not_nrc_aps`
- `run_not_completed`
- `missing_review_summary_root`
- `missing_core_stage_artifacts`
- `mapping_construction_failed`

Recommended selector behavior:

- return non-reviewable NRC APS runs with `reviewable=false` and a populated `disabled_reason_code` when practical
- let the UI disable selection for those rows

## 6. Canonical Node Id Rules

Canonical node ids must be:

- stable
- renderer-independent
- human-readable
- not derived from rendered labels
- not derived from filenames

Example stage ids:

- `source_corpus`
- `preflight`
- `submission`
- `artifact_ingestion`
- `content_index`
- `search_smoke`
- `branch_a_bundle`
- `branch_a_citation_pack`
- `branch_a_evidence_report`
- `branch_a_export`
- `branch_b_bundle`
- `branch_b_citation_pack`
- `branch_b_evidence_report`
- `branch_b_export`
- `export_package`
- `context_packet_package`
- `context_packet_export_a`
- `context_packet_export_b`
- `context_dossier`
- `deterministic_insight_artifact`
- `deterministic_challenge_artifact`
- `deterministic_challenge_review_packet`
- `validate_only_gates`

Final ids should be frozen once and reused across the UI and tests.

## 7. Artifact Tree Model

Each tree entry should include:

- `tree_entry_id`
- `label`
- `display_path`
- `entry_kind`
- `file_class`
- `mapped_node_ids`
- `children_loaded`
- `child_count`

Default v1 presentation rule:

- present the tree as a strict filesystem tree rooted at allowed review roots
- do not require a meaning-first curated grouping mode in v1
- leave room for a later alternate presentation mode over the same tree/model contract

Recommended `file_class` values:

- `runtime_root`
- `database`
- `summary`
- `gate_report`
- `manifest`
- `snapshot`
- `raw_blob`
- `run_report`
- `target_report`
- `content_units`
- `diagnostics`
- `normalized_text`
- `visual_page`
- `directory`
- `other_review_scoped`

## 8. Mismatch And Warning Model

If the review layer detects disagreement between API/DB state and persisted artifacts, it should emit structured warnings.

Example warning model:

```json
{
  "warning_code": "artifact_api_mismatch",
  "severity": "warning",
  "message": "Persisted artifact counts differ from API run counters."
}
```

Recommended warning codes:

- `artifact_api_mismatch`
- `missing_expected_artifact`
- `non_reviewable_run`
- `historical_schema_drift`
- `tree_entry_unmapped`

## 9. Security And Boundary Rules

The review API must:

- bound tree traversal to allowed review roots
- avoid arbitrary path traversal
- avoid exposing unrelated repo/user directories
- remain GET-only in v1
- return explicit empty or warning states instead of generating artifacts

Absolute paths may still be returned in file-details payloads for internal review ergonomics, but the tree model itself should not require absolute paths for identity.

## 10. Future-Compatible Hooks

The v1 contract should leave room for:

- preview metadata
- safe JSON/text preview
- live polling
- cross-run comparison

Preview default when added later:

- start with JSON/text only
- defer safe image preview for PNG visual pages until after the first preview slice works cleanly

None of these should alter the v1 read-only contract or endpoint family.
