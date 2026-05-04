# Phase P10C Closeout: Selected-Material Trace Detail

Status: implemented in the `codex/l3-typed-trace-p11` worktree.

## Scope

Phase P10C is a bounded Layer 3 workbench trace/detail pass for selected APS-derived `DatasetVersion` material. It does not add parsers, schema changes, migrations, new Layer 3 source shapes, Candidate B runtime changes, document trace behavior, or mixed-source package semantics.

The phase uses existing backend authority:

- Explicit `dataset_version_ids` remain the selection mechanism.
- `Dataset`, `DatasetVersion`, `VariableDefinition`, and `DatasetSourceProvenance` remain the trace sources.
- The Gate B material ledger is the rendering surface because the trace is attached to selected material candidates, not to unselected source-family guardrails.

## Implemented Boundary

- Material preview emits `source_trace` for selected APS-derived `DatasetVersion` candidates.
- `source_trace` carries dataset/version identity, variable summary, storage availability, parser family, parser contract, typed content contract, source artifact key, diagnostics ref, target id, accession number, table index, and table hash where present.
- The same trace detail is nested under `source_provenance` so Gate B persistence carries it into `L3MaterialSnapshot.source_provenance_json`.
- The Layer 3 Gate B material ledger displays the selected-material trace card without requiring raw JSON inspection.
- The material filter can match trace fields such as parser family and typed content contract id.

## Explicit Non-Goals

- No document trace or Candidate B PDF trace changes.
- No XML, HTML, or inline-XBRL parser admission.
- No broad workbook semantics.
- No archive-member typed orchestration.
- No new `aps_dataset_version` source shape.
- No schema/model/migration changes.
- No mixed narrative-plus-table package governance.

## Validation Plan

Required local validation:

- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_page.py -q`
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -k "aps_derived_dataset_version" -q`
- `npm run validate:structure`
- `git diff --check`

Because UI assets changed, browser validation is also required before landing:

- Headless Chrome coverage for the Layer 3 workbench route.
- Headed Chrome coverage for the same route.
- Compare the selected-material trace card rendering and console/runtime behavior across both.

## Residual Caveats

- P10C covers selected APS-derived `DatasetVersion` material only.
- Unselected deferred/refused families remain guardrails, not traceable material objects.
- Document/refused/mixed-source trace detail remains future work unless a later phase adds server authority for those surfaces.

## Next

Do not repeat P10A/P10B/P10C in the next PR. The next bounded tranche should be either document/refused/mixed-source trace/detail surfacing backed by server authority, or a separately specified SEC/EDGAR HTML/XML/inline-XBRL parser contract.
