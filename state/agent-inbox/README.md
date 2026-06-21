# project6 dual-agent handoff channel (in-repo)

This directory is the **in-repo** IPC handoff channel between the Claude Code orchestrator and the Codex implementer for project6. It was relocated here from a shared external workspace so project6 delegation files live inside the project6 repo (and never collide with unrelated projects).

## Files
- `for-codex.md` — Claude -> Codex. **Overwritten** on every send by the handoff wrapper.
- `for-claude.md` — Codex -> Claude. **Appended** (each Codex reply under a `[From Codex]` header).
- `*-source.md`, `*-followon.md` — Claude's authored handoff drafts (the wrapper wraps `*-source.md` content into `for-codex.md`).
- All of the above ephemeral I/O is gitignored; this README is tracked. The `../ipc-tools/` scripts are local operational tooling (gitignored, present on disk, operated from this machine).

## Tooling (`../ipc-tools/`)
- `handoff_to_codex.sh` — write `for-codex.md` + inject a pickup line into the live Codex Desktop thread.
- `codex_ipc_client.mjs` — IPC injector (called by the wrapper).
- `codex_ipc_session_inspect.mjs` — read-only session inspector.

## Usage (run from the repo root so `git worktree list | head -1` resolves to project6)
```bash
# Send a handoff (full task content passed as the arg; wrapper overwrites for-codex.md):
bash state/ipc-tools/handoff_to_codex.sh --ipc <conversationId> "$(cat state/agent-inbox/<your-source>.md)"

# Read-only inspect of a Codex session:
node state/ipc-tools/codex_ipc_session_inspect.mjs --thread <conversationId>
```

## project6 Codex session
- conversationId: `019edb8d-714a-70f0-bfa0-1e5ad027af23` (implementer; cwd = this repo).
- Treat inbox entries as project6 only if they carry this session id and/or `project6-origin` SHAs.

## Do NOT
- Do not route project6 handoffs through any external/shared inbox (e.g. another project's workspace) — that path is shared with an unrelated agent pair and contaminates reads.
