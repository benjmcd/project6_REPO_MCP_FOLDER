# P16 Mixed-Source Package Review Submit Freeze

Status: branch-local planning/control freeze only. No mixed-source package-review submit runtime is admitted in this pass.

## Scope

This freeze selects the next implementation boundary after P15: a future mixed-source package-review submit over the package manifests already created by `33-p15-runtime-closeout.md`.

The future runtime pass may proceed only from:

- `client_request_id`
- `session_id`
- `material_preview_id`
- `material_preview_hash`
- `package_review_preview_hash`
- `contract_hash`
- `construction_basis_hash`
- `reconciliation_record_id`
- `output_package_ids`
- `payload_hashes`
- `operator_decision`
- optional `decision_notes`
- optional `expected_package_kinds`

The only admitted `operator_decision` values are:

- `approved`
- `changes_requested`
- `rejected`
- `blocked`

`decision_notes` must be required for `changes_requested`, `rejected`, and `blocked`. `approved` may include notes, but notes must not become payload rewrite authority.

The future runtime must not accept selected-pass `analysis_plan_id`, `pass_run_id`, `preview_id`, `preview_hash`, `result_review_record_ref`, or `analysis_run_id` fields for mixed-source submit. Those remain selected-pass package lifecycle authority, not mixed material-authority lifecycle authority.

## Canonical Authority

Mixed-source submit authority must be recomputed from server-owned state:

1. Load the `L3Session` by `session_id`.
2. Require the committed Gate B material decision on that session.
3. Require `material_preview_id` and `material_preview_hash` to match the Gate B idempotency record.
4. Require the stored Gate B decision manifest hash to match the manifest in session operator context.
5. Recompute the P14 mixed-source package-review preview basis, including selected `dataset_version` and `aps_content_document` source IDs, source manifest, narrative-table links, `contract_hash`, and `package_review_preview_hash`.
6. Load the P15 reconciliation record by `session_id` and `reconciliation_record_id`.
7. Require the reconciliation source gate and package family to be the mixed-source construction runtime boundary from P15.
8. Require P15 construction authority to match the recomputed P14/P12 basis through `construction_basis_hash`, `contract_hash`, and `package_review_preview_hash`.
9. Require exactly the three P15 package rows for `canonical_internal`, `user_facing`, and `review_facing`.
10. Require supplied `output_package_ids`, `payload_hashes`, and optional `expected_package_kinds` to match the current server-loaded package rows.

No request-supplied source IDs, package payload bytes, payload refs, generated text, local paths, provider URLs, connector refs, public URLs, handoff targets, export modes, or edited findings may become submit authority.

## Future Runtime Contract

The first implementation pass should add a mixed-source submit response with schema id:

- `layer3.mixed_source_package_review_submit.v1`

The commit should record exactly one submit decision state over the existing P15 reconciliation/package set. The state belongs with package-review lifecycle state, not with parser output, material preview output, or source-family rows.

The submit state should include:

- `submit_record_ref`
- `package_review_submit_schema_id`
- `package_review_state`
- `operator_decision`
- `decision_notes`
- `material_preview_id`
- `material_preview_hash`
- `contract_hash`
- `package_review_preview_hash`
- `construction_basis_hash`
- `reconciliation_record_id`
- `output_package_ids`
- `package_kinds`
- `payload_hashes`
- package family `mixed_dataset_document`
- negative authority flags

`approved` may make the package-review state approved, but must not enable handoff, export, APS handoff, external export/download, connector dispatch, provider-public URL, public URL, source expansion, parser behavior, payload rewrite, or production readiness in the same tranche.

## Idempotency

Submit idempotency key must include:

- package family: `mixed_dataset_document`
- `client_request_id`
- `session_id`
- `material_preview_id`
- `material_preview_hash`
- `contract_hash`
- `package_review_preview_hash`
- `construction_basis_hash`
- `reconciliation_record_id`
- ordered `output_package_ids`
- ordered `payload_hashes`
- expected package kinds
- `operator_decision`
- `decision_notes`

Same authority basis and same `client_request_id` should replay the existing submit result. Same `client_request_id` with changed authority or changed decision must fail closed. Same package set with a different `client_request_id` after submit should fail as already submitted unless the implementation explicitly freezes and tests a replay-by-authority rule.

## Fail-Closed Cases

Future implementation must cover:

- missing `client_request_id`
- missing or stale `material_preview_id`
- missing or stale `material_preview_hash`
- missing or stale `package_review_preview_hash`
- missing or stale `contract_hash`
- missing or stale `construction_basis_hash`
- missing Gate B material authority
- malformed Gate B decision manifest
- missing P15 reconciliation record
- P15 reconciliation source gate or package family mismatch
- missing, partial, or extra package rows
- unexpected package kind
- stale or mismatched `output_package_ids`
- stale or mismatched `payload_hashes`
- unsupported `operator_decision`
- missing `decision_notes` for non-approval decisions
- selected-pass lifecycle fields on mixed submit request
- package payload or payload rewrite fields on request
- handoff/export/APS handoff/external export/provider/connector/public URL fields on request
- source expansion, parser, schema, migration, local upload, or local directory fields on request
- excluded-tool field on request
- existing conflicting submit state

## Non-Goals

- No runtime code change in this freeze.
- No package-family policy change in this freeze.
- No mixed-source package-review submit admission in this freeze.
- No handoff/export, APS handoff, external export/download, connector dispatch, provider-public URL, or public URL behavior.
- No schema/model/migration change.
- No parser behavior change.
- No source-shape expansion.
- No package payload rewrite from request data.
- No package reconstruction.
- No legacy CSV bridge deprecation.
- No excluded-tool behavior.
- No production-readiness activation.

## Implementation Entry Gate

Implementation may begin only after this freeze is merged and current-main synced. The implementation pass must keep handoff, export, parser, schema, source-shape, payload rewrite, legacy bridge, excluded-tool behavior, and production readiness blocked unless a later freeze admits exactly one of those surfaces.

## Verification For This Freeze

This freeze should validate only docs/manifests:

- JSON syntax for shared manifests.
- Layer 3 authority-index validation.
- Layer 3 target-selection frozen validation.
- Layer 3 progress check.
- `git diff --check`.
