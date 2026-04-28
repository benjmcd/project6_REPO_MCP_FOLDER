# Project6 Agent Harness

This repository is a Python/FastAPI project with SQLAlchemy-backed workflows, NRC APS review tooling, Layer 3 workbench surfaces, and frontend review pages under `backend/app/review_ui/static`.

Use this file as the stable map. Do not turn it into a full project manual. Prefer focused source reads, tracked docs, generated maps, and executable checks over broad context loading.

## Authority Order

1. Live git authority: the focused worktree plus `project6-origin/main`.
2. Actual source files, tests, scripts, and CI configuration.
3. Tracked planning/status docs such as `README.md`, `docs/`, `next_milestone_plans/`, and `frontend_UI_plans/`.
4. Generated navigation aids such as `.codesight/`, when present and fresh.
5. Archive/session/export artifacts only as historical evidence, never as current implementation truth unless revalidated.

Keep repo-confirmed facts, runtime/operator state, planning claims, and inference separate in reports and closeouts.

## Required First Pass

- Start from a clean branch/worktree based on current `project6-origin/main` for implementation work.
- Treat the root checkout as preserved context if it is dirty; do not use it as implementation authority.
- Run `git fetch project6-origin main --prune`, then compare `HEAD` and `project6-origin/main` before editing.
- Read the relevant source files before implementing. Generated maps and docs are navigation aids, not substitutes for source.
- If a manifest or index is involved, first determine whether it is exhaustive or intentionally scoped. Validate declared entries and classify undeclared nearby files as intentional exclusions or real drift.

## Codesight Navigation

Codesight is optional but useful for orientation on large tasks.

- If `.codesight/wiki/index.md` and `.codesight/CODESIGHT.md` exist and are current enough for the task, read the wiki index first, then only the relevant article(s), then the source files.
- If `.codesight/` is missing or obviously stale and project-wide orientation is needed, regenerate it from the repo root with the lightest sufficient command:
  - `npx codesight`
  - `npx codesight --wiki`
- Use `npx codesight --init` or, if globally installed, `codesight --init`, only when intentionally scaffolding agent config. Do not overwrite the maintained root `AGENTS.md` without review.
- Do not run Codesight just because it exists. For narrow source-local tasks, inspect the source and tests directly.
- Treat generated counts, route lists, and schema summaries as hints. Re-check source before making claims or edits.

## Editing Rules

- Prefer the narrowest correct change.
- Use `apply_patch` for manual edits; keep large changes split into reviewable chunks.
- Re-read edited lines immediately after each edit.
- Never delete/remove files. If a file must be retired, move it into the appropriate repo archive area with clear reasoning.
- Do not modify files outside this workspace without explicit user permission.
- Do not use `rg`; use git-aware searches or PowerShell alternatives.
- Keep Windows path constraints in mind: shallow paths, compact kebab-case names, no unnecessary nesting, and relative paths in commands where possible.

## Validation

- Choose targeted checks based on the touched surface.
- `project6.ps1` is the repo-specific command entrypoint for setup, API launch, NRC APS gates, and proof runs; inspect its action list before inventing new commands.
- For backend/API work, prefer focused `python -m pytest ...` slices before broad suites.
- For UI/browser work, use both headed and headless Chrome when practical and compare results.
- For JSON manifests, run `python -m json.tool <file>`.
- Run `git diff --check` before committing.
- Validation commands must not seed, mutate, or generate runtime artifacts unless the task explicitly requires that behavior.
- Use isolated runtime state where possible; do not rely on shared seeded state as proof.

## Layer 3 And Planning Docs

- The Layer 3 planning/progress surfaces live primarily under `next_milestone_plans/`.
- Keep `next_milestone_plans/layer3_progress_manifest.json`, `next_milestone_plans/layer3_workbench_proof_manifest.json`, and `next_milestone_plans/layer3_progress_board.md` aligned when a Layer 3 planning or implementation tranche changes their claims.
- Do not upgrade planning language into implementation truth until the code, tests, merge state, and docs all support that claim.
- Keep current live behavior separate from target-state design in docs and reports.

## Git And PR Workflow

- Avoid parallel git/GitHub operations.
- Do not reset, stash, force-push, or rewrite preserved user work unless explicitly asked.
- Before PR closeout, verify the changed-file set, checks, review/comment threads, and current merged `main` state.
- If GitHub comments identify a real issue, address the narrow issue in a fresh follow-up lane rather than broadening scope opportunistically.

## What Belongs Elsewhere

- Detailed architecture, product behavior, and active milestones belong in tracked docs under `docs/`, `next_milestone_plans/`, or focused planning files.
- Repeatedly enforced style or architecture rules should become tests, linters, scripts, or checklist docs instead of growing this file.
- Tool-specific generated files such as `CLAUDE.md`, `codex.md`, or `.cursorrules` should not become independent sources of truth. If needed, keep them as thin pointers to this file or regenerate them deliberately.
