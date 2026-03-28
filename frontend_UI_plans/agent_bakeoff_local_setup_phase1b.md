# Agent Bake-Off Local Setup: APS Tier1 Retrieval Plane Phase1B

## 1. Purpose

This document freezes the exact lane map for the next bounded bake-off slice after the accepted Phase1A retrieval foundation.

This round is:

- `Phase1B: Operator Retrieval Read Path`

It is not:

- Phase1A shadow retrieval foundation
- default public read-path cutover
- review UI work

## 2. Canonical Baseline

The source baseline for both lanes is the committed main-repo Phase1A implementation:

- repo root branch: `codex/frontend-ui-bakeoff-setup`
- baseline commit: `927c194`

This is the only approved starting point for the next bake-off round.

## 3. Antigravity Lane

Editable Antigravity lane:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-phase1b`

Expected branch:

- `codex/bakeoff-antigravity-phase1b`

Owned output directory inside the lane:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-phase1b\frontend_UI_plans\agent_workspaces\antigravity`

Required owned subfolders:

- `deliverables\`
- `logs\`
- `patches\`
- `screenshots\`

## 4. Jules Lane

GitHub-safe Jules mirror:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\jules_repo_phase1b`

Expected local branch:

- `codex/bakeoff-jules-phase1b`

Expected remote branch:

- `codex/bakeoff-jules-phase1b`

Expected GitHub repo:

- `https://github.com/benjmcd/bakeoff-jules`

Owned output directory inside the mirror:

- `.\frontend_UI_plans\agent_workspaces\jules\`

Required owned subfolders:

- `deliverables/`
- `logs/`
- `patches/`
- `screenshots/`

## 5. Milestone Authority

The milestone authority for this round is:

- `next_milestone_plans\2026-03-27_aps_tier1_retrieval_plane_phase1.md`

Additional live authority surfaces this round:

- `docs\nrc_adams\nrc_aps_reader_path.md`
- `docs\postgres\postgres_status_handoff.md`
- `backend\app\api\router.py`
- `backend\app\schemas\api.py`
- `backend\app\services\nrc_aps_content_index.py`
- `backend\app\services\aps_retrieval_plane.py`
- `backend\app\services\aps_retrieval_plane_validation.py`

## 6. Session Hygiene

Each tool must start a brand-new task/session for this round.

Wrong-context drift examples:

- describing the task as `Slice 01`
- describing the task as `Phase1A`
- focusing on submission packaging only
- trying to reopen review UI work

If wrong-context drift appears in the first summary, stop and restart the session instead of steering the stale thread.
