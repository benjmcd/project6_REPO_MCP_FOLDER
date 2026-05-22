# 961 - Provider-Private Lifecycle Current-Main Sync

## Status

Status: current-main proof checkpoint after the source-directory provider-private lifecycle was extended across the admitted hybrid handoff/export package artifact and package replacement/supersession artifact paths.

Current-main authority: `project6-origin/main` at `7569d4b6 Merge pull request #1596 from benjmcd/codex/l3-hybrid-provider-private-stale-rendered`.

Predecessor checkpoints:

- `959-provider-private-source-directory-use.md`
- `960-main-sync.md`

This checkpoint introduces no route, DTO, database model, migration, service behavior, rendered UI behavior, provider object behavior, connector dispatch, source expansion, RAG/vector/model runtime, public URL/proxy behavior, frontend-only durable authority, or full mockup activation.

## Current-Main Evidence

Merged runtime and rendered-proof PRs after `960-main-sync.md`:

- PR `#1592`: source-directory package provider-private rendered family selector and live proof.
- PR `#1593`: package provider-private stale-authority rendered rejection.
- PR `#1594`: package provider-private replay and use-after-revoke rendered rejection.
- PR `#1595`: hybrid provider-private replay and use-after-revoke rendered rejection.
- PR `#1596`: hybrid provider-private stale-authority rendered rejection.

The admitted provider-private lifecycle now has rendered live-server proof for:

- source-directory hybrid handoff/export package artifact prepare/status/use/revoke;
- source-directory package replacement/supersession artifact prepare/status/use/revoke;
- durable receipt and audit state;
- redacted server-owned use;
- stale-authority rejection for package commit basis drift;
- stale-authority rejection for hybrid package payload hash drift;
- single-use replay rejection;
- use-after-revoke rejection;
- no raw provider URL, raw provider token, public URL, public proxy, provider object write/copy/mutation, arbitrary connector dispatch, credential exposure, source expansion, RAG/vector/model runtime, frontend-only durable authority, or full mockup activation.

## Verification

Focused verification run before PR `#1596` merged:

```powershell
python -m pytest ./backend/tests/test_layer3_source_directory_vector_retrieval.py -q
npx playwright test ./e2e/layer3-workbench.spec.js --grep "proves source-directory scan to hybrid handoff delivery live server path" --project=chromium
npx playwright test ./e2e/layer3-workbench.spec.js --grep "proves source-directory scan to hybrid handoff delivery live server path" --project=chromium --headed
python ./tools/l3-progress-check.py
git diff --check
```

Observed result:

```yaml
focused_pytest: 24 passed
playwright_chromium_headless: 1 passed
playwright_chromium_headed: 1 passed
l3_progress_check: PASS
git_diff_check: PASS
remote_pr_1596_checks:
  backend-layer3-api: success
  test: success
```

## What Comes Next

Immediate next pass:

1. Run the bounded operator runbook from `952-bounded-trial-checkpoint-runbook.md` against current main if a full readiness recheck is needed.
2. Confirm the provider-private lifecycle proof remains visible in the source-directory live path after the next current-main refresh.
3. Stop if the next action would require product authority beyond the admitted provider-private/redacted lifecycle.

Mid-term remaining passes:

1. Record any new provider-private artifact family only through a separate freeze naming the exact artifact family, authority source, routes, controls, rollback, and headed/headless proof.
2. Re-audit provider-public URL, public proxy, connector dispatch, real provider object operations, credentials, source expansion, RAG/vector/model runtime, and Analysis Environment interactivity as separate blocked or intentionally excluded tracks.
3. Keep current bounded trial and mockup activation evidence synchronized after any further rendered-path change.

Long-term target:

1. Maintain a governed provider-private/redacted delivery lifecycle for the bounded Layer 3 source-directory package/handoff path.
2. Classify every critical mockup operator journey as live, read-only, intentionally excluded, or explicitly blocked from current-main evidence.
3. Admit full mockup activation only after a separate final readiness audit proves all blockers closed and records rollback/no-go authority.
