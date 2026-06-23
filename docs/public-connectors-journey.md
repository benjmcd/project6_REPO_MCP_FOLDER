# Public Connectors Journey

This journey covers the public_connectors overlay in the current selected local profile: ScienceBase public/MCS and Senate LDA anonymous metadata. It does not activate or claim OCR, model/agent egress, keyed connectors, nonlocal deployment, high availability, automatic replay, real provider delivery, SEC value reveal, or default-on SEC live network behavior. The current support matrix, not the earlier RC1 analytics-only claim, is the authority for whether these connector slices are selected.

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

## Proof

Focused proof lives in `tests/test_api.py`:

- `test_public_connector_operator_journey_bridges_sciencebase_target_to_analysis`
- `test_public_connector_journey_network_unreachable_is_degraded`
- `test_senate_lda_anonymous_metadata_path_is_no_key_secondary_journey`
