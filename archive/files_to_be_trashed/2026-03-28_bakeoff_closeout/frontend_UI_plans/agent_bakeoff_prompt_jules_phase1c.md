# Agent Bake-Off Prompt: Jules Phase1C Cutover Proof Gate

## 1. How To Use This File

Use this file when running the APS Tier1 retrieval-plane Phase1C bake-off in Jules.

Run Round 0 first in a brand-new session on:

- repo: `benjmcd/bakeoff-jules`
- branch: `codex/bakeoff-jules-phase1c`

## 2. Round 0 Dry-Run Prompt

```text
You are participating in a controlled implementation bake-off for APS Tier1 retrieval-plane Phase1C.

Your editable workspace is this GitHub repo and the currently selected branch.

Your owned bake-off output directory is:

./frontend_UI_plans/agent_workspaces/jules/

Milestone-plan directory in this repo:

./next_milestone_plans/

This round is DRY RUN ONLY. Do not implement code yet.

Context sanity gate:

- this round is `APS Tier1 retrieval-plane Phase1C`
- accepted prior work is the Phase1B operator retrieval read path at baseline commit `6f2d80d`
- if your first summary mentions `Phase1A`, `Phase1B`, `Slice 01`, or review UI work as the current task, stop and report wrong-context drift instead of continuing

Treat the following docs as the authority:

- ./frontend_UI_plans/agent_bakeoff_local_setup_phase1c.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_brief.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_scope.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_implementation_blueprint.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_validation_plan.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_submission_checklist.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_rubric.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1c.md
- ./frontend_UI_plans/JULES_GITHUB_START_HERE.md

Hard constraints:

- validate-only cutover proof only
- canonical APS evidence truth remains canonical
- current public routes must remain unchanged
- no hidden flags, headers, or query switches on the public routes
- no new HTTP routes
- no schema/model/Alembic widening
- no review-UI changes
- no embeddings or vector work
- empty runtime must fail closed
- retrieval-not-materialized and partial materialization must fail closed for required run-scoped proof
- never delete/remove files; if removal is unavoidable, move to an archive location instead
- distinguish repo-confirmed facts from assumptions explicitly
- call out likely tech-debt risks instead of silently accepting them

For this dry run, do not modify files. Produce:

1. a concise Phase1C implementation plan
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
Proceed with implementation for APS Tier1 retrieval-plane Phase1C in this GitHub repo and the currently selected branch.

Your owned bake-off output directory is:

./frontend_UI_plans/agent_workspaces/jules/

Implement the bounded Phase1C slice exactly as defined by:

- ./frontend_UI_plans/agent_bakeoff_local_setup_phase1c.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_brief.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_scope.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_implementation_blueprint.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_validation_plan.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_submission_checklist.md
- ./frontend_UI_plans/agent_bakeoff_phase1c_rubric.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1c.md
- ./frontend_UI_plans/JULES_GITHUB_START_HERE.md

Implement only:

- one validate-only cutover-proof service
- one thin tool wrapper under tools/
- one project6.ps1 validate action
- focused isolated proof tests

Preserve these constraints:

- current public routes must remain unchanged
- no hidden cutover switch on the public routes
- no new HTTP routes
- no review-UI changes
- no schema/model/Alembic changes
- no embeddings or vector work
- empty runtime must fail closed
- retrieval-not-materialized and partial materialization must fail closed for required run-scoped proof
- use isolated in-memory or temp-database state for tests and proof
- do not refresh checked-in tests/reports/*.json as part of this slice
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
9. explicit statement on whether project6.ps1 validation was executed
10. explicit statement on whether the review UI regression suite was run

Write your submission artifacts into:

- ./frontend_UI_plans/agent_workspaces/jules/deliverables/
- ./frontend_UI_plans/agent_workspaces/jules/logs/
- ./frontend_UI_plans/agent_workspaces/jules/patches/
- ./frontend_UI_plans/agent_workspaces/jules/screenshots/

If you hit a real blocker, stop and explain it clearly instead of broadening scope.
```
