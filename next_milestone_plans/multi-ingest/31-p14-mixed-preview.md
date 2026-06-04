# P14 Mixed-Source Package Review Preview

Status: current-main implemented read-only mixed-source package review preview runtime. PR #2185 landed the runtime and planning/proof packet; PR #2186 repaired the package-review preview OpenAPI request-shape contract so selected-pass and material-preview requests are mutually exclusive, including partial cross-shape fields.

## Scope

This phase admits only package-review preview for `mixed_dataset_document` authority derived from:

- P11 material-preview readiness over valid `dataset_version` plus `aps_content_document` candidates.
- A committed Gate B material decision on the session.
- The P12 governed mixed-source package contract.
- The P13 package-family policy registry and P13A route-level gates.

The preview request shape is `session_id` plus `material_preview_id` and `material_preview_hash`. It does not consume selected-pass result-review fields. Server-owned Gate B authority supplies selected source IDs and the decision manifest; request-supplied source IDs are not trusted.

## Runtime Contract

The preview response uses schema `layer3.mixed_source_package_review_preview.v1` and returns:

- `package_family`: `mixed_dataset_document`.
- `contract_schema_id`: `layer3.mixed_source_package_contract.v1`.
- `contract_hash` and `package_review_preview_hash`.
- Selected `dataset_version_ids` and `aps_content_document_ids`.
- Deterministic narrative-table link records with `operator_selected_pair` link type.
- Empty `missing_authority_inputs` on the happy path.
- Negative authority flags proving no schema/migration, parser behavior, source-shape expansion, payload rewrite, handoff, export, or Onlook behavior is admitted.

## Fail-Closed Boundaries

The runtime fails closed when:

- `material_preview_id` or `material_preview_hash` is missing, malformed, or stale against the committed Gate B session authority.
- Gate B authority is absent or internally inconsistent.
- Approved Gate B material is missing either `dataset_version` or `aps_content_document`.
- Approved material contains unexpected source classes or duplicate selected source identities.
- Legacy selected-pass preview fields are supplied with the mixed material-authority request.
- Explicit package, handoff, export, source-widening, payload rewrite, runtime DB write, APS handoff, or Onlook fields are supplied.

Selected-pass review states marked `mixed_dataset_document` still do not enter the legacy package-review preview flow; they return `mixed_source_package_review_preview_requires_material_authority`.

## Non-Goals

- No mixed-source package construction commit.
- No mixed-source package review submit.
- No mixed-source handoff/export, APS handoff, connector dispatch, public URL, or external download behavior.
- No schema or migration change.
- No parser behavior change.
- No source-shape expansion or generic XML/HTML admission.
- No archive-member orchestration.
- No legacy CSV bridge deprecation.
- No Onlook behavior.

## Verification

- `python -B -m py_compile .\backend\app\api\layer3.py .\backend\app\services\layer3_workbench.py .\backend\app\services\layer3_package_review_contract.py .\backend\app\services\layer3_package_family_policy.py .\backend\app\services\layer3_workbench_package_state.py .\backend\tests\test_layer3_api.py .\backend\tests\test_layer3_package_family_policy.py .\backend\tests\test_layer3_workbench.py`
- `python -B -m json.tool .\next_milestone_plans\authority-index.json`
- `python -B -m json.tool .\next_milestone_plans\layer3_progress_manifest.json`
- `python -B -m json.tool .\next_milestone_plans\layer3_workbench_proof_manifest.json`
- `python -B .\tools\l3-authority-index-validate.py`
- `python -B .\tools\l3-target-selection-validate.py --expect frozen`
- `python -B .\tools\l3-progress-check.py`
- `python -B -m pytest .\backend\tests\test_layer3_api.py::test_layer3_package_openapi_contracts .\backend\tests\test_layer3_api.py::test_layer3_api_material_preview_surfaces_mixed_source_package_readiness .\backend\tests\test_layer3_api.py::test_layer3_api_mixed_source_package_review_preview_is_read_only .\backend\tests\test_layer3_api.py::test_layer3_api_mixed_source_package_review_preview_rejects_stale_authority .\backend\tests\test_layer3_api.py::test_layer3_api_mixed_source_package_review_preview_requires_both_material_classes .\backend\tests\test_layer3_api.py::test_layer3_api_mixed_source_package_review_preview_rejects_legacy_and_onlook_fields .\backend\tests\test_layer3_api.py::test_layer3_api_package_review_preview_requires_approved_result_review_and_is_read_only .\backend\tests\test_layer3_api.py::test_layer3_api_package_review_preview_prechecks_fail_closed .\backend\tests\test_layer3_api.py::test_layer3_api_package_review_preview_blocks_unadmitted_package_family`
- `python -B -m pytest .\backend\tests\test_layer3_package_family_policy.py .\backend\tests\test_layer3_workbench_package_state.py .\backend\tests\test_layer3_package_review_contract.py .\backend\tests\test_layer3_package_submit_response.py .\backend\tests\test_layer3_workbench.py -q`
- `python -B -m pytest .\backend\tests\test_layer3_api.py -k "mixed_source_package or package_review_preview or gate_b"`

## Next Posture

The next implementation pass should decide whether and how to admit mixed-source package construction commit from the P14 preview hash. Until that pass lands, commit, submit, handoff, export, parser, schema, source-shape, payload rewrite, and excluded-tool behavior remain blocked.
