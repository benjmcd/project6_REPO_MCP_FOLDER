# Public Connectors Journey

## 2026-09-04 bounded Layer 3 extension

Current main adds an optional public ScienceBase-to-Layer 3 path after the
canonical connector journey below. It is experimental and default-off. With
`LAYER3_PUBLIC_DATASET_ANALYSIS_ENABLED=true`, the workbench may discover only
materialized DatasetVersions whose newest provenance is
`sciencebase/public_api`, and it remains bound to connector target identity.
Result-value inspection requires that flag plus
`LAYER3_PUBLIC_CONNECTOR_VALUE_REVEAL_ENABLED=true`. Returned values remain
bound to approved plan/pass/run and artifact identities, are co-displayed with
complete public provenance, and exclude storage references.

The exact Layer 3 navigation surfaces are:

- `GET /api/v1/layer3/public-dataset-version-candidates` for the gated public
  candidate inventory.
- `POST /api/v1/layer3/execution/result/public-values` for the dual-flag-gated,
  provenance-bound result-value response.

This extension does not widen the shared APS admission predicate, make the
public path default-on, change support-matrix IDs/counts/pins, prove temporal
scientific utility, or authorize a public run. Retained public runs demonstrate
plumbing only; cross-sectional row order is not time. See
[MASTER_CONTEXT](MASTER_CONTEXT.md#2026-09-04-current-state-reconciliation) for
the current bounded state and pending owner decisions. Operator navigation starts
at the
[current operator pointer](OPERATOR_UTILIZATION_INDEX.md#2026-09-04-current-operator-pointer).

This journey covers the public_connectors overlay in the current selected local profile: ScienceBase public/MCS, Senate LDA anonymous metadata, World Bank Indicators anonymous metadata, BLS Public Data API v1 anonymous metadata, OECD SDMX anonymous metadata, and CFTC COT anonymous public report rows. It does not activate or claim OCR, model/agent egress, keyed connectors, nonlocal deployment, high availability, automatic replay, real provider delivery, SEC value reveal, or default-on SEC live network behavior. The current support matrix, not the earlier RC1 analytics-only claim, is the authority for whether these connector slices are selected.

## Canonical ScienceBase Path

The canonical path is:

1. Submit `POST /api/v1/connectors/sciencebase-public/runs` with `q=MCS`, `run_mode=one_shot_import`, `allowed_extensions=[".csv"]`, and `surface_policy=files_only`.
2. Inspect `GET /api/v1/connectors/runs/{run_id}` for `status=completed`, `source_system=sciencebase`, `source_mode=public_api`, and strict public-safe fetch policy with only ScienceBase hosts allowed by default.
3. Read `GET /api/v1/connectors/runs/{run_id}/targets` and take the recommended target's `dataset_version_id`.
4. Call `POST /api/v1/datasets/{dataset_id}/versions/{dataset_version_id}/analysis/recommend` to choose the method-aware analysis path for the ingested dataset.
5. Call `POST /api/v1/analysis-runs` using the target `dataset_version_id` and the recommended `cross_correlation` method.
6. Inspect `GET /api/v1/analysis-runs/{analysis_run_id}` and re-read the connector run and targets through a fresh client to prove persisted recovery.

The public no-key posture is explicit: ScienceBase runs use `source_mode=public_api`, strict public-safe fetch policy, public read confirmation on the ingested target, and no API key, authorization header, or token in run request config.

## Degraded Network Path

If ScienceBase target download hits a network-unreachable transport failure, the operator-visible result is degraded rather than silently complete: the run returns `completed_with_errors`, the target remains without a `dataset_version_id`, and the target is marked `download_failed` with retryable `transport_timeout` telemetry.

## Senate LDA Secondary Path

The Senate LDA path is secondary and metadata-only:

1. Submit `POST /api/v1/connectors/senate-lda/runs` with `run_mode=metadata_only` and `include_filing_detail=false`.
2. Inspect `GET /api/v1/connectors/runs/{run_id}` for official API-only fetch policy scoped to `lda.senate.gov`.
3. Read `GET /api/v1/connectors/runs/{run_id}/targets` for recommended filing targets with dataset versions.

The anonymous posture is explicit: the effective search params record `auth_mode=anonymous`, filing-detail hydration is not called in the metadata-only secondary proof, and no API key, authorization header, or token is stored in run request config.

## World Bank Indicators Secondary Path

The World Bank Indicators path is secondary and metadata-only:

1. Submit `POST /api/v1/connectors/worldbank/runs` with `run_mode=metadata_only`, one or more `indicators`, one or more `countries`, and an optional `date_range`.
2. Inspect `GET /api/v1/connectors/runs/{run_id}` for official API-only fetch policy scoped to `api.worldbank.org`, `auth_mode=anonymous`, and a `worldbank_summary` report ref.
3. Read `GET /api/v1/connectors/runs/{run_id}/targets` for recommended country/indicator targets with metadata-only dataset versions.

The anonymous posture is explicit: the connector has no API key setting, its effective search params record `auth_mode=anonymous`, and the stored provenance carries World Bank attribution, `CC BY 4.0`, and the World Bank summary terms-of-use URL.

## BLS Public Data API v1 Secondary Path

The BLS path is secondary and metadata-only:

1. Submit `POST /api/v1/connectors/bls/runs` with `run_mode=metadata_only`, one or more `series_ids`, optional `start_year`/`end_year`, and an optional `max_requests` per-run budget.
2. Inspect `GET /api/v1/connectors/runs/{run_id}` for official API-only fetch policy scoped to `api.bls.gov`, `auth_mode=anonymous`, and a `bls_summary` report ref.
3. Read the summary/selection report JSON for normalized time-series observations. The database stores metadata-only dataset/version/provenance records; observation values are retained in connector reports.

The anonymous posture is explicit: the connector has no API key setting, the runtime base URL is server-configured as `BLS_API_BASE_URL`, and no `registrationkey` parameter is sent. The connector enforces 25 series/query, a 10-year inclusive span, `max_rps <= 2`, and `max_requests <= 25` per run. The BLS v1 25-queries/day cap across runs remains operator responsibility because this lane does not add durable cross-run quota state.

## OECD SDMX Secondary Path

The OECD SDMX path is secondary and metadata-only:

1. Submit `POST /api/v1/connectors/oecd-sdmx/runs` with `run_mode=metadata_only`, `agency`, `dataflow`, `dimension_key`, optional period bounds, optional `lastNObservations`, and an optional `max_requests` per-run budget.
2. Inspect `GET /api/v1/connectors/runs/{run_id}` for official SDMX API-only fetch policy scoped to `sdmx.oecd.org`, `auth_mode=anonymous`, and an `oecd_sdmx_summary` report ref.
3. Read the summary/selection report JSON for normalized SDMX-CSV rows. The database stores metadata-only dataset/version/provenance records; observation rows are retained in connector reports.

The anonymous posture is explicit: the connector has no API key setting, the runtime base URL is server-configured as `OECD_SDMX_API_BASE_URL`, and no registration credential is sent. The connector uses documented SDMX-CSV `format=csvfilewithlabels`, enforces `max_rps <= 2` and `max_requests <= 30` per run, treats HTTP 413 as terminal `restricted_parameter_413`, and never falls back to JSON. The OECD 60 data downloads/hour limit and non-VPN/non-anonymized source egress posture remain operator responsibility because this lane does not add durable cross-run quota or network-origin controls.

## CFTC COT Secondary Path

The CFTC COT path is secondary and report-row-only:

1. Submit `POST /api/v1/connectors/cftc-cot/runs` with `run_mode=metadata_only` and `report_variant=legacy_futures_only` or `legacy_combined`.
2. Inspect `GET /api/v1/connectors/runs/{run_id}` for official file-only fetch policy scoped to `www.cftc.gov`, `auth_mode=anonymous`, and a `cftc_cot_summary` report ref.
3. Read the summary/selection report JSON for parsed public COT rows. The database stores metadata-only dataset/version/provenance records; row values are retained in connector reports, not raw blob tables.

The anonymous posture is explicit: the connector has no API key setting, the base URL is server-configured as `CFTC_COT_API_BASE_URL`, and the selected current file variants are constrained to CFTC's legacy current Futures-only and Futures-and-Options-Combined text files.

## Proof

Focused proof lives in `tests/test_api.py`:

- `test_public_connector_operator_journey_bridges_sciencebase_target_to_analysis`
- `test_public_connector_journey_network_unreachable_is_degraded`
- `test_senate_lda_anonymous_metadata_path_is_no_key_secondary_journey`
- `test_worldbank_connector_happy_path_reports_and_attribution`
- `test_worldbank_connector_empty_observations_fail_closed`
- `test_worldbank_connector_malformed_observations_fail_closed`
- `test_worldbank_connector_resume_continues_unmanifested_partial_discovery`
- `test_worldbank_connector_rejects_non_worldbank_base_url`
- `test_bls_connector_happy_single_get_reports_and_attribution`
- `test_bls_connector_happy_multi_post_with_years`
- `test_bls_connector_no_key_negative_single_and_multi`
- `test_bls_support_matrix_mirror_and_runtime_probe`
- `test_oecd_sdmx_connector_happy_dataflow_query_reports_and_attribution`
- `test_oecd_sdmx_connector_rejects_budget_over_30`
- `test_oecd_sdmx_connector_413_restricted_parameter_terminal_with_last_n`
- `test_oecd_sdmx_connector_empty_all_null_and_malformed_fail_closed`
- `test_oecd_sdmx_connector_rate_limiter_and_backoff_use_monkeypatched_clock`
- `test_oecd_sdmx_connector_get_redirect_cap_and_final_host`
- `test_oecd_sdmx_connector_unauthorized_terminal`
- `test_oecd_sdmx_connector_idempotency_conflict_and_resume`
- `test_oecd_sdmx_connector_rejects_non_oecd_base_url`
- `test_oecd_sdmx_support_matrix_mirror_and_runtime_probe`
- `test_cftc_cot_connector_happy_path_reports_rows_and_attribution`
- `test_cftc_cot_connector_accepts_headerless_current_report_rows`
- `test_cftc_cot_connector_unrecognized_format_fails_closed`
- `test_cftc_cot_connector_empty_and_all_null_reports_fail_closed`
- `test_cftc_cot_client_enforces_byte_cap_while_streaming`
- `test_cftc_cot_connector_resume_retries_existing_retryable_failed_target`
- `test_cftc_cot_connector_pre_target_cancel_finalizes_without_target`
- `test_cftc_cot_connector_precheck_rejects_non_cftc_and_blocked_ip`
