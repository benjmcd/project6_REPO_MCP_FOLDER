# Method-Aware Framework — Changelog Through Latest Repo

This changelog is reconstructed from the generated planning-pack files, patch summaries, validation reports, and the latest repo archive `method_aware_framework_starter_decomp_break.zip`.

It is accurate to the artifacts available in this conversation, not to an external git history. Where the repo state and README disagree, the code and patch summaries are treated as source of truth.

## 0. Planning Pack Baseline (`planning_pack_v1`)

### Added
- Formalized project charter, MVP scope, architecture spec, data model, API contracts, milestones/backlog.
- Derived SQL schema, SQL DDL, and OpenAPI stub.
- Locked project direction around a **method-aware analytical workflow system** rather than a generic ingestion dashboard.

### Conceptual changes
- Introduced explicit layers for:
  - preprocessing / transformation,
  - method selection and routing,
  - assumption and caveat registry,
  - temporal annotation windows,
  - analysis artifacts and lineage,
  - domain-pack source architecture.

### Outcome
- The system design was narrowed to a first executable slice:
  `CSV -> dataset version -> profiling -> transformations -> annotation -> analysis artifact -> caveats`.

---

## 1. Initial Starter Repo (`method_aware_framework_starter.zip`)

### Added
- First runnable backend slice using:
  - FastAPI
  - SQLAlchemy
  - Alembic
  - Docker Compose / Postgres-oriented structure
- Core workflow objects:
  - `SourceConnector`
  - `Dataset`
  - `DatasetVersion`
  - `VariableDefinition`
  - `VariableProfile`
  - `TransformationRun` / `TransformationStep`
  - `AnnotationWindow`
  - `AnalysisRun`
  - `AssumptionCheck`
  - `CaveatNote`
  - `AnalysisArtifact`
  - `DatasetRow`
- Initial services:
  - CSV upload / ingestion
  - profiling
  - transform recommendation and application
  - cross-correlation analysis
- Initial tests and demo dataset.

### Implemented API spine
- upload source
- list/get datasets
- profile dataset version
- recommend/apply transformations
- create annotations
- create/get analysis runs

### Initial analysis/transform coverage
- Analysis:
  - `cross_correlation`
- Transformations:
  - `z_score`
  - `robust`
  - `min_max`
  - `winsor_zscore`
  - `yeo_johnson`

### Known weaknesses at this stage
- Runtime data storage relied on row-wise ORM persistence (`DatasetRow`) rather than file-backed storage.
- Year parsing and time inference were fragile.
- Placeholder-heavy numeric fields were not robustly coerced.
- Stationarity handling was effectively a stub.
- API responses were weakly typed.

---

## 2. Attached-Dataset Patch (`method_aware_framework_starter_patched.zip`)

This patch was driven by real USGS-style commodity files from:
- `Salient_Commodity_Data_Release_Grouped.zip`
- `mcs2024.zip`
- `mcs2025.zip`

### Fixed
- Rebuilt missing backend package structure so the repo was fully executable.
- Added config, DB session, dependency injection, API router, request schemas, and dataframe persistence utilities.
- Replaced naive `pd.to_datetime()` handling for year fields with year-aware parsing.
- Restricted time-column inference to time-like columns and date-like content.
- Dropped blank trailing rows and removed empty unnamed columns during ingestion.
- Added semantic numeric coercion for tokens such as:
  - `W`
  - `>95`
  - `Less than 1/2 unit.`
- Excluded the time index column from transform recommendation/application.
- Hardened cross-correlation against:
  - constant series,
  - all-NaN lag curves,
  - degenerate pairwise comparisons.
- Added regression coverage for year columns and placeholder values.

### Validation outcome
- Unit tests: **2 passed**.
- Salient end-to-end validation: **135 / 135 passed**.
- Non-salient lighter validation: **22 / 22 upload/profile/recommend passed**; **20 / 22 transform passed**, **2 / 22 correctly returned no transform steps**.

### Effect
- The starter stopped breaking on the main commodity time-series workflow.
- The repo became viable for continued extension instead of needing redesign.

---

## 3. Post-Review Architecture Patch (`method_aware_framework_starter_postreview.zip`)

This patch addressed the strongest external review criticisms.

### Major storage/architecture change
- Replaced runtime row-store usage with **file-backed dataset-version storage**.
- `dataset_version.storage_ref` now points to a **Parquet** file.
- `load_version_dataframe()` now reads from `storage_ref` instead of reconstructing data from `DatasetRow` ORM rows.
- The relational database remained the control plane for lineage, assumptions, caveats, profiling, and artifacts.

### Profiling credibility improvements
- Added real stationarity checks using:
  - ADF
  - KPSS
- `stationarity_hint` is now derived from actual test outcomes rather than returning `not_tested`.

### API contract improvements
- Added Pydantic `response_model` coverage for upload, dataset, profile, transformation, annotation, recommendation, and analysis routes.

### Routing and caveat improvements
- `recommend_analysis()` now uses profiling context.
- `AnalysisRun.route_reason` now records actual routing rationale rather than placeholder text.
- Cross-correlation assumption records now reflect profile-based stationarity context.

### Repo hygiene
- Added `.gitignore` for local databases, caches, and storage artifacts.
- Cleaned eval databases and storage outputs from the delivered repo bundle.

### Validation outcome
- Tests: **3 passed**.
- Targeted real-data sample summary:
  - **30/30 upload**
  - **30/30 profile**
  - **30/30 recommend**
  - **30/30 transform**
  - **30/30 analysis**
  - stationarity present for **29/30** sampled files.

### Remaining limits after this patch
- `DatasetRow` still exists in the schema/model layer for compatibility, but is no longer used in the runtime storage path.
- Seasonality detection remains heuristic.
- Analysis catalog remained narrow at that point.

---

## 4. Decomposition + Structural Break Patch (`method_aware_framework_starter_decomp_break.zip`) — Latest Repo

### Prerequisite fix applied first
- Fixed cross-correlation assumption persistence so `series_stationarity` is **derived from profiled hints** instead of hardcoded `warn`.
- Logic now records:
  - `fail` if any series is profiled as `likely_nonstationary` or `trend_stationary_or_mixed`
  - `pass` if profiled hints exist and none are nonstationary
  - `warn` if no relevant profiling hints exist

### Added analysis method: `decomposition`
- Implemented STL decomposition using `statsmodels.tsa.seasonal.STL`.
- For eligible variables, persists:
  - one PNG per variable with observed / trend / seasonal / residual plots,
  - one JSON per variable with component arrays and summary statistics.
- Added assumption checks:
  - `sufficient_observations`
  - `time_regularity`
  - `stationarity_of_residual`
- Short or irregular series now produce caveats instead of exceptions.

### Added analysis method: `structural_break`
- Implemented structural break detection using `ruptures.Pelt(model="rbf")`.
- Uses STL residuals when decomposition prerequisites are met; otherwise falls back to differenced raw series.
- For eligible variables, persists:
  - one PNG per variable with breakpoints annotated,
  - one JSON per variable with breakpoint indices, timestamps, penalty, and confidence proxy.
- Added assumption checks:
  - `minimum_segment_length`
  - `stationarity_required_for_break_test`
- Always writes caveats about:
  - penalty sensitivity,
  - nonstationary-series interpretation risk.

### Routing update
- Multivariate time series route to:
  - `cross_correlation`
  - `decomposition`
  - `structural_break`
- Univariate time series route to:
  - `decomposition`
  - `structural_break`
- `route_reason` is now aligned with the profile context and routing sequence.

### Evaluation tooling
- Extended `tools/run_attached_dataset_eval.py` with method selection and sample-file based evaluation.
- Added integration coverage for:
  - decomposition artifact creation,
  - structural-break artifact creation,
  - graceful short-series caveat behavior.

### Validation outcome
- Repo tests: **5 passed**.
- 30-file sample eval for `decomposition`:
  - **30/30 analysis calls succeeded**
  - **0 exceptions**
  - **0 artifact-producing runs on that sample**
  - **30/30 caveat-only runs**
- 30-file sample eval for `structural_break`:
  - **30/30 analysis calls succeeded**
  - **0 exceptions**
  - **0 artifact-producing runs on that sample**
  - **30/30 caveat-only runs**
- Positive artifact persistence was confirmed separately via integration tests on an eligible 36-month synthetic series.

### Why the sample produced no artifacts
- The 30-file evaluation sample was dominated by short annual USGS salient tables with roughly **5 yearly observations per transformed series**.
- STL requires **>=24 observations** in this workflow.
- Structural break detection on the same sample therefore correctly fell into the guarded caveat path.

---

## Latest repo state summary

### Analysis methods currently present in code
- `cross_correlation`
- `decomposition`
- `structural_break`

### Storage model currently present in runtime
- Dataset payloads are stored as **Parquet files** referenced by `DatasetVersion.storage_ref`.
- SQL remains the metadata/control plane.

### Profiling state
- Stationarity profiling uses ADF + KPSS.
- Seasonality remains heuristic.

### API state
- Pydantic response models exist.
- Operator workflow is API-first.

### Test/validation state
- Automated tests in latest repo: **5 passed**.
- Latest real-data 30-file sample runs cleanly for all three methods in the sense of **no crashes**, but decomposition and break detection mostly yield caveats due to insufficient observation counts on that sample.

---

## Known inconsistencies / caveats in the latest repo

1. **README is stale relative to code.**
   - The latest repo README still lists `decomposition / VAR / impulse response` as deferred.
   - That is no longer fully true.
   - Code and patch summaries show `decomposition` is implemented; `VAR` and `impulse response` are still deferred.

2. **`DatasetRow` still exists in the model layer.**
   - Runtime no longer depends on it.
   - Full schema cleanup was not completed.

3. **Seasonality detection is still weak compared with stationarity handling.**
   - It remains heuristic rather than model-based.

4. **The latest real-data sample does not prove artifact generation for decomposition/break detection on the USGS annual tables.**
   - It proves graceful failure and caveat persistence.
   - Artifact persistence is proven on synthetic eligible data, not on that short-sample annual set.

---

## Practical version map

- `planning_pack_v1.zip` — design/spec baseline
- `method_aware_framework_starter.zip` — first executable vertical slice
- `method_aware_framework_starter_patched.zip` — ingestion/time/parsing hardening for attached commodity datasets
- `method_aware_framework_starter_postreview.zip` — file-backed storage, real stationarity checks, response models, hygiene
- `method_aware_framework_starter_decomp_break.zip` — latest repo; adds decomposition, structural-break detection, improved assumption persistence

## Bottom line

The repo evolved in four real steps:
1. **specification**,
2. **first executable control-plane slice**,
3. **real-data ingestion hardening**,
4. **storage/profiling credibility upgrade**,
5. **decomposition + structural-break analysis on the existing lineage spine**.

That is the accurate project changelog through the latest repo artifact available here.

---

## 5. ScienceBase Connector Evolution (v1.2 -> v1.3.3 hardening)

This section captures the connector work implemented in this workspace after the earlier analysis-focused patches.

### v1.2 material controls

Added:
- submission idempotency:
  - `Idempotency-Key` + request fingerprint
  - `connector_run_submission` persistence
  - key replay behavior and conflict handling
- outbound fetch policy:
  - HTTPS-only default
  - host allowlist policy
  - blocked IP class enforcement
  - redirect revalidation
- cross-surface dedupe:
  - canonical artifact identity
  - precedence `files > distributionLinks > webLinks`
  - alias persistence
- retry classification and persisted retry eligibility/error class.

### v1.3.2 contract completion

Added:
- explicit scope modes:
  - `keyword_search`, `folder_children`, `folder_descendants`, `explicit_item_ids`, `explicit_dois`
- MCS release mode controls:
  - `annual_release`, `commodity_sheet_release`
- effective search envelope persistence:
  - params, filters, sort/order/page size, exhaustion reason
- partition cursor table and deterministic resume state
- no-op/reconciliation clarity:
  - `not_modified_remote`
  - reconciliation terminal states
  - `budget_blocked`
- selection attribution + permission/access summaries on targets
- expanded run/target response contracts and counters.

### v1.3.3 pilot hardening

Added:
- internal connector modular split:
  - `contracts`, `planner`, `executor`, `reconciliation`, `reporting`, `serialization`
- atomic target transition path with:
  - lease assertion
  - status transition
  - write-time core counter deltas
  - stage-attempt insert
  - run-event insert
- scalable `GET /runs/{id}` behavior using persisted core counters
- run events endpoint and reports endpoint
- live pilot validator scenarios:
  - first import
  - recurring sync
  - budget cap
  - cancel + resume.

### Post-v1.3.3 reliability/doc fixes (current workspace)

Fixed:
- `project6.ps1` now fails when underlying `py` commands fail (exit-code propagation).
- stale PowerShell variable issue (`$Host`) was already corrected to `$apiHost`.
- recurring-sync unchanged path now records explicit reason:
  - `skipped_unchanged_after_conditional_revalidate`
  when conditional headers were sent and upstream returned unchanged content with HTTP 200.
- live pilot validator now accepts conditional no-op proof from either:
  - `not_modified_remote` (304), or
  - `skipped_unchanged_after_conditional_revalidate` (200 unchanged after conditional request).
- live validator hardened for request-failure handling and report-status checks.
- live validator now performs bounded resume attempts when runs finish with retryable non-terminal targets.
- live validator gate summary now separates:
  - `failed_cycles` (scenario-cycle failures),
  - `missing_conditional_noop_gate`,
  - `failed_gate_checks` (aggregate gate failure count).
- live validator default base URL now uses `http://127.0.0.1:8000`.

Added tests:
- recurring-sync conditional revalidate-200 path marks `skipped_unchanged_after_conditional_revalidate`.

Current test status:
- `24 passed` in `tests/test_api.py`.

Additional live verification:
- commodity-sheet non-gate smoke runs were executed on live ScienceBase:
  - `commodity_keywords=["salient"]` and `["production"]` completed with selected targets,
  - `commodity_keywords=["lithium"]` completed with zero targets (valid no-match outcome).

Environment maintenance:
- removed stale `~rocrastinate*` site-packages leftovers that were causing pip warning noise during setup/install commands.

### Known remaining operational caveat

- Some ScienceBase file endpoints observed in this environment do not consistently emit 304 for conditional headers; they may return 200 with updated `Last-Modified` values.
- The gate now captures conditional no-op evidence without assuming universal 304 behavior.
