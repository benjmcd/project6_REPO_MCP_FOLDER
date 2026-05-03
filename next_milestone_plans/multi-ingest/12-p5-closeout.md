# Phase P5 Closeout: Layer 3 APS-Derived Dataset Admission

Status: implemented in the current branch on 2026-05-03.

## Scope

Phase P5 admits explicitly selected APS-derived `DatasetVersion` records into the Layer 3 workbench using the existing `dataset_version` source shape.

This phase does not add a new source class. The repo already had downstream Layer 3 typing and pass-entry logic for `dataset_version`; the missing boundary was real material-preview and Gate B persistence of dataset identity/provenance from APS CSV bridge output.

## Implemented Boundary

- `backend/app/services/layer3_workbench.py` now accepts optional DB-backed `dataset_version_ids` in material preview.
- Material preview projects `Dataset`, `DatasetVersion`, `VariableDefinition`, and APS `DatasetSourceProvenance` fields into candidate source identity, source provenance, payload, and load summary.
- APS-derived provenance is identified by `DatasetSourceProvenance.source_system="nrc_adams_aps"` and serialized with source artifact key, target/accession references, parser family, parser contract, typed content contract, diagnostics ref, and table hash.
- Gate B persists echoed real source identity/provenance into `L3MaterialSnapshot`.
- Gate C reuses the existing `dataset_version` quantitative typing rule.
- Plan preview reuses existing pass-entry admission and preserves `dataset_version_id` in planned passes.
- `backend/app/api/layer3.py` now passes a DB session to material preview and documents optional top-level or filter-level `dataset_version_ids`.

## Explicit No-Go Boundary

- No schema or migration changes.
- No UI changes.
- No new Layer 3 source class.
- No automatic discovery or selection of all bridged datasets.
- No change to `aps_content_document` qualitative document behavior.
- No broad parser support claim for JSON, spreadsheets, SEC/EDGAR, XML, HTML, or mixed document/table packages.

## Validation

Commands run:

- `python -m py_compile .\backend\app\services\layer3_workbench.py .\backend\app\api\layer3.py .\backend\tests\test_layer3_workbench.py`
- `python -m py_compile .\backend\app\api\layer3.py .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_workbench.py`
- `python -m pytest .\backend\tests\test_layer3_workbench.py`
- `python -m pytest .\backend\tests\test_layer3_api.py -k "aps_derived_dataset_version or first_slice_preview_openapi_contracts or full_first_slice_flow"`

Results:

- Py-compile checks passed.
- Layer 3 workbench focused file: `10 passed`.
- Layer 3 API focused selection: `3 passed, 71 deselected`.

Caveat:

- The pytest commands exited successfully but emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`.

## Residual Work

- UI/operator selection for APS-derived dataset versions is now addressed by bounded Phase P10A; see `14-p10a-closeout.md`.
- Backend execution/package proof is recorded in `13-p6-closeout.md`.
- Add broader parser families only in separate slices after backend contracts are defined and tested.
- Add mixed qualitative-plus-table package semantics only after there are at least two proven typed parser families and a defined Layer 3 packaging contract.
