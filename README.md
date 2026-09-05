# Project6: Method-Aware Framework + Connector Stack

> **2026-09-04 state reconciliation:** Current tracked-state authority is
> `project6-origin/main` at `d9412188e9581302429112cc637e416fe666994f`.
> Relevant merged tranches from PRs #2477-#2494 add the ratified connector-intake
> records, connector-only DatasetVersion handoff, adopted-external intake, and
> bounded public ScienceBase analysis/value inspection. The public Layer 3
> additions are experimental and default-off:
> `LAYER3_PUBLIC_DATASET_ANALYSIS_ENABLED=false` and
> `LAYER3_PUBLIC_CONNECTOR_VALUE_REVEAL_ENABLED=false`; values require both
> flags plus admitted `sciencebase/public_api` provenance and are returned only
> with provenance, with storage references excluded. PRs #2495 and #2496 are
> open with clean merge state and 21 successful checks each, but remain owner
> merge decisions and are not on main. See
> [docs/MASTER_CONTEXT.md](docs/MASTER_CONTEXT.md#2026-09-04-current-state-reconciliation)
> for the bounded current summary and explicit non-claims.

> **Current status** (tracked on `project6-origin/main`): the selected final 0.3.0 profile is `base=local_expert`, `overlays=["public_connectors","sec_xbrl_offline"]`. The FastAPI/SQLAlchemy surface defaults to a single-operator local profile (`AUTH_OWNER=none`, `LAYER3_ROUTE_AUTHORIZATION_MODE=identity_presence`): under this local default there is **no authentication boundary** - the server derives a constant local-operator principal without inspecting request headers and treats the caller as owner, so identity/role gating is inert. Identity and role become an actual auth boundary only under the nonlocal/proxy posture (`AUTH_OWNER=proxy` with `TRUSTED_PROXY_MODE=true` behind an authenticating reverse proxy). Sublayer 3C deterministic method/product flows, ScienceBase public/MCS, Senate LDA anonymous metadata, World Bank Indicators anonymous metadata, BLS Public Data API v1 anonymous metadata, OECD SDMX anonymous metadata, and CFTC COT anonymous public report-row connector workflows, connector run observability, and the default-deny model/agent egress policy are present. Public connector support is bounded to operator-workflow + local-deployment for public/anonymous connector use; SEC-XBRL value-bearing support is simulation/offline-replay only for already-acquired operator-supplied evidence with redacted/hash-only outputs. Bounded SEC-XBRL live source-artifact acquisition is present but remains explicit-default-off behind `LAYER3_SEC_EDGAR_LIVE_NETWORK_ENABLED=false` and server-configured User-Agent/rate-limit controls; value reveal / controlled reveal submit remain default-off; and CI covers the PostgreSQL 3C golden path plus the SEC-XBRL test families. This selected local profile is not a production-ready claim for SEC value reveal, real provider delivery, live SEC network, model egress, OCR, keyed connectors, HA, or any nonlocal/default-on behavior.
>
> Agent/operator harness entry point: [docs/agent-harness.md](docs/agent-harness.md).

## Layer-specific and historical status surfaces

The notes below are layer-specific milestones and navigation pointers, not the repository-wide current support posture stated above.

> Earlier NRC APS phase note (2026-03-25): Phase 7/7A (Advanced NRC APS Ingestion) reached an `accepted-state` and Phase 8 (Downstream Consumption) a **CLOSED** state (APS-table materialization invariants satisfied in closure-run-005). Canonical per-layer status and navigation:
> - [nrc_aps_status_handoff.md](docs/nrc_adams/nrc_aps_status_handoff.md) (NRC APS continuation truth)
> - [nrc_aps_authority_matrix.md](docs/nrc_adams/nrc_aps_authority_matrix.md) (repo-wide authority map)
> - [nrc_aps_reader_path.md](docs/nrc_adams/nrc_aps_reader_path.md) (navigational guide)
> - [nrc_aps_ui_launch_runbook.md](docs/nrc_adams/nrc_aps_ui_launch_runbook.md) (review/document-trace/workbench/Candidate B Trace launch contract)
> - [frontend_UI_plans/README.md](frontend_UI_plans/README.md) (review UI / document trace / workbench compare / Candidate B Trace operator/reference front door)
> - [docs/onlook-ops.md](docs/onlook-ops.md) (Onlook testing / troubleshooting / audit / operator front door)
> - [docs/layer3-deployment-security.md](docs/layer3-deployment-security.md) (Layer 3 local/dev deployment-security posture, live non-local startup guardrail, and hardening decisions)
> - [docs/layer3-deploy-hardening.md](docs/layer3-deploy-hardening.md) (Layer 3 non-local deployment hardening governance and first settings guardrail)
> - [postgres_status_handoff.md](docs/postgres/postgres_status_handoff.md) (PostgreSQL Tier1 status)
>
> Some `tests/...` and `tools/...` paths referenced in older docs may not exist in a given export workspace; confirm on-disk presence before treating any as an authority path.

This repository has seven active tracks in one backend:

1. Method-aware tabular analytics flow:
   upload -> profile -> transform -> annotate -> analyze.
2. ScienceBase public connector flow:
   submit run -> discover/hydrate/select -> download -> ingest/profile/recommend -> reports/events.
3. Senate LDA metadata connector flow:
   submit run -> query official filings API -> persist filing targets -> optional detail hydrate -> reports/events.
4. World Bank Indicators metadata connector flow:
   submit run -> query official indicators API -> persist country/indicator targets -> reports/events.
5. BLS Public Data API v1 metadata connector flow:
   submit run -> query official v1 time-series API -> persist metadata/provenance -> reports/events.
6. OECD SDMX metadata connector flow:
   submit run -> query official SDMX API as SDMX-CSV -> persist metadata/provenance -> reports/events.
7. CFTC COT report-row connector flow:
   submit run -> fetch the current official legacy COT text file -> parse public report rows into connector reports -> persist metadata/provenance -> reports/events.

The connector runtime is in-process and currently includes ScienceBase public/MCS, NRC ADAMS APS, Senate LDA metadata, World Bank Indicators metadata, BLS Public Data API v1 metadata, OECD SDMX metadata, and CFTC COT report-row slices with lease safety, resume/cancel, policy controls, and operator observability endpoints.

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
  - `POST /api/v1/connectors/worldbank/runs`
  - `POST /api/v1/connectors/cftc-cot/runs`
  - `POST /api/v1/connectors/bls/runs`
  - `POST /api/v1/connectors/oecd-sdmx/runs`
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
- NRC APS upper analytical continuation on current `main` now extends beyond Deterministic Challenge Artifact v1: the repo also carries the landed Deterministic Challenge Review Packet v1 closeout, the bounded validate-only gate/report refresh lane, the dedicated validate-only runtime/report-ref lane, and the settled later APS family packet. Use `docs/nrc_adams/nrc_aps_status_handoff.md` for the canonical current continuation posture.
- NRC APS lower document-processing layers are now reopened additively:
  - deterministic media detection (`aps_media_detection_v1`)
  - PyMuPDF-based PDF extraction (`aps_document_extraction_v1`)
  - opt-in Candidate B OpenDataLoader PDF processing via `document_processing_engine="candidate_b_opendataloader_pdf"` for the existing NRC APS run-submit path; this is a later explicit runtime-admission reopen. Bounded follow-ups expose the engine metadata on the existing review `/runs` selector response, render Candidate B / OpenDataLoader PDF labels in the existing review/document-trace selectors, and add Candidate B runtime as an explicit Workbench Compare source kind while preserving the bundle source path. Candidate B Trace parity for admitted runtime runs, document-trace parity expansion, DB schema/model/migration work, broad route widening, persistence redesign, and new rendered run-submission UI remain out.
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
- The earlier "move above Deterministic Challenge Artifact v1" continuation is no longer pending on current `main`; that bounded continuation has already landed. Use `docs/nrc_adams/nrc_aps_status_handoff.md` rather than this summary paragraph for the live merged-main continuation posture.
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
- [docs/first-boot-capabilities.md](docs/first-boot-capabilities.md) (What works on a default boot vs. what is gated by key/secret/flag)
- [docs/program-context/INDEX.md](docs/program-context/INDEX.md)
- [docs/analyst_insight/analyst_insight_status_handoff.md](docs/analyst_insight/analyst_insight_status_handoff.md)
- [docs/nrc_adams/nrc_aps_status_handoff.md](docs/nrc_adams/nrc_aps_status_handoff.md)
- [docs/nrc_adams/nrc_aps_ui_launch_runbook.md](docs/nrc_adams/nrc_aps_ui_launch_runbook.md)
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

For the current NRC APS layer status, proof artifacts, closed-layer guidance, and settled continuation posture beyond Deterministic Challenge Artifact v1, use the canonical handoff doc above. The layer-specific runbooks remain gate/operator workflow references.
