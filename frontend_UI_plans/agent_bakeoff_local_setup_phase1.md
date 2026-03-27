# Agent Bake-Off Local Setup: Phase1 Retrieval Plane

## 1. Purpose

This document defines the exact local and GitHub lane mapping for the next bake-off round: APS Tier1 retrieval-plane Phase1A.

It supersedes the older Slice 01 lane names for this milestone.

## 2. Frozen Baseline

Use this source state for the Phase1A bake-off:

- primary committed baseline:
  - `7b67f58`
  - `Embed repo guardrails directly in phase1 packet`
- committed milestone-plan context:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\next_milestone_plans\2026-03-27_aps_tier1_retrieval_plane_phase1.md`

Important:

- the milestone-plan file is now part of the committed Phase1A packet
- the Phase1A lanes should reflect commit `7b67f58` or an equivalent synced copy of its packet contents

## 3. Exact Lane Mapping

### Antigravity

- editable repo lane:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-phase1`
- branch:
  - `codex/bakeoff-antigravity-phase1`
- owned output directory:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-phase1\frontend_UI_plans\agent_workspaces\antigravity`
- milestone-plan directory in lane:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-phase1\next_milestone_plans`

### Jules

- GitHub repo:
  - `https://github.com/benjmcd/bakeoff-jules`
- editable repo branch:
  - `codex/bakeoff-jules-phase1`
- local GitHub-safe mirror:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\jules_repo_phase1`
- owned output directory in mirror:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\jules_repo_phase1\frontend_UI_plans\agent_workspaces\jules`
- milestone-plan directory in mirror:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\jules_repo_phase1\next_milestone_plans`

## 4. Why The Lane Shapes Differ

Antigravity can operate directly on a local isolated worktree.

Jules requires a GitHub-backed repo/branch, so the local mirror exists only to prepare and inspect the GitHub-safe lane that corresponds to:

- repo:
  - `benjmcd/bakeoff-jules`
- branch:
  - `codex/bakeoff-jules-phase1`

## 5. Required Submission Roots

For this phase, each tool must write its non-code artifacts into its own lane-local output directory.

### Antigravity output root

- `...\bakeoff-antigravity-phase1\frontend_UI_plans\agent_workspaces\antigravity\`

### Jules output root

- `...\jules_repo_phase1\frontend_UI_plans\agent_workspaces\jules\`

Within each output root, use:

- `deliverables\`
- `logs\`
- `patches\`
- `screenshots\`

## 6. Phase1A Rule

Do not reuse:

- `bakeoff-antigravity-slice01`
- `bakeoff-jules-slice01`
- the older Slice 01 prompts

Those lanes remain historical references only.

Also do not reuse:

- an older Jules chat/session that previously worked on Slice 01 review UI deliverables
- an older Antigravity task that previously targeted a different milestone

Each Phase1A run must begin in a fresh session/task whose first summary explicitly names `APS Tier1 retrieval-plane Phase1A`.
