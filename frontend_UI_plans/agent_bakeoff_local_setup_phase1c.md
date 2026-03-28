# Agent Bake-Off Local Setup: APS Tier1 Retrieval Plane Phase1C

## 1. Purpose

This document freezes the exact lane map for the next bounded bake-off slice after the accepted Phase1B operator retrieval read path.

This round is:

- `Phase1C: Validate-Only Public Cutover Proof Gate`

It is not:

- Phase1A retrieval-plane build
- Phase1B operator retrieval read path
- default public cutover
- review UI work

## 2. Canonical Baseline

The source baseline for both lanes is the committed main-repo Phase1B implementation:

- repo root branch: `codex/frontend-ui-bakeoff-setup`
- baseline commit: `6f2d80d`

This is the only approved starting point for the Phase1C round.

## 3. Antigravity Lane

Editable Antigravity lane:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-phase1c`

Expected branch:

- `codex/bakeoff-antigravity-phase1c`

Owned output directory inside the lane:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-phase1c\frontend_UI_plans\agent_workspaces\antigravity`

Required owned subfolders:

- `deliverables\`
- `logs\`
- `patches\`
- `screenshots\`

## 4. Jules Lane

GitHub-safe Jules mirror:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\jules_repo_phase1c`

Expected local branch:

- `codex/bakeoff-jules-phase1c`

Expected remote branch:

- `codex/bakeoff-jules-phase1c`

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
- `next_milestone_plans\2026-03-27_aps_tier1_retrieval_plane_phase1c.md`

Additional live authority surfaces this round:

- `docs\postgres\postgres_status_handoff.md`
- `docs\nrc_adams\nrc_aps_reader_path.md`
- `project6.ps1`
- `backend\app\api\router.py`
- `backend\app\schemas\api.py`
- `backend\app\services\nrc_aps_content_index.py`
- `backend\app\services\aps_retrieval_plane_read.py`

## 6. Session Hygiene

Each tool must start a brand-new task/session for this round.

Wrong-context drift examples:

- describing the task as `Slice 01`
- describing the task as `Phase1A` or `Phase1B`
- proposing a default route flip as part of this slice
- reopening review UI work

If wrong-context drift appears in the first summary, stop and restart the session instead of steering the stale thread.
