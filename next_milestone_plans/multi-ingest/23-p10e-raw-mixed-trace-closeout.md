# Phase P10E Closeout

Status: implemented as bounded server-owned raw mixed materialization trace labeling.

## Scope

Phase P10E improves operator trace clarity for the already-admitted server-owned raw mixed materialization sentinel. It makes the Layer 3 DatasetVersion candidate and selected-material trace surfaces label `raw_mixed_materialized` provenance as `server_owned_raw_mixed` instead of inheriting a lower-level parser-family label such as CSV.

The phase is limited to provenance-aware source-family metadata. It does not add parser behavior, source shapes, schema changes, migrations, browser behavior, package construction behavior, broad mixed-source semantics, generic XML/HTML admission, archive-member orchestration, or Onlook work.

## Implemented Boundary

- `layer3_aps_source_family.py` now has a provenance-aware source-family helper.
- Server-owned raw mixed materialization is labeled only when provenance reports:
  - `source_system="local_operator_staged_server_owned_manifest"`;
  - `source_mode="raw_mixed_materialized"`.
- Candidate rows and selected-material source provenance now surface:
  - `source_family="server_owned_raw_mixed"`;
  - `source_family_label="Server-owned raw mixed materialization"`;
  - scope text stating that mixed package semantics remain separately governed.
- Existing admission checks still reject unrecognized raw mixed source systems and APS raw-mixed shortcuts without the server-owned sentinel.

## Validation Targets

Required checks for this tranche:

- `python -m pytest .\backend\tests\test_layer3_aps_source_family.py .\backend\tests\test_layer3_workbench.py -q`
- `python .\tools\validate_structure.py`
- `python .\tools\l3-progress-check.py`
- `python .\tools\l3-target-selection-validate.py --expect frozen`
- `git diff --check`

Browser validation is not required for this tranche unless UI assets change. The rendered workbench already consumes candidate/material source-family labels; this phase changes backend metadata only.

## Residual Boundary

P10E does not settle refused-artifact trace-detail pages, mixed qualitative-plus-table package semantics, archive-member typed orchestration, or legacy CSV bridge deprecation. The next implementation should continue to choose among those separately governed tracks rather than treating raw mixed trace labeling as a package-semantics admission.
