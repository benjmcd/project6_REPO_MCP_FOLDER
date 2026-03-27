# Agent Bake-Off Prompt: Jules Phase1B Retrieval Read Path

## 1. How To Use This File

Use this file when running the APS Tier1 retrieval-plane Phase1B bake-off in Jules.

Run Round 0 first in a brand-new session on:

- repo: `benjmcd/bakeoff-jules`
- branch: `codex/bakeoff-jules-phase1b`

## 2. Round 0 Dry-Run Prompt

```text
You are participating in a controlled implementation bake-off for APS Tier1 retrieval-plane Phase1B.

Your editable workspace is this GitHub repo and the currently selected branch.

Your owned bake-off output directory is:

./frontend_UI_plans/agent_workspaces/jules/

Milestone-plan directory in this repo:

./next_milestone_plans/

This round is DRY RUN ONLY. Do not implement code yet.

Context sanity gate:

- this round is `APS Tier1 retrieval-plane Phase1B`
- accepted prior work is the Phase1A retrieval foundation at baseline commit `927c194`
- if your first summary mentions `Phase1A`, `Slice 01`, or review UI work as the current task, stop and report wrong-context drift instead of continuing

Treat the following docs as the authority:

- ./frontend_UI_plans/agent_bakeoff_local_setup_phase1b.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_brief.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_scope.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_implementation_blueprint.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_validation_plan.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_submission_checklist.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_rubric.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1.md
- ./frontend_UI_plans/JULES_GITHUB_START_HERE.md

Hard constraints:

- additive only
- canonical APS evidence truth remains canonical
- operator-only retrieval routes only; existing public routes must remain unchanged
- `operator-only` means route classification only; do not introduce auth, permissions, or session-model work
- no default read-path cutover
- no review-UI changes
- no schema widening unless a repo-confirmed blocker proves reuse impossible
- no embeddings or vector work
- retrieval empty scope must fail closed
- no model or Alembic migration changes unless a repo-confirmed blocker proves they are required
- never delete/remove files; if removal is unavoidable, move to an archive location instead
- distinguish repo-confirmed facts from assumptions explicitly
- call out likely tech-debt risks instead of silently accepting them

For this dry run, do not modify files. Produce:

1. a concise Phase1B implementation plan
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
Proceed with implementation for APS Tier1 retrieval-plane Phase1B in this GitHub repo and the currently selected branch.

Your owned bake-off output directory is:

./frontend_UI_plans/agent_workspaces/jules/

Implement the bounded Phase1B slice exactly as defined by:

- ./frontend_UI_plans/agent_bakeoff_local_setup_phase1b.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_brief.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_scope.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_implementation_blueprint.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_validation_plan.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_submission_checklist.md
- ./frontend_UI_plans/agent_bakeoff_phase1b_rubric.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1.md
- ./frontend_UI_plans/JULES_GITHUB_START_HERE.md

Implement only:

- one retrieval-plane read service over `aps_retrieval_chunk_v1`
- one operator-only retrieval content-units endpoint
- one operator-only retrieval content-search endpoint
- focused parity and fail-closed tests

Preserve these constraints:

- existing public content-search and content-units routes must remain unchanged
- reuse existing request and response schemas if at all possible
- `operator-only` means route classification only; do not introduce auth, permissions, or session-model work
- no review-UI changes
- no default cutover
- no embeddings or vector work
- no hidden fallback from retrieval route to canonical route
- no model or Alembic migration changes unless a repo-confirmed blocker proves they are required
- never delete/remove files; if removal is unavoidable, move to an archive location instead

Required endpoint routes:

- GET /api/v1/connectors/runs/{connector_run_id}/_operator/retrieval-content-units
- POST /api/v1/connectors/nrc-adams-aps/_operator/retrieval-content-search

Required behavioral rules:

- list order must match the frozen Phase1B ordering rules
- search token and sort semantics must match the frozen Phase1B ordering rules
- retrieval empty scope must fail closed
- retrieval empty scope must return HTTP 409 with explicit retrieval-not-materialized detail
- use isolated in-memory or temp-database state for tests; do not rely on shared checked-in runtime state
- if the task framing drifts back to Phase1A or review UI work, stop and report wrong-context drift

At the end, provide a submission that includes:

1. concise implementation summary
2. changed file list with reasons
3. architecture notes
4. assumptions made
5. risks, tradeoffs, and explicit tech-debt accounting
6. tests added and tests run
7. commands used for validation
8. scope-conformance statement
9. explicit statement on whether the review UI regression suite was run

Write your submission artifacts into:

- ./frontend_UI_plans/agent_workspaces/jules/deliverables/
- ./frontend_UI_plans/agent_workspaces/jules/logs/
- ./frontend_UI_plans/agent_workspaces/jules/patches/
- ./frontend_UI_plans/agent_workspaces/jules/screenshots/

If you hit a real blocker, stop and explain it clearly instead of broadening scope.
```
