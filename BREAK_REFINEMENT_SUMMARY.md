# Break / Decomposition Refinement Summary

## Changes applied

### 1. Structural break model default
- Structural break detection now defaults to `ruptures.Pelt(model="l2")` instead of `model="rbf"`.
- The `model` is exposed through `run.parameters_json` and recorded in artifacts and caveats.
- A caveat is written when a non-`l2` model is chosen because that changes interpretation from mean-shift style breaks toward broader distributional change detection.

### 2. Residual caching / reuse
- `structural_break` now attempts to reuse the latest persisted `decomposition_components` artifact for the same dataset version and variable when the current run is not window-scoped.
- If a cached decomposition artifact is found, the break detector uses `cached_stl_residual` instead of recomputing STL.
- If no cached artifact exists, it falls back to computing STL locally and then to raw differenced data when STL cannot run.

### 3. Zero-breakpoint behavior
- Runs with zero internal breakpoints no longer emit blank-line plot artifacts.
- Instead they write a `no_breakpoints_detected` caveat for the variable.
- Global `no_structural_break_artifacts` is still emitted when no variables produce break artifacts.

### 4. STL period selection priority
- `_choose_stl_period` now prioritizes explicit/inferred frequency hints before consulting seasonality autocorrelation lag.
- `best_lag` is now treated as `seasonality_profile_fallback` rather than first choice.
- When this fallback is used, decomposition writes a caveat noting that autocorrelation lag can represent a harmonic rather than the fundamental seasonal period.

### 5. Test and harness updates
- Added a test that confirms structural break reuses cached STL residuals and records `model_used == "l2"`.
- Added a test for the zero-breakpoint path to ensure it emits caveats rather than empty artifacts.
- Updated the attached-dataset evaluation harness to accept `--break-model` and pass it to `structural_break` runs.

## Validation

### Repo tests
- `pytest -q` => `6 passed`

### Real-data sample rerun
Using the same 30-file salient sample:
- `decomposition`: 30 / 30 uploads succeeded, 30 / 30 analysis calls returned 200, 0 exceptions, 0 persisted artifacts (sample remains ineligible because series are too short for STL)
- `structural_break`: 30 / 30 uploads succeeded, 30 / 30 analysis calls returned 200, 0 exceptions, 0 persisted artifacts (same eligibility constraint; now this path emits caveats instead of blank artifacts)

## Limits that remain
- STL reuse currently reads persisted decomposition JSON artifacts rather than a binary residual sidecar. This is enough to avoid recomputation without changing schema, but it is not the most efficient possible representation.
- Frequency inference is still heuristic when no explicit frequency hint exists.
- The salient commodity sample still does not qualify for decomposition/break artifacts because transformed series typically have only 5 annual observations.
