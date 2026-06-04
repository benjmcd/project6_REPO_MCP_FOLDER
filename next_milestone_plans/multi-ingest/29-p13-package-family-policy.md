# Phase P13 Package-Family Policy Registry

Status: implemented as a no-behavior-change package-family policy registry; mixed-source runtime behavior remains not admitted.

## Scope

This phase implements the package-family policy registry required by Phase P12 before any mixed-source package runtime work.

The registry owner is `backend/app/services/layer3_package_family_policy.py`. It records package-family admission answers for:

- `dataset_version`
- `associated_cohort`
- `qualitative_aps_document`
- `source_intake_qualitative`
- `mixed_dataset_document`

For each family, the registry answers preview, commit, submit, and handoff admission independently, preserves candidate package-kind ordering, and exposes the downstream actions that remain unavailable at preview, construction, submit, and handoff stages.

## Behavior Boundary

This pass is intentionally behavior-preserving for existing package families. Existing package-review preview, construction commit, package-review submit, and handoff/export prepare paths keep their current endpoint signatures and response shapes.

The mixed family `mixed_dataset_document` is explicitly registered but remains blocked for:

- package-review preview
- package construction commit
- package-review submit
- handoff
- export
- APS handoff
- external export/download
- connector dispatch
- provider-public URL behavior

Unknown package families fail closed with the same blocked downstream posture.

## Non-Goals

This pass does not enable mixed-source package review preview, package construction, package-review submit, handoff, export, schema changes, migrations, parser behavior, source-shape expansion, generic XML/HTML admission, archive-member orchestration, legacy CSV bridge deprecation, or Onlook work.

It does not add endpoint request fields, caller-supplied family admission, durable rows, frontend controls, generated artifacts, or runtime package payload semantics.

## Verification

Branch-local verification:

- `python -m py_compile .\backend\app\services\layer3_package_family_policy.py .\backend\app\services\layer3_workbench_package_state.py`
- `python -m pytest .\backend\tests\test_layer3_package_family_policy.py .\backend\tests\test_layer3_workbench_package_state.py .\backend\tests\test_layer3_package_review_contract.py -q`

Focused pytest result: `39 passed, 2 warnings`. The warnings are dependency warnings from `pypdf` and `requests`, not registry failures.

## Residual Work

The next implementation pass may implement read-only mixed-source package review preview only if it consumes this registry, derives authority from the P11 material-preview readiness response and P12 contract, and keeps mixed-source commit, submit, handoff, export, parser, schema, source-shape, and Onlook behavior blocked.

Legacy CSV bridge deprecation remains a separate decision and must not be coupled to mixed-source package semantics.
