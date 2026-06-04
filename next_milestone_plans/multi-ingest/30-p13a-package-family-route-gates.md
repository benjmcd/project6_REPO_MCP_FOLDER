# Phase P13A Package-Family Route Policy Gates

Status: implemented as route-level package-family policy hardening; mixed-source runtime behavior remains not admitted.

## Scope

This phase wires the P13 package-family policy registry into the existing Layer 3 package lifecycle routes:

- package-review preview
- package construction commit
- package-review submit
- handoff/export prepare

The route gates derive package family from server-owned selected-pass result-review state. They reject `mixed_dataset_document` and unknown package families before package preview, package construction, package-review submit, or handoff/export effects can be computed or persisted.

## Behavior Boundary

Existing admitted package families keep their current route behavior:

- `dataset_version`
- `associated_cohort`
- `qualitative_aps_document`
- `source_intake_qualitative`

The gate does not enable mixed-source package review preview, package construction, package-review submit, handoff, export, schema changes, migrations, parser behavior, source-shape expansion, generic XML/HTML admission, archive-member orchestration, legacy CSV bridge deprecation, or excluded-tool work.

## Verification

Branch-local verification on `codex/pkg-gates-0604`:

- `python -B -m py_compile .\backend\app\services\layer3_package_family_policy.py .\backend\app\services\layer3_workbench_package_state.py .\backend\app\services\layer3_workbench.py .\backend\app\api\layer3.py`
- `python -B -m pytest .\backend\tests\test_layer3_package_family_policy.py .\backend\tests\test_layer3_workbench_package_state.py .\backend\tests\test_layer3_package_review_contract.py .\backend\tests\test_layer3_package_submit_response.py -q`
- `python -B -m pytest .\backend\tests\test_layer3_api.py -q -k "mixed_source_package_readiness or material_preview_surfaces_mixed_source_package_readiness or package_review_preview_requires_approved_result_review_and_is_read_only or package_construction_commit_materializes_three_packages_idempotently or package_review_submit_records_decision_without_mutating_packages or handoff_export_prepare_records_reference_envelope_without_side_effects or package_review_submit_prechecks_fail_closed or package_construction_commit_prechecks_fail_closed or package_review_preview_prechecks_fail_closed or package_review_preview_blocks_unadmitted_package_family or package_construction_commit_blocks_unadmitted_package_family or package_review_submit_blocks_unadmitted_package_family or handoff_export_prepare_blocks_unadmitted_package_family"`
- `python -B -m pytest .\backend\tests\test_layer3_source_directory_qualitative_analysis.py .\backend\tests\test_layer3_source_directory_vector_retrieval.py -q -k "package_commit or package_review_submit or handoff_export_prepare or external_export_download"`

Observed focused results:

- Package-family/package-state/contract/submit response slice: `42 passed, 2 warnings`.
- Mixed readiness plus package lifecycle route slice: `12 passed, 269 deselected, 3 warnings`.
- Source-directory package/handoff/export compatibility slice: `16 passed, 26 deselected, 3 warnings`.

## Residual Work

The next implementation pass may implement read-only mixed-source package review preview only if it derives authority from P11 material-preview readiness, satisfies the P12 contract requirements, consumes the P13/P13A policy gates, and keeps mixed-source commit, submit, handoff, export, parser, schema, source-shape, and excluded-tool behavior blocked.
