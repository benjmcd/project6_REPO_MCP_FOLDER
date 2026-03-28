# Agent Bake-Off Local Setup: APS Tier1 Retrieval Plane Phase1D

## 1. Purpose

This document freezes the exact lane map for the next bounded bake-off slice after the accepted Phase1C validate-only cutover proof gate.

This round is:

- `Phase1D: Public Run-Scoped Retrieval Cutover`

It is not:

- Phase1A retrieval-plane build
- Phase1B operator retrieval read path
- Phase1C proof-only work
- review UI work
- omitted-`run_id` search redesign

## 2. Canonical Baseline

The source baseline for both lanes is the committed main-repo Phase1C implementation:

- repo root branch: `codex/frontend-ui-bakeoff-setup`
- baseline commit: `2d0dc36`

This is the only approved starting point for the Phase1D round.

## 3. Antigravity Lane

Editable Antigravity lane:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-phase1d`

Expected branch:

- `codex/bakeoff-antigravity-phase1d`

Owned output directory inside the lane:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\.claude\worktrees\bakeoff-antigravity-phase1d\frontend_UI_plans\agent_workspaces\antigravity`

Required owned subfolders:

- `deliverables\`
- `logs\`
- `patches\`
- `screenshots\`

## 4. Jules Lane

GitHub-safe Jules mirror:

- `C:\Users\benny\OneDrive\Desktop\project6_REPO_MCP_FOLDER\frontend_UI_plans\jules_repo_phase1d`

Expected local branch:

- `codex/bakeoff-jules-phase1d`

Expected remote branch:

- `codex/bakeoff-jules-phase1d`

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
- `next_milestone_plans\2026-03-27_aps_tier1_retrieval_plane_phase1d.md`

Additional live authority surfaces this round:

- `docs\postgres\postgres_status_handoff.md`
- `docs\nrc_adams\nrc_aps_reader_path.md`
- `project6.ps1`
- `backend\app\api\router.py`
- `backend\app\schemas\api.py`
- `backend\app\services\nrc_aps_content_index.py`
- `backend\app\services\aps_retrieval_plane_read.py`
- `backend\app\services\aps_retrieval_plane_cutover_validation.py`

## 6. Session Hygiene

Each tool must start a brand-new task or session for this round.

Wrong-context drift examples:

- describing the task as `Slice 01`
- describing the task as `Phase1A`, `Phase1B`, or `Phase1C`
- proposing another validate-only proof gate instead of live cutover
- reopening review UI work
- broadening omitted-`run_id` search into a larger redesign

If wrong-context drift appears in the first summary, stop and restart the session instead of steering the stale thread.
