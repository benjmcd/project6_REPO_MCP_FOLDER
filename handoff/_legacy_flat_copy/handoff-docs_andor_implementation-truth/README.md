# Project6: Method-Aware Framework + ScienceBase Connector

This repository has two active tracks in one backend:

1. Method-aware tabular analytics flow:
   upload -> profile -> transform -> annotate -> analyze.
2. ScienceBase public connector flow:
   submit run -> discover/hydrate/select -> download -> ingest/profile/recommend -> reports/events.

The ScienceBase connector is implemented through v1.3.3 pilot hardening with in-process execution, lease safety, resume/cancel, policy controls, and operator observability endpoints.

## Current capabilities

### Method-aware analytics
- CSV upload and dataset version creation.
- Parquet-backed dataset payload storage (`DatasetVersion.storage_ref`).
- Variable profiling with ADF/KPSS stationarity hints.
- Transform recommendation + transform application.
- Annotation windows.
- Analysis methods:
  - `cross_correlation`
  - `decomposition` (STL)
  - `structural_break` (ruptures)

### ScienceBase connector
- Endpoints:
  - `POST /api/v1/connectors/sciencebase-public/runs`
  - `POST /api/v1/connectors/sciencebase-mcs/runs`
  - `POST /api/v1/connectors/nrc-adams-aps/runs`
  - `GET /api/v1/connectors/runs/{id}`
  - `GET /api/v1/connectors/runs/{id}/targets`
  - `GET /api/v1/connectors/runs/{id}/events`
  - `GET /api/v1/connectors/runs/{id}/reports`
  - `POST /api/v1/connectors/runs/{id}/cancel`
  - `POST /api/v1/connectors/runs/{id}/resume`
  - `GET /api/v1/connectors/runs/{id}/content-units`
  - `POST /api/v1/connectors/nrc-adams-aps/content-search`
  - `POST /api/v1/connectors/nrc-adams-aps/evidence-bundles`
  - `GET /api/v1/connectors/nrc-adams-aps/evidence-bundles/{bundle_id}`
- Submission idempotency via `Idempotency-Key` and request fingerprinting.
- Scope modes:
  `keyword_search`, `folder_children`, `folder_descendants`, `explicit_item_ids`, `explicit_dois`.
- MCS preset modes:
  `annual_release`, `commodity_sheet_release`.
- Multi-surface normalization (`files`, `distributionLinks`, `webLinks`) with policy gating.
- Outbound fetch controls (scheme/host/IP class/redirect policy).
- Cross-surface canonical dedupe and alias persistence.
- Partition cursor + checkpoint persistence for deterministic resume.
- Write-time core counters on `connector_run` for scalable `GET /runs/{id}`.
- Event log + report artifact bundle per run.

## Out of scope (current)
- Private/authenticated ScienceBase workflows.
- Queue/worker infrastructure (Celery/Redis/etc.).
- Broad non-tabular ingestion.

## Requirements
- Windows PowerShell.
- Python 3.12 via `py -3.12`.

## Quick start

Use the helper script from repo root:

```powershell
# install/update Python deps
.\project6.ps1 -Action setup

# apply alembic migrations
.\project6.ps1 -Action migrate

# start API (foreground)
.\project6.ps1 -Action start-api -Reload
```

In another terminal:

```powershell
# API health probe
.\project6.ps1 -Action status

# run live ScienceBase pilot validation
.\project6.ps1 -Action validate-live -ConsecutiveRuns 3 -TimeoutSeconds 600

# build/check/validate NRC APS replay corpus gate
.\project6.ps1 -Action build-nrc-aps-replay-corpus
.\project6.ps1 -Action check-nrc-aps-replay-corpus
.\project6.ps1 -Action validate-nrc-aps-replay

# validate NRC APS sync delta/drift artifact gate (fail-closed)
.\project6.ps1 -Action validate-nrc-aps-sync-drift

# validate NRC APS safeguard artifact gate (fail-closed)
.\project6.ps1 -Action validate-nrc-aps-safeguards

# validate NRC APS artifact-ingestion artifact gate (fail-closed)
.\project6.ps1 -Action validate-nrc-aps-artifact-ingestion

# validate NRC APS content-index artifact/DB parity gate (fail-closed)
.\project6.ps1 -Action validate-nrc-aps-content-index

# validate NRC APS evidence-bundle gate (fail-closed)
.\project6.ps1 -Action validate-nrc-aps-evidence-bundle

# collect a fresh isolated NRC APS live batch
.\project6.ps1 -Action collect-nrc-aps-live-batch -ConsecutiveRuns 3 -BatchSpacingSeconds 5 -TimeoutSeconds 45

# validate NRC APS promotion governance gate (fail-closed; requires persisted live validation reports)
.\project6.ps1 -Action validate-nrc-aps-promotion

# compare tuned NRC APS promotion policy thresholds without code changes
.\project6.ps1 -Action compare-nrc-aps-promotion-policy `
  -NrcApsBatchManifest "<abs_manifest_path>" `
  -NrcApsTunedPromotionPolicy "<abs_tuned_policy_path>" `
  -NrcApsPromotionRationale "<abs_rationale_path>"

# run the aggregate NRC APS local gate
# this is separate from fresh live batch collection and separate from promotion evaluation
.\project6.ps1 -Action gate-nrc-aps

```

Single command flow:

```powershell
.\project6.ps1 -Action all -ConsecutiveRuns 3 -TimeoutSeconds 600
```

`project6.ps1` now fails fast on underlying Python command errors.

## Troubleshooting

- `ConnectionRefusedError` / `Max retries exceeded` on `localhost:8000`:
  API is not running. Start it with:
  `.\project6.ps1 -Action start-api -Reload`
  then rerun validation.

- `ModuleNotFoundError: No module named 'app'` from manual uvicorn command:
  start from `backend/` with `main:app` (the helper script already does this correctly).

- `ModuleNotFoundError: No module named 'pandas'` (or other deps):
  run `.\project6.ps1 -Action setup` using Python 3.12.

## Live pilot validation gate

Pilot validator script:

```powershell
py -3.12 tools\run_sciencebase_live_pilot_validation.py --base-url http://127.0.0.1:8000 --consecutive-runs 3 --timeout-seconds 600
```

Gate requires:
- three consecutive full-suite cycles pass,
- no non-terminal leftovers,
- operator endpoints are healthy (`/runs`, `/targets`, `/events`, `/reports`),
- at least one conditional no-op in the gate window:
  - `not_modified_remote` (HTTP 304), or
  - `skipped_unchanged_after_conditional_revalidate` (conditional request sent, upstream returned 200 unchanged).

The validator performs bounded automatic resume attempts when a run finishes with retryable non-terminal targets.

Validator output fields:
- `failed_cycles`: count of suite cycles with at least one failed scenario.
- `missing_conditional_noop_gate`: whether the conditional no-op gate was not satisfied.
- `failed_gate_checks`: total gate failures (`failed_cycles` + conditional-noop gate miss).

## Attached local data evaluations

Local archive set is under `data_actual/`.

Run evaluator:

```powershell
py -3.12 tools\run_attached_dataset_eval.py --method-name cross_correlation --data-root data_actual --max-files 30 --seed 7 --output-prefix data_actual_sample30_cc
```

## Key docs
- [docs/nrc_adams/nrc_aps_status_handoff.md](docs/nrc_adams/nrc_aps_status_handoff.md)
- [SCIENCEBASE_PILOT_RUNBOOK.md](SCIENCEBASE_PILOT_RUNBOOK.md)
- [METHOD_AWARE_FRAMEWORK_CHANGELOG.md](METHOD_AWARE_FRAMEWORK_CHANGELOG.md)
- [REPO_INDEX.md](REPO_INDEX.md)
- [data_actual/README.md](data_actual/README.md)
- [docs/nrc_adams/replay_gate_runbook.md](docs/nrc_adams/replay_gate_runbook.md)
- [docs/nrc_adams/sync_drift_gate_runbook.md](docs/nrc_adams/sync_drift_gate_runbook.md)
- [docs/nrc_adams/safeguard_gate_runbook.md](docs/nrc_adams/safeguard_gate_runbook.md)
- [docs/nrc_adams/promotion_gate_runbook.md](docs/nrc_adams/promotion_gate_runbook.md)
- [docs/nrc_adams/content_index_gate_runbook.md](docs/nrc_adams/content_index_gate_runbook.md)
- [docs/nrc_adams/evidence_bundle_gate_runbook.md](docs/nrc_adams/evidence_bundle_gate_runbook.md)

For the current NRC APS layer status, proof artifacts, closed-layer guidance, and next-step handoff, use the canonical handoff doc above. The layer-specific runbooks remain gate/operator workflow references.
