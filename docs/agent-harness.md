# Agent Harness Map

Use this file after `AGENTS.md` when you need the shortest command-oriented path through the repo. It is not a status ledger and does not override source files, tests, CI, or lane-specific docs.

## Source Of Truth

1. Current focused worktree plus `project6-origin/main`.
2. Actual source, tests, scripts, and CI.
3. Tracked docs that declare their scope.
4. Generated navigation only when fresh enough for the task.
5. Archives, exports, and session logs only as historical evidence.

Before implementation, create a clean lane from current `project6-origin/main`. Do not use the dirty root checkout as implementation authority.

## First Commands

```powershell
git fetch project6-origin main
git status --short --branch
```

If editing, use a fresh worktree and unique branch:

```powershell
git worktree add ./worktrees/<lane-name> -b codex/<lane-name> project6-origin/main
cd ./worktrees/<lane-name>
git status --short --branch
```

Use compact lane names such as `harness-entry-p01`. Do not reuse worktrees from unrelated Layer3 or NRC APS lanes.

## Root Scripts

The root `package.json` exposes browser and harness entry points:

```powershell
npm run test:e2e
npm run test:e2e:headed
npm run test:layer3-api
npm run harness:review:urls
npm run harness:review:discover
```

Use `npm run test:e2e -- --list` when you only need to prove Playwright discovery. Run headed and headless browser checks when UI behavior changed.

## Review UI Runtime

The canonical shell-neutral review UI helper is:

```powershell
python ./tools/nrc_ui_launch.py discover
python ./tools/nrc_ui_launch.py serve --latest
python ./tools/nrc_ui_launch.py verify --latest
python ./tools/nrc_ui_launch.py urls
```

It prints the selected run id, review root, runtime root, database, storage root, and base URL. Treat stale sibling-worktree runtime selection as unsafe unless explicitly passed and verified.

## Validation Rules

Pick checks based on touched files:

- Package/scripts/docs: `npm run test:e2e -- --list`, `npm run harness:review:urls`, `git diff --check`.
- Layer3 API surface: `npm run test:layer3-api`.
- Browser/UI behavior: `npm run test:e2e` and a headed slice when practical.
- JSON manifests: `python -m json.tool <file>`.

Validation-only actions must fail closed on missing runtime state and must not seed or generate runtime artifacts unless the command explicitly declares that behavior.

## Non-Interference

- Recheck open PRs and `project6-origin/main` before creating, pushing, or merging.
- Avoid shared ports when another session may be running browser/API checks.
- Do not run `refresh-*`, `prove-*`, or broad `gate-*` commands against shared runtime state unless the lane explicitly owns that state.
- Keep harness work out of `next_milestone_plans/` unless a later scope proves the status/control packet must change.

## Closeout

Before PR closeout:

```powershell
git diff --check
git status --short --branch
gh pr view <number> --json state,isDraft,mergeStateStatus,statusCheckRollup,comments,reviews,url
```

Do not merge until required checks pass and review/comment surfaces have no unresolved action items.
