# Worktree health + cleanup (operational maintenance)

Status: maintenance record + owner-reserved cleanup recipe. Inventory only — this doc deletes nothing.

## Snapshot (2026-06-21)
- **323** git worktrees registered (`git worktree list`). Branch-prefix breakdown: ~247 `codex/`, 7 `feature/`, plus singletons (`claude/`, `docs/`, `fix-*`, `improvement/`, `followup/`, agent-`worktree-*`).
- **20** branches are merged into `project6-origin/main` — their worktrees are safe-to-remove cleanup candidates (removal preserves the branch ref).
- Additional external worktrees exist under `~/.cursor/worktrees/...` (outside the repo `worktrees/` convention).
- The main checkout root is on `codex/root-preserve` (a dirty preserved-state branch), not `main`.

## Risks
- Sprawl: 323 worktrees slow `git worktree`/`status` operations and obscure which lanes are live.
- Orphan/leak risk: external `.cursor` worktrees and detached HEADs accumulate untracked state.
- Convention drift: not all worktrees sit under `<repo>/worktrees/<short-name>`.

## ACTIVE worktrees — DO NOT remove
This list is a point-in-time snapshot — ALWAYS re-verify against `git worktree list` + recent branch activity + the agent inbox before removing anything (step 4 below is authoritative; this list is only a hint).
- `worktrees/sec-live-harden` (`codex/sec-live-harden`) — active Codex lane (M-SEC-LIVE-HARDEN).
- `worktrees/governance-mergegate` (`claude/governance-mergegate`) — Claude governance/hygiene lane (this doc).
- The root checkout on `codex/root-preserve` — owner-reserved (preserved state).
- Worktrees whose branch is already merged to main (e.g. earlier `codex/rc3-*`, `claude/review-thread-fixes`, `claude/sec-live-reconciliation`) are cleanup candidates — but still re-verify per step 4 before removing.

## Safe cleanup recipe (owner-reserved; no auto-delete)
1. Prune stale registrations: `git worktree prune -v`.
2. List merged-branch worktrees: cross-reference `git worktree list` against `git branch --merged project6-origin/main`.
3. For each worktree whose branch is merged AND is not in the ACTIVE list above: `git worktree remove <path>` (preserves the branch ref; add `--force` only if the worktree is dirty and you have verified nothing valuable is uncommitted).
4. Re-verify no other active session owns a worktree before removing it (`git worktree list`, recent branch activity, agent inbox).
5. Leave `.cursor` external worktrees to their owning tool; do not remove from here.

Pruning execution is reserved to the owner: removing a worktree another live session is using would disrupt it. This doc supplies the safe procedure; it does not run it.
