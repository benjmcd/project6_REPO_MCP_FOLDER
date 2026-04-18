# Onlook Ops

## Purpose
This is the canonical operator front door for Onlook use in this repo.

Use this document first when you need to:
- test the current Onlook lane
- troubleshoot local Onlook/runtime issues
- audit whether the lane is still in a usable state
- decide which proof or helper to run next
- use Onlook without widening into live static UI changes by accident

This file is an operator guide.
It is not the planning packet, and it is not a blanket approval to promote sandbox work into live authority.

## Authority Map
Use these surfaces in this order:

1. This file for day-to-day operator flow and command selection.
2. [next_milestone_plans/onlook-plan/README.md](../next_milestone_plans/onlook-plan/README.md) for merged lane status, scope, non-claims, and tool inventory.
3. [next_milestone_plans/onlook-plan/strategy.md](../next_milestone_plans/onlook-plan/strategy.md) for boundary and source-of-truth reasoning.
4. [next_milestone_plans/onlook-plan/pilot-plan.md](../next_milestone_plans/onlook-plan/pilot-plan.md) for operating rules and validation rules.
5. [next_milestone_plans/onlook-plan/impl-plan.md](../next_milestone_plans/onlook-plan/impl-plan.md) for concrete implementation/runtime details and exact local commands.
6. [docs/onlook-normalized-smoke.md](./onlook-normalized-smoke.md) for the current-project first gate only.
7. The executable truth in `tools/*`.

## Core Boundaries
- The live shipped review UI remains `backend/app/review_ui/static/*`.
- Onlook should not be treated as an in-place editor for that live static UI by default.
- The default experimental target is a duplicate sandbox app, not `onlook-ui/` directly.
- `onlook-ui/` is the canonical sandbox source.
- `onlook-ui-copy/` is the default ignored scratch target.
- Any later promotion from duplicate to canonical sandbox source is manual and reviewed.
- Any later move from sandbox source into live static UI is a separate explicit decision.

## Execution Surfaces
- Preferred clean execution surface: a fresh worktree from `project6-origin/main`.
- Preferred repo-native runtime root: `backend/app/storage_test_runtime`.
- Canonical local Onlook operator surface: `ext-onlook-fix/`.
- Clean upstream packaging surface: `ext-onlook-pr/`.
- Clean upstream base reference: `ext-onlook/`.

Do not blur those roles:
- `ext-onlook-fix/` is the local solved operator/debug surface.
- `ext-onlook-pr/` is the cleaner upstream packaging proof surface.
- `ext-onlook/` is the clean base reference, not the default solved surface.

## Default Low-Risk Workflow
1. Preflight the current lane:
```powershell
./tools/check-onlook.ps1
```
2. Prepare a clean duplicate target:
```powershell
./tools/prep-onlook-copy.ps1 -TargetDir onlook-ui-copy -CopyLocalEnv
```
3. Prove the duplicate target before import:
```powershell
./tools/run-onlook-sandbox-smoke.ps1 -Profile core -AppDir onlook-ui-copy
```
4. If compare-family coverage matters, use the full profile:
```powershell
./tools/run-onlook-sandbox-smoke.ps1 -Profile full -AppDir onlook-ui-copy
```
5. Import the duplicate target into Onlook.
6. If you need editor-side proof on the duplicate target, run:
```powershell
./tools/run-onlook-operator-proof.ps1 -AppDir onlook-ui-copy
```
7. Review duplicate-to-canonical differences before any manual merge-back:
```powershell
./tools/diff-onlook-copy.ps1 -TargetDir onlook-ui-copy
```

## Direct Canonical Sandbox Workflow
Use this only when direct canonical write-back is intentional.

1. Preflight:
```powershell
./tools/check-onlook.ps1
```
2. Prove the canonical sandbox routes before import:
```powershell
./tools/run-onlook-sandbox-smoke.ps1 -Profile core
```
3. If compare-family coverage matters:
```powershell
./tools/run-onlook-sandbox-smoke.ps1 -Profile full
```
4. Only then import `onlook-ui/` directly.

## Current-Project First Gate
The current-project first gate is separate from the broader duplicate-target operator proof.

Use:
```powershell
./tools/run-onlook-normalized-smoke.ps1
```

This gate is authoritative only for the current active verified pair recorded in:
- [tools/onlook-active-pair.json](../tools/onlook-active-pair.json)

This gate also requires a real `CSB_API_KEY` to reach the local Onlook web runtime.
Preferred local setup:
- store the real key in `ext-onlook-fix/apps/web/client/.env.local`
- let the startup wrapper import `.env` plus `.env.local` into the process before it launches the local Onlook web host

Read the gate semantics in:
- [docs/onlook-normalized-smoke.md](./onlook-normalized-smoke.md)

## Troubleshooting Decision Tree
- If the local Onlook clones, env files, or patch archives look wrong, start with:
```powershell
./tools/check-onlook.ps1
```
- If the expected local operator clones are missing or no longer trustworthy, rebuild them with:
```powershell
./tools/restore-onlook.ps1 -PatchSet local-writeback
./tools/restore-onlook.ps1 -PatchSet upstream-clean
```
- If the current-project first gate fails before or during `sandbox.start`, verify that `ext-onlook-fix/apps/web/client/.env.local` contains a real `CSB_API_KEY`, then rerun the gate from a cold host.
- If you need local Onlook web on a fresh origin instead of sticky browser state:
```powershell
./tools/start-onlook-web.ps1 -Port 3011
```
- If duplicate prep fails, treat that as a duplicate-target or canonical-sandbox-source issue first. Do not jump straight into Onlook import debugging.
- If sandbox smoke fails, treat that as a pre-Onlook blocker for the sandbox app or its runtime inputs.
- If duplicate-target operator proof fails, treat that as an Onlook import/trust/preview/write-back issue on the duplicate path.
- If normalized smoke fails closed, treat that as active-pair provenance or proof-state drift first, not immediate product proof.

## Current Portability Contract
The default no-arg normalized-smoke path is portable only when the active proof contract is backed by tracked repo surfaces and matching local runtime/helper provenance.

Check:
- `tools/onlook-active-pair.json`
- the `sourceLedgerPath` it currently references
- `./tools/check-onlook.ps1 -ShowGateStatusOnly`

Interpretation:
- if `sourceLedgerPath` resolves to tracked repo truth such as `tools/onlook-proof.json`, the default no-arg gate can travel with the repo as long as the local helper fingerprint and runtime-clone state still match
- if `sourceLedgerPath` resolves to ignored local evidence under `archive/onlook-normalized-smoke/...`, the default no-arg gate is only portable to worktrees or machines that still have that exact local archive evidence

Do not describe the default pair as globally portable without checking the current proof contract first.

## What Each Proof Surface Answers
- `./tools/check-onlook.ps1`
  - Is the local operator surface structurally intact?
- `./tools/run-onlook-sandbox-smoke.ps1`
  - Does the sandbox app itself render and navigate correctly before any Onlook import?
- `./tools/run-onlook-operator-proof.ps1`
  - Can Onlook import and operate on the duplicate sandbox target with trusted preview navigation and duplicate-only write-back?
- `./tools/run-onlook-normalized-smoke.ps1`
  - Does the current active verified pair still pass the current-project first gate?

## Non-Claims
- This file does not claim that live static UI promotion is approved.
- This file does not claim that AI/chat features are proven ready.
- This file does not claim portability unless the current active proof contract is backed by tracked repo surfaces and matching local runtime/helper provenance.
- This file does not replace the Onlook plan packet for design intent or non-claims.
