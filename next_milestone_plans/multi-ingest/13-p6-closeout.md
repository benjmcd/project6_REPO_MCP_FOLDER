# Phase P6 Closeout: APS-Derived Dataset Execution And Package Proof

Status: implemented in the current branch on 2026-05-03.

## Scope

Phase P6 proves that an explicitly selected APS-derived `DatasetVersion` can move past Layer 3 admission into selected-pass execution, result review, package preview, and package construction commit.

This is a selected-pass quantitative package proof. It is not an APS document evidence-bundle handoff proof and it is not a mixed qualitative-plus-table package contract.

## Implemented Boundary

- `backend/tests/test_layer3_api.py` now proves an APS-derived CSV bridge dataset reaches plan approval, execution selection, execution start, result status, result review, package preview, and package commit.
- `backend/app/services/layer3_workbench.py` now derives package response `source_shape="dataset_version"` for single dataset-version selected-pass packages.
- The same package response now exposes `source_dataset_version_ids` for single dataset-version packages instead of only cohort packages.
- Existing associated-cohort behavior remains unchanged and continues to use `source_shape="aligned_wide_table"` with cohort dataset ids.

## Explicit No-Go Boundary

- No schema or migration changes.
- No UI changes.
- No new parser families.
- No new source shape.
- No APS document evidence-bundle handoff claim for typed dataset packages.
- No mixed qualitative/table package semantics.

## Validation

Commands run:

- `python -m py_compile .\backend\app\services\layer3_workbench.py .\backend\tests\test_layer3_api.py`
- `python -m pytest .\backend\tests\test_layer3_api.py -k "aps_derived_dataset_version_reaches_package_commit"`
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py`
- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_api.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -k "not candidate_b"`

Results:

- Py-compile checks passed.
- Layer 3 API focused selection: `1 passed, 73 deselected`.
- Full Layer 3 workbench/API files: `84 passed`.
- Combined APS bridge/parser/media/document plus Layer 3 regression: `227 passed, 10 deselected`.

Caveat:

- The pytest command exited successfully but emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Residual Work

- Bounded APS-derived CSV `DatasetVersion` UI/operator selection was added in Phase P10A; see `14-p10a-closeout.md`.
- Add mixed-source package contracts separately if SEC/EDGAR or other mixed qualitative-plus-table parsers are admitted.
