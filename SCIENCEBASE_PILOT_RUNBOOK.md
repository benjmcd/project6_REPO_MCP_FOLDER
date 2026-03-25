# ScienceBase v1.3.3 Pilot Runbook

## Purpose
Operational runbook for the Annual MCS pilot gate using the public-read ScienceBase connector.

## Preconditions
- API is running with migrations applied through `0006_connector_run_core_counters`.
- ScienceBase connectivity is available from the API runtime.
- Pilot scope is Annual MCS only (`mcs_release_mode=annual_release`).

## Run Submission and Replay
1. Submit via `POST /api/v1/connectors/sciencebase-mcs/runs` with `Idempotency-Key`.
2. On client retry:
   - same key + same payload returns existing run.
   - same key + different payload returns `409`.
3. Poll `GET /api/v1/connectors/runs/{id}` until terminal.

## Cancellation and Resume
1. Cancel with `POST /api/v1/connectors/runs/{id}/cancel`.
2. Wait for run status `cancelled`.
3. Resume with `POST /api/v1/connectors/runs/{id}/resume`.
4. Validate resumed run reaches terminal without non-terminal leftovers.

## Lease Conflict Handling
1. If run `error_summary=lease_conflict`, inspect `GET /runs/{id}/events`.
2. Confirm only one active executor instance owns the lease.
3. Resume the run once lease contention is resolved.

## Budget Exhaustion Handling
1. If `budget_blocked_count > 0` or `budget_summary.budget_exhausted=true`, run completed with budget limits hit.
2. Increase `max_run_bytes` and/or `max_file_bytes` in next submission when appropriate.
3. Keep previous run for audit; do not mutate historical artifacts.

## Reconciliation Interpretation
- Reconciliation-only statuses (`missing_upstream`, `removed_from_item`, `superseded`, `withdrawn`, `out_of_scope`) are terminal and do not enter downloader/ingest.
- Review `reconciliation_summary` and `targets_failures.csv` for operator actions.

## Report Triage Order
1. `GET /api/v1/connectors/runs/{id}` for top-level status and counters.
2. `GET /api/v1/connectors/runs/{id}/events` for stage timeline and reason codes.
3. `GET /api/v1/connectors/runs/{id}/reports` and inspect:
   - `run_summary.json`
   - `targets_failures.csv`
   - `targets_selected.csv`
   - `versioning_decisions.csv`

## Live Pilot Gate
Run:

```powershell
py -3.12 tools/run_sciencebase_live_pilot_validation.py --base-url http://127.0.0.1:8000 --consecutive-runs 3 --timeout-seconds 600
```

Gate passes only if:
- three consecutive suite cycles pass,
- no run is stuck/non-terminal,
- operator surfaces are complete (`/runs`, `/targets`, `/events`, `/reports`),
- at least one run in the gate window proves conditional no-op through either:
  - `not_modified_remote` (HTTP 304), or
  - `skipped_unchanged_after_conditional_revalidate` (conditional request sent, upstream returned unchanged content with HTTP 200).

Validator JSON summary fields:
- `failed_cycles`: suite cycles that had one or more failed scenarios.
- `missing_conditional_noop_gate`: true when no accepted conditional no-op evidence was observed.
- `failed_gate_checks`: aggregate gate failure count (`failed_cycles` plus conditional-noop gate miss).

Note:
- The live validator attempts bounded automatic resume for runs that finish with retryable non-terminal targets before deciding pass/fail.

## Freeze/Tag
After gate pass:
1. Freeze connector changes.
2. Tag release `v1.3.3`.
3. Record pilot evidence bundle (validator output + report references).
