# Agent Bake-Off Prompt: Antigravity

## 1. How To Use This File

Use this file when running the controlled bake-off in Antigravity.

Recommended flow:

1. create the isolated Antigravity lane defined in `agent_bakeoff_local_setup.md`
2. run the Round 0 dry-run prompt first
3. review the resulting plan for scope drift
4. if acceptable, run the Round 1 implementation prompt

## 2. Round 0 Dry-Run Prompt

Paste the following into Antigravity as the first prompt for the isolated workspace:

```text
You are participating in a controlled implementation bake-off for the repo at:

C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER

Focused workspace:

C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans

Your exact editable repo lane for this run is:

C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-slice01

Your lane should be created from:

- branch: codex/bakeoff-antigravity-slice01
- starting point: the committed HEAD of codex/frontend-ui-bakeoff-setup

Your owned bake-off output/work directory for this run is:

C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity

Within that directory, use:

- deliverables\
- logs\
- patches\
- screenshots\

Important:

- actual code edits belong in your isolated Antigravity repo lane
- this owned directory is the canonical drop zone for your notes, logs, screenshots, and exported patch artifacts

This round is DRY RUN ONLY. Do not implement code yet.

Read and use the following planning docs as the authority for scope and implementation shape:

- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_brief.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_scope_slice_01.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_submission_checklist.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_rubric.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_spec.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_data_contract.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_implementation_blueprint.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_canonical_graph_registry.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_mapping_and_reviewability_rules.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_dependency_and_asset_strategy.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_validation_plan.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_example_payloads.md

Hard constraints:

- NRC APS only
- strict read-only behavior
- backend-served additive UI
- no new build toolchain
- no new frontend framework
- no CDN dependencies
- strict filesystem tree as the default tree mode
- right-side details drawer

Not in scope for this round:

- run execution controls
- live polling
- file preview
- JSON/text preview
- image preview
- curated review-tree mode
- non-NRC APS generalization
- cross-run comparison

Golden runtime for validation:

- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011
- run_id = d6be0fff-bbd7-468a-9b00-7103d5995494

For this dry run, do not modify files. Produce:

1. a concise Slice 01 implementation plan
2. the exact files you expect to modify
3. the exact new files you expect to add
4. assumptions
5. likely blockers or risk areas
6. a clear statement confirming whether you can stay within the frozen scope

Write your dry-run notes and planning artifacts into:

- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity\logs\
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity\deliverables\

If a repo-confirmed blocker appears to require broader scope, state it explicitly and stop there.
```

## 3. Round 1 Implementation Prompt

Use this only after the dry-run output is acceptable.

```text
Proceed with implementation for Slice 01 in this isolated Antigravity workspace for:

C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER

Focused planning workspace:

C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans

Your exact editable repo lane for this run is:

C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-slice01

Your lane should be based on:

- branch: codex/bakeoff-antigravity-slice01
- starting point: the committed HEAD of codex/frontend-ui-bakeoff-setup

Your owned bake-off output/work directory for this run is:

C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity

Use this directory for all bake-off artifacts you produce:

- deliverables\
- logs\
- patches\
- screenshots\

Important:

- actual code edits belong in your isolated Antigravity repo lane
- this owned directory is the canonical drop zone for your notes, logs, screenshots, and exported patch artifacts

Implement the bounded first slice exactly as defined by:

- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_brief.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_scope_slice_01.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_submission_checklist.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_rubric.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_spec.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_data_contract.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_implementation_blueprint.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_canonical_graph_registry.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_mapping_and_reviewability_rules.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_dependency_and_asset_strategy.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_validation_plan.md
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_example_payloads.md

Implement only Slice 01:

- additive GET review endpoints
- review model plumbing
- minimal backend-served UI shell
- strict filesystem tree
- right-side details drawer shell
- node/file cross-selection wiring
- focused tests for the slice

Preserve these constraints:

- read-only only
- NRC APS only
- no new frontend framework
- no npm / Vite / Webpack / TypeScript build system
- no CDN assets
- no preview
- no polling
- no execution controls

Important implementation requirements:

- keep the code modular and non-fragile
- follow the implementation blueprint for file/module boundaries
- use the canonical graph registry rather than deriving the graph from Mermaid text
- do not hardcode the single golden runtime as the only supported root
- surface known mismatch cases visibly instead of hiding them

Validate against the golden runtime:

- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\backend\app\storage_test_runtime\lc_e2e\20260327_062011
- run_id = d6be0fff-bbd7-468a-9b00-7103d5995494

At the end, provide a submission that includes:

1. concise implementation summary
2. changed file list with reasons
3. architecture notes
4. assumptions made
5. risks and tradeoffs
6. tests added and tests run
7. commands used for validation
8. scope-conformance statement
9. screenshot(s) or UI evidence if available

Write your submission artifacts into:

- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity\deliverables\
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity\logs\
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity\patches\
- C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity\screenshots\

If you hit a real blocker, stop and explain it clearly instead of broadening scope.
```
