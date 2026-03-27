# NRC APS Review UI Example Payloads

## 1. Purpose

This document provides concrete example payloads for the planned review UI endpoints using the verified golden run:

- `run_id = d6be0fff-bbd7-468a-9b00-7103d5995494`

These examples are intended to eliminate guesswork during implementation and testing.

## 2. Canonical Source Of Truth

These examples are derived from:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\local_corpus_e2e_summary.json`
- runtime artifacts under:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\storage\connectors\reports\`
- gate reports under:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\gate_reports\`

## 3. Run Selector Example

```json
{
  "default_run_id": "d6be0fff-bbd7-468a-9b00-7103d5995494",
  "runs": [
    {
      "run_id": "d6be0fff-bbd7-468a-9b00-7103d5995494",
      "display_label": "20260327_062011 | completed | 43 selected / 0 failed",
      "connector_key": "nrc_adams_aps",
      "status": "completed",
      "submitted_at": "2026-03-27T06:20:14.099291",
      "completed_at": "2026-03-27T06:38:13.733578",
      "reviewable": true,
      "disabled_reason_code": null,
      "summary_counters": {
        "selected_count": 43,
        "downloaded_count": 43,
        "failed_count": 0
      }
    }
  ]
}
```

## 4. Canonical Pipeline Definition Excerpt

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
    },
    {
      "node_id": "deterministic_challenge_review_packet",
      "label": "Deterministic challenge review packet",
      "stage_family": "deterministic",
      "expected_artifact_classes": [
        "run_report"
      ]
    }
  ],
  "edges": [
    {
      "from_node_id": "artifact_ingestion",
      "to_node_id": "content_index"
    },
    {
      "from_node_id": "deterministic_challenge_artifact",
      "to_node_id": "deterministic_challenge_review_packet"
    }
  ]
}
```

## 5. Run-Specific Overview Example

```json
{
  "run_id": "d6be0fff-bbd7-468a-9b00-7103d5995494",
  "pipeline_id": "nrc_aps_review_v1",
  "viewability": {
    "reviewable": true,
    "warnings": [
      {
        "warning_code": "missing_expected_artifact",
        "severity": "warning",
        "message": "run_detail.report_refs advertises artifact_dedup_report, checkpoint_history, and event_log, but those files are not present on disk."
      }
    ]
  },
  "run_summary": {
    "status": "completed",
    "submitted_at": "2026-03-27T06:20:14.099291",
    "completed_at": "2026-03-27T06:38:13.733578"
  },
  "nodes": [
    {
      "node_id": "content_index",
      "state": "complete",
      "summary_metrics": {
        "indexed_content_units": 43,
        "indexing_failures_count": 0,
        "selected_targets": 43,
        "processed_targets": 43
      },
      "artifact_refs": [
        {
          "artifact_id": "run-report::content-index",
          "artifact_class": "run_report",
          "display_path": "storage/connectors/reports/d6be0fff-bbd7-468a-9b00-7103d5995494_aps_content_index_run_v1.json"
        }
      ],
      "mapped_tree_entry_ids": [
        "tree::<sha256(storage/connectors/reports/d6be0fff-bbd7-468a-9b00-7103d5995494_aps_content_index_run_v1.json)>"
      ]
    },
    {
      "node_id": "search_smoke",
      "state": "complete",
      "summary_metrics": {
        "token": "Regulatory",
        "hit_count": 1656
      },
      "artifact_refs": [],
      "mapped_tree_entry_ids": []
    },
    {
      "node_id": "branch_a_bundle",
      "state": "complete",
      "summary_metrics": {
        "branch_accession": "LOCALAPS00010",
        "target_id": "14ccc411-c68e-46f2-9e30-0df7f0b83e70",
        "total_hits": 260
      },
      "artifact_refs": [
        {
          "artifact_id": "bundle::branch_a",
          "artifact_class": "run_report",
          "display_path": "storage/connectors/reports/run_d6be0fff-bbd7-468a-9b00-7103d5995494_f1e81e4c19c86155_e00ed8190968_aps_evidence_bundle_v2.json"
        }
      ],
      "mapped_tree_entry_ids": [
        "tree::<sha256(storage/connectors/reports/run_d6be0fff-bbd7-468a-9b00-7103d5995494_f1e81e4c19c86155_e00ed8190968_aps_evidence_bundle_v2.json)>"
      ]
    },
    {
      "node_id": "deterministic_challenge_review_packet",
      "state": "complete",
      "summary_metrics": {
        "review_item_count": 1,
        "acknowledgement_count": 1,
        "blocker_count": 0,
        "total_challenges": 2
      },
      "artifact_refs": [
        {
          "artifact_id": "review-packet::final",
          "artifact_class": "run_report",
          "display_path": "storage/connectors/reports/run_d6be0fff-bbd7-468a-9b00-7103d5995494_8ed797c94d61bc37dc6761b9_aps_deterministic_challenge_review_packet_v1.json"
        }
      ],
      "mapped_tree_entry_ids": [
        "tree::<sha256(storage/connectors/reports/run_d6be0fff-bbd7-468a-9b00-7103d5995494_8ed797c94d61bc37dc6761b9_aps_deterministic_challenge_review_packet_v1.json)>"
      ]
    }
  ]
}
```

## 6. Artifact Tree Example

```json
{
  "run_id": "d6be0fff-bbd7-468a-9b00-7103d5995494",
  "roots": [
    {
      "tree_entry_id": "tree::<sha256(.)>",
      "label": "20260327_062011",
      "display_path": ".",
      "entry_kind": "directory",
      "file_class": "runtime_root",
      "mapped_node_ids": [],
      "children_loaded": true,
      "child_count": 4,
      "children": [
        {
          "tree_entry_id": "tree::<sha256(local_corpus_e2e_summary.json)>",
          "label": "local_corpus_e2e_summary.json",
          "display_path": "local_corpus_e2e_summary.json",
          "entry_kind": "file",
          "file_class": "summary",
          "mapped_node_ids": [
            "source_corpus",
            "preflight",
            "submission",
            "search_smoke"
          ],
          "children_loaded": false,
          "child_count": 0
        },
        {
          "tree_entry_id": "tree::<sha256(storage/connectors/reports)>",
          "label": "reports",
          "display_path": "storage/connectors/reports",
          "entry_kind": "directory",
          "file_class": "directory",
          "mapped_node_ids": [],
          "children_loaded": false,
          "child_count": 111
        }
      ]
    }
  ]
}
```

## 7. Node Details Example

Example for `GET /api/v1/review/nrc-aps/runs/{run_id}/nodes/content_index`:

```json
{
  "run_id": "d6be0fff-bbd7-468a-9b00-7103d5995494",
  "node_id": "content_index",
  "label": "Content index",
  "stage_family": "core_pipeline",
  "state": "complete",
  "summary_metrics": {
    "indexed_content_units": 43,
    "indexing_failures_count": 0,
    "selected_targets": 43,
    "processed_targets": 43
  },
  "structured_summary": {
    "schema_id": "aps.content_index_run.v1",
    "run_status": "completed",
    "indexed_content_units": 43,
    "indexing_failures_count": 0
  },
  "artifact_refs": [
    {
      "artifact_class": "run_report",
      "display_path": "storage/connectors/reports/d6be0fff-bbd7-468a-9b00-7103d5995494_aps_content_index_run_v1.json"
    },
    {
      "artifact_class": "content_units",
      "display_path_glob_hint": "storage/connectors/reports/*_aps_content_units_v2.json",
      "count": 43
    }
  ],
  "mapped_tree_entry_ids": [
    "tree::<sha256(storage/connectors/reports/d6be0fff-bbd7-468a-9b00-7103d5995494_aps_content_index_run_v1.json)>"
  ],
  "warnings": []
}
```

## 8. File Details Example

Example for the final review packet file:

```json
{
  "run_id": "d6be0fff-bbd7-468a-9b00-7103d5995494",
  "tree_entry_id": "tree::<sha256(storage/connectors/reports/run_d6be0fff-bbd7-468a-9b00-7103d5995494_8ed797c94d61bc37dc6761b9_aps_deterministic_challenge_review_packet_v1.json)>",
  "absolute_path": "C:/Users/benny/OneDrive/Desktop/project6_REPO_MCP_FOLDER/backend/app/storage_test_runtime/lc_e2e/20260327_062011/storage/connectors/reports/run_d6be0fff-bbd7-468a-9b00-7103d5995494_8ed797c94d61bc37dc6761b9_aps_deterministic_challenge_review_packet_v1.json",
  "display_path": "storage/connectors/reports/run_d6be0fff-bbd7-468a-9b00-7103d5995494_8ed797c94d61bc37dc6761b9_aps_deterministic_challenge_review_packet_v1.json",
  "entry_kind": "file",
  "file_class": "run_report",
  "mapped_node_id": "deterministic_challenge_review_packet",
  "metadata": {
    "size_bytes": 4919,
    "modified_at": "2026-03-27T06:39:00.8861379Z"
  },
  "structured_summary": {
    "review_packet_id": "8ed797c94d61bc37dc6761b9a82da8aa67dcedd3f8390d8461d1628431b17b78",
    "review_item_count": 1,
    "acknowledgement_count": 1,
    "blocker_count": 0,
    "total_challenges": 2
  },
  "warnings": []
}
```

## 9. Gate Node Details Example

```json
{
  "run_id": "d6be0fff-bbd7-468a-9b00-7103d5995494",
  "node_id": "validate_only_gates",
  "label": "Validate-only gates",
  "stage_family": "verification",
  "state": "complete",
  "summary_metrics": {
    "gate_count": 12,
    "passed_count": 12,
    "failed_count": 0
  },
  "structured_summary": {
    "all_passed": true,
    "gate_names": [
      "artifact_ingestion",
      "content_index",
      "context_dossier",
      "context_packet",
      "deterministic_challenge_artifact",
      "deterministic_challenge_review_packet",
      "deterministic_insight_artifact",
      "evidence_bundle",
      "evidence_citation_pack",
      "evidence_report",
      "evidence_report_export",
      "evidence_report_export_package"
    ]
  },
  "artifact_refs": [
    {
      "artifact_class": "gate_report",
      "display_path_glob_hint": "gate_reports/*.json",
      "count": 12
    }
  ],
  "mapped_tree_entry_ids": [
    "tree::<sha256(gate_reports/artifact_ingestion.json)>",
    "tree::<sha256(gate_reports/content_index.json)>"
  ],
  "warnings": []
}
```

## 10. Known Warning Example

```json
{
  "warning_code": "missing_expected_artifact",
  "severity": "warning",
  "message": "run_detail.report_refs advertises artifact_dedup_report, checkpoint_history, and event_log, but those files are not present in storage/connectors/reports."
}
```
