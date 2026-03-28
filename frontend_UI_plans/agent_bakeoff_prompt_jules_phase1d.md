# Agent Bake-Off Prompt: Jules Phase1D Public Cutover

## 1. How To Use This File

Use this file when running the APS Tier1 retrieval-plane Phase1D bake-off in Jules.

Run Round 0 first in a brand-new session on:

- repo: `benjmcd/bakeoff-jules`
- branch: `codex/bakeoff-jules-phase1d`

Do not publish, merge, or open a PR during Round 0.

## 2. Round 0 Dry-Run Prompt

```text
You are participating in a controlled implementation bake-off for APS Tier1 retrieval-plane Phase1D.

Your editable workspace is this GitHub repo and the currently selected branch.

Your owned bake-off output directory is:

./frontend_UI_plans/agent_workspaces/jules/

Milestone-plan directory in this repo:

./next_milestone_plans/

This round is DRY RUN ONLY. Do not implement code yet. Do not publish or merge a branch in this round.

Context sanity gate:

- this round is `APS Tier1 retrieval-plane Phase1D`
- accepted prior work is the Phase1C validate-only cutover proof gate at baseline commit `2d0dc36`
- if your first summary mentions `Phase1A`, `Phase1B`, `Phase1C` as the current task, `Slice 01`, proof-only work, or review UI work, stop and report wrong-context drift instead of continuing

Treat the following docs as the authority:

- ./frontend_UI_plans/agent_bakeoff_local_setup_phase1d.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_brief.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_scope.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_implementation_blueprint.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_validation_plan.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_submission_checklist.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_rubric.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1c.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1d.md
- ./frontend_UI_plans/JULES_GITHUB_START_HERE.md

Hard constraints:

- public run-scoped cutover only
- canonical APS evidence truth remains canonical
- public response schemas must remain unchanged
- run-scoped public requests must not silently fall back to canonical reads
- omitted-run_id public search must remain unchanged
- operator routes must remain unchanged
- no new HTTP routes
- no hidden flags, headers, query switches, or config switches
- no schema/model/Alembic widening
- no review-UI changes
- no embeddings or vector work
- empty runtime and retrieval-not-materialized proof behavior remain fail-closed
- never delete/remove files; if removal is unavoidable, move to an archive location instead
- distinguish repo-confirmed facts from assumptions explicitly
- call out likely tech-debt risks instead of silently accepting them

For this dry run, do not modify files. Produce:

1. a concise Phase1D implementation plan
2. the exact files you expect to modify
3. the exact new files you expect to add
4. assumptions
5. blockers, risk areas, and tech-debt risks
6. a clear statement confirming whether you can stay within the frozen scope

Write your dry-run notes and planning artifacts into:

- ./frontend_UI_plans/agent_workspaces/jules/logs/
- ./frontend_UI_plans/agent_workspaces/jules/deliverables/

If a repo-confirmed blocker appears to require broader scope, state it explicitly and stop there.
```

## 3. Round 1 Implementation Prompt

```text
Proceed with implementation for APS Tier1 retrieval-plane Phase1D in this GitHub repo and the currently selected branch.

Your owned bake-off output directory is:

./frontend_UI_plans/agent_workspaces/jules/

Do not auto-publish, auto-merge, or open a PR until the implementation and submission artifacts are reviewed.

Implement the bounded Phase1D slice exactly as defined by:

- ./frontend_UI_plans/agent_bakeoff_local_setup_phase1d.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_brief.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_scope.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_implementation_blueprint.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_validation_plan.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_submission_checklist.md
- ./frontend_UI_plans/agent_bakeoff_phase1d_rubric.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1c.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1d.md
- ./frontend_UI_plans/JULES_GITHUB_START_HERE.md

Implement only:

- public run-scoped `content-units` cutover
- public `content-search` cutover only when `run_id` is explicitly supplied
- explicit no-fallback `409` behavior for absent or partial retrieval materialization
- focused isolated route and proof tests

Preserve these constraints:

- public response schemas must remain unchanged
- omitted-run_id search must remain unchanged
- operator routes must remain unchanged
- no new HTTP routes
- no hidden cutover switch
- no review-UI changes
- no schema/model/Alembic changes
- no embeddings or vector work
- use isolated in-memory or temp-database state for tests and proof
- never delete/remove files; if removal is unavoidable, move to an archive location instead

At the end, provide a submission that includes:

1. concise implementation summary
2. changed file list with reasons
3. architecture notes
4. assumptions made
5. risks, tradeoffs, and explicit tech-debt accounting
6. tests added and tests run
7. commands used for validation
8. scope-conformance statement
9. explicit statement on whether the Phase1C proof was rerun after cutover
10. explicit statement on whether the review UI regression suite was run

Write your submission artifacts into:

- ./frontend_UI_plans/agent_workspaces/jules/deliverables/
- ./frontend_UI_plans/agent_workspaces/jules/logs/
- ./frontend_UI_plans/agent_workspaces/jules/patches/
- ./frontend_UI_plans/agent_workspaces/jules/screenshots/

If you hit a real blocker, stop and explain it clearly instead of broadening scope.
```
