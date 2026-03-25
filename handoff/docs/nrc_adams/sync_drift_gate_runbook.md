# NRC APS Sync Delta/Drift Gate Runbook

> Status note (2026-03-11): current NRC APS status, proof artifacts, closed-layer guidance, and next-step handoff are frozen in [nrc_aps_status_handoff.md](nrc_aps_status_handoff.md). This runbook remains gate-specific/operator-procedural.

## Purpose
This runbook defines the local fail-closed gate for Workstream 2A sync delta/drift artifacts.

The gate validates that each evaluated NRC APS completed run has the required artifact state:
- success artifacts present (`aps_sync_delta`, `aps_sync_drift`), or
- explicit failure artifact state (`aps_sync_drift_failure`) when success artifacts are missing.

## Command
Run from repo root:

```powershell
.\project6.ps1 -Action validate-nrc-aps-sync-drift
```

Direct CLI:

```powershell
py -3.12 tools/nrc_aps_sync_drift_gate.py --report tests/reports/nrc_aps_sync_drift_validation_report.json
```

Optional direct CLI controls:
- `--run-id <id>` (repeatable): validate specific run(s) only.
- `--limit <n>`: validate latest `n` completed NRC APS runs when `--run-id` is not supplied.
- `--allow-empty`: do not fail when no matching runs are found.

## Artifact Schemas and Paths
- `aps.sync_delta.v1` -> `<run_id>_aps_sync_delta_v1.json`
- `aps.sync_drift.v1` -> `<run_id>_aps_sync_drift_v1.json`
- `aps.sync_drift_failure.v1` -> `<run_id>_aps_sync_drift_failure_v1.json`

All artifact files are written to:
- `backend/app/storage/connectors/reports` (or configured storage root equivalent)

## Validation Report
- Path: `tests/reports/nrc_aps_sync_drift_validation_report.json`
- Contains:
  - pass/fail summary
  - per-run checks
  - exact missing/failure reasons
