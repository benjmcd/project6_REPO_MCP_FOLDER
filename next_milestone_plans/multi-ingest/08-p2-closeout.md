# Phase P2 Closeout

Status: implementation closeout for the parser registry skeleton in this branch.

## Implemented Boundary

Phase P2 adds parser-family admission metadata for the processor families already implemented in the repo. It does not rewrite processor execution, add new parser behavior, materialize datasets, change schema, alter Layer 3 source admission, or change UI behavior.

Implemented:

- `nrc_aps_parser_registry` defines `aps_parser_registry_v1`.
- The registry admits current baseline PDF, Candidate B PDF, plain text, image OCR, and archive bundle processors.
- Registry resolution returns stable parser registry contract id, version, admission status, parser family, parser output family, and parser contract id.
- Unsupported parser lookups fail closed with stable parser failure codes.
- Candidate B is admitted only for `application/pdf`.
- Existing document-processing output payloads now include parser-registry metadata.
- Connector diagnostics and extraction payloads now preserve parser-registry metadata.
- Focused tests prove current parser admission and unsupported lookup behavior.

Not implemented:

- CSV parser.
- Spreadsheet parser.
- JSON recordset parser.
- SEC/EDGAR filing parser.
- Dataset bridge.
- Schema/model/migration changes.
- Layer 3 source preview/material preview/typing expansion.
- UI or browser behavior changes.
- Parser execution through the registry.

## Files Changed

Runtime/source:

- `backend/app/services/nrc_aps_parser_registry.py`
- `backend/app/services/nrc_aps_document_processing.py`
- `backend/app/services/connectors_nrc_adams.py`

Tests:

- `tests/test_nrc_aps_parser_registry.py`
- `tests/test_nrc_aps_document_processing.py`
- `tests/test_nrc_aps_expansion.py`

Planning docs:

- `next_milestone_plans/multi-ingest/README.md`
- `next_milestone_plans/multi-ingest/01-live-audit.md`
- `next_milestone_plans/multi-ingest/03-implementation.md`
- `next_milestone_plans/multi-ingest/04-validation.md`
- `next_milestone_plans/multi-ingest/05-decisions.md`
- `next_milestone_plans/multi-ingest/06-adequacy-audit.md`
- `next_milestone_plans/multi-ingest/08-p2-closeout.md`

## Validation

Passed:

- `python -m pytest .\tests\test_nrc_aps_parser_registry.py .\tests\test_nrc_aps_media_detection.py .\tests\test_nrc_aps_artifact_ingestion.py .\tests\test_nrc_aps_document_processing.py .\tests\test_nrc_aps_expansion.py -k "not candidate_b"`

Result:

- `55 passed, 9 deselected`.

Known validation caveat:

- Pytest emitted a Windows temp cleanup `PermissionError` after the green result for `pytest-current`. The command exit code was still successful.
- Candidate B integration tests remain excluded from this focused command because the local `opendataloader-pdf` package version mismatch was already identified during P1 validation.

Not run:

- Browser tests, because no UI assets changed.
- Full backend suite, because P2 touched a narrow registry/document-processing diagnostics surface and the focused suite covers the affected admission paths.

## Scope Recheck

No-go boundaries preserved:

- Candidate B remains PDF-only.
- Existing PDF/text/image/generic-ZIP processing remains admitted.
- CSV/spreadsheet/JSON/XML/HTML are not parsed.
- Typed data is not materialized into datasets.
- Layer 3 still admits only the existing `dataset_version` and `aps_content_document` source classes.
- The registry is not yet the execution dispatcher for parser implementations.
- The planning pack remains outside the settled progress-manifest spine until a separate governance sync admits it.

## Historical Next Action

At P2 closeout time, the next implementation tranche was Phase P3: a narrow CSV/delimited table parser and typed diagnostics. That tranche is now implemented and recorded in `09-p3-closeout.md`.

P3 should admit only bounded CSV/delimited inputs through the registry, prove positive and negative fixtures, and still avoid dataset materialization unless the dataset bridge is explicitly included in that phase. This preserves the non-fragility requirement: parser admission remains separate from dataset bridge, Layer 3 source admission, and UI projection.
