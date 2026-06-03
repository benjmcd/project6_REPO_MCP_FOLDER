# Phase P10F Closeout

Status: implemented as bounded refused/deferred source-family guardrail trace detail.

## Scope

Phase P10F strengthens the existing Layer 3 APS source-family guardrail panel by adding server-owned trace-detail records for refused/deferred source families. It makes non-selectable families auditable without turning them into material candidates.

The phase is limited to `APS_NOT_ADMITTED_SOURCE_FAMILIES` guardrail metadata and its existing workbench rendering. It does not add refused artifact candidates, parser behavior, source shapes, schema changes, migrations, package construction behavior, mixed-source package semantics, generic XML/HTML admission, archive-member orchestration, or Onlook work.

## Implemented Boundary

- `layer3_aps_source_family.py` now emits `layer3.aps_source_family_guardrail_trace.v1` records for refused/deferred guardrails.
- Guardrail trace detail records state:
  - `trace_readiness="guardrail_not_selectable"`;
  - `selectable=false`;
  - materialization state for refused versus deferred families;
  - parser-admission policy authority and no selection authority.
- The Layer 3 workbench source-family summary renders those trace details in the existing deferred/refused guardrail panel.
- The API continues to expose only materialized `DatasetVersion` choices as selectable candidates.

## Validation Targets

Required checks for this tranche:

- `python -m pytest .\backend\tests\test_layer3_aps_source_family.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_page.py -q`
- `python .\tools\validate_structure.py`
- `python .\tools\l3-progress-check.py`
- `python .\tools\l3-target-selection-validate.py --expect frozen`
- `git diff --check`

Browser validation is required for this tranche because rendered workbench assets changed. The focused browser proof is the existing Layer 3 workbench source-family guardrail E2E, which now asserts the trace detail is visible.

## Residual Boundary

P10F does not settle per-artifact refused trace pages, mixed qualitative-plus-table package semantics, archive-member typed orchestration, or legacy CSV bridge deprecation. The next implementation should continue to choose among those separately governed tracks rather than treating guardrail trace detail as parser admission or materialization.
