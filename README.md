# Project6: Method-Aware Framework + Connector Stack

> Status note (2026-03-25): Phase 7/7A (Advanced NRC APS Ingestion) is in an `accepted-state`. Phase 8 (Downstream Consumption) is in a **CLOSED** state (all APS-table materialization invariants satisfied in closure-run-005). The authoritative status and navigation surfaces live in:
> - [nrc_aps_status_handoff.md](docs/nrc_adams/nrc_aps_status_handoff.md) (Accepted 7A Truth)
> - [nrc_aps_authority_matrix.md](docs/nrc_adams/nrc_aps_authority_matrix.md) (Repo-wide Authority Map)
> - [nrc_aps_reader_path.md](docs/nrc_adams/nrc_aps_reader_path.md) (Navigational Guide)
> - [postgres_status_handoff.md](docs/postgres/postgres_status_handoff.md) (PostgreSQL Tier1 Status)
>
> **CRITICAL WARNING**: Unverified `tests/...` and `tools/...` paths referenced below may not exist in this specific export workspace and should not be trusted as safe authority paths unless their on-disk presence is directly confirmed.

This repository has three active tracks in one backend:

1. Method-aware tabular analytics flow:
   upload -> profile -> transform -> annotate -> analyze.
2. ScienceBase public connector flow:
   submit run -> discover/hydrate/select -> download -> ingest/profile/recommend -> reports/events.
3. Senate LDA metadata connector flow:
   submit run -> query official filings API -> persist filing targets -> optional detail hydrate -> reports/events.

The connector runtime is in-process and currently includes ScienceBase public/MCS, NRC ADAMS APS, and Senate LDA metadata slices with lease safety, resume/cancel, policy controls, and operator observability endpoints.

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
  - `POST /api/v1/connectors/senate-lda/runs`
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
  - `POST /api/v1/connectors/nrc-adams-aps/citation-packs`
  - `GET /api/v1/connectors/nrc-adams-aps/citation-packs/{citation_pack_id}`
  - `POST /api/v1/connectors/nrc-adams-aps/evidence-reports`
  - `GET /api/v1/connectors/nrc-adams-aps/evidence-reports/{evidence_report_id}`
  - `POST /api/v1/connectors/nrc-adams-aps/evidence-report-exports`
  - `GET /api/v1/connectors/nrc-adams-aps/evidence-report-exports/{evidence_report_export_id}`
- `POST /api/v1/connectors/nrc-adams-aps/evidence-report-export-packages`
- `GET /api/v1/connectors/nrc-adams-aps/evidence-report-export-packages/{evidence_report_export_package_id}`
- `POST /api/v1/connectors/nrc-adams-aps/context-packets`
- `GET /api/v1/connectors/nrc-adams-aps/context-packets/{context_packet_id}`
- `POST /api/v1/connectors/nrc-adams-aps/context-dossiers`
- `GET /api/v1/connectors/nrc-adams-aps/context-dossiers/{context_dossier_id}`
- `POST /api/v1/connectors/nrc-adams-aps/deterministic-insight-artifacts`
- `GET /api/v1/connectors/nrc-adams-aps/deterministic-insight-artifacts/{deterministic_insight_artifact_id}`
- `POST /api/v1/connectors/nrc-adams-aps/deterministic-challenge-artifacts`
- `GET /api/v1/connectors/nrc-adams-aps/deterministic-challenge-artifacts/{deterministic_challenge_artifact_id}`
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
- Additive NRC APS run-detail refs on `GET /api/v1/connectors/runs/{id}` now include:
  - `aps_evidence_citation_packs`
  - `aps_evidence_citation_pack_failures`
  - `aps_evidence_reports`
  - `aps_evidence_report_failures`
  - `aps_evidence_report_exports`
  - `aps_evidence_report_export_failures`
  - `aps_evidence_report_export_packages`
  - `aps_evidence_report_export_package_failures`
- `aps_context_packets`
- `aps_context_packet_failures`
- `aps_context_dossiers`
- `aps_context_dossier_failures`
- `aps_deterministic_insight_artifacts`
- `aps_deterministic_insight_artifact_failures`
- `aps_deterministic_challenge_artifacts`
- `aps_deterministic_challenge_artifact_failures`
- NRC APS upper analytical layers remain frozen through Deterministic Challenge Artifact v1.
- NRC APS lower document-processing layers are now reopened additively:
  - deterministic media detection (`aps_media_detection_v1`)
  - PyMuPDF-based PDF extraction (`aps_document_extraction_v1`)
  - BOM-aware plain-text decoding
  - OCR adapter wiring via the Tesseract CLI
  - cooperative enforcement of `content_parse_timeout_seconds`
  - content units v2 / chunking v2 with page and unit metadata
- Lower-layer diagnostics refs are now authoritative on the run-target/content-artifact surfaces. The deduplicated content-document row is not the authoritative diagnostics pointer across runs.
- `download_only` content indexing now persists a diagnostics artifact during blob reprocessing.
- Lower-layer corpus proof is now manifest-driven through `tests/fixtures/nrc_aps_docs/v1/manifest.json`, `tests/support_nrc_aps_doc_corpus.py`, and `tests/test_nrc_aps_document_corpus.py`.
- The corpus now includes a representative real NRC PDF fixture at `tests/fixtures/nrc_aps_docs/v1/ML17123A319.pdf`, copied from the local example placed under `data_demo/`.
- Fresh OCR-enabled lower-layer proof is now checked in at:
  - `tests/reports/nrc_aps_document_processing_proof_report.json`
  - `tests/reports/nrc_aps_artifact_ingestion_validation_report.json`
  - `tests/reports/nrc_aps_content_index_validation_report.json`
- Fresh aggregate `gate-nrc-aps` proof was also rerun on March 13, 2026.
  Current aggregate-scoped reports now include refreshed PASS outputs for:
  - `tests/reports/nrc_aps_evidence_bundle_validation_report.json`
  - `tests/reports/nrc_aps_evidence_citation_pack_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_validation_report.json`
  - `tests/reports/nrc_aps_evidence_report_export_package_validation_report.json`
  - `tests/reports/nrc_aps_context_packet_validation_report.json`
  - `tests/reports/nrc_aps_context_dossier_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_insight_artifact_validation_report.json`
  - `tests/reports/nrc_aps_deterministic_challenge_artifact_validation_report.json`
- Other checked-in `tests/reports/*.json` files should still be treated as historical snapshots unless explicitly regenerated in the current pass.
- `project6.ps1 -Action prove-nrc-aps-document-processing` now runs the fresh isolated lower-layer proof lane and then calls the validate-only artifact-ingestion and content-index gates against that isolated runtime.
- OCR success is now proven in this workspace through the `-RequireOcr` lane. The Tesseract CLI is still an external prerequisite for reproducing that proof in another environment, but the OCR adapter now auto-detects the standard Windows install path under `C:\Program Files\Tesseract-OCR` even if the current shell PATH has not refreshed yet.
- Standalone local validation now includes fail-closed Deterministic Challenge Artifact coverage via `validate-nrc-aps-deterministic-challenge-artifact`; `gate-nrc-aps` now invokes the same Challenge validator after the Insight validator in the aggregate path.
- Fresh full `gate-nrc-aps` proof is now rerun on March 13, 2026:
  - aggregate pytest slice: `143 passed, 29 deselected`
  - post-validator dossier ambiguity negative slice: `1 passed, 55 deselected`
  - aggregate validate-only report set refreshed to PASS, including deterministic challenge
- OCR-enabled lower-layer adequacy proof is now established in this workspace.
- The current safe continuation can move above Deterministic Challenge Artifact v1 without reopening the restored lower-layer baseline.
- Senate LDA metadata connector v1 adds:
  - official LDA `/filings/` query support with optional `Authorization: Token <key>` auth
  - one connector target per filing UUID on the existing generic run/targets/events/reports surfaces
  - optional filing-detail hydration via `/filings/{filing_uuid}/`
  - additive `senate_lda_summary` report surfacing on run detail and reports endpoints

## Out of scope (current)
- Private/authenticated ScienceBase workflows.
- Queue/worker infrastructure (Celery/Redis/etc.).
- Broad non-tabular ingestion.

## Requirements
- Windows PowerShell.
- Python 3.12 via `py -3.12`.
- Optional `SENATE_LDA_API_KEY` for higher-rate official LDA access.

## Quick start

Use the helper script from repo root:

```powershell
# configure Tier1 PostgreSQL for this shell, or set the same DATABASE_URL in backend/.env
$env:DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/method_aware"

# install/update Python deps
.\project6.ps1 -Action setup

# apply Tier1 migrations (PostgreSQL-backed by default)
.\project6.ps1 -Action migrate

# start API (foreground; Tier1 PostgreSQL by default)
.\project6.ps1 -Action start-api -Reload
```

Note: the helper script now defaults Tier1 operator actions to PostgreSQL, but the bare no-env runtime default in [backend/app/core/config.py](backend/app/core/config.py) intentionally remains SQLite for now.

SQLite fallback for Tier1 remains available explicitly:

```powershell
.\project6.ps1 -Action migrate -Tier1DatabaseBackend sqlite
.\project6.ps1 -Action start-api -Tier1DatabaseBackend sqlite -Reload
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

# run fresh isolated NRC APS lower-layer document-processing proof
.\project6.ps1 -Action prove-nrc-aps-document-processing

# require OCR-success proof in a Tesseract-enabled validation environment
.\project6.ps1 -Action prove-nrc-aps-document-processing -RequireOcr

# validate NRC APS evidence-bundle gate (fail-closed)
.\project6.ps1 -Action validate-nrc-aps-evidence-bundle

# validate NRC APS evidence-citation-pack gate (fail-closed)
.\project6.ps1 -Action validate-nrc-aps-evidence-citation-pack

# validate NRC APS evidence-report gate (fail-closed)
.\project6.ps1 -Action validate-nrc-aps-evidence-report

# validate NRC APS evidence-report export gate (fail-closed; validates existing persisted test-runtime export artifacts)
.\project6.ps1 -Action validate-nrc-aps-evidence-report-export

# validate NRC APS evidence-report export package gate
# (fail-closed; validates existing persisted test-runtime package artifacts only and does not generate them)
.\project6.ps1 -Action validate-nrc-aps-evidence-report-export-package

# validate NRC APS context packet gate
# (validate-only; current live script also invokes the dossier gate in this action,
# and does not generate artifacts)
.\project6.ps1 -Action validate-nrc-aps-context-packet

# validate NRC APS context dossier gate
# (validate-only; validates existing persisted test-runtime context dossier artifacts only,
# fails closed on empty runtime, and does not generate artifacts)
.\project6.ps1 -Action validate-nrc-aps-context-dossier

# validate NRC APS deterministic insight artifact gate
# (validate-only; validates existing persisted test-runtime insight artifacts only,
# fails closed on empty runtime, and does not generate artifacts)
.\project6.ps1 -Action validate-nrc-aps-deterministic-insight-artifact

# validate NRC APS deterministic challenge artifact gate
# (validate-only; validates existing persisted test-runtime challenge artifacts only,
# fails closed on empty runtime, and does not generate artifacts)
.\project6.ps1 -Action validate-nrc-aps-deterministic-challenge-artifact

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
# and now includes citation-pack, evidence-report, evidence-report export, package,
# context packet, context dossier, deterministic insight, and deterministic challenge coverage
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

For the current NRC APS layer status, proof artifacts, closed-layer guidance, and next-step handoff through Deterministic Challenge Artifact v1, use the canonical handoff doc above. The layer-specific runbooks remain gate/operator workflow references.
