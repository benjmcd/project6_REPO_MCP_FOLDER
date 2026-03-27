# Agent Bake-Off Execution Protocol

## 1. Purpose

This document defines the controlled process for evaluating Google Jules and Google Antigravity separately against the same NRC APS review UI scope.

The goal is not to let each tool freely reinterpret the project. The goal is to compare how each tool executes the same bounded task under the same constraints.

## 2. Canonical Source Of Truth

The bake-off packet is subordinate to the existing review UI planning set in this folder.

Primary authority documents:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_spec.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_data_contract.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_implementation_blueprint.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_canonical_graph_registry.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_mapping_and_reviewability_rules.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_dependency_and_asset_strategy.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_validation_plan.md`
- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\nrc_aps_review_ui_example_payloads.md`

## 3. Core Principle

This should be run as a controlled A/B bake-off.

Do not:

- run both tools in the same mutable workspace
- give them different prompts
- give them different repo states
- judge them on different scope slices

Do:

- use the same starting commit
- use the same bounded task
- use the same planning packet
- use the same scoring rubric

## 4. Recommended Execution Topology

Use three workspaces from the same starting commit:

- one frozen baseline workspace
- one isolated Jules workspace
- one isolated Antigravity workspace

Within this repo, the owned bake-off directories for agent-produced artifacts are:

- Jules:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\jules\`
- Antigravity:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity\`

Recommended use of those directories:

- `deliverables\`
  - final written submission artifacts
- `logs\`
  - run notes, planning output, and validation logs
- `patches\`
  - exported diffs or patch files representing the lane's code changes
- `screenshots\`
  - UI screenshots or walkthrough images

Important distinction:

- actual code edits for the feature should happen in each tool's isolated repo lane
- these owned folders are the canonical submission/output drop zones for each tool's notes, screenshots, logs, and exported patches

Recommended branch/worktree naming:

- baseline: current branch
- Jules: `codex/bakeoff-jules-slice01`
- Antigravity: `codex/bakeoff-antigravity-slice01`

Exact local lane setup, including the frozen starting commit and the recommended `.claude\worktrees\...` paths, is defined in:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_bakeoff_local_setup.md`

The two agent workspaces should not share a writable tree.

If true isolated code-edit worktrees are created later, these owned folders should still be used as the canonical submission/output drop zones for each tool.

## 5. Recommended Bake-Off Order

### 5.1 Round 0: Prompt Dry Run

Give each tool the packet without asking for code yet.

Require:

- implementation plan
- stated assumptions
- identified blockers
- intended file touch list

Purpose:

- catch interpretation drift early
- avoid wasting implementation time if one tool is already broadening scope

### 5.2 Round 1: Bounded Implementation Slice

Once both dry-run plans look acceptable, give each tool the same bounded slice defined in:

- `agent_bakeoff_scope_slice_01.md`

This is the first real comparison round.

### 5.3 Round 2: Optional Follow-Up Slice

Only if needed, run a second slice after scoring Round 1.

Do not run a second slice until the first slice has been reviewed and scored using the same rubric.

## 6. Shared Input Packet

Each tool should receive the same packet:

- `agent_bakeoff_brief.md`
- `agent_bakeoff_scope_slice_01.md`
- `agent_bakeoff_submission_checklist.md`
- `agent_bakeoff_rubric.md`
- all review UI planning docs listed in Section 2

## 7. First Slice Recommendation

The optimal first comparison slice is:

- additive read-only review endpoints
- canonical/run-specific review model plumbing
- strict filesystem tree payload
- minimal backend-served UI shell
- run selector
- view toggle
- right-side details drawer shell

This slice is large enough to reveal architectural quality and scope discipline, but still small enough to compare cleanly.

## 8. Evaluation Procedure

After both tools finish the same slice:

1. collect their changed file lists
2. collect their stated assumptions and known risks
3. run the same test/validation procedure against each output
4. score both using `agent_bakeoff_rubric.md`
5. compare results in one side-by-side review

## 9. Decision Outcomes

The bake-off may end with one of three outcomes:

- Jules is the better implementation path
- Antigravity is the better implementation path
- a hybrid split is best

The hybrid split is allowed only if the first round shows a clear asymmetry, for example:

- one tool is stronger on backend/API structure
- the other is stronger on frontend interaction polish

Do not choose a hybrid split just to avoid deciding.

## 10. What To Preserve During The Bake-Off

Each tool run must preserve:

- read-only v1 boundaries
- backend-served UI strategy
- no-build asset strategy
- NRC APS-only scope
- strict filesystem tree default
- canonical graph registry

## 11. Failure Conditions

A tool output should be treated as failed for the round if it:

- broadens scope beyond the slice
- introduces mutation or execution controls
- introduces a new build toolchain or frontend framework contrary to the plan
- ignores the canonical graph or reviewability rules
- cannot explain its touched files coherently

## 12. Completion Standard

This execution protocol is complete only if the evaluator can answer:

- how each tool will be isolated
- what packet each tool receives
- what slice each tool is asked to implement
- how the outputs will be judged on equal terms
