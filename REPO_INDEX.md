# Project6 Repository Index

Generated: 2026-03-09 (America/Los_Angeles)

> Status note (2026-03-13): NRC APS operational status and current lower-layer document-processing authority now live in [docs/nrc_adams/nrc_aps_status_handoff.md](docs/nrc_adams/nrc_aps_status_handoff.md). This file remains a broad repo map. Older ScienceBase-centric snapshot sections below are not the authoritative NRC APS status surface.
>> Status note (2026-03-14): Phase 7/7A (Advanced NRC APS Ingestion) is in an `accepted-state`. Phase 8 (Downstream Consumption) is in a PROVISIONAL state. The authoritative repository map and authority definitions live in [docs/nrc_adams/nrc_aps_authority_matrix.md](docs/nrc_adams/nrc_aps_authority_matrix.md).
>> Status note (2026-03-26): PostgreSQL Tier1 status and the current split-default semantics now live in [docs/postgres/postgres_status_handoff.md](docs/postgres/postgres_status_handoff.md). This file remains a broad repo map, not the authoritative PostgreSQL lane surface.
>> Status note (2026-04-03): Analyst-insight layer status, contract summary, and deferred tech debt now live in [docs/analyst_insight/analyst_insight_status_handoff.md](docs/analyst_insight/analyst_insight_status_handoff.md). This file remains a broad repo map, not the authoritative analyst-insight lane surface.
>> **CRITICAL WARNING**: Unverified `tests/...` and `tools/...` paths referenced below may not exist in this specific export workspace and should not be trusted as safe authority paths unless their on-disk presence is directly confirmed.

> Proof note (2026-03-13): fresh OCR-enabled lower-layer proof is now checked in at `tests/reports/nrc_aps_document_processing_proof_report.json`, `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`, and `tests/reports/nrc_aps_content_index_validation_report.json`, current OCR-success proof is established in this workspace, and a fresh full `gate-nrc-aps` PASS was rerun on March 13, 2026. The aggregate-scoped APS validation reports refreshed by that gate rerun are now current; other checked-in `tests/reports/*.json` files remain historical snapshots unless explicitly regenerated in the current pass.
> Proof note (2026-03-14): fresh OCR-enabled lower-layer proof and Phase 7A advanced validation are now checked in. Authoritative evidence and audit results (19 OCR, 28 Table verified) are recorded in `docs/nrc_adams/nrc_aps_status_handoff.md`.

## 1) Repository scope

This repository currently contains:

1. Method-aware analysis vertical slice:
   CSV upload -> profile -> transform -> annotate -> analysis artifact persistence.
2. ScienceBase public connector subsystem:
   run submission -> discovery/hydration -> artifact selection -> download -> ingest/profile/recommend -> reports/events.
3. Senate LDA metadata connector subsystem:
   run submission -> official filings query -> target persistence -> optional filing-detail hydrate -> reports/events.

Runtime model is in-process execution (no external worker queue).

## 2) Top-level layout

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI backend, ORM models, services, alembic migrations |
| `tests/` | Integration-heavy API tests (analysis + connector) |
| `tools/` | Live pilot validator and attached-data evaluator scripts |
| `data_demo/` | Demo CSV plus local user-supplied example artifacts; not an authority surface |
| `data_actual/` | Local MCS archives + evaluation outputs |
| `README.md` | Primary operational and capability docs |
| `SCIENCEBASE_PILOT_RUNBOOK.md` | ScienceBase pilot operator runbook |
| `METHOD_AWARE_FRAMEWORK_CHANGELOG.md` | Consolidated project change history |
| `project6.ps1` | Setup/migrate/start/status/validate/all helper script |

## 3) Backend code map

### Entry/config
- `backend/main.py`: app bootstrap, DB init, routes, static mount.
- `backend/app/core/config.py`: settings and storage paths.
- `backend/app/db/session.py`: SQLAlchemy session/engine/base.

### API routes
- `backend/app/api/router.py`: analysis and connector HTTP endpoints.
- `backend/app/schemas/api.py`: pydantic contracts for requests/responses.

### Core services
- `backend/app/services/ingest.py`
- `backend/app/services/profiling.py`
- `backend/app/services/transforms.py`
- `backend/app/services/analysis.py`
- `backend/app/services/connectors_sciencebase.py`
- `backend/app/services/connectors_nrc_adams.py`
- `backend/app/services/connectors_senate_lda.py`
- `backend/app/services/nrc_aps_media_detection.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/nrc_aps_ocr.py`
- `backend/app/services/nrc_aps_artifact_ingestion.py`
- `backend/app/services/nrc_aps_content_index.py`
- `backend/app/services/sciencebase_connector/`
  - `contracts.py`
  - `planner.py`
  - `executor.py`
  - `reconciliation.py`
  - `reporting.py`
  - `serialization.py`

### Migrations
- `backend/alembic/versions/0001_initial.py`
- `backend/alembic/versions/0002_connector_subsystem.py`
- `backend/alembic/versions/0003_core_schema_baseline.py`
- `backend/alembic/versions/0004_connector_contract_completion.py`
- `backend/alembic/versions/0005_connector_run_events.py`
- `backend/alembic/versions/0006_connector_run_core_counters.py`
- `backend/alembic/versions/0007_aps_hardening_state_tables.py`
- `backend/alembic/versions/0008_aps_content_index_tables.py`
- `backend/alembic/versions/0009_aps_document_processing_metadata.py`

## 4) API surface summary

### Analysis/data endpoints
- `POST /api/v1/sources/upload`
- `GET /api/v1/datasets`
- `GET /api/v1/datasets/{dataset_id}`
- `POST /api/v1/datasets/{dataset_id}/versions/{dataset_version_id}/profile`
- `POST /api/v1/datasets/{dataset_id}/versions/{dataset_version_id}/transformations/recommend`
- `POST /api/v1/datasets/{dataset_id}/versions/{dataset_version_id}/transformations/apply`
- `POST /api/v1/datasets/{dataset_id}/versions/{dataset_version_id}/annotations`
- `GET /api/v1/datasets/{dataset_id}/versions/{dataset_version_id}/annotations`
- `POST /api/v1/datasets/{dataset_id}/versions/{dataset_version_id}/analysis/recommend`
- `POST /api/v1/analysis-runs`
- `GET /api/v1/analysis-runs/{analysis_run_id}`

### ScienceBase connector endpoints
- `POST /api/v1/connectors/sciencebase-public/runs`
- `POST /api/v1/connectors/sciencebase-mcs/runs`
- `POST /api/v1/connectors/nrc-adams-aps/runs`
- `POST /api/v1/connectors/senate-lda/runs`
- `GET /api/v1/connectors/runs/{connector_run_id}`
- `GET /api/v1/connectors/runs/{connector_run_id}/targets`
- `GET /api/v1/connectors/runs/{connector_run_id}/events`
- `GET /api/v1/connectors/runs/{connector_run_id}/reports`
- `POST /api/v1/connectors/runs/{connector_run_id}/cancel`
- `POST /api/v1/connectors/runs/{connector_run_id}/resume`
- `GET /api/v1/connectors/runs/{connector_run_id}/content-units`
- `POST /api/v1/connectors/nrc-adams-aps/content-search`
- `POST /api/v1/connectors/nrc-adams-aps/evidence-bundles`
- `GET /api/v1/connectors/nrc-adams-aps/evidence-bundles/{bundle_id}`

## 5) Connector contract highlights

Implemented controls include:
- submission idempotency (`Idempotency-Key`, fingerprint, submission table),
- scope modes (`keyword_search`, folder scopes, explicit IDs, explicit DOIs),
- MCS modes (`annual_release`, `commodity_sheet_release`),
- partition planning + cursor persistence,
- outbound fetch policy + surface policy controls,
- cross-surface dedupe and alias persistence,
- resume/cancel + lease handling,
- write-time core counters for scalable run detail reads,
- event log and report artifact endpoints.
- Senate LDA note: the current additional connector slice is metadata-only and uses the generic run/targets/events/reports APIs to surface filing UUID targets plus optional `/filings/{filing_uuid}/` detail hydration.

## 6) Test inventory

NRC APS note: the current authoritative NRC APS gate/test inventory is in [docs/nrc_adams/nrc_aps_status_handoff.md](docs/nrc_adams/nrc_aps_status_handoff.md). The snapshot below is historical and ScienceBase-era.

Current lower-layer NRC APS test/fixture surfaces added in the live repo:
- `tests/test_nrc_aps_media_detection.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_document_corpus.py`
- `tests/test_nrc_aps_artifact_ingestion.py`
- `tests/test_nrc_aps_content_index.py`
- `tests/test_nrc_aps_content_index_gate.py`
- `tests/support_nrc_aps_doc_corpus.py`
- `tests/fixtures/nrc_aps_docs/v1/manifest.json`
- `tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf`
- `tests/reports/nrc_aps_document_processing_proof_report.json`

Test module: `tests/test_api.py`

Current collected tests (24):
- vertical slice workflow
- year/placeholder parsing
- parquet storage and stationarity
- decomposition/structural-break artifact behavior
- encoding fallback
- connector idempotency
- fetch policy blocks
- cross-surface dedupe
- partition planning
- recurring sync conditional fetch (304 path)
- recurring sync conditional revalidate (200 unchanged path)
- checkpoint frequency
- observability contract fields
- precomputed counter read path
- events/reports endpoint coverage
- resume discovery cursor
- resume target cursor
- scope mode behaviors
- MCS mode validation
- dry-run behavior
- budget blocking and cursor persistence

## 7) Operational scripts

- `project6.ps1`
  - `setup`
  - `migrate`
  - `start-api`
  - `status`
  - `validate-live`
  - `validate-nrc-aps`
  - `collect-nrc-aps-live-batch`
  - `build-nrc-aps-replay-corpus`
  - `validate-nrc-aps-replay`
  - `check-nrc-aps-replay-corpus`
  - `validate-nrc-aps-sync-drift`
  - `validate-nrc-aps-safeguards`
  - `validate-nrc-aps-artifact-ingestion`
  - `validate-nrc-aps-content-index`
  - `prove-nrc-aps-document-processing`
  - `validate-nrc-aps-evidence-bundle`
  - `validate-nrc-aps-promotion`
  - `compare-nrc-aps-promotion-policy`
  - `gate-nrc-aps`
  - `eval-attached`
  - `all`
- `tools/run_sciencebase_live_pilot_validation.py`
  - live-only pilot suite and gate evaluation.
- `tools/run_attached_dataset_eval.py`
  - local archive evaluation harness.
- `tools/run_nrc_aps_live_validation.py`
  - NRC APS live validation cycle runner.
- `tools/nrc_aps_live_validation_batch.py`
  - NRC APS batch collector over live validation cycles.
- `tools/nrc_aps_replay_gate.py`
- `tools/nrc_aps_sync_drift_gate.py`
- `tools/nrc_aps_safeguard_gate.py`
- `tools/nrc_aps_artifact_ingestion_gate.py`
- `tools/nrc_aps_content_index_gate.py`
- `tools/run_nrc_aps_document_processing_proof.py`
- `tools/nrc_aps_evidence_bundle_gate.py`
- `tools/nrc_aps_promotion_gate.py`
- `tools/nrc_aps_promotion_tuning.py`

## 8) Pilot verification status snapshot

NRC APS note: this section is historical for the ScienceBase pilot track. Current NRC APS status, green state, and proof artifacts are frozen in [docs/nrc_adams/nrc_aps_status_handoff.md](docs/nrc_adams/nrc_aps_status_handoff.md).

Verified:
- full automated test suite passes (`24 passed`).
- live suite scenarios run successfully across first import / recurring sync / budget cap / cancel+resume.
- operator endpoints and report generation are exercised in live validation.
- latest full gate run (`.\project6.ps1 -Action all -ConsecutiveRuns 3`) passed with:
  - `failed_cycles=0`
  - `missing_conditional_noop_gate=false`
  - `failed_gate_checks=0`
- non-gate commodity-sheet smoke runs executed successfully:
  - `commodity_keywords=["salient"]`: completed, selected targets present
  - `commodity_keywords=["production"]`: completed, selected targets present
  - `commodity_keywords=["lithium"]`: completed with zero targets (valid no-match path)

Partially verified:
- upstream ScienceBase conditional behavior is variable; HTTP 304 is not guaranteed across sampled file endpoints.
- conditional no-op is therefore tracked through two accepted outcomes:
  - `not_modified_remote` (304),
  - `skipped_unchanged_after_conditional_revalidate` (conditional request sent, unchanged after 200).

## 9) Current known caveats

- This workspace copy does not include a `.git/` directory.
- Connector runtime is intentionally in-process (no distributed worker queue).
- Public-read ScienceBase workflows only; private/authenticated paths are out of scope.
