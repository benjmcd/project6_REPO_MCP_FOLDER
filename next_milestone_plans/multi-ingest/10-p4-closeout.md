# Phase P4 Closeout

Status: historical implementation closeout for the callable CSV dataset bridge in this branch. Phase P4.5 supersedes the connector-orchestration residual noted here.

## Implemented Boundary

Phase P4 materializes admitted CSV parser output into existing dataset authority when explicitly invoked. It does not automatically run during connector finalization, alter Layer 3 source admission, change schema, or add UI behavior.

Implemented:

- `nrc_aps_dataset_bridge` defines `aps_csv_dataset_bridge_v1`.
- The bridge accepts CSV parser output from target artifact payloads.
- The bridge creates deterministic `Dataset` and `DatasetVersion` ids for the same source artifact key, parser contract, table index, and table hash.
- The bridge writes dataframe storage, `VariableDefinition` rows, numeric `VariableProfile` rows, and `DatasetRow` JSON rows.
- The bridge records `DatasetExternalIdentity` and `DatasetSourceProvenance` using existing models.
- Re-running the same content/parser contract returns the existing dataset version without duplicate dataset rows, provenance, or identities.
- Non-CSV parser output fails closed.

Not implemented:

- Connector auto-orchestration of bridge materialization.
- Layer 3 source preview/material preview/typing admission for APS-derived datasets.
- UI or browser behavior changes.
- Schema/model/migration changes.
- Spreadsheet parser.
- JSON recordset parser.
- SEC/EDGAR filing parser.

## Files Changed

Runtime/source:

- `backend/app/services/nrc_aps_dataset_bridge.py`

Tests:

- `tests/test_nrc_aps_dataset_bridge.py`

Planning docs:

- `next_milestone_plans/multi-ingest/README.md`
- `next_milestone_plans/multi-ingest/01-live-audit.md`
- `next_milestone_plans/multi-ingest/03-implementation.md`
- `next_milestone_plans/multi-ingest/04-validation.md`
- `next_milestone_plans/multi-ingest/05-decisions.md`
- `next_milestone_plans/multi-ingest/06-adequacy-audit.md`
- `next_milestone_plans/multi-ingest/09-p3-closeout.md`
- `next_milestone_plans/multi-ingest/10-p4-closeout.md`

## Validation

Passed:

- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py`
- `python -m pytest .\tests\test_nrc_aps_dataset_bridge.py .\tests\test_nrc_aps_content_index.py .\tests\test_nrc_aps_csv_parser.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- Bridge-only: `3 passed`.
- Focused suite: `79 passed, 9 deselected`.

Known validation caveat:

- Pytest emitted the known Windows temp cleanup `PermissionError` after the green result for `pytest-current`. The command exit code was still successful.
- Candidate B integration tests remain excluded from this focused command because the local `opendataloader-pdf` package version mismatch was already identified during P1 validation.

Not run:

- Browser tests, because no UI assets changed.
- Full backend suite, because P4 touched a bounded dataset-bridge service and the focused suite covers the affected parser, content-index, document-processing, and bridge paths.

## Scope Recheck

No-go boundaries preserved:

- Candidate B remains PDF-only.
- Existing PDF/text/image/generic-ZIP document behavior remains admitted.
- CSV bridge materialization is explicit/callable, not automatic connector behavior.
- Layer 3 still admits only the existing source classes; no APS-derived dataset source projection was added.
- Spreadsheet/JSON/XML/HTML/SEC parser behavior remains deferred or refused according to current media policy.
- The planning pack remains outside the settled progress-manifest spine until a separate governance sync admits it.

## Next Action

This P4 closeout is historical. The next implementation tranche at the time was connector/runtime orchestration for the CSV dataset bridge or Layer 3 typed dataset admission.

Connector/runtime orchestration was subsequently implemented as Phase P4.5 behind an explicit config gate. The remaining next slice is Layer 3 typed dataset admission.
