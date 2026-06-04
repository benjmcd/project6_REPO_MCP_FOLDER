# P15 Mixed-Source Package Construction Runtime Closeout

Status: branch-local runtime implementation pending PR merge.

## Scope

This tranche implements the first mixed-source package construction commit
runtime selected by `32-p15-mixed-construction-freeze.md`.
Runtime response schema: `layer3.mixed_source_package_construction_commit.v1`.

The route remains `POST /api/v1/layer3/package/review/commit`, but a
mixed-source request is admitted only when it uses material-authority fields:

- `client_request_id`
- `session_id`
- `material_preview_id`
- `material_preview_hash`
- `package_review_preview_hash`
- `contract_hash`
- optional `expected_package_kinds`

Selected-pass fields remain invalid for this mixed-source path:
`analysis_plan_id`, `pass_run_id`, `preview_id`, `preview_hash`,
`result_review_record_ref`, and `analysis_run_id`.

## Runtime Authority

The runtime recomputes the P14 mixed-source package-review preview from
committed Gate B material authority before writing any package rows. The
supplied `package_review_preview_hash` and `contract_hash` must match the
server-recomputed values.

Construction writes exactly one reconciliation record and three package rows:

- `canonical_internal`
- `user_facing`
- `review_facing`

Package payloads are server-owned manifests over existing P14/P12 authority:
source manifest, narrative-table links, selected `dataset_version` IDs,
selected `aps_content_document` IDs, contract hash, and negative authority
flags. The API response exposes stable package API refs rather than local
filesystem paths.

## Guardrails

- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No submit, handoff, export, APS handoff, external export/download,
  connector dispatch, provider-public URL, or public URL behavior.
- No request-supplied package payload bytes, payload refs, generated text, or
  payload rewrite.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- Legacy selected-pass mixed package markers remain blocked and must use
  material-preview authority instead.

## Verification

Focused branch-local checks:

- `python -B -m py_compile` for touched API/service/test files.
- `python -B -m pytest .\backend\tests\test_layer3_package_family_policy.py .\backend\tests\test_layer3_package_review_contract.py .\backend\tests\test_layer3_workbench_package_state.py -q`
- `python -B -m pytest .\backend\tests\test_layer3_api.py -q -k "mixed_source_package or package_construction_commit or package_openapi_contracts"`

The full closeout also requires authority-index validation, frozen
target-selection validation, progress check, JSON manifest validation, and
`git diff --check`.

## Remaining Work

Mixed-source package-review submit, handoff/export, parser/source-family
expansion, schema changes, payload rewrite, legacy bridge deprecation, and
production-readiness activation remain separate future tranches.
