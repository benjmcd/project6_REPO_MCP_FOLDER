# Agent Bake-Off Local Setup

## 1. Purpose

This document defines the exact local setup for running the Jules and Antigravity bake-off lanes from the same frozen starting point.

It is intentionally specific so the two tools receive:

- the same committed planning packet
- the same codebase state
- different editable worktree paths
- different owned output directories

## 2. Frozen Baseline

Use this committed baseline for the bake-off:

- frozen branch:
  - `codex/frontend-ui-bakeoff-setup`

The planning packet under `frontend_UI_plans\` is part of the committed `HEAD` of that frozen branch, so both isolated lanes inherit the same docs automatically when created from `codex/frontend-ui-bakeoff-setup`.

## 3. Exact Lane Mapping

### Jules

- editable repo lane:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-jules-slice01`
- branch:
  - `codex/bakeoff-jules-slice01`
- owned output directory:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\jules`

### Antigravity

- editable repo lane:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-slice01`
- branch:
  - `codex/bakeoff-antigravity-slice01`
- owned output directory:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\agent_workspaces\antigravity`

## 4. Why `.claude\worktrees\...`

This repo already has a live worktree pattern under `.claude\worktrees\...`, so using the same style is the narrowest repo-fit approach.

Do not point either tool at the root working tree once the isolated lanes are created.

## 5. Exact Setup Commands

Run these from:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER`

### 5.1 Verify The Frozen Starting Point

```powershell
git switch codex/frontend-ui-bakeoff-setup
git status --short
git log -1 --decorate --oneline
```

Expected result:

- clean working tree
- `HEAD -> codex/frontend-ui-bakeoff-setup`
- the latest committed setup freeze on `codex/frontend-ui-bakeoff-setup`

### 5.2 Create The Jules Lane

```powershell
git worktree add ".claude/worktrees/bakeoff-jules-slice01" -b codex/bakeoff-jules-slice01 codex/frontend-ui-bakeoff-setup
```

### 5.3 Create The Antigravity Lane

```powershell
git worktree add ".claude/worktrees/bakeoff-antigravity-slice01" -b codex/bakeoff-antigravity-slice01 codex/frontend-ui-bakeoff-setup
```

### 5.4 Verify Each Lane

```powershell
git -C ".claude/worktrees/bakeoff-jules-slice01" log -1 --decorate --oneline
git -C ".claude/worktrees/bakeoff-antigravity-slice01" log -1 --decorate --oneline
```

Expected result for both:

- the same `HEAD` commit currently checked in on `codex/frontend-ui-bakeoff-setup`

## 6. If A Lane Already Exists

Do not delete or overwrite an existing lane.

Instead, create a new suffixed lane and branch:

```powershell
git worktree add ".claude/worktrees/bakeoff-jules-slice01-rerun01" -b codex/bakeoff-jules-slice01-rerun01 codex/frontend-ui-bakeoff-setup
git worktree add ".claude/worktrees/bakeoff-antigravity-slice01-rerun01" -b codex/bakeoff-antigravity-slice01-rerun01 codex/frontend-ui-bakeoff-setup
```

Mirror the same suffix in the prompt text you give the tool if you use rerun lanes instead of the default paths.

## 7. Prompt Binding Rules

After the worktrees exist:

- point Jules at:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-jules-slice01`
- point Antigravity at:
  - `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-slice01`

Still require each tool to write its non-code bake-off artifacts into its owned output directory under:

- `frontend_UI_plans\agent_workspaces\jules\`
- `frontend_UI_plans\agent_workspaces\antigravity\`

## 8. Evaluation-Safe Workflow

1. Create both isolated lanes from the committed `HEAD` of `codex/frontend-ui-bakeoff-setup`.
2. Paste the Round 0 prompt into each tool after attaching it to the correct editable lane.
3. Review both dry-run outputs.
4. Paste the Round 1 prompt only if both dry-run plans are acceptable.
5. Compare exported patches, screenshots, and written submissions from the owned output directories.

## 9. Non-Goals

This setup doc does not authorize:

- running both tools in the same editable lane
- pointing both tools at the root worktree
- reusing an existing dirty lane
- deleting prior lanes to make room
