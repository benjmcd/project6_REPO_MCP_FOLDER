# Agent Bake-Off Brief

## 1. Objective

Implement a bounded first slice of the NRC APS review UI as defined by the planning documents in `frontend_UI_plans`.

This is a read-only review surface for NRC APS pipeline runs. It is not a run-execution surface, file editor, or general-purpose frontend rewrite.

## 2. Canonical Source Of Truth

You must treat these files as the authority for scope and implementation shape:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_spec.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_data_contract.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_implementation_blueprint.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_canonical_graph_registry.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_mapping_and_reviewability_rules.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_dependency_and_asset_strategy.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_validation_plan.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_example_payloads.md`

## 3. Repo-Fit Constraints

You must preserve all of the following:

- NRC APS-only scope
- strict read-only behavior
- backend-served additive UI
- no new build toolchain
- no new frontend framework
- no CDN dependencies
- strict filesystem tree as the default tree mode
- right-side details drawer

## 4. Explicit Non-Goals

Do not add in this round:

- run execution controls
- live polling
- file preview
- JSON/text preview
- image preview
- curated review-tree mode
- non-NRC APS generalization
- cross-run comparison

## 5. Working Style Requirements

- prefer the narrowest correct implementation
- keep code modular and non-fragile
- separate catalog, graph, tree, details, and UI concerns
- do not hardcode the single golden runtime as the only supported root
- do not derive the graph from Mermaid text or arbitrary filename ordering

## 6. Expected Deliverable Type

This is a code-and-tests deliverable for the bounded slice defined in:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_scope_slice_01.md`

## 7. Required Submission Material

Your output must satisfy:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_submission_checklist.md`

## 8. Evaluation Standard

Your work will be scored using:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_rubric.md`

## 9. Golden Run For Validation

The first implementation slice should validate cleanly against the verified runtime:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011`
- `run_id = d6be0fff-bbd7-468a-9b00-7103d5995494`

## 10. Required Behavioral Outcomes

At the end of the slice, the implementation should support:

- loading the review shell
- selecting the latest completed reviewable NRC APS run by default
- switching between pipeline overview and run-specific overview shell states
- rendering a strict filesystem tree for the selected run
- opening a right-side details drawer for node/file selections

## 11. Failure Conditions

Your output will be treated as a failed bake-off submission if it:

- broadens into a new platform or unrelated UI framework
- violates the read-only boundary
- materially contradicts the frozen planning docs
- produces an implementation that is hard to test or impossible to explain cleanly

