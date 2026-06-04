# Phase P11 Mixed-Source Package Readiness Closeout

Status: implemented as a bounded material-preview readiness projection.

## Scope

This phase connects already-admitted `dataset_version` and `aps_content_document` material authority to a read-only mixed-source package semantics readiness contract.

The implementation adds `mixed_source_package_semantics` to the Layer 3 material-preview service and API response. When valid `dataset_version` and `aps_content_document` material candidates are selected together, the response states that mixed material authority is present and that governed package semantics are still required.

## Boundaries

This phase does not:

- change schema or migrations;
- add parser behavior;
- add a new Layer 3 source shape;
- admit generic XML/HTML;
- orchestrate archive members;
- construct mixed-source packages;
- enable package review preview or commit for mixed sources;
- enable handoff for mixed sources;
- define narrative-table linking or payload semantics;
- include Onlook work.

## Contract

The readiness projection uses schema id `layer3.mixed_source_package_semantics_readiness.v1`.

For valid mixed selections, it reports:

- `material_authority_state`: `mixed_material_authority_present`;
- `package_semantics_state`: `governed_contract_required`;
- `package_construction_enabled`: `false`;
- `package_review_preview_enabled`: `false`;
- `handoff_enabled`: `false`;
- `next_allowed_actions`: `["define_mixed_source_package_contract"]`.

P14 current-runtime note: after the P12 contract, P13 policy registry, and P13A
route gates landed, the material-preview readiness surface now advertises
read-only preview admission with `next_allowed_actions` set to
`["commit_gate_b_material_decision"]`. The P11 closeout above remains the
historical pre-contract readiness boundary.

If both material classes are not validly present, it reports that mixed material authority is not present and directs the operator to select both material classes.

## Validation

Validation performed in this branch:

- `python -m py_compile .\backend\app\services\layer3_workbench.py .\backend\app\api\layer3.py`
- `python -m pytest .\backend\tests\test_layer3_workbench.py -q -k "mixed_source_package_readiness or aps_derived_dataset_version_flows or aps_content_document_flows"`
- `python -m pytest .\backend\tests\test_layer3_api.py -q -k "material_preview_surfaces_mixed_source_package_readiness or first_slice_preview_openapi_contracts"`
- `git diff --check`

Results:

- py_compile passed.
- Workbench focused tests: `3 passed, 24 deselected`.
- API focused runtime/OpenAPI tests: `2 passed, 275 deselected`.
- `git diff --check` found no whitespace errors.

Warnings were limited to existing local dependency warnings from Starlette multipart, pypdf cryptography, and requests dependency versions.

## Residual Work

The next pass should define the governed mixed-source package contract before enabling package construction. That contract must specify narrative-table linking, payload semantics, review preview requirements, package commit behavior, and handoff policy.

Legacy CSV bridge deprecation remains a separate decision. Runtime and tests still encode compatibility between `csv_dataset_bridge_enabled` and `table_dataset_bridge_enabled`, so deprecation should not be coupled to this phase.
