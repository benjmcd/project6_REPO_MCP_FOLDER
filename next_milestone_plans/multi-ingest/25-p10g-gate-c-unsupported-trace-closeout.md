# Phase P10G Closeout

Status: implemented as bounded Gate C unsupported material snapshot trace detail.

## Scope

Phase P10G adds per-artifact trace detail for material snapshots that reach Gate C but cannot be typed because their owner-service source shape has no admitted typing rule.

The phase is limited to existing `L3MaterialSnapshot` authority and existing Gate C `unsupported_material` output. It does not add parser behavior, source shapes, schema changes, migrations, selectable refused material, generic XML/HTML admission, archive-member orchestration, mixed-source package semantics, or Onlook work.

## Implemented Boundary

- `layer3_sublayer_state.snapshot_projection()` now attaches `layer3.gate_c_unsupported_material_trace.v1` detail to unsupported snapshots.
- Trace detail records include:
  - material snapshot identity;
  - owner-service source shape;
  - source plane, payload hash, and co-retrieval group;
  - source identity, source provenance, and load summary;
  - `admission_state="not_admitted_to_gate_c_typing"`;
  - `selectable=false`;
  - no selection authority.
- Gate C preview still returns `blocked_typing_unavailable` when unsupported material is present.
- The Layer 3 workbench renders unsupported snapshot trace detail in the existing Gate C panel.

## Validation Targets

Required checks for this tranche:

- `python -m pytest .\backend\tests\test_layer3_sublayer_state.py .\backend\tests\test_layer3_workbench.py .\backend\tests\test_layer3_page.py -q`
- `python .\tools\validate_structure.py`
- `python .\tools\l3-progress-check.py`
- `python .\tools\l3-target-selection-validate.py --expect frozen`
- `git diff --check`

Browser validation is required for this tranche because rendered workbench assets changed. The focused browser proof is the existing unsupported-only Gate C E2E, which now asserts unsupported material trace detail is visible and no 3C routed input is created.

## Residual Boundary

P10G does not settle parser-level refused artifact pages, mixed qualitative-plus-table package semantics, archive-member typed orchestration, or legacy CSV bridge deprecation. It only makes the existing Gate C unsupported material snapshot boundary inspectable without reading raw JSON.
