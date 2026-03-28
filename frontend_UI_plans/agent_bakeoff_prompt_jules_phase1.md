# Agent Bake-Off Prompt: Jules Phase1 Retrieval Plane

## 1. How To Use This File

Use this file when running the APS Tier1 retrieval-plane Phase1A bake-off in the Jules GitHub mirror.

Recommended flow:

1. use the prepared GitHub branch defined in `agent_bakeoff_local_setup_phase1.md`
2. start a brand-new Jules session for this milestone
3. verify the very first Jules summary explicitly names `APS Tier1 retrieval-plane Phase1A`
4. if Jules mentions `Slice 01`, `review UI deliverables`, or another older milestone, stop and restart with a fresh session
5. run the Round 0 dry-run prompt first
6. review the resulting plan for scope drift
7. if acceptable, run the Round 1 implementation prompt

## 2. Round 0 Dry-Run Prompt

Paste the following into Jules on the GitHub branch `codex/bakeoff-jules-phase1`:

```text
You are participating in a controlled implementation bake-off for APS Tier1 retrieval-plane Phase1A.

Your editable workspace is this GitHub repo and the currently selected branch.

Your owned bake-off output directory is:

./frontend_UI_plans/agent_workspaces/jules/

Milestone-plan directory in this repo:

./next_milestone_plans/

Use the output directory for:

- deliverables/
- logs/
- patches/
- screenshots/

This round is DRY RUN ONLY. Do not implement code yet.

Context sanity gate:

- this round is `APS Tier1 retrieval-plane Phase1A`
- the accepted review UI baseline is prior context only
- if you find yourself summarizing `Slice 01`, `review UI deliverables`, or prior bake-off packaging work as the task, stop immediately and report wrong-context drift instead of continuing

Treat the following docs as the authority for scope and implementation shape:

- ./frontend_UI_plans/agent_bakeoff_local_setup_phase1.md
- ./frontend_UI_plans/agent_bakeoff_phase1_brief.md
- ./frontend_UI_plans/agent_bakeoff_phase1_scope.md
- ./frontend_UI_plans/agent_bakeoff_phase1_implementation_blueprint.md
- ./frontend_UI_plans/agent_bakeoff_phase1_validation_plan.md
- ./frontend_UI_plans/agent_bakeoff_phase1_submission_checklist.md
- ./frontend_UI_plans/agent_bakeoff_phase1_rubric.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1.md
- ./frontend_UI_plans/JULES_GITHUB_START_HERE.md

Hard constraints:

- additive only
- canonical APS evidence truth remains canonical
- no public API or review-UI expansion
- no default read-path cutover
- no embeddings or vector work
- validate-only parity logic must fail closed on empty scope
- follow these repo guardrails:
  - never delete/remove files; if removal is unavoidable, move to an archive location instead
  - keep validation/proof behavior validate-only and fail closed on empty runtime
  - prefer the narrowest correct change and stop on repo-confirmed blockers
  - distinguish repo-confirmed facts from assumptions explicitly
- explicitly call out likely tech-debt risks rather than silently accepting them

Carry-forward regression guardrail:

- do not regress the currently validated review UI baseline if you touch shared code

For this dry run, do not modify files. Produce:

1. a concise Phase1A implementation plan
2. the exact files you expect to modify
3. the exact new files you expect to add
4. assumptions
5. likely blockers, risk areas, and tech-debt risks
6. a clear statement confirming whether you can stay within the frozen scope

Write your dry-run notes and planning artifacts into:

- ./frontend_UI_plans/agent_workspaces/jules/logs/
- ./frontend_UI_plans/agent_workspaces/jules/deliverables/

If a repo-confirmed blocker appears to require broader scope, state it explicitly and stop there.
```

## 3. Round 1 Implementation Prompt

Use this only after the dry-run output is acceptable.

```text
Proceed with implementation for APS Tier1 retrieval-plane Phase1A in this GitHub repo and the currently selected branch.

Your owned bake-off output directory is:

./frontend_UI_plans/agent_workspaces/jules/

Milestone-plan directory in this repo:

./next_milestone_plans/

Use the output directory for:

- deliverables/
- logs/
- patches/
- screenshots/

Implement the bounded Phase1A slice exactly as defined by:

- ./frontend_UI_plans/agent_bakeoff_phase1_brief.md
- ./frontend_UI_plans/agent_bakeoff_phase1_scope.md
- ./frontend_UI_plans/agent_bakeoff_phase1_implementation_blueprint.md
- ./frontend_UI_plans/agent_bakeoff_phase1_validation_plan.md
- ./frontend_UI_plans/agent_bakeoff_phase1_submission_checklist.md
- ./frontend_UI_plans/agent_bakeoff_phase1_rubric.md
- ./next_milestone_plans/2026-03-27_aps_tier1_retrieval_plane_phase1.md
- ./frontend_UI_plans/JULES_GITHUB_START_HERE.md

Implement only:

- additive retrieval-plane migration/model
- retrieval-plane contract/source-signature logic
- deterministic run-scoped derivation/materialization service
- validate-only parity comparison service
- focused retrieval-plane tests

Preserve these constraints:

- no public API additions
- no review-UI changes
- no read-path cutover
- no embeddings/vector work
- no artifact generation
- no silent fallback to document-row diagnostics authority
- follow these repo guardrails:
  - never delete/remove files; if removal is unavoidable, move to an archive location instead
  - keep validation/proof behavior validate-only and fail closed on empty runtime
  - prefer the narrowest correct change and stop on repo-confirmed blockers
  - distinguish repo-confirmed facts from assumptions explicitly

Important implementation requirements:

- keep the code modular and non-fragile
- follow the implementation blueprint for file/module boundaries
- keep the retrieval plane clearly derived, never canonical
- do not make Postgres-specific indexing/ranking the center of this round
- if shared code paths are touched, preserve the validated review UI baseline
- if the task framing drifts back to `Slice 01` or prior review-UI deliverables, stop and report wrong-context drift instead of continuing

At the end, provide a submission that includes:

1. concise implementation summary
2. changed file list with reasons
3. architecture notes
4. assumptions made
5. risks, tradeoffs, and explicit tech-debt accounting
6. tests added and tests run
7. commands used for validation
8. scope-conformance statement
9. any parity examples or structured evidence you produced

Write your submission artifacts into:

- ./frontend_UI_plans/agent_workspaces/jules/deliverables/
- ./frontend_UI_plans/agent_workspaces/jules/logs/
- ./frontend_UI_plans/agent_workspaces/jules/patches/
- ./frontend_UI_plans/agent_workspaces/jules/screenshots/

If you hit a real blocker, stop and explain it clearly instead of broadening scope.
```
