# Post-review patch summary

## Main changes

1. Replaced runtime row-store usage with file-backed dataset-version storage.
   - `dataset_version.storage_ref` now points to a Parquet file.
   - `load_version_dataframe()` reads from `storage_ref` instead of hydrating `DatasetRow` objects.
   - The relational database remains the control plane for lineage, profiling, transformations, assumptions, caveats, and artifacts.

2. Added real stationarity checks to profiling.
   - ADF and KPSS are executed when `detect_stationarity=true`.
   - `stationarity_hint` is now derived from actual test outcomes instead of returning `not_tested`.

3. Added response models.
   - Upload, dataset, profile, transformation, annotation, recommendation, and analysis-run routes now declare `response_model`.

4. Improved routing and caveat quality.
   - `recommend_analysis()` uses profiling context.
   - `AnalysisRun.route_reason` now carries real rationale rather than a placeholder string.
   - Cross-correlation assumption checks now record stationarity profile context.

5. Fixed repo hygiene.
   - Added `.gitignore` for local databases, caches, and storage artifacts.
   - Cleaned committed evaluation outputs from the delivered repo bundle.

## Validation

- Local tests: `3 passed`
- Targeted real-data sample summary: `{'n': 30, 'upload_200': 30, 'profile_200': 30, 'recommend_200': 30, 'transform_ok': 30, 'analysis_200': 30, 'stationarity_any': 29}`

## Remaining limits

- `DatasetRow` model still exists for compatibility but is no longer used by the runtime storage path.
- The Alembic migration scaffold was not fully reworked around removal of `DatasetRow`; the runtime path no longer depends on it.
- Seasonality detection is still heuristic.
- Analysis catalog is still narrow: cross-correlation only.
