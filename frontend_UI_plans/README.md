# NRC APS UI Planning Set

This folder now contains the retained design and implementation-reference documents for the NRC APS review UI surface.

## Purpose

The retained files here are the UI-facing planning references for:

- the canonical NRC APS pipeline shape
- the internal review UI data contract
- node/artifact mapping and reviewability rules
- validation expectations for the review surface

These files remain useful as design and maintenance references even though the separate Jules/Antigravity bake-off packet is no longer part of the active repo surface.

## Canonical Source Of Truth

For the live UI and API behavior, the canonical implementation source of truth is in the root repo backend surface:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\review_nrc_aps.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\index.html`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.css`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\review_ui\static\review.js`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_graph.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_overview.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_tree.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\services\review_nrc_aps_details.py`

The files in this folder are reference material, not the live implementation surface.

## Retained Documents

- `nrc_aps_review_ui_spec.md`
  - primary UI/product specification
- `nrc_aps_review_ui_data_contract.md`
  - internal read-only review API contract reference
- `nrc_aps_review_ui_open_decisions.md`
  - frozen defaults and implementation discretion notes
- `nrc_aps_review_ui_implementation_blueprint.md`
  - repo-fit module/layout blueprint for the review UI
- `nrc_aps_review_ui_canonical_graph_registry.md`
  - canonical stage/node/edge registry and projection intent
- `nrc_aps_review_ui_mapping_and_reviewability_rules.md`
  - node/file mapping and reviewability rules
- `nrc_aps_review_ui_dependency_and_asset_strategy.md`
  - frontend dependency and asset strategy
- `nrc_aps_review_ui_validation_plan.md`
  - review-UI validation expectations
- `nrc_aps_review_ui_example_payloads.md`
  - example payloads derived from the golden run

## Archived Bake-Off Material

The retired Jules/Antigravity bake-off artifacts, prompts, mirrors, and workspaces were moved out of the live planning surface to:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\archive\files_to_be_trashed\2026-03-28_bakeoff_closeout\`

That archive area now holds the obsolete bake-off packet files, agent workspaces, mirror repos, and related worktrees that are no longer intended to drive active implementation.
