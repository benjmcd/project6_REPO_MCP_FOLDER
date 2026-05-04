# Phase P10B Closeout: Layer 3 Typed/Refused Source-Family Surfacing

Status: implemented in the `codex/l3-typed-ui-p10` worktree.

## Scope

Phase P10B is a bounded Layer 3 workbench surfacing pass. It does not add parsers, schema changes, migrations, new Layer 3 source shapes, Candidate B runtime changes, document trace behavior, or mixed-source package semantics.

The phase uses existing backend authority:

- APS-derived `DatasetVersion` rows remain the selectable Layer 3 source shape.
- `DatasetSourceProvenance` remains the source authority for parser family and typed-content contract metadata.
- The Layer 3 candidate endpoint now also returns admitted/materialized source-family metadata and non-selectable deferred/refused guardrails.

## Implemented Boundary

- The candidate endpoint identifies server-backed materialized table families for CSV, XLSX, JSON recordset, and bounded SEC/EDGAR complete-submission text table outputs.
- Candidate rows carry `source_family`, `source_family_label`, `source_admission_state`, and `source_family_scope`.
- Material preview carries source-family metadata into source provenance and load summary for selected APS-derived dataset versions.
- The Layer 3 workbench candidate panel displays admitted/materialized source-family scope and deferred/refused guardrails.
- Static workbench copy no longer implies the panel is CSV-only.

## Explicit Non-Goals

- No XML, HTML, or inline-XBRL parser admission.
- No broad workbook semantics.
- No archive-member XLSX/JSON/SEC-EDGAR table materialization orchestration.
- No new `aps_dataset_version` source shape.
- No schema/model/migration changes.
- No document trace or PDF/Candidate B rendering changes.
- No mixed narrative-plus-table package governance.

## Validation Plan

Required local validation:

- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_page.py -q`
- `python -m pytest .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_api.py -k "dataset_version_candidates or aps_derived_dataset_version" -q`
- `npm run validate:structure`
- `git diff --check`

Because UI assets changed, browser validation is also required before landing:

- Headless Chrome coverage for the Layer 3 workbench route.
- Headed Chrome coverage for the same route.
- Compare the candidate-panel rendering and console/runtime behavior across both.

## Residual Caveats

- The candidate panel now distinguishes admitted/materialized families from deferred/refused guardrails, but it is not a full trace/detail page.
- Refused/deferred families are explanatory guardrails, not selectable source classes.
- A future trace/detail pass may still be needed if operators need per-artifact refused-member inspection from the Layer 3 workbench.

## Next

Do not repeat P10A/P10B in the next PR. The next bounded tranche should be either a deeper typed/refused trace/detail UI pass backed by server authority, or a separately specified SEC/EDGAR HTML/XML/inline-XBRL parser contract.
