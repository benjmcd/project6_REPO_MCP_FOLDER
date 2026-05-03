# Harness Validate Inventory

This inventory classifies the root `project6.ps1` action surface so harness work can distinguish validation-only intent from setup, refresh, artifact generation, runtime mutation, and aggregate orchestration.

Scope:

- Authority is the current tracked `project6.ps1` in the focused worktree.
- This is a wrapper-level inventory only. Script-internal behavior still requires direct audit of the target Python tool or test before behavior changes.
- This file is not a status ledger and does not claim that a command is safe against shared runtime state unless the wrapper proves that property.
- The current wrapper has 38 `ValidateSet` entries and 38 matching `switch` cases.

## Categories

| Category | Meaning |
| --- | --- |
| `setup-service` | Installs dependencies, migrates databases, starts services, or otherwise prepares operator/runtime state. |
| `live-probe` | Talks to a running API, live service, or external source. It may be read-only from the repo's perspective, but it is not isolated. |
| `report-gate` | Runs a validator or gate and passes an explicit report path, usually under `tests/reports`. Treat as report-producing unless the target script proves otherwise. |
| `artifact-build` | Builds, refreshes, compares, or writes derived corpus/proof/report artifacts. |
| `runtime-proof` | Uses isolated runtime tiers to prove behavior and may create runtime state as part of the proof. |
| `compare-eval` | Runs a comparison or evaluation helper whose write behavior is delegated to the target script and arguments. |
| `aggregate` | Orchestrates several actions or tool classes and must be treated as broad mutable workflow. |

## Action Inventory

| Action | Category | Wrapper evidence | Handling posture |
| --- | --- | --- | --- |
| `setup` | `setup-service` | Runs `python -m pip install -r requirements.txt`. | Dependency setup, not validation-only. |
| `migrate` | `setup-service` | Runs Alembic upgrade against Tier 1 database. | Database-mutating migration. |
| `migrate-tier1-postgres` | `setup-service` | Runs SQLite-to-PostgreSQL migration and can pass `--truncate-target`. | Data migration; require explicit operator ownership. |
| `start-api` | `setup-service` | Starts the API foreground under Tier 1 env. | Service process, not a validation command. |
| `status` | `live-probe` | Calls `$BaseUrl/health`. | Read-only health probe against a running API. |
| `validate-sciencebase-live` | `live-probe` | Runs the live validator against `$BaseUrl`. | Live/API dependent; not isolated by wrapper. |
| `validate-live` | `live-probe` | Runs the live validator against `$BaseUrl`. | Live/API dependent; not isolated by wrapper. |
| `validate-nrc-aps` | `live-probe` | Runs `run_nrc_aps_live_validation.py` under Tier 1 env. | Live/runtime dependent; audit target script before treating as pure validate-only. |
| `collect-nrc-aps-live-batch` | `artifact-build` | Passes `--batch-root` under `backend/app/storage/connectors/reports/nrc_aps_live_batches`. | Collects live batch artifacts; not validation-only. |
| `build-nrc-aps-replay-corpus` | `artifact-build` | Runs replay gate `build` with `--out` corpus and `--diff-report`. | Writes or refreshes fixture/report artifacts. |
| `validate-nrc-aps-replay` | `report-gate` | Runs replay gate `validate` with `--report`. | Report-producing validation under Tier 2. |
| `check-nrc-aps-replay-corpus` | `report-gate` | Runs replay gate `check` with `--diff-report`. | Report-producing corpus check under Tier 2. |
| `validate-nrc-aps-sync-drift` | `report-gate` | Runs sync-drift gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-safeguards` | `report-gate` | Runs safeguard gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-artifact-ingestion` | `report-gate` | Runs artifact-ingestion gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-content-index` | `report-gate` | Runs content-index gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-evidence-bundle` | `report-gate` | Runs evidence-bundle gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-evidence-citation-pack` | `report-gate` | Runs evidence-citation-pack gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-evidence-report` | `report-gate` | Runs evidence-report gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-evidence-report-export` | `report-gate` | Runs evidence-report-export gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-evidence-report-export-package` | `report-gate` | Runs evidence-report-export-package gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-context-packet` | `report-gate` | Runs context-packet gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-context-dossier` | `report-gate` | Runs context-dossier gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-deterministic-insight-artifact` | `report-gate` | Runs deterministic-insight-artifact gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-deterministic-challenge-artifact` | `report-gate` | Runs deterministic-challenge-artifact gate with `--report`. | Report-producing validation under Tier 2. |
| `validate-nrc-aps-deterministic-challenge-review-packet` | `report-gate` | Runs deterministic-challenge-review-packet gate with `--report`. | Report-producing validation under Tier 2. |
| `refresh-nrc-aps-review-gate-reports` | `artifact-build` | Requires `NrcApsRunId` and runs refresh helper. | Refreshes derived gate reports; not validation-only. |
| `refresh-nrc-aps-validate-only-gates` | `artifact-build` | Requires `NrcApsRunId` and runs refresh helper under Tier 2. | Refreshes derived validate-only gate artifacts; not validation-only. |
| `validate-nrc-aps-validate-only-gates` | `report-gate` | Runs validate-only gates gate with `--report` by default and optional `--run-id`; the target gate also accepts `--no-report`. | Use `--no-report` when the lane needs artifact-free validation. |
| `validate-nrc-aps-promotion` | `report-gate` | Resolves live batch manifest and policy, then passes `--report`. | Depends on batch manifest; report-producing under Tier 2. |
| `validate-nrc-aps-retrieval-cutover` | `live-probe` | Requires `NrcApsRunId`, optionally passes query, and runs under Tier 1. | Runtime/API cutover validation; audit target script before changing behavior. |
| `compare-nrc-aps-promotion-policy` | `compare-eval` | Requires tuned policy and rationale, then passes `--out-dir`. | Comparison artifact workflow under Tier 2. |
| `prove-nrc-aps-document-processing` | `runtime-proof` | Passes proof and gate report paths under Tier 3. | Proof workflow; may create runtime state and report artifacts. |
| `compare-nrc-aps-candidate-b` | `compare-eval` | Delegates to candidate-B compare runner with pass-through args. | Audit target script and args before assuming write behavior. |
| `gate-nrc-aps` | `aggregate` | Runs many pytest files, then many gates with `--report`; includes a negative test that persists synthetic same-id dossier artifacts. | Broad runtime/report workflow; do not run against shared state casually. |
| `eval-attached` | `compare-eval` | Runs attached dataset eval under Tier 3. | Evaluation workflow; audit target script before assuming write behavior. |
| `bootstrap-sciencebase-live` | `aggregate` | Installs requirements, migrates, starts API, waits for health, runs live validator, then stops the process. | Bootstrap workflow; owns service lifecycle during run. |
| `all` | `aggregate` | Installs requirements, migrates, starts API, waits for health, runs live validator, then stops the process. | Broad setup plus live validation workflow. |

## Guardrails For Next Behavior Work

- Do not infer pure validation behavior from an action name. Use the table above plus direct target-script audit.
- Treat every `--report`, `--diff-report`, `--out`, `--out-dir`, `--batch-root`, proof report, and refresh path as a potential artifact write until the target script proves otherwise.
- Treat Tier 2 and Tier 3 actions as isolated-runtime candidates, not as shared-runtime-safe commands by default.
- Keep `refresh-*`, `prove-*`, `build-*`, `collect-*`, `gate-nrc-aps`, `bootstrap-sciencebase-live`, and `all` outside validate-only automation unless a lane explicitly owns their runtime and artifacts.
- The narrowest next behavior lane should start with one command family. After `validate-nrc-aps-validate-only-gates`, continue only when a target script audit proves whether its report output is intentional or avoidable.
