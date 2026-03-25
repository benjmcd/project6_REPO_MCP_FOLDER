# Decomposition + Structural Break Patch Summary

## Implemented changes

- Updated cross-correlation stationarity assumption result derivation to use profiled stationarity hints instead of a hardcoded `warn`.
- Added `decomposition` analysis method using `statsmodels.tsa.seasonal.STL`.
- Added `structural_break` analysis method using `ruptures.Pelt(model="rbf")`.
- Persisted per-variable PNG and JSON artifacts for both methods when prerequisites are satisfied.
- Persisted assumption checks for:
  - `sufficient_observations`
  - `time_regularity`
  - `stationarity_of_residual`
  - `minimum_segment_length`
  - `stationarity_required_for_break_test`
- Persisted method caveats for penalty sensitivity and nonstationary-series interpretation.
- Updated analysis recommendation routing:
  - multivariate time series -> `cross_correlation`, `decomposition`, `structural_break`
  - univariate time series -> `decomposition`, `structural_break`
- Extended `tools/run_attached_dataset_eval.py` to support method selection and sample-file based evaluation.
- Added integration tests covering decomposition artifact creation, structural break artifact creation, and graceful short-series caveat behavior.

## Validation

### Repo tests

- `pytest -q` -> **5 passed**

### 30-file sample evaluation

Files evaluated from `/mnt/data/postreview_sample.csv`.

#### Decomposition

- upload/profile/recommend/transform/analyze: **30/30 succeeded**
- non-200 analysis responses: **0**
- runs with artifacts: **0/30**
- runs with caveats only: **30/30**

Reason the artifact count is zero on this sample: the selected USGS sample is dominated by *salient* tables with only **5 yearly observations per transformed series**, while the decomposition method intentionally requires **>=24 observations**. The code now records caveats instead of throwing exceptions on that path.

#### Structural break

- upload/profile/recommend/transform/analyze: **30/30 succeeded**
- non-200 analysis responses: **0**
- runs with artifacts: **0/30**
- runs with caveats only: **30/30**

This sample is likewise dominated by short annual series, so break detection generally falls into the caveat path after prerequisite checks.

### Positive artifact validation

The integration test `test_decomposition_and_break_detection_persist_artifacts` uses a 36-month synthetic series and confirms that both methods persist artifacts successfully on an eligible time series.
