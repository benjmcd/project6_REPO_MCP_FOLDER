# NRC APS Review UI Planning Set

This folder contains the planning/specification set for the proposed read-only NRC APS pipeline review UI.

## Purpose

The goal of this planning set is to define a repo-fit frontend review surface that lets a user:

- inspect the canonical NRC APS pipeline as a stable system view
- inspect a specific NRC APS run as a realized artifact graph
- navigate between pipeline stages, persisted files, and run metadata without mutating any runtime or report state

## Canonical Source Of Truth

For this planning set, the authority hierarchy is:

1. live backend/API/runtime surfaces in the root repo
2. current root control/status docs
3. design references used only for layout/interaction inspiration

Primary live authority surfaces:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\main.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\api\router.py`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\docs\nrc_adams\nrc_aps_authority_matrix.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\docs\nrc_adams\nrc_aps_status_handoff.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\local_corpus_e2e_summary.json`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011\`

Design references:

- `C:\Users\benny\Downloads\frontend_UI_UX_planning_context_reference_ref1.drawio.svg`
- `C:\Users\benny\Downloads\frontend_UI_UX_planning_context_reference_ref2.drawio.svg`

## Files In This Planning Set

- `nrc_aps_review_ui_spec.md`
  - primary product/spec document
- `nrc_aps_review_ui_data_contract.md`
  - additive read-only endpoint and model contract
- `nrc_aps_review_ui_open_decisions.md`
  - frozen defaults and non-critical implementation discretion
- `nrc_aps_review_ui_implementation_blueprint.md`
  - exact repo-fit module/file layout and implementation ownership plan
- `nrc_aps_review_ui_canonical_graph_registry.md`
  - exhaustive canonical NRC APS node registry, edge registry, and view projections
- `nrc_aps_review_ui_mapping_and_reviewability_rules.md`
  - run discovery, reviewability, node-artifact mapping, and mismatch handling rules
- `nrc_aps_review_ui_dependency_and_asset_strategy.md`
  - asset strategy, frontend dependency policy, and serving strategy
- `nrc_aps_review_ui_validation_plan.md`
  - validation matrix, golden fixture usage, and non-regression expectations
- `nrc_aps_review_ui_example_payloads.md`
  - concrete example payloads derived from the verified golden run
- `agent_bakeoff_execution_protocol.md`
  - controlled A/B process for running Jules and Antigravity separately against the same scope
- `agent_bakeoff_local_setup.md`
  - exact local branch/worktree setup, lane paths, and frozen starting commit for the bake-off
- `agent_bakeoff_brief.md`
  - vendor-neutral implementation brief to hand to each agent
- `agent_bakeoff_scope_slice_01.md`
  - first bounded implementation slice for the comparison run
- `agent_bakeoff_rubric.md`
  - scoring rubric for comparing the two outputs on equal terms
- `agent_bakeoff_submission_checklist.md`
  - required delivery artifacts each agent run must provide for evaluation
- `agent_bakeoff_prompt_jules.md`
  - ready-to-paste Jules prompts for the dry-run round and Slice 01 implementation round
- `agent_bakeoff_prompt_antigravity.md`
  - ready-to-paste Antigravity prompts for the dry-run round and Slice 01 implementation round
- `agent_workspaces\jules\`
  - dedicated bake-off workspace/output directory for Jules
- `agent_workspaces\antigravity\`
  - dedicated bake-off workspace/output directory for Antigravity

## Planning Boundaries

- This planning set is NRC APS specific.
- This planning set assumes a read-only UI.
- This planning set does not authorize implementation changes by itself.
- This planning set does not authorize file preview, run execution, polling, or mutation as part of v1.
