# NRC APS Safeguard Gate Runbook

> Status note (2026-03-11): current NRC APS status, proof artifacts, closed-layer guidance, and next-step handoff are frozen in [nrc_aps_status_handoff.md](nrc_aps_status_handoff.md). This runbook remains gate-specific/operator-procedural.

## Purpose
This runbook defines the local fail-closed gate for APS operational safeguard artifacts.

The gate validates that each evaluated NRC APS run has a valid safeguard artifact:
- `<run_id>_aps_safeguard_v1.json`
- schema id/version checks (`aps.safeguard_report.v1`, `schema_version=1`)
- deterministic machine-readable presence for retry/timeout/limiter/lint safety evidence

## Command
Run from repo root:

```powershell
.\project6.ps1 -Action validate-nrc-aps-safeguards
```

Direct CLI:

```powershell
py -3.12 tools/nrc_aps_safeguard_gate.py --report tests/reports/nrc_aps_safeguard_validation_report.json
```

Optional direct CLI controls:
- `--run-id <id>` (repeatable): validate specific run(s) only.
- `--limit <n>`: validate latest `n` NRC APS runs when `--run-id` is not supplied.
- `--allow-empty`: do not fail when no matching runs are found.

## Validation Report
- Path: `tests/reports/nrc_aps_safeguard_validation_report.json`
- Contains:
  - pass/fail summary
  - per-run artifact presence/schema checks
  - exact failure reasons (`missing_artifact`, `invalid_json`, `invalid_schema`)

## Pre-Merge Sequence
Use the APS local gate sequence:

```powershell
.\project6.ps1 -Action gate-nrc-aps
```

This executes APS tests plus replay, sync-drift, and safeguard fail-closed validators.
